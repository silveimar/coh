"""Common API schemas and types."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="User-safe error message")
    correlation_id: str | None = Field(None, description="Request correlation ID")
    details: dict[str, str] | None = Field(None, description="Additional error context")


class IdempotencyRequest(BaseModel):
    """Base for requests requiring idempotency and concurrency control."""

    idempotency_key: str = Field(..., description="Unique idempotency key")
    expected_version: int | None = Field(
        None, description="Expected entity version for optimistic concurrency control"
    )
