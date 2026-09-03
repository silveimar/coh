"""SQLAlchemy declarative models for COH domain entities.

These models map to the execution_core domain layer.
Nested Pydantic models are stored as JSON.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from execution_core.domain.enums import (
    ActivationFriction,
    ArchiveStatus,
    Clarity,
    CompletionState,
    DecisionLifecycle,
    EnergyLevel,
    EvidenceAuthority,
    EvidenceResult,
    ForegroundPosition,
    LifecycleState,
    ParkingItemStatus,
    Readiness,
    RelevanceLevel,
    SessionIntent,
    TaskStatus,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class ExecutionSessionModel(Base):
    """ORM model for ExecutionSession aggregate root."""

    __tablename__ = "execution_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(String(255), index=True)
    intent: Mapped[SessionIntent] = mapped_column(Enum(SessionIntent))
    lifecycle_state: Mapped[LifecycleState] = mapped_column(Enum(LifecycleState))
    current_spec_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("specifications.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (Index("ix_sessions_project_created", project_id, created_at),)


class SpecificationModel(Base):
    """ORM model for Specification entity."""

    __tablename__ = "specifications"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    deliverable: Mapped[str] = mapped_column(Text)
    done_when: Mapped[dict] = mapped_column(JSON)
    constraints: Mapped[dict] = mapped_column(JSON)
    non_goals: Mapped[dict] = mapped_column(JSON)
    assumptions: Mapped[dict] = mapped_column(JSON)
    unknowns: Mapped[dict] = mapped_column(JSON)
    clarity: Mapped[Clarity] = mapped_column(Enum(Clarity))
    readiness: Mapped[Readiness] = mapped_column(Enum(Readiness))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskModel(Base):
    """ORM model for Task entity."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    spec_id: Mapped[UUID] = mapped_column(ForeignKey("specifications.id"), index=True)
    spec_revision: Mapped[int] = mapped_column(Integer)
    action_literal: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_when_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[EnergyLevel | None] = mapped_column(Enum(EnergyLevel), nullable=True)
    activation_friction: Mapped[ActivationFriction | None] = mapped_column(
        Enum(ActivationFriction), nullable=True
    )
    goal_leverage: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus))
    completion_state: Mapped[CompletionState] = mapped_column(Enum(CompletionState))
    foreground_position: Mapped[ForegroundPosition] = mapped_column(
        Enum(ForegroundPosition)
    )
    dependencies: Mapped[dict] = mapped_column(JSON)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_tasks_spec_status", spec_id, status),)


class EvidenceModel(Base):
    """ORM model for Evidence entity."""

    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    spec_id: Mapped[UUID] = mapped_column(ForeignKey("specifications.id"), index=True)
    spec_revision: Mapped[int] = mapped_column(Integer)
    criterion_id: Mapped[UUID] = mapped_column(index=True)
    evidence_type: Mapped[str] = mapped_column(String(100))
    authority: Mapped[EvidenceAuthority] = mapped_column(Enum(EvidenceAuthority))
    result: Mapped[EvidenceResult] = mapped_column(Enum(EvidenceResult))
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    archive_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime)
    user_acceptance_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_evidence_criterion", spec_id, criterion_id),)


class CheckpointModel(Base):
    """ORM model for Checkpoint entity."""

    __tablename__ = "checkpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_sessions.id"), index=True
    )
    lifecycle_state: Mapped[LifecycleState] = mapped_column(Enum(LifecycleState))
    spec_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    spec_id: Mapped[UUID | None] = mapped_column(nullable=True)
    spec_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_task_id: Mapped[UUID | None] = mapped_column(nullable=True)
    restart_action: Mapped[str] = mapped_column(Text)
    archive_status: Mapped[ArchiveStatus] = mapped_column(Enum(ArchiveStatus))
    archive_references: Mapped[dict] = mapped_column(JSON)
    material_context: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    checkpoint_reason: Mapped[str] = mapped_column(String(100))

    __table_args__ = (Index("ix_checkpoints_session_created", session_id, created_at),)


class DecisionModel(Base):
    """ORM model for Decision entity."""

    __tablename__ = "decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    selected_option: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    alternatives: Mapped[dict] = mapped_column(JSON)
    evidence_refs: Mapped[dict] = mapped_column(JSON)
    material: Mapped[bool] = mapped_column(Boolean)
    lifecycle: Mapped[DecisionLifecycle] = mapped_column(Enum(DecisionLifecycle))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    superseded_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reopening_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_decisions_lifecycle", lifecycle),)


class ParkingItemModel(Base):
    """ORM model for ParkingItem entity."""

    __tablename__ = "parking_items"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    source_task_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance: Mapped[RelevanceLevel] = mapped_column(Enum(RelevanceLevel))
    blocking: Mapped[bool] = mapped_column(Boolean)
    suggested_disposition: Mapped[str] = mapped_column(Text)
    status: Mapped[ParkingItemStatus] = mapped_column(Enum(ParkingItemStatus))
    revisit_trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_parked: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    promoted_to_task_id: Mapped[UUID | None] = mapped_column(nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_parking_status", status),)
