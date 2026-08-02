# Proposed guide series — organized BY FRAMEWORK / TECHNOLOGY

> **Status 2026-08-01:** historical input to the merged proposal. Its 2026-07-27 counts and open
> questions are intentionally frozen; use the current `guides/` tree and operational notes for
> completion state.

**Lens:** a reader already knows *which* framework they need (Foundation Models, Core AI Swift
runtime, Core AI Python toolchain, MLX Python, MLX Swift, Evaluations, Speech, or a bridge between
them) and wants total depth on it.

**Written:** 2026-07-27, synthesizing a 28-agent sweep plus the lead agent's own reading of
`docs/`, 14 WWDC26 transcripts, and repo spot-checks.

**Count:** 55 topics across 16 pillars.

---

## Landscape summary

The 2026 stack is four product lines that stopped being alternatives and became **layers**.

**Foundation Models (Swift)** is no longer "the API for Apple's on-device LLM". At WWDC26 it became
a *general LLM client abstraction*: `LanguageModelSession` now sits on top of a public
`LanguageModel` protocol, and Apple ships or blesses at least five conformers —
`SystemLanguageModel` (rebuilt on-device model, ~4K context, now with vision),
`PrivateCloudComputeLanguageModel` (32K context, three reasoning levels, no API keys, per-user
daily quota), `CoreAILanguageModel` (your own `.aimodel` on ANE/GPU),
`MLXLanguageModel` (anything on Hugging Face via `mlx-swift-lm`), and
`ChatCompletionsLanguageModel` (any OpenAI-compatible endpoint — which quietly makes
`mlx_lm.server`, Ollama, vLLM and LM Studio into Foundation Models backends today). The framework
core is going open source and is claimed to run "everywhere Swift runs, including Linux servers".
That single protocol is the structural spine of the whole corpus, and it reframes "which framework
do I choose" into "which backend do I choose behind one session API".

The 2026 additions to the framework itself cluster into three areas. **Agentics:** Dynamic
Profiles — a SwiftUI-shaped DSL (`DynamicInstructions` → `Profile` →
`LanguageModelSession.DynamicProfile`) whose `body` is re-evaluated before every request, with
~14 modifiers, lifecycle hooks (`onPrompt`/`onResponse`/`onToolCall`), `historyTransform`,
`@SessionPropertyEntry` shared state, and a now-**mutable** `session.transcript`. **Context
engineering:** an explicit KV-cache contract (instructions → tool definitions → transcript; a change
at position N invalidates everything after N), plus a separately-versioned
`apple/foundation-models-utilities` package shipping `summarizeHistory`/`rollingWindow`/
`droppingCompletedToolCalls` and a `Skills` API whose prompt-vs-instructions storage choice *is* the
KV-cache tradeoff made concrete. **Reliability:** a rewritten error taxonomy (`LanguageModelError`
supersedes the deprecated `GenerationError`, and rebuilding with Xcode 27 silently changes which
`catch` fires), a first-class `Evaluations` framework, and a Foundation Models Instruments template.

**Core AI** is the inference framework that powers on-device Apple Intelligence, now public and
explicitly the successor path for *neural networks* while Core ML retains trees/tabular. Its shape:
a portable `.aimodel` source bundle → **specialization** (device + OS-version specific, expensive,
cached) → `AIModel` → `InferenceFunction` → `NDArray`. Everything downstream of that is where the
real difficulty lives: a non-escapable `View`/`MutableView` memory model built on Span and value
generics, `InterleaveLayout` block strides, `preferredStrides` to avoid hidden layout copies,
**states** (read-and-written-in-place tensors — i.e. KV caches), pipelined `encode(...)` into a
`ComputeStream`, an `AIModelCache` keyed on (URL, SpecializationOptions) with bookmark and
app-group escape hatches, and AOT compilation via `xcrun coreai-build` producing one `.aimodelc`
per device architecture (iOS effectively *requires* this — it cannot JIT). The Python side is three
separate packages: `coreai-torch` (torch.export → Core AI IR, with composite ops, externalization,
custom lowerings and `TorchMetalKernel`), `coreai-opt` (quantization, k-means palettization,
pruning, casting, joint compression), and `coreai-core` (runtime + direct graph authoring).
`apple/coreai-models` adds a 22-model catalog, five Swift runtime products, and — uniquely — three
**agent skills** containing Apple's own empirical ANE/GPU authoring rules and PSNR acceptance gates.

**MLX** is the open array framework for Apple silicon: unified memory with per-op stream placement,
lazy evaluation, `mx.compile`, four quantization modes (affine/mxfp4/mxfp8/nvfp4), custom Metal and
CUDA kernels, and a new RDMA-over-Thunderbolt distributed backend (JACCL). `mlx-lm` is the LLM
layer (18 CLIs, ten KV-cache classes, continuous-batching OpenAI-compatible server, LoRA/DoRA, and
four learned-quantization methods); `mlx-swift-lm` is the Swift port that also hosts
`MLXFoundationModels` — the best readable implementation of the `LanguageModel` protocol in
existence — and `MLXGuidedGeneration` (xgrammar). Notably, **both** Apple's `coreai-models` and
`mlx-swift-lm` independently reach for xgrammar to enforce `@Generable` on non-Apple models.

**Evaluations** (Xcode 27, Swift-only) cuts across everything: an `Evaluation` protocol on Swift
Testing, code-based and model-judge evaluators, `TrajectoryExpectation` for tool-call paths,
`SampleGenerator` for synthetic datasets, and — the most sophisticated content in the corpus —
judge *drift* measured with Cohen's kappa against a 0.6 threshold. Apple positions it as the only
defense against silent behavior change across OS updates, since there is **no model version pinning
API**.

**Speech** changed least: the `SpeechAnalyzer` module pipeline from iOS 26 is intact, with 2026
adding only input-plumbing conveniences (`AssetInputSequenceProvider`,
`CaptureInputSequenceProvider`, `AnalyzerInputConverter`). Its hard parts are asset lifecycle,
finish-state semantics, and the no-audio-conversion contract.

Underneath all of it, **Metal Performance Primitives / TensorOps** exposes matmul and convolution in
MSL with automatic use of the M5 neural accelerator, plus cooperative tensors and MX-format scale
planes — the layer both Core AI and MLX sit on and the layer you drop to for a fused FlashAttention.

Cross-cutting realities the guides must carry throughout: OS/SDK gating is *everywhere*
(26.0 vs 26.4 vs 27.0, Xcode 26 vs 27, `canImport(FoundationModels, _version: 2)`,
`coreai-core >= 1.0.0b2`); on-device memory and jetsam are the dominant shipping constraint;
and specialization/caching/distribution is the unglamorous work that decides whether a feature
launches in 300 ms or 30 s.

---

## Pillars

| Pillar | Rationale |
|---|---|
| **Cross-stack orientation & versioning** | Nothing else is safe to read first. The backend-selection question changed shape in 2026, and every API in the corpus is gated on some combination of OS, SDK, Xcode, and package version. |
| **Foundation Models — core session & generation** | The everyday Swift API surface: sessions, prompting, guided generation, streaming, tools, images. This is where most readers start and where the largest volume of verified evidence sits. |
| **Foundation Models — context engineering & agentics** | The flagship 2026 additions (dynamic profiles, mutable transcripts, KV-cache economics, Skills). Structurally separate because it assumes the core API and has its own failure modes (silent quality loss, infinite tool loops). |
| **Foundation Models — providers & backends** | The `LanguageModel`/`LanguageModelExecutor` protocol pair and the concrete backends (PCC, OpenAI-compatible, third-party). A different audience: package authors, not app authors. |
| **Foundation Models — tooling outside Swift** | `fm` CLI, Python SDK, `#Playground`, Instruments. Non-Swift access paths and the observability story for a non-deterministic runtime. |
| **Core AI — Swift runtime** | Loading, specializing, caching, running, and profiling `.aimodel` assets on device. Dense, low-level, and the place first-launch latency and memory bugs originate. |
| **Core AI — Python toolchain** | `coreai-torch`, `coreai-opt`, `coreai-core`: converting and compressing a PyTorch model into a shippable asset. Separate audience (ML engineers) and separate language. |
| **Core AI — model authoring & LLM deployment** | Empirical hardware rules (ANE vs GPU) and the end-to-end LLM export/bundle/engine story. This is where Apple's own agent skills and the community zoo hold knowledge that exists nowhere else. |
| **Metal / TensorOps** | The kernel layer both Core AI and MLX sit on: matmul2d, quantized tensors with MX scale planes, cooperative tensors, fused FlashAttention. |
| **Evaluations framework** | A whole Swift framework with almost no public documentation; the only sanctioned regression gate against model drift. |
| **MLX — Python** | The array framework and `mlx-lm`: research, conversion, quantization, serving, and fine-tuning on Apple silicon. |
| **MLX — Swift** | `mlx-swift-lm`: the same models inside an app, plus the bridge that makes an MLX model back a `LanguageModelSession`. |
| **Bridges between stacks** | The third-party toolchains that target Core AI from outside — `mlx2coreai` and `swift-lm`. The only public non-Apple descriptions of Core AI's IR and bundle contracts. |
| **Speech** | Small, self-contained, and mostly unchanged in 2026 — but with several sharp, undocumented failure modes. |
| **Shipping & operating on device** | Distribution, updates, memory, thermals, benchmarking. Framework-agnostic but unavoidable, and the single largest source of shipped-app bugs in the forum corpus. |
| **Data & model quality (adjacent)** | DNIKit — the pre-conversion dataset/model introspection tool. Dormant but real, and the only thing in the corpus that addresses dataset quality. |

---

## Topics

### Pillar: Cross-stack orientation & versioning

#### `apple-ai-stack-2026-map`
**The 2026 Apple AI stack: Foundation Models, Core AI, MLX, Core ML, and how to choose a model backend**
*Audience: both · ~6000 words · evidence: strong*

Maps the four product lines and — crucially — explains that Core AI and MLX are now *backends* for
Foundation Models rather than competitors, via the `LanguageModel` protocol. Provides a decision
framework across capability, context size, privacy, offline behavior, quota economics, memory, and
distribution. Includes Apple's explicit routing of non-neural-network models to Core ML and the
WWDC26 lab direction signal.

Sections: the four layers, one diagram · what changed at WWDC26 · the `LanguageModel` protocol as
the spine · SystemLanguageModel vs PCC (4K/32K, offline/online, unlimited/quota, no-reasoning/three
levels) · Core AI: when a custom model beats the system model · MLX: research vs shipping · Core ML
in 2026: trees, tabular, and the narrowing scope · the ANE-access argument and what it's worth ·
measured performance reality (Core AI ~2.5× MLX at 0.6B collapsing to ~1.05× at 8B; MoE inversion) ·
sustained vs burst throughput and joules-per-token · a decision table by feature type ·
privacy-disclosure obligations when you ship someone else's model

Sources: `transcripts/fm-core.md`, `transcripts/fm-ecosystem.md`, `transcripts/coreai-intro.md`,
`web/apple-docs-coreai.md`, `web/community-blogs.md`, `00-ORIENTATION-lead-agent.md`

---

#### `os-sdk-versioning-and-migration`
**Version gating across the 2026 stack: OS, SDK, Xcode, and the iOS 26 → 27 Foundation Models migration**
*Audience: both · ~5500 words · evidence: strong*

One reference for every version gate in the corpus plus a concrete migration checklist. Covers the
26.0/26.4/27.0 split, `@backDeployed`, `canImport(FoundationModels, _version: 2)` (the only reliable
27-SDK test), the deprecated `GenerationError` and its binary-compatibility trap, new enum cases
that break exhaustive switches, and the package-level floors (`coreai-core >= 1.0.0b2`,
`coreai-torch 0.4.1`, `mlx >= 0.31.2`, mlx-swift-lm 3.x breaking changes).

Sections: the decoder ring table · what shipped in 26.0 vs 26.4 vs 27.0 · Xcode 26 vs Xcode 27 and
why rebuilding changes runtime behavior · SDK-conditional compilation patterns that actually work ·
`GenerationError` → `LanguageModelError`/`LanguageModelSession.Error`/`SystemLanguageModel.Error`
case-by-case mapping · new `Transcript.Entry.reasoning` and `Segment.attachment` cases · the three
on-device model generations and re-testing prompts · Core AI asset version floors and the
`Failed to convert to versioned IR` signature · `strip_debug_info` as the pre-0.4.1 rescue ·
Metal Toolchain as a build prerequisite · the simulator-punches-out-to-host trap · a migration
checklist

Sources: `web/apple-docs-fm-evals-speech.md`, `repos/issues-coreai-stack.md`,
`repos/mlx-swift-lm.md`, `forums/forum-pain-points.md`, `repos/issues-community-stack.md`

---

### Pillar: Foundation Models — core session & generation

#### `fm-session-lifecycle-and-prompting`
**LanguageModelSession end to end: initializers, instructions vs prompts, prewarming, and concurrency**
*Audience: Swift app dev · ~5000 words · evidence: strong*

The session object itself, and the security model that governs what goes in instructions vs
prompts. Covers all initializer forms including the 2026 `init(profile:history:)`, the 24
respond/streamResponse overloads, `isResponding` and `concurrentRequests`, `prewarm()` /
`prewarm(promptPrefix:)` with the measured ~700 ms win, and the result-builder APIs.

Sections: creating a session (six init forms, and which are generic over `some LanguageModel`) ·
`Instructions` vs `Prompt`: authorship, ordering, and prompt-injection defense · `InstructionsBuilder`
and `PromptBuilder` (conditionals, loops, embedding a `@Generable` instance) · one-shot prompting
with a fully-populated Generable and the structure-vs-style division of labor · `respond` overload
map · prewarming: what it loads, when to call it, why it is fire-and-forget · `isResponding` and the
one-request-at-a-time rule · session reuse vs recreation · why streaming in the background raises
rate-limit risk · prompt-length findings (Apple's own study: the *most* detailed prompt had the
highest generation-error rate) · supported vs "avoid" capabilities of the on-device model ·
multilingual prompting, including Generable property names as model input

Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`, `transcripts/fm-advanced.md`

---

#### `fm-guided-generation`
**Guided generation: @Generable, @Guide, dynamic schemas, GeneratedContent, and the constraints that don't work**
*Audience: Swift app dev · ~7000 words · evidence: strong*

The complete structured-output story, including the constraint mechanisms that Apple has confirmed
broken. Covers macro-based `@Generable`, the full `GenerationGuide` catalogue, runtime
`DynamicGenerationSchema`, raw `GenerationSchema`/`GeneratedContent`, sampling settings that affect
classification accuracy, and `includeSchemaInPrompt` token economics.

Sections: `@Generable` on structs and enums; composability and top-down constrained decoding ·
`@Guide` forms and the full guide catalogue (pattern, count, range, anyOf, constant, element,
min/max) · which guide is legal on which type · enum-vs-`.anyOf` decision table · ⚠️ the confirmed
`.anyOf` bug: Apple reproduced it, the model still generates out-of-set values; two workarounds ·
why guided generation lets you *delete* prompt text · `includeSchemaInPrompt: false` — and the exact
precondition that makes it safe · `DynamicGenerationSchema`, references, `anyOf`, and
`GenerationSchema(root:dependencies:)` · `GeneratedContent.Kind`, JSON round-tripping, and the
FoundationModels JSON-Schema dialect (`title`, `x-order`, `$defs`, `$ref: "#"`) · `GenerationID` and
stable identity while streaming · greedy sampling for classification enums · guardrails always run
on guided generation, even under permissive settings · failure modes: decoding failures, unsupported
guides, schema-beats-prompt behavior

Depends on: `fm-session-lifecycle-and-prompting`
Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/python-apple-fm-sdk.md`, `forums/forum-pain-points.md`

---

#### `fm-streaming-partially-generated`
**Snapshot streaming: PartiallyGenerated types and real-time SwiftUI**
*Audience: Swift app dev · ~4000 words · evidence: strong*

Why `streamResponse` is not `async`, why every element is a full snapshot rather than a delta, and
how to build UI against a mirror type where every property — at every nesting level — is optional.

