"""Deterministic cause classification (the predicted cause).

v1 is **windowing, not ranking**: the pipeline has already persisted the code-change candidates
(SVN-update revisions in the run window) and data-change candidates (`ut_ref` changes in the
lookback window, with the B1 tolerance margin) on the run. This step turns their *presence* into a
``CODE_CHANGE`` / ``DATA_CHANGE`` / ``INFRASTRUCTURE`` / ``UNKNOWN`` label per newly-opened failure
episode, attaching the evidence so the human can attribute the real cause.

Rule (ordered, documented because it is the whole v1 commitment):

1. **INFRASTRUCTURE** if the failure's derived error type is INFRA (a DB/network fault outranks any
   coincidental commit/data change).
2. **CODE_CHANGE** if code candidates are present and data candidates are not.
3. **DATA_CHANGE** if data candidates are present and code candidates are not.
4. **UNKNOWN** otherwise — both kinds present (genuinely ambiguous; both attached as evidence) or
   neither. There is deliberately **no confidence number**: with no knowledge base to rank against
   on day one it would be fabricated (deferred to the knowledge-base learning loop).

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

from uta.ingest.ut_report import FAILED_STATUSES
from uta.models import Classification, CodeChangeCandidate, DataChangeCandidate, Run, TestResult
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


def _has_infra_failure(session: Session, run: Run, identity_id: int) -> bool:
    types = session.scalars(
        select(TestResult.error_type).where(
            TestResult.run_id == run.id,
            TestResult.test_identity_id == identity_id,
            TestResult.status.in_(FAILED_STATUSES),
        )
    ).all()
    return ErrorType.INFRA in types


def classify_episode(
    session: Session, run: Run, identity_id: int, episode_id: int
) -> Classification:
    """Create and persist the deterministic :class:`Classification` for one new episode."""
    code_n = len(run.code_changes)
    data_n = len(run.data_changes)
    infra = _has_infra_failure(session, run, identity_id)

    if infra:
        cause = PredictedCause.INFRASTRUCTURE
    elif code_n and not data_n:
        cause = PredictedCause.CODE_CHANGE
    elif data_n and not code_n:
        cause = PredictedCause.DATA_CHANGE
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
    }
    classification = Classification(
        episode_id=episode_id,
        predicted_cause=cause,
        confidence=None,  # deferred (v1: null)
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
