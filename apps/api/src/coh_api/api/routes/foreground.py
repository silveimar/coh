"""Foreground routes enforcing I-01 (NOW + NEXT 2 with metadata)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from coh_api.api.schemas.foreground import (
    BlockNowTaskRequest,
    CompleteNowTaskRequest,
    ForegroundResponse,
    ForegroundStatusResponse,
    InterruptNowTaskRequest,
    ParkTaskRequest,
    TaskMetadata,
)
from coh_api.composition import get_container

router = APIRouter(prefix="/foreground", tags=["foreground"])


def _map_task_to_metadata(task) -> TaskMetadata:
    """Map Task domain object to TaskMetadata schema."""
    return TaskMetadata(
        task_id=str(task.id),
        action_literal=task.action_literal,
        done_when_condition=task.done_when_condition,
        estimated_minutes=task.estimated_minutes,
        energy=task.energy.value if task.energy else None,
        activation_friction=task.activation_friction.value
        if task.activation_friction
        else None,
    )


def _map_foreground_to_response(foreground) -> ForegroundResponse:
    """Map Foreground domain object to ForegroundResponse schema."""
    return ForegroundResponse(
        goal=foreground.goal,
        now_task=_map_task_to_metadata(foreground.now_task)
        if foreground.now_task
        else None,
        next_1_task=_map_task_to_metadata(foreground.next_1_task)
        if foreground.next_1_task
        else None,
        next_2_task=_map_task_to_metadata(foreground.next_2_task)
        if foreground.next_2_task
        else None,
        parked_count=foreground.parked_count,
        background_count=foreground.background_count,
    )


@router.get("/{session_id}", response_model=ForegroundResponse)
def get_foreground(session_id: UUID, goal: str | None = None) -> ForegroundResponse:
    """
    Calculate and return foreground from task list.

    Read-only operation, always permitted.
    Enforces I-01: at most one NOW and two NEXT with required metadata.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        try:
            foreground = service.calculate_foreground(session_id, goal)

            # Validate I-01
            valid, violations = foreground.validate_invariant_i01()
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "foreground_invariant_violation",
                        "message": f"I-01 violation: {'; '.join(violations)}",
                    },
                )

            return _map_foreground_to_response(foreground)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "not_found", "message": str(e)},
            )


@router.post("/complete-now", response_model=ForegroundResponse)
def complete_now_task(request: CompleteNowTaskRequest) -> ForegroundResponse:
    """
    Complete NOW task and recalculate foreground (I-05, I-01).

    Material mutation: creates progress record before foreground change.
    Returns new foreground with promoted tasks.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        try:
            foreground = service.complete_now_task(
                session_id=request.session_id,
                task_id=request.task_id,
                completion_notes=request.completion_notes,
            )

            # Validate I-01
            valid, violations = foreground.validate_invariant_i01()
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "foreground_invariant_violation",
                        "message": f"I-01 violation: {'; '.join(violations)}",
                    },
                )

            return _map_foreground_to_response(foreground)
        except ValueError as e:
            error_msg = str(e)
            if "not the NOW task" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "not_now_task", "message": error_msg},
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "not_found", "message": error_msg},
            )


@router.post("/block-now", response_model=ForegroundResponse)
def block_now_task(request: BlockNowTaskRequest) -> ForegroundResponse:
    """
    Block NOW task and recalculate foreground (I-05, I-01).

    Material mutation: creates progress record with blocker before foreground change.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        try:
            foreground = service.block_now_task(
                session_id=request.session_id,
                task_id=request.task_id,
                reason=request.reason,
            )

            # Validate I-01
            valid, violations = foreground.validate_invariant_i01()
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "foreground_invariant_violation",
                        "message": f"I-01 violation: {'; '.join(violations)}",
                    },
                )

            return _map_foreground_to_response(foreground)
        except ValueError as e:
            error_msg = str(e)
            if "not the NOW task" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "not_now_task", "message": error_msg},
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "not_found", "message": error_msg},
            )


@router.post("/park", response_model=ForegroundResponse)
def park_task(request: ParkTaskRequest) -> ForegroundResponse:
    """
    Park task without changing NOW (I-10).

    Material mutation: creates progress record before status change.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        try:
            foreground = service.park_task(
                session_id=request.session_id,
                task_id=request.task_id,
                reason=request.reason,
            )

            # Validate I-01
            valid, violations = foreground.validate_invariant_i01()
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "foreground_invariant_violation",
                        "message": f"I-01 violation: {'; '.join(violations)}",
                    },
                )

            return _map_foreground_to_response(foreground)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "not_found", "message": str(e)},
            )


@router.post("/interrupt-now", response_model=ForegroundResponse)
def interrupt_now_task(request: InterruptNowTaskRequest) -> ForegroundResponse:
    """
    Interrupt NOW task and record progress (I-05).

    Material mutation: creates/updates progress record before foreground change.
    Returns recalculated foreground.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        try:
            foreground = service.interrupt_now_task(
                session_id=request.session_id,
                task_id=request.task_id,
                completed_work=request.completed_work,
                next_steps=request.next_steps,
            )

            # Validate I-01
            valid, violations = foreground.validate_invariant_i01()
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "foreground_invariant_violation",
                        "message": f"I-01 violation: {'; '.join(violations)}",
                    },
                )

            return _map_foreground_to_response(foreground)
        except ValueError as e:
            error_msg = str(e)
            if "not the NOW task" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "not_now_task", "message": error_msg},
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "not_found", "message": error_msg},
            )


@router.get("/status/{session_id}", response_model=ForegroundStatusResponse)
def get_foreground_status(session_id: UUID) -> ForegroundStatusResponse:
    """
    Get current foreground status for read-only inspection.

    Always permitted regardless of state.
    Returns: goal, now_task_id, next_1_id, next_2_id, parked_count, background_count.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.foreground_service(uow)

        status_dict = service.get_foreground_status(session_id)

        # Handle error case
        if "error" in status_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "not_found",
                    "message": status_dict["error"],
                },
            )

        return ForegroundStatusResponse(
            goal=status_dict.get("goal"),
            now_task_id=status_dict.get("now_task_id"),
            next_1_id=status_dict.get("next_1_id"),
            next_2_id=status_dict.get("next_2_id"),
            parked_count=status_dict.get("parked_count", 0),
            background_count=status_dict.get("background_count", 0),
        )
