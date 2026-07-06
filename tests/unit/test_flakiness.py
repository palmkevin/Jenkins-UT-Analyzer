"""Oscillation flakiness.

Pins the definition that makes this pipeline-correct: flakiness is *oscillation*, not fail-rate;
gaps are missing data (never flips); a solidly-failing test is a regression, not flaky.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from tests.builders import get_identity, make_run
from uta.analyze.flakiness import (
    compute_stats,
    history,
    leaderboard,
    leaderboard_candidates,
    recompute_flaky_flags,
)
from uta.models import TestLifecycle

NOW = datetime(2026, 7, 1, tzinfo=UTC)
T = "ut_pkg.mod.test_x"


def _stats(session, name=T):
    ident = get_identity(session, name)
    return compute_stats(session, ident.id, window_days=30, threshold=0.3, now=NOW)


def test_clean_regression_is_not_flaky(session_factory):
    with session_factory() as s:
        for b, st in enumerate(["PASSED", "PASSED", "FAILED", "FAILED", "FAILED"], start=1):
            make_run(s, b, {T: st})
        s.commit()
        st = _stats(s)
    assert st.transitions == 1  # pass→fail once, then stays failing
    assert st.flaky is False
    assert st.pattern == "consecutive"


def test_oscillation_is_flaky(session_factory):
    with session_factory() as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED", "PASSED"], start=1):
            make_run(s, b, {T: st})
        s.commit()
        st = _stats(s)
    assert st.transitions == 4
    assert st.score == 0.8
    assert 0 < st.fail_rate < 1
    assert st.flaky is True
    assert st.pattern == "intermittent"


def test_solidly_failing_is_not_flaky(session_factory):
    with session_factory() as s:
        for b in range(1, 5):
            make_run(s, b, {T: "FAILED"})
        s.commit()
        st = _stats(s)
    assert st.fail_rate == 1.0
    assert st.transitions == 0
    assert st.flaky is False
    assert st.pattern == "stable"


def test_gaps_are_not_transitions(session_factory):
    """A run where the test is absent is a hole, not a fail→pass flip."""
    with session_factory() as s:
        make_run(s, 1, {T: "FAILED"})
        make_run(s, 2, {"other.test": "PASSED"})  # T absent — a gap
        make_run(s, 3, {T: "FAILED"})
        s.commit()
        st = _stats(s)
    assert st.runs_in_window == 2  # only the two runs that produced a result
    assert st.transitions == 0  # fail … fail — the gap is not a flip
    assert st.flaky is False


def test_incomplete_runs_excluded(session_factory):
    with session_factory() as s:
        make_run(s, 1, {T: "FAILED"})
        make_run(s, 2, {T: "PASSED"}, complete=False)  # incomplete — not a data point
        make_run(s, 3, {T: "FAILED"})
        s.commit()
        st = _stats(s)
    assert st.runs_in_window == 2
    assert st.transitions == 0


def test_shard_correlation(session_factory):
    """Failures concentrated in one track (other passes) are flagged shard-correlated."""
    with session_factory() as s:
        make_run(s, 1, {T: "PASSED"})
        make_run(s, 2, {T: "FAILED"}, fail_tracks={T: ("permanent",)})
        make_run(s, 3, {T: "PASSED"})
        make_run(s, 4, {T: "FAILED"}, fail_tracks={T: ("permanent",)})
        s.commit()
        st = _stats(s)
    assert st.shard_correlated is True
    assert st.flaky is True


def test_history_counts(session_factory):
    with session_factory() as s:
        for b, st in enumerate(["FAILED", "PASSED", "FAILED"], start=1):
            make_run(s, b, {T: st})
        s.commit()
        st = _stats(s)
    assert st.failed_total == 2
    assert st.failed_in_window == 2
    assert st.last_failed_at is not None


def test_history_is_oldest_first_within_window(session_factory):
    with session_factory() as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED"], start=1):
            make_run(s, b, {T: st})
        s.commit()
        ident = get_identity(s, T)
        points = history(s, ident.id, window_days=30, now=NOW)
    assert [p["failed"] for p in points] == [False, True, False]
    assert [p["build"] for p in points] == [1, 2, 3]


def test_history_excludes_gaps_and_incomplete_runs(session_factory):
    with session_factory() as s:
        make_run(s, 1, {T: "FAILED"})
        make_run(s, 2, {"other.test": "PASSED"})  # T absent — a gap, not a point
        make_run(s, 3, {T: "PASSED"}, complete=False)  # incomplete — excluded
        make_run(s, 4, {T: "PASSED"})
        s.commit()
        ident = get_identity(s, T)
        points = history(s, ident.id, window_days=30, now=NOW)
    assert [p["build"] for p in points] == [1, 4]


def test_recompute_sets_flag_and_leaderboard(session_factory):
    with session_factory() as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED"], start=1):
            make_run(s, b, {T: st})
        ident = get_identity(s, T)
        s.add(TestLifecycle(test_identity_id=ident.id))
        s.commit()

        n = recompute_flaky_flags(s, window_days=30, threshold=0.3, now=NOW)
        s.commit()
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident.id))
        board = leaderboard(s, window_days=30, threshold=0.3, now=NOW)

    assert n == 1
    assert lc.flaky is True
    assert board and board[0]["test_id"] == T and board[0]["flaky"] is True


def test_leaderboard_candidates_total_is_independent_of_limit(session_factory):
    """The full candidate count is the true total; ``limit`` only caps the displayed rows."""
    names = [f"ut_pkg.mod.test_{i}" for i in range(3)]
    with session_factory() as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED"], start=1):
            make_run(s, b, {n: st for n in names})
        for n in names:
            s.add(TestLifecycle(test_identity_id=get_identity(s, n).id))
        s.commit()

        candidates = leaderboard_candidates(s, window_days=30, threshold=0.3, now=NOW)
        capped = leaderboard(s, window_days=30, threshold=0.3, limit=2, now=NOW)

    assert len(candidates) == 3  # true count, unaffected by any display limit
    assert len(capped) == 2  # leaderboard slices the same candidate list
    assert capped == candidates[:2]
