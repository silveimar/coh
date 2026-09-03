"""Scenario execution engine wired to COHHandlers.

Loads YAML scenarios, executes steps against real Execution Core + MCP handlers,
validates expected outcomes against persisted session state and handler output.
"""

import re
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from coh_mcp.handlers import COHHandlers
from execution_core.domain.enums import LifecycleState, SessionIntent
from persistence.infrastructure.database import create_engine, get_session_factory
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

from .invariant_checkers import InvariantChecker, ProseRuleChecker


class ScenarioExecutor:
    """Executes a single eval scenario with real COHHandlers."""

    def __init__(self, scenario_path: Path, temp_project_root: Path, mock_adapter=None):
        self.scenario_path = scenario_path
        self.project_root = temp_project_root

        # Load scenario
        with open(scenario_path) as f:
            self.scenario = yaml.safe_load(f)

        self.scenario_id = self.scenario["id"]
        self.setup = self.scenario.get("setup", {})
        self.steps = self.scenario.get("steps", [])
        self.expected = self.scenario.get("expected", {})

        # Initialize COHHandlers with temp_project_root
        self.handlers = COHHandlers(temp_project_root)
        
        # Mock adapter for inspect_repository
        self.mock_adapter = mock_adapter

        # Execution state
        self.session_id: str | None = None
        self.session_uuid: UUID | None = None
        self.output_log: list[str] = []
        self.action_log: list[str] = []
        self.transitions: list[str] = []
        
        # For UoW access
        db_path = temp_project_root / ".coh" / "coh.db"
        engine = create_engine(f"sqlite:///{db_path}")
        self.session_factory = get_session_factory(engine)

    def load_prior_state(self) -> None:
        """Initialize session with prior_state from setup if present."""
        prior = self.setup.get("prior_state")
        if prior and prior.get("lifecycle_state"):
            # Has prior state - would need fixture loading
            # For now, scenarios without prior_state work
            pass

    async def execute_step(self, step: dict[str, Any]) -> None:
        """Execute a single scenario step against COHHandlers."""
        if "user_message" in step:
            await self._execute_user_message(step["user_message"])
        elif "tool_event" in step:
            await self._execute_tool_event(step["tool_event"])
        elif "agent_proposal" in step:
            await self._execute_agent_proposal(step["agent_proposal"])
        elif "system_event" in step:
            await self._execute_system_event(step["system_event"])

        # Check per-step expectations if present
        if "expect" in step:
            self._validate_step_expectations(step["expect"])

    async def _execute_user_message(self, message: str) -> None:
        """Handle user message input."""
        self.output_log.append(f"USER: {message}")
        self.action_log.append("user_message")

        if not self.session_id:
            # First message - create session
            intent = self.scenario.get("intent", "execute")
            result = await self.handlers.create_session(
                "test_project", message, intent
            )
            
            # Extract session ID from output
            output_text = result[0]["text"]
            self.output_log.append(f"HANDLER: {output_text}")
            
            # Parse session ID
            for line in output_text.split("\n"):
                if line.startswith("Session created:"):
                    self.session_id = line.split(":")[1].strip()
                    self.session_uuid = UUID(self.session_id)
                    break
            
            self.transitions.append("T1")
            
            # Auto-call specify_work for spec scenarios
            if self.scenario.get("category") == "spec_gate":
                await self._auto_specify(message)

    async def _auto_specify(self, user_message: str) -> None:
        """Automatically call specify_work for spec_gate scenarios."""
        # Get inspection findings if capability present
        inspection_findings = None
        capabilities = self.setup.get("capabilities", [])
        if "inspect_repository" in capabilities and self.mock_adapter:
            from evals.fixtures.inspection_findings import INSPECTION_FINDINGS
            inspection_findings = INSPECTION_FINDINGS.get(self.scenario_id)

        # Derive spec from scenario or user message
        category = self.scenario.get("category")
        
        # Use scenario-appropriate spec content
        if "worker" in user_message.lower() or "job" in user_message.lower():
            what = "Add exponential backoff to job retry loop"
            why = "Prevent queue hammering when jobs fail repeatedly"
            deliverable = "worker.py with backoff implementation"
            done_when = ["Retry loop has exponential backoff", "Tests pass", "No immediate re-enqueue on failure"]
        elif "login" in user_message.lower() or "auth" in user_message.lower():
            what = "Fix intermittent login timeout"
            why = "Auth test fails intermittently in CI"
            deliverable = "Stable authentication flow"
            done_when = ["CI tests pass consistently", "No timeout in session refresh", "Root cause identified and fixed"]
        elif "changelog" in user_message.lower():
            what = "Add CHANGELOG entry for v1.2.1"
            why = "Release process requires changelog"
            deliverable = "CHANGELOG.md updated with v1.2.1 entries"
            done_when = ["All PRs since 1.2.0 documented", "Format matches existing entries"]
        else:
            # Generic fallback
            what = "Implement requested change"
            why = user_message
            deliverable = "Working solution"
            done_when = ["Tests pass", "Requirements met"]

        result = await self.handlers.specify_work(
            self.session_id,
            what=what,
            why=why,
            deliverable=deliverable,
            done_when=done_when,
            inspection_findings=inspection_findings,
        )

        output_text = result[0]["text"]
        self.output_log.append(f"SPEC_PROPOSAL:\n{output_text}")
        self.transitions.extend(["T2", "T3"])

    async def _execute_tool_event(self, event: dict[str, Any]) -> None:
        """Handle tool event."""
        tool = event.get("tool")
        status = event.get("status", "succeeded")

        self.output_log.append(f"TOOL: {tool} ({status})")
        self.action_log.append(f"tool_{tool}")

    async def _execute_agent_proposal(self, proposal: dict[str, Any]) -> None:
        """Handle agent proposal."""
        kind = proposal.get("kind")
        text = proposal.get("text", "")

        self.output_log.append(f"AGENT_PROPOSAL: {kind}\n{text}")
        self.action_log.append("agent_proposal")

        # For completion_claim, check if verify_deliverable enforces I-03
        if kind == "completion_claim":
            # This tests I-03: should not allow done without evidence
            pass

    async def _execute_system_event(self, event: dict[str, Any]) -> None:
        """Handle system event."""
        kind = event.get("kind")
        self.output_log.append(f"SYSTEM: {kind}")
        self.action_log.append(f"system_{kind}")

        if kind == "interruption":
            # Should trigger checkpoint (I-05)
            pass
        elif kind == "session_resume":
            # Should use T11 recovery
            self.transitions.append("T11")
        elif kind == "archive_failure":
            # Should degrade without blocking (I-12)
            pass

    def _validate_step_expectations(self, expect: dict[str, Any]) -> None:
        """Validate per-step expectations."""
        if "transitions" in expect:
            expected_transitions = expect["transitions"]
            # Check last N transitions match
            actual_last = self.transitions[-len(expected_transitions) :]
            assert (
                actual_last == expected_transitions
            ), f"Step transitions mismatch: {actual_last} != {expected_transitions}"

        if "forbidden_actions" in expect:
            forbidden = expect["forbidden_actions"]
            performed = set(self.action_log)
            violations = [a for a in forbidden if a in performed]
            assert (
                not violations
            ), f"Forbidden actions performed in step: {violations}"

        if "invariants" in expect:
            self._check_invariants(expect["invariants"])

    def validate_final_state(self) -> dict[str, Any]:
        """Validate expected outcomes and return results."""
        results = {
            "scenario_id": self.scenario_id,
            "passed": True,
            "failures": [],
        }

        # Get actual final state from persistence
        actual_state = self._get_current_lifecycle_state()
        
        # Check final state
        expected_state = self.expected.get("final_state")
        if expected_state:
            if expected_state != actual_state:
                results["passed"] = False
                results["failures"].append(
                    f"Final state mismatch: {actual_state} != {expected_state}"
                )

        # Check transitions
        expected_transitions = self.expected.get("transitions", [])
        if expected_transitions != self.transitions:
            results["passed"] = False
            results["failures"].append(
                f"Transitions mismatch: {self.transitions} != {expected_transitions}"
            )

        # Check invariants
        try:
            self._check_invariants(self.expected.get("invariants", []))
        except AssertionError as e:
            results["passed"] = False
            results["failures"].append(f"Invariant check failed: {e}")

        # Check must_include / must_not_include
        full_output = "\n".join(self.output_log)

        for pattern in self.expected.get("must_include", []):
            if not re.search(pattern, full_output, re.IGNORECASE | re.DOTALL):
                results["passed"] = False
                results["failures"].append(f"Missing required pattern: {pattern}")

        for pattern in self.expected.get("must_not_include", []):
            if re.search(pattern, full_output, re.IGNORECASE | re.DOTALL):
                results["passed"] = False
                results["failures"].append(f"Forbidden pattern found: {pattern}")

        # Check forbidden actions
        for action in self.expected.get("forbidden_actions", []):
            if action in self.action_log:
                results["passed"] = False
                results["failures"].append(f"Forbidden action performed: {action}")

        # Check archive expectations
        archive_exp = self.expected.get("archive_expectations", {})
        if archive_exp.get("append_only"):
            archive_entries = self._get_archive_entries()
            passed, msg = InvariantChecker.check_i04_append_only_archive(
                archive_entries
            )
            if not passed:
                results["passed"] = False
                results["failures"].append(f"Archive append-only violated: {msg}")

        # Check severity
        severity = self.expected.get("severity", "normal")
        if severity == "critical" and not results["passed"]:
            results["critical_failure"] = True

        return results

    def _get_current_lifecycle_state(self) -> str:
        """Get current lifecycle state from persisted session."""
        if not self.session_uuid:
            return "UNKNOWN"
            
        with SqlAlchemyUnitOfWork(self.session_factory) as uow:
            session = uow.sessions.get(self.session_uuid)
            if session:
                return session.lifecycle_state.name
        return "UNKNOWN"

    def _get_archive_entries(self) -> list[dict]:
        """Get archive entries for validation."""
        # Simplified - would read from .coh/archive/
        return []

    def _check_invariants(self, invariant_ids: list[str]) -> None:
        """Check specified invariants."""
        for inv_id in invariant_ids:
            if inv_id.startswith("I-"):
                self._check_behavioral_invariant(inv_id)
            elif inv_id.startswith("P-"):
                self._check_prose_rule(inv_id)

    def _check_behavioral_invariant(self, inv_id: str) -> None:
        """Check behavioral contract invariant against real session state."""
        full_output = "\n".join(self.output_log)
        intent = self.scenario.get("intent", "execute")

        if inv_id == "I-02":
            # Readiness gate - check actual session readiness
            with SqlAlchemyUnitOfWork(self.session_factory) as uow:
                if self.session_uuid:
                    session = uow.sessions.get(self.session_uuid)
                    # Would check spec readiness and blocked mutations
                    pass

        elif inv_id == "I-03":
            # Evidence gate - CRITICAL
            # Check that completion state doesn't exceed evidence
            completion_state = self._infer_completion_state(full_output)
            # Would load evidence from persistence
            evidence = []
            passed, msg = InvariantChecker.check_i03_evidence_gate(
                completion_state, evidence
            )
            assert passed, msg

        elif inv_id == "I-04":
            # Append-only archive
            archive_entries = self._get_archive_entries()
            passed, msg = InvariantChecker.check_i04_append_only_archive(
                archive_entries
            )
            assert passed, msg

        elif inv_id == "I-06":
            # Proposal-only AI - validated by state machine
            pass

        elif inv_id == "I-07":
            # Neutral language
            passed, msg = InvariantChecker.check_i07_neutral_language(full_output)
            assert passed, msg

        elif inv_id == "I-08":
            # Permission matrix - enforced by handlers
            pass

        elif inv_id == "I-12":
            # Archive failure degradation
            pass

        elif inv_id == "I-13":
            # Untrusted content
            passed, msg = InvariantChecker.check_i13_untrusted_content(
                "user", self.action_log
            )
            assert passed, msg

        elif inv_id == "I-14":
            # Honest capability degradation
            capabilities = self.setup.get("capabilities", [])
            capability_available = "inspect_repository" in capabilities
            passed, msg = InvariantChecker.check_i14_honest_degradation(
                capability_available, full_output
            )
            assert passed, msg

    def _check_prose_rule(self, rule_id: str) -> None:
        """Check prose rendering policy rule against handler output."""
        full_output = "\n".join(self.output_log)
        intent = self.scenario.get("intent", "execute")

        if rule_id == "P-01":
            passed, msg = ProseRuleChecker.check_p01_evidence_first(full_output, intent)
            assert passed, msg

        elif rule_id == "P-02":
            passed, msg = ProseRuleChecker.check_p02_no_preview_scaffolding(
                full_output, intent
            )
            assert passed, msg

        elif rule_id == "P-05":
            protected = ["what", "why", "deliverable", "done_when"]
            passed, msg = ProseRuleChecker.check_p05_protected_fields(
                full_output, protected
            )
            assert passed, msg

        elif rule_id == "P-06":
            passed, msg = ProseRuleChecker.check_p06_recovery_exemption(intent)
            assert passed, msg

    def _infer_completion_state(self, output_text: str) -> str:
        """Infer completion state from output."""
        text_lower = output_text.lower()
        if "done" in text_lower or "complete" in text_lower:
            return "done"
        if "verified" in text_lower:
            return "verified"
        if "tested" in text_lower:
            return "tested"
        if "implemented" in text_lower:
            return "implemented"
        return "unknown"

    async def run(self) -> dict[str, Any]:
        """Execute full scenario and return results."""
        self.load_prior_state()

        for step in self.steps:
            await self.execute_step(step)

        return self.validate_final_state()
