# COH Persistence Layer

SQLAlchemy 2 + Alembic project-local state store for COH (Cognitive Operating Harness).

## Overview

This package provides persistence for the `execution-core` domain models using SQLite with Write-Ahead Logging (WAL) for better concurrency. It implements the repository pattern with optimistic concurrency control via `expected_version`.

## Architecture

- **Ports** (`persistence.ports`): Protocol interfaces defining repository contracts (no SQLAlchemy dependencies)
- **Infrastructure** (`persistence.infrastructure`): Concrete SQLAlchemy implementations
  - `models.py`: Declarative SQLAlchemy models
  - `mappers.py`: Bidirectional conversion between domain and ORM models
  - `repositories.py`: Repository implementations with idempotency key and optimistic locking support
  - `unit_of_work.py`: Transaction coordination across repositories
  - `database.py`: Engine creation, WAL mode configuration

## Setup

```bash
# Install every workspace package and the dev tools (from the repository root)
uv sync --all-packages

# Apply the Alembic migrations (from packages/persistence/, where alembic.ini and alembic/ live)
cd packages/persistence
mkdir -p .coh
uv run alembic upgrade head
```

`alembic.ini` sets `script_location = alembic`, which resolves against the current directory, so the command fails from the repository root. `alembic/env.py` writes to `sqlite:///.coh/coh.db` relative to the current directory and does not create `.coh/`; without it the run fails with "unable to open database file". The result is `packages/persistence/.coh/coh.db`. The MCP adapter and the API do not open that file: each uses `.coh/coh.db` under its own project root or working directory (`handlers.py:46-49`, `composition.py:15-19`).

## Usage

```python
from persistence.infrastructure import (
    create_engine,
    get_session_factory,
    SqlAlchemyUnitOfWork,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.enums import SessionIntent, LifecycleState

# Create engine and session factory
engine = create_engine("sqlite:///.coh/coh.db")
session_factory = get_session_factory(engine)

# Use unit of work for transactional operations
with SqlAlchemyUnitOfWork(session_factory) as uow:
    session = ExecutionSession(
        project_id="my-project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.INSPECT,
    )
    uow.sessions.add(session)
    uow.commit()

# Load session in a new transaction
with SqlAlchemyUnitOfWork(session_factory) as uow:
    loaded_session = uow.sessions.get(session.id)
    # Update with optimistic concurrency check
    loaded_session.lifecycle_state = LifecycleState.SPECIFY
    loaded_session.increment_version()
    uow.sessions.update(loaded_session, expected_version=1)
    uow.commit()
```

## Design Decisions

### JSON Storage for Nested Models

Nested Pydantic models (e.g., `Specification.done_when`, `Task.dependencies`, `Checkpoint.spec_snapshot`) are stored as JSON columns rather than normalized tables. This simplifies the schema and improves read performance for aggregate reconstruction.

### Optimistic Concurrency

The `ExecutionSession` repository enforces optimistic concurrency control:
- `expected_version` parameter in `update()` must match current DB version
- Mismatch raises `OptimisticLockError`
- Domain model's `increment_version()` method must be called before update

### Idempotency Keys

All repositories support optional `idempotency_key` for write operations. Duplicate keys for different entities raise `IdempotencyKeyViolation`. Same key for same entity is silently ignored (write is idempotent).

### Foreign Key Constraints

- `ExecutionSession.current_spec_id` → `Specification.id`
- `Task.spec_id` → `Specification.id`
- `Evidence.spec_id` → `Specification.id`
- `Checkpoint.session_id` → `ExecutionSession.id`

When persisting entities with dependencies, commit parents before children.

## Schema Notes

- **Snake_case columns**: All database columns use `snake_case` naming (e.g., `current_spec_id`, `created_at`)
- **UUID as string**: UUIDs stored as `String(36)` for SQLite compatibility
- **Datetime**: Stored as ISO-8601 strings (SQLite `DATETIME` type)
- **Enums**: Stored as string values (e.g., `"execute"`, `"INSPECT"`)

## Testing

```bash
# Run all persistence tests (from the repository root)
uv run pytest tests/packages/persistence -v

# Run crash/restart test specifically
uv run pytest tests/packages/persistence/test_crash_restart.py -v
```

The crash/restart test (`test_crash_restart.py`) proves that:
1. Session + spec + checkpoint can be persisted
2. After simulated crash (new engine), data can be loaded
3. Spec body can be restored from `Checkpoint.spec_snapshot`

## Trade-offs

**Benefits:**
- Simple schema with fewer joins
- Fast aggregate reconstruction
- Clear separation between domain and persistence
- WAL mode enables concurrent reads during writes

**Trade-offs:**
- JSON columns not normalized (queries within nested structures require JSON functions)
- No foreign key cascades (application must manage deletion order)
- Optimistic locking requires client retry logic

## Next Actions

Phase 1 (this package) provides persistence only. Future phases:

1. ✅ ~~**Archive Writer**: Append-only `.coh/archive/` for full interaction history~~ — Complete: `packages/archive`
2. ✅ ~~**FastAPI Integration**: REST endpoints exposing repositories~~ — Complete: `apps/api`; its routes call application services, which reach these repositories through the unit of work
3. **Huey Task Queue**: Async processing for long-running operations (planned; Decision D2)
4. ✅ ~~**MCP Adapter**: Claude Code server for agent interactions~~ — Complete: `packages/mcp_adapter`
