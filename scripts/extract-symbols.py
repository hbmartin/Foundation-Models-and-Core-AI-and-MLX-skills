#!/usr/bin/env python3
"""Extract API-ish symbols from backticked code spans in the guides.

Output TSV: symbol<TAB>framework-guess<TAB>total-mentions<TAB>n-guides<TAB>sdk26<TAB>sdk27<TAB>guides
  sdk26/sdk27: Y if the bare symbol name appears in any captured 26.x / 27.0 swiftinterface.
  guides: semicolon list of "path:count", highest count first, capped at GUIDE_CAP.

Importable as well as runnable: scripts/build-skills.py calls collect_symbol_counts()
and symbol_rows() directly so it can slice per skill against the *uncapped* guide
list. Slicing the rendered guides/API-INDEX.md instead would lose coverage twice
over, because that page shows only the first 4 of a list already capped here.
"""
import os, re, sys
from collections import defaultdict

# Guides shown per symbol in the TSV. The committed API-INDEX.md is generated
# from this cap, so changing it changes that page; callers who need the full
# association set pass cap=None to symbol_rows().
GUIDE_CAP = 12

# A symbol is: a CamelCase identifier, optionally dotted / parenthesised, found in `code`.
SPAN = re.compile(r'`([^`\n]{2,90})`')
# Accept: TypeName, TypeName.member, method(with:labels:), @Macro, .enumCase, snake_case CLI names kept out.
SYM = re.compile(r'^@?[A-Z][A-Za-z0-9]*(\.[A-Za-z0-9_]+(\(\s*[a-z_:\s]*\))?)*$'
                 r'|^@[A-Z][A-Za-z0-9]*$')

def norm(s):
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    return s

FW_RULES = [
    (r'^(FoundationModels|LanguageModelSession|LanguageModelFeedback|LanguageModelError|StructuredTranscript)(\.|$)', 'FoundationModels'),
    (r'^(CoreAI(?:Asset|Cache|Common|Compiler|Delegates|Runtime)?)(\.|$)', 'CoreAI'),
    (r'^(Evaluations|Evaluator|Evaluation|EvaluationResult)(\.|$)', 'Evaluations'),
    (r'^(LanguageModel|SystemLanguageModel|PrivateCloudCompute|ChatCompletions|MLXLanguageModel|CoreAILanguageModel|Generable|Guide\b|GenerationError|GeneratedContent|Transcript|Instructions|Prompt\b|Profile|DynamicProfile|Tool\b|Tool\.|Session|Respond|QuotaUsage|UnavailableReason|Refusal|Feedback|Adapter|SystemModels)', 'FoundationModels'),
    (r'^(AIModel|InferenceFunction|InferenceValue|NDArray|NDArrayDescriptor|ImageDescriptor|ComputeStream|AssetError|AIModelCache|AssetPack|Specializ)', 'CoreAI'),
    (r'^(MLX|GPUArray)', 'MLX'),
    (r'^(Speech|SFSpeech|SFCustom|DictationTranscriber|AnalyzerInput|AssetInventory|AssetInputSequence|CaptureInputSequence|AnalyzerInputConverter|SpeechDetector|SpeechTranscriber)', 'Speech'),
    (r'^(CSSearchable|CSUser|CSSuggestion|CSImport|Spotlight)', 'CoreSpotlight'),
    (r'^(AppIntent|AppEntity|AppEnum|AppShortcut|IndexedEntity|EntityCollection|SyncableEntity|RelevantEntities|OwnershipProviding|IndexedEntityQuery|ValueRepresentation|UnionValue|StringSearchCriteria|SnippetIntent|LongRunningIntent|ExecutionTargets|AssistantSchema|EntityQuery|IntentDescription|TypeDisplayRepresentation|DisplayRepresentation)', 'AppIntents'),
    (r'^(BarcodeReaderTool|OCRTool|VN[A-Z]|ImageAnaly)', 'Vision'),
    (r'^(MPP|MPS|TensorOps|MTL|Metal)', 'Metal/MPP'),
    (r'^(Evaluations?\b|Eval\b|Grader|Judge|Scorecard)', 'Evaluations'),
    (r'^(CI[A-Z]|CV[A-Z]|CG[A-Z]|CM[A-Z]|AV[A-Z])', 'Media/Core*'),
    (r'^(URL|Data\b|String\b|Task\b|Array|Dictionary|Result\b|Codable|Sendable|Duration|Date\b|UUID|JSON|Foundation)', 'Swift/Foundation'),
    (r'^(View\b|Text\b|Image\b|Button|List\b|NavigationStack|ObservableObject|State\b|Binding|SwiftUI|App\b|Scene\b|WindowGroup)', 'SwiftUI'),
]

