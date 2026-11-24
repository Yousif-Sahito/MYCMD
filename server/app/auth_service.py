from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.app.config import Settings
from server.app.db.models import RefreshSession, User
from server.app.security import (
    access_token,
    decode_access,
    hash_password,
    refresh_hash,
    refresh_token,
    verify_password,
)


class AuthService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings

    def bootstrap(self, email: str, password: str, bootstrap_token: str) -> User:
        if not self.settings.bootstrap_token or bootstrap_token != self.settings.bootstrap_token:
            raise PermissionError("Invalid bootstrap token")
        existing = self.db.scalar(select(User).limit(1))
        if existing is not None:
            raise LookupError("Initial owner already exists")
        email = email.strip().lower()
        if self.db.scalar(select(User).where(User.email == email)) is not None:
            raise LookupError("Initial owner already exists")
        user = User(email=email, password_hash=hash_password(password), status="active")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.db.scalar(select(User).where(User.email == email.strip().lower()))
        if (
            user is None
            or user.status != "active"
            or not verify_password(user.password_hash, password)
        ):
            raise LookupError("Invalid credentials")
        access = access_token(user.id, self.settings.signing_key, self.settings.access_minutes)
        refresh = refresh_token()
        session = RefreshSession(
            user_id=user.id,
            token_hash=refresh_hash(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_days),
        )
        self.db.add(session)
        self.db.commit()
        return user, access, refresh

    def refresh(self, refresh: str) -> tuple[User, str, str]:
        digest = refresh_hash(refresh)
        session = self.db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == digest).with_for_update()
        )
        if session is None or session.revoked_at is not None:
            raise LookupError("Refresh session is invalid")
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            raise LookupError("Refresh session is expired")
        user = self.db.get(User, session.user_id)
        if user is None or user.status != "active":
            raise LookupError("Refresh session is invalid")
        session.revoked_at = datetime.now(UTC)
        access = access_token(user.id, self.settings.signing_key, self.settings.access_minutes)
        new_refresh = refresh_token()
        new_session = RefreshSession(
            user_id=user.id,
            token_hash=refresh_hash(new_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_days),
        )
        self.db.add(new_session)
        self.db.commit()
        return user, access, new_refresh

    def revoke(self, refresh: str) -> None:
        session = self.db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == refresh_hash(refresh))
        )
        if session is None:
            return
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def revoke_for_user(self, user_id: str, refresh: str) -> None:
        session = self.db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == refresh_hash(refresh))
        )
        if session is None:
            return
        if session.user_id != user_id:
            raise PermissionError("Refresh session belongs to another user")
        if session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def user_from_access(self, token: str) -> User:
        try:
            user_id = decode_access(token, self.settings.signing_key)
        except (jwt.InvalidTokenError, jwt.DecodeError) as exc:
            raise LookupError("Invalid access token") from exc
        user = self.db.get(User, user_id)
        if user is None or user.status != "active":
            raise LookupError("Invalid access token")
        return user
