"""Baseline selection + build diff.

**Baseline = the most recent *complete* build before this one** — never blindly the previous build,
because diffing against a partial/aborted build invents phantom regressions and fixes (a test looks
"missing" only because a track never ran). Incomplete builds are still stored and shown (the
pipeline persists them) but skipped here; the chosen baseline id is recorded on the build so the
diff is never ambiguous.

The diff is expressed at **test-identity** granularity (a test builds in both tracks; it is failing
if it fails in *either*), which is also the granularity the lifecycle state machine and the triage
buckets work in.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import Build, TestResult

# Per-identity, per-build status (collapsed across tracks). ``None`` (absent) is represented by the
# key simply being missing from the status map.
FAILED = "FAILED"
PASSED = "PASSED"
SKIPPED = "SKIPPED"

_PASSED_STATUSES = frozenset({"PASSED", "FIXED"})


def identity_status_maps(session: Session, build_ids: Collection[int]) -> dict[int, dict[int, str]]:
    """Collapsed status maps for **many builds in one query** — ``build_id -> {identity_id:
    status}``.

    Same collapse as :func:`identity_status_map`; batching is what keeps pages that diff several
    builds (the builds list) at a constant query count instead of one scan per build (issue #52).
    Every requested id gets an entry (empty for a build with no results).
    """
    maps: dict[int, dict[int, str]] = {build_id: {} for build_id in build_ids}
    if not build_ids:
        return maps
    rows = session.execute(
        select(TestResult.build_id, TestResult.test_identity_id, TestResult.status).where(
            TestResult.build_id.in_(set(build_ids))
        )
    ).all()
    for build_id, identity_id, status in rows:
        collapsed = maps[build_id]
        if status in FAILED_STATUSES:
            collapsed[identity_id] = FAILED  # FAILED in any track wins outright
        elif status in _PASSED_STATUSES:
            if collapsed.get(identity_id) != FAILED:
                collapsed[identity_id] = PASSED
        else:  # SKIPPED / unknown — only fills a slot nothing stronger claimed
            collapsed.setdefault(identity_id, SKIPPED)
    return maps


def identity_status_map(session: Session, build: Build) -> dict[int, str]:
    """Map ``test_identity_id -> collapsed status`` for one build.

    A test builds once per track; the identity is **FAILED** if any track failed, else **PASSED** if
    any track passed, else **SKIPPED**. Absent identities are simply omitted.
    """
    return identity_status_maps(session, [build.id])[build.id]


def select_baseline(session: Session, build: Build) -> Build | None:
    """The most recent **complete** build strictly before ``build`` (by start time), or ``None``."""
    return session.scalar(
        select(Build)
        .where(Build.complete.is_(True), Build.id != build.id, Build.started_at < build.started_at)
        .order_by(Build.started_at.desc())
        .limit(1)
    )


def has_newer_complete_build(session: Session, build: Build) -> bool:
    """Whether a **complete** build with a higher ``build_number`` than ``build`` is already stored.

    The lifecycle state machine only ever advances forward: its transitions mutate the *current*
    ``TestLifecycle``/``FailureEpisode`` rows, so they may only be driven by the newest build. When
    this returns ``True`` the build is a **historical re-ingest** (e.g. the quarantine-recovery
    path,
    issue #82) whose diff describes old facts — applying it would open phantom episodes for
    long-fixed tests, close live episodes "in the past", and clear acknowledgements. The ordering
    is ``build_number`` (unique, monotonic in Jenkins); **strictly** greater, so re-ingesting the
    newest build itself stays on the normal idempotent analysis path.
    """
    return (
        session.scalar(
            select(Build.id)
            .where(Build.complete.is_(True), Build.build_number > build.build_number)
            .limit(1)
        )
        is not None
    )


@dataclass
class RunDiff:
    """The diff of a build against its baseline, at test-identity granularity."""

    baseline_build_id: int | None
    regressions: list[int] = field(default_factory=list)  # newly failing
    newly_fixed: list[int] = field(default_factory=list)  # failing -> passed
    still_failing: list[int] = field(default_factory=list)  # failing in both
    removed: list[int] = field(default_factory=list)  # was failing, now absent


def compute_diff(
    session: Session,
    build: Build,
    baseline: Build | None,
    *,
    current: dict[int, str] | None = None,
    baseline_status: dict[int, str] | None = None,
) -> RunDiff:
    """Diff ``build`` against ``baseline`` (``None`` → first build: every failure is a regression).

    ``current`` / ``baseline_status`` may be passed in to avoid recomputing the status maps when
    the caller (the lifecycle step) already has them.
    """
    cur = current if current is not None else identity_status_map(session, build)
    base = (
        baseline_status
        if baseline_status is not None
        else (identity_status_map(session, baseline) if baseline is not None else {})
    )
    diff = RunDiff(baseline_build_id=baseline.id if baseline is not None else None)

    for identity_id, status in cur.items():
        was_failing = base.get(identity_id) == FAILED
        if status == FAILED:
            (diff.still_failing if was_failing else diff.regressions).append(identity_id)
        elif status == PASSED and was_failing:
            diff.newly_fixed.append(identity_id)

    # Removed: failing in baseline but absent from this build entirely.
    for identity_id, status in base.items():
        if status == FAILED and identity_id not in cur:
            diff.removed.append(identity_id)

    return diff
