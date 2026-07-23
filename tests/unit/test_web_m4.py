"""HTTP-level tests for the M4 surfaces: flaky leaderboard + knowledge-base search.

Also asserts the per-test record now carries the flakiness + recurrence cards.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.flakiness import recompute_flaky_flags
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.kb.store import record_signatures_for_build
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
    """An oscillating test (for the leaderboard) and a recorded signature (for KB search).

    Builds are anchored to *now* (not a fixed epoch) so they always fall inside the flaky
    oscillation window — the leaderboard route computes that window from the real clock, so a
    fixed past date would silently age out and empty the board on later build dates.
    """
    base = datetime.now(UTC) - timedelta(days=2)
    with session_scope(session_factory) as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED"], start=1):
            errors = {"flap.test": ("test failure", _STACK.format(line=b, msg="1 != 2"))}
            build = make_build(
                s, b, {"flap.test": st}, errors=errors, started_at=base + timedelta(hours=b)
            )
            apply_build(s, build)
            record_signatures_for_build(s, build)
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
    assert 'class="sparkline"' in resp.text  # per-test recent-build sparkline (issue #53)
    # Non-hue pass/fail channel (issue #144): failed bars full-height, passed bars shorter.
    assert 'y="0.0"' in resp.text and 'height="22.0"' in resp.text  # failed bar
    assert 'y="9.9"' in resp.text and 'height="12.1"' in resp.text  # passed bar (0.55 × 22)


def test_flaky_leaderboard_total_is_true_count_not_capped(session_factory):
    """The header total counts every oscillating test, even beyond the display limit."""
    from uta.web.views import flaky_leaderboard

    base = datetime.now(UTC) - timedelta(days=2)
    names = [f"flap.test_{i}" for i in range(3)]
    with session_scope(session_factory) as s:
        for b, st in enumerate(["PASSED", "FAILED", "PASSED", "FAILED"], start=1):
            build = make_build(s, b, {n: st for n in names}, started_at=base + timedelta(hours=b))
            apply_build(s, build)
            recompute_flaky_flags(s)

    with session_scope(session_factory) as s:
        view = flaky_leaderboard(s, limit=1)

    assert view["total"] == 3  # true count of oscillating tests
    assert len(view["rows"]) == 1  # display capped by limit


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
    assert 'class="sparkline"' in resp.text  # per-build pass/fail history (issue #53)
