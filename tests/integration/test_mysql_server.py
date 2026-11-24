import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from server.app.config import Settings
from server.app.db.base import Base
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
def test_real_mysql_api_bootstrap_crud_and_owner_isolation() -> None:
    settings = Settings(
        database_url=os.environ["MYCMD_MYSQL_TEST_URL"],
        signing_key="real-mysql-test-signing-key-at-least-32",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="real-mysql-bootstrap-token",
    )
    engine = make_engine(settings)
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
        assert bootstrap.status_code == 201
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
