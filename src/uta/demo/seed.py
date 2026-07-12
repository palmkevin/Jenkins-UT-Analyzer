"""Seed a store with the synthetic demo history via the *real* ingest + analysis pipeline.

This is the single source of the "dummy dataset": it feeds :class:`SyntheticJenkins` /
:class:`SyntheticTrackingFeed` through :func:`uta.ingest.pipeline.ingest_build` build-by-build
(oldest-first, exactly like ``uta bootstrap``), recomputes the flaky flags, then applies a couple of
human triage actions so the dashboard shows acknowledged / attributed states too.

Used both by the ephemeral demo web app (:mod:`uta.demo.app`) and the integration tests, so the two
exercise identical data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from uta.analyze.flakiness import recompute_flaky_flags
from uta.db import session_scope
from uta.demo.dataset import SyntheticJenkins, SyntheticTrackingFeed, build_numbers
from uta.ingest.pipeline import ingest_build
from uta.models import (
    BuildQuarantine,
    IngestJob,
    PollerHeartbeat,
    SettingOverride,
    TestIdentity,
    TestLifecycle,
)
from uta.models.enums import IngestJobStatus
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


def _seed_control_state(
    session_factory: sessionmaker[Session], *, anchor: datetime, builds: list[int]
) -> None:
    """Populate the control-panel's operational tables so the demo's ``/control`` page isn't empty.

    All synthetic (same discipline as the rest of the demo): a healthy **poller heartbeat**, one
    active **threshold override** (so the "overridden" badge + Revert button show), two past
    **ingest jobs** — one done, one errored — and one **quarantined build** (issue #51) so every
    panel renders populated. The store is ephemeral and re-seeded per process, so this is rebuilt
    identically on every restart.

    Idempotent (issue #122): the fixed-PK rows are ``merge``d (upsert) and the previous seed's
    auto-PK ingest jobs are dropped before re-inserting, so re-seeding a persistent store
    (``uta seed-demo``) converges instead of raising duplicate-PK errors.
    """
    last = builds[-1]
    with session_scope(session_factory) as session:
        session.merge(
            PollerHeartbeat(
                id=1,
                last_poll_at=anchor - timedelta(minutes=4),
                last_success_at=anchor - timedelta(minutes=4),
                last_processed_count=1,
                last_processed=str(last),
                last_error=None,
            )
        )
        # A build the poller gave up on: malformed JUnit payload, quarantined after 3 failing
        # ticks — shows the quarantine table with the "quarantined" badge and its recovery hint.
        session.merge(
            BuildQuarantine(
                build_number=builds[0] - 2,
                attempts=3,
                last_error=(
                    "ValueError: unexpected enclosingBlockNames for suite "
                    "'devUTs: Execute - permanent': ['Parallel', '']"
                ),
                first_failed_at=anchor - timedelta(days=1, minutes=14),
                quarantined_at=anchor - timedelta(days=1, minutes=4),
            )
        )
        # Overrides in effect — demonstrate the badge/Revert without perturbing the seeded
        # triage/flaky numbers (kb_top_k only widens how many similar KB cases a test page lists).
        session.merge(SettingOverride(key="kb_top_k", value="8", updated_by=_DEMO_ACTOR))
        # Drop the row cap below a demo run's 32 result rows so the run page's server-side
        # pagination (issue #52) is visible in the live demo. Triage buckets are far smaller, so
        # they render unchanged.
        session.merge(SettingOverride(key="ui_row_limit", value="20", updated_by=_DEMO_ACTOR))
        # The ingest jobs are auto-PK, so a re-seed would duplicate them — drop the previous
        # seed's rows (identifiable by the demo actor) before inserting.
        session.execute(delete(IngestJob).where(IngestJob.requested_by == _DEMO_ACTOR))
        session.add(
            IngestJob(
                build_start=builds[0],
                build_end=builds[3],
                status=IngestJobStatus.DONE,
                builds_total=4,
                builds_done=4,
                requested_by=_DEMO_ACTOR,
                started_at=anchor - timedelta(hours=2),
                finished_at=anchor - timedelta(hours=2, minutes=-3),
            )
        )
        session.add(
            IngestJob(
                build_start=last + 50,
                build_end=last + 50,
                status=IngestJobStatus.ERROR,
                builds_total=1,
                builds_done=0,
                error="HTTPStatusError: 404 Not Found — build detail rotated out of retention.",
                requested_by=_DEMO_ACTOR,
                started_at=anchor - timedelta(minutes=30),
                finished_at=anchor - timedelta(minutes=30, seconds=-8),
            )
        )


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

        # One-click Confirm of the tie-break test's AI suggestion (issue #73): together with the
        # timezone correction above, the control panel's AI-accuracy metric shows one confirmed and
        # one corrected cause instead of an empty panel.
        dt = _current_episode_id(session, "ut_pricing.pr_engine.TestClass.test_discount_tiers")
        if dt is not None:
            actions.confirm(session, dt[1], _DEMO_ACTOR)

    # Synthetic control-panel state so the demo's /control page renders populated (issue #16).
    _seed_control_state(session_factory, anchor=anchor, builds=builds)

    return len(builds)
