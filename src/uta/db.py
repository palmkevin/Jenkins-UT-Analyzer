"""Database engine/session wiring. The app reaches Postgres only via ``DATABASE_URL``."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    return create_engine(database_url, future=True, pool_pre_ping=True)


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def assert_pg_trgm(engine) -> None:
    """Raise RuntimeError if pg_trgm extension is absent (Postgres only; no-op on SQLite)."""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).fetchone()
        if row is None:
            raise RuntimeError(
                "pg_trgm extension is not installed. Run 'alembic upgrade head' to install it."
            )
