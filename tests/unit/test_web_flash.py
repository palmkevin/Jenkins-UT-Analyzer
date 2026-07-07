"""Flash feedback for the mutating actions (issue #75).

Covers the round trip through the real app: a mutating POST 303-redirects with the one-shot
cookie, the next GET renders the banner exactly once (success or error variant), and a reload
doesn't re-show it. Plus the per-action message content — count-bearing where a count exists.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_run
from uta.analyze.lifecycle import apply_run
from uta.control import jobs
from uta.db import Base, make_session_factory, session_scope
from uta.web.app import create_app
from uta.web.flash import FLASH_COOKIE


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
    """Two failing tests with open episodes, for the ack/attribute actions."""
    with session_scope(session_factory) as s:
        r1 = make_run(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_run(s, r1, baseline=None)
    return session_factory


@pytest.fixture
def client(seeded):
    return TestClient(create_app(session_factory=seeded), follow_redirects=False)


def _identity_id(session_factory, name) -> int:
    with session_scope(session_factory) as s:
        return get_identity(s, name).id


def _episode_id(session_factory, name) -> int:
    with session_scope(session_factory) as s:
        return get_identity(s, name).lifecycle.current_episode_id


# ── the round trip (the acceptance check) ──────────────────────────────────────


def test_flash_round_trip_shows_banner_exactly_once(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    assert FLASH_COOKIE in client.cookies  # the message rides the redirect as a cookie

    first = client.get("/")
    assert "Test acknowledged" in first.text
    assert "alert-success" in first.text
    # The render consumed it: cookie deleted, so a reload is clean.
    assert FLASH_COOKIE not in client.cookies
    second = client.get("/")
    assert "Test acknowledged" not in second.text
    assert "alert-success" not in second.text


def test_error_variant_renders_danger_alert(client):
    resp = client.post("/tests/99999/acknowledge", headers={"referer": "/"})
    assert resp.status_code == 303
    page = client.get("/").text
    assert "Nothing acknowledged — the test has never failed" in page
    assert "alert-danger" in page


def test_banner_is_dismissible(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    page = client.get("/").text
    assert "alert-dismissible" in page and "btn-close" in page


# ── per-action messages (count-bearing where a count exists) ───────────────────


def test_bulk_acknowledge_message_carries_count(client, seeded):
    ids = [_identity_id(seeded, n) for n in ("alpha", "beta")]
    client.post(
        "/tests/bulk/acknowledge",
        data={"identity_ids": [str(i) for i in ids]},
        headers={"referer": "/"},
    )
    assert "Acknowledged 2 selected tests" in client.get("/").text


def test_bulk_acknowledge_empty_selection_is_an_error(client):
    client.post("/tests/bulk/acknowledge", data={}, headers={"referer": "/"})
    page = client.get("/").text
    assert "Nothing acknowledged — no tests selected" in page
    assert "alert-danger" in page


def test_acknowledge_by_signature_message_carries_count(session_factory):
    from uta.kb.store import record_signatures_for_run
    from uta.web import actions

    with session_scope(session_factory) as s:
        r1 = make_run(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_run(s, r1, baseline=None)
        record_signatures_for_run(s, r1)
        sig_id = actions._episode_signature_id(
            s, get_identity(s, "alpha").lifecycle.current_episode
        )
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    client.post(f"/signatures/{sig_id}/acknowledge", headers={"referer": "/"})
    assert "Acknowledged 2 tests sharing this failure signature" in client.get("/").text


def test_attribute_message_lists_what_was_saved(client, seeded):
    ep_id = _episode_id(seeded, "alpha")
    client.post(
        f"/episodes/{ep_id}/attribute",
        data={
            "causing_person": "frank",
            "reason_text": "flaky fixture",
            "triage_status": "INVESTIGATING",
        },
        headers={"referer": "/"},
    )
    page = client.get("/").text
    assert "Saved — cause → frank, reason updated, triage status → INVESTIGATING" in page


def test_confirm_message(client, seeded):
    ep_id = _episode_id(seeded, "alpha")
    client.post(f"/episodes/{ep_id}/confirm", headers={"referer": "/"})
    assert "AI suggestion confirmed" in client.get("/").text


def test_bulk_attribute_message_carries_count_and_status(client, seeded):
    ep_ids = [_episode_id(seeded, n) for n in ("alpha", "beta")]
    client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(i) for i in ep_ids], "triage_status": "INVESTIGATING"},
        headers={"referer": "/"},
    )
    assert "Updated 2 selected tests — triage status → INVESTIGATING" in client.get("/").text


def test_identity_set_message(client):
    client.post("/identity", data={"actor": "morgan"}, headers={"referer": "/"})
    assert "Now acting as morgan" in client.get("/").text


# ── control panel: save / revert / ingest on the same pattern ──────────────────


def test_setting_save_message_shows_old_and_new_value(client):
    client.post("/control/settings", data={"key": "flaky_window_days", "value": "45"})
    # env default is 30 → override 45
    assert "Flaky window (days) overridden: 30 → 45" in client.get("/control").text


def test_setting_revert_message_names_the_default(client):
    client.post("/control/settings", data={"key": "flaky_window_days", "value": "45"})
    client.get("/control")  # consume the save flash
    client.post("/control/settings/flaky_window_days/reset")
    assert "Flaky window (days) reverted to its env default (30)" in client.get("/control").text


def test_setting_error_uses_flash_not_query_param(client):
    resp = client.post(
        "/control/settings", data={"key": "flaky_window_days", "value": "9999"}
    )
    assert resp.headers["location"] == "/control"  # no ?error= any more — one pattern
    page = client.get("/control").text
    assert "must be between" in page and "alert-danger" in page
    # One-shot: gone on reload.
    assert "must be between" not in client.get("/control").text


def test_ingest_message_names_job_and_build_range(client, monkeypatch):
    monkeypatch.setattr(jobs, "trigger_ingest", lambda *a, **k: 42)
    client.post("/control/ingest", data={"build_start": "5", "build_end": "7"})
    assert "Ingest job #42 queued for builds #5–#7" in client.get("/control").text
    client.post("/control/ingest", data={"build_start": "5"})
    assert "Ingest job #42 queued for build #5" in client.get("/control").text


def test_ingest_non_numeric_range_is_an_error_flash(client):
    client.post("/control/ingest", data={"build_start": "5", "build_end": "x"})
    page = client.get("/control").text
    assert "Build range must be numeric" in page and "alert-danger" in page
