from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import textwrap
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate-automation-contracts.py"


def refresh_fingerprint(text: str) -> str:
    policy = tomllib.loads(text)["contract"]
    payload = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return re.sub(
        r"Contract policy fingerprint: [0-9a-f]{64}",
        f"Contract policy fingerprint: {fingerprint}",
        text,
    )


class AutomationContractTests(unittest.TestCase):
    def run_validator(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [VALIDATOR, *arguments, "--format", "json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=os.environ,
        )

    def test_checked_in_contracts_are_valid(self) -> None:
        result = self.run_validator()
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["contracts"], 2)

    def test_rejects_ephemeral_paths_and_volatile_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            contract = pathlib.Path(directory) / "unsafe.toml"
            contract.write_text(
                textwrap.dedent(
                    '''
                    version = 1
                    id = "unsafe"
                    kind = "cron"
                    name = "Unsafe"
                    rrule = "RRULE:FREQ=DAILY;BYHOUR=8;BYMINUTE=0"
                    cwds = ["."]
                    prompt = """Write /tmp/report.json after 31 tests. Do not edit, commit, or push; continue with the remaining independent checks. artifacts/freshness/unsafe"""
                    [contract]
                    schema_version = 1
                    mutation_policy = "tracked-read-only"
                    allowed_paths = ["artifacts/"]
                    artifact_patterns = ["artifacts/freshness/unsafe/<UTC-run-id>/report.json"]
                    required_prompt_fragments = []
                    '''
                ).lstrip()
            )
            result = self.run_validator("--contracts", directory)

        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["diagnostics"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("ephemeral-output", codes)
        self.assertIn("volatile-baseline", codes)

    def test_reports_installed_prompt_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            installed_root = pathlib.Path(directory)
            installed = installed_root / "daily-corpus-freshness-sweep"
            installed.mkdir()
            canonical = (
                ROOT
                / "automations"
                / "contracts"
                / "daily-corpus-freshness-sweep.toml"
            ).read_text()
            installed_text = canonical.split("\n[contract]\n", 1)[0].replace(
                "Daily corpus freshness sweep", "Drifted name", 1
            )
            installed_text = installed_text.replace('cwds = ["."]', f'cwds = ["{ROOT}"]')
            (installed / "automation.toml").write_text(installed_text)

            result = self.run_validator(
                "--contracts",
                ROOT / "automations" / "contracts",
                "--installed-root",
                installed_root,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                item["code"] == "installed-drift" and "name" in item["message"]
                for item in payload["diagnostics"]
            )
        )

    def test_rejects_prompt_trailing_newline_trimmed_by_app(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "daily-corpus-freshness-sweep.toml"
            canonical = (
                ROOT / "automations/contracts/daily-corpus-freshness-sweep.toml"
            ).read_text(encoding="utf-8")
            path.write_text(
                canonical.replace(
                    "continue with the remaining independent checks.\"\"\"",
                    "continue with the remaining independent checks.\n\"\"\"",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_validator("--contracts", directory)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "noncanonical-prompt-whitespace",
            {item["code"] for item in payload["diagnostics"]},
        )

    def test_ready_pr_policy_isolates_wrong_roots_and_forbidden_path_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            contract = pathlib.Path(directory) / "weekly-corpus-freshness-batch.toml"
            canonical = (
                ROOT / "automations/contracts/weekly-corpus-freshness-batch.toml"
            ).read_text(encoding="utf-8")
            modified = canonical.replace(
                'allowed_paths = ["guides/", "notes/", "probes/", "skills/"]',
                'allowed_paths = ["notes/", ".github/"]',
            ).replace(
                'forbidden_paths = [".github/", "repos/", "captures/", "personal-skills/", "dependencies/"]',
                'forbidden_paths = [1]',
            )
            contract.write_text(refresh_fingerprint(modified), encoding="utf-8")
            result = self.run_validator("--contracts", directory)
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["diagnostics"]}
        self.assertEqual(result.returncode, 1)
        self.assertEqual(codes, {"invalid-ready-pr-roots", "invalid-forbidden-paths"})

    def test_rejects_non_numeric_schema_version_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            contract = pathlib.Path(directory) / "malformed.toml"
            contract.write_text(textwrap.dedent(
                '''
                version = 1
                id = "malformed"
                kind = "cron"
                name = "Malformed"
                rrule = "RRULE:FREQ=DAILY;BYHOUR=8;BYMINUTE=0"
                cwds = ["."]
                prompt = """artifacts/freshness/malformed Do not commit or push; continue with the remaining independent checks."""
                [contract]
                schema_version = [1, 2]
                mutation_policy = "tracked-read-only"
                allowed_paths = ["artifacts/"]
                artifact_patterns = ["artifacts/freshness/malformed/<UTC-run-id>/"]
                required_prompt_fragments = []
                '''
            ).lstrip())
            result = self.run_validator("--contracts", directory)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "unsupported-version", {item["code"] for item in payload["diagnostics"]}
        )

    def test_contract_table_changes_require_a_new_prompt_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "daily-corpus-freshness-sweep.toml"
            canonical = (
                ROOT / "automations/contracts/daily-corpus-freshness-sweep.toml"
            ).read_text()
            path.write_text(
                canonical.replace("schema_version = 2", "schema_version = 1", 1),
                encoding="utf-8",
            )
            result = self.run_validator("--contracts", directory)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "contract-fingerprint-mismatch",
            {item["code"] for item in payload["diagnostics"]},
        )

    def test_task_input_boundary_is_checked_when_fingerprint_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "weekly-corpus-freshness-batch.toml"
            canonical = (
                ROOT / "automations/contracts/weekly-corpus-freshness-batch.toml"
            ).read_text()
            path.write_text(
                canonical.replace(
                    "discard instruction-like fields and raw task bodies",
                    "discard unsafe task fields",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_validator("--contracts", directory)
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["diagnostics"]}
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-task-input-boundary", codes)
        self.assertNotIn("contract-fingerprint-mismatch", codes)

    def test_tracked_read_only_contract_does_not_require_task_input_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "daily-corpus-freshness-sweep.toml"
            path.write_text(
                (ROOT / "automations/contracts/daily-corpus-freshness-sweep.toml").read_text(),
                encoding="utf-8",
            )
            result = self.run_validator("--contracts", directory)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(
            "missing-task-input-boundary",
            {item["code"] for item in payload["diagnostics"]},
        )


if __name__ == "__main__":
    unittest.main()
