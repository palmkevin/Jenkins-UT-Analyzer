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
from uta.demo.app import build_demo_session_factory, create_demo_app
from uta.demo.dataset import FIRST_BUILD
from uta.models import IngestJob, SettingOverride
from uta.models.enums import IngestJobStatus

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
    assert resp.headers["location"] == "/control"
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "expected_shards") is None
    # The error surfaces on the panel as a one-shot flash banner (issue #75).
    page = client.get(resp.headers["location"]).text
    assert "must be between" in page and "alert-danger" in page
    # …and only once: a reload doesn't re-show it.
    assert "must be between" not in client.get("/control").text


def test_non_whitelisted_key_is_rejected(client, factory):
    resp = client.post(
        "/control/settings", data={"key": "database_url", "value": "x"}, follow_redirects=False
    )
    assert resp.status_code == 303
    with session_scope(factory) as s:
        assert s.get(SettingOverride, "database_url") is None


def test_override_reflected_in_a_view_on_next_load(client, factory):
    """The acceptance check: change the row cap and the build view honours it on the next load."""
    build = FIRST_BUILD + 11  # a complete build with 32 result rows
    # The demo seeds ui_row_limit=20, so the build page arrives already paginated (32 rows → 2
    # pages).
    assert "Page 1 of 2" in client.get(f"/builds/{build}").text

    client.post("/control/settings", data={"key": "ui_row_limit", "value": "1"})
    assert "Page 1 of 32" in client.get(f"/builds/{build}").text  # cap now bites — view reflects it

    client.post("/control/settings/ui_row_limit/reset")
    # Reverted to the env default (50): everything fits on one page again — no pager.
    assert "Page 1 of" not in client.get(f"/builds/{build}").text


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


# ── Demo lockdown (issue #89) ────────────────────────────────────────────────
# The *public demo app* (create_demo_app → demo_mode=True) refuses the control-panel mutations:
# the store is shared by every anonymous visitor, and the ingest route would otherwise build a
# real Jenkins client and send outbound requests from the public host. Everything above this
# section builds the normal create_app on the same demo store and must keep working unchanged.


@pytest.fixture(scope="module")
def demo_client():
    return TestClient(create_demo_app(_MEMORY))


def test_demo_control_page_still_renders_populated(demo_client):
    """Read side untouched: the demo keeps showcasing the whole panel — only mutation is blocked."""
    text = demo_client.get("/control").text
    assert "Control panel" in text
    assert "has not reported a tick yet" not in text  # poller heartbeat panel
    assert "override(s) active" in text  # seeded override badge
    assert "quarantined" in text  # build-quarantine table
    assert "done" in text and "error" in text  # ingest-job history badges
    # The lockdown is shown honestly: a notice plus disabled form buttons.
    assert "Read-only in the public demo" in text
    assert 'type="submit" disabled' in text


def test_demo_rejects_settings_override_post(demo_client):
    resp = demo_client.post(
        "/control/settings",
        data={"key": "flaky_window_days", "value": "45"},
        follow_redirects=False,
    )
    assert resp.status_code == 403
    assert "disabled in the public demo" in resp.text
    # Nothing persisted: only the two seeded overrides (kb_top_k, ui_row_limit) light the badge.
    text = demo_client.get("/control").text
    assert text.count(">overridden<") == 2


def test_demo_rejects_settings_reset_post(demo_client):
    resp = demo_client.post("/control/settings/kb_top_k/reset", follow_redirects=False)
    assert resp.status_code == 403
    assert "disabled in the public demo" in resp.text
    # The seeded override survives.
    assert "override(s) active" in demo_client.get("/control").text


def test_demo_rejects_ingest_post_and_never_builds_a_jenkins_client(demo_client, monkeypatch):
    def _explode(settings):  # pragma: no cover — the assertion is that this never runs
        raise AssertionError("demo mode must never construct a Jenkins client")

    monkeypatch.setattr(jobs, "build_client", _explode)

    resp = demo_client.post(
        "/control/ingest", data={"build_start": "1", "build_end": "999"}, follow_redirects=False
    )
    assert resp.status_code == 403
    assert "disabled in the public demo" in resp.text
    # No job row was created either — the guard builds before any dispatch.
    assert "#1–999" not in demo_client.get("/control").text


# ── HTMX job polling (issue #78) ─────────────────────────────────────────────


def test_jobs_fragment_returns_only_the_partial(client):
    resp = client.get("/control/jobs")
    assert resp.status_code == 200
    assert 'id="ingest-jobs"' in resp.text
    # Just the fragment — none of the page chrome around it.
    assert "<html" not in resp.text
    assert "Tunable thresholds" not in resp.text


def test_no_poll_trigger_when_all_jobs_terminal(client):
    # The demo seeds only terminal jobs (DONE + ERROR): the fragment carries no hx-trigger, so
    # a browser landing on the final state never starts the polling loop.
    assert "hx-trigger" not in client.get("/control/jobs").text
    page = client.get("/control").text
    assert "hx-trigger" not in page
    assert "Reload to refresh job status" not in page  # the manual-reload hint is gone


def test_active_job_polls_and_shows_progress(client, factory):
    with session_scope(factory) as s:
        job = IngestJob(
            build_start=1,
            build_end=4,
            builds_total=4,
            builds_done=1,
            status=IngestJobStatus.RUNNING,
        )
        s.add(job)
        s.flush()
        job_id = job.id
    try:
        fragment = client.get("/control/jobs").text
        # An active job renders the poll trigger — the swap loop keeps refreshing itself.
        assert 'hx-get="/control/jobs"' in fragment
        assert 'hx-trigger="every 3s"' in fragment
        # …and a progress bar at builds_done/builds_total (1/4 → 25%).
        assert "progress-bar" in fragment
        assert "width: 25%" in fragment
        # The full page embeds the same fragment, so the initial load starts the loop.
        assert 'hx-trigger="every 3s"' in client.get("/control").text
    finally:
        with session_scope(factory) as s:  # module-scoped factory — don't leak the RUNNING job
            s.delete(s.get(IngestJob, job_id))
