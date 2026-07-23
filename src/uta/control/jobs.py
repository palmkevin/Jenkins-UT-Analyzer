"""On-demand ingest / re-analysis jobs for the control panel (issue #16).

The monitor kicks off an ingest of a build (or range) from the dashboard; this module creates the
:class:`~uta.models.IngestJob` row and runs it, advancing its status queued → running → done/error
so the UI can poll progress.

**Back-fill semantics, always.** A job passes *no* email sender and *no* LLM hypothesis provider to
:func:`~uta.ingest.pipeline.ingest_build` — a re-ingest must never re-mail a historical regression
or re-spend on hypotheses (identical to ``uta backfill`` / ``bootstrap``). Flaky flags are display-
only, so they are recomputed once after the range rather than per build.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from uta.clients import build_client, build_feed, windows
from uta.config import Settings
from uta.db import session_scope
from uta.ingest.jenkins import JenkinsClient
from uta.models import IngestJob
from uta.models.enums import IngestJobStatus
from uta.refdb.oracle import TrackingFeed

logger = logging.getLogger(__name__)
_MAX_ERROR = 2000


def create_ingest_job(
    session: Session, build_start: int, build_end: int, *, actor: str | None = None
) -> IngestJob:
    """Persist a queued job over the inclusive range (a reversed ``start > end`` is normalised)."""
    lo, hi = min(build_start, build_end), max(build_start, build_end)
    job = IngestJob(
        build_start=lo,
        build_end=hi,
        status=IngestJobStatus.QUEUED,
        builds_total=hi - lo + 1,
        builds_done=0,
        requested_by=actor,
    )
    session.add(job)
    return job


def run_ingest_job(
    session_factory: sessionmaker[Session],
    job_id: int,
    *,
    settings: Settings,
    client: JenkinsClient,
    feed: TrackingFeed | None,
) -> None:
    """Execute a persisted job: ingest each build with back-fill semantics, tracking status.

    Runs synchronously in the calling thread (the web layer hands this to a background thread; tests
    call it directly). Any failure flips the job to ``ERROR`` with the detail captured — the job row
    is the durable record of what happened, so a background failure is never silently lost.
    """
    from uta.analyze.flakiness import recompute_flaky_flags
    from uta.control.quarantine import clear_failure
    from uta.ingest.pipeline import ingest_build

    lookback, tolerance = windows(settings)
    with session_scope(session_factory) as session:
        job = session.get(IngestJob, job_id)
        if job is None:
            return
        job.status = IngestJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        start, end = job.build_start, job.build_end

    try:
        for n in range(start, end + 1):
            # No email sender, no hypothesis provider ⇒ back-fill semantics (never re-mail history).
            ingest_build(
                client,
                session_factory,
                n,
                expected_tracks=settings.expected_tracks,
                feed=feed,
                data_change_lookback=lookback,
                data_change_tolerance=tolerance,
                flaky_window_days=settings.flaky_window_days,
                flaky_threshold=settings.flaky_transition_threshold,
                ingest_unittest_logs=settings.ingest_unittest_stages,
                unittest_suites=settings.unittest_suite_set,
                recompute_flaky=False,
            )
            # An on-demand re-ingest is the recovery path for a quarantined build (issue #51):
            # success means the cause is fixed, so drop its quarantine record.
            clear_failure(session_factory, n)
            with session_scope(session_factory) as session:
                job = session.get(IngestJob, job_id)
                if job is not None:
                    job.builds_done = n - start + 1
        with session_scope(session_factory) as session:
            recompute_flaky_flags(
                session,
                window_days=settings.flaky_window_days,
                threshold=settings.flaky_transition_threshold,
            )
        with session_scope(session_factory) as session:
            job = session.get(IngestJob, job_id)
            if job is not None:
                job.status = IngestJobStatus.DONE
                job.finished_at = datetime.now(UTC)
        logger.info("ingest job #%d done (builds %d..%d)", job_id, start, end)
    except Exception as exc:  # noqa: BLE001 — record any failure on the job row, don't crash the server
        logger.exception("ingest job #%d failed", job_id)
        with session_scope(session_factory) as session:
            job = session.get(IngestJob, job_id)
            if job is not None:
                job.status = IngestJobStatus.ERROR
                job.error = repr(exc)[:_MAX_ERROR]
                job.finished_at = datetime.now(UTC)


def trigger_ingest(
    session_factory: sessionmaker[Session],
    *,
    build_start: int,
    build_end: int,
    settings: Settings,
    actor: str | None = None,
    client: JenkinsClient | None = None,
    feed: TrackingFeed | None = None,
    run_in_thread: bool = True,
) -> int:
    """Create a job and run it (in a background daemon thread by default). Returns the job id.

    The Jenkins client and Oracle feed are built from ``settings`` the same way the CLI back-fill
    runs them, unless injected (tests). With ``run_in_thread=False`` the job runs synchronously —
    used by tests so assertions see the terminal state without racing a thread.
    """
    with session_scope(session_factory) as session:
        job = create_ingest_job(session, build_start, build_end, actor=actor)
        session.flush()
        job_id = job.id

    if client is None:
        client = build_client(settings)
    if feed is None:
        feed = build_feed(settings)

    def _build() -> None:
        run_ingest_job(session_factory, job_id, settings=settings, client=client, feed=feed)

    if run_in_thread:
        threading.Thread(target=_build, name=f"ingest-job-{job_id}", daemon=True).start()
    else:
        _build()
    return job_id


def recover_orphaned_jobs(session_factory: sessionmaker[Session]) -> int:
    """Mark jobs orphaned by a restart as ``ERROR`` — call once at web-process startup (issue #51).

    Jobs build in this process's daemon threads, so a restart kills them mid-flight while their rows
    stay ``QUEUED``/``RUNNING`` forever. Any such row found at startup can only be an orphan (no
    thread survives the process), so it is flipped to ``ERROR`` with an explanatory message rather
    than left lying to the control panel. Returns how many rows were recovered.
    """
    from sqlalchemy import select

    recovered = 0
    with session_scope(session_factory) as session:
        stale = session.scalars(
            select(IngestJob).where(
                IngestJob.status.in_([IngestJobStatus.QUEUED, IngestJobStatus.RUNNING])
            )
        ).all()
        for job in stale:
            job.status = IngestJobStatus.ERROR
            job.error = (
                "orphaned by a restart — the job's thread did not survive; "
                "re-run the range from the control panel"
            )
            job.finished_at = datetime.now(UTC)
            recovered += 1
    if recovered:
        logger.warning("recovered %d orphaned ingest job(s) left QUEUED/RUNNING", recovered)
    return recovered


def recent_jobs(session: Session, *, limit: int = 20) -> list[IngestJob]:
    """The most-recent ingest jobs, newest first (for the control-panel history)."""
    from sqlalchemy import select

    return list(session.scalars(select(IngestJob).order_by(IngestJob.id.desc()).limit(limit)).all())
