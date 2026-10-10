# Architecture Decision Records (ADRs)

An ADR records one architecture decision: the question, the options, what was chosen, and what it costs. ADRs are append-only history. Do not edit an accepted ADR; write a new one that supersedes it.

## ADR or decision log?

| Use | For |
|---|---|
| **ADR** (`docs/adr/`) | A technical or architectural choice made while building: a dependency, service or datastore, schema migration, public API or wire-format change, cross-module refactor, tooling choice. |
| **Decision log** (`docs/decision-log.md`) | A durable product or execution-semantics decision (D1, D2, ...): track, stack, lifecycle, policies, prose rendering. |

If an ADR changes execution semantics, it also gets a decision-log entry. Link them both ways (the ADR's "Decision log" field, and the log entry's rationale).

## When an ADR is required

Any of the following needs an ADR, approved by the owner before the work continues (these are Ask-tier for the fleet; see `FLEET-POLICY.md`):

- a new dependency outside the allowlist
- a new service or datastore
- a schema migration
- a public API change
- a cross-module refactor

If you are unsure, write a short ADR. A rejected or unneeded ADR costs minutes; a silent architecture change costs a slice.

## How to write one

1. Copy `0000-template.md` to `NNNN-short-slug.md` using the next free four-digit number (`0001-...`, `0002-...`). Numbers are never reused.
2. Fill in every section. Keep it to one page where you can. Facts carry a source.
3. Set **Status: Proposed** and open a PR with the ADR (alone, or with the code that needs it, marked as blocked until the ADR is accepted).
4. The owner reviews. On approval, set **Status: Accepted** and the date, and merge.
5. Add a row to the index below in the same PR.

Fleet seats: put the exact question and a recommended default on the queue as a decision (`--human-intent decision`) and link the draft ADR. Work on the affected item waits for the answer.

## Changing or reversing a decision

Never rewrite an accepted ADR. Write a new ADR that states what changed, set the old one to `Superseded by ADR-NNNN`, and update the index. Typo and link fixes are fine.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-uv-dev-dependency-group.md) | Put dev tools in a root uv dependency group | Proposed | 2026-10-09 |
