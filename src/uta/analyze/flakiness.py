"""Oscillation-based flakiness.

Because **every** run is triggered by a trunk commit, "fails then passes" is never "no change" —
there is always a change in play. So flakiness is **not** measured as a fail-rate; it is measured as
**oscillation**: how much a test flip-flops over the window.

- Build the test's pass/fail sequence from the runs in which it **actually produced a result**,
  ordered by run start. Tracks are collapsed per run (FAILED in either ⇒ that run is a fail).
- **Gaps are not transitions.** Incomplete runs and runs where the test was absent leave holes; they
  are simply not in the sequence, so a never-reporting shard is never miscounted as a ``fail→pass``.
- **Score = state transitions ÷ runs** over the window. A clean regression is *one* transition
  (then stays failing); a clean fix is *one* (then stays passing). Many transitions = flaky.
- A test is **FLAKY** when it oscillates: ``score ≥ threshold`` **and** its fail-rate is strictly
  between 0 and 1 (≥1 back-and-forth flip). A solidly-failing test (fail-rate ≈ 1, no flips) is a
  regression, not flaky.

The candidate code/data change signals are still attached for triage but do **not** gate the flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import Run, TestLifecycle, TestResult

# Statuses that count as the test having *produced a result* (a data point in the sequence).
# SKIPPED is treated as a hole (no signal), like an absent shard.
_REPORTED = FAILED_STATUSES | frozenset({"PASSED", "FIXED"})


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class FlakinessStats:
    failed_total: int  # all-time runs in which the test failed
    failed_in_window: int
    last_failed_at: datetime | None
    runs_in_window: int  # runs that produced a result in the window
    transitions: int
    score: float  # transitions ÷ runs_in_window
    fail_rate: float  # fails ÷ runs_in_window
    flaky: bool
    shard_correlated: bool
    pattern: str  # "consecutive" | "intermittent" | "stable" | "none"


@dataclass
class _RunPoint:
    started_at: datetime
    build: int
    failed: bool
    fail_tracks: frozenset[str]
    pass_tracks: frozenset[str]


def _sequence(session: Session, identity_id: int) -> list[_RunPoint]:
    """The test's per-run pass/fail points, oldest-first, only complete runs that produced a result.

    Tracks are collapsed: a run is a *fail* if the test FAILED in any track; a data point exists
    only if the test reported (passed or failed) in at least one track — absent/SKIPPED-only runs
    are holes, not points.
    """
    rows = session.execute(
        select(Run.id, Run.build_number, Run.started_at, TestResult.track, TestResult.status)
        .join(Run, Run.id == TestResult.run_id)
        .where(TestResult.test_identity_id == identity_id, Run.complete.is_(True))
        .order_by(Run.started_at, Run.id)
    ).all()

    by_run: dict[int, _RunPoint] = {}
    order: list[int] = []
    for run_id, build_number, started_at, track, status in rows:
        if status not in _REPORTED:
            continue
        point = by_run.get(run_id)
        if point is None:
            point = _RunPoint(_aware(started_at), build_number, False, frozenset(), frozenset())
            by_run[run_id] = point
            order.append(run_id)
        if status in FAILED_STATUSES:
            point.failed = True
            point.fail_tracks = point.fail_tracks | {track}
        else:
            point.pass_tracks = point.pass_tracks | {track}
    return [by_run[r] for r in order]


def _pattern(seq: list[bool]) -> str:
    """Describe the failure shape of a fail/pass sequence."""
    fails = sum(seq)
    if fails == 0:
        return "none"
    if fails == len(seq):
        return "stable"
    # One contiguous block of failures ⇒ consecutive; otherwise intermittent (interleaved).
    blocks = sum(1 for i, v in enumerate(seq) if v and (i == 0 or not seq[i - 1]))
    return "consecutive" if blocks == 1 else "intermittent"


def compute_stats(
    session: Session,
    identity_id: int,
    *,
    window_days: int = 30,
    threshold: float = 0.3,
    now: datetime | None = None,
) -> FlakinessStats:
    """Flakiness + failure-history stats for one test."""
    now = now or _now()
    cutoff = now - timedelta(days=window_days)
    seq = _sequence(session, identity_id)

    failed_total = sum(1 for p in seq if p.failed)
    last_failed_at = max((p.started_at for p in seq if p.failed), default=None)

    window = [p for p in seq if p.started_at and p.started_at >= cutoff]
    runs_in_window = len(window)
    fails_in_window = sum(1 for p in window if p.failed)

    states = [p.failed for p in window]
    transitions = sum(1 for i in range(1, len(states)) if states[i] != states[i - 1])
    score = transitions / runs_in_window if runs_in_window else 0.0
    fail_rate = fails_in_window / runs_in_window if runs_in_window else 0.0

    flaky = 0.0 < fail_rate < 1.0 and score >= threshold

    # Shard-correlated: among the failing runs, do the failures cluster in ONE track while the other
    # track passes? A consistent single-track failure is a strong infra/flaky tell.
    single_track_fails = sum(
        1 for p in window if p.failed and p.pass_tracks and len(p.fail_tracks) == 1
    )
    shard_correlated = fails_in_window > 0 and single_track_fails == fails_in_window

    return FlakinessStats(
        failed_total=failed_total,
        failed_in_window=fails_in_window,
        last_failed_at=last_failed_at,
        runs_in_window=runs_in_window,
        transitions=transitions,
        score=round(score, 4),
        fail_rate=round(fail_rate, 4),
        flaky=flaky,
        shard_correlated=shard_correlated,
        pattern=_pattern(states),
    )


def history(
    session: Session,
    identity_id: int,
    *,
    window_days: int = 30,
    now: datetime | None = None,
) -> list[dict]:
    """The test's oldest-first pass/fail points within the window, for sparkline rendering.

    Same windowing as :func:`compute_stats` (``started_at >= now - window_days``), so a sparkline
    and its test's flakiness card always agree on which runs are "in window".
    """
    now = now or _now()
    cutoff = now - timedelta(days=window_days)
    seq = _sequence(session, identity_id)
    return [
        {"build": p.build, "started_at": p.started_at, "failed": p.failed}
        for p in seq
        if p.started_at and p.started_at >= cutoff
    ]


def recompute_flaky_flags(
    session: Session,
    *,
    window_days: int = 30,
    threshold: float = 0.3,
    now: datetime | None = None,
) -> int:
    """Refresh ``lifecycle.flaky`` for every test that has a lifecycle row. Returns #flaky.

    Driven after each complete run is analysed. Only ever-failing tests have a lifecycle row, so
    this walks the small failing set, not all ~25k tests. Idempotent: derived purely from results.
    """
    now = now or _now()
    flaky_count = 0
    for lc in session.scalars(select(TestLifecycle)).all():
        stats = compute_stats(
            session, lc.test_identity_id, window_days=window_days, threshold=threshold, now=now
        )
        lc.flaky = stats.flaky
        flaky_count += int(stats.flaky)
    return flaky_count


def leaderboard_candidates(
    session: Session,
    *,
    window_days: int = 30,
    threshold: float = 0.3,
    now: datetime | None = None,
) -> list[dict]:
    """Every leaderboard candidate (oscillating/flaky test), ranked, with **no display limit**.

    This is the true set of unstable tests in the window; ``leaderboard`` slices it for display.
    """
    from uta.models import TestIdentity

    now = now or _now()
    rows: list[dict] = []
    for lc in session.scalars(select(TestLifecycle)).all():
        stats = compute_stats(
            session, lc.test_identity_id, window_days=window_days, threshold=threshold, now=now
        )
        if stats.transitions == 0 and not stats.flaky:
            continue  # never oscillated — not a leaderboard candidate
        ident = session.get(TestIdentity, lc.test_identity_id)
        rows.append(
            {
                "identity_id": lc.test_identity_id,
                "test_id": ident.canonical_name if ident else str(lc.test_identity_id),
                "owner": ident.main_developer if ident else None,
                "flaky": stats.flaky,
                "score": stats.score,
                "transitions": stats.transitions,
                "runs_in_window": stats.runs_in_window,
                "fail_rate": stats.fail_rate,
                "failed_total": stats.failed_total,
                "failed_in_window": stats.failed_in_window,
                "last_failed_at": stats.last_failed_at,
                "shard_correlated": stats.shard_correlated,
                "pattern": stats.pattern,
            }
        )
    rows.sort(key=lambda r: (r["flaky"], r["score"], r["transitions"]), reverse=True)
    return rows


def leaderboard(
    session: Session,
    *,
    window_days: int = 30,
    threshold: float = 0.3,
    limit: int = 50,
    now: datetime | None = None,
) -> list[dict]:
    """The flaky-leaderboard rows: most-unstable tests first, score then transitions."""
    candidates = leaderboard_candidates(
        session, window_days=window_days, threshold=threshold, now=now
    )
    return candidates[:limit]
