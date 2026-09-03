"""Integration tests for archive system."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from coh_archive import (
    Actor,
    ArchiveConfig,
    ArchiveEvent,
    ArchiveService,
    EventStatus,
    ToolEvent,
    WriteOutcome,
)


@pytest.mark.asyncio
async def test_complete_interaction_workflow(tmp_path: Path):
    """End-to-end: user input, agent response, tool events."""
    session_id = uuid4()
    project_id = "test-project"
    config = ArchiveConfig()
    service = ArchiveService(tmp_path, config)

    user_event = ArchiveEvent(
        actor=Actor.USER,
        time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
        session_id=session_id,
        project_id=project_id,
        content="Fix the authentication test",
    )
    user_result = await service.archive_interaction(user_event)
    assert user_result.outcome == WriteOutcome.WRITTEN

    agent_event = ArchiveEvent(
        actor=Actor.AGENT,
        time=datetime(2026, 8, 19, 12, 35, 10, tzinfo=UTC),
        session_id=session_id,
        project_id=project_id,
        content="I'll examine the test and fix the authentication logic.",
    )
    agent_result = await service.archive_interaction(agent_event)
    assert agent_result.outcome == WriteOutcome.WRITTEN

    tool_event = ToolEvent(
        time=datetime(2026, 8, 19, 12, 35, 15, tzinfo=UTC),
        session_id=session_id,
        project_id=project_id,
        tool_name="read_file",
        status=EventStatus.SUCCEEDED,
        invocation_time=datetime(2026, 8, 19, 12, 35, 15, tzinfo=UTC),
        result_time=datetime(2026, 8, 19, 12, 35, 16, tzinfo=UTC),
        input_payload={"path": "tests/test_auth.py"},
        output_payload={"content": "test code here..."},
    )
    tool_result = await service.archive_tool_event(tool_event)
    assert tool_result.outcome == WriteOutcome.WRITTEN

    session_file = tmp_path / user_result.pointer.path
    front_matter, entries = service.read_session_archive(session_file)

    assert front_matter["session_id"] == str(session_id)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_archive_failure_checkpoint_can_mark_degraded(tmp_path: Path):
    """I-12: Archive failure result allows checkpoint to mark degraded status."""
    archive_dir = tmp_path / ".coh" / "archive"
    archive_dir.mkdir(parents=True)
    archive_dir.chmod(0o000)

    try:
        session_id = uuid4()
        config = ArchiveConfig()
        service = ArchiveService(tmp_path, config)

        event = ArchiveEvent(
            actor=Actor.USER,
            time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
            session_id=session_id,
            project_id="test-project",
            content="Test message",
        )

        result = await service.archive_interaction(event)

        assert result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED

        from execution_core.domain.checkpoint import Checkpoint
        from execution_core.domain.enums import LifecycleState

        checkpoint = Checkpoint(
            session_id=session_id,
            lifecycle_state=LifecycleState.EXECUTE,
            restart_action="Continue execution",
        )

        if result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
            checkpoint.mark_degraded()

        from execution_core.domain.enums import ArchiveStatus

        assert checkpoint.archive_status == ArchiveStatus.DEGRADED

    finally:
        archive_dir.chmod(0o755)


@pytest.mark.asyncio
async def test_custom_archive_location(tmp_path: Path):
    """Custom relative archive location works correctly."""
    session_id = uuid4()
    config = ArchiveConfig(directory="custom/history")
    service = ArchiveService(tmp_path, config)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
        session_id=session_id,
        project_id="test-project",
        content="Test",
    )

    result = await service.archive_interaction(event)

    assert result.outcome == WriteOutcome.WRITTEN
    assert (tmp_path / "custom" / "history").exists()


@pytest.mark.asyncio
async def test_recovery_can_navigate_to_archive(tmp_path: Path):
    """I-09: Archive pointers enable recovery navigation."""
    session_id = uuid4()
    config = ArchiveConfig()
    service = ArchiveService(tmp_path, config)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
        session_id=session_id,
        project_id="test-project",
        content="Important decision context",
    )

    result = await service.archive_interaction(event)

    from execution_core.domain.checkpoint import (
        ArchiveReference,
        Checkpoint,
    )
    from execution_core.domain.enums import LifecycleState

    archive_ref = ArchiveReference(
        path=result.pointer.path,
        timestamp=result.pointer.timestamp,
        anchor=result.pointer.entry_id,
    )

    checkpoint = Checkpoint(
        session_id=session_id,
        lifecycle_state=LifecycleState.EXECUTE,
        restart_action="Resume work",
        archive_references=[archive_ref],
    )

    assert len(checkpoint.archive_references) == 1
    assert checkpoint.archive_references[0].path == result.pointer.path
    assert checkpoint.archive_references[0].anchor == result.pointer.entry_id

    archive_file = tmp_path / result.pointer.path
    content = archive_file.read_text()
    assert result.pointer.entry_id in content
    assert "Important decision context" in content


@pytest.mark.asyncio
async def test_append_only_never_overwrites(tmp_path: Path):
    """I-04: Corrections are new entries, never overwrite."""
    session_id = uuid4()
    config = ArchiveConfig()
    service = ArchiveService(tmp_path, config)

    original_event = ArchiveEvent(
        actor=Actor.USER,
        time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
        session_id=session_id,
        project_id="test-project",
        content="Original incorrect instruction",
    )
    original_result = await service.archive_interaction(original_event)

    correction_event = ArchiveEvent(
        actor=Actor.USER,
        time=datetime(2026, 8, 19, 12, 35, 0, tzinfo=UTC),
        session_id=session_id,
        project_id="test-project",
        content="Correction: actually do something else",
    )
    await service.archive_interaction(correction_event)

    session_file = tmp_path / original_result.pointer.path
    content = session_file.read_text()

    assert "Original incorrect instruction" in content
    assert "Correction: actually do something else" in content

    original_idx = content.index("Original incorrect instruction")
    correction_idx = content.index("Correction: actually do something else")
    assert original_idx < correction_idx
