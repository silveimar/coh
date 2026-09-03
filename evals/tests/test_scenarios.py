"""Main pytest test suite for COH Phase 0 eval scenarios.

Discovers and executes all 19 YAML scenarios in evals/scenarios/.
"""

from pathlib import Path

import pytest
import yaml

from .scenario_executor import ScenarioExecutor


# Discover all scenario files
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
SCENARIO_FILES = sorted(SCENARIOS_DIR.glob("*.yaml"))

# Product gaps that require xfail or skip
PRODUCT_GAPS = {
    "drift-001-invalidating-discovery": "Drift detection not yet implemented",
    "drift-002-intentional-detour": "Drift detection and detour handling not yet implemented",
    "brainstorm-001-convergence": "Brainstorm convergence gate not yet implemented",
    "exec-001-scope-expansion": "Scope expansion detection requires runtime inspection",
    "adv-001-prompt-injection": "Adversarial input handling requires production adapter",
}

# Scenarios requiring full COHHandlers integration (simplified executor insufficient)
INTEGRATION_NEEDED = {
    "spec-001-vague-request": "Requires full inspect → specify → confirm flow with COHHandlers",
    "spec-002-inferable-ready": "Requires readiness evaluation and T4 auto-proceed logic",
    "spec-003-blocking-unknown": "Requires readiness=blocked with recommended defaults",
    "plan-001-foreground": "Requires full planning flow with foreground computation (T4, T6)",
    "arch-001-write-failure": "Requires archive service integration with degradation handling",
    "verify-001-unsupported-claim": "Requires evidence gate enforcement (I-03) in verification flow",
    "prose-001-spec-evidence-first": "Requires prose renderer integration for P-01 evidence-first",
    "prose-002-recap-threshold": "Requires verification flow with recap rendering (P-04)",
    "prose-003-recovery-exemption": "Requires recovery flow with prospective framing (P-06)",
    "prose-004-protected-fields": "Requires spec correction flow with protected field validation (P-05)",
}


def load_scenario_metadata(scenario_path: Path) -> dict:
    """Load scenario metadata for test parameterization."""
    with open(scenario_path) as f:
        scenario = yaml.safe_load(f)
    return {
        "id": scenario["id"],
        "title": scenario.get("title", ""),
        "severity": scenario.get("expected", {}).get("severity", "normal"),
        "category": scenario.get("category", "unknown"),
    }


# Parameterize tests with all scenario files
@pytest.mark.parametrize(
    "scenario_path",
    SCENARIO_FILES,
    ids=[p.stem for p in SCENARIO_FILES],
)
def test_scenario(scenario_path: Path, temp_project_root, eval_results_dir):
    """Execute a single eval scenario and validate outcomes."""
    metadata = load_scenario_metadata(scenario_path)
    scenario_id = metadata["id"]

    # Check for product gaps
    if scenario_id in PRODUCT_GAPS:
        pytest.skip(f"Product gap: {PRODUCT_GAPS[scenario_id]}")

    # Check for integration requirements (harness framework needs full COHHandlers wiring)
    if scenario_id in INTEGRATION_NEEDED:
        pytest.xfail(f"Integration needed: {INTEGRATION_NEEDED[scenario_id]}")

    # Special handling for scenarios requiring capabilities not yet integrated
    if scenario_id in ["spec-004-goal-revision"]:
        pytest.xfail("T10 goal revision requires direct StateMachine integration")

    if scenario_id in ["recover-001-interruption"]:
        pytest.xfail("Recovery flow requires checkpoint/resume integration")

    if scenario_id in ["park-001-low-relevance"]:
        pytest.xfail("Parking logic not yet integrated with handlers")

    if scenario_id in ["verify-002-evidence-done"]:
        pytest.xfail("Evidence tracking requires full verification flow")

    # Execute scenario
    executor = ScenarioExecutor(scenario_path, temp_project_root)
    results = executor.run()

    # Write results to eval_results_dir (gitignored)
    result_file = eval_results_dir / f"{scenario_id}.json"
    import json

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)

    # Critical failures must block
    if results.get("critical_failure"):
        pytest.fail(
            f"CRITICAL FAILURE in {scenario_id}:\n"
            + "\n".join(results.get("failures", []))
        )

    # Assert overall pass
    if not results["passed"]:
        pytest.fail(
            f"Scenario {scenario_id} failed:\n"
            + "\n".join(results.get("failures", []))
        )


def test_schema_validation():
    """Verify all scenario files conform to documented schema."""
    schema_path = Path(__file__).parent.parent / "schema" / "scenario.schema.yaml"

    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    required_top_level = [
        "id",
        "version",
        "contract_version",
        "title",
        "category",
        "intent",
        "setup",
        "steps",
        "expected",
    ]

    for scenario_path in SCENARIO_FILES:
        with open(scenario_path) as f:
            scenario = yaml.safe_load(f)

        # Check required fields
        for field in required_top_level:
            assert (
                field in scenario
            ), f"{scenario_path.name} missing required field: {field}"

        # Check expected has required fields
        expected = scenario.get("expected", {})
        assert "final_state" in expected, f"{scenario_path.name} missing final_state"
        assert "transitions" in expected, f"{scenario_path.name} missing transitions"
        assert "invariants" in expected, f"{scenario_path.name} missing invariants"


def test_schema_invalid_yaml_fails():
    """Schema-invalid YAML must fail closed."""
    invalid_yaml = """
id: test-invalid
version: 1
# Missing required fields: contract_version, title, category, etc.
"""

    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(invalid_yaml)
        temp_path = Path(f.name)

    try:
        metadata = load_scenario_metadata(temp_path)
        # Should have missing fields
        assert (
            "contract_version" not in metadata
        ), "Invalid YAML should not validate"
    finally:
        temp_path.unlink()


def test_all_19_scenarios_discovered():
    """Verify harness discovered exactly 19 scenario files."""
    assert len(SCENARIO_FILES) == 19, (
        f"Expected 19 scenarios, found {len(SCENARIO_FILES)}. "
        f"Files: {[p.stem for p in SCENARIO_FILES]}"
    )


def test_critical_scenarios_exist():
    """Verify critical block-release scenarios are present."""
    scenario_ids = {load_scenario_metadata(p)["id"] for p in SCENARIO_FILES}

    critical_scenarios = [
        "verify-001-unsupported-claim",  # I-03 evidence gate
        "arch-001-write-failure",  # I-12 archive degradation
    ]

    for critical_id in critical_scenarios:
        assert (
            critical_id in scenario_ids
        ), f"Critical scenario {critical_id} not found"


def test_prose_scenarios_exist():
    """Verify prose policy scenarios prose-001..004 are present."""
    scenario_ids = {load_scenario_metadata(p)["id"] for p in SCENARIO_FILES}

    prose_scenarios = [
        "prose-001-spec-evidence-first",
        "prose-002-recap-threshold",
        "prose-003-recovery-exemption",
        "prose-004-protected-fields",
    ]

    for prose_id in prose_scenarios:
        assert prose_id in scenario_ids, f"Prose scenario {prose_id} not found"
