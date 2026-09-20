import importlib
import sys

from fastapi.testclient import TestClient

from auth.auth_db import AuthDB
from auth.jwt_handler import create_access_token
from auth.models import UserCreate, UserRole


def load_api_module():
    import auth.dependencies

    auth.dependencies._auth_db = None
    sys.modules.pop("api_server", None)
    return importlib.import_module("api_server")


def test_health_endpoint_returns_only_public_status(runtime_paths):
    api_server = load_api_module()

    with TestClient(api_server.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_output_file_route_requires_auth_and_rejects_escaped_paths(runtime_paths):
    auth_db = AuthDB(str(runtime_paths["database_path"]))
    admin = auth_db.create_user(
        UserCreate(
            username="privileged-user",
            email="privileged@example.com",
            password="safe-password",
            role=UserRole.ADMIN,
        )
    )
    token = create_access_token(admin.user_id, admin.username, admin.role)
    api_server = load_api_module()
    output_file = runtime_paths["output_path"] / "report.txt"
    output_file.write_text("safe output", encoding="utf-8")

    with TestClient(api_server.app) as client:
        unauthenticated = client.get("/api/v1/files/output/report.txt")
        escaped = client.get(
            "/api/v1/files/output/%2E%2E%2Foutside.txt",
            headers={"Authorization": f"Bearer {token}"},
        )
        valid = client.get("/api/v1/files/output/report.txt", headers={"Authorization": f"Bearer {token}"})

    assert unauthenticated.status_code == 401
    assert escaped.status_code == 404
    assert valid.status_code == 200
    assert valid.headers["x-content-type-options"] == "nosniff"
    assert valid.headers["content-security-policy"] == "default-src 'none'; sandbox"
    assert valid.headers["content-disposition"].startswith("attachment;")
