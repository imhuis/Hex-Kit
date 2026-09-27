#!/usr/bin/env python3
"""Synchronize Trellis tasks with GitHub issues using the GitHub REST API."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common.io import read_json_checked, write_json
from common.paths import FILE_TASK_JSON, get_repo_root, get_tasks_dir
from common.task_utils import resolve_task_dir

API_ROOT = "https://api.github.com"
MAX_REPORT_BYTES = 55_000


class GitHubError(RuntimeError):
    """An API or configuration failure safe to show in CLI output."""


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise GitHubError("GITHUB_TOKEN or GH_TOKEN is not set")
    return token


def _repository(repo_root: Path) -> tuple[str, str, str]:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    remote = result.stdout.strip()
    if result.returncode != 0 or not remote:
        raise GitHubError("origin Git remote is not configured")

    if remote.startswith("git@"):
        match = re.fullmatch(r"git@(github\.com|ssh\.github\.com):(?:\d+/)?([^/]+)/([^/]+?)(?:\.git)?", remote)
        if not match:
            raise GitHubError("origin is not a supported GitHub SSH remote")
        owner, name = match.group(2), match.group(3)
    else:
        parsed = urllib.parse.urlparse(remote)
        if parsed.hostname not in {"github.com", "ssh.github.com"}:
            raise GitHubError("origin is not a supported GitHub remote")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise GitHubError("origin GitHub remote has no owner/repository path")
        owner, name = parts[-2], parts[-1]
        if name.endswith(".git"):
            name = name[:-4]

    if not owner or not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise GitHubError("origin GitHub remote has an invalid owner/repository")
    base = f"{API_ROOT}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}"
    return owner, name, base


def _request(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    allow_list: bool = False,
) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {_token()}",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "Trellis-GitHub-Issue-Gate",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise GitHubError(f"GitHub API returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = type(reason).__name__ if reason is not None else type(exc).__name__
        raise GitHubError(f"GitHub API request failed ({detail})") from None
    if not raw:
        return {}
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GitHubError("GitHub API returned an invalid response") from None
    if not isinstance(result, dict) and not (allow_list and isinstance(result, list)):
        raise GitHubError("GitHub API returned an unexpected response")
    return result


def _load_task(task_json_path: Path) -> dict:
    data, reason = read_json_checked(task_json_path)
    if data is None:
        raise GitHubError(f"could not read task metadata ({reason})")
    if not isinstance(data, dict):
        raise GitHubError("task metadata must be a JSON object")
    return data


def _save_task(task_json_path: Path, data: dict) -> None:
    if not write_json(task_json_path, data):
        raise GitHubError(f"could not write {task_json_path}")


@contextlib.contextmanager
def _task_sync_lock(task_json_path: Path):
    """Serialize local issue sync attempts for the same Trellis task."""
    repo_root = get_repo_root()
    lock_dir = repo_root / ".trellis" / ".runtime" / "github-issue-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    identity = f"{repo_root.resolve()}:{task_json_path.parent.name}"
    lock_path = lock_dir / f"{hashlib.sha256(identity.encode('utf-8')).hexdigest()}.lock"
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt
            import time

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            while True:
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _issue_state(data: dict) -> dict:
    meta = data.setdefault("meta", {})
    if not isinstance(meta, dict):
        raise GitHubError("task meta must be a JSON object")
    state = meta.setdefault("githubIssue", {})
    if not isinstance(state, dict):
        raise GitHubError("meta.githubIssue must be a JSON object")
    return state


def _task_json_from_env() -> Path:
    value = os.environ.get("TASK_JSON_PATH")
    if not value:
        raise GitHubError("TASK_JSON_PATH is not set")
    path = Path(value).resolve()
    if path.name != FILE_TASK_JSON or not _is_task_or_archive_dir(path.parent):
        raise GitHubError("TASK_JSON_PATH is not a Trellis task")
    return path


def _task_json_from_argument(value: str) -> Path:
    repo_root = get_repo_root()
    task_dir = resolve_task_dir(value, repo_root)
    if task_dir is None or not _is_task_or_archive_dir(task_dir, repo_root):
        raise GitHubError(f"not a Trellis task: {value}")
    return task_dir / FILE_TASK_JSON


def _is_task_or_archive_dir(task_dir: Path, repo_root: Path | None = None) -> bool:
    try:
        tasks_root = get_tasks_dir(repo_root).resolve()
        relative = task_dir.resolve().relative_to(tasks_root)
    except (OSError, RuntimeError, ValueError):
        return False
    if len(relative.parts) == 1:
        return relative.parts[0] != "archive"
    return (
        len(relative.parts) == 3
        and relative.parts[0] == "archive"
        and re.fullmatch(r"\d{4}-\d{2}", relative.parts[1]) is not None
    )


def _task_marker(task_dir: Path) -> str:
    try:
        relative_path = task_dir.resolve().relative_to(get_tasks_dir().resolve().parent.parent).as_posix()
    except (ValueError, OSError):
        relative_path = task_dir.name
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()


def _find_existing_issue(base: str, owner: str, repository: str, marker: str) -> dict | None:
    query = f'repo:{owner}/{repository} is:issue "trellis-task:{marker}"'
    url = f"{API_ROOT}/search/issues?{urllib.parse.urlencode({'q': query, 'per_page': 10})}"
    response = _request("GET", url)
    issues = response.get("items", [])
    if not isinstance(issues, list):
        raise GitHubError("GitHub issue search returned an invalid result")
    for issue in issues:
        if isinstance(issue, dict) and f"trellis-task:{marker}" in str(issue.get("body", "")):
            return issue
    return None


def _create_issue_locked(task_json_path: Path) -> bool:
    data = _load_task(task_json_path)
    state = _issue_state(data)
    if state.get("exempt") or state.get("status") == "exempt":
        return True
    if state.get("number"):
        return True

    task_dir = task_json_path.parent
    marker = state.get("marker")
    if not isinstance(marker, str) or not marker:
        marker = _task_marker(task_dir)
        state["marker"] = marker
        _save_task(task_json_path, data)
    try:
        owner, repository, base = _repository(get_repo_root())
        existing = _find_existing_issue(base, owner, repository, marker)
        if existing is None:
            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            task_path = task_dir.resolve().relative_to(get_repo_root().resolve()).as_posix()
            safe_task_path = html.escape(task_path, quote=True)
            body = (
                f"{description}\n\n"
                f"Trellis task directory: <code>{safe_task_path}</code>\n"
                f"Task record: <code>{safe_task_path}/task.json</code>\n"
                f"Requirements: <code>{safe_task_path}/prd.md</code>\n\n"
                "<!-- trellis-task:" + marker + " -->"
            )
            existing = _request("POST", f"{base}/issues", {"title": title, "body": body})
        if not isinstance(existing.get("number"), int) or not isinstance(existing.get("html_url"), str):
            raise GitHubError("GitHub did not return an issue number and URL")
        state.update(
            {
                "status": "closed" if existing.get("state") == "closed" else "open",
                "exempt": False,
                "number": existing.get("number"),
                "url": existing.get("html_url"),
                "repository": f"{owner}/{repository}",
            }
        )
        state.pop("lastError", None)
        _save_task(task_json_path, data)
        print(f"GitHub issue synchronized: {state['url']}")
        return True
    except GitHubError as exc:
        state.update({"status": "pending", "exempt": False, "lastError": str(exc)})
        _save_task(task_json_path, data)
        print(f"GitHub issue sync pending for {task_dir.name}: {exc}", file=sys.stderr)
        return False


def create_issue(task_json_path: Path) -> bool:
    with _task_sync_lock(task_json_path):
        return _create_issue_locked(task_json_path)


def _accepted_report(task_json_path: Path, data: dict) -> tuple[str, str]:
    meta = data.get("meta")
    acceptance = meta.get("githubAcceptance") if isinstance(meta, dict) else None
    if not isinstance(acceptance, dict) or acceptance.get("qualityPassed") is not True:
        raise GitHubError("quality acceptance has not been recorded")
    commit = str(acceptance.get("commit", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise GitHubError("acceptance commit must be a full Git SHA")
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=get_repo_root(),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubError("acceptance commit is not present in this repository")
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=get_repo_root(),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubError("acceptance commit is not part of the current branch history")

    report_value = acceptance.get("report")
    if not isinstance(report_value, str) or not report_value:
        raise GitHubError("acceptance report path is missing")
    task_dir = task_json_path.parent.resolve()
    report_path = (task_dir / report_value).resolve()
    try:
        report_path.relative_to(task_dir)
    except ValueError:
        raise GitHubError("acceptance report must be inside the Trellis task directory") from None
    try:
        report = report_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        raise GitHubError("acceptance report could not be read") from None
    if not report:
        raise GitHubError("acceptance report is empty")
    report_bytes = report.encode("utf-8")
    if len(report_bytes) > MAX_REPORT_BYTES:
        raise GitHubError(f"acceptance report exceeds {MAX_REPORT_BYTES} bytes")
    if acceptance.get("reportSha256") != hashlib.sha256(report_bytes).hexdigest():
        raise GitHubError("acceptance report changed after it was approved")
    return commit.lower(), report


def validate_archive_acceptance(task_json_path: Path, data: dict) -> str | None:
    """Return a refusal reason when a linked issue has not passed its gate."""
    meta = data.get("meta")
    state = meta.get("githubIssue", {}) if isinstance(meta, dict) else {}
    if not isinstance(state, dict) or not state.get("number"):
        return None
    if state.get("exempt") or state.get("status") == "exempt":
        return None
    try:
        _accepted_report(task_json_path, data)
    except GitHubError as exc:
        return str(exc)
    return None


def _complete_issue_locked(task_json_path: Path) -> bool:
    data = _load_task(task_json_path)
    state = _issue_state(data)
    if state.get("exempt") or state.get("status") == "exempt":
        return True
    if not state.get("number"):
        print(f"GitHub issue identity is missing for {task_json_path.parent.name}", file=sys.stderr)
        return False
    if data.get("status") != "completed":
        print(f"GitHub issue remains open until task {task_json_path.parent.name} is archived")
        return True

    try:
        commit, report = _accepted_report(task_json_path, data)
        owner, repository, base = _repository(get_repo_root())
        expected_repository = state.get("repository")
        if expected_repository and (
            not isinstance(expected_repository, str)
            or expected_repository.lower() != f"{owner}/{repository}".lower()
        ):
            raise GitHubError(
                "origin no longer matches the repository that owns this issue"
            )
        issue_number = int(state["number"])
        if not state.get("reportCommentId"):
            commit_url = f"https://github.com/{owner}/{repository}/commit/{commit}"
            report_hash = hashlib.sha256(report.encode("utf-8")).hexdigest()
            task_marker = state.get("marker") or _task_marker(task_json_path.parent)
            marker = f"<!-- trellis-acceptance:{task_marker}:{commit}:{report_hash} -->"
            comments = _request(
                "GET",
                f"{base}/issues/{issue_number}/comments?per_page=100&sort=created&direction=desc",
                allow_list=True,
            )
            if not isinstance(comments, list):
                raise GitHubError("GitHub returned an invalid issue comment list")
            existing_comment = next(
                (
                    item for item in comments
                    if isinstance(item, dict) and marker in str(item.get("body", ""))
                ),
                None,
            )
            if existing_comment is None:
                comment = f"## Trellis acceptance report\n\nCommitted code: {commit_url}\n\n{report}\n\n{marker}"
                posted = _request("POST", f"{base}/issues/{issue_number}/comments", {"body": comment})
            else:
                posted = existing_comment
            if not isinstance(posted, dict):
                raise GitHubError("GitHub did not return the acceptance comment")
            comment_id = posted.get("id")
            if not isinstance(comment_id, int):
                raise GitHubError("GitHub did not return the acceptance comment id")
            state["reportCommentId"] = comment_id
            state["acceptanceCommit"] = commit
            _save_task(task_json_path, data)

        _request("PATCH", f"{base}/issues/{issue_number}", {"state": "closed"})
        state.update({"status": "closed", "acceptanceCommit": commit})
        state.pop("lastError", None)
        _save_task(task_json_path, data)
        print(f"Closed GitHub issue #{issue_number} with the acceptance report")
        return True
    except (GitHubError, KeyError, TypeError, ValueError) as exc:
        state["lastError"] = str(exc) if isinstance(exc, GitHubError) else "invalid GitHub issue metadata"
        _save_task(task_json_path, data)
        print(f"GitHub issue closure pending for {task_json_path.parent.name}: {state['lastError']}", file=sys.stderr)
        return False


def complete_issue(task_json_path: Path) -> bool:
    data = _load_task(task_json_path)
    meta = data.get("meta")
    state = meta.get("githubIssue", {}) if isinstance(meta, dict) else {}
    if not isinstance(state, dict) or not state.get("number"):
        return create_issue(task_json_path) and complete_issue(task_json_path)
    with _task_sync_lock(task_json_path):
        return _complete_issue_locked(task_json_path)


def _accept_task_locked(task_json_path: Path, commit: str, report: str, quality_passed: bool) -> int:
    if not quality_passed:
        print("Acceptance requires --quality-passed after the Trellis quality review.", file=sys.stderr)
        return 2
    data = _load_task(task_json_path)
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        print("Acceptance requires a full Git commit SHA.", file=sys.stderr)
        return 2
    task_dir = task_json_path.parent.resolve()
    report_path = (task_dir / report).resolve()
    try:
        report_path.relative_to(task_dir)
    except ValueError:
        print("Acceptance report must be inside the Trellis task directory.", file=sys.stderr)
        return 2
    try:
        report_text = report_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        print("Acceptance report could not be read.", file=sys.stderr)
        return 2
    if not report_text:
        print("Acceptance report is empty.", file=sys.stderr)
        return 2
    report_bytes = report_text.encode("utf-8")
    if len(report_bytes) > MAX_REPORT_BYTES:
        print(f"Acceptance report exceeds {MAX_REPORT_BYTES} bytes.", file=sys.stderr)
        return 2
    meta = data.setdefault("meta", {})
    if not isinstance(meta, dict):
        print("Acceptance refused: task meta must be a JSON object.", file=sys.stderr)
        return 2
    previous_acceptance = meta.get("githubAcceptance")
    meta["githubAcceptance"] = {
        "qualityPassed": True,
        "commit": commit.lower(),
        "report": report_path.relative_to(task_dir).as_posix(),
        "reportSha256": hashlib.sha256(report_bytes).hexdigest(),
    }
    _save_task(task_json_path, data)
    try:
        _accepted_report(task_json_path, data)
    except GitHubError as exc:
        if previous_acceptance is None:
            meta.pop("githubAcceptance", None)
        else:
            meta["githubAcceptance"] = previous_acceptance
        _save_task(task_json_path, data)
        print(f"Acceptance refused: {exc}", file=sys.stderr)
        return 2
    print("GitHub acceptance recorded; the issue will close after task archive.")
    return 0


def accept_task(task_json_path: Path, commit: str, report: str, quality_passed: bool) -> int:
    with _task_sync_lock(task_json_path):
        return _accept_task_locked(task_json_path, commit, report, quality_passed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create", help="Create or recover the task's GitHub issue")
    subparsers.add_parser("complete", help="Post acceptance report and close an archived task's issue")
    retry = subparsers.add_parser("retry", help="Retry pending issue creation or closure")
    retry.add_argument("task", help="Task directory or name")
    accept = subparsers.add_parser("accept", help="Record the commit and quality acceptance report")
    accept.add_argument("task", help="Task directory or name")
    accept.add_argument("--commit", required=True, help="Full SHA of the committed code")
    accept.add_argument("--report", required=True, help="Report file relative to the task directory")
    accept.add_argument("--quality-passed", action="store_true", help="Confirm the Trellis quality review passed")
    args = parser.parse_args()

    try:
        if args.command in {"create", "complete"}:
            task_json_path = _task_json_from_env()
        else:
            task_json_path = _task_json_from_argument(args.task)
        if args.command == "create":
            return 0 if create_issue(task_json_path) else 1
        if args.command == "complete":
            return 0 if complete_issue(task_json_path) else 1
        if args.command == "retry":
            data = _load_task(task_json_path)
            state = _issue_state(data)
            if state.get("exempt") or state.get("status") == "exempt":
                print("GitHub issue is explicitly exempt for this task.")
                return 0
            if not create_issue(task_json_path):
                return 1
            data = _load_task(task_json_path)
            if data.get("status") == "completed":
                return 0 if complete_issue(task_json_path) else 1
            return 0
        return accept_task(task_json_path, args.commit, args.report, args.quality_passed)
    except GitHubError as exc:
        print(f"GitHub issue sync pending: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
