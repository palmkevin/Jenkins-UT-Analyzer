"""'Never lose your place' navigation (issue #143).

Covers the drill-down back-links (test record → the referring filtered triage queue, build detail →
the job-builds list), the same-origin sanitization of the user-controllable ``?return=`` / Referer
inputs, and the ``#episode-N`` fragment that episode-scoped PRG actions append so the browser
lands back on the card that was just edited.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.models import TestLifecycle
from uta.web.app import _same_origin_path, create_app


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
    """A reopened test ("alpha", two episodes) and a passing one ("beta")."""
    with session_scope(session_factory) as s:
        baseline = None
        for build, status in enumerate(["FAILED", "PASSED", "FAILED"], start=1):
            build = make_build(s, build, {"alpha": status, "beta": "PASSED"})
            apply_build(s, build, baseline=baseline)
            baseline = build
    return session_factory


@pytest.fixture
def client(seeded):
    return TestClient(create_app(session_factory=seeded), follow_redirects=False)


def _identity_id(session_factory, name) -> int:
    with session_scope(session_factory) as s:
        return get_identity(s, name).id


def _current_episode_id(session_factory, ident_id) -> int:
    with session_scope(session_factory) as s:
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident_id))
        return lc.current_episode_id


# ── the same-origin gate (pure function) ─────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("/", "/"),
        ("/?owner=AB&sort=name", "/?owner=AB&sort=name"),
        ("/builds?page=2", "/builds?page=2"),
        (None, None),
        ("", None),
        ("https://evil.example/x", None),  # absolute external URL
        ("http://evil.example/?owner=AB", None),
        ("//evil.example/x", None),  # scheme-relative
        ("/\\evil.example", None),  # backslash trick (browser-normalized to //)
        ("javascript:alert(1)", None),
        ("relative/path", None),  # not an absolute path
    ],
)
def test_same_origin_path_gate(raw, expected):
    assert _same_origin_path(raw) == expected


# ── N1: breadcrumbs on the drill-down pages ─────────────────────────────────


def test_record_breadcrumb_falls_back_to_plain_queue(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.get(f"/tests/{ident_id}")
    assert resp.status_code == 200
    assert 'aria-label="breadcrumb"' in resp.text
    assert '<a href="/">&larr; Triage queue</a>' in resp.text


def test_record_breadcrumb_preserves_filtered_queue_url(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.get(f"/tests/{ident_id}", params={"return": "/?owner=AB&sort=name"})
    assert resp.status_code == 200
    # Jinja HTML-escapes the & in the query string.
    assert '<a href="/?owner=AB&amp;sort=name">&larr; Triage queue</a>' in resp.text


@pytest.mark.parametrize(
    "evil",
    ["https://evil.example/x", "//evil.example/x", "/\\evil.example", "javascript:alert(1)"],
)
def test_record_breadcrumb_rejects_non_same_origin_return(client, seeded, evil):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.get(f"/tests/{ident_id}", params={"return": evil})
    assert resp.status_code == 200
    assert "evil.example" not in resp.text
    assert "javascript:" not in resp.text
    assert '<a href="/">&larr; Triage queue</a>' in resp.text  # fell back to the plain queue


def test_missing_record_page_still_has_breadcrumb(client):
    resp = client.get("/tests/99999")
    assert resp.status_code == 200
    assert '<a href="/">&larr; Triage queue</a>' in resp.text


def test_build_page_breadcrumb_links_to_job_builds(client):
    for path in ("/builds/1", "/builds/999"):  # ingested build and the not-ingested branch alike
        resp = client.get(path)
        assert resp.status_code == 200
        assert '<a href="/builds">&larr; Job builds</a>' in resp.text


def test_filtered_triage_queue_links_carry_return_param(client):
    plain = client.get("/")
    assert plain.status_code == 200
    assert "?return=" not in plain.text  # unfiltered queue: no noise on the record links

    # A filter alpha matches (it fails on `permanent`) plus a sort — the full URL state.
    filtered = client.get("/", params={"track": "permanent", "sort": "name"})
    assert filtered.status_code == 200
    # The record link carries the queue URL percent-encoded, so the nested query survives.
    assert "?return=%2F%3Ftrack%3Dpermanent%26sort%3Dname" in filtered.text


# ── N4: episode anchors + redirect-with-fragment ─────────────────────────────


def test_episode_cards_have_stable_anchors_and_anchor_fields(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    page = client.get(f"/tests/{ident_id}").text
    # Two episodes (reopened test) — one anchor each, plus the hidden field on the episode forms.
    assert 'id="episode-1"' in page
    assert 'id="episode-2"' in page
    assert '<input type="hidden" name="anchor" value="episode-2">' in page


def test_attribute_redirects_back_with_episode_fragment(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    ep_id = _current_episode_id(seeded, ident_id)
    resp = client.post(
        f"/episodes/{ep_id}/attribute",
        data={"reason_text": "known infra flake", "anchor": "episode-2"},
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/tests/{ident_id}#episode-2"


def test_confirm_redirects_back_with_episode_fragment(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    ep_id = _current_episode_id(seeded, ident_id)
    resp = client.post(
        f"/episodes/{ep_id}/confirm",
        data={"anchor": "episode-2"},
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/tests/{ident_id}#episode-2"


def test_fragment_redirect_preserves_return_param(client, seeded):
    """The ?return= carried on the record URL survives the PRG bounce (it rides the referer)."""
    ident_id = _identity_id(seeded, "alpha")
    ep_id = _current_episode_id(seeded, ident_id)
    referer = f"/tests/{ident_id}?return=%2F%3Fowner%3DAB"
    resp = client.post(
        f"/episodes/{ep_id}/attribute",
        data={"reason_text": "x", "anchor": "episode-2"},
        headers={"referer": referer},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"{referer}#episode-2"


def test_invalid_anchor_is_dropped_from_redirect(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    ep_id = _current_episode_id(seeded, ident_id)
    resp = client.post(
        f"/episodes/{ep_id}/attribute",
        data={"reason_text": "x", "anchor": "episode-2#//evil.example"},
        headers={"referer": f"/tests/{ident_id}"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/tests/{ident_id}"


def test_action_redirect_never_leaves_the_app(client, seeded):
    """An absolute (attacker-shaped) referer degrades to its same-origin path + query."""
    ident_id = _identity_id(seeded, "alpha")
    resp = client.post(
        f"/tests/{ident_id}/acknowledge",
        headers={"referer": "https://evil.example/?owner=AB"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/?owner=AB"


def test_action_redirect_unusable_referer_falls_back(client, seeded):
    ident_id = _identity_id(seeded, "alpha")
    resp = client.post(
        f"/tests/{ident_id}/acknowledge",
        headers={"referer": "/\\evil.example"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
