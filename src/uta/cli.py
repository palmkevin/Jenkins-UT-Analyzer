"""CLI entrypoints — schema migration and back-fill. Build: ``uta --help``."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from uta.clients import build_client as _build_client
from uta.clients import build_email_sender as _build_email_sender
from uta.clients import build_feed as _build_feed
from uta.clients import build_hypothesis_provider as _build_hypothesis_provider
from uta.clients import build_svn_blame_client as _build_svn_blame_client
from uta.clients import windows as _windows
from uta.config import get_settings
from uta.db import assert_pg_trgm, make_engine, make_session_factory

app = typer.Typer(help="Jenkins UT Analyzer CLI")


def _configure_logging() -> None:
    """Emit the per-build INFO timing logs to stdout.

    Call this **after** ``_run_migrations()``: Alembic's ``fileConfig`` reconfigures the root
    logger and disables pre-existing loggers, so we (re-)assert an INFO stream handler and force
    the ``uta`` logger back on — otherwise the pipeline's per-build timing lines are swallowed.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    root.setLevel(logging.INFO)
    logging.getLogger("uta").setLevel(logging.INFO)
    # Re-enable any uta.* logger a prior fileConfig may have disabled (defensive; the alembic env
    # now passes disable_existing_loggers=False, but this keeps the timing logs robust regardless).
    for name, lg in logging.root.manager.loggerDict.items():
        if name.startswith("uta") and isinstance(lg, logging.Logger):
            lg.disabled = False


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
def backfill(build: int, to: int | None = None) -> None:
    """Fetch, parse, persist and analyse one build, or a ``build..to`` range (live)."""
    from uta.analyze.flakiness import recompute_flaky_flags
    from uta.db import session_scope
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    _run_migrations()
    _configure_logging()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    feed = _build_feed(settings)
    svn_blame_client = _build_svn_blame_client(settings)
    lookback, tolerance = _windows(settings)
    for n in range(build, (to or build) + 1):
        # No email sender on back-fill: historical regressions must not be (re-)mailed. Flaky flags
        # are display-only and derived purely from results, so defer them to a single pass after the
        # loop rather than recomputing the whole failing set every build.
        ingest_build(
            client,
            session_factory,
            n,
            expected_tracks=settings.expected_tracks,
            feed=feed,
            data_change_lookback=lookback,
            data_change_tolerance=tolerance,
            flaky_window_days=settings.flaky_window_days,
            flaky_threshold=settings.flaky_transition_threshold,
            ingest_unittest_logs=settings.ingest_unittest_stages,
            unittest_suites=settings.unittest_suite_set,
            recompute_flaky=False,
            svn_blame_client=svn_blame_client,
        )
        typer.echo(f"ingested build #{n}")
    with session_scope(session_factory) as session:
        recompute_flaky_flags(
            session,
            window_days=settings.flaky_window_days,
            threshold=settings.flaky_transition_threshold,
        )


@app.command("poll")
def poll() -> None:
    """Run the scheduled poller: ingest new completed builds on a fixed interval (live)."""
    from uta.poller import run_scheduler

    settings = get_settings()
    _run_migrations()
    _configure_logging()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    feed = _build_feed(settings)
    email_sender = _build_email_sender(settings)
    hypothesis_provider = _build_hypothesis_provider(settings)
    svn_blame_client = _build_svn_blame_client(settings)
    typer.echo(f"polling every {settings.poll_interval_seconds}s …")
    # Tunable thresholds are re-read from the DB each tick (control panel, issue #16), so only the
    # base settings + non-overridable clients are passed through here.
    run_scheduler(
        client,
        session_factory,
        settings,
        feed=feed,
        email_sender=email_sender,
        email_recipients=settings.email_recipients,
        hypothesis_provider=hypothesis_provider,
        svn_blame_client=svn_blame_client,
    )


@app.command("bootstrap")
def bootstrap(depth: int | None = None) -> None:
    """Populate a fresh store with the last ``depth`` completed builds, oldest-first (live).

    Ingests ``last_completed - depth + 1 … last_completed`` in ascending order so lifecycle and
    episodes accrue chronologically (age N → age 1). Like ``backfill`` it passes no email sender and
    no hypothesis provider — back-filled history must not be (re-)mailed. ``depth`` defaults to
    ``BACKFILL_DEPTH``.
    """
    from uta.analyze.flakiness import recompute_flaky_flags
    from uta.db import session_scope
    from uta.ingest.pipeline import ingest_build

    settings = get_settings()
    depth = depth if depth is not None else settings.backfill_depth
    _run_migrations()
    _configure_logging()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    client = _build_client(settings)
    latest = client.last_completed_build()
    if latest is None:
        typer.echo("no completed build to ingest")
        return
    feed = _build_feed(settings)
    svn_blame_client = _build_svn_blame_client(settings)
    lookback, tolerance = _windows(settings)
    start = max(1, latest - depth + 1)
    for n in range(start, latest + 1):
        # Defer flaky flags to a single post-loop pass (see `backfill`) — they are display-only and
        # derived purely from results, so recomputing per build is wasted work during bootstrap.
        ingest_build(
            client,
            session_factory,
            n,
            expected_tracks=settings.expected_tracks,
            feed=feed,
            data_change_lookback=lookback,
            data_change_tolerance=tolerance,
            flaky_window_days=settings.flaky_window_days,
            flaky_threshold=settings.flaky_transition_threshold,
            ingest_unittest_logs=settings.ingest_unittest_stages,
            unittest_suites=settings.unittest_suite_set,
            recompute_flaky=False,
            svn_blame_client=svn_blame_client,
        )
        typer.echo(f"ingested build #{n}")
    with session_scope(session_factory) as session:
        recompute_flaky_flags(
            session,
            window_days=settings.flaky_window_days,
            threshold=settings.flaky_transition_threshold,
        )


