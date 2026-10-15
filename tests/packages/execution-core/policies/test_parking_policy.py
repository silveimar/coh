"""Tests for I-10 parking, I-05 progress and I-11 detour policies."""

from uuid import uuid4

import pytest

from execution_core.domain.enums import RelevanceLevel, SessionIntent, TaskStatus
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.task import Task
from execution_core.policies.parking_policy import (
    DriftPolicy,
    ParkingPolicy,
    ProgressPolicy,
)


def _task(**overrides: object) -> Task:
    fields: dict[str, object] = {"spec_id": uuid4(), "spec_revision": 1}
    fields.update(overrides)
    return Task.model_validate(fields)


def _parking_item(relevance: RelevanceLevel, blocking: bool) -> ParkingItem:
    return ParkingItem(
        text="Discovered a related cleanup",
        relevance=relevance,
        blocking=blocking,
        suggested_disposition="revisit after NOW",
    )


class TestParkingPolicy:
    """I-10: parking classifies deterministically and never changes NOW."""

    @pytest.mark.parametrize(
        ("relevance", "blocking", "expected"),
        [
            (RelevanceLevel.LOW, False, True),
            (RelevanceLevel.LOW, True, False),
            (RelevanceLevel.MEDIUM, False, False),
        ],
    )
    def test_should_auto_park(
        self, relevance: RelevanceLevel, blocking: bool, expected: bool
    ) -> None:
        assert ParkingPolicy.should_auto_park(relevance, blocking) is expected

    @pytest.mark.parametrize(
        ("text", "relevance", "blocking"),
        [
            ("This is critical and breaks the build", RelevanceLevel.HIGH, True),
            ("Maybe a nice idea for the future", RelevanceLevel.LOW, False),
            ("Rename a variable", RelevanceLevel.MEDIUM, False),
            ("The config is WRONG", RelevanceLevel.MEDIUM, True),
        ],
    )
    def test_classify_relevance_blocking(
        self, text: str, relevance: RelevanceLevel, blocking: bool
    ) -> None:
        assert ParkingPolicy.classify_relevance_blocking(text, _task()) == (
            relevance,
            blocking,
        )

    @pytest.mark.parametrize(
        ("relevance", "blocking"),
        [(RelevanceLevel.HIGH, False), (RelevanceLevel.LOW, True)],
    )
    def test_high_relevance_or_blocking_needs_checkpoint(
        self, relevance: RelevanceLevel, blocking: bool
    ) -> None:
        item = _parking_item(relevance, blocking)

        assert not ParkingPolicy.require_checkpoint_before_high_relevance(item, False)
        assert ParkingPolicy.require_checkpoint_before_high_relevance(item, True)

    def test_low_relevance_needs_no_checkpoint(self) -> None:
        item = _parking_item(RelevanceLevel.LOW, blocking=False)

        assert ParkingPolicy.require_checkpoint_before_high_relevance(item, False)

    def test_park_leaves_now_unchanged(self) -> None:
        now = _task(status=TaskStatus.IN_PROGRESS)
        before = now.model_copy(deep=True)
        item = _parking_item(RelevanceLevel.MEDIUM, blocking=False)

        returned_now, returned_item = ParkingPolicy.park_without_changing_now(now, item)

        assert returned_now is now
        assert returned_now == before
        assert returned_item is item


class TestProgressPolicy:
    """I-05: unfinished work needs a progress record before a switch."""

    @pytest.mark.parametrize("status", [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
    def test_unfinished_task_without_record_is_rejected(
        self, status: TaskStatus
    ) -> None:
        with pytest.raises(ValueError, match="I-05"):
            ProgressPolicy.require_progress_before_switch(_task(status=status), None)

    def test_unfinished_task_with_record_may_switch(self) -> None:
        task = _task(status=TaskStatus.IN_PROGRESS)
        record = ProgressPolicy.create_progress_record(task)

        assert ProgressPolicy.require_progress_before_switch(task, record)

    def test_planned_task_needs_no_record(self) -> None:
        assert ProgressPolicy.require_progress_before_switch(_task(), None)

    def test_progress_record_carries_blocked_reason(self) -> None:
        task = _task()
        task.mark_blocked("Waiting on API key")

        record = ProgressPolicy.create_progress_record(task)

        assert record.task_id == task.id
        assert record.status == TaskStatus.BLOCKED
        assert record.blockers == ["Waiting on API key"]

    def test_progress_record_without_blocker(self) -> None:
        record = ProgressPolicy.create_progress_record(_task())

        assert record.blockers == []


class TestDetourEvaluation:
    """I-11: an on-intent action is not a detour."""

    def test_on_intent_action_continues(self) -> None:
        is_detour, recommendation, alternatives = DriftPolicy.evaluate_detour(
            "Write the endpoint handler",
            "implement feature",
            SessionIntent.EXECUTE,
        )

        assert not is_detour
        assert recommendation == "Continue"
        assert alternatives == []
