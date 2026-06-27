"""Slice-0 ingest pipeline against an in-memory SQLite DB (offline, no Postgres)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient
from uta.db import Base, make_engine, make_session_factory, session_scope
from uta.ingest.pipeline import data_change_window, ingest_build
from uta.models import Run, TestResult


@pytest.fixture
def session_factory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


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
        runs = s.scalar(select(func.count()).select_from(Run))
        results = s.scalar(select(func.count()).select_from(TestResult))
        assert runs == 1
        assert results == 14  # not doubled


def test_data_change_window_looks_back_before_run():
    from datetime import UTC, datetime

    start = datetime(2026, 6, 26, 17, 0, tzinfo=UTC)
    end = datetime(2026, 6, 26, 19, 0, tzinfo=UTC)
    lo, hi = data_change_window((start, end), lookback=timedelta(hours=12))
    assert lo == start - timedelta(hours=12)
    assert hi == end
