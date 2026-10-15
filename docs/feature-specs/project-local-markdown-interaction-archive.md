> **COH — Cognitive Operating Harness** · v0.1 feature spec · Updated 2026-08-19 · Python stack (Decision D2) · Companion docs: `COH-PRD.md`, `COH-Technical-Design.md`, `../COH-Decision-Log.md`
> **This spec's degrade-and-continue failure model is canonical** (Decision D6); the PRD has been amended to match (no staging buffer or automatic fallback file in v0.1). Default archive directory is **`.coh/archive/`** (Decision D10).

## Feature Summary

Create a local, append-only Markdown archive that records every user input, agent output, and available tool activity for a project. The archive gives a solo AI-assisted developer a portable, human-readable history that preserves detail for recovery, decision review, and future reference without making Caveman or any one agent a dependency.

### Scope

* **In scope**:
  * Configurable project-local archive directory
  * Append-only Markdown session files for user messages, agent responses, and tool events
  * Capture of timestamps, source/actor, session/project context, execution-state references, and artifact paths
  * Explicit archive-write result returned to callers
  * Graceful handling of missing or unwritable archive directories
  * Checkpoint records that link to the relevant archive file and entry anchors
* **Out of scope**:
  * Cloud sync, collaboration, encryption-at-rest, or remote backups
  * A visual archive browser
  * Full-text search/indexing
  * Redaction of sensitive content beyond a documented warning and an opt-out configuration
  * Retroactive ingestion of existing chat histories
  * Agent-specific adapters beyond the canonical archive API
* **Prerequisites**:
  * COH Python monorepo with project-root resolution and configuration loading
  * Execution-state/checkpoint service (or checkpoint interface) that accepts archive references
* **Depends on**:
  * Python stdlib filesystem access (`pathlib`, `os`)
  * Pydantic v2 for runtime validation
  * Existing structured logging utility

## Acceptance Criteria

### Must-Have (P0)

1. When an archive-enabled project receives a user input, the system appends a Markdown entry to the configured archive directory before returning control to the workflow, including an ISO 8601 timestamp, entry ID, actor `user`, session ID, project ID, and the complete unmodified message body.

Example Markdown entry:

---

id: user-2026-08-18T12:34:56.789Z-abcd1234 actor: user time: 2026-08-18T12:34:56.789Z session_id: 01234567-89ab-cdef-0123-456789abcdef project_id: my-project

```text
Fix the failing authentication test.

```

---

2. When the agent produces a response, the system appends a separate Markdown entry with actor `agent`, timestamp, session/project IDs, complete unmodified response body, and any supplied execution-state metadata such as goal ID, task ID, state transition, or checkpoint ID.
3. When the adapter supplies tool activity, the system records a tool entry containing tool name, invocation timestamp, result timestamp when available, status (`started`, `succeeded`, or `failed`), sanitized input/output payloads, and references to any output artifacts. The archive service must not invent tool events when an adapter cannot provide them.
4. The archive directory is configurable by project configuration. If omitted, the system uses `.coh/archive/` relative to the project root and creates it recursively on first write.
5. The archive creates one Markdown file per session named `YYYY-MM-DD--.md`. Repeated writes for the same session append in chronological order; a new session creates a new file.
6. Each archive file begins with YAML front matter containing schema version, project ID, session ID, created timestamp, and last-updated timestamp. Each entry has a stable Markdown anchor-compatible ID so checkpoints can reference it.
7. A checkpoint created after an archived event persists the archive file path and latest relevant entry ID. Recovery can use those references to locate the detailed interaction history.
8. Archive failures do not discard or alter the user/agent message in memory. The system returns a structured `archive_write_failed` result, logs the failure with a safe diagnostic, marks the current checkpoint/archive status as degraded, and presents a non-blocking warning that the detailed local record was not saved.
9. The system rejects archive paths that resolve outside the project root unless an explicit `allow_external_archive_path` configuration flag is true.
10. The archive service writes atomically enough to prevent a partial entry from being treated as complete after process interruption: write the entry to a temporary file or buffer, append/rename safely, and include a final entry delimiter only after the entry body is fully written.
11. Entries preserve detail rather than relying on generated summaries. Optional summaries may be stored as metadata, but they must not replace the original message or output body.
12. The archive format remains readable in a standard Markdown editor with no product UI required.

