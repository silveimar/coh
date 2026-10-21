# Requirements: COH (Cognitive Operating Harness)

**Defined:** 2026-10-21
**Core Value:** The Execution Core stays deterministic and authoritative: AI output is proposal-only, and domain policy validates it before any state changes.
**Mission:** chores-q4 (chore, test and docs phases only)

## v1 Requirements

### Typing

- [ ] **TYPE-01**: `uv run pyright packages/archive` reports 0 errors (baseline 5 at d2b31b7)
- [ ] **TYPE-02**: `uv run pyright packages/execution-core` reports 0 errors (baseline 18 at d2b31b7), with stored datetime values unchanged
- [ ] **TYPE-03**: One module passes `mypy --strict`, and CI runs that check on every PR

### Supply chain

- [ ] **SUPP-01**: CI runs deptry and pip-audit on every PR, and a finding fails the job

### Docs

- [ ] **DOCS-01**: `README.md`, package READMEs and the structure section of `docs/coding-rules.md` describe only paths and components that exist, and mark planned ones as planned

### Coverage

- [ ] **COV-01**: CI fails the prose test step when `packages/prose` statement coverage drops below the recorded floor

## v2 Requirements

- **TYPE-04**: Pyright 0 errors for `packages/persistence`, `packages/application`, `apps/api`, `packages/mcp_adapter`
- **TYPE-05**: Pyright runs in CI as a required check
- **COV-02**: Coverage floors for archive, application, persistence, mcp_adapter and api
- **SUPP-02**: Trivy scan and pre-commit hooks

## Out of Scope

| Feature | Reason |
|---------|--------|
| MCP adapter refactor to application services | Cross-module refactor; needs an ADR, not a chore |
| Pyright errors under `tests/` | Protected check set; editing existing test lines is Ask |
| Switching domain datetimes to timezone-aware | Changes stored and wire values; needs a decision-log entry |
| Re-enabling the four disabled pyright strict rules | Larger blast radius; revisit after the per-package phases |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TYPE-01 | Phase 1 | Pending |
| TYPE-02 | Phase 2 | Pending |
| SUPP-01 | Phase 3 | Pending |
| TYPE-03 | Phase 4 | Pending |
| DOCS-01 | Phase 5 | Pending |
| COV-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-21*
*Last updated: 2026-10-21 after initial definition*
