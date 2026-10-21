# Phase 4: mypy strict for coh_prose - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning; build blocked until the mypy ADR is accepted
**Type:** chore (CI). Protected check set: YES — `.github/workflows/ci.yml`. The lead writes the CI step in a checks commit; the builder writes only the ADR draft, `pyproject.toml`/`uv.lock` changes and any source typing fixes.

<domain>
## Phase Boundary

`packages/prose/src/coh_prose` (`__init__.py`, `policy.py`, `renderer.py`) is checked by `mypy --strict` in CI. Requirement: TYPE-03.

In scope: one ADR for mypy; mypy in the root dev group; root `[tool.mypy]`; source typing fixes in `coh_prose` if any; one CI step (lead).
Out of scope: mypy on `tests/packages/prose` (protected); mypy on any other package; new modules; extending `checks-guard` weakening rules; edits to `CONTRIBUTING.md` or `docs/coding-rules.md`.
</domain>

<decisions>
## Implementation Decisions

### Scope
- **D-01:** "One new module" is read as one existing module new to mypy: the `coh_prose` package. No new code is written (chore-only mission). Open question for the owner.
- **D-02:** Only the source tree is checked.

### Dependency and ADR
- **D-03:** A new ADR at the next free number in `docs/adr/` decides mypy: version (floor = locked version, ADR 0001 amendment), CPython 3.15 support and wheel availability, and the license of mypy and every new transitive package. Any license outside MIT/Apache-2.0/BSD/ISC (pathspec may be MPL-2.0) is an owner decision. If a transitive package has no cp315 wheel and its sdist fails, D13's reopen condition applies: stop and raise it.
- **D-04:** The ADR is the first commit of the phase PR and the build waits for its acceptance. If Phase 3 is open at the same time, the two ADRs take distinct numbers; the second to start rebases.
- **D-05:** mypy goes into the root `[dependency-groups] dev` (ADR 0001), so CI's `uv sync --all-packages` installs it.

### Config
- **D-06:** Root `pyproject.toml` `[tool.mypy]`: `strict = true`, `python_version = "3.15"`. No `[[tool.mypy.overrides]]`, no `ignore_*`, no `follow_imports`, no pydantic plugin (its default types `__init__` args as `Any`, weaker than dataclass_transform).
- **D-07:** Scope comes from the checked path in the CI command: `uv run mypy --strict packages/prose/src/coh_prose`.

### Source
- **D-08:** Expected: no source change (pyright 0 errors; pydantic ships `py.typed`; models use dataclass_transform). If mypy reports errors, fix with annotations only, keep pyright at 0, add no suppression.

### Docs
- **D-09:** Do not edit `CONTRIBUTING.md` (Ask-tier) or `docs/coding-rules.md` (Phase 5 territory). The PR description lists the gap "docs name pyright as the only type checker" under choices not dictated by the spec.

### Claude's Discretion
- ADR wording and structure (follow `docs/adr/0000-template.md`).
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `uv run mypy --strict packages/prose/src/coh_prose` exits 0 and prints `Success: no issues found in 3 source files`. The evidence file also shows it exiting 1 with a local, uncommitted untyped `def` added (proof the check bites).
2. `uv run pyright packages/prose` reports 0 errors.
3. `grep -n "mypy --strict packages/prose/src/coh_prose" .github/workflows/ci.yml` returns exactly one line, added in a lead-seat commit, with no `continue-on-error`; CI is green on the PR head.
4. `git diff main...HEAD -- packages/prose/src | grep -nE "type: ignore|# mypy:|pyright: ignore"` prints nothing.
5. `grep -nE "ignore_errors|disable_error_code|follow_imports|ignore_missing_imports|tool\.mypy\.overrides|plugins" pyproject.toml packages/prose/pyproject.toml` prints nothing.
6. `grep -c '^name = "mypy"' uv.lock` prints `1`; `uv lock --check` exits 0; `docs/adr/` holds the mypy ADR with `Status: Accepted`, an index row in `docs/adr/README.md`, and a license line for mypy and each new transitive package.
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 4)
- `docs/adr/0001-uv-dev-dependency-group.md` (dev group, floor = locked version)
- `docs/adr/README.md`, `docs/adr/0000-template.md`
- `docs/decision-log.md` D13 (cp315 wheels)
- `CONTRIBUTING.md` (new dependency needs ADR; licenses; protected check set)
- `FLEET-POLICY.md` (Security row: licenses)
- `pyproject.toml` `[tool.pyright]`
- `.github/scripts/checks_guard.py` (protected set, weakening rules)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Root tooling config pattern: ruff and pyright in root `pyproject.toml`.

### Established Patterns
- `coh_prose` imports only stdlib and pydantic; `__all__` declared in `__init__.py`.
- Possible mypy sites if any: `__init__` without `-> None` (`policy.py:88`, `renderer.py:90`); empty-list assignments filled later.

### Integration Points
- CI `uv sync --all-packages` installs the root dev group (`.github/workflows/ci.yml`).
</code_context>

<specifics>
## Specific Ideas

`pyproject.toml` is not protected, so a later builder commit could weaken mypy through config while the CI command still says `--strict`. Review catches it (criterion 5); a guard rule would be a separate Ask.
</specifics>

<deferred>
## Deferred Ideas

- Adding mypy-weakening tokens to `checks-guard` `WEAKENING_RULES` — Ask, separate checks change.
- mypy on tests or other packages.
- `renderer.py:281-303` can render "None fails" when `first_failing` is `None` — behavior bug, not typing; possible fix phase.
</deferred>
