"""add Build Incidents + generalize triage fields (issue #171)

Adds the build-level triage entity (``build_incidents``), namespaces failure signatures with a
``kind`` discriminator, generalizes the classification/attribution provenance loop to reference an
incident as well as an episode, and generalizes the triage/documentation fields across both
surfaces:

- **build_incidents** table (streak of consecutive non-green builds).
- **failure_episodes**: ``jira_ticket`` renamed to ``cause_ticket`` (existing values preserved), and
  new ``resolution_ticket`` + ``assignee`` columns.
- **failure_signatures**: new ``kind`` column (default ``TEST``); ``test_identity_id`` made nullable
  (incident signatures have no test identity).
- **classifications** / **attributions**: new nullable ``incident_id`` FK; ``episode_id`` made
  nullable (a row now belongs to exactly one of an episode or an incident).

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "build_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("opened_build_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_build_id", sa.Integer(), nullable=True),
        sa.Column("last_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovered_build_id", sa.Integer(), nullable=True),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.Column("build_count", sa.Integer(), nullable=False),
        sa.Column("mixed_kinds", sa.String(length=128), nullable=True),
        sa.Column("failing_stage", sa.String(length=255), nullable=True),
        sa.Column("triage_status", sa.String(length=16), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_by", sa.String(length=128), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee", sa.String(length=128), nullable=True),
        sa.Column("cause_ticket", sa.String(length=32), nullable=True),
        sa.Column("resolution_ticket", sa.String(length=32), nullable=True),
        sa.Column("problem_text", sa.Text(), nullable=True),
        sa.Column("signature_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["opened_build_id"], ["builds.id"]),
        sa.ForeignKeyConstraint(["last_build_id"], ["builds.id"]),
        sa.ForeignKeyConstraint(["recovered_build_id"], ["builds.id"]),
        sa.ForeignKeyConstraint(["signature_id"], ["failure_signatures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_build_incidents_kind", "build_incidents", ["kind"])
    op.create_index("ix_build_incidents_opened_build_id", "build_incidents", ["opened_build_id"])
    op.create_index("ix_build_incidents_is_open", "build_incidents", ["is_open"])
    op.create_index("ix_build_incidents_signature_id", "build_incidents", ["signature_id"])
    op.create_index("ix_build_incidents_acknowledged", "build_incidents", ["acknowledged"])

    # failure_episodes: rename the ticket (values preserved) + the two new generalized fields.
    op.alter_column("failure_episodes", "jira_ticket", new_column_name="cause_ticket")
    op.add_column(
        "failure_episodes", sa.Column("resolution_ticket", sa.String(length=32), nullable=True)
    )
    op.add_column("failure_episodes", sa.Column("assignee", sa.String(length=128), nullable=True))

    # failure_signatures: namespace + nullable identity for incident signatures.
    op.add_column(
        "failure_signatures",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="TEST"),
    )
    op.create_index("ix_failure_signatures_kind", "failure_signatures", ["kind"])
    op.alter_column(
        "failure_signatures", "test_identity_id", existing_type=sa.Integer(), nullable=True
    )

    # classifications / attributions: generalize to reference an incident.
    op.add_column("classifications", sa.Column("incident_id", sa.Integer(), nullable=True))
    op.create_index("ix_classifications_incident_id", "classifications", ["incident_id"])
    op.create_foreign_key(
        "fk_classifications_incident", "classifications", "build_incidents", ["incident_id"], ["id"]
    )
    op.alter_column("classifications", "episode_id", existing_type=sa.Integer(), nullable=True)

    op.add_column("attributions", sa.Column("incident_id", sa.Integer(), nullable=True))
    op.create_index("ix_attributions_incident_id", "attributions", ["incident_id"], unique=True)
    op.create_foreign_key(
        "fk_attributions_incident", "attributions", "build_incidents", ["incident_id"], ["id"]
    )
    op.alter_column("attributions", "episode_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("attributions", "episode_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_attributions_incident", "attributions", type_="foreignkey")
    op.drop_index("ix_attributions_incident_id", "attributions")
    op.drop_column("attributions", "incident_id")

    op.alter_column("classifications", "episode_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_classifications_incident", "classifications", type_="foreignkey")
    op.drop_index("ix_classifications_incident_id", "classifications")
    op.drop_column("classifications", "incident_id")

    op.alter_column(
        "failure_signatures", "test_identity_id", existing_type=sa.Integer(), nullable=False
    )
    op.drop_index("ix_failure_signatures_kind", "failure_signatures")
    op.drop_column("failure_signatures", "kind")

    op.drop_column("failure_episodes", "assignee")
    op.drop_column("failure_episodes", "resolution_ticket")
    op.alter_column("failure_episodes", "cause_ticket", new_column_name="jira_ticket")

    op.drop_index("ix_build_incidents_acknowledged", "build_incidents")
    op.drop_index("ix_build_incidents_signature_id", "build_incidents")
    op.drop_index("ix_build_incidents_is_open", "build_incidents")
    op.drop_index("ix_build_incidents_opened_build_id", "build_incidents")
    op.drop_index("ix_build_incidents_kind", "build_incidents")
    op.drop_table("build_incidents")
