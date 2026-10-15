"""Repository protocols (ports) for persistence layer.

No SQLAlchemy or FastAPI imports allowed in this file.
"""

from typing import Protocol
from uuid import UUID

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.decision import Decision
from execution_core.domain.evidence import Evidence
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import Specification
from execution_core.domain.task import Task


class ExecutionSessionRepository(Protocol):
    """Repository for ExecutionSession aggregate root."""

    def add(
        self, session: ExecutionSession, idempotency_key: str | None = None
    ) -> None:
        """Add a new execution session."""
        ...

    def get(self, session_id: UUID) -> ExecutionSession | None:
        """Retrieve session by ID."""
        ...

    def update(
        self,
        session: ExecutionSession,
        expected_version: int,
        idempotency_key: str | None = None,
    ) -> None:
        """Update session with optimistic concurrency check."""
        ...

    def list_by_project(self, project_id: str) -> list[ExecutionSession]:
        """List all sessions for a project."""
        ...


class SpecificationRepository(Protocol):
    """Repository for Specification entity."""

    def add(self, spec: Specification, idempotency_key: str | None = None) -> None:
        """Add a new specification."""
        ...

    def get(self, spec_id: UUID) -> Specification | None:
        """Retrieve specification by ID."""
        ...

    def update(
        self,
        spec: Specification,
        idempotency_key: str | None = None,
    ) -> None:
        """Update specification."""
        ...


class TaskRepository(Protocol):
    """Repository for Task entity."""

    def add(self, task: Task, idempotency_key: str | None = None) -> None:
        """Add a new task."""
        ...

    def get(self, task_id: UUID) -> Task | None:
        """Retrieve task by ID."""
        ...

    def update(self, task: Task, idempotency_key: str | None = None) -> None:
        """Update task."""
        ...

    def list_by_spec(self, spec_id: UUID) -> list[Task]:
        """List all tasks for a specification."""
        ...


class EvidenceRepository(Protocol):
    """Repository for Evidence entity."""

    def add(self, evidence: Evidence, idempotency_key: str | None = None) -> None:
        """Add a new evidence record."""
        ...

    def get(self, evidence_id: UUID) -> Evidence | None:
        """Retrieve evidence by ID."""
        ...

    def list_by_criterion(self, spec_id: UUID, criterion_id: UUID) -> list[Evidence]:
        """List all evidence for a specific criterion."""
        ...


class CheckpointRepository(Protocol):
    """Repository for Checkpoint entity."""

    def add(self, checkpoint: Checkpoint, idempotency_key: str | None = None) -> None:
        """Add a new checkpoint."""
        ...

    def update_archive_state(self, checkpoint: Checkpoint) -> None:
        """Persist archive status and references of an existing checkpoint (I-12)."""
        ...

    def get(self, checkpoint_id: UUID) -> Checkpoint | None:
        """Retrieve checkpoint by ID."""
        ...

    def get_latest_for_session(self, session_id: UUID) -> Checkpoint | None:
        """Get most recent checkpoint for a session."""
        ...

    def list_by_session(self, session_id: UUID) -> list[Checkpoint]:
        """List all checkpoints for a session."""
        ...


class DecisionRepository(Protocol):
    """Repository for Decision entity."""

    def add(self, decision: Decision, idempotency_key: str | None = None) -> None:
        """Add a new decision."""
        ...

    def get(self, decision_id: UUID) -> Decision | None:
        """Retrieve decision by ID."""
        ...

    def list_active(self) -> list[Decision]:
        """List all active decisions."""
        ...


class ParkingItemRepository(Protocol):
    """Repository for ParkingItem entity."""

    def add(self, item: ParkingItem, idempotency_key: str | None = None) -> None:
        """Add a new parking item."""
        ...

    def get(self, item_id: UUID) -> ParkingItem | None:
        """Retrieve parking item by ID."""
        ...

    def list_active(self) -> list[ParkingItem]:
        """List all active (non-dismissed) parking items."""
        ...


class UnitOfWork(Protocol):
    """Unit of work for coordinating repository operations."""

    sessions: ExecutionSessionRepository
    specifications: SpecificationRepository
    tasks: TaskRepository
    evidence: EvidenceRepository
    checkpoints: CheckpointRepository
    decisions: DecisionRepository
    parking_items: ParkingItemRepository

    def commit(self) -> None:
        """Commit the transaction."""
        ...

    def rollback(self) -> None:
        """Rollback the transaction."""
        ...

    def __enter__(self) -> UnitOfWork:
        """Enter context manager."""
        ...

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        ...
