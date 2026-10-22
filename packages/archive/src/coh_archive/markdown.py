"""Markdown archive writer with append-only semantics."""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from .models import (
    ArchiveConfig,
    ArchiveEvent,
    ArchivePointer,
    ToolEvent,
)
from .paths import (
    generate_artifact_filename,
    generate_entry_id,
    generate_session_filename,
)


class MarkdownArchiveWriter:
    """Append-only Markdown archive writer with per-session serialization."""

    def __init__(self, archive_dir: Path, config: ArchiveConfig, project_root: Path):
        """
        Initialize writer.

        Args:
            archive_dir: Resolved archive directory
            config: Archive configuration
            project_root: Project root directory for relative paths
        """
        self.archive_dir = archive_dir
        self.config = config
        self.project_root = project_root
        self._session_locks: dict[UUID, asyncio.Lock] = {}

    def _get_session_lock(self, session_id: UUID) -> asyncio.Lock:
        """Get or create lock for session to serialize writes."""
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    def _get_session_file_path(
        self, session_id: UUID, timestamp: datetime, part: int | None = None
    ) -> Path:
        """Get path to session archive file."""
        filename = generate_session_filename(session_id, timestamp, part)
        return self.archive_dir / filename

    def _find_current_session_file(
        self, session_id: UUID, timestamp: datetime
    ) -> tuple[Path, int | None]:
        """
        Find current session file, checking rotation.

        Returns:
            (file_path, part_number)
        """
        base_file = self._get_session_file_path(session_id, timestamp)

        if not base_file.exists():
            return base_file, None

        if (
            self.config.rotation_threshold_bytes > 0
            and base_file.stat().st_size < self.config.rotation_threshold_bytes
        ):
            return base_file, None

        part = 1
        while True:
            part_file = self._get_session_file_path(session_id, timestamp, part)
            if not part_file.exists():
                return part_file, part
            if part_file.stat().st_size < self.config.rotation_threshold_bytes:
                return part_file, part
            part += 1

    def _create_front_matter(
        self, session_id: UUID, project_id: str, created: datetime
    ) -> str:
        """Create YAML front matter for session file."""
        front_matter = {
            "schema_version": "1.0.0",
            "session_id": str(session_id),
            "project_id": project_id,
            "created_at": created.isoformat(),
            "last_updated_at": created.isoformat(),
        }
        return "---\n" + yaml.dump(front_matter, sort_keys=False) + "---\n\n"

    def _update_front_matter(self, content: str, last_updated: datetime) -> str:
        """Update last_updated_at in existing front matter."""
        if not content.startswith("---\n"):
            return content

        end_marker = content.find("\n---\n", 4)
        if end_marker == -1:
            return content

        front_matter_str = content[4:end_marker]
        try:
            front_matter = yaml.safe_load(front_matter_str)
            front_matter["last_updated_at"] = last_updated.isoformat()
            updated_yaml = yaml.dump(front_matter, sort_keys=False)
            return f"---\n{updated_yaml}---\n{content[end_marker + 5 :]}"
        except yaml.YAMLError:
            return content

    def _format_event_entry(
        self,
        entry_id: str,
        event: ArchiveEvent | ToolEvent,
        artifact_refs: list[str] | None = None,
    ) -> str:
        """
        Format event as Markdown entry.

        Args:
            entry_id: Stable entry ID
            event: Event to format
            artifact_refs: Optional artifact file references

        Returns:
            Formatted Markdown entry
        """
        metadata: dict[str, Any] = {
            "id": entry_id,
            "actor": event.actor.value,
            "time": event.time.isoformat(),
            "session_id": str(event.session_id),
            "project_id": event.project_id,
        }

        if isinstance(event, ToolEvent):
            metadata["tool_name"] = event.tool_name
            metadata["status"] = event.status.value
            metadata["invocation_time"] = event.invocation_time.isoformat()
            if event.result_time:
                metadata["result_time"] = event.result_time.isoformat()
            if artifact_refs:
                metadata["artifact_paths"] = artifact_refs
        else:
            if event.goal_id:
                metadata["goal_id"] = str(event.goal_id)
            if event.task_id:
                metadata["task_id"] = str(event.task_id)
            if event.state_transition:
                metadata["state_transition"] = event.state_transition
            if event.checkpoint_id:
                metadata["checkpoint_id"] = str(event.checkpoint_id)

        metadata_yaml = yaml.dump(metadata, sort_keys=False)

        if isinstance(event, ToolEvent):
            content_lines = []
            if event.input_payload:
                content_lines.append(
                    "**Input:**\n```json\n"
                    f"{json.dumps(event.input_payload, indent=2)}\n```\n"
                )
            if event.output_payload:
                content_lines.append(
                    "**Output:**\n```json\n"
                    f"{json.dumps(event.output_payload, indent=2)}\n```"
                )
            content = "\n".join(content_lines) if content_lines else ""
        else:
            content = f"```text\n{event.content}\n```"

        return (
            f"### {entry_id}\n\n```yaml\n{metadata_yaml}```\n\n{content}\n\n"
            "---entry-end---\n\n"
        )

    def _write_artifact(self, artifact_path: Path, payload: dict[str, object]) -> None:
        """Write large payload to artifact file."""
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=artifact_path.parent,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp, indent=2)
            tmp_path = Path(tmp.name)

        tmp_path.replace(artifact_path)

    async def write_event(
        self, event: ArchiveEvent
    ) -> tuple[ArchivePointer, list[str]]:
        """
        Write archive event (async version).

        Args:
            event: Event to write

        Returns:
            (archive_pointer, artifact_paths)

        Raises:
            OSError: On write failure
        """
        lock = self._get_session_lock(event.session_id)
        async with lock:
            return await asyncio.to_thread(self._write_event_sync, event)

    def _write_event_sync(
        self, event: ArchiveEvent
    ) -> tuple[ArchivePointer, list[str]]:
        """Synchronous event write implementation."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        entry_id = generate_entry_id(event.actor, event.time, event.content)
        session_file, _ = self._find_current_session_file(event.session_id, event.time)

        is_new_file = not session_file.exists()

        if is_new_file:
            content = self._create_front_matter(
                event.session_id, event.project_id, event.time
            )
        else:
            content = session_file.read_text(encoding="utf-8")
            content = self._update_front_matter(content, event.time)

        entry_markdown = self._format_event_entry(entry_id, event)

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.archive_dir,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as tmp:
            tmp.write(content)
            tmp.write(entry_markdown)
            tmp_path = Path(tmp.name)

        tmp_path.replace(session_file)

        pointer = ArchivePointer(
            path=str(session_file.relative_to(self.project_root)),
            entry_id=entry_id,
            timestamp=event.time,
        )

        return pointer, []

    async def write_tool_event(
        self, event: ToolEvent
    ) -> tuple[ArchivePointer, list[str]]:
        """
        Write tool event with optional artifact spill.

        Args:
            event: Tool event to write

        Returns:
            (archive_pointer, artifact_paths)

        Raises:
            OSError: On write failure
        """
        lock = self._get_session_lock(event.session_id)
        async with lock:
            return await asyncio.to_thread(self._write_tool_event_sync, event)

    def _write_tool_event_sync(
        self, event: ToolEvent
    ) -> tuple[ArchivePointer, list[str]]:
        """Synchronous tool event write implementation."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        entry_id = generate_entry_id(event.actor, event.time, event.tool_name)
        artifact_refs: list[str] = []

        if event.input_payload:
            input_json = json.dumps(event.input_payload, indent=2)
            if len(input_json) > self.config.max_inline_payload_bytes:
                artifact_name = generate_artifact_filename(entry_id, "input", "json")
                artifact_path = self.archive_dir / artifact_name
                self._write_artifact(artifact_path, event.input_payload)
                artifact_refs.append(artifact_name)
                event.input_payload = None

        if event.output_payload:
            output_json = json.dumps(event.output_payload, indent=2)
            if len(output_json) > self.config.max_inline_payload_bytes:
                artifact_name = generate_artifact_filename(entry_id, "output", "json")
                artifact_path = self.archive_dir / artifact_name
                self._write_artifact(artifact_path, event.output_payload)
                artifact_refs.append(artifact_name)
                event.output_payload = None

        session_file, _ = self._find_current_session_file(event.session_id, event.time)
        is_new_file = not session_file.exists()

        if is_new_file:
            content = self._create_front_matter(
                event.session_id, event.project_id, event.time
            )
        else:
            content = session_file.read_text(encoding="utf-8")
            content = self._update_front_matter(content, event.time)

        entry_markdown = self._format_event_entry(
            entry_id, event, artifact_refs or None
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.archive_dir,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as tmp:
            tmp.write(content)
            tmp.write(entry_markdown)
            tmp_path = Path(tmp.name)

        tmp_path.replace(session_file)

        pointer = ArchivePointer(
            path=str(session_file.relative_to(self.project_root)),
            entry_id=entry_id,
            timestamp=event.time,
        )

        return pointer, artifact_refs
