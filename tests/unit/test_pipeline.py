"""Slice-0 ingest pipeline against an in-memory SQLite DB (offline, no Postgres)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient, FakeTrackingFeed
from uta.db import session_scope
from uta.ingest.pipeline import data_change_window, ingest_build
from uta.models import (
    Classification,
    CodeChangeCandidate,
    DataChangeCandidate,
    FailureEpisode,
    Run,
    TestLifecycle,
    TestResult,
)
from uta.models.enums import LifecycleState, PredictedCause


def test_ingest_persists_run_and_results(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, expected_shards=2)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run is not None
        assert run.complete is True
        # Fixture has 14 cases across both tracks.
        n = s.scalar(select(func.count()).select_from(TestResult))
        assert n == 14
        tracks = set(s.scalars(select(TestResult.track)).all())
        assert tracks == {"permanent", "permanent_py39"}


def test_reingest_is_idempotent(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(Run)) == 1
        assert s.scalar(select(func.count()).select_from(TestResult)) == 14  # not doubled
        # Lifecycle/episodes/classifications are not doubled either.
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 7
        assert s.scalar(select(func.count()).select_from(Classification)) == 7


def test_ingest_drives_analysis_and_code_candidates(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702)
    with session_scope(session_factory) as s:
        run = s.scalar(select(Run).where(Run.build_number == 1702))
        assert run.baseline_run_id is None  # first run — nothing to diff against
        # 7 distinct failing identities -> 7 open episodes, all FAILING, all classified.
        assert s.scalar(select(func.count()).select_from(TestLifecycle)) == 7
        states = set(s.scalars(select(TestLifecycle.state)).all())
        assert states == {LifecycleState.FAILING}
        assert s.scalar(select(func.count()).select_from(FailureEpisode)) == 7
        # The fixture carries one SVN commit and no data feed -> CODE_CHANGE.
        assert s.scalar(select(func.count()).select_from(CodeChangeCandidate)) == 1
        causes = set(s.scalars(select(Classification.predicted_cause)).all())
        assert causes == {PredictedCause.CODE_CHANGE}


def test_ingest_with_data_feed_persists_data_candidates(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, feed=FakeTrackingFeed())
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(DataChangeCandidate)) > 0
        # Both code and data candidates present -> ambiguous -> UNKNOWN (both attached as evidence).
        causes = set(s.scalars(select(Classification.predicted_cause)).all())
        assert causes == {PredictedCause.UNKNOWN}


def test_data_change_window_looks_back_with_tolerance():
    from datetime import UTC, datetime

    start = datetime(2026, 6, 26, 17, 0, tzinfo=UTC)
    end = datetime(2026, 6, 26, 19, 0, tzinfo=UTC)
    lo, hi = data_change_window(
        (start, end), lookback=timedelta(hours=12), tolerance=timedelta(minutes=5)
    )
    assert lo == start - timedelta(hours=12) - timedelta(minutes=5)
    assert hi == end + timedelta(minutes=5)
