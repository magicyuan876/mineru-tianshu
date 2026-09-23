import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from auth.auth_db import AuthDB
from auth.jwt_handler import create_access_token
from auth.models import UserCreate, UserRole


def load_api_module():
    import auth.dependencies

    auth.dependencies._auth_db = None
    sys.modules.pop("api_server", None)
    return importlib.import_module("api_server")


def make_token(runtime_paths, role):
    auth_db = AuthDB(str(runtime_paths["database_path"]))
    user = auth_db.create_user(
        UserCreate(
            username=f"cfg-{role.value}-user",
            email=f"cfg-{role.value}@example.com",
            password="safe-password",
            role=role,
        )
    )
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.username, user.role)}"}


def test_task_config_defaults_and_admin_update(runtime_paths):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()

    with TestClient(api_server.app) as client:
        default = client.get("/api/v1/auth/system/config/task", headers=headers)
        updated = client.post("/api/v1/auth/system/config", json={"task_max_retries": 5}, headers=headers)
        after = client.get("/api/v1/auth/system/config/task", headers=headers)

    assert default.status_code == 200
    assert default.json()["config"] == {"max_retries": 2, "max_retries_limit": 10}
    assert updated.status_code == 200
    assert after.json()["config"]["max_retries"] == 5


@pytest.mark.parametrize("bad_value", [-1, 11, "abc", True, 1.5, None])
def test_task_config_rejects_invalid_values(runtime_paths, bad_value):
    headers = make_token(runtime_paths, UserRole.ADMIN)
    api_server = load_api_module()

    with TestClient(api_server.app) as client:
        response = client.post("/api/v1/auth/system/config", json={"task_max_retries": bad_value}, headers=headers)
        after = client.get("/api/v1/auth/system/config/task", headers=headers)

    assert response.status_code == 400
    assert after.json()["config"]["max_retries"] == 2


def test_task_config_requires_admin(runtime_paths):
    headers = make_token(runtime_paths, UserRole.USER)
    api_server = load_api_module()

    with TestClient(api_server.app) as client:
        read = client.get("/api/v1/auth/system/config/task", headers=headers)
        write = client.post("/api/v1/auth/system/config", json={"task_max_retries": 5}, headers=headers)

    assert read.status_code == 403
    assert write.status_code == 403
