"""SQLAlchemy repository implementations with optimistic concurrency."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.decision import Decision
from execution_core.domain.evidence import Evidence
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import Specification
from execution_core.domain.task import Task

from .mappers import (
    CheckpointMapper,
    DecisionMapper,
    EvidenceMapper,
    ExecutionSessionMapper,
    ParkingItemMapper,
    SpecificationMapper,
    TaskMapper,
)
from .models import (
    CheckpointModel,
    DecisionModel,
    EvidenceModel,
    ExecutionSessionModel,
    ParkingItemModel,
    SpecificationModel,
    TaskModel,
)


class OptimisticLockError(Exception):
    """Raised when optimistic concurrency check fails."""

    pass


class IdempotencyKeyViolation(Exception):
    """Raised when idempotency key already exists."""

    pass


class SqlExecutionSessionRepository:
    """SQLAlchemy implementation of ExecutionSessionRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(
        self, session: ExecutionSession, idempotency_key: str | None = None
    ) -> None:
        """Add a new execution session."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != session.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = session.id

        model = ExecutionSessionMapper.to_model(session)
        self._session.add(model)

    def get(self, session_id: UUID) -> ExecutionSession | None:
        """Retrieve session by ID."""
        stmt = select(ExecutionSessionModel).where(
            ExecutionSessionModel.id == session_id
        )
        model = self._session.scalar(stmt)
        if not model:
            return None
        return ExecutionSessionMapper.to_domain(model)

    def update(
        self,
        session: ExecutionSession,
        expected_version: int,
        idempotency_key: str | None = None,
    ) -> None:
        """Update session with optimistic concurrency check."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                return

        stmt = select(ExecutionSessionModel).where(
            ExecutionSessionModel.id == session.id
        )
        model = self._session.scalar(stmt)
        if not model:
            raise ValueError(f"Session {session.id} not found")

        if model.version != expected_version:
            raise OptimisticLockError(
                f"Expected version {expected_version}, got {model.version}"
            )

        ExecutionSessionMapper.update_model(model, session)

        if idempotency_key:
            self._idempotency_keys[idempotency_key] = session.id

    def list_by_project(self, project_id: str) -> list[ExecutionSession]:
        """List all sessions for a project."""
        stmt = (
            select(ExecutionSessionModel)
            .where(ExecutionSessionModel.project_id == project_id)
            .order_by(ExecutionSessionModel.created_at.desc())
        )
        models = self._session.scalars(stmt).all()
        return [ExecutionSessionMapper.to_domain(m) for m in models]


class SqlSpecificationRepository:
    """SQLAlchemy implementation of SpecificationRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, spec: Specification, idempotency_key: str | None = None) -> None:
        """Add a new specification."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != spec.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = spec.id

        model = SpecificationMapper.to_model(spec)
        self._session.add(model)

    def get(self, spec_id: UUID) -> Specification | None:
        """Retrieve specification by ID."""
        stmt = select(SpecificationModel).where(SpecificationModel.id == spec_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return SpecificationMapper.to_domain(model)

    def update(self, spec: Specification, idempotency_key: str | None = None) -> None:
        """Update specification."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                return

        stmt = select(SpecificationModel).where(SpecificationModel.id == spec.id)
        model = self._session.scalar(stmt)
        if not model:
            raise ValueError(f"Specification {spec.id} not found")

        SpecificationMapper.update_model(model, spec)

        if idempotency_key:
            self._idempotency_keys[idempotency_key] = spec.id


class SqlTaskRepository:
    """SQLAlchemy implementation of TaskRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, task: Task, idempotency_key: str | None = None) -> None:
        """Add a new task."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != task.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = task.id

        model = TaskMapper.to_model(task)
        self._session.add(model)

    def get(self, task_id: UUID) -> Task | None:
        """Retrieve task by ID."""
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return TaskMapper.to_domain(model)

    def update(self, task: Task, idempotency_key: str | None = None) -> None:
        """Update task."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                return

        stmt = select(TaskModel).where(TaskModel.id == task.id)
        model = self._session.scalar(stmt)
        if not model:
            raise ValueError(f"Task {task.id} not found")

        TaskMapper.update_model(model, task)

        if idempotency_key:
            self._idempotency_keys[idempotency_key] = task.id

    def list_by_spec(self, spec_id: UUID) -> list[Task]:
        """List all tasks for a specification."""
        stmt = (
            select(TaskModel)
            .where(TaskModel.spec_id == spec_id)
            .order_by(TaskModel.created_at)
        )
        models = self._session.scalars(stmt).all()
        return [TaskMapper.to_domain(m) for m in models]


