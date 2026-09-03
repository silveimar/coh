"""Archive path resolution and validation."""

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import UUID

from .models import Actor, ArchiveConfig


class PathResolutionError(Exception):
    """Archive path resolution or validation failed."""

    pass


def resolve_archive_directory(project_root: Path, config: ArchiveConfig) -> Path:
    """
    Resolve and validate the archive directory.

    Args:
        project_root: Project root directory
        config: Archive configuration

    Returns:
        Resolved archive directory path

    Raises:
        PathResolutionError: If path is invalid or outside project root
    """
    if not config.directory or not config.directory.strip():
        archive_dir = project_root / ".coh" / "archive"
    else:
        archive_dir = Path(config.directory)
        if not archive_dir.is_absolute():
            archive_dir = project_root / archive_dir

    try:
        archive_dir = archive_dir.resolve()
        project_root_resolved = project_root.resolve()
    except (OSError, RuntimeError) as e:
        raise PathResolutionError(f"Failed to resolve archive path: {e}") from e

    if not config.allow_external_path:
        try:
            archive_dir.relative_to(project_root_resolved)
        except ValueError as e:
            raise PathResolutionError(
                f"Archive path {archive_dir} is outside project root "
                f"{project_root_resolved}. Set allow_external_path=true to override."
            ) from e

    return archive_dir


def generate_session_filename(
    session_id: UUID, timestamp: datetime, part: int | None = None
) -> str:
    """
    Generate session archive filename.

    Format: YYYY-MM-DD-<session_id_short>.md
    Or with rotation: YYYY-MM-DD-<session_id_short>-part-N.md

    Args:
        session_id: Session UUID
        timestamp: Session timestamp
        part: Optional rotation part number (1-based)

    Returns:
        Archive filename
    """
    date_str = timestamp.strftime("%Y-%m-%d")
    session_short = str(session_id)[:8]

    if part is None:
        return f"{date_str}-{session_short}.md"
    return f"{date_str}-{session_short}-part-{part}.md"


def generate_entry_id(
    actor: Actor, timestamp: datetime, content_hash_input: str
) -> str:
    """
    Generate stable entry ID for markdown anchors.

    Format: {actor}-{ISO8601}-{4char-hash}

    Args:
        actor: Event actor
        timestamp: Event timestamp
        content_hash_input: Input for hash generation (typically content)

    Returns:
        Entry ID suitable as markdown anchor
    """
    iso_time = timestamp.isoformat()
    content_bytes = content_hash_input.encode("utf-8")
    hash_digest = hashlib.sha256(content_bytes).hexdigest()[:4]

    return f"{actor.value}-{iso_time}-{hash_digest}"


def generate_artifact_filename(
    entry_id: str, payload_type: str, extension: str = "json"
) -> str:
    """
    Generate artifact filename for large payloads.

    Format: {entry_id}-{payload_type}.{extension}

    Args:
        entry_id: Entry ID from generate_entry_id
        payload_type: Type indicator (e.g., 'input', 'output')
        extension: File extension (default: json)

    Returns:
        Artifact filename
    """
    return f"{entry_id}-{payload_type}.{extension}"