Sections: `streamResponse` signature and the not-async gotcha · what `T.PartiallyGenerated` is and
how the macro synthesizes it through the whole type graph · snapshots vs deltas and why Apple chose
snapshots · the mandatory if-let unwrapping pattern and how to avoid writing it by hand · SwiftUI
patterns: stable identity with `GenerationID`, animation, throttling · streaming with tools in the
loop · `ResponseStream.Snapshot`: `content`, `transcriptEntries`, `usage` · reasoning tokens
arriving before readable transcript entries · early-break semantics and cancellation · when *not*
to stream (background work, rate limits) · testing streamed output

Depends on: `fm-guided-generation`
Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`, `repos/noema-ios.md`

---

#### `fm-tools-and-tool-calling`
**Building tools: the Tool protocol, the arguments contract, tool-calling modes, and escaping the required-mode loop**
*Audience: Swift app dev · ~6000 words · evidence: strong*

Everything about giving the model callable code. Includes the six-entry transcript anatomy of a
tool-using turn, why a tool won't be invoked from its description alone, and the documented
infinite-loop footgun in `.required` mode.

Sections: the `Tool` protocol: name, description, `Arguments`, `call(arguments:)` · the Arguments
struct as "the contract between the tool and the model" · runtime-built schemas via
`GenerationSchema` — and the once-computed-at-session-init trap · transcript anatomy of a tool turn
(6 entries, one `toolCalls` entry holding N calls) · why you must *also* instruct the model to call
the tool · greedy sampling for deterministic tool-call tests · `GenerationOptions.ToolCallingMode`
and the profile-modifier form: `.allowed` / `.disallowed` / `.required` · ⚠️ `.required` is an
unbounded while loop — the two sanctioned exits (state-conditioned mode, throwing final-answer tool)
with a compiled reference implementation · `onToolCall` as a security chokepoint, and why throwing
there aborts the whole turn · tool errors, retry loops, and validating arguments you can't constrain ·
tool-spec ordering as a KV-cache-prefix concern · adding or removing tools mid-session

Depends on: `fm-guided-generation`
Sources: `transcripts/fm-core.md`, `transcripts/fm-advanced.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/noema-ios.md`, `forums/forum-pain-points.md`

---

#### `fm-spotlight-rag-and-system-tools`
**Local RAG with SpotlightSearchTool, plus OCRTool and BarcodeReaderTool**
*Audience: Swift app dev · ~6500 words · evidence: strong*

The built-in system tools, dominated by Spotlight-backed retrieval. Includes the configuration
surface, the token-budget consequences of guidance level, and the failure mode that will burn most
adopters: the index returns titles, not bodies.

Sections: the three built-in tools and what each is for · `SpotlightSearchTool.Configuration`:
sources, `Guide(level:format:)`, `contactResolver`, `customStages` · the cross-import overlay — the
tool only materializes if you import both CoreSpotlight and FoundationModels · the tool-call
trajectory: query → index → result-set description → grounded answer · ⚠️ `.complete` guidance
injects ~13k tokens of instructions and blows a 4K context instantly; ship `.focused(.items)` +
`.compact` · consuming `tool.searchResults` and `queryToken`-keyed UI refresh · ⚠️ the metadata gap:
only identity attributes come back, so the model hallucinates bodies — the retrieve-then-hydrate
companion-tool pattern · `searchableItems(forIdentifiers:)` and its caveats · custom `Generable`
pipeline stages (count, table, statistic) and the current beta routing gap · exposing custom
`IndexedEntity` attributes · known failures: the model silently not calling the tool; the
UnifiedAssetFramework Code=5000 model-catalog error; the description/JSON-Schema mismatch that makes
the tool unusable behind non-Apple models · OCRTool and BarcodeReaderTool · platform gaps (no
watchOS)

Depends on: `fm-tools-and-tool-calling`
Sources: `transcripts/fm-ecosystem.md`, `forums/forum-pain-points.md`, `transcripts/fm-core.md`

---

#### `fm-multimodal-image-input`
**Image input: Attachment, ImageReference, orientation, and what the model can't do with pixels**
*Audience: Swift app dev · ~4000 words · evidence: strong*

Vision on the rebuilt on-device model. Accepted formats, labeling for tool disambiguation, token and
latency cost, and the important negative result about spatial localization.

Sections: `Attachment(_:orientation:)` inside a `@PromptBuilder` block · accepted sources: CGImage,
CIImage, CVPixelBuffer, UIImage/NSImage, file URLs · no resolution cap, no image-count cap — the
context window is the only bound · why larger images cost more tokens and latency · `.label(_:)` and
the `Generable` `ImageReference` argument type for tools · image input does not change which model
services the request · ⚠️ EXIF orientation is not applied by `CIImage(contentsOf:)`; bake rotation
into pixels · PhotosPicker `Transferable` wrappers and security-scoped file URLs · ⚠️ the model
lists objects reliably but produces bad bounding boxes — use Vision for coordinates · image budget
estimation (~576 tokens/image as a working figure) · does PCC accept images? (open) · degrading
gracefully when the SDK or OS lacks image support

Depends on: `fm-session-lifecycle-and-prompting`
Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`, `forums/forum-pain-points.md`,
`repos/mlx-swift-examples.md`, `repos/python-apple-fm-sdk.md`

---

#### `fm-availability-errors-and-guardrails`
**Availability, errors, guardrails and refusals: the complete failure taxonomy**
*Audience: Swift app dev · ~6500 words · evidence: strong*

The single largest cluster of real-world pain in the corpus. Distinguishes four unavailability
reasons, two *different* refusal mechanisms, and four distinct error hierarchies, then gives the UX
Apple mandates when the model simply isn't there.

Sections: `isAvailable` / `isSupported` / `availability` and its four cases · ⚠️ availability keys off
the *Siri* language, not the system language; `supportsLocale(_:)` matches "close" languages · the
undocumented iOS 27 beta coupling to the Siri enablement toggle · region, hardware, download-state
and opt-out gates · ⚠️ there is **no** Required Device Capability for Apple Intelligence — you cannot
gate installs; Apple mandates a baseline non-AI experience · the two model tiers (AFM 3 Core vs Core
Advanced) and what that means without a version API · the four error hierarchies: `LanguageModelError`,
`LanguageModelSession.Error`, `SystemLanguageModel.Error`, `PrivateCloudComputeLanguageModel.Error` ·
all nine `LanguageModelError` cases with payload fields · guardrail violations vs model-level refusals
— two mechanisms, different triggers, both must be caught · `SystemLanguageModel(guardrails:)` and
why `.permissiveContentTransformations` does **not** apply to `Generable` · Apple may update
guardrails outside the OS cycle · documented false positives (health data, "frunk", ticks, camping) ·
the iOS 27 beta health-prompt refusal regression · safety design: input/output boundaries, deny
lists, adversarial suites, risk tables · `LanguageModelFeedback` / `logFeedbackAttachment` and the
`#Playground` feedback path · graceful-degradation UX patterns

Sources: `forums/forum-pain-points.md`, `web/apple-docs-fm-evals-speech.md`, `transcripts/fm-core.md`,
`repos/noema-ios.md`

---

#### `fm-context-window-and-kv-cache`
**The context window and the KV cache: token budgeting, prefix preservation, and what invalidates what**
*Audience: Swift app dev · ~6500 words · evidence: strong*

Merges the two topics that are actually one problem: what fits, and what it costs when you change
it. This is the guide that explains why a "harmless" instruction tweak triples your time-to-first-
token.

Sections: 4096 tokens on-device vs 32K on PCC; read `contextSize`, never hardcode · what consumes
the window: instructions, tool *definitions*, Generable schemas, transcript, tool I/O, reasoning
text · `tokenCount(for:)` (26.4+) and `Response.usage` (input/cached/output/reasoning) ·
`exceededContextWindowSize` / `contextSizeExceeded` and the fact that nothing auto-truncates ·
`maximumResponseTokens` and why it produces ungrammatical output · the session token layout:
instructions → tool definitions → transcript entries · the invalidation rule — a change at position
N invalidates everything after N · appending preserves the cache; rewriting instructions,
retrimming, or changing tools does not · conditional `DynamicInstructions` content must be declared
*last* · stateless in-place transforms vs dropping transforms vs stateful transforms, and their
different blast radii · batched consolidation beats incremental trimming · profile switches as a
deliberate full reset · `prewarm(promptPrefix:)` 1–2 s ahead when rehydrating a session · computing
cache hit rate from cached-input-token counts · measured Instruments wins (1044 → 700 max token
count) · "different models have different caching behavior — the only way to be certain is by
measuring"

Depends on: `fm-session-lifecycle-and-prompting`
Sources: `transcripts/fm-advanced.md`, `web/apple-docs-fm-evals-speech.md`, `transcripts/fm-core.md`,
`forums/forum-pain-points.md`

---

### Pillar: Foundation Models — context engineering & agentics

#### `fm-dynamic-profiles`
**Dynamic Profiles from zero: DynamicInstructions, Profile, and the full modifier set**
*Audience: Swift app dev · ~6500 words · evidence: strong*

The flagship 2026 API, built up in three layers, with the exact nested-protocol spelling that
transcripts get wrong.

Sections: the three layers — `DynamicInstructions` → `Profile` →
`LanguageModelSession.DynamicProfile` · ⚠️ the protocol is **nested**; transcript spelling won't
compile · the result-builder `body` and the exactly-one-active-Profile invariant · the body is
re-evaluated before every request — it must be pure; measured 7 evaluations for 3 turns · the full
modifier set: `.model`, `.temperature`, `.samplingMode`, `.reasoningLevel`, `.maximumResponseTokens`,
`.contextOptions`, `.toolCallingMode`, `.transcriptErrorHandlingPolicy`, `.historyTransform`,
`.modifier` · lifecycle modifiers: `onActivate`/`onDeactivate`/`onPrompt`/`onResponse`/`onToolCall`/
`onToolOutput`/`onReasoning` · the three-tier precedence rule (call-site args > innermost profile >
outer container) · nesting `DynamicInstructions` concatenates instructions *and* tools ·
`LanguageModelSession(profile:history:)` · switching profiles mid-session and what survives ·
writing custom `DynamicProfileModifier`s and the `extension DynamicProfile` ergonomics · a worked
multi-mode assistant

Depends on: `fm-session-lifecycle-and-prompting`, `fm-tools-and-tool-calling`
Sources: `transcripts/fm-advanced.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/foundation-models-utilities.md`

---

#### `fm-transcript-and-history-engineering`
**Transcript anatomy, session properties, and history engineering: historyTransform vs the history property**
*Audience: Swift app dev · ~6000 words · evidence: strong*

The transcript as a data structure, the state substrate around it, and the single most consequential
API choice in the framework.

Sections: `Transcript.Entry` — all six cases including the new `.reasoning` · segments: text,
structure, attachment, custom · `Transcript.history` (excludes the leading instructions entry) ·
`session.transcript` is now **mutable** — and mutating while `isResponding` is a trap, not an error ·
`@SessionPropertyEntry` in an extension on `SessionPropertyValues`; the mandatory initial value ·
`@SessionProperty(\.keyPath)` readable from any Tool or Profile; `session.properties` from outside ·
the built-in `@SessionProperty(\.history)` — lossy and global to the session · `historyTransform` —
local, per-profile, non-mutating, lossless · Apple's explicit recommendation and the decision table ·
history is **read-only** inside `DynamicInstructions` and `Tool` bodies · ⚠️ accuracy hazards: models
reason confidently from incomplete evidence; the add-a-tool-mid-session confusion; dangling tool
references after removal · "there's no reliable way for the model to distinguish information that
never existed from information that was removed" · serializing and restoring transcripts

Depends on: `fm-dynamic-profiles`, `fm-context-window-and-kv-cache`
Sources: `transcripts/fm-advanced.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/foundation-models-utilities.md`, `forums/forum-pain-points.md`

---

#### `fm-agentic-orchestration`
**Agentic orchestration: baton-pass, phone-a-friend, model routing, and transcript error policies**
*Audience: Swift app dev · ~5500 words · evidence: strong*

Multi-profile and multi-model architectures inside one session, plus the error/cancellation
semantics that make them survivable.

Sections: why Apple shipped primitives rather than an `Agent` type · **baton-pass** — shared
transcript, a mode variable, a tool that flips it; the receiving profile answers · **phone-a-friend**
— a tool spawns a short-lived child session with an isolated transcript; the parent always answers ·
the opposite transcript semantics of the two, and when each is right · exposing the mode switch
itself as a tool · model routing across on-device / PCC / third-party inside one session · ⚠️
crossing a privacy boundary ships the accumulated transcript to the new backend · ⚠️ crossing from
32K to 4K needs a `historyTransform` or you throw · `transcriptErrorHandlingPolicy`:
`.revertTranscript` (default) vs `.preserveTranscript`, and who owns repair · cancellation mid-turn
and resuming · combining `.required` tool calling with baton-pass · third-party model caveat:
tool-driven routing is unreliable on small models — use guided generation as the routing channel ·
memory cost of keeping two models resident (measured ~920 MB) and switch latency

Depends on: `fm-dynamic-profiles`, `fm-tools-and-tool-calling`
Sources: `transcripts/fm-advanced.md`, `web/apple-docs-fm-evals-speech.md`

---

#### `fm-utilities-skills-and-history-modifiers`
**foundation-models-utilities: Skills, history modifiers, and the KV-cache tradeoff made concrete**
*Audience: Swift app dev · ~6000 words · evidence: strong*

The separately-versioned package that ships the opinionated layer Apple deliberately kept out of the
OS framework. Contains the best single teaching example of KV-cache economics in the corpus.

Sections: what the package is, why it updates between OS releases, and where to file issues ·
`Skill`: two storages, four initializers · ⚠️ **the central tradeoff** — `prompt:` lands in a tool
output (cache preserved, normal priority) vs `instructions:` merges into the first instructions
entry (cache invalidated, high priority) · the choose-which heuristic · a skill activates by
generating a tool call, even prompt-based ones · `allowsDeactivation` and full context reclamation ·
`Skills` conforming to `DynamicInstructions`; the synthesized toggle tool and its schema ·
`SkillActivations` as an `Observable` reference type — hold one per session-equivalent ·
`droppingCompletedToolCalls()` · `rollingWindow(entries:)` and its documented bug ·
`summarizeHistory(entryThreshold:model:instructions:)` — ⚠️ destroys tool-call metadata, requires a
trailing `.prompt` entry, has no default model · outside-in modifier application order, resolved
precisely · the inert-composition trap · rolling your own with `@SessionProperty(\.history)` +
`.onPrompt` · what the shipped SKILL.md gets wrong (seven verified staleness points)

Depends on: `fm-transcript-and-history-engineering`, `fm-context-window-and-kv-cache`
Sources: `repos/foundation-models-utilities.md`, `02-lead-agent-corpus-gaps-filled.md`,
`transcripts/fm-advanced.md`

---

### Pillar: Foundation Models — providers & backends

#### `fm-languagemodel-protocol-and-executor`
**Implementing the LanguageModel protocol: executors, the generation channel, and transcript translation**
*Audience: Swift package author · ~8000 words · evidence: strong*

The architectural centerpiece of WWDC26, with exact protocol declarations from Apple's own agent
skill and two complete worked conformances to read against.

Sections: `LanguageModel` and `LanguageModelExecutor` — verbatim declarations and the associated-type
machinery · `LanguageModelCapabilities.Capability`: `.toolCalling`, `.vision`, `.reasoning`,
`.guidedGeneration` — and why declaring one you don't strictly support is a bug · reading
`LanguageModelExecutorGenerationRequest`: transcript, `enabledToolDefinitions`, schema,
`generationOptions`, `contextOptions`, id, metadata · the `ContextOptions` (prompt content) vs
`GenerationOptions` (decoder loop) split · mapping the six `Transcript.Entry` types onto your
model's roles · the channel: three top-level events (`.response`, `.reasoning`, `.toolCalls`) and
every action · `entryID` hygiene and the coalescing rule · ⚠️ `updateUsage` and `updateMetadata` are
**wholesale replacements**, not additive · ⚠️ every `.toolCall` event must carry the function name ·
`.removeToolCall` because there is no `replaceArguments` · `replaceTextSegment` instead of mutating
prior text · reasoning signatures are opaque bytes · one-shot is streaming underneath · the
prescribed event ordering — and the beta hazard that following it materializes an empty Response
entry on tool-call turns · `Transcript.CustomSegment` for new modalities · attachment segments
(add/remove, no replace) · cancellation contract · testing: request builders, a recording event
sink, and end-to-end through `LanguageModelSession`

