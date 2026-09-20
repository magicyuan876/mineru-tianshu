from webhook import dispatcher


def test_build_task_payload_excludes_parsed_content():
    payload = dispatcher.build_task_payload(
        {
            "task_id": "task-1",
            "file_name": "report.pdf",
            "data": '{"markdown":"secret parsed content"}',
            "result_path": "/output/task-1",
        },
        "task.completed",
    )

    assert payload["result_url"] == "/api/v1/tasks/task-1"
    assert "data" not in payload
    assert "markdown" not in payload


def test_enqueue_task_event_routes_task_and_api_key_webhooks(mocker):
    task_db = mocker.Mock()
    task_db.get_task.return_value = {
        "task_id": "task-1",
        "file_name": "report.pdf",
        "options": '{"webhook_url":"https://task.example/hook"}',
        "api_key_id": "key-1",
    }
    insert_delivery = mocker.patch("webhook.dispatcher.delivery.insert_delivery")
    mocker.patch(
        "webhook.dispatcher.delivery.get_key_webhook",
        return_value={"enabled": True, "url": "https://key.example/hook"},
    )

    dispatcher.enqueue_task_event(task_db, "task-1", "task.completed")

    assert insert_delivery.call_count == 2
    assert {call.kwargs["source"] for call in insert_delivery.call_args_list} == {"task", "api_key"}


def test_key_webhook_disabled_after_enqueue_marks_delivery_dead(mocker):
    row = {
        "delivery_id": "delivery-1",
        "url": "https://key.example/hook",
        "payload": '{"event":"task.completed"}',
        "source": "api_key",
        "api_key_id": "key-1",
    }
    mark_dead = mocker.patch("webhook.dispatcher.delivery.mark_dead")
    mocker.patch("webhook.dispatcher.delivery.get_key_webhook", return_value=None)

    assert dispatcher.deliver_delivery(row, {"timeout": 10, "max_attempts": 3}) is False

    mark_dead.assert_called_once_with("delivery-1", "API key webhook disabled or key removed")


def test_ssrf_failure_marks_delivery_dead_without_http_request(mocker):
    row = {
        "delivery_id": "delivery-1",
        "url": "https://internal.example/hook",
        "payload": '{"event":"task.completed"}',
        "source": "task",
        "attempts": 0,
    }
    mocker.patch("webhook.dispatcher.delivery.validate_webhook_url", side_effect=ValueError("private address"))
    mark_dead = mocker.patch("webhook.dispatcher.delivery.mark_dead")
    post_webhook = mocker.patch("webhook.dispatcher.delivery.post_webhook")

    assert dispatcher.deliver_delivery(row, {"timeout": 10, "max_attempts": 3}) is False

    mark_dead.assert_called_once_with("delivery-1", "SSRF check failed: private address")
    post_webhook.assert_not_called()


def test_http_failure_records_retry_and_success_marks_delivered(mocker):
    row = {
        "delivery_id": "delivery-1",
        "url": "https://public.example/hook",
        "payload": '{"event":"task.completed"}',
        "source": "task",
        "attempts": 1,
    }
    mocker.patch("webhook.dispatcher.delivery.validate_webhook_url")
    retry = mocker.patch("webhook.dispatcher.delivery.mark_retry_or_dead")
    mocker.patch("webhook.dispatcher.delivery.post_webhook", return_value=503)

    assert dispatcher.deliver_delivery(row, {"timeout": 10, "max_attempts": 3}) is False
    retry.assert_called_once_with("delivery-1", 2, 3, "HTTP 503")

    delivered = mocker.patch("webhook.dispatcher.delivery.mark_delivered")
    mocker.patch("webhook.dispatcher.delivery.post_webhook", return_value=204)

    assert dispatcher.deliver_delivery(row, {"timeout": 10, "max_attempts": 3}) is True
    delivered.assert_called_once_with("delivery-1")
