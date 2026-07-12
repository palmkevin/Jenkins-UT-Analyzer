"""owner = main developer (SVN blame); ZEPHYR author kept as zephyr_owner

Redefines "owner" (issue #114). The ZEPHYR test-case author had silently become the dashboard
"Owner"; it is renamed to its honest name ``zephyr_owner`` (data preserved) and a new
``main_developer`` column holds the SVN-blame-derived developer that "Owner" now means (NULL until
blame resolves it — filled by ingest with ``SVN_BLAME_ENABLED`` on, or ``uta reattribute-owners``).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename the mislabeled ZEPHYR-owner columns to their honest name (data preserved as-is).
    op.alter_column("test_identities", "owner_initials", new_column_name="zephyr_owner")
    op.alter_column("test_results", "owner_initials", new_column_name="zephyr_owner")
    # New identity-level "Owner" = the test's main developer (SVN blame); NULL until resolved.
    op.add_column(
        "test_identities",
        sa.Column("main_developer", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("test_identities", "main_developer")
    op.alter_column("test_results", "zephyr_owner", new_column_name="owner_initials")
    op.alter_column("test_identities", "zephyr_owner", new_column_name="owner_initials")
