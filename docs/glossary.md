# COH — Glossary (Canonical Terminology) v1.0

**Status:** canonical terminology reference · **Updated:** 2026-08-19
Companion: `COH-PRD.md` (its Glossary section is a core subset of this document) · `COH-Data-Dictionary.md` (field-level definitions) · `../COH-Decision-Log.md` · `../coh-phase-0/COH-Behavioral-Contract.md`

Rules: one definition per term, defined here and referenced elsewhere. New or changed terms require updating this file in the same change. User-facing language follows the Plain Technical Language spec: neutral, diagnosis-free, literal.

---

## 1. Brand & Concept

| Term | Definition |
|---|---|
| **COH** | Cognitive Operating Harness — the product. An external execution layer that helps turn intention into completed action. |
| **Cognitive Operating Harness** | Full product name (Decision D3). "Operating" = the layer surrounding cognition while it works, like an operating environment/runtime. |
| **Cognitive execution system** | The product *category* COH belongs to (neurodivergent cognitive execution system). Former working name "CES" — retired. |
| **Core promise** | "Start. Move. Recover. Finish." |
| **Capability ≠ execution** | COH's foundational principle: being able to do something is not the same as executing it; execution depends on conditions. |
| **Cognitive chemistry** | COH's brand metaphor (mythology beneath the framework, not the framework itself): activation energy → task initiation; catalyst → friction-reducing intervention; reaction conditions → cognitive/environmental state; buffer → routine/scaffolding; threshold → overload point; equilibrium → sustainable regulation. |
| **COH phases** | The user-facing model: **Orient → Activate → Execute → Recover → Complete**, mapped onto the technical lifecycle (Decision D4). |
| **Orient** | Phase: what am I doing, why, what matters now. Technical states INSPECT + SPECIFY + CONFIRM. |
| **Activate** | Phase: cross the task-initiation barrier. Technical state PLAN + NOW selection (activation-friction aware). |
| **Execute (phase)** | Phase: maintain useful forward motion. Technical state EXECUTE. |
| **Recover (phase)** | Phase: restore context after distraction, overload, interruption, or drift. Cross-cutting Checkpoint event + Recover command. |
| **Complete (phase)** | Phase: recognize done, verify outcome, close the loop. Technical states VERIFY + COMPLETE. |
| **AuDHD-informed, diagnosis-neutral** | Design stance: reduce ambiguity and context-reconstruction cost through clear state and predictable transitions, without diagnosing users or using clinical labels. |

## 2. Lifecycle & Sessions

| Term | Definition |
|---|---|
| **Lifecycle** | The canonical 7-state machine owned by the Execution Core: `INSPECT → SPECIFY → CONFIRM → PLAN → EXECUTE → VERIFY → COMPLETE`. |
| **INSPECT** | Read-only gathering of repository/project context before asking the user anything. |
| **SPECIFY** | Deriving and proposing the specification from evidence. |
| **CONFIRM** | User confirms or corrects the proposed spec; readiness is computed. |
| **PLAN** | Converting a confirmed spec into dependency-aware atomic tasks; foreground computed. |
| **EXECUTE (state)** | Bounded execution slices under the permission matrix. |
| **VERIFY** | Mapping evidence to done-when criteria; computing completion states. |
| **COMPLETE (state)** | Deliverable done; completion summary emitted; parked items preserved. |
| **Checkpoint** | A persisted recovery record (objective, current state, material context, literal restart action). A **cross-cutting event** valid in any state — not a lifecycle state. |
| **Recover (command)** | The entry command that resumes a session from its latest valid checkpoint and renders the recovery summary. Not a lifecycle state. |
| **Transition (T1–T11)** | A guarded state change defined in the Behavioral Contract. Invalid transitions are rejected with the blocked reason and smallest remediation. |
| **Session** | One execution engagement on a project, with a lifecycle state, an intent, and a version (`ExecutionSession`). |
| **Session intent** | Declared or inferred mode of work: `execute`, `plan`, `brainstorm`, `review`, `study`, `recover`. Determines the completion contract and drift definition. Inferred, displayed, overridable. |
| **Goal revision** | A change of objective mid-work (T10): checkpoint first, new spec revision, prior decisions/evidence preserved as history. |
| **Focus profile** | Default configuration bundle: NOW + NEXT 2 foreground, energy/friction shown, drift detection on, one recommended action, persistent checkpoints, decision rationale and evidence gates enabled. |

