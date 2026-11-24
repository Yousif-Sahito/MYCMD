"""Clean source/API startup and health smoke."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.app.config import Settings
from server.app.db.base import Base
from server.app.db.session import make_engine, make_session_factory
from server.app.main import create_app


def main() -> None:
    settings = Settings(
        database_url="sqlite+pysqlite:///.tools/phase6-api-smoke.sqlite3",
        signing_key="phase6-smoke-signing-key-at-least-32-characters",
        public_origin="http://127.0.0.1:5173",
        bootstrap_token="phase6-smoke-bootstrap-token",
    )
    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    app = create_app(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    with TestClient(app) as client:
        health = client.get("/health")
        openapi = client.get("/openapi.json")
        public = client.get("/api/v1/public/portfolio")
        if health.status_code != 200:
            raise RuntimeError("API health smoke failed")
        if openapi.status_code != 200:
            raise RuntimeError("OpenAPI smoke failed")
        if public.status_code != 200:
            raise RuntimeError("Public portfolio smoke failed")
    engine.dispose()
    print("Phase 6 API health, OpenAPI and public portfolio smoke passed")


if __name__ == "__main__":
    main()
