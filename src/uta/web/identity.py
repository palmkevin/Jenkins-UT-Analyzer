"""The acting user for a request — the single choke point every write action stamps.

Two sources, one string, no data-model difference:

- **Phase-1 (default, ``AUTH_ENABLED`` off):** a self-declared name from the ``uta_actor`` browser
  cookie, falling back to the configured default (``test-user``). "No trust is implied" — an
  honesty-system label for the dev phase, deliberately not access control.
- **Phase-2 (``AUTH_ENABLED`` on):** the Keycloak-verified ``preferred_username`` from the login
  session (see :mod:`uta.web.auth`). The ``uta_actor`` cookie is **never** consulted — it is
  self-declared, so honouring it would let anyone stamp actions as anyone. The auth middleware
  guarantees a username on every non-public route; the configured default only ever shows on
  allowlisted paths (which stamp nothing).

Role/group gating is deferred; when it comes, this stays the seam.
"""

from __future__ import annotations

from fastapi import Request

from uta.config import get_settings
from uta.models import Attribution
from uta.web.auth import session_username

ACTOR_COOKIE = "uta_actor"
# The actor is stamped into String(128) *_by columns; a hand-edited cookie must not overflow them.
_ACTOR_MAX_LEN: int = Attribution.__table__.c.validated_by.type.length


def current_actor(request: Request) -> str:
    """The acting user: the verified session user when auth is on, else the self-declared cookie;
    the configured default when neither is present."""
    settings = get_settings()
    if settings.auth_enabled:
        name = session_username(request) if "session" in request.scope else ""
        return name or settings.app_default_actor
    raw = request.cookies.get(ACTOR_COOKIE)
    return (raw or "").strip()[:_ACTOR_MAX_LEN].strip() or settings.app_default_actor
