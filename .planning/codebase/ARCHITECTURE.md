---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
<!-- refreshed: 2026-10-21 -->

# Architecture

**Analysis Date:** 2026-10-21

## System Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                         Adapters (entry)                          │
├───────────────────────────────┬──────────────────────────────────┤
│  MCP adapter (Claude Code)    │  HTTP adapter (FastAPI)           │
│  `packages/mcp_adapter/src/   │  `apps/api/src/coh_api/`          │
│   coh_mcp/server.py`          │   main.py, api/routes/*.py        │
│  `.../coh_mcp/handlers.py`    │  `composition.py` (DI container)  │
└──────────────┬────────────────┴───────────────┬──────────────────┘
               │ (handlers also call repos/SM   │
               │  directly - see Anti-Patterns) │
               ▼                                ▼
┌──────────────────────────────────────────────────────────────────┐
│               Application services                                │
│  `packages/application/src/coh_application/`                      │
│   spec_gate_service.py, foreground_service.py                     │
└──────────────┬───────────────────────────────────┬───────────────┘
               ▼                                   ▼
┌───────────────────────────────┐   ┌──────────────────────────────┐
│ Execution Core (pure domain)  │   │ Persistence ports (Protocol) │
│ `packages/execution-core/src/ │   │ `packages/persistence/src/   │
│  execution_core/`             │   │  persistence/ports/`         │
│ domain/ policies/ events/     │   └──────────────┬───────────────┘
│ state_machine/lifecycle.py    │                  ▼
└───────────────────────────────┘   ┌──────────────────────────────┐
                                    │ SQLAlchemy infrastructure    │
┌───────────────────────────────┐   │ `.../persistence/            │
│ Prose policy / renderer       │   │  infrastructure/`            │
│ `packages/prose/src/coh_prose`│   │ + Alembic `packages/         │
└───────────────────────────────┘   │  persistence/alembic/`       │
┌───────────────────────────────┐   └──────────────┬───────────────┘
│ Markdown archive (append-only)│                  ▼
│ `packages/archive/src/        │        `.coh/coh.db` (SQLite WAL)
│  coh_archive/`                │──────► `.coh/archive/` (Markdown)
└───────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| StateMachine | Lifecycle transitions (INSPECT -> SPECIFY -> CONFIRM -> PLAN -> EXECUTE -> VERIFY -> COMPLETE, plus recover/revise/correct), guards, command idempotency | `packages/execution-core/src/execution_core/state_machine/lifecycle.py` |
| Domain entities | ExecutionSession, Specification, Task, Evidence, Checkpoint, Decision, ParkingItem, Foreground, Command, enums | `packages/execution-core/src/execution_core/domain/` |
| Policies | Deterministic validation: readiness, permission, completion, integrity, parking, foreground (NOW + NEXT 2) | `packages/execution-core/src/execution_core/policies/` |
| Domain events | Event types emitted by the core | `packages/execution-core/src/execution_core/events/domain_events.py` |
| SpecGateService | Propose/confirm spec, readiness status, mutation-permission checks | `packages/application/src/coh_application/spec_gate_service.py` |
| ForegroundService | Calculate foreground, complete/block/park NOW task | `packages/application/src/coh_application/foreground_service.py` |
| Repository ports | `Protocol` interfaces for each aggregate + `UnitOfWork` | `packages/persistence/src/persistence/ports/state_store.py` |
| SQLAlchemy infra | Engine/WAL pragma, ORM models, domain<->ORM mappers, repositories, UoW | `packages/persistence/src/persistence/infrastructure/` |
| ArchiveService | Append-only Markdown interaction archive under `.coh/archive/` | `packages/archive/src/coh_archive/service.py`, `markdown.py`, `paths.py` |
| ProsePolicy / ProseRenderer | Prose rules P-01..P-06 (evidence-first, no scaffolding, recap threshold, protected fields) and rendering of agent-facing output | `packages/prose/src/coh_prose/policy.py`, `renderer.py` |
| MCP server | Tool registry (snake_case names), stdio transport, dispatch | `packages/mcp_adapter/src/coh_mcp/server.py` |
| COHHandlers | Per-tool orchestration: core + persistence + archive + prose | `packages/mcp_adapter/src/coh_mcp/handlers.py` |
| ArchiveCheckpointWiring | Archive writes; on failure marks checkpoint degraded (I-12) | `packages/mcp_adapter/src/coh_mcp/archive_wiring.py` |
| FastAPI app | Routers under `/api/v1`, `/health`, diagnosis-free error handlers | `apps/api/src/coh_api/main.py` |
| ServiceContainer | Engine + session factory, builds UoW and services | `apps/api/src/coh_api/composition.py` |

## Pattern Overview

**Overall:** Hexagonal (ports and adapters) in a uv workspace monorepo, with a pure deterministic domain core.

**Key Characteristics:**
- The Execution Core is authoritative and framework-free (only `pydantic`, per `packages/execution-core/pyproject.toml`). AI output is proposal-only and validated by policies before any state change.
- Persistence is reached through `Protocol` ports and a Unit of Work (`persistence.ports.state_store.UnitOfWork`); SQLAlchemy is confined to `persistence/infrastructure/`.
- Two adapters (MCP over stdio, FastAPI over HTTP) sit on top of application services.
- Archive is a side channel: failures degrade the checkpoint and continue, never block.
- Wire JSON and MCP tool names are snake_case (D10).

## Layers

**Execution Core:**
- Purpose: Domain model, state machine, policies, invariants I-01..I-14
- Location: `packages/execution-core/src/execution_core/`
- Contains: Pydantic models, enums, static policy classes, `StateMachine`, exceptions (`TransitionError`, `CapabilityNotImplemented`, `PermissionDenied`, `ReadinessViolation`)
- Depends on: `pydantic` only
- Used by: application, persistence (mappers), mcp_adapter, tests

**Application:**
- Purpose: Use-case orchestration over a `UnitOfWork`
- Location: `packages/application/src/coh_application/`
- Contains: `SpecGateService`, `ForegroundService` (constructor takes `uow`)
- Depends on: execution_core, `persistence.ports`
- Used by: `apps/api`, `packages/mcp_adapter`

**Persistence:**
- Purpose: Durable state store (SQLite WAL at `.coh/coh.db`)
- Location: `packages/persistence/src/persistence/` (`ports/`, `infrastructure/`), migrations in `packages/persistence/alembic/versions/`
- Depends on: SQLAlchemy, Alembic, execution_core
- Used by: application services (via ports), adapters (for wiring the concrete UoW)

**Archive:**
- Purpose: Append-only Markdown record of user/agent/tool interactions
- Location: `packages/archive/src/coh_archive/`
- Used by: `packages/mcp_adapter/src/coh_mcp/archive_wiring.py`

**Prose:**
- Purpose: Output contract rendering and prose-rule validation
- Location: `packages/prose/src/coh_prose/`
- Used by: `packages/mcp_adapter/src/coh_mcp/handlers.py` (lazy imports inside handler methods)

**Adapters:**
- MCP: `packages/mcp_adapter/src/coh_mcp/` (console script `coh-mcp = coh_mcp.server:main`)
- HTTP: `apps/api/src/coh_api/` (`app = create_app()` in `main.py`)

## Data Flow

### Primary Request Path (MCP tool call)

1. Claude Code calls a tool over stdio; `call_tool` dispatches by name (`packages/mcp_adapter/src/coh_mcp/server.py:337`)
2. `COHHandlers.<tool>` loads state via `SqlAlchemyUnitOfWork(self.session_factory)` (`packages/mcp_adapter/src/coh_mcp/handlers.py:41`)
3. Transition validated by `StateMachine` / policies or delegated to `SpecGateService` / `ForegroundService`
4. Session, checkpoint, tasks persisted; UoW `__exit__` commits
5. Interaction archived through `ArchiveCheckpointWiring` (degrades on failure)
6. Response text rendered with `ProseRenderer` and returned as `[{"type": "text", "text": ...}]`

### HTTP Request Path

1. FastAPI route under `/api/v1/spec-gate` or `/api/v1/foreground` (`apps/api/src/coh_api/api/routes/`)
2. `get_container()` -> `with container.create_uow() as uow:` -> `container.<x>_service(uow)` (`apps/api/src/coh_api/api/routes/spec_gate.py:28`)
3. Service returns domain object; route maps it to a Pydantic schema in `apps/api/src/coh_api/api/schemas/`
4. `ValueError` from services becomes `HTTPException`; uncaught errors return `{"error_code": "internal_error"}` (`apps/api/src/coh_api/main.py:56`)

### Archive Degradation Flow

1. Handler calls `archive_wiring.archive_user_input / archive_agent_output / archive_tool_event`
2. `ArchiveService` writes Markdown, returns `WriteOutcome`
3. `ARCHIVE_WRITE_FAILED` -> `checkpoint.mark_degraded()` and a warning log; work continues (`packages/mcp_adapter/src/coh_mcp/archive_wiring.py:64`)

**State Management:**
- All durable state lives in SQLite at `<project_root>/.coh/coh.db`; each request opens a fresh UoW. No in-memory session cache beyond `StateMachine` command records and archive-wiring counters.

## Key Abstractions

**ExecutionSession + LifecycleState:**
- Purpose: The aggregate tracked through the lifecycle
- Examples: `packages/execution-core/src/execution_core/domain/session.py`, `domain/enums.py`
- Pattern: Pydantic model mutated only via `StateMachine` transitions

**Policy classes:**
- Purpose: Deterministic validators returning decisions or raising domain exceptions
- Examples: `packages/execution-core/src/execution_core/policies/foreground_policy.py`, `completion_policy.py`
- Pattern: Classes with `@staticmethod` methods, no I/O

**UnitOfWork + Repository Protocols:**
- Purpose: Transaction boundary and aggregate access
- Examples: `packages/persistence/src/persistence/ports/state_store.py`, `infrastructure/unit_of_work.py`, `infrastructure/repositories.py`
- Pattern: Context manager; `uow.sessions`, `uow.tasks`, `uow.specifications`, `uow.checkpoints`, `uow.evidence`, `uow.decisions`, `uow.parking_items`; optional `idempotency_key` on writes

**Command:**
- Purpose: Idempotent command envelope checked by the state machine
- Examples: `packages/execution-core/src/execution_core/domain/commands.py`

## Entry Points

**MCP server:**
- Location: `packages/mcp_adapter/src/coh_mcp/server.py` (`main()`; script `coh-mcp`)
- Triggers: Claude Code over stdio
- Responsibilities: 18 tools (create_session, inspect_repository, specify_work, propose_spec, confirm_spec, get_spec_status, get_foreground, complete_now, block_now, park_task, create_checkpoint, recover_session, get_archive_status, plan_work, execute_task, verify_deliverable, ...)

**HTTP API:**
- Location: `apps/api/src/coh_api/main.py` (`app`)
- Triggers: uvicorn
- Responsibilities: spec-gate and foreground routes, `/health`, OpenAPI at `/docs`

**Migrations:**
- Location: `packages/persistence/alembic.ini`, `packages/persistence/alembic/env.py`

## Architectural Constraints

- **Threading:** Async MCP handlers over synchronous SQLAlchemy sessions; FastAPI routes are sync `def`.
- **Global state:** `_container` module global in `apps/api/src/coh_api/composition.py`; `init_services()` is a no-op if already set (tests pre-seed it).
- **Purity:** No FastAPI, SQLAlchemy, Huey, MCP or provider SDK imports in `packages/execution-core`.
- **Local-first:** No cloud, telemetry or UI; DB and archive default to `.coh/` under the working directory / project root.
- **Circular imports:** None detected; prose is imported lazily inside handler methods.

## Anti-Patterns

### MCP handlers bypass application services

**What happens:** `COHHandlers` opens `SqlAlchemyUnitOfWork` and calls repositories directly (about 43 `uow.<repo>` calls) and drives `StateMachine` itself in `packages/mcp_adapter/src/coh_mcp/handlers.py`.
**Why it's wrong:** Violates the rule "MCP tools call application services, never repositories"; business logic duplicates and drifts between adapters.
**Do this instead:** Add a service method in `packages/application/src/coh_application/` and call it from the handler, as routes do in `apps/api/src/coh_api/api/routes/spec_gate.py`.

### Adapter-built persistence wiring duplicated

**What happens:** Both `handlers.py` (`__init__`) and `apps/api/src/coh_api/composition.py` construct the engine and `.coh/coh.db` path independently.
**Why it's wrong:** Two sources of truth for DB location and initialization (`init_db` only in MCP path).
**Do this instead:** Share one composition helper; keep adapters thin.

### Oversized handler module

**What happens:** `handlers.py` is ~1460 lines covering every tool.
**Do this instead:** Put new orchestration in application services; keep handlers to argument parsing, service call, prose rendering.

## Error Handling

**Strategy:** Domain raises typed exceptions; adapters translate to neutral, diagnosis-free messages (I-07).

**Patterns:**
- `TransitionError(message, blocked_reason, remediation)` and `CapabilityNotImplemented` in `lifecycle.py`; MCP-side `CapabilityNotImplementedError` in `packages/mcp_adapter/src/coh_mcp/errors.py` (I-14 NOT_IMPLEMENTED)
- Services raise `ValueError` for missing entities; routes map to `HTTPException`
- Global FastAPI handlers return `{"error_code", "message"}` JSON
- Archive failures never raise to callers; they degrade the checkpoint

## Cross-Cutting Concerns

**Logging:** stdlib `logging` (`logger.warning` in archive wiring); no remote telemetry.
**Validation:** Pydantic models in core and API schemas; policies enforce invariants.
**Authentication:** None (local single-user).

---

*Architecture analysis: 2026-10-21*
