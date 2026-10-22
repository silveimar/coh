# Phase 3: Dependency audit job - Context

**Gathered:** 2026-10-21 (assumptions mode)
**Status:** Ready for planning; build blocked until the ADR is accepted
**Amended:** 2026-10-22 with the owner's answers (Q8 = split, Q9 hybrid plus `uvx --python 3.13`, finding 1 = fix slice)
**Type:** chore (CI). Protected check set: YES — `.github/workflows/ci.yml`. The lead writes both CI jobs in a checks commit; the builder writes the ADR draft, member `pyproject.toml` config, the member `dependencies` changes in D-04 and `uv.lock`.

<domain>
## Phase Boundary

CI fails a PR that introduces an unused, missing or transitive-only dependency (deptry) or a dependency with a known vulnerability (pip-audit). Requirement: SUPP-01.

In scope: one ADR; deptry config; two CI jobs (lead); making `main` deptry-clean per D-04.
Out of scope: making the jobs required status checks (ruleset: owner only, `FLEET-POLICY.md` Never for seats); scanning `tests/`; schedule triggers; `CONTRIBUTING.md` edits (Ask-tier: follow-up); Trivy, pre-commit.
</domain>

<decisions>
## Implementation Decisions

### deptry
- **D-01:** deptry runs once per workspace member (7 runs), scan root = member directory, `--config` = that member's `pyproject.toml`. Not at the repo root (the root project is virtual, `uv.lock` `source = { virtual = "." }`), not `src/` only (persistence imports `alembic` from `packages/persistence/alembic/`), not `tests/`.
- **D-02:** Each member sets `known_first_party`. `package_module_name_map` covers editable members whose module name differs from the distribution name (`prose` → `coh_prose`, `application` → `coh_application`) if deptry cannot read it from installed metadata.
- **D-03:** deptry must see the synced environment (it learns `pyyaml` → `yaml` from installed metadata), so it runs after `uv sync --all-packages`.
- **D-04 (owner answer Q8 = split, 2026-10-22):** `main` has 5 static findings: `packages/application` imports `sqlalchemy` undeclared (DEP003) and declares `coh-archive` unused (DEP002); `packages/mcp_adapter` imports `sqlalchemy` undeclared (DEP003); `apps/api` declares `execution-core` unused and `uvicorn[standard]` (used as CLI only) (DEP002). Resolution:
  - Declare `sqlalchemy` in `packages/application` (truthful: it imports it).
  - Drop `coh-archive` from `packages/application` and `execution-core` from `apps/api`.
  - One commented DEP002 ignore in `apps/api` for `uvicorn` (CLI use only).
  - One commented DEP003 ignore for `sqlalchemy` in `packages/mcp_adapter`. The comment names the layering violation: the 4 inline `from sqlalchemy import select` sites in `handlers.py` bypass the rule that MCP tools call application services, never repositories (AGENTS.md; `.planning/codebase/CONCERNS.md`). The ignore goes away when that violation is fixed. Do not declare `sqlalchemy` in `mcp_adapter`: a manifest line would look intended.
  - No new package enters the lock; member metadata in `uv.lock` changes.

### pip-audit
- **D-05:** Input is the exported lock, not the CI environment: `uv export --locked --all-packages --no-emit-workspace --format requirements.txt -o <tmp>`, then `pip-audit --strict --disable-pip -r <tmp>`. `--all-packages` is mandatory: without it only 21 dev pins are exported and the job passes green while auditing no runtime dependency. `--locked`, not `--frozen`. The dev group is included (CI runs those tools). The audited file keeps hashes (the export default): `--disable-pip` requires a hashed file or `--no-deps`. Never add `--no-hashes` to the audited export; criterion 3 uses `--no-hashes` only to count pins.
- **D-06:** Confirm before build how `--strict` treats marker-excluded lines (`colorama`, `pywin32` on win32; `httpx2-jsfetch` on emscripten). If they count as skipped, exclude those names explicitly in the protected workflow; never drop `--strict`.

