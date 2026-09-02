"""Archive policy enforcing I-04 (append-only) and I-12 (degrade-and-continue)."""

from datetime import datetime


class ArchivePolicy:
    """Enforces I-04 (append-only) and I-12 (archive failure handling)."""

    @staticmethod
    def validate_append_only(
        operation: str, entry_exists: bool, is_overwrite: bool
    ) -> tuple[bool, str]:
        """Enforce I-04: archive is append-only, no overwrites."""
        if operation == "write" and entry_exists and is_overwrite:
            return (
                False,
                "Archive violation (I-04): cannot overwrite existing entry. "
                "Corrections must be new entries.",
            )
        return True, ""

    @staticmethod
    def handle_write_failure(
        entry_content: str, failure_reason: str
    ) -> tuple[str, dict[str, str]]:
        """Enforce I-12: degrade-and-continue on archive failure."""
        return (
            "archive_write_failed",
            {
                "reason": failure_reason,
                "action": (
                    "Checkpoint marked degraded; "
                    "archival resumes on next successful write"
                ),
                "in_memory_preserved": "true",
                "entry_content_hash": str(hash(entry_content)),
            },
        )

    @staticmethod
    def create_archive_reference(
        path: str, timestamp: datetime, anchor: str
    ) -> dict[str, str]:
        """Create stable archive reference for checkpoint provenance (I-09)."""
        return {
            "path": path,
            "timestamp": timestamp.isoformat(),
            "anchor": anchor,
        }

    @staticmethod
    def generate_anchor(actor: str, timestamp: datetime) -> str:
        """Generate stable anchor ID for archive entry."""
        iso_ts = timestamp.strftime("%Y%m%dT%H%M%S")
        hash_suffix = str(hash(f"{actor}{timestamp}"))[-4:]
        return f"{actor}-{iso_ts}-{hash_suffix}"

    @staticmethod
    def should_warn_degraded(archive_status: str) -> bool:
        """Check if degraded archive status warrants user warning."""
        return archive_status == "degraded"


class ProposalPolicy:
    """Enforces I-06: LLM output is proposal-only."""

    @staticmethod
    def validate_proposal_before_mutation(
        proposal_dict: dict, schema_valid: bool, policy_valid: bool
    ) -> tuple[bool, list[str]]:
        """Enforce I-06: proposals pass schema + policy before state change."""
        violations = []

        if not schema_valid:
            violations.append("Proposal fails schema validation")

        if not policy_valid:
            violations.append("Proposal violates domain policy")

        if violations:
            return (
                False,
                violations
                + ["Invalid proposal mutates nothing (I-06). Proposal discarded."],
            )

        return True, []

    @staticmethod
    def require_valid_proposal(
        schema_valid: bool, policy_valid: bool, proposal_source: str
    ) -> None:
        """Enforce I-06: reject invalid LLM output before mutation."""
        if proposal_source == "llm" and (not schema_valid or not policy_valid):
            raise ValueError(
                "Cannot apply LLM proposal: failed validation (I-06). "
                "No authoritative state changed."
            )


class LanguagePolicy:
    """Enforces I-07: neutral, diagnosis-free language."""

    FORBIDDEN_TERMS = [
        "hyperfocus",
        "rumination",
        "defective",
        "broken brain",
        "executive dysfunction",
        "disorder",
        "symptoms",
    ]

    @staticmethod
    def validate_neutral_language(text: str) -> tuple[bool, list[str]]:
        """Enforce I-07: no clinical labels, shame, or blame."""
        violations = []
        text_lower = text.lower()

        for term in LanguagePolicy.FORBIDDEN_TERMS:
            if term in text_lower:
                violations.append(f"Clinical/diagnostic term: '{term}'")

        shame_phrases = ["you should have", "you failed", "you're struggling with"]
        for phrase in shame_phrases:
            if phrase in text_lower:
                violations.append(f"Shame framing: '{phrase}'")

        if violations:
            return False, violations

        return True, []

    @staticmethod
    def require_neutral_language(text: str, context: str) -> None:
        """Enforce I-07: reject text with clinical/shame language."""
        valid, violations = LanguagePolicy.validate_neutral_language(text)
        if not valid:
            raise ValueError(
                f"Language policy violation (I-07) in {context}: "
                f"{'; '.join(violations)}. Use observable state and next move."
            )


class UntrustedContentPolicy:
    """Enforces I-13: instructions in repo/tool output stay data."""

    @staticmethod
    def is_trusted_source(source: str) -> bool:
        """Only user input is trusted command source."""
        return source == "user"

    @staticmethod
    def sanitize_untrusted_content(content: str, source: str) -> tuple[str, bool]:
        """Enforce I-13: treat non-user content as data."""
        if UntrustedContentPolicy.is_trusted_source(source):
            return content, True

        return content, False

    @staticmethod
    def require_trusted_for_command(source: str, command_type: str) -> None:
        """Enforce I-13: gates I-02/I-03/I-08 cannot be bypassed by content."""
        if not UntrustedContentPolicy.is_trusted_source(source):
            raise ValueError(
                f"Cannot execute {command_type} from untrusted source "
                f"'{source}' (I-13). "
                "Repository/tool content cannot bypass gates."
            )
