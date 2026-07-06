"""Baseline selection + run diff.

**Baseline = the most recent *complete* run before this one** — never blindly the previous build,
because diffing against a partial/aborted run invents phantom regressions and fixes (a test looks
"missing" only because a shard never ran). Incomplete runs are still stored and shown (the pipeline
persists them) but skipped here; the chosen baseline id is recorded on the run so the diff is never
ambiguous.

The diff is expressed at **test-identity** granularity (a test runs in both tracks; it is failing
if it fails in *either*), which is also the granularity the lifecycle state machine and the triage
buckets work in.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import Run, TestResult

# Per-identity, per-run status (collapsed across tracks). ``None`` (absent) is represented by the
# key simply being missing from the status map.
FAILED = "FAILED"
PASSED = "PASSED"
SKIPPED = "SKIPPED"

_PASSED_STATUSES = frozenset({"PASSED", "FIXED"})


def identity_status_maps(session: Session, run_ids: Collection[int]) -> dict[int, dict[int, str]]:
    """Collapsed status maps for **many runs in one query** — ``run_id -> {identity_id: status}``.

    Same collapse as :func:`identity_status_map`; batching is what keeps pages that diff several
    runs (the runs list) at a constant query count instead of one scan per run (issue #52).
    Every requested id gets an entry (empty for a run with no results).
    """
    maps: dict[int, dict[int, str]] = {run_id: {} for run_id in run_ids}
    if not run_ids:
        return maps
    rows = session.execute(
        select(TestResult.run_id, TestResult.test_identity_id, TestResult.status).where(
            TestResult.run_id.in_(set(run_ids))
        )
    ).all()
    for run_id, identity_id, status in rows:
        collapsed = maps[run_id]
        if status in FAILED_STATUSES:
            collapsed[identity_id] = FAILED  # FAILED in any track wins outright
        elif status in _PASSED_STATUSES:
            if collapsed.get(identity_id) != FAILED:
                collapsed[identity_id] = PASSED
        else:  # SKIPPED / unknown — only fills a slot nothing stronger claimed
            collapsed.setdefault(identity_id, SKIPPED)
    return maps


def identity_status_map(session: Session, run: Run) -> dict[int, str]:
    """Map ``test_identity_id -> collapsed status`` for one run.

    A test runs once per track; the identity is **FAILED** if any track failed, else **PASSED** if
    any track passed, else **SKIPPED**. Absent identities are simply omitted.
    """
    return identity_status_maps(session, [run.id])[run.id]


def select_baseline(session: Session, run: Run) -> Run | None:
    """The most recent **complete** run strictly before ``run`` (by start time), or ``None``."""
    return session.scalar(
        select(Run)
        .where(Run.complete.is_(True), Run.id != run.id, Run.started_at < run.started_at)
        .order_by(Run.started_at.desc())
        .limit(1)
    )


@dataclass
class RunDiff:
    """The diff of a run against its baseline, at test-identity granularity."""

    baseline_run_id: int | None
    regressions: list[int] = field(default_factory=list)  # newly failing
    newly_fixed: list[int] = field(default_factory=list)  # failing -> passed
    still_failing: list[int] = field(default_factory=list)  # failing in both
    removed: list[int] = field(default_factory=list)  # was failing, now absent


def compute_diff(
    session: Session,
    run: Run,
    baseline: Run | None,
    *,
    current: dict[int, str] | None = None,
    baseline_status: dict[int, str] | None = None,
) -> RunDiff:
    """Diff ``run`` against ``baseline`` (``None`` → first run: every failure is a regression).

    ``current`` / ``baseline_status`` may be passed in to avoid recomputing the status maps when
    the caller (the lifecycle step) already has them.
    """
    cur = current if current is not None else identity_status_map(session, run)
    base = (
        baseline_status
        if baseline_status is not None
        else (identity_status_map(session, baseline) if baseline is not None else {})
    )
    diff = RunDiff(baseline_run_id=baseline.id if baseline is not None else None)

    for identity_id, status in cur.items():
        was_failing = base.get(identity_id) == FAILED
        if status == FAILED:
            (diff.still_failing if was_failing else diff.regressions).append(identity_id)
        elif status == PASSED and was_failing:
            diff.newly_fixed.append(identity_id)

    # Removed: failing in baseline but absent from this run entirely.
    for identity_id, status in base.items():
        if status == FAILED and identity_id not in cur:
            diff.removed.append(identity_id)

    return diff
