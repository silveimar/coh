---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
# Technology Stack

**Analysis Date:** 2026-10-21

## Languages

**Primary:**
- Python 3.15 - all application code in `packages/*/src/` and `apps/api/src/`, all tests in `tests/`, the CI guard script `.github/scripts/checks_guard.py`

**Secondary:**
- YAML - CI workflows (`.github/workflows/ci.yml`, `.github/workflows/checks-guard.yml`), eval scenario schema (`tests/evals/schema/scenario.schema.yaml`) and archive front matter (written by `packages/archive/src/coh_archive/markdown.py`)
- Bash - inline CI steps only (gitleaks scan in `.github/workflows/ci.yml`); no committed shell scripts
- Markdown - interaction archive output format (`.coh/archive/`) and all docs under `docs/`

## Runtime

**Environment:**
- CPython 3.15 (floor set by `.python-version` = `3.15` and `requires-python = ">=3.15"` in every `pyproject.toml`)
- Native wheels for cp315 are locked for five native deps (decision D13, commit "lock cp315 wheels"); `pyyaml` has no cp315 wheel and builds from sdist. CI records whether the build has the libyaml C extension (`yaml.__with_libyaml__`).

**Package Manager:**
- uv (workspace mode), version unpinned (`astral-sh/setup-uv@v4` with `version: "latest"` in CI)
- Lockfile: present (`uv.lock`, lock format `version = 1`)
- Workspace members: `packages/*` and `apps/*` (root `pyproject.toml`, `[tool.uv.workspace]`); inter-package deps use `{ workspace = true }` sources
- Build backend for every member: `hatchling` (`[build-system]` in each `packages/*/pyproject.toml`, `apps/api/pyproject.toml`)

## Frameworks

**Core:**
- Pydantic 2.14.1 (spec `>=2.9.0`) - domain models in `packages/execution-core`, archive models, prose, API schemas (`apps/api/src/coh_api/api/schemas/`)
- FastAPI 0.141.1 (spec `>=0.115.0`) on Starlette 1.6.0 - HTTP adapter (`apps/api/src/coh_api/main.py`)
- Uvicorn 0.52.4 (`uvicorn[standard]>=0.32.0`) - ASGI server for `coh_api.main:app`
- MCP Python SDK 2.1.1 (spec `mcp>=1.0.0`) - stdio MCP server (`packages/mcp_adapter/src/coh_mcp/server.py`)
- SQLAlchemy 2.0.52 (spec `>=2.0.0`) - ORM, repositories, unit of work (`packages/persistence/src/persistence/infrastructure/`)
- Alembic 1.19.1 (spec `>=1.12.0`) - migrations (`packages/persistence/alembic/`, `packages/persistence/alembic.ini`)

**Testing:**
- pytest 9.1.1 - runner; config in `pytest.ini` (`testpaths = tests`, `--import-mode=importlib`, `--strict-markers`)
- pytest-asyncio 1.4.0 - `asyncio_mode = auto`
- pytest-cov 7.1.0 - coverage; config in `.coveragerc`; CI gates `packages/execution-core` at 90% (`--cov-fail-under=90`)
- hypothesis 6.169.0 - property tests (`tests/packages/execution-core/test_properties.py`)
- httpx 0.28.1 - FastAPI TestClient transport (`tests/apps/api/`)

**Build/Dev:**
- ruff 0.17.0 - lint + format (`[tool.ruff]` in root `pyproject.toml`: line length 88, target `py315`, rules E, W, F, I, B, C4, UP; isort first-party list)
- pyright 1.1.414 - strict type checking (`[tool.pyright]`, `typeCheckingMode = "strict"`); not run in CI
- hatchling - wheel builds per package

## Key Dependencies

**Critical:**
- `pydantic` - the only third-party dependency allowed in `packages/execution-core` (no FastAPI/SQLAlchemy/MCP imports there, per `AGENTS.md`)
- `sqlalchemy` + `alembic` - project-local state store; only `packages/persistence` imports them
- `mcp` - Claude Code adapter (decision D5); note the lock resolves a 2.x major against a `>=1.0.0` spec
- `pyyaml` 6.0.3 - archive front matter and eval scenario loading; built from sdist on cp315 (D13)

**Infrastructure:**
- `fastapi`, `uvicorn[standard]` - only in `apps/api`
- Dev group (root `pyproject.toml` `[dependency-groups] dev`): httpx, hypothesis, pyright, pytest, pytest-asyncio, pytest-cov, ruff

**Package dependency graph (workspace):**
- `execution-core` <- `persistence` <- `application` <- `mcp-adapter`, `coh-api`
- `coh-archive` and `prose` are leaves used by `application` / `mcp-adapter`

Adding any dependency requires an accepted decision (`AGENTS.md`, `docs/decision-log.md`).

## Configuration

**Environment:**
- No environment variables read by application code (no `os.environ`/`getenv` under `packages/` or `apps/`)
- Runtime state paths are fixed relative to the project root / CWD:
  - SQLite DB: `.coh/coh.db` (`packages/persistence/src/persistence/infrastructure/database.py`, `apps/api/src/coh_api/composition.py`, `packages/mcp_adapter/src/coh_mcp/handlers.py`)
  - Archive: `.coh/archive/` (`packages/archive/src/coh_archive/paths.py`, `packages/archive/src/coh_archive/models.py`)
- `ServiceContainer(database_url=...)` in `apps/api/src/coh_api/composition.py` accepts an override (used by tests)
- No `.env` files present

**Build:**
- `pyproject.toml` (root: workspace, ruff, pyright, dev group)
- `packages/*/pyproject.toml`, `apps/api/pyproject.toml` (per-member deps, hatch wheel targets)
- `pytest.ini`, `.coveragerc`
- `packages/persistence/alembic.ini`, `packages/persistence/alembic/env.py` (default URL `sqlite:///.coh/coh.db`)

## Platform Requirements

**Development:**
- Python 3.15 + uv; `uv sync --all-packages`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest`
- Linux is the CI platform (`ubuntu-latest`)

**Production:**
- Local-first only for v0.1: no cloud infrastructure, no remote telemetry, no UI (`AGENTS.md`)
- Entry points: `coh-mcp` console script (`coh_mcp.server:main`, declared in `packages/mcp_adapter/pyproject.toml`) launched by Claude Code over stdio; `coh_api.main:app` served by uvicorn on localhost

---

*Stack analysis: 2026-10-21*
