#!/usr/bin/env python3
"""Attach Hex-Kit constraints to an existing Git repository."""

import argparse
from pathlib import Path
import subprocess
import sys


DEFAULT_REPO = "https://github.com/imhuis/Hex-Kit.git"
SUBMODULE = ".agent-spec"
START = "<!-- HEX-KIT:START -->"
END = "<!-- HEX-KIT:END -->"
AGENTS_BLOCK = f"""{START}
## Shared engineering constraints (Hex-Kit)

Before planning, editing, or reviewing code in this monorepo:

1. Read `.agent-spec/AGENTS.md` for shared engineering constraints, rule
   precedence, architecture boundaries, workspace protection, and validation.
2. Read the applicable language constraints under `.agent-spec/constitution/`
   (for example, `AGENTS-TypeScript.md` or `AGENTS-Golang.md`).
3. Read the relevant shared guidelines under `.agent-spec/.trellis/spec/`,
   including the applicable technology profiles and thinking guides.
4. Read this project's own `AGENTS.md`, scoped instructions, and module specs.
   Apply shared constraints to this project's actual architecture and stack;
   unfilled template guidelines do not define project conventions.

Paths in Hex-Kit documentation are relative to `.agent-spec/`. Its Trellis
workflow, tasks, journals, hooks, and skills manage Hex-Kit itself. Use this
project's own workflow and runtime for work in this monorepo; do not write its
task state into the shared submodule.

If `.agent-spec/` is missing or uninitialized, run
`git submodule update --init --recursive -- .agent-spec` before proceeding.
Keep shared rules in the submodule instead of copying them into this file.
{END}"""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        # Git diagnostics may contain repository URLs with embedded credentials.
        raise RuntimeError(f"Git {args[0]} failed (exit {result.returncode}). "
                           "Check repository state, access, and Git configuration.")
    return result.stdout.strip()


def agents_content(path: Path) -> bytes:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("AGENTS.md must be a regular file, not a symlink or directory.")
    original = path.read_bytes() if path.exists() else b"# AGENTS.md\n"
    content = original.decode("utf-8")
    if content.count(START) != content.count(END) or content.count(START) > 1:
        raise ValueError("AGENTS.md has malformed or duplicate Hex-Kit markers.")
    newline = "\r\n" if "\r\n" in content else "\n"
    block = AGENTS_BLOCK.replace("\n", newline)
    if START in content:
        start, end = content.index(START), content.index(END)
        if end < start:
            raise ValueError("AGENTS.md has reversed Hex-Kit markers.")
        content = content[:start] + block + content[end + len(END):]
    else:
        separator = "" if content.endswith(newline * 2) else (
            newline if content.endswith(newline) else newline * 2
        )
        content += separator + block + newline
    return content.encode("utf-8")


def initialize(target: Path, repo: str | None) -> None:
    root = target.resolve(strict=True)
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("Target must be the root of an existing Git repository.")
    if repo is not None and (repo.startswith("-") or not repo.strip()):
        raise ValueError("Repository URL or path must be nonempty and cannot start with '-'.")

    agents = root / "AGENTS.md"
    updated = agents_content(agents)
    modules = root / ".gitmodules"
    if modules.is_symlink() or (modules.exists() and not modules.is_file()):
        raise ValueError(".gitmodules must be a regular file.")
    entries = git(root, "ls-files", "--stage", "--", SUBMODULE).splitlines()
    if entries:
        if len(entries) != 1 or not entries[0].startswith("160000 "):
            raise ValueError(".agent-spec is already tracked as something other than a submodule.")
        if not modules.exists():
            raise ValueError("Existing .agent-spec submodule has no .gitmodules file.")
        if git(root, "config", "-f", ".gitmodules", "--get", f"submodule.{SUBMODULE}.path") != SUBMODULE:
            raise ValueError("Existing submodule must have both name and path .agent-spec.")
        registered_repo = git(root, "config", "-f", ".gitmodules", "--get",
                              f"submodule.{SUBMODULE}.url")
        if repo is not None and registered_repo != repo:
            raise ValueError("Existing .agent-spec uses a different repository; pass its URL via --repo.")
        destination = root / SUBMODULE
        if (destination / ".git").exists():
            if git(destination, "status", "--porcelain"):
                raise ValueError("Resolve pending changes inside .agent-spec first.")
        else:
            git(root, "submodule", "update", "--init", "--", SUBMODULE)
    else:
        # submodule add stages .gitmodules; refuse to mix in pending edits.
        if git(root, "status", "--porcelain", "--ignore-submodules=none", "--",
               ".gitmodules", SUBMODULE):
            raise ValueError("Commit or resolve pending changes in .gitmodules/.agent-spec first.")
        destination = root / SUBMODULE
        if destination.exists() or destination.is_symlink():
            raise ValueError(".agent-spec already exists; refusing to replace it.")
        if modules.exists():
            result = subprocess.run(
                ["git", "-C", str(root), "config", "-f", ".gitmodules",
                 "--get-regexp", r"^submodule\..*\.(path|url)$"],
                capture_output=True, text=True,
            )
            if result.returncode not in (0, 1):
                raise ValueError("Cannot parse .gitmodules.")
            if any(line.split(maxsplit=1)[0].startswith(f"submodule.{SUBMODULE}.")
                   or line.split(maxsplit=1)[-1] == SUBMODULE
                   for line in result.stdout.splitlines()):
                raise ValueError(".gitmodules already contains a conflicting .agent-spec entry.")
        git(root, "submodule", "add", "--name", SUBMODULE, "--",
            repo or DEFAULT_REPO, SUBMODULE)

    if not (root / SUBMODULE / "AGENTS.md").is_file():
        raise ValueError("Submodule has no AGENTS.md; verify --repo points to Hex-Kit. "
                         "Git changes are retained for inspection; target AGENTS.md was not changed.")
    if not agents.exists() or agents.read_bytes() != updated:
        agents.write_bytes(updated)
    print(f"Initialized Hex-Kit constraints in {root}")
    print("Review .gitmodules, .agent-spec, and AGENTS.md. No commit was created.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, default=Path.cwd(),
                        help="Existing Git repository root (default: current directory)")
    parser.add_argument("--repo",
                        help="Repository URL/path (default: existing submodule URL or Hex-Kit remote)")
    args = parser.parse_args()
    try:
        initialize(args.target, args.repo)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Initialization failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
