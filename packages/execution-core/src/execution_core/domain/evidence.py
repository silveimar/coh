"""Evidence domain model for verification and completion."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .clock import utc_now_naive
from .enums import EvidenceAuthority, EvidenceResult


class ArchiveReference(BaseModel):
    """Reference to a specific archive entry."""

    path: str
    timestamp: datetime
    anchor: str


class Evidence(BaseModel):
    """Test result, artifact, or acceptance mapped to a criterion."""

    id: UUID = Field(default_factory=uuid4)
    spec_id: UUID
    spec_revision: int
    criterion_id: UUID
    evidence_type: str
    authority: EvidenceAuthority
    result: EvidenceResult
    summary: str
    source: str
    archive_reference: ArchiveReference | None = None
    tool_reference: str | None = None
    recorded_at: datetime = Field(default_factory=utc_now_naive)
    user_acceptance_rationale: str | None = None
    stale: bool = False

    def can_satisfy_criterion(self) -> bool:
        """Check if evidence has sufficient authority to satisfy a criterion."""
        if self.stale:
            return False

        if self.authority not in [
            EvidenceAuthority.TOOL_VERIFIED,
            EvidenceAuthority.USER_ACCEPTED,
        ]:
            return False

        if self.result not in [EvidenceResult.PASS, EvidenceResult.ACCEPTED]:
            return False

        return True

    def mark_stale(self) -> None:
        """Mark evidence as stale due to spec/implementation changes."""
        self.stale = True

    def is_fresh_for_revision(self, current_revision: int) -> bool:
        """Check if evidence is still valid for the current spec revision."""
        return self.spec_revision == current_revision and not self.stale
