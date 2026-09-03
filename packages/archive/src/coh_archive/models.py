"""Archive domain models and configuration."""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field


class Actor(StrEnum):
    """Event actor type."""

    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


class EventStatus(StrEnum):
    """Tool event execution status."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WriteOutcome(StrEnum):
    """Archive write operation outcome."""

    WRITTEN = "written"
    QUEUED = "queued"
    SKIPPED_DISABLED = "skipped_disabled"
    ARCHIVE_WRITE_FAILED = "archive_write_failed"


class ArchiveConfig(BaseModel):
    """Archive configuration."""

    enabled: bool = True
    directory: str = ".coh/archive"
    allow_external_path: bool = False
    max_inline_payload_bytes: int = 1024 * 100  # 100 KB
    rotation_threshold_bytes: int = 5 * 1024 * 1024  # 5 MB


class ArchiveEvent(BaseModel):
    """Normalized archive event for user/agent interactions."""

    actor: Actor
    time: datetime
    session_id: UUID
    project_id: str
    content: str
    goal_id: UUID | None = None
    task_id: UUID | None = None
    state_transition: str | None = None
    checkpoint_id: UUID | None = None


class ToolEvent(BaseModel):
    """Tool invocation archive event."""

    actor: Actor = Actor.TOOL
    time: datetime
    session_id: UUID
    project_id: str
    tool_name: str
    status: EventStatus
    invocation_time: datetime
    result_time: datetime | None = None
    input_payload: dict[str, object] | None = None
    output_payload: dict[str, object] | None = None
    artifact_paths: list[str] = Field(default_factory=list)


class ArchivePointer(BaseModel):
    """Reference to a specific archive entry."""

    path: str
    entry_id: str
    timestamp: datetime


class ArchiveWriteResult(BaseModel):
    """Result of an archive write operation."""

    outcome: WriteOutcome
    pointer: ArchivePointer | None = None
    error: str | None = None
    project_root: Path | None = None
    resolved_path: Path | None = None
