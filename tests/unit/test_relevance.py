"""Per-test relevance ranking of change candidates (uta.analyze.relevance) — pure, offline.

Covers the three scoring outcomes the acceptance check names — path-match, entity-match and
no-match — plus the ordering contract (matched first, ties chronological) and a golden-fixture
sweep: the real #1702 change (Uniface meta XML) must NOT match a Python devUT failure.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from uta.analyze.relevance import (
    SCORE_ENTITY,
    SCORE_FILE,
    SCORE_MODULE,
    SCORE_PACKAGE,
    rank_candidates,
)
from uta.ingest.svn_update import parse_change_sets
from uta.ingest.ut_report import parse_test_report
from uta.models import CodeChangeCandidate, DataChangeCandidate

_T0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_billing/bi_round.py", line 77, '
    "in test_invoice_rounding\n"
    "    self.assertEqual(a, b)\n"
    "AssertionError: values differ: expected 100 got 101\n"
)


def _code(paths: list[str], *, revision: str = "r1", offset_min: int = 0) -> CodeChangeCandidate:
    return CodeChangeCandidate(
        commit_id=revision,
        revision=revision,
        author="dev",
        message="a change",
        committed_at=_T0 + timedelta(minutes=offset_min),
        paths=json.dumps([{"editType": "edit", "file": f} for f in paths]),
    )


def _data(entity: str, *, component: str | None = None, offset_min: int = 0) -> DataChangeCandidate:
    return DataChangeCandidate(
        lx_table_code=entity,
        pk_lst="42",
        change_type="U",
        component_name=component,
        author="THA",
        changed_at=_T0 + timedelta(minutes=offset_min),
    )


def _rank(code=(), data=(), **ctx):
    defaults = dict(
        file_path="/opt/ls/lx/release/permanent/tests/dev/ut_billing/bi_round.py",
        error_details="values differ: expected 100 got 101",
        error_stack_trace=_STACK,
        class_name="ut_billing.bi_round.TestClass",
    )
    defaults.update(ctx)
    return rank_candidates(code, data, **defaults)


# ── code candidates: path matching ────────────────────────────────────────


def test_module_path_match_scores_highest():
    """Changed file name + parent dir match the test's module despite different roots."""
    ranked = _rank(code=[_code(["/trunk/lx/ut_billing/bi_round.py"])])
    [c] = ranked.code
    assert c.score == SCORE_MODULE
    assert any("bi_round.py" in r and "module" in r for r in c.reasons)
    assert ranked.code_relevant


def test_file_name_only_match_is_weaker():
    ranked = _rank(code=[_code(["/trunk/other_pkg/bi_round.py"])])
    [c] = ranked.code
    assert c.score == SCORE_FILE


def test_package_overlap_is_weakest_match():
    ranked = _rank(code=[_code(["/trunk/lx/ut_billing/bi_tax.py"])])
    [c] = ranked.code
    assert c.score == SCORE_PACKAGE
    assert any("'ut_billing'" in r for r in c.reasons)


def test_generic_file_and_dir_names_do_not_match():
    """__init__.py and generic dirs (trunk/lx/tests/...) must not create fake relevance."""
    ranked = _rank(code=[_code(["/trunk/lx/other/__init__.py", "/trunk/lx/other/mod.py"])])
    [c] = ranked.code
    assert c.score == 0
    assert c.reasons == ()
    assert not ranked.code_relevant


def test_unmatched_code_candidates_stay_chronological_below_matches():
    late_match = _code(["/trunk/lx/ut_billing/bi_round.py"], revision="r3", offset_min=20)
    early_miss = _code(["/trunk/lx/other/mod.py"], revision="r1", offset_min=0)
    mid_miss = _code(["/trunk/lx/other/mod2.py"], revision="r2", offset_min=10)
    ranked = _rank(code=[late_match, early_miss, mid_miss])
    assert [c.revision for c in ranked.code] == ["r3", "r1", "r2"]


def test_class_name_module_matches_without_stack_trace():
    """The class-derived module path alone anchors matching when no frame was extracted."""
    ranked = _rank(
        code=[_code(["/trunk/lx/ut_billing/bi_round.py"])],
        file_path=None,
        error_stack_trace=None,
    )
    assert ranked.code[0].score == SCORE_MODULE


# ── data candidates: entity matching ──────────────────────────────────────


