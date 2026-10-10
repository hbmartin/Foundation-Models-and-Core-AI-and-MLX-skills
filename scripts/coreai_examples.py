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

from scripts.mdlinks import FENCE, code_span_delimiter, fence_closer, fence_opener, iter_lines

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
        rf"(?:\b(?:not|never|no|cannot|neither)|\b\w+n['’]t)"
        rf"(?:\s+{_CLAIM_AUXILIARY})*[\s`*]*$", prefix, re.I))


_REPLACEMENT = r"(?:overwrites?|overwrote|overwritten|overwriting|replace[sd]?|replacing)"
_FAILURE = r"(?:will\s+fail|fails?|raises?\s+(?:a\s+)?FileExistsError|errors?\s+out)"
_CLAIM_AUXILIARY = (
    r"(?:will|would|can|could|is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"not|never|no|cannot|neither|yet|still|currently|silently|automatically|ever|performs|\w+n['’]t)"
)
_SAVING_SUBJECT = r"(?:\b(?:\w+\.)?save_asset(?:\(\))?|\b(?:converter|b3|save|saves|saving))"
_SAVING_ANTECEDENT = r"(?:\b(?:\w+\.)?save_asset(?:\(\))?|\b(?:converter|b3))"
_CLAIM_MODIFIER = (
    rf"(?:\s+{_CLAIM_AUXILIARY}|\s+also|\s+by\s+default|"
    r"\s+in\s+coreai-core\s+1\.0\.0b3\b|\s*,\s*unlike\s+[\w.-]+\s*,)"
)
_DESTINATION_MODIFIERS = (r"(?:(?:the|an?|any|existing|specified|current|old|output|target|destinations?|"
                          r"asset|metadata|its|their|this|that|saved)\s+)*")
_DESTINATION_HEAD = (r"(?:[^\s;,]+\.aimodel\b|(?:destinations?|assets?|files?|director(?:y|ies)|"
                     r"paths?|outputs?|bundles?|targets?)\b)")
_DESTINATION_PHRASE = re.compile(
    rf"(?P<modifiers>{_DESTINATION_MODIFIERS})(?P<head>{_DESTINATION_HEAD})", re.I,
)
_NON_FILESYSTEM = re.compile(
    r"\s+(?:metadata|validation|parity|gates?|checks?|records?|fields?|dtype|devices?|tildes?)\b", re.I,
)
_OVERWRITE_CONTRACT = (
    "AIProgram.save_asset in coreai-core 1.0.0b3 replaces an existing file or directory "
    "at the destination."
)


def _saving_call_names(text: str, *, comments: list[tuple[str, str]] | None = None) -> str:
    """Mask balanced arguments so their punctuation cannot split a prose claim."""
    result, start = [], 0
    fenced_ranges, offset, fence_start = [], 0, None
    for body, newline, fenced in iter_lines(text):
        if fenced and fence_start is None:
            fence_start = offset
        elif not fenced and fence_start is not None:
            fenced_ranges.append((fence_start, offset))
            fence_start = None
        offset += len(body) + len(newline)
    if fence_start is not None:
        fenced_ranges.append((fence_start, offset))
    for call in re.finditer(r"\b(?:\w+\.)?save_asset\s*\(", text):
        if call.start() < start:
            continue
        i, depth, quote = call.end(), 1, None
        limit = next((end for begin, end in fenced_ranges if begin <= call.start() < end), None)
        if limit is None:
            boundary = re.search(r"\n[ \t]*\n", text[call.end():])
            limit = call.end() + boundary.start() if boundary else len(text)
        call_comments = []
        while i < limit and depth:
            if quote:
                if text[i] == "\\":
                    i += 2
                    continue
                if text.startswith(quote, i):
                    i += len(quote)
                    quote = None
                    continue
            elif text[i] in "\"'":
                # A prose possessive isn't a Python string opener. Keep actual
                # Python string prefixes (r'...', f'...', etc.) working.
                word = re.search(r"[A-Za-z]+$", text[:i])
                if (text[i] == "'" and word and i + 1 < limit and text[i + 1].isalnum()
                        and word[0].lower() not in {"r", "b", "u", "f", "br", "rb", "fr", "rf"}):
                    i += 1
                    continue
                quote = text[i] * (3 if text.startswith(text[i] * 3, i) else 1)
                i += len(quote)
                continue
            elif text[i] == "#":
                end = text.find("\n", i)
                end = limit if end < 0 else min(end, limit)
                call_comments.append(text[i:end])
                i = end
                continue
            elif text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        if not depth:
            result.extend((text[start:call.start()], call[0].rstrip()[:-1].strip() + "()"))
            if comments is not None:
                owner = call[0].rstrip()[:-1].strip() + "()"
                comments.extend((owner, comment.lstrip("# ")) for comment in call_comments)
            start = i
    result.append(text[start:])
    return "".join(result)


def _saving_subject(prefix: str) -> bool:
    prefix = _saving_call_names(prefix)
    return not _historical_claim(prefix) and bool(re.search(
        rf"{_SAVING_SUBJECT}{_CLAIM_MODIFIER}*\s*$", prefix, re.I))


def _historical_claim(text: str) -> bool:
    return bool(re.search(r"\b(?:in|as\s+in)\s+coreai-core\s+(?!1\.0\.0b3\b)[\w.]+", text, re.I))


def _saving_antecedent(text: str) -> str | None:
    match = re.match(
        rf"(?:the\s+)?({_SAVING_ANTECEDENT})\b(?:\(\))?"
        rf"(?=\s*$|\s+(?:{_CLAIM_AUXILIARY}|writes?|saves?|validates?|preserves?|"
        rf"{_REPLACEMENT}|{_FAILURE}|also|by|in)\b|\s*,\s*unlike\b)", text, re.I,
    )
    return match[1] if match else None


def _table_prose(line: str) -> str:
    """Join actual table cells, leaving escaped and inline-code pipes intact."""
    cells, cell, delimiter, i = [], [], 0, 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            cell.append(line[i:i + 2])
            i += 2
            continue
        if line[i] == "`":
            end = i + 1
            while end < len(line) and line[end] == "`":
                end += 1
            delimiter = code_span_delimiter(delimiter, end - i)
            cell.append(line[i:end])
            i = end
            continue
        if line[i] == "|" and not delimiter:
            cells.append("".join(cell).strip())
            cell.clear()
        else:
            cell.append(line[i])
        i += 1
    cells.append("".join(cell).strip())
    cells = [cell for cell in cells if cell]
    if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
        return ""
    return " ".join(cells)


def _destination_phrase(text: str, *, qualified: bool = False, complete: bool = False) -> bool:
    """Match the head of a filesystem noun phrase, including an asset metadata file."""
    text = text.strip()
    match = _DESTINATION_PHRASE.match(text)
    if not match or _NON_FILESYSTEM.match(text[match.end():]):
        return False
    if complete and text[match.end():].strip():
        return False
    if re.search(r"\bmetadata\b", match["modifiers"], re.I) and not re.fullmatch(r"files?", match["head"], re.I):
        return False
    # Bare paths/targets/outputs can describe strings, devices or dtypes. Passive
    # claims need an existing/qualified destination or a concrete filesystem head.
    return not (qualified and re.fullmatch(r"paths?|outputs?|bundles?|targets?", match["head"], re.I)
                and not re.search(r"\b(?:existing|specified|current|old|output|target|saved)\b",
                                  match["modifiers"], re.I))


def _destination_subject(prefix: str) -> bool:
    subject = re.sub(rf"(?:\s+{_CLAIM_AUXILIARY})+\s*$", "", prefix.strip(), flags=re.I)
    nouns = re.split(r"\s+and\s+", subject, flags=re.I)
    return bool(nouns and _destination_phrase(nouns[0], qualified=True, complete=True)
                and all(re.fullmatch(r"(?:its|their)\s+contents", noun, re.I)
                        or _destination_phrase(noun, qualified=True, complete=True) for noun in nouns[1:]))


def _overwrite_clauses(text: str) -> list[str]:
    """Separate independent subjects without breaking coordinated verbs or nouns."""
    comments = []
    text = re.sub(r"(?m)^(?: {0,3}>[ \t]?)+", "", text)
    text = _saving_call_names(text, comments=comments)
    text = "\n".join("\n\n" + _table_prose(line) + "\n\n"
                     if line.strip().startswith("|") else line for line in text.splitlines())
    text = re.sub(r"(?m)^ {0,3}(?:[-*+]\s+|\d+[.)]\s+)", "\n\n", text)
    text = re.sub(r"(?m)^ {0,3}(?:⚠️|✅)\s*\*\*[^*\n]+\*\*(?:[ \t]*[—–:-][ \t]*|[ \t]+)", "", text)
    text = re.sub(r"(?im)^\s*In\s+coreai-core\s+1\.0\.0b3\s*,\s*", "", text)
    new_subject = (rf"(?!but\b|and\b|while\b|whereas\b|{_CLAIM_AUXILIARY}\b)"
                   rf"(?:{_SAVING_SUBJECT}|{_DESTINATION_MODIFIERS}{_DESTINATION_HEAD}|(?:the\s+)?[\w.]+)\s+"
                   rf"(?:{_CLAIM_AUXILIARY}\s+)*(?:{_FAILURE}|{_REPLACEMENT})\b")
    inherited_predicate = rf"(?:{_CLAIM_AUXILIARY}\s+)*(?:{_REPLACEMENT}|{_FAILURE})\b"
    clauses = []
    for paragraph in re.split(r"\n\s*\n", text):
        antecedent = None
        for sentence in prose_segments(paragraph):
            sentence = re.sub(r"[`*]", "", sentence).strip()
            sentence = re.sub(r"^(?:[-+]\s+|\d+[.)]\s+|Note:\s*)", "", sentence, flags=re.I)
            contrasts = re.split(
                rf"\b(?:(?:while|whereas|but)\s+(?={new_subject}|{inherited_predicate})"
                rf"|and\s+(?={_CLAIM_AUXILIARY}\s+{inherited_predicate}))",
                sentence, flags=re.I,
            )
            for position, contrast in enumerate(contrasts):
                start = 0
                parts = []
                for boundary in re.finditer(rf"(?:\band\s+|,\s*)(?={new_subject})", contrast, re.I):
                    # Noun coordinations and leading conditions stay together.
                    preceding = contrast[start:boundary.start()]
                    if (re.search(rf"\b(?:{_REPLACEMENT}|{_FAILURE})\b", preceding, re.I)
                            or _saving_antecedent(preceding)):
                        parts.append(contrast[start:boundary.start()].strip())
                        start = boundary.end()
                parts.append(contrast[start:].strip())
                for part in parts:
                    if not part:
                        continue
                    saving = _saving_antecedent(part)
                    if saving:
                        historical = _historical_claim(part)
                        antecedent = None if historical else saving
                    elif re.match(r"it\s+", part, re.I):
                        if antecedent:
                            part = re.sub(r"^it\b", lambda _: antecedent, part, flags=re.I)
                    elif position and antecedent and re.match(inherited_predicate, part, re.I):
                        part = antecedent + " " + part
                    else:
                        antecedent = None
                    clauses.append(part)
    for owner, comment in comments:
        clauses.extend(_overwrite_clauses(owner + ". " + comment))
    return clauses


def asset_replacement_claim(prefix: str, suffix: str) -> bool:
    """Require a local saving/destination subject and a filesystem replacement."""
    api_subject, destination_subject = _saving_subject(prefix), _destination_subject(prefix)
    if _historical_claim(prefix + " " + suffix):
        return False
    suffix = re.sub(rf"^(?:\s+(?:and|or|nor)\s+{_REPLACEMENT})+", "", suffix, flags=re.I)
    suffix = re.sub(r"^\s+of\s+", " ", suffix, flags=re.I).strip()
    if _destination_phrase(suffix):
        return api_subject or destination_subject
    if api_subject and re.fullmatch(r"(?:it|them|this|that)?[\s.!?]*", suffix, re.I):
        return True
    # A passive destination claim may name save_asset as its agent, but another
    # explicit agent must not inherit the surrounding section's API context.
    if not destination_subject:
        return False
    dependency = re.match(r",\s*which\s+(?:the\s+)?([\w.]+)\s+relies\s+on\b", suffix, re.I)
    if dependency and not re.fullmatch(_SAVING_ANTECEDENT, dependency[1], re.I):
        return False
    suffix = re.sub(r"^(?:,\s*)?by\s+default\b\s*", "", suffix, flags=re.I)
    if re.match(r"(?:,\s*)?by\s+", suffix, re.I):
        return bool(re.fullmatch(
            rf"(?:,\s*)?by\s+{_SAVING_SUBJECT}(?:\s*[,].*)?[\s.!?]*", suffix, re.I))
    return not suffix or suffix.startswith(",") or bool(re.match(
        r"(?:so|therefore|because|but\s+(?:preserved|retained|kept))\b", suffix, re.I))


def _destination_existence(clause: str) -> bool:
    if re.search(r",\s*(?:only|provided)\b|,\s*(?:but|and)\s+"
                 rf"(?:(?:it|{_DESTINATION_MODIFIERS}{_DESTINATION_HEAD})\s+)?"
                 r"(?:is|are|has|have|must|needs?)\b", clause, re.I):
        return False
    condition = clause.split(",", 1)[0].strip().rstrip(".!?")
    match = re.fullmatch(r"(?:if|when|because)\s+(.+?)\s+(?:already\s+)?exists?"
                         r"(?:\s+already)?(?:\s+on\s+disk|\s+at\s+(.+))?", condition, re.I)
    if match:
        return ((_destination_phrase(match[1], complete=True)
                 or (match[1].lower() == "something" and bool(match[2])))
                and (not match[2] or _destination_phrase(match[2], complete=True)))
    match = re.fullmatch(r"(?:on|when\s+writing\s+to)\s+((?:(?:an?|the)\s+)?existing\s+.+)", condition, re.I)
    return bool(match and _destination_phrase(match[1], complete=True))


def _destination_failure(clause: str) -> bool:
    if _historical_claim(clause):
        return False
    for failure in re.finditer(rf"\b{_FAILURE}\b", clause, re.I):
        prefix, suffix = clause[:failure.start()], clause[failure.end():].strip()
        suffix = re.sub(r"^(?:(?:immediately|silently|automatically|unexpectedly)\s*|"
                        r"with\s+(?:an?\s+)?(?:FileExistsError|error)\b\s*)*", "", suffix, flags=re.I)
        if not _saving_subject(prefix) or negated_predicate(prefix):
            continue
        if _destination_existence(suffix):
            return True
        if not suffix:
            condition = prefix.split(",", 1)
            if len(condition) == 2 and _destination_existence(condition[0]):
                return True
            if "fileexistserror" in failure[0].lower() and len(condition) == 1:
                return True
    return False


def _contract_paragraphs(text: str) -> list[str]:
    """Extract the bounded prose forms used for the affirmative guarantee."""
    paragraphs, lines = [], []
    fence, comment, code_delimiter = None, False, 0

    def flush():
        if lines:
            paragraphs.append(" ".join(lines))
            lines.clear()

    for line in text.splitlines():
        line = re.sub(r"^(?: {0,3}>[ \t]?)+", "", line)
        if fence:
            if fence_closer(line, fence):
                fence = None
            continue
        opener = fence_opener(line) if not comment and not code_delimiter else None
        if opener:
            flush()
            fence = opener[1]
            continue
        if not line.strip() or (not comment and not code_delimiter
                               and line.expandtabs(4).startswith("    ")):
            flush()
            code_delimiter = 0
            continue
        visible = []
        i = 0
        while i < len(line):
            if comment:
                end = line.find("-->", i)
                if end < 0:
                    break
                comment, i = False, end + 3
            elif line[i] == "\\" and not code_delimiter:
                visible.append(line[i:i + 2])
                i += 2
            elif line[i] == "`":
                end = i + 1
                while end < len(line) and line[end] == "`":
                    end += 1
                run = end - i
                code_delimiter = code_span_delimiter(code_delimiter, run)
                visible.append(line[i:end])
                i = end
            elif not code_delimiter and line.startswith("<!--", i):
                if "".join(visible).strip():
                    lines.append("".join(visible).strip())
                visible.clear()
                flush()
                comment, i = True, i + 4
            else:
                visible.append(line[i])
                i += 1
        if "".join(visible).strip():
            lines.append("".join(visible).strip())
    flush()
    return paragraphs


def _affirmative_overwrite_contract(text: str) -> bool:
    for paragraph in _contract_paragraphs(text):
        paragraph = re.sub(r"~~.*?(?:~~|$)", " ", paragraph, flags=re.S)
        # Identifier code spans are prose formatting; a whole coded sentence is
        # an example, not an affirmative statement of the persistence guarantee.
        paragraph = re.sub(r"(`+)(.*?)\1", lambda match: match[2] if re.fullmatch(
            r"[\w.-]+(?:\(\))?", match[2]) else "\0", paragraph)
        paragraph = re.sub(r"\*|(?<!\w)_{1,2}|_{1,2}(?!\w)", "", paragraph)
        paragraph = " ".join(paragraph.split())
        paragraph = re.sub(r"^✅\s+VERIFIED(?:\s+\(b3 source\))?\s*[—–-]\s*", "", paragraph)
        if paragraph == _OVERWRITE_CONTRACT or paragraph.startswith(_OVERWRITE_CONTRACT + " "):
            return True
    return False


def overwrite_contract_errors(text: str) -> list[str]:
    """Require the versioned prose contract and lint known contradiction families.

    The canonical statement is the positive guarantee. The accompanying bounded
    checks catch known regressions; they do not attempt to parse arbitrary English.
    Fences and hidden comments cannot stand in for the reader-visible statement.
    """
    errors = []
    if not _affirmative_overwrite_contract(text):
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
        for clause in _overwrite_clauses(text):
            for predicate in re.finditer(rf"\b{_REPLACEMENT}\b", clause, re.I):
                prefix, suffix = clause[:predicate.start()], clause[predicate.end():]
                # A coordinated replacement verb inherits the same negation.
                prefix = re.sub(rf"(?:\b{_REPLACEMENT}\s+(?:and|or|nor)\s+)+$", "", prefix, flags=re.I)
                if asset_replacement_claim(prefix, suffix) and negated_predicate(prefix):
                    errors.append("b3 overwrite behavior incorrect")
                    return errors
            if _destination_failure(clause):
                errors.append("b3 overwrite behavior incorrect")
                return errors
    else:
        raise ValueError(f"unknown contract: {contract}")
    return errors
