"""Task domain model with foreground metadata and dependencies."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import (
    ActivationFriction,
    CompletionState,
    EnergyLevel,
    ForegroundPosition,
    TaskStatus,
)


class TaskDependency(BaseModel):
    """Dependency relationship between tasks."""

    task_id: UUID
    dependency_type: str = "blocks"


class Task(BaseModel):
    """An atomic, dependency-aware unit of work."""

    id: UUID = Field(default_factory=uuid4)
    spec_id: UUID
    spec_revision: int
    action_literal: str | None = None
    done_when_condition: str | None = None
    estimated_minutes: int | None = None
    energy: EnergyLevel | None = None
    activation_friction: ActivationFriction | None = None
    goal_leverage: float = 0.5
    status: TaskStatus = TaskStatus.PLANNED
    completion_state: CompletionState = CompletionState.IMPLEMENTED
    foreground_position: ForegroundPosition = ForegroundPosition.BACKGROUND
    dependencies: list[TaskDependency] = Field(default_factory=list)
    blocked_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def is_foreground_eligible(self) -> bool:
        """Check if task can enter the foreground (NOW or NEXT)."""
        if self.status not in [TaskStatus.PLANNED, TaskStatus.IN_PROGRESS]:
            return False

        if not all(
            [
                self.action_literal,
                self.done_when_condition,
                self.estimated_minutes,
                self.energy,
                self.activation_friction,
            ]
        ):
            return False

        return True

    def has_unresolved_dependencies(
        self, completed_task_ids: set[UUID]
    ) -> tuple[bool, list[UUID]]:
        """Check if task has dependencies that are not yet completed."""
        unresolved = [
            dep.task_id
            for dep in self.dependencies
            if dep.task_id not in completed_task_ids
        ]
        return len(unresolved) > 0, unresolved

    def mark_started(self) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_blocked(self, reason: str) -> None:
        """Mark task as blocked with a reason."""
        self.status = TaskStatus.BLOCKED
        self.blocked_reason = reason
        self.updated_at = datetime.utcnow()

    def park(self) -> None:
        """Park the task without changing NOW."""
        self.status = TaskStatus.PARKED
        self.foreground_position = ForegroundPosition.BACKGROUND
        self.updated_at = datetime.utcnow()

    def abandon(self) -> None:
        """Mark task as abandoned."""
        self.status = TaskStatus.ABANDONED
        self.foreground_position = ForegroundPosition.BACKGROUND
        self.updated_at = datetime.utcnow()


class TaskProgressRecord(BaseModel):
    """Interruption-safe progress record for a task."""

    task_id: UUID
    status: TaskStatus
    last_update: datetime = Field(default_factory=datetime.utcnow)
    completed_work: list[str] = Field(default_factory=list)
    attempted_work: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revision: int = 1

    def create_revision(self) -> "TaskProgressRecord":
        """Create a new revision superseding this one."""
        new_record = self.model_copy(deep=True)
        new_record.revision = self.revision + 1
        new_record.created_at = datetime.utcnow()
        new_record.last_update = datetime.utcnow()
        return new_record
