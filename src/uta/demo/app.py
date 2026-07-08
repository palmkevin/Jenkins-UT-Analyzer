"""Ephemeral, self-contained demo web app — the online-hosting entrypoint.

Builds a throwaway SQLite database, creates the schema, seeds it with the synthetic history
(:func:`uta.demo.seed.seed_demo_data`), and wires it into the real FastAPI app. No Postgres, no
``pg_trgm`` (the KB falls back to ``difflib``), no Jenkins/Oracle/SMTP/LLM — nothing external.

The store is a **fresh temp file per process**, re-seeded on startup, so the deployment is stateless
and reproducible: a restart wipes any demo edits and rebuilds the same dataset. Run it with::

    uvicorn uta.demo.app:app --host 0.0.0.0 --port 8000   # (Render supplies $PORT)

Tests build their own in-memory store and call :func:`create_demo_app` with that factory instead.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from uta.db import Base, make_session_factory
from uta.demo.seed import seed_demo_data
from uta.web.app import create_app


def build_demo_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """A session factory over a freshly-created, seeded store.

    With no ``database_url`` a temp-file SQLite is used (thread-safe under the threaded server, and
    ephemeral — gone when the container is reclaimed). Pass ``"sqlite+pysqlite:///:memory:"`` for an
    in-process store (tests): that needs a shared single connection, wired here automatically.
    """
    if database_url is None:
        db_path = Path(tempfile.mkdtemp(prefix="uta-demo-")) / "demo.db"
        database_url = f"sqlite+pysqlite:///{db_path}"

    if ":memory:" in database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    else:
        engine = create_engine(database_url, connect_args={"check_same_thread": False}, future=True)

    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    seed_demo_data(session_factory)
    return session_factory


def create_demo_app(database_url: str | None = None):
    """The FastAPI app backed by a fresh, seeded demo store.

    ``demo_mode=True`` locks down the control panel's mutations (issue #89): the demo is public and
    unauthenticated, so anonymous settings overrides — which degrade the shared store for every
    other visitor — and on-demand ingest — which would build a real Jenkins client and send
    outbound requests from the public host — return 403. The panel still renders fully populated,
    and triage actions stay live (the store is ephemeral).
    """
    return create_app(session_factory=build_demo_session_factory(database_url), demo_mode=True)


app = create_demo_app()
