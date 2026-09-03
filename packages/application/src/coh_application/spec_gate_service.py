"""Specification gate service enforcing I-02 (readiness-based mutation control)."""

from typing import Literal
from uuid import UUID

from execution_core.domain.enums import Readiness
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import (
    Assumption,
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from persistence.ports.state_store import UnitOfWork


class SpecGateService:
    """Spec gate service implementing I-02: no material mutation while Blocked."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def propose_spec(
        self,
        session_id: UUID,
        what: str,
        why: str,
        deliverable: str,
        done_when: list[str],
        constraints: list[str] | None = None,
        non_goals: list[str] | None = None,
        assumptions: list[dict[str, str]] | None = None,
        unknowns: list[dict[str, bool | str]] | None = None,
    ) -> Specification:
        """
        Propose a specification after inspection.

        Required fields: what, why, deliverable, ≥1 done_when.
        Returns computed clarity level and binary readiness.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        done_when_criteria = [
            DoneWhenCriterion(text=criterion) for criterion in done_when
        ]

        assumption_objects = []
        if assumptions:
            for a in assumptions:
                assumption_objects.append(
                    Assumption(
                        text=a["text"],
                        classification=a["classification"],
                        rationale=a.get("rationale"),
                        requires_confirmation=a.get("requires_confirmation", False),
                    )
                )

        unknown_objects = []
        if unknowns:
            for u in unknowns:
                unknown_objects.append(
                    Unknown(
                        text=u["text"],
                        blocking=u.get("blocking", False),
                        discoverable_via_inspection=u.get(
                            "discoverable_via_inspection", True
                        ),
                    )
                )

        spec = Specification(
            what=what,
            why=why,
            deliverable=deliverable,
            done_when=done_when_criteria,
            constraints=constraints or [],
            non_goals=non_goals or [],
            assumptions=assumption_objects,
            unknowns=unknown_objects,
        )

        spec.update_computed_fields()

        return spec

    def confirm_spec(self, session_id: UUID, spec: Specification) -> Specification:
        """
        Confirm specification and persist it (T4).

        Raises ReadinessViolation if spec is not Ready.
        Updates session.current_spec and persists.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        spec.update_computed_fields()

        if spec.readiness != Readiness.READY:
            blockers = self._get_readiness_blockers(spec)
            raise ValueError(
                f"Cannot confirm spec with readiness=BLOCKED. "
                f"Blockers: {', '.join(blockers)}"
            )

        session.current_spec = spec
        session.increment_version()

        self.uow.specifications.add(spec)
        self.uow.sessions.update(session, expected_version=session.version - 1)
        self.uow.commit()

        return spec

    def revise_spec(
        self,
        session_id: UUID,
        spec_id: UUID,
        updates: dict[str, str | list[str]],
    ) -> Specification:
        """
        Revise specification fields (T5).

        Creates new revision with incremented revision number.
        Recomputes clarity and readiness.
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        spec = self.uow.specifications.get(spec_id)
        if not spec:
            raise ValueError(f"Specification {spec_id} not found")

        new_spec = spec.create_revision()

        for key, value in updates.items():
            if hasattr(new_spec, key):
                setattr(new_spec, key, value)

        new_spec.update_computed_fields()

        session.current_spec = new_spec
        session.increment_version()

        self.uow.specifications.add(new_spec)
        self.uow.sessions.update(session, expected_version=session.version - 1)
        self.uow.commit()

        return new_spec

    def check_mutation_allowed(
        self, session_id: UUID
    ) -> tuple[bool, Literal["ready", "blocked"], list[str]]:
        """
        Check if material mutation is allowed (I-02 enforcement).

        Returns: (allowed, readiness_state, blockers)
        - allowed=True if readiness=READY
        - allowed=False if readiness=BLOCKED, with blocker reasons
        - Read-only inspection always permitted
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            return False, "blocked", [f"Session {session_id} not found"]

        spec = self._load_current_spec(session)
        if not spec:
            return False, "blocked", ["No specification exists"]

        if spec.readiness == Readiness.BLOCKED:
            blockers = self._get_readiness_blockers(spec)
            return False, "blocked", blockers

        return True, "ready", []

    def require_ready_for_mutation(self, session_id: UUID) -> None:
        """
        Raise exception if material mutation is not allowed (I-02 gate).

        Used by planning/execution services before mutations.
        """
        allowed, state, blockers = self.check_mutation_allowed(session_id)
        if not allowed:
            raise PermissionError(
                f"Material mutation rejected: readiness is {state.upper()}. "
                f"Blockers: {', '.join(blockers)}. "
                f"Read-only inspection remains permitted."
            )

    def get_spec_status(self, session_id: UUID) -> dict[str, str | list[str]]:
        """
        Get specification status for read-only inspection.

        Always permitted regardless of readiness (I-02).
        """
        session = self.uow.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        spec = self._load_current_spec(session)
        if not spec:
            return {"clarity": "none", "readiness": "blocked", "blockers": []}

        blockers = self._get_readiness_blockers(spec)

        return {
            "spec_id": str(spec.id),
            "revision": str(spec.revision),
            "clarity": spec.clarity.value,
            "readiness": spec.readiness.value,
            "blockers": blockers,
            "what": spec.what,
            "why": spec.why,
            "deliverable": spec.deliverable,
            "done_when_count": len(spec.done_when),
        }

    def get_questions(
        self, spec: Specification
    ) -> dict[str, list[dict[str, str | bool]]]:
        """
        Generate grouped, minimal questions with recommended defaults.

        Groups: blocking_unknowns, material_assumptions.
        Each question has: text, blocking, recommended_default (if practical).
        """
        questions = {"blocking_unknowns": [], "material_assumptions": []}

        blocking_unknowns = [u for u in spec.unknowns if u.blocking and not u.resolved]
        for unknown in blocking_unknowns:
            questions["blocking_unknowns"].append(
                {
                    "id": str(unknown.id),
                    "text": unknown.text,
                    "blocking": True,
                    "discoverable": unknown.discoverable_via_inspection,
                }
            )

        material_assumptions = [
            a
            for a in spec.assumptions
            if a.classification.value == "material"
            and a.requires_confirmation
            and not a.resolved
        ]
        for assumption in material_assumptions:
            questions["material_assumptions"].append(
                {
                    "id": str(assumption.id),
                    "text": assumption.text,
                    "rationale": assumption.rationale or "",
                    "recommended_default": "confirm",
                }
            )

        return questions

    def _load_current_spec(self, session: ExecutionSession) -> Specification | None:
        """Load the current spec for a session by its stored spec ID."""
        if not session.current_spec:
            from sqlalchemy import select

            from persistence.infrastructure.models import ExecutionSessionModel

            if hasattr(self.uow, "_session") and self.uow._session:
                stmt = select(ExecutionSessionModel).where(
                    ExecutionSessionModel.id == session.id
                )
                model = self.uow._session.scalar(stmt)
                if model and model.current_spec_id:
                    return self.uow.specifications.get(model.current_spec_id)
        return session.current_spec

    def _get_readiness_blockers(self, spec: Specification) -> list[str]:
        """Get list of reasons why readiness is blocked."""
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
            for unknown in blocking_unknowns:
                blocker_text = f"Unknown: {unknown.text}"
                # Provide recommended default if not set
                default_recommendation = (
                    "Resolve before proceeding (inspection or clarification required)"
                )
                recommended = unknown.recommended_default or default_recommendation
                blocker_text += f" (recommended: {recommended})"
                blockers.append(blocker_text)

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
