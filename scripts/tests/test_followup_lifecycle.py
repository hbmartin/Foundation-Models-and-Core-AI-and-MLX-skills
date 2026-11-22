"""Failures between persistence boundaries must remain recoverable."""
import contextlib
import io
import json
import os
import pathlib
import signal
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from scripts.tests import test_freshness_jobs as fixtures

cycle, jobs = fixtures.cycle, fixtures.jobs


class FollowupLifecycleTests(unittest.TestCase):
    def prepare(self, root, run_id="followup"):
        repository = fixtures.cycle_tests.FreshnessCycleTests().repository(root)
        args = SimpleNamespace(repository=repository, artifact_root=root / "artifacts", worktree_root=None,
                               run_id=run_id, skip_remote_check=True, skip_fetch=True, ref="HEAD")
        return repository, args

    def options(self, root, manifest, outcome="blocked"):
        return SimpleNamespace(run_root=root / f"artifacts/weekly-improvements/{manifest['runId']}",
                               manifest=manifest, outcome=outcome, pr_url=None, state_path=None)

    def test_duplicate_branch_releases_lock_and_preserves_existing_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, args = self.prepare(root)
            branch = "codex/weekly-improvement-followup"
            cycle.git(repository, "branch", branch)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(cycle.CycleError, "branch already exists"):
                cycle.prepare_run(args)
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())
            self.assertTrue(cycle.git(repository, "show-ref", "--verify", f"refs/heads/{branch}"))
            state = cycle.read_json(root / "artifacts/state/weekly-improvement.json")
            self.assertIn("branch already exists", state["lastRun"]["preparationError"])

    def test_preparation_progress_and_error_survive_failed_writes_and_git(self):
        for failure in ("progress-write", "worktree-add"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository, args = self.prepare(root)
                write, git = cycle.atomic_json, cycle.git
                injected = False
                def atomic(path, payload):
                    nonlocal injected
                    if failure == "progress-write" and path.name == "run.json" and payload.get("branchCreated") and not injected:
                        injected = True
                        raise OSError("preparation progress write failed")
                    return write(path, payload)
                def command(repository, *arguments, **kwargs):
                    if failure == "worktree-add" and arguments[:2] == ("worktree", "add"):
                        raise cycle.CycleError("worktree add failed")
                    return git(repository, *arguments, **kwargs)
                with mock.patch.object(cycle, "atomic_json", side_effect=atomic), mock.patch.object(cycle, "git", side_effect=command), \
                     contextlib.redirect_stdout(io.StringIO()), self.assertRaises((OSError, cycle.CycleError)):
                    cycle.prepare_run(args)
                run = root / "artifacts/weekly-improvements/followup"
                manifest = cycle.read_json(run / "run.json")
                state = cycle.read_json(root / "artifacts/state/weekly-improvement.json")
                self.assertTrue(manifest["preparationError"])
                self.assertEqual(manifest["preparationError"], state["lastRun"]["preparationError"])
                self.assertFalse(pathlib.Path(manifest["lockPath"]).exists())
                self.assertFalse(pathlib.Path(manifest["worktree"]).exists())

    def test_invalid_manifest_is_preserved_and_trusted_identity_cleans(self):
        for payload in (b"[]", b'["bad"]', b'null', b'{}', b'{"wrong":true}', b"\xff"):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository, args = self.prepare(root)
                manifest = cycle.prepare_run(args)
                options = self.options(root, manifest)
                (options.run_root / "run.json").write_bytes(payload)
                with self.assertRaisesRegex(cycle.CycleError, "without trusted identity"):
                    cycle.finalize(SimpleNamespace(**{**vars(options), "manifest": None}))
                self.assertTrue(pathlib.Path(manifest["worktree"]).exists())
                with self.assertRaisesRegex(cycle.CycleError, "run manifest:"), contextlib.redirect_stdout(io.StringIO()):
                    cycle.finalize(options)
                self.assertEqual((options.run_root / "previous-run-manifest.txt").read_bytes(), payload)
                self.assertFalse(pathlib.Path(manifest["lockPath"]).exists())
                self.assertFalse(pathlib.Path(manifest["worktree"]).exists())

    def interrupted_finalization(self, root, outcome="ready"):
        repository, args = self.prepare(root)
        manifest = cycle.prepare_run(args)
        options = self.options(root, manifest, outcome)
        options.pr_url = "https://example.com/pr/1"
        worktree = pathlib.Path(manifest["worktree"])
        (worktree / "guides").mkdir()
        (worktree / "guides/test.md").write_text("changed\n")
        cycle.git(worktree, "add", "guides/test.md")
        cycle.git(worktree, "commit", "-m", "change")
        cycle.atomic_json(options.run_root / "actions.json", {"actions": [{
            "automaticFixEligible": True, "paths": ["guides/test.md"]}]})
        cycle.atomic_json(options.run_root / "pr.json", {"checksPassed": True, "mergeable": True})
        unlink = pathlib.Path.unlink
        def fail(path, *arguments, **kwargs):
            if path == pathlib.Path(manifest["lockPath"]):
                raise OSError("lock release failed")
            return unlink(path, *arguments, **kwargs)
        with mock.patch.object(pathlib.Path, "unlink", fail), \
             mock.patch.object(cycle, "generated_validation_failures", return_value=[]), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(cycle.CycleError, "lock release failed"):
            cycle.finalize(options)
        self.assertFalse(worktree.exists())
        return repository, manifest, options

    def test_ready_cleanup_retry_uses_durable_validation_and_one_history_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, manifest, options = self.interrupted_finalization(root)
            saved = cycle.read_json(options.run_root / "run.json")
            self.assertEqual(saved["validationReceipt"]["request"]["outcome"], "ready")
            self.assertEqual(saved["validationReceipt"]["validators"], ["indexes", "skills"])
            with mock.patch.object(cycle, "generated_validation_failures", side_effect=AssertionError("no worktree")), \
                 contextlib.redirect_stdout(io.StringIO()):
                cycle.finalize(options)
                cycle.finalize(options)
            state = cycle.read_json(root / "artifacts/state/weekly-improvement.json")
            self.assertEqual(len(state["runs"]), 1)
            self.assertEqual(state["lastSuccessfulRun"]["outcome"], "ready")

    def test_missing_worktree_cannot_change_validated_request_or_evidence(self):
        for change in ("outcome", "actions", "pr", "revision", "receipt", "validators", "results"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository, manifest, options = self.interrupted_finalization(root, "draft")
                if change == "outcome":
                    options.outcome = "ready"
                elif change in {"actions", "pr"}:
                    path = options.run_root / f"{change}.json"
                    path.write_text(path.read_text() + "\n")
                elif change == "revision":
                    cycle.git(repository, "update-ref", f"refs/heads/{manifest['branch']}", manifest["baseSha"])
                elif change in {"receipt", "validators", "results"}:
                    saved = cycle.read_json(options.run_root / "run.json")
                    if change == "receipt":
                        saved.pop("validationReceipt")
                    else:
                        saved["validationReceipt"].pop('validators' if change == 'validators' else 'generatedOutputFailures')
                    cycle.atomic_json(options.run_root / "run.json", saved)
                with self.assertRaisesRegex(cycle.CycleError, "missing worktree"):
                    cycle.finalize(options)
                self.assertTrue(pathlib.Path(manifest["lockPath"]).exists())

    def test_receipt_persistence_failure_leaves_worktree_for_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, args = self.prepare(root)
            manifest = cycle.prepare_run(args)
            options = self.options(root, manifest, "no-change")
            write = cycle.atomic_json
            def fail(path, payload):
                if path.name == "run.json" and payload.get("validationReceipt"):
                    raise OSError("receipt write failed")
                return write(path, payload)
            with mock.patch.object(cycle, "atomic_json", side_effect=fail), self.assertRaisesRegex(OSError, "receipt write"):
                cycle.finalize(options)
            self.assertTrue(pathlib.Path(manifest["worktree"]).exists())
            self.assertTrue(pathlib.Path(manifest["lockPath"]).exists())

    def test_repeated_downgraded_request_reports_original_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repository, args = self.prepare(root)
            manifest = cycle.prepare_run(args)
            options = self.options(root, manifest, "no-change")
            write = cycle.atomic_json
            failed = False
            def fail_once(path, payload):
                nonlocal failed
                if path.name == "weekly-improvement.json" and not failed:
                    failed = True
                    raise OSError("transient authority write")
                return write(path, payload)
            with mock.patch.object(cycle, "atomic_json", side_effect=fail_once), self.assertRaises(cycle.CycleError):
                cycle.finalize(options)
            with self.assertRaisesRegex(cycle.CycleError, "previous finalization failed:.*transient authority write"):
                cycle.finalize(options)

    def test_retained_initialization_and_interruptions_record_pending_failure(self):
        for failure in ("initialization", "termination", "sigterm"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                repository, env = fixtures.FreshnessJobIntegrationTests().fixture(root)
                args = SimpleNamespace(repository=repository, artifact_root=root / "artifacts", installed_root=None,
                    command_timeout=30, run_id="retained", thread_review=None, cycle="weekly", ref=None,
                    keep_worktree=True, watch_consumer=None, skip_web=True)
                anchor = {"runId": "previous", "outcome": "ready", "finishedAt": "2026-11-01T00:00:00Z"}
                cycle.atomic_json(root / "artifacts/state/weekly-improvement.json", {
                    "schemaVersion": 2, "runs": [anchor], "lastCollectedRun": anchor, "lastSuccessfulRun": anchor})
                patch = (mock.patch.object(jobs, "Runner", side_effect=OSError("constructor failed")) if failure == "initialization"
                         else mock.patch.object(jobs, "collect", side_effect=lambda *args: os.kill(os.getpid(), signal.SIGTERM))
                         if failure == "sigterm" else mock.patch.object(jobs, "collect", side_effect=KeyboardInterrupt("terminated")))
                output = io.StringIO()
                with mock.patch.dict(os.environ, env), patch, contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                    code = jobs.run(args, cycle)
                self.assertEqual(code, 1 if failure == "initialization" else 130)
                result = json.loads(output.getvalue())
                self.assertTrue(result["retainedForReview"])
                manifest = cycle.read_json(pathlib.Path(result["runRoot"]) / "run.json")
                state = cycle.read_json(root / "artifacts/state/weekly-improvement.json")
                self.assertEqual(manifest["status"], "retained")
                self.assertEqual(manifest["collectionOutcome"], "blocked")
                self.assertTrue(manifest["collectionErrors"])
                self.assertTrue(pathlib.Path(manifest["worktree"]).exists())
                self.assertTrue(pathlib.Path(manifest["lockPath"]).exists())
                self.assertTrue(state["pending"]["retainedForReview"])
                self.assertEqual(state["lastSuccessfulRun"], anchor)
                self.assertEqual(state["lastCollectedRun"], anchor)
                self.assertEqual(len(state["runs"]), 2)
                self.assertTrue(pathlib.Path(result["report"]).exists())


if __name__ == "__main__":
    unittest.main()
