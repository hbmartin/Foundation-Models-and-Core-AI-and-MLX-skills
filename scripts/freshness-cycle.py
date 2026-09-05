#!/usr/bin/env python3
"""Prepare, evaluate, and finalize the repository's weekly improvement cycle."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from automation_policy import (
    ALLOWED_ROOTS,
    FORBIDDEN_COMPONENTS,
    GENERATED_OUTPUTS,
    PROTECTED_PATHS,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts/freshness"
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
DISPOSITIONS = {
    "fixed", "fixed-with-residual", "merged-unreleased", "closed-unfixed",
    "closed-unmerged", "superseded", "consolidated", "unknown",
}
PROHIBITED_FLAGS = (
    "dependencyChange", "workflowChange", "architectureChange", "securityPolicyChange",
    "betaBaselinePromotion", "interfaceCapturePromotion", "personalSkillChange",
    "crossRepositoryChange",
)
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
GENERATED_VALIDATORS = (
    (
        "current-state-blocks",
        (
            "notes/current-state.json",
            "notes/README.md",
            "notes/FRESHNESS-RUNBOOK.md",
            "notes/NEXT-BETA-CHECKLIST.md",
            "probes/README.md",
        ),
        (sys.executable, "scripts/current-state.py", "render", "--check"),
    ),
    (
        "indexes",
        (
            "guides/",
            "notes/synthesis/callout-classifications/",
            "notes/synthesis/SYMPTOM-TAXONOMY.md",
        ),
        (
            sys.executable,
            "-m",
            "unittest",
            "scripts.tests.test_repository_indexes.RepositoryIndexTests."
            "test_committed_indexes_match_clean_generation_and_links",
        ),
    ),
    (
        "skills",
        ("guides/", "skills/"),
        (
            sys.executable,
            "-m",
            "unittest",
            "scripts.tests.test_skills.CommittedSkillsTests."
            "test_committed_skills_match_clean_generation",
        ),
    ),
)
DETERMINISTIC_VALIDATORS = {
    "./scripts/current-state.py render --check": (
        sys.executable, "scripts/current-state.py", "render", "--check",
    ),
}
REGRESSION_TEST_ROOTS = ("scripts/tests/", "probes/Tests/", "tests/")


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


def git(
    repository: pathlib.Path, *arguments: str, check: bool = True, strip: bool = True,
) -> str:
    process = subprocess.run(["git", "-C", str(repository), *arguments], text=True,
                             capture_output=True, check=False)
    if check and process.returncode:
        raise CycleError((process.stderr or process.stdout).strip() or
                         f"git {' '.join(arguments)} failed")
    return process.stdout.strip() if strip else process.stdout


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


def path_matches(path: str, pattern: str) -> bool:
    return path.startswith(pattern) if pattern.endswith("/") else path == pattern


def generated_output(path: str) -> bool:
    return any(path_matches(path, pattern) for pattern in GENERATED_OUTPUTS)


def safe_path(path: str) -> bool:
    parsed = pathlib.PurePosixPath(path)
    if not path or parsed.is_absolute() or ".." in parsed.parts:
        return False
    if any(component in FORBIDDEN_COMPONENTS for component in parsed.parts):
        return False
    if any(path_matches(path, protected) for protected in PROTECTED_PATHS):
        return False
    return any(path.startswith(root) for root in ALLOWED_ROOTS)


def artifact_path(run_root: pathlib.Path, value: Any) -> pathlib.Path | None:
    if not isinstance(value, str):
        return None
    relative = pathlib.PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
        or relative.parts[0] != "results"
    ):
        return None
    resolved = (run_root / pathlib.Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(run_root.resolve())
    except ValueError:
        return None
    return resolved


def run_deterministic_validator(
    manifest: dict[str, Any], validator: str,
) -> subprocess.CompletedProcess[str] | None:
    command = DETERMINISTIC_VALIDATORS.get(validator)
    worktree_value = manifest.get("worktree")
    if command is None or not isinstance(worktree_value, str):
        return None
    worktree = pathlib.Path(worktree_value)
    if not worktree.is_dir():
        return None
    try:
        if (
            git(worktree, "rev-parse", "HEAD") != manifest.get("baseSha")
            or git(worktree, "status", "--porcelain", "--untracked-files=all")
        ):
            return None
    except CycleError:
        return None
    try:
        return subprocess.run(
            command, cwd=worktree, text=True, capture_output=True,
            timeout=300, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def validation_attestation(
    validator: str, target_sha: str, result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "validator": validator,
        "targetSha": target_sha,
        "exitCode": result.returncode,
        "stdoutSha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
        "stderrSha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
    }


def deterministic_failure_is_recorded(
    value: Any, run_root: pathlib.Path, manifest: dict[str, Any],
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "validator", "artifact", "targetSha", "failed",
    }:
        return False
    validator = value.get("validator")
    if (
        not isinstance(validator, str)
        or validator not in DETERMINISTIC_VALIDATORS
    ):
        return False
    evidence_path = artifact_path(run_root, value.get("artifact"))
    if evidence_path is None or not evidence_path.is_file():
        return False
    try:
        recorded = read_json(evidence_path)
    except CycleError:
        return False
    result = run_deterministic_validator(manifest, validator)
    if result is None or result.returncode == 0:
        return False
    expected = validation_attestation(validator, manifest["baseSha"], result)
    return (
        value.get("targetSha") == manifest["baseSha"]
        and value.get("failed") is True
        and recorded == expected
    )


def regression_test_is_valid(value: Any, manifest: dict[str, Any]) -> bool:
    if not isinstance(value, str):
        return False
    relative = pathlib.PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not any(value.startswith(root) for root in REGRESSION_TEST_ROOTS)
    ):
        return False
    root_value = manifest.get("worktree") or manifest.get("repository")
    if not isinstance(root_value, str):
        return False
    return (pathlib.Path(root_value) / pathlib.Path(*relative.parts)).is_file()


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
    if change_kind in {"code", "tooling"} and not regression_test_is_valid(
        action.get("regressionTest"), manifest
    ):
        blockers.append("missing-or-invalid-regression-test")
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
            action.get("deterministicFailure"), run_root, manifest
        )
        if not evidence_valid and not deterministic:
            blockers.append("invalid-structured-task-evidence")
        if distinct_task_count < 2 and not deterministic:
            blockers.append("thread-pattern-not-corroborated")
    for flag in PROHIBITED_FLAGS:
        if action.get(flag) is not False:
            blockers.append(f"prohibited-{flag}")
    generated_paths = [
        path for path in (paths if isinstance(paths, list) else [])
        if isinstance(path, str) and generated_output(path)
    ]
    generated_claim = (
        bool(generated_paths)
        or action.get("generatedFromCanonicalSource") is not None
        or action.get("canonicalSourcePaths") is not None
    )
    if generated_claim:
        sources = action.get("canonicalSourcePaths")
        if action.get("generatedFromCanonicalSource") is not True or not isinstance(sources, list):
            blockers.append("generated-output-lacks-canonical-source")
        elif not sources or not all(
            isinstance(path, str) and path in paths and safe_path(path)
            and not generated_output(path) for path in sources
        ):
            blockers.append("invalid-canonical-source-paths")
    if action.get("diagnostics"):
        blockers.append("ambiguous-diagnostics")
    return blockers


def malformed_candidate(source: str, filename: str, detail: str) -> dict[str, Any]:
    return {
        "id": f"malformed:{filename}",
        "source": source,
        "summary": f"Malformed {filename}",
        "diagnostics": [{"code": "invalid-input-shape", "message": detail}],
    }


def evidence_payload(run_root: pathlib.Path, filename: str) -> tuple[Any, str | None]:
    try:
        return read_json(run_root / filename), None
    except CycleError as error:
        return None, str(error)


def action_candidates(
    run_root: pathlib.Path, manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []
    defects, defects_error = evidence_payload(run_root, "defects.json")
    if defects_error:
        candidates.append(malformed_candidate("defect-report", "defects.json", defects_error))
        defects = {}
    elif defects is None:
        defects = {}
    elif not isinstance(defects, dict):
        candidates.append(malformed_candidate(
            "defect-report", "defects.json", "top level must be an object",
        ))
        defects = {}
    references = defects.get("references", [])
    if not isinstance(references, list):
        candidates.append(malformed_candidate(
            "defect-report", "defects.json", "references must be an array",
        ))
        references = []
    for index, reference in enumerate(references, 1):
        if not isinstance(reference, dict):
            candidates.append(malformed_candidate(
                "defect-report", f"defects.json:reference-{index}",
                "reference must be an object",
            ))
            continue
        if reference.get("verdict") != "STATE-CHANGED":
            continue
        triage = reference.get("triage") or {}
        if not isinstance(triage, dict):
            candidates.append(malformed_candidate(
                "defect-report", f"defects.json:reference-{index}",
                "triage must be an object",
            ))
            continue
        live_url = reference.get("liveUrl")
        candidates.append({
            "id": f"defect:{reference.get('ref', '?')}",
            "source": "defect-report",
            "summary": triage.get("summary") or f"Review {reference.get('ref', 'defect')}",
            "confidence": triage.get("confidence", reference.get("confidence", 0)),
            "resolutionDisposition": triage.get("resolutionDisposition") or
                                     reference.get("resolutionDisposition") or "unknown",
            "evidenceUrls": triage.get("evidenceUrls") or
                            ([live_url] if isinstance(live_url, str) else []),
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
        payload, payload_error = evidence_payload(run_root, filename)
        if payload_error:
            candidates.append(malformed_candidate(default_source, filename, payload_error))
            continue
        if payload is None:
            continue
        if not isinstance(payload, dict):
            candidates.append(malformed_candidate(
                default_source, filename, "top level must be an object",
            ))
            continue
        items = payload.get("actions", [])
        if not isinstance(items, list):
            candidates.append(malformed_candidate(
                default_source, filename, "actions must be an array",
            ))
            continue
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                candidates.append(malformed_candidate(
                    default_source, f"{filename}:action-{index}",
                    "action must be an object",
                ))
                continue
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
    paths = []
    committed = git(
        worktree, "diff", "--name-status", "--find-renames", "-z", f"{base_sha}...HEAD",
        strip=False,
    ).split("\0")
    index = 0
    while index < len(committed) and committed[index]:
        status = committed[index]
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        paths.extend(committed[index:index + path_count])
        index += path_count
    working = git(
        worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all", strip=False,
    ).split("\0")
    index = 0
    while index < len(working) and working[index]:
        entry = working[index]
        index += 1
        status = entry[:2]
        paths.append(entry[3:])
        if "R" in status or "C" in status:
            paths.append(working[index])
            index += 1
    disposable = ("Build/", "artifacts/", "probes/.build/")
    return sorted({path for path in paths if path and not path.startswith(disposable)})


def eligible_actions(run_root: pathlib.Path) -> tuple[list[dict[str, Any]], str | None]:
    try:
        payload = read_json(run_root / "actions.json", {}) or {}
    except CycleError as error:
        return [], str(error)
    if not isinstance(payload, dict) or not isinstance(payload.get("actions", []), list):
        return [], "actions.json must contain an actions array"
    items = payload.get("actions", [])
    if any(not isinstance(item, dict) for item in items):
        return [], "actions.json actions must be objects"
    return [item for item in items if item.get("automaticFixEligible") is True], None


def generated_source_closure(action: dict[str, Any], changed: set[str]) -> bool:
    sources = action.get("canonicalSourcePaths")
    return (
        action.get("generatedFromCanonicalSource") is True
        and isinstance(sources, list)
        and bool(sources)
        and all(isinstance(path, str) and path in changed for path in sources)
    )


def approved_changed_path(
    path: str, actions: list[dict[str, Any]], changed: set[str],
) -> bool:
    if generated_output(path):
        return any(generated_source_closure(action, changed) for action in actions)
    return any(
        isinstance(action.get("paths"), list) and path in action["paths"]
        for action in actions
    )


def generated_validation_failures(worktree: pathlib.Path, paths: list[str]) -> list[str]:
    failures = []
    for name, patterns, command in GENERATED_VALIDATORS:
        if not any(any(path_matches(path, pattern) for pattern in patterns) for path in paths):
            continue
        try:
            result = subprocess.run(
                command,
                cwd=worktree,
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            failures.append(f"{name}: {error}")
            continue
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            failures.append(f"{name}: {detail[0] if detail else f'exit {result.returncode}'}")
    return failures


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
    if args.outcome in {"draft", "ready"} and not args.pr_url:
        raise CycleError(f"{args.outcome} outcome requires --pr-url")
    if args.outcome == "ready":
        pr = read_json(run_root / "pr.json", {}) or {}
        if (
            not isinstance(pr, dict)
            or pr.get("checksPassed") is not True
            or pr.get("mergeable") is not True
        ):
            raise CycleError("ready outcome requires pr.json with checksPassed and mergeable true")
    eligible, actions_error = eligible_actions(run_root)
    changed = set(paths)
    unapproved = [
        path for path in paths if not approved_changed_path(path, eligible, changed)
    ]
    policy_violations = []
    if unsafe:
        policy_violations.append(f"changes outside allowed roots: {unsafe}")
    if actions_error:
        policy_violations.append(actions_error)
    if unapproved:
        policy_violations.append(f"changed paths lack an eligible action: {unapproved}")
    if policy_violations and args.outcome != "blocked":
        raise CycleError("refusing to finalize: " + "; ".join(policy_violations))
    if args.outcome == "no-change" and paths:
        raise CycleError("no-change outcome requires a clean worktree")
    if args.outcome in {"draft", "ready"} and (not paths or not eligible):
        raise CycleError(f"{args.outcome} outcome requires changed paths backed by eligible actions")
    generated_failures = (
        generated_validation_failures(worktree, paths)
        if worktree.exists() and args.outcome in {"draft", "ready"}
        else []
    )
    if generated_failures and args.outcome == "ready":
        raise CycleError(
            "ready outcome requires current generated outputs: " + "; ".join(generated_failures)
        )
    state_path = args.state_path or run_root.parents[1] / "state/weekly-improvement.json"
    state = read_json(state_path, {"schemaVersion": 1, "runs": []})
    entry = {"runId": manifest["runId"], "finishedAt": iso(), "outcome": args.outcome,
             "baseSha": manifest["baseSha"], "branch": manifest["branch"],
             "prUrl": args.pr_url, "changedPaths": paths}
    if policy_violations:
        entry["policyViolations"] = policy_violations
    if generated_failures:
        entry["generatedOutputFailures"] = generated_failures
    state.setdefault("runs", []).append(entry)
    state["runs"] = state["runs"][-20:]
    state["lastRun"] = entry
    successful = args.outcome in {"no-change", "ready"}
    # Record the accepted outcome before cleanup, but do not call it successful
    # until the worktree and disposable products are actually gone.
    state["pending"] = {**entry, "cleanupPending": True}
    atomic_json(state_path, state)
    manifest.update(status="cleanup-pending", finishedAt=entry["finishedAt"],
                    prUrl=args.pr_url)
    atomic_json(run_root / "run.json", manifest)
    if worktree.exists():
        try:
            for build in worktree.rglob("Build"):
                if build.is_dir():
                    shutil.rmtree(build)
            git(repository, "worktree", "remove", "--force", str(worktree))
        except (OSError, CycleError) as error:
            state["pending"] = {**entry, "cleanupPending": True, "cleanupError": str(error)}
            atomic_json(state_path, state)
            manifest.update(status="cleanup-failed", cleanupError=str(error))
            atomic_json(run_root / "run.json", manifest)
            raise
    if args.outcome in {"no-change", "blocked"}:
        git(repository, "branch", "-D", manifest["branch"], check=False)
    if successful:
        state["lastSuccessfulRun"] = entry
    state["pending"] = None if successful else entry
    atomic_json(state_path, state)
    manifest.update(status=args.outcome)
    manifest.pop("cleanupError", None)
    atomic_json(run_root / "run.json", manifest)
    lock_path.unlink(missing_ok=True)
    print(json.dumps(entry, sort_keys=True))
    return 0


def record_failure(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    manifest = read_json(run_root / "run.json")
    if not isinstance(manifest, dict):
        raise CycleError(f"missing run manifest in {run_root}")
    output = artifact_path(run_root, args.artifact)
    if output is None:
        raise CycleError("artifact must be a relative path under results/ inside the run root")
    result = run_deterministic_validator(manifest, args.validator)
    if result is None:
        raise CycleError("validator is not allowlisted or its worktree is unavailable")
    if result.returncode == 0:
        raise CycleError("validator passed; there is no deterministic failure to record")
    atomic_json(
        output,
        validation_attestation(args.validator, manifest["baseSha"], result),
    )
    print(json.dumps({"artifact": args.artifact, "exitCode": result.returncode}))
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
    record_parser = sub.add_parser("record-failure")
    record_parser.add_argument("run_root", type=pathlib.Path)
    record_parser.add_argument(
        "--validator", required=True, choices=tuple(DETERMINISTIC_VALIDATORS)
    )
    record_parser.add_argument("--artifact", required=True)
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
        return {
            "prepare": prepare,
            "evaluate": evaluate,
            "record-failure": record_failure,
            "finalize": finalize,
        }[args.command](args)
    except (CycleError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"freshness cycle: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
