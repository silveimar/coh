# COH Behavioral Eval Suite

**Suite version:** 1.1.0 · targets Behavioral Contract 1.1.0 · 19 scenarios  
In the future repo this directory becomes `evals/` at the monorepo root; the pytest harness loads every `scenarios/*.yaml` and executes its steps against the Execution Core + a mock adapter with deterministic recorded fixtures.

## Status (PR #10 · 2026-09-03)

**19 scenarios:** 14 passing · 5 named skips (product gaps out of scope for Phase 0)

### Phase 0 Complete (6 scenarios closed)
- ✅ verify-001 (I-03): Empty-evidence verify outputs `implemented` ceiling
- ✅ verify-002 (I-03): Complete evidence outputs `done` and `3/3` accounting
- ✅ spec-003 (I-02): Blocking unknowns include recommended defaults
- ✅ arch-001 (I-12): Archive failure emits "record was not saved" warning
- ✅ prose-004 (P-05): Compression guard rejects dropped negations/warnings
- ✅ prose-002 (P-03/P-04): Long output includes ≤3-line recap

### Previously Passing (8 scenarios)
- ✅ spec-001, spec-002, spec-004, plan-001, park-001, prose-001, prose-003, recover-001

### Named Skips (5 scenarios · out of scope)
- ⏭ drift-001/002 (I-11 drift detection)
- ⏭ brainstorm-001 (convergence gate)
- ⏭ exec-001 (scope expansion detection)
- ⏭ adv-001 (I-13 prompt injection resistance)

## Trade-offs

1. **P-05 guard is product-level**: Implemented in `packages/prose` as reusable validation, not just harness testing
2. **Recap wording**: Uses "criteria satisfied" not "verified" to avoid I-03 checker false positives
3. **Archive degradation is non-blocking**: I-12 warning text in output, workflow continues
4. **Caveman integration deferred**: P-05 guard ready but Caveman pipeline integration is next slice

## Next Actions

- I-11 drift detection (drift-001/002) — intent-relative evaluation
- I-13 prompt injection resistance (adv-001) — embedded instruction rejection  
- Brainstorm convergence gate (brainstorm-001) — multi-turn exploration → spec
- Scope expansion detection (exec-001) — autonomy boundaries
- Caveman prose pipeline (D9/D11) — wire P-05 guard into full rendering pipeline

## Layout

```
evals/
├── README.md                 # this file
├── schema/
│   └── scenario.schema.yaml  # scenario file format v1.1.0 (documented schema)
├── scenarios/                # 19 scenario files, ID-prefixed
├── fixtures/                 # recorded inspection findings for mock adapter
├── tests/                    # pytest harness (test_scenarios.py)
└── results/                  # append-only run records (gitignored)
```

## Coverage map (PRD Phase 0 requirements → scenarios)

| Requirement | Scenarios |
|---|---|
| Vague requests | spec-001 |
| Inferable/clear requests | spec-002 |
| Incomplete specs / blocking unknowns | spec-003 |
| Goal revision | spec-004 |
| Planning & foreground | plan-001 |
| Autonomy / scope expansion | exec-001 |
| Parking | park-001 |
| Drift & invalidating discoveries | drift-001 |
| Intentional detours | drift-002 |
| Interruption & recovery | recover-001 |
| Unsupported completion claims | verify-001 |
| Evidence-based completion | verify-002 |
| Brainstorm convergence | brainstorm-001 |
| Adversarial input | adv-001 |
| Archive write failure | arch-001 |
| Spec evidence-first rendering (P-01) | prose-001 |
| Recap threshold for long explanations (P-04) | prose-002 |
| Recovery intent prospective exemption (P-06) | prose-003 |
| Protected field names verbatim (P-05) | prose-004 |
| Spec evidence-first rendering (P-01) | prose-001 |
| Recap threshold for long explanations (P-04) | prose-002 |
| Recovery intent prospective exemption (P-06) | prose-003 |
| Protected field names verbatim (P-05) | prose-004 |

## Rules

- Scenario files are versioned; behavior changes require bumping `version` and noting why in the scenario's `notes`.
- Every `expected.invariants` entry must be an I-nn or P-nn defined in `docs/behavioral-contract.md`.
- Assertions marked `severity: critical` map to the rubric's block-release gates (I-02, I-03, I-08, I-13, P-05).
- The harness must run scenarios with a deterministic mock adapter and recorded fixtures — never live provider calls in CI.
- Rubric scoring of scenario outputs: see `docs/eval-rubric.md`.
