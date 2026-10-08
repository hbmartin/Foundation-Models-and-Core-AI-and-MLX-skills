"""Fail-closed Python fence reader shared by guide guards and native verification.

Metadata immediately precedes a fence, for example:
<!-- coreai-example: {"id": "state-protocol"} -->
Historical exemptions additionally require a pinned converter and core version.
Unmarked fences describe the current release. No third-party imports are needed.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
import json
from pathlib import Path
import re
import tokenize

from scripts.mdlinks import FENCE, fence_opener, iter_lines

PARTS = (7, 8, 9, 10, 17)
MARKER = re.compile(r"<!-- coreai-example: (.+) -->")
ID = re.compile(r"[a-z][a-z0-9-]*\Z")
HISTORICAL = {"0.4.0": "1.0.0b1", "0.4.1": "1.0.0b2", "0.4.2": "1.0.0b2"}


@dataclass(frozen=True)
class Example:
    path: Path
    line: int
    code: str
    id: str | None = None
    historical: dict[str, str] | None = None


def unquote(line: str, depth: int) -> str:
    for _ in range(depth):
        match = re.match(r"^ {0,3}>[ \t]?", line)
        if not match:
            if not line.strip():
                return ""
            raise ValueError("code line leaves its blockquote")
        line = line[match.end():]
    return line


def python_fences(text: str, path: Path = Path("<fixture>")) -> list[Example]:
    examples = []
    lines = text.splitlines()
    i = 0
    pending = None
    seen_ids = set()
    while i < len(lines):
        line = lines[i]
        if "<!-- coreai-example:" in line:
            match = MARKER.fullmatch(line.lstrip(" >"))
            if not match or pending is not None:
                raise ValueError(f"{path}:{i + 1}: malformed example metadata")
            pending = json.loads(match[1])
            if not isinstance(pending, dict) or set(pending) - {"id", "historical"}:
                raise ValueError(f"{path}:{i + 1}: invalid metadata fields")
            name = pending.get("id")
            if not isinstance(name, str) or not ID.fullmatch(name) or name in seen_ids:
                raise ValueError(f"{path}:{i + 1}: invalid or duplicate example ID")
            seen_ids.add(name)
            history = pending.get("historical")
            if "historical" in pending and (
                not isinstance(history, dict)
                or set(history) != {"coreai-torch", "coreai-core"}
                or HISTORICAL.get(history.get("coreai-torch")) != history.get("coreai-core")
            ):
                raise ValueError(f"{path}:{i + 1}: invalid historical exemption")
            i += 1
            continue
        match = fence_opener(line)
        if not match:
            if pending is not None and line.strip():
                raise ValueError(f"{path}:{i + 1}: metadata must immediately precede a fence")
            i += 1
            continue
        fence = match[1]
        language = line[match.end():].strip()
        if language.split()[:1] in (["python"], ["py"]) and language not in ("python", "py"):
            raise ValueError(f"{path}:{i + 1}: unsupported Python fence info")
        depth = line[:match.start(1)].count(">")
        start = i + 2
        body = []
        i += 1
        while i < len(lines):
            closer = FENCE.match(lines[i])
            if (closer and lines[i][:closer.start(1)].count(">") == depth
                    and closer[1][0] == fence[0] and len(closer[1]) >= len(fence)
                    and not lines[i][closer.end():].strip()):
                break
            body.append(unquote(lines[i], depth) if language in ("python", "py") else lines[i])
            i += 1
        if i == len(lines):
            raise ValueError(f"{path}:{start - 1}: unclosed fence")
        if language in ("python", "py"):
            example = Example(path, start, "\n".join(body) + "\n", **(pending or {}))
            # Validate even historical blocks: an exemption is not a parse-error bypass.
            list(code_tokens(example))
            examples.append(example)
        elif pending is not None:
            raise ValueError(f"{path}:{start - 1}: metadata requires a Python fence")
        pending = None
        i += 1
    if pending is not None:
        raise ValueError(f"{path}: dangling example metadata")
    return examples


def code_tokens(example: Example):
    ignored = {tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE,
               tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER}
    try:
        for token in tokenize.generate_tokens(io.StringIO(example.code).readline):
            if token.type == tokenize.ERRORTOKEN and not token.string.isspace():
                raise ValueError(f"invalid token {token.string!r}")
            if token.type == tokenize.NAME and not token.string.isidentifier():
                raise ValueError(f"invalid identifier {token.string!r}")
            if token.type not in ignored and not token.string.isspace():
                yield token
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError) as error:
        raise ValueError(f"{example.path}:{example.line}: tokenization failed: {error}") from error


def optimizer_calls(example: Example) -> list[int]:
    tokens = list(code_tokens(example))
    return [example.line + tokens[i].start[0] - 1 for i in range(len(tokens) - 2)
            if tokens[i].string == "." and tokens[i + 1].type == tokenize.NAME
            and tokens[i + 1].string == "optimize" and tokens[i + 2].string == "("]


def guide_examples(root: Path) -> list[Example]:
    examples = [example for part in PARTS
            for directory in sorted((root / "guides").glob(f"part-{part:02d}-*"))
            for path in sorted(directory.rglob("*.md"))
            for example in python_fences(path.read_text(encoding="utf-8"), path)]
    seen = set()
    for example in examples:
        if example.id is not None:
            if example.id in seen:
                raise ValueError(f"{example.path}:{example.line}: duplicate corpus example ID {example.id}")
            seen.add(example.id)
    return examples


def removed_optimizer_errors(root: Path) -> list[str]:
    return [f"{example.path}:{line}: removed .optimize() call"
            for example in guide_examples(root) if example.historical is None
            for line in optimizer_calls(example)]


def section(text: str, heading: str) -> str:
    """Read a named section without swallowing following peer sections."""
    lines = list(iter_lines(text))
    start = next((i for i, (line, _, fenced) in enumerate(lines)
                  if not fenced and line.startswith(heading)), None)
    if start is None:
        raise ValueError(f"missing heading: {heading}")
    level = len(lines[start][0]) - len(lines[start][0].lstrip("#"))
    end = next((i for i in range(start + 1, len(lines))
                if not lines[i][2] and re.match(rf"^#{{1,{level}}} ", lines[i][0])), len(lines))
    return "".join(line + newline for line, newline, _ in lines[start:end]).removesuffix("\n")


def prose_segments(text: str, *, contrast: bool = False) -> list[str]:
    """Keep wrapped prose together, but stop predicates at sentence/list boundaries."""
    boundary = r"[;!?]|\.(?=\s|$)|\n(?=\s*(?:>\s*)*(?:[-*+] |\d+[.)] ))"
    if contrast:
        boundary += r"|\b(?:and|while|whereas|but)\b"
    return re.split(boundary, text, flags=re.I)


def negated_predicate(prefix: str) -> bool:
    # Limit negation to the predicate's verb phrase, including passive auxiliaries.
    return bool(re.search(
        r"(?:\b(?:not|never|no|cannot)|\b\w+n['’]t)"
        r"(?:\s+(?:yet|still|currently|silently|automatically|ever|been|be|being|have|has|had|will|do|does|did))*"
        r"[\s`*]*$", prefix, re.I))


_ASSET_DESTINATION = (
    r"(?:\b(?:destinations?|assets?|files?|director(?:y|ies)|paths?|outputs?|bundles?|targets?)\b"
    r"|[^\s;,]+\.aimodel\b)"
    r"(?!\s+(?:metadata|validation|parity|gates?|checks?|records?|fields?)\b)"
)
_REPLACEMENT = r"(?:overwrites?|overwrote|overwritten|overwriting|replace[sd]?|replacing)"
_OVERWRITE_CONTRACT = (
    "AIProgram.save_asset in coreai-core 1.0.0b3 replaces an existing file or directory "
    "at the destination."
)


def asset_replacement_claim(prefix: str, suffix: str) -> bool:
    """Recognize bounded destination claims, not arbitrary English predicates."""
    modifiers = r"(?:\s+(?:of|the|an?|any|existing|specified|current|old|output))*"
    auxiliaries = (
        r"(?:\s+(?:will|would|can|could|is|are|was|were|be|been|being|has|have|had|do|does|did|"
        r"not|never|no|cannot|yet|still|currently|silently|automatically|ever|\w+n['’]t))*"
    )
    if re.match(rf"{modifiers}\s+{_ASSET_DESTINATION}", suffix, re.I):
        return True
    compound = rf"(?:\s+and\s+(?:(?:its|their)\s+contents|(?:the\s+)?{_ASSET_DESTINATION}))?"
    if re.search(rf"{_ASSET_DESTINATION}{compound}{auxiliaries}\s*$", prefix, re.I):
        return True
    # Bare API claims and pronoun objects imply the destination. Other explicit
    # objects (for example metadata or a parity gate) do not inherit that context.
    api_subject = re.search(
        rf"\b(?:AIProgram\.)?save_asset(?:\(\))?{auxiliaries}\s*$", prefix, re.I)
    return bool(api_subject and (not suffix.strip() or re.match(
        r"\s+(?:it|them|this|that)\b", suffix, re.I)))


def overwrite_contract_errors(text: str) -> list[str]:
    """Require the versioned prose contract and lint known contradiction families.

    The canonical statement is the positive guarantee. The accompanying bounded
    checks catch known regressions; they do not attempt to parse arbitrary English.
    Fences and hidden comments cannot stand in for the reader-visible statement.
    """
    visible = re.sub(r"<!--.*?(?:-->|$)", "\n", text, flags=re.S)
    visible = "".join(line + newline for line, newline, fenced in iter_lines(visible) if not fenced)
    visible = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", visible)
    visible = re.sub(r"[`*]|(?<!\w)_{1,2}|_{1,2}(?!\w)", "", visible)
    errors = []
    if _OVERWRITE_CONTRACT not in " ".join(visible.split()):
        errors.append("b3 overwrite contract statement missing")
    return errors + contract_errors(text, "overwrite")


def contract_errors(text: str, contract: str) -> list[str]:
    """Semantic checks scoped by callers to the relevant heading/defect row."""
    errors = []
    if contract == "state":
        if re.search(r"(?:requires?|required|must|mandatory).*?`?(?:program\.)?optimize\(\)", text, re.I):
            errors.append("state rewriting incorrectly requires optimize()")
        if re.search(r"optimize\(\).*?(?:required|mandatory)", text, re.I):
            errors.append("optimizer incorrectly marked required")
    elif contract == "rewrite":
        if "AIProgram(module)" in text and re.search(r"with.block.*exits|context.*exit", text, re.I):
            if "with module:" not in text:
                errors.append("rewrite assigned to AIProgram rather than module context")
    elif contract == "issue49":
        square = r"\b(?:square|equal[- ]length)\b"
        rectangular = r"(?:\b(?:rectangular|unequal(?:[- ]length)?)\b|17\s*[×x]\s*23)"
        success = r"\b(?:hid(?:e[sn]?|den)?|passed|passes|correct|unaffected)\b"
        failure = r"\b(?:exposed?|exposes|failed|fails|miscompil(?:e[sd]?|ing))\b"
        if not re.search(square, text, re.I) or not re.search(rectangular, text, re.I):
            return errors
        for clause in prose_segments(text, contrast=True):
            shapes = list(re.finditer(rf"{square}|{rectangular}", clause, re.I))
            for predicate in re.finditer(rf"{success}|{failure}", clause, re.I):
                if negated_predicate(clause[:predicate.start()]):
                    continue
                if not shapes:
                    continue
                shape = min(shapes, key=lambda m: min(abs(m.end() - predicate.start()),
                                                      abs(predicate.end() - m.start())))
                if min(abs(shape.end() - predicate.start()), abs(predicate.end() - shape.start())) > 120:
                    continue
                square_shape = bool(re.fullmatch(square, shape.group(), re.I))
                success_predicate = bool(re.fullmatch(success, predicate.group(), re.I))
                if square_shape == success_predicate:
                    errors.append("square/rectangular #49 explanation reversed")
                    return errors
    elif contract == "overwrite":
        for clause in prose_segments(text):
            clause = re.sub(r"[`*]", "", clause)
            clause = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", clause)
            for predicate in re.finditer(rf"\b{_REPLACEMENT}\b", clause, re.I):
                prefix, suffix = clause[:predicate.start()], clause[predicate.end():]
                # A coordinated replacement verb inherits the same negation.
                prefix = re.sub(rf"(?:\b{_REPLACEMENT}\s+(?:and|or)\s+)+$", "", prefix, flags=re.I)
                if asset_replacement_claim(prefix, suffix) and negated_predicate(prefix):
                    errors.append("b3 overwrite behavior incorrect")
                    return errors
            failure = re.search(r"\bwill\s+fail\b", clause, re.I)
            existence = re.search(
                rf"\b(?:if|when|because)\s+(?:(?:the|an?|any|existing|specified|current|old)\s+)*"
                rf"{_ASSET_DESTINATION}(?:\s+path)?\s+(?:already\s+)?exists?\b"
                rf"|\bon\s+(?:an?\s+)?existing\s+{_ASSET_DESTINATION}", clause, re.I)
            if (failure
                    and re.search(r"\b(?:save_asset|converter|b3|sav(?:e|es|ing))\b", clause[:failure.start()], re.I)
                    and not negated_predicate(clause[:failure.start()])
                    and existence):
                errors.append("b3 overwrite behavior incorrect")
                return errors
    else:
        raise ValueError(f"unknown contract: {contract}")
    return errors
