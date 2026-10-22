"""Archive service with degrade-and-continue semantics."""

import logging
from pathlib import Path
from typing import Any

from .markdown import MarkdownArchiveWriter
from .models import (
    ArchiveConfig,
    ArchiveEvent,
    ArchiveWriteResult,
    ToolEvent,
    WriteOutcome,
)
from .paths import PathResolutionError, resolve_archive_directory

logger = logging.getLogger(__name__)


class ArchiveService:
    """
    Archive service implementing I-04 (append-only) and I-12 (degrade-and-continue).

    Archive write failures never block workflow; in-memory data is preserved,
    and checkpoint records degraded status.
    """

    def __init__(self, project_root: Path, config: ArchiveConfig):
        """
        Initialize archive service.

        Args:
            project_root: Project root directory
            config: Archive configuration
        """
        self.project_root = project_root
        self.config = config
        self._writer: MarkdownArchiveWriter | None = None
        self._archive_dir: Path | None = None

    def _ensure_writer(self) -> MarkdownArchiveWriter:
        """Lazy-initialize writer, resolving archive directory once."""
        if self._writer is None:
            self._archive_dir = resolve_archive_directory(
                self.project_root, self.config
            )
            self._writer = MarkdownArchiveWriter(
                self._archive_dir, self.config, self.project_root
            )
        return self._writer

    async def archive_interaction(self, event: ArchiveEvent) -> ArchiveWriteResult:
        """
        Archive user or agent interaction event.

        Implements I-12: failures degrade-and-continue; never block workflow.

        Args:
            event: Archive event to write

        Returns:
            ArchiveWriteResult with outcome and optional pointer
        """
        if not self.config.enabled:
            return ArchiveWriteResult(
                outcome=WriteOutcome.SKIPPED_DISABLED,
                project_root=self.project_root,
            )

        try:
            writer = self._ensure_writer()
            pointer, _ = await writer.write_event(event)

            return ArchiveWriteResult(
                outcome=WriteOutcome.WRITTEN,
                pointer=pointer,
                project_root=self.project_root,
                resolved_path=self._archive_dir,
            )
        except PathResolutionError as e:
            logger.warning(
                "Archive path resolution failed: %s",
                str(e),
                extra={"session_id": str(event.session_id)},
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Path resolution failed: {e}",
                project_root=self.project_root,
            )
        except OSError as e:
            logger.warning(
                "Archive write failed (non-blocking): %s",
                str(e),
                extra={
                    "session_id": str(event.session_id),
                    "resolved_path": str(self._archive_dir)
                    if self._archive_dir
                    else None,
                },
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Write failed: {e}",
                project_root=self.project_root,
                resolved_path=self._archive_dir,
            )
        except Exception as e:
            logger.exception(
                "Unexpected archive write failure (non-blocking)",
                extra={"session_id": str(event.session_id)},
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Unexpected error: {e}",
                project_root=self.project_root,
            )

    async def archive_tool_event(self, event: ToolEvent) -> ArchiveWriteResult:
        """
        Archive tool invocation event.

        Implements I-12: failures degrade-and-continue; never block workflow.

        Args:
            event: Tool event to write

        Returns:
            ArchiveWriteResult with outcome and optional pointer
        """
        if not self.config.enabled:
            return ArchiveWriteResult(
                outcome=WriteOutcome.SKIPPED_DISABLED,
                project_root=self.project_root,
            )

        try:
            writer = self._ensure_writer()
            pointer, _ = await writer.write_tool_event(event)

            return ArchiveWriteResult(
                outcome=WriteOutcome.WRITTEN,
                pointer=pointer,
                project_root=self.project_root,
                resolved_path=self._archive_dir,
            )
        except PathResolutionError as e:
            logger.warning(
                "Archive path resolution failed: %s",
                str(e),
                extra={"session_id": str(event.session_id)},
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Path resolution failed: {e}",
                project_root=self.project_root,
            )
        except OSError as e:
            logger.warning(
                "Archive write failed (non-blocking): %s",
                str(e),
                extra={
                    "session_id": str(event.session_id),
                    "tool_name": event.tool_name,
                    "resolved_path": str(self._archive_dir)
                    if self._archive_dir
                    else None,
                },
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Write failed: {e}",
                project_root=self.project_root,
                resolved_path=self._archive_dir,
            )
        except Exception as e:
            logger.exception(
                "Unexpected archive write failure (non-blocking)",
                extra={
                    "session_id": str(event.session_id),
                    "tool_name": event.tool_name,
                },
            )
            return ArchiveWriteResult(
                outcome=WriteOutcome.ARCHIVE_WRITE_FAILED,
                error=f"Unexpected error: {e}",
                project_root=self.project_root,
            )

    def read_session_archive(
        self, session_file: Path
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Read and parse session archive file.

        Args:
            session_file: Path to session archive file

        Returns:
            (front_matter_dict, entry_list)

        Raises:
            FileNotFoundError: If session file doesn't exist
            ValueError: If front matter is malformed
        """
        if not session_file.exists():
            raise FileNotFoundError(f"Session archive not found: {session_file}")

        content = session_file.read_text(encoding="utf-8")

        if not content.startswith("---\n"):
            raise ValueError("Archive file missing front matter")

        end_marker = content.find("\n---\n", 4)
        if end_marker == -1:
            raise ValueError("Archive file malformed: no front matter end")

        import yaml

        front_matter_str = content[4:end_marker]
        front_matter = yaml.safe_load(front_matter_str)

        entries_content = content[end_marker + 5 :]
        entries = []

        for entry in entries_content.split("---entry-end---"):
            entry = entry.strip()
            if entry and entry.startswith("###"):
                entries.append(entry)

        return front_matter, entries
