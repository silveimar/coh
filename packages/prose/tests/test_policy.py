"""Tests for prose policy (P-01 through P-06)."""

import pytest

from coh_prose.policy import ProseConfig, ProsePolicy


class TestP01EvidenceFirst:
    """Test P-01: Evidence before conclusion."""

    def test_validation_passes_with_evidence(self):
        policy = ProsePolicy()
        result = policy.validate_evidence_first(
            "worker.py has no backoff. Add exponential backoff.", has_evidence=True
        )
        assert result.valid

    def test_validation_fails_without_evidence(self):
        policy = ProsePolicy()
        result = policy.validate_evidence_first(
            "Add exponential backoff.", has_evidence=False
        )
        assert not result.valid
        assert "P-01 violation" in result.violations[0]


class TestP02NoScaffolding:
    """Test P-02: No prospective scaffolding."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "There are three things to fix",
            "First I'll explain the problem",
            "Let me walk you through",
            "In this section we'll cover",
        ],
    )
    def test_rejects_scaffolding_phrases(self, phrase):
        policy = ProsePolicy()
        result = policy.validate_no_scaffolding(phrase)
        assert not result.valid
        assert "P-02 violation" in result.violations[0]

    def test_accepts_clean_prose(self):
        policy = ProsePolicy()
        result = policy.validate_no_scaffolding(
            "worker.py retry loop has no backoff. "
            "The job re-enqueues immediately on failure."
        )
        assert result.valid


class TestP03RecapThreshold:
    """Test P-03: Retrospective consolidation."""

    def test_requires_recap_above_threshold(self):
        policy = ProsePolicy(ProseConfig(recap_threshold_lines=3))
        long_prose = "\n".join([f"Line {i}" for i in range(10)])

        result = policy.validate_recap_threshold(long_prose)
        assert not result.valid
        assert "P-03 violation" in result.violations[0]

    def test_accepts_recap_when_present(self):
        policy = ProsePolicy(ProseConfig(recap_threshold_lines=3))
        long_prose = "\n".join([f"Line {i}" for i in range(10)])
        long_prose += "\n\nIn short: summary here"

        result = policy.validate_recap_threshold(long_prose)
        assert result.valid

    def test_accepts_short_prose_without_recap(self):
        policy = ProsePolicy(ProseConfig(recap_threshold_lines=10))
        short_prose = "Line 1\nLine 2\nLine 3"

        result = policy.validate_recap_threshold(short_prose)
        assert result.valid


class TestP05ProtectedFields:
    """Test P-05: Protected fields never dropped."""

    def test_detects_dropped_negation(self):
        policy = ProsePolicy()
        original = "Do NOT run the migration against production"
        compressed = "Run the migration when ready"

        result = policy.validate_protected_fields(original, compressed)
        assert not result.valid
        assert "negation" in result.violations[0].lower()

    def test_detects_dropped_warning(self):
        policy = ProsePolicy()
        original = "Warning: this will delete all data"
        compressed = "This will modify data"

        result = policy.validate_protected_fields(original, compressed)
        assert not result.valid
        assert "warning" in result.violations[0].lower()

    def test_accepts_preserved_protected_fields(self):
        policy = ProsePolicy()
        original = "Do not run against production. Warning: irreversible."
        compressed = "Do not run on production. Warning: irreversible."

        result = policy.validate_protected_fields(original, compressed)
        assert result.valid


class TestP06RecoveryExemption:
    """Test P-06: Recovery/foreground exempt from P-01/P-02."""

    def test_recovery_context_is_exempt(self):
        policy = ProsePolicy()
        assert policy.is_recovery_or_foreground_exempt("recovery")
        assert policy.is_recovery_or_foreground_exempt("foreground")
        assert policy.is_recovery_or_foreground_exempt("restart")

    def test_normal_context_not_exempt(self):
        policy = ProsePolicy()
        assert not policy.is_recovery_or_foreground_exempt("specify")
        assert not policy.is_recovery_or_foreground_exempt(None)

    def test_recovery_allows_prospective_framing(self):
        policy = ProsePolicy()
        prose_with_scaffolding = "There are three steps to complete"

        result = policy.validate(
            prose_with_scaffolding, has_evidence=False, context="recovery"
        )
        assert result.valid


class TestIntegratedValidation:
    """Test integrated prose validation."""

    def test_validates_all_policies(self):
        policy = ProsePolicy()
        prose = "There are three things"

        result = policy.validate(prose, has_evidence=False)
        assert not result.valid
        assert len(result.violations) >= 2

    def test_recovery_context_bypasses_p01_p02(self):
        policy = ProsePolicy()
        prose = "First I'll restore the goal"

        result = policy.validate(prose, has_evidence=False, context="recovery")
        assert result.valid
