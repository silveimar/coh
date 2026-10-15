"""Tests for specification domain model and readiness computation."""

from execution_core.domain.enums import AssumptionClass
from execution_core.domain.specification import (
    Assumption,
    Clarity,
    DoneWhenCriterion,
    Readiness,
    Specification,
    Unknown,
)


class TestSpecification:
    """Test specification model and clarity/readiness computation."""

    def test_empty_spec_has_low_clarity_and_blocked(self):
        """Empty spec should have low clarity and blocked readiness."""
        spec = Specification(what="", why="", deliverable="")
        spec.update_computed_fields()

        assert spec.clarity == Clarity.LOW
        assert spec.readiness == Readiness.BLOCKED

    def test_complete_spec_has_ready_clarity_and_readiness(self):
        """Complete spec with all fields should be ready."""
        spec = Specification(
            what="Add user login feature",
            why="Users need authentication",
            deliverable="Working login page with auth",
            done_when=[DoneWhenCriterion(text="User can log in successfully")],
            constraints=["Must use OAuth"],
            non_goals=["Email notifications"],
        )
        spec.update_computed_fields()

        assert spec.clarity == Clarity.READY
        assert spec.readiness == Readiness.READY

    def test_blocking_unknown_prevents_readiness(self):
        """Blocking unknown should prevent readiness."""
        spec = Specification(
            what="Fix bug",
            why="App crashes",
            deliverable="Fixed app",
            done_when=[DoneWhenCriterion(text="No crashes")],
            unknowns=[Unknown(text="What causes crash?", blocking=True)],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.BLOCKED

    def test_non_blocking_unknown_allows_readiness(self):
        """Non-blocking unknown should not prevent readiness."""
        spec = Specification(
            what="Add feature",
            why="User request",
            deliverable="Feature",
            done_when=[DoneWhenCriterion(text="Works")],
            unknowns=[Unknown(text="Performance impact?", blocking=False)],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.READY

    def test_blocking_assumption_prevents_readiness(self):
        """Blocking assumption should prevent readiness."""
        spec = Specification(
            what="Deploy",
            why="Release",
            deliverable="Deployed app",
            done_when=[DoneWhenCriterion(text="Live")],
            assumptions=[
                Assumption(
                    text="Database is compatible",
                    classification=AssumptionClass.BLOCKING,
                )
            ],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.BLOCKED

    def test_unconfirmed_material_assumption_prevents_readiness(self):
        """Unconfirmed material assumption requiring confirmation blocks readiness."""
        spec = Specification(
            what="Add API",
            why="Integration",
            deliverable="API endpoint",
            done_when=[DoneWhenCriterion(text="Returns data")],
            assumptions=[
                Assumption(
                    text="API rate limit is 1000/hour",
                    classification=AssumptionClass.MATERIAL,
                    requires_confirmation=True,
                )
            ],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.BLOCKED

    def test_resolved_blocking_assumption_allows_readiness(self):
        """Resolved blocking assumption should allow readiness."""
        spec = Specification(
            what="Deploy",
            why="Release",
            deliverable="Deployed app",
            done_when=[DoneWhenCriterion(text="Live")],
            assumptions=[
                Assumption(
                    text="Database is compatible",
                    classification=AssumptionClass.BLOCKING,
                    resolved=True,
                )
            ],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.READY

    def test_missing_done_when_blocks_readiness(self):
        """Missing done-when criteria should block readiness."""
        spec = Specification(
            what="Add feature",
            why="User request",
            deliverable="Feature",
            done_when=[],
        )
        spec.update_computed_fields()

        assert spec.readiness == Readiness.BLOCKED

    def test_create_revision_increments_revision_number(self):
        """Creating revision should increment revision number."""
        spec = Specification(
            what="Original",
            why="Why",
            deliverable="Deliverable",
            done_when=[DoneWhenCriterion(text="Done")],
        )
        spec.revision = 1

        new_spec = spec.create_revision()

        assert new_spec.revision == 2
        assert new_spec.id != spec.id
        assert new_spec.confirmed_at is None

    def test_clarity_levels(self):
        """Test clarity computation at different completeness levels."""
        base_spec = Specification(what="", why="", deliverable="", done_when=[])

        base_spec.update_computed_fields()
        assert base_spec.clarity == Clarity.LOW

        base_spec.what = "What"
        base_spec.why = "Why"
        base_spec.update_computed_fields()
        assert base_spec.clarity == Clarity.MEDIUM

        base_spec.deliverable = "Deliverable"
        base_spec.done_when = [DoneWhenCriterion(text="Done")]
        base_spec.update_computed_fields()
        assert base_spec.clarity == Clarity.HIGH

        base_spec.constraints = ["Constraint"]
        base_spec.update_computed_fields()
        assert base_spec.clarity == Clarity.READY
