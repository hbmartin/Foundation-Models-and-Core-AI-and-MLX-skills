from __future__ import annotations

import csv
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "defect-status"


class DefectStatusGoldenTests(unittest.TestCase):
    def make_fixture_checkout(self, directory: str) -> pathlib.Path:
        checkout = pathlib.Path(directory)
        (checkout / "guides").mkdir()
        (checkout / "guides" / "fixture.md").write_text(
            (FIXTURES / "clause-scope.md").read_text()
        )
        return checkout

    def run_report(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.make_fixture_checkout(directory)
            return subprocess.run(
                [
                    ROOT / "scripts" / "refresh_defect_statuses.py",
                    "--source-root",
                    checkout,
                    *arguments,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "SOURCE_DATE_EPOCH": "1785542400"},
            )

    def test_clause_aware_extraction_matches_golden(self) -> None:
        result = self.run_report("--extract-only")

        rows = list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t"))
        actual = [
            {
                key: row[key]
                for key in ("claim_date", "claimed_state", "form", "number", "repo")
            }
            for row in rows
        ]
        expected = json.loads((FIXTURES / "current-extraction.json").read_text())
        self.assertEqual(actual, expected)

    def test_structured_extraction_matches_golden(self) -> None:
        result = self.run_report("--extract-only", "--format", "json")
        actual = json.loads(result.stdout)
        expected = json.loads((FIXTURES / "structured-extraction.json").read_text())

        self.assertEqual(actual, expected)

    def test_wrapper_preserves_legacy_extract_only_tsv(self) -> None:
        result = subprocess.run(
            [
                ROOT / "scripts" / "refresh-defect-statuses.sh",
                "--extract-only",
                "--repo",
                "not/a-repo",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.stdout.splitlines()[0],
            "file\tline\trepo\tnumber\tform\tclaimed_state\tclaim_date\tconfidence\tcontext",
        )

    def test_unreachable_github_is_structured_and_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as empty_path:
            checkout = self.make_fixture_checkout(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    ROOT / "scripts" / "refresh_defect_statuses.py",
                    "--source-root",
                    checkout,
                    "--format",
                    "json",
                    "--sleep-seconds",
                    "0",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": empty_path, "SOURCE_DATE_EPOCH": "1785542400"},
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["summary"]["verdicts"]["UNREACHABLE"], 4)
        self.assertTrue(
            all(
                reference["diagnostics"][-1]["code"] == "github-unreachable"
                for reference in payload["references"]
            )
        )

    def test_output_is_written_as_a_complete_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.make_fixture_checkout(directory)
            output = checkout / "artifacts" / "defects.json"
            result = subprocess.run(
                [
                    sys.executable,
                    ROOT / "scripts" / "refresh_defect_statuses.py",
                    "--source-root",
                    checkout,
                    "--extract-only",
                    "--format",
                    "json",
                    "--output",
                    output,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "SOURCE_DATE_EPOCH": "1785542400"},
            )
            payload = json.loads(output.read_text())

        self.assertIn("Report written to", result.stdout)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["summary"]["references"], 4)


if __name__ == "__main__":
    unittest.main()
