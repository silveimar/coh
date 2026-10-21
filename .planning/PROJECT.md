# COH (Cognitive Operating Harness)

## What This Is

COH is a local-first, Python execution layer that helps solo AI-assisted developers turn intention into completed action. It turns ambiguous requests into confirmed specifications, keeps exactly one NOW task and at most two NEXT tasks in the foreground, preserves decisions and evidence, and recovers reliably after interruptions. Source: `README.md`, `AGENTS.md`.

## Core Value

The Execution Core stays deterministic and authoritative: AI output is proposal-only, and domain policy validates it before any state changes.

## Requirements

### Validated

<!-- Inferred from the existing code at d2b31b7 (see .planning/codebase/). -->

- ✓ Deterministic domain model, policies and lifecycle state machine with no framework imports (`packages/execution-core`) — existing
- ✓ Project-local state store on SQLite with SQLAlchemy and Alembic migrations (`packages/persistence`) — existing
- ✓ Append-only Markdown interaction archive under `.coh/archive/` (`packages/archive`) — existing
- ✓ Prose rendering policy (`packages/prose`) — existing
- ✓ Application services for foreground and spec gate (`packages/application`) — existing
- ✓ FastAPI HTTP adapter (`apps/api`) and MCP adapter for Claude Code (`packages/mcp_adapter`) — existing
- ✓ Behavioral eval harness with 19 scenarios (`tests/evals`) — existing
- ✓ CI: ruff, per-package tests, Execution Core coverage floor at 90%, gitleaks, checks-guard — existing

### Active

Mission `chores-q4`: six independent chore, test and docs phases. See `.planning/REQUIREMENTS.md`.

- [ ] Pyright reports zero errors for `packages/archive`
- [ ] Pyright reports zero errors for `packages/execution-core`
- [ ] CI runs a dependency audit job (deptry and pip-audit)
- [ ] One module is checked by mypy in strict mode in CI
- [ ] Repository docs match the actual layout
- [ ] CI enforces a coverage floor for `packages/prose`

### Out of Scope

- Feature work on execution semantics — `chores-q4` is chore/test/docs only; feature phases keep all four human gates (H-88).
- Fixing the MCP adapter's direct repository access (`packages/mcp_adapter/src/coh_mcp/handlers.py`) — a cross-module refactor needs an ADR and is not a chore.
- Pyright errors under `tests/` (417 at d2b31b7) — protected check set; only the lead may change it, and edits to existing test lines are Ask.
- Pyright in CI as a required check — it would fail on `main` until every package is clean; it comes after the per-package phases.
- Trivy, pre-commit, PR template, `fleet/checker` status — listed in `CONTRIBUTING.md` known gaps; not selected for this mission.

## Context

- Brownfield Python 3.15 monorepo managed with `uv` workspaces; seven packages (see `.planning/codebase/STRUCTURE.md`).
- Pyright baseline at d2b31b7: 648 errors (source 231, tests 417). Per-package table in `.planning/codebase/CONCERNS.md`.
- Coverage at d2b31b7 (statements): prose 94.2%, archive 89.2%, application 87.3%, persistence 83.6%. Only the Execution Core has an enforced floor.
- The work is done by a three-seat fleet (lead, builder, checker) under `FLEET-POLICY.md`. The lead writes the checks commit for any change in the protected check set (`tests/`, `.github/workflows/`, `pytest.ini`, `.coveragerc` and the rest listed in `CONTRIBUTING.md`).

## Constraints

- **Dependencies**: No new dependency without an accepted ADR (`CONTRIBUTING.md`) — deptry, pip-audit and mypy each need one.
- **Protected checks**: Only the lead seat changes the protected check set, authored as the lead seat identity (D14, D15) — `checks-guard` enforces it.
- **No weakening**: Never disable, skip or weaken a test, linter or scanner to make a change pass (`FLEET-POLICY.md`, Never tier).
- **Wire format**: snake_case JSON end to end (D10); no public contract or archive format change without an accepted decision.
- **Public repository**: no secrets, personal data, vault paths or real data in `.planning/` or anywhere else.
- **WIP cap**: at most 2 PRs open; one PR per phase.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Six independent phases, each one PR | WIP cap 2 and owner-only merges; independence lets any phase go next | — Pending |
| Skip new-project domain research | Chore mission on an existing codebase; the codebase map covers the context | — Pending |
| `git.create_tag: false` in config | Tags are Never-tier in `FLEET-POLICY.md` | — Pending |
| Do not generate `.claude/CLAUDE.md` | `CLAUDE.md` already points to `AGENTS.md`; this init is planning files only | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-21 after initialization*
