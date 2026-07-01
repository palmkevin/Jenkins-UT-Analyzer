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
from datetime import UTC, datetime

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


def _aware(dt: datetime | None) -> datetime | None:
    """Normalize a possibly-naive datetime to UTC-aware for consistent comparisons (SQLite)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


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


def _preload_lifecycles(session: Session, identity_ids: set[int]) -> dict[int, TestLifecycle]:
    """Load lifecycle rows for the affected identities in one query (missing ones created here)."""
    lcs: dict[int, TestLifecycle] = {}
    if identity_ids:
        for lc in session.scalars(
            select(TestLifecycle).where(TestLifecycle.test_identity_id.in_(identity_ids))
        ).all():
            lcs[lc.test_identity_id] = lc
    for identity_id in identity_ids:
        if identity_id not in lcs:
            lc = TestLifecycle(test_identity_id=identity_id)
            session.add(lc)
            lcs[identity_id] = lc
    return lcs


def _preload_open_episodes(session: Session, identity_ids: set[int]) -> dict[int, FailureEpisode]:
    """Load the open episode (if any) per affected identity in one query."""
    episodes: dict[int, FailureEpisode] = {}
    if identity_ids:
        for ep in session.scalars(
            select(FailureEpisode).where(
                FailureEpisode.test_identity_id.in_(identity_ids),
                FailureEpisode.is_open.is_(True),
            )
        ).all():
            episodes[ep.test_identity_id] = ep
    return episodes


def _preload_episode_counts(session: Session, identity_ids: set[int]) -> dict[int, int]:
    """Count existing episodes per affected identity (for reopen numbering) in one grouped query."""
    counts: dict[int, int] = {}
    if identity_ids:
        rows = session.execute(
            select(FailureEpisode.test_identity_id, func.count())
            .where(FailureEpisode.test_identity_id.in_(identity_ids))
            .group_by(FailureEpisode.test_identity_id)
        ).all()
        for identity_id, count in rows:
            counts[identity_id] = count
    return counts


def _preload_failing_run_starts(
    session: Session, identity_ids: set[int]
) -> dict[int, list[datetime]]:
    """The distinct complete-run start times in which each affected identity failed (age source).

    Replaces the per-identity COUNT-DISTINCT age query with one scan: an episode's ``age_runs`` is
    then the number of these start times within ``[first_failure_at, upper]`` (computed in Python).
    """
    starts: dict[int, list[datetime]] = {}
    if not identity_ids:
        return starts
    rows = session.execute(
        select(TestResult.test_identity_id, TestResult.run_id, Run.started_at)
        .join(Run, Run.id == TestResult.run_id)
        .where(
            TestResult.test_identity_id.in_(identity_ids),
            TestResult.status.in_(FAILED_STATUSES),
            Run.complete.is_(True),
        )
        .distinct()
    ).all()
    seen: dict[int, set[int]] = {}
    for identity_id, run_id, started_at in rows:
        run_ids = seen.setdefault(identity_id, set())
        if run_id in run_ids:
            continue  # one run can have >1 failing track row — count the run once
        run_ids.add(run_id)
        starts.setdefault(identity_id, []).append(_aware(started_at))
    return starts


def _age_from_starts(
    starts: dict[int, list[datetime]], identity_id: int, episode: FailureEpisode
) -> int:
    """Age = distinct complete failing runs within the episode's open span (from the preload)."""
    upper = _aware(episode.fixed_at or episode.last_failing_at or episode.first_failure_at)
    lower = _aware(episode.first_failure_at)
    return sum(1 for s in starts.get(identity_id, ()) if lower <= s <= upper)


