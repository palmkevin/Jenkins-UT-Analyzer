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

from uta.config import Settings
from uta.control.heartbeat import record_heartbeat
from uta.control.tunables import effective_settings, load_overrides
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


def poll_tick(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    base_settings: Settings,
    *,
    feed: TrackingFeed | None = None,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    hypothesis_provider: HypothesisProvider | None = None,
) -> list[int]:
    """One scheduled poll: resolve live overrides, ingest new builds, record the heartbeat.

    The tunable thresholds are re-read from the DB **every tick** (merged onto the env settings), so
    a control-panel override takes effect on the next poll with no restart (issue #16). Secrets and
    URLs are not tunable, so the pre-built ``client`` / ``feed`` / ``email_sender`` /
    ``hypothesis_provider`` are reused. Any failure is caught, recorded on the heartbeat, and
    swallowed so a single bad tick never kills the long-lived scheduler.
    """
    with session_scope(session_factory) as session:
        cfg = effective_settings(base_settings, load_overrides(session))

    try:
        processed = poll_once(
            client,
            session_factory,
            expected_shards=cfg.expected_shards,
            feed=feed,
            data_change_lookback=timedelta(hours=cfg.data_change_lookback_hours),
            data_change_tolerance=timedelta(minutes=cfg.data_change_tolerance_minutes),
            flaky_window_days=cfg.flaky_window_days,
            flaky_threshold=cfg.flaky_transition_threshold,
            email_sender=email_sender,
            email_recipients=email_recipients,
            email_recovery_notice=cfg.email_recovery_notice,
            hypothesis_provider=hypothesis_provider,
            kb_top_k=cfg.kb_top_k,
            kb_similarity_cutoff=cfg.pgtrgm_similarity_cutoff,
            ingest_unittest_logs=cfg.ingest_unittest_stages,
            unittest_suites=cfg.unittest_suite_set,
            backfill_depth=cfg.backfill_depth,
        )
    except Exception as exc:  # noqa: BLE001 — surface on the heartbeat, keep the scheduler alive
        logger.exception("poll tick failed")
        record_heartbeat(session_factory, processed=[], error=repr(exc))
        return []
    record_heartbeat(session_factory, processed=processed, error=None)
    return processed


def run_scheduler(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    base_settings: Settings,
    *,
    feed: TrackingFeed | None = None,
    email_sender: EmailSender | None = None,
    email_recipients: tuple[str, ...] = (),
    hypothesis_provider: HypothesisProvider | None = None,
) -> None:
    """Block forever, polling on the configured interval (the ``uta poll`` entrypoint).

    Each tick goes through :func:`poll_tick`, which re-resolves runtime overrides and stamps the
    heartbeat, so both live-tuning and poller-health surface without a restart.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler

    def _tick() -> list[int]:
        return poll_tick(
            client,
            session_factory,
            base_settings,
            feed=feed,
            email_sender=email_sender,
            email_recipients=email_recipients,
            hypothesis_provider=hypothesis_provider,
        )

    scheduler = BlockingScheduler()
    scheduler.add_job(
        _tick, "interval", seconds=base_settings.poll_interval_seconds, next_run_time=None
    )
    # Run an immediate pass on startup so a fresh poller doesn't idle until the first interval.
    _tick()
    scheduler.start()
