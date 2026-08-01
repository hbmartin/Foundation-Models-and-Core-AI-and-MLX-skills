#!/usr/bin/env python3
"""Verify a generated skills/ tree independently of the generator.

Companion to scripts/build-skills.py in the same way scripts/verify-docc-site.py
is to the DocC adapter: it re-derives what it can from the committed output
rather than trusting the builder's own bookkeeping.

The check that matters most is relocation. `npx skills add` copies a single
skill directory into .claude/skills/<name>/, detached from this repository, so a
link that resolves here but reaches outside the skill root resolves to nothing
once installed. Every containment and anchor check therefore runs against a
temporary detached copy as well as against the tree in place.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys
import tempfile
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdlinks import SCHEME, iter_lines, scan_inline_links, sha256, split_destination  # noqa: E402
from mdslug import slugify, unique_slug  # noqa: E402

build_skills = None  # loaded lazily so --help works without importing the builder

HTML_ANCHOR = re.compile(r'<a\s+(?:name|id)\s*=\s*"([^"]+)"')
FRONTMATTER_SCALAR = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
SKILL_NAME = re.compile(r"^[a-z][a-z0-9-]*$")

MAX_FRONTMATTER_CHARS = 1000
MAX_BODY_LINES = 260


class VerificationError(RuntimeError):
    """A defect in the generated tree."""


def load_builder():
    global build_skills
    if build_skills is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "build_skills", Path(__file__).resolve().parent / "build-skills.py"
        )
        build_skills = importlib.util.module_from_spec(spec)
        # Register before executing: @dataclass resolves annotations through
        # sys.modules and fails on a module that is not there yet.
        sys.modules["build_skills"] = build_skills
        spec.loader.exec_module(build_skills)
    return build_skills


def parse_frontmatter(text: str, label: str) -> tuple[dict[str, str], int]:
    """Read a scalar-only YAML frontmatter block. Returns (fields, body line count).

    Deliberately strict rather than half-complete: this repository has no
    third-party dependencies, so rather than approximate YAML, reject anything
    that is not a plain `key: value` scalar and let the build fail loudly.
    """
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise VerificationError(f"{label}: must start with a '---' frontmatter fence")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise VerificationError(f"{label}: frontmatter is not closed")
    fields: dict[str, str] = {}
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip():
            continue
        match = FRONTMATTER_SCALAR.match(line)
        if not match:
            raise VerificationError(
                f"{label}:{number}: frontmatter must be flat 'key: value' scalars, got {line!r}"
            )
        key, raw = match.group(1), match.group(2).strip()
        if raw[:1] in ("|", ">", "&", "*", "[", "{"):
            raise VerificationError(f"{label}:{number}: unsupported YAML construct in {key!r}")
        if len(raw) >= 2 and raw[0] == raw[-1] == '"':
            raw = raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        fields[key] = raw
    return fields, len(lines) - end - 1


def anchors_of(path: Path) -> set[str]:
    """Every fragment the file can be addressed by.

    Two namespaces are live at once: GitHub heading slugs, with duplicates
    suffixed the way GitHub suffixes them, and the hand-written `<a name>`
    anchors the corpus uses where a slug would be awkward. A validator that
    knows only one of them reports false failures.
    """
    used: set[str] = set()
    next_suffix: dict[str, int] = defaultdict(int)
    anchors: set[str] = set()
    for body, _, inside_fence in iter_lines(path.read_text(encoding="utf-8")):
        if inside_fence:
            continue
        for match in HTML_ANCHOR.finditer(body):
            anchors.add(match.group(1))
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", body)
        if heading:
            anchors.add(unique_slug(slugify(heading.group(2)), used, next_suffix))
    return anchors


def destinations(text: str) -> list[str]:
    found: list[str] = []

    def collect(inner: str) -> str:
        parsed = split_destination(inner)
        if parsed:
            found.append(parsed[0])
        return inner

    for body, _, inside_fence in iter_lines(text):
        if not inside_fence:
            scan_inline_links(body, collect)
    return found


def check_links(root: Path, label: str) -> int:
    """Every relative link resolves to a real file inside `root`, at a real anchor."""
    checked = 0
    anchor_cache: dict[Path, set[str]] = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        for destination in destinations(path.read_text(encoding="utf-8")):
            if (
                not destination
                or destination.startswith("//")
                or SCHEME.match(destination)
            ):
                continue
            path_text, _, fragment = destination.partition("#")
            target = path
            if path_text:
                decoded = unquote(path_text.partition("?")[0])
                if decoded.startswith("/"):
                    raise VerificationError(
                        f"{label}/{relative}: absolute path {destination!r} cannot resolve "
                        "once the skill is installed elsewhere"
                    )
                joined = posixpath.normpath(
                    posixpath.join(posixpath.dirname(relative), decoded)
                )
                if joined.startswith(".."):
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} escapes the skill root; "
                        "it would dangle once installed into .claude/skills/"
                    )
                target = root / joined
                if not target.is_file():
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} has no file at {joined}"
                    )
            if fragment:
                if target not in anchor_cache:
                    anchor_cache[target] = anchors_of(target)
                if fragment not in anchor_cache[target]:
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} has no matching anchor "
                        f"in {target.relative_to(root).as_posix()}"
                    )
            checked += 1
    return checked


def verify(skills_root: Path, manifest_path: Path) -> dict:
    builder = load_builder()
    if not skills_root.is_dir():
        raise VerificationError(f"{skills_root} is not a directory")
    if (skills_root / "SKILL.md").exists():
        raise VerificationError(
            f"{skills_root}/SKILL.md would shadow every nested skill and make "
            "`npx skills add` vendor the whole repository"
        )

    for path in skills_root.rglob("*"):
        if path.is_symlink():
            raise VerificationError(f"{path}: symlinks do not survive installation")

    names = sorted(
        entry.name for entry in skills_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
    if not names:
        raise VerificationError(f"{skills_root}: no skills found")

    legends: set[str] = set()
    total_links = 0
    for name in names:
        skill_dir = skills_root / name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise VerificationError(f"{name}: no SKILL.md")
        nested = [
            path for path in skill_dir.rglob("SKILL.md") if path != skill_file
        ]
        if nested:
            raise VerificationError(
                f"{name}: nested SKILL.md at {nested[0]} is shadowed by the "
                "shallower one during discovery"
            )
        text = skill_file.read_text(encoding="utf-8")
        fields, body_lines = parse_frontmatter(text, f"{name}/SKILL.md")
        if not SKILL_NAME.match(fields.get("name", "")):
            raise VerificationError(f"{name}: frontmatter name must match {SKILL_NAME.pattern}")
        if fields["name"] != name:
            raise VerificationError(
                f"{name}: frontmatter name {fields['name']!r} must equal the directory name"
            )
        if not fields.get("description"):
            raise VerificationError(f"{name}: a description is required to trigger the skill")
        budget = (
            len(fields["name"]) + len(fields["description"]) + len(fields.get("when_to_use", ""))
        )
        if budget > MAX_FRONTMATTER_CHARS:
            raise VerificationError(
                f"{name}: frontmatter is {budget} chars, over the {MAX_FRONTMATTER_CHARS} "
                "budget; it is resident in context for every session"
            )
        if body_lines > MAX_BODY_LINES:
            raise VerificationError(
                f"{name}: SKILL.md body is {body_lines} lines, over {MAX_BODY_LINES}"
            )
        if builder.EVIDENCE_LEGEND.rstrip() not in text:
            raise VerificationError(
                f"{name}: SKILL.md does not carry the evidence-marker legend verbatim"
            )
        legends.add(builder.EVIDENCE_LEGEND.rstrip())

        # In place, then again from a detached copy, which is what installation
        # produces and where a link reaching outside the skill would dangle.
        total_links += check_links(skill_dir, name)
        with tempfile.TemporaryDirectory() as directory:
            relocated = Path(directory) / ".claude" / "skills" / name
            relocated.parent.mkdir(parents=True)
            shutil.copytree(skill_dir, relocated)
            check_links(relocated, f"{name} (installed)")

    if len(legends) != 1:
        raise VerificationError("skills disagree about the evidence-marker legend")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = manifest.get("files", {})
    on_disk = {
        path.relative_to(skills_root).as_posix(): sha256(path)
        for path in sorted(skills_root.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if set(listed) != set(on_disk):
        missing = sorted(set(listed) - set(on_disk))
        extra = sorted(set(on_disk) - set(listed))
        raise VerificationError(
            f"manifest disagrees with the tree; missing={missing[:5]} extra={extra[:5]}"
        )
    for relative, digest in sorted(listed.items()):
        if on_disk[relative] != digest:
            raise VerificationError(f"{relative}: sha256 does not match the manifest")

    return {"skills": len(names), "files": len(on_disk), "links": total_links}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skills", type=Path, default=Path("skills"))
    parser.add_argument("--manifest", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    manifest = arguments.manifest or (arguments.skills / "skills-manifest.json")
    try:
        summary = verify(arguments.skills, manifest)
    except VerificationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"Verified {summary['skills']} skills, {summary['files']} files, "
        f"{summary['links']} links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
