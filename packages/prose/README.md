# COH Prose

Prose rendering policy for COH. The package checks and renders the free prose that the agent shows around the structured output blocks: inspection findings, rationale, recommendations and decision narration. It implements rules P-01 to P-06 from section 5 of [docs/behavioral-contract.md](../../docs/behavioral-contract.md).

Distribution `prose`, import `coh_prose`. Source: `packages/prose/src/coh_prose/` (`policy.py`, `renderer.py`, `__init__.py`).

## Rules

| Rule | Where it lives |
|---|---|
| P-01 Evidence before conclusion | `ProsePolicy.validate_evidence_first`. `ProseRenderer.render_spec_proposal` puts the inspection findings before the WHAT/WHY/DELIVERABLE/DONE WHEN block. |
| P-02 No prospective scaffolding | `ProsePolicy.validate_no_scaffolding`, which checks the phrase list `SCAFFOLDING_PHRASES`. |
| P-03 Retrospective consolidation | `ProsePolicy.validate_recap_threshold` (threshold `ProseConfig.recap_threshold_lines`, default 12) and `ProseRenderer.add_recap_if_needed`. |
| P-04 Density | Only the flag `ProseConfig.enable_density`; there is no validation method. Section 5 marks P-04 as eval-judged. |
| P-05 Protected fields | `ProtectedField`, `ProsePolicy.validate_protected_fields` and `ProsePolicy.guard_compression`, which returns the original text when a protected marker is dropped. |
| P-06 Precedence: orientation outranks | `ProsePolicy.is_recovery_or_foreground_exempt`. `ProsePolicy.validate` skips P-01 and P-02 for recovery and foreground contexts. Section 5 marks P-06 as eval-judged. |

## Public API

`coh_prose` exports ten names (`__all__` in `__init__.py`):

- Policy: `ProseConfig`, `ProsePolicy`, `ProseValidationResult`, `ProtectedField`.
- Renderer: `ProseRenderer` and the block models `SpecProposal`, `ExecutionForeground`, `RecoverySummary`, `VerificationResult`, `DetourRecommendation`.

The MCP adapter is the consumer: `packages/mcp_adapter/src/coh_mcp/handlers.py` renders spec proposals, recovery summaries, execution foregrounds and verification results through `ProseRenderer`.

## Usage

```python
from coh_prose import ProsePolicy, ProseRenderer, SpecProposal

spec = SpecProposal(
    inspection_findings="Inspection: the export command writes no header row.",
    what="Add a header row to the CSV export",
    why="Downstream imports expect column names",
    deliverable="CSV export with a header row",
    done_when=["The first line of the export lists the column names"],
    clarity="high",
    readiness="ready",
)

# P-01: the inspection findings render before the spec block
print(ProseRenderer().render_spec_proposal(spec))

# P-02: preview phrasing is reported as a violation
print(ProsePolicy().validate_no_scaffolding("There are three things to cover."))
```

The last line prints `valid=False` with one P-02 violation for the phrase "there are".

## Testing

```bash
# From the repository root
uv run pytest tests/packages/prose
```

## Dependencies

- `pydantic>=2.9.0`
