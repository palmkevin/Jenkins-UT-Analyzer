"""Persist failure signatures at ingest and link results to them.

For every **failing** result in a run we compute its normalized signature (``kb.signature``), upsert
a :class:`~uta.models.kb.FailureSignature` keyed by hash, and set ``result.signature_id``. Across
runs these links ARE the recurrence history; the signature's ``occurrence_count`` / first/last-seen
are then **recomputed from the linked results** so a re-ingest (which clears and re-adds a run's
results) never double-counts. Failing tests per run are few (dozens, not the full ~25k), so the
per-run signature work is cheap.

The run's failing results are read via a query (result id, identity id, error text, canonical name)
rather than the ``run.results`` ORM collection, so this works after the pipeline bulk-inserts the
results with Core (which doesn't populate the collection). Signatures are preloaded/created in
batches, ``signature_id`` is written back with a batched UPDATE, and the affected signatures'
aggregates are recomputed in ONE grouped query.
"""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from uta.ingest.ut_report import FAILED_STATUSES
from uta.kb.signature import compute_hash, normalize
from uta.models import FailureSignature, Run, TestIdentity, TestResult

_HASH_CHUNK = 1000


def _recompute_aggregates_bulk(session: Session, signature_ids: set[int]) -> None:
    """Refresh occurrence_count + first/last-seen for all affected signatures in ONE grouped query.

    Signatures with no remaining linked results (a re-ingest whose failure content changed orphans
    them) are reset to a zero/empty aggregate. First/last-seen run ids are the runs holding the
    min/max ``started_at`` — NOT min/max run id, which diverges after a historical re-ingest (an
    older build recovered later gets a higher run id), so a plain per-column min/max can't be used.
    """
    if not signature_ids:
        return
    # Rank each signature's linked results by run start in both directions (run id breaks
    # started_at ties): the rank-1 rows carry the first/last-seen facts, count() the occurrences.
    ranked = (
        select(
            TestResult.signature_id.label("signature_id"),
            Run.id.label("run_id"),
            Run.started_at.label("started_at"),
            func.count().over(partition_by=TestResult.signature_id).label("count"),
            func.row_number()
            .over(
                partition_by=TestResult.signature_id,
                order_by=(Run.started_at.asc(), Run.id.asc()),
            )
            .label("first_rank"),
            func.row_number()
            .over(
                partition_by=TestResult.signature_id,
                order_by=(Run.started_at.desc(), Run.id.desc()),
            )
            .label("last_rank"),
        )
        .join(Run, Run.id == TestResult.run_id)
        .where(TestResult.signature_id.in_(signature_ids))
        .subquery()
    )
    aggregates: dict[int, list] = {}
    for row in session.execute(
        select(ranked).where((ranked.c.first_rank == 1) | (ranked.c.last_rank == 1))
    ):
        agg = aggregates.setdefault(row.signature_id, [row.count, None, None, None, None])
        if row.first_rank == 1:
            agg[1], agg[3] = row.started_at, row.run_id
        if row.last_rank == 1:
            agg[2], agg[4] = row.started_at, row.run_id
    for sig_id in signature_ids:
        signature = session.get(FailureSignature, sig_id)
        if signature is None:
            continue
        count, first_at, last_at, first_run, last_run = aggregates.get(
            sig_id, (0, None, None, None, None)
        )
        signature.occurrence_count = count or 0
        signature.first_seen_at = first_at
        signature.last_seen_at = last_at
        signature.first_seen_run_id = first_run
        signature.last_seen_run_id = last_run


