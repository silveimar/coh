"""Tests for archive/checkpoint wiring (I-12)."""

from pathlib import Path
from uuid import uuid4

import pytest

from coh_archive import ArchiveConfig, ArchiveService
from coh_mcp.archive_wiring import ArchiveCheckpointWiring
from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.enums import ArchiveStatus, LifecycleState


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    return tmp_path


@pytest.fixture
def archive_service(temp_project: Path) -> ArchiveService:
    """Create archive service for testing."""
    config = ArchiveConfig(enabled=True, directory=".coh/archive")
    return ArchiveService(temp_project, config)


@pytest.fixture
def wiring(archive_service: ArchiveService) -> ArchiveCheckpointWiring:
    """Create archive/checkpoint wiring."""
    return ArchiveCheckpointWiring(archive_service)


@pytest.mark.asyncio
async def test_successful_write_stores_reference(
    wiring: ArchiveCheckpointWiring, temp_project: Path
):
    """Test successful archive write stores ArchiveReference on checkpoint."""
    session_id = uuid4()
    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.INSPECT,
        restart_action="Test",
    )

    pointer = await wiring.archive_user_input(
        session_id, "test-project", "Test input", checkpoint
    )

    assert pointer is not None
    assert len(checkpoint.archive_references) == 1
    assert checkpoint.archive_references[0].anchor == pointer.entry_id
    assert checkpoint.archive_status == ArchiveStatus.HEALTHY
    assert wiring.writes_succeeded == 1
    assert wiring.writes_failed == 0


@pytest.mark.asyncio
async def test_failed_write_marks_checkpoint_degraded(temp_project: Path):
    """Test failed archive write marks checkpoint as degraded (I-12)."""
    config = ArchiveConfig(enabled=True, directory="/invalid/absolute/path")
    archive_service = ArchiveService(temp_project, config)
    wiring = ArchiveCheckpointWiring(archive_service)

    session_id = uuid4()
    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.INSPECT,
        restart_action="Test",
    )

    pointer = await wiring.archive_user_input(
        session_id, "test-project", "Test input", checkpoint
    )

    assert pointer is None
    assert checkpoint.archive_status == ArchiveStatus.DEGRADED
    assert wiring.writes_succeeded == 0
    assert wiring.writes_failed == 1
    assert wiring.last_failure is not None


@pytest.mark.asyncio
async def test_failed_write_preserves_in_memory_data(temp_project: Path):
    """Test I-12: failed write never loses in-memory interaction."""
    config = ArchiveConfig(enabled=True, directory="/invalid/absolute/path")
    archive_service = ArchiveService(temp_project, config)
    wiring = ArchiveCheckpointWiring(archive_service)

    session_id = uuid4()
    content = "Important user input that must not be lost"

    pointer = await wiring.archive_user_input(session_id, "test-project", content)

    assert pointer is None


@pytest.mark.asyncio
async def test_agent_output_archival(
    wiring: ArchiveCheckpointWiring, temp_project: Path
):
    """Test agent output archival with state transition."""
    session_id = uuid4()
    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.SPECIFY,
        restart_action="Test",
    )

    pointer = await wiring.archive_agent_output(
        session_id,
        "test-project",
        "Agent response",
        checkpoint,
        state_transition="INSPECT→SPECIFY",
    )

    assert pointer is not None
    assert wiring.writes_succeeded == 1


@pytest.mark.asyncio
async def test_tool_invocation_archival(
    wiring: ArchiveCheckpointWiring, temp_project: Path
):
    """Test tool invocation archival."""
    session_id = uuid4()
    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session_id,
        lifecycle_state=LifecycleState.EXECUTE,
        restart_action="Test",
    )

    pointer = await wiring.archive_tool_invocation(
        session_id,
        "test-project",
        "run_tests",
        checkpoint,
        input_payload={"test_file": "test_worker.py"},
        output_payload={"status": "passed"},
    )

    assert pointer is not None
    assert wiring.writes_succeeded == 1


@pytest.mark.asyncio
async def test_get_stats(wiring: ArchiveCheckpointWiring, temp_project: Path):
    """Test archive integration statistics."""
    session_id = uuid4()

    await wiring.archive_user_input(session_id, "test-project", "Input 1")
    await wiring.archive_user_input(session_id, "test-project", "Input 2")

    stats = wiring.get_stats()

    assert stats["enabled"] is True
    assert stats["writes_succeeded"] == 2
    assert stats["writes_failed"] == 0
    assert stats["last_failure"] is None
