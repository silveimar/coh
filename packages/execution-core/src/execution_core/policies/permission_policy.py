"""Permission policy enforcing I-08 (permission matrix)."""

from ..domain.enums import LifecycleState, Readiness
from ..domain.session import ExecutionSession


class PermissionDenied(Exception):
    """Raised when an action requires explicit confirmation."""

    def __init__(self, message: str, required_permission: str):
        super().__init__(message)
        self.required_permission = required_permission


class PermissionPolicy:
    """Enforces I-08: inspection/spec/plan automatic; changes need confirmation."""

    @staticmethod
    def check_inspection_allowed(session: ExecutionSession) -> bool:
        """Inspection/analysis always automatic (I-08)."""
        return True

    @staticmethod
    def check_spec_proposal_allowed(session: ExecutionSession) -> bool:
        """Spec proposal automatic after inspection (I-08)."""
        return session.lifecycle_state in [
            LifecycleState.INSPECT,
            LifecycleState.SPECIFY,
        ]

    @staticmethod
    def check_plan_allowed(session: ExecutionSession) -> bool:
        """Planning automatic after confirmed spec (I-08)."""
        return session.lifecycle_state in [
            LifecycleState.CONFIRM,
            LifecycleState.PLAN,
        ] and (
            session.current_spec is not None
            and session.current_spec.readiness == Readiness.READY
        )

    @staticmethod
    def check_small_bounded_change_allowed(
        session: ExecutionSession, change_scope: str, confirmed: bool
    ) -> tuple[bool, str]:
        """Small bounded changes automatic after spec confirmation (I-08)."""
        if session.lifecycle_state not in [
            LifecycleState.EXECUTE,
            LifecycleState.VERIFY,
        ]:
            return False, "Not in execution phase"

        if not session.current_spec or not session.current_spec.confirmed_at:
            return False, "Spec not confirmed"

        if change_scope in ["large", "destructive", "expanding"] and not confirmed:
            return False, f"Explicit confirmation required for {change_scope} change"

        return True, ""

    @staticmethod
    def require_confirmation_for_large_change(
        change_scope: str, confirmed: bool
    ) -> None:
        """Enforce I-08: large/destructive/expanding needs explicit confirmation."""
        if change_scope in ["large", "destructive", "expanding"] and not confirmed:
            raise PermissionDenied(
                f"Cannot proceed with {change_scope} change without confirmation",
                f"explicit_confirmation_{change_scope}",
            )

    @staticmethod
    def check_spec_confirmation_belongs_to_user(user_confirmed: bool) -> bool:
        """Enforce I-08: spec confirmation always belongs to user."""
        return user_confirmed

    @staticmethod
    def check_tests_allowed(granted_permissions: list[str]) -> bool:
        """Tests/verification automatic under granted permissions (I-08)."""
        return (
            "run_tests" in granted_permissions or "verification" in granted_permissions
        )

    @staticmethod
    def classify_change_scope(
        files_affected: int, destructive_ops: bool, outside_spec: bool
    ) -> str:
        """Classify change scope for permission check."""
        if destructive_ops:
            return "destructive"
        if outside_spec:
            return "expanding"
        if files_affected > 10:
            return "large"
        return "small"
