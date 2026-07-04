"""Database engine/session wiring. The app reaches Postgres only via ``DATABASE_URL``."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    return create_engine(database_url, future=True, pool_pre_ping=True)


class MissingExtensionError(RuntimeError):
    """Raised on startup when a required Postgres extension is not installed."""


def assert_pg_trgm(engine: Engine) -> None:
    """Assert the ``pg_trgm`` extension is present (KB fuzzy similarity).

    Created by an Alembic migration; this guards against a DB that skipped migrations. A no-op on
    non-Postgres engines (SQLite offline tests have no extensions and don't need this check).
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as conn:
        present = conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
    if not present:
        raise MissingExtensionError(
            "pg_trgm extension is not installed — run `uta migrate` (alembic upgrade head)."
        )


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
