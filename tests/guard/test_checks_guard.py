"""Tests for .github/scripts/checks_guard.py (slice 07, D15).

The guard reads pull requests through the GitHub REST API. These tests replay
recorded, synthetic API responses from tests/guard/fixtures; nothing touches
the network. Cases that need many entries or one changed field are built by
`_api` from the same response shapes.
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
        query = "?" + urllib.parse.urlencode(sorted(params.items())) if params else ""
        key = path + query
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


# --- builders for generated cases ------------------------------------------


def _commit(sha: str, author: dict[str, str], parents: int = 1) -> dict[str, Any]:
    return {
        "sha": sha,
        "parents": [{"sha": "0" * 40}] * parents,
        "commit": {"author": author},
    }


def _file(
    name: str,
    patch: str | None = "@@ -1 +1,2 @@\n x = 1\n+y = 2",
    *,
    status: str = "modified",
    additions: int | None = None,
    deletions: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """A file entry; line counts default to what the patch contains."""
    if patch is not None and (additions is None or deletions is None):
        diff = guard.parse_patch(patch)
        additions = diff.added if additions is None else additions
        deletions = diff.removed if deletions is None else deletions
    adds, dels = additions or 0, deletions or 0
    record: dict[str, Any] = {
        "filename": name,
        "status": status,
        "additions": adds,
        "deletions": dels,
        "changes": adds + dels,
        **extra,
    }
    if patch is not None:
        record["patch"] = patch
    return record


def _totals(files: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "additions": sum(f["additions"] for f in files),
        "deletions": sum(f["deletions"] for f in files),
    }


def _pages(
    base: str, items: list[Any], first: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Pages of 100 for a list; with `first`, pages are commit objects with `files`."""
    pages: dict[str, Any] = {}
    for page, start in enumerate(range(0, len(items) + 1, guard.PER_PAGE), start=1):
        chunk = items[start : start + guard.PER_PAGE]
        key = f"{base}?page={page}&per_page=100"
        if first is None:
            pages[key] = chunk
        else:
            pages[key] = {**(first if page == 1 else {}), "files": chunk}
        if len(chunk) < guard.PER_PAGE:
            break
    return pages


def _api(
    commits: list[tuple[str, dict[str, str], list[dict[str, Any]]]] | None = None,
    pr_files: list[dict[str, Any]] | None = None,
) -> FakeApi:
    """Consistent responses for one PR: its commits, their files, and its files."""
    commits = commits or []
    pr_files = (
        pr_files if pr_files is not None else [f for _, _, fs in commits for f in fs]
    )
    responses: dict[str, Any] = {
        "repos/synthetic/coh/pulls/1": {
            "number": 1,
            "commits": len(commits),
            "changed_files": len(pr_files),
            **_totals(pr_files),
        },
        "repos/synthetic/coh/pulls/1/commits?page=1&per_page=100": [
            _commit(sha, author) for sha, author, _ in commits
        ],
        **_pages("repos/synthetic/coh/pulls/1/files", pr_files),
    }
    for sha, _, files in commits:
        stats = {"total": sum(_totals(files).values()), **_totals(files)}
        responses.update(
            _pages(
                f"repos/synthetic/coh/commits/{sha}",
                files,
                {"sha": sha, "stats": stats},
            )
        )
    return FakeApi(responses)


SHA = "b9" * 20


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
    assert rules(result) == ["content not available; added lines cannot be checked"]


def test_protected_file_without_patch_fails_edits() -> None:
    fx = "lead_protected_file_without_patch"
    assert guard.run("guard", fixture(fx), REPO, 1).passed
    edits = guard.run("edits", fixture(fx), REPO, 1)
    assert not edits.passed
    assert rules(edits) == ["content not available; edits cannot be checked"]


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
    api = guard.GitHubApi("synthetic-token", "https://api.invalid")
    result = guard.run("guard", api, REPO, 1)
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