## 3. Specification & Readiness

| Term | Definition |
|---|---|
| **Specification (spec)** | Structured definition of WHAT, WHY, DELIVERABLE, done-when criteria, constraints, non-goals, assumptions, and unknowns. Revisioned; superseded, never overwritten. |
| **Spec Gate** | The mandatory gate converting intent into a confirmed spec before material execution (the Orient mechanism). |
| **Spec clarity** | Qualitative spec completeness: `low`, `medium`, `high`, `ready`. Percentages only in expanded detail. |
| **Readiness** | Binary execution gate: `ready` or `blocked`. Ready requires: required fields present, no unresolved blocking unknown/assumption, no unconfirmed material assumption policy requires surfacing. |
| **Assumption** | A statement treated as true while work proceeds. Classes: **safe** (proceed unless contradicted), **material** (could meaningfully affect implementation; surface for confirmation), **blocking** (could solve the wrong problem or cause harm; must be resolved). |
| **Unknown** | An identified missing fact. A *blocking unknown* keeps readiness at `blocked`. |
| **Done when** | A measurable condition establishing that a task, spec, or deliverable is complete. |
| **Acceptance criterion** | An individually evidence-checkable element of done-when, referenced by evidence records (criterion ref). |
| **Confirmation model** | The user confirms/corrects a proposed spec rather than authoring one; COH asks only questions it cannot answer from evidence, grouped and minimal, each with a recommended default. |
| **Question budget** | The policy that blocking questions are few, grouped, high-value, and never ask what inspection could discover. |

## 4. Planning & Foreground

| Term | Definition |
|---|---|
| **Task** | An atomic, dependency-aware unit of work with a literal action and measurable done-when condition. |
| **Action literal (`action_literal`)** | The concrete, startable phrasing of a task's action ("Run the harness with X and trigger Y"), required for foreground eligibility. |
| **Foreground** | The visible executable surface: exactly one NOW and at most two NEXT tasks (server-enforced invariant I-01). |
| **NOW task** | The single literal, startable action currently recommended. Never a task with unresolved dependencies. |
| **NEXT 1 / NEXT 2** | The at-most-two upcoming tasks shown after NOW. Everything else is background or parked. |
| **Activation friction** | Difficulty of *starting* an action, independent of duration or complexity. Enum `low|medium|high`. |
| **Energy level** | Cognitive/physical demand of a task. Enum `low|medium|high`. |
| **Goal leverage** | Sequencing weight for expected progress toward the deliverable — never "easiest first". |
| **Plan exit rule** | Planning is complete when deliverable, immediate physical next action, essential dependencies, major risks, and completion evidence are defined well enough to begin. |
| **Foreground promotion** | Recalculation of NOW/NEXT after completing, blocking, parking, or interrupting NOW; deterministic ranking with stable tie-breakers. |

## 5. Execution, Autonomy & Evidence

