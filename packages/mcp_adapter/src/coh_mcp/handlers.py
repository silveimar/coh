"""MCP tool handlers implementing the execution core integration."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from coh_archive import ArchiveConfig, ArchiveService
from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.enums import (
    ArchiveStatus,
    Clarity,
    LifecycleState,
    Readiness,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification

from .archive_wiring import ArchiveCheckpointWiring
from .errors import CapabilityNotImplementedError
from .types import ArchiveIntegration

logger = logging.getLogger(__name__)


class COHHandlers:
    """
    MCP tool handlers integrating execution core + archive.

    Implements I-06 (proposal-only), I-07 (diagnosis-free), I-14 (NOT_IMPLEMENTED).
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.sessions: dict[UUID, ExecutionSession] = {}
        self.checkpoints: dict[UUID, Checkpoint] = {}

        archive_config = ArchiveConfig(enabled=True, directory=".coh/archive")
        archive_service = ArchiveService(project_root, archive_config)
        self.archive_wiring = ArchiveCheckpointWiring(archive_service)

    async def create_session(
        self, project_id: str, user_input: str, intent: str | None = None
    ) -> list[dict]:
        """
        Create new COH session with intent inference.

        Archives user input and transitions to INSPECT.
        """
        session_id = uuid4()

        if intent is None:
            intent = self._infer_intent(user_input)

        session = ExecutionSession(
            id=session_id,
            project_id=project_id,
            intent=SessionIntent(intent),
            lifecycle_state=LifecycleState.INSPECT,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self.sessions[session_id] = session

        checkpoint = Checkpoint(
            id=uuid4(),
            session_id=session_id,
            lifecycle_state=LifecycleState.INSPECT,
            restart_action="Begin repository inspection",
        )
        self.checkpoints[session_id] = checkpoint

        await self.archive_wiring.archive_user_input(
            session_id, project_id, user_input, checkpoint
        )

        archive_status = checkpoint.archive_status.value
        return [
            {
                "type": "text",
                "text": (
                    f"Session created: {session_id}\nIntent: {intent}\n"
                    f"State: INSPECT\n\nArchive status: {archive_status}"
                ),
            }
        ]

    async def inspect_repository(
        self, session_id: str, patterns: list[str] | None = None
    ) -> list[dict]:
        """
        I-14: Inspection capability not implemented.

        Returns NOT_IMPLEMENTED with focused request for inspection context.
        """
        raise CapabilityNotImplementedError(
            capability="repository_inspection",
            context_needed=(
                "File patterns, code structure, test coverage, "
                "or specific inspection targets"
            ),
        )

    async def specify_work(
        self,
        session_id: str,
        what: str,
        why: str,
        deliverable: str,
        done_when: list[str],
        inspection_findings: str | None = None,
    ) -> list[dict]:
        """
        Specify work: derive and propose specification.

        Transitions INSPECT → SPECIFY → CONFIRM.
        Uses prose renderer to ensure P-01 (inspection findings before spec block).
        """
        from coh_prose import ProseRenderer, SpecProposal

        session_uuid = UUID(session_id)
        session = self.sessions.get(session_uuid)
        if not session:
            return [{"type": "text", "text": f"Session not found: {session_id}"}]

        done_when_criteria = [
            DoneWhenCriterion(text=criterion) for criterion in done_when
        ]

        spec = Specification(
            id=uuid4(),
            session_id=session_uuid,
            revision=1,
            what=what,
            why=why,
            deliverable=deliverable,
            done_when=done_when_criteria,
            clarity=Clarity.READY,
            readiness=Readiness.READY,
        )

        session.lifecycle_state = LifecycleState.CONFIRM
        session.updated_at = datetime.now(UTC)

        checkpoint = self.checkpoints.get(session_uuid)
        if checkpoint:
            checkpoint.lifecycle_state = LifecycleState.CONFIRM
            checkpoint.spec_id = spec.id
            checkpoint.spec_revision = spec.revision

        renderer = ProseRenderer()
        spec_proposal = SpecProposal(
            inspection_findings=inspection_findings,
            what=what,
            why=why,
            deliverable=deliverable,
            done_when=done_when,
            clarity=spec.clarity.value,
            readiness=spec.readiness.value,
        )

        rendered = renderer.render_spec_proposal(spec_proposal)

        await self.archive_wiring.archive_agent_output(
            session_uuid,
            session.project_id,
            rendered,
            checkpoint,
            state_transition="INSPECT→SPECIFY→CONFIRM",
        )

        return [
            {
                "type": "text",
                "text": rendered,
            }
        ]

    async def confirm_spec(
        self, session_id: str, confirmed: bool, corrections: dict | None = None
    ) -> list[dict]:
        """Confirm or correct specification."""
        session_uuid = UUID(session_id)
        session = self.sessions.get(session_uuid)
        if not session:
            return [{"type": "text", "text": f"Session not found: {session_id}"}]

        if confirmed:
            session.lifecycle_state = LifecycleState.PLAN
            session.updated_at = datetime.now(UTC)

            checkpoint = self.checkpoints.get(session_uuid)
            if checkpoint:
                checkpoint.lifecycle_state = LifecycleState.PLAN

            return [
                {
                    "type": "text",
                    "text": (
                        "Spec confirmed. Transition: CONFIRM → PLAN\n\n"
                        "Ready to create executable plan."
                    ),
                }
            ]
        else:
            return [
                {
                    "type": "text",
                    "text": (
                        "Spec correction required. Transition: CONFIRM → SPECIFY\n\n"
                        "Provide corrected fields."
                    ),
                }
            ]

    async def create_checkpoint(
        self,
        session_id: str,
        restart_action: str,
        reason: str | None = None,
    ) -> list[dict]:
        """
        Create checkpoint for recovery (I-09).

        Stores restart_action + archive references; checkpoint provenance.
        """
        session_uuid = UUID(session_id)
        session = self.sessions.get(session_uuid)
        if not session:
            return [{"type": "text", "text": f"Session not found: {session_id}"}]

        checkpoint = Checkpoint(
            id=uuid4(),
            session_id=session_uuid,
            lifecycle_state=session.lifecycle_state,
            restart_action=restart_action,
            checkpoint_reason=reason or "manual",
        )

        self.checkpoints[session_uuid] = checkpoint

        state = checkpoint.lifecycle_state.value
        archive_status = checkpoint.archive_status.value
        return [
            {
                "type": "text",
                "text": (
                    f"Checkpoint created: {checkpoint.id}\nState: {state}\n"
                    f"Restart action: {restart_action}\n"
                    f"Archive status: {archive_status}"
                ),
            }
        ]

    async def recover_session(self, session_id: str) -> list[dict]:
        """
        Recover from latest checkpoint (I-09).

        Renders recovery summary with P-06 exemption (prospective framing allowed).
        """
        from coh_prose import ProseRenderer
        from coh_prose import RecoverySummary as ProseRecoverySummary

        session_uuid = UUID(session_id)
        checkpoint = self.checkpoints.get(session_uuid)

        if not checkpoint:
            return [{"type": "text", "text": f"No checkpoint found for: {session_id}"}]

        recovery = ProseRecoverySummary(
            goal="Restore session context",
            why="Resume work after interruption",
            restart_action=checkpoint.restart_action,
            archive_degraded=(checkpoint.archive_status == ArchiveStatus.DEGRADED),
        )

        renderer = ProseRenderer()
        rendered = renderer.render_recovery_summary(recovery)

        return [
            {
                "type": "text",
                "text": rendered,
            }
        ]

    async def get_archive_status(self) -> list[dict]:
        """Get archive integration health (I-12: degradation visibility)."""
        stats = self.archive_wiring.get_stats()

        integration = ArchiveIntegration(
            enabled=stats["enabled"],  # type: ignore
            writes_succeeded=stats["writes_succeeded"],  # type: ignore
            writes_failed=stats["writes_failed"],  # type: ignore
            last_failure=stats["last_failure"],  # type: ignore
        )

        status_text = f"""Archive Integration Status

Enabled: {integration.enabled}
Writes succeeded: {integration.writes_succeeded}
Writes failed: {integration.writes_failed}
"""

        if integration.last_failure:
            status_text += f"\nLast failure: {integration.last_failure}"

        return [
            {
                "type": "text",
                "text": status_text,
            }
        ]

    def _infer_intent(self, user_input: str) -> str:
        """Infer intent from user input (T1)."""
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["recover", "resume", "restore"]):
            return "recover"
        elif any(word in user_lower for word in ["review", "check", "evaluate"]):
            return "review"
        elif any(word in user_lower for word in ["plan", "design", "architect"]):
            return "plan"
        elif any(word in user_lower for word in ["brainstorm", "ideate", "explore"]):
            return "brainstorm"
        elif any(word in user_lower for word in ["learn", "study", "understand"]):
            return "study"
        else:
            return "execute"
