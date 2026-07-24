"""Dashboard read-side projections (uta.web.views) and write-side actions (uta.web.actions).

Exercised against hand-built build sequences (via the lifecycle state machine) on in-memory SQLite —
no Jenkins/Oracle/Postgres. Covers the triage buckets, the per-test record, the build diff, and the
acknowledge/confirm/attribute provenance logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.builders import _EPOCH, get_identity, make_build
from uta.analyze.classify import classify_build
from uta.analyze.lifecycle import apply_build
from uta.db import session_scope
from uta.kb.store import record_signatures_for_build
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
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        q = views.triage_queue(s)
        assert q["counts"]["new"] == 1
        assert q["new"][0]["test_id"] == "t"
        assert q["counts"]["still_failing"] == 0


def test_acknowledged_failure_moves_to_still_failing(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        assert actions.acknowledge(s, get_identity(s, "t").id, "alice") is True
        q = views.triage_queue(s)
        assert q["counts"]["new"] == 0
        assert q["counts"]["still_failing"] == 1
        assert q["still_failing"][0]["acknowledged"] is True


def test_removed_open_episode_surfaces_in_still_failing_with_flag(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"other": "PASSED"})  # "t" absent → REMOVED, episode stays open
        apply_build(s, r2, baseline=r1)
        q = views.triage_queue(s)
        removed = [r for r in q["still_failing"] if r["test_id"] == "t"]
        assert removed and removed[0]["removed"] is True


def test_recently_fixed_window_includes_recent_excludes_old(session_factory):
    now = datetime.now(UTC)
    with session_scope(session_factory) as s:
        # Recent fix: fail then pass a day ago.
        r1 = make_build(s, 1, {"recent": "FAILED"}, started_at=now - timedelta(days=2))
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"recent": "PASSED"}, started_at=now - timedelta(days=1))
        apply_build(s, r2, baseline=r1)
        # Old fix: fixed well outside the 7-day window.
        r3 = make_build(s, 3, {"old": "FAILED"}, started_at=now - timedelta(days=40))
        apply_build(s, r3, baseline=None)
        r4 = make_build(s, 4, {"old": "PASSED"}, started_at=now - timedelta(days=39))
        apply_build(s, r4, baseline=r3)

        q = views.triage_queue(s, recently_fixed_days=7)
        names = {r["test_id"] for r in q["recently_fixed"]}
        assert "recent" in names
        assert "old" not in names


# ── triage error snippets (issue #145) ────────────────────────────────────────

_SNIPPET_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_x/mod.py", line 12, in test_t\n'
    "    check()\n"
    "AssertionError: values differ: expected 1 got 2"
)


def test_triage_rows_carry_error_snippet_from_exception_line(session_factory):
    """The snippet is the trace's closing exception line — errorDetails is often 'test failure'."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"t": "FAILED"},
            error_type={"t": "ASSERTION"},
            errors={"t": ("test failure", _SNIPPET_STACK)},
        )
        apply_build(s, r1, baseline=None)
        row = views.triage_queue(s)["new"][0]
        assert row["error_type"] == "ASSERTION"
        assert row["error_snippet"] == "AssertionError: values differ: expected 1 got 2"


def test_triage_snippet_survives_into_still_failing_bucket(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": (None, _SNIPPET_STACK)})
        apply_build(s, r1, baseline=None)
        actions.acknowledge(s, get_identity(s, "t").id, "alice")
        row = views.triage_queue(s)["still_failing"][0]
        assert row["error_snippet"] == "AssertionError: values differ: expected 1 got 2"


def test_triage_snippet_falls_back_to_first_details_line(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("boom happened\nsecond line", None)})
        apply_build(s, r1, baseline=None)
        assert views.triage_queue(s)["new"][0]["error_snippet"] == "boom happened"


def test_triage_snippet_truncated_to_one_sane_line(session_factory):
    long_msg = "x" * 400
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": (long_msg, None)})
        apply_build(s, r1, baseline=None)
        snippet = views.triage_queue(s)["new"][0]["error_snippet"]
        assert snippet.endswith("…")
        assert len(snippet) <= 160
        assert "\n" not in snippet


