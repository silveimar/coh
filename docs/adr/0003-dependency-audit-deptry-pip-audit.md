# ADR-0003: Check dependencies in CI with deptry and pip-audit

- **Status:** Proposed
- **Date:** 2026-10-22
- **Deciders:** proposed by the builder seat (chores-q4 Phase 3); owner approval required for Accepted
- **Slice / PR:** chores-q4 Phase 3, SUPP-01; the draft PR (number added at acceptance)
- **Decision log:** owner decision needed: defusedxml 0.7.1 (PSF-2.0) and distlib vendored in pip 26.2.2 (PSF-2.0), both in pip-audit's CI-only closure (Q3); certifi 2026.10.19 (MPL-2.0) in pip-audit's closure and vendored in pip, within D16's scope (Q4)

## Question

SUPP-01 needs CI to fail a PR that introduces an unused, missing or transitive-only dependency, or a dependency with a known vulnerability. deptry and pip-audit are new tools, a new dependency needs an accepted ADR (`CONTRIBUTING.md`, Definition of Done), and pip-audit calls an external vulnerability service. Which versions do we adopt, how do they run, and do they and their dependency closures install from wheels and carry an acceptable license on the Python each one runs under?

## Context

- SUPP-01: "CI runs deptry and pip-audit on every PR, and a finding fails the job" (`.planning/REQUIREMENTS.md:17`).
- The risk this closes: no dependency vulnerability audit runs in CI, so vulnerable transitive dependencies go unnoticed (`.planning/codebase/CONCERNS.md:85-89`).
- Scope and shape (`03-CONTEXT.md`):
  - D-01: deptry runs once per workspace member (7 runs), with the member directory as scan root and its `pyproject.toml` as config.
  - D-02: each member sets `known_first_party`; `package_module_name_map` covers members whose module name differs from the distribution name.
  - D-03: deptry runs after `uv sync --all-packages`, because it reads installed metadata.
  - D-04 (owner answer Q8 = split): the five current findings are resolved by declaring, dropping and two commented ignores (see "How they run").
  - D-05: pip-audit audits the hashed `uv export --locked --all-packages --no-emit-workspace` of the lock with `--strict --disable-pip`.
  - D-06: confirm how `--strict` treats marker-excluded lines before the build.
  - D-08 (owner answer Q9 = hybrid): deptry in the root dev group; pip-audit through a pinned `uvx --python 3.13`, so its closure stays out of `uv.lock`; pip-audit's calls to the vulnerability service are approved.
  - D-09 to D-11: uv pinned in the new jobs; two separate jobs with `contents: read`; fail closed.
