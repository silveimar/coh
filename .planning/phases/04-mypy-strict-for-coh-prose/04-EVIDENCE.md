# Phase 04 evidence (H-87)

`<worktree>` is the slice worktree `coh-wt/04-mypy-strict-for-coh-prose`; `<scratch>` is a directory outside it. Each command ran as one Bash call; output is verbatim unless marked.

## Baseline (origin/main f33c7cb plus lead commits 0b49391 and 3fe150b, before builder edits)

The plan was written at origin/main 558b147 with lead commit 5a92ccf. The lead rebased the branch onto f33c7cb (D16 on main) before dispatch: the checks commit is now 0b49391 and the plan commit 3fe150b (queue row qitem-20261022132048-f50750f278382119). PC1, PC2 and PC10 are compared with the row's values; every other planner value is unchanged.

Every diff gate uses `origin/main` in place of `main`: the local `main` ref is stale at 378d9ed (plan finding 2).

PC1 `git -C <worktree> rev-parse origin/main`

```text
f33c7cbfccbd253755b778caf2589c01f6970641
```

PC2 `git -C <worktree> log --format="%h %ae %s" origin/main..HEAD`

```text
3fe150b lead-seat@coh-fleet.invalid docs(planning): Phase 4 plan, mypy strict for coh_prose (TYPE-03)
0b49391 lead-seat@coh-fleet.invalid ci: mypy strict step for coh_prose (TYPE-03 checks)
```

PC3 `git -C <worktree> diff --name-only origin/main...HEAD`

```text
.github/workflows/ci.yml
.planning/phases/04-mypy-strict-for-coh-prose/04-01-PLAN.md
```

PC4 `git -C <worktree> diff --numstat origin/main...HEAD -- .github/workflows/ci.yml`

```text
5	0	.github/workflows/ci.yml
```

PC5 `grep -n "mypy --strict packages/prose/src/coh_prose" <worktree>/.github/workflows/ci.yml`

```text
44:        run: uv run mypy --strict packages/prose/src/coh_prose
```

PC6 `grep -c "on-error" <worktree>/.github/workflows/ci.yml` (exit 1 at count 0, the pass state)

```text
0
```

PC7 `ls <worktree>/docs/adr`

```text
0000-template.md
0001-uv-dev-dependency-group.md
README.md
```

