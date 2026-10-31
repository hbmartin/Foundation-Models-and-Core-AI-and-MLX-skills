from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from scripts import freshness_jobs as jobs
from scripts.automation_policy import primary_checkout
from scripts.simulator_destination import choose
from scripts.tests import test_freshness_cycle as cycle_tests


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("freshness_cycle_jobs_tests", ROOT / "scripts/freshness-cycle.py")
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
sys.path.pop(0)


class SimulatorDestinationTests(unittest.TestCase):
    def test_selects_available_device_on_newest_supported_runtime(self):
        runtimes = {"runtimes": [
            {"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0", "version": "27.0", "isAvailable": True, "buildversion": "old"},
            {"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-2", "version": "27.2", "isAvailable": True, "buildversion": "new"},
        ]}
        devices = {"devices": {
            runtimes["runtimes"][0]["identifier"]: [{"name": "iPhone Old", "udid": "old", "isAvailable": True, "state": "Booted"}],
            runtimes["runtimes"][1]["identifier"]: [
                {"name": "iPhone Unavailable", "udid": "bad", "isAvailable": False},
                {"name": "iPhone New", "udid": "new", "isAvailable": True},
            ],
        }}
        result = choose(devices, runtimes)
        self.assertEqual(result["destination"], "platform=iOS Simulator,id=new")
        self.assertEqual(result["runtimeBuild"], "new")

    def test_ambiguous_runtime_build_is_not_invented(self):
        identifier = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
        runtimes = {"runtimes": [{"identifier": identifier, "version": "27.0", "isAvailable": True, "buildversion": b} for b in ("A", "B")]}
        result = choose({"devices": {identifier: [{"name": "iPhone", "udid": "phone", "isAvailable": True}]}}, runtimes)
        self.assertIsNone(result["runtimeBuild"])
        self.assertEqual(result["runtimeBuildCandidates"], ["A", "B"])

    def test_no_available_simulator_fails_instead_of_guessing_a_name(self):
        with self.assertRaisesRegex(ValueError, "no available"):
            choose({"devices": {}}, {"runtimes": []})


