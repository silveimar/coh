"""Tests for prose renderer."""

from coh_prose.renderer import (
    DetourRecommendation,
    ExecutionForeground,
    ProseRenderer,
    RecoverySummary,
    SpecProposal,
    VerificationResult,
)


class TestSpecProposalRendering:
    """Test spec proposal rendering with P-01 (evidence first)."""

    def test_renders_inspection_findings_before_spec_block(self):
        renderer = ProseRenderer()
        spec = SpecProposal(
            inspection_findings="worker.py has no backoff in retry loop",
            what="Add exponential backoff to job retry",
            why="Prevent queue hammering on repeated failures",
            deliverable="Job retry with exponential backoff",
            done_when=["Tests pass", "Backoff implemented"],
            clarity="ready",
            readiness="ready",
        )

        output = renderer.render_spec_proposal(spec)

        assert "worker.py has no backoff" in output
        assert output.index("worker.py") < output.index("WHAT")

    def test_renders_without_inspection_findings(self):
        renderer = ProseRenderer()
        spec = SpecProposal(
            what="Fix issue",
            why="It's broken",
            deliverable="Fixed issue",
            done_when=["Tests pass"],
            clarity="ready",
            readiness="ready",
        )

        output = renderer.render_spec_proposal(spec)
        assert "WHAT" in output
        assert "WHY" in output


class TestExecutionForegroundRendering:
    """Test execution foreground rendering (P-06 exempt)."""

    def test_renders_execution_foreground(self):
        renderer = ProseRenderer()
        foreground = ExecutionForeground(
            goal="Add retry backoff",
            now="Implement exponential backoff in worker.py",
            now_done_when="Tests pass with backoff behavior",
            now_minutes=15,
            now_energy="medium",
            now_friction="low",
            next_1="Add max retry limit",
            next_2="Add dead letter queue",
            parked_count=2,
        )

        output = renderer.render_execution_foreground(foreground)

        assert "GOAL:" in output
        assert "NOW" in output
        assert "NEXT 1" in output
        assert "NEXT 2" in output
        assert "PARKED: 2" in output


class TestRecoverySummaryRendering:
    """Test recovery summary rendering (P-06 exempt)."""

    def test_renders_recovery_summary_with_all_fields(self):
        renderer = ProseRenderer()
        recovery = RecoverySummary(
            goal="Add retry backoff",
            why="Prevent queue hammering",
            last_verified="Initial inspection complete",
            last_decision="Use exponential backoff",
            last_decision_rationale="Better than linear",
            now="Implement backoff",
            next_1="Add tests",
            next_2="Document behavior",
            parked_count=1,
            restart_action="Open worker.py line 42",
        )

        output = renderer.render_recovery_summary(recovery)

        assert "GOAL:" in output
        assert "WHY:" in output
        assert "LAST VERIFIED:" in output
        assert "LAST DECISION:" in output
        assert "Rationale:" in output
        assert "START HERE:" in output

    def test_shows_archive_degraded_notice(self):
        renderer = ProseRenderer()
        recovery = RecoverySummary(
            goal="Test",
            why="Testing",
            restart_action="Test",
            archive_degraded=True,
        )

        output = renderer.render_recovery_summary(recovery)
        assert "Archive status is degraded" in output


class TestVerificationRendering:
    """Test verification result rendering with evidence (P-01)."""

    def test_renders_criteria_with_evidence(self):
        renderer = ProseRenderer()
        verification = VerificationResult(
            deliverable="Retry backoff",
            criteria_status=[
                {
                    "criterion": "Tests pass",
                    "status": "verified",
                    "evidence": "pytest output: 12 passed",
                },
                {
                    "criterion": "Backoff working",
                    "status": "verified",
                    "evidence": "Log shows increasing delays",
                },
            ],
            completion_state="verified",
            parked_count=0,
        )

        output = renderer.render_verification(verification)

        assert "Criteria status:" in output
        assert "Evidence:" in output
        assert "pytest output" in output


class TestDetourRecommendationRendering:
    """Test detour recommendation rendering (P-01: finding first)."""

    def test_renders_finding_before_recommendation(self):
        renderer = ProseRenderer()
        detour = DetourRecommendation(
            finding="Tests are missing for error paths",
            relevance="high",
            blocking=True,
            recommendation="Add error path tests before completing",
            alternatives=["Continue and add tests later", "Park for separate task"],
        )

        output = renderer.render_detour_recommendation(detour)

        assert "Finding:" in output
        assert "Recommendation:" in output
        assert output.index("Finding:") < output.index("Recommendation:")


class TestRecapAddition:
    """Test P-03: Recap addition when threshold exceeded."""

    def test_adds_recap_when_threshold_exceeded(self):
        renderer = ProseRenderer()
        short_prose = "\n".join([f"Line {i}" for i in range(5)])

        result = renderer.add_recap_if_needed(short_prose, "Summary")
        assert "In short:" not in result

    def test_no_recap_below_threshold(self):
        renderer = ProseRenderer()
        long_prose = "\n".join([f"Line {i}" for i in range(15)])

        result = renderer.add_recap_if_needed(long_prose, "Summary")
        assert "In short:" in result
        assert "Summary" in result

    def test_rejects_recap_exceeding_max_lines(self):
        renderer = ProseRenderer()
        prose = "\n".join([f"Line {i}" for i in range(15)])
        long_recap = "\n".join([f"Recap line {i}" for i in range(5)])

        try:
            renderer.add_recap_if_needed(prose, long_recap)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "exceeds" in str(e)
