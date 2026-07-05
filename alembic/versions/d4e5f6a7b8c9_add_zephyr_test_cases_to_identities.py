"""add zephyr_test_cases to test_identities

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ZEPHYR test case(s) referencing the test, parsed from the failing test's
    # "ZEPHYR TEST CASE INFO" block (nullable; comma-separated ids, resolved at identity level).
    op.add_column(
        "test_identities",
        sa.Column("zephyr_test_cases", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("test_identities", "zephyr_test_cases")