def record_signatures_for_run(
    session: Session, run: Run, stale_signature_ids: set[int] | None = None
) -> int:
    """Compute, upsert and link a signature for every failing result in ``run``.

    Returns the number of failing results signed. Must run after the run's results are flushed (they
    need ids). Idempotent on re-ingest: the run's results were replaced, so we just re-link and
    recompute the affected signatures' aggregates. ``stale_signature_ids`` are the signatures the
    run's **old** results linked to (captured by the pipeline before its idempotent delete) — a
    signature whose failure vanished from the re-ingested content gains no new link, so it must be
    recomputed too or its aggregates stay permanently stale.
    """
    # Read the run's failing results (id + identity + error text + name) rather than run.results,
    # which a Core bulk insert leaves unpopulated.
    failing = session.execute(
        select(
            TestResult.id,
            TestResult.test_identity_id,
            TestResult.error_details,
            TestResult.error_stack_trace,
            TestIdentity.canonical_name,
        )
        .join(TestIdentity, TestIdentity.id == TestResult.test_identity_id)
        .where(TestResult.run_id == run.id, TestResult.status.in_(FAILED_STATUSES))
    ).all()

    # Compute each failing result's signature; collect the hashes so we can preload them in bulk.
    # rows: (result_id, identity_id, sig_text, sig_exception_type, sig_hash)
    rows: list[tuple[int, int, str, str | None, str]] = []
    unsigned_ids: list[int] = []
    for result_id, identity_id, error_details, error_stack_trace, canonical_name in failing:
        sig = normalize(error_details, error_stack_trace)
        if sig is None:
            unsigned_ids.append(result_id)
            continue
        sig_hash = compute_hash(canonical_name, sig.text)
        rows.append((result_id, identity_id, sig.text, sig.exception_type, sig_hash))

    # Preload existing signatures by hash (chunked to keep the IN list bounded).
    needed_hashes = {r[4] for r in rows}
    by_hash: dict[str, FailureSignature] = {}
    hash_list = list(needed_hashes)
    for start in range(0, len(hash_list), _HASH_CHUNK):
        chunk = hash_list[start : start + _HASH_CHUNK]
        for signature in session.scalars(
            select(FailureSignature).where(FailureSignature.signature_hash.in_(chunk))
        ).all():
            by_hash[signature.signature_hash] = signature

    # Create the missing signatures (first result to introduce a hash owns its identity_id).
    for _result_id, identity_id, sig_text, sig_exc, sig_hash in rows:
        if sig_hash not in by_hash:
            signature = FailureSignature(
                test_identity_id=identity_id,
                normalized_text=sig_text,
                signature_hash=sig_hash,
                exception_type=sig_exc,
                occurrence_count=0,
            )
            session.add(signature)
            by_hash[sig_hash] = signature
    session.flush()  # new signatures need ids before we link results

    # Batch the signature_id write-back: one UPDATE per (signature_id, [result_ids]) group, plus a
    # single clear for the results whose text didn't normalize to a signature.
    ids_per_signature: dict[int, list[int]] = {}
    affected: set[int] = set()
    for result_id, _identity_id, _sig_text, _sig_exc, sig_hash in rows:
        sig_id = by_hash[sig_hash].id
        ids_per_signature.setdefault(sig_id, []).append(result_id)
        affected.add(sig_id)

    # ``fetch`` synchronizes any TestResult objects already in the session's identity map (the
    # builder-driven KB tests read back ``result.signature_id`` off live ORM objects); the Core
    # bulk-inserted pipeline path has none loaded, so this stays a single UPDATE either way.
    if unsigned_ids:
        session.execute(
            update(TestResult).where(TestResult.id.in_(unsigned_ids)).values(signature_id=None)
        )
    for sig_id, result_ids in ids_per_signature.items():
        session.execute(
            update(TestResult).where(TestResult.id.in_(result_ids)).values(signature_id=sig_id)
        )

    session.flush()  # links visible before the grouped aggregate recompute

    # Core UPDATEs bypass the ORM identity map. Expire any TestResult instances already loaded in
    # this session (builder-driven callers read ``result.signature_id`` back) so the next access
    # reloads the just-written link; the Core bulk-insert pipeline path has none loaded, so this is
    # a no-op there.
    for result_id in (*unsigned_ids, *(rid for ids in ids_per_signature.values() for rid in ids)):
        obj = session.identity_map.get((TestResult, (result_id,), None))
        if obj is not None:
            session.expire(obj, ["signature_id"])

    _recompute_aggregates_bulk(session, affected | (stale_signature_ids or set()))
    return sum(len(ids) for ids in ids_per_signature.values())
