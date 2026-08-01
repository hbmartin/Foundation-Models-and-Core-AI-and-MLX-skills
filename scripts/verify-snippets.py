#!/usr/bin/env python3
"""Compile-verify the fenced Swift snippets in guides/.

Extracts every ```swift fence, classifies it via fence info-string markers,
wraps fragments in a minimal harness, and runs `swiftc -typecheck` against the
requested SDK(s). Emits a strict-TSV row per fence plus a markdown report.

Marker grammar (space-separated tokens after `swift` in the fence info string;
canonical documentation in notes/snippet-verification/README.md):

    compile:<t>[,<t>...]   must type-check on each named target
    xfail:<t>[,<t>...]     must FAIL to type-check on each target
    imports:A,B            modules the wrapper adds beyond hoisted ones
    defines:A,B            Swift compilation conditions passed with -D
    wrap:none|body|mixed   complete file / force wrapper shape (default: auto)
    lang:5                 pin -swift-version 5 (default 6)
    isolation:mainactor    compile with Swift 6 MainActor default isolation
    illustrative           never compiled (pseudocode, stubs, elided bodies)
    prelude:<name>         reserved; reported PRELUDE-NEEDED, not compiled

TSV columns (tab-delimited, flatten()ed fields):
    file  line  anchor  info  status  wrap  v26  v27  vsim27  v27on26
    vsim27on26  err_line  first_error

Row status: VERIFIED XFAIL-PROVEN MIGRATION-PROVEN FAILED ILLUSTRATIVE STUB ELIDED
    COMMENT-ONLY
    PRELUDE-NEEDED UNCLASSIFIED UNCLASSIFIED-PASS UNCLASSIFIED-FAIL
    MARKER-ERROR PARSE-ERROR
Per-target verdicts: pass fail xfail-pass XFAIL-ERR timeout - skip

Exit codes: 0 = green/backlog only · 1 = FAILED or XFAIL-ERR rows · 2 = marker
or parse errors.

Toolchain identities are resolved per target via xcrun under DEVELOPER_DIR
(never mutating global xcode-select state, per scripts/dump-sdk-interfaces.sh)
and recorded in the report header so every verdict reads "against <sdk build>".
"""

import argparse
import concurrent.futures
import dataclasses
import hashlib
import os
import re
import subprocess
import sys

WRAPPER_VERSION = 1


@dataclasses.dataclass(frozen=True)
class TargetSpec:
    developer_dir: str
    sdk_name: str
    triple_template: str
    column: str
    sdk_generation: str
    deployment_version: "str | None" = None


# Names, not resolved SDK versions: a new beta changes the recorded toolchain
# identity without changing markers. The *-on-26 targets deliberately separate
# the SDK used to compile from the minimum deployment version encoded in the
# target triple.
TARGETS = {
    "26": TargetSpec("/Applications/Xcode.app/Contents/Developer", "macosx",
                     "arm64-apple-macos{v}", "v26", "26"),
    "27": TargetSpec("/Applications/Xcode-beta.app/Contents/Developer", "macosx",
                     "arm64-apple-macos{v}", "v27", "27"),
    "sim27": TargetSpec("/Applications/Xcode-beta.app/Contents/Developer", "iphonesimulator",
                        "arm64-apple-ios{v}-simulator", "vsim27", "27"),
    "27-on-26": TargetSpec("/Applications/Xcode-beta.app/Contents/Developer", "macosx",
                           "arm64-apple-macos{v}", "v27on26", "27", "26.0"),
    "sim27-on-26": TargetSpec("/Applications/Xcode-beta.app/Contents/Developer", "iphonesimulator",
                              "arm64-apple-ios{v}-simulator", "vsim27on26", "27", "26.0"),
}
# Frameworks that live under <platform>/Developer/Library/Frameworks (Xcode-bundled).
XCODE_ONLY_MODULES = {"Evaluations", "Testing", "XCTest"}
# Modules structurally absent from the 26-generation SDKs.
ABSENT_ON_26 = {"CoreAI", "Evaluations"}

GENERATED_PAGES = {"SILENT-FAILURES.md", "API-INDEX.md"}

DECL_KEYWORDS = (
    "import", "struct", "class", "enum", "actor", "protocol", "extension",
    "func", "typealias", "let", "var", "@", "#if", "precedencegroup",
    "operator", "public", "private", "internal", "final", "static", "//", "/*",
)

# Guess-mode import heuristics (guess mode ONLY — marked fences use hoisted +
# declared imports). Unused imports are warnings, not errors.
GUESS_ALWAYS_IMPORTS = ["Foundation", "FoundationModels"]
GUESS_KEYWORD_IMPORTS = [
    (re.compile(r"\bsome View\b|@State\b|@Observable\b|: View\b"), "SwiftUI"),
    (re.compile(r"\bAppIntent\b|\bAppEntity\b|\bAppShortcut"), "AppIntents"),
    (re.compile(r"\bSpeechAnalyzer\b|\bSpeechTranscriber\b|\bAssetInventory\b|\bDictationTranscriber\b"), "Speech"),
    (re.compile(r"\bCSSearchable|\bSpotlightSearchTool\b"), "CoreSpotlight"),
    (re.compile(r"\bAIModel\b|\bInferenceFunction\b|\bNDArray\b"), "CoreAI"),
    (re.compile(r"\bEvaluation\b|\bModelSample\b|\bScoreDimension\b|\bModelJudge"), "Evaluations"),
    (re.compile(r"\bCGImage\b|\bCGContext\b"), "CoreGraphics"),
    (re.compile(r"\bBarcodeReaderTool\b|\bOCRTool\b|\bVNRequest\b|\bClassifyImageRequest\b"), "Vision"),
    (re.compile(r"\bXCTest|\bXCTAssert"), "XCTest"),
    (re.compile(r"@Test\b|#expect\b|@Suite\b"), "Testing"),
]

