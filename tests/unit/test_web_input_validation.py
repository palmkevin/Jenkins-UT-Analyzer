"""Form / path input hardening on the dashboard's write routes (2026-11 bug hunt).

Invalid input must bounce back with an error flash (or a 4xx) and write nothing — never a 500, and
never a value the column can't hold. Exercised through the real app on in-memory SQLite.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.kb.store import record_signatures_for_build
from uta.models import Attribution, BuildIncident, FailureEpisode
from uta.web import actions
from uta.web.app import create_app, normalize_ticket


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
    """Two failing tests sharing one failure signature, with open episodes."""
    with session_scope(session_factory) as s:
        r1 = make_build(
            s,
            1,
            {"alpha": "FAILED", "beta": "FAILED"},
            errors={"alpha": ("boom", "Traceback"), "beta": ("boom", "Traceback")},
        )
        apply_build(s, r1, baseline=None)
        record_signatures_for_build(s, r1)
    return session_factory


@pytest.fixture
def client(seeded):
    return TestClient(create_app(session_factory=seeded), follow_redirects=False)


def _episode_id(sf, name) -> int:
    with session_scope(sf) as s:
        return get_identity(s, name).lifecycle.current_episode_id


def _signature_id(sf, name) -> int:
    with session_scope(sf) as s:
        return actions._episode_signature_id(s, get_identity(s, name).lifecycle.current_episode)


def _episode(sf, name) -> FailureEpisode:
    with session_scope(sf) as s:
        ep = s.get(FailureEpisode, get_identity(s, name).lifecycle.current_episode_id)
        s.expunge(ep)
        return ep


def _incident_id(sf) -> int:
    with session_scope(sf) as s:
        build = make_build(s, 2, {})
        inc = BuildIncident(
            opened_build_id=build.id,
            opened_at=build.started_at,
            last_build_id=build.id,
            last_at=build.started_at,
        )
        s.add(inc)
        s.flush()
        return inc.id


def _flash_page(client) -> str:
    return client.get("/").text


# ── triage-status-unvalidated ──────────────────────────────────────────────────


@pytest.mark.parametrize("route", ["episode", "bulk", "signature", "incident"])
def test_unknown_triage_status_is_rejected_with_flash(client, seeded, route):
    bogus = "NOT_A_STATUS_AT_ALL_REALLY"
    data = {"triage_status": bogus, "causing_person": "frank"}
    if route == "episode":
        url = f"/episodes/{_episode_id(seeded, 'alpha')}/attribute"
    elif route == "bulk":
        url = "/episodes/bulk/attribute"
        data["episode_ids"] = [str(_episode_id(seeded, "alpha"))]
    elif route == "signature":
        url = f"/signatures/{_signature_id(seeded, 'alpha')}/attribute"
    else:
        url = f"/incidents/{_incident_id(seeded)}/attribute"
    resp = client.post(url, data=data, headers={"referer": "/"})
    assert resp.status_code == 303
    page = _flash_page(client)
    assert "Unknown triage status" in page and "alert-danger" in page
    assert _episode(seeded, "alpha").triage_status != bogus
    with session_scope(seeded) as s:
        for inc in s.query(BuildIncident):
            assert inc.triage_status != bogus


# ── unbounded-form-input ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("field", "limit"),
    [("causing_person", 128), ("assignee", 128), ("cause_ticket", 32), ("resolution_ticket", 32)],
)
def test_over_long_episode_field_is_rejected_with_flash(client, seeded, field, limit):
    ep_id = _episode_id(seeded, "alpha")
    resp = client.post(
        f"/episodes/{ep_id}/attribute", data={field: "x" * (limit + 1)}, headers={"referer": "/"}
    )
    assert resp.status_code == 303
    page = _flash_page(client)
    assert f"too long (max {limit} characters)" in page and "alert-danger" in page
    ep = _episode(seeded, "alpha")
    assert ep.assignee is None and ep.cause_ticket is None and ep.resolution_ticket is None


def test_over_long_incident_ticket_is_rejected(client, seeded):
    inc_id = _incident_id(seeded)
    client.post(
        f"/incidents/{inc_id}/attribute", data={"cause_ticket": "X" * 40}, headers={"referer": "/"}
    )
    assert "too long (max 32 characters)" in _flash_page(client)
    with session_scope(seeded) as s:
        assert s.get(BuildIncident, inc_id).cause_ticket is None


def test_over_long_bulk_and_signature_person_is_rejected(client, seeded):
    ep_id = _episode_id(seeded, "alpha")
    client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(ep_id)], "causing_person": "p" * 200},
        headers={"referer": "/"},
    )
    assert "Causing person is too long" in _flash_page(client)
    client.post(
        f"/signatures/{_signature_id(seeded, 'alpha')}/attribute",
        data={"assignee": "a" * 200},
        headers={"referer": "/"},
    )
    assert "Assignee is too long" in _flash_page(client)
    assert _episode(seeded, "alpha").assignee is None


def test_over_long_actor_is_rejected(client):
    client.post("/identity", data={"actor": "n" * 129}, headers={"referer": "/"})
    assert "Acting user is too long (max 128 characters)" in _flash_page(client)
    assert "uta_actor" not in client.cookies


def test_over_long_actor_cookie_is_clamped(client, seeded):
    client.cookies.set("uta_actor", "z" * 300)
    ep_id = _episode_id(seeded, "alpha")
    client.post(f"/episodes/{ep_id}/attribute", data={"causing_person": "frank"})
    with session_scope(seeded) as s:
        attr = s.scalar(select(Attribution).where(Attribution.episode_id == ep_id))
        assert attr.validated_by == "z" * 128


@pytest.mark.parametrize(
    "pasted",
    [
        "https://jira.example.test/browse/LX-123",
        "  https://jira.example.test/jira/browse/LX-123?focusedCommentId=9#comment-9  ",
    ],
)
def test_pasted_jira_url_is_reduced_to_its_key(client, seeded, pasted):
    ep_id = _episode_id(seeded, "alpha")
    client.post(
        f"/episodes/{ep_id}/attribute",
        data={"cause_ticket": pasted, "resolution_ticket": pasted},
        headers={"referer": "/"},
    )
    ep = _episode(seeded, "alpha")
    assert ep.cause_ticket == "LX-123" and ep.resolution_ticket == "LX-123"


def test_normalize_ticket_leaves_plain_keys_and_other_text_alone():
    assert normalize_ticket("  ABC-1 ") == "ABC-1"
    assert normalize_ticket("https://example.test/not-jira") == "https://example.test/not-jira"
    assert normalize_ticket("") == ""


def test_forms_carry_maxlength(client, seeded):
    ep_id = _episode_id(seeded, "alpha")
    with session_scope(seeded) as s:
        identity_id = s.get(FailureEpisode, ep_id).test_identity_id
    page = client.get(f"/tests/{identity_id}").text
    assert 'name="causing_person" maxlength="128"' in page
    assert 'name="assignee" maxlength="128"' in page
    assert 'name="cause_ticket" maxlength="512"' in page  # room for a pasted URL
    assert 'name="actor" maxlength="128"' in page
    inc_page = client.get(f"/incidents/{_incident_id(seeded)}").text
    assert 'name="causing_person" maxlength="128"' in inc_page
    assert 'name="resolution_ticket" maxlength="512"' in inc_page


# ── bulk-ids-int-parse-500 ─────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", ["abc", "1.5", "-3", "", "99999999999999999999", "٣"])
def test_bulk_acknowledge_bad_id_is_an_error_flash(client, seeded, bad):
    good = _episode(seeded, "alpha").test_identity_id
    resp = client.post(
        "/tests/bulk/acknowledge",
        data={"identity_ids": [str(good), bad]},
        headers={"referer": "/"},
    )
    assert resp.status_code == 303
    page = _flash_page(client)
    assert "Invalid test selection — nothing acknowledged" in page
    with session_scope(seeded) as s:
        assert get_identity(s, "alpha").lifecycle.acknowledged is False


@pytest.mark.parametrize("bad", ["abc", "0", "2147483648"])
def test_bulk_attribute_bad_id_is_an_error_flash(client, seeded, bad):
    resp = client.post(
        "/episodes/bulk/attribute",
        data={"episode_ids": [str(_episode_id(seeded, "alpha")), bad], "causing_person": "frank"},
        headers={"referer": "/"},
    )
    assert resp.status_code == 303
    assert "Invalid test selection — nothing updated" in _flash_page(client)
    with session_scope(seeded) as s:
        assert s.scalar(select(Attribution)) is None
