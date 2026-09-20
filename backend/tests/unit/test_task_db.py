def test_claims_highest_priority_task_and_records_worker(task_db):
    low_priority = task_db.create_task("low.pdf", "/tmp/low.pdf", priority=1)
    high_priority = task_db.create_task("high.pdf", "/tmp/high.pdf", priority=10)

    claimed = task_db.get_next_task("worker-a")

    assert claimed["task_id"] == high_priority
    assert task_db.get_task(high_priority)["status"] == "processing"
    assert task_db.get_task(high_priority)["worker_id"] == "worker-a"
    assert task_db.get_task(low_priority)["status"] == "pending"


def test_cancelled_task_cannot_be_overwritten_by_late_worker_completion(task_db):
    task_id = task_db.create_task("document.pdf", "/tmp/document.pdf")
    task_db.get_next_task("worker-a")

    assert task_db.cancel_task(task_id) is True

    task_db.update_task_status(task_id, "completed", worker_id="worker-a", result_path="/tmp/result")
    task_db.update_task_status(task_id, "failed", worker_id="worker-a", error_message="late failure")

    task = task_db.get_task(task_id)
    assert task["status"] == "cancelled"
    assert task["result_path"] is None
    assert task["error_message"] is None


def test_pause_resume_and_retry_follow_task_state_machine(task_db):
    task_id = task_db.create_task("document.pdf", "/tmp/document.pdf")

    assert task_db.pause_task(task_id) is True
    assert task_db.pause_task(task_id) is False
    assert task_db.resume_task(task_id) is True
    assert task_db.resume_task(task_id) is False

    task_db.get_next_task("worker-a")
    task_db.update_task_status(task_id, "failed", worker_id="worker-a", error_message="failed once")

    assert task_db.retry_task(task_id) is True
    task = task_db.get_task(task_id)
    assert task["status"] == "pending"
    assert task["error_message"] is None
    assert task["worker_id"] is None
    assert task["retry_count"] == 1


def test_child_completion_only_returns_parent_after_last_child(task_db):
    parent_id = task_db.create_parent_task("archive.zip", "/tmp/archive.zip")
    child_ids = task_db.create_child_tasks_bulk(
        parent_id,
        [
            {"file_name": "first.pdf", "file_path": "/tmp/first.pdf"},
            {"file_name": "second.pdf", "file_path": "/tmp/second.pdf"},
        ],
    )

    assert task_db.on_child_task_completed(child_ids[0]) is None
    assert task_db.on_child_task_completed(child_ids[1]) == parent_id

    parent = task_db.get_task(parent_id)
    assert parent["child_count"] == 2
    assert parent["child_completed"] == 2


def test_child_failure_marks_processing_parent_failed(task_db):
    parent_id = task_db.create_parent_task("archive.zip", "/tmp/archive.zip")
    child_id = task_db.create_child_tasks_bulk(
        parent_id,
        [{"file_name": "failed.pdf", "file_path": "/tmp/failed.pdf"}],
    )[0]

    task_db.on_child_task_failed(child_id, "parse failed")

    parent = task_db.get_task(parent_id)
    assert parent["status"] == "failed"
    assert "parse failed" in parent["error_message"]


def test_delete_task_files_never_removes_paths_outside_managed_directories(task_db, runtime_paths, tmp_path):
    upload_file = runtime_paths["upload_path"] / "source.pdf"
    upload_file.write_text("source")
    result_directory = runtime_paths["output_path"] / "task-result"
    result_directory.mkdir()
    (result_directory / "result.md").write_text("result")
    external_file = tmp_path / "external.pdf"
    external_file.write_text("external")
    external_directory = tmp_path / "external-result"
    external_directory.mkdir()

    task_db.delete_task_files(
        {
            "task_id": "safe-task",
            "file_path": str(upload_file),
            "result_path": str(result_directory),
        }
    )
    task_db.delete_task_files(
        {
            "task_id": "unsafe-task",
            "file_path": str(external_file),
            "result_path": str(external_directory),
        }
    )

    assert not upload_file.exists()
    assert not result_directory.exists()
    assert external_file.exists()
    assert external_directory.exists()


def test_delete_task_files_can_preserve_source_for_retry(task_db, runtime_paths):
    upload_file = runtime_paths["upload_path"] / "source.pdf"
    upload_file.write_text("source")
    result_directory = runtime_paths["output_path"] / "task-result"
    result_directory.mkdir()

    task_db.delete_task_files(
        {
            "task_id": "retry-task",
            "file_path": str(upload_file),
            "result_path": str(result_directory),
        },
        include_source=False,
    )

    assert upload_file.exists()
    assert not result_directory.exists()
