"""Tests for I-08 permission policy: automatic vs confirmation-gated actions."""

from datetime import UTC, datetime

import pytest

from execution_core.domain.enums import LifecycleState, SessionIntent
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.policies.permission_policy import (
    PermissionDenied,
    PermissionPolicy,
)


def _ready_spec(confirmed: bool = False) -> Specification:
    spec = Specification(
        what="Add feature",
        why="User needs it",
        deliverable="Working feature",
        done_when=[DoneWhenCriterion(text="Feature works")],
        confirmed_at=datetime.now(UTC) if confirmed else None,
    )
    spec.update_computed_fields()
    return spec


def _session(
    state: LifecycleState, spec: Specification | None = None
) -> ExecutionSession:
    return ExecutionSession(
        project_id="test_project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=state,
        current_spec=spec,
    )


class TestAutomaticActions:
    """Inspection, spec proposal and planning are automatic in their states."""

    def test_inspection_always_allowed(self) -> None:
        assert PermissionPolicy.check_inspection_allowed(
            _session(LifecycleState.COMPLETE)
        )

    @pytest.mark.parametrize(
        ("state", "allowed"),
        [
            (LifecycleState.INSPECT, True),
            (LifecycleState.SPECIFY, True),
            (LifecycleState.CONFIRM, False),
            (LifecycleState.EXECUTE, False),
        ],
    )
    def test_spec_proposal_allowed_only_before_confirm(
        self, state: LifecycleState, allowed: bool
    ) -> None:
        assert PermissionPolicy.check_spec_proposal_allowed(_session(state)) is allowed

    def test_plan_allowed_with_ready_spec_in_confirm(self) -> None:
        session = _session(LifecycleState.CONFIRM, _ready_spec())

        assert PermissionPolicy.check_plan_allowed(session)

    def test_plan_not_allowed_without_spec(self) -> None:
        assert not PermissionPolicy.check_plan_allowed(_session(LifecycleState.PLAN))

    def test_plan_not_allowed_outside_confirm_or_plan(self) -> None:
        session = _session(LifecycleState.EXECUTE, _ready_spec())

        assert not PermissionPolicy.check_plan_allowed(session)


class TestSmallBoundedChange:
    """Small changes are automatic after confirmation; larger ones are not."""

    def test_rejected_outside_execution_phase(self) -> None:
        session = _session(LifecycleState.PLAN, _ready_spec(confirmed=True))

        allowed, reason = PermissionPolicy.check_small_bounded_change_allowed(
            session, "small", confirmed=False
        )

        assert not allowed
        assert reason == "Not in execution phase"

    def test_rejected_without_confirmed_spec(self) -> None:
        session = _session(LifecycleState.EXECUTE, _ready_spec(confirmed=False))

        allowed, reason = PermissionPolicy.check_small_bounded_change_allowed(
            session, "small", confirmed=False
        )

        assert not allowed
        assert reason == "Spec not confirmed"

    @pytest.mark.parametrize("scope", ["large", "destructive", "expanding"])
    def test_wide_scope_needs_explicit_confirmation(self, scope: str) -> None:
        session = _session(LifecycleState.VERIFY, _ready_spec(confirmed=True))

        allowed, reason = PermissionPolicy.check_small_bounded_change_allowed(
            session, scope, confirmed=False
        )

        assert not allowed
        assert reason == f"Explicit confirmation required for {scope} change"

    def test_wide_scope_allowed_when_confirmed(self) -> None:
        session = _session(LifecycleState.EXECUTE, _ready_spec(confirmed=True))

        allowed, reason = PermissionPolicy.check_small_bounded_change_allowed(
            session, "destructive", confirmed=True
        )

        assert allowed
        assert reason == ""

    def test_small_scope_allowed_without_extra_confirmation(self) -> None:
        session = _session(LifecycleState.EXECUTE, _ready_spec(confirmed=True))

        allowed, reason = PermissionPolicy.check_small_bounded_change_allowed(
            session, "small", confirmed=False
        )

        assert allowed
        assert reason == ""


class TestConfirmationRules:
    """Large-change confirmation, spec ownership and test permissions."""

    def test_large_change_without_confirmation_raises(self) -> None:
        with pytest.raises(PermissionDenied) as exc_info:
            PermissionPolicy.require_confirmation_for_large_change(
                "expanding", confirmed=False
            )

        assert exc_info.value.required_permission == "explicit_confirmation_expanding"

    def test_small_change_needs_no_confirmation(self) -> None:
        PermissionPolicy.require_confirmation_for_large_change("small", confirmed=False)

    @pytest.mark.parametrize("user_confirmed", [True, False])
    def test_spec_confirmation_belongs_to_user(self, user_confirmed: bool) -> None:
        assert (
            PermissionPolicy.check_spec_confirmation_belongs_to_user(user_confirmed)
            is user_confirmed
        )

    @pytest.mark.parametrize(
        ("granted", "allowed"),
        [
            (["run_tests"], True),
            (["verification"], True),
            (["read_files"], False),
            ([], False),
        ],
    )
    def test_tests_allowed_only_under_granted_permission(
        self, granted: list[str], allowed: bool
    ) -> None:
        assert PermissionPolicy.check_tests_allowed(granted) is allowed


class TestClassifyChangeScope:
    """Scope classification order: destructive, expanding, large, small."""

    @pytest.mark.parametrize(
        ("files", "destructive", "outside_spec", "expected"),
        [
            (1, True, True, "destructive"),
            (50, False, True, "expanding"),
            (11, False, False, "large"),
            (10, False, False, "small"),
        ],
    )
    def test_classification(
        self, files: int, destructive: bool, outside_spec: bool, expected: str
    ) -> None:
        assert (
            PermissionPolicy.classify_change_scope(files, destructive, outside_spec)
            == expected
        )
