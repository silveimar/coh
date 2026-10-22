# Phase 05 evidence (H-87)

Paths are written as `<worktree>` (the slice worktree `coh-wt/05-docs-drift`) and `<scratch>` (the builder session scratchpad). Each command ran as its own call.

Ref substitution: every diff gate uses `origin/main` in place of `main`. The worktree's local `main` ref is stale (378d9ed), while `origin/main` is 7b54147; `main...HEAD` would list every file changed in #28-#35.

Deviation (lead instruction, 09:57Z): the plan counts U+200B with `grep -c $'\xe2\x80\x8b'`. The `$'...'` shell escape raises a permission prompt, so every U+200B count after PC7 uses the escape-free form `grep -c -P '\x{200B}'`. The two PC7 commands below had already run in the plan's form; the escape-free form was run once at the same commit and gives the same count. The extra character count from the handoff note (`grep -o ... | wc -l`) was withdrawn by the lead and not run.

## Baseline (origin/main 7b54147, before edits)

Branch head at baseline: 1e56c5c (lead plan commit).

PC1 `git -C <worktree> rev-parse origin/main`

```text
7b541475d92a88f3cfd6d0b9c87ad73ccfb96efb
```

PC2 `git -C <worktree> diff --name-only origin/main...HEAD`

```text
.planning/phases/05-docs-drift/05-01-PLAN.md
```

PC3 `grep -n '^## ' <worktree>/docs/coding-rules.md`

```text
7:## Executive Summary
19:## Repository Structure
62:## Project Status
68:## Tech Stack & Conventions
92:## Code Style Rules
123:## Component & Architecture Patterns
145:## Do's and Don'ts
181:## Testing & Quality
211:## Common Pitfalls
```

PC4 `grep -n -E 'D1(\.\.\.|-)D11' <worktree>/README.md`

```text
15:│   ├── decision-log.md        # Durable product decisions D1...D11
87:- [Decision Log](docs/decision-log.md) - Product decisions D1-D11
```

PC5 `grep -n -F 'alembic upgrade head' <worktree>/packages/persistence/README.md`

```text
26:alembic upgrade head
```

PC6 `grep -n -E 'Re-exports|auto-created|when Pyright' <worktree>/apps/api/README.md`

```text
21:├── application/             # Re-exports of packages/application services
57:**Database:** SQLite at `.coh/coh.db` (WAL mode, auto-created on first run).
210:### Type checking (when Pyright is added)
```

PC7 `grep -c $'\xe2\x80\x8b' <worktree>/packages/archive/README.md` (plan form)

```text
4
```

PC7 `grep -n $'\xe2\x80\x8b' <worktree>/packages/archive/README.md` (plan form; the invisible U+200B at the start of each line is written here as `<U+200B>`, so this file holds no zero-width bytes)

```text
91:<U+200B>```yaml
97:<U+200B>```
99:<U+200B>```text
101:<U+200B>```
```

PC7 `grep -c -P '\x{200B}' <worktree>/packages/archive/README.md` (escape-free form, used from here on)

```text
4
```

PC8 `ls -a <worktree>/packages/persistence`

```text
.
..
README.md
alembic
alembic.ini
pyproject.toml
src
```

PC9 `git -C <worktree> status --porcelain --untracked-files=all`

```text
(no output)
```

B1 `git -C <worktree> ls-files 'packages/*/README.md' 'apps/*/README.md' | wc -l`

```text
6
```

B2 `grep -o -E 'packages/(execution-core|persistence|archive|prose|mcp_adapter|application)|apps/api' <worktree>/README.md | sort -u | wc -l`

```text
7
```

B3 `grep -o -E '\]\((packages/(execution-core|persistence|archive|prose|mcp_adapter|application)|apps/api)/README\.md\)' <worktree>/README.md | sort -u | wc -l`

```text
1
```

B4 `grep -o -E 'D1 ?(\.\.\.|-|–) ?D[0-9]+' <worktree>/README.md | sort -u`

```text
D1-D11
D1...D11
```

B5 `grep -c -E '^## D[0-9]+ ' <worktree>/docs/decision-log.md`

```text
15
```

B6 `grep -E 'worker/|web/|agent-runtime/|python-client/|frontend/|generated-api/|package\.json|pnpm' <worktree>/docs/coding-rules.md | grep -v -c planned`

```text
15
```

B7 `grep -c -E 'mcp-server|migrations/' <worktree>/docs/coding-rules.md`

