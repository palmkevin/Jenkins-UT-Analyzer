"""Scheduled Jenkins poll: detect new completed builds and ingest them.

The poller is a thin driver over :func:`uta.ingest.pipeline.ingest_build`. Its only real logic is
**which** builds to process: everything above the highest build already in our store, up to the
job's ``lastCompletedBuild``, minus any quarantined builds. That high-water mark lives in the DB
(no separate cursor to keep in sync), so the poll is restart-safe and an on-demand back-fill and
the scheduler converge on the same state.

Resilience (issue #51): a **transient** error (network, HTTP 5xx/429, DB connection blip) is
retried with exponential backoff inside the tick. A build that still fails counts one attempt on
its :class:`~uta.models.BuildQuarantine` row and ends the tick (later builds wait, preserving
lifecycle order) — until the attempt limit, when the build is **quarantined**: recorded, alerted by
email, and skipped so ingest advances past it. A 404-rotated build is quarantined immediately (the
explicit form of the old silent skip).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import timedelta

import httpx
from sqlalchemy import exc as sa_exc
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from uta.config import Settings
from uta.control.heartbeat import record_heartbeat
from uta.control.quarantine import (
    clear_failure,
    quarantine_immediately,
    quarantined_build_numbers,
    record_failure,
)
from uta.control.tunables import effective_settings, load_overrides
from uta.db import session_scope
from uta.delivery.email import EmailSender, send_ops_alert
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.pipeline import ingest_build
from uta.llm import HypothesisProvider
from uta.refdb.oracle import TrackingFeed
from uta.retention import prune

logger = logging.getLogger(__name__)


class BuildIngestError(RuntimeError):
    """A build failed ingest after in-tick retries (its attempt is already recorded).

    Carries the builds processed earlier in the tick so the heartbeat can still report them —
    the failure ends the tick (the build is retried next tick until quarantined), it must not
    erase the progress made before it.
    """

    def __init__(self, build: int, cause: BaseException, processed: list[int]) -> None:
        super().__init__(f"build #{build} failed ingest: {cause!r}")
        self.build = build
        self.cause = cause
        self.processed = processed


def _is_transient(exc: BaseException) -> bool:
    """Worth retrying in-tick: network faults, HTTP 5xx/429, DB connection blips.

    Anything else (a 4xx, a parse ``ValueError`` from a malformed build, …) is deterministic —
    retrying it seconds later cannot succeed, so it fails fast into the attempt counter.
    """
    if isinstance(exc, httpx.TransportError):  # connect/read/write/pool errors and timeouts
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, sa_exc.OperationalError | sa_exc.InterfaceError)


def _with_retries[T](
    fn: Callable[[], T],
    *,
    what: str,
    attempts: int,
    base_seconds: float,
    sleep: Callable[[float], None],
) -> T:
    """Run ``fn``, retrying transient failures with exponential backoff (base, 2×, 4×, …)."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt >= attempts or not _is_transient(exc):
                raise
            delay = base_seconds * 2 ** (attempt - 1)
            logger.warning(
                "%s failed with transient %r (attempt %d/%d) — retrying in %.1fs",
                what,
                exc,
                attempt,
                attempts,
                delay,
            )
            sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover — the loop always returns or raises


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

    Quarantined builds are excluded: a quarantined build persisted no Run, so without the filter it
    would be re-selected every tick forever — skipping it here is what lets ingest advance past it.
    """
    latest = client.last_completed_build()
    if latest is None:
        return []
    highest = highest_ingested_build(session_factory)
    with session_scope(session_factory) as session:
        quarantined = quarantined_build_numbers(session)
    start = highest + 1 if highest else max(1, latest - backfill_depth + 1)
    return [b for b in range(start, latest + 1) if b not in quarantined]


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
    retry_attempts: int = 3,
    retry_base_seconds: float = 2.0,
    quarantine_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> list[int]:
    """Ingest every new completed build once. Returns the build numbers processed.

    The poller is the **live** path, so it forwards the email sender and the LLM hypothesis provider
    — each newly-processed build that introduces a regression triggers the email alert and (with a
    real provider) the LLM hypothesis. Each build is ingested at most once (the high-water mark), so
    neither is re-done.

    Failure handling per build: transient errors retry in-tick (``retry_attempts`` ×
    ``retry_base_seconds`` backoff); a build that still fails records one attempt and raises
    :class:`BuildIngestError`, ending the tick so it is retried next tick — until
    ``quarantine_attempts``, when it is quarantined (recorded + ops-alerted) and the tick continues
    past it. A 404 detail endpoint (build rotated out of Jenkins retention) quarantines immediately.
    """
    builds = _with_retries(
        lambda: builds_to_ingest(client, session_factory, backfill_depth=backfill_depth),
        what="build selection",
        attempts=retry_attempts,
        base_seconds=retry_base_seconds,
        sleep=sleep,
    )
    processed: list[int] = []
    for build in builds:
        try:
            _with_retries(
                lambda build=build: ingest_build(
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
                ),
                what=f"ingest of build #{build}",
                attempts=retry_attempts,
                base_seconds=retry_base_seconds,
                sleep=sleep,
            )
        except Exception as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
                # A build's pointer can outlive its detail endpoint: Jenkins rotates old builds
                # out of retention while ``lastCompletedBuild`` still names them, so a detail
                # fetch 404s. Gone for good — quarantine immediately (the explicit, surfaced form
                # of the old silent skip) and keep polling; retrying it can never succeed.
                reason = f"detail endpoint returned 404 ({exc.request.url})"
                logger.warning("quarantining build #%d: %s", build, reason)
                quarantine_immediately(session_factory, build, reason)
                send_ops_alert(
                    email_sender,
                    email_recipients,
                    subject=f"build #{build} skipped (rotated out of Jenkins retention)",
                    body=(
                        f"Build #{build} was skipped: {reason}.\n"
                        f"The build left no data in the store and will not be retried.\n"
                    ),
                )
                continue
            row = record_failure(
                session_factory, build, repr(exc), quarantine_after=quarantine_attempts
            )
            if row.quarantined_at is not None:
                logger.error(
                    "quarantining build #%d after %d failed attempts: %r",
                    build,
                    row.attempts,
                    exc,
                )
                send_ops_alert(
                    email_sender,
                    email_recipients,
                    subject=f"build #{build} quarantined after {row.attempts} attempts",
                    body=(
                        f"Build #{build} failed ingest on {row.attempts} consecutive polls and "
                        f"has been quarantined — the poller advances past it.\n"
                        f"Last error: {exc!r}\n"
                        f"Re-ingest it from the control panel once the cause is fixed.\n"
                    ),
                )
                continue
            # Not yet at the limit: end the tick so lifecycle order is preserved and the build is
            # retried on the next tick. Later builds wait behind it.
            raise BuildIngestError(build, exc, processed) from exc
        clear_failure(session_factory, build)
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
    sleep: Callable[[float], None] = time.sleep,
) -> list[int]:
    """One scheduled poll: resolve live overrides, ingest new builds, record the heartbeat.

    The tunable thresholds are re-read from the DB **every tick** (merged onto the env settings), so
    a control-panel override takes effect on the next poll with no restart (issue #16). Secrets and
    URLs are not tunable, so the pre-built ``client`` / ``feed`` / ``email_sender`` /
    ``hypothesis_provider`` are reused. Any failure is caught, recorded on the heartbeat, and
    swallowed so a single bad tick never kills the long-lived scheduler; a per-build failure
    (:class:`BuildIngestError`) still reports the builds the tick did process.

    Each successful tick ends with a retention pass (issue #52): old passing results and finished
    ingest jobs are pruned per the (tunable) retention windows. The pass is idempotent, so ticks
    that ingest nothing still keep the store trimmed (a tick cut short by a build failure skips it
    until the next clean tick).
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
            retry_attempts=cfg.poll_retry_attempts,
            retry_base_seconds=cfg.poll_retry_base_seconds,
            quarantine_attempts=cfg.quarantine_after_attempts,
            sleep=sleep,
        )
        with session_scope(session_factory) as session:
            prune(
                session,
                result_retention_days=cfg.result_retention_days,
                ingest_job_retention_days=cfg.ingest_job_retention_days,
            )
    except BuildIngestError as exc:
        logger.exception("poll tick ended early on build #%d", exc.build)
        record_heartbeat(session_factory, processed=exc.processed, error=repr(exc.cause))
        return exc.processed
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