Depends on: `fm-transcript-and-history-engineering`
Sources: `repos/foundation-models-utilities.md`, `transcripts/fm-ecosystem.md`,
`repos/mlx-swift-lm.md`, `repos/apple-coreai-models.md`

---

#### `fm-provider-configuration-state-and-packaging`
**Provider engineering: executor stores, Configuration hashing, stateful KV reuse, errors, auth, and packaging**
*Audience: Swift package author · ~7000 words · evidence: strong*

Everything after the protocol conformance compiles: making it fast, correct under error, and safe to
ship.

Sections: the executor store — `Configuration` is `Hashable` and is the **lookup key, not the model** ·
same configuration ⇒ shared executor ⇒ shared weights and KV state · what belongs in a Configuration,
and the manual `==`/`hash(into:)` pattern for non-Hashable engine handles · automatic
session-scoped teardown, and why a process-global weight cache opts you out ·
⚠️ `prewarm(model:transcript:)` must match the requirement exactly — a near-miss silently binds the
default no-op · stateful executors: you get the **full transcript every call**; diff it, preserve on
append, invalidate back to divergence · reporting `cachedTokenCount` · measured payoff (turn 2:
0.33 s with diffing vs 2.8 s without) · the two structural blockers: post-EOS over-generation
polluting the cache; thinking-model templates stripping historic reasoning · "approximate or throw"
— when to bend to developer intent and when to throw a built-in error · the nine `LanguageModelError`
cases as throw sites · when a custom error type is justified · auth: never take an API key String in
your initializer; token providers, Keychain, App Attest · packaging: SwiftPM platforms, Linux reach,
dependency weight, git-tag distribution · privacy disclosure obligations on both package author and
consumer · server-side tools and the three surfacing levels

Depends on: `fm-languagemodel-protocol-and-executor`
Sources: `transcripts/fm-ecosystem.md`, `repos/foundation-models-utilities.md`,
`repos/mlx-swift-lm.md`

---

#### `fm-private-cloud-compute`
**Private Cloud Compute: eligibility, entitlement, reasoning levels, quota UX, and fallback architecture**
*Audience: Swift app dev · ~5500 words · evidence: strong*

PCC has more policy and UX obligation than API surface, and for a large fraction of readers the
correct answer is "you are not eligible" — so the guide leads with that.

Sections: what PCC is and what it costs the developer (nothing) · ⚠️ eligibility is **three**
conditions: App Store Small Business Program enrollment + fewer than 2 million *lifetime first-time*
downloads + the `com.apple.developer.private-cloud-compute` managed entitlement · losing eligibility
and the 6-month migration window · the one-line switch: `LanguageModelSession(model:
PrivateCloudComputeLanguageModel())` · ⚠️ missing entitlement = runtime `fatalError`, not an error ·
`availability` and its distinct unavailable reasons (`.systemNotReady` has no SystemLanguageModel
analogue) · 4K vs 32K and when the bigger window actually changes your design · reasoning:
`ContextOptions(reasoningLevel:)` with `.light`/`.moderate`/`.deep`; reasoning text lands in its own
transcript segment and **counts against context** · reading reasoning entries and
`usage.output.reasoningTokenCount` for progress UI · `quotaUsage`: `isLimitReached`, `.belowLimit`
with `isApproachingLimit`, `resetDate`, `limitIncreaseSuggestion.show()` · Apple's explicit UX rules:
no alerts, persistent in-place state, disabled button, subtle label, actionable upgrade ·
⚠️ quota-limit-reached is not rate limiting; waiting doesn't help · the Xcode scheme options for
simulating quota states · ⚠️ PCC does not work in the Simulator at all · watchOS 27 and the pairing
question · locale gating and network-failure fallback to on-device · designing PCC as one tier
behind a protocol, never as the foundation

Sources: `transcripts/fm-ecosystem.md`, `02-lead-agent-corpus-gaps-filled.md`,
`forums/forum-pain-points.md`, `web/apple-docs-fm-evals-speech.md`, `repos/noema-ios.md`

---

#### `fm-openai-compatible-backends`
**Connecting Foundation Models to any OpenAI-compatible endpoint with ChatCompletionsLanguageModel**
*Audience: Swift app dev · ~4500 words · evidence: strong*

The single highest practical-leverage item in the corpus: it turns `mlx_lm.server`, Ollama, vLLM and
LM Studio into Foundation Models backends today, without waiting for anything.

Sections: `ChatCompletionsLanguageModel(name:url:additionalHeaders:)` and the capability declaration ·
`supportsGuidedGeneration: false` for servers that don't enforce schemas · the complete transcript →
chat-completions message mapping in both directions · SSE parsing and streaming-chunk coalescing ·
reasoning round-trip · usage reporting · sampling-mode translation and what it refuses ·
⚠️ **the `v1` URL bug**: `baseURL.pathComponents.contains("v1")` breaks any server on a different
version path (`/api/v3` → 404) — status and workaround · what it does *not* support: custom
segments, `prewarm`, `contextOptions` · pointing it at `mlx_lm.server` end to end · pointing it at
Ollama / LM Studio / vLLM · auth headers and where to keep the token · when to write your own
provider instead

Depends on: `fm-languagemodel-protocol-and-executor`
Sources: `repos/foundation-models-utilities.md`, `02-lead-agent-corpus-gaps-filled.md`,
`forums/forum-pain-points.md`, `transcripts/evals-mlx.md`

---

### Pillar: Foundation Models — tooling outside Swift

#### `fm-cli-and-python-sdk`
**Foundation Models without Swift: the fm CLI and the Python SDK**
*Audience: Python ML engineer, scripters · ~7000 words · evidence: strong*

Both non-Swift access paths, including the substantial install friction and the parity gaps that the
WWDC talk understates.

Sections: `fm` ships preinstalled with macOS 27 · `fm respond` / `fm chat` / `fm schema` /
`fm schema object` / `fm serve` · slash commands `/model` and `/save` · structured JSON output for
shell pipelines · ⚠️ `fm serve` is Apple's stated path to PCC from Python — there is no PCC in the
Python SDK · `pip install apple-fm-sdk` and what actually happens: a custom PEP 517 backend shells
out to `swift build` · ⚠️ requires **full Xcode**, not Command Line Tools; the license agreement must
have been accepted · ⚠️ image support is gated on the *build-time* SDK version
(`FM_HAS_MACOS_27_SDK`) as well as runtime OS · the Swift ↔ Python API mapping table ·
`@fm.generable` / `fm.guide` / `generating=` (not `response_type=`) · the guide-vs-type compatibility
matrix, validated at respond() time not decoration time · tools: the bridged-callback design, and why
exceptions become model-visible strings · streaming yields cumulative snapshots; no structured
streaming · transcripts: importing Swift-exported transcript JSON for analysis · `context_size` and
`token_count` (26.4+) · ⚠️ known bugs in 0.2.1: dropped `options` when `generating=` is used;
top-k/top-p/seed serialized as strings and silently ignored; `"Optional" in str(type)` breaking on
Python 3.14 and PEP 604 syntax; a file-descriptor leak that fails after ~240 image calls · memory
management across the boundary and why you must never call `_release()`

Depends on: `fm-guided-generation`
Sources: `transcripts/fm-core.md`, `repos/python-apple-fm-sdk.md`,
`repos/issues-community-stack.md`, `forums/forum-pain-points.md`

---

#### `fm-playground-and-instruments`
**Prototyping and profiling Foundation Models features: #Playground, Instruments, and scheme simulation**
*Audience: Swift app dev · ~5500 words · evidence: strong*

The observability story for a runtime you cannot unit-test in the usual way. Ends with a full worked
debugging narrative.

Sections: `#Playground` — multiple blocks per file as canvas tabs, project-wide type access with no
build, response inspector, thumbs-up/down feedback to Apple · Apple's canonical three-step workflow
(playground → view model → view) · Edit Scheme → "Simulated Foundation Models availability" to
exercise every unavailable branch on one machine · the quota-state simulation options · the
Foundation Models Instruments template: launching it, the record-anyway confirmation ·
⚠️ trace files contain **unencrypted prompts and responses** — treat them as sensitive · the six
lanes (only Instructions and Model Inference are documented) · the Instructions lane as a
profile-switch visualizer · yellow = prefill, orange = decode · the tree view hierarchy: sessions →
requests → model inferences → instructions/prompts/responses/tool calls · the invariant: every model
inference has instructions, a prompt, and either a response or an error · one request fans out into
multiple inferences · the Info column as a triage filter (errors, long durations, large token
counts) · the three metrics and their fixes: TTFT (shorten the prompt), tokens/sec (regression
detection), total latency (stream) · reading cache hit rate · **worked bug**: instruction prose
references a tool that isn't in the toolset; the model loops; nothing throws; the Instructions node
inspector is the only detector · handing off to Evaluations

Depends on: `fm-session-lifecycle-and-prompting`, `fm-context-window-and-kv-cache`
Sources: `transcripts/fm-advanced.md`, `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`

---

### Pillar: Core AI — Swift runtime

#### `coreai-runtime-fundamentals`
**Core AI from zero: AIModelAsset, AIModel, InferenceFunction, and your first inference**
*Audience: Swift app dev · ~5500 words · evidence: strong*

The complete happy path plus every gotcha that blocks a first build, and the inspection API you use
before you ever specialize.

Sections: what Core AI is and where it sits relative to Core ML and Foundation Models · platforms
(all seven, Apple silicon only, 27.0+) · ⚠️ the Metal Toolchain is **not** installed with Xcode;
builds containing `.aimodel` fail with a missing-Metal-compiler error · `.aimodel` files must be in
Compile Sources · the Xcode model viewer: General and Functions tabs, dynamic dims as `?`, editable
metadata · `AIModelAsset`: `isValid(at:)`, `summary(includingStatistics:)`, compute vs storage
types, operation distribution — inspection without paying for specialization · `AIModelAsset.Metadata`
and the six typed subscripts · `AIModel(contentsOf:options:)` — async **because** it specializes ·
`functionNames`, `functionDescriptor(for:)`, `loadFunction(named:)` (nil vs throw, and it can be
expensive too) · `InferenceFunctionDescriptor`: inputs, outputs, **states** · building an `NDArray`,
running, extracting outputs with `Outputs.remove(_:)` · ⚠️ `InferenceValue.ndArray` is a *consuming*
read · image-typed values and `ImageDescriptor` · concurrency: `InferenceFunction` is Sendable and
safe from multiple tasks, but silently allocates more buffers · `AssetError` · adapting to model
changes via descriptors instead of hardcoding

Sources: `web/apple-docs-coreai.md`, `transcripts/coreai-intro.md`, `repos/noema-ios.md`

---

#### `coreai-ndarray-memory-model`
**NDArray deep dive: views, spans, strides, interleaved layouts, and dynamic shapes**
*Audience: Swift app dev · ~6000 words · evidence: strong*

The densest and most error-prone area of Core AI, and one of the heaviest users of modern Swift
ownership features in the whole SDK.

Sections: the four view types — `View`, `MutableView`, `RawView`, `MutableRawView` — and the
compile-time read/write split · non-escapable types, `consuming`/`borrowing`/`mutating`, and why
`consume` appears in Apple's samples · `Span` / `MutableSpan` / `RawSpan` and `contiguousElements`
returning **nil** for non-contiguous layouts · value generics `<let rank: Int>` and `InlineArray`
subscripts · ⚠️ the `shape` handed to `withUnsafePointer` is a `Span<Int>` — no `for-in`, no `map` ·
`slice(at:)` vs `mutatingSlice(at:)`, and trailing dims defaulting to `.all` ·
⚠️ `MutableRawView.view(as:)` returns a **MutableView** despite the name · `NDArrayDescriptor`:
`shape` with `-1` for dynamic, `rank`, `hasDynamicShape`, `minimumByteCount` ·
`resolvingDynamicDimensions(_:)` — required before touching `preferredStrides` or `minimumByteCount` ·
⚠️ `preferredStrides` may be non-contiguous; ignoring it can cost a layout-conversion copy on every
run, but using it forfeits `contiguousElements` · `InterleaveLayout(dimension:factor:)`, the exact
element-offset formula, and the **block-stride** trap · the 33 `ScalarType` cases: FP8, MX block
formats, complex, 128-bit ints, and sub-byte int2–int7 / uint1–uint7 · zero-copy backing from raw
memory, `MTLBuffer` (must be `shared` storage), and `IOSurface` — and their explicit safety contracts ·
watchOS availability cliffs

Depends on: `coreai-runtime-fundamentals`
Sources: `web/apple-docs-coreai.md`, `transcripts/coreai-intro.md`

---

#### `coreai-specialization-and-caching`
**Specialization and AIModelCache: the deployment playbook**
*Audience: Swift app dev · ~5500 words · evidence: strong*

The single largest source of first-launch latency and mysterious storage growth.

Sections: what specialization is — two phases (compile/plan/optimize, then per-compute-unit artifact
generation) and which is expensive · artifacts are tied to **this device and this OS version** ·
the automatic-and-cached default path · the three latency levers: check the cache and gate UI;
`AIModel.specialize(...)` to control *when*; AOT to reduce *how much* · ⚠️ `specialize()` is not AOT —
"you are controlling when specialization happens, not reducing the work it does" ·
`AIModelCache.default` and `cache.model(for:options:)` returning nil without specializing ·
⚠️ the cache key is (source URL, `SpecializationOptions`) — `SpecializationOptions` is Hashable, so
varying it doubles storage and cost · `AIModelCache.Policy` and `PurgeConditions`
(`.sourceAssetChangedOrDeleted`, `.storagePressure`) vs `.persistent` · OS updates always invalidate ·
`deleteEntry` / `deleteEntries` / `deleteAll`, and the docs' own contradiction about live references ·
app-group sharing via `AIModelCache(appGroup:)` + entitlement · the **bookmark workflow**:
`bookmarkData` → UserDefaults → `init?(resolvingBookmark:)`, so you can delete the source asset and
keep running · ⚠️ bookmarks don't pin the entry, and fail two different ways (throw vs nil) ·
`SpecializationOptions`: `.default`, `.cpuOnly`, `preferredComputeUnitKind`,
`ComputeUnitKind.availableKinds` · the undocumented `expectFrequentReshapes` and where Apple's own
code sets it · ⚠️ every new *input shape* on a dynamic graph re-specializes — bucket your prompt
chunks · recovery ladder when a load wedges under storage pressure

Depends on: `coreai-runtime-fundamentals`
Sources: `web/apple-docs-coreai.md`, `transcripts/coreai-intro.md`, `repos/noema-ios.md`,
`repos/issues-community-stack.md`

---

#### `coreai-aot-compilation-and-distribution`
**Ahead-of-time compilation with coreai-build, and shipping .aimodelc to devices**
*Audience: both · ~5000 words · evidence: strong*

On iOS this is not an optimization — it is a requirement, and the failure mode is a maximally
misleading error message.

Sections: `.aimodel` (portable source, MLIR) vs `.aimodelc` (per-architecture compiled) · ⚠️ **iOS
cannot JIT** — loading raw IR on device fails with `NSPOSIXErrorDomain Code=2 "No such file or
directory"` · `xcrun coreai-build compile --platform --min-deployment-version --output
[--preferred-compute] [--architecture]` · one `.aimodelc` per architecture, named
`MyModel.<arch>.aimodelc`; matching at runtime with `AIModel.deviceArchitectureName` ·
⚠️ AOT only targets Apple-Intelligence-capable hardware (A17 Pro+, M1+, M2 Vision Pro) — older
supported devices still pay full on-device specialization · ⚠️ AOT does not eliminate residual
specialization · assembling the bundle afterwards: editing `metadata.json` so `assets.main` points
at the compiled filename · hosting remotely and downloading only the matching architecture via
Background Assets · the first-run / feature-opt-in experience as the place to hide download +
specialization · measured cold vs warm engine-ready times on device · when to ship two bundles
(static/ANE and dynamic/GPU) · `coreai-build inspect` and why success there proves nothing about
compilability

Depends on: `coreai-specialization-and-caching`
Sources: `web/apple-docs-coreai.md`, `transcripts/coreai-intro.md`, `web/community-blogs.md`,
`repos/issues-community-stack.md`

---

