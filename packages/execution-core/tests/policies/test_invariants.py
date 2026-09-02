"""Tests for policies enforcing invariants I-01 through I-14."""

from uuid import uuid4

import pytest

from execution_core.domain.enums import (
    ActivationFriction,
    EnergyLevel,
    EvidenceAuthority,
    EvidenceResult,
    RelevanceLevel,
    SessionIntent,
    TaskStatus,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.domain.task import Task, TaskDependency
from execution_core.policies.completion_policy import (
    CompletionPolicy,
    CompletionViolation,
)
from execution_core.policies.foreground_policy import (
    ForegroundPolicy,
)
from execution_core.policies.integrity_policy import (
    ArchivePolicy,
    LanguagePolicy,
    ProposalPolicy,
    UntrustedContentPolicy,
)
from execution_core.policies.parking_policy import (
    ParkingPolicy,
    ProgressPolicy,
)
from execution_core.policies.permission_policy import (
    PermissionDenied,
    PermissionPolicy,
)
from execution_core.policies.readiness_policy import (
    ReadinessPolicy,
    ReadinessViolation,
)


class TestReadinessPolicy:
    """Test I-02: no material mutation while readiness = Blocked."""

    def test_mutation_blocked_when_spec_not_ready(self):
        """I-02: Material mutation rejected when readiness is blocked."""
        session = ExecutionSession(project_id="test", intent=SessionIntent.EXECUTE)
        spec = Specification(what="", why="", deliverable="", done_when=[])
        spec.update_computed_fields()
        session.current_spec = spec

        with pytest.raises(ReadinessViolation):
            ReadinessPolicy.require_ready_for_mutation(session)

    def test_mutation_allowed_when_ready(self):
        """I-02: Mutation allowed when readiness is ready."""
        session = ExecutionSession(project_id="test", intent=SessionIntent.EXECUTE)
        spec = Specification(
            what="Add feature",
            why="User needs it",
            deliverable="Feature",
            done_when=[DoneWhenCriterion(text="Works")],
        )
        spec.update_computed_fields()
        session.current_spec = spec

        ReadinessPolicy.require_ready_for_mutation(session)


class TestForegroundPolicy:
    """Test I-01: foreground with NOW + NEXT 2 and required metadata."""

    def test_foreground_enforces_one_now_two_next(self):
        """I-01: At most one NOW and two NEXT tasks."""
        session_id = uuid4()
        spec_id = uuid4()

        tasks = [
            Task(
                spec_id=spec_id,
                spec_revision=1,
                action_literal=f"Task {i}",
                done_when_condition="Done",
                estimated_minutes=10,
                energy=EnergyLevel.MEDIUM,
                activation_friction=ActivationFriction.LOW,
                status=TaskStatus.PLANNED,
                goal_leverage=0.5 - i * 0.1,
            )
            for i in range(5)
        ]

        foreground = ForegroundPolicy.calculate_foreground(
            session_id, "Test goal", tasks, 0
        )

        assert foreground.now_task is not None
        assert foreground.next_1_task is not None
        assert foreground.next_2_task is not None
        assert foreground.background_count == 2

    def test_now_task_requires_all_metadata(self):
        """I-01: NOW task must have all required metadata."""
        session_id = uuid4()
        spec_id = uuid4()

        task_missing_metadata = Task(
            spec_id=spec_id,
            spec_revision=1,
            action_literal=None,
            done_when_condition="Done",
            estimated_minutes=None,
            energy=None,
            activation_friction=None,
            status=TaskStatus.PLANNED,
        )

        foreground = ForegroundPolicy.calculate_foreground(
            session_id, "Test goal", [task_missing_metadata], 0
        )

        assert foreground.now_task is None

    def test_now_cannot_have_unresolved_dependencies(self):
        """I-01: Task with unresolved dependencies cannot be NOW."""
        session_id = uuid4()
        spec_id = uuid4()

        dep_task = Task(
            id=uuid4(),
            spec_id=spec_id,
            spec_revision=1,
            status=TaskStatus.PLANNED,
        )

        dependent_task = Task(
            spec_id=spec_id,
            spec_revision=1,
            action_literal="Dependent action",
            done_when_condition="Done",
            estimated_minutes=10,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            status=TaskStatus.PLANNED,
            dependencies=[TaskDependency(task_id=dep_task.id)],
        )

        foreground = ForegroundPolicy.calculate_foreground(
            session_id, "Test goal", [dep_task, dependent_task], 0
        )

        assert foreground.now_task is None


class TestCompletionPolicy:
    """Test I-03: evidence gate for verification and done."""

    def test_cannot_claim_done_without_evidence(self):
        """I-03: Cannot report DONE without criterion-linked evidence."""
        criteria = [
            DoneWhenCriterion(id=uuid4(), text="Feature works"),
            DoneWhenCriterion(id=uuid4(), text="Tests pass"),
        ]

        with pytest.raises(CompletionViolation) as exc:
            CompletionPolicy.require_evidence_for_verification(criteria, [], 1)

        assert "lack evidence" in str(exc.value)

    def test_done_allowed_with_tool_verified_evidence(self):
        """I-03: DONE allowed with tool_verified evidence."""
        criterion = DoneWhenCriterion(id=uuid4(), text="Tests pass")
        spec_id = uuid4()

        evidence = Evidence(
            spec_id=spec_id,
            spec_revision=1,
            criterion_id=criterion.id,
            evidence_type="test",
            authority=EvidenceAuthority.TOOL_VERIFIED,
            result=EvidenceResult.PASS,
            summary="All tests passed",
            source="pytest",
        )

        state, missing = CompletionPolicy.compute_completion_state(
            [criterion], [evidence], 1
        )

        assert state.value == "done"
        assert len(missing) == 0


class TestParkingPolicy:
    """Test I-10: parking preserves focus, I-05: progress before switch."""

    def test_auto_park_low_relevance_non_blocking(self):
        """I-10: Auto-park low relevance, non-blocking items."""
        assert ParkingPolicy.should_auto_park(RelevanceLevel.LOW, False)

    def test_no_auto_park_high_relevance(self):
        """I-10: High relevance items not auto-parked."""
        assert not ParkingPolicy.should_auto_park(RelevanceLevel.HIGH, False)

    def test_require_progress_before_switch(self):
        """I-05: Unfinished task requires progress record before switch."""
        task = Task(
            id=uuid4(), spec_id=uuid4(), spec_revision=1, status=TaskStatus.IN_PROGRESS
        )

        with pytest.raises(ValueError) as exc:
            ProgressPolicy.require_progress_before_switch(task, None)

        assert "progress record required" in str(exc.value)


class TestPermissionPolicy:
    """Test I-08: permission matrix."""

    def test_inspection_always_allowed(self):
        """I-08: Inspection/analysis always automatic."""
        session = ExecutionSession(project_id="test", intent=SessionIntent.EXECUTE)

        assert PermissionPolicy.check_inspection_allowed(session)

    def test_large_change_requires_confirmation(self):
        """I-08: Large changes require explicit confirmation."""
        with pytest.raises(PermissionDenied):
            PermissionPolicy.require_confirmation_for_large_change("large", False)


class TestArchivePolicy:
    """Test I-04: append-only archive, I-12: degrade-and-continue."""

    def test_append_only_prevents_overwrite(self):
        """I-04: Archive entries cannot be overwritten."""
        valid, msg = ArchivePolicy.validate_append_only(
            "write", entry_exists=True, is_overwrite=True
        )

        assert not valid
        assert "cannot overwrite" in msg

    def test_append_only_allows_new_entry(self):
        """I-04: New archive entries allowed."""
        valid, msg = ArchivePolicy.validate_append_only(
            "write", entry_exists=False, is_overwrite=False
        )

        assert valid

    def test_write_failure_degrades_gracefully(self):
        """I-12: Archive failure degrades without blocking."""
        event, metadata = ArchivePolicy.handle_write_failure(
            "entry content", "disk full"
        )

        assert event == "archive_write_failed"
        assert metadata["in_memory_preserved"] == "true"


class TestProposalPolicy:
    """Test I-06: LLM output is proposal-only."""

    def test_invalid_proposal_rejected(self):
        """I-06: Invalid LLM proposal does not mutate state."""
        valid, violations = ProposalPolicy.validate_proposal_before_mutation(
            {}, schema_valid=False, policy_valid=True
        )

        assert not valid
        assert "schema validation" in violations[0]

    def test_invalid_llm_proposal_raises_error(self):
        """I-06: Invalid LLM output raises error."""
        with pytest.raises(ValueError) as exc:
            ProposalPolicy.require_valid_proposal(False, True, "llm")

        assert "failed validation" in str(exc.value)


class TestLanguagePolicy:
    """Test I-07: neutral, diagnosis-free language."""

    def test_clinical_terms_rejected(self):
        """I-07: Clinical labels rejected."""
        text = "You are experiencing executive dysfunction"

        valid, violations = LanguagePolicy.validate_neutral_language(text)

        assert not valid
        assert "executive dysfunction" in str(violations)

    def test_neutral_language_accepted(self):
        """I-07: Neutral language accepted."""
        text = "The task is blocked. Next step: resolve dependency."

        valid, violations = LanguagePolicy.validate_neutral_language(text)

        assert valid
        assert len(violations) == 0


class TestUntrustedContentPolicy:
    """Test I-13: untrusted content stays data."""

    def test_only_user_source_trusted(self):
        """I-13: Only user input is trusted."""
        assert UntrustedContentPolicy.is_trusted_source("user")
        assert not UntrustedContentPolicy.is_trusted_source("repo")
        assert not UntrustedContentPolicy.is_trusted_source("tool")

    def test_untrusted_cannot_execute_commands(self):
        """I-13: Untrusted sources cannot bypass gates."""
        with pytest.raises(ValueError) as exc:
            UntrustedContentPolicy.require_trusted_for_command("repo", "mutation")

        assert "cannot bypass gates" in str(exc.value)
