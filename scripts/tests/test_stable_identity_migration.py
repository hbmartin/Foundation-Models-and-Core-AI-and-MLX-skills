from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MIGRATE = ROOT / "scripts/migrate-stable-identities.py"


def load_module():
    spec = importlib.util.spec_from_file_location("migrate_stable_identities", MIGRATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = load_module()


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
                [sys.executable, MIGRATE, "callouts", "--classified-dir", classified, "--write"],
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
                [sys.executable, MIGRATE, "callouts", "--classified-dir", classified, "--write"],
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
                [sys.executable, MIGRATE, "snippets", "--results", results, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            migrated = results.read_text(encoding="utf-8").splitlines()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(migrated[0].split("\t")[-2:], ["snippet_id", "content_hash"])
        self.assertEqual(migrated[1].split("\t")[-2:], current[1].split("\t")[-2:])

    def test_callout_migration_validates_all_files_before_writing(self) -> None:
        extracted = subprocess.run(
            [sys.executable, ROOT / "scripts/extract-callouts.py", ROOT / "guides"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.splitlines()[0].split("\t")
        with tempfile.TemporaryDirectory() as directory:
            classified = pathlib.Path(directory)
            valid = classified / "a-valid.tsv"
            original = "\t".join((*extracted[:4], "caution-note", "reviewed blurb")) + "\n"
            valid.write_text(original, encoding="utf-8")
            invalid = list(extracted[:4])
            invalid[1] = "999999"
            (classified / "z-invalid.tsv").write_text(
                "\t".join((*invalid, "caution-note", "invalid blurb")) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, MIGRATE, "callouts", "--classified-dir", classified, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(valid.read_text(encoding="utf-8"), original)

    def test_relative_dry_run_paths_and_literal_quotes_are_supported(self) -> None:
        extracted = subprocess.run(
            [sys.executable, ROOT / "scripts/extract-callouts.py", ROOT / "guides"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.splitlines()[0].split("\t")
        with tempfile.TemporaryDirectory() as directory:
            classified = pathlib.Path(directory) / "classified"
            classified.mkdir()
            (classified / "fixture.tsv").write_text(
                "\t".join((*extracted[:4], "caution-note", 'a "literal quote')) + "\n",
                encoding="utf-8",
            )
            relative = os.path.relpath(classified, ROOT)
            result = subprocess.run(
                [sys.executable, MIGRATE, "callouts", "--classified-dir", relative],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("would migrate", result.stdout)

            current = (ROOT / "notes/snippet-verification/results.tsv").read_text(
                encoding="utf-8"
            ).splitlines()
            header = current[0].split("\t")[:-2]
            row = current[1].split("\t")[:-2]
            row[header.index("first_error")] = '"literal diagnostic'
            results = pathlib.Path(directory) / "results.tsv"
            results.write_text(
                "\t".join(header) + "\n" + "\t".join(row) + "\n", encoding="utf-8"
            )
            migrated = subprocess.run(
                [sys.executable, MIGRATE, "snippets", "--results", results, "--write"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(migrated.returncode, 0, migrated.stderr)
            values = results.read_text(encoding="utf-8").splitlines()[1].split("\t")
            self.assertEqual(values[header.index("first_error")], '"literal diagnostic')

    def test_partial_output_from_a_failed_extractor_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            MIGRATION.command_rows([
                sys.executable, "-c", "print('partial\\trow'); raise SystemExit(1)",
            ])
        self.assertIn("command failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
