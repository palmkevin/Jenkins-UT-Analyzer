"""Data retention: prune old raw *passing* results and finished ingest jobs (issue #52).

Nothing else in the store ever deletes, and the analyzed Permanent Pipeline runs **one build per
commit** (ADR-0003), so the raw results table grows fast: at ~25k :class:`~uta.models.TestResult`
rows per build and ~15-20 builds per active weekday (~4-5k builds/year), that is ~110M rows/year of
gross inserts — almost all of them passing rows whose only long-term value is already captured
elsewhere (the build's stored totals, the lifecycle/episode history, and the KB aggregates). That
volume is *why* pruning earns its keep: dropping passing/skipped rows past the retention window
holds the raw table to a bounded working set (~28M rows for the default 90-day window at this
cadence) instead of letting it grow without limit. The policy is therefore:

- **Drop passing/skipped results** from builds older than ``RESULT_RETENTION_DAYS``. **Failing
  results are kept forever** — they are the failure-history evidence: episodes' failure detail,
  the KB signature links (``kb/store.py`` recomputes ``occurrence_count`` from linked results, so
  deleting a linked row would corrupt the count), and the all-time failure counts all read them.
  Only rows with ``signature_id IS NULL`` are ever deleted (belt and braces: a signed row is never
  in scope even if a failing status were mis-classified). At per-commit cadence the kept-forever
  failing rows accumulate ~12x faster than the old once-a-night reasoning assumed, but they remain
  a small fraction of inserts (~0.5-1M/year at a ~0.5-1% fail rate) and are the one term that grows
  unbounded; capping *very old* failure evidence is a possible future refinement, out of scope here.
- **Builds, episodes, lifecycles, attributions and KB signatures/aggregates are kept forever** —
  they carry the long-term value and are tiny next to the raw results.
- **Finished ingest jobs** (DONE/ERROR) older than ``INGEST_JOB_RETENTION_DAYS`` are dropped;
  queued/running jobs are never touched. The poller heartbeat is a singleton row (no history to
  cap; its error text is already length-capped).

Pruning is **idempotent** (a plain cutoff DELETE) and builds on every poll tick plus on demand via
``uta prune``. Both windows are runtime-tunable (control panel); ``0`` disables that window.

Known, accepted degradation: the diff of a build *older than the retention window* loses its
"newly fixed" entries (the passing rows that proved the fix are gone — regressions/still-failing/
removed survive because failing rows are kept). Recent builds — everything inside the window — are
unaffected, and the build's stored pass/fail/skip totals remain exact forever.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import Build, IngestJob, TestResult
from uta.models.enums import IngestJobStatus

logger = logging.getLogger(__name__)

# Ingest jobs in a terminal state — the only ones ever pruned.
_FINISHED_JOB_STATUSES = (IngestJobStatus.DONE, IngestJobStatus.ERROR)


@dataclass(frozen=True)
class PruneReport:
    """What one pruning pass deleted."""

    results_deleted: int
    ingest_jobs_deleted: int

    @property
    def total(self) -> int:
        return self.results_deleted + self.ingest_jobs_deleted


def _cutoff(now: datetime | None, days: int) -> datetime:
    return (now or datetime.now(UTC)) - timedelta(days=days)


def prune_passing_results(
    session: Session, *, retention_days: int, now: datetime | None = None
) -> int:
    """Delete passing/skipped results belonging to builds older than ``retention_days``.

    Returns the number of rows deleted. ``retention_days <= 0`` disables pruning (returns 0).
    The build's ``started_at`` is the age reference (the domain clock), not the row's insert time,
    so a late back-fill of an old build is pruned consistently with its neighbours.
    """
    if retention_days <= 0:
        return 0
    old_builds = select(Build.id).where(Build.started_at < _cutoff(now, retention_days))
    result = session.execute(
        delete(TestResult)
        .where(
            TestResult.status.not_in(FAILED_STATUSES),
            TestResult.signature_id.is_(None),  # never touch a KB-linked row
            TestResult.build_id.in_(old_builds),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0


def prune_ingest_jobs(session: Session, *, retention_days: int, now: datetime | None = None) -> int:
    """Delete DONE/ERROR ingest jobs that finished more than ``retention_days`` ago.

    Returns the number of rows deleted. ``retention_days <= 0`` disables pruning. Queued/running
    jobs are never deleted, whatever their age.
    """
    if retention_days <= 0:
        return 0
    result = session.execute(
        delete(IngestJob)
        .where(
            IngestJob.status.in_(_FINISHED_JOB_STATUSES),
            IngestJob.finished_at.is_not(None),
            IngestJob.finished_at < _cutoff(now, retention_days),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0


def prune(
    session: Session,
    *,
    result_retention_days: int,
    ingest_job_retention_days: int,
    now: datetime | None = None,
) -> PruneReport:
    """One full pruning pass (results + ingest jobs). Idempotent; safe to run every tick."""
    report = PruneReport(
        results_deleted=prune_passing_results(
            session, retention_days=result_retention_days, now=now
        ),
        ingest_jobs_deleted=prune_ingest_jobs(
            session, retention_days=ingest_job_retention_days, now=now
        ),
    )
    if report.total:
        logger.info(
            "pruned %d passing results, %d finished ingest jobs",
            report.results_deleted,
            report.ingest_jobs_deleted,
        )
    return report
