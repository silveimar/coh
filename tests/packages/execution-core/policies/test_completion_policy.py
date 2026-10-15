"""Tests for I-03 completion policy: honest ceilings and criterion checks."""

from uuid import UUID, uuid4

from execution_core.domain.enums import (
    CompletionState,
    EvidenceAuthority,
    EvidenceResult,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.specification import DoneWhenCriterion
from execution_core.policies.completion_policy import CompletionPolicy


def _evidence(
    criterion_id: UUID,
    *,
    authority: EvidenceAuthority = EvidenceAuthority.TOOL_VERIFIED,
    result: EvidenceResult = EvidenceResult.PASS,
    evidence_type: str = "test",
    spec_revision: int = 1,
) -> Evidence:
    return Evidence(
        spec_id=uuid4(),
        spec_revision=spec_revision,
        criterion_id=criterion_id,
        evidence_type=evidence_type,
        authority=authority,
        result=result,
        summary="synthetic evidence",
        source="pytest",
    )


class TestComputeCompletionState:
    """I-03: without qualifying evidence the ceiling stays below DONE."""

    def test_no_criteria_caps_at_implemented(self) -> None:
        state, missing = CompletionPolicy.compute_completion_state([], [], 1)

        assert state == CompletionState.IMPLEMENTED
        assert missing == ["No done-when criteria defined"]

    def test_partial_test_evidence_caps_at_tested(self) -> None:
        covered = DoneWhenCriterion(text="Endpoint returns 200")
        uncovered = DoneWhenCriterion(text="Docs updated")
        evidence = [_evidence(covered.id, evidence_type="test")]

        state, missing = CompletionPolicy.compute_completion_state(
            [covered, uncovered], evidence, 1
        )

        assert state == CompletionState.TESTED
        assert missing == ["Criterion 'Docs updated' lacks evidence"]

    def test_non_qualifying_evidence_caps_at_implemented(self) -> None:
        criterion = DoneWhenCriterion(text="Endpoint returns 200")
        evidence = [
            _evidence(criterion.id, authority=EvidenceAuthority.AGENT_REPORTED),
        ]

        state, missing = CompletionPolicy.compute_completion_state(
            [criterion], evidence, 1
        )

        assert state == CompletionState.IMPLEMENTED
        assert missing == ["Criterion 'Endpoint returns 200' lacks evidence"]

    def test_evidence_for_unknown_criterion_is_ignored(self) -> None:
        criterion = DoneWhenCriterion(text="Endpoint returns 200")
        evidence = [_evidence(uuid4())]

        state, missing = CompletionPolicy.compute_completion_state(
            [criterion], evidence, 1
        )

        assert state == CompletionState.IMPLEMENTED
        assert len(missing) == 1


class TestMarkEvidenceStale:
    """Evidence from an older revision is marked stale; current stays fresh."""

    def test_only_old_revision_evidence_is_marked_stale(self) -> None:
        criterion_id = uuid4()
        old = _evidence(criterion_id, spec_revision=1)
        current = _evidence(criterion_id, spec_revision=2)

        result = CompletionPolicy.mark_evidence_stale([old, current], 2)

        assert result == [old, current]
        assert old.stale
        assert not current.stale


class TestCheckCriterionSatisfied:
    """Each unsatisfied criterion reports the reason it is unsatisfied."""

    def test_satisfied_by_fresh_qualifying_evidence(self) -> None:
        criterion_id = uuid4()

        satisfied, reasons = CompletionPolicy.check_criterion_satisfied(
            criterion_id, [_evidence(criterion_id)], 1
        )

        assert satisfied
        assert reasons == []

    def test_no_evidence_recorded(self) -> None:
        satisfied, reasons = CompletionPolicy.check_criterion_satisfied(
            uuid4(), [_evidence(uuid4())], 1
        )

        assert not satisfied
        assert reasons == ["No evidence recorded"]

    def test_all_evidence_stale(self) -> None:
        criterion_id = uuid4()

        satisfied, reasons = CompletionPolicy.check_criterion_satisfied(
            criterion_id, [_evidence(criterion_id, spec_revision=1)], 2
        )

        assert not satisfied
        assert reasons == ["All evidence is stale"]

    def test_failed_or_inconclusive_evidence(self) -> None:
        criterion_id = uuid4()
        evidence = [
            _evidence(criterion_id, result=EvidenceResult.FAIL),
            _evidence(criterion_id, result=EvidenceResult.INCONCLUSIVE),
        ]

        satisfied, reasons = CompletionPolicy.check_criterion_satisfied(
            criterion_id, evidence, 1
        )

        assert not satisfied
        assert reasons == ["2 evidence item(s) failed or inconclusive"]

    def test_passing_evidence_without_authority(self) -> None:
        criterion_id = uuid4()
        evidence = [
            _evidence(criterion_id, authority=EvidenceAuthority.AGENT_REPORTED),
        ]

        satisfied, reasons = CompletionPolicy.check_criterion_satisfied(
            criterion_id, evidence, 1
        )

        assert not satisfied
        assert reasons == ["Evidence lacks sufficient authority"]
