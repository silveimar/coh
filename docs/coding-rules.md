# COH — Cognitive Operating Harness — AI Coding Rules & Standards

**Status:** Canonical engineering standards for v0.1 · **Updated:** 2026-08-19
**Supersedes:** `deprecated/AI Coding Rules _ Standards.md`
**Decisions applied:** D1–D10 (see `../COH-Decision-Log.md`) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`

## Executive Summary

COH (Cognitive Operating Harness) is a local-first execution layer that helps solo AI-assisted developers turn intention into completed action: it converts ambiguous requests into confirmed specifications, keeps one NOW task and at most two NEXT tasks in the foreground, preserves decisions and evidence, and provides reliable recovery after interruptions. The authoritative product behavior lives in a pure-Python **Execution Core**; AI output is always a proposal that deterministic domain policy validates before any state change. Success is measured by the PRD's behavioral metrics: 5-second task startability, recovery without chat-history search, 100% foreground compliance, and evidence-backed completion.

The Execution Core owns execution semantics: the lifecycle `INSPECT → SPECIFY → CONFIRM → PLAN → EXECUTE → VERIFY → COMPLETE`, plus **Checkpoint as a cross-cutting event and Recover as an explicit entry command** (Decision D4), together with decisions, drift, parking items, readiness, evidence, and policies.

Keep these concepts separate:

- **Domain workflow:** the authoritative Execution Core state machine.
- **Agent workflow:** replaceable LLM and tool orchestration.
- **Background job:** replaceable asynchronous processing.

## Repository Structure

Monorepo: a uv workspace for Python; a pnpm workspace for TypeScript is planned (Decisions D2, D8).

```
.
├── apps/
│   ├── api/                 # FastAPI application and HTTP/SSE transport
│   ├── worker/              # Huey worker entry point and job registration (planned; Decision D2)
│   └── web/                 # React + Vite application (planned; Phase 3 only — Decision D8)
├── packages/
│   ├── execution-core/      # Pure Python domain model, policies, state machine
│   ├── application/         # Application services
│   ├── persistence/         # SQLAlchemy 2 state store: models, repositories, unit of work
│   │   └── alembic/         # Alembic migration environment and revisions (alembic.ini sits beside it)
│   ├── agent-runtime/       # Provider adapters, prompts, tools, agent workflows (planned)
│   ├── archive/             # Append-only Markdown archive writer/reader
│   ├── prose/               # Prose rendering policy (P-01 to P-06) and output renderers
│   ├── mcp_adapter/         # Python MCP adapter (first adapter: Claude Code — D5)
│   └── python-client/       # Optional typed Python API client (planned)
├── frontend/                # TypeScript frontend (planned; Phase 3 only — Decision D8)
│   └── generated-api/       # Generated TypeScript OpenAPI client; do not edit (planned)
├── tests/                   # All tests; tests/evals/ holds the behavioral evaluations and fixtures (Phase 0 suite)
├── docs/                    # Architecture and implementation documentation
├── pyproject.toml           # Root uv workspace configuration
├── uv.lock                  # Committed Python dependency lockfile
├── package.json             # Root pnpm workspace configuration (planned)
└── pnpm-lock.yaml           # Committed TypeScript dependency lockfile (planned)
```

Within Python packages, use `src/` layouts. Keep the Execution Core free of FastAPI, SQLAlchemy, Huey, MCP, React, and agent-framework imports.

```
packages/execution-core/src/execution_core/
├── domain/
├── state_machine/
├── policies/
└── events/

