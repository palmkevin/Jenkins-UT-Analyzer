"""add jira_ticket to failure_episodes

Revision ID: 4f1a2b3c5d6e
Revises: 31fdfa8031ac
Create Date: 2026-06-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f1a2b3c5d6e"
down_revision: str | Sequence[str] | None = "31fdfa8031ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Human-entered Jira ticket per failure episode (nullable; set/cleared from the dashboard).
    op.add_column(
        "failure_episodes",
        sa.Column("jira_ticket", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("failure_episodes", "jira_ticket")
