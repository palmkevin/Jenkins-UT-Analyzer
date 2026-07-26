"""Build Incident detection, streak lifecycle, and enrichment (issue #171).

A **Build Incident** opens on a build whose top-level Jenkins ``result`` is ``FAILURE`` or
``ABORTED`` and recovers on the next build reaching ``SUCCESS`` or ``UNSTABLE`` — independent of the
EXPECTED_TRACKS completeness check that gates *test* analysis, so a FAILURE build that is
"incomplete" (and therefore skipped as a test baseline) still gets its incident. Consecutive
non-green builds collapse into **one** incident (the streak model, mirroring how failure episodes
collapse consecutive test failures); a green build recovers the open one; a later non-green build
opens a fresh incident and bumps the flap/reopen counter.

Enrichment differs by kind:

- ``PIPELINE_FAILURE`` — full reuse of the analysis stack: the change candidates already persisted
  on the build (SVN commits + ``ut_ref`` data changes in the correlation window) drive the
  deterministic :func:`classify_incident`, and — with a real provider — :func:`hypothesize_incident`
  fills the LLM hypothesis from the incident-namespaced knowledge base. A **failure signature** is
  drawn from the failing stage's log (the caller supplies it).
- ``ABORTED`` — no signature, no classification, no change-candidate reasoning: straight to a
  human-documented reason (plus an optional LLM sanity note is out of scope of the deterministic
  path). Nothing is fabricated.

The one reserved kind (``SLOW``, issue #172 — a completed-build duration regression) has no
detector; nothing here opens it. An overrunning *in-progress* build is never an incident (ADR-0006).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.analyze.classify import _sole_author
from uta.analyze.error_type import derive_error_type
from uta.analyze.relevance import rank_candidates
from uta.kb.retrieval import similar_cases
from uta.kb.store import record_incident_signature
from uta.llm import HypothesisProvider, NoopHypothesisProvider
from uta.llm.prompt import build_prompt
from uta.models import Build, BuildIncident, Classification, FailureSignature
from uta.models.enums import ErrorType, IncidentKind, PredictedCause, SignatureKind

# Non-green terminal results that open/extend an incident. UNSTABLE and NOT_BUILT are excluded:
# UNSTABLE is a test-outcome (it *recovers* an incident) and NOT_BUILT is a no-op.
_RESULT_TO_KIND = {
    "FAILURE": IncidentKind.PIPELINE_FAILURE,
    "ABORTED": IncidentKind.ABORTED,
}
# Results that recover an open incident (a red→green-ish transition), independent of completeness.
GREEN_RESULTS = frozenset({"SUCCESS", "UNSTABLE"})
# Every result we act on at all; anything else (e.g. NOT_BUILT, or a null/in-progress result) is a
# no-op for the incident feed.
TERMINAL_RESULTS = frozenset(_RESULT_TO_KIND) | GREEN_RESULTS

_INFRA_CONFIDENCE = 0.9
_CAUSE_CONFIDENCE = 0.6  # a single-kind candidate lead, no per-test relevance ranking to sharpen it
_UNKNOWN_CONFIDENCE = 0.2


@dataclass
class IncidentOutcome:
    """What the incident feed did for one build."""

    incident: BuildIncident | None = None
    opened: bool = False  # a brand-new incident opened this build (a streak start)
    recovered: bool = False


def result_to_kind(result: str | None) -> str | None:
    """The :class:`IncidentKind` a non-green result opens, or ``None`` for green/unknown results."""
    if not result:
        return None
    return _RESULT_TO_KIND.get(result.upper())


def _open_incident(session: Session) -> BuildIncident | None:
    return session.scalar(
        select(BuildIncident)
        .where(BuildIncident.is_open.is_(True))
        .order_by(BuildIncident.opened_build_id.desc())
        .limit(1)
    )


def classify_incident(session: Session, build: Build, incident: BuildIncident) -> Classification:
    """Deterministic cause for a pipeline-failure incident (reuses the classifier's vocabulary).

    Rule (ordered): an INFRA-looking failing-stage signature outranks any coincidental change; else
    a single candidate kind in the window wins (code-only → CODE_CHANGE, data-only → DATA_CHANGE);
    both kinds or none → UNKNOWN (there is no per-test relevance ranking to break a build-level
    tie). A suggested contact rides along when the winning kind has exactly one author. Append-only.
    """
    code_n = len(build.code_changes)
    data_n = len(build.data_changes)

    infra = False
    if incident.signature_id is not None:
        sig = session.get(FailureSignature, incident.signature_id)
        if sig is not None:
            infra = (
                derive_error_type("FAILED", sig.exception_type, sig.normalized_text)
                == ErrorType.INFRA
            )

    contact: str | None = None
    if infra:
        cause, confidence = PredictedCause.INFRASTRUCTURE, _INFRA_CONFIDENCE
    elif code_n and not data_n:
        cause, confidence = PredictedCause.CODE_CHANGE, _CAUSE_CONFIDENCE
        contact = _sole_author(build.code_changes)
    elif data_n and not code_n:
        cause, confidence = PredictedCause.DATA_CHANGE, _CAUSE_CONFIDENCE
        contact = _sole_author(build.data_changes)
    else:
        cause, confidence = PredictedCause.UNKNOWN, _UNKNOWN_CONFIDENCE

    evidence = {
        "code_candidates": code_n,
        "data_candidates": data_n,
        "infra_error": infra,
        "failing_stage": incident.failing_stage,
    }
    classification = Classification(
        incident_id=incident.id,
        predicted_cause=cause,
        confidence=confidence,
        suggested_contact=contact,
        evidence=json.dumps(evidence),
    )
    session.add(classification)
    return classification


def hypothesize_incident(
    session: Session,
    build: Build,
    incident: BuildIncident,
    provider: HypothesisProvider,
    *,
    top_k: int = 5,
    cutoff: float = 0.3,
) -> bool:
    """Fill the incident's LLM hypothesis from the incident-namespaced KB. No-op under Noop.

    Mirrors :func:`uta.analyze.hypothesize.hypothesize_episode` but for a build incident: the RAG
    context is the top-k **incident** signatures similar to this one (never test signatures), plus
    the build's ranked change candidates. Returns whether a value was written.
    """
    if isinstance(provider, NoopHypothesisProvider):
        return False
    if incident.signature_id is None:
        return False
    sig = session.get(FailureSignature, incident.signature_id)
    classification = session.scalar(
        select(Classification)
        .where(Classification.incident_id == incident.id)
        .order_by(Classification.created_at.desc(), Classification.id.desc())
        .limit(1)
    )
    if sig is None or classification is None:
        return False

    cases = similar_cases(
        session,
        sig.normalized_text,
        k=top_k,
        cutoff=cutoff,
        exclude_signature_id=sig.id,
        kind=SignatureKind.INCIDENT,
    )
    ranked = rank_candidates(
        build.code_changes,
        build.data_changes,
        file_path=None,
        error_details=None,
        error_stack_trace=sig.normalized_text,
        class_name=None,
    )
    system, user = build_prompt(
        test_id=f"build #{build.build_number} pipeline failure ({incident.failing_stage or '?'})",
        predicted_cause=classification.predicted_cause,
        error_details=None,
        error_stack_trace=sig.normalized_text,
        code_candidates=ranked.code,
        data_candidates=ranked.data,
        similar_cases=cases,
    )
    hypothesis = provider.hypothesize(system=system, user=user)
    if hypothesis is None:
        return False
    classification.llm_hypothesis = hypothesis.text
    return True


def apply_build_incident(
    session: Session,
    build: Build,
    result: str | None,
    *,
    failing_stage: str | None = None,
    failing_stage_log: str | None = None,
    hypothesis_provider: HypothesisProvider | None = None,
    kb_top_k: int = 5,
    kb_similarity_cutoff: float = 0.3,
) -> IncidentOutcome:
    """Open / extend / recover the build-incident streak for one **terminal** build.

    ``result`` is the build's top-level Jenkins result. Green results recover an open incident;
    ``FAILURE``/``ABORTED`` open a new incident or extend the open one; anything else is a no-op.
    Enrichment (signature + classification + hypothesis) runs only when a *new* ``PIPELINE_FAILURE``
    incident opens. The caller guards against historical re-ingest (incidents advance forward only).
    """
    result_norm = (result or "").upper()
    open_incident = _open_incident(session)

    if result_norm in GREEN_RESULTS:
        if open_incident is not None:
            open_incident.recovered_build_id = build.id
            open_incident.recovered_at = build.started_at
            open_incident.is_open = False
            return IncidentOutcome(incident=open_incident, recovered=True)
        return IncidentOutcome()

    kind = result_to_kind(result_norm)
    if kind is None:
        # NOT_BUILT / null / in-progress — neither opens nor recovers.
        return IncidentOutcome(incident=open_incident)

    if open_incident is not None:
        # Extend the streak — one incident spans consecutive non-green builds. The kind stays
        # whatever opened it; a different kind is noted (mixed streak) but does not split it.
        open_incident.last_build_id = build.id
        open_incident.last_at = build.started_at
        open_incident.build_count = (open_incident.build_count or 1) + 1
        if kind != open_incident.kind:
            others = {k for k in (open_incident.mixed_kinds or "").split(",") if k}
            others.add(kind)
            open_incident.mixed_kinds = ",".join(sorted(others))
        return IncidentOutcome(incident=open_incident)

    # Brand-new incident (a streak start). Reopen/flap count = how many incidents came before.
    prior = session.scalar(select(func.count()).select_from(BuildIncident)) or 0
    incident = BuildIncident(
        kind=kind,
        opened_build_id=build.id,
        opened_at=build.started_at,
        last_build_id=build.id,
        last_at=build.started_at,
        build_count=1,
        reopen_count=prior,
        failing_stage=failing_stage,
    )
    session.add(incident)
    session.flush()  # id needed for the classification / attribution links

    if kind == IncidentKind.PIPELINE_FAILURE:
        record_incident_signature(session, incident, failing_stage_log)
        classify_incident(session, build, incident)
        hypothesize_incident(
            session,
            build,
            incident,
            hypothesis_provider or NoopHypothesisProvider(),
            top_k=kb_top_k,
            cutoff=kb_similarity_cutoff,
        )
    return IncidentOutcome(incident=incident, opened=True)
