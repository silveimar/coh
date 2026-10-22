---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
# Codebase Concerns

**Analysis Date:** 2026-10-21

## Tech Debt

**Pyright is a documented gate but not enforced, and it reports 648 errors:**
- Issue: `docs/coding-rules.md` and `CONTRIBUTING.md` (Definition of Done) require `uv run pyright` to pass. `.github/workflows/ci.yml` does not run it; `CONTRIBUTING.md` "Known gaps" says so.
- Files: `.github/workflows/ci.yml`, `pyproject.toml` (`[tool.pyright]`), `CONTRIBUTING.md`
- Impact: Type regressions reach `main` unseen. No per-package error baseline exists, so "pyright passes" cannot be confirmed.
- Baseline (pyright 1.1.414, `uv sync --all-packages --locked`, commit `f3743a1`, 119 files, `uv run pyright --outputjson` grouped by top two path segments), errors only:

  | Path | Errors |
  |---|---|
  | `packages/mcp_adapter` | 146 |
  | `apps/api` | 26 |
  | `packages/persistence` | 23 |
  | `packages/execution-core` | 18 |
  | `packages/application` | 13 |
  | `packages/archive` | 5 |
  | `packages/prose` | 0 |
  | `tests/packages` | 268 |
  | `tests/evals` | 99 |
  | `tests/apps` | 50 |
  | **Total** | **648** |

  Errors under `tests/` (417) are in the protected check set: only the lead seat may change those files.
- Fix approach: Run `uv run pyright --outputjson` in a synced worktree and group diagnostics by `packages/<name>` and `apps/api`. Add a CI step, in its own PR. Start with `packages/execution-core` (expected to be the cleanest), then add the other packages one at a time, or use a recorded baseline that may only go down.

**Pyright "strict" is weakened by four disabled rules:**
- Issue: `typeCheckingMode = "strict"`, but `reportMissingTypeStubs`, `reportUnknownMemberType`, `reportUnknownVariableType` and `reportUnknownArgumentType` are all `false`.
- Files: `pyproject.toml` lines 50-56
- Impact: Unknown types from SQLAlchemy, MCP and FastAPI pass silently. `get_session_factory` in `packages/persistence/src/persistence/infrastructure/database.py` returns a bare `sessionmaker` (no type parameter).
- Fix approach: Re-enable the rules per package with `executionEnvironments` or per-directory config, starting with `packages/execution-core`.

**Type suppressions without justification:**
- Issue: There are 7 bare `# type: ignore` comments in source, plus 1 in tests. None has the one-line justification and linked issue that the DoD requires ("No new lint or type suppression without a one-line justification").
- Files: `packages/mcp_adapter/src/coh_mcp/handlers.py:596-599` (archive stats dict), `packages/mcp_adapter/src/coh_mcp/archive_wiring.py:146-147` (`tool_data.get(...)`), `packages/persistence/src/persistence/infrastructure/database.py:23` (untyped event listener), `tests/packages/execution-core/state_machine/test_lifecycle.py:501` (deliberate bad call)
- Two `# noqa: E402` late imports mark a circular import between `checkpoint.py`, `session.py` and `specification.py`: `packages/execution-core/src/execution_core/domain/checkpoint.py:41`, `packages/execution-core/src/execution_core/domain/session.py:41`.
- Fix approach: Type the stats with a `TypedDict` and annotate the SQLAlchemy listener parameters. Remove the cycle with `TYPE_CHECKING` imports or a shared module.

**The MCP adapter bypasses the application layer (layer-rule violation):**
- Issue: AGENTS.md says "Routes and MCP tools call application services, never repositories." `COHHandlers` builds its own engine and opens `SqlAlchemyUnitOfWork` directly about 40 times. It calls `uow.sessions`, `uow.specifications`, `uow.tasks`, `uow.evidence` and `uow.checkpoints`, and reaches into the private `uow._session.scalars(...)` (lines 305, 342, 385, 449). Only parts of the flow go through `coh_application`.
- Files: `packages/mcp_adapter/src/coh_mcp/handlers.py` (1464 lines; the largest file in the repository)
- Impact: Lifecycle orchestration is duplicated between the MCP adapter and `packages/application/src/coh_application/*_service.py`, so the two surfaces (MCP and HTTP) can drift. Business logic lives in an adapter.
- Fix approach: Move each handler's orchestration into application services (`SpecGateService`, `ForegroundService` and new ones for session, checkpoint, recover and verify). Handlers should only parse input and render output. Add a public repository method for the current-spec lookup in place of `uow._session` access. This is a cross-module refactor, so it needs an ADR (`CONTRIBUTING.md`).

**One logical operation spans several transactions:**
- Issue: One operation is split across separate `with SqlAlchemyUnitOfWork(...)` blocks. For example, `create_session` commits the session in one UoW and the checkpoint in a second one (`handlers.py:93-99`). `confirm_spec`, `execute_task` and `verify_deliverable` open 2-4 UoWs each.
- Files: `packages/mcp_adapter/src/coh_mcp/handlers.py`
- Impact: A crash between blocks leaves partial state, for example a session with no initial checkpoint. That weakens recovery (feature spec `docs/feature-specs/interruption-recovery-resume-records.md`).
- Fix approach: One UoW per command, inside the application service.

