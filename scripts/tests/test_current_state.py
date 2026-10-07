from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


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
    def test_stable_release_records_reject_beta_and_duplicate_components(self):
        manifest = STATE.load_manifest(STATE.DEFAULT_MANIFEST)
        for kind in ('beta', 'duplicate'):
            candidate = json.loads(json.dumps(manifest))
            if kind == 'beta':
                candidate['stableReleases'][0]['version'] = '27.2 beta 3'
            else:
                candidate['stableReleases'].append(candidate['stableReleases'][0])
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / 'state.json'
                path.write_text(json.dumps(candidate))
                with self.subTest(kind=kind), self.assertRaises(SystemExit):
                    STATE.load_manifest(path)

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

    def test_manifest_rejects_non_string_installed_xcode_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            payload = json.loads((ROOT / "notes/current-state.json").read_text())
            payload["environment"]["installed"]["xcode"]["build"] = 12345
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [SCRIPT, "--manifest", path, "render", "--check"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("installed xcode metadata is invalid", result.stderr)

    def test_manifest_rejects_a_full_run_after_the_snapshot_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            payload = json.loads((ROOT / "notes/current-state.json").read_text())
            payload["verification"]["lastFullRun"] = "2099-01-01"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [SCRIPT, "--manifest", path, "render", "--check"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lastFullRun cannot be later than asOf", result.stderr)

    def test_render_detects_stale_generated_block(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            old_targets = STATE.TARGETS
            try:
                STATE.TARGETS = {}
                for name in old_targets:
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

    def test_failed_selection_retains_prior_evidence_without_using_it(self):
        previous = STATE.load_manifest(ROOT / "notes/current-state.json")["environment"]["installed"]
        def fail(*command, **kwargs):
            return "", "unavailable"
        with mock.patch.object(STATE, "run", side_effect=fail) as command, mock.patch.dict(os.environ, {"DEVELOPER_DIR": ""}):
            observed, blockers = STATE.installed_environment(previous)
        self.assertEqual(observed["xcode"], previous["xcode"])
        self.assertTrue(blockers)
        self.assertFalse(any(c.args[0] in ("xcodebuild", "xcrun") for c in command.call_args_list))

    def test_collector_selects_environment_then_system_not_manifest(self):
        previous = STATE.load_manifest(ROOT / "notes/current-state.json")["environment"]["installed"]
        def commands(*args, **kwargs):
            if args == ("xcode-select", "-p"):
                return "/selected", None
            return "", "unavailable in fixture"
        with mock.patch.object(STATE, "run", side_effect=commands), mock.patch.dict(os.environ, {"DEVELOPER_DIR": ""}):
            observed, _ = STATE.installed_environment(previous)
            self.assertEqual(observed["xcode"]["path"], "/selected")
        with mock.patch.object(STATE, "run", side_effect=commands), mock.patch.dict(os.environ, {"DEVELOPER_DIR": "/explicit"}):
            observed, _ = STATE.installed_environment(previous)
            self.assertEqual(observed["xcode"]["path"], "/explicit")

    def test_simulator_comparison_requires_simulator_release_evidence(self):
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        installed = manifest["environment"]["installed"]
        latest = manifest["environment"]["latestObserved"]
        latest["simulatorRuntimes"] = []
        self.assertFalse(any("Simulator" in x for x in STATE.pending_reasons(installed, latest)))
        latest["simulatorRuntimes"] = [{"name": "iOS", "build": "different-runtime-build"}]
        self.assertTrue(any("Simulator" in x for x in STATE.pending_reasons(installed, latest)))

    def test_unavailable_host_commands_preserve_prior_values_and_report_blockers(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        previous = manifest["environment"]["installed"]
        old_run = STATE.run
        old_which = STATE.shutil.which
        try:
            STATE.run = lambda *args, **kwargs: ("", "simulated unavailable command")
            STATE.shutil.which = lambda name: None
            with mock.patch.dict(STATE.os.environ, {"DEVELOPER_DIR": ""}):
                observed, blockers = STATE.installed_environment(previous)
        finally:
            STATE.run = old_run
            STATE.shutil.which = old_which
        self.assertEqual(observed, previous)
        self.assertTrue(blockers)
        self.assertTrue(all("simulated unavailable command" in item or "fm-path" in item
                            for item in blockers))

    def test_installed_environment_does_not_probe_unsupported_fm_version_flag(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        previous = manifest["environment"]["installed"]
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(args)
            return "", "simulated unavailable command"

        with (
            mock.patch.object(STATE, "run", side_effect=fake_run),
            mock.patch.object(STATE.shutil, "which", return_value="/usr/bin/fm"),
            mock.patch.dict(STATE.os.environ, {"DEVELOPER_DIR": ""}),
        ):
            observed, blockers = STATE.installed_environment(previous)
        self.assertNotIn(("/usr/bin/fm", "--version"), calls)
        self.assertEqual(observed["fm"]["path"], "/usr/bin/fm")
        self.assertFalse(any(item.startswith("fm-version:") for item in blockers))

    def test_unparseable_simulator_output_preserves_prior_values_and_reports_blocker(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        previous = manifest["environment"]["installed"]
        old_run = STATE.run
        old_which = STATE.shutil.which
        try:
            def fake_run(*args, **kwargs):
                if args == ("xcode-select", "-p"):
                    return "/selected/Developer", None
                if args[:4] == ("xcrun", "simctl", "list", "runtimes"):
                    return "== Runtimes ==\nunrecognized runtime format", None
                return "", "simulated unavailable command"

            STATE.run = fake_run
            STATE.shutil.which = lambda name: None
            observed, blockers = STATE.installed_environment(previous)
        finally:
            STATE.run = old_run
            STATE.shutil.which = old_which
        self.assertEqual(observed["simulatorRuntimes"], previous["simulatorRuntimes"])
        self.assertIn(
            "simulator-runtimes: output contained no recognized iOS runtimes",
            blockers,
        )

    def test_generated_output_checks_rederive_status_and_date(self) -> None:
        outcomes = iter((("", None), ("", "stale index"), ("", None)))
        old_run = STATE.run
        try:
            STATE.run = lambda *args, **kwargs: next(outcomes)
            outputs, blockers = STATE.generated_output_state()
        finally:
            STATE.run = old_run
        today = STATE.dt.datetime.now(STATE.dt.timezone.utc).date().isoformat()
        self.assertEqual(outputs["currentStateBlocks"]["status"], "current")
        self.assertEqual(outputs["indexes"]["status"], "stale")
        self.assertEqual(outputs["skills"]["status"], "current")
        self.assertTrue(all(item["checkedAt"] == today for item in outputs.values()))
        self.assertEqual(blockers, ["generated-output-indexes: stale index"])

    def test_collect_uses_fresh_generated_output_results(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        derived = json.loads(json.dumps(manifest["generatedOutputs"]))
        derived["indexes"]["status"] = "stale"
        old_corpus = STATE.corpus_state
        old_environment = STATE.installed_environment
        old_snippets = STATE.snippet_state
        old_generated = STATE.generated_output_state
        try:
            STATE.corpus_state = lambda: manifest["corpus"]
            STATE.installed_environment = lambda previous: (previous, [])
            STATE.snippet_state = lambda previous: previous
            STATE.generated_output_state = lambda: (
                derived, ["generated-output-indexes: stale index"]
            )
            collected = STATE.collect(manifest)
        finally:
            STATE.corpus_state = old_corpus
            STATE.installed_environment = old_environment
            STATE.snippet_state = old_snippets
            STATE.generated_output_state = old_generated
        self.assertEqual(collected["generatedOutputs"], derived)
        self.assertIn("generated-output-indexes: stale index", collected["collection"]["blockers"])

    def test_snippet_collection_preserves_last_attested_full_run(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        previous = json.loads(json.dumps(manifest["verification"]))
        previous["lastFullRun"] = "2001-02-03"

        observed = STATE.snippet_state(previous)

        self.assertEqual("2001-02-03", observed["lastFullRun"])

    def test_pending_reason_does_not_claim_a_newer_installed_build_trails(self) -> None:
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        installed = json.loads(json.dumps(manifest["environment"]["installed"]))
        latest = manifest["environment"]["latestObserved"]
        installed["xcode"]["build"] = "99Z999"
        reasons = STATE.pending_reasons(installed, latest)
        xcode_reason = next(reason for reason in reasons if "Xcode" in reason)
        self.assertIn("differs from observed build", xcode_reason)
        self.assertNotIn("trails", xcode_reason)

    def test_daily_collection_skips_checks_without_redating_prior_results(self):
        manifest = STATE.load_manifest(ROOT / "notes/current-state.json")
        with mock.patch.object(STATE, "installed_environment", return_value=(manifest["environment"]["installed"], [])), mock.patch.object(STATE, "generated_output_state") as checks:
            observed = STATE.collect(manifest, skip_generated_checks=True)
        checks.assert_not_called()
        self.assertEqual(manifest["generatedOutputs"], observed["generatedOutputs"])
        self.assertFalse(observed["collection"]["generatedOutputsChecked"])
        self.assertTrue(observed["collection"]["complete"])

    def test_atomic_output_preserves_existing_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "state.json"
            path.write_text("old\n", encoding="utf-8")
            path.chmod(0o640)
            STATE.atomic_text(path, "new\n")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
