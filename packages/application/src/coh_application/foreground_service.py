"""Foreground execution service enforcing I-01 (NOW + NEXT 2 with metadata)."""

from uuid import UUID

from execution_core.domain.enums import ForegroundPosition, TaskStatus
from execution_core.domain.foreground import Foreground
from execution_core.domain.task import Task, TaskProgressRecord
from execution_core.policies.foreground_policy import ForegroundPolicy
from persistence.ports.state_store import UnitOfWork


class ForegroundService:
    """Foreground service implementing I-01: exactly 1 NOW + ≤2 NEXT."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def calculate_foreground(
        self, session_id: UUID, goal: str | None = None
    ) -> Foreground:
        """
        Calculate foreground from task list.

        Enforces I-01:
        - At most one NOW task
        - At most two NEXT tasks
        - NOW has action_literal, done_when_condition, minutes, energy, friction
        - Task with unresolved dependencies is never NOW
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        spec = self._load_current_spec(session)
        if not spec:
            raise ValueError(f"Session {session_id} has no specification")

        tasks = self.uow.tasks.list_by_spec(spec.id)

        parked_items = self.uow.parking_items.list_active()
        parked_count = len(parked_items)

        goal_text = goal or spec.what

        foreground = ForegroundPolicy.calculate_foreground(
            session_id=session_id,
            goal=goal_text,
            tasks=tasks,
            parked_count=parked_count,
        )

        return foreground

    def complete_now_task(
        self, session_id: UUID, task_id: UUID, completion_notes: str | None = None
    ) -> Foreground:
        """
        Complete NOW task and recalculate foreground (I-05, I-01).

        Creates progress record before foreground change (I-05).
        Returns new foreground with promoted tasks.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = self.uow.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.foreground_position != ForegroundPosition.NOW:
            raise ValueError(f"Task {task_id} is not the NOW task")

        # I-05: Create progress record before state change (persistence deferred)
        _progress_record = TaskProgressRecord(
            task_id=task_id,
            status=task.status,
            completed_work=[completion_notes or "Task completed"],
        )

        task.mark_completed()
        task.foreground_position = ForegroundPosition.BACKGROUND

        self.uow.tasks.update(task)

        spec = self._load_current_spec(session)
        if not spec:
            raise ValueError(f"Session {session_id} has no specification")

        remaining_tasks = [
            t for t in self.uow.tasks.list_by_spec(spec.id) if t.id != task_id
        ]

        parked_count = len(self.uow.parking_items.list_active())

        new_foreground = ForegroundPolicy.promote_after_completion(
            session_id=session_id,
            goal=spec.what,
            remaining_tasks=remaining_tasks,
            parked_count=parked_count,
        )

        self.uow.commit()

        return new_foreground

    def block_now_task(
        self, session_id: UUID, task_id: UUID, reason: str
    ) -> Foreground:
        """
        Block NOW task and recalculate foreground (I-05, I-01).

        Creates progress record with blocker before foreground change (I-05).
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = self.uow.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.foreground_position != ForegroundPosition.NOW:
            raise ValueError(f"Task {task_id} is not the NOW task")

        # I-05: Create progress record before state change (persistence deferred)
        _progress_record = TaskProgressRecord(
            task_id=task_id,
            status=task.status,
            blockers=[reason],
        )

        task.mark_blocked(reason)
        task.foreground_position = ForegroundPosition.BACKGROUND

        self.uow.tasks.update(task)

        spec = self._load_current_spec(session)
        if not spec:
            raise ValueError(f"Session {session_id} has no specification")

        remaining_tasks = [
            t
            for t in self.uow.tasks.list_by_spec(spec.id)
            if t.status not in [TaskStatus.BLOCKED, TaskStatus.COMPLETED]
        ]

        parked_count = len(self.uow.parking_items.list_active())

        new_foreground = ForegroundPolicy.calculate_foreground(
            session_id=session_id,
            goal=spec.what,
            tasks=remaining_tasks,
            parked_count=parked_count,
        )

        self.uow.commit()

        return new_foreground

    def park_task(self, session_id: UUID, task_id: UUID, reason: str) -> Foreground:
        """
        Park task without changing NOW (I-10).

        Creates progress record before status change.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = self.uow.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # I-05: Create progress record before state change (persistence deferred)
        _progress_record = TaskProgressRecord(
            task_id=task_id,
            status=task.status,
            attempted_work=[f"Parked: {reason}"],
        )

        task.park()

        self.uow.tasks.update(task)

        spec = self._load_current_spec(session)
        if not spec:
            raise ValueError(f"Session {session_id} has no specification")

        remaining_tasks = [
            t
            for t in self.uow.tasks.list_by_spec(spec.id)
            if t.status not in [TaskStatus.PARKED, TaskStatus.COMPLETED]
        ]

        parked_count = len(self.uow.parking_items.list_active()) + 1

        new_foreground = ForegroundPolicy.calculate_foreground(
            session_id=session_id,
            goal=spec.what,
            tasks=remaining_tasks,
            parked_count=parked_count,
        )

        self.uow.commit()

        return new_foreground

    def interrupt_now_task(
        self,
        session_id: UUID,
        task_id: UUID,
        completed_work: list[str],
        next_steps: list[str],
    ) -> Foreground:
        """
        Interrupt NOW task and record progress (I-05).

        Creates/updates progress record before foreground change.
        Returns recalculated foreground.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = self.uow.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.foreground_position != ForegroundPosition.NOW:
            raise ValueError(f"Task {task_id} is not the NOW task")

        # I-05: Create progress record before state change (persistence deferred)
        _progress_record = TaskProgressRecord(
            task_id=task_id,
            status=task.status,
            completed_work=completed_work,
            next_steps=next_steps,
        )

        task.foreground_position = ForegroundPosition.BACKGROUND

        self.uow.tasks.update(task)

        spec = self._load_current_spec(session)
        if not spec:
            raise ValueError(f"Session {session_id} has no specification")

        remaining_tasks = [
            t
            for t in self.uow.tasks.list_by_spec(spec.id)
            if t.status
            not in [TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.PARKED]
        ]

        parked_count = len(self.uow.parking_items.list_active())

        new_foreground = ForegroundPolicy.calculate_foreground(
            session_id=session_id,
            goal=spec.what,
            tasks=remaining_tasks,
            parked_count=parked_count,
        )

        self.uow.commit()

        return new_foreground

    def validate_now_task_ready(self, task: Task) -> tuple[bool, list[str]]:
        """
        Validate NOW task has required metadata (I-01).

        Returns: (valid, violations)
        """
        violations = []

        if not task.action_literal:
            violations.append("Missing action_literal")
        if not task.done_when_condition:
            violations.append("Missing done_when_condition")
        if task.estimated_minutes is None:
            violations.append("Missing estimated_minutes")
        if task.energy is None:
            violations.append("Missing energy")
        if task.activation_friction is None:
            violations.append("Missing activation_friction")

        return len(violations) == 0, violations

    def _load_current_spec(self, session):
        """Load the current spec for a session by its stored spec ID."""
        if not session.current_spec:
            from sqlalchemy import select

            from persistence.infrastructure.models import ExecutionSessionModel

            if hasattr(self.uow, "_session") and self.uow._session:
                stmt = select(ExecutionSessionModel).where(
                    ExecutionSessionModel.id == session.id
                )
                model = self.uow._session.scalar(stmt)
                if model and model.current_spec_id:
                    return self.uow.specifications.get(model.current_spec_id)
        return session.current_spec

    def get_foreground_status(self, session_id: UUID) -> dict[str, str | int | None]:
        """
        Get current foreground status for read-only inspection.

        Returns: goal, now_task_id, next_1_id, next_2_id, parked_count, background_count
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        spec = self._load_current_spec(session)
        if not spec:
            return {"error": "No specification exists"}

        tasks = self.uow.tasks.list_by_spec(spec.id)
        parked_count = len(self.uow.parking_items.list_active())

        foreground = ForegroundPolicy.calculate_foreground(
            session_id=session_id,
            goal=spec.what,
            tasks=tasks,
            parked_count=parked_count,
        )

        return {
            "goal": foreground.goal,
            "now_task_id": str(foreground.now_task.id) if foreground.now_task else None,
            "next_1_id": str(foreground.next_1_task.id)
            if foreground.next_1_task
            else None,
            "next_2_id": str(foreground.next_2_task.id)
            if foreground.next_2_task
            else None,
            "parked_count": foreground.parked_count,
            "background_count": foreground.background_count,
        }
