import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        ph.verify(password_hash, password)
        return True
    except Exception:
        return False


def access_token(user_id: str, signing_key: str, minutes: int) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
            "jti": str(uuid4()),
        },
        signing_key,
        algorithm="HS256",
    )


def decode_access(token: str, signing_key: str) -> str:
    payload = jwt.decode(token, signing_key, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Expected access token")
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("Missing subject")
    return subject


def refresh_token() -> str:
    return str(uuid4()) + "-" + str(uuid4())


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
