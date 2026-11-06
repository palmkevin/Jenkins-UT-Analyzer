"""Form / path input hardening on the dashboard's write routes (2026-11 bug hunt).

Invalid input must bounce back with an error flash (or a 4xx) and write nothing — never a 500, and
never a value the column can't hold. Exercised through the real app on in-memory SQLite.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.kb.store import record_signatures_for_build
from uta.models import BuildIncident, FailureEpisode
from uta.web import actions
from uta.web.app import create_app


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
