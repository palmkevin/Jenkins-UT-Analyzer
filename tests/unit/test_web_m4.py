"""HTTP-level tests for the M4 surfaces: flaky leaderboard (§3) + knowledge-base search (§4).

Also asserts the per-test record now carries the flakiness + recurrence cards.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_run
from uta.analyze.flakiness import recompute_flaky_flags
from uta.analyze.lifecycle import apply_run
from uta.db import Base, make_session_factory, session_scope
from uta.kb.store import record_signatures_for_run
from uta.web.app import create_app

_STACK = (
    "Traceback (most recent call last):\n"
    '  File "/opt/ls/lx/release/permanent/tests/dev/ut_ar/x.py", line {line}, in test_x\n'
    "    self.assertEqual(a, b)\n"
    "AssertionError: {msg}\n"
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def seeded(session_factory):
    """An oscillating test (for the leaderboard) and a recorded signature (for KB search)."""
    with session_scope(session_factory) as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED"], start=1):
            errors = {"flap.test": ("test failure", _STACK.format(line=b, msg="1 != 2"))}
            run = make_run(s, b, {"flap.test": st}, errors=errors)
            apply_run(s, run)
            record_signatures_for_run(s, run)
            recompute_flaky_flags(s)
    return session_factory


@pytest.fixture
def client(seeded):
    return TestClient(create_app(session_factory=seeded), follow_redirects=False)


def test_flaky_leaderboard_lists_oscillating_test(client):
    resp = client.get("/flaky")
    assert resp.status_code == 200
    assert "Flaky leaderboard" in resp.text
    assert "flap.test" in resp.text


def test_kb_search_empty_then_match(client):
    empty = client.get("/kb")
    assert empty.status_code == 200
    assert "Knowledge base" in empty.text

    hit = client.get("/kb", params={"q": "AssertionError\n<NUM> != <NUM>"})
    assert hit.status_code == 200
    assert "flap.test" in hit.text


def test_test_record_shows_flakiness_and_recurrence(client, seeded):
    with session_scope(seeded) as s:
        ident_id = get_identity(s, "flap.test").id
    resp = client.get(f"/tests/{ident_id}")
    assert resp.status_code == 200
    assert "Flakiness" in resp.text
    assert "Knowledge base" in resp.text  # recurrence card heading
    assert "seen" in resp.text
