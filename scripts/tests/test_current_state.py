from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/current-state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("current_state", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STATE = load_module()


class CurrentStateTests(unittest.TestCase):
    def test_checked_in_blocks_are_current(self) -> None:
        result = subprocess.run([SCRIPT, "render", "--check"], cwd=ROOT, text=True,
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_collect_writes_schema_and_live_corpus_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "observed.json"
            result = subprocess.run([SCRIPT, "collect", "--output", output], cwd=ROOT,
                                    text=True, capture_output=True, check=False)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertIsInstance(payload["corpus"]["callouts"]["total"], int)
        self.assertGreaterEqual(payload["corpus"]["callouts"]["total"], 0)
        self.assertEqual(
            payload["pendingEvent"]["value"], bool(payload["pendingEvent"]["reasons"])
        )
        self.assertEqual(
            payload["collection"]["complete"], not payload["collection"]["blockers"]
        )

    def test_collect_refuses_to_overwrite_the_tracked_manifest(self) -> None:
        before = (ROOT / "notes/current-state.json").read_bytes()
        result = subprocess.run(
            [SCRIPT, "collect", "--output", ROOT / "notes/current-state.json"], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output is tracked", result.stderr)
        self.assertEqual((ROOT / "notes/current-state.json").read_bytes(), before)

    def test_manifest_rejects_incomplete_probe_topology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            payload = json.loads((ROOT / "notes/current-state.json").read_text())
            del next(iter(payload["probeBaselines"].values()))["hostingMode"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run([SCRIPT, "--manifest", path, "render", "--check"],
                                    cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("complete topology", result.stderr)

    def test_manifest_rejects_inconsistent_verification_totals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            payload = json.loads((ROOT / "notes/current-state.json").read_text())
            payload["verification"]["snippetFences"] += 1
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run([SCRIPT, "--manifest", path, "render", "--check"],
                                    cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status counts", result.stderr)

    def test_manifest_rejects_non_object_and_impossible_dates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            path.write_text("[]\n", encoding="utf-8")
            result = subprocess.run([SCRIPT, "--manifest", path, "render", "--check"],
                                    cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("schema version 1", result.stderr)

            payload = json.loads((ROOT / "notes/current-state.json").read_text())
            payload["asOf"] = "2026-99-99"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run([SCRIPT, "--manifest", path, "render", "--check"],
                                    cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ISO date", result.stderr)

    def test_render_detects_stale_generated_block(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            old_targets = STATE.TARGETS
            try:
                STATE.TARGETS = {}
                for name in ("notes", "runbook", "next-beta", "probes"):
                    path = root / f"{name}.md"
                    path.write_text(
                        f"<!-- current-state:{name}:start -->\nstale\n"
                        f"<!-- current-state:{name}:end -->\n", encoding="utf-8"
                    )
                    STATE.TARGETS[name] = path
                self.assertEqual(STATE.render(manifest, write=False), 1)
                self.assertEqual(STATE.render(manifest, write=True), 0)
                self.assertEqual(STATE.render(manifest, write=False), 0)
            finally:
                STATE.TARGETS = old_targets

    def test_render_handles_no_installed_simulator_runtime(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        manifest["environment"]["installed"]["simulatorRuntimes"] = []
        blocks = STATE.render_blocks(manifest)
        self.assertIn("runtime is `unknown`", blocks["runbook"])

    def test_unavailable_host_commands_preserve_prior_values_and_report_blockers(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        previous = manifest["environment"]["installed"]
        old_run = STATE.run
        old_which = STATE.shutil.which
        try:
            STATE.run = lambda *args, **kwargs: ("", "simulated unavailable command")
            STATE.shutil.which = lambda name: None
            observed, blockers = STATE.installed_environment(previous)
        finally:
            STATE.run = old_run
            STATE.shutil.which = old_which
        self.assertEqual(observed, previous)
        self.assertTrue(blockers)
        self.assertTrue(all("simulated unavailable command" in item or "fm-path" in item
                            for item in blockers))

    def test_atomic_output_preserves_existing_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            path.write_text("old\n", encoding="utf-8")
            path.chmod(0o640)
            STATE.atomic_text(path, "new\n")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
