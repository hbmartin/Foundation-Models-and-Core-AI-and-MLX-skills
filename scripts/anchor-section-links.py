#!/usr/bin/env python3
"""Add and verify GitHub anchors on section-scoped part-router links.

Part READMEs use labels such as ``[8.1 §4.4](references/01-guide.md)`` to
route readers into large reference guides. A section label without a fragment
still opens the whole file, defeating that routing contract. This tool derives
the fragment from the first cited section, using the repository's GitHub-faithful
slugger and the complete heading namespace of the target document.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import re
import sys

from mdlinks import SCHEME, iter_lines
from mdslug import slugify, unique_slug


SECTION_LINK = re.compile(
    r"\[(?P<label>[^]\n]*§[^]\n]*)\]"
    r"\((?P<destination>[^)#\n]*\.md)(?:#(?P<fragment>[^)\s]+))?\)"
)
SECTION_NUMBER = re.compile(r"§\s*(\d+(?:\.\d+)*)")
HEADING = re.compile(
    r"^ {0,3}#{1,6}[ \t]+(?P<text>.*?)(?:[ \t]+#+[ \t]*)?$"
)


class SectionLinkError(ValueError):
    """A section-scoped link cannot be mapped to exactly one heading."""


def heading_anchors(path: Path) -> list[tuple[str, str]]:
    """Return rendered heading text and GitHub anchor, including duplicates."""
    anchors: list[tuple[str, str]] = []
    used: set[str] = set()
    next_suffix: defaultdict[str, int] = defaultdict(int)
    for body, _newline, inside_fence in iter_lines(path.read_text(encoding="utf-8")):
        if inside_fence:
            continue
        match = HEADING.match(body)
        if not match:
            continue
        heading = match.group("text").strip()
        anchor = unique_slug(slugify(heading), used, next_suffix)
        anchors.append((heading, anchor))
    return anchors


def expected_anchor(label: str, target: Path) -> str:
    section = SECTION_NUMBER.search(label)
    if not section:
        raise SectionLinkError(f"section label has no numeric section: {label!r}")
    number = section.group(1)
    # Most guides use `## 3. Title`; Part 11 intentionally uses `## §3 — Title`.
    prefix = re.compile(
        rf"^(?:§\s*)?{re.escape(number)}"
        rf"(?=$|\s|\.(?!\d)|\s*[—:])"
    )
    matches = [anchor for heading, anchor in heading_anchors(target) if prefix.match(heading)]
    if len(matches) != 1:
        raise SectionLinkError(
            f"{label!r} maps to {len(matches)} headings in {target}; expected exactly one"
        )
    return matches[0]


def process_part_readme(path: Path, *, write: bool) -> tuple[int, list[str]]:
    original = path.read_text(encoding="utf-8")
    errors: list[str] = []
    changes = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changes
        label = match.group("label")
        destination = match.group("destination")
        if SCHEME.match(destination):
            return match.group(0)
        target = (path.parent / destination).resolve()
        if not target.is_file():
            errors.append(f"{path}: missing section-link target {destination}")
            return match.group(0)
        try:
            expected = expected_anchor(label, target)
        except SectionLinkError as error:
            errors.append(f"{path}: {error}")
            return match.group(0)
        actual = match.group("fragment")
        if actual == expected:
            return match.group(0)
        if not write:
            errors.append(
                f"{path}: [{label}]({destination}) needs fragment #{expected}"
            )
            return match.group(0)
        changes += 1
        return f"[{label}]({destination}#{expected})"

    rendered = "".join(
        body + newline
        if inside_fence
        else SECTION_LINK.sub(replace, body) + newline
        for body, newline, inside_fence in iter_lines(original)
    )
    if write and rendered != original:
        path.write_text(rendered, encoding="utf-8")
    return changes, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guides", nargs="?", type=Path, default=Path("guides"))
    parser.add_argument(
        "--write", action="store_true", help="add or correct fragments in place"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = sorted(args.guides.glob("part-*/README.md"))
    if not files:
        print(f"no part READMEs found under {args.guides}", file=sys.stderr)
        return 2
    total = 0
    errors: list[str] = []
    for path in files:
        changed, file_errors = process_part_readme(path, write=args.write)
        total += changed
        errors.extend(file_errors)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    action = "updated" if args.write else "verified"
    print(f"{action} {len(files)} part README(s); {total} link(s) changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