### ADR
- **D-07:** One ADR at the next free number in `docs/adr/` covers both tools: versions, licenses (deptry MIT, pip-audit Apache-2.0 expected; verify), the license status of each tool's dependency closure (for example defusedxml PSF-2.0: owner approval if outside MIT/Apache-2.0/BSD/ISC), cp315 wheels (D13), and approval of pip-audit's calls to the vulnerability service (external API call, Ask-tier). It records `uv audit` (in uv 0.13.0) as a considered option. deptry's closure is `click`, `packaging` (both already locked) and `requirements-parser` (not locked); the ADR lists `requirements-parser` with its license. The ADR also records that a red on `main` caused only by the pip-audit job (a new advisory against an already-locked package) is handled as a fix slice, not as a dispatch pause (owner answer f1 = fix slice, 2026-10-22). Until the matching CULTURE.md exception merges through a retro PR, the Autopilot "`main` red" pause rule still applies as written. Phases 3 and 4 never run at the same time (ROADMAP order), so the ADR takes the next free number.
- **D-08 (owner answer Q9 = hybrid):** deptry in the root dev group; pip-audit via `uvx --python 3.13 pip-audit==<pinned>` in the workflow so its closure stays out of `uv.lock`. `--python 3.13` because pip-audit's closure has native packages (for example `msgpack` through `cachecontrol`) that may lack cp315 wheels (D13); pip-audit audits the exported file, not the running environment, so the interpreter version does not change the result. Approved: pip-audit's calls to the vulnerability service (only public package names and versions leave the machine).
- **D-09:** Pin uv in the new jobs (CI floats `version: "latest"`; the export format spelling changed across uv versions).

### CI shape
- **D-10:** Two new jobs in `.github/workflows/ci.yml` (`deptry`, `pip-audit`), same `on:` block (push and PR to `main`), `permissions: contents: read`. Not steps in `lint-and-test` (a test failure would skip them).
- **D-11:** Fail closed like the gitleaks job: no `continue-on-error`; `set -o pipefail` with tee; the pip-audit job checks its input (at least 50 pins, `sqlalchemy==` present, no `-e` lines) before auditing; the deptry loop runs all 7 members, collects status and checks each scanned more than 0 files; findings to `$GITHUB_STEP_SUMMARY`.

### Claude's Discretion
- Job and step names; summary formatting.
</decisions>

<acceptance_criteria>
## Testable Acceptance Criteria

1. `docs/adr/` holds the ADR with `Status: Accepted`, an index row in `docs/adr/README.md`, and a version and license for deptry and pip-audit.
2. `grep -nE 'deptry|pip-audit' .github/workflows/ci.yml` shows both tools with exact pins; `grep -c 'continue-on-error' .github/workflows/ci.yml` prints `0`; `--strict` is present; `git log --format=%ae main..HEAD -- .github/workflows/` prints only `lead-seat@coh-fleet.invalid`.
3. `uv export --locked --all-packages --no-emit-workspace --format requirements.txt --no-hashes` prints at least 50 `==` pins including `fastapi==`, `sqlalchemy==`, `mcp==`, `pyyaml==`, and no line starting with `-e`.
4. On the PR head, deptry exits 0 for each of the 7 member directories and pip-audit exits 0 on the export.
5. Evidence file: deptry on a scratch copy of a member with a seeded unused dependency exits 1 and prints `DEP002`; `pip-audit --strict --disable-pip --no-deps -r` on a file containing `requests==2.19.1` exits 1.
6. `gh pr checks <n>` shows both new jobs and `checks-guard` passing on the exact head SHA.
</acceptance_criteria>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (Phase 3)
- `docs/adr/0001-uv-dev-dependency-group.md`, `docs/adr/README.md`, `docs/adr/0000-template.md`
- `docs/decision-log.md` D13 (cp315 wheels), D14, D15
- `CONTRIBUTING.md` (new dependency needs ADR; licenses; protected check set; "Known gaps")
- `FLEET-POLICY.md` (CI/CD row: new tool is Ask; Security row: external APIs, licenses)
- `.github/workflows/ci.yml` (gitleaks job: fail-closed pattern)
- `.github/scripts/checks_guard.py` (protected set, weakening tokens)
- `pyproject.toml`, `packages/*/pyproject.toml`, `apps/api/pyproject.toml`, `uv.lock`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- gitleaks job: pinned version env vars, input sanity checks, step summary, collected exit status.

### Established Patterns
- Runtime dependencies are per member; dev tools only in the root group (ADR 0001).

### Integration Points
- `checks-guard` fails any non-lead commit that adds `continue-on-error`.
</code_context>

<specifics>
## Specific Ideas

deptry findings above are from static reading (grep), not a run; the planner re-derives them with the pinned deptry before choosing D-04.
</specifics>

<deferred>
## Deferred Ideas

- `CONTRIBUTING.md` lines on what CI runs and "Known gaps" — Ask-tier follow-up.
- Making the jobs required checks — owner ruleset action.
- `certifi` (MPL-2.0) is already locked through httpx. The owner approved it (Q13, 2026-10-22); the lead records it in `docs/decision-log.md` after Phase 5 merges.
- CULTURE.md exception for a pip-audit-only red on `main` — lead routes it through the next retro PR; the owner merges.
- deptry/pip-audit weakening tokens in `checks-guard` — separate Ask.
</deferred>
