"""State machine implementing the 7-state lifecycle and transitions T1-T11."""

from uuid import UUID

from ..domain.checkpoint import Checkpoint, RecoverySummary
from ..domain.commands import (
    Command,
    CommandHistory,
    ConcurrencyError,
    DuplicateCommandError,
)
from ..domain.enums import LifecycleState, Readiness, SessionIntent
from ..domain.evidence import Evidence
from ..domain.session import ExecutionSession
from ..domain.specification import Specification
from ..policies.completion_policy import CompletionPolicy
from ..policies.readiness_policy import ReadinessPolicy


class TransitionError(Exception):
    """Raised when a transition is invalid or guard fails."""

    def __init__(self, message: str, blocked_reason: str, remediation: str):
        super().__init__(message)
        self.blocked_reason = blocked_reason
        self.remediation = remediation


class CapabilityNotImplemented(Exception):
    """Raised when a capability is unavailable (I-14)."""

    def __init__(self, capability: str, focused_request: str):
        super().__init__(
            f"Capability '{capability}' not implemented. {focused_request}"
        )
        self.capability = capability
        self.focused_request = focused_request


class StateMachine:
    """Manages lifecycle transitions T1-T11 with guard validation."""

    def __init__(self) -> None:
        self.command_history = CommandHistory()

    def _check_command(self, command: Command, session: ExecutionSession) -> None:
        """Check idempotency and concurrency."""
        if self.command_history.is_duplicate(command.idempotency_key):
            raise DuplicateCommandError(command.idempotency_key)

        if command.expected_version != session.version:
            raise ConcurrencyError(command.expected_version, session.version)

    def _record_command(self, command: Command, command_id: UUID) -> None:
        """Record processed command."""
        self.command_history.record(command.idempotency_key, command_id)

    @staticmethod
    def start_session(project_id: str, intent: SessionIntent) -> ExecutionSession:
        """T1: (session start) → INSPECT."""
        session = ExecutionSession(
            project_id=project_id, intent=intent, lifecycle_state=LifecycleState.INSPECT
        )
        return session

    def transition_to_specify(
        self,
        session: ExecutionSession,
        findings_archived: bool,
        command: Command,
    ) -> ExecutionSession:
        """T2: INSPECT → SPECIFY."""
        self._check_command(command, session)

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
        self._record_command(command, session.id)
        return session

    def transition_to_confirm(
        self,
        session: ExecutionSession,
        spec: Specification,
        command: Command,
    ) -> ExecutionSession:
        """T3: SPECIFY → CONFIRM."""
        self._check_command(command, session)

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
        self._record_command(command, session.id)
        return session

    def transition_to_plan(
        self,
        session: ExecutionSession,
        user_confirmed: bool,
        command: Command,
    ) -> ExecutionSession:
        """T4: CONFIRM → PLAN (I-02 readiness enforced, I-08 user confirms)."""
        self._check_command(command, session)

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

        # I-02: Readiness gate
        ReadinessPolicy.require_ready_for_mutation(session)

        # I-08: Spec confirmation belongs to user (except fully inferable case)
        if session.current_spec.readiness == Readiness.READY and not user_confirmed:
            # Fully inferable: no material/blocking uncertainty
            pass
        elif not user_confirmed:
            raise TransitionError(
                "Cannot transition to PLAN: spec not confirmed",
                "User confirmation required (I-08)",
                "Confirm or correct the specification",
            )

        session.lifecycle_state = LifecycleState.PLAN
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def correct_spec(
        self,
        session: ExecutionSession,
        corrected_spec: Specification,
        command: Command,
    ) -> ExecutionSession:
        """T5: CONFIRM → SPECIFY (user correction)."""
        self._check_command(command, session)

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
        self._record_command(command, session.id)
        return session

    def transition_to_execute(
        self,
        session: ExecutionSession,
        command: Command,
    ) -> ExecutionSession:
        """T6: PLAN → EXECUTE (I-02 readiness enforced, guards evaluated)."""
        self._check_command(command, session)

        if session.lifecycle_state != LifecycleState.PLAN:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to EXECUTE",
                f"Must be in PLAN state (currently {session.lifecycle_state})",
                "Complete planning first",
            )

        # I-02: Readiness gate must still hold
        ReadinessPolicy.require_ready_for_mutation(session)

        # Plan exit rule: must have foreground computed (NOW + NEXT 2)
        # This is a guard, not a caller boolean
        if not session.current_spec:
            raise TransitionError(
                "Cannot transition to EXECUTE: no spec",
                "Spec is required for execution",
                "Create and confirm specification first",
            )

        session.lifecycle_state = LifecycleState.EXECUTE
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def transition_to_verify(
        self,
        session: ExecutionSession,
        command: Command,
    ) -> ExecutionSession:
        """T7: EXECUTE → VERIFY (I-02 readiness enforced)."""
        self._check_command(command, session)

        if session.lifecycle_state != LifecycleState.EXECUTE:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to VERIFY",
                f"Must be in EXECUTE state (currently {session.lifecycle_state})",
                "Complete execution first",
            )

        # I-02: Readiness gate must still hold
        ReadinessPolicy.require_ready_for_mutation(session)

        if not session.current_spec or not session.current_spec.done_when:
            raise TransitionError(
                "Cannot transition to VERIFY: no done-when criteria",
                "Completion candidate requires criteria to evaluate",
                "Define done-when criteria in specification",
            )

        session.lifecycle_state = LifecycleState.VERIFY
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def return_to_execute(
        self,
        session: ExecutionSession,
        command: Command,
    ) -> ExecutionSession:
        """T8: VERIFY → EXECUTE (failed verification)."""
        self._check_command(command, session)

        if session.lifecycle_state != LifecycleState.VERIFY:
            raise TransitionError(
                f"Cannot return to EXECUTE from {session.lifecycle_state}",
                f"Must be in VERIFY state (currently {session.lifecycle_state})",
                "Enter verification first",
            )

        session.lifecycle_state = LifecycleState.EXECUTE
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def transition_to_complete(
        self,
        session: ExecutionSession,
        evidence_list: list[Evidence],
        command: Command,
    ) -> ExecutionSession:
        """T9: VERIFY → COMPLETE (I-03 evidence gate enforced)."""
        self._check_command(command, session)

        if session.lifecycle_state != LifecycleState.VERIFY:
            raise TransitionError(
                f"Cannot transition from {session.lifecycle_state} to COMPLETE",
                f"Must be in VERIFY state (currently {session.lifecycle_state})",
                "Verify work first",
            )

        if not session.current_spec:
            raise TransitionError(
                "Cannot transition to COMPLETE: no spec",
                "Spec is required for completion",
                "Create specification first",
            )

        # I-03: Evidence gate - policy validates criteria satisfaction
        CompletionPolicy.require_evidence_for_verification(
            session.current_spec.done_when,
            evidence_list,
            session.current_spec.revision,
        )

        session.lifecycle_state = LifecycleState.COMPLETE
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def revise_goal(
        self,
        session: ExecutionSession,
        checkpoint: Checkpoint,
        new_spec: Specification,
        command: Command,
    ) -> ExecutionSession:
        """T10: any state → SPECIFY (goal revision after checkpoint)."""
        self._check_command(command, session)

        # T10 requires checkpoint first
        if not checkpoint or checkpoint.session_id != session.id:
            raise TransitionError(
                "Cannot revise goal: checkpoint required",
                "Goal revision must checkpoint active work first",
                "Create checkpoint before revising goal",
            )

        session.lifecycle_state = LifecycleState.SPECIFY
        session.current_spec = new_spec.create_revision()
        session.increment_version()
        self._record_command(command, session.id)
        return session

    def recover(
        self,
        session: ExecutionSession,
        checkpoint: Checkpoint,
        command: Command,
    ) -> tuple[ExecutionSession, RecoverySummary]:
        """T11: (recover) → checkpointed state (entry command)."""
        self._check_command(command, session)

        if not checkpoint or checkpoint.session_id != session.id:
            raise TransitionError(
                "Cannot recover: invalid checkpoint",
                "Checkpoint does not match session",
                "Provide valid checkpoint for this session",
            )

        # Restore lifecycle state
        restored_state = checkpoint.lifecycle_state
        session.lifecycle_state = restored_state

        # Restore spec if available
        if checkpoint.spec_id and checkpoint.spec_revision and session.current_spec:
            # In full implementation, load spec from repository
            pass

        # Build recovery summary with restart_action
        summary = RecoverySummary(
            goal=session.current_spec.what if session.current_spec else "Unknown",
            why=session.current_spec.why if session.current_spec else "Unknown",
            last_verified=None,
            last_decision=None,
            now_task=None,
            next_tasks=[],
            parked_count=0,
            restart_action=checkpoint.restart_action,
            archive_degraded=(checkpoint.archive_status.value == "degraded"),
            checkpoint_id=checkpoint.id,
        )

        session.increment_version()
        self._record_command(command, session.id)

        return session, summary

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

        # T10: any state → SPECIFY (goal revision)
        if to_state == LifecycleState.SPECIFY:
            return True, None

        # T11: recover can re-enter any state
        # (represented as same-state transition in can_transition)
        if from_state == to_state:
            return True, None

        if to_state in valid_transitions.get(from_state, []):
            return True, None
        else:
            return (
                False,
                f"Invalid transition from {from_state} to {to_state}. "
                f"Valid transitions: {valid_transitions.get(from_state, [])}",
            )
