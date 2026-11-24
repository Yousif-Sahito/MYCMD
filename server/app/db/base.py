from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def uuid_text() -> str:
    return str(uuid4())
