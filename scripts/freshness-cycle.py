#!/usr/bin/env python3
"""Prepare, evaluate, and finalize the repository's weekly improvement cycle."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts/freshness"
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
ALLOWED_ROOTS = ("guides/", "notes/", "probes/", "scripts/", "skills/", "automations/")
FORBIDDEN_PREFIXES = (".github/", ".git/", "repos/", "captures/", "/")
DISPOSITIONS = {
    "fixed", "fixed-with-residual", "merged-unreleased", "closed-unfixed",
    "closed-unmerged", "superseded", "consolidated", "unknown",
}
PROHIBITED_FLAGS = (
    "dependencyChange", "workflowChange", "architectureChange", "securityPolicyChange",
    "betaBaselinePromotion", "interfaceCapturePromotion", "personalSkillChange",
    "crossRepositoryChange",
)
GENERATED_OUTPUTS = ("skills/", "guides/API-INDEX.md", "guides/SILENT-FAILURES.md")
THREAD_EVIDENCE_KEYS = {
    "taskId", "taskUrl", "updatedAt", "repositoryIdentity", "patternKey", "observation",
}
THREAD_ACTION_KEYS = {
    "id", "source", "summary", "confidence", "resolutionDisposition", "evidenceUrls",
    "evidenceDate", "targetSha", "exactCurrentTarget", "paths", "changeKind",
    "regressionTest", "canonicalSourcePaths", "generatedFromCanonicalSource",
    "diagnostics", "patternKey", "taskEvidence", "deterministicFailure",
    "threadReviewSchemaVersion", "threadReviewRepositoryIdentity",
    "threadReviewUnexpectedFields", *PROHIBITED_FLAGS,
}
ISO_TIMESTAMP = re.compile(r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$")


class CycleError(RuntimeError):
    pass


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now()).isoformat().replace("+00:00", "Z")


def atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: pathlib.Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CycleError(f"invalid JSON at {path}: {error}") from error


def git(repository: pathlib.Path, *arguments: str, check: bool = True) -> str:
    process = subprocess.run(["git", "-C", str(repository), *arguments], text=True,
                             capture_output=True, check=False)
    if check and process.returncode:
        raise CycleError((process.stderr or process.stdout).strip() or
                         f"git {' '.join(arguments)} failed")
    return process.stdout.strip()


def acquire_lock(lock_path: pathlib.Path, run_id: str) -> dict[str, Any]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    recovered = None
    if lock_path.exists():
        old = read_json(lock_path, {})
        try:
            created = dt.datetime.fromisoformat(old["createdAt"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as error:
            raise CycleError(f"invalid active lock {lock_path}: {error}") from error
        age = now() - created
        if age <= dt.timedelta(hours=24):
            raise CycleError(f"weekly cycle is locked by run {old.get('runId', '?')}")
        recovered = old
        lock_path.unlink()
    value = {"schemaVersion": 1, "runId": run_id, "createdAt": iso(),
             "recoveredLock": recovered}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(lock_path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
    return value


def open_automation_pr(repository: pathlib.Path) -> dict[str, Any] | None:
    process = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json",
         "number,title,headRefName,url,isDraft"],
        cwd=repository, text=True, capture_output=True, check=False,
    )
    if process.returncode:
        raise CycleError((process.stderr or process.stdout).strip() or "cannot query open PRs")
    for item in json.loads(process.stdout):
        if item.get("headRefName", "").startswith("codex/weekly-improvement-"):
            return item
    return None


def prepare(args: argparse.Namespace) -> int:
    if not SAFE_RUN_ID.fullmatch(args.run_id):
        raise CycleError("run id must be collision-safe ASCII without path separators")
    repository = args.repository.resolve()
    artifact_root = args.artifact_root.resolve()
    run_root = artifact_root / "weekly-improvements" / args.run_id
    lock_path = artifact_root / "state/weekly-improvement.lock.json"
    if run_root.exists():
        raise CycleError(f"refusing to reuse run directory {run_root}")
    lock = acquire_lock(lock_path, args.run_id)
    worktree = (args.worktree_root or artifact_root / "worktrees").resolve() / args.run_id
    branch = f"codex/weekly-improvement-{args.run_id.lower()}"
    try:
        if not args.skip_remote_check:
            existing = open_automation_pr(repository)
            if existing:
                raise CycleError(f"automation PR already open: {existing['url']}")
        git(repository, "fetch", "origin", "main")
        base_sha = git(repository, "rev-parse", "origin/main^{commit}")
        if worktree.exists():
            raise CycleError(f"worktree path already exists: {worktree}")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git(repository, "worktree", "add", "-b", branch, str(worktree), "origin/main")
        for name in ("logs", "results", "probe-artifacts"):
            (run_root / name).mkdir(parents=True, exist_ok=True)
        manifest = {
            "schemaVersion": 1,
            "runId": args.run_id,
            "createdAt": iso(),
            "repository": str(repository),
            "repositoryIdentity": git(repository, "config", "--get", "remote.origin.url"),
            "baseSha": base_sha,
            "branch": branch,
            "worktree": str(worktree),
            "lockPath": str(lock_path),
            "recoveredLock": lock.get("recoveredLock"),
            "status": "prepared",
        }
        atomic_json(run_root / "run.json", manifest)
        lock.update({"runRoot": str(run_root), "worktree": str(worktree),
                     "branch": branch, "baseSha": base_sha})
        atomic_json(lock_path, lock)
    except Exception:
        if worktree.exists():
            git(repository, "worktree", "remove", "--force", str(worktree), check=False)
        if lock_path.exists() and read_json(lock_path, {}).get("runId") == args.run_id:
            lock_path.unlink()
        raise
    print(json.dumps({"runRoot": str(run_root), "worktree": str(worktree),
                      "branch": branch, "baseSha": base_sha}, sort_keys=True))
    return 0


def safe_path(path: str) -> bool:
    if not path or ".." in pathlib.PurePosixPath(path).parts:
        return False
    if any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return False
    return any(path.startswith(root) for root in ALLOWED_ROOTS)


def deterministic_failure_is_recorded(
    value: Any, run_root: pathlib.Path, base_sha: str,
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "validator", "artifact", "targetSha", "failed",
    }:
        return False
    validator = value.get("validator")
    artifact = value.get("artifact")
    if (
        not isinstance(validator, str)
        or not validator.startswith("./scripts/")
        or "\n" in validator
        or not isinstance(artifact, str)
    ):
        return False
    relative = pathlib.PurePosixPath(artifact)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        return False
    evidence_path = (run_root / pathlib.Path(*relative.parts)).resolve()
    try:
        evidence_path.relative_to(run_root.resolve())
    except ValueError:
        return False
    return (
        value.get("targetSha") == base_sha
        and value.get("failed") is True
        and evidence_path.is_file()
    )


def thread_evidence_status(
    action: dict[str, Any], repository_identity: str,
) -> tuple[bool, int]:
    evidence = action.get("taskEvidence")
    pattern_key = action.get("patternKey")
    if not isinstance(evidence, list) or not isinstance(pattern_key, str) or not pattern_key:
        return False, 0
    task_ids = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != THREAD_EVIDENCE_KEYS:
            return False, 0
        if (
            not isinstance(item.get("taskId"), str)
            or not item["taskId"]
            or not isinstance(item.get("taskUrl"), str)
            or not item["taskUrl"].startswith(("https://", "http://"))
            or not ISO_TIMESTAMP.fullmatch(str(item.get("updatedAt", "")))
            or item.get("repositoryIdentity") != repository_identity
            or item.get("patternKey") != pattern_key
            or not isinstance(item.get("observation"), str)
            or not item["observation"].strip()
        ):
            return False, 0
        task_ids.add(item["taskId"])
    return bool(task_ids), len(task_ids)


def eligibility(
    action: dict[str, Any], manifest: dict[str, Any], run_root: pathlib.Path,
) -> list[str]:
    blockers = []
    base_sha = manifest["baseSha"]
    confidence = action.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or confidence < 0.90:
        blockers.append("confidence-below-0.90")
    disposition = action.get("resolutionDisposition")
    if disposition not in DISPOSITIONS or disposition == "unknown":
        blockers.append("resolution-disposition-not-actionable")
    evidence = action.get("evidenceUrls")
    if not isinstance(evidence, list) or not evidence or not all(
        isinstance(url, str) and url.startswith(("https://", "http://")) for url in evidence
    ):
        blockers.append("missing-evidence-urls")
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", str(action.get("evidenceDate", ""))):
        blockers.append("missing-evidence-date")
    if action.get("targetSha") != base_sha:
        blockers.append("target-is-not-current")
    if action.get("exactCurrentTarget") is not True:
        blockers.append("exact-current-target-not-confirmed")
    paths = action.get("paths")
    if not isinstance(paths, list) or not paths or not all(
        isinstance(path, str) and safe_path(path) for path in paths
    ):
        blockers.append("path-outside-allowed-roots")
    change_kind = action.get("changeKind")
    if change_kind not in {"docs", "code", "tooling"}:
        blockers.append("missing-or-invalid-change-kind")
    if change_kind in {"code", "tooling"} and not action.get("regressionTest"):
        blockers.append("missing-regression-test")
    if action.get("source") == "thread-retrospective":
        if action.get("threadReviewSchemaVersion") != 2:
            blockers.append("invalid-thread-review-schema")
        if action.get("threadReviewRepositoryIdentity") != manifest.get("repositoryIdentity"):
            blockers.append("thread-review-repository-mismatch")
        if action.get("threadReviewUnexpectedFields"):
            blockers.append("untrusted-thread-review-fields")
        if set(action) - THREAD_ACTION_KEYS:
            blockers.append("untrusted-thread-action-fields")
        evidence_valid, distinct_task_count = thread_evidence_status(
            action, str(manifest.get("repositoryIdentity", ""))
        )
        deterministic = deterministic_failure_is_recorded(
            action.get("deterministicFailure"), run_root, base_sha
        )
        if not evidence_valid:
            blockers.append("invalid-structured-task-evidence")
        if not evidence_valid or not (distinct_task_count >= 2 or deterministic):
            blockers.append("thread-pattern-not-corroborated")
    for flag in PROHIBITED_FLAGS:
        if action.get(flag) is not False:
            blockers.append(f"prohibited-{flag}")
    generated_paths = [path for path in paths or [] if path.startswith(GENERATED_OUTPUTS)]
    if generated_paths:
        sources = action.get("canonicalSourcePaths")
        if action.get("generatedFromCanonicalSource") is not True or not isinstance(sources, list):
            blockers.append("generated-output-lacks-canonical-source")
        elif not sources or not all(
            isinstance(path, str) and path in paths and safe_path(path)
            and not path.startswith(GENERATED_OUTPUTS) for path in sources
        ):
            blockers.append("invalid-canonical-source-paths")
    if action.get("diagnostics"):
        blockers.append("ambiguous-diagnostics")
    return blockers


def action_candidates(
    run_root: pathlib.Path, manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []
    defects = read_json(run_root / "defects.json", {}) or {}
    for reference in defects.get("references", []):
        if reference.get("verdict") != "STATE-CHANGED":
            continue
        triage = reference.get("triage") or {}
        candidates.append({
            "id": f"defect:{reference.get('ref', '?')}",
            "source": "defect-report",
            "summary": triage.get("summary") or f"Review {reference.get('ref', 'defect')}",
            "confidence": triage.get("confidence", reference.get("confidence", 0)),
            "resolutionDisposition": triage.get("resolutionDisposition") or
                                     reference.get("resolutionDisposition") or "unknown",
            "evidenceUrls": triage.get("evidenceUrls") or
                            [reference.get("live", {}).get("url")],
            "evidenceDate": triage.get("evidenceDate"),
            "targetSha": triage.get("targetSha"),
            "exactCurrentTarget": triage.get("exactCurrentTarget", False),
            "paths": triage.get("paths", []),
            "changeKind": triage.get("changeKind", "docs"),
            "regressionTest": triage.get("regressionTest"),
            "canonicalSourcePaths": triage.get("canonicalSourcePaths"),
            "generatedFromCanonicalSource": triage.get("generatedFromCanonicalSource"),
            "diagnostics": reference.get("diagnostics", []),
            **{flag: triage.get(flag) for flag in PROHIBITED_FLAGS},
        })
    for filename, default_source in (
        ("thread-review.json", "thread-retrospective"),
        ("validation.json", "deterministic-validation"),
    ):
        payload = read_json(run_root / filename, {}) or {}
        for item in payload.get("actions", []):
            candidate = dict(item)
            # The evidence lane, not untrusted input, determines the source. This
            # prevents task text from bypassing the stricter retrospective gate.
            candidate["source"] = default_source
            if default_source == "thread-retrospective":
                candidate["threadReviewSchemaVersion"] = payload.get("schemaVersion")
                candidate["threadReviewRepositoryIdentity"] = payload.get(
                    "repositoryIdentity"
                )
                candidate["threadReviewUnexpectedFields"] = sorted(
                    set(payload) - {"schemaVersion", "repositoryIdentity", "actions"}
                )
            candidates.append(candidate)
    return candidates


def evaluate(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    manifest = read_json(run_root / "run.json")
    if not manifest:
        raise CycleError(f"missing run manifest in {run_root}")
    actions = []
    for number, candidate in enumerate(action_candidates(run_root, manifest), 1):
        item = dict(candidate)
        item.setdefault("id", f"action-{number:04d}")
        blockers = eligibility(item, manifest, run_root)
        item["automaticFixEligible"] = not blockers
        item["eligibilityBlockers"] = blockers
        actions.append(item)
    payload = {
        "schemaVersion": 1,
        "runId": manifest["runId"],
        "evaluatedAt": iso(),
        "summary": {"total": len(actions),
                    "eligible": sum(item["automaticFixEligible"] for item in actions),
                    "reportOnly": sum(not item["automaticFixEligible"] for item in actions)},
        "actions": actions,
    }
    atomic_json(run_root / "actions.json", payload)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


def changed_paths(worktree: pathlib.Path, base_sha: str) -> list[str]:
    committed = git(worktree, "diff", "--name-only", f"{base_sha}...HEAD").splitlines()
    working = git(worktree, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    paths = list(committed)
    for line in working:
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    disposable = ("Build/", "artifacts/", "probes/.build/")
    return sorted({path for path in paths if path and not path.startswith(disposable)})


def finalize(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    manifest = read_json(run_root / "run.json")
    if not manifest:
        raise CycleError(f"missing run manifest in {run_root}")
    worktree = pathlib.Path(manifest["worktree"])
    repository = pathlib.Path(manifest["repository"])
    lock_path = pathlib.Path(manifest["lockPath"])
    lock = read_json(lock_path, {})
    if lock.get("runId") != manifest["runId"]:
        raise CycleError("active lock belongs to another run; refusing to finalize")
    paths = changed_paths(worktree, manifest["baseSha"]) if worktree.exists() else []
    unsafe = [path for path in paths if not safe_path(path)]
    if unsafe:
        raise CycleError(f"refusing to finalize changes outside allowed roots: {unsafe}")
    if args.outcome in {"draft", "ready"} and not args.pr_url:
        raise CycleError(f"{args.outcome} outcome requires --pr-url")
    if args.outcome == "ready":
        pr = read_json(run_root / "pr.json", {}) or {}
        if pr.get("checksPassed") is not True or pr.get("mergeable") is not True:
            raise CycleError("ready outcome requires pr.json with checksPassed and mergeable true")
    actions = read_json(run_root / "actions.json", {}) or {}
    eligible = [item for item in actions.get("actions", [])
                if item.get("automaticFixEligible") is True]
    approved_paths = {path for item in eligible for path in item.get("paths", [])}
    unapproved = [path for path in paths if path not in approved_paths]
    if unapproved:
        raise CycleError(f"changed paths lack an eligible action: {unapproved}")
    if args.outcome in {"draft", "ready"} and (not paths or not eligible):
        raise CycleError(f"{args.outcome} outcome requires changed paths backed by eligible actions")
    state_path = args.state_path or run_root.parents[1] / "state/weekly-improvement.json"
    state = read_json(state_path, {"schemaVersion": 1, "runs": []})
    entry = {"runId": manifest["runId"], "finishedAt": iso(), "outcome": args.outcome,
             "baseSha": manifest["baseSha"], "branch": manifest["branch"],
             "prUrl": args.pr_url, "changedPaths": paths}
    state.setdefault("runs", []).append(entry)
    state["runs"] = state["runs"][-20:]
    state["lastRun"] = entry
    if args.outcome in {"no-change", "ready"}:
        state["lastSuccessfulRun"] = entry
    state["pending"] = None if args.outcome in {"no-change", "ready"} else entry
    if worktree.exists():
        for build in worktree.rglob("Build"):
            if build.is_dir():
                shutil.rmtree(build)
        git(repository, "worktree", "remove", "--force", str(worktree))
    if args.outcome in {"no-change", "blocked"}:
        git(repository, "branch", "-D", manifest["branch"], check=False)
    atomic_json(state_path, state)
    manifest.update(status=args.outcome, finishedAt=entry["finishedAt"], prUrl=args.pr_url)
    atomic_json(run_root / "run.json", manifest)
    lock_path.unlink(missing_ok=True)
    print(json.dumps(entry, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("cycle", choices=("weekly",))
    prepare_parser.add_argument("--run-id", required=True)
    prepare_parser.add_argument("--repository", type=pathlib.Path, default=ROOT)
    prepare_parser.add_argument("--artifact-root", type=pathlib.Path,
                                default=DEFAULT_ARTIFACT_ROOT)
    prepare_parser.add_argument("--worktree-root", type=pathlib.Path)
    prepare_parser.add_argument("--skip-remote-check", action="store_true",
                                help=argparse.SUPPRESS)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("run_root", type=pathlib.Path)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("run_root", type=pathlib.Path)
    finalize_parser.add_argument("--outcome", required=True,
                                 choices=("no-change", "blocked", "draft", "ready"))
    finalize_parser.add_argument("--pr-url")
    finalize_parser.add_argument("--state-path", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return {"prepare": prepare, "evaluate": evaluate, "finalize": finalize}[args.command](args)
    except (CycleError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"freshness cycle: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
