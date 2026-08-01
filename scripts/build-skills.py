#!/usr/bin/env python3
"""Generate installable Claude Code skills from guides/.

The Markdown under guides/ is canonical; this adapter only reads it and writes
transformed copies into skills/, which is committed so `npx skills add
<owner>/<repo>` can resolve it. Layout, per skill:

    skills/<name>/SKILL.md                      generated router
    skills/<name>/references/<guides-relative>  copied part READMEs
    skills/<name>/references/API-INDEX.md       symbol slice
    skills/<name>/references/SILENT-FAILURES.md symptom slice
    skills/<name>/references/SECTION-MAPS.md    heading maps for the deep guides

references/ mirrors the guides-relative path layout on purpose. That keeps every
intra-document anchor and every link between two owned part READMEs valid
without rewriting, so the rewrite surface is only the links that genuinely leave
the skill.

The deep reference guides (94-232 KB each) are not copied. They are addressed by
GitHub URL with a resolved anchor, and SECTION-MAPS.md gives the anchor for every
section so a fetch can be aimed rather than dragged.

Context economics drive the SKILL.md shape: a skill's description sits in
Claude's context permanently, and its body persists for a whole session once
invoked, while everything under references/ costs nothing until read. So the body
is a router, never a copy of a guide.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, replace
import datetime
import importlib.util
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
from mdlinks import (  # noqa: E402  (path set above so the sibling modules resolve)
    SCHEME,
    github_url,
    is_within,
    iter_lines,
    page_target,
    scan_inline_links,
    sha256,
    source_snapshot,
    split_destination,
)
from mdslug import slugify, unique_slug  # noqa: E402

def _load_sibling(name: str, filename: str):
    """Import a kebab-case sibling script, as scripts/tests/ already does."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename
    )
    module = importlib.util.module_from_spec(spec)
    # Register before executing, so anything the sibling defines that resolves
    # annotations through sys.modules (dataclasses do) still works.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


extract_symbols = _load_sibling("extract_symbols", "extract-symbols.py")


PART_README = re.compile(r"^part-(\d{2})-[^/]+/README\.md$")
REFERENCE = re.compile(r"^part-(\d{2})-[^/]+/references/(\d{2})-[^/]+\.md$")
PART_TITLE = re.compile(r"^#\s+Part\s+(\d+)\s+—\s+(.+?)\s*$")
BOLD_LABEL = re.compile(r"^\*\*([A-Z][^:*]*):\*\*")
GUIDE_CARD = re.compile(r"^###\s+\[(\d+)\.(\d+)\s+—\s+(.+?)\]\(([^)]+)\)\s*$")
FOOTNOTE_REF = re.compile(r"\[\^[^\]]+\]")
GUIDE_LINK = re.compile(
    r"\[([^\]]*)\]\(https?://[^)\s]*/guides/part-\d{2}-[^)\s]*/references/[^)\s]*\)"
)
SENTENCE_END = re.compile(r"(?<=[a-zA-Z*)\]`\"])\.(?:\s|$)")

GENERATED_MARKER = ".generated-by-build-skills"
SKILL_NAME = re.compile(r"^[a-z][a-z0-9-]*$")

# Both caps are enforced here rather than left to review, because both are
# recurring context costs rather than one-off ones: the frontmatter triple is
# always resident, and the body persists for the rest of a session once invoked.
MAX_FRONTMATTER_CHARS = 1000
MAX_BODY_LINES = 260
API_LINKS_SHOWN = 4

FW_ORDER = [
    "FoundationModels", "CoreAI", "Evaluations", "MLX", "Speech", "AppIntents",
    "CoreSpotlight", "Vision", "Metal/MPP", "SwiftUI", "Media/Core*",
    "Swift/Foundation", "other",
]

# Emitted verbatim into every SKILL.md and asserted byte-identical by
# verify-skills.py. Dropping a class here teaches the model to promote a
# reconstruction or a directional measurement into a stated fact, which is the
# exact failure the corpus's conventions exist to prevent.
EVIDENCE_LEGEND = """\
Every non-obvious claim in `references/` carries one of these. Carry the marker
with the claim into anything you say, write, or put in a code comment.

- ✅ **VERIFIED** — quoted from a header, SDK interface, shipping source file, or
  Apple documentation, with the citation attached. Safe to rely on.
- 🟡 **RECONSTRUCTED** — the concept is attested, usually from a WWDC session, but
  the exact spelling is inferred. Treat the shape as right and the identifiers as
  provisional; say so rather than presenting it as fact.
- 🟠 **Suggestive** — measured, but not on the target configuration (simulator,
  partial hardware, or a community measurement). Directional only.
- 🔴 **GAP** — could not be verified. The callout names what is unknown and what
  would resolve it. Never guess past one.
- ⚠️ **SILENT FAILURE** — fails without throwing. Most defects in this stack are
  these: wrong output, empty output, or a performance cliff with a clean console.
"""

READ_PROTOCOL = """\
`references/` holds far more than fits in context. Never read a file whole —
route to the section you need:

1. **You have a symptom** (wrong output, empty result, silent no-op, perf cliff,
   something ignored) — `Grep` `references/SILENT-FAILURES.md` for words from what
   you actually observed. Entries are grouped by symptom and each links to the
   guide section that explains it.
2. **You have a symbol** (`LanguageModelSession`, `AIModel`, `mx.compile`, …) —
   `Grep` `references/API-INDEX.md`. The row shows whether the symbol appears in
   the captured 26.5 and 27.0 SDK interfaces; **blank in both columns means the
   spelling is not SDK-confirmed**, so treat it as provisional.
3. **You have a task** — use the triage table below, then the part README it
   points at.

The deep reference guides are not bundled. `references/SECTION-MAPS.md` lists
every section of every one with its anchor; fetch a single section rather than a
whole file.
"""


