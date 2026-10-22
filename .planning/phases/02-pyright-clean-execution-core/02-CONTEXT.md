# Phase 2: Pyright clean execution-core - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning
**Type:** chore. Protected check set: not touched.

<domain>
## Phase Boundary

`packages/execution-core` reaches 0 pyright errors (baseline 18 at f3743a1), with no behavior change and no change to the value or form of any stored or serialized datetime. Requirement: TYPE-02.

In scope: the 13 `Field(default_factory=datetime.utcnow)` sites, `policies/integrity_policy.py:69`, `state_machine/lifecycle.py:69-71`, `policies/parking_policy.py:125`, all under `packages/execution-core/src/execution_core/`.
Out of scope: the existing aware `datetime.now(UTC)` sites (mutators and aware default lambdas); switching any timestamp to timezone-aware; pyright errors in other packages or under `tests/`.
</domain>

<decisions>
## Implementation Decisions

### utcnow replacement
- **D-01:** Every `datetime.utcnow` default factory becomes a factory that returns naive UTC: `datetime.now(UTC).replace(tzinfo=None)`. Same wall-clock value, `tzinfo is None`, same `isoformat()` string. Reason: `_serialize_for_json` in `packages/persistence/src/persistence/infrastructure/mappers.py:43-44` writes `isoformat()` into JSON columns (`specifications.done_when/assumptions/unknowns`, `checkpoints.spec_snapshot`); an aware default would add `+00:00` to newly stored strings, a stored-format change that needs a decision-log entry.
- **D-02:** The expression lives in one helper in a new leaf module of execution-core (for example `execution_core/domain/clock.py`, `utc_now_naive() -> datetime`) that imports no domain module, passed directly as `default_factory`. Reason: 13 sites in 7 files; one definition prevents a copy that drops `.replace(tzinfo=None)`. Module name must follow `docs/coding-rules.md` (no `utils`/`misc`).
- **D-03:** The ~25 existing `datetime.now(UTC)` sites stay as they are (for example `domain/task.py:78-124`, `domain/checkpoint.py:33`, `events/domain_events.py:18`). They produce no pyright error, and changing them changes stored form.

### Other five errors
- **D-04:** `policies/parking_policy.py:125`: discard the unused value as `_`, matching `state_machine/lifecycle.py:288`.
- **D-05:** `policies/integrity_policy.py:69` `proposal_dict: dict` and `state_machine/lifecycle.py:71` `-> dict` become `dict[str, Any]`, matching `events/domain_events.py:20`. No `NoReturn`: that would change a declared public signature.

### Tests and proof
- **D-06:** No test file changes. `grep -rn utcnow tests` is empty and no test asserts timestamp form. The naive-UTC result is proven in the evidence file by running the real constructors (see criterion 4), not by a new test.

### Claude's Discretion
- Exact helper module and function name, within the coding-rules naming rules.
- Line wrapping at the 88-character limit.
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `uv run pyright packages/execution-core` exits 0 and prints `0 errors`.
2. `grep -rn "utcnow" packages/execution-core/src` prints nothing.
3. `uv run pytest tests/packages/execution-core -q -W error::DeprecationWarning --cov=packages/execution-core/src` passes with the same test count as `main` (189 at f3743a1), and `uv run coverage report --include='packages/execution-core/src/*' --fail-under=90` exits 0. Before the fix the pytest command fails on DeprecationWarning.
   Note: do not write the pytest-cov fail-under flag literally in any builder-committed file (PLAN, SUMMARY, VERIFICATION, evidence): `checks-guard` treats it as a weakening token in non-lead commits. Use `coverage report --fail-under` as above.
4. For each model whose field defaulted to `utcnow` (`Task`, `Evidence`, `Decision`, `ParkingItem`, `ExecutionSession`, `Foreground`, `Specification`, `DoneWhenCriterion`, `Assumption`, `Unknown`), constructing it with defaults gives `created_at.tzinfo is None` and an `isoformat()` with no offset. Output pasted in the evidence file.
5. `git diff main --name-only` lists nothing under `tests/`, `evals/` or `.github/`, and no `pytest.ini` or `.coveragerc`; `git diff main | grep -E '^\+.*(type: ignore|pyright: ignore|noqa)'` prints nothing.
6. `uv run pytest tests/evals` and `uv run pytest tests/packages/persistence` pass with the same counts as `main`.
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 2)
- `.planning/codebase/CONCERNS.md` (pyright baseline)
- `docs/coding-rules.md` (naming, typing)
- `docs/decision-log.md` (D10 wire format)
- `packages/persistence/src/persistence/infrastructure/mappers.py:43-44` (JSON datetime serialization)
- `packages/persistence/src/persistence/infrastructure/models.py` (DateTime columns, no timezone)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Discard pattern `x, _ = ...` at `state_machine/lifecycle.py:288`, `policies/foreground_policy.py:65`.
- `dict[str, Any]` precedent at `events/domain_events.py:20`.

### Established Patterns
- Domain modules have a circular import handled by late imports (`domain/checkpoint.py:41`, `domain/session.py:41`); the helper must be a leaf.
- SQLite `DATETIME` drops tzinfo on write, so column bytes are the same either way; JSON columns are what constrain the choice.

### Integration Points
- `packages/application/src/coh_application/spec_gate_service.py:45-85` builds spec objects from defaults, then sets an aware `updated_at`: stored `spec_snapshot` already mixes forms today. Leave that as is.
</code_context>

<specifics>
## Specific Ideas

Baseline at f3743a1: 189 tests pass, 95.60% coverage, about 1687 DeprecationWarnings from `utcnow` through pydantic default factories.
</specifics>

<deferred>
## Deferred Ideas

- A lasting test pinning `tzinfo is None` on the defaults (lead checks commit) — open question for the owner.
- Making all domain timestamps consistently aware — needs a decision-log entry; out of scope.
- `NoReturn` on `analyze_findings_with_tool` — signature change; out of scope.
</deferred>
