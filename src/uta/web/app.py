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

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from starlette.middleware.sessions import SessionMiddleware

from uta.clients import build_email_sender
from uta.config import Settings, get_settings
from uta.control import jobs
from uta.control.health import check_health
from uta.control.tunables import (
    TUNABLES_BY_KEY,
    clear_override,
    effective_settings,
    load_overrides,
    set_override,
)
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
from uta.web.csrf import install_csrf_middleware
from uta.web.flash import FLASH_COOKIE, clear_flash, get_flash, set_flash
from uta.web.identity import ACTOR_COOKIE, current_actor

_WEB_DIR = Path(__file__).parent
_TEMPLATES = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
_STATIC_DIR = _WEB_DIR / "static"


def _ts_text(value: datetime) -> str:
    """The plain-text timestamp form: seconds precision plus an explicit ``UTC`` label.

    The app normalizes every stored instant to UTC, but readers are in Luxembourg (UTC+1/+2), so
    an unlabelled wall-clock string is silently ambiguous (issue #144). Used for the visible text
    of :func:`format_ts` and for hover ``title`` attributes (:func:`format_reltime`).
    """
    return value.strftime("%Y-%m-%d %H:%M:%S") + " UTC"


def format_ts(value: object) -> str:
    """Render a timestamp to seconds precision, explicitly labelled ``UTC`` (issues #35, #144).

    Drops the sub-second component; the visible text ends in `` UTC`` and the wrapping ``<span>``
    carries the full ISO-8601 form (with offset) in its hover ``title``. Naive datetimes are
    treated as UTC (SQLite drops tzinfo; the app normalizes to UTC). Returns ``"—"`` for ``None``
    so every render site can drop its own ``or "—"`` fallback. Non-datetime values fall through
    to ``str`` unchanged.
    """
    if value is None:
        return "—"
    if not isinstance(value, datetime):
        return str(value)
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    iso = aware.isoformat(timespec="seconds")
    return Markup(f'<span title="{escape(iso)}">{escape(_ts_text(value))}</span>')


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


