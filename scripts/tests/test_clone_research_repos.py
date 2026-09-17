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

    def test_failed_fetch_does_not_prevent_later_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source"
            source.mkdir()
            self.run_git("init", "--quiet", cwd=source)
            self.run_git("config", "user.name", "Test User", cwd=source)
            self.run_git("config", "user.email", "test@example.com", cwd=source)
            (source / "README.md").write_text("fixture\n", encoding="utf-8")
            self.run_git("add", "README.md", cwd=source)
            self.run_git("commit", "--quiet", "-m", "fixture", cwd=source)
            good_sha = self.run_git("rev-parse", "HEAD", cwd=source)

            remotes = temporary / "remotes"
            good_remote = remotes / "example" / "good"
            good_remote.parent.mkdir(parents=True)
            self.run_git("clone", "--quiet", "--bare", str(source), str(good_remote), cwd=temporary)

            checkouts = temporary / "checkouts"
            environment = os.environ.copy()
            environment.update(
                {
                    "RESEARCH_REPOS_ROOT": str(checkouts),
                    "RESEARCH_REPOS_REMOTE_BASE": remotes.as_uri(),
                    "RESEARCH_REPOS_ENTRIES": (
                        "example/missing 0000000000000000000000000000000000000000\n"
                        f"example/good {good_sha}"
                    ),
                }
            )
            result = subprocess.run(
                [SCRIPT],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("example/missing could not fetch", result.stderr)
            self.assertIn("Completed with 1 research repository failure", result.stderr)
            self.assertIn(f"example/good pinned at {good_sha}", result.stdout)
            self.assertEqual(
                good_sha,
                self.run_git("rev-parse", "HEAD", cwd=checkouts / "example__good"),
            )


if __name__ == "__main__":
    unittest.main()
