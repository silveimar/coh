"""Markdown formatting and append-only behavior tests."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from coh_archive import (
    Actor,
    ArchiveConfig,
    ArchiveEvent,
    EventStatus,
    ToolEvent,
)
from coh_archive.markdown import MarkdownArchiveWriter


@pytest.mark.asyncio
async def test_write_creates_file_with_front_matter(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """First write creates file with YAML front matter."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig()
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test user message",
    )

    pointer, _ = await writer.write_event(event)

    session_file = tmp_path / pointer.path
    assert session_file.exists()

    content = session_file.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "schema_version: 1.0.0" in content
    assert f"session_id: {session_id}" in content
    assert f"project_id: {project_id}" in content


@pytest.mark.asyncio
async def test_append_preserves_previous_entries(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Second write appends without overwriting first entry."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig()
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    event1 = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="First message",
    )
    pointer1, _ = await writer.write_event(event1)

    event2 = ArchiveEvent(
        actor=Actor.AGENT,
        time=datetime(2026, 8, 19, 12, 35, 0, tzinfo=UTC),
        session_id=session_id,
        project_id=project_id,
        content="Agent response",
    )
    pointer2, _ = await writer.write_event(event2)

    session_file = tmp_path / pointer1.path
    content = session_file.read_text(encoding="utf-8")

    assert "First message" in content
    assert "Agent response" in content
    assert content.index("First message") < content.index("Agent response")


@pytest.mark.asyncio
async def test_entry_has_closing_delimiter(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Entries have closing delimiter for incomplete-entry detection."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig()
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Test message",
    )
    pointer, _ = await writer.write_event(event)

    session_file = tmp_path / pointer.path
    content = session_file.read_text(encoding="utf-8")

    assert "---entry-end---" in content


@pytest.mark.asyncio
async def test_tool_event_with_inline_payloads(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Tool event with small payloads writes inline."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig(max_inline_payload_bytes=1024 * 100)
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    tool_event = ToolEvent(
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        tool_name="test_tool",
        status=EventStatus.SUCCEEDED,
        invocation_time=timestamp,
        result_time=datetime(2026, 8, 19, 12, 35, 0, tzinfo=UTC),
        input_payload={"key": "value"},
        output_payload={"result": "success"},
    )

    pointer, artifacts = await writer.write_tool_event(tool_event)

    session_file = tmp_path / pointer.path
    content = session_file.read_text(encoding="utf-8")

    assert '"key": "value"' in content
    assert '"result": "success"' in content
    assert len(artifacts) == 0


@pytest.mark.asyncio
async def test_tool_event_spills_large_payloads(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Tool event with large payloads writes to artifact files."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig(max_inline_payload_bytes=50)
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    large_payload = {"data": "x" * 1000}

    tool_event = ToolEvent(
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        tool_name="test_tool",
        status=EventStatus.SUCCEEDED,
        invocation_time=timestamp,
        input_payload=large_payload,
    )

    pointer, artifacts = await writer.write_tool_event(tool_event)

    assert len(artifacts) > 0
    artifact_path = archive_dir / artifacts[0]
    assert artifact_path.exists()

    artifact_data = json.loads(artifact_path.read_text())
    assert artifact_data == large_payload


@pytest.mark.asyncio
async def test_rotation_creates_new_file(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Archive rotates to new file when size exceeds threshold."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig(rotation_threshold_bytes=500)
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    for _i in range(5):
        event = ArchiveEvent(
            actor=Actor.USER,
            time=timestamp,
            session_id=session_id,
            project_id=project_id,
            content="x" * 200,
        )
        pointer, _ = await writer.write_event(event)

    archive_files = list(archive_dir.glob("*.md"))
    assert len(archive_files) > 1
    assert any("-part-" in f.name for f in archive_files)


@pytest.mark.asyncio
async def test_entry_id_is_stable_anchor(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Entry ID is stable and suitable as markdown anchor."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig()
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    event = ArchiveEvent(
        actor=Actor.USER,
        time=timestamp,
        session_id=session_id,
        project_id=project_id,
        content="Anchor test",
    )
    pointer, _ = await writer.write_event(event)

    assert pointer.entry_id.startswith("user-")
    assert len(pointer.entry_id.split("-")) >= 3


@pytest.mark.asyncio
async def test_concurrent_writes_serialized(
    tmp_path: Path, session_id, project_id: str, timestamp: datetime
):
    """Concurrent writes to same session are serialized."""
    archive_dir = tmp_path / ".coh" / "archive"
    config = ArchiveConfig()
    writer = MarkdownArchiveWriter(archive_dir, config, tmp_path)

    async def write_event(content: str):
        event = ArchiveEvent(
            actor=Actor.USER,
            time=timestamp,
            session_id=session_id,
            project_id=project_id,
            content=content,
        )
        return await writer.write_event(event)

    results = await asyncio.gather(
        write_event("Message 1"),
        write_event("Message 2"),
        write_event("Message 3"),
    )

    session_file = tmp_path / results[0][0].path
    content = session_file.read_text(encoding="utf-8")

    assert "Message 1" in content
    assert "Message 2" in content
    assert "Message 3" in content
    assert content.count("---entry-end---") == 3
