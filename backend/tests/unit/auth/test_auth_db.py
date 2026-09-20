from datetime import datetime, timedelta

import pytest

from auth.models import Permission, UserCreate, UserRole


def create_user(auth_db, username="alice", password="safe-password", email=None):
    return auth_db.create_user(
        UserCreate(
            username=username,
            email=email or f"{username}@example.com",
            password=password,
            role=UserRole.USER,
        )
    )


def test_authentication_requires_correct_password_and_stores_only_hash(auth_db):
    user = create_user(auth_db)

    assert auth_db.authenticate_user("alice", "safe-password").user_id == user.user_id
    assert auth_db.authenticate_user("alice", "wrong-password") is None

    with auth_db.get_cursor() as cursor:
        stored_hash = cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user.user_id,)).fetchone()[
            "password_hash"
        ]
    assert stored_hash != "safe-password"
    assert "$" in stored_hash


def test_duplicate_username_and_email_are_rejected(auth_db):
    create_user(auth_db)

    with pytest.raises(ValueError, match="Username"):
        create_user(auth_db, email="different@example.com")

    with pytest.raises(ValueError, match="Email"):
        auth_db.create_user(
            UserCreate(username="other", email="alice@example.com", password="safe-password", role=UserRole.USER)
        )


def test_api_key_is_scoped_and_database_never_stores_plaintext(auth_db):
    user = create_user(auth_db)
    issued = auth_db.create_api_key(user.user_id, "limited", scopes=[Permission.TASK_SUBMIT.value])

    authenticated = auth_db.verify_api_key(issued["api_key"])

    assert authenticated is not None
    assert authenticated.api_key_id == issued["key_id"]
    assert authenticated.has_permission(Permission.TASK_SUBMIT) is True
    assert authenticated.has_permission(Permission.TASK_VIEW_OWN) is False

    with auth_db.get_cursor() as cursor:
        row = cursor.execute("SELECT api_key_hash FROM api_keys WHERE key_id = ?", (issued["key_id"],)).fetchone()
    assert issued["api_key"] not in row["api_key_hash"]


def test_revoked_token_and_password_change_invalidate_prior_credentials(auth_db):
    user = create_user(auth_db)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    auth_db.revoke_token("token-1", user.user_id, expires_at)
    assert auth_db.is_token_revoked("token-1") is True

    assert auth_db.get_token_epoch(user.user_id) == 0
    assert auth_db.change_password(user.user_id, "safe-password", "new-safe-password") is True
    assert auth_db.get_token_epoch(user.user_id) == 1
    assert auth_db.authenticate_user("alice", "safe-password") is None
    assert auth_db.authenticate_user("alice", "new-safe-password") is not None
