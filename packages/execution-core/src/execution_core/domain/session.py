"""Execution session aggregate root."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .clock import utc_now_naive
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
    created_at: datetime = Field(default_factory=utc_now_naive)
    updated_at: datetime = Field(default_factory=utc_now_naive)
    checkpoints: list[Checkpoint] = Field(default_factory=list)

    def increment_version(self) -> None:
        """Increment version for optimistic concurrency control."""
        self.version += 1
        self.updated_at = datetime.now(UTC)

    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Add checkpoint to session history."""
        self.checkpoints.append(checkpoint)

    def get_latest_checkpoint(self) -> Checkpoint | None:
        """Get most recent checkpoint for this session."""
        if not self.checkpoints:
            return None
        return max(self.checkpoints, key=lambda c: c.created_at)


from .checkpoint import Checkpoint  # noqa: E402

ExecutionSession.model_rebuild()
