#!/usr/bin/env python3
"""Extract API-ish symbols from backticked code spans in the guides.

Output TSV: symbol<TAB>framework-guess<TAB>total-mentions<TAB>n-guides<TAB>sdk26<TAB>sdk27<TAB>guides
  sdk26/sdk27: Y if the leading type appears and every dotted uppercase type component
  is one contiguous subpath of a declared/qualified type chain in a captured swiftinterface.
  A longer chain may prove any contiguous type subpath; `::` module qualifiers may appear only at
  the start of a recorded path and are never treated as nested type components.
  guides: semicolon list of "path:count", highest count first, capped at GUIDE_CAP.

Importable as well as runnable: scripts/build-skills.py calls collect_symbol_counts()
and symbol_rows() directly so it can slice per skill against the *uncapped* guide
list. Slicing the rendered guides/API-INDEX.md instead would lose coverage twice
over, because that page shows only the first 4 of a list already capped here.
"""
import os, re, sys
from collections import defaultdict

from mdlinks import iter_lines

# Guides shown per symbol in the TSV. The committed API-INDEX.md is generated
# from this cap, so changing it changes that page; callers who need the full
# association set pass cap=None to symbol_rows().
GUIDE_CAP = 12

# A symbol is: a CamelCase identifier, optionally dotted / parenthesised, found in `code`.
SPAN = re.compile(r'`([^`\n]{2,90})`')
# Accept: TypeName, TypeName.member, method(with:labels:), @Macro, .enumCase, snake_case CLI names kept out.
SYM = re.compile(r'^@?[A-Z][A-Za-z0-9]*(\.[A-Za-z0-9_]+(\(\s*[a-z_:\s]*\))?)*$'
                 r'|^@[A-Z][A-Za-z0-9]*$')
TYPE_NAME = re.compile(r'\b[A-Z][A-Za-z0-9_]*\b')
QUALIFIED_TYPE_PATH = re.compile(
    r'\b_?[A-Z][A-Za-z0-9_]*(?:(?:::|\.)_?[A-Z][A-Za-z0-9_]*)+'
)
TYPE_DECLARATION = re.compile(
    r'\b(struct|class|enum|protocol|typealias|associatedtype)\s+'
    r'([A-Z][A-Za-z0-9_]*)\b'
)
EXTENSION_DECLARATION = re.compile(
    r'\bextension\s+(_?[A-Z][A-Za-z0-9_]*(?:(?:::|\.)_?[A-Z][A-Za-z0-9_]*)*)'
)

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
            # Scan prose lines only. Backticks inside fenced examples are source
            # syntax, not inline mentions, and previously advertised fake symbols
            # such as fixture type names in the generated API index.
            for line, _newline, inside_fence in iter_lines(text):
                if inside_fence:
                    continue
                for m in SPAN.finditer(line):
                    s = norm(m.group(1))
                    if (
                        SYM.match(s)
                        and not re.search(r'\.(swift|py|md|json|txt|h|zip)$', s)
                        # Reject handle-like prose tokens such as `J0hn` without
                        # excluding API families whose digits end a component
                        # (`Float16`) or precede another capital (`SHA256Digest`).
                        and not re.search(r'\d[a-z]', s)
                    ):
                        counts[s][rel] += 1
    return counts


