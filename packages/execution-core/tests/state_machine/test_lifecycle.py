"""Tests for state machine lifecycle transitions T1-T11."""

from uuid import uuid4

import pytest

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.commands import (
    ConcurrencyError,
    ConfirmSpecCommand,
    RecoverCommand,
    ReviseGoalCommand,
    TransitionToSpecifyCommand,
)
from execution_core.domain.enums import (
    ArchiveStatus,
    EvidenceAuthority,
    EvidenceResult,
    LifecycleState,
    SessionIntent,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.specification import (
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from execution_core.policies.completion_policy import CompletionViolation
from execution_core.policies.readiness_policy import ReadinessViolation
from execution_core.state_machine.lifecycle import StateMachine, TransitionError


class TestStateMachineTransitions:
    """Test lifecycle transitions T1-T11 with guard validation and commands."""

    def test_t1_start_session_creates_inspect_state(self) -> None:
        """T1: Session start should enter INSPECT state."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)

        assert session.lifecycle_state == LifecycleState.INSPECT
        assert session.project_id == "project-1"
        assert session.intent == SessionIntent.EXECUTE
        assert session.version == 1

    def test_t2_inspect_to_specify_with_command(self) -> None:
        """T2: INSPECT → SPECIFY requires command with version check."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd = TransitionToSpecifyCommand(
            idempotency_key="cmd_t2_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd
        )

        assert session.lifecycle_state == LifecycleState.SPECIFY
        assert session.version == 2

    def test_t2_inspect_to_specify_fails_without_archive(self) -> None:
        """T2: INSPECT → SPECIFY fails without archived findings."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd = TransitionToSpecifyCommand(
            idempotency_key="cmd_t2_fail",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )

        with pytest.raises(TransitionError) as exc:
            machine.transition_to_specify(session, findings_archived=False, command=cmd)

        assert "findings not archived" in str(exc.value)

    def test_t2_inspect_to_specify_fails_with_wrong_version(self) -> None:
        """T2: Transition fails with stale version."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd = TransitionToSpecifyCommand(
            idempotency_key="cmd_t2_stale",
            expected_version=99,  # Wrong version
            session_id=session.id,
            findings_archived=True,
        )

        with pytest.raises(ConcurrencyError):
            machine.transition_to_specify(session, findings_archived=True, command=cmd)

    def test_t3_specify_to_confirm_with_complete_spec(self) -> None:
        """T3: SPECIFY → CONFIRM requires complete spec."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd1 = TransitionToSpecifyCommand(
            idempotency_key="cmd_t3_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd1
        )

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()

        cmd2 = ConfirmSpecCommand(
            idempotency_key="cmd_t3_002",
            expected_version=2,
            session_id=session.id,
            spec=spec,
            user_confirmed=False,
        )
        session = machine.transition_to_confirm(session, spec, cmd2)

        assert session.lifecycle_state == LifecycleState.CONFIRM
        assert session.current_spec is not None

    def test_t3_specify_to_confirm_fails_with_incomplete_spec(self) -> None:
        """T3: SPECIFY → CONFIRM fails without required fields."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd1 = TransitionToSpecifyCommand(
            idempotency_key="cmd_t3_fail_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd1
        )

        spec = Specification(what="Add feature", why="", deliverable="", done_when=[])
        spec.update_computed_fields()

        cmd2 = ConfirmSpecCommand(
            idempotency_key="cmd_t3_fail_002",
            expected_version=2,
            session_id=session.id,
            spec=spec,
            user_confirmed=False,
        )

        with pytest.raises(TransitionError) as exc:
            machine.transition_to_confirm(session, spec, cmd2)

        assert "incomplete spec" in str(exc.value)

    def test_t4_confirm_to_plan_requires_readiness_and_confirmation(self) -> None:
        """T4: CONFIRM → PLAN enforces I-02 readiness and I-08 confirmation."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        # Transition to SPECIFY
        cmd1 = TransitionToSpecifyCommand(
            idempotency_key="cmd_t4_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd1
        )

        # Create ready spec
        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()

        # Transition to CONFIRM
        cmd2 = ConfirmSpecCommand(
            idempotency_key="cmd_t4_002",
            expected_version=2,
            session_id=session.id,
            spec=spec,
            user_confirmed=False,
        )
        session = machine.transition_to_confirm(session, spec, cmd2)

        # Transition to PLAN with user confirmation
        from execution_core.domain.commands import TransitionToPlanCommand

        cmd3 = TransitionToPlanCommand(
            idempotency_key="cmd_t4_003",
            expected_version=3,
            session_id=session.id,
            user_confirmed=True,
        )
        session = machine.transition_to_plan(
            session, user_confirmed=True, command=cmd3, change_scope="small"
        )

        assert session.lifecycle_state == LifecycleState.PLAN

    def test_t4_confirm_to_plan_fails_with_blocked_readiness(self) -> None:
        """T4: CONFIRM → PLAN fails if readiness is blocked (I-02)."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd1 = TransitionToSpecifyCommand(
            idempotency_key="cmd_t4_blocked_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd1
        )

        # Create spec with blocking unknown
        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()
        spec.unknowns.append(Unknown(text="Blocking unknown", blocking=True))
        spec.update_computed_fields()

        cmd2 = ConfirmSpecCommand(
            idempotency_key="cmd_t4_blocked_002",
            expected_version=2,
            session_id=session.id,
            spec=spec,
            user_confirmed=False,
        )
        session = machine.transition_to_confirm(session, spec, cmd2)

        from execution_core.domain.commands import TransitionToPlanCommand

        cmd3 = TransitionToPlanCommand(
            idempotency_key="cmd_t4_blocked_003",
            expected_version=3,
            session_id=session.id,
            user_confirmed=True,
        )

        with pytest.raises(ReadinessViolation) as exc:
            machine.transition_to_plan(
                session, user_confirmed=True, command=cmd3, change_scope="small"
            )

        assert "readiness" in str(exc.value).lower()

    def test_t5_correct_spec_returns_to_specify(self) -> None:
        """T5: CONFIRM → SPECIFY on user correction creates revision."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        cmd1 = TransitionToSpecifyCommand(
            idempotency_key="cmd_t5_001",
            expected_version=1,
            session_id=session.id,
            findings_archived=True,
        )
        session = machine.transition_to_specify(
            session, findings_archived=True, command=cmd1
        )

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()

        cmd2 = ConfirmSpecCommand(
            idempotency_key="cmd_t5_002",
            expected_version=2,
            session_id=session.id,
            spec=spec,
            user_confirmed=False,
        )
        session = machine.transition_to_confirm(session, spec, cmd2)

        corrected_spec = spec.model_copy(deep=True)
        corrected_spec.what = "Updated feature description"

        from execution_core.domain.commands import Command

        cmd3 = Command(idempotency_key="cmd_t5_003", expected_version=3)
        session = machine.correct_spec(session, corrected_spec, cmd3)

        assert session.lifecycle_state == LifecycleState.SPECIFY
        assert session.current_spec.revision == spec.revision + 1

    def test_t6_plan_to_execute_enforces_readiness(self) -> None:
        """T6: PLAN → EXECUTE enforces I-02 readiness."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.PLAN

        # Spec with blocking unknown (readiness will be BLOCKED)
        spec = Specification(
            what="Feature",
            why="Needed",
            deliverable="Output",
            done_when=[DoneWhenCriterion(text="Works")],
            unknowns=[Unknown(text="How to implement?", blocking=True, resolved=False)],
        )
        spec.update_computed_fields()
        session.current_spec = spec

        from execution_core.domain.commands import TransitionToExecuteCommand

        cmd = TransitionToExecuteCommand(
            idempotency_key="cmd_t6_001",
            expected_version=1,
            session_id=session.id,
            foreground_computed=True,
        )

        # Should fail on readiness check before reaching foreground check
        from execution_core.policies.readiness_policy import ReadinessViolation

        with pytest.raises(ReadinessViolation):
            # Pass empty tasks - will fail on readiness first
            machine.transition_to_execute(session, cmd, tasks=[])

    def test_t7_execute_to_verify_enforces_readiness(self) -> None:
        """T7: EXECUTE → VERIFY enforces I-02 readiness."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.EXECUTE

        spec = Specification(
            what="Feature",
            why="Needed",
            deliverable="Output",
            done_when=[DoneWhenCriterion(text="Works")],
        )
        spec.update_computed_fields()
        session.current_spec = spec

        from execution_core.domain.commands import TransitionToVerifyCommand

        cmd = TransitionToVerifyCommand(
            idempotency_key="cmd_t7_001",
            expected_version=1,
            session_id=session.id,
            work_completed=True,
        )
        session = machine.transition_to_verify(session, cmd)

        assert session.lifecycle_state == LifecycleState.VERIFY

    def test_t8_verify_to_execute_on_failed_criteria(self) -> None:
        """T8: VERIFY → EXECUTE when criteria fail."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        from execution_core.domain.commands import Command

        cmd = Command(idempotency_key="cmd_t8_001", expected_version=1)
        session = machine.return_to_execute(session, cmd)

        assert session.lifecycle_state == LifecycleState.EXECUTE

    def test_t9_verify_to_complete_enforces_evidence_gate(self) -> None:
        """T9: VERIFY → COMPLETE enforces I-03 evidence gate."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        criterion = DoneWhenCriterion(text="Tests pass")
        spec = Specification(
            what="Feature",
            why="Needed",
            deliverable="Output",
            done_when=[criterion],
        )
        spec.update_computed_fields()
        session.current_spec = spec

        # Create qualifying evidence
        evidence = Evidence(
            id=uuid4(),
            criterion_id=criterion.id,
            evidence_type="test",
            source="ci_system",
            result=EvidenceResult.PASS,
            authority=EvidenceAuthority.TOOL_VERIFIED,
            spec_id=spec.id,
            spec_revision=1,
            summary="All tests passed",
        )

        from execution_core.domain.commands import CompleteVerificationCommand

        cmd = CompleteVerificationCommand(
            idempotency_key="cmd_t9_001",
            expected_version=1,
            session_id=session.id,
            evidence_ids=[evidence.id],
        )
        session = machine.transition_to_complete(session, [evidence], cmd)

        assert session.lifecycle_state == LifecycleState.COMPLETE

    def test_t9_verify_to_complete_fails_without_evidence(self) -> None:
        """T9: VERIFY → COMPLETE fails without qualifying evidence (I-03)."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        criterion = DoneWhenCriterion(text="Tests pass")
        spec = Specification(
            what="Feature",
            why="Needed",
            deliverable="Output",
            done_when=[criterion],
        )
        spec.update_computed_fields()
        session.current_spec = spec

        from execution_core.domain.commands import CompleteVerificationCommand

        cmd = CompleteVerificationCommand(
            idempotency_key="cmd_t9_fail",
            expected_version=1,
            session_id=session.id,
            evidence_ids=[],
        )

        with pytest.raises(CompletionViolation):
            machine.transition_to_complete(session, [], cmd)

    def test_t10_goal_revision_requires_checkpoint_first(self) -> None:
        """T10: Goal revision requires checkpoint before new spec."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.EXECUTE

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.EXECUTE,
            restart_action="Continue implementation",
            archive_status=ArchiveStatus.HEALTHY,
        )

        new_spec = Specification(
            what="Revised goal",
            why="Requirements changed",
            deliverable="New output",
            done_when=[DoneWhenCriterion(text="New criteria")],
        )
        new_spec.update_computed_fields()

        cmd = ReviseGoalCommand(
            idempotency_key="cmd_t10_001",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=checkpoint.id,
            new_spec=new_spec,
        )
        session = machine.revise_goal(session, checkpoint, new_spec, cmd)

        assert session.lifecycle_state == LifecycleState.SPECIFY

    def test_t10_goal_revision_fails_without_checkpoint(self) -> None:
        """T10: Goal revision fails without checkpoint."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        new_spec = Specification(
            what="Revised",
            why="Changed",
            deliverable="New",
            done_when=[DoneWhenCriterion(text="New")],
        )
        new_spec.update_computed_fields()

        cmd = ReviseGoalCommand(
            idempotency_key="cmd_t10_fail",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=uuid4(),
            new_spec=new_spec,
        )

        with pytest.raises(TransitionError) as exc:
            machine.revise_goal(session, None, new_spec, cmd)  # type: ignore

        assert "checkpoint required" in str(exc.value)

    def test_t11_recover_restores_state_and_renders_summary(self) -> None:
        """T11: Recover command restores state and renders recovery summary."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        spec = Specification(
            what="Feature",
            why="Needed",
            deliverable="Output",
            done_when=[DoneWhenCriterion(text="Works")],
        )
        spec.update_computed_fields()
        session.current_spec = spec
        session.lifecycle_state = LifecycleState.COMPLETE

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.EXECUTE,
            restart_action="Continue from checkpoint",
            archive_status=ArchiveStatus.HEALTHY,
            spec_id=spec.id,
            spec_revision=spec.revision,
        )

        cmd = RecoverCommand(
            idempotency_key="cmd_t11_001",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=checkpoint.id,
        )
        session, summary = machine.recover(session, checkpoint, cmd)

        assert session.lifecycle_state == LifecycleState.EXECUTE
        assert summary.restart_action == "Continue from checkpoint"
        assert summary.checkpoint_id == checkpoint.id
        assert not summary.archive_degraded

    def test_t11_recover_reports_degraded_archive(self) -> None:
        """T11: Recover reports when archive is degraded."""
        machine = StateMachine()
        session = machine.start_session("project-1", SessionIntent.EXECUTE)

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.PLAN,
            restart_action="Resume planning",
            archive_status=ArchiveStatus.DEGRADED,
        )

        cmd = RecoverCommand(
            idempotency_key="cmd_t11_degraded",
            expected_version=1,
            session_id=session.id,
            checkpoint_id=checkpoint.id,
        )
        session, summary = machine.recover(session, checkpoint, cmd)

        assert summary.archive_degraded

    def test_can_transition_allows_t10_any_to_specify(self) -> None:
        """can_transition allows T10 (any → SPECIFY)."""
        can, error = StateMachine.can_transition(
            LifecycleState.EXECUTE, LifecycleState.SPECIFY
        )
        assert can
        assert error is None

    def test_can_transition_allows_t11_recover_same_state(self) -> None:
        """can_transition allows T11 (recover to same state)."""
        can, error = StateMachine.can_transition(
            LifecycleState.EXECUTE, LifecycleState.EXECUTE
        )
        assert can
        assert error is None

    def test_invalid_transition_detected(self) -> None:
        """Invalid transitions should be detected."""
        can, error = StateMachine.can_transition(
            LifecycleState.CONFIRM, LifecycleState.COMPLETE
        )
        assert not can
        assert "Invalid transition" in error

    def test_valid_sequential_transition_allowed(self) -> None:
        """Valid sequential transitions should be allowed."""
        can, error = StateMachine.can_transition(
            LifecycleState.PLAN, LifecycleState.EXECUTE
        )
        assert can
        assert error is None
