"""Readiness policy enforcing I-02 (readiness gate)."""

from ..domain.enums import Readiness
from ..domain.session import ExecutionSession


class ReadinessViolation(Exception):
    """Raised when attempting material mutation while blocked."""

    def __init__(self, message: str):
        super().__init__(message)


class ReadinessPolicy:
    """Enforces I-02: no material mutation while readiness = Blocked."""

    @staticmethod
    def check_mutation_allowed(session: ExecutionSession) -> tuple[bool, str]:
        """Check if material mutations are allowed based on readiness."""
        if not session.current_spec:
            return False, "No specification exists"

        if session.current_spec.readiness == Readiness.BLOCKED:
            blockers = ReadinessPolicy._get_blockers(session)
            return False, f"Readiness is BLOCKED. Blockers: {', '.join(blockers)}"

        return True, "Mutation allowed"

    @staticmethod
    def require_ready_for_mutation(session: ExecutionSession) -> None:
        """Raise exception if mutation is not allowed."""
        allowed, reason = ReadinessPolicy.check_mutation_allowed(session)
        if not allowed:
            raise ReadinessViolation(
                f"Material mutation rejected: {reason}. "
                "Read-only inspection remains permitted."
            )

    @staticmethod
    def _get_blockers(session: ExecutionSession) -> list[str]:
        """Get list of reasons why readiness is blocked."""
        if not session.current_spec:
            return ["No specification"]

        spec = session.current_spec
        blockers = []

        if not spec.what:
            blockers.append("Missing WHAT")
        if not spec.why:
            blockers.append("Missing WHY")
        if not spec.deliverable:
            blockers.append("Missing DELIVERABLE")
        if not spec.done_when:
            blockers.append("Missing DONE WHEN criteria")

        blocking_unknowns = [u for u in spec.unknowns if u.blocking and not u.resolved]
        if blocking_unknowns:
            blockers.append(f"{len(blocking_unknowns)} blocking unknown(s)")

        blocking_assumptions = [
            a
            for a in spec.assumptions
            if a.classification.value == "blocking" and not a.resolved
        ]
        if blocking_assumptions:
            blockers.append(f"{len(blocking_assumptions)} blocking assumption(s)")

        unconfirmed_material = [
            a
            for a in spec.assumptions
            if a.classification.value == "material"
            and a.requires_confirmation
            and not a.resolved
        ]
        if unconfirmed_material:
            blockers.append(
                f"{len(unconfirmed_material)} unconfirmed material assumption(s)"
            )

        return blockers
