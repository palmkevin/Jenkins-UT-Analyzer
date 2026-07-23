"""Scheduled poll selection + ingest (uta.poller)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient
from uta.db import session_scope
from uta.models import Build
from uta.poller import build_scheduler, builds_to_ingest, highest_ingested_build, poll_once


class _MultiBuildFake(FakeJenkinsClient):
    """Serves the #1702 golden fixtures for *any* build number; configurable high-water mark."""

    def __init__(self, last_completed: int) -> None:
        super().__init__()
        self._last_completed = last_completed

    def _load(self, name: str, build: int) -> dict:
        return super()._load(name, self._build)  # reuse 1702 fixtures regardless of build

    def last_completed_build(self) -> int | None:
        return self._last_completed


def test_builds_to_ingest_from_empty_store(session_factory):
    # Fewer completed builds than the depth ⇒ floor at 1 (whole history, oldest-first).
    assert builds_to_ingest(_MultiBuildFake(last_completed=3), session_factory) == [1, 2, 3]


def test_cold_start_is_bounded_to_backfill_depth(session_factory):
    # Empty store + many builds ⇒ only the last `backfill_depth`, oldest-first (age N → age 1).
    assert builds_to_ingest(
        _MultiBuildFake(last_completed=100), session_factory, backfill_depth=10
    ) == list(range(91, 101))


def test_backfill_depth_ignored_once_store_is_non_empty(session_factory):
    poll_once(_MultiBuildFake(last_completed=2), session_factory)
    # High-water mark present ⇒ incremental above it regardless of depth.
    assert builds_to_ingest(
        _MultiBuildFake(last_completed=50), session_factory, backfill_depth=10
    ) == list(range(3, 51))


def test_builds_to_ingest_skips_already_ingested(session_factory):
    poll_once(_MultiBuildFake(last_completed=2), session_factory)
    assert highest_ingested_build(session_factory) == 2
    # Now only the new build above the high-water mark is selected.
    assert builds_to_ingest(_MultiBuildFake(last_completed=4), session_factory) == [3, 4]


def test_poll_once_is_idempotent(session_factory):
    client = _MultiBuildFake(last_completed=2)
    assert poll_once(client, session_factory) == [1, 2]
    assert poll_once(client, session_factory) == []  # nothing new
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(Build)) == 2


def test_no_completed_build_yields_nothing(session_factory):
    assert builds_to_ingest(_MultiBuildFake(last_completed=None), session_factory) == []


class _Rotated404Fake(_MultiBuildFake):
    """Serves the fixtures for every build except ``missing``, whose detail endpoint 404s.

    Models a build whose ``lastCompletedBuild`` pointer outlived its retention window: the number
    is valid but ``/<n>/api/json`` is gone.
    """

    def __init__(self, last_completed: int, missing: int) -> None:
        super().__init__(last_completed=last_completed)
        self._missing = missing

    def build_meta(self, build: int) -> dict:
        if build == self._missing:
            request = httpx.Request("GET", f"http://jenkins/{build}/api/json")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not Found", request=request, response=response)
        return super().build_meta(build)


def test_poll_once_skips_build_with_404_detail(session_factory):
    # Build #2's detail endpoint 404s; #1 and #3 still ingest, and no error propagates.
    client = _Rotated404Fake(last_completed=3, missing=2)
    assert poll_once(client, session_factory) == [1, 3]
    with session_scope(session_factory) as s:
        assert s.scalar(select(func.count()).select_from(Build)) == 2
    # The vanished build left no high-water mark; a later build advanced it past the gap.
    assert highest_ingested_build(session_factory) == 3
    # A subsequent tick with nothing new above the mark is a no-op (no retry of #2).
    assert poll_once(client, session_factory) == []


def test_scheduler_job_is_not_paused():
    # Regression for issue #80: an explicit ``next_run_time=None`` adds the job *paused* in
    # APScheduler 3.x, so the poller ran its one startup tick and then never fired again.
    # ``start()`` blocks forever on a BlockingScheduler, so assert on the unstarted registration:
    # a paused job carries ``next_run_time is None``, a healthy pending job either has a concrete
    # first fire time or leaves it unset for the scheduler to compute from the trigger on start.
    scheduler = build_scheduler(lambda: [], interval_seconds=60)
    (job,) = scheduler.get_jobs()
    assert getattr(job, "next_run_time", "unset — computed on start()") is not None
    # And the interval trigger itself has a next fire time, so the job will actually recur.
    assert job.trigger.get_next_fire_time(None, datetime.now(UTC)) is not None