| Term | Definition |
|---|---|
| **Permission matrix** | Canonical autonomy policy (PRD): inspection/analysis/spec/plan automatic; tests/verification automatic under granted permissions; small bounded changes automatic after spec confirmation; large-scope/destructive/scope-expanding actions require explicit confirmation; spec and plan confirmation always belong to the user. |
| **Bounded slice** | The unit of agent execution: work that returns to a checkpoint or decision gate instead of silently expanding scope. |
| **Scope expansion** | Newly discovered work beyond the confirmed spec; requires relevance/blocking evaluation and (if large) confirmation — or parking. |
| **Completion states** | `implemented` → `tested` → `verified` → `done`. Separate from task status. |
| **Implemented** | The change exists, with no evidence beyond its existence. |
| **Tested** | Tests were run and results recorded, but done-when criteria are not (all) evidence-satisfied. |
| **Verified** | Required evidence has been evaluated against the agreed done-when criteria. |
| **Done** | Every done-when criterion has non-stale qualifying evidence or recorded user acceptance. |
| **Evidence** | A test result, artifact, review finding, reproducible behavior, or user acceptance mapped to a criterion (with spec revision pinned). |
| **Evidence gate** | Invariant I-03: never report Verified/Done without criterion-linked, non-stale, qualifying evidence. Honest ceiling without it: Implemented or Tested. |
| **Authority level** | Evidence provenance class: `tool_verified` (COH observed the tool run), `agent_reported` (claimed without observed output — supplemental only), `user_accepted` (explicit acceptance with rationale). Only the first and last can satisfy criteria. |
| **Stale evidence** | Evidence pinned to a superseded spec/implementation revision; flagged `needs revalidation`, cannot satisfy criteria. |

## 6. Decisions, Parking, Drift

| Term | Definition |
|---|---|
| **Decision** | Durable record of a selected option: question, outcome, rationale, alternatives (with rejection reasons), evidence refs, materiality, lifecycle (`active`/`superseded`/`reopened`). |
| **Materiality rule** | A decision is material if it constrains future implementation, changes external behavior, is costly to reverse, or resolves a blocking assumption. Minor reversible choices stay in task notes. |
| **Supersession** | Replacing a decision (or spec) with a new revision while preserving and linking the prior record. Nothing historical is overwritten. |
| **Parking item / Parking lot** | A structured capture of a non-current idea, discovery, follow-up, or secondary action — with source task, context, relevance, blocking impact, suggested disposition, optional revisit trigger — stored without touching the NOW task (I-10). |
| **Auto-park** | Deterministic rule (D10): relevance = low AND blocking = false → park automatically, disclose in the next update. |
| **Promotion (parking)** | Converting a parked item into a planned task, carrying its captured context; the original item survives as linked history. |
| **Drift** | Deviation from the active session intent that has *not* been consciously accepted. Intent-relative (I-11): each intent defines its own drift. |
| **Detour** | A consciously chosen deviation — intentional, recorded with a return point; repeated warnings suppressed for the same evidence until it ends. |
| **Rabbit-hole rule** | Multi-signal intervention threshold: prolonged estimate overrun + little new evidence + multiple side branches + increasing objective distance. |
| **Brainstorm convergence gate** | The mandatory end of divergence: candidates evaluated against stated criteria → one recommendation + retained alternatives + next action. |
| **Neutral language** | Invariant I-07: interventions describe observable state and a next move; no clinical terms, shame framing, or blame. |

## 7. Checkpoints, Recovery, Archive

| Term | Definition |
|---|---|
| **Progress record** | The interruption-safe record every task maintains: status, last update time, completed work, attempted work, blockers, ordered next steps. Created/updated *before* any foreground switch (I-05). |
| **Restart action (`restart_action`)** | The literal imperative next step stored in every checkpoint. Canonical term (D10); rendered in UI as "Start Here". |
| **Recovery summary** | The structured resume output: GOAL → WHY → LAST VERIFIED → LAST DECISION → NOW → NEXT 2 → PARKED count → START HERE. |
| **Archive** | The append-only, human-readable Markdown record of every user input, agent output, tool event, state change, and linked artifact. Default location `.coh/archive/` (D10). |
| **Archive entry** | One recorded interaction in a session archive file, with a stable anchor ID (`{actor}-{ISO8601}-{4char-hash}`) and closing delimiter. Never rewritten (I-04). |
| **Anchor** | The stable per-entry ID that lets checkpoints and recovery link to exact archive positions (path + timestamp + anchor). |
| **Archive status** | Checkpoint-level health of archival: `healthy` or `degraded`. |
| **Degrade-and-continue** | Archive failure policy (D6): failed writes return `archive_write_failed`, mark checkpoints degraded, warn non-blockingly, never block or lose the in-memory interaction; archival resumes on the next successful write. |
| **Rotation** | Splitting a session archive file when it exceeds 5 MB (`…--part-N.md`); pointers identify the correct part. |
| **Human-readable export** | The portability guarantee: structured state plus archive exportable and inspectable without COH. |

