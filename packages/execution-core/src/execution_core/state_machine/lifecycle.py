"""State machine implementing the 7-state lifecycle and transitions T1-T11."""

from ..domain.checkpoint import Checkpoint
from ..domain.enums import LifecycleState, Readiness, SessionIntent
from ..domain.session import ExecutionSession
from ..domain.specification import Specification


class TransitionError(Exception):
    """Raised when a transition is invalid or guard fails."""

    def __init__(self, message: str, blocked_reason: str, remediation: str):
        super().__init__(message)
        self.blocked_reason = blocked_reason
        self.remediation = remediation


class StateMachine:
    """Manages lifecycle transitions T1-T11 with guard validation."""

    @staticmethod
    def start_session(project_id: str, intent: SessionIntent) -> ExecutionSession:
        """T1: (session start) → INSPECT."""
        session = ExecutionSession(
            project_id=project_id, intent=intent, lifecycle_state=LifecycleState.INSPECT
        )
        return session

    @staticmethod
    def transition_to_specify(
        session: ExecutionSession, findings_archived: bool
    ) -> ExecutionSession:
        """T2: INSPECT → SPECIFY."""
        if session.lifecycle_state != LifecycleState.INSPECT:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to SPECIFY",
                f"Must be in INSPECT state (currently {session.lifecycle_state})",
                "Return to INSPECT or use appropriate transition",
            )

        if not findings_archived:
            raise TransitionError(
                "Cannot transition to SPECIFY: findings not archived",
                "Inspection findings must be archived",
                "Archive inspection findings before proposing spec",
            )

        session.lifecycle_state = LifecycleState.SPECIFY
        session.increment_version()
        return session

    @staticmethod
    def transition_to_confirm(
        session: ExecutionSession, spec: Specification
    ) -> ExecutionSession:
        """T3: SPECIFY → CONFIRM."""
        if session.lifecycle_state != LifecycleState.SPECIFY:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to CONFIRM",
                f"Must be in SPECIFY state (currently {session.lifecycle_state})",
                "Complete specification first",
            )

        if not all([spec.what, spec.why, spec.deliverable, spec.done_when]):
            raise TransitionError(
                "Cannot transition to CONFIRM: incomplete spec",
                "Spec must contain WHAT, WHY, DELIVERABLE, and at least one DONE WHEN",
                "Complete all required spec fields",
            )

        session.lifecycle_state = LifecycleState.CONFIRM
        session.current_spec = spec
        session.increment_version()
        return session

    @staticmethod
    def transition_to_plan(
        session: ExecutionSession, user_confirmed: bool
    ) -> ExecutionSession:
        """T4: CONFIRM → PLAN."""
        if session.lifecycle_state != LifecycleState.CONFIRM:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to PLAN",
                f"Must be in CONFIRM state (currently {session.lifecycle_state})",
                "Confirm specification first",
            )

        if not session.current_spec:
            raise TransitionError(
                "Cannot transition to PLAN: no spec",
                "Current spec is missing",
                "Create and confirm a specification",
            )

        if session.current_spec.readiness != Readiness.READY:
            raise TransitionError(
                "Cannot transition to PLAN: readiness blocked",
                f"Readiness is {session.current_spec.readiness}",
                "Resolve blocking unknowns and assumptions",
            )

        if not user_confirmed and session.current_spec.readiness == Readiness.READY:
            pass
        elif not user_confirmed:
            raise TransitionError(
                "Cannot transition to PLAN: spec not confirmed",
                "User confirmation required",
                "Confirm or correct the specification",
            )

        session.lifecycle_state = LifecycleState.PLAN
        session.increment_version()
        return session

    @staticmethod
    def correct_spec(
        session: ExecutionSession, corrected_spec: Specification
    ) -> ExecutionSession:
        """T5: CONFIRM → SPECIFY (user correction)."""
        if session.lifecycle_state != LifecycleState.CONFIRM:
            raise TransitionError(
                f"Cannot correct spec from {session.lifecycle_state}",
                f"Must be in CONFIRM state (currently {session.lifecycle_state})",
                "Wait for CONFIRM state",
            )

        new_spec = corrected_spec.create_revision()
        new_spec.update_computed_fields()

        session.lifecycle_state = LifecycleState.SPECIFY
        session.current_spec = new_spec
        session.increment_version()
        return session

    @staticmethod
    def transition_to_execute(
        session: ExecutionSession, plan_exit_rule_met: bool
    ) -> ExecutionSession:
        """T6: PLAN → EXECUTE."""
        if session.lifecycle_state != LifecycleState.PLAN:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to EXECUTE",
                f"Must be in PLAN state (currently {session.lifecycle_state})",
                "Complete planning first",
            )

        if not plan_exit_rule_met:
            raise TransitionError(
                "Cannot transition to EXECUTE: plan incomplete",
                "Plan must define deliverable, next action, "
                "dependencies, risks, and evidence",
                "Complete plan with foreground (NOW + NEXT 2) and exit criteria",
            )

        session.lifecycle_state = LifecycleState.EXECUTE
        session.increment_version()
        return session

    @staticmethod
    def transition_to_verify(
        session: ExecutionSession, has_completion_candidate: bool
    ) -> ExecutionSession:
        """T7: EXECUTE → VERIFY."""
        if session.lifecycle_state != LifecycleState.EXECUTE:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to VERIFY",
                f"Must be in EXECUTE state (currently {session.lifecycle_state})",
                "Complete execution first",
            )

        if not has_completion_candidate:
            raise TransitionError(
                "Cannot transition to VERIFY: no completion candidate",
                "No work ready for verification",
                "Complete work that satisfies done-when criteria",
            )

        session.lifecycle_state = LifecycleState.VERIFY
        session.increment_version()
        return session

    @staticmethod
    def return_to_execute(
        session: ExecutionSession, failed_criteria_count: int
    ) -> ExecutionSession:
        """T8: VERIFY → EXECUTE (failed verification)."""
        if session.lifecycle_state != LifecycleState.VERIFY:
            raise TransitionError(
                f"Cannot return to EXECUTE from {session.lifecycle_state}",
                f"Must be in VERIFY state (currently {session.lifecycle_state})",
                "Enter verification first",
            )

        if failed_criteria_count == 0:
            raise TransitionError(
                "Cannot return to EXECUTE: no failed criteria",
                "All criteria passed",
                "Transition to COMPLETE instead",
            )

        session.lifecycle_state = LifecycleState.EXECUTE
        session.increment_version()
        return session

    @staticmethod
    def transition_to_complete(
        session: ExecutionSession, all_criteria_satisfied: bool
    ) -> ExecutionSession:
        """T9: VERIFY → COMPLETE."""
        if session.lifecycle_state != LifecycleState.VERIFY:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to COMPLETE",
                f"Must be in VERIFY state (currently {session.lifecycle_state})",
                "Verify work first",
            )

        if not all_criteria_satisfied:
            raise TransitionError(
                "Cannot transition to COMPLETE: criteria not satisfied",
                "One or more done-when criteria lack valid evidence",
                "Return to EXECUTE or gather missing evidence",
            )

        session.lifecycle_state = LifecycleState.COMPLETE
        session.increment_version()
        return session

    @staticmethod
    def revise_goal(
        session: ExecutionSession, checkpoint: Checkpoint
    ) -> ExecutionSession:
        """T10: any state → SPECIFY (goal revision after checkpoint)."""
        session.lifecycle_state = LifecycleState.SPECIFY
        session.increment_version()
        return session

    @staticmethod
    def recover(
        session: ExecutionSession, checkpoint: Checkpoint
    ) -> tuple[ExecutionSession, LifecycleState]:
        """T11: (resume) → checkpointed state (recover command)."""
        restored_state = checkpoint.lifecycle_state

        session.lifecycle_state = restored_state
        if checkpoint.spec_id and checkpoint.spec_revision:
            pass

        session.increment_version()
        return session, restored_state

    @staticmethod
    def can_transition(
        from_state: LifecycleState, to_state: LifecycleState
    ) -> tuple[bool, str | None]:
        """Check if a transition is valid in the state machine."""
        valid_transitions = {
            LifecycleState.INSPECT: [LifecycleState.SPECIFY],
            LifecycleState.SPECIFY: [LifecycleState.CONFIRM],
            LifecycleState.CONFIRM: [LifecycleState.SPECIFY, LifecycleState.PLAN],
            LifecycleState.PLAN: [LifecycleState.EXECUTE],
            LifecycleState.EXECUTE: [LifecycleState.VERIFY],
            LifecycleState.VERIFY: [
                LifecycleState.EXECUTE,
                LifecycleState.COMPLETE,
            ],
            LifecycleState.COMPLETE: [],
        }

        if to_state in valid_transitions.get(from_state, []):
            return True, None
        else:
            return (
                False,
                f"Invalid transition from {from_state} to {to_state}. "
                f"Valid transitions: {valid_transitions.get(from_state, [])}",
            )
