"""Lifecycle state machine + failure episodes (PLAN §1).

Driven once per **complete** run, comparing each test identity's collapsed status in this run
against the **baseline** (the previous complete run). Working only from those two persisted facts —
never from the stored lifecycle state — makes re-running the analysis for an already-processed run
**idempotent**: the same (baseline, run) pair always yields the same transitions.

Transitions (lifecycle state is *about the result*; acknowledgement is orthogonal, §1):

- not-failing → **FAILING** (regression): open a new episode. If the test had a prior (closed)
  episode this is a *reopen* — bump ``reopen_count`` and clear acknowledgement so it re-enters the
  New bucket (§0).
- FAILING → FAILING (still failing): extend the open episode's last-failing pointer + age.
- FAILING → **FIXED**: the test ran and **passed** again — close the open episode (set fixed-in
  run). Set only on a real pass, never on removal.
- FAILING → **REMOVED**: the test is absent from this complete run — the episode stays open
  (disappeared ≠ fixed), surfaced with a Removed flag.

Only identities that have ever failed get a lifecycle row (§1: the record exists "for every test
that is or has been failing"); perpetually-passing tests are left untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.analyze.baseline import (
    RunDiff,
    compute_diff,
    identity_status_map,
    select_baseline,
)
from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import FailureEpisode, Run, TestLifecycle, TestResult
from uta.models.enums import LifecycleState


@dataclass
class RunAnalysis:
    """Outcome of analysing one run — drives classification and the §2 summary."""

    baseline_run_id: int | None
    diff: RunDiff
    # Episodes opened *this* run (identity_id, episode_id) — the regressions to classify.
    opened_episodes: list[tuple[int, int]] = field(default_factory=list)


def _open_episode(session: Session, identity_id: int) -> FailureEpisode | None:
    return session.scalar(
        select(FailureEpisode).where(
            FailureEpisode.test_identity_id == identity_id,
            FailureEpisode.is_open.is_(True),
        )
    )


def _episode_count(session: Session, identity_id: int) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(FailureEpisode)
            .where(FailureEpisode.test_identity_id == identity_id)
        )
        or 0
    )


def _age_runs(session: Session, identity_id: int, episode: FailureEpisode) -> int:
    """Count complete runs in which this identity failed within the episode's open span."""
    upper = episode.fixed_at or episode.last_failing_at or episode.first_failure_at
    return (
        session.scalar(
            select(func.count(func.distinct(TestResult.run_id)))
            .join(Run, Run.id == TestResult.run_id)
            .where(
                TestResult.test_identity_id == identity_id,
                TestResult.status.in_(FAILED_STATUSES),
                Run.complete.is_(True),
                Run.started_at >= episode.first_failure_at,
                Run.started_at <= upper,
            )
        )
        or 0
    )


def _get_or_create_lifecycle(session: Session, identity_id: int) -> TestLifecycle:
    lc = session.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == identity_id))
    if lc is None:
        lc = TestLifecycle(test_identity_id=identity_id)
        session.add(lc)
    return lc


def apply_run(session: Session, run: Run, *, baseline: Run | None = None) -> RunAnalysis:
    """Advance lifecycle + episodes for ``run`` vs its baseline. Idempotent per (baseline, run).

    ``baseline`` defaults to :func:`select_baseline`; pass it explicitly to avoid a re-query. Only
    call for **complete** runs — an incomplete run's absent tests would be misread as removals.
    """
    if baseline is None:
        baseline = select_baseline(session, run)

    current = identity_status_map(session, run)
    base_status = identity_status_map(session, baseline) if baseline is not None else {}
    diff = compute_diff(session, run, baseline, current=current, baseline_status=base_status)
    analysis = RunAnalysis(baseline_run_id=diff.baseline_run_id, diff=diff)

    for identity_id in diff.regressions:
        lc = _get_or_create_lifecycle(session, identity_id)
        episode = _open_episode(session, identity_id)
        newly_opened = episode is None
        if newly_opened:
            prior = _episode_count(session, identity_id)
            episode = FailureEpisode(
                test_identity_id=identity_id,
                episode_number=prior + 1,
                first_failure_run_id=run.id,
                first_failure_at=run.started_at,
            )
            session.add(episode)
            session.flush()  # need episode.id for the current_episode back-pointer
            if prior > 0:  # reopen: clear acknowledgement, count the reopen
                lc.reopen_count = prior
                lc.acknowledged = False
                lc.acknowledged_by = None
                lc.acknowledged_at = None
            analysis.opened_episodes.append((identity_id, episode.id))
        episode.last_failing_run_id = run.id
        episode.last_failing_at = run.started_at
        episode.is_open = True
        episode.age_runs = _age_runs(session, identity_id, episode)
        lc.state = LifecycleState.FAILING
        lc.current_episode_id = episode.id
        lc.last_failing_run_id = run.id
        lc.last_failing_at = run.started_at
        if lc.all_time_first_failure_run_id is None:
            lc.all_time_first_failure_run_id = run.id
            lc.all_time_first_failure_at = run.started_at

    for identity_id in diff.still_failing:
        lc = _get_or_create_lifecycle(session, identity_id)
        episode = _open_episode(session, identity_id)
        if episode is None:  # defensive: failing in baseline but no episode yet — open one
            episode = FailureEpisode(
                test_identity_id=identity_id,
                episode_number=_episode_count(session, identity_id) + 1,
                first_failure_run_id=run.id,
                first_failure_at=run.started_at,
            )
            session.add(episode)
            session.flush()
            analysis.opened_episodes.append((identity_id, episode.id))
        episode.last_failing_run_id = run.id
        episode.last_failing_at = run.started_at
        episode.age_runs = _age_runs(session, identity_id, episode)
        lc.state = LifecycleState.FAILING
        lc.current_episode_id = episode.id
        lc.last_failing_run_id = run.id
        lc.last_failing_at = run.started_at

    for identity_id in diff.newly_fixed:
        lc = _get_or_create_lifecycle(session, identity_id)
        episode = _open_episode(session, identity_id)
        if episode is not None:
            episode.fixed_in_run_id = run.id
            episode.fixed_at = run.started_at
            episode.is_open = False
            episode.age_runs = _age_runs(session, identity_id, episode)
            lc.current_episode_id = episode.id
        lc.state = LifecycleState.FIXED

    for identity_id in diff.removed:
        lc = _get_or_create_lifecycle(session, identity_id)
        # Episode stays open — a disappearance is never counted as a fix.
        lc.state = LifecycleState.REMOVED

    run.baseline_run_id = diff.baseline_run_id
    return analysis
