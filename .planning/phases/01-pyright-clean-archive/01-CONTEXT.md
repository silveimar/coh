# Phase 1: Pyright clean archive - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning
**Type:** chore. Protected check set: not touched.

<domain>
## Phase Boundary

`packages/archive` reaches 0 pyright errors (baseline 5 at f3743a1), with no behavior change and no change to the on-disk archive format. Requirement: TYPE-01.

In scope: `packages/archive/src/coh_archive/markdown.py:222`, `:305` and `service.py:138` (reportUnusedVariable); `service.py:189` (reportUnknownParameterType, reportMissingTypeArgument).
Out of scope: pyright errors under `tests/packages/archive` (53, protected); surfacing tool-event artifacts in `ArchiveWriteResult` or `ToolEvent.artifact_paths`; the inline `import yaml`, broad `except Exception` and payload mutation in the writer.
</domain>

<decisions>
## Implementation Decisions

### Unused variables
- **D-01:** At `markdown.py:222` and `:305`, keep the `self._find_current_session_file(...)` call and bind its unused second element to `_`. Do not delete the statement: `session_file` from the same unpacking is used later (`markdown.py:226-252`, `:308-336`). Do not change the private method's signature.
- **D-02:** At `service.py:138`, discard the artifact list with `pointer, _ = ...`, the same pattern as `service.py:71`. Do not route artifacts into `ArchiveWriteResult` (public service API, `docs/feature-specs/project-local-markdown-interaction-archive.md:142`).

### Return type of `read_session_archive`
- **D-03:** Annotate `service.py:189` as `tuple[dict[str, Any], list[str]]` (`from typing import Any`, standard library). The body stays identical. Reason: `yaml.safe_load` returns `Any` in the bundled stubs, and the package already uses `dict[str, Any]` for YAML metadata (`markdown.py:8`, `:133`). The PR description lists this choice (`CONTRIBUTING.md` DoD).
- **D-04:** Completing a bare `dict` annotation is type-only: the runtime object is identical and annotations are not the archive format. No decision-log entry.

### Claude's Discretion
- None beyond formatting.
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `uv run pyright --outputjson packages/archive | jq '.summary.errorCount'` prints `0`.
2. `uv run pyright --outputjson | jq '.summary.errorCount'` prints exactly 5 fewer than on `main` (648 at f3743a1).
3. `uv run pytest tests/packages/archive -q` and `uv run pytest tests/packages/mcp_adapter/test_archive_wiring.py -q` pass with the same counts as `main` (33 and 6 at f3743a1).
4. `git diff --name-only main...HEAD -- . ':!.planning'` lists only `packages/archive/src/coh_archive/markdown.py` and `packages/archive/src/coh_archive/service.py`.
5. `git diff main...HEAD -- packages/archive | grep -E '^\+.*(type: ignore|pyright: ignore|noqa)'` prints nothing.
6. `uv run ruff check packages/archive` and `uv run ruff format --check packages/archive` pass.
7. Evidence file (H-87 "Ran it"): one run through a real entry point that writes an interaction (MCP `create_session` path, or `ArchiveService.archive_interaction` and `archive_tool_event` called directly) and shows the written session file, plus a `read_session_archive` call on it.
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 1)
- `.planning/codebase/CONCERNS.md` (pyright baseline)
- `docs/feature-specs/project-local-markdown-interaction-archive.md` (public service API, append-only contract)
- `docs/coding-rules.md` (typing)
- `CONTRIBUTING.md` (DoD, protected check set)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_` discard already accepted by pyright here: `service.py:71`.

### Established Patterns
- Archive failures degrade and continue: the broad `except Exception` at `service.py:107` would hide a NameError from a deleted statement as `ARCHIVE_WRITE_FAILED`. `tests/packages/archive/test_service.py:57-61` catches that case.

### Integration Points
- Production path: MCP `create_session` (`packages/mcp_adapter/src/coh_mcp/handlers.py:57-88`) → `archive_wiring.archive_user_input` → `ArchiveService.archive_interaction` → `write_event` → `markdown.py:222`.
- `markdown.py:305`, `service.py:138` and `read_session_archive` are reached only from tests today.
</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.
</specifics>

<deferred>
## Deferred Ideas

- `ToolEvent.artifact_paths` (`models.py:73`) is defined but never filled — possible follow-up; public-contract change.
- `dict[str, object]` instead of `dict[str, Any]` for `read_session_archive` — stricter; revisit when a production reader exists.
</deferred>
