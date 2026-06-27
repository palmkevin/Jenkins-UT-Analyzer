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


@app.command("backfill")
def backfill(build: int) -> None:
    """Fetch, parse and persist one Jenkins build (live — requires Jenkins access)."""
    from uta.ingest.jenkins import HttpJenkinsClient
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    _run_migrations()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = HttpJenkinsClient(
        settings.jenkins_job_url,
        user=settings.jenkins_user,
        token=settings.jenkins_api_token,
    )
    ingest_build(client, session_factory, build, expected_shards=settings.expected_shards)
    typer.echo(f"ingested build #{build}")


if __name__ == "__main__":
    app()
