"""Deterministic classification (uta.analyze.classify): the score-magnitude relevance tie-break
(#50/#73) and the documented confidence formula (#73)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from tests.builders import _EPOCH, make_build
from uta.analyze.classify import classify_build
from uta.analyze.lifecycle import apply_build
from uta.db import session_scope
from uta.kb.store import record_signatures_for_build
from uta.models import Attribution, Classification, CodeChangeCandidate, DataChangeCandidate
from uta.models.enums import ErrorType, PredictedCause, Provenance

# A stack trace whose in-tree frame anchors path matching for test "t" (see _STACK usage below).
_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_pkg/mod.py", line 7, in t\n'
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)


def _add_code(build, commit_id="r123", author="dev", paths_json=None):
    build.code_changes.append(
        CodeChangeCandidate(
            commit_id=commit_id, author=author, committed_at=_EPOCH, paths=paths_json
        )
    )


def _add_data(build, author=None, component=None):
    build.data_changes.append(
        DataChangeCandidate(
            lx_table_code="LXFOO",
            change_type="U",
            component_name=component,
            author=author,
            changed_at=_EPOCH,
        )
    )


def _classify(session, build):
    analysis = apply_build(session, build, baseline=None)
    session.flush()
    classify_build(session, build, analysis.opened_episodes)
    return session.scalars(select(Classification)).all()


def test_code_only_is_code_change(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert json.loads(c.evidence)["code_candidates"] == 1
        assert c.suggested_contact == "dev"  # sole commit author -> suggested contact


def test_data_only_is_data_change(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_data(build, author="THA")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        assert c.suggested_contact == "THA"  # sole USRCODE -> suggested contact


def test_infra_error_outranks_candidates(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"}, error_type={"t": ErrorType.INFRA})
        _add_code(build)
        _add_data(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.INFRASTRUCTURE
        assert c.suggested_contact is None  # infra fault: no person to point at
        assert c.confidence == pytest.approx(0.9)  # INFRA is read directly off the error type


def test_both_candidates_no_relevance_is_unknown(session_factory):
    """Both kinds present and neither matches this test -> the tie stays UNKNOWN."""
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build)
        _add_data(build, author="THA")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        assert c.suggested_contact is None  # mixed signals: never guess a person
        assert json.loads(c.evidence)["relevance"]["tie_break"] is None


def test_relevant_code_breaks_the_tie_to_code_change(session_factory):
    """Both kinds present, but the commit touches the failing test's module -> CODE_CHANGE."""
    with session_scope(session_factory) as s:
        build = make_build(
            s, 1, {"t": "FAILED"}, errors={"t": ("boom", _STACK.format(msg="1 != 2"))}
        )
        _add_code(build, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        _add_data(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["tie_break"] == "code"
        assert relevance["top_code"]["candidate"] == "r123"
        assert relevance["top_code"]["reasons"]


def test_relevant_data_breaks_the_tie_to_data_change(session_factory):
    """Both kinds present, but the error text names the changed entity -> DATA_CHANGE."""
    with session_scope(session_factory) as s:
        build = make_build(
            s,
            1,
            {"t": "FAILED"},
            errors={"t": ("lookup failed for LXFOO row", _STACK.format(msg="missing LXFOO row"))},
        )
        _add_code(build)
        _add_data(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["tie_break"] == "data"
        assert relevance["top_data"]["candidate"] == "LXFOO"


def test_both_kinds_equally_relevant_stays_unknown(session_factory):
    """Code AND data both match this test at the same tier — within the margin -> UNKNOWN."""
    with session_scope(session_factory) as s:
        build = make_build(
            s,
            1,
            {"t": "FAILED"},
            errors={"t": ("boom", _STACK.format(msg="missing LXFOO row"))},
        )
        _add_code(build, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        _add_data(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["code_matched"] == 1 and relevance["data_matched"] == 1
        # A close tie is a low-confidence UNKNOWN — the acceptance's "close tie" case (#73).
        assert c.confidence == pytest.approx(0.2)


def test_strong_code_match_outscores_weak_data_match(session_factory):
    """A tier-3 module code match beats a tier-2 component data mention instead of UNKNOWN (#73)."""
    with session_scope(session_factory) as s:
        build = make_build(
            s,
            1,
            {"t": "FAILED"},
            # The component name (not the entity) appears in the error text -> data tier 2;
            # the commit touches the failing test's own module -> code tier 3.
            errors={"t": ("boom", _STACK.format(msg="stale rows after LXFOO_CSVC refresh"))},
        )
        _add_code(build, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        _add_data(build, author="THA", component="LXFOO_CSVC")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        evidence = json.loads(c.evidence)
        assert evidence["relevance"]["tie_break"] == "code"
        assert evidence["relevance"]["top_code"]["score"] == 3.0
        assert evidence["relevance"]["top_data"]["score"] == 2.0
        # gap = (3-2)/3 -> 0.5 + 0.4/3 ~= 0.63.
        assert c.confidence == pytest.approx(0.63)


def test_strong_data_match_outscores_weak_code_match(session_factory):
    """Symmetric: a tier-3 entity mention beats a tier-1 package-only code match (#73)."""
    with session_scope(session_factory) as s:
        build = make_build(
            s,
            1,
            {"t": "FAILED"},
            # The entity itself is named in the error text -> data tier 3; the commit only touches
            # a sibling file in the test's package -> code tier 1.
            errors={"t": ("boom", _STACK.format(msg="missing LXFOO row"))},
        )
        _add_code(build, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/other.py"}]')
        _add_data(build, author="THA")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        evidence = json.loads(c.evidence)
        assert evidence["relevance"]["tie_break"] == "data"
        # gap = (3-1)/3 -> 0.5 + 0.4*2/3 ~= 0.77.
        assert c.confidence == pytest.approx(0.77)
        assert c.suggested_contact == "THA"


def test_no_candidates_is_unknown(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        assert c.confidence == pytest.approx(0.2)
        assert c.suggested_contact is None


# ── Confidence formula (#73) ─────────────────────────────────────────────────


def test_unambiguous_single_candidate_has_high_confidence(session_factory):
    """Code-only window + a module-level match on this test -> the high-confidence case."""
    with session_scope(session_factory) as s:
        build = make_build(
            s, 1, {"t": "FAILED"}, errors={"t": ("boom", _STACK.format(msg="1 != 2"))}
        )
        _add_code(build, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        # Unopposed full-tier match: 0.5 + 0.4 * 3/3 = 0.9.
        assert c.confidence == pytest.approx(0.9)
        inputs = json.loads(c.evidence)["confidence"]
        assert inputs == {"win_score": 3.0, "lose_score": 0.0, "kb_provenance_weight": 0}


def test_single_candidate_without_relevance_has_base_confidence(session_factory):
    """Code-only but nothing links the commit to this test -> base confidence, no gap term."""
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.confidence == pytest.approx(0.5)


def test_kb_provenance_boosts_confidence(session_factory):
    """A human-corrected conclusion on this failure's signature raises the confidence (#73)."""
    stack = _STACK.format(msg="1 != 2")
    with session_scope(session_factory) as s:
        # Episode 1: the failure occurs and a human corrects the AI's cause -> the conclusion
        # attaches to the failure signature (HUMAN_CORRECTED, the strongest tier).
        run1 = make_build(s, 1, {"t": "FAILED"}, errors={"t": ("boom", stack)})
        record_signatures_for_build(s, run1)
        analysis = apply_build(s, run1, baseline=None)
        s.flush()
        classify_build(s, run1, analysis.opened_episodes)
        [(_, episode_id)] = analysis.opened_episodes
        signature_id = run1.results[0].signature_id
        assert signature_id is not None
        s.add(
            Attribution(
                episode_id=episode_id,
                signature_id=signature_id,
                causing_person="dev",
                cause_provenance=Provenance.HUMAN_CORRECTED,
                original_ai_cause="someone-else",
            )
        )
        # The test recovers, then regresses again with the same failure -> a new episode whose
        # signature the KB now knows with validated human knowledge.
        run2 = make_build(s, 2, {"t": "PASSED"})
        apply_build(s, run2, baseline=run1)
        s.flush()
        run3 = make_build(s, 3, {"t": "FAILED"}, errors={"t": ("boom", stack)})
        _add_code(run3, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        record_signatures_for_build(s, run3)
        analysis3 = apply_build(s, run3, baseline=run2)
        s.flush()
        classify_build(s, run3, analysis3.opened_episodes)
        s.flush()
        newest = s.scalars(select(Classification).order_by(Classification.id.desc()).limit(1)).one()
        assert newest.predicted_cause == PredictedCause.CODE_CHANGE
        # 0.5 (base) + 0.4 (full-tier gap) + 0.1 * 4/4 (HUMAN_CORRECTED) = 1.0, capped.
        assert newest.confidence == pytest.approx(1.0)
        assert json.loads(newest.evidence)["confidence"]["kb_provenance_weight"] == 4


def test_multiple_code_authors_leave_contact_unset(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build, commit_id="r123", author="dev-a")
        _add_code(build, commit_id="r124", author="dev-b")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.suggested_contact is None


def test_single_author_across_multiple_commits_is_suggested(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build, commit_id="r123", author="dev")
        _add_code(build, commit_id="r124", author="dev")
        s.flush()
        [c] = _classify(s, build)
        assert c.suggested_contact == "dev"


def test_authorless_candidate_leaves_contact_unset(session_factory):
    # An unknown author means someone unidentified is in play — too ambiguous to suggest anyone.
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_code(build, commit_id="r123", author="dev")
        _add_code(build, commit_id="r124", author=None)
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.suggested_contact is None


def test_multiple_data_authors_leave_contact_unset(session_factory):
    with session_scope(session_factory) as s:
        build = make_build(s, 1, {"t": "FAILED"})
        _add_data(build, author="THA")
        _add_data(build, author="MEL")
        s.flush()
        [c] = _classify(s, build)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        assert c.suggested_contact is None
