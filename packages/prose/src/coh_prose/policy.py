"""Prose rendering policy (P-01 through P-06) per Behavioral Contract §5."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ProtectedField(StrEnum):
    """Protected fields that must never be dropped (P-05)."""

    CAUSALITY = "causality"
    SEQUENCE = "sequence"
    NEGATION = "negation"
    DEPENDENCIES = "dependencies"
    CONSTRAINTS = "constraints"
    WARNINGS = "warnings"
    COMPLETION_CRITERIA = "completion_criteria"
    DECISION_RATIONALE = "decision_rationale"


class ProseConfig(BaseModel):
    """Prose rendering configuration."""

    recap_threshold_lines: int = 12
    max_recap_lines: int = 3
    enable_evidence_first: bool = True
    enable_no_scaffolding: bool = True
    enable_recap: bool = True
    enable_density: bool = True
    enable_protected_fields: bool = True


class ProseValidationResult(BaseModel):
    """Result of prose policy validation."""

    valid: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProsePolicy:
    """
    Prose rendering policy enforcer (P-01 through P-06).

    P-01: Evidence before conclusion
    P-02: No prospective scaffolding
    P-03: Retrospective consolidation (recap when > threshold)
    P-04: Density (no filler)
    P-05: Protected fields never dropped
    P-06: Recovery/foreground exempt from P-01/P-02
    """

    # P-02: Preview/agenda phrases to reject
    SCAFFOLDING_PHRASES = [
        "there are",
        "first i'll",
        "first, i'll",
        "let me walk you through",
        "in this section",
        "we'll cover",
        "i'll explain",
        "i'm going to explain",
        "i'm going to cover",
        "i'm going to describe",
        "let me explain",
        "let me describe",
        "let me cover",
    ]

    # P-05: Protected field markers (simplified - full implementation would use NLP)
    PROTECTED_MARKERS = {
        ProtectedField.NEGATION: [
            "not",
            "don't",
            "doesn't",
            "won't",
            "can't",
            "never",
            "no ",
        ],
        ProtectedField.WARNINGS: ["warning", "caution", "careful", "risk", "danger"],
        ProtectedField.CONSTRAINTS: ["must", "required", "only", "constraint"],
        ProtectedField.DEPENDENCIES: ["depends on", "requires", "needs", "blocked by"],
        ProtectedField.CAUSALITY: ["because", "therefore", "thus", "so", "since"],
        ProtectedField.SEQUENCE: ["first", "then", "next", "after", "before"],
    }

    def __init__(self, config: ProseConfig | None = None):
        self.config = config or ProseConfig()

    def validate_evidence_first(
        self, prose: str, has_evidence: bool
    ) -> ProseValidationResult:
        """
        P-01: Evidence before conclusion.

        For spec proposals, inspection findings should appear before the spec block.
        """
        if not self.config.enable_evidence_first:
            return ProseValidationResult(valid=True)

        if not has_evidence:
            return ProseValidationResult(
                valid=False,
                violations=[
                    "P-01 violation: No concrete evidence/observation before conclusion"
                ],
            )

        return ProseValidationResult(valid=True)

    def validate_no_scaffolding(self, prose: str) -> ProseValidationResult:
        """
        P-02: No prospective scaffolding.

        Reject preview/agenda phrasing.
        """
        if not self.config.enable_no_scaffolding:
            return ProseValidationResult(valid=True)

        prose_lower = prose.lower()
        violations = []

        for phrase in self.SCAFFOLDING_PHRASES:
            if phrase in prose_lower:
                violations.append(
                    f'P-02 violation: Found scaffolding phrase "{phrase}"'
                )

        if violations:
            return ProseValidationResult(valid=False, violations=violations)

        return ProseValidationResult(valid=True)

    def validate_recap_threshold(self, prose: str) -> ProseValidationResult:
        """
        P-03: Retrospective consolidation.

        Prose exceeding threshold should have a recap of ≤3 lines.
        Below threshold, no recap should be added.
        """
        if not self.config.enable_recap:
            return ProseValidationResult(valid=True)

        lines = [line for line in prose.split("\n") if line.strip()]
        line_count = len(lines)

        if line_count > self.config.recap_threshold_lines:
            recap_indicators = ["in short", "to recap", "in summary", "recap:"]
            has_recap = any(
                indicator in prose.lower() for indicator in recap_indicators
            )

            if not has_recap:
                return ProseValidationResult(
                    valid=False,
                    violations=[
                        f"P-03 violation: Prose has {line_count} lines "
                        f"(>{self.config.recap_threshold_lines}) but no recap"
                    ],
                )

        return ProseValidationResult(valid=True)

    def validate_protected_fields(
        self, original: str, compressed: str
    ) -> ProseValidationResult:
        """
        P-05: Protected fields never dropped.

        Validates that compression didn't remove protected content.
        """
        if not self.config.enable_protected_fields:
            return ProseValidationResult(valid=True)

        violations = []

        for field, markers in self.PROTECTED_MARKERS.items():
            original_lower = original.lower()
            compressed_lower = compressed.lower()

            for marker in markers:
                if marker in original_lower and marker not in compressed_lower:
                    violations.append(
                        f'P-05 violation: Protected field "{field.value}" '
                        f'marker "{marker}" dropped in compression'
                    )

        if violations:
            return ProseValidationResult(valid=False, violations=violations)

        return ProseValidationResult(valid=True)

    def is_recovery_or_foreground_exempt(self, context: str | None) -> bool:
        """
        P-06: Recovery/foreground context is exempt from P-01/P-02.

        Prospective framing is the model being restored.
        """
        if context is None:
            return False

        context_lower = context.lower()
        return any(
            keyword in context_lower
            for keyword in ["recover", "recovery", "foreground", "restart"]
        )

    def validate(
        self,
        prose: str,
        has_evidence: bool = False,
        context: str | None = None,
    ) -> ProseValidationResult:
        """
        Validate prose against all applicable policies.

        Args:
            prose: The prose to validate
            has_evidence: Whether evidence precedes conclusions (P-01)
            context: Context indicator (e.g., "recovery", "foreground")
                for P-06 exemption

        Returns:
            ProseValidationResult with violations
        """
        is_exempt = self.is_recovery_or_foreground_exempt(context)

        all_violations = []
        all_warnings = []

        if not is_exempt:
            result = self.validate_evidence_first(prose, has_evidence)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)

            result = self.validate_no_scaffolding(prose)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)

        result = self.validate_recap_threshold(prose)
        all_violations.extend(result.violations)
        all_warnings.extend(result.warnings)

        return ProseValidationResult(
            valid=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
        )
