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
            "pg_trgm extension is not installed — build `uta migrate` (alembic upgrade head)."
        )


# Arbitrary, stable key for the ingest advisory lock ("uta" + "i"ngest as bytes).
INGEST_LOCK_KEY = 0x75746169


def acquire_ingest_lock(session: Session) -> None:
    """Serialise build ingests across processes: a Postgres transaction-scoped advisory lock.

    The poller and control-panel ingest jobs (another process) both write the same lifecycle /
    episode rows; without this two concurrent ingests lose updates or hit unique violations. The
    lock is released automatically when the session's transaction commits or rolls back. A no-op
    on other dialects (SQLite tests are single-process and serialise writes anyway).
    """
    if session.get_bind().dialect.name != "postgresql":
        return
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": INGEST_LOCK_KEY})


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
