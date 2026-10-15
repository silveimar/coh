"""Archive service tests including I-12 degrade-and-continue."""

from datetime import UTC, datetime
from pathlib import Path

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
async def test_archive_disabled_returns_skipped(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """Disabled archive returns SKIPPED_DISABLED without filesystem access."""
    config = ArchiveConfig(enabled=False)
    service = ArchiveService(project_root, config)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test message",
    )

    result = await service.archive_interaction(event)

    assert result.outcome == WriteOutcome.SKIPPED_DISABLED
    assert result.pointer is None


@pytest.mark.asyncio
async def test_successful_write_returns_pointer(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """Successful write returns WRITTEN with archive pointer."""
    config = ArchiveConfig()
    service = ArchiveService(project_root, config)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test message",
    )

    result = await service.archive_interaction(event)

    assert result.outcome == WriteOutcome.WRITTEN
    assert result.pointer is not None
    assert result.pointer.entry_id.startswith("user-")


@pytest.mark.asyncio
async def test_write_failure_degrades_non_blocking(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """I-12: Write failure returns ARCHIVE_WRITE_FAILED, non-blocking."""
    archive_dir = project_root / ".coh" / "archive"
    archive_dir.mkdir(parents=True)
    archive_dir.chmod(0o000)

    try:
        config = ArchiveConfig()
        service = ArchiveService(project_root, config)

        event = ArchiveEvent(
            actor=Actor.USER,
            time=timestamp,
            session_id=session_id,
            project_id=project_id,
            content="Test message",
        )

        result = await service.archive_interaction(event)

        assert result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED
        assert result.error is not None
        assert "Write failed" in result.error or "Permission" in result.error
        assert result.pointer is None
    finally:
        archive_dir.chmod(0o755)


@pytest.mark.asyncio
async def test_path_resolution_failure_degrades(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """I-12: Path resolution failure returns ARCHIVE_WRITE_FAILED."""
    config = ArchiveConfig(
        directory="/absolute/external/path", allow_external_path=False
    )
    service = ArchiveService(project_root, config)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test message",
    )

    result = await service.archive_interaction(event)

    assert result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED
    assert "Path resolution failed" in result.error


@pytest.mark.asyncio
async def test_tool_event_write_success(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """Tool event archival succeeds."""
    config = ArchiveConfig()
    service = ArchiveService(project_root, config)

    tool_event = ToolEvent(
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        tool_name="test_tool",
        status=EventStatus.SUCCEEDED,
        invocation_time=timestamp,
        input_payload={"key": "value"},
    )

    result = await service.archive_tool_event(tool_event)

    assert result.outcome == WriteOutcome.WRITTEN
    assert result.pointer is not None


@pytest.mark.asyncio
async def test_read_session_archive(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """Read session archive returns front matter and entries."""
    config = ArchiveConfig()
    service = ArchiveService(project_root, config)

    event1 = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="First message",
    )
    result1 = await service.archive_interaction(event1)

    event2 = ArchiveEvent(
        actor=Actor.AGENT,
        time=datetime(2026, 8, 19, 12, 35, 0, tzinfo=UTC),
        session_id=session_id,
        project_id=project_id,
        content="Agent response",
    )
    await service.archive_interaction(event2)

    session_file = project_root / result1.pointer.path

    front_matter, entries = service.read_session_archive(session_file)

    assert front_matter["session_id"] == str(session_id)
    assert front_matter["project_id"] == project_id
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_in_memory_data_preserved_on_failure(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """I-12: In-memory event data is preserved despite archive failure."""
    archive_dir = project_root / ".coh" / "archive"
    archive_dir.mkdir(parents=True)
    archive_dir.chmod(0o000)

    try:
        config = ArchiveConfig()
        service = ArchiveService(project_root, config)

        original_content = "Important user message that must not be lost"
        event = ArchiveEvent(
            actor=Actor.USER,
            time=timestamp,
            session_id=session_id,
            project_id=project_id,
            content=original_content,
        )

        result = await service.archive_interaction(event)

        assert result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED
        assert event.content == original_content
        assert event.actor == Actor.USER
        assert event.session_id == session_id
    finally:
        archive_dir.chmod(0o755)


@pytest.mark.asyncio
async def test_lazy_writer_initialization(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """Writer is initialized lazily on first write."""
    config = ArchiveConfig()
    service = ArchiveService(project_root, config)

    assert service._writer is None
    assert service._archive_dir is None

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test",
    )
    await service.archive_interaction(event)

    assert service._writer is not None
    assert service._archive_dir is not None


@pytest.mark.asyncio
async def test_multiple_events_append_chronologically(
    project_root: Path, session_id, project_id: str, timestamp: datetime
):
    """I-04: Multiple events append in chronological order, never overwrite."""
    config = ArchiveConfig()
    service = ArchiveService(project_root, config)

    events = [
        ArchiveEvent(
            actor=Actor.USER,
            time=datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC),
            session_id=session_id,
            project_id=project_id,
            content="First",
        ),
        ArchiveEvent(
            actor=Actor.AGENT,
            time=datetime(2026, 8, 19, 12, 35, 0, tzinfo=UTC),
            session_id=session_id,
            project_id=project_id,
            content="Second",
        ),
        ArchiveEvent(
            actor=Actor.USER,
            time=datetime(2026, 8, 19, 12, 35, 30, tzinfo=UTC),
            session_id=session_id,
            project_id=project_id,
            content="Third",
        ),
    ]

    pointers = []
    for event in events:
        result = await service.archive_interaction(event)
        assert result.outcome == WriteOutcome.WRITTEN
        pointers.append(result.pointer)

    session_file = project_root / pointers[0].path
    content = session_file.read_text(encoding="utf-8")

    first_idx = content.index("First")
    second_idx = content.index("Second")
    third_idx = content.index("Third")

    assert first_idx < second_idx < third_idx
    assert content.count("---entry-end---") == 3