### Should-Have (P1)

1. The archive rotates to a new file when a session file exceeds 5 MB, using `YYYY-MM-DD----part-N.md`, and checkpoint references identify the correct part.
2. Configuration supports `archive.enabled: false`; when disabled, no archive directories or files are created and callers receive a successful `skipped_disabled` result.
3. Tool payload formatting truncates individual inline payloads above a configurable limit and writes the complete payload to a sibling artifact file, with a Markdown link from the event entry.
4. The archive exposes a `readSessionArchive()` helper that returns parsed front matter and entries for recovery and future UI use.

### Nice-to-Have (P2)

1. Add a compact session index file containing session date, IDs, title/goal, final status, and archive file path.
2. Add a user-configurable warning banner when content appears likely to contain credentials, without attempting automatic redaction.

## User Flow

### Happy Path

1. **Entry point**: A supported agent adapter starts or resumes a project session and loads archive configuration.
2. **Action**: The user submits a request such as “Fix the failing authentication test.”
3. **Feedback**: The adapter calls `archiveInteraction()` with a `user` event. The archive directory is created if it does not exist, and the session Markdown file is created or appended.
4. **Result**: The agent response and any available tool events are recorded as separate, chronologically ordered entries in the same session archive. The active checkpoint stores the latest archive pointer.
5. **Next step**: If the session is interrupted, recovery reads the checkpoint pointer and can link the user to the complete session record.

### Alternate Paths

* **Path B — custom archive folder**: The project configuration sets `archive.directory` to a relative path such as `.agent-history/`. The resolver validates it remains under the project root, creates it on first write, and uses it for all session files.
* **Path C — archive disabled**: The configuration sets `archive.enabled` to `false`. The adapter continues its normal workflow and receives `skipped_disabled`; no filesystem write is attempted.
* **Path D — tool output is large**: The adapter passes output above the inline limit. The archive stores a concise event entry and writes the full payload to an artifact file beside the session archive.
* **Path E — write failure**: A permissions or disk error occurs. The current interaction continues, the system surfaces an archive-degraded warning, and the next successful write retries normal archival without rewriting prior entries.

## Edge Cases & Error States

### Input Validation

* Empty session ID, project ID, actor, or event body → reject with a typed validation error before any file operation.
* Invalid archive directory type or empty directory string → use the default directory and emit a configuration warning.
* Absolute archive path outside project root while `allow_external_archive_path` is false → reject configuration with `ARCHIVE_PATH_OUTSIDE_PROJECT` and do not write.
* Event payload exceeds configured maximum artifact size → store an event status noting truncation, preserve the available metadata, and return a `payload_too_large` warning.

### System Errors

* Network failure → not applicable; archive is local-first and must not require network access.
* Filesystem permission failure → return `archive_write_failed`, log the resolved target path and OS error code without logging message body, retain in-memory workflow state, and mark checkpoint archival status `degraded`.
* Disk full or I/O error → same behavior as permission failure; do not report the task itself as failed solely because archival failed.
* Process interruption during write → write entries to a temporary file and atomically rename/append only after completion; recovery ignores incomplete entries that lack the closing delimiter and leaves previous valid entries readable.
* Concurrent writes to one session file → serialize writes through a per-session async queue; preserve call order and prevent interleaved Markdown.

### Permission & State