def test_triage_snippet_none_without_error_text(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        row = views.triage_queue(s)["new"][0]
        assert row["error_snippet"] is None
        assert row["error_type"] is None


# ── long-list capping (issue #19) ─────────────────────────────────────────────


def test_triage_new_bucket_capped_with_full_count(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        q = views.triage_queue(s, limit=2)
        # Rows are capped to the limit, but the count reports the true total.
        assert len(q["new"]) == 2
        assert q["counts"]["new"] == 5
        assert q["truncated"]["new"] is True


def test_triage_expand_renders_bucket_in_full(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        q = views.triage_queue(s, limit=2, expand=["new"])
        assert len(q["new"]) == 5
        assert q["truncated"]["new"] is False


def test_triage_limit_zero_disables_cap(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "FAILED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        q = views.triage_queue(s, limit=0)
        assert len(q["new"]) == 5
        assert q["truncated"]["new"] is False


def test_run_results_paginate_with_full_total(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        # 5 tests × 2 tracks = 10 result rows → 4 pages of 3.
        summary = views.build_summary(s, 1, limit=3)
        assert len(summary["results"]) == 3
        assert summary["results_total"] == 10
        assert (summary["page"], summary["pages"]) == (1, 4)
        # The last page carries the remainder; pages don't overlap.
        last = views.build_summary(s, 1, limit=3, page=4)
        assert len(last["results"]) == 1
        assert last["page"] == 4
        seen = [
            (r["test_id"], r["track"])
            for p in range(1, 5)
            for r in views.build_summary(s, 1, limit=3, page=p)["results"]
        ]
        assert len(seen) == 10
        assert len(set(seen)) == 10  # stable ordering — no row repeats across pages


def test_run_results_page_out_of_range_clamps(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        assert views.build_summary(s, 1, limit=3, page=99)["page"] == 4
        assert views.build_summary(s, 1, limit=3, page=0)["page"] == 1


def test_run_results_limit_zero_disables_pagination(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {f"t{i:03d}": "PASSED" for i in range(5)})
        apply_build(s, r1, baseline=None)
        summary = views.build_summary(s, 1, limit=0)
        assert len(summary["results"]) == 10
        assert (summary["page"], summary["pages"]) == (1, 1)


# ── per-test record ─────────────────────────────────────────────────────────


def test_test_record_exposes_lifecycle_and_episode(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"t": "FAILED"},
            error_type={"t": "assertion"},
            errors={"t": ("boom went the assertion", "Traceback ...\n  line 3")},
        )
        apply_build(s, r1, baseline=None)
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
        assert failure["build"]["number"] == 1


def test_test_record_scopes_failure_detail_per_episode(session_factory):
    """Each episode carries the error detail of *its own* last-failing build, not the newest one."""
    with session_scope(session_factory) as s:
        # Episode 1: fail in #1, fixed in #2.
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("first-episode error", None)})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"t": "PASSED"})
        apply_build(s, r2, baseline=r1)
        # Episode 2 (reopen): fail again in #3 with a different error.
        r3 = make_build(s, 3, {"t": "REGRESSION"}, errors={"t": ("second-episode error", None)})
        apply_build(s, r3, baseline=r2)

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
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("boom", None)})
        apply_build(s, r1, baseline=None)
        ident = get_identity(s, "t")
        ident.zephyr_test_cases = "LX-T4792,LX-T5001"
        s.flush()
        rec = views.test_record(s, ident.id)
        assert rec["zephyr_test_cases"] == ["LX-T4792", "LX-T5001"]


