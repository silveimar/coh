"""Domain events for audit and event stream."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..domain.enums import LifecycleState


class DomainEvent(BaseModel):
    """Base class for all domain events."""

    id: UUID = Field(default_factory=uuid4)
    event_type: str
    session_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionStarted(DomainEvent):
    """Session creation event (T1)."""

    event_type: str = "session_started"
    project_id: str
    intent: str


class StateTransitioned(DomainEvent):
    """Lifecycle state transition event."""

    event_type: str = "state_transitioned"
    from_state: LifecycleState
    to_state: LifecycleState
    transition_id: str


class SpecProposed(DomainEvent):
    """Spec proposal event."""

    event_type: str = "spec_proposed"
    spec_id: UUID
    spec_revision: int


class SpecConfirmed(DomainEvent):
    """Spec confirmation event."""

    event_type: str = "spec_confirmed"
    spec_id: UUID
    spec_revision: int
    user_confirmed: bool


class SpecCorrected(DomainEvent):
    """Spec correction event (T5)."""

    event_type: str = "spec_corrected"
    old_spec_id: UUID
    new_spec_id: UUID
    new_revision: int


class ReadinessChanged(DomainEvent):
    """Readiness status change event."""

    event_type: str = "readiness_changed"
    spec_id: UUID
    old_readiness: str
    new_readiness: str
    blockers: list[str]


class TaskCreated(DomainEvent):
    """Task creation event."""

    event_type: str = "task_created"
    task_id: UUID
    spec_id: UUID


class TaskStatusChanged(DomainEvent):
    """Task status change event."""

    event_type: str = "task_status_changed"
    task_id: UUID
    old_status: str
    new_status: str
    reason: str | None = None


class ForegroundCalculated(DomainEvent):
    """Foreground calculation event."""

    event_type: str = "foreground_calculated"
    now_task_id: UUID | None = None
    next_task_ids: list[UUID] = Field(default_factory=list)
    parked_count: int


class EvidenceRecorded(DomainEvent):
    """Evidence recording event."""

    event_type: str = "evidence_recorded"
    evidence_id: UUID
    criterion_id: UUID
    result: str
    authority: str


class CompletionStateChanged(DomainEvent):
    """Completion state change event."""

    event_type: str = "completion_state_changed"
    task_id: UUID
    old_state: str
    new_state: str


class CheckpointCreated(DomainEvent):
    """Checkpoint creation event."""

    event_type: str = "checkpoint_created"
    checkpoint_id: UUID
    lifecycle_state: LifecycleState
    restart_action: str
    archive_status: str


class RecoveryInitiated(DomainEvent):
    """Recovery command event (T11)."""

    event_type: str = "recovery_initiated"
    checkpoint_id: UUID
    restored_state: LifecycleState


class DecisionRecorded(DomainEvent):
    """Decision recording event."""

    event_type: str = "decision_recorded"
    decision_id: UUID
    material: bool


class ParkingItemCreated(DomainEvent):
    """Parking item creation event."""

    event_type: str = "parking_item_created"
    parking_item_id: UUID
    relevance: str
    blocking: bool
    auto_parked: bool


class ArchiveRecorded(DomainEvent):
    """Archive write success event."""

    event_type: str = "archive_recorded"
    path: str
    anchor: str


class ArchiveWriteFailed(DomainEvent):
    """Archive write failure event (I-12)."""

    event_type: str = "archive_write_failed"
    reason: str
    checkpoint_id: UUID | None = None
