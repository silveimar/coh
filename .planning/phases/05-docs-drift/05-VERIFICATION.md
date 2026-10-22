# Phase 05 verification (builder self-check)

This is the builder seat's self-check, not the slice proof. The slice proof is the checker's report on the head SHA. The commands ran at 6d1cd0b, the committed Task 4 head, before the builder's evidence, summary and verification commit. The full output is in `05-EVIDENCE.md`.

## Criteria

Criterion 5 uses `origin/main` in place of `main`, because the worktree's local `main` ref is stale (378d9ed) and `main...HEAD` would list every file changed in #28-#35.

| # | CONTEXT criterion | Command | Result | Verdict |
|---|---|---|---|---|
| 1 | 7 member READMEs tracked | `git ls-files 'packages/*/README.md' 'apps/*/README.md' \| wc -l` | `7` (baseline 6) | PASS |
| 2 | README.md names all 7 members | CONTEXT grep: `grep -o -E 'packages/(execution-core\|persistence\|archive\|prose\|mcp_adapter\|application)\|apps/api' README.md \| sort -u \| wc -l`; link gate: `grep -o -E '\]\((packages/(...)\|apps/api)/README\.md\)' README.md \| sort -u \| wc -l` | CONTEXT grep `7`. It does not discriminate: it already printed 7 at baseline, because the test paths contain the package names. Link gate `7` (baseline 1) | PASS |
| 3 | only D1-D15 in README.md; decision log has 15 entries | `grep -o -E 'D1 ?(\.\.\.\|-\|–) ?D[0-9]+' README.md \| sort -u`; `grep -c -E '^## D[0-9]+ ' docs/decision-log.md` | `D1-D15`; `15` | PASS |
| 4 | in the Repository Structure section, every worker/web/agent-runtime/python-client/frontend/generated-api/package.json/pnpm line says planned; no mcp-server/ or top-level migrations/ | `grep -n -E 'worker/\|web/\|agent-runtime/\|python-client/\|frontend/\|generated-api/\|package\.json\|pnpm' docs/coding-rules.md`, then `\| grep -v -c planned`; `grep -c -E 'mcp-server\|migrations/' docs/coding-rules.md` | 9 lines in the section (21-46), all with `planned`. `grep -v -c planned` prints `6` (baseline 15); the 6 are lines 70, 76, 86, 117, 175 and 209, all after `66:## Project Status`. MCP/migrations grep `0` (baseline 2) | PASS |
| 5 | diff lists only the allowed paths; every coding-rules hunk lies in the section of the base version | `git diff --name-only origin/main...HEAD`; `git diff -U0 origin/main...HEAD -- docs/coding-rules.md` | At 6d1cd0b: `.planning/phases/05-docs-drift/05-01-PLAN.md`, `.planning/phases/05-docs-drift/05-EVIDENCE.md`, `README.md`, `apps/api/README.md`, `docs/coding-rules.md`, and the application, archive, execution-core, persistence and prose READMEs. Old-side hunk ranges: 21, 27-28, 31, 33-37, 42-43, 58, and an insertion after 61. All lie within the section body, lines 20-61 | PASS (rechecked after the final commit; see 05-01-SUMMARY.md) |
| 6 | every repository path in the 9 texts listed with its `test -e` result or planned; zero unexplained misses; prose snippet output pasted | Command P plus one `ls -d` per file (05-EVIDENCE.md, "Task 5 path checks") | 307 tokens: 193 repository paths (0 missing), 8 planned, 106 not repository paths. See the inventory below; the snippet output is below | PASS |

Extra checks (05-EVIDENCE.md): the U+200B count in `packages/archive/README.md` is 4 before and after (D-11). `apps/api/README.md:57` is unchanged, and `packages/mcp_adapter/README.md` has no diff (D-10). `README.md:3` is unchanged (D-07). No `.coh/` or DB file exists in the worktree after the alembic runs.

## Path inventory (criterion 6)

Classes: R is a repository path, P a planned path (its line says planned), and X is not a repository path. Each R path printed in that file's `ls -d` (05-EVIDENCE.md, "Task 5 path checks"). "exists" below means the path printed.

