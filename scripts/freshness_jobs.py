"""Execute the deterministic daily and weekly freshness lanes with durable evidence."""

from __future__ import annotations

import datetime as dt
import contextlib
import email.utils
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from types import SimpleNamespace


SOURCES = {
    "releases": "https://developer.apple.com/news/releases/rss/releases.rss",
    "news": "https://developer.apple.com/news/rss/news.rss",
    "foundationmodels": "https://developer.apple.com/documentation/updates/foundationmodels.md",
}


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


class Runner:
    def __init__(self, root, repository, cycle, timeout=600):
        self.root, self.repository, self.cycle = root, repository, cycle
        self.timeout = timeout
        self.steps = []
        self.findings = []
        for name in ("logs", "results", "probe-artifacts"):
            (root / name).mkdir(parents=True, exist_ok=True)

    def record(self, name, status, **details):
        result = {"name": name, "status": status, **details}
        self.cycle.atomic_json(self.root / "results" / f"{name}.json", result)
        self.steps.append(result)
        print(f"{name}: {status}", file=sys.stderr, flush=True)
        return result

    def command(self, name, command, timeout=None):
        log = self.root / "logs" / f"{name}.log"
        print(f"{name}: running", file=sys.stderr, flush=True)
        started = timestamp()
        code, error = 127, None
        process = None
        with log.open("w") as output:
            try:
                process = subprocess.Popen(command, cwd=self.repository, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=timeout or self.timeout)
                except subprocess.TimeoutExpired:
                    error = f"command timed out after {timeout or self.timeout} seconds"
                    self.stop(process)
                    code = 124
                except BaseException:
                    self.stop(process)
                    raise
            except OSError as exception:
                error = str(exception)
        if code and error is None:
            error = f"command exited {code}; see {log}"
        return self.record(name, "passed" if code == 0 else "blocked",
                           command=list(map(str, command)), exitCode=code, error=error,
                           startedAt=started, finishedAt=timestamp(), log=str(log))

    @staticmethod
    def stop(process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        except ProcessLookupError:
            process.wait()

    def document(self, name, path, validate):
        try:
            payload = json.loads(path.read_text())
            validate(payload)
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.record(name, "blocked", error=f"invalid {path.name}: {error}")
            return None
        self.record(name, "passed", artifact=str(path))
        return payload


def validate_defects(payload):
    if not isinstance(payload, dict) or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 2:
        raise ValueError("expected defect report schema version 2")
    if not isinstance(payload.get("references"), list):
        raise ValueError("references must be an array")
    verdicts = payload["summary"]["verdicts"]
    for key in ("UNREACHABLE", "AMBIGUOUS", "STATE-CHANGED"):
        if type(verdicts.get(key)) is not int or verdicts[key] < 0:
            raise ValueError(f"summary verdict {key} must be a nonnegative integer")


def validate_observation(payload):
    if not isinstance(payload, dict) or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1:
        raise ValueError("expected observed-state schema version 1")
    collection = payload["collection"]
    if type(collection.get("complete")) is not bool or not isinstance(collection.get("blockers"), list):
        raise ValueError("missing explicit collection coverage")
    if not isinstance(payload["environment"]["installed"], dict):
        raise ValueError("missing installed environment")
    installed = payload["environment"]["installed"]
    if any(not isinstance(installed.get(k), dict) for k in ("xcode", "os", "sdks")):
        raise ValueError("missing installed Xcode, OS, or SDK metadata")
    if not isinstance(installed.get("simulatorRuntimes"), list):
        raise ValueError("missing Simulator runtime observations")
    if collection["complete"] and collection["blockers"]:
        raise ValueError("complete observation cannot retain coverage blockers")


def read_thread_review(path, identity, cycle):
    payload = json.loads(path.read_text())
    if (not isinstance(payload, dict) or set(payload) != {"schemaVersion", "repositoryIdentity", "actions"}
            or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 2
            or payload.get("repositoryIdentity") != identity or not isinstance(payload.get("actions"), list)):
        raise ValueError("thread review requires schema 2, the exact repository identity, and actions only")
    for action in payload["actions"]:
        if not isinstance(action, dict) or set(action) - cycle.THREAD_ACTION_KEYS:
            raise ValueError("thread action contains unsupported or instruction-like fields")
        valid, _ = cycle.thread_evidence_status(action, identity)
        deterministic = action.get("deterministicFailure")
        deterministic_shape = (isinstance(deterministic, dict)
                               and set(deterministic) == {"validator", "artifact", "targetSha", "failed"}
                               and deterministic.get("validator") in cycle.DETERMINISTIC_VALIDATORS
                               and deterministic.get("failed") is True
                               and all(isinstance(deterministic.get(k), str) for k in ("artifact", "targetSha")))
        if not valid and not (deterministic_shape and not action.get("taskEvidence")):
            raise ValueError("thread action requires valid structured task observations or deterministic-failure metadata")
        # Corroboration and the run-bound failure attestation remain evaluate's
        # responsibility. A well-formed one-task observation is report-only.
    return payload


def release_records(payload):
    root = ET.fromstring(payload)
    items = root.findall(".//item")
    if not items:
        raise ValueError("release feed contains no items")
    records = []
    for item in items:
        title = item.findtext("title", "").strip()
        match = re.fullmatch(r"(Xcode|iOS|macOS)\s+(.+?)\s+\(([^()]+)\)", title)
        if match and re.match(r"\d+(?:\.\d+)*", match[2]):
            date = email.utils.parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
            records.append({"component": match[1], "version": match[2], "build": match[3],
                            "released": date, "url": item.findtext("link", SOURCES["releases"])})
    if not records:
        raise ValueError("release feed contains no identifiable Xcode, iOS, or macOS releases")
    return records


def release_rank(record):
    version = record["version"]
    numbers = tuple(map(int, re.match(r"\d+(?:\.\d+)*", version)[0].split(".")))
    return numbers, 0 if "beta" in version.lower() else 1 if "rc" in version.lower() else 2


def watch_sources(runner, baseline, state_path, timeout=40):
    try:
        previous = runner.cycle.read_json(state_path, {})
        if not isinstance(previous, dict):
            raise ValueError("source-watch state must be an object")
    except (ValueError, runner.cycle.CycleError) as error:
        runner.record("official-source-state", "blocked", error=str(error))
        previous = {}
    captures, releases = [], []
    directory = runner.root / "official-sources"
    directory.mkdir(exist_ok=True)
    for name, url in SOURCES.items():
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "corpus-freshness/1"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read(2 * 1024 * 1024 + 1)
                if len(data) > 2 * 1024 * 1024:
                    raise ValueError("source exceeds 2 MiB capture limit")
            (directory / f"{name}.txt").write_bytes(data)
            if name == "releases":
                releases = release_records(data)
            elif name == "news":
                if not ET.fromstring(data).findall(".//item"):
                    raise ValueError("news feed contains no items")
            elif not data.decode("utf-8").strip().startswith(("<!--", "#")):
                raise ValueError("expected Foundation Models Markdown documentation")
            digest = hashlib.sha256(data).hexdigest()
            captures.append({"name": name, "url": url, "sha256": digest, "capturedAt": timestamp()})
            if name == "foundationmodels" and previous.get(name) not in (None, digest):
                runner.findings.append({"kind": "documentation-changed", "url": url,
                                        "oldHash": previous[name], "newHash": digest})
            runner.record(f"official-{name}", "passed", url=url, sha256=digest)
        except (OSError, ValueError, ET.ParseError, TypeError) as error:
            runner.record(f"official-{name}", "blocked", url=url, error=str(error))
    for component, key in (("Xcode", "xcode"), ("iOS", "ios"), ("macOS", "macos")):
        records = [r for r in releases if r["component"] == component]
        if not records:
            continue
        rank = max(map(release_rank, records))
        newest = [r for r in records if release_rank(r) == rank]
        old = baseline["environment"]["latestObserved"][key]
        if not any(r["version"] == old["version"] and r["build"] == old["build"] for r in newest):
            runner.findings.append({"kind": "release-changed", "component": component,
                                    "recorded": old, "observed": newest})
    runner.cycle.atomic_json(directory / "manifest.json", {"schemaVersion": 1,
                             "captures": captures, "releases": releases})
    if len(captures) == len(SOURCES):
        runner.cycle.atomic_json(state_path, {r["name"]: r["sha256"] for r in captures})


def collect(runner, mode, baseline, thread_review, args):
    root = runner.root
    defects = ["./scripts/refresh-defect-statuses.sh", "--format", "json", "--output", str(root / "defects.json")]
    if mode == "daily":
        defects.append("--changed-only")
    runner.command("defects", defects)
    data = runner.document("defect-report", root / "defects.json", validate_defects)
    if data:
        verdicts = data["summary"]["verdicts"]
        if verdicts["UNREACHABLE"] or verdicts["AMBIGUOUS"]:
            runner.record("defect-coverage", "blocked", verdicts=verdicts)
            runner.findings.append({"kind": "defect-coverage", "verdicts": verdicts,
                                    "unreachableReferences": data.get("unreachableReferences", []),
                                    "artifact": str(root / "defects.json")})
        if verdicts["STATE-CHANGED"]:
            runner.findings.append({"kind": "defect-state-changed", "count": verdicts["STATE-CHANGED"],
                                    "references": [{key: row[key] for key in
                                                    ("ref", "registryId", "liveUrl", "claims", "liveState", "latestClaimDate", "closedAt", "mergeTimestamp", "sightingIds")
                                                    if key in row}
                                                   for row in data["references"] if isinstance(row, dict) and row.get("verdict") == "STATE-CHANGED"],
                                    "artifact": str(root / "defects.json")})
    command = ["./scripts/current-state.py", "collect", "--output", str(root / "observed-state.json")]
    if mode == "daily":
        command.append("--skip-generated-checks")
    runner.command("current-state", command)
    data = runner.document("observed-state", root / "observed-state.json", validate_observation)
    if data:
        if not data["collection"]["complete"]:
            runner.record("observation-coverage", "blocked", blockers=data["collection"]["blockers"])
        if mode == "weekly" and (data["collection"].get("generatedOutputsChecked") is not True
                                 or any(data.get("generatedOutputs", {}).get(k, {}).get("status") != "current"
                                        for k in ("currentStateBlocks", "indexes", "skills"))):
            runner.record("generated-output-coverage", "blocked", error="weekly generated-output checks did not all attest current output")
        installed = data["environment"]["installed"]
        for component in ("xcode", "os", "sdks", "simulatorRuntimes"):
            if installed[component] != baseline["environment"]["installed"][component]:
                runner.findings.append({"kind": "installed-state-changed", "component": component,
                                        "recorded": baseline["environment"]["installed"][component],
                                        "observed": installed[component]})
    for name, command in (("xcode", ["xcodebuild", "-version"]), ("os", ["sw_vers"]),
                          ("fm-path", ["xcrun", "--no-cache", "--find", "fm"])):
        runner.command(name, command, timeout=45)
    fm_result = runner.steps[-1]
    if fm_result["status"] == "passed":
        fm = pathlib.Path(fm_result["log"]).read_text().strip()
        if pathlib.Path(fm).is_absolute():
            runner.command("fm-help", [fm, "--help"], timeout=45)
        else:
            runner.record("fm-help", "blocked", error="xcrun did not return an absolute tool path")
    if args.skip_web:
        runner.record("official-sources", "blocked", error="official-source checks explicitly skipped")
    else:
        watch_sources(runner, baseline, args.artifact_root / "state/official-source-watch.json")
    if mode == "weekly":
        probe_env = ["env", "AUTOMATION_ID=weekly-improvements", f"PROBE_ARTIFACT_ROOT={root / 'probe-artifacts'}"]
        host = runner.command("host-probes", [*probe_env, f"PROBE_RUN_ID={args.run_id}-host", "./scripts/run-probes.sh", "host"])
        selection = runner.command("simulator-destination", [sys.executable, "scripts/simulator_destination.py", "--json"], timeout=90)
        simulator = None
        if selection["status"] == "passed":
            try:
                destination = json.loads(pathlib.Path(selection["log"]).read_text())
                if not isinstance(destination.get("destination"), str):
                    raise ValueError("missing simulator destination")
                simulator = runner.command("simulator-probes", [*probe_env, f"PROBE_RUN_ID={args.run_id}-simulator", "./scripts/run-probes.sh", "simulator", "--destination", destination["destination"]])
            except (ValueError, OSError) as error:
                runner.record("simulator-probes", "blocked", error=f"invalid simulator selection: {error}")
        else:
            runner.record("simulator-probes", "blocked", error="no available simulator destination; see simulator-destination log")
        summaries = {}
        for name, result in (("host", host), ("simulator", simulator)):
            if result:
                text = pathlib.Path(result["log"]).read_text(errors="replace")
                totals = re.findall(r"Executed (\d+) tests?, with (?:(\d+) tests? skipped and )?(\d+) failures?", text)
                summaries[name] = {"hostingMode": "tool-hosted", "log": result["log"],
                                   "totals": dict(zip(("tests", "skipped", "failures"),
                                                     map(lambda v: int(v or 0), totals[-1]))) if totals else None,
                                   "observations": [line for line in text.splitlines() if line.startswith("PROBE-RESULT ")]}
                if not totals:
                    runner.record(f"{name}-probe-coverage", "blocked", error="probe log contains no completed XCTest summary")
        runner.cycle.atomic_json(root / "probe-summary.json", {"schemaVersion": 1, "lanes": summaries,
                                 "comparison": "Counts and measured defaults are not compared across different complete topologies."})
        runner.command("research-mirrors", ["./scripts/clone-research-repos.sh"])
        runner.command("apple-docs-watch", ["./scripts/capture-apple-docs-watch.py", "--output", str(root / "apple-docs")])
        if thread_review is None:
            runner.record("thread-review", "blocked", error="provide a reviewed schema-v2 --thread-review document; repository tasks were not reviewed")
            thread_review = {"schemaVersion": 2, "repositoryIdentity": runner.cycle.read_json(root / "run.json")["repositoryIdentity"], "actions": []}
        else:
            runner.record("thread-review", "passed", candidateActions=len(thread_review["actions"]))
        runner.cycle.atomic_json(root / "thread-review.json", thread_review)
        runner.cycle.atomic_json(root / "validation.json", {"schemaVersion": 1, "actions": [], "steps": runner.steps})
        with contextlib.redirect_stdout(sys.stderr):
            runner.cycle.evaluate(SimpleNamespace(run_root=root))
        for action in runner.cycle.read_json(root / "actions.json")["actions"]:
            runner.findings.append({"kind": "action-review", "id": action["id"],
                                    "summary": action.get("summary"),
                                    "automaticFixEligible": action["automaticFixEligible"],
                                    "eligibilityBlockers": action["eligibilityBlockers"]})


def clean_builds(root):
    removed = []
    for build in (root / "probe-artifacts").glob("*/Build"):
        if build.is_symlink() or not build.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"refusing to clean build outside this run: {build}")
        if build.is_dir():
            shutil.rmtree(build)
            removed.append(str(build))
    return removed


