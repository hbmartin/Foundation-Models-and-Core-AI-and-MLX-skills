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
import signal
import subprocess
import sys
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from types import SimpleNamespace

try:
    from . import source_watch, probe_evidence
except ImportError:  # Direct script entry point.
    import source_watch
    import probe_evidence


SOURCES = {
    "releases": "https://developer.apple.com/news/releases/rss/releases.rss",
    "news": "https://developer.apple.com/news/rss/news.rss",
    "foundationmodels": "https://developer.apple.com/documentation/updates/foundationmodels.md",
}


class Runner:
    def __init__(self, root, repository, cycle, timeout=600):
        self.root, self.repository, self.cycle = root, repository, cycle
        self.timeout = timeout
        self.steps = []
        self.findings = []
        self.source_update = None
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
        started = self.cycle.iso()
        code, error = 127, None
        process = None
        stdout = self.root / "logs" / f"{name}.stdout"
        stderr = self.root / "logs" / f"{name}.stderr"
        with stdout.open("w") as output, stderr.open("w") as diagnostics:
            try:
                process = subprocess.Popen(command, cwd=self.repository, stdout=output,
                                           stderr=diagnostics, start_new_session=True)
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
        log.write_text(stdout.read_text(errors="replace") + stderr.read_text(errors="replace"))
        if code and error is None:
            error = f"command exited {code}; see {log}"
        return self.record(name, "passed" if code == 0 else "blocked",
                           command=list(map(str, command)), exitCode=code, error=error,
                           startedAt=started, finishedAt=self.cycle.iso(), log=str(log),
                           stdout=str(stdout), stderr=str(stderr))

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

    @contextlib.contextmanager
    def lane(self, name):
        try:
            yield
        except Exception as error:
            self.record(name, "blocked", error=f"{type(error).__name__}: {error}")


def validate_defects(payload):
    if not isinstance(payload, dict) or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 2:
        raise ValueError("expected defect report schema version 2")
    if not isinstance(payload.get("references"), list):
        raise ValueError("references must be an array")
    verdicts = payload["summary"]["verdicts"]
    if not isinstance(verdicts, dict):
        raise ValueError("summary verdicts must be an object")
    for key in ("UNREACHABLE", "AMBIGUOUS", "STATE-CHANGED"):
        if type(verdicts.get(key)) is not int or verdicts[key] < 0:
            raise ValueError(f"summary verdict {key} must be a nonnegative integer")


def validate_observation(payload):
    if not isinstance(payload, dict) or type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1:
        raise ValueError("expected observed-state schema version 1")
    collection = payload["collection"]
    if not isinstance(collection, dict):
        raise ValueError("collection must be an object")
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
        deterministic_shape = cycle.deterministic_failure_shape(deterministic)
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
            published = email.utils.parsedate_to_datetime(item.findtext("pubDate"))
            date = published.date().isoformat()
            records.append({"component": match[1], "version": match[2], "build": match[3],
                            "released": date, "publishedAt": published.isoformat(), "url": item.findtext("link", SOURCES["releases"])})
    if not records:
        raise ValueError("release feed contains no identifiable Xcode, iOS, or macOS releases")
    return records


def release_rank(record):
    version = record["version"]
    numbers = tuple(map(int, re.match(r"\d+(?:\.\d+)*", version)[0].split(".")))
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers = numbers[:-1]
    numbers += (0,) * max(0, 3 - len(numbers))
    prerelease = re.search(r"\b(beta|rc|release candidate)(?:\s*(\d+))?\b", version, re.I)
    if not prerelease:
        return numbers, 2, 0
    return numbers, 0 if prerelease[1].lower() == "beta" else 1, int(prerelease[2] or 1)


def news_records(payload):
    items = ET.fromstring(payload).findall(".//item")
    if not items:
        raise ValueError("news feed contains no items")
    records = []
    for item in items:
        title = item.findtext("title", "").strip()
        if not title:
            raise ValueError("news item has no title")
        url = item.findtext("link", "").strip()
        published = item.findtext("pubDate", "").strip()
        identity = item.findtext("guid", "").strip() or url or hashlib.sha256(
            json.dumps([title, published]).encode()).hexdigest()
        records.append({"id": identity, "title": title, "url": url or SOURCES["news"],
                        "published": published})
    return records


