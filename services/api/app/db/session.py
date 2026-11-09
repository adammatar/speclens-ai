"""SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create (cached) SQLAlchemy engine from settings."""
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection: object, _connection_record: object) -> None:
        register_vector(dbapi_connection)  # type: ignore[arg-type]

    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory bound to the app engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
