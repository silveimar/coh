"""Test crash/restart recovery with real domain models."""

from uuid import uuid4

from persistence.infrastructure.database import init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from execution_core.domain.checkpoint import Checkpoint
from execution_core.domain.enums import (
    ArchiveStatus,
    Clarity,
    LifecycleState,
    Readiness,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification


def test_crash_restart_recovery(temp_db: str) -> None:
    """Test full crash/restart cycle with spec_snapshot persistence.

    This proves:
    1. Session + spec + checkpoint can be persisted
    2. After simulated crash (new engine), data can be loaded
    3. Spec body can be restored from checkpoint's spec_snapshot
    """
    # Create initial session with spec
    session = ExecutionSession(
        id=uuid4(),
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.INSPECT,
    )

    spec = Specification(
        id=uuid4(),
        what="Build persistence layer",
        why="To survive process restarts",
        deliverable="Working SQLAlchemy + Alembic integration",
        done_when=[
            DoneWhenCriterion(text="All repository tests pass"),
            DoneWhenCriterion(text="Crash/restart test passes"),
        ],
        clarity=Clarity.HIGH,
        readiness=Readiness.READY,
    )
    spec.update_computed_fields()

    # Link spec to session
    session.current_spec = spec

    # Create checkpoint with spec snapshot
    checkpoint = Checkpoint(
        id=uuid4(),
        session_id=session.id,
        lifecycle_state=session.lifecycle_state,
        spec_snapshot=spec,
        spec_id=spec.id,
        spec_revision=spec.revision,
        restart_action="Resume persistence layer implementation",
        archive_status=ArchiveStatus.HEALTHY,
    )

    # Persist everything (first engine/session)
    engine1 = create_engine(temp_db, connect_args={"check_same_thread": False})
    init_db(engine1)
    session_factory1 = sessionmaker(bind=engine1, autoflush=False, autocommit=False)

    # Persist spec first (no dependencies)
    with SqlAlchemyUnitOfWork(session_factory1) as uow:
        uow.specifications.add(spec)
        uow.commit()

    # Then persist session (depends on spec)
    with SqlAlchemyUnitOfWork(session_factory1) as uow:
        uow.sessions.add(session)
        uow.commit()

    # Finally persist checkpoint (depends on session)
    with SqlAlchemyUnitOfWork(session_factory1) as uow:
        uow.checkpoints.add(checkpoint)
        uow.commit()

    engine1.dispose()

    # Simulate crash: new engine, new session factory
    engine2 = create_engine(temp_db, connect_args={"check_same_thread": False})
    session_factory2 = sessionmaker(bind=engine2, autoflush=False, autocommit=False)

    # Recover from checkpoint
    with SqlAlchemyUnitOfWork(session_factory2) as uow:
        loaded_checkpoint = uow.checkpoints.get(checkpoint.id)
        assert loaded_checkpoint is not None
        assert (
            loaded_checkpoint.restart_action
            == "Resume persistence layer implementation"
        )

        # Verify spec snapshot was persisted correctly
        assert loaded_checkpoint.spec_snapshot is not None
        assert loaded_checkpoint.spec_snapshot.what == "Build persistence layer"
        assert loaded_checkpoint.spec_snapshot.why == "To survive process restarts"
        assert len(loaded_checkpoint.spec_snapshot.done_when) == 2
        assert (
            loaded_checkpoint.spec_snapshot.done_when[0].text
            == "All repository tests pass"
        )

        # Verify we can load the original session
        loaded_session = uow.sessions.get(session.id)
        assert loaded_session is not None
        assert loaded_session.project_id == "test-project"

    engine2.dispose()
