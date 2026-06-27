"""Persist failure signatures at ingest and link results to them (PLAN §4).

For every **failing** result in a run we compute its normalized signature (``kb.signature``), upsert
a :class:`~uta.models.kb.FailureSignature` keyed by hash, and set ``result.signature_id``. Across
runs these links ARE the recurrence history; the signature's ``occurrence_count`` / first/last-seen
are then **recomputed from the linked results** so a re-ingest (which clears and re-adds a run's
results) never double-counts. Failing tests per run are few (dozens, not the full ~25k), so the
per-run signature work is cheap.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.signature import compute_hash, normalize
from uta.models import FailureSignature, Run, TestResult


def _recompute_aggregates(session: Session, signature: FailureSignature) -> None:
    """Refresh occurrence_count + first/last-seen from the results currently linked (idempotent)."""
    row = session.execute(
        select(
            func.count(TestResult.id),
            func.min(Run.started_at),
            func.max(Run.started_at),
            func.min(Run.id),
            func.max(Run.id),
        )
        .join(Run, Run.id == TestResult.run_id)
        .where(TestResult.signature_id == signature.id)
    ).one()
    count, first_at, last_at, first_run, last_run = row
    signature.occurrence_count = count or 0
    signature.first_seen_at = first_at
    signature.last_seen_at = last_at
    signature.first_seen_run_id = first_run
    signature.last_seen_run_id = last_run


def record_signatures_for_run(session: Session, run: Run) -> int:
    """Compute, upsert and link a signature for every failing result in ``run``.

    Returns the number of failing results signed. Must run after the run's results are flushed (they
    need ids). Idempotent on re-ingest: the run's results were replaced, so we just re-link and
    recompute the affected signatures' aggregates.
    """
    failing = [r for r in run.results if r.status in FAILED_STATUSES]
    cache: dict[str, FailureSignature] = {}
    affected: set[int] = set()
    signed = 0

    for result in failing:
        sig = normalize(result.error_details, result.error_stack_trace)
        if sig is None:
            result.signature_id = None
            continue
        identity_name = result.identity.canonical_name
        sig_hash = compute_hash(identity_name, sig.text)

        signature = cache.get(sig_hash)
        if signature is None:
            signature = session.scalar(
                select(FailureSignature).where(FailureSignature.signature_hash == sig_hash)
            )
            if signature is None:
                signature = FailureSignature(
                    test_identity_id=result.test_identity_id,
                    normalized_text=sig.text,
                    signature_hash=sig_hash,
                    exception_type=sig.exception_type,
                    occurrence_count=0,
                )
                session.add(signature)
                session.flush()  # need the id to link results
            cache[sig_hash] = signature

        result.signature = signature
        affected.add(signature.id)
        signed += 1

    session.flush()  # links visible before aggregate recompute
    for sig_id in affected:
        _recompute_aggregates(session, session.get(FailureSignature, sig_id))
    return signed