def test_test_record_zephyr_test_cases_empty_when_unset(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("boom", None)})
        apply_build(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
        assert rec["zephyr_test_cases"] == []


def test_evidence_items_flatten_the_classifier_shape():
    """Issue #159: the persisted evidence JSON becomes whitelisted, readable label/value rows."""
    items = dict(
        views._evidence_items(
            {
                "code_candidates": 1,
                "data_candidates": 0,
                "infra_error": True,
                "baseline_build_id": 7,
                "relevance": {
                    "code_matched": 1,
                    "data_matched": 0,
                    "tie_break": None,
                    "top_code": {
                        "candidate": "r48606",
                        "author": "S. Okafor",
                        "score": 3.0,
                        "reasons": ["touches ut_x/mod.py"],
                    },
                    "top_data": None,
                },
                "confidence": {"win_score": 3.0, "lose_score": 0.0, "kb_provenance_weight": 4},
            }
        )
    )
    assert items["Infrastructure error"] == "yes"
    assert items["Code changes in window"] == "1 candidate · 1 matched this test"
    assert items["Data changes in window"] == "none"
    assert items["Top code match"] == "r48606 by S. Okafor (score 3) — touches ut_x/mod.py"
    assert "Tie-break" not in items  # null tie-break renders no row
    assert items["Confidence inputs"] == "relevance score 3 vs 0 · KB provenance weight 4"
    assert "baseline_build_id" not in str(items)  # internal PK stays whitelisted out


def test_evidence_items_handle_degenerate_payloads():
    """A bare string / list / empty payload never crashes and never renders an empty shell."""
    assert views._evidence_items(None) == []
    assert views._evidence_items({}) == []
    assert views._evidence_items("") == []
    assert views._evidence_items([]) == []
    assert views._evidence_items("legacy free-text note") == [("Evidence", "legacy free-text note")]
    assert views._evidence_items(["a", "b"]) == [("Evidence", "a; b")]
    # A dict with only unknown keys yields no rows (whitelist), so the template renders no block.
    assert views._evidence_items({"internal_only": 1}) == []


def test_test_record_missing_identity_is_none(session_factory):
    with session_scope(session_factory) as s:
        assert views.test_record(s, 9999) is None


def test_test_record_exposes_sparkline_history(session_factory):
    """Anchored to *now* (not a fixed epoch) so the build stays inside the default flaky window."""
    base = datetime.now(UTC) - timedelta(days=2)
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"}, started_at=base)
        apply_build(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
    # A failed bar spans the full height (y=0) — the non-hue channel of issue #144.
    assert rec["spark"].bars == [
        {"x": 0.0, "y": 0.0, "width": 120.0, "height": 22.0, "failed": True, "number": 1}
    ]


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
        r1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("lookup failed for LXFOO row", stack)})
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
        apply_build(s, r1, baseline=None)
        rec = views.test_record(s, get_identity(s, "t").id)
        cand = rec["candidates"]
        # The relevant commit outranks the chronologically-earlier unrelated one, reason visible.
        assert [c["revision"] for c in cand["code"]] == ["200", "100"]
        assert cand["code"][0]["reasons"] and "module" in cand["code"][0]["reasons"][0]
        assert cand["code"][1]["reasons"] == []
        assert [d["entity"] for d in cand["data"]] == ["LXFOO", "ACINVORD"]
        assert "mentioned in the error text" in cand["data"][0]["reasons"][0]


# ── build summary ──────────────────────────────────────────────────────────────


def test_build_summary_diff_against_baseline(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_build(s, r2, baseline=r1)
        summary = views.build_summary(s, 2)
        assert summary["number"] == 2
        assert summary["baseline"]["number"] == 1
        regressed = {r["test_id"] for r in summary["diff"]["regressions"]["rows"]}
        fixed = {r["test_id"] for r in summary["diff"]["newly_fixed"]["rows"]}
        assert "b" in regressed and "a" in fixed
        assert summary["diff"]["regressions"]["total"] == 1
        assert summary["diff"]["newly_fixed"]["total"] == 1
        assert "totals" in summary and "tracks" in summary


def test_build_summary_caps_diff_buckets_unless_expanded(session_factory):
    # 25 pass→fail transitions: the regressions bucket reports the full total but renders only
    # DIFF_ROW_LIMIT rows (issue #151) until the bucket's key is in ?expand=.
    names = [f"t{i:02d}" for i in range(25)]
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {n: "PASSED" for n in names})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {n: "FAILED" for n in names})
        apply_build(s, r2, baseline=r1)

        bucket = views.build_summary(s, 2)["diff"]["regressions"]
        assert bucket["total"] == 25
        assert len(bucket["rows"]) == views.DIFF_ROW_LIMIT

        expanded = views.build_summary(s, 2, expand=["regressions"])["diff"]["regressions"]
        assert len(expanded["rows"]) == 25


def test_build_expand_urls_preserve_query_and_anchor():
    # The "Show all N" link keeps the rest of the query string (failures_only, results page) and
    # only adds its bucket to ?expand=, jumping back to the diff anchor.
    urls = views.build_expand_urls(1702, {"failures_only": "1", "page": "2"})
    assert urls["regressions"] == "/builds/1702?failures_only=1&page=2&expand=regressions#diff"
    assert urls["removed"] == "/builds/1702?failures_only=1&page=2&expand=removed#diff"


def test_build_expand_urls_merge_with_already_expanded_buckets():
    # The current ?expand= value in the params is superseded, not duplicated; already-expanded
    # buckets stay expanded and the target bucket is appended exactly once.
    urls = views.build_expand_urls(5, {"expand": "regressions"}, expand=["regressions"])
    assert urls["removed"] == "/builds/5?expand=regressions,removed#diff"
    assert urls["regressions"] == "/builds/5?expand=regressions#diff"


