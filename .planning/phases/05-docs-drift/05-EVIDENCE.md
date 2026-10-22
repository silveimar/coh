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

Committed as b0931e8. After the commit, `git -C <worktree> ls-files 'packages/*/README.md' 'apps/*/README.md' | wc -l` printed `7`.

## Task 2

1. `grep -n '^## ' <worktree>/docs/coding-rules.md` (the same 9 headings in the same order; every line after 19 shifts by +4)

```text
7:## Executive Summary
19:## Repository Structure
66:## Project Status
72:## Tech Stack & Conventions
96:## Code Style Rules
127:## Component & Architecture Patterns
149:## Do's and Don'ts
185:## Testing & Quality
215:## Common Pitfalls
```

2. `git -C <worktree> diff -U0 origin/main -- docs/coding-rules.md`, run before the commit (the working-tree form). Old-side ranges: 21, 27-28, 31, 33-37, 42-43, 58, and an insertion after 61. All lie within lines 20-61.

```text
diff --git a/docs/coding-rules.md b/docs/coding-rules.md
index 9dbe243..a693596 100644
--- a/docs/coding-rules.md
+++ b/docs/coding-rules.md
@@ -21 +21 @@ Keep these concepts separate:
-Polyglot monorepo: uv workspace for Python, pnpm workspace for TypeScript.
+Monorepo: a uv workspace for Python; a pnpm workspace for TypeScript is planned (Decisions D2, D8).
@@ -27,2 +27,2 @@ Polyglot monorepo: uv workspace for Python, pnpm workspace for TypeScript.
-│   ├── worker/              # Huey worker entry point and job registration
-│   └── web/                 # React + Vite application (Phase 3 only — Decision D8)
+│   ├── worker/              # Huey worker entry point and job registration (planned; Decision D2)
+│   └── web/                 # React + Vite application (planned; Phase 3 only — Decision D8)
@@ -31 +31,4 @@ Polyglot monorepo: uv workspace for Python, pnpm workspace for TypeScript.
-│   ├── agent-runtime/       # Provider adapters, prompts, tools, agent workflows
+│   ├── application/         # Application services
+│   ├── persistence/         # SQLAlchemy 2 state store: models, repositories, unit of work
+│   │   └── alembic/         # Alembic migration environment and revisions (alembic.ini sits beside it)
+│   ├── agent-runtime/       # Provider adapters, prompts, tools, agent workflows (planned)
@@ -33,5 +36,5 @@ Polyglot monorepo: uv workspace for Python, pnpm workspace for TypeScript.
-│   ├── mcp-server/          # Python MCP adapter (first adapter: Claude Code — D5)
-│   └── python-client/       # Optional typed Python API client
-├── frontend/
-│   └── generated-api/       # Generated TypeScript OpenAPI client; do not edit
-├── migrations/              # Alembic migration environment and revisions
+│   ├── prose/               # Prose rendering policy (P-01 to P-06) and output renderers
+│   ├── mcp_adapter/         # Python MCP adapter (first adapter: Claude Code — D5)
+│   └── python-client/       # Optional typed Python API client (planned)
+├── frontend/                # TypeScript frontend (planned; Phase 3 only — Decision D8)
+│   └── generated-api/       # Generated TypeScript OpenAPI client; do not edit (planned)
@@ -42,2 +45,2 @@ Polyglot monorepo: uv workspace for Python, pnpm workspace for TypeScript.
-├── package.json             # Root pnpm workspace configuration
-└── pnpm-lock.yaml           # Committed TypeScript dependency lockfile
+├── package.json             # Root pnpm workspace configuration (planned)
+└── pnpm-lock.yaml           # Committed TypeScript dependency lockfile (planned)
@@ -58 +60,0 @@ apps/api/src/coh_api/
-├── infrastructure/
@@ -61,0 +64,2 @@ apps/api/src/coh_api/
+The API has no infrastructure layer of its own: `composition.py` imports the engine, session factory and unit of work from `packages/persistence` (`apps/api/src/coh_api/composition.py:6-7`).
+
```

