# ADR-0001: Put dev tools in a root uv dependency group

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** proposed by lead/owner draft; owner approval required for Accepted
- **Slice / PR:** foundation / slice 01 (dev tooling installs with `uv sync`)
- **Decision log:** none (tooling only, no execution-semantics change)

## Question

How should the repository declare its development tools (ruff, pyright, pytest and plugins, hypothesis, httpx) so that a plain `uv sync --all-packages` installs them, and CI and the README can use the same command?

## Context

Facts from `main` @ `8d32247` (checked 2026-10-09 in a clean copy):

- The tools are declared as per-package `[project.optional-dependencies] dev` extras in `packages/*/pyproject.toml` and `apps/api/pyproject.toml`.
- `uv sync --all-packages` does not install extras, so `uv run ruff`, `uv run pytest` and `uv run pyright` fail with "Failed to spawn". The README's `uv sync` then `uv run pytest` does not work as written.
- CI works around it with `uv pip install -e "packages/...[dev]" ...` after `uv sync` (`.github/workflows/ci.yml`).
- The extras are inconsistent: `persistence` has none; `application` and `apps/api` lack pyright; versions differ (`pytest>=8.3.0` vs `>=8.3.2`, `ruff>=0.6.0` vs `>=0.6.3`).
- `docs/coding-rules.md` makes `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` and `uv run pytest` the quality gates, from the repo root.
- Constraints: uv is the only Python package manager (coding rules); no new dependency without approval; the lockfile is committed.

## Options considered

### Option A: root `[dependency-groups] dev` (PEP 735)
- Declare the union of dev tools once in the root `pyproject.toml`. uv installs the `dev` group by default on `uv sync`.
- Pros: one place, one version per tool, `uv sync --all-packages` is enough; CI drops the `uv pip install -e` step; matches the README.
- Cons: dev tools are no longer declared per package, so installing one package alone from PyPI-style metadata does not offer a `dev` extra. Packages are not published, so this has no current cost.
- Cost to adopt and reverse: small; one `pyproject.toml` edit plus a lockfile update. Reverse by restoring the extras.
- Verified: adding the group in a clean copy made `uv sync --all-packages` install ruff 0.16.5, pyright 1.1.411 and pytest 9.1.1.

### Option B: keep the extras and use `uv sync --all-packages --all-extras`
- Pros: no `pyproject.toml` change.
- Cons: every developer, the README and CI must remember the flag; per-package drift stays; the extras remain inconsistent.
- Cost to adopt and reverse: none, but the problem stays.

### Option C: per-package dependency groups
- Pros: tools stay next to each package.
- Cons: `uv sync --all-packages` does not install member packages' groups by default, so the same flag problem returns; more places to keep in step.

### Option D: do nothing
- Cons: the documented commands keep failing from a fresh clone; CI keeps its workaround.

## Decision

**Selected:** Option A.

It is the only option where the documented commands work unchanged from a fresh clone, with one declaration per tool. The downside accepted: dev tools are no longer visible as per-package extras.

Constraints on the change:

- Use the highest minimum already declared for each tool (pytest `>=8.3.2`, ruff `>=0.6.3`, others as declared). No version bumps and no new tool.
- Remove a per-package `dev` extra only if nothing else references it; otherwise keep it and note why.
- `uv.lock` changes only as the move requires.

## Consequences

- **What changes:** root `pyproject.toml` (new group), `uv.lock`, CI install step, README "Getting Started" and "Running Tests", possibly the per-package extras.
- **What gets easier:** `uv sync --all-packages` gives a working environment; Pyright and the other gates can be run locally and added to CI later without another install step.
- **What gets harder:** nothing material.
- **Follow-up work:** each as its own slice or card: Pyright in CI, ruff over the whole repo, the root `pytest` conftest collision.
- **Rollback:** revert the PR; the extras and CI step come back with it.

## Compliance checklist

- [x] Stays inside the layer rules (no source changes)
- [x] New dependency: none; existing dev tools are moved, at their current minimum versions (licenses unchanged)
- [x] Schema change: not applicable
- [x] Public API, wire format or archive format: not applicable
- [x] No new infrastructure
- [x] Tests: the same suite passes before and after, with counts recorded in the PR
- [x] Decision-log entry: not needed (no semantics change)

## Reopen when

uv changes how dependency groups are resolved in workspaces, or a package is published separately and needs its own `dev` extra.

## References

- `.github/workflows/ci.yml`, `pyproject.toml`, `packages/*/pyproject.toml`, `apps/api/pyproject.toml`
- `docs/coding-rules.md` (quality gates)
- uv documentation on dependency groups and workspaces

## Amendment 2026-10-11: floors raised to the latest releases

- **Decision:** owner decision `qitem-20261011201048-7a1da1d2c6e1eebd`, applied in PR #12 (slice 01). It replaces the "highest minimum already declared, no version bumps" constraint above for these seven tools. The rest of the decision stands.
- **Why:** the owner chose to move the dev tools to their current releases in the same PR, so the declared floors match what is installed.
- **Floors in the root `[dependency-groups] dev`,** each equal to its locked version:

| Tool | Floor before (highest declared minimum) | Floor now | Locked before | Locked now |
|---|---|---|---|---|
| ruff | `>=0.6.3` | `>=0.17.0` | 0.16.5 | 0.17.0 |
| pyright | `>=1.1.380` | `>=1.1.414` | 1.1.411 | 1.1.414 |
| pytest | `>=8.3.2` | `>=9.1.1` | 9.1.1 | 9.1.1 |
| pytest-cov | `>=5.0.0` | `>=7.1.0` | 7.1.0 | 7.1.0 |
| pytest-asyncio | `>=0.24.0` | `>=1.4.0` | 1.4.0 | 1.4.0 |
| hypothesis | `>=6.112.0` | `>=6.169.0` | 6.167.1 | 6.169.0 |
| httpx | `>=0.27.0` | `>=0.28.1` | 0.28.1 | 0.28.1 |

- **Effect on `uv.lock`:** only ruff, pyright and hypothesis change version. No runtime or transitive dependency changes.
- **Verified:** ruff check and format, and every package's tests under Python 3.15.0, give the same counts as `main`. No code changes were needed.
