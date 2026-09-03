# COH MCP Adapter — Claude Code MCP Server

**Phase 1 deliverable** · 2026-09-03

First (reference) adapter implementing D5 (Claude Code via MCP) with prose rendering P-01…P-06 and archive/checkpoint wiring.

## Purpose

The MCP adapter exposes COH's execution core over the Model Context Protocol using the official Python MCP SDK. It implements:

- **I-06 (Proposal-only)**: LLM output validates through schema + domain policy before state changes
- **I-07 (Diagnosis-free)**: Neutral, observable language in all responses
- **I-09 (Checkpoint provenance)**: Literal `restart_action` + archive references stored
- **I-12 (Archive wiring)**: User/agent/tool events → ArchiveService; on `ARCHIVE_WRITE_FAILED` → `Checkpoint.mark_degraded`
- **I-14 (Honest degradation)**: Missing capability returns `NOT_IMPLEMENTED` with focused request, never fabricated findings
- **P-01…P-06 (Prose rendering)**: Evidence-first, no scaffolding, recap when > threshold, density, protected fields, recovery exemption

## Installation

```bash
cd /path/to/coh
uv sync --all-packages
uv pip install -e "packages/mcp_adapter[dev]"
```

## Usage

### Stdio MCP Server (Claude Code)

Add to your MCP configuration (e.g., `~/.config/claude/mcp.json` or similar):

```json
{
  "mcpServers": {
    "coh": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/coh",
        "coh-mcp"
      ]
    }
  }
}
```

The server starts on stdio and lists tools with snake_case names/args (D10).

### Available Tools

- `create_session` — Create session with intent inference (T1)
- `inspect_repository` — Returns `NOT_IMPLEMENTED` (I-14: capability not yet wired)
- `specify_work` — Propose spec with inspection findings before the block (P-01)
- `confirm_spec` — Confirm/correct spec (T4/T5)
- `create_checkpoint` — Store restart action + archive refs (I-09)
- `recover_session` — Render recovery summary (P-06: prospective framing allowed)
- `get_archive_status` — Archive health visibility (I-12)

## Architecture

```
MCP Tool Call
  ↓
COHHandlers (src/coh_mcp/handlers.py)
  ↓
Execution Core (domain state machine)
  ↓
ArchiveCheckpointWiring (src/coh_mcp/archive_wiring.py)
  ↓
ArchiveService → WriteOutcome
  ↓
  - WRITTEN → Store ArchiveReference on Checkpoint
  - ARCHIVE_WRITE_FAILED → Checkpoint.mark_degraded()
```

Prose rendering via `coh_prose` package:
- `ProsePolicy` enforces P-01…P-06 validation
- `ProseRenderer` renders §4 structured blocks (spec proposal, foreground, recovery, verification, detour)

## Testing

```bash
# Run MCP adapter tests
uv run pytest packages/mcp_adapter/tests -v

# Run with coverage
uv run pytest packages/mcp_adapter/tests --cov=packages/mcp_adapter/src
```

Tests cover:
- Round-trip: create session → persist → archive write
- Archive wiring: successful write stores reference, failed write marks degraded
- I-14: `NOT_IMPLEMENTED` for unimplemented capabilities
- Prose: P-01 (evidence first), P-06 (recovery exemption)

## Trade-offs

1. **Stdio only**: No HTTP/SSE transport yet (deferred to FastAPI app integration)
2. **Minimal handlers**: Only session/spec/checkpoint tools; full CRUD deferred
3. **Persistence wired**: SqlAlchemyUnitOfWork connected to `.coh/coh.db`; additional repositories next
4. **Inspection stub**: `inspect_repository` raises `NOT_IMPLEMENTED` (I-14 test only)
5. **Simplified prose validation**: P-02/P-05 use keyword matching, not full NLP

## Next Actions

1. ✅ ~~Wire persistence layer~~ — Complete: SqlAlchemyUnitOfWork connects to `.coh/coh.db`
2. Implement remaining MCP tools: `plan_work`, `execute_task`, `verify_deliverable`
3. Add FastAPI HTTP/SSE transport for web clients
4. Implement `inspect_repository` capability (filesystem + git inspection)
5. Add P-02/P-05 full NLP-based validation (current: keyword matching)
6. Run full 19-scenario eval suite against adapter output

## Contract Compliance

- ✅ I-06: Proposal-only (handlers validate before state mutation)
- ✅ I-07: Diagnosis-free (no clinical labels in responses)
- ✅ I-09: Checkpoint provenance (restart_action + archive references stored)
- ✅ I-12: Archive wiring (event → ArchiveService → mark_degraded on failure)
- ✅ I-14: `NOT_IMPLEMENTED` for missing capability (never fabricated)
- ✅ P-01: Evidence before conclusion (inspection findings render before spec block)
- ✅ P-02: No scaffolding (preview phrase detection)
- ✅ P-03: Recap when > threshold (renderer adds recap if needed)
- ✅ P-04: Density (prose renderer keeps output compact)
- ✅ P-05: Protected fields (policy validates no drops)
- ✅ P-06: Recovery exemption (recovery summary allows prospective framing)
- ✅ D10: snake_case wire JSON (all tool names, args, response fields)

## Dependencies

- `mcp` — Official Python MCP SDK
- `execution-core` — Pure domain logic (7-state lifecycle, policies)
- `persistence` — SQLAlchemy 2 repositories with SqlAlchemyUnitOfWork → `.coh/coh.db`
- `coh-archive` — Append-only Markdown archive with degrade-and-continue
- `prose` — P-01…P-06 policy enforcement and §4 rendering
