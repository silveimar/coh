"""Tests for domain event models: snake_case event types and serialization."""

from typing import Any
from uuid import uuid4

import pytest

from execution_core.domain.enums import LifecycleState
from execution_core.events.domain_events import (
    ArchiveRecorded,
    ArchiveWriteFailed,
    CheckpointCreated,
    CompletionStateChanged,
    DecisionRecorded,
    DomainEvent,
    EvidenceRecorded,
    ForegroundCalculated,
    ParkingItemCreated,
    ReadinessChanged,
    RecoveryInitiated,
    SessionStarted,
    SpecConfirmed,
    SpecCorrected,
    SpecProposed,
    StateTransitioned,
    TaskCreated,
    TaskStatusChanged,
)

EVENT_CASES: list[tuple[type[DomainEvent], str, dict[str, Any]]] = [
    (
        SessionStarted,
        "session_started",
        {"project_id": "test_project", "intent": "execute"},
    ),
    (
        StateTransitioned,
        "state_transitioned",
        {
            "from_state": LifecycleState.INSPECT,
            "to_state": LifecycleState.SPECIFY,
            "transition_id": "T2",
        },
    ),
    (SpecProposed, "spec_proposed", {"spec_id": uuid4(), "spec_revision": 1}),
    (
        SpecConfirmed,
        "spec_confirmed",
        {"spec_id": uuid4(), "spec_revision": 1, "user_confirmed": True},
    ),
    (
        SpecCorrected,
        "spec_corrected",
        {"old_spec_id": uuid4(), "new_spec_id": uuid4(), "new_revision": 2},
    ),
    (
        ReadinessChanged,
        "readiness_changed",
        {
            "spec_id": uuid4(),
            "old_readiness": "blocked",
            "new_readiness": "ready",
            "blockers": [],
        },
    ),
    (TaskCreated, "task_created", {"task_id": uuid4(), "spec_id": uuid4()}),
    (
        TaskStatusChanged,
        "task_status_changed",
        {"task_id": uuid4(), "old_status": "planned", "new_status": "in_progress"},
    ),
    (ForegroundCalculated, "foreground_calculated", {"parked_count": 0}),
    (
        EvidenceRecorded,
        "evidence_recorded",
        {
            "evidence_id": uuid4(),
            "criterion_id": uuid4(),
            "result": "pass",
            "authority": "tool_verified",
        },
    ),
    (
        CompletionStateChanged,
        "completion_state_changed",
        {"task_id": uuid4(), "old_state": "implemented", "new_state": "tested"},
    ),
    (
        CheckpointCreated,
        "checkpoint_created",
        {
            "checkpoint_id": uuid4(),
            "lifecycle_state": LifecycleState.EXECUTE,
            "restart_action": "Resume the handler",
            "archive_status": "healthy",
        },
    ),
    (
        RecoveryInitiated,
        "recovery_initiated",
        {"checkpoint_id": uuid4(), "restored_state": LifecycleState.PLAN},
    ),
    (DecisionRecorded, "decision_recorded", {"decision_id": uuid4(), "material": True}),
    (
        ParkingItemCreated,
        "parking_item_created",
        {
            "parking_item_id": uuid4(),
            "relevance": "low",
            "blocking": False,
            "auto_parked": True,
        },
    ),
    (
        ArchiveRecorded,
        "archive_recorded",
        {"path": ".coh/archive/session/inspect.md", "anchor": "inspect-findings"},
    ),
    (ArchiveWriteFailed, "archive_write_failed", {"reason": "disk full"}),
]


class TestDomainEvents:
    """Each event carries its snake_case type and round-trips through JSON."""

    @pytest.mark.parametrize(
        ("event_cls", "event_type", "fields"),
        EVENT_CASES,
        ids=[case[1] for case in EVENT_CASES],
    )
    def test_event_type_and_json_round_trip(
        self,
        event_cls: type[DomainEvent],
        event_type: str,
        fields: dict[str, Any],
    ) -> None:
        event = event_cls(session_id=uuid4(), actor="user", **fields)

        assert event.event_type == event_type
        assert event.metadata == {}
        assert event_cls.model_validate_json(event.model_dump_json()) == event

    def test_optional_fields_default_to_empty(self) -> None:
        foreground = ForegroundCalculated(
            session_id=uuid4(), actor="system", parked_count=2
        )
        failure = ArchiveWriteFailed(session_id=uuid4(), actor="system", reason="io")
        status = TaskStatusChanged(
            session_id=uuid4(),
            actor="system",
            task_id=uuid4(),
            old_status="planned",
            new_status="blocked",
        )

        assert foreground.now_task_id is None
        assert foreground.next_task_ids == []
        assert failure.checkpoint_id is None
        assert status.reason is None

    def test_event_ids_are_unique(self) -> None:
        session_id = uuid4()
        first = SessionStarted(
            session_id=session_id, actor="user", project_id="p", intent="execute"
        )
        second = SessionStarted(
            session_id=session_id, actor="user", project_id="p", intent="execute"
        )

        assert first.id != second.id