def test_build_summary_unknown_build_is_none(session_factory):
    with session_scope(session_factory) as s:
        assert views.build_summary(s, 12345) is None


# ── job builds (issue #37) ──────────────────────────────────────────────────────


def test_job_builds_lists_newest_first_with_diff_counts(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_build(s, r2, baseline=r1)

        result = views.job_builds(s)
        assert [row["number"] for row in result["builds"]] == [2, 1]  # newest first
        newest = result["builds"][0]
        assert newest["status"] == "SUCCESS"
        assert newest["regressions"] == 1  # b newly failing
        assert newest["newly_fixed"] == 1  # a fixed
        assert newest["duration_seconds"] == 1800.0  # make_build builds are 30 min
        # First build has no baseline: every failure is a regression, nothing newly fixed.
        oldest = result["builds"][1]
        assert oldest["regressions"] == 1  # a
        assert oldest["newly_fixed"] == 0


def test_job_builds_totals_and_poller_next(session_factory):
    now = datetime.now(UTC)
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"a": "PASSED"})
        r1.total_passed, r1.total_failed, r1.total_skipped = 10, 2, 1
        apply_build(s, r1, baseline=None)
        s.add(PollerHeartbeat(id=1, last_poll_at=now, last_processed_count=1))
        s.flush()

        result = views.job_builds(s, poll_interval_seconds=300)
        totals = result["builds"][0]["totals"]
        assert totals == {"passed": 10, "failed": 2, "skipped": 1, "total": 13}
        poller = result["poller"]
        # SQLite drops tzinfo on round-trip; compare tz-normalized (as the view does downstream).
        last = views._aware(poller["last_poll_at"])
        assert last == now
        assert poller["next_poll_at"] == last + timedelta(seconds=300)


def test_latest_build_returns_newest_build_by_started_at(session_factory):
    with session_scope(session_factory) as s:
        make_build(s, 1, {"a": "PASSED"})
        r2 = make_build(s, 2, {"a": "PASSED"})  # later build => later started_at
        s.flush()

        latest = views.latest_build(s)
        assert latest["number"] == 2
        assert latest["url"] == r2.url
        assert views._aware(latest["started_at"]) == r2.started_at


def test_latest_build_empty_store_is_none(session_factory):
    with session_scope(session_factory) as s:
        assert views.latest_build(s) is None


def test_job_builds_empty_store_and_no_heartbeat(session_factory):
    with session_scope(session_factory) as s:
        result = views.job_builds(s, poll_interval_seconds=300)
        assert result["builds"] == []
        assert result["poller"]["last_poll_at"] is None
        assert result["poller"]["next_poll_at"] is None
        assert result["timeline"] is None


def test_job_builds_timeline_is_oldest_first(session_factory):
    """The timeline chart reads left-to-right in time, unlike the (newest-first) table rows."""
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"a": "FAILED", "b": "PASSED"})
        apply_build(s, r1, baseline=None)
        r2 = make_build(s, 2, {"a": "PASSED", "b": "FAILED"})
        apply_build(s, r2, baseline=r1)

        result = views.job_builds(s)
        tl = result["timeline"]
        assert tl.first_build == 1
        assert tl.last_build == 2
        assert tl.builds == 2


def test_job_builds_paginates_newest_first(session_factory):
    with session_scope(session_factory) as s:
        prev = None
        for build in range(1, 8):  # 7 builds, pages of 3
            build = make_build(s, build, {"a": "PASSED"})
            apply_build(s, build, baseline=prev)
            prev = build

        first = views.job_builds(s, limit=3)
        assert (first["total"], first["page"], first["pages"]) == (7, 1, 3)
        assert [r["number"] for r in first["builds"]] == [7, 6, 5]
        # Later pages continue the newest-first order; diff counts still resolve (the page-boundary
        # baseline of build 5 is build 4, which lives on page 2).
        second = views.job_builds(s, limit=3, page=2)
        assert [r["number"] for r in second["builds"]] == [4, 3, 2]
        last = views.job_builds(s, limit=3, page=3)
        assert [r["number"] for r in last["builds"]] == [1]


# ── actions: provenance ─────────────────────────────────────────────────────────


def _episode_id(session, name) -> int:
    lc = _lc(session, name)
    return lc.current_episode_id


