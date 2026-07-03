"""Seed a store with the synthetic demo history via the *real* ingest + analysis pipeline.

This is the single source of the "dummy dataset": it feeds :class:`SyntheticJenkins` /
:class:`SyntheticTrackingFeed` through :func:`uta.ingest.pipeline.ingest_build` build-by-build
(oldest-first, exactly like ``uta bootstrap``), recomputes the flaky flags, then applies a couple of
human triage actions so the dashboard shows acknowledged / attributed states too.

Used both by the ephemeral demo web app (:mod:`uta.demo.app`) and the integration tests, so the two
exercise identical data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from uta.analyze.flakiness import recompute_flaky_flags
from uta.db import session_scope
from uta.demo.dataset import SyntheticJenkins, SyntheticTrackingFeed, build_numbers
from uta.ingest.pipeline import ingest_build
from uta.models import TestIdentity, TestLifecycle
from uta.web import actions

# The self-declared actors that "triaged" the demo data (invented handles, not real users).
_DEMO_ACTOR = "demo-user"

# Tests to acknowledge (moves them New -> Still failing) and, optionally, attribute a cause to.
_ACKNOWLEDGE = (
    "ut_core.co_time.TestClass.test_timezone_convert",
    "ut_core.co_math.TestClass.test_matrix_inverse",
)


def _current_episode_id(session: Session, canonical_name: str) -> tuple[int, int] | None:
    """(identity_id, current_episode_id) for a test, or ``None`` if it has no open episode."""
    ident = session.scalar(
        select(TestIdentity).where(TestIdentity.canonical_name == canonical_name)
    )
    if ident is None:
        return None
    lc = session.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident.id))
    if lc is None or lc.current_episode_id is None:
        return None
    return ident.id, lc.current_episode_id


def seed_demo_data(
    session_factory: sessionmaker[Session],
    *,
    anchor: datetime | None = None,
    flaky_window_days: int = 30,
    flaky_threshold: float = 0.3,
) -> int:
    """Populate an (already-migrated / created) store with the synthetic history.

    Returns the number of builds ingested. Idempotent-ish: re-seeding the same store re-ingests each
    build (the pipeline is idempotent per build) but the triage actions are simply re-applied.
    """
    anchor = anchor or datetime.now(UTC)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)

    client = SyntheticJenkins(anchor=anchor)
    feed = SyntheticTrackingFeed(anchor=anchor)

    builds = build_numbers()
    for build in builds:
        ingest_build(
            client,
            session_factory,
            build,
            expected_shards=2,
            feed=feed,
            flaky_window_days=flaky_window_days,
            flaky_threshold=flaky_threshold,
            ingest_unittest_logs=False,
            recompute_flaky=False,  # one pass after the loop (flags are display-only)
        )

    with session_scope(session_factory) as session:
        recompute_flaky_flags(session, window_days=flaky_window_days, threshold=flaky_threshold)

    # A few human triage actions so acknowledged / attributed states are represented too.
    with session_scope(session_factory) as session:
        for name in _ACKNOWLEDGE:
            found = _current_episode_id(session, name)
            if found is not None:
                actions.acknowledge(session, found[0], _DEMO_ACTOR)

        tz = _current_episode_id(session, "ut_core.co_time.TestClass.test_timezone_convert")
        if tz is not None:
            actions.set_attribution(
                session,
                tz[1],
                _DEMO_ACTOR,
                causing_person="THA",
                reason_text="Reference table updated without a matching migration.",
                triage_status="in_progress",
                jira_ticket="LX-8842",
            )

    return len(builds)
