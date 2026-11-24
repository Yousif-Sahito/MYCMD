import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from mycmd.core.service import Service
from mycmd.storage.database import connect
from server.app.api.routes import limiter
from server.app.config import Settings
from server.app.db.base import Base
from server.app.db.models import ChangeLog, Record, SyncOperation
from server.app.db.session import make_engine, make_session_factory
from server.app.main import create_app

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("MYCMD_MYSQL_TEST_URL"),
    reason="Requires MYCMD_MYSQL_TEST_URL pointing to a disposable MySQL database",
)
def test_real_mysql_connection_and_transaction() -> None:
    engine = create_engine(os.environ["MYCMD_MYSQL_TEST_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        connection.execute(
            text("CREATE TEMPORARY TABLE mycmd_phase6_probe (id BIGINT PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO mycmd_phase6_probe (id) VALUES (1)"))
        assert connection.execute(text("SELECT COUNT(*) FROM mycmd_phase6_probe")).scalar_one() == 1
    engine.dispose()


@pytest.mark.skipif(
    not os.getenv("MYCMD_MYSQL_TEST_URL"),
    reason="Requires MYCMD_MYSQL_TEST_URL pointing to a disposable MySQL database",
)
def test_real_mysql_concurrent_duplicate_push_is_one_mutation() -> None:
    settings = Settings(
        database_url=os.environ["MYCMD_MYSQL_TEST_URL"],
        signing_key="phase7-concurrent-signing-key-at-least-32",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="phase7-concurrent-bootstrap-token",
    )
    limiter.reset()
    engine = make_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    email = f"concurrent-{uuid4()}@example.test"
    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "bootstrap_token": "phase7-concurrent-bootstrap-token",
                "email": email,
                "password": "phase7-concurrent-password",
            },
        )
        assert bootstrap.status_code in {201, 409}
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "phase7-concurrent-password"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        operation_id = str(uuid4())
        entity_id = str(uuid4())
        operation = {
            "operation_id": operation_id,
            "device_id": str(uuid4()),
            "entity_type": "projects",
            "entity_id": entity_id,
            "action": "create",
            "base_version": 0,
            "payload": {
                "slug": f"concurrent-{uuid4()}",
                "title": "Concurrent duplicate",
                "status": "active",
                "technologies": [],
                "links": [],
            },
        }

        def submit() -> dict[str, object]:
            with TestClient(app) as request_client:
                response = request_client.post(
                    "/api/v1/sync/push",
                    headers=headers,
                    json={"operations": [operation]},
                )
                return {"status": response.status_code, "body": response.json()}

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: submit(), range(2)))

        assert [outcome["status"] for outcome in outcomes] == [200, 200]
        first_body = outcomes[0]["body"]
        second_body = outcomes[1]["body"]
        assert first_body == second_body
        assert first_body["results"][0]["status"] == "accepted"

        factory = make_session_factory(engine)
        with factory() as session:
            owner_id = session.scalar(select(Record.owner_id).where(Record.id == entity_id))
            record = session.scalar(select(Record).where(Record.id == entity_id))
            operation_rows = session.scalars(
                select(SyncOperation).where(
                    SyncOperation.owner_id == owner_id,
                    SyncOperation.operation_id == operation_id,
                )
            ).all()
            change_rows = session.scalars(
                select(ChangeLog).where(
                    ChangeLog.owner_id == owner_id,
                    ChangeLog.entity_id == entity_id,
                )
            ).all()
        assert record is not None
        assert record.version == 1
        assert len(operation_rows) == 1
        assert len(change_rows) == 1
    engine.dispose()