#### `coreai-states-and-pipelined-execution`
**States, KV caches, and pipelined inference: ComputeStream, AsyncValue, and preallocated outputs**
*Audience: Swift app dev · ~6000 words · evidence: strong*

The two performance tiers above "call run()": stateful inference, and encoding work without awaiting
it.

Sections: what a "state" is — an input read *and updated in place* during inference · the KV-cache
story end to end: `register_buffer` in PyTorch → mutable buffer in the exported program →
`state_names` at conversion → `InferenceFunction.MutableViews` at runtime · building MutableViews
recursively and passing them with `consume` · ⚠️ you must supply a view for **every** state; there
is no `stateCount` · fixed-size caches and the up-front memory tradeoff · the snake-game lesson:
latency grows "at a much slower rate", not flat · `outputViews:` for preallocated outputs — and the
behavioral fork where those outputs are then **omitted** from the returned `Outputs` ·
`encode(inputs:states:outputViews:to:)` — `throws`, not `async throws`; it returns once work is
encoded · `ComputeStream()` and `ComputeStream(commandQueue:)`; automatic serialization by data
dependency · `AsyncValue` / `AsyncMutableValue`, MTLBuffer-backed values, and the copy-on-read
behavior · `currentWorkCompleted()` · a real pipelined decode loop: pipeline depth, rotating
buffers, keeping the next token on the GPU, backpressure gating, and an empty-command-buffer
completion sentinel · ⚠️ in-place state updates copy the whole cache every step unless you park a
placeholder NDArray in the slot

Depends on: `coreai-ndarray-memory-model`
Sources: `transcripts/coreai-intro.md`, `web/apple-docs-coreai.md`, `repos/apple-coreai-models.md`,
`repos/noema-ios.md`

---

#### `coreai-debugging-and-profiling`
**Debugging and profiling Core AI: the Debugger app, the Xcode gauge, Instruments, and numerics validation**
*Audience: both · ~6500 words · evidence: strong*

All three tools plus the Python-side reference-run machinery that makes the most valuable one work.

Sections: the recommended triage order — gauge → Instruments → Debugger · the Xcode **debug gauge**:
requires the target to *directly* link CoreAI; three event types; exporting inputs as `.npy`/`.npz` ·
⚠️ the More menu is unavailable for events recorded before you opened the report · the **Instruments
Core AI template**: four bundled instruments, four event categories (Specialization, Load, Setup,
Inference) — and the gauge/Instruments colour and category disagreement · frequent Load events as a
bug signal · the standalone **Core AI Debugger** app: navigator grouped by PyTorch module, structure
viewer, source viewer mapping back to Python lines, inspector with tensor values · running against a
chosen hardware target · **sync points** — automatically identified op pairs — and the five
similarity metrics (PSNR default, MAE, MSE, max-abs, mean-relative) with metric-aware colouring ·
producing the reference run: `save_intermediates(...)` → `.aimodelintermediates` ·
⚠️ the Source Viewer needs debug metadata embedded at export (`USE_LOCAL_COREAI=1`,
`ENABLE_DEBUG_INFO=1`) · `TorchConverter.Mode.DEBUG` is the default and embeds torch stack traces —
strip for release · the worked case: uniform int4 broke one detection; low-PSNR sync points
clustered in a 4%-of-params decoder; excluding it restored quality at almost no size cost · Apple's
PSNR acceptance gates

Depends on: `coreai-runtime-fundamentals`
Sources: `transcripts/coreai-python-metal.md`, `web/apple-docs-coreai.md`,
`transcripts/coreai-intro.md`, `repos/coreai-torch.md`

---

#### `coreai-model-bundles-and-llm-engines`
**Model bundles and the Core AI LLM runtime: metadata.json 0.2, engines, KV strategies, and samplers**
*Audience: Swift app dev · ~7000 words · evidence: strong*

The `apple/coreai-models` Swift package — the layer between a raw `.aimodel` and a working chat
loop, plus the bundle format everything agrees on and no Apple doc describes.

Sections: why some models need more than a `.aimodel` (tokenizers, multi-asset pipelines) ·
`metadata.json` **schema 0.2**: `metadata_version`, `kind` (llm/vlm/diffusion/segmenter), the
`assets` role map, the `language` block, `function_map`, `vision` block · the `tokenizer/` sibling
directory and its nine files · ⚠️ the `.aimodel` is a **directory**; pointing `resourcesAt:` at it
instead of the parent gives a misleading version error · what `verify()` checks and who calls it ·
`EngineFactory` and structure auto-detection from graph function names · the four engines: pipelined
(GPU, on-device MPSGraph sampling, **no logits**), sequential (CPU sampling, logits available),
static-shape (ANE, chunked), and the VLM engine · the variant × structure compatibility matrix ·
`KVCacheStrategy`: `.auto` / `.fixedSize` / `.growing` / ⚠️ `.chunked` is accepted but unimplemented ·
memory math and the 9.6 GB → 155 MB chunked-prefill arithmetic · sampling: greedy/temperature/topK/
topP/minP, the CPU Accelerate path and the MPSGraph GPU path · ⚠️ a shared execution descriptor
across pipelined steps corrupts output above temperature 0 · implicit prefix caching via token
history; ⚠️ the pipelined engine cannot reuse KV across turns · streaming detokenization, U+FFFD, and
SentencePiece spacing · reasoning-tag and tool-call stream parsers · guided generation via xgrammar
and why it excludes the pipelined engine · `CoreAILanguageModel` as a `LanguageModel` conformance,
and what FM does *not* forward (only temperature) · the VLM/diffusion/speech/detection products in
brief

Depends on: `coreai-runtime-fundamentals`, `fm-languagemodel-protocol-and-executor`
Sources: `repos/apple-coreai-models.md`, `repos/noema-ios.md`, `01-lead-agent-repo-spotchecks.md`,
`repos/issues-coreai-stack.md`

---

### Pillar: Core AI — Python toolchain

#### `coreai-torch-conversion-and-io-contract`
**PyTorch to .aimodel: the coreai-torch pipeline and the IO/state contract**
*Audience: Python ML engineer · ~9000 words · evidence: strong*

The end-to-end bring-up path, the Python-side runtime you use to prove the conversion is
numerically correct before anyone writes Swift, and the naming/state/dynamic-shape contract that
silently corrupts models when you get it wrong.

**Part 1 — the pipeline.**

Sections: install (`pip install coreai-torch`, or `uv sync` from source) and the version gates
(Python 3.11+, torch 2.8–2.13, `coreai-core` pinned) · the canonical pipeline: `.eval()` →
`torch.export.export` → `run_decompositions(get_decomp_table())` → `TorchConverter` → `to_coreai()` →
`optimize()` → `save_asset()` · ⚠️ `run_decompositions` is **mandatory** — skipping it leaves ops with
no lowering rule · ⚠️ what `get_decomp_table()` deliberately preserves and why the default torch
table breaks `instance_norm` · ⚠️ `to_coreai()` runs **zero** optimization; forgetting `optimize()`
leaves unfused casts and a broken state signature · ⚠️ `optimize()` is not always semantics-preserving
— a documented case deletes a broadcast-significant `expand_dims` and costs ~17 dB PSNR; always A/B ·
`add_exported_program` vs `add_pytorch_module` and when each is required · multi-entrypoint assets:
several staged programs, distinct `entrypoint_name`s, one `to_coreai()` — the SAM3 three-function
split and its measured 76% prompt-swap win · `TorchConverter.Mode.DEBUG` (the default) vs `RELEASE` ·
running from Python: `AIModelAsset.load` → `async with asset.executable()` → `load_function` →
`await fn({...})`, and materializing with `.numpy()` **inside** the block · numeric parity assertion
against the torch module · the `.aimodel` on-disk shape

**Part 2 — the IO/state contract.** A dense set of non-obvious, non-contractual behaviors that
silently corrupt models when violated. This is where KV caches are born.

Sections: ⚠️ **breaking change**: `input_names`/`output_names` now cover only *non-stateful* IO ·
what counts as state — registered buffers mutated in place, and mutated user inputs — and the fact
that there is **no opt-out** · `state_names` ordering: buffers in registration order, then mutated
user inputs in signature order · the `MutableBuffers.buffer_mutation` IR attribute · ⚠️ default names
and ordering are "observed FX behavior, not a stable PyTorch contract"; the converter cannot detect
silent reordering — always name explicitly and re-verify on torch upgrades · why stateful models
*require* `optimize()` (mutation outputs become tokens) · the runtime `state=` protocol and
`desc.state_descriptor(name)` · dynamic shapes via `torch.export` `Dim`s; SymInts become `?` ·
⚠️ forgetting `dynamic_shapes` bakes in your sample sequence length · the SymInt hardening story:
bare `pow`/`round`, mixed-rank concat, mixed SymInt+int dim lists, dynamic concat axes ·
⚠️ symbolic slice arguments are rejected outright; INT32 slice clamping · ops that require static
shapes (`split`, `var`/`std` with ddof, `tensordot`, `tril`/`triu`, …) · ⚠️ int64→int32 and
float64→float32 are **silently narrowed** everywhere · sub-byte and reduced-precision dtypes
(uint1–6, int2/4, fp8, bf16, fp4 packed) and `inject_subbyte_tensors` · ⚠️ `torch.empty` lowers to
zeros

Sources: `repos/coreai-torch.md`, `transcripts/coreai-python-metal.md`,
`01-lead-agent-repo-spotchecks.md`, `repos/issues-coreai-stack.md`, `transcripts/coreai-intro.md`,
`repos/apple-coreai-models.md`

---

#### `coreai-torch-composites-lowerings-and-metal-kernels`
**Extending the converter: composite ops, externalization, custom lowerings, and TorchMetalKernel**
*Audience: Python ML engineer · ~7000 words · evidence: strong*

Everything between "convert as-is" and "write your own GPU kernel", including three concepts that
appear in no WWDC transcript.

Sections: **composite ops** — the built-in library (`SDPA`, `RoPE`, `RMSNorm`, `GatherMM`,
`GatedDeltaUpdate`) as a signal to the compiler that a fast kernel exists · `GatherMM` = MoE expert
dispatch; `GatedDeltaUpdate` = linear-attention/SSM state update — first-class MoE and SSM support
nobody announced · ⚠️ `ExternalizeSpec(target_class=...)` must name the **inner impl class**
(`RMSNormImpl`, never the wrapper) · a spec that matches nothing only warns · **externalization**:
the five-phase mark/re-export/prepare/export/emit/restore pipeline, per-call-site UUID graph names,
automatic composite IO naming, and the tensor-only/optional-arg rules · ⚠️ the ATen SDPA composite
and the module SDPA composite are **different**; the module version uses a lower-right causal mask
while torch uses upper-left — they diverge whenever q_len ≠ k_len (i.e. every decode step) ·
`RoPE` fp32 requirements and the Gemma3 `RMSNorm` numerics special case · **custom lowerings**:
`register_torch_lowering`, the `(values_map, node, loc)` contract, `get_operand`/`get_operands`,
multi-result nodes, `allow_override`, reserved namespaces, and `generate_composite_decl` · the op
registry and `supported-aten-ops.md`: FX qualified `op.overload` names, and the footgun that a
different overload from the decomposition pipeline is simply unsupported · the two validator error
messages and a decision tree (decomp-table tweak vs custom lowering vs Metal kernel) ·
**`TorchMetalKernel`**: the PyTorch-reference + MSL-body pairing, auto-generated signatures,
`MetalParameter`, `template_dtypes`, `helper_src`, mandatory `result_shapes` at every call site,
`register_custom_kernels` ordering, scalar-literal baking, and `StorageKind.METAL` inputs ·
⚠️ higher-order ops (`cond`, `while_loop`) only run on the interpreter compute unit ·
⚠️ transposed conv3d is unsupported; general conv_transpose falls back to a zero-filled composite
that saves cleanly and produces garbage

Depends on: `coreai-torch-conversion-and-io-contract`
Sources: `repos/coreai-torch.md`, `transcripts/coreai-python-metal.md`,
`01-lead-agent-repo-spotchecks.md`, `repos/issues-coreai-stack.md`

---

#### `coreai-opt-quantization`
**coreai-opt quantization: the config hierarchy, specs, graph vs eager, and QAT**
*Audience: Python ML engineer · ~7000 words · evidence: strong*

The largest and most error-prone API surface in the compression toolkit, where the wrong config
silently leaves a layer uncompressed.

Sections: the compressor lifecycle: `__init__` → `prepare(example_inputs)` → optional
`calibration_mode()`/`training_mode()` → `finalize(backend=)` · the three-level config hierarchy
(`QuantizerConfig` → `ModuleQuantizerConfig` → `OpQuantizerConfig`) and precedence
(module_name > module_type > global; op_name > op_type > defaults) · ⚠️ omitting a field applies
defaults; passing `None` **disables** compression for that scope — this distinction is load-bearing
and is how you exclude a layer · ⚠️ `module_type_configs` keys must be fully-qualified class paths ·
the three op-level tensor groups (`op_input_spec`, `op_output_spec`, `op_state_spec`) and what
weight-only means · `QuantizationSpec`: dtype catalogue (int2–8, uint2–8, fp8 e4m3/e5m2, fp4), qscheme,
qformulation (ZP vs MINVAL), granularity (per-tensor/channel/block), scale dtype · the MXFP4 recipe
and E8M0 power-of-two scales · the four qparams calculators and axis-resolution defaults by module
type · **GRAPH vs EAGER**: BN folding, shared observers, fake-quant dedup — and Apple's own statement
that they are *not guaranteed to produce equivalent models* · ⚠️ per-channel activation quantization
around channel-altering ops, the shape-aware safety check, and the concat-pulls-in-transpose hazard ·
QAT: `QATSchedule`, `step()` cadence, the observer/fake-quant state machine, mutual exclusivity with
manual enable/disable · KV-cache quantization (graph-only, CoreAI-only) · ⚠️ block-size/granularity
mismatches **silently disable** the layer with only a warning · calibration data and `get_c4` · the
Core ML export restriction matrix and `CoreMLExportError` · `finalize` destroys dense weights in
place · `mmap_dir` for large models

Sources: `repos/coreai-optimization.md`, `transcripts/coreai-python-metal.md`,
`repos/issues-coreai-stack.md`

---

#### `coreai-opt-palettization-pruning-and-joint`
**Palettization, pruning, casting, and joint compression — plus compressing an already-converted asset**
*Audience: Python ML engineer · ~6500 words · evidence: strong*

The other three coreai-opt techniques, the combinations that actually ship, and the ANE hardware
limit that changes every recipe.

Sections: k-means palettization: `PalettizationSpec` (n_bits ∈ {1,2,3,4,6,8}, granularity,
`cluster_dim`, `lut_qspec`, `enable_per_channel_scale`) · scalar vs vector palettization and
effective bits-per-weight math · ⚠️ `enable_per_channel_scale=True` produces rank-6 LUTs, **which
ANE rejects** (max rank 5), silently forcing GPU fallback — this is why the shipped SAM3 recipe
leaves it off · `PerGroupedChannelGranularity` divisibility requirements · ⚠️ palettization silently
**disables itself per layer** on incompatibility with only a warning · sensitivity-weighted k-means
(SqueezeLLM): squared-gradient hooks, normalization, `sensitivity_path` save/load ·
⚠️ `finalize(backend=CoreAI)` frees the original dense weights in place · determinism, `num_workers`,
and `enable_fast_kmeans_mode` · magnitude pruning: unstructured vs `ChannelStructured`, the
realized-sparsity rounding trap, `ConstantSparsity` vs `PolynomialDecay` schedules ·
`cast_to_16_bit_precision` on an ExportedProgram — stronger than `.half()` and different from
autocast; always compress first, cast second · **joint compression**: palettize → finalize →
quantize activations, why the ordering is mandatory, why the LUT must be INT8 to unlock the W8A8
runtime path, and why it is CoreAI-only · mixed-precision recipes: sensitivity → greedy → per-layer
config, with measured accuracy-vs-BPW curves · `coreai_utils`: `quantize_weights` /
`palettize_weights` / `sparsify_weights` on an already-converted `AIProgram`, entirely without
PyTorch · `ModelInspector` as the tool that tells you the exact config key strings

Depends on: `coreai-opt-quantization`
Sources: `repos/coreai-optimization.md`, `transcripts/coreai-python-metal.md`,
`repos/apple-coreai-models.md`

---

### Pillar: Core AI — model authoring & LLM deployment