def guess_fw(sym):
    base = sym.lstrip('@.')
    for pat, fw in FW_RULES:
        if re.search(pat, base):
            return fw
    return 'other'


def collect_symbol_counts(root):
    """symbol -> {guide-relative path: mention count}, uncapped and unfiltered."""
    counts = defaultdict(lambda: defaultdict(int))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            # Never scan the generated index pages: the symbol index would index
            # itself, inflating every count on each regeneration.
            if not fn.endswith('.md') or fn in ('SILENT-FAILURES.md', 'API-INDEX.md'):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            with open(path, encoding='utf-8') as handle:
                text = handle.read()
            # Inline `code` spans only; fenced blocks contribute nothing (a fence
            # line never forms a span), so no stripping pass is needed.
            for m in SPAN.finditer(text):
                s = norm(m.group(1))
                if SYM.match(s) and not re.search(r'\.(swift|py|md|json|txt|h)$', s):
                    counts[s][rel] += 1
    return counts


def sdk_presence(iface_dir):
    """(text of every captured 26.x interface, text of every 27.x interface)."""
    def iface_text(pattern):
        buf = []
        if not os.path.isdir(iface_dir):
            return ''
        for fn in os.listdir(iface_dir):
            if pattern in fn and fn.endswith('.swiftinterface'):
                with open(os.path.join(iface_dir, fn), encoding='utf-8') as handle:
                    buf.append(handle.read())
        return '\n'.join(buf)
    return iface_text('-26.'), iface_text('-27.')


def symbol_rows(counts, sdk26, sdk27, cap=GUIDE_CAP):
    """Rendered rows in TSV order. cap=None keeps every guide association.

    The noise floor and the sort are corpus-wide on purpose: a caller slicing
    per skill must start from the same symbol set the series index uses, or it
    produces a different index rather than a subset of one.
    """
    out = []
    for sym, files in counts.items():
        total = sum(files.values())
        if total < 2 and len(files) < 2:
            continue  # noise floor: mentioned once in one guide
        base = sym.lstrip('@.').split('.')[0].split('(')[0]
        in26 = 'Y' if base and re.search(r'\b%s\b' % re.escape(base), sdk26) else ''
        in27 = 'Y' if base and re.search(r'\b%s\b' % re.escape(base), sdk27) else ''
        # Counts often tie at the visible cutoff. Use the guide path as an explicit
        # secondary key so selection stays stable independently of traversal order.
        top = sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))
        if cap is not None:
            top = top[:cap]
        out.append((sym, guess_fw(sym), total, len(files), in26, in27,
                    ';'.join(f'{p}:{c}' for p, c in top)))
    out.sort(key=lambda r: (-r[2], r[0]))
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "guides"
    iface_dir = sys.argv[2] if len(sys.argv) > 2 else "notes/sdk-interfaces"
    sdk26, sdk27 = sdk_presence(iface_dir)
    out = symbol_rows(collect_symbol_counts(root), sdk26, sdk27)
    for r in out:
        print('\t'.join(str(x) for x in r))
    print(f"# symbols kept: {len(out)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