class SqlEvidenceRepository:
    """SQLAlchemy implementation of EvidenceRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, evidence: Evidence, idempotency_key: str | None = None) -> None:
        """Add a new evidence record."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != evidence.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = evidence.id

        model = EvidenceMapper.to_model(evidence)
        self._session.add(model)

    def get(self, evidence_id: UUID) -> Evidence | None:
        """Retrieve evidence by ID."""
        stmt = select(EvidenceModel).where(EvidenceModel.id == evidence_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return EvidenceMapper.to_domain(model)

    def list_by_criterion(self, spec_id: UUID, criterion_id: UUID) -> list[Evidence]:
        """List all evidence for a specific criterion."""
        stmt = (
            select(EvidenceModel)
            .where(
                EvidenceModel.spec_id == spec_id,
                EvidenceModel.criterion_id == criterion_id,
            )
            .order_by(EvidenceModel.recorded_at)
        )
        models = self._session.scalars(stmt).all()
        return [EvidenceMapper.to_domain(m) for m in models]


class SqlCheckpointRepository:
    """SQLAlchemy implementation of CheckpointRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, checkpoint: Checkpoint, idempotency_key: str | None = None) -> None:
        """Add a new checkpoint."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != checkpoint.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = checkpoint.id

        model = CheckpointMapper.to_model(checkpoint)
        self._session.add(model)

    def get(self, checkpoint_id: UUID) -> Checkpoint | None:
        """Retrieve checkpoint by ID."""
        stmt = select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return CheckpointMapper.to_domain(model)

    def get_latest_for_session(self, session_id: UUID) -> Checkpoint | None:
        """Get most recent checkpoint for a session."""
        stmt = (
            select(CheckpointModel)
            .where(CheckpointModel.session_id == session_id)
            .order_by(CheckpointModel.created_at.desc())
            .limit(1)
        )
        model = self._session.scalar(stmt)
        if not model:
            return None
        return CheckpointMapper.to_domain(model)

    def list_by_session(self, session_id: UUID) -> list[Checkpoint]:
        """List all checkpoints for a session."""
        stmt = (
            select(CheckpointModel)
            .where(CheckpointModel.session_id == session_id)
            .order_by(CheckpointModel.created_at)
        )
        models = self._session.scalars(stmt).all()
        return [CheckpointMapper.to_domain(m) for m in models]


class SqlDecisionRepository:
    """SQLAlchemy implementation of DecisionRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, decision: Decision, idempotency_key: str | None = None) -> None:
        """Add a new decision."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != decision.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = decision.id

        model = DecisionMapper.to_model(decision)
        self._session.add(model)

    def get(self, decision_id: UUID) -> Decision | None:
        """Retrieve decision by ID."""
        stmt = select(DecisionModel).where(DecisionModel.id == decision_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return DecisionMapper.to_domain(model)

    def list_active(self) -> list[Decision]:
        """List all active decisions."""
        from execution_core.domain.enums import DecisionLifecycle

        stmt = (
            select(DecisionModel)
            .where(DecisionModel.lifecycle == DecisionLifecycle.ACTIVE)
            .order_by(DecisionModel.created_at)
        )
        models = self._session.scalars(stmt).all()
        return [DecisionMapper.to_domain(m) for m in models]


class SqlParkingItemRepository:
    """SQLAlchemy implementation of ParkingItemRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._idempotency_keys: dict[str, UUID] = {}

    def add(self, item: ParkingItem, idempotency_key: str | None = None) -> None:
        """Add a new parking item."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                if self._idempotency_keys[idempotency_key] != item.id:
                    raise IdempotencyKeyViolation(
                        f"Idempotency key {idempotency_key} already used"
                    )
                return
            self._idempotency_keys[idempotency_key] = item.id

        model = ParkingItemMapper.to_model(item)
        self._session.add(model)

    def get(self, item_id: UUID) -> ParkingItem | None:
        """Retrieve parking item by ID."""
        stmt = select(ParkingItemModel).where(ParkingItemModel.id == item_id)
        model = self._session.scalar(stmt)
        if not model:
            return None
        return ParkingItemMapper.to_domain(model)

    def list_active(self) -> list[ParkingItem]:
        """List all active (non-dismissed) parking items."""
        from execution_core.domain.enums import ParkingItemStatus

        stmt = (
            select(ParkingItemModel)
            .where(ParkingItemModel.status == ParkingItemStatus.PARKED)
            .order_by(ParkingItemModel.created_at)
        )
        models = self._session.scalars(stmt).all()
        return [ParkingItemMapper.to_domain(m) for m in models]
