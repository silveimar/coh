> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`
> **Storage decision:** the store is defined as a port; **SQLite (WAL) via SQLAlchemy 2 + Alembic is the chosen v0.1 implementation** (Decision D2, per COH-Technical-Design.md). The port abstraction remains so PostgreSQL can replace SQLite as an infrastructure migration.

## Feature Summary

Create the canonical project-local state store for goals, specifications, tasks, foreground, decisions, checkpoints, parking items, evidence, sessions, and archive references. It enables local-first continuity and future visual surfaces without treating Markdown summaries as the only source of truth.

### Scope

* **In scope**: Storage interfaces, entity schemas, revisions, atomic persistence, queries, archive references, and portability/export hooks.
* **Out of scope**: Final database selection, cloud synchronization, visual app, full migration tooling.
* **Prerequisites**: Project root/configuration resolution.
* **Depends on**: Interaction archive and all execution domain services.

## Acceptance Criteria

### Must-Have (P0)

1. Store supports UserProfile, Project, Goal, Specification, Session, Task, Decision, Checkpoint, ParkingItem, Evidence, DriftEvent, Foreground, and archive-reference records.
2. Every mutable record has stable ID, timestamps, revision/version metadata, and project scope.
3. Store supports atomic or recoverable writes so a crash cannot silently produce an inconsistent active task, checkpoint, and archive reference state.
4. Store exposes queries for active goal, active foreground, latest checkpoint, resumable task, task dependencies, relevant decisions, parked items, and evidence by criterion.
5. Store is local-first and uses a configurable project-local data location with portable export capability.
6. State changes emit archive events or durable pending-archive markers; no state change is treated as fully durable until its required persistence policy is met.

### Should-Have (P1)

7. Store supports append-only history for decisions, evidence, checkpoints, and state transitions.
8. Read operations repair or flag recoverable partial writes.

### Nice-to-Have (P2)

9. Store supports snapshot export for a future visual app and diagnostic bundle.

## User Flow

### Happy Path

1. **Entry point**: Core service creates or updates execution state.
2. **Action**: Service writes a validated revision through the state store.
3. **Feedback**: Write returns durable record ID/revision and archive correlation state.
4. **Result**: Later services query the same project-local state for foreground and recovery.
5. **Next step**: User resumes work or exports portable project context.

### Alternate Paths

* **Path B**: Store detects recoverable partial transaction and repairs/flags it before serving active state.
* **Path C**: Configured path is unavailable; system reports error and does not silently fall back to an unknown location.

## Edge Cases & Error States

### Input Validation

* Missing project scope → reject write.
* Invalid entity relationship → reject with relationship-specific error.
* Revision conflict → return conflict result with latest revision reference.

### System Errors

* Disk full/write failure → preserve operation draft, report durable-write failure, and block operations requiring persistence.
* Corrupt state record → quarantine record, retain raw bytes, and report recovery guidance.
* Timeout/lock contention → retry boundedly, then return retryable error.

### Permission & State

* Read-only project filesystem → allow reads; reject writes clearly.
* Concurrent process → use file/transaction lock or compare-and-swap semantics.
* Empty project → initialize only explicit project metadata; do not invent tasks.
* Rate limited external service → irrelevant; state store remains local.

## Technical Approach

### Files to Create/Modify

* `packages/execution-core/src/execution_core/domain/entities.py` — canonical entity types and IDs (per COH-Technical-Design.md data model).
* `apps/api/src/coh_api/application/ports/state_store.py` — storage port (protocol) and query API.
* `apps/api/src/coh_api/infrastructure/repositories/` — SQLAlchemy repository implementations (SQLite/WAL).
* `apps/api/src/coh_api/infrastructure/unit_of_work.py` — atomic/recoverable write coordinator (transaction + archive correlation).
* `apps/api/src/coh_api/application/exporter.py` — portable snapshot/export.
* `apps/api/src/coh_api/infrastructure/project_paths.py` — configurable data location.
* `migrations/` — Alembic revisions for every schema change.
* `apps/api/tests/test_state_store.py` — persistence and recovery tests (incl. mid-write crash repair).

### Data Flow

1. Domain service validates mutation.
2. Transaction coordinator stages entity revision and archive correlation/pending marker.
3. Local store commits durable state.
4. Archive writer completes correlated append or leaves repairable pending state.
5. Query API serves latest valid revisions to services/adapters.

### New Dependencies

SQLAlchemy 2, Alembic, and SQLite (stdlib driver) per Decision D2 — already part of the approved baseline; no additional packages.

## Dependencies & Risks

### Dependencies

* **Upstream**: Project configuration.
* **Downstream**: Every execution feature, future visual app.
* **External**: Local filesystem.

### Technical Risks

* **Performance**: Revision history can grow; design indexes/compaction without deleting required archive history.
* **Security**: Local records contain sensitive code/work context; use restrictive default permissions.
* **Data integrity**: This is the canonical state layer; prioritize atomicity, auditability, and repairability.

### Rollout Strategy

* **Feature flag**: `executionStateStore.enabled` only for migration/testing.
* **Staged rollout**: Reference implementation with archive, then migrate individual feature services.
* **Rollback plan**: Keep prior state readable and exportable; never destructive-migrate without backup.

## Test Plan

### Manual Testing

1. Create goal, task, checkpoint, and archive reference; restart process and query all.
2. Simulate mid-write crash and verify repair/flag behavior.
3. Configure unwritable path and verify explicit failure.

### Automated Tests

* **Unit tests**: Schema, relationship, revision validation.
* **Integration tests**: Atomic write/recovery and concurrent writers.
* **E2E tests**: Spec through recovery using persisted state.

### Regression Checks

* Verify archive-only feature remains readable.
* Verify state path configuration does not redirect silently.
* Check error tracking for corruption and write failures.
