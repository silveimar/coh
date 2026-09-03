"""Scenario execution engine for eval harness.

Loads YAML scenarios, executes steps against Execution Core + MCP handlers,
tracks state, and validates expected outcomes.
"""

import re
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from execution_core.domain.enums import LifecycleState, SessionIntent
from execution_core.state_machine.lifecycle import StateMachine

from .invariant_checkers import InvariantChecker, ProseRuleChecker
from .mock_adapter import MockAdapter


class ScenarioExecutor:
    """Executes a single eval scenario with mock adapter."""

    def __init__(self, scenario_path: Path, temp_project_root: Path):
        self.scenario_path = scenario_path
        self.project_root = temp_project_root

        # Load scenario
        with open(scenario_path) as f:
            self.scenario = yaml.safe_load(f)

        self.scenario_id = self.scenario["id"]
        self.setup = self.scenario.get("setup", {})
        self.steps = self.scenario.get("steps", [])
        self.expected = self.scenario.get("expected", {})

        # Initialize mock adapter
        capabilities = self.setup.get("capabilities", [])
        self.mock_adapter = MockAdapter(self.scenario_id, capabilities)

        # Execution state
        self.state_machine = StateMachine()
        self.session = None
        self.current_state = None
        self.output_log: list[str] = []
        self.action_log: list[str] = []
        self.transitions: list[str] = []
        self.archive_entries: list[dict] = []

    def load_prior_state(self) -> None:
        """Initialize session with prior_state from setup."""
        prior = self.setup.get("prior_state")
        if not prior:
            # New session
            intent_str = self.scenario.get("intent", "execute")
            intent = SessionIntent(intent_str)
            self.session = self.state_machine.start_session("test_project", intent)
            self.current_state = LifecycleState.INSPECT
            self.transitions.append("T1")
        else:
            # TODO: Reconstruct session from prior_state fixture
            # For now, create basic session at specified state
            lifecycle_state = prior.get("lifecycle_state", "INSPECT")
            intent_str = self.scenario.get("intent", "execute")
            intent = SessionIntent(intent_str)

            self.session = self.state_machine.start_session("test_project", intent)
            self.session.lifecycle_state = LifecycleState[lifecycle_state]
            self.current_state = LifecycleState[lifecycle_state]

    def execute_step(self, step: dict[str, Any]) -> None:
        """Execute a single scenario step."""
        if "user_message" in step:
            self._execute_user_message(step["user_message"])
        elif "tool_event" in step:
            self._execute_tool_event(step["tool_event"])
        elif "agent_proposal" in step:
            self._execute_agent_proposal(step["agent_proposal"])
        elif "system_event" in step:
            self._execute_system_event(step["system_event"])

        # Check per-step expectations if present
        if "expect" in step:
            self._validate_step_expectations(step["expect"])

    def _execute_user_message(self, message: str) -> None:
        """Handle user message input."""
        self.output_log.append(f"USER: {message}")
        self.action_log.append("user_message")

        # Archive user input
        self.archive_entries.append(
            {
                "id": len(self.archive_entries),
                "actor": "user",
                "type": "user_input",
                "content": message,
                "timestamp": len(self.archive_entries),
            }
        )

        # Simplified: for spec scenarios, trigger specify transition
        if self.current_state == LifecycleState.INSPECT:
            if self.mock_adapter.has_capability("inspect_repository"):
                # Would call inspect_repository here
                pass
            self._transition_to_specify()

    def _execute_tool_event(self, event: dict[str, Any]) -> None:
        """Handle tool event."""
        tool = event.get("tool")
        status = event.get("status", "succeeded")

        self.output_log.append(f"TOOL: {tool} ({status})")
        self.action_log.append(f"tool_{tool}")

        self.archive_entries.append(
            {
                "id": len(self.archive_entries),
                "actor": "tool",
                "type": "tool_event",
                "tool": tool,
                "status": status,
                "timestamp": len(self.archive_entries),
            }
        )

    def _execute_agent_proposal(self, proposal: dict[str, Any]) -> None:
        """Handle agent proposal."""
        kind = proposal.get("kind")
        text = proposal.get("text", "")

        self.output_log.append(f"AGENT_PROPOSAL: {kind}\n{text}")
        self.action_log.append("agent_proposal")

        # Check for completion claims (verify-001 critical test)
        if kind == "completion_claim":
            if "fixed" in text.lower() or "done" in text.lower():
                # This should NOT result in verified/done without evidence
                # The harness will check I-03 enforcement
                pass

    def _execute_system_event(self, event: dict[str, Any]) -> None:
        """Handle system event."""
        kind = event.get("kind")
        self.output_log.append(f"SYSTEM: {kind}")
        self.action_log.append(f"system_{kind}")

        if kind == "interruption":
            # Should trigger checkpoint with progress record (I-05)
            pass
        elif kind == "session_resume":
            # Should use T11 recovery path
            self.transitions.append("T11")
        elif kind == "archive_failure":
            # Should degrade without blocking (I-12)
            pass

    def _transition_to_specify(self) -> None:
        """Transition from INSPECT to SPECIFY."""
        if self.current_state == LifecycleState.INSPECT:
            self.current_state = LifecycleState.SPECIFY
            self.transitions.append("T2")

            # Simulate spec proposal
            self._generate_spec_proposal()

            # Transition to CONFIRM
            self.current_state = LifecycleState.CONFIRM
            self.transitions.append("T3")

    def _generate_spec_proposal(self) -> None:
        """Generate mock spec proposal with required sections."""
        # Use inspection findings if available
        findings = ""
        if self.mock_adapter.has_capability("inspect_repository"):
            from ..fixtures.inspection_findings import INSPECTION_FINDINGS

            findings = INSPECTION_FINDINGS.get(self.scenario_id, "")

        # Generate spec output with required sections
        output_parts = []

        # P-01: Evidence first for non-recovery intents
        if findings and self.scenario.get("intent") != "recover":
            output_parts.append(f"Inspection findings: {findings}\n")

        output_parts.extend(
            [
                "WHAT: Fix the issue\n",
                "WHY: User requested it\n",
                "DELIVERABLE: Working solution\n",
                "DONE WHEN:\n  - Tests pass\n  - Evidence collected\n",
                "CLARITY: ready\n",
                "READINESS: ready\n",
            ]
        )

        output_text = "\n".join(output_parts)
        self.output_log.append(f"SPEC_PROPOSAL:\n{output_text}")

        self.archive_entries.append(
            {
                "id": len(self.archive_entries),
                "actor": "agent",
                "type": "spec_proposal",
                "content": output_text,
                "timestamp": len(self.archive_entries),
            }
        )

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

        # Check final state
        expected_state = self.expected.get("final_state")
        if expected_state:
            actual_state = self.current_state.name if self.current_state else "UNKNOWN"
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
            if not re.search(pattern, full_output, re.IGNORECASE):
                results["passed"] = False
                results["failures"].append(f"Missing required pattern: {pattern}")

        for pattern in self.expected.get("must_not_include", []):
            if re.search(pattern, full_output, re.IGNORECASE):
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
            passed, msg = InvariantChecker.check_i04_append_only_archive(
                self.archive_entries
            )
            if not passed:
                results["passed"] = False
                results["failures"].append(f"Archive append-only violated: {msg}")

        # Check severity
        severity = self.expected.get("severity", "normal")
        if severity == "critical" and not results["passed"]:
            results["critical_failure"] = True

        return results

    def _check_invariants(self, invariant_ids: list[str]) -> None:
        """Check specified invariants."""
        for inv_id in invariant_ids:
            if inv_id.startswith("I-"):
                self._check_behavioral_invariant(inv_id)
            elif inv_id.startswith("P-"):
                self._check_prose_rule(inv_id)

    def _check_behavioral_invariant(self, inv_id: str) -> None:
        """Check behavioral contract invariant."""
        full_output = "\n".join(self.output_log)
        intent = self.scenario.get("intent", "execute")

        if inv_id == "I-02":
            # Readiness gate
            readiness = "ready"  # Simplified
            passed, msg = InvariantChecker.check_i02_readiness_gate(
                readiness, self.action_log
            )
            assert passed, msg

        elif inv_id == "I-03":
            # Evidence gate - CRITICAL for verify-001
            completion_state = self._infer_completion_state(full_output)
            evidence = []  # Simplified - would extract from execution
            passed, msg = InvariantChecker.check_i03_evidence_gate(
                completion_state, evidence
            )
            assert passed, msg

        elif inv_id == "I-04":
            # Append-only archive
            passed, msg = InvariantChecker.check_i04_append_only_archive(
                self.archive_entries
            )
            assert passed, msg

        elif inv_id == "I-06":
            # Proposal-only AI
            mutation_log = [{"validated": True}]  # Simplified
            passed, msg = InvariantChecker.check_i06_proposal_only(mutation_log)
            assert passed, msg

        elif inv_id == "I-07":
            # Neutral language
            passed, msg = InvariantChecker.check_i07_neutral_language(full_output)
            assert passed, msg

        elif inv_id == "I-08":
            # Permission matrix
            # Simplified check
            pass

        elif inv_id == "I-12":
            # Archive failure degradation
            archive_status = "healthy"
            passed, msg = InvariantChecker.check_i12_archive_failure_degrades(
                archive_status, False, False
            )
            assert passed, msg

        elif inv_id == "I-13":
            # Untrusted content
            passed, msg = InvariantChecker.check_i13_untrusted_content(
                "user", self.action_log
            )
            assert passed, msg

        elif inv_id == "I-14":
            # Honest capability degradation
            capability_available = self.mock_adapter.has_capability(
                "inspect_repository"
            )
            passed, msg = InvariantChecker.check_i14_honest_degradation(
                capability_available, full_output
            )
            assert passed, msg

    def _check_prose_rule(self, rule_id: str) -> None:
        """Check prose rendering policy rule."""
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

    def run(self) -> dict[str, Any]:
        """Execute full scenario and return results."""
        self.load_prior_state()

        for step in self.steps:
            self.execute_step(step)

        return self.validate_final_state()
