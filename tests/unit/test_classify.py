"""Deterministic classification (uta.analyze.classify)."""

from __future__ import annotations

import json

from sqlalchemy import select

from tests.builders import _EPOCH, make_run
from uta.analyze.classify import classify_run
from uta.analyze.lifecycle import apply_run
from uta.db import session_scope
from uta.models import Classification, CodeChangeCandidate, DataChangeCandidate
from uta.models.enums import ErrorType, PredictedCause


def _add_code(run):
    run.code_changes.append(
        CodeChangeCandidate(commit_id="r123", author="dev", committed_at=_EPOCH)
    )


def _add_data(run):
    run.data_changes.append(
        DataChangeCandidate(lx_table_code="LXFOO", change_type="U", changed_at=_EPOCH)
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


def test_data_only_is_data_change(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.DATA_CHANGE


def test_infra_error_outranks_candidates(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"}, error_type={"t": ErrorType.INFRA})
        _add_code(run)
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.INFRASTRUCTURE


def test_both_candidates_is_unknown(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        _add_code(run)
        _add_data(run)
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.UNKNOWN


def test_no_candidates_is_unknown(session_factory):
    with session_scope(session_factory) as s:
        run = make_run(s, 1, {"t": "FAILED"})
        s.flush()
        [c] = _classify(s, run)
        assert c.predicted_cause == PredictedCause.UNKNOWN
        assert c.confidence is None
