"""Archive/checkpoint wiring implementing I-12 degrade-and-continue."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from coh_archive import (
    Actor,
    ArchiveEvent,
    ArchivePointer,
    ArchiveService,
    ToolEvent,
    WriteOutcome,
)
from execution_core.domain.checkpoint import ArchiveReference, Checkpoint

logger = logging.getLogger(__name__)


class ArchiveCheckpointWiring:
    """
    Wires archive writes to checkpoint degradation (I-12).

    This is the product wiring that PR #3 left as next actions:
    - User/agent/tool events → ArchiveService.archive_interaction / archive_tool_event
    - On WriteOutcome.ARCHIVE_WRITE_FAILED → Checkpoint.mark_degraded
    - Successful writes → store ArchiveReference on checkpoint
    """

    def __init__(self, archive_service: ArchiveService):
        self.archive_service = archive_service
        self.writes_succeeded = 0
        self.writes_failed = 0
        self.last_failure: str | None = None

    async def archive_user_input(
        self,
        session_id: UUID,
        project_id: str,
        content: str,
        checkpoint: Checkpoint | None = None,
    ) -> ArchivePointer | None:
        """
        Archive user input, wiring to checkpoint on failure.

        Returns ArchivePointer on success, None on failure (checkpoint marked degraded).
        """
        event = ArchiveEvent(
            actor=Actor.USER,
            time=datetime.now(UTC),
            session_id=session_id,
            project_id=project_id,
            content=content,
        )

        result = await self.archive_service.archive_interaction(event)

        if result.outcome == WriteOutcome.WRITTEN:
            self.writes_succeeded += 1
            if checkpoint and result.pointer:
                self._store_reference(checkpoint, result.pointer)
            return result.pointer

        elif result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
            self.writes_failed += 1
            self.last_failure = result.error
            if checkpoint:
                checkpoint.mark_degraded()
            logger.warning(
                "Archive write failed (degraded): %s",
                result.error,
                extra={"session_id": str(session_id)},
            )
            return None

        return None

    async def archive_agent_output(
        self,
        session_id: UUID,
        project_id: str,
        content: str,
        checkpoint: Checkpoint | None = None,
        state_transition: str | None = None,
    ) -> ArchivePointer | None:
        """
        Archive agent output, wiring to checkpoint on failure.

        Returns ArchivePointer on success, None on failure (checkpoint marked degraded).
        """
        event = ArchiveEvent(
            actor=Actor.AGENT,
            time=datetime.now(UTC),
            session_id=session_id,
            project_id=project_id,
            content=content,
            state_transition=state_transition,
        )

        result = await self.archive_service.archive_interaction(event)

        if result.outcome == WriteOutcome.WRITTEN:
            self.writes_succeeded += 1
            if checkpoint and result.pointer:
                self._store_reference(checkpoint, result.pointer)
            return result.pointer

        elif result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
            self.writes_failed += 1
            self.last_failure = result.error
            if checkpoint:
                checkpoint.mark_degraded()
            logger.warning(
                "Archive write failed (degraded): %s",
                result.error,
                extra={"session_id": str(session_id)},
            )
            return None

        return None

    async def archive_tool_invocation(
        self,
        session_id: UUID,
        project_id: str,
        tool_name: str,
        checkpoint: Checkpoint | None = None,
        **tool_data: object,
    ) -> ArchivePointer | None:
        """
        Archive tool invocation, wiring to checkpoint on failure.

        Returns ArchivePointer on success, None on failure (checkpoint marked degraded).
        """
        from coh_archive import EventStatus

        event = ToolEvent(
            actor=Actor.TOOL,
            time=datetime.now(UTC),
            session_id=session_id,
            project_id=project_id,
            tool_name=tool_name,
            status=EventStatus.SUCCEEDED,
            invocation_time=datetime.now(UTC),
            result_time=datetime.now(UTC),
            input_payload=tool_data.get("input_payload"),  # type: ignore
            output_payload=tool_data.get("output_payload"),  # type: ignore
        )

        result = await self.archive_service.archive_tool_event(event)

        if result.outcome == WriteOutcome.WRITTEN:
            self.writes_succeeded += 1
            if checkpoint and result.pointer:
                self._store_reference(checkpoint, result.pointer)
            return result.pointer

        elif result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
            self.writes_failed += 1
            self.last_failure = result.error
            if checkpoint:
                checkpoint.mark_degraded()
            logger.warning(
                "Archive write failed (degraded): %s",
                result.error,
                extra={"session_id": str(session_id), "tool_name": tool_name},
            )
            return None

        return None

    def _store_reference(self, checkpoint: Checkpoint, pointer: ArchivePointer) -> None:
        """Store archive reference on checkpoint."""
        ref = ArchiveReference(
            path=pointer.path,
            timestamp=pointer.timestamp,
            anchor=pointer.entry_id,
        )
        checkpoint.archive_references.append(ref)

    def get_stats(self) -> dict[str, object]:
        """Get archive integration statistics."""
        return {
            "enabled": self.archive_service.config.enabled,
            "writes_succeeded": self.writes_succeeded,
            "writes_failed": self.writes_failed,
            "last_failure": self.last_failure,
        }
