from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/clone-research-repos.sh"


class CloneResearchRepositoriesTests(unittest.TestCase):
    def run_git(self, *arguments: str, cwd: Path) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def make_source(self, temporary: Path) -> tuple[Path, str]:
        source = temporary / "source"
        source.mkdir()
        self.run_git("init", "--quiet", cwd=source)
        self.run_git("config", "user.name", "Test User", cwd=source)
        self.run_git("config", "user.email", "test@example.com", cwd=source)
        self.run_git("config", "commit.gpgSign", "true", cwd=source)
        (source / "README.md").write_text("fixture\n", encoding="utf-8")
        self.run_git("add", "README.md", cwd=source)
        self.run_git(
            "-c", "commit.gpgSign=false", "commit", "--quiet", "-m", "fixture", cwd=source
        )
        return source, self.run_git("rev-parse", "HEAD", cwd=source)

    def run_script(self, temporary: Path, entries: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "RESEARCH_REPOS_ROOT": str(temporary / "checkouts"),
                "RESEARCH_REPOS_REMOTE_BASE": (temporary / "remotes").as_uri(),
                "RESEARCH_REPOS_ENTRIES": entries,
            }
        )
        return subprocess.run(
            [SCRIPT],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_failed_fetch_does_not_prevent_later_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source, good_sha = self.make_source(temporary)

            remotes = temporary / "remotes"
            good_remote = remotes / "example" / "good"
            good_remote.parent.mkdir(parents=True)
            self.run_git("clone", "--quiet", "--bare", str(source), str(good_remote), cwd=temporary)

            result = self.run_script(
                temporary,
                "example/missing 0000000000000000000000000000000000000000\n"
                f"example/good {good_sha}",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("example/missing could not fetch", result.stderr)
            self.assertIn("Completed with 1 research repository failure", result.stderr)
            self.assertIn(f"example/good pinned at {good_sha}", result.stdout)
            self.assertEqual(
                good_sha,
                self.run_git(
                    "rev-parse", "HEAD", cwd=temporary / "checkouts" / "example__good"
                ),
            )

    def test_empty_and_whitespace_only_override_is_a_successful_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script(Path(directory), " \n\t\n   ")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Done. All research repositories match", result.stdout)

    def test_indented_and_tab_separated_entry_uses_the_parsed_slug(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source, good_sha = self.make_source(temporary)
            good_remote = temporary / "remotes" / "example" / "good"
            good_remote.parent.mkdir(parents=True)
            self.run_git("clone", "--quiet", "--bare", str(source), str(good_remote), cwd=temporary)

            result = self.run_script(temporary, f"  example/good\t{good_sha}  ")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"example/good pinned at {good_sha}", result.stdout)

    def test_malformed_entry_reports_a_clear_error_and_repo_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script(
                Path(directory),
                "example/bad not-a-full-sha unexpected-field",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository entry must contain exactly OWNER/REPO", result.stderr)
        self.assertIn("  - example/bad", result.stderr)


if __name__ == "__main__":
    unittest.main()
