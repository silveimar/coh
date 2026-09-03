"""Foreground policy enforcing I-01 (NOW + NEXT 2 with required metadata)."""

from uuid import UUID

from ..domain.enums import TaskStatus
from ..domain.foreground import Foreground
from ..domain.task import Task


class ForegroundViolation(Exception):
    """Raised when foreground invariant I-01 is violated."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


class ForegroundPolicy:
    """Enforces I-01: at most one NOW and two NEXT with required metadata."""

    @staticmethod
    def calculate_foreground(
        session_id: UUID,
        goal: str,
        tasks: list[Task],
        parked_count: int,
    ) -> Foreground:
        """Calculate foreground from task list using deterministic ranking."""
        eligible = [t for t in tasks if ForegroundPolicy._is_eligible(t, tasks)]

        if not eligible:
            return Foreground(
                session_id=session_id,
                goal=goal,
                parked_count=parked_count,
                background_count=len(tasks),
            )

        ranked = ForegroundPolicy._rank_tasks(eligible)

        now_task = ranked[0] if len(ranked) > 0 else None
        next_1 = ranked[1] if len(ranked) > 1 else None
        next_2 = ranked[2] if len(ranked) > 2 else None

        foreground = Foreground(
            session_id=session_id,
            goal=goal,
            now_task=now_task,
            next_1_task=next_1,
            next_2_task=next_2,
            parked_count=parked_count,
            background_count=len(tasks) - min(3, len(ranked)),
        )

        ForegroundPolicy.enforce_invariant_i01(foreground)
        return foreground

    @staticmethod
    def _is_eligible(task: Task, all_tasks: list[Task]) -> bool:
        """Check if task is eligible for foreground."""
        if not task.is_foreground_eligible():
            return False

        completed_ids = {t.id for t in all_tasks if t.status == TaskStatus.COMPLETED}
        has_unresolved, _ = task.has_unresolved_dependencies(completed_ids)

        return not has_unresolved

    @staticmethod
    def _rank_tasks(tasks: list[Task]) -> list[Task]:
        """Rank eligible tasks using weighted scoring with stable tie-breaker."""

        def score(task: Task) -> tuple[float, str]:
            weights = {
                "goal_leverage": 0.3,
                "energy": -0.1,
                "friction": -0.15,
            }

            s = weights["goal_leverage"] * task.goal_leverage

            energy_scores = {"low": 0.1, "medium": 0.0, "high": -0.1}
            if task.energy:
                s += weights["energy"] * energy_scores.get(task.energy.value, 0)

            friction_scores = {"low": 0.1, "medium": 0.0, "high": -0.1}
            if task.activation_friction:
                s += weights["friction"] * friction_scores.get(
                    task.activation_friction.value, 0
                )

            return (-s, str(task.id))

        return sorted(tasks, key=score)

    @staticmethod
    def enforce_invariant_i01(foreground: Foreground) -> None:
        """Enforce I-01: verify foreground structure and metadata."""
        valid, violations = foreground.validate_invariant_i01()
        if not valid:
            raise ForegroundViolation(
                f"Foreground violates I-01: {'; '.join(violations)}", violations
            )

    @staticmethod
    def promote_after_completion(
        session_id: UUID, goal: str, remaining_tasks: list[Task], parked_count: int
    ) -> Foreground:
        """Recalculate foreground after NOW task completion."""
        return ForegroundPolicy.calculate_foreground(
            session_id, goal, remaining_tasks, parked_count
        )

    @staticmethod
    def validate_now_task_no_unresolved_dependencies(
        now_task: Task, all_tasks: list[Task]
    ) -> tuple[bool, str | None]:
        """Part of I-01: NOW must not have unresolved dependencies."""
        completed_ids = {t.id for t in all_tasks if t.status == TaskStatus.COMPLETED}
        has_unresolved, unresolved_ids = now_task.has_unresolved_dependencies(
            completed_ids
        )

        if has_unresolved:
            return (
                False,
                f"NOW task has unresolved dependencies: {unresolved_ids}",
            )

        return True, None