```text
2
```

B8 `grep -o -E '(├──|└──) [a-z_]+\.py' <worktree>/packages/execution-core/README.md | sort -u | wc -l`

```text
14
```

B8 `git -C <worktree> ls-files -- 'packages/execution-core/src/execution_core/*.py' | grep -v -c __init__`

```text
19
```

B9 `grep -c -F '✅ ~~'` on the six READMEs

```text
<worktree>/packages/persistence/README.md:0
<worktree>/packages/application/README.md:0
<worktree>/packages/archive/README.md:0
<worktree>/packages/mcp_adapter/README.md:3
<worktree>/apps/api/README.md:0
<worktree>/packages/execution-core/README.md:0
```

`uv sync --all-packages --locked --directory <worktree>`

```text
Resolved 68 packages in 0.82ms
Checked 64 packages in 0.37ms
```

B10 `uv run --no-sync --directory <worktree> pytest tests/packages/prose -q`

```text
....................................                                     [100%]
36 passed in 0.08s
```

B11 `uv run --no-sync --directory <worktree> pytest tests/packages/application -q`

```text
...........................                                              [100%]
27 passed in 0.28s
```

All PC and B values match the planner values.

## Task 1

S1, the prose README Usage snippet through the real package: `uv run --no-sync --directory <worktree> python -c "from coh_prose import ProsePolicy, ProseRenderer, SpecProposal; spec = SpecProposal(inspection_findings='Inspection: the export command writes no header row.', what='Add a header row to the CSV export', why='Downstream imports expect column names', deliverable='CSV export with a header row', done_when=['The first line of the export lists the column names'], clarity='high', readiness='ready'); print(ProseRenderer().render_spec_proposal(spec)); print(ProsePolicy().validate_no_scaffolding('There are three things to cover.'))"`

```text
Inspection: the export command writes no header row.

WHAT
Add a header row to the CSV export

WHY
Downstream imports expect column names

DELIVERABLE
CSV export with a header row

DONE WHEN
1. The first line of the export lists the column names

CLARITY: high
READINESS: ready
valid=False violations=['P-02 violation: Found scaffolding phrase "there are"'] warnings=[]
```

`uv run --no-sync --directory <worktree> pytest tests/packages/prose -q`

```text
....................................                                     [100%]
36 passed in 0.08s
```

`ls -d` on the seven READMEs linked from the new Packages section

```text
<worktree>/apps/api/README.md
<worktree>/packages/application/README.md
<worktree>/packages/archive/README.md
<worktree>/packages/execution-core/README.md
<worktree>/packages/mcp_adapter/README.md
<worktree>/packages/persistence/README.md
<worktree>/packages/prose/README.md
```

`ls -d` on the import package directories named in the Packages list (`execution_core`, `persistence`, `coh_archive`, `coh_prose`, `coh_mcp`, `coh_application`, `coh_api`)

```text
<worktree>/apps/api/src/coh_api
<worktree>/packages/application/src/coh_application
<worktree>/packages/archive/src/coh_archive
<worktree>/packages/execution-core/src/execution_core
<worktree>/packages/mcp_adapter/src/coh_mcp
<worktree>/packages/persistence/src/persistence
<worktree>/packages/prose/src/coh_prose
```

Gates on the edited files:

| Command | Output |
|---|---|
| `grep -o -w -E 'ProseConfig\|ProsePolicy\|ProseValidationResult\|ProtectedField\|DetourRecommendation\|ExecutionForeground\|ProseRenderer\|RecoverySummary\|SpecProposal\|VerificationResult' <worktree>/packages/prose/README.md \| sort -u \| wc -l` | `10` |
| `grep -o -E 'P-0[1-6]' <worktree>/packages/prose/README.md \| sort -u \| wc -l` | `6` |
| `grep -c -F -e 'uv run pytest tests/packages/prose' -e 'packages/mcp_adapter/src/coh_mcp/handlers.py' -e 'docs/behavioral-contract.md' -e 'pydantic' -e 'coh_prose' <worktree>/packages/prose/README.md` | `7` |
| `grep -c -i -E 'readability\|profile' <worktree>/packages/prose/README.md` | `0` |
| `grep -n -F '**Status:** Phase 0 complete, execution-core implementation in progress' <worktree>/README.md` | `3:**Status:** Phase 0 complete, execution-core implementation in progress` |
| link gate (B3 command) | `7` |
| range gate (B4 command) | `D1-D15` |
