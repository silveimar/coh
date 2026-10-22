# Phase 03 evidence (H-87)

Commands ran on 2026-10-22 from the builder seat, uv 0.13.0. Stand-ins: `<worktree>` is the slice worktree `coh-wt/03-dependency-audit-job`; `<scratch>` is the builder session's scratch directory, outside the repository; `<sp>` is `<scratch>/dep-adr/pip-audit-site` (pip-audit's closure installed with `--target`); `<repo>` is the GitHub `owner/name` slug. Host paths are replaced with these stand-ins; no other output line is dropped, except copyright and author lines. Every diff gate uses `origin/main`, because local `main` is stale (plan finding 2).

## Preconditions

PC1 `git -C <worktree> merge-base --is-ancestor 2215cd823dcc0ed1546aa6b63306d06199149c8e HEAD`

```text
exit=0
```

PC2 `git -C <worktree> merge-base HEAD origin/main`, then `git -C <worktree> rev-parse origin/main`

```text
2215cd823dcc0ed1546aa6b63306d06199149c8e
2215cd823dcc0ed1546aa6b63306d06199149c8e
```

PC3 `gh pr view 38 --repo <repo> --json state --jq .state`

```text
MERGED
```

PC4 `ls <worktree>/docs/adr`

```text
0000-template.md
0001-uv-dev-dependency-group.md
0002-mypy-strict-for-coh-prose.md
README.md
```

PC5 `grep -c "^## D17" <worktree>/docs/decision-log.md`, then `grep -c "^## D18" <worktree>/docs/decision-log.md` (exit 1 at count 0, the pass state)

```text
1
0
```

PC6 `gh pr list --repo <repo> --state open --json number,files --jq '.[] | select(any(.files[]; .path == "uv.lock" or .path == "pyproject.toml")) | .number'`

```text
(no output)
```

PC7 `gh pr list --repo <repo> --state open --json number --jq length`

```text
1
```

PC8 `git -C <worktree> status --porcelain --untracked-files=all --ignored`

```text
(no output)
```

PC9 `uv --version`

```text
uv 0.13.0 (x86_64-unknown-linux-gnu)
```

PCL1 `git -C <worktree> log --format="%h %ae %s" origin/main..HEAD`

```text
02105fb lead-seat@coh-fleet.invalid ci: deptry and pip-audit jobs (SUPP-01 checks)
6fa1cee lead-seat@coh-fleet.invalid docs(03): plan for the deptry and pip-audit jobs
```

PCL2 `git -C <worktree> diff --name-only origin/main...HEAD`

```text
.github/workflows/ci.yml
.planning/phases/03-dependency-audit-job/03-01-PLAN.md
```

PCL3 `git -C <worktree> diff --numstat origin/main...HEAD -- .github/workflows/ci.yml`

```text
131	0	.github/workflows/ci.yml
```

PCL4 `grep -n -E '^  (deptry|pip-audit):$' <worktree>/.github/workflows/ci.yml`

```text
178:  deptry:
257:  pip-audit:
```

PCL5 `grep -n -E 'deptry 0\.25\.1|pip-audit==2\.10\.1' <worktree>/.github/workflows/ci.yml`

```text
206:          if [ "$rc" -ne 0 ] || [ "$v" != "deptry 0.25.1" ]; then
207:            echo "::error::deptry version gate: expected 'deptry 0.25.1' with exit 0, got '$v' (exit $rc)"
297:          uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip --progress-spinner off -r "$RUNNER_TEMP/requirements.txt" 2>&1 | tee "$RUNNER_TEMP/pip-audit.log" || rc=$?
```

PCL6 `grep -c -F 'version: "0.13.0"' <worktree>/.github/workflows/ci.yml`

```text
2
```

PCL7 `grep -c "on-error" <worktree>/.github/workflows/ci.yml` (the error-tolerance key; exit 1 at count 0, the pass state)

```text
0
```

PCL8 `grep -n -F -- '--strict --disable-pip' <worktree>/.github/workflows/ci.yml` (one line; it also holds `--python 3.13` and `pip-audit==2.10.1`)

```text
297:          uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip --progress-spinner off -r "$RUNNER_TEMP/requirements.txt" 2>&1 | tee "$RUNNER_TEMP/pip-audit.log" || rc=$?
```

PCL9 `grep -n -F 'uv export --locked --all-packages --no-emit-workspace --format requirements.txt -o' <worktree>/.github/workflows/ci.yml`, then `grep -c -F -- '--no-hashes' <worktree>/.github/workflows/ci.yml`

```text
273:        run: uv export --locked --all-packages --no-emit-workspace --format requirements.txt -o "$RUNNER_TEMP/requirements.txt"
0
```

PCL10 `grep -n -F 'packages/archive packages/execution-core packages/persistence packages/prose packages/mcp_adapter packages/application apps/api' <worktree>/.github/workflows/ci.yml`

```text
219:          members="packages/archive packages/execution-core packages/persistence packages/prose packages/mcp_adapter packages/application apps/api"
```

PCL11 `grep -c -F 'contents: read' <worktree>/.github/workflows/ci.yml`

```text
3
```

