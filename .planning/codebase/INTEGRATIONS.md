---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
# External Integrations

**Analysis Date:** 2026-10-21

## APIs & External Services

**Agent host (MCP):**
- Claude Code - the first and only agent adapter (decision D5); consumes COH tools over stdio
  - SDK/Client: `mcp` (`mcp.server.Server`, `mcp.server.stdio.stdio_server`) in `packages/mcp_adapter/src/coh_mcp/server.py`
  - Tools are snake_case (D10), e.g. `create_session`, `inspect_repository`; unavailable capabilities return NOT_IMPLEMENTED (I-14, `packages/mcp_adapter/src/coh_mcp/errors.py`)
  - Auth: none (local stdio process)

**HTTP adapter:**
- Local FastAPI app (`apps/api/src/coh_api/main.py`), routes under `/api/v1` (`apps/api/src/coh_api/api/routes/spec_gate.py`, `apps/api/src/coh_api/api/routes/foreground.py`), plus `/health`, `/docs`, `/redoc`, `/openapi.json`
  - Auth: none

**LLM / AI providers:**
- Not detected. No provider SDK is a dependency; AI output arrives as proposals through the MCP host and is validated by domain policy (`packages/execution-core/src/execution_core/policies/`).

## Data Storage

**Databases:**
- SQLite (project-local file `.coh/coh.db`), WAL mode, `synchronous=NORMAL`, `foreign_keys=ON`
  - Connection: hard-coded default URL `sqlite:///.coh/coh.db` (`packages/persistence/src/persistence/infrastructure/database.py`); overridable via `ServiceContainer(database_url=...)` in `apps/api/src/coh_api/composition.py`; no env var
  - Client: SQLAlchemy 2.x ORM (`packages/persistence/src/persistence/infrastructure/models.py`, `repositories.py`, `unit_of_work.py`, `mappers.py`), port in `packages/persistence/src/persistence/ports/state_store.py`
  - Migrations: Alembic, `packages/persistence/alembic/versions/001_initial_schema.py`
  - Note: the `connect` pragma listener is registered on the global `Engine` class, so it fires for every engine in the process

**File Storage:**
- Local filesystem only: append-only Markdown interaction archive at `.coh/archive/` (`packages/archive/src/coh_archive/service.py`, `markdown.py`, `paths.py`). Failures degrade and never block work.

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None. Single local user; no auth on the MCP server or HTTP API.

## Monitoring & Observability

**Error Tracking:**
- None (no remote telemetry by policy)

**Logs:**
- No logging framework configured; the API returns diagnosis-free error envelopes (`error_code`, `message`) from handlers in `apps/api/src/coh_api/main.py`

## CI/CD & Deployment

**Hosting:**
- Not applicable (local-first; runs on the developer machine)

**CI Pipeline:**
- GitHub Actions
  - `.github/workflows/ci.yml`: uv sync, ruff lint/format, per-package pytest with coverage (execution-core gated at 90%), eval harness (`tests/evals`), guard tests (`tests/guard`)
  - Codecov upload via `codecov/codecov-action@v5` on pull requests (`coverage.xml`)
  - Gitleaks 8.30.1 secret scan (release binary pinned by SHA-256, PR range plus full history)
  - `.github/workflows/checks-guard.yml` (`pull_request_target`): runs `.github/scripts/checks_guard.py` from the base branch to protect the check set (D15); calls the GitHub REST API with `urllib` using `GITHUB_TOKEN` (read-only permissions)

## Environment Configuration

**Required env vars:**
- None for the application
- CI only: `GITHUB_TOKEN`, `PR_NUMBER` (checks-guard), `EVENT_NAME`, `BASE_SHA`, `HEAD_SHA` (gitleaks step)

**Secrets location:**
- GitHub Actions built-in `github.token` only; no repository secrets referenced in workflows. No `.env` files in the repository.

## Webhooks & Callbacks

**Incoming:**
- None (GitHub `pull_request` / `pull_request_target` events trigger CI only)

**Outgoing:**
- None from the application. CI makes outbound calls to the GitHub REST API (checks-guard), GitHub releases (gitleaks download) and Codecov.

---

*Integration audit: 2026-10-21*
