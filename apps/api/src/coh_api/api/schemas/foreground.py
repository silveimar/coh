"""Foreground request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class TaskMetadata(BaseModel):
    """Task metadata for NOW/NEXT display."""

    task_id: str
    action_literal: str | None = None
    done_when_condition: str | None = None
    estimated_minutes: int | None = None
    energy: str | None = None  # low|medium|high
    activation_friction: str | None = None  # low|medium|high


class ForegroundResponse(BaseModel):
    """Foreground execution response."""

    goal: str
    now_task: TaskMetadata | None = None
    next_1_task: TaskMetadata | None = None
    next_2_task: TaskMetadata | None = None
    parked_count: int
    background_count: int


class CompleteNowTaskRequest(BaseModel):
    """Request to complete NOW task."""

    session_id: UUID
    task_id: UUID
    completion_notes: str | None = None
    idempotency_key: str
    expected_version: int | None = None


class BlockNowTaskRequest(BaseModel):
    """Request to block NOW task."""

    session_id: UUID
    task_id: UUID
    reason: str = Field(..., min_length=1)
    idempotency_key: str
    expected_version: int | None = None


class ParkTaskRequest(BaseModel):
    """Request to park a task."""

    session_id: UUID
    task_id: UUID
    reason: str = Field(..., min_length=1)
    idempotency_key: str
    expected_version: int | None = None


class InterruptNowTaskRequest(BaseModel):
    """Request to interrupt NOW task."""

    session_id: UUID
    task_id: UUID
    completed_work: list[str]
    next_steps: list[str]
    idempotency_key: str
    expected_version: int | None = None


class ForegroundStatusResponse(BaseModel):
    """Response for foreground status (read-only)."""

    goal: str | None = None
    now_task_id: str | None = None
    next_1_id: str | None = None
    next_2_id: str | None = None
    parked_count: int = 0
    background_count: int = 0
