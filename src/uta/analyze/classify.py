"""Deterministic cause classification (the predicted cause).

The pipeline has already persisted the code-change candidates (SVN-update revisions in the build
window) and data-change candidates (`ut_ref` changes in the lookback window, with the B1 tolerance
margin) on the build. This step turns their presence — sharpened by the **per-test relevance
ranking** (:mod:`uta.analyze.relevance`) — into a ``CODE_CHANGE`` / ``DATA_CHANGE`` /
``INFRASTRUCTURE`` / ``UNKNOWN`` label per newly-opened failure episode, attaching the evidence so
the human can attribute the real cause.

Rule (ordered, documented because it is the whole commitment):

1. **INFRASTRUCTURE** if the failure's derived error type is INFRA (a DB/network fault outranks any
   coincidental commit/data change).
2. **CODE_CHANGE** if code candidates are present and data candidates are not.
3. **DATA_CHANGE** if data candidates are present and code candidates are not.
4. Both kinds present: **relevance breaks the tie by score magnitude** (issue #73) — the top code
   candidate's relevance score is compared against the top data candidate's, and the stronger kind
   wins when it leads by at least :data:`TIE_BREAK_MARGIN` (one full relevance tier). A tier-3
   module-level code match therefore beats a tier-2 component data mention instead of collapsing to
   UNKNOWN; the tie-break is recorded in the evidence.
5. **UNKNOWN** otherwise — scores within the margin (including both zero), or no candidates at all.

Every classification also carries a **confidence** in ``[0, 1]`` — deterministic and documented,
not a learned model (see :func:`_confidence`):

- ``INFRASTRUCTURE``: flat **0.9** — the INFRA error type is read directly off the failure.
- ``CODE_CHANGE`` / ``DATA_CHANGE``: ``0.5 + 0.4 * gap + 0.1 * kb``, where ``gap`` is the relevance
  score lead of the winning kind's top candidate over the losing kind's, normalized by the top
  tier (:data:`~uta.analyze.relevance.SCORE_MODULE`), and ``kb`` is the strongest KB provenance
  weight attached to this failure's signature, normalized by the ``HUMAN_CORRECTED`` maximum
  (:data:`~uta.kb.retrieval.PROVENANCE_WEIGHT`) — validated human knowledge about this exact
  failure raises confidence.
- ``UNKNOWN``: flat **0.2** — ambiguity is the finding; nothing boosts confidence in it.

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

from uta.analyze.relevance import SCORE_MODULE, RankedChanges, rank_candidates
from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.retrieval import PROVENANCE_WEIGHT, strongest_provenance_weight
from uta.models import (
    Build,
    Classification,
    CodeChangeCandidate,
    DataChangeCandidate,
    TestIdentity,
    TestResult,
)
from uta.models.enums import ErrorType, PredictedCause, Provenance

# The score lead the top candidate of one kind needs over the other kind's to win a "both kinds
# present" tie — one full relevance tier, so equal-tier matches stay UNKNOWN while any genuinely
# stronger match (module vs component, entity vs package, match vs no match) resolves the tie.
TIE_BREAK_MARGIN = 1.0

# Confidence formula weights (documented in the module docstring).
_BASE_CONFIDENCE = 0.5  # a predicted cause with no relevance lead starts here
_GAP_WEIGHT = 0.4  # how much a full-tier relevance lead is worth
_KB_WEIGHT = 0.1  # how much fully-validated KB knowledge of this signature is worth
_INFRA_CONFIDENCE = 0.9  # INFRA is read directly off the failure's error type
_UNKNOWN_CONFIDENCE = 0.2  # ambiguity is the finding
_MAX_PROVENANCE_WEIGHT = PROVENANCE_WEIGHT[Provenance.HUMAN_CORRECTED]


def _sole_author(candidates: Iterable[CodeChangeCandidate | DataChangeCandidate]) -> str | None:
    """The single author behind *all* candidates, or ``None`` when unknown or ambiguous.

    Conservative by design: a candidate without an author means someone unknown is in play, and
    more than one distinct author is genuinely ambiguous — both yield ``None``.
    """
    authors = {(c.author or "").strip() for c in candidates}
    if len(authors) != 1:
        return None
    return next(iter(authors)) or None


def _failing_results(session: Session, build: Build, identity_id: int) -> list[TestResult]:
    return list(
        session.scalars(
            select(TestResult)
            .where(
                TestResult.build_id == build.id,
                TestResult.test_identity_id == identity_id,
                TestResult.status.in_(FAILED_STATUSES),
            )
            .order_by(TestResult.id)
        )
    )


def _rank_for_failure(
    session: Session, build: Build, identity_id: int, failures: list[TestResult]
) -> RankedChanges:
    """Rank the build's candidates against this test's failure (the first result with error
    text)."""
    primary = next(
        (r for r in failures if r.error_details or r.error_stack_trace),
        failures[0] if failures else None,
    )
    identity = session.get(TestIdentity, identity_id)
    return rank_candidates(
        build.code_changes,
        build.data_changes,
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


def _signature_provenance_weight(session: Session, failures: list[TestResult]) -> int:
    """The strongest KB provenance weight attached to this failure's signature (0 when unknown).

    The pipeline records signatures before classifying, so a recurring failure's result already
    links to the signature carrying past (possibly human-validated) conclusions.
    """
    signature_id = next((r.signature_id for r in failures if r.signature_id is not None), None)
    return strongest_provenance_weight(session, signature_id)


def _confidence(
    cause: str, *, win_score: float, lose_score: float, kb_provenance_weight: int
) -> float:
    """The documented deterministic confidence formula (issue #73) — see the module docstring.

    ``win_score``/``lose_score`` are the top relevance scores of the predicted kind and the other
    kind (0 when that kind has no candidates), so the gap term also rewards an unopposed match.
    """
    if cause == PredictedCause.INFRASTRUCTURE:
        return _INFRA_CONFIDENCE
    if cause == PredictedCause.UNKNOWN:
        return _UNKNOWN_CONFIDENCE
    gap = min(1.0, max(0.0, win_score - lose_score) / SCORE_MODULE)
    kb = kb_provenance_weight / _MAX_PROVENANCE_WEIGHT
    return round(min(1.0, _BASE_CONFIDENCE + _GAP_WEIGHT * gap + _KB_WEIGHT * kb), 2)


def classify_episode(
    session: Session, build: Build, identity_id: int, episode_id: int
) -> Classification:
    """Create and persist the deterministic :class:`Classification` for one new episode."""
    code_n = len(build.code_changes)
    data_n = len(build.data_changes)
    failures = _failing_results(session, build, identity_id)
    infra = any(r.error_type == ErrorType.INFRA for r in failures)
    ranked = _rank_for_failure(session, build, identity_id, failures)
    code_score = ranked.top_code.score if ranked.top_code else 0.0
    data_score = ranked.top_data.score if ranked.top_data else 0.0

    tie_break: str | None = None
    if infra:
        cause = PredictedCause.INFRASTRUCTURE
    elif code_n and not data_n:
        cause = PredictedCause.CODE_CHANGE
    elif data_n and not code_n:
        cause = PredictedCause.DATA_CHANGE
    elif code_n and data_n and code_score - data_score >= TIE_BREAK_MARGIN:
        cause = PredictedCause.CODE_CHANGE
        tie_break = "code"
    elif code_n and data_n and data_score - code_score >= TIE_BREAK_MARGIN:
        cause = PredictedCause.DATA_CHANGE
        tie_break = "data"
    else:
        cause = PredictedCause.UNKNOWN

    if cause == PredictedCause.CODE_CHANGE:
        contact = _sole_author(build.code_changes)
        win_score, lose_score = code_score, data_score
    elif cause == PredictedCause.DATA_CHANGE:
        contact = _sole_author(build.data_changes)
        win_score, lose_score = data_score, code_score
    else:
        contact = None
        win_score, lose_score = 0.0, 0.0

    kb_weight = _signature_provenance_weight(session, failures)
    confidence = _confidence(
        cause, win_score=win_score, lose_score=lose_score, kb_provenance_weight=kb_weight
    )

    evidence = {
        "code_candidates": code_n,
        "data_candidates": data_n,
        "infra_error": infra,
        "baseline_build_id": build.baseline_build_id,
        "relevance": {
            "code_matched": sum(1 for c in ranked.code if c.score > 0),
            "data_matched": sum(1 for d in ranked.data if d.score > 0),
            "tie_break": tie_break,
            "top_code": _top_evidence(ranked.top_code),
            "top_data": _top_evidence(ranked.top_data),
        },
        # The confidence formula's inputs, so the number is auditable from the record page.
        "confidence": {
            "win_score": win_score,
            "lose_score": lose_score,
            "kb_provenance_weight": kb_weight,
        },
    }
    classification = Classification(
        episode_id=episode_id,
        predicted_cause=cause,
        confidence=confidence,
        suggested_contact=contact,
        evidence=json.dumps(evidence),
    )
    session.add(classification)
    return classification


def classify_build(session: Session, build: Build, opened_episodes: list[tuple[int, int]]) -> int:
    """Classify every episode newly opened by this build. Returns how many were classified."""
    for identity_id, episode_id in opened_episodes:
        classify_episode(session, build, identity_id, episode_id)
    return len(opened_episodes)
