"""Command types for state mutations with idempotency and concurrency control."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .specification import Specification


class Command(BaseModel):
    """Base command with idempotency and optimistic concurrency."""

    idempotency_key: str
    expected_version: int
    source: str = "user"  # Source of command: user, repository, tool_output
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StartSessionCommand(Command):
    """Command to start a new execution session."""

    project_id: str
    intent: str


class TransitionToSpecifyCommand(Command):
    """Command to transition from INSPECT to SPECIFY."""

    session_id: UUID
    findings_archived: bool


class ConfirmSpecCommand(Command):
    """Command to confirm or correct a specification."""

    session_id: UUID
    spec: Specification
    user_confirmed: bool


class TransitionToPlanCommand(Command):
    """Command to transition from CONFIRM to PLAN."""

    session_id: UUID
    user_confirmed: bool


class TransitionToExecuteCommand(Command):
    """Command to transition from PLAN to EXECUTE."""

    session_id: UUID


class TransitionToVerifyCommand(Command):
    """Command to transition from EXECUTE to VERIFY."""

    session_id: UUID


class CompleteVerificationCommand(Command):
    """Command to complete verification and transition to COMPLETE."""

    session_id: UUID
    evidence_ids: list[UUID]


class ReviseGoalCommand(Command):
    """Command to revise goal (T10) - must checkpoint first."""

    session_id: UUID
    checkpoint_id: UUID
    new_spec: Specification


class RecoverCommand(Command):
    """Command to recover from checkpoint (T11)."""

    session_id: UUID
    checkpoint_id: UUID


class CommandHistory(BaseModel):
    """Track processed commands for idempotency."""

    processed_keys: dict[str, UUID] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if command has already been processed."""
        return idempotency_key in self.processed_keys

    def record(self, idempotency_key: str, command_id: UUID) -> None:
        """Record a processed command."""
        self.processed_keys[idempotency_key] = command_id
        self.last_updated = datetime.now(UTC)


class ConcurrencyError(Exception):
    """Raised when expected_version does not match current version."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Concurrency conflict: expected version {expected}, "
            f"actual version {actual}"
        )
        self.expected_version = expected
        self.actual_version = actual


class DuplicateCommandError(Exception):
    """Raised when idempotency_key has already been processed."""

    def __init__(self, idempotency_key: str):
        super().__init__(
            f"Command with idempotency_key '{idempotency_key}' already processed"
        )
        self.idempotency_key = idempotency_key
