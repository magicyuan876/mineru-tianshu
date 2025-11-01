"""
MinerU Tianshu - SQLite Task Database Manager
天枢任务数据库管理器

负责任务的持久化存储、状态管理和原子性操作
"""

import sqlite3
import json
import uuid
from contextlib import contextmanager
from typing import Optional, List, Dict
from pathlib import Path


class TaskDB:
    """任务数据库管理类"""

    def __init__(self, db_path=None):
        # 导入所需模块
        import os
        from pathlib import Path
        
        # 优先使用传入的路径，其次使用环境变量，最后使用默认路径
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "/app/data/db/mineru_tianshu.db")
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

            # 创建索引加速查询
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_id ON tasks(worker_id)")

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

        Args:
            file_name: 文件名
            file_path: 文件路径
            backend: 处理后端 (pipeline/vlm-transformers/vlm-vllm-engine)
            options: 处理选项 (dict)
            priority: 优先级，数字越大越优先
            user_id: 用户ID (可选,用于权限控制)

        Returns:
            task_id: 任务ID
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
        return task_id

    def get_next_task(self, worker_id: str, max_retries: int = 3) -> Optional[Dict]:
        """
        获取下一个待处理任务（原子操作，防止并发冲突）

        Args:
            worker_id: Worker ID
            max_retries: 当任务被其他 worker 抢走时的最大重试次数（默认3次）

        Returns:
            task: 任务字典，如果没有任务返回 None

        并发安全说明：
            1. 使用 BEGIN IMMEDIATE 立即获取写锁
            2. UPDATE 时检查 status = 'pending' 防止重复拉取
            3. 检查 rowcount 确保更新成功
            4. 如果任务被抢走，立即重试而不是返回 None（避免不必要的等待）
        """
        from loguru import logger
        
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
                            # 因为队列中可能还有其他待处理任务
                            if attempt == 0:  # 只在第一次尝试时记录日志
                                logger.debug(f"Task {task_id} was grabbed by another worker, retrying...")
                            continue

                        return dict(task)
                    else:
                        # 队列中没有待处理任务，返回 None
                        # 只在第一次尝试时记录调试信息（避免日志过多）
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
                    # 最后一次尝试失败，返回 None
                    return None
                # 等待一小段时间后重试
                import time
                time.sleep(0.1)

        # 重试次数用尽，仍未获取到任务（高并发场景）
        logger.warning(f"⚠️  Failed to get task after {max_retries} attempts")
        return None

    def update_task_status(
        self, task_id: str, status: str, result_path: str = None, error_message: str = None, worker_id: str = None
    ):
        """
        更新任务状态（使用预定义 SQL 模板，防止 SQL 注入）

        Args:
            task_id: 任务ID
            status: 新状态 (pending/processing/completed/failed/cancelled)
            result_path: 结果路径（可选）
            error_message: 错误信息（可选）
            worker_id: Worker ID（可选，用于并发检查）

        Returns:
            bool: 更新是否成功

        并发安全说明：
            1. 更新为 completed/failed 时会检查状态是 processing
            2. 如果提供 worker_id，会检查任务是否属于该 worker
            3. 返回 False 表示任务被其他进程修改了

        安全说明：
            使用预定义的 SQL 模板，完全避免 SQL 注入风险
        """
        with self.get_cursor() as cursor:
            success = False

            # 根据不同状态使用预定义的 SQL 模板
            if status == "completed":
                # 完成状态：更新状态、完成时间和结果路径
                if worker_id:
                    # 带 worker_id 验证
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            result_path = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                        AND worker_id = ?
                    """
                    cursor.execute(sql, (status, result_path, task_id, worker_id))
                else:
                    # 不验证 worker_id
                    sql = """
                        UPDATE tasks
                        SET status = ?,
                            completed_at = CURRENT_TIMESTAMP,
                            result_path = ?
                        WHERE task_id = ?
                        AND status = 'processing'
                    """
                    cursor.execute(sql, (status, result_path, task_id))

                success = cursor.rowcount > 0

            elif status == "failed":
                # 失败状态：更新状态、完成时间和错误信息
                if worker_id:
                    # 带 worker_id 验证
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
                    # 不验证 worker_id
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
                # 取消状态：直接更新状态
                sql = """
                    UPDATE tasks
                    SET status = ?,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """
                cursor.execute(sql, (status, task_id))
                success = cursor.rowcount > 0

            elif status == "pending":
                # 重置为待处理状态
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
                # 其他状态（如 processing）：简单更新状态
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

            return success

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        查询任务详情

        Args:
            task_id: 任务ID

        Returns:
            task: 任务字典，如果不存在返回 None
        """
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            return dict(task) if task else None

    def get_queue_stats(self) -> Dict[str, int]:
        """
        获取队列统计信息

        Returns:
            stats: 各状态的任务数量
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            """)
            stats = {row["status"]: row["count"] for row in cursor.fetchall()}
            return stats

    def get_tasks_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """
        根据状态获取任务列表

        Args:
            status: 任务状态
            limit: 返回数量限制

        Returns:
            tasks: 任务列表
        """
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

    def cleanup_old_task_files(self, days: int = 7):
        """
        清理旧任务的结果文件（保留数据库记录）

        Args:
            days: 清理多少天前的任务文件

        Returns:
            int: 删除的文件目录数

        注意：
            - 只删除结果文件，保留数据库记录
            - 数据库中的 result_path 字段会被清空
            - 用户仍可查询任务状态和历史记录
        """
        from pathlib import Path
        import shutil

        with self.get_cursor() as cursor:
            # 查询要清理文件的任务
            cursor.execute(
                """
                SELECT task_id, result_path FROM tasks
                WHERE completed_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'failed')
                AND result_path IS NOT NULL
            """,
                (days,),
            )

            old_tasks = cursor.fetchall()
            file_count = 0

            # 删除结果文件
            for task in old_tasks:
                if task["result_path"]:
                    result_path = Path(task["result_path"])
                    if result_path.exists() and result_path.is_dir():
                        try:
                            shutil.rmtree(result_path)
                            file_count += 1

                            # 清空数据库中的 result_path，表示文件已被清理
                            cursor.execute(
                                """
                                UPDATE tasks
                                SET result_path = NULL
                                WHERE task_id = ?
                            """,
                                (task["task_id"],),
                            )

                        except Exception as e:
                            from loguru import logger

                            logger.warning(f"Failed to delete result files for task {task['task_id']}: {e}")

            return file_count

    def cleanup_old_task_records(self, days: int = 30):
        """
        清理极旧的任务记录（可选功能）

        Args:
            days: 删除多少天前的任务记录

        Returns:
            int: 删除的记录数

        注意：
            - 这个方法会永久删除数据库记录
            - 建议设置较长的保留期（如30-90天）
            - 一般情况下不需要调用此方法
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM tasks
                WHERE completed_at < datetime('now', '-' || ? || ' days')
                AND status IN ('completed', 'failed')
            """,
                (days,),
            )

            deleted_count = cursor.rowcount
            return deleted_count

    def reset_stale_tasks(self, timeout_minutes: int = 60):
        """
        重置超时的 processing 任务为 pending

        Args:
            timeout_minutes: 超时时间（分钟）
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET status = 'pending',
                    worker_id = NULL,
                    retry_count = retry_count + 1
                WHERE status = 'processing'
                AND started_at < datetime('now', '-' || ? || ' minutes')
            """,
                (timeout_minutes,),
            )
            reset_count = cursor.rowcount
            return reset_count


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