* Unauthorized access → if the runtime user cannot create or write the configured folder, show the archive-degraded warning and provide the resolved path in diagnostics.
* Stale data / concurrent edit → archive files are append-only. Never overwrite an existing entry; create a new event indicating any corrected or superseding state.
* Empty state (no data yet) → a new session file contains valid front matter and no event entries until the first interaction is recorded.
* Rate limited → not applicable. Internal queue backpressure may return `queued` while preserving write order.
* Sensitive data → show documentation and configuration copy that the archive stores raw conversation content locally. Do not claim automatic secret redaction in v1.

## Technical Approach

### Files to Create/Modify

* `packages/archive/src/coh_archive/models.py` — Pydantic schemas for archive configuration, archive events, write results, and archive pointers.
* `packages/archive/src/coh_archive/paths.py` — project-root path resolution, default directory (`.coh/archive/`), external-path enforcement, safe filename generation.
* `packages/archive/src/coh_archive/markdown.py` — append-only Markdown formatting, front-matter creation/update, atomic write handling, rotation, artifact writing, per-session write serialization.
* `packages/archive/src/coh_archive/service.py` — public `archive_interaction()`, `archive_tool_event()`, and `read_session_archive()` service API.
* `tests/packages/archive/test_markdown.py` — unit tests for format, append order, rotation, atomic/incomplete-entry behavior, payload artifacts.
* `tests/packages/archive/test_paths.py` — unit tests for default path, relative custom path, traversal rejection, permitted external path behavior.
* `packages/execution-core/src/execution_core/domain/checkpoint.py` — extend checkpoint state with `archive_status`, `archive_ref`, and `archive_refs` when a checkpoint spans rotated archive files.
* `apps/api/src/coh_api/application/checkpoint_service.py` — accept and persist the latest archive pointer without making checkpoint success dependent on archive success.
* `apps/api/src/coh_api/infrastructure/config.py` — add and validate the `archive` configuration block and defaults.
* `packages/agent-runtime/src/agent_runtime/adapter.py` — optional normalized interaction and tool-event hooks that adapters call; no vendor-specific types in the archive core.
* `packages/mcp-server/src/coh_mcp/session_lifecycle.py` — call the archive service for user inputs, agent outputs, and available tool lifecycle events.
* `docs/configuration.md` — document archive location, enabled/disabled behavior, external path opt-in, raw-content privacy warning, and artifact files.

### Data Flow

1. Adapter receives a user message, agent output, or supported tool lifecycle event.
2. Adapter normalizes it to `ArchiveEvent` and calls `archive_interaction()` or `archive_tool_event()`.
3. The archive service validates the event and loads validated project archive configuration.
4. Path resolution determines the project-local archive folder and session file; it validates the resolved path boundary.
5. The Markdown formatter creates front matter on first write and formats a stable event section with metadata, full content, and optional artifact links.
6. The writer serializes writes for the session, persists any large payload artifact, then safely appends the completed event.
7. The service returns `ArchiveWriteResult` with `written`, `queued`, `skipped_disabled`, or `archive_write_failed`, plus an `ArchivePointer` on success.
8. Checkpoint creation or update stores the latest successful pointer and sets archive status to `healthy` or `degraded`.
9. Recovery reads the checkpoint pointer, calls `read_session_archive()` when detailed history is needed, and renders a link/path to the relevant entry.

#### Entry Schema and Anchor Rules (exact)

* Entry anchor (ID): `{actor}-{ISO8601}-{4char-hash}`
* YAML metadata block per entry: `id`, `actor`, `time`, `session_id`, `project_id`, `tool_name?`, `status?`, `artifact_paths?`
* Body fenced as ` ```text ` for raw content
* Closing delimiter on its own line: `---entry-end---` (written only after the entry body is fully flushed; readers ignore trailing entries that lack it)

Example event section:

```markdown
### id: user-2026-08-19T12:34:56.789Z-abcd

​```yaml
actor: user
time: 2026-08-19T12:34:56.789Z
session_id: 01234567-89ab-cdef-0123-456789abcdef
project_id: my-project
​```