IMPORT_RE = re.compile(r"^\s*(?:@[\w()., ]+\s+)?import\s+([A-Za-z_][A-Za-z0-9_.]*)")
FENCE_OPEN_RE = re.compile(r"^(\s*)```([\w.+-]*)\s*(.*?)\s*$")
FENCE_CLOSE_RE = re.compile(r"^\s*```\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
STUB_RE = re.compile(r"\{\s*get(\s+set)?\s*\}")
WRONGNESS_RE = re.compile(r"\bWRONG\b|does not compile|❌")
SWIFT_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CONDITION_RE = re.compile(r"^\s*#(?:if|elseif)\s+(.+)$")
BUILTIN_CONDITION_CALL_RE = re.compile(
    r"\b(?:canImport|os|arch|targetEnvironment|swift|compiler|hasFeature|hasAttribute)\s*\([^)]*\)")

# Diagnostics that mean the fence is a contextual excerpt rather than a
# self-contained compilation unit. These receive an explicit prelude marker;
# they are not promoted to VERIFIED and remain visible as PRELUDE-NEEDED.
CONTEXT_DIAGNOSTICS = (
    "cannot find '",
    "cannot find type '",
    "cannot find operator '",
    "no such module ",
    "no macro named ",
    "external macro implementation type ",
    "unknown attribute ",
)

# Diagnostics produced by deliberately excerpted declarations, SDK-interface
# spellings, pseudocode placeholders, or elided control-flow bodies. These are
# useful to readers but are not claims of standalone compilability.
ILLUSTRATIVE_DIAGNOSTICS = (
    "expected ",
    "unexpected ",
    # NOT bare "missing ": "missing argument for parameter" is a semantic
    # defect in real code, not an elision signal, and must reach a human.
    "missing return in",
    "initializers may only be declared within a type",
    "initializer requires a body",
    "declaration is only valid at file scope",
    "static methods may only be declared on a type",
    "static properties may only be declared on a type",
    "return invalid outside of a func",
    "consecutive statements on a line must be separated",
    "only classes and class members may be marked",
    "attribute 'public' can only be used in a non-local scope",
    "attribute 'private' can only be used in a non-local scope",
    "attribute 'package' can only be used in a non-local scope",
    "package access level used on ",
    "extraneous ",
    "labeled block needs ",
    "label can only appear inside a ",
    "case' label in a 'switch' must have at least one executable statement",
    "function is unused ",
    "macro cannot be attached to global function",
)


# ---------------------------------------------------------------------------
# Anchor slugs — copied from scripts/extract-callouts.py (do NOT import it: its
# top level executes an extraction). Keep byte-identical so anchors agree.

def slugify(h):
    h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', h)  # [text](url) -> text, as GitHub slugs do
    h = re.sub(r'[`*_]', '', h).strip()
    h = h.lower()
    out = []
    for ch in h:
        if ch.isalnum():
            out.append(ch)
        elif ch in ' -':
            out.append('-' if ch == ' ' else ch)
        # everything else dropped (github slug rule approximation)
    return re.sub(r'-{2,}', '-', ''.join(out)).strip('-')


def flatten(text, limit=400):
    return re.sub(r"\s+", " ", str(text)).strip()[:limit]


# ---------------------------------------------------------------------------
# Data model


@dataclasses.dataclass
class Fence:
    rel_path: str
    open_line: int  # 1-indexed line of the opening ``` in the guide file
    indent: int
    lang: str
    info: str
    body: list  # lines, indent-stripped
    anchor: str


class MarkerError(Exception):
    pass


@dataclasses.dataclass
class Markers:
    compile_targets: tuple = ()
    xfail_targets: tuple = ()
    imports: tuple = ()
    defines: tuple = ()
    wrap: str = "auto"  # auto | none | body | mixed
    lang: str = "6"
    isolation: str = "nonisolated"  # nonisolated | mainactor
    illustrative: bool = False
    prelude: "str | None" = None


@dataclasses.dataclass
class Toolchain:
    name: str
    developer_dir: str
    sdk_path: str
    sdk_version: str
    sdk_build: str
    triple: str
    xcode_version: str
    xcode_build: str
    framework_dirs: tuple


@dataclasses.dataclass
class CompileResult:
    verdict: str  # pass | fail | timeout
    first_error: str = ""
    err_line: str = ""  # guide-file line of first error, when mappable


# ---------------------------------------------------------------------------
# Extraction


def iter_guide_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn in GENERATED_PAGES:
                continue
            yield os.path.join(dirpath, fn)


def extract_fences(root):
    """Yield (fences, parse_errors). Tracks ALL fences (any language) so
    headings inside code blocks are not misparsed; yields only swift ones."""
    fences, errors = [], []
    for path in iter_guide_files(root):
        rel = os.path.relpath(path, root)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        seen_slugs = {}
        anchor = ""
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            m = HEADING_RE.match(line)
            if m:
                slug = slugify(m.group(2))
                if slug in seen_slugs:
                    seen_slugs[slug] += 1
                    anchor = f"{slug}-{seen_slugs[slug]}"
                else:
                    seen_slugs[slug] = 0
                    anchor = slug
                i += 1
                continue
            m = FENCE_OPEN_RE.match(line)
            if m and line.lstrip().startswith("```"):
                indent = len(m.group(1))
                lang = m.group(2)
                info = m.group(3)
                open_line = i + 1
                body = []
                i += 1
                closed = False
                while i < n:
                    if FENCE_CLOSE_RE.match(lines[i]):
                        closed = True
                        i += 1
                        break
                    content = lines[i]
                    # CommonMark: strip up to the fence's indent.
                    strip = 0
                    while strip < indent and strip < len(content) and content[strip] == " ":
                        strip += 1
                    body.append(content[strip:].rstrip("\n"))
                    i += 1
                if not closed:
                    errors.append((rel, open_line, "unterminated fence"))
                    break
                if lang == "swift":
                    fences.append(Fence(rel, open_line, indent, lang, info, body, anchor))
                continue
            i += 1
    return fences, errors


# ---------------------------------------------------------------------------
# Markers


def parse_markers(info):
    mk = Markers()
    if not info:
        return mk
    seen = set()
    for token in info.split():
        key = token.split(":", 1)[0]
        if key in seen:
            raise MarkerError(f"duplicate marker {key!r}")
        seen.add(key)
        if token == "illustrative":
            mk.illustrative = True
        elif token.startswith("compile:"):
            mk.compile_targets = tuple(token[len("compile:"):].split(","))
        elif token.startswith("xfail:"):
            mk.xfail_targets = tuple(token[len("xfail:"):].split(","))
        elif token.startswith("imports:"):
            value = token[len("imports:"):]
            if not value:
                raise MarkerError("imports requires at least one module")
            mk.imports = tuple(value.split(","))
            if any(not SWIFT_IDENTIFIER_RE.match(part) for part in mk.imports):
                raise MarkerError(f"invalid imports value {value!r}")
        elif token.startswith("defines:"):
            value = token[len("defines:"):]
            if not value:
                raise MarkerError("defines requires at least one compilation condition")
            mk.defines = tuple(value.split(","))
            if any(not SWIFT_IDENTIFIER_RE.match(part) for part in mk.defines):
                raise MarkerError(f"invalid defines value {value!r}")
        elif token.startswith("wrap:"):
            mk.wrap = token[len("wrap:"):]
            if mk.wrap not in ("none", "body", "mixed"):
                raise MarkerError(f"wrap must be none|body|mixed, got {mk.wrap!r}")
        elif token.startswith("lang:"):
            mk.lang = token[len("lang:"):]
            if mk.lang not in ("5", "6"):
                raise MarkerError(f"lang must be 5|6, got {mk.lang!r}")
        elif token.startswith("isolation:"):
            mk.isolation = token[len("isolation:"):]
            if mk.isolation not in ("nonisolated", "mainactor"):
                raise MarkerError(
                    f"isolation must be nonisolated|mainactor, got {mk.isolation!r}")
        elif token.startswith("prelude:"):
            mk.prelude = token[len("prelude:"):]
            if not mk.prelude:
                raise MarkerError("prelude requires a non-empty name")
        else:
            raise MarkerError(f"unknown marker {token!r}")
    for t in mk.compile_targets + mk.xfail_targets:
        if t not in TARGETS:
            raise MarkerError(f"unknown target {t!r}")
    overlap = set(mk.compile_targets) & set(mk.xfail_targets)
    if overlap:
        raise MarkerError(f"target(s) in both compile and xfail: {sorted(overlap)}")
    if mk.wrap == "none" and mk.imports:
        raise MarkerError("wrap:none is verbatim and cannot be combined with imports")
    if mk.prelude and (mk.compile_targets or mk.xfail_targets):
        raise MarkerError("prelude excludes compile and xfail: the fence is deferred, "
                          "not compiled against the named targets")
    if mk.illustrative and len(seen) > 1:
        raise MarkerError("illustrative excludes all other markers")
    return mk


def strip_swift_comments(lines):
    """Return lines with // and /* */ comments removed for structural checks.

    This is intentionally not a Swift lexer. It only decides whether a fence
    contains semantic source; compilation remains the authority for syntax.
    """
    result = []
    block_depth = 0
    for original in lines:
        line = original
        out = []
        i = 0
        while i < len(line):
            if block_depth:
                if line.startswith("/*", i):
                    block_depth += 1
                    i += 2
                    continue
                if line.startswith("*/", i):
                    block_depth -= 1
                    i += 2
                    continue
                i += 1
                continue
            if line.startswith("/*", i):
                block_depth = 1
                i += 2
                continue
            if line.startswith("//", i):
                break
            out.append(line[i])
            i += 1
        result.append("".join(out))
    return result


def effective_code_lines(body):
    """Semantic lines after comments, imports, attributes-only, and #if scaffolding."""
    result = []
    for line in strip_swift_comments(body):
        stripped = line.strip()
        if not stripped or IMPORT_RE.match(stripped):
            continue
        if re.match(r"^#(?:if|elseif|else|endif|warning|error|sourceLocation)\b", stripped):
            continue
        if re.match(r"^@[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?$", stripped):
            continue
        if re.match(r"^[{};]+$", stripped):
            continue
        result.append(stripped)
    return result


def custom_conditions(body):
    """Return user-defined identifiers referenced by #if/#elseif conditions."""
    found = set()
    for line in strip_swift_comments(body):
        match = CONDITION_RE.match(line)
        if not match:
            continue
        expression = BUILTIN_CONDITION_CALL_RE.sub(" ", match.group(1))
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression):
            if token not in {"true", "false"}:
                found.add(token)
    return found