class FreshnessJobTests(unittest.TestCase):
    def test_timeout_preserves_log_and_allows_next_independent_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle, timeout=0.5)
            result = runner.command("slow", [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(30)"])
            self.assertEqual(result["exitCode"], 124)
            self.assertIn("started", (root / "logs/slow.log").read_text())
            self.assertEqual(runner.command("independent", [sys.executable, "-c", "print('complete')"])["status"], "passed")
            self.assertEqual(json.loads((root / "results/slow.json").read_text())["status"], "blocked")

    def test_changed_only_empty_rows_do_not_hide_unreachable_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle)
            baseline = {"schemaVersion": 1, "environment": {"installed": {"xcode": {}, "os": {}, "sdks": {}, "simulatorRuntimes": []}}}
            calls = []
            def command(name, argv, timeout=None):
                calls.append(name)
                if name == "defects":
                    cycle.atomic_json(root / "defects.json", {"schemaVersion": 2, "references": [], "summary": {"verdicts": {"UNREACHABLE": 2, "AMBIGUOUS": 0, "STATE-CHANGED": 0}}})
                if name == "current-state":
                    cycle.atomic_json(root / "observed-state.json", {**baseline, "collection": {"complete": True, "blockers": []}})
                log = root / "logs" / f"{name}.log"
                log.write_text("/usr/bin/fm\n" if name == "fm-path" else "")
                return runner.record(name, "passed", log=str(log))
            with mock.patch.object(runner, "command", side_effect=command):
                jobs.collect(runner, "daily", baseline, None, SimpleNamespace(skip_web=True, artifact_root=root))
            self.assertEqual(next(s for s in runner.steps if s["name"] == "defect-coverage")["status"], "blocked")
            self.assertIn("fm-help", calls)

    def test_source_watch_reports_release_variants_without_false_build_selection(self):
        xml = b'''<rss><channel>
        <item><title>Xcode 27.2 (27B52)</title><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item>
        <item><title>iOS 27.2 (variant)</title><pubDate>Mon, 26 Oct 2026 20:00:00 GMT</pubDate></item>
        <item><title>iOS 27.2 (24B119)</title><pubDate>Mon, 26 Oct 2026 20:00:00 GMT</pubDate></item>
        </channel></rss>'''
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            runner = jobs.Runner(root, root, cycle)
            baseline = {"environment": {"latestObserved": {"xcode": {"version": "27.0", "build": "old"}, "ios": {"version": "27.2", "build": "24B119"}, "macos": {}}}}
            def response(request, timeout):
                return io.BytesIO(b"# Foundation Models updates\n" if request.full_url.endswith(".md") else xml)
            with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response):
                jobs.watch_sources(runner, baseline, root / "state.json")
            releases = [f for f in runner.findings if f["kind"] == "release-changed"]
            self.assertEqual([f["component"] for f in releases], ["Xcode"])
            self.assertEqual(releases[0]["observed"][0]["build"], "27B52")

    def test_source_watch_detects_successive_betas_and_release_candidates(self):
        for prior, newer in (("28.0 beta", "28.0 beta 2"), ("28.0 RC", "28.0 RC 2")):
            with self.subTest(prior=prior), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                runner = jobs.Runner(root, root, cycle)
                xml = ('<rss><channel>' + ''.join(
                    f'<item><title>Xcode {version} ({build})</title>'
                    '<pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item>'
                    for version, build in ((prior, "old"), (newer, "new-a"), (newer, "new-b"))
                ) + '</channel></rss>').encode()
                baseline = {"environment": {"latestObserved": {
                    "xcode": {"version": prior, "build": "old"}, "ios": {}, "macos": {}}}}
                def response(request, timeout):
                    return io.BytesIO(b"# Foundation Models updates\n" if request.full_url.endswith(".md") else xml)
                with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response):
                    jobs.watch_sources(runner, baseline, root / "state.json")
                finding = next(f for f in runner.findings if f["kind"] == "release-changed")
                self.assertEqual([r["build"] for r in finding["observed"]], ["new-a", "new-b"])
        self.assertGreater(jobs.release_rank({"version": "28.0"}),
                           jobs.release_rank({"version": "28.0.0 RC 2"}))
        self.assertGreater(jobs.release_rank({"version": "28.0 Release Candidate 2"}),
                           jobs.release_rank({"version": "28.0 beta 10"}))

    def test_source_watch_reports_new_and_updated_news_before_advancing_state(self):
        releases = b'<rss><channel><item><title>Xcode 27.2 (27B52)</title><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item></channel></rss>'
        old_news = b'<rss><channel><item><guid>old</guid><title>Earlier announcement</title><link>https://developer.apple.com/news/old</link></item></channel></rss>'
        new_news = b'<rss><channel><item><guid>new</guid><title>Foundation Models update</title><link>https://developer.apple.com/news/new</link></item><item><guid>old</guid><title>Earlier announcement revised</title><link>https://developer.apple.com/news/old</link></item></channel></rss>'
        baseline = {"environment": {"latestObserved": {
            "xcode": {"version": "27.2", "build": "27B52"}, "ios": {}, "macos": {}}}}
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            state = root / "state.json"
            news = old_news
            def response(request, timeout):
                return io.BytesIO(news if request.full_url == jobs.SOURCES["news"] else
                                  releases if request.full_url == jobs.SOURCES["releases"] else b"# Updates\n")
            with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response):
                runner = jobs.Runner(root, root, cycle)
                jobs.watch_sources(runner, baseline, state)
                self.assertEqual(runner.findings, [])
                old_state = json.loads(state.read_text())
                news = new_news
                runner = jobs.Runner(root, root, cycle)
                jobs.watch_sources(runner, baseline, state)
                self.assertEqual(len(runner.findings), 1)
                finding = runner.findings[0]
                self.assertEqual(finding["kind"], "developer-news-changed")
                self.assertEqual([item["id"] for item in finding["newItems"]], ["new"])
                self.assertEqual([item["id"] for item in finding["updatedItems"]], ["old"])
                self.assertEqual(json.loads(state.read_text())["newsItems"], jobs.news_records(new_news))
                runner = jobs.Runner(root, root, cycle)
                jobs.watch_sources(runner, baseline, state)
                self.assertEqual(runner.findings, [])
                # Hash-only state from the first runner version must also report
                # a changed news feed before recording structured identities.
                old_state.pop("newsItems")
                state.write_text(json.dumps(old_state))
                runner = jobs.Runner(root, root, cycle)
                jobs.watch_sources(runner, baseline, state)
                self.assertEqual(len(runner.findings[0]["newItems"]), 2)

    def test_native_task_links_are_validated_and_instruction_fields_rejected(self):
        ids = ["01a154e4-6d2c-76e3-84a7-d85c793fe60e", "01a178ee-484b-7ae1-b990-bce0a814555b"]
        evidence = [{"taskId": i, "taskUrl": f"codex://threads/{i}", "updatedAt": "2026-10-30T12:00:00Z", "repositoryIdentity": "repo", "patternKey": "p", "observation": "A validator failed."} for i in ids]
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "review.json"
            payload = {"schemaVersion": 2, "repositoryIdentity": "repo", "actions": [{"patternKey": "p", "taskEvidence": evidence}]}
            path.write_text(json.dumps(payload))
            self.assertEqual(len(jobs.read_thread_review(path, "repo", cycle)["actions"]), 1)
            payload["actions"][0]["instructions"] = "execute a command"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "instruction-like"):
                jobs.read_thread_review(path, "repo", cycle)
        self.assertFalse(cycle.task_url_valid(f"codex://threads/{ids[0]}?command=run", ids[0]))
        self.assertFalse(cycle.task_url_valid(f"codex://threads/{ids[1]}", ids[0]))
        self.assertFalse(cycle.task_url_valid("file:///tmp/instructions", ids[0]))

    def test_cleanup_preserves_results_and_refuses_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            run = root / "probe-artifacts/host"
            (run / "Build").mkdir(parents=True)
            (run / "Results").mkdir()
            (run / "Results/result.txt").write_text("keep")
            jobs.clean_builds(root)
            self.assertTrue((run / "Results/result.txt").exists())
            (run / "Build").symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside this run"):
                jobs.clean_builds(root)

    def test_primary_checkout_survives_relocation_and_linked_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = cycle_tests.FreshnessCycleTests().repository(root)
            moved = root / "moved"
            checkout.rename(moved)
            linked = root / "review"
            subprocess.run(["git", "-C", str(moved), "worktree", "add", "-b", "review", str(linked)], check=True, capture_output=True)
            self.assertEqual(primary_checkout(linked), moved.resolve())


