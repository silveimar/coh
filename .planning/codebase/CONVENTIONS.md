---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
# Coding Conventions

**Analysis Date:** 2026-10-21

Canonical source: `docs/coding-rules.md` (engineering standards) and `CONTRIBUTING.md` (workflow, Definition of Done). This document summarizes what those rules require and what the code actually does. When they disagree, follow `docs/coding-rules.md` for new code.

## Naming Patterns

**Files:**
- Python modules are `snake_case.py`, named for the domain concept or role: `packages/execution-core/src/execution_core/policies/completion_policy.py`, `packages/application/src/coh_application/spec_gate_service.py`, `packages/persistence/src/persistence/infrastructure/unit_of_work.py`.
- Policy modules end in `_policy.py`; application services end in `_service.py`; API routes and schemas share a feature name (`apps/api/src/coh_api/api/routes/spec_gate.py` + `apps/api/src/coh_api/api/schemas/spec_gate.py`).
- Package directories on disk may be kebab-case (`packages/execution-core/`), but importable package names are `snake_case` and usually `coh_`-prefixed: `execution_core`, `persistence`, `coh_archive`, `coh_prose`, `coh_mcp`, `coh_application`, `coh_api`.
- Never use vague names (`utils`, `misc`, `manager`, `handler`, `data`) for domain behavior (`docs/coding-rules.md`). `coh_mcp/handlers.py` is an adapter-boundary exception, not a pattern to copy into domain code.

**Functions:**
- `snake_case`, verb-first: `compute_completion_state`, `require_evidence_for_verification`, `check_mutation_allowed`, `is_foreground_eligible`.
- `require_*` raises on violation; `check_*` returns a `(bool, reasons)` tuple; `compute_*` returns derived state; `is_*` returns `bool`.
- Private helpers use a leading underscore: `_get_readiness_blockers`, `_load_current_spec` in `packages/application/src/coh_application/spec_gate_service.py`.

**Variables:**
- `snake_case`; constants `UPPER_SNAKE_CASE` (`SCENARIOS_DIR`, `PRODUCT_GAPS` in `tests/evals/tests/test_scenarios.py`).
- Module logger is always `logger = logging.getLogger(__name__)`.

**Types:**
- Classes, enums and Pydantic models are `PascalCase` with precise domain names: `Task`, `TaskDependency`, `Specification`, `DoneWhenCriterion`, `ExecutionSession`, `Checkpoint`, `ParkingItem`.
- Enums live in `packages/execution-core/src/execution_core/domain/enums.py` (`LifecycleState`, `Readiness`, `TaskStatus`, `CompletionState`, `EvidenceResult`).
- Exceptions end in `Violation` (domain policy) or `Error` (adapter/infrastructure): `CompletionViolation` in `completion_policy.py`, `CapabilityNotImplementedError` in `packages/mcp_adapter/src/coh_mcp/errors.py`.
- Wire JSON and Pydantic field names are `snake_case` end to end (D10). Never alias to camelCase.
- Terminology must match `docs/glossary.md`; a rename needs a `docs/decision-log.md` entry.

## Code Style

**Formatting:**
- Ruff format, configured in root `pyproject.toml`: `line-length = 88`, `target-version = "py315"`.
- Double quotes, trailing commas, formatter-controlled wrapping. Run `uv run ruff format --check .`.

**Linting:**
- Ruff lint, rule sets `E`, `W`, `F`, `I`, `B`, `C4`, `UP` (`pyproject.toml` `[tool.ruff.lint]`), no ignores.
- Pyright `typeCheckingMode = "strict"` with `reportUnknownMemberType/VariableType/ArgumentType` and `reportMissingTypeStubs` disabled (`pyproject.toml` `[tool.pyright]`). Pyright is not run in CI; run `uv run pyright` locally.
- Inline suppressions need a one-line justification and a linked issue or test (`CONTRIBUTING.md`). Existing unjustified suppressions (`# type: ignore` in `packages/mcp_adapter/src/coh_mcp/handlers.py` and `archive_wiring.py`, `packages/persistence/src/persistence/infrastructure/database.py`; `# noqa: E402` in `execution_core/domain/checkpoint.py` and `session.py`) are debt, not precedent.
- `pragma: no cover` and skip markers in diffs are flagged by the checks guard (`.github/scripts/checks_guard.py`). Do not add them.

**Typing:**
- Use modern syntax: `list[str]`, `dict[UUID, list[Evidence]]`, `X | None`, `Literal["ready", "blocked"]`, `datetime.UTC`.
- Annotate every public function signature including the return type (`-> None` too).
- Domain entities are Pydantic v2 `BaseModel`s with `Field(default_factory=...)` for ids, lists and timestamps (`packages/execution-core/src/execution_core/domain/task.py`).

## Import Organization

**Order (enforced by Ruff `I`):**
1. Standard library (`from uuid import UUID`, `import logging`)
2. Third-party (`pydantic`, `fastapi`, `sqlalchemy`, `pytest`, `hypothesis`)
3. First-party, declared in `[tool.ruff.lint.isort] known-first-party`: `execution_core`, `coh_archive`, `persistence`, `coh_prose`, `coh_mcp`, `coh_application`, `coh_api`

One blank line between groups.

**Relative vs absolute:**
- Inside `execution_core`, use relative imports: `from ..domain.enums import CompletionState`, `from .enums import TaskStatus`.
- Across packages, use absolute first-party imports: `from execution_core.domain.specification import Specification`, `from persistence.ports.state_store import UnitOfWork`.

