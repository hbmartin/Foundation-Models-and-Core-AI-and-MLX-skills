#!/usr/bin/env python3
"""Compile-verify the fenced Swift snippets in guides/.

Extracts every ```swift fence, classifies it via fence info-string markers,
wraps fragments in a minimal harness, and runs `swiftc -typecheck` against the
requested SDK(s). Emits a strict-TSV row per fence plus a markdown report.

Marker grammar (space-separated tokens after `swift` in the fence info string;
canonical documentation in notes/snippet-verification/README.md):

    compile:<t>[,<t>...]   must type-check on each target   t ∈ {26, 27, sim27}
    xfail:<t>[,<t>...]     must FAIL to type-check on each target
    imports:A,B            modules the wrapper adds beyond hoisted ones
    wrap:none|body         complete file / force func-body wrap (default: auto)
    lang:5                 pin -swift-version 5 (default 6)
    illustrative           never compiled (pseudocode, stubs, elided bodies)
    prelude:<name>         reserved; reported PRELUDE-NEEDED, not compiled

TSV columns (tab-delimited, flatten()ed fields):
    file  line  anchor  info  status  wrap  v26  v27  vsim27  err_line  first_error

Row status: VERIFIED XFAIL-PROVEN FAILED ILLUSTRATIVE STUB ELIDED
    PRELUDE-NEEDED UNCLASSIFIED UNCLASSIFIED-PASS UNCLASSIFIED-FAIL
    MARKER-ERROR PARSE-ERROR
Per-target verdicts: pass fail xfail-pass XFAIL-ERR no-sdk timeout - skip

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

# Target name -> (developer dir, xcrun sdk name, triple template).
# Names, not versions: a new beta changes the resolved identity, never the marker.
TARGETS = {
    "26": ("/Applications/Xcode.app/Contents/Developer", "macosx",
           "arm64-apple-macos{v}"),
    "27": ("/Applications/Xcode-beta.app/Contents/Developer", "macosx",
           "arm64-apple-macos{v}"),
    "sim27": ("/Applications/Xcode-beta.app/Contents/Developer", "iphonesimulator",
              "arm64-apple-ios{v}-simulator"),
}
# Frameworks that live under <platform>/Developer/Library/Frameworks (Xcode-bundled).
XCODE_ONLY_MODULES = {"Evaluations"}
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


# ---------------------------------------------------------------------------
# Anchor slugs — copied from scripts/extract-callouts.py (do NOT import it: its
# top level executes an extraction). Keep byte-identical so anchors agree.

def slugify(text):
    text = re.sub(r"[`*_~]", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\s一-鿿-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s]+", "-", text)
    return text


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
    wrap: str = "auto"  # auto | none | body
    lang: str = "6"
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
    for token in info.split():
        if token == "illustrative":
            mk.illustrative = True
        elif token.startswith("compile:"):
            mk.compile_targets = tuple(token[len("compile:"):].split(","))
        elif token.startswith("xfail:"):
            mk.xfail_targets = tuple(token[len("xfail:"):].split(","))
        elif token.startswith("imports:"):
            mk.imports = tuple(token[len("imports:"):].split(","))
        elif token.startswith("wrap:"):
            mk.wrap = token[len("wrap:"):]
            if mk.wrap not in ("none", "body"):
                raise MarkerError(f"wrap must be none|body, got {mk.wrap!r}")
        elif token.startswith("lang:"):
            mk.lang = token[len("lang:"):]
            if mk.lang not in ("5", "6"):
                raise MarkerError(f"lang must be 5|6, got {mk.lang!r}")
        elif token.startswith("prelude:"):
            mk.prelude = token[len("prelude:"):]
        else:
            raise MarkerError(f"unknown marker {token!r}")
    for t in mk.compile_targets + mk.xfail_targets:
        if t not in TARGETS:
            raise MarkerError(f"unknown target {t!r}")
    overlap = set(mk.compile_targets) & set(mk.xfail_targets)
    if overlap:
        raise MarkerError(f"target(s) in both compile and xfail: {sorted(overlap)}")
    if mk.illustrative and (mk.compile_targets or mk.xfail_targets or mk.imports
                            or mk.wrap != "auto" or mk.prelude):
        raise MarkerError("illustrative excludes all other markers")
    return mk


def validate_markers_against_body(mk, body_imports):
    """compile:26 / xfail:26 with a structurally-absent module is dishonest
    (trivially true xfail) — hard error."""
    absent = set(body_imports) & ABSENT_ON_26 | set(mk.imports) & ABSENT_ON_26
    if absent and "26" in mk.compile_targets + mk.xfail_targets:
        raise MarkerError(
            f"module(s) {sorted(absent)} do not exist in the 26 SDK; "
            "use targets 27/sim27 (verifier reports no-sdk for 26)")


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


def synthesize(fence, extra_imports, wrap):
    """Return (source, linemap) where linemap[gen_line_0based] = guide 1-based
    line or None for synthesized lines."""
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
        else:  # top
            for i, line in zip(rest_map, rest):
                gen.append(line)
                linemap.append(body_offset + 1 + i)
    return "\n".join(gen) + "\n", linemap, modules


# ---------------------------------------------------------------------------
# Toolchains + compilation


def discover_toolchain(name):
    dev_dir, sdk_name, triple_tpl = TARGETS[name]
    if not os.path.isdir(dev_dir):
        raise SystemExit(f"error: developer dir for target {name} missing: {dev_dir}")
    env = dict(os.environ, DEVELOPER_DIR=dev_dir)

    def xcrun(*args):
        return subprocess.run(["xcrun"] + list(args), env=env, capture_output=True,
                              text=True, check=True).stdout.strip()

    sdk_path = xcrun("--sdk", sdk_name, "--show-sdk-path")
    sdk_version = xcrun("--sdk", sdk_name, "--show-sdk-version")
    sdk_build = xcrun("--sdk", sdk_name, "--show-sdk-build-version")
    out = subprocess.run(["xcodebuild", "-version"], env=env, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    xcode_version = out[0].replace("Xcode", "").strip() if out else "?"
    xcode_build = out[1].replace("Build version", "").strip() if len(out) > 1 else "?"
    platform_dir = {"macosx": "MacOSX", "iphonesimulator": "iPhoneSimulator"}[sdk_name]
    fw = os.path.join(dev_dir, "Platforms", f"{platform_dir}.platform",
                      "Developer", "Library", "Frameworks")
    return Toolchain(name, dev_dir, sdk_path, sdk_version, sdk_build,
                     triple_tpl.format(v=sdk_version), xcode_version, xcode_build,
                     (fw,) if os.path.isdir(fw) else ())


FIRST_ERROR_RE = re.compile(r"^<stdin>:(\d+):(\d+): error: (.*)$")


def typecheck(source, tc, swift_version, needs_xcode_frameworks, cache_root,
              linemap=None, timeout=60, stub=None):
    if stub is not None:
        return CompileResult("pass") if stub == "pass" else \
            CompileResult("fail", first_error=stub.split(":", 1)[1] if ":" in stub else "stubbed failure")
    cmd = ["xcrun", "swiftc", "-typecheck",
           "-swift-version", swift_version,
           "-sdk", tc.sdk_path,
           "-target", tc.triple,
           "-diagnostic-style", "llvm",
           "-module-cache-path", os.path.join(cache_root, tc.sdk_build)]
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
    guess_kwargs = dict(swift_version=mk.lang, cache_root=opts.cache_root,
                        timeout=opts.timeout, stub=opts.stub_compiler)
    if mk.wrap == "auto":
        first_choice = choose_wrap(hoist_imports(fence.body)[2])
        order = [first_choice, "body" if first_choice == "top" else "top"]
    else:
        order = [mk.wrap]
    last = None
    needs_xcode_fw = bool(set(imports) & XCODE_ONLY_MODULES)
    for wrap in order:
        source, linemap, _modules = synthesize(fence, imports, wrap)
        result = typecheck(source, tc, linemap=linemap,
                           needs_xcode_frameworks=needs_xcode_fw, **guess_kwargs)
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
           "wrap": "", "v26": "-", "v27": "-", "vsim27": "-",
           "err_line": "", "first_error": "", "flags": autodetect(fence)}
    col = {"26": "v26", "27": "v27", "sim27": "vsim27"}
    try:
        mk = parse_markers(fence.info)
        body_imports = hoist_imports(fence.body)[0]
        validate_markers_against_body(mk, body_imports)
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
        overall = "VERIFIED" if mk.compile_targets else "XFAIL-PROVEN"
        for target in mk.compile_targets + mk.xfail_targets:
            xfail = target in mk.xfail_targets
            body_imports = hoist_imports(fence.body)[0]
            if target == "26" and set(body_imports) & ABSENT_ON_26:
                row[col[target]] = "no-sdk"
                continue
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
    verdict, wrap, result = compile_variants(fence, Markers(), imports, tc, opts, False)
    row[col[target]] = verdict
    row["wrap"] = wrap
    row["status"] = "UNCLASSIFIED-PASS" if verdict == "pass" else "UNCLASSIFIED-FAIL"
    row["first_error"] = result.first_error
    row["err_line"] = result.err_line
    row["_guess_imports"] = imports
    return row


# ---------------------------------------------------------------------------
# Output


TSV_COLUMNS = ["file", "line", "anchor", "info", "status", "wrap",
               "v26", "v27", "vsim27", "err_line", "first_error"]


def write_tsv(rows, out):
    out.write("\t".join(TSV_COLUMNS) + "\n")
    for r in rows:
        out.write("\t".join(flatten(r.get(c, "")) if c == "first_error" else
                            flatten(r.get(c, ""), 200) for c in TSV_COLUMNS) + "\n")


def write_report(rows, toolchains, opts, out):
    from collections import Counter, defaultdict
    counts = Counter(r["status"] for r in rows)
    out.write("# Snippet compile-verification report\n\n")
    out.write(f"Generated by scripts/verify-snippets.py (WRAPPER_VERSION={WRAPPER_VERSION}, "
              f"-swift-version 6 default, jobs={opts.jobs}"
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

    per_guide = defaultdict(Counter)
    for r in rows:
        per_guide[r["file"]][r["status"]] += 1
    out.write("## Per-guide rollup\n\n")
    out.write("| guide | fences | verified/pass | xfail-proven | illus./stub/elided | unclassified pass–fail | FAILING |\n")
    out.write("|---|---|---|---|---|---|---|\n")
    for guide in sorted(per_guide):
        c = per_guide[guide]
        total = sum(c.values())
        out.write(f"| {guide} | {total} | {c['VERIFIED'] + c['UNCLASSIFIED-PASS']} | "
                  f"{c['XFAIL-PROVEN']} | {c['ILLUSTRATIVE'] + c['STUB'] + c['ELIDED']} | "
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


def write_markers(rows, guides_root, opts):
    """Add compile:27 [imports:...] to UNCLASSIFIED-PASS fences and
    illustrative to STUB/ELIDED ones. Only opening-fence lines change."""
    dirty = subprocess.run(["git", "status", "--porcelain", "--", guides_root],
                           capture_output=True, text=True).stdout.strip()
    if dirty and not opts.stub_compiler:
        raise SystemExit("error: guides tree is dirty; commit or stash before --write-markers")

    pre_fences, _ = extract_fences(guides_root)
    pre_hashes = [hashlib.sha256("\n".join(f.body).encode()).hexdigest() for f in pre_fences]

    by_file = {}
    for r in rows:
        new_info = None
        if r["status"] == "UNCLASSIFIED-PASS":
            new_info = f"compile:{opts.guess_target}"
            extra = r.get("_needed_imports")
            if extra:
                new_info += " imports:" + ",".join(extra)
        elif r["status"] in ("STUB", "ELIDED"):
            new_info = "illustrative"
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
    actually needed: recompile with hoisted-only; record extras if required."""
    tc = toolchains[opts.guess_target]
    for r in rows:
        if r["status"] != "UNCLASSIFIED-PASS":
            continue
        fence = r["_fence"]
        verdict, _, _ = compile_variants(fence, Markers(), [], tc, opts, False)
        if verdict == "pass":
            r["_needed_imports"] = []
            continue
        # Binary-search would be overkill; drop imports one at a time.
        needed = list(r.get("_guess_imports", []))
        for mod in list(needed):
            trial = [m for m in needed if m != mod]
            verdict, _, _ = compile_variants(fence, Markers(), trial, tc, opts, False)
            if verdict == "pass":
                needed = trial
        r["_needed_imports"] = [m for m in needed if m not in ("Foundation",)] or needed
    return rows


