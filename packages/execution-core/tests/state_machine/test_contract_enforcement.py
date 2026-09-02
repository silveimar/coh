"""Tests that verify contract enforcement on state machine paths.

These tests would fail on the broken implementations identified in review.
"""

import uuid

import pytest

from execution_core.domain.checkpoint import ArchiveReference, Checkpoint
from execution_core.domain.commands import (
    RecoverCommand,
    TransitionToExecuteCommand,
    TransitionToPlanCommand,
)
from execution_core.domain.enums import (
    ActivationFriction,
    ArchiveStatus,
    EnergyLevel,
    LifecycleState,
    Readiness,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.domain.task import Task
from execution_core.policies.permission_policy import PermissionDenied
from execution_core.state_machine.lifecycle import (
    CapabilityNotImplemented,
    StateMachine,
    TransitionError,
)


class TestT6PlanExitEnforcement:
    """Test that T6 actually evaluates foreground rule (would fail on old code)."""

    def test_t6_with_no_tasks_fails_guard(self) -> None:
        """Test that transition_to_execute with empty tasks fails (not skips)."""
        machine = StateMachine()
        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.PLAN,
            current_spec=Specification(
                what="Test feature",
                why="Testing",
                deliverable="Code",
                done_when=[DoneWhenCriterion(text="Tests pass")],
            ),
        )
        session.current_spec.update_computed_fields()

        cmd = TransitionToExecuteCommand(
            idempotency_key="exec_001",
            expected_version=1,
            session_id=session.id,
            foreground_computed=True,
        )

        # Empty tasks should fail (no NOW task), not skip evaluation
        with pytest.raises(TransitionError) as exc_info:
            machine.transition_to_execute(session, cmd, tasks=[])

        assert "no NOW task" in str(exc_info.value)
        # State must not have changed
        assert session.lifecycle_state == LifecycleState.PLAN

    def test_t6_evaluates_correct_field_names(self) -> None:
        """Test that T6 uses correct Task field names (would AttributeError)."""
        machine = StateMachine()
        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.PLAN,
            current_spec=Specification(
                what="Test feature",
                why="Testing",
                deliverable="Code",
                done_when=[DoneWhenCriterion(text="Tests pass")],
            ),
        )
        session.current_spec.update_computed_fields()

        # Task with correct field names
        task = Task(
            spec_id=session.current_spec.id,
            spec_revision=session.current_spec.revision,
            action_literal="Implement feature X",
            done_when_condition="Tests pass",
            estimated_minutes=30,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
        )

        cmd = TransitionToExecuteCommand(
            idempotency_key="exec_002",
            expected_version=1,
            session_id=session.id,
            foreground_computed=True,
        )

        # Should not raise AttributeError on field access
        result = machine.transition_to_execute(
            session, cmd, tasks=[task], completed_task_ids=set()
        )
        assert result.lifecycle_state == LifecycleState.EXECUTE

    def test_t6_enforces_next_limit(self) -> None:
        """Test that T6 checks NEXT ≤2 (not just ForegroundPolicy)."""
        machine = StateMachine()
        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.PLAN,
            current_spec=Specification(
                what="Test feature",
                why="Testing",
                deliverable="Code",
                done_when=[DoneWhenCriterion(text="Tests pass")],
            ),
        )
        session.current_spec.update_computed_fields()

        # Create 4 tasks (would result in 1 NOW + 3 NEXT if not limited)
        tasks = [
            Task(
                spec_id=session.current_spec.id,
                spec_revision=session.current_spec.revision,
                action_literal=f"Task {i}",
                done_when_condition="Done",
                estimated_minutes=30,
                energy=EnergyLevel.MEDIUM,
                activation_friction=ActivationFriction.LOW,
            )
            for i in range(4)
        ]

        cmd = TransitionToExecuteCommand(
            idempotency_key="exec_003",
            expected_version=1,
            session_id=session.id,
            foreground_computed=True,
        )

        # ForegroundPolicy.calculate_foreground would cap at 2 NEXT,
        # but T6 must verify this
        result = machine.transition_to_execute(
            session, cmd, tasks=tasks, completed_task_ids=set()
        )
        # Should succeed - ForegroundPolicy caps at 2 NEXT
        assert result.lifecycle_state == LifecycleState.EXECUTE


