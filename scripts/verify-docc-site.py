#!/usr/bin/env python3
"""Verify a static DocC archive against build-docc-site.py's manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


class VerificationError(RuntimeError):
    pass


def walk_urls(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "url" and isinstance(child, str):
                yield child
            yield from walk_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_urls(child)


def verify(site: Path, manifest_path: Path) -> tuple[int, int]:
    site = site.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {page["identifier"].casefold() for page in manifest["pages"]}
    data_root = site / "data" / "documentation"
    if not (site / "index.html").is_file():
        raise VerificationError(f"missing static-site entry point: {site / 'index.html'}")
    if not data_root.is_dir():
        raise VerificationError(f"missing DocC render data: {data_root}")

    found: dict[str, Path] = {}
    broken_markdown_urls: list[tuple[Path, str]] = []
    for path in sorted(data_root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        identifier = payload.get("identifier", {}).get("url")
        if not identifier:
            continue
        leaf = identifier.rstrip("/").rsplit("/", 1)[-1].casefold()
        if leaf in found:
            raise VerificationError(f"duplicate rendered identifier {leaf}: {found[leaf]} and {path}")
        found[leaf] = path

        for value in walk_urls(payload):
            lowered = value.casefold()
            if ".md" in lowered and "://" not in lowered and not lowered.startswith("doc:"):
                broken_markdown_urls.append((path, value))

        rendered_relative = path.relative_to(site / "data").with_suffix("")
        html = site / rendered_relative / "index.html"
        if not html.is_file():
            raise VerificationError(f"missing static HTML route for {path}: {html}")

    missing = sorted(expected - set(found))
    unexpected = sorted(set(found) - expected)
    if missing:
        raise VerificationError(f"missing rendered pages: {', '.join(missing)}")
    if unexpected:
        raise VerificationError(f"unexpected rendered pages: {', '.join(unexpected)}")
    if broken_markdown_urls:
        examples = ", ".join(f"{path.name}: {value}" for path, value in broken_markdown_urls[:5])
        raise VerificationError(f"relative .md URLs survived DocC conversion: {examples}")
    return len(expected), len(list(site.rglob("*.html")))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        page_count, html_count = verify(arguments.site, arguments.manifest)
    except (VerificationError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Verified {page_count} DocC pages and {html_count} static HTML files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
