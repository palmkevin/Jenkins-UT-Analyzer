"""Alembic migration tests — run against the CI-provided Postgres.

These tests require a live Postgres connection (DATABASE_URL env var).
They are NOT marked ``live`` — they use the throwaway CI Postgres, not a
gated external system. CI provides the DB via a ``services:`` block.

If DATABASE_URL is not set or doesn't point at Postgres, these tests are
skipped automatically so the suite stays green offline.
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
POSTGRES_AVAILABLE = DATABASE_URL.startswith("postgresql")


@pytest.fixture
def pg_engine():
    """Function-scoped Postgres engine; skips if DATABASE_URL is not Postgres."""
    if not POSTGRES_AVAILABLE:
        pytest.skip("DATABASE_URL not set to a Postgres URL — skipping migration tests")
    engine = create_engine(DATABASE_URL, future=True)
    yield engine
    engine.dispose()


def _alembic_cfg() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


@pytest.fixture
def clean_db(pg_engine):
    """Drop all tables and the alembic_version table before each test."""
    with pg_engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        # Drop in reverse dependency order
        for tbl in [
            "kb_signatures",
            "test_classifications",
            "run_signals",
            "failure_episodes",
            "test_lifecycle",
            "test_results",
            "test_identity",
            "run_shards",
            "runs",
        ]:
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        conn.commit()
    yield


def test_upgrade_head(pg_engine, clean_db):
    """alembic upgrade head must complete without error."""
    command.upgrade(_alembic_cfg(), "head")


def test_downgrade_base(pg_engine, clean_db):
    """upgrade then downgrade must leave no application tables."""
    cfg = _alembic_cfg()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    with pg_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        remaining = [row[0] for row in result]
        assert remaining == [], f"Tables remain after downgrade: {remaining}"


def test_pg_trgm_available_after_upgrade(clean_db, pg_engine):
    """pg_trgm extension must be installed by the migration."""
    command.upgrade(_alembic_cfg(), "head")
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).fetchone()
        assert row is not None, "pg_trgm was not installed by the migration"


def test_gin_index_exists(clean_db, pg_engine):
    """The GIN/pg_trgm index on kb_signatures.sig_text must exist after upgrade."""
    command.upgrade(_alembic_cfg(), "head")
    with pg_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'kb_signatures' "
                "  AND indexname = 'kb_sigs_text_trgm_idx'"
            )
        ).fetchone()
        assert row is not None, "GIN index kb_sigs_text_trgm_idx not found"


def test_assert_pg_trgm_helper(clean_db, pg_engine):
    """assert_pg_trgm must pass after the migration has run."""
    from uta.db import assert_pg_trgm

    command.upgrade(_alembic_cfg(), "head")
    assert_pg_trgm(pg_engine)  # must not raise


def test_assert_pg_trgm_no_op_on_sqlite():
    """assert_pg_trgm must be a no-op when the dialect is not Postgres."""
    from uta.db import assert_pg_trgm, make_engine

    engine = make_engine("sqlite+pysqlite:///:memory:")
    assert_pg_trgm(engine)  # must not raise


def test_trgm_similarity_query(clean_db, pg_engine):
    """After migration, a pg_trgm similarity query must execute on kb_signatures."""

    command.upgrade(_alembic_cfg(), "head")

    # Insert a test identity and a KB signature.
    with pg_engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO test_identity (test_id, class_name, method) "
                "VALUES ('pkg.Cls.test_foo', 'pkg.Cls', 'test_foo')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO kb_signatures (sig_hash, sig_text, test_identity_id, "
                "  created_at, updated_at) "
                "VALUES ('hash1', 'AssertionError: expected <NUM> got <NUM>', 1, now(), now())"
            )
        )
        conn.commit()

    with pg_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT sig_hash, similarity(sig_text, :q) AS sim "
                "FROM kb_signatures "
                "ORDER BY sim DESC LIMIT 5"
            ),
            {"q": "AssertionError: expected 42 got 37"},
        ).fetchall()
        assert len(result) == 1
        assert result[0][0] == "hash1"
        assert result[0][1] > 0.0  # non-zero similarity