### README.md — Command P: 53 tokens; 51 repository paths (0 missing); 0 planned; 2 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 11 | `packages/` | R | `packages` | exists |
| 12 | `execution-core/` | R | `packages/execution-core` | exists |
| 13 | `persistence/` | R | `packages/persistence` | exists |
| 13 | `alembic/` | R | `packages/persistence/alembic` | exists |
| 14 | `archive/` | R | `packages/archive` | exists |
| 15 | `prose/` | R | `packages/prose` | exists |
| 16 | `mcp_adapter/` | R | `packages/mcp_adapter` | exists |
| 17 | `application/` | R | `packages/application` | exists |
| 18 | `apps/` | R | `apps` | exists |
| 19 | `api/` | R | `apps/api` | exists |
| 20 | `docs/` | R | `docs` | exists |
| 21 | `behavioral-contract.md` | R | `docs/behavioral-contract.md` | exists |
| 22 | `decision-log.md` | R | `docs/decision-log.md` | exists |
| 23 | `coding-rules.md` | R | `docs/coding-rules.md` | exists |
| 24 | `feature-specs/` | R | `docs/feature-specs` | exists |
| 25 | `tests/` | R | `tests` | exists |
| 25 | `packages/` | R | `tests/packages` | exists |
| 25 | `apps/` | R | `tests/apps` | exists |
| 25 | `evals/` | R | `tests/evals` | exists |
| 58 | `tests/` | R | `tests` | exists |
| 58 | `pytest.ini` | R | `pytest.ini` | exists |
| 59 | `.coveragerc` | R | `.coveragerc` | exists |
| 66 | `tests/packages/execution-core` | R | same | exists |
| 67 | `tests/packages/persistence` | R | same | exists |
| 68 | `tests/packages/archive` | R | same | exists |
| 69 | `tests/packages/prose` | R | same | exists |
| 70 | `tests/packages/mcp_adapter` | R | same | exists |
| 71 | `tests/packages/application` | R | same | exists |
| 72 | `tests/apps/api` | R | same | exists |
| 75 | `tests/evals` | R | same | exists |
| 78 | `tests/packages/execution-core` | R | same | exists |
| 78 | `packages/execution-core/src` | R | same | exists |
| 87 | `pyproject.toml` | R | `pyproject.toml` | exists |
| 89 | `packages/execution-core/README.md` (link text and target) | R x2 | same | exists |
| 90 | `packages/persistence/README.md` (link text and target) | R x2 | same | exists |
| 91 | `packages/archive/README.md` (link text and target) | R x2 | same | exists |
| 92 | `packages/prose/README.md` (link text and target) | R x2 | same | exists |
| 93 | `packages/mcp_adapter/README.md` (link text and target) | R x2 | same | exists |
| 94 | `packages/application/README.md` (link text and target) | R x2 | same | exists |
| 95 | `apps/api/README.md` (link text and target) | R x2 | same | exists |
| 99 | `docs/behavioral-contract.md` | R | same | exists |
| 100 | `docs/decision-log.md` | R | same | exists |
| 101 | `docs/coding-rules.md` | R | same | exists |
| 102 | `docs/glossary.md` | R | same | exists |
| 41, 47 | `//docs.astral.sh/uv/`, `//astral.sh/uv/install.sh` | X x2 | | URL |

