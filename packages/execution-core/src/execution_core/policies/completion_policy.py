"""Completion policy enforcing I-03 (evidence gate)."""

from uuid import UUID

from ..domain.enums import CompletionState, EvidenceResult
from ..domain.evidence import Evidence
from ..domain.specification import DoneWhenCriterion


class CompletionViolation(Exception):
    """Raised when attempting to claim verification/done without evidence."""

    def __init__(self, message: str, missing_criteria: list[str]):
        super().__init__(message)
        self.missing_criteria = missing_criteria


class CompletionPolicy:
    """Enforces I-03: evidence gate for verification and completion."""

    @staticmethod
    def compute_completion_state(
        criteria: list[DoneWhenCriterion],
        evidence_list: list[Evidence],
        spec_revision: int,
    ) -> tuple[CompletionState, list[str]]:
        """Compute completion state based on evidence satisfaction."""
        if not criteria:
            return CompletionState.IMPLEMENTED, ["No done-when criteria defined"]

        criterion_map = {c.id: c for c in criteria}
        evidence_by_criterion: dict[UUID, list[Evidence]] = {}

        for ev in evidence_list:
            if ev.criterion_id in criterion_map:
                if ev.criterion_id not in evidence_by_criterion:
                    evidence_by_criterion[ev.criterion_id] = []
                evidence_by_criterion[ev.criterion_id].append(ev)

        missing_evidence = []
        has_test_results = False
        all_satisfied = True

        for criterion in criteria:
            evidences = evidence_by_criterion.get(criterion.id, [])
            fresh_evidences = [
                e for e in evidences if e.is_fresh_for_revision(spec_revision)
            ]

            satisfying = [e for e in fresh_evidences if e.can_satisfy_criterion()]

            if not satisfying:
                all_satisfied = False
                missing_evidence.append(f"Criterion '{criterion.text}' lacks evidence")
            else:
                for e in fresh_evidences:
                    if e.evidence_type in ["test", "build"]:
                        has_test_results = True

        if all_satisfied:
            return CompletionState.DONE, []
        elif has_test_results or any(evidence_list):
            if has_test_results:
                return CompletionState.TESTED, missing_evidence
            else:
                return CompletionState.VERIFIED, missing_evidence
        else:
            return CompletionState.IMPLEMENTED, missing_evidence

    @staticmethod
    def require_evidence_for_verification(
        criteria: list[DoneWhenCriterion],
        evidence_list: list[Evidence],
        spec_revision: int,
    ) -> None:
        """Enforce I-03: reject VERIFIED/DONE without evidence."""
        state, missing = CompletionPolicy.compute_completion_state(
            criteria, evidence_list, spec_revision
        )

        if state in [CompletionState.IMPLEMENTED, CompletionState.TESTED] and missing:
            raise CompletionViolation(
                f"Cannot claim VERIFIED or DONE: {len(missing)} criteria lack evidence. "
                f"Honest ceiling: {state.value}",
                missing,
            )

    @staticmethod
    def mark_evidence_stale(
        evidence_list: list[Evidence], current_revision: int
    ) -> list[Evidence]:
        """Mark evidence as stale when spec/implementation revision changes."""
        for ev in evidence_list:
            if not ev.is_fresh_for_revision(current_revision):
                ev.mark_stale()
        return evidence_list

    @staticmethod
    def check_criterion_satisfied(
        criterion_id: UUID, evidence_list: list[Evidence], spec_revision: int
    ) -> tuple[bool, list[str]]:
        """Check if a specific criterion is satisfied by evidence."""
        relevant = [e for e in evidence_list if e.criterion_id == criterion_id]
        fresh = [e for e in relevant if e.is_fresh_for_revision(spec_revision)]
        satisfying = [e for e in fresh if e.can_satisfy_criterion()]

        if satisfying:
            return True, []
        else:
            reasons = []
            if not relevant:
                reasons.append("No evidence recorded")
            elif not fresh:
                reasons.append("All evidence is stale")
            else:
                failing = [
                    e
                    for e in fresh
                    if e.result in [EvidenceResult.FAIL, EvidenceResult.INCONCLUSIVE]
                ]
                if failing:
                    reasons.append(
                        f"{len(failing)} evidence item(s) failed or inconclusive"
                    )
                else:
                    reasons.append("Evidence lacks sufficient authority")

            return False, reasons