def test_pagination_reads_commit_files_past_the_first_100() -> None:
    files = [_file(f"packages/prose/src/coh_prose/m{i}.py") for i in range(150)]
    files[120] = _file(
        "packages/prose/src/coh_prose/m120.py",
        '@@ -1 +1,2 @@\n x = 1\n+import pytest  # pytest.skip("later")',
    )
    api = _api([(SHA, BUILDER, files)])
    result = guard.run("guard", api, REPO, 1)
    assert rules(result) == ["adds `pytest.skip(`"]
    assert result.findings[0].path == "packages/prose/src/coh_prose/m120.py"
    assert f"repos/synthetic/coh/commits/{SHA}?page=2&per_page=100" in api.requested


def test_pagination_reads_pr_files_past_the_first_100() -> None:
    files = [_file(f"docs/page{i}.md") for i in range(150)]
    files[140] = _file(
        "tests/evals/scenarios/old.yaml",
        "@@ -1,3 +0,0 @@\n-a\n-b\n-c",
        status="removed",
    )
    result = guard.run("edits", _api(pr_files=files), REPO, 1)
    assert rules(result) == ["protected file deleted"]


def test_exactly_100_files_reads_an_empty_second_page() -> None:
    api = _api(pr_files=[_file(f"docs/page{i}.md") for i in range(100)])
    assert guard.run("edits", api, REPO, 1).passed
    assert "repos/synthetic/coh/pulls/1/files?page=2&per_page=100" in api.requested


# --- F1: hunk lines that look like diff headers -----------------------------


def test_added_line_starting_with_plus_plus_is_scanned() -> None:
    patch = "@@ -1 +1,2 @@\n x = 1\n+++counter  # pragma: no cover"
    files = [_file("packages/prose/src/coh_prose/counter.py", patch)]
    result = guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1)
    assert rules(result) == ["adds `pragma: no cover`"]


def test_removed_line_starting_with_minus_minus_is_an_edit() -> None:
    patch = "@@ -1 +1 @@\n---old\n+--new"
    assert guard.parse_patch(patch).removed == 1
    files = [_file("tests/evals/fixtures/flags.txt", patch)]
    result = guard.run("edits", _api(pr_files=files), REPO, 1)
    assert rules(result) == ["existing protected lines edited or deleted"]


def test_parse_patch_counts_and_runs() -> None:
    patch = (
        "@@ -1,3 +1,4 @@\n a\n-b\n+c\n+d\n e\n"
        "@@ -10 +11,2 @@\n f\n+g\n\\ No newline at end of file"
    )
    diff = guard.parse_patch(patch)
    assert (diff.added, diff.removed) == (3, 1)
    assert diff.added_runs == [["c", "d"], ["g"]]


@pytest.mark.parametrize(
    "patch",
    [
        "--- a/x.py\n+++ b/x.py\n@@ -1 +1,2 @@\n x\n+y",  # text outside a hunk
        "@@ -1,1 +1,3 @@\n x\n+y",  # hunk shorter than its header
        "@@ -1 +1 @@\n x\n+y",  # hunk longer than its header
        "@@ -1 +1,2 @@\n x\n?y",  # unknown line tag
    ],
)
def test_malformed_patch_fails_closed(patch: str) -> None:
    files = [_file("packages/x.py", patch, additions=1, deletions=0)]
    result = guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1)
    assert result.error is not None


# --- F2: missing patch is accepted only when no content is possible ---------


def test_modified_protected_file_without_patch_and_zero_changes_fails_edits() -> None:
    files = [_file("tests/fixtures/data.bin", None)]
    result = guard.run("edits", _api(pr_files=files), REPO, 1)
    assert rules(result) == ["content not available; edits cannot be checked"]


def test_modified_file_without_patch_and_zero_changes_fails_guard() -> None:
    files = [_file("packages/prose/data/table.bin", None)]
    result = guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1)
    assert rules(result) == ["content not available; added lines cannot be checked"]


def test_added_binary_file_without_patch_fails_guard() -> None:
    files = [_file("packages/prose/data/blob.bin", None, status="added", sha="ab" * 20)]
    result = guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1)
    assert rules(result) == ["content not available; added lines cannot be checked"]


def test_added_empty_file_passes_guard() -> None:
    files = [
        _file(
            "packages/prose/src/coh_prose/__init__.py",
            None,
            status="added",
            sha=guard.EMPTY_BLOB_SHA,
        )
    ]
    assert guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1).passed


