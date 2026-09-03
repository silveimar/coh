"""Prose renderer implementing the output contract §4."""

from pydantic import BaseModel, Field

from .policy import ProseConfig, ProsePolicy


class ProseBlock(BaseModel):
    """A prose content block with optional evidence."""

    content: str
    has_evidence: bool = False
    context: str | None = None


class SpecProposal(BaseModel):
    """Spec proposal output (SPECIFY/CONFIRM state)."""

    inspection_findings: str | None = None
    what: str
    why: str
    deliverable: str
    done_when: list[str] = Field(default_factory=list)
    clarity: str
    readiness: str
    blockers: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ExecutionForeground(BaseModel):
    """Execution foreground output (PLAN/EXECUTE state)."""

    goal: str
    now: str
    now_done_when: str
    now_minutes: int | None = None
    now_energy: str | None = None
    now_friction: str | None = None
    next_1: str | None = None
    next_2: str | None = None
    parked_count: int = 0


class RecoverySummary(BaseModel):
    """Recovery summary output (recover intent)."""

    goal: str
    why: str
    last_verified: str | None = None
    last_decision: str | None = None
    last_decision_rationale: str | None = None
    now: str | None = None
    next_1: str | None = None
    next_2: str | None = None
    parked_count: int = 0
    restart_action: str
    archive_degraded: bool = False


class VerificationResult(BaseModel):
    """Verification/completion output (VERIFY/COMPLETE state)."""

    deliverable: str
    criteria_status: list[dict[str, str]] = Field(default_factory=list)
    completion_state: str
    remaining_blockers: list[str] = Field(default_factory=list)
    parked_count: int = 0
    next_action: str | None = None


class DetourRecommendation(BaseModel):
    """Detour recommendation output."""

    finding: str
    relevance: str
    blocking: bool
    recommendation: str
    alternatives: list[str] = Field(default_factory=list)


