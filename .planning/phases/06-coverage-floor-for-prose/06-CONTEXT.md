# Phase 6: Coverage floor for prose - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning
**Type:** test (CI). Protected check set: YES — `.github/workflows/ci.yml`. This phase is the lead's checks commit only; there is no builder change.

<domain>
## Phase Boundary

CI fails when `packages/prose` statement coverage, measured for prose alone, drops below its current level. Requirement: COV-01.

In scope: one new step in `.github/workflows/ci.yml`, added lines only.
Out of scope: editing any existing `ci.yml` line; `.coveragerc` or `pytest.ini`; floors for other packages; the Codecov flag; `CONTRIBUTING.md` "Known gaps" wording.
</domain>

<decisions>
## Implementation Decisions

### Measurement
- **D-01:** Add a step directly after "Run prose tests": `uv run coverage report --include='packages/prose/src/*' --fail-under=94`. It reads the `.coverage` data the prose step appended to and reports prose files only. The existing prose `run:` line stays byte-identical.
- **D-02:** Do not put the pytest-cov fail-under flag on the prose step. With `--cov-append` the total is cumulative across execution-core, persistence, archive and prose: replayed locally it reads 88.88% and would turn CI red.
- **D-03:** No `fail_under` in `.coveragerc`: it would apply to every pytest-cov step, and persistence (about 84-88%) would fail.

### Floor
- **D-04:** Integer floor 94 at coverage's default precision 0, statements only (`.coveragerc` has no `branch`). Prose alone is 276/293 = 94.2%. Effective threshold is 93.5% (rounding), matching the integer style of the execution-core floor. A tighter `--precision=1 --fail-under=94.2` is an open question.

### Protected-set mechanics
- **D-05:** One lead-authored commit, additions only, so `checks-edits` raises no owner-approval finding. Keep the trailing whitespace on `ci.yml:43` intact.
- **D-06:** No non-lead commit in this PR may contain the pytest-cov fail-under flag text in any file (`checks-guard` weakening token). The coverage `--fail-under` form does not match it.

### Proof
- **D-07:** Evidence is a sequential local replay of the CI test steps (execution-core, persistence, archive, prose, without `--cov-report=xml`, since `coverage.xml` is not gitignored), then the new command at 94 (exit 0) and at 95 (exit 2).

### Claude's Discretion
- Step name.
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `git diff main --numstat -- .github/workflows/ci.yml` shows 0 deleted lines; `git diff main --name-only` lists no `.coveragerc`, `pytest.ini`, `tests/` or `.github/scripts/` path.
2. `grep -n "coverage report --include='packages/prose/src/\*' --fail-under=94" .github/workflows/ci.yml` returns exactly one line, between the `Run prose tests` and `Run mcp_adapter tests` steps; `grep -c -- '--cov-append' .github/workflows/ci.yml` is unchanged from `main`.
3. Replaying the CI steps in order, then `uv run coverage report --include='packages/prose/src/*' --fail-under=94` exits 0 and prints `TOTAL 293 17 94%` (or higher if tests were added).
4. The same replay, then `--fail-under=95`, exits 2 with `Coverage failure: total of 94 is less than fail-under=95`.
5. `git log main..HEAD --format=%ae -- .github/workflows/ci.yml` prints only `lead-seat@coh-fleet.invalid`.
6. `Lint and Test (Python 3.15)`, `checks-guard` and `checks-edits` pass on the PR head.
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 6)
- `.github/workflows/ci.yml` (test steps, `--cov-append`)
- `.coveragerc`
- `.github/workflows/checks-guard.yml`, `.github/scripts/checks_guard.py` (lead identity, weakening tokens, checks-edits)
- `docs/decision-log.md` D14, D15
- `CONTRIBUTING.md` ("Known gaps": floors at current coverage, only go up)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Execution-core floor precedent: integer 90 on `ci.yml:42`.

### Established Patterns
- Each CI test step limits measurement with `--cov=<pkg>/src` and appends to one `.coverage` file; Codecov uploads the cumulative `coverage.xml`.

### Integration Points
- `checks-edits` becomes a required check on Nov 1 (`.github/workflows/checks-guard.yml`, D15).
</code_context>

<specifics>
## Specific Ideas

If prose data is missing, `coverage report` prints `No data to report` and exits 1: the step fails closed.
</specifics>

<deferred>
## Deferred Ideas

- `CONTRIBUTING.md` "Known gaps" line on coverage floors becomes partly stale — later docs pass (Ask-tier file).
- Floors for archive, application, persistence, mcp_adapter, api (COV-02).
</deferred>
