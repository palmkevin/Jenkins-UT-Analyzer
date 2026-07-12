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


def test_human_entered_cause_outranks_unconfirmed_ai_reason(session_factory):
    """A triager may validate only *who* caused it — that's human knowledge (issue #126).

    ``cause_provenance=HUMAN_ENTERED`` with ``reason_provenance`` still at its AI_UNCONFIRMED
    default must rank above an unconfirmed AI reason on equal text similarity and carry the
    human provenance label — not weight 0 from reading ``reason_provenance`` alone.
    """
    with session_factory() as s:
        _fail_run(s, 1, name="ut_ar.arinv_csvc.test_a", msg="zzz")
        _fail_run(s, 2, name="ut_ar.arinv_csvc.test_b", msg="zzz")
        _fail_run(s, 3, name="ut_ar.arinv_csvc.test_c", msg="zzz")
        s.commit()
        sig = {
            t: s.scalar(
                select(FailureSignature).where(
                    FailureSignature.test_identity_id
                    == get_identity(s, f"ut_ar.arinv_csvc.test_{t}").id
                )
            )
            for t in ("a", "b", "c")
        }
        # B: the set-attribution path with only causing_person filled — cause becomes
        # HUMAN_ENTERED while reason_provenance keeps its AI_UNCONFIRMED default.
        s.add(
            Attribution(
                episode_id=1,
                signature_id=sig["b"].id,
                causing_person="ako",
                cause_provenance=Provenance.HUMAN_ENTERED,
            )
        )
        # C: an unconfirmed AI reason only.
        s.add(
            Attribution(
                episode_id=2,
                signature_id=sig["c"].id,
                reason_text="maybe a fee rounding change",
                reason_provenance=Provenance.AI_UNCONFIRMED,
            )
        )
        s.commit()
        cases = similar_cases(
            s, sig["a"].normalized_text, k=5, cutoff=0.1, exclude_signature_id=sig["a"].id
        )
        b_case = next(c for c in cases if c.signature_id == sig["b"].id)
        c_case = next(c for c in cases if c.signature_id == sig["c"].id)
        assert b_case.provenance == Provenance.HUMAN_ENTERED
        assert b_case.provenance_weight == 3
        assert b_case.causing_person == "ako"
        assert c_case.provenance_weight == 0
        # Same normalized text → equal similarity; the human-entered cause must win the tie.
        assert b_case.similarity == c_case.similarity
        assert cases.index(b_case) < cases.index(c_case)
