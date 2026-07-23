"""Query-count guards for the dashboard read paths (issue #52).

The triage and builds pages must stay **O(1) queries in the number of rows** — the per-row lazy-load
patterns (latest classification per episode, build refs, identity/episode/attribution) regressed the
pages as the store grew. A SQLAlchemy statement counter asserts the count is flat: the same number
of statements for a small store and a several-times-larger one.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

from tests.builders import make_build
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.kb.store import record_signatures_for_build
from uta.models import TestLifecycle
from uta.web import views


def _counted_factory():
    """A fresh in-memory store whose engine counts every executed statement."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    counter = {"statements": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        counter["statements"] += 1

    return make_session_factory(engine), counter


def _seed_triage(session_factory, n: int) -> None:
    """``n`` ever-failing tests with bucket variety: new, acknowledged, and recently fixed."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {f"t{i:03d}": "FAILED" for i in range(n)},
            errors={f"t{i:03d}": (f"err {i}", None) for i in range(n)},
        )
        apply_build(s, r1, baseline=None)
        # Signatures recorded so the New rows' blast-radius pass (issue #152) has ids to batch.
        record_signatures_for_build(s, r1)
        # A third get fixed in build 2 (→ recently fixed), the rest keep failing.
        statuses = {f"t{i:03d}": ("PASSED" if i % 3 == 0 else "FAILED") for i in range(n)}
        r2 = make_build(s, 2, statuses)
        apply_build(s, r2, baseline=r1)
    with session_scope(session_factory) as s:
        # Acknowledge a third of the still-failing set (→ the still-failing bucket splits).
        for i, lc in enumerate(s.scalars(select(TestLifecycle)).all()):
            if i % 3 == 1:
                lc.acknowledged = True


def _triage_count_for(n: int) -> int:
    factory, counter = _counted_factory()
    _seed_triage(factory, n)
    with session_scope(factory) as s:
        counter["statements"] = 0
        views.triage_queue(s, limit=0)
        return counter["statements"]


def test_triage_queue_query_count_does_not_grow_with_rows():
    small, large = _triage_count_for(6), _triage_count_for(48)
    assert small == large, f"triage query count grew with rows: {small} -> {large}"
    # Eager lifecycle scan + latest-classification batch + build-ref batch + failure-info batch
    # + signature-blast-radius batch (issue #152).
    assert large <= 5


def _job_builds_count_for(n_builds: int) -> int:
    factory, counter = _counted_factory()
    with session_scope(factory) as s:
        prev = None
        for build in range(1, n_builds + 1):
            build = make_build(s, build, {"a": "PASSED", "b": "FAILED"})
            apply_build(s, build, baseline=prev)
            prev = build
    with session_scope(factory) as s:
        counter["statements"] = 0
        views.job_builds(s, limit=0)
        return counter["statements"]


def test_job_builds_query_count_does_not_grow_with_runs():
    small, large = _job_builds_count_for(4), _job_builds_count_for(12)
    assert small == large, f"job_builds query count grew with builds: {small} -> {large}"
    # Count + page of builds + first-build baseline fallback + grouped status scan + heartbeat.
    assert large <= 7