### docs/coding-rules.md (Repository Structure, lines 20-65) — Command P: 39 tokens; 28 repository paths (0 missing); 8 planned; 3 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 25 | `apps/` | R | `apps` | exists |
| 26 | `api/` | R | `apps/api` | exists |
| 27 | `worker/` | P | `apps/worker` | planned (Decision D2); cannot access |
| 28 | `web/` | P | `apps/web` | planned (Phase 3, Decision D8); cannot access |
| 29 | `packages/` | R | `packages` | exists |
| 30 | `execution-core/` | R | `packages/execution-core` | exists |
| 31 | `application/` | R | `packages/application` | exists |
| 32 | `persistence/` | R | `packages/persistence` | exists |
| 33 | `alembic/` | R | `packages/persistence/alembic` | exists |
| 33 | `alembic.ini` | R | `packages/persistence/alembic.ini` | exists |
| 34 | `agent-runtime/` | P | `packages/agent-runtime` | planned; cannot access |
| 35 | `archive/` | R | `packages/archive` | exists |
| 36 | `prose/` | R | `packages/prose` | exists |
| 37 | `mcp_adapter/` | R | `packages/mcp_adapter` | exists |
| 38 | `python-client/` | P | `packages/python-client` | planned; cannot access |
| 39 | `frontend/` | P | `frontend` | planned (Phase 3, Decision D8); cannot access |
| 40 | `generated-api/` | P | `frontend/generated-api` | planned; cannot access |
| 41 | `tests/` | R | `tests` | exists |
| 41 | `tests/evals/` | R | `tests/evals` | exists |
| 42 | `docs/` | R | `docs` | exists |
| 43 | `pyproject.toml` | R | `pyproject.toml` | exists |
| 44 | `uv.lock` | R | `uv.lock` | exists |
| 45 | `package.json` | P | `package.json` | planned; cannot access |
| 46 | `pnpm-lock.yaml` | P | `pnpm-lock.yaml` | planned; cannot access |
| 52 | `packages/execution-core/src/execution_core/` | R | same | exists |
| 53 | `domain/` | R | `packages/execution-core/src/execution_core/domain` | exists |
| 54 | `state_machine/` | R | `.../execution_core/state_machine` | exists |
| 55 | `policies/` | R | `.../execution_core/policies` | exists |
| 56 | `events/` | R | `.../execution_core/events` | exists |
| 58 | `apps/api/src/coh_api/` | R | same | exists |
| 59 | `api/` | R | `apps/api/src/coh_api/api` | exists |
| 60 | `application/` | R | `apps/api/src/coh_api/application` | exists |
| 61 | `composition.py` | R | `apps/api/src/coh_api/composition.py` | exists |
| 64 | `composition.py` | R | `apps/api/src/coh_api/composition.py` | exists |
| 64 | `packages/persistence` | R | same | exists |
| 64 | `apps/api/src/coh_api/composition.py` | R | same | exists |
| 26, 35 | `HTTP/SSE`, `writer/reader` | X x2 | | slash-joined prose words |
| 49 | `src/` | X | | convention (`src/` layout) |

### packages/execution-core/README.md — Command P: 45 tokens; 37 repository paths (0 missing); 0 planned; 8 not repository paths

The tree root `src/execution_core/` resolves to `packages/execution-core/src/execution_core` (written `<ec>` below).

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 18 | `src/execution_core/` | R | `<ec>` | exists |
| 19 | `domain/` | R | `<ec>/domain` | exists |
| 20-30 | `session.py`, `specification.py`, `task.py`, `evidence.py`, `checkpoint.py`, `decision.py`, `parking_item.py`, `foreground.py`, `commands.py`, `enums.py`, `clock.py` | R x11 | `<ec>/domain/<name>` | all exist |
| 31 | `state_machine/` | R | `<ec>/state_machine` | exists |
| 32 | `lifecycle.py` | R | `<ec>/state_machine/lifecycle.py` | exists |
| 33 | `policies/` | R | `<ec>/policies` | exists |
| 34-39 | `readiness_policy.py`, `foreground_policy.py`, `completion_policy.py`, `parking_policy.py`, `permission_policy.py`, `integrity_policy.py` | R x6 | `<ec>/policies/<name>` | all exist |
| 40 | `events/` | R | `<ec>/events` | exists |
| 41 | `domain_events.py` | R | `<ec>/events/domain_events.py` | exists |
| 52 | `docs/behavioral-contract.md`, `../../docs/behavioral-contract.md` (link text and target) | R x2 | `docs/behavioral-contract.md` | exists |
| 79, 82 | `tests/packages/execution-core` | R x2 | same | exists |
| 85 | `tests/packages/execution-core/test_properties.py` | R | same | exists |
| 124 | `packages/persistence` | R | same | exists |
| 125 | `apps/api` | R | same | exists |
| 129 | `packages/mcp_adapter` | R | same | exists |
| 130 | `packages/archive` | R | same | exists |
| 142 | `pyproject.toml` | R | `pyproject.toml` | exists |
| 142 | `docs/adr/0001-uv-dev-dependency-group.md` | R | same | exists |
| 146 | `docs/coding-rules.md`, `docs/behavioral-contract.md` | R x2 | same | exist |
| 21, 48, 50, 50, 92, 133, 147 | `WHAT/WHY/DELIVERABLE/DONE`, `Verified/Done`, `Inspection/spec/plan`, `large/destructive`, `I/O`, `Focus/Recovery`, `before/alongside` | X x7 | | slash-joined prose words |
| 130 | `.coh/archive/` | X | | runtime path |

