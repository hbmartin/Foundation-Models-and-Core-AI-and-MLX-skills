# Proposed guide series — organized by DEPTH LAYER

**Lens:** app-level API → high-level frameworks → runtime internals → compiler/conversion →
quantization math → Metal/ANE hardware.
**Written for:** a reader who wants to genuinely understand the machine, not just call it.
**Author:** synthesis agent (depth lens), 2026-07-27
**Sources:** the full `notes/` corpus (31 files, ~3.6 MB) — transcripts, repo deep-dives, Apple docs
harvests, forum mining, community writing. Deep-read this session: `transcripts/coreai-python-metal.md`
(all 2132 lines), `web/apple-docs-coreai.md` (runtime + NDArray sections), `repos/coreai-torch.md`
(composite ops / externalization / state), `repos/apple-coreai-models.md` (engines / sampling /
xgrammar), `repos/mlx-core.md` (fast kernels / quantization / Metal internals), `repos/noema-ios.md`
(memory), plus all three lead-agent orientation files.

---

## Why depth layers

The 2026 stack is unusually *legible* as a vertical: the same object (a KV cache, a 4-bit weight, a
matmul) reappears at every layer with a different name and a different set of footguns.

```
L1  app surface        availability, quota, jetsam, Background Assets
L2  framework API      LanguageModelSession, @Generable, Tool, Attachment
L3  framework internals LanguageModel/Executor protocol, transcript diffing, KV economics
L5  runtime internals   AIModel → InferenceFunction → NDArray; engines; samplers; xgrammar
L6  compiler            torch.export → decomp → Core AI MLIR → .aimodel → specialize → .aimodelc
L7  quantization        int4/int8/fp4/fp8, MX E8M0 block scales, k-means LUTs
L8  hardware            TensorOps matmul2d, cooperative tensors, ANE rank/alignment rules
```

Four facts make this ordering the right spine:

1. **Core AI and MLX are no longer alternatives to Foundation Models — they are backends for it.**
   `CoreAILanguageModel` and `MLXLanguageModel` conform to the new public `LanguageModel` protocol.
   So the "which framework" question dissolves into "which layer am I working at."
2. **The same numeric format runs the whole height of the stack.** `torch.float8_e8m0fnu` +
   `block_size=32` in `coreai-opt` → `float8e8m0fn` in `NDArray.ScalarType` → `fp8_e8m0` scale planes
   in MSL → `mxfp4`/`mxfp8` in MLX. One reference table serves five guides.
3. **The same KV cache appears four times.** As `historyTransform` (L3), as `states:` on
   `InferenceFunction.run` (L5), as `register_buffer` + `state_names` (L6), as an `MTLBuffer`
   rotated by pipeline depth (L5/L8).
4. **The failure modes are layer-local and the diagnostics are cross-layer.** A missing detection in
   SAM3 is a *quantization* bug (L7) found with a *debugger* (L6) because of an *ANE rank limit*
   (L8). Guides that don't teach the vertical can't teach the diagnosis.

---

## Pillars

| Pillar | Rationale |
|---|---|
| **L0 · Orientation and the layer map** | Nothing else parses without the layer diagram and the version matrix. The corpus contains at least six distinct OS/SDK/wheel gates that silently change behavior. |
| **L1 · App surface and shipping** | The unglamorous band: availability gating, PCC eligibility, memory limits, asset delivery. The forums show this is where most developers actually get stuck. |
| **L2 · Foundation Models API surface** | The framework as most people will use it: sessions, guided generation, tools, images, context budget. |
| **L3 · Framework internals and the provider boundary** | Where 2026 got interesting: Dynamic Profiles, session properties, the `LanguageModel`/`LanguageModelExecutor` protocol, KV-cache economics, Instruments. |
| **L4 · Evaluation and measurement** | Cuts across every layer; Apple explicitly makes it the only way to validate context-engineering and compression decisions. |
| **L5 · Core AI runtime internals** | `AIModel`/`InferenceFunction`/`NDArray`, specialization/caching, states, `ComputeStream` pipelining, and the four real LLM engines in `coreai-models`. |
| **L6 · Compiler and conversion** | `coreai-torch`: decomposition contract, op lowering, composite ops, externalization, state IO naming, numeric debugging. Plus the MLX→Core AI bridge. |
| **L7 · Quantization and numerics** | `coreai-opt` quantization/palettization/pruning, the cross-stack numeric-format reference, MLX's four quantization modes. |
| **L8 · Metal and ANE hardware** | TensorOps `matmul2d`, cooperative tensors, MX scale planes, custom Metal kernels, and the empirical ANE/GPU authoring rules from Apple's own agent skills. |
| **L9 · MLX as a parallel stack** | MLX solves the same problems one layer lower and in the open; reading it teaches the machine. |
| **L10 · Adjacent surfaces** | Speech (`SpeechAnalyzer`) and DNIKit — real parts of the corpus that would otherwise be crowded out. |

---

## Recommended ordering and the must-write core

### The 12 must-write guides (write these first, in this order)

These are chosen because each one is (a) load-bearing for many others, (b) strongly evidenced, and
(c) unavailable in a correct form anywhere else.

1. `stack-layer-map-and-version-gating` — the spine, plus the six version gates.
2. `coreai-runtime-fundamentals` — asset vs model vs function; nothing at L5+ parses without it.
3. `coreai-specialization-caching-and-aot` — the #1 source of first-launch stalls and wedged loads.
4. `coreai-torch-conversion-pipeline` — the mandatory decomposition contract; skip it and nothing converts.
5. `fm-sessions-and-prompting` — instructions-vs-prompts is the framework's security model.
6. `fm-guided-generation-and-streaming` — `@Generable` is the framework's differentiator.
7. `fm-dynamic-profiles` — the headline 2026 API; documented almost nowhere correctly (note the
   nested spelling `LanguageModelSession.DynamicProfile`).
8. `fm-context-engineering-and-kv-cache` — the single most consequential design decision in the framework.
9. `coreai-states-and-kv-cache` — the same problem one layer down; the SAM3/Snake teaching arc.
10. `coreai-opt-quantization` — you cannot ship a custom model without it.
11. `ane-and-gpu-authoring-rules` — Apple's own empirical rules; the densest gotcha source in the corpus.
12. `device-memory-and-thermal-budgeting` — the difference between a demo and a shipping app.

### Phasing

- **Phase 1 (foundation, 12 guides):** the must-write core above.
- **Phase 2 (breadth, ~13):** L1 shipping guides, remaining L2 API surface, `fm-tools`,
  `fm-instruments-profiling`, `evals-foundations`, `coreai-llm-inference-engines`,
  `coreai-torch-op-lowering-and-coverage`, `coreai-opt-palettization`.
- **Phase 3 (depth, ~18):** the provider boundary (L3), the rest of L6, the whole of L8,
  `coreai-lowlevel-performance`, `coreai-xgrammar-guided-decoding`.
- **Phase 4 (parallel stack + adjacent, ~12):** MLX (L9), `mlx-to-coreai-bridge`, Speech, DNIKit.

Phase 3 is the phase most organizations would skip. It is the reason to write this series at all:
TensorOps cooperative tensors, the `matmul2d` dtype matrix, `InterleaveLayout` block strides,
transcript diffing for KV reuse, and the externalization pipeline exist in no readable public
writing.

---

## Topics

### L0 · Orientation and the layer map

---

#### 1. `stack-layer-map-and-version-gating`
**The 2026 Apple AI stack: a layer map, and every version gate that changes behavior**
*Audience: both · ~4500 words · evidence: strong*

Establishes the vertical (Foundation Models → Core AI / MLX → Metal Performance Primitives) and the
reframing that matters most: `CoreAILanguageModel` and `MLXLanguageModel` are `LanguageModel`
conformers, so Core AI and MLX are backends for Foundation Models rather than competitors. Then
enumerates every gate that silently changes behavior — iOS/macOS 26.0 vs 26.2 vs 26.4 vs 27.0,
Xcode 26 vs 27 (and `canImport(FoundationModels, _version: 2)`), `coreai-core` 1.0.0b1 vs b2,
`MLX_METAL_VERSION >= 400` + deployment target 26.2 for NAX, and the A17 Pro/M1/M2 hardware floor
for AOT compilation. Ends with a decision table: given your model, target, and constraints, which
layer do you work at.