@app.command("reattribute-owners")
def reattribute_owners(refresh: bool = False, limit: int | None = None) -> None:
    """Backfill each test's owner = main developer from ``svn blame`` (issue #114, live).

    The one-shot "fix existing data" pass after redefining ownership: resolves
    ``TestIdentity.main_developer`` for every test whose source file blames to an author. By default
    only tests with no owner yet are resolved; ``--refresh`` re-blames all. Requires
    ``SVN_BLAME_ENABLED`` + ``SVN_REPO_BASE_URL`` (else there is no blame client and it is a no-op).
    """
    from uta.analyze.ownership import resolve_all
    from uta.db import session_scope

    settings = get_settings()
    _run_migrations()
    _configure_logging()
    svn_blame_client = _build_svn_blame_client(settings)
    if svn_blame_client is None:
        typer.echo("SVN blame disabled — set SVN_BLAME_ENABLED + SVN_REPO_BASE_URL; nothing to do")
        return
    session_factory = make_session_factory(make_engine(settings.database_url))
    with session_scope(session_factory) as session:
        resolved = resolve_all(session, svn_blame_client, refresh=refresh, limit=limit)
    typer.echo(f"resolved main developer for {resolved} test(s)")


@app.command("prune")
def prune_cmd(result_days: int | None = None, job_days: int | None = None) -> None:
    """Prune old passing results and finished ingest jobs per the retention policy (issue #52).

    The same idempotent pass the poller builds on every tick — this command is the on-demand /
    first-time variant (e.g. right after enabling retention on a store with years of history).
    Days default to ``RESULT_RETENTION_DAYS`` / ``INGEST_JOB_RETENTION_DAYS``; 0 disables that
    window.
    """
    from uta.db import session_scope
    from uta.retention import prune

    settings = get_settings()
    _run_migrations()
    _configure_logging()
    session_factory = make_session_factory(make_engine(settings.database_url))
    with session_scope(session_factory) as session:
        report = prune(
            session,
            result_retention_days=(
                result_days if result_days is not None else settings.result_retention_days
            ),
            ingest_job_retention_days=(
                job_days if job_days is not None else settings.ingest_job_retention_days
            ),
        )
    typer.echo(
        f"pruned {report.results_deleted} passing results, "
        f"{report.ingest_jobs_deleted} finished ingest jobs"
    )


@app.command("seed-demo")
def seed_demo() -> None:
    """Populate the configured ``DATABASE_URL`` with the synthetic demo dataset (no externals).

    Brings the schema to head, then seeds a full synthetic build history via the real ingest
    pipeline. Use this for a persistent (e.g. Postgres) demo instance; the ephemeral in-memory web
    app seeds itself on startup (``uta demo`` / ``uvicorn uta.demo.app:app``).
    """
    from uta.demo.seed import seed_demo_data

    settings = get_settings()
    _run_migrations()
    _configure_logging()
    engine = make_engine(settings.database_url)
    assert_pg_trgm(engine)
    session_factory = make_session_factory(engine)
    count = seed_demo_data(session_factory)
    typer.echo(f"seeded {count} synthetic builds into {settings.database_url}")


@app.command("demo")
def demo(host: str = "0.0.0.0", port: int = 8000) -> None:  # noqa: S104 - demo binds all ifaces
    """Run the self-contained demo app: an ephemeral in-memory store, seeded, served (no externals).

    This is the online-hosting entrypoint. It needs no Jenkins/Oracle/Postgres — a fresh SQLite
    store is created and seeded with the synthetic dataset in-process, then served with uvicorn.
    """
    import uvicorn

    from uta.demo.app import create_demo_app

    _configure_logging()
    typer.echo(f"serving demo on http://{host}:{port} (ephemeral synthetic dataset)")
    uvicorn.run(create_demo_app(), host=host, port=port)


if __name__ == "__main__":
    app()
