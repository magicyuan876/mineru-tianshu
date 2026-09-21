import importlib
import sys
import types
from pathlib import Path

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


def test_legacy_office_conversion_uses_unique_libreoffice_profiles(monkeypatch, mocker, tmp_path):
    """每次转换必须使用独立的 UserInstallation profile

    LibreOffice 是单实例模型：多个进程共用默认 profile 时，后来的调用会把活交给
    已有实例后直接退出，表现为 exit 1 或 exit 0 但无产出。Worker 有多个进程并发，
    线上正是因此出现大量转换失败。
    """
    worker_module = load_worker_module(monkeypatch)
    worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
    source = tmp_path / "legacy.xls"
    source.write_bytes(b"xls")
    commands = []

    def fake_run(command, timeout):
        commands.append((command, timeout))
        output_dir = Path(command[command.index("--outdir") + 1])
        (output_dir / "legacy.xlsx").write_bytes(b"xlsx")
        return b"", b"", 0

    mocker.patch.object(worker_module.MinerUWorkerAPI, "_run_with_process_group", side_effect=fake_run)

    first_output = worker._convert_office_to_new_format(str(source))
    second_output = worker._convert_office_to_new_format(str(source))

    assert first_output == str(tmp_path / "legacy.xlsx")
    assert second_output == str(tmp_path / "legacy.xlsx")
    assert len(commands) == 2
    profiles = []
    for command, timeout in commands:
        profile = next(argument for argument in command if argument.startswith("-env:UserInstallation="))
        profiles.append(profile)
        assert command[0] == "libreoffice"
        assert command[command.index("--convert-to") + 1] == "xlsx"
        assert timeout == 180
    assert profiles[0] != profiles[1]


def test_legacy_office_conversion_timeout_is_configurable(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setenv("OFFICE_CONVERT_TIMEOUT", "42")
    worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"doc")
    seen = []

    def fake_run(command, timeout):
        seen.append(timeout)
        Path(command[command.index("--outdir") + 1], "legacy.docx").write_bytes(b"docx")
        return b"", b"", 0

    mocker.patch.object(worker_module.MinerUWorkerAPI, "_run_with_process_group", side_effect=fake_run)
    worker._convert_office_to_new_format(str(source))

    assert seen == [42]


def test_legacy_office_conversion_failure_skips_markitdown(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    worker._convert_office_to_new_format = mocker.Mock(side_effect=RuntimeError("conversion timed out"))
    worker._process_with_markitdown = mocker.Mock()
    source = tmp_path / "legacy.xls"
    source.write_bytes(b"xls")

    with pytest.raises(RuntimeError, match="conversion timed out"):
        worker._process_task(
            {"task_id": "task-office-timeout", "file_path": str(source), "backend": "auto", "options": "{}"}
        )

    worker._process_with_mineru.assert_not_called()
    worker._process_with_markitdown.assert_not_called()
    update = worker.task_db.update_task_status.call_args
    assert update.args[1] == "failed"
    worker._enqueue_webhook.assert_called_once_with("task-office-timeout", "task.failed")


def test_legacy_office_conversion_passes_ooxml_to_mineru(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"doc")
    converted = tmp_path / "legacy.docx"
    worker._convert_office_to_new_format = mocker.Mock(return_value=str(converted))
    worker._process_with_markitdown = mocker.Mock()

    worker._process_task(
        {"task_id": "task-office-success", "file_path": str(source), "backend": "auto", "options": "{}"}
    )

    worker._process_with_mineru.assert_called_once_with(str(converted), {"parse_mode": "pipeline"})
    worker._process_with_markitdown.assert_not_called()


@pytest.mark.parametrize("mineru_result", [RuntimeError("engine failure"), None])
def test_legacy_office_mineru_failure_falls_back_with_converted_file(monkeypatch, mocker, tmp_path, mineru_result):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    source = tmp_path / "legacy.xls"
    source.write_bytes(b"xls")
    converted = tmp_path / "legacy.xlsx"
    worker._convert_office_to_new_format = mocker.Mock(return_value=str(converted))
    if isinstance(mineru_result, Exception):
        worker._process_with_mineru.side_effect = mineru_result
    else:
        worker._process_with_mineru.return_value = mineru_result
    worker._process_with_markitdown = mocker.Mock(
        return_value={
            "result_path": "/output/task-office-fallback",
            "pdf_path": None,
            "json_content": [],
            "content": "# Fallback",
            "markdown_file": "result.md",
        }
    )

    worker._process_task(
        {"task_id": "task-office-fallback", "file_path": str(source), "backend": "auto", "options": "{}"}
    )

    worker._process_with_markitdown.assert_called_once_with(str(converted))
    update = worker.task_db.update_task_status.call_args.kwargs
    assert update["status"] == "completed"


def test_legacy_office_mineru_failure_without_markitdown_preserves_error(monkeypatch, mocker, tmp_path):
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
    worker = make_worker(worker_module, mocker)
    source = tmp_path / "legacy.ppt"
    source.write_bytes(b"ppt")
    converted = tmp_path / "legacy.pptx"
    worker._convert_office_to_new_format = mocker.Mock(return_value=str(converted))
    worker._process_with_mineru.side_effect = RuntimeError("engine failure")
    worker.markitdown = None

    with pytest.raises(RuntimeError, match="engine failure"):
        worker._process_task(
            {"task_id": "task-office-no-fallback", "file_path": str(source), "backend": "auto", "options": "{}"}
        )

    update = worker.task_db.update_task_status.call_args
    assert update.args[1] == "failed"
    assert "RuntimeError: engine failure" in update.kwargs["error_message"]
