# COH API — FastAPI HTTP Adapter

**Phase 1 HTTP transport** for COH's SpecGateService and ForegroundService. Thin routes that validate input, call application services, and map outcomes to HTTP responses. No Huey worker, no React UI, no remote telemetry.

## Status

**v0.1 Local-first FastAPI adapter** — ready for local development. MCP tools calling these services are a later slice (tracked separately).

## Architecture

```
apps/api/src/coh_api/
├── api/
│   ├── routes/
│   │   ├── spec_gate.py     # Spec gate routes (propose, confirm, revise, status, mutation-allowed)
│   │   └── foreground.py    # Foreground routes (get, complete_now, block_now, park, interrupt)
│   └── schemas/
│       ├── common.py         # Shared schemas (ErrorResponse, IdempotencyRequest)
│       ├── spec_gate.py      # Spec gate request/response models
│       └── foreground.py     # Foreground request/response models
├── application/             # Re-exports of packages/application services
├── composition.py           # Service container: SQLite WAL, UnitOfWork, service wiring
└── main.py                  # FastAPI app with OpenAPI, error handlers, lifespan
```

**Design principles:**
- **Thin routes:** validate → call one service → map outcomes. No domain logic in routes.
- **Diagnosis-free errors:** stable machine codes, user-safe messages, no stigmatizing language.
- **I-02 enforcement:** blocked mutations return 4xx; read-only inspection always permitted.
- **I-01 enforcement:** foreground validates exactly 1 NOW + ≤2 NEXT with required metadata.
- **Snake_case wire JSON** (Decision D10): all request/response fields, enum values, error codes.
- **No FastAPI imports in execution-core:** domain stays pure Python.

## Running Locally

### Prerequisites

- Python 3.12+
- uv package manager

### Installation

From workspace root:

```bash
uv sync --all-packages
uv pip install -e "apps/api[dev]"
```

### Start the server

```bash
uv run uvicorn coh_api.main:app --reload
```

**Local-only binding** (D7): uvicorn defaults to 127.0.0.1:8000. Add `--host 0.0.0.0` only when needed for container/VM access.

**Database:** SQLite at `.coh/coh.db` (WAL mode, auto-created on first run).

**OpenAPI docs:** http://localhost:8000/docs

**Health check:** http://localhost:8000/health

### Example request

```bash
# Check spec gate status (read-only, always permitted)
curl http://localhost:8000/api/v1/spec-gate/status/{session_id}

# Propose a specification
curl -X POST http://localhost:8000/api/v1/spec-gate/propose \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "what": "Implement user authentication",
    "why": "Security requirement",
    "deliverable": "Working login/logout with JWT",
    "done_when": ["User can login", "User can logout"]
  }'

# Get foreground
curl http://localhost:8000/api/v1/foreground/{session_id}
```

## Testing

Run all API tests:

```bash
uv run pytest apps/api/tests
```

Run with coverage:

```bash
uv run pytest apps/api/tests --cov=apps/api/src --cov-report=term
```

**Key test scenarios:**
- I-02: blocked mutations return 422 when spec is missing required fields
- I-01: foreground enforces NOW/NEXT constraints and metadata requirements
- Snake_case: all wire JSON uses snake_case field names
- Diagnosis-free: error messages use neutral, observable language

## Routes

### Spec Gate (I-02 enforcement)

**POST** `/api/v1/spec-gate/propose` — Propose spec (read-only, always permitted)
**POST** `/api/v1/spec-gate/confirm` — Confirm spec (material mutation, requires readiness=READY)
**POST** `/api/v1/spec-gate/revise` — Revise spec (creates new revision)
**GET** `/api/v1/spec-gate/status/{session_id}` — Get spec status (read-only)
**GET** `/api/v1/spec-gate/mutation-allowed/{session_id}` — Check mutation allowed (read-only)

### Foreground (I-01 enforcement)

