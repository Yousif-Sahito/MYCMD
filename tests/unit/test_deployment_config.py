from pathlib import Path

import pytest

from server.app.config import Settings


def test_production_settings_require_mysql_https_and_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MYCMD_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://mycmd:test-only@mysql:3306/mycmd",
    )
    monkeypatch.setenv("MYCMD_SECRET_KEY", "phase10-production-signing-key-with-32-chars")
    monkeypatch.setenv("MYCMD_BOOTSTRAP_TOKEN", "phase10-production-bootstrap")
    monkeypatch.setenv("MYCMD_PUBLIC_ORIGIN", "https://portfolio.example.test")

    settings = Settings.load()
    assert settings.environment == "production"
    assert settings.public_origin.startswith("https://")


def test_production_settings_reject_http_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MYCMD_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://mycmd:test-only@mysql:3306/mycmd",
    )
    monkeypatch.setenv("MYCMD_SECRET_KEY", "phase10-production-signing-key-with-32-chars")
    monkeypatch.setenv("MYCMD_BOOTSTRAP_TOKEN", "phase10-production-bootstrap")
    monkeypatch.setenv("MYCMD_PUBLIC_ORIGIN", "http://portfolio.example.test")

    with pytest.raises(RuntimeError, match="HTTPS"):
        Settings.load()


def test_phase10_deployment_files_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "Dockerfile.api").is_file()
    assert (root / "Caddyfile").is_file()
    assert (root / "compose.production.yaml").is_file()
    assert (root / "scripts" / "deployment_check.py").is_file()
    assert (root / "scripts" / "mysql_backup.py").is_file()
    assert (root / "scripts" / "migration_rehearsal.py").is_file()
