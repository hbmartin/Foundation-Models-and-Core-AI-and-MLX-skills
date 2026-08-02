"""Small, render-only adaptations for the MkDocs documentation site.

The Markdown in ``guides/`` remains the canonical corpus.  This hook only
normalizes verifier annotations that Markdown renderers do not understand,
routes repository evidence links to GitHub, and derives navigation from the
existing guide hierarchy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

try:
    from scripts.mdslug import slugify
except ModuleNotFoundError:  # MkDocs can load a hook with scripts/ on sys.path.
    from mdslug import slugify


PART_DIRECTORY = re.compile(r"part-(?P<number>\d{2})-[a-z0-9-]+$")
REFERENCE_FILE = re.compile(r"(?P<number>\d{2})-[a-z0-9-]+\.md$")
HEADING_ONE = re.compile(r"^#\s+(.+?)\s*$")
MARKDOWN_LINK = re.compile(r"\[([^]]+)\]\(([^)]*)\)")
CODE_SPAN = re.compile(r"(?<!`)`+([^`]+?)`+(?!`)")
EMPHASIS_MARKER = re.compile(r"(?<!\\)[*_]")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FENCE = re.compile(
    r"^(?P<prefix>(?: {0,3}>[ \t]?)* {0,3})"
    r"(?P<marker>`{3,}|~{3,})(?P<info>[^\n]*)$"
)
REFERENCE_DEFINITION = re.compile(
    r"^(?P<prefix> {0,3}\[(?!\^)[^]\n]+\]:[ \t]*)(?P<body>.*)$"
)
ATX_HEADING = re.compile(
    r"^(?P<prefix>(?: {0,3}>[ \t]?)* {0,3}#{1,6}[ \t]+)"
    r"(?P<title>.*?)(?P<closing>[ \t]+#+[ \t]*)?$"
)
VERIFIER_METADATA_PREFIXES = (
    "compile:",
    "defines:",
    "imports:",
    "prelude:",
    "xfail:",
)
EXTERNAL_LINK_OVERRIDES = {
    (
        "part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md",
        "MLXHuggingFace",
    ): "https://github.com/ml-explore/mlx-swift-lm/tree/main/Libraries/MLXHuggingFace",
}


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def first_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = HEADING_ONE.fullmatch(line)
        if not match:
            raise ValueError(f"{path}: first content line must be an H1 page title")
        return strip_inline_markdown(match.group(1))
    raise ValueError(f"{path}: file is empty")


def strip_inline_markdown(title: str) -> str:
    """Return a readable plain-text navigation label from a source H1."""
    title = MARKDOWN_LINK.sub(r"\1", title)
    title = CODE_SPAN.sub(r"\1", title)
    title = EMPHASIS_MARKER.sub("", title)
    return title.replace("\\`", "`").strip()


def build_navigation(docs_dir: Path) -> list[dict[str, Any]]:
    """Build the complete, deterministic navigation from the guide tree."""
    docs_dir = docs_dir.resolve()
    root = docs_dir / "README.md"
    api_index = docs_dir / "API-INDEX.md"
    failure_index = docs_dir / "SILENT-FAILURES.md"
    required = (root, api_index, failure_index)
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"missing required guide page: {missing[0]}")

    included = {path.resolve() for path in required}
    parts: list[dict[str, Any]] = []
    part_directories = sorted(
        (
            path
            for path in docs_dir.iterdir()
            if path.is_dir() and PART_DIRECTORY.fullmatch(path.name)
        ),
        key=lambda path: int(PART_DIRECTORY.fullmatch(path.name).group("number")),
    )
    if not part_directories:
        raise ValueError(f"{docs_dir}: no numbered part directories found")

    for directory in part_directories:
        overview = directory / "README.md"
        if not overview.is_file():
            raise ValueError(f"{directory}: missing README.md")
        included.add(overview.resolve())
        children: list[dict[str, str]] = [
            {"Overview": overview.relative_to(docs_dir).as_posix()}
        ]

        references_dir = directory / "references"
        references = (
            sorted(
                (
                    path
                    for path in references_dir.glob("*.md")
                    if REFERENCE_FILE.fullmatch(path.name)
                ),
                key=lambda path: int(REFERENCE_FILE.fullmatch(path.name).group("number")),
            )
            if references_dir.is_dir()
            else []
        )
        for reference in references:
            included.add(reference.resolve())
            children.append(
                {
                    first_title(reference): reference.relative_to(docs_dir).as_posix()
                }
            )
        parts.append({first_title(overview): children})

    all_markdown = {path.resolve() for path in docs_dir.rglob("*.md")}
    unexpected = sorted(all_markdown - included)
    if unexpected:
        relative = unexpected[0].relative_to(docs_dir).as_posix()
        raise ValueError(f"unrecognized guide page is missing from navigation: {relative}")

    return [
        {"Overview": "README.md"},
        {"Parts": parts},
        {
            "Cross-cutting indexes": [
                {first_title(api_index): "API-INDEX.md"},
                {first_title(failure_index): "SILENT-FAILURES.md"},
            ]
        },
    ]


def split_destination(inner: str) -> tuple[str, str] | None:
    """Split a Markdown link body into destination and optional title suffix."""
    leading_length = len(inner) - len(inner.lstrip())
    leading = inner[:leading_length]
    remainder = inner[leading_length:]
    if not remainder:
        return None
    if remainder.startswith("<"):
        end = remainder.find(">", 1)
        if end < 0:
            return None
        return remainder[1:end], leading + remainder[end + 1 :]

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
    return remainder[:end], leading + remainder[end:]


def github_url(
    target: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    query: str,
    fragment: str,
) -> str:
    relative = target.relative_to(repository_root).as_posix()
    object_kind = "tree" if target.is_dir() else "blob"
    url = (
        f"{repository_url.rstrip('/')}/{object_kind}/"
        f"{quote(branch, safe='')}/{quote(relative, safe='/')}"
    )
    if query:
        url += f"?{query}"
    if fragment:
        url += f"#{fragment}"
    return url


def rewrite_destination(
    destination: str,
    source_path: Path,
    docs_dir: Path,
    repository_root: Path,
    repository_url: str,
    branch: str = "main",
) -> str:
    """Route an existing repository target outside guides/ to GitHub."""
    source_relative = source_path.resolve().relative_to(docs_dir.resolve()).as_posix()
    override = EXTERNAL_LINK_OVERRIDES.get((source_relative, destination))
    if override:
        return override
    if (
        not destination
        or destination.startswith(("#", "//", "/"))
        or SCHEME.match(destination)
    ):
        return destination

    path_and_query, fragment_separator, fragment = destination.partition("#")
    raw_path, query_separator, query = path_and_query.partition("?")
    if not raw_path:
        return destination
    decoded_path = unquote(raw_path.replace("\\ ", " "))
    candidate = (source_path.parent / decoded_path).resolve()
    docs_dir = docs_dir.resolve()
    repository_root = repository_root.resolve()

    if is_within(candidate, docs_dir):
        index_page = candidate / "README.md" if candidate.is_dir() else None
        if index_page and index_page.is_file():
            normalized = raw_path.rstrip("/") + "/README.md"
            if query_separator:
                normalized += f"?{query}"
            if fragment_separator:
                normalized += f"#{fragment}"
            return normalized
        return destination
    if not is_within(candidate, repository_root) or not candidate.exists():
        return destination
    return github_url(
        candidate,
        repository_root,
        repository_url,
        branch,
        query if query_separator else "",
        fragment if fragment_separator else "",
    )


def rewrite_link_body(
    inner: str,
    source_path: Path,
    docs_dir: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
) -> str:
    parsed = split_destination(inner)
    if not parsed:
        return inner
    destination, suffix = parsed
    rewritten = rewrite_destination(
        destination,
        source_path,
        docs_dir,
        repository_root,
        repository_url,
        branch,
    )
    return f"{rewritten}{suffix}"


def rewrite_inline_links(
    line: str,
    source_path: Path,
    docs_dir: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
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
            result.append(
                rewrite_link_body(
                    line[body_start:cursor],
                    source_path,
                    docs_dir,
                    repository_root,
                    repository_url,
                    branch,
                )
            )
            result.append(")")
            index = cursor + 1
            continue

        result.append(line[index])
        index += 1
    return "".join(result)


def is_verifier_metadata(token: str) -> bool:
    return token == "illustrative" or token.startswith(VERIFIER_METADATA_PREFIXES)


def normalize_fence(match: re.Match[str]) -> str:
    info = match.group("info").strip()
    fields = info.split()
    if (
        len(fields) > 1
        and fields[0].casefold() == "swift"
        and all(is_verifier_metadata(field) for field in fields[1:])
    ):
        info = fields[0]
    return f"{match.group('prefix')}{match.group('marker')}{info}"


def transform_markdown(
    markdown: str,
    source_path: Path,
    docs_dir: Path,
    repository_root: Path,
    repository_url: str,
    branch: str = "main",
) -> str:
    """Apply all render-only transforms without writing the source file."""
    output: list[str] = []
    active_fence: tuple[str, int] | None = None
    heading_counts: dict[str, int] = {}

    for line in markdown.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        fence = FENCE.fullmatch(body)

        if active_fence:
            if fence:
                marker = fence.group("marker")
                if (
                    marker[0] == active_fence[0]
                    and len(marker) >= active_fence[1]
                    and not fence.group("info").strip()
                ):
                    active_fence = None
            output.append(body + newline)
            continue

        if fence:
            marker = fence.group("marker")
            active_fence = (marker[0], len(marker))
            output.append(normalize_fence(fence) + newline)
            continue

        heading = ATX_HEADING.fullmatch(body)
        if heading and "{#" not in heading.group("title"):
            heading_slug = slugify(heading.group("title"))
            occurrence = heading_counts.get(heading_slug, 0)
            heading_counts[heading_slug] = occurrence + 1
            if heading_slug and occurrence:
                body = (
                    f"{heading.group('prefix')}{heading.group('title')}"
                    f" {{#{heading_slug}-{occurrence}}}"
                    f"{heading.group('closing') or ''}"
                )

        definition = REFERENCE_DEFINITION.fullmatch(body)
        if definition:
            rewritten = rewrite_link_body(
                definition.group("body"),
                source_path,
                docs_dir,
                repository_root,
                repository_url,
                branch,
            )
            output.append(definition.group("prefix") + rewritten + newline)
            continue

        output.append(
            rewrite_inline_links(
                body,
                source_path,
                docs_dir,
                repository_root,
                repository_url,
                branch,
            )
            + newline
        )
    return "".join(output)


def on_config(config: Any) -> Any:
    docs_dir = Path(config["docs_dir"])
    config["nav"] = build_navigation(docs_dir)
    mdx_configs = getattr(config, "mdx_configs", None)
    if mdx_configs is None:
        mdx_configs = config.setdefault("mdx_configs", {})
    mdx_configs.setdefault("toc", {})["slugify"] = slugify
    return config


def on_page_markdown(markdown: str, page: Any, config: Any, files: Any) -> str:
    del files
    config_path = getattr(config, "config_file_path", None)
    repository_root = (
        Path(config_path).resolve().parent if config_path else Path.cwd().resolve()
    )
    docs_dir = Path(config["docs_dir"]).resolve()
    extra = config.get("extra", {})
    branch = extra.get("repository_branch", "main")
    return transform_markdown(
        markdown,
        Path(page.file.abs_src_path).resolve(),
        docs_dir,
        repository_root,
        config["repo_url"],
        branch,
    )
