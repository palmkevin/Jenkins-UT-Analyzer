"""Rename build_shards → build_tracks: the ubiquitous language says "Track"

The domain-modeling session recorded in ADR-0002 settled on **Track** as the single canonical term
for the parallel lanes the nightly build runs the test suite in, banning "shard" (nothing is
partitioned — every lane runs the full suite). This renames the table, its index and its unique
constraint to match; the ``track`` column already spoke the right language (it matches
``test_results.track``) and is untouched. Data is untouched — every operation is a pure rename.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-23 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = [
    ("build_shards", "build_tracks"),
]
_INDEXES = [
    ("ix_build_shards_build_id", "ix_build_tracks_build_id"),
]
_CONSTRAINTS = [
    ("build_tracks", "uq_build_shard_track", "uq_build_track"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for old, new in _TABLES:
        op.rename_table(old, new)
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
    for old, new in reversed(_TABLES):
        op.rename_table(new, old)
