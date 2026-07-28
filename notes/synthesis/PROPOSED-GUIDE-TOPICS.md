# Proposed guide series — Apple's 2026 AI/ML developer stack

**Merged, adjudicated topic list · 50 guides in 16 parts**
Final editor's synthesis of three independent proposals (by framework, by task, by depth), reconciled against the research corpus in `notes/`.
Date: 2026-07-27 · Corpus: 34 research files, ~3.6 MB of grounded notes.

---

## 1. Landscape summary

**The single most important thing that changed in 2026: the four product lines stopped being alternatives and became layers.**

At the top, the **Foundation Models framework** is no longer "the API for Apple's on-device LLM." `LanguageModelSession` now sits on a public **`LanguageModel` / `LanguageModelExecutor`** protocol pair, and Apple ships or blesses at least five conformers: `SystemLanguageModel` (rebuilt on-device model, ~4K context, now accepting image attachments), `PrivateCloudComputeLanguageModel` (32K context, three reasoning levels, no API keys, per-user daily quota), `CoreAILanguageModel` (your own `.aimodel` on ANE or GPU), `MLXLanguageModel` (anything on Hugging Face, via `mlx-swift-lm`), and `ChatCompletionsLanguageModel` (any OpenAI-compatible endpoint — which quietly turns `mlx_lm.server`, Ollama, vLLM and LM Studio into Foundation Models backends *today*). "Which framework do I choose" has become "which backend do I choose behind one session API." That reframing is the spine of this series.

The framework's own 2026 additions cluster into three areas. **Agentics:** Dynamic Profiles — a SwiftUI-shaped DSL (`DynamicInstructions` → `Profile` → the nested `LanguageModelSession.DynamicProfile`) whose `body` is re-evaluated before every request, with ~14 modifiers, lifecycle hooks, `@SessionPropertyEntry` shared state, a now-mutable `session.transcript`, and `toolCallingMode(.required)` documented as an unbounded loop you must break yourself. **Context engineering:** an explicit KV-cache contract (instructions → tool definitions → transcript; a change at position N invalidates everything after N), plus the separately-versioned `apple/foundation-models-utilities` package shipping `summarizeHistory` / `rollingWindow` / `droppingCompletedToolCalls` and a Skills API whose `prompt:`-versus-`instructions:` storage choice *is* the KV-cache trade-off made concrete. **Reliability:** a rewritten error taxonomy (`LanguageModelError` supersedes the deprecated `GenerationError`, and rebuilding with Xcode 27 silently changes which `catch` fires), a first-class Evaluations framework, and a Foundation Models Instruments template.

Below that, **Core AI** is "the inference framework powering on-device Apple Intelligence," now public and explicitly the successor path for neural networks while Core ML retains trees and tabular work. Its shape: a portable `.aimodel` *source* bundle → specialization (device- **and OS-version**-specific, expensive, cached) → `AIModel` → `InferenceFunction` → `NDArray`. The difficulty lives downstream: a non-escapable `View`/`MutableView` memory model built on `Span` and value generics, `InterleaveLayout` block strides, `preferredStrides` to avoid hidden layout copies, **states** (tensors read and written in place — i.e. KV caches), pipelined `encode()` into a `ComputeStream`, an `AIModelCache` keyed on `(URL, SpecializationOptions)` with bookmark and app-group escape hatches, and AOT compilation via `xcrun coreai-build` producing one `.aimodelc` per device architecture — which iOS effectively *requires*, because it cannot JIT. The Python side is three packages: `coreai-torch` (`torch.export` → Core AI MLIR, with composite ops, externalization, custom lowerings and `TorchMetalKernel`), `coreai-opt` (quantization, k-means palettization, pruning, casting, joint compression), and `coreai-core` (runtime plus direct graph authoring). `apple/coreai-models` adds a 22-model catalog, five Swift runtime products, four real LLM engines, and — uniquely — three **agent skills** containing Apple's own empirical ANE/GPU authoring rules and PSNR acceptance gates.

**MLX** is the open array framework for Apple silicon: unified memory with per-op stream placement, lazy evaluation, `mx.compile`, four quantization modes (affine / mxfp4 / mxfp8 / nvfp4), custom Metal and CUDA kernels, and a new RDMA-over-Thunderbolt distributed backend (JACCL). `mlx-lm` is the LLM layer — 18 CLIs, ten KV-cache classes, a continuous-batching OpenAI-compatible server, LoRA/DoRA (now the *surviving* on-device adaptation story, since Foundation Models custom adapters are discontinued in OS 27), and four learned-quantization methods. `mlx-swift-lm` is the Swift port, which also hosts `MLXFoundationModels` — the best readable implementation of the `LanguageModel` protocol in existence — and `MLXGuidedGeneration`. Notably, both Apple's `coreai-models` and `mlx-swift-lm` independently reach for **xgrammar** to enforce `@Generable` on non-Apple models; convergent design documented in no transcript and no doc page.

**Evaluations** (Xcode 27, Swift-only, built on Swift Testing + TabularData) cuts across everything: an `Evaluation` protocol, code-based and model-judge evaluators, `TrajectoryExpectation` for tool-call paths, `SampleGenerator` for synthetic datasets, and — the most statistically sophisticated content in the corpus — judge drift measured with Cohen's kappa against a 0.6 threshold. Apple positions it as the only defense against silent behavior change across OS updates, because **there is no model version pinning API**.

**Speech** changed least: the `SpeechAnalyzer` module pipeline from iOS 26 is intact, with 2026 adding only input-plumbing conveniences. Its hard parts are asset lifecycle, finish-state semantics, and the no-audio-conversion contract. There is **no new TTS API** despite the keynote's speech-generation claims — Apple confirmed this on the forums. Underneath everything, **Metal Performance Primitives / TensorOps** exposes matmul and convolution in MSL with automatic use of the M5 neural accelerator, plus cooperative tensors and MX-format scale planes.

Three cross-cutting realities every guide must carry:

1. **Version gating is everywhere.** 26.0 vs 26.4 vs 27.0; Xcode 26 vs 27; `canImport(FoundationModels, _version: 2)`; `coreai-core >= 1.0.0b2`; the A17 Pro / M1 / M2 AOT hardware floor; MLX's TF32 and NAX gates. Version confusion is the largest source of phantom bug reports in the forum corpus, closely followed by the Simulator "punching out" to the host macOS.
2. **Most defects in this stack do not throw.** `.anyOf` doesn't constrain generation (Apple reproduced it). `AIProgram.optimize()` can delete a broadcast-significant op. The GPU delegate executes `floor`/`trunc`/`ceil` as identity. MLX's `gather_qmm` silently exposes recycled memory on M5 at certain row counts. MLX's fused SDPA fallback is silent. Every guide needs a "silent failure" callout.
3. **Rankings invert by measurement axis.** Core AI leads MLX 2.47× at 0.6B, 1.05× at 8B, and *loses* MoE by 28%. Burst throughput inverts under ten minutes of sustained load. Energy-per-token inverts again. One number is always wrong.

---

## 2. Pillars

| # | Pillar | Guides | Rationale |
|---|---|---|---|
| P1 | Cross-stack orientation & gating | 2 | Nothing else is safe to read first. The backend-selection question changed shape, and every API is gated on some combination of OS / SDK / Xcode / package / hardware. |
| P2 | Foundation Models — core API | 6 | The everyday Swift surface: sessions, guided generation, streaming, tools, images, failures. Highest reader volume, deepest evidence. |
| P3 | Foundation Models — context & agentics | 4 | Where 2026 changed most, and where multi-turn apps actually fail. Its own failure modes: silent quality loss from transcript surgery, infinite tool loops. |
| P4 | Foundation Models — providers & backends | 4 | PCC plus the `LanguageModel` protocol. The architectural headline of the year, and a different audience (package authors). |
| P5 | Developer tooling & non-Swift access | 2 | `#Playground`, Instruments, the `fm` CLI and the Python SDK. The only observability story for a non-deterministic runtime. |
| P6 | Evaluations | 3 | Apple's stated answer to non-determinism and the only regression gate against OS-update model drift. |
| P7 | Core AI — Swift runtime | 4 | Loading, specializing, caching, running, pipelining. Origin of first-launch latency, storage growth, and memory bugs. |
| P8 | Core AI — Python conversion | 3 | `coreai-torch`: a compiler, deserving compiler-shaped guides. Strictly sequential, unforgiving, mostly silent when wrong. |
| P9 | Core AI — compression & numerics | 3 | `coreai-opt` plus a cross-stack numeric-format reference that serves five other guides. |
| P10 | Core AI — authoring, debugging, LLM deployment | 3 | Apple's own empirical hardware rules (which invert by target), the three debugging tools, and the end-to-end LLM export recipe. |
| P11 | Metal / TensorOps | 2 | The kernel layer both Core AI and MLX sit on. Verifiable against shipped SDK headers. |
| P12 | MLX — Python | 6 | Research, conversion, quantization, serving, fine-tuning, distributed. Deep official docs plus a large issue-tracker corpus of empirical hardware behavior. |
| P13 | MLX — Swift | 3 | The same models inside an app, plus the most readable third-party `LanguageModel` conformance in existence. |
| P14 | Cross-stack bridges | 1 | `mlx2coreai` and `swift-lm` — the only public non-Apple descriptions of Core AI's MLIR-level and bundle-level contracts. |
| P15 | Shipping & operating on device | 2 | Distribution, memory, jetsam, thermals, honest measurement. The largest source of shipped-app bugs in the forum corpus. |
| P16 | Adjacent capabilities | 2 | Speech (self-contained, sharp undocumented failure modes) and DNIKit (the only pre-conversion data-quality topic). |

---

## 3. Table of contents

