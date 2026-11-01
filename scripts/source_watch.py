"""Reviewed source baselines, pending observations, and exact-capture acknowledgment."""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import pathlib


@contextlib.contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load(path, cycle, legacy=None):
    value = cycle.read_json(path, None)
    if value is None and legacy is not None:
        value = cycle.read_json(legacy, None)
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("source-watch state must be an object")
    if value.get("schemaVersion") != 2:
        return {"schemaVersion": 2, "reviewed": {}, "latestObserved": {}, "pending": {},
                "legacySeed": value}
    for key in ("reviewed", "latestObserved", "pending"):
        if not isinstance(value.get(key), dict):
            raise ValueError(f"source-watch {key} must be an object")
        for name, observation in value[key].items():
            if not isinstance(observation, dict) or not isinstance(observation.get("sha256"), str):
                raise ValueError(f"invalid source-watch observation for {name}")
    return value


def observe(state, observations):
    latest = dict(state["latestObserved"])
    pending = dict(state["pending"])
    for name, current in observations.items():
        prior = latest.get(name)
        if prior and dt.datetime.fromisoformat(prior["capturedAt"].replace("Z", "+00:00")) > dt.datetime.fromisoformat(current["capturedAt"].replace("Z", "+00:00")):
            continue  # A slower older run cannot supersede a newer committed capture.
        latest[name] = current
        if name == "releases":
            continue
        reviewed = state["reviewed"].get(name)
        if reviewed is None or reviewed["sha256"] != current["sha256"] or name in pending:
            pending[name] = current
    return {**state, "latestObserved": latest, "pending": pending}


def findings(state):
    result = []
    for name, current in sorted(state["pending"].items()):
        reviewed = state["reviewed"].get(name)
        kind = "documentation-disagreement" if name == "image-reference" and not current.get("pagesAgree", True) else "source-review-required" if reviewed is None else (
            "developer-news-changed" if name == "news" else "documentation-changed")
        finding = {"kind": kind, "source": name, "url": current["url"],
                   "oldHash": reviewed["sha256"] if reviewed else None,
                   "newHash": current["sha256"], "requiresAcknowledgment": True}
        if name == "news":
            old = {item["id"]: item for item in reviewed.get("newsItems", [])} if reviewed else {}
            items = current.get("newsItems", [])
            finding["newItems"] = [item for item in items if item["id"] not in old]
            finding["updatedItems"] = [item for item in items if item["id"] in old and item != old[item["id"]]]
        result.append(finding)
    return result


def commit(update, cycle):
    path = pathlib.Path(update["statePath"])
    with locked(path):
        state = load(path, cycle, pathlib.Path(update["legacyPath"]) if update.get("legacyPath") else None)
        cycle.atomic_json(path, observe(state, update["observations"]))


def acknowledge(args, cycle):
    root = args.run_root.resolve()
    report = cycle.read_json(root / "report.json")
    update = report.get("sourceWatch") if isinstance(report, dict) else None
    if not isinstance(update, dict):
        raise cycle.CycleError("report has no source-watch captures to acknowledge")
    path = pathlib.Path(update["statePath"])
    with locked(path):
        state = load(path, cycle)
        selected = {}
        for name, captured in update["observations"].items():
            if name == "releases":
                continue
            relative = pathlib.PurePosixPath(captured.get("capturePath", f"official-sources/{name}.txt"))
            if relative.is_absolute() or ".." in relative.parts:
                raise cycle.CycleError("source capture path escapes its report")
            payload = (root / relative).read_bytes()
            for source in captured.get("files", []):
                source_path = pathlib.PurePosixPath(source["path"])
                if source_path.is_absolute() or ".." in source_path.parts or hashlib.sha256((root / source_path).read_bytes()).hexdigest() != source["sha256"]:
                    raise cycle.CycleError(f"{name} documentation bytes no longer match the capture")
            if hashlib.sha256(payload).hexdigest() != captured["sha256"]:
                raise cycle.CycleError(f"{name} capture hash no longer matches this report")
            latest = state["latestObserved"].get(name)
            if latest is None or latest["sha256"] != captured["sha256"]:
                raise cycle.CycleError(f"stale {name} acknowledgment; review the latest report")
            selected[name] = captured
        if not selected:
            raise cycle.CycleError("report contains no complete documentation/news captures")
        for name, captured in selected.items():
            state["reviewed"][name] = {**captured, "acknowledgedAt": cycle.iso(), "report": str(root / "report.json")}
            state["pending"].pop(name, None)
        cycle.atomic_json(path, state)
    print(json.dumps({"statePath": str(path), "acknowledged": sorted(selected)}))
    return 0
