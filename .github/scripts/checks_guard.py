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

Every gap in the data fails closed: an API error, a missing or malformed field,
a file whose content cannot be read, a patch that does not match the file's
declared line counts, line totals that do not add up, a merge commit, or a PR
too large to list completely.

Weakening rules match literal tokens, tolerating whitespace and line breaks
inside a run of added lines. They do not follow aliases or dynamic code.

Standard library only; the runner's system ``python3`` runs it.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

# The lead seat's commit author (CONTRIBUTING.md, fleet section).
LEAD_AUTHOR_EMAIL = "lead-seat@coh-fleet.invalid"

# Protected set P. Keep in sync with coh-fleet
# openrig-specs/agents/shared/runtime/hooks/protected-paths.json and its
# isProtected(): the path is normalized, a directory matches as a run of path
# segments anywhere in it, a file name matches the last segment (trailing `*`
# or `?` stripped) and a path matches the path's tail.
PROTECTED_DIRS = ("tests", "evals", ".github/workflows", ".github/scripts")
PROTECTED_FILES = ("conftest.py", "pytest.ini", ".coveragerc", "tox.ini", "setup.cfg")
PROTECTED_PATHS = (".github/CODEOWNERS",)

# An added line containing any of these tokens weakens a check.
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

# Git's blob id for an empty file: an added file with this id has no content.
EMPTY_BLOB_SHA = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
FILE_STATUSES = (
    "added",
    "removed",
    "modified",
    "renamed",
    "copied",
    "changed",
    "unchanged",
)

EDITS_APPROVAL_NOTE = "owner approval needed"

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def _rule_pattern(rule: str) -> re.Pattern[str]:
    tokens = re.findall(r"\w+|[^\w\s]", rule)
    return re.compile(r"\s*".join(re.escape(t) for t in tokens))


_RULE_PATTERNS = tuple((rule, _rule_pattern(rule)) for rule in WEAKENING_RULES)


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


@dataclass(frozen=True)
class FileChange:
    filename: str
    previous_filename: str | None
    status: str
    additions: int
    deletions: int
    patch: str | None
    sha: str | None


@dataclass(frozen=True)
class Diff:
    """Content of a patch: runs of consecutive added lines, and line counts."""

    added_runs: list[list[str]]
    added: int
    removed: int


# --- protected set --------------------------------------------------------


def _segments(path: str) -> list[str]:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    return [s for s in normalized.split("/") if s and s != "."]


def _contains_run(segs: list[str], run: list[str]) -> bool:
    return any(segs[i : i + len(run)] == run for i in range(len(segs) - len(run) + 1))


def is_protected(path: str | None) -> bool:
    if not path:
        return False
    segs = _segments(path)
    if not segs:
        return False
    if segs[-1].rstrip("*?") in PROTECTED_FILES:
        return True
    if any(_contains_run(segs, _segments(d)) for d in PROTECTED_DIRS):
        return True
    for p in PROTECTED_PATHS:
        run = _segments(p)
        if segs[-len(run) :] == run:
            return True
    return False


# --- patches --------------------------------------------------------------


def parse_patch(patch: str) -> Diff:
    """Parse a GitHub file patch (a sequence of hunks) by its hunk line counts.

    Line prefixes are read only inside a hunk, so an added line whose content
    starts with `++` or `--` is kept. Anything that is not a hunk, or a hunk
    whose lines do not match its header, raises GuardError.
    """
    lines = patch.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    runs: list[list[str]] = []
    run: list[str] = []
    added = removed = 0
    old_left = new_left = 0
    for line in lines:
        if old_left == 0 and new_left == 0:
            if run:
                runs.append(run)
                run = []
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            header = _HUNK_HEADER.match(line)
            if not header:
                raise GuardError("patch text outside a hunk")
            old_left = int(header.group(1)) if header.group(1) is not None else 1
            new_left = int(header.group(2)) if header.group(2) is not None else 1
            continue
        tag, content = line[:1], line[1:]
        if tag == "+":
            added += 1
            new_left -= 1
            run.append(content)
        elif tag == "-":
            removed += 1
            old_left -= 1
            if run:
                runs.append(run)
                run = []
        elif tag in (" ", ""):
            old_left -= 1
            new_left -= 1
            if run:
                runs.append(run)
                run = []
        elif tag != "\\":
            raise GuardError("unexpected line in a patch hunk")
        if old_left < 0 or new_left < 0:
            raise GuardError("patch hunk longer than its header says")
    if old_left or new_left:
        raise GuardError("patch hunk shorter than its header says")
    if run:
        runs.append(run)
    return Diff(runs, added, removed)


def weakening_rules_in(text: str) -> list[str]:
    return [rule for rule, pattern in _RULE_PATTERNS if pattern.search(text)]


def _joined(run: list[str]) -> str:
    """One run of added lines as text, line continuations removed."""
    parts = [line.rstrip() for line in run]
    return " ".join(p[:-1] if p.endswith("\\") else p for p in parts)


# --- API records ----------------------------------------------------------