class SDKPresence:
    """Precomputed interface token and ordered type-path presence.

    A token set preserves the intentionally coarse behavior for a bare type or a
    lowercase member spelling. Dotted uppercase spellings must be a contiguous subpath
    of one declaration or qualified reference. Module-qualified interface spellings such
    as ``Module::Outer.Module::Inner`` are normalized to ``Outer.Inner`` while retaining
    ``Module.Outer.Inner``; a module qualifier in the middle starts a new chain instead
    of becoming a fake nested type.
    """

    def __init__(self, sources=()):
        self.names = set()
        self.type_paths = set()
        for module, text in sources:
            self.names.update(TYPE_NAME.findall(text))
            self._index_qualified_references(text)
            self._index_declarations(module, text)

    @staticmethod
    def _qualified_type_chains(spelling):
        """Return ``(module, type-components)`` chains without crossing modules.

        Swift interfaces repeat a module qualifier before nested components, for
        example ``CoreAI::Value.CoreAI::Descriptor``. Equal qualifiers belong to
        one type chain. A qualifier introduced after an unqualified path, or a
        different qualifier, starts a new chain.
        """
        chains = []
        active_module = None
        active_parts = []
        for atom in spelling.split('.'):
            qualified = atom.split('::')
            if len(qualified) == 1:
                active_parts.append(atom)
                continue
            if len(qualified) != 2 or not all(qualified):
                if active_parts:
                    chains.append((active_module, active_parts))
                active_module = None
                active_parts = []
                continue
            next_module, name = qualified
            if active_parts and active_module != next_module:
                chains.append((active_module, active_parts))
                active_parts = []
            active_module = next_module
            active_parts.append(name)
        if active_parts:
            chains.append((active_module, active_parts))
        return chains

    def _record_path(self, parts):
        parts = tuple(part for part in parts if part and part[0].isupper())
        # Record every contiguous path of two or more components. Suffixes are
        # useful because a module (and occasionally an enclosing compatibility
        # namespace) can be omitted at a Swift call site; prefixes are required
        # because a longer qualified reference also proves its enclosing path.
        for start in range(max(0, len(parts) - 1)):
            for end in range(start + 2, len(parts) + 1):
                self.type_paths.add(parts[start:end])

    def _record_qualified_spelling(self, spelling):
        for module, parts in self._qualified_type_chains(spelling):
            self._record_path(parts)
            if module:
                # A dotted guide spelling may explicitly name its module, but a
                # module token is valid only as the leading component.
                self._record_path([module, *parts])

    def _index_qualified_references(self, text):
        for match in QUALIFIED_TYPE_PATH.finditer(text):
            self._record_qualified_spelling(match.group())

    def _index_declarations(self, module, text):
        depth = 0
        # Each item is (minimum brace depth while active, owning module,
        # path without module). Extensions can target a foreign module, so the
        # file's module is not sufficient provenance for nested declarations.
        contexts = []
        for line in text.splitlines():
            while contexts and depth < contexts[-1][0]:
                contexts.pop()

            extension = EXTENSION_DECLARATION.search(line)
            declaration = TYPE_DECLARATION.search(line)
            opens_block = '{' in line
            if extension and opens_block:
                chains = self._qualified_type_chains(extension.group(1))
                extension_module, parts = chains[-1] if chains else (None, [])
                # Older textual interfaces can repeat the file module with a
                # dot (``Module.Type``). Strip only that known module: a dotted
                # ``Outer.Inner`` may instead be a genuine nested type.
                if extension_module is None and module and parts and parts[0] == module:
                    extension_module, parts = module, parts[1:]
                self._record_path(parts)
                path_module = extension_module or module
                self._record_path(([path_module] if path_module else []) + parts)
                contexts.append((depth + 1, path_module, parts))
            elif declaration:
                kind, name = declaration.groups()
                path_module = contexts[-1][1] if contexts else module
                parent = contexts[-1][2] if contexts else []
                path = [*parent, name]
                self._record_path(([path_module] if path_module else []) + path)
                self._record_path(path)
                if opens_block and kind not in ('typealias', 'associatedtype'):
                    contexts.append((depth + 1, path_module, path))

            depth += line.count('{') - line.count('}')
            while contexts and depth < contexts[-1][0]:
                contexts.pop()

    def contains(self, symbol):
        parts = [part.split('(')[0]
                 for part in symbol.lstrip('@.').split('.')]
        checked = [part for part in parts if part and part[0].isupper()] or parts[:1]
        if len(checked) == 1:
            return bool(checked) and checked[0] in self.names
        return tuple(checked) in self.type_paths


def sdk_presence(iface_dir):
    """Precomputed presence indexes for captured 26.x and 27.x interfaces."""
    def iface_index(pattern):
        sources = []
        if not os.path.isdir(iface_dir):
            return SDKPresence()
        for fn in sorted(os.listdir(iface_dir)):
            if pattern not in fn or not fn.endswith('.swiftinterface'):
                continue
            module_match = re.match(r'(.+)-(?:26|27)\.', fn)
            module = module_match.group(1) if module_match else None
            with open(os.path.join(iface_dir, fn), encoding='utf-8') as handle:
                sources.append((module, handle.read()))
        return SDKPresence(sources)
    return iface_index('-26.'), iface_index('-27.')


def symbol_rows(counts, sdk26, sdk27, cap=GUIDE_CAP):
    """Rendered rows in TSV order. cap=None keeps every guide association.

    The noise floor and the sort are corpus-wide on purpose: a caller slicing
    per skill must start from the same symbol set the series index uses, or it
    produces a different index rather than a subset of one.
    """
    sdk26 = sdk26 if isinstance(sdk26, SDKPresence) else SDKPresence([(None, sdk26)])
    sdk27 = sdk27 if isinstance(sdk27, SDKPresence) else SDKPresence([(None, sdk27)])
    out = []
    for sym, files in counts.items():
        total = sum(files.values())
        if total < 2 and len(files) < 2:
            continue  # noise floor: mentioned once in one guide
        in26 = 'Y' if sdk26.contains(sym) else ''
        in27 = 'Y' if sdk27.contains(sym) else ''
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
