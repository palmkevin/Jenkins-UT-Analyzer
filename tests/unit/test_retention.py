"""Retention pruning (issue #52): old passing results and finished ingest jobs.

The load-bearing guarantee: pruning must never disturb the long-term record — KB signature
occurrence counts (recomputed from *linked* results), episode history, lifecycles and builds all
survive; only old passing/skipped raw rows (and finished ingest jobs) go.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from tests.builders import get_identity, make_build
from tests.unit.test_poller import _MultiBuildFake
from uta.analyze.lifecycle import apply_build
from uta.config import Settings
from uta.control.heartbeat import read_heartbeat
from uta.db import session_scope
from uta.kb.store import record_signatures_for_build
from uta.models import Build, FailureEpisode, FailureSignature, IngestJob, TestResult
from uta.models.enums import IngestJobStatus
from uta.poller import poll_tick
from uta.retention import prune, prune_ingest_jobs, prune_passing_results
from uta.web import views

_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
_OLD = _NOW - timedelta(days=120)  # outside the 90-day default window
_RECENT = _NOW - timedelta(days=5)


def _result_count(session, **filters) -> int:
    query = select(func.count()).select_from(TestResult)
    for attr, value in filters.items():
        query = query.where(getattr(TestResult, attr) == value)
    return session.scalar(query)


def test_prune_drops_only_old_passing_results(session_factory):
    with session_scope(session_factory) as s:
        old = make_build(
            s, 1, {"pass": "PASSED", "skip": "SKIPPED", "fail": "FAILED"}, started_at=_OLD
        )
        recent = make_build(s, 2, {"pass": "PASSED", "fail": "FAILED"}, started_at=_RECENT)
        deleted = prune_passing_results(s, retention_days=90, now=_NOW)
        # Old build: PASSED + SKIPPED rows go (2 tests × 2 tracks); its FAILED rows stay.
        assert deleted == 4
        assert _result_count(s, build_id=old.id) == 2
        assert _result_count(s, build_id=old.id, status="FAILED") == 2
        # Recent build: untouched.
        assert _result_count(s, build_id=recent.id) == 4
        # Builds themselves are never deleted.
        assert s.scalar(select(func.count()).select_from(Build)) == 2


def test_prune_is_idempotent_and_zero_disables(session_factory):
    with session_scope(session_factory) as s:
        make_build(s, 1, {"pass": "PASSED"}, started_at=_OLD)
        assert prune_passing_results(s, retention_days=0, now=_NOW) == 0  # disabled → keeps all
        assert prune_passing_results(s, retention_days=90, now=_NOW) == 2
        assert prune_passing_results(s, retention_days=90, now=_NOW) == 0  # second pass: no-op


def test_kb_occurrence_counts_survive_pruning(session_factory):
    """The acceptance check: pruning never corrupts the KB aggregates.

    Failing results are the KB's linked evidence; only unsigned passing rows are deleted, so the
    recomputed occurrence counts (kb/store recomputes from linked results) stay exact.
    """
    errors = {"fail": ("boom: values differ", "Traceback ...")}
    with session_scope(session_factory) as s:
        r1 = make_build(s, 1, {"fail": "FAILED", "pass": "PASSED"}, started_at=_OLD, errors=errors)
        record_signatures_for_build(s, r1)
        r2 = make_build(
            s,
            2,
            {"fail": "FAILED", "pass": "PASSED"},
            started_at=_OLD + timedelta(days=1),
            errors=errors,
        )
        record_signatures_for_build(s, r2)
        signature = s.scalar(select(FailureSignature))
        assert signature.occurrence_count == 4  # 2 builds × 2 tracks, same signature

        prune_passing_results(s, retention_days=90, now=_NOW)

        # Every signed (failing) row survives; the aggregate is untouched and still recomputable.
        signature = s.scalar(select(FailureSignature))
        assert signature.occurrence_count == 4
        linked = s.scalar(
            select(func.count())
            .select_from(TestResult)
            .where(TestResult.signature_id == signature.id)
        )
        assert linked == 4


def test_episode_history_survives_pruning(session_factory):
    """Episodes (and their failure detail) outlive the pruning of the era's passing rows."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s, 1, {"t": "FAILED", "pass": "PASSED"}, started_at=_OLD, errors={"t": ("kaboom", None)}
        )
        apply_build(s, r1, baseline=None)
        r2 = make_build(
            s, 2, {"t": "PASSED", "pass": "PASSED"}, started_at=_OLD + timedelta(days=1)
        )
        apply_build(s, r2, baseline=r1)

        prune_passing_results(s, retention_days=90, now=_NOW)

        episode = s.scalar(select(FailureEpisode))
        assert episode is not None and episode.is_open is False
        assert episode.fixed_in_build_id == r2.id  # the fix record survives its pruned pass rows
        record = views.test_record(s, get_identity(s, "t").id)
        assert record["lifecycle"]["state"] == "FIXED"
        assert len(record["episodes"]) == 1
        # The episode's failure detail still resolves — the failing row was kept.
        assert record["episodes"][0]["failure"]["error_details"] == "kaboom"


def _job(status: str, finished_at: datetime | None) -> IngestJob:
    return IngestJob(
        build_start=1, build_end=1, status=status, builds_total=1, finished_at=finished_at
    )


def test_prune_ingest_jobs_only_old_and_finished(session_factory):
    with session_scope(session_factory) as s:
        s.add(_job(IngestJobStatus.DONE, _OLD))  # old + finished → pruned
        s.add(_job(IngestJobStatus.ERROR, _OLD))  # old + finished → pruned
        s.add(_job(IngestJobStatus.DONE, _RECENT))  # recent → kept
        s.add(_job(IngestJobStatus.RUNNING, None))  # not finished → kept, whatever its age
        s.flush()
        assert prune_ingest_jobs(s, retention_days=0, now=_NOW) == 0  # disabled → keeps all
        assert prune_ingest_jobs(s, retention_days=30, now=_NOW) == 2
        remaining = set(s.scalars(select(IngestJob.status)).all())
        assert remaining == {IngestJobStatus.DONE, IngestJobStatus.RUNNING}


def test_prune_report_combines_both_passes(session_factory):
    with session_scope(session_factory) as s:
        make_build(s, 1, {"pass": "PASSED"}, started_at=_OLD)
        s.add(_job(IngestJobStatus.DONE, _OLD))
        s.flush()
        report = prune(s, result_retention_days=90, ingest_job_retention_days=30, now=_NOW)
        assert report.results_deleted == 2
        assert report.ingest_jobs_deleted == 1
        assert report.total == 3


def test_poll_tick_runs_the_retention_pass(session_factory):
    """The poller prunes every tick — even one that ingests nothing — and stays healthy."""
    with session_scope(session_factory) as s:
        make_build(s, 1, {"pass": "PASSED", "fail": "FAILED"}, started_at=_OLD)
        s.add(_job(IngestJobStatus.DONE, _OLD))

    settings = Settings(result_retention_days=90, ingest_job_retention_days=30)
    # last_completed == the already-ingested high-water mark ⇒ the tick ingests nothing.
    poll_tick(_MultiBuildFake(last_completed=1), session_factory, settings)

    with session_scope(session_factory) as s:
        assert _result_count(s, status="PASSED") == 0
        assert _result_count(s, status="FAILED") == 2
        assert s.scalar(select(func.count()).select_from(IngestJob)) == 0
        hb = read_heartbeat(s)
        assert hb is not None and hb.last_error is None
