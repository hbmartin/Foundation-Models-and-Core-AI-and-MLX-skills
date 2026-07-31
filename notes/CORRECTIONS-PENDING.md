# Corrections pending — apply to already-written guides

Findings that arrived AFTER a guide was drafted, or that supersede what a note said. Every item
here must be reconciled before the affected guide is considered done.

Status legend: 🔧 not yet applied · ✅ applied · ⚠️ partially applied

**Reconciled 2026-07-31.** Every item was audited against the guides on disk; the markers below are
now authoritative. Ten items were found fully applied; C6's last residue (the part-17/part-16
reassertions of the retracted ANE-routing claim) was fixed during the reconciliation pass; C7
remains ⚠️ partial — its facts landed but the owning non-LLM guide is unwritten, tracked as open
backlog. Where a register entry was itself superseded by later evidence (C3's scale-plane deletion
and 26.2 floor), the item now carries a superseded note; the guides follow the later finding.

---

## ✅ C1 — Siri-enablement gating is a BUG, not behaviour

**Applied:** part-01 ref 02 §7.4 ("an acknowledged defect, not a gate", Frameworks-Engineer quote),
part-02 ref 06 (~:276–285), part-17 ref 01 (~:48, ~:1495).

**Affects:** `part-01-orientation-and-gating/references/02-platform-and-version-gating.md`,
and any guide that repeats the availability story (Part 2 guide 06, Part 17 guide 01).

**What we believed:** forum threads 835211 and 836760 report that
`SystemLanguageModel.default.availability` returns `.appleIntelligenceNotEnabled` unless the user
has enabled "Siri"/"Hey Siri" or "Press Side Button for Siri". Our notes and the Part 1 brief
present this as *behaviour to design around*, including an EU-availability concern.

**What is actually true:** an **Apple Frameworks Engineer confirmed on thread 836760 that this is a
bug.** Source: `notes/web/app-intents-siri-schemas.md`.

**Required change:** keep the symptom (developers will hit it on 27 betas), but reclassify it from
"a gate you must design around" to "a known defect with an Apple acknowledgement." Do not advise
readers to build permanent UX around requiring Siri. Add the Apple acknowledgement and mark status
as unresolved-as-of-2026-07-27. This materially changes the advice.

---

## ✅ C2 — The second Core Spotlight on-ramp is `indexAppEntities`

**Applied:** part-02 ref 04 §2.3 "One index, three consumers" (mechanism at ~:249, diagram
~:282–287, Part 16 cross-link). The declared delegate-invocation gap is preserved in the guide's
gap table, as instructed below.

**Affects:** `part-02-foundation-models-everyday-api/references/04-spotlight-rag-and-system-tools.md`

**Open question in our corpus** (`notes/transcripts/fm-ecosystem.md:1400-1401`): WWDC26 session 246
says content reaches the model if your app "donates searchable items to Core Spotlight, **or indexed
entities for Apple Intelligence**" — we could not identify what that second clause meant.

**Resolved:** it is `IndexedEntity` + **`CSSearchableIndex.indexAppEntities(_:)`**. App Intents
entities and Core Spotlight items land in the **same semantic index**, which is then read by three
different consumers: Siri entity resolution, `SpotlightSearchTool`, and Spotlight search itself.
Source: `notes/web/app-intents-siri-schemas.md`.

**Required change:** replace the unresolved note with the real mechanism, and add a short section
on the one-index/three-consumers model. Cross-link to the new Part 16 App Intents guides.

**Remaining 🔴 GAP:** whether `CSSearchableIndexDelegate.searchableItems(forIdentifiers:)` fires
for entity-indexed content (as opposed to `CSSearchableItem`-donated content) is unverified. Keep
as a declared gap.

---

## ✅ C3 — Part 11 must be rebuilt around what MPP actually ships

