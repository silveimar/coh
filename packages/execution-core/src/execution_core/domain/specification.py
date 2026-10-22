"""Specification domain model (WHAT/WHY/DELIVERABLE/DONE WHEN)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .clock import utc_now_naive
from .enums import AssumptionClass, Clarity, Readiness


class Assumption(BaseModel):
    """A statement treated as true while work proceeds."""

    id: UUID = Field(default_factory=uuid4)
    text: str
    classification: AssumptionClass
    rationale: str | None = None
    requires_confirmation: bool = False
    resolved: bool = False
    resolution_notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now_naive)


class Unknown(BaseModel):
    """An identified missing fact."""

    id: UUID = Field(default_factory=uuid4)
    text: str
    blocking: bool
    discoverable_via_inspection: bool = True
    resolved: bool = False
    resolution_value: str | None = None
    created_at: datetime = Field(default_factory=utc_now_naive)


class DoneWhenCriterion(BaseModel):
    """A measurable condition establishing completion."""

    id: UUID = Field(default_factory=uuid4)
    text: str
    measurable: bool = True
    created_at: datetime = Field(default_factory=utc_now_naive)


class Specification(BaseModel):
    """Structured definition of WHAT, WHY, DELIVERABLE, done-when criteria."""

    id: UUID = Field(default_factory=uuid4)
    revision: int = 1
    what: str
    why: str
    deliverable: str
    done_when: list[DoneWhenCriterion] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    clarity: Clarity = Clarity.LOW
    readiness: Readiness = Readiness.BLOCKED
    created_at: datetime = Field(default_factory=utc_now_naive)
    updated_at: datetime = Field(default_factory=utc_now_naive)
    confirmed_at: datetime | None = None

    def compute_clarity(self) -> Clarity:
        """Compute clarity level from spec completeness."""
        score = 0
        total = 6

        if self.what:
            score += 1
        if self.why:
            score += 1
        if self.deliverable:
            score += 1
        if self.done_when:
            score += 1
        if self.constraints or self.non_goals:
            score += 1
        if not any(u.blocking and not u.resolved for u in self.unknowns):
            score += 1

        ratio = score / total
        if ratio >= 0.9:
            return Clarity.READY
        elif ratio >= 0.7:
            return Clarity.HIGH
        elif ratio >= 0.4:
            return Clarity.MEDIUM
        else:
            return Clarity.LOW

    def compute_readiness(self) -> Readiness:
        """Compute binary execution gate status."""
        if not all([self.what, self.why, self.deliverable, self.done_when]):
            return Readiness.BLOCKED

        if any(u.blocking and not u.resolved for u in self.unknowns):
            return Readiness.BLOCKED

        if any(
            a.classification == AssumptionClass.BLOCKING and not a.resolved
            for a in self.assumptions
        ):
            return Readiness.BLOCKED

        unconfirmed_material = [
            a
            for a in self.assumptions
            if a.classification == AssumptionClass.MATERIAL
            and a.requires_confirmation
            and not a.resolved
        ]
        if unconfirmed_material:
            return Readiness.BLOCKED

        return Readiness.READY

    def update_computed_fields(self) -> None:
        """Recompute clarity and readiness after spec changes."""
        self.clarity = self.compute_clarity()
        self.readiness = self.compute_readiness()
        self.updated_at = datetime.now(UTC)

    def create_revision(self) -> Specification:
        """Create a new revision with incremented revision number."""
        new_spec = self.model_copy(deep=True)
        new_spec.id = uuid4()
        new_spec.revision = self.revision + 1
        new_spec.created_at = datetime.now(UTC)
        new_spec.updated_at = datetime.now(UTC)
        new_spec.confirmed_at = None
        new_spec.update_computed_fields()
        return new_spec