- Why deptry goes in the dev group: deptry reads the installed metadata of the project's environment to map packages to modules (D-03), so it must run inside the synced project environment; an install outside it cannot see those packages (deptry documentation, `https://deptry.com/`).
- Python and wheels: the floor is CPython 3.15 (D12). A dependency without a cp315 wheel is acceptable only while its sdist builds in CI; a failure to install from wheel or sdist reopens D13.
- License policy: MIT, Apache-2.0, BSD and ISC are allowed without approval; anything else needs the owner (`CONTRIBUTING.md`, `FLEET-POLICY.md` Security row). D16 approves certifi under MPL-2.0, used unmodified. D17 approves pathspec under MPL-2.0. No decision-log entry approves PSF-2.0.
- The CI jobs already exist: the lead's checks commit 02105fb appends two jobs to `.github/workflows/ci.yml`, "Dependency check (deptry)" and "Vulnerability audit (pip-audit)". Both pin uv 0.13.0. The deptry job syncs the workspace, fails unless `deptry --version` prints `deptry 0.25.1`, runs deptry on the 7 members in a fixed order, fails a member that exits non-zero or scans 0 files, and fails when the workspace holds a member the loop does not run. The pip-audit job exports the lock with hashes, checks the export (at least 50 pins, a `sqlalchemy==` pin, no editable line), then runs `uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip` on it. Until deptry is in the dev group, the deptry job fails at its version gate.
- Measurements on 2026-10-22, uv 0.13.0, at 02105fb (origin/main 2215cd8 plus the lead's commits); full output in `03-EVIDENCE.md`, decisive lines in the appendix:
  - V2: `uv pip install --no-build --no-cache --python 3.15 deptry==0.25.1` installed 4 packages, all from wheels: click 8.5.0, deptry 0.25.1, packaging 26.3, requirements-parser 0.13.1.
  - V5: the same for `pip-audit==2.10.1` on CPython 3.13.16 installed 28 packages, all from wheels. V8 (informational): the same 28 also install from wheels on CPython 3.15.0, so D-08's premise ("may lack cp315 wheels") does not hold today.
  - V9 to V11: `deptry 0.25.1` and `pip-audit 2.10.1`, which are also the newest releases on that date.
  - B5 and R1-R7: with deptry's default config, persistence, mcp_adapter, application and apps/api fail; with the D-02 settings passed as flags, exactly the five D-04 findings remain.
  - D1-D5: the D-06 result below.
  - T1-T10 (tracer): in a scratch copy of the tree with the full change, `uv lock` resolves 75 packages; the lock adds only deptry and requirements-parser and deletes 4 member-metadata lines; all 7 deptry runs exit 0; pip-audit exits 0 on the 67-pin export; the application, api and mcp_adapter tests give 75 passed, the same as before.
- `uv audit` exists in uv 0.13.0 ("Audit the project's dependencies", with `--service-format` and `--python-platform`, V12). It was not run, because it calls a service D-08 does not approve.

## Options considered

### Option A: the D-08 hybrid
- What it is: deptry 0.25.1 in the root dev group (floor `>=0.25.1`, equal to the locked version; ADR-0001 amendment), run per member with per-member config after the D-04 split; pip-audit 2.10.1 through a pinned `uvx --python 3.13` on the hashed `uv export --locked --all-packages` (D-05).
- Pros: deptry runs in the environment it must inspect, pinned by `uv.lock` with hashes. pip-audit's 28-package closure, including certifi and defusedxml, stays out of `uv.lock`. Both jobs are already written and fail closed. The tracer passed end to end.
- Cons: two install paths for dev tools; pip-audit's closure is not locked (only pip-audit is pinned), so its other 27 packages may change between runs; a new advisory can turn `main` red with no code change.
- Cost to adopt and reverse: small. One dev-group line, 7 member config tables, 3 dependency-list edits and the lock entries. Revert the builder commits; the jobs come out only through a lead checks commit.

### Option B: both tools in the root dev group
- What it is: also add pip-audit to the root dev group and run it with `uv run`.
- Pros: one install path for every dev tool (ADR-0001); pip-audit's closure locked with hashes.
- Cons: the 28-package closure enters `uv.lock`, with certifi (already locked) and defusedxml (PSF-2.0, new); pip-audit then shares the environment it audits. The owner chose Option A (Q9).
- Cost to adopt and reverse: small, but it widens the lock and the license questions.

### Option C: `uv audit` instead of pip-audit
- What it is: audit `uv.lock` directly with uv's own command (V12).
- Pros: no extra tool; reads the lock, not an export; `--python-platform` could cover the marker-only pins (Q5).
- Cons: SUPP-01 and the owner's answer name pip-audit; it queries OSV, a different service than the one D-08 approves; its behavior was not verified in this phase; the lint-and-test job floats uv's version.
- Cost to adopt and reverse: small to adopt; it needs its own owner approval for the service.

### Option D: do nothing
- What it is: no dependency checks in CI.
- Pros: no new dependency, no license question.
- Cons: SUPP-01 stays unmet; the CONCERNS.md risk stays; the lead's jobs stay red until a lead checks commit removes them.
- Cost to adopt and reverse: none to adopt; the requirement stays open.

## Decision

**Selected:** Option A, with deptry 0.25.1 (floor `>=0.25.1`, equal to the locked version) and pip-audit 2.10.1 (pinned in the workflow). Both are the newest releases on 2026-10-22 (V11).

Option A meets SUPP-01 with both tools pinned, keeps the vulnerability tool and its closure out of the environment it audits, and follows the owner's answer (Q9). The accepted downsides are an unlocked pip-audit closure, a `main` that can turn red on a new advisory, and the license questions below.

Table 1, deptry closure (installed on CPython 3.15.0, V2-V4):

| Package | Version | Role | In uv.lock before this ADR | License (source) | Allowed list | Wheel installed on CPython 3.15 |
|---|---|---|---|---|---|---|
| deptry | 0.25.1 | direct, root dev group | no | MIT (METADATA `License-Expression`) | yes | `cp310-abi3-manylinux_2_17_x86_64` |
| click | 8.5.0 | transitive of deptry | yes (8.5.0) | BSD-3-Clause (METADATA `License-Expression`) | yes | `py3-none-any` |
| packaging | 26.3 | transitive of deptry and requirements-parser | yes (26.3) | Apache-2.0 OR BSD-2-Clause (METADATA `License-Expression`) | yes | `py3-none-any` |
| requirements-parser | 0.13.1 | transitive of deptry | no | Apache-2.0 (METADATA `License` and classifier) | yes | `py3-none-any` |

deptry also declares `colorama>=0.4.6` on win32 (colorama 0.4.6 is already locked) and `tomli` below Python 3.15 only (V4); neither installs on the Linux runner.

Table 2, pip-audit closure (installed on CPython 3.13.16 by `uvx`; not in `uv.lock`; V5-V7):

| Package | Version | License (source) | Allowed list | Wheel installed on CPython 3.13 |
|---|---|---|---|---|
| pip-audit | 2.10.1 | Apache-2.0 (classifier) | yes | `py3-none-any` |
| boolean.py | 5.0 | BSD-2-Clause (`License`) | yes | `py3-none-any` |
| CacheControl | 0.14.4 | Apache-2.0 (`License-Expression`) | yes | `py3-none-any` |
| certifi | 2026.10.19 | MPL-2.0 (`License` and classifier) | no: owner decision (Q4) | `py3-none-any` |
| charset-normalizer | 3.5.2 | MIT (`License`) | yes | `cp313-cp313-manylinux_2_17_x86_64` |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 (`License` and classifier) | yes | `py3-none-any` |
| defusedxml | 0.7.1 | PSF-2.0 (`License: PSFL`, classifier Python Software Foundation License) | no: owner decision (Q3) | `py2-none-any`, `py3-none-any` |
| filelock | 4.2.4 | MIT (`License-Expression`) | yes | `py3-none-any` |
| idna | 3.20 | BSD-3-Clause (`License-Expression`) | yes | `py3-none-any` |
| license-expression | 30.4.4 | Apache-2.0 (`License`) | yes | `py3-none-any` |
| markdown-it-py | 4.2.0 | MIT (classifier) | yes | `py3-none-any` |
| mdurl | 0.1.2 | MIT (classifier) | yes | `py3-none-any` |
| msgpack | 1.2.3 | Apache-2.0 (`License-Expression`) | yes | `cp313-cp313-manylinux_2_17_x86_64` |
| packageurl-python | 0.17.6 | MIT (`License` and classifier) | yes | `py3-none-any` |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause (`License-Expression`) | yes | `py3-none-any` |
| pip | 26.2.2 | MIT (`License-Expression`); vendors 18 components, see the next row | yes | `py3-none-any` |
| pip-api | 0.0.35 | Apache-2.0 (`License` text and classifier) | yes | `py3-none-any` |
| pip-requirements-parser | 32.0.1 | MIT (`License`) | yes | `py3-none-any` |
| platformdirs | 4.13.5 | MIT (`License-Expression`) | yes | `py3-none-any` |
| py-serializable | 2.1.0 | Apache-2.0 (`License` and classifier) | yes | `py3-none-any` |
| Pygments | 2.21.0 | BSD-2-Clause (`License-Expression`) | yes | `py3-none-any` |
| pyparsing | 3.3.3 | MIT (`License-Expression`) | yes | `py3-none-any` |
| requests | 2.34.2 | Apache-2.0 (`License` and classifier) | yes | `py3-none-any` |
| rich | 15.0.0 | MIT (`License` and classifier) | yes | `py3-none-any` |
| sortedcontainers | 2.4.0 | Apache-2.0 (`License: Apache 2.0` and classifier) | yes | `py2-none-any`, `py3-none-any` |
| tomli | 2.5.0 | MIT (`License-Expression`) | yes | `cp313-cp313-manylinux_2_17_x86_64` |
| tomli-w | 1.2.0 | MIT (classifier) | yes | `py3-none-any` |
| urllib3 | 2.8.0 | MIT (`License-Expression`) | yes | `py3-none-any` |
| pip's vendored components outside the list | in pip 26.2.2 | certifi: MPL-2.0 (`_vendor/certifi/LICENSE` line 15); distlib: PSF-2.0 (`_vendor/distlib/LICENSE.txt` line 93) | no: owner decision (Q3, Q4) | (inside the pip wheel) |

The other 16 components vendored in pip carry MIT, Apache-2.0, BSD or ISC license text (V7b; resolvelib's file is the ISC grant without the word "ISC", packaging's points to its Apache-2.0 and BSD files).

### How they run

- **deptry** (D-01, D-03, D-09, D-11): CI syncs the workspace with `uv sync --all-packages --locked`, checks the version, then runs `uv run --no-sync deptry --no-ansi <member> --config <member>/pyproject.toml` for `packages/archive`, `packages/execution-core`, `packages/persistence`, `packages/prose`, `packages/mcp_adapter`, `packages/application` and `apps/api`. A member fails on a non-zero exit or 0 scanned files; the job also fails if the workspace holds a member the loop does not run.
- **Per-member config (D-02):** each member's `pyproject.toml` gets a `[tool.deptry]` table with `known_first_party` set to its own module (`coh_archive`, `execution_core`, `persistence`, `coh_prose`, `coh_mcp`, `coh_application`, `coh_api`). This clears the self-import findings in persistence (`alembic/env.py`) and apps/api. `package_module_name_map` goes only in the two members that declare `prose` or `application`: mcp_adapter (`application = "coh_application"`, `prose = "coh_prose"`) and apps/api (`application = "coh_application"`), because deptry cannot read those mappings from the editable installs (B5 against R5 and R7).
- **The D-04 split:**
  - `packages/application` declares `sqlalchemy>=2.0.0` (it imports it; the specifier persistence already uses) and drops `coh-archive`, which it does not use, with its `[tool.uv.sources]` line.
  - `apps/api` drops `execution-core`, which it does not import.
  - `apps/api` ignores DEP002 for `uvicorn` only, under a comment: uvicorn is the server that runs the app from the command line, and no module imports it.
  - `packages/mcp_adapter` ignores DEP003 for `sqlalchemy` only, under a comment: `handlers.py` has 4 inline `from sqlalchemy import select` sites, a layer-rule violation (MCP tools must call application services, AGENTS.md); the ignore goes away when that is fixed, and sqlalchemy is not declared there so the violation does not look intended.
  - No other ignore, exclude or per-rule key is allowed. No new package enters the lock through the split; member metadata in `uv.lock` changes (T6).
- **pip-audit** (D-05, D-08, D-09, D-11): CI exports the lock with hashes, checks the export, and runs `uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip` on it with the default service. The exit code is pip-audit's.

### D-06 result

Measured in D1-D5. pip-audit 2.10.1 evaluates environment markers and drops a line whose marker is false before auditing; it does not count it as skipped. On the 65-pin hashed export of 02105fb (10 lines with markers), the JSON report lists 62 audited dependencies, 0 with a skip reason and 0 vulnerable; colorama and pywin32 (`sys_platform == 'win32'`) and httpx2-jsfetch (`sys_platform == 'emscripten'`) are absent (D4). A file holding only `colorama==0.4.6 ; sys_platform == 'win32'` exits 0 with `No known vulnerabilities found` (D5). So `--strict` passes with no exclusions, and the workflow needs none. Consequence: those 3 pins are never audited on the Linux runner, and an export whose every line is marker-excluded would pass; the pip-audit job's input checks (at least 50 pins, a `sqlalchemy==` pin) guard against that.

### Owner decisions needed

- **Q1:** Accept deptry 0.25.1 in the root dev group with its closure (new in the lock: deptry 0.25.1 and requirements-parser 0.13.1, Table 1), the per-member config and the D-04 split? **Recommended default:** accept.
- **Q2:** Accept pip-audit 2.10.1 run through `uvx --python 3.13`, where only pip-audit is pinned and its other 27 packages resolve at each run and stay out of `uv.lock` (Table 2)? **Recommended default:** accept (D-08).
- **Q3:** Approve defusedxml 0.7.1 and pip's vendored distlib under PSF-2.0 as parts of pip-audit's CI-only closure (not in `uv.lock`, not shipped or redistributed by COH)? **Recommended default:** approve, recorded by the lead as its own decision-log entry, because no entry approves PSF-2.0. Note for the owner: typing-extensions (PSF-2.0) is already in `uv.lock` with no decision-log entry (ADR-0002 table). Alternative: reject; the pip-audit half of SUPP-01 then stops until Option C or another tool is evaluated.
- **Q4:** Confirm that D16 covers certifi 2026.10.19 in pip-audit's closure and as vendored in pip: the same package, used unmodified, not added to `uv.lock` through this path, not redistributed? **Recommended default:** confirm; no new entry, because D16's reopen conditions concern the lock and redistribution by COH.
- **Q5:** Accept that the marker-only pins are not audited on the Linux runner: colorama 0.4.6 and pywin32 312 on win32, httpx2-jsfetch 1.0 on emscripten (pywin32 reaches the MCP adapter's runtime through mcp 2.3.0 on win32, per `uv.lock`)? **Recommended default:** accept, with the reopen condition below; covering them is a separate Ask (for example `uv audit --python-platform windows`).

No package installed from an sdist build (V2 and V5 ran with `--no-build`), so there is no sdist question.

### Already decided (cited, not asked again)

- pip-audit's calls to the vulnerability service (the default `pypi` service; only public package names and versions leave the runner) are approved by the owner (D-08, answer Q9).
- A red on `main` caused only by the pip-audit job (a new advisory against an already-locked package) is handled as a fix slice, not as a dispatch pause (owner answer f1, 2026-10-22). Until the matching CULTURE.md exception merges through a retro PR, the Autopilot "`main` red" pause rule applies as written.

## Consequences

- **What changes:** root `pyproject.toml` gains `"deptry>=0.25.1"` in the dev group. The 7 member `pyproject.toml` files gain the `[tool.deptry]` tables; application and apps/api change their dependency lists (D-04). `uv.lock` gains deptry and requirements-parser and loses 4 member-metadata lines. The lead's two jobs (02105fb) start passing.
- **What gets easier:** an unused, undeclared or transitive-only dependency and a known-vulnerable pin fail the PR instead of reaching `main` unnoticed. The same commands run locally.
- **What gets harder:**
  - A new advisory can turn `main` red with no code change (handled by f1 as a fix slice).
  - Member dependencies and their deptry config must change together.
  - A deptry or pip-audit version bump needs a lead checks commit, because ci.yml pins both.
  - pip-audit's closure is not locked, so it can change between runs.
- **Follow-up work,** each its own item:
  - Docs that name neither tool are not edited here: `CONTRIBUTING.md:50`, `:55`; `README.md:50`; `AGENTS.md:41`.
  - The mcp_adapter layer violation; fixing it removes the DEP003 ignore.
  - checks-guard rules for deptry or pip-audit weakening: an Ask.
  - Making the two jobs required status checks: the owner's ruleset.
  - The D-06 gap (the 3 marker-only pins).
  - The CULTURE.md exception for a pip-audit-only red, through the retro PR.
- **Rollback:** revert the builder commits (dependency, lock, member config and the D-04 split). The jobs come out only through a lead checks commit.

## Compliance checklist

- [x] Stays inside the layer rules: no source change. The mcp_adapter violation already exists; this ADR records it with an ignore and does not widen it.
- [x] New dependency: deptry 0.25.1 (MIT) and requirements-parser 0.13.1 (Apache-2.0) enter `uv.lock`; click and packaging are already locked. pip-audit 2.10.1 (Apache-2.0) and its closure run in CI only and are not a project dependency; certifi (MPL-2.0) and defusedxml and pip's vendored distlib (PSF-2.0) in that closure are outside the allowed list and need the owner (Q3, Q4). Maintenance status: both tools resolved as the newest releases on PyPI on 2026-10-22 (V11); release dates and maintainer activity were not checked.
- [x] Schema change: not applicable.
- [x] Public API, wire format or archive format: not applicable.
- [x] No new infrastructure.
- [x] Tests: no behavior change; the application, api and mcp_adapter tests are re-run after the dependency changes (tracer: 75 passed, equal to the baseline).
- [x] Decision-log entry: no execution-semantics change. A PSF-2.0 approval, if given, is its own entry written by the lead (Q3).

## Reopen when

- A deptry closure package stops shipping a wheel for CPython 3.15, a pip-audit closure package for 3.13, or an sdist build fails (D13).
- A closure license changes, or a package outside the allowed list enters either closure.
- pip-audit's default service changes or needs credentials.
- A pip-audit release counts marker-excluded lines as skipped (D-06).
- COH supports win32 or emscripten.
- The mcp_adapter layer violation is fixed (remove the DEP003 ignore).
- A workspace member is added or renamed.
- The owner moves the audit to `uv audit`.

## References

- `.planning/phases/03-dependency-audit-job/03-CONTEXT.md`
- `.planning/ROADMAP.md` (Phase 3), `.planning/REQUIREMENTS.md` (SUPP-01)
- `docs/adr/0001-uv-dev-dependency-group.md`, `docs/adr/0002-mypy-strict-for-coh-prose.md`
- `docs/decision-log.md` D12, D13, D16 and D17
- `CONTRIBUTING.md`, `FLEET-POLICY.md` (Security and CI/CD rows)
- `.planning/codebase/CONCERNS.md`
- `https://pypi.org/project/deptry/`, `https://pypi.org/project/pip-audit/`, `https://pypi.org/project/requirements-parser/`, `https://deptry.com/`
- `.planning/phases/03-dependency-audit-job/03-EVIDENCE.md` for every raw output

## Appendix: verification summary

Run on 2026-10-22 with uv 0.13.0. `<scratch>` is a directory outside the repository; `<sp>` stands for `<scratch>/dep-adr/pip-audit-site`. Decisive lines only; the full outputs are in `03-EVIDENCE.md`.

V2 `uv pip install --directory <scratch>/dep-adr/tools --no-config --no-cache --no-build --strict --python 3.15 --target <scratch>/dep-adr/deptry-site deptry==0.25.1` (exit 0)

```text
Using CPython 3.15.0
Installed 4 packages in 1ms
 + click==8.5.0
 + deptry==0.25.1
 + packaging==26.3
 + requirements-parser==0.13.1
```

In V3 and V4 the path prefix `<scratch>/dep-adr/deptry-site/` is left out of each line.

V3 `grep -H -E "^(Tag|Root-Is-Purelib):"` on the 4 `WHEEL` files (exit 0), tag lines

```text
deptry-0.25.1.dist-info/WHEEL:Tag: cp310-abi3-manylinux_2_17_x86_64
click-8.5.0.dist-info/WHEEL:Tag: py3-none-any
packaging-26.3.dist-info/WHEEL:Tag: py3-none-any
requirements_parser-0.13.1.dist-info/WHEEL:Tag: py3-none-any
```

V4 `grep -r -H -E "^(Name|Version|License|Classifier: License|Requires-Dist)" <scratch>/dep-adr/deptry-site --include=METADATA` (exit 0), license lines

```text
click-8.5.0.dist-info/METADATA:License-Expression: BSD-3-Clause
deptry-0.25.1.dist-info/METADATA:License-Expression: MIT
requirements_parser-0.13.1.dist-info/METADATA:License: Apache-2.0
packaging-26.3.dist-info/METADATA:License-Expression: Apache-2.0 OR BSD-2-Clause
```

V5 `uv pip install --directory <scratch>/dep-adr/tools --no-config --no-cache --no-build --strict --python 3.13 --target <sp> pip-audit==2.10.1` (exit 0)

```text
Using CPython 3.13.16
Resolved 28 packages in 154ms
Installed 28 packages in 22ms
 + certifi==2026.10.19
 + defusedxml==0.7.1
 + pip==26.2.2
 + pip-audit==2.10.1
```

(4 of the 28 `+` lines shown; all 28 are in the evidence file and in Table 2.)

V6 `grep -r -H -E "^Tag:" <sp> --include=WHEEL` (exit 0), the native wheels

```text
<sp>/msgpack-1.2.3.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
<sp>/tomli-2.5.0.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
<sp>/charset_normalizer-3.5.2.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
```

V7 `grep -r -H -E "^(Name|Version|License:|License-Expression|Classifier: License)" <sp> --include=METADATA` (exit 0), the lines outside the allowed list

```text
<sp>/certifi-2026.10.19.dist-info/METADATA:License: MPL-2.0
<sp>/certifi-2026.10.19.dist-info/METADATA:Classifier: License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)
<sp>/defusedxml-0.7.1.dist-info/METADATA:License: PSFL
<sp>/defusedxml-0.7.1.dist-info/METADATA:Classifier: License :: OSI Approved :: Python Software Foundation License
```

V7b pip's vendored code

```text
$ grep -c -E "^License-File: src/pip/_vendor/" <sp>/pip-26.2.2.dist-info/METADATA
20
$ grep -n -m 1 -i -E "mozilla public license" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/certifi/LICENSE
15:This Source Code Form is subject to the terms of the Mozilla Public License,
$ grep -n -i -E "^ *PYTHON SOFTWARE FOUNDATION LICENSE" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/distlib/LICENSE.txt
93:PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
```

The 20 license files belong to 18 components (packaging ships 3).

V9 and V10

```text
$ uv run --no-project --no-config --python 3.15 --directory <scratch>/dep-adr/tools --with deptry==0.25.1 deptry --version
deptry 0.25.1
$ uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --version
pip-audit 2.10.1
```

R1-R7, deptry 0.25.1 with the D-02 settings as flags on the unmodified tree: archive, execution-core, persistence and prose exit 0; the other three exit 1 with

```text
packages/mcp_adapter/src/coh_mcp/handlers.py:298:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:335:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:378:21: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:442:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/application/pyproject.toml: DEP002 'coh-archive' defined as a dependency but not used in the codebase
packages/application/src/coh_application/foreground_service.py:293:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/application/src/coh_application/spec_gate_service.py:266:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
apps/api/pyproject.toml: DEP002 'uvicorn' defined as a dependency but not used in the codebase
apps/api/pyproject.toml: DEP002 'execution-core' defined as a dependency but not used in the codebase
```

D3 `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip -r <scratch>/dep-adr/base-hashed.txt --format json -o <scratch>/dep-adr/base-audit.json` (exit 0)

```text
No known vulnerabilities found
```

D4 `jq` summary of the D3 report

```text
"audited": 62, "skipped": [], "vulnerable": [], "marker_only_present": []
```

D5 pip-audit `--strict --disable-pip --no-deps` on `colorama==0.4.6 ; sys_platform == 'win32'` (exit 0)

```text
No known vulnerabilities found
```

D6 the same on `requests==2.19.1` (exit 1)

```text
Found 10 known vulnerabilities in 1 package
requests 2.19.1  PYSEC-2018-28   2.20.0
```

(1 of the 10 `requests` rows shown.)

T6 `grep -E '^[-+](name|version) = |^[-+] +\{ name = '` on the tracer's lock diff: 17 lines, with these package entries

```text
+name = "deptry"
+version = "0.25.1"
+name = "requirements-parser"
+version = "0.13.1"
```

and 4 deleted member-metadata lines (`coh-archive` and `execution-core`, each as a dependency and as a requirement).

T8 in the tracer copy: `deptry --version` prints `deptry 0.25.1`; all 7 member runs exit 0 with `Success! No dependency issues found.`, scanning archive 5, execution-core 24, persistence 11, prose 3, mcp_adapter 6, application 3 and apps/api 12 files.

T9 the tracer's hashed export has 67 pins; pip-audit on it exits 0 with `No known vulnerabilities found`.
