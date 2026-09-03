"""MCP adapter error types implementing I-14."""


class COHMCPError(Exception):
    """Base error for COH MCP adapter."""

    pass


class CapabilityNotImplementedError(COHMCPError):
    """
    I-14: Missing adapter capability returns NOT_IMPLEMENTED.

    Never fabricates findings; returns focused request for unavailable context only.
    """

    def __init__(self, capability: str, context_needed: str):
        self.capability = capability
        self.context_needed = context_needed
        super().__init__(
            f"Capability '{capability}' not implemented. Need: {context_needed}"
        )
