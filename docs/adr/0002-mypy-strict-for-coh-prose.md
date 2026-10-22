# ADR-0002: Add mypy to the root dev group and check coh_prose with mypy --strict

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** proposed by the builder seat (chores-q4 Phase 4); accepted by the owner (Q1 accept, Q2 approve), queue row qitem-20261022141325-97bd7544
- **Slice / PR:** chores-q4 Phase 4, TYPE-03; PR #38
- **Decision log:** D17 (pathspec under MPL-2.0, dev-only). D16's reopen condition was met ("another MPL-2.0 or weak-copyleft package enters the lock"); D16 stands for certifi.

## Question

TYPE-03 needs one module under `mypy --strict`, with CI running that check on every PR. mypy is a new dependency, and a new dependency needs an accepted ADR (`CONTRIBUTING.md`, Definition of Done). Which mypy version and config do we adopt, and do mypy and every package it pulls in install from wheels and carry an acceptable license on CPython 3.15?

## Context

- TYPE-03: "One module passes `mypy --strict`, and CI runs that check on every PR" (`.planning/REQUIREMENTS.md:13`).
- Scope (`04-CONTEXT.md`): the module is the existing `coh_prose` package (`__init__.py`, `policy.py`, `renderer.py`); no new code is written (D-01). Only the source tree is checked, not `tests/packages/prose` (D-02). The scope comes from the path in the CI command, not from config (D-07).
- Placement (D-05): mypy goes into the root `[dependency-groups] dev`, so CI's `uv sync --all-packages` installs it (ADR-0001). The floor equals the locked version (ADR-0001, amendment 2026-10-11).
- Config (D-06): root `[tool.mypy]` with `strict = true` and `python_version = "3.15"`. No per-module overrides, no ignore keys, no import-following key, no plugin. If mypy refused `python_version = "3.15"`, the key would be dropped, never lowered.
- Source (D-08): no source change is expected. If mypy reports errors, fix them with annotations only, keep pyright at 0, add no suppression.
- Baselines at origin/main f33c7cb plus the lead's commits: `uv run pyright packages/prose` prints `0 errors, 0 warnings, 0 informations`; `uv run pytest tests/packages/prose -q` prints `36 passed` (`04-EVIDENCE.md`, Baseline).
- Python and wheels: the floor is CPython 3.15 (D12). A dependency without a cp315 wheel is acceptable only while its sdist builds in CI; a failure to install from wheel or sdist reopens D13.
- License policy: MIT, Apache-2.0, BSD and ISC are allowed without approval; anything else needs the owner (`CONTRIBUTING.md`, `FLEET-POLICY.md` Security row). D16 approves certifi under MPL-2.0 and says it approves no other MPL-2.0 package.
- The CI step already exists: the lead's checks commit 0b49391 adds `uv run mypy --strict packages/prose/src/coh_prose` to `.github/workflows/ci.yml` after the ruff format check. Until mypy is in the dev group, that step cannot spawn mypy, so the PR's Lint and Test job is red at that step.
- D-03a check, run on 2026-10-22 in a scratch virtual environment outside the repository (full output in the appendix):
  - CPython 3.15.0 (V5). `uv pip install --no-build --no-cache mypy` resolved mypy 2.4.0 and 5 other packages, and installed all 6 from published wheels; no sdist was built (V3).
  - Wheel tags (V6): mypy and librt `cp315-cp315-manylinux_2_17_x86_64`; ast-serialize `cp315-abi3-manylinux_2_17_x86_64`; mypy-extensions, pathspec and typing-extensions `py3-none-any`.
  - Licenses (V7 and the license files): mypy, mypy-extensions, librt and ast-serialize MIT; pathspec MPL-2.0; typing-extensions PSF-2.0 (already locked, not new).
  - `python_version = "3.15"` is accepted: a config file with the D-06 table prints the Success line and no complaint (V10). Strict mode comes from the file: an untyped `def` fails with `no-untyped-def` without the `--strict` flag (V11).
  - Preview on the real tree: the D-06 config on `packages/prose/src/coh_prose` prints `Success: no issues found in 3 source files` (V12). No source change is expected.
  - Already in `uv.lock` (V13): only typing-extensions 4.16.0, the same version mypy resolved. The new lock packages would be ast-serialize, librt, mypy, mypy-extensions and pathspec. This is inferred from V3 and V13; Task 4's lock diff confirms it.

## Options considered

