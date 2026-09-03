from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-probes.sh"


class ProbeRunnerTests(unittest.TestCase):
    def run_runner(
        self, *arguments: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [RUNNER, *arguments],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, **(env or {})},
        )

    def test_rejects_unsafe_run_id_before_creating_artifacts(self) -> None:
        result = self.run_runner("host", "--run-id", "../escape")

        self.assertEqual(result.returncode, 64)
        self.assertIn("invalid run id", result.stderr)

    def test_refuses_to_reuse_a_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            existing = pathlib.Path(directory) / "fixed"
            existing.mkdir()
            result = self.run_runner(
                "host",
                "--run-id",
                "fixed",
                env={"PROBE_ARTIFACT_ROOT": directory},
            )

        self.assertEqual(result.returncode, 73)
        self.assertIn("refusing to reuse artifact directory", result.stderr)

    def test_device_preflight_requires_a_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_runner(
                "device",
                "--run-id",
                "device-missing-destination",
                env={"PROBE_ARTIFACT_ROOT": directory, "DEVELOPMENT_TEAM": "TEAM"},
            )

        self.assertEqual(result.returncode, 64)
        self.assertIn("device mode requires --destination", result.stderr)

    def test_source_declares_clean_build_and_durable_result_paths(self) -> None:
        source = RUNNER.read_text()

        self.assertIn('--scratch-path "$run_root/Build/SwiftPM"', source)
        self.assertIn('-derivedDataPath "$run_root/Build/DerivedData"', source)
        self.assertIn('-resultBundlePath "$run_root/Results/DeviceProbes.xcresult"', source)
        self.assertIn('--project "$project_dir"', source)
        self.assertIn(
            'ln -s "$repo_root/probes/DeviceProbeAssets" "$project_dir/DeviceProbeAssets"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
