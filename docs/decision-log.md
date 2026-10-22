# COH — Decision Log

Durable product/engineering decisions for the **Cognitive Operating Harness (COH)**. Format follows COH's own Decision Log spec: question, selected option, rationale, alternatives, reopening conditions. Append-only; supersede rather than edit.

---

## D1 — v0.1 product track

- **Question:** Which of the two documented products is v0.1 — the local-first agent execution layer (Track A) or the hosted capture-planning workspace (Track B)?
- **Selected:** Track A — local-first agent execution layer.
- **Rationale:** Matches the PRD's core promise (spec gate, foreground, evidence, recovery for a solo AI-assisted developer); local-first canonical state is a hard requirement; Track B has no Execution Core and cannot enforce the product's guarantees.
- **Alternatives rejected:** Track B first (different product; loses the differentiator); both in parallel (splits a 1–2 person team).
- **Reopen when:** Track A is validated and a hosted/multi-device surface is prioritized. Track B docs are preserved in `chatprd-docs/deprecated/`.
- **Decided:** 2026-08-19, Silver.

## D2 — Implementation stack

- **Question:** Python core (Coding Rules/Technical Design) or TypeScript (feature specs' file plans)?
- **Selected:** Python 3.12+ backend: FastAPI, SQLAlchemy 2 + SQLite (WAL) + Alembic, Huey (SQLite-backed), pure-Python `execution-core` package; uv + pnpm polyglot monorepo; React/Vite reserved for the Phase 3 visual app. MCP adapter in Python.
- **Rationale:** The engineering-complete docs (Coding Rules, Technical Design) are Python; deterministic-core testing strategy (pytest/Hypothesis) fits; MCP server story is Python.
- **Alternatives rejected:** TypeScript core (would require rewriting both engineering baselines); Next.js stack (Track B only).
- **Consequence:** All 11 feature specs' "Files to Create/Modify" sections ported to the Python monorepo layout.
- **Decided:** 2026-08-19, Silver.

## D3 — Product name

- **Question:** Working name for the product formerly called "Agent-Independent Cognitive Execution System" / "CES".
- **Selected:** **Cognitive Operating Harness (COH)**. Category descriptor: neurodivergent cognitive execution system. Promise: "Start. Move. Recover. Finish." Principle: capability ≠ execution; COH changes conditions so intention can become action.
- **Rationale:** See `COH-cognitive-operating-harness.md` (branding analysis). Chemistry metaphor is brand mythology, not framework.
- **Decided:** 2026-08-19, Silver.

## D4 — Lifecycle: technical state machine vs COH phases

- **Question:** How do COH's five phases (Orient → Activate → Execute → Recover → Complete) relate to the technical lifecycle?
- **Selected:** The Execution Core state machine is canonical and 7-state: `INSPECT → SPECIFY → CONFIRM → PLAN → EXECUTE → VERIFY → COMPLETE`. **Checkpoint is a cross-cutting event** valid in any state; **Recover is an entry command** for resuming a session. The COH phases are the conceptual/user-facing layer mapped onto it:
  - **Orient** = Inspect + Specify + Confirm
  - **Activate** = Plan + NOW selection (activation-friction aware)
  - **Execute** = Execute
  - **Recover** = checkpoint/recovery (cross-cutting)
  - **Complete** = Verify + Complete
- **Rationale:** Keeps deterministic transitions testable while giving users a human model; resolves the PRD-vs-Technical-Design lifecycle conflict (evaluation §6 #4).
- **Reopen when:** Real usage shows the mapping confuses rather than clarifies.
- **Decided:** 2026-08-19, Silver.

## D5 — First agent adapter

- **Question:** Which agent environment does v0.1 integrate with first?
- **Selected:** **Claude Code via MCP.** The Python MCP server is the first (and reference) adapter; Cursor/Codex and others follow through the same provider-neutral contract.
- **Rationale:** MCP adapter already specified in the technical baseline; it's the environment in daily use; proves agent-independence via a standard protocol rather than a bespoke integration.
- **Decided:** 2026-08-19, Silver.

## D6 — Archive write-failure policy

- **Question:** PRD's retry + staging-buffer + fallback-file model, or the feature spec's degrade-and-continue model?
- **Selected:** **Degrade-and-continue** (per the Markdown Archive feature spec): bounded retry on next write, structured `archive_write_failed` result, checkpoint archive status `degraded`, non-blocking user warning, no in-memory staging buffer or automatic fallback file in v0.1.
- **Rationale:** Simpler, honest failure surface; staging buffers create silent-loss risk on crash; the workflow must never block on archival.
- **Reopen when:** Real archive-failure telemetry shows data loss users care about.
- **Decided:** 2026-08-19, Silver.

## D7 — Telemetry for v0.1

- **Selected:** **Local-only.** The Markdown archive + domain events are the audit stream. No remote collection in v0.1. The hosted telemetry design is deprecated to future reference; if remote telemetry ever ships it is opt-in, metadata-only, consent-gated, using the PRD event taxonomy (snake_case).
- **Decided:** 2026-08-19, Silver.

## D8 — v0.1 UI

- **Selected:** **None.** v0.1 output is agent-rendered (via MCP adapter). Focus/Timer, Timeline, Quest Map, and Recovery visual surfaces are Phase 3 discovery, driven by the same state model.
- **Decided:** 2026-08-19, Silver.

## D9 — Caveman's role

- **Selected:** Caveman is an **optional output-compression integration**, deferred past v0.1. It must preserve COH's protected structured fields and runs only after language-accessibility policy is applied. It is not a data-import dependency; the OAuth-import model belonged to deprecated Track B.
- **Decided:** 2026-08-19, Silver.

## D10 — Shared conventions (bundle)

- **Energy / activation-friction scales:** enums `low | medium | high` everywhere (no numeric scales in contracts; UI may map to visuals later).
- **Wire JSON casing:** **snake_case** for all API/adapter/MCP JSON (amends the Coding Rules' earlier camelCase note; matches every existing contract example and Python-native serialization).
- **Restart terminology:** canonical field is `restart_action` (UI copy may render it as "Start Here").
- **Archive default directory:** `.coh/archive/` relative to project root.
- **Event naming:** snake_case product events per PRD taxonomy, including `archive_recorded` and `archive_write_failed`.
- **Parking/drift classification:** deterministic, configurable heuristics in v1 — no ML classifier; thresholds kept as configuration for a possible later classifier.
- **Metrics:** PRD behavioral metrics are primary; Technical Design operational targets are engineering SLOs; Track B funnel metrics retired with Track B.
- **Adapter contract:** the PRD's contract section is the single normative definition; the Agent Adapter feature spec defers to it.
- **Decided:** 2026-08-19, Silver.

## D11 — Cognitive Readability Profile shapes prose rendering

- **Question:** How does the owner's Cognitive Readability Profile (CRP, "evidence-first constructive processing") apply to COH output?
- **Selected:** Behavioral Contract **§5 Prose Rendering Policy** (P-01…P-06), contract **1.1.0**. Structured §4 blocks keep their fixed ordering (navigation). Free prose around them is evidence-first, without prospective scaffolding, dense, with retrospective recap over threshold. In SPECIFY/CONFIRM, inspection findings render before the spec block, so the block functions as retrospective consolidation rather than an advance frame. Precedence: orientation/recovery framing > CRP minimal-signposting (recovery summary and foreground exempt from P-01/P-02). Protected fields guarded identically to Caveman via the compression guard; pipeline extends D9: language accessibility → CRP prose policy → optional Caveman. The profile is versioned user data kept outside this repository; only strong signals are enforceable rules, mild signals are soft presenter defaults with no lint/eval.
- **Rationale:** Two §4 templates (detour recommendation, verification) already follow the evidence→conclusion shape; the amendment generalizes that to prose without touching the state machine or invariants. The profile is preference-based, hence rules limited to strong signals and an explicit exemption where preferences plausibly invert (post-interruption recovery).
- **Alternatives rejected:** Reordering §4 blocks themselves (breaks navigation/recovery function, MAJOR bump, eval churn); encoding mild signals as rules (risk of hardening context-dependent preferences); leaving CRP as informal guidance (untestable, contradicts Phase 0 method).
- **Reopen when:** A profile retest contradicts a strong signal; recovery-mode usage shows the P-06 precedence is wrong; or comprehension/speed testing diverges from preference results.
- **Decided:** 2026-09-01, Silver.
- **Redacted:** 2026-10-21, personal profile details removed before the repository goes public. The decision is unchanged.

## D12 - Python floor 3.15 (amends D2)

- **Question:** D2 set "Python 3.12+". CI and the dev runtime run only 3.15, so the 3.12 promise is untested. Keep 3.12+ with a test matrix, or raise the floor?
- **Selected:** Python 3.15+. `requires-python = ">=3.15"`, ruff `target-version = "py315"`. The rest of D2's stack is unchanged.
- **Rationale:** COH is an application, not a library, so older interpreters buy nothing. Python has no LTS line; 3.15 (released 2026-10-01) has the longest support window. One tested version matches what CI runs.
- **Alternatives rejected:** 3.12+ with a CI matrix (doubles CI time to keep a promise no user needs); leaving 3.12+ untested.
- **Reopen when:** a required dependency lacks 3.15 wheels, or COH ships a component meant to be imported by other projects.
- **Decided:** 2026-10-14, Silver.

## D14 - One protected test tree

- **Question:** Tests live in eight places (each package's `tests/`, `apps/api/tests/`, `evals/`), with test config inside `pyproject.toml`. How can the fleet's builder be kept from editing the checks that judge its work?
- **Selected:** All tests, eval scenarios, fixtures and test config live under `tests/`, with root `pytest.ini` and `.coveragerc`. `tests/**`, `conftest.py`, `pytest.ini`, `.coveragerc`, `tox.ini`, `setup.cfg`, `.github/workflows/**` and `.github/CODEOWNERS` are the protected check set.
- **Rationale:** One path set is simple to protect and audit. Fleet decision H-87 (loop engineering): checks are written before the build by the lead seat and kept out of the builder's reach.
- **Alternatives rejected:** protecting eight scattered paths; a separate checks repository (fork PRs on a public repo get no secrets to read it); a path-restriction ruleset (push rulesets need GitHub Team).
- **Decided:** 2026-10-14, Silver.

## D15 - checks-guard

- **Question:** The builder writes code and could also edit the tests and CI that judge it. Instructions forbid it; nothing enforces it on GitHub.
- **Selected:** A required `checks-guard` job on `pull_request_target` that reads the PR through the API and fails when a protected path (D14) changes in a commit not authored by the lead seat, or when an added line weakens a check anywhere. A second job, `checks-edits`, flags edits or deletions of existing protected lines; from Nov 1 (public repo) it gates on owner approval through the `checks-approval` environment.
- **Rationale:** Fleet decision H-87. `pull_request_target` runs the base copy, so a PR cannot change its own judge. Fail closed on any missing data.
- **Limits:** The fleet and the owner share one GitHub identity, so the commit author is a convention the fleet's Never tier protects, not a credential. A separate fleet account would make it a credential.
- **Decided:** 2026-10-14, Silver.

## D13 - D12 reopened: dependency wheels on 3.15

- **Question:** D12's reopen condition ("a required dependency lacks 3.15 wheels") was met at its own merge: five locked packages had no cp315 wheels. Keep 3.15, or lower the floor?
- **Selected:** Keep Python 3.15+ (D12 stands). Locked versions are upgraded to releases that ship cp315 wheels (pydantic-core, markupsafe, httptools, uvloop). pyyaml has no cp315 wheel yet and builds from sdist; accepted while CI's cold `uv sync` passes.
- **Rationale:** The gap was stale locked versions, not missing 3.15 support upstream. A 3.14 floor would undo D12 for one package that has a working source build.
- **Alternatives rejected:** lowering the floor to 3.14 (wheels exist for all five); pinning to old versions without cp315 wheels.
- **Reopen when:** a required dependency fails to install on 3.15 from wheel or sdist, or pyyaml's sdist build fails in CI.
- **Decided:** 2026-10-14, Silver.

## D16 - certifi under MPL-2.0

- **Question:** `certifi` (MPL-2.0) is already in `uv.lock` as a transitive dependency of `httpx` and `httpcore`; `httpx` is in the root `dev` group (the FastAPI test client needs it). The license policy (`FLEET-POLICY.md`, `CONTRIBUTING.md`) allows MIT, Apache-2.0, BSD and ISC without approval; anything else needs the owner. Keep it, or drop `httpx`?
- **Selected:** Approve `certifi` under MPL-2.0 as a transitive dependency, used unmodified. No other MPL-2.0 package is approved by this entry.
- **Rationale:** MPL-2.0 is file-level copyleft. Installing and using `certifi` for development and tests is not distribution and triggers no MPL obligation. Redistributing MPL-covered files, changed or not, carries the license's notice and source-availability requirements; COH does not vendor or redistribute `certifi` today. The package reaches the lock only through the dev group, so no COH runtime component ships it. The dependency audit (chores-q4 Phase 3) needs the license question closed before it runs.
- **Alternatives rejected:** dropping `httpx` (breaks the API tests to avoid a license that imposes no obligation on dev-only use); a blanket MPL-2.0 allowance (wider than the one package that needs it).
- **Reopen when:** COH modifies, vendors or redistributes `certifi` files (for example in a runtime dependency or a packaged release), or another MPL-2.0 or weak-copyleft package enters the lock.
- **Decided:** 2026-10-22, Silver (owner answer Q13, chores-q4 planning review).

## D17 - pathspec under MPL-2.0 (D16 reopened)

- **Question:** ADR-0002 adds mypy 2.4.0 to the root `dev` group. Its dependency closure includes `pathspec` 1.1.1 (MPL-2.0), which meets D16's reopen condition ("another MPL-2.0 or weak-copyleft package enters the lock"). Approve it, or keep mypy out?
- **Selected:** Approve `pathspec` under MPL-2.0 as a dev-only transitive dependency of mypy, used unmodified. D16 stands for `certifi`. No other MPL-2.0 package is approved by this entry.
- **Rationale:** The same distinction as D16: using `pathspec` for type checking in development and CI is not distribution and triggers no MPL obligation. Redistributing MPL-covered files, changed or not, carries the license's notice and source-availability requirements; COH does not vendor or redistribute `pathspec`. It reaches the lock only through the dev group, so no COH runtime component ships it.
- **Alternatives rejected:** rejecting `pathspec`, which leaves TYPE-03 unmet until a mypy release without it is evaluated; running mypy through an unlocked `uvx` (installs the same closure and drops the version pin, ADR-0002 option C); a blanket MPL-2.0 allowance (wider than the one package that needs it).
- **Reopen when:** COH modifies, vendors or redistributes `pathspec` files, `pathspec` moves out of the dev group, or another MPL-2.0 or weak-copyleft package enters the lock.
- **Decided:** 2026-10-22, Silver (owner answer to the ADR-0002 decision, chores-q4 Phase 4).