### Option A: mypy 2.4.0 in the root dev group, floor `>=2.4.0`, D-06 config
- What it is: add `"mypy>=2.4.0"` to the root `[dependency-groups] dev`, lock it at 2.4.0, add the root `[tool.mypy]` table (`strict = true`, `python_version = "3.15"`), and let the lead's CI step pick the path.
- Pros: one install path for every dev tool (ADR-0001); the version CI runs is pinned by `uv.lock` with hashes; the config is two keys with nothing that weakens strict mode; the check passes today with no source change (V12).
- Cons: five new packages in the dev lock, one of them (pathspec) under MPL-2.0, which needs an owner decision. A second strict type checker on coh_prose means a fix must satisfy both mypy and pyright.
- Cost to adopt and reverse: small. One dev-group line, one config table and the lock entries. Revert the builder commits to remove it; the CI step comes out only through a lead checks commit.

### Option B: do nothing (pyright strict only)
- What it is: keep pyright as the only type checker.
- Pros: no new dependency, no license question.
- Cons: TYPE-03 stays unmet, and the lead's CI step stays red until a lead checks commit removes it.
- Cost to adopt and reverse: none to adopt; the requirement stays open.

### Option C: run mypy through an unlocked tool runner (`uvx mypy`)
- What it is: call mypy in CI without adding it to the project.
- Pros: nothing in `pyproject.toml` or `uv.lock`.
- Cons: the version is not pinned by `uv.lock`, so CI can change checker versions between runs; it creates a second place for dev tools, against ADR-0001; it does not avoid the pathspec license question, since the same closure is installed.
- Cost to adopt and reverse: small to adopt; it brings back the drift ADR-0001 removed.

## Decision

**Selected:** Option A, with mypy 2.4.0 (floor `>=2.4.0`, equal to the locked version). `python_version = "3.15"` is kept, because mypy 2.4.0 accepts it (V10).

Option A is the only option that meets TYPE-03 with a pinned, locked checker and a config that cannot quietly weaken strict mode. The accepted downside is the pathspec license question below and a second checker that every coh_prose change must satisfy.

| Package | Version | Role | In uv.lock before this ADR | License (source) | Allowed list | Wheel installed on CPython 3.15 |
|---|---|---|---|---|---|---|
| mypy | 2.4.0 | direct | no | MIT (METADATA `License-Expression`); bundles typeshed, Apache-2.0 and MIT (`licenses/mypy/typeshed/LICENSE`) | yes | `cp315-cp315-manylinux_2_17_x86_64` |
| ast-serialize | 0.13.1 | transitive of mypy | no | MIT (METADATA `License-Expression`; `licenses/crates/LICENSE` lists 16 derived libraries, each with the MIT grant) | yes | `cp315-abi3-manylinux_2_17_x86_64` |
| librt | 0.16.0 | transitive of mypy | no | MIT (METADATA `License-Expression`) | yes | `cp315-cp315-manylinux_2_17_x86_64` |
| mypy-extensions | 1.1.0 | transitive of mypy | no | MIT (METADATA `License-Expression`; `licenses/LICENSE` line 1) | yes | `py3-none-any` |
| pathspec | 1.1.1 | transitive of mypy | no | MPL-2.0 (METADATA classifier; `licenses/LICENSE` line 1) | no: owner approved, D17 | `py3-none-any` |
| typing-extensions | 4.16.0 | transitive of mypy | yes (4.16.0) | PSF-2.0 (METADATA `License-Expression`) | not new: already locked, unchanged | `py3-none-any` |

The planner's PyPI pre-read showed no license field for mypy-extensions. The installed 1.1.0 wheel declares `License-Expression: MIT`, and its license file says MIT, so it is on the allowed list.

### Owner decisions needed

- **Q1:** Accept mypy 2.4.0 and the closure in the table above, with the D-06 config (`strict = true`, `python_version = "3.15"`)? **Recommended default:** accept.
- **Q2:** Approve pathspec 1.1.1 under MPL-2.0 as a dev-only transitive dependency of mypy? **Recommended default:** approve for dev-only use on D16's reasoning (dev-only, used unmodified, not vendored or redistributed), recorded by the lead as its own decision-log entry, because D16 approves no other MPL-2.0 package. Alternative: reject; this phase then stops with TYPE-03 unmet until a mypy release without that dependency is evaluated.

No package installed from an sdist build, so there is no sdist question (V3 ran with `--no-build`).

**Owner answers (2026-10-22, queue row qitem-20261022141325-97bd7544):** Q1 accept. Q2 approve; the lead recorded it as D17.

