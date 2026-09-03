from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate-automation-contracts.py"


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


if __name__ == "__main__":
    unittest.main()