### packages/persistence/README.md — Command P: 27 tokens; 19 repository paths (0 missing); 0 planned; 8 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 13-17 | `models.py`, `mappers.py`, `repositories.py`, `unit_of_work.py`, `database.py` | R x5 | `packages/persistence/src/persistence/infrastructure/<name>` (the Architecture list) | all exist |
| 25 | `packages/persistence/` | R | `packages/persistence` | exists |
| 25 | `alembic.ini` | R | `packages/persistence/alembic.ini` | exists |
| 25 | `alembic/` | R | `packages/persistence/alembic` | exists |
| 26 | `packages/persistence` | R | same | exists |
| 31 | `alembic.ini` | R | `packages/persistence/alembic.ini` | exists |
| 31 | `alembic/env.py` | R | `packages/persistence/alembic/env.py` | exists |
| 31 | `handlers.py` | R | `packages/mcp_adapter/src/coh_mcp/handlers.py` | exists |
| 31 | `composition.py` | R | `apps/api/src/coh_api/composition.py` | exists |
| 105 | `tests/packages/persistence` | R | same | exists |
| 108 | `tests/packages/persistence/test_crash_restart.py` | R | same | exists |
| 111 | `test_crash_restart.py` | R | `tests/packages/persistence/test_crash_restart.py` | exists |
| 133 | `packages/archive` | R | same | exists |
| 134 | `apps/api` | R | same | exists |
| 136 | `packages/mcp_adapter` | R | same | exists |
| 31, 31, 31, 31, 45, 133 | `///.coh/coh.db`, `.coh/`, `packages/persistence/.coh/coh.db`, `.coh/coh.db`, `///.coh/coh.db`, `.coh/archive/` | X x6 | | runtime path (created by a run, never committed) |
| 107, 111 | `crash/restart` | X x2 | | slash-joined prose words |

### packages/archive/README.md — Command P: 23 tokens; 11 repository paths (0 missing); 0 planned; 12 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 145 | `checkpoint.py` ("execution-core checkpoint.py") | R | `packages/execution-core/src/execution_core/domain/checkpoint.py` | exists |
| 173-176 | `test_paths.py`, `test_markdown.py`, `test_service.py`, `test_integration.py` | R x4 | `tests/packages/archive/<name>` (the Testing list) | all exist |
| 181, 187 | `tests/packages/archive` | R x2 | same | exists |
| 192 | `packages/mcp_adapter/src/coh_mcp/archive_wiring.py` | R | same | exists |
| 192 | `handlers.py` | R | `packages/mcp_adapter/src/coh_mcp/handlers.py` | exists |
| 192 | `archive_wiring.py` | R | `packages/mcp_adapter/src/coh_mcp/archive_wiring.py` | exists |
| 193 | `packages/mcp_adapter/src/coh_mcp/archive_wiring.py` | R | same | exists |
| 17, 72 | `-part-N.md` | X x2 | | placeholder (filename pattern) |
| 37 | `/path/to/project` | X | | placeholder |
| 40, 113 | `.coh/archive` | X x2 | | runtime path |
| 173, 176, 192, 195, 201, 202, 204 | `filename/ID`, `I-04/I-12`, `user/agent`, `YAML/TOML`, `search/indexing`, `Redaction/secret`, `sync/collaboration` | X x7 | | slash-joined prose words |

### packages/prose/README.md — Command P: 10 tokens; 9 repository paths (0 missing); 0 planned; 1 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 3 | `docs/behavioral-contract.md`, `../../docs/behavioral-contract.md` (link text and target) | R x2 | `docs/behavioral-contract.md` | exists |
| 5 | `packages/prose/src/coh_prose/` | R | `packages/prose/src/coh_prose` | exists |
| 5 | `policy.py`, `renderer.py`, `__init__.py` | R x3 | `packages/prose/src/coh_prose/<name>` | all exist |
| 20 | `__init__.py` | R | `packages/prose/src/coh_prose/__init__.py` | exists |
| 25 | `packages/mcp_adapter/src/coh_mcp/handlers.py` | R | same | exists |
| 55 | `tests/packages/prose` | R | same | exists |
| 11 | `WHAT/WHY/DELIVERABLE/DONE` | X | | slash-joined prose words |