## 8. Architecture & Integration

| Term | Definition |
|---|---|
| **Execution Core** | The deterministic, dependency-light Python domain layer owning lifecycle, policies, readiness, foreground, drift, evidence, and invariant enforcement. Sole authority for execution state. |
| **Proposal-only AI** | Invariant I-06: LLM output is a proposal validated by schema + domain policy before any authoritative change. |
| **Agent adapter** | Provider-neutral integration translating an agent environment's capabilities into COH's contract (normative definition: COH-PRD → Agent Adapter Contract). |
| **Capability negotiation** | Handshake in which an adapter declares supported capabilities; missing ones degrade gracefully (`NOT_IMPLEMENTED`, I-14). |
| **MCP adapter** | The Python MCP server — COH's first adapter, targeting Claude Code (D5). Calls application services; never bypasses the core. |
| **Protected fields** | The canonical list (PRD) that no compression/transformation may remove or conflate: what, deliverable, done-when, constraints, non-goals, rationale, acceptance criteria, action literals, dependencies, required evidence, NOW identity, restart_action, archive refs, negations. |
| **Caveman** | External companion product; in COH it is an *optional output-compression integration*, deferred past v0.1 (D9). Must respect protected fields; applied only after language-accessibility policy. |
| **Plain Technical (language profile)** | Accessibility profile: short sentences, common vocabulary, literal phrasing, explicit causality; technical terms kept and briefly defined on first meaningful use. Independent of verbosity. Precedence: accessibility beats compression. |
| **Domain event** | Append-only audit record of a state change (not full event sourcing). |
| **JobRunner** | The protocol behind which background jobs run (Huey implementation in v0.1). |
| **Local-first** | Project-local canonical state (SQLite + archive files); no cloud dependency, no remote telemetry in v0.1 (D1/D7). |
| **Track A / Track B** | Historical labels from the doc review: Track A = this product (local-first execution layer, chosen); Track B = deprecated hosted capture-planning SaaS (in `deprecated/`). |
| **Causal CRDT / Sync conflict** | Future-sync vocabulary (post-v0.1): CRDT merging for append-only aggregates; a *sync conflict* is a semantic incompatibility requiring explicit resolution — never last-write-wins for lifecycle. |
| **Idempotency** | Repeating an operation yields the same effective result without duplicating state. Commands carry idempotency keys *and* `expected_version` (concurrency control — the two are not interchangeable). |

## 9. Evaluation

| Term | Definition |
|---|---|
| **Behavioral contract** | `coh-phase-0/COH-Behavioral-Contract.md`: the versioned, testable definition of states, transitions (T-ids), invariants (I-ids), intents, and output contract. |
| **Invariant (I-01…I-14)** | A binary-testable rule the system must never violate; referenced by eval scenarios; critical ones (I-02, I-03, I-08, I-13) block release on any failure. |
| **Scenario suite** | The versioned YAML evals in `coh-phase-0/evals/` run against the core with a mock adapter. |
| **Rubric** | Five-dimension human scoring (usefulness, grounding, actionability, concision, safety), 0–2 each, pass ≥8/10 with no zero. |
| **Critical safety event** | Unconfirmed destructive action, evidence-gate bypass, injection compliance, or clinical labeling. Zero tolerance; blocks release. |
| **Output contract** | The fixed section ordering for each output type (spec proposal, foreground, recovery summary, verification). |

---

*Maintenance: this glossary is canonical. The PRD Glossary is a curated subset; the Data Dictionary (`COH-Data-Dictionary.md`) holds field-level detail. Terms may be added by PR; renames or semantic changes require a Decision Log entry.*
