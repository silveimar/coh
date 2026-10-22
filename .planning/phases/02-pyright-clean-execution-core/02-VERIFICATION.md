# Phase 02 verification (builder self-check)

This is the builder seat's self-check, not the slice proof. The slice proof is the checker's report on the head SHA. Every result below comes from the after-run at code commit c3fdf39 (full outputs in `02-EVIDENCE.md`). Later commits touch only `.planning`.

| # | CONTEXT criterion | Command | Result | Verdict |
|---|---|---|---|---|
| 1 | execution-core pyright 0 | `uv run pyright --outputjson packages/execution-core \| jq '.summary'` | `errorCount: 0` | PASS |
| 1 | repo pyright base minus 18 | `uv run pyright --outputjson \| jq '.summary.errorCount'` | `625` (base 643) | PASS |
| 2 | no deprecated factory in src | `git grep -n utcnow -- packages/execution-core/src` | no output | PASS |
| 3 | criterion-3 pytest, 199 tests | `uv run pytest tests/packages/execution-core -q -W error::DeprecationWarning --cov=packages/execution-core/src` | `199 passed` (baseline: 133 failed, 66 passed) | PASS |
| 3 | coverage at 90 | `uv run coverage report --include='packages/execution-core/src/*' --fail-under=90` | exit 0, TOTAL 96% | PASS |
| 4 | defaults naive, UTC, offset-free; stored form kept | E1 | 13 of 13 field lines and 3 of 3 stored lines True; `deprecation_warnings: 0` (baseline 18); every other line identical to the baseline | PASS |
| D-06 | lead test under the error filter | `uv run pytest tests/packages/execution-core/domain/test_naive_utc_defaults.py -q -W error::DeprecationWarning` | `10 passed` (baseline 10 failed) | PASS |
| 5 | only the 11 source files after the checks commit | `git diff --name-only 915fd1e HEAD -- . ':!.planning'` | the 11 planned files | PASS |
| 5 | protected set touched only by the lead seat | `git log --format='%an' origin/main..HEAD -- tests evals .github pytest.ini .coveragerc` | `COH lead seat` | PASS |
| 5 | no suppression comments | `git diff origin/main...HEAD -- packages/execution-core \| grep -c -E '^\+.*(type: ignore\|pyright: ignore\|noqa)'` | `0` | PASS |
| D-03 | aware sites unchanged | R18 / R23 | 25 lines kept, 0 removed | PASS |
| 6 | evals and persistence at base counts | `uv run pytest tests/evals -q` / `uv run pytest tests/packages/persistence -q` | 18 passed, 5 skipped, 1 xfailed / 9 passed | PASS |
| DoD | full suite and ruff | `uv run pytest -q` / `uv run ruff check .` / `uv run ruff format --check .` | 460 passed, 5 skipped, 1 xfailed / `All checks passed!` / no file would be reformatted | PASS |

Prohibitions: no protected path, dependency, decision-log, `STATE.md` or `ROADMAP.md` change. The diff is the 11 source files plus this phase directory (37 insertions, 16 deletions under `packages`).

Not checked: the MCP and API handlers were not driven directly; there is no SQLite round trip; pyright does not run in CI; the test-side pyright errors are protected and out of scope.
