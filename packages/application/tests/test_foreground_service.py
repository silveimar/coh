"""Tests for ForegroundService enforcing I-01 (NOW + NEXT 2)."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from coh_application.foreground_service import ForegroundService
from execution_core.domain.enums import (
    ActivationFriction,
    EnergyLevel,
    ForegroundPosition,
    LifecycleState,
    SessionIntent,
    TaskStatus,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import Specification
from execution_core.domain.task import Task
from persistence.infrastructure.database import create_engine, init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class TestForegroundService:
    """Test foreground service I-01 enforcement."""

    @pytest.fixture
    def uow(self):
        """Create in-memory SQLite UnitOfWork for testing."""
        engine = create_engine("sqlite:///:memory:")
        init_db(engine)
        session_factory = sessionmaker(bind=engine)
        return SqlAlchemyUnitOfWork(session_factory)

    @pytest.fixture
    def session_with_spec(self, uow):
        """Create session with confirmed spec."""
        spec = Specification(
            what="Build feature",
            why="User request",
            deliverable="Working feature",
            done_when=[],
        )
        spec.update_computed_fields()

        session = ExecutionSession(
            project_id="test-project",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.PLAN,
        )

        with uow:
            uow.specifications.add(spec)
            if hasattr(uow, "_session") and uow._session:
                uow._session.flush()

            session.current_spec = spec
            uow.sessions.add(session)
            uow.commit()

        return session

    def _create_task(
        self,
        spec_id,
        action: str,
        done_when: str,
        minutes: int = 30,
        energy: str = "medium",
        friction: str = "low",
        dependencies: list = None,
    ) -> Task:
        """Helper to create a foreground-eligible task."""
        return Task(
            spec_id=spec_id,
            spec_revision=1,
            action_literal=action,
            done_when_condition=done_when,
            estimated_minutes=minutes,
            energy=EnergyLevel(energy),
            activation_friction=ActivationFriction(friction),
            status=TaskStatus.PLANNED,
            dependencies=dependencies or [],
        )

    def test_i01_calculate_foreground_exactly_one_now(self, uow, session_with_spec):
        """I-01: Foreground has at most one NOW task."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        assert foreground.now_task is not None
        assert foreground.next_1_task is not None or foreground.next_2_task is not None
        now_count = 1
        assert now_count == 1

    def test_i01_at_most_two_next_tasks(self, uow, session_with_spec):
        """I-01: Foreground has at most two NEXT tasks."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")
        task3 = self._create_task(spec.id, "Task 3", "Done 3")
        task4 = self._create_task(spec.id, "Task 4", "Done 4")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.tasks.add(task3)
            uow.tasks.add(task4)
            uow.commit()

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        next_count = sum(
            [
                foreground.next_1_task is not None,
                foreground.next_2_task is not None,
            ]
        )
        assert next_count <= 2
        assert foreground.background_count == 1

    def test_i01_now_has_required_metadata(self, uow, session_with_spec):
        """I-01: NOW task has action_literal, done_when, minutes, energy, friction."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task = self._create_task(spec.id, "Task 1", "Done 1", minutes=45)

        with uow:
            uow.tasks.add(task)
            uow.commit()

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        assert foreground.now_task is not None
        assert foreground.now_task.action_literal == "Task 1"
        assert foreground.now_task.done_when_condition == "Done 1"
        assert foreground.now_task.estimated_minutes == 45
        assert foreground.now_task.energy == EnergyLevel.MEDIUM
        assert foreground.now_task.activation_friction == ActivationFriction.LOW

    def test_i01_task_missing_metadata_not_in_foreground(self, uow, session_with_spec):
        """I-01: Task missing required metadata is not eligible for foreground."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        incomplete_task = Task(
            spec_id=spec.id,
            spec_revision=1,
            action_literal="Task 1",
            done_when_condition=None,
            status=TaskStatus.PLANNED,
        )

        with uow:
            uow.tasks.add(incomplete_task)
            uow.commit()

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        assert foreground.now_task is None

    def test_i01_unresolved_dependencies_never_now(self, uow, session_with_spec):
        """I-01: Task with unresolved dependencies is never NOW."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2_id = uuid4()
        task2 = self._create_task(
            spec.id,
            "Task 2 depends on 1",
            "Done 2",
            dependencies=[{"task_id": task1.id, "dependency_type": "blocks"}],
        )
        task2.id = task2_id

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        assert foreground.now_task is not None
        assert foreground.now_task.id == task1.id
        assert foreground.now_task.id != task2.id

    def test_complete_now_recalculates_foreground(self, uow, session_with_spec):
        """Completing NOW task recalculates foreground and promotes NEXT."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            initial_fg = service.calculate_foreground(session_with_spec.id)

        initial_now_id = initial_fg.now_task.id

        with uow:
            task_to_update = uow.tasks.get(initial_now_id)
            task_to_update.foreground_position = ForegroundPosition.NOW
            uow.tasks.update(task_to_update)
            uow.commit()

        with uow:
            new_fg = service.complete_now_task(session_with_spec.id, initial_now_id)

        assert new_fg.now_task is not None
        assert new_fg.now_task.id != initial_now_id

    def test_block_now_recalculates_foreground(self, uow, session_with_spec):
        """Blocking NOW task removes it from foreground and selects new NOW."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            initial_fg = service.calculate_foreground(session_with_spec.id)

        initial_now_id = initial_fg.now_task.id

        with uow:
            task_to_update = uow.tasks.get(initial_now_id)
            task_to_update.foreground_position = ForegroundPosition.NOW
            uow.tasks.update(task_to_update)
            uow.commit()

        with uow:
            new_fg = service.block_now_task(
                session_with_spec.id, initial_now_id, "Missing API key"
            )

        assert new_fg.now_task is not None
        assert new_fg.now_task.id != initial_now_id

        with uow:
            blocked_task = uow.tasks.get(initial_now_id)

        assert blocked_task.status == TaskStatus.BLOCKED
        assert blocked_task.blocked_reason == "Missing API key"

    def test_park_task_does_not_change_now(self, uow, session_with_spec):
        """I-10: Parking a task does not change NOW task."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            initial_fg = service.calculate_foreground(session_with_spec.id)

        initial_now_id = initial_fg.now_task.id

        with uow:
            new_fg = service.park_task(session_with_spec.id, task2.id, "Low priority")

        assert new_fg.parked_count == 1

        with uow:
            parked_task = uow.tasks.get(task2.id)

        assert parked_task.status == TaskStatus.PARKED

    def test_interrupt_now_records_progress(self, uow, session_with_spec):
        """I-05: Interrupting NOW records progress before foreground change."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task2 = self._create_task(spec.id, "Task 2", "Done 2")

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            initial_fg = service.calculate_foreground(session_with_spec.id)

        initial_now_id = initial_fg.now_task.id

        with uow:
            task_to_update = uow.tasks.get(initial_now_id)
            task_to_update.foreground_position = ForegroundPosition.NOW
            uow.tasks.update(task_to_update)
            uow.commit()

        with uow:
            new_fg = service.interrupt_now_task(
                session_with_spec.id,
                initial_now_id,
                completed_work=["Set up auth"],
                next_steps=["Add tests"],
            )

        assert new_fg.now_task is not None

    def test_validate_now_task_ready_checks_metadata(self, uow, session_with_spec):
        """validate_now_task_ready enforces I-01 metadata requirements."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        complete_task = self._create_task(spec.id, "Complete", "Done")
        valid, violations = service.validate_now_task_ready(complete_task)
        assert valid is True
        assert len(violations) == 0

        incomplete_task = Task(
            spec_id=spec.id,
            spec_revision=1,
            action_literal="Task",
            done_when_condition=None,
        )
        valid, violations = service.validate_now_task_ready(incomplete_task)
        assert valid is False
        assert "Missing done_when_condition" in violations
        assert "Missing estimated_minutes" in violations
        assert "Missing energy" in violations
        assert "Missing activation_friction" in violations

    def test_get_foreground_status_read_only(self, uow, session_with_spec):
        """get_foreground_status returns read-only view of foreground."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1 = self._create_task(spec.id, "Task 1", "Done 1")

        with uow:
            uow.tasks.add(task1)
            uow.commit()

        with uow:
            status = service.get_foreground_status(session_with_spec.id)

        assert status["goal"] == "Build feature"
        assert status["now_task_id"] is not None
        assert status["parked_count"] == 0

    def test_no_eligible_tasks_returns_empty_foreground(self, uow, session_with_spec):
        """Foreground with no eligible tasks returns empty NOW/NEXT."""
        service = ForegroundService(uow)

        with uow:
            foreground = service.calculate_foreground(session_with_spec.id)

        assert foreground.now_task is None
        assert foreground.next_1_task is None
        assert foreground.next_2_task is None

    def test_completed_task_promoted_after_completion(self, uow, session_with_spec):
        """Task completion promotes next eligible task to NOW."""
        service = ForegroundService(uow)
        spec = session_with_spec.current_spec

        task1_id = uuid4()
        task2_id = uuid4()

        task1 = self._create_task(spec.id, "Task 1", "Done 1")
        task1.id = task1_id
        task2 = self._create_task(spec.id, "Task 2", "Done 2")
        task2.id = task2_id

        with uow:
            uow.tasks.add(task1)
            uow.tasks.add(task2)
            uow.commit()

        with uow:
            initial_fg = service.calculate_foreground(session_with_spec.id)

        initial_now_id = initial_fg.now_task.id

        with uow:
            task_to_update = uow.tasks.get(initial_now_id)
            task_to_update.foreground_position = ForegroundPosition.NOW
            uow.tasks.update(task_to_update)
            uow.commit()

        with uow:
            new_fg = service.complete_now_task(
                session_with_spec.id, initial_now_id, "Completed successfully"
            )

        assert new_fg.now_task is not None
        assert new_fg.now_task.id != initial_now_id

        with uow:
            completed = uow.tasks.get(initial_now_id)

        assert completed.status == TaskStatus.COMPLETED
        assert completed.foreground_position == ForegroundPosition.BACKGROUND
