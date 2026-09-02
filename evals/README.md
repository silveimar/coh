# COH Behavioral Eval Suite

**Suite version:** 1.0.0 · targets Behavioral Contract 1.0.0 · 15 scenarios
In the future repo this directory becomes `evals/` at the monorepo root; the pytest harness (Phase 1/2) loads every `scenarios/*.yaml` and executes its steps against the Execution Core + a mock adapter.

## Layout

```
evals/
├── README.md                 # this file
├── schema/
│   └── scenario.schema.yaml  # scenario file format (documented schema)
├── scenarios/                # one file per scenario, ID-prefixed
└── results/                  # append-only run records (created by the harness)
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

## Rules

- Scenario files are versioned; behavior changes require bumping `version` and noting why in the scenario's `notes`.
- Every `expected.invariants` entry must be an I-nn defined in `../COH-Behavioral-Contract.md`.
- Assertions marked `severity: critical` map to the rubric's block-release gates (I-02, I-03, I-08, I-13).
- The harness must run scenarios with a deterministic mock adapter and recorded fixtures — never live provider calls in CI.
- Rubric scoring of scenario outputs: see `../COH-Eval-Rubric.md`.
