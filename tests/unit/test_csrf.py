"""Offline tests of the app-wide cross-site write guard (CSRF, issue #88).

Exercised through real routes — a control endpoint and a triage action — with the browser fetch
metadata (``Sec-Fetch-Site`` / ``Origin``) set by hand. The TestClient sends neither header by
default, which is exactly the non-browser case the guard must keep allowing.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from uta.db import Base, make_session_factory
from uta.web.app import create_app

# One control-panel write and two triage writes — all must be behind the same app-wide guard.
# Empty store is fine: reset is a no-op for an unset key, acknowledge/attribute for an unknown
# identity/signature.
CONTROL_POST = "/control/settings/ui_row_limit/reset"
TRIAGE_POST = "/tests/1/acknowledge"
SIGNATURE_ATTRIBUTE_POST = "/signatures/1/attribute"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    return TestClient(create_app(session_factory=sf), follow_redirects=False)


@pytest.mark.parametrize("path", [CONTROL_POST, TRIAGE_POST, SIGNATURE_ATTRIBUTE_POST])
def test_cross_site_fetch_post_is_rejected(client, path):
    resp = client.post(path, headers={"Sec-Fetch-Site": "cross-site"})
    assert resp.status_code == 403


def test_same_site_fetch_post_is_rejected(client):
    # A sibling subdomain is still another origin — nothing legitimate posts from one.
    resp = client.post(CONTROL_POST, headers={"Sec-Fetch-Site": "same-site"})
    assert resp.status_code == 403


@pytest.mark.parametrize("path", [CONTROL_POST, TRIAGE_POST, SIGNATURE_ATTRIBUTE_POST])
def test_mismatching_origin_post_is_rejected(client, path):
    resp = client.post(path, headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403


def test_same_host_different_port_origin_is_rejected(client):
    resp = client.post(CONTROL_POST, headers={"Origin": "http://testserver:8080"})
    assert resp.status_code == 403


def test_null_origin_post_is_rejected(client):
    # Sandboxed iframes / data: URLs send the literal `Origin: null`.
    resp = client.post(CONTROL_POST, headers={"Origin": "null"})
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "headers",
    [
        {"Sec-Fetch-Site": "same-origin"},  # HTMX / same-page form post in a real browser
        {"Sec-Fetch-Site": "none"},  # direct (user-initiated) request
        {"Origin": "http://testserver"},  # older browser, matching host
        {},  # non-browser client (curl, scripts, this TestClient)
    ],
)
@pytest.mark.parametrize("path", [CONTROL_POST, TRIAGE_POST, SIGNATURE_ATTRIBUTE_POST])
def test_legitimate_posts_pass_through(client, path, headers):
    resp = client.post(path, headers=headers)
    assert resp.status_code == 303  # the routes' normal Post/Redirect/Get bounce


def test_sec_fetch_site_wins_over_a_matching_origin(client):
    # Fetch metadata is the stronger evidence; a matching Origin doesn't rehabilitate cross-site.
    resp = client.post(
        CONTROL_POST,
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "http://testserver"},
    )
    assert resp.status_code == 403


def test_gets_are_untouched(client):
    # Reads are safe by design (and the auth-on OIDC redirect dance is all GETs).
    resp = client.get("/health", headers={"Sec-Fetch-Site": "cross-site"})
    assert resp.status_code == 200
