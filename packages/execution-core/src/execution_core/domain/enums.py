"""Shared enums and value types across the domain."""

from enum import Enum


class EnergyLevel(str, Enum):
    """Cognitive/physical demand of a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActivationFriction(str, Enum):
    """Difficulty of starting an action, independent of duration or complexity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Readiness(str, Enum):
    """Binary execution gate."""

    READY = "ready"
    BLOCKED = "blocked"


class Clarity(str, Enum):
    """Qualitative spec completeness."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    READY = "ready"


class CompletionState(str, Enum):
    """Task/deliverable completion progression."""

    IMPLEMENTED = "implemented"
    TESTED = "tested"
    VERIFIED = "verified"
    DONE = "done"


class LifecycleState(str, Enum):
    """The 7-state execution lifecycle."""

    INSPECT = "INSPECT"
    SPECIFY = "SPECIFY"
    CONFIRM = "CONFIRM"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"


class SessionIntent(str, Enum):
    """Mode of work determining completion contract and drift definition."""

    EXECUTE = "execute"
    PLAN = "plan"
    BRAINSTORM = "brainstorm"
    REVIEW = "review"
    STUDY = "study"
    RECOVER = "recover"


class ArchiveStatus(str, Enum):
    """Checkpoint-level health of archival."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"


class AssumptionClass(str, Enum):
    """Classification of assumptions by risk level."""

    SAFE = "safe"
    MATERIAL = "material"
    BLOCKING = "blocking"


class EvidenceAuthority(str, Enum):
    """Source-derived authority level for evidence."""

    TOOL_VERIFIED = "tool_verified"
    AGENT_REPORTED = "agent_reported"
    USER_ACCEPTED = "user_accepted"


class EvidenceResult(str, Enum):
    """Evidence evaluation outcome."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    ACCEPTED = "accepted"


class TaskStatus(str, Enum):
    """Task lifecycle status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    PARKED = "parked"
    ABANDONED = "abandoned"


class ForegroundPosition(str, Enum):
    """Task position in the execution foreground."""

    NOW = "NOW"
    NEXT_1 = "NEXT_1"
    NEXT_2 = "NEXT_2"
    BACKGROUND = "BACKGROUND"


class ParkingItemStatus(str, Enum):
    """Parking item lifecycle status."""

    PARKED = "parked"
    PROMOTED = "promoted"
    DISMISSED = "dismissed"


class DecisionLifecycle(str, Enum):
    """Decision record lifecycle."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REOPENED = "reopened"


class RelevanceLevel(str, Enum):
    """Parking item relevance assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
