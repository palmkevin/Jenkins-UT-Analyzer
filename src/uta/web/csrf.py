"""App-wide cross-site write guard (CSRF, issue #88).

Every state-changing POST (control panel, triage actions, ``/identity``) was forgeable: with
``AUTH_ENABLED=false`` — the default and the current production posture — a malicious external
page could auto-submit a form to any of them from an intranet user's browser, and the change would
land stamped as that user's declared actor. Even auth-on only mitigated this incidentally (the
``SameSite=Lax`` session cookie).

The guard is **header-based, not token-based** — the "resource isolation" pattern built on browser
fetch metadata rather than a synchronizer token:

- ``Sec-Fetch-Site`` present (every current browser engine sends it, on every request): allow only
  ``same-origin`` and ``none`` (direct navigation); reject ``cross-site`` / ``same-site`` with 403.
- else ``Origin`` present (older browsers still send it on cross-origin POSTs): reject when its
  host:port doesn't match the request ``Host``.
- neither present: allow. Only non-browser clients (curl, scripts, the offline TestClient) omit
  both, and CSRF is a *browser* attack — a forged cross-site form post from any modern browser
  always carries the evidence above.

Why not tokens: a token needs plumbing through every template and HTMX request plus somewhere to
keep server state or a signed cookie — and a cookie-tied token can't work in auth-off mode, where
there is no session at all. The header check needs neither, behaves identically with the auth flag
on or off, and leaves the existing header-less test clients untouched.

Scope: unsafe methods only (POST/PUT/PATCH/DELETE); GET/HEAD pass through, so the auth-on OIDC
redirect dance (``/login`` → Keycloak → ``/auth/callback``, all GETs) is unaffected.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Sec-Fetch-Site values that may mutate: the page itself, or a direct (non-site-initiated)
# request. `same-site` (a sibling subdomain) is deliberately *not* trusted — nothing legitimate
# posts from one.
_ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})


def _is_cross_site(request: Request) -> bool:
    """Browser-provided evidence that this request was initiated by another site."""
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site.lower() not in _ALLOWED_FETCH_SITES
    origin = request.headers.get("origin")
    if origin is not None:
        # `Origin: null` (sandboxed iframe, data: URL, …) has an empty netloc ⇒ mismatch ⇒ reject.
        return urlsplit(origin).netloc.lower() != request.headers.get("host", "").lower()
    return False  # no browser evidence ⇒ non-browser client ⇒ not a CSRF vector


def install_csrf_middleware(app: FastAPI) -> None:
    """Reject cross-site unsafe-method requests app-wide with a 403 (see module docstring)."""

    @app.middleware("http")
    async def reject_cross_site_writes(request: Request, call_next):
        if request.method in UNSAFE_METHODS and _is_cross_site(request):
            return PlainTextResponse("cross-site request rejected", status_code=403)
        return await call_next(request)
