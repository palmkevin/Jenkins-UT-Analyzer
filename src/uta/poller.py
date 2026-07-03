"""Scheduled Jenkins poll (PLAN §"Trigger"): detect new completed builds and ingest them.

The poller is a thin driver over :func:`uta.ingest.pipeline.ingest_build`. Its only real logic is
**which** builds to process: everything above the highest build already in our store, up to the
job's ``lastCompletedBuild``. That high-water mark lives in the DB (no separate cursor to keep in
sync), so the poll is restart-safe and an on-demand back-fill and the scheduler converge on the
same state.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.delivery.email import EmailSender
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.pipeline import ingest_build
from uta.llm import HypothesisProvider
from uta.refdb.oracle import TrackingFeed

logger = logging.getLogger(__name__)


def highest_ingested_build(session_factory: sessionmaker[Session]) -> int:
    from uta.models import Run

    with session_scope(session_factory) as session:
        return session.scalar(select(func.max(Run.build_number))) or 0


def builds_to_ingest(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    *,
    backfill_depth: int = 10,
) -> list[int]:
    """The not-yet-ingested completed builds, oldest first (so lifecycle advances in order).

    On a **fresh** store (no builds yet) the window is bounded to the last ``backfill_depth``
    completed builds — ingesting every historical build from #1 is neither wanted nor feasible — so
    a cold start populates ``latest - backfill_depth + 1 … latest`` oldest-first (age N → age 1).
    Once the store is non-empty, selection is purely incremental above the high-water mark.
    """
    latest = client.last_completed_build()
    if latest is None:
        return []
    highest = highest_ingested_build(session_factory)
    start = highest + 1 if highest else max(1, latest - backfill_depth + 1)
    return list(range(start, latest + 1))


def poll_once(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    *,
    expected_shards: int = 2,
    feed: TrackingFeed | None = None,
    data_change_lookback: timedelta = timedelta(hours=12),
    data_change_tolerance: timedelta = timedelta(minutes=5),
    flaky_window_days: int = 30,
    flaky_threshold: float = 0.3,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    email_recovery_notice: bool = False,
    hypothesis_provider: HypothesisProvider | None = None,
    kb_top_k: int = 5,
    kb_similarity_cutoff: float = 0.3,
    ingest_unittest_logs: bool = False,
    unittest_suites: frozenset[str] | set[str] | None = None,
    backfill_depth: int = 10,
) -> list[int]:
    """Ingest every new completed build once. Returns the build numbers processed.

    The poller is the **live** path, so it forwards the email sender and the LLM hypothesis provider
    — each newly-processed build that introduces a regression triggers the §5 alert and (with a real
    provider) the §4 hypothesis. Each build is ingested at most once (the high-water mark), so
    neither is re-done.
    """
    processed: list[int] = []
    for build in builds_to_ingest(client, session_factory, backfill_depth=backfill_depth):
        try:
            ingest_build(
                client,
                session_factory,
                build,
                expected_shards=expected_shards,
                feed=feed,
                data_change_lookback=data_change_lookback,
                data_change_tolerance=data_change_tolerance,
                flaky_window_days=flaky_window_days,
                flaky_threshold=flaky_threshold,
                email_sender=email_sender,
                email_recipients=email_recipients,
                email_recovery_notice=email_recovery_notice,
                hypothesis_provider=hypothesis_provider,
                kb_top_k=kb_top_k,
                kb_similarity_cutoff=kb_similarity_cutoff,
                ingest_unittest_logs=ingest_unittest_logs,
                unittest_suites=unittest_suites,
            )
        except httpx.HTTPStatusError as exc:
            # A build's pointer can outlive its detail endpoint: Jenkins rotates old builds out
            # of retention while ``lastCompletedBuild`` still names them, so a detail fetch 404s.
            # That's an expected gap, not a fault — skip the build and keep polling. Persisting no
            # Run for it leaves the high-water mark unadvanced *for this build*; a later successful
            # build advances it past the gap, so the vanished build is never retried (gone for
            # good). Any other HTTP error is a real fault and propagates.
            if exc.response.status_code != 404:
                raise
            logger.warning(
                "skipping build #%d: detail endpoint returned 404 (%s)", build, exc.request.url
            )
            continue
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
    flaky_window_days: int = 30,
    flaky_threshold: float = 0.3,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    email_recovery_notice: bool = False,
    hypothesis_provider: HypothesisProvider | None = None,
    kb_top_k: int = 5,
    kb_similarity_cutoff: float = 0.3,
    ingest_unittest_logs: bool = False,
    unittest_suites: frozenset[str] | set[str] | None = None,
    backfill_depth: int = 10,
) -> None:
    """Block forever, polling on a fixed interval (the ``uta poll`` entrypoint)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    def _tick() -> list[int]:
        return poll_once(
            client,
            session_factory,
            expected_shards=expected_shards,
            feed=feed,
            data_change_lookback=data_change_lookback,
            data_change_tolerance=data_change_tolerance,
            flaky_window_days=flaky_window_days,
            flaky_threshold=flaky_threshold,
            email_sender=email_sender,
            email_recipients=email_recipients,
            email_recovery_notice=email_recovery_notice,
            hypothesis_provider=hypothesis_provider,
            kb_top_k=kb_top_k,
            kb_similarity_cutoff=kb_similarity_cutoff,
            ingest_unittest_logs=ingest_unittest_logs,
            unittest_suites=unittest_suites,
            backfill_depth=backfill_depth,
        )

    scheduler = BlockingScheduler()
    scheduler.add_job(_tick, "interval", seconds=interval_seconds, next_run_time=None)
    # Run an immediate pass on startup so a fresh poller doesn't idle until the first interval.
    _tick()
    scheduler.start()
