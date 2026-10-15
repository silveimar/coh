"""Tests for task domain model and foreground eligibility."""

from uuid import uuid4

from execution_core.domain.enums import (
    ActivationFriction,
    EnergyLevel,
    ForegroundPosition,
    TaskStatus,
)
from execution_core.domain.task import Task, TaskDependency, TaskProgressRecord


class TestTask:
    """Test task model and foreground eligibility."""

    def test_task_foreground_eligible_with_all_metadata(self):
        """Task with all required metadata should be foreground eligible."""
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            action_literal="Run the tests",
            done_when_condition="All tests pass",
            estimated_minutes=15,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            status=TaskStatus.PLANNED,
        )

        assert task.is_foreground_eligible()

    def test_task_not_eligible_without_action_literal(self):
        """Task without action literal should not be eligible."""
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            action_literal=None,
            done_when_condition="Done",
            estimated_minutes=15,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            status=TaskStatus.PLANNED,
        )

        assert not task.is_foreground_eligible()

    def test_completed_task_not_eligible(self):
        """Completed task should not be eligible."""
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            action_literal="Action",
            done_when_condition="Done",
            estimated_minutes=15,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            status=TaskStatus.COMPLETED,
        )

        assert not task.is_foreground_eligible()

    def test_task_with_unresolved_dependencies(self):
        """Task should detect unresolved dependencies."""
        dep_id = uuid4()
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            action_literal="Action",
            done_when_condition="Done",
            estimated_minutes=15,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            dependencies=[TaskDependency(task_id=dep_id)],
        )

        has_unresolved, unresolved_ids = task.has_unresolved_dependencies(set())

        assert has_unresolved
        assert dep_id in unresolved_ids

    def test_task_with_resolved_dependencies(self):
        """Task with completed dependencies should have no unresolved deps."""
        dep_id = uuid4()
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            dependencies=[TaskDependency(task_id=dep_id)],
        )

        has_unresolved, unresolved_ids = task.has_unresolved_dependencies({dep_id})

        assert not has_unresolved
        assert len(unresolved_ids) == 0

    def test_mark_started_updates_status_and_timestamp(self):
        """Marking task started should update status and timestamp."""
        task = Task(spec_id=uuid4(), spec_revision=1, status=TaskStatus.PLANNED)

        task.mark_started()

        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

    def test_mark_completed_updates_status_and_timestamp(self):
        """Marking task completed should update status and timestamp."""
        task = Task(spec_id=uuid4(), spec_revision=1, status=TaskStatus.IN_PROGRESS)

        task.mark_completed()

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_mark_blocked_with_reason(self):
        """Marking task blocked should store reason."""
        task = Task(spec_id=uuid4(), spec_revision=1, status=TaskStatus.IN_PROGRESS)

        task.mark_blocked("Waiting for API response")

        assert task.status == TaskStatus.BLOCKED
        assert task.blocked_reason == "Waiting for API response"

    def test_park_task_removes_from_foreground(self):
        """Parking task should move to background."""
        task = Task(
            spec_id=uuid4(),
            spec_revision=1,
            status=TaskStatus.IN_PROGRESS,
            foreground_position=ForegroundPosition.NOW,
        )

        task.park()

        assert task.status == TaskStatus.PARKED
        assert task.foreground_position == ForegroundPosition.BACKGROUND


class TestTaskProgressRecord:
    """Test task progress record for interruption safety."""

    def test_create_progress_record(self):
        """Creating progress record should capture task state."""
        task_id = uuid4()
        record = TaskProgressRecord(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            completed_work=["Wrote tests"],
            blockers=["Need API key"],
        )

        assert record.task_id == task_id
        assert record.status == TaskStatus.IN_PROGRESS
        assert "Wrote tests" in record.completed_work
        assert "Need API key" in record.blockers

    def test_create_revision_increments_revision_number(self):
        """Creating revision should increment revision number."""
        record = TaskProgressRecord(
            task_id=uuid4(), status=TaskStatus.IN_PROGRESS, revision=1
        )

        new_record = record.create_revision()

        assert new_record.revision == 2
        assert new_record.task_id == record.task_id
