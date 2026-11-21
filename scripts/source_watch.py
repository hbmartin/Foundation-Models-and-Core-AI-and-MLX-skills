"""Reviewed source baselines, pending observations, and exact-capture acknowledgment."""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET


def empty_state():
    return {"schemaVersion": 2, "reviewed": {}, "latestObserved": {}, "pending": {}}


def news_records(payload, fallback_url="https://developer.apple.com/news/rss/news.rss"):
    items = ET.fromstring(payload).findall(".//item")
    if not items:
        raise ValueError("news feed contains no items")
    def content(element):
        return {"tag": element.tag, "attributes": element.attrib,
                "text": (element.text or "").strip(),
                "tail": (element.tail or "").strip(),
                "children": [content(child) for child in element]}
    records, identities = [], set()
    for item in items:
        title = item.findtext("title", "").strip()
        if not title:
            raise ValueError("news item has no title")
        url = item.findtext("link", "").strip()
        published = item.findtext("pubDate", "").strip()
        identity = item.findtext("guid", "").strip() or url or hashlib.sha256(
            json.dumps([title, published]).encode()).hexdigest()
        if identity in identities:
            raise ValueError(f"duplicate news identity: {identity}")
        identities.add(identity)
        details = [content(child) for child in item if child.tag not in {"title", "link", "pubDate", "guid"}]
        records.append({"id": identity, "title": title, "url": url or fallback_url, "published": published,
                        "content": sorted(details, key=lambda value: json.dumps(value, sort_keys=True))})
    return records


def news_hash(observation):
    items = observation.get("newsItems")
    if not isinstance(items, list) or not items or any(not isinstance(item, dict) or "content" not in item for item in items):
        return None  # Old item summaries did not retain descriptions/content.
    canonical = sorted(json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for item in items)
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode()).hexdigest()


def same_content(name, before, after):
    if name == "news":
        a, b = news_hash(before), news_hash(after)
        return a is not None and a == b
    return before["sha256"] == after["sha256"]


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
        return {**empty_state(), "legacySeed": value}
    for key in ("reviewed", "latestObserved", "pending"):
        if not isinstance(value.get(key), dict):
            raise ValueError(f"source-watch {key} must be an object")
        for name, observation in value[key].items():
            if not isinstance(observation, dict) or not isinstance(observation.get("sha256"), str):
                raise ValueError(f"invalid source-watch observation for {name}")
            if not all(isinstance(observation.get(field), str) for field in ("url", "capturedAt")):
                raise ValueError(f"missing source-watch capture metadata for {name}")
            captured = dt.datetime.fromisoformat(observation["capturedAt"].replace("Z", "+00:00"))
            if captured.tzinfo is None:
                raise ValueError(f"source-watch capture time has no timezone for {name}")
            for field in ("report", "capturePath"):
                if field in observation and not isinstance(observation[field], str):
                    raise ValueError(f"invalid source-watch {field} for {name}")
            if name == "news" and "newsItems" in observation:
                items = observation["newsItems"]
                if (not isinstance(items, list) or any(not isinstance(item, dict)
                        or not all(isinstance(item.get(field), str) for field in ("id", "title", "url", "published"))
                        or "content" in item and not isinstance(item["content"], list) for item in items)):
                    raise ValueError("source-watch newsItems must contain structured news records")
    reviewed = value["reviewed"].get("news")
    if reviewed and news_hash(reviewed) is None and reviewed.get("report"):
        # Upgrade only from hash-verified retained bytes, never an incomplete summary.
        relative = pathlib.PurePosixPath(reviewed.get("capturePath", "official-sources/news.txt"))
        if not relative.is_absolute() and ".." not in relative.parts:
            try:
                payload = (pathlib.Path(reviewed["report"]).parent / relative).read_bytes()
                if hashlib.sha256(payload).hexdigest() == reviewed["sha256"]:
                    reviewed["newsItems"] = news_records(payload)
            except (OSError, ValueError, ET.ParseError):
                pass  # The next observation explicitly requires migration review.
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
        if reviewed is None or not same_content(name, reviewed, current) or name in pending:
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
            finding["semanticHash"] = news_hash(current)
            if reviewed and news_hash(reviewed) is None:
                finding["migrationRequired"] = True
            old = {item["id"]: item for item in reviewed.get("newsItems", [])} if reviewed else {}
            items = current.get("newsItems", [])
            finding["newItems"] = [item for item in items if item["id"] not in old]
            finding["updatedItems"] = [item for item in items if item["id"] in old and item != old[item["id"]]]
        result.append(finding)
    return result


def commit(update, cycle):
    if update.get("stateBlocked"):
        raise ValueError("source-watch state is unreadable; captures retained without replacing state")
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
            if name == "news":
                captured = {**captured, "newsItems": news_records(payload)}
            latest = state["latestObserved"].get(name)
            if latest is None or not same_content(name, latest, captured):
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
