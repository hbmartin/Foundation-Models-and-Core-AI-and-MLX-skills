"""Regression checks for resource recovery and reviewed source monitoring."""
import contextlib
import io
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from scripts.tests import test_freshness_jobs as fixtures
from scripts import probe_evidence

jobs, cycle = fixtures.jobs, fixtures.cycle


class LifecycleRepairs(unittest.TestCase):
    def exercise(self, fault):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, env = fixtures.FreshnessJobIntegrationTests().fixture(root)
            args = SimpleNamespace(repository=repository, artifact_root=root / "artifacts", installed_root=None,
                                   command_timeout=30, run_id="repair", thread_review=None, cycle="weekly",
                                   ref=None, keep_worktree=False, watch_consumer=None)
            real_read, real_write, real_finalize = cycle.read_json, cycle.atomic_json, cycle.finalize
            injected = False
            def read(path, *rest):
                if fault in ("manifest", "baseline", "actions") and not injected_flags[0]:
                    match = ((fault == "manifest" and str(path).endswith("repair/run.json"))
                             or (fault == "baseline" and "/worktrees/" in str(path) and str(path).endswith("current-state.json"))
                             or (fault == "actions" and str(path).endswith("actions.json")))
                    if match:
                        injected_flags[0] = True
                        raise OSError("injected read failure")
                return real_read(path, *rest)
            def write(path, payload):
                nonlocal injected
                if not injected and ((fault == "preflight" and path.name == "preflight.json")
                                     or (fault == "authority" and path.name == "weekly-improvement.json")):
                    injected = True
                    raise OSError("injected write failure")
                return real_write(path, payload)
            def finalize(options):
                if fault == "refusal" and options.outcome != "blocked":
                    raise cycle.CycleError("injected policy refusal")
                return real_finalize(options)
            def collect(runner, *rest):
                real_write(runner.root / "actions.json", {"summary": {"eligible": 0}})
                if fault == "findings":
                    runner.findings.append({"kind": "documentation-changed"})
                if fault == "interrupt":
                    raise KeyboardInterrupt("injected termination")
            injected_flags = [False]
            with mock.patch.dict(os.environ, env), mock.patch.object(cycle, "open_automation_pr", return_value=None), \
                 mock.patch.object(cycle, "read_json", side_effect=read), mock.patch.object(cycle, "atomic_json", side_effect=write), \
                 mock.patch.object(cycle, "finalize", side_effect=finalize), mock.patch.object(jobs, "collect", side_effect=collect), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = jobs.execute(args, cycle)
            self.assertFalse((root / "artifacts/worktrees/repair").exists())
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())
            state = real_read(root / "artifacts/state/weekly-improvement.json")
            self.assertNotIn("lastSuccessfulRun", state)
            self.assertTrue((root / "artifacts/weekly-improvements/repair/report.json").exists())
            return code, state

    def test_post_prepare_failures_always_clean(self):
        for fault in ("manifest", "baseline", "actions", "preflight", "authority", "refusal"):
            with self.subTest(fault=fault):
                code, state = self.exercise(fault)
                self.assertEqual(code, 1)
                self.assertEqual(state["lastRun"]["outcome"], "blocked")

    def test_interruption_cleans_and_preserves_exit_status(self):
        self.assertEqual(self.exercise("interrupt")[0], 130)

    def test_findings_are_collected_pending_and_not_success(self):
        code, state = self.exercise("findings")
        self.assertEqual(code, 0)
        self.assertEqual(state["lastCollectedRun"]["outcome"], "findings")
        self.assertEqual(state["pending"]["outcome"], "findings")

    def test_offline_preparation_does_not_fetch_or_query_github(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
            real_git = cycle.git
            calls = []
            def git(repository, *args, **kwargs):
                calls.append(args)
                return real_git(repository, *args, **kwargs)
            with mock.patch.object(cycle, "git", side_effect=git), mock.patch.object(cycle, "open_automation_pr") as query:
                manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts", worktree_root=None,
                    run_id="offline", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
                query.assert_not_called()
                self.assertFalse(any(args[0] == "fetch" for args in calls))
                self.assertTrue(manifest["remoteChecksSkipped"])
                with contextlib.redirect_stdout(io.StringIO()):
                    cycle.finalize(SimpleNamespace(run_root=root / "artifacts/weekly-improvements/offline", outcome="blocked", pr_url=None, state_path=None, manifest=manifest))

    def test_prepare_interrupt_after_worktree_creation_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
            real_write = cycle.atomic_json
            def write(path, payload):
                if path.name == "run.json" and payload.get("status") == "prepared":
                    raise KeyboardInterrupt("SIGTERM")
                return real_write(path, payload)
            with mock.patch.object(cycle, "atomic_json", side_effect=write), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts",
                        worktree_root=None, run_id="prepare", skip_remote_check=True, ref=None))
            self.assertFalse((root / "artifacts/worktrees/prepare").exists())
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())


