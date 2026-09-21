"""
文件搬运工具：拷贝内容成功即算成功，元数据尽力而为

背景：
    解析结果从容器内临时目录（/tmp）搬到挂载出来的输出目录时，宿主机侧可能是
    NFS / CIFS / 虚拟机共享目录。这类文件系统对「修改文件元数据」的支持并不完整：
    内容能正常写入，但 utime / chmod / xattr 会返回 EPERM（NFS 的 root_squash、
    NFSv4 idmap 不匹配、CIFS 由 mount 参数伪造属主等都会导致这一结果）。

    shutil.copy2 / shutil.move 默认会调用 copystat 同步时间戳与权限，一旦失败
    就会抛 PermissionError，让整个解析任务失败——而这些元数据对解析结果、前端
    展示、任务状态没有任何影响。

因此统一走这里的两个函数：内容拷贝失败才算失败，元数据拷贝失败只记 debug 日志。
"""

import os
import shutil
from pathlib import Path

from loguru import logger


def copy_file(src, dst):
    """拷贝文件内容；时间戳/权限等元数据尽力而为，失败不影响主流程

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        Path: 目标文件路径
    """
    shutil.copyfile(src, dst)
    try:
        shutil.copystat(src, dst)
    except OSError as e:
        # NFS/CIFS 等文件系统不支持修改元数据，内容已拷贝成功，忽略即可
        logger.debug(f"跳过元数据拷贝 {dst}: {e}")
    return Path(dst)


def move_file(src, dst):
    """移动文件；跨设备移动时退化为「拷贝内容 + 删除源文件」

    shutil.move 在跨文件系统时内部使用 copy2，同样会因元数据拷贝失败而抛错。
    /tmp 与挂载出来的输出目录通常不在同一设备上，因此必须显式指定 copy_function。

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        Path: 目标文件路径
    """
    return Path(shutil.move(str(src), str(dst), copy_function=copy_file))


# ----------------------------------------------------------------------------
# 数据库所在文件系统检测
#
# SQLite 的 WAL 模式依赖 POSIX 建议锁（flock/fcntl）语义。NFS / CIFS 上这套语义
# 不可靠（NFS 的锁需要 lockd/NLM，网络抖动或 root_squash 都会破坏它），后果不是
# 报错而是**静默的数据库损坏** —— 而 auth_db 与 task_db 共用同一个文件，损坏意味着
# 任务表和用户表、API Key 一起丢失。
#
# task_db.py 的注释早就写了「数据库需放在本地盘上」，但此前没有任何一处执行这条
# 约束。这里把它变成启动时的硬检查。
# ----------------------------------------------------------------------------

# 明确不可用：锁语义不可靠，必须拒绝启动
NETWORK_FILESYSTEMS = {
    "nfs",
    "nfs4",
    "cifs",
    "smb2",
    "smb3",
    "smbfs",
    "afs",
    "ceph",
    "glusterfs",
    "lustre",
    "davfs",
    "fuse.sshfs",
    "fuse.rclone",
    "fuse.s3fs",
}

# 宿主机共享目录（Docker Desktop / 虚拟机）：本机开发常见，锁语义好于网络盘但仍非最佳，
# 仅告警不拦截
SHARED_FILESYSTEMS = {"9p", "virtiofs", "drvfs", "vboxsf", "vmhgfs"}


def detect_filesystem_type(path):
    """返回 path 所在挂载点的文件系统类型（Linux 下解析 /proc/self/mounts）

    Args:
        path: 待检测路径，不存在时逐级向上找到最近的已存在目录

    Returns:
        str: 文件系统类型；无法判定时返回空字符串
    """
    mounts = Path("/proc/self/mounts")
    if not mounts.exists():
        # 非 Linux（如 macOS 原生部署 / Windows）无此接口，跳过检测
        return ""

    target = Path(path).resolve()
    while not target.exists() and target != target.parent:
        target = target.parent

    best_mount = ""
    best_type = ""
    try:
        for line in mounts.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = line.split()
            if len(fields) < 3:
                continue
            mount_point, fs_type = fields[1], fields[2]
            # /proc/mounts 中空格等字符以八进制转义（\040）书写
            mount_point = mount_point.replace("\040", " ")
            try:
                mount_path = Path(mount_point)
            except (ValueError, OSError):
                continue
            # 取匹配到的最长挂载点（最具体的那个）
            if (target == mount_path or mount_path in target.parents) and len(mount_point) >= len(best_mount):
                best_mount = mount_point
                best_type = fs_type
    except OSError as e:
        logger.debug(f"读取 /proc/self/mounts 失败: {e}")
        return ""

    return best_type


def assert_local_filesystem(db_path):
    """校验 SQLite 数据库不在网络文件系统上，否则拒绝启动

    设置环境变量 TIANSHU_ALLOW_NETWORK_DB=true 可跳过（仅用于明确知道风险的场景）。

    Args:
        db_path: 数据库文件路径

    Raises:
        RuntimeError: 数据库位于 NFS/CIFS 等网络文件系统上
    """
    fs_type = detect_filesystem_type(Path(db_path).parent)
    if not fs_type:
        return

    if fs_type in NETWORK_FILESYSTEMS:
        if os.getenv("TIANSHU_ALLOW_NETWORK_DB", "").lower() in ("1", "true", "yes"):
            logger.warning(
                f"⚠️  数据库位于网络文件系统 ({fs_type}) 上：{db_path}\n"
                f"    已由 TIANSHU_ALLOW_NETWORK_DB 跳过检查，SQLite WAL 在此类文件系统上"
                f"可能静默损坏数据，请自行承担风险。"
            )
            return
        raise RuntimeError(
            f"数据库不能放在网络文件系统上（当前: {fs_type}，路径: {db_path}）。\n"
            f"SQLite 的 WAL 模式依赖 POSIX 文件锁，NFS/CIFS 上锁语义不可靠，"
            f"会导致数据库静默损坏（任务数据与用户/API Key 共用同一文件）。\n"
            f"解决方式：把 DATABASE_PATH 指向本地磁盘目录（输出目录 data/output 仍可放网络盘），\n"
            f"例如宿主机 .env 中设置 DATABASE_PATH=/var/lib/tianshu/db/mineru_tianshu.db 并挂载本地盘。\n"
            f"明确知晓风险时可设置 TIANSHU_ALLOW_NETWORK_DB=true 跳过此检查。"
        )

    if fs_type in SHARED_FILESYSTEMS:
        logger.warning(
            f"⚠️  数据库位于宿主机共享目录 ({fs_type}): {db_path}\n"
            f"    本机开发可用，生产部署建议放在容器可直接访问的本地磁盘上。"
        )
