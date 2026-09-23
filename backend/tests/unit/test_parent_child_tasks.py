"""主子任务联动：完成计数、重试、取消、删除、清理失败任务"""


def set_status(task_db, task_id, status, error=None):
    with task_db.get_cursor() as cursor:
        cursor.execute("UPDATE tasks SET status = ?, error_message = ? WHERE task_id = ?", (status, error, task_id))


def make_split_parent(task_db, n=3):
    """模拟 worker 拆分大 PDF（与 litserve_worker._should_split_pdf 的调用顺序一致）"""
    parent_id = task_db.create_task("big.pdf", "/tmp/big.pdf")
    task_db.get_next_task("worker-a")
    task_db.convert_to_parent_task(parent_id, child_count=0)
    children = task_db.create_child_tasks_bulk(
        parent_id, [{"file_name": f"big_p{i}.pdf", "file_path": f"/tmp/big_p{i}.pdf"} for i in range(n)]
    )
    task_db.convert_to_parent_task(parent_id, child_count=n)
    return parent_id, children


def status_of(task_db, task_id):
    return task_db.get_task(task_id)["status"]


def test_completion_counts_real_completed_children_and_merges_once(task_db):
    parent_id, children = make_split_parent(task_db, 2)

    set_status(task_db, children[0], "completed")
    assert task_db.on_child_task_completed(children[0]) is None
    set_status(task_db, children[1], "completed")
    assert task_db.on_child_task_completed(children[1]) == parent_id

    # 重复回调（并发完成 / 重跑）不会再次触发合并，计数也不会超过实际完成数
    assert task_db.on_child_task_completed(children[1]) is None
    assert task_db.get_task(parent_id)["child_completed"] == 2


def test_completion_does_not_merge_into_failed_parent(task_db):
    parent_id, children = make_split_parent(task_db, 2)
    set_status(task_db, children[0], "failed", "boom")
    task_db.on_child_task_failed(children[0], "boom")
    assert status_of(task_db, parent_id) == "failed"

    set_status(task_db, children[1], "completed")
    assert task_db.on_child_task_completed(children[1]) is None


def test_retry_parent_requeues_failed_and_cancelled_children_only(task_db):
    parent_id, children = make_split_parent(task_db, 3)
    set_status(task_db, children[0], "completed")
    set_status(task_db, children[1], "failed", "boom")
    set_status(task_db, children[2], "cancelled")
    set_status(task_db, parent_id, "failed", "Subtask failed")

    assert {c["task_id"] for c in task_db.get_children_to_retry(parent_id)} == {children[1], children[2]}
    assert task_db.retry_task(parent_id) is True

    parent = task_db.get_task(parent_id)
    assert parent["status"] == "processing"  # 等待子任务完成后合并，不会被 worker 当成新任务拆分
    assert parent["error_message"] is None
    assert status_of(task_db, children[0]) == "completed"
    assert status_of(task_db, children[1]) == "pending"
    assert status_of(task_db, children[2]) == "pending"
    assert task_db.get_task(children[1])["error_message"] is None

    # 重跑的子任务完成后正常合并
    set_status(task_db, children[1], "completed")
    assert task_db.on_child_task_completed(children[1]) is None
    set_status(task_db, children[2], "completed")
    assert task_db.on_child_task_completed(children[2]) == parent_id


def test_retry_parent_with_all_children_completed_only_remerges(task_db):
    parent_id, children = make_split_parent(task_db, 2)
    for child in children:
        set_status(task_db, child, "completed")
    set_status(task_db, parent_id, "failed", "merge failed")

    assert task_db.retry_task(parent_id) is True

    # 交给 worker 重新拉取：子任务已全部完成，只做合并
    assert status_of(task_db, parent_id) == "pending"
    assert task_db.all_children_completed(parent_id) is True
    assert [status_of(task_db, c) for c in children] == ["completed", "completed"]


def test_retry_child_revives_failed_parent(task_db):
    parent_id, children = make_split_parent(task_db, 2)
    set_status(task_db, children[0], "completed")
    set_status(task_db, children[1], "failed", "boom")
    set_status(task_db, parent_id, "failed", "Subtask failed")

    assert task_db.retry_task(children[1]) is True

    assert status_of(task_db, parent_id) == "processing"
    set_status(task_db, children[1], "completed")
    assert task_db.on_child_task_completed(children[1]) == parent_id


def test_cancel_parent_cascades_to_unfinished_children(task_db):
    parent_id, children = make_split_parent(task_db, 3)
    set_status(task_db, children[0], "completed")
    set_status(task_db, children[1], "processing")

    assert task_db.cancel_task(parent_id) is True

    assert status_of(task_db, parent_id) == "cancelled"
    assert status_of(task_db, children[0]) == "completed"
    assert status_of(task_db, children[1]) == "cancelled"
    assert status_of(task_db, children[2]) == "cancelled"


def test_clear_failed_removes_failed_parents_as_a_group(task_db):
    # 失败的父任务：连同全部子任务（含已完成的）一起清理
    failed_parent, failed_children = make_split_parent(task_db, 2)
    set_status(task_db, failed_children[0], "completed")
    set_status(task_db, failed_children[1], "failed", "boom")
    set_status(task_db, failed_parent, "failed", "Subtask failed")

    # 父任务被取消：它的失败子任务保留，供排查
    cancelled_parent, kept_children = make_split_parent(task_db, 1)
    set_status(task_db, kept_children[0], "failed", "boom")
    set_status(task_db, cancelled_parent, "cancelled")

    # 普通失败任务、以及父任务已不存在的孤儿子任务：清理
    plain_failed = task_db.create_task("plain.pdf", "/tmp/plain.pdf")
    set_status(task_db, plain_failed, "failed", "boom")
    orphan = task_db.create_task("orphan.pdf", "/tmp/orphan.pdf")
    with task_db.get_cursor() as cursor:
        cursor.execute("UPDATE tasks SET parent_task_id = 'gone', status = 'failed' WHERE task_id = ?", (orphan,))

    assert task_db.clear_failed_tasks() == 5

    for gone in [failed_parent, *failed_children, plain_failed, orphan]:
        assert task_db.get_task(gone) is None
    assert status_of(task_db, cancelled_parent) == "cancelled"
    assert status_of(task_db, kept_children[0]) == "failed"


def test_children_stats_and_delete_task_tree(task_db):
    parent_id, children = make_split_parent(task_db, 3)
    set_status(task_db, children[0], "completed")
    set_status(task_db, children[1], "failed", "boom")

    stats = task_db.get_children_stats([parent_id])[parent_id]
    assert stats == {"total": 3, "completed": 1, "failed": 1, "pending": 1}

    assert task_db.delete_task_tree(task_db.get_task(parent_id)) == 4
    assert task_db.get_task(parent_id) is None
    assert all(task_db.get_task(c) is None for c in children)
