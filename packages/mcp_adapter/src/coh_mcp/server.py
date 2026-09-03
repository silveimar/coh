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
                name="propose_spec",
                description=(
                    "Propose specification via SpecGateService "
                    "(read-only, always permitted)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
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
                description="User confirms or corrects spec proposal (I-02 gate)",
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
                name="get_spec_status",
                description="Get specification status (read-only, always permitted)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="get_foreground",
                description="Get foreground (I-01: NOW + ≤2 NEXT with metadata)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="complete_now",
                description="Complete NOW task (I-05, I-01)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "task_id": {"type": "string"},
                        "completion_notes": {"type": "string"},
                    },
                    "required": ["session_id", "task_id"],
                },
            ),
            Tool(
                name="block_now",
                description="Block NOW task (I-05, I-01)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "task_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["session_id", "task_id", "reason"],
                },
            ),
            Tool(
                name="park_task",
                description="Park task without changing NOW (I-10)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "task_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["session_id", "task_id", "reason"],
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
            Tool(
                name="plan_work",
                description=(
                    "Create executable plan from task list "
                    "(session must be PLAN; persists tasks, seeds I-01 foreground)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action_literal": {"type": "string"},
                                    "done_when_condition": {"type": "string"},
                                    "estimated_minutes": {"type": "integer"},
                                    "energy": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high"],
                                    },
                                    "activation_friction": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high"],
                                    },
                                    "dependencies": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    },
                                },
                                "required": [
                                    "action_literal",
                                    "done_when_condition",
                                    "estimated_minutes",
                                    "energy",
                                    "activation_friction",
                                ],
                            },
                        },
                    },
                    "required": ["session_id", "tasks"],
                },
            ),
            Tool(
                name="execute_task",
                description=(
                    "Execute planned work (T6: PLAN → EXECUTE; "
                    "validates I-01 NOW metadata)"
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
                name="verify_deliverable",
                description=(
                    "Verify deliverable with evidence "
                    "(T7 → T9 complete or T8 return to execute)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "evidence_list": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "criterion_text": {"type": "string"},
                                    "evidence_type": {"type": "string"},
                                    "authority": {
                                        "type": "string",
                                        "enum": [
                                            "tool_verified",
                                            "user_accepted",
                                            "user_reported",
                                            "agent_observed",
                                        ],
                                    },
                                    "result": {
                                        "type": "string",
                                        "enum": [
                                            "pass",
                                            "fail",
                                            "accepted",
                                            "inconclusive",
                                        ],
                                    },
                                    "summary": {"type": "string"},
                                    "source": {"type": "string"},
                                },
                                "required": ["criterion_text", "summary"],
                            },
                        },
                    },
                    "required": ["session_id", "evidence_list"],
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
            elif name == "propose_spec":
                return await handlers.propose_spec(**arguments)
            elif name == "confirm_spec":
                return await handlers.confirm_spec(**arguments)
            elif name == "get_spec_status":
                return await handlers.get_spec_status(**arguments)
            elif name == "get_foreground":
                return await handlers.get_foreground(**arguments)
            elif name == "complete_now":
                return await handlers.complete_now(**arguments)
            elif name == "block_now":
                return await handlers.block_now(**arguments)
            elif name == "park_task":
                return await handlers.park_task(**arguments)
            elif name == "create_checkpoint":
                return await handlers.create_checkpoint(**arguments)
            elif name == "recover_session":
                return await handlers.recover_session(**arguments)
            elif name == "get_archive_status":
                return await handlers.get_archive_status()
            elif name == "plan_work":
                return await handlers.plan_work(**arguments)
            elif name == "execute_task":
                return await handlers.execute_task(**arguments)
            elif name == "verify_deliverable":
                return await handlers.verify_deliverable(**arguments)
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
