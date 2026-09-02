"""Tests for state machine lifecycle transitions T1-T11."""

import pytest

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.enums import (
    LifecycleState,
    SessionIntent,
)
from execution_core.domain.specification import (
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from execution_core.state_machine.lifecycle import StateMachine, TransitionError


class TestStateMachineTransitions:
    """Test lifecycle transitions T1-T11 with guard validation."""

    def test_t1_start_session_creates_inspect_state(self):
        """T1: Session start should enter INSPECT state."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)

        assert session.lifecycle_state == LifecycleState.INSPECT
        assert session.project_id == "project-1"
        assert session.intent == SessionIntent.EXECUTE

    def test_t2_inspect_to_specify_with_archived_findings(self):
        """T2: INSPECT → SPECIFY requires archived findings."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)

        session = StateMachine.transition_to_specify(session, findings_archived=True)

        assert session.lifecycle_state == LifecycleState.SPECIFY

    def test_t2_inspect_to_specify_fails_without_archive(self):
        """T2: INSPECT → SPECIFY fails without archived findings."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)

        with pytest.raises(TransitionError) as exc:
            StateMachine.transition_to_specify(session, findings_archived=False)

        assert "findings not archived" in str(exc.value)

    def test_t3_specify_to_confirm_with_complete_spec(self):
        """T3: SPECIFY → CONFIRM requires complete spec."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session = StateMachine.transition_to_specify(session, findings_archived=True)

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )

        session = StateMachine.transition_to_confirm(session, spec)

        assert session.lifecycle_state == LifecycleState.CONFIRM
        assert session.current_spec is not None

    def test_t3_specify_to_confirm_fails_with_incomplete_spec(self):
        """T3: SPECIFY → CONFIRM fails without required fields."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session = StateMachine.transition_to_specify(session, findings_archived=True)

        spec = Specification(what="Add feature", why="", deliverable="", done_when=[])

        with pytest.raises(TransitionError) as exc:
            StateMachine.transition_to_confirm(session, spec)

        assert "incomplete spec" in str(exc.value)

    def test_t4_confirm_to_plan_with_ready_spec(self):
        """T4: CONFIRM → PLAN requires ready spec."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session = StateMachine.transition_to_specify(session, findings_archived=True)

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()

        session = StateMachine.transition_to_confirm(session, spec)
        session = StateMachine.transition_to_plan(session, user_confirmed=True)

        assert session.lifecycle_state == LifecycleState.PLAN

    def test_t4_confirm_to_plan_fails_with_blocked_readiness(self):
        """T4: CONFIRM → PLAN fails if readiness is blocked."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session = StateMachine.transition_to_specify(session, findings_archived=True)

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.unknowns.append(Unknown(text="Blocking unknown", blocking=True))
        spec.update_computed_fields()

        session = StateMachine.transition_to_confirm(session, spec)

        with pytest.raises(TransitionError) as exc:
            StateMachine.transition_to_plan(session, user_confirmed=True)

        assert "readiness blocked" in str(exc.value)

    def test_t5_correct_spec_returns_to_specify(self):
        """T5: CONFIRM → SPECIFY on user correction."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session = StateMachine.transition_to_specify(session, findings_archived=True)

        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Working feature",
            done_when=[DoneWhenCriterion(text="Feature works")],
        )
        spec.update_computed_fields()

        session = StateMachine.transition_to_confirm(session, spec)

        corrected_spec = spec.model_copy(deep=True)
        corrected_spec.what = "Updated feature description"

        session = StateMachine.correct_spec(session, corrected_spec)

        assert session.lifecycle_state == LifecycleState.SPECIFY
        assert session.current_spec.revision == spec.revision + 1

    def test_t6_plan_to_execute_with_plan_exit_rule(self):
        """T6: PLAN → EXECUTE requires plan exit rule met."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.PLAN

        session = StateMachine.transition_to_execute(session, plan_exit_rule_met=True)

        assert session.lifecycle_state == LifecycleState.EXECUTE

    def test_t6_plan_to_execute_fails_without_exit_rule(self):
        """T6: PLAN → EXECUTE fails if plan incomplete."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.PLAN

        with pytest.raises(TransitionError) as exc:
            StateMachine.transition_to_execute(session, plan_exit_rule_met=False)

        assert "plan incomplete" in str(exc.value)

    def test_t7_execute_to_verify_with_completion_candidate(self):
        """T7: EXECUTE → VERIFY with completion candidate."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.EXECUTE

        session = StateMachine.transition_to_verify(
            session, has_completion_candidate=True
        )

        assert session.lifecycle_state == LifecycleState.VERIFY

    def test_t8_verify_to_execute_on_failed_criteria(self):
        """T8: VERIFY → EXECUTE when criteria fail."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        session = StateMachine.return_to_execute(session, failed_criteria_count=2)

        assert session.lifecycle_state == LifecycleState.EXECUTE

    def test_t8_verify_to_execute_fails_with_no_failures(self):
        """T8: VERIFY → EXECUTE fails if no criteria failed."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        with pytest.raises(TransitionError) as exc:
            StateMachine.return_to_execute(session, failed_criteria_count=0)

        assert "no failed criteria" in str(exc.value)

    def test_t9_verify_to_complete_with_satisfied_criteria(self):
        """T9: VERIFY → COMPLETE when all criteria satisfied."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        session = StateMachine.transition_to_complete(
            session, all_criteria_satisfied=True
        )

        assert session.lifecycle_state == LifecycleState.COMPLETE

    def test_t9_verify_to_complete_fails_without_satisfied_criteria(self):
        """T9: VERIFY → COMPLETE fails if criteria not satisfied."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.VERIFY

        with pytest.raises(TransitionError) as exc:
            StateMachine.transition_to_complete(session, all_criteria_satisfied=False)

        assert "criteria not satisfied" in str(exc.value)

    def test_t10_goal_revision_from_any_state_to_specify(self):
        """T10: Any state → SPECIFY on goal revision after checkpoint."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.EXECUTE

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.EXECUTE,
            restart_action="Continue implementation",
        )

        session = StateMachine.revise_goal(session, checkpoint)

        assert session.lifecycle_state == LifecycleState.SPECIFY

    def test_t11_recover_restores_checkpointed_state(self):
        """T11: Recover command restores checkpointed state."""
        session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)
        session.lifecycle_state = LifecycleState.COMPLETE

        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.EXECUTE,
            restart_action="Continue from last checkpoint",
        )

        session, restored_state = StateMachine.recover(session, checkpoint)

        assert session.lifecycle_state == LifecycleState.EXECUTE
        assert restored_state == LifecycleState.EXECUTE

    def test_invalid_transition_detected(self):
        """Invalid transitions should be detected."""
        can_transition, error = StateMachine.can_transition(
            LifecycleState.CONFIRM, LifecycleState.EXECUTE
        )

        assert not can_transition
        assert "Invalid transition" in error

    def test_valid_transition_allowed(self):
        """Valid transitions should be allowed."""
        can_transition, error = StateMachine.can_transition(
            LifecycleState.PLAN, LifecycleState.EXECUTE
        )

        assert can_transition
        assert error is None
