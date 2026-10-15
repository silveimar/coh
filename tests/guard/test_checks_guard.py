"""Tests for .github/scripts/checks_guard.py (slice 07, D15).

The guard reads pull requests through the GitHub REST API. These tests replay
recorded, synthetic API responses from tests/guard/fixtures; nothing touches
the network.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
import urllib.parse
from email.message import Message
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO = "synthetic/coh"
LEAD = {"name": "COH lead seat", "email": "lead-seat@coh-fleet.invalid"}
BUILDER = {"name": "Builder", "email": "builder@example.invalid"}


def _load_guard() -> ModuleType:
    path = REPO_ROOT / ".github" / "scripts" / "checks_guard.py"
    spec = importlib.util.spec_from_file_location("checks_guard", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["checks_guard"] = module
    spec.loader.exec_module(module)
    return module


guard = _load_guard()


class FakeApi:
    """Replays recorded responses keyed by API path and query string."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.requested: list[str] = []

    def get(self, path: str, params: dict[str, int] | None = None) -> Any:
        key = path + (
            "?" + urllib.parse.urlencode(sorted(params.items())) if params else ""
        )
        self.requested.append(key)
        assert key in self.responses, f"no recorded response for {key}"
        body = self.responses[key]
        if isinstance(body, dict) and "__error__" in body:
            raise guard.GuardError(
                f"GitHub API request failed for {path}: {body['__error__']}"
            )
        return body