def test_set_attribution_human_entered_when_no_ai(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
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
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
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
        build = make_build(s, 1, {"t": "FAILED"})
        build.code_changes.append(
            CodeChangeCandidate(commit_id="r777", author="dev-dave", committed_at=_EPOCH)
        )
        analysis = apply_build(s, build, baseline=None)
        s.flush()
        classify_build(s, build, analysis.opened_episodes)
        s.flush()
        ep_id = _episode_id(s, "t")
        attr = actions.confirm(s, ep_id, "alice")
        assert attr.causing_person == "dev-dave"
        assert attr.cause_provenance == Provenance.AI_CONFIRMED
        assert attr.original_ai_cause == "dev-dave"


def test_set_attribution_correction_retains_original_ai(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
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
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
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
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
        get_identity(s, "alpha").main_developer = "AB"
        get_identity(s, "alpha").suite = "ut_pricing"
        get_identity(s, "beta").main_developer = "CD"
        get_identity(s, "beta").suite = "ut_billing"

        by_owner = views.triage_queue(s, filters={"owner": "ab"})
        assert {r["test_id"] for r in by_owner["new"]} == {"alpha"}
        assert by_owner["counts"]["new"] == 1

        by_suite = views.triage_queue(s, filters={"suite": "billing"})
        assert {r["test_id"] for r in by_suite["new"]} == {"beta"}


def test_triage_filters_by_triage_status(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
        actions.acknowledge(s, get_identity(s, "alpha").id, "dana")
        actions.acknowledge(s, get_identity(s, "beta").id, "dana")
        _lc(s, "alpha").current_episode.triage_status = "INVESTIGATING"

        by_status = views.triage_queue(s, filters={"triage_status": "INVESTIGATING"})
        assert {r["test_id"] for r in by_status["still_failing"]} == {"alpha"}


def test_triage_filters_by_flaky(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
        _lc(s, "alpha").flaky = True

        by_flaky = views.triage_queue(s, filters={"flaky": "1"})
        assert {r["test_id"] for r in by_flaky["new"]} == {"alpha"}


def test_triage_sort_by_name_and_owner(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"zeta": "FAILED", "alpha": "FAILED"})
        apply_build(s, r1, baseline=None)
        get_identity(s, "zeta").main_developer = "AA"
        get_identity(s, "alpha").main_developer = "ZZ"

        by_name = views.triage_queue(s, sort="name")
        assert [r["test_id"] for r in by_name["new"]] == ["alpha", "zeta"]

        by_owner = views.triage_queue(s, sort="owner")
        assert [r["test_id"] for r in by_owner["new"]] == ["zeta", "alpha"]


def test_triage_filter_options_lists_distinct_owners_and_suites(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "PASSED"})
        apply_build(s, r1, baseline=None)
        get_identity(s, "alpha").main_developer = "AB"
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


def test_triage_filter_chips_preserve_expand():
    # Removing a chip must not collapse an expanded section (issue #151): the remove URL keeps
    # the current ?expand= set alongside the surviving filters and sort.
    (chip,) = views.triage_filter_chips({"owner": "KP"}, sort="name", expand=["new"])
    assert chip["remove_url"] == "/?sort=name&expand=new"


def test_triage_sort_links_preserve_expand():
    # Re-sorting (or toggling the active sort off) keeps the expanded sections in the URL.
    links = views.triage_sort_links({"owner": "KP"}, expand=["new", "still_failing"])
    assert links["name"]["url"] == "/?owner=KP&sort=name&expand=new,still_failing"

    active = views.triage_sort_links({}, sort="name", expand=["new"])
    assert active["name"] == {"active": True, "url": "/?expand=new"}


def test_triage_expand_urls_preserve_filters_and_sort():
    # The "Load all" link keeps the whole URL state (filters + sort) and only adds its section
    # to ?expand=, jumping back to the section anchor.
    urls = views.triage_expand_urls({"owner": "KP"}, sort="name")
    assert urls["new"] == "/?owner=KP&sort=name&expand=new#new"
    assert urls["still_failing"] == "/?owner=KP&sort=name&expand=still_failing#still_failing"
    assert urls["recently_fixed"] == "/?owner=KP&sort=name&expand=recently_fixed#recently_fixed"


def test_triage_expand_urls_merge_with_already_expanded_sections():
    urls = views.triage_expand_urls({}, expand=["new"])
    # Already-expanded sections stay expanded; the target section is appended exactly once.
    assert urls["still_failing"] == "/?expand=new,still_failing#still_failing"
    assert urls["new"] == "/?expand=new#new"


# ── pivot links (issue #157) ──────────────────────────────────────────────────


def test_pivot_url_builds_single_filter_queue_urls():
    assert views.pivot_url("owner", "KP") == "/?owner=KP"
    assert views.pivot_url("cause", "CODE_CHANGE") == "/?cause=CODE_CHANGE"
    # Values are URL-encoded; the pivot carries exactly one filter, never inherited state.
    assert views.pivot_url("suite", "ut a&b") == "/?suite=ut+a%26b"


def test_pivot_url_empty_value_yields_none():
    assert views.pivot_url("owner", None) is None
    assert views.pivot_url("suite", "") is None


def test_triage_rows_carry_pivot_urls(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"t": "FAILED"})
        apply_build(s, r1, baseline=None)
        get_identity(s, "t").main_developer = "KP"
        s.add(
            Classification(
                episode_id=_lc(s, "t").current_episode_id,
                predicted_cause=PredictedCause.DATA_CHANGE,
            )
        )
        s.flush()
        row = views.triage_queue(s)["new"][0]
        assert row["owner_url"] == "/?owner=KP"
        assert row["cause_url"] == "/?cause=DATA_CHANGE"


def test_triage_row_pivot_urls_none_without_owner_or_classification(session_factory):
    with session_scope(session_factory) as s:
        apply_build(s, make_build(s, 1, {"t": "FAILED"}), baseline=None)
        row = views.triage_queue(s)["new"][0]
        assert row["owner_url"] is None
        assert row["cause_url"] is None


def test_search_rows_carry_suite_and_owner_pivot_urls(session_factory):
    with session_scope(session_factory) as s:
        ident = get_identity(s, "ut_a.TestClass.test_thing")
        ident.suite = "ut_a"
        ident.main_developer = "KP"
        (row,) = views.test_search(s, "thing")
        assert row["suite_url"] == "/?suite=ut_a"
        assert row["owner_url"] == "/?owner=KP"


def test_triage_row_carries_tracks_and_signature_for_bulk_by_signature(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(
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
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)

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
        r1 = make_build(
            s,
            1,
            {"both": "FAILED", "single": "FAILED"},
            fail_tracks={"single": ("permanent_py39",)},
        )
        apply_build(s, r1, baseline=None)

        by_perm = views.triage_queue(s, filters={"track": "permanent"})
        assert {r["test_id"] for r in by_perm["new"]} == {"both"}

        by_py39 = views.triage_queue(s, filters={"track": "permanent_py39"})
        assert {r["test_id"] for r in by_py39["new"]} == {"both", "single"}

        rows = {r["test_id"]: r for r in by_py39["new"]}
        assert rows["both"]["tracks"] == ["permanent", "permanent_py39"]
        assert rows["single"]["tracks"] == ["permanent_py39"]


# ── build-results failures-only filter (issue #63) ────────────────────────────


def test_build_summary_failures_only_filters_results_and_total(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "PASSED"})
        apply_build(s, r1, baseline=None)

        all_rows = views.build_summary(s, 1)
        assert all_rows["results_total"] == 4  # 2 tests x 2 tracks
        assert all_rows["failures_only"] is False

        failing_only = views.build_summary(s, 1, failures_only=True)
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


def test_test_search_positive_limit_caps_results(session_factory):
    with session_scope(session_factory) as s:
        for n in range(3):
            get_identity(s, f"ut_pricing.pr_engine.TestClass.test_margin_{n}")

        results = views.test_search(s, "margin", limit=2)
        assert len(results) == 2


def test_test_search_limit_zero_disables_the_cap(session_factory):
    """``ui_row_limit = 0`` means "no cap" everywhere — the search must not emit ``LIMIT 0``."""
    with session_scope(session_factory) as s:
        for n in range(3):
            get_identity(s, f"ut_pricing.pr_engine.TestClass.test_margin_{n}")

        results = views.test_search(s, "margin", limit=0)
        assert len(results) == 3


# ── bulk actions (issue #63) ─────────────────────────────────────────────────


def test_bulk_acknowledge_stamps_all_selected(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"})
        apply_build(s, r1, baseline=None)
        ids = [get_identity(s, n).id for n in ("alpha", "beta")]

        count = actions.bulk_acknowledge(s, ids, "dana")
        assert count == 2
        assert _lc(s, "alpha").acknowledged is True
        assert _lc(s, "alpha").acknowledged_by == "dana"
        assert _lc(s, "beta").acknowledged is True
        assert _lc(s, "gamma").acknowledged is False


def test_bulk_acknowledge_skips_unknown_ids(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED"})
        apply_build(s, r1, baseline=None)
        ident = get_identity(s, "alpha")

        count = actions.bulk_acknowledge(s, [ident.id, 999999], "dana")
        assert count == 1


def test_acknowledge_by_signature_only_acks_unacknowledged_matching_tests(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)

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
        r1 = make_build(
            s,
            1,
            {"test_email_dispatch": "FAILED", "test_sms_dispatch": "FAILED"},
            errors={
                "test_email_dispatch": (None, _stack("test_email_dispatch")),
                "test_sms_dispatch": (None, _stack("test_sms_dispatch")),
            },
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)

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
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        actions.acknowledge(s, get_identity(s, "beta").id, "dana")
        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)

        count = actions.acknowledge_by_signature(s, sig_id, "erin")
        assert count == 1  # only alpha; beta was already acknowledged
        assert _lc(s, "beta").acknowledged_by == "dana"  # untouched


# ── signature ack blast radius on New rows (issue #152) ─────────────────────


def test_triage_new_rows_carry_signature_ack_blast_radius(session_factory):
    """Two tests sharing an error key count 2 on each row; a distinct error counts 1 — the "(N)"
    the "Ack all w/ signature" button shows before the click (and its render-at-all threshold)."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)

        rows = {r["test_id"]: r for r in views.triage_queue(s)["new"]}
        assert rows["alpha"]["signature_ack_count"] == 2
        assert rows["beta"]["signature_ack_count"] == 2
        assert rows["gamma"]["signature_ack_count"] == 1


def test_signature_ack_count_zero_without_signature(session_factory):
    """A New row with no recorded signature shows no bulk-ack control — count 0, id None."""
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED"})
        apply_build(s, r1, baseline=None)
        row = views.triage_queue(s)["new"][0]
        assert row["signature_id"] is None
        assert row["signature_ack_count"] == 0


def test_signature_ack_count_equals_action_blast_radius(session_factory):
    """The "(N)" shown before the click equals what :func:`acknowledge_by_signature` then
    acknowledges — same ``_error_key`` grouping over the same unacknowledged-failing scope, even
    though each test's frame lines (and therefore signature rows) are distinct."""

    def _stack(func: str) -> str:
        return (
            "Traceback (most recent call last):\n"
            f'  File "/opt/ls/lx/release/permanent/tests/dev/ut_notify/nt_dispatch.py", '
            f"line 63, in {func}\n"
            "    result = run_case()\n"
            "ConnectionError: SMTP relay unreachable: connection refused"
        )

    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"email": "FAILED", "sms": "FAILED", "push": "FAILED"},
            errors={n: (None, _stack(f"test_{n}_dispatch")) for n in ("email", "sms", "push")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        # An already-acknowledged sharer sits in Still failing — outside both the New bucket and
        # the bulk action's unacknowledged-only scope, so it must not inflate the count.
        actions.acknowledge(s, get_identity(s, "push").id, "dana")

        rows = {r["test_id"]: r for r in views.triage_queue(s)["new"]}
        shown = rows["email"]["signature_ack_count"]
        assert shown == rows["sms"]["signature_ack_count"] == 2

        acked = actions.acknowledge_by_signature(s, rows["email"]["signature_id"], "erin")
        assert acked == shown


def test_signature_ack_count_ignores_view_filters(session_factory):
    """A filtered view still reports the full blast radius — the bulk action acknowledges every
    matching test regardless of the filters that produced the page."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"both": "FAILED", "py39only": "FAILED"},
            errors={"both": ("boom", "Traceback"), "py39only": ("boom", "Traceback")},
            fail_tracks={"py39only": ("permanent_py39",)},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)

        q = views.triage_queue(s, filters={"track": "permanent"})
        assert {r["test_id"] for r in q["new"]} == {"both"}  # the sibling is filtered out …
        assert q["new"][0]["signature_ack_count"] == 2  # … but one click still acks both


def test_bulk_set_attribution_applies_to_all_episodes(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
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


def test_bulk_set_attribution_all_blank_writes_nothing_and_returns_zero(session_factory):
    """An all-blank bulk submit must count 0 — set_attribution would touch none of the episodes
    (issue #150: the flash count must not claim updates that never happened)."""
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
        ep_ids = [_lc(s, "alpha").current_episode_id, _lc(s, "beta").current_episode_id]

        count = actions.bulk_set_attribution(
            s, ep_ids, "frank", causing_person="  ", reason_text="", triage_status=None
        )
        assert count == 0
        for ep_id in ep_ids:
            ep = s.get(FailureEpisode, ep_id)
            assert ep.triage_status == "UNTRIAGED"
            assert ep.attribution is None


def test_bulk_set_attribution_counts_only_existing_episodes(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"alpha": "FAILED"})
        apply_build(s, r1, baseline=None)
        ep_id = _lc(s, "alpha").current_episode_id

        count = actions.bulk_set_attribution(s, [ep_id, 424242], "frank", causing_person="carol")
        assert count == 1
        assert s.get(FailureEpisode, ep_id).attribution.causing_person == "carol"


def test_has_attribution_input_ignores_whitespace_only_fields():
    assert actions.has_attribution_input("", "  ", None) is False
    assert actions.has_attribution_input("carol", "", None) is True
    assert actions.has_attribution_input("", "bad fixture", None) is True
    assert actions.has_attribution_input(None, None, "INVESTIGATING") is True


# ── signature-wide attribution (issue #106) ──────────────────────────────────


def test_attribute_by_signature_applies_to_all_matching_open_episodes(session_factory):
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED", "gamma": "FAILED"},
            errors={
                "alpha": ("boom", "Traceback"),
                "beta": ("boom", "Traceback"),
                "gamma": ("different", "Traceback"),
            },
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)

        count = actions.attribute_by_signature(
            s,
            sig_id,
            "erin",
            causing_person="frank",
            reason_text="SMTP relay outage",
            triage_status="ROOT_CAUSED",
            jira_ticket="LX-42",
        )
        assert count == 2
        for name in ("alpha", "beta"):
            ep = _lc(s, name).current_episode
            assert ep.triage_status == "ROOT_CAUSED"
            assert ep.jira_ticket == "LX-42"
            assert ep.attribution.causing_person == "frank"
            assert ep.attribution.reason_text == "SMTP relay outage"
            assert ep.attribution.validated_by == "erin"
            # The conclusion attaches to *that* episode's own signature for KB recurrence.
            assert ep.attribution.signature_id == actions._episode_signature_id(s, ep)
        # gamma's failure does not share the signature — entirely untouched.
        gamma_ep = _lc(s, "gamma").current_episode
        assert gamma_ep.triage_status == "UNTRIAGED"
        assert gamma_ep.jira_ticket is None
        assert gamma_ep.attribution is None


def test_attribute_by_signature_mixed_provenance(session_factory):
    """A signature-wide apply over a mixed set derives provenance per episode: the one with a
    prior AI suggestion reads as a correction (original AI values retained), the one without as
    ground-truth entry."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        # Only beta carries an AI suggestion.
        s.add(
            Classification(
                episode_id=_lc(s, "beta").current_episode_id,
                predicted_cause=PredictedCause.CODE_CHANGE,
                suggested_contact="dev-dave",
                llm_hypothesis="trunk commit r123",
            )
        )
        s.flush()
        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)

        count = actions.attribute_by_signature(
            s, sig_id, "alice", causing_person="real-rita", reason_text="ut_ref table X changed"
        )
        assert count == 2
        alpha_attr = _lc(s, "alpha").current_episode.attribution
        assert alpha_attr.cause_provenance == Provenance.HUMAN_ENTERED
        assert alpha_attr.reason_provenance == Provenance.HUMAN_ENTERED
        assert alpha_attr.original_ai_cause is None
        beta_attr = _lc(s, "beta").current_episode.attribution
        assert beta_attr.cause_provenance == Provenance.HUMAN_CORRECTED
        assert beta_attr.original_ai_cause == "dev-dave"
        assert beta_attr.reason_provenance == Provenance.HUMAN_CORRECTED
        assert beta_attr.original_ai_reason == "trunk commit r123"


def test_attribute_by_signature_empty_jira_leaves_tickets_untouched(session_factory):
    """Unlike the single-episode form, an empty Jira field never mass-clears existing tickets."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        beta_ep_id = _lc(s, "beta").current_episode_id
        actions.set_attribution(s, beta_ep_id, "bob", jira_ticket="LX-7")
        sig_id = actions._episode_signature_id(s, _lc(s, "alpha").current_episode)

        actions.attribute_by_signature(s, sig_id, "erin", causing_person="frank", jira_ticket="")
        assert s.get(FailureEpisode, beta_ep_id).jira_ticket == "LX-7"


def test_attribute_by_signature_unknown_signature_is_a_noop(session_factory):
    with session_scope(session_factory) as s:
        assert actions.attribute_by_signature(s, 424242, "erin", causing_person="frank") == 0