def source_state_path(runner, args):
    consumer = getattr(args, "watch_consumer", None)
    if consumer:
        if not runner.cycle.SAFE_RUN_ID.fullmatch(consumer):
            raise ValueError("invalid watch consumer")
        return args.artifact_root / "state/source-watch" / f"{consumer}.json"
    return runner.root / "official-sources/state.json"


def watch_sources(runner, baseline, state_path, timeout=40):
    legacy = state_path.parent.parent / "official-source-watch.json" if state_path.parent.name == "source-watch" else None
    with source_watch.locked(state_path):
        previous = source_watch.load(state_path, runner.cycle, legacy)
    captures, releases, observations = [], [], {}
    directory = runner.root / "official-sources"
    directory.mkdir(exist_ok=True)
    for name, url in SOURCES.items():
        with runner.lane(f"official-{name}"):
            request = urllib.request.Request(url, headers={"User-Agent": "corpus-freshness/1"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read(2 * 1024 * 1024 + 1)
                if len(data) > 2 * 1024 * 1024:
                    raise ValueError("source exceeds 2 MiB capture limit")
            (directory / f"{name}.txt").write_bytes(data)
            if name == "releases":
                releases = release_records(data)
            elif name == "news":
                news = news_records(data)
            elif not data.decode("utf-8").strip().startswith(("<!--", "#")):
                raise ValueError("expected Foundation Models Markdown documentation")
            current = {"name": name, "url": url, "sha256": hashlib.sha256(data).hexdigest(),
                       "capturedAt": runner.cycle.iso(dt.datetime.now(dt.timezone.utc))}
            if name == "news":
                current["newsItems"] = news
            observations[name] = current
            captures.append(current)
            runner.record(f"official-{name}", "passed", url=url, sha256=current["sha256"])
    for component, key in (("Xcode", "xcode"), ("iOS", "ios"), ("macOS", "macos")):
        with runner.lane(f"release-{key}"):
            records = [r for r in releases if r["component"] == component]
            if not records:
                continue
            rank = max(map(release_rank, records))
            newest = [r for r in records if release_rank(r) == rank]
            old = baseline["environment"]["latestObserved"][key]
            if not isinstance(old, dict) or not isinstance(old.get("version"), str):
                raise ValueError(f"missing recorded release for {component}")
            matching = release_rank(old) == rank
            if not matching or old.get("build") not in {r["build"] for r in newest}:
                runner.findings.append({"kind": "release-changed", "component": component,
                                        "recorded": old, "observed": newest})
            elif len({r["build"] for r in newest}) > 1:
                runner.findings.append({"kind": "release-build-set-changed", "component": component,
                                        "recorded": old, "observed": newest,
                                        "interpretation": "Multiple same-version builds require review; no authoritative build inferred."})
    runner.cycle.atomic_json(directory / "manifest.json", {"schemaVersion": 2,
                             "captures": captures, "releases": releases})
    state = source_watch.observe(previous, observations)
    runner.findings.extend(source_watch.findings(state))
    runner.source_update = {"statePath": str(state_path), "legacyPath": str(legacy) if legacy else None,
                            "observations": observations}


def collect_defects(runner, mode, baseline, thread_review, args):
    root = runner.root
    root = runner.root
    defects = ["./scripts/refresh-defect-statuses.sh", "--format", "json", "--output", str(root / "defects.json")]
    if mode == "daily":
        defects.append("--changed-only")
    if args.skip_web:
        runner.record("defects", "blocked", error="GitHub defect lookups explicitly skipped")
        return
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


def collect_observation(runner, mode, baseline, thread_review, args):
    root = runner.root
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


def collect_tools(runner, mode, baseline, thread_review, args):
    root = runner.root
    for name, command in (("xcode", ["xcodebuild", "-version"]), ("os", ["sw_vers"]),
                          ("fm-path", ["xcrun", "--no-cache", "--find", "fm"])):
        runner.command(name, command, timeout=45)
    fm_result = runner.steps[-1]
    if fm_result["status"] == "passed":
        fm = pathlib.Path(fm_result.get("stdout", fm_result["log"])).read_text().strip()
        if pathlib.Path(fm).is_absolute():
            runner.command("fm-help", [fm, "--help"], timeout=45)
        else:
            runner.record("fm-help", "blocked", error="xcrun did not return an absolute tool path")


def collect_sources(runner, mode, baseline, thread_review, args):
    root = runner.root
    if args.skip_web:
        runner.record("official-sources", "blocked", error="official-source checks explicitly skipped")
    else:
        watch_sources(runner, baseline, source_state_path(runner, args))


def collect_probes(runner, mode, baseline, thread_review, args):
    root = runner.root
    probe_env = ["env", "AUTOMATION_ID=weekly-improvements", f"PROBE_ARTIFACT_ROOT={root / 'probe-artifacts'}"]
    host = runner.command("host-probes", [*probe_env, f"PROBE_RUN_ID={args.run_id}-host", "./scripts/run-probes.sh", "host"])
    selection = runner.command("simulator-destination", [sys.executable, "scripts/simulator_destination.py", "--json"], timeout=90)
    simulator = None
    if selection["status"] == "passed":
        try:
            destination = json.loads(pathlib.Path(selection.get("stdout", selection["log"])).read_text())
            if not isinstance(destination.get("destination"), str):
                raise ValueError("missing simulator destination")
            simulator = runner.command("simulator-probes", [*probe_env, f"PROBE_RUN_ID={args.run_id}-simulator", "./scripts/run-probes.sh", "simulator", "--destination", destination["destination"]])
        except (ValueError, OSError) as error:
            runner.record("simulator-probes", "blocked", error=f"invalid simulator selection: {error}")
    else:
        runner.record("simulator-probes", "blocked", error="no available simulator destination; see simulator-destination log")
    summaries = {}
    observed = runner.cycle.read_json(root / "observed-state.json", {})
    installed = observed.get("environment", {}).get("installed", {})
    for name, result in (("host", host), ("simulator", simulator)):
        if result:
            with runner.lane(f"{name}-probe-coverage"):
                text = pathlib.Path(result["log"]).read_text(errors="replace")
                hardware = re.search(r"hw.model=(\S+)", text)
                topology = {"hostingMode": "tool-hosted", "observedAt": runner.cycle.iso(),
                            "xcodeVersion": installed.get("xcode", {}).get("version"),
                            "xcodeBuild": installed.get("xcode", {}).get("build"),
                            "sdks": installed.get("sdks", {}), "buildConfiguration": "Debug"}
                if name == "host":
                    topology.update(platform="macOS", osVersion=installed.get("os", {}).get("version"),
                                    osBuild=installed.get("os", {}).get("build"),
                                    destination="local arm64 host", device=hardware[1] if hardware else None)
                else:
                    topology.update(platform="iOS Simulator", osVersion=destination.get("version"),
                                    osBuild=destination.get("runtimeBuild"), destination=destination["destination"],
                                    device=destination.get("device"), runtimeIdentifier=destination.get("runtimeIdentifier"),
                                    udid=destination.get("udid"))
                run_directory = root / "probe-artifacts" / f"{args.run_id}-{name}"
                context_path = run_directory / "run-context.json"
                selection_context = runner.cycle.read_json(context_path, {})
                summaries[name] = probe_evidence.summarize(result["log"], run_directory, topology, selection_context.get("excludedTests", []))
                summaries[name]["includedTests"] = selection_context.get("includedTests", [])
                if context_path.exists():
                    summaries[name]["sources"].append({"path": str(context_path), "sha256": hashlib.sha256(context_path.read_bytes()).hexdigest()})
    runner.cycle.atomic_json(root / "probe-summary.json", {"schemaVersion": 2, "lanes": summaries,
                             "comparison": "Counts and measured defaults are not compared across different complete topologies."})


def collect_auxiliary(runner, mode, baseline, thread_review, args):
    root = runner.root
    if args.skip_web:
        runner.record("research-mirrors", "blocked", error="mirror fetches explicitly skipped")
        runner.record("apple-docs-watch", "blocked", error="documentation fetches explicitly skipped")
        return
    mirrors = args.artifact_root / "cache/research-mirrors"
    runner.command("research-mirrors", ["env", f"RESEARCH_REPOS_ROOT={mirrors}", "./scripts/clone-research-repos.sh"])
    result = runner.command("apple-docs-watch", ["./scripts/capture-apple-docs-watch.py", "--output", str(root / "apple-docs")])
    manifest = runner.document("apple-docs-manifest", root / "apple-docs/manifest.json", validate_docs_watch)
    if manifest and result.get("exitCode") in (0, 1):
        result["status"], result["error"] = "passed", None
        runner.cycle.atomic_json(root / "results/apple-docs-watch.json", result)
        capture = {"pagesAgree": manifest["pagesAgree"], "captures": [
            {key: item.get(key) for key in ("name", "sha256", "methodSpellings")} for item in manifest["captures"]]}
        source_path = root / "official-sources/image-reference.txt"
        source_path.parent.mkdir(exist_ok=True)
        source_path.write_text(json.dumps(capture, sort_keys=True))
        if runner.source_update is None:
            runner.source_update = {"statePath": str(source_state_path(runner, args)), "observations": {}}
        runner.source_update["observations"]["image-reference"] = {
            "name": "image-reference", "url": "https://developer.apple.com/documentation/foundationmodels/imagereference",
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "capturedAt": runner.cycle.iso(dt.datetime.now(dt.timezone.utc)), "pagesAgree": manifest["pagesAgree"],
            "files": [{"path": f"apple-docs/{item.get('path', item['name'] + '.md')}", "sha256": item.get("sha256")} for item in manifest["captures"]]}
        path = pathlib.Path(runner.source_update["statePath"])
        with source_watch.locked(path):
            previous = source_watch.load(path, runner.cycle)
        updated = source_watch.observe(previous, runner.source_update["observations"])
        runner.findings[:] = [finding for finding in runner.findings if finding.get("source") != "image-reference"]
        runner.findings.extend(finding for finding in source_watch.findings(updated) if finding["source"] == "image-reference")


def validate_docs_watch(payload):
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1 or type(payload.get("pagesAgree")) is not bool:
        raise ValueError("invalid documentation watch manifest")
    captures = payload.get("captures")
    if (not isinstance(captures, list) or len(captures) != 2
            or {c.get("name") for c in captures if isinstance(c, dict)} != {"overview", "member"}
            or any(c.get("status") != "captured" or not c.get("methodSpellings") for c in captures)):
        raise ValueError("documentation capture or declaration coverage incomplete")


def collect_review(runner, mode, baseline, thread_review, args):
    root = runner.root
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


def collect(runner, mode, baseline, thread_review, args):
    lanes = [collect_defects, collect_observation, collect_tools, collect_sources]
    if mode == "weekly":
        lanes += [collect_probes, collect_auxiliary, collect_review]
    for lane in lanes:
        with runner.lane(getattr(lane, "__name__", "collection-lane")):
            lane(runner, mode, baseline, thread_review, args)


def write_report(runner, mode, outcome, emit=True, **details):
    payload = {"schemaVersion": 1, "mode": mode, "runId": runner.root.name,
               "reportedAt": runner.cycle.iso(), "outcome": outcome,
               "steps": runner.steps, "findings": runner.findings,
               "sourceWatch": runner.source_update, **details}
    runner.cycle.atomic_json(runner.root / "report.json", payload)
    lines = [f"{mode.title()} freshness run: {runner.root.name}", f"Outcome: {outcome}", ""]
    lines.extend(f"{s['name']}: {s['status']}" + (f" — {s['error']}" if s.get("error") else "") for s in runner.steps)
    lines.extend(["", "Findings:", *(json.dumps(f, sort_keys=True) for f in runner.findings)])
    (runner.root / "report.txt").write_text("\n".join(lines) + "\n")
    if runner.source_update:
        source_watch.commit(runner.source_update, runner.cycle)
    if emit:
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
    consumer = getattr(args, "watch_consumer", None)
    if consumer and not cycle.SAFE_RUN_ID.fullmatch(consumer):
        raise cycle.CycleError("invalid watch consumer")
    baseline = cycle.read_json(args.repository / "notes/current-state.json")
    identity = cycle.git(args.repository, "config", "--get", "remote.origin.url")
    review = read_thread_review(args.thread_review, identity, cycle) if args.thread_review else None
    if args.cycle == "weekly":
        with contextlib.redirect_stdout(sys.stderr):
            manifest = cycle.prepare_run(SimpleNamespace(repository=args.repository, artifact_root=args.artifact_root,
                                          worktree_root=None, run_id=args.run_id,
                                          skip_remote_check=False, ref=args.ref))
        root = args.artifact_root / "weekly-improvements" / args.run_id
        repository = pathlib.Path(manifest["worktree"])
    else:
        root = args.artifact_root / "daily-defects" / args.run_id
        if root.exists():
            raise cycle.CycleError(f"refusing to reuse run directory {root}")
        root.mkdir(parents=True)
        repository = args.repository
        manifest = {"schemaVersion": 1, "runId": args.run_id, "createdAt": cycle.iso(),
                    "repositoryIdentity": identity, "status": "running"}
    runner = None
    error = None
    interrupted = False
    retained = False
    outcome = "blocked"

    def note(name, exception):
        if runner is not None:
            try:
                runner.record(name, "blocked", error=str(exception) or type(exception).__name__)
            except OSError as recording_error:
                print(f"{name}: {exception}; recording failed: {recording_error}", file=sys.stderr)

    try:
        runner = Runner(root, repository, cycle, args.command_timeout)
        cycle.atomic_json(root / "preflight.json", gate)
        if args.cycle == "weekly":
            cycle.read_json(root / "run.json")  # Validate persistence; cleanup uses the in-memory identity.
            baseline = cycle.read_json(repository / "notes/current-state.json")
        else:
            cycle.atomic_json(root / "run.json", manifest)
        collect(runner, args.cycle, baseline, review, args)
        blocked = any(step["status"] == "blocked" for step in runner.steps)
        outcome = "blocked" if blocked else "findings" if runner.findings else "clean"
        if args.cycle == "weekly":
            actions = cycle.read_json(root / "actions.json", {"summary": {"eligible": 0}})
            eligible = actions["summary"]["eligible"]
            if eligible and not args.keep_worktree:
                note("implementation", "eligible actions need reviewed implementation; use --keep-worktree to retain preparation")
                outcome = "blocked"
            cycle.atomic_json(root / "pr.json", {"checksPassed": outcome != "blocked", "mergeable": False, "prUrl": None})
        details = {"worktree": str(repository), "retainedForReview": True} if args.cycle == "weekly" and args.keep_worktree else {}
        write_report(runner, args.cycle, outcome, emit=False, **details)
        retained = bool(details)
    except (Exception, KeyboardInterrupt) as exception:
        error = str(exception) or "run interrupted"
        interrupted = isinstance(exception, KeyboardInterrupt)
        outcome = "blocked"
        note("collection", exception)
    finally:
        # A second handled termination must not interrupt teardown after the first.
        previous_term = previous_int = None
        try:
            previous_term = signal.signal(signal.SIGTERM, signal.SIG_IGN)
            previous_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
        except ValueError:
            pass
        try:
            if args.cycle == "weekly" and not retained:
                final_outcome = "no-change" if outcome == "clean" else outcome
                try:
                    with contextlib.redirect_stdout(sys.stderr):
                        cycle.finalize(SimpleNamespace(run_root=root, outcome=final_outcome, pr_url=None,
                                                       state_path=None, manifest=manifest))
                except Exception as exception:
                    outcome = "blocked"
                    note("finalization", exception)
                    # Policy refusals remain strict for manual callers. The runner owns
                    # disposal and explicitly records a blocked outcome before cleanup.
                    try:
                        with contextlib.redirect_stdout(sys.stderr):
                            cycle.finalize(SimpleNamespace(run_root=root, outcome="blocked", pr_url=None,
                                                           state_path=None, manifest=manifest))
                    except Exception as cleanup_error:
                        note("cleanup", cleanup_error)
            elif args.cycle == "daily":
                manifest.update(status="no-change" if outcome == "clean" else outcome, finishedAt=cycle.iso())
                cycle.atomic_json(root / "run.json", manifest)
        finally:
            if previous_term is not None:
                signal.signal(signal.SIGTERM, previous_term)
            if previous_int is not None:
                signal.signal(signal.SIGINT, previous_int)
    if runner is None:
        raise cycle.CycleError(error or "runner initialization failed; cleanup attempted")
    details = {"worktree": str(repository), "retainedForReview": True} if retained else {}
    write_report(runner, args.cycle, outcome, **details)
    return 130 if interrupted else 1 if outcome == "blocked" or error else 0
