"""Mock adapter for deterministic eval scenario execution.

Returns recorded fixtures; never calls live LLMs or network.
Implements capabilities from setup.capabilities only.
"""

from pathlib import Path
from typing import Any
from uuid import UUID

from coh_mcp.errors import CapabilityNotImplementedError

from ..fixtures.inspection_findings import INSPECTION_FINDINGS


class MockAdapter:
    """Deterministic mock adapter for eval harness.
    
    Supplies recorded fixtures when scenario lists a capability.
    Raises CapabilityNotImplementedError otherwise (I-14).
    """

    def __init__(self, scenario_id: str, capabilities: list[str] | None = None):
        self.scenario_id = scenario_id
        self.capabilities = capabilities or []
        self.call_log: list[dict[str, Any]] = []

    def has_capability(self, capability: str) -> bool:
        """Check if capability is available."""
        return capability in self.capabilities

    async def inspect_repository(
        self, session_id: str, patterns: list[str] | None = None
    ) -> list[dict]:
        """Return recorded inspection findings for this scenario."""
        self.call_log.append(
            {"tool": "inspect_repository", "session_id": session_id, "patterns": patterns}
        )

        if not self.has_capability("inspect_repository"):
            raise CapabilityNotImplementedError(
                capability="repository_inspection",
                context_needed="File patterns, code structure, test coverage",
            )

        finding = INSPECTION_FINDINGS.get(self.scenario_id, "No fixture available")
        
        return [
            {
                "type": "text",
                "text": f"Inspection findings:\n{finding}",
            }
        ]

    def record_action(self, action: str, **kwargs) -> None:
        """Record action for forbidden_actions checking."""
        self.call_log.append({"action": action, **kwargs})

    def get_actions_performed(self) -> list[str]:
        """Return list of action names performed."""
        return [entry.get("action") for entry in self.call_log if "action" in entry]
