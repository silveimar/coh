# COH — Cognitive Operating Harness · Agent Instructions

This project folder contains the product documentation for **COH (Cognitive Operating Harness)** — a local-first, Python-based execution layer that helps solo AI-assisted developers turn intention into completed action. Working name history: "Cognitive Execution System / CES" (renamed 2026-08-19).

## Canonical documents (read these; treat everything else as reference)

- `COH-Decision-Log.md` — durable decisions D1–D11 (track, stack, name, lifecycle, adapter, policies, prose rendering). **Check here before proposing changes that touch a recorded decision.**
- `COH-Cognitive-Readability-Profile.md` — versioned user-profile data (CRP v0.1): Silver's readability preferences. Source for Behavioral Contract §5 (Prose Rendering Policy, P-01…P-06). Strong signals only are rules; mild signals are soft defaults.
- `chatprd-docs/COH-PRD.md` — product requirements; also the normative agent-adapter contract and protected-field list.
- `chatprd-docs/COH-Technical-Design.md` — architecture, data model, testing, deployment.
- `chatprd-docs/COH-Coding-Rules.md` — engineering standards (Python 3.12+/FastAPI/SQLAlchemy 2/SQLite/Huey; uv + pnpm monorepo; snake_case wire JSON).
- `chatprd-docs/COH-Glossary.md` — **canonical terminology** (the PRD glossary is a subset). One definition per term; renames/semantic changes need a Decision Log entry.
- `chatprd-docs/COH-Data-Dictionary.md` — **canonical field-level reference**: conventions, all enum value sets, every entity, wire objects, archive file format, event taxonomy. Schema changes must update this file in the same change as the Alembic migration.
- `chatprd-docs/Feature Spec_ *.md` — 11 v0.1 feature specs, ported to the Python layout.
- `ChatPRD-Docs-Evaluation.md` — documentation review, inconsistency register, and modifications log.
- `COH-cognitive-operating-harness.md` — branding/conceptual model (Orient → Activate → Execute → Recover → Complete).
- `coh-phase-0/` — Phase 0 deliverables: `COH-Behavioral-Contract.md` v1.1.0 (state machine, invariants I-01…I-14, output contract, prose rendering policy P-01…P-06), `COH-Eval-Rubric.md` (scoring + pre-committed release thresholds), and `evals/` (versioned YAML scenario suite, 19 scenarios incl. `prose-*` for P-01…P-06; destined for the repo's `evals/` directory). Eval scenarios reference contract invariant/transition/prose-rule IDs — keep them in sync.

## Hard rules for agents working here

- `chatprd-docs/deprecated/` is history — never implement from it or edit it.
- The Execution Core is deterministic and authoritative; AI output is proposal-only.
- v0.1 is local-first: no cloud infrastructure, no remote telemetry, no UI (agent-rendered output via the Claude Code MCP adapter).
- The interaction archive (`.coh/archive/`) is append-only; archive failures degrade-and-continue, never block work.
- Record semantics-changing choices in `COH-Decision-Log.md` (append; supersede, don't edit).
- Use neutral, diagnosis-free language in all user-facing text.
- **Communicate per the CRP** (`COH-Cognitive-Readability-Profile.md`): when explaining, proposing, or reviewing anything to Silver in this project, lead with concrete evidence/observations and let the conclusion emerge — never open with previews or agendas ("There are three things…", "First I'll…"). Keep density high, cut filler, introduce a term after the behavior it names, and end explanations longer than ~12 lines with a recap of ≤3 lines restating the model. Exception: orientation/recovery output (resuming work, restoring context) may use prospective framing — there, GOAL-first *is* the model being handed back. Never let compression or reordering drop causality, negation, warnings, constraints, or decision rationale. Strong profile signals are rules; mild signals (3–2) are soft defaults — don't harden them.
