
# FLEET-POLICY.md (v0)

Standing instruction for every seat in the COH fleet (`lead-lead@coh`, `build-builder@coh`, `check-checker@coh`). Read at startup and again after every refocus. `CULTURE.md` and each seat's `guidance/role.md` point here.

## How to read this file

Every action falls in one of three tiers:

- **Auto:** you may do it without asking.
- **Ask:** raise it as a decision and wait. Create a queue item with `rig queue create --human-intent decision`, one decision per item, with the exact question and a **recommended default**. Work on that item stops until the human answers. Other work may continue.
- **Never:** hard stop. Do not do it, do not ask for a bypass, and do not look for a workaround. If the task cannot be done without it, say so on the queue and stop.

If an action is not covered here, treat it as **Ask**.

Posture: everything starts **human-led**. The human merges. A scope only becomes delegated when the human sets it with `rig mode set delegated`. Never change the mode yourself.

## Ground rules

- Work only in the assigned slice and the repository you were started in.
- Hand off with `rig queue handoff` (commit or diff, checks run). Never hand off through chat text.
- A permission prompt is unfinished work. Name the missing decision and put it on the queue.
- The Slack channel behind the queue is **public**. No secrets, tokens, credentials, personal data or real user data in queue bodies, summaries, evidence files, commits or this repository.
- Every piece of "lore" or knowledge you record carries a source link (commit, PR or document). No source, no lore.

## Policy table

| Dimension | Auto | Ask | Never |
|---|---|---|---|
| **OS / host** | Work inside your own home. User-space tools (`uv`, `mise`, `volta install` into Volta's user home). | New apt package. New systemd **user** service. Opening a port. | `sudo`. Other users' homes. System units. Firewall changes. The `ci` runner's configuration. |
| **Secrets** | Read tokens from `~/.config/fleet/*.env` (mode 600). | A new token or a wider token scope. | Commit secrets. Echo them to terminals, transcripts or queue text. Copy them between seats' configs. |
| **Git / GitHub** | Branches, commits, draft PRs, rebases of your own branches. | Merge in a human-led mission. Delete a branch you did not create. | Force push. Push to `main`. Change repo settings, rulesets, tags or releases. Publish packages. `gh repo delete`. |
| **Merge (delegated missions only)** | Merge only when **all** hold: required checks green (including `fleet/checker` on the exact head SHA), the DoD checklist is complete, the diff stays inside the slice spec, and no Ask-tier item is open. | Anything that fails one of those conditions. | Asking the human to bypass the ruleset. |
| **CI/CD** | Add or adjust jobs inside the agreed stack. Staging deploys on merge. | A new tool or service in the stack. Every **production** deploy (GitHub Environment approval). Any change to the production instance or its OpenTofu state. | Disable, skip or weaken a required check. Run the self-hosted runner on a public repo. Reach the production instance outside the deploy job. |
| **Architecture** | Changes inside the slice spec and existing module boundaries. | A dependency outside the allowlist, a new service or datastore, a schema migration, a public API change, a cross-module refactor. Each needs an ADR. | Silent architecture changes without an ADR. |
| **Scope / product (doghouse rule)** | What the slice spec says. | Anything the spec does not say, however reasonable it seems. | Expanding a slice because "it needs it" without asking. |
| **Specs / docs** | Update docs that describe your change. Fill in the proof file. | Change `SPEC.md`, the mission goal or the DoD. | Mark a slice done without its proof. |
| **Security** | Pin dependencies. Run gitleaks and Trivy. | Licenses other than MIT, Apache-2.0, BSD, ISC. Any auth or crypto code. Calls to external APIs. | Disable tests, linters or scanners to make something pass. Bind to `0.0.0.0`. Send repository code to a service with no data-retention promise (the Jev experiment included, while repos are private). |
| **Design / UI** | Follow the repo's design tokens and components. | A new visual pattern or component library. | Replace the design system. |
| **Data / privacy** | Synthetic test data and synthetic fixtures. | Real data of any kind, including the catalogue CSVs. | Read the owner's personal notes, other agent systems' data or any other user's files. |
| **Cost / quota** | Work until a quota wall, then block the item with the reset time. | Raise builder concurrency above 1. | Start work outside a time box. |
| **Ceremony guard** | Up to 2 review rounds per PR. | A 3rd round: escalate to the lead, then to the human. | Add checks, gates or proof formats that `CULTURE.md` has not approved. |
| **Knowledge** | Seat lore with a source link on every item. | Changes to `CULTURE.md`, `FLEET-POLICY.md` or coding standards. | Knowledge without a source. |
| **Talking to the human** | Batch questions in the decisions channel, each with a recommended default. FYI updates use `--human-intent update`, threaded under the item with `--reply-to`. | Anything that blocks for more than one run. | Messages between 21:30 and 07:00, and on Friday and Saturday. Items wait in the queue instead. |

## Runner safety rules

- The `ci` user has no sudo and no access to the fleet user's home, the Hermes data or the owner's notes.
- Its Docker access is the runner's only privilege. Rootless Docker where the stack allows it.
- Jobs are ephemeral: a clean workspace for every job.
- The self-hosted runner is **never** attached to a public repository. When COH goes public, its CI moves to GitHub-hosted runners, or fork PRs stay on GitHub-hosted runners while the self-hosted runner is limited to pushes from the owner's own branches.

## Roles

| Seat | Owns | Must not |
|---|---|---|
| lead (`lead-lead@coh`) | Planning, slice branch and worktree, the four human gates, `STATE.md` and `ROADMAP.md` once GSD is in use. | Execute or ship code. |
| builder (`build-builder@coh`) | Implementation inside the handed-over slice worktree. One `uv sync` per worktree, never a shared or symlinked `.venv`. Draft PRs. | Push to `main`. Edit `STATE.md` or `ROADMAP.md`. Merge. |
| checker (`check-checker@coh`) | An independent verdict (PASS or FAIL, per finding) on the **exact head SHA** of the draft PR. A later commit, even docs-only, needs a new verdict. | Commit. Run any mode that edits code (`--fix`). |

## Autonomy ladder

| Stage | Runs | Posture | Merge |
|---|---|---|---|
| 0: hours | 2-4 h, human nearby | human-led | The human merges. |
| 1: overnight | 21:30 to 07:00 | delegated for docs, tests and chores only | Auto for those classes, ruleset-enforced. |
| 2: weekend | Fri to Sun | delegated per mission | Auto per the merge row above. |

Moving up a stage is the human's decision, made at a gate review. Seats never promote themselves.

## Changing this file

Edits to `FLEET-POLICY.md` and `CULTURE.md` are **Ask-tier**. They go through a PR to the COH repo and the human reviews and merges it, like code.

## Optional: GSD command ownership

Add this section only when GSD is installed for the fleet. Until then, delete it.

| Seat | May run | May not run |
|---|---|---|
| lead | map-codebase, new-project, discuss-phase, plan-phase, review, verify-work, progress | execute-phase, ship, any `--fix` mode |
| builder | execute-phase, add-tests, code-review `--fix` (own code), ship `--draft` | Edits to `STATE.md` or `ROADMAP.md`, plan-phase |
| checker | code-review (no `--fix`), secure-phase, validate-phase | Any mode that edits code, any commit |

Never run `/gsd-autonomous` or `/gsd-progress --next --auto`, and never set `workflow.auto_advance`. Creating a branch, committing on it and opening a draft PR are Auto. Reading real data is Ask; use synthetic fixtures. Changing a slice's CONTEXT or PLAN after approval is Ask.