def apply_run(session: Session, run: Run, *, baseline: Run | None = None) -> RunAnalysis:
    """Advance lifecycle + episodes for ``run`` vs its baseline. Idempotent per (baseline, run).

    ``baseline`` defaults to :func:`select_baseline`; pass it explicitly to avoid a re-query. Only
    call for **complete** runs — an incomplete run's absent tests would be misread as removals.

    Batched: the affected identities' lifecycles, open episodes, episode counts and failing-run
    start times are each preloaded in a single query (not one round-trip per test), and all new
    episodes are flushed once. The transition logic and field updates are identical to the
    unbatched form, so results (and idempotency per (baseline, run)) are preserved.
    """
    if baseline is None:
        baseline = select_baseline(session, run)

    current = identity_status_map(session, run)
    base_status = identity_status_map(session, baseline) if baseline is not None else {}
    diff = compute_diff(session, run, baseline, current=current, baseline_status=base_status)
    analysis = RunAnalysis(baseline_run_id=diff.baseline_run_id, diff=diff)

    affected: set[int] = set(diff.regressions) | set(diff.still_failing)
    affected |= set(diff.newly_fixed) | set(diff.removed)
    # Age is only ever computed for the failing identities (regressions + still_failing + the
    # newly_fixed episode's final age); preload their failing-run start times together.
    failing_ids = set(diff.regressions) | set(diff.still_failing) | set(diff.newly_fixed)

    lifecycles = _preload_lifecycles(session, affected)
    open_episodes = _preload_open_episodes(session, affected)
    episode_counts = _preload_episode_counts(session, affected)
    starts = _preload_failing_run_starts(session, failing_ids)

    # New episodes opened this run, tracked so we can flush once then resolve their ids.
    new_episodes: list[tuple[int, FailureEpisode]] = []

    def _new_episode(identity_id: int) -> FailureEpisode:
        episode = FailureEpisode(
            test_identity_id=identity_id,
            episode_number=episode_counts.get(identity_id, 0) + 1,
            first_failure_run_id=run.id,
            first_failure_at=run.started_at,
        )
        session.add(episode)
        open_episodes[identity_id] = episode
        new_episodes.append((identity_id, episode))
        return episode

    for identity_id in diff.regressions:
        lc = lifecycles[identity_id]
        episode = open_episodes.get(identity_id)
        newly_opened = episode is None
        if newly_opened:
            prior = episode_counts.get(identity_id, 0)
            episode = _new_episode(identity_id)
            if prior > 0:  # reopen: clear acknowledgement, count the reopen
                lc.reopen_count = prior
                lc.acknowledged = False
                lc.acknowledged_by = None
                lc.acknowledged_at = None
        episode.last_failing_run_id = run.id
        episode.last_failing_at = run.started_at
        episode.is_open = True
        lc.state = LifecycleState.FAILING
        lc.last_failing_run_id = run.id
        lc.last_failing_at = run.started_at
        if lc.all_time_first_failure_run_id is None:
            lc.all_time_first_failure_run_id = run.id
            lc.all_time_first_failure_at = run.started_at

    for identity_id in diff.still_failing:
        lc = lifecycles[identity_id]
        episode = open_episodes.get(identity_id)
        if episode is None:  # defensive: failing in baseline but no episode yet — open one
            episode = _new_episode(identity_id)
        episode.last_failing_run_id = run.id
        episode.last_failing_at = run.started_at
        lc.state = LifecycleState.FAILING
        lc.last_failing_run_id = run.id
        lc.last_failing_at = run.started_at

    for identity_id in diff.newly_fixed:
        lc = lifecycles[identity_id]
        episode = open_episodes.get(identity_id)
        if episode is not None:
            episode.fixed_in_run_id = run.id
            episode.fixed_at = run.started_at
            episode.is_open = False
        lc.state = LifecycleState.FIXED

    for identity_id in diff.removed:
        lc = lifecycles[identity_id]
        # Episode stays open — a disappearance is never counted as a fix.
        lc.state = LifecycleState.REMOVED

    # Flush once so every new episode has an id (for the current_episode link + opened_episodes).
    if new_episodes:
        session.flush()
    for identity_id, episode in new_episodes:
        analysis.opened_episodes.append((identity_id, episode.id))

    # Ages + current_episode link, now that failing-run starts include this run and ids exist.
    for identity_id in diff.regressions:
        episode = open_episodes[identity_id]
        episode.age_runs = _age_from_starts(starts, identity_id, episode)
        lifecycles[identity_id].current_episode_id = episode.id
    for identity_id in diff.still_failing:
        episode = open_episodes[identity_id]
        episode.age_runs = _age_from_starts(starts, identity_id, episode)
        lifecycles[identity_id].current_episode_id = episode.id
    for identity_id in diff.newly_fixed:
        episode = open_episodes.get(identity_id)
        if episode is not None:
            episode.age_runs = _age_from_starts(starts, identity_id, episode)
            lifecycles[identity_id].current_episode_id = episode.id

    run.baseline_run_id = diff.baseline_run_id
    return analysis