#### `coreai-ane-vs-gpu-authoring-rules`
**Authoring models for the Neural Engine vs the GPU: two opposite rulesets**
*Audience: Python ML engineer · ~8000 words · evidence: strong*

Apple's own empirical deployment knowledge, shipped as agent skills and nowhere else. The correct
pattern *inverts* depending on target, which is exactly why this needs one comparative guide.

Sections: why re-authoring exists — hitting native hardware primitives instead of falling back ·
**ANE rules:** max tensor rank 5 · dtypes fp16/int8/int16 only, and any stray fp32 (including a bare
Python float literal) falls back · fully static shapes; export one function per shape config ·
the last axis is "width" and pads to 64 bytes — a singleton last dim costs 32× memory at fp16 and
64× at int8 · **BC1S** layout `(B, C, 1, S)` with exact permute/reshape recipes · `nn.Conv2d(1×1)`
instead of `nn.Linear`, with the weight-reshape helper · transpose bookkeeping at every projection
site as a source of silent correctness bugs · per-head attention (`bchq,bkhc->bkhq`) instead of
fused SDPA · causal mask shaped `(1, key, 1, query)` with `-40000.0`, **never** `-inf` · KV cache
must return **post-RoPE** keys or PSNR collapses to ~20 dB · softmax on the channel dim ·
convolution strides factoring into 2s and 3s · prefer high-level ops over hand-decomposed ones ·
graph segmentation and why one unsupported op can dominate small-model latency ·
**GPU rules:** standard (B,S,D) layouts, `nn.Linear`, fused QKV and fused QK-norm/RoPE, a single
fused SDPA across all heads, up-before-gate MLP ordering, `mutable_slice_update` stateful KV,
MoE via `SwitchLinear`/`SwitchGLU`/`GatherMM` with stacked expert weights, meta-device +
per-layer safetensors streaming for 7B+ · the **PSNR verification gates**: >70 dB re-authored vs
source, >70 dB ANE-vs-GPU layout, ≥40 dB compiled vs torch, ≥35 dB after 4-bit palettization ·
the bottom-up authoring order (norm → projections → attention → MLP → block) with per-primitive
verification · architecture discovery by running code with forward hooks, not reading it ·
~20 concrete failure signatures from `common_issues.md` · installing and driving the Core AI agent
skills

Depends on: `coreai-torch-conversion-and-io-contract`
Sources: `01-lead-agent-repo-spotchecks.md`, `repos/apple-coreai-models.md`,
`transcripts/coreai-python-metal.md`, `repos/issues-community-stack.md`

---

#### `coreai-llm-export-end-to-end`
**Exporting an LLM to Core AI: macOS dynamic, iOS static, compression presets, and the model registry**
*Audience: Python ML engineer · ~7000 words · evidence: strong*

The complete, reproducible recipe from a Hugging Face checkpoint to a loadable bundle, on both
platform paths, using Apple's own tooling.

Sections: `uv run coreai.model.registry --list-models` and the preset system (hf_id, family, variant,
compression, precision, max context) · `uv run coreai.llm.export <model> --platform iOS|macOS` and
the full flag surface · deterministic bundle naming and `--as-export-args`/`--as-output-name` for
scripting · **macOS dynamic path**: `(input_ids, position_ids)` in, `logits` fp16 out, `(keyCache,
valueCache)` states read positionally — and the engine's hard rejection of anything else ·
**iOS static path**: four entrypoints (`load_embeddings`, `gather_embeddings`, `extend`,
`prompt_opt`), the query-length × cache-length shape grid, `extend_<cacheLen>_<qLen>` naming,
IOSurface hardware constraints, uint16 position_ids · ⚠️ iOS export only supports a subset of model
types · compression asymmetry: macOS defaults to INT4 per-block, iOS to 4-bit per-grouped-channel
palettization with 8-bit embeddings · custom YAML compression recipes and their strict schema ·
memory-efficient streaming weight loading vs the legacy full-RAM path · assembling the bundle
(metadata.json, tokenizer files, function_map) · gated Hugging Face models and per-model quirks
(Gemma 3 needs bfloat16; GPT-OSS ships pre-quantized MXFP4) · running it: `llm-runner` flags,
`llm-benchmark` methodology, published perplexity/BPW tables · ⚠️ hybrid/SSM models
(GatedDeltaNet, Mamba2) fail the stock engine's two-state check · the multi-model app pattern:
two small task-specific models, independent upgrades, >1 GB download problem, first-run opt-in

Depends on: `coreai-torch-conversion-and-io-contract`, `coreai-model-bundles-and-llm-engines`
Sources: `repos/apple-coreai-models.md`, `transcripts/coreai-intro.md`,
`transcripts/coreai-python-metal.md`, `repos/issues-coreai-stack.md`

---

### Pillar: Metal / TensorOps

#### `tensorops-matmul-quantized-tensors-and-flashattention`
**TensorOps end to end: matmul2d, quantized Metal tensors with MX scale planes, cooperative tensors, and a fused FlashAttention**
*Audience: Metal/kernel author · ~9500 words · evidence: strong*

The MSL layer both Core AI and MLX sit on, grounded in the shipped SDK headers rather than only the
talk — built from a first matmul all the way to a fused attention kernel.

**Part 1 — matmul2d and quantized tensors.**

Sections: where TensorOps sits (MPS → Metal Performance Primitives + TensorOps) and what the M5
neural accelerator is · `mpp::tensor_ops::matmul2d_descriptor(m,n,k,transpose_left,transpose_right,
relaxed_precision,mode)` · ⚠️ the default `mode` is `multiply`, **not** `multiply_accumulate`, and
the examples assume C is zeroed · execution scopes: `execution_thread`, `execution_simdgroup`,
`execution_simdgroups<N>` — and the undefined behavior if the dispatched simdgroup count disagrees ·
`run()` must be scope-uniform; fragment shaders only get `execution_thread` · tensor tags:
`tensor_handle`, `tensor_offset` (from `.slice()`), `tensor_inline` (stack-constructed) ·
`slice()` vs `static_slice<...>` and the bounds-checking cost · host-side `MTLTensorDescriptor`,
`MTLTensorExtents`, usage flags, and rank limits · ⚠️ alignment rules: `strides[0]` must be 1;
64-byte alignment for machine-learning usage; **128-byte** alignment for sub-byte dtypes · the
quantized dtype timeline (int4/int8 in 26.4; fp4/fp8/int2 claimed for 27) · **scale planes** — one
`MTLTensor` carrying quantized data plus an E8M0 block-wise scale plane via a plane descriptor with
`blockFactors` and an auxiliary plane map · slicing slices data and scales together · feeding
quantized tensors straight to TensorOps so hardware acceleration engages · the supported dtype
matrix, and the fact that 4-bit types appear only as the right operand · how E8M0/block-32 lines up
with coreai-opt's MXFP4 spec and MLX's mxfp4

**Part 2 — cooperative tensors and FlashAttention.** The mechanism that lets you keep intermediates
in registers instead of round-tripping threadgroup memory, built up to a complete FlashAttention
skeleton.

Sections: what a cooperative tensor *owns* (thread-private data distributed across the scope) versus
the non-owning handle/offset/inline tensors · implementation-defined layout, and why it is only
valid for threads in that op's scope · accessors: `get_capacity()`, `get_mask(i)`, `operator[]`,
`get_multidimensional_index`, `load`/`store`, iterators · ⚠️ not all elements are valid — always
guard with `get_mask(i)`, and `#pragma unroll full` is "imperative for performance" · the three-tier
dequantization preference order: feed quantized tensors directly > dequantize into a cooperative
tensor > fall back to threadgroup memory · `reduce_rows` / `reduce_columns`, `reduction_operation`,
and the destination-factory helpers · ⚠️ `identity` defaults to `sum_identity` (0) **even for max/min**
— you must pass `-INFINITY` explicitly · `map_iterator` to bridge shapes for elementwise softmax,
guarded by `is_iterator_compatible` · **new in 27**: passing a cooperative tensor directly as a
matmul input via `get_left/right_input_cooperative_tensor(src)`, gated on
`is_compatible_as_left/right_input` — with the threadgroup fallback that keeps `op.run` identical ·
building FlashAttention: simdgroup-owns-complete-rows mapping so softmax needs no cross-group
exchange; slicing Q by simdgroup id; the running-max/running-sum loop · wiring the kernel into a
model via `TorchMetalKernel` and monkey-patching the HF attention implementation · the untouched
half: `MPPTensorOpsConvolution2d.h`

Sources: `transcripts/coreai-python-metal.md`, `repos/mlx-core.md`

---

### Pillar: Evaluations framework

#### `evaluations-fundamentals`
**The Evaluations framework: building blocks, Swift Testing integration, and the Xcode report**
*Audience: Swift app dev · ~6000 words · evidence: strong*

A whole Xcode 27 framework with essentially no public documentation. This is the foundation every
other Evaluations guide assumes.

Sections: why unit tests break for generative systems, and Apple's three questions · ⚠️ Swift-only,
Xcode 27+, macOS/iOS/watchOS/visionOS (tvOS absent) · not LLM-only — "any stochastic system" · the
`Evaluation` protocol's four responsibilities: `dataset`, `subject(from:)`, `evaluators`,
`aggregateMetrics(using:)` · `ModelSample` / `ModelSampleProtocol` and Codable datasets ·
loaders: `ArrayLoader`, `JSONLoader` (⚠️ silently skips malformed rows), `StreamLoader` · `Metric`
and its passing/failing/scoring/ignore results; the metric name doubles as a DataFrame column ·
`Evaluator` closures over the subject's output · `MetricsAggregator`: built-in statistics, `custom`,
and `group` · running it: `@Test(.evaluates(myEvaluation))`, `EvaluationContext.current.result`,
`aggregateValue(...)` inside `#expect` · the Xcode 27 report navigator: aggregate charts, results
table, assistant-editor per-sample detail with prompt, measurements, and full response · the Compare
view and `notes:` for labelling runs · the auto-generated test attachment · `EvaluationResult`
summary/detailed DataFrames and typed column subscripts · ⚠️ a passing test does not mean good
output — the pass/fail metric that hid a degenerate distribution (100% pass, always exactly 8 tags),
and the fix of pairing it with a scored metric · 20–30 samples is a fine start; coverage beats count ·
⚠️ PCC-backed evaluation may consume the user's metered quota in CI

Sources: `transcripts/evals-mlx.md`, `web/apple-docs-fm-evals-speech.md`

---

#### `evaluations-model-judges-and-alignment`
**Model judges, ScoreDimensions, and measuring judge drift with Cohen's kappa**
*Audience: Swift app dev · ~7000 words · evidence: strong*

Qualitative evaluation, and then the meta-evaluation that tells you whether your judge can be
trusted. The most statistically sophisticated material in the corpus.

Sections: when a metric must be qualitative — "if you can measure it in code it's quantitative" ·
a judge is just another `Evaluator` producing the same `Metric` type, so they mix freely ·
⚠️ the judge must be **at least as capable** as the model under test (on-device feature → PCC judge) ·
judge anatomy: instruction, feature input, feature output, scoring guide — the framework supplies
three of four · `ScoringScale`: numeric, pass/fail, custom enum · ⚠️ use an **even** number of levels
(1–4) so the judge cannot default to a neutral middle · `ScoreDimension` authoring: name,
description, per-level descriptions · pointwise, multi-dimension (all dimensions in one judge call),
and pairwise-vs-baseline modes · `ModelJudgePrompt(instructions:evaluationTarget:reference:)` and
why app context matters (a review-site judge treating criticism as a valid book descriptor) ·
rationales as the primary debugging signal · the refinement loop: when you disagree, the judge is
usually faithfully following your rubric — **split the dimension** · **drift**: systematic judge/human
disagreement that widens with dataset size · ⚠️ plain accuracy is misleading on score-skewed datasets ·
Cohen's kappa: `(accuracy − chance) / (1 − chance)`, target ≥ 0.6, implemented as a **custom
aggregation** (not a built-in) · the meta-evaluation recipe: pull the Xcode attachment, add human
ratings, freeze `subject(from:)` to return pre-generated output so the judge is the only variable ·
three documented judge-improvement iterations and the relevance-up/usefulness-down tradeoff decision ·
⚠️ too many few-shot examples overfits the alignment score

Depends on: `evaluations-fundamentals`
Sources: `transcripts/evals-mlx.md`, `web/apple-docs-fm-evals-speech.md`

---

#### `evaluations-datasets-trajectories-and-hill-climbing`
**Building evaluation datasets, evaluating agentic behavior, and evaluation-driven development**
*Audience: Swift app dev · ~9500 words · evidence: strong*

Where most teams actually spend their time: getting enough data, checking *how* the model got there
rather than only *what* it produced, and running the improvement loop as a real experiment.

**Part 1 — synthetic datasets with `SampleGenerator`.**

Sections: seeds first — hand-write 20–30 samples that cover the space · `makeSamples(prompt:dataset:
targetCount:)` on an array of samples, returning an async stream · ⚠️ `targetCount` is the size of the
**final** dataset **including** your seeds · full `SampleGenerator` control: `sessionProvider`,
`samplingStrategy`, `validator` · ⚠️ `sessionProvider` is called once and reused for continuity — but
context exhaustion mid-run throws and it is called **again** with no prior context, so instructions
must be self-contained · random vs sliding-window sampling and when order matters · the `validator`
closure: prompt rules are not guarantees, the validator is the only enforcement · ⚠️ it sees one
sample in isolation — corpus-level properties (length variation, genre diversity) cannot be checked
there · `samples` vs `invalidSamples`, updated live · generating tool-call datasets: `Trajectory-
Expectation` is itself `@Generable`, but the generating model knows nothing about your tools —
describe them in prose · recommended validation metrics for synthesized tool samples · ⚠️ expect
scores to **drop** when you scale the dataset; the four hypotheses when they do · using PCC as the
generation model for its larger context · running generation from a command-line tool

**Part 2 — tool trajectories and hill climbing.** Checking *how* the model got there, plus the
experimental discipline that makes an eval suite useful.

