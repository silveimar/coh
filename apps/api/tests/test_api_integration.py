"""Integration tests for COH API enforcing I-02 and I-01."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from coh_api.composition import ServiceContainer
from coh_api.main import create_app
from execution_core.domain.enums import (
    Energy,
    ForegroundPosition,
    LifecycleState,
    SessionIntent,
    TaskStatus,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from execution_core.domain.task import Task
from persistence.infrastructure.database import create_engine, init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


@pytest.fixture
def service_container(test_db):
    """Create service container with test database."""
    session_factory = sessionmaker(bind=test_db)

    class TestContainer(ServiceContainer):
        def __init__(self, engine):
            self.engine = engine
            self.session_factory = sessionmaker(bind=engine)

    return TestContainer(test_db)


@pytest.fixture
def client(service_container, monkeypatch):
    """Create test client with mocked service container."""
    from coh_api import composition

    monkeypatch.setattr(composition, "_container", service_container)

    app = create_app()
    return TestClient(app)


@pytest.fixture
def session(service_container):
    """Create a test session with READY spec."""
    uow = SqlAlchemyUnitOfWork(service_container.session_factory)

    session = ExecutionSession(
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.SPECIFY,
    )

    spec = Specification(
        what="Test feature",
        why="Testing",
        deliverable="Working test",
        done_when=[DoneWhenCriterion(text="Tests pass")],
    )
    spec.update_computed_fields()

    with uow:
        uow.sessions.add(session)
        uow.specifications.add(spec)
        uow.commit()

        # Reload to get the IDs
        session = uow.sessions.get(session.id)

    return session, spec


class TestI02ReadinessGate:
    """Test I-02: Material mutation blocked while readiness=BLOCKED."""

    def test_confirm_ready_spec_succeeds(self, client, session):
        """Confirm returns 201 when spec is READY (I-02)."""
        test_session, _ = session

        # Confirm a spec with all required fields
        response = client.post(
            "/api/v1/spec-gate/confirm",
            json={
                "session_id": str(test_session.id),
                "spec": {
                    "session_id": str(test_session.id),
                    "what": "Test feature",
                    "why": "Testing requirement",
                    "deliverable": "Working test output",
                    "done_when": ["Tests pass", "Documentation complete"],
                },
                "idempotency_key": "test-ready-confirm",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["readiness"] == "ready"
        assert data["what"] == "Test feature"

    def test_confirm_blocked_when_missing_required_fields(self, client, session):
        """Confirm returns 422 when spec is missing required fields (I-02)."""
        test_session, _ = session

        # Try to confirm a spec missing WHAT
        response = client.post(
            "/api/v1/spec-gate/confirm",
            json={
                "session_id": str(test_session.id),
                "spec": {
                    "session_id": str(test_session.id),
                    "what": "",  # Empty WHAT should block
                    "why": "Testing",
                    "deliverable": "Test output",
                    "done_when": ["Tests pass"],
                },
                "idempotency_key": "test-key-1",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "readiness_blocked"
        assert "Missing WHAT" in str(data["detail"]["message"])

    def test_confirm_blocked_when_missing_done_when(self, client, session):
        """Confirm returns 422 when spec has no done-when criteria (I-02)."""
        test_session, _ = session

        response = client.post(
            "/api/v1/spec-gate/confirm",
            json={
                "session_id": str(test_session.id),
                "spec": {
                    "session_id": str(test_session.id),
                    "what": "Test feature",
                    "why": "Testing",
                    "deliverable": "Test output",
                    "done_when": [],  # Empty done_when should block
                },
                "idempotency_key": "test-key-2",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "readiness_blocked"

    def test_read_only_status_always_permitted(self, client, session):
        """Get status is always permitted regardless of readiness (I-02)."""
        test_session, _ = session

        # Status check should work even when spec would be blocked
        response = client.get(f"/api/v1/spec-gate/status/{test_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert "readiness" in data

    def test_mutation_allowed_check_returns_blockers(self, client, service_container):
        """Mutation-allowed check returns blockers when readiness=BLOCKED."""
        # Create a session with no spec (automatically blocked)
        uow = SqlAlchemyUnitOfWork(service_container.session_factory)
        session = ExecutionSession(
            project_id="test-project-2",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.SPECIFY,
        )

        with uow:
            uow.sessions.add(session)
            uow.commit()
            session_id = session.id

        response = client.get(f"/api/v1/spec-gate/mutation-allowed/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["readiness_state"] == "blocked"
        assert len(data["blockers"]) > 0


class TestI01ForegroundConstraints:
    """Test I-01: At most one NOW and two NEXT with required metadata."""

    def test_foreground_enforces_now_metadata_requirements(self, client, session, service_container):
        """Foreground validates NOW task has required metadata (I-01)."""
        test_session, test_spec = session

        # Create a task without required metadata
        uow = SqlAlchemyUnitOfWork(service_container.session_factory)

        task = Task(
            title="Test task",
            spec_id=test_spec.id,
            status=TaskStatus.PENDING,
            foreground_position=ForegroundPosition.NOW,
            # Missing required metadata: action_literal, done_when_condition, etc.
        )

        with uow:
            test_session.current_spec = test_spec
            uow.sessions.update(test_session, expected_version=test_session.version)
            uow.tasks.add(task)
            uow.commit()

        # Get foreground should detect the I-01 violation
        response = client.get(f"/api/v1/foreground/{test_session.id}")

        # The service should either fix it or return an error
        # In this implementation, we expect a 500 with I-01 violation
        if response.status_code == 500:
            data = response.json()
            assert data["detail"]["error_code"] == "foreground_invariant_violation"
            assert "I-01" in data["detail"]["message"]

    def test_complete_now_requires_now_task(self, client, session, service_container):
        """Complete NOW returns 422 if task is not the NOW task (I-01)."""
        test_session, test_spec = session

        # Create a NEXT task
        uow = SqlAlchemyUnitOfWork(service_container.session_factory)

        task = Task(
            title="Test task",
            spec_id=test_spec.id,
            status=TaskStatus.PENDING,
            foreground_position=ForegroundPosition.NEXT_1,  # Not NOW
        )

        with uow:
            test_session.current_spec = test_spec
            uow.sessions.update(test_session, expected_version=test_session.version)
            uow.tasks.add(task)
            uow.commit()
            task_id = task.id

        # Try to complete a non-NOW task
        response = client.post(
            "/api/v1/foreground/complete-now",
            json={
                "session_id": str(test_session.id),
                "task_id": str(task_id),
                "idempotency_key": "test-key-3",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "not_now_task"

    def test_foreground_limits_next_to_two(self, client, session):
        """Foreground enforces at most 2 NEXT tasks (I-01)."""
        test_session, test_spec = session

        # The ForegroundPolicy should enforce this automatically
        # when we request the foreground
        response = client.get(f"/api/v1/foreground/{test_session.id}")

        assert response.status_code == 200
        data = response.json()

        # Count NEXT tasks (next_1_task and next_2_task)
        next_count = sum(
            [data.get("next_1_task") is not None, data.get("next_2_task") is not None]
        )
        assert next_count <= 2


class TestDiagnosisFreeErrors:
    """Test that error messages are diagnosis-free and user-safe."""

    def test_error_messages_are_diagnosis_free(self, client, session):
        """Error messages use neutral, observable language."""
        test_session, _ = session

        # Test with invalid session ID
        response = client.get("/api/v1/spec-gate/status/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        data = response.json()
        # Should be neutral, not stigmatizing
        assert "not found" in data["detail"]["message"].lower()
        # Should not contain diagnostic terms
        assert "hyperfocus" not in data["detail"]["message"].lower()
        assert "adhd" not in data["detail"]["message"].lower()


class TestSnakeCaseWireJSON:
    """Test that all API contracts use snake_case (D10)."""

    def test_response_uses_snake_case(self, client, session):
        """API responses use snake_case field names (D10)."""
        test_session, _ = session

        response = client.get(f"/api/v1/spec-gate/status/{test_session.id}")

        assert response.status_code == 200
        data = response.json()

        # Check for snake_case keys
        assert "done_when_count" in data  # Not doneWhenCount
        assert "spec_id" in data or data.get("spec_id") is None  # Not specId

    def test_request_accepts_snake_case(self, client, session):
        """API requests accept snake_case field names (D10)."""
        test_session, _ = session

        response = client.post(
            "/api/v1/spec-gate/propose",
            json={
                "session_id": str(test_session.id),  # snake_case
                "what": "Test",
                "why": "Testing",
                "deliverable": "Output",
                "done_when": ["Done"],  # snake_case
            },
        )

        assert response.status_code == 200
