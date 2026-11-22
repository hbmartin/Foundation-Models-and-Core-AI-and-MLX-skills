"""Regression checks for resource recovery and reviewed source monitoring."""
import contextlib
import io
import hashlib
import json
import os
import pathlib
import signal
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
            real_report = jobs.write_report
            real_acquire = cycle.acquire_lock
            real_unlink = pathlib.Path.unlink
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
                if fault == "prepare-sigterm" and path.name == "run.json" and payload.get("status") == "prepared":
                    os.kill(os.getpid(), signal.SIGTERM)
                if not injected and ((fault == "preflight" and path.name == "preflight.json")
                                     or (fault == "authority" and path.name == "weekly-improvement.json")
                                     or (fault == "terminal-manifest" and path.name == "run.json" and payload.get("status") == "no-change")
                                     or (fault == "terminal-authority" and path.name == "weekly-improvement.json" and payload.get("pending") is None)):
                    injected = True
                    raise OSError("injected write failure")
                return real_write(path, payload)
            def finalize(options):
                if fault == "refusal" and options.outcome != "blocked":
                    raise cycle.CycleError("injected policy refusal")
                return real_finalize(options)
            def report(*arguments, **options):
                nonlocal injected
                if fault == "report-always" or fault == "report-once" and not injected:
                    injected = True
                    raise OSError("injected report failure")
                return real_report(*arguments, **options)
            def collect(runner, *rest):
                real_write(runner.root / "actions.json", {"summary": {"eligible": 0}})
                if fault == "findings":
                    runner.findings.append({"kind": "documentation-changed"})
                if fault == "interrupt":
                    raise KeyboardInterrupt("injected termination")
                if fault == "sigterm":
                    os.kill(os.getpid(), signal.SIGTERM)
            def acquire(*arguments):
                value = real_acquire(*arguments)
                if fault == "lock":
                    raise OSError("injected failure after lock acquisition")
                return value
            def unlink(path, *arguments, **options):
                nonlocal injected
                if fault == "lock-release" and path.name == "weekly-improvement.lock.json" and not injected:
                    injected = True
                    raise OSError("injected lock release failure")
                return real_unlink(path, *arguments, **options)
            injected_flags = [False]
            output = io.StringIO()
            with mock.patch.dict(os.environ, env), mock.patch.object(cycle, "open_automation_pr", return_value=None), \
                 mock.patch.object(cycle, "read_json", side_effect=read), mock.patch.object(cycle, "atomic_json", side_effect=write), \
                 mock.patch.object(cycle, "finalize", side_effect=finalize), mock.patch.object(jobs, "collect", side_effect=collect), \
                 mock.patch.object(jobs, "write_report", side_effect=report), \
                 mock.patch.object(cycle, "acquire_lock", side_effect=acquire), \
                 mock.patch.object(pathlib.Path, "unlink", unlink), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = jobs.run(args, cycle)
                except OSError:
                    if fault != "lock":
                        raise
                    code = 1
                except KeyboardInterrupt:
                    if fault != "prepare-sigterm":
                        raise
                    code = 130
            self.assertFalse((root / "artifacts/worktrees/repair").exists())
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())
            state = real_read(root / "artifacts/state/weekly-improvement.json")
            self.assertEqual(len(state["runs"]), 1)
            self.assertNotIn("conflicting finalization request", json.dumps(state))
            if (root / "artifacts/weekly-improvements/repair/report.json").exists():
                self.assertNotIn("conflicting finalization request", (root / "artifacts/weekly-improvements/repair/report.json").read_text())
            self.assertNotIn("lastSuccessfulRun", state)
            self.assertTrue((root / "artifacts/weekly-improvements/repair/run.json").exists())
            if fault not in ("lock", "prepare-sigterm", "report-always"):
                self.assertTrue((root / "artifacts/weekly-improvements/repair/report.json").exists())
            if fault.startswith("report-"):
                result = json.loads(output.getvalue())
                self.assertEqual(result["outcome"], "blocked")
                self.assertIn("runRoot", result)
                if fault == "report-always":
                    self.assertIn("reportError", result)
            return code, state

    def test_post_prepare_failures_always_clean(self):
        for fault in ("lock", "manifest", "baseline", "actions", "preflight", "authority", "refusal", "lock-release", "terminal-manifest", "terminal-authority"):
            with self.subTest(fault=fault):
                code, state = self.exercise(fault)
                self.assertEqual(code, 1)
                self.assertEqual(state["lastRun"]["outcome"], "blocked")

    def test_interruption_cleans_and_preserves_exit_status(self):
        self.assertEqual(self.exercise("interrupt")[0], 130)

    def test_report_failures_still_emit_result_and_clean(self):
        for fault in ("report-once", "report-always"):
            with self.subTest(fault=fault):
                self.assertEqual(self.exercise(fault)[0], 1)

    def test_sigterm_uses_run_handler_cleans_and_restores_previous_handler(self):
        before = signal.getsignal(signal.SIGTERM)
        self.assertEqual(self.exercise("sigterm")[0], 130)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)
        self.assertEqual(self.exercise("prepare-sigterm")[0], 130)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_finalization_refuses_foreign_lock_and_worktree_ownership(self):
        for foreign_lock in (False, True):
            with self.subTest(foreign_lock=foreign_lock), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
                manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts", worktree_root=None,
                    run_id="ownership", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
                worktree = pathlib.Path(manifest["worktree"])
                lock = pathlib.Path(manifest["lockPath"])
                if foreign_lock:
                    cycle.atomic_json(lock, {"runId": "someone-else"})
                else:
                    cycle.git(worktree, "checkout", "-b", "someone-else")
                with self.assertRaises(cycle.CycleError), contextlib.redirect_stdout(io.StringIO()):
                    cycle.finalize(SimpleNamespace(run_root=root / "artifacts/weekly-improvements/ownership", outcome="blocked", pr_url=None,
                        state_path=None, manifest=manifest))
                self.assertTrue(worktree.exists())
                self.assertTrue(lock.exists())
                authority = cycle.read_json(root / "artifacts/state/weekly-improvement.json", {})
                self.assertNotIn("lastSuccessfulRun", authority)

    def test_commit_failure_keeps_requested_worktree_and_emits_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, env = fixtures.FreshnessJobIntegrationTests().fixture(root)
            args = SimpleNamespace(repository=repository, artifact_root=root / "artifacts", installed_root=None,
                command_timeout=30, run_id="retained", thread_review=None, cycle="weekly", ref=None,
                keep_worktree=True, watch_consumer=None, skip_web=True)
            def collect(runner, *rest):
                cycle.atomic_json(runner.root / "actions.json", {"summary": {"eligible": 0}})
                runner.source_update = {"statePath": str(root / "sources.json"), "observations": {}}
            output = io.StringIO()
            with mock.patch.dict(os.environ, env), mock.patch.object(jobs, "collect", side_effect=collect), \
                 mock.patch.object(jobs.source_watch, "commit", side_effect=OSError("commit failed")) as commit, \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(jobs.run(args, cycle), 1)
            result = json.loads(output.getvalue())
            self.assertTrue(result["retainedForReview"])
            self.assertEqual(result["outcome"], "blocked")
            self.assertTrue(pathlib.Path(result["worktree"]).exists())
            self.assertTrue((root / "artifacts/state/weekly-improvement.lock.json").exists())
            self.assertTrue(cycle.git(repository, "show-ref", "--verify", "refs/heads/codex/weekly-improvement-retained"))
            self.assertTrue(pathlib.Path(result["report"]).exists())
            commit.assert_called_once()

    def test_corrupt_authority_cleans_resources_and_preserves_unbacked_bytes(self):
        for failed_backup in (False, True):
            with self.subTest(failed_backup=failed_backup), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
                manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts",
                    worktree_root=None, run_id="corrupt", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
                run = root / "artifacts/weekly-improvements/corrupt"
                authority = root / "artifacts/state/weekly-improvement.json"
                original = b'\xff prior authority bytes'
                authority.write_bytes(original)
                options = SimpleNamespace(run_root=run, outcome="blocked", pr_url=None, state_path=None, manifest=manifest)
                with mock.patch.object(pathlib.Path, "write_bytes", side_effect=OSError("backup failed")) if failed_backup else contextlib.nullcontext():
                    with self.assertRaises(cycle.CycleError), contextlib.redirect_stdout(io.StringIO()):
                        cycle.finalize(options)
                self.assertFalse(pathlib.Path(manifest["worktree"]).exists())
                self.assertFalse(cycle.git(repository, "show-ref", "--verify", f"refs/heads/{manifest['branch']}", check=False))
                if failed_backup:
                    self.assertEqual(authority.read_bytes(), original)
                    self.assertTrue(pathlib.Path(manifest["lockPath"]).exists())
                else:
                    self.assertEqual((run / "previous-authority-state.txt").read_bytes(), original)
                    self.assertFalse(pathlib.Path(manifest["lockPath"]).exists())
                self.assertEqual(cycle.read_json(run / "run.json")["status"], "cleanup-failed" if failed_backup else "blocked")

    def test_completed_retry_checks_outcome_and_uses_persisted_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
            manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts",
                worktree_root=None, run_id="retry", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
            run = root / "artifacts/weekly-improvements/retry"
            options = SimpleNamespace(run_root=run, outcome="blocked", pr_url=None, state_path=None, manifest=manifest)
            with contextlib.redirect_stdout(io.StringIO()):
                cycle.finalize(options)
                cycle.finalize(options)  # The supplied preparation is intentionally stale.
            self.assertEqual(len(cycle.read_json(root / "artifacts/state/weekly-improvement.json")["runs"]), 1)
            persisted = cycle.read_json(run / "run.json")
            persisted.update(status="draft", prUrl="https://example.com/pr/1")
            cycle.atomic_json(run / "run.json", persisted)
            options.outcome, options.pr_url = "ready", persisted["prUrl"]
            with self.assertRaisesRegex(cycle.CycleError, "already finalized as draft"):
                cycle.finalize(options)
            self.assertEqual(cycle.read_json(run / "run.json")["status"], "draft")

    def test_unreadable_authority_and_failed_backup_preserve_history_until_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
            manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts",
                worktree_root=None, run_id="authority-retry", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
            authority = (root / "artifacts/state/weekly-improvement.json").resolve()
            anchor = {"runId": "earlier", "finishedAt": "2026-11-01T00:00:00Z", "outcome": "no-change"}
            original = {"schemaVersion": 2, "runs": [anchor], "lastCollectedRun": anchor, "lastSuccessfulRun": anchor}
            cycle.atomic_json(authority, original)
            original_bytes = authority.read_bytes()
            real_read = cycle.read_json
            def read(path, *arguments):
                if path == authority:
                    raise OSError("authority temporarily unreadable")
                return real_read(path, *arguments)
            run = root / "artifacts/weekly-improvements/authority-retry"
            options = SimpleNamespace(run_root=run, outcome="blocked", pr_url=None, state_path=None, manifest=manifest)
            with mock.patch.object(cycle, "read_json", side_effect=read), \
                 mock.patch.object(pathlib.Path, "write_bytes", side_effect=OSError("backup failed")), \
                 self.assertRaises(cycle.CycleError):
                cycle.finalize(options)
            self.assertEqual(authority.read_bytes(), original_bytes)
            self.assertFalse(pathlib.Path(manifest["worktree"]).exists())
            with contextlib.redirect_stdout(io.StringIO()):
                cycle.finalize(options)
                cycle.finalize(options)
            state = real_read(authority)
            self.assertEqual(state["lastCollectedRun"], anchor)
            self.assertEqual(state["lastSuccessfulRun"], anchor)
            self.assertEqual([row["runId"] for row in state["runs"]], ["earlier", "authority-retry"])
            self.assertFalse(pathlib.Path(manifest["lockPath"]).exists())

    def test_explicit_remote_ref_is_refreshed_while_local_ref_and_sha_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
            old = cycle.git(repository, "rev-parse", "HEAD")
            cycle.git(repository, "branch", "local-candidate", old)
            (repository / "notes/candidate.md").write_text("reviewed candidate\n")
            cycle.git(repository, "add", "notes/candidate.md")
            cycle.git(repository, "commit", "-m", "candidate")
            latest = cycle.git(repository, "rev-parse", "HEAD")
            cycle.git(repository, "push", "origin", "HEAD:refs/heads/candidate")
            for n, ref in enumerate(("origin/candidate", "refs/remotes/origin/candidate", "local-candidate", old)):
                cycle.git(repository, "update-ref", "refs/remotes/origin/candidate", old)
                manifest = cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts", worktree_root=None,
                    run_id=f"ref-{n}", skip_remote_check=True, ref=ref))
                self.assertEqual(manifest["requestedRef"], ref)
                self.assertEqual(manifest["baseSha"], latest if n < 2 else old)
                with contextlib.redirect_stdout(io.StringIO()):
                    cycle.finalize(SimpleNamespace(run_root=root / f"artifacts/weekly-improvements/ref-{n}", outcome="blocked", pr_url=None,
                        state_path=None, manifest=manifest))

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

    def test_interrupt_inside_git_creation_removes_partial_and_complete_resources(self):
        for complete in (False, True):
            with self.subTest(complete=complete), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
                original = cycle.git
                def git(repo, *args, **kwargs):
                    if args[:2] == ("worktree", "add"):
                        if complete:
                            original(repo, *args, **kwargs)
                        else:
                            original(repo, "branch", args[3], args[5])
                        raise KeyboardInterrupt("terminated during Git creation")
                    return original(repo, *args, **kwargs)
                with mock.patch.object(cycle, "git", side_effect=git), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(KeyboardInterrupt):
                        cycle.prepare_run(SimpleNamespace(repository=repository, artifact_root=root / "artifacts", worktree_root=None,
                            run_id="creation", skip_remote_check=True, skip_fetch=True, ref="HEAD"))
                self.assertFalse((root / "artifacts/worktrees/creation").exists())
                self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())
                self.assertFalse(original(repository, "show-ref", "--verify", "refs/heads/codex/weekly-improvement-creation", check=False))

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
    def test_real_docs_subprocess_disagreement_and_crashes(self):
        for failure in (None, "missing-manifest", "traceback-after-manifest"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                runner = jobs.Runner(root / "run", root, cycle)
                overview, member = root / "overview.md", root / "member.md"
                overview.write_text("func resolve(in:)\n")
                member.write_text("func resolved(in:)\n")
                real_command = runner.command
                def command(name, argv, **options):
                    if name == "research-mirrors":
                        argv = [sys.executable, "-c", "print('mirrors checked')"]
                    else:
                        argv = [sys.executable, str(fixtures.ROOT / "scripts/capture-apple-docs-watch.py"),
                                "--output", str(runner.root / "apple-docs"), "--overview-source", str(overview),
                                "--member-source", str(member)]
                        if failure == "missing-manifest":
                            argv = [sys.executable, "-c", "raise RuntimeError('capture crashed')"]
                        elif failure == "traceback-after-manifest":
                            argv = [sys.executable, "-c", "import runpy,sys; sys.argv=sys.argv[1:]; "
                                    "\ntry: runpy.run_path(sys.argv[0],run_name='__main__')"
                                    "\nexcept SystemExit: raise RuntimeError('crashed after capture')", *argv[1:]]
                    return real_command(name, argv, **options)
                with mock.patch.object(runner, "command", side_effect=command), runner.lane("auxiliary"):
                    jobs.collect_auxiliary(runner, "weekly", {}, None, SimpleNamespace(skip_web=False, artifact_root=root))
                result = next(step for step in runner.steps if step["name"] == "apple-docs-watch")
                self.assertEqual(result["status"], "blocked" if failure else "passed")
                if failure:
                    self.assertIsNone(runner.source_update)
                else:
                    self.assertFalse(any(step["status"] == "blocked" for step in runner.steps))
                    self.assertEqual(runner.findings[0]["kind"], "documentation-disagreement")

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
                    (root / "docs.stdout").write_bytes((root / "apple-docs/manifest.json").read_bytes())
                    (root / "docs.stderr").write_text("")
                return runner.record(name, "blocked" if name == "apple-docs-watch" else "passed", exitCode=1 if name == "apple-docs-watch" else 0,
                                     stdout=str(root / "docs.stdout"), stderr=str(root / "docs.stderr"))
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
    def capture(self, root, state, docs="# Initial\n", versions=(("27.2", "27B52"),), reviewed_builds=None, news_payload=None):
        runner = jobs.Runner(root, root, cycle)
        feed = ('<rss><channel>' + ''.join(f'<item><title>Xcode {v} ({b})</title><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item>' for v, b in versions) + '</channel></rss>').encode()
        def response(request, timeout):
            return io.BytesIO(docs.encode() if request.full_url.endswith(".md") else
                              news_payload if news_payload is not None and request.full_url == jobs.SOURCES["news"] else feed)
        baseline = {"environment": {"latestObserved": {"xcode": {"version": "27.2", "build": "27B52"}}}}
        if reviewed_builds is not None:
            baseline["environment"]["latestObserved"]["xcode"]["reviewedBuilds"] = reviewed_builds
        with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response):
            jobs.watch_sources(runner, baseline, state)
        jobs.source_watch.commit(runner.source_update, cycle)
        jobs.write_report(runner, "daily", "findings", emit=False)
        return runner

    def test_news_rebuilds_order_content_and_equivalent_acknowledgments(self):
        def feed(build, content="first", reverse=False):
            items = [f'<item><guid>a</guid><title>A</title><description>{content}</description></item>',
                     '<item><guid>b</guid><title>B</title></item>']
            if reverse:
                items.reverse()
            return ('<rss><channel><lastBuildDate>' + build + '</lastBuildDate>' + ''.join(items) + '</channel></rss>').encode()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = pathlib.Path(directory)
            state = root / "state/news.json"
            self.capture(root / "one", state, news_payload=feed("one"))
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "one"), cycle)
            self.assertEqual(self.capture(root / "two", state, news_payload=feed("two", reverse=True)).findings, [])
            changed = self.capture(root / "three", state, news_payload=feed("three", "edited"))
            finding = next(f for f in changed.findings if f["source"] == "news")
            self.assertEqual([item["id"] for item in finding["updatedItems"]], ["a"])
            self.capture(root / "four", state, news_payload=feed("four", "edited", True))
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "three"), cycle)
            self.assertEqual(self.capture(root / "five", state, news_payload=feed("five", "edited")).findings, [])
            self.capture(root / "six", state, news_payload=feed("six", "newer"))
            with self.assertRaisesRegex(cycle.CycleError, "stale news"):
                jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "three"), cycle)

    def test_pre_upgrade_observed_news_can_be_acknowledged_and_migrates_all_sections(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = pathlib.Path(directory)
            state_path = root / "state/news.json"
            self.capture(root / "one", state_path)
            state = cycle.read_json(state_path)
            for section in ("latestObserved", "pending"):
                for item in state[section]["news"]["newsItems"]:
                    item.pop("content")
                state[section]["news"].pop("report", None)
            cycle.atomic_json(state_path, state)
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "one"), cycle)
            self.assertNotIn("news", cycle.read_json(state_path)["pending"])
            state = cycle.read_json(state_path)
            news = state["reviewed"]["news"]
            state["latestObserved"]["news"] = dict(news)
            state["pending"]["news"] = dict(news)
            for section in ("reviewed", "latestObserved", "pending"):
                state[section]["news"] = {**state[section]["news"], "newsItems": [
                    {k: v for k, v in item.items() if k != "content"} for item in news["newsItems"]]}
            cycle.atomic_json(state_path, state)
            migrated = jobs.source_watch.load(state_path, cycle)
            for section in ("reviewed", "latestObserved", "pending"):
                self.assertIsNotNone(jobs.source_watch.news_hash(migrated[section]["news"]))

    def test_duplicate_news_is_idempotent_and_conflicting_variants_remain_reviewable(self):
        def feed(values):
            return ('<rss><channel>' + ''.join('<item><guid>a</guid><title>A</title><description>' + value +
                '</description></item>' for value in values) + '</channel></rss>').encode()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = pathlib.Path(directory)
            state = root / "state/news.json"
            self.capture(root / "one", state, news_payload=feed(['first']))
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "one"), cycle)
            self.assertEqual(self.capture(root / "two", state, news_payload=feed(['first', 'first'])).findings, [])
            changed = self.capture(root / "three", state, news_payload=feed(['first', 'edited', 'first']))
            finding = next(item for item in changed.findings if item['source'] == 'news')
            self.assertEqual(len(finding['identityConflicts'][0]['variants']), 2)
            self.assertEqual(len(finding['updatedItems']), 2)
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "three"), cycle)
            self.assertEqual(self.capture(root / "four", state, news_payload=feed(['edited', 'first'])).findings, [])
            self.assertTrue(self.capture(root / "five", state, news_payload=feed(['edited'])).findings)

    def test_legacy_news_upgrade_requires_retained_capture_or_explicit_review(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = pathlib.Path(directory)
            state = root / "state/news.json"
            self.capture(root / "one", state)
            jobs.source_watch.acknowledge(SimpleNamespace(run_root=root / "one"), cycle)
            original = cycle.read_json(state)
            for item in original["reviewed"]["news"]["newsItems"]:
                item.pop("content")
            cycle.atomic_json(state, original)
            self.assertEqual(self.capture(root / "two", state).findings, [])
            original["reviewed"]["news"].pop("report")
            cycle.atomic_json(state, original)
            self.assertEqual(self.capture(root / "three", state).findings, [])
            rebuilt = (root / "one/official-sources/news.txt").read_bytes().replace(
                b'<channel>', b'<channel><lastBuildDate>rebuilt</lastBuildDate>')
            finding = next(f for f in self.capture(root / "four", state, news_payload=rebuilt).findings if f["source"] == "news")
            self.assertTrue(finding["migrationRequired"])

    def test_bad_state_preserves_bytes_and_does_not_block_release_capture(self):
        malformed = jobs.source_watch.empty_state()
        malformed['reviewed']['news'] = {'sha256': 'old', 'capturedAt': 'invalid', 'url': 'url', 'report': 42}
        for original in (b'\xff', b'{broken JSON', json.dumps(malformed).encode()):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                state = root / "bad.json"
                state.write_bytes(original)
                runner = jobs.Runner(root / "run", root, cycle)
                feed = b'<rss><channel><item><title>Xcode 28.0 (new)</title><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item></channel></rss>'
                def response(request, timeout):
                    return io.BytesIO(b'# Docs' if request.full_url.endswith('.md') else feed)
                baseline = {"environment": {"latestObserved": {"xcode": {"version": "27.2", "build": "old"}}}}
                with mock.patch.object(jobs.urllib.request, "urlopen", side_effect=response) as fetch:
                    jobs.watch_sources(runner, baseline, state)
                self.assertEqual(fetch.call_count, 3)
                self.assertTrue(any(f["kind"] == "release-changed" for f in runner.findings))
                with self.assertRaisesRegex(ValueError, "unreadable"):
                    jobs.source_watch.commit(runner.source_update, cycle)
                self.assertEqual(state.read_bytes(), original)

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