def test_pure_rename_outside_the_set_passes_guard() -> None:
    files = [
        _file(
            "packages/prose/src/coh_prose/new_name.py",
            None,
            status="renamed",
            previous_filename="packages/prose/src/coh_prose/old_name.py",
        )
    ]
    assert guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1).passed


# --- F3: missing, malformed or inconsistent data fails closed ----------------


def test_commit_with_no_files_but_positive_stats_fails_closed() -> None:
    sha = SHA
    api = _api([(sha, BUILDER, [])], pr_files=[_file("packages/x.py")])
    api.responses[f"repos/synthetic/coh/commits/{sha}?page=1&per_page=100"]["stats"] = {
        "total": 1,
        "additions": 1,
        "deletions": 0,
    }
    result = guard.run("guard", api, REPO, 1)
    assert result.error is not None and "do not add up" in result.error


def test_commit_without_stats_fails_closed() -> None:
    api = _api([(SHA, BUILDER, [_file("packages/x.py")])])
    del api.responses[f"repos/synthetic/coh/commits/{SHA}?page=1&per_page=100"]["stats"]
    result = guard.run("guard", api, REPO, 1)
    assert result.error is not None and "stats" in result.error


@pytest.mark.parametrize("mode", ["guard", "edits"])
def test_file_without_filename_fails_closed(mode: str) -> None:
    record = _file("packages/x.py")
    del record["filename"]
    result = guard.run(mode, _api([(SHA, BUILDER, [record])]), REPO, 1)
    assert result.error is not None and "filename" in result.error


@pytest.mark.parametrize(
    "change",
    [
        {"status": "mystery"},
        {"additions": -1},
        {"changes": 7},
        {"previous_filename": "elsewhere.py"},
        {"patch": 42},
    ],
)
def test_malformed_file_entry_fails_closed(change: dict[str, Any]) -> None:
    record = {**_file("packages/x.py"), **change}
    result = guard.run("edits", _api(pr_files=[record]), REPO, 1)
    assert result.error is not None


def test_patch_missing_a_declared_deletion_fails_closed() -> None:
    record = _file(
        "tests/fixtures/data.txt", "@@ -1 +1,2 @@\n x\n+y", additions=1, deletions=1
    )
    result = guard.run("edits", _api(pr_files=[record]), REPO, 1)
    assert result.error is not None and "line counts" in result.error


def test_declared_deletion_on_protected_file_is_an_edit_even_without_patch() -> None:
    record = _file("tests/fixtures/data.bin", None, additions=0, deletions=4)
    result = guard.run("edits", _api(pr_files=[record]), REPO, 1)
    assert rules(result) == ["existing protected lines edited or deleted"]


def test_pr_totals_that_do_not_add_up_fail_closed() -> None:
    api = _api(pr_files=[_file("docs/a.md")])
    api.responses["repos/synthetic/coh/pulls/1"]["deletions"] = 9
    result = guard.run("edits", api, REPO, 1)
    assert result.error is not None and "do not add up" in result.error


def test_commit_without_parents_fails_closed() -> None:
    api = _api([(SHA, BUILDER, [_file("packages/x.py")])])
    del api.responses["repos/synthetic/coh/pulls/1/commits?page=1&per_page=100"][0][
        "parents"
    ]
    result = guard.run("guard", api, REPO, 1)
    assert result.error is not None and "parents" in result.error


def test_incomplete_file_listing_fails_closed() -> None:
    api = _api(pr_files=[_file(f"docs/page{i}.md") for i in range(40)])
    api.responses["repos/synthetic/coh/pulls/1"]["changed_files"] = 41
    result = guard.run("edits", api, REPO, 1)
    assert result.error == "listed 40 of 41 changed files"


@pytest.mark.parametrize(
    ("mode", "counts"),
    [("guard", {"commits": 250}), ("edits", {"changed_files": 3000})],
)
def test_pr_too_large_to_list_fails_closed(mode: str, counts: dict[str, int]) -> None:
    pr = {"number": 1, "commits": 1, "changed_files": 1, "additions": 0, "deletions": 0}
    result = guard.run(
        mode, FakeApi({"repos/synthetic/coh/pulls/1": {**pr, **counts}}), REPO, 1
    )
    assert result.error is not None and "at most" in result.error


