"""Environment-based server configuration."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    signing_key: str
    public_origin: str
    bootstrap_token: str
    access_minutes: int = 15
    refresh_days: int = 30
    environment: str = "development"

    @classmethod
    def load(cls) -> "Settings":
        database_url = os.getenv("DATABASE_URL", "").strip()
        signing_key = os.getenv("MYCMD_SECRET_KEY", "").strip()
        public_origin = os.getenv("MYCMD_PUBLIC_ORIGIN", "http://127.0.0.1:5173").strip()
        bootstrap_token = os.getenv("MYCMD_BOOTSTRAP_TOKEN", "").strip()
        environment = os.getenv("MYCMD_ENVIRONMENT", "development").strip() or "development"
        access_minutes = _int_setting("MYCMD_ACCESS_TOKEN_MINUTES", 15)
        refresh_days = _int_setting("MYCMD_REFRESH_TOKEN_DAYS", 30)
        if environment == "production":
            if not database_url:
                raise RuntimeError("DATABASE_URL is required in production")
            if not signing_key or len(signing_key) < 32:
                raise RuntimeError("MYCMD_SECRET_KEY must contain at least 32 characters")
        if not database_url:
            database_url = "sqlite+pysqlite:///" + str(
                Path(".tools/mycmd-phase6-test.sqlite3").resolve()
            ).replace("\\", "/")
        if "*" in public_origin:
            raise RuntimeError("Wildcard public origins are not allowed")
        if environment not in {"development", "staging", "production"}:
            raise RuntimeError("MYCMD_ENVIRONMENT must be development, staging or production")
        if not signing_key:
            signing_key = "development-only-signing-key-change-before-production"
        if not public_origin:
            raise RuntimeError("MYCMD_PUBLIC_ORIGIN cannot be empty")
        return cls(
            database_url=database_url,
            signing_key=signing_key,
            public_origin=public_origin,
            bootstrap_token=bootstrap_token,
            access_minutes=access_minutes,
            refresh_days=refresh_days,
            environment=environment,
        )


def _int_setting(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be positive")
    return parsed
