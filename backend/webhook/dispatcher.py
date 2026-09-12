"""
MinerU Tianshu - Webhook 事件入队与投递调度

任务进入终态时由 Worker 调用 enqueue_task_event 写入投递记录；
调度器定期调用 process_pending_deliveries 扫描到期记录并投递。
所有函数都不抛异常给调用方，绝不能影响任务主流程 / 调度器主循环。
"""

import json

from loguru import logger

from . import delivery
from .config import get_webhook_config


def build_task_payload(task: dict, event: str) -> dict:
    """构造任务事件报文；不含解析结果内容，只给结果查询地址"""
    status = "completed" if event == "task.completed" else "failed"
    task_id = task.get("task_id", "")
    return {
        "event": event,
        "task_id": task_id,
        "file_name": task.get("file_name"),
        "status": status,
        "error_message": task.get("error_message") if status == "failed" else None,
        "created_at": str(task.get("created_at") or ""),
        "completed_at": str(task.get("completed_at") or ""),
        "result_url": f"/api/v1/tasks/{task_id}",
    }


def enqueue_task_event(task_db, task_id: str, event: str) -> None:
    """任务终态触发：按全局配置与任务级 webhook_url 各写一条投递记录

    读配置或写表失败仅告警；子任务由 Worker 侧过滤，这里不重复判断。
    """
    try:
        task = task_db.get_task(task_id)
        if not task:
            logger.warning(f"⚠️ Webhook 入队跳过：任务 {task_id} 不存在")
            return

        try:
            options = json.loads(task.get("options") or "{}")
        except (json.JSONDecodeError, TypeError):
            options = {}

        cfg = get_webhook_config()
        payload = build_task_payload(task, event)
        enqueued = 0

        # 全局 webhook：需启用、配置了 URL 且事件在订阅列表里
        if cfg["enabled"] and cfg["url"] and event in cfg["events"]:
            delivery.insert_delivery(task_id, event, cfg["url"], payload)
            enqueued += 1

        # 任务级 webhook：随任务提交时携带，不受订阅事件列表限制
        task_url = (options.get("webhook_url") or "").strip()
        if task_url:
            delivery.insert_delivery(task_id, event, task_url, payload)
            enqueued += 1

        if enqueued:
            logger.info(f"🔔 Webhook 已入队 {enqueued} 条（任务 {task_id}，事件 {event}）")
    except Exception as e:
        logger.warning(f"⚠️ Webhook 入队失败（任务 {task_id}，事件 {event}）: {e}")


def deliver_delivery(row: dict, secret: str, timeout: int, max_attempts: int) -> bool:
    """投递单条记录并按结果更新状态，返回是否投递成功"""
    delivery_id = row["delivery_id"]
    url = row["url"]
    try:
        payload = json.loads(row["payload"])
    except (json.JSONDecodeError, TypeError):
        delivery.mark_dead(delivery_id, "Invalid payload JSON")
        return False

    # SSRF 防护：目标必须解析到公网地址，失败直接置 dead（重试无意义）
    try:
        delivery.validate_webhook_url(url)
    except ValueError as e:
        delivery.mark_dead(delivery_id, f"SSRF check failed: {e}")
        logger.warning(f"⚠️ Webhook 投递被拒（{delivery_id}）: {e}")
        return False

    attempts = int(row.get("attempts") or 0) + 1
    try:
        status_code = delivery.post_webhook(url, payload, secret=secret, timeout=timeout)
        if 200 <= status_code < 300:
            delivery.mark_delivered(delivery_id)
            logger.info(f"✅ Webhook 投递成功（{delivery_id}，HTTP {status_code}）")
            return True
        delivery.mark_retry_or_dead(delivery_id, attempts, max_attempts, f"HTTP {status_code}")
        logger.warning(f"⚠️ Webhook 投递返回 HTTP {status_code}（{delivery_id}，第 {attempts} 次）")
    except Exception as e:
        delivery.mark_retry_or_dead(delivery_id, attempts, max_attempts, f"{type(e).__name__}: {e}")
        logger.warning(f"⚠️ Webhook 投递失败（{delivery_id}，第 {attempts} 次）: {e}")
    return False


def process_pending_deliveries() -> None:
    """扫描到期的 pending 记录并逐条同步投递（供调度器主循环调用）"""
    try:
        cfg = get_webhook_config()
        rows = delivery.fetch_due_deliveries()
        for row in rows:
            try:
                deliver_delivery(row, cfg["secret"], cfg["timeout"], cfg["max_attempts"])
            except Exception as e:
                logger.error(f"❌ Webhook 投递循环单条异常（{row.get('delivery_id')}）: {e}")
    except Exception as e:
        logger.error(f"❌ Webhook 投递循环异常: {e}")
