"""LLM prompt assembly (Milestone 5 + issue #50) — pure, no I/O, no network."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

from uta.analyze.relevance import RankedCodeChange, RankedDataChange
from uta.kb.retrieval import SimilarCase
from uta.llm.prompt import build_prompt

_T0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)


def _case(**kw) -> SimilarCase:
    base = dict(
        signature_id=1,
        identity_id=1,
        test_id="pkg.mod.TestA.test_x",
        exception_type="AssertionError",
        occurrence_count=3,
        similarity=0.82,
        reason_text=None,
        causing_person=None,
        provenance=None,
        provenance_weight=0,
    )
    base.update(kw)
    return SimilarCase(**base)


def _code(**kw) -> RankedCodeChange:
    base = dict(
        revision="48612",
        author="R. Devlin",
        message="LX-612: adjust rounding",
        committed_at=_T0,
        score=3.0,
        reasons=("changed trunk/lx/ut_billing/bi_round.py matches the failing test's module",),
    )
    base.update(kw)
    return RankedCodeChange(**base)


def _data(**kw) -> RankedDataChange:
    base = dict(
        entity="LORDER",
        pk="10487",
        change_type="U",
        component="LORDER_RPT",
        author="THA",
        changed_at=_T0,
        score=3.0,
        reasons=("entity LORDER mentioned in the error text",),
    )
    base.update(kw)
    return RankedDataChange(**base)


def test_includes_failure_cause_and_signal_counts():
    system, user = build_prompt(
        test_id="pkg.mod.TestB.test_y",
        predicted_cause="CODE_CHANGE",
        error_details="AssertionError: expected 3 got 4",
        error_stack_trace="Traceback ... line 12",
        code_candidates=[_code(), _code(revision="48613", reasons=())],
        data_candidates=[],
        similar_cases=[],
    )
    assert "one concise sentence" in system.lower() or "one sentence" in system.lower()
    assert "pkg.mod.TestB.test_y" in user
    assert "CODE_CHANGE" in user
    assert "2 code change(s)" in user
    assert "0 reference-data change(s)" in user
    assert "(no similar past cases on record)" in user


def test_candidate_details_reach_the_prompt():
    """Authors, paths and entities of the ranked candidates appear — not just counts (issue #50)."""
    _, user = build_prompt(
        test_id="t",
        predicted_cause="UNKNOWN",
        error_details="boom",
        error_stack_trace=None,
        code_candidates=[_code()],
        data_candidates=[_data()],
        similar_cases=[],
    )
    assert "48612" in user and "R. Devlin" in user
    assert "LX-612: adjust rounding" in user
    assert "trunk/lx/ut_billing/bi_round.py" in user  # the match reason names the changed path
    assert "LORDER" in user and "THA" in user
    assert "entity LORDER mentioned in the error text" in user


def test_unmatched_candidates_are_flagged_and_overflow_is_counted():
    code = [_code(revision=str(i), reasons=(), score=0.0) for i in range(5)]
    _, user = build_prompt(
        test_id="t",
        predicted_cause=None,
        error_details=None,
        error_stack_trace=None,
        code_candidates=code,
        data_candidates=[],
        similar_cases=[],
    )
    assert "[no direct match to this test]" in user
    assert "(+2 less relevant, omitted)" in user  # only the top 3 are rendered in detail
    assert "5 code change(s)" in user


def test_redaction_discipline_holds():
    """Only key/author fields can reach the prompt — the ranked dataclasses have no row-content
    field at all, so raw ``MODDATA`` (which may carry patient data) cannot leak by construction."""
    allowed = {
        "entity",
        "pk",
        "change_type",
        "component",
        "author",
        "changed_at",
        "score",
        "reasons",
    }
    assert {f.name for f in dataclasses.fields(RankedDataChange)} == allowed
    _, user = build_prompt(
        test_id="t",
        predicted_cause="DATA_CHANGE",
        error_details="values differ",
        error_stack_trace=None,
        code_candidates=[],
        data_candidates=[_data()],
        similar_cases=[],
    )
    assert "MODDATA" not in user


def test_renders_similar_cases_with_validated_conclusions():
    _, user = build_prompt(
        test_id="t",
        predicted_cause="UNKNOWN",
        error_details="boom",
        error_stack_trace=None,
        code_candidates=[],
        data_candidates=[_data()],
        similar_cases=[
            _case(
                reason_text="ref-data row deleted", causing_person="ABC", provenance="HUMAN_ENTERED"
            ),
        ],
    )
    assert "ref-data row deleted" in user
    assert "attributed to ABC" in user
    assert "HUMAN_ENTERED" in user
    assert "similarity 0.82" in user


def test_truncates_long_error_text_and_commit_message():
    long_err = "x" * 5000
    _, user = build_prompt(
        test_id="t",
        predicted_cause=None,
        error_details=long_err,
        error_stack_trace=None,
        code_candidates=[_code(message="m" * 500)],
        data_candidates=[],
        similar_cases=[],
    )
    assert "…[truncated]" in user
    assert "x" * 5000 not in user  # the full untruncated blob never reaches the prompt
    assert "m" * 500 not in user  # commit messages are capped too
    # missing predicted cause falls back to UNKNOWN
    assert "UNKNOWN" in user


def test_is_deterministic():
    args = dict(
        test_id="t",
        predicted_cause="DATA_CHANGE",
        error_details="e",
        error_stack_trace="s",
        code_candidates=[_code()],
        data_candidates=[_data()],
        similar_cases=[_case()],
    )
    assert build_prompt(**args) == build_prompt(**args)
