"""Tests for state machine guard branches not exercised by the T1-T11 flow tests."""

from collections.abc import Callable
from uuid import uuid4

import pytest

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.commands import Command
from execution_core.domain.enums import (
    ActivationFriction,
    EnergyLevel,
    LifecycleState,
    SessionIntent,
    TaskStatus,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.domain.task import Task, TaskDependency
from execution_core.state_machine.lifecycle import StateMachine, TransitionError


def _ready_spec() -> Specification:
    spec = Specification(
        what="Add feature",
        why="User needs it",
        deliverable="Working feature",
        done_when=[DoneWhenCriterion(text="Feature works")],
    )
    spec.update_computed_fields()
    return spec


def _session(
    state: LifecycleState, spec: Specification | None = None
) -> ExecutionSession:
    return ExecutionSession(
        project_id="test_project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=state,
        current_spec=spec,
    )


def _command(session: ExecutionSession) -> Command:
    return Command(idempotency_key=str(uuid4()), expected_version=session.version)


def _complete_task(**overrides: object) -> Task:
    fields: dict[str, object] = {
        "spec_id": uuid4(),
        "spec_revision": 1,
        "action_literal": "Write the handler",
        "done_when_condition": "Handler returns 200",
        "estimated_minutes": 15,
        "energy": EnergyLevel.LOW,
        "activation_friction": ActivationFriction.LOW,
    }
    fields.update(overrides)
    return Task.model_validate(fields)


Transition = Callable[[StateMachine, ExecutionSession, Command], object]

WRONG_STATE_CASES: list[tuple[str, LifecycleState, Transition, str]] = [
    (
        "T2 specify",
        LifecycleState.SPECIFY,
        lambda m, s, c: m.transition_to_specify(s, findings_archived=True, command=c),
        "Must be in INSPECT state",
    ),
    (
        "T3 confirm",
        LifecycleState.INSPECT,
        lambda m, s, c: m.transition_to_confirm(s, spec=_ready_spec(), command=c),
        "Must be in SPECIFY state",
    ),
    (
        "T4 plan",
        LifecycleState.INSPECT,
        lambda m, s, c: m.transition_to_plan(
            s, user_confirmed=True, command=c, change_scope="small"
        ),
        "Must be in CONFIRM state",
    ),
    (
        "T5 correct spec",
        LifecycleState.INSPECT,
        lambda m, s, c: m.correct_spec(s, corrected_spec=_ready_spec(), command=c),
        "Must be in CONFIRM state",
    ),
    (
        "T6 execute",
        LifecycleState.INSPECT,
        lambda m, s, c: m.transition_to_execute(s, command=c, tasks=[]),
        "Must be in PLAN state",
    ),
    (
        "T7 verify",
        LifecycleState.INSPECT,
        lambda m, s, c: m.transition_to_verify(s, command=c),
        "Must be in EXECUTE state",
    ),
    (
        "T8 return to execute",
        LifecycleState.INSPECT,
        lambda m, s, c: m.return_to_execute(s, command=c),
        "Must be in VERIFY state",
    ),
    (
        "T9 complete",
        LifecycleState.INSPECT,
        lambda m, s, c: m.transition_to_complete(s, evidence_list=[], command=c),
        "Must be in VERIFY state",
    ),
]


class TestWrongSourceState:
    """Each transition rejects a session that is not in its source state."""

    @pytest.mark.parametrize(
        ("state", "transition", "expected_reason"),
        [case[1:] for case in WRONG_STATE_CASES],
        ids=[case[0] for case in WRONG_STATE_CASES],
    )
    def test_transition_rejected_from_wrong_state(
        self,
        state: LifecycleState,
        transition: Transition,
        expected_reason: str,
    ) -> None:
        machine = StateMachine()
        session = _session(state, _ready_spec())

        with pytest.raises(TransitionError) as exc_info:
            transition(machine, session, _command(session))

        assert expected_reason in exc_info.value.blocked_reason
        assert session.lifecycle_state == state
        assert session.version == 1


class TestMissingSpecGuards:
    """Transitions that need a current spec reject a session without one."""

    def test_t4_plan_requires_spec(self) -> None:
        machine = StateMachine()
        session = _session(LifecycleState.CONFIRM)

        with pytest.raises(TransitionError) as exc_info:
            machine.transition_to_plan(
                session,
                user_confirmed=True,
                command=_command(session),
                change_scope="small",
            )

        assert "no spec" in str(exc_info.value)
        assert session.lifecycle_state == LifecycleState.CONFIRM

    def test_t9_complete_requires_spec(self) -> None:
        machine = StateMachine()
        session = _session(LifecycleState.VERIFY)

        with pytest.raises(TransitionError) as exc_info:
            machine.transition_to_complete(
                session, evidence_list=[], command=_command(session)
            )

        assert "no spec" in str(exc_info.value)
        assert session.lifecycle_state == LifecycleState.VERIFY


class TestT6NowDependencies:
    """T6 checks NOW dependencies against the caller's completed task ids."""

    def test_now_with_dependency_outside_completed_ids_is_rejected(self) -> None:
        machine = StateMachine()
        session = _session(LifecycleState.PLAN, _ready_spec())
        dependency = _complete_task(status=TaskStatus.COMPLETED)
        now = _complete_task(dependencies=[TaskDependency(task_id=dependency.id)])

        with pytest.raises(TransitionError) as exc_info:
            machine.transition_to_execute(
                session, command=_command(session), tasks=[dependency, now]
            )

        assert exc_info.value.blocked_reason == "NOW task has unresolved dependencies"
        assert session.lifecycle_state == LifecycleState.PLAN

    def test_now_with_dependency_in_completed_ids_enters_execute(self) -> None:
        machine = StateMachine()
        session = _session(LifecycleState.PLAN, _ready_spec())
        dependency = _complete_task(status=TaskStatus.COMPLETED)
        now = _complete_task(dependencies=[TaskDependency(task_id=dependency.id)])

        machine.transition_to_execute(
            session,
            command=_command(session),
            tasks=[dependency, now],
            completed_task_ids={dependency.id},
        )

        assert session.lifecycle_state == LifecycleState.EXECUTE


class TestT11RecoverGuards:
    """T11 rejects checkpoints that do not belong to the session or its spec."""

    def test_checkpoint_from_other_session_is_rejected(self) -> None:
        machine = StateMachine()
        session = _session(LifecycleState.EXECUTE, _ready_spec())
        checkpoint = Checkpoint(
            session_id=uuid4(),
            lifecycle_state=LifecycleState.PLAN,
            restart_action="Resume planning",
        )

        with pytest.raises(TransitionError) as exc_info:
            machine.recover(session, checkpoint, _command(session))

        assert exc_info.value.blocked_reason == "Checkpoint does not match session"
        assert session.lifecycle_state == LifecycleState.EXECUTE

    def test_checkpoint_spec_id_mismatch_without_snapshot_is_rejected(self) -> None:
        machine = StateMachine()
        current_spec = _ready_spec()
        session = _session(LifecycleState.EXECUTE, current_spec)
        other_spec_id = uuid4()
        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.PLAN,
            spec_id=other_spec_id,
            restart_action="Resume planning",
        )

        with pytest.raises(TransitionError) as exc_info:
            machine.recover(session, checkpoint, _command(session))

        assert "spec mismatch" in str(exc_info.value)
        assert str(other_spec_id) in exc_info.value.blocked_reason
        assert session.current_spec is current_spec

    def test_checkpoint_spec_id_match_without_snapshot_keeps_spec(self) -> None:
        machine = StateMachine()
        current_spec = _ready_spec()
        session = _session(LifecycleState.EXECUTE, current_spec)
        checkpoint = Checkpoint(
            session_id=session.id,
            lifecycle_state=LifecycleState.PLAN,
            spec_id=current_spec.id,
            restart_action="Resume planning",
        )

        session, summary = machine.recover(session, checkpoint, _command(session))

        assert session.lifecycle_state == LifecycleState.PLAN
        assert session.current_spec is current_spec
        assert summary.goal == "Add feature"
        assert summary.restart_action == "Resume planning"
