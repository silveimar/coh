"""Stored-format guard: timestamps that defaulted through utcnow stay naive UTC.

JSON columns store these values with isoformat(); an aware default would add
"+00:00" to newly stored strings (Phase 2 CONTEXT D-01, D-06).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel

from execution_core.domain.decision import Decision
from execution_core.domain.enums import (
    AssumptionClass,
    EvidenceAuthority,
    EvidenceResult,
    RelevanceLevel,
    SessionIntent,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.foreground import Foreground
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import (
    Assumption,
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from execution_core.domain.task import Task

DEFAULTED_FIELDS: list[tuple[str, Callable[[], BaseModel], tuple[str, ...]]] = [
    (
        "Task",
        lambda: Task(spec_id=uuid4(), spec_revision=1),
        ("created_at", "updated_at"),
    ),
    (
        "Evidence",
        lambda: Evidence(
            spec_id=uuid4(),
            spec_revision=1,
            criterion_id=uuid4(),
            evidence_type="test_run",
            authority=EvidenceAuthority.TOOL_VERIFIED,
            result=EvidenceResult.PASS,
            summary="synthetic summary",
            source="synthetic",
        ),
        ("recorded_at",),
    ),
    (
        "Decision",
        lambda: Decision(
            question="synthetic question",
            selected_option="a",
            rationale="synthetic rationale",
        ),
        ("created_at",),
    ),
    (
        "ParkingItem",
        lambda: ParkingItem(
            text="synthetic item",
            relevance=RelevanceLevel.LOW,
            suggested_disposition="revisit later",
        ),
        ("created_at",),
    ),
    (
        "ExecutionSession",
        lambda: ExecutionSession(
            project_id="synthetic-project", intent=SessionIntent.EXECUTE
        ),
        ("created_at", "updated_at"),
    ),
    (
        "Foreground",
        lambda: Foreground(session_id=uuid4(), goal="synthetic goal"),
        ("calculated_at",),
    ),
    (
        "Specification",
        lambda: Specification(
            what="synthetic what", why="synthetic why", deliverable="synthetic"
        ),
        ("created_at", "updated_at"),
    ),
    (
        "DoneWhenCriterion",
        lambda: DoneWhenCriterion(text="synthetic criterion"),
        ("created_at",),
    ),
    (
        "Assumption",
        lambda: Assumption(
            text="synthetic assumption", classification=AssumptionClass.SAFE
        ),
        ("created_at",),
    ),
    (
        "Unknown",
        lambda: Unknown(text="synthetic unknown", blocking=False),
        ("created_at",),
    ),
]


@pytest.mark.parametrize(
    ("factory", "fields"),
    [(factory, fields) for _, factory, fields in DEFAULTED_FIELDS],
    ids=[name for name, _, _ in DEFAULTED_FIELDS],
)
def test_default_timestamp_is_naive_utc(
    factory: Callable[[], BaseModel], fields: tuple[str, ...]
) -> None:
    before = datetime.now(UTC).replace(tzinfo=None)
    model = factory()
    after = datetime.now(UTC).replace(tzinfo=None)

    for field in fields:
        value = getattr(model, field)
        assert isinstance(value, datetime)
        assert value.tzinfo is None, field
        assert "+" not in value.isoformat(), field
        assert not value.isoformat().endswith("Z"), field
        assert before <= value <= after, field
