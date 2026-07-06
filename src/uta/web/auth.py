"""Phase-2 Keycloak OIDC (flag-gated: ``AUTH_ENABLED``, off by default).

Confidential client, Authorization Code Flow + PKCE, via Authlib — token exchange and ID-token
validation are the library's job, never hand-rolled. The verified ``preferred_username`` lands in
the (signed-cookie) Starlette session; :func:`uta.web.identity.current_actor` reads it from there,
so routes and the data model are untouched. With the flag off none of this is wired and the app is
byte-for-byte the Phase-1 honesty-system app.

Enforcement is a middleware, not a per-route dependency, so it fails **closed**: a future route is
protected by default and only the explicit allowlist below is public.
"""

from __future__ import annotations

from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from uta.config import Settings

# Session keys. "user" is the whole auth seam: tests seed it (a signed session cookie) instead of
# faking Authlib's network calls — the middleware and current_actor paths stay real.
SESSION_USER_KEY = "user"
SESSION_ID_TOKEN_KEY = "id_token"  # kept for RP-initiated logout's id_token_hint
SESSION_RETURN_TO_KEY = "return_to"

# Public surface when auth is on: health for monitors, the auth endpoints themselves, and the
# vendored static assets (no data behind them; keeps asset fetches out of the return-to stash).
ALLOW_PATHS = frozenset({"/health", "/login", "/auth/callback", "/logout"})
ALLOW_PREFIXES = ("/static/",)

# Sessions outlive a working day, not much more — Keycloak's SSO session makes the re-login on
# expiry a transparent redirect bounce, so short is cheap and limits cookie-replay exposure.
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60


def make_oauth(settings: Settings) -> OAuth:
    """Authlib client, self-configured from the realm's OIDC discovery document."""
    oauth = OAuth()
    oauth.register(
        name="keycloak",
        server_metadata_url=settings.oidc_server_metadata_url,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        client_kwargs={
            # preferred_username / email / name are standard claims of these scopes — no custom
            # mapper needed for the "any realm user" model.
            "scope": "openid profile email",
            "code_challenge_method": "S256",  # PKCE
        },
    )
    return oauth


def _safe_return_target(target: object) -> str:
    """A stashed return target, constrained to a same-site path (no scheme-relative ``//host``)."""
    if isinstance(target, str) and target.startswith("/") and not target.startswith("//"):
        return target
    return "/"


def register_auth_routes(app: FastAPI, oauth: OAuth, settings: Settings) -> None:
    @app.get("/login")
    async def login(request: Request):
        # url_for honors X-Forwarded-* (uvicorn --proxy-headers), so behind Traefik this is the
        # externally-registered https callback, not the container-internal address.
        redirect_uri = str(request.url_for("auth_callback"))
        return await oauth.keycloak.authorize_redirect(request, redirect_uri)

    @app.get("/auth/callback", name="auth_callback")
    async def auth_callback(request: Request):
        # Exchanges the code AND validates the ID token (issuer/audience/signature/expiry).
        token = await oauth.keycloak.authorize_access_token(request)
        claims = token.get("userinfo") or {}
        request.session[SESSION_USER_KEY] = {
            "sub": claims.get("sub", ""),
            "preferred_username": claims.get("preferred_username", ""),
            "email": claims.get("email", ""),
            "name": claims.get("name", ""),
        }
        request.session[SESSION_ID_TOKEN_KEY] = token.get("id_token", "")
        target = _safe_return_target(request.session.pop(SESSION_RETURN_TO_KEY, None))
        return RedirectResponse(target, status_code=303)

    @app.get("/logout")
    async def logout(request: Request):
        # RP-initiated logout: clear our session, then end the *central* Keycloak session too —
        # otherwise the next /login silently signs the "logged-out" user straight back in.
        id_token = request.session.pop(SESSION_ID_TOKEN_KEY, "")
        request.session.clear()
        metadata = await oauth.keycloak.load_server_metadata()
        post_logout = settings.oidc_post_logout_redirect or str(request.base_url)
        end_session = metadata.get("end_session_endpoint")
        if not end_session:
            return RedirectResponse(post_logout, status_code=303)
        params = {
            "post_logout_redirect_uri": post_logout,
            "client_id": settings.oidc_client_id,
        }
        if id_token:
            # Skips Keycloak's "do you want to log out?" confirmation page.
            params["id_token_hint"] = id_token
        return RedirectResponse(f"{end_session}?{urlencode(params)}", status_code=303)


def install_auth_middleware(app: FastAPI) -> None:
    """Require a logged-in session everywhere except the allowlist (installed only when auth is on).

    Browser GETs bounce to ``/login`` with the asked-for page stashed so the callback can land the
    user back where they started; non-GETs get a plain 401 (a redirected POST would lose its body
    anyway, and a 401 is honest to HTMX/scripts).
    """

    @app.middleware("http")
    async def require_auth(request: Request, call_next):
        path = request.url.path
        if (
            path in ALLOW_PATHS
            or path.startswith(ALLOW_PREFIXES)
            or request.session.get(SESSION_USER_KEY)
        ):
            return await call_next(request)
        if request.method == "GET":
            query = request.url.query
            request.session[SESSION_RETURN_TO_KEY] = path + (f"?{query}" if query else "")
            return RedirectResponse("/login", status_code=303)
        return PlainTextResponse("authentication required", status_code=401)
