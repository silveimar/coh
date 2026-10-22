# Phase 06 evidence (H-87)

Base: origin/main d7f3316. Head at replay: e184f64. Lead checks commit: bb3576d (`.github/workflows/ci.yml`, one new step "Check prose coverage floor"). This phase has no builder code change.

`<worktree>` stands for the checkout path of the slice worktree. Every command below ran from it through `uv run --directory <worktree>` or `git -C <worktree>`, one command per call.

## Replay of the CI test steps

The steps run in CI order and append to one `.coverage` data file. They differ from CI in two ways. They omit the xml report, so no coverage.xml is written. The execution-core step also omits its pytest-cov floor flag, which does not change the collected data (PLAN Task 1).

| Step | Command | Result |
|---|---|---|
| 1 | `uv run coverage erase` | no output |
| 2 | `uv run pytest tests/packages/execution-core --cov=packages/execution-core/src --cov-report=term -q` | `199 passed` |
| 3 | `uv run pytest tests/packages/persistence --cov=packages/persistence/src --cov-append --cov-report=term -q` | `9 passed` |
| 4 | `uv run pytest tests/packages/archive --cov=packages/archive/src --cov-append --cov-report=term -q` | `33 passed` |
| 5 | `uv run pytest tests/packages/prose --cov=packages/prose/src --cov-append --cov-report=term -q` | `36 passed` |

Prose rows of the step 5 terminal report:

```text
packages/prose/src/coh_prose/__init__.py                                       3      0   100%
packages/prose/src/coh_prose/policy.py                                        93      4    96%
packages/prose/src/coh_prose/renderer.py                                     197     13    93%
```

## Floor at 94 (step 6, the exact command of the new CI step)

`uv run coverage report --include='packages/prose/src/*' --fail-under=94` (exit 0)

```text
Name                                       Stmts   Miss  Cover
--------------------------------------------------------------
packages/prose/src/coh_prose/__init__.py       3      0   100%
packages/prose/src/coh_prose/policy.py        93      4    96%
packages/prose/src/coh_prose/renderer.py     197     13    93%
--------------------------------------------------------------
TOTAL                                        293     17    94%
```

## Floor at 95 (step 7, failing direction)

`uv run coverage report --include='packages/prose/src/*' --fail-under=95` (exit 2)

```text
Name                                       Stmts   Miss  Cover
--------------------------------------------------------------
packages/prose/src/coh_prose/__init__.py       3      0   100%
packages/prose/src/coh_prose/policy.py        93      4    96%
packages/prose/src/coh_prose/renderer.py     197     13    93%
--------------------------------------------------------------
TOTAL                                        293     17    94%
Coverage failure: total of 94 is less than fail-under=95
```

## Fail-closed probe (step 8)

`uv run coverage erase` (no output), then `uv run coverage report --include='packages/prose/src/*' --fail-under=94` (exit 1)

```text
No data to report.
```

## Static checks

`git -C <worktree> diff origin/main --numstat -- .github/workflows/ci.yml`

```text
6	0	.github/workflows/ci.yml
```

`git -C <worktree> diff origin/main --name-only` (run before the builder's evidence commits)

```text
.github/workflows/ci.yml
.planning/ROADMAP.md
.planning/STATE.md
.planning/phases/06-coverage-floor-for-prose/06-01-PLAN.md
```

`grep -n "coverage report --include='packages/prose/src/\*' --fail-under=94" .github/workflows/ci.yml`

```text
57:        run: uv run coverage report --include='packages/prose/src/*' --fail-under=94
```

`grep -n -E 'name: Run (prose|mcp_adapter) tests' .github/workflows/ci.yml` shows that the new step sits between the prose and mcp_adapter steps:

```text
50:      - name: Run prose tests
59:      - name: Run mcp_adapter tests
```

`grep -c -- '--cov-append' .github/workflows/ci.yml` on HEAD, and `git show origin/main:.github/workflows/ci.yml | grep -c -- '--cov-append'`. The counts are equal, so no existing step changed:

```text
6
6
```

`git -C <worktree> log origin/main..HEAD --format=%ae -- .github/workflows/ci.yml`

```text
lead-seat@coh-fleet.invalid
```

`git -C <worktree> status --short --untracked-files=all` after the replay: no output, so no coverage.xml or other stray file was left.

## Not checked

- These steps ran locally, not in CI. The PR's own CI run is what proves the step runs in CI, and the PR records it.
- A real coverage drop below 94 in CI was not exercised. Step 7 exercises the failing direction locally, by raising the floor to 95 on the same data.
