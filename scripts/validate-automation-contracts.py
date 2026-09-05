#!/usr/bin/env python3
"""Validate checked-in Codex automation contracts and optionally installed copies."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import tomllib
from dataclasses import dataclass
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_ROOT = ROOT / "automations" / "contracts"
SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TEMP_PATH = re.compile(r"(?<![A-Za-z0-9_])/(?:private/)?tmp(?:/|\b)")
VOLATILE_COUNT = re.compile(r"\b\d+\s+(?:tests?|skips?|skipped|failures?)\b", re.IGNORECASE)
VOLATILE_BETA = re.compile(r"\b(?:Xcode|iOS|macOS)\s+\d+(?:\.\d+)?\s+beta\s+\d+\b", re.IGNORECASE)
STALE_COMMANDS = (
    "xcodebuild test -scheme Probes-Package",
    "cd probes && swift test",
)
REQUIRED_TOP_LEVEL = {
    "version": int,
    "id": str,
    "kind": str,
    "name": str,
    "prompt": str,
    "rrule": str,
    "cwds": list,
    "contract": dict,
}


@dataclass(frozen=True)
class Diagnostic:
    contract: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"contract": self.contract, "code": self.code, "message": self.message}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--contracts", type=pathlib.Path, default=DEFAULT_CONTRACT_ROOT)
    parser.add_argument(
        "--installed-root",
        type=pathlib.Path,
        help="also compare each contract with <root>/<id>/automation.toml",
    )
    parser.add_argument(
        "--installed",
        action="store_true",
        help="compare with CODEX_HOME/automations (or ~/.codex/automations)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def load_toml(path: pathlib.Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle), None
    except (OSError, tomllib.TOMLDecodeError) as error:
        return None, str(error)


def validate_contract(path: pathlib.Path, data: dict[str, Any]) -> list[Diagnostic]:
    label = path.name
    diagnostics: list[Diagnostic] = []

    for key, expected_type in REQUIRED_TOP_LEVEL.items():
        value = data.get(key)
        if not isinstance(value, expected_type) or isinstance(value, bool):
            diagnostics.append(
                Diagnostic(label, "invalid-field", f"{key} must be {expected_type.__name__}")
            )

    if diagnostics:
        return diagnostics

    identifier = data["id"]
    prompt = data["prompt"]
    policy = data["contract"]
    if not SAFE_IDENTIFIER.fullmatch(identifier):
        diagnostics.append(Diagnostic(label, "invalid-id", f"invalid id: {identifier!r}"))
    if path.stem != identifier:
        diagnostics.append(
            Diagnostic(label, "filename-id-mismatch", f"filename must be {identifier}.toml")
        )
    schema_version = policy.get("schema_version")
    if data["version"] != 1 or schema_version not in {1, 2}:
        diagnostics.append(Diagnostic(label, "unsupported-version",
                                      "automation version must be 1 and contract schema must be 1 or 2"))
    if data["kind"] != "cron":
        diagnostics.append(Diagnostic(label, "invalid-kind", "kind must be cron"))
    if not re.fullmatch(r"RRULE:FREQ=(?:DAILY|WEEKLY)(?:;[A-Z]+=[A-Z0-9,-]+)+", data["rrule"]):
        diagnostics.append(Diagnostic(label, "invalid-rrule", f"unsupported schedule: {data['rrule']}"))
    if data["cwds"] != ["."]:
        diagnostics.append(
            Diagnostic(label, "nonportable-cwd", "cwds must be the repository-relative ['.']")
        )

    mutation_policy = policy.get("mutation_policy")
    allowed_paths = policy.get("allowed_paths")
    artifacts = policy.get("artifact_patterns")
    required_fragments = policy.get("required_prompt_fragments")
    if mutation_policy not in {"tracked-read-only", "bounded", "isolated-ready-pr"}:
        diagnostics.append(
            Diagnostic(
                label,
                "invalid-mutation-policy",
                "mutation_policy must be tracked-read-only, bounded, or isolated-ready-pr",
            )
        )
    if not isinstance(allowed_paths, list) or not all(isinstance(item, str) for item in allowed_paths):
        diagnostics.append(Diagnostic(label, "invalid-allowed-paths", "allowed_paths must be strings"))
        allowed_paths = []
    if mutation_policy == "tracked-read-only" and allowed_paths != ["artifacts/"]:
        diagnostics.append(
            Diagnostic(
                label,
                "tracked-write-risk",
                "tracked-read-only contracts may write only to artifacts/",
            )
        )
    if mutation_policy == "bounded" and not allowed_paths:
        diagnostics.append(
            Diagnostic(label, "unbounded-mutation", "bounded contracts must name allowed paths")
        )
    if mutation_policy == "isolated-ready-pr":
        required_roots = {"guides/", "notes/", "probes/", "scripts/", "skills/", "automations/"}
        if set(allowed_paths) != required_roots:
            diagnostics.append(
                Diagnostic(label, "invalid-ready-pr-roots",
                           f"isolated-ready-pr allowed_paths must equal {sorted(required_roots)!r}")
            )
        forbidden_paths = policy.get("forbidden_paths")
        if not isinstance(forbidden_paths, list) or not all(
            isinstance(item, str) for item in forbidden_paths
        ):
            diagnostics.append(
                Diagnostic(label, "invalid-forbidden-paths",
                           "isolated-ready-pr contracts must name forbidden_paths")
            )
        required_boundaries = (
            "temporary worktree", "draft pull request", "mark it ready", "Never merge",
            "never rebase", "never force-push", "personal skill",
        )
        for fragment in required_boundaries:
            if fragment not in prompt:
                diagnostics.append(
                    Diagnostic(label, "missing-ready-pr-boundary",
                               f"prompt must contain {fragment!r}")
                )
    for allowed_path in allowed_paths:
        if allowed_path.startswith("/") or ".." in pathlib.PurePosixPath(allowed_path).parts:
            diagnostics.append(
                Diagnostic(label, "unsafe-allowed-path", f"allowed path must be repository-relative: {allowed_path}")
            )

    if not isinstance(artifacts, list) or not artifacts or not all(isinstance(item, str) for item in artifacts):
        diagnostics.append(
            Diagnostic(label, "missing-artifact", "artifact_patterns must contain at least one string")
        )
        artifacts = []
    for artifact in artifacts:
        if not artifact.startswith("artifacts/freshness/") or artifact.startswith("/"):
            diagnostics.append(
                Diagnostic(label, "unsafe-artifact", f"artifact must be under artifacts/freshness/: {artifact}")
            )
        stable_prefix = artifact.split("<", 1)[0].rstrip("/-")
        if stable_prefix not in prompt:
            diagnostics.append(
                Diagnostic(label, "artifact-not-in-prompt", f"prompt must name {stable_prefix}")
            )

    if not isinstance(required_fragments, list) or not all(
        isinstance(item, str) and item for item in required_fragments
    ):
        diagnostics.append(
            Diagnostic(label, "invalid-required-fragments", "required_prompt_fragments must be strings")
        )
        required_fragments = []
    for fragment in required_fragments:
        if fragment not in prompt:
            diagnostics.append(
                Diagnostic(label, "missing-prompt-fragment", f"prompt must contain {fragment!r}")
            )

    if TEMP_PATH.search(prompt):
        diagnostics.append(Diagnostic(label, "ephemeral-output", "prompt must not use /tmp"))
    if VOLATILE_COUNT.search(prompt) or VOLATILE_BETA.search(prompt):
        diagnostics.append(
            Diagnostic(label, "volatile-baseline", "prompt must defer volatile counts and beta versions to repository docs")
        )
    for stale_command in STALE_COMMANDS:
        if stale_command in prompt:
            diagnostics.append(
                Diagnostic(label, "noncanonical-command", f"replace stale command: {stale_command}")
            )
    if mutation_policy != "isolated-ready-pr" and (
        "Do not" not in prompt or "commit" not in prompt or "push" not in prompt
    ):
        diagnostics.append(
            Diagnostic(label, "missing-mutation-boundary", "prompt must explicitly prohibit commits and pushes")
        )
    if "continue with the remaining independent checks" not in prompt:
        diagnostics.append(
            Diagnostic(label, "missing-partial-failure-policy", "prompt must continue independent checks after a blocker")
        )

    return diagnostics


def validate_installed(
    contract_path: pathlib.Path,
    contract: dict[str, Any],
    installed_root: pathlib.Path,
) -> list[Diagnostic]:
    label = contract_path.name
    installed_path = installed_root / contract["id"] / "automation.toml"
    installed, error = load_toml(installed_path)
    if error or installed is None:
        return [Diagnostic(label, "installed-missing", f"cannot read {installed_path}: {error}")]

    diagnostics: list[Diagnostic] = []
    for key in ("version", "id", "kind", "name", "prompt", "rrule"):
        if installed.get(key) != contract[key]:
            diagnostics.append(
                Diagnostic(label, "installed-drift", f"installed {key} differs from the contract")
            )

    expected_cwds = [str((ROOT / item).resolve()) for item in contract["cwds"]]
    if installed.get("cwds") != expected_cwds:
        diagnostics.append(
            Diagnostic(
                label,
                "installed-drift",
                f"installed cwds must equal {expected_cwds!r}",
            )
        )
    return diagnostics


def main() -> int:
    arguments = parse_arguments()
    paths = sorted(arguments.contracts.glob("*.toml"))
    diagnostics: list[Diagnostic] = []
    loaded: list[tuple[pathlib.Path, dict[str, Any]]] = []

    if not paths:
        diagnostics.append(
            Diagnostic(str(arguments.contracts), "no-contracts", "no .toml contracts found")
        )
    for path in paths:
        data, error = load_toml(path)
        if error or data is None:
            diagnostics.append(Diagnostic(path.name, "invalid-toml", error or "unknown error"))
            continue
        diagnostics.extend(validate_contract(path, data))
        loaded.append((path, data))

    identifiers = [data.get("id") for _, data in loaded]
    for identifier in sorted({item for item in identifiers if identifiers.count(item) > 1}):
        diagnostics.append(Diagnostic(str(identifier), "duplicate-id", "automation id is not unique"))

    if arguments.installed and arguments.installed_root:
        diagnostics.append(
            Diagnostic("arguments", "conflicting-installed-options",
                       "use --installed or --installed-root, not both")
        )
    installed_root = arguments.installed_root
    if arguments.installed and installed_root is None:
        codex_home = os.environ.get("CODEX_HOME")
        installed_root = pathlib.Path(codex_home).expanduser() if codex_home else pathlib.Path.home() / ".codex"
        installed_root = installed_root / "automations"
    if installed_root:
        for path, data in loaded:
            if not validate_contract(path, data):
                diagnostics.extend(validate_installed(path, data, installed_root))

    payload = {
        "schemaVersion": 1,
        "valid": not diagnostics,
        "contracts": len(paths),
        "diagnostics": [item.as_dict() for item in diagnostics],
    }
    if arguments.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif diagnostics:
        for item in diagnostics:
            print(f"{item.contract}: {item.code}: {item.message}", file=sys.stderr)
    else:
        suffix = " and installed copies" if installed_root else ""
        print(f"Validated {len(paths)} automation contracts{suffix}.")
    return 0 if not diagnostics else 1


if __name__ == "__main__":
    raise SystemExit(main())