# ---------------------------------------------------------------------------
# Main


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--guides", default="guides")
    ap.add_argument("--sdk", action="append", choices=sorted(TARGETS),
                    dest="sdks", default=None,
                    help="targets to resolve (repeatable); default: those the markers request")
    ap.add_argument("--guess", action="store_true",
                    help="attempt unmarked fences against --guess-target")
    ap.add_argument("--guess-target", default="27", choices=sorted(TARGETS))
    ap.add_argument("--changed", nargs="?", const="HEAD", default=None, metavar="REF",
                    help="only fences in guide files changed vs REF (default HEAD)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", default=None,
                    help="directory for results.tsv + report.md (default: stdout TSV only)")
    ap.add_argument("--write-markers", action="store_true")
    ap.add_argument("--cache-root",
                    default=os.path.expanduser("~/Library/Caches/snippet-verify"))
    ap.add_argument("--stub-compiler", default=None, metavar="pass|fail:<msg>",
                    help="test-only: replace swiftc with a fixed result")
    opts = ap.parse_args(argv)

    fences, parse_errors = extract_fences(opts.guides)
    if opts.changed:
        changed = subprocess.run(
            ["git", "diff", "--name-only", opts.changed, "--", opts.guides],
            capture_output=True, text=True).stdout.splitlines()
        changed = {os.path.relpath(p, opts.guides) for p in changed}
        status_files = subprocess.run(
            ["git", "status", "--porcelain", "--", opts.guides],
            capture_output=True, text=True).stdout.splitlines()
        changed |= {os.path.relpath(l[3:].strip(), opts.guides) for l in status_files if l}
        fences = [f for f in fences if f.rel_path in changed]

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
                     "status": "PARSE-ERROR", "wrap": "", "v26": "-", "v27": "-",
                     "vsim27": "-", "err_line": "", "first_error": msg, "flags": set()})

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
