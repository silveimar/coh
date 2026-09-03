"""Path resolution and validation tests."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from coh_archive import Actor, ArchiveConfig
from coh_archive.paths import (
    PathResolutionError,
    generate_artifact_filename,
    generate_entry_id,
    generate_session_filename,
    resolve_archive_directory,
)


def test_resolve_default_archive_directory(project_root: Path):
    """Default archive directory resolves to .coh/archive under project root."""
    config = ArchiveConfig(directory=".coh/archive")
    resolved = resolve_archive_directory(project_root, config)

    assert resolved == project_root / ".coh" / "archive"


def test_resolve_custom_relative_directory(project_root: Path):
    """Custom relative directory resolves under project root."""
    config = ArchiveConfig(directory="custom/archive")
    resolved = resolve_archive_directory(project_root, config)

    assert resolved == project_root / "custom" / "archive"


def test_reject_external_path_without_flag(project_root: Path):
    """External absolute path rejected when allow_external_path is false."""
    external_path = Path("/tmp/external-archive")
    config = ArchiveConfig(
        directory=str(external_path), allow_external_path=False
    )

    with pytest.raises(PathResolutionError, match="outside project root"):
        resolve_archive_directory(project_root, config)


def test_allow_external_path_with_flag(project_root: Path):
    """External absolute path allowed when allow_external_path is true."""
    external_path = Path("/tmp/external-archive")
    config = ArchiveConfig(
        directory=str(external_path), allow_external_path=True
    )

    resolved = resolve_archive_directory(project_root, config)
    assert resolved == external_path


def test_reject_traversal_attack(project_root: Path):
    """Path traversal attempts are rejected."""
    config = ArchiveConfig(directory="../../../etc/passwd")

    with pytest.raises(PathResolutionError, match="outside project root"):
        resolve_archive_directory(project_root, config)


def test_generate_session_filename():
    """Session filename format is correct."""
    session_id = uuid4()
    timestamp = datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC)

    filename = generate_session_filename(session_id, timestamp)

    assert filename.startswith("2026-08-19-")
    assert filename.endswith(".md")
    assert str(session_id)[:8] in filename


def test_generate_session_filename_with_rotation():
    """Session filename with rotation part is correct."""
    session_id = uuid4()
    timestamp = datetime(2026, 8, 19, 12, 34, 56, tzinfo=UTC)

    filename = generate_session_filename(session_id, timestamp, part=3)

    assert filename.startswith("2026-08-19-")
    assert "-part-3.md" in filename


def test_generate_entry_id_format():
    """Entry ID format matches {actor}-{ISO8601}-{4char-hash}."""
    timestamp = datetime(2026, 8, 19, 12, 34, 56, 789000, tzinfo=UTC)
    content = "Test content for hashing"

    entry_id = generate_entry_id(Actor.USER, timestamp, content)

    assert entry_id.startswith("user-2026-08-19T12:34:56.789000+00:00-")
    parts = entry_id.split("-")
    hash_part = parts[-1]
    assert len(hash_part) == 4


def test_generate_entry_id_stable():
    """Entry ID is stable for same inputs."""
    timestamp = datetime(2026, 8, 19, 12, 34, 56, 789000, tzinfo=UTC)
    content = "Stable content"

    id1 = generate_entry_id(Actor.AGENT, timestamp, content)
    id2 = generate_entry_id(Actor.AGENT, timestamp, content)

    assert id1 == id2


def test_generate_artifact_filename():
    """Artifact filename format is correct."""
    entry_id = "user-2026-08-19T12:34:56.789000+00:00-abcd"

    filename = generate_artifact_filename(entry_id, "input", "json")

    assert filename == "user-2026-08-19T12:34:56.789000+00:00-abcd-input.json"


def test_empty_directory_uses_default(project_root: Path):
    """Empty directory string uses default path."""
    config = ArchiveConfig(directory="")
    resolved = resolve_archive_directory(project_root, config)

    assert resolved == project_root / ".coh" / "archive"
