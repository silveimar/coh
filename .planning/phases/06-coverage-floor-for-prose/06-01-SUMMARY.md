---
phase: 06-coverage-floor-for-prose
plan: 01
requirements: [COV-01]
status: complete
key_files:
  created:
    - .planning/phases/06-coverage-floor-for-prose/06-EVIDENCE.md
    - .planning/phases/06-coverage-floor-for-prose/06-01-SUMMARY.md
    - .planning/phases/06-coverage-floor-for-prose/06-VERIFICATION.md
  lead_checks_commit:
    - bb3576d ci: prose statement coverage floor at 94 (COV-01, Phase 6 checks)
---

# Phase 06 Plan 01: Coverage floor for prose (summary)

CI now fails when `packages/prose` statement coverage, measured for prose alone, drops below 94%. The lead checks commit bb3576d adds one step, "Check prose coverage floor", directly after "Run prose tests". It runs `uv run coverage report --include='packages/prose/src/*' --fail-under=94` and adds 6 lines to `ci.yml` without deleting any. The builder made no code change; this plan is the evidence and the ship.

## Numbers

| Measure | Result |
|---|---|
| Replay test counts (execution-core, persistence, archive, prose) | 199, 9, 33, 36 passed |
| Prose alone, floor at 94 | `TOTAL 293 17 94%`, exit 0 |
| Prose alone, floor at 95 | `Coverage failure: total of 94 is less than fail-under=95`, exit 2 |
| No coverage data, floor at 94 | `No data to report.`, exit 1 (fails closed) |
| `--cov-append` count in `ci.yml`, HEAD and origin/main | 6 and 6 |
| `ci.yml` authors on the branch | only `lead-seat@coh-fleet.invalid` |

The full output is in `06-EVIDENCE.md`. All values match the plan and the Gate 1 replay.

## Choices not dictated by the spec

- The replay omits the xml report, so no coverage.xml appears in the worktree (D-07). The execution-core replay step also omits its pytest-cov floor flag, which leaves the collected data unchanged and keeps the checks-guard weakening token out of builder files (D-06).
- Diff checks compare against `origin/main`, because the worktree's local `main` ref is stale.

## Deviations

None.

## Not covered

- These checks ran locally. The PR's CI run is what proves the step runs in CI.
- A real drop below 94 in CI was not exercised. The failing direction was checked locally by raising the floor to 95.
