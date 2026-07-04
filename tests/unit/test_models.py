"""Offline schema tests for the full Information model (SQLite in-memory, no Postgres).

Exercises the relationships, constraints and defaults that the migration must preserve. Postgres-
only concerns (pg_trgm, the GIN index, the real migration) live in ``test_migrations.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError

from uta.db import Base, make_session_factory, session_scope
from uta.models import (
    Attribution,
    Classification,
    CodeChangeCandidate,
    DataChangeCandidate,
    FailureEpisode,
    FailureSignature,
    LifecycleState,
    PredictedCause,
    Provenance,
    Run,
    RunShard,
    TestIdentity,
    TestLifecycle,
    TestResult,
    TriageStatus,
)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def _utc() -> datetime:
    return datetime(2026, 6, 27, 17, 0, tzinfo=UTC)


def _run(build: int = 1) -> Run:
    return Run(build_number=build, status="SUCCESS", started_at=_utc(), finished_at=_utc())


def test_full_graph_persists_and_reloads(session_factory):
    """A run + identity + result + lifecycle + episode + attribution + classification + signals."""
    with session_scope(session_factory) as s:
        run = _run()
        ident = TestIdentity(
            canonical_name="ut_acc.ac.TestC.test_x", class_name="ut_acc.ac.TestC", method="test_x"
        )
        s.add_all([run, ident])
        s.flush()

        sig = FailureSignature(
            test_identity_id=ident.id,
            normalized_text="expected <NUM> but was <NUM>",
            signature_hash="hash-abc",
            exception_type="AssertionError",
        )
        s.add(sig)
        s.flush()

        run.shards.append(RunShard(track="permanent", status="SUCCESS", started_at=_utc()))
        run.results.append(
            TestResult(identity=ident, track="permanent", status="FAILED", signature=sig)
        )
        run.code_changes.append(
            CodeChangeCandidate(commit_id="r123", author="alice", committed_at=_utc())
        )
        run.data_changes.append(
            DataChangeCandidate(lx_table_code="BFLOG", change_type="U", changed_at=_utc())
        )

        ep = FailureEpisode(
            identity=ident,
            episode_number=1,
            first_failure_run_id=run.id,
            first_failure_at=_utc(),
        )
        s.add(ep)
        s.flush()
        ep.attribution = Attribution(reason_text="bad fixture")
        ep.classifications.append(Classification(predicted_cause=PredictedCause.DATA_CHANGE))
        lc = TestLifecycle(identity=ident)
        s.add(lc)
        s.flush()
        lc.current_episode = ep

    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1))
        assert len(run.shards) == 1
        assert len(run.code_changes) == 1 and len(run.data_changes) == 1
        result = run.results[0]
        assert result.identity.canonical_name == "ut_acc.ac.TestC.test_x"
        assert result.signature.signature_hash == "hash-abc"
        ident = result.identity
        assert ident.lifecycle.current_episode.episode_number == 1
        assert ident.episodes[0].attribution.reason_text == "bad fixture"
        assert ident.episodes[0].classifications[0].predicted_cause == "DATA_CHANGE"


def test_defaults_match_design(session_factory):
    """Lifecycle/triage/provenance defaults and the deferred (null) confidence."""
    with session_scope(session_factory) as s:
        run, ident = _run(), TestIdentity(canonical_name="a.B.t")
        s.add_all([run, ident])
        s.flush()
        ep = FailureEpisode(
            identity=ident, episode_number=1, first_failure_run_id=run.id, first_failure_at=_utc()
        )
        s.add_all([ep, TestLifecycle(identity=ident)])
        s.flush()
        s.add_all([Attribution(episode_id=ep.id), Classification(episode_id=ep.id)])

    with session_scope(session_factory) as s:
        lc = s.scalar(select(TestLifecycle))
        assert lc.state == LifecycleState.FAILING
        assert lc.flaky is False and lc.acknowledged is False and lc.reopen_count == 0
        ep = s.scalar(select(FailureEpisode))
        assert ep.triage_status == TriageStatus.UNTRIAGED and ep.is_open is True
        attr = s.scalar(select(Attribution))
        assert attr.cause_provenance == Provenance.AI_UNCONFIRMED
        assert attr.reason_provenance == Provenance.AI_UNCONFIRMED
        cls = s.scalar(select(Classification))
        assert cls.predicted_cause == PredictedCause.UNKNOWN
        assert cls.confidence is None  # deferred per design


def test_unique_run_test_track(session_factory):
    """The (run, test, track) identity key is enforced."""
    with session_scope(session_factory) as s:
        run, ident = _run(), TestIdentity(canonical_name="a.B.t")
        s.add_all([run, ident])
        s.flush()
        s.add(TestResult(run=run, identity=ident, track="permanent", status="FAILED"))
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as s:
            run = s.scalar(select(Run))
            ident = s.scalar(select(TestIdentity))
            s.add(
                TestResult(
                    run_id=run.id, test_identity_id=ident.id, track="permanent", status="FAILED"
                )
            )


def test_same_test_both_tracks_allowed(session_factory):
    """The same test in both tracks is two distinct results, not a clash."""
    with session_scope(session_factory) as s:
        run, ident = _run(), TestIdentity(canonical_name="a.B.t")
        s.add_all([run, ident])
        s.flush()
        s.add_all(
            [
                TestResult(run=run, identity=ident, track="permanent", status="FAILED"),
                TestResult(run=run, identity=ident, track="permanent_py39", status="FAILED"),
            ]
        )
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(TestResult)) == 2


def test_episode_number_unique_per_identity(session_factory):
    with session_scope(session_factory) as s:
        run, ident = _run(), TestIdentity(canonical_name="a.B.t")
        s.add_all([run, ident])
        s.flush()
        s.add(
            FailureEpisode(
                identity=ident,
                episode_number=1,
                first_failure_run_id=run.id,
                first_failure_at=_utc(),
            )
        )
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as s:
            run = s.scalar(select(Run))
            ident = s.scalar(select(TestIdentity))
            s.add(
                FailureEpisode(
                    test_identity_id=ident.id,
                    episode_number=1,
                    first_failure_run_id=run.id,
                    first_failure_at=_utc(),
                )
            )


def test_signature_hash_unique(session_factory):
    with session_scope(session_factory) as s:
        ident = TestIdentity(canonical_name="a.B.t")
        s.add(ident)
        s.flush()
        s.add(
            FailureSignature(test_identity_id=ident.id, normalized_text="x", signature_hash="dup")
        )
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as s:
            ident = s.scalar(select(TestIdentity))
            s.add(
                FailureSignature(
                    test_identity_id=ident.id, normalized_text="y", signature_hash="dup"
                )
            )


def test_identity_alias_self_reference(session_factory):
    """A renamed test points at its canonical identity so history can follow the pointer."""
    with session_scope(session_factory) as s:
        old = TestIdentity(canonical_name="a.Old.t")
        s.add(old)
        s.flush()
        s.add(TestIdentity(canonical_name="a.New.t", alias_of_id=old.id, alias_state="CONFIRMED"))
    with session_scope(session_factory) as s:
        new = s.scalar(select(TestIdentity).where(TestIdentity.canonical_name == "a.New.t"))
        assert new.alias_of.canonical_name == "a.Old.t"


def test_failure_history_is_results_across_runs(session_factory):
    """Failure history = test_results across runs, no separate table."""
    with session_scope(session_factory) as s:
        ident = TestIdentity(canonical_name="a.B.t")
        s.add(ident)
        s.flush()
        for build, status in [(1, "FAILED"), (2, "PASSED"), (3, "FAILED")]:
            run = _run(build)
            s.add(run)
            s.flush()
            s.add(TestResult(run=run, identity=ident, track="permanent", status=status))
    with session_scope(session_factory) as s:
        ident = s.scalar(select(TestIdentity))
        fails = s.scalar(
            select(func.count())
            .select_from(TestResult)
            .where(TestResult.test_identity_id == ident.id, TestResult.status == "FAILED")
        )
        assert fails == 2


def test_run_cascade_deletes_children(session_factory):
    with session_scope(session_factory) as s:
        run, ident = _run(), TestIdentity(canonical_name="a.B.t")
        s.add_all([run, ident])
        s.flush()
        run.results.append(TestResult(identity=ident, track="permanent", status="FAILED"))
        run.shards.append(RunShard(track="permanent", status="SUCCESS"))
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run))
        s.delete(run)
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(TestResult)) == 0
        assert s.scalar(select(func.count()).select_from(RunShard)) == 0
        # The identity is independent of any single run — it survives.
        assert s.scalar(select(func.count()).select_from(TestIdentity)) == 1
