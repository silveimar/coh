"""COH Application Services — spec gate and foreground execution composition.

This package composes execution-core policies with persistence to implement:
- Specification gate service (I-02: readiness, mutation rejection)
- Foreground execution service (I-01: NOW + NEXT 2 with metadata enforcement)

No FastAPI, no HTTP, no Huey, no UI, no telemetry — pure application layer.
"""

from .foreground_service import ForegroundService
from .spec_gate_service import SpecGateService

__all__ = ["SpecGateService", "ForegroundService"]
