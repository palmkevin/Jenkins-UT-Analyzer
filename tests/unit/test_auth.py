"""Phase-2 Keycloak auth (issue #17) — offline, both flag positions.

The auth seam is "is there a logged-in user in the session, and who": tests seed it by signing a
real Starlette session cookie (same itsdangerous format ``SessionMiddleware`` uses) instead of
faking Authlib's network calls, so the real middleware chain, cookie verification, and
``current_actor`` path are exercised. ``/login`` and ``/auth/callback`` talk to the live Keycloak
(discovery + token exchange) and are covered by ``tests/live/test_keycloak_live.py`` plus the
deployment smoke test — not here (offline gate).
"""

from __future__ import annotations

import base64
import json

import pytest
from authlib.integrations.starlette_client import StarletteOAuth2App
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from tests.builders import get_identity, make_build
from uta.analyze.lifecycle import apply_build
from uta.db import Base, make_session_factory, session_scope
from uta.models import TestLifecycle
from uta.web.app import create_app

SECRET = "test-session-secret"


@pytest.fixture
def seeded():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as s:
        build = make_build(s, 1, {"alpha": "FAILED"})
        apply_build(s, build, baseline=None)
    return factory


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_SECRET", SECRET)


@pytest.fixture
def client(seeded, auth_on):
    # https base URL: the session cookie is Secure (https_only=True) and would be dropped over http.
    return TestClient(create_app(session_factory=seeded), base_url="https://uta.test")


def session_cookie(data: dict, secret: str = SECRET) -> str:
    """A signed session cookie exactly as Starlette's SessionMiddleware writes it."""
    payload = base64.b64encode(json.dumps(data).encode())
    return TimestampSigner(secret).sign(payload).decode()


def login(client: TestClient, username: str = "kc-user") -> None:
    data = {
        "user": {"sub": "abc", "preferred_username": username, "email": "", "name": ""},
        "id_token": "fake-id-token",
    }
    # domain must match so the server's clearing Set-Cookie (on /logout) replaces this entry.
    client.cookies.set("session", session_cookie(data), domain="uta.test")


def _identity_id(factory, name: str) -> int:
    with session_scope(factory) as s:
        return get_identity(s, name).id


# ── Flag off (default): byte-for-byte Phase-1 behaviour ─────────────────────────


def test_auth_off_serves_without_session(seeded):
    client = TestClient(create_app(session_factory=seeded), follow_redirects=False)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "test-user" in resp.text  # Phase-1 default actor, self-declared form still present
    assert 'action="/identity"' in resp.text
    assert "/logout" not in resp.text


def test_auth_on_requires_session_secret(seeded, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SESSION_SECRET", "")
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        create_app(session_factory=seeded)


# ── Flag on: middleware gate ────────────────────────────────────────────────────


def test_unauthenticated_get_redirects_to_login(client):
    resp = client.get("/?owner=zoe", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_unauthenticated_post_gets_401(client):
    resp = client.post("/tests/1/acknowledge", follow_redirects=False)
    assert resp.status_code == 401


def test_health_reachable_without_session(client):
    assert client.get("/health", follow_redirects=False).status_code == 200


def test_static_reachable_without_session(client):
    resp = client.get("/static/bootstrap.min.css", follow_redirects=False)
    assert resp.status_code == 200


def test_tampered_session_cookie_is_rejected(client):
    client.cookies.set("session", session_cookie({"user": {"preferred_username": "mallory"}}, "x"))
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303  # bad signature ⇒ empty session ⇒ challenged


# ── Flag on: verified principal drives current_actor ────────────────────────────


def test_logged_in_user_sees_pages_and_logout(client):
    login(client, "morgan")
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "morgan" in resp.text
    assert 'href="/logout"' in resp.text
    assert 'action="/identity"' not in resp.text  # self-declared form gone


def test_actions_stamp_the_verified_username(client, seeded):
    login(client, "morgan")
    client.cookies.set("uta_actor", "impostor")  # Phase-1 cookie must lose to the session
    ident = _identity_id(seeded, "alpha")
    resp = client.post(f"/tests/{ident}/acknowledge", follow_redirects=False)
    assert resp.status_code == 303
    with session_scope(seeded) as s:
        lc = s.scalar(select(TestLifecycle).where(TestLifecycle.test_identity_id == ident))
        assert lc.acknowledged_by == "morgan"


def test_login_redirect_stashes_return_target(client, seeded):
    ident = _identity_id(seeded, "alpha")
    resp = client.get(f"/tests/{ident}?expand=all", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
    # The asked-for page is stashed in the signed session so the callback can land the user back.
    raw = client.cookies.get("session")
    stash = json.loads(base64.b64decode(raw.split(".")[0]))
    assert stash["return_to"] == f"/tests/{ident}?expand=all"


def test_callback_return_target_rejects_offsite(client):
    from uta.web.auth import _safe_return_target

    assert _safe_return_target("/tests/7?x=1") == "/tests/7?x=1"
    assert _safe_return_target("//evil.example/") == "/"
    assert _safe_return_target("https://evil.example/") == "/"
    assert _safe_return_target(None) == "/"


def test_login_redirects_to_keycloak_with_pkce(client, monkeypatch):
    async def fake_metadata(self):
        return {"authorization_endpoint": "https://kc.example/realms/x/auth"}

    monkeypatch.setattr(StarletteOAuth2App, "load_server_metadata", fake_metadata)
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert loc.startswith("https://kc.example/realms/x/auth?")
    assert "client_id=internal-ut-analyzer" in loc
    assert "code_challenge_method=S256" in loc  # PKCE actually on, not just intended
    assert "redirect_uri=https%3A%2F%2Futa.test%2Fauth%2Fcallback" in loc
    assert "scope=openid+profile+email" in loc


# ── Flag on: logout ends the central session ────────────────────────────────────


def test_logout_clears_session_and_hits_keycloak_end_session(seeded, auth_on, monkeypatch):
    async def fake_metadata(self):
        return {"end_session_endpoint": "https://kc.example/realms/x/logout"}

    monkeypatch.setattr(StarletteOAuth2App, "load_server_metadata", fake_metadata)
    # Set before create_app: the logout route captures settings at app-construction time.
    monkeypatch.setenv("OIDC_POST_LOGOUT_REDIRECT", "https://tool.example/")
    client = TestClient(create_app(session_factory=seeded), base_url="https://uta.test")

    login(client, "morgan")
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 303
    loc = resp.headers["location"]
    assert loc.startswith("https://kc.example/realms/x/logout?")
    assert "post_logout_redirect_uri=https%3A%2F%2Ftool.example%2F" in loc
    assert "id_token_hint=fake-id-token" in loc
    # The local session is gone: the next page hit is challenged again.
    assert client.get("/", follow_redirects=False).status_code == 303
