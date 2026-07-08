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
from uta.kb.store import record_signatures_for_run
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


def test_run_results_paginate_with_full_total(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        # 5 tests × 2 tracks = 10 result rows → 4 pages of 3.
        summary = views.run_summary(s, 1, limit=3)
        assert len(summary["results"]) == 3
        assert summary["results_total"] == 10
        assert (summary["page"], summary["pages"]) == (1, 4)
        # The last page carries the remainder; pages don't overlap.
        last = views.run_summary(s, 1, limit=3, page=4)
        assert len(last["results"]) == 1
        assert last["page"] == 4
        seen = [
            (r["test_id"], r["track"])
            for p in range(1, 5)
            for r in views.run_summary(s, 1, limit=3, page=p)["results"]
        ]
        assert len(seen) == 10
        assert len(set(seen)) == 10  # stable ordering — no row repeats across pages


def test_run_results_page_out_of_range_clamps(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        assert views.run_summary(s, 1, limit=3, page=99)["page"] == 4
        assert views.run_summary(s, 1, limit=3, page=0)["page"] == 1


def test_run_results_limit_zero_disables_pagination(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_run(s, r1, baseline=None)
        summary = views.run_summary(s, 1, limit=0)
        assert len(summary["results"]) == 10
        assert (summary["page"], summary["pages"]) == (1, 1)


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


def test_test_record_candidates_ranked_by_relevance_with_reasons(session_factory):
    """Candidates are ordered by relevance to *this* test, each carrying its match reason (#50)."""
    from uta.models import DataChangeCandidate

    stack = (
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/dev/ut_pkg/mod.py", line 7, in t\n'
        "AssertionError: lookup failed for LXFOO row\n"
    )
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"t": "FAILED"}, errors={"t": ("lookup failed for LXFOO row", stack)})
        # Earlier unrelated commit vs later commit touching the failing test's module.
        r1.code_changes.append(
            CodeChangeCandidate(
                commit_id="100",
                revision="100",
                committed_at=t0,
                paths='[{"editType": "edit", "file": "/trunk/lx/other/thing.py"}]',
            )
        )
        r1.code_changes.append(
            CodeChangeCandidate(
                commit_id="200",
                revision="200",
                committed_at=t0 + timedelta(minutes=5),
                paths='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]',
            )
        )
        # Earlier unmentioned entity vs later entity named in the error text.
        r1.data_changes.append(
            DataChangeCandidate(lx_table_code="ACINVORD", change_type="U", changed_at=t0)
        )
        r1.data_changes.append(
            DataChangeCandidate(
                lx_table_code="LXFOO", change_type="U", changed_at=t0 + timedelta(minutes=5)
            )
        )
        apply_run(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
        cand = rec["candidates"]
        # The relevant commit outranks the chronologically-earlier unrelated one, reason visible.
        assert [c["revision"] for c in cand["code"]] == ["200", "100"]
        assert cand["code"][0]["reasons"] and "module" in cand["code"][0]["reasons"][0]
        assert cand["code"][1]["reasons"] == []
        assert [d["entity"] for d in cand["data"]] == ["LXFOO", "ACINVORD"]
        assert "mentioned in the error text" in cand["data"][0]["reasons"][0]


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


def test_job_runs_paginates_newest_first(session_factory):
    with session_scope(session_factory) as s:
        prev = None
        for build in range(1, 8):  # 7 runs, pages of 3
            run = make_run(s, build, {"a": "PASSED"})
            apply_run(s, run, baseline=prev)
            prev = run

        first = views.job_runs(s, limit=3)
        assert (first["total"], first["page"], first["pages"]) == (7, 1, 3)
        assert [r["build"] for r in first["runs"]] == [7, 6, 5]
        # Later pages continue the newest-first order; diff counts still resolve (the page-boundary
        # baseline of build 5 is build 4, which lives on page 2).
        second = views.job_runs(s, limit=3, page=2)
        assert [r["build"] for r in second["runs"]] == [4, 3, 2]
        last = views.job_runs(s, limit=3, page=3)
        assert [r["build"] for r in last["runs"]] == [1]


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


# ── triage filters/sort (issue #63) ─────────────────────────────────────────


def test_triage_filters_by_owner_and_suite(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        get_identity(s, "alpha").owner_initials = "AB"
        get_identity(s, "alpha").suite = "ut_pricing"
        get_identity(s, "beta").owner_initials = "CD"
        get_identity(s, "beta").suite = "ut_billing"

        by_owner = views.triage_queue(s, filters={"owner": "ab"})
        assert {r["test_id"] for r in by_owner["new"]} == {"alpha"}
        assert by_owner["counts"]["new"] == 1

        by_suite = views.triage_queue(s, filters={"suite": "billing"})
        assert {r["test_id"] for r in by_suite["new"]} == {"beta"}


def test_triage_filters_by_triage_status(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        actions.acknowledge(s, get_identity(s, "alpha").id, "dana")
        actions.acknowledge(s, get_identity(s, "beta").id, "dana")
        _lc(s, "alpha").current_episode.triage_status = "INVESTIGATING"

        by_status = views.triage_queue(s, filters={"triage_status": "INVESTIGATING"})
        assert {r["test_id"] for r in by_status["still_failing"]} == {"alpha"}


def test_triage_filters_by_flaky(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        _lc(s, "alpha").flaky = True

        by_flaky = views.triage_queue(s, filters={"flaky": "1"})
        assert {r["test_id"] for r in by_flaky["new"]} == {"alpha"}


def test_triage_sort_by_name_and_owner(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"zeta": "FAILED", "alpha": "FAILED"})
        apply_run(s, r1, baseline=None)
        get_identity(s, "zeta").owner_initials = "AA"
        get_identity(s, "alpha").owner_initials = "ZZ"

        by_name = views.triage_queue(s, sort="name")
        assert [r["test_id"] for r in by_name["new"]] == ["alpha", "zeta"]

        by_owner = views.triage_queue(s, sort="owner")
        assert [r["test_id"] for r in by_owner["new"]] == ["zeta", "alpha"]


def test_triage_filter_options_lists_distinct_owners_and_suites(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "PASSED"})
        apply_run(s, r1, baseline=None)
        get_identity(s, "alpha").owner_initials = "AB"
        get_identity(s, "alpha").suite = "ut_pricing"

        options = views.triage_filter_options(s)
        assert "AB" in options["owners"]
        assert "ut_pricing" in options["suites"]


# ── active-filter chips + header sort links (issue #77) ──────────────────────


def test_triage_filter_chips_one_per_active_filter_with_remove_url():
    chips = views.triage_filter_chips({"owner": "KP", "flaky": "1"}, sort="name")
    assert [c["label"] for c in chips] == ["owner: KP", "flaky only"]
    by_key = {c["key"]: c for c in chips}
    # Each ✕ drops just its own filter and keeps the rest, including the sort.
    assert by_key["owner"]["remove_url"] == "/?flaky=1&sort=name"
    assert by_key["flaky"]["remove_url"] == "/?owner=KP&sort=name"


def test_triage_filter_chips_empty_when_nothing_active():
    assert views.triage_filter_chips({}) == []


def test_triage_filter_chip_removing_last_filter_links_home():
    (chip,) = views.triage_filter_chips({"suite": "ut_pricing"})
    assert chip["label"] == "suite: ut_pricing"
    assert chip["remove_url"] == "/"


def test_triage_sort_links_apply_and_toggle_off():
    links = views.triage_sort_links({"owner": "KP"})
    assert links["name"] == {"active": False, "url": "/?owner=KP&sort=name"}
    assert links["owner"] == {"active": False, "url": "/?owner=KP&sort=owner"}

    active = views.triage_sort_links({"owner": "KP"}, sort="name")
    # The active sort marks itself and its link toggles back to the age default.
    assert active["name"] == {"active": True, "url": "/?owner=KP"}
    assert active["owner"] == {"active": False, "url": "/?owner=KP&sort=owner"}


def test_triage_row_carries_tracks_and_signature_for_bulk_by_signature(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("boom", "Traceback"),
            },
            fail_tracks={"alpha": ("permanent",), "beta": ("permanent",)},
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)

        queue = views.triage_queue(s)
        rows = {r["test_id"]: r for r in queue["new"]}
        assert rows["alpha"]["tracks"] == ["permanent"]
        assert rows["alpha"]["signature_id"] is not None
        # Distinct tests with the same error text get distinct signatures (hash includes identity).
        assert rows["alpha"]["signature_id"] != rows["beta"]["signature_id"]
        # A test failing in both tracks carries both (issue #84) and still anchors one signature —
        # the normalizer strips the track prefix, so both tracks' failures share it.
        assert rows["gamma"]["tracks"] == ["permanent", "permanent_py39"]
        assert rows["gamma"]["signature_id"] is not None


def test_triage_track_filter_matches_any_failing_track(session_factory):
    # Issue #84: "both" fails in both tracks, "single" only in permanent_py39. The exact-track
    # filter used to keep only one arbitrary track per row, hiding "both" from one of the filters.
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"both": "FAILED", "single": "FAILED"},
            fail_tracks={"single": ("permanent_py39",)},
        )
        apply_run(s, r1, baseline=None)

        by_perm = views.triage_queue(s, filters={"track": "permanent"})
        assert {r["test_id"] for r in by_perm["new"]} == {"both"}

        by_py39 = views.triage_queue(s, filters={"track": "permanent_py39"})
        assert {r["test_id"] for r in by_py39["new"]} == {"both", "single"}

        rows = {r["test_id"]: r for r in by_py39["new"]}
        assert rows["both"]["tracks"] == ["permanent", "permanent_py39"]
        assert rows["single"]["tracks"] == ["permanent_py39"]


