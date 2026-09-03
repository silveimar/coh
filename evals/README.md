# COH Behavioral Eval Suite

**Suite version:** 1.1.0 · targets Behavioral Contract 1.1.0 · 19 scenarios
In the future repo this directory becomes `evals/` at the monorepo root; the pytest harness loads every `scenarios/*.yaml` and executes its steps against the Execution Core + a mock adapter with deterministic recorded fixtures.

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
