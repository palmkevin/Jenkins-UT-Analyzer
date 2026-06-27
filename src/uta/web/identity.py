"""Phase-1 self-declared identity (PLAN §"Users & identity").

No authentication: the acting user is a plain string read from a browser cookie (``uta_actor``),
falling back to the configured default (``test-user``). Every human action — acknowledge, confirm,
attribute — is stamped with this string, and Phase-2 (Keycloak) swaps *how* the value is obtained
with **no data-model change**: the same ``actor`` field then holds the authenticated principal.

"No trust is implied" — a self-declared name is an honesty-system label for the dev phase,
deliberately not access control.
"""

from __future__ import annotations

from fastapi import Request

from uta.config import get_settings

ACTOR_COOKIE = "uta_actor"


def current_actor(request: Request) -> str:
    """The acting user for this request: the ``uta_actor`` cookie, else the configured default."""
    raw = request.cookies.get(ACTOR_COOKIE)
    name = (raw or "").strip()
    return name or get_settings().app_default_actor