**Layer rules (hard):**
- `packages/execution-core` imports only stdlib and Pydantic. No FastAPI, SQLAlchemy, Huey, MCP or provider SDKs.
- Application services depend on the `UnitOfWork` port (`packages/persistence/src/persistence/ports/state_store.py`), not concrete repositories. Note: `SpecGateService._load_current_spec` imports SQLAlchemy and reaches into `uow._session`; do not copy this.
- Routes (`apps/api/src/coh_api/api/routes/`) and MCP tools (`packages/mcp_adapter/src/coh_mcp/`) call application services, never repositories.
- Do not call private (`_`-prefixed) methods across layers; `apps/api/src/coh_api/api/routes/spec_gate.py` calls `service._get_readiness_blockers`, which is a violation to avoid in new code.

**Path Aliases:**
- None. Packages resolve through the uv workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`).

## Error Handling

**Patterns:**
- Domain policies raise typed exceptions carrying structured detail:
  ```python
  class CompletionViolation(Exception):
      def __init__(self, message: str, missing_criteria: list[str]):
          super().__init__(message)
          self.missing_criteria = missing_criteria
  ```
  (`packages/execution-core/src/execution_core/policies/completion_policy.py`)
- Paired query/guard methods: `check_mutation_allowed()` returns `(allowed, state, blockers)`; `require_ready_for_mutation()` raises when not allowed (`spec_gate_service.py`). Provide both when a gate is needed by multiple callers.
- Application services currently raise `ValueError` for not-found and `PermissionError` for gate rejection; routes map them to `HTTPException` with a status code. Prefer a typed domain exception for new gates.
- Missing adapter capability raises `CapabilityNotImplementedError` (I-14); never fabricate results.
- Archive failures degrade and continue (D6): catch `PathResolutionError`, `OSError`, then `Exception`, log, and return `ArchiveWriteResult(outcome=WriteOutcome.ARCHIVE_WRITE_FAILED, error=...)`. Never raise from an archive write (`packages/archive/src/coh_archive/service.py`).
- Error messages are neutral and diagnosis-free ("blocked", "decision needed", "recovery step") and cite the invariant behavior, e.g. `"Material mutation rejected: readiness is BLOCKED. ... Read-only inspection remains permitted."`.
- API errors should carry a stable machine-readable code, a user-safe message and a correlation ID (`docs/coding-rules.md`).

## Logging

**Framework:** stdlib `logging`.

**Patterns:**
- `logger = logging.getLogger(__name__)` at module top (`coh_archive/service.py`, `coh_mcp/handlers.py`, `coh_mcp/archive_wiring.py`).
- `%`-style lazy arguments plus `extra={...}` for structured context:
  ```python
  logger.warning(
      "Archive write failed (non-blocking): %s",
      str(e),
      extra={"session_id": str(event.session_id)},
  )
  ```
- `logger.warning` for degraded-but-continuing paths; `logger.exception` for unexpected exceptions.
- No logging in `execution_core`; domain code stays pure and returns/raises instead.
- Never log secrets, tokens or personal data. Logs are local-only (D7).

## Comments

**When to Comment:**
- Tag code with the contract ID it enforces: `# I-03: Only tool_verified or user_accepted can satisfy`. Invariants `I-01`..`I-14`, transitions `T1`.., prose rules `P-01`..`P-06` come from `docs/behavioral-contract.md`.
- Explain non-obvious constraints, not mechanics.

**Docstrings:**
- Every module starts with a one-line docstring naming its purpose and invariant: `"""Completion policy enforcing I-03 (evidence gate)."""`.
- Every class and public method has a docstring. Multi-line docstrings open on the line after `"""`, give a summary, then `Raises ...` / `Returns: ...` notes in prose. Google-style `Returns:` sections appear in `coh_archive`.

## Function Design

**Size:** Keep policy and service methods focused on one rule; extract helpers (`_get_readiness_blockers`) when a method collects reasons.

**Parameters:** Keyword-friendly signatures with typed optionals defaulting to `None` and normalized inside (`constraints or []`). Do not use mutable defaults (one test helper in `tests/packages/application/test_foreground_service.py` uses `list = None`; avoid).

**Return Values:** Return domain models or explicit tuples `(bool, list[str])`. Pydantic response models at the API boundary. Avoid untyped `dict` returns for domain data (`get_spec_status` returns a dict; prefer a model for new code).

**Sync vs async:** Domain, policies and application services are synchronous. Async only at I/O boundaries (MCP handlers, archive writer, HTTP).

**Policies:** Stateless classes with `@staticmethod`s (`CompletionPolicy`). Services take their port in `__init__` (`SpecGateService(uow)`).

## Module Design

**Exports:** `src/` layout per package. Import from the concrete module (`execution_core.domain.task`), not from package roots; most `__init__.py` files are empty or docstring-only. `coh_archive/__init__.py` is the exception and re-exports its public API (`from coh_archive import ArchiveConfig`).

**Barrel Files:** Only `coh_archive`. Do not add barrels elsewhere without a reason.

**Composition:** Wire dependencies in `apps/api/src/coh_api/composition.py` (`get_container()`, `create_uow()`, `spec_gate_service(uow)`).

## Commits and Branches

- Branch `type/short-slug`; commits `type: summary` (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`), imperative mood, under about 72 characters (`CONTRIBUTING.md`).
- One concern per PR. New dependencies, contract changes, schema migrations and execution-semantics changes need an accepted ADR or decision-log entry first.

---

*Convention analysis: 2026-10-21*
