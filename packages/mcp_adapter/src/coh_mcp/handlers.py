"""MCP tool handlers implementing the execution core integration."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from coh_application import ForegroundService, SpecGateService
from coh_archive import ArchiveConfig, ArchiveService
from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.commands import Command
from execution_core.domain.enums import (
    LifecycleState,
    Readiness,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from execution_core.state_machine.lifecycle import StateMachine
from persistence.infrastructure.database import (
    create_engine,
    get_session_factory,
    init_db,
)
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

from .archive_wiring import ArchiveCheckpointWiring
from .errors import CapabilityNotImplementedError
from .types import ArchiveIntegration

logger = logging.getLogger(__name__)


class COHHandlers:
    """
    MCP tool handlers integrating execution core + persistence + archive.

    Implements I-06 (proposal-only), I-07 (diagnosis-free), I-14 (NOT_IMPLEMENTED).
    Uses SqlAlchemyUnitOfWork + SQLite WAL for persistence.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_machine = StateMachine()

        # Initialize persistence (SQLite WAL under project)
        db_path = project_root / ".coh" / "coh.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}")
        init_db(engine)
        self.session_factory = get_session_factory(engine)

        # Initialize archive
        archive_config = ArchiveConfig(enabled=True, directory=".coh/archive")
        archive_service = ArchiveService(project_root, archive_config)
        self.archive_wiring = ArchiveCheckpointWiring(archive_service)

    async def create_session(
        self, project_id: str, user_input: str, intent: str | None = None
    ) -> list[dict]:
        """
        Create new COH session with intent inference.

        T1: (session start) → INSPECT.
        Archives user input, persists session + initial checkpoint.
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

        checkpoint = Checkpoint(
            id=uuid4(),
            session_id=session_id,
            lifecycle_state=LifecycleState.INSPECT,
            restart_action="Begin repository inspection",
        )

        # Archive user input
        await self.archive_wiring.archive_user_input(
            session_id, project_id, user_input, checkpoint
        )

        # Persist session first (FK parent), then checkpoint (FK child)
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            uow.sessions.add(session)
            # UoW __exit__ commits on success

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            uow.checkpoints.add(checkpoint)
            # UoW __exit__ commits on success

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

        Uses SpecGateService.propose_spec (read-only, always permitted).
        Returns computed clarity/readiness + blockers.
        T2 findings_archived only True if archive write succeeded (fail closed).
        Persists spec and transitions INSPECT → SPECIFY → CONFIRM (T2 + T3).
        Uses prose renderer to ensure P-01 (inspection findings before spec block).
        """
        from coh_prose import ProseRenderer, SpecProposal

        session_uuid = UUID(session_id)

        # Load session + checkpoint from persistence
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(session_uuid)
            if not session:
                return [{"type": "text", "text": f"Session not found: {session_id}"}]

            checkpoint = uow.checkpoints.get_latest_for_session(session_uuid)

        # Archive inspection findings if provided and track success
        # T2 requires findings_archived=True:
        # - If no findings provided, treat as "nothing to archive" = True
        # - If findings provided, True only if archive write succeeded (fail closed)
        if inspection_findings:
            archive_pointer = await self.archive_wiring.archive_agent_output(
                session_uuid,
                session.project_id,
                f"Inspection findings:\n{inspection_findings}",
                checkpoint,
            )
            findings_archived = archive_pointer is not None
            # If archive failed, mark degraded and T2 will fail
            if not findings_archived and checkpoint:
                checkpoint.mark_degraded()
        else:
            # No findings to archive = success
            findings_archived = True

        # T2: INSPECT → SPECIFY (findings_archived only True if archive succeeded)
        command = Command(
            idempotency_key=f"specify-{session_uuid}-{datetime.now(UTC).isoformat()}",
            expected_version=session.version,
            source="user",
        )
        session = self.state_machine.transition_to_specify(
            session, findings_archived=findings_archived, command=command
        )

        # Persist session after T2
        expected_version = session.version - 1
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            uow.sessions.update(session, expected_version)

        # Propose spec via SpecGateService (computes clarity/readiness)
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            spec_gate = SpecGateService(uow)
            spec = spec_gate.propose_spec(
                session_id=session_uuid,
                what=what,
                why=why,
                deliverable=deliverable,
                done_when=done_when,
            )

        # Persist spec
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            uow.specifications.add(spec)

        # T3: SPECIFY → CONFIRM (link spec to session)
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(session_uuid)
            command = Command(
                idempotency_key=f"confirm-{session_uuid}-{datetime.now(UTC).isoformat()}",
                expected_version=session.version,
                source="user",
            )
            session = self.state_machine.transition_to_confirm(session, spec, command)
            expected_version = session.version - 1
            uow.sessions.update(session, expected_version)

        # Render spec proposal with P-01
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

        # Archive agent output
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
        """
        Confirm or correct specification (T4/T5).

        I-02: check_mutation_allowed first. If blocked, return error payload.
        If ready and confirmed=true, SpecGateService.confirm_spec + T4.
        If confirmed=false, propose revised spec (T5).
        """
        session_uuid = UUID(session_id)

        # I-02: Check readiness gate before mutation
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            spec_gate = SpecGateService(uow)
            allowed, state, blockers = spec_gate.check_mutation_allowed(session_uuid)

        if not allowed:
            # I-02: Blocked confirmation returns structured error, no T4
            blockers_text = "\n".join(f"- {b}" for b in blockers)
            return [
                {
                    "type": "text",
                    "text": (
                        f"Cannot confirm specification: "
                        f"readiness is {state.upper()}\n\n"
                        f"Blockers:\n{blockers_text}\n\n"
                        "Read-only inspection remains permitted."
                    ),
                }
            ]

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(session_uuid)
            if not session:
                return [{"type": "text", "text": f"Session not found: {session_id}"}]

            # Load current_spec via SpecGateService
            spec_gate = SpecGateService(uow)
            spec_status = spec_gate.get_spec_status(session_uuid)
            if "error" in spec_status:
                return [{"type": "text", "text": spec_status["error"]}]

        if confirmed:
            # Transition SPECIFY → CONFIRM (T3) if not already in CONFIRM
            with SqlAlchemyUnitOfWork(self.session_factory) as uow:
                session = uow.sessions.get(session_uuid)

                # Load spec to transition with
                from sqlalchemy import select

                from persistence.infrastructure.models import ExecutionSessionModel

                stmt = select(ExecutionSessionModel).where(
                    ExecutionSessionModel.id == session_uuid
                )
                session_model = uow._session.scalars(stmt).one_or_none()
                if session_model and session_model.current_spec_id:
                    spec = uow.specifications.get(session_model.current_spec_id)
                else:
                    return [
                        {
                            "type": "text",
                            "text": "No specification to confirm",
                        }
                    ]

                # T3: SPECIFY → CONFIRM (if not already in CONFIRM)
                if session.lifecycle_state == LifecycleState.SPECIFY:
                    command = Command(
                        idempotency_key=f"confirm-{session_uuid}-{datetime.now(UTC).isoformat()}",
                        expected_version=session.version,
                        source="user",
                    )
                    session = self.state_machine.transition_to_confirm(
                        session, spec, command
                    )

                    expected_version = session.version - 1
                    uow.sessions.update(session, expected_version)

            # T4: CONFIRM → PLAN (I-02 readiness + I-08 confirmation)
            with SqlAlchemyUnitOfWork(self.session_factory) as uow:
                session = uow.sessions.get(session_uuid)

                # Load spec for session
                from sqlalchemy import select

                from persistence.infrastructure.models import ExecutionSessionModel

                stmt = select(ExecutionSessionModel).where(
                    ExecutionSessionModel.id == session_uuid
                )
                session_model = uow._session.scalars(stmt).one_or_none()
                if session_model and session_model.current_spec_id:
                    session.current_spec = uow.specifications.get(
                        session_model.current_spec_id
                    )

                command = Command(
                    idempotency_key=f"plan-{session_uuid}-{datetime.now(UTC).isoformat()}",
                    expected_version=session.version,
                    source="user",
                )
                session = self.state_machine.transition_to_plan(
                    session,
                    user_confirmed=True,
                    command=command,
                    change_scope="small",
                )

                expected_version = session.version - 1
                uow.sessions.update(session, expected_version)

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
            # T5: CONFIRM → SPECIFY (user correction)
            if corrections:
                with SqlAlchemyUnitOfWork(self.session_factory) as uow:
                    session = uow.sessions.get(session_uuid)

                    from sqlalchemy import select

                    from persistence.infrastructure.models import ExecutionSessionModel

                    stmt = select(ExecutionSessionModel).where(
                        ExecutionSessionModel.id == session_uuid
                    )
                    session_model = uow._session.scalars(stmt).one_or_none()
                    if session_model and session_model.current_spec_id:
                        spec = uow.specifications.get(session_model.current_spec_id)
                    else:
                        return [
                            {
                                "type": "text",
                                "text": "No specification to correct",
                            }
                        ]

                    command = Command(
                        idempotency_key=f"correct-{session_uuid}-{datetime.now(UTC).isoformat()}",
                        expected_version=session.version,
                        source="user",
                    )
                    corrected_spec = spec.model_copy(update=corrections)
                    session = self.state_machine.correct_spec(
                        session, corrected_spec, command
                    )

                    expected_version = session.version - 1
                    uow.sessions.update(session, expected_version)

            return [
                {
                    "type": "text",
                    "text": (
                        "Spec correction required. "
                        "Transition: CONFIRM → SPECIFY\n\n"
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

        ADDs checkpoint (never replaces). Sets spec_snapshot from session.current_spec.
        Copies archive_references from latest checkpoint (preserves I-09 provenance).
        """
        session_uuid = UUID(session_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(session_uuid)
            if not session:
                return [{"type": "text", "text": f"Session not found: {session_id}"}]

            # Load current_spec by querying ORM model for current_spec_id
            # (persistence to_domain mapper doesn't eager-load relationships)
            from sqlalchemy import select

            from persistence.infrastructure.models import ExecutionSessionModel

            stmt = select(ExecutionSessionModel).where(
                ExecutionSessionModel.id == session_uuid
            )
            session_model = uow._session.scalars(stmt).one_or_none()
            if session_model and session_model.current_spec_id:
                session.current_spec = uow.specifications.get(
                    session_model.current_spec_id
                )

            # Get latest checkpoint to copy archive_references (I-09)
            prev_checkpoint = uow.checkpoints.get_latest_for_session(session_uuid)

            checkpoint = Checkpoint(
                id=uuid4(),
                session_id=session_uuid,
                lifecycle_state=session.lifecycle_state,
                restart_action=restart_action,
                checkpoint_reason=reason or "manual",
                spec_id=session.current_spec.id if session.current_spec else None,
                spec_revision=(
                    session.current_spec.revision if session.current_spec else None
                ),
                spec_snapshot=(
                    session.current_spec.model_copy(deep=True)
                    if session.current_spec
                    else None
                ),
            )

            # Copy archive_references from previous checkpoint (I-09)
            if prev_checkpoint and prev_checkpoint.archive_references:
                checkpoint.archive_references = (
                    prev_checkpoint.archive_references.copy()
                )

            # ADD checkpoint (never replace)
            uow.checkpoints.add(checkpoint)
            uow.commit()

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
        Recover from latest checkpoint via T11 (StateMachine.recover).

        Restores spec from spec_snapshot. Renders RecoverySummary with P-06 exemption.
        """
        from coh_prose import ProseRenderer
        from coh_prose import RecoverySummary as ProseRecoverySummary

        session_uuid = UUID(session_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(session_uuid)
            if not session:
                return [{"type": "text", "text": f"Session not found: {session_id}"}]

            # Capture expected_version before T11
            expected_version = session.version

            checkpoint = uow.checkpoints.get_latest_for_session(session_uuid)
            if not checkpoint:
                return [
                    {"type": "text", "text": f"No checkpoint found for: {session_id}"}
                ]

        # T11: recover via state machine (restores spec from spec_snapshot)
        command = Command(
            idempotency_key=f"recover-{session_uuid}-{datetime.now(UTC).isoformat()}",
            expected_version=session.version,
            source="user",
        )
        session, recovery_summary = self.state_machine.recover(
            session, checkpoint, command
        )

        # Persist recovered session
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            uow.sessions.update(session, expected_version)
            # UoW __exit__ commits on success

        # Render recovery summary with P-06 exemption (prospective framing allowed)
        renderer = ProseRenderer()
        prose_recovery = ProseRecoverySummary(
            goal=recovery_summary.goal,
            why=recovery_summary.why,
            last_verified=recovery_summary.last_verified,
            last_decision=recovery_summary.last_decision,
            now_task=recovery_summary.now_task,
            next_tasks=recovery_summary.next_tasks,
            parked_count=recovery_summary.parked_count,
            restart_action=recovery_summary.restart_action,
            archive_degraded=recovery_summary.archive_degraded,
        )

        rendered = renderer.render_recovery_summary(prose_recovery)

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

    async def propose_spec(
        self,
        session_id: str,
        what: str,
        why: str,
        deliverable: str,
        done_when: list[str],
    ) -> list[dict]:
        """
        Propose specification via SpecGateService (read-only, always permitted).

        Returns computed clarity/readiness + blockers.
        Does not persist or transition state.
        """
        session_uuid = UUID(session_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            spec_gate = SpecGateService(uow)
            try:
                spec = spec_gate.propose_spec(
                    session_id=session_uuid,
                    what=what,
                    why=why,
                    deliverable=deliverable,
                    done_when=done_when,
                )
            except ValueError as e:
                return [{"type": "text", "text": str(e)}]

        # Get blockers if not ready
        blockers_text = ""
        if spec.readiness == Readiness.BLOCKED:
            with SqlAlchemyUnitOfWork(self.session_factory) as uow:
                spec_gate = SpecGateService(uow)
                blockers = spec_gate._get_readiness_blockers(spec)
                blockers_list = "\n".join(f"- {b}" for b in blockers)
                blockers_text = f"\n\nBlockers:\n{blockers_list}"

        return [
            {
                "type": "text",
                "text": (
                    f"Spec proposal (not persisted):\n\n"
                    f"WHAT: {spec.what}\n"
                    f"WHY: {spec.why}\n"
                    f"DELIVERABLE: {spec.deliverable}\n"
                    "DONE WHEN:\n"
                    + "\n".join(f"- {d.text}" for d in spec.done_when)
                    + "\n\n"
                    f"Clarity: {spec.clarity.value}\n"
                    f"Readiness: {spec.readiness.value}"
                    f"{blockers_text}"
                ),
            }
        ]

    async def get_spec_status(self, session_id: str) -> list[dict]:
        """
        Get specification status (read-only, always permitted per I-02).

        Returns clarity, readiness, blockers.
        """
        session_uuid = UUID(session_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            spec_gate = SpecGateService(uow)
            status = spec_gate.get_spec_status(session_uuid)

        if "error" in status:
            return [{"type": "text", "text": status["error"]}]

        blockers_text = ""
        if status.get("blockers"):
            blockers_text = "\n\nBlockers:\n" + "\n".join(
                f"- {b}" for b in status["blockers"]
            )

        return [
            {
                "type": "text",
                "text": (
                    f"Specification Status\n\n"
                    f"Spec ID: {status.get('spec_id', 'N/A')}\n"
                    f"Revision: {status.get('revision', 'N/A')}\n"
                    f"Clarity: {status.get('clarity', 'none')}\n"
                    f"Readiness: {status.get('readiness', 'blocked')}\n"
                    f"WHAT: {status.get('what', 'N/A')}\n"
                    f"Done when criteria: {status.get('done_when_count', 0)}"
                    f"{blockers_text}"
                ),
            }
        ]

    async def get_foreground(self, session_id: str) -> list[dict]:
        """
        Get foreground (I-01: NOW + ≤2 NEXT with metadata).

        Uses ForegroundService.calculate_foreground.
        Returns now_task, next_1_task, next_2_task with full metadata.
        """
        from coh_prose import ExecutionForeground, ProseRenderer

        session_uuid = UUID(session_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            foreground_service = ForegroundService(uow)
            try:
                foreground = foreground_service.calculate_foreground(session_uuid)
            except ValueError as e:
                return [{"type": "text", "text": str(e)}]

        # Render with P-06 (foreground uses prospective framing)
        renderer = ProseRenderer()

        # Prepare foreground for rendering (I-01 metadata)
        if foreground.now_task:
            now_text = foreground.now_task.action_literal or "No action"
            now_done_when = foreground.now_task.done_when_condition or ""
            now_minutes = foreground.now_task.estimated_minutes
            now_energy = foreground.now_task.energy
            now_friction = foreground.now_task.activation_friction
        else:
            now_text = "No active task"
            now_done_when = ""
            now_minutes = None
            now_energy = None
            now_friction = None

        foreground_view = ExecutionForeground(
            goal=foreground.goal,
            now=now_text,
            now_done_when=now_done_when,
            now_minutes=now_minutes,
            now_energy=now_energy,
            now_friction=now_friction,
            next_1=(
                foreground.next_1_task.action_literal
                if foreground.next_1_task
                else None
            ),
            next_2=(
                foreground.next_2_task.action_literal
                if foreground.next_2_task
                else None
            ),
            parked_count=foreground.parked_count,
        )

        rendered = renderer.render_execution_foreground(foreground_view)

        return [
            {
                "type": "text",
                "text": rendered,
            }
        ]

    async def complete_now(
        self, session_id: str, task_id: str, completion_notes: str | None = None
    ) -> list[dict]:
        """
        Complete NOW task (I-05, I-01).

        Calls ForegroundService.complete_now_task.
        Returns new foreground after promotion.
        """
        session_uuid = UUID(session_id)
        task_uuid = UUID(task_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            foreground_service = ForegroundService(uow)
            try:
                new_foreground = foreground_service.complete_now_task(
                    session_uuid, task_uuid, completion_notes
                )
            except ValueError as e:
                return [{"type": "text", "text": f"Error: {e}"}]

        now_literal = (
            new_foreground.now_task.action_literal
            if new_foreground.now_task
            else "None"
        )
        next_literal = (
            new_foreground.next_1_task.action_literal
            if new_foreground.next_1_task
            else "None"
        )

        return [
            {
                "type": "text",
                "text": (
                    f"Task {task_id} completed.\n\n"
                    f"New foreground:\n"
                    f"NOW: {now_literal}\n"
                    f"NEXT: {next_literal}"
                ),
            }
        ]

    async def block_now(
        self, session_id: str, task_id: str, reason: str
    ) -> list[dict]:
        """
        Block NOW task (I-05, I-01).

        Calls ForegroundService.block_now_task.
        Returns new foreground after recalculation.
        """
        session_uuid = UUID(session_id)
        task_uuid = UUID(task_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            foreground_service = ForegroundService(uow)
            try:
                new_foreground = foreground_service.block_now_task(
                    session_uuid, task_uuid, reason
                )
            except ValueError as e:
                return [{"type": "text", "text": f"Error: {e}"}]

        now_literal = (
            new_foreground.now_task.action_literal
            if new_foreground.now_task
            else "None"
        )
        next_literal = (
            new_foreground.next_1_task.action_literal
            if new_foreground.next_1_task
            else "None"
        )

        return [
            {
                "type": "text",
                "text": (
                    f"Task {task_id} blocked: {reason}\n\n"
                    f"New foreground:\n"
                    f"NOW: {now_literal}\n"
                    f"NEXT: {next_literal}"
                ),
            }
        ]

    async def park_task(
        self, session_id: str, task_id: str, reason: str
    ) -> list[dict]:
        """
        Park task without changing NOW (I-10).

        Calls ForegroundService.park_task.
        Returns updated foreground.
        """
        session_uuid = UUID(session_id)
        task_uuid = UUID(task_id)

        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            foreground_service = ForegroundService(uow)
            try:
                new_foreground = foreground_service.park_task(
                    session_uuid, task_uuid, reason
                )
            except ValueError as e:
                return [{"type": "text", "text": f"Error: {e}"}]

        return [
            {
                "type": "text",
                "text": (
                    f"Task {task_id} parked: {reason}\n\n"
                    f"Parked count: {new_foreground.parked_count}"
                ),
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