# ── run-results failures-only filter (issue #63) ────────────────────────────


def test_run_summary_failures_only_filters_results_and_total(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "PASSED"})
        apply_run(s, r1, baseline=None)

        all_rows = views.run_summary(s, 1)
        assert all_rows["results_total"] == 4  # 2 tests x 2 tracks
        assert all_rows["failures_only"] is False

        failing_only = views.run_summary(s, 1, failures_only=True)
        assert failing_only["results_total"] == 2  # alpha x 2 tracks
        assert failing_only["failures_only"] is True
        assert all(r["status"] == "FAILED" for r in failing_only["results"])


# ── global test search (issue #63) ──────────────────────────────────────────


def test_test_search_matches_substring_case_insensitively(session_factory):
    with session_scope(session_factory) as s:
        get_identity(s, "ut_pricing.pr_engine.TestClass.test_margin_calc")
        get_identity(s, "ut_billing.bi_tax.TestClass.test_vat_rate")

        results = views.test_search(s, "MARGIN")
        assert [r["test_id"] for r in results] == [
            "ut_pricing.pr_engine.TestClass.test_margin_calc"
        ]


def test_test_search_empty_query_returns_nothing(session_factory):
    with session_scope(session_factory) as s:
        assert views.test_search(s, "") == []
        assert views.test_search(s, "   ") == []


