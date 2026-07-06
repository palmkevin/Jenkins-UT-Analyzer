"""Live Keycloak reachability (local-only, never in CI — see the testing contract).

Asserts the realm's OIDC discovery document exposes everything the Phase-2 auth flow relies on.
Run once the confidential client is provisioned:  pytest -m live tests/live/test_keycloak_live.py
"""

from __future__ import annotations

import httpx
import pytest

from uta.config import get_settings

pytestmark = pytest.mark.live


def test_discovery_document_supports_our_flow():
    settings = get_settings()
    resp = httpx.get(settings.oidc_server_metadata_url, timeout=10)
    resp.raise_for_status()
    meta = resp.json()

    # Endpoints the login/logout flow uses.
    assert meta["authorization_endpoint"]
    assert meta["token_endpoint"]
    assert meta["end_session_endpoint"]  # RP-initiated logout

    # Auth Code Flow + PKCE, confidential-client secret auth.
    assert "authorization_code" in meta["grant_types_supported"]
    assert "S256" in meta["code_challenge_methods_supported"]
    assert {"client_secret_basic", "client_secret_post"} & set(
        meta["token_endpoint_auth_methods_supported"]
    )

    # The "any realm user" model needs only standard claims — no custom mapper.
    assert {"openid", "profile", "email"} <= set(meta["scopes_supported"])
    assert "preferred_username" in meta["claims_supported"]
