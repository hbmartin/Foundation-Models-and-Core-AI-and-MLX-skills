#!/usr/bin/env python3
"""Apply DocC's section-link fix-its to a disposable generated catalog.

GitHub and DocC derive different anchors for the same Markdown headings.  A
first, non-publishing DocC conversion reports the exact anchor spellings that
its installed version accepts.  This tool applies only those structured DocC
fix-its, and only to Markdown files inside the generated catalog.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlparse


UNRESOLVED_TOPIC = "org.swift.docc.unresolvedTopicReference"
GENERATED_MARKER_SUFFIX = ".generated-by-build-docc-site"
ANCHOR_SUMMARY = re.compile(
    r"^'(?P<old>.*)' (?:is not an anchor of|doesn't exist at) '.*'$",
    re.DOTALL,
)
DOC_FRAGMENT = re.compile(r"<doc:[^>]*#(?P<fragment>[^>]+)>")


class CanonicalizationError(RuntimeError):
    """A diagnostic could not be safely applied to the generated catalog."""


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def diagnostic_source(value: str) -> Path:
    parsed = urlparse(value)
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
        raise CanonicalizationError(f"unsupported DocC diagnostic source: {value}")
    return Path(unquote(parsed.path)).resolve()


def replacement_text(diagnostic: dict[str, object]) -> str | None:
    solutions = diagnostic.get("solutions")
    if not isinstance(solutions, list) or not solutions:
        # The page resolved but the GitHub fragment did not. Falling back to
        # the page route is preferable to publishing a broken section link.
        return None
    solution = solutions[0]
    if not isinstance(solution, dict):
        raise CanonicalizationError(
            f"invalid DocC solution for: {diagnostic.get('summary')}"
        )
    replacements = solution.get("replacements")
    if not isinstance(replacements, list) or len(replacements) != 1:
        raise CanonicalizationError(
            f"expected one DocC replacement for: {diagnostic.get('summary')}"
        )
    text = replacements[0].get("text")
    if not isinstance(text, str) or not text:
        raise CanonicalizationError(
            f"DocC supplied an empty replacement for: {diagnostic.get('summary')}"
        )
    # DocC's topic-reference parser collapses literal repeated hyphens before
    # resolution, even when its own fix-it asks for the repeated form. Such a
    # landmark cannot be expressed reliably as a <doc:> fragment, so keep the
    # resolved page link and drop only that fragment.
    if "--" in text:
        return None
    return text


def docc_reported_fragment(fragment: str) -> str:
    """A fragment as DocC's resolver echoes it in diagnostics.

    Before resolution DocC percent-decodes the fragment, drops underscores,
    collapses repeated hyphens, and trims edge hyphens, so a diagnostic's
    spelling can differ from the literal ``<doc:...#fragment>`` in the
    generated Markdown (Swift 6.2's docc reports '#a--omit-x_y' as
    'a-omit-xy'). Combining marks are ignored on both sides because the
    catalog drops a GitHub-faithful anchor's leading U+FE0F while diagnostics
    echo the mark.
    """
    decoded = "".join(
        ch
        for ch in unquote(fragment)
        if unicodedata.category(ch) not in ("Mn", "Me")
    )
    return re.sub(r"-{2,}", "-", decoded.replace("_", "")).strip("-")


def replace_fragment(
    lines: list[str], old: str, new: str | None, line_number: int | None, source: Path
) -> bool:
    old_token = f"#{old}"
    if "#" in old:
        # A fragment whose first character is a combining mark merges with
        # the '#' separator into one grapheme, so DocC echoes the whole
        # page#fragment as a single unresolved topic. Match on the fragment.
        old = old.split("#", 1)[1]

    def replace_on_line(index: int) -> bool | None:
        if not 0 <= index < len(lines):
            return None
        line = lines[index]
        links = list(DOC_FRAGMENT.finditer(line))
        exact_matches = [link for link in links if link.group("fragment") == old]
        if len(exact_matches) == 1:
            matches = exact_matches
        elif len(exact_matches) > 1:
            return None
        else:
            # DocC normalizes punctuation in diagnostics. Restrict that
            # fallback to the actual <doc:...> fragment instead of replacing
            # a same-line URL.
            normalized_old = docc_reported_fragment(old)
            matches = [
                link
                for link in links
                if docc_reported_fragment(link.group("fragment"))
                == normalized_old
            ]
        if len(matches) == 1:
            link = matches[0]
            start, end = link.span("fragment")
            replacement = new or ""
            if new is None:
                start -= 1  # remove the fragment's leading '#', too
            lines[index] = line[:start] + replacement + line[end:]
            return True
        if len(matches) > 1:
            return None
        if new is not None and any(
            link.group("fragment") == new for link in links
        ):
            return False
        if new is None and not links and "<doc:" in line:
            return False
        return None

    candidate_indexes: list[int] = []
    if isinstance(line_number, int) and line_number > 0:
        candidate_indexes.append(line_number - 1)

    for index in dict.fromkeys(candidate_indexes):
        result = replace_on_line(index)
        if result is not None:
            return result

    normalized_old = docc_reported_fragment(old)
    occurrences = [
        index
        for index, line in enumerate(lines)
        if any(
            link.group("fragment") == old
            or docc_reported_fragment(link.group("fragment")) == normalized_old
            for link in DOC_FRAGMENT.finditer(line)
        )
    ]
    if len(occurrences) == 1:
        result = replace_on_line(occurrences[0])
        if result is not None:
            return result
    if not occurrences and new is not None and any(
        any(link.group("fragment") == new for link in DOC_FRAGMENT.finditer(line))
        for line in lines
    ):
        return False
    raise CanonicalizationError(
        f"could not uniquely locate DocC fragment {old_token!r} in {source}"
    )


def canonicalize(catalog: Path, diagnostics_path: Path) -> tuple[int, int]:
    catalog = catalog.resolve()
    if catalog.suffix != ".docc" or not catalog.is_dir():
        raise CanonicalizationError(f"generated DocC catalog does not exist: {catalog}")
    marker = catalog.parent / f".{catalog.name}{GENERATED_MARKER_SUFFIX}"
    if not marker.is_file():
        raise CanonicalizationError(
            f"refusing to edit catalog without generated marker: {catalog}"
        )
    payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise CanonicalizationError(f"invalid DocC diagnostics file: {diagnostics_path}")

    files: dict[Path, list[str]] = {}
    changed_files: set[Path] = set()
    applied = 0

    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            continue
        identifier = diagnostic.get("id")
        # Apple-platform DocC emits the identifier; Swift 6.3.3's Linux JSON
        # omits it. In the latter form, recognize the same diagnostic by its
        # tightly constrained summary and validate its source/replacement below.
        if identifier is not None and identifier != UNRESOLVED_TOPIC:
            continue
        summary = diagnostic.get("summary")
        if not isinstance(summary, str):
            if identifier == UNRESOLVED_TOPIC:
                raise CanonicalizationError("DocC unresolved-link diagnostic has no summary")
            continue
        match = ANCHOR_SUMMARY.fullmatch(summary)
        if not match:
            if identifier is None:
                continue
            # A missing page is not an anchor spelling difference and must not
            # be hidden. Fail here with a clearer error than the second pass.
            raise CanonicalizationError(f"unresolved DocC page reference: {summary}")
        source_value = diagnostic.get("source")
        if not isinstance(source_value, str):
            raise CanonicalizationError(f"DocC diagnostic has no source: {summary}")
        source = diagnostic_source(source_value)
        if not is_within(source, catalog) or source.suffix.casefold() != ".md":
            raise CanonicalizationError(
                f"refusing to apply a DocC fix outside the generated catalog: {source}"
            )

        lines = files.setdefault(
            source, source.read_text(encoding="utf-8").splitlines(keepends=True)
        )
        location = diagnostic.get("range")
        start = location.get("start") if isinstance(location, dict) else None
        line_number = start.get("line") if isinstance(start, dict) else None
        changed = replace_fragment(
            lines,
            match.group("old"),
            replacement_text(diagnostic),
            line_number if isinstance(line_number, int) else None,
            source,
        )
        if changed:
            changed_files.add(source)
            applied += 1

    for source in sorted(changed_files):
        source.write_text("".join(files[source]), encoding="utf-8")
    return applied, len(changed_files)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        applied, file_count = canonicalize(arguments.catalog, arguments.diagnostics)
    except (CanonicalizationError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Applied {applied} DocC anchor corrections across {file_count} generated files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
