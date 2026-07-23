"""Rename runs → builds: the ubiquitous language says "Build"

The domain-modeling session (CONTEXT.md, ADR-0001 era) settled the canonical term for one nightly
execution: **Build** (matching Jenkins-speak and the ingest layer's ``ingest_build``), retiring
"run". This renames the tables, every ``run_id``-flavored column, and the run-named indexes and
unique constraints so the schema speaks the same language as the code. Data is untouched — every
operation is a pure rename.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-23 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (old, new) — tables first; columns are addressed by the *new* table names.
_TABLES = [
    ("runs", "builds"),
    ("run_shards", "build_shards"),
]
_COLUMNS = [
    ("builds", "baseline_run_id", "baseline_build_id"),
    ("build_shards", "run_id", "build_id"),
    ("test_results", "run_id", "build_id"),
    ("test_lifecycles", "all_time_first_failure_run_id", "all_time_first_failure_build_id"),
    ("test_lifecycles", "last_failing_run_id", "last_failing_build_id"),
    ("failure_episodes", "first_failure_run_id", "first_failure_build_id"),
    ("failure_episodes", "last_failing_run_id", "last_failing_build_id"),
    ("failure_episodes", "fixed_in_run_id", "fixed_in_build_id"),
    ("failure_episodes", "age_runs", "age_builds"),
    ("failure_signatures", "first_seen_run_id", "first_seen_build_id"),
    ("failure_signatures", "last_seen_run_id", "last_seen_build_id"),
    ("code_change_candidates", "run_id", "build_id"),
    ("data_change_candidates", "run_id", "build_id"),
]
_INDEXES = [
    ("ix_runs_build_number", "ix_builds_build_number"),
    ("ix_run_shards_run_id", "ix_build_shards_build_id"),
    ("ix_test_results_run_id", "ix_test_results_build_id"),
    ("ix_test_results_identity_run", "ix_test_results_identity_build"),
    ("ix_code_change_candidates_run_id", "ix_code_change_candidates_build_id"),
    ("ix_data_change_candidates_run_id", "ix_data_change_candidates_build_id"),
]
_CONSTRAINTS = [
    ("build_shards", "uq_run_shard_track", "uq_build_shard_track"),
    ("test_results", "uq_run_test_track", "uq_build_test_track"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for old, new in _TABLES:
        op.rename_table(old, new)
    for table, old, new in _COLUMNS:
        op.alter_column(table, old, new_column_name=new)
    for old, new in _INDEXES:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")
    for table, old, new in _CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}")


def downgrade() -> None:
    """Downgrade schema."""
    for table, old, new in _CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}")
    for old, new in _INDEXES:
        op.execute(f"ALTER INDEX {new} RENAME TO {old}")
    for table, old, new in reversed(_COLUMNS):
        op.alter_column(table, new, new_column_name=old)
    for old, new in reversed(_TABLES):
        op.rename_table(new, old)