Sections: why output-only evaluation is insufficient — "the final output can look correct while the
path to get there isn't right" · `TrajectoryExpectation(ordered:unordered:disallowed:allows-
AdditionalToolCalls:)` · `ToolExpectation` and `.anyOrder(...)` groups · the nine `ArgumentMatcher`
strategies: `.exact`, `.keyOnly`, `.oneOf`, `.range`, `.pattern`, `.contains`, `.hasPrefix`,
`.hasSuffix`, and the LLM-backed `.naturalLanguage(argumentName:criteria:)` · `ToolCallEvaluator`
(`allPass` / `percentagePass`) and how it drives the session · ordered trajectories catching real
bugs (details-before-lookup with no id yet) · `disallowed:` as a negative-instruction test ·
a Spotlight-grounded worked example with a result-coverage metric over expected item identifiers ·
**hill climbing**: develop → evaluate → analyze → repeat; Apple's name for it is
evaluation-driven development · control vs experimental evaluations in one `@Suite` ·
⚠️ promote the accepted change into the baseline before the next experiment or you vary two things ·
the Xcode Compare view · hill-climbing things other than prompts: adding a tool with a defaulted
`tools:` parameter so existing evaluations keep compiling · using Evaluations as an OS-update
regression gate, since there is no model version pinning · the Python alternative when Swift isn't
an option (FM Python SDK + pandas + a server-model judge)

Depends on: `evaluations-fundamentals`, `fm-tools-and-tool-calling`
Sources: `transcripts/evals-mlx.md`, `transcripts/fm-ecosystem.md`,
`web/apple-docs-fm-evals-speech.md`

---

### Pillar: MLX — Python

#### `mlx-core-fundamentals`
**MLX fundamentals: arrays, unified memory, lazy evaluation, streams, and NumPy divergences**
*Audience: Python ML engineer · ~6000 words · evidence: strong*

The mental model, and the places MLX deliberately differs from NumPy in ways that cause silent
wrongness.

Sections: install matrix (Apple silicon + native Python 3.10+ + macOS 14; CUDA 12/13 and CPU wheels) ·
unified memory: you place **operations**, not data, via `stream=` — with the measured 2.8 ms → 1.4 ms
CPU/GPU split example · automatic cross-stream dependency insertion · lazy evaluation: what builds a
graph, what forces it (`print`, `np.array`, `memoryview`, `.item()`, any save), and `mx.eval` /
`mx.async_eval` · graph-size guidance and `MLX_BFS_MAX_WIDTH` · ⚠️ `print(loss)` before
`mx.eval(loss, params)` triggers a forward-only partial evaluation · ⚠️ **no bounds checking** on
indexing — out-of-bounds is undefined behavior because GPU exceptions can't propagate ·
⚠️ slicing **copies**, unlike NumPy · ⚠️ duplicate-index assignment is nondeterministic; use
`array.at[idx].add(...)` · boolean masks are assignment-only · ⚠️ `mx.empty` is an alias for
`mx.zeros` · dtype notes: float64 is CPU-only; bfloat16 cannot cross the buffer protocol ·
interop: buffer protocol vs DLPack, zero-copy `asarray(copy=False)` with its 16 KiB page-alignment
requirement, PyTorch ≥ 2.12 MPS shared storage, and ⚠️ DLPack does **not** synchronize pending Metal
work · ⚠️ writing through a NumPy view bypasses autodiff and silently produces wrong gradients ·
streams: `new_stream`, `new_thread_local_stream`, thread affinity, `synchronize` · `mlx.nn.Module`
as a dict subclass and what does/doesn't enter the parameter tree · optimizers and schedulers,
including Muon and `MultiOptimizer`

Sources: `web/mlx-docs-site.md`, `repos/mlx-core.md`, `repos/mlx-examples.md`

---

#### `mlx-compile-transforms-export-and-custom-kernels`
**Extending MLX: mx.compile, function transforms, .mlxfn export, and custom Metal/CUDA kernels**
*Audience: Python ML engineer · ~10000 words · evidence: strong*

Everything you reach for once the built-in ops stop being enough — from fusing a graph to shipping
your own kernel.

**Part 1 — compile, transforms, and export.**

Sections: the two compile passes (simplify, fuse) and `CompileMode` · ⚠️ **only element-wise/broadcast
primitives fuse** — never matmuls or reductions; the exact fusable set · the four recompilation
triggers (shape, ndim, dtype, arity) and the unbounded per-signature cache · `shapeless=True` and what
it does *not* exempt · ⚠️ shapeless silently bakes in the first trace's shape for any Python
arithmetic on `.shape`; use `flatten(0,1)` not `reshape(shape[0]*shape[1], -1)` · purity: printing
inside a compiled function crashes on placeholder tracers · captured arrays become frozen constants
unless declared with `inputs=`/`outputs=` · the canonical compiled training step with
`[model.state, optimizer.state]` and `mx.random.state` for Dropout · measured wins (gelu 15.5 ms →
3.1 ms) · `MLX_DISABLE_COMPILE` and the enable/disable API · transforms: `grad`/`value_and_grad`
with `argnums`/`argnames`, `vjp`/`jvp`, `vmap` with prefix-tree axes, `checkpoint` ·
`mx.custom_function` with `.vjp`/`.jvp`/`.vmap` sub-decorators, and captured variables getting zero
gradient · ⚠️ a transform of a compiled function is not itself compiled · export: `export_function`,
the `exporter` context manager for multi-trace files with constant dedup, `import_function`, and the
callback form for graph inspection · ⚠️ imported functions **always** return a tuple and reject
mismatched shapes/dtypes/kwarg names · ⚠️ exporting a Module bakes in its parameters — and their
random-initialization graph if unevaluated · consuming an `.mlxfn` from C++

**Part 2 — custom Metal and CUDA kernels with `mx.fast`.**

Sections: `mx.fast.metal_kernel(name, input_names, output_names, source, header, ensure_row_
contiguous, atomic_outputs, compile_options)` — `source` is the **body**, the signature is generated ·
what triggers injection of `<name>_shape` / `_strides` / `_ndim` · every MSL attribute in Table 5.8
becomes a function argument if referenced · `template=[("T", dtype)]` for one kernel across dtypes ·
the call signature: `inputs`, `output_shapes`, `output_dtypes`, `grid`, `threadgroup`, `init_value`,
`verbose` · ⚠️ `grid` is in **threads** (dispatchThreads), not threadgroups · ⚠️ `ensure_row_
contiguous=True` silently copies non-contiguous inputs · `utils.h` is auto-included (`elem_to_loc`,
`ceildiv`) · `compile_options={'math_mode': 'safe'|'relaxed'|'fast'}` — ⚠️ leaving `safe` is what
preserves `exp(-inf) == 0` for masked softmax · differentiable kernels: `atomic_outputs=True` +
`init_value=0` + `atomic_fetch_add_explicit`, simdgroup pre-reduction with `simd_sum`, wired up via
`mx.custom_function` — measured grid_sample vjp 676.4 ms → 16.7 ms · ⚠️ constructing a kernel builds
a new Metal library each time; hoist it out of hot loops · the CUDA twins: `cuda_kernel`,
`precompiled_cuda_kernel` (PTX/cubin, and it leaves outputs uninitialized without `init_value`) ·
debugging: `MLX_METAL_DEBUG` builds, `MTL_CAPTURE_ENABLED` + `mx.metal.start_capture`, Metal 3.2
shader `os_log` · authoring a native C++/Metal extension when a fast kernel isn't enough

Depends on: `mlx-core-fundamentals`
Sources: `web/mlx-docs-site.md`, `repos/mlx-core.md`, `repos/mlx-examples.md`

---

#### `mlx-quantization-formats`
**MLX quantization: affine, mxfp4, mxfp8, nvfp4, and quantized activations**
*Audience: Python ML engineer · ~5000 words · evidence: strong*

Sections: the four modes with their exact group-size / bits / scale-type table (affine 32/64/128 with
biases; mxfp4 g32 E8M0; mxfp8 g32 E8M0; nvfp4 g16 E4M3) · packing layout and why only affine has
biases · `mx.quantize` / `mx.dequantize` / `mx.quantized_matmul` · `mx.gather_qmm` for MoE expert
dispatch, `sorted_indices`, `segmented_mm` · `mx.qqmm` — quantizing activations on the fly (nvfp4 and
mxfp8 only, 2-D only, w must be non-quantized to receive gradients) · `mx.to_fp8` / `from_fp8` ·
`nn.quantize(model, ..., class_predicate=)` and `quantize_input=True` · `QuantizedLinear` /
`QuantizedEmbedding` (frozen) and `QQLinear` for QAT, which flips its weight between quantized and
dequantized across train/eval · ⚠️ affine rejects `bits == 7` · ⚠️ nvfp4 `global_scale` is **not
supported on Metal** · ⚠️ mxfp8 qqmm is not bit-exact against a dequantized reference ·
⚠️ silent MoE corruption on M5/NAX when gathered rows > 32768 and rows % 64 ≠ 0 — unwritten output
rows expose stale allocator memory, so regression tests must poison the buffer · a second defect on
`K % 64 != 0` that also hits mxfp4 · how MLX's formats line up with coreai-opt's MXFP4 spec and
Metal's scale planes

Depends on: `mlx-core-fundamentals`
Sources: `web/mlx-docs-site.md`, `repos/mlx-core.md`, `repos/issues-mlx-stack.md`

---

#### `mlx-memory-attention-and-numerics`
**MLX on real hardware: allocator limits, fused-attention coverage, and numerical reproducibility**
*Audience: Python ML engineer · ~6500 words · evidence: strong*

The three empirical topics that decide whether an MLX workload runs, runs fast, and produces the
same answer twice. Almost all of this is issue-tracker evidence, not documentation.

Sections: the memory knobs — `set_memory_limit`, `set_cache_limit`, `set_wired_limit`
(macOS 15+ plus `sysctl iogpu.wired_limit_mb`), `clear_cache` · ⚠️ `get_peak_memory()` tracks
**active only** and excludes the buffer pool — measured 1.00 GB reported against a 60 GB OS
footprint; gate on active+cache · ⚠️ `Resource limit (499000) exceeded` is a **buffer count**, not
bytes, with no setter — the two ways to hit it (unbounded compile-variant accumulation; caches built
functionally with concatenate) and their fixes · the buffer-cache reuse window and why monotonically
growing KV appends miss it forever, poisoning the pool for unrelated later work ·
⚠️ **fused SDPA coverage is narrow and the fallback is silent**: vector-path head dims {64,96,128,256},
full-path {64,80,128} — so Gemma 4's d=512 layers and Qwen3VL's d=72 vision tower never fuse ·
unfused prefill transient memory as a formula, and the chunking that only bounds it linearly ·
⚠️ the fused kernel is bypassed entirely during training on Metal · `MLX_SDPA_BLOCKS` and its
multiple-of-32 requirement · numerics: `MLX_ENABLE_TF32` defaults to **1**, is read once at first
use, and is gated on gen-17 hardware (M5/A19) with macOS ≥ 26.2 · batch-vs-single logit divergence
from two independent mechanisms · a shape-gated A19 fp32 matmul defect · what tolerances a test suite
can honestly assert · reading the GPU architecture string and its chip-class tuning

Depends on: `mlx-core-fundamentals`
Sources: `repos/issues-mlx-stack.md`, `repos/mlx-core.md`, `web/mlx-docs-site.md`

---

#### `mlx-distributed`
**Distributed MLX: ring, JACCL, MPI, NCCL — plus tensor parallelism and FSDP**
*Audience: Python ML engineer · ~5500 words · evidence: strong*

Sections: `mx.distributed.init(strict:backend:)` and ⚠️ its **sticky** semantics — the first
successful backend wins all later bare calls · the four backends and their tradeoffs; ring is always
available and usually beats MPI · ⚠️ collectives are silent no-ops at group size 1, so a
single-process run looks like it works · the collective set, and `sum_scatter` being NCCL-only ·
`Group.split(color:key:)` · `mlx.launch` (`--hosts`, `--hostfile`, `-n`, `--backend`, `--env`,
`--connections-per-ip`) and the stdin-broadcast/stdout-gather behavior that makes `pdb` usable ·
`mlx.distributed_config --over thunderbolt --auto-setup --dot` · the raw env-var contract for
scheduler-launched jobs · **JACCL**: RDMA over Thunderbolt 5, macOS 26.2+, a fully connected mesh,
and `rdma_ctl enable` from **Recovery** (it cannot be done remotely even with sudo); verify with
`ibv_devices` · `MLX_METAL_FAST_SYNCH=1` as "pretty critical for low-latency communication" ·
tensor parallelism: `AllToShardedLinear` (shards outputs, no gather) paired with
`ShardedToAllLinear` (shards inputs, all_sums) and why the asymmetry lets them compose; the full
Llama attention+FFN sharding recipe · data parallel via `nn.average_gradients` and its batching ·
FSDP via `nn.fully_shard` / `fsdp_apply_gradients`, axis-0 divisibility requirements, and
`clip_grad_norm_sharded` · the motivating case: a 1.6T-parameter model needing >800 GB · known
fragility (recv spinning forever on peer loss, ring socket death wedging all ranks)

Depends on: `mlx-core-fundamentals`
Sources: `web/mlx-docs-site.md`, `repos/mlx-core.md`, `transcripts/evals-mlx.md`,
`repos/issues-mlx-stack.md`

---

#### `mlx-lm-cli-conversion-and-quantization`
**mlx-lm: the CLI surface, model conversion, and learned quantization**
*Audience: Python ML engineer · ~6500 words · evidence: strong*

Sections: the 18 console scripts and the `python -m mlx_lm <sub>` dispatcher · `mlx_lm.generate` /
`chat` / `convert` / `fuse` / `server` / `evaluate` / `perplexity` / `benchmark` / `cache_prompt` /
`manage` / `upload` / `share` with real flags · `mlx_lm.load(...)` and ⚠️ `lazy=False` being the
default (an 18 GB spike on a MoE before the first token) · `mlx_lm.convert` with `--q-mode`
affine/mxfp4/nvfp4/mxfp8, `--quantize-activations`, and mixed-precision `--quant-predicate` recipes
modelled on Q4_K_M · ingesting AutoAWQ / GPTQ / compressed-tensors checkpoints natively ·
the four **learned** quantization CLIs — `dwq` (KD on scales/biases), `awq` (grid scale + clip
search), `gptq` (Hessian + Cholesky), `dynamic_quant` (gradient sensitivity to a BPW target) — and
the shared calibration corpus · ⚠️ documented defaults disagree with the code in several places ·
⚠️ AWQ supports only seven model types; GPTQ only 2/4/8 bits with a fallback that raises effective
BPW · ⚠️ `convert` refuses to write to an existing path and `save_config` silently strips keys ·
⚠️ CVE-2026-5843: `config.json`'s `model_file` executed arbitrary Python on a plain `load()` — now
behind `trust_remote_code` · ⚠️ `rich` and `regex` are imported but not declared as dependencies ·
GGUF export limits · evaluating the result with `mlx_lm.evaluate` (lm-eval `mlxlm`) and
`mlx_lm.perplexity`

Depends on: `mlx-quantization-formats`
Sources: `repos/mlx-lm.md`, `repos/issues-mlx-stack.md`, `repos/mlx-examples.md`

---

#### `mlx-lm-generation-caching-and-speculative`
**mlx-lm generation internals: KV cache types, prompt caching, and speculative decoding**
*Audience: Python ML engineer · ~6500 words · evidence: strong*

Sections: `generate` / `stream_generate` / `generate_step` and the `GenerationResponse` fields ·
samplers: exact application order (top_p → min_p → top_k → XTC) and ⚠️ `temp == 0` short-circuiting
to argmax, silently disabling every other filter · logits processors and the GPU-resident token ring ·
**the ten KV cache classes** and which are trimmable — trimmability gates both speculative decoding
and prompt reuse · `QuantizedKVCache`: ⚠️ it **raises** peak memory 30–73% during *prefill* while
lowering it 16–20% during decode, because unfused quantized attention materializes chunk×context
scores; the `prefill_step_size` mitigation · ⚠️ `--kv-bits` is a capacity lever, not a throughput
lever (measured −7.4% decode at 0.5K context) · ⚠️ `RotatingKVCache.to_quantized()` raises
`NotImplementedError`, so `--kv-bits` crashes on the first request for any sliding-window model —
and `hasattr` guards don't catch it · disk prompt caching: `cache_prompt`, the safetensors layout,
the `<query>` template trick, and the server's trie-backed LRU with prefix and rewind hits ·
speculative decoding: draft/verify/rewind, tokenizer compatibility, ⚠️ it is **not** bit-identical at
temp 0 (exact bf16 logit ties break differently), ⚠️ recurrent/SSM models are excluded outright ·
MTP: ⚠️ mlx-lm strips MTP weights at load *and* shifts norm weights, producing 56–79% slower decode
that looks like it worked · batch generation and `BatchGenerator` for RL workflows

Depends on: `mlx-lm-cli-conversion-and-quantization`
Sources: `repos/mlx-lm.md`, `repos/issues-mlx-stack.md`

---

#### `mlx-lm-server-and-local-agents`
**Running mlx_lm.server: continuous batching, OpenAI compatibility, and local agentic workflows**
*Audience: Python ML engineer / agent builders · ~5500 words · evidence: strong*

Sections: the four-layer local agentic stack (MLX → mlx-lm → server → agent) · starting the server
and the full flag set (`--decode-concurrency`, `--prompt-concurrency`, `--prefill-step-size`,
`--prompt-cache-size`, `--kv-bits`, `--draft-model`, `--chat-template-args`) · continuous batching:
how `BatchGenerator` moves sequences between prefill and decode batches so subagents don't queue ·
⚠️ `--draft-model` disables batching, and any request setting `seed` drains the batch · prompt-cache
segmentation by system/user/thinking and category-aware eviction · tool calling: the ten
auto-selected parsers, `tool_parser_type`, and ⚠️ passing tools to a tokenizer without tool support
only logs a warning · reasoning exposed as `message.reasoning` (not OpenAI's `reasoning_content`) ·
`usage.prompt_tokens_details.cached_tokens` · pointing agents at it: OpenCode, and **Xcode 27**
via Settings → Intelligence → Add Chat Provider → Locally Hosted · pointing **Foundation Models**
at it via `ChatCompletionsLanguageModel` · ⚠️ "not recommended for production; only basic security
checks" · the failure taxonomy: idle core spin, 404-on-error, uncaught-exception hang, and a
**livelock** where the GPU stays busy delivering zero tokens (defeating both `is_alive()` and
per-iteration heartbeats) — delivery-staleness is the only valid watchdog · distributed serving:
only rank 0 serves HTTP · M5 neural accelerators and why prefill dominates agentic sessions

Depends on: `mlx-lm-generation-caching-and-speculative`
Sources: `transcripts/evals-mlx.md`, `repos/mlx-lm.md`, `repos/issues-mlx-stack.md`,
`repos/foundation-models-utilities.md`

---

#### `mlx-lm-finetuning-and-porting`
**Fine-tuning with LoRA/DoRA and porting a new architecture to mlx-lm**
*Audience: Python ML engineer · ~6000 words · evidence: moderate*

Sections: the `mlx_lm.lora` workflow, YAML config schema, and every flag · which layers can take
adapters (Linear, QuantizedLinear, SwitchLinear, Embedding, and anything with `to_lora`), and
auto-discovery when `keys` is absent · LoRA vs QLoRA vs DoRA, and ⚠️ DoRA dequantizing the base
weight on **every** forward pass · dataset formats: chat, tools, completions, plain text, HF datasets ·
prompt masking, gradient accumulation, gradient checkpointing (⚠️ it monkey-patches the class), LR
schedules with warmup, five optimizers, W&B/SwanLab callbacks · length-sorted padded batching and the
rank-strided distributed variant · `mlx_lm.fuse`, de-quantizing on fuse, and GGUF export limits ·
the standalone `lora/` example as the from-scratch counterpart · ⚠️ known blockers: autograd through
MoE routing (`scatter_axis` VJP) and a documented hang at certain rank/module combinations ·
**porting an architecture**: the `ModelArgs`/`Model`/`sanitize`/`make_cache`/`shard`/
`quant_predicate` contract, the shared `base.py`/`rope_utils.py`/`switch_layers.py` toolkit, the 2026
per-layer config schema (per-layer `layer_types`, `mlp_layer_types`, nested `rope_parameters`), and
the test conventions

Depends on: `mlx-lm-cli-conversion-and-quantization`
Sources: `repos/mlx-lm.md`, `repos/mlx-examples.md`, `repos/issues-mlx-stack.md`

---

### Pillar: MLX — Swift

#### `mlx-swift-lm-getting-started`
**mlx-swift-lm 3.x: package setup, the HuggingFace macros, and the concurrency model**
*Audience: Swift app dev · ~5500 words · evidence: strong*

Sections: what 3.x changed — the package no longer depends on swift-transformers or
swift-huggingface; `Downloader`, `Tokenizer`, and `TokenizerLoader` are now protocols you supply ·
the three integration styles: hand-rolled protocols, an integration package (none exist yet), or the
in-repo `MLXHuggingFace` macros · `#hubDownloader()`, `#huggingFaceTokenizerLoader()`,
`#huggingFaceLoadModelContainer(configuration:)` — what they expand to and the imports they assume ·
the `FoundationModelsIntegration` SwiftPM trait · ⚠️ `swift test` does not work; use `xcodebuild
-skipPackagePluginValidation`, and `-skipMacroValidation` for consumers · `ModelContainer` vs
`ModelContext` vs `ModelConfiguration` · `perform`, `sending`/`consuming` semantics, `SendableBox`,
and ⚠️ `MLXArray` is not `Sendable` — always `eval()` before returning · running multiple
`ChatSession`s in parallel against one set of weights · the async-load idiom every sample app uses
(a three-state enum storing the `Task` itself) · `NSCache`-backed model switching · model loading
internals: config decode → type registry → EOS resolution → concurrent tokenizer + weight load ·
mixed-precision quantized checkpoints and per-module overrides · the 62/17/10 model type registries
and the "will this HF repo load?" checklist

