from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app.api.routes import limiter
from server.app.config import Settings
from server.app.db.base import Base
from server.app.db.session import make_engine, make_session_factory
from server.app.main import create_app


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    limiter.reset()
    database = tmp_path / "phase6.sqlite3"
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{database}",
        signing_key="phase6-test-signing-key-32-characters",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="phase6-bootstrap-test-token",
    )
    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    with TestClient(app) as client:
        yield client
    engine.dispose()


def auth(api: TestClient) -> dict[str, str]:
    bootstrap = api.post(
        "/api/v1/auth/bootstrap",
        json={
            "bootstrap_token": "phase6-bootstrap-test-token",
            "email": "owner@example.test",
            "password": "long-test-password",
        },
    )
    assert bootstrap.status_code == 201
    login = api.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.test", "password": "long-test-password"},
    )
    assert login.status_code == 200
    tokens = login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_health_and_public_portfolio(api: TestClient) -> None:
    health = api.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ready"
    public = api.get("/api/v1/public/portfolio")
    assert public.status_code == 200
    assert public.json()["source"] == "curated-public"
    assert "password_hash" not in public.text


def test_bootstrap_login_me_refresh_logout(api: TestClient) -> None:
    headers = auth(api)
    me = api.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    login = api.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.test", "password": "long-test-password"},
    )
    refresh_token = login.json()["refresh_token"]
    refreshed = api.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    replay = api.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay.status_code == 401
    logout = api.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logout.status_code == 204


def test_owner_project_crud_conflict_and_pagination(api: TestClient) -> None:
    headers = auth(api)
    created = api.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "data": {
                "slug": "phase6-api",
                "title": "Phase 6 API",
                "status": "active",
                "technologies": ["FastAPI", "MySQL"],
                "links": [],
            }
        },
    )
    assert created.status_code == 201
    record = created.json()
    listed = api.get("/api/v1/projects?page=1&page_size=20", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    updated = api.patch(
        f"/api/v1/projects/{record['id']}",
        headers=headers,
        json={
            "expected_version": 1,
            "data": {"notes": "Owner update", "description": "Verified"},
        },
    )
    assert updated.status_code == 200
    stale = api.patch(
        f"/api/v1/projects/{record['id']}",
        headers=headers,
        json={"expected_version": 1, "data": {"notes": "Stale"}},
    )
    assert stale.status_code == 409
    deleted = api.delete(
        f"/api/v1/projects/{record['id']}?expected_version=2",
        headers=headers,
    )
    assert deleted.status_code == 204
    repeated = api.delete(
        f"/api/v1/projects/{record['id']}?expected_version=3",
        headers=headers,
    )
    assert repeated.status_code == 404


def test_cross_owner_and_unauthorized(api: TestClient) -> None:
    unauthenticated = api.get("/api/v1/projects")
    assert unauthenticated.status_code == 401
    headers = auth(api)
    result = api.get("/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=headers)
    assert result.status_code == 404


def test_malformed_json_validation_and_logout_owner_scope(api: TestClient) -> None:
    malformed = api.post(
        "/api/v1/auth/login",
        content="{",
        headers={"content-type": "application/json"},
    )
    assert malformed.status_code == 422
    auth(api)
    api.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.test", "password": "long-test-password"},
    )


def test_cors_public_origin_and_rate_limit_shape(api: TestClient) -> None:
    allowed = api.get(
        "/api/v1/public/portfolio",
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    assert allowed.status_code == 200
    assert "access-control-allow-origin" in allowed.headers
    disallowed = api.get(
        "/api/v1/public/portfolio",
        headers={"Origin": "https://attacker.example"},
    )
    assert disallowed.status_code == 200
    assert "access-control-allow-origin" not in disallowed.headers


def test_sync_push_pull_duplicate_and_conflict(api: TestClient) -> None:
    headers = auth(api)
    operation_id = "11111111-1111-4111-8111-111111111111"
    entity_id = "22222222-2222-4222-8222-222222222222"
    device_id = "33333333-3333-4333-8333-333333333333"
    operation = {
        "operation_id": operation_id,
        "device_id": device_id,
        "entity_type": "projects",
        "entity_id": entity_id,
        "action": "create",
        "base_version": 0,
        "payload": {
            "slug": "sync-project",
            "title": "Sync Project",
            "status": "active",
            "technologies": [],
            "links": [],
        },
    }
    pushed = api.post(
        "/api/v1/sync/push",
        headers=headers,
        json={"operations": [operation]},
    )
    assert pushed.status_code == 200
    first = pushed.json()["results"][0]
    assert first["status"] == "accepted"

    repeated = api.post(
        "/api/v1/sync/push",
        headers=headers,
        json={"operations": [operation]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["results"][0]["status"] == "accepted"
    assert repeated.json()["results"][0] == first

    server_edit = api.patch(
        f"/api/v1/projects/{entity_id}",
        headers=headers,
        json={
            "expected_version": 1,
            "data": {"notes": "Server won first"},
        },
    )
    assert server_edit.status_code == 200

    stale_update = dict(operation)
    stale_update.update(
        {
            "operation_id": "44444444-4444-4444-8444-444444444444",
            "action": "update",
            "base_version": 1,
            "payload": {"notes": "stale"},
        }
    )
    conflict = api.post(
        "/api/v1/sync/push",
        headers=headers,
        json={"operations": [stale_update]},
    )
    assert conflict.status_code == 200
    assert conflict.json()["results"][0]["status"] == "conflict"

    pulled = api.get(
        "/api/v1/sync/pull?cursor=0&limit=100",
        headers=headers,
    )
    assert pulled.status_code == 200
    body = pulled.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["entity_id"] == entity_id
    assert body["next_cursor"] >= 1
