"""Pytest fixtures and configuration for eval harness."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_root():
    """Temporary project root for isolated test execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".coh").mkdir(parents=True, exist_ok=True)
        (root / ".coh" / "archive").mkdir(parents=True, exist_ok=True)
        yield root


@pytest.fixture
def eval_results_dir():
    """Directory for eval run results (gitignored)."""
    results = Path(__file__).parent.parent / "results"
    results.mkdir(parents=True, exist_ok=True)
    return results
