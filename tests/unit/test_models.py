"""Unit tests for the Milestone 1 Information model (SQLite, fully offline)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from uta.db import Base, make_engine, make_session_factory, session_scope
from uta.models import (
    CAUSE_CODE_CHANGE,
    EPISODE_OPEN,
    LIFECYCLE_FAILING,
    LIFECYCLE_FIXED,
    LIFECYCLE_REMOVED,
    PROVENANCE_HUMAN_ENTERED,
    SIGNAL_SVN_COMMIT,
    TRIAGE_UNTRIAGED,
    FailureEpisode,
    KbSignature,
    Run,
    RunShard,
    RunSignal,
    TestClassification,
    TestIdentity,
    TestLifecycle,
    TestResult,
)


@pytest.fixture
def sf():
    """In-memory SQLite session factory with the full M1 schema."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def _now() -> datetime:
    return datetime(2026, 6, 27, 10, 0, tzinfo=UTC)


def _run(build: int = 1) -> Run:
    t = _now()
    return Run(build_number=build, status="SUCCESS", started_at=t, finished_at=t, complete=True)


def _identity(test_id: str = "pkg.Cls.test_foo") -> TestIdentity:
    parts = test_id.rsplit(".", 1)
    return TestIdentity(test_id=test_id, class_name=parts[0], method=parts[1])


# ── Basic creation ────────────────────────────────────────────────────────────


def test_create_all_succeeds(sf):
    """create_all must raise no error — proves all table DDL is valid SQL."""
    with session_scope(sf) as s:
        # insert a run just to confirm tables exist and are writable
        s.add(_run())
    with session_scope(sf) as s:
        assert s.scalar(select(func.count()).select_from(Run)) == 1


def test_run_shard(sf):
    t = _now()
    with session_scope(sf) as s:
        run = _run()
        s.add(run)
        s.flush()
        s.add(
            RunShard(
                run_id=run.id,
                track="permanent",
                status="SUCCESS",
                started_at=t,
                finished_at=t,
            )
        )
    with session_scope(sf) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1))
        assert len(run.shards) == 1
        assert run.shards[0].track == "permanent"


def test_run_shard_unique_constraint(sf):
    """Inserting the same track twice for a run must violate the unique constraint."""
    from sqlalchemy.exc import IntegrityError

    now = _now()
    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            run = _run()
            s.add(run)
            s.flush()
            s.add(
                RunShard(
                    run_id=run.id,
                    track="permanent",
                    status="SUCCESS",
                    started_at=now,
                    finished_at=now,
                )
            )
            s.add(
                RunShard(
                    run_id=run.id,
                    track="permanent",
                    status="FAILED",
                    started_at=now,
                    finished_at=now,
                )
            )


