"""Parking policy enforcing I-10 (parking preserves focus) and I-11 (drift)."""

from ..domain.enums import RelevanceLevel, SessionIntent
from ..domain.parking_item import ParkingItem
from ..domain.task import Task, TaskProgressRecord


class ParkingPolicy:
    """Enforces I-10: parking items never change NOW execution state."""

    @staticmethod
    def should_auto_park(relevance: RelevanceLevel, blocking: bool) -> bool:
        """Deterministic auto-park rule: low relevance AND non-blocking."""
        return ParkingItem.should_auto_park(relevance, blocking)

    @staticmethod
    def classify_relevance_blocking(
        item_text: str, source_task: Task
    ) -> tuple[RelevanceLevel, bool]:
        """Deterministic classification using configurable heuristics."""
        blocking_keywords = ["breaks", "invalid", "wrong", "blocker", "cannot"]
        high_relevance_keywords = ["critical", "urgent", "required", "must"]
        low_relevance_keywords = ["nice", "future", "maybe", "consider", "idea"]

        text_lower = item_text.lower()

        blocking = any(kw in text_lower for kw in blocking_keywords)

        if any(kw in text_lower for kw in high_relevance_keywords):
            relevance = RelevanceLevel.HIGH
        elif any(kw in text_lower for kw in low_relevance_keywords):
            relevance = RelevanceLevel.LOW
        else:
            relevance = RelevanceLevel.MEDIUM

        return relevance, blocking

    @staticmethod
    def require_checkpoint_before_high_relevance(
        parking_item: ParkingItem, checkpoint_created: bool
    ) -> bool:
        """Enforce I-10: high-relevance/blocking items need checkpoint first."""
        if parking_item.relevance == RelevanceLevel.HIGH or parking_item.blocking:
            return checkpoint_created
        return True

    @staticmethod
    def park_without_changing_now(
        now_task: Task, parking_item: ParkingItem
    ) -> tuple[Task, ParkingItem]:
        """Enforce I-10: creating parking item leaves NOW unchanged."""
        return now_task, parking_item


class ProgressPolicy:
    """Enforces I-05: progress record before foreground switch."""

    @staticmethod
    def require_progress_before_switch(
        task: Task, progress_record: TaskProgressRecord | None
    ) -> bool:
        """Enforce I-05: unfinished task must have progress before switch."""
        if task.status in ["in_progress", "blocked"] and not progress_record:
            raise ValueError(
                f"Cannot switch from task {task.id}: "
                "progress record required before foreground change (I-05)"
            )
        return True

    @staticmethod
    def create_progress_record(task: Task) -> TaskProgressRecord:
        """Create interruption-safe progress record for task."""
        return TaskProgressRecord(
            task_id=task.id,
            status=task.status,
            completed_work=[],
            attempted_work=[],
            blockers=[task.blocked_reason] if task.blocked_reason else [],
            next_steps=[],
        )


class DriftPolicy:
    """Enforces I-11: drift evaluation relative to session intent."""

    @staticmethod
    def is_drift(
        session_intent: SessionIntent, current_action: str, objective: str
    ) -> tuple[bool, str]:
        """
        Intent-relative drift detection (I-11).

        Returns (is_drift, reason) tuple.
        """
        drift_signals = {
            SessionIntent.EXECUTE: ["plan", "brainstorm", "unrelated"],
            SessionIntent.PLAN: ["implement", "test", "unrelated"],
            SessionIntent.BRAINSTORM: ["implement", "converge_without_evaluation"],
            SessionIntent.REVIEW: ["modify", "implement"],
            SessionIntent.STUDY: ["tangent", "unrelated"],
            SessionIntent.RECOVER: ["new_scope"],
        }

        signals = drift_signals.get(session_intent, [])
        action_lower = current_action.lower()

        for signal in signals:
            if signal in action_lower:
                return (
                    True,
                    f"Drift detected: {signal} deviates from {session_intent.value}",
                )

        return False, ""

    @staticmethod
    def evaluate_detour(
        current_action: str, objective: str, session_intent: SessionIntent
    ) -> tuple[bool, str, list[str]]:
        """
        Evaluate if current action is intentional detour or drift.

        Returns (is_detour, recommendation, alternatives).
        """
        is_drift_detected, reason = DriftPolicy.is_drift(
            session_intent, current_action, objective
        )

        if not is_drift_detected:
            return False, "Continue", []

        # Provide recommendation and alternatives
        recommendation = "Investigate relevance before continuing"
        alternatives = [
            "Continue intentionally and record detour",
            "Park discovery and return to objective",
            "Revise goal if discovery invalidates objective",
        ]

        return True, recommendation, alternatives
