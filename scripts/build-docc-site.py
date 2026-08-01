#!/usr/bin/env python3
"""Build a disposable, article-only DocC catalog from guides/.

The Markdown files under guides/ are the canonical source.  This adapter only
reads them and writes transformed copies with globally unique DocC page names,
DocC navigation, and resolvable links into a generated .docc catalog.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
from urllib.parse import quote, unquote


PART_README = re.compile(r"^part-(\d{2})-[^/]+/README\.md$")
REFERENCE = re.compile(
    r"^part-(\d{2})-[^/]+/references/(\d{2})-[^/]+\.md$"
)
FENCE = re.compile(r"^(?: {0,3}>[ \t]?)* {0,3}(`{3,}|~{3,})")
BLOCK_QUOTE_LINE = re.compile(
    r"^(?P<prefix>(?: {0,3}>[ \t]?)+)(?P<content>.*)$"
)
HEADING_ONE = re.compile(
    r"^(?P<prefix>(?: {0,3}>[ \t]?)* {0,3})#\s+(?P<title>.+?)\s*$"
)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
GENERATED_MARKER_SUFFIX = ".generated-by-build-docc-site"
DEFAULT_BUNDLE_IDENTIFIER = "dev.hbmartin.apple-ai-guides"
DOCC_ASIDE_TAGS = {
    "attention",
    "author",
    "authors",
    "bug",
    "complexity",
    "copyright",
    "date",
    "experiment",
    "important",
    "invariant",
    "mutatingvariant",
    "nonmutatingvariant",
    "note",
    "postcondition",
    "precondition",
    "remark",
    "requires",
    "seealso",
    "since",
    "throws",
    "tip",
    "todo",
    "version",
    "warning",
}

# The Part 13 guide quotes an upstream DocC page whose extensionless target is
# meaningful only inside mlx-swift-lm's documentation bundle. Keep that source
# quotation unchanged and give its generated copy a public upstream target.
EXTERNAL_LINK_OVERRIDES = {
    (
        "part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md",
        "MLXHuggingFace",
    ): "https://github.com/ml-explore/mlx-swift-lm/tree/main/Libraries/MLXHuggingFace",
}


class CatalogError(RuntimeError):
    """An actionable error in the source corpus or requested output."""


@dataclass(frozen=True)
class Page:
    source: Path
    source_relative: str
    identifier: str
    output_name: str
    role: str
    title: str
    part: int | None = None
    guide: int | None = None
    sha256: str = ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_snapshot(source_root: Path) -> dict[Path, str]:
    return {path.resolve(): sha256(path) for path in sorted(source_root.rglob("*.md"))}


def first_title(text: str, source: Path) -> str:
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if not match:
            raise CatalogError(f"{source}: first content line must be an H1 page title")
        return match.group(1)
    raise CatalogError(f"{source}: file is empty")


def discover_pages(source_root: Path) -> list[Page]:
    pages: list[Page] = []
    identifiers: dict[str, str] = {}

    for source in sorted(source_root.rglob("*.md")):
        relative = source.relative_to(source_root).as_posix()
        text = source.read_text(encoding="utf-8")
        title = first_title(text, source)
        part_match = PART_README.fullmatch(relative)
        reference_match = REFERENCE.fullmatch(relative)

        if relative == "README.md":
            identifier, output_name, role = "AppleAIGuides", "AppleAIGuides.md", "root"
            part = guide = None
        elif relative == "API-INDEX.md":
            identifier, output_name, role = "API-Index", "API-Index.md", "index"
            part = guide = None
        elif relative == "SILENT-FAILURES.md":
            identifier = "Silent-Failures"
            output_name, role = "Silent-Failures.md", "index"
            part = guide = None
        elif part_match:
            part = int(part_match.group(1))
            identifier = f"Part-{part:02d}"
            output_name, role, guide = f"{identifier}.md", "part", None
        elif reference_match:
            part, guide = map(int, reference_match.groups())
            identifier = f"Part-{part:02d}-Guide-{guide:02d}"
            output_name, role = f"{identifier}.md", "guide"
        else:
            raise CatalogError(
                f"{relative}: unrecognized guide path; expected a root/index, part README, "
                "or numbered file under a part's references/ directory"
            )

        if identifier.casefold() in identifiers:
            raise CatalogError(
                f"{relative}: DocC identifier {identifier!r} collides with "
                f"{identifiers[identifier.casefold()]}"
            )
        identifiers[identifier.casefold()] = relative
        pages.append(
            Page(
                source=source.resolve(),
                source_relative=relative,
                identifier=identifier,
                output_name=output_name,
                role=role,
                title=title,
                part=part,
                guide=guide,
                sha256=sha256(source),
            )
        )

    if not any(page.role == "root" for page in pages):
        raise CatalogError(f"{source_root}: missing README.md")

    part_numbers = {page.part for page in pages if page.role == "part"}
    for page in pages:
        if page.role == "guide" and page.part not in part_numbers:
            raise CatalogError(
                f"{page.source_relative}: has no matching part README for part {page.part}"
            )
    return pages


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def split_destination(inner: str) -> tuple[str, str, bool] | None:
    """Return (destination, suffix, was_angle_wrapped) for a Markdown link body."""
    leading_length = len(inner) - len(inner.lstrip())
    leading = inner[:leading_length]
    remainder = inner[leading_length:]
    if not remainder:
        return None
    if remainder.startswith("<"):
        end = remainder.find(">", 1)
        if end < 0:
            return None
        return remainder[1:end], leading + remainder[end + 1 :], True

    escaped = False
    end = 0
    while end < len(remainder):
        character = remainder[end]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character.isspace():
            break
        end += 1
    return remainder[:end], leading + remainder[end:], False


def page_target(candidate: Path, raw_path: str) -> Path:
    if raw_path.endswith("/") or candidate.is_dir():
        return candidate / "README.md"
    return candidate


def docc_addressable_fragment(fragment: str) -> str:
    """A GitHub-faithful anchor rewritten so DocC can address it.

    A ⚠️ heading's slug begins with the U+FE0F variation selector, and a
    combining mark merges with the ``#`` separator into a single grapheme, so
    DocC cannot split the reference and reports the whole page#fragment as one
    unresolved topic. Leading marks are dropped and the rest percent-encoded
    for the catalog copy only; the diagnostics pass then canonicalizes these
    fragments to DocC's own anchor spellings. GitHub copies keep the marks.
    """
    decoded = unquote(fragment)
    index = 0
    while index < len(decoded) and unicodedata.category(decoded[index]) in ("Mn", "Me"):
        index += 1
    return quote(decoded[index:], safe="!$&()*+,;=:@/?")


def github_url(
    target: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    fragment: str,
) -> str:
    relative = target.relative_to(repository_root).as_posix()
    object_kind = "tree" if target.is_dir() else "blob"
    url = f"{repository_url.rstrip('/')}/{object_kind}/{quote(branch, safe='')}/{quote(relative, safe='/')}"
    return f"{url}#{fragment}" if fragment else url


def rewrite_destination(
    destination: str,
    source_page: Page,
    pages_by_source: dict[Path, Page],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    bundle_identifier: str,
) -> str:
    override = EXTERNAL_LINK_OVERRIDES.get(
        (source_page.source_relative, destination)
    )
    if override:
        return override
    if (
        not destination
        or destination.startswith(("#", "//"))
        or SCHEME.match(destination)
    ):
        return destination

    path_text, separator, fragment = destination.partition("#")
    if not path_text:
        return destination
    path_without_query, query_separator, query = path_text.partition("?")
    decoded_path = unquote(path_without_query)
    candidate = (source_page.source.parent / decoded_path).resolve()
    candidate_page_path = page_target(candidate, decoded_path)
    target_page = pages_by_source.get(candidate_page_path)
    if target_page:
        if query_separator:
            raise CatalogError(
                f"{source_page.source_relative}: internal guide link has unsupported query: "
                f"{destination}"
            )
        # A technology root sits outside the generated documentation hierarchy,
        # so it is not resolvable by its short identifier from child articles.
        # Its absolute documentation URI is stable because both the adapter and
        # DocC conversion use the same fallback bundle identifier.
        if target_page.role == "root":
            doc_reference = (
                f"//{bundle_identifier}/documentation/{target_page.identifier}"
            )
        else:
            doc_reference = target_page.identifier
        if separator:
            doc_reference += f"#{docc_addressable_fragment(fragment)}"
        return f"<doc:{doc_reference}>"

    if is_within(candidate, source_root):
        raise CatalogError(
            f"{source_page.source_relative}: internal link target does not exist in the "
            f"DocC page registry: {destination}"
        )

    if is_within(candidate, repository_root) and candidate.exists():
        if query_separator:
            raise CatalogError(
                f"{source_page.source_relative}: repository-file link has unsupported query: "
                f"{destination}"
            )
        return github_url(
            candidate, repository_root, repository_url, branch, fragment if separator else ""
        )

    raise CatalogError(
        f"{source_page.source_relative}: unresolved relative link target: {destination}"
    )


def rewrite_link_body(
    inner: str,
    source_page: Page,
    pages_by_source: dict[Path, Page],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    bundle_identifier: str,
) -> str:
    parsed = split_destination(inner)
    if not parsed:
        return inner
    destination, suffix, _ = parsed
    rewritten = rewrite_destination(
        destination,
        source_page,
        pages_by_source,
        source_root,
        repository_root,
        repository_url,
        branch,
        bundle_identifier,
    )
    return f"{rewritten}{suffix}"


def rewrite_inline_links(
    line: str,
    source_page: Page,
    pages_by_source: dict[Path, Page],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    bundle_identifier: str,
) -> str:
    """Rewrite inline Markdown link destinations while ignoring inline code."""
    result: list[str] = []
    index = 0
    code_delimiter = 0

    while index < len(line):
        if line[index] == "`":
            end = index
            while end < len(line) and line[end] == "`":
                end += 1
            run = end - index
            if code_delimiter == 0:
                code_delimiter = run
            elif code_delimiter == run:
                code_delimiter = 0
            result.append(line[index:end])
            index = end
            continue

        if code_delimiter == 0 and line.startswith("](", index):
            result.append("](")
            body_start = index + 2
            cursor = body_start
            depth = 1
            escaped = False
            angle_wrapped = False
            while cursor < len(line):
                character = line[cursor]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == "<" and depth == 1:
                    angle_wrapped = True
                elif character == ">" and depth == 1:
                    angle_wrapped = False
                elif not angle_wrapped and character == "(":
                    depth += 1
                elif not angle_wrapped and character == ")":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            if depth != 0:
                result.append(line[body_start:])
                return "".join(result)
            inner = line[body_start:cursor]
            result.append(
                rewrite_link_body(
                    inner,
                    source_page,
                    pages_by_source,
                    source_root,
                    repository_root,
                    repository_url,
                    branch,
                    bundle_identifier,
                )
            )
            result.append(")")
            index = cursor + 1
            continue

        result.append(line[index])
        index += 1
    return "".join(result)


BACKTICK_RUN = re.compile(r"`+")

# Block starts that end the current inline-parsing context. CommonMark does
# not treat indented code as interrupting an ordinary paragraph, but stopping
# here is intentionally conservative: the generated DocC copy must never let
# an unmatched source delimiter change later block markup.
ATX_HEADING_START = re.compile(r" {0,3}#{1,6}(?:[ \t]+|$)")
LIST_ITEM_START = re.compile(r" {0,3}(?:[-+*]|\d{1,9}[.)])(?:[ \t]+|$)")
# Capture the indentation of a non-empty list item's paragraph so continuation
# lines are not mistaken for top-level indented code. Wider/ tabbed padding is
# left conservative because CommonMark assigns it different block semantics.
LIST_ITEM_CONTEXT = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>[-+*]|\d{1,9}[.)])"
    r"(?P<spacing> {1,4})(?=\S)"
)
INDENTED_CODE_START = re.compile(r"(?: {4}|\t)")
SETEXT_HEADING_START = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")
THEMATIC_BREAK_START = re.compile(
    r" {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})$"
)
LINK_DEFINITION_START = re.compile(r" {0,3}\[[^]\n]+\]:[ \t]*(?:\S|$)")
TABLE_DELIMITER_START = re.compile(
    r" {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t]*$"
)
DOCC_DIRECTIVE_START = re.compile(r" {0,3}@\w")
HTML_BLOCK_START = re.compile(
    r" {0,3}(?:<!--|<\?|<![A-Z]|<!\[CDATA\[|"
    r"</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|"
    r"col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|"
    r"footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|"
    r"link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|"
    r"section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)"
    r"(?:[ \t]|/?>|$)|<(?:script|pre|style|textarea)(?:[ \t]|>|$))",
    re.IGNORECASE,
)
PARAGRAPH_BLOCK_STARTS = (
    ATX_HEADING_START,
    LIST_ITEM_START,
    INDENTED_CODE_START,
    SETEXT_HEADING_START,
    THEMATIC_BREAK_START,
    LINK_DEFINITION_START,
    TABLE_DELIMITER_START,
    DOCC_DIRECTIVE_START,
    HTML_BLOCK_START,
)

# A page abstract is the first plain paragraph after the title; lists, quotes,
# tables, and directives never become one.
NON_ABSTRACT_PREFIX = re.compile(r"[-*+]\s|\d+[.)]\s|[>#|@]")
ABSTRACT_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def has_backtick_run(text: str, length: int) -> bool:
    return any(len(match.group()) == length for match in BACKTICK_RUN.finditer(text))


def paragraph_lookahead(lines: list[str], index: int) -> str:
    """The current paragraph's remaining text after ``lines[index]``.

    CommonMark resolves block structure before inline code spans, so a span
    may only open when its closing run appears before the paragraph ends.
    Blank lines, fenced code, container changes, and paragraph-interrupting
    block starts terminate the search.
    """
    current = lines[index][:-1] if lines[index].endswith("\n") else lines[index]
    current_quote = BLOCK_QUOTE_LINE.match(current)
    current_quote_depth = (
        current_quote.group("prefix").count(">") if current_quote else 0
    )
    current_content = current_quote.group("content") if current_quote else current
    current_list = LIST_ITEM_CONTEXT.match(current_content)
    list_content_indent = (
        sum(len(current_list.group(name)) for name in ("indent", "marker", "spacing"))
        if current_list
        else 0
    )
    collected = []
    for line in lines[index + 1 :]:
        body = line[:-1] if line.endswith("\n") else line
        quote = BLOCK_QUOTE_LINE.match(body)
        quote_depth = quote.group("prefix").count(">") if quote else 0
        content = quote.group("content") if quote else body
        if list_content_indent and content.startswith(" " * list_content_indent):
            content = content[list_content_indent:]
        if (
            not body.strip()
            or quote_depth != current_quote_depth
            or FENCE.match(body)
            or FENCE.match(content)
            or any(pattern.match(content) for pattern in PARAGRAPH_BLOCK_STARTS)
        ):
            break
        collected.append(body)
    return "\n".join(collected)


def transform_code_spans_and_doc_references(
    line: str, code_delimiter: int, lookahead: str = ""
) -> tuple[str, int]:
    """Escape prose ``<doc:`` references while preserving code spans.

    The active backtick-run length is carried across lines so every valid
    multiline code span stays verbatim; a run with no exact-length closer
    before the paragraph ends never opens a span, as in CommonMark. Exact
    double-backtick spans are rendered as HTML code elements because DocC
    otherwise treats them as symbol links.
    """
    result: list[str] = []
    index = 0

    while index < len(line):
        if line[index] == "`":
            end = index
            while end < len(line) and line[end] == "`":
                end += 1
            run = end - index
            if code_delimiter == 0:
                if has_backtick_run(line[end:], run) or has_backtick_run(
                    lookahead, run
                ):
                    code_delimiter = run
                    result.append("<code>" if run == 2 else line[index:end])
                else:
                    result.append(line[index:end])
            elif code_delimiter == run:
                result.append("</code>" if run == 2 else line[index:end])
                code_delimiter = 0
            else:
                # Backtick runs nested inside an exact double-backtick span
                # are literal code content. HTML-encode them so Swift
                # Markdown cannot reinterpret them as symbol references.
                result.append("&#96;" * run if code_delimiter == 2 else line[index:end])
            index = end
            continue
        if code_delimiter == 2:
            result.append(html.escape(line[index]))
            index += 1
            continue
        if code_delimiter == 0 and line.startswith("<doc:", index):
            result.append("\\<doc:")
            index += len("<doc:")
            continue
        result.append(line[index])
        index += 1
    return "".join(result), code_delimiter


def protect_plain_block_quote_from_aside_parsing(line: str) -> str:
    """Keep a prose colon from becoming a DocC aside tag.

    Swift Markdown 6.3.3 can trap while stripping a multiword tag from a
    block quote whose first text node ends at a colon. An empty inline HTML
    comment makes the first child non-text without changing rendered prose.
    Real DocC aside tags remain untouched.
    """
    match = BLOCK_QUOTE_LINE.match(line)
    if not match:
        return line
    content = match.group("content")
    before_colon, separator, _ = content.partition(":")
    if not separator:
        return line
    normalized_tag = re.sub(r"[\s-]+", "", before_colon).casefold()
    if normalized_tag in DOCC_ASIDE_TAGS:
        return line
    return f'{match.group("prefix")}<!-- -->{content}'


def transform_markdown(
    page: Page,
    pages_by_source: dict[Path, Page],
    source_root: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    bundle_identifier: str,
) -> str:
    source_text = page.source.read_text(encoding="utf-8")
    output: list[str] = []
    fence_character = ""
    fence_length = 0
    saw_title = False
    code_span_delimiter = 0
    block_quote_open = False
    awaiting_abstract = False
    in_abstract = False

    lines = source_text.splitlines(keepends=True)
    for line_index, line in enumerate(lines):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        fence = FENCE.match(body)
        if fence:
            marker = fence.group(1)
            if not fence_character:
                fence_character, fence_length = marker[0], len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character, fence_length = "", 0
            awaiting_abstract = in_abstract = False
            output.append(body + newline)
            quote = BLOCK_QUOTE_LINE.match(body)
            block_quote_open = bool(quote and quote.group("content").strip())
            continue
        if fence_character:
            output.append(body + newline)
            continue

        quote = BLOCK_QUOTE_LINE.match(body)
        if quote:
            if not block_quote_open and quote.group("content").strip():
                body = protect_plain_block_quote_from_aside_parsing(body)
                block_quote_open = True
        else:
            block_quote_open = False

        heading = HEADING_ONE.match(body)
        is_title = False
        if heading:
            if saw_title:
                body = f"{heading.group('prefix')}## {heading.group('title')}"
            else:
                saw_title = True
                is_title = True

        if is_title:
            awaiting_abstract = True
        elif body.startswith("#") or quote:
            awaiting_abstract = in_abstract = False
        elif in_abstract and not body.strip():
            in_abstract = False
        elif (awaiting_abstract or in_abstract) and body.strip():
            if awaiting_abstract:
                awaiting_abstract = False
                in_abstract = NON_ABSTRACT_PREFIX.match(body.lstrip()) is None
            if in_abstract:
                # DocC never displays links in a page abstract, and Swift
                # 6.2's docc warns about them, which --warnings-as-errors
                # turns fatal. Keep the visible text; the GitHub-rendered
                # copies keep their links.
                body = ABSTRACT_LINK.sub(r"\1", body)

        # These sequences in the source quote upstream DocC/RST syntax. In an
        # article-only catalog they are prose, not links to symbols. Code
        # spans keep their content verbatim.
        lookahead = paragraph_lookahead(lines, line_index) if "`" in body else ""
        body, code_span_delimiter = transform_code_spans_and_doc_references(
            body, code_span_delimiter, lookahead
        )
        body = rewrite_inline_links(
            body,
            page,
            pages_by_source,
            source_root,
            repository_root,
            repository_url,
            branch,
            bundle_identifier,
        )
        output.append(body + newline)

    if code_span_delimiter == 2:
        raise CatalogError(f"{page.source_relative}: unclosed double-backtick code span")

    transformed = "".join(output)
    if not transformed.endswith("\n"):
        transformed += "\n"

    if page.role == "root":
        lines = transformed.splitlines(keepends=True)
        insertion = next(
            (index + 1 for index, line in enumerate(lines) if line.startswith("# ")), None
        )
        if insertion is None:
            raise CatalogError(f"{page.source_relative}: could not insert technology metadata")
        lines[insertion:insertion] = [
            "\n",
            "@Metadata {\n",
            "  @TechnologyRoot\n",
            "}\n",
        ]
        transformed = "".join(lines)

    return transformed


def topics_for(page: Page, pages: list[Page]) -> str:
    if page.role == "root":
        parts = sorted((item for item in pages if item.role == "part"), key=lambda item: item.part)
        indexes = sorted((item for item in pages if item.role == "index"), key=lambda item: item.identifier)
        lines = ["\n## Topics\n", "\n### Parts\n", "\n"]
        lines.extend(f"- <doc:{item.identifier}>\n" for item in parts)
        lines.extend(["\n### Cross-cutting indexes\n", "\n"])
        lines.extend(f"- <doc:{item.identifier}>\n" for item in indexes)
        return "".join(lines)
    if page.role == "part":
        guides = sorted(
            (item for item in pages if item.role == "guide" and item.part == page.part),
            key=lambda item: item.guide,
        )
        lines = ["\n## Topics\n", "\n### Guides in this part\n", "\n"]
        lines.extend(f"- <doc:{item.identifier}>\n" for item in guides)
        return "".join(lines)
    return ""


def safe_replace_catalog(catalog: Path, generated: Path) -> None:
    marker = catalog.parent / f".{catalog.name}{GENERATED_MARKER_SUFFIX}"
    if catalog.exists():
        if not marker.is_file():
            raise CatalogError(
                f"refusing to replace existing catalog without generated marker: {catalog}"
            )
        shutil.rmtree(catalog)
    os.replace(generated, catalog)
    marker.write_text(f"generated catalog: {catalog}\n", encoding="utf-8")


def build_catalog(
    source_root: Path,
    catalog: Path,
    manifest: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    bundle_identifier: str = DEFAULT_BUNDLE_IDENTIFIER,
) -> dict[str, object]:
    source_root = source_root.resolve()
    repository_root = repository_root.resolve()
    catalog = catalog.resolve()
    manifest = manifest.resolve()

    if catalog.suffix != ".docc":
        raise CatalogError(f"catalog path must end in .docc: {catalog}")
    if not source_root.is_dir():
        raise CatalogError(f"source directory does not exist: {source_root}")
    if not is_within(source_root, repository_root):
        raise CatalogError(f"source directory must be within repository root: {source_root}")
    if not is_within(catalog, repository_root):
        raise CatalogError(f"generated catalog must be within the repository root: {catalog}")
    if is_within(catalog, source_root) or catalog in (source_root, repository_root):
        raise CatalogError(f"generated catalog must be outside the source and repository roots: {catalog}")
    if not is_within(manifest, repository_root) or is_within(manifest, source_root):
        raise CatalogError(
            f"generated manifest must be within the repository and outside the source: {manifest}"
        )
    if not re.fullmatch(r"[A-Za-z0-9.-]+", bundle_identifier):
        raise CatalogError(f"invalid DocC bundle identifier: {bundle_identifier!r}")

    before = source_snapshot(source_root)
    pages = discover_pages(source_root)
    pages_by_source = {page.source: page for page in pages}

    catalog.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=".docc-stage-", dir=catalog.parent))
    generated = temporary_root / catalog.name
    generated.mkdir()
    try:
        for page in pages:
            content = transform_markdown(
                page,
                pages_by_source,
                source_root,
                repository_root,
                repository_url,
                branch,
                bundle_identifier,
            )
            content += topics_for(page, pages)
            (generated / page.output_name).write_text(content, encoding="utf-8")

        after = source_snapshot(source_root)
        if before != after:
            changed = sorted(
                str(path)
                for path in set(before) | set(after)
                if before.get(path) != after.get(path)
            )
            raise CatalogError(f"source guides changed during catalog generation: {changed}")

        safe_replace_catalog(catalog, generated)
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)

    manifest_data: dict[str, object] = {
        "schema_version": 1,
        "source_root": source_root.relative_to(repository_root).as_posix(),
        "catalog": str(catalog),
        "repository_url": repository_url.rstrip("/"),
        "branch": branch,
        "bundle_identifier": bundle_identifier,
        "page_count": len(pages),
        "pages": [
            {
                **asdict(page),
                "source": page.source_relative,
            }
            for page in pages
        ],
    }
    manifest.write_text(
        json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest_data


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="canonical guides directory")
    parser.add_argument("--catalog", type=Path, required=True, help="generated .docc directory")
    parser.add_argument("--manifest", type=Path, help="generated page manifest JSON")
    parser.add_argument(
        "--repository-root",
        type=Path,
        help="checkout root; defaults to the source directory's parent",
    )
    parser.add_argument(
        "--repository-url",
        default="https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills",
    )
    parser.add_argument("--branch", default="main")
    parser.add_argument(
        "--bundle-identifier",
        default=DEFAULT_BUNDLE_IDENTIFIER,
        help="DocC fallback bundle identifier used by the conversion step",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    source = arguments.source.resolve()
    catalog = arguments.catalog.resolve()
    repository_root = (arguments.repository_root or source.parent).resolve()
    manifest = (arguments.manifest or catalog.parent / "docc-manifest.json").resolve()
    try:
        data = build_catalog(
            source,
            catalog,
            manifest,
            repository_root,
            arguments.repository_url,
            arguments.branch,
            arguments.bundle_identifier,
        )
    except (CatalogError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Generated {data['page_count']} DocC pages in {catalog}")
    print(f"Wrote manifest to {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