def _int(record: dict[str, Any], key: str, what: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GuardError(f"{what}: missing or invalid `{key}`")
    return value


def file_change(record: Any) -> FileChange:
    """Validate one entry of a commit's or PR's `files` list."""
    if not isinstance(record, dict):
        raise GuardError("file entry is not an object")
    name = record.get("filename")
    if not isinstance(name, str) or not name:
        raise GuardError("file entry without a filename")
    what = f"file `{name}`"
    status = record.get("status")
    if status not in FILE_STATUSES:
        raise GuardError(f"{what}: unknown status {status!r}")
    additions = _int(record, "additions", what)
    deletions = _int(record, "deletions", what)
    if _int(record, "changes", what) != additions + deletions:
        raise GuardError(f"{what}: `changes` is not additions + deletions")
    previous = record.get("previous_filename")
    if status in ("renamed", "copied"):
        if not isinstance(previous, str) or not previous:
            raise GuardError(f"{what}: {status} without `previous_filename`")
    elif previous is not None:
        raise GuardError(f"{what}: unexpected `previous_filename`")
    patch = record.get("patch")
    if patch is not None and not isinstance(patch, str):
        raise GuardError(f"{what}: invalid `patch`")
    sha = record.get("sha")
    return FileChange(
        name,
        previous,
        str(status),
        additions,
        deletions,
        patch,
        sha if isinstance(sha, str) else None,
    )


def content(change: FileChange) -> Diff | None:
    """The file's diff, or None when its content cannot be established."""
    if change.patch is not None:
        diff = parse_patch(change.patch)
        if diff.added != change.additions or diff.removed != change.deletions:
            raise GuardError(
                f"patch for `{change.filename}` does not match its line counts"
            )
        return diff
    if change.additions == 0 and change.deletions == 0:
        if change.status == "renamed":  # pure rename, content unchanged
            return Diff([], 0, 0)
        if change.status == "added" and change.sha == EMPTY_BLOB_SHA:
            return Diff([], 0, 0)
    if change.status == "removed" and change.additions == 0:
        return Diff([], 0, change.deletions)
    return None


def _totals_match(changes: list[FileChange], stats: dict[str, Any], what: str) -> None:
    additions = _int(stats, "additions", what)
    deletions = _int(stats, "deletions", what)
    if sum(c.additions for c in changes) != additions or (
        sum(c.deletions for c in changes) != deletions
    ):
        raise GuardError(f"{what}: listed files do not add up to its line totals")


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


def _pull(api: Api, repo: str, number: int) -> dict[str, Any]:
    pr = api.get(f"repos/{repo}/pulls/{number}")
    if not isinstance(pr, dict):
        raise GuardError("could not read the pull request")
    for key in ("commits", "changed_files", "additions", "deletions"):
        _int(pr, key, "pull request")
    return pr


def _commit_sha(commit: Any) -> str:
    if not isinstance(commit, dict):
        raise GuardError("commit entry is not an object")
    sha = commit.get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise GuardError("commit entry without a valid sha")
    if not isinstance(commit.get("parents"), list):
        raise GuardError(f"commit {sha[:12]}: missing `parents`")
    return sha


def _is_lead(commit: dict[str, Any]) -> bool:
    author = (commit.get("commit") or {}).get("author") or {}
    return author.get("email") == LEAD_AUTHOR_EMAIL


def _commit_changes(api: Api, repo: str, sha: str) -> list[FileChange]:
    path = f"repos/{repo}/commits/{sha}"
    first = api.get(path, {"per_page": PER_PAGE, "page": 1})
    stats = first.get("stats") if isinstance(first, dict) else None
    if not isinstance(stats, dict):
        raise GuardError(f"commit {sha[:12]}: missing `stats`")
    records = _get_all(api, path, MAX_FILES, key="files")
    changes = [file_change(r) for r in records]
    _totals_match(changes, stats, f"commit {sha[:12]}")
    return changes


# --- the two checks -------------------------------------------------------


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
        full_sha = _commit_sha(commit)
        sha = full_sha[:12]
        if len(commit["parents"]) > 1:
            findings.append(
                Finding(sha, "-", "merge commit (rebase the branch instead)")
            )
            continue
        if _is_lead(commit):
            continue
        for change in _commit_changes(api, repo, full_sha):
            if is_protected(change.filename) or is_protected(change.previous_filename):
                findings.append(
                    Finding(
                        sha,
                        change.filename,
                        "protected path changed by a non-lead commit",
                    )
                )
            diff = content(change)
            if diff is None:
                findings.append(
                    Finding(
                        sha,
                        change.filename,
                        "content not available; added lines cannot be checked",
                    )
                )
                continue
            for run in diff.added_runs:
                for rule in weakening_rules_in(_joined(run)):
                    findings.append(Finding(sha, change.filename, f"adds `{rule}`"))
    return findings


def check_edits(api: Api, repo: str, number: int) -> list[Finding]:
    pr = _pull(api, repo, number)
    if pr["changed_files"] >= MAX_FILES:
        count = pr["changed_files"]
        raise GuardError(
            f"the PR changes {count} files; GitHub lists at most {MAX_FILES}"
        )
    records = _get_all(api, f"repos/{repo}/pulls/{number}/files", MAX_FILES)
    if len(records) != pr["changed_files"]:
        raise GuardError(
            f"listed {len(records)} of {pr['changed_files']} changed files"
        )
    changes = [file_change(r) for r in records]
    _totals_match(changes, pr, "pull request")

    findings: list[Finding] = []
    for change in changes:
        name, previous = change.filename, change.previous_filename
        if not (is_protected(name) or is_protected(previous)):
            continue
        diff = content(change)  # raises when a patch contradicts its line counts
        if change.status == "removed":
            findings.append(Finding("PR", name, "protected file deleted"))
        elif change.status == "renamed":
            findings.append(
                Finding("PR", f"{previous} -> {name}", "protected file renamed")
            )
        elif change.deletions > 0:
            findings.append(
                Finding("PR", name, "existing protected lines edited or deleted")
            )
        elif diff is None:
            findings.append(
                Finding("PR", name, "content not available; edits cannot be checked")
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
        try:
            result = run(mode, api, repo, number)
        except Exception as exc:  # noqa: BLE001 (any unexpected shape fails closed)
            result = Result(
                mode, error=f"unexpected error: {type(exc).__name__}: {exc}"
            )

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