### Part 1 — Orientation and gating
1. [`apple-ai-stack-2026-map`](#1-apple-ai-stack-2026-map) — The 2026 Apple AI stack, and how to choose a model backend ★
2. [`platform-and-version-gating`](#2-platform-and-version-gating) — Every version, hardware, entitlement and runtime-surface gate ★

### Part 2 — Foundation Models: the everyday API
3. [`fm-sessions-and-prompting`](#3-fm-sessions-and-prompting) — `LanguageModelSession` end to end ★
4. [`fm-guided-generation-and-streaming`](#4-fm-guided-generation-and-streaming) — `@Generable`, `@Guide`, dynamic schemas, snapshot streaming ★
5. [`fm-tools-and-tool-calling`](#5-fm-tools-and-tool-calling) — The `Tool` protocol, calling modes, and the required-mode loop ★
6. [`fm-spotlight-rag-and-system-tools`](#6-fm-spotlight-rag-and-system-tools) — Local RAG with `SpotlightSearchTool`, plus OCR and barcodes
7. [`fm-image-input-and-attachments`](#7-fm-image-input-and-attachments) — Image input, and what the model cannot do with pixels
8. [`fm-availability-errors-and-guardrails`](#8-fm-availability-errors-and-guardrails) — The complete failure taxonomy ★

### Part 3 — Foundation Models: context, profiles, agentic sessions
9. [`fm-context-window-and-kv-cache`](#9-fm-context-window-and-kv-cache) — Token budgeting, transcript anatomy, KV-cache economics ★
10. [`fm-dynamic-profiles-and-session-state`](#10-fm-dynamic-profiles-and-session-state) — Dynamic Profiles, modifiers, session properties ★
11. [`fm-utilities-skills-and-history-modifiers`](#11-fm-utilities-skills-and-history-modifiers) — `foundation-models-utilities`: Skills and history transforms
12. [`fm-agentic-orchestration`](#12-fm-agentic-orchestration) — Baton-pass, phone-a-friend, model routing, transcript error policy

### Part 4 — Foundation Models: beyond the built-in model
13. [`fm-private-cloud-compute`](#13-fm-private-cloud-compute) — Eligibility, entitlement, reasoning levels, quota UX
14. [`byo-model-behind-languagemodelsession`](#14-byo-model-behind-languagemodelsession) — Core AI, MLX, and any OpenAI-compatible server
15. [`authoring-a-languagemodel-provider`](#15-authoring-a-languagemodel-provider) — The protocol, capabilities, and the generation channel
16. [`provider-executor-store-and-kv-reuse`](#16-provider-executor-store-and-kv-reuse) — Executor lifecycle, transcript diffing, packaging

### Part 5 — Prototyping, profiling, and non-Swift access
17. [`fm-playground-and-instruments`](#17-fm-playground-and-instruments) — `#Playground`, scheme simulation, and reading a trace
18. [`fm-cli-and-python-sdk`](#18-fm-cli-and-python-sdk) — The `fm` CLI and `apple-fm-sdk` ⚠

### Part 6 — Evaluations
19. [`evals-foundations-and-hill-climbing`](#19-evals-foundations-and-hill-climbing) — Building blocks, Swift Testing, evaluation-driven development
20. [`evals-model-judges-and-alignment`](#20-evals-model-judges-and-alignment) — Judges, score dimensions, drift, Cohen's kappa
21. [`evals-datasets-and-tool-trajectories`](#21-evals-datasets-and-tool-trajectories) — `SampleGenerator` and `TrajectoryExpectation`

### Part 7 — Core AI: the Swift runtime
22. [`coreai-runtime-and-ndarray`](#22-coreai-runtime-and-ndarray) — `AIModel`, `InferenceFunction`, `NDArray`, and the memory model ★
23. [`coreai-specialization-caching-and-aot`](#23-coreai-specialization-caching-and-aot) — The first-launch stall, the cache, and `coreai-build` ★
24. [`coreai-states-and-pipelined-execution`](#24-coreai-states-and-pipelined-execution) — States as KV cache; `ComputeStream` pipelining
25. [`coreai-bundles-engines-and-guided-decoding`](#25-coreai-bundles-engines-and-guided-decoding) — Model bundles, four LLM engines, xgrammar

### Part 8 — Core AI: converting a model from PyTorch
26. [`coreai-torch-conversion-and-io-contract`](#26-coreai-torch-conversion-and-io-contract) — The pipeline, and the IO/state/dynamic-shape contract ★
27. [`coreai-torch-coverage-composites-and-lowerings`](#27-coreai-torch-coverage-composites-and-lowerings) — When an op won't convert; composites and externalization
28. [`coreai-custom-metal-kernels`](#28-coreai-custom-metal-kernels) — `TorchMetalKernel` end to end

### Part 9 — Core AI: compression and numeric formats
29. [`coreai-opt-quantization`](#29-coreai-opt-quantization) — Config hierarchy, specs, GRAPH vs EAGER, QAT
30. [`coreai-opt-palettization-pruning-and-joint`](#30-coreai-opt-palettization-pruning-and-joint) — Palettization, the ANE rank-5 ceiling, joint compression
31. [`numeric-formats-across-the-stack`](#31-numeric-formats-across-the-stack) — int4 to MX: who supports what, at every layer

### Part 10 — Core AI: authoring for the hardware, debugging, LLM deployment
32. [`ane-vs-gpu-authoring-rules`](#32-ane-vs-gpu-authoring-rules) — Two opposite rulesets, from Apple's own agent skills
33. [`coreai-debugging-and-profiling`](#33-coreai-debugging-and-profiling) — Debug gauge, Instruments, Core AI Debugger, sync points, PSNR
34. [`coreai-llm-export-end-to-end`](#34-coreai-llm-export-end-to-end) — HF checkpoint to loadable bundle, macOS dynamic and iOS static

### Part 11 — Metal and TensorOps
35. [`tensorops-matmul-and-quantized-tensors`](#35-tensorops-matmul-and-quantized-tensors) — `matmul2d`, `MTLTensor`, MX scale planes
36. [`tensorops-cooperative-tensors-and-flashattention`](#36-tensorops-cooperative-tensors-and-flashattention) — Cooperative tensors, reductions, fused attention

### Part 12 — MLX in Python
37. [`mlx-core-fundamentals`](#37-mlx-core-fundamentals) — Lazy evaluation, unified memory, streams, compile, transforms
38. [`mlx-numerics-hardware-gating-and-kernels`](#38-mlx-numerics-hardware-gating-and-kernels) — TF32, NAX, silent SDPA fallback, custom Metal kernels
39. [`mlx-quantization`](#39-mlx-quantization) — Four modes, learned quantization, and the corruption bugs
40. [`mlx-lm-cli-generation-and-caching`](#40-mlx-lm-cli-generation-and-caching) — 18 CLIs, the generation API, KV caches, speculative decoding
41. [`mlx-lm-serving-and-distributed`](#41-mlx-lm-serving-and-distributed) — `mlx_lm.server`, local agents, JACCL over Thunderbolt
42. [`mlx-lm-finetuning-and-porting`](#42-mlx-lm-finetuning-and-porting) — LoRA/DoRA, and adding a new architecture

### Part 13 — MLX in Swift
43. [`mlx-swift-lm-in-an-app`](#43-mlx-swift-lm-in-an-app) — Package setup, concurrency, wired memory, media input
44. [`mlx-swift-lm-generation-tools-and-cache`](#44-mlx-swift-lm-generation-tools-and-cache) — Generation, ten tool formats, eight cache types
45. [`mlx-swift-fm-bridge-and-guided-generation`](#45-mlx-swift-fm-bridge-and-guided-generation) — `MLXFoundationModels` and `MLXGuidedGeneration`

### Part 14 — Bridges between stacks
46. [`coreai-bridges-mlx2coreai-and-swift-lm`](#46-coreai-bridges-mlx2coreai-and-swift-lm) — Third-party paths into Core AI

### Part 15 — Shipping and operating on device
47. [`shipping-model-distribution-and-updates`](#47-shipping-model-distribution-and-updates) — Background Assets, per-architecture variants, versioning
48. [`on-device-memory-thermals-and-benchmarking`](#48-on-device-memory-thermals-and-benchmarking) — Jetsam, thermals, energy, and honest measurement ★

### Part 16 — Adjacent capabilities
49. [`speech-analyzer-end-to-end`](#49-speech-analyzer-end-to-end) — `SpeechAnalyzer`, transcribers, assets, custom vocabulary
50. [`dnikit-dataset-and-model-introspection`](#50-dnikit-dataset-and-model-introspection) — Pre-conversion data and network auditing ⚠

★ = must-write core (12) · ⚠ = evidence caveats, read the topic entry before scheduling

---

## 4. Per-topic detail

---

### Part 1 — Orientation and gating

#### 1. `apple-ai-stack-2026-map`
**The 2026 Apple AI stack: Foundation Models, Core AI, MLX, Core ML — and how to choose a model backend**

| | |
|---|---|
| **Pillar** | P1 Cross-stack orientation & gating |
| **Audience** | Both (Swift app devs and Python ML engineers) |
| **Evidence** | **Strong** |
| **Length** | ~5,500 words |
| **Depends on** | — |

**Scope.** Maps the four product lines and explains the structural change of WWDC26: Core AI and MLX are now *backends* for Foundation Models via the `LanguageModel` protocol, not competitors to it. Provides a decision framework across capability, context size, privacy, offline behavior, quota economics, memory and distribution, grounded in measured numbers rather than folklore. Includes Apple's explicit routing of non-neural-network models to Core ML, and an explicit "sources to distrust" note, because two of roughly fourteen community sources in the corpus are demonstrably fabricated.

**Key sections**
- The four layers, in one diagram, and what each layer owns
- What actually changed at WWDC26: the `LanguageModel` protocol as the spine
- `SystemLanguageModel` vs PCC: 4K/32K, offline/online, unlimited/quota, no-reasoning/three-levels
- Core AI: when a custom `.aimodel` beats the system model
- MLX: research iteration and open-weight breadth versus end-user deployment
- Core ML in 2026: trees, tabular, and the narrowing scope
- The ANE-access argument, and what it is actually worth
- Measured reality: ~2.47× Core AI over MLX at 0.6B collapsing to ~1.05× at 8B, and the MoE inversion to MLX +28%
- Three rankings from the same hardware: burst throughput, sustained throughput, joules per token
- Decision tree: do you own weights? need offline? need a custom architecture?
- Hybrid architectures shipping today (a six-backend production app) and why they exist
- Sources to distrust: the two fabricated community articles (`.coreaimodel`, `coreai-torch convert`, "iOS 20", an invented on-device LoRA API)
- Anti-patterns: choosing on tok/s alone; choosing before checking device eligibility

**Sources.** `00-ORIENTATION-lead-agent.md` · `transcripts/fm-core.md` · `transcripts/fm-ecosystem.md` · `transcripts/coreai-intro.md` · `web/apple-docs-coreai.md` · `web/community-blogs.md` · `repos/noema-ios.md` · `forums/forum-pain-points.md`

---

#### 2. `platform-and-version-gating`
**Will this even run? OS versions, SDK gates, hardware tiers, entitlements, and runtime surfaces**

| | |
|---|---|
| **Pillar** | P1 Cross-stack orientation & gating |
| **Audience** | Swift app dev (Python readers: sections 1, 8–10) |
| **Evidence** | **Strong** |
| **Length** | ~6,000 words |
| **Depends on** | 1 |

**Scope.** One reference for every gate between your code and a working feature, plus a concrete iOS 26 → 27 migration checklist. Covers the 26.0 / 26.4 / 27.0 split, the two on-device model tiers, the Apple Intelligence hardware floor, entitlements, region and language gating, and the App Store reality that there is *no* Required Device Capability for Apple Intelligence — so you cannot stop unsupported devices from installing your app. Ends with where a Foundation Models feature can and cannot live: extensions, background execution, Shortcuts, WebKit, notarized Macs.

**Key sections**
- The decoder-ring table: which API landed in 26.0 / 26.4 / 27.0, including `@backDeployed` exceptions
- Two on-device models — AFM 3 Core vs Core Advanced — and the exact device split
- Hardware floors: A17 Pro / M1 / M2 for Apple Intelligence and for `coreai-build` AOT
- `canImport(FoundationModels, _version: 2)` as the only reliable 27-SDK test; SDK-conditional compilation patterns that work
- Xcode 26 vs Xcode 27: why rebuilding silently changes which `catch` clause fires
- New enum cases (`Transcript.Entry.reasoning`, `Segment.attachment`) that break exhaustive switches
- Language and locale gating: `supportsLocale` follows the *Siri* language, and the undocumented iOS 27 beta Siri-toggle coupling
- Entitlements: private-cloud-compute, increased-memory-limit, app groups, `continued-processing.gpu`
- App Store distribution: no capability flag, Apple's mandated baseline non-AI experience, checking availability before taking payment
- The Simulator trap: it punches out to the host macOS, producing meaningless `-1` errors; PCC does not work there at all
- Package-level floors: `coreai-core >= 1.0.0b2`, `torch 2.8–2.13`, `mlx-swift-lm` 3.x, the Metal Toolchain build prerequisite
- Runtime surfaces: extensions run `SystemLanguageModel` out-of-process (no memory-limit cost) but XPC-restricted extensions cannot use it at all; no NPU priority entitlement; Shortcuts' "Use Model" has no error handling; WebKit needs `WKUserContentController`
- A copy-paste preflight checklist, and a 26 → 27 migration checklist

**Sources.** `forums/forum-pain-points.md` · `web/apple-docs-fm-evals-speech.md` · `web/apple-docs-coreai.md` · `02-lead-agent-corpus-gaps-filled.md` · `repos/issues-coreai-stack.md` · `repos/mlx-swift-lm.md` · `repos/noema-ios.md`

---

### Part 2 — Foundation Models: the everyday API

#### 3. `fm-sessions-and-prompting`
**`LanguageModelSession` end to end: initializers, instructions vs prompts, prewarming, concurrency**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~5,000 words |
| **Depends on** | 2 |

**Scope.** The session object itself, and the security model governing what goes in instructions versus prompts — instructions come from the developer, prompts may come from the user, the model is trained to obey instructions over prompts, and that ordering *is* the prompt-injection defense. Covers all initializer forms including the 2026 profile-based ones, the `respond` / `streamResponse` overload map, `isResponding` and concurrency, and prompting technique for a small on-device model.

**Key sections**
- Creating a session: six init forms, and which are generic over `some LanguageModel`
- `Instructions {}` vs `Prompt {}`: authorship, transcript ordering guarantees, prompt-injection defense
- Never interpolate user input into instructions — Apple's explicit rule
- `InstructionsBuilder` and `PromptBuilder`: conditionals, loops, embedding a `Generable` instance
- One-shot prompting with a fully-populated `@Generable` example, and the structure-vs-style division of labor
- The `respond` overload map, and why `streamResponse` is not `async`
- `prewarm()` and `prewarm(promptPrefix:)`: what they load, and the measured ~700 ms win
- `isResponding` and the one-request-at-a-time rule; why streaming in the background raises rate-limit risk
- `GenerationOptions`: sampling modes, temperature, `maximumResponseTokens` and its ungrammatical-output warning
- Greedy sampling as a *testing* tool, not a quality tool
- Apple's counter-intuitive finding: the most detailed prompt had the highest generation-error rate
- Supported vs "avoid" capabilities of the on-device model; multilingual prompting, where property names are model input
- Session reuse versus recreation; prompt gating across the three on-device model generations

**Sources.** `transcripts/fm-core.md` · `web/apple-docs-fm-evals-speech.md` · `transcripts/fm-advanced.md` · `forums/forum-pain-points.md`

---

#### 4. `fm-guided-generation-and-streaming`
**Guided generation and snapshot streaming: `@Generable`, `@Guide`, dynamic schemas, `PartiallyGenerated`**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~7,500 words |
| **Depends on** | 3 |

**Scope.** Two mechanisms usually taught separately that are really one system: top-down constrained decoding produces a partially-valid object at every step, which is exactly what makes snapshot streaming possible. Covers the complete `@Guide` vocabulary and which guides are legal on which types, runtime schema construction, the `PartiallyGenerated` mirror types, and the constraint mechanism Apple has confirmed broken.

**Key sections**
- `@Generable` on structs and enums; composability and top-down constrained decoding
- What structural guarantees buy you, and what they do *not* guarantee
- The full `@Guide` catalogue: description, `.range`, `.count`, `.pattern`, `.anyOf`, `.constant`, `.element`, min/max
- The guide-to-type compatibility matrix, derived from 28 negative test classes
- Compile-time enum vs runtime `.anyOf`: a decision table
- **The confirmed `.anyOf` bug** — Apple reproduced it; the model still generates out-of-set values; two workarounds
- Why guided generation lets you delete prompt text — and the token cost of the schema
- `includeSchemaInPrompt: false` and the exact precondition that makes it safe
- `DynamicGenerationSchema`, references, anyOf unions, `GenerationSchema(root:dependencies:)`
- `GeneratedContent.Kind`, JSON round-tripping, and the FoundationModels JSON-Schema dialect
- `streamResponse` returns an `AsyncSequence` — do not `await` the call itself
- `T.PartiallyGenerated`: how the macro synthesizes it through the whole type graph; snapshots, not deltas
- SwiftUI patterns that avoid the if-let boilerplate; `GenerationID` for stable identity in `ForEach`; throttling and animation
- `ResponseStream.Snapshot`: content, transcript entries, usage; reasoning tokens arriving before readable entries
- Cancellation, early break, and the iOS background-GPU trap
- Failure taxonomy: decoding failure, unsupported guide, invalid schema, schema-beats-prompt behavior; classification enums need greedy sampling

**Sources.** `transcripts/fm-core.md` · `web/apple-docs-fm-evals-speech.md` · `forums/forum-pain-points.md` · `repos/python-apple-fm-sdk.md` · `repos/noema-ios.md`

---

#### 5. `fm-tools-and-tool-calling`
**Building tools: the `Tool` protocol, the arguments contract, calling modes, and escaping the required-mode loop**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~5,500 words |
| **Depends on** | 4 |

**Scope.** Everything from a first tool to a bounded agent loop. Emphasizes the two facts that trip everyone up: the model will not reliably call your tool from its name and description alone, and `.required` puts the model in an unbounded `while` loop unless you build an explicit exit. Includes the six-entry transcript anatomy of one tool-using turn, observed live.

**Key sections**
- `Tool` conformance: `name`, `description`, `Arguments` as the model-tool contract, `call(arguments:)`
- Why you must *also* write an instruction sentence telling the model to use the tool
- The six-entry transcript anatomy of one tool turn; one `toolCalls` entry holds N calls
- Automatic invocation: how outputs are re-inserted and synthesized
- Runtime-built schemas via `GenerationSchema`, and the once-computed-at-session-init trap
- `ToolCallingMode` in both spellings: `GenerationOptions(toolCallingMode:)` and the profile modifier
- **`.required` is a `while` loop** — the two sanctioned exits, with a compiled reference implementation
- `onToolCall` as an approval chokepoint, and why throwing there aborts the whole turn (no per-call rejection)
- Tool errors, retry loops, and validating arguments you cannot constrain
- Tool definitions cost context: they sit in the token budget *and* in the KV prefix
- Deterministic ordering of tool specs, and adding or removing tools mid-session
- Greedy sampling for deterministic tool-call tests; testing tools without a model

**Sources.** `transcripts/fm-core.md` · `transcripts/fm-advanced.md` · `web/apple-docs-fm-evals-speech.md` · `forums/forum-pain-points.md` · `repos/noema-ios.md`

---

#### 6. `fm-spotlight-rag-and-system-tools`
**Local RAG with `SpotlightSearchTool`, plus `OCRTool` and `BarcodeReaderTool`**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (Vision-backed tool declarations: moderate) |
| **Length** | ~6,000 words |
| **Depends on** | 5 |

**Scope.** Apple's "fully local RAG with no vector database" story, taught honestly — including the failure that will burn most adopters. Core Spotlight stores text content in a compact searchable-but-not-readable representation, so a model answering from search results alone sees only identity attributes and will hallucinate bodies. The guide teaches retrieve-then-hydrate as the primary recipe, and documents two live bugs.

**Key sections**
- The cross-import overlay: the tool only materializes if you import both CoreSpotlight and FoundationModels
- `SpotlightSearchTool.Configuration`: sources, `Guide(level:format:)`, `contactResolver`, `customStages`
- The tool-call trajectory: model decides → generates a query → Spotlight executes → model reasons
- Guidance level as a token-budget decision: `.complete` injects ~13k tokens and blows a 4K context instantly; ship `.focused(.items)` + `.compact`
- Consuming `tool.searchResults`: batched `SearchReply`s and `queryToken`-keyed UI refresh
- **The metadata gap** — results carry identity attributes only, so the model invents bodies
- The retrieve-then-hydrate pattern: `searchableItems(forIdentifiers:)` plus a companion fetch tool
- Custom `Generable` pipeline stages for count / table / statistic over result sets, and the current beta routing gap
- Exposing custom `IndexedEntity` attributes to the model
- Known issue: the tool's `description` and its generated JSON Schema disagree, making it uninvokable by non-Apple models (DTS-confirmed)
- Other failures: `UnifiedAssetFramework` Code=5000 model-catalog error; the model silently not calling the tool; `.required` as a probe
- `OCRTool` and `BarcodeReaderTool` — Vision-backed, free, and when to use them instead of the LLM
- Platform gaps: no watchOS; evaluating a Spotlight-grounded feature with a result-coverage metric

**Sources.** `transcripts/fm-ecosystem.md` · `forums/forum-pain-points.md` · `web/apple-docs-fm-evals-speech.md` · `transcripts/fm-core.md`

---

#### 7. `fm-image-input-and-attachments`
**Image input: `Attachment`, labels, `ImageReference`, token cost, and what the model cannot do with pixels**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (per-image token cost: moderate) |
| **Length** | ~3,000 words |
| **Depends on** | 3 |

**Scope.** The 2026 multimodal surface: images go directly into a prompt builder, any size and aspect ratio, no cropping or padding — but larger images cost more tokens and latency, and image input does not change which model services the request. The important negative result is that the model lists objects reliably and produces unreliable bounding boxes, so spatial localization belongs to Vision.

**Key sections**
- `Attachment(_:orientation:)` and `Attachment(imageURL:)` inside a `PromptBuilder` block
- Accepted sources: `CGImage`, `CIImage`, `CVPixelBuffer`, `UIImage`/`NSImage`, file URLs
- No documented resolution cap and no image-count cap — the context window is the only bound
- `.label(_:)` and the `Generable` `ImageReference` argument type for tools; `resolved(in:)`
- `Transcript.AttachmentSegment` and the new `Segment.attachment` case
- EXIF orientation is not applied by `CIImage(contentsOf:)` — bake rotation into pixels
- PhotosPicker `Transferable` wrappers and security-scoped file URLs on macOS
- Image budget estimation (~576 tokens per image as a working figure) for a context meter
- The bounding-box limitation, and routing localization to Vision saliency or detection
- Which backends accept images: on-device, PCC (unverified), third-party capability declaration
- Build-time vs runtime gating of image support, with the Python SDK's SDK flag as the cautionary case

**Sources.** `transcripts/fm-core.md` · `web/apple-docs-fm-evals-speech.md` · `forums/forum-pain-points.md` · `repos/mlx-swift-examples.md` · `repos/python-apple-fm-sdk.md`

---

#### 8. `fm-availability-errors-and-guardrails`
**When it goes wrong: availability, the 2026 error taxonomy, guardrails vs refusals, and safety design**

| | |
|---|---|
| **Pillar** | P2 Foundation Models — core API |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 3 |

**Scope.** The single largest and longest-running cluster of real-world pain in the corpus — thirteen forum threads spanning June 2025 to July 2026 with no resolution. Distinguishes four unavailability reasons, four distinct error hierarchies, and two *different* refusal mechanisms that developers constantly conflate. Ends with the design work Apple asks of you and the graceful-degradation UX Apple mandates.

**Key sections**
- Availability first: `isAvailable` / `isSupported` / `availability` and its four unavailable reasons
- What each reason implies for UX, and testing every branch via the Xcode scheme option
- The 2026 error split: `LanguageModelError`, `LanguageModelSession.Error`, `SystemLanguageModel.Error`, PCC errors
- `GenerationError` is deprecated but binary-compatible — rebuilding with Xcode 27 silently changes which `catch` fires
- All nine `LanguageModelError` cases with their payload fields
- **Two refusal surfaces**: `guardrailViolation` (classifier) vs `LanguageModelError.refusal` (model-level, untouchable by guardrail settings)
- `SystemLanguageModel(guardrails: .permissiveContentTransformations)` — and why it does not apply to `Generable`
- Apple may update guardrails outside the OS release cycle, so your prompt suite must run regularly
- Real false positives from the field, and the iOS 27 beta health-content refusal regression (FB23513774)
- Undocumented error codes seen in the wild: `SensitiveContentAnalysisML` 15, `ModelManagerError` 1046, `UnifiedAssetFramework` 5000
- Safety design: bounded input/output patterns, hosted deny lists, `@Generable` enum outputs, adversarial suites, the risk-assessment table
- `logFeedbackAttachment(sentiment:issues:desiredOutput:)` and the `#Playground` thumbs-up path
- Graceful degradation: a protocol seam with a non-AI fallback

**Sources.** `forums/forum-pain-points.md` · `web/apple-docs-fm-evals-speech.md` · `transcripts/fm-core.md` · `repos/noema-ios.md`

---

### Part 3 — Foundation Models: context, profiles, agentic sessions

#### 9. `fm-context-window-and-kv-cache`
**Context management: the 4K window, transcript anatomy, history compaction, and KV-cache economics**

| | |
|---|---|
| **Pillar** | P3 Foundation Models — context & agentics |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 5 |

**Scope.** Merges the two questions that always arrive together — *why did I get `exceededContextWindowSize`* and *why is time-to-first-token getting worse* — because both are about the same token layout. The mental model in one sentence: a session is instructions → tool definitions → transcript entries, and a change at position N invalidates the cache for everything after N. That sentence explains `historyTransform`, `summarizeHistory`, the Skills API, and why conditional instruction content must be declared last.

**Key sections**
- 4096 tokens on-device vs 32K on PCC — read `contextSize`, never hardcode
- What consumes the window: instructions, tool definitions, `Generable` schemas, transcript, tool I/O, reasoning text, images
- `tokenCount(for:)` (26.4+) and `Response.usage` with input / cached / output / reasoning counts
- Building a segmented context meter; `exceededContextWindowSize` and the fact that nothing auto-truncates
- `Transcript.Entry`: all six cases including the new `.reasoning`; segments (text, structure, attachment, custom)
- `Transcript.history` and why it excludes the leading instructions entry
- `session.transcript` is now mutable — but mutating while `isResponding` is a programmer error, not a thrown error
- The iOS 26 idiom (rebuild from a compacted `Transcript`) vs the iOS 27 idiom (mutate in place)
- `historyTransform` (local, lossless, per-profile) vs the `history` session property (lossy, global) — Apple's stated preference and a decision table
- The invalidation rule and its blast radius: appending preserves the cache; rewriting instructions, trimming, or changing tools does not
- Stateless-in-place vs dropping vs stateful transforms, and their different costs
- Conditional `DynamicInstructions` content must be declared last; batched consolidation beats incremental trimming
- Restoring a session has no KV cache — `prewarm(promptPrefix:)` 1–2 seconds ahead
- Measuring cache hit rate from cached-input-token counts; the measured 1044 → 700 max-token win
- **The accuracy hazard**: models reason confidently from evidence you removed

**Sources.** `transcripts/fm-advanced.md` · `web/apple-docs-fm-evals-speech.md` · `transcripts/fm-core.md` · `forums/forum-pain-points.md` · `repos/foundation-models-utilities.md` · `repos/noema-ios.md`

---

#### 10. `fm-dynamic-profiles-and-session-state`
**Dynamic Profiles from zero: `DynamicInstructions`, `Profile`, `LanguageModelSession.DynamicProfile`, and session properties**

| | |
|---|---|
| **Pillar** | P3 Foundation Models — context & agentics |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (exact modifier closure arities: moderate) |
| **Length** | ~6,500 words |
| **Depends on** | 5, 9 |

**Scope.** The flagship 2026 API and the one most likely to be written up incorrectly: the protocol is **nested** (`LanguageModelSession.DynamicProfile`), so code copied from the WWDC narration will not compile. A dynamic profile's `body` is re-evaluated before every prompt and resolves to exactly one active profile, which means the body must be pure and all imperative work belongs in lifecycle modifiers. Also carries session properties as the shared-state substrate.

**Key sections**
- The two problems Apple built it for: context management, and capability/cost boundaries
- The three layers: `DynamicInstructions` → `Profile` → `LanguageModelSession.DynamicProfile`
- The naming trap, and the exact nested spelling
- `var body: some LanguageModelSession.DynamicProfile`, the result builder, and the exactly-one-active-`Profile` invariant
- Nesting `DynamicInstructions` concatenates instructions *and* tools
- The body is re-evaluated every prompt (measured: 7 evaluations for 3 turns) — it must be pure
- The full modifier set: `model`, `temperature`, `samplingMode`, `reasoningLevel`, `maximumResponseTokens`, `contextOptions`, `toolCallingMode`, `transcriptErrorHandlingPolicy`, `historyTransform`, `modifier`
- Lifecycle modifiers: `onActivate`, `onDeactivate`, `onPrompt`, `onResponse`, `onToolCall`, `onToolOutput`, `onReasoning`
- The three-tier precedence rule: call-site arguments → innermost profile → outer container
- Session properties: `@SessionPropertyEntry` in an extension on `SessionPropertyValues`, `@SessionProperty(\.keyPath)`, `session.properties`
- History is read-only inside `DynamicInstructions` and `Tool` bodies
- Writing a reusable `DynamicProfileModifier`, and the extension ergonomics
- `LanguageModelSession(profile:)` and `(profile:history:)`; profile switches take effect on the next request and are a deliberate KV reset
- A worked multi-mode assistant

**Sources.** `transcripts/fm-advanced.md` · `web/apple-docs-fm-evals-speech.md` · `repos/foundation-models-utilities.md` · `forums/forum-pain-points.md`

---

#### 11. `fm-utilities-skills-and-history-modifiers`
**`foundation-models-utilities`: Skills, history modifiers, and the KV-cache trade-off made concrete**

| | |
|---|---|
| **Pillar** | P3 Foundation Models — context & agentics |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~5,500 words |
| **Depends on** | 9, 10 |

**Scope.** The separately-versioned, explicitly-experimental package that ships the opinionated layer Apple deliberately kept out of the OS framework — and the supported replacement for the context management people have been hand-rolling. Its Skill API is also the clearest teaching example of KV-cache economics in the corpus, because the choice between `prompt:` and `instructions:` decides whether the cache survives. Supported on Apple platforms *and select Linux distributions*, which is the concrete evidence for the "everywhere Swift runs" claim.

**Key sections**
- What ships out of band, why the API is explicitly unstable, and where to file issues (the forums, not GitHub)
- `Skill`: two storages and four initializers
- **The central table**: `prompt:` lands in a tool-output entry (cache preserved, normal priority) vs `instructions:` rewrites the instructions entry (cache invalidated, high priority)
- The choose-which heuristic, and the ASCII transcript diagrams worth reproducing
- A skill activates by generating a tool call — even `prompt:`-based ones
- `allowsDeactivation` and full context reclamation, combined with `droppingCompletedToolCalls`
- `Skills` conforming to `DynamicInstructions`; the synthesized toggle tool and its schema
- `SkillActivations` is `Observable` + `RandomAccessCollection`, so it drives SwiftUI directly — hold one per session
- `droppingCompletedToolCalls()`; `rollingWindow(entries:)` and its documented bug
- `summarizeHistory`: destroys tool-call metadata, requires a trailing prompt entry, has no default model
- Modifier application order (outside-in) resolved precisely, and the inert-composition trap
- Rolling your own with `@SessionProperty(\.history)` + `.onPrompt` — and why you now shouldn't
- What the shipped `SKILL.md` gets wrong: seven verified staleness points
- Known issues: `SkillActivation` build failures on the 26 SDK; the `ChatCompletionsLanguageModel` `v1` path bug

**Sources.** `repos/foundation-models-utilities.md` · `02-lead-agent-corpus-gaps-filled.md` · `transcripts/fm-advanced.md` · `forums/forum-pain-points.md`

---

#### 12. `fm-agentic-orchestration`
**Agentic orchestration: baton-pass, phone-a-friend, model routing, and transcript error policy**

| | |
|---|---|
| **Pillar** | P3 Foundation Models — context & agentics |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~4,500 words |
| **Depends on** | 10 |

**Scope.** Apple shipped primitives, not an `Agent` type — explicitly, because the field changes week to week. This guide covers the two orchestration patterns Apple named, which have *opposite* transcript semantics and are easy to conflate, plus the error, cancellation and routing machinery that makes multi-step agents survivable across model boundaries.

**Key sections**
- Why there is no `Agent` type
- Baton-pass: shared transcript, a mode variable, a tool that flips it; the receiving profile answers
- Phone-a-friend: a tool spawns a short-lived child session with an isolated transcript; the parent always answers
- Side-by-side comparison: transcript visibility, who answers last, cost, privacy
- Exposing the mode switch itself to the model as a tool
- Combining baton-pass with `.toolCallingMode(.required)` and a compiled reference exit condition
- Model routing across on-device, PCC and third-party inside one session
- Crossing a privacy boundary ships the accumulated transcript to the new backend
- Crossing from a 32K profile to a 4K one throws unless you apply a `historyTransform`
- `transcriptErrorHandlingPolicy`: `.revertTranscript` (default) vs `.preserveTranscript`, and who owns repair
- Cancellation mid-turn, resuming, and repairing a preserved transcript
- Third-party caveat: tool-driven routing is unreliable on small models — route with guided generation instead
- Memory cost of keeping two models resident; why every context-engineering change needs an Evaluations gate

**Sources.** `transcripts/fm-advanced.md` · `web/apple-docs-fm-evals-speech.md` · `repos/mlx-swift-lm.md` · `repos/apple-coreai-models.md`

---

### Part 4 — Foundation Models: beyond the built-in model

#### 13. `fm-private-cloud-compute`
**Private Cloud Compute end to end: eligibility, entitlement, reasoning levels, quota UX, and fallback architecture**

| | |
|---|---|
| **Pillar** | P4 Foundation Models — providers & backends |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (Small Business Program condition: one more direct confirmation recommended) |
| **Length** | ~4,500 words |
| **Depends on** | 8 |

**Scope.** PCC has far more policy than API, and for a large fraction of readers the correct answer is "you are not eligible" — so the guide leads with the three-condition gate rather than the one-line model swap. Then covers the capability delta (32K, reasoning), the quota UX Apple prescribes in detail, and designing PCC as one tier behind a protocol rather than as the foundation.

**Key sections**
- What PCC is, and what it costs the developer (nothing)
- **Eligibility is three conditions**: App Store Small Business Program enrollment, fewer than 2 million *lifetime first-time* downloads, and the managed entitlement — only the second is mentioned in the WWDC sessions
- Losing eligibility: notification plus a six-month migration window; TestFlight installs don't count
- The one-line switch to `PrivateCloudComputeLanguageModel()`; a missing entitlement is a runtime `fatalError`, not a catchable error
- `availability` and its distinct unavailable reasons (`systemNotReady` has no `SystemLanguageModel` analogue)
- 4K vs 32K, and when the bigger window actually changes your design
- `ContextOptions(reasoningLevel:)` — light, moderate, deep — and reasoning text counting against the context limit
- Reading reasoning entries and `reasoningTokenCount` for progress UI
- `quotaUsage`: `isLimitReached`, `belowLimit` with `isApproachingLimit`, `resetDate`, `limitIncreaseSuggestion.show()`
- Apple's prescribed quota UX: no alerts, persistent in-place state, disabled button, actionable upgrade — and why waiting doesn't help
- Xcode scheme options for simulating quota states; PCC does not work in the Simulator at all
- watchOS 27 as a PCC-primary surface, and the open pairing question
- Locale gating, network-failure fallback to on-device, and designing a tiered protocol seam
- Open question: does PCC accept images, and do they carry separate quota?

**Sources.** `transcripts/fm-ecosystem.md` · `02-lead-agent-corpus-gaps-filled.md` · `forums/forum-pain-points.md` · `web/apple-docs-fm-evals-speech.md` · `repos/noema-ios.md`

---

#### 14. `byo-model-behind-languagemodelsession`
**Running an open-weight model behind `LanguageModelSession`: Core AI, MLX, and any OpenAI-compatible endpoint**

| | |
|---|---|
| **Pillar** | P4 Foundation Models — providers & backends |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~4,000 words |
| **Depends on** | 1, 5 |

**Scope.** The consumer-side answer to "I want a different model but I like this API" — three concrete paths, each roughly one line to adopt. This is the single highest practical-leverage item in the corpus, because `ChatCompletionsLanguageModel` turns `mlx_lm.server`, Ollama, vLLM and LM Studio into Foundation Models backends today, without waiting for anything.

**Key sections**
- What "everything downstream stays the same" actually buys you: streaming, `@Generable`, tools, Instruments, evaluations
- `CoreAILanguageModel(resourcesAt:variant:kvCacheStrategy:)` for your own bundle
- `MLXLanguageModel` from `MLXFoundationModels` in `mlx-swift-lm` (requires the 27 SDK)
- `ChatCompletionsLanguageModel(name:url:additionalHeaders:)` — and `supportsGuidedGeneration: false` for servers that don't enforce schemas
- **The live `v1` path bug**: `pathComponents.contains("v1")` breaks servers on other version paths (FB23837262)
- Capability declaration is user-visible: vision, toolCalling, guidedGeneration, reasoning
- How guided generation is enforced on a non-Apple model: xgrammar constrained decoding
- Pointing it at `mlx_lm.server`, Ollama, LM Studio and vLLM, end to end
- `usage` token accounting across providers, built for per-token billing
- Auth for cloud providers: token provider + Keychain + App Attest; never an API-key initializer
- The privacy-disclosure obligation on both package author and consumer
- What breaks with small models: tool-call dialects, decoding failures, thinking-token loops
- A capability-based routing table for a multi-model app; when to write your own provider instead

**Sources.** `transcripts/fm-ecosystem.md` · `repos/foundation-models-utilities.md` · `repos/mlx-swift-lm.md` · `repos/apple-coreai-models.md` · `02-lead-agent-corpus-gaps-filled.md` · `forums/forum-pain-points.md`

---

#### 15. `authoring-a-languagemodel-provider`
**Authoring a `LanguageModel` provider package: the protocol, capabilities, transcript translation, and the generation channel**

| | |
|---|---|
| **Pillar** | P4 Foundation Models — providers & backends |
| **Audience** | Swift package author |
| **Evidence** | **Strong** |
| **Length** | ~7,500 words |
| **Depends on** | 9, 14 |

**Scope.** The architectural centerpiece of WWDC26, and the guide with the highest ratio of importance to existing documentation. Two protocols and one linking value: `LanguageModel` declares capabilities and vends a `Configuration`; `LanguageModelExecutor` owns weights and streams. Written against Apple's own `foundation-models-language-model-protocol` agent skill, with three real conformances (`ChatCompletions`, `CoreAI`, `MLX`) readable side by side.

**Key sections**
- `LanguageModel` and `LanguageModelExecutor`: verbatim declarations and the associated-type machinery
- `LanguageModelCapabilities.Capability`, and why declaring one you don't strictly support is a bug (the framework routes on it)
- Reading a request: transcript, `enabledToolDefinitions`, schema, options, id, metadata
- The `ContextOptions` (prompt content) vs `GenerationOptions` (decoder loop) split
- Mapping the six `Transcript.Entry` types onto your model's system/user/assistant roles
- The generation channel: three top-level events, every action (`appendText`, `appendArguments`, `updateMetadata`, `updateUsage`, `replaceTextSegment`, `removeToolCall`)
- `entryID` hygiene and the consecutive-events-only coalescing rule
- `updateUsage` and `updateMetadata` are wholesale replacements, not additive
- Every `toolCall` event must carry the function name; `removeToolCall` exists because there is no `replaceArguments`
- Reasoning signatures are opaque bytes; one-shot is streaming underneath
- The prescribed event ordering — and the beta hazard that following it materializes an empty Response entry on tool-call turns
- `Transcript.CustomSegment` as the modality extension point; attachment segments add and remove but never replace
- Approximate or throw: when to bend to developer intent, and when to throw a built-in `LanguageModelError`
- Server-side tools and the three disclosure levels
- Cancellation contract; testing with request builders, a recording event sink, and end-to-end through `LanguageModelSession`

**Sources.** `repos/foundation-models-utilities.md` · `transcripts/fm-ecosystem.md` · `repos/mlx-swift-lm.md` · `repos/apple-coreai-models.md`

---

#### 16. `provider-executor-store-and-kv-reuse`
**Provider internals: the executor store, `Configuration` hashing, prewarm lifecycle, stateful KV reuse, auth and packaging**

| | |
|---|---|
| **Pillar** | P4 Foundation Models — providers & backends |
| **Audience** | Swift package author |
| **Evidence** | **Strong** |
| **Length** | ~6,000 words |
| **Depends on** | 15 |

**Scope.** Everything after the protocol conformance compiles: making it fast, correct under error, and safe to ship. The hard part is that your executor receives the *full transcript* on every `respond` call — you must diff it, preserve state on append-only changes, and invalidate back to the divergence point otherwise. Measured payoff in a real implementation: 0.33 s turn-two latency versus 2.8 s without diffing.

**Key sections**
- The per-session executor store: `Configuration` is `Hashable` and is the lookup key — *not* the model
- Same configuration ⇒ shared executor, shared weights, shared KV state
- What belongs in a `Configuration`, and the manual `==`/`hash` pattern for non-Hashable engine handles
- Automatic session-scoped teardown, and why a process-global weights cache opts you out
- The silent-no-op `prewarm` trap: a near-miss signature compiles and binds the default
- The transcript-diff algorithm: append-only fast path, divergence detection, invalidate-to-divergence
- Reporting `cachedTokenCount` honestly, and the measured payoff
- Two structural blockers: post-EOS over-generation poisoning the cache; thinking-model templates stripping historic reasoning
- Incremental detokenization: U+FFFD handling and one token of SentencePiece context
- Parsing reasoning tags and tool calls out of a raw text stream with hold-back windows
- Auth: never take an API key `String` in your initializer; token providers, Keychain, App Attest
- Packaging: SwiftPM platforms, Linux reach, dependency weight, git-tag distribution
- The `updateUsage` symbol present in the `.swiftinterface` but absent from the dylib, which SIGSEGVs at image load

**Sources.** `transcripts/fm-ecosystem.md` · `repos/foundation-models-utilities.md` · `repos/mlx-swift-lm.md` · `repos/apple-coreai-models.md` · `repos/issues-mlx-stack.md`

---

### Part 5 — Prototyping, profiling, and non-Swift access

#### 17. `fm-playground-and-instruments`
**Prototyping and profiling: `#Playground`, scheme simulation, and reading a Foundation Models trace**

| | |
|---|---|
| **Pillar** | P5 Developer tooling & non-Swift access |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (four of six Instruments lanes unnamed in the corpus) |
| **Length** | ~4,500 words |
| **Depends on** | 5, 9 |

**Scope.** The only observability story for a runtime you cannot unit-test in the usual way. The worked bug is the teaching device: instruction prose referenced a tool that was never registered, the model looped forever, and nothing threw — nothing in the SDK cross-checks instruction prose against the declared toolset. The diagnostic sequence is the transferable skill.

**Key sections**
- `#Playground`: multiple blocks as canvas tabs, project-wide type access with no build, the response inspector, thumbs-up feedback
- Apple's canonical three-step workflow: playground → view model → view
- Edit Scheme → "Simulated Foundation Models availability" to exercise every unavailable and quota branch on one machine
- Launching the Instruments Foundation Models template, and the record-anyway confirmation
- **Privacy**: trace files contain unencrypted prompts and responses — treat them as sensitive
- The lanes: Instructions (a profile-switch visualizer) and Model Inference (yellow prefill, orange decode); the other four are undocumented — do not fabricate them
- The tree hierarchy, and the invariant that every model inference has instructions, a prompt, and either a response or an error
- One user request fans out into multiple model inferences
- The Info column as a triage filter for errors, long durations, and large token counts
- The Instructions node inspector — the only cross-check of prose against the declared toolset
- The three metrics with prescribed fixes: time to first token, tokens per second, total latency
- Reading cache invalidations and cache hit rate from a trace
- The full worked debugging narrative, symptom to verified fix
- The instrument works with any `LanguageModel` provider, not just Apple's; handing off to Evaluations

**Sources.** `transcripts/fm-advanced.md` · `transcripts/fm-core.md` · `web/apple-docs-fm-evals-speech.md`

---

#### 18. `fm-cli-and-python-sdk` ⚠
**Foundation Models without Swift: the `fm` CLI and `apple-fm-sdk`**

| | |
|---|---|
| **Pillar** | P5 Developer tooling & non-Swift access |
| **Audience** | Python ML engineer, scripters |
| **Evidence** | **Moderate** — see caveat |
| **Length** | ~5,500 words |
| **Depends on** | 4 |

> **⚠ Evidence caveat.** The `fm` CLI's actual flags were never shown on screen; only semantic option names were spoken aloud ("the model option", "the image option"). `fm schema object`'s argument grammar, the full subcommand list, the slash commands beyond `/model` and `/save`, and everything about `fm serve` need a live macOS 27 run before publication. Separately, the public `apple/python-apple-fm-sdk` repo is at the **26 generation** (no PCC, no dynamic profiles, no `LanguageModel` protocol) while WWDC26 presented the SDK as new-this-year; whether a 27-era release exists is unresolved.

**Scope.** Both non-Swift access paths, including the substantial install friction the WWDC talk understates and the parity gaps that matter. Covers `fm`'s subcommands and `fm serve` as Apple's stated path to PCC from Python (there is no PCC in the SDK), then the SDK's custom build backend, its Swift↔Python API mapping, and five confirmed bugs found by reading both sides of the bridge.

**Key sections**
- `fm` ships preinstalled with macOS 27: `respond`, `chat`, `schema`, `schema object`, `serve`
- Slash commands and structured JSON output for shell pipelines
- `fm serve` as the sanctioned PCC bridge from Python — and as a Chat-Completions endpoint
- `pip install apple-fm-sdk`: a custom PEP 517 backend that shells out to `swift build`; requires full Xcode, not CLT, with the license accepted
- Image support is gated on the **build-time** SDK version as well as the runtime OS
- The Swift → Python API mapping table
- `@fm.generable`, `fm.guide` as a default value, `generating=` (not `response_type=`)
- The guide-versus-type compatibility matrix, validated at `respond()` time rather than decoration time
- Tools: the bridged-callback design, and why exceptions become model-visible strings
- Streaming yields cumulative snapshots; there is no structured streaming
- Transcripts: importing Swift-exported transcript JSON for batch analysis — the real cross-language workflow
- `context_size` and `token_count` (macOS 26.4+)
- Known bugs in 0.2.1: dropped options with `generating=`, sampling params serialized as strings and ignored, Python 3.14 optionality detection, and an FD leak that fails after ~240 image calls (fixed on `main`, not in a tagged release)
- Memory management across the boundary, and why you must never call `_release()`

**Sources.** `repos/python-apple-fm-sdk.md` · `transcripts/fm-core.md` · `repos/issues-community-stack.md` · `01-lead-agent-repo-spotchecks.md` · `forums/forum-pain-points.md`

---

### Part 6 — Evaluations

#### 19. `evals-foundations-and-hill-climbing`
**The Evaluations framework: building blocks, Swift Testing integration, the Xcode report, and evaluation-driven development**

| | |
|---|---|
| **Pillar** | P6 Evaluations |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (a full docs index and 12+ article pages were harvested; several exact signatures remain unverified) |
| **Length** | ~5,500 words |
| **Depends on** | 3 |

**Scope.** New in Xcode 27, Swift-only, built on Swift Testing and TabularData, and explicitly not LLM-only — any stochastic system qualifies. Covers the `Evaluation` protocol's four responsibilities, loaders, metrics and aggregation, the `.evaluates` test trait, the Xcode report where the actual analysis happens, and the hill-climbing loop Apple calls evaluation-driven development. Mark reconstructed signatures visibly; several names come from spoken narration rather than a fetched page.

**Key sections**
- Why generative models break a contract fundamental to software testing; Apple's three questions
- Platform gates: Swift only, Xcode 27+, macOS/iOS/watchOS/visionOS (tvOS absent)
- The `Evaluation` protocol: `dataset`, `subject(from:)`, `evaluators`, `aggregateMetrics(using:)`
- `ModelSample` / `ModelSampleProtocol` / `ModelSubject` / `StructuredTranscript`; Codable datasets
- Loaders: `ArrayLoader`, `JSONLoader` (which silently skips malformed rows), `StreamLoader`
- `Metric` and its `passing` / `failing` / `scoring` / `ignore` results; the name doubles as a DataFrame column
- `MetricsAggregator`: built-in statistics, custom, and group aggregation
- Running it: `@Test(.evaluates(...))`, `EvaluationContext.current.result`, `aggregateValue` inside `#expect`
- The Xcode 27 report navigator: charts, results table, per-sample assistant editor; the Compare view and run notes
- `EvaluationResult` summary and detailed DataFrames with typed column subscripts
- **A passing test does not mean good output** — the `@Guide(count:)` case where a 100% pass rate hid a degenerate distribution
- 20–30 hand-written samples is a fine start; coverage beats count
- The hill-climbing loop: develop → evaluate → analyze → repeat; change one variable, then promote the winner into the baseline
- Hill-climbing things that are not prompts (adding a tool with a defaulted parameter, so the old evaluation keeps working)
- Using Evaluations as the regression gate against OS-update model drift, since there is no version pinning API
- PCC-backed evaluation may consume the user's metered quota in CI

**Sources.** `transcripts/evals-mlx.md` · `web/apple-docs-fm-evals-speech.md` · `forums/forum-pain-points.md`

---

#### 20. `evals-model-judges-and-alignment`
**Model judges, score dimensions, drift, and Cohen's kappa**

| | |
|---|---|
| **Pillar** | P6 Evaluations |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (ScoringMode cases and a few initializer shapes unverified) |
| **Length** | ~7,000 words |
| **Depends on** | 19 |

**Scope.** Qualitative evaluation, and then the meta-evaluation that tells you whether your judge can be trusted. The central conceptual moment is that when you disagree with a judge, the judge is usually faithfully following your rubric — so you split the dimension rather than argue with the score. The second half is the most statistically sophisticated material in the corpus: drift, why accuracy is the wrong alignment metric on skewed datasets, and the kappa-based meta-evaluation recipe.

**Key sections**
- When a metric must be qualitative: "if you can measure it in code it's quantitative"
- A judge is just another `Evaluator` producing the same `Metric` type — quantitative and qualitative mix freely
- The judge must be at least as capable as the model under test (on-device feature → PCC judge)
- Judge anatomy: instruction, feature input, feature output, scoring guide — the framework handles all but the last
- `ScoringScale`: numeric, pass/fail, custom enum; use an **even** number of levels so the judge cannot default to a neutral middle
- `ScoreDimension` authoring: name, description, per-level observable descriptions
- Pointwise, multi-dimension (all dimensions in one call), and pairwise-vs-baseline modes
- `ModelJudgePrompt` and why app context matters — a context-free judge treats criticism as a valid descriptor
- Rationales as the primary debugging signal; uniform scores mean your dimension is too broad
- The refinement loop and the worked "quality → Relevance + Usefulness" split
- **Drift**: systematic judge/human disagreement that widens with dataset size
- Why plain accuracy is misleading on score-skewed datasets (and they always are)
- Cohen's kappa: `(accuracy − chance) / (1 − chance)`, prevalence-weighted, with the 0.6 threshold — implemented as a custom aggregation, not a built-in
- The meta-evaluation recipe: pull the Xcode attachment, add human ratings, freeze `subject()` so the judge is the only variable
- Three documented improvement iterations and the relevance-up/usefulness-down trade-off
- Too many few-shot examples overfit the alignment score itself; when to stop tuning the judge

**Sources.** `transcripts/evals-mlx.md` · `web/apple-docs-fm-evals-speech.md`

---

#### 21. `evals-datasets-and-tool-trajectories`
**Building evaluation datasets with `SampleGenerator`, and evaluating agentic behavior with `TrajectoryExpectation`**

| | |
|---|---|
| **Pillar** | P6 Evaluations |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 5, 19 |

**Scope.** Where most teams actually spend their time: getting enough data, and then checking *how* the model got there rather than only what it produced. Two halves that belong together because trajectory expectations are themselves `Generable`, so the same generator builds both kinds of dataset. Leads with the healthy reality check that scaling a dataset from 13 to 100 samples made the scores drop — which was the point.

**Key sections**
- Seeds first: 20–30 hand-written samples covering the space
- `makeSamples(prompt:dataset:targetCount:)` and the `targetCount` trap — it *includes* your seeds
- Full `SampleGenerator` control: `sessionProvider`, `samplingStrategy`, `validator`
- `sessionProvider` is called once but re-invoked with **no prior context** on context exhaustion — instructions must be self-contained
- Random vs sliding-window sampling, and when order is meaningful
- The validator sees one sample in isolation, so corpus-level properties cannot be checked there; prompt rules are not guarantees
- `samples` vs `invalidSamples`, updated live; running generation from a command-line tool and checking the result in
- Expect scores to drop when you scale, and the four hypotheses when they do
- Why output-only evaluation is insufficient: "the final output can look correct while the path to get there isn't"
- `TrajectoryExpectation` with ordered, unordered, disallowed, and `allowsAdditionalToolCalls`; `ToolExpectation` any-order groups
- The nine `ArgumentMatcher` strategies, including the judge-backed `naturalLanguage` matcher
- `ToolCallEvaluator` with `allPass` and `percentagePass`
- Ordered trajectories catching real bugs (calling get-details before you have an ID); `disallowed` as a negative-instruction test
- Synthesizing trajectory datasets — and the fact that the generating model knows nothing about your tools
- Stub tools for evaluation; a Spotlight-grounded worked example with a result-coverage metric
- Running output and trajectory evaluation in one suite

**Sources.** `transcripts/evals-mlx.md` · `web/apple-docs-fm-evals-speech.md` · `transcripts/fm-ecosystem.md`

---

### Part 7 — Core AI: the Swift runtime

#### 22. `coreai-runtime-and-ndarray`
**Core AI from zero: `AIModelAsset`, `AIModel`, `InferenceFunction`, and the `NDArray` memory model**

| | |
|---|---|
| **Pillar** | P7 Core AI — Swift runtime |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (no documented error type for the throwing paths — see gaps) |
| **Length** | ~7,000 words |
| **Depends on** | 1, 2 |

**Scope.** The complete happy path plus every gotcha that blocks a first build, and then the densest, most error-prone area of the framework: the memory model. Core AI is one of the heaviest users of modern Swift ownership features in the SDK — `Span`, value generics, `~Escapable`, `consuming` — so the API is unreadable without that background, and this guide teaches both. Ends with the layout rule that silently costs a copy on every inference.

**Key sections**
- What Core AI is, where it sits relative to Core ML and Foundation Models, and the seven platforms it ships on
- The Metal Toolchain is not installed with Xcode: builds containing `.aimodel` fail with a missing-Metal-compiler error; `.aimodel` must be in Compile Sources
- `AIModelAsset`: inspect without specializing — `isValid(at:)`, `summary(includingStatistics:)`, compute vs storage types, operation distribution, the six typed metadata subscripts
- The Xcode model viewer: General and Functions tabs, dynamic dims as `?`, editable metadata
- `AIModel(contentsOf:options:)` is `async` because it specializes; `functionNames`, `functionDescriptor(for:)`, `loadFunction(named:)` — nil vs throw, and it can be expensive too
- `InferenceFunctionDescriptor`: inputs, outputs, states — adapt to model changes via descriptors instead of hardcoding
- Ownership traps: `InferenceValue.ndArray` is a consuming read; `Outputs.remove(_:)` is a destructive take-once; a double take is a fatal error
- The four view types and the compile-time read/write split; `Span` / `MutableSpan` / `RawSpan` / `MutableRawSpan`
- `contiguousElements` returns nil for non-contiguous layouts; `withUnsafePointer`; the shape is a non-escapable `Span<Int>` with no `for-in` and no `map`
- `slice(at:)` vs `mutatingSlice(at:)`, trailing dims defaulting to `.all`, and `MutableRawView.view(as:)` returning a `MutableView` despite the name
- `NDArrayDescriptor`: `-1` for dynamic, `hasDynamicShape`, `resolvingDynamicDimensions(_:)` required before `preferredStrides` or `minimumByteCount`
- **`preferredStrides` may be non-contiguous** — ignoring it can cost a layout-conversion copy on every run
- `InterleaveLayout`: block strides, the exact element-offset formula, and when the shape/stride equivalence breaks
- The 33 `ScalarType` cases: FP8, MX block formats, complex, 128-bit ints, sub-byte int2–int7
- Zero-copy backing from raw memory, `MTLBuffer` (shared storage only) and `IOSurface`; image values and `ImageDescriptor`
- Concurrency: `InferenceFunction` is `Sendable` but silently allocates more scratch buffers to be so; watchOS availability cliffs

**Sources.** `web/apple-docs-coreai.md` · `transcripts/coreai-intro.md` · `repos/apple-coreai-models.md` · `repos/swift-lm.md` · `repos/noema-ios.md`

---

#### 23. `coreai-specialization-caching-and-aot`
**Specialization, `AIModelCache`, and ahead-of-time compilation with `coreai-build`**

| | |
|---|---|
| **Pillar** | P7 Core AI — Swift runtime |
| **Audience** | Both |
| **Evidence** | **Strong** (`coreai-build`'s full flag surface unknown; cache-deletion semantics self-contradictory in Apple's docs) |
| **Length** | ~6,500 words |
| **Depends on** | 22 |

**Scope.** The single largest source of first-launch latency, wedged loads and mysterious storage growth — and, on iOS, of a maximally misleading error message. A `.aimodel` is portable *source*; before it can run it must be specialized to this device **and this OS version**, and iOS cannot JIT the IR at all, so AOT is not an optimization there but a requirement. Covers the cache key, the bookmark workflow that lets you delete the source, and per-architecture artifact fan-out.

**Key sections**
- What specialization actually is: two phases, and which is expensive; artifacts tied to device *and* OS version
- The automatic-and-cached default path, and the three latency levers
- `AIModelCache.default` and `model(for:options:)` returning nil **without** specializing — use it to gate "preparing…" UI
- The cache key is `(source URL, SpecializationOptions)`; `SpecializationOptions` is `Hashable`, so varying it duplicates multi-GB entries
- `AIModel.specialize(...)` controls *when*, not *how much*
- `AIModelCache.Policy` and `PurgeConditions` vs `.persistent`; OS updates always invalidate
- `deleteEntry` / `deleteEntries` / `deleteAll` — and the documented contradiction about live references
- App-group sharing via `AIModelCache(appGroup:)` plus entitlement, and its nil-return failure modes
- The bookmark workflow: `bookmarkData` → UserDefaults → `init?(resolvingBookmark:)`; bookmarks do not pin the entry and fail two different ways
- `SpecializationOptions`: default, cpuOnly, `preferredComputeUnitKind`, `availableKinds`, and the undocumented `expectFrequentReshapes`
- Every new input shape on a dynamic graph re-specializes — bucket your prefill chunks
- **iOS cannot JIT**: loading raw IR on device fails with `NSPOSIXErrorDomain Code=2 "No such file or directory"`
- `xcrun coreai-build compile` and its flags; one `.aimodelc` per architecture matched with `AIModel.deviceArchitectureName`
- AOT targets only Apple-Intelligence-capable hardware (A17 Pro+, M1+, M2 Vision Pro) and does not eliminate residual specialization
- The bundle hand-edit afterwards: point `metadata.json`'s `assets.main` at the compiled filename
- Compute unit is fixed by export shape, not a runtime flag — ship two bundles if you need both
- Known crashes: ANE pre-compiler SIGSEGV on linear INT4; a macOS `.aimodelc` load regression
- Measured cold vs warm engine-ready times; a recovery ladder for wedged loads

**Sources.** `web/apple-docs-coreai.md` · `transcripts/coreai-intro.md` · `web/community-blogs.md` · `repos/noema-ios.md` · `repos/issues-coreai-stack.md` · `repos/issues-community-stack.md`

---

#### 24. `coreai-states-and-pipelined-execution`
**States, KV caches, and pipelined inference: `ComputeStream`, `AsyncValue`, and pre-allocated outputs**

| | |
|---|---|
| **Pillar** | P7 Core AI — Swift runtime |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~6,000 words |
| **Depends on** | 22 |

**Scope.** The highest-leverage performance technique in Core AI, taught end to end across three layers, plus the tier above `run()`. Apple's own teaching arc: a decode loop whose inference intervals visibly grow in the Instruments track, fixed by turning the KV cache into **state** — an argument the function both reads and writes in place. Includes the honest hedge that latency still grows, just far more slowly, and a real pipelined decode loop with buffer rotation and backpressure.

**Key sections**
- What a state is; the KV-cache story end to end: `register_buffer` → mutable buffer → `state_names` → `MutableViews`
- Building `MutableViews` recursively and passing them with `consume`; you must supply a view for every state (there is no `stateCount`)
- Fixed-size caches and the up-front memory trade-off; the "latency grows more slowly, not flat" lesson
- The copy-on-write trap: in-place state updates copy the whole cache every step unless you park a placeholder `NDArray` in the slot
- Cross-turn state reuse via a fed-token log and prefix comparison
- The host-cache alternative, and why the ANE compiler sometimes forces it
- `outputViews:` for pre-allocated outputs — and the fork where those outputs are omitted from the returned `Outputs`
- `encode(...)` is `throws`, not `async throws`: it returns once work is *encoded*
- `ComputeStream()` and `ComputeStream(commandQueue:)`; automatic serialization by data dependency
- `AsyncValue` (a class) and `AsyncMutableValue` (a struct), MTLBuffer-backed values, copy-on-read, `currentWorkCompleted()`
- A real pipelined decode loop: pipeline depth, rotating buffers, keeping the next token on the GPU, backpressure, and an empty-command-buffer completion sentinel
- Diagnosing the growing-inference-interval signature in Instruments

**Sources.** `transcripts/coreai-intro.md` · `web/apple-docs-coreai.md` · `repos/apple-coreai-models.md` · `repos/noema-ios.md` · `repos/swift-lm.md`

---

#### 25. `coreai-bundles-engines-and-guided-decoding`
**Model bundles and the Core AI LLM runtime: `metadata.json` 0.2, four engines, KV strategies, samplers, and xgrammar**

| | |
|---|---|
| **Pillar** | P7 Core AI — Swift runtime |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~7,500 words |
| **Depends on** | 22, 24, 15 |

**Scope.** The layer between a raw `.aimodel` and a working chat loop. Covers the bundle format that everything in the ecosystem agrees on and no Apple doc describes; the four real LLM engines and why the choice is made *for* you by graph structure rather than a runtime flag; and — a mechanism that appears in no transcript and no doc page — how `@Generable` is enforced on an arbitrary model via grammar-constrained decoding. Both Apple's `coreai-models` and `mlx-swift-lm` independently reach for xgrammar; convergent design worth documenting.

**Key sections**
- Why some models need more than a `.aimodel`: tokenizers, multi-asset pipelines, three-asset VLMs
- `metadata.json` schema 0.2: `metadata_version`, `kind`, the assets role map, the language block, `function_map`, the vision block
- The `tokenizer/` sibling directory; runtime-family folder conventions matched on exact path components
- The `.aimodel` is a *directory* — pointing `resourcesAt:` at it yields a misleading version error; the `coreai-core >= 1.0.0b2` producer gate
- What `verify()` checks, and who calls it
- `EngineFactory` auto-detection from graph function names → structure → engine → specialization options
- The four engines: pipelined GPU (no logits), sequential (CPU sampling, logits), static-shape ANE, and VLM; the variant-by-structure compatibility matrix
- `KVCacheStrategy`: auto, fixedSize, growing, and `chunked` which is accepted but unimplemented
- Prefill chunking memory math: 9.6 GB of fp16 logits unchunked vs 155 MB at 512; S=1 decode-only bundles cannot take block prefill
- Implicit prefix caching via token history; the pipelined engine cannot rewind because of overshoot past EOS
- Sampling: the CPU Accelerate path and the MPSGraph GPU path; a shared execution descriptor corrupts output above temperature 0
- **Guided decoding with xgrammar**: the C bridge, DLPack bitmasks, grammar compilation, masking sentinels, dual termination detection — and why it excludes the pipelined engine
- A confirmed dead parameter: stop-token ids are accepted and never forwarded; multi-token stop sequences unsupported
- Streaming detokenization, U+FFFD, SentencePiece spacing; reasoning-tag and tool-call stream parsers
- `CoreAILanguageModel` as a `LanguageModel` conformance — and what Foundation Models does *not* forward (only temperature)
- Hybrid and SSM models hit the two-state engine wall ("Expected 2 states, got 4")

**Sources.** `repos/apple-coreai-models.md` · `repos/noema-ios.md` · `01-lead-agent-repo-spotchecks.md` · `repos/issues-coreai-stack.md` · `repos/issues-community-stack.md` · `repos/mlx-swift-lm.md`

---

### Part 8 — Core AI: converting a model from PyTorch

#### 26. `coreai-torch-conversion-and-io-contract`
**PyTorch to `.aimodel`: the `coreai-torch` pipeline, and the IO / state / dynamic-shape contract**

| | |
|---|---|
| **Pillar** | P8 Core AI — Python conversion |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~8,500 words |
| **Depends on** | 22 |

**Scope.** The spine guide for everything in Parts 8–10. There is no `convert()` function: the pipeline is export → decompose with Core AI's table → convert → optimize → save, and each stage has a silent failure mode. The second half is the naming/state/dynamic-shape contract, which is small in surface area and enormous in footgun density — the default names and state ordering are *observed FX behavior*, not a stable PyTorch contract, and the converter can only assert that counts match.

**Key sections**
- Install and version gates: Python 3.11+, torch 2.8–2.13, a pinned `coreai-core`; `uv` for the model recipes
- The canonical pipeline: `eval()` → `torch.export` → `run_decompositions(get_decomp_table())` → `TorchConverter` → `to_coreai` → `optimize` → `save_asset`
- `run_decompositions` is **mandatory**; what `get_decomp_table` deliberately preserves and why
- `to_coreai()` runs zero optimization — forgetting `optimize()` leaves unfused casts and a broken state signature
- **`optimize()` is not always semantics-preserving**: a documented ~17 dB PSNR regression; always A/B numerically
- `add_exported_program` vs `add_pytorch_module` with `export_fn` and `externalize_modules`
- `TorchConverter(mode:)`: `DEBUG` is the default and embeds torch stack traces — strip for release
- Naming arguments are keyword-only in source; `to_coreai(entrypoints=)`, `clear(entrypoints=)`, converter reuse
- Multi-entrypoint assets and the SAM3 three-function split, with its measured 76% prompt-swap win
- Running from Python for numeric parity, and the buffer-lifetime footgun (`.numpy()` inside the executable block)
- **Part 2 — the contract**: `input_names`/`output_names` now cover only non-stateful IO (a breaking change)
- What counts as state (registered buffers *and* mutated forward arguments) and the fact that there is no opt-out
- `state_names` ordering rules, the `MutableBuffers.buffer_mutation` IR attribute, and why stateful models effectively require `optimize()`
- Dynamic shapes: `Dim`, SymInts surfacing as `?`, the INT32 slice clamp, symbolic slice arguments rejected outright
- Ops that raise on dynamic values: split, var/std with ddof, tensordot, tril/triu
- int64 → int32 and float64 → float32 silently narrowed everywhere; sub-byte and reduced-precision dtypes; `inject_subbyte_tensors`
- Reading the emitted IR, filecheck-style assertions, and the `graphdiff` / `freqop` CLIs
- The `coreai-core >= 1.0.0b2` version floor and `strip_debug_info` as the rescue path

**Sources.** `repos/coreai-torch.md` · `transcripts/coreai-python-metal.md` · `01-lead-agent-repo-spotchecks.md` · `repos/issues-coreai-stack.md` · `transcripts/coreai-intro.md` · `repos/apple-coreai-models.md`

---

#### 27. `coreai-torch-coverage-composites-and-lowerings`
**When an op won't convert: coverage, composite ops, externalization, and custom lowerings**

| | |
|---|---|
| **Pillar** | P8 Core AI — Python conversion |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~7,500 words |
| **Depends on** | 26 |

**Scope.** The "my model won't convert" guide, plus the performance half nobody talks about: composite ops are how you tell Core AI "this is attention / RoPE / RMSNorm / MoE dispatch" so it dispatches to a fast kernel instead of a decomposed soup. Contains three concepts absent from every WWDC transcript — a first-class composite-op library, externalization, and custom op lowering — including the finding that Core AI has first-class MoE (`gather_mm`) and linear-attention/SSM (`gated_delta_update`) support that nobody announced.

**Key sections**
- The op-resolver contract: FX-qualified `op.overload` names, and the footgun that a different overload is simply unsupported
- The two pre-conversion validator errors, and the decision tree they imply
- The composite-op library as a signal that a fast kernel exists: SDPA, RoPE, RMSNorm, layer/group/instance norm, pixel shuffle
- **`GatherMM` is MoE expert dispatch; `GatedDeltaUpdate` is a linear-attention/SSM state update** — stated in no talk
- The three-step pattern: named submodule → module-based conversion → `ExternalizeSpec`
- `ExternalizeSpec` must target the inner impl class; a spec matching nothing only *warns*, so typos are silent no-ops
- The five-phase externalization pipeline, and the invariant that your model is never left mutated
- Per-call-site UUID graph names — never hard-code symbol names; the runtime cannot deduplicate invocations
- Semantic divergences: ATen SDPA vs module SDPA (lower-right vs upper-left causal masks diverge at every decode step)
- RoPE fp32 requirements, the HF partial-rotary pairing discrepancy, the Gemma3 RMSNorm numerics special case
- `register_torch_lowering`: the callback contract, multi-result nodes, `allow_override`, reserved namespaces, operand helpers
- `generate_composite_decl` and emitting a named composite
- Externalization for memory-efficient weight loading and iOS embedding quantization
- Still unsupported: transposed conv3d; general `conv_transpose` falls back to a zero-filled composite that saves cleanly and produces garbage
- A decision tree: decomp-table tweak vs custom lowering vs custom Metal kernel
- Silent-miscompile catalogue: packed-tensor concat, int64 accumulator narrowing, negative-axis quantize, folded cast round-trips; four open PRs fixing live defects

**Sources.** `repos/coreai-torch.md` · `01-lead-agent-repo-spotchecks.md` · `transcripts/coreai-python-metal.md` · `repos/issues-coreai-stack.md` · `repos/apple-coreai-models.md`

---

#### 28. `coreai-custom-metal-kernels`
**Writing a custom Metal kernel for Core AI with `TorchMetalKernel`**

| | |
|---|---|
| **Pillar** | P8 Core AI — Python conversion |
| **Audience** | Python ML engineer |
| **Evidence** | **Moderate** (API surface documented; the demoed MSL bodies were on screen but never read aloud) |
| **Length** | ~4,000 words |
| **Depends on** | 27 |

**Scope.** The escape hatch when no op and no composite fits: author a Metal kernel in Python paired with a PyTorch reference used only for shape inference, and ship the MSL *inside* the `.aimodel` so the kernel travels with the model. This guide covers the Python-side authoring API; guides 35–36 teach the MSL you write inside it.

**Key sections**
- The pairing model: a PyTorch reference for shape inference plus an MSL body string; what export actually sees
- What Core AI generates for you: signature, buffer bindings, includes
- `MetalParameter` for thread-position attributes
- `result_shapes` required at every call site for dynamic-shape output inference
- `register_custom_kernels` must be called before `add_exported_program`
- Construction-time validation of the reference function's annotations
- `template_dtypes` for one kernel across half/float/bfloat; `helper_src` for typedefs and TensorOps includes
- Tensors inside the body are Metal tensor objects with `get_extent` and multi-index subscripting
- Scalar arguments are baked in as literals; bools widen; per-value PSO sub-caches
- Runtime inputs must be Metal-backed (`StorageKind.METAL`) NDArrays
- Higher-order ops only run on the interpreter compute unit
- Failure mode: a malformed MSL body converts fine and only fails at `load_function`
- Worked examples: a SiLU kernel, and a fused FlashAttention monkey-patched into a HuggingFace attention implementation
- When *not* to do this — prefer a composite op

**Sources.** `transcripts/coreai-python-metal.md` · `repos/coreai-torch.md`

---

### Part 9 — Core AI: compression and numeric formats

#### 29. `coreai-opt-quantization`
**`coreai-opt` quantization: the config hierarchy, specs, GRAPH vs EAGER, and QAT**

| | |
|---|---|
| **Pillar** | P9 Core AI — compression & numerics |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 26 |

**Scope.** The largest and most error-prone API surface in the compression stack, because mis-configuration does not raise — the layer silently disables itself and ships uncompressed, with only a warning in the log. Everything is config-driven with a strict three-level precedence, and the GRAPH/EAGER split is a *correctness* fork rather than a performance knob: Apple states the two are not guaranteed equivalent.

**Key sections**
- Install, and the `coreai-opt` (distribution) vs `coreai_opt` (import) naming split
- The universal compressor lifecycle: init → `prepare` → calibrate or train → `finalize`; you evaluate the *prepared* model
- The three-level config precedence: `module_name` (regex) > `module_type` > global
- **Omitting a field applies defaults; passing `None` disables compression for that scope** — the load-bearing distinction, and how you exclude a sensitive block
- `module_type_configs` keys must be fully-qualified class paths
- The three op-level tensor groups (`op_input_spec`, `op_output_spec`, `op_state_spec`), and how weight-only is expressed
- `QuantizationSpec`: dtype catalogue including fp8 and fp4 with E8M0 MX scales, qscheme, qformulation, granularity, scale dtype
- The presets (`w8`, `w4`, `w4_per_block`) and exactly what they expand to; the MXFP4-weight / FP8-activation recipe
- The four qparams calculators and axis-resolution defaults by module type
- YAML configs with anchors
- **GRAPH vs EAGER**: BN folding, shared observers, fake-quant dedup — and reconciling the talk's advice with the repo's default
- Calibration semantics: observers on, weight fake-quant on, activation fake-quant off; `get_c4` calibration data
- Per-channel activation quantization around channel-altering ops, the concat-pulls-in-transpose hazard, and the shape-aware fallback
- QAT: `QATSchedule`, `step()` cadence, the observer/fake-quant state machine, mutual exclusivity with manual control
- KV-cache quantization: graph-mode and Core AI only
- Silent self-disable on block-size or granularity mismatch — watch the logs
- `ModelInspector` for discovering exact config key strings; the Core ML export restriction matrix and `CoreMLExportError`
- `finalize` destroys dense weights in place; `mmap_dir` for large models

**Sources.** `repos/coreai-optimization.md` · `transcripts/coreai-python-metal.md` · `repos/issues-coreai-stack.md` · `01-lead-agent-repo-spotchecks.md`

---

#### 30. `coreai-opt-palettization-pruning-and-joint`
**Palettization, pruning, casting, joint compression — and the ANE rank-5 ceiling that changes every recipe**

| | |
|---|---|
| **Pillar** | P9 Core AI — compression & numerics |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 29 |

**Scope.** The compression scheme Apple actually ships for iOS, plus the parts of `coreai-opt` that never appeared in a session at all (pruning, casting, joint compression, mixed precision, and compressing an already-converted asset). Contains the single most valuable hardware footgun in the corpus: enabling per-channel scale produces rank-6 LUTs, ANE's max tensor rank is 5, and the runtime silently falls back to the GPU.

**Key sections**
- Palettization vs quantization; effective bits-per-weight including LUT and scale overhead
- `PalettizationSpec`: `n_bits`, granularity, `cluster_dim`, `lut_qspec`, `enable_per_channel_scale`
- Scalar per-tensor, scalar per-grouped-channel, and vector palettization, with the divisibility requirements
- **`enable_per_channel_scale` produces a rank-6 LUT that the ANE rejects** — verbatim from the shipping SAM3 recipe
- `enable_fast_kmeans_mode` (the default) rounds weights before clustering; vector palettization is non-deterministic and only seedable with one worker
- Sensitivity-weighted k-means (SqueezeLLM): gradient hooks, normalization, sensitivity save/load
- `finalize(backend=CoreAI)` frees the original dense weights in place and is not reversible; `mmap_dir` for very large models
- Palettization silently disables itself per layer on incompatibility, with only a warning
- Why iOS defaults to palettization and macOS to linear INT4, and the ANE pre-compiler SIGSEGV that explains it
- Magnitude pruning: unstructured global top-k vs channel-structured L1, and the realized-sparsity rounding trap
- Sparsity schedules: constant vs polynomial decay; n:m structured sparsity
- `cast_to_16_bit_precision` on an `ExportedProgram` — stronger than `.half()`, different from autocast; compress first, cast second
- Joint compression: palettize → finalize → quantize activations → calibrate → finalize; why the LUT must be INT8 to unlock W8A8, and why it is CoreAI-only
- Mixed precision: sensitivity sweep, greedy recipe, per-layer `module_name_configs` with a global `None`; BPW accounting and the accuracy-vs-BPW curve
- `coreai_utils`: `quantize_weights` / `palettize_weights` / `sparsify_weights` on an already-converted `AIProgram`, with no PyTorch involved
- Running a systematic sweep with Apple's `model-compression-exploration` skill protocol; reporting a size/quality frontier instead of a single number

**Sources.** `repos/coreai-optimization.md` · `transcripts/coreai-python-metal.md` · `repos/apple-coreai-models.md` · `repos/issues-coreai-stack.md` · `01-lead-agent-repo-spotchecks.md`

---

#### 31. `numeric-formats-across-the-stack`
**Numeric formats across the stack: int4 to MX, and who supports what**

| | |
|---|---|
| **Pillar** | P9 Core AI — compression & numerics |
| **Audience** | Both |
| **Evidence** | **Strong** |
| **Length** | ~3,500 words |
| **Depends on** | 1 |

**Scope.** A short reference guide that serves at least five others. The same MX microscaling format runs the entire height of the stack — packed FP4 elements with block-32 E8M0 scales in `coreai-opt`, the same element and scale types in `NDArray.ScalarType`, E8M0 scale planes in MSL, and `mxfp4`/`mxfp8` in MLX — and knowing that makes every layer legible at once. Draft this early even though it publishes here.

**Key sections**
- Affine quantization: scale plus zero-point or minval, the formula, and the packed-uint32 layout
- Lookup-table palettization, and how it differs structurally
- What "granularity" means at each layer: per-tensor, per-channel, per-grouped-channel, per-block
- The MX family: E2M1 elements, E8M0 shared exponent, 32-element blocks
- NVFP4 and its E4M3 scale; fp8 E4M3FN vs E5M2
- Sub-byte integers down to 1 bit, and the odd widths that point at fine-grained schemes
- A cross-stack support matrix: `coreai-opt` dtypes ↔ `NDArray.ScalarType` (33 cases) ↔ the TensorOps dtype table ↔ MLX's four modes
- Why 4-bit appears only as the *right* operand in the TensorOps matmul table
- Alignment consequences: 128-byte strides for sub-byte tensors, 64-byte for ML usage
- Why quantization shifts activation distributions past the fp16 threshold
- ANE fp16 overflow thresholds for softplus, mish and logsumexp — and Apple's sanctioned fix (rewrite the PyTorch module, don't patch the converter)
- Reading a bits-per-weight number honestly

**Sources.** `transcripts/coreai-python-metal.md` · `web/apple-docs-coreai.md` · `repos/coreai-optimization.md` · `repos/mlx-core.md` · `repos/issues-coreai-stack.md`

---

### Part 10 — Core AI: authoring for the hardware, debugging, LLM deployment

#### 32. `ane-vs-gpu-authoring-rules`
**Authoring models for the Neural Engine vs the GPU: two opposite rulesets**

| | |
|---|---|
| **Pillar** | P10 Core AI — authoring, debugging, LLM deployment |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~7,500 words |
| **Depends on** | 26, 27 |

**Scope.** The densest source of practical hardware knowledge in the entire corpus — roughly 950 lines of Apple's own empirical rules, shipped as agent skills in `apple/coreai-models` and documented in no video and no doc page. The framing that makes it teachable: almost every ANE rule has a GPU rule that is its exact inverse, so a pattern that is *required* on one target is a pessimization on the other. Includes Apple's PSNR acceptance gates restated as CI thresholds.

**Key sections**
- Why re-authoring exists: op residency, graph segmentation, and cross-accelerator transfer overhead dominating small-model latency
- ANE hard limits: max tensor rank 5; fp16/int8/int16 only, where a bare Python float literal forces fallback
- Fully static shapes — export one function per shape configuration
- The 64-byte width-alignment rule: a singleton last axis costs 32× memory at fp16, 64× at int8
- BC1S layout `(B, C, 1, S)` with exact permute and reshape recipes, standard ↔ BC1S and multi-head GPU ↔ BC1S
- `nn.Conv2d(kernel_size=1)` instead of `nn.Linear`, with the weight-reshape helper
- Transpose bookkeeping at every projection site — "a common source of silent correctness bugs"
- Prefer high-level ops; softmax on the channel dim; convolution strides that factor into 2s and 3s
- Causal masks shaped `(1, key, 1, query)` with `-40000.0`, never `-inf`
- Per-head attention via einsum; KV cache must return **post-RoPE** keys or PSNR collapses to ~20 dB
- fp16 activation overflow thresholds, and that Apple's fix is to rewrite the PyTorch module
- **GPU rules, inverted**: standard layouts, `nn.Linear`, one fused SDPA over all heads, fused QKV and QK-norm, up-before-gate MLP ordering, `mutable_slice_update` stateful KV
- GPU MoE via `SwitchLinear` / `SwitchGLU` / `GatherMM` with stacked expert weights; streaming weight loading for 7B+
- The PSNR acceptance gates: >70 dB re-authored, >70 dB layout, ≥40 dB compiled, ≥35 dB palettized
- The bottom-up authoring order (norm → projections → attention → MLP → block) with per-primitive verification, and the `from_source_model` factory convention
- Architecture discovery by *running* code with forward hooks, not reading it
- About twenty concrete failure signatures from `common_issues.md`; installing and driving the Core AI agent skills

**Sources.** `01-lead-agent-repo-spotchecks.md` · `repos/apple-coreai-models.md` · `transcripts/coreai-python-metal.md` · `repos/issues-coreai-stack.md` · `repos/issues-community-stack.md`

---

#### 33. `coreai-debugging-and-profiling`
**Debugging and profiling Core AI: the debug gauge, Instruments, the Core AI Debugger, sync points and PSNR**

| | |
|---|---|
| **Pillar** | P10 Core AI — authoring, debugging, LLM deployment |
| **Audience** | Both |
| **Evidence** | **Strong** (no hands-on account of the Debugger app exists anywhere in the corpus) |
| **Length** | ~6,500 words |
| **Depends on** | 22, 26 |

**Scope.** All three Core AI tools plus the Python-side reference-run machinery that makes the most valuable one work. The most reusable idea in the corpus is the Debugger's **sync-point** model: automatically paired operations whose outputs should match a PyTorch reference, each scored by a similarity metric, sortable. Apple's own example turned a lost detection into a one-block config change in minutes.

**Key sections**
- The recommended triage order: debug gauge → Instruments → Core AI Debugger
- The Xcode debug gauge: it requires *direct* CoreAI linkage; three event types; exporting captured inputs as `.npy`/`.npz`
- The More menu is unavailable for events recorded before you opened the report
- The Instruments Core AI template: four bundled instruments, four event categories (Specialization, Load, Setup, Inference)
- The gauge shows three categories and Instruments shows four, with disagreeing colours — a real cross-tool confusion
- Frequent Load events as an explicit bug signal; the growing-inference-interval signature that means you need states
- The standalone Core AI Debugger app: navigator grouped by PyTorch module, structure viewer, source viewer, inspector with tensor values
- Running against a chosen hardware target; comparison sessions across target, compute unit, or a reference run
- **Sync points** and the five similarity metrics with metric-aware colouring (PSNR default)
- Producing the reference run: `save_intermediates` → `.aimodelintermediates`; the two preview environment variables required for debug metadata
- The worked diagnosis: a low-PSNR cluster in a 4%-of-params decoder, excluded from quantization by name pattern, baseline quality restored at a fraction of the size
- Apple's PSNR acceptance gates restated as CI thresholds
- The rest of `coreai_torch.debugging` that nobody demos: NaN/Inf bisection validators, cross-framework comparators, graph diff, op-level benchmarking, search strategies
- `Mode.DEBUG` is the default and ships torch stack traces — strip for release
- The four A/B gates every conversion should run

**Sources.** `transcripts/coreai-python-metal.md` · `web/apple-docs-coreai.md` · `repos/coreai-torch.md` · `transcripts/coreai-intro.md` · `repos/issues-coreai-stack.md`

---

#### 34. `coreai-llm-export-end-to-end`
**Exporting an LLM to Core AI: macOS dynamic, iOS static, compression presets, and the model registry**

| | |
|---|---|
| **Pillar** | P10 Core AI — authoring, debugging, LLM deployment |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 26, 25, 30 |

**Scope.** The complete, reproducible recipe from a Hugging Face checkpoint to a loadable bundle, on both platform paths, using Apple's own tooling. Covers the registry and preset system, the two very different graph contracts, the asymmetric compression defaults, the reproducibility hazard (the same command produced a 2.2× slower artifact after an OS upgrade with identical wheels), and the models that simply do not work.

**Key sections**
- The model registry CLI and the preset system; `coreai.llm.export` and its full flag surface
- Deterministic bundle naming, and round-tripping presets into CLI invocations
- **macOS dynamic path**: the exact input/output/state contract, read *positionally* by the engine
- **iOS static path**: four entrypoints, the query-length × cache-length shape grid, the naming scheme
- IOSurface hardware constraints and uint16 `position_ids`; iOS export supports only a subset of model types
- Compression asymmetry: macOS INT4 per-block vs iOS 4-bit palettization with 8-bit embeddings
- Custom YAML compression recipes and their strict schema
- Memory-efficient streaming weight loading vs the legacy full-RAM path
- Assembling the bundle: `metadata.json`, tokenizer files, `function_map`
- Gated Hugging Face models and per-model quirks
- Running it: `llm-runner` flags, `llm-benchmark` methodology, published perplexity and BPW tables
- **Export artifacts are build artifacts, not pure functions of the recipe** — the dequant-fold decision consults the running OS; archive artifacts and record versions
- Hybrid and SSM models fail the stock engine's two-state check
- The multi-model app pattern: two small task-specific models, upgraded independently

**Sources.** `repos/apple-coreai-models.md` · `transcripts/coreai-intro.md` · `transcripts/coreai-python-metal.md` · `repos/issues-coreai-stack.md` · `web/community-blogs.md`

---

### Part 11 — Metal and TensorOps

#### 35. `tensorops-matmul-and-quantized-tensors`
**TensorOps from scratch: `matmul2d`, execution scopes, `MTLTensor`, and MX scale planes**

| | |
|---|---|
| **Pillar** | P11 Metal / TensorOps |
| **Audience** | Metal / kernel author |
| **Evidence** | **Strong** for `matmul2d` (verifiable against shipped SDK headers) · **Moderate** for the 27-era scale-plane spellings |
| **Length** | ~6,000 words |
| **Depends on** | 31 |

**Scope.** The bottom of the stack, where Core AI and MLX both land, grounded in the shipped `MetalPerformancePrimitives` header rather than only the talk. The M5 neural accelerator is a block in each shader core aimed squarely at LLM prefill, and the 2026 headline is a single `MTLTensor` carrying its scales as an additional plane. The scale-plane API does not appear in the Xcode 26.6 SDK and must be published as unverified until re-harvested.

**Key sections**
- Where TensorOps sits; the namespace, include line, and deployment-target feature gate
- The M5 neural accelerator, and what "automatically uses available hardware acceleration" means in practice
- `matmul2d_descriptor`: dimensions, dynamic K, transposes, relaxed precision
- **The default mode is multiply, not multiply_accumulate** — examples assume a pre-zeroed destination
- The three execution scopes; run calls must be scope-uniform; undefined behavior when the dispatched SIMD-group count disagrees; fragment shaders are single-thread only
- Host-side dispatch pairing via thread execution width
- The four descriptor tags (handle, offset, inline, …) and three address spaces
- `slice()` per threadgroup vs bounds-check-free `static_slice<>()` for interior tiles
- `MTLTensorDescriptor`: extents, usage flags, max rank; creating tensors from a device or a buffer
- Alignment rules: first stride of one, 64-byte second stride for ML usage, 128-byte strides for sub-byte dtypes
- The quantized dtype timeline: int4/int8 in 26.4; fp4, fp8 and int2 claimed for 27
- **Scale planes**: plane descriptor, block factors (32×1 ⇒ 32 elements per scale), auxiliary plane map, attachment to the tensor descriptor
- Slicing slices data *and* scale planes together; feeding quantized tensors straight to `matmul2d` and letting TensorOps dequantize
- The supported dtype matrix, and 4-bit types appearing only as the right operand
- A real production call site from MLX's own GEMM kernels, with fragment-layout constants
- An explicit list of what remains unverified pending a newer SDK

**Sources.** `transcripts/coreai-python-metal.md` · `repos/mlx-core.md` · `repos/coreai-optimization.md`

---

#### 36. `tensorops-cooperative-tensors-and-flashattention`
**Cooperative tensors, reductions, and building a fused FlashAttention**

| | |
|---|---|
| **Pillar** | P11 Metal / TensorOps |
| **Audience** | Metal / kernel author |
| **Evidence** | **Moderate–strong** (concepts confirmed; the demoed MSL was on screen but never read aloud, so the kernel is a reconstruction) |
| **Length** | ~5,500 words |
| **Depends on** | 35 |

**Scope.** The advanced half, and the guide almost nobody else will write. A cooperative tensor owns thread-private data distributed across the threads of an execution scope, which is what lets you do softmax, bias and activation in registers instead of round-tripping threadgroup memory. Culminates in a full FlashAttention skeleton and its integration back through `TorchMetalKernel`.

**Key sections**
- What a cooperative tensor owns, and its implementation-defined layout
- The accessor API, and the validity mask that must always be checked
- Full unrolling described as *imperative* for performance
- In-register post-processing as the core motivation; the three-tier dequantization preference order
- `reduce_rows` and `reduce_columns`, and the identity-default footgun when the operation is max or min
- Reduction destination factories so you never guess the shape
- `map_iterator` between differently-shaped cooperative tensors, guarded by `is_iterator_compatible`
- **New in 27**: passing a cooperative tensor directly as a matmul input — and the mandatory `is_compatible_as_left/right_input` check plus threadgroup fallback
- The SDK-versus-talk availability discrepancy worth flagging
- Building FlashAttention: `execution_simdgroup` scope so each SIMD group owns complete rows, slicing Q, the running max/sum loop, in-register softmax, PV
- Wiring the finished kernel into a model via `TorchMetalKernel`
- How this compares to MLX's `mx.fast.metal_kernel` ergonomics

**Sources.** `transcripts/coreai-python-metal.md` · `repos/mlx-core.md`

---

### Part 12 — MLX in Python

#### 37. `mlx-core-fundamentals`
**MLX fundamentals: lazy evaluation, unified memory, streams, `mx.compile`, transforms, and NumPy divergences**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~6,000 words |
| **Depends on** | 1 |

**Scope.** The mental model that makes everything else in MLX legible — and the one that transfers directly to reasoning about Core AI. Also the places MLX deliberately differs from NumPy in ways that produce silent wrongness rather than errors: no bounds checking, slicing copies, nondeterministic duplicate-index assignment, and NumPy views that bypass autodiff.

**Key sections**
- Install matrix: Apple silicon + native Python 3.10+ + macOS 14; CUDA and CPU wheels
- Lazy evaluation: what builds a graph, what forces it, `mx.eval` vs `async_eval`, graph-size guidance and `MLX_BFS_MAX_WIDTH`
- `print(loss)` before `mx.eval` triggers a forward-only partial evaluation
- Unified memory: you place *operations* via `stream=`, never arrays; automatic cross-stream dependency insertion; the measured CPU/GPU split example
- Streams: `new_stream`, thread-local streams, thread affinity, `synchronize`
- `mx.compile`: the simplify and fuse passes; only element-wise and broadcast primitives fuse — never matmuls or reductions
- The four recompilation triggers and the unbounded per-signature cache; `shapeless=True` and what it does not exempt
- Shapeless silently bakes in the first trace's shape for Python arithmetic on `.shape`
- Purity: printing inside a compiled function crashes on placeholder tracers; captured arrays become frozen constants unless declared with `inputs=`/`outputs=`
- The canonical compiled training step, including `mx.random.state` for Dropout; `MLX_DISABLE_COMPILE`
- Transforms: `grad`, `value_and_grad`, `vjp`, `jvp`, `vmap`, `checkpoint`, `mx.custom_function`; a transform of a compiled function is not itself compiled
- Export: `export_function`, the exporter context manager, `import_function`; imported functions always return a tuple and reject mismatched shapes
- Indexing divergences: no bounds checking, slicing copies, nondeterministic duplicate writes, `array.at[idx].add`, `mx.empty` being literally `mx.zeros`
- Interop: buffer protocol vs DLPack, zero-copy asarray with page alignment, PyTorch MPS shared storage — and DLPack not synchronizing pending Metal work
- Writing through a NumPy view bypasses autodiff and silently produces wrong gradients
- `mlx.nn.Module` as a dict subclass; optimizers and schedulers including Muon and MultiOptimizer

**Sources.** `web/mlx-docs-site.md` · `repos/mlx-core.md` · `repos/mlx-examples.md` · `repos/issues-mlx-stack.md`

---

#### 38. `mlx-numerics-hardware-gating-and-kernels`
**MLX on real hardware: TF32, NAX, silent SDPA fallback, allocator limits — and writing your own Metal kernel**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** (almost entirely issue-tracker evidence with measured reproductions) |
| **Length** | ~7,000 words |
| **Depends on** | 37 |

**Scope.** The guide that saves someone a week, plus its natural sequel. MLX's fastest paths are hardware-gated, undocumented, and on by default, so the same code produces different — and occasionally wrong — numbers on M5/A19 than on M2 while every op-level parity test passes. Then: when the fused path doesn't exist, you write the kernel yourself, including the differentiable case that delivered a measured 40× backward-pass speedup.

**Key sections**
- The fused-op signatures and their gotchas: RoPE (exactly one of base or freqs, per-batch offsets), SDPA (GQA without pre-tiling, float32 softmax, lower-right causal alignment, attention sinks)
- **Fused SDPA coverage is narrow and the fallback is silent** — no log, no env var, no predicate; the exact head-dim tables
- Consequences: Gemma 4's d=512 layers and Qwen3VL's d=72 vision tower never fuse; detecting it with a Metal System Trace
- The fused kernel is bypassed entirely during training on Metal
- Unfused prefill transient memory as a formula, and why chunking only bounds it linearly
- `MLX_SDPA_BLOCKS` must be a multiple of 32 or attention corrupts silently
- `MLX_ENABLE_TF32` defaults to 1, is undocumented, is read once at first use, and is inert before GPU generation 17
- Why TF32 affects anything built from GEMMs, including unfused attention; the A19 shape-gated wrong fp32 matmul
- Batch-vs-single logit divergence from two independent mechanisms; what tolerances a test suite can honestly assert
- Memory knobs: memory limit, cache limit, wired limit, `clear_cache`; `get_peak_memory` tracks active only and can undercount by orders of magnitude
- The 499000 *buffer-count* resource limit with no setter, and the two ways to hit it without leaking bytes
- The buffer-cache reuse window, and why growing KV appends miss it forever and poison the pool
- The architecture-suffix taxonomy and per-chip-class command-buffer limits
- **Custom kernels**: `mx.fast.metal_kernel` signature generation, shape/strides injection, `ensure_row_contiguous`'s silent copies, `grid` in threads not threadgroups
- `math_mode`: `safe` is the default and preserves `exp(-inf) == 0`, which masked softmax depends on
- Differentiable kernels: `atomic_outputs` + `init_value` + simdgroup pre-reduction, wired into `mx.custom_function`
- Constructing a kernel builds a new Metal library — hoist it out of hot loops; the CUDA twins; debugging with Metal capture and shader `os_log`

**Sources.** `repos/issues-mlx-stack.md` · `repos/mlx-core.md` · `web/mlx-docs-site.md` · `repos/mlx-examples.md`

---

#### 39. `mlx-quantization`
**Quantization in MLX: affine, MXFP4, MXFP8, NVFP4, quantized activations, and learned quantization**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~5,000 words |
| **Depends on** | 31, 37 |

**Scope.** MLX's quantization is the most readable implementation of these formats anywhere, and it now includes activation quantization and four learned-quantization methods. Useful on its own and as a Rosetta stone for the Core AI side, since the two stacks implement the same MX formats with different ergonomics. Also documents the silent hardware-gated corruption that makes regression testing non-obvious.

**Key sections**
- The four modes with their exact group-size, bit-width and scale-type table; packing layout; why only affine has biases
- `mx.quantize`, `dequantize`, `quantized_matmul`, and their validation errors
- `mx.gather_qmm` for MoE expert dispatch, `sorted_indices`, `segmented_mm`
- `mx.qqmm`: quantizing activations on the fly, and its mode and rank restrictions
- `mx.to_fp8` / `from_fp8`; `nn.quantize` with a `class_predicate` that can return kwargs
- `QuantizedLinear` and `QuantizedEmbedding` are frozen on construction; `QQLinear` flips its stored weight across train/eval to enable QAT
- `mlx_lm.convert` static quantization and mixed-precision quant-predicate recipes
- Ingesting AutoAWQ, GPTQ and compressed-tensors checkpoints natively
- The four learned-quantization CLIs — DWQ, AWQ, GPTQ, dynamic — and the shared calibration corpus
- AWQ supports only seven model types; GPTQ only 2/4/8 bits with a BPW-raising fallback; documented defaults disagree with the code in several places
- `affine` rejects `bits == 7`; `nvfp4` `global_scale` is unsupported on Metal; `mxfp8 qqmm` is not bit-exact
- **Silent MoE corruption on M5/NAX** when gathered rows exceed 32768 and are not a multiple of 64 — exposing recycled memory
- A second defect on `K % 64 != 0` that also hits mxfp4
- Why a regression test must poison the output buffer to detect unwritten rows
- How MLX's formats line up with `coreai-opt`'s MXFP4 spec and Metal's scale planes

**Sources.** `repos/mlx-core.md` · `repos/mlx-lm.md` · `web/mlx-docs-site.md` · `repos/issues-mlx-stack.md`

---

#### 40. `mlx-lm-cli-generation-and-caching`
**mlx-lm end to end: 18 CLIs, the generation API, KV cache types, prompt caching, and speculative decoding**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~8,000 words |
| **Depends on** | 39 |

**Scope.** The tabulated reference for anyone driving MLX from a shell or embedding it in Python, plus the caching machinery that makes the second turn fast. Covers all ten KV cache classes and which are trimmable — trimmability gates speculative decoding *and* prefix reuse, which excludes a whole class of models — and the counter-intuitive result that quantized KV raises prefill memory while lowering decode memory.

**Key sections**
- The 18 console scripts and the dispatcher; the main CLIs with real flags
- `load`, `generate`, `stream_generate`, `generate_step`, and the `GenerationResponse` fields
- `mlx_lm.load` with `lazy=False` as the default, and its memory spike on MoE models
- Sampler application order, and `temp == 0` short-circuiting to argmax and silently disabling top-k, min-p and XTC
- Logits processors and the GPU-resident token ring
- `mlx_lm.convert`: q-mode across affine/mxfp4/nvfp4/mxfp8, quantize-activations, mixed-precision recipes; `convert` refuses to write to an existing path; `save_config` silently strips keys
- The model zoo: 121 architectures, the 2026 per-layer config schema (`layer_types`, `mlp_layer_types`, nested `rope_parameters`)
- **The ten KV cache classes** and which are trimmable
- `QuantizedKVCache` raises peak memory 30–73% during prefill while lowering it during decode; the mechanism and the `prefill_step_size` mitigation
- `--kv-bits` is a capacity lever, not a throughput lever; `RotatingKVCache.to_quantized` raises, so it crashes on sliding-window models — and `hasattr` guards do not catch it
- Disk prompt caching: `cache_prompt`, the safetensors layout, the query-template trick, the model-name check
- Longest-shared-prefix trimming across turns as the TTFT lever
- Speculative decoding: draft → verify → rewind; tokenizer compatibility; acceptance rate; it is **not** bit-identical at temp 0 because exact bf16 logit ties break differently
- Recurrent and SSM models are excluded outright; MTP weights are stripped at load and norm weights shifted, producing slower decode that looks like it worked
- Batch generation and `BatchGenerator` for RL workflows
- Packaging hazards: `rich` and `regex` imported but not declared; `transformers >= 5.13` breaks imports; **CVE-2026-5843** (`config.json` `model_file` executed arbitrary Python on a plain `load()`)

**Sources.** `repos/mlx-lm.md` · `repos/issues-mlx-stack.md` · `web/mlx-docs-site.md` · `repos/mlx-examples.md`

---

#### 41. `mlx-lm-serving-and-distributed`
**Serving with `mlx_lm.server`: continuous batching, local agents, and distributed inference over Thunderbolt RDMA**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer / agent builders |
| **Evidence** | **Strong** |
| **Length** | ~6,000 words |
| **Depends on** | 40 |

**Scope.** Standing up an OpenAI-compatible local endpoint that agents — including Xcode 27's own Intelligence provider and Foundation Models via `ChatCompletionsLanguageModel` — can talk to, and then scaling it past one machine. Includes the production failure taxonomy, notably a livelock in which the GPU stays busy delivering zero tokens, defeating naive health checks.

**Key sections**
- The four-layer local agentic stack; server flags and the full OpenAI-compatible surface
- Continuous batching: how `BatchGenerator` moves sequences between prefill and decode batches, and why it matters for subagent fan-out
- The batchability killers: `--draft-model` disables batching; any request setting `seed` drains the batch
- Server prompt caching: a trie-backed LRU with exact, prefix and rewound hits; category-aware eviction so system-prompt caches survive longest
- Tool calling: ten auto-selected parsers from the chat template, `tool_parser_type`, and the warning-only path when the tokenizer has no tool support
- Reasoning exposed as `message.reasoning`, not OpenAI's `reasoning_content`; cached-token reporting in `usage`
- Pointing agents at it: OpenCode, and **Xcode 27 → Settings → Intelligence → Add Chat Provider → Locally Hosted**
- Pointing Foundation Models at it via `ChatCompletionsLanguageModel` (and its `v1`-path caveat)
- "Not recommended for production": only basic security checks; errors surfacing as HTTP 404
- The failure taxonomy: idle core spin, uncaught-exception hang, and the **livelock** — why delivery staleness is the only valid watchdog
- Why agentic sessions are prefill-dominated, and what the M5 neural accelerators buy (matmul 4× M4)
- Distributed: `mx.distributed.init` is sticky (first successful backend wins all later bare calls); collectives are silent no-ops at group size 1
- The four backends and how to choose; `mlx.launch` flags and hostfiles; `mlx.distributed_config` auto-setup
- **JACCL**: RDMA over Thunderbolt 5, macOS 26.2+, a fully connected mesh, and `rdma_ctl enable` from Recovery — a step that cannot be done remotely; `MLX_METAL_FAST_SYNCH` as critical
- Tensor parallelism (`AllToShardedLinear` + `ShardedToAllLinear` and why the asymmetry composes), data parallel via `average_gradients`, FSDP via `fully_shard`
- The motivating case (a 1.6T model needing >800 GB) and known fragility: spinning receives, socket-thread death wedging all ranks; only rank 0 serves HTTP

**Sources.** `transcripts/evals-mlx.md` · `repos/mlx-lm.md` · `web/mlx-docs-site.md` · `repos/mlx-core.md` · `repos/issues-mlx-stack.md` · `repos/foundation-models-utilities.md`

---

#### 42. `mlx-lm-finetuning-and-porting`
**Fine-tuning on Apple silicon with LoRA/DoRA, and porting a new architecture to mlx-lm**

| | |
|---|---|
| **Pillar** | P12 MLX — Python |
| **Audience** | Python ML engineer |
| **Evidence** | **Strong** |
| **Length** | ~5,500 words |
| **Depends on** | 40 |

**Scope.** The surviving on-device adaptation story, now that Foundation Models custom adapters are discontinued in OS 27 — a framing that should open the guide. Covers the full workflow from dataset to a fused, quantized, shippable model, the traps that waste a training run, and the contract you implement when adding a new model architecture.

**Key sections**
- Why this matters more in 2026: FM custom adapters are gone in OS 27, and Apple names Core ML / Core AI + Background Assets as the migration path
- The `mlx_lm.lora` workflow, YAML config schema, and every flag
- What can take adapters — Linear, QuantizedLinear, SwitchLinear, Embedding — and auto-discovery when `keys` is absent
- LoRA vs QLoRA vs DoRA, and DoRA dequantizing the base weight on every forward pass
- Dataset formats: chat, tools, completions, plain text, HF datasets
- Prompt masking, gradient accumulation, gradient checkpointing (it monkey-patches the class `__call__` — a process-global side effect)
- LR schedules with warmup, five optimizers including Muon and its exclusions, W&B/SwanLab callbacks (and the one that gets silently overwritten)
- Length-sorted padded batching and the rank-strided distributed variant; `average_gradients`; FSDP
- `mlx_lm.fuse`, de-quantizing on fuse, and GGUF export limits
- The standalone `lora` example as the from-scratch counterpart; the WWDC25 knowledge-injection demo as a worked case
- Known blockers: autograd through MoE routing (scatter VJP), and a documented hang at certain rank/module combinations
- **Porting an architecture**: the `ModelArgs` / `Model` / `sanitize` / `make_cache` / `shard` / `quant_predicate` contract
- The shared base, `rope_utils` and `switch_layers` toolkit; test conventions

**Sources.** `repos/mlx-lm.md` · `repos/mlx-examples.md` · `repos/issues-mlx-stack.md` · `forums/forum-pain-points.md`

---

### Part 13 — MLX in Swift

#### 43. `mlx-swift-lm-in-an-app`
**Shipping MLX inside a Swift app: package setup, the 3.x redesign, concurrency, wired memory, and media input**

| | |
|---|---|
| **Pillar** | P13 MLX — Swift |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~6,500 words |
| **Depends on** | 37 |

**Scope.** The Swift deployment path, pinned to the 3.x breaking redesign that decoupled the package from HuggingFace. Leads with the concurrency model, which is the number one source of consumer errors under Swift 6 strict concurrency, then covers the app-side realities: wired memory policies, entitlements, device gating, VLM media input, and the vision-prefill blowup that allocated 33.9 GB.

**Key sections**
- What 3.x changed: `Downloader`, `Tokenizer` and `TokenizerLoader` are now protocols you supply
- The three integration styles: hand-rolled, an integration package, or the in-repo `MLXHuggingFace` macros — and what they expand to
- The `FoundationModelsIntegration` SwiftPM trait
- `swift test` does not work: use `xcodebuild` with `-skipPackagePluginValidation`, and `-skipMacroValidation` for consumers
- `ModelContainer` vs `ModelContext` vs `ModelConfiguration`; `perform`, sending/consuming semantics, `SendableBox`, and `MLXArray` not being `Sendable`
- Running multiple `ChatSession`s in parallel against one set of weights; the async-load idiom; NSCache-backed model switching
- Model loading internals: config decode, type registry, EOS resolution, concurrent tokenizer and weight load; mixed-precision quantized checkpoints
- The wired-memory system: manager, tickets, policies, and measuring weight / KV / workspace bytes
- `Memory.cacheLimit` and `memoryLimit` — the old `GPU.set(cacheLimit:)` is gone and every pre-2026 tutorial breaks; the cache limit is process-wide, so refcount it
- Reading `Memory.memoryLimit` to detect a low-memory device before writing it; the increased-memory-limit entitlement
- MLX requires A13+ and needs float16 forced below that
- VLM media input: PhotosPicker `Transferable` wrappers, EXIF baked into pixels, security-scoped URLs, resize processing
- **Qwen3VL vision prefill allocating 33.9 GB** from a dense joint mask plus an unfused head dim, and the two-part fix
- SwiftUI streaming: isolating per-token updates, scroll anchoring, cancellation, markdown without dependencies
- Porting a model architecture to Swift: config Codables, `ModuleInfo`/`ParameterInfo`, the block skeleton, `sanitize`, tied embeddings, RoPE helpers, MoE `SwitchGLU`, registration; trace-based debugging against Python
- The four-hop fix-propagation chain, and why version pinning matters

**Sources.** `repos/mlx-swift-lm.md` · `repos/mlx-swift-examples.md` · `repos/issues-mlx-stack.md` · `01-lead-agent-repo-spotchecks.md` · `repos/noema-ios.md`

---

#### 44. `mlx-swift-lm-generation-tools-and-cache`
**Generation, streaming, tool calling, reasoning, and KV caching in mlx-swift-lm**

| | |
|---|---|
| **Pillar** | P13 MLX — Swift |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (some internals sampled rather than read end to end) |
| **Length** | ~7,000 words |
| **Depends on** | 43 |

**Scope.** The generation entry points and when each is right, the cancellation rules that matter on iOS, the ten tool-call wire formats with their per-model parsers, and the eight KV cache implementations — including a cluster of value-semantics and trimmability bugs that silently lose context or corrupt attention. This is where reading Swift source is genuinely faster than reading docs.

**Key sections**
- The generation entry points: `generate`, `generateTask`, `generateTokens`, `ChatSession`
- `TokenIterator` (prefill happens in `init`) and the `Generation` event enum
- `GenerateParameters` in full, and temperature defaulting to **0.6**, not 0; sampler ordering matching Python exactly; argPartition-based top-k
- Penalty processors on a GPU-resident token ring
- **Cancellation must be checked before `iterator.next()`** — a post-cancel GPU submission faults when an app backgrounds; breaking out of an `AsyncStream` early leaves GPU work in flight on the same cache
- `ChatSession`'s eight initializers, history vs cache rehydration, `streamResponse` and `streamDetails`
- The default image processing downsizes to 512×512; a trailing empty assistant message breaks the chat template
- Tool calling: `Tool<Input,Output>`, the parameter DSL, `execute(with:)`
- The ten wire formats and `ToolCallFormat.infer`, including its llama vocab-size heuristic
- **Gemma 4 tool calls are never extracted** because of an exact-equality model-type check
- The streaming tool-call state machine, and the ordered vs unordered APIs you must not mix
- Reasoning: `ReasoningConfig`, prompt strategies, delimiter parsing, per-family inference rules; `LMOutput.State` threaded across turns
- The `KVCache` protocol and its eight implementations
- `attentionWithCacheUpdate` performs the update — calling `cache.update` yourself first is a shipped bug that doubles the cache
- A model conforming to `KVCacheDimensionProvider` must populate `kvHeads` per layer or generation traps
- Affine KV quantization vs **TurboQuant** (Walsh-Hadamard rotation, Lloyd-Max codebooks, JIT Metal kernels); why prefill stays fp16; which layers never convert
- `kvScheme` overrides `kvBits`, and an unrecognized scheme string is silently ignored
- **`maybeQuantizeKVCache` takes `inout [KVCache]` and replaces elements, so quantized caches never propagate back and context is silently lost**
- `RotatingKVCache` becomes permanently untrimmable once its window wraps, no-oping speculative rollback and defeating prefix reuse
- Prompt-cache save/load in a Python-compatible safetensors layout; `MLX.compile` freezing the cache write position because `offset` is a Swift `Int`

**Sources.** `repos/mlx-swift-lm.md` · `repos/mlx-swift-examples.md` · `repos/issues-mlx-stack.md`

---

#### 45. `mlx-swift-fm-bridge-and-guided-generation`
**`MLXFoundationModels` and `MLXGuidedGeneration`: backing `LanguageModelSession` with an MLX model**

| | |
|---|---|
| **Pillar** | P13 MLX — Swift |
| **Audience** | Swift app dev / package author |
| **Evidence** | **Strong** |
| **Length** | ~5,000 words |
| **Depends on** | 44, 15 |

**Scope.** The most readable third-party `LanguageModel` conformance in existence — small enough to read end to end — plus the xgrammar-backed mechanism that makes `@Generable` work on a non-Apple model. Also the best case study in SDK-gating discipline, since the target compiles to nothing on the 26 SDK and the package had to survive real API drift across the betas.

**Key sections**
- `MLXLanguageModel(modelID:)` and what you get for free
- Declared capabilities, and how each maps to MLX machinery
- `SchemaConverter` and the tool-calling envelope
- **The schema-serialization bug class**: `GenerationSchema` emits root-anchored `$ref` while the envelope buries `$defs`, so nested `Generable` tool arguments failed grammar compilation
- Rewrite `$ref`s on raw `JSONEncoder` output — a `JSONSerialization` round-trip escapes slashes and the match silently never fires
- `toolCalling` on a VLM-loaded model was a process-killing abort from a 1-D `LMInput`
- Multi-round tool calling, `ToolCallingModeResolution`, and the ordered response/toolCall output enum
- `MLXGuidedGeneration`: xgrammar constraint compilation, composite logit processors, mask snapshots, whitespace and closing-token bias
- The vendored xgrammar with renamed symbols so it cannot collide with Core AI's prebuilt copy — a real packaging lesson
- SDK gating: the target compiles to nothing on the 26 SDK; guard with `canImport(_version: 2)`, because availability annotations alone are insufficient
- FM API drift across the betas: `SamplingMode.Kind` renames, and an `updateUsage` overload in the `.swiftinterface` but absent from the dylib that SIGSEGVs at image load
- Reading this alongside `CoreAILanguageModel` and `ChatCompletionsLanguageModel`

**Sources.** `repos/mlx-swift-lm.md` · `01-lead-agent-repo-spotchecks.md` · `repos/issues-mlx-stack.md` · `repos/apple-coreai-models.md`

---

### Part 14 — Bridges between stacks

#### 46. `coreai-bridges-mlx2coreai-and-swift-lm`
**Third-party paths into Core AI: `mlx2coreai` and `swift-lm`**

| | |
|---|---|
| **Pillar** | P14 Cross-stack bridges |
| **Audience** | Python ML engineer / Swift package author |
| **Evidence** | **Strong** as description · **Thin** on verified end-to-end numerical parity |
| **Length** | ~7,000 words |
| **Depends on** | 26, 25 |

**Scope.** The two independent, non-Apple toolchains that target Core AI from outside. Both are worth studying as tools *and* as documentation: they are the only public descriptions of Core AI's MLIR-level and bundle-level contracts written outside Apple, and `mlx2coreai` reproduces Apple's own macOS stateful-LLM contract byte for byte. Must carry the caveat that op coverage is asset-generation coverage, not runtime numerical parity.

**Key sections**
- `mlx2coreai`: the capture → SSA IR → normalize → lower → save pipeline; callback tracing vs the legacy DOT path
- The emitted contract: one `main` entrypoint with `input_ids`, `position_ids`, and mutable `keyCache`/`valueCache`
- `convert-mlx-lm-stateful` in one command; `position_ids` must carry the full prefix range; batch size 1 only; no sliding-window models
- Weights as MLX constants — inline `ConstantOp`s or dense resources above a threshold, with **no separate weight file**
- Dynamic shapes recovered by a two-capture probe that differences integer attributes
- Composite declarations for `rms_norm`, `rope` and `sdpa` as private no-inline fusable-kernel hints
- Statefulness via IR pseudo-ops and the duck-typed cache shim that makes MLX record a `slice_update`
- The name-remap gotcha that collapses whole op families, and the three silent miscompiles it causes (log2/log10 → natural log; shifts → AND)
- No quantization or palettization support anywhere in the bridge; forced dtype narrowing
- It pins `coreai-core 1.0.0b1`, below the loader floor, so its bundles should be rejected by current betas
- Why a Swift runner ships alongside: incomplete Python runtime bindings
- `swift-lm`: a Swift DSL → LMIR → a versioned JSON executable contract → a generic Python lowerer
- The stateless vs stateful contracts, with states derived purely from the IR graph
- SHA-256 contract pinning inside the bundle, and the hard-fail-never-fallback policy with an operation path
- `CoreAIStateSession`: MTLBuffer-backed persistent states and a hand-rolled async mutex
- The VLM adapter: Apple's three-asset contract and image-placeholder expansion; `expectFrequentReshapes` rejected outright as a reproducible beta failure
- When either is the right tool, and when to go back to `coreai-torch`

**Sources.** `repos/mlx2coreai.md` · `repos/swift-lm.md` · `01-lead-agent-repo-spotchecks.md` · `repos/issues-community-stack.md` · `repos/apple-coreai-models.md`

---

### Part 15 — Shipping and operating on device

#### 47. `shipping-model-distribution-and-updates`
**Shipping and updating model assets: Background Assets, per-architecture variants, first-run flows, and versioning**

| | |
|---|---|
| **Pillar** | P15 Shipping & operating on device |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** |
| **Length** | ~5,500 words |
| **Depends on** | 23 |

**Scope.** Bundling models into your app is usually the wrong answer — two small models added over 1 GB to the download in Apple's own demo, hitting every updater including people who will never use the feature. This is the distribution architecture that avoids that, plus the download engineering that makes it reliable, from a shipping App Store app.

**Key sections**
- The bundling problem, quantified; the first-run/feature-intro opt-in as the place to hide both download and specialization latency
- Background Assets: Apple-hosted managed asset packs, `AssetPackManager`, required Info.plist keys, `ensureLocalAvailability` before you construct anything
- One asset pack per architecture: detect `deviceArchitectureName` and request only the matching variant
- The bundle hand-edit after AOT compile; hosting variants remotely
- A production download engine: dual foreground/background `URLSession` with live task migration
- Tasks created while the app is inactive are discretionary regardless of the flag
- `URLSession` fires cancel **before** completion, so migration must suppress the spurious cancellation error
- Range-header resumes report segment-relative bytes; resume-data resumes report absolute
- `BGContinuedProcessingTask`: fresh UUID per batch, wildcard identifiers, resumable expiration
- Discovering models: HF repo tags, a bundled catalog snapshot, side-loading
- Storage hygiene: sandbox re-homing, verifying bundle integrity, deleting sources while keeping cached specializations, what an OS update invalidates
- **Versioning and pinning**: export artifacts are build artifacts, not pure functions of the recipe — archive them and record versions
- Updating a model in the field without breaking cached specializations or bookmarks
- Custom LoRA adapters are discontinued in OS 27: the 26.x pipeline for anyone still shipping there (`xcrun ba-package foundation-models package`, the `"onDemand": null` → ITMS-91140 manifest bug), and the named migration path

**Sources.** `transcripts/coreai-intro.md` · `web/apple-docs-coreai.md` · `repos/noema-ios.md` · `forums/forum-pain-points.md` · `web/community-blogs.md` · `repos/issues-community-stack.md`

---

#### 48. `on-device-memory-thermals-and-benchmarking`
**Operating within device limits: memory budgets, jetsam, thermal throttling, energy — and honest benchmarking**

| | |
|---|---|
| **Pillar** | P15 Shipping & operating on device |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (measurements are community-sourced and must be attributed) |
| **Length** | ~9,000 words |
| **Depends on** | 22, 43 |

**Scope.** The highest crash-avoidance value in the series, from a shipping six-backend App Store app, plus the measurement discipline that makes any of it reportable. The core insight: on unified memory, allocation headroom alone is **not** a fit test, because mmap-backed weights become resident as inference touches them — a broad logical overcommit will launch and then OOM at long context. The remedy is a two-stage gate, a hysteretic pressure governor, and verified unloads.

**Key sections**
- The two OS-level signals: `os_proc_available_memory()` vs `phys_footprint`; reconstructing the real process limit
- Per-device budget tables, the storage-tier override, and the increased-memory-limit entitlement
- **The two-stage launch gate**: incremental allocation, plus a total working-set ceiling because mmap'd weights become resident
- MoE plus mmap means every expert is resident — active-experts-only accounting is badly wrong
- Exact KV-bytes-per-token math from model metadata; recurrent/SSM state and compute-buffer accounting
- Self-calibrating a transient reserve from measured launch peaks
- A hysteretic four-level pressure governor with recovery factors, and what to do at each level
- Format-aware background unload policy, re-polling while a turn still streams, and **verified** unloads (sample, detach in one transaction, settle, classify the delta)
- MLX specifics: the process-wide cache limit must be refcounted; wired limits
- Core AI specifics: fixed-size KV pre-allocation, unchunked prefill blowups, the iPhone depth jetsam wall; on iPadOS OOM presents as a bare `std::bad_alloc`
- Thermals: measured 600-second unplugged retention across ANE, Core AI and GPU runtimes; clamping threads, disabling warmup and keep-in-memory under serious state
- Energy: `powermetrics`, joules per token — and why the lowest-wattage runtime had the *worst* energy per token
- **Benchmarking methodology**: why one number is always wrong (burst / sustained / energy / quality give four rankings)
- Release vs Debug contamination — one benchmark's own row inflated a lead from 1.4× to 1.6×
- Cold vs warm (71 vs 181 tok/s on the same bundle); state the build per row; interleaved ABBA rounds, fresh process per cell, medians hiding heavy tails
- Page-cache control and the absurd-speedup canary; `mx.eval` inside the timed region or lazy evaluation defers the work
- Disclosing jetsams, failed runs, exact hardware/OS/Xcode versions; a reusable report template
- A device-limits checklist before submission

**Sources.** `repos/noema-ios.md` · `web/community-blogs.md` · `repos/issues-mlx-stack.md` · `repos/mlx-swift-examples.md` · `repos/issues-coreai-stack.md` · `repos/apple-coreai-models.md` · `forums/forum-pain-points.md`

---

### Part 16 — Adjacent capabilities

#### 49. `speech-analyzer-end-to-end`
**The Speech framework end to end: `SpeechAnalyzer`, transcriber selection, asset lifecycle, and custom vocabulary**

| | |
|---|---|
| **Pillar** | P16 Adjacent capabilities |
| **Audience** | Swift app dev |
| **Evidence** | **Strong** (complete Apple docs harvest; no WWDC transcript in corpus) |
| **Length** | ~9,000 words |
| **Depends on** | 2 |

**Scope.** The modern on-device speech-to-text stack, mostly unchanged in 2026 apart from input-plumbing conveniences, but with several sharp, undocumented failure modes that are easy to hit and hard to diagnose. Two halves: the analyzer pipeline and its finish semantics, then transcriber selection, asset lifecycle and accuracy biasing. Must state the negative result: there is **no** new TTS API for the second-generation model, confirmed by Apple on the forums.

**Key sections**
- The two API generations that coexist; the canonical eight-step flow
- `SpeechAnalyzer` as a final actor holding modules, analyzing one input sequence at a time
- New in 2026: `AssetInputSequenceProvider`, `CaptureInputSequenceProvider`, `AnalyzerInputConverter` — replacing hand-installed audio-engine taps
- **The analyzer performs no audio conversion** (to keep CMTime sample-accurate): feed `bestAvailableAudioFormat`, which returns nil until assets are installed
- Structured versus autonomous analysis; `analyzeSequence`, `start`, `finalize`, `cancel`, `finishAndFinalize`
- **Terminating your input stream does not finish the session** — result streams hang open
- The system caps simultaneous analyzers; `insufficientResources`; `ignoresResourceLimits` removes the cap but Apple warns of an unpredictable error; `ModelRetention` tuning
- `SpeechDetector` as a VAD gate: it needs a transcriber, its result stream reports errors not speech events, and it can drop real speech
- Consuming results: volatile vs finalized, the two documented merge strategies, time-range and confidence attributes
- The cancellation-shield subtlety in the display task, or you miss the final update
- `SpeechTranscriber` vs `DictationTranscriber`: different platform matrices, both preset matrices, and how to destructure and modify a preset
- Transcription, reporting and result-attribute options; content hints
- Asset lifecycle: the install request returns nil when already installed; auto-reserved locales; `maximumReservedLocales`; assets are system-managed and shared across apps
- Biasing accuracy: `contextualStrings` vs a real custom language model — the `SFCustomLanguageModelData` DSL, X-SAMPA pronunciations, building the `.bin`, `prepareCustomLanguageModel`
- Custom vocabulary binds only to `DictationTranscriber`; the sample does not run in the Simulator
- **No speech synthesis API exists for the 2026 model** — Apple directs developers to AVFoundation

**Sources.** `web/apple-docs-fm-evals-speech.md` · `00-ORIENTATION-lead-agent.md` · `forums/forum-pain-points.md`

---

#### 50. `dnikit-dataset-and-model-introspection` ⚠
**DNIKit: auditing datasets and networks before you convert**

| | |
|---|---|
| **Pillar** | P16 Adjacent capabilities |
| **Audience** | Python ML engineer |
| **Evidence** | **Moderate** — see caveat |
| **Length** | ~4,000 words |
| **Depends on** | — |

> **⚠ Evidence caveat.** DNIKit is effectively dormant: last release 2023, one commit since, and the published PyPI build is broken under Keras 3. The 2026 fix exists only on `main`, `main`'s own test suite reportedly fails from dependency drift, and nothing in the corpus was executed. Write this as an *evaluate-whether-to-use-this* assessment, status first, not as a tutorial — and consider deferring until someone runs it.

**Scope.** The only thing in the corpus that addresses dataset quality and pre-deployment model analysis rather than deployment: find near-duplicates, rare and mislabeled samples, dead units and compressible layers *before* you spend a week on a Core AI export. Its architecture and algorithms are the durable value; its packaging is not.

**Key sections**
- Status and compatibility first: dormancy, the broken published build, what still works
- The `Producer` → `PipelineStage` → `Introspector` model, and its strict lazy evaluation
- `Batch`: fields, snapshots, metadata; the three standard keys; frozen arrays; `Batch.Builder`
- `peek_first_batch` as the pipeline debugger — nothing runs until `introspect()`
- The canonical pipeline: data → pooled responses → cache
- Familiarity: GMM density over PCA-reduced embeddings, the two-phase fit-then-score pattern, rare/mislabeled data and distribution gaps
- Duplicates: approximate nearest neighbours plus transitive closure, and the two threshold strategies
- IUA for dead units — and that it wants un-pooled responses, unlike everything else
- PFA for network compression: covariance eigen-spectrum, the KL/Energy/Size strategies, unit selection, published compression results — and that it emits a *recipe* you must retrain from
- `DatasetReport` and its Symphony-compatible DataFrame column contract; the canonical PCA-then-UMAP recipe
- Memory reality: only IncrementalPCA streams; Familiarity and Duplicates load everything into RAM
- Backends: TF1/TF2 complete, PyTorch data-only, no Core ML / Core AI / MLX backend
- **The escape hatch**: a custom `Producer` yielding precomputed activations — exactly how you would introspect an MLX or Core AI model
- How this feeds the compression guides (which layers tolerate compression) and where it sits relative to Evaluations

**Sources.** `repos/dnikit.md`

---

## 5. Recommendation

### 5.1 The must-write core (12)

These are load-bearing: the most readers need them, the most other guides depend on them, and they prevent the most expensive mistakes. All twelve appear in at least two of the three independent proposals' core lists.

| # | Guide | Why it is core |
|---|---|---|
| 1 | `apple-ai-stack-2026-map` | Nothing else is safe to read first. The backend-selection question changed shape entirely in 2026. |
| 2 | `platform-and-version-gating` | Every API in the corpus is gated on some combination of OS / SDK / Xcode / package / hardware, and version confusion is the largest source of phantom bug reports. |
| 3 | `fm-sessions-and-prompting` | The instructions-vs-prompts split is the framework's security model, not an ergonomic detail. |
| 4 | `fm-guided-generation-and-streaming` | `@Generable` is the framework's differentiator, and the confirmed-broken `.anyOf` guide must be documented before anyone ships on it. |
| 5 | `fm-tools-and-tool-calling` | Prerequisite for Spotlight, agentics, evaluations, and every provider guide — and `.required` is an unbounded loop. |
| 6 | `fm-availability-errors-and-guardrails` | The single largest and longest-running pain cluster in the forums; blocks more readers than any API gap. |
| 7 | `fm-context-window-and-kv-cache` | The most consequential design area in the framework, and the model that explains four other guides. |
| 8 | `fm-dynamic-profiles-and-session-state` | The flagship 2026 API, and the one most likely to be written up wrong (the protocol is nested). |
| 9 | `coreai-runtime-and-ndarray` | Every Core AI guide assumes this object model, and the Swift-ownership surface is unreadable without a primer. |
| 10 | `coreai-specialization-caching-and-aot` | The #1 source of first-launch stalls, wedged loads and disk bloat — and on iOS, AOT is mandatory with a maximally misleading failure. |
| 11 | `coreai-torch-conversion-and-io-contract` | The spine of Parts 8–10. Skip the decomposition step and nothing converts; skip `optimize()` and stateful models break silently. |
| 12 | `on-device-memory-thermals-and-benchmarking` | The difference between a demo and a shipping app, and the highest crash-avoidance value in the series. |

**Nearly core** (write next if the budget allows 20): `fm-private-cloud-compute`, `byo-model-behind-languagemodelsession`, `authoring-a-languagemodel-provider`, `coreai-states-and-pipelined-execution`, `ane-vs-gpu-authoring-rules`, `coreai-opt-quantization`, `evals-foundations-and-hill-climbing`, `mlx-core-fundamentals`.

### 5.2 Suggested phasing

**Wave 1 — "I can ship something" (guides 1–8, 17)**
The must-write FM core plus orientation and the Instruments guide. A reader finishing wave 1 has a working, gated, debuggable Foundation Models feature. Deliberately front-loads failure handling *before* advanced features, because availability and guardrails block more readers than any missing API.

**Wave 2 — "It works at scale" (9–12, 19–21)**
Context and KV economics, Dynamic Profiles, Skills, orchestration — then the whole Evaluations set. Pair guide 9 with guide 10; they are the same subject from two directions. Evaluations lands here, not later, because Apple's answer to OS-update model drift is "have an eval suite," and readers need it *before* v1 ships.

**Wave 3 — "Beyond the built-in model" (13–16, 18)**
PCC first, because its eligibility policy gates a large fraction of readers out entirely and the fallback is a different architecture. Then the consumer-side BYO guide, the two provider-authoring guides, and the non-Swift access paths. Hold guide 18 until someone has run `fm` on macOS 27.

**Wave 4 — Core AI, end to end (22–34, plus 31 drafted early)**
Strictly sequential, because the corpus is. Runtime → specialization/AOT → states → engines; then conversion → coverage/composites → kernels; then compression; then ANE/GPU authoring, debugging and LLM export. Put states (24) and ANE/GPU authoring (32) *early* relative to their part, because they determine whether the rest of the pipeline is worth running, and put debugging (33) immediately after the first compression guide, since that is exactly when quality regresses. Draft `numeric-formats-across-the-stack` (31) first inside this wave — five other guides cite it.

**Wave 5 — MLX, Metal, bridges, shipping, adjacent (35–50)**
Can run largely in parallel with wave 4; it is a different reader. Order MLX Python-first, then the Swift app path, then bridges. The Metal guides (35–36) should follow guide 28 so `TorchMetalKernel` is already established. Shipping (47–48) closes the loop back to wave 1. Speech (49) is fully independent — schedule by demand. Defer DNIKit (50) until someone runs it.

### 5.3 Cross-cutting editorial rules

Adopt these **before** guide #1 is written; retrofitting is expensive.

1. **A visible verified/unverified convention.** A large fraction of this corpus is beta-era, and many API spellings are reconstructions from spoken WWDC narration rather than anything seen in writing. Every guide must mark reconstructed signatures inline.
2. **Version floor in the first 200 words**, and every API marked with its earliest OS (26.0 / 26.4 / 27.0). The corpus shows constant confusion here.
3. **A "silent failure" callout box in every guide.** The defining property of this stack is that most defects do not throw.
4. **Attribute every measurement**: Apple / community / our own, plus hardware, OS, Xcode, build configuration and date. Never present a community benchmark as Apple-official.
5. **A short "known-bad claims" reference** carried near guide 1, so downstream readers and coding agents do not reintroduce `.coreaimodel`, `.aiasset`, a `coreai-torch convert` CLI, "iOS 20 / macOS 17", or the invented on-device LoRA training API. Two of roughly fourteen community sources in the corpus are demonstrably fabricated and a third uses the wrong asset extension.
6. **Prefer forum-verified Apple-staff answers over transcript paraphrase where they conflict.** Several transcript claims are already superseded — custom adapters, PCC eligibility, the model-tier split.

---

## 6. Where our evidence is thin

Honest accounting. Items marked **BLOCKING** should stop a guide from publishing until resolved.

### 6.1 Blocking — need a live machine

| Gap | Affects | What is needed |
|---|---|---|
| **The `fm` CLI's actual flags.** Only semantic option names were spoken ("the model option"). `fm schema object`'s grammar, the full subcommand list, slash commands beyond `/model` and `/save`, and everything about `fm serve` are unknown. | 18 | A macOS 27 machine, `fm --help` on every subcommand. |
| **`coreai-build`'s full CLI surface.** Four flags are attested; `--architecture h18p` comes from a community source; no published enumeration of architecture codes or `--preferred-compute` values; unknown whether subcommands beyond `compile` and `inspect` exist. | 23, 34, 47 | macOS 27 + the Metal Toolchain. |
| **Xcode 27 Instruments lane names.** Only 2 of the Foundation Models template's 6 lanes are named anywhere in the corpus; the Core AI template's lane and metric names come from prose, not screenshots. **Do not fabricate the others.** | 17, 33 | Someone with Xcode 27 to enumerate them. |
| **Core AI error types.** No inference, specialization or cache error type appears in the 312 indexed Core AI symbols; `AssetError` covers asset operations only. What `AIModel.init`, `loadFunction`, `run`, `encode` and cache deletion actually throw is unknown. | 22, 23 | Device testing, or a newer SDK. |
| **`AIModelCache` deletion semantics contradict themselves** in Apple's own docs — the reference page says deleting a referenced entry throws; the caching article says deletion is deferred. | 23 | A device test. |
| **The `MTLTensor` scale-plane API is entirely unverified.** The plane descriptor type, `blockFactors`, the auxiliary plane map and the E8M0 tensor data-type case do not appear in the Xcode 26.6 SDK. Likewise the 27-era TensorOps element type names and `map_iterator`'s real argument. | 35, 36 | Re-harvest against an Xcode 27 SDK. |
| **The Core AI Debugger has no hands-on account anywhere** — all community coverage restates the docs. The full similarity-metric list beyond PSNR and the target list in scheme settings are unknown. | 33 | Run the app. |
| **Several Core AI beta defects have unknown current status** and must be re-tested: the `AIProgram.optimize()` silent miscompile (~17 dB PSNR loss); the linear-INT4 ANE pre-compile SIGSEGV; the Gemma-4 MPSGraph 208 KB decode scratch-heap overflow; the >16-token prefill nondeterminism Apple could not reproduce; the iOS KV-state-shape ≥2048 output corruption on iPhone 17 Pro. | 23, 27, 30, 33 | A 27-beta device, current wheels. |
| **Whether the macOS 26→27 export-lowering regression was fixed.** Same command, identical wheels, 2.2× slower artifact, because the dequant-fold decision consults the running OS. Forensics dated 2026-06-11; it is now late July. This single fact changes advice in three guides. | 23, 34, 47 | Re-run the export on current betas. |
| **Whether hybrid/SSM support has landed.** Apple's pipelined engine validates exactly two states, so Qwen3.5 GatedDeltaNet, LFM2.5 and Granite 4 Mamba2 bundles fail at load. A community fork patches this; upstream status unverified. | 25, 34 | Check `apple/coreai-models` HEAD. |

### 6.2 Unresolved facts — verify before asserting either way

- **Is the core FoundationModels framework actually open source yet?** Session 241 announced it and claimed it runs "everywhere Swift runs, including Linux servers," but a search across `apple/*` and `swiftlang/*` on 2026-07-27 found only `foundation-models-utilities`, `python-apple-fm-sdk` and `coreai-models`. The Linux claim currently rests on the utilities package README. **Do not assert either way.**
- **The Python SDK's iOS 27 parity.** The public repo is at the 26 generation while WWDC26 presented it as new-this-year. This decides whether guide 18 is worth its length.
- **PCC image input.** Session 319 describes feeding a markdown file's "text and images" into a PCC-backed session, but no doc corroborates it, and nothing addresses separate image quota, cost or size limits.
- **The PCC Small Business Program condition** rests on secondary sources plus the developer-site guide, not a transcript quote. One more direct confirmation from Apple's entitlement application page is recommended before publishing eligibility advice.
- **`SpecializationOptions.expectFrequentReshapes`** has no discussion text, no documented default and no initializer that sets it — yet Apple's own code sets it true for dynamic-shape GPU LLMs, and `swift-lm` rejects it outright as a reproducible beta failure. All behavior is inferred.
- **`coreai-core`'s Python API** is known only from third-party call sites. `AIProgram._from_mlir_module` is private; `optimize()`'s parameters and synchrony, the full pass catalog, the exact `.aimodel` on-disk layout, and whether the Python runtime mutates state NDArrays in place are all unconfirmed.
- **Sub-byte scalar access from Swift.** `NDArray.ScalarType` exposes int2–int7 and uint1–uint7, but there is no matching `BitwiseCopyable` Swift type and no documented vended type, so palettized data can only be read through `RawView`.
- **Evaluations API spellings.** The framework docs exist and are substantial (a 44 KB index, ~30 symbol pages, 12+ articles harvested) — the earlier "documentation desert" read was wrong. But several names remain unreconciled: `ScoringMode`'s cases, the exact `.evaluates` trait signature, `aggregateMetrics(using:)`'s argument, whether `if/else` works in an `evaluators` block (only `buildOptional` is listed), and `ScoreDimension`'s initializer shape.
- **MLX → Core AI numerical parity.** `mlx2coreai`'s own docs say its op coverage is "asset generation coverage, not runtime numerical parity," and nothing in the corpus verifies a converted MLX model end to end on device.
- **`OCRTool` and `BarcodeReaderTool` declarations** were never harvested; guide 6 describes them only from the Foundation-Models side. Argument schemas and output types are unverified.

### 6.3 Known negatives — state them, do not invent coverage

- **Speech synthesis / expressive TTS does not exist as an API.** The WWDC26 keynote advertised improved speech generation on the second-generation on-device model; Apple explicitly confirmed on the forums (thread 834149) that no new API shipped and directed developers to AVFoundation. Guide 49 must state this.
- **Custom LoRA adapters are discontinued in OS 27** — two independent Apple-staff statements. The Adapter Training Toolkit stops at 26.0.0. All adapter material (`.fmadapter`, `SystemLanguageModel.Adapter`, `xcrun ba-package foundation-models`) is now historical; the named migration path (Core ML/Core AI + Background Assets) is documented end to end nowhere.
- **Core AI ships with zero Apple sample code** — 0 sampleCode entries across all 312 indexed symbols, and `/documentation/updates/coreai` 404s. Every Core AI runtime guide rests on doc prose plus third-party code.
- **There is no model version pinning API**, which is why Evaluations is positioned as the regression gate.

### 6.4 Deliberately deferred — real, but out of corpus

- **App Intents, App Schemas, and Siri AI on-screen awareness.** This is a genuine and large forum cluster (8 threads, one with 14 replies and ~1k views): custom `AppEntity` types are discoverable by Siri but only actionable through whitelisted schema domains; on-screen handoff works only via `@AppEntity(schema: .files.file)` + `FileEntityIdentifier` + `FileRepresentation`; raw internal errors leak to end users. **But the relevant WWDC sessions (240, 343, 345) are not in our transcript corpus**, and Apple staff routinely deflect these questions out of the Foundation Models forum. Recommend a separate research pass before committing a guide.
- **Apple's sample-code projects were never read**: Origami (dynamic profiles), Book Tracker (Evaluations, 31 KB), the generative-game-content sample, and the advanced speech-to-text sample. These are the richest end-to-end examples in existence and would materially improve guides 10, 12, 19–21 and 49. **Highest-value cheap win available.**
- **Two WWDC sessions referenced but absent**: "Explore distributed inference and training with MLX" and the M5 machine-learning talk. Guides 41 and 35 lean on repo evidence in their place.
- **Four open `coreai-torch` PRs fix live silent-miscompile bugs** (stable fp16 softplus/mish/logsumexp, integer true-divide promotion, intx cat dim, int64 accumulator narrowing) and were unmerged as of 2026-07-27. Treat all four as live defects on 0.4.1 until confirmed merged.
