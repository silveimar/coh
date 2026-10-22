---
last_mapped_commit: d2b31b774e3d57f71984cc065d5f59a3641ea9ef
last_mapped_at: 2026-10-21
---
# Codebase Structure

**Analysis Date:** 2026-10-21

## Directory Layout

```
coh/
├── packages/
│   ├── execution-core/     # Pure domain: domain/, policies/, events/, state_machine/ (import name execution_core)
│   ├── application/        # Application services (coh_application)
│   ├── persistence/        # Ports + SQLAlchemy infra + alembic/ (import name persistence)
│   ├── archive/            # Append-only Markdown interaction archive (coh_archive)
│   ├── prose/              # Prose policy + renderer (coh_prose)
│   └── mcp_adapter/        # MCP server for Claude Code (coh_mcp)
├── apps/
│   └── api/                # FastAPI HTTP adapter (coh_api)
├── tests/
│   ├── packages/<pkg>/     # Unit/integration tests per package
│   ├── apps/api/           # API integration tests
│   ├── evals/              # Behavioral scenarios (YAML), schema, harness
│   └── guard/              # Tests for the checks-guard CI script
├── docs/                   # Contract, rules, decision log, ADRs, feature specs, glossary
├── .github/                # CI workflows + scripts/checks_guard.py
├── pyproject.toml          # uv workspace root (members packages/*, apps/*)
├── uv.lock                 # Locked dependencies
├── pytest.ini / .coveragerc
├── .python-version         # Python floor
├── AGENTS.md / CLAUDE.md   # Agent instructions
├── FLEET-POLICY.md         # Auto / Ask / Never actions
└── CONTRIBUTING.md         # Workflow and Definition of Done
```

## Directory Purposes

**`packages/execution-core/src/execution_core/`:**
- Purpose: Authoritative deterministic core; no framework imports
- Contains: `domain/` (session.py, specification.py, task.py, evidence.py, checkpoint.py, decision.py, parking_item.py, foreground.py, commands.py, enums.py), `policies/` (*_policy.py), `events/domain_events.py`, `state_machine/lifecycle.py`
- Key files: `state_machine/lifecycle.py`, `domain/enums.py`

**`packages/application/src/coh_application/`:**
- Purpose: Use-case services taking a `UnitOfWork`
- Key files: `spec_gate_service.py`, `foreground_service.py`, `__init__.py` (re-exports)

**`packages/persistence/`:**
- Purpose: State store
- Contains: `src/persistence/ports/state_store.py` (Protocols), `src/persistence/infrastructure/` (database.py, models.py, mappers.py, repositories.py, unit_of_work.py), `alembic/versions/` (e.g. `001_initial_schema.py`), `alembic.ini`

**`packages/archive/src/coh_archive/`:**
- Purpose: Markdown archive writer/reader
- Key files: `service.py`, `markdown.py`, `paths.py`, `models.py`

**`packages/prose/src/coh_prose/`:**
- Purpose: Prose rules and output renderers
- Key files: `policy.py`, `renderer.py`

**`packages/mcp_adapter/src/coh_mcp/`:**
- Purpose: MCP adapter
- Key files: `server.py` (tool list + dispatch), `handlers.py`, `archive_wiring.py`, `errors.py`, `types.py`

**`apps/api/src/coh_api/`:**
- Purpose: HTTP adapter
- Key files: `main.py`, `composition.py`, `api/routes/{spec_gate,foreground}.py`, `api/schemas/{spec_gate,foreground,common}.py`; `application/__init__.py` is an empty placeholder

**`tests/evals/`:**
- Purpose: 19 behavioral scenarios referencing contract IDs
- Contains: `scenarios/*.yaml`, `schema/scenario.schema.yaml`, `tests/` (scenario_executor.py, invariant_checkers.py, mock_adapter.py, test_scenarios.py), `fixtures/`

**`docs/`:**
- Key files: `behavioral-contract.md`, `coding-rules.md`, `decision-log.md`, `eval-rubric.md`, `glossary.md`, `adr/` (0000-template.md, 0001-*.md), `feature-specs/*.md`

