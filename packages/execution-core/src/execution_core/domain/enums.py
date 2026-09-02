"""Shared enums and value types across the domain."""

from enum import StrEnum


class EnergyLevel(StrEnum):
    """Cognitive/physical demand of a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActivationFriction(StrEnum):
    """Difficulty of starting an action, independent of duration or complexity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Readiness(StrEnum):
    """Binary execution gate."""

    READY = "ready"
    BLOCKED = "blocked"


class Clarity(StrEnum):
    """Qualitative spec completeness."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    READY = "ready"


class CompletionState(StrEnum):
    """Task/deliverable completion progression."""

    IMPLEMENTED = "implemented"
    TESTED = "tested"
    VERIFIED = "verified"
    DONE = "done"


class LifecycleState(StrEnum):
    """The 7-state execution lifecycle."""

    INSPECT = "INSPECT"
    SPECIFY = "SPECIFY"
    CONFIRM = "CONFIRM"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"


class SessionIntent(StrEnum):
    """Mode of work determining completion contract and drift definition."""

    EXECUTE = "execute"
    PLAN = "plan"
    BRAINSTORM = "brainstorm"
    REVIEW = "review"
    STUDY = "study"
    RECOVER = "recover"


class ArchiveStatus(StrEnum):
    """Checkpoint-level health of archival."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"


class AssumptionClass(StrEnum):
    """Classification of assumptions by risk level."""

    SAFE = "safe"
    MATERIAL = "material"
    BLOCKING = "blocking"


class EvidenceAuthority(StrEnum):
    """Source-derived authority level for evidence."""

    TOOL_VERIFIED = "tool_verified"
    AGENT_REPORTED = "agent_reported"
    USER_ACCEPTED = "user_accepted"


class EvidenceResult(StrEnum):
    """Evidence evaluation outcome."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    ACCEPTED = "accepted"


class TaskStatus(StrEnum):
    """Task lifecycle status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    PARKED = "parked"
    ABANDONED = "abandoned"


class ForegroundPosition(StrEnum):
    """Task position in the execution foreground."""

    NOW = "NOW"
    NEXT_1 = "NEXT_1"
    NEXT_2 = "NEXT_2"
    BACKGROUND = "BACKGROUND"


class ParkingItemStatus(StrEnum):
    """Parking item lifecycle status."""

    PARKED = "parked"
    PROMOTED = "promoted"
    DISMISSED = "dismissed"


class DecisionLifecycle(StrEnum):
    """Decision record lifecycle."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REOPENED = "reopened"


class RelevanceLevel(StrEnum):
    """Parking item relevance assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
