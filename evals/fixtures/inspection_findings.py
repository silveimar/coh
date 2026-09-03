"""Recorded inspection findings fixtures for eval scenarios.

Mock adapter returns these when inspect_repository is called,
keyed by scenario id. No live inspection; I-14 stub in product.
"""

INSPECTION_FINDINGS = {
    "spec-001-vague-request": (
        "auth test intermittent timeout in CI logs; "
        "recent commit 8a3f touched session refresh; "
        "tests/ directory exists with login flow coverage"
    ),
    "spec-002-inferable-ready": (
        "README.md documents release process; "
        "merged PRs since v1.2.0: #42 (fix), #43 (feature), #44 (docs); "
        "CHANGELOG.md exists with established format"
    ),
    "spec-003-blocking-unknown": (
        "auth module found with JWT implementation; "
        "config references OAUTH_PROVIDER but no provider configured; "
        "deployment target unknown from codebase"
    ),
    "prose-001-spec-evidence-first": (
        "worker.py retry loop re-enqueues failed jobs with no delay; "
        "no backoff or max-attempt cap; "
        "#TODO backoff comment exists; "
        "tests cover happy path only"
    ),
    "prose-002-recap-threshold": (
        "14 architectural components across 8 subsystems; "
        "caching layer requires Redis 6+ with cluster mode; "
        "authentication flow spans 3 services; "
        "deployment dependencies: Postgres 14, Redis 6, RabbitMQ 3.9"
    ),
    "prose-003-recovery-exemption": (
        "mid-execution checkpoint with task_001 in progress; "
        "blocker: CI environment differs from production; "
        "decision_01: use Docker for environment parity; "
        "parked_item: performance optimization deferred"
    ),
    "prose-004-protected-fields": (
        "existing spec revision 1 confirmed; "
        "field names: what, why, deliverable, done_when (protected); "
        "user correction targets deliverable field only"
    ),
    "drift-001-invalidating-discovery": (
        "API endpoint /auth/refresh found deprecated in v2.0 docs; "
        "migration guide recommends /auth/token/renew; "
        "current implementation uses deprecated endpoint; "
        "no tests for new endpoint"
    ),
    "drift-002-intentional-detour": (
        "unrelated dependency update available: requests 2.28 -> 2.31; "
        "security advisory CVE-2023-32681 affects current version; "
        "update requires minimal changes"
    ),
}