Sources: `repos/mlx-swift-lm.md`, `repos/mlx-swift-examples.md`, `01-lead-agent-repo-spotchecks.md`

---

#### `mlx-swift-lm-generation-and-tools`
**Generation, streaming, tool calling, and reasoning in mlx-swift-lm**
*Audience: Swift app dev · ~6500 words · evidence: strong*

Sections: the generation entry points — `generate`, `generateTask`, `generateTokens`, and
`ChatSession` — and when each is right · `TokenIterator` (prefill happens in `init`) and the
`Generation` event enum (`.chunk`, `.toolCall`, `.info`) · `GenerateParameters` in full — ⚠️
`temperature` defaults to **0.6**, not 0 · sampler ordering matching Python exactly, and
`argPartition`-based top-k · penalty processors on a GPU-resident token ring · ⚠️ cancellation must
be checked **before** `iterator.next()`; a post-cancel GPU submission faults when an app backgrounds ·
⚠️ breaking out of an `AsyncStream` early leaves GPU work in flight on the same KV cache — use the
`...Task` variants and await · `ChatSession`'s eight initializers, history vs cache rehydration,
`streamResponse` / `streamDetails`, `saveCache` · ⚠️ default image `Processing` downsizes to 512×512 ·
⚠️ a trailing empty assistant message breaks the chat template · tool calling: `Tool<Input,Output>`,
the parameter DSL, `ToolCall.execute(with:)`, and the **ten** wire formats with per-model parsers ·
`ToolCallFormat.infer(from:)` and its `llama` vocab-size heuristic · ⚠️ Gemma 4 tool calls are never
extracted (exact-equality `"gemma"` vs `model_type "gemma4"`) · streaming tool-call state machine and
the ordered vs unordered APIs you must not mix · reasoning: `ReasoningConfig`, prompt strategies,
delimiter parsing, and per-family inference rules · `LMOutput.State` (M-RoPE deltas, cross-attention)
threaded across turns

Depends on: `mlx-swift-lm-getting-started`
Sources: `repos/mlx-swift-lm.md`, `repos/mlx-swift-examples.md`

---

#### `mlx-swift-lm-kv-cache-and-quantization`
**KV caching in Swift: eight cache types, quantization, TurboQuant, and prompt-cache serialization**
*Audience: Swift app dev · ~5500 words · evidence: strong*

Sections: the `KVCache` protocol: offset, `ropeOffset`, `maxSize`, `update`, `state`/`metaState`,
`isTrimmable`, `trim`, `makeMask`, `prepare`, `finalize` · the eight concrete classes and their
tradeoffs · `attentionWithCacheUpdate` — ⚠️ it performs the update; calling `cache.update` yourself
first is a real shipped bug that doubles the cache and corrupts attention · ⚠️ a model conforming to
`KVCacheDimensionProvider` must populate `kvHeads` per layer or generation traps · affine KV
quantization (`kvBits`/`kvGroupSize`/`quantizedKVStart`) vs **TurboQuant** schemes
(Walsh–Hadamard rotation + Lloyd-Max codebooks, JIT Metal kernels) · why prefill stays fp16 and
compression starts at the first decode step · which layers never convert (rotating/sliding-window,
hybrid recurrent) · ⚠️ `kvScheme` overrides `kvBits`, and an unrecognized scheme string is silently
ignored · ⚠️ `maybeQuantizeKVCache` takes `inout [KVCache]` and replaces **elements**, so quantized
caches never propagate back to `ChatSession` — all context after `quantizedKVStart` is silently lost ·
⚠️ `RotatingKVCache` becomes permanently untrimmable once its window wraps, silently no-oping
speculative rollback and defeating prefix reuse · prompt-cache save/load in a Python-compatible
safetensors layout · longest-shared-prefix trimming across turns as the TTFT lever ·
⚠️ `MLX.compile` freezes the cache write position because `offset` is a Swift `Int`

Depends on: `mlx-swift-lm-generation-and-tools`
Sources: `repos/mlx-swift-lm.md`, `repos/issues-mlx-stack.md`

---

#### `mlx-swift-fm-bridge-and-guided-generation`
**MLXFoundationModels and MLXGuidedGeneration: backing LanguageModelSession with an MLX model**
*Audience: Swift app dev / package author · ~5500 words · evidence: strong*

The most readable third-party `LanguageModel` conformance in existence, plus the xgrammar-backed
mechanism that makes `@Generable` work on a non-Apple model.

Sections: `MLXLanguageModel(modelID:)` and what you get for free (sessions, streaming, `@Generable`,
dynamic profiles) · declared capabilities and how each maps to MLX machinery · `SchemaConverter`
and the tool-calling envelope · ⚠️ `GenerationSchema` emits root-anchored `$ref` while the envelope
buries `$defs` — nested `@Generable` tool arguments failed grammar compilation until fixed ·
⚠️ rewrite `$ref`s on raw `JSONEncoder` output; a `JSONSerialization` round-trip escapes `/` and the
match silently never fires · ⚠️ `.toolCalling` on a VLM-loaded model was a process-killing abort
because the tool path built a 1-D `LMInput` · multi-round tool calling, `ToolCallingModeResolution`,
and the ordered `.response`/`.toolCall` output enum · `MLXGuidedGeneration`: xgrammar constraint
compilation, `CompositeLogitProcessor`, mask snapshots, whitespace and closing-token bias ·
the vendored xgrammar with renamed symbols so it cannot collide with **Core AI's prebuilt copy** —
direct evidence about Core AI's internals · ⚠️ SDK gating: the whole target compiles to nothing on
the 26 SDK; guard with `canImport(FoundationModels, _version: 2)` · FM API drift observed in the
betas: `SamplingMode.Kind` renames, and an `updateUsage` overload declared in the `.swiftinterface`
but absent from the dylib that **SIGSEGVs at image load**

Depends on: `mlx-swift-lm-generation-and-tools`, `fm-languagemodel-protocol-and-executor`
Sources: `repos/mlx-swift-lm.md`, `01-lead-agent-repo-spotchecks.md`, `repos/issues-mlx-stack.md`

---

#### `mlx-swift-app-integration-and-porting`
**Shipping MLX in an app: wired memory, entitlements, media input — and porting a model to Swift**
*Audience: Swift app dev · ~6500 words · evidence: strong*

Sections: the wired-memory system: `WiredMemoryManager`/`Ticket`/`Policy`, the four built-in policies,
measuring weight/KV/workspace bytes, and policy-only mode on CPU · `Memory.cacheLimit` /
`memoryLimit` / `snapshot()` — ⚠️ the old `MLX.GPU.set(cacheLimit:)` is gone; every pre-2026 tutorial
breaks · reading `Memory.memoryLimit` to detect a low-memory device before writing it ·
`com.apple.developer.kernel.increased-memory-limit` and the other entitlements sample apps ship ·
⚠️ the cache limit is process-wide — refcount it across models · MLX requires A13+ and needs float16
forced below that · VLM media input: PhotosPicker `Transferable` wrappers, EXIF baked into pixels,
security-scoped URLs, `UserInput.Processing(resize:)` · ⚠️ Qwen3VL vision prefill allocating 33.9 GB
from a dense joint mask plus a head dim outside the fused kernel — and the two-part fix · SwiftUI
streaming: isolating per-token updates, scroll anchoring, cancellation, markdown without
dependencies · LoRA adapters and on-device training · in-Swift model conversion as an
`mlx_lm.convert` replacement · **porting an architecture to Swift**: config Codables,
`@ModuleInfo`/`@ParameterInfo`, the attention/MLP/block skeleton, `sanitize`, tied embeddings, RoPE
helpers, MoE `SwitchGLU`, registration, and trace-based debugging against Python · the four-hop fix
propagation chain (mlx → mlx-c → mlx-swift → mlx-swift-lm) and why version pinning matters ·
using MLX as a general numerical library (compile, `metalKernel`, MLXArray → IOSurface → CALayer)

Depends on: `mlx-swift-lm-getting-started`
Sources: `repos/mlx-swift-examples.md`, `repos/mlx-swift-lm.md`, `repos/issues-mlx-stack.md`,
`repos/mlx-examples.md`

---

### Pillar: Bridges between stacks

#### `coreai-conversion-bridges-mlx2coreai-and-swift-lm`
**Third-party paths into Core AI: mlx2coreai and swift-lm**
*Audience: Python ML engineer / Swift package author · ~9000 words · evidence: moderate*

The two independent, non-Apple toolchains that target Core AI. Both are worth studying because they
are the only public descriptions of Core AI's MLIR-level and bundle-level contracts written by
someone outside Apple.

**Part 1 — mlx2coreai: the MLX → Core AI bridge.**

Sections: what it does — trace MLX with `mx.export_function(callback, ...)`, parse the event stream
into a small SSA IR, normalize and shape-infer, emit `coreai.GraphOp` MLIR, save an `.aimodel`
(`main.mlirb` + `main.hash` + `metadata.json`) · `convert_mlx_to_coreai` and `ConversionConfig` ·
weights as MLX "constants" → inline `ConstantOp`s or `DenseResourceElementsAttr` dense resources
above a threshold — there is no separate weight file · ⚠️ no quantization or palettization support at
all; bf16 stays bf16, fp64→fp32 and int64→int32 forced · dynamic shapes recovered by a **two-capture
probe**, differencing integer attributes to find real dimensions · composite declarations for
`rms_norm`, `rope`, and `scaled_dot_product_attention` as fusable-kernel hints ·
`convert-mlx-lm-stateful`: the `main` entrypoint with `input_ids`, `position_ids`, and mutable
`keyCache`/`valueCache`, matching Apple's own macOS contract byte for byte (including the trace
constants) · the `_ExportableLayeredKVCache` duck-typed shim that makes MLX record a
`slice_update` · position_ids must carry the **full** prefix range · ⚠️ batch size 1 only; no
sliding-window models · op coverage: 156 MLX names → 121 lowering keys, all exercised — but
"asset-generation coverage, not runtime numerical parity" · known silent miscompiles (log2/log10 →
natural log; shifts → AND) · ⚠️ the package pins `coreai-core==1.0.0b1`, **below** the loader floor,
so bundles it produces should be rejected by current Xcode 27 betas · why a Swift runner ships
alongside (incomplete Python bindings, no `state=` in its own runtime helper)

**Part 2 — swift-lm: a declarative Swift DSL that compiles to Core AI.** The only public example of
a versioned "executable contract" between a Swift model description and a Python lowerer, and the
only public non-Apple Core AI VLM adapter.

Sections: the pipeline — Swift `ModelComponent` DSL → LMIR → a versioned JSON `CoreAIExportDocument`
→ a **generic** Python lowerer → coreai-torch → `.aimodel` · why the 0.10 direct-Metal runtime was
demoted after the Core AI pivot · `swiftlm-ir` and `swiftlm-coreai` CLIs · the stateless contract
(`input_ids`/`position_ids` → logits, dynamic sequence) vs the **stateful** contract (`[1,1]` input
with a full-prefix `position_ids` and `keyCache`/`valueCache`/`convCache` states) · how states are
derived purely from the IR graph for attention, ShortConv, and GatedDeltaNet ·
SHA-256 contract pinning inside the bundle · the hard-fail-never-fallback policy and the exact
unsupported list (vision primitives, sliding-window attention, scaled RoPE, non-SwiGLU experts) ·
`CoreAIStateSession`: MTLBuffer-backed persistent states, recursive `AsyncMutableViews`, and a
hand-rolled async mutex to serialize GPU submissions under actor reentrancy · the **VLM adapter**:
Apple's three-asset contract (vision → embedding → decoder), `CoreAISequentialVLMEngine`, image
placeholder expansion, and the asymmetric text-vs-tokens prompt validation ·
⚠️ `expectFrequentReshapes` is rejected outright as a reproducible beta failure · portability traps
(`storageModeManaged` is macOS/x86_64 only)

Depends on: `coreai-torch-conversion-and-io-contract`, `coreai-model-bundles-and-llm-engines`
Sources: `repos/mlx2coreai.md`, `repos/swift-lm.md`, `01-lead-agent-repo-spotchecks.md`

---

### Pillar: Speech

#### `speech-analyzer-transcribers-and-assets`
**The Speech framework end to end: SpeechAnalyzer, transcriber selection, assets, and custom vocabulary**
*Audience: Swift app dev · ~9500 words · evidence: strong*

The modern speech-to-text stack. Mostly unchanged in 2026 apart from input plumbing, but with
several sharp failure modes that are easy to hit and hard to diagnose.

**Part 1 — the analyzer pipeline.**