def _condition_value(expression, defines):
    """Evaluate a custom-only Swift compilation condition, or return None.

    SDK/compiler predicates are deliberately unknown: swiftc remains their
    authority. This small evaluator exists only to reject a marked fence whose
    custom `defines:` selection statically compiles every semantic line out.
    """
    if BUILTIN_CONDITION_CALL_RE.search(expression):
        return None
    tokens = re.findall(r"&&|\|\||!|\(|\)|\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
    if "".join(tokens) != re.sub(r"\s+", "", expression):
        return None
    translated = []
    for token in tokens:
        if token == "&&":
            translated.append(" and ")
        elif token == "||":
            translated.append(" or ")
        elif token == "!":
            translated.append(" not ")
        elif token in ("(", ")"):
            translated.append(token)
        elif token == "true":
            translated.append("True")
        elif token == "false":
            translated.append("False")
        else:
            translated.append("True" if token in defines else "False")
    try:
        return bool(eval("".join(translated).strip(), {"__builtins__": {}}, {}))
    except (SyntaxError, TypeError):
        return None


def active_effective_code_lines(body, defines):
    """Return semantic lines not proven inactive by custom #if conditions."""
    active = True
    stack = []
    result = []
    for line in strip_swift_comments(body):
        stripped = line.strip()
        match = re.match(r"^#if\s+(.+)$", stripped)
        if match:
            value = _condition_value(match.group(1), set(defines))
            stack.append([active, value, value])
            active = False if active is False or value is False else active
            continue
        match = re.match(r"^#elseif\s+(.+)$", stripped)
        if match and stack:
            parent, prior, _ = stack[-1]
            value = _condition_value(match.group(1), set(defines))
            if parent is False or prior is True:
                active = False
            elif prior is None or value is None:
                active = None
            else:
                active = value
            stack[-1][1] = True if prior is True or value is True else (
                None if prior is None or value is None else False)
            stack[-1][2] = value
            continue
        if re.match(r"^#else\b", stripped) and stack:
            parent, prior, _ = stack[-1]
            active = False if parent is False or prior is True else (
                None if prior is None else parent)
            stack[-1][1] = True
            continue
        if re.match(r"^#endif\b", stripped) and stack:
            active = stack.pop()[0]
            continue
        if active is not False and effective_code_lines([line]):
            result.append(stripped)
    return result


def validate_markers_against_body(mk, fence):
    """compile:26 / xfail:26 with a structurally-absent module is dishonest
    (trivially true xfail) — hard error."""
    body_imports = hoist_imports(fence.body)[0]
    absent = set(body_imports) & ABSENT_ON_26 | set(mk.imports) & ABSENT_ON_26
    sdk26_targets = [target for target in mk.compile_targets + mk.xfail_targets
                     if TARGETS[target].sdk_generation == "26"]
    if absent and sdk26_targets:
        raise MarkerError(
            f"module(s) {sorted(absent)} do not exist in the 26 SDK; "
            "use an SDK-27 target")
    if mk.compile_targets or mk.xfail_targets:
        if not effective_code_lines(fence.body):
            raise MarkerError("compile/xfail fence has no semantic Swift source")
        missing_defines = custom_conditions(fence.body) - set(mk.defines)
        if missing_defines:
            raise MarkerError(
                f"custom compilation condition(s) {sorted(missing_defines)} require defines:")
        if not active_effective_code_lines(fence.body, mk.defines):
            raise MarkerError("compile/xfail fence is entirely inactive under its defines")


# ---------------------------------------------------------------------------
# Auto-detection (advisory + guess-mode routing)


def autodetect(fence):
    flags = set()
    code_lines = [l for l in fence.body if l.strip() and not l.strip().startswith("//")]
    stub_hits = sum(1 for l in code_lines if STUB_RE.search(l))
    if stub_hits >= 1:
        flags.add("stub")
    for l in code_lines:
        stripped = re.sub(r"//.*$", "", l).strip()
        # An elision is a token-isolated ellipsis, not a range operator.
        if stripped in ("...", "…") or re.search(r"(?<![.\w])\.\.\.(?![.\w<(])\s*$", stripped) \
                or "…" in stripped:
            flags.add("elided")
            break
    if any(WRONGNESS_RE.search(l) for l in fence.body):
        flags.add("wrongness")
    if not effective_code_lines(fence.body):
        flags.add("comment-only")
    if custom_conditions(fence.body):
        flags.add("custom-conditional")
    return flags


# ---------------------------------------------------------------------------
# Wrapper synthesis


def hoist_imports(body):
    """Return (modules, import_lines, rest, rest_linemap) where rest_linemap[i]
    is the 0-based body index of rest[i]."""
    modules, import_lines, rest, linemap = [], [], [], []
    for idx, line in enumerate(body):
        m = IMPORT_RE.match(line)
        if m:
            if m.group(1) not in modules:
                modules.append(m.group(1))
                import_lines.append(line.strip())
        else:
            rest.append(line)
            linemap.append(idx)
    return modules, import_lines, rest, linemap


def choose_wrap(rest):
    """'top' when the fence reads as file-scope declarations, else 'body'."""
    for line in rest:
        s = line.strip()
        if not s:
            continue
        return "top" if s.startswith(DECL_KEYWORDS) else "body"
    return "top"


MIXED_TOP_LEVEL_PREFIXES = (
    "@", "struct ", "class ", "enum ", "actor ", "protocol ",
    "extension ", "func ", "typealias ", "precedencegroup ", "operator ",
    "public ", "package ", "internal ", "private ", "fileprivate ",
    "final ", "nonisolated ", "#if", "#available",
)


def swift_brace_deltas(lines):
    """Yield structural brace deltas while ignoring comments and strings.

    This remains a deliberately small lexer for wrapper routing, but it tracks
    the Swift constructs that commonly contain literal braces in guide code.
    Compilation, rather than this helper, remains the syntax authority.
    """
    block_depth = 0
    string_delimiter = None
    for line in lines:
        delta = 0
        i = 0
        while i < len(line):
            if block_depth:
                if line.startswith("/*", i):
                    block_depth += 1
                    i += 2
                elif line.startswith("*/", i):
                    block_depth -= 1
                    i += 2
                else:
                    i += 1
                continue
            if string_delimiter:
                if string_delimiter == '"' and line[i] == "\\":
                    i += 2
                elif line.startswith(string_delimiter, i):
                    i += len(string_delimiter)
                    string_delimiter = None
                else:
                    i += 1
                continue
            if line.startswith("//", i):
                break
            if line.startswith("/*", i):
                block_depth = 1
                i += 2
                continue
            if line.startswith('"""', i):
                string_delimiter = '"""'
                i += 3
                continue
            if line[i] == '"':
                string_delimiter = '"'
                i += 1
                continue
            if line[i] == "{":
                delta += 1
            elif line[i] == "}":
                delta -= 1
            i += 1
        # Ordinary strings cannot continue across a newline. Multiline string
        # delimiters remain active until their closing triple quote.
        if string_delimiter == '"':
            string_delimiter = None
        yield delta


def mixed_split_index(rest):
    """Return the line where executable example code begins.

    Many guide fences intentionally combine file-scope declarations (especially
    attached-macro types) with the few statements that use them. Neither the
    old all-top nor all-body wrapper can type-check that honest, common shape:
    top-level ``await`` is rejected, while an attached macro on a local type is
    also rejected. ``mixed`` retains the declaration prefix at file scope and
    wraps the executable suffix in the async test function.

    This is deliberately conservative: it only splits after seeing a genuine
    file-scope declaration and only at brace depth zero. Fences that interleave
    declarations and statements still fail and require an explicit marker or a
    prelude instead of being rearranged speculatively.
    """
    depth = 0
    saw_declaration = False
    pending_attributes = False
    for i, (line, brace_delta) in enumerate(zip(rest, swift_brace_deltas(rest))):
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            continue
        if depth == 0:
            is_attribute = s.startswith("@")
            is_declaration = s.startswith(MIXED_TOP_LEVEL_PREFIXES)
            if is_attribute:
                pending_attributes = True
            elif is_declaration or pending_attributes:
                saw_declaration = True
                pending_attributes = False
            elif saw_declaration:
                return i
        depth += brace_delta
        depth = max(depth, 0)
    return len(rest)


def synthesize(fence, extra_imports, wrap):
    """Return (source, linemap, modules).

    ``linemap[generated_line_0based]`` is the guide's 1-based line or None for
    synthesized lines; ``modules`` is the de-duplicated imported-module list.
    """
    modules, import_lines, rest, rest_map = hoist_imports(fence.body)
    for mod in extra_imports:
        if mod not in modules:
            modules.append(mod)
            import_lines.append(f"import {mod}")
    gen, linemap = [], []
    body_offset = fence.open_line  # body line i (0-based) is guide line open_line+1+i
    if wrap == "none":
        for i, line in enumerate(fence.body):
            gen.append(line)
            linemap.append(body_offset + 1 + i)
    else:
        for line in import_lines:
            gen.append(line)
            linemap.append(None)
        if wrap == "body":
            gen.append("func __verify_snippet() async throws {")
            linemap.append(None)
            for i, line in zip(rest_map, rest):
                gen.append(line)
                linemap.append(body_offset + 1 + i)
            gen.append("}")
            linemap.append(None)
        elif wrap == "mixed":
            split = mixed_split_index(rest)
            for i, line in zip(rest_map[:split], rest[:split]):
                gen.append(line)
                linemap.append(body_offset + 1 + i)
            if any(line.strip() for line in rest[split:]):
                gen.append("func __verify_snippet() async throws {")
                linemap.append(None)
                for i, line in zip(rest_map[split:], rest[split:]):
                    gen.append(line)
                    linemap.append(body_offset + 1 + i)
                gen.append("}")
                linemap.append(None)
        else:  # top
            for i, line in zip(rest_map, rest):
                gen.append(line)
                linemap.append(body_offset + 1 + i)
    return "\n".join(gen) + "\n", linemap, modules


# ---------------------------------------------------------------------------
# Toolchains + compilation


def discover_toolchain(name):
    spec = TARGETS[name]
    dev_dir, sdk_name = spec.developer_dir, spec.sdk_name
    if not os.path.isdir(dev_dir):
        raise SystemExit(f"error: developer dir for target {name} missing: {dev_dir}")
    env = dict(os.environ, DEVELOPER_DIR=dev_dir)

    def checked_output(command):
        try:
            return subprocess.run(command, env=env, capture_output=True,
                                  text=True, check=True).stdout.strip()
        except subprocess.CalledProcessError as error:
            detail = flatten(error.stderr or error.stdout or f"exit {error.returncode}")
            raise SystemExit(
                f"error: toolchain discovery for target {name} failed: "
                f"{' '.join(command)}: {detail}"
            ) from error
        except OSError as error:
            raise SystemExit(
                f"error: toolchain discovery for target {name} failed: "
                f"{' '.join(command)}: {error}"
            ) from error

    def xcrun(*args):
        return checked_output(["xcrun"] + list(args))

    sdk_path = xcrun("--sdk", sdk_name, "--show-sdk-path")
    sdk_version = xcrun("--sdk", sdk_name, "--show-sdk-version")
    sdk_build = xcrun("--sdk", sdk_name, "--show-sdk-build-version")
    out = checked_output(["xcodebuild", "-version"]).splitlines()
    xcode_version = out[0].replace("Xcode", "").strip() if out else "?"
    xcode_build = out[1].replace("Build version", "").strip() if len(out) > 1 else "?"
    platform_dir = {"macosx": "MacOSX", "iphonesimulator": "iPhoneSimulator"}[sdk_name]
    fw = os.path.join(dev_dir, "Platforms", f"{platform_dir}.platform",
                      "Developer", "Library", "Frameworks")
    deployment_version = spec.deployment_version or sdk_version
    return Toolchain(name, dev_dir, sdk_path, sdk_version, sdk_build,
                     spec.triple_template.format(v=deployment_version), xcode_version, xcode_build,
                     (fw,) if os.path.isdir(fw) else ())


FIRST_ERROR_RE = re.compile(r"^<stdin>:(\d+):(\d+): error: (.*)$")


def typecheck(source, tc, swift_version, default_isolation, defines,
              needs_xcode_frameworks, cache_root,
              linemap=None, timeout=60, stub=None, parse_as_library=True):
    if stub is not None:
        return CompileResult("pass") if stub == "pass" else \
            CompileResult("fail", first_error=stub.split(":", 1)[1] if ":" in stub else "stubbed failure")
    cmd = ["xcrun", "swiftc", "-typecheck"]
    if parse_as_library:
        cmd.append("-parse-as-library")
    cmd += [
           "-swift-version", swift_version,
           "-sdk", tc.sdk_path,
           "-target", tc.triple,
           "-diagnostic-style", "llvm",
           "-module-cache-path", os.path.join(cache_root, tc.sdk_build)]
    if default_isolation == "mainactor":
        cmd += ["-default-isolation", "MainActor"]
    for condition in defines:
        cmd += ["-D", condition]
    if needs_xcode_frameworks:
        for fw in tc.framework_dirs:
            cmd += ["-F", fw]
    cmd.append("-")
    env = dict(os.environ, DEVELOPER_DIR=tc.developer_dir)
    try:
        proc = subprocess.run(cmd, input=source, env=env, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return CompileResult("timeout")
    if proc.returncode == 0:
        return CompileResult("pass")
    first, err_line = "", ""
    for out_line in proc.stderr.splitlines():
        m = FIRST_ERROR_RE.match(out_line)
        if m:
            first = m.group(3)
            gen_line = int(m.group(1)) - 1
            if linemap and 0 <= gen_line < len(linemap) and linemap[gen_line]:
                err_line = str(linemap[gen_line])
            break
    if not first:
        first = flatten(proc.stderr, 200) or f"swiftc exit {proc.returncode}"
    return CompileResult("fail", first_error=flatten(first), err_line=err_line)


# ---------------------------------------------------------------------------
# Per-fence verification


def compile_variants(fence, mk, imports, tc, opts, xfail):
    """Try the requested wrap (auto retries the alternate). Returns
    (verdict, wrap_used, CompileResult)."""
    guess_kwargs = dict(swift_version=mk.lang,
                        default_isolation=mk.isolation,
                        defines=mk.defines,
                        cache_root=opts.cache_root,
                        timeout=opts.timeout, stub=opts.stub_compiler)
    if mk.wrap == "auto":
        first_choice = choose_wrap(hoist_imports(fence.body)[2])
        alternate = "body" if first_choice == "top" else "top"
        order = [first_choice, alternate, "mixed"]
    else:
        order = [mk.wrap]
    last = None
    body_modules = set(hoist_imports(fence.body)[0])
    needs_xcode_fw = bool((set(imports) | body_modules) & XCODE_ONLY_MODULES)
    for wrap in order:
        source, linemap, _modules = synthesize(fence, imports, wrap)
        result = typecheck(source, tc, linemap=linemap,
                           needs_xcode_frameworks=needs_xcode_fw,
                           parse_as_library=wrap != "none", **guess_kwargs)
        last = (wrap, result)
        if result.verdict == "pass":
            break
    assert last is not None  # order always has >= 1 element
    wrap, result = last
    if xfail:
        if result.verdict == "fail":
            return "xfail-pass", wrap, result
        if result.verdict == "pass":
            return "XFAIL-ERR", wrap, CompileResult("pass", first_error="expected failure but compiled")
        return result.verdict, wrap, result
    return result.verdict, wrap, result


def verify_fence(fence, toolchains, opts):
    row = {"file": fence.rel_path, "line": str(fence.open_line),
           "anchor": fence.anchor, "info": fence.info, "status": "",
           "wrap": "", **{spec.column: "-" for spec in TARGETS.values()},
           "err_line": "", "first_error": "", "flags": autodetect(fence)}
    col = {name: spec.column for name, spec in TARGETS.items()}
    try:
        mk = parse_markers(fence.info)
        validate_markers_against_body(mk, fence)
    except MarkerError as e:
        row["status"] = "MARKER-ERROR"
        row["first_error"] = flatten(str(e))
        return row

    if mk.illustrative:
        row["status"] = "ILLUSTRATIVE"
        return row
    if mk.prelude:
        row["status"] = "PRELUDE-NEEDED"
        return row

    if mk.compile_targets or mk.xfail_targets:
        if mk.compile_targets and mk.xfail_targets:
            overall = "MIGRATION-PROVEN"
        else:
            overall = "VERIFIED" if mk.compile_targets else "XFAIL-PROVEN"
        for target in mk.compile_targets + mk.xfail_targets:
            xfail = target in mk.xfail_targets
            tc = toolchains[target]
            verdict, wrap, result = compile_variants(
                fence, mk, list(mk.imports), tc, opts, xfail)
            row[col[target]] = verdict
            row["wrap"] = wrap
            if verdict in ("fail", "timeout"):
                overall = "FAILED"
                row["first_error"] = result.first_error
                row["err_line"] = result.err_line
            elif verdict == "XFAIL-ERR":
                overall = "XFAIL-ERR"
                row["first_error"] = result.first_error
        row["status"] = overall
        return row

    # Unmarked.
    if not opts.guess:
        row["status"] = "UNCLASSIFIED"
        return row
    if "comment-only" in row["flags"]:
        row["status"] = "COMMENT-ONLY"
        return row
    if "custom-conditional" in row["flags"]:
        row["status"] = "UNCLASSIFIED-FAIL"
        row["first_error"] = "custom compilation condition requires an explicit defines: marker"
        return row
    if "stub" in row["flags"]:
        row["status"] = "STUB"
        return row
    if "elided" in row["flags"]:
        row["status"] = "ELIDED"
        return row
    body_text = "\n".join(fence.body)
    imports = list(GUESS_ALWAYS_IMPORTS)
    for pattern, mod in GUESS_KEYWORD_IMPORTS:
        if pattern.search(body_text) and mod not in imports:
            imports.append(mod)
    target = opts.guess_target
    tc = toolchains[target]
    def retry_mainactor_if_needed(target_name, verdict, wrap, result):
        if verdict != "fail" or not any(
                fragment in result.first_error for fragment in (
                    "concurrency-safe", "non-Sendable type", "main actor-isolated")):
            return verdict, wrap, result
        isolated = Markers(isolation="mainactor")
        v2, w2, r2 = compile_variants(
            fence, isolated, imports, toolchains[target_name], opts, False)
        if v2 == "pass":
            row["_guess_isolation"] = "mainactor"
            return v2, w2, r2
        return verdict, wrap, result

    verdict, wrap, result = compile_variants(fence, Markers(), imports, tc, opts, False)
    verdict, wrap, result = retry_mainactor_if_needed(target, verdict, wrap, result)
    # iOS-only snippets (UIKit, WidgetKit, …) can never compile against the macOS
    # SDK — fall back to the simulator target before calling them failures.
    if (verdict == "fail" and "no such module" in result.first_error
            and target != "sim27" and "sim27" in toolchains):
        v2, w2, r2 = compile_variants(fence, Markers(), imports,
                                      toolchains["sim27"], opts, False)
        v2, w2, r2 = retry_mainactor_if_needed("sim27", v2, w2, r2)
        if v2 == "pass":
            target, verdict, wrap, result = "sim27", v2, w2, r2
    row[col[target]] = verdict
    row["wrap"] = wrap
    row["status"] = "UNCLASSIFIED-PASS" if verdict == "pass" else "UNCLASSIFIED-FAIL"
    row["first_error"] = result.first_error
    row["err_line"] = result.err_line
    row["_guess_imports"] = imports
    row["_pass_target"] = target
    return row


# ---------------------------------------------------------------------------
# Output


TSV_COLUMNS = ["file", "line", "anchor", "info", "status", "wrap",
               "v26", "v27", "vsim27", "v27on26", "vsim27on26",
               "err_line", "first_error"]


def write_tsv(rows, out):
    out.write("\t".join(TSV_COLUMNS) + "\n")
    for r in rows:
        fields = [flatten(r.get(c, "")) if c == "first_error" else
                  flatten(r.get(c, ""), 200) for c in TSV_COLUMNS]
        # Keep the TSV rectangular without emitting trailing tab whitespace for
        # rows that have no diagnostic. A dash already means “not applicable”
        # in the target columns, so use it consistently for every empty field.
        out.write("\t".join(value or "-" for value in fields) + "\n")


def write_report(rows, toolchains, opts, out):
    from collections import Counter, defaultdict
    counts = Counter(r["status"] for r in rows)
    out.write("# Snippet compile-verification report\n\n")
    out.write(f"Generated by scripts/verify-snippets.py (WRAPPER_VERSION={WRAPPER_VERSION}, "
              f"-swift-version 6 default"
              f"{', guess mode' if opts.guess else ''}). Honesty rule: every verdict is\n"
              "against the exact SDK builds below, never against \"iOS 27\" in the abstract.\n\n")
    out.write("| target | Xcode | SDK | triple |\n|---|---|---|---|\n")
    for name, tc in sorted(toolchains.items()):
        out.write(f"| {name} | {tc.xcode_version} ({tc.xcode_build}) | "
                  f"{tc.sdk_version} ({tc.sdk_build}) | {tc.triple} |\n")
    out.write(f"\n**Totals over {len(rows)} Swift fences:** ")
    out.write(" · ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "\n\n")
    backlog = counts.get("UNCLASSIFIED", 0) + counts.get("UNCLASSIFIED-FAIL", 0)
    out.write(f"**UNCLASSIFIED backlog (the metric): {backlog}**\n\n")
    out.write(f"**PRELUDE backlog (classified contextual excerpts): "
              f"{counts.get('PRELUDE-NEEDED', 0)}**\n\n")

    per_guide = defaultdict(Counter)
    for r in rows:
        per_guide[r["file"]][r["status"]] += 1
    out.write("## Per-guide rollup\n\n")
    out.write("| guide | fences | verified/pass | migration-proven | xfail-proven | illus./stub/elided/comment-only | unclassified pass–fail | FAILING |\n")
    out.write("|---|---|---|---|---|---|---|---|\n")
    for guide in sorted(per_guide):
        c = per_guide[guide]
        total = sum(c.values())
        out.write(f"| {guide} | {total} | {c['VERIFIED'] + c['UNCLASSIFIED-PASS']} | "
                  f"{c['MIGRATION-PROVEN']} | {c['XFAIL-PROVEN']} | "
                  f"{c['ILLUSTRATIVE'] + c['STUB'] + c['ELIDED'] + c['COMMENT-ONLY']} | "
                  f"{c['UNCLASSIFIED-PASS']}–{c['UNCLASSIFIED-FAIL']} | "
                  f"{c['FAILED'] + c['XFAIL-ERR']} |\n")

    failures = [r for r in rows if r["status"] in ("FAILED", "XFAIL-ERR", "MARKER-ERROR", "PARSE-ERROR")]
    if failures:
        out.write("\n## Failures (work items)\n\n")
        for r in failures:
            loc = f"{r['file']}:{r.get('err_line') or r['line']}"
            out.write(f"- **{r['status']}** `{loc}` (#{r['anchor']}) — {r['first_error']}\n")
    fails = [r for r in rows if r["status"] == "UNCLASSIFIED-FAIL"]
    if fails:
        out.write("\n## Guess-mode failures (triage input)\n\n")
        for r in fails:
            loc = f"{r['file']}:{r.get('err_line') or r['line']}"
            out.write(f"- `{loc}` (#{r['anchor']}) — {r['first_error']}\n")
    wrong = [r for r in rows if "wrongness" in r.get("flags", set())
             and r["status"] not in ("ILLUSTRATIVE",)]
    if wrong:
        out.write("\n## Wrongness-candidates (possible xfail: markers — triage by hand)\n\n")
        for r in wrong:
            out.write(f"- `{r['file']}:{r['line']}` (#{r['anchor']}) — status {r['status']}\n")


# ---------------------------------------------------------------------------
# --write-markers


def triage_marker_for_row(row):
    """Return a conservative marker for a failed guess, or None for review.

    The diagnostic is only a routing signal. High-signal semantic/compiler
    findings (ambiguity, type conversion, Swift 6 isolation, mutability) stay
    unmarked so a human must fix or deliberately classify them.
    """
    error = row.get("first_error", "")
    if "wrongness" in row.get("flags", set()):
        return None
    if "unavailable in macOS" in error or "not available on macOS" in error:
        return "prelude:platform-target"
    if error.startswith("no such module "):
        return "prelude:external-module"
    if any(fragment in error for fragment in CONTEXT_DIAGNOSTICS):
        # Swift identifier-resolution diagnostics always end " in scope";
        # anything else that merely mentions "cannot find" stays for review.
        if "cannot find" in error and " in scope" not in error:
            return None
        return "prelude:guide-context"
    if any(fragment in error for fragment in ILLUSTRATIVE_DIAGNOSTICS):
        return "illustrative"
    return None


def write_markers(rows, guides_root, opts):
    """Add compile:27 [imports:...] to UNCLASSIFIED-PASS fences and
    illustrative to STUB/ELIDED ones. Only opening-fence lines change."""
    if not opts.stub_compiler and not opts.allow_dirty_guides:
        try:
            dirty = subprocess.run(["git", "status", "--porcelain", "--", guides_root],
                                   capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, OSError) as exc:
            raise SystemExit(
                f"error: cannot determine guides tree state for --write-markers: {exc}")
        if dirty:
            raise SystemExit("error: guides tree is dirty; commit or stash before --write-markers")

    pre_fences, _ = extract_fences(guides_root)
    pre_hashes = [hashlib.sha256("\n".join(f.body).encode()).hexdigest() for f in pre_fences]

    by_file = {}
    for r in rows:
        new_info = None
        if r["status"] == "UNCLASSIFIED-PASS":
            new_info = f"compile:{r.get('_pass_target', opts.guess_target)}"
            extra = r.get("_needed_imports")
            if extra:
                new_info += " imports:" + ",".join(extra)
            if r.get("_guess_isolation") == "mainactor":
                new_info += " isolation:mainactor"
        elif r["status"] in ("STUB", "ELIDED", "COMMENT-ONLY"):
            new_info = "illustrative"
        elif opts.write_triage_markers and r["status"] == "UNCLASSIFIED-FAIL":
            new_info = triage_marker_for_row(r)
        if new_info:
            by_file.setdefault(r["file"], []).append((int(r["line"]), new_info))

    edited = 0
    for rel, edits in sorted(by_file.items()):
        path = os.path.join(guides_root, rel)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for line_no, new_info in sorted(edits, reverse=True):
            old = lines[line_no - 1]
            m = FENCE_OPEN_RE.match(old)
            if not m or m.group(2) != "swift" or m.group(3):
                raise SystemExit(f"error: refusing to edit {rel}:{line_no}: "
                                 f"not a bare swift fence anymore: {old!r}")
            lines[line_no - 1] = f"{m.group(1)}```swift {new_info}\n"
            edited += 1
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"# marked {len(edits):4d} fences in {rel}", file=sys.stderr)

    post_fences, post_errors = extract_fences(guides_root)
    post_hashes = [hashlib.sha256("\n".join(f.body).encode()).hexdigest() for f in post_fences]
    if post_errors or len(post_fences) != len(pre_fences) or post_hashes != pre_hashes:
        raise SystemExit("error: post-edit re-extraction mismatch — fence count or "
                         "bodies changed; review the guides tree before committing")
    return edited


def refine_needed_imports(rows, toolchains, opts):
    """For each UNCLASSIFIED-PASS row, find whether guess-injected imports were
    actually needed: recompile with hoisted-only; record extras if required.

    Rows are independent and run in parallel; each row's greedy drop sequence
    remains ordered because later trials depend on the imports retained by the
    previous trial.
    """
    candidates = [r for r in rows if r["status"] == "UNCLASSIFIED-PASS"]

    def refine(r):
        tc = toolchains[r.get("_pass_target", opts.guess_target)]
        fence = r["_fence"]
        guess_markers = Markers(isolation=r.get("_guess_isolation", "nonisolated"))
        verdict, _, _ = compile_variants(fence, guess_markers, [], tc, opts, False)
        if verdict == "pass":
            r["_needed_imports"] = []
            return
        # Binary-search would be overkill; drop imports one at a time. Whatever
        # survives the drop test is needed — including Foundation.
        needed = list(r.get("_guess_imports", []))
        for mod in list(needed):
            trial = [m for m in needed if m != mod]
            verdict, _, _ = compile_variants(fence, guess_markers, trial, tc, opts, False)
            if verdict == "pass":
                needed = trial
        r["_needed_imports"] = needed
    with concurrent.futures.ThreadPoolExecutor(max_workers=opts.jobs) as pool:
        list(pool.map(refine, candidates))
    return rows


# ---------------------------------------------------------------------------
# Main


AUTO_CHANGED_REF = "__auto_pr_base__"


def run_git(repo_root, args, *, text=True):
    try:
        return subprocess.run(["git", "-C", repo_root] + list(args),
                              capture_output=True, text=text, check=True).stdout
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr
        raise SystemExit(f"error: git {' '.join(args)} failed: {flatten(detail or error)}")


def resolve_changed_base(repo_root, requested):
    if requested != AUTO_CHANGED_REF:
        base = requested
    elif os.environ.get("GITHUB_BASE_REF"):
        github_base = os.environ["GITHUB_BASE_REF"]
        remote_candidate = f"origin/{github_base}"
        probe = subprocess.run(["git", "-C", repo_root, "rev-parse", "--verify",
                                f"{remote_candidate}^{{commit}}"], capture_output=True)
        base = remote_candidate if probe.returncode == 0 else github_base
    else:
        symbolic = run_git(repo_root, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"])
        base = symbolic.strip().removeprefix("refs/remotes/")
    run_git(repo_root, ["rev-parse", "--verify", f"{base}^{{commit}}"])
    return base


def nul_paths(repo_root, args):
    raw = run_git(repo_root, args, text=False)
    return {part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part}


def changed_guide_files(guides_root, requested_ref):
    repo_root = run_git(os.getcwd(), ["rev-parse", "--show-toplevel"]).strip()
    guides_abs = os.path.abspath(guides_root)
    guides_repo_rel = os.path.relpath(guides_abs, repo_root)
    if guides_repo_rel == os.pardir or guides_repo_rel.startswith(os.pardir + os.sep):
        raise SystemExit("error: --changed requires --guides to be inside the Git repository")
    base = resolve_changed_base(repo_root, requested_ref)
    pathspec = ["--", guides_repo_rel]
    paths = set()
    paths |= nul_paths(repo_root, ["diff", "--name-only", "-z", f"{base}...HEAD"] + pathspec)
    paths |= nul_paths(repo_root, ["diff", "--name-only", "-z"] + pathspec)
    paths |= nul_paths(repo_root, ["diff", "--cached", "--name-only", "-z"] + pathspec)
    paths |= nul_paths(repo_root, ["ls-files", "--others", "--exclude-standard", "-z"] + pathspec)
    changed = set()
    for repo_relative in paths:
        absolute = os.path.normpath(os.path.join(repo_root, repo_relative))
        relative = os.path.relpath(absolute, guides_abs)
        if relative != os.pardir and not relative.startswith(os.pardir + os.sep):
            changed.add(relative)
    return changed, base


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--guides", default="guides")
    ap.add_argument("--sdk", action="append", choices=sorted(TARGETS),
                    dest="sdks", default=None,
                    help="targets to resolve (repeatable); default: those the markers request")
    ap.add_argument("--guess", action="store_true",
                    help="attempt unmarked fences against --guess-target")
    ap.add_argument("--guess-target", default="27", choices=sorted(TARGETS))
    ap.add_argument("--changed", nargs="?", const=AUTO_CHANGED_REF, default=None, metavar="REF",
                    help="only fences in guide files changed vs REF (default: PR/default branch)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", default=None,
                    help="directory for results.tsv + report.md (default: stdout TSV only)")
    ap.add_argument("--write-markers", action="store_true")
    ap.add_argument("--write-triage-markers", action="store_true",
                    help="also classify safe failed guesses as illustrative or prelude-needed")
    ap.add_argument("--allow-dirty-guides", action="store_true",
                    help="permit marker-only edits in an already-dirty guides tree")
    ap.add_argument("--cache-root",
                    default=os.path.expanduser("~/Library/Caches/snippet-verify"))
    ap.add_argument("--stub-compiler", default=None, metavar="pass|fail:<msg>",
                    help="test-only: replace swiftc with a fixed result")
    opts = ap.parse_args(argv)

    if not os.path.isdir(opts.guides):
        raise SystemExit(f"error: guides root does not exist or is not a directory: {opts.guides}")
    fences, parse_errors = extract_fences(opts.guides)
    if not fences and not parse_errors:
        raise SystemExit(f"error: guides root contains no Swift fences: {opts.guides}")
    if opts.changed is not None:
        if not opts.changed:
            raise SystemExit("error: --changed requires a non-empty ref")
        changed, base = changed_guide_files(opts.guides, opts.changed)
        if not changed:
            print(f"# zero changed guide files versus {base}", file=sys.stderr)
        fences = [f for f in fences if f.rel_path in changed]
        parse_errors = [error for error in parse_errors if error[0] in changed]

    # Which targets do we need? Marker-requested plus guess target.
    needed = set(opts.sdks or [])
    for f in fences:
        try:
            mk = parse_markers(f.info)
            needed |= set(mk.compile_targets) | set(mk.xfail_targets)
        except MarkerError:
            pass
    if opts.guess:
        needed.add(opts.guess_target)
        needed.add("sim27")  # iOS-only-module fallback target
    toolchains = {}
    if not opts.stub_compiler:
        for name in sorted(needed):
            toolchains[name] = discover_toolchain(name)
    else:
        for name in sorted(needed or {opts.guess_target}):
            toolchains[name] = Toolchain(name, "/stub", "/stub-sdk", "0.0", "STUB",
                                         "stub-triple", "0.0", "STUB", ())

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=opts.jobs) as pool:
        futures = {pool.submit(verify_fence, f, toolchains, opts): f for f in fences}
        for fut in concurrent.futures.as_completed(futures):
            row = fut.result()
            row["_fence"] = futures[fut]
            rows.append(row)
    rows.sort(key=lambda r: (r["file"], int(r["line"])))
    for rel, line, msg in parse_errors:
        rows.append({"file": rel, "line": str(line), "anchor": "", "info": "",
                     "status": "PARSE-ERROR", "wrap": "",
                     **{spec.column: "-" for spec in TARGETS.values()},
                     "err_line": "", "first_error": msg, "flags": set()})

    if opts.write_triage_markers:
        opts.write_markers = True
    if opts.write_markers:
        if not opts.guess:
            raise SystemExit("error: --write-markers requires --guess (a fresh guess run)")
        refine_needed_imports(rows, toolchains, opts)
        edited = write_markers(rows, opts.guides, opts)
        print(f"# wrote markers on {edited} fences", file=sys.stderr)

    if opts.out:
        os.makedirs(opts.out, exist_ok=True)
        tsv_path = os.path.join(opts.out, "results.tsv")
        tmp = tsv_path + f".tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            write_tsv(rows, f)
        os.replace(tmp, tsv_path)
        report_path = os.path.join(opts.out, "report.md")
        tmp = report_path + f".tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            write_report(rows, toolchains, opts, f)
        os.replace(tmp, report_path)
        print(f"# wrote {tsv_path} and {report_path}", file=sys.stderr)
    else:
        write_tsv(rows, sys.stdout)

    from collections import Counter
    counts = Counter(r["status"] for r in rows)
    print(f"# total fences: {len(rows)}", file=sys.stderr)
    print(f"# by status: {dict(sorted(counts.items()))}", file=sys.stderr)
    if counts.get("MARKER-ERROR") or counts.get("PARSE-ERROR"):
        return 2
    if counts.get("FAILED") or counts.get("XFAIL-ERR"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
