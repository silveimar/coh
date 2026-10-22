# Phase 02 evidence (H-87)

Measured base: origin/main 0e93597. Starting HEAD: 4249bb8. CHECKS_SHA (lead checks commit): 915fd1e.

How the CONTEXT criteria are read on this branch (02-01-PLAN context section):

- Criterion 3: the expected test count is 199, the 189 tests that main has plus the 10 cases the lead checks commit 915fd1e adds.
- Criterion 4: the evidence covers the field each model actually defaults, 13 fields across 10 models, including `Evidence.recorded_at` and `Foreground.calculated_at`.
- Criterion 5: three gates. From the checks commit to HEAD, nothing changes outside the 11 source files and `.planning` (R20). On the whole branch, only author `COH lead seat` touches the protected set (R21). No added line in `packages/execution-core` carries a suppression comment (R22).

`<worktree>` stands for the checkout path of the slice worktree. Every command below ran with that path substituted.

## Baseline (origin/main 0e93597, checks commit 915fd1e, before edits)

R1 `git -C <worktree> rev-parse --short origin/main`

```text
0e93597
```

R2 `git -C <worktree> rev-parse --short HEAD`

```text
4249bb8
```

R3 `git -C <worktree> log --format='%h %s' origin/main..HEAD`

```text
4249bb8 docs(planning): Phase 2 plan (pyright clean execution-core)
915fd1e test(execution-core): guard naive UTC default timestamps (Phase 2 checks, D-06)
```

R4 `git -C <worktree> diff --name-only origin/main...HEAD -- . ':!.planning'`

```text
tests/packages/execution-core/domain/test_naive_utc_defaults.py
```

R5 `uv run --directory <worktree> pyright --outputjson packages/execution-core | jq -r '.generalDiagnostics[] | "\(.file | split("/") | .[-2:] | join("/")):\(.range.start.line + 1) \(.rule)"'`

```text
domain/decision.py:29 reportDeprecated
domain/evidence.py:33 reportDeprecated
domain/foreground.py:21 reportDeprecated
domain/parking_item.py:24 reportDeprecated
domain/session.py:21 reportDeprecated
domain/session.py:22 reportDeprecated
domain/specification.py:21 reportDeprecated
domain/specification.py:33 reportDeprecated
domain/specification.py:42 reportDeprecated
domain/specification.py:60 reportDeprecated
domain/specification.py:61 reportDeprecated
domain/task.py:41 reportDeprecated
domain/task.py:42 reportDeprecated
policies/integrity_policy.py:69 reportUnknownParameterType
policies/integrity_policy.py:69 reportMissingTypeArgument
policies/parking_policy.py:125 reportUnusedVariable
state_machine/lifecycle.py:69 reportUnknownParameterType
state_machine/lifecycle.py:71 reportMissingTypeArgument
```

R6 `uv run --directory <worktree> pyright --outputjson packages/execution-core | jq '.summary'`

```text
{
  "filesAnalyzed": 23,
  "errorCount": 18,
  "warningCount": 0,
  "informationCount": 0,
  "timeInSec": 0.597
}
```

R7 `uv run --directory <worktree> pyright --outputjson | jq '.summary.errorCount'`

```text
643
```

R8 `git -C <worktree> grep -n utcnow -- packages/execution-core/src`

