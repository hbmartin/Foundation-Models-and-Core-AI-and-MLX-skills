# Proposed guide series — organized by developer task and journey

> **Status 2026-08-01:** historical input to the merged proposal. Its 2026-07-27 counts and open
> questions are intentionally frozen; use the current `guides/` tree and operational notes for
> completion state.

**Synthesized:** 2026-07-27
**Lens:** organize by *what the reader is trying to do*, not by which Apple framework owns the API.
The target reader has a job (get a model on a phone; make a chat feature; stop the crashes) and does
**not** yet know whether the answer is Foundation Models, Core AI, MLX, or Core ML.
**Corpus:** 28-agent sweep — 6 WWDC26 transcript themes, 18 repo deep-dives, 4 web/doc harvests,
1 forum harvest, plus 3 lead-agent grounding files. ~63k lines of notes.

---

## Landscape in one page

Four product lines that, as of WWDC26, stopped being alternatives and became **layers**:

```
      ┌──────────────────────────────────────────────────────────────────────┐
 API  │  FoundationModels — LanguageModelSession                             │
 tier │    Dynamic Profiles · @Generable · Tools · Transcript · Evaluations  │
      └───────────────────────────┬──────────────────────────────────────────┘
                                  │  `LanguageModel` protocol (NEW 2026)
      ┌───────────────────────────┴──────────────────────────────────────────┐
Model │ SystemLanguageModel │ PrivateCloudCompute │ CoreAILanguageModel │     │
 tier │ (on-device 4K)      │ (server 32K, reason)│ (your .aimodel)     │ MLX │
      │                     │                     │                     │ +   │
      │                     │                     │                     │ChatCompletions
      └───────────────────────────┬──────────────────────────────────────────┘
      ┌───────────────────────────┴──────────────────────────────────────────┐
Exec  │ Core AI (AIModel/InferenceFunction/NDArray, ANE+GPU+CPU)  │  MLX      │
 tier │ coreai-torch (convert) · coreai-opt (compress) · coreai-build (AOT)   │
      └───────────────────────────┬──────────────────────────────────────────┘
      ┌───────────────────────────┴──────────────────────────────────────────┐
Metal │ Metal Performance Primitives + TensorOps (matmul2d, cooperative      │
 tier │ tensors, quantized MTLTensor + MX scale planes, M5 neural accel.)     │
      └──────────────────────────────────────────────────────────────────────┘
```

The single most important reframing for a task-oriented series: **"which framework" is now mostly
"which model tier", because Core AI and MLX are `LanguageModel` conformers.** A reader can keep the
entire `LanguageModelSession` surface — streaming, `@Generable`, tools, Instruments — while swapping
the model underneath from Apple's on-device 3B to a Qwen3 they converted themselves.

### Version decoder ring
- Everything new here is **iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 + Xcode 27**.
- **iOS 26.4** is a real mid-cycle boundary: `tokenCount(for:)` and `contextSize` shipped there,
  guardrails were retuned, and a *different on-device model version* means prompts must be re-tested.
- Two on-device models now exist (Apple staff, forum 832910): **AFM 3 Core** and **AFM 3 Core
  Advanced** (iPhone Air / 17 Pro / 17 Pro Max, iPad M4+ ≥12 GB, Mac M3+ ≥12 GB, Vision Pro M5).
- **Custom LoRA adapters are discontinued in OS 27** (two independent Apple-staff confirmations).
  Migration path Apple names: Core ML or Core AI for the model, Background Assets for delivery.

### The five journeys the series must serve
1. **"I just want an LLM feature in my app."** → Foundation Models, on-device, ~10 guides.
2. **"The built-in model isn't enough."** → PCC, provider protocol, BYO open-weight model.
3. **"I have a PyTorch model."** → torch.export → coreai-torch → coreai-opt → coreai-build → runtime.
4. **"I want to run open-weight LLMs on Apple silicon."** → MLX (Python for research, Swift for apps).
5. **"It works on my Mac but not on the phone."** → memory, thermals, specialization, distribution.

### What the corpus is unusually strong on (and most guide series would miss)
- **Silent-wrong-answer bugs.** `.anyOf` doesn't constrain (Apple-reproduced). `AIProgram.optimize()`
  deletes broadcast-significant ops. GPU delegate runs `floor` as identity. Affine `gather_qmm`
  corrupts on M5 when rows %64≠0. MLX log2/log10 lower to natural log. None of these throw.
- **Export artifacts are not reproducible functions of the recipe.** The same
  `coreai.llm.export qwen3-0.6b` produced a 2.2× slower artifact after a macOS 26→27β upgrade with
  identical wheels, because the dequant-fold decision consults the *running OS*.
- **Burst vs sustained inverts the ranking.** Core AI 181 tok/s burst on iPhone 17 Pro retains ~56%
  over 10 minutes; MLX retains 38%; the ANE retains 67%. And energy-per-token inverts again.
- **Memory is the #1 shipping failure**, and one shipping app (Noema) has a fully worked
  two-stage launch gate, a hysteretic pressure ladder, and verified unloads.
- **Apple's own agent skills** (`coreai-models/skills/`) contain ANE authoring rules and PSNR
  acceptance gates that appear in no video and no doc page.

### Coding recommendation (see end of file for full rationale)
Write the **12 core guides** first (marked ⭐), in three waves. They are the ones every other guide
depends on, and they cover the three most common reader states: choosing, building, and shipping.

---

## Pillars

| # | Pillar | Why it exists |
|---|---|---|
| 1 | Orient & decide | The reader does not know which framework to use, and the wrong choice is expensive. Also carries the hardware/OS/entitlement gate matrix that determines whether *anything* will work. |
| 2 | Build with the built-in model | The 80% path: an LLM feature with zero model management. Highest reader volume. |
| 3 | Context engineering & agentic sessions | Where iOS 27 changed most (Dynamic Profiles, mutable transcript) and where multi-turn apps fail. |
| 4 | Beyond the built-in model | PCC, the `LanguageModel` protocol, and putting an open-weight model behind the same session API. |
| 5 | Convert a model to Core AI | The PyTorch→`.aimodel` pipeline. Dense, sequential, and unforgiving; the failure modes are silent. |
| 6 | Compress & optimize weights | Where size/quality/latency is actually traded, and where ANE-specific hardware limits bite. |
| 7 | Run models on device with Core AI | Runtime API, specialization/caching, AOT, bundles, engines. The gap between "converted" and "runs". |
| 8 | Debug numerics & profile | Non-deterministic systems need dedicated observability; this corpus has three separate toolchains for it. |
| 9 | MLX | The open framework: research in Python, deployment in Swift, plus the honest correctness caveats. |
| 10 | Evaluate & iterate | Apple's stated answer to "language models are non-deterministic". Also the only defense against OS-update drift. |
| 11 | Ship, distribute & operate | Downloads, updates, memory, thermals, App Store gating. Unglamorous, highest crash-avoidance value. |
| 12 | Adjacent capabilities | Speech, data/model introspection, Metal TensorOps — real corpus content that would otherwise be dropped. |

---

# The topics

Legend: **E** = evidence strength (strong / moderate / thin). **Len** = estimated length.
⭐ = proposed must-write core.

---

## Pillar 1 — Orient & decide

### 1. ⭐ `choosing-your-2026-apple-ai-stack`
**Choosing between Foundation Models, Core AI, MLX, and Core ML — a decision guide with measurements**
*Audience:* both · *E:* strong · *Len:* ~5,000 words · *depends on:* —

**Scope.** Answers the first question every reader has, without hand-waving. Establishes the layered
mental model (API tier / model tier / execution tier), shows that Core AI and MLX are now
`LanguageModel` backends rather than competitors, and grounds the decision in real measured numbers
rather than marketing. Includes the cases where the answer is "none of these — use Vision" or
"use Core ML".

