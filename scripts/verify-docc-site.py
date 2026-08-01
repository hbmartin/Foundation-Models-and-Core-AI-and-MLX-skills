#!/usr/bin/env python3
"""Verify a static DocC archive against build-docc-site.py's manifest."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import posixpath
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys
from urllib.parse import unquote, urlparse


class VerificationError(RuntimeError):
    pass


BASE_URL = re.compile(r"\bbaseUrl\s*=\s*['\"](?P<url>[^'\"]+)['\"]")
LINK_ASSET_RELATIONSHIPS = {
    "icon",
    "mask-icon",
    "modulepreload",
    "preload",
    "stylesheet",
}
TEMPLATE_FILES = {"index.html", "index-template.html"}


class PageAssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attributes):
        values = dict(attributes)
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
            self.assets.append(values["src"])
        elif tag == "link" and values.get("href"):
            relationships = set(values.get("rel", "").casefold().split())
            if relationships & LINK_ASSET_RELATIONSHIPS:
                self.assets.append(values["href"])
            if "stylesheet" in relationships:
                self.stylesheets.append(values["href"])


def local_asset_path(
    site: Path, html_path: Path, asset_url: str, base_url: str | None
) -> Path | None:
    parsed = urlparse(asset_url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None

    decoded = unquote(parsed.path)
    if decoded.startswith("/"):
        if not base_url:
            raise VerificationError(
                f"{html_path}: root-relative asset has no DocC baseUrl: {asset_url}"
            )
        base_path = urlparse(base_url).path
        if not base_path.endswith("/"):
            base_path += "/"
        if not decoded.startswith(base_path):
            raise VerificationError(
                f"{html_path}: asset is outside DocC baseUrl {base_path!r}: {asset_url}"
            )
        relative = decoded[len(base_path) :]
    else:
        html_directory = html_path.parent.relative_to(site).as_posix()
        relative = posixpath.join(html_directory, decoded)

    normalized = posixpath.normpath(relative)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise VerificationError(f"{html_path}: unsafe local asset path: {asset_url}")
    return site.joinpath(*PurePosixPath(normalized).parts)


def verify_html_assets(site: Path) -> int:
    found_assets: set[Path] = set()
    for html_path in sorted(site.rglob("*.html")):
        text = html_path.read_text(encoding="utf-8")
        parser = PageAssetParser()
        parser.feed(text)
        if not parser.scripts:
            raise VerificationError(f"{html_path}: missing DocC JavaScript entry point")
        if not parser.stylesheets:
            raise VerificationError(f"{html_path}: missing DocC stylesheet")

        base_match = BASE_URL.search(text)
        base_url = base_match.group("url") if base_match else None
        for asset_url in parser.assets:
            asset = local_asset_path(site, html_path, asset_url, base_url)
            if asset is None:
                continue
            if not asset.is_file():
                raise VerificationError(
                    f"{html_path}: missing referenced browser asset: {asset_url}"
                )
            if asset.stat().st_size == 0:
                raise VerificationError(
                    f"{html_path}: referenced browser asset is empty: {asset_url}"
                )
            found_assets.add(asset)
    return len(found_assets)


def verify_renderer_assets(site: Path, renderer: Path) -> None:
    renderer = renderer.resolve()
    for template_name in TEMPLATE_FILES:
        template = renderer / template_name
        if not template.is_file() or template.stat().st_size == 0:
            raise VerificationError(f"invalid DocC renderer template: {template}")

    renderer_assets = [
        path
        for path in sorted(renderer.rglob("*"))
        if path.is_file() and path.relative_to(renderer).as_posix() not in TEMPLATE_FILES
    ]
    if not renderer_assets:
        raise VerificationError(f"DocC renderer has no browser assets: {renderer}")

    for source in renderer_assets:
        relative = source.relative_to(renderer)
        target = site / relative
        if not target.is_file():
            raise VerificationError(f"missing DocC renderer asset: {relative}")
        if source.read_bytes() != target.read_bytes():
            raise VerificationError(f"DocC renderer asset differs from source: {relative}")

    links = [path for path in site.rglob("*") if path.is_symlink()]
    if links:
        examples = ", ".join(str(path.relative_to(site)) for path in links[:5])
        raise VerificationError(f"site contains links that Pages cannot publish: {examples}")


def walk_urls(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "url" and isinstance(child, str):
                yield child
            yield from walk_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_urls(child)


def verify(
    site: Path, manifest_path: Path, renderer: Path | None = None
) -> tuple[int, int, int]:
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
            parsed = urlparse(value)
            if (
                not parsed.scheme
                and not parsed.netloc
                and parsed.path.casefold().endswith(".md")
            ):
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
    asset_count = verify_html_assets(site)
    if renderer is not None:
        verify_renderer_assets(site, renderer)
    return len(expected), len(list(site.rglob("*.html"))), asset_count


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--renderer",
        type=Path,
        help="Pinned DocC renderer directory whose assets must exactly match the site",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        page_count, html_count, asset_count = verify(
            arguments.site, arguments.manifest, arguments.renderer
        )
    except (VerificationError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"Verified {page_count} DocC pages, {html_count} static HTML files, "
        f"and {asset_count} referenced browser assets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