3. `grep -n -E 'worker/|web/|agent-runtime/|python-client/|frontend/|generated-api/|package\.json|pnpm' <worktree>/docs/coding-rules.md`

```text
21:Monorepo: a uv workspace for Python; a pnpm workspace for TypeScript is planned (Decisions D2, D8).
27:│   ├── worker/              # Huey worker entry point and job registration (planned; Decision D2)
28:│   └── web/                 # React + Vite application (planned; Phase 3 only — Decision D8)
34:│   ├── agent-runtime/       # Provider adapters, prompts, tools, agent workflows (planned)
38:│   └── python-client/       # Optional typed Python API client (planned)
39:├── frontend/                # TypeScript frontend (planned; Phase 3 only — Decision D8)
40:│   └── generated-api/       # Generated TypeScript OpenAPI client; do not edit (planned)
45:├── package.json             # Root pnpm workspace configuration (planned)
46:└── pnpm-lock.yaml           # Committed TypeScript dependency lockfile (planned)
70:- Monorepo: yes — uv workspace (Python) + pnpm workspace (TypeScript).
76:- **Package managers:** uv for all Python operations; pnpm for all TypeScript operations. Commit both lockfiles.
86:- **API contract:** Pydantic models at API/integration boundaries generate the OpenAPI schema. Generate the TypeScript client into `frontend/generated-api/` (Hey API or `openapi-ts` via a checked-in command). Never hand-maintain duplicate types; never edit generated files.
117:- Use generated API types from `frontend/generated-api/` for all server contracts; explicit return types for exported functions and hooks.
175:- DON'T hand-write duplicate TypeScript versions of Pydantic API schemas or edit `frontend/generated-api/`.
209:- Frontend (Phase 3): lint/format checks, `pnpm exec tsc --noEmit`, `pnpm test`.
```

4. The same grep piped to `grep -v -c planned` (baseline 15). The 6 lines left, 70, 76, 86, 117, 175 and 209, all come after `66:## Project Status`, outside the section.

```text
6
```

Other Task 2 gates:

| Command | Output |
|---|---|
| `grep -c -E 'mcp-server\|migrations/' <worktree>/docs/coding-rules.md` | `0` (baseline 2) |
| `grep -c -F 'composition.py:6-7' <worktree>/docs/coding-rules.md` | `1` (baseline 0) |
| `grep -c -E '(├──\|└──) (mcp_adapter\|persistence\|prose\|application\|alembic)/' <worktree>/docs/coding-rules.md` | `6` (baseline 1) |
| `grep -c -F 'infrastructure/' <worktree>/docs/coding-rules.md` | `0` (baseline 1) |
| `grep -n -F 'Huey with SQLite initially' <worktree>/docs/coding-rules.md` | `87:- **Background jobs:** Huey with SQLite initially; ...` |
| `git -C <worktree> show origin/main:docs/coding-rules.md \| grep -n -F 'Huey with SQLite initially'` | `83:- **Background jobs:** Huey with SQLite initially; ...` (same text, shifted by +4) |

5. `ls -d` on every R and P path of the new section (exit 2; "cannot access" only for the 8 planned paths)

```text
ls: cannot access '<worktree>/apps/worker': No such file or directory
ls: cannot access '<worktree>/apps/web': No such file or directory
ls: cannot access '<worktree>/packages/agent-runtime': No such file or directory
ls: cannot access '<worktree>/packages/python-client': No such file or directory
ls: cannot access '<worktree>/frontend': No such file or directory
ls: cannot access '<worktree>/frontend/generated-api': No such file or directory
ls: cannot access '<worktree>/package.json': No such file or directory
ls: cannot access '<worktree>/pnpm-lock.yaml': No such file or directory
<worktree>/apps
<worktree>/apps/api
<worktree>/apps/api/src/coh_api
<worktree>/apps/api/src/coh_api/api
<worktree>/apps/api/src/coh_api/application
<worktree>/apps/api/src/coh_api/composition.py
<worktree>/docs
<worktree>/packages
<worktree>/packages/application
<worktree>/packages/archive
<worktree>/packages/execution-core
<worktree>/packages/execution-core/src/execution_core
<worktree>/packages/execution-core/src/execution_core/domain
<worktree>/packages/execution-core/src/execution_core/events
<worktree>/packages/execution-core/src/execution_core/policies
<worktree>/packages/execution-core/src/execution_core/state_machine
<worktree>/packages/mcp_adapter
<worktree>/packages/persistence
<worktree>/packages/persistence/alembic
<worktree>/packages/persistence/alembic.ini
<worktree>/packages/prose
<worktree>/pyproject.toml
<worktree>/tests
<worktree>/tests/evals
<worktree>/uv.lock
```