**Key sections**
1. The four-layer stack diagram and what each layer owns
2. Decision tree: do you own model weights? do you need offline? do you need custom architecture?
3. Foundation Models: what you get free (streaming, guided generation, tools, Instruments, evals)
4. Core AI: when a custom `.aimodel` is worth the pipeline cost
5. MLX: research iteration, open-weight breadth, and the "not for end-user deployment" argument
6. Core ML's remaining scope — Apple explicitly routes decision trees / tabular work there
7. Measured reality check: Core AI 2.47× MLX at 0.6B → 1.05× at 8B; MoE inverts (MLX +28%)
8. Burst vs sustained vs energy-per-token — three different rankings from the same hardware
9. What "Core AI and MLX are LanguageModel conformers" buys you, concretely
10. Hybrid architectures shipping today (Noema's six-backend enum) and why they exist
11. Anti-patterns: choosing on tok/s alone; choosing before checking device eligibility
12. Where to go next, per journey

**Sources:** `00-ORIENTATION-lead-agent.md`; `transcripts/fm-core.md`; `transcripts/fm-ecosystem.md`;
`transcripts/coreai-intro.md`; `web/community-blogs.md`; `web/apple-docs-coreai.md`;
`repos/noema-ios.md`; `forums/forum-pain-points.md`

---

### 2. ⭐ `platform-gating-os-hardware-entitlements-appstore`
**Will this even run? OS versions, hardware tiers, entitlements, and App Store distribution**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 1

**Scope.** A single reference for every gate between your code and a working feature: OS/SDK version
floors per API, the AFM 3 Core vs Core Advanced hardware split, the Apple-Intelligence device floor,
entitlements, region/language gating, and the fact that **the App Store has no Required Device
Capability for Apple Intelligence** — so you cannot stop unsupported devices from installing.

**Key sections**
1. Version matrix: which API landed in 26.0 / 26.4 / 27.0 (with `@backDeployed` exceptions)
2. Two on-device models: AFM 3 Core vs Core Advanced, and the device list
3. Hardware floors: A17 Pro / M1 / M2 for Apple Intelligence and for `coreai-build` AOT
4. `SystemLanguageModel.availability` — all four unavailable reasons and their prescribed UX
5. The undocumented Siri coupling (iOS 27 b1 returns `.appleIntelligenceNotEnabled` unless Siri is on)
6. Language and locale gating: `supportsLocale(_:)` follows the *Siri* language, not the system one
7. Entitlements: `private-cloud-compute`, `increased-memory-limit`, app groups, background GPU
8. PCC eligibility as a business gate: Small Business Program + <2M lifetime first-time downloads
9. App Store distribution: no capability flag, Apple's baseline-non-AI-experience requirement,
   and checking availability *before* taking payment
10. Region/EU considerations and what still works there
11. SDK-conditional compilation: `canImport(FoundationModels, _version: 2)`, Xcode 27 build settings
12. A copy-paste preflight checklist

**Sources:** `forums/forum-pain-points.md`; `web/apple-docs-fm-evals-speech.md`;
`web/apple-docs-coreai.md`; `02-lead-agent-corpus-gaps-filled.md`; `repos/noema-ios.md`;
`repos/mlx-swift-lm.md`

---

## Pillar 2 — Build with the built-in model (Foundation Models)

### 3. ⭐ `fm-first-session-prompts-and-instructions`
**Your first Foundation Models feature: sessions, instructions vs prompts, `#Playground`, and prompt design**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* 2

**Scope.** The end-to-end first feature, following Apple's own code-along methodology
(`#Playground` → view model → view). Covers the instructions/prompts split as a *security* model,
not just an ergonomic one, plus prompting technique for a small on-device model and what to do when
the model version changes underneath you.

**Key sections**
1. `LanguageModelSession` lifecycle; when to make a new session vs reuse
2. `Instructions {}` vs `Prompt {}` — the two result builders and who authors each
3. Why the model is *trained* to obey instructions over prompts, and prompt-injection defense
4. Never interpolate user input into instructions (Apple's explicit rule)
5. `#Playground`: multi-block canvas tabs, project-type access without building, thumbs-up feedback
6. The three-step workflow and the `MARK: Chapter N` progress convention
7. Prompting the on-device model: Apple's supported vs avoid capability tables
8. Conditional prompts with Swift control flow inside `PromptBuilder`
9. One-shot prompting by embedding a fully-populated `@Generable` **instance** as the example
10. Apple's counter-intuitive finding: the most detailed prompt had the *highest* error rate
11. `prewarm()` and `prewarm(promptPrefix:)` — moving ~700 ms out of the user-visible window
12. Model-version drift: `#available(iOS 26.4)` prompt gating and localized prompt tables
13. First-feature checklist

**Sources:** `transcripts/fm-core.md` (meet-with-apple-205 code-along);
`web/apple-docs-fm-evals-speech.md`; `forums/forum-pain-points.md`

---

### 4. ⭐ `fm-guided-generation-generable-guide-schemas`
**Guided generation: `@Generable`, `@Guide`, constrained decoding, dynamic schemas, and failure modes**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,000 words · *depends on:* 3

**Scope.** How structured output actually works (constrained decoding, top-down, structurally
guaranteed), the full `@Guide` constraint vocabulary and which constraints are legal on which types,
runtime schema construction with `DynamicGenerationSchema`, and the confirmed-broken `.anyOf` guide
with two working workarounds.

**Key sections**
1. `@Generable` on structs and enums; composability and nested types
2. Constrained decoding: why structure is guaranteed and what that does *not* guarantee
3. The `@Guide` catalogue: `description`, `.range`, `.count`, `.pattern`, `.anyOf`, `.constant`,
   `.element`, min/max variants
4. The guide↔type compatibility matrix (derived from 28 negative test classes in the Python SDK)
5. Enum-for-compile-time-known vs `.anyOf`-for-runtime-known — the decision table
6. 🚩 `.anyOf` does not constrain generation — Apple-reproduced. Validate in code + shout in instructions
7. Guided generation lets you *delete* prompt text — and the token cost of the schema
8. `includeSchemaInPrompt: false` and the exact precondition that makes it safe
9. `DynamicGenerationSchema` + `GenerationSchema(root:dependencies:)` for runtime-built schemas
10. `GeneratedContent` and reading values by property
11. Classification with `@Generable enum` + `GenerationOptions(samplingMode: .greedy)`
12. Multilingual: property names are model input, exactly like `@Guide` descriptions
13. Failure taxonomy: decoding failure, unsupported guide, invalid schema, refusal-on-guided-generation
14. Swift ↔ Python schema parity (the 7 checked-in fixture types)

**Sources:** `transcripts/fm-core.md`; `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md` (thread 812501); `repos/python-apple-fm-sdk.md`

---

### 5. `fm-streaming-partially-generated-ui`
**Streaming into SwiftUI: snapshot streaming, `PartiallyGenerated`, throttling, and cancellation**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 4

**Scope.** Real-time UI over a non-deterministic generator. Covers the two things everyone gets
wrong — `streamResponse` is not `async`, and every element is a full *snapshot* not a delta — plus
the mandatory optional-unwrapping across every nested type, and cancellation that doesn't corrupt
state or crash on backgrounding.

**Key sections**
1. `streamResponse(to:generating:)` returns an `AsyncSequence` — do not `await` the call itself
2. Snapshots vs deltas, and why `.content` is a full `T.PartiallyGenerated`
3. How `PartiallyGenerated` is synthesized for every type in the graph
4. `if let` across nested types — the boilerplate and SwiftUI patterns that reduce it
5. `GenerationID` for stable identity across snapshots in `ForEach`
6. Throttling UI updates; isolating per-token `@Published` writes from the whole-view invalidation
7. Cumulative-vs-delta detection when you also support non-Apple backends
8. Reasoning streams (PCC): `Transcript.Entry.reasoning`, segments, signatures, progress UI
9. Cancellation: `withTaskCancellationHandler`, cancel-before-`next()`, and the iOS background-GPU trap
10. Structured streaming caveat: the Python SDK has none; plan for text-only there
11. Testing streaming deterministically

**Sources:** `transcripts/fm-core.md`; `repos/mlx-swift-examples.md`; `repos/noema-ios.md`;
`repos/python-apple-fm-sdk.md`; `web/apple-docs-fm-evals-speech.md`

---

### 6. ⭐ `fm-tool-calling`
**Tool calling: the `Tool` protocol, the argument contract, transcript anatomy, and forcing (or forbidding) tool use**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,000 words · *depends on:* 4

**Scope.** Everything from a first tool to a bounded agent loop. Emphasizes the two facts that trip
people up: the model will *not* reliably call your tool from its name and description alone, and
`.required` puts the model in an unbounded while loop unless you build an exit.

**Key sections**
1. `Tool` conformance: `name`, `description`, `Arguments` as the model↔tool contract, `call`
2. Why you must *also* write an instruction sentence telling the model to use the tool
3. The six-entry transcript anatomy of one tool-using turn (one `toolCalls` entry, N `toolOutput`)
4. Automatic invocation: how outputs are re-inserted and synthesized
5. `GenerationOptions(samplingMode: .greedy)` for deterministic tool-call tests
6. `ToolCallingMode`: `.allowed` / `.disallowed` / `.required`, and both API surfaces
7. 🚩 `.required` is a while loop — the two sanctioned exits (state-conditioned mode; throwing final-answer tool)
8. Errors from tools: what reaches the model vs what reaches you
9. `.onToolCall` as an approval chokepoint — and that throwing there aborts the whole turn
10. Runtime-built tool schemas, and the once-computed `Tool.parameters` trap
11. Tool definitions cost context: they sit in the token budget and in the KV prefix
12. Deterministic ordering of tool specs and why it matters for cache reuse
13. Testing tools without a model

**Sources:** `transcripts/fm-core.md`; `transcripts/fm-advanced.md`;
`web/apple-docs-fm-evals-speech.md`; `forums/forum-pain-points.md`; `repos/noema-ios.md`

---

### 7. `fm-spotlight-and-vision-tools`
**Built-in tools: local RAG with `SpotlightSearchTool`, plus `OCRTool` and `BarcodeReaderTool`**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* 6

**Scope.** Grounding a model in the user's own content with zero vector database. Covers the full
`SpotlightSearchTool` configuration surface, consuming results for list UI, and — critically — the
**metadata gap** that makes the model hallucinate note bodies, plus the description/JSON-Schema
mismatch Apple has acknowledged as a known issue.

**Key sections**
1. Why local RAG: Core Spotlight as an index you already populate
2. `SpotlightSearchTool()` and the cross-import overlay (you must import *both* modules)
3. `Configuration`: `sources`, `guide`, `contactResolver`, `customStages`
4. `Guide` levels (`.complete` / `.focused` / `.dynamic`) and formats — a **token budget** decision
   (🚩 `.complete` injects ~13k tokens and instantly blows a 4K window)
5. The search trajectory: model decides → generates query → Spotlight executes → model reasons
6. Consuming `tool.searchResults`: `SearchReply` batches and `queryToken`-keyed UI refresh
7. 🚩 The metadata gap: results carry identity attributes only, so the model invents bodies
8. The retrieve-then-hydrate pattern: `searchableItems(forIdentifiers:)` and a companion fetch tool
9. Pipeline stages: `Generable` `CustomStage`s for count/table/statistic over result sets
10. 🚩 Known issue: the tool's description and its generated JSON Schema disagree — non-Apple models fail
11. Other failures: model-catalog asset error, tool silently not invoked, `.required` as a probe
12. `OCRTool` and `BarcodeReaderTool` — Vision-backed, free, and when to use them instead of the LLM
13. Evaluating a Spotlight-grounded feature with a result-coverage metric

**Sources:** `transcripts/fm-ecosystem.md` (session 246); `forums/forum-pain-points.md`;
`web/apple-docs-fm-evals-speech.md`; `transcripts/fm-core.md`

---

### 8. `fm-image-input-attachments`
**Image input: `Attachment`, labels, `ImageReference`, token cost, and what the model cannot do**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 4

**Scope.** The 2026 multimodal surface: inserting images into prompt builders, labeling them so tools
can reference specific ones, and the honest limits — larger images cost tokens and latency, and the
model cannot produce reliable bounding boxes.

**Key sections**
1. `Attachment(_:orientation:)` inside `@PromptBuilder`; accepted types (CGImage/CIImage/CVPixelBuffer/URL)
2. No cropping or padding required — but bigger images cost more tokens and latency
3. `.label(_:)` and why labels matter once tools are involved
4. `ImageReference` as a `Generable` tool-argument type; `.resolved(in:)`
5. `Transcript.AttachmentSegment` / `ImageAttachment` and the new `Segment.attachment` case
6. EXIF orientation: `CIImage(contentsOf:)` ignores the tag — bake orientation into pixels
7. PhotosPicker and security-scoped file URLs on macOS; a `Transferable` that actually works
8. Image count, context budget, and a per-image token estimate for a context meter
9. 🚩 Bounding boxes are unreliable — use Vision saliency/detection for coordinates
10. Which models accept images (on-device vs PCC vs third-party capability declaration)
11. Build-time vs runtime gating of image support (the Python SDK's SDK-version flag as the cautionary case)

**Sources:** `transcripts/fm-core.md`; `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`; `repos/mlx-swift-examples.md`; `repos/python-apple-fm-sdk.md`

---

### 9. ⭐ `fm-failure-handling-errors-guardrails-safety`
**When it goes wrong: availability, the 2026 error taxonomy, guardrails vs refusals, and safety design**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,000 words · *depends on:* 3

**Scope.** The single largest and longest-running cluster of developer pain in the forums. Covers the
error-type reshuffle (and its binary-compatibility trap), the two *different* refusal mechanisms
people constantly conflate, guardrail configuration and its `Generable` exclusion, and the design
work — deny lists, bounded I/O, risk tables — that Apple asks of you.

**Key sections**
1. Availability first: four unavailable reasons and the UX each implies
2. Testing all availability branches on one machine (Xcode scheme "Simulated … Availability")
3. The 2026 error split: `LanguageModelError` / `LanguageModelSession.Error` / `SystemLanguageModel.Error`
   / `PrivateCloudComputeLanguageModel.Error`
4. 🚩 `GenerationError` is deprecated but *binary compatible* — rebuilding with Xcode 27 silently
   changes which `catch` fires
5. 🚩 Two refusal surfaces: `guardrailViolation` (classifier) vs `LanguageModelError.refusal`
   (model-level, unaffected by guardrail settings)
6. `SystemLanguageModel(guardrails: .permissiveContentTransformations)` — string generation only
7. Real false positives from the field (tick treatment, "frunk", theology, camping) and the iOS 27
   health-prompt refusal regression
8. Apple may update guardrails *outside the OS cycle* — why your prompt suite must run regularly
9. Prompt injection: instructions outrank prompts; never interpolate user input
10. Bounded input/output patterns, hosted deny lists, `@Generable enum` outputs
11. The risk-assessment table and the four adversarial input categories
12. `logFeedbackAttachment(sentiment:issues:desiredOutput:)` and the `#Playground` thumbs-up flow
13. 🚩 The Simulator trap: it punches out to the host macOS, producing meaningless `-1` errors
14. Graceful degradation architecture: a protocol seam with a non-AI fallback

**Sources:** `forums/forum-pain-points.md`; `web/apple-docs-fm-evals-speech.md`;
`transcripts/fm-core.md`; `repos/noema-ios.md`

---

### 10. ⭐ `fm-context-window-and-kv-cache`
**Context management: the 4K window, token accounting, history compaction, and KV-cache economics**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,000 words · *depends on:* 6

**Scope.** Merges the two questions that always arrive together: *"why did I get
`exceededContextWindowSize`"* and *"why is time-to-first-token getting worse"*. Both are about the
same token layout. Covers what consumes the window, how to measure it, how to compact history, and
the precise rules for keeping the KV cache warm.

**Key sections**
1. The 4K on-device window (8K reported on iOS 27 by one shipping app — read `contextSize`, don't hardcode)
2. What counts: instructions + tool definitions + tool I/O + `@Generable` schemas + all responses
3. `SystemLanguageModel.contextSize` and `tokenCount(for:)` (26.4+, `@backDeployed` differences)
4. Building a segmented context meter (system prompt / tool guidance / schemas / history / images)
5. Recovering from `contextSizeExceeded`: compaction, retry-once, session rebuild
6. iOS 26 idiom (rebuild a session from a compacted `Transcript`) vs iOS 27 idiom (mutable transcript)
7. `transcript.history` and `@SessionProperty(\.history)` — lossy and global to the session
8. `historyTransform` — local, lossless, per-profile; Apple's stated preference
9. Session token layout: instructions → tool definitions → transcript entries
10. 🚩 A change at position N invalidates the cache for everything after N
11. Conditional content in `DynamicInstructions` must go **last**
12. Stateless in-place transforms preserve the cache; dropping transforms invalidate from the drop
    point; stateful transforms invalidate every request
13. Batched consolidation beats incremental trimming
14. `prewarm()` 1–2 s ahead of a restored session; restoring costs a full re-prefill
15. Measuring cache hit rate (cached input tokens ÷ total input tokens) and reading it in Instruments
16. 🚩 The accuracy hazard: models reason confidently from history you removed

**Sources:** `transcripts/fm-advanced.md`; `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`; `repos/foundation-models-utilities.md`; `repos/noema-ios.md`

---

### 11. `fm-instruments-profiling-and-debugging`
**Debugging a Foundation Models feature with Instruments: lanes, the inference tree, and silent failures**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,000 words · *depends on:* 6

**Scope.** The only observability story for a non-deterministic runtime. Reproduces Apple's worked
silent-failure bug end to end — instruction prose referencing a tool that was never registered,
producing an infinite loop with no error — because the *diagnostic sequence* is the transferable skill.

**Key sections**
1. Exact click path; Xcode 27 + latest OS; works with **any** `LanguageModel`, not just Apple's
2. 🚩 Trace files contain raw prompts and responses unencrypted — handle as sensitive data
3. Lanes: Instructions (a profile-switch visualizer) and Model Inference (yellow prefill / orange decode)
4. Tree view hierarchy: sessions → requests → model inferences → instructions/prompts/responses/tool calls
5. The invariant: every model inference has instructions, a prompt, and a response *or* an error
6. One user request fans out into multiple model inferences
7. The Instructions node inspector — the only place that cross-checks prose against the declared toolset
8. Worked debugging narrative: symptom → lane → inspector → missing tool → fix → verified
9. The Info column as a triage filter (errors, long durations, large token counts)
10. Three metrics with prescribed fixes: TTFT (shorten the prompt), tokens/sec (regression detection),
    total latency (stream to fix *perceived* latency)
11. Reading cache invalidations from a trace
12. Profile switches take effect on the **next** request, not mid-request

**Sources:** `transcripts/fm-advanced.md` (session 243); `web/apple-docs-fm-evals-speech.md`

---

## Pillar 3 — Context engineering & agentic sessions

### 12. ⭐ `fm-dynamic-profiles`
**Dynamic Profiles from zero: `DynamicInstructions`, `Profile`, `LanguageModelSession.DynamicProfile`**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* 10

**Scope.** The flagship 2026 API and the prerequisite for every advanced session topic. A SwiftUI-shaped
declarative layer where the body is re-evaluated before every prompt, resolving to exactly one active
profile. Gets the nested protocol spelling right (transcripts say `DynamicProfile`; the real type is
`LanguageModelSession.DynamicProfile`).

**Key sections**
1. The two problems Apple built it for: context management and capability/cost boundaries
2. Three layers: `DynamicInstructions` → `Profile` → `LanguageModelSession.DynamicProfile`
3. 🚩 Naming: the protocol is nested — code copied from the talk will not compile
4. `var body: some LanguageModelSession.DynamicProfile` and the result builder
5. Nesting `DynamicInstructions` concatenates instructions *and* tools
6. 🚩 The body is re-evaluated every prompt (measured: 7 evaluations for 3 turns) — it must be pure
7. All imperative work belongs in lifecycle modifiers, not the body
8. The full modifier list: `model`, `temperature`, `samplingMode`, `reasoningLevel`,
   `maximumResponseTokens`, `toolCallingMode`, `transcriptErrorHandlingPolicy`, `historyTransform`, `modifier`
9. Three-tier precedence: call-site options > innermost profile > outer container
10. Lifecycle callbacks: `onActivate`/`onDeactivate`/`onPrompt`/`onResponse`/`onToolCall`/`onToolOutput`/`onReasoning`
11. Session properties: `@SessionPropertyEntry` in `SessionPropertyValues`, `@SessionProperty(\.key)`,
    reading `session.properties`
12. 🚩 History is read-only inside `DynamicInstructions` and `Tool` bodies
13. Writing a reusable `DynamicProfileModifier`
14. `LanguageModelSession(profile:)` / `(profile:history:)` and rehydration cost
15. 🚩 Switching profiles is a deliberate KV reset — do it at conversation boundaries

**Sources:** `transcripts/fm-advanced.md` (session 242); `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`; `repos/foundation-models-utilities.md`

---

### 13. `fm-agentic-orchestration-patterns`
**Agentic patterns: baton-pass, phone-a-friend, bounded tool loops, and transcript error policy**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 12

**Scope.** The two orchestration patterns Apple named, with opposite transcript semantics, plus the
machinery that makes multi-step agents survivable: bounded `.required` loops, transcript rollback
policy, and the newly-mutable transcript with its programmer-error trap.

**Key sections**
1. Baton-pass: shared transcript, a mode variable, a tool that flips it; the receiver answers
2. Phone-a-friend: a tool spawns an isolated child session; the parent always answers
3. Side-by-side comparison table (transcript visibility, who answers last, cost, privacy)
4. Exposing the mode switch itself to the model as a tool
5. Combining baton-pass with `.toolCallingMode(.required)` and a compiled reference exit condition
6. `transcriptErrorHandlingPolicy`: `.revertTranscript` (default) vs `.preserveTranscript`
7. 🚩 `session.transcript` is mutable only when `isResponding == false` — otherwise it traps
8. Repairing a transcript after a preserved failure
9. Cross-model orchestration: on-device → PCC → third party, and the privacy hop
10. 🚩 Context-size mismatch when handing a PCC-sized transcript to a 4K on-device profile
11. 🚩 Third-party providers: tool-driven baton-pass is unreliable; use guided generation to route
12. Why every context-engineering change needs an Evaluations gate

**Sources:** `transcripts/fm-advanced.md`; `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`; `repos/mlx-swift-lm.md`

---

### 14. `fm-utilities-skills-and-history-modifiers`
**`foundation-models-utilities`: Skills, history modifiers, and the out-of-band package**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 12

**Scope.** Apple's separately-versioned, experimental package — the supported replacement for
hand-rolled context management. Its `Skill` API is also the clearest teaching example of KV-cache
economics anywhere in the corpus, because the choice between `prompt:` and `instructions:` decides
whether the cache survives.

**Key sections**
1. What ships out of band and why the API is explicitly unstable
2. `droppingCompletedToolCalls()`, `rollingWindow(entries:)`, `summarizeHistory(entryThreshold:model:…)`
3. Modifier application order ("outside-in") resolved precisely, with the documented `rollingWindow` bug
4. 🚩 `summarizeHistory` collapses everything into one `.prompt` entry and destroys tool-call metadata
5. Composing strategies — Apple's stated "no one-size-fits-all"
6. `Skills`: just-in-time procedural knowledge, `DynamicInstructions` conformance, result builder
7. The activation mechanism: the model activates a skill by emitting a tool call
8. ⭐ The central table: `prompt:` → tool-output entry → **cache preserved**;
   `instructions:` → merged into the instructions entry → **cache invalidated**, higher priority
9. `allowsDeactivation:` and full context reclamation with `droppingCompletedToolCalls()`
10. `SkillActivations` is `Observable` + `RandomAccessCollection` → drives SwiftUI directly
11. Known issues: `SkillActivation` build failures, the `ChatCompletionsLanguageModel` `v1` path bug
12. "Here's what people hand-rolled; here's the supported way now"

**Sources:** `repos/foundation-models-utilities.md`; `02-lead-agent-corpus-gaps-filled.md`;
`transcripts/fm-advanced.md`; `forums/forum-pain-points.md`

---

## Pillar 4 — Beyond the built-in model

### 15. ⭐ `fm-private-cloud-compute`
**Private Cloud Compute end to end: eligibility, entitlement, reasoning levels, quota UX, and fallback**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 9

**Scope.** More policy than API. Leads with eligibility because for many readers the answer is
"you cannot use this", and the fallback is an entirely different architecture. Then covers the
32K/reasoning capability delta, the mandated quota UX, and the tiering seam.

**Key sections**
1. The one-line switch: `LanguageModelSession(model: PrivateCloudComputeLanguageModel())`
2. Eligibility is three conditions: Small Business Program + <2M *lifetime* first-time downloads +
   the managed entitlement (and the 6-month migration cliff if you outgrow it)
3. 🚩 Missing entitlement is a runtime `fatalError`, not a catchable error
4. On-device vs PCC comparison: offline, unlimited, 4K, no reasoning — vs network, quota, 32K, reasoning
5. `ContextOptions(reasoningLevel:)` — `.light` / `.moderate` / `.deep`, and that reasoning tokens
   count against the context limit
6. Reasoning in the transcript: a separate segment, inspectable for progress UI, absent from content
7. `quotaUsage`: `isLimitReached`, `.belowLimit(info).isApproachingLimit`, `resetDate`,
   `limitIncreaseSuggestion.show()`
8. Apple's prescribed quota UX: no alerts, persistent in-place state, disabled button, upgrade affordance
9. Xcode scheme simulation of quota states
10. 🚩 PCC does not work in the Simulator at all; availability reasons differ from on-device
11. watchOS 27 as a PCC-primary surface, and the pairing question
12. Designing a tiered protocol seam so PCC is one implementation, not the foundation
13. Retry-on-device when PCC fails for network reasons

**Sources:** `transcripts/fm-ecosystem.md` (session 319); `transcripts/fm-core.md`;
`forums/forum-pain-points.md`; `web/apple-docs-fm-evals-speech.md`;
`02-lead-agent-corpus-gaps-filled.md`; `repos/noema-ios.md`

---

### 16. ⭐ `byo-model-behind-languagemodelsession`
**Running an open-weight model behind `LanguageModelSession`: Core AI, MLX, and Chat Completions**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,000 words · *depends on:* 1

**Scope.** The consumer-side answer to "I want a different model but I like this API." Three concrete
paths, each one line to adopt, with the capability and quality caveats that decide between them.
This is the guide that turns the framework-choice question from either/or into a swap.

**Key sections**
1. What "everything downstream stays the same" actually buys (streaming, `@Generable`, tools, Instruments)
2. `CoreAILanguageModel(resourcesAt:variant:kvCacheStrategy:)` — your own `.aimodel` bundle
3. `MLXLanguageModel(...)` from `MLXFoundationModels` in `ml-explore/mlx-swift-lm`
   (🚩 requires the 27 SDK; developers famously could not find this module)
4. `ChatCompletionsLanguageModel(name:url:supportsGuidedGeneration:)` → any OpenAI-compatible server,
   including `mlx_lm.server`, Ollama, LM Studio, vLLM
5. 🚩 The hardcoded `v1` path bug that breaks non-`/v1` endpoints
6. Capability declaration is user-visible: `.vision`, `.toolCalling`, `.guidedGeneration`, `.reasoning`
7. How guided generation is enforced on non-Apple models: xgrammar constrained decoding
   (both Apple's `coreai-models` and `mlx-swift-lm` converge on it)
8. `usage` token accounting across providers — built for per-token billing
9. Auth for cloud providers: never take an API key in an initializer; token provider + Keychain + App Attest
10. 🚩 Privacy disclosure obligation on both package authors and consumers
11. What breaks with small models: tool-call dialects, decoding failures, thinking-token loops
12. A capability-based routing table for a multi-model app

**Sources:** `transcripts/fm-ecosystem.md` (session 339); `repos/foundation-models-utilities.md`;
`repos/mlx-swift-lm.md`; `repos/apple-coreai-models.md`; `01-lead-agent-repo-spotchecks.md`;
`forums/forum-pain-points.md`

---

### 17. `authoring-a-languagemodel-provider-package`
**Authoring a `LanguageModel` provider package: protocol, capabilities, executor store, packaging**
*Audience:* Swift app dev (library author) · *E:* strong · *Len:* ~5,500 words · *depends on:* 16

**Scope.** The library-author side of the 2026 headline API. Covers the two-protocol split, the
`Configuration`-as-cache-key semantics that catch everyone, lifecycle and teardown, error design, and
SwiftPM packaging including Linux reach. Anchored on three real conformances that can be read
side by side.

**Key sections**
1. `LanguageModel`: `capabilities` + `executorConfiguration` + `associatedtype Executor`
2. `LanguageModelExecutor`: `init(configuration:)`, `prewarm(model:transcript:)`, `respond(to:model:streamingInto:)`
3. 🚩 "The configuration is the lookup key, **not** the model" — one executor per unique Configuration
4. Making `Configuration` `Hashable` when it wraps non-Hashable engine handles
5. Automatic session-scoped teardown — and why a process-global weights cache opts you out
6. 🚩 The silent-no-op `prewarm` trap: a near-miss signature compiles and is never called
7. Declaring capabilities is routing-relevant: the framework rejects unsupported requests *before* you run
8. `ContextOptions` (what goes into the prompt) vs `GenerationOptions` (the decoder loop)
9. "Approximate or throw": when to bend to developer intent; when to throw a built-in `LanguageModelError`
10. Custom error types only for service-specific failures (subscriptions, account state)
11. Custom segments as the modality extension point; server-side tools and three disclosure levels
12. SwiftPM packaging: platforms, Linux, dependency weight, repo-URL-as-distribution
13. Apple's own written guidance: the `foundation-models-language-model-protocol` agent skill
14. Three conformances compared: `ChatCompletionsLanguageModel`, `CoreAILanguageModel`, `MLXLanguageModel`

**Sources:** `transcripts/fm-ecosystem.md`; `repos/foundation-models-utilities.md`;
`repos/apple-coreai-models.md`; `repos/mlx-swift-lm.md`; `web/apple-docs-fm-evals-speech.md`

---

### 18. `provider-transcript-channel-and-stateful-kv`
**Provider internals: transcript translation, the generation channel, and stateful KV reuse**
*Audience:* Swift app dev (library author) · *E:* strong · *Len:* ~5,000 words · *depends on:* 17

**Scope.** The two hardest parts of writing a provider, both undocumented outside one video and three
source trees: mapping six transcript entry types onto whatever roles your model has, emitting channel
events in an order that doesn't produce phantom transcript entries, and diffing transcripts so you can
reuse a KV cache instead of re-prefilling every turn.

**Key sections**
1. The six entry types and how to route them (instructions/prompt/response → system/user/assistant;
   toolCalls/toolOutput/reasoning also → assistant when there is no dedicated role)
2. Reading the request: transcript, `enabledToolDefinitions`, `schema`, `generationOptions`, `contextOptions`, `id`
3. Channel events: `.response` / `.reasoning` / `.toolCalls`; actions `appendText`, `appendArguments`,
   `updateMetadata`, `updateUsage`
4. Usage accounting: input total/cached, output total/reasoning
5. 🚩 Sending usage upfront materializes an **empty Response entry** on tool-call turns — send at end of turn
6. 🚩 The `updateUsage(input:output:metadata:)` symbol that exists in the `.swiftinterface` but not the
   dylib — the compiled reference alone aborts at image load
7. One-shot is streaming underneath; the framework collects deltas
8. Stateful executors: the executor receives the full transcript every call
9. Transcript diffing: append-only fast path, divergence detection, invalidate-back-to-divergence
10. Measured payoff: 97 cached tokens reused, latency flat at ~0.33 s vs 2.8 s without diffing
11. 🚩 Structural blockers: post-EOS over-generation poisoning the cache; thinking-model templates
    stripping historic reasoning blocks
12. Incremental detokenization: U+FFFD handling and keeping one token of context for SentencePiece
13. Parsing reasoning and tool calls out of a raw text stream with hold-back windows

**Sources:** `transcripts/fm-ecosystem.md`; `repos/apple-coreai-models.md`;
`repos/mlx-swift-lm.md`; `repos/foundation-models-utilities.md`; `repos/issues-mlx-stack.md`

---

## Pillar 5 — Convert a model to Core AI

### 19. ⭐ `coreai-conversion-pipeline-overview`
**From PyTorch checkpoint to running on device: the complete Core AI pipeline**
*Audience:* Python ML engineer + Swift app dev · *E:* strong · *Len:* ~5,000 words · *depends on:* 1

**Scope.** The spine guide. One worked model, all the way through: export → decompose → convert →
optimize → save → verify numerics in Python → inspect in Xcode → compile AOT → load in Swift. Every
later Core AI guide is a zoom-in on one stage of this.

**Key sections**
1. Vocabulary first: `.aimodel` (portable source **directory**) vs `.aimodelc` (per-arch compiled) vs
   the specialized cache entry
2. Install: `pip install coreai-torch` (brings `coreai`), `coreai-opt`, and `uv` for the model recipes
3. 🚩 Prerequisite everyone hits: the **Metal Toolchain** is not installed with Xcode
4. Stage 1 — `model.eval()` + `torch.export.export(...)` with `dynamic_shapes`
5. Stage 2 — 🚩 mandatory `ep.run_decompositions(get_decomp_table())`
6. Stage 3 — `TorchConverter().add_exported_program(ep).to_coreai()`
7. Stage 4 — 🚩 `to_coreai()` runs **zero** optimization; you must call `.optimize()`
8. Stage 5 — `save_asset(Path("Model.aimodel"))`
9. Stage 6 — numeric parity in Python: run the `.aimodel` and `np.allclose` against PyTorch
10. Stage 7 — the Xcode model viewer (General/Functions tabs, `?` for dynamic dims)
11. Stage 8 — Swift: `AIModel(contentsOf:)` → `loadFunction(named: "main")` → `NDArray` → `run`
12. 🚩 `AIProgram.optimize()` is not always semantics-preserving — always A/B it numerically
13. 🚩 Version floor: bundles exported with `coreai-core < 1.0.0b2` fail on Xcode 27 β3+
    (`Failed to convert to versioned IR`) — and the recovery via `strip_debug_info`
14. Where each of the following guides picks up

**Sources:** `transcripts/coreai-intro.md`; `transcripts/coreai-python-metal.md`;
`repos/coreai-torch.md`; `web/apple-docs-coreai.md`; `repos/issues-coreai-stack.md`;
`web/community-blogs.md`

---

### 20. `coreai-torch-converter-reference`
**`coreai-torch` reference: `TorchConverter`, decomposition, IO naming, dynamic shapes, multi-entrypoint assets**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~6,500 words · *depends on:* 19

**Scope.** The exhaustive converter reference, including the signature details the published docs get
wrong (keyword-only naming args), the IO/state naming rules that "are observed FX behavior, not a
stable contract", and building one asset with several entrypoints — which is how SAM3 gets a 76%
faster prompt swap.

**Key sections**
1. `TorchConverter(mode:)` — `Mode.DEBUG` (the default, embeds torch stack traces) vs `Mode.RELEASE`
2. 🚩 `input_names`/`output_names`/`state_names`/`entrypoint_name` are **keyword-only** in source
3. `add_exported_program` vs `add_pytorch_module(export_fn=, externalize_modules=)` — the capability split
4. `get_decomp_table()`: the 12 ops it preserves and why skipping it is a hard failure
5. `to_coreai(entrypoints=)`, `clear(entrypoints=)`, converter reuse
6. Multi-entrypoint assets: staging N programs with distinct entrypoint names in one `.aimodel`
7. The SAM3 three-function split (`image_encode` / `text_encode` / `detect`) and the cadence payoff
8. Dynamic shapes: `Dim`, how SymInts become `?`, and the INT32 slice clamp
9. 🚩 Ops that reject dynamic dims (`split`, `var`/`std` with ddof, `tensordot`, `tril`/`triu`, …)
10. Dtype narrowing: int64→int32 and float64→float32, silently, everywhere
11. Sub-byte and reduced-precision dtypes the IR supports (uint1–uint7, int2–int4, fp8, fp4, bf16)
12. Pre-conversion validation and its two actionable error messages
13. Reading the emitted IR; filecheck-style assertions in your own tests
14. `graphdiff` and `freqop` CLIs
15. Version gates: torch 2.8–2.13, `coreai-core==1.0.0b2` pin, Python ≥3.11

**Sources:** `repos/coreai-torch.md`; `transcripts/coreai-python-metal.md`;
`repos/issues-coreai-stack.md`; `repos/apple-coreai-models.md`

---

### 21. ⭐ `coreai-stateful-export-and-kv-cache`
**Stateful models: exporting a KV cache as Core AI "states"**
*Audience:* Python ML engineer + Swift app dev · *E:* strong · *Len:* ~5,000 words · *depends on:* 20

**Scope.** The single highest-leverage Core AI performance technique and the subtlest contract in the
whole conversion pipeline. Covers what counts as state, the ordering rules that break silently, the
IR attribute that marks it, and the Swift side that must supply a mutable view for every state.

**Key sections**
1. Why: transformer decode is quadratic without a cache — visible as growing inference intervals
2. What counts as state: `register_buffer` + in-place mutation, and mutated user inputs. **No opt-out.**
3. `state_names`: one name per state, used for both the input and its mutation output
4. 🚩 `input_names`/`output_names` cover *non-stateful* IO only — a breaking change from earlier releases
5. 🚩 Ordering is prescribed (buffers in registration order, then mutated user inputs) and is
   "observed FX behavior, not a stable PyTorch contract" — always name explicitly
6. The `MutableBuffers.buffer_mutation` IR attribute
7. 🚩 Stateful models effectively **require** `optimize()`, or mutation outputs vanish from the runtime dict
8. `coreai::mutable_slice_update` and Apple's `KVCache.update_and_fetch(layer, offset, k, v)` primitive
9. Cache shape convention: `(n_layers, batch, n_kv_heads, max_seq_len, head_dim)`, seq axis = 3
10. The stateful LLM contract: `input_ids` `[1,1]` + `position_ids` carrying the **full prefix range**
11. Fixed max-context allocation and its memory cost
12. Swift side: `InferenceFunction.MutableViews`, `consume`, `run(inputs:states:outputViews:)`
13. 🚩 Copy-on-write: park a placeholder in the state slot or you copy the whole cache every step
14. Host-cache exports as the alternative when the ANE compiler rejects in-graph indexed writes
15. 🚩 `slice_update` with runtime-value begin/end crashes ANECompiler at load
16. Hybrid/SSM state (conv + recurrent) and the `Expected 2 states, got 4` engine wall

**Sources:** `transcripts/coreai-intro.md`; `repos/coreai-torch.md`; `repos/apple-coreai-models.md`;
`repos/mlx2coreai.md`; `repos/noema-ios.md`; `repos/issues-coreai-stack.md`; `repos/swift-lm.md`

---

### 22. `coreai-op-coverage-composites-externalization`
**When an op won't convert: coverage, composite ops, externalization, and custom lowerings**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,000 words · *depends on:* 20

**Scope.** The "my model won't convert" guide, plus the *performance* half nobody talks about:
composite ops are how you tell Core AI "this is attention / RoPE / RMSNorm / MoE dispatch" so it can
dispatch to fast kernels instead of a decomposed soup.

**Key sections**
1. The op-resolver contract: FX-qualified `op.overload` names, and the overload-mismatch footgun
2. Reading the two validator errors and the decision tree they imply
3. The composite-op library: `SDPA`, `RoPE`, `RMSNorm`, `GatherMM` (MoE), `GatedDeltaUpdate` (SSM)
4. Core AI has first-class MoE and linear-attention support — stated in no talk
5. `ExternalizeSpec(target_class=, composite_op_name=, composite_attrs=)` and the
   🚩 must-target-the-**Impl**-class trap
6. 🚩 A spec that matches nothing emits only a `UserWarning` — typos are silent no-ops
7. The five-phase externalization pipeline (mark → re-export → prepare → export → emit/restore)
8. Per-call-site UUID graph names; never hard-code symbol names
9. `register_torch_lowering(qualified_name, allow_override=)` — the callback contract and helpers
10. `generate_composite_decl` and emitting a named composite
11. 🚩 Semantic divergences to know: ATen SDPA vs `composite_ops.SDPA` (mask-based vs attributes);
    lower-right vs upper-left causal masking; partial-rotary RoPE pairing vs HuggingFace
12. Externalization for memory-efficient weight loading and iOS embedding quantization
13. What is still unsupported (conv_transpose3d; higher-order ops outside the interpreter)
14. Decision tree: decomp-table tweak vs custom lowering vs custom Metal kernel

**Sources:** `repos/coreai-torch.md`; `01-lead-agent-repo-spotchecks.md`;
`transcripts/coreai-python-metal.md`; `repos/issues-coreai-stack.md`; `repos/apple-coreai-models.md`

---

### 23. `coreai-custom-metal-kernels`
**Writing a custom Metal kernel for Core AI with `TorchMetalKernel`**
*Audience:* Python ML engineer · *E:* moderate · *Len:* ~4,000 words · *depends on:* 22

**Scope.** The escape hatch when no op and no composite fits: author a Metal kernel in Python, pair it
with a PyTorch reference for shape inference, and ship the MSL *inside* the `.aimodel`.

**Key sections**
1. The pairing: a PyTorch reference function (shape inference only) + an MSL body string
2. What Core AI generates for you: signature, buffer bindings, `#include <metal_stdlib>`
3. `MetalParameter(name, metal_type, attribute)` for thread-position attributes
4. `result_shapes` at every call site — required so dynamic output shapes can be derived
5. `template_dtypes` for one kernel across half/float/bfloat, and `helper_src` for typedefs
6. Tensors inside the kernel are Metal tensor objects (`get_extent`, multi-index subscripting)
7. 🚩 `register_custom_kernels()` must be called **before** `add_exported_program()`
8. 🚩 Scalar arguments are baked in as literals; bools widen to `ui8`; per-value PSO sub-caches
9. Runtime inputs must be `NDArray(..., backing=StorageKind.METAL)`
10. Failure mode: a malformed MSL body converts fine and fails at `load_function`
11. Worked example: fused attention as a kernel, monkey-patched into a HuggingFace module
12. When *not* to do this — prefer a composite op

**Sources:** `transcripts/coreai-python-metal.md`; `repos/coreai-torch.md`

---

### 24. ⭐ `coreai-authoring-for-ane-vs-gpu`
**Re-authoring a model for the Neural Engine vs the GPU — the rules are opposite**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~6,500 words · *depends on:* 21

**Scope.** The densest practical content in the corpus, most of it from Apple's own agent skills and
found in no video or doc page. The critical framing: ANE and GPU want **inverted** designs, so a
pattern that is required on one is a pessimization on the other.

**Key sections**
1. Why re-author at all: op residency, graph segmentation, and cross-accelerator transfer overhead
2. ANE hard limits: max tensor rank 5; fp16/int8/int16 only; fully static shapes
3. 🚩 The 64-byte width alignment rule — a singleton last axis costs 32× memory at fp16, 64× at int8
4. BC1S layout `(B, C, 1, S)` and the exact permute/reshape recipes
5. `nn.Conv2d(kernel_size=1)` instead of `nn.Linear`, with weight-reshape helpers
6. Transpose bookkeeping at every projection site — "a common source of silent correctness bugs"
7. 🚩 Any fp32 literal falls back off the ANE — `x * (1.0 + s)` is a bug
8. Causal masks: shape `(1, key, 1, query)` and mask value `-40000.0`, **never** `-inf`
9. Per-head attention (`K@Q`, not `Q@Kᵀ`); readonly KV I/O returning **post-RoPE** keys
10. 🚩 fp16 activation overflow: softplus/mish collapse at x≈10.4, logsumexp at 7.63 — and Apple's
    stated fix is to rewrite the PyTorch module, not the converter
11. GPU rules, inverted: standard `(B,S,D)`, `nn.Linear`, one fused SDPA over all heads,
    fused QKV, up-before-gate MLP ordering
12. MoE on GPU: `SwitchLinear` / `SwitchGLU` / `GatherMM` with stacked expert weights
13. PSNR acceptance gates: re-authored vs source >70 dB; ANE vs GPU layout >70 dB;
    compiled vs torch ≥40 dB; post-4-bit ≥35 dB
14. Bottom-up authoring order and the `from_source_model` factory convention
15. Architecture discovery by running code (`register_forward_hook`), not reading it
16. ~20 concrete failure signatures from `common_issues.md`

**Sources:** `01-lead-agent-repo-spotchecks.md`; `repos/apple-coreai-models.md`;
`transcripts/coreai-python-metal.md`; `repos/issues-coreai-stack.md`;
`repos/coreai-torch.md`; `web/community-blogs.md`

---

### 25. `alternative-export-front-ends-mlx2coreai-and-swift-lm`
**Getting to `.aimodel` without PyTorch: the MLX→Core AI bridge and swift-lm's declarative export**
*Audience:* Python ML engineer + Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 19

**Scope.** Two independent third-party stacks that produce Core AI assets from something other than a
`torch.export` program. Valuable both as usable tools and as the clearest available documentation of
Core AI's IR and bundle contracts, because both had to reverse-engineer them.

**Key sections**
1. `mlx2coreai`: capture MLX graphs via `mx.export_function`, lower to Core AI MLIR, write `.aimodel`
2. `convert-mlx-lm-stateful` — the one command that yields a stateful LLM bundle
3. The emitted contract: `main` entrypoint, `input_ids`, `position_ids`, mutable `keyCache`/`valueCache`
4. Dynamic shapes via two-capture "probe differencing" — and why `shapeless=True` alone is insufficient
5. Composite emission for `rms_norm` / `rope` / `sdpa` as private `no_inline` graphs
6. Weights as `DenseResourceElementsAttr` inside `main.mlirb` — there is no separate weight file
7. Op coverage: 156 MLX source names → 121 lowering keys, and the "asset generation ≠ numerical parity" caveat
8. 🚩 Known silent miscompiles: `log2`/`log10` → natural log; left/right shift → AND; boolean masks added
9. 🚩 It pins `coreai-core==1.0.0b1`, below the loader floor — bundles may be rejected by Xcode 27 β3+
10. `swift-lm`: a declarative Swift DSL → LMIR → a versioned JSON "executable contract" → generic lowering
11. Its stateful contract for LFM2 (`keyCache`/`valueCache`/`convCache`) and the SHA-256-pinned bundle
12. Its explicit no-fallback policy: hard-fail with an operation path rather than silently degrade
13. When either is the right tool, and when to go back to `coreai-torch`

**Sources:** `repos/mlx2coreai.md`; `repos/swift-lm.md`; `01-lead-agent-repo-spotchecks.md`;
`repos/issues-community-stack.md`

---

## Pillar 6 — Compress & optimize weights

### 26. ⭐ `coreai-opt-quantization`
**Quantizing with `coreai-opt`: config hierarchy, presets, graph vs eager, and QAT**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~6,000 words · *depends on:* 19

**Scope.** The largest API surface in the compression stack and the most error-prone, because
mis-configuration does not raise — the layer silently disables itself and ships uncompressed.

**Key sections**
1. The universal lifecycle: `__init__` → `prepare(example_inputs)` → calibrate/train → `finalize(backend=)`
2. Three-level config precedence: `module_name_configs` (regex) > `module_type_configs` > `global_config`
3. 🚩 Omitting a spec field applies defaults; passing `None` **disables** compression for that group
4. 🚩 `module_type_configs` keys must be fully qualified (`torch.nn.modules.linear.Linear`)
5. `op_input_spec` / `op_output_spec` / `op_state_spec` — the three op-level tensor groups
6. `QuantizationSpec`: dtype, scheme, formulation, granularity, scale dtype
7. Dtype catalogue: int2/4/8, uint2/4/8, fp8 e4m3/e5m2, fp4 e2m1 with e8m0 MX scales
8. Presets `w8` / `w4` / `w4_per_block(block_size=32)` and what they actually expand to
9. `ExecutionMode.GRAPH` vs `EAGER` — a correctness fork, not a perf knob (fusion, shared observers,
   fake-quant dedup) and "not guaranteed to produce equivalent models"
10. Calibration semantics: observers on, weight FQ on, **activation FQ off**
11. QAT: `QATSchedule`, `step()` cadence, and 🚩 mutual exclusivity with the manual enable/disable API
12. 🚩 Silent self-disable on granularity/block mismatch — watch the logs
13. Per-channel activation quantization and the shape-aware safety downgrade around shared observers
14. KV-cache quantization (graph-mode + Core AI only)
15. `ModelInspector` as the tool for discovering the exact config key strings
16. CoreML export restriction matrix and its exact error messages
17. Real numbers: ResNet50 W8A8 74.22 → 76.56%; SAM3 3 GB → ~430 MB with a quality regression

**Sources:** `repos/coreai-optimization.md`; `transcripts/coreai-python-metal.md`;
`01-lead-agent-repo-spotchecks.md`; `repos/issues-coreai-stack.md`

---

### 27. `coreai-opt-palettization-for-ane`
**Palettization: k-means LUTs, per-grouped-channel scales, sensitivity, and the ANE rank-5 ceiling**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~4,500 words · *depends on:* 26

**Scope.** The compression scheme Apple actually ships for iOS, plus the single hardware limit that
changes every recipe and appears in no talk: turning on per-channel scales produces rank-6 LUTs that
the ANE rejects, silently forcing a GPU fallback.

**Key sections**
1. Palettization vs quantization; effective bits-per-weight math including LUT and scale overhead
2. `PalettizationSpec`: `n_bits` ∈ {1,2,3,4,6,8}, `granularity`, `cluster_dim`, `lut_qspec`,
   `enable_per_channel_scale`
3. Scalar per-tensor / scalar per-grouped-channel / vector palettization
4. 🚩 `enable_per_channel_scale=True` → rank-6 LUT → **ANE rejects it** (max rank 5) → GPU fallback
5. `enable_fast_kmeans_mode` (the default) rounds weights before clustering
6. 🚩 Vector palettization is non-deterministic and only seedable with `num_workers=1`
7. Sensitivity-weighted k-means (SqueezeLLM): squared-gradient hooks, normalization, save/load
8. 🚩 `finalize(backend=CoreAI)` **frees the dense weights in place** — not reversible
9. `mmap_dir` for finalizing very large models without holding weights in RAM
10. 🚩 Silent per-layer skip on incompatible granularity — only a warning
11. Real recipe: SAM3 iOS — image encoder 4-bit gs32, text encoder 6-bit gs8, detector fp16
12. Why iOS defaults to palettization and macOS to linear INT4 (and 🚩 linear INT4 SIGSEGVs the ANE
    pre-compiler)
13. Requires a C++ toolchain at runtime (vendored k-means is JIT-compiled)

**Sources:** `repos/coreai-optimization.md`; `repos/apple-coreai-models.md`;
`transcripts/coreai-python-metal.md`; `repos/issues-coreai-stack.md`

---

### 28. `coreai-opt-pruning-joint-and-mixed-precision`
**Pruning, joint compression, mixed precision, and compressing an already-converted asset**
*Audience:* Python ML engineer · *E:* moderate · *Len:* ~4,000 words · *depends on:* 27

**Scope.** The remaining coreai-opt surface: magnitude pruning with schedules, stacking palettization
with activation quantization, assigning precision per layer from a sensitivity sweep, and the
PyTorch-free path that rewrites weights inside an existing `.aimodel`.

**Key sections**
1. Magnitude pruning: unstructured global top-k vs channel-structured L1 ranking
2. 🚩 Channel-structured sparsity rounds **down** to multiples of 1/num_channels
3. `ConstantSparsitySchedule` vs `PolynomialDecaySchedule` (formula, `update_frequency`)
4. Joint compression order: palettize → finalize → quantize activations → calibrate → finalize
5. Why the LUT must be INT8 to unlock the W8A8 runtime path; 🚩 CoreAI-backend-only
6. Mixed precision: sensitivity → greedy recipe → per-layer `module_name_configs` with `global_config=None`
7. BPW accounting and the accuracy-vs-BPW curve (ResNet50 uniform 4-bit 65.87% vs 3.95 BPW 70.27%)
8. `coreai_opt.casting.cast_to_16_bit_precision` on an `ExportedProgram` — stronger than `.half()`
   or `torch.autocast`, and 🚩 always compress first, cast second
9. `coreai_utils.{quantize,palettize,sparsify}_weights` — compressing an `AIProgram` with no PyTorch
10. n:m structured sparsity and joint sparse+quant / sparse+palettized
11. Running a systematic compression sweep (Apple's `model-compression-exploration` skill protocol)
12. Reporting a size/quality frontier instead of one number

**Sources:** `repos/coreai-optimization.md`; `repos/apple-coreai-models.md`;
`01-lead-agent-repo-spotchecks.md`

---

## Pillar 7 — Run models on device with Core AI

### 29. ⭐ `coreai-swift-runtime-api`
**The Core AI Swift runtime: `AIModel`, `InferenceFunction`, `NDArray`, and the low-level fast path**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,500 words · *depends on:* 19

**Scope.** Everything between "I have an `.aimodel`" and "I have outputs", including the memory model.
Core AI is one of the heaviest users of modern Swift ownership features in the whole SDK, and the API
is unreadable without that background — so this guide teaches both. Ends with the optimization tier.

**Key sections**
1. `AIModel` — `init(contentsOf:options:)` (async because it specializes), `functionNames`,
   `loadFunction(named:)` (nil for unknown, throws on failure)
2. `AIModelAsset` — inspect without specializing; `isValid(at:)` as a cheap preflight; `Summary`; metadata
3. `InferenceFunctionDescriptor` — `inputNames`/`outputNames`/`stateNames`, per-name descriptors,
   and adapting to model changes without code changes
4. `NDArray`: shape, strides, scalar type, the 33-case `ScalarType` zoo
5. The four view types (`View`/`MutableView`/`RawView`/`MutableRawView`) and Span vs MutableSpan
6. `contiguousElements` can be `nil`; `withUnsafe(Mutable)Pointer`; 🚩 `shape` is a non-escapable
   `Span<Int>` with no `Sequence` conformance
7. `slice(at:)` vs `mutatingSlice(at:)`; trailing dims default to `.all`
8. `run(inputs:states:outputViews:)`, `consuming` MutableViews, and the `consume` operator
9. `Outputs.remove(_:)` is a destructive take-once; `InferenceValue.ndArray` is a **consuming** read
10. Concurrency: `InferenceFunction` is Sendable and safely concurrent — 🚩 at the cost of extra buffers
11. Image I/O: `ImageDescriptor` and `CVMutablePixelBuffer`
12. `NDArrayDescriptor.preferredStrides` — 🚩 ignoring it may cost a layout copy on **every** run
13. `resolvingDynamicDimensions(_:)`, `minimumByteCount`, and the `-1` vs `?` convention
14. `InterleaveLayout`: block strides and the exact element-offset formula
15. Pipelining: `encode(... to: ComputeStream)` (throws, not async), `AsyncValue`, `AsyncMutableValue`
16. Zero-copy interop: MTLBuffer (must be `shared`) and IOSurface, and the safety contracts

**Sources:** `web/apple-docs-coreai.md`; `transcripts/coreai-intro.md`;
`repos/apple-coreai-models.md`; `repos/swift-lm.md`

---

### 30. ⭐ `coreai-specialization-and-caching`
**Specialization and the model cache: the first-launch stall, cache keys, bookmarks, and app groups**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,000 words · *depends on:* 29

**Scope.** The largest source of first-launch latency and disk-usage bugs. Explains what
specialization is, when it happens, what the cache key actually is, how to delete the source file and
keep running, and the recovery ladder when a load gets wedged.

**Key sections**
1. What specialization is: compile (expensive) then generate per-compute-unit artifacts
2. Tied to **both** device hardware and OS version — an OS update always invalidates every entry
3. 🚩 The cache key is (source URL + `SpecializationOptions`) — varying options duplicates multi-GB entries
4. `AIModelCache.default.model(for:options:)` returns nil without specializing — use it to gate UI
5. `AIModel.specialize(...)` controls **when**, not how much work
6. `Policy` and `PurgeConditions` (`.sourceAssetChangedOrDeleted`, `.storagePressure`) vs `.persistent`
7. `bookmarkData` + `init(resolvingBookmark:)` — delete the source `.aimodel` and keep the cache
8. 🚩 Bookmarks do not pin the entry; only a live `AIModel` does. Malformed → throws; stale → nil
9. App-group sharing: `AIModelCache(appGroup:)` + entitlement, and the nil-return failure modes
10. `SpecializationOptions`: `.default`, `.cpuOnly`, `preferredComputeUnitKind`, `expectFrequentReshapes`
11. 🚩 Every new *input shape* on a dynamic graph re-specializes — bucket your prefill chunks
12. The recovery ladder: `deleteEntries(for:)` → retry → fall back to `.default` → check the cache
13. Measured cold vs warm: 31.7 s vs 10.8 s engine-ready for a 4.6 GiB bundle on iPhone 17 Pro
14. Hiding the stall in a first-run/feature-intro experience

**Sources:** `web/apple-docs-coreai.md`; `transcripts/coreai-intro.md`; `repos/noema-ios.md`;
`repos/issues-community-stack.md`; `web/community-blogs.md`

---

### 31. ⭐ `coreai-aot-compilation-and-per-arch-distribution`
**Ahead-of-time compilation with `coreai-build`, and shipping one `.aimodelc` per architecture**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,000 words · *depends on:* 30

**Scope.** On iOS this is not an optimization — it is **mandatory** for large decode graphs, because
iOS cannot JIT-compile the exported IR, and the failure is a maximally misleading "No such file or
directory". Covers the toolchain, the per-architecture artifact fan-out, and the hand-edit nobody
documents.

**Key sections**
1. 🚩 iOS cannot JIT the MLIR — the ENOENT failure signature and what it really means
2. `xcrun coreai-build compile Model.aimodel --platform iOS --min-deployment-version 27.0 --output dir/`
3. Output naming: `Model.<arch>.aimodelc`, matched at runtime by `AIModel.deviceArchitectureName`
4. `--preferred-compute` and the architecture flag (`h18p` = iPhone 17 Pro class)
5. 🚩 AOT only targets Apple-Intelligence-capable hardware (A17 Pro / M1 / M2)
6. 🚩 AOT does **not** eliminate on-device specialization
7. 🚩 The bundle hand-edit: point `metadata.json`'s `assets.main` at the compiled filename
8. Hosting variants remotely and downloading only the matching architecture via Background Assets
9. Loading is the same `init(contentsOf:)` — no code change
10. 🚩 Compute unit is fixed by *export shape*, not a runtime flag: static → ANE, dynamic → GPU.
    Ship two bundles if you need both.
11. Known crashes: ANE pre-compiler SIGSEGV on linear blockwise INT4; macOS `.aimodelc` load
    regression while iOS AOT works
12. Verifying an AOT artifact before you ship it

**Sources:** `web/apple-docs-coreai.md`; `transcripts/coreai-intro.md`; `web/community-blogs.md`;
`repos/issues-coreai-stack.md`; `repos/issues-community-stack.md`; `repos/noema-ios.md`

---

### 32. `coreai-model-bundles`
**Model bundles: `metadata.json` 0.2, tokenizers, function maps, and the errors you'll hit**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 29

**Scope.** A `.aimodel` alone is rarely enough — LLMs need a tokenizer, diffusion needs several
models, VLMs need three assets. The bundle layout is the de-facto interchange format that Apple's
Swift package, `mlx2coreai`, `swift-lm`, and shipping apps all target, and it is documented nowhere.

**Key sections**
1. Bundle vs asset: 🚩 an `.aimodel` is a **directory**, and pointing `resourcesAt:` at it fails with
   a misleading `unsupported metadata_version '0.1'`
2. `metadata.json` schema 0.2: `kind` (llm/vlm/diffusion/segmenter), `assets` role map, kind-specific block
3. The `language` block: tokenizer, `vocab_size`, `max_context_length`, `embedded_tokenizer`, `function_map`
4. `function_map` for chunked-static models (role → physical function names)
5. The `vision` block for VLMs: image size, patch size, image token count/id, mean/std, rescale
6. Tokenizer directory contents (tokenizer.json required; chat template; added tokens)
7. Bundle-name conventions that carry meaning (`ios-ane/`, `ios-gpu/`, `gpu-pipelined/`, `macos/`)
   and 🚩 why you must match exact path components, not substrings
8. `.aimodel` internals: `main.mlirb`, `main.hash`, inner `metadata.json`, the `producer` key
9. 🚩 The `coreai-core >= 1.0.0b2` producer gate and the pre-b2 signature
10. `verify()` and what it does *not* check
11. Xcode: adding the folder with "Apply once to folder"; Compile Sources placement
12. Synthesizing a bundle around a bare `.aimodel` (a working reference implementation)

**Sources:** `repos/apple-coreai-models.md`; `repos/noema-ios.md`; `repos/mlx2coreai.md`;
`repos/swift-lm.md`; `repos/issues-community-stack.md`

---

### 33. `coreai-llm-engines-and-guided-generation`
**Running an LLM on Core AI: `CoreAILanguageModel`, engine selection, KV strategies, and xgrammar**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* 32

**Scope.** The layer that turns a converted `.aimodel` into a working chat model. Covers the four
engines and why the choice is made *for* you by graph structure, the KV-cache strategies and their
memory math, prefill chunking, and how `@Generable` is enforced on a non-Apple model.

**Key sections**
1. `CoreAILanguageModel(resourcesAt:mode:variant:kvCacheStrategy:)`; lazy vs eager load
2. `EngineFactory` auto-detection from graph function names → structure → engine + specialization options
3. The four engines: pipelined (GPU, no logits), sequential (CPU sampling, logits), static-shape (ANE),
   sequential VLM
4. 🚩 The pipelined GPU engine cannot return logits — which rules out guided generation and
   continuation-style eval on the default macOS path
5. `KVCacheStrategy`: `.auto` / `.fixedSize` / `.growing` / `.chunked` — 🚩 `.chunked` is unimplemented,
   `.fixedSize` pre-allocates the full context and slows every step
6. Prefill chunking math: a 32K prompt on a 152k-vocab model needs 9.6 GB of fp16 logits unchunked
   vs 155 MB at 512
7. 🚩 S=1 decode-only bundles cannot take block prefill (`COREAI_CHUNK_THRESHOLD=1`)
8. 🚩 The pipelined engine cannot reuse KV across turns — pipeline overshoot past EOS pollutes state
9. Cross-turn reuse without a KV API: a session-long decoder with a fed-token log
10. Sampling: greedy/temperature/topK/topP/minP, CPU vs on-GPU MPSGraph samplers
11. Guided generation via xgrammar: DLPack bitmasks, `ConstrainedGenerationSession`, termination detection
12. Streaming detokenization, reasoning-tag parsing, and tool-call parsing across model families
13. 🚩 Hybrid/SSM models hit `Expected 2 states, got 4` on the stock engine
14. VLM path: the three-asset contract and image-placeholder expansion

**Sources:** `repos/apple-coreai-models.md`; `repos/noema-ios.md`; `transcripts/coreai-intro.md`;
`repos/issues-community-stack.md`; `01-lead-agent-repo-spotchecks.md`

---

## Pillar 8 — Debug numerics & profile

### 34. ⭐ `coreai-debugging-numerics-psnr-and-fp16`
**Debugging numerics: Core AI Debugger, sync points, PSNR gates, and fp16 overflow**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,500 words · *depends on:* 24

**Scope.** "It converted, but the answers are wrong." The most reusable debugging idea in the whole
corpus is the Debugger's *sync point* model — automatically paired ops whose outputs should match a
PyTorch reference, scored and sortable — and the workflow that turns a quality regression into a
one-block config change.

**Key sections**
1. Triage order: debug gauge → Instruments → Core AI Debugger
2. The four Debugger panes; op grouping by PyTorch module; tracing back to the originating Python line
3. Running on a chosen hardware target and seeing the specialized graph
4. Producing a reference run: `save_intermediates(...)` → `.aimodelintermediates`
5. 🚩 Debug metadata requires `USE_LOCAL_COREAI=1` and `ENABLE_DEBUG_INFO=1` in the preview
6. Sync points and the five similarity metrics (PSNR default, MAE, MSE, max-abs, mean-relative)
7. The worked diagnosis: low-PSNR cluster in the detector decoder → 4% of params → exclude it from
   quantization → baseline quality at a fraction of the size
8. Apple's PSNR acceptance gates, restated as CI thresholds
9. The `coreai_torch.debugging` toolkit nobody demos: NaN/Inf bisection validators, cross-framework
   comparators, graph-isomorphism diff, op benchmarking, three search strategies
10. 🚩 fp16 overflow on ANE: per-op thresholds and stable decompositions you must write yourself
11. 🚩 Silent-miscompile catalogue: `optimize()` deleting broadcast-significant ops; GPU `floor` as
    identity; cast round-trip folding; bool-mask tensor clobbering
12. The four A/B gates every conversion should run (eager vs Core AI; optimize on/off; CPU/GPU/ANE;
    greedy token oracle)
13. 🚩 `Mode.DEBUG` is the default and ships torch stack traces — use `strip_debug_info` for release

**Sources:** `transcripts/coreai-python-metal.md`; `repos/coreai-torch.md`;
`web/apple-docs-coreai.md`; `repos/issues-coreai-stack.md`; `01-lead-agent-repo-spotchecks.md`

---

### 35. `coreai-instruments-and-debug-gauge`
**Profiling Core AI: the Xcode debug gauge and the Instruments template**
*Audience:* Swift app dev · *E:* moderate · *Len:* ~3,000 words · *depends on:* 30

**Scope.** "It runs, but it's slow or it stalls." Two tools with overlapping-but-different event
models — a discrepancy that will confuse anyone moving between them.

**Key sections**
1. The debug gauge: where it appears and 🚩 that the target must **directly** link CoreAI.framework
2. Gauge event types (Inference / Load / Specialization) and live streaming activity
3. 🚩 The More menu is unavailable for events recorded before you opened the report
4. Exporting captured inputs (`.npy` single / zipped `.npz` multi) into a Debugger session
5. The Instruments template: four bundled instruments (Core AI, Neural Engine, GPU, Time Profiler)
6. Four event categories in order — Specialization / Load / Setup / Inference
7. 🚩 The gauge shows three, Instruments shows four, and the two use **different colors** for
   Load and Specialization
8. Reading the model::function track hierarchy
9. Frequent Load events = you are reloading models (an explicit bug signal)
10. Diagnosing the growing-inference-interval signature that means "you need states"
11. Aggregation differences (total vs max vs median) across the two UIs
12. Handing off to the Core AI Debugger when the problem turns out to be numerical

**Sources:** `web/apple-docs-coreai.md`; `transcripts/coreai-intro.md`;
`transcripts/coreai-python-metal.md`

---

### 36. ⭐ `benchmarking-on-device-models-honestly`
**Benchmarking on-device models honestly: speed, memory, energy, quality, and the traps**
*Audience:* both · *E:* strong · *Len:* ~5,000 words · *depends on:* 1

**Scope.** Cross-cutting methodology, backed by an unusual amount of real measurement in this corpus
and by an equal amount of evidence that most published numbers are wrong. Teaches the reader to
produce numbers that survive scrutiny — and to read other people's numbers skeptically.

**Key sections**
1. Why one number is always wrong: burst vs sustained vs energy vs quality give four rankings
2. 🚩 Debug vs Release contamination — one benchmark's own MLX row inflated a lead from 1.4× to 1.6×
3. Cold vs warm: 71 vs 181 tok/s on the same bundle; report both and say which UX each models
4. Thermal protocol: 600 s unplugged retention (Core AI 56%, MLX 38%, ANE 67%)
5. Energy per token via `powermetrics` — and why the lowest-wattage runtime had the worst joules/token
6. Memory is not comparable across runtimes (mmap'd vs wired vs out-of-process)
7. Quality on the same axis: GSM8K-style scoring alongside speed; no runtime is Pareto-dominant
8. 🚩 State the *build* per row — a shipped default quant scored 3.0% where a demoted build scored 87%
9. Interleaved ABBA rounds, fresh process per cell, medians hide heavy tails
10. Page-cache control (`F_NOCACHE`) and the absurd-speedup canary
11. MLX-specific: `mx.eval` inside the timed region, or lazy evaluation defers the work past your timer
12. Disclosing jetsams, failed runs, and hardware/OS/Xcode versions
13. A reusable report template

**Sources:** `web/community-blogs.md`; `repos/mlx-swift-examples.md`; `repos/issues-mlx-stack.md`;
`repos/apple-coreai-models.md`; `repos/mlx-core.md`

---

## Pillar 9 — MLX

### 37. ⭐ `mlx-fundamentals`
**MLX fundamentals: lazy evaluation, unified memory, streams, and `mx.compile`**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,500 words · *depends on:* 1

**Scope.** The four concepts that make MLX behave unlike NumPy or PyTorch, and where every newcomer's
first bug comes from. Includes the NumPy divergences that silently produce wrong answers.

**Key sections**
1. Lazy evaluation: the graph, when to call `mx.eval`, and every implicit evaluation trigger
2. 🚩 `print(loss)` before `mx.eval(loss, params)` triggers a forward-only partial evaluation
3. Unified memory: you place *operations* (`stream=`), never arrays; automatic cross-stream deps
4. Streams: `default_stream`, `new_stream` (thread-affine!), `new_thread_local_stream`
5. `mx.compile`: what it fuses (element-wise/broadcast only — never matmul or reduction)
6. The four recompilation triggers and `shapeless=True`'s limits
7. 🚩 Captured arrays become frozen constants — `inputs=`/`outputs=` state capture, incl. `mx.random.state`
8. 🚩 Shapeless silently bakes in shapes computed with Python arithmetic on `.shape`
9. Indexing divergences: no bounds checking; slicing copies; duplicate-index writes are nondeterministic
10. `array.at[idx].add(...)` as the correct scatter-accumulate
11. 🚩 `mx.empty` is literally `mx.zeros`
12. Interop: buffer protocol vs DLPack, zero-copy rules, PyTorch ≥2.12 MPS shared storage,
    🚩 and how NumPy views silently break autodiff
13. Memory knobs: active vs cache vs peak, `set_wired_limit`, `iogpu.wired_limit_mb`
14. Function transforms: `grad` / `value_and_grad` / `vmap` / `vjp` / `jvp` / `checkpoint` / `custom_function`

**Sources:** `web/mlx-docs-site.md`; `repos/mlx-core.md`; `repos/issues-mlx-stack.md`;
`repos/mlx-examples.md`

---

### 38. `mlx-custom-metal-kernels`
**Custom Metal (and CUDA) kernels in MLX with `mx.fast.metal_kernel`**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~3,500 words · *depends on:* 37

**Scope.** Writing a kernel when a fused primitive doesn't exist — including the differentiable case,
which needs atomics and an init value, and delivered a measured 40× on a real backward pass.

**Key sections**
1. What `mx.fast.metal_kernel` generates for you from inputs, outputs, templates, and MSL attributes
2. Automatic `<name>_shape` / `_strides` / `_ndim` injection when referenced
3. 🚩 `grid` is in **threads** (dispatchThreads), not threadgroups
4. `ensure_row_contiguous` and its silent copies
5. `template=` for dtype specialization; the auto-included `utils.h` helpers
6. 🚩 `compile_options={'math_mode': ...}` — the default `'safe'` preserves `exp(-inf)==0`, which
   masked softmax depends on
7. Differentiable kernels: `atomic_outputs=True` + `init_value=0` + simdgroup pre-reduction
8. Wiring a kernel into `mx.custom_function` with a `.vjp`
9. 🚩 Constructing a kernel JIT-compiles a Metal library — hoist it out of hot loops
10. CUDA twins: `cuda_kernel` and `precompiled_cuda_kernel` (PTX/cubin)
11. Measured wins: grid_sample forward 55.7 → 6.7 ms; vjp 676.4 → 16.7 ms

**Sources:** `web/mlx-docs-site.md`; `repos/mlx-core.md`; `repos/mlx-examples.md`

---

### 39. `mlx-lm-cli-and-python-api`
**`mlx-lm` end to end: every CLI, the generation API, and the model zoo**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~6,000 words · *depends on:* 37

**Scope.** The tabulated reference for the 18 console scripts plus the Python generation API. The most
requested artifact for anyone driving MLX from a shell, and the place to document the undeclared
dependencies and stale defaults that break a fresh install.

**Key sections**
1. `load` / `generate` / `stream_generate` / `generate_step` — signatures and return shapes
2. `GenerationResponse` fields and what each timing means
3. Sampling: `make_sampler` (temp / top_p / min_p / top_k / XTC) and application order
4. 🚩 `temp == 0` short-circuits to argmax, silently disabling top_k / min_p / XTC
5. Logits processors: repetition / presence / frequency penalties and the GPU-resident token ring
6. `mlx_lm.generate` / `chat` / `convert` / `fuse` / `evaluate` / `perplexity` / `benchmark` /
   `cache_prompt` / `manage` / `upload` / `share`
7. The model zoo: 121 architectures including the 2026 families (gemma4, qwen3_5, deepseek_v32,
   qwen3_next, kimi, minimax, laguna) and what per-layer config schemas now look like
8. Tokenizers: streaming detokenizers, thinking-token detection, the ten tool-call parsers and
   how they're auto-selected from the chat template
9. 🚩 `rich` and `regex` are imported but not declared — a bare `pip install` breaks `chat` and `lora`
10. 🚩 `stream_generate(max_tokens=0)` raises `UnboundLocalError`; `generate()` returns `None` on empty
11. 🚩 CVE-2026-5843: `config.json`'s `model_file` executed arbitrary Python — now behind
    `trust_remote_code`
12. 🚩 transformers ≥5.13 breaks imports on the current PyPI release
13. Porting a new architecture: the `ModelArgs`/`Model`/`sanitize`/`make_cache`/`shard` contract

**Sources:** `repos/mlx-lm.md`; `repos/issues-mlx-stack.md`; `web/mlx-docs-site.md`

---

### 40. `mlx-quantization`
**Quantizing models with MLX: affine, MXFP4, MXFP8, NVFP4, and learned quantization**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,000 words · *depends on:* 39

**Scope.** Four quantization modes with different group sizes, bit widths and scale types, plus the
four learned-quantization CLIs (DWQ / AWQ / GPTQ / dynamic) — and the correctness traps that make some
combinations silently produce garbage on M5.

**Key sections**
1. The mode table: affine (gs 32/64/128, 2–8 bits, has biases) vs mxfp4 / mxfp8 / nvfp4 (no biases)
2. E8M0 block scales and how the MX format lines up across MLX, coreai-opt, and Metal
3. `mx.quantize` / `dequantize` / `quantized_matmul` / `gather_qmm` / `qqmm`
4. `nn.quantize(model, class_predicate=, quantize_input=)` and `QQLinear` for QAT
5. `mlx_lm.convert` static quantization and mixed-precision recipes (Q4_K_M-style rules)
6. Loading externally-quantized checkpoints: AutoAWQ / GPTQ / compressed-tensors
7. Learned quantization: DWQ (KD on scales/biases), AWQ (grid + clip search), GPTQ (Hessian),
   dynamic (gradient sensitivity to a BPW target)
8. The shared calibration corpus and where it caches
9. 🚩 nvfp4 `global_scale` is not supported on the Metal backend
10. 🚩 Affine `gather_qmm` corrupts silently on M5/NAX when gathered rows >32768 and rows%64≠0 —
    unwritten rows expose recycled memory
11. 🚩 A second `K % 64 != 0` defect that also hits mxfp4
12. Activation quantization: only nvfp4/mxfp8, only bias-free linears
13. Writing regression tests that poison the output buffer so unwritten rows are detectable

**Sources:** `repos/mlx-lm.md`; `repos/mlx-core.md`; `repos/issues-mlx-stack.md`;
`web/mlx-docs-site.md`

---

### 41. `mlx-lm-server-batching-and-scaling`
**Serving with `mlx_lm.server`: OpenAI compatibility, continuous batching, prompt caching, and distributed**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,500 words · *depends on:* 39

**Scope.** Turning MLX into a local API endpoint that agents can talk to — including Xcode's own
Intelligence provider — and scaling it up: continuous batching for subagent fan-out, trie-backed
prompt caching, and multi-machine sharding when the model doesn't fit.

**Key sections**
1. Endpoints, request/response fields, streaming, keepalives, `stream_options.include_usage`
2. Concurrency: `--decode-concurrency` (32) and `--prompt-concurrency` (8); how sequences migrate
3. `BatchGenerator`: `insert` / `insert_segments` / `next_generated` / cache extraction
4. Server prompt caching: `PromptTrie` + `LRUPromptCache`, exact/prefix/rewound hits,
   category-aware eviction that keeps system prompts longest
5. Tool calls and reasoning over the wire; 🚩 `message.reasoning` is not OpenAI's `reasoning_content`
6. Pointing agents at it: OpenCode, and **Xcode → Settings → Intelligence → Add Chat Provider →
   Locally Hosted**
7. `ChatCompletionsLanguageModel` → this server → any HF model behind `LanguageModelSession`
8. 🚩 Passing `seed` disables batching entirely; a draft model makes the model non-batchable
9. 🚩 Not recommended for production ("only basic security checks"); errors surface as HTTP 404
10. 🚩 Livelock: the batch loop can burn GPU while delivering zero tokens — heartbeat detectors miss it;
    delivery-staleness is the correct signal
11. 🚩 Idle busy-poll pins a CPU core
12. Distributed: `mlx.launch`, hostfiles, ring vs JACCL vs MPI vs NCCL, Thunderbolt RDMA on macOS 26.2+
13. `mlx.distributed_config --auto-setup`, and 🚩 `rdma_ctl enable` must be run from Recovery
14. Tensor parallel vs pipeline parallel in `mlx-lm`; `mlx_lm.share` for node-to-node distribution

**Sources:** `repos/mlx-lm.md`; `transcripts/evals-mlx.md` (session 232); `web/mlx-docs-site.md`;
`repos/mlx-core.md`; `repos/issues-mlx-stack.md`; `02-lead-agent-corpus-gaps-filled.md`

---

### 42. `mlx-lm-finetuning-lora`
**Fine-tuning on Apple silicon: LoRA, QLoRA, DoRA, and full fine-tuning with `mlx-lm`**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~5,000 words · *depends on:* 39

**Scope.** The surviving on-device adaptation story now that Foundation Models adapters are
discontinued. Full workflow from dataset to a fused, quantized, shippable model.

**Key sections**
1. Why this matters more in 2026: FM custom adapters are gone in OS 27
2. `mlx_lm.lora` flags and the YAML config schema
3. What gets adapted: Linear, QuantizedLinear, SwitchLinear, Embedding, and auto-discovered keys
4. LoRA vs DoRA — 🚩 DoRA dequantizes the base weight on **every** forward pass
5. Dataset formats: chat / tools / completions / raw text, plus HF datasets
6. Prompt masking, gradient accumulation, gradient checkpointing, LR schedules with warmup
7. 🚩 `grad_checkpoint` monkey-patches `type(layer).__call__` — a process-global side effect
8. Optimizers: adam / adamw / muon / sgd / adafactor, and Muon's documented exclusions
9. Distributed training: batch striding by rank, `average_gradients`, FSDP
10. Experiment tracking (W&B / SwanLab) and 🚩 the callback that gets silently overwritten
11. `mlx_lm.fuse`, de-quantize-on-fuse, GGUF export limits
12. The WWDC25 knowledge-injection demo as a worked example
13. 🚩 Known blockers: scatter VJP through MoE routing; a hang at rank 16 with 7 target modules

**Sources:** `repos/mlx-lm.md`; `repos/mlx-examples.md`; `repos/issues-mlx-stack.md`;
`forums/forum-pain-points.md`

---

### 43. ⭐ `mlx-swift-in-an-app`
**Shipping an MLX model inside a Swift app: `ModelContainer`, `ChatSession`, tools, and concurrency**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,000 words · *depends on:* 37

**Scope.** The Swift deployment path, pinned to the 3.x redesign that decoupled HuggingFace. Covers
the concurrency model (the #1 source of consumer errors under Swift 6 strict concurrency), the 12
generation entry points, and the media/tool plumbing.

**Key sections**
1. Package setup for `mlx-swift-lm` 3.x and the three integration styles
2. 🚩 3.x broke the HuggingFace dependency: `Downloader` / `Tokenizer` / `TokenizerLoader` are protocols
3. The `MLXHuggingFace` macros (`#hubDownloader`, `#huggingFaceTokenizerLoader`,
   `#huggingFaceLoadModelContainer`) and 🚩 the `-skipMacroValidation` build requirement
4. `ModelContainer` / `ModelContext` / `perform` — and why `MLXArray` is not `Sendable`
5. `ChatSession`: all initializers, history vs prompt-cache rehydration, `streamDetails`
6. `generate` vs `generateTask` vs `generateTokens` — 🚩 breaking out of a stream early leaves GPU work
   in flight against the same KV cache
7. `GenerateParameters` — 🚩 `temperature` defaults to **0.6**, not 0
8. VLM input: images/videos, `UserInput.Processing(resize:)`, 🚩 the default 512×512 downscale
9. 🚩 EXIF orientation, PhotosPicker `Transferable`s, security-scoped file URLs
10. Tool calling: `Tool<Input,Output>`, the ten wire formats, streaming `ToolCallProcessor`,
    and the assistant-tool_calls-then-tool-results ordering
11. Reasoning models: `ReasoningConfig` and per-family prompt strategies
12. LoRA adapters at runtime: `LoRAContainer`, scoped `perform(with:)`
13. Model compatibility: what `model_type` drives, and the 62/17/10 registries
14. 🚩 `swift test` does not work — use `xcodebuild test` with the documented flags

**Sources:** `repos/mlx-swift-lm.md`; `repos/mlx-swift-examples.md`; `repos/issues-mlx-stack.md`;
`repos/noema-ios.md`

---

### 44. `mlx-kv-cache-and-speculative-decoding`
**KV caching, prompt reuse, and speculative decoding in MLX (Python and Swift)**
*Audience:* both · *E:* strong · *Len:* ~5,000 words · *depends on:* 39

**Scope.** How to make the second turn fast, and how to make decode faster than one token per forward
pass. The two topics belong together because speculative decoding *requires* a trimmable cache, which
excludes a whole class of models.

**Key sections**
1. The cache-type matrix: KVCache, Quantized, Rotating, Chunked, Concatenate, Arrays, Batch variants
2. Trimmability rules — and what they gate
3. Prompt caches on disk: the safetensors layout, `mlx_lm.cache_prompt`, the `<query>` prefix trick
4. Cross-turn reuse: longest-shared-prefix trimming so TTFT is O(new turn), not O(history)
5. 🚩 In Swift, `maybeQuantizeKVCache` takes `inout [KVCache]` and replaces *elements* — the caller
   loses all context after `quantizedKVStart`
6. 🚩 `RotatingKVCache.to_quantized()` raises `NotImplementedError`, so `--kv-bits` crashes on the
   first request for Gemma 4 and other hybrid models
7. 🚩 `RotatingKVCache` becomes permanently untrimmable once its window wraps
8. 🚩 QuantizedKVCache *raises* peak memory 30–73% during prefill while lowering it in decode —
   mitigate with a smaller `prefill_step_size`
9. `--kv-bits` is a capacity lever, not a throughput lever (measured: −7.4% decode at 0.5K)
10. Speculative decoding: draft/verify/rewind, tokenizer compatibility, acceptance rate
11. 🚩 Temp=0 speculative decoding is **not** bit-identical — exact bf16 logit ties break differently
12. MTP drafters and the manual type registration they require
13. 🚩 The L=8→12 kernel-routing cliff sits exactly where verify steps live
14. 🚩 mlx-lm strips MTP weights at load and shifts norm weights, making MTP checkpoints 56–79% slower

**Sources:** `repos/mlx-lm.md`; `repos/mlx-swift-lm.md`; `repos/issues-mlx-stack.md`;
`repos/noema-ios.md`

---

### 45. `mlx-numerical-correctness-on-apple-silicon`
**Numerical reproducibility and silent corruption in MLX: TF32, NAX, and hardware-gated bugs**
*Audience:* Python ML engineer · *E:* strong · *Len:* ~4,000 words · *depends on:* 37

**Scope.** The guide that saves someone a week. MLX's fastest paths are hardware-gated, undocumented,
and on by default — so the same code produces different (and occasionally wrong) numbers on M5/A19
than on M2, while every op-level parity test passes.

**Key sections**
1. `MLX_ENABLE_TF32` defaults to **1**, is undocumented, and is read once at first use
2. NAX gating: `is_nax_available()` = macOS ≥26.2 && GPU arch gen ≥17 — so the flag looks inert on M3
3. TF32 affects anything built from GEMMs, including unfused attention paths
4. Batch-vs-single divergence on gen-17 from two independent mechanisms; why rtol=1e-5 cannot hold
5. 🚩 A19 shape-gated wrong fp32 matmul (M=N=64 with K≤127, etc.) — not fixed by disabling TF32
6. 🚩 Silent MoE corruption on M5 (rows>32768 && rows%64≠0) — unwritten rows show recycled memory
7. 🚩 Fused SDPA coverage is narrow and the fallback is **silent**: vector path {64,96,128,256};
   full path {64,80,128}. Gemma 4 global layers (d=512) never fuse.
8. Detecting the fallback (Metal System Trace); there is no log and no predicate
9. 🚩 `MLX_SDPA_BLOCKS` must be a multiple of 32 or attention corrupts silently
10. 🚩 The 832-thread pipeline cap on M1/M2 makes an unchecked dispatch return **all zeros**
11. Unfused prefill transient memory math and why chunking only bounds it linearly
12. Version-gating on recent correctness fixes
13. A reproducibility checklist for papers and benchmarks

**Sources:** `repos/issues-mlx-stack.md`; `repos/mlx-core.md`; `web/mlx-docs-site.md`

---

## Pillar 10 — Evaluate & iterate

### 46. ⭐ `evals-your-first-evaluation`
**Your first evaluation: the `Evaluation` protocol, metrics, aggregation, and the hill-climbing loop**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* 3

**Scope.** The foundation every other Evaluations guide assumes, plus the workflow Apple names
"evaluation-driven development". Includes the Xcode 27 report and Compare view, which is where the
analysis actually happens and which is documented in text nowhere.

**Key sections**
1. Why: "generative models break a contract fundamental to software testing"
2. The framework is **not** LLM-only — any stochastic system, including classifiers
3. The four responsibilities: `dataset` → `subject(from:)` → `evaluators` → `aggregateMetrics(using:)`
4. Loaders: `ArrayLoader`, `JSONLoader`, `StreamLoader` (🚩 JSONLoader silently skips malformed rows)
5. `ModelSample`, `ModelSubject`, `StructuredTranscript`
6. `Metric` and its result factories: passing / failing / scoring / ignore
7. `MetricsAggregator`: mean, median, mode, min, max, stddev, variance, `custom(of:label:_:)`, `group`
8. Running it: `@Test(.evaluates(myEvaluation))`, `EvaluationContext.current.result`, `#expect`
9. Reading results: `.summary` / `.detailed` DataFrames and typed column subscripts
10. The Xcode 27 Evaluations report: charts, results table, per-sample assistant editor
11. The Compare view, `notes:` labeling, and the auto-generated attachment
12. 🚩 A passing test does not mean good output — pair pass/fail metrics with scored ones
13. 🚩 The `@Guide(count:)` cautionary tale: 100% pass rate hiding a degenerate distribution
14. Develop → evaluate → analyze; change one variable; promote the winner into the baseline
15. Hill-climbing more than prompts: tools, model choice, dataset, evaluators themselves
16. Using Evaluations as the regression gate against OS-update model drift

**Sources:** `transcripts/evals-mlx.md` (sessions 298/335); `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`

---

### 47. `evals-model-judges`
**Model judges: `ModelJudgeEvaluator`, score dimensions, and prompts that produce actionable scores**
*Audience:* Swift app dev · *E:* strong · *Len:* ~4,500 words · *depends on:* 46

**Scope.** Qualitative measurement. Judge design is a distinct skill from writing code-based
evaluators, and the failure mode — uniform, uninformative scores — has a specific diagnosis.

**Key sections**
1. What a judge is: a subjective rating applied *consistently* across your whole dataset
2. 🚩 The judge must be at least as capable as the model under test (on-device → PCC judge)
3. The four parts, and that the framework handles all but the scoring guide
4. `ScoringScale`: `.numeric`, `.passFail`, `.custom(SomeEnum.self)`
5. 🚩 Use an **even** number of levels — 1–4 — so the judge can't default to a neutral middle
6. `ScoreDimension`: name + description + observable level descriptions
7. Pointwise single-metric, pointwise multi-dimension (one judge call), and pairwise-vs-baseline modes
8. `ModelJudgePrompt`: `instructions` (app context), `evaluationTarget`, `reference`
9. Why app context matters: a judge with no context treats criticism as a valid descriptor
10. 🚩 When you disagree with the judge, the judge is usually right *by your rubric* — refine the rubric
11. 🚩 Uniform scores mean your dimension is too broad — split it (quality → relevance + usefulness)
12. Rationales as the primary debugging signal
13. Few-shot calibration, and the overfitting limit
14. 🚩 PCC-backed judges consume the user's metered quota — a real CI concern

**Sources:** `transcripts/evals-mlx.md` (session 298); `web/apple-docs-fm-evals-speech.md`;
`forums/forum-pain-points.md`

---

### 48. `evals-judge-alignment-and-drift`
**Evaluating your evaluator: judge drift, why accuracy lies, and Cohen's kappa**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 47

**Scope.** The most statistically sophisticated content in the corpus, and the least documented.
A judge you never validate silently diverges from you as the dataset grows — and plain accuracy will
not show it.

**Key sections**
1. Drift: systematic disagreement that widens with dataset size
2. 🚩 Why accuracy fails: eval datasets skew toward good output, so a high-score-biased judge looks aligned
3. Cohen's kappa: `(accuracy − chance) / (1 − chance)`, with chance weighted by prevalence
4. The 0.6 threshold and where it comes from
5. 🚩 Kappa is **not** a built-in — you implement it as a custom aggregation
6. The meta-evaluation recipe: pull the Xcode attachment, add your own human ratings, feed it back
7. Freezing feature nondeterminism: `subject(from:)` just returns the already-generated output
8. Three documented improvement iterations (app context + examples; sharper dimension descriptions;
   few-shot examples of your own judgements) and the relevance-up/usefulness-down trade-off
9. 🚩 Too many few-shot examples overfit the alignment score itself
10. Promoting the accepted change into the baseline before the next experiment
11. When to stop tuning the judge and go back to tuning the feature

**Sources:** `transcripts/evals-mlx.md` (session 335); `web/apple-docs-fm-evals-speech.md`

---

### 49. `evals-synthetic-datasets`
**Generating evaluation datasets with `SampleGenerator`**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 46

**Scope.** Dataset construction is where most teams spend their time. Covers the generator's full
surface plus the two traps that produce a subtly wrong dataset without any error.

**Key sections**
1. Start hand-written: 20–30 samples, coverage over count
2. `makeSamples(prompt:dataset:targetCount:)` — the simple path, returning an async stream
3. 🚩 `targetCount` is the **final** dataset size *including* your seeds
4. Full `SampleGenerator`: `sessionProvider`, `samplingStrategy`, `validator`
5. 🚩 `sessionProvider` can be called more than once — context exhaustion mid-run forces a fresh,
   context-free session, so instructions must be self-contained
6. Random vs sliding-window sampling, and when order is meaningful
7. 🚩 The validator sees one sample in isolation — corpus-level rules cannot be checked there
8. Prompt rules are not guarantees; the validator is the only enforcement layer
9. `samples` / `invalidSamples` streaming in real time
10. 🚩 Expect scores to **drop** when you scale from 13 to 100 samples — that is the point
11. Four hypotheses when they drop (prompt, feature, evaluation, dataset)
12. Synthesizing tool-call datasets, and that the generating model knows nothing about your tools
13. Running generation from a command-line tool and checking it in

**Sources:** `transcripts/evals-mlx.md` (session 299); `web/apple-docs-fm-evals-speech.md`

---

### 50. `evals-tool-call-trajectories`
**Evaluating agentic behavior: trajectory expectations and argument matchers**
*Audience:* Swift app dev · *E:* strong · *Len:* ~3,500 words · *depends on:* 49

**Scope.** A completely different evaluation modality: checking *how* the model got there, not just
what it said. Motivated by the observation that a plausible answer can come from a wrong path.

**Key sections**
1. Why: "the final output can look correct while the path to get there isn't"
2. `TrajectoryExpectation(ordered:unordered:disallowed:allowsAdditionalToolCalls:)`
3. `ToolExpectation(_:arguments:)` and `.anyOrder(_:)` groups
4. Ordered trajectories catch real bugs (calling get-details before you have an ID)
5. `disallowed:` for testing negative instruction following
6. The nine `ArgumentMatcher` strategies, including `.naturalLanguage(argumentName:criteria:)`
   which delegates to a judge model
7. `ToolCallEvaluator(allPass:percentagePass:)` and what it drives
8. `TrajectoryExpectation` is itself `@Generable` — so trajectory datasets can be synthesized
9. Validation metrics for synthesized trajectories (expectation exists; ≥1 call; all tools real)
10. Stub tools for evaluation vs the real implementations
11. Evaluating a Spotlight-grounded feature: expected item identifiers and a result-coverage metric
12. Running output evaluation and trajectory evaluation in one suite

**Sources:** `transcripts/evals-mlx.md` (session 299); `transcripts/fm-ecosystem.md` (session 246);
`web/apple-docs-fm-evals-speech.md`

---

## Pillar 11 — Ship, distribute & operate

### 51. ⭐ `shipping-model-downloads-and-updates`
**Shipping and updating models: Background Assets, first-run UX, per-architecture variants, and versioning**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,000 words · *depends on:* 31

**Scope.** Bundling a model into your app is usually the wrong answer — two small models added >1 GB
to an app download, hitting every updater including people who will never use the feature. This is
the distribution architecture that avoids that, plus the download engineering that makes it reliable.

**Key sections**
1. The bundling problem, quantified, and the opt-in feature-intro screen as the fix
2. Background Assets: Apple-hosted managed asset packs, `AssetPackManager`, status updates
3. One asset pack per architecture; detect `deviceArchitectureName` and request only the match
4. Where specialization latency hides naturally (the same first-run screen)
5. Two-session download engineering: background identifier + fast foreground session, live migration
6. 🚩 Background-session tasks *created while inactive* are discretionary regardless of your flag
7. 🚩 The cancel callback fires before `didCompleteWithError` — suppress the spurious failure
8. 🚩 Range-header resumes report segment-relative bytes; resume-data resumes report absolute
9. iOS 26 `BGContinuedProcessingTask`: fresh UUID per batch, wildcard permitted identifiers,
   `strategy = .fail`, monotonic progress, resumable expiration
10. Discovering models: HF repo tags, a bundled catalog snapshot, side-loading
11. Versioning and pinning: 🚩 export artifacts are **build artifacts** — archive them, record
    wheel + OS versions, and re-verify after any toolchain bump
12. Updating a model in the field without breaking cached specializations or bookmarks
13. Storage hygiene: cache policies, purging, and what an OS update invalidates

**Sources:** `transcripts/coreai-intro.md`; `web/apple-docs-coreai.md`; `repos/noema-ios.md`;
`forums/forum-pain-points.md`; `web/community-blogs.md`; `repos/issues-community-stack.md`

---

### 52. ⭐ `on-device-memory-thermals-and-power`
**Operating within device limits: memory budgets, jetsam, thermal throttling, and energy**
*Audience:* Swift app dev · *E:* strong · *Len:* ~6,000 words · *depends on:* 29

**Scope.** The highest crash-avoidance value in the series, and the area where the corpus has an
unusually complete worked implementation from a shipping app. On iOS, headroom alone is not a
sufficient fit test — mmap'd weights become resident as inference touches them, so a broad
overcommit launches and then OOMs at long context.

**Key sections**
1. The two OS-level signals: `os_proc_available_memory()` and `phys_footprint`
2. Reconstructing the real process limit; per-device budget tables; the increased-memory-limit entitlement
3. The two-stage launch gate: incremental allocation *and* a total working-set ceiling
4. 🚩 MoE + mmap means **every** expert is resident — "active experts only" accounting is badly wrong
5. Exact pre-launch sizing when the runtime offers it (model / context / compute / projector bytes)
6. Self-calibrating a transient reserve from measured launch peaks
7. A hysteretic pressure ladder (warn/pressure/critical/emergency with recovery factors)
8. Background unload policy by runtime class; re-polling while a turn is still streaming
9. Verified unloads: sample before, detach in one transaction, settle, classify the delta
10. MLX specifics: process-wide `Memory.cacheLimit` must be **refcounted**; RAM-scaled limits;
    `set_wired_limit` and `iogpu.wired_limit_mb`
11. Core AI specifics: fixed-size KV pre-allocation, unchunked prefill logits blowups, the iPhone
    "depth jetsam wall"
12. 🚩 On iPadOS, OOM presents as a bare `std::bad_alloc` with no useful Xcode output
13. Thermals: sustained retention by runtime (GPU wins the sprint, ANE wins the marathon) and what
    that implies for always-on features
14. Energy per token, and why low instantaneous wattage ≠ low energy
15. Clamping threads and disabling warmup under serious/critical thermal state
16. A device-limits checklist before submission

**Sources:** `repos/noema-ios.md`; `web/community-blogs.md`; `repos/issues-mlx-stack.md`;
`repos/mlx-swift-examples.md`; `repos/issues-coreai-stack.md`; `forums/forum-pain-points.md`

---

### 53. `operating-fm-features-outside-the-main-app`
**Extensions, background execution, Shortcuts, WebKit, and notarized Macs**
*Audience:* Swift app dev · *E:* moderate · *Len:* ~2,500 words · *depends on:* 9

**Scope.** Short, high-value, and answered almost entirely by Apple staff in forum threads that exist
nowhere else. Where a Foundation Models feature can and cannot live.

**Key sections**
1. App extensions: `SystemLanguageModel` runs out-of-process and does **not** count against the
   extension memory limit
2. 🚩 Some extension types cannot use it at all because XPC is blocked for privacy reasons
3. Background execution: the OS schedules on-device LLM work by thermals; 🚩 there is no NPU priority
   entitlement (the GPU `continued-processing` entitlement has no analogue)
4. Streaming in the background raises `rateLimited` risk — prefer non-streaming `respond`
5. Non-App-Store notarized macOS apps can use the on-device model
6. Shortcuts' "Use Model" action has 🚩 no error handling at all — no try/catch exists
7. WebKit: `WKUserContentController` is the only bridge; there is no JS interface
8. watchOS: PCC-primary, pairing requirements, and a known build failure on beta 2
9. Designing a feature so it degrades gracefully in each of these environments

**Sources:** `forums/forum-pain-points.md`; `web/apple-docs-fm-evals-speech.md`

---

## Pillar 12 — Adjacent capabilities

### 54. `speechanalyzer-transcription-pipeline`
**Speech-to-text with `SpeechAnalyzer`: the module pipeline, input providers, and asset management**
*Audience:* Swift app dev · *E:* strong · *Len:* ~5,500 words · *depends on:* —

**Scope.** The modern on-device transcription stack, including the 2026 additions that remove the
hand-rolled audio-engine tap. Also covers the finish semantics that produce hangs, and the asset
lifecycle you must drive before anything works.

**Key sections**
1. The pipeline: analyzer + modules + an async input sequence
2. 🚩 Assets first: `bestAvailableAudioFormat(compatibleWith:)` returns nil until they're installed
3. `AssetInventory`: the four-step install, `assetInstallationRequest(supporting:)` (🚩 nil when
   already installed), reservations and `maximumReservedLocales`, `Status`
4. 🚩 Assets are system-managed, shared across apps, and can be unsubscribed if unused
5. New in 2026: `AssetInputSequenceProvider`, `CaptureInputSequenceProvider`, `AnalyzerInputConverter`
6. 🚩 The analyzer performs **no** audio conversion, to keep `CMTime` sample-accurate
7. `analyzeSequence`, `start(inputSequence:)`, `finalize(through:)`, `finalizeAndFinish(through:)`
8. 🚩 Terminating your input stream does **not** finish the session — result streams hang open
9. 🚩 Simultaneity limits and `insufficientResources`; `ignoresResourceLimits` and its warning
10. `SpeechTranscriber` vs `DictationTranscriber`: different platforms, presets, and options
11. Both preset matrices, and extending a preset
12. `SpeechDetector` (VAD): 🚩 it only works alongside a transcriber, and its results report *errors*
13. Result handling: time-range and confidence attributes, volatile vs finalized merging
14. 🚩 Shielding the display task from cancellation, or you miss the final update
15. Biasing accuracy: `AnalysisContext.contextualStrings` vs `SFCustomLanguageModelData` +
    `SFSpeechLanguageModel` (X-SAMPA pronunciations, phrase counts, templates) — DictationTranscriber only
16. 🚩 No new speech *synthesis* API exists for the 2026 model — Apple confirmed this in the forums

**Sources:** `web/apple-docs-fm-evals-speech.md`; `00-ORIENTATION-lead-agent.md`;
`forums/forum-pain-points.md`

---

### 55. `metal-tensorops-and-quantized-tensors`
**Metal TensorOps: `matmul2d`, cooperative tensors, quantized `MTLTensor`s, and fused FlashAttention**
*Audience:* Python ML engineer (Metal-curious) · *E:* strong · *Len:* ~5,500 words · *depends on:* 23

**Scope.** The bottom of the stack, where Core AI and MLX both land. Worth a guide because the M5
neural accelerator, the MX quantized formats, and the new cooperative-tensor-as-matmul-input
capability are what make a hand-written fused attention kernel competitive in 2026.

**Key sections**
1. Where TensorOps sits: MSL API in MetalPerformancePrimitives, used by both Core AI and MLX
2. The M5 neural accelerator: a block in each shader core, aimed at LLM prefill
3. `matmul2d_descriptor` parameters and 🚩 the `multiply` (not `multiply_accumulate`) default
4. Execution scopes: `execution_thread` / `execution_simdgroup` / `execution_simdgroups<N>`
5. `slice()` vs `static_slice<>()` and the bounds-checking cost
6. Quantized dtypes: int4/int8 (26.4), fp4/fp8/int2 (27), and their alignment requirements
7. 🚩 Sub-byte types require 128-byte stride alignment; ML usage requires 64-byte
8. Scale planes (new in 27): one `MTLTensor` carrying data + E8M0 block scales; slicing slices both
9. Cooperative tensors: thread-private ownership, masks, `get_capacity`, `map_iterator`
10. The three-tier dequantization preference order
11. `reduce_rows` / `reduce_columns` and 🚩 the identity parameter that defaults to sum-identity
    even for a max reduction
12. FlashAttention: SIMD-group row ownership, in-register softmax, and feeding a cooperative tensor
    directly into the second matmul (new in 27)
13. 🚩 `is_compatible_as_left/right_input` and `is_iterator_compatible` must be checked first
14. Integrating the result back through `TorchMetalKernel`
15. How the MX format lines up across Metal, coreai-opt, and MLX

**Sources:** `transcripts/coreai-python-metal.md` (session 330); `repos/mlx-core.md`;
`01-lead-agent-repo-spotchecks.md`

---

### 56. `dnikit-dataset-and-model-introspection`
**Auditing datasets and networks before you ship: DNIKit**
*Audience:* Python ML engineer · *E:* moderate · *Len:* ~4,000 words · *depends on:* —

**Scope.** The upstream, pre-conversion half of model quality: find near-duplicates, rare and
mislabeled samples, dead units, and compressible layers *before* you spend a week on Core AI export.
Must lead with an honest status warning — the project is effectively dormant and its PyPI build is
broken under Keras 3.

**Key sections**
1. 🚩 Status first: last release 2023, one commit since; PyPI build broken with Keras 3; fix is main-only
2. The architecture: `Producer` → `PipelineStage` → `Introspector`, strictly lazy
3. `Batch`: fields, snapshots, metadata; the three standard keys; frozen arrays
4. `peek_first_batch` as the pipeline debugger; nothing runs until `introspect()`
5. The canonical pipeline: data → preprocess → resize → model responses → pool to B×C → cache
6. `Familiarity` (GMM over PCA-40 embeddings): find rare data, mislabeled data, distribution gaps
7. `Duplicates` (annoy + transitive closure): near-duplicate clusters and threshold strategies
8. `IUA`: dead units — 🚩 and that it wants **un-pooled** responses, unlike everything else
9. `PFA`: principal filter analysis → a per-layer recommended-unit-count recipe you then retrain from
10. `DatasetReport` and its Symphony-compatible DataFrame column contract
11. Memory reality: only PCA streams; Familiarity and Duplicates load everything into RAM
12. Framework backends: TF1/TF2 complete, PyTorch data-only, 🚩 **no** Core ML / Core AI / MLX backend
13. The escape hatch for unsupported frameworks: a custom Producer that yields precomputed responses —
    which is exactly how you would introspect an MLX or Core AI model
14. How this feeds the compression guides: which layers tolerate compression, and why

**Sources:** `repos/dnikit.md`

---

## Coverage check

| Corpus area | Topics |
|---|---|
| Foundation Models (core) | 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| Dynamic profiles / agentic | 12, 13, 14 |
| PCC / providers / BYO models | 15, 16, 17, 18 |
| Core AI conversion | 19, 20, 21, 22, 23, 24, 25 |
| Compression | 26, 27, 28 |
| Core AI runtime / deployment | 29, 30, 31, 32, 33 |
| Debugging / profiling | 11, 34, 35, 36 |
| MLX | 37, 38, 39, 40, 41, 42, 43, 44, 45 |
| Evaluations | 46, 47, 48, 49, 50 |
| Ship / operate | 2, 51, 52, 53 |
| Speech | 54 |
| Metal / TensorOps | 55 |
| DNIKit | 56 |
| MLX↔Core AI bridge | 25, 16 |
| Community repos (noema, model-zoo, swift-lm) | 25, 30, 32, 33, 36, 51, 52 |
| Python SDK / fm CLI | folded into 5, 9, 46 — **see gap note** |

---

## Recommended ordering and the must-write core

### The 12-guide core (⭐)
These are the guides that (a) the most readers need, (b) the most other guides depend on, and
(c) prevent the most expensive mistakes:

1 `choosing-your-2026-apple-ai-stack` · 2 `platform-gating-…` · 3 `fm-first-session-…` ·
4 `fm-guided-generation-…` · 6 `fm-tool-calling` · 9 `fm-failure-handling-…` ·
10 `fm-context-window-and-kv-cache` · 12 `fm-dynamic-profiles` · 19 `coreai-conversion-pipeline-overview` ·
29 `coreai-swift-runtime-api` · 46 `evals-your-first-evaluation` · 52 `on-device-memory-thermals-and-power`

(Plus 15 `fm-private-cloud-compute`, 16 `byo-model-behind-languagemodelsession`,
21 `coreai-stateful-export-and-kv-cache`, 24 `coreai-authoring-for-ane-vs-gpu`,
26 `coreai-opt-quantization`, 30 `coreai-specialization-and-caching`,
31 `coreai-aot-compilation-…`, 34 `coreai-debugging-numerics-…`, 36 `benchmarking-…`,
37 `mlx-fundamentals`, 43 `mlx-swift-in-an-app`, 51 `shipping-model-downloads-…` — the extended
core if the budget allows 24.)

### Phasing

**Wave 1 — "I can ship something" (guides 1, 2, 3, 4, 6, 9, 5, 11).**
A reader finishing wave 1 has a working, gated, debuggable Foundation Models feature. Deliberately
front-loads failure handling (9) before the advanced features, because availability and guardrails
block more readers than any API gap.

**Wave 2 — "It works at scale" (10, 12, 13, 14, 46, 47, 48, 7, 8).**
Context, agentic sessions, and evaluation. Pair 10 (context/KV) with 12 (dynamic profiles) — they
are the same subject from two directions. Evaluation lands here, not later, because Apple's answer to
OS-update drift is "have an eval suite", and readers need that before they ship v1.

**Wave 3 — "Beyond the built-in model" (15, 16, 17, 18, 53, 49, 50).**
PCC first (policy gates a lot of readers out), then BYO models, then the provider-authoring pair.

**Wave 4 — Core AI conversion (19, 20, 21, 24, 22, 26, 27, 34, 23, 25, 28).**
Strictly sequential; 19 is the spine. Put stateful export (21) and ANE/GPU authoring (24) early
because they determine whether the rest of the pipeline is even worth running, and put numerics
debugging (34) immediately after the first compression guide, since that is when quality regresses.

**Wave 5 — Core AI deployment (29, 30, 31, 32, 33, 35, 51, 52, 36).**
The "converted but doesn't run" cluster. 52 (memory/thermals) and 51 (distribution) close the loop
back to shipping.

**Wave 6 — MLX (37, 39, 43, 40, 44, 41, 45, 42, 38).**
Can run fully in parallel with waves 4–5; different reader. Order Python-first, then the Swift app
path, then the correctness and scaling material.

**Wave 7 — Adjacent (54, 55, 56).**
Independent; schedule by demand.

### Cross-cutting editorial rules
- **Every guide states its version floor in the first 200 words** and marks each API with its
  earliest OS (26.0 / 26.4 / 27.0). The corpus shows constant confusion here.
- **Every guide has a "silent failure" callout box.** The defining property of this stack is that
  most defects do not throw.
- **Attribute community measurements as community-measured**, never as Apple-official, and name the
  hardware, OS, build configuration and date.
- **Never publish code from the two documented fabricated sources** (`.coreaimodel`, `.aiasset`,
  "iOS 20", the invented on-device LoRA API). Guide 1 or 2 should carry a short "sources to distrust" note.
- **Prefer forum-verified Apple-staff answers over transcript paraphrase** where they conflict —
  several transcript claims (adapters, PCC eligibility) are already superseded.

---

## Coverage gaps — where evidence is thin and more research is needed

1. **The `fm` CLI's actual flags.** Only semantic option names were spoken aloud (`the model option`,
   `the image option`). `fm schema object`'s argument grammar was never shown. An Apple engineer
   named `fm serve` in a forum reply, and nothing else about it exists. **Needs a live macOS 27 run
   before any CLI guide is written.** Currently folded into guide 46/9 rather than given its own topic.
2. **The Python SDK's 27-era parity.** The public repo is at the 26 generation (no PCC, no dynamic
   profiles, no `LanguageModel` protocol) while WWDC26 presented it as new. Whether a 27-era release
   exists is unresolved, and it changes whether a Python SDK guide is worth writing standalone.
3. **Whether the core FoundationModels framework is actually open source yet.** Session 241 announced
   it; no `apple/*` or `swiftlang/*` repo was found as of 2026-07-27. The Linux claim rests on the
   utilities package's README. Do not assert either.
4. **Evaluations API spellings.** No Apple doc existed when the transcripts were mined, and the docs
   harvest later confirmed the framework exists — but several names remain unreconciled
   (`ModelSample` vs `ModelSampleProtocol`, `ScoringMode` cases, the `.evaluates` trait's exact
   signature, whether a kappa aggregator ships). Verify against the real Xcode 27 module interface.
5. **Core AI error types.** No inference/specialization/cache error type appears in the 312 indexed
   symbols; `AssetError` covers asset operations only. What `AIModel.init`, `loadFunction`, `run`,
   and cache deletion actually throw is unknown, and a failure-handling section cannot be written
   without it.
6. **`coreai-build`'s full CLI.** Four flags are documented; `--architecture h18p` comes from a
   community source; the enumeration of architecture names has no published list; whether there are
   subcommands beyond `compile` is unknown.
7. **`SpecializationOptions.expectFrequentReshapes`** has no discussion, no documented default, and
   no initializer that sets it — yet Apple's own code sets it. Behavior is inferred.
8. **Whether the macOS 26→27 export-lowering regression was fixed.** The forensics are dated
   2026-06-11 and it is now late July. This single fact changes the advice in guides 19, 31 and 51.
9. **Sub-byte scalar access from Swift.** `NDArray.ScalarType` has int2–int7 and uint1–uint7, but
   there is no matching `BitwiseCopyable` Swift type and no documented vended type — so guide 29
   cannot show how to read palettized data without `RawView`.
10. **`AIModelCache` deletion semantics contradict themselves** in Apple's own docs (throws vs
    defers). Needs a device test.
11. **Speech synthesis.** The WWDC26 keynote advertised improved speech generation; Apple confirmed
    in the forums that **no API shipped**. Do not invent coverage; guide 54 should say so explicitly.
12. **Vision framework's `OCRTool` / `BarcodeReaderTool` declarations** were never harvested — guide 7
    describes them from FM-side references only.
13. **Xcode 27 Instruments lane names.** Only 2 of the Foundation Models template's 6 lanes are named
    anywhere, and the Core AI template's lane/metric names come from prose. Both guides 11 and 35 need
    someone with Xcode 27 to enumerate them.
14. **Apple sample-code projects were never read**: Origami (dynamic profiles), Book Tracker
    (Evaluations, 31 KB), the generative-game-content sample, and the advanced speech-to-text sample.
    These are the richest end-to-end examples in existence and would materially improve guides
    12, 13, 46 and 54.
15. **MLX↔Core AI numerical parity.** `mlx2coreai`'s own docs say op coverage is "asset generation
    coverage, not runtime numerical parity", and nothing in the corpus verifies a converted MLX model
    end to end. Guide 25 must flag this rather than imply the path is validated.
16. **DNIKit's current runnability.** Nothing was executed; the Keras 3 fix is main-only and main's own
    test suite reportedly fails from dependency drift. Guide 56 should be written as an
    "evaluate whether to use this" guide, not a tutorial, until someone runs it.
