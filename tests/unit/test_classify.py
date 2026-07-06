"""Deterministic classification (uta.analyze.classify), incl. the relevance tie-break (#50)."""

from __future__ import annotations

import json

from sqlalchemy import select

from tests.builders import _EPOCH, make_run
from uta.analyze.classify import classify_run
from uta.analyze.lifecycle import apply_run
from uta.db import session_scope
from uta.models import Classification, CodeChangeCandidate, DataChangeCandidate
from uta.models.enums import ErrorType, PredictedCause

# A stack trace whose in-tree frame anchors path matching for test "t" (see _STACK usage below).
_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_pkg/mod.py", line 7, in t\n'
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)


def _add_code(run, commit_id="r123", author="dev", paths_json=None):
    run.code_changes.append(
        CodeChangeCandidate(
            commit_id=commit_id, author=author, committed_at=_EPOCH, paths=paths_json
        )
    )


def _add_data(run, author=None):
    run.data_changes.append(
        DataChangeCandidate(
            lx_table_code="LXFOO", change_type="U", author=author, changed_at=_EPOCH
        )
    )


def _classify(session, run):
    analysis = apply_run(session, run, baseline=None)
    session.flush()
    classify_run(session, run, analysis.opened_episodes)
    return session.scalars(select(Classification)).all()


def test_code_only_is_code_change(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert json.loads(c.evidence)["code_candidates"] == 1
        assert c.suggested_contact == "dev"  # sole commit author -> suggested contact


def test_data_only_is_data_change(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_data(run, author="THA")
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        assert c.suggested_contact == "THA"  # sole USRCODE -> suggested contact


def test_infra_error_outranks_candidates(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"}, error_type={"t": ErrorType.INFRA})
        _add_code(run)
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.INFRASTRUCTURE
        assert c.suggested_contact is None  # infra fault: no person to point at


def test_both_candidates_no_relevance_is_unknown(session_factory):
    """Both kinds present and neither matches this test -> the tie stays UNKNOWN."""
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run)
        _add_data(run, author="THA")
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        assert c.suggested_contact is None  # mixed signals: never guess a person
        assert json.loads(c.evidence)["relevance"]["tie_break"] is None


def test_relevant_code_breaks_the_tie_to_code_change(session_factory):
    """Both kinds present, but the commit touches the failing test's module -> CODE_CHANGE."""
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"}, errors={"t": ("boom", _STACK.format(msg="1 != 2"))})
        _add_code(run, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["tie_break"] == "code"
        assert relevance["top_code"]["candidate"] == "r123"
        assert relevance["top_code"]["reasons"]


def test_relevant_data_breaks_the_tie_to_data_change(session_factory):
    """Both kinds present, but the error text names the changed entity -> DATA_CHANGE."""
    with session_scope(session_factory) as s:
        run = make_run(
            s,
            1,
            {"t": "FAILED"},
            errors={"t": ("lookup failed for LXFOO row", _STACK.format(msg="missing LXFOO row"))},
        )
        _add_code(run)
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["tie_break"] == "data"
        assert relevance["top_data"]["candidate"] == "LXFOO"


def test_both_kinds_relevant_stays_unknown(session_factory):
    """When code AND data both match this test, the tie is genuinely ambiguous -> UNKNOWN."""
    with session_scope(session_factory) as s:
        run = make_run(
            s,
            1,
            {"t": "FAILED"},
            errors={"t": ("boom", _STACK.format(msg="missing LXFOO row"))},
        )
        _add_code(run, paths_json='[{"editType": "edit", "file": "/trunk/lx/ut_pkg/mod.py"}]')
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        relevance = json.loads(c.evidence)["relevance"]
        assert relevance["code_matched"] == 1 and relevance["data_matched"] == 1


def test_no_candidates_is_unknown(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        assert c.confidence is None
        assert c.suggested_contact is None


def test_multiple_code_authors_leave_contact_unset(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run, commit_id="r123", author="dev-a")
        _add_code(run, commit_id="r124", author="dev-b")
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.suggested_contact is None


def test_single_author_across_multiple_commits_is_suggested(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run, commit_id="r123", author="dev")
        _add_code(run, commit_id="r124", author="dev")
        s.flush()
        [c] = _classify(s, run)
        assert c.suggested_contact == "dev"


def test_authorless_candidate_leaves_contact_unset(session_factory):
    # An unknown author means someone unidentified is in play — too ambiguous to suggest anyone.
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run, commit_id="r123", author="dev")
        _add_code(run, commit_id="r124", author=None)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.CODE_CHANGE
        assert c.suggested_contact is None


def test_multiple_data_authors_leave_contact_unset(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_data(run, author="THA")
        _add_data(run, author="MEL")
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE
        assert c.suggested_contact is None
