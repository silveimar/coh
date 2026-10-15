> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`
> Canonical field name is `restart_action` (Decision D10); "Start Here" is UI copy only. The progress-record shape is defined once in COH-PRD.md → Interruption-Safe Progress Records.

## Feature Summary

Persist a recoverable record whenever an unfinished task is interrupted, so a user can resume with the last known status, blockers, evidence, and one literal `restart_action`. This supports solo AI-assisted developers who lose working context across interruptions.

### Scope

* **In scope**: Create/update interruption records; render recovery summaries; link recovery records to the interaction archive.
* **Out of scope**: Visual recovery screen, timers, automatic inference of task completion.
* **Prerequisites**: Project-local execution state and Markdown interaction archive.
* **Depends on**: Task, checkpoint, decision, evidence, and archive-reference interfaces.

## Acceptance Criteria

### Must-Have (P0)

1. When an unfinished task is paused, interrupted, or superseded, the system persists a recovery record before switching foreground work.
2. A recovery record includes task identity, goal, last known status, completed or attempted work, blockers, decisions with rationale, evidence references, parked-item references, and one exact restart action.
3. Resuming a task returns a structured summary containing Goal, Why, Last Verified, Last Decision, Now, Next 2, Parked count, and Start Here.
4. Recovery records reference relevant archive entries and state changes using stable identifiers.
5. If a required recovery write fails, the system reports the failure and blocks a foreground switch unless the user explicitly overrides.

### Should-Have (P1)

6. The system creates checkpoints at task transitions, major decisions, verification results, and explicit session stop.
7. A new recovery record supersedes prior records without deleting history.

### Nice-to-Have (P2)

8. The system detects inactivity from an adapter and suggests a checkpoint without creating one silently.

## User Flow

### Happy Path

1. **Entry point**: User is executing an unfinished task with current status and next steps.
2. **Action**: User says to pause, starts another task, or the adapter emits an interruption event.
3. **Feedback**: System writes a checkpoint and confirms the saved restart action.
4. **Result**: User later requests resume and sees the concise recovery summary.
5. **Next step**: User starts the literal restart action or selects another preserved next step.

### Alternate Paths

* **Path B**: If no active task exists, show no-resumable-work state and link to the latest completed session.
* **Path C**: If the user intentionally abandons work, retain the checkpoint and mark the task abandoned; do not present it as active.

## Edge Cases & Error States

### Input Validation

* Missing task ID → reject checkpoint creation with `Cannot checkpoint: no active task.`
* Empty restart action → derive one from the current task only if unambiguous; otherwise request one.
* Restart action longer than configured limit → require a concise imperative action and retain detail in notes.

### System Errors

* Archive or state write failure → show `Recovery record was not saved`, retain in-memory payload, and offer retry/export.
* Partial write → mark record incomplete, do not mark the checkpoint durable, and retry idempotently.
* Timeout → preserve local draft and show retry action.

### Permission & State

* Unauthorized project path → do not write; report configured path and required access.
* Concurrent checkpoint update → append a new revision and identify the latest revision.
* Empty state → show `No interrupted task is available to resume.`
* Rate limited → queue noncritical checkpoint suggestions; explicit pause still requires durable write.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/recovery.py` — recovery record, checkpoint reason, validation; TaskProgressRecord revisions.
* `apps/api/src/coh_api/application/recovery_service.py` — create, revise, list, resume operations.
* `apps/api/src/coh_api/infrastructure/repositories/checkpoint_repository.py` — persistence updates.
* `packages/archive/src/coh_archive/writer.py` — archive links for checkpoints.
* `packages/agent-runtime/src/agent_runtime/adapter.py` — interruption and resume events.
* `tests/packages/execution-core/test_recovery.py` and `tests/apps/api/test_recovery_service.py` — unit and integration coverage.

### Data Flow

1. Adapter or user emits pause, interruption, task switch, or resume request.
2. Recovery service loads active task and related state.
3. Service validates required recovery fields and writes an immutable revision through the state store.
4. Archive writer records the checkpoint event and returns an archive reference.
5. State store commits the archive reference and recovery record.
6. Resume request reads the latest durable revision and formats the recovery summary.

### New Dependencies

No new runtime dependencies required. Use existing filesystem, serialization, and test utilities; add a lock/atomic-write utility only if absent.

## Dependencies & Risks

### Dependencies

* **Upstream**: Execution state store, task foreground, interaction archive.
* **Downstream**: Recovery UI, visual app, drift/detour behavior.
* **External**: Local filesystem permissions.

### Technical Risks

* **Performance**: Frequent checkpoints may cause write churn; use event-driven writes and small records.
* **Security**: Records can contain sensitive project context; keep storage local and respect configured paths.
* **Data integrity**: A crash between archive and state writes can create dangling references; use durable ordering and repair on read.

### Rollout Strategy

* **Feature flag**: `recoveryRecords.enabled`, default on for new projects.
* **Staged rollout**: Manual checkpoints first, then automatic event-driven checkpoints.
* **Rollback plan**: Disable automatic creation while leaving existing records readable.

## Test Plan

### Manual Testing

1. Pause an active task and confirm all resume fields persist after restart.
2. Switch tasks and confirm the previous task has a restart action.
3. Simulate a write failure and confirm task switch is blocked or explicitly overridden.

### Automated Tests

* **Unit tests**: Field validation, restart-action rules, revision selection.
* **Integration tests**: Atomic state/archive persistence and repair of partial writes.
* **E2E tests**: Execute, interrupt, restart process, and resume from the latest checkpoint.

### Regression Checks

* Verify archive entries remain append-only.
* Verify completed tasks are not presented as interrupted work.
* Check error tracking for checkpoint persistence failures.
