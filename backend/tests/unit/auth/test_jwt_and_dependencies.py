from datetime import datetime, timedelta

from auth.dependencies import _authenticate_jwt
from auth.jwt_handler import create_access_token, decode_token_payload, verify_token
from auth.models import UserCreate, UserRole


def test_jwt_round_trip_and_invalid_signature_are_rejected(auth_db):
    user = auth_db.create_user(
        UserCreate(username="alice", email="alice@example.com", password="safe-password", role=UserRole.USER)
    )
    token = create_access_token(user.user_id, user.username, UserRole.USER)

    token_data = verify_token(token)

    assert token_data.user_id == user.user_id
    assert verify_token(f"{token}invalid") is None


def test_expired_jwt_is_rejected():
    token = create_access_token("user-1", "alice", UserRole.USER, expires_delta=timedelta(seconds=-1))

    assert verify_token(token) is None
    assert decode_token_payload(token) is None


def test_authentication_rejects_revoked_and_outdated_token_epochs(auth_db):
    user = auth_db.create_user(
        UserCreate(username="alice", email="alice@example.com", password="safe-password", role=UserRole.USER)
    )
    token = create_access_token(user.user_id, user.username, user.role)
    payload = decode_token_payload(token)

    assert _authenticate_jwt(token, auth_db).user_id == user.user_id

    auth_db.revoke_token(payload["jti"], user.user_id, datetime.utcnow() + timedelta(hours=1))
    assert _authenticate_jwt(token, auth_db) is None

    fresh_token = create_access_token(user.user_id, user.username, user.role)
    assert auth_db.change_password(user.user_id, "safe-password", "new-safe-password") is True
    assert _authenticate_jwt(fresh_token, auth_db) is None
