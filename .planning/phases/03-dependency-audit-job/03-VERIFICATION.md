# Phase 03 verification (builder self-check)

This is the builder seat's self-check. It is not the slice proof; the slice proof is the checker's report on the head SHA. The commands ran at ca26cc3, and the commit that adds this file changes only this file, 03-01-SUMMARY.md and 03-EVIDENCE.md. Full output is in `03-EVIDENCE.md`, "Task 4 (build)" and "Task 5 (final gates)".

Criterion 2 uses `origin/main` in place of `main`, because the local `main` ref is stale (plan finding 2). Criterion 3 uses the builder's export form with `--no-header --quiet -o <file>`, because `-o` also prints the export and the header carries host paths (plan finding 12).

| # | CONTEXT criterion | Command | Result | Verdict |
|---|---|---|---|---|
| 1 | ADR with Status Accepted, an index row, and a version and license for deptry and pip-audit | `grep -c -F '**Status:** Accepted'` on the ADR; index-row grep; `grep -n -E '^\| (deptry\|pip-audit) \|'` on the ADR | `1`; row 46 says Accepted; deptry 0.25.1 MIT, pip-audit 2.10.1 Apache-2.0, plus every closure package in Tables 1 and 2 | PASS |
| 2 | ci.yml shows both tools with exact pins, no error-tolerance key, `--strict` present, workflow commits only by the lead seat | `grep -nE 'deptry\|pip-audit'` on ci.yml; `grep -c "on-error"`; `grep -c -F -- '--strict --disable-pip'`; `git log --format=%ae origin/main..HEAD -- .github/workflows/`; numstat | Line 206 holds `deptry 0.25.1`, line 297 holds `pip-audit==2.10.1`; error-tolerance count 0; `--strict --disable-pip` once (line 297); only `lead-seat@coh-fleet.invalid`; `131 0` | PASS |
| 3 | The `--no-hashes` export has at least 50 pins including fastapi, sqlalchemy, mcp and pyyaml, and no `-e` line | `uv export --locked --all-packages --no-emit-workspace --format requirements.txt --no-hashes --no-header --quiet -o <scratch>/dep-adr/head-nohash.txt`; three `grep -c` | `67`; `4`; `0` | PASS |
| 4 | On the head, deptry exits 0 for each of the 7 members and pip-audit exits 0 on the export | 7 × `uv run --no-sync deptry --no-ansi <m> --config <m>/pyproject.toml`; `uvx --python 3.13 pip-audit==2.10.1 --strict --disable-pip -r <hashed export>` | All 7 exit 0 with `Success! No dependency issues found.` (archive 5, execution-core 24, persistence 11, prose 3, mcp_adapter 6, application 3, apps/api 12 files); pip-audit exit 0, `No known vulnerabilities found` | PASS |
| 5 | deptry exits 1 with DEP002 on a seeded scratch copy; pip-audit `--strict --disable-pip --no-deps` exits 1 on `requests==2.19.1` | deptry on `<scratch>/dep-adr/bite-prose` with `sqlalchemy>=2.0.0` seeded; pip-audit on `<scratch>/dep-adr/probe/vulnerable.txt` | deptry exit 1, `DEP002 'sqlalchemy' defined as a dependency but not used in the codebase`, `Found 1 dependency issue.`; pip-audit exit 1, `Found 10 known vulnerabilities in 1 package` | PASS |
| 6 | `gh pr checks <n>` shows both new jobs and checks-guard passing on the exact head SHA | `gh pr checks 39 --repo <repo>`; `gh run view 39814532635 --repo <repo> --json headSha,conclusion,jobs` | On 43a4a0d (run 39814532635, `success`): Dependency check (deptry) pass, Vulnerability audit (pip-audit) pass, Lint and Test pass, Secret scan pass; checks-guard pass (run 39814528261). checks-edits pending: it waits for the owner's checks-approval environment because the branch carries the lead's ci.yml commit; per the plan this is not a failure (lead row, 16:40Z). The commit that records this changes only phase docs; its own run is in 03-EVIDENCE.md and the checker's report | PASS (checks-edits pending owner approval) |

## Not checked

- The CI bash glue (loop, exit-code capture, step summary) other than through the PR's own run.
- pip-audit on the win32 and emscripten marker sets (colorama, pywin32, httpx2-jsfetch; owner answer Q5).
- pip-audit's closure on any day other than 2026-10-22: it is not locked, only pip-audit is pinned.
- Wheel availability on platforms other than linux x86_64.
- pip-audit's behavior when its vulnerability service is unreachable.
