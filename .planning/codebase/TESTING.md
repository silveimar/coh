---
last_mapped_commit: f3743a11b018cc723740bbc93bdc1a29836a3469
last_mapped_at: 2026-10-21
---
# Testing Patterns

**Analysis Date:** 2026-10-21

## Test Framework

**Runner:**
- pytest >= 9.1.1 (root `pyproject.toml` `[dependency-groups] dev`)
- Config: `pytest.ini` (`testpaths = tests`, `python_files = test_*.py *_test.py`, `addopts = --strict-markers --import-mode=importlib`, `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function`)
- Coverage config: `.coveragerc` (source `packages/*/src`, `apps/*/src`; excludes `Protocol` classes, `abstractmethod`, `TYPE_CHECKING`, `__repr__`)

**Plugins / libraries:**
- `pytest-asyncio` >= 1.4.0 (auto mode)
- `pytest-cov` >= 7.1.0
- `hypothesis` >= 6.169.0 for property tests
- `httpx` >= 0.28.1 (FastAPI `TestClient`)
- `pyyaml` for eval scenarios

**Assertion Library:**
- Plain `assert` and `pytest.raises`.

**Run Commands:**

```bash
uv run pytest                                   # All tests under tests/
uv run pytest tests/packages/execution-core     # One package
uv run pytest tests/packages/execution-core --cov=packages/execution-core/src --cov-report=term --cov-fail-under=90   # Core coverage gate
uv run pytest tests/evals --tb=short            # Behavioral eval harness
uv run pytest tests/guard                       # checks-guard tests
```

No watch mode is configured.

## Test File Organization

**Location:**
- Separate tree under `tests/`, mirroring the source layout. Every directory has an `__init__.py`.

**Naming:**
- `test_*.py` only (pytest.ini also accepts `*_test.py`; do not use it). Classes `Test*`, functions `test_*`.

**Structure:**

```
tests/
├── packages/
│   ├── execution-core/{domain,events,policies,state_machine}/test_*.py
│   │   └── test_properties.py          # Hypothesis property tests
│   ├── persistence/conftest.py, test_repositories.py, test_crash_restart.py
│   ├── archive/conftest.py, test_markdown.py, test_paths.py, test_service.py, test_integration.py
│   ├── prose/test_policy.py, test_renderer.py
│   ├── mcp_adapter/test_handlers.py, test_new_tools.py, test_archive_wiring.py, ...
│   └── application/test_foreground_service.py, test_spec_gate_service.py
├── apps/api/conftest.py, test_api_integration.py
├── evals/
│   ├── scenarios/*.yaml                # 19 behavioral scenarios
│   ├── schema/scenario.schema.yaml
│   ├── fixtures/inspection_findings.py
│   └── tests/{conftest,mock_adapter,scenario_executor,invariant_checkers,test_scenarios}.py
└── guard/test_checks_guard.py + fixtures/*.json
```

New tests for `packages/<dir>/src/<pkg>/<sub>/<mod>.py` go in `tests/packages/<dir>/<sub>/test_<mod>.py`.

**Protected check set:** `tests/`, any `conftest.py`, `pytest.ini`, `.coveragerc`, `.github/workflows/`, `.github/scripts/` may be changed only in lead-authored checks commits (`CONTRIBUTING.md`, D14/D15). Builders do not edit tests; `.github/workflows/checks-guard.yml` enforces this.

## Test Structure

**Suite Organization:**

```python
"""Tests for ForegroundService enforcing I-01 (NOW + NEXT 2)."""

class TestForegroundService:
    """Test foreground service I-01 enforcement."""

    @pytest.fixture
    def uow(self):
        engine = create_engine("sqlite:///:memory:")
        init_db(engine)
        return SqlAlchemyUnitOfWork(sessionmaker(bind=engine))

    def _create_task(self, spec_id, action: str, done_when: str, ...) -> Task:
        """Helper to create a foreground-eligible task."""
```

(`tests/packages/application/test_foreground_service.py`)

**Patterns:**
- Module docstring names the unit and the invariant under test (I-xx).
- Group by class (`Test<Unit>`) in domain/application tests; module-level functions with module fixtures in adapter tests (`tests/packages/mcp_adapter/test_handlers.py`).
- Each test has a docstring stating the behavior, often with the contract ID: `"""Test I-14: inspect_repository returns NOT_IMPLEMENTED."""`.
- Setup via fixtures; `_helper` methods build valid domain objects.
- Teardown via `yield` fixtures (`engine.dispose()` in `tests/packages/persistence/conftest.py`) or `tmp_path`.

## Mocking

**Framework:** No `unittest.mock`. Use real implementations over SQLite plus hand-written fakes and `monkeypatch`.

**Patterns:**

```python
# Swap the composition-root container before app creation


@pytest.fixture
def client(service_container, monkeypatch):
    from coh_api import composition

    monkeypatch.setattr(composition, "_container", service_container)
    return TestClient(create_app())
```

