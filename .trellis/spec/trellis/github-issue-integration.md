# GitHub Issue Integration

## 1. Scope / Trigger

Use this contract when a Trellis task should be tracked in GitHub. The boundary
is the local task lifecycle (`task.py` and `task.json`) to GitHub Issues REST
API. The integration is best-effort for synchronization and strict only for
closing a linked issue: GitHub outages must not prevent local work, while a
known issue cannot be closed without a committed change and accepted report.

## 2. Signatures

```text
task.py create <title> --description <text> [--no-github-issue]
github_issue.py create                         # TASK_JSON_PATH lifecycle hook
github_issue.py accept <task> --commit <sha> --report <path> --quality-passed
github_issue.py complete                      # TASK_JSON_PATH after-archive hook
github_issue.py retry <task>
```

The API operations are `GET /search/issues`, `POST /repos/{owner}/{repo}/issues`,
`POST /repos/{owner}/{repo}/issues/{number}/comments`, and
`PATCH /repos/{owner}/{repo}/issues/{number}`.

## 3. Contracts

- Repository identity comes from `remote.origin.url`; supported hosts are
  `github.com` and `ssh.github.com` with an owner/repository path.
- `GITHUB_TOKEN` or `GH_TOKEN` supplies credentials. The token requires Issues
  read/write access and must never be persisted or printed.
- `meta.githubIssue` stores `status`, `exempt`, a stable SHA-256 task `marker`, `number`,
  `url`, `repository`, `reportCommentId`, `acceptanceCommit`, and a non-secret
  `lastError`.
- `meta.githubAcceptance` stores `qualityPassed: true`, a full 40-character
  commit SHA, a report path relative to the task directory, and the SHA-256 of
  its trimmed UTF-8 contents. Changing an accepted report requires recording
  acceptance again.
- Acceptance reports must be non-empty UTF-8 files inside the task directory
  and no larger than 55,000 bytes. The referenced commit must exist and be an
  ancestor of the current branch `HEAD`.
- A linked issue requires a valid acceptance record before task archival. The
  after-archive hook posts the report and commit link, then closes the issue.
- Missing credentials, network/API errors, and missing repository remotes set
  issue sync to `pending`; they do not stop task creation or archival. Retry is
  safe: issue discovery uses a stable task marker, existing report comments are
  found using an embedded marker, and issue closure is idempotent.
- `--no-github-issue` stores `status: exempt`; exempt tasks skip synchronization
  and the archive gate.

## 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Supported GitHub remote and token available | Create or recover the issue and persist number/URL |
| No token, unsupported remote, or API failure | Persist `pending` and a safe error; allow local lifecycle to continue |
| Explicit exemption | Skip issue creation, completion, and archive validation |
| Linked issue without quality acceptance | Refuse task archive before mutating task state |
| Missing, empty, oversized, or out-of-task report | Refuse acceptance and issue closure |
| Invalid or non-ancestor commit SHA | Refuse acceptance and issue closure |
| Archived task with pending GitHub sync | Retry issue creation, report posting, and closure from persisted task data |

## 5. Good / Base / Bad Cases

- **Good**: Run quality review, commit implementation, write the report, record
  acceptance, archive, then post the report and close the issue.
- **Base**: GitHub is offline during task creation. Work locally; after network
  access returns, run `github_issue.py retry <task>`.
- **Bad**: Archive a linked task before recording quality acceptance. The
  archive command refuses before changing its status or moving its directory.
- **Bad**: Put a report path outside the task directory or use an arbitrary
  commit SHA. Acceptance is rejected.

## 6. Tests Required

When adding or changing tests for this contract, assert:

- Task creation marks explicit exemptions and otherwise attempts the create
  hook without storing credentials.
- Missing credentials persist pending state without an HTTP request or task
  creation failure.
- Archive rejects a linked issue unless quality status, report, and reachable
  commit all validate, and leaves task state unchanged on refusal.
- Successful completion posts one report comment and closes the issue; retries
  do not duplicate that comment.
- Archived task paths can be resolved for retry while paths outside the task
  tree remain rejected.

Do not add a new test framework or broaden tests beyond these behaviors.

## 7. Wrong vs Correct

### Wrong

```python
if task_data["status"] == "completed":
    close_github_issue()
```

Completion alone does not prove that implementation was committed or quality
review passed, and the issue would close without a useful report.

### Correct

```text
quality review passes → commit SHA + task-local report recorded
→ archive validates acceptance → issue comment is posted → issue is closed
```

Persist issue identifiers and acceptance evidence in `task.json`; never infer
external synchronization state from transient hook output.
