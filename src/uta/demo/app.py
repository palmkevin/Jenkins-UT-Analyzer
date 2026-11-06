"""Ephemeral, self-contained demo web app — the online-hosting entrypoint.

Builds a throwaway SQLite database, creates the schema, seeds it with the synthetic history
(:func:`uta.demo.seed.seed_demo_data`), and wires it into the real FastAPI app. No Postgres, no
``pg_trgm`` (the KB falls back to ``difflib``), no Jenkins/Oracle/SMTP/LLM — nothing external.

The store is a **fresh temp-file SQLite per process** (not in-memory: the threaded server needs a
file every connection can open), seeded once on first use, so the deployment is stateless and
reproducible: a restart wipes any demo edits and rebuilds the same dataset. The temp directory is
removed at interpreter exit. Build it with::

    uvicorn uta.demo.app:app --host 0.0.0.0 --port 8000   # (Render supplies $PORT)

``app`` is resolved **lazily** (a module ``__getattr__``), so merely importing this module — as the
tests and ``uta demo`` do — seeds nothing; the first access to ``uta.demo.app.app`` (or
:func:`get_demo_app`) builds and seeds the one per-process app. Tests build their own in-memory
store and call :func:`create_demo_app` with that factory instead.
"""

from __future__ import annotations

import atexit
import shutil
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from uta.control.heartbeat import read_heartbeat
from uta.db import Base, make_session_factory, session_scope
from uta.demo.seed import seed_demo_data
from uta.web.app import create_app


def build_demo_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """A session factory over a freshly-created, seeded store.

    With no ``database_url`` a temp-file SQLite is used (thread-safe under the threaded server, and
    ephemeral — its directory is removed at interpreter exit). Pass
    ``"sqlite+pysqlite:///:memory:"`` for an in-process store (tests): that needs a shared single
    connection, wired here automatically.
    """
    temp_dir: str | None = None
    if database_url is None:
        temp_dir = tempfile.mkdtemp(prefix="uta-demo-")
        database_url = f"sqlite+pysqlite:///{Path(temp_dir) / 'demo.db'}"

    if ":memory:" in database_url:
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    else:
        engine = create_engine(database_url, connect_args={"check_same_thread": False}, future=True)
    if temp_dir is not None:
        atexit.register(_remove_temp_store, engine, temp_dir)

    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    seed_demo_data(session_factory)
    return session_factory


def _remove_temp_store(engine: Engine, temp_dir: str) -> None:
    """Close the engine's connections and delete the throwaway store's temp directory."""
    engine.dispose()
    shutil.rmtree(temp_dir, ignore_errors=True)


def _freshen_heartbeat(session_factory: sessionmaker[Session]) -> None:
    """Re-stamp the seeded heartbeat's freshness so the demo's ``/health`` never goes stale.

    The demo runs no poller, so the heartbeat seeded for the ``/control`` panel would otherwise
    cross the staleness window (``poll_interval_seconds × poller_stale_after_intervals``, ~21 min
    with defaults) and flip ``/health`` to 503 — and Render's ``healthCheckPath`` would then
    restart the service, wiping the ephemeral store mid-session (issue #125). Only the timestamps
    move; the seeded tick details (processed builds, count) stay as the panel shows them.
    """
    now = datetime.now(UTC)
    with session_scope(session_factory) as session:
        hb = read_heartbeat(session)
        if hb is not None:
            hb.last_poll_at = now
            hb.last_success_at = now


def create_demo_app(
    database_url: str | None = None, session_factory: sessionmaker[Session] | None = None
):
    """The FastAPI app backed by a fresh, seeded demo store.

    ``demo_mode=True`` locks down the control panel's mutations (issue #89): the demo is public and
    unauthenticated, so anonymous settings overrides — which degrade the shared store for every
    other visitor — and on-demand ingest — which would build a real Jenkins client and send
    outbound requests from the public host — return 403. The panel still renders fully populated,
    and triage actions stay live (the store is ephemeral).

    Every ``/health`` probe re-stamps the seeded poller heartbeat first (see
    :func:`_freshen_heartbeat`), so the pollerless demo stays healthy for the process's whole
    lifetime — staleness detection for real deployments is untouched.
    """
    factory = session_factory or build_demo_session_factory(database_url)
    app = create_app(session_factory=factory, demo_mode=True)

    @app.middleware("http")
    async def keep_heartbeat_fresh(request: Request, call_next):
        if request.url.path == "/health":
            _freshen_heartbeat(factory)
        return await call_next(request)

    return app


_app = None
_app_lock = threading.Lock()


def get_demo_app():
    """The process's one demo app — built and seeded on first call, reused after (thread-safe)."""
    global _app
    with _app_lock:
        if _app is None:
            _app = create_demo_app()
        return _app


def __getattr__(name: str):
    # ``uvicorn uta.demo.app:app`` (render.yaml) resolves ``app`` by attribute access, which lands
    # here: the seed happens on that first access, not at import time.
    if name == "app":
        return get_demo_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
