"""add poller-resilience state (issue #51)

The ``build_quarantines`` table (per-build failure attempts + quarantine record, surfaced on the
control panel) and two heartbeat columns: ``last_success_at`` (what ``/health`` evaluates for
staleness — only error-free ticks move it) and ``stale_alerted_at`` (the ops staleness-alert latch).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "build_quarantines",
        sa.Column("build_number", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("first_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("stale_alerted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("poller_heartbeats", "stale_alerted_at")
    op.drop_column("poller_heartbeats", "last_success_at")
    op.drop_table("build_quarantines")
