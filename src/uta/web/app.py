"""Slice-0 web app: one read-only view listing an ingested run's tests.

Milestones 3+ build the triage queue, per-test record and run summary on top of this.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from uta.config import get_settings
from uta.db import make_engine, make_session_factory, session_scope
from uta.models import Run, TestResult

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def create_app(session_factory=None) -> FastAPI:
    if session_factory is None:
        settings = get_settings()
        session_factory = make_session_factory(make_engine(settings.database_url))
    app = FastAPI(title="Jenkins UT Analyzer")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/runs/{build}", response_class=HTMLResponse)
    def run_view(request: Request, build: int):
        with session_scope(session_factory) as s:
            run = s.scalar(select(Run).where(Run.build_number == build))
            results = (
                s.scalars(
                    select(TestResult)
                    .where(TestResult.run_id == run.id)
                    .order_by(TestResult.status, TestResult.test_id)
                ).all()
                if run
                else []
            )
            # Detach simple view data so templates don't touch a closed session.
            view = {
                "run": None
                if run is None
                else {
                    "build": run.build_number,
                    "status": run.status,
                    "complete": run.complete,
                    "started_at": run.started_at,
                    "finished_at": run.finished_at,
                },
                "results": [
                    {
                        "test_id": r.test_id,
                        "track": r.track,
                        "status": r.status,
                        "duration": r.duration,
                        "owner": r.owner_initials,
                        "file_path": r.file_path,
                        "line": r.line,
                    }
                    for r in results
                ],
            }
        return _TEMPLATES.TemplateResponse(request, "run.html", view)

    return app


app = create_app()
