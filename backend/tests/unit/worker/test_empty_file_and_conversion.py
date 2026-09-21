"""空文件拦截与旧版 Office 转换的健壮性

对应线上故障：
  - 0 字节文件被一路送进解析引擎，最终由 pdfium 抛出
    `PdfiumError: Failed to load document (PDFium: Data format error).`
    （日志里 _should_split_pdf 已经打印 "Cannot read an empty file" 却继续执行）
  - LibreOffice 转换失败时错误被 capture_output 吞掉，error_message 只剩退出码
"""

import sys

import pytest

from test_routing import load_worker_module, make_worker


class TestEmptySourceFile:
    def test_validate_rejects_empty_file(self, monkeypatch, tmp_path):
        worker_module = load_worker_module(monkeypatch)
        empty = tmp_path / "empty.docx"
        empty.write_bytes(b"")

        with pytest.raises(ValueError, match="内容为空"):
            worker_module.MinerUWorkerAPI._validate_source_file(str(empty))

    def test_validate_rejects_missing_file(self, monkeypatch, tmp_path):
        worker_module = load_worker_module(monkeypatch)

        with pytest.raises(FileNotFoundError):
            worker_module.MinerUWorkerAPI._validate_source_file(str(tmp_path / "nope.pdf"))

    def test_validate_accepts_normal_file(self, monkeypatch, tmp_path):
        worker_module = load_worker_module(monkeypatch)
        ok = tmp_path / "ok.pdf"
        ok.write_bytes(b"%PDF-1.4")

        assert worker_module.MinerUWorkerAPI._validate_source_file(str(ok)) == 8

    def test_empty_file_fails_task_before_reaching_engine(self, monkeypatch, mocker, tmp_path):
        """核心回归：空文件绝不能走到解析引擎"""
        worker_module = load_worker_module(monkeypatch)
        monkeypatch.setattr(worker_module, "MINERU_PIPELINE_AVAILABLE", True)
        worker = make_worker(worker_module, mocker)
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")

        # _process_task 记录失败状态后会把异常重新抛出，交给 _worker_loop
        with pytest.raises(ValueError):
            worker._process_task({"task_id": "t-empty", "file_path": str(empty), "backend": "auto", "options": "{}"})

        worker._process_with_mineru.assert_not_called()
        # 失败路径按位置传参：update_task_status(task_id, "failed", error_message=...)
        call = worker.task_db.update_task_status.call_args
        assert call.args[1] == "failed"
        assert "空" in call.kwargs["error_message"]


class TestConversionDiagnostics:
    def test_tail_strips_java_warning(self, monkeypatch):
        worker_module = load_worker_module(monkeypatch)
        out = b"Warning: failed to launch javaldx - java may not function correctly\nError: real problem\n"

        assert worker_module.MinerUWorkerAPI._tail(out) == "Error: real problem"

    def test_tail_handles_empty_and_binary(self, monkeypatch):
        worker_module = load_worker_module(monkeypatch)

        assert worker_module.MinerUWorkerAPI._tail(b"") == ""
        assert worker_module.MinerUWorkerAPI._tail(b"\xff\xfe bad bytes") != ""

    def test_nonzero_exit_surfaces_stderr(self, monkeypatch, mocker, tmp_path):
        """转换失败时 LibreOffice 的 stderr 必须出现在错误信息里"""
        worker_module = load_worker_module(monkeypatch)
        worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
        src = tmp_path / "doc.doc"
        src.write_bytes(b"ole2-ish")
        mocker.patch.object(
            worker_module.MinerUWorkerAPI,
            "_run_with_process_group",
            return_value=(b"", b"Error: source file could not be loaded", 1),
        )

        with pytest.raises(RuntimeError, match="source file could not be loaded"):
            worker._convert_office_to_new_format(str(src))

    def test_exit_zero_without_output_surfaces_streams(self, monkeypatch, mocker, tmp_path):
        """LibreOffice 常见行为：退出 0 但没产出，错误信息要带上它说了什么"""
        worker_module = load_worker_module(monkeypatch)
        worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
        src = tmp_path / "doc.doc"
        src.write_bytes(b"ole2-ish")
        mocker.patch.object(
            worker_module.MinerUWorkerAPI,
            "_run_with_process_group",
            return_value=(b"nothing converted", b"", 0),
        )

        with pytest.raises(RuntimeError, match="output missing"):
            worker._convert_office_to_new_format(str(src))

    def test_empty_source_rejected_before_launching_libreoffice(self, monkeypatch, mocker, tmp_path):
        worker_module = load_worker_module(monkeypatch)
        worker = worker_module.MinerUWorkerAPI.__new__(worker_module.MinerUWorkerAPI)
        src = tmp_path / "empty.doc"
        src.write_bytes(b"")
        run = mocker.patch.object(worker_module.MinerUWorkerAPI, "_run_with_process_group")

        # 校验发生在启动 LibreOffice 之前，直接抛 ValueError（不包装成 RuntimeError）
        with pytest.raises(ValueError, match="内容为空"):
            worker._convert_office_to_new_format(str(src))
        run.assert_not_called()


class TestProcessGroupCleanup:
    def test_normal_exit_returns_streams(self, monkeypatch):
        worker_module = load_worker_module(monkeypatch)

        stdout, stderr, rc = worker_module.MinerUWorkerAPI._run_with_process_group(
            [sys.executable, "-c", "import sys; sys.stdout.write('out'); sys.stderr.write('err')"], 30
        )

        assert stdout == b"out" and stderr == b"err" and rc == 0

    def test_timeout_kills_and_raises(self, monkeypatch):
        worker_module = load_worker_module(monkeypatch)

        with pytest.raises(RuntimeError, match="转换超时"):
            worker_module.MinerUWorkerAPI._run_with_process_group(
                [sys.executable, "-c", "import time; time.sleep(30)"], 1
            )