def _relative_text(seconds: float) -> str:
    """``seconds`` of age → coarse human text ("3 h ago"); negative means a future time."""
    future = seconds < 0
    seconds = abs(seconds)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        n, unit = int(seconds // 60), "min"
    elif seconds < 86400:
        n, unit = int(seconds // 3600), "h"
    else:
        n = int(seconds // 86400)
        unit = "day" if n == 1 else "days"
    return f"in {n} {unit}" if future else f"{n} {unit} ago"


def format_reltime(value: object) -> str:
    """Render a timestamp as relative age with the absolute form in a hover title (issue #79).

    ``<span title="2026-06-29 16:15:46 UTC">2 days ago</span>`` — server-side, no JS. Applied where
    *age* is what the reader cares about (triage first-failed/fixed-at, test-record lifecycle and
    episode times); tabular run listings stay absolute via ``|ts``. ``None`` renders as ``"—"``
    and non-datetimes fall through to ``str``, mirroring :func:`format_ts`.
    """
    if value is None:
        return "—"
    if not isinstance(value, datetime):
        return str(value)
    # SQLite (offline tests) drops tzinfo; the app normalizes to UTC, so treat naive as UTC.
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    age = (datetime.now(UTC) - aware).total_seconds()
    return Markup(f'<span title="{escape(_ts_text(value))}">{escape(_relative_text(age))}</span>')


_TEMPLATES.env.filters["ts"] = format_ts
_TEMPLATES.env.filters["duration"] = format_duration
_TEMPLATES.env.filters["reltime"] = format_reltime


def nav_section(path: str) -> str | None:
    """Which navbar entry a request path belongs to, for the active-link highlight (issue #79).

    Test-record pages count as Triage (they're the queue's drill-down); ``/search`` and unknown
    paths highlight nothing.
    """
    if path == "/" or path.startswith("/tests"):
        return "triage"
    if path.startswith("/runs"):
        return "runs"
    if path.startswith("/flaky"):
        return "flaky"
    if path.startswith("/kb"):
        return "kb"
    if path.startswith("/control"):
        return "control"
    return None


def _expanded(request: Request) -> list[str]:
    """Sections the reader asked to render in full — the ``?expand=a,b`` query param (issue #19).

    A capped section's "Load all N Tests" link points back with its key added here, so the same
    page re-renders that one bucket in full while the rest stay capped.
    """
    raw = request.query_params.get("expand", "")
    return [s for s in raw.split(",") if s]


def _n(count: int, noun: str) -> str:
    """``3 tests`` / ``1 test`` — count-bearing flash messages without pluralization typos."""
    return f"{count} {noun}{'' if count == 1 else 's'}"


# In-page anchors appended to PRG redirects (issue #143) — a bare fragment id like "episode-3".
# Fragments never reach the server (browsers strip them from Referer), so actions that should land
# on a specific card pass the id explicitly via a hidden form field, validated against this.
_ANCHOR_RE = re.compile(r"[A-Za-z0-9_-]+")


def _same_origin_path(raw: str | None) -> str | None:
    """Validate user-controllable URL input (``?return=`` / a reduced Referer) as a same-origin
    relative path — the only thing the app may redirect to or emit as a back-link (issue #143).

    Accepts an absolute-path reference only: no scheme, no authority (which also kills the
    scheme-relative ``//host`` form), a leading ``/``, and no backslash anywhere (browsers
    normalize ``\\`` to ``/``, so ``/\\host`` would turn scheme-relative client-side). Anything
    else yields ``None`` and the caller falls back to a known-safe URL.
    """
    if not raw:
        return None
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc:
        return None
    path = parts.path
    if not path.startswith("/") or "\\" in path:
        return None
    return f"{path}?{parts.query}" if parts.query else path


def _referer_path(request: Request) -> str | None:
    """The Referer header reduced to a validated same-origin relative path (or ``None``).

    Browsers send an absolute Referer; only its path + query are kept — scheme and host are
    discarded, not trusted — so a PRG bounce can never leave the app whatever the header claims.
    """
    raw = request.headers.get("referer")
    if not raw:
        return None
    parts = urlsplit(raw)
    rel = f"{parts.path}?{parts.query}" if parts.query else parts.path
    return _same_origin_path(rel)


_TRIAGE_FILTER_KEYS = ("owner", "suite", "track", "cause", "triage_status", "flaky")


def _triage_filters(request: Request) -> dict[str, str]:
    """The triage queue's filter-bar state (issue #63) — query params, so it's bookmarkable and
    survives an action's Post/Redirect/Get round trip via the referer header."""
    return {k: v for k, v in request.query_params.items() if k in _TRIAGE_FILTER_KEYS and v}


def create_app(
    session_factory=None, *, email_sender: EmailSender | None = None, demo_mode: bool = False
) -> FastAPI:
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

    # CSRF guard (issue #88) — unconditional, because it must hold in auth-off mode too (auth-on's
    # SameSite=Lax cookie only mitigated cross-site POSTs incidentally). Added after the auth block
    # ⇒ outermost, so cross-site writes are rejected even on auth-exempt paths; it never reads the
    # session, so sitting outside SessionMiddleware is fine. See uta.web.csrf for the design.
    install_csrf_middleware(app)

    def effective(s) -> Settings:
        """Env settings with the DB threshold overrides applied — the live view of the tunables."""
        return effective_settings(get_settings(), load_overrides(s))

    def render(
        request: Request, template: str, context: dict, *, cfg: Settings | None = None
    ) -> HTMLResponse:
        cfg = cfg or get_settings()
        # The navbar badge shows the live unacknowledged-new count on every page — one cheap
        # COUNT query, not the whole triage projection (issue #79).
        with session_scope(session_factory) as s:
            triage_new_count = views.new_failing_count(s)
        context = {
            **context,
            "nav_active": nav_section(request.url.path),
            "triage_new_count": triage_new_count,
            "actor": current_actor(request),
            "auth_enabled": get_settings().auth_enabled,
            "jira_base_url": cfg.jira_base_url,
            "fisheye_changelog_url": cfg.fisheye_changelog_url,
            "zephyr_test_case_url_prefix": cfg.zephyr_test_case_url_prefix,
            "row_limit": cfg.ui_row_limit,
            "flash": get_flash(request),
        }
        response = _TEMPLATES.TemplateResponse(request, template, context)
        # One-shot: the render that displayed the flash deletes its cookie, so a reload is clean.
        if FLASH_COOKIE in request.cookies:
            clear_flash(response)
        return response

    def back(request: Request, fallback: str = "/", *, anchor: str = "") -> RedirectResponse:
        # Post/Redirect/Get: bounce back to the page the action came from. Only the referer's
        # path + query are used — never its scheme/host — so the redirect can't leave the app
        # (a crafted absolute referer degrades to its path, an unusable one to the fallback).
        # `anchor` optionally appends a `#fragment` so the browser lands on the acted-on card
        # (issue #143); it's validated because it, too, arrives as request input.
        target = _referer_path(request) or fallback
        if anchor and _ANCHOR_RE.fullmatch(anchor):
            target = f"{target}#{anchor}"
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
        expand = _expanded(request)
        with session_scope(session_factory) as s:
            cfg = effective(s)
            queue = views.triage_queue(
                s,
                recently_fixed_days=cfg.recently_fixed_days,
                limit=cfg.ui_row_limit,
                expand=expand,
                filters=filters,
                sort=sort or None,
            )
            options = views.triage_filter_options(s)
            last_run = views.latest_run(s)
        options["tracks"] = ["permanent", "permanent_py39"]
        options["causes"] = list(PredictedCause)
        options["triage_statuses"] = list(TriageStatus)
        # Record links carry the queue's URL-encoded state as ?return=, so the record page's
        # back-link restores this exact filtered/sorted view (issue #143). Empty on the plain
        # queue — the record's back-link already defaults to "/".
        queue_url = views.triage_url(filters, sort or None)
        return render(
            request,
            "triage.html",
            {
                "queue": queue,
                "filters": filters,
                "sort": sort,
                "options": options,
                "last_run": last_run,
                "chips": views.triage_filter_chips(filters, sort or None),
                "sort_links": views.triage_sort_links(filters, sort or None),
                "expand_urls": views.triage_expand_urls(filters, sort or None, expand),
                "return_qs": quote(queue_url, safe="") if queue_url != "/" else "",
            },
            cfg=cfg,
        )

    @app.get("/tests/{identity_id}", response_class=HTMLResponse)
    def test_record(request: Request, identity_id: int):
        # The breadcrumb's back target (issue #143): the referring triage-queue URL carried in
        # ?return= (sanitized — same-origin relative paths only), else the plain queue.
        back_url = _same_origin_path(request.query_params.get("return")) or "/"
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
            request,
            "test_record.html",
            {"record": record, "identity_id": identity_id, "back_url": back_url},
            cfg=cfg,
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
    #
    # Demo lockdown (issue #89): the public demo serves anonymous visitors off one shared store, so
    # its control-panel *mutations* are refused — a settings override degrades every other visitor's
    # view, and an on-demand ingest would build a real Jenkins client and send outbound requests
    # from a public host. The panel itself still renders; triage actions stay live (the store is
    # ephemeral and they're part of the demo story).
    def demo_locked() -> PlainTextResponse | None:
        if not demo_mode:
            return None
        return PlainTextResponse(
            "This action is disabled in the public demo — the control panel is read-only here.",
            status_code=403,
        )

    @app.get("/control", response_class=HTMLResponse)
    def control_view(request: Request):
        with session_scope(session_factory) as s:
            cfg = effective(s)
            panel = control.control_panel(s, get_settings())
        return render(request, "control.html", {"panel": panel, "demo_mode": demo_mode}, cfg=cfg)

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
        if (locked := demo_locked()) is not None:
            return locked
        # Empty value ⇒ revert to the env default; a value ⇒ validated override.
        resp = RedirectResponse("/control", status_code=303)
        tunable = TUNABLES_BY_KEY.get(key)
        label = tunable.label if tunable else key
        try:
            with session_scope(session_factory) as s:
                # The pre-change effective value, for a "was X" message (whitelisted keys only —
                # never getattr an arbitrary submitted key, that could echo a secret).
                old = getattr(effective(s), key) if tunable else None
                if value.strip() == "":
                    clear_override(s, key)
                    default = getattr(get_settings(), key) if tunable else None
                    set_flash(resp, f"{label} reverted to its env default ({default})")
                else:
                    set_override(s, key, value, actor=current_actor(request))
                    set_flash(resp, f"{label} overridden: {old} → {tunable.coerce(value)}")
        except ValueError as exc:
            set_flash(resp, str(exc), "error")
        return resp

    @app.post("/control/settings/{key}/reset")
    def reset_setting(request: Request, key: str):
        if (locked := demo_locked()) is not None:
            return locked
        with session_scope(session_factory) as s:
            clear_override(s, key)
        resp = RedirectResponse("/control", status_code=303)
        tunable = TUNABLES_BY_KEY.get(key)
        if tunable is not None:
            default = getattr(get_settings(), key)
            set_flash(resp, f"{tunable.label} reverted to its env default ({default})")
        else:
            set_flash(resp, f"{key!r} is not an overridable setting", "error")
        return resp

    @app.post("/control/ingest")
    def trigger_ingest(request: Request, build_start: int = Form(...), build_end: str = Form("")):
        if (locked := demo_locked()) is not None:
            return locked
        resp = RedirectResponse("/control", status_code=303)
        try:
            end = int(build_end) if build_end.strip() else build_start
        except ValueError:
            set_flash(resp, "Build range must be numeric", "error")
            return resp
        with session_scope(session_factory) as s:
            cfg = effective(s)
        job_id = jobs.trigger_ingest(
            session_factory,
            build_start=build_start,
            build_end=end,
            settings=cfg,
            actor=current_actor(request),
        )
        builds = f"build #{build_start}" if end == build_start else f"builds #{build_start}–#{end}"
        set_flash(resp, f"Ingest job #{job_id} queued for {builds}")
        return resp

    # ── Actions (Post/Redirect/Get) ──────────────────────────────────────────
    @app.post("/identity")
    def set_identity(request: Request, actor: str = Form("")):
        resp = back(request)
        name = actor.strip()
        if name:
            resp.set_cookie(ACTOR_COOKIE, name, max_age=60 * 60 * 24 * 365, samesite="lax")
            set_flash(resp, f"Now acting as {name}")
        else:
            resp.delete_cookie(ACTOR_COOKIE)
            set_flash(resp, "Acting identity cleared — back to the default actor")
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
            count = actions.bulk_acknowledge(s, identity_ids, actor)
        resp = back(request)
        if count:
            set_flash(resp, f"Acknowledged {_n(count, 'selected test')}")
        else:
            set_flash(resp, "Nothing acknowledged — no tests selected", "error")
        return resp

    @app.post("/tests/{identity_id}/acknowledge")
    def acknowledge(request: Request, identity_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            ok = actions.acknowledge(s, identity_id, actor)
        resp = back(request)
        if ok:
            set_flash(resp, "Test acknowledged — moved to the Still-failing bucket")
        else:
            set_flash(resp, "Nothing acknowledged — the test has never failed", "error")
        return resp

    @app.post("/signatures/{signature_id}/acknowledge")
    def acknowledge_signature(request: Request, signature_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            count = actions.acknowledge_by_signature(s, signature_id, actor)
        resp = back(request)
        if count:
            set_flash(resp, f"Acknowledged {_n(count, 'test')} sharing this failure signature")
        else:
            set_flash(resp, "No unacknowledged failing tests share this signature", "error")
        return resp

    @app.post("/signatures/{signature_id}/attribute")
    def attribute_signature(
        request: Request,
        signature_id: int,
        causing_person: str = Form(""),
        reason_text: str = Form(""),
        triage_status: str = Form(""),
        jira_ticket: str = Form(""),
        anchor: str = Form(""),
    ):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            count = actions.attribute_by_signature(
                s,
                signature_id,
                actor,
                causing_person=causing_person,
                reason_text=reason_text,
                triage_status=triage_status or None,
                jira_ticket=jira_ticket,
            )
        resp = back(request, anchor=anchor)
        if count:
            parts = []
            if causing_person.strip():
                parts.append(f"cause → {causing_person.strip()}")
            if reason_text.strip():
                parts.append("reason updated")
            if triage_status:
                parts.append(f"triage status → {triage_status}")
            if jira_ticket.strip():
                parts.append(f"Jira ticket → {jira_ticket.strip()}")
            message = f"Updated {_n(count, 'test')} sharing this failure signature"
            if parts:
                message += " — " + ", ".join(parts)
            set_flash(resp, message)
        else:
            set_flash(resp, "No open failing tests share this signature", "error")
        return resp

    @app.post("/episodes/bulk/attribute")
    async def bulk_attribute(request: Request):
        form = await request.form()
        episode_ids = [int(v) for v in form.getlist("episode_ids")]
        actor = current_actor(request)
        triage_status = str(form.get("triage_status", "")) or None
        with session_scope(session_factory) as s:
            count = actions.bulk_set_attribution(
                s,
                episode_ids,
                actor,
                causing_person=str(form.get("causing_person", "")),
                reason_text=str(form.get("reason_text", "")),
                triage_status=triage_status,
            )
        resp = back(request)
        if count:
            message = f"Updated {_n(count, 'selected test')}"
            if triage_status:
                message += f" — triage status → {triage_status}"
            set_flash(resp, message)
        else:
            set_flash(resp, "Nothing updated — no tests selected", "error")
        return resp

    @app.post("/episodes/{episode_id}/confirm")
    def confirm(request: Request, episode_id: int, anchor: str = Form("")):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            attr = actions.confirm(s, episode_id, actor)
            confirmed_cause = attr.causing_person if attr else None
        resp = back(request, anchor=anchor)
        if attr is not None:
            suffix = f" — cause → {confirmed_cause}" if confirmed_cause else ""
            set_flash(resp, f"AI suggestion confirmed{suffix}")
        else:
            set_flash(resp, "Episode not found — nothing confirmed", "error")
        return resp

    @app.post("/episodes/{episode_id}/attribute")
    def attribute(
        request: Request,
        episode_id: int,
        causing_person: str = Form(""),
        reason_text: str = Form(""),
        triage_status: str = Form(""),
        jira_ticket: str = Form(""),
        anchor: str = Form(""),
    ):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            attr = actions.set_attribution(
                s,
                episode_id,
                actor,
                causing_person=causing_person,
                reason_text=reason_text,
                triage_status=triage_status or None,
                jira_ticket=jira_ticket,
            )
        resp = back(request, anchor=anchor)
        if attr is None:
            set_flash(resp, "Episode not found — nothing saved", "error")
            return resp
        parts = []
        if causing_person.strip():
            parts.append(f"cause → {causing_person.strip()}")
        if reason_text.strip():
            parts.append("reason updated")
        if triage_status:
            parts.append(f"triage status → {triage_status}")
        if jira_ticket.strip():
            parts.append(f"Jira ticket → {jira_ticket.strip()}")
        message = "Saved — " + ", ".join(parts) if parts else "Saved (no changes submitted)"
        set_flash(resp, message)
        return resp

    return app


app = create_app()
