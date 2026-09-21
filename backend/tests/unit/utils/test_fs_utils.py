"""文件搬运与数据库落盘位置的安全约束

对应线上故障：
  - issue #84：结果文件从 /tmp 搬到挂载出来的输出目录时，NFS/CIFS 上 copystat
    抛 PermissionError(EPERM)，导致整个解析任务失败。
  - task_db 注释中「数据库需放在本地盘上」此前无任何强制手段，SQLite WAL 在
    网络文件系统上会静默损坏。
"""

import pytest

from utils import fs_utils
from utils.fs_utils import assert_local_filesystem, copy_file, move_file


def _eperm(*_args, **_kwargs):
    """模拟 NFS/CIFS 上 utime 返回的 EPERM"""
    raise PermissionError(1, "Operation not permitted")


class TestCopyFile:
    def test_copies_content(self, tmp_path):
        src = tmp_path / "a.txt"
        src.write_text("hello", encoding="utf-8")
        dst = tmp_path / "b.txt"

        copy_file(src, dst)

        assert dst.read_text(encoding="utf-8") == "hello"

    def test_survives_metadata_failure(self, tmp_path, monkeypatch):
        """copystat 失败不应让拷贝失败 —— 时间戳对业务无意义"""
        src = tmp_path / "a.txt"
        src.write_text("hello", encoding="utf-8")
        dst = tmp_path / "b.txt"
        monkeypatch.setattr(fs_utils.shutil, "copystat", _eperm)

        copy_file(src, dst)

        assert dst.read_text(encoding="utf-8") == "hello"

    def test_real_errors_still_raise(self, tmp_path):
        """内容拷贝失败必须照常抛错，不能被降级逻辑吞掉"""
        with pytest.raises(FileNotFoundError):
            copy_file(tmp_path / "missing.txt", tmp_path / "out.txt")


class TestMoveFile:
    def test_cross_device_move_survives_metadata_failure(self, tmp_path, monkeypatch):
        """/tmp 到挂载目录是跨设备移动，shutil.move 内部会走拷贝 + copystat"""
        src = tmp_path / "a.txt"
        src.write_text("moved", encoding="utf-8")
        dst = tmp_path / "b.txt"

        def _cross_device(*_args, **_kwargs):
            raise OSError(18, "Invalid cross-device link")

        monkeypatch.setattr(fs_utils.shutil, "copystat", _eperm)
        monkeypatch.setattr(fs_utils.os, "rename", _cross_device)

        result = move_file(src, dst)

        assert result.read_text(encoding="utf-8") == "moved"
        assert not src.exists()


class TestDatabaseFilesystemGuard:
    @pytest.mark.parametrize("fs_type", ["nfs", "nfs4", "cifs", "fuse.sshfs"])
    def test_rejects_network_filesystem(self, tmp_path, monkeypatch, fs_type):
        monkeypatch.setattr(fs_utils, "detect_filesystem_type", lambda _p: fs_type)
        monkeypatch.delenv("TIANSHU_ALLOW_NETWORK_DB", raising=False)

        with pytest.raises(RuntimeError, match="网络文件系统"):
            assert_local_filesystem(tmp_path / "db" / "tianshu.db")

    def test_network_filesystem_can_be_overridden(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fs_utils, "detect_filesystem_type", lambda _p: "nfs")
        monkeypatch.setenv("TIANSHU_ALLOW_NETWORK_DB", "true")

        assert_local_filesystem(tmp_path / "db" / "tianshu.db")

    @pytest.mark.parametrize("fs_type", ["9p", "virtiofs", "drvfs"])
    def test_shared_filesystem_only_warns(self, tmp_path, monkeypatch, fs_type):
        """Docker Desktop 等宿主机共享目录：本机开发常见，不应拦截"""
        monkeypatch.setattr(fs_utils, "detect_filesystem_type", lambda _p: fs_type)

        assert_local_filesystem(tmp_path / "db" / "tianshu.db")

    @pytest.mark.parametrize("fs_type", ["ext4", "xfs", "btrfs", "overlay", ""])
    def test_allows_local_filesystem(self, tmp_path, monkeypatch, fs_type):
        monkeypatch.setattr(fs_utils, "detect_filesystem_type", lambda _p: fs_type)

        assert_local_filesystem(tmp_path / "db" / "tianshu.db")
