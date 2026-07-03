"""Dashboard web app (PLAN §5) — opens on the §0 triage queue.

Surfaces:
- ``GET /``                         the daily triage queue (§0), the primary landing view.
- ``GET /tests/{identity_id}``      the per-test record (§1) with the full evidence + actions.
- ``GET /runs/{build}``             the run-level summary (§2): totals, shards, baseline + diff.
- action POSTs (acknowledge / confirm / attribute / identity) → redirect back (PRG).

Route handlers stay thin: read-side projections live in :mod:`uta.web.views`, write-side mutations
in :mod:`uta.web.actions`. Both return detached data / commit via ``session_scope`` so templates
never touch a live session (the Slice-0 pattern).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from uta.config import get_settings
from uta.db import assert_pg_trgm, make_engine, make_session_factory, session_scope
from uta.web import actions, views
from uta.web.identity import ACTOR_COOKIE, current_actor

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _expanded(request: Request) -> list[str]:
    """Sections the reader asked to render in full — the ``?expand=a,b`` query param (issue #19).

    A capped section's "Load all N Tests" link points back with its key added here, so the same
    page re-renders that one bucket in full while the rest stay capped.
    """
    raw = request.query_params.get("expand", "")
    return [s for s in raw.split(",") if s]


def create_app(session_factory=None) -> FastAPI:
    startup_engine = None
    if session_factory is None:
        settings = get_settings()
        startup_engine = make_engine(settings.database_url)
        session_factory = make_session_factory(startup_engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Fail fast if the DB skipped migrations — deferred to startup so import doesn't connect
        # (tests inject a session_factory, leaving startup_engine None, and never hit this).
        if startup_engine is not None:
            assert_pg_trgm(startup_engine)
        yield

    app = FastAPI(title="Jenkins UT Analyzer", lifespan=lifespan)

    def render(request: Request, template: str, context: dict) -> HTMLResponse:
        cfg = get_settings()
        context = {
            **context,
            "actor": current_actor(request),
            "jira_base_url": cfg.jira_base_url,
            "fisheye_changelog_url": cfg.fisheye_changelog_url,
            "expand": _expanded(request),
            "row_limit": cfg.ui_row_limit,
        }
        return _TEMPLATES.TemplateResponse(request, template, context)

    def back(request: Request, fallback: str = "/") -> RedirectResponse:
        # Post/Redirect/Get: bounce back to the page the action came from.
        target = request.headers.get("referer") or fallback
        return RedirectResponse(target, status_code=303)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def triage(request: Request):
        cfg = get_settings()
        with session_scope(session_factory) as s:
            queue = views.triage_queue(
                s,
                recently_fixed_days=cfg.recently_fixed_days,
                limit=cfg.ui_row_limit,
                expand=_expanded(request),
            )
        return render(request, "triage.html", {"queue": queue})

    @app.get("/tests/{identity_id}", response_class=HTMLResponse)
    def test_record(request: Request, identity_id: int):
        cfg = get_settings()
        with session_scope(session_factory) as s:
            record = views.test_record(
                s,
                identity_id,
                flaky_window_days=cfg.flaky_window_days,
                flaky_threshold=cfg.flaky_transition_threshold,
                kb_top_k=cfg.kb_top_k,
                kb_cutoff=cfg.pgtrgm_similarity_cutoff,
            )
        return render(request, "test_record.html", {"record": record, "identity_id": identity_id})

    @app.get("/runs/{build}", response_class=HTMLResponse)
    def run_view(request: Request, build: int):
        cfg = get_settings()
        with session_scope(session_factory) as s:
            run = views.run_summary(s, build, limit=cfg.ui_row_limit, expand=_expanded(request))
        return render(request, "run.html", {"run": run, "build": build})

    @app.get("/flaky", response_class=HTMLResponse)
    def flaky_view(request: Request):
        cfg = get_settings()
        with session_scope(session_factory) as s:
            board = views.flaky_leaderboard(
                s,
                window_days=cfg.flaky_window_days,
                threshold=cfg.flaky_transition_threshold,
            )
        return render(request, "flaky.html", {"board": board})

    @app.get("/kb", response_class=HTMLResponse)
    def kb_view(request: Request, q: str = ""):
        cfg = get_settings()
        with session_scope(session_factory) as s:
            results = views.kb_search(s, q, cutoff=cfg.pgtrgm_similarity_cutoff)
        return render(request, "kb.html", {"kb": results})

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

    @app.post("/tests/{identity_id}/acknowledge")
    def acknowledge(request: Request, identity_id: int):
        actor = current_actor(request)
        with session_scope(session_factory) as s:
            actions.acknowledge(s, identity_id, actor)
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
