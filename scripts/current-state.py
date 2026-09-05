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
    required = {"schemaVersion", "asOf", "corpus", "environment", "pendingEvent",
                "probeBaselines", "verification"}
    if value.get("schemaVersion") != 1 or not required.issubset(value):
        raise SystemExit("error: current-state manifest is not schema version 1")
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", str(value["asOf"])):
        raise SystemExit("error: current-state asOf must be an ISO date")

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

    environment = require_object(value, "environment", {"installed", "latestObserved"})
    installed = require_object(
        environment, "installed", {"os", "xcode", "sdks", "simulatorRuntimes", "fm"}
    )
    require_object(installed, "os", {"name", "version", "build"})
    require_object(installed, "xcode", {"path", "version", "build"})
    sdks = require_object(installed, "sdks", {"macosx", "iphoneos"})
    require_object(sdks, "macosx", {"version", "build"})
    require_object(sdks, "iphoneos", {"version", "build"})
    require_object(installed, "fm", {"path", "version"})
    runtimes = installed["simulatorRuntimes"]
    if not isinstance(runtimes, list) or any(
        not isinstance(item, dict) or not {"name", "version", "build"}.issubset(item)
        for item in runtimes
    ):
        raise SystemExit("error: current-state simulatorRuntimes must be a runtime array")
    latest = require_object(environment, "latestObserved", {"xcode", "ios", "macos"})
    for name in ("xcode", "ios", "macos"):
        release = require_object(latest, name, {"version", "build", "released", "sourceUrl"})
        if not re.fullmatch(r"20\d\d-\d\d-\d\d", str(release["released"])) or not str(
            release["sourceUrl"]
        ).startswith(("https://", "http://")):
            raise SystemExit(f"error: current-state latestObserved {name!r} lacks dated source evidence")

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
    if not isinstance(verification["blocker"], str) or not re.fullmatch(
        r"20\d\d-\d\d-\d\d", str(verification["lastFullRun"])
    ):
        raise SystemExit("error: current-state verification must include blocker text and an ISO date")
    return value


def run(*command: str, env: dict | None = None) -> str:
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


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


def installed_environment(previous: dict) -> dict:
    sw = dict(
        line.split(":", 1) for line in run("sw_vers").splitlines() if ":" in line
    )
    xcode_path = os.environ.get("DEVELOPER_DIR") or previous["xcode"]["path"]
    env = {**os.environ, "DEVELOPER_DIR": xcode_path}
    xcode_lines = run("xcodebuild", "-version", env=env).splitlines()

    def sdk(name: str) -> dict:
        return {
            "version": run("xcrun", "--sdk", name, "--show-sdk-version", env=env) or None,
            "build": run("xcrun", "--sdk", name, "--show-sdk-build-version", env=env) or None,
        }

    runtimes = []
    for line in run("xcrun", "simctl", "list", "runtimes", env=env).splitlines():
        match = re.match(r"(iOS) ([0-9.]+) \([0-9.]+ - ([^)]+)\)", line.strip())
        if match:
            runtimes.append({"name": match.group(1), "version": match.group(2),
                             "build": match.group(3)})
    return {
        "os": {"name": sw.get("ProductName", "").strip() or None,
               "version": sw.get("ProductVersion", "").strip() or None,
               "build": sw.get("BuildVersion", "").strip() or None},
        "xcode": {"path": xcode_path,
                  "version": xcode_lines[0].removeprefix("Xcode ") if xcode_lines else None,
                  "build": xcode_lines[1].removeprefix("Build version ")
                  if len(xcode_lines) > 1 else None},
        "sdks": {"macosx": sdk("macosx"), "iphoneos": sdk("iphoneos")},
        "simulatorRuntimes": runtimes,
        "fm": {"path": shutil.which("fm"), "version": None},
    }


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


def collect(manifest: dict) -> dict:
    value = json.loads(json.dumps(manifest))
    value["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    value["corpus"] = corpus_state()
    value["environment"]["installed"] = installed_environment(
        manifest["environment"]["installed"]
    )
    value["verification"] = snippet_state(manifest["verification"])
    installed = value["environment"]["installed"]
    latest = value["environment"]["latestObserved"]
    latest_runtime = max(
        (item for item in installed["simulatorRuntimes"] if item["name"] == "iOS"),
        key=lambda item: item["build"], default={"build": None},
    )
    comparisons = (
        ("Xcode", installed["xcode"]["build"], latest["xcode"]["build"]),
        ("macOS", installed["os"]["build"], latest["macos"]["build"]),
        ("iOS Simulator", latest_runtime.get("build"), latest["ios"]["build"]),
    )
    reasons = [f"Installed {name} build {actual or 'unknown'} trails observed build {expected}."
               for name, actual, expected in comparisons if actual != expected]
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
    statuses = ", ".join(f"{count} `{name}`" for name, count in verification["statusCounts"].items())
    reasons = " ".join(state["pendingEvent"]["reasons"]) or "No release-event refresh is pending."
    ios_runtimes = [item for item in installed["simulatorRuntimes"] if item["name"] == "iOS"]
    newest_ios_runtime = max(
        ios_runtimes, key=lambda item: item.get("build") or "", default={"build": "unknown"}
    )["build"]
    baselines = "\n".join(topology_line(key, value)
                          for key, value in state["probeBaselines"].items())
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
            f"`{installed['fm']['path']}`. Latest observed: Xcode {latest['xcode']['version']} "
            f"({latest['xcode']['build']}), iOS {latest['ios']['version']} ({latest['ios']['build']}), "
            f"and macOS {latest['macos']['version']} ({latest['macos']['build']}). {reasons}"
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
