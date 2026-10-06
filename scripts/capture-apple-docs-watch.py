#!/usr/bin/env python3
"""Capture the ImageReference documentation watch pages with durable hashes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.request
import urllib.error


DEFAULT_OVERVIEW = "https://developer.apple.com/documentation/foundationmodels/imagereference.md"
DEFAULT_MEMBER = (
    "https://developer.apple.com/documentation/foundationmodels/imagereference/"
    "resolved%28in%3A%29.md"
)


def read_source(source: str) -> bytes:
    if source.startswith(("https://", "http://")):
        request = urllib.request.Request(source, headers={"User-Agent": "corpus-freshness/1"})
        with urllib.request.urlopen(request, timeout=40) as response:
            return response.read()
    return pathlib.Path(source).read_bytes()


def spellings(payload: bytes) -> list[str]:
    text = payload.decode("utf-8")
    return sorted(set(re.findall(r"\bfunc\s+(resolve|resolved)\s*\(in\b", text)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--overview-source", default=DEFAULT_OVERVIEW)
    parser.add_argument("--member-source", default=DEFAULT_MEMBER)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    captures = []
    observed = {}
    for name, source in (("overview", args.overview_source), ("member", args.member_source)):
        try:
            payload = read_source(source)
            methods = spellings(payload)
        except (OSError, UnicodeError, urllib.error.URLError) as error:
            captures.append({"name": name, "source": source, "status": "failed",
                             "error": f"{type(error).__name__}: {error}"})
            continue
        destination = args.output / f"{name}.md"
        destination.write_bytes(payload)
        observed[name] = methods
        captures.append({
            "name": name,
            "status": "captured",
            "source": source,
            "path": destination.name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "methodSpellings": methods,
        })

    agrees = observed == {"overview": ["resolved"], "member": ["resolved"]}
    manifest = {
        "schemaVersion": 1,
        "capturedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "expectedCurrentSpelling": "resolved",
        "pagesAgree": agrees,
        "captures": captures,
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True))
    return 0 if agrees else 1


if __name__ == "__main__":
    raise SystemExit(main())
