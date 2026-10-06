import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "capture-apple-docs-watch.py"


class AppleDocsWatchTests(unittest.TestCase):
    def run_capture(self, overview: str, member: str):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            overview_path = root / "overview-source.md"
            member_path = root / "member-source.md"
            overview_path.write_text(overview, encoding="utf-8")
            member_path.write_text(member, encoding="utf-8")
            output = root / "capture"
            result = subprocess.run(
                [sys.executable, SCRIPT, "--output", output,
                 "--overview-source", overview_path,
                 "--member-source", member_path],
                text=True, capture_output=True, check=False,
            )
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            return result, manifest

    def test_agreeing_current_pages_pass_and_are_hashed(self):
        result, manifest = self.run_capture(
            "`func resolved(in transcript: some Sequence<Entry>)`",
            "func resolved(in transcript: some Sequence<Entry>)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(manifest["pagesAgree"])
        self.assertEqual(
            [item["methodSpellings"] for item in manifest["captures"]],
            [["resolved"], ["resolved"]],
        )
        self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["captures"]))

    def test_disagreement_is_preserved_and_fails(self):
        result, manifest = self.run_capture(
            "func resolve(in transcript: Transcript)",
            "func resolved(in transcript: some Sequence<Entry>)",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(manifest["pagesAgree"])
        self.assertEqual(manifest["captures"][0]["methodSpellings"], ["resolve"])

    def test_missing_declarations_fail(self):
        result, manifest = self.run_capture("No declaration here", "func resolved(in:)")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(manifest["pagesAgree"])
        self.assertEqual(manifest["captures"][0]["methodSpellings"], [])

    def test_capture_failure_retains_independent_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            member = root / "member.md"
            member.write_text("func resolved(in:)")
            result = subprocess.run([sys.executable, SCRIPT, "--output", root / "out",
                "--overview-source", root / "missing.md", "--member-source", member],
                capture_output=True, text=True)
            manifest = json.loads((root / "out/manifest.json").read_text())
            self.assertEqual(result.returncode, 1)
            self.assertFalse(manifest["pagesAgree"])
            self.assertEqual(manifest["captures"][0]["status"], "failed")
            self.assertEqual(manifest["captures"][1]["status"], "captured")
            self.assertEqual(len(manifest["captures"][1]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
