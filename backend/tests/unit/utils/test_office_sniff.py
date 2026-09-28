"""Office 文件真实格式识别

线上 10 个 .xlsx（销售提成、调薪提名表）全部报 BadZipFile：文件受加密保护，
加密后是 OLE 复合文档而不是 ZIP。另有改了扩展名的旧版 .xls、HTML 伪装的表格。
"""

import pytest

from utils.office_sniff import EncryptedDocumentError, encrypted_document_message, sniff_office_file

OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 504


def u16(name):
    return name.encode("utf-16-le")


def ole_with(*names):
    # 目录项名为 UTF-16LE，位置不固定（常在文件末尾）
    return OLE + b"\x00" * 4096 + b"".join(u16(n) + b"\x00\x00" for n in names)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"PK\x03\x04" + b"\x00" * 100, ("ooxml", None)),
        (
            ole_with("EncryptionInfo", "EncryptedPackage", "DRMEncryptedDataSpace", "DRMEncryptedTransform"),
            ("encrypted", "irm"),
        ),
        (
            ole_with("EncryptionInfo", "EncryptedPackage", "StrongEncryptionDataSpace", "StrongEncryptionTransform"),
            ("encrypted", "password"),
        ),
        (ole_with("EncryptionInfo", "EncryptedPackage"), ("encrypted", "unknown")),
        (ole_with("Workbook", "SummaryInformation"), ("legacy", ".xls")),
        (ole_with("WordDocument", "1Table"), ("legacy", ".doc")),
        (ole_with("PowerPoint Document", "Current User"), ("legacy", ".ppt")),
        (b"\xef\xbb\xbf  <html><table><tr><td>1</td></tr></table></html>", ("html", ".html")),
        (b'<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"/>', ("html", ".html")),
        (b"garbage bytes", ("unknown", None)),
    ],
)
def test_sniff_by_content(tmp_path, content, expected):
    path = tmp_path / "file.xlsx"
    path.write_bytes(content)

    result = sniff_office_file(path)

    assert (result.kind, result.detail) == expected
    assert sniff_office_file(content, extension=".xlsx") == result


def test_non_ooxml_extensions_are_not_read(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(ole_with("EncryptedPackage"))

    assert sniff_office_file(path).kind == "unknown"


def test_real_password_encrypted_xlsx_is_detected(tmp_path):
    """用 msoffcrypto 生成与 Excel「用密码进行加密」相同格式的真实加密文件"""
    ooxml = pytest.importorskip("msoffcrypto.format.ooxml")
    from openpyxl import Workbook

    plain = tmp_path / "plain.xlsx"
    Workbook().save(plain)
    encrypted = tmp_path / "encrypted.xlsx"
    with open(plain, "rb") as fi, open(encrypted, "wb") as fo:
        ooxml.OOXMLFile(fi).encrypt("secret", fo)

    assert sniff_office_file(plain).kind == "ooxml"
    result = sniff_office_file(encrypted)
    assert (result.kind, result.detail) == ("encrypted", "password")


@pytest.mark.parametrize("protection", ["irm", "password", "unknown"])
def test_encrypted_error_message_is_readable(protection):
    err = EncryptedDocumentError(protection, "Q2 Sales Commission.xlsx")

    assert isinstance(err, ValueError)
    assert "Q2 Sales Commission.xlsx" in str(err)
    assert "无法解析" in str(err)
    assert str(err) == encrypted_document_message(protection, "Q2 Sales Commission.xlsx")