PCL12 `grep -n -E 'deptry|pip-audit' <worktree>/.github/workflows/ci.yml` (criterion 2's grep; every line is in the two new jobs, lines 176-302)

```text
176:  # SUPP-01: deptry per workspace member (03-CONTEXT D-01, D-11). Findings and
177:  # ignores live in each member's [tool.deptry] table, never on this command line.
178:  deptry:
179:    name: Dependency check (deptry)
200:      # deptry is a root dev dependency; a version bump needs a lead checks commit.
201:      - name: Check the deptry version
204:          v="$(uv run --no-sync deptry --version 2>&1)" || rc=$?
206:          if [ "$rc" -ne 0 ] || [ "$v" != "deptry 0.25.1" ]; then
207:            echo "::error::deptry version gate: expected 'deptry 0.25.1' with exit 0, got '$v' (exit $rc)"
211:      - name: Run deptry on each member
214:          # the `| tee` below would hide the deptry exit code.
217:          # A member fails when deptry exits non-zero or scans no file. deptry
225:            uv run --no-sync deptry --no-ansi "$member" --config "$member/pyproject.toml" 2>&1 | tee "$RUNNER_TEMP/deptry.log" || rc=$?
226:            files=$(grep -oE 'Scanning [0-9]+ files?' "$RUNNER_TEMP/deptry.log" | grep -oE '[0-9]+' | head -n 1) || files=0
232:              echo "### deptry: $member"
237:              cat "$RUNNER_TEMP/deptry.log"
247:            echo "::error::deptry ran on $ran members; the workspace has $found member pyproject.toml files; expected 7 and 7"
251:            echo "::error::deptry failed for:$failed"
256:  # SUPP-01: pip-audit on the locked export (03-CONTEXT D-05, D-08, D-11).
257:  pip-audit:
258:    name: Vulnerability audit (pip-audit)
293:      - name: Run pip-audit
297:          uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip --progress-spinner off -r "$RUNNER_TEMP/requirements.txt" 2>&1 | tee "$RUNNER_TEMP/pip-audit.log" || rc=$?
299:            echo "### pip-audit (exit code $rc)"
302:            cat "$RUNNER_TEMP/pip-audit.log"
```

All of PC1-PC9 and PCL1-PCL12 match the plan. PCL6 prints 2 and PCL11 prints 3, as expected after the rebase.

## Baseline (origin/main 2215cd8 plus the lead's commits 6fa1cee and 02105fb, before builder edits)

`git -C <worktree> rev-parse HEAD` printed `02105fb6c8e2a74d32fd58ba01cb16202f3d9740`. B0-B3 and B5 ran in a `git archive` copy of that HEAD at `<scratch>/dep-adr/copy`, so the worktree has no `.venv`. `origin/main` replaces the stale local `main` (plan finding 2).

B0 `git -C <worktree> archive -o <scratch>/dep-adr/head.tar HEAD`, `mkdir -p <scratch>/dep-adr/copy <scratch>/dep-adr/tools <scratch>/dep-adr/probe`, `tar -xf <scratch>/dep-adr/head.tar -C <scratch>/dep-adr/copy` (each exit 0, no output), then `uv sync --directory <scratch>/dep-adr/copy --all-packages --locked` (exit 0)

```text
Using CPython 3.15.0
Creating virtual environment at: .venv
Resolved 73 packages in 0.77ms
   Building application @ file://<scratch>/dep-adr/copy/packages/application
   Building coh-api @ file://<scratch>/dep-adr/copy/apps/api
   Building coh-archive @ file://<scratch>/dep-adr/copy/packages/archive
   Building execution-core @ file://<scratch>/dep-adr/copy/packages/execution-core
   Building persistence @ file://<scratch>/dep-adr/copy/packages/persistence
   Building prose @ file://<scratch>/dep-adr/copy/packages/prose
   Building mcp-adapter @ file://<scratch>/dep-adr/copy/packages/mcp_adapter
      Built coh-archive @ file://<scratch>/dep-adr/copy/packages/archive
      Built execution-core @ file://<scratch>/dep-adr/copy/packages/execution-core
      Built prose @ file://<scratch>/dep-adr/copy/packages/prose
      Built mcp-adapter @ file://<scratch>/dep-adr/copy/packages/mcp_adapter
      Built persistence @ file://<scratch>/dep-adr/copy/packages/persistence
      Built application @ file://<scratch>/dep-adr/copy/packages/application
      Built coh-api @ file://<scratch>/dep-adr/copy/apps/api
Prepared 7 packages in 219ms
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
Installed 69 packages in 66ms
 + alembic==1.19.1
 + annotated-doc==0.0.5
 + annotated-types==0.8.0
 + anyio==4.15.0
 + application==0.1.0 (from file://<scratch>/dep-adr/copy/packages/application)
 + ast-serialize==0.13.1
 + attrs==26.1.0
 + certifi==2026.10.19
 + cffi==2.1.1
 + click==8.5.0
 + coh-api==0.1.0 (from file://<scratch>/dep-adr/copy/apps/api)
 + coh-archive==0.1.0 (from file://<scratch>/dep-adr/copy/packages/archive)
 + coverage==7.16.0
 + cryptography==50.0.1
 + execution-core==0.1.0 (from file://<scratch>/dep-adr/copy/packages/execution-core)
 + fastapi==0.141.1
 + greenlet==3.5.5
 + h11==0.16.0
 + httpcore==1.0.9
 + httpcore2==2.12.0
 + httptools==0.9.0
 + httpx==0.28.1
 + httpx2==2.12.0
 + hypothesis==6.169.0
 + idna==3.19
 + iniconfig==2.3.0
 + jsonschema==4.26.0
 + jsonschema-specifications==2025.9.1
 + librt==0.16.0
 + mako==1.4.3
 + markupsafe==3.0.4
 + mcp==2.3.0
 + mcp-adapter==0.1.0 (from file://<scratch>/dep-adr/copy/packages/mcp_adapter)
 + mcp-types==2.3.0
 + mypy==2.4.0
 + mypy-extensions==1.1.0
 + nodeenv==1.10.0
 + opentelemetry-api==1.44.0
 + packaging==26.3
 + pathspec==1.1.1
 + persistence==0.1.0 (from file://<scratch>/dep-adr/copy/packages/persistence)
 + pluggy==1.6.0
 + prose==0.1.0 (from file://<scratch>/dep-adr/copy/packages/prose)
 + pycparser==3.0
 + pydantic==2.14.1
 + pydantic-core==2.50.1
 + pygments==2.21.0
 + pyjwt==2.15.1
 + pyright==1.1.414
 + pytest==9.1.1
 + pytest-asyncio==1.4.0
 + pytest-cov==7.1.0
 + python-dotenv==1.2.3
 + python-multipart==0.0.32
 + pyyaml==6.0.3
 + referencing==0.37.0
 + rpds-py==2026.6.3
 + ruff==0.17.0
 + sortedcontainers==2.4.0
 + sqlalchemy==2.0.52
 + sse-starlette==3.4.8
 + starlette==1.6.0
 + truststore==0.10.4
 + typing-extensions==4.16.0
 + typing-inspection==0.4.4
 + uvicorn==0.52.4
 + uvloop==0.23.0
 + watchfiles==1.2.0
 + websockets==17.1
```

B1 `uv run --no-sync --directory <scratch>/dep-adr/copy pytest tests/packages/application -q`

```text
...........................                                              [100%]
27 passed in 0.87s
```

B2 `uv run --no-sync --directory <scratch>/dep-adr/copy pytest tests/apps/api -q`

```text
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.15/site-packages/starlette/testclient.py:53
  <scratch>/dep-adr/copy/.venv/lib/python3.15/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

tests/apps/api/test_api_integration.py::TestI02ReadinessGate::test_confirm_blocked_when_spec_is_blocked
  <scratch>/dep-adr/copy/.venv/lib/python3.15/site-packages/anyio/_backends/_asyncio.py:1100: StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = context.run(func, *args)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 2 warnings in 0.41s
```

B3 `uv run --no-sync --directory <scratch>/dep-adr/copy pytest tests/packages/mcp_adapter -q`

```text
.......................................                                  [100%]
39 passed in 0.87s
```

B4 `uv export --directory <worktree> --locked --all-packages --no-emit-workspace --format requirements.txt --no-hashes --no-header --quiet -o <scratch>/dep-adr/base-nohash.txt` (exit 0, no output), then `grep -c -E '^[A-Za-z0-9._-]+==' <scratch>/dep-adr/base-nohash.txt`, `grep -c -E '^-e ' <scratch>/dep-adr/base-nohash.txt` and PC8's status command

```text
65
0
(status: no output, the same as PC8)
```

B5 deptry 0.25.1 at the default config (the current findings), `uv run --no-sync --directory <scratch>/dep-adr/copy --with deptry==0.25.1 deptry --no-ansi <m> --config <m>/pyproject.toml` for each member `<m>`:

`packages/archive` (exit 0)

```text
Scanning 5 files...

Success! No dependency issues found.
```

`packages/execution-core` (exit 0)

```text
Scanning 24 files...

Success! No dependency issues found.
```

`packages/persistence` (exit 1)

```text
Scanning 11 files...

packages/persistence/alembic/env.py:8:1: DEP003 'persistence' imported but it is a transitive dependency
Found 1 dependency issue.

For more information, see the documentation: https://deptry.com/
```

`packages/prose` (exit 0)

```text
Scanning 3 files...

Success! No dependency issues found.
```

`packages/mcp_adapter` (exit 1)

```text
Scanning 6 files...

packages/mcp_adapter/pyproject.toml: DEP002 'prose' defined as a dependency but not used in the codebase
packages/mcp_adapter/pyproject.toml: DEP002 'application' defined as a dependency but not used in the codebase
packages/mcp_adapter/src/coh_mcp/handlers.py:8:1: DEP003 'coh_application' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:146:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:298:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:335:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:378:21: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:442:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:534:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:535:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:719:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:898:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:1022:9: DEP003 'coh_application' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:1023:9: DEP003 'coh_prose' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:1213:9: DEP003 'coh_prose' imported but it is a transitive dependency
Found 15 dependency issues.

For more information, see the documentation: https://deptry.com/
```

`packages/application` (exit 1)

```text
Scanning 3 files...

packages/application/pyproject.toml: DEP002 'coh-archive' defined as a dependency but not used in the codebase
packages/application/src/coh_application/foreground_service.py:293:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/application/src/coh_application/spec_gate_service.py:266:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
Found 3 dependency issues.

For more information, see the documentation: https://deptry.com/
```

`apps/api` (exit 1)

```text
Scanning 12 files...

apps/api/pyproject.toml: DEP002 'uvicorn' defined as a dependency but not used in the codebase
apps/api/pyproject.toml: DEP002 'execution-core' defined as a dependency but not used in the codebase
apps/api/pyproject.toml: DEP002 'application' defined as a dependency but not used in the codebase
apps/api/src/coh_api/api/routes/foreground.py:7:1: DEP003 'coh_api' imported but it is a transitive dependency
apps/api/src/coh_api/api/routes/foreground.py:16:1: DEP003 'coh_api' imported but it is a transitive dependency
apps/api/src/coh_api/api/routes/spec_gate.py:7:1: DEP003 'coh_api' imported but it is a transitive dependency
apps/api/src/coh_api/api/routes/spec_gate.py:15:1: DEP003 'coh_api' imported but it is a transitive dependency
apps/api/src/coh_api/composition.py:5:1: DEP003 'coh_application' imported but it is a transitive dependency
apps/api/src/coh_api/main.py:9:1: DEP003 'coh_api' imported but it is a transitive dependency
apps/api/src/coh_api/main.py:10:1: DEP003 'coh_api' imported but it is a transitive dependency
Found 10 dependency issues.

For more information, see the documentation: https://deptry.com/
```

B5 matches plan finding 3, "Default config" column, for all 7 members.

B6 `grep -c '^name = "deptry"' <worktree>/uv.lock` (exit 1 at count 0), then `grep -n -A1 -E '^name = "(click|deptry|packaging|requirements-parser)"' <worktree>/uv.lock`

```text
0
177:name = "click"
178-version = "8.5.0"
--
808:name = "packaging"
809-version = "26.3"
```

B7 `grep -n -A 10 -F '[dependency-groups]' <worktree>/pyproject.toml`

```text
8:[dependency-groups]
9-dev = [
10-    "httpx>=0.28.1",
11-    "hypothesis>=6.169.0",
12-    "mypy>=2.4.0",
13-    "pyright>=1.1.414",
14-    "pytest>=9.1.1",
15-    "pytest-asyncio>=1.4.0",
16-    "pytest-cov>=7.1.0",
17-    "ruff>=0.17.0",
18-]
```

B8 `grep -c -F '[tool.deptry' <worktree>/packages/archive/pyproject.toml <worktree>/packages/execution-core/pyproject.toml <worktree>/packages/persistence/pyproject.toml <worktree>/packages/prose/pyproject.toml <worktree>/packages/mcp_adapter/pyproject.toml <worktree>/packages/application/pyproject.toml <worktree>/apps/api/pyproject.toml` (output order as printed)

```text
<worktree>/packages/persistence/pyproject.toml:0
<worktree>/packages/archive/pyproject.toml:0
<worktree>/packages/application/pyproject.toml:0
<worktree>/packages/prose/pyproject.toml:0
<worktree>/packages/mcp_adapter/pyproject.toml:0
<worktree>/apps/api/pyproject.toml:0
<worktree>/packages/execution-core/pyproject.toml:0
```

B9 `grep -c -E '^ +"sqlalchemy' <worktree>/packages/mcp_adapter/pyproject.toml`, `grep -n -E '^ +"(coh-archive|sqlalchemy)' <worktree>/packages/application/pyproject.toml`, `grep -c -E '^ +"execution-core' <worktree>/apps/api/pyproject.toml`

```text
0
9:    "coh-archive",
1
```

## Task 1 (scratch)

Nothing in this section wrote inside `<worktree>`. Scratch tools ran through `uv pip install --target`, `uv run --no-project --with` and `uvx`, never through a virtual-environment binary path.

### Step C: the tools

V2 `uv pip install --directory <scratch>/dep-adr/tools --no-config --no-cache --no-build --strict --python 3.15 --target <scratch>/dep-adr/deptry-site deptry==0.25.1` (exit 0; V2b not needed)

```text
Using CPython 3.15.0
Resolved 4 packages in 101ms
Downloading deptry (1.8MiB)
 Downloaded deptry
Prepared 4 packages in 46ms
Installed 4 packages in 1ms
 + click==8.5.0
 + deptry==0.25.1
 + packaging==26.3
 + requirements-parser==0.13.1
```

V3 `grep -H -E "^(Tag|Root-Is-Purelib):"` on the four `WHEEL` files under `<scratch>/dep-adr/deptry-site/` (the plan's `*.dist-info/WHEEL` glob, with each file named; exit 0)

```text
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/WHEEL:Root-Is-Purelib: false
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/WHEEL:Tag: cp310-abi3-manylinux_2_17_x86_64
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/WHEEL:Tag: cp310-abi3-manylinux2014_x86_64
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/WHEEL:Root-Is-Purelib: true
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/WHEEL:Tag: py3-none-any
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/WHEEL:Root-Is-Purelib: true
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/WHEEL:Tag: py3-none-any
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/WHEEL:Root-Is-Purelib: true
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/WHEEL:Tag: py3-none-any
```

V4 `grep -r -H -E "^(Name|Version|License|Classifier: License|Requires-Dist)" <scratch>/dep-adr/deptry-site --include=METADATA` (exit 0)

```text
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/METADATA:Name: click
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/METADATA:Version: 8.5.0
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/METADATA:License-Expression: BSD-3-Clause
<scratch>/dep-adr/deptry-site/click-8.5.0.dist-info/METADATA:License-File: LICENSE.txt
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Name: deptry
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Version: 0.25.1
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Requires-Dist: click>=8.0.0,<9
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Requires-Dist: colorama>=0.4.6 ; sys_platform == 'win32'
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Requires-Dist: packaging>=23.2
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Requires-Dist: requirements-parser>=0.11.0,<1
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:Requires-Dist: tomli>=2.0.1 ; python_full_version < '3.15'
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:License-File: LICENSE
<scratch>/dep-adr/deptry-site/deptry-0.25.1.dist-info/METADATA:License-Expression: MIT
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:Name: requirements-parser
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:Version: 0.13.1
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:License: Apache-2.0
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:License-File: AUTHORS.md
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:License-File: LICENSE
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<scratch>/dep-adr/deptry-site/requirements_parser-0.13.1.dist-info/METADATA:Requires-Dist: packaging (>=23.2)
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:Name: packaging
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:Version: 26.3
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:License-Expression: Apache-2.0 OR BSD-2-Clause
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:License-File: LICENSE
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:License-File: LICENSE.APACHE
<scratch>/dep-adr/deptry-site/packaging-26.3.dist-info/METADATA:License-File: LICENSE.BSD
```

V5 `uv pip install --directory <scratch>/dep-adr/tools --no-config --no-cache --no-build --strict --python 3.13 --target <sp> pip-audit==2.10.1` (exit 0; V5b not needed)

```text
Using CPython 3.13.16
Resolved 28 packages in 154ms
Downloading pygments (1.2MiB)
Downloading pip (1.7MiB)
 Downloaded pygments
 Downloaded pip
Prepared 28 packages in 79ms
Installed 28 packages in 22ms
 + boolean-py==5.0
 + cachecontrol==0.14.4
 + certifi==2026.10.19
 + charset-normalizer==3.5.2
 + cyclonedx-python-lib==11.12.0
 + defusedxml==0.7.1
 + filelock==4.2.4
 + idna==3.20
 + license-expression==30.4.4
 + markdown-it-py==4.2.0
 + mdurl==0.1.2
 + msgpack==1.2.3
 + packageurl-python==0.17.6
 + packaging==26.3
 + pip==26.2.2
 + pip-api==0.0.35
 + pip-audit==2.10.1
 + pip-requirements-parser==32.0.1
 + platformdirs==4.13.5
 + py-serializable==2.1.0
 + pygments==2.21.0
 + pyparsing==3.3.3
 + requests==2.34.2
 + rich==15.0.0
 + sortedcontainers==2.4.0
 + tomli==2.5.0
 + tomli-w==1.2.0
 + urllib3==2.8.0
```

V6 `grep -r -H -E "^Tag:" <sp> --include=WHEEL` (exit 0)

```text
<sp>/py_serializable-2.1.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/packageurl_python-0.17.6.dist-info/WHEEL:Tag: py3-none-any
<sp>/packaging-26.3.dist-info/WHEEL:Tag: py3-none-any
<sp>/mdurl-0.1.2.dist-info/WHEEL:Tag: py3-none-any
<sp>/requests-2.34.2.dist-info/WHEEL:Tag: py3-none-any
<sp>/msgpack-1.2.3.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
<sp>/msgpack-1.2.3.dist-info/WHEEL:Tag: cp313-cp313-manylinux2014_x86_64
<sp>/msgpack-1.2.3.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_28_x86_64
<sp>/pip-26.2.2.dist-info/WHEEL:Tag: py3-none-any
<sp>/tomli_w-1.2.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/defusedxml-0.7.1.dist-info/WHEEL:Tag: py2-none-any
<sp>/defusedxml-0.7.1.dist-info/WHEEL:Tag: py3-none-any
<sp>/rich-15.0.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/cyclonedx_python_lib-11.12.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/sortedcontainers-2.4.0.dist-info/WHEEL:Tag: py2-none-any
<sp>/sortedcontainers-2.4.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/pyparsing-3.3.3.dist-info/WHEEL:Tag: py3-none-any
<sp>/boolean_py-5.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/license_expression-30.4.4.dist-info/WHEEL:Tag: py3-none-any
<sp>/cachecontrol-0.14.4.dist-info/WHEEL:Tag: py3-none-any
<sp>/tomli-2.5.0.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
<sp>/tomli-2.5.0.dist-info/WHEEL:Tag: cp313-cp313-manylinux2014_x86_64
<sp>/tomli-2.5.0.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_28_x86_64
<sp>/platformdirs-4.13.5.dist-info/WHEEL:Tag: py3-none-any
<sp>/filelock-4.2.4.dist-info/WHEEL:Tag: py3-none-any
<sp>/certifi-2026.10.19.dist-info/WHEEL:Tag: py3-none-any
<sp>/charset_normalizer-3.5.2.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_17_x86_64
<sp>/charset_normalizer-3.5.2.dist-info/WHEEL:Tag: cp313-cp313-manylinux2014_x86_64
<sp>/charset_normalizer-3.5.2.dist-info/WHEEL:Tag: cp313-cp313-manylinux_2_28_x86_64
<sp>/idna-3.20.dist-info/WHEEL:Tag: py3-none-any
<sp>/pip_api-0.0.35.dist-info/WHEEL:Tag: py3-none-any
<sp>/markdown_it_py-4.2.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/pygments-2.21.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/urllib3-2.8.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/pip_requirements_parser-32.0.1.dist-info/WHEEL:Tag: py3-none-any
<sp>/pip_audit-2.10.1.dist-info/WHEEL:Tag: py3-none-any
```

V7 `grep -r -H -E "^(Name|Version|License:|License-Expression|Classifier: License)" <sp> --include=METADATA` (exit 0). Deviation: the plan's pattern `^(...|License|...)` also matches every `License-File` line and ran to 32 KB, so the pattern was narrowed to `License:` and `License-Expression`. A follow-up call that piped this grep through `sed` to shorten paths raised a permission prompt; the lead declined it (15:41Z) and asked for the bare grep, with paths shortened here instead. Lines that are long-description text, not metadata fields (tomli's TOML note, pip_audit's table headers), are kept because grep printed them.

```text
<sp>/filelock-4.2.4.dist-info/METADATA:Name: filelock
<sp>/filelock-4.2.4.dist-info/METADATA:Version: 4.2.4
<sp>/filelock-4.2.4.dist-info/METADATA:License-Expression: MIT
<sp>/filelock-4.2.4.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/sortedcontainers-2.4.0.dist-info/METADATA:Name: sortedcontainers
<sp>/sortedcontainers-2.4.0.dist-info/METADATA:Version: 2.4.0
<sp>/sortedcontainers-2.4.0.dist-info/METADATA:License: Apache 2.0
<sp>/sortedcontainers-2.4.0.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/packageurl_python-0.17.6.dist-info/METADATA:Name: packageurl-python
<sp>/packageurl_python-0.17.6.dist-info/METADATA:Version: 0.17.6
<sp>/packageurl_python-0.17.6.dist-info/METADATA:License: MIT
<sp>/packageurl_python-0.17.6.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/packageurl_python-0.17.6.dist-info/METADATA:License: MIT
<sp>/msgpack-1.2.3.dist-info/METADATA:Name: msgpack
<sp>/msgpack-1.2.3.dist-info/METADATA:Version: 1.2.3
<sp>/msgpack-1.2.3.dist-info/METADATA:License-Expression: Apache-2.0
<sp>/py_serializable-2.1.0.dist-info/METADATA:Name: py-serializable
<sp>/py_serializable-2.1.0.dist-info/METADATA:Version: 2.1.0
<sp>/py_serializable-2.1.0.dist-info/METADATA:License: Apache-2.0
<sp>/py_serializable-2.1.0.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/pip-26.2.2.dist-info/METADATA:Name: pip
<sp>/pip-26.2.2.dist-info/METADATA:Version: 26.2.2
<sp>/pip-26.2.2.dist-info/METADATA:License-Expression: MIT
<sp>/boolean_py-5.0.dist-info/METADATA:Name: boolean.py
<sp>/boolean_py-5.0.dist-info/METADATA:Version: 5.0
<sp>/boolean_py-5.0.dist-info/METADATA:License: BSD-2-Clause
<sp>/mdurl-0.1.2.dist-info/METADATA:Name: mdurl
<sp>/mdurl-0.1.2.dist-info/METADATA:Version: 0.1.2
<sp>/mdurl-0.1.2.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/pygments-2.21.0.dist-info/METADATA:Name: Pygments
<sp>/pygments-2.21.0.dist-info/METADATA:Version: 2.21.0
<sp>/pygments-2.21.0.dist-info/METADATA:License-Expression: BSD-2-Clause
<sp>/tomli-2.5.0.dist-info/METADATA:Name: tomli
<sp>/tomli-2.5.0.dist-info/METADATA:Version: 2.5.0
<sp>/tomli-2.5.0.dist-info/METADATA:License-Expression: MIT
<sp>/tomli-2.5.0.dist-info/METADATA:Version 2.4.0 and later are compatible with [TOML v1.1.0](https://toml.io/en/v1.1.0).
<sp>/tomli_w-1.2.0.dist-info/METADATA:Name: tomli_w
<sp>/tomli_w-1.2.0.dist-info/METADATA:Version: 1.2.0
<sp>/tomli_w-1.2.0.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/pip_api-0.0.35.dist-info/METADATA:Name: pip_api
<sp>/pip_api-0.0.35.dist-info/METADATA:Version: 0.0.35
<sp>/pip_api-0.0.35.dist-info/METADATA:License:                               Apache License
<sp>/pip_api-0.0.35.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/pyparsing-3.3.3.dist-info/METADATA:Name: pyparsing
<sp>/pyparsing-3.3.3.dist-info/METADATA:Version: 3.3.3
<sp>/pyparsing-3.3.3.dist-info/METADATA:License-Expression: MIT
<sp>/certifi-2026.10.19.dist-info/METADATA:Name: certifi
<sp>/certifi-2026.10.19.dist-info/METADATA:Version: 2026.10.19
<sp>/certifi-2026.10.19.dist-info/METADATA:License: MPL-2.0
<sp>/certifi-2026.10.19.dist-info/METADATA:Classifier: License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)
<sp>/packaging-26.3.dist-info/METADATA:Name: packaging
<sp>/packaging-26.3.dist-info/METADATA:Version: 26.3
<sp>/packaging-26.3.dist-info/METADATA:License-Expression: Apache-2.0 OR BSD-2-Clause
<sp>/rich-15.0.0.dist-info/METADATA:Name: rich
<sp>/rich-15.0.0.dist-info/METADATA:Version: 15.0.0
<sp>/rich-15.0.0.dist-info/METADATA:License: MIT
<sp>/rich-15.0.0.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/requests-2.34.2.dist-info/METADATA:Name: requests
<sp>/requests-2.34.2.dist-info/METADATA:Version: 2.34.2
<sp>/requests-2.34.2.dist-info/METADATA:License: Apache-2.0
<sp>/requests-2.34.2.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/pip_requirements_parser-32.0.1.dist-info/METADATA:Name: pip-requirements-parser
<sp>/pip_requirements_parser-32.0.1.dist-info/METADATA:Version: 32.0.1
<sp>/pip_requirements_parser-32.0.1.dist-info/METADATA:License: MIT
<sp>/platformdirs-4.13.5.dist-info/METADATA:Name: platformdirs
<sp>/platformdirs-4.13.5.dist-info/METADATA:Version: 4.13.5
<sp>/platformdirs-4.13.5.dist-info/METADATA:License-Expression: MIT
<sp>/platformdirs-4.13.5.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/defusedxml-0.7.1.dist-info/METADATA:Name: defusedxml
<sp>/defusedxml-0.7.1.dist-info/METADATA:Version: 0.7.1
<sp>/defusedxml-0.7.1.dist-info/METADATA:License: PSFL
<sp>/defusedxml-0.7.1.dist-info/METADATA:Classifier: License :: OSI Approved :: Python Software Foundation License
<sp>/pip_audit-2.10.1.dist-info/METADATA:Name: pip_audit
<sp>/pip_audit-2.10.1.dist-info/METADATA:Version: 2.10.1
<sp>/pip_audit-2.10.1.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/pip_audit-2.10.1.dist-info/METADATA:Name  Version ID             Fix Versions
<sp>/pip_audit-2.10.1.dist-info/METADATA:Name  Version ID             Fix Versions Aliases
<sp>/pip_audit-2.10.1.dist-info/METADATA:Name  Version ID             Fix Versions Description
<sp>/pip_audit-2.10.1.dist-info/METADATA:Name  Version ID             Fix Versions Applied Fix
<sp>/license_expression-30.4.4.dist-info/METADATA:Name: license-expression
<sp>/license_expression-30.4.4.dist-info/METADATA:Version: 30.4.4
<sp>/license_expression-30.4.4.dist-info/METADATA:License: Apache-2.0
<sp>/charset_normalizer-3.5.2.dist-info/METADATA:Name: charset-normalizer
<sp>/charset_normalizer-3.5.2.dist-info/METADATA:Version: 3.5.2
<sp>/charset_normalizer-3.5.2.dist-info/METADATA:License: MIT
<sp>/urllib3-2.8.0.dist-info/METADATA:Name: urllib3
<sp>/urllib3-2.8.0.dist-info/METADATA:Version: 2.8.0
<sp>/urllib3-2.8.0.dist-info/METADATA:License-Expression: MIT
<sp>/cyclonedx_python_lib-11.12.0.dist-info/METADATA:Name: cyclonedx-python-lib
<sp>/cyclonedx_python_lib-11.12.0.dist-info/METADATA:Version: 11.12.0
<sp>/cyclonedx_python_lib-11.12.0.dist-info/METADATA:License: Apache-2.0
<sp>/cyclonedx_python_lib-11.12.0.dist-info/METADATA:Classifier: License :: OSI Approved :: Apache Software License
<sp>/markdown_it_py-4.2.0.dist-info/METADATA:Name: markdown-it-py
<sp>/markdown_it_py-4.2.0.dist-info/METADATA:Version: 4.2.0
<sp>/markdown_it_py-4.2.0.dist-info/METADATA:Classifier: License :: OSI Approved :: MIT License
<sp>/idna-3.20.dist-info/METADATA:Name: idna
<sp>/idna-3.20.dist-info/METADATA:Version: 3.20
<sp>/idna-3.20.dist-info/METADATA:License-Expression: BSD-3-Clause
<sp>/cachecontrol-0.14.4.dist-info/METADATA:Name: CacheControl
<sp>/cachecontrol-0.14.4.dist-info/METADATA:Version: 0.14.4
<sp>/cachecontrol-0.14.4.dist-info/METADATA:License-Expression: Apache-2.0
```

Every one of the 28 packages declares a license field or a license classifier; the four with a classifier only (pip_audit, tomli_w, markdown-it-py, mdurl) take the classifier as the source, so no license-file fallback was needed. pip_api's `License:` field holds the full Apache License text; its first line is shown. Outside the allowed list (S2): certifi (MPL-2.0) and defusedxml (PSFL, classifier Python Software Foundation License).

V7b, pip's vendored code. `grep -c -E "^License-File: src/pip/_vendor/" <sp>/pip-26.2.2.dist-info/METADATA`

```text
20
```

The 20 license files belong to 18 vendored components: packaging ships 3 (`LICENSE`, `LICENSE.APACHE`, `LICENSE.BSD`). The planner's 18 counts components.

`grep -r -c -i -E "mit license|permission is hereby granted|apache license|redistribution and use in source and binary forms|isc license|mozilla public license|python software foundation license" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor`

```text
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/packaging/LICENSE:0
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/cachecontrol/LICENSE.txt:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/certifi/LICENSE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/packaging/LICENSE.APACHE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/distro/LICENSE:4
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/distlib/LICENSE.txt:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/msgpack/COPYING:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/idna/LICENSE.md:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/platformdirs/LICENSE:2
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/pkg_resources/LICENSE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/rich/LICENSE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/requests/LICENSE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/packaging/LICENSE.BSD:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/resolvelib/LICENSE:0
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/tomli_w/LICENSE:2
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/pygments/LICENSE:1
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/pyproject_hooks/LICENSE:2
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/tomli/LICENSE:2
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/urllib3/LICENSE.txt:2
<sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/truststore/LICENSE:2
```

Two files match nothing. `packaging/LICENSE` points to the other two files:

`grep -n -i -E "license|see " <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/packaging/LICENSE`

```text
1:This software is made available under the terms of *either* of the licenses
2:found in LICENSE.APACHE or LICENSE.BSD. Contributions to this software is made
3:under the terms of *both* these licenses.
```

`resolvelib/LICENSE` carries the ISC grant text without the word "ISC":

`grep -n -i -E "isc|permission to use|permission is" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/resolvelib/LICENSE`

```text
3:Permission to use, copy, modify, and distribute this software for any
7:THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
```

The two vendored components outside the list:

`grep -n -m 1 -i -E "mozilla public license" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/certifi/LICENSE`

```text
15:This Source Code Form is subject to the terms of the Mozilla Public License,
```

`grep -n -i -E "^ *PYTHON SOFTWARE FOUNDATION LICENSE" <sp>/pip-26.2.2.dist-info/licenses/src/pip/_vendor/distlib/LICENSE.txt`

```text
93:PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
```

V8 (informational) `uv pip install --directory <scratch>/dep-adr/tools --no-config --no-cache --no-build --strict --python 3.15 --target <scratch>/dep-adr/pip-audit-site-315 pip-audit==2.10.1` (exit 0: pip-audit's closure also installs from wheels on CPython 3.15)

```text
Using CPython 3.15.0
Resolved 28 packages in 173ms
Downloading pip (1.7MiB)
Downloading pygments (1.2MiB)
 Downloaded pygments
 Downloaded pip
Prepared 28 packages in 82ms
Installed 28 packages in 28ms
 + boolean-py==5.0
 + cachecontrol==0.14.4
 + certifi==2026.10.19
 + charset-normalizer==3.5.2
 + cyclonedx-python-lib==11.12.0
 + defusedxml==0.7.1
 + filelock==4.2.4
 + idna==3.20
 + license-expression==30.4.4
 + markdown-it-py==4.2.0
 + mdurl==0.1.2
 + msgpack==1.2.3
 + packageurl-python==0.17.6
 + packaging==26.3
 + pip==26.2.2
 + pip-api==0.0.35
 + pip-audit==2.10.1
 + pip-requirements-parser==32.0.1
 + platformdirs==4.13.5
 + py-serializable==2.1.0
 + pygments==2.21.0
 + pyparsing==3.3.3
 + requests==2.34.2
 + rich==15.0.0
 + sortedcontainers==2.4.0
 + tomli==2.5.0
 + tomli-w==1.2.0
 + urllib3==2.8.0
```

V9 `uv run --no-project --no-config --python 3.15 --directory <scratch>/dep-adr/tools --with deptry==0.25.1 deptry --version`

```text
deptry 0.25.1
```

V10 `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --version`

```text
pip-audit 2.10.1
```

V11 the newest releases: the V9 command with `--with deptry` and the V10 command with `pip-audit`, both unpinned

```text
deptry 0.25.1
pip-audit 2.10.1
```

The ci.yml pins are the newest releases on 2026-10-22.

V12 `uv audit --help | grep -n -E "^Audit|--service-format|--python-platform <"`

```text
1:Audit the project's dependencies
28:      --service-format <SERVICE_FORMAT>
36:      --python-platform <PYTHON_PLATFORM>
```

### Step D: the D-04 re-derivation (D-02 passed as flags, unmodified copy)

Each command is `uv run --no-sync --directory <scratch>/dep-adr/copy --with deptry==0.25.1 deptry --no-ansi <m> --config <m>/pyproject.toml` plus the flags shown.

R1 `packages/archive --known-first-party coh_archive` (exit 0)

```text
Scanning 5 files...

Success! No dependency issues found.
```

R2 `packages/execution-core --known-first-party execution_core` (exit 0)

```text
Scanning 24 files...

Success! No dependency issues found.
```

R3 `packages/persistence --known-first-party persistence` (exit 0)

```text
Scanning 11 files...

Success! No dependency issues found.
```

R4 `packages/prose --known-first-party coh_prose` (exit 0)

```text
Scanning 3 files...

Success! No dependency issues found.
```

R5 `packages/mcp_adapter --known-first-party coh_mcp --package-module-name-map prose=coh_prose,application=coh_application` (exit 1)

```text
Scanning 6 files...

packages/mcp_adapter/src/coh_mcp/handlers.py:298:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:335:17: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:378:21: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/mcp_adapter/src/coh_mcp/handlers.py:442:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
Found 4 dependency issues.

For more information, see the documentation: https://deptry.com/
```

R6 `packages/application --known-first-party coh_application` (exit 1)

```text
Scanning 3 files...

packages/application/pyproject.toml: DEP002 'coh-archive' defined as a dependency but not used in the codebase
packages/application/src/coh_application/foreground_service.py:293:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
packages/application/src/coh_application/spec_gate_service.py:266:13: DEP003 'sqlalchemy' imported but it is a transitive dependency
Found 3 dependency issues.

For more information, see the documentation: https://deptry.com/
```

R7 `apps/api --known-first-party coh_api --package-module-name-map application=coh_application` (exit 1)

```text
Scanning 12 files...

apps/api/pyproject.toml: DEP002 'uvicorn' defined as a dependency but not used in the codebase
apps/api/pyproject.toml: DEP002 'execution-core' defined as a dependency but not used in the codebase
Found 2 dependency issues.

For more information, see the documentation: https://deptry.com/
```

R1-R7 print exactly CONTEXT D-04's five findings: application `sqlalchemy` (DEP003) and `coh-archive` (DEP002); mcp_adapter `sqlalchemy` (DEP003, 4 sites); apps/api `uvicorn` and `execution-core` (DEP002).

### Step E: pip-audit and D-06 on the real lock

D1 `uv export --directory <worktree> --locked --all-packages --no-emit-workspace --format requirements.txt --no-header --quiet -o <scratch>/dep-adr/base-hashed.txt` (exit 0, no output)

D2 `grep -c -E '^[A-Za-z0-9._-]+==' <scratch>/dep-adr/base-hashed.txt`, then `grep -n -E '^[A-Za-z0-9._-]+==.* ; ' <scratch>/dep-adr/base-hashed.txt`

```text
65
75:cffi==2.1.1 ; platform_python_implementation != 'PyPy' \
106:colorama==0.4.6 ; sys_platform == 'win32' \
177:greenlet==3.5.5 ; platform_machine == 'AMD64' or platform_machine == 'WIN32' or platform_machine == 'aarch64' or platform_machine == 'amd64' or platform_machine == 'ppc64le' or platform_machine == 'win32' or platform_machine == 'x86_64' \
207:httpcore2==2.12.0 ; sys_platform != 'emscripten' \
247:httpx2-jsfetch==1.0 ; sys_platform == 'emscripten' \
308:librt==0.16.0 ; platform_python_implementation != 'PyPy' \
434:pycparser==3.0 ; implementation_name != 'PyPy' and platform_python_implementation != 'PyPy' \
514:pywin32==312 ; sys_platform == 'win32' \
604:truststore==0.10.4 ; sys_platform != 'emscripten' \
638:uvloop==0.23.0 ; platform_python_implementation != 'PyPy' and sys_platform != 'cygwin' and sys_platform != 'win32' \
```

10 marker lines (planner: 9). The extra one is not a stop: only colorama, httpx2-jsfetch and pywin32 are false on linux x86_64 CPython, as planned.

D3 `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip -r <scratch>/dep-adr/base-hashed.txt --format json -o <scratch>/dep-adr/base-audit.json` (exit 0)

```text
No known vulnerabilities found
```

D4 `jq '{audited: (.dependencies | length), skipped: [.dependencies[] | select(.skip_reason != null) | .name], vulnerable: [.dependencies[] | select((.vulns // []) | length > 0) | .name], marker_only_present: [.dependencies[] | select(.name == "colorama" or .name == "pywin32" or .name == "httpx2-jsfetch") | .name]}' <scratch>/dep-adr/base-audit.json`

```text
{
  "audited": 62,
  "skipped": [],
  "vulnerable": [],
  "marker_only_present": []
}
```

D5 `<scratch>/dep-adr/probe/marker-only.txt` holds the single line `colorama==0.4.6 ; sys_platform == 'win32'` (Write tool). `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip --no-deps -r <scratch>/dep-adr/probe/marker-only.txt` (exit 0)

```text
WARNING:pip_audit._cli:--no-deps is supported, but users are encouraged to fully hash their pinned dependencies
WARNING:pip_audit._cli:Consider using a tool like `pip-compile`: https://pip-tools.readthedocs.io/en/latest/#using-hashes
No known vulnerabilities found
```

D6 `<scratch>/dep-adr/probe/vulnerable.txt` holds `requests==2.19.1` (Write tool). The D5 command on it (exit 1)

```text
WARNING:pip_audit._cli:--no-deps is supported, but users are encouraged to fully hash their pinned dependencies
WARNING:pip_audit._cli:Consider using a tool like `pip-compile`: https://pip-tools.readthedocs.io/en/latest/#using-hashes
Found 10 known vulnerabilities in 1 package
Name     Version ID              Fix Versions
-------- ------- --------------- ------------
requests 2.19.1  PYSEC-2018-28   2.20.0
requests 2.19.1  PYSEC-2018-28   2.20.0
requests 2.19.1  PYSEC-2023-74   2.31.0
requests 2.19.1  PYSEC-2023-74   2.31.0
requests 2.19.1  PYSEC-2026-1873 2.32.0
requests 2.19.1  PYSEC-2026-1872 2.32.4
requests 2.19.1  PYSEC-2026-2275 2.33.0
requests 2.19.1  PYSEC-2026-1873 2.32.0
requests 2.19.1  PYSEC-2026-1872 2.32.4
requests 2.19.1  PYSEC-2026-2275 2.33.0
```

D7 `git -C <worktree> status --porcelain --untracked-files=all --ignored`

```text
(no output, the same as PC8)
```

### Step F: the tracer (the whole change in the scratch copy)

T1 With the Edit tool, T-CFG applied to the 7 member files and T-DEP to `packages/application/pyproject.toml` and `apps/api/pyproject.toml` in `<scratch>/dep-adr/copy`, exactly as the plan writes them.

T2 `uv add --directory <scratch>/dep-adr/copy --dev --no-sync "deptry==0.25.1"` (exit 0), then the Edit tool changed `"deptry==0.25.1",` to `"deptry>=0.25.1",`; `grep -n -F '"deptry' <scratch>/dep-adr/copy/pyproject.toml`

```text
Resolved 75 packages in 123ms
10:    "deptry>=0.25.1",
```

T3 `uv lock --directory <scratch>/dep-adr/copy` (exit 0), then `uv lock --check --directory <scratch>/dep-adr/copy`

```text
Resolved 75 packages in 5ms
Resolved 75 packages in 0.83ms
exit=0
```

T4 `git diff --no-index --unified=0 --output=<scratch>/dep-adr/lockdiff.txt <worktree>/uv.lock <scratch>/dep-adr/copy/uv.lock` (exit 1: the files differ, as expected)

T5 `grep -c -E '^-[^-]' <scratch>/dep-adr/lockdiff.txt`

```text
4
```

T6 `grep -E '^[-+](name|version) = |^[-+] +\{ name = ' <scratch>/dep-adr/lockdiff.txt` (exactly the 17 lines of plan finding 6)

```text
-    { name = "coh-archive" },
+    { name = "sqlalchemy" },
-    { name = "coh-archive", editable = "packages/archive" },
+    { name = "sqlalchemy", specifier = ">=2.0.0" },
-    { name = "execution-core" },
-    { name = "execution-core", editable = "packages/execution-core" },
+    { name = "deptry" },
+    { name = "deptry", specifier = ">=0.25.1" },
+name = "deptry"
+version = "0.25.1"
+    { name = "click" },
+    { name = "colorama", marker = "sys_platform == 'win32'" },
+    { name = "packaging" },
+    { name = "requirements-parser" },
+name = "requirements-parser"
+version = "0.13.1"
+    { name = "packaging" },
```

T7 `uv sync --directory <scratch>/dep-adr/copy --all-packages --locked` (exit 0)

```text
Resolved 75 packages in 0.87ms
   Building application @ file://<scratch>/dep-adr/copy/packages/application
   Building coh-api @ file://<scratch>/dep-adr/copy/apps/api
   Building coh-archive @ file://<scratch>/dep-adr/copy/packages/archive
   Building execution-core @ file://<scratch>/dep-adr/copy/packages/execution-core
   Building mcp-adapter @ file://<scratch>/dep-adr/copy/packages/mcp_adapter
   Building persistence @ file://<scratch>/dep-adr/copy/packages/persistence
   Building prose @ file://<scratch>/dep-adr/copy/packages/prose
      Built persistence @ file://<scratch>/dep-adr/copy/packages/persistence
      Built coh-api @ file://<scratch>/dep-adr/copy/apps/api
      Built mcp-adapter @ file://<scratch>/dep-adr/copy/packages/mcp_adapter
      Built execution-core @ file://<scratch>/dep-adr/copy/packages/execution-core
      Built coh-archive @ file://<scratch>/dep-adr/copy/packages/archive
      Built prose @ file://<scratch>/dep-adr/copy/packages/prose
      Built application @ file://<scratch>/dep-adr/copy/packages/application
Prepared 7 packages in 213ms
Uninstalled 7 packages in 0.67ms
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
Installed 9 packages in 1ms
 ~ application==0.1.0 (from file://<scratch>/dep-adr/copy/packages/application)
 ~ coh-api==0.1.0 (from file://<scratch>/dep-adr/copy/apps/api)
 ~ coh-archive==0.1.0 (from file://<scratch>/dep-adr/copy/packages/archive)
 + deptry==0.25.1
 ~ execution-core==0.1.0 (from file://<scratch>/dep-adr/copy/packages/execution-core)
 ~ mcp-adapter==0.1.0 (from file://<scratch>/dep-adr/copy/packages/mcp_adapter)
 ~ persistence==0.1.0 (from file://<scratch>/dep-adr/copy/packages/persistence)
 ~ prose==0.1.0 (from file://<scratch>/dep-adr/copy/packages/prose)
 + requirements-parser==0.13.1
```

T8 `uv run --no-sync --directory <scratch>/dep-adr/copy deptry --version`, then `uv run --no-sync --directory <scratch>/dep-adr/copy deptry --no-ansi <m> --config <m>/pyproject.toml` for each member (each exit 0)

```text
deptry 0.25.1
```

| Member | Exit | Output |
|---|---|---|
| packages/archive | 0 | `Scanning 5 files...` / `Success! No dependency issues found.` |
| packages/execution-core | 0 | `Scanning 24 files...` / `Success! No dependency issues found.` |
| packages/persistence | 0 | `Scanning 11 files...` / `Success! No dependency issues found.` |
| packages/prose | 0 | `Scanning 3 files...` / `Success! No dependency issues found.` |
| packages/mcp_adapter | 0 | `Scanning 6 files...` / `Success! No dependency issues found.` |
| packages/application | 0 | `Scanning 3 files...` / `Success! No dependency issues found.` |
| apps/api | 0 | `Scanning 12 files...` / `Success! No dependency issues found.` |

Each run printed exactly those two lines with a blank line between them.

T9 `uv export --directory <scratch>/dep-adr/copy --locked --all-packages --no-emit-workspace --format requirements.txt --no-header --quiet -o <scratch>/dep-adr/build-hashed.txt` (exit 0, no output), `grep -c -E '^[A-Za-z0-9._-]+==' <scratch>/dep-adr/build-hashed.txt`, then `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip -r <scratch>/dep-adr/build-hashed.txt` (exit 0)

```text
67
No known vulnerabilities found
```

T10 `uv run --no-sync --directory <scratch>/dep-adr/copy pytest tests/packages/application tests/apps/api tests/packages/mcp_adapter -q` (75 = B1 27 + B2 9 + B3 39)

```text
........................................................................ [ 96%]
...                                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.15/site-packages/starlette/testclient.py:53
  <scratch>/dep-adr/copy/.venv/lib/python3.15/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

tests/apps/api/test_api_integration.py::TestI02ReadinessGate::test_confirm_blocked_when_spec_is_blocked
  <scratch>/dep-adr/copy/.venv/lib/python3.15/site-packages/anyio/_backends/_asyncio.py:1100: StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = context.run(func, *args)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
75 passed, 2 warnings in 0.93s
```

After T10, `git -C <worktree> status --porcelain --untracked-files=all --ignored` printed nothing.

### Step G: stop rules

- S1 (D13 reopen): did not fire. V2 (CPython 3.15) and V5 (CPython 3.13) installed every package from a wheel with `--no-build --no-cache`.
- S2 (license): fired, which is not a stop. Outside the allowed list: certifi 2026.10.19 (MPL-2.0) and defusedxml 0.7.1 (PSF-2.0) in pip-audit's closure, and certifi (MPL-2.0) and distlib (PSF-2.0) vendored in pip 26.2.2. ADR-0003 carries them as owner questions.
- S3 (findings): did not fire. R1-R7 print exactly D-04's five findings.
- S4 (advisory): did not fire. D3 and T9 report no known vulnerability.
- S5 (D-06): did not fire. D5 exits 0 and D4 shows `skipped: []`; no exclusion is needed.
- S6 (tracer): did not fire. All 7 T8 runs exit 0 with the planned file counts, T5 prints 4, T6 prints the 17 planned lines, T9 exits 0, and T10 equals B1 + B2 + B3.

## Task 4 (build)

Resume row qitem-20261022162351-9cad306d: the owner accepted ADR-0003 (Q1 and Q2 accept, Q3 approve CI-only as D18, Q4 confirm under D16, Q5 accept). The lead's D18 commit d92220a was already the worktree HEAD (`git -C <worktree> pull --ff-only` printed `Already up to date.`; `git log -3` showed d92220a on top). L1-L13 unchanged.

### Step A: acceptance

ADR-0003 set to Accepted (Deciders, PR #39, Decision log D18 and D16, owner answers line, tables, checklist, reopen line); index row set to Accepted. Commit d3e8da0 `docs(adr): accept ADR-0003 (owner decision qitem-20261022162351-9cad306d)`.

### Step B: deptry in the root dev group

`uv add --directory <worktree> --dev --no-sync "deptry==0.25.1"` (exit 0)

```text
Using CPython 3.15.0
Resolved 75 packages in 142ms
```

The Edit tool changed `"deptry==0.25.1",` to `"deptry>=0.25.1",`. Then `uv lock --directory <worktree>` (exit 0) and `git -C <worktree> diff --numstat`

```text
Using CPython 3.15.0
Resolved 75 packages in 6ms
1	0	pyproject.toml
36	0	uv.lock
```

Self-scan of the added lines: 0. Commit 73a48ba `build(deps): add deptry 0.25.1 to the root dev group (ADR-0003, SUPP-01)`.

### Step C: member config and the D-04 split

T-CFG and T-DEP applied with the Edit tool, exactly as in the tracer. Then `uv lock --directory <worktree>`, `uv lock --check --directory <worktree>` and `git -C <worktree> diff --numstat`

```text
Using CPython 3.15.0
Resolved 75 packages in 6ms
Using CPython 3.15.0
Resolved 75 packages in 0.86ms
exit=0
11	1	apps/api/pyproject.toml
4	2	packages/application/pyproject.toml
3	0	packages/archive/pyproject.toml
3	0	packages/execution-core/pyproject.toml
15	0	packages/mcp_adapter/pyproject.toml
3	0	packages/persistence/pyproject.toml
3	0	packages/prose/pyproject.toml
2	4	uv.lock
```

Self-scan of the added lines: 0. Commit 67d62d8 `chore(deps): deptry config per member and the D-04 split (ADR-0003, SUPP-01)`.

### Step D: the real entry points on the committed tree

`uv sync --directory <worktree> --all-packages --locked` (exit 0)

```text
Using CPython 3.15.0
Creating virtual environment at: .venv
Resolved 75 packages in 0.80ms
   Building application @ file://<worktree>/packages/application
   Building coh-api @ file://<worktree>/apps/api
   Building coh-archive @ file://<worktree>/packages/archive
   Building execution-core @ file://<worktree>/packages/execution-core
   Building persistence @ file://<worktree>/packages/persistence
   Building mcp-adapter @ file://<worktree>/packages/mcp_adapter
   Building prose @ file://<worktree>/packages/prose
      Built persistence @ file://<worktree>/packages/persistence
      Built application @ file://<worktree>/packages/application
      Built coh-archive @ file://<worktree>/packages/archive
      Built mcp-adapter @ file://<worktree>/packages/mcp_adapter
      Built execution-core @ file://<worktree>/packages/execution-core
      Built prose @ file://<worktree>/packages/prose
      Built coh-api @ file://<worktree>/apps/api
Prepared 7 packages in 221ms
Installed 71 packages in 28ms
```

The 71 `+` lines are the B0 list (with `<worktree>` in place of `<scratch>/dep-adr/copy`) plus `+ deptry==0.25.1` and `+ requirements-parser==0.13.1`.

`uv run --no-sync --directory <worktree> deptry --version` (the value the lead's version gate checks)

```text
deptry 0.25.1
```

`uv run --no-sync --directory <worktree> deptry --no-ansi <m> --config <m>/pyproject.toml` for each member (criterion 4):

| Member | Exit | Output |
|---|---|---|
| packages/archive | 0 | `Scanning 5 files...` / `Success! No dependency issues found.` |
| packages/execution-core | 0 | `Scanning 24 files...` / `Success! No dependency issues found.` |
| packages/persistence | 0 | `Scanning 11 files...` / `Success! No dependency issues found.` |
| packages/prose | 0 | `Scanning 3 files...` / `Success! No dependency issues found.` |
| packages/mcp_adapter | 0 | `Scanning 6 files...` / `Success! No dependency issues found.` |
| packages/application | 0 | `Scanning 3 files...` / `Success! No dependency issues found.` |
| apps/api | 0 | `Scanning 12 files...` / `Success! No dependency issues found.` |

Each run printed exactly those two lines with a blank line between them.

`uv export --directory <worktree> --locked --all-packages --no-emit-workspace --format requirements.txt --no-header --quiet -o <scratch>/dep-adr/head-hashed.txt` (exit 0, no output), then `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip -r <scratch>/dep-adr/head-hashed.txt` (exit 0; criterion 4)

```text
No known vulnerabilities found
```

`uv export --directory <worktree> --locked --all-packages --no-emit-workspace --format requirements.txt --no-hashes --no-header --quiet -o <scratch>/dep-adr/head-nohash.txt` (exit 0, no output), then `grep -c -E '^[A-Za-z0-9._-]+=='`, `grep -c -E '^(fastapi|sqlalchemy|mcp|pyyaml)=='` and `grep -c -E '^-e '` on it (criterion 3)

```text
67
4
0
```

Tests (B1-B3 counts):

`uv run --no-sync --directory <worktree> pytest tests/packages/application -q`

```text
...........................                                              [100%]
27 passed in 0.87s
```

`uv run --no-sync --directory <worktree> pytest tests/apps/api -q`

```text
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.15/site-packages/starlette/testclient.py:53
  <worktree>/.venv/lib/python3.15/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

tests/apps/api/test_api_integration.py::TestI02ReadinessGate::test_confirm_blocked_when_spec_is_blocked
  <worktree>/.venv/lib/python3.15/site-packages/anyio/_backends/_asyncio.py:1100: StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    result = context.run(func, *args)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 2 warnings in 0.42s
```

`uv run --no-sync --directory <worktree> pytest tests/packages/mcp_adapter -q`

```text
.......................................                                  [100%]
39 passed in 0.85s
```

`uv run --no-sync --directory <worktree> ruff check .` and `uv run --no-sync --directory <worktree> ruff format --check .`

```text
All checks passed!
193 files already formatted
```

### Step E: bite proofs (criterion 5)

`cp -r <worktree>/packages/prose <scratch>/dep-adr/bite-prose`, then the Edit tool added `    "sqlalchemy>=2.0.0",` after `    "pydantic>=2.9.0",` in `<scratch>/dep-adr/bite-prose/pyproject.toml`. `uv run --no-sync --directory <worktree> deptry --no-ansi <scratch>/dep-adr/bite-prose --config <scratch>/dep-adr/bite-prose/pyproject.toml` (exit 1)

```text
Scanning 3 files...

<scratch>/dep-adr/bite-prose/pyproject.toml: DEP002 'sqlalchemy' defined as a dependency but not used in the codebase
Found 1 dependency issue.

For more information, see the documentation: https://deptry.com/
```

Task 1's D6 again: `uvx --directory <scratch>/dep-adr/tools --no-config --python 3.13 pip-audit==2.10.1 --strict --disable-pip --no-deps -r <scratch>/dep-adr/probe/vulnerable.txt` (exit 1)

```text
WARNING:pip_audit._cli:--no-deps is supported, but users are encouraged to fully hash their pinned dependencies
WARNING:pip_audit._cli:Consider using a tool like `pip-compile`: https://pip-tools.readthedocs.io/en/latest/#using-hashes
Found 10 known vulnerabilities in 1 package
Name     Version ID              Fix Versions
-------- ------- --------------- ------------
requests 2.19.1  PYSEC-2018-28   2.20.0
requests 2.19.1  PYSEC-2018-28   2.20.0
requests 2.19.1  PYSEC-2023-74   2.31.0
requests 2.19.1  PYSEC-2023-74   2.31.0
requests 2.19.1  PYSEC-2026-1873 2.32.0
requests 2.19.1  PYSEC-2026-1872 2.32.4
requests 2.19.1  PYSEC-2026-2275 2.33.0
requests 2.19.1  PYSEC-2026-1873 2.32.0
requests 2.19.1  PYSEC-2026-1872 2.32.4
requests 2.19.1  PYSEC-2026-2275 2.33.0
```

`git -C <worktree> status --porcelain --untracked-files=all` after both bites printed nothing.

### Task 4 gates

`git -C <worktree> diff origin/main...HEAD -- uv.lock | grep -E '^\+name = '`

```text
+name = "deptry"
+name = "requirements-parser"
```

The same diff piped to `grep -c -E '^-[^-]'`, then to `grep -c -E '^-version = '`

```text
4
0
```

`grep -n -F '"deptry>=' <worktree>/pyproject.toml`

```text
10:    "deptry>=0.25.1",
```

`grep -c -F '[tool.deptry]'` on the 7 member files: each prints 1 (output order as printed: prose, execution-core, persistence, mcp_adapter, application, archive, apps/api).

`grep -n -E '^DEP00[0-9] = '` on the 7 member files

```text
<worktree>/packages/mcp_adapter/pyproject.toml:46:DEP003 = ["sqlalchemy"]
<worktree>/apps/api/pyproject.toml:30:DEP002 = ["uvicorn"]
```

`grep -n -E '^(ignore|exclude|extend_exclude|requirements_files|requirements_files_dev|pep621_dev_dependency_groups|optional_dependencies_dev_groups|non_dev_dependency_groups|experimental_namespace_package) *='` on the 7 member files: no output, exit 1 (the pass state).

`grep -c -E '^ +"sqlalchemy' <worktree>/packages/mcp_adapter/pyproject.toml`

```text
0
```

`grep -n -E '^ +"(coh-archive|sqlalchemy|execution-core)' <worktree>/packages/application/pyproject.toml <worktree>/apps/api/pyproject.toml`

```text
<worktree>/packages/application/pyproject.toml:7:    "execution-core",
<worktree>/packages/application/pyproject.toml:9:    "sqlalchemy>=2.0.0",
```

`git -C <worktree> diff --numstat origin/main...HEAD -- pyproject.toml packages apps` (equals the planner numstat)

```text
11	1	apps/api/pyproject.toml
4	2	packages/application/pyproject.toml
3	0	packages/archive/pyproject.toml
3	0	packages/execution-core/pyproject.toml
15	0	packages/mcp_adapter/pyproject.toml
3	0	packages/persistence/pyproject.toml
3	0	packages/prose/pyproject.toml
1	0	pyproject.toml
```

D-07 order, `git -C <worktree> log --reverse --format="%h %ae %s" --name-only origin/main..HEAD` (author addresses: lead commits `lead-seat@coh-fleet.invalid`, builder commits the repository's default noreply address, shown here as `<builder>`)

```text
6fa1cee lead-seat@coh-fleet.invalid docs(03): plan for the deptry and pip-audit jobs
.planning/phases/03-dependency-audit-job/03-01-PLAN.md
02105fb lead-seat@coh-fleet.invalid ci: deptry and pip-audit jobs (SUPP-01 checks)
.github/workflows/ci.yml
2c6a1e4 <builder> docs(adr): propose ADR-0003, deptry and pip-audit in CI (SUPP-01)
.planning/phases/03-dependency-audit-job/03-EVIDENCE.md
docs/adr/0003-dependency-audit-deptry-pip-audit.md
docs/adr/README.md
d92220a lead-seat@coh-fleet.invalid docs(decision-log): D18, PSF-2.0 in pip-audit's CI-only closure
README.md
docs/decision-log.md
d3e8da0 <builder> docs(adr): accept ADR-0003 (owner decision qitem-20261022162351-9cad306d)
docs/adr/0003-dependency-audit-deptry-pip-audit.md
docs/adr/README.md
73a48ba <builder> build(deps): add deptry 0.25.1 to the root dev group (ADR-0003, SUPP-01)
pyproject.toml
uv.lock
67d62d8 <builder> chore(deps): deptry config per member and the D-04 split (ADR-0003, SUPP-01)
apps/api/pyproject.toml
packages/application/pyproject.toml
packages/archive/pyproject.toml
packages/execution-core/pyproject.toml
packages/mcp_adapter/pyproject.toml
packages/persistence/pyproject.toml
packages/prose/pyproject.toml
uv.lock
```

No `pyproject.toml` or `uv.lock` path appears before the accept commit d3e8da0.
