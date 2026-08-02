#!/usr/bin/env python3
"""Verify a generated skills/ tree independently of the generator.

Companion to scripts/build-skills.py in the same way scripts/verify-docc-site.py
is to the DocC adapter: it re-derives what it can from the committed output
rather than trusting the builder's own bookkeeping.

The check that matters most is relocation. `npx skills add` installs a single
skill directory into an agent-specific project path, detached from this
repository, so a link that resolves here but reaches outside the skill root
resolves to nothing once installed. Every containment and anchor check therefore
runs against temporary Codex and Claude Code copies as well as the tree in place.
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
from mdlinks import (  # noqa: E402
    SCHEME,
    InlineScanner,
    iter_lines,
    sha256,
    split_destination,
)
from mdslug import slugify, unique_slug  # noqa: E402

HTML_ANCHOR = re.compile(r'<a\s+(?:name|id)\s*=\s*"([^"]+)"')
# A reference-link definition, but never a footnote definition: '[^x]:' shares
# the shape and is not a link.
REFERENCE_DEFINITION = re.compile(r"^ {0,3}\[(?!\^)[^\]]+\]:\s*(\S.*)$")
# A [text][label] usage; [text][] and [label] shortcut forms are not used here.
REFERENCE_USAGE = re.compile(r"\[[^\]]*\]\[([^\]]+)\]")
CODE_SPAN = re.compile(r"`+[^`]*`+")
FRONTMATTER_SCALAR = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_FRONTMATTER_FIELDS = {"name", "description"}

# Stated here rather than imported from the generator: a verifier that asks the
# generator what it should have produced cannot catch the generator weakening it.
REQUIRED_MARKERS = (
    "✅ **VERIFIED**",
    "🟡 **RECONSTRUCTED**",
    "🟠 **Suggestive**",
    "🔴 **GAP**",
    "⚠️ **SILENT FAILURE**",
)

MAX_FRONTMATTER_CHARS = 1000
MAX_DESCRIPTION_CHARS = 1024
MAX_SKILL_NAME_CHARS = 64
MAX_BODY_LINES = 260
MIN_TRIGGER_EVALS_PER_CLASS = 4


class VerificationError(RuntimeError):
    """A defect in the generated tree."""


def parse_frontmatter(text: str, label: str) -> tuple[dict[str, str], int, str]:
    """Read a scalar-only YAML frontmatter block.

    Returns (fields, body line count, the raw block). The raw block is what the
    agent actually holds in context, so it — not the sum of the decoded values —
    is what the resident-context budget is measured against: quoting and
    escaping a description makes the rendered YAML longer than its text.

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
        if key in fields:
            raise VerificationError(f"{label}:{number}: duplicate frontmatter key {key!r}")
        if raw[:1] in ("|", ">", "&", "*", "[", "{"):
            raise VerificationError(f"{label}:{number}: unsupported YAML construct in {key!r}")
        if len(raw) >= 2 and raw[0] == raw[-1] == '"':
            raw = raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        fields[key] = raw
    return fields, len(lines) - end - 1, "\n".join(lines[: end + 1])


def verify_openai_metadata(skill_dir: Path, name: str) -> None:
    """Check the generated OpenAI UI metadata without adding a YAML dependency."""
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        raise VerificationError(f"{name}: no agents/openai.yaml")
    text = path.read_text(encoding="utf-8")

    def quoted(field: str) -> str:
        match = re.search(rf"^  {re.escape(field)}:\s*(.+)$", text, re.M)
        if not match:
            raise VerificationError(f"{name}: agents/openai.yaml lacks {field}")
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError as error:
            raise VerificationError(
                f"{name}: agents/openai.yaml {field} must be a quoted string: {error}"
            )
        if not isinstance(value, str) or not value:
            raise VerificationError(f"{name}: agents/openai.yaml {field} must be non-empty")
        return value

    quoted("display_name")
    short = quoted("short_description")
    if not 25 <= len(short) <= 64:
        raise VerificationError(
            f"{name}: agents/openai.yaml short_description must be 25-64 characters"
        )
    prompt = quoted("default_prompt")
    if f"${name}" not in prompt:
        raise VerificationError(
            f"{name}: agents/openai.yaml default_prompt must mention ${name}"
        )
    if "\npolicy:\n  allow_implicit_invocation: true\n" not in text:
        raise VerificationError(
            f"{name}: agents/openai.yaml must allow implicit invocation"
        )