def fixture(name: str) -> FakeApi:
    return FakeApi(json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8")))


def rules(result: Any) -> list[str]:
    return [f.rule for f in result.findings]


# --- spec item 4 cases -------------------------------------------------------


def test_builder_commit_touching_tests_fails() -> None:
    result = guard.run("guard", fixture("builder_touches_tests"), REPO, 1)
    assert not result.passed
    assert result.findings[0].path == "tests/packages/prose/test_renderer.py"
    assert result.findings[0].commit == "b1b1b1b1b1b1"
    assert "protected path changed by a non-lead commit" in rules(result)


def test_lead_commit_adding_a_test_passes_both_jobs() -> None:
    assert guard.run("guard", fixture("lead_adds_test"), REPO, 1).passed
    assert guard.run("edits", fixture("lead_adds_test"), REPO, 1).passed


def test_lead_commit_deleting_a_test_line_passes_guard_and_fails_edits() -> None:
    assert guard.run("guard", fixture("lead_deletes_test_line"), REPO, 1).passed
    edits = guard.run("edits", fixture("lead_deletes_test_line"), REPO, 1)
    assert not edits.passed
    assert rules(edits) == ["existing protected lines edited or deleted"]
    assert "owner approval needed" in guard.summary(edits)


def test_builder_adding_pragma_no_cover_in_packages_fails() -> None:
    result = guard.run("guard", fixture("builder_pragma_in_packages"), REPO, 1)
    assert not result.passed
    assert rules(result) == ["adds `pragma: no cover`"]
    assert result.findings[0].path == "packages/prose/src/coh_prose/renderer.py"


def test_builder_editing_ci_workflow_fails() -> None:
    result = guard.run("guard", fixture("builder_edits_ci_workflow"), REPO, 1)
    assert not result.passed
    assert result.findings[0].path == ".github/workflows/ci.yml"
    assert "protected path changed by a non-lead commit" in rules(result)


def test_file_without_patch_fails_guard() -> None:
    result = guard.run("guard", fixture("file_without_patch"), REPO, 1)
    assert not result.passed
    assert rules(result) == ["no patch available; added lines cannot be checked"]


def test_protected_file_without_patch_fails_edits() -> None:
    assert guard.run(
        "guard", fixture("lead_protected_file_without_patch"), REPO, 1
    ).passed
    edits = guard.run("edits", fixture("lead_protected_file_without_patch"), REPO, 1)
    assert not edits.passed
    assert rules(edits) == ["no patch available; edits cannot be checked"]


@pytest.mark.parametrize("mode", ["guard", "edits"])
def test_api_error_fails_closed(mode: str) -> None:
    result = guard.run(mode, fixture("api_error"), REPO, 1)
    assert not result.passed
    assert result.error is not None and "502" in result.error
    assert "Failed closed" in guard.summary(result)


def test_http_error_from_github_becomes_guard_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise urllib.error.HTTPError(
            "https://api.invalid/x", 403, "Forbidden", Message(), io.BytesIO(b"")
        )

    monkeypatch.setattr(guard.urllib.request, "urlopen", refuse)
    result = guard.run(
        "guard", guard.GitHubApi("synthetic-token", "https://api.invalid"), REPO, 1
    )
    assert not result.passed
    assert result.error is not None and "403" in result.error


def test_builder_rename_into_tests_is_treated_as_a_protected_change() -> None:
    result = guard.run("guard", fixture("builder_renames_into_tests"), REPO, 1)
    assert not result.passed
    assert "protected path changed by a non-lead commit" in rules(result)
    edits = guard.run("edits", fixture("builder_renames_into_tests"), REPO, 1)
    assert rules(edits) == ["protected file renamed"]


def test_lead_rename_out_of_tests_passes_guard_and_fails_edits() -> None:
    assert guard.run("guard", fixture("lead_renames_out_of_tests"), REPO, 1).passed
    edits = guard.run("edits", fixture("lead_renames_out_of_tests"), REPO, 1)
    assert rules(edits) == ["protected file renamed"]
    old = "tests/evals/scenarios/sample_scenario.yaml"
    new = "docs/examples/sample_scenario.yaml"
    assert edits.findings[0].path == f"{old} -> {new}"


# --- pagination: built from the same recorded shapes, too long to keep as files --


def _commit(sha: str, author: dict[str, str]) -> dict[str, Any]:
    return {"sha": sha, "parents": [{"sha": "0" * 40}], "commit": {"author": author}}


def _file(name: str, patch: str = "@@ -1 +1,2 @@\n x = 1\n+y = 2") -> dict[str, Any]:
    return {"filename": name, "status": "modified", "changes": 1, "patch": patch}


def _paged(base: str, items: list[Any], key: str | None = None) -> dict[str, Any]:
    pages: dict[str, Any] = {}
    for page, start in enumerate(range(0, len(items) + 1, guard.PER_PAGE), start=1):
        chunk = items[start : start + guard.PER_PAGE]
        pages[f"{base}?page={page}&per_page=100"] = {"files": chunk} if key else chunk
        if len(chunk) < guard.PER_PAGE:
            break
    return pages


def test_pagination_reads_commit_files_past_the_first_100() -> None:
    sha = "b7" * 20
    files = [_file(f"packages/prose/src/coh_prose/m{i}.py") for i in range(150)]
    files[120] = _file(
        "packages/prose/src/coh_prose/m120.py",
        '@@ -1 +1,2 @@\n x = 1\n+import pytest  # pytest.skip("later")',
    )
    responses = {
        "repos/synthetic/coh/pulls/1": {
            "number": 1,
            "commits": 1,
            "changed_files": 150,
        },
        "repos/synthetic/coh/pulls/1/commits?page=1&per_page=100": [
            _commit(sha, BUILDER)
        ],
        **_paged(f"repos/synthetic/coh/commits/{sha}", files, key="files"),
    }
    api = FakeApi(responses)
    result = guard.run("guard", api, REPO, 1)
    assert rules(result) == ["adds `pytest.skip(`"]
    assert result.findings[0].path == "packages/prose/src/coh_prose/m120.py"
    assert f"repos/synthetic/coh/commits/{sha}?page=2&per_page=100" in api.requested


def test_pagination_reads_pr_files_past_the_first_100() -> None:
    files = [_file(f"docs/page{i}.md") for i in range(150)]
    files[140] = {
        "filename": "tests/evals/scenarios/old.yaml",
        "status": "removed",
        "changes": 3,
        "patch": "@@ -1,3 +0,0 @@\n-a\n-b\n-c",
    }
    responses = {
        "repos/synthetic/coh/pulls/1": {
            "number": 1,
            "commits": 1,
            "changed_files": 150,
        },
        **_paged("repos/synthetic/coh/pulls/1/files", files),
    }
    result = guard.run("edits", FakeApi(responses), REPO, 1)
    assert rules(result) == ["protected file deleted"]


def test_exactly_100_files_reads_an_empty_second_page() -> None:
    files = [_file(f"docs/page{i}.md") for i in range(100)]
    responses = {
        "repos/synthetic/coh/pulls/1": {
            "number": 1,
            "commits": 1,
            "changed_files": 100,
        },
        **_paged("repos/synthetic/coh/pulls/1/files", files),
    }
    api = FakeApi(responses)
    assert guard.run("edits", api, REPO, 1).passed
    assert "repos/synthetic/coh/pulls/1/files?page=2&per_page=100" in api.requested


def test_incomplete_file_listing_fails_closed() -> None:
    files = [_file(f"docs/page{i}.md") for i in range(40)]
    responses = {
        "repos/synthetic/coh/pulls/1": {"number": 1, "commits": 1, "changed_files": 41},
        **_paged("repos/synthetic/coh/pulls/1/files", files),
    }
    result = guard.run("edits", FakeApi(responses), REPO, 1)
    assert result.error == "listed 40 of 41 changed files"


@pytest.mark.parametrize(
    ("mode", "pr"),
    [
        ("guard", {"number": 1, "commits": 250, "changed_files": 1}),
        ("edits", {"number": 1, "commits": 1, "changed_files": 3000}),
    ],
)
def test_pr_too_large_to_list_fails_closed(mode: str, pr: dict[str, int]) -> None:
    result = guard.run(mode, FakeApi({"repos/synthetic/coh/pulls/1": pr}), REPO, 1)
    assert result.error is not None and "at most" in result.error


# --- further fail-closed and identity rules ----------------------------------


def test_merge_commit_fails_guard() -> None:
    result = guard.run("guard", fixture("merge_commit"), REPO, 1)
    assert rules(result) == ["merge commit (rebase the branch instead)"]


def test_lead_identity_is_the_author_email_not_the_name() -> None:
    impostor = {"name": "COH lead seat", "email": "builder@example.invalid"}
    sha = "b8" * 20
    responses = {
        "repos/synthetic/coh/pulls/1": {"number": 1, "commits": 1, "changed_files": 1},
        "repos/synthetic/coh/pulls/1/commits?page=1&per_page=100": [
            _commit(sha, impostor)
        ],
        f"repos/synthetic/coh/commits/{sha}?page=1&per_page=100": {
            "files": [_file("tests/guard/test_x.py")]
        },
    }
    result = guard.run("guard", FakeApi(responses), REPO, 1)
    assert "protected path changed by a non-lead commit" in rules(result)


@pytest.mark.parametrize("rule", guard.WEAKENING_RULES)
def test_every_weakening_rule_is_detected_in_an_added_line(rule: str) -> None:
    assert rule in guard.weakening_rules_in(f"    something {rule} something")


def test_weakening_rules_ignore_removed_and_context_lines() -> None:
    patch = "@@ -1,2 +1,2 @@\n # pragma: no cover\n-pytest.mark.skip\n+ok = True"
    assert guard.added_lines(patch) == ["ok = True"]


@pytest.mark.parametrize(
    ("path", "protected"),
    [
        ("tests/packages/prose/test_renderer.py", True),
        ("tests/guard/fixtures/api_error.json", True),
        ("evals/scenarios/a.yaml", True),
        ("packages/prose/tests/test_x.py", True),
        ("packages/prose/conftest.py", True),
        ("pytest.ini", True),
        (".coveragerc", True),
        ("tox.ini", True),
        ("setup.cfg", True),
        (".github/workflows/ci.yml", True),
        (".github/scripts/checks_guard.py", True),
        (".github/CODEOWNERS", True),
        ("packages/prose/src/coh_prose/renderer.py", False),
        ("docs/testing.md", False),
        ("pyproject.toml", False),
        (".github/pull_request_template.md", False),
        ("contests/notes.md", False),
        (None, False),
    ],
)
def test_protected_set(path: str | None, protected: bool) -> None:
    assert guard.is_protected(path) is protected


def test_main_writes_the_job_summary_and_fails_on_missing_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert guard.main(["checks_guard.py", "guard"]) == 2
    assert "Failed closed" in summary_file.read_text(encoding="utf-8")
