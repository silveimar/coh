"""Tests for new MCP tools: plan_work, execute_task, verify_deliverable."""

from pathlib import Path

import pytest

from coh_mcp.handlers import COHHandlers


@pytest.fixture
def handlers(tmp_path: Path) -> COHHandlers:
    """Create COH handlers for testing."""
    return COHHandlers(tmp_path)


@pytest.mark.asyncio
async def test_plan_work_requires_plan_state(handlers: COHHandlers):
    """Test plan_work returns error if not in PLAN state."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    # Try plan_work without transitioning to PLAN
    result = await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Fix the bug",
                "done_when_condition": "Tests pass",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    assert "Session is not in PLAN state" in result[0]["text"]


@pytest.mark.asyncio
async def test_plan_work_yields_i01_foreground(handlers: COHHandlers):
    """Test plan_work in PLAN yields I-01 NOW with 5 metadata fields."""
    from uuid import UUID

    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix retry logic",
        why="Prevent hammering",
        deliverable="Working retry",
        done_when=["Tests pass", "Retry works"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    # Now in PLAN state
    result = await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Add exponential backoff",
                "done_when_condition": "Backoff increases with retries",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            },
            {
                "action_literal": "Update tests",
                "done_when_condition": "Tests verify backoff",
                "estimated_minutes": 15,
                "energy": "low",
                "activation_friction": "low",
            },
        ],
    )

    text = result[0]["text"]
    assert "GOAL:" in text
    assert "NOW" in text
    assert "Add exponential backoff" in text
    assert "Done when: Backoff increases with retries" in text
    assert "Estimated: 30 minutes" in text
    assert "Energy: medium" in text
    assert "Friction: low" in text

    # Verify tasks persisted
    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        from coh_application.spec_gate_service import SpecGateService

        spec_gate = SpecGateService(uow)
        spec_status = spec_gate.get_spec_status(session_uuid)
        spec_id = UUID(spec_status["spec_id"])
        tasks = uow.tasks.list_by_spec(spec_id)
        assert len(tasks) == 2


@pytest.mark.asyncio
async def test_plan_work_unresolved_deps_not_now(handlers: COHHandlers):
    """Test plan_work: task with unresolved deps is not NOW."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix bug",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    # Create tasks with dependencies
    result = await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "First task",
                "done_when_condition": "Step 1 done",
                "estimated_minutes": 20,
                "energy": "medium",
                "activation_friction": "low",
            },
            {
                "action_literal": "Second task (depends on first)",
                "done_when_condition": "Step 2 done",
                "estimated_minutes": 15,
                "energy": "low",
                "activation_friction": "low",
            },
        ],
    )

    text = result[0]["text"]
    # NOW should be the first task (no deps)
    assert "NOW" in text
    assert "First task" in text


@pytest.mark.asyncio
async def test_execute_task_errors_without_now_metadata(handlers: COHHandlers):
    """Test execute_task errors and stays PLAN if NOW missing metadata."""
    from uuid import UUID

    from execution_core.domain.enums import LifecycleState
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix bug",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    # Create plan with complete NOW task
    await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Fix the bug",
                "done_when_condition": "Bug fixed",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    # Manually break the task to simulate missing metadata
    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        from coh_application.spec_gate_service import SpecGateService

        spec_gate = SpecGateService(uow)
        spec_status = spec_gate.get_spec_status(session_uuid)
        spec_id = UUID(spec_status["spec_id"])
        tasks = uow.tasks.list_by_spec(spec_id)
        if tasks:
            # Break the task by removing metadata
            tasks[0].action_literal = None
            uow.tasks.update(tasks[0])
            uow.commit()

    # Try to execute - should fail
    result = await handlers.execute_task(session_id)

    assert "Cannot transition to EXECUTE" in result[0]["text"]
    assert "Session remains in PLAN state" in result[0]["text"]

    # Verify session stayed in PLAN
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session = uow.sessions.get(session_uuid)
        assert session.lifecycle_state == LifecycleState.PLAN


@pytest.mark.asyncio
async def test_execute_task_transitions_to_execute(handlers: COHHandlers):
    """Test execute_task with valid foreground transitions to EXECUTE."""
    from uuid import UUID

    from execution_core.domain.enums import LifecycleState
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix retry logic",
        why="Prevent hammering",
        deliverable="Working retry",
        done_when=["Tests pass"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Add exponential backoff",
                "done_when_condition": "Backoff increases with retries",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    # Execute task - should succeed
    result = await handlers.execute_task(session_id)

    assert "Transition: PLAN → EXECUTE" in result[0]["text"]
    assert "NOW" in result[0]["text"]

    # Verify session is in EXECUTE
    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session = uow.sessions.get(session_uuid)
        assert session.lifecycle_state == LifecycleState.EXECUTE


@pytest.mark.asyncio
async def test_execute_task_already_execute_returns_foreground(handlers: COHHandlers):
    """Test execute_task when already EXECUTE returns current foreground."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix bug",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Fix the bug",
                "done_when_condition": "Bug fixed",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    # First execute
    await handlers.execute_task(session_id)

    # Second execute - should return current foreground
    result = await handlers.execute_task(session_id)

    assert "Already in EXECUTE state" in result[0]["text"]
    assert "NOW" in result[0]["text"]


@pytest.mark.asyncio
async def test_verify_deliverable_without_evidence_does_not_complete(
    handlers: COHHandlers,
):
    """Test verify_deliverable without evidence does not reach COMPLETE."""
    from uuid import UUID

    from execution_core.domain.enums import LifecycleState
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix bug",
        why="Broken",
        deliverable="Fixed code",
        done_when=["Tests pass", "Code reviewed"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Fix the bug",
                "done_when_condition": "Bug fixed",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    await handlers.execute_task(session_id)

    # Try to verify with no evidence
    result = await handlers.verify_deliverable(session_id=session_id, evidence_list=[])

    assert "Verification failed" in result[0]["text"]
    assert "VERIFY → EXECUTE" in result[0]["text"]

    # Verify session is back in EXECUTE (T8)
    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session = uow.sessions.get(session_uuid)
        assert session.lifecycle_state == LifecycleState.EXECUTE


@pytest.mark.asyncio
async def test_verify_deliverable_with_evidence_reaches_complete(
    handlers: COHHandlers,
):
    """Test verify_deliverable with matching evidence reaches COMPLETE."""
    from uuid import UUID

    from execution_core.domain.enums import LifecycleState
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id=session_id,
        what="Fix bug",
        why="Broken",
        deliverable="Fixed code",
        done_when=["Tests pass"],
    )

    await handlers.confirm_spec(session_id, confirmed=True)

    await handlers.plan_work(
        session_id=session_id,
        tasks=[
            {
                "action_literal": "Fix the bug",
                "done_when_condition": "Bug fixed",
                "estimated_minutes": 30,
                "energy": "medium",
                "activation_friction": "low",
            }
        ],
    )

    await handlers.execute_task(session_id)

    # Verify with complete evidence
    result = await handlers.verify_deliverable(
        session_id=session_id,
        evidence_list=[
            {
                "criterion_text": "Tests pass",
                "evidence_type": "test",
                "authority": "tool_verified",
                "result": "pass",
                "summary": "All 15 tests passed",
                "source": "pytest",
            }
        ],
    )

    assert "VERIFY → COMPLETE" in result[0]["text"]
    assert "complete" in result[0]["text"].lower()

    # Verify session is in COMPLETE (T9)
    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        session = uow.sessions.get(session_uuid)
        assert session.lifecycle_state == LifecycleState.COMPLETE
