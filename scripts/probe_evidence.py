"""Parse retained XCTest evidence without discarding measurements or skip reasons."""
from __future__ import annotations

import hashlib
import pathlib
import re


def parse_log(text):
    totals = re.findall(r"Executed (\d+) tests?, with (?:(\d+) tests? skipped and )?(\d+) failures?", text)
    if not totals:
        raise ValueError("probe log contains no completed XCTest summary")
    results, skips = [], {}
    for line in text.splitlines():
        match = re.search(r"PROBE-RESULT name=(\S+) value=(.*)", line)
        if match:
            value, separator, detail = match[2].partition(" detail=")
            results.append({"name": match[1], "value": value, "detail": detail if separator else "",
                            "raw": match[0]})
        if "SKIPPED:" in line:
            test = re.search(r"-?(\[[^\]]+\])", line)
            if test:
                skips[test[1]] = {"test": test[1], "reason": "SKIPPED:" + line.split("SKIPPED:", 1)[1]}
    counts = dict(zip(("tests", "skipped", "failures"), (int(v or 0) for v in totals[-1])))
    if counts["skipped"] != len(skips):
        raise ValueError(f"summary has {counts['skipped']} skips but retained log explains {len(skips)}")
    return {**counts, "results": results, "skipReasons": list(skips.values())}


def summarize(log, run_directory, topology, excluded_tests=()):
    log = pathlib.Path(log)
    data = log.read_bytes()
    parsed = parse_log(data.decode("utf-8", errors="replace"))
    return {"topology": {**topology, **{k: parsed[k] for k in ("tests", "skipped", "failures")}},
            "results": parsed["results"], "skipReasons": parsed["skipReasons"],
            "runDirectory": str(run_directory), "excludedTests": list(excluded_tests),
            "sources": [{"path": str(log), "sha256": hashlib.sha256(data).hexdigest()}]}
