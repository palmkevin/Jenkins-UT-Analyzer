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


def _build_email_sender(settings):
    """The SMTP sender, or ``None`` when email is not configured (host + recipients required)."""
    if not settings.smtp_host or not settings.email_recipients:
        return None
    from uta.delivery.email import SmtpEmailSender

    return SmtpEmailSender(settings.smtp_host, settings.smtp_port, settings.smtp_from)


def _build_hypothesis_provider(settings):
    """The configured LLM provider (Anthropic or OpenAI), or Noop when no key is set.

    ``LLM_PROVIDER`` picks explicitly; empty auto-selects whichever key is configured (Anthropic
    wins if both). A chosen provider with no key falls back to Noop (no model call).
    """
    from uta.llm import NoopHypothesisProvider

    choice = (settings.llm_provider or "").lower()
    if not choice:
        if settings.anthropic_api_key:
            choice = "anthropic"
        elif settings.openai_api_key:
            choice = "openai"

    if choice == "anthropic" and settings.anthropic_api_key:
        from uta.llm.claude import AnthropicHypothesisProvider

        return AnthropicHypothesisProvider(
            settings.anthropic_api_key, model=settings.anthropic_model
        )
    if choice == "openai" and settings.openai_api_key:
        from uta.llm.openai_provider import OpenAIHypothesisProvider

        return OpenAIHypothesisProvider(settings.openai_api_key, model=settings.openai_model)
    return NoopHypothesisProvider()


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
        # No email sender on back-fill: historical regressions must not be (re-)mailed.
        ingest_build(
            client,
            session_factory,
            n,
            expected_shards=settings.expected_shards,
            feed=feed,
            data_change_lookback=lookback,
            data_change_tolerance=tolerance,
            flaky_window_days=settings.flaky_window_days,
            flaky_threshold=settings.flaky_transition_threshold,
            ingest_unittest_logs=settings.ingest_unittest_stages,
            unittest_suites=settings.unittest_suite_set,
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
    email_sender = _build_email_sender(settings)
    hypothesis_provider = _build_hypothesis_provider(settings)
    typer.echo(f"polling every {settings.poll_interval_seconds}s …")
    run_scheduler(
        client,
        session_factory,
        interval_seconds=settings.poll_interval_seconds,
        expected_shards=settings.expected_shards,
        feed=feed,
        data_change_lookback=lookback,
        data_change_tolerance=tolerance,
        flaky_window_days=settings.flaky_window_days,
        flaky_threshold=settings.flaky_transition_threshold,
        email_sender=email_sender,
        email_recipients=settings.email_recipients,
        email_recovery_notice=settings.email_recovery_notice,
        hypothesis_provider=hypothesis_provider,
        kb_top_k=settings.kb_top_k,
        kb_similarity_cutoff=settings.pgtrgm_similarity_cutoff,
        ingest_unittest_logs=settings.ingest_unittest_stages,
        unittest_suites=settings.unittest_suite_set,
        backfill_depth=settings.backfill_depth,
    )


@app.command("bootstrap")
def bootstrap(depth: int | None = None) -> None:
    """Populate a fresh store with the last ``depth`` completed builds, oldest-first (live).

    Ingests ``last_completed - depth + 1 … last_completed`` in ascending order so lifecycle and
    episodes accrue chronologically (age N → age 1). Like ``backfill`` it passes no email sender and
    no hypothesis provider — back-filled history must not be (re-)mailed. ``depth`` defaults to
    ``BACKFILL_DEPTH``.
    """
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    depth = depth if depth is not None else settings.backfill_depth
    _run_migrations()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    latest = client.last_completed_build()
    if latest is None:
        typer.echo("no completed build to ingest")
        return
    feed = _build_feed(settings)
    lookback, tolerance = _windows(settings)
    start = max(1, latest - depth + 1)
    for n in range(start, latest + 1):
        ingest_build(
            client,
            session_factory,
            n,
            expected_shards=settings.expected_shards,
            feed=feed,
            data_change_lookback=lookback,
            data_change_tolerance=tolerance,
            flaky_window_days=settings.flaky_window_days,
            flaky_threshold=settings.flaky_transition_threshold,
            ingest_unittest_logs=settings.ingest_unittest_stages,
            unittest_suites=settings.unittest_suite_set,
        )
        typer.echo(f"ingested build #{n}")


if __name__ == "__main__":
    app()
