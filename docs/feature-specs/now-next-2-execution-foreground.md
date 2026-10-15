> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`
> Energy and activation-friction use enums `low | medium | high` (Decision D10); no numeric scales in contracts.

## Feature Summary

Create the focused execution foreground that shows exactly one current task and two ordered next tasks while preserving the larger plan outside working memory. It helps users start work and avoid overwhelm without losing dependency-aware context.

### Scope

* **In scope**: Task selection, NOW + NEXT 2 projection, task metadata, ordering, and foreground updates.
* **Out of scope**: Full project scheduling, calendar integration, visual timer UI.
* **Prerequisites**: Goal, specification, task, and execution-readiness state.
* **Depends on**: Spec gate, state store, parking lot, recovery records.

## Acceptance Criteria

### Must-Have (P0)

1. For an executable goal, the system shows one NOW task and at most two NEXT tasks.

2. Every foreground task has a literal action, Done When criterion, estimated time, energy level, and activation-friction level.

3. The system never selects a task with unresolved dependencies as NOW.

4. Completing, blocking, parking, or interrupting NOW recalculates the foreground and persists the prior task status.

5. The foreground does not expose more than three executable tasks by default; remaining work is summarized as parked or hidden plan count.

6. The system records and reports foreground metrics locally: (a) % of sessions where the user starts NOW within 2 minutes, (b) average time-to-next-promotion after completing NOW, and (c) % of manual overrides per active plan.

### Should-Have (P1)

7. Ordering considers goal leverage, dependency readiness, unblocking value, risk reduction, evidence generation, activation friction, and effort.
8. User can manually select an eligible task as NOW; the system records the override reason if supplied.

### Nice-to-Have (P2)

9. The system adapts recommendation order to a user-selected energy availability setting.

## User Flow

### Happy Path

1. **Entry point**: A READY specification has a plan with eligible tasks.
2. **Action**: System calculates the foreground.
3. **Feedback**: User sees Goal, NOW, Done When, NEXT 1, NEXT 2, and Parked count.
4. **Result**: User performs NOW and records progress or evidence.
5. **Next step**: System promotes the next eligible task after completion.

### Alternate Paths

* **Path B**: If no task is eligible, show blockers and the recommended unblock action.
* **Path C**: If user chooses another eligible task, update NOW and preserve the former recommendation in plan history.

## Edge Cases & Error States

### Input Validation

* Missing literal action → task cannot enter foreground; return validation error with example of required literal action format (e.g., "Write 300-word summary of section X").
* Missing Done When → task can be planned but not selected as NOW; surface guidance to add a measurable Done When (e.g., "send draft to reviewer").
* Invalid time, energy, or activation values → reject with field-specific validation and allowed values (time: 1–480 minutes; energy: `low|medium|high`; activation friction: `low|medium|high`).

### System Errors

* State read failure → show last durable foreground with stale indicator and retry.
* Foreground write failure → do not claim promotion; retain prior foreground.
* Calculation timeout → use deterministic dependency-first fallback and record fallback use.

### Permission & State

* BLOCKED execution readiness → show proposed next discovery/confirmation action, not implementation work.
* Concurrent task update → resolve against latest task revision and recalculate.
* Empty plan → show `No executable task yet` with CTA to create plan.
* Rate limited adapter → keep local foreground state unchanged.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/task.py` — task metadata, eligibility, status, foreground position.
* `packages/execution-core/src/execution_core/policies/foreground_policy.py` — deterministic ranking and NOW/NEXT selection.
* `apps/api/src/coh_api/application/foreground_service.py` — calculate and promote foreground.
* `apps/api/src/coh_api/infrastructure/repositories/task_repository.py` — foreground persistence.
* `apps/api/src/coh_api/api/schemas/foreground.py` — output contract (read model).
* `tests/packages/execution-core/test_foreground_policy.py` — ordering and transition tests.

### Data Flow

1. Plan or task status changes.
2. Foreground service loads READY spec, task graph, user preferences (including energy availability), and active checkpoint.
3. Eligibility filter removes completed, parked, blocked, and invalid tasks.
4. Ranking selects NOW and two NEXT tasks using a weighted scoring function (example weights: dependency_readiness=0.3, goal_leverage=0.25, unblocking_value=0.15, effort=-0.15, activation_friction=-0.1). Include deterministic tie-breaker by earliest creation or lowest id.
5. Store persists a foreground revision and an immutable audit record for manual overrides (user id, timestamp, reason).
6. Presenter emits concise execution output and archive event.

### New Dependencies

No new packages required; use existing graph utilities or implement a small dependency traversal utility.

## Dependencies & Risks

### Dependencies

* **Upstream**: Spec gate and task model.
* **Downstream**: Recovery, timers, visual Focus view.
* **External**: None.

### Technical Risks

* **Performance**: Large plans may make ranking expensive; only rank eligible frontier tasks.
* **Security**: No new external surface.
* **Data integrity**: Manual overrides must not break dependency constraints.

### Rollout Strategy

* **Feature flag**: `foreground.enabled`.
* **Staged rollout**: Default output only, then persistent automatic promotion.
* **Rollback plan**: Return full task list view while retaining task state.

## Test Plan

### Manual Testing

1. Create five dependent tasks and verify one NOW plus two NEXT only.
2. Complete NOW and verify correct promotion.
3. Attempt to select a blocked task and confirm rejection.

### Automated Tests

* **Unit tests**: Eligibility, ranking, metadata validation.
* **Integration tests**: Persisted promotion and concurrent updates.
* **E2E tests**: Ready spec through task completion.

### Regression Checks

* Verify parking items do not appear as foreground tasks.
* Verify recovery records capture foreground transitions.
* Check error tracking for invalid plan data.
