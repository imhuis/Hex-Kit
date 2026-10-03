"""Integration tests using local repositories; no network or extra packages."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "init-project.py"


class InitializeProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="hex-kit-test-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "hex kit"
        self.target = base / "my monorepo"
        self.env = {**os.environ, "GIT_ALLOW_PROTOCOL": "file",
                    "GIT_TERMINAL_PROMPT": "0"}
        for root in (self.source, self.target):
            root.mkdir()
            self.git(root, "init")
            (root / "AGENTS.md").write_bytes(b"# Local rules\r\n\r\nKeep this rule.\r\n")
            self.git(root, "add", "AGENTS.md")
            if root == self.source:
                (root / "scripts").mkdir()
                (root / "scripts" / SCRIPT.name).write_bytes(SCRIPT.read_bytes())
                self.git(root, "add", "scripts")
            self.commit(root)

    def git(self, root: Path, *args: str) -> str:
        result = subprocess.run(["git", "-C", str(root), *args], env=self.env,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def commit(self, root: Path) -> None:
        self.git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "core.hooksPath=/dev/null", "commit", "-m", "test fixture")

    def initialize(self, success: bool = True, repo: Path | None = None) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.target),
                                 "--repo", str(repo or self.source)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return result

    def save_initialization(self) -> None:
        self.initialize()
        self.git(self.target, "add", "AGENTS.md")
        self.commit(self.target)

    def test_initialization_preserves_rules_and_unrelated_staging(self) -> None:
        (self.target / "work.txt").write_text("staged work", encoding="utf-8")
        self.git(self.target, "add", "work.txt")
        head = self.git(self.target, "rev-parse", "HEAD")
        agents_index = self.git(self.target, "show", ":AGENTS.md")
        self.initialize()
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(self.target, "show", ":AGENTS.md"), agents_index)
        self.assertEqual(self.git(self.target, "show", ":work.txt"), "staged work")
        self.assertEqual(self.git(self.target, "config", "-f", ".gitmodules", "--get",
                                  "submodule..agent-spec.path"), ".agent-spec")
        self.assertTrue(self.git(self.target, "ls-files", "--stage", "--", ".agent-spec")
                        .startswith("160000 "))
        content = (self.target / "AGENTS.md").read_bytes()
        self.assertTrue(content.startswith(b"# Local rules\r\n\r\nKeep this rule.\r\n"))
        self.assertIn(b".agent-spec/AGENTS.md", content)
        self.assertNotIn(b"\n", content.replace(b"\r\n", b""))

    def test_repeat_is_idempotent_and_does_not_advance_revision(self) -> None:
        self.save_initialization()
        before = (self.target / "AGENTS.md").read_bytes()
        pinned = self.git(self.target / ".agent-spec", "rev-parse", "HEAD")
        (self.source / "new.txt").write_text("new upstream work", encoding="utf-8")
        self.git(self.source, "add", "new.txt")
        self.commit(self.source)
        self.initialize()
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), before)
        self.assertEqual(self.git(self.target / ".agent-spec", "rev-parse", "HEAD"), pinned)
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")

    def test_uninitialized_submodule_is_restored(self) -> None:
        self.save_initialization()
        self.git(self.target, "submodule", "deinit", "--", ".agent-spec")
        self.initialize()
        self.assertTrue((self.target / ".agent-spec" / "AGENTS.md").is_file())

    def test_missing_agents_file_is_created(self) -> None:
        self.git(self.target, "rm", "AGENTS.md")
        self.commit(self.target)
        self.initialize()
        self.assertTrue((self.target / "AGENTS.md").read_text(encoding="utf-8")
                        .startswith("# AGENTS.md\n"))

    def test_new_repository_without_commits(self) -> None:
        self.target = self.target.parent / "empty repo"
        self.target.mkdir()
        self.git(self.target, "init")
        self.initialize()
        self.assertTrue((self.target / ".agent-spec" / "AGENTS.md").is_file())

    def test_manual_submodule_add_then_initialize_from_target(self) -> None:
        self.target = self.target.parent / "three step repo"
        self.target.mkdir()
        self.git(self.target, "init")
        self.git(self.target, "submodule", "add", "--name", ".agent-spec",
                 "--", str(self.source), ".agent-spec")
        staged_before = self.git(self.target, "diff", "--cached")
        result = subprocess.run(
            [sys.executable, "-B", ".agent-spec/scripts/init-project.py"],
            cwd=self.target, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(self.target, "diff", "--cached"), staged_before)
        self.assertIn(".agent-spec/AGENTS.md",
                      (self.target / "AGENTS.md").read_text(encoding="utf-8"))

    def test_updates_only_managed_section(self) -> None:
        self.save_initialization()
        path = self.target / "AGENTS.md"
        path.write_text("Before\n<!-- HEX-KIT:START -->\nOld rules\n"
                        "<!-- HEX-KIT:END -->\nAfter\n", encoding="utf-8")
        self.initialize()
        content = path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("Before\n<!-- HEX-KIT:START -->"))
        self.assertTrue(content.endswith("<!-- HEX-KIT:END -->\nAfter\n"))
        self.assertNotIn("Old rules", content)
        self.assertEqual(content.count("<!-- HEX-KIT:START -->"), 1)

    def test_dirty_submodule_is_rejected_even_when_git_ignores_it(self) -> None:
        self.save_initialization()
        self.git(self.target, "config", "submodule..agent-spec.ignore", "all")
        path = self.target / ".agent-spec" / "AGENTS.md"
        path.write_text("pending submodule work", encoding="utf-8")
        self.initialize(success=False)
        self.assertEqual(path.read_text(), "pending submodule work")

    def test_malformed_markers_fail_before_git_mutation(self) -> None:
        path = self.target / "AGENTS.md"
        content = b"My work\n<!-- HEX-KIT:START -->\n"
        path.write_bytes(content)
        before = self.git(self.target, "status", "--porcelain")
        self.initialize(success=False)
        self.assertEqual(path.read_bytes(), content)
        self.assertEqual(self.git(self.target, "status", "--porcelain"), before)
        self.assertFalse((self.target / ".gitmodules").exists())

    def test_existing_directory_is_not_replaced(self) -> None:
        destination = self.target / ".agent-spec"
        destination.mkdir()
        (destination / "work.txt").write_text("preserve", encoding="utf-8")
        self.initialize(success=False)
        self.assertEqual((destination / "work.txt").read_text(), "preserve")
        self.assertFalse((self.target / ".gitmodules").exists())

    def test_pending_gitmodules_changes_are_preserved(self) -> None:
        path = self.target / ".gitmodules"
        path.write_text("# pending work\n", encoding="utf-8")
        self.git(self.target, "add", ".gitmodules")
        path.write_text("# further pending work\n", encoding="utf-8")
        self.initialize(success=False)
        self.assertEqual(self.git(self.target, "show", ":.gitmodules"), "# pending work")
        self.assertEqual(path.read_text(), "# further pending work\n")

    def test_different_repository_is_rejected_without_changes(self) -> None:
        self.save_initialization()
        self.initialize(success=False, repo=self.source.parent / "other")
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