def test_entity_mentioned_in_error_text_matches():
    ranked = _rank(
        data=[_data("LORDER")],
        error_details="lookup failed for LORDER row 10487",
    )
    [d] = ranked.data
    assert d.score == SCORE_ENTITY
    assert any("LORDER" in r and "mentioned" in r for r in d.reasons)
    assert ranked.data_relevant


def test_entity_substring_of_longer_word_does_not_match():
    """LORDERTR contains LORDER but is a different entity — word boundaries required."""
    ranked = _rank(data=[_data("LORDER")], error_details="change tracked on LORDERTR only")
    assert ranked.data[0].score == 0


def test_component_mention_matches_weaker_than_entity():
    ranked = _rank(
        data=[_data("LORDER", component="LORDER_RPT")],
        error_details="report LORDER_RPT crashed",
    )
    [d] = ranked.data
    assert 0 < d.score < SCORE_ENTITY
    assert any("LORDER_RPT" in r for r in d.reasons)


def test_matched_entity_ranks_above_unmatched():
    ranked = _rank(
        data=[_data("ACINVORD", offset_min=0), _data("LORDER", offset_min=5)],
        error_details="values differ for LORDER: expected 2 got 1",
    )
    assert [d.entity for d in ranked.data] == ["LORDER", "ACINVORD"]
    assert ranked.data[0].reasons and not ranked.data[1].reasons


# ── no-match / degenerate context ─────────────────────────────────────────


def test_no_context_yields_zero_scores_chronological():
    """With nothing to match against, ranking degrades to the chronological v1 presentation."""
    ranked = rank_candidates(
        [_code(["/trunk/lx/a.py"], revision="r2", offset_min=10),
         _code(["/trunk/lx/b.py"], revision="r1", offset_min=0)],
        [_data("LORDER")],
    )
    assert all(c.score == 0 for c in ranked.code)
    assert all(d.score == 0 for d in ranked.data)
    assert [c.revision for c in ranked.code] == ["r1", "r2"]
    assert not ranked.code_relevant and not ranked.data_relevant


def test_malformed_paths_json_is_tolerated():
    cand = _code([])
    cand.paths = "not json"
    ranked = _rank(code=[cand])
    assert ranked.code[0].score == 0


def test_is_deterministic():
    args = dict(
        code=[_code(["/trunk/lx/ut_billing/bi_round.py"]), _code(["/trunk/lx/other.py"])],
        data=[_data("LORDER"), _data("ACINVORD")],
    )
    assert _rank(**args) == _rank(**args)


# ── golden fixtures: the real #1702 shapes ────────────────────────────────


def test_1702_meta_xml_change_does_not_match_devut_failure(change_sets_1702, test_report_1702):
    """The build's real change (Uniface meta XML) is irrelevant to a Python devUT failure."""
    change = parse_change_sets(change_sets_1702).changes[0]
    cand = CodeChangeCandidate(
        commit_id=change.commit_id,
        revision=change.commit_id,
        author=change.author,
        message=change.message,
        committed_at=change.when,
        paths=json.dumps([{"editType": p.edit_type, "file": p.file} for p in change.paths]),
    )
    failure = next(c for c in parse_test_report(test_report_1702).failed() if c.error_stack_trace)
    ranked = rank_candidates(
        [cand],
        [],
        file_path=failure.file_path,
        error_details=failure.error_details,
        error_stack_trace=failure.error_stack_trace,
        class_name=failure.class_name,
    )
    [c] = ranked.code
    assert c.score == 0
    assert c.reasons == ()


def test_1702_frame_shaped_path_matches_when_commit_touches_module(test_report_1702):
    """A commit touching the failing test's own module ranks as a module match on real frames."""
    failure = next(c for c in parse_test_report(test_report_1702).failed() if c.file_path)
    # Derive a plausible trunk path for the test's own module from its real frame path.
    module_tail = "/".join(failure.file_path.rsplit("/", 2)[-2:])  # e.g. ut_accounting/ac_csvc.py
    ranked = rank_candidates(
        [_code([f"/trunk/lx/{module_tail}"])],
        [],
        file_path=failure.file_path,
        error_details=failure.error_details,
        error_stack_trace=failure.error_stack_trace,
        class_name=failure.class_name,
    )
    assert ranked.code[0].score == SCORE_MODULE