class SkillError(RuntimeError):
    """An actionable error in the source corpus, the manifest, or the output."""


@dataclass(frozen=True)
class GuidePage:
    source: Path
    relative: str
    role: str  # "root" | "index" | "part" | "guide"
    part: int | None
    guide: int | None
    title: str


@dataclass(frozen=True)
class SkillSpec:
    name: str
    title: str
    description: str
    when_to_use: str
    related: tuple[str, ...]
    owns: dict[int, frozenset[int] | None]  # part -> reference numbers, None = all
    max_triage_rows: int
    full_indexes: bool


@dataclass(frozen=True)
class GuideCard:
    guide_id: str
    part: int
    guide: int
    title: str
    destination: str
    abstract: str


@dataclass(frozen=True)
class PartRouter:
    part: int
    directory: str
    title: str
    version_floor: str
    audience: str
    warnings: tuple[tuple[str, str], ...]  # (heading text, anchor)
    triage_anchor: str
    triage_header: tuple[str, ...]
    triage_rows: tuple[str, ...]  # raw table rows, links already rewritten
    cards: tuple[GuideCard, ...]


def generation_date() -> str:
    """Today, or SOURCE_DATE_EPOCH, so a regenerated tree can be byte-compared."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is None:
        return datetime.date.today().isoformat()
    try:
        stamp = int(epoch)
    except ValueError:
        raise SkillError(f"SOURCE_DATE_EPOCH must be an integer, got {epoch!r}")
    return datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).date().isoformat()


def part_num(path: str) -> int:
    match = re.match(r"part-(\d+)", path)
    return int(match.group(1)) if match else 0


def guide_label(path: str) -> str:
    """The series' own N.M / N.README notation, matching scripts/build-indexes.py."""
    part = part_num(path)
    match = re.search(r"references/(\d+)-", path)
    if match:
        return f"{part}.{int(match.group(1))}"
    if path.endswith("README.md") and part:
        return f"{part}.README"
    return "root"


def guide_number(path: str) -> int | None:
    match = re.search(r"references/(\d+)-", path)
    return int(match.group(1)) if match else None


def close_code_spans(text: str) -> str:
    """Drop a trailing unbalanced code span.

    An odd backtick count means a truncation landed inside `` `code` ``. GitHub
    would then run the span to the next backtick anywhere later in the document,
    swallowing the rest of a table cell, so cut back to before the opener rather
    than emitting it.
    """
    if text.count("`") % 2 == 0:
        return text
    return text[: text.rfind("`")].rstrip()


def first_sentence(paragraph: str, limit: int = 240) -> str:
    """The first sentence of a wrapped Markdown paragraph, for a summary table.

    The lookbehind keeps version numbers intact: '27.0 and only 27.0. `import'
    splits, '26.0 on iOS' does not. Truncation falls back to a word boundary and
    never splits a code span, because these strings land in table cells where a
    dangling backtick corrupts the rest of the row.
    """
    text = " ".join(paragraph.split())
    match = SENTENCE_END.search(text)
    if match:
        text = text[: match.end()].strip()
    if len(text) <= limit:
        return close_code_spans(text)
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return close_code_spans(cut.rstrip()) + " …"


def first_title(text: str, source: Path) -> str:
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if not match:
            raise SkillError(f"{source}: first content line must be an H1 title")
        return match.group(1)
    raise SkillError(f"{source}: file is empty")


def discover_pages(source_root: Path) -> list[GuidePage]:
    pages: list[GuidePage] = []
    for source in sorted(source_root.rglob("*.md")):
        relative = source.relative_to(source_root).as_posix()
        title = first_title(source.read_text(encoding="utf-8"), source)
        part_match = PART_README.fullmatch(relative)
        reference_match = REFERENCE.fullmatch(relative)
        if relative == "README.md":
            role, part, guide = "root", None, None
        elif relative in ("API-INDEX.md", "SILENT-FAILURES.md"):
            role, part, guide = "index", None, None
        elif part_match:
            role, part, guide = "part", int(part_match.group(1)), None
        elif reference_match:
            role = "guide"
            part, guide = map(int, reference_match.groups())
        else:
            raise SkillError(
                f"{relative}: unrecognized guide path; expected a root/index page, a part "
                "README, or a numbered file under a part's references/ directory"
            )
        pages.append(GuidePage(source.resolve(), relative, role, part, guide, title))
    if not any(page.role == "root" for page in pages):
        raise SkillError(f"{source_root}: missing README.md")
    return pages


