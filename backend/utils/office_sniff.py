"""
Office 文件真实格式识别

.xlsx / .docx / .pptx 本应是 ZIP 包（OOXML），但线上常见三类「扩展名对、内容不对」的文件：
- 加密文件：敏感度标签 / IRM 权限管理、或设置了打开密码的 Office 文件，加密后是 OLE 复合文档，
  里面只有 EncryptionInfo / EncryptedPackage 两个流，任何解析器都读不出内容
- 旧版格式改了扩展名：业务系统「导出 Excel」导出的其实是 .xls（OLE），却命名为 .xlsx
- 网页伪装的表格：导出的是 HTML 表格或 Excel 2003 XML

按扩展名直接交给解析器只会得到 BadZipFile 之类的内部报错。这里按文件头识别真实格式，
加密文件给出可读的失败原因，改名的旧格式 / HTML 转交对应的解析路径。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

OOXML_EXTENSIONS = frozenset({".xlsx", ".docx", ".pptx"})

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
# OLE 目录项名是 UTF-16LE；目录可能在文件末尾，所以需要读完整个 OLE 文件（加密 / 旧版 Office 通常只有几 MB）
_MAX_OLE_SCAN_BYTES = 256 * 1024 * 1024


def _u16(name: str) -> bytes:
    return name.encode("utf-16-le")


# 加密容器（MS-OFFCRYPTO）：数据空间里的变换名区分 IRM 与密码加密
_ENCRYPTED_MARKERS = (_u16("EncryptedPackage"), _u16("EncryptionInfo"))
_IRM_MARKERS = (_u16("DRMEncryptedTransform"), _u16("DRMEncryptedDataSpace"))
_PASSWORD_MARKERS = (_u16("StrongEncryptionTransform"), _u16("StrongEncryptionDataSpace"))

# 旧版 Office 的主数据流名 → 对应扩展名
_LEGACY_STREAMS = (
    (_u16("WordDocument"), ".doc"),
    (_u16("PowerPoint Document"), ".ppt"),
    (_u16("Workbook"), ".xls"),
    (_u16("Book"), ".xls"),
)


@dataclass(frozen=True)
class OfficeSniffResult:
    """kind: ooxml | encrypted | legacy | html | unknown"""

    kind: str
    # legacy / html：应改用的扩展名；encrypted：保护类型 irm / password / unknown
    detail: Optional[str] = None


class EncryptedDocumentError(ValueError):
    """Office 文件受加密保护，无法解析（不做任何绕过尝试）"""

    def __init__(self, protection: str, file_name: str = ""):
        self.protection = protection
        self.file_name = file_name
        super().__init__(encrypted_document_message(protection, file_name))


def encrypted_document_message(protection: str, file_name: str = "") -> str:
    name = f"「{file_name}」" if file_name else "该文件"
    if protection == "irm":
        return (
            f"{name}受权限管理保护（敏感度标签 / IRM 加密），无法解析。"
            "请在 Office 中移除保护，或另存为未加密的副本后重新上传。"
        )
    if protection == "password":
        return f"{name}设置了打开密码，无法解析。请在 Office 中移除密码后重新上传。"
    return f"{name}已加密，无法解析。请移除加密后重新上传。"


def sniff_office_file(source: Union[str, Path, bytes], extension: Optional[str] = None) -> OfficeSniffResult:
    """识别 .xlsx / .docx / .pptx 的真实格式；其他扩展名直接返回 unknown，不读文件"""
    if isinstance(source, (str, Path)):
        path = Path(source)
        ext = (extension or path.suffix).lower()
        if ext not in OOXML_EXTENSIONS:
            return OfficeSniffResult("unknown")
        with open(path, "rb") as fh:
            head = fh.read(8)
            if head.startswith(_OLE_MAGIC):
                fh.seek(0)
                data = fh.read(_MAX_OLE_SCAN_BYTES)
            else:
                data = head + fh.read(4096)
    else:
        ext = (extension or "").lower()
        if ext not in OOXML_EXTENSIONS:
            return OfficeSniffResult("unknown")
        data = source[:_MAX_OLE_SCAN_BYTES]

    if data.startswith(_ZIP_MAGIC):
        return OfficeSniffResult("ooxml")

    if data.startswith(_OLE_MAGIC):
        if any(m in data for m in _ENCRYPTED_MARKERS):
            if any(m in data for m in _IRM_MARKERS):
                return OfficeSniffResult("encrypted", "irm")
            if any(m in data for m in _PASSWORD_MARKERS):
                return OfficeSniffResult("encrypted", "password")
            return OfficeSniffResult("encrypted", "unknown")
        for marker, legacy_ext in _LEGACY_STREAMS:
            if marker in data:
                return OfficeSniffResult("legacy", legacy_ext)
        return OfficeSniffResult("unknown")

    text_head = data.lstrip(b"\xef\xbb\xbf \t\r\n")[:1]
    if text_head == b"<":
        return OfficeSniffResult("html", ".html")

    return OfficeSniffResult("unknown")
