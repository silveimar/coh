---
phase: 01-pyright-clean-archive
plan: 01
requirements: [TYPE-01]
status: complete
key_files:
  modified:
    - packages/archive/src/coh_archive/markdown.py
    - packages/archive/src/coh_archive/service.py
  created:
    - .planning/phases/01-pyright-clean-archive/01-EVIDENCE.md
commits:
  - 0e37a94 chore(archive): clear the 5 pyright errors in packages/archive (TYPE-01)
  - a903ddf docs(planning): Phase 1 H-87 evidence (baseline and after)
---

# Phase 01 Plan 01: Pyright clean archive (summary)

`packages/archive` now reports 0 pyright errors (was 5). The change is four edits in two files. Runtime behavior and the on-disk archive format did not change: the synthetic E1 run writes a byte-identical session file before and after.

## Numbers

| Measure | CONTEXT (f3743a1) | Measured base (origin/main e450c04) | After (0e37a94) |
|---|---|---|---|
| `pyright packages/archive` errorCount | 5 | 5 | 0 |
| Whole-repo pyright errorCount | 648 | 648 | 643 |
| `pytest tests/packages/archive` | 33 passed | 33 passed | 33 passed |
| `pytest tests/packages/mcp_adapter/test_archive_wiring.py` | 6 passed | 6 passed | 6 passed |
| E1 `session_sha256` | n/a | 12bccf8e…fcc91 | 12bccf8e…fcc91 |

The PLAN names 576ee9e as base. The measured base is e450c04, because the commits after 576ee9e touch only `.planning`. Full outputs are in `01-EVIDENCE.md`.

## Edits

- D-01, `markdown.py`: both `_find_current_session_file` unpackings in `_write_event_sync` and `_write_tool_event_sync` bind the unused part number to `_`. The call and `session_file` stay.
- D-02, `service.py` `archive_tool_event`: `pointer, _ = await writer.write_tool_event(event)`, the same pattern as `archive_interaction`. Artifacts are not routed into `ArchiveWriteResult`.
- D-03, `service.py` `read_session_archive`: return annotation `tuple[dict[str, Any], list[str]]`, with `from typing import Any`. Body unchanged.

## Choices not dictated by the spec

- `dict[str, Any]`, not `dict[str, object]` (D-03). `yaml.safe_load` returns `Any` in the bundled stubs, and the package already types YAML metadata as `dict[str, Any]`. The stricter form is deferred until a production reader exists. Type-only, so no decision-log entry (D-04).
- Layout follows ruff format: the two `markdown.py` calls collapse to one line each (they fit in 88 columns once `part` became `_`). The completed `read_session_archive` signature is 91 columns, so it wraps over three lines.
- Diff gates use `origin/main`, not local `main`. Local `main` in the worktree is stale at 378d9ed, so `main...HEAD` already listed unrelated files before any edit.

## Deviations

- PLAN step A1, `git rev-parse --short origin/main HEAD`, fails (`fatal: Needed a single revision`): `--short` takes one revision. It was run as two commands. Recorded in `01-EVIDENCE.md`.

## Not covered

- The MCP `create_session` handler was not driven directly. `test_archive_wiring.py` covers that wiring.
- CI does not run pyright. The pyright numbers are local runs.
- The 53 pyright errors under `tests/packages/archive` are in the protected check set and out of scope.
