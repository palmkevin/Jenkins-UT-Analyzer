"""End-to-end integration tests over the synthetic demo dataset.

These drive the *real* ingest -> analysis -> web stack on the fabricated history (no external
system), so they double as the smoke test for the online-hosted demo: if these pass, the deployed
app renders a populated, coherent dashboard. They run in the default offline suite (no ``live``
marker), so CI executes them on every PR.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from uta.demo.app import build_demo_session_factory, create_demo_app
from uta.demo.dataset import FIRST_BUILD
from uta.models import TestIdentity
from uta.web import views

_MEMORY = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="module")
def session_factory():
    """One seeded in-memory store shared across the read-only assertions (seeding is slow)."""
    return build_demo_session_factory(_MEMORY)


@pytest.fixture(scope="module")
def queue(session_factory):
    return views.triage_queue(session_factory(), recently_fixed_days=7, limit=200)


def test_every_triage_bucket_is_populated(queue):
    counts = queue["counts"]
    assert counts["new"] >= 1
    assert counts["still_failing"] >= 1
    assert counts["recently_fixed"] >= 1


def test_all_four_predicted_causes_are_represented(queue):
    causes = {
        row["predicted_cause"]
        for bucket in ("new", "still_failing", "recently_fixed")
        for row in queue[bucket]
    }
    assert {"CODE_CHANGE", "DATA_CHANGE", "INFRASTRUCTURE", "UNKNOWN"} <= causes


def test_removed_test_is_flagged_in_still_failing(queue):
    assert any(row.get("removed") for row in queue["still_failing"])


def test_acknowledged_and_attributed_failure_is_present(queue):
    tz = next(
        r
        for r in queue["still_failing"]
        if r["test_id"] == "ut_core.co_time.TestClass.test_timezone_convert"
    )
    assert tz["acknowledged"] is True
    assert tz["causing_person"] == "THA"
    assert tz["predicted_cause"] == "DATA_CHANGE"


def test_flaky_leaderboard_has_a_flaky_test(session_factory):
    board = views.flaky_leaderboard(session_factory(), window_days=30, threshold=0.3)
    flaky = [r for r in board["rows"] if r["flaky"]]
    assert flaky, "expected at least one flaky test on the leaderboard"
    assert any(r["test_id"].endswith("test_pdf_render") for r in flaky)


def test_recurrence_and_similar_cases(session_factory):
    session = session_factory()
    ident = session.scalar(
        select(TestIdentity).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    record = views.test_record(session, ident.id)
    recurrence = record["recurrence"]
    assert recurrence is not None
    assert recurrence["occurrence_count"] > 1  # the same failure recurs across builds
    assert recurrence["similar"], "expected fuzzy-similar past cases"


def test_run_summary_has_baseline_and_diff(session_factory):
    # Build 612 (index 11) opens the invoice-rounding regression.
    run = views.run_summary(session_factory(), FIRST_BUILD + 11, limit=500)
    assert run is not None
    assert run["complete"] is True
    assert run["baseline"] is not None
    assert run["baseline"]["build"] == FIRST_BUILD + 10
    reg = {r["test_id"] for r in run["diff"]["regressions"]}
    assert "ut_billing.bi_round.TestClass.test_invoice_rounding" in reg


def test_demo_app_serves_all_views():
    client = TestClient(create_demo_app(_MEMORY))
    health = client.get("/health")
    assert health.status_code == 200
    # The seeded heartbeat is fresh, so the demo reports a healthy poller.
    assert health.json()["status"] == "ok"
    assert health.json()["poller"] == "ok"
    for path in ("/", "/flaky", "/kb", f"/runs/{FIRST_BUILD + 11}"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert resp.text  # non-empty HTML
    assert "test_" in client.get("/").text  # the triage queue lists tests


def test_demo_app_test_record_route():
    from uta.web.app import create_app

    factory = build_demo_session_factory(_MEMORY)
    ident_id = factory().scalar(
        select(TestIdentity.id).where(
            TestIdentity.canonical_name == "ut_core.co_time.TestClass.test_timezone_convert"
        )
    )
    client = TestClient(create_app(session_factory=factory))
    resp = client.get(f"/tests/{ident_id}")
    assert resp.status_code == 200
    assert "timezone" in resp.text.lower()