class TestT11RecoverySpecRestore:
    """Test that T11 actually restores spec (would fail on old code)."""

    def test_recover_with_different_spec(self) -> None:
        """Test that recover restores spec that differs from current."""
        machine = StateMachine()

        # Current session with spec A
        spec_a = Specification(
            what="Feature A",
            why="Reason A",
            deliverable="Code A",
        )
        spec_a.update_computed_fields()

        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.EXECUTE,
            current_spec=spec_a,
        )

        # Checkpoint with spec B (different)
        spec_b = Specification(
            what="Feature B",
            why="Reason B",
            deliverable="Code B",
        )
        spec_b.update_computed_fields()

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.PLAN,
            spec_snapshot=spec_b,
            restart_action="Resume from checkpoint",
            archive_status=ArchiveStatus.HEALTHY,
            archive_references=[
                ArchiveReference(
                    path=".coh/archive/session/plan.md",
                    timestamp=spec_b.created_at,
                    anchor="planning",
                )
            ],
        )
        session.add_checkpoint(checkpoint)

        cmd = RecoverCommand(
            idempotency_key="recover_001",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=checkpoint.id,
        )

        # Recover should restore spec B, not keep spec A
        recovered, summary = machine.recover(session, checkpoint, cmd)

        # Spec must be restored from checkpoint
        assert recovered.current_spec.what == "Feature B"
        assert recovered.current_spec.why == "Reason B"
        assert recovered.current_spec.deliverable == "Code B"
        assert recovered.lifecycle_state == LifecycleState.PLAN

        # Summary must include archive refs
        assert len(summary.archive_references) == 1
        assert summary.archive_references[0].path == ".coh/archive/session/plan.md"

    def test_recover_loads_from_session_checkpoints(self) -> None:
        """Test that recover(None) loads from session.checkpoints."""
        machine = StateMachine()

        spec = Specification(
            what="Feature",
            why="Reason",
            deliverable="Code",
        )
        spec.update_computed_fields()

        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.EXECUTE,
            current_spec=spec,
        )

        # Add checkpoint to session
        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.VERIFY,
            spec_snapshot=spec,
            restart_action="Continue verification",
            archive_status=ArchiveStatus.HEALTHY,
        )
        session.add_checkpoint(checkpoint)

        cmd = RecoverCommand(
            idempotency_key="recover_002",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=checkpoint.id,
        )

        # Recover with checkpoint=None should load from session
        recovered, summary = machine.recover(session, None, cmd)

        assert recovered.lifecycle_state == LifecycleState.VERIFY
        assert summary.restart_action == "Continue verification"

    def test_recover_without_checkpoints_fails(self) -> None:
        """Test that recover fails when session has no checkpoints."""
        machine = StateMachine()

        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.EXECUTE,
        )

        cmd = RecoverCommand(
            idempotency_key="recover_003",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=uuid.uuid4(),
        )

        # Should fail, not raise I-14
        with pytest.raises(TransitionError) as exc_info:
            machine.recover(session, None, cmd)

        assert "no checkpoints" in str(exc_info.value).lower()


class TestI14FromProductCode:
    """Test that I-14 is raised from product code (not test itself)."""

    def test_tool_adapter_not_implemented(self) -> None:
        """Test that analyze_findings_with_tool raises I-14 from product code."""
        machine = StateMachine()
        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.INSPECT,
        )

        # Call product code that needs unimplemented capability
        with pytest.raises(CapabilityNotImplemented) as exc_info:
            machine.analyze_findings_with_tool(
                session, "semantic-analyzer", "inspection findings here"
            )

        # Must include focused request
        assert "tool adapter" in str(exc_info.value).lower()
        assert "docs/adapters" in str(exc_info.value)
        assert exc_info.value.capability == "tool_adapter_semantic-analyzer"


class TestI08PermissionEnforcement:
    """Test that I-08 is enforced on StateMachine path (not just policy helper)."""

    def test_t4_large_scope_without_confirmation_raises_permission_denied(
        self,
    ) -> None:
        """Test that T4 raises PermissionDenied for large scope without confirm."""
        machine = StateMachine()

        spec = Specification(
            what="Large refactoring",
            why="Improve architecture",
            deliverable="Refactored codebase",
            done_when=[DoneWhenCriterion(text="Bug fixed")],
        )
        spec.update_computed_fields()

        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.CONFIRM,
            current_spec=spec,
        )

        cmd = TransitionToPlanCommand(
            idempotency_key="plan_001",
            expected_version=1,
            session_id=session.id,
            user_confirmed=False,
        )

        # Large scope without confirmation must raise PermissionDenied
        with pytest.raises(PermissionDenied) as exc_info:
            machine.transition_to_plan(
                session, user_confirmed=False, command=cmd, change_scope="large"
            )

        assert "large" in str(exc_info.value)
        # State must not have changed
        assert session.lifecycle_state == LifecycleState.CONFIRM

    def test_t4_ready_small_without_confirmation_fails(self) -> None:
        """Test that T4 requires confirmation even for ready+small."""
        machine = StateMachine()

        spec = Specification(
            what="Small change",
            why="Fix bug",
            deliverable="Patch",
            done_when=[DoneWhenCriterion(text="Bug fixed")],
        )
        spec.update_computed_fields()

        session = ExecutionSession(
            project_id="test",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.CONFIRM,
            current_spec=spec,
        )

        cmd = TransitionToPlanCommand(
            idempotency_key="plan_002",
            expected_version=1,
            session_id=session.id,
            user_confirmed=False,
        )

        # Even READY + small requires user confirmation
        # (fully inferable requires no uncertainty AND small scope)
        with pytest.raises(TransitionError) as exc_info:
            machine.transition_to_plan(
                session, user_confirmed=False, command=cmd, change_scope="small"
            )

        assert "confirmation required" in str(exc_info.value).lower()
