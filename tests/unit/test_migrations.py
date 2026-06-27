"""Migration + pg_trgm tests against a real Postgres.

These are part of the **offline** gate (not ``live``): CI provides an ephemeral Postgres via
``services:`` and sets ``DATABASE_URL``. When no Postgres is reachable (a dev box without one) they
**skip**, so ``pytest -m "not live"`` stays green everywhere. They are destructive — they drop and
recreate the ``public`` schema — so ``DATABASE_URL`` must point at a throwaway database.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from uta.config import get_settings
from uta.db import MissingExtensionError, assert_pg_trgm, make_engine

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

# Every table the Information model must create.
_EXPECTED_TABLES = {
    "runs",
    "run_shards",
    "test_identities",
    "test_results",
    "test_lifecycles",
    "failure_episodes",
    "attributions",
    "classifications",
    "code_change_candidates",
    "data_change_candidates",
    "failure_signatures",
}


def _alembic_cfg() -> Config:
    return Config(str(_ALEMBIC_INI))


@pytest.fixture
def pg_engine():
    url = get_settings().database_url
    if not url.startswith("postgresql"):
        pytest.skip("migration tests require Postgres (set DATABASE_URL)")
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        engine.dispose()
        pytest.skip("Postgres not reachable (DATABASE_URL points at no live server)")

    def _reset() -> None:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))

    _reset()
    yield engine
    _reset()
    engine.dispose()


def test_upgrade_builds_full_schema_with_pg_trgm(pg_engine):
    command.upgrade(_alembic_cfg(), "head")

    tables = set(inspect(pg_engine).get_table_names())
    assert _EXPECTED_TABLES <= tables, f"missing: {_EXPECTED_TABLES - tables}"

    with pg_engine.connect() as conn:
        assert conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'"))
        assert (
            conn.scalar(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE indexname='ix_failure_signatures_normalized_text_trgm'"
                )
            )
            .lower()
            .find("gin")
            != -1
        )
        # The fuzzy similarity the KB (§4) relies on is actually usable.
        sim = conn.scalar(
            text("SELECT similarity('expected <NUM>', 'expected <NUM> but was <NUM>')")
        )
        assert sim is not None and sim > 0

    # The startup guard is satisfied once migrations have run.
    assert_pg_trgm(pg_engine)


def test_use_alter_circular_fk_is_created(pg_engine):
    """The lifecycle<->episode circular FK must land (autogenerate omits use_alter FKs)."""
    command.upgrade(_alembic_cfg(), "head")
    with pg_engine.connect() as conn:
        assert conn.scalar(
            text("SELECT 1 FROM pg_constraint WHERE conname='fk_lifecycle_current_episode'")
        )


def test_downgrade_is_clean_and_guard_detects_missing_extension(pg_engine):
    command.upgrade(_alembic_cfg(), "head")
    command.downgrade(_alembic_cfg(), "base")

    tables = set(inspect(pg_engine).get_table_names())
    assert tables <= {"alembic_version"}, f"left behind: {tables}"

    with pg_engine.connect() as conn:
        assert not conn.scalar(text("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'"))

    # With the extension gone, the startup guard must fail loudly.
    with pytest.raises(MissingExtensionError):
        assert_pg_trgm(pg_engine)
