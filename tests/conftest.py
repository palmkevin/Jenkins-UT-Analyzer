"""Shared offline test fixtures. Nothing here touches a gated external system."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _bad_log_calls_are_failures():
    """Make a malformed ``uta.*`` log call fail the test that triggers it.

    A log record is only *formatted* once it reaches a handler, so a broken call — the classic
    ``%d`` fed an ORM object — is invisible while the logger sits at its default WARNING level:
    ``logging`` swallows the error and prints a ``--- Logging error ---`` dump to stderr, which
    nothing asserts on. Raising the ``uta`` logger to DEBUG makes every one of our records reach
    pytest's ``LogCaptureHandler``, whose ``handleError`` re-raises rather than printing, so the
    formatting error surfaces as a test failure.

    Scoped to the ``uta`` tree on purpose: setting the *root* level instead would also enable
    SQLAlchemy's statement logging, filling captured records with every SQL statement in a
    DB-heavy suite that is already memory-tight.
    """
    logger = logging.getLogger("uta")
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        logger.setLevel(previous)


def _load(rel: str) -> dict:
    return json.loads((FIXTURES / rel).read_text())


@pytest.fixture
def session_factory():
    """An in-memory SQLite store with the full schema created (offline, no Postgres)."""
    from uta.db import Base, make_engine, make_session_factory

    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def test_report_1702() -> dict:
    return _load("jenkins/testReport_1702.json")


@pytest.fixture
def change_sets_1702() -> dict:
    return _load("jenkins/changeSets_1702.json")


@pytest.fixture
def wfapi_1702() -> dict:
    return _load("jenkins/wfapi_1702.json")
