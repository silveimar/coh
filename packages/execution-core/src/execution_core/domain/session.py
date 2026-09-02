"""Execution session aggregate root."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import LifecycleState, SessionIntent
from .specification import Specification


class ExecutionSession(BaseModel):
    """One execution engagement on a project with lifecycle state and intent."""

    id: UUID = Field(default_factory=uuid4)
    project_id: str
    intent: SessionIntent
    lifecycle_state: LifecycleState = LifecycleState.INSPECT
    current_spec: Specification | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def increment_version(self) -> None:
        """Increment version for optimistic concurrency control."""
        self.version += 1
        self.updated_at = datetime.now(UTC)
