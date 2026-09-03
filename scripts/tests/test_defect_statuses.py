from __future__ import annotations

import csv
import io
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "defect-status"


class DefectStatusCharacterizationTests(unittest.TestCase):
    def test_current_extraction_matches_golden(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            (checkout / "guides").mkdir()
            (checkout / "scripts").mkdir()
            shutil.copy2(FIXTURES / "clause-scope.md", checkout / "guides" / "fixture.md")
            shutil.copy2(
                ROOT / "scripts" / "refresh-defect-statuses.sh",
                checkout / "scripts" / "refresh-defect-statuses.sh",
            )
            result = subprocess.run(
                [checkout / "scripts" / "refresh-defect-statuses.sh", "--extract-only"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            )

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


if __name__ == "__main__":
    unittest.main()
