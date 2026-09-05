#!/usr/bin/env python3
"""Collect, validate, and render the corpus's canonical current-state manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "notes/current-state.json"
TARGETS = {
    "notes": ROOT / "notes/README.md",
    "runbook": ROOT / "notes/FRESHNESS-RUNBOOK.md",
    "next-beta": ROOT / "notes/NEXT-BETA-CHECKLIST.md",
    "probes": ROOT / "probes/README.md",
}
GENERATED_CHECKS = {
    "currentStateBlocks": (
        "./scripts/current-state.py render --check",
        (sys.executable, "scripts/current-state.py", "render", "--check"),
    ),
    "indexes": (
        "python3 -m unittest scripts.tests.test_repository_indexes."
        "RepositoryIndexTests.test_committed_indexes_match_clean_generation_and_links",
        (
            sys.executable,
            "-m",
            "unittest",
            "scripts.tests.test_repository_indexes.RepositoryIndexTests."
            "test_committed_indexes_match_clean_generation_and_links",
        ),
    ),
    "skills": (
        "python3 -m unittest scripts.tests.test_skills."
        "CommittedSkillsTests.test_committed_skills_match_clean_generation",
        (
            sys.executable,
            "-m",
            "unittest",
            "scripts.tests.test_skills.CommittedSkillsTests."
            "test_committed_skills_match_clean_generation",
        ),
    ),
}


def require_iso_date(value: object, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"20\d\d-\d\d-\d\d", value):
        raise SystemExit(f"error: {label} must be an ISO date")
    try:
        dt.date.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(f"error: {label} must be an ISO date: {error}") from error


def atomic_text(path: pathlib.Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = path.stat().st_mode if path.exists() else None
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(contents)
        if existing_mode is not None:
            os.chmod(temporary, existing_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_manifest(path: pathlib.Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: cannot read current-state manifest: {error}")
    required = {"schemaVersion", "asOf", "corpus", "generatedOutputs", "environment",
                "pendingEvent", "probeBaselines", "verification"}
    if (
        not isinstance(value, dict)
        or value.get("schemaVersion") != 1
        or not required.issubset(value)
    ):
        raise SystemExit("error: current-state manifest is not schema version 1")
    require_iso_date(value["asOf"], "current-state asOf")

    def require_object(container: dict, key: str, fields: set[str]) -> dict:
        item = container.get(key)
        if not isinstance(item, dict) or not fields.issubset(item):
            raise SystemExit(
                f"error: current-state {key!r} must contain {sorted(fields)!r}"
            )
        return item

    corpus = require_object(
        value, "corpus",
        {"parts", "referenceGuides", "guideMarkdownFiles", "callouts", "symbols",
         "generatedSkills", "externalLinks"},
    )
    counts = [corpus[key] for key in (
        "parts", "referenceGuides", "guideMarkdownFiles", "symbols", "generatedSkills",
        "externalLinks",
    )]
    callouts = require_object(corpus, "callouts", {"total", "concreteSilentFailures"})
    counts.extend(callouts.values())
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts):
        raise SystemExit("error: current-state corpus counts must be non-negative integers")

    generated = value["generatedOutputs"]
    if not isinstance(generated, dict) or set(generated) != {
        "currentStateBlocks", "indexes", "skills",
    }:
        raise SystemExit("error: current-state generatedOutputs has an invalid shape")
    for name, output in generated.items():
        expected_command = GENERATED_CHECKS[name][0]
        if (
            not isinstance(output, dict)
            or set(output) != {"status", "checkedAt", "checkCommand"}
            or output["status"] not in {"current", "stale", "unknown"}
            or output["checkCommand"] != expected_command
        ):
            raise SystemExit(f"error: generated output {name!r} has invalid status metadata")
        require_iso_date(output["checkedAt"], f"generated output {name!r} checkedAt")

    environment = require_object(value, "environment", {"installed", "latestObserved"})
    installed = require_object(
        environment, "installed", {"os", "xcode", "sdks", "simulatorRuntimes", "fm"}
    )
    require_object(installed, "os", {"name", "version", "build"})
    installed_xcode = require_object(installed, "xcode", {"path", "version", "build"})
    if any(
        not isinstance(installed_xcode[field], str) or not installed_xcode[field]
        for field in ("path", "version", "build")
    ):
        raise SystemExit("error: current-state installed xcode metadata is invalid")
    sdks = require_object(installed, "sdks", {"macosx", "iphoneos"})
    require_object(sdks, "macosx", {"version", "build"})
    require_object(sdks, "iphoneos", {"version", "build"})
    installed_fm = require_object(
        installed, "fm", {"path", "version", "build", "exception"}
    )
    if (
        not isinstance(installed_fm["path"], str)
        or not installed_fm["path"]
        or not isinstance(installed_fm["build"], str)
        or not installed_fm["build"]
        or installed_fm["version"] is not None
        and (not isinstance(installed_fm["version"], str) or not installed_fm["version"])
        or not isinstance(installed_fm["exception"], str)
        or installed_fm["version"] is None and not installed_fm["exception"]
    ):
        raise SystemExit("error: current-state installed fm metadata is invalid")
    runtimes = installed["simulatorRuntimes"]
    if not isinstance(runtimes, list) or any(
        not isinstance(item, dict) or not {"name", "version", "build"}.issubset(item)
        for item in runtimes
    ):
        raise SystemExit("error: current-state simulatorRuntimes must be a runtime array")
    latest = require_object(
        environment, "latestObserved",
        {"xcode", "ios", "macos", "sdks", "simulatorRuntimes", "fm"},
    )
    for name in ("xcode", "ios", "macos"):
        release = require_object(latest, name, {"version", "build", "released", "sourceUrl"})
        require_iso_date(
            release["released"], f"current-state latestObserved {name!r} release date"
        )
        if not str(release["sourceUrl"]).startswith(("https://", "http://")):
            raise SystemExit(f"error: current-state latestObserved {name!r} lacks dated source evidence")
    latest_sdks = require_object(latest, "sdks", {"macosx", "iphoneos"})
    for name in ("macosx", "iphoneos"):
        sdk_release = require_object(
            latest_sdks, name,
            {"version", "build", "released", "sourceUrl", "exception"},
        )
        require_iso_date(
            sdk_release["released"], f"current-state latestObserved SDK {name!r} release date"
        )
        if (
            not isinstance(sdk_release["version"], str)
            or not sdk_release["version"]
            or sdk_release["build"] is not None
            and (not isinstance(sdk_release["build"], str) or not sdk_release["build"])
            or not isinstance(sdk_release["exception"], str)
            or sdk_release["build"] is None and not sdk_release["exception"]
            or not str(sdk_release["sourceUrl"]).startswith(("https://", "http://"))
        ):
            raise SystemExit(f"error: current-state latestObserved SDK {name!r} is invalid")
    runtime_releases = latest["simulatorRuntimes"]
    if not isinstance(runtime_releases, list) or not runtime_releases:
        raise SystemExit("error: current-state latestObserved simulatorRuntimes must not be empty")
    for release in runtime_releases:
        if not isinstance(release, dict) or not {
            "name", "version", "build", "released", "sourceUrl",
        }.issubset(release):
            raise SystemExit("error: current-state latestObserved runtime is invalid")
        require_iso_date(release["released"], "current-state latestObserved runtime release date")
        if not str(release["sourceUrl"]).startswith(("https://", "http://")):
            raise SystemExit("error: current-state latestObserved runtime lacks source evidence")
    latest_fm = require_object(
        latest, "fm", {"version", "build", "released", "sourceUrl", "exception"}
    )
    require_iso_date(latest_fm["released"], "current-state latestObserved fm release date")
    if (
        latest_fm["version"] is not None
        and (not isinstance(latest_fm["version"], str) or not latest_fm["version"])
        or not isinstance(latest_fm["build"], str)
        or not latest_fm["build"]
        or not isinstance(latest_fm["exception"], str)
        or latest_fm["version"] is None and not latest_fm["exception"]
        or not str(latest_fm["sourceUrl"]).startswith(("https://", "http://"))
    ):
        raise SystemExit("error: current-state latestObserved fm is invalid")

    pending = require_object(value, "pendingEvent", {"value", "reasons"})
    if not isinstance(pending["value"], bool) or not isinstance(pending["reasons"], list) or not all(
        isinstance(reason, str) and reason.strip() for reason in pending["reasons"]
    ):
        raise SystemExit("error: current-state pendingEvent must contain a boolean and reasons")
    if pending["value"] != bool(pending["reasons"]):
        raise SystemExit("error: current-state pendingEvent value and reasons disagree")

    if not isinstance(value["probeBaselines"], dict) or not value["probeBaselines"]:
        raise SystemExit("error: current-state probeBaselines must be a non-empty object")
    for key, baseline in value["probeBaselines"].items():
        topology = {"hostingMode", "platform", "osVersion", "osBuild", "xcodeVersion",
                    "xcodeBuild", "destination", "device", "tests", "skipped", "failures",
                    "exceptions"}
        if not isinstance(baseline, dict) or not topology.issubset(baseline):
            raise SystemExit(f"error: probe baseline {key!r} lacks a complete topology")
        if any(not isinstance(baseline[field], str) or not baseline[field].strip()
               for field in topology - {"tests", "skipped", "failures"}):
            raise SystemExit(f"error: probe baseline {key!r} has empty topology fields")
        if any(isinstance(baseline[field], bool) or not isinstance(baseline[field], int)
               or baseline[field] < 0 for field in ("tests", "skipped", "failures")):
            raise SystemExit(f"error: probe baseline {key!r} has invalid result counts")

    verification = require_object(
        value, "verification",
        {"snippetFences", "statusCounts", "unclassified", "errors", "blocker", "lastFullRun"},
    )
    status_counts = verification["statusCounts"]
    if not isinstance(status_counts, dict) or any(
        not isinstance(name, str) or isinstance(count, bool) or not isinstance(count, int) or count < 0
        for name, count in status_counts.items()
    ):
        raise SystemExit("error: current-state verification statusCounts are invalid")
    if any(isinstance(verification[field], bool) or not isinstance(verification[field], int)
           or verification[field] < 0 for field in ("snippetFences", "unclassified", "errors")):
        raise SystemExit("error: current-state verification totals must be non-negative integers")
    if sum(status_counts.values()) != verification["snippetFences"]:
        raise SystemExit("error: current-state snippet status counts do not equal snippetFences")
    if not isinstance(verification["blocker"], str):
        raise SystemExit("error: current-state verification must include blocker text")
    require_iso_date(
        verification["lastFullRun"], "current-state verification lastFullRun"
    )
    if "collection" in value:
        collection = require_object(
            value, "collection", {"complete", "blockers", "observedAt"}
        )
        if (
            not isinstance(collection["complete"], bool)
            or not isinstance(collection["blockers"], list)
            or not all(isinstance(item, str) and item for item in collection["blockers"])
            or collection["complete"] != (not collection["blockers"])
            or not isinstance(collection["observedAt"], str)
        ):
            raise SystemExit("error: current-state collection status is invalid")
        try:
            dt.datetime.fromisoformat(collection["observedAt"].replace("Z", "+00:00"))
        except ValueError as error:
            raise SystemExit(
                f"error: current-state collection observedAt is invalid: {error}"
            ) from error
    return value


def run(*command: str, env: dict | None = None) -> tuple[str, str | None]:
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return "", str(error)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return "", detail[0] if detail else f"exit {result.returncode}"
    return result.stdout.strip(), None


def is_tracked(path: pathlib.Path) -> bool:
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", str(relative)],
        text=True, capture_output=True, check=False,
    )
    return result.returncode == 0


def corpus_state() -> dict:
    process = subprocess.run(
        [sys.executable, str(ROOT / "scripts/extract-callouts.py"), str(ROOT / "guides")],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    callouts = [line.split("\t") for line in process.stdout.splitlines() if line]
    concrete = 0
    for path in (ROOT / "notes/synthesis/callout-classifications").glob("*.tsv"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and line.split("\t")[-2] != "caution-note":
                concrete += 1
    api = (ROOT / "guides/API-INDEX.md").read_text(encoding="utf-8")
    symbol_match = re.search(r"\*\*(\d+) symbols referenced", api)
    links = set()
    for path in (ROOT / "guides").rglob("*.md"):
        links.update(re.findall(r"https?://[^\s)>]+", path.read_text(encoding="utf-8")))
    return {
        "parts": len(list((ROOT / "guides").glob("part-*"))),
        "referenceGuides": len(list((ROOT / "guides").glob("part-*/references/*.md"))),
        "guideMarkdownFiles": len(list((ROOT / "guides").rglob("*.md"))),
        "callouts": {"total": len(callouts), "concreteSilentFailures": concrete},
        "symbols": int(symbol_match.group(1)) if symbol_match else 0,
        "generatedSkills": len([p for p in (ROOT / "skills").iterdir() if p.is_dir()]),
        "externalLinks": len(links),
    }


def installed_environment(previous: dict) -> tuple[dict, list[str]]:
    blockers = []

    def observe(label: str, *command: str, env: dict | None = None) -> str:
        output, error = run(*command, env=env)
        if error:
            blockers.append(f"{label}: {error}")
        return output

    sw_output = observe("operating-system", "sw_vers")
    sw = dict(
        line.split(":", 1) for line in sw_output.splitlines() if ":" in line
    )
    xcode_path = os.environ.get("DEVELOPER_DIR") or previous["xcode"]["path"]
    env = {**os.environ, "DEVELOPER_DIR": xcode_path}
    xcode_lines = observe("xcode", "xcodebuild", "-version", env=env).splitlines()

    def sdk(name: str) -> dict:
        prior = previous["sdks"][name]
        return {
            "version": observe(
                f"{name}-version", "xcrun", "--sdk", name, "--show-sdk-version", env=env
            ) or prior["version"],
            "build": observe(
                f"{name}-build", "xcrun", "--sdk", name,
                "--show-sdk-build-version", env=env
            ) or prior["build"],
        }

    runtimes = []
    runtime_output = observe(
        "simulator-runtimes", "xcrun", "simctl", "list", "runtimes", env=env
    )
    for line in runtime_output.splitlines():
        match = re.match(r"(iOS) ([0-9.]+) \([0-9.]+ - ([^)]+)\)", line.strip())
        if match:
            runtimes.append({"name": match.group(1), "version": match.group(2),
                             "build": match.group(3)})
    if not runtimes:
        if runtime_output:
            blockers.append(
                "simulator-runtimes: output contained no recognized iOS runtimes"
            )
        runtimes = previous["simulatorRuntimes"]
    discovered_fm_path = shutil.which("fm")
    fm_path = discovered_fm_path or previous["fm"]["path"]
    fm_version = previous["fm"]["version"]
    if not discovered_fm_path:
        blockers.append("fm-path: executable not found")
    value = {
        "os": {"name": sw.get("ProductName", "").strip() or previous["os"]["name"],
               "version": sw.get("ProductVersion", "").strip() or previous["os"]["version"],
               "build": sw.get("BuildVersion", "").strip() or previous["os"]["build"]},
        "xcode": {"path": xcode_path,
                  "version": xcode_lines[0].removeprefix("Xcode ") if xcode_lines
                  else previous["xcode"]["version"],
                  "build": xcode_lines[1].removeprefix("Build version ")
                  if len(xcode_lines) > 1 else previous["xcode"]["build"]},
        "sdks": {"macosx": sdk("macosx"), "iphoneos": sdk("iphoneos")},
        "simulatorRuntimes": runtimes,
        "fm": {
            "path": fm_path,
            "version": fm_version,
            "build": sw.get("BuildVersion", "").strip() or previous["fm"]["build"],
            "exception": "fm has no independent --version option; provenance is the owning macOS build.",
        },
    }
    return value, blockers


def snippet_state(previous: dict) -> dict:
    path = ROOT / "notes/snippet-verification/results.tsv"
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    status_index = header.index("status")
    counts = Counter(line.split("\t")[status_index] for line in lines[1:] if line)
    result = dict(previous)
    result["snippetFences"] = sum(counts.values())
    result["statusCounts"] = dict(sorted(counts.items()))
    result["unclassified"] = sum(value for key, value in counts.items()
                                 if key.startswith("UNCLASSIFIED") or key == "NEEDS-VERIFICATION")
    result["errors"] = sum(counts.get(key, 0) for key in
                           ("FAILED", "XFAIL-ERR", "MARKER-ERROR", "PARSE-ERROR"))
    return result


def generated_output_state() -> tuple[dict, list[str]]:
    checked_at = dt.datetime.now(dt.timezone.utc).date().isoformat()
    outputs = {}
    blockers = []
    for name, (display_command, command) in GENERATED_CHECKS.items():
        _, error = run(*command)
        outputs[name] = {
            "status": "stale" if error else "current",
            "checkedAt": checked_at,
            "checkCommand": display_command,
        }
        if error:
            blockers.append(f"generated-output-{name}: {error}")
    return outputs, blockers


def pending_reasons(installed: dict, latest: dict) -> list[str]:
    latest_runtime = max(
        (item for item in installed["simulatorRuntimes"] if item["name"] == "iOS"),
        key=lambda item: item["build"],
        default={"build": None},
    )
    comparisons = (
        ("Xcode", installed["xcode"]["build"], latest["xcode"]["build"]),
        ("macOS", installed["os"]["build"], latest["macos"]["build"]),
        ("iOS Simulator", latest_runtime.get("build"), latest["ios"]["build"]),
    )
    return [
        f"Installed {name} build {actual or 'unknown'} differs from observed build {expected}."
        for name, actual, expected in comparisons
        if actual != expected
    ]


def collect(manifest: dict) -> dict:
    value = json.loads(json.dumps(manifest))
    value["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    value["corpus"] = corpus_state()
    installed, blockers = installed_environment(
        manifest["environment"]["installed"]
    )
    value["environment"]["installed"] = installed
    generated_outputs, generated_blockers = generated_output_state()
    value["generatedOutputs"] = generated_outputs
    blockers.extend(generated_blockers)
    value["collection"] = {
        "complete": not blockers,
        "blockers": blockers,
        "observedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        .replace("+00:00", "Z"),
    }
    value["verification"] = snippet_state(manifest["verification"])
    installed = value["environment"]["installed"]
    latest = value["environment"]["latestObserved"]
    reasons = pending_reasons(installed, latest)
    value["pendingEvent"] = {"value": bool(reasons), "reasons": reasons}
    return value


def topology_line(key: str, baseline: dict) -> str:
    result = f"{baseline['tests']} tests / {baseline['skipped']} skipped / {baseline['failures']} failures"
    context = f"; contextSize={baseline['contextSize']}" if "contextSize" in baseline else ""
    return (f"- `{key}` — {baseline['hostingMode']}; {baseline['platform']} "
            f"{baseline['osVersion']} ({baseline['osBuild']}); Xcode {baseline['xcodeVersion']} "
            f"({baseline['xcodeBuild']}); destination `{baseline['destination']}`; "
            f"device `{baseline['device']}`; {result}{context}. {baseline['exceptions']}")


def render_blocks(state: dict) -> dict[str, str]:
    corpus = state["corpus"]
    installed = state["environment"]["installed"]
    latest = state["environment"]["latestObserved"]
    verification = state["verification"]
    generated = state["generatedOutputs"]
    statuses = ", ".join(f"{count} `{name}`" for name, count in verification["statusCounts"].items())
    reasons = " ".join(state["pendingEvent"]["reasons"]) or "No release-event refresh is pending."
    ios_runtimes = [item for item in installed["simulatorRuntimes"] if item["name"] == "iOS"]
    newest_ios_runtime = max(
        ios_runtimes, key=lambda item: item.get("build") or "", default={"build": "unknown"}
    )["build"]
    baselines = "\n".join(topology_line(key, value)
                          for key, value in state["probeBaselines"].items())
    output_status = ", ".join(
        f"{name}={details['status']} ({details['checkedAt']})"
        for name, details in generated.items()
    )
    fm_version = installed["fm"]["version"] or (
        f"no independent version; macOS build {installed['fm']['build']}"
    )
    return {
        "notes": (
            f"**As of {state['asOf']}**, the corpus has {corpus['referenceGuides']} reference guides "
            f"in {corpus['parts']} parts, {corpus['callouts']['total']} classified callouts "
            f"({corpus['callouts']['concreteSilentFailures']} concrete silent failures), "
            f"{corpus['symbols']} indexed symbols, and {corpus['generatedSkills']} generated skills.\n\n"
            f"Snippet verification covers {verification['snippetFences']} fences: {statuses}. "
            f"Blocker: {verification['blocker']}\n\n"
            f"Installed: macOS {installed['os']['version']} ({installed['os']['build']}), "
            f"Xcode {installed['xcode']['version']} ({installed['xcode']['build']}), and `fm` at "
            f"`{installed['fm']['path']}` ({fm_version}). Latest observed: Xcode {latest['xcode']['version']} "
            f"({latest['xcode']['build']}), iOS {latest['ios']['version']} ({latest['ios']['build']}), "
            f"and macOS {latest['macos']['version']} ({latest['macos']['build']}); SDK and runtime "
            f"versions are recorded separately in the manifest, and `fm` has no independent version "
            f"surface. Generated outputs: {output_status}. {reasons}"
        ),
        "runbook": (
            f"> **Current trigger, generated {state['asOf']}:** {reasons} The installed topology is "
            f"macOS {installed['os']['version']} build `{installed['os']['build']}`, Xcode "
            f"{installed['xcode']['version']} build `{installed['xcode']['build']}`, and the newest "
            f"installed iOS Simulator runtime is `{newest_ios_runtime}`. "
            "Use the topology-keyed baselines in `probes/README.md`; counts are not universal."
        ),
        "next-beta": (
            f"Current installed baseline: Xcode {installed['xcode']['version']} `{installed['xcode']['build']}`, "
            f"macOS {installed['os']['version']} `{installed['os']['build']}`, macOS SDK "
            f"`{installed['sdks']['macosx']['build']}`, iOS SDK `{installed['sdks']['iphoneos']['build']}`, "
            f"and newest iOS Simulator runtime `{newest_ios_runtime}`. "
            f"Latest observed releases are Xcode {latest['xcode']['version']} `{latest['xcode']['build']}`, "
            f"iOS {latest['ios']['version']} `{latest['ios']['build']}`, and macOS "
            f"{latest['macos']['version']} `{latest['macos']['build']}`. {reasons}"
        ),
        "probes": baselines,
    }


def replace_block(text: str, name: str, contents: str) -> str:
    start = f"<!-- current-state:{name}:start -->"
    end = f"<!-- current-state:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if len(pattern.findall(text)) != 1:
        raise SystemExit(f"error: expected exactly one generated {name!r} block")
    return pattern.sub(f"{start}\n{contents.rstrip()}\n{end}", text)


def render(state: dict, write: bool) -> int:
    stale = []
    for name, contents in render_blocks(state).items():
        path = TARGETS[name]
        original = path.read_text(encoding="utf-8")
        expected = replace_block(original, name, contents)
        if expected != original:
            stale.append(path)
            if write:
                atomic_text(path, expected)
    if stale and not write:
        for path in stale:
            try:
                label = path.relative_to(ROOT)
            except ValueError:
                label = path
            print(f"stale generated current-state block: {label}", file=sys.stderr)
        return 1
    print(f"{'Updated' if write else 'Verified'} {len(TARGETS)} current-state blocks.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--output", type=pathlib.Path, required=True)
    render_parser = subparsers.add_parser("render")
    mode = render_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    if args.command == "collect":
        if args.output.resolve() == args.manifest.resolve() or is_tracked(args.output):
            raise SystemExit(
                f"error: collect output is tracked: {args.output}; collect into artifacts/ or /tmp"
            )
        observed = collect(manifest)
        atomic_text(args.output, json.dumps(observed, indent=2, sort_keys=True) + "\n")
        print(f"Collected current state in {args.output}")
        return 0
    return render(manifest, args.write)


if __name__ == "__main__":
    raise SystemExit(main())
