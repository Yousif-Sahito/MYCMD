from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.config import Settings


def make_engine(settings: Settings) -> Engine:
    url = settings.database_url
    if url.startswith("mysql"):
        return create_engine(url, pool_pre_ping=True, pool_recycle=280)
    return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(factory: sessionmaker[Session]) -> Iterator[Session]:
    db = factory()
    try:
        yield db
    finally:
        db.close()
