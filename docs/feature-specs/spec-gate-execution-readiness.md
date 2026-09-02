> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`

## Feature Summary

Implement the mandatory specification gate that converts intent into WHAT, WHY, DELIVERABLE, and DONE WHEN before material execution. The feature exposes Spec Clarity and binary Execution Readiness while minimizing unnecessary user questions. This is the COH **Orient** phase (Decision D4).

### Scope

* **In scope**: Proposed specifications, field confirmation, assumptions/unknowns, clarity levels, readiness gate, and agent question policy.
* **Out of scope**: Automated code inspection implementation, full planning, mutation execution.
* **Prerequisites**: Project context and agent adapter input/output contract.
* **Depends on**: State store, language layer, archive.

## Acceptance Criteria

### Must-Have (P0)

1. Every material execution request has WHAT, WHY, DELIVERABLE, and DONE WHEN recorded before mutation begins.
2. System proposes inferred fields after inspection rather than requiring the user to author a spec from scratch.
3. Spec Clarity displays only Low, Medium, High, or Ready; percentage completeness is available only in expanded detail.
4. Execution Readiness displays only Ready or Blocked and is Ready only when required fields exist, no blocking unknown/assumption remains, and no unresolved confirmation-required risk exists.
5. Blocking questions are grouped, minimal, and include one recommended default where practical.
6. Read-only inspection remains permitted while execution readiness is Blocked; material mutation is rejected.

### Should-Have (P1)

7. Assumptions are classified Safe, Material, or Blocking and retain rationale.
8. Goal change checkpoints active work and creates a new specification revision.

### Nice-to-Have (P2)

9. Expanded completeness explains which missing fields or unknowns prevent Ready.

## User Flow

### Happy Path

1. **Entry point**: User requests a change or outcome.
2. **Action**: Adapter performs allowed read-only inspection and proposes the spec.
3. **Feedback**: User sees clarity, readiness, assumptions, and only necessary confirm/correct prompts.
4. **Result**: Confirmation resolves blocking gaps and state becomes Ready.
5. **Next step**: Planning can generate NOW + NEXT 2.

### Alternate Paths

* **Path B**: If spec is inferably complete, show inferred Ready spec and proceed without forced confirmation.
* **Path C**: If user changes goal, checkpoint previous work and restart the gate.

## Edge Cases & Error States

### Input Validation

* Missing mandatory field → readiness remains Blocked with field-specific explanation.
* Conflicting field values → require resolution and preserve alternatives.
* Invalid clarity value → compute from canonical state; reject client-provided value.

### System Errors

* Inspection failure → show available evidence, mark gaps unknown, and ask only undiscoverable essential question.
* State write failure → do not grant Ready; retain proposed spec locally for retry.
* Timeout → keep read-only findings and report incomplete inspection.

### Permission & State

* Unauthorized inspection path → identify unavailable source without inventing findings.
* Stale confirmation → compare spec revision and request review of changed fields.
* Empty request → request objective, not implementation details.
* Rate limited agent → allow user confirmation of known fields, defer further inspection.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/specification.py` — full spec model (what/why/deliverable/done-when/constraints/non-goals/assumptions/unknowns), clarity/readiness rules, assumption classes.
* `packages/execution-core/src/execution_core/policies/readiness_policy.py` — readiness gate evaluation.
* `apps/api/src/coh_api/application/spec_gate_service.py` — propose, confirm, revise, authorize execution.
* `apps/api/src/coh_api/application/question_policy.py` — question budget and recommendation formatting.
* `packages/agent-runtime/src/agent_runtime/adapter.py` — inspection capability interface.
* `apps/api/src/coh_api/infrastructure/repositories/spec_repository.py` — spec revisions.
* `packages/execution-core/tests/test_readiness_policy.py` — readiness truth table.

### Data Flow

1. User request enters adapter.
2. Adapter returns inspection evidence.
3. Spec service derives proposal, unknowns, assumptions, clarity, and readiness.
4. User confirmation updates only selected fields.
5. Service writes revision and emits archive event.
6. Plan/mutation services request readiness authorization.

### New Dependencies

None.

## Dependencies & Risks

### Dependencies

* **Upstream**: Agent adapter inspection capabilities.
* **Downstream**: Planning, execution autonomy, verification.
* **External**: None.

### Technical Risks

* **Performance**: Excessive inspection can delay action; bound inspection by relevance.
* **Security**: Do not inspect unavailable/unauthorized resources.
* **Data integrity**: Readiness must be recomputed after every material spec revision.

### Rollout Strategy

* **Feature flag**: `specGate.enabled`.
* **Staged rollout**: Advisory mode, then enforce before mutations.
* **Rollback plan**: Return to advisory while preserving spec history.

## Test Plan

### Manual Testing

1. Submit vague request and verify proposal plus targeted question.
2. Submit clear constrained request and verify Ready without extra confirmation.
3. Change goal mid-task and verify checkpoint plus new gate.

### Automated Tests

* **Unit tests**: Readiness truth table, assumption classes, clarity presentation.
* **Integration tests**: Mutation authorization and revision conflict handling.
* **E2E tests**: Request through Ready plan entry.

### Regression Checks

* Verify language complexity does not change semantic clarity.
* Verify archive captures user confirmations.
* Check error tracking for blocked-but-mutated attempts.
