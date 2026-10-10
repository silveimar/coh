# ADR-NNNN: <short title in the imperative, e.g. "Use Hypothesis for state-machine tests">

- **Status:** Proposed | Accepted | Rejected | Superseded by ADR-NNNN
- **Date:** YYYY-MM-DD
- **Deciders:** <owner approval is required for Accepted; list who proposed and who decided>
- **Slice / PR:** <card or slice id, PR link>
- **Decision log:** <D-number if this also changes a recorded decision, otherwise "none">

## Question

What are we deciding, in one or two sentences? State the trigger: which dependency, service, datastore, schema change, API change or refactor made this decision necessary now.

## Context

What forces apply? Include the constraints that make this hard: local-first (D1, D7), the Execution Core boundary, wire format (D10), archive rules (D6), the slice spec, cost, quota and time. Facts only, each with a source (file, commit, PR or doc). Mark anything inferred as inferred.

## Options considered

### Option A: <name>
- What it is, in one line.
- Pros:
- Cons:
- Cost to adopt and to reverse:

### Option B: <name>
- What it is, in one line.
- Pros:
- Cons:
- Cost to adopt and to reverse:

(Add options as needed. "Do nothing" is always an option; include it.)

## Decision

**Selected:** Option <X>.

One short paragraph on why it wins against the constraints above. Say what you are accepting as the downside.

## Consequences

- **What changes:** files, modules, dependencies, migrations, CI jobs, docs.
- **What gets easier:**
- **What gets harder:**
- **Follow-up work:** each item is a new card or slice, not a TODO in code.
- **Rollback:** how to undo this, and what it would cost.

## Compliance checklist

Tick what applies. Unticked items need a line explaining why.

- [ ] Stays inside the layer rules (no FastAPI, SQLAlchemy, Huey, MCP or provider-SDK imports in `packages/execution-core`)
- [ ] New dependency: name, version, license (MIT, Apache-2.0, BSD or ISC, otherwise owner approval), maintenance status
- [ ] Schema change: Alembic migration in the same PR (and the data dictionary, if it exists in this repo)
- [ ] Public API, wire format or archive format change: versioning and compatibility plan
- [ ] No new infrastructure (Docker, Redis, Celery, cloud) without a documented requirement
- [ ] Tests and, where behavior changes, eval scenarios updated
- [ ] Decision-log entry added if execution semantics change

## Reopen when

The conditions under which this decision should be revisited (a metric, a scale limit, a dependency end of life, a new requirement).

## References

Links to the spec, PR, issue, benchmark or external documentation. Every claim above that is not obvious should trace to one of these.
