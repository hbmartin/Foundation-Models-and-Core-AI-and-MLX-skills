"""Markdown link scanning and path helpers, shared by the guide tooling.

Companion to scripts/mdslug.py. That module owns heading anchors; this one owns
everything needed to walk a guide's inline links without corrupting the parts of
the document that only look like links.

Two traps this module exists to avoid, both of which a naive `\\]\\(` regex falls
into:

* Fenced and blockquoted code contains link-shaped text. `[Int](repeating: 0,
  count: rank)` is a Swift subscript and `> [](mx::StreamOrDevice s) {` is quoted
  C++, and there are eight such spans in the corpus. FENCE deliberately matches a
  fence that is *inside* a block quote, because the guides quote hundreds of code
  blocks inside evidence callouts.
* Link destinations nest. `[text](path/to(file).md)` and `[text](<a b.md>)` both
  need balanced scanning, and an inline code span may contain a bare `](`.

FENCE, split_destination, page_target, is_within, github_url, sha256 and
source_snapshot were extracted verbatim from scripts/build-docc-site.py, which
now imports them from here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import hashlib
from pathlib import Path
import re
from urllib.parse import quote

# A fence, optionally nested in any depth of block quote. extract-callouts.py
# uses a deliberately stricter pattern that ignores blockquoted fences, because
# it relies on the "> " prefix to suppress headings; anything that rewrites
# content must use this one or it will edit quoted source code.
FENCE = re.compile(r"^(?: {0,3}>[ \t]?)* {0,3}(`{3,}|~{3,})")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_snapshot(source_root: Path) -> dict[Path, str]:
    return {path.resolve(): sha256(path) for path in sorted(source_root.rglob("*.md"))}


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def page_target(candidate: Path, raw_path: str) -> Path:
    if raw_path.endswith("/") or candidate.is_dir():
        return candidate / "README.md"
    return candidate


def github_url(
    target: Path,
    repository_root: Path,
    repository_url: str,
    branch: str,
    fragment: str,
) -> str:
    relative = target.relative_to(repository_root).as_posix()
    object_kind = "tree" if target.is_dir() else "blob"
    url = (
        f"{repository_url.rstrip('/')}/{object_kind}/"
        f"{quote(branch, safe='')}/{quote(relative, safe='/')}"
    )
    return f"{url}#{fragment}" if fragment else url


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


def iter_lines(text: str) -> Iterator[tuple[str, str, bool]]:
    """Yield (body, newline, inside_fence) for every line, tracking fences.

    A line that opens or closes a fence reports inside_fence=True along with the
    content between them, so a caller can copy every fenced line through
    untouched. That keeps ```swift compile:27 info strings and their bodies
    byte-identical, which scripts/verify-snippets.py depends on.
    """
    fence: str | None = None
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\n")
        newline = raw[len(body) :]
        match = FENCE.match(body)
        if fence is None:
            if match:
                fence = match.group(1)
                yield body, newline, True
                continue
            yield body, newline, False
            continue
        # Inside a fence: only a run of the same character, at least as long as
        # the opener, closes it.
        if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
            fence = None
        yield body, newline, True


def scan_inline_links(line: str, rewrite_body: Callable[[str], str]) -> str:
    """Rewrite inline Markdown link destinations while ignoring inline code.

    rewrite_body receives the raw text between the parentheses of a `](...)` and
    returns its replacement, so callers can resolve destinations however they
    like without reimplementing the scanner.
    """
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
            result.append(rewrite_body(line[body_start:cursor]))
            result.append(")")
            index = cursor + 1
            continue

        result.append(line[index])
        index += 1
    return "".join(result)
