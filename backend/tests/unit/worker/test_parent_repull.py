from tests.unit.worker.test_routing import load_worker_module, make_worker


def repulled_parent(tmp_path):
    source = tmp_path / "big.pdf"
    source.write_bytes(b"%PDF-1.4")
    return {
        "task_id": "parent-1",
        "file_path": str(source),
        "backend": "auto",
        "options": "{}",
        "is_parent": 1,
        "child_count": 3,
    }


def test_repulled_parent_with_all_children_completed_is_merged(monkeypatch, mocker, tmp_path):
    worker = make_worker(load_worker_module(monkeypatch), mocker)
    worker.task_db.all_children_completed.return_value = True
    worker._merge_parent_task_results = mocker.Mock()

    worker._process_task(repulled_parent(tmp_path))

    worker._merge_parent_task_results.assert_called_once_with("parent-1")
    worker._should_split_pdf.assert_not_called()
    worker._process_with_mineru.assert_not_called()


def test_repulled_parent_with_unfinished_children_is_not_resplit(monkeypatch, mocker, tmp_path):
    worker = make_worker(load_worker_module(monkeypatch), mocker)
    worker.task_db.all_children_completed.return_value = False
    worker._merge_parent_task_results = mocker.Mock()

    worker._process_task(repulled_parent(tmp_path))

    worker._merge_parent_task_results.assert_not_called()
    worker._should_split_pdf.assert_not_called()
    worker._process_with_mineru.assert_not_called()


def test_merge_failure_marks_parent_failed_and_notifies(monkeypatch, mocker, tmp_path):
    worker = make_worker(load_worker_module(monkeypatch), mocker)
    worker.task_db.all_children_completed.return_value = True
    worker._merge_parent_task_results = mocker.Mock(side_effect=RuntimeError("disk full"))

    worker._process_task(repulled_parent(tmp_path))

    worker.task_db.update_task_status.assert_called_once_with("parent-1", "failed", error_message="disk full")
    worker._enqueue_webhook.assert_called_once_with("parent-1", "task.failed")
