import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-32-characters")
os.environ.setdefault("TIANSHU_ADMIN_PASSWORD", "test-admin-password")


@pytest.fixture
def runtime_paths(tmp_path, monkeypatch):
    database_path = tmp_path / "tianshu.db"
    upload_path = tmp_path / "uploads"
    output_path = tmp_path / "output"
    upload_path.mkdir()
    output_path.mkdir()

    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("UPLOAD_PATH", str(upload_path))
    monkeypatch.setenv("OUTPUT_PATH", str(output_path))
    monkeypatch.setenv("TIANSHU_ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("REDIS_QUEUE_ENABLED", "false")

    return {
        "database_path": database_path,
        "upload_path": upload_path,
        "output_path": output_path,
    }


@pytest.fixture
def task_db(runtime_paths):
    from task_db import TaskDB

    return TaskDB(runtime_paths["database_path"])


@pytest.fixture
def auth_db(runtime_paths):
    from auth.auth_db import AuthDB

    return AuthDB(str(runtime_paths["database_path"]))
