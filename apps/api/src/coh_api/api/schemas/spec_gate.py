"""Spec gate request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class AssumptionInput(BaseModel):
    """Assumption input for spec proposal."""

    text: str
    classification: str
    rationale: str | None = None
    requires_confirmation: bool = False


class UnknownInput(BaseModel):
    """Unknown input for spec proposal."""

    text: str
    blocking: bool = False
    discoverable_via_inspection: bool = True


class ProposeSpecRequest(BaseModel):
    """Request to propose a specification."""

    session_id: UUID
    what: str = Field(..., min_length=1)
    why: str = Field(..., min_length=1)
    deliverable: str = Field(..., min_length=1)
    done_when: list[str] = Field(..., min_length=1)
    constraints: list[str] | None = None
    non_goals: list[str] | None = None
    assumptions: list[AssumptionInput] | None = None
    unknowns: list[UnknownInput] | None = None


class SpecResponse(BaseModel):
    """Specification response."""

    spec_id: str
    revision: int
    what: str
    why: str
    deliverable: str
    done_when: list[str]
    constraints: list[str]
    non_goals: list[str]
    clarity: str  # low|medium|high|ready
    readiness: str  # ready|blocked
    blockers: list[str]


class ConfirmSpecRequest(BaseModel):
    """Request to confirm a specification."""

    session_id: UUID
    spec: ProposeSpecRequest
    idempotency_key: str
    expected_version: int | None = None


class ReviseSpecRequest(BaseModel):
    """Request to revise a specification."""

    session_id: UUID
    spec_id: UUID
    updates: dict[str, str | list[str]]
    idempotency_key: str
    expected_version: int | None = None


class MutationAllowedResponse(BaseModel):
    """Response for mutation-allowed check."""

    allowed: bool
    readiness_state: str  # ready|blocked
    blockers: list[str]


class SpecStatusResponse(BaseModel):
    """Response for spec status (read-only)."""

    spec_id: str | None = None
    revision: str | None = None
    clarity: str  # none|low|medium|high|ready
    readiness: str  # ready|blocked
    blockers: list[str]
    what: str | None = None
    why: str | None = None
    deliverable: str | None = None
    done_when_count: int = 0