Committed as d9a4a1c.

## Task 3

### Step A, alembic runs

1. `ls -a <worktree>/packages/persistence` (precondition: no `.coh`): output identical to PC8 (`.`, `..`, `README.md`, `alembic`, `alembic.ini`, `pyproject.toml`, `src`).

2. R1 `uv run --no-sync --directory <worktree> alembic upgrade head` (exit 255)

```text
FAILED: No 'script_location' key found in configuration.
```

3. R2 `uv run --no-sync --directory <worktree>/packages/persistence alembic upgrade head` (exit 1). The traceback is long, with two chained exceptions. The frames inside site-packages are elided here and marked `[...]`; the env.py frames and the final lines are verbatim.

```text
Traceback (most recent call last):
  File "<worktree>/.venv/lib/python3.15/site-packages/sqlalchemy/engine/base.py", line 144, in __init__
    self._dbapi_connection = engine.raw_connection()
[...]
sqlite3.OperationalError: unable to open database file

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "<worktree>/.venv/bin/alembic", line 10, in <module>
    sys.exit(main())
[...]
  File "<worktree>/packages/persistence/alembic/env.py", line 53, in <module>
    run_migrations_online()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "<worktree>/packages/persistence/alembic/env.py", line 43, in run_migrations_online
    with connectable.connect() as connection:
         ~~~~~~~~~~~~~~~~~~~^^
[...]
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
(Background on this error at: https://sqlalche.me/e/20/e3q8)
```

4. `ls -a <worktree>/packages/persistence` after R2: unchanged, no `.coh` entry.

```text
.
..
README.md
alembic
alembic.ini
pyproject.toml
src
```

5. `git -C <worktree> status --porcelain --untracked-files=all` after R2

```text
(no output)
```

6. `mkdir -p <scratch>/alembic-run` (no output)
7. `cp -r <worktree>/packages/persistence <scratch>/alembic-run/` (no output)
8. `mkdir <scratch>/alembic-run/persistence/.coh` (no output)