**Schema management is split between `create_all` and Alembic:**
- Issue: `init_db` is documented "for testing only, use Alembic in production", but the MCP server runtime calls it (`handlers.py:49`). The API never initializes the schema or runs migrations (`apps/api/src/coh_api/composition.py`). There is one migration, `packages/persistence/alembic/versions/001_initial_schema.py`.
- Files: `packages/persistence/src/persistence/infrastructure/database.py:37-39`, `packages/mcp_adapter/src/coh_mcp/handlers.py:49`, `apps/api/src/coh_api/composition.py`
- Impact: The model and the migration can diverge undetected. An API process started against a fresh `.coh/coh.db` has no tables unless the MCP server ran first. A future schema change is not applied to existing databases created by `create_all`.
- Fix approach: Run `alembic upgrade head` (programmatically) at startup for both adapters. Add a test that compares `Base.metadata` with the migrated schema.

**Application layer depends on the persistence package for its port:**
- Issue: The `UnitOfWork` protocol lives in `packages/persistence/src/persistence/ports/state_store.py`. `coh_application` imports it from there (`foreground_service.py:9`, `spec_gate_service.py:14`), so the application package depends on the package that contains SQLAlchemy.
- Impact: Application services cannot be installed or tested without SQLAlchemy, which blurs the port and adapter boundary.
- Fix approach: Move the ports to `packages/application` or `packages/execution-core`. This needs an ADR (cross-module).

## Known Bugs

**`inspect_repository` is a stub:**
- Symptoms: It always raises `CapabilityNotImplementedError` (I-14), and `server.py:376` maps that to a NOT_IMPLEMENTED response.
- Files: `packages/mcp_adapter/src/coh_mcp/handlers.py:112-126`, `packages/mcp_adapter/src/coh_mcp/errors.py`
- Trigger: Any call to the inspect tool.
- Workaround: The contract allows it (I-14); the user supplies inspection context. Track it as a missing feature, not a regression.

**Intent inference is keyword-based:**
- Files: `packages/mcp_adapter/src/coh_mcp/handlers.py:1449` (`_infer_intent`)
- Symptoms: Intent is inferred heuristically in the adapter, not by domain policy. A misclassification feeds `SessionIntent(...)` directly.

No other confirmed defects were found by static inspection. No TODO or FIXME markers exist in `packages/` or `apps/`.

## Security Considerations

**No dependency vulnerability audit in CI:**
- Risk: Vulnerable transitive dependencies (fastapi, uvicorn[standard], sqlalchemy, mcp, pydantic, pyyaml built from sdist per D13) go unnoticed.
- Files: `.github/workflows/ci.yml` (jobs: `lint-and-test`, `gitleaks` only), `uv.lock`
- Current mitigation: `uv.lock` is committed. A gitleaks secret scan runs with a pinned version and SHA-256 check, and it fails closed (`ci.yml` lines 75-163).
- Recommendations: Add pip-audit or osv-scanner against `uv.lock`, then Trivy and deptry, each in its own PR (listed as planned in `CONTRIBUTING.md`). Pre-commit hooks are also not wired up.

**Unpinned CI tooling:**
- Risk: `astral-sh/setup-uv@v4` uses `version: "latest"`. The actions are pinned by tag, not by SHA (`actions/checkout@v4`, `actions/setup-python@v5`, `codecov/codecov-action@v5`).
- Files: `.github/workflows/ci.yml` lines 15-24, 69
- Recommendations: Pin the uv version and pin actions by commit SHA.

**Broad exception handling:**
- Files: `packages/archive/src/coh_archive/service.py:107,175`, `packages/mcp_adapter/src/coh_mcp/handlers.py:501`
- Risk: Low. The archive degrade-and-continue rule calls for this. Make sure failures are counted (`writes_failed`, `last_failure`) and never swallowed silently.

**`check_same_thread=False` on SQLite:**
- Files: `packages/persistence/src/persistence/infrastructure/database.py:15`
- Risk: Safe only while each session stays on one thread. The global `ServiceContainer` (`apps/api/src/coh_api/composition.py:38`) shares one engine across FastAPI threadpool workers.

## Performance Bottlenecks

Not a current concern: v0.1 is local-first and single-user.
- `COHHandlers` opens several sessions per tool call and re-reads the session and spec in each one (`handlers.py`). This costs little on SQLite WAL but grows with the call count.

## Fragile Areas

**`packages/mcp_adapter/src/coh_mcp/handlers.py`:**
- Why fragile: 1464 lines in one class. Optimistic concurrency (`expected_version`) is threaded by hand across multiple UoWs. It accesses the private `uow._session`.
- Safe modification: Change one tool method at a time and run `tests/packages/mcp_adapter/` (5 test modules) plus `tests/evals`.
- Test coverage: No coverage floor (see below).

