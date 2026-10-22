# Roadmap: COH (Cognitive Operating Harness)

## Overview

Mission `chores-q4` pays down six pieces of tooling and docs debt recorded in `CONTRIBUTING.md` ("Known gaps") and `.planning/codebase/CONCERNS.md`. Every phase is a chore, test or docs phase, and each one ships as one PR. The phases have no code dependency on each other; they run in the fixed order under "Execution Order" below, within the WIP cap of 2 open PRs. Phases 3, 4 and 6 change the protected check set: the lead writes those checks commits, and the builder never does.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Pyright clean archive** - `packages/archive` reaches 0 pyright errors (baseline 5)
- [x] **Phase 2: Pyright clean execution-core** - `packages/execution-core` reaches 0 pyright errors (baseline 18) with stored datetimes unchanged
- [ ] **Phase 3: Dependency audit job** - CI runs deptry and pip-audit on every PR (protected: `.github/workflows/`)
- [ ] **Phase 4: mypy strict for coh_prose** - `packages/prose/src/coh_prose` passes `mypy --strict` in CI (protected: `.github/workflows/`)
- [x] **Phase 5: Docs drift** - README, package READMEs and the `docs/coding-rules.md` structure section match the actual layout
- [x] **Phase 6: Coverage floor for prose** - CI enforces a statement coverage floor for `packages/prose` (protected: `.github/workflows/`)

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
**Plans**: 1 plan

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
**Plans**: 1 plan

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
**Plans**: 1 plan

## Progress

**Execution Order:**
1, 2, 6, 5, 4, 3 (owner answer, 2026-10-22): cheap and mechanical phases first, Phase 6 is lead-only, the two ADR phases last. At most 2 PRs are open at a time. Phases 3 and 4 both change the root dev group and `uv.lock`, so they are never open at the same time.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pyright clean archive | 1/1 | Complete (#33) | 2026-10-22 |
| 2. Pyright clean execution-core | 1/1 | Complete (#34) | 2026-10-22 |
| 3. Dependency audit job | 0/TBD | Not started | - |
| 4. mypy strict for coh_prose | 0/TBD | Not started | - |
| 5. Docs drift | 1/1 | Complete (#36) | 2026-10-22 |
| 6. Coverage floor for prose | 1/1 | Complete (#35) | 2026-10-22 |

## Backlog

Not part of mission chores-q4. Each item needs its own scope gate before it is planned.

### Phase 999.1: Unify naive defaults and aware mutators in execution-core (BACKLOG)

**Goal:** Domain timestamps in `packages/execution-core` use one timezone form. Today the defaults are naive UTC (`domain/clock.py` `utc_now_naive()`, Phase 2 D-01), while about 25 mutators set aware `datetime.now(UTC)` values (for example `Task.start()` sets an aware `updated_at` while `created_at` stays naive). Comparing or subtracting a naive and an aware field (`updated_at - created_at`, sorting by timestamp) raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
**Source:** acting-lead review of PR #34 (2026-10-22).
**Constraint:** switching to aware values changes stored and wire timestamp strings (`+00:00` in JSON columns), so it needs a decision-log entry first (REQUIREMENTS "Out of Scope"; Phase 2 D-03).
**Plans:** none yet

### Phase 999.2: Prose coverage floor must not hide later test failures (BACKLOG)

**Goal:** In `.github/workflows/ci.yml` the "Check prose coverage floor" step runs before the mcp_adapter, application, api, eval and checks-guard test steps. When prose coverage dips below the floor, the job stops there, and failures in those later steps stay hidden until the floor is fixed. Move the floor after the last test step, or let the later test steps run with `if: success() || failure()`.
**Source:** acting-lead review of PR #35 (2026-10-22).
**Constraint:** protected check set (`.github/workflows/`): the lead writes the change, and editing an existing line is an owner Ask (moving the step edits existing lines).
**Plans:** none yet

### Phase 999.3: Alembic revisions never run on the app databases (BACKLOG)

**Goal:** The runtime databases and the Alembic revisions agree, and migrations can run on an existing user database. Today the MCP adapter (`packages/mcp_adapter/src/coh_mcp/handlers.py:46-49`) builds its `.coh/coh.db` with `init_db(engine)` (`metadata.create_all`), so its database carries no `alembic_version` stamp. The API (`apps/api/src/coh_api/composition.py:16-21`) opens `.coh/coh.db` in the working directory and creates no tables at all. The documented `alembic upgrade head` (`env.py` hard-codes `sqlite:///.coh/coh.db` relative to the working directory) creates another database under `packages/persistence/.coh/` that neither adapter opens. The first real migration against an existing user database will fail or try to recreate tables, and drift between the models and the revisions goes undetected.
**Suggested shape:** run `command.upgrade(cfg, "head")` against the app database at startup, or stamp databases that `create_all` built; make the `env.py` URL configurable (Phase 5 F-6); add a CI test that compares `alembic upgrade head` with `metadata.create_all` (for example `alembic check`).
**Source:** acting-lead review of PR #36 (2026-10-22); Phase 5 follow-up F-6.
**Constraint:** changes execution or persistence semantics: needs an accepted decision before build; the CI test is a protected-set change (lead).
**Plans:** none yet

### Phase 999.4: Phase 5 docs follow-ups (BACKLOG)

**Goal:** Close the smaller findings Phase 5 recorded but did not fix (`05-VERIFICATION.md`, "Follow-ups"):
- F-8: `archive_tool_invocation` (`packages/mcp_adapter/src/coh_mcp/archive_wiring.py`) has no caller in `handlers.py`, so tool events are not archived yet.
- F-1: the `packages/execution-core/README.md` Usage snippet calls the instance method `transition_to_specify` on the class and omits its required `command` argument, so it raises `TypeError` as written (found by reading, not run).
- D-10: `apps/api/README.md:57` says the database is "auto-created on first run".
- D-10: the `packages/mcp_adapter/README.md` architecture diagram shows every handler going through application services, but some handlers write through `SqlAlchemyUnitOfWork` repositories directly (for example `handlers.py:93-98`). AGENTS.md: "Routes and MCP tools call application services, never repositories."
**Source:** Phase 5 (PR #36) verification, 2026-10-22.
**Constraint:** F-1 and the `apps/api` line are docs; F-8 and the handler routing are code (the routing fix may overlap 999.3).
**Plans:** none yet