def verify_trigger_evals(skill_dir: Path, name: str) -> int:
    """Validate portable positive and near-miss negative trigger fixtures."""
    path = skill_dir / "evals" / "eval_queries.json"
    if not path.is_file():
        raise VerificationError(f"{name}: no evals/eval_queries.json")
    try:
        queries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VerificationError(f"{name}: invalid eval_queries.json: {error}")
    if not isinstance(queries, list):
        raise VerificationError(f"{name}: eval_queries.json must contain a list")
    seen: set[str] = set()
    counts = {True: 0, False: 0}
    for number, item in enumerate(queries, 1):
        if not isinstance(item, dict) or set(item) != {"query", "should_trigger"}:
            raise VerificationError(
                f"{name}: eval query {number} must contain only query and should_trigger"
            )
        query, should_trigger = item["query"], item["should_trigger"]
        if not isinstance(query, str) or not query.strip():
            raise VerificationError(f"{name}: eval query {number} has no query text")
        if query in seen:
            raise VerificationError(f"{name}: duplicate eval query {query!r}")
        seen.add(query)
        if not isinstance(should_trigger, bool):
            raise VerificationError(
                f"{name}: eval query {number} should_trigger must be boolean"
            )
        counts[should_trigger] += 1
    for expected, count in counts.items():
        if count < MIN_TRIGGER_EVALS_PER_CLASS:
            raise VerificationError(
                f"{name}: needs at least {MIN_TRIGGER_EVALS_PER_CLASS} eval queries with "
                f"should_trigger={str(expected).lower()}"
            )
    return len(queries)


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
    """Every link destination in the document, inline and reference-style.

    The corpus authors inline links exclusively today, but a reference
    definition is just as capable of escaping the skill root, and this verifier
    is the safety net that has to notice.
    """
    found: list[str] = []

    def collect(inner: str) -> str:
        parsed = split_destination(inner)
        if parsed:
            found.append(parsed[0])
        return inner

    labels: set[str] = set()
    used_labels: list[str] = []
    scanner = InlineScanner()
    for body, _, inside_fence in iter_lines(text):
        if inside_fence:
            scanner.reset()
            continue
        scanner.scan(body, collect)
        # Strip inline code first: `matrix[i][j]` is a code span, not a
        # reference link, and the corpus is full of them.
        used_labels += [
            label
            for label in REFERENCE_USAGE.findall(CODE_SPAN.sub("", body))
            if label.strip() and not label.startswith("^")
        ]
        definition = REFERENCE_DEFINITION.match(body)
        if definition:
            labels.add(definition.group(0).split("]:")[0].lstrip(" [").casefold())
            destination = definition.group(1).strip()
            if destination.startswith("<") and destination.endswith(">"):
                destination = destination[1:-1]
            found.append(destination.split()[0] if destination.split() else "")
    undefined = sorted(
        {label for label in used_labels if label.casefold() not in labels}
    )
    if undefined:
        raise VerificationError(
            f"reference-style link labels with no definition: {undefined}"
        )
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
                if joined == ".." or joined.startswith("../"):
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} escapes the skill root; "
                        "it would dangle once installed into an agent skills directory"
                    )
                target = root / joined
                if not target.is_file():
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} has no file at {joined}"
                    )
            if fragment:
                if target not in anchor_cache:
                    anchor_cache[target] = anchors_of(target)
                decoded_fragment = unquote(fragment)
                if decoded_fragment not in anchor_cache[target]:
                    raise VerificationError(
                        f"{label}/{relative}: link {destination!r} has no matching anchor "
                        f"in {target.relative_to(root).as_posix()}"
                    )
            checked += 1
    return checked


def verify(skills_root: Path, manifest_path: Path) -> dict:
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
    total_evals = 0
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
        fields, body_lines, frontmatter = parse_frontmatter(text, f"{name}/SKILL.md")
        unexpected = set(fields) - ALLOWED_FRONTMATTER_FIELDS
        if unexpected:
            raise VerificationError(
                f"{name}: non-portable frontmatter fields {sorted(unexpected)}; "
                "put host metadata under agents/"
            )
        if len(fields.get("name", "")) > MAX_SKILL_NAME_CHARS or not SKILL_NAME.fullmatch(
            fields.get("name", "")
        ):
            raise VerificationError(f"{name}: frontmatter name must match {SKILL_NAME.pattern}")
        if fields["name"] != name:
            raise VerificationError(
                f"{name}: frontmatter name {fields['name']!r} must equal the directory name"
            )
        if not fields.get("description"):
            raise VerificationError(f"{name}: a description is required to trigger the skill")
        if len(fields["description"]) > MAX_DESCRIPTION_CHARS:
            raise VerificationError(
                f"{name}: description exceeds {MAX_DESCRIPTION_CHARS} characters"
            )
        # The whole rendered block, matching what build-skills.py budgets. Summing
        # the decoded field values would undercount by the quoting, the escapes and
        # the key names, and let an oversized block through.
        budget = len(frontmatter)
        if budget > MAX_FRONTMATTER_CHARS:
            raise VerificationError(
                f"{name}: frontmatter is {budget} chars, over the {MAX_FRONTMATTER_CHARS} "
                "budget; it is resident in context for every session"
            )
        if body_lines > MAX_BODY_LINES:
            raise VerificationError(
                f"{name}: SKILL.md body is {body_lines} lines, over {MAX_BODY_LINES}"
            )
        missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
        if missing:
            raise VerificationError(
                f"{name}: SKILL.md is missing evidence markers {missing}. Every class "
                "must be present or the model will flatten a reconstruction into fact."
            )
        start = text.index(REQUIRED_MARKERS[0])
        end = text.find("\n## ", text.index(REQUIRED_MARKERS[-1]))
        if end < 0:
            raise VerificationError(
                f"{name}: the evidence legend is not followed by a '## ' section, so its "
                "extent cannot be compared across skills"
            )
        legends.add(text[start:end])
        for markdown in sorted(skill_dir.rglob("*.md")):
            markdown_text = markdown.read_text(encoding="utf-8")
            for token in ("`Grep`", "`WebFetch`"):
                if token in markdown_text:
                    relative = markdown.relative_to(skill_dir)
                    raise VerificationError(
                        f"{name}: {relative} uses host-specific tool name {token}"
                    )
        verify_openai_metadata(skill_dir, name)
        total_evals += verify_trigger_evals(skill_dir, name)

        # In place, then again from a detached copy, which is what installation
        # produces and where a link reaching outside the skill would dangle.
        total_links += check_links(skill_dir, name)
        with tempfile.TemporaryDirectory() as directory:
            for agent_dir in (".agents", ".claude"):
                relocated = Path(directory) / agent_dir / "skills" / name
                relocated.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(skill_dir, relocated)
                check_links(relocated, f"{name} (installed under {agent_dir})")

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

    return {
        "skills": len(names),
        "files": len(on_disk),
        "links": total_links,
        "trigger_evals": total_evals,
    }


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
        f"{summary['links']} links, {summary['trigger_evals']} trigger evals"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
