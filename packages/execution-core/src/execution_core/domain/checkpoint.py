"""Checkpoint and recovery domain models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import ArchiveStatus, LifecycleState


class ArchiveReference(BaseModel):
    """Reference to a specific archive entry."""

    path: str
    timestamp: datetime
    anchor: str


class Checkpoint(BaseModel):
    """Persisted recovery record with literal restart action."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    lifecycle_state: LifecycleState
    spec_snapshot: Specification | None = None
    spec_id: UUID | None = None
    spec_revision: int | None = None
    current_task_id: UUID | None = None
    restart_action: str
    archive_status: ArchiveStatus = ArchiveStatus.HEALTHY
    archive_references: list[ArchiveReference] = Field(default_factory=list)
    material_context: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checkpoint_reason: str = "manual"

    def mark_degraded(self) -> None:
        """Mark archive status as degraded due to write failure."""
        self.archive_status = ArchiveStatus.DEGRADED


from ..domain.specification import Specification  # noqa: E402

Checkpoint.model_rebuild()


class RecoverySummary(BaseModel):
    """Structured output for resuming a session."""

    goal: str
    why: str
    last_verified: str | None = None
    last_decision: str | None = None
    last_decision_rationale: str | None = None
    now_task: str | None = None
    next_tasks: list[str] = Field(default_factory=list)
    parked_count: int = 0
    restart_action: str
    archive_degraded: bool = False
    archive_references: list[ArchiveReference] = Field(default_factory=list)
    checkpoint_id: UUID