Sections: the two API generations that coexist (SpeechAnalyzer vs SFSpeechRecognizer) · the
canonical eight-step flow, verbatim · `SpeechAnalyzer` as a `final actor` holding modules ·
⚠️ **one input sequence at a time** · the 2026 additions: `AssetInputSequenceProvider` (files),
`CaptureInputSequenceProvider` (mic/AVCaptureSession), `AnalyzerInputConverter` (AVAudioBuffer →
`[AnalyzerInput]`, synchronous and throwing) · ⚠️ SpeechAnalyzer performs **no** audio conversion, to
keep CMTime sample-accurate — you must feed `bestAvailableAudioFormat(compatibleWith:)`, which
returns nil until assets are installed, so assets come first · structured (`analyzeSequence`) vs
autonomous (`start`) analysis · ⚠️ terminating your input stream does **not** finish the session;
result streams hang open until you call a finish method or deallocate · `finalize(through:)`,
`finalizeAndFinish(through:)`, `cancelAndFinishNow()`, `cancelAnalysis(before:)` ·
⚠️ the system caps simultaneous analyzers and throws `insufficientResources`;
`ignoresResourceLimits` removes the cap but Apple warns of "an unpredictable error" ·
`ModelRetention` tuning · `SpeechDetector` as a VAD gate — it needs a transcriber module, its
results stream reports *errors* not speech events, and VAD can drop real speech · consuming results
as an `AsyncSequence`, volatile vs finalized results, and the two documented merge strategies ·
⚠️ cancellation shielding for the display task

**Part 2 — transcriber selection, assets, and custom vocabulary.**

Sections: `SpeechTranscriber` vs `DictationTranscriber` — the full comparison (platforms, presets,
options, content hints) and ⚠️ their **different platform matrices** (SpeechTranscriber has tvOS,
DictationTranscriber does not; neither lists watchOS) · both preset matrices mapping preset names to
exact option combinations, and how to destructure and modify a preset · `TranscriptionOption`,
`ReportingOption` (alternatives, fast results, volatile results), `ResultAttributeOption` (audio time
range, confidence) · `DictationTranscriber.ContentHint`: `.shortForm`, `.farField`,
`.atypicalSpeech`, `.customizedLanguage` · working with the result `AttributedString`:
`TimeRangeAttribute` and `ConfidenceAttribute` · **asset lifecycle**: `AssetInventory.assetInstall-
ationRequest(supporting:)` → `downloadAndInstall()`, ⚠️ it returns **nil** when already installed
(do not force-unwrap) and auto-reserves locales · `reserve(locale:)` / `release(reservedLocale:)` /
`maximumReservedLocales` and the throw when you exceed it · `AssetInventory.Status` and its
comparable ordering · assets are system-managed, shared across apps, auto-updated, and the system
can unsubscribe unused ones · progress reporting and request consolidation · biasing accuracy:
`AnalysisContext.contextualStrings` for lightweight hints vs `SFCustomLanguageModelData` for a real
custom LM · the result-builder DSL (`PhraseCount`, `PhraseCountsFromTemplates`, `Template`,
`CustomPronunciation` with X-SAMPA), building the `.bin`, and
`SFSpeechLanguageModel.prepareCustomLanguageModel(for:configuration:)` · ⚠️ custom vocabulary binds
only to `DictationTranscriber`; ⚠️ the sample does not run in the Simulator

Sources: `web/apple-docs-fm-evals-speech.md`, `00-ORIENTATION-lead-agent.md`

---

### Pillar: Shipping & operating on device

#### `shipping-and-operating-on-device-models`
**Shipping on-device models: distribution and updates, memory and jetsam, thermals, and honest benchmarking**
*Audience: Swift app dev · ~11000 words · evidence: strong*

Framework-agnostic but unavoidable, and the single largest source of shipped-app bugs in the forum
corpus: getting a multi-gigabyte model onto a device, keeping it there without being killed, and
measuring any of it credibly.

**Part 1 — distribution, updates, and storage.**

Sections: why you cannot bundle: >1 GB added to the download hits every updater, including people
who will never use the feature · the first-run / feature-intro opt-in screen as the correct place to
put the download **and** to hide specialization latency · Background Assets: Apple-hosted managed
asset packs, `BAHasManagedAssetPacks` / `BAUsesAppleHosting` / `BAAppGroupID`,
`StoreDownloaderExtension` · `AssetPackManager.ensureLocalAvailability(of:requireLatestVersion:)`
before you construct anything, and `statusUpdates(forAssetPackWithID:)` for progress ·
per-architecture `.aimodelc` variants: detect at runtime, request only the matching one ·
a production download engine: dual foreground/background `URLSession` with live task migration, and
⚠️ tasks *created* while inactive are discretionary regardless of `isDiscretionary` ·
⚠️ URLSession fires the cancel callback before `didCompleteWithError`, so migration must suppress
`NSURLErrorCancelled` · ⚠️ Range-header resumes report segment-relative bytes; resume-data resumes
report absolute — adding the offset twice freezes progress · iOS 26 `BGContinuedProcessingTask` for
keeping downloads on the fast session after backgrounding (`strategy = .fail`, wildcard identifiers,
1 Hz monotonic progress, resumable expiration) · storage: sandbox re-homing, verifying bundle
integrity, deleting sources while keeping cached specializations · model updates, versioning
artifacts, and why an `.aimodel` is a build artifact rather than a pure function of its recipe ·
Hugging Face as a distribution channel and repo tagging

**Part 2 — memory, jetsam, thermals, and benchmarking.** The dominant shipping constraint, plus the
measurement discipline you need to make any claim about it. Grounded almost entirely in a shipping
multi-backend app and an independent benchmark repo.

Sections: `os_proc_available_memory()` vs `phys_footprint`, reconstructing the process limit, and the
`increased-memory-limit` entitlement · the **two-stage launch gate**: incremental allocation must fit
available headroom, *and* the total logical working set must fit an advisory ceiling — because
mmap'd weights become resident as inference touches them · ⚠️ MoE + mmap means **every** expert is
resident; active-experts-only accounting is badly wrong · KV-per-token math and self-calibrating
transient reserves from measured launch peaks · a hysteretic four-level pressure governor with
recovery factors, and what to do at each level · background unload policy by runtime class, and
re-polling while a turn still streams · verifying unloads instead of assuming them (sample before,
detach in one transaction, settle, classify the delta) · ⚠️ Core AI has an iPhone "depth jetsam wall"
with no known control API · ⚠️ `std::bad_alloc` on iPadOS means jetsam — read Console.app, not Xcode ·
thermals: clamping threads, disabling warmup and keep-in-memory under serious/critical state ·
**sustained vs burst**: measured 10-minute retention (ANE 67%, Core AI 56%, GPU 38–48%) — "the GPU
wins the sprint; the ANE wins the marathon" · ⚠️ low instantaneous power ≠ low energy: CoreML/ANE
draws the least power and has the *worst* joules-per-token · benchmarking methodology: Release vs
Debug contamination (a real published result inflated a headline from ~1.4× to 1.6×),
thermal-nominal cold starts, cold vs warm reporting, stating the build per row, disclosing failed
runs, and why mmap'd vs wired memory are not comparable numbers

Depends on: `coreai-aot-compilation-and-distribution`
Sources: `repos/noema-ios.md`, `web/community-blogs.md`, `repos/issues-mlx-stack.md`,
`transcripts/coreai-intro.md`, `web/apple-docs-coreai.md`, `repos/apple-coreai-models.md`

---

### Pillar: Data & model quality (adjacent)

#### `dnikit-dataset-and-model-introspection`
**DNIKit: dataset and model introspection before you convert**
*Audience: Python ML engineer · ~4500 words · evidence: moderate*

The only thing in the corpus that addresses dataset quality and pre-deployment model analysis. Its
status must be stated honestly up front.

Sections: ⚠️ status first — v2.0.0 (2023), effectively dormant, PyPI build broken under Keras 3, the
fix exists only on `main`, and its own test suite currently fails · the Producer → PipelineStage →
Introspector model and its strict lazy evaluation · `Batch` (fields / snapshots / metadata),
`Batch.Builder`, and the three standard metadata keys · **PFA** for network compression: covariance
eigen-spectrum, the KL/Energy/Size strategies, unit selection, and the published compression results
(VGG-16 at 8×/3×/1.4× with accuracy *gains*) · ⚠️ PFA emits a recipe — you must retrain · **IUA**
for dead units · **Familiarity** (GMM over PCA-reduced embeddings) for rare/mislabeled data, and the
two-phase fit-then-score pattern where the introspector is itself a PipelineStage · **Duplicates**
(annoy + transitive closure) with Slope vs Percentile thresholds · **DatasetReport** and its
Symphony-compatible DataFrame column contract · the canonical PCA(1024→40) then UMAP/t-SNE recipe ·
⚠️ most introspectors accumulate the entire response set in RAM; only IncrementalPCA streams ·
how it relates to the Apple stack: it is a *pre-conversion* tool — you use it to pick data and
architecture, then convert with coreai-torch · the escape hatch for unsupported frameworks (a custom
Producer yielding precomputed activations), which is exactly how you would introspect an MLX model

Sources: `repos/dnikit.md`

---

## Recommended ordering and phasing

**Phase 0 — write these first regardless (the "core 12").** These are the guides everything else
links back to, and the ones a reader is most likely to need on day one.

1. `apple-ai-stack-2026-map`
2. `os-sdk-versioning-and-migration`
3. `fm-session-lifecycle-and-prompting`
4. `fm-guided-generation`
5. `fm-tools-and-tool-calling`
6. `fm-availability-errors-and-guardrails`
7. `fm-context-window-and-kv-cache`
8. `fm-dynamic-profiles`
9. `coreai-runtime-fundamentals`
10. `coreai-specialization-and-caching`
11. `coreai-torch-conversion-and-io-contract`
12. `mlx-core-fundamentals`

Rationale: 1–2 are prerequisites for reading anything else safely. 3–8 are the Foundation Models
spine and cover the two largest real-world pain clusters (availability/errors and context). 9–11 are
the minimum viable Core AI path — you cannot discuss anything else in Core AI without the
asset/specialize/run model and the conversion pipeline. 12 anchors MLX.

**Phase 1 — completes each framework to a usable state (16 guides).**
`fm-streaming-partially-generated` · `fm-multimodal-image-input` ·
`fm-transcript-and-history-engineering` · `fm-private-cloud-compute` ·
`fm-openai-compatible-backends` · `fm-playground-and-instruments` ·
`coreai-ndarray-memory-model` · `coreai-aot-compilation-and-distribution` ·
`coreai-states-and-pipelined-execution` · `coreai-model-bundles-and-llm-engines` ·
`coreai-opt-quantization` · `evaluations-fundamentals` ·
`mlx-lm-cli-conversion-and-quantization` · `mlx-lm-generation-caching-and-speculative` ·
`mlx-swift-lm-getting-started` · `shipping-and-operating-on-device-models`

**Phase 2 — depth and specialization (18 guides).** The agentic, provider, authoring-rules,
compression, Evaluations-depth, MLX-depth and MLX-Swift pillars:
`fm-spotlight-rag-and-system-tools` · `fm-agentic-orchestration` ·
`fm-utilities-skills-and-history-modifiers` · `fm-languagemodel-protocol-and-executor` ·
`fm-provider-configuration-state-and-packaging` · `fm-cli-and-python-sdk` ·
`coreai-debugging-and-profiling` · `coreai-torch-composites-lowerings-and-metal-kernels` ·
`coreai-opt-palettization-pruning-and-joint` · `coreai-ane-vs-gpu-authoring-rules` ·
`coreai-llm-export-end-to-end` · `evaluations-model-judges-and-alignment` ·
`evaluations-datasets-trajectories-and-hill-climbing` · `mlx-quantization-formats` ·
`mlx-memory-attention-and-numerics` · `mlx-lm-server-and-local-agents` ·
`mlx-swift-lm-generation-and-tools` · `mlx-swift-lm-kv-cache-and-quantization`

**Phase 3 — long tail and specialist material (9 guides).**
`mlx-compile-transforms-export-and-custom-kernels` · `mlx-distributed` ·
`mlx-lm-finetuning-and-porting` · `mlx-swift-fm-bridge-and-guided-generation` ·
`mlx-swift-app-integration-and-porting` ·
`tensorops-matmul-quantized-tensors-and-flashattention` ·
`coreai-conversion-bridges-mlx2coreai-and-swift-lm` ·
`speech-analyzer-transcribers-and-assets` · `dnikit-dataset-and-model-introspection`

**Two structural recommendations.**

*Ship a shared "verified vs unverified" convention.* A large fraction of this corpus is beta-era and
several claims are reconstructions from spoken narration. Every guide should mark API spellings that
were never seen in writing, and every measured number should carry its source (Apple, community, or
our own reading) and its hardware.

*Do not write the community-numbers guides from the community alone.* The benchmark material in
`shipping-and-operating-on-device-models` and `apple-ai-stack-2026-map` is genuinely unique, but two of
the ~14 community sources in the corpus are demonstrably fabricated (inventing `.coreaimodel`, a
`coreai-torch convert` CLI, "iOS 20", and an on-device LoRA API). Attribute community measurements
explicitly and spot-check anything that contradicts Apple's docs.

---

## Coverage gaps — where evidence is thin before writing

1. **The core Foundation Models open-source repo does not appear to exist yet.** Session 241 says the
   framework core is going open source; a GitHub search found only `foundation-models-utilities`,
   `python-apple-fm-sdk`, and `coreai-models`. Any guide claiming you can read or build the core must
   verify this first.
2. **Core AI has zero sample code and no release-notes page.** 0 `sampleCode` entries across all 312
   indexed symbols, and `/documentation/updates/coreai` 404s. The runtime guides rest on doc prose
   plus third-party code.
3. **`AIModel` → `InferenceFunction` is undocumented in every community source**, and no error type
   is documented for the throwing paths of `AIModel.init`, `loadFunction`, `run`, `encode`, or cache
   deletion. `AssetError` covers only asset operations.
4. **`coreai-build`'s full flag surface is unknown.** Apple names four flags; a fifth
   (`--architecture h18p`) is third-party only. The valid architecture codes are not published
   anywhere.
5. **The Evaluations framework has almost no written documentation and only three forum threads.**
   Several API spellings (`ScoringMode` cases, `aggregateMetrics(using:)`'s argument, the results
   bundle type, the `.evaluates` trait signature) are reconstructions. Vision/multimodal evaluation
   is an open, unanswered question.
6. **The `fm` CLI's actual flags were never shown.** Only semantic option names were spoken; long/short
   forms, `fm schema object`'s argument grammar, and the full subcommand list all need a live macOS 27
   run. Same for `fm serve`.
7. **The Foundation Models Instruments template has six lanes and only two are named** in any source.
   Do not fabricate the other four.
8. **Speech synthesis / TTS is entirely absent.** The WWDC26 keynote advertised better speech
   generation on the second-gen model; Apple confirmed on the forums that **no new API** exists. Do
   not invent coverage.
9. **PCC image input is unverified.** One transcript implies feeding images to PCC; no doc corroborates
   it, and nothing addresses separate image quota or cost.
10. **Custom adapters are discontinued in OS 27** (two independent Apple-staff statements), so any
    adapter material is historical. The migration path (Core ML / Core AI + Background Assets) is
    named but not documented end to end.
11. **Several Core AI beta bugs have unknown current status**: the `optimize()` silent miscompile, the
    linear-INT4 ANE pre-compiler SIGSEGV, the Gemma-4 MPSGraph scratch-heap overflow, the >16-token
    prefill nondeterminism, and the iOS KV-shape ≥2048 corruption. All need re-testing before
    publication.
12. **`coreai-core`'s Python API is only known from call sites.** `AIProgram._from_mlir_module` is
    private; `optimize()`'s parameters, the `.aimodel` on-disk layout, and whether the runtime mutates
    state NDArrays in place are all unconfirmed.
13. **MLX Swift internals were sampled, not read**: `TurboQuantKVCache` (1,765 lines),
    `SpeculativeTokenIterator`, `MTPSpeculativeTokenIterator`, and most of `ToolCallProcessor`. Also,
    55 of 56 LLM model files and all 17 VLM files were catalogued but not read.
14. **DNIKit's Keras 3 compatibility is unverified.** Nothing was executed; the 2026 fix exists only
    on `main` and there is no `.keras`-format loader at all.
15. **Two of ~14 community web sources are fabricated**, and a third uses a wrong file extension.
    Treat the community-blog pillar as needing per-claim corroboration.
