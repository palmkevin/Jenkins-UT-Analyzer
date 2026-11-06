"""make the later tables' created_at / updated_at NOT NULL (migration drift)

``TimestampMixin`` declares ``created_at`` / ``updated_at`` NOT NULL, and the initial schema created
them that way, but the migrations that added the control-panel, poller-resilience and Build
Incident tables declared them nullable — so ``alembic revision --autogenerate`` against an
upgraded database was never empty. Any NULL left by a hand insert is stamped ``now()`` first so
the constraint can be applied.

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-11-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "setting_overrides",
    "ingest_jobs",
    "poller_heartbeats",
    "build_quarantines",
    "build_incidents",
)
_COLUMNS = ("created_at", "updated_at")


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        for column in _COLUMNS:
            op.execute(sa.text(f"UPDATE {table} SET {column} = now() WHERE {column} IS NULL"))
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_server_default=sa.func.now(),
                nullable=False,
            )


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(_TABLES):
        for column in reversed(_COLUMNS):
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_server_default=sa.func.now(),
                nullable=True,
            )
