"""Spec gate routes enforcing I-02 (readiness-based mutation control)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from coh_api.api.schemas.spec_gate import (
    ConfirmSpecRequest,
    MutationAllowedResponse,
    ProposeSpecRequest,
    ReviseSpecRequest,
    SpecResponse,
    SpecStatusResponse,
)
from coh_api.composition import get_container

router = APIRouter(prefix="/spec-gate", tags=["spec-gate"])


@router.post("/propose", response_model=SpecResponse)
def propose_spec(request: ProposeSpecRequest) -> SpecResponse:
    """
    Propose a specification after inspection.

    Read-only operation, always permitted (I-02).
    Returns computed clarity and readiness.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.spec_gate_service(uow)

        assumptions_dicts = None
        if request.assumptions:
            assumptions_dicts = [
                {
                    "text": a.text,
                    "classification": a.classification,
                    "rationale": a.rationale,
                    "requires_confirmation": a.requires_confirmation,
                }
                for a in request.assumptions
            ]

        unknowns_dicts = None
        if request.unknowns:
            unknowns_dicts = [
                {
                    "text": u.text,
                    "blocking": u.blocking,
                    "discoverable_via_inspection": u.discoverable_via_inspection,
                }
                for u in request.unknowns
            ]

        try:
            spec = service.propose_spec(
                session_id=request.session_id,
                what=request.what,
                why=request.why,
                deliverable=request.deliverable,
                done_when=request.done_when,
                constraints=request.constraints,
                non_goals=request.non_goals,
                assumptions=assumptions_dicts,
                unknowns=unknowns_dicts,
            )

            blockers = service._get_readiness_blockers(spec)

            return SpecResponse(
                spec_id=str(spec.id),
                revision=spec.revision,
                what=spec.what,
                why=spec.why,
                deliverable=spec.deliverable,
                done_when=[criterion.text for criterion in spec.done_when],
                constraints=spec.constraints,
                non_goals=spec.non_goals,
                clarity=spec.clarity.value,
                readiness=spec.readiness.value,
                blockers=blockers,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "session_not_found", "message": str(e)},
            ) from None


@router.post(
    "/confirm", response_model=SpecResponse, status_code=status.HTTP_201_CREATED
)
def confirm_spec(request: ConfirmSpecRequest) -> SpecResponse:
    """
    Confirm specification and persist it (T4).

    Material mutation: requires readiness=READY (I-02).
    Returns 422 if specification is blocked.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.spec_gate_service(uow)

        # I-02: Check mutation allowed before proceeding
        allowed, state, blockers = service.check_mutation_allowed(request.session_id)
        if not allowed:
            blockers_text = ", ".join(blockers)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "readiness_blocked",
                    "message": (
                        f"Material mutation rejected: readiness is "
                        f"{state.upper()}. Blockers: {blockers_text}. "
                        f"Read-only inspection remains permitted."
                    ),
                    "blockers": blockers,
                },
            )

        # Reconstruct spec from request
        assumptions_dicts = None
        if request.spec.assumptions:
            assumptions_dicts = [
                {
                    "text": a.text,
                    "classification": a.classification,
                    "rationale": a.rationale,
                    "requires_confirmation": a.requires_confirmation,
                }
                for a in request.spec.assumptions
            ]

        unknowns_dicts = None
        if request.spec.unknowns:
            unknowns_dicts = [
                {
                    "text": u.text,
                    "blocking": u.blocking,
                    "discoverable_via_inspection": u.discoverable_via_inspection,
                }
                for u in request.spec.unknowns
            ]

        try:
            # First propose to get the spec object
            spec = service.propose_spec(
                session_id=request.session_id,
                what=request.spec.what,
                why=request.spec.why,
                deliverable=request.spec.deliverable,
                done_when=request.spec.done_when,
                constraints=request.spec.constraints,
                non_goals=request.spec.non_goals,
                assumptions=assumptions_dicts,
                unknowns=unknowns_dicts,
            )

            # Then confirm it
            confirmed_spec = service.confirm_spec(request.session_id, spec)

            blockers = service._get_readiness_blockers(confirmed_spec)

            return SpecResponse(
                spec_id=str(confirmed_spec.id),
                revision=confirmed_spec.revision,
                what=confirmed_spec.what,
                why=confirmed_spec.why,
                deliverable=confirmed_spec.deliverable,
                done_when=[criterion.text for criterion in confirmed_spec.done_when],
                constraints=confirmed_spec.constraints,
                non_goals=confirmed_spec.non_goals,
                clarity=confirmed_spec.clarity.value,
                readiness=confirmed_spec.readiness.value,
                blockers=blockers,
            )
        except ValueError as e:
            error_msg = str(e)
            if "readiness=BLOCKED" in error_msg or "Cannot confirm" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "readiness_blocked", "message": error_msg},
                ) from None
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "session_not_found", "message": error_msg},
            ) from None


@router.post("/revise", response_model=SpecResponse)
def revise_spec(request: ReviseSpecRequest) -> SpecResponse:
    """
    Revise specification fields (T5).

    Material mutation: creates new revision.
    Recomputes clarity and readiness.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.spec_gate_service(uow)

        try:
            revised_spec = service.revise_spec(
                session_id=request.session_id,
                spec_id=request.spec_id,
                updates=request.updates,
            )

            blockers = service._get_readiness_blockers(revised_spec)

            return SpecResponse(
                spec_id=str(revised_spec.id),
                revision=revised_spec.revision,
                what=revised_spec.what,
                why=revised_spec.why,
                deliverable=revised_spec.deliverable,
                done_when=[criterion.text for criterion in revised_spec.done_when],
                constraints=revised_spec.constraints,
                non_goals=revised_spec.non_goals,
                clarity=revised_spec.clarity.value,
                readiness=revised_spec.readiness.value,
                blockers=blockers,
            )
        except ValueError as e:
            message = str(e)
            if "not found" in message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error_code": "not_found", "message": message},
                ) from None
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_code": "invalid_revision", "message": message},
            ) from None


@router.get("/mutation-allowed/{session_id}", response_model=MutationAllowedResponse)
def check_mutation_allowed(session_id: UUID) -> MutationAllowedResponse:
    """
    Check if material mutation is allowed (I-02 enforcement).

    Read-only operation, always permitted.
    Returns allowed=False with blockers if readiness=BLOCKED.
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.spec_gate_service(uow)

        allowed, state, blockers = service.check_mutation_allowed(session_id)

        return MutationAllowedResponse(
            allowed=allowed, readiness_state=state, blockers=blockers
        )


@router.get("/status/{session_id}", response_model=SpecStatusResponse)
def get_spec_status(session_id: UUID) -> SpecStatusResponse:
    """
    Get specification status for read-only inspection.

    Always permitted regardless of readiness (I-02).
    """
    container = get_container()

    with container.create_uow() as uow:
        service = container.spec_gate_service(uow)

        status_dict = service.get_spec_status(session_id)

        # Handle error case
        if "error" in status_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "session_not_found",
                    "message": status_dict["error"],
                },
            )

        return SpecStatusResponse(
            spec_id=status_dict.get("spec_id"),
            revision=status_dict.get("revision"),
            clarity=status_dict.get("clarity", "none"),
            readiness=status_dict.get("readiness", "blocked"),
            blockers=status_dict.get("blockers", []),
            what=status_dict.get("what"),
            why=status_dict.get("why"),
            deliverable=status_dict.get("deliverable"),
            done_when_count=status_dict.get("done_when_count", 0),
        )