(`tests/apps/api/test_api_integration.py`)

```python
class FakeApi:
    """Replays recorded responses keyed by API path and query string."""
```

(`tests/guard/test_checks_guard.py`, with `monkeypatch.setattr(guard.urllib.request, "urlopen", refuse)` to forbid network)

- Eval harness uses `MockAdapter(scenario_id, capabilities)` (`tests/evals/tests/mock_adapter.py`) to drive real `COHHandlers` deterministically.

**What to Mock:**
- External boundaries only: network/GitHub API, model providers, adapter capabilities, environment variables (`monkeypatch.setenv`).

**What NOT to Mock:**
- Domain models, policies, state machine, application services, SQLite persistence and the archive writer. Use in-memory or temp-file SQLite and `tmp_path` instead.
- Never call a live model provider in CI.

## Fixtures and Factories

**Test Data:**

```python
@pytest.fixture
def archive_config() -> ArchiveConfig:
    return ArchiveConfig(enabled=True, directory=".coh/archive")


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 8, 19, 12, 34, 56, 789000, tzinfo=UTC)
```

(`tests/packages/archive/conftest.py`)

```python
@pytest.fixture
def temp_db() -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    return f"sqlite:///{temp_file.name}"
```

(`tests/packages/persistence/conftest.py`)

**Location:**
- Per-package `conftest.py` (`tests/packages/archive/`, `tests/packages/persistence/`, `tests/apps/api/`, `tests/evals/tests/`).
- Static fixtures: `tests/guard/fixtures/*.json` (recorded synthetic API responses), `tests/evals/fixtures/inspection_findings.py`, `tests/evals/scenarios/*.yaml`.
- All data is synthetic: `project_id="test-project"`, `.invalid` email domains, `"synthetic-token"`. Never use real user data.
- Prefer `tmp_path` over `tempfile` for new fixtures (cleanup is automatic).

## Coverage

**Requirements:**
- Execution Core: >= 90% lines, enforced in CI (`--cov-fail-under=90` in `.github/workflows/ci.yml`).
- Other packages: measured with `--cov-append`, no enforced floor.
- Do not add `pragma: no cover`; the checks guard rejects it.

**View Coverage:**

```bash
uv run pytest tests/packages/execution-core --cov=packages/execution-core/src --cov-report=term
```

## Test Types

**Unit Tests:**
- Domain models, policies and state machine in `tests/packages/execution-core/`: every transition, invalid transition and invariant (`test_transition_guards.py`, `test_contract_enforcement.py`, `test_invariants.py`).

**Property Tests:**
- Hypothesis `@given` with `st.text`, `st.integers` on policies and spec readiness (`tests/packages/execution-core/test_properties.py`).
  ```python
  @given(num_blocking_unknowns=st.integers(min_value=1, max_value=5))
  def test_blocking_unknowns_prevent_readiness(self, num_blocking_unknowns):
      """Property: Any blocking unknown prevents readiness."""
  ```

**Integration Tests:**
- Application services over in-memory SQLite `SqlAlchemyUnitOfWork`; persistence crash/restart (`test_crash_restart.py`); archive end-to-end (`tests/packages/archive/test_integration.py`); MCP handlers with real persistence (`test_persistence_integration.py`); FastAPI via `TestClient` (`tests/apps/api/test_api_integration.py`).

**Behavioral Evals:**
- `tests/evals/tests/test_scenarios.py` parametrizes over every `tests/evals/scenarios/*.yaml` (ids = file stem), runs them through `ScenarioExecutor` and `invariant_checkers.py`. Scoring and thresholds: `docs/eval-rubric.md`. Scenarios reference contract IDs; keep them in sync with `docs/behavioral-contract.md`.
- Unimplemented capabilities are skipped only through the `PRODUCT_GAPS` dict with invariant and reason. Do not add other skips.

**E2E Tests:**
- Not used beyond the eval harness and MCP handler round-trips.

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
async def test_create_session_round_trip(handlers: COHHandlers):
    result = await handlers.create_session(
        project_id="test-project", user_input="Fix the retry logic", intent="execute"
    )
    assert "State: INSPECT" in result[0]["text"]
```

(`asyncio_mode = auto` makes the marker optional; existing tests keep it.)

**Error Testing:**

```python
with pytest.raises(CapabilityNotImplementedError) as exc_info:
    ...
```

Assert on structured exception attributes (e.g. `CompletionViolation.missing_criteria`) rather than message text where possible.

**Verifying through persistence:**
After calling an adapter or service, reopen a `SqlAlchemyUnitOfWork(handlers.session_factory)` and assert the stored state (`tests/packages/mcp_adapter/test_handlers.py`).

## CI

`.github/workflows/ci.yml` runs ruff check/format, then pytest per package in order (execution-core with the 90% gate, persistence, archive, prose, mcp_adapter, application, api), the eval harness and the guard tests, plus a gitleaks scan. Pyright is not in CI.

---

*Testing analysis: 2026-10-21*
