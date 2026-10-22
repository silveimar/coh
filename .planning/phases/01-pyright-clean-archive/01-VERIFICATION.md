# Phase 01 verification (builder self-check)

Self-check by the builder seat, not the slice proof. The slice proof is the checker's report on the head SHA. Re-run by a fresh builder session at a903ddf, after the original session paused for context.

| # | CONTEXT criterion | Command (run at a903ddf) | Result | Verdict |
|---|---|---|---|---|
| 1 | archive pyright 0 | `uv run pyright --outputjson packages/archive \| jq '.summary.errorCount'` | `0` | PASS |
| 2 | repo pyright base minus 5 | `uv run pyright --outputjson \| jq '.summary.errorCount'` | `643` (base 648; from `01-EVIDENCE.md`, not re-run in this session) | PASS |
| 3 | suites at base counts | `uv run pytest tests/packages/archive tests/packages/mcp_adapter/test_archive_wiring.py -q` | `39 passed` (33 + 6) | PASS |
| 4 | only two files outside .planning | `git diff origin/main...HEAD -- packages` | `markdown.py`, `service.py`; four edits, as planned | PASS |
| 5 | no suppression comments | same diff, inspected | none added | PASS |
| 6 | ruff | `uv run ruff check .` / `uv run ruff format --check .` | `All checks passed!` / `168 files already formatted` | PASS |
| 7 | H-87 run through a real entry point | E1 (see `01-EVIDENCE.md`) | `interaction: written`, `tool_event: written`, `entries: 2`, `session_sha256: 12bccf8e…fcc91`, the same as the baseline | PASS |

Prohibitions: no protected path, dependency, decision-log, `STATE.md` or `ROADMAP.md` change (diff limited to the two source files plus this phase directory).

Not checked: the MCP `create_session` handler directly; pyright in CI (not configured); the 53 test-side pyright errors (protected, out of scope).
