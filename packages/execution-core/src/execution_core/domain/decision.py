"""Decision domain model for rationale preservation."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import DecisionLifecycle


class Alternative(BaseModel):
    """Rejected alternative with rejection reason."""

    text: str
    rejection_reason: str


class Decision(BaseModel):
    """Durable record of a selected option."""

    id: UUID = Field(default_factory=uuid4)
    question: str
    selected_option: str
    rationale: str
    alternatives: list[Alternative] = Field(default_factory=list)
    evidence_refs: list[UUID] = Field(default_factory=list)
    material: bool = True
    lifecycle: DecisionLifecycle = DecisionLifecycle.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    superseded_at: datetime | None = None
    superseded_by: UUID | None = None
    reopened_at: datetime | None = None
    reopening_reason: str | None = None

    def supersede(self, new_decision_id: UUID) -> None:
        """Mark this decision as superseded by a new one."""
        self.lifecycle = DecisionLifecycle.SUPERSEDED
        self.superseded_at = datetime.now(UTC)
        self.superseded_by = new_decision_id

    def reopen(self, reason: str) -> None:
        """Reopen a decision for reconsideration."""
        self.lifecycle = DecisionLifecycle.REOPENED
        self.reopened_at = datetime.now(UTC)
        self.reopening_reason = reason
