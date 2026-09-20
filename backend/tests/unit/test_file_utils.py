import pytest

from utils.file_utils import FilenameValidationError, ensure_within_directory, sanitize_filename


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("report.PDF", "report.pdf"),
        ("../../report.pdf", "report.pdf"),
        (r"C:\uploads\report.pdf", "report.pdf"),
        ("report<draft>.pdf", "report_draft_.pdf"),
    ],
)
def test_sanitize_filename_removes_path_components_and_unsafe_characters(raw_name, expected):
    assert sanitize_filename(raw_name) == expected


@pytest.mark.parametrize("raw_name", ["", "../", "con.pdf", "report.exe", "report", ".pdf"])
def test_sanitize_filename_rejects_unsafe_or_unsupported_names(raw_name):
    with pytest.raises(FilenameValidationError):
        sanitize_filename(raw_name)


def test_ensure_within_directory_accepts_managed_path(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    file_path = uploads / "report.pdf"

    assert ensure_within_directory(file_path, uploads) == file_path.resolve()


def test_ensure_within_directory_rejects_escaped_path(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    escaped_path = tmp_path / "outside.pdf"

    with pytest.raises(FilenameValidationError):
        ensure_within_directory(escaped_path, uploads)
