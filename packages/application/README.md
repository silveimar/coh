# COH Application Services

**Phase 1 deliverable** · 2026-09-03

Application services layer composing execution-core policies with persistence for spec-gate and foreground execution. No FastAPI, no HTTP, no Huey, no UI, no telemetry — pure application coordination layer.

## Purpose

The application package implements two critical COH services:

- **Spec Gate Service (I-02)**: Enforces readiness-based mutation control. Proposes, confirms, and revises specifications; computes clarity + binary readiness; generates grouped minimal questions with recommended defaults; rejects material mutation while Blocked; always permits read-only inspection.

- **Foreground Service (I-01)**: Enforces exactly 1 NOW + ≤2 NEXT task presentation with required metadata (literal action, done-when, minutes, energy, activation friction); prevents tasks with unresolved dependencies from becoming NOW; recalculates foreground on complete/block/park/interrupt; persists prior task status (I-05).

## Installation

```bash
cd /path/to/coh
uv sync --all-packages
```

## Usage

### Spec Gate Service

```python
from persistence.infrastructure.database import create_engine, init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from sqlalchemy.orm import sessionmaker
from coh_application import SpecGateService

engine = create_engine("sqlite:///.coh/coh.db")
init_db(engine)
session_factory = sessionmaker(bind=engine)

with SqlAlchemyUnitOfWork(session_factory) as uow:
    service = SpecGateService(uow)
    
    # Propose spec after inspection
    spec = service.propose_spec(
        session_id=session_id,
        what="Implement user authentication",
        why="Security requirement",
        deliverable="Working login/logout with JWT",
        done_when=["User can login", "User can logout"],
    )
    
    # Check readiness before mutations
    allowed, state, blockers = service.check_mutation_allowed(session_id)
    if not allowed:
        print(f"Blocked: {blockers}")
    
    # Confirm when ready
    if spec.readiness == "ready":
        confirmed = service.confirm_spec(session_id, spec)
```

### Foreground Service

```python
from coh_application import ForegroundService

with SqlAlchemyUnitOfWork(session_factory) as uow:
    service = ForegroundService(uow)

    # Calculate foreground (1 NOW + ≤2 NEXT)
    foreground = service.calculate_foreground(session_id)

    print(f"NOW: {foreground.now_task.action_literal}")
    print(
        f"NEXT 1: {foreground.next_1_task.action_literal if foreground.next_1_task else 'None'}"
    )
    print(f"Parked: {foreground.parked_count}")

    # Complete NOW and promote
    new_fg = service.complete_now_task(
        session_id, foreground.now_task.id, "Completed successfully"
    )
```

## Architecture

```
Application Services
  ↓
SpecGateService / ForegroundService
  ↓
Execution Core (policies: ReadinessPolicy, ForegroundPolicy)
  ↓
Persistence (UnitOfWork → repositories)
  ↓
SQLAlchemy models → `.coh/coh.db`
```

Deterministic policies in execution-core compute readiness/foreground; application services coordinate persistence and enforce invariants.

## Testing

```bash
# Run application tests
pytest packages/application/tests -v

# With coverage
pytest packages/application/tests --cov=packages/application/src
```

Tests cover:
- **Spec gate**: Readiness truth table (WHAT/WHY/DELIVERABLE/DONE WHEN required, blocking unknowns/assumptions, unconfirmed material assumptions); I-02 mutation rejection when Blocked; read-only inspection always permitted; question policy (grouped, minimal, recommended defaults)
- **Foreground**: I-01 (exactly 1 NOW + ≤2 NEXT); NOW metadata required (action_literal, done_when_condition, estimated_minutes, energy, activation_friction); unresolved dependencies never NOW; recalculation on complete/block/park/interrupt; progress records before foreground change (I-05)

## Trade-offs

1. **No HTTP/SSE**: Application services are pure Python; FastAPI integration is the next layer (Phase 2)
2. **UnitOfWork per operation**: Each service method expects a fresh UnitOfWork context; caller manages transaction boundaries
3. **Spec loading helper**: `_load_current_spec()` manually loads spec from database because ExecutionSessionMapper doesn't populate relationships (decision: keep mapper simple, let services handle loading)
4. **Progress records created but not persisted**: TaskProgressRecord objects are created in foreground methods (I-05 compliance) but not yet wired to a repository; persistence is deferred to task history feature
5. **No archive integration**: Services don't emit archive events yet; archive wiring is MCP adapter's responsibility (already done there for session/spec/checkpoint)

## Invariants Enforced

- **I-01**: Foreground shows exactly 1 NOW + ≤2 NEXT; NOW has required metadata; task with unresolved dependencies is never NOW
- **I-02**: Material mutation rejected when readiness=BLOCKED; read-only inspection always permitted
- **I-05**: Progress record created before interrupting/completing/blocking NOW task (currently created but not persisted)

## Next Actions

1. Add FastAPI routes wrapping these services (apps/api or separate HTTP layer)
2. Wire TaskProgressRecord persistence to a repository
3. Emit archive events from service methods (or keep it in adapter layer)
4. Add service-level metrics (readiness check frequency, foreground recalculation triggers)
5. Implement remaining MCP tools using these services (`plan_work`, `execute_task`, `verify_deliverable`)

## Dependencies

- `execution-core` — Domain logic (Specification, Task, policies)
- `persistence` — SQLAlchemy repositories + UnitOfWork
- `coh-archive` — (not yet integrated at service layer)
