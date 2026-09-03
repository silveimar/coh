"""Tests for MCP handlers."""

from pathlib import Path

import pytest

from coh_mcp.errors import CapabilityNotImplementedError
from coh_mcp.handlers import COHHandlers


@pytest.fixture
def handlers(tmp_path: Path) -> COHHandlers:
    """Create COH handlers for testing."""
    return COHHandlers(tmp_path)


@pytest.mark.asyncio
async def test_create_session_round_trip(handlers: COHHandlers):
    """Test create_session round-trip: persist via archive."""
    from uuid import UUID

    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix the retry logic",
        intent="execute",
    )

    assert len(result) == 1
    assert "Session created:" in result[0]["text"]
    assert "Intent: execute" in result[0]["text"]
    assert "State: INSPECT" in result[0]["text"]
    assert "Archive status:" in result[0]["text"]

    # Extract session_id from result text
    session_id_str = result[0]["text"].split("\n")[0].split(": ")[1]
    session_id = UUID(session_id_str)

    # Verify via persistence
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session = uow.sessions.get(session_id)
        assert session is not None
        checkpoint = uow.checkpoints.get_latest_for_session(session_id)
        assert checkpoint is not None


@pytest.mark.asyncio
async def test_intent_inference(handlers: COHHandlers):
    """Test intent inference (T1)."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Recover my previous session",
    )

    assert "Intent: recover" in result[0]["text"]


@pytest.mark.asyncio
async def test_inspect_repository_raises_not_implemented(handlers: COHHandlers):
    """Test I-14: inspect_repository returns NOT_IMPLEMENTED."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    # Extract session_id from result text
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    with pytest.raises(CapabilityNotImplementedError) as exc_info:
        await handlers.inspect_repository(session_id)

    assert exc_info.value.capability == "repository_inspection"
    assert "inspection targets" in exc_info.value.context_needed


