> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`

## Feature Summary

Implement evidence-based completion so the system distinguishes Implemented, Tested, Verified, and Done. It prevents false completion claims by mapping acceptance criteria to durable evidence.

### Scope

* **In scope**: Completion states, evidence records, criterion evaluation, verification output, and failure return to execution.
* **Out of scope**: Test runner implementation, CI provider integration, deployment automation.
* **Prerequisites**: Specification with DONE WHEN criteria and task state.
* **Depends on**: Archive, state store, agent adapter/tool events.

## Acceptance Criteria

### Must-Have (P0)

1. System represents IMPLEMENTED, TESTED, VERIFIED, and DONE as separate states.
2. DONE is permitted only when every agreed DONE WHEN criterion has supporting evidence (valid for current spec revision and trusted) or explicit user acceptance recorded with rationale and approver identity.
3. Evidence records include criterion reference (spec id + criterion id + spec revision), evidence type (test/build/inspection/reproduction/user-acceptance), source (agent/tool/user with identity), timestamp, result (pass|fail|inconclusive|accepted), summary, archive/tool reference when available, and an **authority level** — a source-derived enum: `tool_verified` (produced by a tool run COH observed), `agent_reported` (claimed by an agent without observed tool output), or `user_accepted` (explicit user acceptance with rationale). Only `tool_verified` or `user_accepted` evidence can satisfy a done-when criterion; `agent_reported` evidence is supplemental.
4. Failed verification preserves evidence, updates the task status, and returns work to EXECUTE rather than declaring completion.
5. Completion output lists deliverable, verified criteria, remaining blockers, and retained parked discoveries concisely.

### Should-Have (P1)

6. System detects stale evidence when the specification or relevant implementation revision changes.
7. User can mark an acceptance criterion accepted manually with recorded rationale.

### Nice-to-Have (P2)

8. System recommends the minimum evidence needed for each criterion.

## User Flow

### Happy Path

1. **Entry point**: Implementation work reaches a task or deliverable completion candidate.
2. **Action**: Agent records test, build, inspection, reproduction, or user-acceptance evidence.
3. **Feedback**: System shows criterion-by-criterion verification status including: evidence list (with provenance), current result, freshness relative to spec revision, and recommended next action when failed or inconclusive.
4. **Result**: All criteria pass and status advances to Verified then Done.
5. **Next step**: System emits concise completion summary and preserves parking items.

### Alternate Paths

* **Path B**: If a criterion fails, show evidence and recommended next execution action.
* **Path C**: If evidence cannot be automated, request user acceptance with clear scope.

## Edge Cases & Error States

### Input Validation

* Evidence without criterion reference → store as supplemental only; cannot satisfy Done When.
* Unsupported result → reject; allow pass, fail, inconclusive, accepted.
* Empty user-acceptance rationale → require reason.

### System Errors

* Tool result unavailable → record inconclusive evidence and do not advance status.
* State write failure → do not display Verified or Done.
* Timeout → preserve pending verification attempt.

### Permission & State

* Review-only session → collect findings but do not claim implementation/verification.
* Stale evidence → mark needs revalidation.
* No criteria → block Done and direct user to Spec Gate.
* Concurrent evidence updates → append evidence; recompute criterion status.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/evidence.py` — evidence model, result types, authority levels.
* `packages/execution-core/src/execution_core/policies/completion_policy.py` — completion-state transition rules (Implemented/Tested/Verified/Done) and staleness detection.
* `apps/api/src/coh_api/application/verification_service.py` — record/evaluate evidence.
* `packages/agent-runtime/src/agent_runtime/adapter.py` — tool/test evidence normalization (incl. `run_tests` task_id linkage per the PRD contract).
* `apps/api/src/coh_api/infrastructure/repositories/evidence_repository.py` — evidence persistence.
* `tests/packages/execution-core/test_completion_policy.py` — transition and staleness tests.

### Data Flow

1. Adapter or user supplies evidence.
2. Verification service validates and links it to criterion/spec revision.
3. Service computes criterion and deliverable completion state.
4. State/archive writes persist evidence and transition.
5. Presenter returns verified/failure summary and next action.

### New Dependencies

None.

## Dependencies & Risks

### Dependencies

* **Upstream**: Spec Gate, task execution, tool events.
* **Downstream**: Recovery, visual completion view, analytics.
* **External**: Optional test/build tools through adapters.

### Technical Risks

* **Performance**: Large evidence sets require indexed criterion lookup.
* **Security**: Tool output may contain secrets; archive redaction policy must apply.
* **Data integrity**: Do not allow stale evidence to satisfy revised requirements.

### Rollout Strategy

* **Feature flag**: `verificationGate.enabled`.
* **Staged rollout**: Display statuses, then enforce Done gate.
* **Rollback plan**: Disable enforcement while retaining evidence.

## Test Plan

### Manual Testing

1. Add passing evidence for all criteria and verify Done.
2. Add failed test evidence and verify return to Execute.
3. Revise a criterion and verify old evidence becomes stale.

### Automated Tests

* **Unit tests**: State machine, evidence validation, stale detection.
* **Integration tests**: Tool-event normalization and archive references.
* **E2E tests**: Implement through verified completion.

### Regression Checks

* Verify archive is append-only for evidence.
* Verify parked work does not block Done unless explicitly a criterion.
* Check error tracking for false completion attempts.
