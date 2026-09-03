"""MCP adapter wire types (snake_case per D10)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionData(BaseModel):
    """Session wire representation."""

    id: UUID
    project_id: str
    intent: str
    lifecycle_state: str
    created_at: datetime
    last_active_at: datetime


class SpecificationData(BaseModel):
    """Specification wire representation."""

    id: UUID
    revision: int
    what: str
    why: str
    deliverable: str
    done_when: list[str] = Field(default_factory=list)
    clarity: str
    readiness: str
    blockers: list[str] = Field(default_factory=list)


class TaskData(BaseModel):
    """Task wire representation."""

    id: UUID
    name: str
    status: str
    action_literal: str | None = None
    done_when_condition: str | None = None
    estimated_minutes: int | None = None
    energy_level: str | None = None
    activation_friction: str | None = None
    foreground_position: str | None = None


class CheckpointData(BaseModel):
    """Checkpoint wire representation."""

    id: UUID
    session_id: UUID
    lifecycle_state: str
    restart_action: str
    archive_status: str
    created_at: datetime


class ArchiveIntegration(BaseModel):
    """Archive integration wiring status."""

    enabled: bool
    writes_succeeded: int = 0
    writes_failed: int = 0
    last_failure: str | None = None