def test_test_identity_unique(sf):
    """test_identity.test_id must be unique."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            s.add(_identity("pkg.Cls.test_foo"))
            s.add(_identity("pkg.Cls.test_foo"))


def test_test_identity_alias(sf):
    with session_scope(sf) as s:
        canonical = _identity("pkg.OldCls.test_foo")
        alias = _identity("pkg.NewCls.test_foo")
        s.add(canonical)
        s.flush()
        alias.alias_of_id = canonical.id
        alias.alias_confirmed = True
        s.add(alias)
    with session_scope(sf) as s:
        alias = s.scalar(select(TestIdentity).where(TestIdentity.test_id == "pkg.NewCls.test_foo"))
        assert alias.alias_of_id is not None
        assert alias.alias_confirmed is True


def test_test_result_with_identity_fk(sf):
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        s.add(
            TestResult(
                run_id=run.id,
                test_id=ident.test_id,
                test_identity_id=ident.id,
                track="permanent",
                status="FAILED",
                error_details="AssertionError",
                error_stack_trace="Traceback...\n  File test_foo.py:42",
            )
        )
    with session_scope(sf) as s:
        result = s.scalar(select(TestResult))
        assert result.test_identity_id is not None
        assert result.error_stack_trace is not None


def test_test_result_without_identity_fk(sf):
    """test_identity_id is nullable — Slice 0 ingest still works without it."""
    with session_scope(sf) as s:
        run = _run()
        s.add(run)
        s.flush()
        s.add(
            TestResult(
                run_id=run.id, test_id="pkg.Cls.test_foo", track="permanent", status="PASSED"
            )
        )
    with session_scope(sf) as s:
        r = s.scalar(select(TestResult))
        assert r.test_identity_id is None


def test_lifecycle(sf):
    with session_scope(sf) as s:
        ident = _identity()
        s.add(ident)
        s.flush()
        s.add(
            TestLifecycle(
                test_identity_id=ident.id,
                state=LIFECYCLE_FAILING,
                flaky=False,
                reopen_count=0,
            )
        )
    with session_scope(sf) as s:
        lc = s.scalar(select(TestLifecycle))
        assert lc.state == LIFECYCLE_FAILING
        assert lc.acknowledged is False
        assert lc.reopen_count == 0


def test_lifecycle_unique_per_identity(sf):
    """One lifecycle row per identity — second insert must fail."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            ident = _identity()
            s.add(ident)
            s.flush()
            s.add(TestLifecycle(test_identity_id=ident.id, state=LIFECYCLE_FAILING))
            s.add(TestLifecycle(test_identity_id=ident.id, state=LIFECYCLE_FIXED))


def test_failure_episode(sf):
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        s.add(
            FailureEpisode(
                test_identity_id=ident.id,
                episode_number=1,
                first_failure_run_id=run.id,
                state=EPISODE_OPEN,
                triage_status=TRIAGE_UNTRIAGED,
            )
        )
    with session_scope(sf) as s:
        ep = s.scalar(select(FailureEpisode))
        assert ep.episode_number == 1
        assert ep.state == EPISODE_OPEN
        assert ep.fixed_in_run_id is None


def test_failure_episode_with_attribution(sf):
    t = _now()
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        s.add(
            FailureEpisode(
                test_identity_id=ident.id,
                episode_number=1,
                first_failure_run_id=run.id,
                cause=CAUSE_CODE_CHANGE,
                reason="Rev 12345 broke the DB connection pool",
                provenance=PROVENANCE_HUMAN_ENTERED,
                causing_person="alice",
                confirmed_by="alice",
                confirmed_at=t,
            )
        )
    with session_scope(sf) as s:
        ep = s.scalar(select(FailureEpisode))
        assert ep.cause == CAUSE_CODE_CHANGE
        assert ep.provenance == PROVENANCE_HUMAN_ENTERED
        assert ep.causing_person == "alice"


def test_failure_episode_unique_per_test(sf):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            run = _run()
            ident = _identity()
            s.add(run)
            s.add(ident)
            s.flush()
            s.add(
                FailureEpisode(
                    test_identity_id=ident.id, episode_number=1, first_failure_run_id=run.id
                )
            )
            s.add(
                FailureEpisode(
                    test_identity_id=ident.id, episode_number=1, first_failure_run_id=run.id
                )
            )


def test_run_signal(sf):
    t = _now()
    with session_scope(sf) as s:
        run = _run()
        s.add(run)
        s.flush()
        s.add(
            RunSignal(
                run_id=run.id,
                signal_type=SIGNAL_SVN_COMMIT,
                occurred_at=t,
                author="alice",
                description="Rev 12345: fix connection pool",
                details={"paths": ["/trunk/web_modules/foo.py"], "revision": "12345"},
            )
        )
    with session_scope(sf) as s:
        sig = s.scalar(select(RunSignal))
        assert sig.signal_type == SIGNAL_SVN_COMMIT
        assert sig.details["revision"] == "12345"


def test_test_classification(sf):
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        s.add(
            TestClassification(
                run_id=run.id,
                test_identity_id=ident.id,
                predicted_cause=CAUSE_CODE_CHANGE,
                suggested_contact="alice",
            )
        )
    with session_scope(sf) as s:
        tc = s.scalar(select(TestClassification))
        assert tc.predicted_cause == CAUSE_CODE_CHANGE


