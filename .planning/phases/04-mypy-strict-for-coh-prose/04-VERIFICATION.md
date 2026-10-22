# Phase 04 verification (builder self-check)

This is the builder seat's self-check. It is not the slice proof; the slice proof is the checker's report on the head SHA. The commands ran at 2bb00cc, and the commit that adds this file changes only this file, 04-01-SUMMARY.md and 04-EVIDENCE.md. Full output is in `04-EVIDENCE.md`, "Task 4 (build)" and "Task 5 (final gates)".

Criterion 4 uses `origin/main` in place of `main`: the local `main` ref is stale at 378d9ed, while `origin/main` is f33c7cb.

| # | CONTEXT criterion | Command | Result | Verdict |
|---|---|---|---|---|
| 1 | `mypy --strict` on coh_prose exits 0 with the Success line; it exits 1 with an untyped `def` added | `uv run mypy --strict packages/prose/src/coh_prose`; bite run with `_bite_probe(value)` appended to `policy.py` | exit 0, `Success: no issues found in 3 source files`. Bite run: exit 1, `policy.py:271: error: Function is missing a type annotation  [no-untyped-def]`, `Found 1 error in 1 file (checked 3 source files)`. Probe removed; status clean; Success again | PASS |
| 2 | `uv run pyright packages/prose` reports 0 errors | `uv run pyright packages/prose` | `0 errors, 0 warnings, 0 informations` (baseline the same); prose tests `36 passed` (baseline 36) | PASS |
| 3 | The CI grep returns one line, from a lead-seat commit, with no error-tolerance key; CI green on the PR head | `grep -n "mypy --strict packages/prose/src/coh_prose" .github/workflows/ci.yml`; `grep -c "on-error"`; `git log origin/main..HEAD -- .github`; numstat; `grep -n -A 2` of the step | One line (44). Count 0. Only 0b49391 by `lead-seat@coh-fleet.invalid`, `5 0`. Lines 43-45 are name, run and blank. CI on the head: UNKNOWN until the PR run completes; the PR's run and the checker fill it in | PASS for the grep, author and additions checks; CI UNKNOWN |
| 4 | No suppression comment in the coh_prose diff | `git diff origin/main...HEAD -- packages/prose/src \| grep -nE "type: ignore\|# mypy:\|pyright: ignore"` | The coh_prose diff is empty; no output | PASS |
| 5 | No mypy-weakening key in either pyproject file | `grep -nE "ignore_errors\|disable_error_code\|follow_imports\|ignore_missing_imports\|tool\.mypy\.overrides\|plugins" pyproject.toml packages/prose/pyproject.toml` | no output (exit 1). `[tool.mypy]` holds `strict = true` and `python_version = "3.15"` only | PASS |
| 6 | One mypy in the lock; `uv lock --check` exits 0; ADR Accepted, indexed, with license lines | `grep -c '^name = "mypy"' uv.lock`; `uv lock --check`; Status and index-row grep | `1`; exit 0; Status Accepted 1, index row Accepted 1; dependency table has 6 rows, each with a license (mypy and 5 transitive packages) | PASS |

## Not checked

- CI on the head: UNKNOWN until the PR run completes.
- The mypy cp315 wheels on any platform other than linux x86_64.
- mypy on tests or other packages (out of scope, D-02).
- The deferred `renderer.py:281-303` rendering when no criterion fails.
