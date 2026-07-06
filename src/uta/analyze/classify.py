"""Deterministic cause classification (the predicted cause).

The pipeline has already persisted the code-change candidates (SVN-update revisions in the run
window) and data-change candidates (`ut_ref` changes in the lookback window, with the B1 tolerance
margin) on the run. This step turns their presence — sharpened by the **per-test relevance
ranking** (:mod:`uta.analyze.relevance`) — into a ``CODE_CHANGE`` / ``DATA_CHANGE`` /
``INFRASTRUCTURE`` / ``UNKNOWN`` label per newly-opened failure episode, attaching the evidence so
the human can attribute the real cause.

Rule (ordered, documented because it is the whole commitment):

1. **INFRASTRUCTURE** if the failure's derived error type is INFRA (a DB/network fault outranks any
   coincidental commit/data change).
2. **CODE_CHANGE** if code candidates are present and data candidates are not.
3. **DATA_CHANGE** if data candidates are present and code candidates are not.
4. Both kinds present: **relevance breaks the tie** — if exactly one kind has a candidate that
   matches *this* test (changed path overlaps the test's module/stack frames, or the changed
   entity is named in the error text), that kind wins; the tie-break is recorded in the evidence.
5. **UNKNOWN** otherwise — both kinds relevant, neither relevant, or no candidates at all. There
   is deliberately **no confidence number**: the coarse relevance tiers can order candidates but a
   calibrated confidence still needs the knowledge-base learning loop (deferred).

A **suggested contact** rides along when the winning cause has exactly one author in play: the SVN
commit author for ``CODE_CHANGE``, the ``V_TRACKING`` ``USRCODE`` for ``DATA_CHANGE``. Anything
ambiguous — several authors, or a candidate whose author is unknown — leaves it ``None`` rather
than guess, so the one-click Confirm never stamps a fabricated person.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from uta.analyze.relevance import RankedChanges, rank_candidates
from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import (
    Classification,
    CodeChangeCandidate,
    DataChangeCandidate,
    Run,
    TestIdentity,
    TestResult,
)
from uta.models.enums import ErrorType, PredictedCause


def _sole_author(candidates: Iterable[CodeChangeCandidate | DataChangeCandidate]) -> str | None:
    """The single author behind *all* candidates, or ``None`` when unknown or ambiguous.

    Conservative by design: a candidate without an author means someone unknown is in play, and
    more than one distinct author is genuinely ambiguous — both yield ``None``.
    """
    authors = {(c.author or "").strip() for c in candidates}
    if len(authors) != 1:
        return None
    return next(iter(authors)) or None


def _failing_results(session: Session, run: Run, identity_id: int) -> list[TestResult]:
    return list(
        session.scalars(
            select(TestResult)
            .where(
                TestResult.run_id == run.id,
                TestResult.test_identity_id == identity_id,
                TestResult.status.in_(FAILED_STATUSES),
            )
            .order_by(TestResult.id)
        )
    )


def _rank_for_failure(
    session: Session, run: Run, identity_id: int, failures: list[TestResult]
) -> RankedChanges:
    """Rank the run's candidates against this test's failure (the first result with error text)."""
    primary = next(
        (r for r in failures if r.error_details or r.error_stack_trace),
        failures[0] if failures else None,
    )
    identity = session.get(TestIdentity, identity_id)
    return rank_candidates(
        run.code_changes,
        run.data_changes,
        file_path=primary.file_path if primary else None,
        error_details=primary.error_details if primary else None,
        error_stack_trace=primary.error_stack_trace if primary else None,
        class_name=identity.class_name if identity else None,
    )


def _top_evidence(top) -> dict | None:
    """The strongest match of one kind, for the evidence JSON (only when it actually matched)."""
    if top is None or top.score <= 0:
        return None
    label = getattr(top, "revision", None) or getattr(top, "entity", None)
    return {
        "candidate": label,
        "author": top.author,
        "score": top.score,
        "reasons": list(top.reasons),
    }


def classify_episode(
    session: Session, run: Run, identity_id: int, episode_id: int
) -> Classification:
    """Create and persist the deterministic :class:`Classification` for one new episode."""
    code_n = len(run.code_changes)
    data_n = len(run.data_changes)
    failures = _failing_results(session, run, identity_id)
    infra = any(r.error_type == ErrorType.INFRA for r in failures)
    ranked = _rank_for_failure(session, run, identity_id, failures)

    tie_break: str | None = None
    if infra:
        cause = PredictedCause.INFRASTRUCTURE
    elif code_n and not data_n:
        cause = PredictedCause.CODE_CHANGE
    elif data_n and not code_n:
        cause = PredictedCause.DATA_CHANGE
    elif code_n and data_n and ranked.code_relevant and not ranked.data_relevant:
        cause = PredictedCause.CODE_CHANGE
        tie_break = "code"
    elif code_n and data_n and ranked.data_relevant and not ranked.code_relevant:
        cause = PredictedCause.DATA_CHANGE
        tie_break = "data"
    else:
        cause = PredictedCause.UNKNOWN

    if cause == PredictedCause.CODE_CHANGE:
        contact = _sole_author(run.code_changes)
    elif cause == PredictedCause.DATA_CHANGE:
        contact = _sole_author(run.data_changes)
    else:
        contact = None

    evidence = {
        "code_candidates": code_n,
        "data_candidates": data_n,
        "infra_error": infra,
        "baseline_run_id": run.baseline_run_id,
        "relevance": {
            "code_matched": sum(1 for c in ranked.code if c.score > 0),
            "data_matched": sum(1 for d in ranked.data if d.score > 0),
            "tie_break": tie_break,
            "top_code": _top_evidence(ranked.top_code),
            "top_data": _top_evidence(ranked.top_data),
        },
    }
    classification = Classification(
        episode_id=episode_id,
        predicted_cause=cause,
        confidence=None,  # deferred (needs the KB learning loop to calibrate)
        suggested_contact=contact,
        evidence=json.dumps(evidence),
    )
    session.add(classification)
    return classification


def classify_run(session: Session, run: Run, opened_episodes: list[tuple[int, int]]) -> int:
    """Classify every episode newly opened by this run. Returns how many were classified."""
    for identity_id, episode_id in opened_episodes:
        classify_episode(session, run, identity_id, episode_id)
    return len(opened_episodes)
