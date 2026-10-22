---
phase: 05-docs-drift
plan: 01
requirements: [DOCS-01]
status: complete
key_files:
  created:
    - packages/prose/README.md
    - .planning/phases/05-docs-drift/05-EVIDENCE.md
    - .planning/phases/05-docs-drift/05-VERIFICATION.md
    - .planning/phases/05-docs-drift/05-01-SUMMARY.md
  modified:
    - README.md
    - docs/coding-rules.md
    - packages/execution-core/README.md
    - packages/persistence/README.md
    - packages/application/README.md
    - packages/archive/README.md
    - apps/api/README.md
---

# Phase 05 Plan 01: Docs drift (summary)

The 9 in-scope texts name 307 path tokens. Each of the 193 repository paths printed in an `ls -d` run, and the 8 paths that do not exist are labelled planned. All 8 are in the coding-rules Repository Structure section: `apps/worker`, `apps/web`, `packages/agent-runtime`, `packages/python-client`, `frontend`, `frontend/generated-api`, `package.json` and `pnpm-lock.yaml`. The other 106 tokens are not repository paths: URLs, routes, runtime `.coh/` paths, placeholders and slash-joined words. The new `packages/prose/README.md` Usage snippet ran through the real package and printed the P-01 ordering and the P-02 violation.

Base: origin/main 7b54147. Branch commits: 1e56c5c (lead plan), b0931e8 (Task 1), d9a4a1c (Task 2), 825ed96 (Task 3), 6d1cd0b (Task 4), then the commit carrying this summary.

## What changed

- `README.md`: the tree and the Packages section list and link all seven workspace members (link gate 7, baseline 1). Both decision ranges read `D1-D15`. Line 3 is unchanged (D-07).
- `docs/coding-rules.md`: only the `## Repository Structure` body changed (old-side hunks within lines 21-61). The hyphenated MCP directory became `mcp_adapter/`. The top-level migration directory went, and `persistence/` with its `alembic/` child took its place. `application/` and `prose/` were added. Every D2- or D8-backed absent entry stays, labelled `(planned)` or `(planned; Decision Dn)`. The API `infrastructure/` entry was replaced by a note citing `composition.py:6-7`. The word "Polyglot" was dropped on purpose: line 21 now says the pnpm workspace is planned (D-03, the pnpm half).
- `packages/prose/README.md` (new, D-12): purpose, Rules (P-01 to P-06 mapped to the methods that implement them), Public API (all 10 names), Usage, Testing and Dependencies. It names no profile file and no person.
- execution-core, persistence, application, archive and apps/api READMEs: the D-08 done markers (`✅ ~~item~~ — Complete: <where>`) and Huey labelled planned (Decision D2). The D-09 fixes:
  - execution-core: the root dev group replaces the per-package dev list, and the tree gained `session.py`, `commands.py`, `enums.py`, `clock.py` and `events/domain_events.py`, so it lists all 19 modules.
  - persistence: `uv sync --all-packages` and the alembic Setup text.
  - application: `uv run` on both test commands.
  - apps/api: the `application/` placeholder comment and the type-checking note.

## Alembic outcome (D-09)

- R1, from the repository root: exit 255, `FAILED: No 'script_location' key found in configuration.`
- R2, from `packages/persistence/` in the worktree: exit 1, `sqlite3.OperationalError: unable to open database file`. No file was written.
- R3, from a scratch copy with `.coh/` present: exit 0, `Running upgrade  -> 001_initial_schema`. It created 7 tables plus `alembic_version`.

The persistence Setup therefore documents `cd packages/persistence`, `mkdir -p .coh` and `uv run alembic upgrade head`. It says the result is `packages/persistence/.coh/coh.db`, which neither adapter opens. The underlying code issue is follow-up F-6. No `.coh/` or DB file was left in the worktree.

## Archive item split (D-08)

Archive Next Action 1 is marked done for the user/agent half: `archive_user_input` and `archive_agent_output` are called from `handlers.py`. The tool-lifecycle half stays open in the same line: `archive_tool_invocation` exists, but no handler calls it (F-8). Item 2, checkpoint wiring, is done. Items 3-5 are unchanged.

## Findings and deviations

- Ref substitution: every diff gate uses `origin/main` in place of `main`. The worktree's local `main` is stale at 378d9ed, while `origin/main` is 7b54147.
- Criterion 2 already passed at baseline (7), because the test paths in README.md contain the package names. The link gate (7 unique member-README links, baseline 1) was added as the discriminating check.
- U+200B counts (D-11), lead instruction 09:57Z: the plan's `grep -c $'\xe2\x80\x8b'` form raises a permission prompt, so every count after PC7 uses `grep -c -P '\x{200B}'`. Both forms printed 4 at the same commit, and the count is 4 after the edit. The handoff note's extra `grep -o ... | wc -l` character count was withdrawn by the lead and not run. The PC7 line-number output in 05-EVIDENCE.md writes each U+200B as `<U+200B>`, so the evidence file holds no zero-width bytes.
- The R2 traceback in 05-EVIDENCE.md has its site-packages frames elided (marked `[...]`). The env.py frames and the final error lines are verbatim.
- Y1 reported 26 pyright errors for apps/api, so the type-checking note says it currently reports errors.

## Choices not dictated by the spec

- The T-CR wording, as planned. The label form is `(planned)` or `(planned; Decision Dn)`, appended to the existing tree comment.
- README Packages list format: one linked line per member, `[path](path): description (import name)`. The import directories were checked with `ls -d`.
- Prose README section order: purpose, Rules (table), Public API, Usage, Testing, Dependencies. The Rules table also cites section 5's eval-judged note for P-04 and P-06.

## Follow-ups (recorded, not edited)

F-1 to F-9 and the two D-10 defects are listed with file:line evidence in 05-VERIFICATION.md, "Follow-ups". F-9: once the lead appends the certifi entry (D-06), `README.md` needs `D1-D16`.

## Final gates (run at 2cb602f, after the verification commit)

| Command | Output |
|---|---|
| `git -C <worktree> diff --name-only origin/main...HEAD` | the 4 files under `.planning/phases/05-docs-drift/`, `README.md`, `apps/api/README.md`, `docs/coding-rules.md`, and the application, archive, execution-core, persistence and prose READMEs. Nothing else |
| `git -C <worktree> ls-files 'packages/*/README.md' 'apps/*/README.md' \| wc -l` | `7` |
| `grep -c -E '^## D[0-9]+ ' <worktree>/docs/decision-log.md` | `15` |
| `git -C <worktree> status --porcelain --untracked-files=all` | (no output) |
| `grep -c -E '/(home\|tmp)/'` on 05-EVIDENCE.md, 05-VERIFICATION.md and 05-01-SUMMARY.md | `0`, `0`, `0` |
| `git -C <worktree> diff origin/main...HEAD \| grep -c -E '/(home\|tmp)/'` | `0` |
| decider name from the decision-log Decided lines, in `git -C <worktree> diff -U0 origin/main...HEAD` (`grep -c -i -w`) | 0 matches |
| `git -C <worktree> diff origin/main...HEAD \| grep -c -P '\x{200B}'` | `0` (no zero-width character added or removed) |
| `grep -c -P '\x{200B}' <worktree>/packages/archive/README.md` | `4` |
| 05-VERIFICATION.md: inventory headings with `(0 missing)` / required sections / pasted `valid=False violations=` | `9` / `5` / `1` |

This summary edit is the only change after 2cb602f.

## Not covered

GitHub rendering was not viewed. Usage snippets other than the prose one were not run. Alembic against a database that `create_all` already populated was not exercised. CI on the PR head is UNKNOWN until it runs.
