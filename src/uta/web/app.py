"""Dashboard web app — opens on the triage queue.

Surfaces:
- ``GET /``                         the daily triage queue, the primary landing view.
- ``GET /tests/{identity_id}``      the per-test record with the full evidence + actions.
- ``GET /runs/{build}``             the run-level summary: totals, shards, baseline + diff.
- action POSTs (acknowledge / confirm / attribute / identity) → redirect back (PRG).

Route handlers stay thin: read-side projections live in :mod:`uta.web.views`, write-side mutations
in :mod:`uta.web.actions`. Both return detached data / commit via ``session_scope`` so templates
never touch a live session (the Slice-0 pattern).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from uta.clients import build_email_sender
from uta.config import Settings, get_settings
from uta.control import jobs
from uta.control.health import check_health
from uta.control.tunables import clear_override, effective_settings, load_overrides, set_override
from uta.db import assert_pg_trgm, make_engine, make_session_factory, session_scope
from uta.delivery.email import EmailSender
from uta.models.enums import PredictedCause, TriageStatus
from uta.web import actions, control, views
from uta.web.auth import (
    SESSION_MAX_AGE_SECONDS,
    install_auth_middleware,
    make_oauth,
    register_auth_routes,
)
from uta.web.identity import ACTOR_COOKIE, current_actor

_WEB_DIR = Path(__file__).parent
_TEMPLATES = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
_STATIC_DIR = _WEB_DIR / "static"


def format_ts(value: object) -> str:
    """Render a timestamp to seconds precision as ordinary, wrappable text (issue #35).

    Drops the sub-second component and the ``+00:00`` tz suffix that ``datetime.__str__``
    emits (the app normalizes to UTC, so bare wall-clock seconds is what's wanted). Returns
    ``"—"`` for ``None`` so every render site can drop its own ``or "—"`` fallback. Non-datetime
    values fall through to ``str`` unchanged.
    """
    if value is None:
        return "—"
    strftime = getattr(value, "strftime", None)
    if strftime is None:
        return str(value)
    return strftime("%Y-%m-%d %H:%M:%S")


def format_duration(value: object) -> str:
    """Render a duration in seconds as compact ``Hh Mm Ss`` text (issue #37).

    Drops leading zero units (``90`` → ``1m 30s``, ``5`` → ``5s``); ``None`` renders as ``"—"``.
    Non-numeric values fall through to ``str`` unchanged.
    """
    if value is None:
        return "—"
    if not isinstance(value, (int, float)):
        return str(value)
    total = int(value)
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


_TEMPLATES.env.filters["ts"] = format_ts
_TEMPLATES.env.filters["duration"] = format_duration


def _expanded(request: Request) -> list[str]:
    """Sections the reader asked to render in full — the ``?expand=a,b`` query param (issue #19).

    A capped section's "Load all N Tests" link points back with its key added here, so the same
    page re-renders that one bucket in full while the rest stay capped.
    """
    raw = request.query_params.get("expand", "")
    return [s for s in raw.split(",") if s]


_TRIAGE_FILTER_KEYS = ("owner", "suite", "track", "cause", "triage_status", "flaky")


def _triage_filters(request: Request) -> dict[str, str]:
    """The triage queue's filter-bar state (issue #63) — query params, so it's bookmarkable and
    survives an action's Post/Redirect/Get round trip via the referer header."""
    return {k: v for k, v in request.query_params.items() if k in _TRIAGE_FILTER_KEYS and v}


def create_app(session_factory=None, *, email_sender: EmailSender | None = None) -> FastAPI:
    startup_engine = None
    if session_factory is None:
        settings = get_settings()
        startup_engine = make_engine(settings.database_url)
        session_factory = make_session_factory(startup_engine)
        # Ops alerts (/health staleness, issue #51) ride the same SMTP seam as the regression
        # report; ``None`` when email isn't configured. Tests inject a recording sender instead.
        email_sender = build_email_sender(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Fail fast if the DB skipped migrations — deferred to startup so import doesn't connect
        # (tests inject a session_factory, leaving startup_engine None, and never hit this).
        if startup_engine is not None:
            assert_pg_trgm(startup_engine)
        # On-demand ingest jobs run in *this process's* daemon threads, so any QUEUED/RUNNING row
        # found at startup was orphaned by a restart — flip it to ERROR instead of letting it lie
        # to the control panel forever (issue #51).
        jobs.recover_orphaned_jobs(session_factory)
        yield

    app = FastAPI(title="Jenkins UT Analyzer", lifespan=lifespan)

    # Vendored front-end assets (Bootstrap CSS). Served locally — no CDN / runtime network
    # dependency, in keeping with the self-contained, offline-first design.
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ── Phase-2 auth (Keycloak OIDC, issue #17) — wired only when AUTH_ENABLED ────────────────
    # Flag off (default): none of this exists and the app is the Phase-1 honesty-system app.
    auth_settings = get_settings()
    if auth_settings.auth_enabled:
        if not auth_settings.session_secret:
            raise ValueError("AUTH_ENABLED=true requires SESSION_SECRET to be set")
        register_auth_routes(app, make_oauth(auth_settings), auth_settings)
        install_auth_middleware(app)
        # Added last ⇒ outermost, so request.session exists by the time require_auth runs.
        app.add_middleware(
            SessionMiddleware,
            secret_key=auth_settings.session_secret,
            same_site="lax",
            https_only=True,  # TLS terminates at Traefik; the cookie never travels in clear
            max_age=SESSION_MAX_AGE_SECONDS,
        )

    def effective(s) -> Settings:
        """Env settings with the DB threshold overrides applied — the live view of the tunables."""
        return effective_settings(get_settings(), load_overrides(s))

    def render(
        request: Request, template: str, context: dict, *, cfg: Settings | None = None
    ) -> HTMLResponse:
        cfg = cfg or get_settings()
        context = {
            **context,
            "actor": current_actor(request),
            "auth_enabled": get_settings().auth_enabled,
            "jira_base_url": cfg.jira_base_url,
            "fisheye_changelog_url": cfg.fisheye_changelog_url,
            "zephyr_test_case_url_prefix": cfg.zephyr_test_case_url_prefix,
            "expand": _expanded(request),
            "row_limit": cfg.ui_row_limit,
        }
        return _TEMPLATES.TemplateResponse(request, template, context)

    def back(request: Request, fallback: str = "/") -> RedirectResponse:
        # Post/Redirect/Get: bounce back to the page the action came from.
        target = request.headers.get("referer") or fallback
        return RedirectResponse(target, status_code=303)

    @app.get("/health")
    def health() -> JSONResponse:
        # Real health (issue #51): DB ping + poller-heartbeat freshness. 503 lets an external
        # monitor page on a dead DB or a poller with no successful tick in N intervals; a
        # deployment that runs no poller (demo, web-only) reports poller "never" and stays 200.
        cfg = get_settings()
        report = check_health(
            session_factory,
            cfg,
            email_sender=email_sender,
            email_recipients=cfg.email_recipients,
        )
        return JSONResponse(report.payload(), status_code=200 if report.ok else 503)

    @app.get("/", response_class=HTMLResponse)
    def triage(request: Request, sort: str = ""):
        filters = _triage_filters(request)
        with session_scope(session_factory) as s:
            cfg = effective(s)
            queue = views.triage_queue(
                s,
                recently_fixed_days=cfg.recently_fixed_days,
                limit=cfg.ui_row_limit,
                expand=_expanded(request),
                filters=filters,
                sort=sort or None,
            )
            options = views.triage_filter_options(s)
        options["tracks"] = ["permanent", "permanent_py39"]
        options["causes"] = list(PredictedCause)
        options["triage_statuses"] = list(TriageStatus)
        return render(
            request,
            "triage.html",
            {"queue": queue, "filters": filters, "sort": sort, "options": options},
            cfg=cfg,
        )

    @app.get("/tests/{identity_id}", response_class=HTMLResponse)
    def test_record(request: Request, identity_id: int):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            record = views.test_record(
                s,
                identity_id,
                flaky_window_days=cfg.flaky_window_days,
                flaky_threshold=cfg.flaky_transition_threshold,
                kb_top_k=cfg.kb_top_k,
                kb_cutoff=cfg.pgtrgm_similarity_cutoff,
            )
        return render(
            request, "test_record.html", {"record": record, "identity_id": identity_id}, cfg=cfg
        )

    @app.get("/runs", response_class=HTMLResponse)
    def runs_view(request: Request, page: int = 1):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            runs = views.job_runs(
                s,
                poll_interval_seconds=cfg.poll_interval_seconds,
                limit=cfg.ui_row_limit,
                page=page,
            )
        return render(request, "runs.html", {"runs": runs}, cfg=cfg)

    @app.get("/runs/{build}", response_class=HTMLResponse)
    def run_view(request: Request, build: int, page: int = 1, failures_only: bool = False):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            run = views.run_summary(
                s, build, limit=cfg.ui_row_limit, page=page, failures_only=failures_only
            )
        return render(request, "run.html", {"run": run, "build": build}, cfg=cfg)

    @app.get("/flaky", response_class=HTMLResponse)
    def flaky_view(request: Request):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            board = views.flaky_leaderboard(
                s,
                window_days=cfg.flaky_window_days,
                threshold=cfg.flaky_transition_threshold,
            )
        return render(request, "flaky.html", {"board": board}, cfg=cfg)

    @app.get("/kb", response_class=HTMLResponse)
    def kb_view(request: Request, q: str = ""):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            results = views.kb_search(s, q, cutoff=cfg.pgtrgm_similarity_cutoff)
        return render(request, "kb.html", {"kb": results}, cfg=cfg)

    @app.get("/search", response_class=HTMLResponse)
    def search_view(request: Request, q: str = ""):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            results = views.test_search(s, q, limit=cfg.ui_row_limit)
        # A unique match jumps straight to the record; the navbar box is a "go to test" shortcut.
        if len(results) == 1:
            return RedirectResponse(f"/tests/{results[0]['identity_id']}", status_code=303)
        return render(request, "search.html", {"query": q, "results": results}, cfg=cfg)

    # ── Control panel (issue #16) ────────────────────────────────────────────
    # Access is deliberately open for now (honesty system, no auth anywhere yet). These handlers are
    # the single choke point to gate once auth lands — guard them here, not per-call.
    @app.get("/control", response_class=HTMLResponse)
    def control_view(request: Request, error: str = ""):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            panel = control.control_panel(s, get_settings(), error=error or None)
        return render(request, "control.html", {"panel": panel}, cfg=cfg)

    @app.get("/control/jobs", response_class=HTMLResponse)
    def control_jobs_fragment(request: Request):
        # The HTMX poll target (issue #78): just the ingest-jobs table, re-fetched every few
        # seconds while a job is QUEUED/RUNNING. The partial drops its own hx-trigger once all
        # jobs are terminal, so polling stops without any client-side state.
        with session_scope(session_factory) as s:
            ctx = control.jobs_panel(s)
        return _TEMPLATES.TemplateResponse(request, "_control_jobs.html", ctx)

    @app.post("/control/settings")
    def set_setting(request: Request, key: str = Form(...), value: str = Form("")):
        # Empty value ⇒ revert to the env default; a value ⇒ validated override.
        try:
            with session_scope(session_factory) as s:
                if value.strip() == "":
                    clear_override(s, key)
                else:
                    set_override(s, key, value, actor=current_actor(request))
        except ValueError as exc:
            return RedirectResponse(f"/control?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/control", status_code=303)

    @app.post("/control/settings/{key}/reset")
    def reset_setting(request: Request, key: str):
        with session_scope(session_factory) as s:
            clear_override(s, key)
        return RedirectResponse("/control", status_code=303)

    @app.post("/control/ingest")
    def trigger_ingest(request: Request, build_start: int = Form(...), build_end: str = Form("")):
        try:
            end = int(build_end) if build_end.strip() else build_start
        except ValueError:
            return RedirectResponse(
                f"/control?error={quote('Build range must be numeric')}", status_code=303
            )
        with session_scope(session_factory) as s:
            cfg = effective(s)
        jobs.trigger_ingest(
            session_factory,
            build_start=build_start,
            build_end=end,
            settings=cfg,
            actor=current_actor(request),
        )
        return RedirectResponse("/control", status_code=303)

    # ── Actions (Post/Redirect/Get) ──────────────────────────────────────────
    @app.post("/identity")
    def set_identity(request: Request, actor: str = Form("")):
        resp = back(request)
        name = actor.strip()
        if name:
            resp.set_cookie(ACTOR_COOKIE, name, max_age=60 * 60 * 24 * 365, samesite="lax")
        else:
            resp.delete_cookie(ACTOR_COOKIE)
        return resp

    # Literal-path bulk routes are registered before their `{id}`-parametrized siblings — FastAPI
    # matches routes in registration order, so `/tests/bulk/acknowledge` must win over
    # `/tests/{identity_id}/acknowledge` (which would otherwise swallow it with identity_id="bulk").
    @app.post("/tests/bulk/acknowledge")
    async def bulk_acknowledge(request: Request):
        form = await request.form()
        identity_ids = [int(v) for v in form.getlist("identity_ids")]
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.bulk_acknowledge(s, identity_ids, actor)
        return back(request)

    @app.post("/tests/{identity_id}/acknowledge")
    def acknowledge(request: Request, identity_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.acknowledge(s, identity_id, actor)
        return back(request)

    @app.post("/signatures/{signature_id}/acknowledge")
    def acknowledge_signature(request: Request, signature_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.acknowledge_by_signature(s, signature_id, actor)
        return back(request)

    @app.post("/episodes/bulk/attribute")
    async def bulk_attribute(request: Request):
        form = await request.form()
        episode_ids = [int(v) for v in form.getlist("episode_ids")]
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.bulk_set_attribution(
                s,
                episode_ids,
                actor,
                causing_person=str(form.get("causing_person", "")),
                reason_text=str(form.get("reason_text", "")),
                triage_status=str(form.get("triage_status", "")) or None,
            )
        return back(request)

    @app.post("/episodes/{episode_id}/confirm")
    def confirm(request: Request, episode_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.confirm(s, episode_id, actor)
        return back(request)

    @app.post("/episodes/{episode_id}/attribute")
    def attribute(
        request: Request,
        episode_id: int,
        causing_person: str = Form(""),
        reason_text: str = Form(""),
        triage_status: str = Form(""),
        jira_ticket: str = Form(""),
    ):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.set_attribution(
                s,
                episode_id,
                actor,
                causing_person=causing_person,
                reason_text=reason_text,
                triage_status=triage_status or None,
                jira_ticket=jira_ticket,
            )
        return back(request)

    return app


app = create_app()
