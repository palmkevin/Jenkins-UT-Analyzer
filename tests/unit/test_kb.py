"""Knowledge base: signature store + retrieval.

Covers the offline (SQLite/difflib) path of the recurrence engine: upsert + idempotent occurrence
counting, exact recurrence by hash, fuzzy similar-case retrieval, and provenance weighting.
"""

from __future__ import annotations

from sqlalchemy import select

from tests.builders import get_identity, make_run
from uta.kb.retrieval import exact_recurrence, similar_cases
from uta.kb.signature import normalize
from uta.kb.store import record_signatures_for_run
from uta.models import Attribution, FailureSignature
from uta.models.enums import Provenance

_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_ar/arinv_csvc.py", line {line}, in test_x\n'
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)
T = "ut_ar.arinv_csvc.test_x"


def _fail_run(session, build, name=T, line=92, msg="1 != 2"):
    run = make_run(
        session,
        build,
        {name: "FAILED"},
        errors={name: ("test failure", _STACK.format(line=line, msg=msg))},
    )
    record_signatures_for_run(session, run)
    return run


def test_signature_created_and_linked(session_factory):
    with session_factory() as s:
        run = _fail_run(s, 1)
        s.commit()
        sigs = s.scalars(select(FailureSignature)).all()
        assert len(sigs) == 1
        assert sigs[0].occurrence_count == 2  # one per track
        for r in run.results:
            assert r.signature_id == sigs[0].id


def test_recurrence_same_bug_across_runs(session_factory):
    with session_factory() as s:
        _fail_run(s, 1, line=92, msg="1 != 2")
        _fail_run(s, 2, line=99, msg="5 != 9")  # same bug, different run noise
        s.commit()
        sigs = s.scalars(select(FailureSignature)).all()
        assert len(sigs) == 1  # collapsed under one signature
        assert sigs[0].occurrence_count == 4  # 2 runs × 2 tracks
        assert sigs[0].first_seen_run_id != sigs[0].last_seen_run_id


def test_reingest_does_not_double_count(session_factory):
    """Re-ingest clears+rebuilds a run's results; occurrence is recomputed, never inflated."""
    from uta.models import Run, TestResult

    with session_factory() as s:
        _fail_run(s, 1)
        s.commit()
    with session_factory() as s:
        run = s.scalar(select(Run).where(Run.build_number == 1))
        run.results.clear()  # the pipeline's idempotent re-ingest path
        s.flush()
        ident = get_identity(s, T)
        for track in ("permanent", "permanent_py39"):
            run.results.append(
                TestResult(
                    identity=ident,
                    track=track,
                    status="FAILED",
                    error_details="test failure",
                    error_stack_trace=_STACK.format(line=92, msg="x"),
                )
            )
        s.flush()
        record_signatures_for_run(s, run)
        s.commit()
        sig = s.scalar(select(FailureSignature))
        assert sig.occurrence_count == 2  # not 4 — recomputed from the live links


def test_reingest_with_changed_error_text_resets_the_orphaned_signature(session_factory):
    """Changed failure text hashes to a NEW signature; the old one — linked only via the deleted
    rows — is recomputed through ``stale_signature_ids`` (the pipeline's pre-delete capture) and
    gets the documented zero/empty reset instead of staying permanently stale."""
    from uta.models import Run, TestResult

    value_stack = (
        "Traceback (most recent call last):\n"
        '  File "/opt/ls/lx/release/permanent/tests/dev/ut_ar/arinv_csvc.py", line 92, in test_x\n'
        "    parse(x)\n"
        "ValueError: bad literal\n"
    )
    with session_factory() as s:
        _fail_run(s, 1)
        s.commit()
    with session_factory() as s:
        run = s.scalar(select(Run).where(Run.build_number == 1))
        # The pipeline's idempotent re-ingest path: capture the old links, then clear + rebuild
        # with a different failure (ValueError instead of AssertionError → different hash).
        stale = set(
            s.scalars(
                select(TestResult.signature_id.distinct()).where(
                    TestResult.run_id == run.id, TestResult.signature_id.is_not(None)
                )
            )
        )
        run.results.clear()
        s.flush()
        ident = get_identity(s, T)
        for track in ("permanent", "permanent_py39"):
            run.results.append(
                TestResult(
                    identity=ident,
                    track=track,
                    status="FAILED",
                    error_details="test failure",
                    error_stack_trace=value_stack,
                )
            )
        s.flush()
        record_signatures_for_run(s, run, stale_signature_ids=stale)
        s.commit()
        by_exc = {
            sig.exception_type: sig for sig in s.scalars(select(FailureSignature)).all()
        }
        assert set(by_exc) == {"AssertionError", "ValueError"}
        old, new = by_exc["AssertionError"], by_exc["ValueError"]
        assert old.occurrence_count == 0  # orphaned → the documented zero/empty reset
        assert old.first_seen_at is None and old.last_seen_at is None
        assert old.first_seen_run_id is None and old.last_seen_run_id is None
        assert new.occurrence_count == 2
        assert new.last_seen_run_id == run.id


