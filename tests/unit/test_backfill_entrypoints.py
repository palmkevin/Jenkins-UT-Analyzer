"""Every back-fill entry point ingests like the poller (backfill-paths-drop-incidents).

``uta backfill``, ``uta bootstrap`` and the control-panel job must pass Build Incidents and the
SVN blame client to ``ingest_build`` and resolve the control panel's DB overrides — only the
live-path extras (alerts, LLM hypotheses) are left out.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from tests.fakes import FakeJenkinsClient
from uta import cli
from uta.config import Settings
from uta.control.jobs import create_ingest_job, run_ingest_job, trigger_ingest
from uta.control.tunables import set_override
from uta.db import Base, make_engine, make_session_factory, session_scope

_BLAME = object()  # sentinel blame client


class _Fake(FakeJenkinsClient):
    def last_completed_build(self) -> int | None:
        return 3


@pytest.fixture
def captured(monkeypatch):
    import uta.ingest.pipeline as pipeline

    calls: list[tuple[int, dict]] = []

    def _record(client, session_factory, number, **kwargs):
        calls.append((number, kwargs))
        return number

    monkeypatch.setattr(pipeline, "ingest_build", _record)
    return calls


def test_control_panel_job_passes_incidents_and_blame(session_factory, captured):
    with session_scope(session_factory) as s:
        job = create_ingest_job(s, 1, 1)
        s.flush()
        job_id = job.id
    run_ingest_job(
        session_factory,
        job_id,
        settings=Settings(ingest_build_incidents=True),
        client=_Fake(),
        feed=None,
        svn_blame_client=_BLAME,
    )
    ((_, kwargs),) = captured
    assert kwargs["ingest_build_incidents"] is True
    assert kwargs["svn_blame_client"] is _BLAME
    assert "channels" not in kwargs and "hypothesis_provider" not in kwargs


def test_trigger_ingest_builds_the_blame_client_from_settings(
    session_factory, captured, monkeypatch
):
    import uta.control.jobs as jobs

    monkeypatch.setattr(jobs, "build_svn_blame_client", lambda settings: _BLAME)
    trigger_ingest(
        session_factory,
        build_start=1,
        build_end=1,
        settings=Settings(),
        client=_Fake(),
        feed=None,
        run_in_thread=False,
    )
    ((_, kwargs),) = captured
    assert kwargs["svn_blame_client"] is _BLAME


@pytest.fixture
def cli_store(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(database_url=url))
    monkeypatch.setattr(cli, "_run_migrations", lambda: None)
    monkeypatch.setattr(cli, "_build_client", lambda settings: _Fake())
    monkeypatch.setattr(cli, "_build_feed", lambda settings: None)
    monkeypatch.setattr(cli, "_build_svn_blame_client", lambda settings: _BLAME)
    return factory


@pytest.mark.parametrize("argv", [["backfill", "1", "--to", "2"], ["bootstrap"]])
def test_cli_backfill_paths_match_the_poller(argv, cli_store, captured):
    with session_scope(cli_store) as s:
        set_override(s, "flaky_window_days", "12")  # a control-panel override
        set_override(s, "backfill_depth", "2")
    result = CliRunner().invoke(cli.app, argv)
    assert result.exit_code == 0, result.output
    assert [n for n, _ in captured] == ([1, 2] if argv[0] == "backfill" else [2, 3])
    for _, kwargs in captured:
        assert kwargs["ingest_build_incidents"] is True
        assert kwargs["svn_blame_client"] is _BLAME
        assert kwargs["flaky_window_days"] == 12  # DB override honoured, not the env default
