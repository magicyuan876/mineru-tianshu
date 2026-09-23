from fastapi.testclient import TestClient

from auth.models import UserRole
from tests.integration.test_task_config_api import load_api_module, make_token
from tests.unit.test_parent_child_tasks import make_split_parent, set_status


def setup_split_task(db):
    parent_id, children = make_split_parent(db, 3)
    for i, child in enumerate(children):
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET options = ? WHERE task_id = ?",
                (f'{{"chunk_info": {{"start_page": {30 - i * 10}, "end_page": {39 - i * 10}}}}}', child),
            )
    set_status(db, children[0], "completed")
    set_status(db, children[1], "failed", "boom")
    set_status(db, parent_id, "failed", "Subtask failed")
    plain = db.create_task("plain.pdf", "/tmp/plain.pdf")
    return parent_id, children, plain


def test_list_shows_top_level_tasks_with_children_stats(runtime_paths):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()
    parent_id, children, plain = setup_split_task(api_server.db)

    with TestClient(api_server.app) as client:
        listed = client.get("/api/v1/queue/tasks", headers=headers).json()
        with_children = client.get("/api/v1/queue/tasks", params={"include_children": True}, headers=headers).json()
        by_child_id = client.get("/api/v1/queue/tasks", params={"search": children[1]}, headers=headers).json()

    ids = {t["task_id"] for t in listed["tasks"]}
    assert ids == {parent_id, plain}
    assert listed["total"] == 2
    parent = next(t for t in listed["tasks"] if t["task_id"] == parent_id)
    assert parent["children_stats"] == {"total": 3, "completed": 1, "failed": 1, "pending": 1}
    assert with_children["total"] == 5
    assert [t["task_id"] for t in by_child_id["tasks"]] == [children[1]]


def test_children_endpoint_sorted_by_page(runtime_paths):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()
    parent_id, children, _ = setup_split_task(api_server.db)

    with TestClient(api_server.app) as client:
        body = client.get(f"/api/v1/tasks/{parent_id}/children", headers=headers).json()
        other = client.get(f"/api/v1/tasks/{parent_id}/children", headers=make_token(runtime_paths, UserRole.USER))

    assert [c["chunk_info"]["start_page"] for c in body["children"]] == [10, 20, 30]
    assert [c["task_id"] for c in body["children"]] == list(reversed(children))
    assert other.status_code == 403


def test_retry_parent_requeues_failed_subtasks_and_delete_cascades(runtime_paths):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()
    db = api_server.db
    parent_id, children, _ = setup_split_task(db)

    with TestClient(api_server.app) as client:
        retried = client.post(f"/api/v1/tasks/{parent_id}/retry", headers=headers).json()
        assert retried["retried_subtasks"] == 1
        assert db.get_task(parent_id)["status"] == "processing"
        assert db.get_task(children[1])["status"] == "pending"
        assert db.get_task(children[0])["status"] == "completed"

        deleted = client.delete(f"/api/v1/tasks/{parent_id}", headers=headers)

    assert deleted.status_code == 200
    assert db.get_task(parent_id) is None
    assert all(db.get_task(c) is None for c in children)


def test_list_uses_composite_index_and_paginates_ties_stably(runtime_paths):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()
    db = api_server.db

    # 排序若退化成「取出全部顶层任务再排序」，会连同每行 data 大字段一起读，大库上列表接口卡死
    with db.get_cursor() as cursor:
        plan = cursor.execute(
            "EXPLAIN QUERY PLAN SELECT rowid FROM tasks WHERE parent_task_id IS NULL "
            "ORDER BY created_at DESC, rowid DESC LIMIT 20"
        ).fetchall()
    assert "idx_parent_created" in " ".join(row[3] for row in plan)

    # 25 个同一时刻创建的任务：分两页取回应恰好不重不漏
    ids = [db.create_task(f"same_{i}.pdf", f"/tmp/same_{i}.pdf") for i in range(25)]
    with db.get_cursor() as cursor:
        cursor.execute("UPDATE tasks SET created_at = '2026-09-24 01:00:00'")

    with TestClient(api_server.app) as client:
        page1 = client.get("/api/v1/queue/tasks", params={"page": 1, "page_size": 20}, headers=headers).json()
        page2 = client.get("/api/v1/queue/tasks", params={"page": 2, "page_size": 20}, headers=headers).json()

    got = [t["task_id"] for t in page1["tasks"] + page2["tasks"]]
    assert len(got) == 25 and set(got) == set(ids)
