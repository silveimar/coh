> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`

## Feature Summary

Persist meaningful decisions with the chosen option, rationale, alternatives, evidence, and conditions for reopening. This protects context continuity for users and agents across interruptions and future work.

**Materiality rule:** a decision is *material* — and prompts a recorded decision — when it constrains future implementation choices, changes external or public behavior, is costly to reverse, or resolves a blocking assumption. Minor, cheaply reversible choices stay in task notes and are not logged as decisions.

### Scope

* **In scope**: Create, link, retrieve, supersede, and reopen decision records.
* **Out of scope**: Automated architecture decision generation or organization-wide governance.
* **Prerequisites**: Project/goal context and archive.
* **Depends on**: State store, recovery records, spec revisions.

## Acceptance Criteria

### Must-Have (P0)

1. User or agent can record a meaningful decision with the following explicit fields: question, selected option, concise rationale (why), alternatives, rejected-alternative rationale, evidence/context (links or attachments), timestamp, author (user/agent), materiality flag, and lifecycle state (active/superseded/reopened).
2. Every decision links to project and applicable goal/spec/task context.
3. Recovery summaries show the latest relevant decision and its rationale when one exists.
4. A decision is reopened only on new evidence, changed constraints, changed goal, invalidated assumption, or explicit user request.
5. Superseding a decision preserves the prior record and links both versions.

### Should-Have (P1)

6. Decision records support a concise presentation and expanded history.
7. The archive includes a durable entry for create, reopen, and supersede events.

### Nice-to-Have (P2)

8. System flags repeated reopening without changed evidence during planning.

## User Flow

### Happy Path

1. **Entry point**: A material choice (per the materiality rule above) arises during specification, planning, or execution.
2. **Action**: The system prompts for or detects the decision moment.
3. **Feedback**: System records selected option, why, and alternatives.
4. **Result**: Future output and recovery cite the decision without asking the user to reconstruct it.
5. **Next step**: Work proceeds under the decision.

### Alternate Paths

* **Path B**: New evidence invalidates a decision; system presents reopening reason and creates a superseding revision.
* **Path C**: Minor reversible choice is not logged; system keeps it in local task notes.

## Edge Cases & Error States

### Input Validation

* Missing question or selected option → reject decision creation.
* Missing rationale → require concise why for material decisions.
* Duplicate decision → link to existing record and request explicit supersede if changed.

### System Errors

* Persistence failure → do not claim decision is durable; keep a retryable draft.
* Archive failure → mark archive pending and repair.
* Timeout → retain draft locally.

### Permission & State

* User rejects agent recommendation → record user-selected alternative without framing as error.
* Stale spec context → attach current and prior spec revisions.
* Empty state → show `No recorded decisions for this context.`
* Concurrent updates → preserve both revisions and require resolution only if execution conflict exists.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/decision.py` — decision and reopening model, materiality rule.
* `apps/api/src/coh_api/application/decision_service.py` — create, list, supersede, reopen.
* `apps/api/src/coh_api/application/recovery_service.py` — relevant-decision lookup.
* `apps/api/src/coh_api/infrastructure/repositories/decision_repository.py` — persistence and indexes.
* `packages/archive/src/coh_archive/writer.py` — decision archive events.
* `packages/execution-core/tests/test_decision.py` and `apps/api/tests/test_decision_service.py` — lifecycle tests.

### Data Flow

1. Agent/user submits decision payload.
2. Service validates materiality and required rationale.
3. Store writes immutable decision revision with indexes: projectId, goalId, specId, taskId, status, timestamps; ensure query APIs return latest active decision per context and maintain full revision history.
4. Archive writes corresponding interaction event.
5. Recovery/planning services query relevant latest decisions.

### New Dependencies

None.

## Dependencies & Risks

### Dependencies

* **Upstream**: Spec and task context.
* **Downstream**: Recovery, planning, agent prompts.
* **External**: None.

### Technical Risks

* **Performance**: Context search may grow; index by project, goal, task, and status. Include monitoring (latency, query volume) and paging limits.
* **Security**: Rationales can expose sensitive context. v0.1 is local-first single-profile (Decision D1/D7): records stay project-local with restrictive file permissions and never leave the machine. Access levels (member/viewer/admin) and field-level encryption-at-rest are **future hosted-mode** concerns, out of v0.1 scope.
* **Data integrity**: Never overwrite historical rationale. Add automated integrity checks and version reconciliation tests.

### Rollout Strategy

* **Feature flag**: `decisionLog.enabled`.
* **Staged rollout**: Manual recording, then agent-suggested material decisions.
* **Rollback plan**: Disable suggestions while preserving history.

## Test Plan

### Manual Testing

1. Record a decision and resume later; verify why appears.
2. Reopen due to new evidence and verify original persists.
3. Reject an agent recommendation and verify user choice is retained.

### Automated Tests

* **Unit tests**: Validation and valid reopening conditions.
* **Integration tests**: Recovery lookup and archive append.
* **E2E tests**: Decision during execution through interruption recovery.

### Regression Checks

* Verify minor task notes do not create excessive decision records.
* Verify decisions are not reopened merely for alternatives.
* Check error tracking for persistence failures.
