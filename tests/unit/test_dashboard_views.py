"""Dashboard read-side projections (uta.web.views) and write-side actions (uta.web.actions).

Exercised against hand-built run sequences (via the lifecycle state machine) on in-memory SQLite —
no Jenkins/Oracle/Postgres. Covers the triage buckets, the per-test record, the run diff, and the
acknowledge/confirm/attribute provenance logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.builders import _EPOCH, get_identity, make_run
from uta.analyze.classify import classify_run
from uta.analyze.lifecycle import apply_run
from uta.db import session_scope
from uta.models import (
    Classification,
    CodeChangeCandidate,
    FailureEpisode,
    PollerHeartbeat,
    TestLifecycle,
)
from uta.models.enums import PredictedCause, Provenance
from uta.web import actions, views


def _lc(session, name):
    ident = get_identity(session, name)
    return session.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident.id))


# ── triage queue ──────────────────────────────────────────────────────────


def test_new_bucket_holds_unacknowledged_failures(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        q = views.triage_queue(s)
        assert q["counts"]["new"] == 1
        assert q["new"][0]["test_id"] == "t"
        assert q["counts"]["still_failing"] == 0


def test_acknowledged_failure_moves_to_still_failing(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        assert actions.acknowledge(s, get_identity(s, "t").id, "alice") is True
        q = views.triage_queue(s)
        assert q["counts"]["new"] == 0
        assert q["counts"]["still_failing"] == 1
        assert q["still_failing"][0]["acknowledged"] is True


def test_removed_open_episode_surfaces_in_still_failing_with_flag(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"other": "PASSED"})  # "t" absent → REMOVED, episode stays open
        apply_run(s, r2, baseline=r1)
        q = views.triage_queue(s)
        removed = [r for r in q["still_failing"] if r["test_id"] == "t"]
        assert removed and removed[0]["removed"] is True


def test_recently_fixed_window_includes_recent_excludes_old(session_factory):
    now = datetime.now(UTC)
    with session_scope(session_factory) as s:
        # Recent fix: fail then pass a day ago.
        r1 = make_run(s, 1, {"recent": "FAILED"}, started_at=now - timedelta(days=2))
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"recent": "PASSED"}, started_at=now - timedelta(days=1))
        apply_run(s, r2, baseline=r1)
        # Old fix: fixed well outside the 7-day window.
        r3 = make_run(s, 3, {"old": "FAILED"}, started_at=now - timedelta(days=40))
        apply_run(s, r3, baseline=None)
        r4 = make_run(s, 4, {"old": "PASSED"}, started_at=now - timedelta(days=39))
        apply_run(s, r4, baseline=r3)

        q = views.triage_queue(s, recently_fixed_days=7)
        names = {r["test_id"] for r in q["recently_fixed"]}
        assert "recent" in names
        assert "old" not in names


# ── long-list capping (issue #19) ─────────────────────────────────────────────


def test_triage_new_bucket_capped_with_full_count(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        q = views.triage_queue(s, limit=2)
        # Rows are capped to the limit, but the count reports the true total.
        assert len(q["new"]) == 2
        assert q["counts"]["new"] == 5
        assert q["truncated"]["new"] is True


def test_triage_expand_renders_bucket_in_full(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        q = views.triage_queue(s, limit=2, expand=["new"])
        assert len(q["new"]) == 5
        assert q["truncated"]["new"] is False


def test_triage_limit_zero_disables_cap(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        q = views.triage_queue(s, limit=0)
        assert len(q["new"]) == 5
        assert q["truncated"]["new"] is False


def test_run_results_capped_with_full_total(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        # 5 tests × 2 tracks = 10 result rows.
        summary = views.run_summary(s, 1, limit=3)
        assert len(summary["results"]) == 3
        assert summary["results_total"] == 10
        # Expanding renders every row.
        full = views.run_summary(s, 1, limit=3, expand=["results"])
        assert len(full["results"]) == 10


# ── per-test record ─────────────────────────────────────────────────────────


def test_test_record_exposes_lifecycle_and_episode(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"t": "FAILED"},
            error_type={"t": "assertion"},
            errors={"t": ("boom went the assertion", "Traceback ...\n  line 3")},
        )
        apply_run(s, r1, baseline=None)
        ident_id = get_identity(s, "t").id
        rec = views.test_record(s, ident_id)
        assert rec["test_id"] == "t"
        assert rec["lifecycle"]["state"] == "FAILING"
        assert len(rec["episodes"]) == 1
        assert rec["episodes"][0]["is_open"] is True
        # The single "latest_failure" section is gone; error detail hangs off the episode now.
        assert "latest_failure" not in rec
        failure = rec["episodes"][0]["failure"]
        assert failure["status"] == "FAILED"
        assert failure["error_type"] == "assertion"
        assert failure["error_details"] == "boom went the assertion"
        assert failure["error_stack_trace"].startswith("Traceback")
        assert failure["run"]["build"] == 1


def test_test_record_scopes_failure_detail_per_episode(session_factory):
    """Each episode carries the error detail of *its own* last-failing run, not the newest one."""
    with session_scope(session_factory) as s:
        # Episode 1: fail in #1, fixed in #2.
        r1 = make_run(s, 1, {"t": "FAILED"}, errors={"t": ("first-episode error", None)})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"t": "PASSED"})
        apply_run(s, r2, baseline=r1)
        # Episode 2 (reopen): fail again in #3 with a different error.
        r3 = make_run(s, 3, {"t": "REGRESSION"}, errors={"t": ("second-episode error", None)})
        apply_run(s, r3, baseline=r2)

        ident_id = get_identity(s, "t").id
        rec = views.test_record(s, ident_id)
        eps = {e["episode_number"]: e for e in rec["episodes"]}
        assert eps[1]["failure"]["error_details"] == "first-episode error"
        assert eps[1]["is_open"] is False
        assert eps[2]["failure"]["error_details"] == "second-episode error"
        assert eps[2]["is_open"] is True
        # The current+open episode is #2.
        assert rec["lifecycle"]["current_episode_id"] == eps[2]["id"]


def test_test_record_exposes_zephyr_test_cases(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"}, errors={"t": ("boom", None)})
        apply_run(s, r1, baseline=None)
        ident = get_identity(s, "t")
        ident.zephyr_test_cases = "LX-T4792,LX-T5001"
        s.flush()
        rec = views.test_record(s, ident.id)
        assert rec["zephyr_test_cases"] == ["LX-T4792", "LX-T5001"]


def test_test_record_zephyr_test_cases_empty_when_unset(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"}, errors={"t": ("boom", None)})
        apply_run(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
        assert rec["zephyr_test_cases"] == []


def test_test_record_missing_identity_is_none(session_factory):
    with session_scope(session_factory) as s:
        assert views.test_record(s, 9999) is None


def test_test_record_exposes_sparkline_history(session_factory):
    """Anchored to *now* (not a fixed epoch) so the run stays inside the default flaky window."""
    base = datetime.now(UTC) - timedelta(days=2)
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"}, started_at=base)
        apply_run(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
    assert rec["spark"].bars == [{"x": 0.0, "width": 120.0, "failed": True, "build": 1}]


# ── run summary ──────────────────────────────────────────────────────────────


def test_run_summary_diff_against_baseline(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_run(s, r2, baseline=r1)
        summary = views.run_summary(s, 2)
        assert summary["build"] == 2
        assert summary["baseline"]["build"] == 1
        regressed = {r["test_id"] for r in summary["diff"]["regressions"]}
        fixed = {r["test_id"] for r in summary["diff"]["newly_fixed"]}
        assert "b" in regressed and "a" in fixed
        assert "totals" in summary and "shards" in summary


def test_run_summary_unknown_build_is_none(session_factory):
    with session_scope(session_factory) as s:
        assert views.run_summary(s, 12345) is None


# ── job runs (issue #37) ──────────────────────────────────────────────────────


def test_job_runs_lists_newest_first_with_diff_counts(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_run(s, r2, baseline=r1)

        result = views.job_runs(s)
        assert [row["build"] for row in result["runs"]] == [2, 1]  # newest first
        newest = result["runs"][0]
        assert newest["status"] == "SUCCESS"
        assert newest["regressions"] == 1  # b newly failing
        assert newest["newly_fixed"] == 1  # a fixed
        assert newest["duration_seconds"] == 1800.0  # make_run runs are 30 min
        # First run has no baseline: every failure is a regression, nothing newly fixed.
        oldest = result["runs"][1]
        assert oldest["regressions"] == 1  # a
        assert oldest["newly_fixed"] == 0


def test_job_runs_totals_and_poller_next(session_factory):
    now = datetime.now(UTC)
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"a": "PASSED"})
        r1.total_passed, r1.total_failed, r1.total_skipped = 10, 2, 1
        apply_run(s, r1, baseline=None)
        s.add(PollerHeartbeat(id=1, last_poll_at=now, last_processed_count=1))
        s.flush()

        result = views.job_runs(s, poll_interval_seconds=300)
        totals = result["runs"][0]["totals"]
        assert totals == {"passed": 10, "failed": 2, "skipped": 1, "total": 13}
        poller = result["poller"]
        # SQLite drops tzinfo on round-trip; compare tz-normalized (as the view does downstream).
        last = views._aware(poller["last_poll_at"])
        assert last == now
        assert poller["next_poll_at"] == last + timedelta(seconds=300)


def test_job_runs_empty_store_and_no_heartbeat(session_factory):
    with session_scope(session_factory) as s:
        result = views.job_runs(s, poll_interval_seconds=300)
        assert result["runs"] == []
        assert result["poller"]["last_poll_at"] is None
        assert result["poller"]["next_poll_at"] is None
        assert result["timeline"] is None


def test_job_runs_timeline_is_oldest_first(session_factory):
    """The timeline chart reads left-to-right in time, unlike the (newest-first) table rows."""
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_run(s, r1, baseline=None)
        r2 = make_run(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_run(s, r2, baseline=r1)

        result = views.job_runs(s)
        tl = result["timeline"]
        assert tl.first_build == 1
        assert tl.last_build == 2
        assert tl.runs == 2


# ── actions: provenance ─────────────────────────────────────────────────────────


def _episode_id(session, name) -> int:
    lc = _lc(session, name)
    return lc.current_episode_id


def test_set_attribution_human_entered_when_no_ai(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_id = _episode_id(s, "t")
        attr = actions.set_attribution(
            s, ep_id, "bob", causing_person="carol", reason_text="bad fixture"
        )
        assert attr.causing_person == "carol"
        assert attr.cause_provenance == Provenance.HUMAN_ENTERED
        assert attr.reason_provenance == Provenance.HUMAN_ENTERED
        assert attr.entered_by == "bob" and attr.validated_by == "bob"


def test_confirm_accepts_ai_suggestion(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_id = _episode_id(s, "t")
        # Seed an AI suggestion to confirm.
        s.add(
            Classification(
                episode_id=ep_id,
                predicted_cause=PredictedCause.CODE_CHANGE,
                suggested_contact="dev-dave",
                llm_hypothesis="likely the trunk commit r123",
            )
        )
        s.flush()
        attr = actions.confirm(s, ep_id, "alice")
        assert attr.causing_person == "dev-dave"
        assert attr.reason_text == "likely the trunk commit r123"
        assert attr.cause_provenance == Provenance.AI_CONFIRMED
        assert attr.reason_provenance == Provenance.AI_CONFIRMED
        assert attr.validated_by == "alice"


def test_confirm_stamps_classifier_suggested_contact(session_factory):
    # End-to-end: the deterministic classifier suggests the sole commit author (#49), and one-click
    # Confirm stamps that person as causing_person with AI_CONFIRMED provenance.
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        run.code_changes.append(
            CodeChangeCandidate(commit_id="r777", author="dev-dave", committed_at=_EPOCH)
        )
        analysis = apply_run(s, run, baseline=None)
        s.flush()
        classify_run(s, run, analysis.opened_episodes)
        s.flush()
        ep_id = _episode_id(s, "t")
        attr = actions.confirm(s, ep_id, "alice")
        assert attr.causing_person == "dev-dave"
        assert attr.cause_provenance == Provenance.AI_CONFIRMED
        assert attr.original_ai_cause == "dev-dave"


def test_set_attribution_correction_retains_original_ai(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_id = _episode_id(s, "t")
        s.add(
            Classification(
                episode_id=ep_id,
                predicted_cause=PredictedCause.CODE_CHANGE,
                suggested_contact="dev-dave",
                llm_hypothesis="trunk commit r123",
            )
        )
        s.flush()
        attr = actions.set_attribution(
            s, ep_id, "alice", causing_person="real-rita", reason_text="ut_ref table X changed"
        )
        assert attr.cause_provenance == Provenance.HUMAN_CORRECTED
        assert attr.original_ai_cause == "dev-dave"
        assert attr.reason_provenance == Provenance.HUMAN_CORRECTED
        assert attr.original_ai_reason == "trunk commit r123"


def test_set_attribution_sets_and_clears_jira_ticket(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_id = _episode_id(s, "t")
        ep = s.get(FailureEpisode, ep_id)
        # Set a ticket (trimmed); it lives on the episode, not the Attribution row.
        actions.set_attribution(s, ep_id, "bob", jira_ticket="  ABC-123  ")
        assert ep.jira_ticket == "ABC-123"
        # Omitting the field leaves it untouched…
        actions.set_attribution(s, ep_id, "bob", causing_person="carol")
        assert ep.jira_ticket == "ABC-123"
        # …and an empty submission clears it.
        actions.set_attribution(s, ep_id, "bob", jira_ticket="")
        assert ep.jira_ticket is None


def test_acknowledge_unknown_identity_returns_false(session_factory):
    with session_scope(session_factory) as s:
        assert actions.acknowledge(s, 4242, "alice") is False
