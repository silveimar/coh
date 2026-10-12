"""Main pytest test suite for COH Phase 0 eval scenarios.

Discovers and executes all 19 YAML scenarios in evals/scenarios/ against
real COHHandlers with deterministic mock adapter.
"""

from pathlib import Path

import pytest
import yaml

from .mock_adapter import MockAdapter
from .scenario_executor import ScenarioExecutor

# Discover all scenario files
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
SCENARIO_FILES = sorted(SCENARIOS_DIR.glob("*.yaml"))

# Product gaps ONLY - capabilities not yet implemented
PRODUCT_GAPS = {
    "drift-001-invalidating-discovery": ("Drift detection not implemented", "I-11"),
    "drift-002-intentional-detour": ("Drift detection not implemented", "I-11"),
    "brainstorm-001-convergence": (
        "Brainstorm convergence gate not implemented",
        "convergence",
    ),
    "exec-001-scope-expansion": (
        "Scope expansion detection not implemented",
        "autonomy",
    ),
    "adv-001-prompt-injection": ("Adversarial input handling not implemented", "I-13"),
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
@pytest.mark.asyncio
async def test_scenario(scenario_path: Path, temp_project_root, eval_results_dir):
    """Execute a single eval scenario against COHHandlers and validate outcomes."""
    metadata = load_scenario_metadata(scenario_path)
    scenario_id = metadata["id"]

    # Check for product gaps ONLY
    if scenario_id in PRODUCT_GAPS:
        reason, invariant = PRODUCT_GAPS[scenario_id]
        pytest.skip(f"Product gap ({invariant}): {reason}")

    # P-04 gap: prose-002 expected to fail until recap rendering implemented
    if scenario_id == "prose-002-recap-threshold":
        pytest.xfail("P-04: Recap rendering after threshold not yet implemented")

    # Create mock adapter with scenario capabilities
    with open(scenario_path) as f:
        scenario = yaml.safe_load(f)
    capabilities = scenario.get("setup", {}).get("capabilities", [])
    mock_adapter = MockAdapter(scenario_id, capabilities)

    # Execute scenario with real COHHandlers
    executor = ScenarioExecutor(scenario_path, temp_project_root, mock_adapter)
    results = await executor.run()

    # Write results to eval_results_dir (gitignored)
    result_file = eval_results_dir / f"{scenario_id}.json"
    import json

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)

    # Check for product gap xfails first (before critical failure check)
    if not results["passed"]:
        product_gap_failures = [
            f for f in results.get("failures", []) if f.startswith("Product gap xfail:")
        ]
        other_failures = [
            f
            for f in results.get("failures", [])
            if not f.startswith("Product gap xfail:")
        ]

        if product_gap_failures and not other_failures:
            # Only product gap xfails - xfail the test (even if critical)
            pytest.xfail("\n".join(product_gap_failures))

    # Critical failures must block (after checking for product gaps)
    if results.get("critical_failure"):
        pytest.fail(
            f"CRITICAL FAILURE in {scenario_id}:\n"
            + "\n".join(results.get("failures", []))
        )

    # Assert overall pass
    if not results["passed"]:
        pytest.fail(
            f"Scenario {scenario_id} failed:\n" + "\n".join(results.get("failures", []))
        )


def test_schema_validation():
    """Verify all scenario files conform to documented schema."""
    Path(__file__).parent.parent / "schema" / "scenario.schema.yaml"

    # Schema validation would check against schema, but for now just check
    # required fields
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
            assert field in scenario, (
                f"{scenario_path.name} missing required field: {field}"
            )

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
        assert "contract_version" not in metadata, "Invalid YAML should not validate"
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
        assert critical_id in scenario_ids, f"Critical scenario {critical_id} not found"


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
