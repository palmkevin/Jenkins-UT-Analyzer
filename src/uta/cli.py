"""CLI entrypoints — schema migration and back-fill. Run: ``uta --help``."""

from __future__ import annotations

from pathlib import Path

import typer

from uta.config import get_settings
from uta.db import assert_pg_trgm, make_engine, make_session_factory

app = typer.Typer(help="Jenkins UT Analyzer CLI")

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _run_migrations() -> None:
    """Apply Alembic migrations up to head (reads ``DATABASE_URL`` via the app settings)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


@app.command("migrate")
def migrate() -> None:
    """Bring the database schema to head (Alembic) and assert ``pg_trgm`` is installed."""
    _run_migrations()
    assert_pg_trgm(make_engine(get_settings().database_url))
    typer.echo("schema at head; pg_trgm present")


@app.command("init-db")
def init_db() -> None:
    """Deprecated alias for ``migrate`` (Milestone 1 replaced create_all with Alembic)."""
    migrate()


def _build_client(settings):
    from uta.ingest.jenkins import HttpJenkinsClient

    return HttpJenkinsClient(
        settings.jenkins_job_url,
        user=settings.jenkins_user,
        token=settings.jenkins_api_token,
    )


def _build_feed(settings):
    """The Oracle ut_ref feed, or ``None`` if no password is set (data candidates skipped)."""
    if not settings.ut_ref_password:
        return None
    from uta.refdb.oracle import OracleTrackingFeed

    return OracleTrackingFeed(
        settings.ut_ref_host,
        settings.ut_ref_port,
        settings.ut_ref_service,
        settings.ut_ref_user,
        settings.ut_ref_password,
        thick=settings.ut_ref_thick,
    )


def _windows(settings):
    from datetime import timedelta

    return (
        timedelta(hours=settings.data_change_lookback_hours),
        timedelta(minutes=settings.data_change_tolerance_minutes),
    )


@app.command("backfill")
def backfill(build: int, to: int | None = None) -> None:
    """Fetch, parse, persist and analyse one build, or a ``build..to`` range (live)."""
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    _run_migrations()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    feed = _build_feed(settings)
    lookback, tolerance = _windows(settings)
    for n in range(build, (to or build) + 1):
        ingest_build(
            client,
            session_factory,
            n,
            expected_shards=settings.expected_shards,
            feed=feed,
            data_change_lookback=lookback,
            data_change_tolerance=tolerance,
        )
        typer.echo(f"ingested build #{n}")


@app.command("poll")
def poll() -> None:
    """Run the scheduled poller: ingest new completed builds on a fixed interval (live)."""
    from uta.poller import run_scheduler

    settings = get_settings()
    _run_migrations()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    feed = _build_feed(settings)
    lookback, tolerance = _windows(settings)
    typer.echo(f"polling every {settings.poll_interval_seconds}s …")
    run_scheduler(
        client,
        session_factory,
        interval_seconds=settings.poll_interval_seconds,
        expected_shards=settings.expected_shards,
        feed=feed,
        data_change_lookback=lookback,
        data_change_tolerance=tolerance,
    )


if __name__ == "__main__":
    app()