### packages/mcp_adapter/README.md — Command P: 22 tokens; 6 repository paths (0 missing); 0 planned; 16 not repository paths

This file is unchanged (D-10).

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 82 | `src/coh_mcp/handlers.py` | R | `packages/mcp_adapter/src/coh_mcp/handlers.py` | exists |
| 92 | `src/coh_mcp/archive_wiring.py` | R | `packages/mcp_adapter/src/coh_mcp/archive_wiring.py` | exists |
| 108, 111 | `tests/packages/mcp_adapter` | R x2 | same | exists |
| 111 | `packages/mcp_adapter/src` | R | same | exists |
| 123 | `apps/api` | R | same | exists |
| 21, 39 | `/path/to/coh` | X x2 | | placeholder |
| 29 | `~/.config/claude/mcp.json` | X | | host path outside the repository (F-5) |
| 90, 124, 130, 158 | `.coh/coh.db` | X x4 | | runtime path |
| 5, 14, 47, 58, 58, 122, 126, 133, 135 | `archive/checkpoint`, `User/agent/tool`, `names/args`, `Confirm/correct`, `T4/T5`, `HTTP/SSE`, `P-02/P-05`, `HTTP/SSE`, `P-02/P-05` | X x9 | | slash-joined prose words |

### packages/application/README.md — Command P: 20 tokens; 7 repository paths (0 missing); 0 planned; 13 not repository paths

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 101, 104 | `tests/packages/application` | R x2 | same | exists |
| 104 | `packages/application/src` | R | same | exists |
| 127 | `apps/api` | R | same | exists |
| 127 | `apps/api/src/coh_api/api/routes/spec_gate.py` | R | same | exists |
| 127 | `foreground.py` | R | `apps/api/src/coh_api/api/routes/foreground.py` | exists |
| 131 | `packages/mcp_adapter/src/coh_mcp/server.py` | R | same | exists |
| 18 | `/path/to/coh` | X | | placeholder |
| 32, 92 | `///.coh/coh.db`, `.coh/coh.db` | X x2 | | runtime path |
| 86 | `/` | X | | separator in "SpecGateService / ForegroundService" |
| 13, 44, 95, 108, 108, 109, 113, 117, 123 | `complete/block/park/interrupt`, `login/logout`, `readiness/foreground`, `WHAT/WHY/DELIVERABLE/DONE`, `unknowns/assumptions`, `complete/block/park/interrupt`, `HTTP/SSE`, `session/spec/checkpoint`, `interrupting/completing/blocking` | X x9 | | slash-joined prose words |

### apps/api/README.md — Command P: 68 tokens; 25 repository paths (0 missing); 0 planned; 43 not repository paths

The tree root is `apps/api/src/coh_api/` (written `<api>` below).

| Line | Token | Class | Resolved path | Result |
|---|---|---|---|---|
| 12 | `apps/api/src/coh_api/` | R | `<api>` | exists |
| 13 | `api/` | R | `<api>/api` | exists |
| 14 | `routes/` | R | `<api>/api/routes` | exists |
| 15, 16 | `spec_gate.py`, `foreground.py` | R x2 | `<api>/api/routes/<name>` | exist |
| 17 | `schemas/` | R | `<api>/api/schemas` | exists |
| 18-20 | `common.py`, `spec_gate.py`, `foreground.py` | R x3 | `<api>/api/schemas/<name>` | all exist |
| 21 | `application/` | R | `<api>/application` | exists |
| 21, 22 | `composition.py` | R x2 | `<api>/composition.py` | exists |
| 23 | `main.py` | R | `<api>/main.py` | exists |
| 89, 95 | `tests/apps/api` | R x2 | same | exists |
| 95 | `apps/api/src` | R | same | exists |
| 174 | `composition.py` | R | `<api>/composition.py` | exists |
| 201, 207, 215 | `apps/api` | R x3 | same | exists |
| 212 | `CONTRIBUTING.md` | R | same | exists |
| 212 | `apps/api.` (sentence period included) | R | `apps/api` | exists |
| 220 | `AGENTS.md`, `docs/coding-rules.md`, `docs/decision-log.md` | R x3 | same | all exist |
| 57, 136 | `.coh/coh.db` | X x2 | | runtime path |
| 59, 61, 67, 70, 81 (2 each) | `//localhost`, then `8000/docs`, `8000/health`, `8000/api/v1/...` | X x10 | | URL |
| 108-112, 116-121, 125 | `/api/v1/spec-gate/...` (5), `/api/v1/foreground/...` (6), `/health` | X x12 | | HTTP route |
| 71 | `application/json` | X | | media type |
| 19, 20, 31, 55, 76, 100, 132, 134, 139, 149, 157, 158, 158, 164, 167, 168, 189, 193 | `request/response` (x4), `container/VM`, `login/logout`, `NOW/NEXT` (x2), `lint/format` (x2), `Docker/Redis/cloud`, `Checkpoint/Recovery` (x2), `Verification/completion`, `VERIFY/COMPLETE`, `Redis/SQLite`, `inspection/verification`, `input/output` | X x18 | | slash-joined prose words. Line 168 says planned, but `inspection/verification` names no path, so it is X, not P |

