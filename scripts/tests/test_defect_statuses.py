from __future__ import annotations

import csv
import io
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

from scripts import refresh_defect_statuses as reporter


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
            "file\tline\trepo\tnumber\tform\tclaimed_state\tclaim_date\tcontext",
        )

    def test_legacy_tsv_preserves_form_group_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            (checkout / "guides").mkdir()
            (checkout / "guides" / "fixture.md").write_text(
                "The mlx issue #1 and https://github.com/ml-explore/mlx/issues/2 are open.\n"
            )
            sightings = reporter.extract(checkout)

        rows = list(
            csv.DictReader(io.StringIO(reporter.sighting_tsv(sightings)), delimiter="\t")
        )
        self.assertEqual([row["number"] for row in rows], ["2", "1"])

    def test_claim_parser_prefers_bounded_state_after_reference(self) -> None:
        text = (
            'mlx#3821 ("Source builds silently drop every NAX kernel", CLOSED) and its fix '
            'PR #3824 ("Warn at configure time when NAX kernels are disabled", MERGED)'
        )
        start = text.index("#3824")

        state, confidence, diagnostics = reporter.claim_in_clause(
            text, start, start + len("#3824")
        )

        self.assertEqual(state, "MERGED")
        self.assertEqual(confidence, 0.9)
        self.assertEqual(diagnostics, [])

    def test_claim_parser_does_not_reach_across_a_long_clause(self) -> None:
        text = "merged PR #62 " + ("unrelated detail " * 10) + "issue #85"
        start = text.index("#85")

        state, confidence, diagnostics = reporter.claim_in_clause(
            text, start, start + len("#85")
        )

        self.assertIsNone(state)
        self.assertEqual(confidence, 1.0)
        self.assertEqual(diagnostics, [])

    def test_context_is_centered_on_each_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = pathlib.Path(directory)
            (checkout / "guides").mkdir()
            (checkout / "guides" / "fixture.md").write_text(
                ("background detail " * 30) + "The mlx issue #42 remains open.\n"
            )
            sightings = reporter.extract(checkout)

        self.assertEqual(len(sightings), 1)
        self.assertIn("#42", sightings[0]["context"])
        self.assertLessEqual(len(sightings[0]["context"]), 240)

    def test_low_confidence_or_diagnostic_claim_is_ambiguous(self) -> None:
        live = {"kind": "issue", "state": "OPEN", "closedAt": None}

        self.assertEqual(reporter.verdict(live, ["CLOSED"], None, 0.6), "AMBIGUOUS")
        self.assertEqual(
            reporter.verdict(
                live,
                ["CLOSED"],
                None,
                0.9,
                [{"code": "multiple-state-words", "message": "ambiguous"}],
            ),
            "AMBIGUOUS",
        )

    def test_real_corpus_pins_reference_local_claims(self) -> None:
        sightings = reporter.extract(ROOT)

        def claim(path: str, line: int, number: int) -> str | None:
            matches = [
                sighting["claimedState"]
                for sighting in sightings
                if sighting["file"] == path
                and sighting["line"] == line
                and sighting["number"] == number
            ]
            self.assertEqual(len(matches), 1, (path, line, number, matches))
            return matches[0]

        quantization = (
            "guides/part-12-mlx-python/references/03-quantization.md"
        )
        fundamentals = (
            "guides/part-12-mlx-python/references/01-core-fundamentals.md"
        )
        runtime = (
            "guides/part-07-coreai-swift-runtime/references/01-runtime-and-ndarray.md"
        )
        self.assertEqual(claim(quantization, 1266, 3824), "MERGED")
        self.assertEqual(claim(fundamentals, 122, 3924), "CLOSED")
        self.assertIsNone(claim(runtime, 3664, 85))

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

    def test_changed_only_keeps_full_unreachable_summary(self) -> None:
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
                    "--changed-only",
                    "--sleep-seconds",
                    "0",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": empty_path, "SOURCE_DATE_EPOCH": "1785542400"},
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["references"], [])
        self.assertEqual(payload["summary"]["references"], 4)
        self.assertEqual(payload["summary"]["verdicts"]["UNREACHABLE"], 4)

    def test_output_is_written_as_a_complete_json_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.make_fixture_checkout(directory)
            output = checkout / "artifacts" / "defects.json"
            ordinary = checkout / "ordinary.json"
            ordinary.write_text("{}\n")
            expected_mode = stat.S_IMODE(ordinary.stat().st_mode)
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
            actual_mode = stat.S_IMODE(output.stat().st_mode)

        self.assertIn("Report written to", result.stdout)
        self.assertEqual(payload["schemaVersion"], 2)
        self.assertEqual(payload["summary"]["references"], 4)
        self.assertEqual(actual_mode, expected_mode)

    def test_schema_v2_separates_transition_from_resolution(self) -> None:
        live = {
            "kind": "PR", "state": "MERGED", "url": "https://github.com/o/r/pull/1",
            "closedAt": "2026-09-05", "mergedAt": "2026-09-05",
            "stateReason": None, "title": "Fix",
        }
        self.assertEqual(reporter.transition_kind(live, ["OPEN"]), "OPEN_TO_MERGED")
        payload = reporter.structured_payload([], [], "2026-09-05T00:00:00Z", None,
                                              extraction_only=True)
        self.assertIn("unknown", payload["resolutionDispositions"])

    def test_every_resolution_disposition_is_valid_and_unknown_is_report_only(self) -> None:
        self.assertEqual(set(reporter.RESOLUTION_DISPOSITIONS), {
            "fixed", "fixed-with-residual", "merged-unreleased", "closed-unfixed",
            "closed-unmerged", "superseded", "consolidated", "unknown",
        })
        references = reporter.group_references(
            [{
                "repository": "owner/repository", "number": 1, "claimedState": "OPEN",
                "claimDate": None, "id": "s0001", "confidence": 1.0, "diagnostics": [],
            }],
            perform_lookup=False,
            sleep_seconds=0,
        )
        self.assertEqual(references[0]["resolutionDisposition"], "unknown")
        self.assertFalse(references[0]["automaticFixEligible"])
        self.assertEqual(references[0]["transitionKind"], "UNKNOWN")
        self.assertIsNone(references[0]["liveState"])

    def test_same_day_closure_does_not_look_newer_than_a_date_claim(self) -> None:
        live = {
            "kind": "issue", "state": "CLOSED",
            "closedAt": "2026-09-05T23:59:59Z",
        }
        self.assertEqual(
            reporter.verdict(live, [], "2026-09-05"), "STALE-DATE-ONLY"
        )
        self.assertEqual(
            reporter.verdict(live, [], "2026-09-04"), "STATE-CHANGED"
        )

    def test_atomic_output_preserves_existing_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.make_fixture_checkout(directory)
            output = checkout / "defects.json"
            output.write_text("old\n")
            output.chmod(0o640)

            subprocess.run(
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
            )

            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o640)

    def test_wrapper_resolves_relative_output_from_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "wrapper-output.json"
            relative_output = os.path.relpath(output, ROOT)

            subprocess.run(
                [
                    ROOT / "scripts" / "refresh-defect-statuses.sh",
                    "--extract-only",
                    "--format",
                    "json",
                    "--repo",
                    "not/a-repo",
                    "--output",
                    relative_output,
                ],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
