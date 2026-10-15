# COH (Cognitive Operating Harness)

**Status:** Phase 0 complete, execution-core implementation in progress

COH (Cognitive Operating Harness) is a local-first execution layer that helps solo AI-assisted developers turn intention into completed action. It converts ambiguous requests into confirmed specifications, keeps exactly one NOW task and at most two NEXT tasks in the foreground, preserves decisions and evidence, and provides reliable recovery after interruptions.

## Project Structure

```
.
├── packages/
│   └── execution-core/        # Deterministic domain model and lifecycle
├── docs/                      # Phase 0 documentation
│   ├── behavioral-contract.md  # State machine, invariants I-01...I-14, T1...T11
│   ├── decision-log.md        # Durable product decisions D1...D11
│   ├── coding-rules.md        # Engineering standards
│   └── feature-specs/         # Feature specifications
└── tests/                     # All tests: packages/, apps/ and evals/ (behavioral scenarios)
```

## Core Principles

- **Capability ≠ execution:** Being able to do something is not the same as executing it
- **Deterministic core:** AI output is proposal-only; domain policies validate before state changes
- **Local-first:** Project-local canonical state, no cloud dependency
- **Append-only archive:** All interactions preserved, corrections are new entries
- **Evidence-backed completion:** Work is never "done" without criterion-linked evidence

## Getting Started

### Prerequisites

- Python 3.15+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup (installs every package plus the dev tools:
# ruff, pyright, pytest and plugins, hypothesis, httpx)
git clone <repository-url>
cd coh
uv sync --all-packages
```

### Running Tests

All tests live under `tests/`. The pytest settings are in `pytest.ini` and the
coverage settings in `.coveragerc`.

```bash
# Run every test, including the eval harness
uv run pytest

# Run each package's tests
uv run pytest tests/packages/execution-core
uv run pytest tests/packages/persistence
uv run pytest tests/packages/archive
uv run pytest tests/packages/prose
uv run pytest tests/packages/mcp_adapter
uv run pytest tests/packages/application
uv run pytest tests/apps/api

# Run the behavioral eval harness
uv run pytest tests/evals

# Run with coverage
uv run pytest tests/packages/execution-core --cov=packages/execution-core/src

# Run linting (the same commands CI runs)
uv run ruff check .
uv run ruff format --check .
```

## Packages

### execution-core

See [packages/execution-core/README.md](packages/execution-core/README.md) for details on the deterministic domain model and lifecycle implementation.

## Documentation

- [Behavioral Contract](docs/behavioral-contract.md) - State machine, invariants, transitions
- [Decision Log](docs/decision-log.md) - Product decisions D1-D11
- [Coding Rules](docs/coding-rules.md) - Engineering standards and conventions
- [Glossary](docs/glossary.md) - Canonical terminology

## License

[To be determined]
