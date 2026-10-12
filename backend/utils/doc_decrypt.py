"""
加密文档前置解密

支持三类加密格式，密码由用户在提交任务时提供：
- PDF：打开密码（pikepdf）；空密码 / 仅所有者密码的 PDF 顺手移除限制另存明文副本
- Office：.docx/.xlsx/.pptx 及旧版 .doc/.xls/.ppt 的打开密码（msoffcrypto-tool）
- ZIP：传统 ZipCrypto 与 AES 加密（pyzipper）

统一入口 decrypt_if_needed()：未加密文件原样返回（零额外 IO 开销的试探）；
解密成功返回写到 output_root/decrypted/{task_id}/ 的明文副本路径（保持原扩展名，
下游引擎与路由对扩展名敏感）；无法处理时抛 DocDecryptError，文案为友好中文，
绝不透出底层库的原始异常文本。
"""

import io
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Union

try:
    import pikepdf

    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

try:
    import msoffcrypto

    MSOFFCRYPTO_AVAILABLE = True
except ImportError:
    MSOFFCRYPTO_AVAILABLE = False

try:
    import pyzipper

    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False

OFFICE_EXTENSIONS = frozenset({".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"})


class DocDecryptError(Exception):
    """文档解密失败（密码缺失 / 密码错误 / 文件损坏），文案面向终端用户"""


def decrypted_dir(output_root: Union[str, Path], task_id: str) -> Path:
    """解密产物目录：output_root/decrypted/{task_id}/"""
    return Path(output_root) / "decrypted" / task_id


def cleanup_decrypted(dest_dir: Union[str, Path]) -> None:
    """任务结束后清理解密产物；任何失败都不抛出，由调用方在 finally 中使用"""
    shutil.rmtree(dest_dir, ignore_errors=True)


def decrypt_if_needed(
    file_path: str,
    ext: str,
    password: Optional[str],
    dest_dir: Union[str, Path],
) -> str:
    """返回（可能解密后的）文件路径。未加密原样返回；解密成功返回明文副本路径。

    Raises:
        DocDecryptError: 文件已加密但未提供密码，或密码错误 / 文件损坏
    """
    ext = (ext or Path(file_path).suffix).lower()
    if ext == ".pdf":
        return _decrypt_pdf(file_path, password, dest_dir)
    if ext in OFFICE_EXTENSIONS:
        return _decrypt_office(file_path, password, dest_dir)
    if ext == ".zip":
        return _decrypt_zip(file_path, password, dest_dir)
    return file_path


def _target_path(dest_dir: Union[str, Path], source_path: Union[str, Path]) -> Path:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    return dest / Path(source_path).name


def _decrypt_pdf(file_path: str, password: Optional[str], dest_dir) -> str:
    if not PIKEPDF_AVAILABLE:
        # 轻量依赖缺失（如 CI 最小环境）：探测 /Encrypt 标记，加密文档明确报错，其余放行给下游
        try:
            if b"/Encrypt" in Path(file_path).read_bytes():
                raise DocDecryptError("服务器缺少 PDF 解密组件（pikepdf），无法处理加密文档")
        except DocDecryptError:
            raise
        except OSError:
            pass
        return file_path

    try:
        pdf = pikepdf.open(file_path)
    except pikepdf.PasswordError:
        # 需要打开密码
        if not password:
            raise DocDecryptError("文档已加密，请在提交任务时提供打开密码")
        try:
            pdf = pikepdf.open(file_path, password=password)
        except pikepdf.PasswordError:
            raise DocDecryptError("PDF 密码错误或文档已损坏")
        except Exception:
            raise DocDecryptError("PDF 解密失败，文档可能已损坏")
    except DocDecryptError:
        raise
    except Exception:
        raise DocDecryptError("PDF 文件无法打开，可能已损坏或格式不受支持")

    with pdf:
        if not pdf.is_encrypted:
            # 完全未加密：原样走流水线
            return file_path
        # 空密码 / 仅所有者密码：可直接打开，另存明文副本移除权限限制
        target = _target_path(dest_dir, file_path)
        try:
            pdf.save(target)
        except Exception:
            raise DocDecryptError("PDF 解密副本写出失败")
        return str(target)


def _decrypt_office(file_path: str, password: Optional[str], dest_dir) -> str:
    if not MSOFFCRYPTO_AVAILABLE:
        raise DocDecryptError("服务器缺少 Office 解密组件（msoffcrypto-tool），无法处理加密文档")

    # 先试探是否加密；无法按 Office 加密容器解析（如伪装扩展名）交给下游引擎自行报错
    try:
        with open(file_path, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            encrypted = office_file.is_encrypted()
    except DocDecryptError:
        raise
    except Exception:
        return file_path

    if not encrypted:
        return file_path

    if not password:
        raise DocDecryptError("文档已加密，请在提交任务时提供打开密码")

    try:
        with open(file_path, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            office_file.load_key(password=password)
            buf = io.BytesIO()
            office_file.decrypt(buf)
    except DocDecryptError:
        raise
    except Exception:
        # InvalidKeyError 等一律改写为友好文案，不透出原始异常
        raise DocDecryptError("文档密码错误或文件已损坏")

    target = _target_path(dest_dir, file_path)
    target.write_bytes(buf.getvalue())
    return str(target)


def _decrypt_zip(file_path: str, password: Optional[str], dest_dir) -> str:
    if not zipfile.is_zipfile(file_path):
        # 不是合法 zip（伪装扩展名等），交给下游报错
        return file_path

    with zipfile.ZipFile(file_path) as zf:
        infos = zf.infolist()

    # 加密条目的通用标志位（ZipCrypto 与 AES 均置位）
    if not any(info.flag_bits & 0x1 for info in infos):
        return file_path

    if not PYZIPPER_AVAILABLE:
        raise DocDecryptError("服务器缺少 ZIP 解密组件（pyzipper），无法处理加密压缩包")

    if not password:
        raise DocDecryptError("压缩包已加密，请在提交任务时提供密码")

    target = _target_path(dest_dir, file_path)
    try:
        with pyzipper.AESZipFile(file_path) as zf:
            zf.pwd = password.encode("utf-8")
            entries = [(info.filename, zf.read(info)) for info in zf.infolist() if not info.is_dir()]
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
            for name, data in entries:
                out.writestr(name, data)
    except DocDecryptError:
        raise
    except Exception:
        raise DocDecryptError("压缩包密码错误或文件已损坏")
    return str(target)
