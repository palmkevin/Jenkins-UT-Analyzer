"""LLM prompt assembly (Milestone 5) — pure, no I/O, no network."""

from __future__ import annotations

from uta.kb.retrieval import SimilarCase
from uta.llm.prompt import build_prompt


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


def test_includes_failure_cause_and_signal_counts():
    system, user = build_prompt(
        test_id="pkg.mod.TestB.test_y",
        predicted_cause="CODE_CHANGE",
        error_details="AssertionError: expected 3 got 4",
        error_stack_trace="Traceback ... line 12",
        code_candidates=2,
        data_candidates=0,
        similar_cases=[],
    )
    assert "one concise sentence" in system.lower() or "one sentence" in system.lower()
    assert "pkg.mod.TestB.test_y" in user
    assert "CODE_CHANGE" in user
    assert "2 code change(s)" in user
    assert "0 reference-data change(s)" in user
    assert "(no similar past cases on record)" in user


def test_renders_similar_cases_with_validated_conclusions():
    _, user = build_prompt(
        test_id="t",
        predicted_cause="UNKNOWN",
        error_details="boom",
        error_stack_trace=None,
        code_candidates=0,
        data_candidates=1,
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


def test_truncates_long_error_text():
    long_err = "x" * 5000
    _, user = build_prompt(
        test_id="t",
        predicted_cause=None,
        error_details=long_err,
        error_stack_trace=None,
        code_candidates=0,
        data_candidates=0,
        similar_cases=[],
    )
    assert "…[truncated]" in user
    assert "x" * 5000 not in user  # the full untruncated blob never reaches the prompt
    # missing predicted cause falls back to UNKNOWN
    assert "UNKNOWN" in user


def test_is_deterministic():
    args = dict(
        test_id="t",
        predicted_cause="DATA_CHANGE",
        error_details="e",
        error_stack_trace="s",
        code_candidates=1,
        data_candidates=1,
        similar_cases=[_case()],
    )
    assert build_prompt(**args) == build_prompt(**args)