def test_unexpected_exception_in_main_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("synthetic")

    monkeypatch.setattr(guard, "run", boom)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    assert guard.main(["checks_guard.py", "guard"]) == 2
    assert "unexpected error" in (tmp_path / "summary.md").read_text(encoding="utf-8")


# --- F4: weakening tokens across whitespace and line continuations ----------


@pytest.mark.parametrize(
    ("lines", "rule"),
    [
        (["pytest.skip \\", '    ("skip", allow_module_level=True)'], "pytest.skip("),
        (['pytest.skip ("later")'], "pytest.skip("),
        (["@pytest . mark . xfail"], "pytest.mark.xfail"),
        (["x = 1  # pragma:  no  cover"], "pragma: no cover"),
        (["[ tool.coverage.run ]"], "[tool.coverage"),
        (["@unittest.skipIf(True, 'x')"], "unittest.skip"),
    ],
)
def test_weakening_rule_survives_whitespace_and_continuations(
    lines: list[str], rule: str
) -> None:
    patch = f"@@ -1 +1,{len(lines) + 1} @@\n x\n" + "\n".join(
        f"+{line}" for line in lines
    )
    files = [_file("packages/prose/src/coh_prose/m.py", patch)]
    result = guard.run("guard", _api([(SHA, BUILDER, files)]), REPO, 1)
    assert f"adds `{rule}`" in rules(result)


def test_tokens_split_by_a_removed_line_are_not_joined() -> None:
    patch = "@@ -1 +1,2 @@\n+pytest.\n-old\n+skip("
    assert guard.parse_patch(patch).added_runs == [["pytest."], ["skip("]]


# --- identity, merges and the protected set --------------------------------


def test_merge_commit_fails_guard() -> None:
    result = guard.run("guard", fixture("merge_commit"), REPO, 1)
    assert rules(result) == ["merge commit (rebase the branch instead)"]


def test_lead_identity_is_the_author_email_not_the_name() -> None:
    impostor = {"name": "COH lead seat", "email": "builder@example.invalid"}
    result = guard.run(
        "guard", _api([(SHA, impostor, [_file("tests/guard/test_x.py")])]), REPO, 1
    )
    assert "protected path changed by a non-lead commit" in rules(result)


def test_lead_commit_is_not_scanned_for_weakening_rules() -> None:
    files = [_file("tests/guard/test_x.py", "@@ -1 +1,2 @@\n x\n+# pragma: no cover")]
    assert guard.run("guard", _api([(SHA, LEAD, files)]), REPO, 1).passed


@pytest.mark.parametrize("rule", guard.WEAKENING_RULES)
def test_every_weakening_rule_is_detected_in_an_added_line(rule: str) -> None:
    assert rule in guard.weakening_rules_in(f"    something {rule} something")


@pytest.mark.parametrize(
    ("path", "protected"),
    [
        ("tests/packages/prose/test_renderer.py", True),
        ("tests/guard/fixtures/api_error.json", True),
        ("evals/scenarios/a.yaml", True),
        ("packages/prose/tests/test_x.py", True),
        ("packages/prose/conftest.py", True),
        ("pytest.ini", True),
        ("pytest.ini*", True),
        (".coveragerc", True),
        ("tox.ini", True),
        ("setup.cfg", True),
        (".github/workflows/ci.yml", True),
        (".github/scripts/checks_guard.py", True),
        (".github/CODEOWNERS", True),
        ("folder/.github/CODEOWNERS", True),
        ("./tests/a.py", True),
        ("tests/../src/a.py", False),
        ("packages/prose/src/coh_prose/renderer.py", False),
        ("docs/testing.md", False),
        ("pyproject.toml", False),
        (".github/pull_request_template.md", False),
        ("contests/notes.md", False),
        ("Tests/a.py", False),
        (None, False),
    ],
)
def test_protected_set_matches_the_seat_hook(path: str | None, protected: bool) -> None:
    assert guard.is_protected(path) is protected


def test_main_writes_the_job_summary_and_fails_on_missing_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert guard.main(["checks_guard.py", "guard"]) == 2
    assert "Failed closed" in summary_file.read_text(encoding="utf-8")