PC8 `gh pr list --repo silveimar/coh --state open --json number,headRefName,files --jq '.[] | select(any(.files[]; .path | startswith("docs/adr/"))) | .number'` (`--repo` added because the seat's shell is not inside the worktree)

```text
(no output)
```

PC9 `git -C <worktree> status --porcelain --untracked-files=all`

```text
(no output)
```

PC10 `grep -c "^## D16" <worktree>/docs/decision-log.md`

```text
1
```

PC10 prints 1 (planner value 0, before the rebase), so the ADR cites D16 directly (plan finding 3).

B0 `uv sync --directory <worktree> --all-packages --locked`

```text
Resolved 68 packages in 0.79ms
Checked 64 packages in 0.31ms
```

B1 `uv run --no-sync --directory <worktree> pyright packages/prose`

```text
0 errors, 0 warnings, 0 informations
```

B2 `uv run --no-sync --directory <worktree> pytest tests/packages/prose -q`

```text
....................................                                     [100%]
36 passed in 0.08s
```

B3 `grep -nE "ignore_errors|disable_error_code|follow_imports|ignore_missing_imports|tool\.mypy\.overrides|plugins" <worktree>/pyproject.toml <worktree>/packages/prose/pyproject.toml` (exit 1)

```text
(no output)
```

B4 `grep -c '^name = "mypy"' <worktree>/uv.lock`

```text
0
```

B5 `grep -n -A1 -E '^name = "(typing-extensions|mypy|mypy-extensions|pathspec|librt|ast-serialize)"' <worktree>/uv.lock`

```text
1038:name = "typing-extensions"
1039-version = "4.16.0"
```

B6 `grep -c -E '^\[tool\.mypy' <worktree>/pyproject.toml`

```text
0
```

B7 `uv --version`

```text
uv 0.13.0 (x86_64-unknown-linux-gnu)
```

All PC and B values match the planner values, apart from the rebase SHAs and PC10 noted above.

## Task 1 (D-03a, scratch)

The verbatim output of V2-V13 is in `docs/adr/0002-mypy-strict-for-coh-prose.md`, "Appendix: D-03a verification output". Exit codes:

| Step | Command (short) | Exit | Result |
|---|---|---|---|
| V1 | `mkdir -p <scratch>/mypy-adr` | 0 | |
| V2 | `uv venv --no-project --no-config --python 3.15 ...` | 0 | CPython 3.15.0 |
| V3 | `uv pip install --no-config --no-cache --no-build --strict ... mypy` | 0 | 6 packages from wheels; mypy 2.4.0. V3b not needed |
| V4 | `uv pip list ...` | 0 | ast-serialize 0.13.1, librt 0.16.0, mypy 2.4.0, mypy-extensions 1.1.0, pathspec 1.1.1, typing-extensions 4.16.0 |
| V5 | `python --version` | 0 | Python 3.15.0 |
| V6 | `grep ... WHEEL` | 0 | cp315-cp315 (mypy, librt), cp315-abi3 (ast-serialize), py3-none-any (others) |
| V7 | `grep ... METADATA`, then license files | 0 | MIT x4, MPL-2.0 (pathspec), PSF-2.0 (typing-extensions, already locked) |
| V8 | `mypy --version` | 0 | `mypy 2.4.0 (compiled: yes)` |
| V9 | `mypy --strict --python-version 3.15 -c ...` | 0 | Success, 1 source file |
| V10 | `mypy --config-file probe-config.toml -c <typed def>` | 0 | Success; no python_version complaint |
| V11 | `mypy --config-file probe-config.toml -c <untyped def>` | 1 | `no-untyped-def`, as expected |
| V12 | `mypy --config-file probe-config.toml ... <worktree>/packages/prose/src/coh_prose` | 0 | `Success: no issues found in 3 source files` |
| V13 | `grep -n -A1 ... <worktree>/uv.lock` | 0 | only typing-extensions 4.16.0 already locked |

V14 `git -C <worktree> status --porcelain --untracked-files=all`, after V1-V13:

```text
(no output)
```

Every V-step cache and venv sat under `<scratch>`; the worktree stayed clean.

Stop rules:

- S1 (D13 reopen): did not fire. V3 installed every package from a published wheel with `--no-build --no-cache`.
- S2 (license): fired for pathspec 1.1.1 (MPL-2.0, new to the lock). The lead's dispatch row (decision 1) says license findings go up in the Proposed ADR as an owner question, so the ADR carries it as Q2, with the lead's recommended default, and Task 1 continued to its commit.
- mypy-extensions: the planner's PyPI pre-read showed no license field. The installed 1.1.0 wheel declares `License-Expression: MIT`, and its license file line 1 says MIT. It is on the allowed list; no owner question.
- typing-extensions (PSF-2.0) is already locked at the same version, so it is not a new package and S2 does not apply to it.

### Task 1 gates

Deviation, lead instruction 13:27Z on the phase row: calling the scratch venv's binary by path (`<scratch>/mypy-adr/venv/bin/mypy`) is not allowlisted and raises a permission prompt. The lead declined that prompt for the probe gate. Every later scratch mypy call runs through `uv run --no-project --python 3.15 --with mypy==2.4.0 mypy ...` with the same arguments. V8-V12 above ran earlier through the venv binary; the wheel-only install (V3) stays the D-03a evidence.

`grep -c -x -E '## (Question|Context|Options considered|Decision|Consequences|Compliance checklist|Reopen when|References)' <worktree>/docs/adr/0002-mypy-strict-for-coh-prose.md`

```text
8
```

`grep -c -F '**Status:** Proposed' <worktree>/docs/adr/0002-mypy-strict-for-coh-prose.md`

```text
1
```

`grep -c -F '| [0002](0002-mypy-strict-for-coh-prose.md) |' <worktree>/docs/adr/README.md`

```text
1
```

`uv run --no-project --python 3.15 --with mypy==2.4.0 mypy --config-file <scratch>/mypy-adr/probe-config.toml --cache-dir <scratch>/mypy-adr/cache -c 'def add(a: int, b: int) -> int: return a + b'` (exit 0)

```text
Downloading ast-serialize (1.2MiB)
Downloading mypy (14.7MiB)
 Downloaded ast-serialize
 Downloaded mypy
Installed 6 packages in 7ms
Success: no issues found in 1 source file
```

Dependency table rows, `grep -c -E '^\| (mypy|ast-serialize|librt|mypy-extensions|pathspec|typing-extensions) \|' <worktree>/docs/adr/0002-mypy-strict-for-coh-prose.md`

```text
6
```

Appendix and owner-questions headings, `grep -c -F -e '## Appendix: D-03a verification output' -e '### Owner decisions needed' <worktree>/docs/adr/0002-mypy-strict-for-coh-prose.md`

```text
2
```

The host-path gate (`/(home|tmp)/`) and the checks-guard token self-scan print 0 for the ADR, the ADR index and this file. They run again after this edit, before the commit.
