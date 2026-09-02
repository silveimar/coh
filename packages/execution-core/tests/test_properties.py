"""Property-based tests using Hypothesis for state machine and policies."""

from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st

from execution_core.domain.enums import (
    ActivationFriction,
    EnergyLevel,
    EvidenceAuthority,
    EvidenceResult,
    LifecycleState,
    Readiness,
    TaskStatus,
)
from execution_core.domain.evidence import Evidence
from execution_core.domain.session import SessionIntent
from execution_core.domain.specification import (
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from execution_core.domain.task import Task, TaskDependency
from execution_core.policies.completion_policy import CompletionPolicy
from execution_core.policies.foreground_policy import ForegroundPolicy
from execution_core.state_machine.lifecycle import StateMachine


class TestSpecificationProperties:
    """Property-based tests for specification invariants."""

    @given(
        what=st.text(min_size=0, max_size=100),
        why=st.text(min_size=0, max_size=100),
        deliverable=st.text(min_size=0, max_size=100),
        num_criteria=st.integers(min_value=0, max_value=5),
    )
    def test_readiness_blocked_without_required_fields(
        self, what, why, deliverable, num_criteria
    ):
        """Property: Spec without required fields is always BLOCKED."""
        criteria = [
            DoneWhenCriterion(text=f"Criterion {i}") for i in range(num_criteria)
        ]

        spec = Specification(
            what=what, why=why, deliverable=deliverable, done_when=criteria
        )
        spec.update_computed_fields()

        if not all([what, why, deliverable, criteria]):
            assert spec.readiness == Readiness.BLOCKED

    @given(num_blocking_unknowns=st.integers(min_value=1, max_value=5))
    def test_blocking_unknowns_prevent_readiness(self, num_blocking_unknowns):
        """Property: Any blocking unknown prevents readiness."""
        spec = Specification(
            what="What",
            why="Why",
            deliverable="Deliverable",
            done_when=[DoneWhenCriterion(text="Done")],
            unknowns=[
                Unknown(text=f"Unknown {i}", blocking=True)
                for i in range(num_blocking_unknowns)
            ],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.BLOCKED

    @given(revision=st.integers(min_value=1, max_value=100))
    def test_create_revision_always_increments(self, revision):
        """Property: Creating revision always increments revision number."""
        spec = Specification(
            what="What",
            why="Why",
            deliverable="Deliverable",
            done_when=[DoneWhenCriterion(text="Done")],
        )
        spec.revision = revision

        new_spec = spec.create_revision()

        assert new_spec.revision == revision + 1
        assert new_spec.id != spec.id


class TestForegroundProperties:
    """Property-based tests for foreground policy invariants."""

    @given(num_eligible_tasks=st.integers(min_value=0, max_value=10))
    def test_foreground_never_exceeds_limits(self, num_eligible_tasks):
        """Property: Foreground never has more than 1 NOW and 2 NEXT."""
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
                goal_leverage=0.5,
            )
            for i in range(num_eligible_tasks)
        ]

        foreground = ForegroundPolicy.calculate_foreground(session_id, "Goal", tasks, 0)

        now_count = 1 if foreground.now_task else 0
        next_count = (1 if foreground.next_1_task else 0) + (
            1 if foreground.next_2_task else 0
        )

        assert now_count <= 1
        assert next_count <= 2

    @given(
        num_deps=st.integers(min_value=1, max_value=5),
        num_completed=st.integers(min_value=0, max_value=5),
    )
    def test_task_with_unresolved_deps_not_now(self, num_deps, num_completed):
        """
        Property: Task with unresolved dependencies cannot become NOW
        via foreground policy.
        """
        session_id = uuid4()
        spec_id = uuid4()

        dep_ids = [uuid4() for _ in range(num_deps)]
        completed_ids = set(dep_ids[:num_completed])

        dep_tasks = [
            Task(
                id=dep_id,
                spec_id=spec_id,
                spec_revision=1,
                status=TaskStatus.COMPLETED
                if dep_id in completed_ids
                else TaskStatus.PLANNED,
            )
            for dep_id in dep_ids
        ]

        task = Task(
            spec_id=spec_id,
            spec_revision=1,
            action_literal="Dependent task",
            done_when_condition="Done",
            estimated_minutes=10,
            energy=EnergyLevel.MEDIUM,
            activation_friction=ActivationFriction.LOW,
            status=TaskStatus.PLANNED,
            dependencies=[TaskDependency(task_id=dep_id) for dep_id in dep_ids],
        )

        foreground = ForegroundPolicy.calculate_foreground(
            session_id, "Test goal", dep_tasks + [task], 0
        )

        has_unresolved, _ = task.has_unresolved_dependencies(completed_ids)

        if has_unresolved:
            assert foreground.now_task is None or foreground.now_task.id != task.id


class TestCompletionProperties:
    """Property-based tests for completion policy invariants."""

    @given(
        num_criteria=st.integers(min_value=1, max_value=5),
        evidence_per_criterion=st.integers(min_value=0, max_value=2),
    )
    def test_done_requires_evidence_for_all_criteria(
        self, num_criteria, evidence_per_criterion
    ):
        """Property: DONE requires evidence for every criterion."""
        spec_id = uuid4()
        criteria = [
            DoneWhenCriterion(text=f"Criterion {i}") for i in range(num_criteria)
        ]

        evidence_list = []
        for criterion in criteria:
            for _ in range(evidence_per_criterion):
                evidence_list.append(
                    Evidence(
                        spec_id=spec_id,
                        spec_revision=1,
                        criterion_id=criterion.id,
                        evidence_type="test",
                        authority=EvidenceAuthority.TOOL_VERIFIED,
                        result=EvidenceResult.PASS,
                        summary="Passed",
                        source="test",
                    )
                )

        state, missing = CompletionPolicy.compute_completion_state(
            criteria, evidence_list, 1
        )

        if evidence_per_criterion == 0:
            assert state.value != "done"
            assert len(missing) == num_criteria
        else:
            assert state.value == "done"
            assert len(missing) == 0

    @given(spec_revision=st.integers(min_value=1, max_value=10))
    def test_stale_evidence_cannot_satisfy_criteria(self, spec_revision):
        """Property: Evidence from old revision cannot satisfy current criteria."""
        spec_id = uuid4()
        criterion = DoneWhenCriterion(text="Test criterion")

        old_evidence = Evidence(
            spec_id=spec_id,
            spec_revision=1,
            criterion_id=criterion.id,
            evidence_type="test",
            authority=EvidenceAuthority.TOOL_VERIFIED,
            result=EvidenceResult.PASS,
            summary="Old evidence",
            source="test",
        )

        if spec_revision > 1:
            assert not old_evidence.is_fresh_for_revision(spec_revision)
            old_evidence.mark_stale()
            assert not old_evidence.can_satisfy_criterion()


class TestStateMachineProperties:
    """Property-based tests for state machine transitions."""

    @given(
        from_state=st.sampled_from(LifecycleState),
        to_state=st.sampled_from(LifecycleState),
    )
    def test_transition_validation_is_deterministic(self, from_state, to_state):
        """Property: Same transition check always gives same result."""
        result1, msg1 = StateMachine.can_transition(from_state, to_state)
        result2, msg2 = StateMachine.can_transition(from_state, to_state)

        assert result1 == result2
        if msg1:
            assert msg1 == msg2

    @given(intent=st.sampled_from(SessionIntent))
    def test_session_start_always_enters_inspect(self, intent):
        """Property: Starting session always enters INSPECT."""
        session = StateMachine.start_session("test-project", intent)

        assert session.lifecycle_state == LifecycleState.INSPECT
        assert session.intent == intent
