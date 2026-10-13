"""Mappers between domain models and SQLAlchemy models.

Handles JSON serialization for nested Pydantic models.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from execution_core.domain.checkpoint import ArchiveReference, Checkpoint
from execution_core.domain.decision import Alternative, Decision
from execution_core.domain.evidence import Evidence
from execution_core.domain.parking_item import ParkingItem
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import (
    Assumption,
    DoneWhenCriterion,
    Specification,
    Unknown,
)
from execution_core.domain.task import Task, TaskDependency

from .models import (
    CheckpointModel,
    DecisionModel,
    EvidenceModel,
    ExecutionSessionModel,
    ParkingItemModel,
    SpecificationModel,
    TaskModel,
)


def _serialize_for_json(obj: Any) -> Any:
    """Recursively serialize objects for JSON storage.

    Handles UUID, datetime, Pydantic models, lists, and dicts.
    """
    if obj is None:
        return None
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        dumped = obj.model_dump()
        return _serialize_for_json(dumped)
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]
    return obj


def _deserialize_archive_reference(
    data: dict | None,
) -> ArchiveReference | None:
    """Deserialize ArchiveReference from JSON dict."""
    if not data:
        return None
    return ArchiveReference(
        path=data["path"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
        anchor=data["anchor"],
    )


def _deserialize_archive_references(data: list | dict) -> list[ArchiveReference]:
    """Deserialize list of ArchiveReference from JSON."""
    if isinstance(data, dict):
        return []
    return [
        ArchiveReference(
            path=item["path"],
            timestamp=datetime.fromisoformat(item["timestamp"]),
            anchor=item["anchor"],
        )
        for item in data
    ]


def _deserialize_spec_snapshot(data: dict | None) -> Specification | None:
    """Deserialize Specification from JSON dict."""
    if not data:
        return None

    # Convert ISO strings back to datetime objects
    created_at = (
        datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("created_at"), str)
        else data["created_at"]
    )
    updated_at = (
        datetime.fromisoformat(data["updated_at"])
        if isinstance(data.get("updated_at"), str)
        else data["updated_at"]
    )
    confirmed_at = (
        datetime.fromisoformat(data["confirmed_at"])
        if data.get("confirmed_at") and isinstance(data["confirmed_at"], str)
        else data.get("confirmed_at")
    )

    # Convert UUID strings back to UUID objects
    spec_id = UUID(data["id"]) if isinstance(data["id"], str) else data["id"]

    # Reconstruct nested Pydantic models
    assumptions = []
    for a_data in data.get("assumptions", []):
        a_id = UUID(a_data["id"]) if isinstance(a_data["id"], str) else a_data["id"]
        a_created_at = (
            datetime.fromisoformat(a_data["created_at"])
            if isinstance(a_data["created_at"], str)
            else a_data["created_at"]
        )
        assumptions.append(
            Assumption(
                id=a_id,
                text=a_data["text"],
                classification=a_data["classification"],
                rationale=a_data.get("rationale"),
                requires_confirmation=a_data.get("requires_confirmation", False),
                resolved=a_data.get("resolved", False),
                resolution_notes=a_data.get("resolution_notes"),
                created_at=a_created_at,
            )
        )

    unknowns = []
    for u_data in data.get("unknowns", []):
        u_id = UUID(u_data["id"]) if isinstance(u_data["id"], str) else u_data["id"]
        u_created_at = (
            datetime.fromisoformat(u_data["created_at"])
            if isinstance(u_data["created_at"], str)
            else u_data["created_at"]
        )
        unknowns.append(
            Unknown(
                id=u_id,
                text=u_data["text"],
                blocking=u_data["blocking"],
                discoverable_via_inspection=u_data.get(
                    "discoverable_via_inspection", True
                ),
                resolved=u_data.get("resolved", False),
                resolution_value=u_data.get("resolution_value"),
                created_at=u_created_at,
            )
        )

    done_when = []
    for d_data in data.get("done_when", []):
        d_id = UUID(d_data["id"]) if isinstance(d_data["id"], str) else d_data["id"]
        d_created_at = (
            datetime.fromisoformat(d_data["created_at"])
            if isinstance(d_data["created_at"], str)
            else d_data["created_at"]
        )
        done_when.append(
            DoneWhenCriterion(
                id=d_id,
                text=d_data["text"],
                measurable=d_data.get("measurable", True),
                created_at=d_created_at,
            )
        )

    return Specification(
        id=spec_id,
        revision=data["revision"],
        what=data["what"],
        why=data["why"],
        deliverable=data["deliverable"],
        done_when=done_when,
        constraints=data.get("constraints", []),
        non_goals=data.get("non_goals", []),
        assumptions=assumptions,
        unknowns=unknowns,
        clarity=data["clarity"],
        readiness=data["readiness"],
        created_at=created_at,
        updated_at=updated_at,
        confirmed_at=confirmed_at,
    )


class ExecutionSessionMapper:
    """Map between ExecutionSession and ExecutionSessionModel."""

    @staticmethod
    def to_model(session: ExecutionSession) -> ExecutionSessionModel:
        """Convert domain ExecutionSession to ORM model."""
        return ExecutionSessionModel(
            id=session.id,
            project_id=session.project_id,
            intent=session.intent,
            lifecycle_state=session.lifecycle_state,
            current_spec_id=session.current_spec.id if session.current_spec else None,
            version=session.version,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def to_domain(model: ExecutionSessionModel) -> ExecutionSession:
        """Convert ORM model to domain ExecutionSession."""
        return ExecutionSession(
            id=model.id,
            project_id=model.project_id,
            intent=model.intent,
            lifecycle_state=model.lifecycle_state,
            current_spec=None,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            checkpoints=[],
        )

    @staticmethod
    def update_model(model: ExecutionSessionModel, session: ExecutionSession) -> None:
        """Update existing ORM model from domain object."""
        model.project_id = session.project_id
        model.intent = session.intent
        model.lifecycle_state = session.lifecycle_state
        model.current_spec_id = (
            session.current_spec.id if session.current_spec else None
        )
        model.version = session.version
        model.updated_at = session.updated_at


class SpecificationMapper:
    """Map between Specification and SpecificationModel."""

    @staticmethod
    def to_model(spec: Specification) -> SpecificationModel:
        """Convert domain Specification to ORM model."""
        return SpecificationModel(
            id=spec.id,
            revision=spec.revision,
            what=spec.what,
            why=spec.why,
            deliverable=spec.deliverable,
            done_when=_serialize_for_json(spec.done_when),
            constraints=_serialize_for_json(spec.constraints),
            non_goals=_serialize_for_json(spec.non_goals),
            assumptions=_serialize_for_json(spec.assumptions),
            unknowns=_serialize_for_json(spec.unknowns),
            clarity=spec.clarity,
            readiness=spec.readiness,
            created_at=spec.created_at,
            updated_at=spec.updated_at,
            confirmed_at=spec.confirmed_at,
        )

    @staticmethod
    def to_domain(model: SpecificationModel) -> Specification:
        """Convert ORM model to domain Specification."""
        # Reconstruct nested Pydantic models
        assumptions = (
            [Assumption(**a) for a in model.assumptions]
            if isinstance(model.assumptions, list)
            else []
        )
        unknowns = (
            [Unknown(**u) for u in model.unknowns]
            if isinstance(model.unknowns, list)
            else []
        )
        done_when = (
            [DoneWhenCriterion(**d) for d in model.done_when]
            if isinstance(model.done_when, list)
            else []
        )

        return Specification(
            id=model.id,
            revision=model.revision,
            what=model.what,
            why=model.why,
            deliverable=model.deliverable,
            done_when=done_when,
            constraints=model.constraints
            if isinstance(model.constraints, list)
            else [],
            non_goals=model.non_goals if isinstance(model.non_goals, list) else [],
            assumptions=assumptions,
            unknowns=unknowns,
            clarity=model.clarity,
            readiness=model.readiness,
            created_at=model.created_at,
            updated_at=model.updated_at,
            confirmed_at=model.confirmed_at,
        )

    @staticmethod
    def update_model(model: SpecificationModel, spec: Specification) -> None:
        """Update existing ORM model from domain object."""
        model.revision = spec.revision
        model.what = spec.what
        model.why = spec.why
        model.deliverable = spec.deliverable
        model.done_when = _serialize_for_json(spec.done_when)
        model.constraints = _serialize_for_json(spec.constraints)
        model.non_goals = _serialize_for_json(spec.non_goals)
        model.assumptions = _serialize_for_json(spec.assumptions)
        model.unknowns = _serialize_for_json(spec.unknowns)
        model.clarity = spec.clarity
        model.readiness = spec.readiness
        model.updated_at = spec.updated_at
        model.confirmed_at = spec.confirmed_at


class TaskMapper:
    """Map between Task and TaskModel."""

    @staticmethod
    def to_model(task: Task) -> TaskModel:
        """Convert domain Task to ORM model."""
        return TaskModel(
            id=task.id,
            spec_id=task.spec_id,
            spec_revision=task.spec_revision,
            action_literal=task.action_literal,
            done_when_condition=task.done_when_condition,
            estimated_minutes=task.estimated_minutes,
            energy=task.energy,
            activation_friction=task.activation_friction,
            goal_leverage=task.goal_leverage,
            status=task.status,
            completion_state=task.completion_state,
            foreground_position=task.foreground_position,
            dependencies=_serialize_for_json(task.dependencies),
            blocked_reason=task.blocked_reason,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    @staticmethod
    def to_domain(model: TaskModel) -> Task:
        """Convert ORM model to domain Task."""
        dependencies = (
            [TaskDependency(**d) for d in model.dependencies]
            if isinstance(model.dependencies, list)
            else []
        )

        return Task(
            id=model.id,
            spec_id=model.spec_id,
            spec_revision=model.spec_revision,
            action_literal=model.action_literal,
            done_when_condition=model.done_when_condition,
            estimated_minutes=model.estimated_minutes,
            energy=model.energy,
            activation_friction=model.activation_friction,
            goal_leverage=model.goal_leverage,
            status=model.status,
            completion_state=model.completion_state,
            foreground_position=model.foreground_position,
            dependencies=dependencies,
            blocked_reason=model.blocked_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def update_model(model: TaskModel, task: Task) -> None:
        """Update existing ORM model from domain object."""
        model.action_literal = task.action_literal
        model.done_when_condition = task.done_when_condition
        model.estimated_minutes = task.estimated_minutes
        model.energy = task.energy
        model.activation_friction = task.activation_friction
        model.goal_leverage = task.goal_leverage
        model.status = task.status
        model.completion_state = task.completion_state
        model.foreground_position = task.foreground_position
        model.dependencies = _serialize_for_json(task.dependencies)
        model.blocked_reason = task.blocked_reason
        model.updated_at = task.updated_at
        model.started_at = task.started_at
        model.completed_at = task.completed_at


class EvidenceMapper:
    """Map between Evidence and EvidenceModel."""

    @staticmethod
    def to_model(evidence: Evidence) -> EvidenceModel:
        """Convert domain Evidence to ORM model."""
        return EvidenceModel(
            id=evidence.id,
            spec_id=evidence.spec_id,
            spec_revision=evidence.spec_revision,
            criterion_id=evidence.criterion_id,
            evidence_type=evidence.evidence_type,
            authority=evidence.authority,
            result=evidence.result,
            summary=evidence.summary,
            source=evidence.source,
            archive_reference=_serialize_for_json(evidence.archive_reference),
            tool_reference=evidence.tool_reference,
            recorded_at=evidence.recorded_at,
            user_acceptance_rationale=evidence.user_acceptance_rationale,
            stale=evidence.stale,
        )

    @staticmethod
    def to_domain(model: EvidenceModel) -> Evidence:
        """Convert ORM model to domain Evidence."""
        from execution_core.domain.evidence import (
            ArchiveReference as EvidenceArchiveReference,
        )

        archive_ref = None
        if model.archive_reference:
            archive_ref = EvidenceArchiveReference(
                path=model.archive_reference["path"],
                timestamp=datetime.fromisoformat(model.archive_reference["timestamp"])
                if isinstance(model.archive_reference["timestamp"], str)
                else model.archive_reference["timestamp"],
                anchor=model.archive_reference["anchor"],
            )

        return Evidence(
            id=model.id,
            spec_id=model.spec_id,
            spec_revision=model.spec_revision,
            criterion_id=model.criterion_id,
            evidence_type=model.evidence_type,
            authority=model.authority,
            result=model.result,
            summary=model.summary,
            source=model.source,
            archive_reference=archive_ref,
            tool_reference=model.tool_reference,
            recorded_at=model.recorded_at,
            user_acceptance_rationale=model.user_acceptance_rationale,
            stale=model.stale,
        )


class CheckpointMapper:
    """Map between Checkpoint and CheckpointModel."""

    @staticmethod
    def to_model(checkpoint: Checkpoint) -> CheckpointModel:
        """Convert domain Checkpoint to ORM model."""
        return CheckpointModel(
            id=checkpoint.id,
            session_id=checkpoint.session_id,
            lifecycle_state=checkpoint.lifecycle_state,
            spec_snapshot=_serialize_for_json(checkpoint.spec_snapshot),
            spec_id=checkpoint.spec_id,
            spec_revision=checkpoint.spec_revision,
            current_task_id=checkpoint.current_task_id,
            restart_action=checkpoint.restart_action,
            archive_status=checkpoint.archive_status,
            archive_references=_serialize_for_json(checkpoint.archive_references),
            material_context=_serialize_for_json(checkpoint.material_context),
            created_at=checkpoint.created_at,
            checkpoint_reason=checkpoint.checkpoint_reason,
        )

    @staticmethod
    def to_domain(model: CheckpointModel) -> Checkpoint:
        """Convert ORM model to domain Checkpoint."""
        spec_snapshot = _deserialize_spec_snapshot(model.spec_snapshot)
        archive_refs = _deserialize_archive_references(model.archive_references)

        return Checkpoint(
            id=model.id,
            session_id=model.session_id,
            lifecycle_state=model.lifecycle_state,
            spec_snapshot=spec_snapshot,
            spec_id=model.spec_id,
            spec_revision=model.spec_revision,
            current_task_id=model.current_task_id,
            restart_action=model.restart_action,
            archive_status=model.archive_status,
            archive_references=archive_refs,
            material_context=model.material_context
            if isinstance(model.material_context, dict)
            else {},
            created_at=model.created_at,
            checkpoint_reason=model.checkpoint_reason,
        )

    @staticmethod
    def update_archive_state(model: CheckpointModel, checkpoint: Checkpoint) -> None:
        """Copy archive status and references only; other fields stay as added."""
        model.archive_status = checkpoint.archive_status
        model.archive_references = _serialize_for_json(checkpoint.archive_references)


class DecisionMapper:
    """Map between Decision and DecisionModel."""

    @staticmethod
    def to_model(decision: Decision) -> DecisionModel:
        """Convert domain Decision to ORM model."""
        return DecisionModel(
            id=decision.id,
            question=decision.question,
            selected_option=decision.selected_option,
            rationale=decision.rationale,
            alternatives=_serialize_for_json(decision.alternatives),
            evidence_refs=_serialize_for_json(decision.evidence_refs),
            material=decision.material,
            lifecycle=decision.lifecycle,
            created_at=decision.created_at,
            superseded_at=decision.superseded_at,
            superseded_by=decision.superseded_by,
            reopened_at=decision.reopened_at,
            reopening_reason=decision.reopening_reason,
        )

    @staticmethod
    def to_domain(model: DecisionModel) -> Decision:
        """Convert ORM model to domain Decision."""
        alternatives = (
            [Alternative(**a) for a in model.alternatives]
            if isinstance(model.alternatives, list)
            else []
        )
        evidence_refs = (
            [UUID(ref) if isinstance(ref, str) else ref for ref in model.evidence_refs]
            if isinstance(model.evidence_refs, list)
            else []
        )

        return Decision(
            id=model.id,
            question=model.question,
            selected_option=model.selected_option,
            rationale=model.rationale,
            alternatives=alternatives,
            evidence_refs=evidence_refs,
            material=model.material,
            lifecycle=model.lifecycle,
            created_at=model.created_at,
            superseded_at=model.superseded_at,
            superseded_by=model.superseded_by,
            reopened_at=model.reopened_at,
            reopening_reason=model.reopening_reason,
        )


class ParkingItemMapper:
    """Map between ParkingItem and ParkingItemModel."""

    @staticmethod
    def to_model(item: ParkingItem) -> ParkingItemModel:
        """Convert domain ParkingItem to ORM model."""
        return ParkingItemModel(
            id=item.id,
            text=item.text,
            source_task_id=item.source_task_id,
            source_context=item.source_context,
            relevance=item.relevance,
            blocking=item.blocking,
            suggested_disposition=item.suggested_disposition,
            status=item.status,
            revisit_trigger=item.revisit_trigger,
            auto_parked=item.auto_parked,
            created_at=item.created_at,
            promoted_at=item.promoted_at,
            promoted_to_task_id=item.promoted_to_task_id,
            dismissed_at=item.dismissed_at,
            dismissal_reason=item.dismissal_reason,
        )

    @staticmethod
    def to_domain(model: ParkingItemModel) -> ParkingItem:
        """Convert ORM model to domain ParkingItem."""
        return ParkingItem(
            id=model.id,
            text=model.text,
            source_task_id=model.source_task_id,
            source_context=model.source_context,
            relevance=model.relevance,
            blocking=model.blocking,
            suggested_disposition=model.suggested_disposition,
            status=model.status,
            revisit_trigger=model.revisit_trigger,
            auto_parked=model.auto_parked,
            created_at=model.created_at,
            promoted_at=model.promoted_at,
            promoted_to_task_id=model.promoted_to_task_id,
            dismissed_at=model.dismissed_at,
            dismissal_reason=model.dismissal_reason,
        )
