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

    assert len(handlers.sessions) == 1
    assert len(handlers.checkpoints) == 1


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
    await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = str(list(handlers.sessions.keys())[0])

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

    session_id = str(list(handlers.sessions.keys())[0])

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

    session_id = str(list(handlers.sessions.keys())[0])

    await handlers.specify_work(
        session_id=session_id,
        what="Fix",
        why="Broken",
        deliverable="Fixed",
        done_when=["Done"],
    )

    result = await handlers.confirm_spec(session_id, confirmed=True)

    assert "CONFIRM → PLAN" in result[0]["text"]


@pytest.mark.asyncio
async def test_create_checkpoint_stores_restart_action(handlers: COHHandlers):
    """Test I-09: checkpoint stores restart_action + archive references."""
    result = await handlers.create_session(
        project_id="test-project",
        user_input="Fix bug",
    )

    session_id = str(list(handlers.sessions.keys())[0])

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

    session_id = str(list(handlers.sessions.keys())[0])

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
    from execution_core.domain.enums import LifecycleState

    session_id = uuid4()

    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.EXECUTE,
        restart_action="Test",
    )

    checkpoint.mark_degraded()

    handlers.checkpoints[session_id] = checkpoint

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
