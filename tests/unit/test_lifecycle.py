"""Lifecycle state machine + failure episodes (uta.analyze.lifecycle)."""

from __future__ import annotations

from sqlalchemy import func, select

from tests.builders import get_identity, make_run
from uta.analyze.lifecycle import apply_run
from uta.db import session_scope
from uta.models import FailureEpisode, TestLifecycle
from uta.models.enums import LifecycleState


def _lc(session, name):
    ident = get_identity(session, name)
    return session.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident.id))


def _episodes(session, name):
    ident = get_identity(session, name)
    return session.scalars(
        select(FailureEpisode)
        .where(FailureEpisode.test_identity_id == ident.id)
        .order_by(FailureEpisode.episode_number)
    ).all()


def test_new_failure_opens_episode_and_sets_failing(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        analysis = apply_run(s, run, baseline=None)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.FAILING
        assert lc.reopen_count == 0
        episodes = _episodes(s, "t")
        assert len(episodes) == 1 and episodes[0].is_open
        assert episodes[0].first_failure_run_id == run.id
        assert lc.all_time_first_failure_run_id == run.id
        assert len(analysis.opened_episodes) == 1


def test_fix_closes_episode(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"t": "PASSED"})
        apply_run(s, r2, baseline=r1)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.FIXED
        ep = _episodes(s, "t")[0]
        assert ep.is_open is False
        assert ep.fixed_in_run_id == r2.id


def test_reopen_opens_new_episode_bumps_count_clears_ack(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"t": "PASSED"})
        apply_run(s, r2, baseline=r1)
        # A human acknowledged it before it reopened.
        lc = _lc(s, "t")
        lc.acknowledged = True
        lc.acknowledged_by = "alice"
        s.flush()
        r3 = make_run(s, 3, {"t": "FAILED"})
        apply_run(s, r3, baseline=r2)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.FAILING
        assert lc.reopen_count == 1
        assert lc.acknowledged is False and lc.acknowledged_by is None
        eps = _episodes(s, "t")
        assert len(eps) == 2
        assert eps[1].episode_number == 2 and eps[1].is_open


def test_removed_keeps_episode_open(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"other": "PASSED"})  # "t" absent
        apply_run(s, r2, baseline=r1)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.REMOVED
        ep = _episodes(s, "t")[0]
        assert ep.is_open is True  # disappeared != fixed
        assert ep.fixed_in_run_id is None


def test_removed_then_reappearing_pass_closes_episode(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"other": "PASSED"})  # "t" absent -> REMOVED, episode open
        apply_run(s, r2, baseline=r1)
        r3 = make_run(s, 3, {"t": "PASSED", "other": "PASSED"})  # reappears passing
        analysis = apply_run(s, r3, baseline=r2)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.FIXED
        ep = _episodes(s, "t")[0]
        assert ep.is_open is False
        assert ep.fixed_in_run_id == r3.id
        assert get_identity(s, "t").id in analysis.diff.newly_fixed
        # Re-applying the same run stays idempotent: nothing open to reconcile.
        apply_run(s, r3, baseline=r2)
        eps = _episodes(s, "t")
        assert len(eps) == 1 and eps[0].is_open is False


def test_removed_then_reappearing_failure_continues_same_episode(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"other": "PASSED"})  # "t" absent -> REMOVED, episode open
        apply_run(s, r2, baseline=r1)
        r3 = make_run(s, 3, {"t": "FAILED", "other": "PASSED"})  # reappears still failing
        apply_run(s, r3, baseline=r2)
        lc = _lc(s, "t")
        assert lc.state == LifecycleState.FAILING
        assert lc.reopen_count == 0  # same episode continues — not a reopen
        eps = _episodes(s, "t")
        assert len(eps) == 1 and eps[0].is_open
        assert eps[0].last_failing_run_id == r3.id
        assert eps[0].fixed_in_run_id is None


def test_still_failing_extends_episode_and_age(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"t": "FAILED"})
        apply_run(s, r2, baseline=r1)
        ep = _episodes(s, "t")[0]
        assert ep.last_failing_run_id == r2.id
        assert ep.age_runs == 2  # failed in two complete runs


def test_reapply_same_run_is_idempotent(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        apply_run(s, r1, baseline=None)  # re-apply
        n_eps = s.scalar(select(func.count()).select_from(FailureEpisode))
        n_lc = s.scalar(select(func.count()).select_from(TestLifecycle))
        assert n_eps == 1 and n_lc == 1