**GET** `/api/v1/foreground/{session_id}` — Calculate foreground (read-only)
**POST** `/api/v1/foreground/complete-now` — Complete NOW task (material mutation)
**POST** `/api/v1/foreground/block-now` — Block NOW task (material mutation)
**POST** `/api/v1/foreground/park` — Park task (material mutation, preserves NOW)
**POST** `/api/v1/foreground/interrupt-now` — Interrupt NOW task (material mutation)
**GET** `/api/v1/foreground/status/{session_id}` — Get foreground status (read-only)

### Health

**GET** `/health` — Health check (returns `{"status": "healthy"}`)

## Trade-offs

### What's included

✅ Thin FastAPI routes wrapping SpecGateService + ForegroundService
✅ Pydantic request/response schemas with snake_case (D10)
✅ I-02 enforcement: blocked mutations return 422 with stable error codes
✅ I-01 enforcement: foreground validates NOW/NEXT constraints
✅ OpenAPI 3.1 schema generated from FastAPI routes
✅ SQLite WAL database at `.coh/coh.db`
✅ Diagnosis-free error messages
✅ TestClient integration tests for invariants
✅ CI integration (ruff lint/format + pytest)

### What's deferred

❌ **Huey worker:** no async job processing in v0.1 (local-first, single-process)
❌ **React UI:** output is agent-rendered via MCP adapter (Phase 3)
❌ **MCP tools calling these routes:** tracked as separate slice
❌ **TypeScript client generation:** no frontend yet (OpenAPI available for future use)
❌ **Authentication:** single local profile in v0.1
❌ **Remote telemetry:** local-only (Decision D7)
❌ **Docker/Redis/cloud:** local-first SQLite (Decision D7)
❌ **Idempotency store:** idempotency_key accepted but not yet enforced (tracked for Phase 2)
❌ **Optimistic concurrency control:** expected_version accepted but not yet enforced (tracked for Phase 2)

### Known limitations

- **Service composition:** Each request creates a new UnitOfWork. For long-running operations, this is correct (one UoW per command). For read-heavy workloads, consider connection pooling in Phase 2.
- **Progress records:** I-05 progress records are created but not yet persisted (domain models exist, persistence mapping deferred to next slice).
- **Checkpoint/Recovery routes:** not included in this slice (covered by MCP adapter).
- **Verification/completion routes:** deferred to VERIFY/COMPLETE slice.
- **Parking items:** ForegroundService references them but persistence not yet wired.

## Next Actions

1. **MCP tools** calling these HTTP routes (separate slice)
2. **Idempotency enforcement** with Redis/SQLite store
3. **Optimistic concurrency control** enforcement via expected_version
4. **Progress record persistence** (I-05 full implementation)
5. **Checkpoint/Recovery HTTP routes** (for non-MCP clients)
6. **Huey worker integration** for async inspection/verification
7. **TypeScript client generation** when UI is added (Phase 3)

## Relationship to Other Packages

- **execution-core:** Domain models, state machine, policies (pure Python, no FastAPI)
- **persistence:** SQLAlchemy repositories, UnitOfWork, SQLite WAL (used via composition.py)
- **application:** SpecGateService, ForegroundService (wrapped by routes)
- **mcp_adapter:** Claude Code MCP server (separate adapter, not imported here)

## Decision Log References

- **D7:** Local-first, no cloud infrastructure in v0.1
- **D8:** No UI in v0.1, agent-rendered output only
- **D10:** snake_case wire JSON everywhere (API, MCP, events)

## Coding Rules Compliance

✅ Thin routes (validate, call service, map outcomes)
✅ No FastAPI imports in execution-core
✅ SQLite WAL via persistence package
✅ Pydantic validation on all route input/output
✅ Diagnosis-free error messages (neutral language)
✅ Snake_case wire JSON (D10)
✅ Tests for I-02 and I-01 enforcement
✅ Ruff lint/format passing
✅ CI integration

## Development

### Formatting

```bash
uv run ruff format apps/api
```

### Linting

```bash
uv run ruff check apps/api
```

### Type checking (when Pyright is added)

```bash
uv run pyright apps/api
```

---

**Questions?** See `AGENTS.md`, `docs/coding-rules.md`, `docs/decision-log.md` in the workspace root.
