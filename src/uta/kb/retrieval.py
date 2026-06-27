"""Knowledge-base retrieval (PLAN §4) — exact recurrence + fuzzy similar cases, on stock Postgres.

Two cheap layers, no vector store:

1. **Exact recurrence** — equality on the signature **hash** (test identity + normalized text).
   Index-backed, zero false positives: "we've seen this *exact* failure before."
2. **Fuzzy "similar past cases"** — trigram ``similarity()`` over the normalized text (the
   ``pg_trgm`` GIN index), ``ORDER BY similarity DESC LIMIT k``. Offline (SQLite, no ``pg_trgm``)
   this degrades to a :mod:`difflib` ratio over the few rows the tests create — same shape, same
   ranking contract, so the logic is exercised by the offline gate.

Both layers are **provenance-weighted**: each match carries the strongest *validated* human
conclusion attached to that signature, and near-equal matches are ordered so confirmed/corrected
knowledge ranks above unvalidated AI guesses (PLAN §4: validation is what teaches).
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.kb.signature import NormalizedSignature, compute_hash
from uta.models import Attribution, FailureSignature, TestIdentity
from uta.models.enums import Provenance

# How strongly a conclusion teaches the KB — validation, not authorship (PLAN §4). Unconfirmed AI
# guesses are weak hints (weight 0), human corrections the most informative.
PROVENANCE_WEIGHT: dict[str, int] = {
    Provenance.HUMAN_CORRECTED: 4,
    Provenance.HUMAN_ENTERED: 3,
    Provenance.AI_CONFIRMED: 2,
    Provenance.AI_UNCONFIRMED: 0,
}


@dataclass(frozen=True)
class SimilarCase:
    signature_id: int
    identity_id: int
    test_id: str
    exception_type: str | None
    occurrence_count: int
    similarity: float
    reason_text: str | None
    causing_person: str | None
    provenance: str | None
    provenance_weight: int


def _is_postgres(session: Session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def _best_attribution(session: Session, signature_id: int) -> Attribution | None:
    """The strongest *validated* conclusion attached to a signature (provenance-weighted)."""
    attrs = session.scalars(
        select(Attribution).where(
            Attribution.signature_id == signature_id,
            (Attribution.reason_text.isnot(None)) | (Attribution.causing_person.isnot(None)),
        )
    ).all()
    if not attrs:
        return None
    return max(
        attrs,
        key=lambda a: (
            PROVENANCE_WEIGHT.get(a.reason_provenance, 0),
            a.validated_at or a.created_at,
        ),
    )


def exact_recurrence(
    session: Session, identity_name: str, sig: NormalizedSignature
) -> FailureSignature | None:
    """The stored signature whose hash matches this failure exactly, if any (instant lookup)."""
    sig_hash = compute_hash(identity_name, sig.text)
    return session.scalar(
        select(FailureSignature).where(FailureSignature.signature_hash == sig_hash)
    )


def _to_case(session: Session, sig: FailureSignature, similarity: float) -> SimilarCase:
    best = _best_attribution(session, sig.id)
    return SimilarCase(
        signature_id=sig.id,
        identity_id=sig.test_identity_id,
        test_id=session.get(TestIdentity, sig.test_identity_id).canonical_name,
        exception_type=sig.exception_type,
        occurrence_count=sig.occurrence_count,
        similarity=round(similarity, 4),
        reason_text=best.reason_text if best else None,
        causing_person=best.causing_person if best else None,
        provenance=best.reason_provenance if best else None,
        provenance_weight=PROVENANCE_WEIGHT.get(best.reason_provenance, 0) if best else 0,
    )


def similar_cases(
    session: Session,
    normalized_text: str,
    *,
    k: int = 5,
    cutoff: float = 0.3,
    exclude_signature_id: int | None = None,
) -> list[SimilarCase]:
    """Top-``k`` historical signatures most similar to ``normalized_text`` (similarity > cutoff).

    Ranked by trigram similarity, then by provenance weight so confirmed knowledge surfaces among
    near-equal text matches. Postgres uses ``pg_trgm``; offline falls back to a difflib ratio.
    """
    if _is_postgres(session):
        sim = func.similarity(FailureSignature.normalized_text, normalized_text)
        stmt = select(FailureSignature, sim.label("sim")).where(sim > cutoff)
        if exclude_signature_id is not None:
            stmt = stmt.where(FailureSignature.id != exclude_signature_id)
        rows = session.execute(stmt.order_by(sim.desc()).limit(max(k * 2, k))).all()
        scored = [(s, float(score)) for s, score in rows]
    else:
        scored = []
        for s in session.scalars(select(FailureSignature)).all():
            if exclude_signature_id is not None and s.id == exclude_signature_id:
                continue
            ratio = SequenceMatcher(None, normalized_text, s.normalized_text).ratio()
            if ratio > cutoff:
                scored.append((s, ratio))
        scored.sort(key=lambda t: t[1], reverse=True)

    cases = [_to_case(session, s, score) for s, score in scored]
    cases.sort(key=lambda c: (c.similarity, c.provenance_weight), reverse=True)
    return cases[:k]