def test_test_classification_unique(sf):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            run = _run()
            ident = _identity()
            s.add(run)
            s.add(ident)
            s.flush()
            s.add(
                TestClassification(
                    run_id=run.id, test_identity_id=ident.id, predicted_cause="CODE_CHANGE"
                )
            )
            s.add(
                TestClassification(
                    run_id=run.id, test_identity_id=ident.id, predicted_cause="UNKNOWN"
                )
            )


def test_kb_signature(sf):
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        ep = FailureEpisode(
            test_identity_id=ident.id,
            episode_number=1,
            first_failure_run_id=run.id,
        )
        s.add(ep)
        s.flush()
        s.add(
            KbSignature(
                sig_hash="abc123",
                sig_text="AssertionError: expected <NUM> but got <NUM>",
                test_identity_id=ident.id,
                episode_id=ep.id,
                confirmed_cause=CAUSE_CODE_CHANGE,
                confirmed_reason="Rev 12345 broke comparison",
                provenance=PROVENANCE_HUMAN_ENTERED,
            )
        )
    with session_scope(sf) as s:
        kb = s.scalar(select(KbSignature))
        assert kb.sig_hash == "abc123"
        assert kb.confirmed_cause == CAUSE_CODE_CHANGE


def test_kb_signature_hash_unique(sf):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with session_scope(sf) as s:
            ident = _identity()
            s.add(ident)
            s.flush()
            s.add(KbSignature(sig_hash="dup", sig_text="err 1", test_identity_id=ident.id))
            s.add(KbSignature(sig_hash="dup", sig_text="err 2", test_identity_id=ident.id))


def test_baseline_run_self_reference(sf):
    """Run.baseline_run_id is a nullable self-FK."""
    now = _now()
    with session_scope(sf) as s:
        prev = Run(build_number=1, status="SUCCESS", started_at=now, finished_at=now, complete=True)
        s.add(prev)
        s.flush()
        curr = Run(
            build_number=2,
            status="SUCCESS",
            started_at=now,
            finished_at=now,
            complete=True,
            baseline_run_id=prev.id,
        )
        s.add(curr)
    with session_scope(sf) as s:
        curr = s.scalar(select(Run).where(Run.build_number == 2))
        assert curr.baseline_run_id is not None


def test_lifecycle_state_transitions(sf):
    """Manually step through FAILING → FIXED → FAILING to verify reopen logic."""
    with session_scope(sf) as s:
        run = _run()
        ident = _identity()
        s.add(run)
        s.add(ident)
        s.flush()
        lc = TestLifecycle(test_identity_id=ident.id, state=LIFECYCLE_FAILING)
        s.add(lc)
    with session_scope(sf) as s:
        lc = s.scalar(select(TestLifecycle))
        lc.state = LIFECYCLE_FIXED
    with session_scope(sf) as s:
        lc = s.scalar(select(TestLifecycle))
        assert lc.state == LIFECYCLE_FIXED
        # reopen: clear acknowledgement, increment counter
        lc.state = LIFECYCLE_FAILING
        lc.reopen_count += 1
        lc.acknowledged = False
        lc.acknowledged_by = None
        lc.acknowledged_at = None
    with session_scope(sf) as s:
        lc = s.scalar(select(TestLifecycle))
        assert lc.state == LIFECYCLE_FAILING
        assert lc.reopen_count == 1
        assert lc.acknowledged is False


def test_all_lifecycle_states(sf):
    for state in (LIFECYCLE_FAILING, LIFECYCLE_FIXED, LIFECYCLE_REMOVED):
        with session_scope(sf) as s:
            ident = _identity(f"pkg.Cls.test_{state}")
            s.add(ident)
            s.flush()
            s.add(TestLifecycle(test_identity_id=ident.id, state=state))
        with session_scope(sf) as s:
            lc = s.scalar(
                select(TestLifecycle)
                .join(TestIdentity)
                .where(TestIdentity.test_id == f"pkg.Cls.test_{state}")
            )
            assert lc.state == state