Totals over the nine texts: 307 tokens; 193 repository paths, 0 missing; 8 planned, all in the coding-rules section; 106 not repository paths.

## Prose README snippet output (H-87)

`uv run --no-sync --directory <worktree> python -c "from coh_prose import ProsePolicy, ProseRenderer, SpecProposal; spec = SpecProposal(inspection_findings='Inspection: the export command writes no header row.', what='Add a header row to the CSV export', why='Downstream imports expect column names', deliverable='CSV export with a header row', done_when=['The first line of the export lists the column names'], clarity='high', readiness='ready'); print(ProseRenderer().render_spec_proposal(spec)); print(ProsePolicy().validate_no_scaffolding('There are three things to cover.'))"`

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

## Follow-ups (not edited)

- F-1 `packages/execution-core/README.md`, Usage snippet: it calls the instance method `transition_to_specify` on the class and omits its required `command` argument (`state_machine/lifecycle.py:96-101`). As written it raises TypeError. Found by reading; not run.
- F-2 `packages/application/README.md:113` (Trade-offs) calls FastAPI integration "the next layer (Phase 2)"; `apps/api` exists. D-08 covers Next Actions only.
- F-3 `apps/api/README.md:7` (Status) calls MCP tools calling these services "a later slice", yet `packages/mcp_adapter/src/coh_mcp/handlers.py` imports both services and calls them.
- F-4 `docs/coding-rules.md:26` describes `apps/api/` as "HTTP/SSE transport", but no SSE route exists. That is a component claim, not a path.
- F-5 `packages/mcp_adapter/README.md:29` names a host MCP config path outside the repository; it was not verified (and the file is D-10).
- F-6 `packages/persistence/alembic/env.py:35` hard-codes `sqlite:///.coh/coh.db` relative to the working directory and overrides any configured URL. Migrations therefore cannot target the database the adapters open (runs R1-R3). `.coh/` is also not gitignored outside `apps/api/`.
- F-7 `packages/execution-core/README.md`, Contributing: `uv run pytest tests` measures no coverage, while the 90% gate lives in `ci.yml`.
- F-8 The tool-lifecycle archive path has no caller: `archive_tool_invocation` in `packages/mcp_adapter/src/coh_mcp/archive_wiring.py:122` is never called from `handlers.py`. That is a code gap; the archive README keeps it open.
- F-9 Once the lead appends the certifi entry after merge (D-06), the D1-D15 ranges in `README.md` will be stale by one entry and need D1-D16.
- D-10 defect: `apps/api/README.md:57` says the database is "auto-created on first run"; unchanged on purpose.
- D-10 defect: `packages/mcp_adapter/README.md:79-98`, the architecture diagram; unchanged on purpose.

## Not checked

- GitHub rendering of the READMEs (links, tables, the D-11 nested code fences) was not viewed.
- No Usage snippet other than the prose one was run. F-1 came from reading.
- Claims other than paths, the D-08 and D-09 items and the prose README facts were not re-verified.
- Alembic against a database that `create_all` already populated was not exercised.
- CI on the PR head is UNKNOWN until it runs.