def load_manifest(path: Path, pages: list[GuidePage]) -> tuple[str, str, list[SkillSpec]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SkillError(f"{path}: {error}")
    if document.get("schema_version") != 1:
        raise SkillError(f"{path}: expected schema_version 1")
    repository = document.get("repository", {})
    url, branch = repository.get("url"), repository.get("branch")
    if not url or not branch:
        raise SkillError(f"{path}: repository.url and repository.branch are required")
    default_rows = document.get("defaults", {}).get("max_triage_rows", 18)

    available: dict[int, set[int]] = {}
    for page in pages:
        if page.role == "part":
            available.setdefault(page.part, set())
        elif page.role == "guide":
            available.setdefault(page.part, set()).add(page.guide)

    specs: list[SkillSpec] = []
    claimed: dict[tuple[int, int | None], str] = {}
    for entry in document.get("skills", []):
        name = entry.get("name", "")
        if any(spec.name == name for spec in specs):
            raise SkillError(f"{path}: duplicate skill name {name!r}")
        if not SKILL_NAME.match(name):
            raise SkillError(f"{path}: skill name {name!r} must match {SKILL_NAME.pattern}")
        if not entry.get("description"):
            raise SkillError(f"{path}: {name} needs a description; it is the whole trigger")
        budget = len(
            render_frontmatter(name, entry["description"], entry.get("when_to_use", ""))
        )
        if budget > MAX_FRONTMATTER_CHARS:
            raise SkillError(
                f"{path}: {name} renders {budget} chars of frontmatter, over the "
                f"{MAX_FRONTMATTER_CHARS} budget; it is always resident in context"
            )
        owns: dict[int, frozenset[int] | None] = {}
        for owned in entry.get("owns", []):
            part = owned["part"]
            if part not in available:
                raise SkillError(f"{path}: {name} claims part {part}, which has no README")
            references = owned.get("references")
            if references is None:
                owns[part] = None
                keys = [(part, None)] + [(part, n) for n in sorted(available[part])]
            else:
                unknown = set(references) - available[part]
                if unknown:
                    raise SkillError(
                        f"{path}: {name} claims part {part} references {sorted(unknown)}, "
                        "which do not exist"
                    )
                owns[part] = frozenset(references)
                keys = [(part, n) for n in sorted(references)]
            for key in keys:
                if key in claimed:
                    raise SkillError(
                        f"{path}: {key} is claimed by both {claimed[key]} and {name}; "
                        "ownership must be disjoint"
                    )
                claimed[key] = name
        specs.append(
            SkillSpec(
                name=name,
                title=entry.get("title", name),
                description=entry["description"],
                when_to_use=entry.get("when_to_use", ""),
                related=tuple(entry.get("related", ())),
                owns=owns,
                max_triage_rows=entry.get("max_triage_rows", default_rows),
                full_indexes=bool(entry.get("full_indexes")),
            )
        )

    names = {spec.name for spec in specs}
    for spec in specs:
        for sibling in spec.related:
            if sibling not in names:
                raise SkillError(f"{path}: {spec.name} relates to unknown skill {sibling!r}")

    # A part README with no owner would silently vanish from every skill, and an
    # unowned reference would vanish from the section maps, so demand a total cover.
    for part, references in sorted(available.items()):
        if (part, None) not in claimed and not any(
            (part, number) in claimed for number in references
        ):
            raise SkillError(f"{path}: part {part} is not owned by any skill")
        for number in sorted(references):
            if (part, None) not in claimed and (part, number) not in claimed:
                raise SkillError(f"{path}: part {part} reference {number} is not owned")
    return url, branch, specs


TRIAGE_REFERENCE = re.compile(r"references/(\d{2})-")


def owns_row(row: str, owned: frozenset[int] | None) -> bool:
    """Does this triage row cite only guides the skill carries?

    Three skills share part 16, so an unfiltered table routes a reader to a deep
    guide that is missing from their own section map. A row citing no guide at
    all (a plain cross-part pointer) is kept.
    """
    if owned is None:
        return True
    cited = {int(number) for number in TRIAGE_REFERENCE.findall(row)}
    return not cited or bool(cited & owned)


README_CARD_ANCHOR = re.compile(r"#(\d{1,2})(\d)--")


def owns_readme_entry(line: str, guide_id: str, spec: SkillSpec) -> bool:
    """Attribute a part-README index entry to the reference guide it describes.

    Three skills share the part-16 README, so every `16.README` entry would
    otherwise land in all three — putting speech symptoms in the evaluations
    skill. Those entries link to a card heading whose anchor starts with the
    card number (`#164--one-index-three-consumers…`), which is enough to tell
    which guide the entry is really about. Entries that point somewhere else in
    the README are part-wide and stay.
    """
    if not guide_id.endswith(".README"):
        return True
    part = int(guide_id.split(".")[0])
    owned = spec.owns.get(part)
    if owned is None:
        return True
    match = README_CARD_ANCHOR.search(line)
    if not match or int(match.group(1)) != part:
        return True
    return int(match.group(2)) in owned


def owns_page(spec: SkillSpec, page: GuidePage) -> bool:
    if page.role == "root":
        return spec.full_indexes
    if page.role == "index":
        return spec.full_indexes
    if page.part not in spec.owns:
        return False
    references = spec.owns[page.part]
    if page.role == "part":
        return True
    return references is None or page.guide in references


# ---------------------------------------------------------------- part parsing

def split_sections(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """(preamble lines, [(H2 heading text, body lines)]), fence-aware."""
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for body, _, inside_fence in iter_lines(text):
        if not inside_fence and body.startswith("## "):
            if current:
                sections.append(current)
            current = (body[3:].strip(), [])
            continue
        (current[1] if current else preamble).append(body)
    if current:
        sections.append(current)
    return preamble, sections


def bold_paragraph(lines: list[str], label: str) -> str:
    """The paragraph introduced by '**Label:**', joined, or ''."""
    collected: list[str] = []
    for line in lines:
        if collected:
            if not line.strip() or BOLD_LABEL.match(line):
                break
            collected.append(line)
            continue
        if line.startswith(f"**{label}:**"):
            collected.append(line[len(label) + 5 :].strip())
    return " ".join(collected).strip()


def parse_table(lines: list[str]) -> tuple[tuple[str, ...], list[str]]:
    """(header cells, data rows) of the first pipe table in `lines`."""
    rows = [line for line in lines if line.startswith("|")]
    if len(rows) < 3:
        return (), []
    header = tuple(cell.strip() for cell in rows[0].strip("|").split("|"))
    return header, rows[2:]


def parse_part_readme(page: GuidePage, text: str) -> PartRouter:
    """Parse a part README ordinally, refusing anything it does not recognize.

    Structure varies more than it looks: seven parts carry a '⚠️ Read this
    before …' H2 ahead of 'Why this part exists', part 12 suffixes its reading
    order heading, part 14 uses the singular 'The guide in this part', and part
    17 has no audience paragraph, no reading order, a 'five-minute triage'
    heading, and a triage table whose columns are reordered. Prefix-match the
    headings that vary and hard-error on anything unknown, so a future guide
    edit fails here rather than silently dropping content from a skill.
    """
    preamble, sections = split_sections(text)
    title_match = PART_TITLE.match(preamble[0] if preamble else "")
    if not title_match or int(title_match.group(1)) != page.part:
        raise SkillError(f"{page.relative}: first line must be '# Part {page.part} — <title>'")

    version_floor = bold_paragraph(preamble, "Version floor")
    if not version_floor:
        raise SkillError(f"{page.relative}: missing a '**Version floor:**' paragraph")

    warnings: list[tuple[str, str]] = []
    triage_anchor = ""
    triage_header: tuple[str, ...] = ()
    triage_rows: list[str] = []
    cards: list[GuideCard] = []
    seen_why = False
    for heading, body in sections:
        if heading == "Why this part exists":
            seen_why = True
        elif not seen_why:
            # The pre-"Why" H2s are evidence caveats, and they are routinely the
            # most load-bearing content in the part. Keep them addressable.
            warnings.append((heading, slugify(heading)))
        elif heading.startswith("Read this first"):
            triage_anchor = slugify(heading)
            triage_header, triage_rows = parse_table(body)
            if not triage_rows:
                raise SkillError(f"{page.relative}: '{heading}' has no triage table")
        elif re.fullmatch(r"The guides? in this part", heading):
            cards = parse_cards(page, body)
        elif heading.startswith("Reading order"):
            pass
        elif heading in (
            "What this part deliberately does not cover",
            "Sources for this part",
        ):
            pass
        else:
            raise SkillError(
                f"{page.relative}: unrecognized H2 '## {heading}'. Add a rule for it in "
                "parse_part_readme rather than letting its content vanish from the skill."
            )

    if not seen_why:
        raise SkillError(f"{page.relative}: missing '## Why this part exists'")
    if not triage_anchor:
        raise SkillError(f"{page.relative}: missing a '## Read this first…' section")
    if not cards:
        raise SkillError(f"{page.relative}: missing '## The guides in this part'")

    return PartRouter(
        part=page.part,
        directory=page.relative.split("/")[0],
        title=title_match.group(2),
        version_floor=version_floor,
        audience=bold_paragraph(preamble, "Who this is for"),
        warnings=tuple(warnings),
        triage_anchor=triage_anchor,
        triage_header=triage_header,
        triage_rows=tuple(triage_rows),
        cards=tuple(cards),
    )


def parse_cards(page: GuidePage, body: list[str]) -> list[GuideCard]:
    cards: list[GuideCard] = []
    pending: GuideCard | None = None
    abstract: list[str] = []
    for line in body:
        match = GUIDE_CARD.match(line)
        if match:
            if pending:
                cards.append(replace(pending, abstract=first_sentence(" ".join(abstract), 300)))
            part, guide = int(match.group(1)), int(match.group(2))
            if part != page.part:
                raise SkillError(f"{page.relative}: card {part}.{guide} is not in part {page.part}")
            pending = GuideCard(
                guide_id=f"{part}.{guide}",
                part=part,
                guide=guide,
                title=match.group(3),
                destination=match.group(4),
                abstract="",
            )
            abstract = []
            continue
        if pending and not abstract and line.startswith(">"):
            continue  # the reproduced callouts follow the abstract; skip them
        if pending and line.strip() and not line.startswith((">", "|", "#")):
            abstract.append(line.strip())
    if pending:
        cards.append(replace(pending, abstract=first_sentence(" ".join(abstract), 300)))
    return cards


# ------------------------------------------------------------- link rewriting

def resolve_destination(
    destination: str,
    page_relative: str,
    output_dir: str,
    owned: set[str],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
) -> str:
    """Map one link destination into the skill tree.

    `page_relative` is where the text was authored, which is what the link
    resolves against; `output_dir` is where the rewritten text will live inside
    the skill, which is what the result must be relative to. The two differ
    whenever content is lifted out of a part README into SKILL.md.

    Bundled targets stay relative — references/ mirrors the guides-relative
    layout, so a link between two bundled files keeps working. Everything else
    that resolves inside the repository becomes a GitHub URL with its fragment
    intact, and anything that resolves nowhere is an error, so a part that
    quietly lost its owner fails the build rather than shipping a dangling link
    into someone's project.
    """
    if not destination or destination.startswith(("#", "//")) or SCHEME.match(destination):
        return destination
    path_text, _, fragment = destination.partition("#")
    if not path_text:
        return destination
    decoded = unquote(path_text.partition("?")[0])
    source_dir = (source_root / page_relative).parent
    candidate = (source_dir / decoded).resolve()
    target = page_target(candidate, decoded)

    if is_within(target, source_root):
        relative = target.relative_to(source_root).as_posix()
        if relative in owned:
            inside = posixpath.relpath(f"references/{relative}", output_dir or ".")
            return f"{inside}#{fragment}" if fragment else inside
        if not target.exists():
            raise SkillError(
                f"{page_relative}: link {destination!r} points inside guides/ but "
                f"{relative} does not exist"
            )
        return github_url(target, repository_root, repository_url, branch, fragment)
    if is_within(candidate, repository_root) and candidate.exists():
        return github_url(candidate, repository_root, repository_url, branch, fragment)
    raise SkillError(f"{page_relative}: link {destination!r} does not resolve")


def rewrite_text(
    text: str,
    page_relative: str,
    output_dir: str,
    owned: set[str],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
) -> str:
    """Rewrite every link in a document, leaving fenced code byte-identical."""

    def rewrite_body(inner: str) -> str:
        parsed = split_destination(inner)
        if not parsed:
            return inner
        destination, suffix, angle_wrapped = parsed
        resolved = resolve_destination(
            destination, page_relative, output_dir, owned, source_root,
            repository_root, repository_url, branch,
        )
        if angle_wrapped:
            return f"<{resolved}>{suffix}"
        return f"{resolved}{suffix}"

    out: list[str] = []
    for body, newline, inside_fence in iter_lines(text):
        out.append(body if inside_fence else scan_inline_links(body, rewrite_body))
        out.append(newline)
    return "".join(out)


# ------------------------------------------------------------------ rendering

def render_silent_slice(
    text: str, spec: SkillSpec, owned_ids: set[str], date: str, series_url: str
) -> str:
    """Filter SILENT-FAILURES.md to this skill's guides.

    Slicing the rendered page is safe here in a way it is not for the symbol
    index: every bullet carries its guide id anchored at end of line, and no
    bullet is truncated. Anchor the match at '$' or a blurb ending '— 2.35 s'
    reads as a guide id.
    """
    entry = re.compile(r"^- \[.*\]\(.*\) — (root|\d{1,2}\.(?:README|\d{1,2}))( 🔇)?$")
    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    group: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = (line[3:].strip(), [])
            group = None
            continue
        if current is None:
            continue
        if line.startswith("**Part ") and line.endswith("**"):
            group = line
            continue
        match = entry.match(line)
        if not match:
            continue
        if match.group(1) not in owned_ids:
            continue
        if not owns_readme_entry(line, match.group(1), spec):
            continue
        if group:
            current[1].append("")
            current[1].append(group)
            current[1].append("")
            group = None
        current[1].append(line)
    if current:
        sections.append(current)

    kept = [(name, body) for name, body in sections if body]
    total = sum(1 for name, body in kept for line in body if line.startswith("- ["))
    out = [
        "# Silent-failure index — " + spec.title,
        "",
        f"**{total} ⚠️ callouts from the guide parts this skill covers, sorted by the symptom "
        "you would observe.** Most defects in this stack do not throw, so the symptom is what "
        "you start from.",
        "",
        f"> Sliced from the series index on {date}. The full index across all 17 parts is at "
        f"{series_url}. Generated — regenerate with `./scripts/build-skills.sh` rather than "
        "editing by hand.",
        "",
        "| Symptom | Entries |",
        "|---|---:|",
    ]
    for name, body in kept:
        count = sum(1 for line in body if line.startswith("- ["))
        out.append(f"| [{name}](#{slugify(name)}) | {count} |")
    for name, body in kept:
        out.append("")
        out.append(f"## {name}")
        out.extend(body)
    out += ["", "---", "", "🔇 = the guide marks this as an explicit **SILENT FAILURE** callout.", ""]
    return "\n".join(out)


def render_api_slice(
    rows: list[tuple], spec: SkillSpec, owned_ids: set[str], date: str,
    series_url: str, link_for: "callable",
) -> str:
    """Render this skill's symbols from uncapped counts.

    The noise floor, keep filter and framework grouping stay corpus-wide so the
    result is a true subset of the series index rather than a different index.
    Only the 'Covered in' column is narrowed, and its '+N more' is recomputed
    against owned guides.
    """
    by_framework: dict[str, list[tuple]] = {}
    total_series = 0
    for symbol, framework, total, nguides, in26, in27, guides in rows:
        if not (nguides >= 2 or total >= 4 or in26 or in27):
            continue
        total_series += 1
        pairs = []
        for chunk in guides.split(";"):
            path, _, count = chunk.rpartition(":")
            # By owned guide, not owned part: three skills share part 16, and a
            # slice that linked to guides the skill does not carry would send a
            # reader to a section map that has never heard of them.
            if path and guide_label(path) in owned_ids:
                pairs.append((path, int(count)))
        if not pairs:
            continue
        by_framework.setdefault(framework, []).append(
            (symbol, in26, in27, sorted(pairs, key=lambda pair: (-pair[1], pair[0])))
        )

    kept = sum(len(entries) for entries in by_framework.values())
    out = [
        "# API & symbol index — " + spec.title,
        "",
        f"**{kept} symbols, of {total_series} across the series, that the guide parts in this "
        "skill cover — with whether each exists in the captured 26.5 / 27.0 beta SDK "
        "interfaces.**",
        "",
        "> A `✓` means the bare symbol name appears in the corresponding captured "
        "`.swiftinterface` (a presence check, not a signature match — the guides carry the "
        "signature-level citations). **Blank in both columns means the spelling is not "
        "SDK-confirmed**: package types and C/ObjC-only API legitimately show neither, but so "
        "does a reconstruction. A symbol absent from this page may still be covered elsewhere "
        f"in the series — the full index is at {series_url}. Sliced on {date}; regenerate with "
        "`./scripts/build-skills.sh` rather than editing by hand.",
    ]
    for framework in FW_ORDER:
        entries = by_framework.get(framework, [])
        if not entries:
            continue
        entries.sort(key=lambda entry: entry[0].lstrip("@.").lower())
        out += ["", f"## {framework}  <sub>{len(entries)} symbols</sub>", ""]
        out.append("| Symbol | 26.5 | 27.0 | Covered in |")
        out.append("|---|:-:|:-:|---|")
        for symbol, in26, in27, pairs in entries:
            shown = [f"[{guide_label(path)}]({link_for(path)})" for path, _ in pairs[:API_LINKS_SHOWN]]
            more = len(pairs) - len(shown)
            tail = f" +{more} more" if more > 0 else ""
            out.append(
                f"| `{symbol}` | {'✓' if in26 else ''} | {'✓' if in27 else ''} | "
                f"{', '.join(shown)}{tail} |"
            )
    out.append("")
    return "\n".join(out)


def render_section_maps(
    spec: SkillSpec, routers: list[PartRouter], source_root: Path,
    repository_root: Path, repository_url: str, branch: str, date: str,
    to_references: "callable",
) -> str:
    """A heading map plus URL for every deep guide this skill covers.

    Derived from the real '## ' headings rather than each file's hand-written
    '## Contents', which one reference lacks entirely and which can drift.
    """
    out = [
        "# Section maps for the deep reference guides",
        "",
        "The deep guides are 94–232 KB each and are **not bundled** with this skill. Each one "
        "below gives its URL once, then every **top-level** (`##`) section as an anchor; a "
        "guide's own `## Contents` lists its subsections. To read a section, `WebFetch` "
        "`<url>#<anchor>` — never the whole file. If you need sustained access, ask the user "
        "before cloning the corpus (see SKILL.md).",
        "",
        f"> Generated {date} from the guide headings. Regenerate with "
        "`./scripts/build-skills.sh` rather than editing by hand.",
    ]
    for router in routers:
        owned = spec.owns[router.part]
        cards = [card for card in router.cards if owned is None or card.guide in owned]
        if not cards:
            continue
        out += ["", f"## Part {router.part} — {router.title}"]
        for card in cards:
            target = (source_root / router.directory / card.destination).resolve()
            if not target.exists():
                raise SkillError(f"part {router.part}: card {card.guide_id} has no file")
            url = github_url(target, repository_root, repository_url, branch, "")
            out += ["", f"### {card.guide_id} — {card.title}", ""]
            if card.abstract:
                out += [to_references(card.abstract, router), ""]
            # The URL appears once per guide rather than once per section: at
            # ~150 characters it would otherwise dominate a file whose whole
            # purpose is to be read cheaply.
            out += [f"**URL:** <{url}>", "", "| Section | Anchor |", "|---|---|"]
            used: set[str] = set()
            next_suffix: dict[str, int] = defaultdict(int)
            for body, _, inside_fence in iter_lines(target.read_text(encoding="utf-8")):
                if inside_fence or not body.startswith("## "):
                    continue
                heading = body[3:].strip()
                # GitHub leaves the first occurrence bare and suffixes the
                # rest, resolving each candidate against every anchor already
                # taken on the page.
                anchor = unique_slug(slugify(heading), used, next_suffix)
                cell = heading.replace("|", "\\|")
                out.append(f"| {cell} | `#{anchor}` |")
    out.append("")
    return "\n".join(out)


def render_frontmatter(name: str, description: str, when_to_use: str) -> str:
    """The exact YAML block emitted into SKILL.md, so its size can be budgeted."""
    lines = ["---", f"name: {name}", f"description: {yaml_scalar(description)}"]
    if when_to_use:
        lines.append(f"when_to_use: {yaml_scalar(when_to_use)}")
    lines.append("---")
    return "\n".join(lines)


def render_skill_md(
    spec: SkillSpec, routers: list[PartRouter], date: str, to_root: 'callable'
) -> str:
    parts = ", ".join(f"Part {router.part}" for router in routers)
    lines = render_frontmatter(spec.name, spec.description, spec.when_to_use).splitlines()
    lines += [
        "",
        f"# {spec.title}",
        "",
        f"{parts} of an independent, evidence-backed guide series on Apple's 2026 on-device AI "
        "stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. "
        "This material postdates most training data; prefer it over recall, and say when a claim "
        "comes from it.",
        "",
        "## Evidence markers — never flatten these",
        "",
        EVIDENCE_LEGEND.rstrip(),
        "",
        "## Find the answer in three moves",
        "",
        READ_PROTOCOL.rstrip(),
        "",
        "## Version floors",
        "",
        "| Part | Floor |",
        "|---|---|",
    ]
    for router in routers:
        lines.append(
            f"| [{router.part}](references/{router.directory}/README.md) "
            f"| {to_root(strip_footnotes(first_sentence(router.version_floor)), router)} |"
        )

    caveats = [(router, heading, anchor)
               for router in routers for heading, anchor in router.warnings]
    if caveats:
        lines += ["", "## Read these before you trust a signature", ""]
        for router, heading, anchor in caveats:
            clean = heading.lstrip("⚠️ ").strip()
            lines.append(
                f"- **Part {router.part}** — "
                f"[{to_root(strip_footnotes(clean), router)}]"
                f"(references/{router.directory}/README.md#{anchor})"
            )

    lines += [
        "", "## Triage", "",
        "A `N.M` label is a deep reference guide; look it up in "
        "`references/SECTION-MAPS.md` for its sections and URL.", "",
    ]
    quota = max(3, spec.max_triage_rows // max(len(routers), 1))
    for router in routers:
        owned = spec.owns[router.part]
        rows = [row for row in router.triage_rows if owns_row(row, owned)]
        shown = rows[:quota]
        header = router.triage_header or ("If your situation is…", "Read", "Why")
        lines += [
            f"**Part {router.part} — {router.title}** "
            f"([all {len(router.triage_rows)} rows]"
            f"(references/{router.directory}/README.md#{router.triage_anchor}))",
            "",
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
        ]
        lines += [to_root(strip_footnotes(row), router) for row in shown]
        lines.append("")

    lines += ["## The deep reference guides", "",
              "Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.", ""]
    for router in routers:
        owned = spec.owns[router.part]
        for card in router.cards:
            if owned is not None and card.guide not in owned:
                continue
            summary = to_root(first_sentence(strip_footnotes(card.abstract), 170), router)
            lines.append(f"- **{card.guide_id}** {card.title} — {summary}")
    lines += [
        "",
        "To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming "
        "the section. For sustained work, ask the user before cloning the corpus locally:",
        "",
        "```bash",
        "git clone --depth 1 --filter=blob:none --sparse \\",
        "  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git",
        "cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides",
        "```",
    ]
    if spec.related:
        lines += ["", "## Related skills", "",
                  "Adjacent parts of the series live in these sibling skills: "
                  + ", ".join(f"`{name}`" for name in spec.related) + "."]
    lines.append("")
    return "\n".join(lines)


def yaml_scalar(text: str) -> str:
    """Quote a description so a strict scalar-only YAML reader round-trips it."""
    if "\n" in text:
        raise SkillError(
            "frontmatter values must be single-line; a newline would emit a block "
            "scalar that verify-skills.py deliberately refuses to parse"
        )
    if re.search(r'[:#\'"]|^\s|\s$', text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def strip_footnotes(text: str) -> str:
    """Drop footnote references from text lifted out of a guide.

    The definition stays behind in the part README, so a surviving `[^x]` in a
    SKILL.md renders as a dangling marker.
    """
    return FOOTNOTE_REF.sub("", text)


# --------------------------------------------------------------------- build

def safe_replace_skills(skills_root: Path, staged: Path) -> None:
    """Swap the staged tree in, but never over a tree this script did not write.

    The marker lives inside the tree and is committed with it, so a fresh clone
    can regenerate. A hand-authored skills/ has no marker and is refused.
    """
    if skills_root.exists() and not (skills_root / GENERATED_MARKER).exists():
        raise SkillError(
            f"{skills_root} exists but {skills_root / GENERATED_MARKER} does not; "
            "refusing to replace a tree this script did not generate"
        )
    backup = skills_root.parent / f".{skills_root.name}.replaced"
    if backup.exists():
        shutil.rmtree(backup)
    if skills_root.exists():
        os.replace(skills_root, backup)
    try:
        os.replace(staged, skills_root)
    except BaseException:
        if backup.exists():
            os.replace(backup, skills_root)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def build_skills(
    source_root: Path,
    skills_root: Path,
    manifest_path: Path,
    repository_root: Path,
    interfaces: Path,
) -> dict:
    source_root = source_root.resolve()
    skills_root = skills_root.resolve()
    repository_root = repository_root.resolve()
    if not is_within(source_root, repository_root):
        raise SkillError(f"{source_root} is outside {repository_root}")
    if is_within(skills_root, source_root) or skills_root in (source_root, repository_root):
        raise SkillError(f"{skills_root} must be outside the guide sources")

    before = source_snapshot(source_root)
    date = generation_date()
    pages = discover_pages(source_root)
    repository_url, branch, specs = load_manifest(manifest_path, pages)

    routers: dict[int, PartRouter] = {}
    for page in pages:
        if page.role == "part":
            routers[page.part] = parse_part_readme(
                page, page.source.read_text(encoding="utf-8")
            )

    counts = extract_symbols.collect_symbol_counts(str(source_root))
    sdk26, sdk27 = extract_symbols.sdk_presence(str(interfaces))
    symbol_rows = extract_symbols.symbol_rows(counts, sdk26, sdk27, cap=None)
    silent_text = (source_root / "SILENT-FAILURES.md").read_text(encoding="utf-8")

    skills_root.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".skills-stage-", dir=skills_root.parent))
    files: dict[str, str] = {}
    try:
        for spec in specs:
            owned_pages = [page for page in pages if owns_page(spec, page)]
            # Ownership and bundling are different things: a skill owns its deep
            # reference guides for indexing and section maps, but only the part
            # READMEs and the hub's series README are copied in. `bundled` is
            # what link resolution may leave as a relative path.
            bundled_pages = [page for page in owned_pages if page.role in ("part", "root")]
            owned = {page.relative for page in bundled_pages}
            owned_ids: set[str] = set()
            for part, references in spec.owns.items():
                owned_ids.add(f"{part}.README")
                for page in pages:
                    if page.role == "guide" and page.part == part:
                        if references is None or page.guide in references:
                            owned_ids.add(f"{part}.{page.guide}")
            # The hub skill is where you land when you do not yet know which
            # framework owns the problem, so its two indexes span the whole
            # series rather than just the part it bundles.
            if spec.full_indexes:
                owned_ids = {guide_label(page.relative) for page in pages} | {"root"}
            index_ids = owned_ids

            skill_dir = staged / spec.name
            (skill_dir / "references").mkdir(parents=True)
            spec_routers = [routers[part] for part in sorted(spec.owns)]

            for page in bundled_pages:
                destination = skill_dir / "references" / page.relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    rewrite_text(
                        page.source.read_text(encoding="utf-8"), page.relative,
                        posixpath.dirname(f"references/{page.relative}"), owned,
                        source_root, repository_root, repository_url, branch,
                    ),
                    encoding="utf-8",
                )

            def link_for(path: str, _owned=owned) -> str:
                if path in _owned:
                    return path
                return github_url(
                    source_root / path, repository_root, repository_url, branch, ""
                )

            def to_root(text: str, router: PartRouter, _owned=owned) -> str:
                """Re-point links in text lifted from a part README into SKILL.md.

                Links to bundled files stay clickable. Links to a deep guide
                would become a ~150-character GitHub URL, which is a poor trade
                inside a body that persists for a whole session — the `N.M §K`
                label already identifies the section, and SECTION-MAPS.md turns
                it back into a URL. So those are flattened to their text.
                """
                rewritten = rewrite_text(
                    text, f"{router.directory}/README.md", "", _owned,
                    source_root, repository_root, repository_url, branch,
                )
                return GUIDE_LINK.sub(r"\1", rewritten)

            def to_references(text: str, router: PartRouter, _owned=owned) -> str:
                """Same, for text lifted into a file under references/."""
                return rewrite_text(
                    text, f"{router.directory}/README.md", "references", _owned,
                    source_root, repository_root, repository_url, branch,
                )

            series = f"{repository_url}/blob/{branch}/guides"
            write(skill_dir / "SKILL.md", render_skill_md(spec, spec_routers, date, to_root))
            write(
                skill_dir / "references" / "SILENT-FAILURES.md",
                rewrite_text(
                    render_silent_slice(
                        silent_text, spec, owned_ids, date, f"{series}/SILENT-FAILURES.md"
                    ),
                    "SILENT-FAILURES.md", "references", owned, source_root,
                    repository_root, repository_url, branch,
                ),
            )
            write(
                skill_dir / "references" / "API-INDEX.md",
                render_api_slice(
                    symbol_rows, spec, index_ids, date,
                    f"{series}/API-INDEX.md", link_for,
                ),
            )
            write(
                skill_dir / "references" / "SECTION-MAPS.md",
                render_section_maps(
                    spec, spec_routers, source_root, repository_root,
                    repository_url, branch, date, to_references,
                ),
            )

            rendered = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()
            body_lines = len(rendered) - rendered.index("---", 1) - 1
            if body_lines > MAX_BODY_LINES:
                raise SkillError(
                    f"{spec.name}: SKILL.md is {body_lines} lines, over the {MAX_BODY_LINES} "
                    "budget; lower max_triage_rows in the manifest"
                )

        write(staged / "README.md", render_roster(specs, repository_url, date))
        write(
            staged / GENERATED_MARKER,
            "Generated by scripts/build-skills.py from guides/.\n"
            "Delete this file to stop the generator from replacing this tree.\n",
        )
        for path in sorted(staged.rglob("*")):
            if path.is_file():
                files[path.relative_to(staged).as_posix()] = sha256(path)

        after = source_snapshot(source_root)
        if before != after:
            changed = sorted(
                str(path) for path in set(before) | set(after)
                if before.get(path) != after.get(path)
            )
            raise SkillError(f"guide sources changed during generation: {', '.join(changed)}")

        safe_replace_skills(skills_root, staged)
        staged = None
    finally:
        if staged is not None and staged.exists():
            shutil.rmtree(staged)

    return {
        "schema_version": 1,
        "generated": date,
        "repository": {"url": repository_url, "branch": branch},
        "skill_count": len(specs),
        "file_count": len(files),
        "files": dict(sorted(files.items())),
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_roster(specs: list[SkillSpec], repository_url: str, date: str) -> str:
    slug = repository_url.rstrip("/").split("github.com/")[-1]
    lines = [
        "# Claude Code skills for Apple's on-device AI stack",
        "",
        "Generated from [`guides/`](../guides/) — the canonical corpus. Edit the guides and "
        "run `./scripts/build-skills.sh`; never edit anything in this directory by hand.",
        "",
        "Install every skill into the current project:",
        "",
        "```bash",
        f"npx skills add {slug} --all",
        "```",
        "",
        "Or just the one you need, globally:",
        "",
        "```bash",
        f"npx skills add {slug} --skill apple-foundation-models -g",
        "```",
        "",
        "| Skill | Covers | What it is for |",
        "|---|---|---|",
    ]
    for spec in specs:
        # Name the reference subset for a part shared between skills, so the
        # three skills that each own a slice of part 16 are told apart.
        owned = []
        for part in sorted(spec.owns):
            references = spec.owns[part]
            if references is None:
                owned.append(str(part))
            else:
                owned += [f"{part}.{number}" for number in sorted(references)]
        lines.append(f"| `{spec.name}` | Part {', '.join(owned)} | {spec.description} |")
    lines += [
        "",
        "Each skill's `SKILL.md` is a router: it carries the evidence-marker legend, the "
        "version floors, a triage table, and a lookup protocol. The bulk of the material sits "
        "in `references/`, which costs nothing until read — the part READMEs, a symbol index "
        "sliced to that skill, a silent-failure index sliced to that skill, and section maps "
        "addressing the deep reference guides that stay in this repository.",
        "",
        f"Generated {date}.",
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=Path("guides"))
    parser.add_argument("--skills", type=Path, default=Path("skills"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("notes/synthesis/skill-manifest.json")
    )
    parser.add_argument(
        "--build-manifest", type=Path, default=None,
        help="where to write the generated file manifest (default: <skills>/skills-manifest.json)",
    )
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--interfaces", type=Path, default=Path("notes/sdk-interfaces"))
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        manifest = build_skills(
            arguments.source,
            arguments.skills,
            arguments.manifest,
            arguments.repository_root,
            arguments.interfaces,
        )
    except SkillError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    target = arguments.build_manifest or (arguments.skills / "skills-manifest.json")
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    # The manifest lists the tree it describes, so it cannot list itself.
    write(target, payload)
    print(
        f"Wrote {manifest['skill_count']} skills, {manifest['file_count']} files, "
        f"to {arguments.skills}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
