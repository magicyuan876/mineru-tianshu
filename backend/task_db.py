"""
MinerU Tianshu - SQLite Task Database Manager
天枢任务数据库管理器

负责任务的持久化存储、状态管理和原子性操作

架构说明 (Hybrid Queue):
    - SQLite: 任务元数据存储、历史记录、结果管理
    - Redis (可选): 高性能任务队列、优先级调度
    - 当 Redis 可用时，队列操作由 Redis 处理
    - 当 Redis 不可用时，自动回退到 SQLite

更新日志:
    - [新增] data 字段支持，用于存储 json_content 和 pdf_path 等扩展元数据
    - [修复] clear_failed_tasks 增加物理文件删除逻辑
"""

import sqlite3
import json
import uuid
import shutil
import os
from contextlib import contextmanager
from typing import Optional, List, Dict
from pathlib import Path
from loguru import logger

from utils import assert_local_filesystem

# 导入 Redis 队列（可选）
try:
    from redis_queue import get_redis_queue

    REDIS_QUEUE_AVAILABLE = True
except ImportError:
    REDIS_QUEUE_AVAILABLE = False

    def get_redis_queue():
        return None


def _resolve_output_dir() -> Path:
    """解析输出根目录（与 api_server / worker 使用同一环境变量来源）"""
    env = os.getenv("OUTPUT_PATH")
    if env:
        return Path(env).resolve()
    return (Path(__file__).parent.parent / "data" / "output").resolve()


def _resolve_upload_dir() -> Path:
    """解析上传根目录（与 api_server 使用同一环境变量来源）"""
    env = os.getenv("UPLOAD_PATH")
    if env:
        return Path(env).resolve()
    return (Path(__file__).parent.parent / "input").resolve()


