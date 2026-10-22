---
phase: 04-mypy-strict-for-coh-prose
plan: 01
requirements: [TYPE-03]
status: complete
key_files:
  created:
    - docs/adr/0002-mypy-strict-for-coh-prose.md
    - .planning/phases/04-mypy-strict-for-coh-prose/04-EVIDENCE.md
    - .planning/phases/04-mypy-strict-for-coh-prose/04-VERIFICATION.md
    - .planning/phases/04-mypy-strict-for-coh-prose/04-01-SUMMARY.md
  modified:
    - docs/adr/README.md
    - pyproject.toml
    - uv.lock
---

# Phase 04 Plan 01: mypy strict for coh_prose (summary)

`uv run mypy --strict packages/prose/src/coh_prose` prints `Success: no issues found in 3 source files` with no source change. With an untyped `def` appended to `policy.py`, it exits 1 with `[no-untyped-def]` and `Found 1 error in 1 file (checked 3 source files)`. pyright stays at `0 errors, 0 warnings, 0 informations`, and the prose tests at `36 passed`.

## Base and commits

The base is origin/main f33c7cb. The plan was written at 558b147 with lead commit 5a92ccf; the lead rebased before dispatch, which made the checks commit 0b49391 and the plan commit 3fe150b.

| Commit | Author seat | What |
|---|---|---|
| 0b49391 | lead | CI step `Run mypy strict (coh_prose)` (+5/-0) |
| 3fe150b | lead | Plan |
| ff77e91 | builder | ADR-0002 Proposed, index row, Task 1 evidence |
| a1c9e12 | lead | D17 (pathspec under MPL-2.0), README D1-D17 |
| fde02e0 | builder | ADR-0002 Accepted |
| baaff7c | builder | `mypy>=2.4.0` in the root dev group, `[tool.mypy]`, uv.lock |
| 2bb00cc | builder | Task 4 evidence |

The commit carrying this summary follows them. Every diff gate uses `origin/main`, because local `main` is stale at 378d9ed.

## Dependency

- **Version:** mypy 2.4.0, with the floor `>=2.4.0` equal to the locked version.
- **New lock packages:** ast-serialize 0.13.1, librt 0.16.0, mypy 2.4.0, mypy-extensions 1.1.0 and pathspec 1.1.1. typing-extensions stays at 4.16.0. Licenses and wheel tags are in ADR-0002's table and appendix.
- **Wheels:** every package installed from a wheel on CPython 3.15.0 (`--no-build --no-cache`).
- **Owner answers** (row qitem-20261022141325-97bd7544): Q1 accept; Q2 approve pathspec under MPL-2.0 for dev-only use. The lead recorded Q2 as D17.
- **Config:** `python_version = "3.15"` is kept, because mypy 2.4.0 accepts it.

## Source changes

None. The coh_prose diff against origin/main is empty.

## Deviations

- The lead rebased the branch before dispatch, so PC1, PC2 and PC10 were checked against the row's SHAs. PC10 printed 1, so the ADR cites D16 directly.
- Scratch mypy calls go through `uv run --no-project --python 3.15 --with mypy==2.4.0` (lead instruction, 13:27Z). Calling the scratch venv's binary by path raised a permission prompt. V8-V12 ran before the instruction, through the venv binary.
- mypy-extensions is not a license question. The planner's PyPI pre-read showed no license field, but the installed 1.1.0 wheel declares `License-Expression: MIT`, and its license file says MIT.
- `.mypy_cache/` appears at the worktree root after each mypy run. `git status` does not show it, because the cache writes its own catch-all `.gitignore`. It was removed with `rm -r` before every handoff, per the dispatch rule.
- PC8 ran with `--repo silveimar/coh`, because the seat's shell is not inside the worktree.
- `README.md` and `docs/decision-log.md` differ from origin/main through lead commit a1c9e12. The resume row allows both paths in the file gates.

## Choices not dictated by the spec

1. D-09 gap: the docs name pyright as the only type checker, and this phase does not edit them. Sites:
   - `CONTRIBUTING.md:46`, `:54`, `:63`
   - `docs/coding-rules.md:69`, `:90`, `:192`, `:208`
   - `AGENTS.md:37`, `:41`
2. `README.md:49-50` lists the dev-group tools and does not name mypy. It is outside the CONTEXT scope.
3. ADR number, slug and title: 0002, `0002-mypy-strict-for-coh-prose.md`.
4. The dependency was added pinned (`mypy==2.4.0`) and then relaxed to `>=2.4.0`. The floor therefore equals the locked and verified version.
5. `--no-build --no-cache` proves the wheel-only install. `py3-none-any` and `cp315-abi3` wheels both count.
6. The D-06 config ran against the real coh_prose tree in scratch (V12) before the ADR was written.
7. The evidence file is `04-EVIDENCE.md`, and the PR title is `chore(prose): mypy strict for coh_prose in CI (TYPE-03)`.
8. `origin/main` replaces the stale local `main` in criterion 4 and every diff gate.
9. The tracer was the scratch end-to-end run, because D-04 forbade touching the dependency before acceptance.

## Follow-ups

- The D-09 docs gap (sites above).
- `README.md:49-50`: add mypy to the listed dev tools.
- checks-guard tokens for mypy-weakening config: an Ask, as a separate checks change.
- mypy beyond coh_prose: deferred.
- `renderer.py:281-303`: renders "None fails" when no criterion fails. Deferred.
- `.mypy_cache/` is not in the root `.gitignore`. It stays hidden only through mypy's own inner `.gitignore`. Adding it to the root `.gitignore` is outside this phase's files.

## Not covered

- CI on the head: UNKNOWN until the PR run completes.
- Wheels on platforms other than linux x86_64.
- mypy on tests or other packages.