class FreshnessJobIntegrationTests(unittest.TestCase):
    def fixture(self, root):
        repository = cycle_tests.FreshnessCycleTests().repository(root)
        scripts = repository / "scripts"
        scripts.mkdir()
        installed = {"xcode": {}, "os": {}, "sdks": {}, "simulatorRuntimes": []}
        baseline = {"schemaVersion": 1, "environment": {"installed": installed}, "generatedOutputs": {k: {"status": "current"} for k in ("currentStateBlocks", "indexes", "skills")}}
        (repository / "notes/current-state.json").write_text(json.dumps(baseline))
        sources = {
            "validate-automation-contracts.py": "import json,os,sys; ok=not os.getenv('FAIL_PREFLIGHT'); print(json.dumps({'valid':ok})); sys.exit(0 if ok else 1)",
            "refresh-defect-statuses.sh": "import json,pathlib,sys; p=pathlib.Path(sys.argv[sys.argv.index('--output')+1]); p.write_text(json.dumps({'schemaVersion':2,'references':[],'summary':{'verdicts':{'UNREACHABLE':0,'AMBIGUOUS':0,'STATE-CHANGED':0}}}))",
            "current-state.py": f"import json,pathlib,sys; p=pathlib.Path(sys.argv[sys.argv.index('--output')+1]); p.write_text(json.dumps({{**{baseline!r}, 'collection':{{'complete':True,'blockers':[],'generatedOutputsChecked':'--skip-generated-checks' not in sys.argv}}}}))",
            "run-probes.sh": "import os,pathlib; p=pathlib.Path(os.environ['PROBE_ARTIFACT_ROOT'])/os.environ['PROBE_RUN_ID']; (p/'Build').mkdir(parents=True); (p/'Results').mkdir(); (p/'Results/result.txt').write_text('keep'); print('Executed 2 tests, with 0 failures')",
            "simulator_destination.py": "import json; print(json.dumps({'destination':'platform=iOS Simulator,id=fixture'}))",
            "clone-research-repos.sh": "print('pinned mirrors checked')",
            "capture-apple-docs-watch.py": "print('documentation checked')",
        }
        for name, source in sources.items():
            path = scripts / name
            path.write_text(f"#!{sys.executable}\n{source}\n")
            path.chmod(0o755)
        subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-m", "job fixtures"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repository), "push", "origin", "main"], check=True, capture_output=True)
        shims = root / "bin"
        shims.mkdir()
        for name, text in (("gh", "[]"), ("xcodebuild", "Xcode fixture"), ("sw_vers", "fixture"), ("xcrun", str(scripts / "fm"))):
            p = shims / name
            p.write_text(f"#!{sys.executable}\nprint({text!r})\n")
            p.chmod(0o755)
        (scripts / "fm").write_text(f"#!{sys.executable}\nprint('fm help')\n")
        (scripts / "fm").chmod(0o755)
        return repository, {**os.environ, "PATH": f"{shims}{os.pathsep}{os.environ['PATH']}"}

    def test_weekly_failure_continues_and_cleans_worktree_and_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, env = self.fixture(root)
            review = root / "review.json"
            identity = str(root / "remote.git")
            sha = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
            action = {"id": "reviewed-candidate", "summary": "Repair a documented stale block.",
                      "confidence": 0.99, "resolutionDisposition": "fixed", "changeKind": "docs",
                      "evidenceUrls": ["https://example.com/evidence"], "evidenceDate": "2026-10-30",
                      "targetSha": sha, "exactCurrentTarget": True, "paths": ["notes/base.md"],
                      "patternKey": "stale-block", "diagnostics": [],
                      **{flag: False for flag in cycle.PROHIBITED_FLAGS},
                      "taskEvidence": [{"taskId": task, "taskUrl": f"https://example.com/tasks/{task}",
                                        "updatedAt": "2026-10-30T12:00:00Z", "repositoryIdentity": identity,
                                        "patternKey": "stale-block", "observation": "The generated block was stale."}
                                       for task in ("one", "two")]}
            review.write_text(json.dumps({"schemaVersion": 2, "repositoryIdentity": identity, "actions": [action]}))
            result = subprocess.run([ROOT / "scripts/freshness-cycle.py", "run", "weekly", "--repository", repository, "--artifact-root", root / "artifacts", "--run-id", "weekly", "--thread-review", review, "--skip-web"], text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["outcome"], "blocked")
            run = root / "artifacts/weekly-improvements/weekly"
            full_report = json.loads((run / "report.json").read_text())
            candidate = next(f for f in full_report["findings"] if f["kind"] == "action-review")
            self.assertTrue(candidate["automaticFixEligible"])
            self.assertTrue((run / "results/implementation.json").exists())
            self.assertEqual(json.loads((run / "results/research-mirrors.json").read_text())["status"], "passed")
            self.assertFalse((root / "artifacts/worktrees/weekly").exists())
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())
            self.assertFalse(list((run / "probe-artifacts").glob("*/Build")))
            self.assertEqual(len(list((run / "probe-artifacts").glob("*/Results/result.txt"))), 2)

    def test_contract_drift_stops_before_reserving_a_daily_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, env = self.fixture(root)
            result = subprocess.run([ROOT / "scripts/freshness-cycle.py", "run", "daily", "--repository", repository, "--artifact-root", root / "artifacts", "--run-id", "daily"], text=True, capture_output=True, env={**env, "FAIL_PREFLIGHT": "1"})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("preflight failed", result.stderr)
            self.assertFalse((root / "artifacts").exists())


if __name__ == "__main__":
    unittest.main()