class TaskDB:
    """任务数据库管理类"""

    def __init__(self, db_path=None):
        # 导入所需模块
        from pathlib import Path

        # 优先使用传入的路径，其次使用环境变量，最后使用默认路径
        if db_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            default_db = project_root / "data" / "db" / "mineru_tianshu.db"
            db_path = os.getenv("DATABASE_PATH", str(default_db))
            # 确保父目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            # 确保使用绝对路径
            db_path = str(Path(db_path).resolve())
        else:
            # 确保使用绝对路径
            db_path = str(Path(db_path).resolve())

        # 确保 db_path 是绝对路径字符串
        self.db_path = str(Path(db_path).resolve())

        # WAL 依赖 POSIX 文件锁，NFS/CIFS 上会静默损坏数据库，启动时直接拦截
        assert_local_filesystem(self.db_path)

        self._init_db()

    def _get_conn(self):
        """获取数据库连接（每次创建新连接，避免 pickle 问题）

        并发安全说明：
            - 使用 check_same_thread=False 是安全的，因为：
              1. 每次调用都创建新连接，不跨线程共享
              2. 连接使用完立即关闭（在 get_cursor 上下文管理器中）
              3. 不使用连接池，避免线程间共享同一连接
            - timeout=30.0 防止死锁，如果锁等待超过30秒会抛出异常

        WAL 说明：
            默认的 rollback journal 模式下，一次写会独占整个数据库文件，连读也被阻塞。
            worker 持续写任务状态时，API 侧所有查询都会排队等锁 —— 而这些查询是在
            事件循环里同步执行的，一旦等锁就会冻结整个 API 服务。
            WAL 让读写互不阻塞，是本项目并发模型下的必需项。

            journal_mode 是持久化在数据库文件里的属性，设置一次即长期生效，
            每次连接重复设置无副作用。注意 WAL 不支持网络文件系统（NFS/CIFS），
            数据库需放在本地盘上。
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_cursor(self):
        """上下文管理器，自动提交和错误处理"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()  # 关闭连接

    def _init_db(self):
        """初始化数据库表"""
        with self.get_cursor() as cursor:
            # 创建表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    backend TEXT DEFAULT 'pipeline',
                    options TEXT,
                    result_path TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    worker_id TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)

            # 创建基础索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_id ON tasks(worker_id)")

            # 迁移：添加 parent_task_id 等字段（如果不存在）
            try:
                cursor.execute("SELECT parent_task_id FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                # 字段不存在，添加新字段
                logger.info("📊 Migrating database schema: adding parent-child task support")
                cursor.execute("ALTER TABLE tasks ADD COLUMN parent_task_id TEXT")
                cursor.execute("ALTER TABLE tasks ADD COLUMN is_parent INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE tasks ADD COLUMN child_count INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE tasks ADD COLUMN child_completed INTEGER DEFAULT 0")
                logger.info("✅ Parent-child task fields added")

            # 创建主子任务索引（字段存在后才创建）
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_task ON tasks(parent_task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_is_parent ON tasks(is_parent)")
            # 任务列表默认只列顶层任务并按时间倒序分页：没有这个复合索引时 SQLite 会先取出全部顶层任务
            # 再排序，而每行的 data 列里是整份 Markdown / 版面 JSON，大库上列表接口会直接卡死
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_created ON tasks(parent_task_id, created_at)")

            # 迁移：添加 user_id 字段（如果不存在）
            try:
                cursor.execute("SELECT user_id FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("📊 Migrating database schema: adding user_id field")
                cursor.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT")
                logger.info("✅ user_id field added")

            # 迁移：添加 data 字段（如果不存在）- 用于存储 pdf_path, json_content 等
            try:
                cursor.execute("SELECT data FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("📊 Migrating database schema: adding data field")
                cursor.execute("ALTER TABLE tasks ADD COLUMN data TEXT")
                logger.info("✅ data field added")

            # 迁移：添加 api_key_id 字段（记录提交任务所用的 API Key，供 Key 级 webhook 路由）
            try:
                cursor.execute("SELECT api_key_id FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("📊 Migrating database schema: adding api_key_id field")
                cursor.execute("ALTER TABLE tasks ADD COLUMN api_key_id TEXT")
                logger.info("✅ api_key_id field added")

            # 迁移：添加 stale_reset_count 字段（超时自动重置次数，与手动重试的 retry_count 分开计数）
            try:
                cursor.execute("SELECT stale_reset_count FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("📊 Migrating database schema: adding stale_reset_count field")
                cursor.execute("ALTER TABLE tasks ADD COLUMN stale_reset_count INTEGER DEFAULT 0")
                logger.info("✅ stale_reset_count field added")

    def create_task(
        self,
        file_name: str,
        file_path: str,
        backend: str = "pipeline",
        options: dict = None,
        priority: int = 0,
        user_id: str = None,
        api_key_id: str = None,
    ) -> str:
        """
        创建新任务
        """
        task_id = str(uuid.uuid4())
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (task_id, file_name, file_path, backend, options, priority, user_id, api_key_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (task_id, file_name, file_path, backend, json.dumps(options or {}), priority, user_id, api_key_id),
            )

        # 入队到 Redis（如果可用）
        self._enqueue_to_redis(
            task_id,
            priority,
            {
                "file_name": file_name,
                "backend": backend,
            },
        )

        return task_id

    def _enqueue_to_redis(self, task_id: str, priority: int, task_data: dict = None) -> bool:
        """将任务加入 Redis 队列"""
        if not REDIS_QUEUE_AVAILABLE:
            return False

        redis_queue = get_redis_queue()
        if redis_queue:
            try:
                return redis_queue.enqueue(task_id, priority, task_data)
            except Exception as e:
                logger.warning(f"⚠️  Failed to enqueue to Redis, SQLite fallback active: {e}")
        return False

    def sync_pending_to_redis(self) -> int:
        """把 SQLite 里的 pending 任务补回 Redis 队列，返回补入的数量

        Redis 只是加速层，SQLite 才是真相源。二者会在这些情况下发散：
          - Redis 重启且数据卷被清空 / AOF 损坏 / key 被淘汰
          - 入队时 Redis 短暂不可用（create 只记 warning 就继续）
          - worker 在 BZPOPMIN 之后、SQLite 认领之前被杀

        发散不会丢任务（get_next_task 找不到 Redis 任务时会回落到 SQLite 抢锁路径），
        但那批任务从此绕开 Redis，恰好退化成我们要避免的锁竞争。这里做定期对账。

        只补差集，不整体重入：enqueue 的 score 含时间戳，重复 ZADD 会刷新 score，
        把同优先级下的 FIFO 顺序打乱。
        """
        if not REDIS_QUEUE_AVAILABLE:
            return 0

        redis_queue = get_redis_queue()
        if not redis_queue:
            return 0

        queued = redis_queue.get_queued_ids()
        if queued is None:
            # 读不到队列时宁可不动，也好过误判成空队列后全量重入
            return 0

        with self.get_cursor() as cursor:
            cursor.execute("SELECT task_id, priority, file_name, backend FROM tasks WHERE status = 'pending'")
            pending = cursor.fetchall()

        missing = [row for row in pending if row["task_id"] not in queued]

        # pending 的任务不可能同时还被某个 worker 持有，清掉 processing 里的残留
        redis_queue.prune_processing([row["task_id"] for row in pending])

        for row in missing:
            self._enqueue_to_redis(
                row["task_id"], row["priority"], {"file_name": row["file_name"], "backend": row["backend"]}
            )

        if missing:
            logger.warning(f"🔄 Re-enqueued {len(missing)} pending task(s) missing from the Redis queue")
        return len(missing)

    def get_next_task(self, worker_id: str, max_retries: int = 3) -> Optional[Dict]:
        """
        获取下一个待处理任务（原子操作，防止并发冲突）
        """
        from loguru import logger

        # 尝试使用 Redis 队列（如果可用）
        task = self._get_next_task_redis(worker_id)
        if task is not None:
            return task

        # Redis 不可用或出错，回退到 SQLite
        for attempt in range(max_retries):
            try:
                with self.get_cursor() as cursor:
                    # 使用事务确保原子性
                    cursor.execute("BEGIN IMMEDIATE")

                    # 按优先级和创建时间获取任务
                    cursor.execute("""
                        SELECT * FROM tasks
                        WHERE status = 'pending'
                        ORDER BY priority DESC, created_at ASC
                        LIMIT 1
                    """)

                    task = cursor.fetchone()
                    if task:
                        task_id = task["task_id"]
                        # 立即标记为 processing，并确保状态仍是 pending
                        cursor.execute(
                            """
                            UPDATE tasks
                            SET status = 'processing',
                                started_at = CURRENT_TIMESTAMP,
                                worker_id = ?
                            WHERE task_id = ? AND status = 'pending'
                        """,
                            (worker_id, task_id),
                        )

                        # 检查是否更新成功（防止被其他 worker 抢走）
                        if cursor.rowcount == 0:
                            # 任务被其他进程抢走了，立即重试
                            if attempt == 0:  # 只在第一次尝试时记录日志
                                logger.debug(f"Task {task_id} was grabbed by another worker, retrying...")
                            continue

                        return dict(task)
                    else:
                        # 队列中没有待处理任务，返回 None
                        if attempt == 0:
                            # 检查是否有 pending 任务（用于诊断）
                            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
                            pending_count = cursor.fetchone()["count"]
                            if pending_count > 0:
                                logger.warning(
                                    f"⚠️  Found {pending_count} pending tasks but failed to grab one "
                                    f"(attempt {attempt + 1}/{max_retries})"
                                )
                        return None

            except Exception as e:
                logger.error(f"❌ Error in get_next_task (attempt {attempt + 1}/{max_retries}): {e}")
                logger.exception(e)
                if attempt == max_retries - 1:
                    return None
                # 等待一小段时间后重试
                import time

                time.sleep(0.1)

        # 重试次数用尽，仍未获取到任务（高并发场景）
        logger.warning(f"⚠️  Failed to get task after {max_retries} attempts")
        return None

    def _get_next_task_redis(self, worker_id: str) -> Optional[Dict]:
        """从 Redis 队列获取下一个任务"""
        if not REDIS_QUEUE_AVAILABLE:
            return None

        redis_queue = get_redis_queue()
        if not redis_queue:
            return None

        try:
            # 从 Redis 获取任务 ID（阻塞式，1秒超时）
            task_id = redis_queue.dequeue(worker_id, timeout=1.0)
            if not task_id:
                return None

            # 从 SQLite 获取完整任务数据
            with self.get_cursor() as cursor:
                cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                task = cursor.fetchone()

                if not task:
                    logger.error(f"❌ Task {task_id} found in Redis but not in SQLite")
                    redis_queue.fail(task_id, worker_id, requeue=False)
                    return None

                # 更新 SQLite 中的任务状态
                cursor.execute(
                    """
                    UPDATE tasks
                    SET status = 'processing',
                        started_at = CURRENT_TIMESTAMP,
                        worker_id = ?
                    WHERE task_id = ? AND status = 'pending'
                    """,
                    (worker_id, task_id),
                )

                if cursor.rowcount == 0:
                    logger.warning(f"⚠️  Task {task_id} status changed, skipping")
                    redis_queue.fail(task_id, worker_id, requeue=False)
                    return None

                logger.info(f"📤 [Redis] Task {task_id} claimed by worker {worker_id}")
                return dict(task)

        except Exception as e:
            logger.error(f"❌ Redis dequeue failed, falling back to SQLite: {e}")
            return None

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result_path: str = None,
        error_message: str = None,
        worker_id: str = None,
        data: str = None,  # 新增：接收扩展数据（JSON字符串）
    ):
        """
        更新任务状态
        """
        with self.get_cursor() as cursor:
            success = False

            # 根据不同状态使用预定义的 SQL 模板
            if status == "completed":
                # 修复：写入 data 字段
                if worker_id:
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            result_path = ?,
                            data = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                        AND worker_id = ?
                    """
                    cursor.execute(sql, (status, result_path, data, task_id, worker_id))
                else:
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            result_path = ?,
                            data = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                    """
                    cursor.execute(sql, (status, result_path, data, task_id))

                success = cursor.rowcount > 0

            elif status == "failed":
                if worker_id:
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                        AND worker_id = ?
                    """
                    cursor.execute(sql, (status, error_message, task_id, worker_id))
                else:
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                    """
                    cursor.execute(sql, (status, error_message, task_id))

                success = cursor.rowcount > 0

            elif status == "cancelled":
                sql = """
                    UPDATE tasks
                    SET status = ?,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """
                cursor.execute(sql, (status, task_id))
                success = cursor.rowcount > 0

            elif status == "pending":
                sql = """
                    UPDATE tasks
                    SET status = ?,
                        worker_id = NULL,
                        started_at = NULL
                    WHERE task_id = ?
                """
                cursor.execute(sql, (status, task_id))
                success = cursor.rowcount > 0

            else:
                sql = """
                    UPDATE tasks
                    SET status = ?
                    WHERE task_id = ?
                """
                cursor.execute(sql, (status, task_id))
                success = cursor.rowcount > 0

            # 调试日志（仅在失败时）
            if not success and status in ["completed", "failed"]:
                from loguru import logger

                logger.debug(f"Status update failed: task_id={task_id}, status={status}, " f"worker_id={worker_id}")

            # 通知 Redis 任务完成/失败（清理 processing set）
            if success and status in ["completed", "failed"]:
                self._notify_redis_task_done(task_id, worker_id or "", status)

            return success

    def _notify_redis_task_done(self, task_id: str, worker_id: str, status: str):
        """通知 Redis 任务已完成/失败"""
        if not REDIS_QUEUE_AVAILABLE:
            return

        redis_queue = get_redis_queue()
        if redis_queue:
            try:
                if status == "completed":
                    redis_queue.complete(task_id, worker_id)
                else:
                    redis_queue.fail(task_id, worker_id, requeue=False)
            except Exception as e:
                logger.warning(f"⚠️  Failed to notify Redis about task {task_id}: {e}")

    def get_task(self, task_id: str) -> Optional[Dict]:
        """查询任务详情"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            return dict(task) if task else None

    def ping(self) -> bool:
        """数据库探活，供未鉴权的 /health 使用：只验证连接可用，不返回任何内部数据"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT 1")
        return True

    def get_queue_stats(self) -> Dict[str, int]:
        """获取队列统计信息"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """)
            stats = {row["status"]: row["count"] for row in cursor.fetchall()}

        # 添加 Redis 队列统计（如果可用）
        if REDIS_QUEUE_AVAILABLE:
            redis_queue = get_redis_queue()
            if redis_queue:
                try:
                    redis_stats = redis_queue.get_stats()
                    stats["_redis_enabled"] = True
                    stats["_redis_pending"] = redis_stats.get("pending", 0)
                    stats["_redis_processing"] = redis_stats.get("processing", 0)
                except Exception as e:
                    stats["_redis_enabled"] = False
                    stats["_redis_error"] = str(e)
            else:
                stats["_redis_enabled"] = False
        else:
            stats["_redis_enabled"] = False

        return stats

    def get_tasks_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """根据状态获取任务列表"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM tasks
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (status, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # 核心修复：物理删除文件逻辑
    # -------------------------------------------------------------------------
    def delete_task_files(self, task_row, include_source: bool = True):
        """安全删除任务的源文件和结果目录（带目录逃逸防护）

        Args:
            task_row: 任务记录（需包含 task_id / file_path / result_path）
            include_source: 是否删除上传的源文件（重试/清缓存场景传 False 保留源文件）
        """
        task_id = task_row["task_id"]

        # 1. 删除上传的源文件
        if include_source and task_row["file_path"]:
            try:
                fp = Path(task_row["file_path"]).resolve()
                if fp.is_relative_to(_resolve_upload_dir()):
                    if fp.is_file():
                        fp.unlink()
                        logger.debug(f"Deleted source file for task {task_id}")
                else:
                    logger.warning(f"⚠️  Skip deleting source file outside upload dir for task {task_id}: {fp}")
            except Exception as e:
                logger.warning(f"Failed to delete source file for task {task_id}: {e}")

        # 2. 删除结果目录
        if task_row["result_path"] and task_row["result_path"] != "CLEARED":
            try:
                rp = Path(task_row["result_path"]).resolve()
                if rp.is_relative_to(_resolve_output_dir()):
                    if rp.is_dir():
                        shutil.rmtree(rp)
                        logger.debug(f"Deleted result dir for task {task_id}")
                else:
                    logger.warning(f"⚠️  Skip deleting result dir outside output dir for task {task_id}: {rp}")
            except Exception as e:
                logger.warning(f"Failed to delete result dir for task {task_id}: {e}")

    # 兼容旧名，避免破坏既有调用
    _delete_task_files = delete_task_files

    def get_task_by_output_path(self, rel_path: str) -> Optional[Dict]:
        """按输出相对路径反查任务（URL 首段即结果目录名，为 Worker 写入的 result_path 的 basename）"""
        first_segment = rel_path.replace("\\", "/").lstrip("/").split("/")[0]
        if not first_segment:
            return None
        candidate = str((_resolve_output_dir() / first_segment).resolve())
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE result_path = ?", (candidate,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            # 兜底：历史记录可能存在路径分隔符差异
            cursor.execute("SELECT * FROM tasks WHERE result_path LIKE ?", (f"%/{first_segment}",))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_task_by_upload_path(self, rel_path: str) -> Optional[Dict]:
        """按上传文件名精确反查任务（upload 目录内文件名唯一，不接受子目录）"""
        name = rel_path.replace("\\", "/").lstrip("/")
        if not name or "/" in name:
            return None
        candidate = str((_resolve_upload_dir() / name).resolve())
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE file_path = ?", (candidate,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def cleanup_old_task_records(self, days: int = 30):
        """清理旧任务"""
        with self.get_cursor() as cursor:
            # 先查询要删除的任务及其文件路径
            cursor.execute(
                """
                SELECT task_id, file_path, result_path FROM tasks
                WHERE completed_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'failed')
            """,
                (days,),
            )
            old_tasks = cursor.fetchall()

            # 删除所有相关文件
            for task in old_tasks:
                self._delete_task_files(task)

            # 删除数据库记录
            cursor.execute(
                """
                DELETE FROM tasks
                WHERE completed_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'failed')
            """,
                (days,),
            )

            return cursor.rowcount

    def reset_stale_tasks(self, timeout_minutes: int = 60, max_retries: int = 2) -> Dict:
        """处理超时的 processing 任务：未超过自动重试上限的打回 pending，超过的判定失败

        自动重置次数记在 stale_reset_count，与手动重试的 retry_count 分开：
        手动重试会清零该计数，重新获得完整的自动重试额度。

        已拆分出子任务的父任务不参与：父任务在子任务全部完成前一直是 processing，
        started_at 停在拆分时刻，大文件跑几个小时是正常的，不能按超时处理。

        Args:
            timeout_minutes: 超时时间（分钟）
            max_retries: 自动重试上限，0 表示超时即失败

        Returns:
            {"reset_count": 打回 pending 的数量,
             "failed_count": 判定失败的数量,
             "failed_tasks": [{"task_id", "parent_task_id", "error_message"}, ...]}
        """
        max_retries = max(0, int(max_retries))
        requeue = []
        failed_tasks = []

        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT task_id, priority, file_name, backend, parent_task_id,
                       COALESCE(stale_reset_count, 0) AS stale_reset_count
                FROM tasks
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                AND NOT (COALESCE(is_parent, 0) = 1 AND COALESCE(child_count, 0) > 0)
            """,
                (timeout_minutes,),
            )
            stale = [dict(row) for row in cursor.fetchall()]

            # 逐行更新并带上 status = 'processing' 条件：SELECT 之后 worker 可能恰好完成了任务，
            # 不能把刚写入的 completed 覆盖掉
            for row in stale:
                if row["stale_reset_count"] < max_retries:
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status = 'pending',
                            worker_id = NULL,
                            retry_count = retry_count + 1,
                            stale_reset_count = COALESCE(stale_reset_count, 0) + 1
                        WHERE task_id = ? AND status = 'processing'
                    """,
                        (row["task_id"],),
                    )
                    if cursor.rowcount > 0:
                        requeue.append(row)
                else:
                    error_message = (
                        f"任务处理超时：运行超过 {timeout_minutes} 分钟未完成，"
                        f"已自动重试 {row['stale_reset_count']} 次仍未成功"
                    )
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status = 'failed',
                            worker_id = NULL,
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = ?
                        WHERE task_id = ? AND status = 'processing'
                    """,
                        (error_message, row["task_id"]),
                    )
                    if cursor.rowcount > 0:
                        failed_tasks.append(
                            {
                                "task_id": row["task_id"],
                                "parent_task_id": row["parent_task_id"],
                                "error_message": error_message,
                            }
                        )

        # 重置后要重新入队，否则这些任务只能靠 SQLite 抢锁路径被认领
        for row in requeue:
            self._enqueue_to_redis(
                row["task_id"], row["priority"], {"file_name": row["file_name"], "backend": row["backend"]}
            )

        # 子任务失败要连带父任务失败，与 worker 侧失败路径保持一致
        for task in failed_tasks:
            if task["parent_task_id"]:
                self.on_child_task_failed(task["task_id"], task["error_message"])
            logger.error(f"❌ Task {task['task_id']} marked as failed: {task['error_message']}")

        return {"reset_count": len(requeue), "failed_count": len(failed_tasks), "failed_tasks": failed_tasks}

    # -------------------------------------------------------------------------
    # 新增功能：清理失败任务 (包含物理文件删除)
    # -------------------------------------------------------------------------
    def clear_failed_tasks(self) -> int:
        """
        一键清理所有失败的任务
        执行步骤: 1.查询路径 -> 2.删除磁盘文件 -> 3.删除数据库记录

        主子任务按组清理：
        - 失败的顶层任务：连同它的全部子任务一起删除，不留下查不到分片的父任务
        - 父任务已不存在的失败子任务（孤儿）：删除
        - 父任务未失败（处理中 / 已完成 / 已取消）的失败子任务：保留，供排查或单独重试
        """
        with self.get_cursor() as cursor:
            # 1. 待删除行：失败的顶层任务 + 它们的全部子任务 + 失败的孤儿子任务
            cursor.execute(
                """
                SELECT task_id, file_path, result_path FROM tasks
                WHERE (parent_task_id IS NULL AND status = 'failed')
                   OR parent_task_id IN (SELECT task_id FROM tasks WHERE parent_task_id IS NULL AND status = 'failed')
                   OR (status = 'failed' AND parent_task_id IS NOT NULL
                       AND parent_task_id NOT IN (SELECT task_id FROM tasks))
                """
            )
            doomed = cursor.fetchall()

            # 2. 物理删除
            for task in doomed:
                self._delete_task_files(task)

            # 3. 数据库删除
            ids = [task["task_id"] for task in doomed]
            for start in range(0, len(ids), 500):
                batch = ids[start : start + 500]
                cursor.execute(f"DELETE FROM tasks WHERE task_id IN ({','.join('?' * len(batch))})", batch)
            logger.info(f"🧹 Cleared {len(ids)} failed tasks (including subtasks of failed parents)")
            return len(ids)

    # ============================================================================
    # 主子任务支持 (Parent-Child Task Support)
    # ============================================================================

    def create_parent_task(
        self,
        file_name: str,
        file_path: str,
        backend: str = "pipeline",
        options: dict = None,
        priority: int = 0,
        user_id: str = None,
    ) -> str:
        """创建主任务"""
        task_id = str(uuid.uuid4())
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (
                    task_id, file_name, file_path, backend, options,
                    status, priority, user_id, is_parent, child_count
                ) VALUES (?, ?, ?, ?, ?, 'processing', ?, ?, 1, 0)
            """,
                (task_id, file_name, file_path, backend, json.dumps(options or {}), priority, user_id),
            )
        logger.info(f"📋 Created parent task: {task_id}")
        return task_id

    def convert_to_parent_task(self, task_id: str, child_count: int = 0):
        """将普通任务转换为父任务"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET is_parent = 1, child_count = ?, status = 'processing'
                WHERE task_id = ?
                """,
                (child_count, task_id),
            )
        logger.info(f"🔄 Converted task {task_id} to parent task with {child_count} children")

    def create_child_tasks_bulk(
        self,
        parent_task_id: str,
        children: List[Dict],
        backend: str = "pipeline",
        priority: int = 0,
        user_id: str = None,
    ) -> List[str]:
        """批量创建子任务（单事务）

        每个子任务单开一个写事务、并各自更新同一个父任务行的话，PDF 按小页数切片时
        子任务可达上百个，那就是上百个背靠背的写事务 —— 期间 API 侧的查询会反复撞上
        锁等待。这里合并为一个事务：N 次 INSERT + 1 次父计数更新。

        Args:
            parent_task_id: 父任务 ID
            children: [{"file_name": str, "file_path": str, "options": dict}, ...]
            backend / priority / user_id: 所有子任务共用

        Returns:
            按入参顺序返回的子任务 ID 列表
        """
        if not children:
            return []

        task_ids = [str(uuid.uuid4()) for _ in children]

        with self.get_cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO tasks (
                    task_id, parent_task_id, file_name, file_path,
                    backend, options, status, priority, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
                [
                    (
                        task_id,
                        parent_task_id,
                        child["file_name"],
                        child["file_path"],
                        backend,
                        json.dumps(child.get("options") or {}),
                        priority,
                        user_id,
                    )
                    for task_id, child in zip(task_ids, children)
                ],
            )

            # 父任务的子任务计数一次性累加，而不是每个子任务更新一次
            cursor.execute(
                """
                UPDATE tasks
                SET child_count = child_count + ?
                WHERE task_id = ?
            """,
                (len(children), parent_task_id),
            )

        # 入队放在事务提交之后：worker 一旦从 Redis 取到 ID 就会立刻回查 SQLite，
        # 提交前入队会让它查不到行。
        for task_id, child in zip(task_ids, children):
            self._enqueue_to_redis(task_id, priority, {"file_name": child["file_name"], "backend": backend})

        logger.debug(f"📄 Created {len(task_ids)} child tasks in one transaction (parent: {parent_task_id})")
        return task_ids

    def on_child_task_completed(self, child_task_id: str) -> Optional[str]:
        """子任务完成回调"""
        with self.get_cursor() as cursor:
            # 获取父任务ID
            cursor.execute(
                """
                SELECT parent_task_id FROM tasks WHERE task_id = ?
            """,
                (child_task_id,),
            )
            row = cursor.fetchone()

            if not row or not row["parent_task_id"]:
                return None  # 不是子任务

            parent_task_id = row["parent_task_id"]

            # 按实际已完成的子任务数回写计数，而不是 +1：失败子任务重试后再次完成、
            # 或已完成子任务被重跑时，自增会重复计数
            completed = self._count_completed_children(cursor, parent_task_id)

            # 带条件更新：两个子任务几乎同时完成时，只有真正把计数推进到新值的那一方拿到 rowcount，
            # 避免双方都看到"已全部完成"而重复合并
            cursor.execute(
                "UPDATE tasks SET child_completed = ? WHERE task_id = ? AND child_completed <> ?",
                (completed, parent_task_id, completed),
            )
            advanced = cursor.rowcount > 0

            cursor.execute(
                "SELECT child_count, status, file_name FROM tasks WHERE task_id = ?",
                (parent_task_id,),
            )
            parent = cursor.fetchone()

            if not parent:
                return None

            # 父任务已失败 / 已取消时不合并：等用户重试父任务后，由最后完成的子任务触发
            if advanced and completed >= parent["child_count"] and parent["status"] == "processing":
                logger.info(
                    f"🎉 All subtasks completed for parent task {parent_task_id} "
                    f"({completed}/{parent['child_count']}) - {parent['file_name']}"
                )
                return parent_task_id

            logger.info(f"⏳ Subtask progress: {completed}/{parent['child_count']} for parent task {parent_task_id}")

        return None

    @staticmethod
    def _count_completed_children(cursor, parent_task_id: str) -> int:
        cursor.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE parent_task_id = ? AND status = 'completed'",
            (parent_task_id,),
        )
        return cursor.fetchone()["n"]

    def all_children_completed(self, parent_task_id: str) -> bool:
        """父任务的子任务是否已全部完成（用于父任务被重新拉取时判断是否只差合并）"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT child_count FROM tasks WHERE task_id = ?", (parent_task_id,))
            row = cursor.fetchone()
            if not row or not row["child_count"]:
                return False
            return self._count_completed_children(cursor, parent_task_id) >= row["child_count"]

    def on_child_task_failed(self, child_task_id: str, error_message: str):
        """子任务失败回调"""
        with self.get_cursor() as cursor:
            # 获取父任务ID
            cursor.execute(
                """
                SELECT parent_task_id FROM tasks WHERE task_id = ?
            """,
                (child_task_id,),
            )
            row = cursor.fetchone()

            if not row or not row["parent_task_id"]:
                return  # 不是子任务

            parent_task_id = row["parent_task_id"]

            # 标记父任务为失败
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = ?
                WHERE task_id = ?
                AND status = 'processing'
            """,
                (f"Subtask {child_task_id} failed: {error_message}", parent_task_id),
            )

            if cursor.rowcount > 0:
                logger.error(f"❌ Parent task {parent_task_id} marked as failed due to subtask failure")

    def get_task_with_children(self, task_id: str) -> Optional[Dict]:
        """获取任务及其所有子任务"""
        with self.get_cursor() as cursor:
            # 获取主任务
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            parent_row = cursor.fetchone()

            if not parent_row:
                return None

            parent = dict(parent_row)

            # 如果是主任务，获取所有子任务
            if parent.get("is_parent"):
                cursor.execute(
                    """
                    SELECT * FROM tasks
                    WHERE parent_task_id = ?
                    ORDER BY created_at
                """,
                    (task_id,),
                )
                children = [dict(row) for row in cursor.fetchall()]
                parent["children"] = children
            else:
                parent["children"] = []

            return parent

    def get_child_tasks(self, parent_task_id: str) -> List[Dict]:
        """获取父任务的所有子任务"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM tasks
                WHERE parent_task_id = ?
                ORDER BY created_at
            """,
                (parent_task_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_children_stats(self, parent_task_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """批量统计父任务下各状态的子任务数，返回 {parent_id: {"total": n, "completed": n, ...}}"""
        stats: Dict[str, Dict[str, int]] = {}
        if not parent_task_ids:
            return stats
        with self.get_cursor() as cursor:
            for start in range(0, len(parent_task_ids), 500):
                batch = parent_task_ids[start : start + 500]
                cursor.execute(
                    f"""
                    SELECT parent_task_id, status, COUNT(*) AS n FROM tasks
                    WHERE parent_task_id IN ({",".join("?" * len(batch))})
                    GROUP BY parent_task_id, status
                    """,
                    batch,
                )
                for row in cursor.fetchall():
                    entry = stats.setdefault(row["parent_task_id"], {"total": 0})
                    entry[row["status"]] = row["n"]
                    entry["total"] += row["n"]
        return stats

    def delete_task_tree(self, task_row: Dict) -> int:
        """彻底删除任务：父任务连同全部子任务的文件与记录一起删除，返回删除的记录数"""
        children = self.get_child_tasks(task_row["task_id"]) if task_row.get("is_parent") else []
        for child in children:
            self.delete_task_files(child)
        self.delete_task_files(task_row)
        with self.get_cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE parent_task_id = ?", (task_row["task_id"],))
            deleted = cursor.rowcount
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_row["task_id"],))
            return deleted + cursor.rowcount

    # ========================================================================
    # 新增功能：重试、清理、暂停、恢复、清理缓存
    # ========================================================================

    # 父任务重试时需要重跑的子任务状态
    CHILD_RETRY_STATUSES = ("failed", "cancelled")

    @staticmethod
    def _is_split_parent(task: Dict) -> bool:
        return bool(task.get("is_parent")) and (task.get("child_count") or 0) > 0

    def get_children_to_retry(self, parent_task_id: str) -> List[Dict]:
        """父任务重试时会被重跑的子任务（失败 / 已取消），供调用方先清理其旧产物"""
        placeholders = ",".join("?" * len(self.CHILD_RETRY_STATUSES))
        with self.get_cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM tasks WHERE parent_task_id = ? AND status IN ({placeholders})",
                (parent_task_id, *self.CHILD_RETRY_STATUSES),
            )
            return [dict(row) for row in cursor.fetchall()]

    def retry_task(self, task_id: str) -> bool:
        """
        重试任务：将任务状态重置为 pending，清空错误和时间，重试次数 +1

        手动重试同时清零 stale_reset_count，让任务重新获得完整的超时自动重试额度。
        - 已拆分的父任务：转为重跑失败 / 已取消的子任务，父任务回到 processing 等待合并
        - 子任务：父任务若已失败 / 已取消，一并恢复为 processing，否则子任务完成后无法合并
        """
        task = self.get_task(task_id)
        if not task:
            return False
        if self._is_split_parent(task):
            return self._retry_parent_task(task_id)

        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL,
                    worker_id = NULL,
                    retry_count = retry_count + 1,
                    stale_reset_count = 0
                WHERE task_id = ?
                """,
                (task_id,),
            )
            ok = cursor.rowcount > 0
            if ok and task.get("parent_task_id"):
                self._revive_parent(cursor, task["parent_task_id"])

        if ok:
            self._requeue_pending(task_id)
        return ok

    @staticmethod
    def _revive_parent(cursor, parent_task_id: str) -> None:
        """把已失败 / 已取消的父任务恢复为 processing（等待子任务完成后合并）"""
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'processing',
                error_message = NULL,
                completed_at = NULL,
                worker_id = NULL
            WHERE task_id = ? AND status IN ('failed', 'cancelled')
            """,
            (parent_task_id,),
        )

    def _retry_parent_task(self, parent_task_id: str) -> bool:
        """重试已拆分的父任务：重跑失败 / 已取消的子任务，已完成的保留

        子任务已全部完成（通常是合并那一步失败）时，把父任务置为 pending，
        由 worker 重新拉取后只做合并（见 litserve_worker._process_task 的父任务分支）。
        """
        placeholders = ",".join("?" * len(self.CHILD_RETRY_STATUSES))
        with self.get_cursor() as cursor:
            cursor.execute(
                f"SELECT task_id FROM tasks WHERE parent_task_id = ? AND status IN ({placeholders})",
                (parent_task_id, *self.CHILD_RETRY_STATUSES),
            )
            retry_ids = [row["task_id"] for row in cursor.fetchall()]

            for child_id in retry_ids:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET status = 'pending',
                        error_message = NULL,
                        started_at = NULL,
                        completed_at = NULL,
                        worker_id = NULL,
                        retry_count = retry_count + 1,
                        stale_reset_count = 0
                    WHERE task_id = ?
                    """,
                    (child_id,),
                )

            cursor.execute("SELECT child_count FROM tasks WHERE task_id = ?", (parent_task_id,))
            child_count = cursor.fetchone()["child_count"]
            only_merge = self._count_completed_children(cursor, parent_task_id) >= child_count

            cursor.execute(
                """
                UPDATE tasks
                SET status = ?,
                    error_message = NULL,
                    completed_at = NULL,
                    worker_id = NULL,
                    retry_count = retry_count + 1,
                    stale_reset_count = 0
                WHERE task_id = ?
                """,
                ("pending" if only_merge else "processing", parent_task_id),
            )
            ok = cursor.rowcount > 0

        if ok:
            for child_id in retry_ids:
                self._requeue_pending(child_id)
            if only_merge:
                self._requeue_pending(parent_task_id)
            logger.info(
                f"🔁 Parent task {parent_task_id} retried: {len(retry_ids)} subtasks requeued"
                + (" (all subtasks completed, re-merging only)" if only_merge else "")
            )
        return ok

    def _requeue_pending(self, task_id: str):
        """把一个已经置回 pending 的任务重新放进 Redis 队列

        不入队也不会丢任务（SQLite 抢锁路径兜底），但那样就绕开了 Redis，
        正是我们要避免的锁竞争路径。在事务提交后调用。
        """
        if not REDIS_QUEUE_AVAILABLE:
            return
        with self.get_cursor() as cursor:
            cursor.execute("SELECT task_id, priority, file_name, backend FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
        if row:
            self._enqueue_to_redis(
                row["task_id"], row["priority"], {"file_name": row["file_name"], "backend": row["backend"]}
            )

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务：将 pending/processing/paused 状态的任务标记为 cancelled。
        - 已取消的任务不会被打回 pending，也不会被调度器再次派发
        - 正在处理的任务由 worker 在完成/失败时根据状态机自动跳过（completed/failed 仅对 processing 生效）
        - 已拆分的父任务：未完成的子任务一并取消，排队中的不再占用处理名额
        """
        cancel_sql = """
            UPDATE tasks
            SET status = 'cancelled',
                started_at = NULL,
                completed_at = CURRENT_TIMESTAMP,
                worker_id = NULL
            WHERE {target}
            AND status IN ('pending', 'processing', 'paused')
        """
        with self.get_cursor() as cursor:
            cursor.execute(cancel_sql.format(target="task_id = ?"), (task_id,))
            ok = cursor.rowcount > 0
            if ok:
                cursor.execute(cancel_sql.format(target="parent_task_id = ?"), (task_id,))
                if cursor.rowcount:
                    logger.info(f"🚫 Cancelled {cursor.rowcount} unfinished subtasks of parent task {task_id}")
            return ok

    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务：仅允许暂停处于 pending（排队中）的任务
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'paused'
                WHERE task_id = ? AND status = 'pending'
                """,
                (task_id,),
            )
            return cursor.rowcount > 0

    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务：将 paused 状态的任务重新放回 pending 队列
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'pending'
                WHERE task_id = ? AND status = 'paused'
                """,
                (task_id,),
            )
            ok = cursor.rowcount > 0

        if ok:
            self._requeue_pending(task_id)
        return ok

    def clear_task_cache(self, task_id: str) -> bool:
        """
        清理任务缓存：先物理删除解析产物，再将 result_path 标记为已清理（保留数据库历史记录）
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # 仅删除解析产物，保留上传的源文件
        self.delete_task_files(task, include_source=False)

        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET result_path = 'CLEARED'
                WHERE task_id = ?
                """,
                (task_id,),
            )
            return cursor.rowcount > 0


if __name__ == "__main__":
    # 测试代码
    db = TaskDB("test_tianshu.db")

    # 创建测试任务
    task_id = db.create_task(
        file_name="test.pdf",
        file_path="/tmp/test.pdf",
        backend="pipeline",
        options={"lang": "ch", "formula_enable": True},
        priority=1,
    )
    print(f"Created task: {task_id}")

    # 查询任务
    task = db.get_task(task_id)
    print(f"Task details: {task}")

    # 获取统计
    stats = db.get_queue_stats()
    print(f"Queue stats: {stats}")

    # 清理测试数据库
    Path("test_tianshu.db").unlink(missing_ok=True)
    print("Test completed!")
