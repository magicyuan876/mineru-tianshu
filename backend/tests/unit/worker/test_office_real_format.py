from pathlib import Path

import pytest

from tests.unit.utils.test_office_sniff import ole_with
from tests.unit.worker.test_routing import load_worker_module, make_worker


def task_for(path):
    return {
        "task_id": "task-office",
        "file_path": str(path),
        "file_name": path.name,
        "backend": "auto",
        "options": "{}",
    }


def test_encrypted_xlsx_fails_with_readable_reason(monkeypatch, mocker, tmp_path):
    worker = make_worker(load_worker_module(monkeypatch), mocker)
    worker._process_with_markitdown = mocker.Mock()
    source = tmp_path / "Q2 Sales Commission.xlsx"
    source.write_bytes(ole_with("EncryptionInfo", "EncryptedPackage", "DRMEncryptedTransform"))

    with pytest.raises(ValueError, match="权限管理保护"):
        worker._process_task(task_for(source))

    worker._process_with_markitdown.assert_not_called()
    update = worker.task_db.update_task_status.call_args
    assert update.args[1] == "failed"
    assert update.kwargs["error_message"].startswith("EncryptedDocumentError: ")
    assert "BadZipFile" not in update.kwargs["error_message"]


@pytest.mark.parametrize(
    ("markers", "real_ext"),
    [(("Workbook",), ".xls"), (None, ".html")],
)
def test_renamed_legacy_or_html_is_parsed_by_real_format(monkeypatch, mocker, tmp_path, markers, real_ext):
    worker = make_worker(load_worker_module(monkeypatch), mocker)
    seen = {}

    def fake_markitdown(path):
        seen["path"] = path
        seen["existed"] = Path(path).exists()
        return {"result_path": "/output/x", "pdf_path": None, "content": "ok"}

    worker._process_with_markitdown = mocker.Mock(side_effect=fake_markitdown)
    source = tmp_path / "export.xlsx"
    source.write_bytes(ole_with(*markers) if markers else b"<html><table><tr><td>1</td></tr></table></html>")

    worker._process_task(task_for(source))

    assert Path(seen["path"]).suffix == real_ext
    assert Path(seen["path"]).stem == source.stem  # 输出目录名不变
    assert seen["existed"] is True
    assert not Path(seen["path"]).exists()  # 纠正用的副本解析完即删除
    assert source.exists()  # 原始上传文件保留，重试还要用
    assert worker.task_db.update_task_status.call_args.kwargs["status"] == "completed"