class CollectionRepairs(unittest.TestCase):
    def test_stdout_is_not_contaminated_by_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            result = jobs.Runner(root, root, cycle).command("path", [sys.executable, "-c",
                "import sys; print('/usr/bin/fm'); print('xcrun warning', file=sys.stderr)"])
            self.assertEqual(pathlib.Path(result["stdout"]).read_text().strip(), "/usr/bin/fm")
            self.assertIn("xcrun warning", pathlib.Path(result["log"]).read_text())

    def test_malformed_lane_does_not_stop_later_lanes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle)
            def malformed(*args):
                jobs.validate_observation({"schemaVersion": 1, "collection": None})
            with mock.patch.object(jobs, "collect_defects", side_effect=malformed), \
                 mock.patch.object(jobs, "collect_observation") as later, \
                 mock.patch.object(jobs, "collect_tools"), mock.patch.object(jobs, "collect_sources"):
                jobs.collect(runner, "daily", {}, None, None)
            later.assert_called_once()
            self.assertEqual(runner.steps[0]["status"], "blocked")

    def test_offline_auxiliary_lanes_never_launch_network_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle)
            with mock.patch.object(runner, "command") as command:
                jobs.collect_auxiliary(runner, "weekly", {}, None, SimpleNamespace(skip_web=True))
                jobs.collect_defects(runner, "weekly", {}, None, SimpleNamespace(skip_web=True))
            command.assert_not_called()
            self.assertEqual(len(runner.steps), 3)

    def test_complete_documentation_disagreement_is_a_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle)
            captured_commands = []
            def command(name, argv, **options):
                captured_commands.append(argv)
                if name == "apple-docs-watch":
                    captures = []
                    (root / "apple-docs").mkdir()
                    for n, m in (("overview", "resolve"), ("member", "resolved")):
                        payload = f"func {m}(in:)".encode()
                        (root / "apple-docs" / f"{n}.md").write_bytes(payload)
                        captures.append({"name": n, "status": "captured", "path": f"{n}.md",
                                         "sha256": hashlib.sha256(payload).hexdigest(), "methodSpellings": [m]})
                    cycle.atomic_json(root / "apple-docs/manifest.json", {"schemaVersion": 1, "pagesAgree": False, "captures": captures})
                return runner.record(name, "blocked" if name == "apple-docs-watch" else "passed", exitCode=1 if name == "apple-docs-watch" else 0)
            with mock.patch.object(runner, "command", side_effect=command):
                jobs.collect_auxiliary(runner, "weekly", {}, None, SimpleNamespace(skip_web=False, artifact_root=root))
            self.assertEqual(runner.findings[0]["kind"], "documentation-disagreement")
            self.assertFalse(any(s["status"] == "blocked" for s in runner.steps))
            self.assertIn(f"RESEARCH_REPOS_ROOT={root / 'cache/research-mirrors'}", captured_commands[0])

    def test_probe_parser_retains_detail_and_requires_skip_coverage(self):
        log = "PROBE-RESULT name=example value=ok detail=important\n-[Example test] : Test skipped - SKIPPED: intentional\nExecuted 2 tests, with 1 test skipped and 0 failures\n"
        result = probe_evidence.parse_log(log)
        self.assertEqual(result["results"][0]["detail"], "important")
        self.assertEqual(len(result["skipReasons"]), 1)
        with self.assertRaises(ValueError):
            probe_evidence.parse_log(log.replace("1 test skipped", "2 tests skipped"))

    def test_pinned_simulator_does_not_choose_future_runtime(self):
        runtimes = {"runtimes": [{"identifier": f"com.apple.CoreSimulator.SimRuntime.iOS-{v}-0", "version": f"{v}.0", "buildversion": str(v), "isAvailable": True} for v in (27, 28)]}
        devices = {"devices": {r["identifier"]: [{"name": "iPhone Test", "udid": r["version"], "isAvailable": True}] for r in runtimes["runtimes"]}}
        pinned = {"osVersion": "27.0", "osBuild": "27", "device": "iPhone Test"}
        self.assertEqual(fixtures.choose(devices, runtimes, pinned=pinned)["runtimeBuild"], "27")
        pinned["osBuild"] = "missing"
        with self.assertRaises(ValueError):
            fixtures.choose(devices, runtimes, pinned=pinned)


