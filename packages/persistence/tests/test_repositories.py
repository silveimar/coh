"""Test repository implementations with optimistic concurrency."""

from uuid import uuid4

import pytest
from persistence.infrastructure.repositories import OptimisticLockError
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.decision import Alternative, Decision
from execution_core.domain.enums import (
    ArchiveStatus,
    Clarity,
    DecisionLifecycle,
    EvidenceAuthority,
    EvidenceResult,
    LifecycleState,
    ParkingItemStatus,
    Readiness,
    RelevanceLevel,
    SessionIntent,
    TaskStatus,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.domain.task import Task


def test_session_crud(session_factory) -> None:
    """Test basic ExecutionSession CRUD operations."""
    session = ExecutionSession(
        id=uuid4(),
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.INSPECT,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.sessions.add(session)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        loaded = uow.sessions.get(session.id)
        assert loaded is not None
        assert loaded.project_id == "test-project"
        assert loaded.intent == SessionIntent.EXECUTE


def test_session_optimistic_locking(session_factory) -> None:
    """Test optimistic concurrency control on session updates."""
    session = ExecutionSession(
        id=uuid4(),
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.sessions.add(session)
        uow.commit()

    # Update with correct version
    session.lifecycle_state = LifecycleState.SPECIFY
    session.increment_version()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.sessions.update(session, expected_version=1)
        uow.commit()

    # Attempt update with stale version should fail
    session.lifecycle_state = LifecycleState.EXECUTE
    session.increment_version()

    with pytest.raises(OptimisticLockError):
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            uow.sessions.update(session, expected_version=1)
            uow.commit()


def test_specification_with_nested_models(session_factory) -> None:
    """Test Specification with nested Pydantic models."""
    spec = Specification(
        id=uuid4(),
        what="Test spec",
        why="To verify nested model persistence",
        deliverable="Working test",
        done_when=[
            DoneWhenCriterion(text="Criterion 1"),
            DoneWhenCriterion(text="Criterion 2"),
        ],
        constraints=["Constraint A", "Constraint B"],
        non_goals=["Not this"],
        clarity=Clarity.MEDIUM,
        readiness=Readiness.BLOCKED,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.specifications.add(spec)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        loaded = uow.specifications.get(spec.id)
        assert loaded is not None
        assert len(loaded.done_when) == 2
        assert loaded.done_when[0].text == "Criterion 1"
        assert len(loaded.constraints) == 2
        assert loaded.constraints[0] == "Constraint A"


def test_task_repository(session_factory) -> None:
    """Test Task CRUD operations."""
    # Create spec first
    spec = Specification(
        id=uuid4(),
        what="Test",
        why="Testing",
        deliverable="Tests",
        clarity=Clarity.LOW,
        readiness=Readiness.BLOCKED,
    )

    task = Task(
        id=uuid4(),
        spec_id=spec.id,
        spec_revision=1,
        action_literal="Write tests",
        status=TaskStatus.PLANNED,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.specifications.add(spec)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.tasks.add(task)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        loaded = uow.tasks.get(task.id)
        assert loaded is not None
        assert loaded.action_literal == "Write tests"

        tasks = uow.tasks.list_by_spec(spec.id)
        assert len(tasks) == 1


def test_evidence_for_criterion(session_factory) -> None:
    """Test Evidence repository with criterion lookup."""
    spec = Specification(
        id=uuid4(),
        what="Test",
        why="Testing",
        deliverable="Tests",
        done_when=[DoneWhenCriterion(text="All tests pass")],
        clarity=Clarity.LOW,
        readiness=Readiness.BLOCKED,
    )

    criterion_id = spec.done_when[0].id

    evidence = Evidence(
        id=uuid4(),
        spec_id=spec.id,
        spec_revision=1,
        criterion_id=criterion_id,
        evidence_type="test_run",
        authority=EvidenceAuthority.TOOL_VERIFIED,
        result=EvidenceResult.PASS,
        summary="All tests passed",
        source="pytest",
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.specifications.add(spec)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.evidence.add(evidence)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        evidence_list = uow.evidence.list_by_criterion(spec.id, criterion_id)
        assert len(evidence_list) == 1
        assert evidence_list[0].summary == "All tests passed"


def test_checkpoint_latest_for_session(session_factory) -> None:
    """Test getting latest checkpoint for a session."""
    session = ExecutionSession(
        id=uuid4(),
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
    )

    spec = Specification(
        id=uuid4(),
        what="Test",
        why="Testing",
        deliverable="Tests",
        clarity=Clarity.LOW,
        readiness=Readiness.BLOCKED,
    )

    checkpoint1 = Checkpoint(
        id=uuid4(),
        session_id=session.id,
        lifecycle_state=LifecycleState.INSPECT,
        restart_action="First checkpoint",
        archive_status=ArchiveStatus.HEALTHY,
    )

    checkpoint2 = Checkpoint(
        id=uuid4(),
        session_id=session.id,
        lifecycle_state=LifecycleState.SPECIFY,
        restart_action="Second checkpoint",
        archive_status=ArchiveStatus.HEALTHY,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.sessions.add(session)
        uow.specifications.add(spec)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.checkpoints.add(checkpoint1)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.checkpoints.add(checkpoint2)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        latest = uow.checkpoints.get_latest_for_session(session.id)
        assert latest is not None
        assert latest.restart_action == "Second checkpoint"


def test_decision_lifecycle(session_factory) -> None:
    """Test Decision repository with alternatives."""
    decision = Decision(
        id=uuid4(),
        question="Which approach?",
        selected_option="Approach A",
        rationale="It's simpler",
        alternatives=[
            Alternative(text="Approach B", rejection_reason="Too complex"),
        ],
        material=True,
        lifecycle=DecisionLifecycle.ACTIVE,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.decisions.add(decision)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        loaded = uow.decisions.get(decision.id)
        assert loaded is not None
        assert loaded.selected_option == "Approach A"
        assert len(loaded.alternatives) == 1
        assert loaded.alternatives[0].text == "Approach B"


def test_parking_item_active_list(session_factory) -> None:
    """Test ParkingItem repository active items filter."""
    item1 = ParkingItem(
        id=uuid4(),
        text="Something to remember",
        relevance=RelevanceLevel.MEDIUM,
        blocking=False,
        suggested_disposition="Review later",
        status=ParkingItemStatus.PARKED,
    )

    item2 = ParkingItem(
        id=uuid4(),
        text="Already handled",
        relevance=RelevanceLevel.HIGH,
        blocking=False,
        suggested_disposition="Done",
        status=ParkingItemStatus.DISMISSED,
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.parking_items.add(item1)
        uow.parking_items.add(item2)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        active = uow.parking_items.list_active()
        assert len(active) == 1
        assert active[0].text == "Something to remember"
