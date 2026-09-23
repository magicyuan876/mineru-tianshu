import pytest


def make_stale(task_db, task_id, minutes=120):
    """把 processing 任务的 started_at 拨回过去，模拟卡死"""
    with task_db.get_cursor() as cursor:
        cursor.execute(
            "UPDATE tasks SET started_at = datetime('now', ?) WHERE task_id = ?",
            (f"-{minutes} minutes", task_id),
        )


def claim_and_stall(task_db, task_id):
    claimed = task_db.get_next_task("worker-a")
    assert claimed["task_id"] == task_id
    make_stale(task_db, task_id)


def test_stale_task_is_requeued_until_retry_limit_then_failed(task_db):
    task_id = task_db.create_task("sheet.xlsx", "/tmp/sheet.xlsx")

    for attempt in range(1, 3):
        claim_and_stall(task_db, task_id)
        result = task_db.reset_stale_tasks(60, max_retries=2)
        assert result["reset_count"] == 1 and result["failed_count"] == 0
        task = task_db.get_task(task_id)
        assert task["status"] == "pending"
        assert task["stale_reset_count"] == attempt

    claim_and_stall(task_db, task_id)
    result = task_db.reset_stale_tasks(60, max_retries=2)

    assert result["reset_count"] == 0 and result["failed_count"] == 1
    task = task_db.get_task(task_id)
    assert task["status"] == "failed"
    assert task["completed_at"] is not None
    assert "超过 60 分钟" in task["error_message"] and "已自动重试 2 次" in task["error_message"]
    assert result["failed_tasks"] == [
        {"task_id": task_id, "parent_task_id": None, "error_message": task["error_message"]}
    ]


def test_zero_retries_fails_on_first_timeout(task_db):
    task_id = task_db.create_task("sheet.xlsx", "/tmp/sheet.xlsx")
    claim_and_stall(task_db, task_id)

    result = task_db.reset_stale_tasks(60, max_retries=0)

    assert result["failed_count"] == 1
    assert task_db.get_task(task_id)["status"] == "failed"


def test_recent_processing_task_is_left_alone(task_db):
    task_id = task_db.create_task("doc.pdf", "/tmp/doc.pdf")
    task_db.get_next_task("worker-a")

    result = task_db.reset_stale_tasks(60, max_retries=0)

    assert result == {"reset_count": 0, "failed_count": 0, "failed_tasks": []}
    assert task_db.get_task(task_id)["status"] == "processing"


def test_parent_waiting_for_children_is_never_reset_or_failed(task_db):
    parent_id = task_db.create_task("big.pdf", "/tmp/big.pdf")
    task_db.get_next_task("worker-a")
    task_db.convert_to_parent_task(parent_id, child_count=1)
    task_db.create_child_tasks_bulk(parent_id, [{"file_name": "part1.pdf", "file_path": "/tmp/part1.pdf"}])
    make_stale(task_db, parent_id, minutes=600)

    result = task_db.reset_stale_tasks(60, max_retries=0)

    assert result["failed_count"] == 0 and result["reset_count"] == 0
    assert task_db.get_task(parent_id)["status"] == "processing"


def test_stale_child_failure_fails_its_parent(task_db):
    parent_id = task_db.create_task("big.pdf", "/tmp/big.pdf")
    task_db.get_next_task("worker-a")
    task_db.convert_to_parent_task(parent_id, child_count=1)
    (child_id,) = task_db.create_child_tasks_bulk(
        parent_id, [{"file_name": "part1.pdf", "file_path": "/tmp/part1.pdf"}]
    )
    claim_and_stall(task_db, child_id)

    result = task_db.reset_stale_tasks(60, max_retries=0)

    assert result["failed_tasks"][0]["parent_task_id"] == parent_id
    assert task_db.get_task(child_id)["status"] == "failed"
    parent = task_db.get_task(parent_id)
    assert parent["status"] == "failed"
    assert child_id in parent["error_message"]


def test_manual_retry_restores_full_auto_retry_budget(task_db):
    task_id = task_db.create_task("sheet.xlsx", "/tmp/sheet.xlsx")
    claim_and_stall(task_db, task_id)
    task_db.reset_stale_tasks(60, max_retries=1)
    claim_and_stall(task_db, task_id)
    task_db.reset_stale_tasks(60, max_retries=1)
    assert task_db.get_task(task_id)["status"] == "failed"

    assert task_db.retry_task(task_id) is True
    assert task_db.get_task(task_id)["stale_reset_count"] == 0

    claim_and_stall(task_db, task_id)
    task_db.reset_stale_tasks(60, max_retries=1)
    assert task_db.get_task(task_id)["status"] == "pending"


def test_handle_stale_tasks_uses_configured_limit_and_notifies_top_level_only(task_db, mocker):
    from auth.system_config import SystemConfig
    import stale_tasks

    SystemConfig(task_db.db_path).set_config("task_max_retries", "0")
    enqueue = mocker.patch("webhook.dispatcher.enqueue_task_event")

    parent_id = task_db.create_task("big.pdf", "/tmp/big.pdf")
    task_db.get_next_task("worker-a")
    task_db.convert_to_parent_task(parent_id, child_count=1)
    (child_id,) = task_db.create_child_tasks_bulk(
        parent_id, [{"file_name": "part1.pdf", "file_path": "/tmp/part1.pdf"}]
    )
    claim_and_stall(task_db, child_id)
    top_id = task_db.create_task("sheet.xlsx", "/tmp/sheet.xlsx")
    claim_and_stall(task_db, top_id)

    result = stale_tasks.handle_stale_tasks(task_db, 60)

    assert result["max_retries"] == 0
    assert result["failed_count"] == 2
    enqueue.assert_called_once_with(task_db, top_id, "task.failed")


@pytest.mark.parametrize(("stored", "expected"), [(None, 2), ("", 2), ("5", 5), ("0", 0), ("abc", 2), ("99", 2)])
def test_get_task_max_retries_falls_back_to_default(task_db, stored, expected):
    from auth.system_config import SystemConfig, get_task_max_retries

    config = SystemConfig(task_db.db_path)
    if stored is not None:
        config.set_config("task_max_retries", stored)

    assert get_task_max_retries(config) == expected