​```text
Fix the failing authentication test.
​```

---entry-end---
```

### New Dependencies

* No new production package is required beyond the approved baseline: Python stdlib (`pathlib`, `os`, `tempfile`) and Pydantic v2.
* Add `python-frontmatter` (or use `PyYAML`, already transitively available) only if hand-writing the YAML front-matter read/write path would create avoidable risk. Requires approval per the Coding Rules dependency policy.

## Dependencies & Risks

### Dependencies

* **Upstream**: Project-root discovery, configuration loading, session IDs, checkpoint service, and agent adapter lifecycle hooks.
* **Downstream**: Interruption recovery, decision/context review, future visual archive browser, audit/export workflows, and any full-text search feature.
* **External**: Local filesystem only. No cloud service is required.

### Technical Risks

* **Performance**: Long agent sessions and verbose tool output can generate large files. Use append-only writes, configurable inline payload limits, artifacts for oversized payloads, and 5 MB rotation. Expected v1 volume is one active user/session, so per-session write queues are sufficient.
* **Security**: Raw archived content can contain secrets, proprietary code, or personal data. Keep archive project-local by default, require explicit opt-in for external paths, document the risk, and do not send archive content to remote services.
* **Data integrity**: Process termination and concurrent callbacks can corrupt append-only files. Use a per-session queue, safe write/rename strategy, closing delimiters, and tolerant reads that ignore incomplete trailing entries.
* **Compatibility**: Agent tools expose different event detail. The normalized event schema must support partial tool metadata and clearly distinguish unavailable detail from empty detail.

### Rollout Strategy

* **Feature flag**: Use `archive.enabled`, default `true` for new local projects and configurable per project.
* **Staged rollout**: Internal/solo workflow → pilot with a second supported adapter → general availability after recovery and corruption tests pass.
* **Rollback plan**: Set `archive.enabled: false`; preserve existing Markdown files untouched. If a format bug occurs, increment schema version for new files and keep the reader backward-compatible.

## Test Plan

### Manual Testing

Step-by-step QA checklist:

1. Start a new project session, send a user request, receive an agent response, and verify a session Markdown file contains complete, chronological user and agent entries with front matter.
2. Configure a custom relative archive folder and verify files are written only under that project-root location.
3. Attempt an external or traversal archive path with external paths disabled and verify configuration is rejected without a write.
4. Generate a tool event with a large output and verify the Markdown event links to a complete sibling artifact file.
5. Interrupt a write process or simulate an incomplete trailing entry; verify prior entries remain readable and recovery ignores the incomplete entry.
6. Make the archive directory unwritable; verify the workflow continues, a non-blocking degraded warning appears, diagnostics omit content, and the checkpoint records degraded archive status.
7. Create a checkpoint after a successful event and verify it stores the archive file and entry ID; use recovery to locate the detailed event.
8. Set `archive.enabled: false` and verify no directory or files are created.
9. Force session content past 5 MB and verify rotation preserves chronological references and checkpoint pointers.

### Automated Tests

* **Unit tests**: Configuration and path validation; schema validation; event-to-Markdown formatting; front matter; stable entry IDs; append ordering; file rotation; large payload artifacts; incomplete trailing entry handling; write-result error mapping.
* **Integration tests**: Adapter lifecycle to archive service to filesystem; checkpoint linkage after successful and failed writes; disabled archive flow; per-session concurrent write serialization.
* **E2E tests**: Start a session through a supported local adapter, create user/agent/tool records, interrupt and recover, and verify the recovery experience links to the correct archived record.

### Regression Checks

* Verify normal agent execution continues when archiving is disabled or fails.
* Verify checkpoints still save when the archive is degraded.
* Verify task interruption records, NOW + NEXT 2 foreground, decision rationale, and parking items remain unchanged.
* Check local logs/error tracking for archive I/O errors after deploy.
