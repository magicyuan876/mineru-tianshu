"""
MinerU Tianshu - 超时任务处理

调度器定时调用与管理员手动触发（/admin/reset-stale）共用同一套逻辑：
读取管理员配置的自动重试上限 → 重置或判定失败 → 失败任务补发 task.failed webhook。
"""

from loguru import logger

from auth.system_config import get_task_max_retries


def handle_stale_tasks(task_db, timeout_minutes: int) -> dict:
    """处理超时任务，返回 TaskDB.reset_stale_tasks 的结果（附带本次使用的 max_retries）"""
    max_retries = get_task_max_retries()
    result = task_db.reset_stale_tasks(timeout_minutes, max_retries=max_retries)

    # 与 worker 侧一致：子任务失败不单独通知，由父任务统一处理
    for task in result["failed_tasks"]:
        if task["parent_task_id"]:
            continue
        try:
            from webhook.dispatcher import enqueue_task_event

            enqueue_task_event(task_db, task["task_id"], "task.failed")
        except Exception as e:
            logger.warning(f"⚠️ Webhook 通知入队失败（任务 {task['task_id']}，事件 task.failed）: {e}")

    result["max_retries"] = max_retries
    return result
