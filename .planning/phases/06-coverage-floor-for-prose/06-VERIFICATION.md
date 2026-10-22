# Phase 06 verification (builder self-check)

This is the builder seat's self-check, not the slice proof. The slice proof is the checker's report on the head SHA. Commands ran at e184f64, before the builder's `.planning` commits. Full output is in `06-EVIDENCE.md`.

| # | CONTEXT criterion | Command | Result | Verdict |
|---|---|---|---|---|
| 1 | `ci.yml` additions only; no `.coveragerc`, `pytest.ini`, `tests/` or `.github/scripts/` path | `git diff origin/main --numstat -- .github/workflows/ci.yml` / `git diff origin/main --name-only` | `6 0`; only `ci.yml`, ROADMAP, STATE and this phase directory | PASS |
| 2 | one floor line between the prose and mcp_adapter steps; `--cov-append` count unchanged | `grep -n` on `ci.yml` / `grep -c -- '--cov-append'` on HEAD and origin/main | line 57, between lines 50 and 59; 6 and 6 | PASS |
| 3 | replay, then floor 94, exits 0 | the CI test steps in order, then `uv run coverage report --include='packages/prose/src/*' --fail-under=94` | `TOTAL 293 17 94%`, exit 0 | PASS |
| 4 | same data, floor 95, exits 2 | `uv run coverage report --include='packages/prose/src/*' --fail-under=95` | `Coverage failure: total of 94 is less than fail-under=95`, exit 2 | PASS |
| 5 | only the lead seat authors `ci.yml` changes | `git log origin/main..HEAD --format=%ae -- .github/workflows/ci.yml` | `lead-seat@coh-fleet.invalid` | PASS |
| 6 | Lint and Test (Python 3.15), checks-guard and checks-edits pass on the PR head | PR CI | not yet run; filled in by the PR's own CI run and the checker | UNKNOWN until CI completes |

Extra check: after `coverage erase`, the floor command prints `No data to report.` and exits 1, so the step fails closed.

Prohibitions: the builder commits touch only this phase directory. They make no change to `.github/`, `tests/`, `.coveragerc`, `pytest.ini`, `STATE.md` or `ROADMAP.md`, and they add no coverage.xml. The phase files were scanned for the checks-guard weakening flag and for absolute host paths, and neither was found.
