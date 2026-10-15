# COH Archive — Append-only Markdown Interaction Recording

**Phase 1 deliverable** · 2026-09-03

Implements I-04 (append-only archive) and I-12 (degrade-and-continue) from the Behavioral Contract.

## Purpose

The archive package provides a local-first, human-readable Markdown record of every user input, agent output, and tool event in a COH session. Archive write failures never block the workflow; they degrade gracefully and allow the checkpoint to record degraded status for later recovery visibility.

## Features

- **Append-only semantics (I-04)**: Entries never overwrite; corrections are new entries
- **Degrade-and-continue (I-12)**: Write failures return `archive_write_failed` result, mark checkpoint `archive_status` degraded, preserve in-memory data, non-blocking
- **Stable entry IDs**: Each entry has a markdown-anchor-compatible ID for checkpoint references
- **Per-session files**: One `.md` file per session with YAML front matter
- **Rotation**: Files rotate to `-part-N.md` when exceeding 5 MB
- **Artifact spill**: Large tool payloads (>100 KB) write to separate JSON files
- **Path validation**: Archive directory must be under project root unless `allow_external_path=true`
- **Async writes**: Per-session locks serialize concurrent writes

## Usage

```python
from pathlib import Path
from datetime import UTC, datetime
from uuid import uuid4
from coh_archive import (
    ArchiveService,
    ArchiveConfig,
    ArchiveEvent,
    Actor,
    WriteOutcome,
)

# Initialize
project_root = Path("/path/to/project")
config = ArchiveConfig(
    enabled=True,
    directory=".coh/archive",  # relative to project_root
)
service = ArchiveService(project_root, config)

# Archive user input
event = ArchiveEvent(
    actor=Actor.USER,
    time=datetime.now(UTC),
    session_id=uuid4(),
    project_id="my-project",
    content="Fix the authentication test",
)

result = await service.archive_interaction(event)

if result.outcome == WriteOutcome.WRITTEN:
    # Success: pointer available for checkpoint
    pointer = result.pointer
    print(f"Archived: {pointer.path} #{pointer.entry_id}")
elif result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
    # I-12: degraded, non-blocking; mark checkpoint
    print(f"Archive degraded: {result.error}")
    # checkpoint.mark_degraded() happens at checkpoint layer
elif result.outcome == WriteOutcome.SKIPPED_DISABLED:
    # Archive disabled in config
    pass
```

## Archive Format

### Session file

**Filename:** `YYYY-MM-DD-<session_id_short>.md` (or `-part-N.md` for rotations)

**Front matter:**

```yaml
---
schema_version: 1.0.0
session_id: 01234567-89ab-cdef-0123-456789abcdef
project_id: my-project
created_at: 2026-08-19T12:34:56.789000+00:00
last_updated_at: 2026-08-19T12:35:10.000000+00:00
---
```

**Entry:**

```markdown
### user-2026-08-19T12:34:56.789000+00:00-abcd

​```yaml
id: user-2026-08-19T12:34:56.789000+00:00-abcd
actor: user
time: 2026-08-19T12:34:56.789000+00:00
session_id: 01234567-89ab-cdef-0123-456789abcdef
project_id: my-project
​```

​```text
Fix the authentication test
​```

---entry-end---
```

The `---entry-end---` delimiter enables incomplete-entry detection after process interruption.

## Configuration

```python
ArchiveConfig(
    enabled=True,  # False to disable archiving
    directory=".coh/archive",  # Relative or absolute path
    allow_external_path=False,  # Reject paths outside project root
    max_inline_payload_bytes=102400,  # 100 KB; larger spills to artifact
    rotation_threshold_bytes=5242880,  # 5 MB; trigger rotation
)
```

## Trade-offs

### Chosen

- **Markdown over JSON**: Human-readable without tooling; grep-friendly; standard editor support
- **Per-session files**: Natural archive unit; session-scoped rotation and lock granularity
- **Append-only**: Simple, auditable, no edit complexity; corrections are explicit new entries
- **Atomic writes via temp+rename**: Process interruption leaves prior entries intact
- **Degrade-and-continue**: Never blocks workflow; degraded status visible in recovery

### Rejected for v0.1

- **Staging buffer**: Would hide silent-loss risk on crash; requires separate failure-path testing
- **Automatic fallback file**: Unclear recovery semantics; better to degrade honestly and surface the issue
- **Remote sync**: Local-first principle; cloud sync is Phase 3+
- **Full-text search**: Out of scope; can be added later without format changes
- **Encryption at rest**: User data; local filesystem security model applies

## Integration with Execution Core

The archive package has **no import dependency** on execution-core or persistence. It provides models and a service; the checkpoint layer consumes `ArchivePointer` and converts it to `ArchiveReference` for storage.

**Port pattern:**

```python
# execution-core checkpoint.py already has:
class ArchiveReference(BaseModel):
    path: str
    timestamp: datetime
    anchor: str


# Archive service returns ArchivePointer (same shape):
class ArchivePointer(BaseModel):
    path: str
    entry_id: str  # == anchor
    timestamp: datetime


# Checkpoint layer adapts:
if result.outcome == WriteOutcome.WRITTEN:
    archive_ref = ArchiveReference(
        path=result.pointer.path,
        timestamp=result.pointer.timestamp,
        anchor=result.pointer.entry_id,
    )
    checkpoint.archive_references.append(archive_ref)
elif result.outcome == WriteOutcome.ARCHIVE_WRITE_FAILED:
    checkpoint.mark_degraded()
```

## Testing

- `test_paths.py`: Path resolution, validation, filename/ID generation
- `test_markdown.py`: Formatting, append order, rotation, artifacts, concurrency
- `test_service.py`: Service API, degrade-and-continue, disabled config, lazy init
- `test_integration.py`: End-to-end workflows, checkpoint integration, I-04/I-12 scenarios

**Run tests:**

```bash
uv run pytest tests/packages/archive -v
```

**Coverage:**

```bash
uv run pytest tests/packages/archive --cov=coh_archive --cov-report=term-missing
```

## Next Actions

1. **Adapter integration**: MCP server calls `archive_interaction()` on user/agent messages, `archive_tool_event()` on tool lifecycle
2. **Checkpoint wiring**: Checkpoint service adapts `ArchivePointer` → `ArchiveReference`, calls `mark_degraded()` on write failure
3. **Recovery rendering**: Recovery summary reads `checkpoint.archive_references` and can call `service.read_session_archive()` for detail
4. **Configuration loading**: API layer loads `ArchiveConfig` from project config YAML/TOML
5. **Telemetry events**: Emit `archive_recorded` (success) and `archive_write_failed` (degraded) per Decision D10

## Out of Scope (for now)

- Visual archive browser (Phase 3)
- Full-text search/indexing
- Redaction/secret detection (warning + opt-out config only)
- Retroactive ingestion of existing chat histories
- Cloud sync/collaboration
- Encryption at rest
