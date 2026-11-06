"""Flash feedback for the mutating actions (issue #75).

Covers the round trip through the real app: a mutating POST 303-redirects with the one-shot
cookie, the next GET renders the banner exactly once (success or error variant), and a reload
doesn't re-show it. Plus the per-action message content — count-bearing where a count exists.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.lifecycle import apply_build
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
        r1 = make_build(s, 1, {"alpha": "FAILED", "beta": "FAILED"})
        apply_build(s, r1, baseline=None)
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


def test_flash_renders_as_fixed_live_region_toast(client, seeded):
    """The flash floats over the viewport corner (issue #150) — an in-flow banner would be
    scrolled out of view when the redirect lands on an in-page anchor — and announces itself
    politely to screen readers."""
    ident_id = _identity_id(seeded, "alpha")
    client.post(f"/tests/{ident_id}/acknowledge", headers={"referer": "/"})
    page = client.get("/").text
    toast = re.search(r'<div class="[^"]*uta-toast[^"]*"[^>]*>', page)
    assert toast, "no toast markup"
    assert "position-fixed" in toast.group(0)
    assert 'role="status"' in toast.group(0)
    assert 'aria-live="polite"' in toast.group(0)
    # The auto-dismiss script (pause-on-hover) ships with the page.
    assert "uta-toast" in page and "mouseenter" in page


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
    from uta.kb.store import record_signatures_for_build
    from uta.web import actions

    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        sig_id = actions._episode_signature_id(
            s, get_identity(s, "alpha").lifecycle.current_episode
        )
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    client.post(f"/signatures/{sig_id}/acknowledge", headers={"referer": "/"})
    assert "Acknowledged 2 tests sharing this failure signature" in client.get("/").text


def test_attribute_by_signature_message_carries_count(session_factory):
    from uta.kb.store import record_signatures_for_build
    from uta.web import actions

    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
        sig_id = actions._episode_signature_id(
            s, get_identity(s, "alpha").lifecycle.current_episode
        )
    client = TestClient(create_app(session_factory=session_factory), follow_redirects=False)
    client.post(
        f"/signatures/{sig_id}/attribute",
        data={"causing_person": "frank", "triage_status": "ROOT_CAUSED"},
        headers={"referer": "/"},
    )
    page = client.get("/").text
    assert (
        "Updated 2 tests sharing this failure signature — cause → frank, "
        "triage status → ROOT_CAUSED" in page
    )


def test_attribute_by_signature_unknown_signature_is_an_error_flash(client):
    client.post(
        "/signatures/424242/attribute", data={"causing_person": "x"}, headers={"referer": "/"}
    )
    page = client.get("/").text
    assert "No open failing tests share this signature" in page
    assert "alert-danger" in page


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


def _suggest(session_factory, *, contact=None, hypothesis=None, episode_id=None, incident_id=None):
    from uta.models import Classification
    from uta.models.enums import PredictedCause

    with session_scope(session_factory) as s:
        s.add(
            Classification(
                episode_id=episode_id,
                incident_id=incident_id,
                predicted_cause=PredictedCause.CODE_CHANGE,
                suggested_contact=contact,
                llm_hypothesis=hypothesis,
            )
        )


def _attribution_count(session_factory) -> int:
    from sqlalchemy import func, select

    from uta.models import Attribution

    with session_scope(session_factory) as s:
        return s.scalar(select(func.count()).select_from(Attribution))


def test_confirm_message(client, seeded):
    ep_id = _episode_id(seeded, "alpha")
    _suggest(seeded, contact="dev-dave", hypothesis="trunk commit r1", episode_id=ep_id)
    client.post(f"/episodes/{ep_id}/confirm", headers={"referer": "/"})
    assert "AI suggestion confirmed — cause → dev-dave" in client.get("/").text


def test_confirm_with_no_ai_suggestion_says_so_and_creates_no_row(client, seeded):
    # confirm-clobbers-human-reason: nothing suggested ⇒ nothing confirmed, no empty Attribution.
    ep_id = _episode_id(seeded, "alpha")
    client.post(f"/episodes/{ep_id}/confirm", headers={"referer": "/"})
    page = client.get("/").text
    assert "Nothing to confirm — the AI made no suggestion" in page
    assert "AI suggestion confirmed" not in page
    assert _attribution_count(seeded) == 0


def test_confirm_of_a_hypothesis_only_never_reports_the_human_cause(client, seeded):
    # The AI suggested only a hypothesis; the human-entered cause is kept but was not *confirmed*,
    # so the flash must not claim "cause → <human value>".
    ep_id = _episode_id(seeded, "alpha")
    client.post(
        f"/episodes/{ep_id}/attribute", data={"causing_person": "carol"}, headers={"referer": "/"}
    )
    client.get("/")  # consume that flash
    _suggest(seeded, hypothesis="trunk commit r1", episode_id=ep_id)
    client.post(f"/episodes/{ep_id}/confirm", headers={"referer": "/"})
    page = client.get("/").text
    assert "AI suggestion confirmed — hypothesis only" in page
    assert "cause → carol" not in page


def _incident_id(session_factory) -> int:
    from uta.analyze.incident import apply_build_incident

    with session_scope(session_factory) as s:
        b = make_build(s, 2, {})
        s.flush()
        inc = apply_build_incident(
            s, b, "FAILURE", failing_stage="Compile", failing_stage_log="compilation failed\nexit 1"
        ).incident
        s.flush()
        return inc.id


def test_confirm_incident_with_no_ai_suggestion_says_so_and_creates_no_row(client, seeded):
    from sqlalchemy import update

    from uta.models import Classification

    inc_id = _incident_id(seeded)
    with session_scope(seeded) as s:  # whatever the classifier said, the AI suggested nothing
        s.execute(
            update(Classification)
            .where(Classification.incident_id == inc_id)
            .values(suggested_contact=None, llm_hypothesis=None)
        )
    client.post(f"/incidents/{inc_id}/confirm", headers={"referer": "/"})
    page = client.get("/").text
    assert "Nothing to confirm — the AI made no suggestion" in page
    assert _attribution_count(seeded) == 0


def test_confirm_incident_reports_the_confirmed_cause(client, seeded):
    inc_id = _incident_id(seeded)
    _suggest(seeded, contact="dev-dana", incident_id=inc_id)
    client.post(f"/incidents/{inc_id}/confirm", headers={"referer": "/"})
    assert "AI suggestion confirmed — cause → dev-dana" in client.get("/").text
    assert _attribution_count(seeded) == 1


def test_bulk_attribute_message_carries_count_and_status(client, seeded):
    ep_ids = [_episode_id(seeded, n) for n in ("alpha", "beta")]
    client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(i) for i in ep_ids], "triage_status": "INVESTIGATING"},
        headers={"referer": "/"},
    )
    assert "Updated 2 selected tests — triage status → INVESTIGATING" in client.get("/").text


def test_bulk_attribute_all_blank_input_is_a_nothing_to_apply_error(client, seeded):
    """A selection with every field blank writes nothing, so it must not flash "Updated N"
    (issue #150)."""
    ep_ids = [_episode_id(seeded, n) for n in ("alpha", "beta")]
    client.post(
        "/episodes/bulk/attribute",
        data={
            "episode_ids": [str(i) for i in ep_ids],
            "causing_person": "  ",
            "reason_text": "",
            "triage_status": "",
        },
        headers={"referer": "/"},
    )
    page = client.get("/").text
    assert "Nothing to apply — fill in a status, person or reason" in page
    assert "alert-danger" in page
    assert "Updated" not in page


def test_bulk_attribute_counts_only_episodes_actually_updated(client, seeded):
    """A stale selection (an episode id that no longer exists) must not inflate the count."""
    ep_id = _episode_id(seeded, "alpha")
    client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(ep_id), "424242"], "causing_person": "frank"},
        headers={"referer": "/"},
    )
    assert "Updated 1 selected test" in client.get("/").text


def test_bulk_attribute_vanished_selection_is_an_error(client):
    client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": ["424242"], "causing_person": "frank"},
        headers={"referer": "/"},
    )
    page = client.get("/").text
    assert "Nothing updated — the selected tests no longer exist" in page
    assert "alert-danger" in page


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
    resp = client.post("/control/settings", data={"key": "flaky_window_days", "value": "9999"})
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


def test_ingest_above_high_water_is_an_error_flash(client, monkeypatch):
    """Store tops out at #1: queueing #5 would strand #2-#4 (ondemand-ingest-jumps-high-water)."""
    monkeypatch.setattr(jobs, "build_client", lambda settings: object())
    monkeypatch.setattr(jobs, "build_feed", lambda settings: None)
    client.post("/control/ingest", data={"build_start": "5"})
    page = client.get("/control").text
    assert "above the high-water mark" in page and "alert-danger" in page
