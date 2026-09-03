"""MCP server implementation using official Python MCP SDK."""

from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from .errors import CapabilityNotImplementedError
from .handlers import COHHandlers


def create_server(project_root: Path | None = None) -> Server:
    """
    Create COH MCP server.

    Args:
        project_root: Project root directory (defaults to current directory)

    Returns:
        Configured MCP Server instance
    """
    if project_root is None:
        project_root = Path.cwd()

    server = Server("coh")
    handlers = COHHandlers(project_root)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available COH tools (snake_case names per D10)."""
        return [
            Tool(
                name="create_session",
                description="Create new COH session with intent inference",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "user_input": {"type": "string"},
                        "intent": {
                            "type": "string",
                            "enum": [
                                "execute",
                                "plan",
                                "brainstorm",
                                "review",
                                "study",
                                "recover",
                            ],
                        },
                    },
                    "required": ["project_id", "user_input"],
                },
            ),
            Tool(
                name="inspect_repository",
                description=(
                    "Read-only inspection gathering "
                    "(I-14: returns NOT_IMPLEMENTED if unavailable)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "patterns": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="specify_work",
                description=(
                    "Derive and propose specification (WHAT/WHY/DELIVERABLE/DONE WHEN)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "inspection_findings": {"type": "string"},
                        "what": {"type": "string"},
                        "why": {"type": "string"},
                        "deliverable": {"type": "string"},
                        "done_when": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "session_id",
                        "what",
                        "why",
                        "deliverable",
                        "done_when",
                    ],
                },
            ),
            Tool(
                name="confirm_spec",
                description="User confirms or corrects spec proposal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "confirmed": {"type": "boolean"},
                        "corrections": {"type": "object"},
                    },
                    "required": ["session_id", "confirmed"],
                },
            ),
            Tool(
                name="create_checkpoint",
                description=(
                    "Create checkpoint for recovery "
                    "(I-09: stores restart_action + archive references)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "restart_action": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["session_id", "restart_action"],
                },
            ),
            Tool(
                name="recover_session",
                description=(
                    "Recover from latest checkpoint (I-09: navigate to archive records)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="get_archive_status",
                description=(
                    "Get archive integration health (I-12: degradation visibility)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[dict]:
        """Handle tool invocations."""
        try:
            if name == "create_session":
                return await handlers.create_session(**arguments)
            elif name == "inspect_repository":
                return await handlers.inspect_repository(**arguments)
            elif name == "specify_work":
                return await handlers.specify_work(**arguments)
            elif name == "confirm_spec":
                return await handlers.confirm_spec(**arguments)
            elif name == "create_checkpoint":
                return await handlers.create_checkpoint(**arguments)
            elif name == "recover_session":
                return await handlers.recover_session(**arguments)
            elif name == "get_archive_status":
                return await handlers.get_archive_status()
            else:
                raise ValueError(f"Unknown tool: {name}")

        except CapabilityNotImplementedError as e:
            return [
                {
                    "type": "text",
                    "text": (
                        f"NOT_IMPLEMENTED: {e.capability}\nNeed: {e.context_needed}"
                    ),
                }
            ]

    return server


async def main():
    """Run MCP server on stdio."""
    project_root = Path.cwd()
    server = create_server(project_root)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