9. R3 `uv run --no-sync --project <worktree> --directory <scratch>/alembic-run/persistence alembic upgrade head` (exit 0)

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Initial COH persistence schema
```

R3-T `uv run --no-sync --project <worktree> python -c "import sqlite3; c = sqlite3.connect('<scratch>/alembic-run/persistence/.coh/coh.db'); print(sorted(r[0] for r in c.execute(\"select name from sqlite_master where type='table'\"))); print(c.execute('select version_num from alembic_version').fetchall())"`

```text
['alembic_version', 'checkpoints', 'decisions', 'evidence', 'execution_sessions', 'parking_items', 'specifications', 'tasks']
[('001_initial_schema',)]
```

Source lines behind the Setup prose: `alembic/env.py:35` sets `configuration["sqlalchemy.url"] = "sqlite:///.coh/coh.db"`; `handlers.py:46-49` opens `project_root / ".coh" / "coh.db"`; `composition.py:15-19` defaults to `Path.cwd() / ".coh"` / `coh.db`.

### Step B, evidence for the D-08 markers

`grep -n -E 'include_router' <worktree>/apps/api/src/coh_api/main.py`

```text
38:    app.include_router(spec_gate.router, prefix="/api/v1")
39:    app.include_router(foreground.router, prefix="/api/v1")
```

`grep -n -i huey` on the root `pyproject.toml` and the seven member `pyproject.toml` files

```text
(no output)
```

`grep -n -E 'name="(plan_work|execute_task|verify_deliverable)"' <worktree>/packages/mcp_adapter/src/coh_mcp/server.py`

```text
233:                name="plan_work",
277:                name="execute_task",
291:                name="verify_deliverable",
```

`git -C <worktree> ls-files -- 'packages/execution-core/src/execution_core/*.py'` (24 files, 5 of them `__init__.py`, so 19 modules)

```text
packages/execution-core/src/execution_core/__init__.py
packages/execution-core/src/execution_core/domain/__init__.py
packages/execution-core/src/execution_core/domain/checkpoint.py
packages/execution-core/src/execution_core/domain/clock.py
packages/execution-core/src/execution_core/domain/commands.py
packages/execution-core/src/execution_core/domain/decision.py
packages/execution-core/src/execution_core/domain/enums.py
packages/execution-core/src/execution_core/domain/evidence.py
packages/execution-core/src/execution_core/domain/foreground.py
packages/execution-core/src/execution_core/domain/parking_item.py
packages/execution-core/src/execution_core/domain/session.py
packages/execution-core/src/execution_core/domain/specification.py
packages/execution-core/src/execution_core/domain/task.py
packages/execution-core/src/execution_core/events/__init__.py
packages/execution-core/src/execution_core/events/domain_events.py
packages/execution-core/src/execution_core/policies/__init__.py
packages/execution-core/src/execution_core/policies/completion_policy.py
packages/execution-core/src/execution_core/policies/foreground_policy.py
packages/execution-core/src/execution_core/policies/integrity_policy.py
packages/execution-core/src/execution_core/policies/parking_policy.py
packages/execution-core/src/execution_core/policies/permission_policy.py
packages/execution-core/src/execution_core/policies/readiness_policy.py
packages/execution-core/src/execution_core/state_machine/__init__.py
packages/execution-core/src/execution_core/state_machine/lifecycle.py
```

### Step D, the corrected test command and the gates

`uv run --no-sync --directory <worktree> pytest tests/packages/application -q`

```text
...........................                                              [100%]
27 passed in 0.28s
```

| Command | Output |
|---|---|
| `grep -o -E '(├──\|└──) [a-z_]+\.py' <worktree>/packages/execution-core/README.md \| sort -u \| wc -l` | `19` (baseline 14) |
| `grep -c -F 'uv run pytest tests/packages/application' <worktree>/packages/application/README.md` | `2` (baseline 0) |
| `grep -c -F 'uv pip install' <worktree>/packages/persistence/README.md` | `0` (baseline 1) |
| `grep -c -F -e 'uv run alembic upgrade head' -e 'sqlite:///.coh/coh.db' -e 'unable to open database file' <worktree>/packages/persistence/README.md` | `3` |
| `grep -c -E 'pytest>=8\.3\.0\|ruff>=0\.6\.0' <worktree>/packages/execution-core/README.md` | `0` (baseline 2) |
| `grep -c -F 'dependency-groups' <worktree>/packages/execution-core/README.md` | `1` (baseline 0) |
| `grep -c -F '✅ ~~'` on the execution-core, persistence and application READMEs | `4`, `3`, `2` |

`grep -n -F 'Huey' <worktree>/packages/execution-core/README.md <worktree>/packages/persistence/README.md`. The Next Actions lines say planned. Execution-core line 103 is the old line 98, unchanged and shifted by the five added tree lines.

```text
<worktree>/packages/persistence/README.md:135:3. **Huey Task Queue**: Async processing for long-running operations (planned; Decision D2)
<worktree>/packages/execution-core/README.md:103:The package imports no FastAPI, SQLAlchemy, Huey, or MCP. Those live in the application and adapter layers.
<worktree>/packages/execution-core/README.md:126:- Background jobs via Huey (planned; Decision D2)
```
