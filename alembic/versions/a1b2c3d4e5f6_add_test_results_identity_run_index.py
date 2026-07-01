"""add composite index on test_results (test_identity_id, run_id)

Revision ID: a1b2c3d4e5f6
Revises: 4f1a2b3c5d6e
Create Date: 2026-07-01 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "4f1a2b3c5d6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Speeds the flaky `_sequence` and lifecycle age queries (scan one identity across runs).
    op.create_index(
        "ix_test_results_identity_run",
        "test_results",
        ["test_identity_id", "run_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_test_results_identity_run", table_name="test_results")
