from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MIGRATE = ROOT / "scripts/migrate-stable-identities.py"


class StableIdentityMigrationTests(unittest.TestCase):
    def test_callout_migration_rekeys_an_exact_legacy_row(self) -> None:
        extracted = subprocess.run(
            [sys.executable, ROOT / "scripts/extract-callouts.py", ROOT / "guides"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.splitlines()[0].split("\t")
        with tempfile.TemporaryDirectory() as directory:
            classified = pathlib.Path(directory)
            legacy = classified / "fixture.tsv"
            legacy.write_text(
                "\t".join((*extracted[:4], "caution-note", "reviewed blurb")) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [MIGRATE, "callouts", "--classified-dir", classified, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            lines = legacy.read_text(encoding="utf-8").splitlines()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(lines[0], "# schema-version: 2")
        self.assertEqual(lines[1].split("\t")[1:3], extracted[6:8])

    def test_callout_migration_rejects_a_moved_legacy_row(self) -> None:
        extracted = subprocess.run(
            [sys.executable, ROOT / "scripts/extract-callouts.py", ROOT / "guides"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.splitlines()[0].split("\t")
        extracted[1] = "999999"
        with tempfile.TemporaryDirectory() as directory:
            classified = pathlib.Path(directory)
            (classified / "fixture.tsv").write_text(
                "\t".join((*extracted[:4], "caution-note", "reviewed blurb")) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [MIGRATE, "callouts", "--classified-dir", classified, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restore the pre-edit corpus", result.stderr)

    def test_snippet_migration_adds_identity_columns_without_reverification(self) -> None:
        current = (ROOT / "notes/snippet-verification/results.tsv").read_text(
            encoding="utf-8"
        ).splitlines()
        header = current[0].split("\t")[:-2]
        row = current[1].split("\t")[:-2]
        with tempfile.TemporaryDirectory() as directory:
            results = pathlib.Path(directory) / "results.tsv"
            results.write_text(
                "\t".join(header) + "\n" + "\t".join(row) + "\n", encoding="utf-8"
            )
            result = subprocess.run(
                [MIGRATE, "snippets", "--results", results, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            migrated = results.read_text(encoding="utf-8").splitlines()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(migrated[0].split("\t")[-2:], ["snippet_id", "content_hash"])
        self.assertEqual(migrated[1].split("\t")[-2:], current[1].split("\t")[-2:])


if __name__ == "__main__":
    unittest.main()
