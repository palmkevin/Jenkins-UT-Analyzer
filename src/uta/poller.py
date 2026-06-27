"""Scheduled Jenkins poll (PLAN §"Trigger"): detect new completed builds and ingest them.

The poller is a thin driver over :func:`uta.ingest.pipeline.ingest_build`. Its only real logic is
**which** builds to process: everything above the highest build already in our store, up to the
job's ``lastCompletedBuild``. That high-water mark lives in the DB (no separate cursor to keep in
sync), so the poll is restart-safe and an on-demand back-fill and the scheduler converge on the
same state.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.pipeline import ingest_build
from uta.refdb.oracle import TrackingFeed


def highest_ingested_build(session_factory: sessionmaker[Session]) -> int:
    from uta.models import Run

    with session_scope(session_factory) as session:
        return session.scalar(select(func.max(Run.build_number))) or 0


def builds_to_ingest(client: JenkinsClient, session_factory: sessionmaker[Session]) -> list[int]:
    """The not-yet-ingested completed builds, oldest first (so lifecycle advances in order)."""
    latest = client.last_completed_build()
    if latest is None:
        return []
    highest = highest_ingested_build(session_factory)
    return list(range(highest + 1, latest + 1))


def poll_once(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    *,
    expected_shards: int = 2,
    feed: TrackingFeed | None = None,
    data_change_lookback: timedelta = timedelta(hours=12),
    data_change_tolerance: timedelta = timedelta(minutes=5),
) -> list[int]:
    """Ingest every new completed build once. Returns the build numbers processed."""
    processed: list[int] = []
    for build in builds_to_ingest(client, session_factory):
        ingest_build(
            client,
            session_factory,
            build,
            expected_shards=expected_shards,
            feed=feed,
            data_change_lookback=data_change_lookback,
            data_change_tolerance=data_change_tolerance,
        )
        processed.append(build)
    return processed


def run_scheduler(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    *,
    interval_seconds: int,
    expected_shards: int = 2,
    feed: TrackingFeed | None = None,
    data_change_lookback: timedelta = timedelta(hours=12),
    data_change_tolerance: timedelta = timedelta(minutes=5),
) -> None:
    """Block forever, polling on a fixed interval (the ``uta poll`` entrypoint)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: poll_once(
            client,
            session_factory,
            expected_shards=expected_shards,
            feed=feed,
            data_change_lookback=data_change_lookback,
            data_change_tolerance=data_change_tolerance,
        ),
        "interval",
        seconds=interval_seconds,
        next_run_time=None,
    )
    # Run an immediate pass on startup so a fresh poller doesn't idle until the first interval.
    poll_once(
        client,
        session_factory,
        expected_shards=expected_shards,
        feed=feed,
        data_change_lookback=data_change_lookback,
        data_change_tolerance=data_change_tolerance,
    )
    scheduler.start()
