from __future__ import annotations

import os
import pathlib
import plistlib
import re
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-probes.sh"
FOUNDATION_MODELS_PROBES = (
    ROOT / "probes" / "Tests" / "ProbesTests" / "FoundationModelsProbes.swift"
)


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

    def make_command_shim(self, directory: pathlib.Path, name: str) -> pathlib.Path:
        shim = directory / name
        shim.write_text(
            """#!/bin/sh
set -eu
{
  printf 'pwd=%s\\n' "$PWD"
  printf 'artifact=%s\\n' "${PROBE_ARTIFACT_DIR-}"
  printf 'arg=%s\\n' "$@"
} > "$COMMAND_LOG"
"""
        )
        shim.chmod(0o755)
        return shim

    def make_xcodebuild_shim(self, directory: pathlib.Path) -> pathlib.Path:
        shim = directory / "xcodebuild"
        shim.write_text(
            """#!/bin/sh
set -eu
{
  printf 'command=%s\n' "$*"
  printf 'pwd=%s\n' "$PWD"
  printf 'artifact=%s\n' "${PROBE_ARTIFACT_DIR-}"
  printf 'arg=%s\n' "$@"
} >> "$COMMAND_LOG"

if [ "${1-}" = build-for-testing ]; then
  previous=
  derived_data=
  for argument in "$@"; do
    if [ "$previous" = -derivedDataPath ]; then
      derived_data=$argument
    fi
    previous=$argument
  done
  products="$derived_data/Build/Products"
  mkdir -p "$products"
  printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
    '<plist version="1.0"><dict><key>TestConfigurations</key><array><dict><key>TestTargets</key><array><dict><key>EnvironmentVariables</key><dict><key>EXISTING</key><string>preserved</string></dict></dict></array></dict></array></dict></plist>' \
    > "$products/Probes-Package.xctestrun"
fi
"""
        )
        shim.chmod(0o755)
        return shim

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

            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

        self.assertEqual(result.returncode, 64)
        self.assertIn("device mode requires --destination", result.stderr)

    def test_unknown_mode_does_not_reserve_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_runner(
                "typo",
                "--run-id",
                "retryable",
                env={"PROBE_ARTIFACT_ROOT": directory},
            )

            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

        self.assertEqual(result.returncode, 64)
        self.assertIn("unknown mode", result.stderr)

    def test_missing_xcodegen_does_not_reserve_device_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_runner(
                "device",
                "--run-id",
                "retryable-device",
                "--destination",
                "platform=iOS,id=example",
                "--team-id",
                "TEAM",
                env={
                    "PATH": os.defpath,
                    "PROBE_ARTIFACT_ROOT": directory,
                },
            )

            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

        self.assertEqual(result.returncode, 69)
        self.assertIn("xcodegen is required", result.stderr)

    def test_host_exports_durable_probe_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            shims = root / "bin"
            shims.mkdir()
            self.make_command_shim(shims, "swift")
            command_log = root / "host-command.txt"

            result = self.run_runner(
                "host",
                "--run-id",
                "host-artifacts",
                env={
                    "COMMAND_LOG": str(command_log),
                    "PATH": f"{shims}{os.pathsep}{os.defpath}",
                    "PROBE_ARTIFACT_ROOT": str(root / "artifacts"),
                },
            )
            log = command_log.read_text()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"artifact={root / 'artifacts/host-artifacts/ProbeArtifacts'}",
            log,
        )
        self.assertIn("arg=--package-path", log)
        self.assertIn("arg=--scratch-path", log)

    def test_simulator_preserves_tool_hosted_lane_and_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            shims = root / "bin"
            shims.mkdir()
            self.make_xcodebuild_shim(shims)
            command_log = root / "simulator-command.txt"

            result = self.run_runner(
                "simulator",
                "--run-id",
                "simulator-baseline",
                "--",
                "-only-testing:ProbesTests/ExampleTests/testExample",
                env={
                    "COMMAND_LOG": str(command_log),
                    "PATH": f"{shims}{os.pathsep}{os.defpath}",
                    "PROBE_ARTIFACT_ROOT": str(root / "artifacts"),
                    "PROBE_ENUM_RUNS": "37",
                },
            )
            log = command_log.read_text()
            xctestrun = next(
                (root / "artifacts/simulator-baseline/Build/DerivedData").rglob(
                    "*.xctestrun"
                )
            )
            with xctestrun.open("rb") as source:
                target_environment = plistlib.load(source)["TestConfigurations"][0][
                    "TestTargets"
                ][0]["EnvironmentVariables"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("command=build-for-testing", log)
        self.assertIn("command=test-without-building", log)
        self.assertIn(f"pwd={ROOT / 'probes'}", log)
        self.assertIn("arg=Probes-Package", log)
        self.assertIn("arg=platform=iOS Simulator,name=iPhone 17 Pro,OS=27.0", log)
        self.assertIn("arg=-only-testing:ProbesTests/ExampleTests/testExample", log)
        self.assertNotIn("DeviceProbes", log)
        self.assertIn(
            f"artifact={root / 'artifacts/simulator-baseline/ProbeArtifacts'}",
            log,
        )
        self.assertEqual(target_environment["EXISTING"], "preserved")
        self.assertEqual(target_environment["PROBE_ENUM_RUNS"], "37")
        self.assertEqual(
            target_environment["PROBE_ARTIFACT_DIR"],
            str(root / "artifacts/simulator-baseline/ProbeArtifacts"),
        )

    def test_source_declares_clean_build_and_durable_result_paths(self) -> None:
        source = RUNNER.read_text()

        self.assertIn('--scratch-path "$run_root/Build/SwiftPM"', source)
        self.assertIn('-derivedDataPath "$run_root/Build/DerivedData"', source)
        self.assertIn('test-without-building', source)
        self.assertIn('-xctestrun "$xctestrun_path"', source)
        self.assertIn('-resultBundlePath "$run_root/Results/Probes-Package.xcresult"', source)
        self.assertIn('-resultBundlePath "$run_root/Results/DeviceProbes.xcresult"', source)
        self.assertIn('--project "$project_dir"', source)
        self.assertIn(
            'ln -s "$repo_root/probes/DeviceProbeAssets" "$project_dir/DeviceProbeAssets"',
            source,
        )

    def test_every_default_model_access_is_preceded_by_explicit_consent(self) -> None:
        source = FOUNDATION_MODELS_PROBES.read_text(encoding="utf-8")
        test_methods = re.split(r"(?=^    func test)", source, flags=re.MULTILINE)[1:]

        unchecked = []
        for method in test_methods:
            access = method.find("SystemLanguageModel.default")
            if access < 0:
                continue
            consent = [
                position
                for spelling in (
                    "try skipUnlessHostModelAccessAllowed(",
                    "try skipUnlessModelAvailable(",
                )
                if 0 <= (position := method.find(spelling)) < access
            ]
            if not consent:
                name = method.split("(", 1)[0].removeprefix("    func ")
                unchecked.append(name)

        self.assertEqual(
            unchecked, [], f"default model access without consent: {unchecked}"
        )


if __name__ == "__main__":
    unittest.main()
