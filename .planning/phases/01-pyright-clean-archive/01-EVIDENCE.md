# Phase 01 evidence (H-87)

Measured base: `origin/main` e450c04 (the PLAN names 576ee9e; commits since 576ee9e touch only `.planning`). Starting HEAD: 890e9fa (the PLAN commit). `__SCRATCHPAD__` stands for the session scratchpad directory, outside the repository; the real path is not recorded here.

## Baseline (origin/main e450c04, before edits)

A1. `git -C <worktree> rev-parse --short origin/main HEAD` as written in the PLAN fails, because `--short` accepts one revision:

```text
fatal: Needed a single revision
```

Run as two commands instead:

`git -C <worktree> rev-parse --short origin/main`

```text
e450c04
```

`git -C <worktree> rev-parse --short HEAD`

```text
890e9fa
```

A2. `git -C <worktree> diff --name-only origin/main...HEAD -- . ':!.planning'`

```text
```

(empty: no change outside `.planning` before the edits)

A3. `uv run pyright --outputjson packages/archive | jq -r '.generalDiagnostics[] | "\(.file | split("/") | last):\(.range.start.line + 1) \(.rule)"'`

```text
markdown.py:222 reportUnusedVariable
markdown.py:305 reportUnusedVariable
service.py:138 reportUnusedVariable
service.py:189 reportUnknownParameterType
service.py:189 reportMissingTypeArgument
```

A4. `uv run pyright --outputjson | jq '.summary.errorCount'`

```text
648
```

A5. `uv run pytest tests/packages/archive -q`

```text
.................................                                        [100%]
33 passed in 0.09s
```

A6. `uv run pytest tests/packages/mcp_adapter/test_archive_wiring.py -q`

```text
......                                                                   [100%]
6 passed in 0.37s
```

A7. Command E1:

```text
uv run python -c 'import asyncio, hashlib, tempfile; from datetime import datetime, UTC; from pathlib import Path; from uuid import UUID; from coh_archive import Actor, ArchiveConfig, ArchiveEvent, ArchiveService, EventStatus, ToolEvent; root = Path(tempfile.mkdtemp(dir="__SCRATCHPAD__")); svc = ArchiveService(root, ArchiveConfig(max_inline_payload_bytes=64)); sid = UUID("00000000-0000-4000-8000-000000000001"); t = datetime(2026, 1, 1, 12, 0, tzinfo=UTC); loop = asyncio.new_event_loop(); r1 = loop.run_until_complete(svc.archive_interaction(ArchiveEvent(actor=Actor.USER, time=t, session_id=sid, project_id="synthetic-project", content="synthetic user input"))); r2 = loop.run_until_complete(svc.archive_tool_event(ToolEvent(time=t, session_id=sid, project_id="synthetic-project", tool_name="synthetic_tool", status=EventStatus.SUCCEEDED, invocation_time=t, result_time=t, input_payload={"q": "small"}, output_payload={"rows": ["x" * 40, "y" * 40]}))); f = root / r1.pointer.path; fm, entries = svc.read_session_archive(f); print("interaction:", r1.outcome.value, r1.pointer.path, r1.pointer.entry_id); print("tool_event:", r2.outcome.value, r2.pointer.path, r2.pointer.entry_id); print("archive_files:", sorted(p.name for p in f.parent.iterdir())); print("front_matter:", fm); print("entries:", len(entries)); print("session_sha256:", hashlib.sha256(f.read_bytes()).hexdigest()); print("----- session file -----"); print(f.read_text(encoding="utf-8"))'
```

````text
interaction: written .coh/archive/2026-01-01-00000000.md user-2026-01-01T12:00:00+00:00-a4fa
tool_event: written .coh/archive/2026-01-01-00000000.md tool-2026-01-01T12:00:00+00:00-97ac
archive_files: ['2026-01-01-00000000.md', 'tool-2026-01-01T12:00:00+00:00-97ac-output.json']
front_matter: {'schema_version': '1.0.0', 'session_id': '00000000-0000-4000-8000-000000000001', 'project_id': 'synthetic-project', 'created_at': '2026-01-01T12:00:00+00:00', 'last_updated_at': '2026-01-01T12:00:00+00:00'}
entries: 2
session_sha256: 12bccf8e93452ce499182021d2c181f2fb9363b0d9469c5fbd3393c6c20fcc91
----- session file -----
---
schema_version: 1.0.0
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
created_at: '2026-01-01T12:00:00+00:00'
last_updated_at: '2026-01-01T12:00:00+00:00'
---

### user-2026-01-01T12:00:00+00:00-a4fa

```yaml
id: user-2026-01-01T12:00:00+00:00-a4fa
actor: user
time: '2026-01-01T12:00:00+00:00'
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
```

```text
synthetic user input
```

---entry-end---

### tool-2026-01-01T12:00:00+00:00-97ac

```yaml
id: tool-2026-01-01T12:00:00+00:00-97ac
actor: tool
time: '2026-01-01T12:00:00+00:00'
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
tool_name: synthetic_tool
status: succeeded
invocation_time: '2026-01-01T12:00:00+00:00'
result_time: '2026-01-01T12:00:00+00:00'
artifact_paths:
- tool-2026-01-01T12:00:00+00:00-97ac-output.json
```

**Input:**
```json
{
  "q": "small"
}
```


---entry-end---
````

Precondition (Task 1 step B): 5 diagnostics at the 4 CONTEXT locations, matching the PLAN table. N_main = 648; archive suite 33 passed; wiring suite 6 passed. Proceed.