class SourceWatchRepairs(unittest.TestCase):
    def capture(self, root, state, docs="# Initial\n", versions=(("27.2", "27B52"),), reviewed_builds=None):
        runner = jobs.Runner(root, root, cycle)
        feed = ('<rss><channel>' + ''.join(f'<item><title>Xcode {v} ({b})</title><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item>' for v, b in versions) + '</channel></rss>').encode()
        def response(request, timeout):
            return io.BytesIO(docs.encode() if request.full_url.endswith(".md") else feed)
        baseline = {"environment": {"latestObserved": {"xcode": {"version": "27.2", "build": "27B52"}}}}
        if reviewed_builds is not None:
            baseline["environment"]["latestObserved"]["xcode"]["reviewedBuilds"] = reviewed_builds
        with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response):
            jobs.watch_sources(runner, baseline, state)
        jobs.write_report(runner, "daily", "findings", emit=False)
        return runner

    def test_pending_survives_runs_and_stale_acknowledgment_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory);state = root / "state/weekly.json"
            self.capture(root / "one", state)
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "one"), cycle)
            changed = self.capture(root / "two", state, "# Changed\n")
            repeated = self.capture(root / "three", state, "# Changed\n")
            self.assertEqual(changed.findings, repeated.findings)
            self.capture(root / "four", state, "# Newer\n")
            with self.assertRaisesRegex(cycle.CycleError, "stale"):
                jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "two"), cycle)
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "four"), cycle)
            self.assertEqual(self.capture(root / "five", state, "# Newer\n").findings, [])

    def test_consumers_and_legacy_seed_are_not_implicitly_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name in ("daily", "weekly"):
                self.capture(root / name, root / "state" / f"{name}.json")
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "daily"), cycle)
            self.assertTrue(cycle.read_json(root / "state/weekly.json")["pending"])
            legacy = root / "legacy.json";cycle.atomic_json(legacy, {"foundationmodels": "old"})
            migrated = jobs.source_watch.load(legacy, cycle)
            self.assertEqual(migrated["reviewed"], {})
            self.assertEqual(migrated["legacySeed"]["foundationmodels"], "old")

    def test_slower_older_capture_cannot_overwrite_newer_committed_state(self):
        old = {"name": "foundationmodels", "url": "https://example.com", "sha256": "old", "capturedAt": "2026-11-01T10:00:00Z"}
        new = {**old, "sha256": "new", "capturedAt": "2026-11-01T10:00:01Z"}
        state = {"schemaVersion": 2, "reviewed": {}, "latestObserved": {}, "pending": {}}
        state = jobs.source_watch.observe(state, {"foundationmodels": new})
        state = jobs.source_watch.observe(state, {"foundationmodels": old})
        self.assertEqual(state["latestObserved"]["foundationmodels"]["sha256"], "new")
        self.assertEqual(state["pending"]["foundationmodels"]["sha256"], "new")

    def test_version_alias_is_not_a_release_and_retained_old_build_does_not_hide_respin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            alias = self.capture(root / "alias", root / "state1.json", versions=(("27.2.0", "27B52"),))
            self.assertFalse(any(f["kind"].startswith("release-") for f in alias.findings))
            respin = self.capture(root / "respin", root / "state2.json", versions=(("27.2", "27B52"), ("27.2", "new")))
            self.assertTrue(any(f["kind"] == "release-build-set-changed" for f in respin.findings))
            reviewed = self.capture(root / "reviewed", root / "state3.json", versions=(("27.2", "27B52"), ("27.2", "new")), reviewed_builds=["27B52", "new"])
            self.assertFalse(any(f["kind"].startswith("release-") for f in reviewed.findings))
