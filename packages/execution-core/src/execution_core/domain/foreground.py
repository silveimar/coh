"""Foreground domain model for NOW + NEXT 2 execution surface."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .task import Task


class Foreground(BaseModel):
    """The visible executable surface: exactly one NOW and at most two NEXT."""

    session_id: UUID
    goal: str
    now_task: Task | None = None
    next_1_task: Task | None = None
    next_2_task: Task | None = None
    parked_count: int = 0
    background_count: int = 0
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    revision: int = 1

    def validate_invariant_i01(self) -> tuple[bool, list[str]]:
        """Validate I-01: at most one NOW and two NEXT with required metadata."""
        violations = []

        if self.now_task:
            if not all(
                [
                    self.now_task.action_literal,
                    self.now_task.done_when_condition,
                    self.now_task.estimated_minutes is not None,
                    self.now_task.energy is not None,
                    self.now_task.activation_friction is not None,
                ]
            ):
                violations.append(
                    "NOW task missing required metadata "
                    "(action_literal, done_when_condition, estimated_minutes, energy, activation_friction)"
                )

        next_count = sum([self.next_1_task is not None, self.next_2_task is not None])
        if next_count > 2:
            violations.append(f"Too many NEXT tasks: {next_count} (max 2)")

        return len(violations) == 0, violations

    def create_revision(self) -> "Foreground":
        """Create a new foreground revision."""
        new_fg = self.model_copy(deep=True)
        new_fg.revision = self.revision + 1
        new_fg.calculated_at = datetime.utcnow()
        return new_fg