## Consequences

- **What changes:** root `pyproject.toml` gains `"mypy>=2.4.0"` in the dev group and a `[tool.mypy]` table with `strict = true` and `python_version = "3.15"`. `uv.lock` gains ast-serialize, librt, mypy, mypy-extensions and pathspec. The lead's CI step (0b49391) starts passing. No coh_prose source change is expected (V12).
- **What gets easier:** coh_prose has a second, independent strict checker in CI, and the same command runs locally with `uv run`.
- **What gets harder:** two strict checkers on coh_prose. A change must satisfy both with no suppression (D-08).
- **Follow-up work,** each its own item:
  - The docs name pyright as the only type checker and are not edited here (D-09): `CONTRIBUTING.md:46`, `:54`, `:63`; `docs/coding-rules.md:69`, `:90`, `:192`, `:208`; `AGENTS.md:37`, `:41`.
  - `README.md:49-50` lists the dev-group tools and will not name mypy.
  - checks-guard rules for mypy-weakening config: an Ask, as a separate checks change.
  - mypy beyond coh_prose: deferred.
- **Rollback:** revert the builder commits (dependency, lock and config). The CI step comes out only through a lead checks commit.

## Compliance checklist

- [x] Stays inside the layer rules: no source change expected; any fix is an annotation in coh_prose only.
- [x] New dependency: mypy 2.4.0 (MIT), ast-serialize 0.13.1 (MIT), librt 0.16.0 (MIT), mypy-extensions 1.1.0 (MIT), pathspec 1.1.1 (MPL-2.0). pathspec is outside the allowed list; the owner approved it for dev-only use (Q2, D17). Maintenance status: V3 resolved mypy 2.4.0 as the newest release on PyPI; release dates and maintainer activity were not checked.
- [x] Schema change: not applicable.
- [x] Public API, wire format or archive format: not applicable.
- [x] No new infrastructure.
- [x] Tests: no behavior change; pyright (0) and the prose tests (36 passed) are re-run after the build.
- [x] Decision-log entry: no execution-semantics change. The pathspec license approval, if given, is its own entry written by the lead (Q2).

## Reopen when

- mypy or a closure package stops shipping a wheel for the CPython version CI runs, or an sdist build fails (D13).
- mypy refuses the configured `python_version`.
- A closure license changes, or a package with a license outside the allowed list enters the closure.
- A coh_prose change cannot satisfy both mypy and pyright without a suppression.
- Scope widens beyond coh_prose.

## References

- `.planning/phases/04-mypy-strict-for-coh-prose/04-CONTEXT.md`
- `.planning/ROADMAP.md` (Phase 4), `.planning/REQUIREMENTS.md` (TYPE-03)
- `docs/adr/0001-uv-dev-dependency-group.md`
- `docs/decision-log.md` D12, D13, D16 and D17
- `CONTRIBUTING.md`, `FLEET-POLICY.md` (Security row)
- `https://pypi.org/project/mypy/`, `https://pypi.org/project/ast-serialize/`, `https://pypi.org/project/librt/`, `https://pypi.org/project/mypy-extensions/`, `https://pypi.org/project/pathspec/`, `https://pypi.org/project/typing-extensions/`
- mypy configuration docs: `https://mypy.readthedocs.io/en/stable/config_file.html`

## Appendix: D-03a verification output

Run on 2026-10-22 with uv 0.13.0. `<scratch>` is a directory outside the repository; `<sp>` stands for `<scratch>/mypy-adr/venv/lib/python3.15/site-packages`. Paths are replaced; the output is otherwise verbatim.

V2 `uv venv --no-project --no-config --python 3.15 <scratch>/mypy-adr/venv` (exit 0)

```text
Using CPython 3.15.0
Creating virtual environment at: <scratch>/mypy-adr/venv
Activate with: source <scratch>/mypy-adr/venv/bin/activate
```

V3 `uv pip install --no-config --no-cache --no-build --strict --python <scratch>/mypy-adr/venv/bin/python mypy` (exit 0)

```text
Using Python 3.15.0 environment at: <scratch>/mypy-adr/venv
Resolved 6 packages in 153ms
Downloading mypy (14.7MiB)
Downloading ast-serialize (1.2MiB)
 Downloaded ast-serialize
 Downloaded mypy
Prepared 6 packages in 179ms
Installed 6 packages in 5ms
 + ast-serialize==0.13.1
 + librt==0.16.0
 + mypy==2.4.0
 + mypy-extensions==1.1.0
 + pathspec==1.1.1
 + typing-extensions==4.16.0
```