## Key File Locations

**Entry Points:**
- `packages/mcp_adapter/src/coh_mcp/server.py`: `main()`, console script `coh-mcp`
- `apps/api/src/coh_api/main.py`: FastAPI `app`

**Configuration:**
- `pyproject.toml`: workspace, ruff, pyright, dev group
- `packages/*/pyproject.toml`, `apps/api/pyproject.toml`: per-package deps and `[tool.uv.sources]`
- `pytest.ini`, `.coveragerc`: test discovery and coverage (core gate 90%)
- `packages/persistence/alembic.ini`: migrations
- `.github/workflows/ci.yml`, `.github/workflows/checks-guard.yml`

**Core Logic:**
- `packages/execution-core/src/execution_core/state_machine/lifecycle.py`
- `packages/execution-core/src/execution_core/policies/`
- `packages/application/src/coh_application/`

**Testing:**
- `tests/packages/<package-dir>/` mirrors package layout (e.g. `tests/packages/execution-core/{domain,policies,state_machine,events}/`)
- `tests/apps/api/`, `tests/evals/`, `tests/guard/`

## Naming Conventions

**Files:**
- snake_case modules: `foreground_service.py`, `archive_wiring.py`
- Policies: `<topic>_policy.py`; services: `<topic>_service.py`
- Tests: `test_<subject>.py`; shared fixtures in `conftest.py`
- Eval scenarios: `<area>-NNN-<slug>.yaml` (e.g. `spec-001-vague-request.yaml`)
- Migrations: `NNN_<description>.py`; ADRs: `NNNN-<slug>.md`

**Directories:**
- Package dirs are kebab-case or snake_case (`execution-core`, `mcp_adapter`); import names are snake_case, prefixed `coh_` except `execution_core` and `persistence`
- Every package uses `src/` layout: `packages/<dir>/src/<import_name>/`

## Where to Add New Code

**New use case:**
- Service: `packages/application/src/coh_application/<topic>_service.py`, export in `__init__.py`
- Tests: `tests/packages/application/test_<topic>_service.py`

**New domain rule or invariant:**
- Entity/enum: `packages/execution-core/src/execution_core/domain/`
- Rule: `packages/execution-core/src/execution_core/policies/<topic>_policy.py`
- Transition: `state_machine/lifecycle.py`
- Tests: `tests/packages/execution-core/<subdir>/`; update `docs/behavioral-contract.md` and matching `tests/evals/scenarios/` when contract IDs change

**New MCP tool:**
- Register in `packages/mcp_adapter/src/coh_mcp/server.py` (`list_tools` + `call_tool`), implement thin method in `handlers.py` that calls an application service
- Tests: `tests/packages/mcp_adapter/`

**New HTTP endpoint:**
- Route: `apps/api/src/coh_api/api/routes/<topic>.py`, schema: `api/schemas/<topic>.py`, register in `main.py` under `/api/v1`; obtain services via `get_container()`
- Tests: `tests/apps/api/`

**New persisted aggregate:**
- Port in `persistence/ports/state_store.py`, ORM model in `infrastructure/models.py`, mapper in `mappers.py`, repository in `repositories.py`, attribute on UoW in `unit_of_work.py`, Alembic revision in `packages/persistence/alembic/versions/`

**Prose / output format:**
- `packages/prose/src/coh_prose/renderer.py` (models + `render_*`) and `policy.py`

**Utilities:**
- No shared utils package; place helpers in the owning package.

## Special Directories

**`.coh/`:**
- Purpose: Runtime state (`coh.db` SQLite WAL, `archive/` Markdown) under project root / cwd
- Generated: Yes
- Committed: No

**`packages/persistence/alembic/`:**
- Purpose: Schema migrations
- Generated: Partly (revision files)
- Committed: Yes

**`.planning/`:**
- Purpose: GSD phase specs and codebase maps
- Generated: By GSD tooling
- Committed: Yes

**Protected check set:**
- Purpose: `tests/` and CI workflow files guarded by `.github/scripts/checks_guard.py` (builders may not edit)
- Committed: Yes

---

*Structure analysis: 2026-10-21*
