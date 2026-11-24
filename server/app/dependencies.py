from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from server.app.auth_service import AuthService
from server.app.config import Settings
from server.app.db.models import User


def get_settings(request: Request) -> Settings:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings are unavailable")
    return settings


def get_db(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    db = factory()
    try:
        yield db
    finally:
        db.close()


def current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return AuthService(db, request.app.state.settings).user_from_access(token)
    except LookupError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