Task 1 checkpoint (after the `_write_event_sync` edit only): archive pyright errorCount 4; both suites `39 passed`; `ruff format --check packages/archive` printed `6 files already formatted`.

## After (code commit 0e37a94)

1. `git -C <worktree> rev-parse --short HEAD`

```text
0e37a94
```

2. Command E1 (same command as the baseline, `__SCRATCHPAD__` substituted at run time):

````text
interaction: written .coh/archive/2026-01-01-00000000.md user-2026-01-01T12:00:00+00:00-a4fa
tool_event: written .coh/archive/2026-01-01-00000000.md tool-2026-01-01T12:00:00+00:00-97ac
archive_files: ['2026-01-01-00000000.md', 'tool-2026-01-01T12:00:00+00:00-97ac-output.json']
front_matter: {'schema_version': '1.0.0', 'session_id': '00000000-0000-4000-8000-000000000001', 'project_id': 'synthetic-project', 'created_at': '2026-01-01T12:00:00+00:00', 'last_updated_at': '2026-01-01T12:00:00+00:00'}
entries: 2
session_sha256: 12bccf8e93452ce499182021d2c181f2fb9363b0d9469c5fbd3393c6c20fcc91
----- session file -----
---
schema_version: 1.0.0
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
created_at: '2026-01-01T12:00:00+00:00'
last_updated_at: '2026-01-01T12:00:00+00:00'
---

### user-2026-01-01T12:00:00+00:00-a4fa

```yaml
id: user-2026-01-01T12:00:00+00:00-a4fa
actor: user
time: '2026-01-01T12:00:00+00:00'
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
```

```text
synthetic user input
```

---entry-end---

### tool-2026-01-01T12:00:00+00:00-97ac

```yaml
id: tool-2026-01-01T12:00:00+00:00-97ac
actor: tool
time: '2026-01-01T12:00:00+00:00'
session_id: 00000000-0000-4000-8000-000000000001
project_id: synthetic-project
tool_name: synthetic_tool
status: succeeded
invocation_time: '2026-01-01T12:00:00+00:00'
result_time: '2026-01-01T12:00:00+00:00'
artifact_paths:
- tool-2026-01-01T12:00:00+00:00-97ac-output.json
```

**Input:**
```json
{
  "q": "small"
}
```


---entry-end---
````

3. `uv run pyright --outputjson packages/archive | jq '.summary'`

```text
{
  "filesAnalyzed": 5,
  "errorCount": 0,
  "warningCount": 0,
  "informationCount": 0,
  "timeInSec": 0.493
}
```

4. `uv run pyright --outputjson | jq '.summary.errorCount'`

```text
643
```

5. `uv run pytest tests/packages/archive -q`

```text
.................................                                        [100%]
33 passed in 0.09s
```

6. `uv run pytest tests/packages/mcp_adapter/test_archive_wiring.py -q`

```text
......                                                                   [100%]
6 passed in 0.37s
```

7. `uv run ruff check packages/archive`

```text
All checks passed!
```

8. `uv run ruff format --check packages/archive`

```text
6 files already formatted
```

9. `git -C <worktree> diff --name-only origin/main...HEAD -- . ':!.planning'`

```text
packages/archive/src/coh_archive/markdown.py
packages/archive/src/coh_archive/service.py
```

10. `git -C <worktree> diff origin/main...HEAD -- packages/archive | grep -c -E '^\+.*(type: ignore|pyright: ignore|noqa)'`

```text
0
```

11. `git -C <worktree> diff --stat origin/main...HEAD -- packages`

```text
 packages/archive/src/coh_archive/markdown.py | 8 ++------
 packages/archive/src/coh_archive/service.py  | 7 +++++--
 2 files changed, 7 insertions(+), 8 deletions(-)
```

`git -C <worktree> diff --numstat origin/main -- packages/archive` (Task 2 gate): `2 6 markdown.py`, `5 2 service.py`, matching the planner's target diff. `git status --porcelain --untracked-files=all -- . ':!.planning'` printed nothing: the evidence run wrote no `.coh/` into the worktree.

## Comparison

Criteria 4 and 5 use `origin/main` instead of the local `main`, which is stale in this worktree (see the PLAN context section).

| Row | CONTEXT criterion | Baseline (e450c04) | After (0e37a94) | Verdict |
|---|---|---|---|---|
| archive pyright errors | 1 | 5 | 0 | PASS |
| whole-repo pyright errors | 2 | 648 | 643 (648 minus 5) | PASS |
| archive tests passed | 3 | 33 | 33 | PASS |
| wiring tests passed | 3 | 6 | 6 | PASS |
| ruff check packages/archive | 6 | All checks passed! | All checks passed! | PASS |
| ruff format --check packages/archive | 6 | 6 files already formatted | 6 files already formatted | PASS |
| files changed outside .planning | 4 | none | markdown.py, service.py | PASS |
| suppression comments added | 5 | n/a | 0 | PASS |
| E1 session_sha256 | 7 | 12bccf8e…fcc91 | 12bccf8e…fcc91 (identical) | PASS |

## Not checked

- The MCP `create_session` handler is not driven directly. E1 calls the `ArchiveService` API (`archive_interaction`, `archive_tool_event`, `read_session_archive`); `test_archive_wiring.py` covers the MCP wiring into `archive_interaction`.
- CI does not run pyright (known gap in CONTRIBUTING); the pyright numbers above are local runs only.
- The 53 pyright errors under `tests/packages/archive` are in the protected check set and out of scope; they are unchanged.
