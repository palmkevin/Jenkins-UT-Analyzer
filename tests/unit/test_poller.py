"""Scheduled poll selection + ingest (uta.poller)."""

from __future__ import annotations

from sqlalchemy import func, select

from tests.fakes import FakeJenkinsClient
from uta.db import session_scope
from uta.models import Run
from uta.poller import builds_to_ingest, highest_ingested_build, poll_once


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
    assert builds_to_ingest(_MultiBuildFake(last_completed=3), session_factory) == [1, 2, 3]


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
        assert s.scalar(select(func.count()).select_from(Run)) == 2


def test_no_completed_build_yields_nothing(session_factory):
    assert builds_to_ingest(_MultiBuildFake(last_completed=None), session_factory) == []
