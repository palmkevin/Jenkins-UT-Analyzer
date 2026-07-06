"""The acting user for a request — the single choke point every write action stamps.

Two sources, one string, no data-model difference:

- **Phase-1 (default, ``AUTH_ENABLED`` off):** a self-declared name from the ``uta_actor`` browser
  cookie, falling back to the configured default (``test-user``). "No trust is implied" — an
  honesty-system label for the dev phase, deliberately not access control.
- **Phase-2 (``AUTH_ENABLED`` on):** the Keycloak-verified ``preferred_username`` from the login
  session (see :mod:`uta.web.auth`). The auth middleware guarantees a session on every non-public
  route, so the Phase-1 fallback below only ever fires on allowlisted paths (which stamp nothing).

Role/group gating is deferred; when it comes, this stays the seam.
"""

from __future__ import annotations

from fastapi import Request

from uta.config import get_settings
from uta.web.auth import SESSION_USER_KEY

ACTOR_COOKIE = "uta_actor"


def current_actor(request: Request) -> str:
    """The acting user for this request: verified session user, else cookie, else the default."""
    settings = get_settings()
    if settings.auth_enabled and "session" in request.scope:
        user = request.session.get(SESSION_USER_KEY) or {}
        name = (user.get("preferred_username") or "").strip()
        if name:
            return name
    raw = request.cookies.get(ACTOR_COOKIE)
    return (raw or "").strip() or settings.app_default_actor