V4 `uv pip list --no-config --python <scratch>/mypy-adr/venv/bin/python` (exit 0)

```text
Using Python 3.15.0 environment at: <scratch>/mypy-adr/venv
Package           Version
----------------- -------
ast-serialize     0.13.1
librt             0.16.0
mypy              2.4.0
mypy-extensions   1.1.0
pathspec          1.1.1
typing-extensions 4.16.0
```

V5 `<scratch>/mypy-adr/venv/bin/python --version` (exit 0)

```text
Python 3.15.0
```

V6 `grep -H -E "^(Tag|Root-Is-Purelib):" <sp>/*.dist-info/WHEEL` (exit 0)

```text
<sp>/pathspec-1.1.1.dist-info/WHEEL:Root-Is-Purelib: true
<sp>/pathspec-1.1.1.dist-info/WHEEL:Tag: py3-none-any
<sp>/mypy_extensions-1.1.0.dist-info/WHEEL:Root-Is-Purelib: true
<sp>/mypy_extensions-1.1.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/librt-0.16.0.dist-info/WHEEL:Root-Is-Purelib: false
<sp>/librt-0.16.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux_2_17_x86_64
<sp>/librt-0.16.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux2014_x86_64
<sp>/librt-0.16.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux_2_28_x86_64
<sp>/mypy-2.4.0.dist-info/WHEEL:Root-Is-Purelib: false
<sp>/mypy-2.4.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux_2_17_x86_64
<sp>/mypy-2.4.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux2014_x86_64
<sp>/mypy-2.4.0.dist-info/WHEEL:Tag: cp315-cp315-manylinux_2_28_x86_64
<sp>/typing_extensions-4.16.0.dist-info/WHEEL:Root-Is-Purelib: true
<sp>/typing_extensions-4.16.0.dist-info/WHEEL:Tag: py3-none-any
<sp>/ast_serialize-0.13.1.dist-info/WHEEL:Root-Is-Purelib: false
<sp>/ast_serialize-0.13.1.dist-info/WHEEL:Tag: cp315-abi3-manylinux_2_17_x86_64
<sp>/ast_serialize-0.13.1.dist-info/WHEEL:Tag: cp315-abi3-manylinux2014_x86_64
<sp>/ast_serialize-0.13.1.dist-info/WHEEL:Tag: cp315-abi3t-manylinux_2_17_x86_64
<sp>/ast_serialize-0.13.1.dist-info/WHEEL:Tag: cp315-abi3t-manylinux2014_x86_64
```

V7 `grep -H -E "^(Name|Version|License|Classifier: License)" <sp>/*.dist-info/METADATA` (exit 0)

```text
<sp>/librt-0.16.0.dist-info/METADATA:Name: librt
<sp>/librt-0.16.0.dist-info/METADATA:Version: 0.16.0
<sp>/librt-0.16.0.dist-info/METADATA:License-Expression: MIT
<sp>/librt-0.16.0.dist-info/METADATA:License-File: LICENSE
<sp>/mypy-2.4.0.dist-info/METADATA:Name: mypy
<sp>/mypy-2.4.0.dist-info/METADATA:Version: 2.4.0
<sp>/mypy-2.4.0.dist-info/METADATA:License-Expression: MIT
<sp>/mypy-2.4.0.dist-info/METADATA:License-File: LICENSE
<sp>/mypy-2.4.0.dist-info/METADATA:License-File: mypy/typeshed/LICENSE
<sp>/mypy_extensions-1.1.0.dist-info/METADATA:Name: mypy_extensions
<sp>/mypy_extensions-1.1.0.dist-info/METADATA:Version: 1.1.0
<sp>/mypy_extensions-1.1.0.dist-info/METADATA:License-Expression: MIT
<sp>/mypy_extensions-1.1.0.dist-info/METADATA:License-File: LICENSE
<sp>/ast_serialize-0.13.1.dist-info/METADATA:Name: ast_serialize
<sp>/ast_serialize-0.13.1.dist-info/METADATA:Version: 0.13.1
<sp>/ast_serialize-0.13.1.dist-info/METADATA:License-File: LICENSE
<sp>/ast_serialize-0.13.1.dist-info/METADATA:License-File: crates/LICENSE
<sp>/ast_serialize-0.13.1.dist-info/METADATA:License-Expression: MIT
<sp>/pathspec-1.1.1.dist-info/METADATA:Name: pathspec
<sp>/pathspec-1.1.1.dist-info/METADATA:Version: 1.1.1
<sp>/pathspec-1.1.1.dist-info/METADATA:Classifier: License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)
<sp>/pathspec-1.1.1.dist-info/METADATA:License-File: LICENSE
<sp>/pathspec-1.1.1.dist-info/METADATA:License
<sp>/typing_extensions-4.16.0.dist-info/METADATA:Name: typing_extensions
<sp>/typing_extensions-4.16.0.dist-info/METADATA:Version: 4.16.0
<sp>/typing_extensions-4.16.0.dist-info/METADATA:License-Expression: PSF-2.0
<sp>/typing_extensions-4.16.0.dist-info/METADATA:License-File: LICENSE
```

