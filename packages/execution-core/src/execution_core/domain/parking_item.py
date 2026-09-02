"""Parking lot for secondary actions and discoveries."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import ParkingItemStatus, RelevanceLevel


class ParkingItem(BaseModel):
    """A structured capture of a non-current idea or discovery."""

    id: UUID = Field(default_factory=uuid4)
    text: str
    source_task_id: UUID | None = None
    source_context: str | None = None
    relevance: RelevanceLevel
    blocking: bool = False
    suggested_disposition: str
    status: ParkingItemStatus = ParkingItemStatus.PARKED
    revisit_trigger: str | None = None
    auto_parked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    promoted_at: datetime | None = None
    promoted_to_task_id: UUID | None = None
    dismissed_at: datetime | None = None
    dismissal_reason: str | None = None

    def promote_to_task(self, task_id: UUID) -> None:
        """Mark item as promoted to a planned task."""
        self.status = ParkingItemStatus.PROMOTED
        self.promoted_at = datetime.utcnow()
        self.promoted_to_task_id = task_id

    def dismiss(self, reason: str) -> None:
        """Mark item as dismissed with a reason."""
        self.status = ParkingItemStatus.DISMISSED
        self.dismissed_at = datetime.utcnow()
        self.dismissal_reason = reason

    @staticmethod
    def should_auto_park(relevance: RelevanceLevel, blocking: bool) -> bool:
        """Deterministic rule: auto-park if low relevance and non-blocking."""
        return relevance == RelevanceLevel.LOW and not blocking