def write_report(runner, mode, outcome, **details):
    payload = {"schemaVersion": 1, "mode": mode, "runId": runner.root.name,
               "reportedAt": timestamp(), "outcome": outcome,
               "steps": runner.steps, "findings": runner.findings, **details}
    runner.cycle.atomic_json(runner.root / "report.json", payload)
    lines = [f"{mode.title()} freshness run: {runner.root.name}", f"Outcome: {outcome}", ""]
    lines.extend(f"{s['name']}: {s['status']}" + (f" — {s['error']}" if s.get("error") else "") for s in runner.steps)
    lines.extend(["", "Findings:", *(json.dumps(f, sort_keys=True) for f in runner.findings)])
    (runner.root / "report.txt").write_text("\n".join(lines) + "\n")
    print(json.dumps({"runRoot": str(runner.root), "report": str(runner.root / "report.txt"),
                      "outcome": outcome, **details}, sort_keys=True))


def run(args, cycle):
    def interrupt(_number, _frame):
        raise KeyboardInterrupt("run terminated")
    previous = None
    try:
        previous = signal.signal(signal.SIGTERM, interrupt)
    except ValueError:  # Library callers may be outside the main thread.
        pass
    try:
        return execute(args, cycle)
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)


def execute(args, cycle):
    args.repository = args.repository.resolve()
    args.artifact_root = args.artifact_root.resolve()
    preflight = [sys.executable, str(args.repository / "scripts/validate-automation-contracts.py"), "--format", "json"]
    preflight += ["--installed-root", str(args.installed_root)] if args.installed_root else ["--installed"]
    result = subprocess.run(preflight, capture_output=True, text=True, timeout=args.command_timeout, check=False)
    if result.returncode:
        raise cycle.CycleError("installed-contract preflight failed: " + (result.stdout or result.stderr).strip())
    gate = json.loads(result.stdout)
    if gate.get("valid") is not True:
        raise cycle.CycleError("installed-contract preflight did not attest valid contracts")
    args.run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    if not cycle.SAFE_RUN_ID.fullmatch(args.run_id):
        raise cycle.CycleError("invalid run id")
    baseline = cycle.read_json(args.repository / "notes/current-state.json")
    identity = cycle.git(args.repository, "config", "--get", "remote.origin.url")
    review = read_thread_review(args.thread_review, identity, cycle) if args.thread_review else None
    if args.cycle == "weekly":
        with contextlib.redirect_stdout(sys.stderr):
            cycle.prepare(SimpleNamespace(repository=args.repository, artifact_root=args.artifact_root,
                                          worktree_root=None, run_id=args.run_id,
                                          skip_remote_check=False, ref=args.ref))
        root = args.artifact_root / "weekly-improvements" / args.run_id
        manifest = cycle.read_json(root / "run.json")
        repository = pathlib.Path(manifest["worktree"])
        baseline = cycle.read_json(repository / "notes/current-state.json")
    else:
        root = args.artifact_root / "daily-defects" / args.run_id
        if root.exists():
            raise cycle.CycleError(f"refusing to reuse run directory {root}")
        root.parent.mkdir(parents=True, exist_ok=True)
        root.mkdir()
        repository = args.repository
    runner = Runner(root, repository, cycle, args.command_timeout)
    cycle.atomic_json(root / "preflight.json", gate)
    if args.cycle == "daily":
        cycle.atomic_json(root / "run.json", {"schemaVersion": 1, "runId": args.run_id,
                          "createdAt": timestamp(), "repositoryIdentity": identity, "status": "running"})
    error = None
    interrupted = False
    try:
        collect(runner, args.cycle, baseline, review, args)
    except (Exception, KeyboardInterrupt) as exception:
        error = str(exception) or "run interrupted"
        interrupted = isinstance(exception, KeyboardInterrupt)
        runner.record("collection", "blocked", error=error)
    blocked = any(step["status"] == "blocked" for step in runner.steps)
    outcome = "blocked" if blocked else "findings" if runner.findings else "clean"
    if args.cycle == "weekly":
        actions = cycle.read_json(root / "actions.json", {"summary": {"eligible": 0}})
        eligible = actions["summary"]["eligible"]
        if eligible and not args.keep_worktree:
            runner.record("implementation", "blocked", error="eligible actions need reviewed implementation; use --keep-worktree to retain preparation")
            blocked, outcome = True, "blocked"
        if args.keep_worktree:
            write_report(runner, args.cycle, outcome, worktree=str(repository), retainedForReview=True)
            return 130 if interrupted else 1 if blocked else 0
        cycle.atomic_json(root / "pr.json", {"checksPassed": not blocked, "mergeable": False, "prUrl": None})
        try:
            with contextlib.redirect_stdout(sys.stderr):
                cycle.finalize(SimpleNamespace(run_root=root, outcome="blocked" if blocked else "no-change", pr_url=None, state_path=None))
        except (OSError, ValueError, cycle.CycleError) as exception:
            runner.record("cleanup", "blocked", error=str(exception))
            blocked, outcome = True, "blocked"
    else:
        manifest = cycle.read_json(root / "run.json")
        manifest.update(status="no-change" if outcome == "clean" else outcome, finishedAt=timestamp())
        cycle.atomic_json(root / "run.json", manifest)
    write_report(runner, args.cycle, outcome)
    return 130 if interrupted else 1 if blocked or error else 0
