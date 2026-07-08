"""Control-panel HTTP routes over the demo stack (issue #16).

Drives the real FastAPI app so it covers the acceptance check end-to-end: change a threshold and see
a view reflect it on next load; trigger an ingest and watch it reach a terminal state; view the
poller heartbeat. The ingest route's Jenkins client is stubbed (offline suite touches no network).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.unit.test_control import _MultiBuildFake
from uta.control import jobs
from uta.control.jobs import trigger_ingest as _real_trigger
from uta.db import session_scope
from uta.demo.app import build_demo_session_factory
from uta.demo.dataset import FIRST_BUILD
from uta.models import IngestJob, SettingOverride

_MEMORY = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="module")
def factory():
    return build_demo_session_factory(_MEMORY)


@pytest.fixture
def client(factory):
    return TestClient(create_demo_app_from(factory))


def create_demo_app_from(factory):
    from uta.web.app import create_app

    return create_app(session_factory=factory)


def test_control_page_renders(client):
    resp = client.get("/control")
    assert resp.status_code == 200
    assert "Control panel" in resp.text
    assert "Flaky threshold" in resp.text  # a tunable label
    assert "Poller health" in resp.text


def test_demo_seeds_control_panel_state(client):
    """The seed populates all three panels so the Render showcase isn't half-empty (issue #16)."""
    text = client.get("/control").text
    assert "has not reported a tick yet" not in text  # heartbeat is seeded
    assert "override(s) active" in text  # the seeded kb_top_k override lights the badge
    assert "done" in text and "error" in text  # both seeded ingest jobs are listed


def test_set_and_revert_override_roundtrips(client, factory):
    # Set an override.
    resp = client.post(
        "/control/settings",
        data={"key": "flaky_window_days", "value": "45"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "flaky_window_days").value == "45"
    assert "overridden" in client.get("/control").text

    # Revert it.
    resp = client.post("/control/settings/flaky_window_days/reset", follow_redirects=False)
    assert resp.status_code == 303
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "flaky_window_days") is None


def test_empty_value_reverts_override(client, factory):
    client.post("/control/settings", data={"key": "kb_top_k", "value": "9"})
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "kb_top_k").value == "9"
    client.post("/control/settings", data={"key": "kb_top_k", "value": ""})
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "kb_top_k") is None


def test_invalid_override_is_rejected_with_error(client, factory):
    resp = client.post(
        "/control/settings", data={"key": "expected_shards", "value": "999"}, follow_redirects=False
    )
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "expected_shards") is None
    # The error surfaces on the panel.
    assert "must be between" in client.get(resp.headers["location"]).text


def test_non_whitelisted_key_is_rejected(client, factory):
    resp = client.post(
        "/control/settings", data={"key": "database_url", "value": "x"}, follow_redirects=False
    )
    assert resp.status_code == 303
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "database_url") is None


def test_override_reflected_in_a_view_on_next_load(client, factory):
    """The acceptance check: change the row cap and the run view honours it on the next load."""
    build = FIRST_BUILD + 11  # a complete run with 32 result rows
    # The demo seeds ui_row_limit=20, so the run page arrives already paginated (32 rows → 2 pages).
    assert "Page 1 of 2" in client.get(f"/runs/{build}").text

    client.post("/control/settings", data={"key": "ui_row_limit", "value": "1"})
    assert "Page 1 of 32" in client.get(f"/runs/{build}").text  # cap now bites — view reflects it

    client.post("/control/settings/ui_row_limit/reset")
    # Reverted to the env default (50): everything fits on one page again — no pager.
    assert "Page 1 of" not in client.get(f"/runs/{build}").text


def test_trigger_ingest_route_dispatches_job(client, factory, monkeypatch):
    # Stub the Jenkins client so the route's ingest runs synchronously on fixtures (no network).
    def _stub_trigger(session_factory, **kwargs):
        kwargs.pop("client", None)
        kwargs.pop("feed", None)
        kwargs.pop("run_in_thread", None)
        return _real_trigger(
            session_factory, client=_MultiBuildFake(), feed=None, run_in_thread=False, **kwargs
        )

    monkeypatch.setattr(jobs, "trigger_ingest", _stub_trigger)

    resp = client.post("/control/ingest", data={"build_start": "1"}, follow_redirects=False)
    assert resp.status_code == 303
    with session_scope(factory) as s:
        job = s.query(IngestJob).order_by(IngestJob.id.desc()).first()
        assert job.status == "DONE"
        assert job.build_start == 1 and job.build_end == 1
    # The job history is shown on the panel.
    assert "Ingest / re-analysis" in client.get("/control").text
