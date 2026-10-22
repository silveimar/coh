# Roadmap: COH (Cognitive Operating Harness)

## Overview

Mission `chores-q4` pays down six pieces of tooling and docs debt recorded in `CONTRIBUTING.md` ("Known gaps") and `.planning/codebase/CONCERNS.md`. Every phase is a chore, test or docs phase, and each one ships as one PR. The phases have no code dependency on each other; they run in the fixed order under "Execution Order" below, within the WIP cap of 2 open PRs. Phases 3, 4 and 6 change the protected check set: the lead writes those checks commits, and the builder never does.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Pyright clean archive** - `packages/archive` reaches 0 pyright errors (baseline 5)
- [ ] **Phase 2: Pyright clean execution-core** - `packages/execution-core` reaches 0 pyright errors (baseline 18) with stored datetimes unchanged
- [ ] **Phase 3: Dependency audit job** - CI runs deptry and pip-audit on every PR (protected: `.github/workflows/`)
- [ ] **Phase 4: mypy strict for coh_prose** - `packages/prose/src/coh_prose` passes `mypy --strict` in CI (protected: `.github/workflows/`)
- [ ] **Phase 5: Docs drift** - README, package READMEs and the `docs/coding-rules.md` structure section match the actual layout
- [ ] **Phase 6: Coverage floor for prose** - CI enforces a statement coverage floor for `packages/prose` (protected: `.github/workflows/`)

## Phase Details

### Phase 1: Pyright clean archive
**Goal**: `packages/archive` has zero pyright errors under the repository's strict config, with no behavior change.
**Type**: chore
**Depends on**: Nothing (independent)
**Requirements**: TYPE-01
**Protected check set**: not touched
**Success Criteria** (what must be TRUE):
  1. `uv run pyright packages/archive` exits 0 and reports 0 errors.
  2. `uv run pytest tests/packages/archive` passes with the same test count as `main`.
  3. The diff adds no `# type: ignore`, `# pyright: ignore` or `# noqa`.
**Plans**: 1 plan

### Phase 2: Pyright clean execution-core
**Goal**: `packages/execution-core` has zero pyright errors, and every stored or serialized datetime keeps its current value and form.
**Type**: chore
**Depends on**: Nothing (independent)
**Requirements**: TYPE-02
**Protected check set**: not touched
**Success Criteria** (what must be TRUE):
  1. `uv run pyright packages/execution-core` exits 0 and reports 0 errors.
  2. `uv run pytest tests/packages/execution-core --cov=packages/execution-core/src` passes, and `uv run coverage report --include='packages/execution-core/src/*' --fail-under=90` exits 0.
  3. `uv run pytest tests/evals` passes its thresholds.
  4. Fields that defaulted through `datetime.utcnow` still default to naive UTC (`tzinfo is None`); existing `datetime.now(UTC)` sites are unchanged. Persisted and wire values keep their current form.
**Plans**: TBD

### Phase 3: Dependency audit job
**Goal**: CI fails a PR that introduces an unused, missing or transitive-only dependency (deptry) or a dependency with a known vulnerability (pip-audit).
**Type**: chore (CI)
**Depends on**: Nothing (independent); an accepted ADR for the two tools is required before build
**Requirements**: SUPP-01
**Protected check set**: YES — `.github/workflows/`. The lead writes the CI jobs in a checks commit; the builder writes only the ADR draft, `pyproject.toml` config, the member dependency changes in 03-CONTEXT D-04 (owner answer: split) and `uv.lock`.
**Success Criteria** (what must be TRUE):
  1. An accepted ADR in `docs/adr/` covers deptry and pip-audit (license, pinning, how they run).
  2. A CI job runs both tools on every PR and push to `main` and is green on the PR head.
  3. Each tool fails the job on a finding (shown by the tool's exit code contract in the evidence file).
**Plans**: TBD

### Phase 4: mypy strict for coh_prose
**Goal**: `packages/prose/src/coh_prose` is checked by `mypy --strict` in CI.
**Type**: chore (CI)
**Depends on**: Nothing (independent); an accepted ADR for mypy is required before build
**Requirements**: TYPE-03
**Protected check set**: YES — `.github/workflows/`. The lead writes the CI step in a checks commit; the builder writes only the ADR draft, `pyproject.toml` config and any source typing fixes.
**Success Criteria** (what must be TRUE):
  1. `uv run mypy --strict packages/prose/src/coh_prose` exits 0.
  2. A CI step runs that command on every PR and is green on the PR head.
  3. `uv run pyright packages/prose` still reports 0 errors.
**Plans**: TBD

### Phase 5: Docs drift
**Goal**: The repository docs describe only what exists and mark planned components as planned.
**Type**: docs
**Depends on**: Nothing (independent)
**Requirements**: DOCS-01
**Protected check set**: not touched
**Success Criteria** (what must be TRUE):
  1. Every path named in the structure section of `docs/coding-rules.md`, in `README.md` and in each package README exists, or is labelled "planned".
  2. `README.md` lists all seven packages and the decision range that `docs/decision-log.md` actually holds.
  3. `packages/prose` has a README.
**Plans**: TBD

### Phase 6: Coverage floor for prose
**Goal**: CI fails when `packages/prose` statement coverage drops below its current level.
**Type**: test (CI)
**Depends on**: Nothing (independent)
**Requirements**: COV-01
**Protected check set**: YES — `.github/workflows/ci.yml`. This phase is the lead's checks commit only; there is no builder change.
**Success Criteria** (what must be TRUE):
  1. A new CI step right after the prose tests runs `coverage report --include='packages/prose/src/*' --fail-under=94` (prose-only, measured 94.2% at f3743a1); the existing prose test line is unchanged (additions only).
  2. CI is green on the PR head.
  3. The evidence file shows the step failing when replayed locally with a floor above current coverage.
**Plans**: TBD

## Progress

**Execution Order:**
1, 2, 6, 5, 4, 3 (owner answer, 2026-10-22): cheap and mechanical phases first, Phase 6 is lead-only, the two ADR phases last. At most 2 PRs are open at a time. Phases 3 and 4 both change the root dev group and `uv.lock`, so they are never open at the same time.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pyright clean archive | 0/TBD | Not started | - |
| 2. Pyright clean execution-core | 0/TBD | Not started | - |
| 3. Dependency audit job | 0/TBD | Not started | - |
| 4. mypy strict for coh_prose | 0/TBD | Not started | - |
| 5. Docs drift | 0/TBD | Not started | - |
| 6. Coverage floor for prose | 0/TBD | Not started | - |