apps/api/src/coh_api/
├── api/
├── application/
└── composition.py
```

The API has no infrastructure layer of its own: `composition.py` imports the engine, session factory and unit of work from `packages/persistence` (`apps/api/src/coh_api/composition.py:6-7`).

## Project Status

- Maturity: Prototype
- Key technologies: Python 3.15+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite (WAL), Huey, MCP; React, TypeScript, Vite, TanStack Query (Phase 3); OpenAPI 3.1, pytest, Hypothesis, Ruff, Pyright, Vitest, Playwright.
- Monorepo: yes — uv workspace (Python) + pnpm workspace (TypeScript).

## Tech Stack & Conventions

- **Framework:** FastAPI backend with REST + SSE; OpenAPI 3.1 generated from routes. No TypeScript backend or BFF without a documented frontend-specific need.
- **Language:** Python 3.15+ with modern typing and explicit domain types; TypeScript strict mode for frontend code.
- **Package managers:** uv for all Python operations; pnpm for all TypeScript operations. Commit both lockfiles.
- **Database:** SQLite for local-first persistence; verify WAL mode. PostgreSQL migration is a documented infrastructure change (compatibility checks, schema tests, staged Alembic upgrade) — never a domain-model rewrite.
- **ORM:** SQLAlchemy 2 declarative models behind explicit repositories/unit-of-work. Never expose ORM entities through the API or domain layer.
- **Migrations:** Alembic for every schema change. Never modify an applied migration revision outside local development. Alembic is the only migration system in this repository.
- **Auth:** not selected for v0.1 (single local profile). Keep identity behind application dependencies and ports; no provider-specific user models in the Execution Core.
- **Hosting:** local-first. Do not add Docker, Redis, Celery, or cloud infrastructure without an explicit documented requirement (Decisions D1, D7).
- **Archive (P0):** the append-only Markdown interaction archive at `.coh/archive/` is a core invariant. Never overwrite or rewrite an existing entry; corrections are new entries. Archive failures degrade-and-continue (Decision D6): return `archive_write_failed`, mark checkpoint archive status `degraded`, never block the workflow, never lose the in-memory message.
- **Wire JSON casing:** **snake_case for all API, adapter, and MCP JSON** (Decision D10 — amends the previous camelCase note; matches every contract example and Python-native serialization). The generated TypeScript client consumes snake_case types; do not alias to camelCase at the boundary.
- **UI (Phase 3):** React + TypeScript + Vite; semantic HTML, accessible interactions; the UI must support focus, recovery, timeline, and quest-map workflows without encoding execution policy.
- **State management (Phase 3):** TanStack Query for all server state; a small client store only for ephemeral UI state.
- **API contract:** Pydantic models at API/integration boundaries generate the OpenAPI schema. Generate the TypeScript client into `frontend/generated-api/` (Hey API or `openapi-ts` via a checked-in command). Never hand-maintain duplicate types; never edit generated files.
- **Background jobs:** Huey with SQLite initially; API and worker as separate processes; access jobs only through the `JobRunner` protocol — no `@huey.task()` decorators in application code.
- **Agent orchestration:** framework-light direct provider SDK adapters behind `ReasoningProvider` protocols with Pydantic structured outputs. LangGraph optional for durable agent-runtime workflows only; never canonical product execution state.
- **MCP:** a Python adapter calling application services. MCP tools must not write directly to repositories or bypass policy checks. The Claude Code MCP server is the first adapter (Decision D5) and the reference implementation of the PRD adapter contract.
- **Python tooling:** Ruff (lint + format), pytest, Pyright. Root-level configuration.
- **Frontend testing (Phase 3):** Vitest for unit/component; Playwright for critical E2E flows.
- **Observability:** structured logs with correlation IDs. Local-only in v0.1 (Decision D7); OpenTelemetry only when external deployment warrants it.

Use async Python only at integration boundaries: HTTP, SSE, LLM calls, MCP, external APIs, parallel inspection. Keep domain models, policies, state transitions, and ordinary transformations synchronous.

## Code Style Rules

### Naming Conventions

- Python packages/modules: `snake_case` (`execution_readiness.py`). Classes/enums/Pydantic models: `PascalCase`. Functions/variables/fields: `snake_case`. Constants: `UPPER_SNAKE_CASE`.
- TypeScript component files: `PascalCase` (`TaskTimeline.tsx`); non-component files: `kebab-case` (`use-task-session.ts`); variables/functions `camelCase`; types/interfaces `PascalCase`.
- Directories: `kebab-case` in frontend code, `snake_case` in Python packages.
- Database tables/columns: `snake_case`.
- Wire JSON fields: `snake_case` end to end (Decision D10).
- Name domain concepts precisely: `Checkpoint`, `ParkingItem`, `DriftEvent`, `TaskProgressRecord`, `ExecutionReadiness`, `RestartAction`. Never vague names (`data`, `handler`, `manager`, `utils`, `misc`) for domain behavior.

### Imports & Exports

- Python import order: stdlib, third-party, local — one blank line between groups. TypeScript: React, third-party, local.
- Prefer named exports in TypeScript; default exports only where framework conventions require.
- Cross package boundaries only through public interfaces; no private-module imports; no circular imports — move shared protocols/value objects to the lowest appropriate layer.
- Never import FastAPI, SQLAlchemy, Huey, or provider SDKs into `packages/execution-core/`.

### TypeScript (Phase 3)

- `strict` mode; no `any`; `unknown` for untrusted values, narrowed before use.
- Use generated API types from `frontend/generated-api/` for all server contracts; explicit return types for exported functions and hooks.
- Functional components; hooks for UI concerns only; no `useEffect` for server data fetching — TanStack Query.
- No execution policies, readiness calculations, or state transitions in React components.

### Formatting

- Ruff format + check before committing; Prettier + ESLint for TypeScript, centralized config.
- 88-character Python lines unless the formatter excepts.
- No inline lint-rule disables without a concise justification and a linked issue or test case.

## Component & Architecture Patterns

### API Routes

- Routes stay thin: authenticate, validate transport input, invoke one application service, map known outcomes to responses.
- Pydantic validation on all route input and output. Routes in `apps/api/src/coh_api/api/routes/`; transport schemas in `api/schemas/`; use cases in `application/`; domain rules in `execution-core`.
- Consistent error object: stable machine-readable code, user-safe message, correlation ID.
- Commands require idempotency keys **and** `expected_version` optimistic concurrency where they mutate execution state — idempotency does not replace concurrency control.
- Version externally consumed API paths before breaking contracts; regenerate and commit the TypeScript client after schema changes.
- Keep synchronous domain commands synchronous; enqueue only long-running or non-interactive work.

Do: call an application service that records a decision and applies policy checks.
Don't: update a repository directly from a route or MCP tool.

### Data Fetching & State (Phase 3)

- FastAPI routes are the only HTTP boundary for the web client; generated client functions behind feature-level TanStack Query hooks; query keys include every server-state input.
- Model loading, empty, error, and success states for every asynchronous screen; SSE events reconciled with the query cache; server-side pagination for growing collections.
- Backend Pydantic validation is authoritative; React Hook Form + Zod only for non-trivial forms.
- Domain state lives in the database, reconstructed through application services: relational current state + append-only domain events + explicit checkpoint snapshots. No full event sourcing without an explicit decision.
- Never share a SQLAlchemy `AsyncSession` across concurrent tasks; create sessions per request, command, or worker scope.

## Do's and Don'ts

### Do

- DO keep the Execution Core the sole authority for execution state, transitions, readiness, autonomy, drift, evidence, and verification policies.
- DO represent domain workflow state explicitly and persist transitions, checkpoints, decisions, progress records, and evidence.
- DO keep the domain layer deterministic and dependency-light.
- DO use Pydantic models for API I/O, LLM structured output, worker payloads, and MCP-facing schemas.
- DO treat LLM output as a proposal that domain policy must validate before it changes authoritative state.
- DO use protocols for replaceable boundaries: `ReasoningProvider`, `JobRunner`, repositories, filesystem access, archive writer, MCP integration.
- DO write every archive entry append-only, with stable anchors, and link checkpoints to archive references.
- DO create Alembic migrations for every schema change and test upgrades from an empty database.
- DO keep job handlers idempotent and safe to retry, reporting durable status, failure reason, timestamps, and correlation IDs.
- DO regenerate the TypeScript client after route-schema changes; handle loading/error/retry/empty/recovery states in async flows.
- DO emit structured logs and propagate correlation IDs across HTTP requests, jobs, and agent calls.
- DO write tests before or alongside changes to policies, state transitions, persistence mappings, and API behavior.
- DO preserve accessible, diagnosis-neutral language; never frame users as defective in recovery or drift guidance.
- DO ask before adding a dependency, changing a public API contract, introducing cloud infrastructure, or altering execution semantics.

### Don't

- DON'T use `any` in TypeScript or untyped dictionaries as substitutes for Python domain models.
- DON'T put FastAPI, SQLAlchemy, Huey, MCP, React, or agent-framework dependencies in `execution-core`.
- DON'T let an LLM, LangGraph graph, or queue pipeline become the canonical execution state machine.
- DON'T model human-confirmed workflow steps as queue task chains.
- DON'T use `useEffect` for server data fetching or cache synchronization.
- DON'T hand-write duplicate TypeScript versions of Pydantic API schemas or edit `frontend/generated-api/`.
- DON'T expose ORM entities through routes or persist raw provider responses as trusted domain facts.
- DON'T place business logic in React components, FastAPI routes, MCP tools, SQLAlchemy models, or Huey task decorators.
- DON'T share one `AsyncSession` across concurrent coroutines, or make every Python function `async`.
- DON'T add Redis, Celery, Kafka, Temporal, Docker, or a cloud service without a documented scale or durability requirement.
- DON'T install new dependencies without approval.
- DON'T silently convert uncertain, inferred, or model-generated information into confirmed requirements, decisions, or evidence.
- DON'T bypass readiness, autonomy, foreground, language, drift, archive, or verification policies for convenience.
- DON'T rewrite applied migration history, modify generated client code, or overwrite archive entries.

## Testing & Quality

### Frameworks

- Unit/integration: pytest, test files named `test_*.py` (or `*_test.py` — pick one per package and stay consistent), under the root `tests/` directory, mirroring the source tree.
- Property-based: Hypothesis for state-machine and policy invariants.
- E2E: MCP-adapter critical flows in v0.1; Playwright for web workflows in Phase 3.
- Static analysis: Pyright for Python; `tsc --noEmit` for TypeScript.

### What to Test

- All deterministic domain policies: readiness, autonomy (permission matrix), foreground, drift, language, verification.
- Every state-machine transition, invalid transition, and checkpoint/recover path — including interruption creating a complete progress record before foreground switch.
- Archive: append-only completeness for every user input, agent output, and available tool result; degrade-and-continue failure behavior; rotation; atomic writes; tolerant reads.
- Application services with fake ports; integration tests against SQLite where persistence behavior matters.
- API routes: validation, authorization boundaries when present, response contracts, idempotency, concurrency conflicts, error mapping.
- Generated-client compatibility via contract checks or regeneration in CI.
- Job handlers: idempotency, retries, durable status updates, safe failure handling.
- Provider adapters with recorded fixtures or fakes; ordinary CI never depends on live model-provider calls.
- E2E critical paths: create/specify work → confirm and plan → start/complete a task → checkpoint → recover context → handle a failed asynchronous job.

### Quality Gates

- `uv run ruff check .` · `uv run ruff format --check .` · `uv run pyright` · `uv run pytest` — all must pass.
- Frontend (Phase 3): lint/format checks, `pnpm exec tsc --noEmit`, `pnpm test`.
- Execution Core coverage ≥90% lines; critical state-machine branches covered; behavioral evals (Phase 0 suite) pass thresholds.
- Alembic migrations upgrade a fresh SQLite database successfully.
- Regenerate the OpenAPI TypeScript client; CI fails on stale generated output.
- Review required for public API, database migration, execution-policy, archive-format, and dependency changes.

## Common Pitfalls

- **Treating agent orchestration state as product execution state.** Persist product state in the Execution Core; LangGraph/provider workflows are replaceable runtime details. Example separation: `AgentProposal{source: "llm", proposal: CheckpointProposal}` parsed and validated by the Execution Core before any state update.
- **Letting model output declare readiness or make authoritative decisions.** Parse into Pydantic proposals; apply deterministic domain policies before updating state.
- **Modeling human-in-the-loop workflow as Huey/Celery task chains.** Persist the domain state machine; resume through explicit application commands after user input.
- **Spreading Huey decorators through use cases.** Depend on `JobRunner`; register Huey implementations only in worker composition code.
- **Introducing Redis/Celery before the local-first workload requires them.** SQLite-backed Huey first; reassess only with documented durability/throughput/multi-host requirements.
- **Making everything async.** Async at I/O boundaries; deterministic domain code stays synchronous and easy to test.
- **Sharing `AsyncSession` across concurrent operations.** One session scope per request/command/worker execution.
- **Hand-maintaining duplicate schemas.** Pydantic + FastAPI OpenAPI is the source of truth; generate the TS client; never edit generated files.
- **Returning ORM models or raw exceptions from routes.** Map outcomes to Pydantic response models and stable safe error codes.
- **Putting policy calculations in the UI for responsiveness.** UI previews are allowed; backend policy results are authoritative and displayed distinctly from drafts.
- **Treating `domain_events` as full event sourcing.** Append-only events for auditability alongside relational current state and explicit checkpoints.
- **Writing integrations against domain internals.** MCP, filesystem, Git, and provider integrations go through application services and ports.
- **Treating archive writes as optional or rewritable.** Every user-visible interaction gets an append-only entry; failures degrade visibly (`archive_write_failed`, checkpoint `degraded`) and never block or silently drop work.
- **Changing execution semantics inside a feature without documenting it.** Add or update a decision record (see `../COH-Decision-Log.md`), policy tests, and migration/contract changes before changing behavior.
- **Stigmatizing or ambiguous language in recovery and drift experiences.** Use neutral, observable terms: "context changed," "decision needed," "blocked," "recovery step."
