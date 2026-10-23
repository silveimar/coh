"""Tests for SpecGateService enforcing I-02 (readiness gate)."""

import pytest
from sqlalchemy.orm import sessionmaker

from coh_application.spec_gate_service import SpecGateService
from execution_core.domain.enums import (
    LifecycleState,
    Readiness,
    SessionIntent,
)
from execution_core.domain.session import ExecutionSession
from persistence.infrastructure.database import create_engine, init_db
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class TestSpecGateService:
    """Test spec gate service I-02 enforcement and readiness computation."""

    @pytest.fixture
    def uow(self):
        """Create in-memory SQLite UnitOfWork for testing."""
        engine = create_engine("sqlite:///:memory:")
        init_db(engine)
        session_factory = sessionmaker(bind=engine)
        return SqlAlchemyUnitOfWork(session_factory)

    @pytest.fixture
    def session(self, uow):
        """Create a test session."""
        session = ExecutionSession(
            project_id="test-project",
            intent=SessionIntent.EXECUTE,
            lifecycle_state=LifecycleState.SPECIFY,
        )
        with uow:
            uow.sessions.add(session)
            uow.commit()
        return session

    def test_propose_spec_computes_ready_when_complete(self, uow, session):
        """Spec with all required fields computes readiness=READY."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Implement user authentication",
                why="Security requirement",
                deliverable="Working login/logout with JWT",
                done_when=["User can login", "User can logout", "Tokens expire"],
            )

        assert spec.readiness == Readiness.READY
        assert spec.what
        assert spec.why
        assert spec.deliverable
        assert len(spec.done_when) == 3

    def test_propose_spec_blocked_without_required_fields(self, uow, session):
        """Spec missing required fields computes readiness=BLOCKED."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="",
                why="Security",
                deliverable="Login",
                done_when=["User can login"],
            )

        assert spec.readiness == Readiness.BLOCKED

        with uow:
            spec2 = service.propose_spec(
                session_id=session.id,
                what="Auth",
                why="",
                deliverable="Login",
                done_when=["User can login"],
            )

        assert spec2.readiness == Readiness.BLOCKED

        with uow:
            spec3 = service.propose_spec(
                session_id=session.id,
                what="Auth",
                why="Security",
                deliverable="",
                done_when=["User can login"],
            )

        assert spec3.readiness == Readiness.BLOCKED

        with uow:
            spec4 = service.propose_spec(
                session_id=session.id,
                what="Auth",
                why="Security",
                deliverable="Login",
                done_when=[],
            )

        assert spec4.readiness == Readiness.BLOCKED

    def test_readiness_truth_table_blocking_unknown(self, uow, session):
        """Readiness=BLOCKED when blocking unknown is unresolved."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Implement API",
                why="Required",
                deliverable="API endpoint",
                done_when=["Endpoint works"],
                unknowns=[
                    {"text": "Which auth method?", "blocking": True},
                ],
            )

        assert spec.readiness == Readiness.BLOCKED
        blockers = service._get_readiness_blockers(spec)
        assert any("Unknown:" in b and "recommended:" in b for b in blockers)

        spec.unknowns[0].resolved = True
        spec.update_computed_fields()
        assert spec.readiness == Readiness.READY

    def test_readiness_truth_table_blocking_assumption(self, uow, session):
        """Readiness=BLOCKED when blocking assumption is unresolved."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Deploy service",
                why="Release",
                deliverable="Live service",
                done_when=["Service responds"],
                assumptions=[
                    {
                        "text": "Infrastructure available",
                        "classification": "blocking",
                        "requires_confirmation": True,
                    }
                ],
            )

        assert spec.readiness == Readiness.BLOCKED
        blockers = service._get_readiness_blockers(spec)
        assert any("blocking assumption" in b for b in blockers)

    def test_readiness_truth_table_unconfirmed_material_assumption(self, uow, session):
        """Readiness=BLOCKED when material assumption requires confirmation."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Implement feature",
                why="User request",
                deliverable="Working feature",
                done_when=["Feature works"],
                assumptions=[
                    {
                        "text": "Users prefer option A",
                        "classification": "material",
                        "requires_confirmation": True,
                    }
                ],
            )

        assert spec.readiness == Readiness.BLOCKED
        blockers = service._get_readiness_blockers(spec)
        assert any("unconfirmed material assumption" in b for b in blockers)

        spec.assumptions[0].resolved = True
        spec.update_computed_fields()
        assert spec.readiness == Readiness.READY

    def test_readiness_safe_assumption_does_not_block(self, uow, session):
        """Readiness=READY when only safe assumptions exist."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Add logging",
                why="Debugging",
                deliverable="Logs captured",
                done_when=["Logs appear"],
                assumptions=[
                    {
                        "text": "Default log level is INFO",
                        "classification": "safe",
                    }
                ],
            )

        assert spec.readiness == Readiness.READY

    def test_i02_reject_mutation_while_blocked(self, uow, session):
        """I-02: Material mutation rejected while readiness=BLOCKED."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )
            uow.specifications.add(spec)
            loaded_session = uow.sessions.get(session.id)
            loaded_session.current_spec = spec
            uow.sessions.update(loaded_session, expected_version=1)
            uow.commit()

        with pytest.raises(PermissionError) as exc_info:
            with uow:
                service.require_ready_for_mutation(session.id)

        assert "Material mutation rejected" in str(exc_info.value)
        assert "readiness is BLOCKED" in str(exc_info.value)
        assert "Read-only inspection remains permitted" in str(exc_info.value)

    def test_i02_allow_mutation_when_ready(self, uow, session):
        """I-02: Material mutation allowed when readiness=READY."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Complete spec",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )
            uow.specifications.add(spec)
            loaded_session = uow.sessions.get(session.id)
            loaded_session.current_spec = spec
            uow.sessions.update(loaded_session, expected_version=1)
            uow.commit()

        with uow:
            service.require_ready_for_mutation(session.id)

    def test_i02_read_only_inspection_always_permitted(self, uow, session):
        """I-02: Read-only inspection permitted regardless of readiness."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )
            uow.specifications.add(spec)
            loaded_session = uow.sessions.get(session.id)
            loaded_session.current_spec = spec
            uow.sessions.update(loaded_session, expected_version=1)
            uow.commit()

        with uow:
            status = service.get_spec_status(session.id)

        assert status["readiness"] == "blocked"
        assert "Missing WHAT" in status["blockers"]

    def test_check_mutation_allowed_returns_correct_state(self, uow, session):
        """check_mutation_allowed returns (allowed, state, blockers)."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Test",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )
            uow.specifications.add(spec)
            loaded_session = uow.sessions.get(session.id)
            loaded_session.current_spec = spec
            uow.sessions.update(loaded_session, expected_version=1)
            uow.commit()

        with uow:
            allowed, state, blockers = service.check_mutation_allowed(session.id)

        assert allowed is True
        assert state == "ready"
        assert len(blockers) == 0

        with uow:
            spec.what = ""
            spec.update_computed_fields()
            uow.specifications.update(spec)
            uow.commit()

        with uow:
            allowed, state, blockers = service.check_mutation_allowed(session.id)

        assert allowed is False
        assert state == "blocked"
        assert "Missing WHAT" in blockers

    def test_confirm_spec_rejects_blocked_spec(self, uow, session):
        """confirm_spec raises ValueError when spec is BLOCKED."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )

        with pytest.raises(ValueError) as exc_info:
            with uow:
                service.confirm_spec(session.id, spec)

        assert "Cannot confirm spec with readiness=BLOCKED" in str(exc_info.value)

    def test_confirm_spec_persists_ready_spec(self, uow, session):
        """confirm_spec persists spec and updates session when READY."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Complete",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )

        with uow:
            confirmed = service.confirm_spec(session.id, spec)

        assert confirmed.readiness == Readiness.READY

        with uow:
            status = service.get_spec_status(session.id)

        assert status["spec_id"] == str(confirmed.id)
        assert status["readiness"] == "ready"

    def test_revise_spec_creates_new_revision(self, uow, session):
        """revise_spec creates new revision with incremented revision number."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Original",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
            )
            confirmed = service.confirm_spec(session.id, spec)

        assert confirmed.revision == 1

        with uow:
            revised = service.revise_spec(session.id, confirmed.id, {"what": "Revised"})

        assert revised.revision == 2
        assert revised.what == "Revised"
        assert revised.id != confirmed.id

    def test_revise_spec_done_when_round_trips(self, uow, session):
        """done_when text is stored as criteria and can be loaded again."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Original",
                why="Reason",
                deliverable="Output",
                done_when=["Old criterion"],
            )
            confirmed = service.confirm_spec(session.id, spec)

        with uow:
            revised = service.revise_spec(
                session.id,
                confirmed.id,
                {
                    "done_when": ["New criterion"],
                    "constraints": ["stay local"],
                },
            )

        assert [criterion.text for criterion in revised.done_when] == ["New criterion"]
        assert revised.constraints == ["stay local"]

        with uow:
            loaded = uow.specifications.get(revised.id)
            status = service.get_spec_status(session.id)

        assert loaded is not None
        assert [criterion.text for criterion in loaded.done_when] == ["New criterion"]
        assert loaded.constraints == ["stay local"]
        assert status["spec_id"] == str(revised.id)
        assert status["done_when_count"] == 1
        assert status["readiness"] == "ready"

    def test_revise_spec_rejects_unsafe_updates_without_writing(self, uow, session):
        """Unknown fields and mistyped lists do not replace the current spec."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Original",
                why="Reason",
                deliverable="Output",
                done_when=["Old criterion"],
            )
            confirmed = service.confirm_spec(session.id, spec)

        with pytest.raises(ValueError, match="Cannot revise field"):
            with uow:
                service.revise_spec(session.id, confirmed.id, {"id": str(confirmed.id)})

        with pytest.raises(ValueError, match="constraints must be a list of strings"):
            with uow:
                service.revise_spec(
                    session.id, confirmed.id, {"constraints": "stay local"}
                )

        with uow:
            status = service.get_spec_status(session.id)
            loaded = uow.specifications.get(confirmed.id)

        assert status["spec_id"] == str(confirmed.id)
        assert status["revision"] == "1"
        assert loaded is not None
        assert loaded.constraints == []

    def test_get_questions_groups_blocking_and_material(self, uow, session):
        """get_questions returns grouped questions with recommended defaults."""
        service = SpecGateService(uow)

        with uow:
            spec = service.propose_spec(
                session_id=session.id,
                what="Feature",
                why="Reason",
                deliverable="Output",
                done_when=["Done"],
                unknowns=[
                    {"text": "Unknown 1", "blocking": True},
                    {"text": "Unknown 2", "blocking": False},
                ],
                assumptions=[
                    {
                        "text": "Assumption 1",
                        "classification": "material",
                        "requires_confirmation": True,
                    },
                    {
                        "text": "Assumption 2",
                        "classification": "safe",
                    },
                ],
            )

        questions = service.get_questions(spec)

        assert len(questions["blocking_unknowns"]) == 1
        assert questions["blocking_unknowns"][0]["text"] == "Unknown 1"

        assert len(questions["material_assumptions"]) == 1
        assert questions["material_assumptions"][0]["text"] == "Assumption 1"
        assert questions["material_assumptions"][0]["recommended_default"] == "confirm"
