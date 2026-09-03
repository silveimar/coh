"""Initial COH persistence schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables for COH domain entities."""

    # Specifications table
    op.create_table(
        "specifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("what", sa.Text(), nullable=False),
        sa.Column("why", sa.Text(), nullable=False),
        sa.Column("deliverable", sa.Text(), nullable=False),
        sa.Column("done_when", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("non_goals", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("unknowns", sa.JSON(), nullable=False),
        sa.Column("clarity", sa.String(20), nullable=False),
        sa.Column("readiness", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
    )

    # Execution sessions table
    op.create_table(
        "execution_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("intent", sa.String(50), nullable=False),
        sa.Column("lifecycle_state", sa.String(50), nullable=False),
        sa.Column("current_spec_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["current_spec_id"], ["specifications.id"]),
    )
    op.create_index(
        "ix_sessions_project_created",
        "execution_sessions",
        ["project_id", "created_at"],
    )

    # Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("spec_id", sa.String(36), nullable=False),
        sa.Column("spec_revision", sa.Integer(), nullable=False),
        sa.Column("action_literal", sa.Text(), nullable=True),
        sa.Column("done_when_condition", sa.Text(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("energy", sa.String(20), nullable=True),
        sa.Column("activation_friction", sa.String(20), nullable=True),
        sa.Column("goal_leverage", sa.Float(), nullable=False, default=0.5),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completion_state", sa.String(20), nullable=False),
        sa.Column("foreground_position", sa.String(20), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["spec_id"], ["specifications.id"]),
    )
    op.create_index("ix_tasks_spec_status", "tasks", ["spec_id", "status"])

    # Evidence table
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("spec_id", sa.String(36), nullable=False),
        sa.Column("spec_revision", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.String(36), nullable=False),
        sa.Column("evidence_type", sa.String(100), nullable=False),
        sa.Column("authority", sa.String(50), nullable=False),
        sa.Column("result", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("archive_reference", sa.JSON(), nullable=True),
        sa.Column("tool_reference", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("user_acceptance_rationale", sa.Text(), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(["spec_id"], ["specifications.id"]),
    )
    op.create_index("ix_evidence_criterion", "evidence", ["spec_id", "criterion_id"])

    # Checkpoints table
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("lifecycle_state", sa.String(50), nullable=False),
        sa.Column("spec_snapshot", sa.JSON(), nullable=True),
        sa.Column("spec_id", sa.String(36), nullable=True),
        sa.Column("spec_revision", sa.Integer(), nullable=True),
        sa.Column("current_task_id", sa.String(36), nullable=True),
        sa.Column("restart_action", sa.Text(), nullable=False),
        sa.Column("archive_status", sa.String(20), nullable=False),
        sa.Column("archive_references", sa.JSON(), nullable=False),
        sa.Column("material_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("checkpoint_reason", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["execution_sessions.id"]),
    )
    op.create_index(
        "ix_checkpoints_session_created", "checkpoints", ["session_id", "created_at"]
    )

    # Decisions table
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("selected_option", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("material", sa.Boolean(), nullable=False),
        sa.Column("lifecycle", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_by", sa.String(36), nullable=True),
        sa.Column("reopened_at", sa.DateTime(), nullable=True),
        sa.Column("reopening_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_decisions_lifecycle", "decisions", ["lifecycle"])

    # Parking items table
    op.create_table(
        "parking_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_task_id", sa.String(36), nullable=True),
        sa.Column("source_context", sa.Text(), nullable=True),
        sa.Column("relevance", sa.String(20), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("suggested_disposition", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revisit_trigger", sa.Text(), nullable=True),
        sa.Column("auto_parked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("promoted_to_task_id", sa.String(36), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_parking_status", "parking_items", ["status"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("parking_items")
    op.drop_table("decisions")
    op.drop_table("checkpoints")
    op.drop_table("evidence")
    op.drop_table("tasks")
    op.drop_table("execution_sessions")
    op.drop_table("specifications")
