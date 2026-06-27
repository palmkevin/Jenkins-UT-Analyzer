"""CLI entrypoints — back-fill and schema bootstrap. Run: ``uta --help``."""

from __future__ import annotations

import typer

from uta.config import get_settings
from uta.db import Base, make_engine, make_session_factory

app = typer.Typer(help="Jenkins UT Analyzer CLI")


@app.command("init-db")
def init_db() -> None:
    """Create the Slice-0 schema (Milestone 1 replaces this with Alembic migrations)."""
    settings = get_settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    typer.echo("schema created")


@app.command("backfill")
def backfill(build: int) -> None:
    """Fetch, parse and persist one Jenkins build (live — requires Jenkins access)."""
    from uta.ingest.jenkins import HttpJenkinsClient
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
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
