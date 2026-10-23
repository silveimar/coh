"""Integration tests for COH API enforcing I-02 and I-01."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from coh_api.composition import ServiceContainer
from coh_api.main import create_app
from execution_core.domain.enums import (
    LifecycleState,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from execution_core.domain.specification import DoneWhenCriterion, Specification
from persistence.infrastructure.database import create_engine, init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def test_db(tmp_path):
    """Create temp file test database."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    return engine


@pytest.fixture
def service_container(test_db):
    """Create service container with test database."""

    class TestContainer(ServiceContainer):
        def __init__(self, engine):
            self.engine = engine
            self.session_factory = sessionmaker(bind=engine)

    return TestContainer(test_db)


@pytest.fixture
def client(service_container, monkeypatch):
    """Create test client with mocked service container."""
    from coh_api import composition

    # Set container BEFORE creating app so lifespan doesn't overwrite
    monkeypatch.setattr(composition, "_container", service_container)

    app = create_app()
    return TestClient(app)


@pytest.fixture
def session_with_ready_spec(service_container):
    """Create a test session with READY spec."""
    uow = SqlAlchemyUnitOfWork(service_container.session_factory)

    session = ExecutionSession(
        project_id="test-project",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.CONFIRM,
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
        session.current_spec = spec
        uow.specifications.add(spec)
        uow.sessions.update(session, expected_version=session.version)
        uow.commit()

        # Reload to get fresh state
        session = uow.sessions.get(session.id)
        spec = uow.specifications.get(spec.id)

    return session, spec


@pytest.fixture
def session_with_blocked_spec(service_container):
    """Create a test session with BLOCKED spec (missing required fields)."""
    uow = SqlAlchemyUnitOfWork(service_container.session_factory)

    session = ExecutionSession(
        project_id="test-project-blocked",
        intent=SessionIntent.EXECUTE,
        lifecycle_state=LifecycleState.SPECIFY,
    )

    # Spec with empty what - will be BLOCKED
    spec = Specification(
        what="",  # Missing WHAT makes it blocked
        why="Testing",
        deliverable="Test output",
        done_when=[DoneWhenCriterion(text="Done")],
    )
    spec.update_computed_fields()

    with uow:
        uow.sessions.add(session)
        session.current_spec = spec
        uow.specifications.add(spec)
        uow.sessions.update(session, expected_version=session.version)
        uow.commit()

        session = uow.sessions.get(session.id)
        spec = uow.specifications.get(spec.id)

    return session, spec


class TestI02ReadinessGate:
    """Test I-02: Material mutation blocked while readiness=BLOCKED."""

    def test_confirm_ready_spec_succeeds(self, client, session_with_ready_spec):
        """Confirm returns 201 when spec is READY (I-02)."""
        test_session, _ = session_with_ready_spec

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

    def test_confirm_blocked_when_spec_is_blocked(
        self, client, session_with_blocked_spec
    ):
        """Confirm returns 422 when session's current spec is BLOCKED (I-02)."""
        test_session, _ = session_with_blocked_spec

        # Try to confirm - should check current spec readiness
        response = client.post(
            "/api/v1/spec-gate/confirm",
            json={
                "session_id": str(test_session.id),
                "spec": {
                    "session_id": str(test_session.id),
                    "what": "Valid spec",
                    "why": "Testing",
                    "deliverable": "Test output",
                    "done_when": ["Tests pass"],
                },
                "idempotency_key": "test-key-1",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error_code"] == "readiness_blocked"
        assert "Missing WHAT" in str(data["detail"])

    def test_revise_done_when_round_trips(self, client, session_with_ready_spec):
        """Revising done_when stores criteria and leaves the spec readable."""
        test_session, spec = session_with_ready_spec

        response = client.post(
            "/api/v1/spec-gate/revise",
            json={
                "session_id": str(test_session.id),
                "spec_id": str(spec.id),
                "updates": {
                    "what": "Revised feature",
                    "done_when": ["Criterion replaced"],
                },
                "idempotency_key": "revise-done-when",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["what"] == "Revised feature"
        assert data["done_when"] == ["Criterion replaced"]
        assert data["revision"] == 2

        status = client.get(f"/api/v1/spec-gate/status/{test_session.id}")
        assert status.status_code == 200
        body = status.json()
        assert body["spec_id"] == data["spec_id"]
        assert body["what"] == "Revised feature"
        assert body["done_when_count"] == 1

    def test_revise_rejects_unknown_field(self, client, session_with_ready_spec):
        """A field outside the revision allow-list does not replace the spec."""
        test_session, spec = session_with_ready_spec

        response = client.post(
            "/api/v1/spec-gate/revise",
            json={
                "session_id": str(test_session.id),
                "spec_id": str(spec.id),
                "updates": {"id": str(spec.id)},
                "idempotency_key": "revise-id",
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"]["error_code"] == "invalid_revision"

        status = client.get(f"/api/v1/spec-gate/status/{test_session.id}")
        assert status.status_code == 200
        body = status.json()
        assert body["spec_id"] == str(spec.id)
        assert body["revision"] == "1"

    def test_read_only_status_always_permitted(self, client, session_with_blocked_spec):
        """Get status is always permitted regardless of readiness (I-02)."""
        test_session, _ = session_with_blocked_spec

        # Status check should work even when spec is blocked
        response = client.get(f"/api/v1/spec-gate/status/{test_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["readiness"] == "blocked"
        assert len(data["blockers"]) > 0

    def test_mutation_allowed_check_returns_blockers(
        self, client, service_container, session_with_blocked_spec
    ):
        """Mutation-allowed check returns blockers when readiness=BLOCKED."""
        test_session, _ = session_with_blocked_spec

        response = client.get(f"/api/v1/spec-gate/mutation-allowed/{test_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["readiness_state"] == "blocked"
        assert len(data["blockers"]) > 0


class TestI01ForegroundConstraints:
    """Test I-01: At most one NOW and two NEXT with required metadata."""

    def test_foreground_returns_valid_shape(self, client, session_with_ready_spec):
        """Foreground returns valid I-01 shape: ≤1 NOW + ≤2 NEXT."""
        test_session, _ = session_with_ready_spec

        response = client.get(f"/api/v1/foreground/{test_session.id}")

        # GET operations should always succeed
        assert response.status_code == 200
        data = response.json()

        # Verify I-01 constraints
        assert "now_task" in data
        assert "next_1_task" in data
        assert "next_2_task" in data
        assert "parked_count" in data
        assert "background_count" in data

    def test_foreground_status_always_permitted(
        self, client, session_with_blocked_spec
    ):
        """Foreground status is always permitted (read-only)."""
        test_session, _ = session_with_blocked_spec

        response = client.get(f"/api/v1/foreground/status/{test_session.id}")

        # GET operations should always succeed
        assert response.status_code == 200
        data = response.json()
        assert "parked_count" in data


class TestDiagnosisFreeErrors:
    """Test that error messages are diagnosis-free and user-safe."""

    def test_error_messages_are_diagnosis_free(self, client):
        """Error messages use neutral, observable language."""
        # Test with invalid session ID
        response = client.get(
            "/api/v1/spec-gate/status/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404
        data = response.json()
        # Should be neutral, not stigmatizing
        assert "not found" in data["detail"]["message"].lower()
        # Should not contain diagnostic terms
        assert "hyperfocus" not in data["detail"]["message"].lower()
        assert "adhd" not in data["detail"]["message"].lower()


class TestSnakeCaseWireJSON:
    """Test that all API contracts use snake_case (D10)."""

    def test_response_uses_snake_case(self, client, session_with_ready_spec):
        """API responses use snake_case field names (D10)."""
        test_session, _ = session_with_ready_spec

        response = client.get(f"/api/v1/spec-gate/status/{test_session.id}")

        assert response.status_code == 200
        data = response.json()

        # Check for snake_case keys
        assert "done_when_count" in data
        assert "spec_id" in data or data.get("spec_id") is None

    def test_request_accepts_snake_case(self, client, session_with_ready_spec):
        """API requests accept snake_case field names (D10)."""
        test_session, _ = session_with_ready_spec

        response = client.post(
            "/api/v1/spec-gate/propose",
            json={
                "session_id": str(test_session.id),
                "what": "Test",
                "why": "Testing",
                "deliverable": "Output",
                "done_when": ["Done"],
            },
        )

        assert response.status_code == 200
