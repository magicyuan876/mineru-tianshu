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

# 导入 Redis 队列（可选）
try:
    from redis_queue import get_redis_queue

    REDIS_QUEUE_AVAILABLE = True
except ImportError:
    REDIS_QUEUE_AVAILABLE = False

    def get_redis_queue():
        return None


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
        self._init_db()

    def _get_conn(self):
        """获取数据库连接（每次创建新连接，避免 pickle 问题）

        并发安全说明：
            - 使用 check_same_thread=False 是安全的，因为：
              1. 每次调用都创建新连接，不跨线程共享
              2. 连接使用完立即关闭（在 get_cursor 上下文管理器中）
              3. 不使用连接池，避免线程间共享同一连接
            - timeout=30.0 防止死锁，如果锁等待超过30秒会抛出异常
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
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

    def create_task(
        self,
        file_name: str,
        file_path: str,
        backend: str = "pipeline",
        options: dict = None,
        priority: int = 0,
        user_id: str = None,
    ) -> str:
        """
        创建新任务
        """
        task_id = str(uuid.uuid4())
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (task_id, file_name, file_path, backend, options, priority, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (task_id, file_name, file_path, backend, json.dumps(options or {}), priority, user_id),
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
    def _delete_task_files(self, task_row):
        """辅助方法：安全删除任务的源文件和结果目录"""
        task_id = task_row["task_id"]

        # 1. 删除上传的源文件
        if task_row["file_path"]:
            try:
                fp = Path(task_row["file_path"])
                if fp.exists() and fp.is_file():
                    fp.unlink()
                    logger.debug(f"Deleted source file for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to delete source file for task {task_id}: {e}")

        # 2. 删除结果目录
        if task_row["result_path"]:
            try:
                rp = Path(task_row["result_path"])
                if rp.exists() and rp.is_dir():
                    shutil.rmtree(rp)
                    logger.debug(f"Deleted result dir for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to delete result dir for task {task_id}: {e}")

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

    def reset_tasks_from_dead_worker(self, worker_id_prefix: str, current_worker_id: str) -> int:
        """
        重置属于已死亡 Worker 实例的 processing 任务。

        Worker ID 格式: tianshu-{hostname}-{device}-{pid}
        重启后 PID 变化，旧实例的任务会永远卡在 processing。
        本方法通过前缀匹配（hostname+device 相同）找到候选任务，
        再用 PID 存活检测过滤出真正已死亡 worker 的任务，
        避免误伤同设备上并行运行的兄弟 worker 的在途任务。

        Args:
            worker_id_prefix: 当前设备的前缀，如 "tianshu-cb3e2d3f2604-cuda:0"
            current_worker_id: 当前 Worker 自身 ID，排除在外避免重置自己的任务
        """
        import os as _os

        dead_task_ids: list = []
        dead_task_priorities: dict = {}
        alive_skipped = 0
        unparsable = 0
        reset_count = 0

        with self.get_cursor() as cursor:
            # 先取候选：前缀匹配、非自身、且仍在 processing
            # 排除父任务（is_parent=1）：父任务的进度由子任务回调驱动，不应因 worker 重启
            # 被重置后重新拆分（会重复拆分 + child_completed 计数错乱 + 提前合并删分片）
            cursor.execute(
                """
                SELECT task_id, worker_id, priority FROM tasks
                WHERE status = 'processing'
                  AND worker_id LIKE ? || '-%'
                  AND worker_id != ?
                  AND (is_parent IS NULL OR is_parent = 0)
                """,
                (worker_id_prefix, current_worker_id),
            )
            candidates = cursor.fetchall()

            for row in candidates:
                wid = row["worker_id"] or ""
                # 从尾部解析 PID（格式: tianshu-{hostname}-{device}-{pid}）
                try:
                    pid = int(wid.rsplit("-", 1)[-1])
                except (ValueError, IndexError):
                    # 无法解析 PID：保守起见当作遗留任务一起重置
                    dead_task_ids.append(row["task_id"])
                    dead_task_priorities[row["task_id"]] = row["priority"]
                    unparsable += 1
                    continue

                # 前缀已限定 hostname，所有候选都在本机 → os.kill(pid, 0) 可用
                try:
                    _os.kill(pid, 0)
                    # 进程存在 → 兄弟 worker 的活任务，跳过
                    alive_skipped += 1
                except ProcessLookupError:
                    # 进程已不存在 → 真正遗留的死任务
                    dead_task_ids.append(row["task_id"])
                    dead_task_priorities[row["task_id"]] = row["priority"]
                except PermissionError:
                    # 进程存在但属于其他用户（通常不会发生于容器内）→ 保守跳过
                    alive_skipped += 1
                except Exception:
                    # 任何其它异常 → 保守跳过，交给 reset_stale_tasks 兜底
                    alive_skipped += 1

            if not dead_task_ids:
                if alive_skipped > 0:
                    logger.info(
                        f"✅ Dead-worker recovery: skipped {alive_skipped} tasks "
                        f"belonging to live sibling workers under '{worker_id_prefix}'"
                    )
                return 0

            # 用具体 task_id 做 UPDATE，避免再次条件扫描时误伤刚启动的兄弟 worker
            placeholders = ",".join("?" * len(dead_task_ids))
            cursor.execute(
                f"""
                UPDATE tasks
                SET status = 'pending',
                    worker_id = NULL,
                    retry_count = retry_count + 1
                WHERE task_id IN ({placeholders})
                  AND status = 'processing'
                """,
                dead_task_ids,
            )
            reset_count = cursor.rowcount
            if reset_count > 0:
                extras = []
                if alive_skipped:
                    extras.append(f"skipped {alive_skipped} live sibling tasks")
                if unparsable:
                    extras.append(f"{unparsable} unparsable worker_ids reset")
                suffix = f" ({', '.join(extras)})" if extras else ""
                logger.warning(
                    f"🔄 Dead worker recovery: reset {reset_count} tasks "
                    f"from previous instances of '{worker_id_prefix}'{suffix}"
                )

        # 事务提交后再重新入队到 Redis：否则任务只在 SQLite 标 pending、不在 Redis 队列，
        # 成为无人处理的孤儿。
        for tid in dead_task_ids:
            self._enqueue_to_redis(tid, dead_task_priorities.get(tid) or 0)

        return reset_count

    def reset_stale_tasks(self, timeout_minutes: int = 60, max_retries: int = 3):
        """
        重置超时的 processing 任务为 pending；超过最大重试次数的标记为 failed。

        关键保证（避免"失败重试后仍失败却永久卡住"与"父任务死循环重拆"）：
        - 子任务超时且 retry_count >= max_retries → 标 failed（不再无限重试卡死）
        - 被超限标 failed 的子任务，其父任务联动标 failed（否则父任务永久卡 processing）
        - 父任务本身排除在超时重置之外（避免被重置后重复拆分、child_completed 计数错乱、
          提前合并删分片）；父任务的收尾交给 reap_stale_parent_tasks 兜底回收。
        """
        stale_tasks: list = []
        reset_count = 0

        with self.get_cursor() as cursor:
            # 1. 找出"即将因超限被标 failed"的子任务的父任务，稍后联动标记父任务失败。
            #    （这条标 failed 走直接 SQL，不触发 on_child_task_failed 回调，
            #      不联动的话父任务会永久卡在 processing。）
            cursor.execute(
                """
                SELECT DISTINCT parent_task_id FROM tasks
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                AND retry_count >= ?
                AND parent_task_id IS NOT NULL
                """,
                (timeout_minutes, max_retries),
            )
            failed_parent_ids = [row["parent_task_id"] for row in cursor.fetchall()]

            # 2. 超过重试次数的任务标 failed（父任务除外，父任务由子任务回调/兜底驱动）
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = 'Max retries exceeded (retry_count >= ' || ? || '). Task may cause worker OOM or crash.'
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                AND retry_count >= ?
                AND (is_parent IS NULL OR is_parent = 0)
                """,
                (max_retries, timeout_minutes, max_retries),
            )
            failed_count = cursor.rowcount
            if failed_count > 0:
                logger.warning(f"⚠️  Marked {failed_count} tasks as failed (exceeded {max_retries} retries)")

            # 3. 联动：被超限标 failed 的子任务，其父任务也标 failed
            for _pid in failed_parent_ids:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET status = 'failed',
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = 'A subtask exceeded max retries and failed.'
                    WHERE task_id = ? AND status = 'processing'
                    """,
                    (_pid,),
                )

            # 4. 其余超时任务（父任务除外）查出后重置为 pending 重试
            cursor.execute(
                """
                SELECT task_id, priority FROM tasks
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                AND (is_parent IS NULL OR is_parent = 0)
                """,
                (timeout_minutes,),
            )
            stale_tasks = [(row["task_id"], row["priority"]) for row in cursor.fetchall()]

            cursor.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    worker_id = NULL,
                    retry_count = retry_count + 1
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                AND (is_parent IS NULL OR is_parent = 0)
                """,
                (timeout_minutes,),
            )
            reset_count = cursor.rowcount

        # 事务提交后再 re-enqueue 到 Redis：
        # Redis 模式下 worker 优先从 Redis 队列取任务，只改 SQLite 的 status 而不 re-enqueue
        # 会让任务变成"SQLite=pending 但不在 Redis 队列"的孤儿，长期无人处理。
        # （SQLite 模式下 _enqueue_to_redis 为 no-op。）
        for task_id, priority in stale_tasks:
            self._enqueue_to_redis(task_id, priority or 0)

        return reset_count

    def update_heartbeat(self, task_id: str, worker_id: str) -> bool:
        """
        心跳续租：刷新正在处理任务的 started_at。

        worker 处理长任务（如大分片）期间定期调用，使 started_at 保持新鲜，
        避免被 reset_stale_tasks 误判为"超时卡死"而重置（worker 与 scheduler
        分属不同进程/容器，无法跨进程探活，故用心跳续租实现"还活着"的判定）。
        只有任务仍是 processing 且属于该 worker 时才续租。
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET started_at = CURRENT_TIMESTAMP
                WHERE task_id = ? AND worker_id = ? AND status = 'processing'
                """,
                (task_id, worker_id),
            )
            return cursor.rowcount > 0

    def reap_stale_parent_tasks(self, timeout_minutes: int = 120) -> int:
        """
        父任务兜底回收。

        父任务被排除在 reset_stale_tasks 之外（避免被重置后重复拆分），代价是
        "拆分中途崩溃"或"子任务已终结却没合并"的父任务会永久卡在 processing。
        本方法定期扫描超时父任务并按子任务真实状态收尾：
          - 无子任务（拆分中途崩溃，子任务还没建成）        → 标 failed
          - 仍有 pending/processing 子任务在推进            → 不动（视为正常长任务）
          - 子任务全部 completed（只差合并没成功）          → 删旧子任务并还原为普通 pending 重处理
          - 其余（存在 failed / cancelled 子任务）          → 标 failed

        Args:
            timeout_minutes: 父任务 processing 超过此时长才介入（应远大于单分片处理时长）
        Returns:
            int: 处理的父任务数
        """
        handled = 0
        reset_parent_ids: list = []

        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT task_id FROM tasks
                WHERE is_parent = 1 AND status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
                """,
                (timeout_minutes,),
            )
            parent_ids = [row["task_id"] for row in cursor.fetchall()]

            for pid in parent_ids:
                cursor.execute("SELECT status FROM tasks WHERE parent_task_id = ?", (pid,))
                child_statuses = [row["status"] for row in cursor.fetchall()]
                active = any(s in ("pending", "processing") for s in child_statuses)

                if not child_statuses:
                    # 拆分中途崩溃：父任务已标 is_parent 但子任务未建成
                    cursor.execute(
                        """
                        UPDATE tasks SET status='failed', completed_at=CURRENT_TIMESTAMP,
                            error_message='PDF split crashed before subtasks were created; please re-submit.'
                        WHERE task_id=? AND status='processing'
                        """,
                        (pid,),
                    )
                    handled += cursor.rowcount
                elif active:
                    # 仍有 pending/processing 子任务在推进父任务，视为正常长任务，不处理
                    continue
                elif all(s == "completed" for s in child_statuses):
                    # 子任务全部完成却没合并（合并步骤丢失）→ 删旧子任务并把父任务还原为普通
                    # pending 任务，让 worker 重新拾取、重新拆分处理
                    cursor.execute("DELETE FROM tasks WHERE parent_task_id = ?", (pid,))
                    cursor.execute(
                        """
                        UPDATE tasks
                        SET status='pending', is_parent=0, child_count=0, child_completed=0,
                            worker_id=NULL, started_at=NULL, completed_at=NULL,
                            error_message=NULL, retry_count=0
                        WHERE task_id=?
                        """,
                        (pid,),
                    )
                    if cursor.rowcount > 0:
                        reset_parent_ids.append(pid)
                        handled += 1
                else:
                    # 无在途子任务，但非全部 completed（存在 failed / cancelled）→ 父任务标 failed
                    cursor.execute(
                        """
                        UPDATE tasks SET status='failed', completed_at=CURRENT_TIMESTAMP,
                            error_message='One or more subtasks failed or were cancelled.'
                        WHERE task_id=? AND status='processing'
                        """,
                        (pid,),
                    )
                    handled += cursor.rowcount

            if handled > 0:
                logger.warning(f"🩺 Reaped {handled} stale parent task(s) (timeout: {timeout_minutes}m)")

        # 事务提交后 re-enqueue（SQLite 模式为 no-op；Redis 模式下需要）
        for pid in reset_parent_ids:
            self._enqueue_to_redis(pid, 0)

        return handled

    # -------------------------------------------------------------------------
    # 新增功能：清理失败任务 (包含物理文件删除)
    # -------------------------------------------------------------------------
    def clear_failed_tasks(self) -> int:
        """
        一键清理所有失败的任务
        执行步骤: 1.查询路径 -> 2.删除磁盘文件 -> 3.删除数据库记录
        """
        with self.get_cursor() as cursor:
            # 1. 查询所有 failed 任务
            cursor.execute("SELECT task_id, file_path, result_path FROM tasks WHERE status = 'failed'")
            failed_tasks = cursor.fetchall()

            count = 0
            # 2. 物理删除
            for task in failed_tasks:
                self._delete_task_files(task)
                count += 1

            # 3. 数据库删除
            cursor.execute("DELETE FROM tasks WHERE status = 'failed'")
            logger.info(f"🧹 Cleared {cursor.rowcount} failed tasks (files deleted for {count} tasks)")
            return cursor.rowcount

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
        """将普通任务转换为父任务

        [修复] 同时把 child_completed 清零：
            当 Worker OOM 重启导致父任务被重置为 pending 并被重新拆分时，
            若不清零 child_completed，旧的完成计数会残留，
            进而在新一轮拆分中提前满足 "child_completed >= child_count"，
            触发提前合并、删除尚未处理完的分片，导致结果残缺却显示 completed。
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET is_parent = 1, child_count = ?, child_completed = 0, status = 'processing'
                WHERE task_id = ?
                """,
                (child_count, task_id),
            )
        logger.info(f"🔄 Converted task {task_id} to parent task with {child_count} children (child_completed reset to 0)")

    def create_child_task(
        self,
        parent_task_id: str,
        file_name: str,
        file_path: str,
        backend: str = "pipeline",
        options: dict = None,
        priority: int = 0,
        user_id: str = None,
    ) -> str:
        """创建子任务"""
        task_id = str(uuid.uuid4())
        with self.get_cursor() as cursor:
            # 创建子任务
            cursor.execute(
                """
                INSERT INTO tasks (
                    task_id, parent_task_id, file_name, file_path,
                    backend, options, status, priority, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
                (
                    task_id,
                    parent_task_id,
                    file_name,
                    file_path,
                    backend,
                    json.dumps(options or {}),
                    priority,
                    user_id,
                ),
            )

            # 更新父任务的子任务计数
            cursor.execute(
                """
                UPDATE tasks
                SET child_count = child_count + 1
                WHERE task_id = ?
            """,
                (parent_task_id,),
            )

        logger.debug(f"📄 Created child task: {task_id} (parent: {parent_task_id})")
        return task_id

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

            # 更新父任务的完成计数
            cursor.execute(
                """
                UPDATE tasks
                SET child_completed = child_completed + 1
                WHERE task_id = ?
            """,
                (parent_task_id,),
            )

            # 检查是否所有子任务都完成了
            cursor.execute(
                """
                SELECT child_count, child_completed, file_name
                FROM tasks WHERE task_id = ?
            """,
                (parent_task_id,),
            )
            parent = cursor.fetchone()

            if parent and parent["child_completed"] >= parent["child_count"]:
                # 所有子任务完成
                logger.info(
                    f"🎉 All subtasks completed for parent task {parent_task_id} "
                    f"({parent['child_completed']}/{parent['child_count']}) - {parent['file_name']}"
                )
                return parent_task_id

            if parent:
                logger.info(
                    f"⏳ Subtask progress: {parent['child_completed']}/{parent['child_count']} "
                    f"for parent task {parent_task_id}"
                )

        return None

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

    def delete_child_tasks(self, parent_task_id: str) -> int:
        """删除某父任务下的所有子任务记录及其分片文件。

        [修复] 用于「重新拆分」前清理上一轮残留的子任务：
            Worker OOM 重启 -> 父任务被重置为 pending -> 被重新拆分时，
            上一轮的子任务记录仍残留在库中。若不清理，重拆会产生重复子任务，
            导致 child_completed 计数错乱、合并时读取到陈旧/已删除的分片结果。
        返回删除的子任务数量。
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT task_id, file_path, result_path FROM tasks WHERE parent_task_id = ?",
                (parent_task_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                self._delete_task_files(row)
            cursor.execute("DELETE FROM tasks WHERE parent_task_id = ?", (parent_task_id,))
            return cursor.rowcount

    # ========================================================================
    # 新增功能：重试、清理、暂停、恢复、清理缓存
    # ========================================================================

    def retry_task(self, task_id: str) -> bool:
        """
        重试任务：将任务状态重置为 pending，清空错误和时间，重试次数 +1
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL,
                    worker_id = NULL,
                    retry_count = retry_count + 1
                WHERE task_id = ?
                """,
                (task_id,),
            )
            return cursor.rowcount > 0

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
            return cursor.rowcount > 0

    def clear_task_cache(self, task_id: str) -> bool:
        """
        清理任务缓存：保留数据库历史记录，但将 result_path 标记为已清理
        """
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
