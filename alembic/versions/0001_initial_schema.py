"""Initial schema — Milestone 1 full Information model.

Revision ID: 0001
Revises: —
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pg_trgm is required for fuzzy similarity search on kb_signatures.sig_text.
    # IF NOT EXISTS is safe to run multiple times.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("build_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("url", sa.String(512), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("complete", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("baseline_run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=True),
    )
    op.create_index("ix_runs_build_number", "runs", ["build_number"], unique=True)
    op.create_index("ix_runs_baseline_run_id", "runs", ["baseline_run_id"])

    op.create_table(
        "run_shards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("track", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "track", name="uq_run_shard_track"),
    )
    op.create_index("ix_run_shards_run_id", "run_shards", ["run_id"])

    op.create_table(
        "test_identity",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("test_id", sa.String(512), nullable=False),
        sa.Column("suite", sa.String(256), nullable=True),
        sa.Column("class_name", sa.String(256), nullable=False),
        sa.Column("method", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("alias_of_id", sa.Integer, sa.ForeignKey("test_identity.id"), nullable=True),
        sa.Column("alias_confirmed", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_test_identity_test_id", "test_identity", ["test_id"], unique=True)
    op.create_index("ix_test_identity_alias_of_id", "test_identity", ["alias_of_id"])

    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("test_id", sa.String(512), nullable=False),
        sa.Column(
            "test_identity_id",
            sa.Integer,
            sa.ForeignKey("test_identity.id"),
            nullable=True,
        ),
        sa.Column("track", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("duration", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("file_path", sa.String(512), nullable=True),
        sa.Column("line", sa.Integer, nullable=True),
        sa.Column("owner_initials", sa.String(32), nullable=True),
        sa.Column("error_details", sa.Text, nullable=True),
        sa.Column("error_stack_trace", sa.Text, nullable=True),
        sa.UniqueConstraint("run_id", "test_id", "track", name="uq_run_test_track"),
    )
    op.create_index("ix_test_results_run_id", "test_results", ["run_id"])
    op.create_index("ix_test_results_test_id", "test_results", ["test_id"])
    op.create_index("ix_test_results_test_identity_id", "test_results", ["test_identity_id"])

    op.create_table(
        "test_lifecycle",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "test_identity_id",
            sa.Integer,
            sa.ForeignKey("test_identity.id"),
            nullable=False,
        ),
        sa.Column("state", sa.String(16), nullable=False, server_default="FAILING"),
        sa.Column("flaky", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reopen_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("acknowledged_by", sa.String(128), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_test_lifecycle_test_identity_id", "test_lifecycle", ["test_identity_id"], unique=True
    )

    op.create_table(
        "failure_episodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "test_identity_id",
            sa.Integer,
            sa.ForeignKey("test_identity.id"),
            nullable=False,
        ),
        sa.Column("episode_number", sa.Integer, nullable=False),
        sa.Column("first_failure_run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("fixed_in_run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("cause", sa.String(32), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("provenance", sa.String(32), nullable=True),
        sa.Column("original_ai_value", sa.Text, nullable=True),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("causing_person", sa.String(128), nullable=True),
        sa.Column("triage_status", sa.String(32), nullable=False, server_default="UNTRIAGED"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("test_identity_id", "episode_number", name="uq_episode_per_test"),
    )
    op.create_index(
        "ix_failure_episodes_test_identity_id", "failure_episodes", ["test_identity_id"]
    )
    op.create_index(
        "ix_failure_episodes_first_failure_run_id",
        "failure_episodes",
        ["first_failure_run_id"],
    )
    op.create_index("ix_failure_episodes_fixed_in_run_id", "failure_episodes", ["fixed_in_run_id"])

    op.create_table(
        "run_signals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("signal_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("details", sa.JSON, nullable=True),
    )
    op.create_index("ix_run_signals_run_id", "run_signals", ["run_id"])

    op.create_table(
        "test_classifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column(
            "test_identity_id",
            sa.Integer,
            sa.ForeignKey("test_identity.id"),
            nullable=False,
        ),
        sa.Column("predicted_cause", sa.String(32), nullable=True),
        sa.Column("llm_hypothesis", sa.Text, nullable=True),
        sa.Column("suggested_contact", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("run_id", "test_identity_id", name="uq_classification_run_test"),
    )
    op.create_index("ix_test_classifications_run_id", "test_classifications", ["run_id"])
    op.create_index(
        "ix_test_classifications_test_identity_id",
        "test_classifications",
        ["test_identity_id"],
    )

    op.create_table(
        "kb_signatures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sig_hash", sa.String(64), nullable=False),
        sa.Column("sig_text", sa.Text, nullable=False),
        sa.Column(
            "test_identity_id",
            sa.Integer,
            sa.ForeignKey("test_identity.id"),
            nullable=False,
        ),
        sa.Column("episode_id", sa.Integer, sa.ForeignKey("failure_episodes.id"), nullable=True),
        sa.Column("confirmed_cause", sa.String(32), nullable=True),
        sa.Column("confirmed_reason", sa.Text, nullable=True),
        sa.Column("provenance", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_kb_signatures_sig_hash", "kb_signatures", ["sig_hash"], unique=True)
    op.create_index("ix_kb_signatures_test_identity_id", "kb_signatures", ["test_identity_id"])
    op.create_index("ix_kb_signatures_episode_id", "kb_signatures", ["episode_id"])

    # GIN/pg_trgm index for fuzzy similarity search on normalized error text.
    # Enables: ORDER BY similarity(sig_text, :query) DESC LIMIT k
    op.execute(
        "CREATE INDEX kb_sigs_text_trgm_idx ON kb_signatures USING GIN (sig_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS kb_sigs_text_trgm_idx")
    op.drop_table("kb_signatures")
    op.drop_table("test_classifications")
    op.drop_table("run_signals")
    op.drop_table("failure_episodes")
    op.drop_table("test_lifecycle")
    op.drop_table("test_results")
    op.drop_table("test_identity")
    op.drop_table("run_shards")
    op.drop_table("runs")
    # Leave pg_trgm installed — it may be used by other extensions.
