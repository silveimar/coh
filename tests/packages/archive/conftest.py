"""Shared test fixtures."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from coh_archive import ArchiveConfig


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create temporary project root."""
    return tmp_path


@pytest.fixture
def archive_config() -> ArchiveConfig:
    """Default archive configuration."""
    return ArchiveConfig(enabled=True, directory=".coh/archive")


@pytest.fixture
def session_id():
    """Generate test session ID."""
    return uuid4()


@pytest.fixture
def project_id() -> str:
    """Test project ID."""
    return "test-project"


@pytest.fixture
def timestamp() -> datetime:
    """Fixed timestamp for tests."""
    return datetime(2026, 8, 19, 12, 34, 56, 789000, tzinfo=UTC)