```text
packages/execution-core/src/execution_core/domain/decision.py:29:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/evidence.py:33:    recorded_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/foreground.py:21:    calculated_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/parking_item.py:24:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/session.py:21:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/session.py:22:    updated_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/specification.py:21:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/specification.py:33:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/specification.py:42:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/specification.py:60:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/specification.py:61:    updated_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/task.py:41:    created_at: datetime = Field(default_factory=datetime.utcnow)
packages/execution-core/src/execution_core/domain/task.py:42:    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

R9 `uv run --directory <worktree> pytest tests/packages/execution-core -q -W error::DeprecationWarning --cov=packages/execution-core/src --tb=no -rN` (exit 1)

```text
FFFFFFFFFFFFFFFFFFFFFFFFFFFFF.....................FFFFF......F......FFFF [ 36%]
FFFFFFFFFFFF..FF.............FFFFFFFFFFFFFF.FFFFFFFFFFFFFFF............F [ 72%]
FFFFFFFFFFFFFFFFFFFFFFFFFF....FFFFFFFFFFFFFFFFFFFFFFF.F                  [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.15.0-final-0 ________________

Name                                                                       Stmts   Miss  Cover
----------------------------------------------------------------------------------------------
packages/execution-core/src/execution_core/__init__.py                         1      0   100%
packages/execution-core/src/execution_core/domain/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/domain/checkpoint.py               29      1    97%
packages/execution-core/src/execution_core/domain/commands.py                 33      8    76%
packages/execution-core/src/execution_core/domain/decision.py                 24      6    75%
packages/execution-core/src/execution_core/domain/enums.py                    77      0   100%
packages/execution-core/src/execution_core/domain/evidence.py                 24      9    62%
packages/execution-core/src/execution_core/domain/foreground.py               26     12    54%
packages/execution-core/src/execution_core/domain/parking_item.py             28      6    79%
packages/execution-core/src/execution_core/domain/session.py                  24      6    75%
packages/execution-core/src/execution_core/domain/specification.py            81     43    47%
packages/execution-core/src/execution_core/domain/task.py                     66     22    67%
packages/execution-core/src/execution_core/events/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/events/domain_events.py            47      0   100%
packages/execution-core/src/execution_core/policies/__init__.py                0      0   100%
packages/execution-core/src/execution_core/policies/completion_policy.py      68     51    25%
packages/execution-core/src/execution_core/policies/foreground_policy.py      56     34    39%
packages/execution-core/src/execution_core/policies/integrity_policy.py       73     11    85%
packages/execution-core/src/execution_core/policies/parking_policy.py         55     19    65%
packages/execution-core/src/execution_core/policies/permission_policy.py      44     10    77%
packages/execution-core/src/execution_core/policies/readiness_policy.py       43     32    26%
packages/execution-core/src/execution_core/state_machine/__init__.py           0      0   100%
packages/execution-core/src/execution_core/state_machine/lifecycle.py        179    134    25%
----------------------------------------------------------------------------------------------
TOTAL                                                                        978    404    59%
133 failed, 66 passed in 0.97s
```

R10 `uv run --directory <worktree> pytest tests/packages/execution-core -q --cov=packages/execution-core/src --disable-warnings`

```text
........................................................................ [ 36%]
........................................................................ [ 72%]
.......................................................                  [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.15.0-final-0 ________________

Name                                                                       Stmts   Miss  Cover
----------------------------------------------------------------------------------------------
packages/execution-core/src/execution_core/__init__.py                         1      0   100%
packages/execution-core/src/execution_core/domain/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/domain/checkpoint.py               29      1    97%
packages/execution-core/src/execution_core/domain/commands.py                 33      0   100%
packages/execution-core/src/execution_core/domain/decision.py                 24      0   100%
packages/execution-core/src/execution_core/domain/enums.py                    77      0   100%
packages/execution-core/src/execution_core/domain/evidence.py                 24      0   100%
packages/execution-core/src/execution_core/domain/foreground.py               26      6    77%
packages/execution-core/src/execution_core/domain/parking_item.py             28      6    79%
packages/execution-core/src/execution_core/domain/session.py                  24      0   100%
packages/execution-core/src/execution_core/domain/specification.py            81      0   100%
packages/execution-core/src/execution_core/domain/task.py                     66      3    95%
packages/execution-core/src/execution_core/events/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/events/domain_events.py            47      0   100%
packages/execution-core/src/execution_core/policies/__init__.py                0      0   100%
packages/execution-core/src/execution_core/policies/completion_policy.py      68      0   100%
packages/execution-core/src/execution_core/policies/foreground_policy.py      56      9    84%
packages/execution-core/src/execution_core/policies/integrity_policy.py       73     11    85%
packages/execution-core/src/execution_core/policies/parking_policy.py         55      0   100%
packages/execution-core/src/execution_core/policies/permission_policy.py      44      0   100%
packages/execution-core/src/execution_core/policies/readiness_policy.py       43      4    91%
packages/execution-core/src/execution_core/state_machine/__init__.py           0      0   100%
packages/execution-core/src/execution_core/state_machine/lifecycle.py        179      3    98%
----------------------------------------------------------------------------------------------
TOTAL                                                                        978     43    96%
199 passed, 1716 warnings in 0.33s
```

R11 `uv run --directory <worktree> coverage report --include='packages/execution-core/src/*' --fail-under=90` (exit 0)

```text
Name                                                                       Stmts   Miss  Cover
----------------------------------------------------------------------------------------------
packages/execution-core/src/execution_core/__init__.py                         1      0   100%
packages/execution-core/src/execution_core/domain/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/domain/checkpoint.py               29      1    97%
packages/execution-core/src/execution_core/domain/commands.py                 33      0   100%
packages/execution-core/src/execution_core/domain/decision.py                 24      0   100%
packages/execution-core/src/execution_core/domain/enums.py                    77      0   100%
packages/execution-core/src/execution_core/domain/evidence.py                 24      0   100%
packages/execution-core/src/execution_core/domain/foreground.py               26      6    77%
packages/execution-core/src/execution_core/domain/parking_item.py             28      6    79%
packages/execution-core/src/execution_core/domain/session.py                  24      0   100%
packages/execution-core/src/execution_core/domain/specification.py            81      0   100%
packages/execution-core/src/execution_core/domain/task.py                     66      3    95%
packages/execution-core/src/execution_core/events/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/events/domain_events.py            47      0   100%
packages/execution-core/src/execution_core/policies/__init__.py                0      0   100%
packages/execution-core/src/execution_core/policies/completion_policy.py      68      0   100%
packages/execution-core/src/execution_core/policies/foreground_policy.py      56      9    84%
packages/execution-core/src/execution_core/policies/integrity_policy.py       73     11    85%
packages/execution-core/src/execution_core/policies/parking_policy.py         55      0   100%
packages/execution-core/src/execution_core/policies/permission_policy.py      44      0   100%
packages/execution-core/src/execution_core/policies/readiness_policy.py       43      4    91%
packages/execution-core/src/execution_core/state_machine/__init__.py           0      0   100%
packages/execution-core/src/execution_core/state_machine/lifecycle.py        179      3    98%
----------------------------------------------------------------------------------------------
TOTAL                                                                        978     43    96%
```

R12 `uv run --directory <worktree> pytest tests/packages/execution-core/domain/test_naive_utc_defaults.py -q -W error::DeprecationWarning --tb=no -rN` (exit 1)

```text
FFFFFFFFFF                                                               [100%]
10 failed in 0.08s
```

R13 `uv run --directory <worktree> pytest tests/evals -q --disable-warnings`

```text
s.ssss.....x............                                                 [100%]
18 passed, 5 skipped, 1 xfailed, 142 warnings in 0.72s
```

R14 `uv run --directory <worktree> pytest tests/packages/persistence -q --disable-warnings`

```text
.........                                                                [100%]
9 passed, 29 warnings in 0.09s
```

R15 `uv run --directory <worktree> pytest -q --disable-warnings`

```text
.........s.ssss.....x................................................... [ 15%]
........................................................................ [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 77%]
........................................................................ [ 92%]
..................................                                       [100%]
460 passed, 5 skipped, 1 xfailed, 2257 warnings in 1.71s
```

R16 `uv run --directory <worktree> ruff check .`

```text
All checks passed!
```

R17 `uv run --directory <worktree> ruff format --check .` (172, not the planning-time 171: ruff counts the PLAN file committed after that measurement)

```text
172 files already formatted
```

R18 `git -C <worktree> grep -h -F 'datetime.now(UTC)' -- packages/execution-core/src ':!packages/execution-core/src/execution_core/domain/clock.py' | wc -l`

```text
25
```

R19 Command E1

```text
uv run --directory <worktree> python -c 'import os, re, time, warnings; os.environ["TZ"] = "JST-9"; time.tzset(); log = []; warnings.simplefilter("always"); warnings.showwarning = lambda message, category, *rest, **kw: log.append(category.__name__); from datetime import UTC, datetime; from uuid import uuid4; from execution_core.domain.decision import Decision; from execution_core.domain.enums import AssumptionClass, EvidenceAuthority, EvidenceResult, RelevanceLevel, SessionIntent; from execution_core.domain.evidence import Evidence; from execution_core.domain.foreground import Foreground; from execution_core.domain.parking_item import ParkingItem; from execution_core.domain.session import ExecutionSession; from execution_core.domain.specification import Assumption, DoneWhenCriterion, Specification, Unknown; from execution_core.domain.task import Task; from persistence.infrastructure.mappers import SpecificationMapper; now_utc = lambda: datetime.now(UTC).replace(tzinfo=None); t0 = now_utc(); cases = [("Task", Task(spec_id=uuid4(), spec_revision=1), ("created_at", "updated_at")), ("Evidence", Evidence(spec_id=uuid4(), spec_revision=1, criterion_id=uuid4(), evidence_type="test_run", authority=EvidenceAuthority.TOOL_VERIFIED, result=EvidenceResult.PASS, summary="synthetic summary", source="synthetic"), ("recorded_at",)), ("Decision", Decision(question="synthetic question", selected_option="a", rationale="synthetic rationale"), ("created_at",)), ("ParkingItem", ParkingItem(text="synthetic item", relevance=RelevanceLevel.LOW, suggested_disposition="revisit later"), ("created_at",)), ("ExecutionSession", ExecutionSession(project_id="synthetic-project", intent=SessionIntent.EXECUTE), ("created_at", "updated_at")), ("Foreground", Foreground(session_id=uuid4(), goal="synthetic goal"), ("calculated_at",)), ("Specification", Specification(what="synthetic what", why="synthetic why", deliverable="synthetic"), ("created_at", "updated_at")), ("DoneWhenCriterion", DoneWhenCriterion(text="synthetic criterion"), ("created_at",)), ("Assumption", Assumption(text="synthetic assumption", classification=AssumptionClass.SAFE), ("created_at",)), ("Unknown", Unknown(text="synthetic unknown", blocking=False), ("created_at",))]; spec = Specification(what="synthetic what", why="synthetic why", deliverable="synthetic", done_when=[DoneWhenCriterion(text="synthetic criterion")], assumptions=[Assumption(text="synthetic assumption", classification=AssumptionClass.SAFE)], unknowns=[Unknown(text="synthetic unknown", blocking=False)]); row = SpecificationMapper.to_model(spec); t1 = now_utc(); shape = lambda s: re.sub("[0-9]", "9", s); offset_free = lambda s: re.search("([+-][0-9][0-9]:[0-9][0-9]|Z)$", s) is None; print("process_tz:", time.tzname[0], "local_minus_utc_hours:", round((datetime.now() - now_utc()).total_seconds() / 3600, 1)); print("\n".join(f"{name}.{field} tzinfo={getattr(m, field).tzinfo} offset_free={offset_free(getattr(m, field).isoformat())} utc_wall_clock={t1 >= getattr(m, field) >= t0} iso_shape={shape(getattr(m, field).isoformat())}" for name, m, fields in cases for field in fields)); stored = [("done_when", row.done_when[0]["created_at"]), ("assumptions", row.assumptions[0]["created_at"]), ("unknowns", row.unknowns[0]["created_at"])]; print("\n".join(f"specifications.{col}[0].created_at stored={shape(s)} offset_free={offset_free(s)}" for col, s in stored)); print("defaulted_fields:", sum(len(f) for _, _, f in cases)); print("deprecation_warnings:", log.count("DeprecationWarning"))'
```

```text
process_tz: JST local_minus_utc_hours: 9.0
Task.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Task.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Evidence.recorded_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Decision.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ParkingItem.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ExecutionSession.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ExecutionSession.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Foreground.calculated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Specification.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Specification.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
DoneWhenCriterion.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Assumption.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Unknown.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
specifications.done_when[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
specifications.assumptions[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
specifications.unknowns[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
defaulted_fields: 13
deprecation_warnings: 18
```

Precondition check (Task 1 Step B): every baseline output matches the plan. R5 lists the 18 diagnostics at the planned sites, R9 fails (133 failed, 66 passed), R10 reports 199 passed, R11 exits 0, R12 reports 10 failed, R13 to R17 pass, and E1 prints 13 field lines and 3 stored lines, all True, with 18 DeprecationWarnings.

Tracer checkpoint (Task 1 edits only, code commit 80cf663): pyright on packages/execution-core reports 11 errors, the lead test subset for Specification, DoneWhenCriterion, Assumption, Unknown and ExecutionSession reports 5 passed and 5 deselected under the DeprecationWarning error filter, and E1 counts 6 DeprecationWarnings with every field and stored line still naive, UTC and offset-free.

## After (code commit c3fdf39)

Every command ran on code commit c3fdf39, the head that completes the source diff. The commands are the same as in the Baseline section. R9 runs exactly as CONTEXT criterion 3 writes it, with no extra flags.

R1 `git -C <worktree> rev-parse --short origin/main`

```text
0e93597
```

R2 `git -C <worktree> rev-parse --short HEAD`

```text
c3fdf39
```

R3 `git -C <worktree> log --format='%h %s' origin/main..HEAD`

```text
c3fdf39 fix(execution-core): clear the last pyright diagnostics (TYPE-02)
a62c8aa fix(execution-core): move remaining domain defaults onto utc_now_naive (TYPE-02)
40a830b docs(planning): Phase 2 baseline evidence and tracer checkpoint
80cf663 fix(execution-core): naive UTC clock for Specification and ExecutionSession defaults (TYPE-02)
4249bb8 docs(planning): Phase 2 plan (pyright clean execution-core)
915fd1e test(execution-core): guard naive UTC default timestamps (Phase 2 checks, D-06)
```

R4 `git -C <worktree> diff --name-only origin/main...HEAD -- . ':!.planning'`

```text
packages/execution-core/src/execution_core/domain/clock.py
packages/execution-core/src/execution_core/domain/decision.py
packages/execution-core/src/execution_core/domain/evidence.py
packages/execution-core/src/execution_core/domain/foreground.py
packages/execution-core/src/execution_core/domain/parking_item.py
packages/execution-core/src/execution_core/domain/session.py
packages/execution-core/src/execution_core/domain/specification.py
packages/execution-core/src/execution_core/domain/task.py
packages/execution-core/src/execution_core/policies/integrity_policy.py
packages/execution-core/src/execution_core/policies/parking_policy.py
packages/execution-core/src/execution_core/state_machine/lifecycle.py
tests/packages/execution-core/domain/test_naive_utc_defaults.py
```

R5 (no output: no diagnostics)

```text
```

R6

```text
{
  "filesAnalyzed": 24,
  "errorCount": 0,
  "warningCount": 0,
  "informationCount": 0,
  "timeInSec": 0.571
}
```

R7

```text
625
```

R8 (no output; git grep exit 1)

```text
```

R9 `uv run --directory <worktree> pytest tests/packages/execution-core -q -W error::DeprecationWarning --cov=packages/execution-core/src` (exit 0)

```text
........................................................................ [ 36%]
........................................................................ [ 72%]
.......................................................                  [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.15.0-final-0 ________________

Name                                                                       Stmts   Miss  Cover
----------------------------------------------------------------------------------------------
packages/execution-core/src/execution_core/__init__.py                         1      0   100%
packages/execution-core/src/execution_core/domain/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/domain/checkpoint.py               29      1    97%
packages/execution-core/src/execution_core/domain/clock.py                     3      0   100%
packages/execution-core/src/execution_core/domain/commands.py                 33      0   100%
packages/execution-core/src/execution_core/domain/decision.py                 25      0   100%
packages/execution-core/src/execution_core/domain/enums.py                    77      0   100%
packages/execution-core/src/execution_core/domain/evidence.py                 25      0   100%
packages/execution-core/src/execution_core/domain/foreground.py               27      6    78%
packages/execution-core/src/execution_core/domain/parking_item.py             29      6    79%
packages/execution-core/src/execution_core/domain/session.py                  25      0   100%
packages/execution-core/src/execution_core/domain/specification.py            82      0   100%
packages/execution-core/src/execution_core/domain/task.py                     67      3    96%
packages/execution-core/src/execution_core/events/__init__.py                  0      0   100%
packages/execution-core/src/execution_core/events/domain_events.py            47      0   100%
packages/execution-core/src/execution_core/policies/__init__.py                0      0   100%
packages/execution-core/src/execution_core/policies/completion_policy.py      68      0   100%
packages/execution-core/src/execution_core/policies/foreground_policy.py      56      9    84%
packages/execution-core/src/execution_core/policies/integrity_policy.py       74     11    85%
packages/execution-core/src/execution_core/policies/parking_policy.py         55      0   100%
packages/execution-core/src/execution_core/policies/permission_policy.py      44      0   100%
packages/execution-core/src/execution_core/policies/readiness_policy.py       43      4    91%
packages/execution-core/src/execution_core/state_machine/__init__.py           0      0   100%
packages/execution-core/src/execution_core/state_machine/lifecycle.py        180      3    98%
----------------------------------------------------------------------------------------------
TOTAL                                                                        990     43    96%
199 passed in 0.32s
```

R10 (coverage table identical to R9; summary line)

```text
199 passed in 0.32s
```

R11 (exit 0; table identical to R9, final line)

```text
TOTAL                                                                        990     43    96%
```

R12

```text
..........                                                               [100%]
10 passed in 0.08s
```

R13

```text
s.ssss.....x............                                                 [100%]
18 passed, 5 skipped, 1 xfailed in 0.71s
```

R14

```text
.........                                                                [100%]
9 passed in 0.09s
```

R15

```text
.........s.ssss.....x................................................... [ 15%]
........................................................................ [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 77%]
........................................................................ [ 92%]
..................................                                       [100%]
460 passed, 5 skipped, 1 xfailed, 2 warnings in 1.61s
```

R16

```text
All checks passed!
```

R17 (174 = 172 at baseline plus clock.py plus this evidence file)

```text
174 files already formatted
```

R18

```text
25
```

R19 Command E1 (same command as the Baseline section)

```text
process_tz: JST local_minus_utc_hours: 9.0
Task.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Task.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Evidence.recorded_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Decision.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ParkingItem.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ExecutionSession.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
ExecutionSession.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Foreground.calculated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Specification.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Specification.updated_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
DoneWhenCriterion.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Assumption.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
Unknown.created_at tzinfo=None offset_free=True utc_wall_clock=True iso_shape=9999-99-99T99:99:99.999999
specifications.done_when[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
specifications.assumptions[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
specifications.unknowns[0].created_at stored=9999-99-99T99:99:99.999999 offset_free=True
defaulted_fields: 13
deprecation_warnings: 0
```

R20 `git -C <worktree> diff --name-only 915fd1e HEAD -- . ':!.planning'`

```text
packages/execution-core/src/execution_core/domain/clock.py
packages/execution-core/src/execution_core/domain/decision.py
packages/execution-core/src/execution_core/domain/evidence.py
packages/execution-core/src/execution_core/domain/foreground.py
packages/execution-core/src/execution_core/domain/parking_item.py
packages/execution-core/src/execution_core/domain/session.py
packages/execution-core/src/execution_core/domain/specification.py
packages/execution-core/src/execution_core/domain/task.py
packages/execution-core/src/execution_core/policies/integrity_policy.py
packages/execution-core/src/execution_core/policies/parking_policy.py
packages/execution-core/src/execution_core/state_machine/lifecycle.py
```

R21 `git -C <worktree> log --format='%an' origin/main..HEAD -- tests evals .github pytest.ini .coveragerc`

```text
COH lead seat
```

R22 `git -C <worktree> diff origin/main...HEAD -- packages/execution-core | grep -c -E '^\+.*(type: ignore|pyright: ignore|noqa)'`

```text
0
```

R23 `git -C <worktree> diff origin/main...HEAD -- packages/execution-core | grep -c -E '^-.*datetime\.now\(UTC\)'`

```text
0
```

R24 `git -C <worktree> diff --stat origin/main...HEAD -- packages`

```text
 packages/execution-core/src/execution_core/domain/clock.py   | 12 ++++++++++++
 .../execution-core/src/execution_core/domain/decision.py     |  3 ++-
 .../execution-core/src/execution_core/domain/evidence.py     |  3 ++-
 .../execution-core/src/execution_core/domain/foreground.py   |  3 ++-
 .../execution-core/src/execution_core/domain/parking_item.py |  3 ++-
 packages/execution-core/src/execution_core/domain/session.py |  5 +++--
 .../src/execution_core/domain/specification.py               | 11 ++++++-----
 packages/execution-core/src/execution_core/domain/task.py    |  5 +++--
 .../src/execution_core/policies/integrity_policy.py          |  3 ++-
 .../src/execution_core/policies/parking_policy.py            |  2 +-
 .../src/execution_core/state_machine/lifecycle.py            |  3 ++-
 11 files changed, 37 insertions(+), 16 deletions(-)
```

R25 `git -C <worktree> status --porcelain --untracked-files=all -- . ':!.planning'` (no output)

```text
```

## Comparison

| Row | CONTEXT criterion | Baseline | After | Verdict |
|---|---|---|---|---|
| execution-core pyright errors | 1 | 18 | 0 | PASS |
| whole-repo pyright errors | 1 | 643 | 625 (643 minus 18) | PASS |
| deprecated factory lines in src | 2 | 13 | 0 | PASS |
| criterion-3 pytest command | 3 | 133 failed, 66 passed (exit 1) | 199 passed (exit 0) | PASS |
| coverage report exit code and TOTAL | 3 | exit 0, 96% | exit 0, 96% | PASS |
| E1 field lines naive, UTC and offset-free | 4 | 13 of 13 | 13 of 13 | PASS |
| E1 stored JSON-column strings offset-free | 4 | 3 of 3 | 3 of 3 | PASS |
| E1 deprecation_warnings | 4 | 18 | 0 | PASS |
| lead test under the error filter | D-06 | 10 failed | 10 passed | PASS |
| files changed after the checks commit | 5 | n/a | the 11 planned source files | PASS |
| protected-set authors | 5 | COH lead seat | COH lead seat | PASS |
| suppression count | 5 | n/a | 0 | PASS |
| aware datetime lines outside clock.py, removed aware lines | D-03 | 25, n/a | 25, 0 | PASS |
| tests/evals | 6 | 18 passed, 5 skipped, 1 xfailed | 18 passed, 5 skipped, 1 xfailed | PASS |
| tests/packages/persistence | 6 | 9 passed | 9 passed | PASS |
| full suite | DoD | 460 passed, 5 skipped, 1 xfailed | 460 passed, 5 skipped, 1 xfailed | PASS |
| ruff check and ruff format, whole repository | DoD | pass, 172 formatted | pass, 174 formatted | PASS |
| worktree status outside .planning | - | n/a | clean | PASS |

## Not checked

- The MCP and API handlers are not driven directly. E1 calls the domain API and the persistence mapper; the full suite covers tests/apps/api and tests/packages/mcp_adapter.
- No SQLite round trip. The CONTEXT notes that DATETIME columns drop tzinfo on write; the persistence suite covers the mapping.
- spec_gate_service still sets an aware updated_at on spec objects. The mixed stored form predates this phase and is out of scope.
- CI does not run pyright (known gap in CONTRIBUTING).
- The pyright errors under tests/packages/execution-core are protected and unchanged.
- The lead's test runs in the host time zone, while E1 forces UTC+9.