**Applied — with two register bullets superseded by later evidence.** Part 11 is written and tells
the *current* story: the **27.0 SDK headers DO ship blockwise scale planes** (`tensor_blockwise` +
`tensor_plane_scales`, ue8m0-only — see `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 6, which
inverted this item's "scale planes do not exist" finding for the 27 surface; the 26.x absence below
remains true), and the availability story is the Tech Talk ladder per C10.5, **not** the "26.2"
this item's required-change paragraph asks for. All other bullets (reduce_rows, descriptor arity,
execution aliases, the two silent failures, NAX freshness, the mlx-core.md source fix) landed in
part-11 refs 01/02.

**Affects:** all of `part-11-metal-and-tensorops/`.

**What we believed** (from WWDC26 session 330, spoken narration only): `MTLTensor` can carry a
**scale plane** alongside quantised data, using FP8 `E8M0` block-wise scale factors declared via a
plane descriptor with `dataType` + `blockFactors` and an auxiliary plane map; new dtypes in 27
include int2, fp4, fp8.

**What is actually true** (`notes/repos/mlx-tensorops-kernels.md`, verified against the
`MetalPerformancePrimitives` headers shipped in the Xcode 26.6 SDK — ~14,300 lines including
Apple's own prose and four worked examples — plus the Metal-language headers in the cryptex
toolchain):

- **Scale planes do not exist.** Zero hits for `scale`, `plane`, `fp8` or `e8m0` across all ~17k
  lines of headers.
- **Availability is NOT 27 — but it is also NOT "26.2".**
  ⚠️ **This bullet previously said "26.2" and that was wrong.** Tech Talk 111432
  ("Accelerate your machine learning workloads with the M5 and A19 GPUs") gives an explicit
  per-point-release feature ladder of **26.1, 26.3 and 26.4 — there is no 26.2 in it.**
  See `notes/transcripts/missing-sessions.md` §7.5, which the agent that found it called the most
  consequential correction in that file. **Take the version floor from the ladder in §7.5, not from
  this register, and not from any earlier draft.**
- Supported tensor element types include `int8_t` and `metal::int4b_format` / `uint4b_format`.
  **int2, fp4, fp8 and E8M0 are absent** from `__tensor_ops_datatype`.
- MLX **hand-dequantises** in software into threadgroup memory
  (`QuantizedBlockLoader::load_unsafe` → `threadgroup T* dst`), then loads full-precision tiles into
  registers and cooperative tensors. MPP only ever sees dense half/bfloat/float.
- `fp8_e8m0` / `fp8_e4m3` / `fp4_e2m1` are **MLX's own structs** in `fp8.h` / `fp4.h`, not Metal types.
- `matmul2d_descriptor` takes 7 positional args and its **default mode is `multiply`, not
  `multiply_accumulate`**.
- `execution_simdgroup` / `execution_thread` are **aliases** for `execution_simdgroups<1>` /
  `execution_threads<1>`. **`execution_threadgroup` does not exist.**
- `reduce_rows` is a **free function**, not a member; signature `(src, dst, op, identity)`;
  `reduction_operation` has exactly three cases `{sum, max, min}`.
- Cooperative tensors **can** be fed directly into a matmul — confirmed by SFINAE in `run()` and
  proven by MLX. `get_{left,right}_input_cooperative_tensor` take *element* types;
  `get_destination_cooperative_tensor` takes *operand* types — this asymmetry is the #1 compile
  failure.
- The M5 neural accelerator has **no API**; it is inferred from
  `get_architecture_gen() >= 17` (18 for `'p'`).

**Required change:** delete the scale-plane material entirely — there is no compiling example of it
anywhere. Rewrite the guide around "TensorOps gives you 4- and 8-bit integer operands and no scale
mechanism; here is how MLX builds MX and NV formats on top of that." ~~Correct the availability
floor to 26.2.~~ (Superseded — use C10.5's ladder; see the Applied note above. The scale-plane
deletion is likewise superseded for the 27 surface.) Correct guide 35's source list, which
currently cites `notes/repos/mlx-core.md` for material that file does not contain.

**Two ⚠️ SILENT FAILURE callouts this creates:**
1. `reduce_rows`' `identity` defaults to `sum_identity` (zero) **regardless of the operation**, so
   `reduction_operation::max` silently clamps negative values to 0.
2. `relaxed_precision = true` is hardcoded at `nax.h:406`, which is why the host gates float32 on
   `MLX_ENABLE_TF32` — one feature, two halves, and they must be taught together.

**Freshness caution:** four NAX correctness fixes landed in the three days before 2026-07-27
(#3912, #3922, #3924) — including a missing `else` in `tile_matmad_nax` that silently miscompiles
odd tile shapes. Present NAX as new and sharp-edged.

---

## ✅ C4 — `@Generable` is unavailable on the fast BYO-model path

**Applied:** part-01 map decision-table row (~:1068) + §5.1; part-04 ref 02 §5 ("The logits
constraint"); attributed as community-measured.

**Affects:** `part-02-foundation-models-everyday-api/references/02-guided-generation-and-streaming.md`
(already briefed), `part-04-beyond-the-built-in-model/` (all guides), and the Part 1 decision table.

Grammar-constrained decoding requires access to engine **logits**. GPU-pipelined Core AI bundles
never expose them. Consequence: an app that brings its own model **loses Apple's flagship
structured-generation feature exactly when it selects the fastest backend.**
Source: `notes/repos/john-rocky-models.md` (community-measured; attribute as such).

**Required change:** this is a first-class architectural constraint, not a footnote. It belongs in
the Part 1 backend decision table as a column, and needs a full section in Part 4.

---

## ✅ C5 — Prefix reuse is worth ~101×, but not for hybrid architectures

**Applied:** part-01 §5.2 + decision-table row; part-03 ref 01 (~:2226–2273, incl. the
hybrid-model table); part-04 ref 04 §9.4; part-07 ref 03. The `trimKVCache` return-value contract
appears verbatim in all three reference guides.

**Affects:** `part-03-context-profiles-agentic/` (KV cache guide), `part-04-beyond-the-built-in-model/`
(provider executor guide), `part-07-coreai-swift-runtime/` (states guide), Part 1 decision table.

Community-measured (`notes/repos/john-rocky-models.md`): turn-2 TTFT **23.28 s → 0.230 s (101×)** at
4k context with byte-identical greedy output; 15.2× at 357 tokens (qwen3-0.6b, Mac).

Mechanism: trimming the KV cache is a **single integer assignment** — nothing is cleared, only
`processedTokenCount` rewinds. It is free because attention is causal, so rows at or beyond the
retained position are overwritten before any query can read them.

**The constraint that matters for model selection:** `trimKVCache` returns `-1` (unsupported)
whenever `extraStates` is non-empty. SSM / GatedDeltaNet state is a *running scan*, not
positionally addressed, so it cannot be rewound. **Linear-attention and hybrid models — Qwen3.5,
Qwen3.6, LFM2.5, Granite 4 — forfeit prefix caching entirely and must re-prefill every turn.**

**Required change:** treat this as a model-selection consequence in Part 1, not just a tuning tip.
Also note the API contract: `trimKVCache(to:)` returns the *actual* retained prefix, which may be
`length - 1` because the last generated token's KV lags one step — callers must prefill from the
returned value, not the requested one.

---

## ✅ C6 — Splitting a model into multiple functions is what routes it to the ANE

**Applied — and rescoped.** The claim as written above was later narrowed: the split drives the
optional `coreai-models` **loader's** ANE preference (`ModelStructure.swift` classifier), a package
loading policy, not a Core AI framework routing contract. The rescoped framing landed in parts
7/8/9/10/14 behind the shared `[^sample-routing-policy]` footnote; the last two reassertions of the
unscoped claim (part-17 ref 02 §7.6 + tables, part-16 ref 01 §14.2) were fixed 2026-07-31. The
re-encode caveat is in part-07 ref 04 and part-17 ref 02 §7.6.

**Affects:** `part-07-coreai-swift-runtime/`, `part-08-coreai-pytorch-conversion/`,
`part-10-coreai-hardware-authoring-debugging/`.

WWDC26 session 325 presents splitting SAM3 into three entrypoints (`image_encode` / `text_encode` /
`detect`) as a **latency trick** — run each at a different cadence, 76% faster second inference.

Reading the shipped code (`notes/repos/coreai-models-nonllm.md`,
`ModelStructure.swift:71-80`) shows the split is also what **routes the model to the Neural
Engine**. That is a much stronger reason to do it, and it changes how the technique should be
taught.

⚠️ **But**: `CoreAISegmentationEngine` **re-runs `image_encode` on every call** and exposes no
cache. The 76% figure requires caller-side work that Apple's own package does not do for you.

---

## ⚠️ C7 — Non-LLM Core AI needs coverage that the 50-topic list lacked

**Partially applied — OPEN BACKLOG.** Every verified fact below landed, scattered: llm-benchmark-only
+ no published non-LLM numbers (part-10 ref 03, part-09 ref 02, part-16 ref 01), zero
`CVPixelBuffer`/EXIF handling and the two box conventions (part-17 ref 05), swallowed diffusion
quantisation (part-09 ref 01 §17.2, part-10 ref 03), `BundleKind`/`SpeechBundle` (part-17 ref 06,
part-07 README). **What was asked for and does not exist: an owning guide for
`CoreAISegmentation`/`CoreAIObjectDetection`/`CoreAIDiffusion`** — part-07 ref 04 defers non-LLM
products to Part 16, and Part 16 covers only `CoreAISpeech` (§14). Source when written:
`notes/repos/coreai-models-nonllm.md`.

**Affects:** new guides needed in `part-07-coreai-swift-runtime/` and
`part-16-adjacent-capabilities/`.

The original proposal covered Core AI **only for LLMs**. `apple/coreai-models` ships four non-LLM
Swift products — `CoreAISegmentation`, `CoreAIObjectDetection`, `CoreAISpeech`, `CoreAIDiffusion` —
and its catalog is dominated by vision, audio and diffusion models. Details in
`notes/repos/coreai-models-nonllm.md`.

Notable, all ✅ verified against source:
- `Tools/benchmark` is actually **`llm-benchmark`** and imports `CoreAILanguageModels`. **There is
  no non-LLM benchmark tool**, and **no quality or latency number is published for any non-LLM
  model in the repo.**
- **Zero `CVPixelBuffer` handling and zero EXIF/orientation handling** in the entire non-LLM Swift
  tree. Image orientation is the caller's problem.
- `Segment.box` origin **flips on macOS**; `DetectedObject.boundingBox` does not. Two different box
  conventions coexist (XYXY vs cxcywh).
- Diffusion quantisation failures are **swallowed with a warning** (`export/compiler.py:69-72`).
  ⚠️ SILENT FAILURE.
- `BundleKind` = `{llm, vlm, diffusion, segmenter}` — no case for speech or detection, yet
  `SpeechBundle` requires an `encoder.aimodel` + `decoder.aimodel` split that **nothing in the repo
  produces**.

---

## ✅ C8 — Add three App Intents / Siri guides to Part 16

**Applied:** all three guides exist — part-16 refs `02-app-schema-domains.md`,
`03-onscreen-awareness.md`, `04-entities-spotlight-and-foundation-models.md` — and are listed in
`guides/README.md`. The transcript gap declared at the end of this item is also closed (see note
there).

**Affects:** `part-16-adjacent-capabilities/`.

Source: `notes/web/app-intents-siri-schemas.md` (1,652 lines). Verdict from the research pass was
three guides:

1. **App Schema Domains: the complete map** — all **23 domains in three tiers** (13 primary,
   2 single-purpose, 8 Shortcuts-only), ~177 intents / ~73 entities / ~50 enums. This enumeration
   **exists nowhere in one place, not even in Apple's own documentation.** Must state the absent
   categories plainly: fitness, health, finance, commerce, travel, food, transport, social,
   education, games. Cover `.system.searchInApp` as the one reachable Siri hook for uncovered app
   categories — it takes an unstructured string and works regardless of domain adoption or
   indexing. Fold in query protocols, `SnippetIntent` (iOS 26, not new), and the new execution
   model (`LongRunningIntent`, `ExecutionTargets`, `EntityCollection`, `@UnionValue`) as sections.
2. **On-screen awareness: making Siri understand "this"** — the two distinct paths (a
   screenshot/OCR path that **never calls `entities(for:)`**, versus true entity resolution), the
   four annotation shapes, and the verified working hand-off recipe: `@AppEntity(schema: .files.file)`
   + `FileEntityIdentifier.file(url:)` + **`FileRepresentation`** (not `DataRepresentation`).
   Plain custom `AppEntity` + `Transferable` never resolved. Caveat: needs a real file on disk.
3. **Entities, Spotlight, and Foundation Models: one index, three consumers** — the guide only we
   can write, because we already hold the `SpotlightSearchTool` notes. See C2.

**Cautions to carry into all three:** release-year labels are soft (the updates page and session
345 disagree; 345 says "2027 releases"), and `ValueRepresentation` vs `IntentValueRepresentation`
is an unresolved naming hazard. Apple's DTS engineer deflected the key architectural thread to
Feedback Assistant (FB23813341) **without answering**, and Apple's docs contradict the observed
behaviour by claiming "Schema application is optional but recommended" — say so.

~~🔴 GAP: WWDC26 sessions 240, 343, 344 and 345 are absent from our transcript corpus.~~
**RESOLVED** — the C10 recovery pass fetched all four (plus Tech Talk 111432); they live in
`transcripts/` and the three guides were written against them.

---

## ✅ C9 — Apple's own sample code corrects 66 items, several already written into Parts 1–2

**Applied** (spot-checked rows a–p): `Tool.name` "optional to implement" wording (part-02 ref 03),
the 5-case `LanguageModelError` list + "`SystemLanguageModel.Error` is tested first" (part-02
ref 06), the zero-partials silent failure (part-02 refs 01 §6.4 + 02), DynamicProfile-as-projection
anchoring part-03 ref 02, and the Part 6 rows (`ModelSubject`, `ToolCallEvaluator` +
`structuredTranscript`, hand-rolled Cohen's kappa in part-06 ref 03).

**Source:** `notes/web/apple-sample-code.md` (2,108 lines; §2 is a 66-row corrections table).
**Status of evidence:** these are ✅ VERIFIED against compiling Apple sample projects — the
strongest evidence class in the whole corpus. They **outrank** WWDC transcript reconstructions
everywhere they conflict.

**Samples obtained:** Origami (200 MB, 61 Swift files, iOS 27) · Book Tracker (56 MB, 20 Swift,
macOS 27) · "Searching indexed content with natural language" — the hiking-trails app (128 MB,
6 Swift, iOS 27).

⚠️ **Two samples are stale and must not be cited as 2026 evidence:** the coffee/generative-game
sample and the SpeechAnalyzer sample are **iOS 26 / WWDC25 leftovers, never refreshed**.
Grep-verified: **`DictationTranscriber`, `CaptureInputSequenceProvider`, `SFCustomLanguageModelData`
and the `datagenerator` CLI appear in NO sample.** Part 16's Speech guide must say so.
Also re-confirmed: **`coreai` has zero sample-code projects.**

### Corrections that invalidate text already written

| # | Affects | Was | Actually |
|---|---|---|---|
| a | Part 3 briefs, my orientation note | `some LanguageModelSession.DynamicProfile` | **`var body: some DynamicProfile`** — Apple uses the SHORT name in the body type. Conformance stays nested. My earlier "naming correction" was half wrong. |
| b | Part 3 | `Profile(model:) { … }` | **`Profile { … }.model(x)`** — a modifier, not an initialiser label |
| c | Part 3 | `historyTransform` signature UNVERIFIED | **`.historyTransform(f)`, `f: ([Transcript.Entry]) -> [Transcript.Entry]`** — a plain function reference works |
| d | Part 2 g1, Part 3 | — | **`LanguageModelSession(profile:history:)`** — the `history:` label taking a `Transcript` was missing from our notes entirely |
| e | **Part 2 g6 (errors)** | error case list uncertain | **`LanguageModelError` = `.timeout`, `.guardrailViolation`, `.refusal`, `.contextSizeExceeded`, `.unsupportedLanguageOrLocale`**, non-frozen. Confirmed by two independent archives. Critically: **`SystemLanguageModel.Error` is checked FIRST**, and `GeneratedContent.ParsingError` is separate. |
| f | **Part 2 g3 (tools)** | 🔴 GAP on `Tool.name` default | **`Tool.name` is OPTIONAL**, and **`Tool` has an `Output` associated type.** The GAP box can be closed. |
| g | **Part 2 g4 (Spotlight)** | much marked 🟡 | `SpotlightSearchTool(configuration: .init(sources: [.coreSpotlight(.init(searchableIndexDelegate:fetchAttributes:))], guide: .focused()/.complete))`. **No entitlement required.** Tool name is **`spotlight_search`**. `tool.searchResults` is an `AsyncSequence` whose `.content` is a **7-case non-frozen** enum. Most of guide 2.4's 🟡 markers can be upgraded. |
| h | Part 2 g5 (images) | attachment API 🟡 | **`Attachment(image).label(id)`** → `@Generable var image: ImageReference` → **`.attachmentLabel`**. Fully worked round-trip exists. |
| i | Part 2 g1 | — | `Transcript.Response(assetIDs:segments:)` — **`assetIDs` is required**, sample passes `[""]`. `Transcript` is `Encodable`. |
| j | Part 6 (Evaluations) | — | **`ModelSubject<T>`** (`init(value:)`, `init(value:transcript:)`) is the return type of `subject(from:)` — absent from our symbol list. `Evaluator { input, subject in … }` is **2-arg**, collected in `var evaluators: Evaluators`. Metric factories: `.passing()`, `.failing()`, `.scoring(_:)`, each optionally with `rationale:`. |
| k | Part 6 | — | `ModelJudgePrompt(instructions:evaluationTarget:reference:)` — **`reference` returns `[String: String]`**, not a string. |
| l | Part 6 | — | `ToolCallEvaluator(allPass:percentagePass:)` requires **`session.transcript.structuredTranscript`**; the call-site type is **`ToolExpectation`**; 7 matchers including **`.naturalLanguage(argumentName:criteria:)`**. |
| m | Part 6 | implied framework support | **Cohen's kappa is hand-rolled in the sample, NOT provided by the framework.** Session 335 does not say otherwise, but a reader would assume it ships. |
| n | Part 2 g1/g6 | — | `SystemLanguageModel()` bare init is 2026 house style. `SystemLanguageModel(guardrails: .permissiveContentTransformations)` **appears in a sample** — previously known only from a forum post. |
| o | Part 2 g1, g2 | — | ⚠️ **SILENT FAILURE:** a stream can finish yielding **zero partials** when the model emits only a tool call (`CoachModel.swift:67-72`). Any "spinner until first token" UI hangs forever. This is a real, subtle bug class and deserves a callout in the streaming guide. |
| p | Part 1 g2, Part 2 g6 | proactive gating advised | The **2026 samples dropped proactive `availability` gating** in favour of reactive `SystemLanguageModel.Error` catching; the stale iOS 26 game still gates. Guides should teach **both**, and say which Apple's current samples actually do. |

### Five patterns worth reproducing verbatim in guides
1. **DynamicProfile as a projection of an `@Observable` state machine** — mutating `state.mode` *is*
   the agent handoff; the transcript stays intact. This is a much cleaner framing than the
   transcript's "swapping hats" and should anchor the Part 3 profiles guide.
2. **Labelled attachments + `ImageReference`** for multi-image analysis keyed back to app objects.
3. **Book Tracker's full ladder**: `#Playground` → heuristics → model judge → `SampleGenerator` →
   **κ-calibration of the judge** → `.evaluates(info:)` for diffable runs, with `DatasetExtractor`
   as the human-scoring link. This is the spine of Part 6.
4. **Tool-as-consent-request** — `MovePhotoToStepTool` → Yes/No UI → synthesized follow-up turn.
5. **Two-channel results** — prose from the model, real `CSSearchableItem`s from the tool's side
   channel. Anchors Part 2 guide 4.

### Reusable discovery recipe (worth documenting in the research index)
`developer.apple.com/tutorials/data/index/<framework>` → filter `type == "sampleCode"`; then
`…/tutorials/data/documentation/<framework>/<slug>.json` → grep for the `docs-assets…zip` URL.
**sosumi.ai does not expose sample ZIPs** — use the tutorials JSON API instead.

---

## ✅ C10 — Seven recovered transcripts resolve three long-standing gaps and add one silent failure

**Applied** (all sub-items): C10.1 in part-02 refs 03 §10 + 05 (watchOS asymmetry kept un-smoothed);
C10.2's required-label callout in both refs 03 and 05; C10.3 in part-16 ref 04 §11.4; C10.4 in
part-12 ref 05 §§16–19 + 24 (with the global `--batch-size` named as a silent failure); C10.5 in
part-11 (see the superseded note on C3); C10.6 in part-16 ref 02 §14.1.

**Source:** `notes/transcripts/missing-sessions.md` (3,216 lines) plus seven new raw transcripts in
`transcripts/`: `wwdc2026-{233,237,240,343,344,345}.txt` and `tech-talks-111432.txt`.

⚠️ **Technique correction for all future research** — `WebFetch` on
`developer.apple.com/videos/play/...` **works directly** and returns the transcript *plus* Apple's
published code-sample blocks. No mirror needed. Only `/documentation/` paths require `sosumi.ai`.
Unknown session numbers are found fastest by fetching the **Related Videos** block of a session that
cites the one you want — that is how Tech Talk 111432 was located, and WebSearch did not find it.

### C10.1 — `BarcodeReaderTool` / `OCRTool`: 🔴 GAP → 🟡 PARTIAL
**Affects:** `part-02-…/references/03-tools-and-tool-calling.md` (has an open GAP on these),
`…/05-image-input-and-attachments.md`.

✅ VERIFIED: both are **`struct`s in the Vision framework** (not FoundationModels), conforming to
`Sendable, SendableMetatype, FoundationModels.Tool`. Both:
`init(name: String? = nil, description: String? = nil)`.
Availability **iOS / iPadOS / macOS / visionOS 27.0+ Beta**.
⚠️ **`BarcodeReaderTool` also lists watchOS; `OCRTool` does not** — a verified difference with an
unverified cause. Do not smooth it over.
Outputs (Apple prose only, not a published signature): barcode → an **array of `Barcode`** carrying
decoded content plus symbology; OCR → a **`String`**, 30+ languages.
~~🔴 Still a genuine GAP: the `Arguments` / `Output` associated types and the `Barcode` type are
not published. Resolving needs an SDK interface dump.~~ **RESOLVED 2026-07-29** — the captured
`_Vision_FoundationModels` cross-import overlay answers it (`Output` is a deliberately unnameable
opaque `some PromptRepresentable`); cited in part-02 ref 03 §10.

### C10.2 — ⚠️ NEW SILENT FAILURE: image tool calls require an attachment label
**Affects:** guides 2.3 and 2.5, **both already written and already corrected once.**

`Attachment(image).label("flyer")` is **REQUIRED** for image tool calls, and **silently no-ops if
omitted.** This is exactly the class of defect the series exists to document, and it is not in
either guide yet. Needs a callout in both.

### C10.3 — `.system.searchInApp` is a RENAME, not a new schema
**Affects:** the Part 16 App Intents guides (since written; see C8).

Confirmed twice on session 343's page (transcript + Apple code sample), verbatim: *"The `.system`
search schema introduced in iOS 17 is now named `.system.searchInApp`."* It takes
`var criteria: StringSearchCriteria` (`.term`), and `StringSearchCriteria` is an **iOS 17.2** type —
which independently corroborates that this is a rename. It works regardless of domain adoption or
indexing. The UNVERIFIED flag at `notes/web/app-intents-siri-schemas.md:858` can be downgraded.

### C10.4 — MLX distributed: RESOLVED IN FULL
**Affects:** `part-12-mlx-python/` (the serving/distributed guide), Part 1's decision material.

✅ `mlx.launch --hostfile <f> -- /remote/path/to/<exe> <args>`. The hostfile is a **JSON array of
`{ssh, ips[], rdma[]}`**, where `rdma` is a **positional adjacency matrix with `null` on the
diagonal**. Config tool: `mlx.distributed_config --hosts --output --env MLX_METAL_FAST_SYNCH=1
--auto-setup --backend jaccl|jaccl-ring`.
**RDMA over Thunderbolt 5 requires macOS 26.2**, a System Settings toggle, and a reboot.
Mesh is strictly better than ring — JACCL routes ring-over-mesh automatically.
Measured on **4× M3 Ultra** (attribute to Apple, from the session): **~3× decode** on Qwen 3.6 27B;
fine-tuning **180 → 600 tok/s** on Qwen 3.5 9B; and 1T-parameter Kimi 2.6 (~1 TB at 8-bit) fits
across four machines.
⚠️ **`--batch-size` is GLOBAL and must be scaled by N.** Easy to get silently wrong.

### C10.5 — TensorOps: restate the version story; scale-plane non-existence is now SETTLED
**Affects:** `part-11-metal-and-tensorops/` (since written). **This supersedes C3's version bullet.**

Tech Talk 111432 gives an explicit per-point-release ladder:
**26.0** intro (WWDC25 session 262) · **26.1** bfloat · **26.3** cooperative tensors as matmul
*inputs* · **26.4** int4/int8. **26.2 is never mentioned.**

→ **Do not write a blanket "26.2".** Write the ladder, and add that the shipped 26.6 SDK headers
annotate the symbol as 26.2. Both facts are true and they are about different things.

The int4/int8-only dtype set **matches the header finding exactly** (no int2, fp4 or fp8).

**Scale planes: promote from "not found" to SETTLED NON-EXISTENCE.** This is a third independent
source, and it does better than absence — it names what shipped *instead*: **in-kernel custom
dequantisation into a cooperative tensor**, which is precisely the MLX pattern we already
documented. The guide can now teach the real technique rather than merely reporting a void.

Citable bonus number (Apple-published): the SIMD-group-matrix path shows **0% neural-accelerator
utilisation** on M5, and a 4K×4K matmul goes **2 s → 0.5 s → 0.33 s** across kernel versions v1/v2/v3.

### C10.6 — `IntentParameter.valueState` (the incidental find worth a callout)
**Affects:** Part 16 App Intents guides.

From session 344: `.set(value)` / `.set(nil)` / `.unset` distinguishes **"change it"** from
**"clear it"** from **"don't touch it"**. ⚠️ Every `if let` in an update-style intent silently
conflates the last two. Deserves its own callout box.

---

## ✅ C11 — TN3193 read: the context-window conflict is SETTLED at 4096

**Applied:** part-03 ref 01 §3.3 ("settled by TN3193") + §2.6 (the six mitigations); part-17 ref 03
§5 (the coexistence wrinkle) + §12.5; part-02 ref 06 catches both spellings. Residual stale
presentations of the conflict as open (part-03 README, part-04 ref 01) were fixed 2026-07-31.

**Affects:** `part-03-…/references/01-context-window-and-kv-cache.md` (which declared this an open
gap and correctly flagged that TN3193 had never been read), `part-02-…/references/06-availability-
errors-and-guardrails.md`, `part-17-…/references/03-error-taxonomy-migration.md`.

**Source:** Apple Technical Note **TN3193 — "Managing the on-device foundation model's context
window"**, fetched 2026-07-27 via
`https://sosumi.ai/documentation/technotes/tn3193-managing-the-on-device-foundation-model-s-context-window`
(note the slug: `model-s`, not `models`; the `models` spelling 404s).

### The settled facts
- ✅ **4096 tokens per `LanguageModelSession`.** Apple states it plainly. The 8192 figure — a
  third-party app's source comment claiming device probing returns it — is **not corroborated by
  Apple** and should be demoted to a footnote, not presented as an equal-weight conflict.
  Keep the standing advice to read `contextSize` at runtime rather than hardcoding either number.
- ✅ `contextSize` and `tokenCount(for:)` arrived in **iOS 26.4**. TN3193 confirms `tokenCount(for:)`
  covers **instructions, prompts, tools, schemas and transcript entries** — which corroborates the
  multi-overload story our guide marked 🟡 RECONSTRUCTED. The individual Swift signatures are still
  unpublished, so keep the markers on the signatures while upgrading the *existence* claim.

### ⚠️ The error-taxonomy wrinkle — important for Part 17
TN3193 names the overflow error as:
**`LanguageModelSession.GenerationError.exceededContextWindowSize(_:)`**

Note it is `GenerationError`, **nested under `LanguageModelSession`** — while Apple's 2026 sample
code shows **`LanguageModelError.contextSizeExceeded`**. So the two taxonomies **coexist**: this is
direct evidence for the 26 → 27 migration story rather than a contradiction. Part 17's
error-taxonomy guide should cite both spellings side by side as the before/after pair, and Part 2's
failure-taxonomy guide should catch both.

### Apple's six recommended mitigations (use these verbatim as the guide's structure)
1. **Split tasks across multiple sessions** — smaller steps, a new session each, combine results.
2. **Request less content** — put the target length in the prompt ("In 3 sentences…") and use
   `Guide(description:)` with `maximumCount(_:)`.
3. **Reduce prompt size** — concise language; 1–3 paragraphs maximum.
4. **Use `Generable` types efficiently** — minimise type complexity, short property names, apply
   `@Guide` sparingly. (Every guide costs context.)
5. **Optimise tool calling** — brief descriptions, **limit to 3–5 tools**, and consider running
   tools *before* calling the model.
6. **Implement RAG** — fetch relevant snippets dynamically instead of passing a whole knowledge base.
   Cross-link to the `SpotlightSearchTool` guide.

Recovery pattern Apple documents: catch the error, create a **new** session, and optionally preserve
context by summarising the old `transcript` or by selecting important entries from it to seed the
new session. TN3193 ships a code example using the **first and last** transcript entries.

🔴 **Remaining GAP:** TN3193 says nothing about KV-cache behaviour or transcript-trimming APIs, so
everything the guides say about cache invalidation still rests on session 242 plus the
`foundation-models-utilities` source. Do not upgrade those markers on the strength of this note.

---

## ✅ C12 — The 26.5 FoundationModels .swiftinterface was on this machine all along

**Applied** — and the "apply after the 27 interface is read" precondition at the end of this item
was met on 2026-07-29 (both interface sets captured): the nine-case `GenerationError` ↔
`LanguageModelError` mapping (part-17 ref 03 §§3–5), `Tool` protocol requirements +
`includesSchemaInInstructions` (part-02 ref 03 §4.4, default `true` probe-verified 2026-07-31),
five `tokenCount(for:)` overloads (part-03 ref 01), and the negative-evidence version floors.

**Source:** `notes/sdk-interfaces/FoundationModels-26.5-macos.swiftinterface` (copied verbatim from
MacOSX26.5.sdk; module version 1.5.2, Swift 6.3.2, `-target arm64e-apple-macos26.5`) and the
extracted-declarations file beside it. This is **compiler-emitted API text = the cleanest evidence
class that exists**, above sample code. It covers the **26.x surface** — the framework shipped in
26.0 and this machine is 26.5. Everything below is ✅ VERIFIED for 26.5.

⚠️ **Scope discipline for whoever applies this:** the guides target **27**. The 26 surface is a
subset of 27, so for structural APIs (sessions, prompting, tools, guided generation) the 26.5
interface is strong evidence they exist in 27 too — mark them "✅ verified in 26.5 SDK; stable in 27
unless noted". BUT the error namespace is NOT stable (see below), so do not blanket-apply.

### The migration is now provable from the SDK (Part 17 guide 03, Part 2.6)
- 26.5 has **`LanguageModelSession.GenerationError`** with **nine** cases:
  `exceededContextWindowSize`, `assetsUnavailable`, `guardrailViolation`, `unsupportedGuide`,
  `unsupportedLanguageOrLocale`, `decodingFailure`, `rateLimited`, `concurrentRequests`,
  `refusal(Refusal, Context)`. Each non-refusal case carries a `Context` (with `explanation` and
  `explanationStream`).
- `LanguageModelError` is **absent** (grep 0). So the 27 sample-code case list
  (`.timeout/.contextSizeExceeded/...`) is the *rename target*. The before→after mapping is now
  exact: e.g. 26.5 `.exceededContextWindowSize` → 27 `.contextSizeExceeded`; several 26.5 cases
  (`assetsUnavailable`, `unsupportedGuide`, `decodingFailure`, `concurrentRequests`) have no
  confirmed 27 counterpart — call that out.

### Gaps to CLOSE with ✅ (26.x surface)
- **`Tool` is `public protocol Tool<Arguments, Output> : Sendable`**, with
  `associatedtype Output : PromptRepresentable`, `associatedtype Arguments :
  ConvertibleFromGeneratedContent`, and requirements `var name: String { get }`,
  `var description: String { get }`, `var includesSchemaInInstructions: Bool { get }`.
  ⚠️ Reconciles the sample-code "name is optional" finding: the protocol requirement is
  `name: String` (non-optional TYPE) but there is a default implementation (line 821), so it is
  *optional to implement*, not an `Optional`. Fix guide 2.3's wording to say exactly that. And
  `includesSchemaInInstructions` is a real protocol requirement — closes that gap too.
- **`tokenCount(for:)` has FIVE overloads** (all `async throws -> Int`): `some PromptRepresentable`,
  `Instructions`, `[any Tool]`, `GenerationSchema`, `some Collection<Transcript.Entry>`. Closes the
  Part 3.1 gap that had four of these as 🟡. Corroborates TN3193.
- **`respond`/`streamResponse`: 18 overloads.** Notably a **direct `@_disfavoredOverload
  respond(to prompt: String, ...)`** exists — so a bare String is a real overload, not just
  PromptRepresentable conformance (closes a Part 2.1 gap). The full `schema:`/`generating:` families
  are present with `includeSchemaInPrompt: Bool = true`.
- **Four `LanguageModelSession` inits**, all `model: SystemLanguageModel = .default` — so in 26.5
  `model:` is concretely typed `SystemLanguageModel`, NOT generic. (The 27 generic-over-`LanguageModel`
  overload is the addition; keep that 🟡 until the 27 interface is read.)
- **`SystemLanguageModel.Availability`** (`@frozen`): `.available` / `.unavailable(UnavailableReason)`;
  **`UnavailableReason`**: `deviceNotEligible`, `appleIntelligenceNotEnabled`, `modelNotReady`.
  Closes the Part 1.2 / 2.6 UnavailableReason gap.
- **`init(useCase:guardrails:)`** and **`init(adapter:guardrails:)`** exist — confirms the
  `guardrails:` init the guides had only from a forum post, and confirms `Adapter` is a 26.x type
  (relevant to Part 17's adapter-sunset framing).
- **`GenerationOptions`**: `sampling: SamplingMode?`, `temperature: Double?`,
  `maximumResponseTokens: Int?`. ⚠️ **No `toolCallingMode` in 26.5** — confirms it is a 27 addition
  (validates the version-floor claim). `SamplingMode.random(top k:seed:)` and
  `random(probabilityThreshold:seed:)` are the verified factory spellings.
- Full public type list captured (44 types incl. `Adapter`, `Refusal`, `ResponseStream`,
  `Snapshot`, `StructuredSegment`, `Transcript`, `UseCase`).

### Negative evidence (validates version-floor tables) — all grep-0 in 26.5
`LanguageModelExecutor`, `PrivateCloudComputeLanguageModel`, `DynamicProfile`, `ContextOptions`,
`QuotaUsage`, `LanguageModelError`. And **Vision 26.5 has 0 hits for `BarcodeReaderTool`/`OCRTool`** —
confirming those are 27-only, matching the transcript pass.

### Apply when? ~~AFTER the running Part-17+sweep workflow finishes (it edits 2.3/2.5/3.1), as ONE
consolidated SDK pass — ideally together with the 27 interface once Xcode 27 is installed.~~
**Done** — the sweep finished, both interface sets were captured 2026-07-29, and the consolidated
pass landed (see the Applied note at the top of this item).
