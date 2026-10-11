# COH (Cognitive Operating Harness): Agent Instructions

COH is a local-first, Python-based execution layer that helps solo AI-assisted developers turn intention into completed action. This repository holds the code, the Phase 0 documentation and the behavioral evals. (Working name history: "Cognitive Execution System / CES", renamed 2026-08-19.)

## Read these first

- `FLEET-POLICY.md`: what you may do on your own (Auto), what needs a decision (Ask) and what is forbidden (Never). If an action is not covered, treat it as Ask.
- `CONTRIBUTING.md`: workflow, checks and the Definition of Done.
- `docs/coding-rules.md`: engineering standards (architecture, layers, naming, testing).
- `docs/decision-log.md`: durable decisions D1 onward. Check it before proposing a change that touches a recorded decision.
- `docs/adr/`: architecture decision records and the template.
- `docs/behavioral-contract.md`: state machine, invariants I-01 to I-14, transitions, output contract, prose rules P-01 to P-06.
- `docs/eval-rubric.md` and `evals/`: scoring, release thresholds and the 19 scenario suite. Scenarios reference contract IDs; keep them in sync.
- `docs/glossary.md`: canonical terminology. One definition per term; a rename or semantic change needs a decision-log entry.
- `docs/feature-specs/`: the feature specs the slices implement.

Not in this repository: the PRD, the Technical Design, the Data Dictionary and the readability profile. Do not look for them, do not recreate them from memory, and ask the owner if a task depends on one.

## Layout

```
packages/execution-core   pure domain model, policies, state machine (no framework imports)
packages/persistence      SQLAlchemy + Alembic (alembic/ lives here)
packages/archive          append-only Markdown interaction archive
packages/prose            prose rendering policy
packages/mcp_adapter      MCP adapter (first adapter: Claude Code)
packages/application      application services
apps/api                  FastAPI HTTP adapter
evals/                    behavioral scenarios and harness
```

## Commands

```bash
uv sync --all-packages
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest <package>/tests        # run per package until the root run is fixed
```

CI runs ruff on the packages and the tests per package (`.github/workflows/ci.yml`). Known gaps (Pyright not in CI, the root `pytest` run) are listed in `CONTRIBUTING.md`.

## Hard rules

- The Execution Core is deterministic and authoritative. AI output is proposal-only; domain policy validates it before any state change.
- No FastAPI, SQLAlchemy, Huey, MCP or provider-SDK imports in `packages/execution-core`. Routes and MCP tools call application services, never repositories.
- v0.1 is local-first: no cloud infrastructure, no remote telemetry, no UI. Agent-rendered output goes through the Claude Code MCP adapter.
- The interaction archive (`.coh/archive/`) is append-only. Archive failures degrade and continue; they never block work.
- Wire JSON is snake_case end to end (D10).
- Record semantics-changing choices in `docs/decision-log.md` (append; supersede, never edit). Record architecture choices as ADRs.
- User-facing text is neutral and diagnosis-free ("context changed", "decision needed", "blocked", "recovery step").
- Never add a dependency, change a public contract or the archive format, or change execution semantics without an accepted decision.
- No secrets, tokens, personal data or real user data in code, commits, PR text, queue items or logs. Use synthetic fixtures.

## How to write to the owner

Applies to queue items, PR descriptions and summaries the owner reads:

- Lead with concrete observations and evidence, and let the conclusion follow. Do not open with previews or agendas ("There are three things...", "First I will...").
- Keep density high and cut filler. Introduce a term after the behavior it names.
- End an explanation longer than about 12 lines with a recap of at most 3 lines.
- Orientation and recovery output (resuming work, restoring context) may state the goal first.
- Never drop causality, negation, warnings, constraints or decision rationale in the name of brevity.
- Every question carries a recommended default.
