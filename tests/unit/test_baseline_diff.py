"""Baseline selection + run diff (uta.analyze.baseline)."""

from __future__ import annotations

from datetime import timedelta

from tests.builders import _EPOCH, get_identity, make_run
from uta.analyze.baseline import FAILED, compute_diff, identity_status_map, select_baseline
from uta.db import session_scope


def test_failed_in_any_track_collapses_to_failed(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {})
        ident = get_identity(s, "pkg.Test.t")
        # One track passes, the other fails -> identity is FAILED.
        from uta.models import TestResult

        run.results.append(TestResult(identity=ident, track="permanent", status="PASSED"))
        run.results.append(TestResult(identity=ident, track="permanent_py39", status="FAILED"))
        s.flush()
        assert identity_status_map(s, run)[ident.id] == FAILED


def test_baseline_is_most_recent_complete_run(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"a": "PASSED"})
        make_run(s, 2, {"a": "PASSED"}, complete=False)  # incomplete — must be skipped
        r3 = make_run(s, 3, {"a": "PASSED"})
        assert select_baseline(s, r3).id == r1.id  # not the incomplete r2


def test_diff_buckets(session_factory):
    with session_scope(session_factory) as s:
        base = make_run(s, 1, {"fixed": "FAILED", "still": "FAILED", "stays": "PASSED"})
        run = make_run(
            s,
            2,
            {"fixed": "PASSED", "still": "FAILED", "regressed": "FAILED", "stays": "PASSED"},
        )
        diff = compute_diff(s, run, base)
        name = {get_identity(s, n).id: n for n in ["fixed", "still", "stays", "regressed"]}
        assert {name[i] for i in diff.regressions} == {"regressed"}
        assert {name[i] for i in diff.newly_fixed} == {"fixed"}
        assert {name[i] for i in diff.still_failing} == {"still"}
        assert diff.removed == []
        assert diff.baseline_run_id == base.id


def test_removed_when_failing_test_disappears(session_factory):
    with session_scope(session_factory) as s:
        base = make_run(s, 1, {"gone": "FAILED", "ok": "PASSED"})
        run = make_run(s, 2, {"ok": "PASSED"})  # "gone" absent entirely
        diff = compute_diff(s, run, base)
        assert diff.removed == [get_identity(s, "gone").id]


def test_first_run_has_no_baseline_all_failures_are_regressions(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"a": "FAILED", "b": "PASSED"}, started_at=_EPOCH + timedelta(hours=1))
        diff = compute_diff(s, run, None)
        assert diff.baseline_run_id is None
        assert diff.regressions == [get_identity(s, "a").id]