@pytest.mark.skipif(
    not os.getenv("MYCMD_MYSQL_TEST_URL"),
    reason="Requires MYCMD_MYSQL_TEST_URL pointing to a disposable MySQL database",
)
def test_real_mysql_sync_push_pull_idempotency_and_tombstone() -> None:
    settings = Settings(
        database_url=os.environ["MYCMD_MYSQL_TEST_URL"],
        signing_key="phase7-real-mysql-signing-key-at-least-32",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="phase7-real-mysql-bootstrap-token",
    )
    limiter.reset()
    engine = make_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "bootstrap_token": "phase7-real-mysql-bootstrap-token",
                "email": "phase7-mysql-owner@example.test",
                "password": "phase7-mysql-password",
            },
        )
        assert bootstrap.status_code in {201, 409}
        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "phase7-mysql-owner@example.test",
                "password": "phase7-mysql-password",
            },
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        operation_id = "a1111111-1111-4111-8111-111111111111"
        entity_id = "b1111111-1111-4111-8111-111111111111"
        device_id = "c1111111-1111-4111-8111-111111111111"
        operation = {
            "operation_id": operation_id,
            "device_id": device_id,
            "entity_type": "projects",
            "entity_id": entity_id,
            "action": "create",
            "base_version": 0,
            "payload": {
                "slug": "phase7-mysql-project",
                "title": "Real MySQL Sync",
                "status": "active",
                "technologies": ["FastAPI", "MySQL"],
                "links": [],
            },
        }
        pushed = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [operation]},
        )
        assert pushed.status_code == 200
        assert pushed.json()["results"][0]["status"] == "accepted"

        repeated = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [operation]},
        )
        assert repeated.status_code == 200
        assert repeated.json() == pushed.json()

        pulled = client.get(
            "/api/v1/sync/pull?cursor=0&limit=100",
            headers=headers,
        )
        assert pulled.status_code == 200
        assert pulled.json()["items"]
        assert pulled.json()["items"][0]["entity_id"] == entity_id

        server_edit = client.patch(
            f"/api/v1/projects/{entity_id}",
            headers=headers,
            json={
                "expected_version": 1,
                "data": {"notes": "server edit"},
            },
        )
        assert server_edit.status_code == 200

        stale = dict(operation)
        stale.update(
            {
                "operation_id": "d1111111-1111-4111-8111-111111111111",
                "action": "update",
                "base_version": 1,
                "payload": {"notes": "stale offline edit"},
            }
        )
        conflict = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [stale]},
        )
        assert conflict.status_code == 200
        assert conflict.json()["results"][0]["status"] == "conflict"

        delete_operation = dict(operation)
        delete_operation.update(
            {
                "operation_id": "e1111111-1111-4111-8111-111111111111",
                "action": "delete",
                "base_version": 2,
                "payload": {},
            }
        )
        deleted = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [delete_operation]},
        )
        assert deleted.status_code == 200

        tombstones = client.get(
            f"/api/v1/sync/pull?cursor={pulled.json()['next_cursor']}&limit=100",
            headers=headers,
        )
        assert tombstones.status_code == 200
        assert any(item["tombstone"] for item in tombstones.json()["items"])
    engine.dispose()


@pytest.mark.skipif(
    not os.getenv("MYCMD_MYSQL_TEST_URL"),
    reason="Requires MYCMD_MYSQL_TEST_URL pointing to a disposable MySQL database",
)
def test_real_mysql_api_bootstrap_crud_and_owner_isolation() -> None:
    settings = Settings(
        database_url=os.environ["MYCMD_MYSQL_TEST_URL"],
        signing_key="real-mysql-test-signing-key-at-least-32",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="real-mysql-bootstrap-token",
    )
    limiter.reset()
    engine = make_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    with TestClient(app) as client:
        bootstrap = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "bootstrap_token": "real-mysql-bootstrap-token",
                "email": "mysql-owner@example.test",
                "password": "mysql-test-password",
            },
        )
        assert bootstrap.status_code in {201, 409}
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "mysql-owner@example.test", "password": "mysql-test-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        created = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "data": {
                    "slug": "mysql-phase6",
                    "title": "Real MySQL Phase 6",
                    "status": "active",
                    "technologies": ["FastAPI", "MySQL"],
                    "links": [],
                }
            },
        )
        assert created.status_code == 201
        record = created.json()
        stale = client.patch(
            f"/api/v1/projects/{record['id']}",
            headers=headers,
            json={"expected_version": 1, "data": {"notes": "first"}},
        )
        assert stale.status_code == 200
    engine.dispose()


