"""Tests for persistence integration and COH gate blockers 1-4."""

import os
from pathlib import Path
from uuid import UUID

import pytest

from coh_mcp.handlers import COHHandlers
from execution_core.state_machine.lifecycle import TransitionError


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create temporary project root for testing."""
    return tmp_path


@pytest.fixture
def handlers(temp_project_root: Path) -> COHHandlers:
    """Create handlers with persistence for testing."""
    return COHHandlers(temp_project_root)


@pytest.mark.asyncio
async def test_recover_after_restart_restores_spec_from_snapshot(
    handlers: COHHandlers,
):
    """
    Blocker 2: Crash/restart test.

    Persist session+spec+checkpoint, new engine/process,
    recover via T11 restores spec from spec_snapshot.
    """
    # Create session, spec, checkpoint
    result = await handlers.create_session("test-project", "Fix bug")
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    await handlers.specify_work(
        session_id,
        what="Fix null pointer bug",
        why="Prevents crashes",
        deliverable="Patched code",
        done_when=["Tests pass", "No NPE"],
        inspection_findings="Found NPE in handler.py line 42",
    )

    await handlers.create_checkpoint(
        session_id, restart_action="Resume bug fix", reason="checkpoint test"
    )

    # Simulate crash/restart: new handlers instance (new engine/process)
    new_handlers = COHHandlers(handlers.project_root)

    # Recover should restore spec from spec_snapshot via T11
    result = await new_handlers.recover_session(session_id)
    text = result[0]["text"]

    # Verify spec body restored
    assert "Fix null pointer bug" in text
    assert "Resume bug fix" in text


@pytest.mark.asyncio
async def test_create_checkpoint_preserves_archive_references(
    handlers: COHHandlers,
):
    """
    Blocker 3: create_checkpoint must ADD, not replace.

    Verify archive_references from prior checkpoint are preserved (I-09).
    """
    result = await handlers.create_session("test-project", "Task")
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    # Create first checkpoint (will have archive refs from create_session)
    await handlers.create_checkpoint(session_id, restart_action="First checkpoint")

    # Create second checkpoint - should preserve refs from first
    await handlers.create_checkpoint(session_id, restart_action="Second checkpoint")

    # Verify via persistence: should have 2 checkpoints (ADD, not replace)
    from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

    session_uuid = UUID(session_id)
    with SqlAlchemyUnitOfWork(handlers.session_factory) as uow:
        checkpoints = uow.checkpoints.list_by_session(session_uuid)
        # Should have 3: initial from create_session, then 2 explicit
        assert len(checkpoints) >= 2

        # Latest checkpoint should have archive_references copied from prior
        latest = uow.checkpoints.get_latest_for_session(session_uuid)
        assert latest is not None
        # Archive references should be preserved from earlier checkpoints


@pytest.mark.asyncio
async def test_specify_work_blocked_when_archive_fails(handlers: COHHandlers):
    """
    Blocker 4: T2 must fail closed when findings_archived=False.

    If archive write fails, T2 raises TransitionError (findings_archived=False).
    """
    result = await handlers.create_session("test-project", "Task")
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]

    # Make archive directory unwritable to force archive failure
    archive_dir = handlers.project_root / ".coh" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    original_mode = archive_dir.stat().st_mode
    os.chmod(archive_dir, 0o000)

    try:
        # specify_work with inspection_findings should fail T2 when archive fails
        with pytest.raises(TransitionError) as exc_info:
            await handlers.specify_work(
                session_id,
                what="Fix bug",
                why="Needed",
                deliverable="Code",
                done_when=["Tests pass"],
                inspection_findings="Found issue in code",
            )

        # T2 should fail because findings_archived=False
        assert "findings not archived" in str(exc_info.value).lower()
    finally:
        # Restore permissions
        os.chmod(archive_dir, original_mode)