**`packages/execution-core/src/execution_core/state_machine/lifecycle.py` (518 lines) and `packages/persistence/src/persistence/infrastructure/mappers.py` (597 lines):**
- Why fragile: Mappers translate every domain field by hand. A new domain field that is not mapped is silently dropped.
- Safe modification: Extend `tests/packages/persistence/test_repositories.py` with a round-trip test for each new field.

**Eval harness:**
- Files: `tests/evals/tests/scenario_executor.py` (raises `NotImplementedError` for unhandled scenarios, lines 58, 893, 906, 928; caught at line 761)
- Why fragile: Scenario IDs must stay in sync with `docs/behavioral-contract.md` invariants I-01 to I-14 and prose rules P-01 to P-06. A scenario without a handler may be caught instead of failing. Check how line 761 reports it.

## Scaling Limits

**SQLite single-writer:**
- Current capacity: One local user; one `.coh/coh.db` per project.
- Limit: Concurrent MCP and API writers contend for the WAL write lock.
- Scaling path: Out of scope for v0.1 (D1, D7: no added datastore without an ADR).

## Dependencies at Risk

**Python 3.15 floor:**
- Risk: Several native dependencies needed cp315 wheel locking (D13, commit "lock cp315 wheels for five native deps"). pyyaml builds from its sdist; CI logs whether the libyaml C extension was built (`ci.yml` lines 30-33).
- Impact: A new release without cp315 wheels can break `uv sync` in CI.
- Migration plan: Keep `uv.lock` pinned and review lock updates for wheel availability.

**Loose lower-bound pins in package manifests:**
- Files: `packages/mcp_adapter/pyproject.toml` (`mcp>=1.0.0`), `apps/api/pyproject.toml` (`fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`)
- Risk: Only `uv.lock` constrains the versions. The MCP SDK changes quickly.

## Missing Critical Features

**CI gates listed in `CONTRIBUTING.md` but not implemented:**
- Problem: pyright, dependency audit, Trivy, deptry, pre-commit, the `fleet/checker` required status and a PR template under `.github/` are all missing.
- Blocks: The Definition of Done items "pyright passes" and "`fleet/checker` success on exact head SHA" cannot be checked by machine.

**Documented components that do not exist:**
- `docs/coding-rules.md` (Repository Structure, lines 19-44) describes `apps/worker/` (Huey), `apps/web/`, `packages/agent-runtime/`, `packages/mcp-server/`, `packages/python-client/`, `frontend/`, a top-level `migrations/`, `package.json` and `pnpm-lock.yaml`. None exists. The real layout uses `packages/mcp_adapter/`, `packages/persistence/alembic/`, `packages/prose/`, `packages/application/` and `packages/persistence/`.
- Huey or a `JobRunner` is referenced in `docs/coding-rules.md:83`, `packages/persistence/README.md:131` and `packages/execution-core/README.md:121`, but no job runner exists in the code and Huey is not a dependency.
- Impact: Agents that follow the coding rules may create files in paths that do not exist.
- Fix approach: Update the structure section of `docs/coding-rules.md` to the actual layout (the `AGENTS.md` "Layout" block is accurate), and mark planned components as planned.

**Documentation gaps:**
- `packages/prose/` has no `README.md`; every other package has one.

## Test Coverage Gaps

**Coverage floor enforced only for the Execution Core:**
- What's not tested: No floor exists for `packages/persistence`, `packages/archive`, `packages/prose`, `packages/mcp_adapter`, `packages/application` or `apps/api`. Their CI steps use `--cov-append` without `--cov-fail-under` (`ci.yml` lines 44-60). Only `tests/packages/execution-core` has `--cov-fail-under=90` (line 42).
- Also: Codecov uploads the combined `coverage.xml` under the single flag `execution-core` (`ci.yml` lines 68-73), so per-package trends are mislabeled.
- Files: `.github/workflows/ci.yml`, `.coveragerc`
- Risk: Coverage in the adapter and persistence code can fall unnoticed. That is where the layer violations and multi-transaction logic above live.
- Priority: High for `packages/mcp_adapter` and `packages/persistence`; Medium for the others.
- Fix approach: Measure current coverage per package and set each floor at that value (per `CONTRIBUTING.md`: "set each at current coverage and let it only go up"). This changes the protected check set (`.github/workflows/`), so it is a lead-seat checks commit.

**Schema and migration parity untested:**
- What's not tested: The tests do not check that `001_initial_schema.py` matches `Base.metadata` in `packages/persistence/src/persistence/infrastructure/models.py`. The tests use `init_db` and `create_all`.
- Priority: Medium.

**API startup against a fresh database:**
- What's not tested: The `apps/api` startup path with no existing `.coh/coh.db`. `tests/apps/api/test_api_integration.py` (lines 15-46) calls `init_db` itself and monkeypatches `composition._container`, so the real `init_services` path is never exercised.
- Priority: Medium.

---

*Concerns audit: 2026-10-21*