class ProseRenderer:
    """
    Prose renderer implementing §4 Output Contract with P-01 through P-06.

    Renders structured blocks with surrounding prose that follows the prose policy.
    """

    def __init__(self, config: ProseConfig | None = None):
        self.config = config or ProseConfig()
        self.policy = ProsePolicy(self.config)

    def render_spec_proposal(self, spec: SpecProposal) -> str:
        """
        Render spec proposal with inspection findings BEFORE the spec block (P-01).

        SPECIFY/CONFIRM state output.
        """
        output = []

        if spec.inspection_findings:
            output.append(spec.inspection_findings)
            output.append("")

        output.append("WHAT")
        output.append(spec.what)
        output.append("")

        output.append("WHY")
        output.append(spec.why)
        output.append("")

        output.append("DELIVERABLE")
        output.append(spec.deliverable)
        output.append("")

        output.append("DONE WHEN")
        for idx, criterion in enumerate(spec.done_when, 1):
            output.append(f"{idx}. {criterion}")
        output.append("")

        output.append(f"CLARITY: {spec.clarity}")
        output.append(f"READINESS: {spec.readiness}")

        if spec.blockers:
            output.append("")
            output.append("Blockers:")
            for blocker in spec.blockers:
                output.append(f"- {blocker}")

        if spec.open_questions:
            output.append("")
            output.append("Open questions:")
            for question in spec.open_questions:
                output.append(f"- {question}")

        return "\n".join(output)

    def render_execution_foreground(self, foreground: ExecutionForeground) -> str:
        """
        Render execution foreground (P-06: exempt from P-01/P-02).

        PLAN/EXECUTE state output.
        """
        output = []

        output.append(f"GOAL: {foreground.goal}")
        output.append("")

        output.append("NOW")
        output.append(foreground.now)
        output.append(f"Done when: {foreground.now_done_when}")

        if foreground.now_minutes:
            output.append(f"Estimated: {foreground.now_minutes} minutes")
        if foreground.now_energy:
            output.append(f"Energy: {foreground.now_energy}")
        if foreground.now_friction:
            output.append(f"Friction: {foreground.now_friction}")
        output.append("")

        if foreground.next_1:
            output.append("NEXT 1")
            output.append(foreground.next_1)
            output.append("")

        if foreground.next_2:
            output.append("NEXT 2")
            output.append(foreground.next_2)
            output.append("")

        output.append(f"PARKED: {foreground.parked_count}")

        return "\n".join(output)

    def render_recovery_summary(self, recovery: RecoverySummary) -> str:
        """
        Render recovery summary (P-06: exempt from P-01/P-02).

        Recover intent output with prospective framing.
        """
        output = []

        output.append(f"GOAL: {recovery.goal}")
        output.append("")
        output.append(f"WHY: {recovery.why}")
        output.append("")

        if recovery.last_verified:
            output.append(f"LAST VERIFIED: {recovery.last_verified}")
            output.append("")

        if recovery.last_decision:
            output.append(f"LAST DECISION: {recovery.last_decision}")
            if recovery.last_decision_rationale:
                output.append(f"Rationale: {recovery.last_decision_rationale}")
            output.append("")

        if recovery.now:
            output.append("NOW")
            output.append(recovery.now)
            output.append("")

        if recovery.next_1 or recovery.next_2:
            output.append("NEXT")
            if recovery.next_1:
                output.append(f"1. {recovery.next_1}")
            if recovery.next_2:
                output.append(f"2. {recovery.next_2}")
            output.append("")

        output.append(f"PARKED: {recovery.parked_count}")
        output.append("")

        output.append(f"START HERE: {recovery.restart_action}")

        if recovery.archive_degraded:
            output.append("")
            output.append(
                "Note: Archive status is degraded. "
                "Some interaction history may be incomplete."
            )

        return "\n".join(output)

    def render_verification(self, verification: VerificationResult) -> str:
        """
        Render verification result with criterion-by-criterion evidence (P-01).

        VERIFY/COMPLETE state output.
        """
        output = []

        output.append(f"Deliverable: {verification.deliverable}")
        output.append("")

        output.append("Criteria status:")
        for criterion in verification.criteria_status:
            status = criterion.get("status", "unknown")
            evidence = criterion.get("evidence", "none")
            output.append(f"- {criterion.get('criterion', 'unknown')}: {status}")
            output.append(f"  Evidence: {evidence}")
        output.append("")

        output.append(f"Completion state: {verification.completion_state}")

        if verification.remaining_blockers:
            output.append("")
            output.append("Remaining blockers:")
            for blocker in verification.remaining_blockers:
                output.append(f"- {blocker}")

        output.append("")
        output.append(f"PARKED: {verification.parked_count}")

        if verification.next_action:
            output.append("")
            output.append(f"Next action: {verification.next_action}")

        return "\n".join(output)

    def render_detour_recommendation(self, detour: DetourRecommendation) -> str:
        """
        Render detour recommendation: finding → assessment → recommendation (P-01).
        """
        output = []

        output.append("Finding:")
        output.append(detour.finding)
        output.append("")

        assessment = f"Relevance: {detour.relevance}"
        if detour.blocking:
            assessment += " (blocking)"
        output.append(assessment)
        output.append("")

        output.append("Recommendation:")
        output.append(detour.recommendation)

        if detour.alternatives:
            output.append("")
            output.append("Alternatives:")
            for alt in detour.alternatives:
                output.append(f"- {alt}")

        return "\n".join(output)

    def add_recap_if_needed(self, prose: str, recap: str) -> str:
        """
        Add recap to prose if it exceeds threshold (P-03).

        Args:
            prose: Original prose
            recap: Recap text (≤3 lines)

        Returns:
            Prose with recap if threshold exceeded
        """
        if not self.config.enable_recap:
            return prose

        lines = [line for line in prose.split("\n") if line.strip()]
        if len(lines) <= self.config.recap_threshold_lines:
            return prose

        recap_lines = [line for line in recap.split("\n") if line.strip()]
        if len(recap_lines) > self.config.max_recap_lines:
            raise ValueError(
                f"Recap exceeds {self.config.max_recap_lines} lines: {len(recap_lines)}"
            )

        return f"{prose}\n\nIn short: {recap}"