def test_first_last_seen_run_ids_follow_started_at_not_run_id(session_factory):
    """A historical re-ingest gives an OLDER build a HIGHER run id (quarantine recovery); the
    first/last-seen run ids must belong to the runs with min/max ``started_at``, never min/max
    run id."""
    from uta.models import Run

    with session_factory() as s:
        newer = _fail_run(s, 105)  # ingested first → lower run id, later started_at
        older = _fail_run(s, 104)  # recovered later → higher run id, earlier started_at
        s.commit()
        assert older.id > newer.id and older.started_at < newer.started_at  # the premise
        sig = s.scalar(select(FailureSignature))
        # Compare against DB-round-tripped values (SQLite drops tzinfo on the way through).
        started = dict(s.execute(select(Run.id, Run.started_at)).all())
        assert sig.first_seen_run_id == older.id
        assert sig.first_seen_at == started[older.id]
        assert sig.last_seen_run_id == newer.id
        assert sig.last_seen_at == started[newer.id]


def test_exact_recurrence_lookup(session_factory):
    with session_factory() as s:
        _fail_run(s, 1)
        s.commit()
        # Same bug, fresh run noise (different line + assertion values) → same normalized signature.
        sig = normalize("test failure", _STACK.format(line=305, msg="7 != 8"))
        found = exact_recurrence(s, T, sig)
        assert found is not None
        # A different test with the same text is a different signature.
        assert exact_recurrence(s, "other.test", sig) is None


def test_similar_cases_offline_difflib(session_factory):
    with session_factory() as s:
        _fail_run(s, 1, name="ut_ar.arinv_csvc.test_x", msg="aaa")
        _fail_run(s, 2, name="ut_ar.arinv_csvc.test_y", msg="bbb")  # near-identical text
        s.commit()
        sig = s.scalar(
            select(FailureSignature).where(
                FailureSignature.test_identity_id == get_identity(s, "ut_ar.arinv_csvc.test_x").id
            )
        )
        cases = similar_cases(s, sig.normalized_text, k=5, cutoff=0.3, exclude_signature_id=sig.id)
        assert any(c.test_id == "ut_ar.arinv_csvc.test_y" for c in cases)


def test_provenance_weighting_orders_confirmed_first(session_factory):
    with session_factory() as s:
        _fail_run(s, 1, name="ut_ar.arinv_csvc.test_a", msg="zzz")
        _fail_run(s, 2, name="ut_ar.arinv_csvc.test_b", msg="zzz")
        s.commit()
        a = get_identity(s, "ut_ar.arinv_csvc.test_a")
        b = get_identity(s, "ut_ar.arinv_csvc.test_b")
        sig_a = s.scalar(select(FailureSignature).where(FailureSignature.test_identity_id == a.id))
        sig_b = s.scalar(select(FailureSignature).where(FailureSignature.test_identity_id == b.id))
        # Attach a strong human-entered reason to B's signature only (episode FK is irrelevant to
        # the KB read and unenforced on SQLite — the retrieval keys on signature_id).
        s.add(
            Attribution(
                episode_id=1,
                signature_id=sig_b.id,
                reason_text="off-by-one in reminder fee",
                causing_person="ako",
                reason_provenance=Provenance.HUMAN_ENTERED,
            )
        )
        s.commit()
        cases = similar_cases(
            s, sig_a.normalized_text, k=5, cutoff=0.1, exclude_signature_id=sig_a.id
        )
        match = next(c for c in cases if c.signature_id == sig_b.id)
        assert match.reason_text == "off-by-one in reminder fee"
        assert match.provenance_weight == 3