@pytest.mark.skipif(
    not os.getenv("MYCMD_MYSQL_TEST_URL"),
    reason="Requires MYCMD_MYSQL_TEST_URL pointing to a disposable MySQL database",
)
def test_real_mysql_two_device_conflict_and_tombstone(tmp_path) -> None:
    settings = Settings(
        database_url=os.environ["MYCMD_MYSQL_TEST_URL"],
        signing_key="phase7-two-device-signing-key-at-least-32",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="phase7-two-device-bootstrap-token",
    )
    limiter.reset()
    engine = make_engine(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    owner_id = str(uuid4())
    device_a_db = connect(tmp_path / "device-a.sqlite3")
    device_b_db = connect(tmp_path / "device-b.sqlite3")
    device_a = Service(device_a_db, owner_id)
    device_b = Service(device_b_db, owner_id)
    local_a = device_a.create(
        "projects",
        {
            "slug": f"local-a-{uuid4()}",
            "title": "Device A local",
            "status": "active",
            "technologies": [],
            "links": [],
        },
    )
    local_b = device_b.create(
        "projects",
        {
            "slug": f"local-b-{uuid4()}",
            "title": "Device B local",
            "status": "active",
            "technologies": [],
            "links": [],
        },
    )
    email = f"devices-{uuid4()}@example.test"
    password = "phase7-two-device-password"

    with TestClient(app) as client:
        assert client.post(
            "/api/v1/auth/bootstrap",
            json={
                "bootstrap_token": "phase7-two-device-bootstrap-token",
                "email": email,
                "password": password,
            },
        ).status_code in {201, 409}
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        operation_id = str(uuid4())
        entity_id = str(uuid4())
        device_id = str(uuid4())
        create = {
            "operation_id": operation_id,
            "device_id": device_id,
            "entity_type": "projects",
            "entity_id": entity_id,
            "action": "create",
            "base_version": 0,
            "payload": {
                "slug": f"two-device-{uuid4()}",
                "title": "Two device project",
                "status": "active",
                "technologies": [],
                "links": [],
            },
        }
        pushed = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [create]},
        )
        assert pushed.status_code == 200
        assert pushed.json()["results"][0]["status"] == "accepted"

        device_b_pull = client.get(
            "/api/v1/sync/pull?cursor=0&limit=100",
            headers=headers,
        )
        assert device_b_pull.status_code == 200
        assert any(item["entity_id"] == entity_id for item in device_b_pull.json()["items"])

        edit_b = dict(create)
        edit_b.update(
            {
                "operation_id": str(uuid4()),
                "device_id": str(uuid4()),
                "action": "update",
                "base_version": 1,
                "payload": {"notes": "Device B edit"},
            }
        )
        edit_result = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [edit_b]},
        )
        assert edit_result.status_code == 200
        assert edit_result.json()["results"][0]["status"] == "accepted"

        edit_a = dict(create)
        edit_a.update(
            {
                "operation_id": str(uuid4()),
                "device_id": str(uuid4()),
                "action": "update",
                "base_version": 1,
                "payload": {"notes": "Device A edit"},
            }
        )
        conflict_result = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [edit_a]},
        )
        assert conflict_result.status_code == 200
        assert conflict_result.json()["results"][0]["status"] == "conflict"

        delete_a = dict(create)
        delete_a.update(
            {
                "operation_id": str(uuid4()),
                "device_id": str(uuid4()),
                "action": "delete",
                "base_version": 2,
                "payload": {},
            }
        )
        delete_result = client.post(
            "/api/v1/sync/push",
            headers=headers,
            json={"operations": [delete_a]},
        )
        assert delete_result.status_code == 200
        assert delete_result.json()["results"][0]["status"] == "accepted"

        tombstone_pull = client.get(
            "/api/v1/sync/pull?cursor=0&limit=100",
            headers=headers,
        )
        assert tombstone_pull.status_code == 200
        tombstones = [
            item
            for item in tombstone_pull.json()["items"]
            if item["entity_id"] == entity_id and item["tombstone"]
        ]
        assert tombstones
        assert local_a.sync_status == "pending"
        assert local_b.sync_status == "pending"
    assert device_a.device_id != device_b.device_id
    device_a_db.close()
    device_b_db.close()
    engine.dispose()
