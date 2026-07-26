"""add overrunning-build snapshot to the poller heartbeat (issue #184)

Six columns on ``poller_heartbeats`` holding the single-row overrunning-build snapshot the poller
overwrites each tick: the current in-progress build's number/start, the stored Expected Duration
median (seconds), whether a build is building, the poller-computed ``overrunning`` flag the
dashboard banner reflects, and the one-email-per-build de-dup marker.

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning_build_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning_expected_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning_building", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "poller_heartbeats",
        sa.Column("overrunning_alerted_build_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("poller_heartbeats", "overrunning_alerted_build_number")
    op.drop_column("poller_heartbeats", "overrunning")
    op.drop_column("poller_heartbeats", "overrunning_building")
    op.drop_column("poller_heartbeats", "overrunning_expected_seconds")
    op.drop_column("poller_heartbeats", "overrunning_started_at")
    op.drop_column("poller_heartbeats", "overrunning_build_number")