The bare `License` line in pathspec's METADATA is a heading in its long description (line 180, followed by "*pathspec* is licensed under the `Mozilla Public License Version 2.0`").

V7, license files. Each command is `grep -n -m 1 -i -E "mit license|permission is hereby granted|apache license|bsd|isc license|mozilla public license" <file>` unless shown otherwise. Copyright lines are not reproduced.

`<sp>/pathspec-1.1.1.dist-info/licenses/LICENSE` (exit 0)

```text
1:Mozilla Public License Version 2.0
```

`<sp>/mypy_extensions-1.1.0.dist-info/licenses/LICENSE` (exit 0)

```text
1:Mypy extensions are licensed under the terms of the MIT license, reproduced below.
```

`grep -n -i -E "<same pattern>" <sp>/mypy-2.4.0.dist-info/licenses/mypy/typeshed/LICENSE` (no `-m 1`; exit 0)

```text
1:The "typeshed" project is licensed under the terms of the Apache license, as
6:Apache License
183:   APPENDIX: How to apply the Apache License to your work.
185:      To apply the Apache License to your work, attach the following
196:   Licensed under the Apache License, Version 2.0 (the "License");
215:The MIT License
219:Permission is hereby granted, free of charge, to any person obtaining a
```

`<sp>/ast_serialize-0.13.1.dist-info/licenses/crates/LICENSE`, three counts (each exit 0, except the last, which exits 1 at count 0):

```text
$ grep -c -E "^- .*licensed (as follows|under)" <file>
16
$ grep -c "Permission is hereby granted" <file>
17
$ grep -c -i -E "apache|bsd|isc license|mozilla|gnu|gpl" <file>
0
```

The 17 MIT grants are the top-level grant plus one for each of the 16 derived libraries.

V8 `<scratch>/mypy-adr/venv/bin/mypy --version` (exit 0)

```text
mypy 2.4.0 (compiled: yes)
```

V9 `<scratch>/mypy-adr/venv/bin/mypy --cache-dir <scratch>/mypy-adr/cache --strict --python-version 3.15 -c "def add(a: int, b: int) -> int: return a + b"` (exit 0)

```text
Success: no issues found in 1 source file
```

V10 `<scratch>/mypy-adr/probe-config.toml` holds the three D-06 lines (`[tool.mypy]`, `strict = true`, `python_version = "3.15"`). Command: `<scratch>/mypy-adr/venv/bin/mypy --config-file <scratch>/mypy-adr/probe-config.toml --cache-dir <scratch>/mypy-adr/cache -c "def add(a: int, b: int) -> int: return a + b"` (exit 0)

```text
Success: no issues found in 1 source file
```

V11 `<scratch>/mypy-adr/venv/bin/mypy --config-file <scratch>/mypy-adr/probe-config.toml --cache-dir <scratch>/mypy-adr/cache -c "def add(a, b): return a + b"` (exit 1)

```text
<string>:1: error: Function is missing a type annotation  [no-untyped-def]
Found 1 error in 1 file (checked 1 source file)
```

V12 `<scratch>/mypy-adr/venv/bin/mypy --config-file <scratch>/mypy-adr/probe-config.toml --cache-dir <scratch>/mypy-adr/cache --python-executable <worktree>/.venv/bin/python <worktree>/packages/prose/src/coh_prose` (exit 0)

```text
Success: no issues found in 3 source files
```

V13 `grep -n -A1 -E '^name = "(ast-serialize|librt|mypy|mypy-extensions|pathspec|typing-extensions)"' <worktree>/uv.lock` (exit 0)

```text
1038:name = "typing-extensions"
1039-version = "4.16.0"
```