# ── bulk actions (issue #63) ─────────────────────────────────────────────────


def test_bulk_acknowledge_stamps_all_selected(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"})
        apply_run(s, r1, baseline=None)
        ids = [get_identity(s, n).id for n in ("alpha", "beta")]

        count = actions.bulk_acknowledge(s, ids, "dana")
        assert count == 2
        assert _lc(s, "alpha").acknowledged is True
        assert _lc(s, "alpha").acknowledged_by == "dana"
        assert _lc(s, "beta").acknowledged is True
        assert _lc(s, "gamma").acknowledged is False


def test_bulk_acknowledge_skips_unknown_ids(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED"})
        apply_run(s, r1, baseline=None)
        ident = get_identity(s, "alpha")

        count = actions.bulk_acknowledge(s, [ident.id, 999999], "dana")
        assert count == 1


def test_acknowledge_by_signature_only_acks_unacknowledged_matching_tests(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)

        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)
        assert sig_id is not None

        # gamma is a different signature entirely, so only alpha+beta should be acknowledged.
        count = actions.acknowledge_by_signature(s, sig_id, "erin")
        assert count == 2
        assert _lc(s, "alpha").acknowledged is True
        assert _lc(s, "alpha").acknowledged_by == "erin"
        assert _lc(s, "beta").acknowledged is True
        assert _lc(s, "gamma").acknowledged is False


def test_acknowledge_by_signature_matches_across_tests_despite_distinct_frames(session_factory):
    """Real stack traces embed each test's own function name in the frame line, so two tests
    hitting the same outage still get distinct ``normalized_text`` — the bulk action must match on
    exception type + message with the frame lines stripped (see ``actions._error_key``), not literal
    signature-row identity."""

    def _stack(func: str) -> str:
        return (
            "Traceback (most recent call last):\n"
            f'  File "/opt/ls/lx/release/permanent/tests/dev/ut_notify/nt_dispatch.py", '
            f"line 63, in {func}\n"
            "    result = run_case()\n"
            "ConnectionError: SMTP relay unreachable: connection refused"
        )

    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"test_email_dispatch": "FAILED", "test_sms_dispatch": "FAILED"},
            errors={
                "test_email_dispatch": (None, _stack("test_email_dispatch")),
                "test_sms_dispatch": (None, _stack("test_sms_dispatch")),
            },
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)

        email_sig_id = actions._episode_signature_id(
            s, _lc(s, "test_email_dispatch").current_episode
        )
        sms_sig_id = actions._episode_signature_id(s, _lc(s, "test_sms_dispatch").current_episode)
        assert email_sig_id != sms_sig_id  # distinct signature rows (identity is part of the hash)

        count = actions.acknowledge_by_signature(s, email_sig_id, "erin")
        assert count == 2
        assert _lc(s, "test_email_dispatch").acknowledged is True
        assert _lc(s, "test_sms_dispatch").acknowledged is True


def test_acknowledge_by_signature_skips_already_acknowledged(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)
        actions.acknowledge(s, get_identity(s, "beta").id, "dana")
        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)

        count = actions.acknowledge_by_signature(s, sig_id, "erin")
        assert count == 1  # only alpha; beta was already acknowledged
        assert _lc(s, "beta").acknowledged_by == "dana"  # untouched


def test_bulk_set_attribution_applies_to_all_episodes(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
        ep_ids = [_lc(s, "alpha").current_episode_id, _lc(s, "beta").current_episode_id]

        count = actions.bulk_set_attribution(
            s, ep_ids, "frank", triage_status="INVESTIGATING", reason_text="shared root cause"
        )
        assert count == 2
        alpha_ep = s.get(FailureEpisode, ep_ids[0])
        beta_ep = s.get(FailureEpisode, ep_ids[1])
        assert alpha_ep.triage_status == "INVESTIGATING"
        assert beta_ep.triage_status == "INVESTIGATING"
        assert alpha_ep.attribution.reason_text == "shared root cause"
        assert beta_ep.attribution.reason_text == "shared root cause"
