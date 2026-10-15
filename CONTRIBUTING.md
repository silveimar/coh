# Contributing to COH

This guide and Definition of Done (DoD) apply to everyone who changes this repository: the owner and the fleet seats (lead, builder, checker). Three files work together:

- **[docs/coding-rules.md](docs/coding-rules.md)**: the engineering standards (architecture, naming, do's and don'ts, testing). This guide does not repeat them; it says how a change moves from branch to merge.
- **[FLEET-POLICY.md](FLEET-POLICY.md)**: what the fleet may do on its own (Auto / Ask / Never).
- **[docs/decision-log.md](docs/decision-log.md)**: durable product and execution-semantics decisions (D1 onward). Check it before proposing a change that touches a recorded decision.
- **[docs/adr/](docs/adr/README.md)**: architecture decision records, with a template. Use one for any technical or architectural choice (see below).

Changing this file is an Ask-tier change for the fleet and goes through a PR like code.

## Principles

- **One concern per PR.** Do not mix a tooling change with a feature, or a refactor with a fix.
- **The slice spec is the scope.** Anything it does not say is a question for the owner, however reasonable it seems.
- **Green before and after.** The full suite passes before you start and after you finish.
- **The Execution Core is authoritative.** AI output is proposal-only. Business logic never goes into routes, MCP tools, ORM models or job decorators (see the coding rules).
- **No secrets, ever,** in code, commits, PR text or logs.

## Setup

Requires Python 3.15+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repository-url> && cd coh
uv sync --all-packages
```

Use one `uv sync` per git worktree. Never share or symlink a `.venv` between worktrees.

## Workflow

1. **Branch** from an up-to-date `main`: `type/short-slug` (for example `chore/uv-migration`, `feat/foreground-limit`, `fix/archive-rotation`).
2. **Commit** in small steps. Use `type: summary` (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`), imperative mood, subject under about 72 characters.
3. **Open a draft PR** early. Mark it ready when the DoD below is complete.
4. **Review.** At most **2 review rounds**. A third goes to the lead, then to the owner.
5. **Merge.** `main` takes changes by PR only. Never push to `main`; never force push. Once the ruleset is in place it requires a PR, linear history, an up-to-date branch and green required checks.

## Checks

Run these before asking for review. They are the gates in `docs/coding-rules.md`.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

CI (`.github/workflows/ci.yml`) currently runs ruff (check and format) on the whole repository (`.`), the tests per package with coverage, and the eval harness (`tests/evals`).

**Known gaps, tracked for the foundation mission:**

- CI does not run `pyright` yet, although the coding rules make it a gate. Run it locally until it does.
- The planned additions are not wired up yet: dependency audit (pip-audit or osv-scanner), Trivy, deptry, pre-commit, and the `fleet/checker` required status. Add each in its own PR.
- CI enforces a coverage floor only for the Execution Core (`--cov-fail-under=90`, lines). The other packages have no enforced floor yet; set each at current coverage and let it only go up.

## Definition of Done

A PR is done when **every** item holds:

- [ ] The change matches the slice spec. Nothing beyond it. Any choice the spec did not dictate is listed in the PR description.
- [ ] `ruff check`, `ruff format --check`, `pyright` and `pytest` pass locally, and CI is green.
- [ ] The behavioral evals still pass their thresholds (`uv run pytest tests/evals`).
- [ ] Tests cover the change: every new policy, state-machine transition and invalid transition, persistence mapping or API behavior has a test. Execution Core coverage stays at or above 90%.
- [ ] New code is typed. No new lint or type suppression without a one-line justification and a linked issue or test.
- [ ] Layer rules hold: no FastAPI, SQLAlchemy, Huey, MCP or provider-SDK imports in `packages/execution-core`; routes and MCP tools call application services and never repositories.
- [ ] No new dependency without an accepted ADR. Licenses other than MIT, Apache-2.0, BSD or ISC also need owner approval.
- [ ] A schema change has an accepted ADR and ships with its Alembic migration in the same PR (migrations live in `packages/persistence/alembic`). Applied migrations are never rewritten.
- [ ] A semantics-changing choice is recorded in `docs/decision-log.md` (append; supersede, never edit), with policy tests. Any architecture decision from the list below has an accepted ADR.
- [ ] Docs that describe the change are updated (README, feature spec, glossary if a term changed).
- [ ] User-facing text is neutral and diagnosis-free ("context changed", "decision needed", "blocked", "recovery step").
- [ ] The archive stays append-only. Archive failures degrade and continue; they never block work.
- [ ] No secrets, tokens, personal data or real user data in the diff. Tests use synthetic fixtures.
- [ ] The slice's proof file lists the commands run and their results.
- [ ] `fleet/checker` has posted `success` on the **exact head SHA** (once that status exists). A later commit, even docs-only, needs a new verdict.
- [ ] No Ask-tier question is still open.

## Pull requests

The PR description gives:

- **The chain:** card, then spec, then the COH goal it serves.
- **What changed and why,** in a few lines.
- **Choices not dictated by the spec,** each with its reason.
- **Checks run** and their results.
- **Risk and rollback** when runtime behavior changes.

Keep the diff small enough to review in one sitting; split it if not. A PR template under `.github/` is a foundation-mission deliverable and will carry these fields.

## Decisions that need the owner first

Stop and raise a decision (with a recommended default) before you do any of these. Each one needs an ADR (`docs/adr/0000-template.md`), accepted by the owner before the work continues:

- add a dependency;
- change a public API contract, the wire format (snake_case JSON, D10) or the archive format;
- add a service or datastore, or any Docker, Redis, Celery or cloud infrastructure (D1, D7);
- change execution semantics, readiness, autonomy, foreground, drift, language or verification policy;
- do a cross-module refactor or a schema migration.

Execution-semantics changes also get a `docs/decision-log.md` entry. The ADR README explains which record to use.

## Tests

- pytest, with Hypothesis for state-machine and policy invariants. Test files are `test_*.py`, under `tests/` (`tests/packages/<package-dir>/`, `tests/apps/api/`, `tests/evals/`). Pytest settings live in `pytest.ini` and coverage settings in `.coveragerc`.
- Ordinary CI never calls a live model provider. Use fakes or recorded fixtures.
- Never disable, skip or weaken a test, linter or scanner to make a change pass. Fix the cause or raise it as a decision.
- Tests, eval scenarios and the behavioral contract reference invariant IDs (I-01 to I-14) and prose rules (P-01 to P-06). Keep them in sync when you change one.

## Security

- Dependencies are pinned through `uv.lock`, which is committed.
- Do not bind services to `0.0.0.0`.
- Authentication, cryptography and calls to external APIs need explicit owner approval.
- Report a suspected vulnerability privately to the owner, not in a public issue.

## Releases and deploys

Tags, releases and package publishing are done by the owner only. Deploy steps arrive with the foundation mission; until then there is nothing to deploy.

## Questions

Ask early. A short question with a recommended default costs less than a large PR in the wrong direction.
