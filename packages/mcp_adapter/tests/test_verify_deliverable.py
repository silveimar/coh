"""Tests for verify_deliverable criterion accounting (I-03)."""

from pathlib import Path

import pytest

from coh_mcp.handlers import COHHandlers

CRITERIA = [f"Test {i} passes" for i in range(5)]


@pytest.fixture
def handlers(tmp_path: Path) -> COHHandlers:
    """Create handlers with persistence for testing."""
    return COHHandlers(tmp_path)


async def _session_in_verify(handlers: COHHandlers) -> str:
    result = await handlers.create_session("test-project", "Check verification")
    session_id = result[0]["text"].split("\n")[0].split(": ")[1]
    await handlers.specify_work(
        session_id,
        what="Synthetic change",
        why="Verify accounting",
        deliverable="Code",
        done_when=CRITERIA,
    )
    await handlers.confirm_spec(session_id, confirmed=True)
    await handlers.plan_work(
        session_id,
        tasks=[
            {
                "name": "Implement",
                "action_literal": "Implement change",
                "done_when_condition": "Test passes",
                "estimated_minutes": 10,
                "energy": "low",
                "activation_friction": "low",
                "dependencies": [],
            }
        ],
    )
    await handlers.execute_task(session_id)
    return session_id


def _evidence(criterion: str, authority: str, result: str) -> dict[str, str]:
    return {
        "criterion_text": criterion,
        "evidence_type": "test",
        "authority": authority,
        "result": result,
        "summary": f"Synthetic {result}",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("authority", "result", "status"),
    [
        ("tool_verified", "fail", "1 evidence item(s) failed or inconclusive"),
        ("tool_verified", "inconclusive", "1 evidence item(s) failed or inconclusive"),
        ("agent_reported", "pass", "Evidence lacks sufficient authority"),
    ],
)
async def test_non_qualifying_evidence_is_not_counted(
    handlers: COHHandlers, authority: str, result: str, status: str
):
    """Recorded but non-qualifying evidence never counts as satisfied."""
    session_id = await _session_in_verify(handlers)

    output = await handlers.verify_deliverable(
        session_id,
        evidence_list=[_evidence(c, authority, result) for c in CRITERIA],
    )
    text = output[0]["text"]

    assert "CRITERIA_STATUS: 0/5" in text
    assert f"- {CRITERIA[0]}: {status}" in text
    assert ": satisfied" not in text
    assert "work complete" not in text
    assert "Completion state: done" not in text


@pytest.mark.asyncio
async def test_partial_qualifying_evidence_counts_only_passes(handlers: COHHandlers):
    """Only qualifying evidence counts; the recap names the failing criteria."""
    session_id = await _session_in_verify(handlers)
    evidence = [_evidence(c, "tool_verified", "pass") for c in CRITERIA[:3]]
    evidence.append(_evidence(CRITERIA[3], "tool_verified", "fail"))

    output = await handlers.verify_deliverable(session_id, evidence_list=evidence)
    text = output[0]["text"]

    assert "CRITERIA_STATUS: 3/5" in text
    assert f"- {CRITERIA[3]}: 1 evidence item(s) failed or inconclusive" in text
    assert f"- {CRITERIA[4]}: No evidence recorded" in text
    assert "2 criteria fails" in text
    assert "work complete" not in text


@pytest.mark.asyncio
async def test_all_qualifying_evidence_reports_complete(handlers: COHHandlers):
    """All criteria with qualifying evidence: T9, 5/5 and work complete."""
    session_id = await _session_in_verify(handlers)

    output = await handlers.verify_deliverable(
        session_id,
        evidence_list=[_evidence(c, "tool_verified", "pass") for c in CRITERIA],
    )
    text = output[0]["text"]

    assert "VERIFY → COMPLETE" in text
    assert "CRITERIA_STATUS: 5/5" in text
    assert "Completion state: done" in text
    assert "work complete" in text
