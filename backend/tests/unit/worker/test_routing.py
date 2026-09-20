import importlib
import sys
import types

import pytest


def load_worker_module(monkeypatch):
    litserve = types.ModuleType("litserve")

    class LitAPI:
        def __init__(self, *args, **kwargs):
            pass

    litserve.LitAPI = LitAPI
    litserve.LitServer = object
    connector = types.ModuleType("litserve.connector")
    connector.check_cuda_with_nvidia_smi = lambda: False
    mcp = types.ModuleType("litserve.mcp")
    monkeypatch.setitem(sys.modules, "litserve", litserve)
    monkeypatch.setitem(sys.modules, "litserve.connector", connector)
    monkeypatch.setitem(sys.modules, "litserve.mcp", mcp)
    sys.modules.pop("litserve_worker", None)
    return importlib.import_module("litserve_worker")


def make_worker(worker_module, mocker):
    worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
    worker.mineru_vllm_api = "http://vllm.example/v1"
    worker.vllm_controller = mocker.Mock()
    worker.watermark_handler = None
    worker.markitdown = object()
    worker.task_db = mocker.Mock()
    worker._enqueue_webhook = mocker.Mock()
    worker._should_split_pdf = mocker.Mock(return_value=False)
    worker._should_split_zip = mocker.Mock(return_value=False)
    worker._process_with_mineru = mocker.Mock(
        return_value={
            "result_path": "/output/task-1",
            "pdf_path": "source.pdf",
            "json_content": [{"type": "text"}],
            "content": "# Result",
            "markdown_file": "result.md",
        }
    )
    return worker


def test_external_vllm_url_does_not_trigger_local_container_start(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    source = tmp_path / "document.pdf"
    source.write_bytes(b"pdf")

    worker._process_task(
        {
            "task_id": "task-1",
            "file_path": str(source),
            "backend": "vlm-http-client",
            "options": '{"server_url":"https://remote.example/v1"}',
        }
    )

    worker.vllm_controller.ensure_running.assert_not_called()
    worker._process_with_mineru.assert_called_once()
    update = worker.task_db.update_task_status.call_args.kwargs
    assert update["status"] == "completed"
    assert '"pdf_path": "source.pdf"' in update["data"]
    assert '"markdown_file": "result.md"' in update["data"]
    worker._enqueue_webhook.assert_called_once_with("task-1", "task.completed")


def test_local_vllm_backend_starts_container_and_pdf_split_short_circuits(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    source = tmp_path / "document.pdf"
    source.write_bytes(b"pdf")

    worker._process_task(
        {
            "task_id": "task-1",
            "file_path": str(source),
            "backend": "vlm-http-client",
            "options": "{}",
        }
    )
    worker.vllm_controller.ensure_running.assert_called_once_with(worker_module.VLLM_MINERU_CONTAINER)

    worker = make_worker(worker_module, mocker)
    worker._should_split_pdf.return_value = True
    worker._process_task(
        {
            "task_id": "task-2",
            "file_path": str(source),
            "backend": "pipeline",
            "options": "{}",
        }
    )
    worker._process_with_mineru.assert_not_called()
    worker.task_db.update_task_status.assert_not_called()
    worker._enqueue_webhook.assert_not_called()


def test_worker_failure_marks_task_failed_and_enqueues_one_failure_webhook(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    worker._process_with_mineru.side_effect = RuntimeError("engine failure")
    source = tmp_path / "document.pdf"
    source.write_bytes(b"pdf")

    with pytest.raises(RuntimeError, match="engine failure"):
        worker._process_task(
            {
                "task_id": "task-1",
                "file_path": str(source),
                "backend": "pipeline",
                "options": "{}",
            }
        )

    update = worker.task_db.update_task_status.call_args
    assert update.args[1] == "failed"
    assert "RuntimeError: engine failure" in update.kwargs["error_message"]
    worker._enqueue_webhook.assert_called_once_with("task-1", "task.failed")
