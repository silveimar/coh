---
phase: 02-pyright-clean-execution-core
plan: 01
requirements: [TYPE-02]
status: complete
key_files:
  created:
    - packages/execution-core/src/execution_core/domain/clock.py
    - .planning/phases/02-pyright-clean-execution-core/02-EVIDENCE.md
  modified:
    - packages/execution-core/src/execution_core/domain/specification.py
    - packages/execution-core/src/execution_core/domain/session.py
    - packages/execution-core/src/execution_core/domain/task.py
    - packages/execution-core/src/execution_core/domain/decision.py
    - packages/execution-core/src/execution_core/domain/evidence.py
    - packages/execution-core/src/execution_core/domain/parking_item.py
    - packages/execution-core/src/execution_core/domain/foreground.py
    - packages/execution-core/src/execution_core/policies/integrity_policy.py
    - packages/execution-core/src/execution_core/policies/parking_policy.py
    - packages/execution-core/src/execution_core/state_machine/lifecycle.py
commits:
  - 80cf663 fix(execution-core): naive UTC clock for Specification and ExecutionSession defaults (TYPE-02)
  - 40a830b docs(planning): Phase 2 baseline evidence and tracer checkpoint
  - a62c8aa fix(execution-core): move remaining domain defaults onto utc_now_naive (TYPE-02)
  - c3fdf39 fix(execution-core): clear the last pyright diagnostics (TYPE-02)
  - 66658a6 docs(planning): Phase 2 after-run evidence, comparison and not-checked list
---

# Phase 02 Plan 01: Pyright clean execution-core (summary)

`packages/execution-core` now reports 0 pyright errors; it reported 18 before. The 13 deprecated default factories now go through one helper, `utc_now_naive()`, which returns naive UTC. The stored form did not change: E1 forces the process time zone to UTC+9 and passes a Specification through `SpecificationMapper.to_model`. Its output is identical before and after, except `deprecation_warnings`, which drops from 18 to 0.

## Numbers

| Measure | CONTEXT (f3743a1) | Measured base (origin/main 0e93597 + checks 915fd1e) | After (c3fdf39) |
|---|---|---|---|
| `pyright packages/execution-core` errorCount | 18 | 18 | 0 |
| Whole-repo pyright errorCount | n/a | 643 | 625 |
| Criterion-3 pytest command (`-W error::DeprecationWarning`) | fails | 133 failed, 66 passed | 199 passed |
| Execution-core tests | 189 | 199 (189 + 10 lead-added) | 199 |
| Coverage TOTAL | 95.60% | 96% (935 of 978) | 96% (947 of 990) |
| E1 deprecation_warnings | n/a | 18 | 0 |
| tests/evals | n/a | 18 passed, 5 skipped, 1 xfailed | same |
| tests/packages/persistence | n/a | 9 passed | 9 passed |
| Full suite | n/a | 460 passed, 5 skipped, 1 xfailed | same |

Full outputs are in `02-EVIDENCE.md`. The source diff is 11 files changed, with 37 insertions and 16 deletions, as the plan specified.

## How the criteria were read on this branch

- Diff gates use `origin/main`, not local `main`. The local `main` ref in the worktree is stale at 378d9ed.
- Criterion 3: the expected count is 199, the 189 tests that main has plus the 10 from the lead checks commit 915fd1e.
- Criterion 4: the evidence covers the field each model defaults, 13 fields in total, including `Evidence.recorded_at` and `Foreground.calculated_at`.
- Criterion 5 has three gates. After 915fd1e, only the 11 source files change (R20). Only `COH lead seat` touches the protected set (R21). There are 0 suppression comments (R22).

## Choices not dictated by the spec

- The helper is named `execution_core/domain/clock.py` with function `utc_now_naive`, chosen within the coding-rules naming rules. Its only import is stdlib `datetime`, so it is a leaf module.
- The helper is not exported from `domain/__init__.py`.
- The package README module tree is not updated (Phase 5, DOCS-01).
- E1 forces the process time zone to UTC+9 and passes a Specification through the persistence mapper, so a local-time or aware default would show up in its output.
- `dict[str, Any]` follows the `events/domain_events.py` precedent (D-05), and `NoReturn` is not used.

## Deviations

- The work ran in two builder sessions. A context watchdog fired after commit c3fdf39. The lead decided at 07:37Z that the same session should finish Step C, so Tasks 1 to 3 were not repeated.
- R17 reports 172 formatted files at baseline, not the planning-time 171, because ruff counts the PLAN file committed after that measurement. The plan does not gate this count.
- R10 and R11 after the change are pasted in shortened form: the coverage table is identical to R9's, so only the summary and TOTAL lines appear.

## Not covered

- The MCP and API handlers were not driven directly. The full suite covers them.
- There is no SQLite round trip; the persistence suite covers the mapping.
- `spec_gate_service` still sets an aware `updated_at` on spec objects. This predates the phase and is out of scope.
- CI does not run pyright.
- The pyright errors under `tests/packages/execution-core` are protected and were not changed.
