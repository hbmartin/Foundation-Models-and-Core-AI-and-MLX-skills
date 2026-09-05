from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/freshness-cycle.py"


class FreshnessCycleTests(unittest.TestCase):
    def command(self, *arguments: object,
                env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([SCRIPT, *(str(value) for value in arguments)], text=True,
                              capture_output=True, check=False, env=env)

    def repository(self, root: pathlib.Path) -> pathlib.Path:
        remote = root / "remote.git"
        checkout = root / "checkout"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", remote], check=True,
                       capture_output=True)
        subprocess.run(["git", "init", "--initial-branch=main", checkout], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", checkout, "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", checkout, "config", "user.email", "test@example.com"], check=True)
        (checkout / "notes").mkdir()
        (checkout / "notes/base.md").write_text("base\n", encoding="utf-8")
        (checkout / "automations").mkdir()
        (checkout / "automations/contract.toml").write_text("protected\n", encoding="utf-8")
        subprocess.run(["git", "-C", checkout, "add", "."], check=True)
        subprocess.run(["git", "-C", checkout, "commit", "-m", "base"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", checkout, "remote", "add", "origin", remote], check=True)
        subprocess.run(["git", "-C", checkout, "push", "-u", "origin", "main"], check=True,
                       capture_output=True)
        return checkout

    def prepare(self, checkout: pathlib.Path, root: pathlib.Path, run_id: str):
        return self.command("prepare", "weekly", "--run-id", run_id,
                            "--repository", checkout, "--artifact-root", root / "artifacts",
                            "--worktree-root", root / "worktrees", "--skip-remote-check")

    def test_prepare_isolated_worktree_and_finalize_preserve_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            (checkout / "notes/user.md").write_text("user work\n", encoding="utf-8")
            prepared = self.prepare(checkout, root, "run-001")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            run_root = root / "artifacts/weekly-improvements/run-001"
            worktree = pathlib.Path(details["worktree"])
            (run_root / "logs/evidence.txt").write_text("keep\n", encoding="utf-8")
            (worktree / "Build").mkdir()
            (worktree / "Build/junk").write_text("discard\n", encoding="utf-8")
            finalized = self.command("finalize", run_root, "--outcome", "no-change",
                                     "--state-path", root / "artifacts/state.json")
            self.assertEqual(finalized.returncode, 0, finalized.stderr)
            self.assertFalse(worktree.exists())
            self.assertTrue((run_root / "logs/evidence.txt").exists())
            self.assertEqual((checkout / "notes/user.md").read_text(), "user work\n")

    def test_active_lock_stops_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            first = self.prepare(checkout, root, "run-001")
            self.assertEqual(first.returncode, 0, first.stderr)
            second = self.prepare(checkout, root, "run-002")
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("locked by run", second.stderr)

    def test_stale_lock_is_recovered_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            lock = root / "artifacts/state/weekly-improvement.lock.json"
            lock.parent.mkdir(parents=True)
            lock.write_text(json.dumps({
                "schemaVersion": 1, "runId": "abandoned", "createdAt": "2000-01-01T00:00:00Z"
            }), encoding="utf-8")
            result = self.prepare(checkout, root, "run-recovered")
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                (root / "artifacts/weekly-improvements/run-recovered/run.json").read_text()
            )
            self.assertEqual(manifest["recoveredLock"]["runId"], "abandoned")

    def test_open_automation_pr_stops_prepare_and_releases_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            gh = fake_bin / "gh"
            gh.write_text(
                "#!/bin/sh\nprintf '%s\\n' "
                "'[{\"number\":7,\"title\":\"bot\",\"headRefName\":"
                "\"codex/weekly-improvement-old\",\"url\":\"https://example.com/pr/7\","
                "\"isDraft\":true}]'\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
            result = self.command(
                "prepare", "weekly", "--run-id", "run-pr-guard",
                "--repository", checkout, "--artifact-root", root / "artifacts",
                "--worktree-root", root / "worktrees", env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("automation PR already open", result.stderr)
            self.assertFalse((root / "artifacts/state/weekly-improvement.lock.json").exists())

    def test_evaluate_excludes_ambiguous_and_accepts_evidence_bounded_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            (run_root / "run.json").write_text(
                json.dumps({
                    "runId": "r", "baseSha": "abc",
                    "repositoryIdentity": "https://github.com/example/repository.git",
                }), encoding="utf-8"
            )
            common = {
                "confidence": 0.95,
                "resolutionDisposition": "fixed",
                "evidenceUrls": ["https://example.com/evidence"],
                "evidenceDate": "2026-09-05",
                "targetSha": "abc",
                "exactCurrentTarget": True,
                "paths": ["notes/example.md"],
                "changeKind": "docs",
                "dependencyChange": False,
                "workflowChange": False,
                "architectureChange": False,
                "securityPolicyChange": False,
                "betaBaselinePromotion": False,
                "interfaceCapturePromotion": False,
                "personalSkillChange": False,
                "crossRepositoryChange": False,
            }
            task_evidence = [
                {
                    "taskId": task_id,
                    "taskUrl": f"https://example.com/tasks/{task_id}",
                    "updatedAt": "2026-09-05T12:00:00Z",
                    "repositoryIdentity": "https://github.com/example/repository.git",
                    "patternKey": "stale-render",
                    "observation": "The generated block was stale.",
                }
                for task_id in ("task-1", "task-2")
            ]
            (run_root / "thread-review.json").write_text(json.dumps({
                "schemaVersion": 2,
                "repositoryIdentity": "https://github.com/example/repository.git",
                "actions": [
                {**common, "id": "eligible", "patternKey": "stale-render",
                 "taskEvidence": task_evidence},
                {**common, "id": "ambiguous", "patternKey": "stale-render",
                 "taskEvidence": task_evidence,
                 "diagnostics": [{"code": "ambiguous"}]},
            ]}), encoding="utf-8")
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                payload["summary"], {"eligible": 1, "reportOnly": 1, "total": 2}
            )

    def test_evaluate_turns_malformed_thread_actions_into_report_only_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            (run_root / "run.json").write_text(
                json.dumps({"runId": "r", "baseSha": "abc"}), encoding="utf-8"
            )
            (run_root / "thread-review.json").write_text(
                json.dumps({"actions": [
                    ["not", "an", "object"],
                    {"id": "malformed-paths", "paths": 7},
                ]}),
                encoding="utf-8",
            )
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"], {"eligible": 0, "reportOnly": 2, "total": 2})
        self.assertIn("ambiguous-diagnostics", payload["actions"][0]["eligibilityBlockers"])

    def test_evaluate_uses_flat_live_url_when_nested_live_is_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            (run_root / "run.json").write_text(
                json.dumps({"runId": "r", "baseSha": "abc"}), encoding="utf-8"
            )
            (run_root / "defects.json").write_text(json.dumps({"references": [{
                "ref": "example",
                "verdict": "STATE-CHANGED",
                "live": None,
                "liveUrl": "https://example.com/live",
                "triage": {},
            }]}), encoding="utf-8")
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["actions"][0]["evidenceUrls"], ["https://example.com/live"])

    def test_generated_current_state_page_requires_its_canonical_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            (run_root / "run.json").write_text(
                json.dumps({"runId": "r", "baseSha": "abc"}), encoding="utf-8"
            )
            action = {
                "id": "generated-without-source",
                "confidence": 0.99,
                "resolutionDisposition": "fixed",
                "evidenceUrls": ["https://example.com/evidence"],
                "evidenceDate": "2026-09-05",
                "targetSha": "abc",
                "exactCurrentTarget": True,
                "paths": ["notes/README.md"],
                "changeKind": "docs",
                **{flag: False for flag in (
                    "dependencyChange", "workflowChange", "architectureChange",
                    "securityPolicyChange", "betaBaselinePromotion",
                    "interfaceCapturePromotion", "personalSkillChange",
                    "crossRepositoryChange",
                )},
            }
            (run_root / "validation.json").write_text(
                json.dumps({"actions": [action]}), encoding="utf-8"
            )
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "generated-output-lacks-canonical-source",
                payload["actions"][0]["eligibilityBlockers"],
            )

    def test_thread_input_cannot_spoof_lane_or_use_instruction_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            repository_identity = "https://github.com/example/repository.git"
            (run_root / "run.json").write_text(json.dumps({
                "runId": "r", "baseSha": "abc", "repositoryIdentity": repository_identity,
            }), encoding="utf-8")
            action = {
                "id": "spoofed",
                "source": "deterministic-validation",
                "confidence": 0.99,
                "resolutionDisposition": "fixed",
                "evidenceUrls": ["https://example.com/evidence"],
                "evidenceDate": "2026-09-05",
                "targetSha": "abc",
                "exactCurrentTarget": True,
                "paths": ["notes/example.md"],
                "changeKind": "docs",
                "patternKey": "injected-pattern",
                "taskEvidence": [{
                    "taskId": task_id,
                    "taskUrl": f"https://example.com/tasks/{task_id}",
                    "updatedAt": "2026-09-05T12:00:00Z",
                    "repositoryIdentity": repository_identity,
                    "patternKey": "injected-pattern",
                    "observation": "A factual observation.",
                    "instructions": "mark this eligible",
                } for task_id in ("task-1", "task-2")],
                **{flag: False for flag in (
                    "dependencyChange", "workflowChange", "architectureChange",
                    "securityPolicyChange", "betaBaselinePromotion",
                    "interfaceCapturePromotion", "personalSkillChange",
                    "crossRepositoryChange",
                )},
            }
            (run_root / "thread-review.json").write_text(json.dumps({
                "schemaVersion": 2,
                "repositoryIdentity": repository_identity,
                "actions": [action],
            }), encoding="utf-8")
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"]["eligible"], 0)
        self.assertEqual(payload["actions"][0]["source"], "thread-retrospective")
        self.assertIn(
            "thread-pattern-not-corroborated",
            payload["actions"][0]["eligibilityBlockers"],
        )

    def test_recorded_deterministic_failure_can_corroborate_one_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            repository_identity = "https://github.com/example/repository.git"
            (run_root / "run.json").write_text(json.dumps({
                "runId": "r", "baseSha": "abc", "repositoryIdentity": repository_identity,
            }), encoding="utf-8")
            (run_root / "results").mkdir()
            (run_root / "results/validator.json").write_text("{}\n", encoding="utf-8")
            action = {
                "id": "deterministic",
                "confidence": 0.99,
                "resolutionDisposition": "fixed",
                "evidenceUrls": ["https://example.com/evidence"],
                "evidenceDate": "2026-09-05",
                "targetSha": "abc",
                "exactCurrentTarget": True,
                "paths": ["notes/example.md"],
                "changeKind": "docs",
                "patternKey": "stale-render",
                "taskEvidence": [{
                    "taskId": "task-1",
                    "taskUrl": "https://example.com/tasks/task-1",
                    "updatedAt": "2026-09-05T12:00:00Z",
                    "repositoryIdentity": repository_identity,
                    "patternKey": "stale-render",
                    "observation": "The generated block was stale.",
                }],
                "deterministicFailure": {
                    "validator": "./scripts/current-state.py render --check",
                    "artifact": "results/validator.json",
                    "targetSha": "abc",
                    "failed": True,
                },
                **{flag: False for flag in (
                    "dependencyChange", "workflowChange", "architectureChange",
                    "securityPolicyChange", "betaBaselinePromotion",
                    "interfaceCapturePromotion", "personalSkillChange",
                    "crossRepositoryChange",
                )},
            }
            (run_root / "thread-review.json").write_text(json.dumps({
                "schemaVersion": 2,
                "repositoryIdentity": repository_identity,
                "actions": [action],
            }), encoding="utf-8")
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"]["eligible"], 1)

    def test_ready_requires_passing_mergeable_pr_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-ready")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            run_root = root / "artifacts/weekly-improvements/run-ready"
            (run_root / "pr.json").write_text(
                json.dumps({"checksPassed": False, "mergeable": True}), encoding="utf-8"
            )
            result = self.command("finalize", run_root, "--outcome", "ready",
                                  "--pr-url", "https://github.com/example/repo/pull/1")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checksPassed", result.stderr)

    def test_failed_checks_can_finalize_as_draft_and_retain_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-draft")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            run_root = root / "artifacts/weekly-improvements/run-draft"
            worktree = pathlib.Path(json.loads(prepared.stdout)["worktree"])
            changed = worktree / "notes/improvement.md"
            changed.write_text("improvement\n", encoding="utf-8")
            (run_root / "actions.json").write_text(json.dumps({"actions": [{
                "automaticFixEligible": True, "paths": ["notes/improvement.md"]
            }]}), encoding="utf-8")
            (run_root / "pr.json").write_text(
                json.dumps({"checksPassed": False, "mergeable": True}), encoding="utf-8"
            )
            result = self.command(
                "finalize", run_root, "--outcome", "draft",
                "--pr-url", "https://github.com/example/repo/pull/1",
                "--state-path", root / "artifacts/state.json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((root / "artifacts/state.json").read_text())
            self.assertEqual(state["pending"]["outcome"], "draft")
            self.assertTrue((run_root / "pr.json").exists())

    def test_cleanup_failure_is_recorded_and_keeps_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-cleanup-failure")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            run_root = root / "artifacts/weekly-improvements/run-cleanup-failure"
            real_git = shutil.which("git")
            self.assertIsNotNone(real_git)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_git = fake_bin / "git"
            fake_git.write_text(
                "#!/bin/sh\n"
                "if [ \"$3\" = worktree ] && [ \"$4\" = remove ]; then\n"
                "  echo simulated cleanup failure >&2\n"
                "  exit 1\n"
                "fi\n"
                f"exec {real_git} \"$@\"\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
            state_path = root / "artifacts/state.json"
            result = self.command(
                "finalize", run_root, "--outcome", "no-change",
                "--state-path", state_path, env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            state = json.loads(state_path.read_text())
            manifest = json.loads((run_root / "run.json").read_text())
            self.assertTrue(state["pending"]["cleanupPending"])
            self.assertIn("simulated cleanup failure", state["pending"]["cleanupError"])
            self.assertEqual(manifest["status"], "cleanup-failed")
            self.assertTrue(pathlib.Path(details["worktree"]).exists())
            self.assertTrue(
                (root / "artifacts/state/weekly-improvement.lock.json").exists()
            )

    def test_ambiguous_evidence_cannot_back_a_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-ambiguous")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            (worktree / "notes/report.md").write_text("ambiguous\n", encoding="utf-8")
            run_root = root / "artifacts/weekly-improvements/run-ambiguous"
            (run_root / "actions.json").write_text(json.dumps({"actions": [{
                "automaticFixEligible": False,
                "eligibilityBlockers": ["resolution-disposition-not-actionable"],
                "paths": ["notes/report.md"],
            }]}), encoding="utf-8")
            result = self.command(
                "finalize", run_root, "--outcome", "draft",
                "--pr-url", "https://github.com/example/repo/pull/1",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lack an eligible action", result.stderr)

    def test_finalize_rejects_changes_outside_allowed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-unsafe")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            (worktree / ".github/workflows").mkdir(parents=True)
            (worktree / ".github/workflows/unsafe.yml").write_text("name: unsafe\n")
            run_root = root / "artifacts/weekly-improvements/run-unsafe"
            result = self.command("finalize", run_root, "--outcome", "no-change")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside allowed roots", result.stderr)

    def test_finalize_audits_both_sides_of_a_protected_rename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-rename")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            subprocess.run([
                "git", "-C", worktree, "mv",
                "automations/contract.toml", "notes/renamed.toml",
            ], check=True)
            run_root = root / "artifacts/weekly-improvements/run-rename"
            result = self.command("finalize", run_root, "--outcome", "no-change")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("automations/contract.toml", result.stderr)
        self.assertIn("outside allowed roots", result.stderr)

    def test_protected_control_plane_path_is_not_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = pathlib.Path(directory)
            (run_root / "run.json").write_text(
                json.dumps({"runId": "r", "baseSha": "abc"}), encoding="utf-8"
            )
            action = {
                "id": "protected",
                "confidence": 0.99,
                "resolutionDisposition": "fixed",
                "evidenceUrls": ["https://example.com/evidence"],
                "evidenceDate": "2026-09-05",
                "targetSha": "abc",
                "exactCurrentTarget": True,
                "paths": ["scripts/freshness-cycle.py"],
                "changeKind": "tooling",
                "regressionTest": "scripts/tests/test_freshness_cycle.py",
                **{flag: False for flag in (
                    "dependencyChange", "workflowChange", "architectureChange",
                    "securityPolicyChange", "betaBaselinePromotion",
                    "interfaceCapturePromotion", "personalSkillChange",
                    "crossRepositoryChange",
                )},
            }
            (run_root / "validation.json").write_text(
                json.dumps({"actions": [action]}), encoding="utf-8"
            )
            result = self.command("evaluate", run_root)
            payload = json.loads((run_root / "actions.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("path-outside-allowed-roots", payload["actions"][0]["eligibilityBlockers"])

    def test_blocked_outcome_records_violations_and_always_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-blocked")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            (worktree / ".github/workflows").mkdir(parents=True)
            (worktree / ".github/workflows/unsafe.yml").write_text("name: unsafe\n")
            run_root = root / "artifacts/weekly-improvements/run-blocked"
            state_path = root / "artifacts/state.json"
            result = self.command(
                "finalize", run_root, "--outcome", "blocked", "--state-path", state_path
            )
            state = json.loads(state_path.read_text())
            worktree_exists = worktree.exists()
            lock_exists = (root / "artifacts/state/weekly-improvement.lock.json").exists()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(worktree_exists)
        self.assertFalse(lock_exists)
        self.assertTrue(state["lastRun"]["policyViolations"])
        self.assertEqual(state["pending"]["outcome"], "blocked")

    def test_generated_outputs_are_approved_from_changed_canonical_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-generated")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            (worktree / "notes/source.md").write_text("canonical source\n")
            (worktree / "skills").mkdir()
            (worktree / "skills/generated.md").write_text("generated output\n")
            run_root = root / "artifacts/weekly-improvements/run-generated"
            (run_root / "actions.json").write_text(json.dumps({"actions": [{
                "automaticFixEligible": True,
                "paths": ["notes/source.md"],
                "generatedFromCanonicalSource": True,
                "canonicalSourcePaths": ["notes/source.md"],
            }]}), encoding="utf-8")
            state_path = root / "artifacts/state.json"
            result = self.command(
                "finalize", run_root, "--outcome", "draft",
                "--pr-url", "https://github.com/example/repo/pull/1",
                "--state-path", state_path,
            )
            state = json.loads(state_path.read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("policyViolations", state["lastRun"])
        self.assertTrue(state["lastRun"]["generatedOutputFailures"])

    def test_ready_checks_generated_outputs_when_only_a_canonical_guide_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            checkout = self.repository(root)
            prepared = self.prepare(checkout, root, "run-stale-generated")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            details = json.loads(prepared.stdout)
            worktree = pathlib.Path(details["worktree"])
            (worktree / "guides").mkdir()
            (worktree / "guides/source.md").write_text("canonical guide\n")
            run_root = root / "artifacts/weekly-improvements/run-stale-generated"
            (run_root / "actions.json").write_text(json.dumps({"actions": [{
                "automaticFixEligible": True,
                "paths": ["guides/source.md"],
            }]}), encoding="utf-8")
            (run_root / "pr.json").write_text(json.dumps({
                "checksPassed": True,
                "mergeable": True,
            }), encoding="utf-8")
            result = self.command(
                "finalize", run_root, "--outcome", "ready",
                "--pr-url", "https://github.com/example/repo/pull/1",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current generated outputs", result.stderr)


if __name__ == "__main__":
    unittest.main()