Sections: the four product lines and how they interlock · the `LanguageModel` protocol as the seam ·
Core AI vs Core ML (Apple's explicit routing: neural nets → Core AI, trees/tabular → Core ML) ·
the version matrix table · SDK-conditional compilation in practice · the Metal Toolchain as a
hidden build dependency · what runs where (device / simulator / Linux) · a "which layer" decision
tree · known naming traps (`.aimodel` vs `.aimodelc`, `coreai-opt` vs `coreai_opt`,
`LanguageModelSession.DynamicProfile` nesting) · what is *not* in this series and why.

Sources: `00-ORIENTATION-lead-agent.md`, `01-lead-agent-repo-spotchecks.md`,
`02-lead-agent-corpus-gaps-filled.md`, `web/apple-docs-coreai.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/mlx-swift-lm.md` §21, `repos/issues-community-stack.md`.

---

### L1 · App surface and shipping

---

#### 2. `fm-availability-and-degradation`
**Availability, eligibility, and graceful degradation for Foundation Models**
*Audience: Swift · ~3000 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

The largest single pain cluster in the developer forums. Covers `SystemLanguageModel.default.availability`
and its four unavailable reasons, `isAvailable`/`isSupported`, `supportsLocale(_:)` and the fact that
it keys on the **Siri** language rather than the system language, the undocumented iOS 27 beta
requirement that Siri be enabled at all, and the hard fact that there is **no Required Device
Capability for Apple Intelligence** — so you cannot keep your app off unsupported devices and must
ship a baseline non-AI experience.

Sections: the four unavailable reasons and their prescribed UX · `isAvailable` vs `availability` ·
the Siri-language coupling and how users fix it · region/EU considerations · the two on-device model
tiers (AFM 3 Core vs AFM 3 Core Advanced) and the hardware split · why there is no device-capability
gate and what Apple mandates instead · Xcode's "Simulated Foundation Models availability" scheme
option · why availability ≠ a working request (`ModelManagerError 1046`) · testing every branch on
one machine · the watchOS/PCC pairing question.

Sources: `forums/forum-pain-points.md`, `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`,
`repos/noema-ios.md` §6.

---

#### 3. `fm-error-taxonomy-and-guardrails`
**Errors, refusals, and guardrails: the complete taxonomy**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `fm-availability-and-degradation`*

Three error hierarchies now coexist, one of them deprecated, and the deprecation is
binary-compatible — meaning rebuilding with Xcode 27 silently changes which `catch` clause fires.
Separately, there are **two distinct refusal mechanisms** that developers routinely conflate: the
guardrail classifier (`LanguageModelError.guardrailViolation`) and a model-level refusal ("The model
refused to answer" / "May contain sensitive content") that is unaffected by the guardrails setting.

Sections: `LanguageModelError` vs `LanguageModelSession.Error` vs `SystemLanguageModel.Error` vs the
deprecated `GenerationError` · the Xcode 26/27 rebuild behavior · guardrail classifier vs model
refusal, with the exact strings · `SystemLanguageModel(guardrails: .permissiveContentTransformations)`
and why it does **not** apply to `Generable` · the documented iOS 27 health/medical refusal regression ·
real-world false positives from the forums (tick removal, "frunk", "Lock Pride", theology) ·
Apple's stated right to update guardrails outside the OS release cycle · `logFeedbackAttachment` and
the `#Playground` thumbs-up path · undocumented error identifiers seen in the wild
(`SensitiveContentAnalysisML error 15`, `UnifiedAssetFramework Code=5000`) · a defensive catch pattern.

Sources: `forums/forum-pain-points.md`, `web/apple-docs-fm-evals-speech.md`, `transcripts/fm-core.md`.

---

#### 4. `pcc-adoption-and-quota`
**Private Cloud Compute: eligibility, entitlement, reasoning levels, and quota UX**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `fm-availability-and-degradation`*

PCC has more policy than API. Eligibility is **three** conditions — App Store Small Business Program
enrollment, fewer than 2 million *lifetime first-time* downloads, and a managed entitlement — and
only the download threshold is mentioned in the WWDC sessions. For a large fraction of readers the
answer is "you are not eligible", so the guide leads with that and routes them to the fallback path.

Sections: the three eligibility conditions and the 6-month loss-of-eligibility cliff · the
`com.apple.developer.private-cloud-compute` entitlement and the correct application URL ·
`PrivateCloudComputeLanguageModel()` and the one-line model swap · 4K vs 32K context as a decision ·
`ContextOptions(reasoningLevel:)` — `.light`/`.moderate`/`.deep` — and the fact that reasoning text
consumes context · reading reasoning from `Transcript.Entry.reasoning` and
`usage.output.reasoningTokenCount` · the `quotaUsage` API and why it is deliberately coarse ·
Apple's prescriptive quota UX ("no alerts; persist in place; disable the button") ·
`limitIncreaseSuggestion.show()` · Xcode scheme options for simulating quota states · PCC on watchOS ·
PCC does not work in the Simulator · designing PCC as one tier behind a protocol.

Sources: `transcripts/fm-ecosystem.md`, `transcripts/fm-core.md`, `02-lead-agent-corpus-gaps-filled.md` §C,
`forums/forum-pain-points.md`, `web/apple-docs-fm-evals-speech.md`, `repos/noema-ios.md` §6.

---

#### 5. `on-device-model-distribution`
**Shipping and updating model assets: Background Assets, per-architecture variants, first-run flows**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

Bundling two small models added **over 1 GB** to an app download in Apple's own demo, hitting every
updater including people who will never use the feature. The answer is a first-run opt-in that
triggers a Background Assets download, which is also the natural place to hide specialization
latency. AOT compilation produces one `.aimodelc` per device architecture, so you must detect the
architecture at runtime and download only the matching variant.

Sections: the download-size problem, quantified · feature-intro screen as the opt-in surface ·
Background Assets and Apple-hosted managed asset packs · `AIModel.deviceArchitectureName` →
`MyModel.<arch>.aimodelc` · hosting per-architecture variants remotely · the bundle layout
(`metadata.json` + `tokenizer/` + nested `.aimodel`) · hand-editing `assets.main` after AOT compile ·
production download engines: dual foreground/background `URLSession`, live task migration, the
discretionary-when-backgrounded trap, Range vs resume-data byte accounting · iOS 26
`BGContinuedProcessingTask` with `strategy = .fail` and wildcard identifiers · model updates and
cache invalidation on OS upgrade · what happened to custom LoRA adapters (discontinued in OS 27) and
the migration path.

Sources: `transcripts/coreai-intro.md`, `web/apple-docs-coreai.md` §21, `repos/noema-ios.md` §11,
`forums/forum-pain-points.md`.

---

#### 6. `device-memory-and-thermal-budgeting`
**Memory, jetsam, and thermals: budgeting on-device inference on iOS**
*Audience: Swift · ~5000 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

The best material in the whole corpus for shipping, and it comes from a real app rather than a demo.
The core insight: on unified memory, allocation headroom alone is not a fit test, because mmap-backed
weights become resident as inference touches them — a broad logical overcommit will launch and then
OOM at long context. The remedy is a two-stage gate.

Sections: `os_proc_available_memory()` vs `phys_footprint` and reconstructing the process limit ·
per-device budget tables and the storage-tier override trick · the two-stage launch gate
(incremental allocation, then a total-working-set ceiling at ~1.11× on iOS) · why MoE means *every*
expert is resident under mmap · exact KV-bytes-per-token math from model metadata · recurrent/SSM
state accounting · compute-buffer models · self-calibrating transient reserves from measured launch
peaks · a hysteretic four-level pressure governor with recovery factors · format-aware background
unload policy and *verified* unloads (sample before, detach in one transaction, classify the delta) ·
the `kernel.increased-memory-limit` entitlement · `std::bad_alloc` as the jetsam signature ·
thermal state as a first-class input (clamping threads, disabling warmup, blocking paged launches) ·
process-wide MLX cache-limit refcounting.

Sources: `repos/noema-ios.md` §10 (the deep-read anchor), `repos/mlx-swift-lm.md` §17,
`repos/issues-mlx-stack.md`, `repos/apple-coreai-models.md` §10.

---

### L2 · Foundation Models API surface

---

#### 7. `fm-sessions-and-prompting`
**`LanguageModelSession`: instructions vs prompts, prewarming, and what actually works in a prompt**
*Audience: Swift · ~4000 words · evidence: strong · depends on: `fm-availability-and-degradation`*

The foundation guide for everything above L2. Its most important content is the security model:
instructions come from the developer, prompts may come from the user, the model is *trained* to obey
instructions over prompts, and that ordering is the prompt-injection defense — so never interpolate
user input into instructions. Also covers the measured performance work: `prewarm()` moved ~700 ms of
asset loading out of the session window in Apple's own Instruments demo.

Sections: session construction forms and lifetime · `Instructions {}` / `Prompt {}` result builders ·
the instructions-outrank-prompts security model · transcript ordering guarantees · `respond` vs
`streamResponse` (and why `streamResponse` is *not* `async`) · `prewarm()` and `prewarm(promptPrefix:)` ·
`isResponding` and `concurrentRequests` · `GenerationOptions`: sampling modes, temperature,
`maximumResponseTokens` (and Apple's own warning that hard caps produce malformed output) ·
greedy sampling as a *testing* tool, not a quality tool · one-shot prompting with a fully-populated
`@Generable` instance · Apple's counter-intuitive empirical finding that longer rule-heavy prompts
raise context-window errors and *lower* recall · prompting across the three on-device model versions ·
`#Playground` as the experimentation surface.

Sources: `transcripts/fm-core.md` (the 1013-line code-along), `web/apple-docs-fm-evals-speech.md`,
`transcripts/evals-mlx.md` (334 prompt study).

---

#### 8. `fm-guided-generation-and-streaming`
**Guided generation: `@Generable`, `@Guide`, dynamic schemas, and snapshot streaming**
*Audience: Swift · ~5500 words · evidence: strong · depends on: `fm-sessions-and-prompting`*

Two mechanisms that are usually taught separately but are one system: constrained decoding produces a
partially-valid object at every step, which is exactly what makes snapshot streaming possible. Covers
the full guide vocabulary, the two distinct constraint mechanisms (compile-time enums vs runtime
`.anyOf`), runtime schema construction with `DynamicGenerationSchema`, and the `PartiallyGenerated`
mirror types.

Sections: `@Generable` on structs and enums; composability and top-down constrained decoding ·
the full `GenerationGuide` catalogue (`pattern`/`element`/`count`/`constant`/`anyOf`/`range`/
`minimum`/`maximumCount`…) · enum-vs-`.anyOf` decision table · **the confirmed `.anyOf` bug** (Apple
reproduced it; the guide lists options in the schema but does not constrain generation) and its two
workarounds · why adopting `@Generable` lets you *delete* prompt text · `includeSchemaInPrompt: false`
and the causal chain that makes it safe (measured 1044 → 700 max tokens) · `DynamicGenerationSchema`,
references, and `anyOf` unions · `GeneratedContent` and `GenerationID` · `T.PartiallyGenerated` and
why every property including nested types is optional · why each streamed `.content` is a full
**snapshot**, not a delta · SwiftUI patterns that avoid the if-let boilerplate Apple's presenter gave
up on · classification enums require `.greedy` sampling.

Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`, `forums/forum-pain-points.md`,
`repos/python-apple-fm-sdk.md` §7.

---

#### 9. `fm-tools-and-calling-modes`
**Building tools: the `Tool` protocol, transcript anatomy, and escaping required-mode loops**
*Audience: Swift · ~4000 words · evidence: strong · depends on: `fm-guided-generation-and-streaming`*

Covers the `Tool` protocol end to end plus the 2026 addition that most needs a warning:
`toolCallingMode: .required` puts the model in an unbounded while loop and *you* must supply the exit
condition. Includes the six-entry transcript anatomy of a single tool-using turn, observed live.

Sections: `name`, `description`, `Arguments` as "the contract between the tool and the model" ·
`call(arguments:)` and its return type · why a tool will **not** reliably be invoked from its
definition alone (you must also instruct) · the six-entry transcript of one tool turn (one
`toolCalls` entry holding N calls; one `toolOutput` entry each) · `ToolCallingMode`
`.allowed`/`.disallowed`/`.required` in both the profile-modifier and `GenerationOptions` spellings ·
the two sanctioned exits from required mode (conditionalize the mode; a final-answer tool that
throws) · a compiled reference implementation of the required→disallowed gate · greedy sampling for
deterministic tool-call tests · `Tool.parameters` is computed **once** at session init and never
re-read · the built-in Vision-backed tools (`OCRTool`, `BarcodeReaderTool`) · tool schemas cost
context budget.

Sources: `transcripts/fm-core.md`, `transcripts/fm-advanced.md` §1.11, `forums/forum-pain-points.md`,
`repos/mlx-swift-lm.md` §12.

---

#### 10. `fm-spotlight-rag`
**Local RAG with `SpotlightSearchTool`: guidance profiles, pipeline stages, and the metadata gap**
*Audience: Swift · ~4500 words · evidence: strong · depends on: `fm-tools-and-calling-modes`*

Apple's "fully local Retrieval-Augmented Generation with no vector database" story, taught honestly —
including the failure that will burn most adopters. Core Spotlight stores text content in a compact
representation that is searchable but **not readable by a language model**, so a model answering from
search results alone sees only titles and will hallucinate bodies. The guide teaches the
retrieve-then-hydrate pattern as the primary recipe.

Sections: `SpotlightSearchTool()` and the cross-import overlay (you must import **both**
`CoreSpotlight` and `FoundationModels`) · `Configuration`: `sources`, `guide`, `contactResolver`,
`customStages` · the tool-call trajectory · **the metadata gap**: identity attributes only, the
documented hallucination case, and the `searchableItems(forIdentifiers:)` hydration hook · the
verified companion-`Tool` hydration pattern · `Guide(level:format:)` as a *token budget* decision —
`.complete` injects ~13k tokens and instantly exceeds a 4K context · `GuidanceProfile` fields ·
consuming `tool.searchResults` and keying UI refresh on `queryToken` (the model may call the tool
more than once per response) · `CustomStage` pipeline computation (count/table/statistic) and the
27.0-beta routing gap · known failures: the `UnifiedAssetFramework Code=5000` model-catalog error,
and the tool simply not being invoked · the description/JSON-Schema mismatch that makes the tool
unusable behind non-Apple models · evaluating a Spotlight-grounded feature with result coverage.

Sources: `transcripts/fm-ecosystem.md` (session 246), `forums/forum-pain-points.md`,
`web/apple-docs-fm-evals-speech.md`.

---

#### 11. `fm-multimodal-attachments`
**Image input: `Attachment`, `ImageReference`, and the limits of what the model can see**
*Audience: Swift · ~2500 words · evidence: moderate · depends on: `fm-guided-generation-and-streaming`*

New in 2026: images go directly into a `@PromptBuilder` block. Any size and aspect ratio is accepted
with no cropping or padding — but larger images cost more tokens and more latency, and image input
does **not** change which model services the request. The critical limitation: the model lists objects
correctly but produces unreliable bounding boxes, so spatial localization belongs to Vision.

Sections: `Attachment(_:orientation:)` and `Attachment(imageURL:)` inside `Prompt {}` · supported
sources (`UIImage`/`NSImage`/`CGImage`/Core Image/`CVPixelBuffer`/file URLs) · `.label(_:)` and why
labels matter · `ImageReference` as a `Generable` tool-argument type; `.resolved(in:)` · token and
latency cost as a function of image size · no documented resolution limit; count bounded only by
context · **the bounding-box limitation** and routing localization to Vision/`CoreAIObjectDetection` ·
EXIF orientation as a silent-wrong-answer bug in SwiftUI photo pickers · resize/`UserInput.Processing`
defaults that silently downscale · the macOS-27-SDK build gate in the Python SDK.

Sources: `transcripts/fm-core.md`, `web/apple-docs-fm-evals-speech.md`, `forums/forum-pain-points.md`,
`repos/mlx-swift-examples.md`, `repos/python-apple-fm-sdk.md` §6.

---

#### 12. `fm-cli-and-python-sdk`
**`fm` on the command line and `apple-fm-sdk` in Python**
*Audience: Python ML engineer / scripting · ~4500 words · evidence: moderate · depends on: `fm-sessions-and-prompting`*

The non-Swift on-ramp, taught with its real limits. The Python SDK compiles Swift at install time and
hard-requires full Xcode; it targets the 26-generation API; and Apple has stated on the record that
**PCC will not be added to it** — you reach PCC via the `fm` CLI or `fm serve`.

Sections: `fm respond` / `fm chat` / `fm schema` and the slash commands · `fm serve` as a
Chat-Completions endpoint (and therefore as a PCC bridge) · shell-scripting structured JSON out of
`fm respond --schema` · `pip install apple-fm-sdk`: the custom PEP 517 backend, the five preflight
checks, the Xcode.app-not-CLT requirement, and the `FM_HAS_MACOS_27_SDK` feature gate ·
Swift↔Python API mapping table · `@fm.generable` / `fm.guide` and the guide/type compatibility matrix ·
the `generating=` (not `response_type=`) requirement · streaming yields cumulative snapshots ·
`Transcript` JSON round-trip: export from a Swift app, analyze in Python · token counting and the
macOS 26.4 gate · **known bugs**: dropped `options` on `respond(generating:)`, string-vs-Int sampling
serialization that silently ignores seeds, `"Optional" in str(type)` optionality detection that
breaks on Python 3.14 and PEP 604 syntax, the FD leak fixed on `main` but not in any tag ·
what the Python SDK cannot do (PCC, feedback, manual tool-call interception).

Sources: `repos/python-apple-fm-sdk.md` (full), `transcripts/fm-core.md` (session 334),
`repos/issues-community-stack.md`, `01-lead-agent-repo-spotchecks.md`.

---

### L3 · Framework internals and the provider boundary

---

#### 13. `fm-dynamic-profiles`
**Dynamic Profiles: `DynamicInstructions` → `Profile` → `LanguageModelSession.DynamicProfile`**
*Audience: Swift · ~5500 words · evidence: strong · depends on: `fm-tools-and-calling-modes`*

The headline 2026 API and the one most likely to be written up incorrectly. The protocol is
**nested** (`LanguageModelSession.DynamicProfile`, matching Apple's own doc URL path), the `body` is
re-evaluated before *every* prompt, and a dynamic profile resolves to exactly **one** active profile
at a time. Because the body is re-evaluated (measured at 7 evaluations for 3 turns by a third party),
it must be pure — all imperative work belongs in lifecycle modifiers.

Sections: the three layers and what each owns · the nested-protocol spelling and why transcript-copied
code won't compile · `DynamicInstructions` composition (nesting concatenates instructions **and**
tools) · the result-builder `body` and the single-active-profile invariant · the pure-body rule ·
the full modifier set (`model`, `temperature`, `samplingMode`, `reasoningLevel`,
`maximumResponseTokens`, `toolCallingMode`, `transcriptErrorHandlingPolicy`, `modifier`,
`historyTransform`) · lifecycle modifiers (`onActivate`/`onDeactivate`/`onPrompt`/`onResponse`/
`onToolCall`/`onToolOutput`/`onReasoning`) and their real arities · the three-tier modifier
precedence · session properties: `@SessionPropertyEntry`, `@SessionProperty(\.keyPath)`,
`session.properties`, and the mandatory-initial-value rule · custom `DynamicProfileModifier` ·
`LanguageModelSession(profile:)` and `(profile:history:)` · profile switches take effect on the
**next** request, not mid-request · `.onToolCall` cannot reject a single call — a throw aborts the turn.

Sources: `transcripts/fm-advanced.md` (session 242, the deep-read anchor),
`repos/foundation-models-utilities.md`, `web/apple-docs-fm-evals-speech.md`,
`forums/forum-pain-points.md`, `repos/mlx-swift-lm.md` (compiled reference implementations).

---

#### 14. `fm-context-engineering-and-kv-cache`
**Context engineering: the token budget, history transforms, Skills, and KV-cache economics**
*Audience: Swift · ~6000 words · evidence: strong · depends on: `fm-dynamic-profiles`*

The single most consequential design area in the framework, and the one where Apple explicitly took
the training wheels off. The mental model: a session's transcript is `[instructions entry] + history`,
laid out as `instructions → tool definitions → transcript entries`; a change at position N
invalidates the cache for everything after N. That one sentence explains `historyTransform`,
`summarizeHistory`, the Skills API, and why conditional instruction content must go **last**.

Sections: the 4096-token on-device window (and 32K on PCC); what consumes it — instructions, prompts,
tool *definitions*, `@Generable` schemas, tool I/O, reasoning tokens · `contextSize` and
`tokenCount(for:)` (iOS 26.4+, `@backDeployed`) · `LanguageModelError.contextSizeExceeded` and
recovery · the session token layout and the invalidation blast radius ·
`historyTransform` (local, lossless, per-profile) vs `@SessionProperty(\.history)` (lossy, global)
and Apple's explicit recommendation · stateless-in-place vs stateless-dropping vs stateful transforms
and their cache consequences · the `foundation-models-utilities` modifiers — `droppingCompletedToolCalls`,
`rollingWindow`, `summarizeHistory` — applied outside-in, and what `summarizeHistory` destroys
(tool-call IDs) · **the Skills API as the best teaching example in the corpus**: initializing a
`Skill` with `prompt:` appends a tool-output entry (cache preserved) while `instructions:` rewrites
the first instructions entry (cache invalidated, but higher model priority); `allowsDeactivation` ·
conditional content must be declared last · batched consolidation beats incremental trimming ·
restoring a session has no KV cache — `prewarm()` 1–2 s ahead · the *accuracy* hazard: models reason
confidently from incomplete evidence, and adding a tool mid-session is often ignored · measuring
cache hit rate.

Sources: `transcripts/fm-advanced.md` §1.6/§1.13, `repos/foundation-models-utilities.md` §5/§6,
`web/apple-docs-fm-evals-speech.md` (the new KV-caching article), `forums/forum-pain-points.md`.

---

#### 15. `fm-agentic-orchestration`
**Agentic orchestration: baton-pass, phone-a-friend, and transcript error policy**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `fm-context-engineering-and-kv-cache`*

Apple shipped *primitives*, not an `Agent` type — explicitly, because "this field is changing
week-to-week." This guide covers the two named orchestration patterns with opposite transcript
semantics, plus the newly-mutable transcript and its crash risk.

Sections: why there is no `Agent` type · **baton-pass** (shared transcript, a mode variable, a tool
that flips it; the receiving profile answers) · **phone-a-friend** (a tool spawns a short-lived child
session with an isolated transcript; the parent always answers) · choosing between them ·
exposing the mode switch itself as a tool · crossing model boundaries mid-session and the privacy
implications (the accumulated on-device transcript ships to the new backend) · context-size mismatch
when switching from a 32K profile to a 4K one, and `historyTransform` as the fix ·
`transcriptErrorHandlingPolicy`: `.revertTranscript` (default) vs `.preserveTranscript` ·
`session.transcript` is now mutable — but mutating while `isResponding == true` is a **programmer
error** (a trap, not a throw) · repairing a transcript after cancellation · why third-party providers
make tool-driven baton-pass unreliable and guided generation is the better routing channel.

Sources: `transcripts/fm-advanced.md` §1.10/§1.12, `transcripts/fm-core.md`,
`repos/mlx-swift-lm.md`, `repos/apple-coreai-models.md`.

---

#### 16. `languagemodel-provider-package`
**Authoring a `LanguageModel` provider: capabilities, executors, and the generation channel**
*Audience: Swift · ~7000 words · evidence: strong · depends on: `fm-dynamic-profiles`*

The architectural centerpiece of the 2026 release, and the guide with the highest ratio of importance
to existing documentation. Two protocols and one linking value: `LanguageModel` declares capabilities
and vends an `executorConfiguration`; `LanguageModelExecutor` owns weights and streams; the
`Hashable` `Configuration` is the lookup key — "the configuration is the lookup key, **not** the
model." Includes the full streaming-channel event vocabulary and the "approximate or throw" error
contract.

Sections: the two protocols and the `Configuration` seam · `LanguageModelCapabilities.Capability`
(`.vision`, `.guidedGeneration`, `.reasoning`, `.toolCalling`) and why declaring them is
routing-relevant, not decorative · mapping the six transcript entry types onto your model's roles ·
reading a `LanguageModelExecutorGenerationRequest` (transcript, `enabledToolDefinitions`, `schema`,
`generationOptions`, `contextOptions`, `id`) · `ContextOptions` (what goes into the prompt) vs
`GenerationOptions` (the decoder loop) — a clean split worth teaching explicitly ·
the channel: `.response`/`.reasoning`/`.toolCalls` events and `.appendText`/`.appendArguments`/
`.updateMetadata`/`.updateUsage` actions · usage accounting including cached and reasoning tokens ·
one-shot is always streaming internally · the prescribed event ordering and **the beta hazard it
causes** (upfront usage materializes an empty `Response` entry on tool-call turns) ·
"approximate or throw": prefer built-in `LanguageModelError`s · custom segments as the modality
extension point · server-side tools and the three disclosure levels · auth guidance (never take an
API key string; token provider + Keychain + App Attest) · SwiftPM packaging, Linux reach, and
dependency weight · `ChatCompletionsLanguageModel` as the ready-made bridge that turns
`mlx_lm.server`, Ollama, LM Studio and vLLM into Foundation Models backends — including its
hardcoded `v1` path bug · **the `updateUsage` symbol-drift crash**: the beta `.swiftinterface`
declares a three-parameter overload the dylib doesn't export, and under arm64 chained fixups the
process aborts at image load.

Sources: `transcripts/fm-ecosystem.md` (session 339), `repos/foundation-models-utilities.md`,
`repos/mlx-swift-lm.md` §21, `repos/apple-coreai-models.md` §9, `forums/forum-pain-points.md`.

---

#### 17. `executor-store-and-transcript-diffing`
**Stateful executors: the executor store, prewarm lifecycle, and KV reuse via transcript diffing**
*Audience: Swift · ~4000 words · evidence: strong · depends on: `languagemodel-provider-package`*

The performance half of the provider story, and the part that is genuinely hard. Your executor
receives the **full transcript on every `respond` call** — you must diff it against what you saw last
time, preserve state on append-only changes, and invalidate back to the divergence point otherwise.
Measured payoff in a real implementation: turn 2 reused 97 cached tokens, prefilled 18, latency flat
at ~0.33 s versus 2.8 s without diffing.

Sections: the per-session executor store keyed by `Configuration`; same config ⇒ same executor ⇒
reused KV · what automatic teardown does and does not cover · why a process-global weights cache opts
you out and forces explicit eviction · **the silent-no-op `prewarm` trap**: the protocol ships a
default no-op, so a near-miss signature compiles and is never called (Apple's own `CoreAILanguageModel`
reportedly has this bug) · the transcript-diff algorithm: append-only fast path, divergence detection,
invalidate-to-divergence · reporting `Usage.Input.cachedTokenCount` honestly · the two structural
blockers: post-EOS over-generation poisoning the cache, and thinking-model templates stripping
historic reasoning blocks · measured multi-turn re-prefill tax without diffing · pipeline overshoot
past EOS making cross-turn reuse impossible on some engines · `Configuration` hashing when it wraps
non-`Hashable` engine handles.

Sources: `transcripts/fm-ecosystem.md` (session 339), `repos/apple-coreai-models.md` §10,
`repos/mlx-swift-lm.md` §11/§14, `repos/issues-community-stack.md`.

---

#### 18. `fm-instruments-profiling`
**Reading a Foundation Models trace: lanes, the inference tree, and silent failures**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `fm-dynamic-profiles`*

The only observability story for a non-deterministic runtime. The worked bug is the teaching device:
instruction prose referenced a `switchToTutorialMode` tool that was not actually configured with that
instruction set; the model kept accepting input and making tool calls and **never threw an error**.
Nothing cross-checks instruction prose against the declared toolset at compile time.

Sections: the exact click path and the Xcode 27 requirement · **the privacy warning**: traces record
prompts and responses unencrypted; logging is off in production but on for the duration of the trace ·
the six lanes (only Instructions and Model Inference are named on stage — do not fabricate the rest) ·
the Instructions lane as a profile-switch visualizer · yellow = prefill, orange = decode · the tree
hierarchy Sessions → Requests → Model Inferences → {Instructions, Prompts, Responses/Errors, Tool
Calls} · the invariant to check first: every model inference has instructions, a prompt, and either a
response or an error · one user request fans out into multiple model inferences · the Info column as
a triage filter (errors, long durations, large token counts) · the Instructions node inspector, which
is what finds the bug · the three metrics — Time to First Token (shorten the prompt), Tokens per
Second (regression detection), Total Latency (stream to reduce *perceived* latency) · the doc-only
cache-hit-rate metric (cached input tokens / total input tokens) · the Instrument works with **any**
`LanguageModel` provider, not just Apple's.

Sources: `transcripts/fm-advanced.md` PART 2 (session 243), `web/apple-docs-fm-evals-speech.md`,
`transcripts/fm-core.md` (the 2025 template baseline and the 1044→700 measurement).

---

### L4 · Evaluation and measurement

---

#### 19. `evals-foundations-and-hill-climbing`
**The Evaluations framework: building blocks, Swift Testing integration, and evaluation-driven development**
*Audience: Swift · ~5000 words · evidence: moderate · depends on: `fm-sessions-and-prompting`*

New in Xcode 27, Swift-only, built on Swift Testing and TabularData. The premise: generative models
"break a contract that is fundamental to software testing" — same input, different output — so unit
tests are insufficient. Note honestly that the framework has **no local Apple doc coverage** in parts
of the corpus and some signatures are reconstructed from narration; flag reconstructions.

Sections: the `Evaluation` protocol's four responsibilities — `dataset`, `subject(from:)`,
`evaluators`, `aggregateMetrics(using:)` · loaders (`ArrayLoader`/`JSONLoader`/`StreamLoader`) and
the silent-skip-malformed-rows trap · `Metric` and its passing/failing/scoring result factories ·
`MetricsAggregator` including grouping and custom aggregation · the `.evaluates(_:)` test trait and
`EvaluationContext.current.result` · `#expect` against `aggregateValue` · the Xcode 27 Evaluations
report: aggregate charts, results table, assistant editor, the Compare view, `notes:` for labeling
runs · **a passing test does not mean good output** — the framework's own worked example ·
pass/fail range metrics mask degenerate distributions (100% pass while the model always emits exactly
8 tags); always pair a range metric with a scored one · the hill-climbing loop (develop → evaluate →
analyze) and Apple's name for it · experiment hygiene: change one variable, then promote the
experimental change into the baseline · hill-climbing things that are not prompts (adding a tool, with
`tools:` defaulted to `[]` so the old evaluation keeps working) · it is not LLM-only.

Sources: `transcripts/evals-mlx.md` PART 1 and PART 3, `web/apple-docs-fm-evals-speech.md`,
`transcripts/fm-ecosystem.md` (session 246's eval section).

---

#### 20. `evals-model-judges`
**Model judges: rubrics, score dimensions, drift, and Cohen's kappa**
*Audience: Swift · ~6500 words · evidence: moderate · depends on: `evals-foundations-and-hill-climbing`*

A judge is "just another `Evaluator`" producing the same `Metric` type, so quantitative and
qualitative evaluators mix freely. The central conceptual moment: when you disagree with the judge,
the judge is usually faithfully following *your* rubric — you meant something specific by "relevant
and useful" and the judge interpreted those words differently.

The second half asks the harder question: is your judge aligned with *you*? Drift is systematic
judge-vs-human disagreement that widens as the dataset grows, and plain accuracy is a bad alignment
metric because evaluation datasets skew toward high-quality output.

Sections: judge anatomy (instruction, feature input, feature output, scoring guide) and what the
framework handles for you · the judge must be at least as capable as the model under test
(on-device feature → PCC judge) · `ScoringScale`: `.numeric`, `.passFail`, `.custom` ·
**why an even number of levels** — it prevents defaulting to a neutral middle — and why four ·
`ScoreDimension` authoring; if every score comes out the same, your dimension is too broad · the
split-the-dimension move (quality → Relevance + Usefulness) with the worked case study ·
`ModelJudgePrompt`: `instructions` (app context), `evaluationTarget` (response formatting),
`reference` · pointwise vs multi-dimension (all dimensions in one judge call, no extra latency) vs
pairwise-against-baseline · **rationales are the product** — "you'll learn more from a single run
than from hours of careful planning" · few-shot calibration and the overfitting warning · PCC quota
risk when a judged run hits PCC in CI. · **drift and alignment** · the definition of drift and why it grows with dataset size · why accuracy fails on a skewed score distribution · Cohen's kappa: `(accuracy − chance) / (1 − chance)`, with chance weighted by score prevalence · the 0.6 threshold and its provenance · implementing kappa as a **custom aggregation method** (it is not a built-in) · the meta-evaluation recipe: pull the auto-generated Xcode test attachment from the previous run, extract (input, output) pairs, add your own human ratings, feed that file back as the dataset, and freeze `subject(from:)` to return the already-generated output so the judge is the only variable · the three documented improvement iterations (richer app context → sharper dimension descriptions → few-shot examples of your own judgements) · accepting a change that improves one dimension and degrades another · few-shot overfitting destroys your ability to tell whether the judge is aligned.

Sources: `transcripts/evals-mlx.md` §1.12 and PART 3 (session 335), `web/apple-docs-fm-evals-speech.md`.

---

#### 21. `evals-synthetic-data`
**Synthetic evaluation datasets with `SampleGenerator`**
*Audience: Swift · ~3000 words · evidence: moderate · depends on: `evals-foundations-and-hill-climbing`*

Where most teams will spend their time, and where the API has three non-obvious contracts. The
reality check worth leading with: expanding a dataset from 13 to 100 samples made the scores **drop**,
revealing the feature was never as good as the small dataset suggested.

Sections: `makeSamples(prompt:dataset:targetCount:)` — the simple path · **`targetCount` is the size
of the final dataset including your seeds** (13 seeds + target 100 ⇒ 87 generated) · the full
`SampleGenerator`: `sessionProvider`, `samplingStrategy`, `validator` · **the session-reuse contract**:
the generator calls `sessionProvider` once and reuses the session for continuity, but context
exhaustion mid-run throws and forces a fresh session with no prior context — so your instructions must
be self-contained · random vs sliding-window sampling · the validator runs on **one sample in
isolation**, so corpus-level rules ("reviews must vary in length") are structurally uncheckable there ·
prompt rules are not guarantees; the validator is the only enforcement layer · `samples` and
`invalidSamples` streaming in real time · start with 20–30 hand-written samples; coverage beats count ·
the four hypotheses when scores drop after scaling · running generation from a command-line tool.

Sources: `transcripts/evals-mlx.md` PART 2 (session 299), `web/apple-docs-fm-evals-speech.md`.

---

#### 22. `evals-tool-trajectories`
**Evaluating the path, not just the answer: trajectory expectations and tool-call evaluation**
*Audience: Swift · ~3000 words · evidence: moderate · depends on: `evals-synthetic-data`*

A completely different evaluation modality. The motivating insight: "a model might give you a
reasonable-sounding answer without ever calling the right tool — the final output can look correct
while the path to get there isn't."

Sections: `ToolCallEvaluator` and what it drives · `TrajectoryExpectation(ordered:unordered:
disallowed:allowsAdditionalToolCalls:)` · `ToolExpectation` and `.anyOrder(_:)` groups ·
the nine `ArgumentMatcher` strategies — `.exact`, `.keyOnly`, `.oneOf`, `.range`, `.pattern`,
`.contains`, `.hasPrefix`, `.hasSuffix`, and the LLM-backed `.naturalLanguage(argumentName:criteria:)` ·
`disallowed:` as a test of *negative* instruction following · ordered trajectories catching real bugs
(an agent that fetches details before it has an id) · `TrajectoryExpectation` is itself `Generable`,
so you can synthesize trajectory datasets — but the generating model knows nothing about your tools,
so you must describe each tool, its purpose, and ordering constraints in prose · validation metrics
for synthesized tool samples · stub tools for evaluation · combining output evaluation and trajectory
evaluation in one suite.

Sources: `transcripts/evals-mlx.md` §2.7/§2.8, `web/apple-docs-fm-evals-speech.md`,
`transcripts/fm-ecosystem.md` (246's Spotlight trajectory example).

---

### L5 · Core AI runtime internals

---

#### 23. `coreai-runtime-fundamentals`
**Core AI from the bottom: `AIModel` → `InferenceFunction` → `NDArray`**
*Audience: Swift · ~4500 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

The entry point to everything at L5 and above. Core AI is "the inference framework powering on-device
Apple Intelligence", now public, for neural networks specifically — Apple explicitly routes decision
trees and tabular feature engineering to Core ML. The Swift API is one of the heaviest users of modern
Swift ownership features in the entire SDK, and reading its signatures requires a short primer.

Sections: the framework's scope and its boundary with Core ML · the three-type progressive-disclosure
design · `AIModelAsset` (inspect without specializing) vs `AIModel` (specialized, runnable) ·
`AIModelAsset.isValid(at:)`, `summary(includingStatistics:)`, `Metadata` and the six typed subscripts ·
`AIModel.functionNames`, `functionDescriptor(for:)`, `loadFunction(named:)` (throws on failure,
returns `nil` for an unknown name, and is itself potentially expensive) · `InferenceFunctionDescriptor`:
`inputNames`/`outputNames`/`stateNames` and the asymmetry that there is no `stateCount` ·
`InferenceValue`, `.Descriptor`, and `.Kind` · **`InferenceValue.ndArray` is a *consuming* read**
despite looking like a getter; `Outputs.remove(_:)` is take-once; `NamedMutableViews.take(_:)`
fatal-errors on a second take · `run(inputs:states:outputViews:)` and the `outputViews` fork (outputs
you pre-allocate are updated in place and **omitted** from the returned `Outputs`) ·
`InferenceFunction` is `Sendable` and concurrency-safe — but it silently allocates more scratch to
support concurrency · the Xcode model viewer (General/Functions tabs, `?` for dynamic dims) ·
**the Metal Toolchain build gate** · adding `.aimodel` to Compile Sources · a Swift-ownership primer:
`Span`/`MutableSpan`, value generics `<let rank: Int>`, `InlineArray`, `[n of T]`, typed throws,
`~Copyable`, `consuming`/`borrowing`.

Sources: `web/apple-docs-coreai.md` §2–§8 and §19 (the deep-read anchor), `transcripts/coreai-intro.md`,
`repos/apple-coreai-models.md`, `repos/swift-lm.md` §5.

---

#### 24. `coreai-ndarray-memory-model`
**`NDArray` in depth: shapes, strides, views, preferred layouts, and interleaving**
*Audience: Swift · ~5000 words · evidence: strong · depends on: `coreai-runtime-fundamentals`*

The densest and most error-prone area of the framework, and the place where a wrong assumption costs
a hidden copy on every inference. `NDArrayDescriptor.preferredStrides` exists because specialization
may prefer a **non-contiguous** layout; passing a plain contiguous array "may incur a copy to the
preferred layout." Using the preferred strides means `contiguousElements` returns `nil` and you must
index by dynamically respecting the returned strides.

Sections: the four view types — `View`/`MutableView`/`RawView`/`MutableRawView` — and when each
applies · `Span` vs `MutableSpan` vs `RawSpan` vs `MutableRawSpan` · `contiguousElements` vs
`withUnsafePointer`/`withUnsafeMutablePointer` · `slice(at:)` vs `mutatingSlice(at:)`, and that
unspecified trailing dimensions default to `.all` · `view(as:)` has a default type argument;
`mutableView`/`mutableRawView` are `mutating` · **`NDArray.InterleaveLayout`**, the framework's most
detailed doc page: the block-stride semantics, the exact element-offset formula
`(i[d]/f)*strides[d] + (i[d]%f) + Σ i[k]*strides[k]`, the shape/stride equivalence, and when the
equivalence breaks · **`preferredStrides` as a performance lever** with the full worked pattern ·
`minimumByteCount` for manual allocation · dynamic shapes: `-1` in the API but `?` in the model
viewer; `hasDynamicShape`; `resolvingDynamicDimensions(_:)`; accessing `preferredStrides` on a dynamic
descriptor is a programming error · **the 33-case `ScalarType` zoo**: fp8 E4M3FN/E5M2, MX
`float4e2m1fn`/`float8e8m0fn`, complex, 128-bit ints, sub-byte `int2`–`int7` and `uint1`–`uint7` ·
zero-copy backing from `MTLBuffer` (must be `shared` storage mode) and `IOSurface`, and their explicit
unsafety contracts · image values via `CVMutablePixelBuffer` and `ImageDescriptor` · watchOS
availability cliffs on the Metal-backed initializers.

Sources: `web/apple-docs-coreai.md` §9–§14 (deep-read anchor), `repos/swift-lm.md` §5,
`repos/apple-coreai-models.md` §10.

---

#### 25. `coreai-specialization-caching-and-aot`
**Specialization and caching: the cost model, `AIModelCache`, bookmarks, and `coreai-build`**
*Audience: both · ~5500 words · evidence: strong · depends on: `coreai-runtime-fundamentals`*

The single largest source of first-launch latency, wedged loads, and mysterious disk usage. The `.aimodel`
is a **portable source** representation, not an executable; before it can run it must be specialized to
the device *and* the OS version. Two phases: compilation (the expensive one) and per-compute-unit
artifact generation. The cache key is `(source URL, SpecializationOptions)`, so silently varying
options doubles both storage and specialization cost.

Sections: what specialization actually is, and the two phases · the cache key and why
`SpecializationOptions` being `Hashable` matters · `AIModelCache.default`, `model(for:options:)` as a
non-specializing probe for gating "preparing…" UI · `AIModel.specialize(...)` controls **when**, not
**how much** work · `AIModelCache.Policy` and `PurgeConditions` (`.sourceAssetChangedOrDeleted`,
`.storagePressure`) · OS updates always invalidate every entry regardless of policy ·
`AIModelCache(appGroup:)` + the App Groups entitlement to share specializations across apps/extensions ·
**the bookmark workflow**: `model.bookmarkData` → `UserDefaults` → `AIModel(resolvingBookmark:)` lets
you delete the source `.aimodel` and keep running; bookmarks do *not* pin the entry; malformed
bookmarks throw while stale ones return `nil` · `SpecializationOptions`: `.default`, `.cpuOnly`,
`init(preferredComputeUnitKind:)`, `expectFrequentReshapes`, `ComputeUnitKind.availableKinds` ·
**AOT**: `xcrun coreai-build compile … --platform iOS --min-deployment-version 27.0`, one
`MyModel.<arch>.aimodelc` per architecture, and the **A17 Pro / M1 / M2 hardware gate** · AOT does not
eliminate on-device specialization · **iOS cannot JIT** — loading raw IR on device fails with a
misleading `NSPOSIXErrorDomain Code=2 "No such file or directory"` · the community-measured
export-lowering regression where the *same command* produced a 2.2× slower artifact across an OS
upgrade, and `strings main.mlirb` as the forensic tool · recovery ladder for wedged loads.

Sources: `web/apple-docs-coreai.md` §15–§17 and §20–§21 (deep-read anchor),
`transcripts/coreai-intro.md`, `web/community-blogs.md`, `repos/noema-ios.md` §4,
`repos/issues-coreai-stack.md`.

---

#### 26. `coreai-states-and-kv-cache`
**States: in-place mutable arguments, and the KV cache as a runtime contract**
*Audience: both · ~4500 words · evidence: strong · depends on: `coreai-ndarray-memory-model`*

The highest-leverage performance technique in Core AI, taught end to end across three layers. The
teaching arc is Apple's own: a transformer decode loop whose inference intervals visibly grow in the
Core AI instrument, fixed by turning the KV cache into *state* — an argument the function both reads
and writes in place. Honest hedge: latency still grows, "at a much slower rate", not flat.

Sections: what a state is (`stateNames`, `stateDescriptor(of:)`) and the requirement to supply a
mutable view for **every** state · `InferenceFunction.MutableViews`, `consume`, and why the collections
can't be reused · authoring the cache in PyTorch: `register_buffer` + in-place mutation → mutable
buffers in the exported program → `state_names` at conversion → `MutableBuffers.buffer_mutation` in
the IR · the runtime `states:` argument and the observed IR attribute · fixed-size vs growing caches
and their memory/latency tradeoff · the conventional LLM `.aimodel` signature (`input_ids`,
`position_ids`, mutable `keyCache`/`valueCache`, `logits`), independently confirmed by three separate
projects · why `position_ids` carries the full prefix range in the stateful contract · the
host-cache alternative (caches as ordinary I/O) that exists because the ANE compiler rejects in-graph
indexed KV writes · **the copy-on-write trap**: in-place state updates copy the entire KV/SSM cache
every decode step unless you park a placeholder in the state slot · cross-turn state reuse without a
KV API, via a fed-token log and prefix comparison · quadratic attention made visible in Instruments.

Sources: `transcripts/coreai-intro.md` §3.4, `repos/coreai-torch.md` §12,
`repos/apple-coreai-models.md` §10, `repos/mlx2coreai.md` §11, `repos/noema-ios.md` §4,
`web/apple-docs-coreai.md`.

---

#### 27. `coreai-lowlevel-performance`
**Low-level Core AI: preferred layouts, pre-allocated outputs, and `ComputeStream` pipelining**
*Audience: Swift · ~4000 words · evidence: strong · depends on: `coreai-ndarray-memory-model`, `coreai-states-and-kv-cache`*

The tight-inference-loop tier: three techniques that Apple teased in one sentence and that turn out to
have a complete, readable API. `encode(...)` is **`throws`, not `async throws`** — it returns as soon
as the work is *encoded*, which is what lets you chain stages without awaiting intermediates.

Sections: avoiding the hidden layout-conversion copy with `preferredStrides` · pre-allocating outputs
via `outputViews:` and the resulting change in what `Outputs` contains · `ComputeStream()` vs
`ComputeStream(commandQueue:)` and encoding onto your own Metal queue ·
`encode(inputs:states:outputViews:to:)` and building a multi-stage pipeline ·
`InferenceFunction.AsyncValue` (a `final class`) vs `AsyncMutableValue` (a `struct`) and why the
asymmetry · `AsyncMutableViews` and automatic synchronization when successive encodes mutate the same
value · `currentWorkCompleted()` · `init(unsafeBuffer:)` — `shared` storage mode required, and the
copy-on-read behavior for `MTLBuffer`-backed values · a real production pipeline: pipeline depth 3,
rotating cache-position/output/logits buffers, decode reading its next input token straight out of the
previous step's GPU buffer with no CPU round-trip · **backpressure**: why a `PipelineGate` is
necessary when the decode loop submits ~220 encodes/s and the sampler drains ~70/s · the
empty-command-buffer completion sentinel for ordering guarantees · concurrency raises scratch-memory
footprint silently.

Sources: `web/apple-docs-coreai.md` §4 and §8 (deep-read anchor), `repos/apple-coreai-models.md` §10.5,
`transcripts/coreai-intro.md` §3.5, `repos/swift-lm.md` §5.

---

#### 28. `coreai-llm-inference-engines`
**Four ways to run an LLM on Core AI: pipelined GPU, sequential, static-shape ANE, and VLM**
*Audience: Swift · ~6000 words · evidence: strong · depends on: `coreai-states-and-kv-cache`, `coreai-lowlevel-performance`*

The best-documented real LLM runtime in the corpus, and the guide that explains *why* export shape
determines compute unit. `EngineFactory` auto-detects structure from graph function names **before**
specializing, and the structure then picks both the engine and the `SpecializationOptions`. You do not
choose the compute unit at runtime; your export chose it.

Sections: `InferenceEngine` protocol and `InferenceOptions`/`InferenceOutput` · structure detection
from graph names (`extend*` + `load_embeddings` → chunked-static; `main` → dynamic;
`image_encode`+`text_encode`+`detect` → segmenter) and the derived `SpecializationOptions` ·
the variant × structure compatibility matrix and `unsupportedEngineVariant` ·
**`CoreAISequentialEngine`**: the strict 2-input/1-output/2-state contract read positionally,
CPU-side sampling, `supportsLogits == true` · **`CoreAIPipelinedEngine`**: GPU encode pipelining,
on-device sampling, `supportsLogits == false` — which structurally rules out guided generation and
continuation-based evaluation · **`StaticShapeEngine`**: the exact ANE I/O name contract
(`out_logits`, `key_cache`, `value_cache`), bucketed `extend_<ctx>_<batch>` functions, embedding table
loaded once · **`CoreAISequentialVLMEngine`**: three assets, `EmbeddedInput` scatter-merge at
placeholder positions · `KVCacheStrategy` `.auto`/`.fixedSize`/`.growing`/`.chunked` — with `.chunked`
**not implemented** and `.fixedSize` warned against (multi-GB preallocation *and* slower per-step
decode) · **chunked prefill memory math**: a 32K prompt on a 151,936-vocab model needs a 9.6 GB fp16
logits buffer unchunked vs 155 MB at 512-token chunks · `COREAI_CHUNK_THRESHOLD` · implicit prefix
caching via `TokenHistory` memcmp; why the pipelined engine can't do partial rewind · sampling: CPU
`CompositeSampler` (Accelerate, min-heap top-K, minP in logit space) vs `MPSGraphSampler` (vocab size
and temperature fixed at construction) · the shared-execution-descriptor bug that produced garbled
output at temperature > 0 · stop reasons and cancellation.

Sources: `repos/apple-coreai-models.md` §10–§11 (deep-read anchor), `repos/noema-ios.md` §4,
`repos/issues-coreai-stack.md`, `web/community-blogs.md`.

---

#### 29. `coreai-xgrammar-guided-decoding`
**How `@Generable` is enforced on an arbitrary model: grammar-constrained decoding with xgrammar**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `coreai-llm-inference-engines`, `fm-guided-generation-and-streaming`*

A genuinely deep mechanism that appears in **no** WWDC transcript and no Apple doc, discovered by
reading source: both Apple's `coreai-models` and `mlx-swift-lm` independently reach for `mlc-ai/xgrammar`
to enforce guided generation on non-Apple models. Convergent design, and the honest answer to "how
does structured output work when the model wasn't trained for it."

Sections: why prompt-level schema description is not enforcement · the C bridge surface (14
declarations) and the DLPack `DLTensor` bitmask · `GrammarCompiler.compileJSONSchema` and
`GrammarMatcher` · `ConstrainedGenerationSession` as a `~Copyable` type; `nextTokenBitmask()`,
`applyMask(to:)`, `acceptToken(_:)` · masking to `-.infinity` / `-Float16.greatestFiniteMagnitude`
and the fp16 sentinel choice · dual termination detection (`isTerminated` **or** an all-zeros bitmask) ·
`VocabularyType` (`raw`/`byteFallback`/`byteLevel`) and the default-value mismatch that silently
changes vocab semantics · why constrained decoding requires **per-step logits** and therefore cannot
use the pipelined GPU engine · the FM hand-off: JSON-encoding a `GenerationSchema` and throwing
`unsupportedCapability(.guidedGeneration)` when the engine can't comply · **a confirmed dead
parameter**: `stopTokenIds:` is accepted, documented, and never forwarded — and why that forced
"defense in depth" in the decoder loop · multi-token stop sequences are unsupported · special tokens
leaking into structured output, and the fix.

Sources: `repos/apple-coreai-models.md` §12 (deep-read anchor), `01-lead-agent-repo-spotchecks.md`,
`repos/mlx-swift-lm.md`, `repos/issues-mlx-stack.md`.

---

#### 30. `coreai-bundles-and-fm-bridge`
**Model bundles and `CoreAILanguageModel`: turning an `.aimodel` into a Foundation Models backend**
*Audience: Swift · ~3500 words · evidence: strong · depends on: `coreai-llm-inference-engines`, `languagemodel-provider-package`*

Some models need more than an `.aimodel`: LLMs need a tokenizer, diffusion runs several models in
sequence. The bundle concept appears in no Apple doc but is a de-facto interchange format that at
least three independent projects target. Then the payoff: one line turns that bundle into a
`LanguageModelSession` backend with `@Generable` and streaming intact.

Sections: the `metadata.json` **schema 0.2**: `metadata_version`, `kind` (`llm`/`vlm`/`diffusion`/
`segmenter`), the `assets` role map, the `language` block, `function_map` · the sibling `tokenizer/`
directory and its contents · runtime-family folder conventions (`ios-ane` / `ios-gpu` /
`gpu-pipelined` / `macos`) and why they must be matched on exact path components · hand-editing
`assets.main` after AOT compile · `verify()` and what it does not check ·
`CoreAILanguageModel(resourcesAt:mode:variant:kvCacheStrategy:)`, `LoadMode.lazy`/`.eager`,
`load()`/`unload()`, `estimatedSizeOnDiskBytes` · capability auto-detection from tokenizer probes ·
`LanguageModelSession(model:)` and what survives (same `respond(to:)`, same streaming, same
structured output) and what does not (only `temperature` is forwarded — topK/topP/minP are
unreachable through FM) · streaming detokenization: the U+FFFD multi-byte problem and the
one-token-of-context rule for SentencePiece spacing · reasoning-tag and tool-call parsers with
hold-back windows · pointing `resourcesAt:` at the `.aimodel` instead of its parent yields a
misleading `unsupported metadata_version '0.1'` error.

Sources: `repos/apple-coreai-models.md` §6/§9 (deep-read anchor), `transcripts/coreai-intro.md`,
`repos/noema-ios.md` §4, `repos/mlx2coreai.md`, `repos/issues-community-stack.md`.

---

### L6 · Compiler and conversion

---

#### 31. `coreai-torch-conversion-pipeline`
**PyTorch → `.aimodel`: the conversion pipeline and its non-negotiable contract**
*Audience: Python ML engineer · ~4500 words · evidence: strong · depends on: `coreai-runtime-fundamentals`*

The entry point for everything at L6. There is no `convert()` function: the pipeline is
`torch.export.export` → `run_decompositions(get_decomp_table())` → `TorchConverter` →
`AIProgram.optimize()` → `save_asset()`. The decomposition step is **mandatory** and skipping it
leaves ops with no lowering rule; `to_coreai()` runs **zero** optimization passes.

Sections: install (`pip install coreai-torch` brings `coreai` too) and the naming map
(`coreai-torch`/`coreai_torch`, `coreai-opt`/`coreai_opt`, plain `coreai`) · `.eval()` before export ·
`torch.export` and what an `ExportedProgram` captures · **`get_decomp_table()`**: the default ATen
table minus the ops Core AI lowers as composites; each call returns a fresh copy · `TorchConverter()`,
`add_exported_program` vs `add_pytorch_module` (and when externalization forces the latter) ·
`to_coreai()` is a *pure* conversion; `optimize()` is in-place and its return value is never used ·
**`optimize()` can silently change semantics** — a community-reproduced case where a
broadcast-significant axis move was deleted, costing ~17 dB PSNR; always A/B `optimize=True` vs
`False` · `save_asset()` returns an `AIModelAsset`; the `.aimodel` is a **directory** ·
**multi-entrypoint assets**: several exported programs on one converter with distinct
`entrypoint_name`s, and the measured 76% second-inference win from splitting by cadence ·
running inference from Python (`async with asset.executable()`, `load_function`, `await fn(inputs)`)
and the buffer-lifetime footgun · `SpecializationOptions` is macOS-only in Python ·
numeric-parity verification against the PyTorch original as a required step.

Sources: `transcripts/coreai-python-metal.md` PART 1 (deep-read anchor), `repos/coreai-torch.md`
§4–§7, `01-lead-agent-repo-spotchecks.md`.

---

#### 32. `coreai-torch-op-lowering-and-coverage`
**Op coverage: the lowering registry, what converts, and adding your own lowering**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `coreai-torch-conversion-pipeline`*

The contract nobody reads until conversion fails. Op names are FX-qualified `op_name.overload`, and
"when PyTorch's decomposition pipeline produces a different overload than the one listed, that
overload is not supported" — a classic footgun. Includes the decision tree between tweaking the
decomposition table, registering a lowering, and writing a Metal kernel.

Sections: the resolver key format and the ~180-entry ATen table · the five-level dispatch precedence
(externalized → user lowerings → ATen → custom/`coreai` → higher-order) · the two pre-conversion
validator errors and how to read them · higher-order ops (`cond`, `while_loop`) and their
compute-unit limitation · `register_torch_lowering()`, the `(values_map, node, loc)` callback,
`get_operand`/`get_operands`, multi-result nodes, `allow_override=True`, and the reserved namespaces ·
authoring against the *private* `coreai._compiler.dialects` API and what that means for stability ·
`generate_composite_decl` for emitting a named composite · SDPA lowering specifics: the ATen path
always emits `is_causal=false` and materializes causal masking as a `-1e4` additive mask ·
**silent-miscompile catalogue**: `aten.cat` on packed intx tensors always running on dim 0, int64
accumulators narrowed to int32, negative-axis quantize landing a dimension early, GPU floor/trunc/ceil
executing as identity, cast round-trips folded away · a numerics A/B harness pattern.

Sources: `repos/coreai-torch.md` §8–§9 (deep-read anchor), `repos/issues-coreai-stack.md`,
`transcripts/coreai-python-metal.md`.

---

#### 33. `coreai-torch-composite-ops`
**Composite ops and externalization: preserving RMSNorm, RoPE, SDPA, GatherMM and GatedDeltaUpdate**
*Audience: Python ML engineer · ~7000 words · evidence: strong · depends on: `coreai-torch-op-lowering-and-coverage`*

The main performance lever the framework exposes, and a fact nobody said out loud at WWDC: Core AI
has **first-class MoE and linear-attention/SSM support** via `gather_mm` and `gated_delta_update`.
Marking a well-known building block as a composite lets the compiler recognize it and substitute an
optimized implementation.

The second half of the guide teaches the mechanism from the inside, because the failure modes of
composite ops — silently unmatched specs, non-tensor arguments, optional-argument handling — are only
understandable once you have seen the externalization pipeline. Reassuring invariant: your model is
never left mutated.

Sections: the two categories — module-class composites you build with, vs ATen-derived composites
recognized automatically · the three-step pattern (named submodule → `add_pytorch_module` →
`ExternalizeSpec`) · `RMSNormImpl` (and the trap that `target_class` must be `RMSNormImpl`, never the
`RMSNorm` wrapper), including its deliberate fp32 intermediate and the Gemma3 fp32-scale special case ·
`SDPA`: MHA/GQA/MQA shapes, "do not pre-tile K/V", attention **sinks**, the sliding `window_size`, and
the **lower-right vs upper-left causal mask difference** from `torch.nn.functional` — which matters at
every autoregressive decode step · `RoPE`: the cos/sin resolution priority, hard fp32 requirements on
`position_ids` and `freqs` (fp16 gives wrong generated text), partial rotation, and the
contiguous-vs-half-split pairing discrepancy with HF `partial_rotary_factor` models · `GatherMM` as
the MoE dispatch primitive, with the fused gate+up variant · `GatedDeltaUpdate` and the fact that it
uses `torch.ops.higher_order.while_loop` internally · the ATen-derived composite attribute schemas ·
reading the emitted `#coreai.composite_declaration` IR · upstream-bug workarounds shipped in the
library (`_vanilla_repeat_interleave`, manual lower-right masks). · **externalization internals** · the five phases — mark & re-export, prepare, export submodules, emit IR, restore · the temporary `coreai_torch_ext::` custom ops and how they're registered · **each call site gets its own UUID-suffixed graph** so the runtime cannot deduplicate invocations · automatic composite I/O naming from the graph signature (parameters/buffers first, then user inputs) · why inner submodules are decomposed with the *default* table rather than `get_decomp_table()` · why fake inputs are fresh concrete tensors rather than the parent's `FakeTensor`s · per-call-site dynamic-shape reconstruction · `ExternalizeSpec` matching rules and first-match-wins · **unmatched target classes only warn** — typos and stale references are silent no-ops · marked-but-unreachable submodules are skipped · bare-class "simple externalization" is experimental and buys nothing · the two hard requirements (all forward args that become inputs must be tensors; optionals must be `Tensor | None = None`) · reading the emitted `coreai.graph private noinline` + `coreai.invoke` IR.

Sources: `repos/coreai-torch.md` §10–§11 (deep-read anchor), `transcripts/coreai-python-metal.md` §1.11,
`01-lead-agent-repo-spotchecks.md`.

---

#### 34. `coreai-torch-io-state-and-dynamic-shapes`
**IO naming, state semantics, and dynamic shapes: the contract that breaks on a PyTorch upgrade**
*Audience: Python ML engineer · ~3500 words · evidence: strong · depends on: `coreai-torch-conversion-pipeline`, `coreai-states-and-kv-cache`*

Small surface, enormous footgun density. There is **no opt-out from state**: any in-place mutation of
a registered buffer or a `forward()` argument makes it state. And the default names and `state_names`
ordering are "observed behavior from the FX graph, not a stable contract from PyTorch" — the converter
asserts counts match but "cannot detect silent reordering."

Sections: the two things that count as state, and how to *avoid* state (clone first, or go
out-of-place) · `input_names`/`output_names`/`state_names` and the **breaking change** that IO names
no longer cover state · the default-name table per category · the prescribed `state_names` ordering
(buffers in registration order, then mutated user inputs in signature order) · why you must name
explicitly for production and re-verify on PyTorch upgrades · the `MutableBuffers.buffer_mutation`
IR attribute and why stateful models effectively require `optimize()` · dynamic shapes: `Dim`,
`dynamic_shapes=`, SymInts becoming `?` in Core AI types · **the INT32 slice clamp** (ATen uses
INT64_MAX to mean "to end"; Core AI indices are si32) · symbolic `SymInt` slice arguments are rejected
outright · ops that raise on dynamic values (`max_pool2d` with dynamic stride, transposed conv3d) ·
**int64→int32 and fp64→fp32 narrowing everywhere**, and when that is a correctness bug · sub-byte and
reduced-precision dtypes (`uint1`–`uint6`, `int2`/`int4`, fp8, bf16, packed fp4) · the static-vs-dynamic
export decision as the thing that picks your compute unit.

Sources: `repos/coreai-torch.md` §12–§14 (deep-read anchor), `transcripts/coreai-python-metal.md` §1.5,
`repos/issues-coreai-stack.md`.

---

#### 35. `coreai-numeric-debugging`
**Finding the bad op: Core AI Debugger, sync points, and the `coreai_torch.debugging` toolkit**
*Audience: Python ML engineer · ~4500 words · evidence: strong · depends on: `coreai-torch-conversion-pipeline`*

The most reusable debugging idea in the corpus. **Sync points** are automatically-identified operation
pairs — one from the specialized model, one from PyTorch — whose outputs are expected to match, each
scored by a similarity metric (PSNR by default). Sort by similarity, arrow-key through the worst, and
a pattern emerges. Apple's own worked example turned "one occluded flower stopped being detected" into
a revised quantization scheme in minutes.

Sections: the three-tool triage order — debug gauge → Instruments → Core AI Debugger · the debug gauge
requires the target to link `CoreAI.framework` **directly**, and it is the only entry point to a live
Debugger session and to exporting a specific inference's input tensors (`.npy`/`.npz`) · the
Instruments Core AI template: four bundled instruments, four event categories (Specialization, Load,
Setup, Inference), and the gauge/Instruments discrepancy in both count and colors · frequent Load
events as an explicit bug signal · Core AI Debugger's four panes and the navigator grouped by PyTorch
module · running on a real device for true runtime results · comparison sessions: another target,
another compute unit, or a reference run · **`save_intermediates(program, inputs, output_dir, node_filter=, coreai_program=)`**
and `load_intermediates`, the `.aimodelintermediates` layout, and how `coreai_program=` supplies the
source mapping that powers the source viewer · the preview env gate `USE_LOCAL_COREAI=1` +
`ENABLE_DEBUG_INFO=1` · the rest of `coreai_torch.debugging`, which never appeared on stage: NaN/Inf
bisection validators for both PyTorch and Core AI programs, a cross-framework comparator with
rtol/atol, `CoreAIInspector` for deployed-model intermediates, graph-isomorphism diffing, op-level
benchmarking with module rollups, and three search strategies · `TorchConverter.Mode.DEBUG` is the
**default** and embeds full torch stack traces — use `RELEASE` or `strip_debug_info` for shipping ·
`strip_debug_info` also rescues pre-0.4.1 assets rejected by the OS 27 loader.

Sources: `transcripts/coreai-python-metal.md` §1.10 (deep-read anchor), `repos/coreai-torch.md` §17,
`web/apple-docs-coreai.md` §22–§27, `repos/issues-coreai-stack.md`.

---

#### 36. `model-reauthoring-case-study`
**Re-authoring a model for on-device: the SAM3 case study end to end**
*Audience: Python ML engineer · ~6000 words · evidence: strong · depends on: `coreai-torch-composite-ops`, `coreai-torch-io-state-and-dynamic-shapes`, `coreai-opt-palettization`*

The capstone guide for L6/L7/L8, and the only fully reproducible end-to-end example in the corpus
(the recipe ships in `apple/coreai-models` and can be run with one `uv run` command). Re-authoring
means "a completely different implementation of the source code" targeting a specific compute unit —
different ops, different layouts, different interfaces.

Sections: the model and its parameter distribution (848M; encoders = 96%, detector = 4% — which is
what makes the whole story work) · **the three-function split** (`image_encode`/`text_encode`/`detect`)
and running each at a different cadence, with the measured 76% prompt-swap win · BC1S `(B, C, 1, S)`
layout and the `nn.Linear` → `nn.Conv2d(1×1)` weight surgery · GELU approximated with sigmoid ·
window attention (28 layers, 24×24) plus global attention at four indices · per-function compression:
image encoder 4-bit palettization gs=32, text encoder 6-bit gs=8, detector fp16 with **no** weight
compression · **the discrepancy worth teaching**: the talk says "4-bit to the two encoders", the
shipped recipe is asymmetric · **the `enable_per_channel_scale` trap**: `True` lowers to rank-6 LUTs
that ANE rejects (max rank 5), forcing GPU fallback — so the shipped recipe leaves it off and accepts
a small quality regression · fp16 casting after export, before conversion · resolution reduction
(1008 → 336) for iPhone · the diagnosis loop: aggressive uniform quantization → one occluded flower
lost → Debugger sync points cluster in the detector → exclude the detector via
`module_name_configs = {"detector.*": None}` → baseline quality at a fraction of the size ·
plugging a custom FlashAttention Metal kernel into the same model · the runnable CLI and its flags ·
gated-model and dependency-conflict practicalities (PEP 723 inline script with `override-dependencies`).

Sources: `transcripts/coreai-python-metal.md` §1.6/§1.9/§1.12 (deep-read anchor),
`repos/apple-coreai-models.md`, `repos/coreai-optimization.md`, `01-lead-agent-repo-spotchecks.md`.

---

#### 37. `mlx-to-coreai-bridge`
**MLX → Core AI: capturing an MLX graph and lowering it to `.aimodel`**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `coreai-torch-conversion-pipeline`, `coreai-states-and-kv-cache`*

The other conversion front-end, and the best evidence in the corpus for what Core AI's IR actually
looks like from the outside. It traces MLX with `mx.export_function(callback, …)`, parses the event
stream into a small SSA IR, normalizes and shape-infers, and emits Core AI MLIR — deliberately
reproducing Apple's own macOS LLM contract byte for byte, including `keyCache`/`valueCache` names,
the `(L, B, H, T, D)` cache shape with sequence axis 3, and the same trace constants.

Sections: the capture→IR→normalize→lower→save pipeline · callback tracing vs the legacy DOT path, and
why the callback path preserves primitive state · **the `name_remap` gotcha**: `Sum`/`Prod`/`Min`/`Max`
all arrive as `Reduce`, all bitwise ops as `BitwiseBinary`, `Log2`/`Log10` as `Log` with the base in
state — the single most important fact for understanding the op registry, and the source of three
silent miscompiles (`log2` → natural log, shifts → AND, `argmax` unsupported) · weights as
`DenseResourceElementsAttr` dense resources above a size threshold; there is no separate weight file ·
**dynamic shapes via probe differencing**: capture at two shapes and treat every integer attribute
that changed by exactly the dimension delta as a runtime dimension reference · composite emission for
`rms_norm`/`rope`/`sdpa` as private `no_inline` graphs with `composite_declaration` attributes ·
statefulness via three IR pseudo-ops and the `MutableBuffers.buffer_mutation` argument attribute ·
the `_ExportableLayeredKVCache` duck-type that makes MLX's tracer record a `slice_update` ·
multi-entrypoint support that no converter currently uses · no quantization support anywhere ·
the `coreai-core==1.0.0b1` pin that is below the b2 loader floor · why the project ships a **Swift**
runner: the Python bindings lack preallocated output views, mutable-state ownership, and working
specialization control.

Sources: `repos/mlx2coreai.md` (full), `01-lead-agent-repo-spotchecks.md`, `repos/apple-coreai-models.md`,
`repos/swift-lm.md` (a second, independent Swift→Core AI export contract).

---

### L7 · Quantization and numerics

---

#### 38. `coreai-opt-quantization`
**`coreai-opt` quantization: the config hierarchy, specs, and the GRAPH-vs-EAGER decision**
*Audience: Python ML engineer · ~5500 words · evidence: strong · depends on: `coreai-torch-conversion-pipeline`*

The largest and most error-prone API surface in the compression stack. Everything is config-driven
with a strict three-level precedence — `module_name_configs` (regex) > `module_type_configs` >
`global_config` — and setting any scope to `None` is how you say "leave this alone." That `None` is
exactly the "ignore the detector" mechanism from the SAM3 story.

Sections: install and the `coreai-opt`/`coreai_opt` naming split · the universal compressor lifecycle
(`__init__` → `prepare(example_inputs)` → optional calibration/training → `finalize`) and the rule
that you evaluate the **prepared** model, not the finalized one · the three-level config precedence and
the `None`-disables mechanism · the three op-level tensor groups (`op_input_spec`, `op_output_spec`,
`op_state_spec`) and how weight-only quantization is expressed · `QuantizationSpec`: dtypes
(int2–int8, uint, fp8 E4M3FN/E5M2, packed fp4), `qscheme`, `qformulation` (ZP vs MINVAL), granularity
(per-tensor / per-channel / per-block), `scale_dtype` · the presets `w8`/`w4`/`w4_per_block` and their
exact expansions · the `W_MXFP4_A_FP8` recipe with `block_size=32` + `float8_e8m0fnu` · YAML configs
with anchors · **GRAPH vs EAGER is a correctness fork, not a perf knob**: GRAPH does conv+bn+relu
fusion, shared-observer detection and fake-quant dedup; EAGER does none, so ops like MaxPool get
independent input/output observers "which can cause incorrect quantization" — and the two modes are
explicitly *not guaranteed to produce equivalent models* · reconciling the talk ("EAGER works great
for weight compression") with the repo (GRAPH is the default and the recommendation) · calibration
semantics: observers on, **weight** fake-quant on, **activation** fake-quant off · QAT with
`QATSchedule` and the mandatory `quantizer.step()` · `kv_cache_quant_configs` (graph-mode only) ·
per-channel activation quantization and the shape-aware axis-safety rules around shared observers ·
silent failure modes: mis-configured block sizes disable themselves with only a warning ·
`module_type_configs` keys must be fully-qualified class paths.

Sources: `repos/coreai-optimization.md` §5–§6 (deep-read anchor),
`transcripts/coreai-python-metal.md` §1.7–§1.9, `repos/issues-coreai-stack.md`.

---

#### 39. `coreai-opt-palettization`
**Palettization, pruning, casting, and joint compression**
*Audience: Python ML engineer · ~6500 words · evidence: strong · depends on: `coreai-opt-quantization`*

Lookup-table compression, described by Apple as "well-suited for power efficiency on iOS" and used in
the shipped SAM3 recipe. Contains the single most valuable hardware footgun in the corpus:
`enable_per_channel_scale=True` lowers to rank-6 LUTs, and **ANE's max tensor rank is 5**, so the
runtime silently falls back to GPU.

The guide then covers the parts of `coreai-opt` that never appeared in a session at all: a first-class
pruning module, an fp16/int16 casting pass that operates on the exported program, a PyTorch-free MLIR
path that compresses an already-converted `AIProgram`, and the documented ordering for combining
techniques.

Sections: scalar vs vector palettization and the effective bits-per-weight math
(`n_bits / cluster_dim`) · `PalettizationSpec`: `n_bits ∈ {1,2,3,4,6,8}` (no 5 or 7), `lut_qspec`,
`granularity`, `cluster_dim`, `enable_per_channel_scale` · `PerTensorGranularity` vs
`PerGroupedChannelGranularity` and the divisibility requirement · LUT quantization constraints
(per-tensor only, int8/uint8/fp8 only, FP8 requires symmetric, MINVAL rejected) · the presets
`w4`/`w6`/`w8` and how they differ from what the talk described · **the rank-6 LUT / ANE-rank-5
trap**, verbatim from the shipping recipe's own docstring · sensitivity-weighted k-means (SqueezeLLM):
`calibration_mode(loss_fn=)`, squared-gradient hooks, normalization and clipping, saving/loading
sensitivities across runs · `num_workers` and why the default of 1 is slow on large models ·
non-determinism with `cluster_dim > 1` and why seeding only works at `num_workers=1` ·
`enable_fast_kmeans_mode` rounding · **`finalize(backend=CoreAI)` destroys the original dense weights
in place** · `mmap_dir` (eager + CoreAI + CPU only; files must outlive the model) · palettization
silently disables itself per layer on incompatibility — watch the logs · the emitted `lut_to_dense`
and `constexpr_blockwise_shift_scale` ops, and the community finding that linear blockwise-INT4
SIGSEGVs the ANE pre-compiler while the byte-identical palettized program compiles to 31 ANE regions. · **pruning, casting, and joint compression** · `MagnitudePruner`: unstructured global top-k vs `ChannelStructured` L1 channel ranking · **realized sparsity rounds down to multiples of 1/num_channels** · `ConstantSparsitySchedule` vs `PolynomialDecaySchedule` (formula, `update_frequency`, `begin_step`) and the fine-tuning loop · `coreai_opt.casting`: `cast_fp32_to_fp16`, `cast_int32_to_int16`, `cast_to_16_bit_precision` — they operate on an `ExportedProgram` *after* export and are strictly stronger than `.half()` or `torch.autocast`, with an aggressive FP pass and a conservative INT pass · always compress first, cast second · **joint compression**: palettize → `finalize(CoreAI)` (because `torch.export` cannot trace parametrizations) → `Quantizer` with `op_state_spec=None` → calibrate → finalize; CoreAI-only; the INT8 LUT is what unlocks the W8A8 runtime path · mixed-precision recipes: the sensitivity → greedy → apply workflow and BPW accounting including scale/LUT overhead · **`coreai_opt.coreai_utils`**: a completely PyTorch-free path that walks the MLIR and rewrites `coreai.constant` ops — `quantize_weights`, `palettize_weights`, `sparsify_weights` with n:m structured sparsity and joint sparse+quant · `ModelInspector` as the tool for discovering the exact strings your config needs (op names differ between graph and eager mode) · debugging accuracy loss with intermediate-activation SNR · the CoreML export restriction matrix and its error messages · published accuracy/size numbers.

Sources: `repos/coreai-optimization.md` §7–§14 (deep-read anchor),
`transcripts/coreai-python-metal.md` §1.12, `repos/apple-coreai-models.md`,
`repos/issues-coreai-stack.md`, `01-lead-agent-repo-spotchecks.md`.

---

#### 40. `numeric-formats-cross-stack`
**Numeric formats across the stack: int4 to MX, and who supports what**
*Audience: both · ~3500 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

A reference guide that serves five other guides. The same MX microscaling format runs the entire
height of the stack — `torch.float4_e2m1fn_x2` + `block_size=32` + `torch.float8_e8m0fnu` in
`coreai-opt`; `float4e2m1fn` and `float8e8m0fn` in `NDArray.ScalarType`; `fp8_e8m0` scale planes in
MSL; `mxfp4`/`mxfp8` group-32 in MLX — and knowing that makes every layer legible.

Sections: affine quantization (scale + zero-point/minval), the exact formula, and the packing layout ·
lookup-table palettization and how it differs · what "granularity" means at each layer (per-tensor /
per-channel / per-block / per-grouped-channel) · the MX (OCP microscaling) family: E2M1 elements,
E8M0 shared exponent, 32-element blocks · NVFP4 and its E4M3 scale · fp8 E4M3FN vs E5M2 ·
sub-byte integers down to `uint1`, and the odd widths (`int3`, `int5`–`int7`) that point at
fine-grained schemes · **a cross-stack support matrix**: which formats `coreai-opt` emits, which
`NDArray.ScalarType` names, which the TensorOps matmul dtype table accepts (and the fact that 4-bit
appears only as the **right/weight** operand — there is no int4×int4), which MLX's four modes support,
and which are CUDA-only (`global_scale`) · alignment consequences: sub-byte tensors need 128-byte
stride alignment vs 64 for ML-usage tensors · why quantization shifts activation distributions and can
push previously-safe values over the fp16 threshold · ANE fp16 overflow thresholds for softplus, mish,
logsumexp, and logcumsumexp, and Apple's sanctioned model-side fix.

Sources: `transcripts/coreai-python-metal.md` PART 2 (deep-read anchor), `web/apple-docs-coreai.md` §11,
`repos/mlx-core.md` §10, `repos/coreai-optimization.md`, `repos/issues-coreai-stack.md`.

---

#### 41. `mlx-quantization`
**Quantization in MLX: four modes, `qqmm`, and quantization-aware training**
*Audience: Python ML engineer · ~3500 words · evidence: strong · depends on: `numeric-formats-cross-stack`*

MLX's quantization is the most readable implementation of these formats anywhere, and it now includes
activation quantization. Useful both on its own and as a Rosetta stone for the Core AI side.

Sections: the four modes with their exact defaults — affine (gs 32/64/128, bits 2–8 excluding 7,
scale = input dtype, has bias), mxfp4 (gs 32, E8M0), mxfp8 (gs 32, E8M0), nvfp4 (gs 16, E4M3) ·
the affine formula and the uint32 packing layout · `quantize`/`dequantize`/`quantized_matmul` and
their validation errors · `gather_qmm` as the MoE expert matmul, `sorted_indices`, and the confirmed
M5/NAX corruption when gathered rows exceed 32768 and aren't a multiple of 64 (unwritten rows exposing
stale allocator memory — sometimes coincidentally plausible) · **`qqmm`**: quantizing activations on
the fly; nvfp4 and mxfp8 only; 2-D only; `w` must be non-quantized to receive gradients ·
`to_fp8`/`from_fp8` · `nn.quantize` with class predicates that can return kwargs · `QuantizedLinear`/
`QuantizedEmbedding` are **frozen** on construction · **`QQLinear`** flips its stored weight between
quantized (eval) and dequantized (train) form, enabling QAT · `global_scale` is CUDA-only on the
Metal backend · mxfp8 results are not bit-exact and the tolerance discussion in Apple's own example ·
mixed-precision recipes and learned-quantization CLIs in mlx-lm (DWQ / AWQ / GPTQ / dynamic).

Sources: `repos/mlx-core.md` §10 (deep-read anchor), `repos/mlx-lm.md` §7, `web/mlx-docs-site.md`,
`repos/issues-mlx-stack.md`.

---

### L8 · Metal and ANE hardware

---

#### 42. `ane-and-gpu-authoring-rules`
**Authoring PyTorch for the target compute unit: the ANE rules and their GPU inverses**
*Audience: Python ML engineer · ~6000 words · evidence: strong · depends on: `coreai-torch-composite-ops`*

The densest source of practical hardware knowledge in the entire corpus — Apple's own agent-skill
reference files, ~950 lines of empirical rules. The framing that makes it teachable: almost every ANE
rule has a GPU rule that is its exact **inverse**, so the guide presents them side by side and the
reader learns that "correct on-device PyTorch" is target-dependent, not universal.

Sections: **ANE**: max tensor rank 5 · dtypes fp16/int8/int16 only, and *any* fp32 — including a bare
Python float literal — falls back to GPU/CPU · fully static shapes ("export one function per static
shape config") · the last axis is treated as *width*, must be contiguous and 64-byte aligned, so a
singleton last dim costs 32× memory at fp16 and 64× at int8 · **BC1S** `(B, C, 1, S)` with exact
permute/reshape recipes · `nn.Conv2d(1×1)` instead of `nn.Linear`, with the weight-conversion helper ·
transpose bookkeeping at every projection site as a source of silent correctness bugs · prefer
high-level ops (`nn.LayerNorm`, `nn.RMSNorm`) over hand-decomposed equivalents · softmax on the channel
dim · convolution strides that factor into 2s and 3s · the causal mask shaped `(1, key, 1, query)`
with `-40000.0` rather than IEEE `-inf` · KV cache must return **post-RoPE** keys or PSNR collapses to
~20 dB · per-head attention via einsum · **GPU**: standard `(B, S, D)` layouts, `nn.Linear`, a single
fused SDPA processing all heads in parallel, fused QKV and QK-norm/RoPE, up-before-gate MLP ordering,
stateful KV via `mutable_slice_update`, MoE via `SwitchLinear`/`SwitchGLU`/`GatherMM` with stacked
expert weights, meta-device + per-layer safetensors streaming for 7B+ models · **the verification
gates**: re-authored vs source > 70 dB, ANE layout vs GPU layout > 70 dB, compiled vs torch ≥ 40 dB,
post-4-bit-palettization ≥ 35 dB · bottom-up authoring order (norm → projections → attention → MLP →
block) with per-primitive verification · the architecture-discovery phase ("run code, don't read code";
`register_forward_hook`) · a PSNR-driven failure-signature catalogue.

Sources: `01-lead-agent-repo-spotchecks.md` (the skills deep-read), `transcripts/coreai-python-metal.md`
§1.12, `repos/apple-coreai-models.md` §15, `repos/issues-coreai-stack.md`,
`repos/issues-community-stack.md`.

---

#### 43. `coreai-custom-metal-kernels`
**Custom Metal kernels in Core AI: `TorchMetalKernel` end to end**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `coreai-torch-op-lowering-and-coverage`*

Where the compiler layer meets the hardware layer. You author a **pair** — a PyTorch reference used
only for shape inference during `torch.export`, and an MSL body — and Core AI binds them and embeds
the MSL directly in the asset. "The kernel travels with the model."

Sections: the pair-authoring model and what `torch.export` actually sees · the constructor:
`name`, `input_names`, `result_names`, `src` (the **body** only — signature, buffer bindings and
`#include <metal_stdlib>` are generated), `torch_defn`, `metal_params`, `helper_src`,
`template_dtypes` · `MetalParameter` and Metal thread attributes · **`result_shapes` is required at
every call site** so Core AI can bake output-shape computation for dynamic inputs ·
`register_custom_kernels()` must run **before** `add_exported_program()` · construction-time validation
of `torch_defn` annotations and parameter counts (`TypeError`/`ValueError`) · dtype templating with a
placeholder replaced by the Metal type at compile time · multiple outputs · inside `src`, tensors are
Metal *tensor* objects exposing `.get_extent(i)` and multi-index subscripting, not raw pointers ·
`helper_src` as the home for type aliases and TensorOps includes · scalar arguments baked as literals
and bool widened to `ui8` · the emitted `coreai.metal4_kernel` IR with `hw_constraints` · runtime
inputs must be `StorageKind.METAL`-backed · a malformed MSL body converts fine and only fails at
`load_function` · the experimental-API warnings on `coreai.authoring` and `coreai._compiler` · the
worked SiLU example and the FlashAttention integration (monkey-patching the HF attention
implementation to call your kernel).

Sources: `transcripts/coreai-python-metal.md` §1.11 (deep-read anchor), `repos/coreai-torch.md` §15.

---

#### 44. `tensorops-matmul2d`
**TensorOps from scratch: `matmul2d`, execution scopes, and tiling**
*Audience: Metal / kernel author · ~4500 words · evidence: strong · depends on: `numeric-formats-cross-stack`*

The bottom of the stack. TensorOps is a Metal Shading Language API that "automatically uses any
available hardware acceleration across all Apple Silicon GPU generations" — including the M5 neural
accelerator, a new block inside each shader core aimed at dense compute-bound work such as LLM
prefill. Ground truth exists in the shipped SDK header, so this guide can be exact.

Sections: where TensorOps sits (Core AI and MLX → MPS → MPP + TensorOps) and the three stated reasons
to drop to this level · the namespace `mpp::tensor_ops`, the include line, and the
`__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2` feature gate · `matmul2d_descriptor`: `m`/`n`/`k`
(with `dynamic_extent` meaning "read K from the tensor"), `transpose_left`/`transpose_right`,
`relaxed_precision`, and **the `mode` default of `multiply`, not `multiply_accumulate`** — the header's
own examples assume C is pre-zeroed · the three execution scopes (`execution_thread`,
`execution_simdgroup`, `execution_simdgroups<N>`), the requirement that `run()` calls be
execution-scope **uniform**, and the undefined behavior when the dispatched SIMD-group count doesn't
match · fragment shaders support only `execution_thread` · host-side dispatch pairing via
`threadExecutionWidth` · the four descriptor tags (`handle`, `offset`, `inline`, `none`) and three
address spaces · `slice()` per threadgroup vs bounds-check-free `static_slice<...>` for interior tiles,
and the measured perf argument for both · the full supported dtype matrix, and the observation that
4-bit appears only as the right operand · a real production call site from MLX's own GEMM kernels,
with its fragment layout constants.

Sources: `transcripts/coreai-python-metal.md` PART 2 §2.1–§2.2 (deep-read anchor, cross-verified
against the Xcode SDK headers), `repos/mlx-core.md` §20.

---

#### 45. `tensorops-cooperative-tensors`
**Cooperative tensors, reductions, and building FlashAttention**
*Audience: Metal / kernel author · ~5000 words · evidence: strong · depends on: `tensorops-matmul2d`*

The advanced half, and the guide almost nobody else will write. A cooperative tensor **owns**
thread-private data distributed across the threads of an execution scope, which is what lets you do
softmax, bias, and activation in registers instead of round-tripping through threadgroup memory.

Sections: what a cooperative tensor is, and how it differs from the three non-owning wrapper tags ·
the accessor API: `get_capacity()`, `get_mask(i)` (not all elements are valid — always guard),
`operator[]`, `get_multidimensional_index(i)`, `load`/`store`, `begin`/`end`, `map_iterator` ·
`#pragma unroll full` described as "imperative for performance" · in-register post-processing as the
core motivation · **the three-tier dequantization decision tree**: feed quantized tensors straight to
TensorOps (hardware dequant) > dequantize into a cooperative tensor (registers only) > dequantize into
threadgroup memory and wrap as an inline threadgroup tensor · `reduce_rows`/`reduce_columns`,
`reduction_operation`, and **the identity-default footgun**: `identity` defaults to `sum_identity`
even when `op` is `max`, so you must pass `-INFINITY` explicitly · the row/column reduction destination
factories so you never guess the shape · `map_iterator` for bridging two differently-shaped cooperative
tensors, and `is_iterator_compatible` — a second compatibility check the talk never mentions, with a
documented threadgroup fallback · **feeding a cooperative tensor directly into a matmul**:
`get_left_input_cooperative_tensor(src)`, and the mandatory `is_compatible_as_left_input` /
`is_compatible_as_right_input` guard ("either way, the call to `op.run` is the same") · the SDK-vs-talk
availability discrepancy worth flagging · a full FlashAttention skeleton: per-SIMD-group scope so each
group owns complete rows, Q@Kᵀ into a cooperative tensor, row max, in-register softmax, row sum,
then P@V.

Sources: `transcripts/coreai-python-metal.md` PART 2 §2.3–§2.5 (deep-read anchor, cross-verified
against `MPPTensorOpsMatMul2d.h`), `repos/mlx-core.md`.

---

#### 46. `metal-tensors-and-scale-planes`
**`MTLTensor`, quantized data types, and MX scale planes**
*Audience: Metal / kernel author · ~3000 words · evidence: moderate · depends on: `numeric-formats-cross-stack`*

The host-side half of the hardware story, and the guide that must be most careful about what is
verified. The headline iOS/macOS 27 feature — a single `MTLTensor` carrying its scales as an
additional plane — is confirmed by transcript and corroborated by the rest of the stack, but the exact
Objective-C/Swift spellings do **not** appear in the Xcode 26 SDK and must be marked unverified.

Sections: `MTLTensorDescriptor` (dimensions, strides, dataType, usage, storage/cache modes) and
`MTLTensorExtents`, `MTL_TENSOR_MAX_RANK 16` · creating tensors from a device or a buffer ·
`MTLTensorUsage` including `.machineLearning` · the `MTLTensorDataType` enum and the precise
availability pin (`Int4`/`UInt4` gated at `macos(26.4), ios(26.4)`, which dates "an update to macOS
and iOS 26") · **the alignment rules** — the concrete answer to "check the documentation":
`strides[0]` must be 1; with ML usage `strides[1]` is 64-byte aligned; for sub-byte dtypes every
`strides[i>=1]` is 128-byte aligned · host-side data movement (`replaceSliceOrigin:` /
`getBytes:fromSliceOrigin:`) · **scale planes**: a plane descriptor with `dataType` and `blockFactors`,
an auxiliary plane map tagging it as scales, attached to the tensor descriptor · the 32×1 block giving
32 elements per scale · slicing slices data and scale planes together according to block size ·
kernel-side type aliases and `tensor_handle` vs `tensor_inline` construction on the shader stack ·
corroboration of the E8M0/block-32 story from `coreai-opt` and MLX · an explicit list of what is
unverified pending an Xcode 27 SDK.

Sources: `transcripts/coreai-python-metal.md` §2.2 (deep-read anchor), `repos/mlx-core.md`,
`repos/coreai-optimization.md`.

---

### L9 · MLX as a parallel stack

---

#### 47. `mlx-lazy-eval-compile-streams`
**MLX's execution model: lazy evaluation, unified memory, streams, and `mx.compile`**
*Audience: Python ML engineer · ~5000 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

The mental model that makes everything else in MLX make sense, and the one that transfers directly to
reasoning about Core AI. You never move arrays to devices; you place *operations* via `stream=`, and
MLX auto-inserts cross-stream dependencies.

Sections: the record-then-eval model and every implicit evaluation trigger (print, numpy conversion,
memoryview, `.item()`, any save, scalar-array control flow) · graph-size guidance and
`MLX_BFS_MAX_WIDTH` · **the partial-evaluation trap**: `print(loss)` before `mx.eval(loss, params)`
computes only the forward pass · unified memory and per-op stream placement, with the measured 2× win
from splitting a matmul (GPU) from a 500-iteration loop (CPU) · `Stream` vs `ThreadLocalStream` and
thread-affinity rules · `mx.compile`: the simplify and fuse passes, the exact fusable primitive set
(element-wise/broadcast only — never matmul or reduction) · the four recompilation triggers and what
`shapeless=True` does and does not exempt · compiled functions must be pure; captured arrays become
frozen constants unless declared with `inputs=`/`outputs=` · the canonical
`@partial(mx.compile, inputs=state, outputs=state)` training step, including `mx.random.state` for
dropout · the shapeless mis-specialization footgun (`x.shape[0]*x.shape[1]` bakes in the first shape) ·
measured speedups · memory management: active vs peak vs cache, `set_memory_limit`/`set_cache_limit`/
`set_wired_limit`, and the fact that **`get_peak_memory()` tracks active only** and can undercount by
2–60× · the 499000 live-buffer count limit and the two ways to hit it without leaking bytes.

Sources: `web/mlx-docs-site.md` (deep-read anchor), `repos/mlx-core.md` §3–§7,
`repos/issues-mlx-stack.md`.

---

#### 48. `mlx-fast-kernels-and-numerics`
**`mx.fast`, fused-kernel coverage, and numerical reproducibility on Apple silicon**
*Audience: Python ML engineer · ~4500 words · evidence: strong · depends on: `mlx-lazy-eval-compile-streams`*

Two subjects that belong together because both are about *silent* behavior. MLX's fused SDPA coverage
is narrow and the fallback is silent — there is no log, no env var, and no predicate to query it — and
separately, TF32 and the NAX kernels change numerics without changing any API.

Sections: `rms_norm`, `layer_norm`, `rope`, `scaled_dot_product_attention` signatures ·
RoPE gotchas (exactly one of `base`/`freqs` must be `None`; per-batch offsets; `traditional`) ·
SDPA semantics: GQA/MQA without pre-tiling, softmax always in float32, `"causal"` uses **lower-right**
alignment, attention sinks · **the exact fused-kernel routing tables**: vector path (`T_q <= 8`)
accepts head dims {64, 96, 128, 256} plus (192, 128); full path accepts {64, 80, 128} — so Gemma 4's
d=512 global layers never fuse at prefill and Qwen3VL's d=72 vision tower never fuses · the fused
kernel is bypassed entirely during training on Metal · what the fallback materializes, and the
transient-memory formula · `MLX_SDPA_BLOCKS` and its must-be-a-multiple-of-32 requirement ·
**`MLX_ENABLE_TF32` defaults to 1**, is read once at first use, is inert before GPU generation 17 and
active on M5/A19 with macOS ≥ 26.2 — and it affects any unfused attention path because those are built
from GEMMs · `is_nax_available()`: the build gate (Metal ≥ 4, SDK ≥ 26.2, deployment target ≥ 26.2)
and the runtime gate (OS ≥ 26.2 and architecture generation ≥ 17, ≥ 18 for phone-class GPUs) ·
the architecture-suffix taxonomy (`p`/`g`/`s`/`d`) and per-class command-buffer limits ·
batch-vs-single divergence and why a strict `rtol=1e-5` equivalence assertion cannot hold on
generation-17 hardware · what tolerances to write into tests.

Sources: `repos/mlx-core.md` §9 and §20 (deep-read anchor), `repos/issues-mlx-stack.md`,
`web/mlx-docs-site.md`.

---

#### 49. `mlx-custom-kernels-and-extensions`
**Extending MLX: `mx.fast.metal_kernel`, custom primitives, and C++ integration**
*Audience: Python ML engineer / kernel author · ~4500 words · evidence: strong · depends on: `mlx-fast-kernels-and-numerics`*

The other custom-kernel API in the stack, worth reading alongside `TorchMetalKernel` because the two
solve the same problem with different ergonomics. MLX generates the signature from four sources and
injects shape/stride/ndim identifiers only if they appear in your source.

Sections: `mx.fast.metal_kernel(...)` returns a callable; the constructor and call parameters ·
the signature-generation rules and the generated code you can inspect with `verbose=True` ·
`template=[("T", dtype)]` for dtype specialization · Metal attributes become function arguments (all
of MSL spec Table 5.8) · `ensure_row_contiguous=False` plus the auto-injected shape/strides and
`elem_to_loc` · **`compile_options={"math_mode": ...}`**: `"safe"` is the default and preserves
`exp(-inf) == 0`, which masked/causal softmax depends on · **`atomic_outputs=True` + `init_value`**
for backward passes, with `simd_sum` pre-reduction and the measured 40× VJP speedup · the perf note
that constructing a kernel builds a new Metal library — hoist it out of hot loops · `grid` is in
**threads**, not threadgroups · `mx.fast.cuda_kernel` and `precompiled_cuda_kernel` (PTX/cubin) ·
custom `Primitive`s in C++: `eval_cpu`/`eval_gpu`/`jvp`/`vjp`/`vmap`, the Metal command-encoder API,
`mlx_build_metallib`, nanobind bindings, and setuptools packaging · consuming MLX from a plain CMake
C++ project via `python -m mlx --cmake-dir` · Metal capture and shader `os_log` debugging.

Sources: `repos/mlx-core.md` §9.4, §20.3, §21–§22 (deep-read anchor), `web/mlx-docs-site.md`,
`repos/mlx-examples.md`.

---

#### 50. `mlx-lm-caches-and-prompt-caching`
**KV caches in mlx-lm: ten cache types, trimmability, and prompt caching**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `mlx-lazy-eval-compile-streams`*

Ten distinct cache classes exist and the differences are load-bearing: trimmability gates speculative
decoding and prefix reuse, and quantized KV *raises* peak memory during prefill while lowering it
during decode.

Sections: the ten classes and a decision table · trimmability: which caches support it, and
`RotatingKVCache` becoming permanently untrimmable once its window wraps · `to_quantized` presence
does not imply implementation (`hasattr` guards do not save you) · quantized KV as a **capacity**
lever, not a throughput one — measured decode cost and near-identical quality · **why quantized KV
raises prefill peak memory 30–73%**: the unfused quantized attention path materializes
chunk × context scores; reduce `prefill_step_size` as the mitigation · `quantized_kv_start` differs
between the library default (0) and the CLI default (5000) · prompt caching to disk: the safetensors
format with class names and `meta_state`, the model-name check, and the `<query>` chat-template
stripping trick · server-side prefix reuse: `LRUPromptCache` over a token trie serving exact,
prefix, and *rewound-longer* hits, with category-aware eviction so system-prompt caches survive
longest · segmenting a chat prompt into system / user / thinking-tail so each is cached separately ·
correctness hazards in prefix reuse.

Sources: `repos/mlx-lm.md` §5 (deep-read anchor), `repos/issues-mlx-stack.md`, `web/mlx-docs-site.md`.

---

#### 51. `mlx-lm-server-and-agents`
**Running `mlx_lm.server`: continuous batching, tool calling, and local agentic workflows**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `mlx-lm-caches-and-prompt-caching`*

The four-layer local agentic stack (MLX → MLX-LM → MLX-LM Server → agent), and the practical path to
pointing Xcode's own AI at a locally hosted model. Also the bridge back to Foundation Models via
`ChatCompletionsLanguageModel`.

Sections: the four layers and what each owns · `mlx_lm.server` flags and the OpenAI-compatible surface ·
**continuous batching**: `BatchGenerator` with separate prefill and decode batches, and why it matters
for parallel subagents · the batchability killers (`seed`, draft models) · tool calling: ten
model-specific parsers auto-selected by substring-matching the chat template, and the text-level
state machine that replaced token-level matching · reasoning models and the `reasoning` field
deviation from OpenAI · connecting agents: OpenCode, and Xcode 27's Settings ▸ Intelligence ▸ Add
Chat Provider ▸ Locally Hosted · **connecting to Foundation Models**: `ChatCompletionsLanguageModel`
turns any OpenAI-compatible server — including this one — into a `LanguageModelSession` backend, with
the hardcoded `v1` path caveat · M5 Neural Accelerators and why agentic sessions are prefill-dominated ·
production failure modes: idle core spin, livelock with live GPU work that defeats both `is_alive()`
and per-iteration heartbeats, and delivery-staleness as the correct liveness signal ·
`CVE-2026-5843` / `trust_remote_code` and safe-by-default loading · the "not recommended for
production" security caveat.

Sources: `transcripts/evals-mlx.md` PART 4 (session 232), `repos/mlx-lm.md` §6,
`repos/foundation-models-utilities.md` §3, `repos/issues-mlx-stack.md`.

---

#### 52. `mlx-swift-on-device`
**MLX Swift on device: model containers, generation, and the Foundation Models bridge**
*Audience: Swift · ~5000 words · evidence: strong · depends on: `mlx-lazy-eval-compile-streams`, `languagemodel-provider-package`*

The Swift half of MLX, which in 2026 became the reference implementation of a third-party
`LanguageModel` provider — small enough to read, and the best worked example in existence of
conforming a runtime to Apple's protocol.

Sections: the 3.x redesign that decoupled tokenizer and downloader packages into protocols, and the
`MLXHuggingFace` macros (`#hubDownloader`, `#huggingFaceTokenizerLoader`,
`#huggingFaceLoadModelContainer`) · `ModelContainer`/`ModelContext` and the Swift 6 concurrency model ·
`ChatSession` and the generation event stream · `TokenIterator`, prefill in `init`, and carrying
`LMOutput.State` across turns · KV cache ownership: why `maybeQuantizeKVCache` taking `inout [KVCache]`
silently loses context after `quantizedKVStart`, and why `MLX.compile` freezes a Swift `Int` cache
offset into the graph · speculative decoding (draft-model and MTP) and the trimmable-cache requirement ·
tool calling: ten wire formats, auto-detection, the streaming processor · **`MLXFoundationModels`**:
declaring capabilities, transcript conversion, schema conversion, and grammar constraints via the same
xgrammar the Core AI stack uses · wired memory coordination for concurrent inference ·
`Memory.cacheLimit`/`memoryLimit`/`snapshot()` and the increased-memory-limit entitlement ·
**SDK gating**: `#if FoundationModelsIntegration && canImport(FoundationModels, _version: 2)`, and why
`@available` alone is insufficient · testing (`swift test` does not work; use `xcodebuild`) · the
four-hop fix-propagation chain mlx → mlx-c → mlx-swift → mlx-swift-lm.

Sources: `repos/mlx-swift-lm.md` (full, deep-read anchor), `repos/mlx-swift-examples.md`,
`01-lead-agent-repo-spotchecks.md`, `repos/issues-mlx-stack.md`.

---

#### 53. `mlx-distributed`
**Distributed MLX: ring, JACCL over Thunderbolt RDMA, MPI, and NCCL**
*Audience: Python ML engineer · ~4000 words · evidence: strong · depends on: `mlx-lazy-eval-compile-streams`*

The layer where a model larger than any single machine becomes runnable — a 1.6-trillion-parameter
model needs over 800 GB for weights alone, exceeding even a 512 GB Mac. Also the 2026 headline:
Thunderbolt RDMA.

Sections: the four backends and how to choose · `mx.distributed.init(strict:backend:)` and its
**sticky** semantics (the first successfully initialized backend wins all later bare calls) ·
collectives are silent no-ops at group size 1, so a single-process run looks like it works ·
`mlx.launch` and `mlx.distributed_config` flags; hostfile schemas per backend · **JACCL**: RDMA over
Thunderbolt 5, macOS 26.2+, a fully connected mesh, and `rdma_ctl enable` which must be run from macOS
Recovery and cannot be done remotely even with sudo; verify with `ibv_devices` · `MLX_METAL_FAST_SYNCH`
described as "pretty critical for low-latency communication" · running without `mlx.launch` via the
documented env-var contract · ring backend supports only neighbor send/recv · **tensor parallelism**:
`AllToShardedLinear` shards outputs without gathering, `ShardedToAllLinear` shards inputs and does
all-sum — and the asymmetry is what lets them compose without an intermediate gather; the Llama
attention+FFN sharding recipe · **data parallelism** and `nn.average_gradients` · `nn.fsdp_apply_gradients`
(reduce-scatter → clip → local step → all-gather) and its divisibility constraints · known fragility:
spinning receives on peer loss, silent socket-thread death, GPU lockups under fast-synch.

Sources: `web/mlx-docs-site.md` (deep-read anchor), `repos/mlx-core.md` §18,
`transcripts/evals-mlx.md` PART 4, `repos/issues-mlx-stack.md`.

---

### L10 · Adjacent surfaces

---

#### 54. `speech-on-device`
**`SpeechAnalyzer`: the modern speech-to-text pipeline, transcribers, and asset lifecycle**
*Audience: Swift · ~5000 words · evidence: strong · depends on: `stack-layer-map-and-version-gating`*

The other on-device model framework in the 2026 stack, with a genuinely subtle lifecycle. The trap
that catches everyone: terminating your input `AsyncStream` does **not** finish the session — result
streams only terminate when you call a finish method or deallocate the analyzer.

Sections: the analyzer + modules architecture and the eight-step pipeline · the 2026 additions:
`AssetInputSequenceProvider` (files), `CaptureInputSequenceProvider` (mic/`AVCaptureSession`), and
`AnalyzerInputConverter` — which replace hand-installing audio-engine taps · `analyzeSequence`,
`start`, `finalize(through:)`, `finalizeAndFinish(through:)`, `cancelAndFinishNow()` and the
finish-state semantics · `SpeechAnalyzer.Options`: priority, `ModelRetention`, `ignoresResourceLimits`
and Apple's warning about "an unpredictable error" at real hardware limits · the simultaneous-analyzer
cap and `SFSpeechError.insufficientResources` · **the analyzer performs no audio conversion** (to keep
`CMTime` sample-accurate), so you must use `bestAvailableAudioFormat(compatibleWith:)` — which returns
`nil` until assets are installed, meaning assets come first · `SpeechTranscriber` vs
`DictationTranscriber`: different platform matrices, different presets, different options, and only
`DictationTranscriber` takes content hints and custom vocabularies · both preset matrices ·
volatile vs finalized results and the two documented merge strategies · time-range and confidence
attributes on `AttributedString` · `SpeechDetector` as a VAD gate (its result stream reports errors,
not speech events) · asset lifecycle: `AssetInventory`, installation requests that return `nil` when
already installed, locale reservations and `maximumReservedLocales`, and system-managed shared assets ·
custom vocabularies via `SFCustomLanguageModelData` and X-SAMPA pronunciations · the cancellation-shield
subtlety in display tasks · **no new TTS/expressive-voice API exists** despite the keynote — do not
invent coverage.

Sources: `web/apple-docs-fm-evals-speech.md` (Speech sections, deep-read anchor),
`00-ORIENTATION-lead-agent.md` §7, `forums/forum-pain-points.md`.

---

#### 55. `dnikit-data-introspection`
**DNIKit: dataset and network introspection before you ship a model**
*Audience: Python ML engineer · ~4000 words · evidence: moderate · depends on: `stack-layer-map-and-version-gating`*

The upstream, pre-conversion tier: finding duplicate, rare, and mislabeled data, and finding redundant
network capacity, *before* you compress and convert. Must be introduced honestly — DNIKit is
effectively dormant (last release 2023, one commit since), its PyPI build is broken with Keras 3, and
it has no Core AI or MLX backend. Its value is the pipeline architecture and the algorithms.

Sections: the Producer → PipelineStage → Introspector model and strict lazy evaluation · the `Batch`
container: fields, snapshots, metadata, and the three standard metadata keys · writing a custom
Producer, and **the escape hatch that matters here** — for unsupported frameworks (MLX, Core AI, JAX)
you write a Producer that yields already-computed model responses · debugging with `peek_first_batch`
and `PipelineDebugger` · **PFA** for network compression: the eigen-spectrum of the response
covariance, the three strategies (KL, Energy, Size), unit selection, and the fact that it emits a
*recipe* you must retrain against — with the published VGG-16 compression/accuracy numbers · **IUA**
for dead units · **Familiarity**: GMM density over PCA-reduced embeddings, the two-phase fit-then-score
pattern, and the train/test likelihood-ratio thresholds as a distribution-shift heuristic ·
**Duplicates**: annoy + per-column L2 normalization + transitive closure, with Slope and Percentile
threshold strategies · `DimensionReduction` and the canonical PCA(1024→40) → UMAP(→2) recipe ·
`DatasetReport` and its Symphony-compatible column contract · memory characteristics (which
introspectors stream and which accumulate) · the install matrix and its real landmines · where this
sits relative to the Evaluations framework.

Sources: `repos/dnikit.md` (full, deep-read anchor).

---

## Coverage gaps — where evidence is thin and more research is needed

1. **The Evaluations framework has no local Apple doc coverage in parts of the corpus.** Several
   signatures (`ScoringMode` cases, the `evaluators` result-builder's `buildEither`, the results-bundle
   type name, `aggregateValue`'s argument type) are reconstructed from spoken narration. Verify against
   the real Xcode 27 module interface before publishing guides 19–23.
2. **The iOS/macOS 27 `MTLTensor` scale-plane API is entirely unverified.** The plane-descriptor type,
   `blockFactors`, the auxiliary plane map, and the E8M0 `MTLTensorDataType` case do not appear in the
   Xcode 26.6 SDK. Guide 49 must mark them as such, and someone should re-harvest against Xcode 27.
3. **`coreai-build`'s full CLI surface is unknown.** Only `compile` with four flags is attested;
   `--architecture h18p` and `--preferred-compute neural-engine` come from community sources. The
   enumeration of `deviceArchitectureName` values is likewise undocumented. Needs a machine with
   Xcode 27 + Metal Toolchain.
4. **No error type is documented for Core AI's throwing paths.** `AssetError` covers asset operations
   only; nothing covers `AIModel.init`, `loadFunction`, `run`, `encode`, or cache deletion. Guide 24
   currently cannot tell readers what to catch.
5. **The core Foundation Models framework's open-sourcing has no repo.** Session 241 announced it;
   searches found only `foundation-models-utilities`, `python-apple-fm-sdk`, and `coreai-models`.
   Guide 1 must flag this as unresolved rather than asserting it.
6. **Custom adapters were discontinued in OS 27**, confirmed twice by Apple staff, but the migration
   path (Core ML or Core AI + Background Assets) has no worked example anywhere in the corpus. Guide 5
   can only gesture at it.
7. **MSL-side scale-plane and new-27 element-type spellings** (fp4/fp8/int2 in `__tensor_ops_datatype`),
   `map_iterator`'s real argument, and the `tensor_inline` constructor's parameter list are all
   unresolved. Affects guides 47–49.
8. **The FlashAttention and SiLU MSL bodies from session 330/325 were shown but never read aloud.**
   The "TensorOps sample code" download presumably contains them; without it, guide 48's kernel is a
   reconstruction.
9. **The Core AI Debugger has no hands-on account anywhere** — all community coverage restates the
   docs. Guide 37's Debugger sections need someone to actually run it, including the list of
   selectable similarity metrics beyond PSNR and what targets appear in scheme settings.
10. **`AIProgram.optimize()`'s parameters and pass catalogue are unknown**, and it is now known to be
    capable of silent miscompiles. Guide 32's A/B advice is sound but the mechanism is opaque.
11. **PCC image input** is implied by one transcript line but corroborated by no doc, and separate
    image quotas/costs are unaddressed. Affects guides 4 and 11.
12. **Speech synthesis / expressive TTS is a genuine corpus gap.** The WWDC26 keynote announced a
    second-generation on-device model with better speech generation; Apple staff confirmed on the
    forums that **no new API exists**. Do not manufacture coverage.
13. **Several MLX numbers are community-measured, not Apple-official** (Core AI vs MLX throughput,
    thermal retention, energy per token, fork speedups). Guides 51 and 55 must attribute them
    explicitly and note the Debug-vs-Release contamination that inflated at least one headline.
14. **DNIKit's current Keras 3 compatibility is unverified** — the fix is on `main` only, the PyPI
    build is broken, and `main`'s own test suite reportedly fails from dependency drift. Guide 58 must
    state status before API.
15. **The 2M-download PCC eligibility gate's Small Business Program condition rests on secondary
    sources**, not a transcript quote. Recommend one more direct confirmation from Apple's entitlement
    application page before guide 4 publishes eligibility advice.
