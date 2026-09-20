import hashlib
import hmac
import json
import socket

import pytest

from webhook import delivery


def test_validate_webhook_url_rejects_any_non_public_dns_answer(mocker):
    mocker.patch(
        "webhook.delivery.socket.getaddrinfo",
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )

    with pytest.raises(ValueError, match="non-public"):
        delivery.validate_webhook_url("https://example.com/hook")


@pytest.mark.parametrize("url", ["ftp://example.com/hook", "https:///hook"])
def test_validate_webhook_url_rejects_invalid_url_before_dns(url):
    with pytest.raises(ValueError):
        delivery.validate_webhook_url(url)


@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        ({"auth_type": "bearer", "auth_token": "token"}, {"Authorization": "Bearer token"}),
        (
            {"auth_type": "basic", "auth_username": "user", "auth_password": "pass"},
            {"Authorization": "Basic dXNlcjpwYXNz"},
        ),
        ({"auth_type": "api_key", "auth_header_name": "X-Key", "auth_header_value": "value"}, {"X-Key": "value"}),
        ({"auth_type": "api_key", "auth_header_name": "X Bad", "auth_header_value": "value"}, {}),
    ],
)
def test_build_auth_headers_only_allows_safe_configurations(auth, expected):
    assert delivery.build_auth_headers(auth) == expected


def test_post_webhook_signs_exact_json_body_and_disables_redirects_and_environment_proxy(mocker):
    captured = {}

    class FakeResponse:
        status_code = 204

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def post(self, url, content, headers):
            captured.update(url=url, content=content, headers=headers)
            return FakeResponse()

    mocker.patch("webhook.delivery.time.time", return_value=1_700_000_000)
    mocker.patch("webhook.delivery.httpx.Client", FakeClient)
    payload = {"event": "task.completed", "delivery_id": "delivery-1", "title": "中文"}

    assert delivery.post_webhook("https://example.com/hook", payload, secret="shared-secret") == 204

    expected_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    expected_signature = hmac.new(b"shared-secret", b"1700000000." + expected_body, hashlib.sha256).hexdigest()
    assert captured["client_kwargs"] == {"timeout": 10, "follow_redirects": False, "trust_env": False}
    assert captured["content"] == expected_body
    assert captured["headers"]["X-Tianshu-Signature"] == f"sha256={expected_signature}"


def test_failed_delivery_becomes_dead_after_max_attempts(runtime_paths):
    delivery_id = delivery.insert_delivery(
        "task-1", "task.failed", "https://example.com/hook", {"event": "task.failed"}
    )

    delivery.mark_retry_or_dead(delivery_id, attempts=3, max_attempts=3, error="failure" * 200)

    row = delivery.list_deliveries(status_filter="dead")[0][0]
    assert row["delivery_id"] == delivery_id
    assert row["attempts"] == 3
    assert len(row["last_error"]) == delivery.MAX_ERROR_LENGTH


def test_failed_delivery_schedules_retry_before_attempt_limit(runtime_paths):
    delivery_id = delivery.insert_delivery(
        "task-1", "task.failed", "https://example.com/hook", {"event": "task.failed"}
    )

    delivery.mark_retry_or_dead(delivery_id, attempts=1, max_attempts=3, error="temporary failure")

    due = delivery.fetch_due_deliveries()
    assert due == []
    rows, _ = delivery.list_deliveries(status_filter="pending")
    assert rows[0]["delivery_id"] == delivery_id
    assert rows[0]["attempts"] == 1
