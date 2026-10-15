"""checks-guard: server-side protection of the COH check set (H-87, D14, D15).

Runs from `.github/workflows/checks-guard.yml` on `pull_request_target`, so
GitHub executes the base branch copy of this file. It reads the pull request
through the REST API only and never checks out or runs PR code.

Two modes:

- ``guard`` (job ``checks-guard``) fails when (a) a commit not authored by the
  lead seat touches a protected path, or (b) a line added by a non-lead commit,
  in any file, matches a weakening rule.
- ``edits`` (job ``checks-edits``) fails when the PR as a whole deletes,
  renames or edits existing lines of a protected path, whoever authored it.
  It needs owner approval.

Every gap in the data fails closed: an API error, a protected or scanned file
without a patch, a merge commit, or a PR too large to list completely.

Standard library only; the runner's system ``python3`` runs it.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Protocol

# The lead seat's commit author (CONTRIBUTING.md, fleet section).
LEAD_AUTHOR_EMAIL = "lead-seat@coh-fleet.invalid"

# Protected set P. Keep in sync with coh-fleet
# openrig-specs/agents/shared/runtime/hooks/protected-paths.json and its
# isProtected(): a directory matches as a run of path segments anywhere in the
# path, a file name matches the last segment, a path matches the path's tail.
PROTECTED_DIRS = ("tests", "evals", ".github/workflows", ".github/scripts")
PROTECTED_FILES = ("conftest.py", "pytest.ini", ".coveragerc", "tox.ini", "setup.cfg")
PROTECTED_PATHS = (".github/CODEOWNERS",)

# An added line containing any of these weakens a check.
WEAKENING_RULES = (
    "pragma: no cover",
    "pytest.mark.skip",
    "pytest.mark.skipif",
    "pytest.mark.xfail",
    "pytest.skip(",
    "pytest.xfail(",
    "unittest.skip",
    "--deselect",
    "--cov-fail-under",
    "continue-on-error",
    "[tool.pytest",
    "[tool.coverage",
)

PER_PAGE = 100
# GitHub lists at most 250 commits of a PR and 3000 files of a PR or commit.
MAX_COMMITS = 250
MAX_FILES = 3000

EDITS_APPROVAL_NOTE = "owner approval needed"


class GuardError(Exception):
    """The guard could not read complete data, so it fails closed."""


class Api(Protocol):
    def get(self, path: str, params: dict[str, int] | None = None) -> Any: ...


@dataclass(frozen=True)
class Finding:
    commit: str
    path: str
    rule: str


@dataclass
class Result:
    mode: str
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and not self.findings


def _segments(path: str) -> list[str]:
    return [
        s
        for s in PurePosixPath(path.replace("\\", "/")).parts
        if s not in ("", ".", "/")
    ]


def _contains_run(segs: list[str], run: list[str]) -> bool:
    return any(segs[i : i + len(run)] == run for i in range(len(segs) - len(run) + 1))


def is_protected(path: str | None) -> bool:
    if not path:
        return False
    segs = _segments(path)
    if not segs:
        return False
    if segs[-1] in PROTECTED_FILES:
        return True
    if any(_contains_run(segs, _segments(d)) for d in PROTECTED_DIRS):
        return True
    for p in PROTECTED_PATHS:
        run = _segments(p)
        if segs[-len(run) :] == run:
            return True
    return False


def added_lines(patch: str) -> list[str]:
    return [
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def removed_lines(patch: str) -> list[str]:
    return [
        line[1:]
        for line in patch.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]


def weakening_rules_in(line: str) -> list[str]:
    return [rule for rule in WEAKENING_RULES if rule in line]


def _get_all(api: Api, path: str, limit: int, key: str | None = None) -> list[Any]:
    """Read every page of a list endpoint; `key` selects the list inside an object."""
    items: list[Any] = []
    page = 1
    while True:
        body = api.get(path, {"per_page": PER_PAGE, "page": page})
        chunk = body.get(key) if key and isinstance(body, dict) else body
        if not isinstance(chunk, list):
            raise GuardError(f"unexpected response for {path} page {page}")
        items.extend(chunk)
        if len(items) >= limit:
            raise GuardError(
                f"{path} lists {limit} or more entries; too large to check completely"
            )
        if len(chunk) < PER_PAGE:
            return items
        page += 1


def _sha(commit: dict[str, Any]) -> str:
    return str(commit.get("sha", "?"))[:12]


def _is_lead(commit: dict[str, Any]) -> bool:
    author = (commit.get("commit") or {}).get("author") or {}
    return author.get("email") == LEAD_AUTHOR_EMAIL


def _pull(api: Api, repo: str, number: int) -> dict[str, Any]:
    pr = api.get(f"repos/{repo}/pulls/{number}")
    if (
        not isinstance(pr, dict)
        or not isinstance(pr.get("commits"), int)
        or not isinstance(pr.get("changed_files"), int)
    ):
        raise GuardError("could not read the pull request")
    return pr


def check_guard(api: Api, repo: str, number: int) -> list[Finding]:
    pr = _pull(api, repo, number)
    if pr["commits"] >= MAX_COMMITS:
        raise GuardError(
            f"the PR has {pr['commits']} commits; GitHub lists at most {MAX_COMMITS}"
        )
    commits = _get_all(api, f"repos/{repo}/pulls/{number}/commits", MAX_COMMITS)
    if len(commits) != pr["commits"]:
        raise GuardError(f"listed {len(commits)} of {pr['commits']} commits")

    findings: list[Finding] = []
    for commit in commits:
        sha = _sha(commit)
        if len(commit.get("parents") or []) > 1:
            findings.append(
                Finding(sha, "-", "merge commit (rebase the branch instead)")
            )
            continue
        if _is_lead(commit):
            continue
        files = _get_all(
            api, f"repos/{repo}/commits/{commit['sha']}", MAX_FILES, key="files"
        )
        for f in files:
            name = f.get("filename")
            previous = f.get("previous_filename")
            if is_protected(name) or is_protected(previous):
                findings.append(
                    Finding(
                        sha, str(name), "protected path changed by a non-lead commit"
                    )
                )
            patch = f.get("patch")
            if patch is None:
                if f.get("changes", 1) != 0:
                    findings.append(
                        Finding(
                            sha,
                            str(name),
                            "no patch available; added lines cannot be checked",
                        )
                    )
                continue
            for line in added_lines(patch):
                for rule in weakening_rules_in(line):
                    findings.append(Finding(sha, str(name), f"adds `{rule}`"))
    return findings


def check_edits(api: Api, repo: str, number: int) -> list[Finding]:
    pr = _pull(api, repo, number)
    if pr["changed_files"] >= MAX_FILES:
        count = pr["changed_files"]
        raise GuardError(
            f"the PR changes {count} files; GitHub lists at most {MAX_FILES}"
        )
    files = _get_all(api, f"repos/{repo}/pulls/{number}/files", MAX_FILES)
    if len(files) != pr["changed_files"]:
        raise GuardError(f"listed {len(files)} of {pr['changed_files']} changed files")

    findings: list[Finding] = []
    for f in files:
        name = f.get("filename")
        previous = f.get("previous_filename")
        if not (is_protected(name) or is_protected(previous)):
            continue
        status = f.get("status")
        if status == "removed":
            findings.append(Finding("PR", str(name), "protected file deleted"))
            continue
        if status == "renamed":
            findings.append(
                Finding("PR", f"{previous} -> {name}", "protected file renamed")
            )
            continue
        patch = f.get("patch")
        if patch is None:
            if f.get("changes", 1) != 0:
                findings.append(
                    Finding(
                        "PR", str(name), "no patch available; edits cannot be checked"
                    )
                )
            continue
        if removed_lines(patch):
            findings.append(
                Finding("PR", str(name), "existing protected lines edited or deleted")
            )
    return findings


def run(mode: str, api: Api, repo: str, number: int) -> Result:
    result = Result(mode)
    try:
        if mode == "guard":
            result.findings = check_guard(api, repo, number)
        elif mode == "edits":
            result.findings = check_edits(api, repo, number)
        else:
            result.error = f"unknown mode {mode!r}"
    except GuardError as exc:
        result.error = str(exc)
    return result


def summary(result: Result) -> str:
    job = "checks-guard" if result.mode == "guard" else "checks-edits"
    lines = [f"### {job}", ""]
    if result.error:
        lines += [f"**Failed closed: {result.error}.**", ""]
    if result.findings:
        if result.mode == "edits":
            lines += [
                f"**{EDITS_APPROVAL_NOTE}:** this PR changes existing protected"
                " check lines.",
                "",
            ]
        lines += ["| Commit | Path | Rule |", "|---|---|---|"]
        lines += [f"| `{f.commit}` | `{f.path}` | {f.rule} |" for f in result.findings]
        lines.append("")
    if result.passed:
        lines += ["Pass: no finding.", ""]
    return "\n".join(lines)


class GitHubApi:
    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        self._token = token
        self._base = base_url.rstrip("/")

    def get(self, path: str, params: dict[str, int] | None = None) -> Any:
        url = f"{self._base}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(sorted(params.items()))
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (fixed https API base)
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise GuardError(f"GitHub API request failed for {path}: {exc}") from exc


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    try:
        token = os.environ["GITHUB_TOKEN"]
        repo = os.environ["GITHUB_REPOSITORY"]
        number = int(os.environ["PR_NUMBER"])
    except (KeyError, ValueError) as exc:
        result = Result(mode, error=f"missing or invalid environment: {exc}")
    else:
        api = GitHubApi(
            token, os.environ.get("GITHUB_API_URL", "https://api.github.com")
        )
        result = run(mode, api, repo, number)

    text = summary(result)
    print(text)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if result.error:
        return 2
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