@pytest.mark.asyncio
async def test_specify_work_renders_with_prose(handlers: COHHandlers):
    """Test specify_work uses prose renderer (P-01: findings before spec)."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix retry",
    )

    # Extract session_id from result text
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    result = await handlers.specify_work(
        session_id=session_id,
        inspection_findings="worker.py has no backoff in retry loop",
        what="Add exponential backoff",
        why="Prevent queue hammering",
        deliverable="Retry with backoff",
        done_when=["Tests pass", "Backoff works"],
    )

    text = result[0]["text"]
    assert "worker.py has no backoff" in text
    assert text.index("worker.py") < text.index("WHAT")
    assert "WHAT" in text
    assert "WHY" in text
    assert "DELIVERABLE" in text
    assert "DONE WHEN" in text


@pytest.mark.asyncio
async def test_confirm_spec_transitions(handlers: COHHandlers):
    """Test confirm_spec transitions to PLAN."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    # Extract session_id from result text
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    # specify_work now only transitions to SPECIFY, not CONFIRM
    await handlers.specify_work(
        session_id=session_id,
        what="Fix",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    result = await handlers.confirm_spec(session_id, confirmed=True)

    # Should see CONFIRM → PLAN
    assert "PLAN" in result[0]["text"] or "CONFIRM → PLAN" in result[0]["text"]


@pytest.mark.asyncio
async def test_create_checkpoint_stores_restart_action(handlers: COHHandlers):
    """Test I-09: checkpoint stores restart_action + archive references."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    # Extract session_id from result text
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    result = await handlers.create_checkpoint(
        session_id=session_id,
        restart_action="Open worker.py line 42",
        reason="before long operation",
    )

    assert "Checkpoint created:" in result[0]["text"]
    assert "Open worker.py line 42" in result[0]["text"]
    assert "Archive status:" in result[0]["text"]


@pytest.mark.asyncio
async def test_recover_session_renders_with_p06_exemption(handlers: COHHandlers):
    """Test recover_session uses P-06 exemption (prospective framing allowed)."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    # Extract session_id from result text
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.create_checkpoint(
        session_id=session_id,
        restart_action="Continue from worker.py",
    )

    result = await handlers.recover_session(session_id)

    text = result[0]["text"]
    assert "GOAL:" in text
    assert "WHY:" in text
    assert "START HERE:" in text
    assert "Continue from worker.py" in text


@pytest.mark.asyncio
async def test_recover_session_shows_archive_degraded_notice(
    handlers: COHHandlers, tmp_path: Path
):
    """Test I-12: recovery summary shows archive degradation notice."""
    from uuid import uuid4

    from execution_core.domain.checkpoint import Checkpoint
    from execution_core.domain.enums import ArchiveStatus, LifecycleState
    from execution_core.domain.session import ExecutionSession
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_id = uuid4()

    # Create session and checkpoint in persistence
    session = ExecutionSession(
        id=session_id,
        project_id="test-project",
        intent="execute",
        lifecycle_state=LifecycleState.EXECUTE,
    )

    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.EXECUTE,
        restart_action="Test",
        archive_status=ArchiveStatus.DEGRADED,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.add(session)

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.checkpoints.add(checkpoint)

    result = await handlers.recover_session(str(session_id))

    text = result[0]["text"]
    assert "Archive status is degraded" in text


@pytest.mark.asyncio
async def test_get_archive_status(handlers: COHHandlers):
    """Test get_archive_status returns integration health."""
    result = await handlers.get_archive_status()

    text = result[0]["text"]
    assert "Archive Integration Status" in text
    assert "Enabled:" in text
    assert "Writes succeeded:" in text
    assert "Writes failed:" in text


@pytest.mark.asyncio
async def test_propose_spec_returns_computed_readiness(handlers: COHHandlers):
    """Test propose_spec returns computed clarity/readiness without persisting."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    result = await handlers.propose_spec(
        session_id=session_id,
        what="Fix retry logic",
        why="Prevent queue hammering",
        deliverable="Working retry",
        done_when=["Tests pass"],
    )

    text = result[0]["text"]
    assert "Clarity:" in text
    assert "Readiness:" in text


@pytest.mark.asyncio
async def test_propose_spec_with_missing_what_returns_blocked(handlers: COHHandlers):
    """Test propose_spec with missing WHAT returns blocked with blockers."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    # Transition to SPECIFY first
    await handlers.specify_work(
        session_id=session_id,
        what="Fix retry",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    result = await handlers.propose_spec(
        session_id=session_id,
        what="",  # Missing WHAT
        why="Prevent issues",
        deliverable="Working retry",
        done_when=["Tests pass"],
    )

    text = result[0]["text"]
    assert "Readiness: blocked" in text
    assert "Blockers:" in text
    assert "Missing WHAT" in text


@pytest.mark.asyncio
async def test_confirm_spec_while_blocked_returns_error(handlers: COHHandlers):
    """Test I-02: confirm_spec while readiness=BLOCKED returns error, no T4."""
    from uuid import uuid4

    from execution_core.domain.enums import LifecycleState
    from execution_core.domain.session import ExecutionSession
    from execution_core.domain.specification import Specification
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_id = uuid4()

    # Create session in SPECIFY state
    session = ExecutionSession(
        id=session_id,
        project_id="test-project",
        intent="execute",
        lifecycle_state=LifecycleState.SPECIFY,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.add(session)

    # Create spec with missing WHAT (blocked)
    spec = Specification(
        id=uuid4(),
        session_id=session_id,
        revision=1,
        what="",  # Missing WHAT
        why="Test",
        deliverable="Test",
        done_when=[],  # Missing done_when
    )

    spec.update_computed_fields()

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.specifications.add(spec)

    # Link spec to session
    session.current_spec = spec
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.update(session, expected_version=session.version)

    # Attempt to confirm - should fail with error
    result = await handlers.confirm_spec(str(session_id), confirmed=True)

    text = result[0]["text"]
    assert "Cannot confirm specification" in text
    assert "readiness is BLOCKED" in text
    assert "Blockers:" in text
    assert "Missing WHAT" in text or "Missing DONE WHEN" in text

    # Verify session is still in SPECIFY state (no T4 transition)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session_check = uow.sessions.get(session_id)
        assert session_check.lifecycle_state == LifecycleState.SPECIFY


@pytest.mark.asyncio
async def test_get_spec_status_while_blocked_succeeds(handlers: COHHandlers):
    """Test I-02: get_spec_status succeeds even when readiness=BLOCKED."""
    from uuid import uuid4

    from execution_core.domain.enums import LifecycleState
    from execution_core.domain.session import ExecutionSession
    from execution_core.domain.specification import Specification
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_id = uuid4()

    session = ExecutionSession(
        id=session_id,
        project_id="test-project",
        intent="execute",
        lifecycle_state=LifecycleState.SPECIFY,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.add(session)

    spec = Specification(
        id=uuid4(),
        session_id=session_id,
        revision=1,
        what="",  # Missing WHAT
        why="Test",
        deliverable="Test",
        done_when=[],
    )

    spec.update_computed_fields()

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.specifications.add(spec)

    session.current_spec = spec
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.update(session, expected_version=session.version)

    # get_spec_status should succeed even when blocked
    result = await handlers.get_spec_status(str(session_id))

    text = result[0]["text"]
    assert "Specification Status" in text
    assert "Readiness: blocked" in text
    assert "Blockers:" in text


@pytest.mark.asyncio
async def test_get_foreground_returns_i01_shape(handlers: COHHandlers):
    """Test I-01: get_foreground returns NOW with 5 metadata fields."""
    from uuid import uuid4

    from execution_core.domain.enums import (
        ActivationFriction,
        EnergyLevel,
        ForegroundPosition,
        LifecycleState,
        TaskStatus,
    )
    from execution_core.domain.session import ExecutionSession
    from execution_core.domain.specification import DoneWhenCriterion, Specification
    from execution_core.domain.task import Task
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_id = uuid4()
    spec_id = uuid4()

    session = ExecutionSession(
        id=session_id,
        project_id="test-project",
        intent="execute",
        lifecycle_state=LifecycleState.EXECUTE,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.add(session)

    spec = Specification(
        id=spec_id,
        session_id=session_id,
        revision=1,
        what="Test work",
        why="Testing",
        deliverable="Test output",
        done_when=[DoneWhenCriterion(text="Complete")],
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.specifications.add(spec)

    session.current_spec = spec
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.update(session, expected_version=session.version)

    # Create NOW task with all 5 metadata fields (I-01)
    now_task = Task(
        id=uuid4(),
        spec_id=spec_id,
        spec_revision=1,
        action_literal="Add exponential backoff to worker.py",
        done_when_condition="Tests pass and backoff works",
        estimated_minutes=45,
        energy=EnergyLevel.MEDIUM,
        activation_friction=ActivationFriction.MEDIUM,
        status=TaskStatus.IN_PROGRESS,
        foreground_position=ForegroundPosition.NOW,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.tasks.add(now_task)

    # get_foreground should return NOW with all 5 metadata fields
    result = await handlers.get_foreground(str(session_id))

    text = result[0]["text"]
    assert "NOW:" in text or "GOAL:" in text
    # Verify prose rendering includes metadata
    assert "45" in text or "minutes" in text.lower()
    assert "medium" in text.lower() or "energy" in text.lower()


@pytest.mark.asyncio
async def test_complete_now_on_non_now_task_errors(handlers: COHHandlers):
    """Test complete_now on a non-NOW task returns error."""
    from uuid import uuid4

    from execution_core.domain.enums import (
        ForegroundPosition,
        LifecycleState,
        TaskStatus,
    )
    from execution_core.domain.session import ExecutionSession
    from execution_core.domain.specification import DoneWhenCriterion, Specification
    from execution_core.domain.task import Task
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_id = uuid4()
    spec_id = uuid4()

    session = ExecutionSession(
        id=session_id,
        project_id="test-project",
        intent="execute",
        lifecycle_state=LifecycleState.EXECUTE,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.add(session)

    spec = Specification(
        id=spec_id,
        session_id=session_id,
        revision=1,
        what="Test work",
        why="Testing",
        deliverable="Test output",
        done_when=[DoneWhenCriterion(text="Complete")],
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.specifications.add(spec)

    session.current_spec = spec
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.sessions.update(session, expected_version=session.version)

    # Create NEXT task (not NOW)
    next_task = Task(
        id=uuid4(),
        spec_id=spec_id,
        spec_revision=1,
        action_literal="Fix retry logic",
        status=TaskStatus.PLANNED,
        foreground_position=ForegroundPosition.NEXT_1,
    )

    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        uow.tasks.add(next_task)

    # Attempt to complete NEXT task as if it were NOW - should error
    result = await handlers.complete_now(
        str(session_id), str(next_task.id), "Done"
    )

    text = result[0]["text"]
    assert "Error:" in text
    assert "not the NOW task" in text
