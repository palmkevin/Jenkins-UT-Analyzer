"""One-shot flash messages across the Post/Redirect/Get bounce (issue #75).

Every mutating POST 303-redirects back to the page it came from; its confirmation rides a
short-lived cookie set on the redirect response and **deleted by the very next page render**, so a
reload never re-shows it (a query param would stick in the address bar and re-fire on refresh).
Two variants: ``success`` (the default) and ``error`` — rendered by ``base.html`` as a dismissible
alert at the top of ``<main>``, so every page gets it for free.

The payload is URL-quoted JSON: quoting keeps the cookie value ASCII-safe (messages carry arrows,
dashes and user input), JSON keeps message + category one atomic value.
"""

from __future__ import annotations

import json
from urllib.parse import quote, unquote

from fastapi import Request, Response

FLASH_COOKIE = "uta_flash"
# Belt-and-braces: a flash that never gets rendered (redirect to a JSON page, abandoned tab)
# expires on its own instead of surprising the user minutes later.
_MAX_AGE_SECONDS = 60


def set_flash(response: Response, message: str, category: str = "success") -> None:
    """Attach a one-shot ``message`` to a redirect response (``category``: success | error)."""
    payload = quote(json.dumps({"message": message, "category": category}))
    response.set_cookie(FLASH_COOKIE, payload, max_age=_MAX_AGE_SECONDS, samesite="lax")


def get_flash(request: Request) -> dict | None:
    """The pending flash carried by the request, or None. Malformed cookies read as None."""
    raw = request.cookies.get(FLASH_COOKIE)
    if raw is None:
        return None
    try:
        data = json.loads(unquote(raw))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not data.get("message"):
        return None
    return {"message": str(data["message"]), "category": str(data.get("category", "success"))}


def clear_flash(response: Response) -> None:
    """Delete the flash cookie — called by the render that displayed (or rejected) it."""
    response.delete_cookie(FLASH_COOKIE)
