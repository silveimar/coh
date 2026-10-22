# Phase 5: Docs drift - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning
**Type:** docs. Protected check set: not touched.

<domain>
## Phase Boundary

The repository docs describe only what exists and mark planned components as planned. Requirement: DOCS-01.

In scope: `README.md`; the `## Repository Structure` section of `docs/coding-rules.md` (lines 19-60 at f3743a1); the seven workspace member READMEs (`packages/{execution-core,persistence,archive,prose,mcp_adapter,application}/README.md`, `apps/api/README.md`); a new `packages/prose/README.md`.
Out of scope (do not edit): every other section of `docs/coding-rules.md` (header, Tech Stack rules including line 83, line 226: standards text, Ask-tier per `FLEET-POLICY.md`); `docs/decision-log.md` (append-only); `docs/glossary.md` (rename needs a decision-log entry); `docs/feature-specs/`; `AGENTS.md`, `CONTRIBUTING.md`, `FLEET-POLICY.md`; any code or test.
</domain>

<decisions>
## Implementation Decisions

### coding-rules.md structure section
- **D-01:** Edit only the `## Repository Structure` section, with layout corrections and "planned" labels. Merging the planning PR is the owner's approval of this boundary (FLEET-POLICY: coding-standards changes are Ask).
- **D-02:** Entries that exist under another path are corrected: `packages/mcp-server/` → `packages/mcp_adapter/`; top-level `migrations/` → `packages/persistence/alembic/`. The tree gains the existing `persistence/`, `prose/` and `application/` packages.
- **D-03:** Entries absent but backed by a recorded decision stay and are labelled "planned": `apps/worker/` (Huey, D2), `apps/web/` (D8), `packages/agent-runtime/`, `packages/python-client/`, `frontend/generated-api/`, `package.json`, `pnpm-lock.yaml`, and the pnpm half of line 21. Nothing backed by D2 or D8 is deleted.
- **D-04:** `apps/api/src/coh_api/infrastructure/` (line 58) is replaced by a note that infrastructure lives in `packages/persistence` (`apps/api/src/coh_api/composition.py:6-7`). Not labelled "planned": that would invite a duplicate layer.

### README.md
- **D-05:** "Seven packages" = six under `packages/` plus `apps/api` (`pyproject.toml` workspace members). The structure tree and the Packages section both list all seven, each linking to its README.
- **D-06:** Both decision ranges (lines 15 and 87) become `D1-D15` (15 entries, no gaps).
- **D-07:** The status line (`README.md:3`) stays unchanged; its wording is the owner's (open question).

### Package READMEs
- **D-08:** "Next Actions" items that describe now-existing components as future work are marked done with the existing ✅ + strikethrough pattern (`packages/mcp_adapter/README.md:130-132`). Huey items get "planned".
- **D-09:** Factual fixes from the drift inventory: dev dependencies live in the root group (ADR 0001), install via `uv sync --all-packages`, `uv run pytest`, `apps/api/README.md:21` re-exports claim, `apps/api/README.md:210` pyright note. `packages/persistence/README.md:26` (`alembic upgrade head` location) is corrected only after running it from `packages/persistence/` and pasting the output.
- **D-10:** Claims that point at known defects stay untouched and are listed as follow-ups: `apps/api/README.md:57` ("auto-created on first run": tables are not created), `packages/mcp_adapter/README.md:79-98` (handlers bypass application services).
- **D-11:** Preserve the zero-width characters in `packages/archive/README.md:91-101` that nest code fences.

### New prose README
- **D-12:** `packages/prose/README.md` describes only what is in the package: distribution `prose`, import `coh_prose`, public names from `src/coh_prose/__init__.py`, rules P-01 to P-06 (`docs/behavioral-contract.md` §5), pydantic dependency, its consumer `packages/mcp_adapter/src/coh_mcp/handlers.py`, and `uv run pytest tests/packages/prose`. It names no readability-profile file and no person (public repo; `AGENTS.md`). It includes one Usage snippet, run with `uv run python -c` and pasted into the evidence file.

### Claude's Discretion
- Wording and ordering inside each README, within the facts above.
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `git ls-files 'packages/*/README.md' 'apps/*/README.md' | wc -l` prints `7`.
2. `grep -o -E 'packages/(execution-core|persistence|archive|prose|mcp_adapter|application)|apps/api' README.md | sort -u | wc -l` prints `7`.
3. `grep -o -E 'D1 ?(\.\.\.|-|–) ?D[0-9]+' README.md | sort -u` prints only `D1-D15`, and `grep -c -E '^## D[0-9]+ ' docs/decision-log.md` prints `15`.
4. In the `## Repository Structure` section of `docs/coding-rules.md`, every line naming `worker/`, `web/`, `agent-runtime/`, `python-client/`, `frontend/`, `generated-api/`, `package.json` or `pnpm` contains "planned", and no line names `mcp-server/` or a top-level `migrations/`.
5. `git diff --name-only main...HEAD` lists only `README.md`, `docs/coding-rules.md`, `packages/*/README.md`, `apps/api/README.md` and `.planning/phases/05-*`; every hunk in `docs/coding-rules.md` falls inside the `## Repository Structure` section of the `main` version.
6. `05-VERIFICATION.md` lists every repository path named in `README.md`, the coding-rules structure section and the seven READMEs, each with its `test -e` result or "planned", zero unexplained misses; the prose README snippet output is pasted (H-87).
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 5)
- `.planning/codebase/CONCERNS.md` ("Documented components that do not exist"), `.planning/codebase/STRUCTURE.md`
- `AGENTS.md` ("Layout" block: accurate reference)
- `FLEET-POLICY.md` (Knowledge row: coding-standards changes are Ask)
- `docs/decision-log.md` (D2, D8, D11; append-only)
- `docs/adr/0001-uv-dev-dependency-group.md`
- `docs/behavioral-contract.md` §5 (P-01 to P-06)
- `pyproject.toml` (workspace members)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Done-marker pattern: `packages/mcp_adapter/README.md:130-132`.
- Accurate layout: `AGENTS.md` "Layout" block.

### Established Patterns
- Every package README has a Usage section.

### Integration Points
- No test or CI reads these docs (grep of `tests/` and `.github/`), so docs-only edits cannot break checks.
</code_context>

<specifics>
## Specific Ideas

The decisions above cover every drift item found at f3743a1. The planner re-derives the full inventory with `test -e` on each path named in the in-scope files.
</specifics>

<deferred>
## Deferred Ideas

- `docs/coding-rules.md` header and line 226 (`../COH-Decision-Log.md`, "D1–D10 applied"), pnpm/Huey/`JobRunner` rule text — Ask (standards text).
- `docs/glossary.md:139` `JobRunner` (Huey) — needs a decision-log entry.
- `docs/feature-specs/*` planned-file lists naming `agent-runtime/`, `mcp-server/`, `migrations/`.
- `README.md:3` status line wording — owner.
- Known defects behind `apps/api/README.md:57` and the MCP adapter diagram — code fixes, not docs.
</deferred>
