---
phase: 03-dependency-audit-job
plan: 01
requirements: [SUPP-01]
status: complete
key_files:
  created:
    - docs/adr/0003-dependency-audit-deptry-pip-audit.md
    - .planning/phases/03-dependency-audit-job/03-EVIDENCE.md
    - .planning/phases/03-dependency-audit-job/03-VERIFICATION.md
    - .planning/phases/03-dependency-audit-job/03-01-SUMMARY.md
  modified:
    - docs/adr/README.md
    - pyproject.toml
    - uv.lock
    - packages/archive/pyproject.toml
    - packages/execution-core/pyproject.toml
    - packages/persistence/pyproject.toml
    - packages/prose/pyproject.toml
    - packages/mcp_adapter/pyproject.toml
    - packages/application/pyproject.toml
    - apps/api/pyproject.toml
---

# Phase 03 Plan 01: deptry and pip-audit in CI (summary)

On the committed tree, deptry 0.25.1 exits 0 on all 7 workspace members (archive 5, execution-core 24, persistence 11, prose 3, mcp_adapter 6, application 3, apps/api 12 files scanned). pip-audit 2.10.1 (`--strict --disable-pip`) exits 0 on the hashed lock export with `No known vulnerabilities found`. Both bite: deptry exits 1 with DEP002 on a scratch copy of prose with a seeded unused `sqlalchemy`, and pip-audit exits 1 on `requests==2.19.1` (10 known vulnerabilities). The application, api and mcp_adapter tests stay at 27, 9 and 39 passed; ruff check and format pass.

## Base and commits

The base is origin/main 2215cd8 (PR #38's merge). Local `main` is stale, so every diff gate uses `origin/main` (plan finding 2). The planner measured on #38's head tree 1b1237e; the lead confirmed 2215cd8's tree equals it, and the re-measured baselines matched (finding 1).

| Commit | Author seat | What |
|---|---|---|
| 6fa1cee | lead | Plan |
| 02105fb | lead | CI jobs `deptry` and `pip-audit` (+131/-0) |
| 2c6a1e4 | builder | ADR-0003 Proposed, index row, Task 1 evidence |
| d92220a | lead | D18 (PSF-2.0, CI-only), README D1-D18 |
| d3e8da0 | builder | ADR-0003 Accepted |
| 73a48ba | builder | `deptry>=0.25.1` in the root dev group, uv.lock |
| 67d62d8 | builder | Per-member deptry config and the D-04 split, uv.lock |
| ca26cc3 | builder | Task 4 evidence |

The commit carrying this summary follows them.

## Tools, closures and owner answers

- deptry 0.25.1 (MIT) in the root dev group, floor equal to the locked version. New in the lock: deptry 0.25.1 and requirements-parser 0.13.1 (Apache-2.0); click and packaging were already locked.
- pip-audit 2.10.1 (Apache-2.0) runs through `uvx --python 3.13`; its 28-package closure is not locked.
- Licenses and wheel tags for both closures: ADR-0003 Tables 1 and 2. Every package installed from a wheel (`--no-build --no-cache`); pip-audit's closure also installs on CPython 3.15.
- Owner answers (queue row qitem-20261022162351-9cad306d): Q1 and Q2 accept. Q3 approve defusedxml and pip's vendored distlib under PSF-2.0, CI-only; the lead recorded it as D18 (d92220a). Q4 confirm D16 covers certifi in the closure and vendored in pip. Q5 accept the marker-only gap; reopen if COH supports Windows.

## D-04, D-06 and the bites

- **D-04:** the five findings are resolved.
  - application declares `sqlalchemy>=2.0.0` and drops `coh-archive`, with its source line.
  - apps/api drops `execution-core`.
  - Two commented ignores: DEP002 `uvicorn` in apps/api (a command-line server that no module imports), and DEP003 `sqlalchemy` in mcp_adapter (the layer violation in `handlers.py`; remove it when that is fixed).
  - No other deptry key.
- **D-06:** pip-audit drops marker-excluded lines instead of skipping them. 62 dependencies audited, 0 skipped; a marker-only file exits 0. No exclusions needed; colorama, pywin32 and httpx2-jsfetch are not audited on Linux.
- **Lock:** against origin/main, `uv.lock` adds exactly deptry and requirements-parser, deletes only the 4 coh-archive and execution-core member-metadata lines, deletes no version line; `uv lock --check` exits 0.

## Deviations

- V7's METADATA grep was narrowed to `License:` and `License-Expression`, because the planned `License` alternative also matched every `License-File` line (32 KB). A version piped through `sed` raised a permission prompt; the lead declined it and asked for the bare grep, with paths shortened only in the evidence file.
- D2 counted 10 marker lines, not the planner's 9. The 3 that are false on Linux are the planned ones.
- V7b printed 20 vendored license files: 18 components, with packaging shipping 3.
- `README.md` and `docs/decision-log.md` differ from origin/main through lead commit d92220a; the resume row allows both paths in the file gates.
- `gh` calls use `--repo <repo>`, because the seat's shell is not inside the worktree.

## Choices not dictated by the spec

1. ADR number, slug and title: 0003, `0003-dependency-audit-deptry-pip-audit.md`, "Check dependencies in CI with deptry and pip-audit".
2. The tracer was a scratch copy of HEAD carrying the full config, because D-07 forbade touching the worktree's dependencies before acceptance.
3. deptry was added pinned (`==0.25.1`) and relaxed to `>=0.25.1`, so the floor equals the locked, verified version.
4. application declares `sqlalchemy>=2.0.0`, the specifier persistence already uses; the lock keeps 2.0.52.
5. application's now-unused `coh-archive` source line is removed (L2).
6. `package_module_name_map` appears only in the two members that declare `prose` or `application` (L4).
7. The comment wording of the two ignores.
8. Builder exports add `--no-header --quiet`; CI uses D-05's command.
9. `origin/main` replaces the stale local `main` in criterion 2's `git log` and every diff gate.
10. The deptry bite seeds `sqlalchemy>=2.0.0` into a scratch copy of the built `packages/prose`.
11. Evidence file `03-EVIDENCE.md`; PR title `chore(deps): deptry and pip-audit in CI (SUPP-01)`.
12. Docs that name neither tool are not edited: `CONTRIBUTING.md:50`, `:55`; `README.md:50`; `AGENTS.md:41`.

Lead defaults L1-L13: confirmed unchanged by the lead on the dispatch and resume rows.

## Follow-ups

- Docs that name neither tool: `CONTRIBUTING.md:50`, `:55`; `README.md:50`; `AGENTS.md:41`.
- The mcp_adapter layer violation; fixing it removes the DEP003 ignore.
- checks-guard rules for deptry and pip-audit weakening: an Ask.
- Required status checks for the two jobs: the owner's ruleset.
- The D-06 gap (the 3 marker-only pins); reopen if COH supports Windows.
- The CULTURE.md exception for a pip-audit-only red on `main`, through the retro PR.
- typing-extensions (PSF-2.0) in `uv.lock` has no decision-log entry; the owner left it open outside this phase.

## Not covered

- CI on 43a4a0d: deptry, pip-audit, Lint and Test, gitleaks and checks-guard pass; checks-edits waits for the owner's checks-approval environment (03-VERIFICATION.md criterion 6).
- pip-audit's closure on other days, the win32 and emscripten marker sets, other platforms' wheels, and an unreachable vulnerability service.
