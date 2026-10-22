# COH Execution Core

**Pure Python deterministic domain model implementing the COH lifecycle, policies, and invariants I-01 through I-14.**

## Overview

The execution-core package is the authoritative source for COH's execution semantics. It implements:

- **7-state lifecycle:** INSPECT → SPECIFY → CONFIRM → PLAN → EXECUTE → VERIFY → COMPLETE
- **Transitions T1-T11** with guard validation
- **Invariants I-01 through I-14** enforced via domain policies
- **Checkpoint and recovery** (cross-cutting event and entry command)
- **Evidence-based verification** with authority levels and staleness detection

## Architecture

```
src/execution_core/
├── domain/           # Aggregates and entities
│   ├── session.py        # ExecutionSession aggregate root
│   ├── specification.py   # WHAT/WHY/DELIVERABLE/DONE WHEN
│   ├── task.py           # Atomic work units with dependencies
│   ├── evidence.py       # Criterion-linked verification evidence
│   ├── checkpoint.py     # Recovery records with restart actions
│   ├── decision.py       # Rationale preservation
│   ├── parking_item.py   # Secondary actions and discoveries
│   ├── foreground.py     # NOW + NEXT 2 execution surface
│   ├── commands.py       # Command types with idempotency and concurrency control
│   ├── enums.py          # Shared enums and value types
│   └── clock.py          # Naive UTC clock for timestamp defaults
├── state_machine/   # Lifecycle transitions
│   └── lifecycle.py      # T1-T11 with TransitionError
├── policies/        # Invariant enforcement
│   ├── readiness_policy.py      # I-02: no mutation while blocked
│   ├── foreground_policy.py     # I-01: one NOW, two NEXT
│   ├── completion_policy.py     # I-03: evidence gate
│   ├── parking_policy.py        # I-05, I-10, I-11
│   ├── permission_policy.py     # I-08: permission matrix
│   └── integrity_policy.py      # I-04, I-06, I-07, I-12, I-13
└── events/          # Domain events for audit
    └── domain_events.py  # Domain event models
```

## Key Invariants

- **I-01 (Foreground):** At most one NOW and two NEXT tasks; NOW has all required metadata and no unresolved dependencies
- **I-02 (Readiness gate):** No material mutation while readiness = Blocked
- **I-03 (Evidence gate):** Work never reported Verified/Done without criterion-linked, non-stale, qualifying evidence
- **I-06 (Proposal-only AI):** LLM output validated before authoritative state changes
- **I-08 (Permission matrix):** Inspection/spec/plan automatic; large/destructive changes need confirmation

See [docs/behavioral-contract.md](../../docs/behavioral-contract.md) for all 14 invariants.

## Usage

```python
from execution_core.state_machine.lifecycle import StateMachine
from execution_core.domain.session import ExecutionSession
from execution_core.domain.enums import SessionIntent

# Start a session
session = StateMachine.start_session("project-1", SessionIntent.EXECUTE)

# Transition through lifecycle
session = StateMachine.transition_to_specify(session, findings_archived=True)
# ... propose spec, transition to CONFIRM, etc.
```

## Testing

Tests cover:

- **Unit tests:** All domain models, state machine transitions, policy rules
- **Property-based tests (Hypothesis):** State machine invariants, policy consistency
- **Coverage:** ≥90% lines in execution-core

```bash
# Run tests (from the repository root)
uv run pytest tests/packages/execution-core

# With coverage
uv run pytest tests/packages/execution-core --cov --cov-report=html

# Property-based tests only
uv run pytest tests/packages/execution-core/test_properties.py
```

## Design Choices

### Synchronous Domain

The domain layer is purely synchronous. Async boundaries belong at I/O (HTTP, MCP, LLM calls), not in deterministic policy evaluation.

### Pydantic Models

All domain entities use Pydantic for:
- Schema validation
- JSON serialization (snake_case)
- Type safety with Python 3.15+ type hints

### No Framework Dependencies

The package imports no FastAPI, SQLAlchemy, Huey, or MCP. Those live in the application and adapter layers.

### Optimistic Concurrency

Commands that mutate sessions carry `expected_version`. Idempotency keys are required but do not replace concurrency control.

## Assumptions

1. **Single-project sessions:** Each session works on one project at a time
2. **Local execution:** No distributed coordination needed
3. **Human-in-the-loop:** Confirmations belong to users, not inferred

## Trade-offs

- **Strict validation:** Guards prevent invalid transitions at the cost of verbosity
- **Revision-based history:** Supersession rather than mutation preserves causality but increases storage
- **No ORM in domain:** Keeps domain pure but requires mapping in infrastructure layer

## Next Actions

### Application Layer (not in this package)
- ✅ ~~Persistence via SQLAlchemy repositories~~ — Complete: `packages/persistence`
- ✅ ~~HTTP API with FastAPI routes~~ — Complete: `apps/api`
- Background jobs via Huey (planned; Decision D2)

### Adapter Layer (not in this package)
- ✅ ~~MCP server implementing adapter contract~~ — Complete: `packages/mcp_adapter`
- ✅ ~~Archive writer for `.coh/archive/`~~ — Complete: `packages/archive`

### Phase 1+
- Visual Focus/Recovery UI
- Drift automation
- Multi-device sync (CRDTs)

## Dependencies

- `pydantic>=2.9.0` - domain model validation

### Dev Dependencies
Dev tools are declared once, in the root `pyproject.toml` `[dependency-groups] dev` group (ADR 0001, `docs/adr/0001-uv-dev-dependency-group.md`): pytest, pytest-asyncio, pytest-cov, hypothesis, ruff, pyright and httpx. `uv sync --all-packages` installs them.

## Contributing

1. Read `docs/coding-rules.md` and `docs/behavioral-contract.md`
2. Write tests before/alongside changes
3. Run `uv run ruff format .` and `uv run ruff check .`
4. Ensure `uv run pytest tests` passes with ≥90% coverage
5. Changes affecting invariants or transitions require a Decision Log entry

## License

[To be determined]
