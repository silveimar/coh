> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`
> Classification is deterministic in v1 (Decision D10): relevance and blocking impact come from configurable heuristics, not an ML classifier.

## Feature Summary

Capture secondary actions, follow-ups, and side discoveries without disrupting the active task (NOW). The parking lot preserves context and source relationships while keeping the execution foreground small; NOW is the currently active task or goal the user is focused on.

### Scope

* **In scope**: Create, classify, list, promote, dismiss, and archive parking items.
* **Out of scope**: Automatic project backlog management or reminders.
* **Prerequisites**: Active task/goal context and project-local state.
* **Depends on**: Foreground service, recovery records, interaction archive.

## Acceptance Criteria

### Must-Have (P0)

1. User or agent can park a secondary action without changing the active NOW task.
2. Each item stores text, source task or goal, context, relevance, blocking impact, suggested disposition, created time, and status.
3. Low-relevance, non-blocking discoveries can be parked automatically using deterministic, configurable rules (default: relevance = low AND blocking impact = false); automatically parked items are disclosed in the next concise update and surfaced with a link to their source.
4. High-relevance discoveries require a recommendation to investigate, continue intentionally, or park; current task checkpoint is preserved first.
5. Parking item creation, promotion, dismissal, and status changes are appended to the Markdown archive.

### Should-Have (P1)

6. User can promote an item to a planned task without retyping its captured context.
7. Items may have an optional revisit trigger such as after current goal, on next planning session, or manual review.

### Nice-to-Have (P2)

8. The system groups similar parking items while retaining originals and source links.

## User Flow

### Happy Path

1. **Entry point**: User is executing NOW and identifies a follow-up.
2. **Action**: User says `park` or agent detects a low-relevance side discovery.
3. **Feedback**: System confirms item is parked and keeps NOW unchanged.
4. **Result**: Parked count increments; the item is available for later review.
5. **Next step**: User continues NOW or promotes item during planning.

### Alternate Paths

* **Path B**: If discovery may invalidate current work, system checkpoints and recommends a detour.
* **Path C**: If user rejects an item, mark dismissed with reason; do not delete history.

## Edge Cases & Error States

### Input Validation

* Empty item text → reject with `Describe the follow-up or discovery to park.`
* Missing source context → allow item but mark source as project-level.
* Duplicate item → warn with existing item link; user may create a distinct item.

### System Errors

* Write failure → do not claim item is parked; retain draft and offer retry.
* Archive failure after state write → mark archive pending and repair later.
* Timeout → retain local draft.

### Permission & State

* No active task → allow project-level parking.
* Completed source task → preserve association and allow promotion.
* Empty state → show `No parked items.`
* Concurrent updates → create revisions; do not overwrite user notes.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/parking_item.py` — schema and validation.
* `packages/execution-core/src/execution_core/policies/parking_policy.py` — deterministic relevance/blocking rules.
* `apps/api/src/coh_api/application/parking_service.py` — capture, promote, dismiss, review.
* `apps/api/src/coh_api/infrastructure/repositories/parking_repository.py` — persistence.
* `packages/archive/src/coh_archive/writer.py` — event entries.
* `packages/execution-core/tests/test_parking_policy.py` and `apps/api/tests/test_parking_service.py` — lifecycle tests.

### Data Flow

1. Agent/user submits secondary action or discovery.
2. Service attaches source context and evaluates relevance/blocking impact with deterministic, configurable rules.
3. Default policy: relevance = low AND blocking = false → auto-park; relevance = high OR blocking = true → checkpoint current task and recommend investigate / continue intentionally / park.
4. Low-risk item persists without switching foreground; high-risk item checkpoints first.
5. Archive records the event with source link, timestamp, and rule-evaluation metadata.
6. Review or promotion converts selected item into a plan candidate/task; promotion copies source context and preserves the original item as linked history.

### New Dependencies

None.

## Dependencies & Risks

### Dependencies

* **Upstream**: Task/goal context, foreground, recovery.
* **Downstream**: Drift behavior, planning, visual Quest Map.
* **External**: None.

### Technical Risks

* **Performance**: Large parking lists need filtering; defer indexing until needed.
* **Security**: Parking notes may contain sensitive discoveries; local storage rules apply.
* **Data integrity**: Promotion must retain source and avoid duplicated task identity.

### Rollout Strategy

* **Feature flag**: `parkingLot.enabled`.
* **Staged rollout**: Manual capture, then automatic low-risk capture.
* **Rollback plan**: Disable automatic capture; retain records.

## Test Plan

### Manual Testing

1. Park a follow-up while a task is active and verify NOW does not change.
2. Promote parked item into a task and verify context carries over.
3. Trigger high-relevance discovery and verify checkpoint/recommendation behavior.

### Automated Tests

* **Unit tests**: Validation, classification handling, duplicate detection.
* **Integration tests**: State/archive consistency and promotion.
* **E2E tests**: Execute task, park item, complete task, promote item.

### Regression Checks

* Verify parked items remain outside NOW + NEXT 2.
* Verify interruption recovery lists associated parked count.
* Check error tracking for failed parking writes.
