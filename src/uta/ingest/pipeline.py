"""Slice-0 ingest pipeline: fetch one build -> parse -> persist a run + its results.

Wires the Jenkins client (real or fake) and the parsers. Idempotent on ``build_number``: a
re-ingest replaces the run's results rather than duplicating them.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from uta.db import session_scope
from uta.ingest.jenkins import JenkinsClient
from uta.ingest.ut_report import parse_test_report
from uta.ingest.wfapi import parse_wfapi
from uta.models import Run, TestResult


def ingest_build(
    client: JenkinsClient,
    session_factory: sessionmaker[Session],
    build: int,
    *,
    expected_shards: int = 2,
) -> int:
    """Fetch, parse and persist one build. Returns the run's build_number."""
    meta = client.build_meta(build)
    timing = parse_wfapi(client.wfapi(build))
    report = parse_test_report(client.test_report(build))
    win_start, win_end = timing.window

    with session_scope(session_factory) as session:
        run = session.scalar(select(Run).where(Run.build_number == build))
        if run is None:
            run = Run(build_number=build)
            session.add(run)
        else:
            run.results.clear()  # idempotent re-ingest
            session.flush()  # delete old rows before re-inserting (unique constraint)

        run.status = meta.get("result") or timing.status
        run.url = meta.get("url", "")
        run.started_at = win_start
        run.finished_at = win_end
        run.complete = timing.is_complete(expected_shards)

        for case in report.cases:
            run.results.append(
                TestResult(
                    test_id=case.test_id,
                    track=case.track,
                    status=case.status,
                    duration=case.duration,
                    file_path=case.file_path,
                    line=case.line,
                    owner_initials=case.owner_initials,
                    error_details=case.error_details,
                )
            )
    return build


def data_change_window(timing_window: tuple, lookback: timedelta = timedelta(hours=12)) -> tuple:
    """The UTC window for candidate data changes: a lookback before the run through its end.

    Data changes precede the nightly run (confirmed empirically on #1702 — the run's own window had
    no tracked changes), so we look back from the run start. ``lookback`` is a provisional default,
    tuned on real data later.
    """
    start, end = timing_window
    return start - lookback, end
