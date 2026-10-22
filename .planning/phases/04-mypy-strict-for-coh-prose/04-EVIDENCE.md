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

## Task 4 (build)

Resume signal: queue row qitem-20261022141325-97bd7544 from lead-lead@coh. The owner's answers were Q1 accept and Q2 approve; the lead recorded Q2 as D17 in lead-seat commit a1c9e12 (`docs/decision-log.md` D17, and `README.md` D1-D17). `git -C <worktree> pull --ff-only` printed `Already up to date.`, with head a1c9e12.

Step A: ADR-0002 set to Accepted (Deciders, Slice / PR #38, Decision log D17, the dependency checklist line ticked, the owner answers recorded) and the index row set to Accepted. Commit fde02e0 `docs(adr): accept ADR-0002 (owner decision qitem-20261022141325-97bd7544)`.

Step B, the dependency.

`uv add --directory <worktree> --dev --no-sync "mypy==2.4.0"` (exit 0)

```text
Resolved 73 packages in 268ms
```

The Edit tool then changed the dev-group line `"mypy==2.4.0",` to `"mypy>=2.4.0",`. uv placed it between hypothesis and pyright.

`uv lock --directory <worktree>` (exit 0)

```text
Resolved 73 packages in 5ms
```

Step C: the Edit tool appended the D-06 table after `[tool.pyright]`, with one blank line before it. `python_version` is kept (ADR-0002, V10).

Step B and C gates:

`uv lock --check --directory <worktree>` (exit 0)

```text
Resolved 73 packages in 0.77ms
```

`grep -c '^name = "mypy"' <worktree>/uv.lock`

```text
1
```

`grep -n -A1 '^name = "mypy"' <worktree>/uv.lock`

```text
749:name = "mypy"
750-version = "2.4.0"
```

`grep -n -F '"mypy>=' <worktree>/pyproject.toml`

```text
12:    "mypy>=2.4.0",
```

New lock packages, `git -C <worktree> diff origin/main -- uv.lock` filtered with `grep -E '^\+name = '`. The diff went to a file first because its output was too large, so this was two commands.

```text
+name = "ast-serialize"
+name = "librt"
+name = "mypy"
+name = "mypy-extensions"
+name = "pathspec"
```

These are the five new packages in ADR-0002's table. typing-extensions stays at 4.16.0.

`git -C <worktree> diff --numstat origin/main -- pyproject.toml uv.lock` (working tree before the commit; zero deletions)

```text
5	0	pyproject.toml
133	0	uv.lock
```

`grep -n -A 3 -F '[tool.mypy]' <worktree>/pyproject.toml`

```text
59:[tool.mypy]
60-strict = true
61-python_version = "3.15"
```

Criterion 5, `grep -nE "ignore_errors|disable_error_code|follow_imports|ignore_missing_imports|tool\.mypy\.overrides|plugins" <worktree>/pyproject.toml <worktree>/packages/prose/pyproject.toml` (exit 1)

```text
(no output)
```

Step D.

`uv sync --directory <worktree> --all-packages --locked` (exit 0)

```text
Resolved 73 packages in 0.78ms
Installed 5 packages in 8ms
 + ast-serialize==0.13.1
 + librt==0.16.0
 + mypy==2.4.0
 + mypy-extensions==1.1.0
 + pathspec==1.1.1
```

The CI command, `uv run --no-sync --directory <worktree> mypy --strict packages/prose/src/coh_prose` (exit 0)

```text
Success: no issues found in 3 source files
```

No coh_prose change was needed (D-08).

`uv run --no-sync --directory <worktree> pyright packages/prose` (exit 0)

```text
0 errors, 0 warnings, 0 informations
```

`uv run --no-sync --directory <worktree> pytest tests/packages/prose -q` (exit 0)

```text
....................................                                     [100%]
36 passed in 0.08s
```

`uv run --no-sync --directory <worktree> ruff check .` (exit 0)

```text
All checks passed!
```

`uv run --no-sync --directory <worktree> ruff format --check .` (exit 0)

```text
188 files already formatted
```

Step E: commit baaff7c `build(deps): add mypy 2.4.0 to the root dev group with strict config (ADR-0002, TYPE-03)`, with `pyproject.toml` and `uv.lock` only. There was no source commit.

Step F, the bite proof on the committed tree. The Edit tool appended an untyped function to `policy.py`. `git -C <worktree> diff -- packages/prose/src/coh_prose/policy.py`:

```text
@@ -266,3 +266,7 @@ class ProsePolicy:
             violations=all_violations,
             warnings=all_warnings,
         )
+
+
+def _bite_probe(value):
+    return value
```

`uv run --no-sync --directory <worktree> mypy --strict packages/prose/src/coh_prose` (exit 1)

```text
packages/prose/src/coh_prose/policy.py:271: error: Function is missing a type annotation  [no-untyped-def]
Found 1 error in 1 file (checked 3 source files)
```

The Edit tool then removed the four added lines.

`git -C <worktree> status --porcelain --untracked-files=all`

```text
(no output)
```

The same mypy command again (exit 0):

```text
Success: no issues found in 3 source files
```

`.mypy_cache/`: mypy created it at the worktree root. `git status` does not show it, because mypy writes a catch-all `.gitignore` inside it (`ls -a` printed `.gitignore`, `3.15`, `CACHEDIR.TAG`). It was removed with `rm -r <worktree>/.mypy_cache`, per the dispatch rule that no `.mypy_cache` is left behind. Later mypy runs recreate it, so it is removed again before handoff.

## Task 5 (final gates)

All of these ran at 2bb00cc (Task 4 evidence commit). The only commit after it carries this section, VERIFICATION and SUMMARY.

D-04 order, `git -C <worktree> log --reverse --format="%h %ae %s" --name-only origin/main..HEAD`. Blank lines are removed here; the output is otherwise verbatim.

```text
0b49391 lead-seat@coh-fleet.invalid ci: mypy strict step for coh_prose (TYPE-03 checks)
.github/workflows/ci.yml
3fe150b lead-seat@coh-fleet.invalid docs(planning): Phase 4 plan, mypy strict for coh_prose (TYPE-03)
.planning/phases/04-mypy-strict-for-coh-prose/04-01-PLAN.md
ff77e91 6440797+silveimar@users.noreply.github.com docs(adr): propose ADR-0002, mypy strict for coh_prose (TYPE-03)
.planning/phases/04-mypy-strict-for-coh-prose/04-EVIDENCE.md
docs/adr/0002-mypy-strict-for-coh-prose.md
docs/adr/README.md
a1c9e12 lead-seat@coh-fleet.invalid docs(decision-log): D17 pathspec MPL-2.0 dev-only (D16 reopened)
README.md
docs/decision-log.md
fde02e0 6440797+silveimar@users.noreply.github.com docs(adr): accept ADR-0002 (owner decision qitem-20261022141325-97bd7544)
docs/adr/0002-mypy-strict-for-coh-prose.md
docs/adr/README.md
baaff7c 6440797+silveimar@users.noreply.github.com build(deps): add mypy 2.4.0 to the root dev group with strict config (ADR-0002, TYPE-03)
pyproject.toml
uv.lock
2bb00cc 6440797+silveimar@users.noreply.github.com docs(04): build evidence
.planning/phases/04-mypy-strict-for-coh-prose/04-EVIDENCE.md
```

No pyproject.toml, uv.lock or coh_prose path appears before the accept commit fde02e0.

Criterion 1, `uv run --no-sync --directory <worktree> mypy --strict packages/prose/src/coh_prose` (exit 0)

```text
Success: no issues found in 3 source files
```

Criterion 2, `uv run --no-sync --directory <worktree> pyright packages/prose` (exit 0)

```text
0 errors, 0 warnings, 0 informations
```

`uv run --no-sync --directory <worktree> pytest tests/packages/prose -q` (exit 0)

```text
....................................                                     [100%]
36 passed in 0.09s
```

Criterion 3, `grep -n "mypy --strict packages/prose/src/coh_prose" <worktree>/.github/workflows/ci.yml`

```text
44:        run: uv run mypy --strict packages/prose/src/coh_prose
```

`grep -c "on-error" <worktree>/.github/workflows/ci.yml` (exit 1 at count 0, the pass state)

```text
0
```

`git -C <worktree> log --format="%h %ae %s" origin/main..HEAD -- .github`

```text
0b49391 lead-seat@coh-fleet.invalid ci: mypy strict step for coh_prose (TYPE-03 checks)
```

`git -C <worktree> diff --numstat origin/main...HEAD -- .github/workflows/ci.yml`

```text
5	0	.github/workflows/ci.yml
```

`grep -n -A 2 "Run mypy strict (coh_prose)" <worktree>/.github/workflows/ci.yml`

```text
43:      - name: Run mypy strict (coh_prose)
44-        run: uv run mypy --strict packages/prose/src/coh_prose
45-
```

Criterion 4, `git -C <worktree> diff origin/main...HEAD -- packages/prose/src`. The diff is empty, so the plan's `grep -nE "type: ignore|# mypy:|pyright: ignore"` over it prints nothing.

```text
(no output)
```

Criterion 5, `grep -nE "ignore_errors|disable_error_code|follow_imports|ignore_missing_imports|tool\.mypy\.overrides|plugins" <worktree>/pyproject.toml <worktree>/packages/prose/pyproject.toml` (exit 1)

```text
(no output)
```

Criterion 6, `grep -c '^name = "mypy"' <worktree>/uv.lock`

```text
1
```

`uv lock --check --directory <worktree>` (exit 0)

```text
Resolved 73 packages in 0.85ms
```

`grep -c -F -e '**Status:** Accepted' -e '| [0002](0002-mypy-strict-for-coh-prose.md) | Add mypy to the root dev group and check coh_prose with mypy --strict | Accepted |' <ADR> <ADR index>`

```text
<worktree>/docs/adr/README.md:1
<worktree>/docs/adr/0002-mypy-strict-for-coh-prose.md:1
```

The ADR's dependency table has a license line for mypy and for each of the 5 transitive packages (Task 1 gate: 6 rows).

`git -C <worktree> diff --name-only origin/main...HEAD`

```text
.github/workflows/ci.yml
.planning/phases/04-mypy-strict-for-coh-prose/04-01-PLAN.md
.planning/phases/04-mypy-strict-for-coh-prose/04-EVIDENCE.md
README.md
docs/adr/0002-mypy-strict-for-coh-prose.md
docs/adr/README.md
docs/decision-log.md
pyproject.toml
uv.lock
```

`.github/workflows/ci.yml` and `04-01-PLAN.md` come from the lead commits 0b49391 and 3fe150b. `README.md` and `docs/decision-log.md` come from lead commit a1c9e12 (D17), which the resume row allows. The builder edited neither.

Privacy:

- Decider name from the decision-log Decided lines, in `git -C <worktree> diff -U0 origin/main...HEAD` (`grep -c -i -w`): 1 match. It is the `Decided` line of D17 in lead commit a1c9e12, which follows the log's existing convention.
- The same grep restricted to the builder paths (`docs/adr pyproject.toml uv.lock .planning/phases/04-mypy-strict-for-coh-prose packages`): 0 matches.
- Metadata author, maintainer and copyright lines added under `docs/adr` and `04-EVIDENCE.md`: 0.
