# Orientation notes — lead agent's own reading

**Written by:** lead agent (not a subagent), 2026-07-27
**Purpose:** independent grounding, read *before* subagent results arrived, so the final topic
proposal is not solely dependent on delegated summaries. Everything here comes from files I read
directly in-session.

**Sources I personally read end-to-end:**
- All 6 files in `docs/` (Apple developer docs, extracted via sosumi.ai)
- `transcripts/wwdc2026-{232,241,242,243,246,298,299,319,324,325,326,330,334,335}.txt` (14 of 16)
- Not personally read (delegated): `meet-with-apple-205.txt` (1013-line FM code-along)

---

## 0. Timeline / version decoder ring

This corpus describes **WWDC 2026**, shipping in **iOS 27 / iPadOS 27 / macOS 27 / watchOS 27 /
visionOS 27 / tvOS 27**, with **Xcode 27**. Session 241 literally says "Our 2027 release".

Prior art referenced: WWDC24 = Apple Intelligence announced. WWDC25 = Foundation Models framework
v1 (iOS 26), SpeechAnalyzer (iOS 26). **iOS 26.4** is called out as a mid-cycle release that added
context-size inspection + token-counting APIs and reduced guardrail false positives.

⚠️ This postdates my training data. **Nothing in the guides may be written from memory.**

---

## 1. The stack, as of WWDC26

Four largely-independent product lines that now interlock through one protocol:

```
┌────────────────────────────────────────────────────────────────────┐
│  Foundation Models framework (Swift, now OPEN SOURCE)              │
│  LanguageModelSession ── backed by any `LanguageModel` conformer   │
│    ├─ SystemLanguageModel            (on-device, rebuilt, 4k ctx)  │
│    ├─ PrivateCloudComputeLanguageModel (server, 32k ctx, reasoning)│
│    ├─ CoreAILanguageModel            (your own .aimodel, ANE/GPU)  │
│    ├─ MLXLanguageModel               (mlx-community HF models)     │
│    └─ 3rd-party pkgs (Anthropic, Google, ChatCompletions, …)       │
├────────────────────────────────────────────────────────────────────┤
│  Core AI  — the inference framework powering Apple Intelligence    │
│  Swift runtime: AIModel / InferenceFunction / NDArray / caches     │
│  Python: coreai-torch (convert), coreai-opt (compress)             │
│  Tools: Xcode model viewer, coreai-build (AOT), Core AI Debugger,  │
│         Core AI Instrument + debug gauge                           │
├────────────────────────────────────────────────────────────────────┤
│  MLX — open-source array framework for Apple silicon               │
│  mlx / mlx-lm / mlx-swift-lm / examples; OpenAI-compatible server  │
├────────────────────────────────────────────────────────────────────┤
│  Metal Performance Primitives + TensorOps (MSL) — custom kernels   │
└────────────────────────────────────────────────────────────────────┘
        Evaluations framework (Xcode 27) cuts across all of the above
```

**Key structural insight for the guides:** Core AI and MLX are *not* competitors to Foundation
Models any more — they are now **backends** for it. `CoreAILanguageModel` and `MLXLanguageModel`
are open-source `LanguageModel` conformers. That reframes the whole "which framework do I pick"
question and should be an early guide.

---

## 2. Foundation Models framework — what's new in the 2026 release

### 2.1 Open source
- The **core framework** is going open source. Explicitly pitched as "a great solution for
  interacting with LLMs everywhere Swift runs, **including Linux servers**" (241).
- New package: **Foundation Models framework utilities** — updated *between OS releases*,
  houses "emerging and experimental building blocks". Contains, per 241 + 242:
  - profile modifiers for transcript management
  - a **Skills** type (procedural knowledge loading)
  - a `LanguageModel` that speaks the **Chat Completions** standard

### 2.2 New on-device model
- "Rebuilt from the ground up": better logic, better instruction following, better tool calling.
- **Vision / image input.** `ImageAttachment`-style insertion into prompt builders. Accepts
  `UIImage`, `NSImage`, `CGImage`, Core Image types, `CVPixelBuffer`, file URLs.
  Any size / aspect ratio — no crop/pad needed. **Larger images = more tokens + more latency.**
- Context: **4k** (vs PCC's 32k) — stated in 319.
- iOS 26.4 added APIs for context size + token counting; 241 says "use these going forward".

### 2.3 PrivateCloudComputeLanguageModel
- Same model that powers many Apple Intelligence features. **32,000 token** context.
- **Reasoning**, with three levels: `light`, `moderate`, `deep`. Set via the new
  **`contextOptions`** argument on respond (or a `reasoningLevel` profile modifier).
- Reasoning output lands in a **separate segment of the transcript** — observable for progress UI.
  It consumes tokens and **counts against the context limit**.
- No API keys, no auth, no account setup — rides the OS + iCloud. **No token cost to developer.**
- Per-user **daily quota**, tied to the user's iCloud account; iCloud+ raises it.
- Gated: **apps with < 2M first-time downloads**; requires an **entitlement**, apply on the
  developer website.
- Requires internet; on-device works offline. Both require Apple Intelligence–capable device.
- **Brings Foundation Models to watchOS 27** (because inference is remote).
- `quotaUsage` on the model, with `isLimitReached` and a "nearing limit" state.
  UX guidance: do **not** use an alert; persist the state in-place, disable the button, show a
  subtle label with an actionable "manage limit" button.
- **Xcode debug option:** Scheme > Run > Options > *Simulate Apple Foundation Models Availability*
  → `Quota Usage Limit Reached` / `Nearing Usage Limit`. Great testability story.
- `contextSize` property now available on both `SystemLanguageModel` and
  `PrivateCloudComputeLanguageModel`.

### 2.4 The `LanguageModel` protocol (session 339 — the whole session is about this)
The single most architecturally important addition. Two types:

- **`LanguageModel`** — describes the model: declares **capabilities**, and vends a
  **`Configuration`**.
- **`LanguageModelExecutor`** — does the work: `init(configuration:)`, `prewarm()`, `respond(...)`.

Mechanics worth a guide on their own:
- Each session holds an **executor store**. `Configuration` is `Hashable` and is the **lookup key**
  — *not* the model. Same configuration ⇒ same executor instance ⇒ reused KV cache / connection.
  Different configuration ⇒ new executor.
- Session dealloc ⇒ store released ⇒ executor `deinit` ⇒ weights freed. No manual teardown.
- `prewarm()` is **not guaranteed to run**; design so weights load exactly once either way.
- Executor receives the **full transcript on every `respond` call**. It must diff against what it
  saw last time: appended-only ⇒ preserve state; removed/modified ⇒ **invalidate back to the
  divergence point**. This is where stateful/KV-cache integrations live.
- **Six transcript entry types**: instructions, prompt, response, tool call, tool output,
  reasoning. Your executor maps them onto your model's roles (commonly system/user/assistant).
- Request carries **`ContextOptions`** (what goes in the prompt: reasoning level, response schema)
  and **`GenerationOptions`** (decoder loop: sampling, temperature, max response length).
  Good clean split — worth teaching explicitly.
- Response is **always streaming internally**; the one-shot API just collects deltas.
- Prescribed **event ordering**: (1) metadata update (model + request IDs), (2) usage update
  (prompt token counts), then (3) text deltas as they arrive.
- **`LanguageModelError`** built-ins: context window overflow, rate limits, refusals, more.
  Guidance: prefer built-ins; define custom errors only for service-specific failures.
- Extensibility: **response metadata** (dictionary; e.g. `tokensPerSecond`, `timeToFirstToken`),
  and **custom segments** (must be `PromptRepresentable`; segment ID controls
  add-vs-update-while-streaming) — the escape hatch for new modalities (audio, video).
- **Server-side tools** pattern, three disclosure levels: (a) run privately, stream only the
  answer; (b) attach metadata such as citations to text deltas; (c) surface the tool's structured
  output as custom segments.
- Auth guidance for package authors: **do not take an API key as a String in your initializer** —
  offer a token provider or sign-in flow; persist with Keychain; look at **App Attest** for device
  attestation.

### 2.5 Dynamic profiles (session 242 — the agentic primitive)
- `DynamicProfile` protocol with a `body` returning a `Profile`. A `Profile` = **instructions +
  tools + modifiers** (model, temperature, samplingMode, reasoningLevel, …).
- New `LanguageModelSession` initializer takes a `DynamicProfile`.
- **The body is re-evaluated before every prompt.** A DynamicProfile resolves to exactly *one*
  active Profile at a time; you use plain Swift conditionals to choose.
- **`DynamicInstructions`** — reusable, **composable** bundle of instructions + tools. Nesting
  concatenates.
- **`historyTransform`** — local, non-mutating transform of the transcript history applied *before*
  prompting. Lossless w.r.t. the real transcript; scoped to the profile.
- **Lifecycle modifiers** — e.g. `onResponse` — run imperative code at session boundaries.
- **Session properties** — `@SessionPropertyEntry` macro in an extension on `SessionPropertyValues`.
  All mutable, all need an initial value, readable/writable from any Tool or Profile.
  Built-in `history` property is **lossy and global to the session**; prefer `historyTransform` for
  lossless, profile-scoped edits.
- **Custom modifiers**: conform to `DynamicProfileModifier`, expose via an extension on
  `DynamicProfile`.
- **Orchestration patterns, named by Apple:**
  - **baton-pass** — shared transcript, a mode variable, a tool that flips it. Receiving profile
    produces the final answer.
  - **phone-a-friend** — tool spawns a short-lived child session with an *isolated* transcript;
    result returns as tool output; parent always answers.
- **Tool calling mode**: `.allowed` (default, existing behavior) / `.disallowed` / `.required`.
  ⚠️ `.required` puts the model in a **while loop — you must provide an exit condition.** Two
  suggested exits: conditionalize the mode on a variable, or give it a "final answer" tool that
  **throws** (throwing aborts the loop and returns control).
- **`transcriptErrorHandlingPolicy`**: `.revertTranscript` (default) / `.preserveTranscript`.
  With `.preserveTranscript` you own putting the transcript back into a good state.
- **`session.transcript` is now mutable** — but only when `isResponding == false`. Mutating during
  a response is a **programmer error**.
- **KV cache warning (important, gets its own guide):** appending preserves the cache and minimizes
  TTFT. Removing entries, changing attached tools, or updating instructions typically **invalidates
  the cache**. Last year the API was deliberately append-only; "this year we're taking the training
  wheels off." Different models have different caching behavior — **measure**.
- **Accuracy warning:** rewriting history can confuse the model (e.g. it saw itself do the task
  without a tool, so it repeats that behavior after you add the tool). Use Evaluations to quantify
  context-engineering changes.

### 2.6 System tools (new, built-in)
- **`BarcodeReaderTool`** and **`OCRTool`** — Vision-framework backed.
- **`SpotlightSearchTool`** — fully local RAG over Core Spotlight. iOS/iPadOS/macOS/visionOS.
  Session 246 is a deep dive; it is *far* richer than a one-liner:
  - configure with e.g. a `FileSource` to search app-sandbox file paths
  - **index delegate gains `searchableItems(forIdentifiers:)`** to recover the full
    `CSSearchableItem` — necessary because some Spotlight metadata (text content, HTML) is stored
    in a compact searchable-but-not-readable representation the LLM can't read
  - results available on the tool itself as an **async sequence of search replies in batches**,
    each with a **`queryToken`** — needed because the model may call the tool multiple times per
    response; use the token to decide when to refresh UI
  - **`GuidanceProfile`** — scope which search capabilities (people, dates, …) and which metadata
    attributes the model is guided on. Explicitly: on-device models have restricted context, so
    use focused guidance
  - **contact resolver** for reference resolution ("who is 'they'?")
  - **custom pipeline stages** — `Generable` types the model generates on demand; combine index
    queries + computation (count, group-by-month, average) server-side for efficiency; app can
    register its own (e.g. a "happiness score" stage running sentiment analysis over notes)
  - pipeline-stage output can come back as a **partial result with an LLM-generated label**

### 2.7 `fm` CLI + Python SDK (session 334)
- **`fm` ships preinstalled with macOS 27.** Subcommands seen: `fm respond`, `fm chat`,
  `fm schema object`, plus `--help`. Options include `--model` (switch to PCC), `--image`,
  `--schema`. `fm chat` has slash commands: `/model`, `/save`.
- Designed for shell scripting; the demo pipes structured JSON out of `fm respond --schema` and
  drives file moves with it.
- **Foundation Models SDK for Python** — requires **Python ≥ 3.10, Xcode installed, Apple silicon
  Mac**. pip-installable. Mirrors the Swift API: `LanguageModelSession`, `session.respond`,
  tool calling, streaming, image input, and **`@fm.generable`** decorator + `generating=` argument
  for guided generation.
- Pitched use case: **evaluation pipelines in Python** — pandas + matplotlib + a third-party judge
  model. The demo compares three prompt variants and charts error rate / excess items / missed
  items / hallucinated items.

### 2.8 Debugging: the Foundation Models Instrument (session 243)
- Xcode 27, Instruments **"Foundation Models" template**. Works with **any** model used through
  the framework, not just Apple's.
- ⚠️ **Captures prompt and response data.** Logging is off in production but **on for the duration
  of the trace** — "keep your trace files somewhere safe". There's a "Record Anyway" confirmation.
- **6 lanes.** Named ones: **Instructions** (how long a given instruction+tool set was active) and
  **Model Inference** (yellow = input/prompt processing, orange = response generation).
- **Tree detail view** hierarchy: sessions → requests → model inferences → instructions / prompts /
  responses. Inspector shows summary + duration visualizations + token usage metrics.
- **Info column** flags errors, long durations, large token counts.
- Three headline metrics taught: **Time to First Token** (fix: shorten the prompt),
  **Tokens per Second** (benchmark/regression detection), **Total Latency** (fix perceived latency
  with streaming).
- The worked bug is instructive: a tool referenced in the instructions text but **not listed in the
  toolset** ⇒ model loops forever, **silent failure, no error thrown**. Instruments is how you see
  it. This is a great "debugging" guide opener.
- Also called out in 242 as the way to **detect KV cache invalidations**.

---

## 3. Core AI

### 3.1 Positioning (324)
- "The **inference framework powering on-device Apple Intelligence**", now public.
- "Next evolution of on-device AI execution." Built for modern workloads. CPU + GPU + ANE.
- Scale claims: speaker diarization → VLM Q&A → **70B-parameter agentic assistant**, all local.
- Core ML is *not* dead: docs say if you use "model types other than neural networks, such as
  decision trees or tabular feature engineering, see Core ML."
- Swift API uses **non-escapable types** for memory safety without perf cost — this is a real
  Swift-language teaching moment (`NDArray.View` / `NDArray.MutableView`).

### 3.2 Runtime types (docs + 324)
- **`AIModel`** — `init(contentsOf:options:)` (async — specialization must finish first),
  `init(resolvingBookmark:)`, `functionNames`, `loadFunction(named:)` (throws on failure, returns
  `nil` if no such function), `functionDescriptor(for:)`, `bookmarkData`,
  static `deviceArchitectureName`, static `specialize(contentsOf:options:cache:cachePolicy:)`.
  `Sendable`.
- **`InferenceFunction`** — `run(inputs:)`, and (from 324) a `states:` argument; `descriptor`.
  Safe to call the same function from different tasks concurrently.
- **`InferenceFunctionDescriptor`** — `inputDescriptor(of:)` → `InferenceValue.Descriptor`,
  which is `.ndArray(NDArrayDescriptor)` or an image; gives `shape`, `scalarType`.
  Use it to adapt to model changes **without changing code between deployments**.
- **`NDArray`** — `init(shape:scalarType:)`, read-only by default; `view()` for reads,
  `mutableView(as:)` for writes, `contiguousElements` (can be `nil` → non-contiguous layout).
- **`InferenceValue`** — `.ndArray` or `.pixelBuffer` (`CVMutablePixelBuffer` for image-typed I/O).
- Outputs are extracted with `outputs.remove("name")`.
- Also in the framework index but not yet covered by our local docs: **`AIModelAsset`**,
  **`ImageDescriptor`**, **`ComputeStream`**, **`AssetError`**, and the article
  *"Inspecting, debugging, and profiling Core AI models"* — ⚠️ we do **not** have that article
  locally; a web agent is fetching it.

### 3.3 Specialization + caching (the docs article + 324 + 326)
This is a genuinely deep topic and clearly deserves a standalone guide.
- `.aimodel` = **portable source** representation. Before running it must be **specialized** to the
  device → executable code tied to **that device's hardware AND OS version**.
- Two phases: (1) compilation — segment, plan, optimize compute (**this is the expensive one**);
  (2) generate executable artifacts per compute unit.
- Automatic + cached by default. First call specializes and stores; later calls load from cache.
- **`AIModelCache.default`**; `cache.model(for:options:)` returns `nil` if not cached (**does not
  specialize**) — use it to gate features / show "preparing…" UI.
- **`AIModel.specialize(contentsOf:options:cache:cachePolicy:)`** — specialize *without* loading,
  at a moment you choose (after download, on feature opt-in).
- **`AIModelCache.Policy`**: default (system may reclaim under storage pressure or source-model
  change) vs **`.persistent`**.
- `cache.deleteEntries(for:)`; deletion deferred while an `AIModel` instance still uses the entry.
- **App groups**: `AIModelCache(appGroup:)` + App Groups entitlement ⇒ share specializations
  across apps/extensions instead of duplicating.
- **Bookmarks**: `model.bookmarkData` → persist (e.g. UserDefaults) → `AIModel(resolvingBookmark:)`
  on next launch ⇒ **you can delete the source `.aimodel` and still run**. Bookmarks break on
  purge / manual delete / **OS update**; must handle re-download.
- **`SpecializationOptions`**: `.default` (system picks compute units to minimize latency),
  `.cpuOnly`, `init(preferredComputeUnitKind:)`. Check `ComputeUnitKind.availableKinds`.
  Concrete use case given: small background model → `.cpuOnly` so it doesn't contend with
  foreground GPU work.
- **AOT compilation** via `coreai-build`:
  - needs the **Metal Toolchain** (Xcode > Settings > Components, or
    `xcodebuild -downloadComponent MetalToolchain`)
  - `xcrun coreai-build compile MyModel.aimodel --platform iOS --min-deployment-version 27.0 --output compiled/`
  - emits **one `.aimodelc` per device architecture**, named `MyModel.<arch>.aimodelc`, where
    `<arch>` matches `AIModel.deviceArchitectureName` at runtime
  - each `.aimodelc` works on any OS ≥ the min deployment version passed
  - `--preferred-compute` to override compute unit selection
  - ⚠️ **only compiles for Apple-Intelligence-capable devices**: iPhone/iPad **A17 Pro or later**,
    Mac **M1 or later**, Vision Pro **M2 or later**
  - recommended distribution: host remotely, download only the matching arch, via
    **Background Assets**
  - loading is the same `init(contentsOf:options:)` — no code change
  - ⚠️ still requires *some* on-device specialization
- Xcode integration gotcha: **`.aimodel` files must be in Compile Sources**, and **builds fail with
  a missing Metal compiler error if the Metal Toolchain isn't installed**.

### 3.4 States / KV cache in Core AI (324 — the snake game)
Very teachable end-to-end story:
- Transformer decode loop got slower over time (quadratic in sequence length) — **visible as
  growing inference intervals in the Core AI Instrument**.
- Fix: **states** = inputs that are both **read and updated in-place** during inference.
- Authoring side: `torch.register_buffer` for the K/V cache tensors ⇒ they become **mutable buffers
  in the exported program** ⇒ Core AI converts them to **states**.
- Conversion side: pass **`state_names`** to the convert call.
- Runtime side: hold the cache `NDArray`s on your type, build a collection of `MutableView`s, pass
  as the **`states:` argument** of `InferenceFunction.run`.
- Model was converted with a **fixed max-context cache size**.

### 3.5 Low-level perf APIs (324, briefly — likely thin evidence, flag it)
- query the **optimal memory layout** of `NDArray` arguments and allocate to match, to avoid
  layout conversion at inference time
- **pre-allocate output values** for the framework to write into
- **asynchronous values** to pipeline multiple inference functions
- (`ComputeStream` in the framework index is presumably the vehicle — needs verification)

### 3.6 Core AI Python (325)
- `pip install coreai-torch` → installs **`coreai`** and **`coreai-torch`**.
- Flow: `torch.export(model, example_input)` → `ExportedProgram` →
  **run decompositions with Core AI's custom decomposition table** (⚠️ important: preserves
  high-level semantics Core AI supports natively, e.g. **attention**) →
  **`TorchConverter`** with input/output names → optimize → save `.aimodel`.
- **`dynamic_shapes=`** on `torch.export` to avoid baking in a traced sequence length.
- Python can **specialize and run inference natively** — `run` takes a dict of name → numpy array.
  Used for numerics verification vs the PyTorch original (assert small delta).
- **Multiple functions in one asset**: one `TorchConverter`, N exported programs, each with its own
  **entrypoint name**. SAM3 demo: `image_encode` / `text_encode` / `detect`.
  Payoff quantified: swapping only the text prompt re-ran text_encode + detect ⇒ **76% faster**
  second inference after warmup.
- **Custom Metal 4 kernels**: `TorchMetalKernel(metal source, PyTorch reference, input/output
  names)`; register with the converter; **MSL is embedded in the asset and ships with the model**.
  Must pass **result shapes** at each instantiation so Core AI can derive output shapes for dynamic
  inputs. Names in the MSL must match the declared input/output names.
- **`coreai-opt`** (the optimization library):
  - **config-driven**; per-scheme so you can compress differently for macOS vs iOS
  - **int4, int8, FP4, FP8** weight compression, flexible granularity
  - **presets** — e.g. `presets.w4` = 4-bit per-channel symmetric
  - **`ExecutionMode.EAGER`** for weight compression; **`GRAPH`** mode for activations
  - `Quantizer(config)` → pass model + example inputs → `prepare` / `finalize`
  - **`KMeansPalettizer`** for lookup-table palettization (4-bit palettization w/ per-channel
    scales; called out as **well-suited for power efficiency on iOS**)
  - a helper for **casting the program to fp16**
  - calibration-data quantization **or QAT** on larger datasets
  - SAM3 numbers: fp32 baseline **>3 GB** → w4 everywhere **~430 MB**, but quality regressed
    (an occluded flower stopped being detected)
- **Model re-authoring** (the advanced tier):
  - replace ops, change tensor layouts, change model interfaces
  - **predefined patterns** that signal concepts to Core AI — explicitly: **in-place KV cache
    updates**
  - **for iOS specifically**: static tensor shapes, **channels-first layouts**, and
    **convolutional op patterns instead of Linear layers** ⇒ lets Core AI hit native hardware
    primitives / the right compute unit
  - demands rigorous **module-level and model-level testing**
- **Core AI skills** — agent skills shipped in `coreai-models` that you install into your coding
  assistant. Apple says most of the session's code was co-developed with an agent using them.
  (Note: `skills/` dirs exist in `apple/coreai-models`, `john-rocky/*`, `mlx-swift-lm`.)

### 3.7 Core AI Debugger (325)
Standalone **application** (developer.apple.com/core-ai-debugger/). Feature set:
- **Navigator**: operations grouped **by PyTorch module**
- **Structure viewer**: graph of connectivity, execution order, data dependencies
- **Source viewer**: maps back to the **original Python source line**
- **Inspector**: op description, inputs/outputs, and **output tensor values** after a device run
- **Run on device**: pick a target, supply inputs, Run → specializes and executes for real
- **Comparison sessions**: compare two configurations (different Target or Compute Unit), or
  against a **reference run loaded from an Intermediates File**
- **NEW "save intermediates" API** in Python: executes a PyTorch model and captures intermediate
  tensors at each op → the reference file
- **Sync points**: automatically-identified op pairs where specialized output should match PyTorch;
  each scored by a similarity metric, **default PSNR** (changeable). Green/yellow/red nodes,
  sortable by similarity.
- The worked example: sort by similarity → low-PSNR sync points cluster in the **detector decoder**
  → detector is only 4% of params so compressing it wasn't buying anything → **exclude detector
  from the quantization scheme** → baseline quality restored at a fraction of the size.

### 3.8 coreai-models repo (325, 326)
Four things in one repo:
1. **model catalog** (`models/`) with per-model **export recipes**, incl. platform-specific variants
2. **`python/`** reusable export primitives
3. **Swift package** of runtime libraries — named products seen: **`CoreAILM`**,
   **`CoreAISegmentation`**. These wrap pre/post-processing (text encoding in, mask extraction +
   labeling out) so you don't hand-wrangle tensors
4. **agent skills**
Plus: **an API for creating a Core AI Language model that plugs into Foundation Models**, including
**bring-your-own token sampling strategies**.

### 3.9 The multi-model app pattern (326)
Concrete, very guide-able deployment narrative:
- Two small task-specific models beat one big one: **SAM 3** (segmentation, ViT) + **Qwen3 0.6B**
  (multilingual reasoning LLM). Rationale: better quality, smaller individual size, **upgrade
  independently**. Targeting **<1B params each**.
- SAM3 `.aimodel` shown as **623 MB**, targeting iOS 27.0 / macOS 27.0, exposing **3 functions**
  (`imageEncode`, `detect`, …).
- Distribution problem: bundling both added **>1 GB to app download**, hitting every updater
  including people who'll never use the feature. Solution: **Background Assets**, downloaded only
  when the user opts into the feature from a **first-run/feature-intro screen** — which is also the
  natural place to hide specialization latency.
- Then AOT-compile with `coreai-build`, ship **one background asset per architecture**, detect
  arch at runtime, request the matching one.
- macOS variant reuses the same code with a **larger model** (Qwen3 **8B**) + batch processing +
  longer context (whole-curriculum generation). "Same code, calling the same API, just a more
  capable model underneath."
- The LLM is loaded with **`CoreAILanguageModel`** ("one line — asset loading, engine creation,
  tokenizer setup — all abstracted"), then used via **`LanguageModelSession`** with
  `@Generable` guided generation. **You `import FoundationModels`.**

---

## 4. Metal / TensorOps (330)

Layering stated explicitly: Core AI and MLX sit on **Metal Performance Shaders**, which sits on
**Metal Performance Primitives + TensorOps**.

- **TensorOps** = a **Metal Shading Language** API for tensor ops (matmul, convolution) that
  automatically uses available hardware acceleration across all Apple silicon GPU generations.
- **M5 neural accelerator**: a new hardware block **in each shader core**, alongside the other GPU
  pipelines, aimed at dense compute-bound work — explicitly **LLM prefill**.
- **Quantized data types in Metal tensors:**
  - int4/int8 landed in an update to **macOS/iOS 26**
  - **macOS/iOS 27 adds fp4, fp8, and int2**
  - ⚠️ new small dtypes have **additional alignment requirements** — check Metal docs
- **Scale planes (new in 27):** one `MTLTensor` can carry quantized data + scales.
  Uses **FP8 E8M0 block-wise scale factors** (MX formats). Build a descriptor for the scale plane
  with `dataType` + `blockFactors`, create an **auxiliary plane map** tagging it as scales, attach
  to the tensor descriptor. Example: `fp8_e8m0_` scales with a **32×1 block** ⇒ 32 data elements
  share one scale.
- Kernel-side: `tensor_handle` (host-allocated) vs **`tensor_inline`** (constructed on the shader
  stack from buffer pointers).
- `slice(...)` by threadgroup ID slices **data and scale planes together**.
- `matmul2d_descriptor` → `matmul2d` op (parameterized by simdgroup count) → pass quantized tensors
  and **TensorOps dequantizes for you**.
- **Cooperative tensors** — storage distributed across participating threads' private memory.
  Lets you dequantize a custom format into registers instead of round-tripping threadgroup memory.
- **FlashAttention with TensorOps** (the advanced worked example):
  - `execution_simdgroup` operation scope so each simdgroup owns **complete rows** ⇒ softmax with
    no cross-simdgroup exchange
  - `reduce_rows` (e.g. `max` with init `-INFINITY`) → result in another cooperative tensor
  - `map_iterator` to map an element of the 2D cooperative tensor to its row-reduction element
  - **new in 27**: cooperative tensors can be fed **directly** into a matmul via
    `get_left_input_cooperative_tensor` (in macOS 26 you had to store to threadgroup memory first)
  - ⚠️ **must call `is_compatible_as_left_input` / `..._right_input` first** — layouts differ by
    dtype and other factors; if incompatible you still have to round-trip threadgroup memory
- Integration demo: custom FlashAttention MSL string → `TorchMetalKernel` → monkey-patch the
  HuggingFace attention implementation to call it → export SAM3 → run.

---

## 5. Evaluations framework (298, 299, 335)

New in **Xcode 27**; supports **macOS, iOS, watchOS, visionOS**. `import Evaluations`.
Explicitly not LLM-only — "you can evaluate any stochastic system, such as classifiers and linear
regression models."

**Core types:** `Evaluation` protocol, `ModelSample`, `Metric`, `Evaluator`,
`ModelJudgeEvaluator`, `ScoreDimension`, `ModelJudgePrompt`, `SampleGenerator`,
`TrajectoryExpectation`, `ToolCallEvaluator`, `ModelSampleProtocol`.

**The five steps** of an evaluation: (1) `subject(from:)` — the code under measurement;
(2) `dataset` — the samples; (3) evaluators + metrics; (4) `aggregateMetrics(using:)`;
(5) a test to run it.

**Swift Testing integration:** `@Suite`, `@Test`, and a new **`.evaluates` trait** taking the
evaluation + a notes dictionary (notes are how you label a run for later comparison).
Inside the test you get a **results bundle**; `results.aggregateValue(...)` then `#expect(...)`.
Also: **`#Playground` macro** is used for the ad-hoc human-judgement pass before you automate.

**Xcode 27 Evaluations Report:** report navigator → Evaluations; aggregate metric charts on top,
results table below; assistant editor shows per-sample prompt, each measurement, and the full model
response; **Compare button** for run-to-run comparison and a side-by-side comparison view.
Evaluation runs produce an **Xcode attachment** containing all the generated evaluation data —
which 335 then re-reads to build a second, meta evaluation. Nice trick.

**Quantitative vs qualitative rule of thumb (quotable):** "if you can measure it in code, then it's
quantitative. And if you can only describe it in words, then you need a qualitative metric, using a
ModelJudgeEvaluator."

**Model judges:**
- A judge is **just another `Evaluator`** producing the same `Metric` type — mix freely.
- Judge should be **at least as capable as the model being evaluated** (on-device feature → PCC
  judge).
- Components: instructions, feature input, feature output, **scoring guide**. Framework handles all
  but the scoring guide.
- **1–4 scale recommended** — even number prevents defaulting to a neutral middle; four levels give
  enough distinction without diluting meaning.
- **`ScoreDimension`** — name + description + scale. When you disagree with a score, **split the
  question into separate dimensions** (their example: "quality" → `Relevance` + `Usefulness`).
- **`ModelJudgePrompt`** — gives the judge app context, formats the response
  (`evaluationTarget`), passes expected values as reference.
- **Rationales are essential** — they show why the judge scored as it did. "You'll learn more from
  a single run than from hours of careful planning."

**Drift + alignment (335 — this is the standout, most sophisticated content in the corpus):**
- **Drift** = systematic disagreement between the model judge and the human expert. Widens as the
  dataset grows.
- **Accuracy** (% exact agreement) is a bad alignment measure when the score distribution is skewed
  — and it usually is, because datasets over-represent good output.
- **Cohen's kappa** (Jacob Cohen, 1960) is the recommended alignment metric:
  `(accuracy − chance agreement) / (1 − chance agreement)`, with chance weighted by score
  prevalence. **Target ≥ 0.6** ("a meaningful level of agreement").
- You implement it as a **custom aggregation method**, alongside mean and stddev per dimension.
- The meta-evaluation: dataset = (summary, tags, *my* ratings) extracted from the previous run's
  Xcode attachment; subject = just return the already-generated tags; evaluator = the same model
  judge; aggregate = Cohen's kappa. Then hill-climb the *judge*.
- **Experimental discipline**: control vs experimental prompt, **change one variable at a time**;
  when the experimental prompt wins, **backport it into the baseline** before testing the next
  change so there's still only one difference.
- Overfitting warning: give the judge **only a few** few-shot examples — a long list overfits the
  alignment score.

**Hill climbing (335):** develop → run → check expectations → analyze → repeat.
"**Evaluation-driven development**" is Apple's name for centering the loop.
Things you can hill-climb: instructions, tools, model choice, dataset, aggregation methods, the
evaluators themselves. Real example of a non-prompt change: adding a **book-lookup tool** to the
tagging service and comparing with/without (`tools:` defaulted to `[]` so the old evaluation kept
working — good API-design lesson).

**Synthetic data (299):**
- **`makeSamples`** needs prompt + dataset + **`targetCount`**. ⚠️ `targetCount` is the size of the
  **full resulting dataset including your seeds** (100 target + 13 seeds ⇒ 87 generated).
  Returns an **async stream**.
- **`SampleGenerator`** for full control: **`sessionProvider`** closure returning a
  `LanguageModelSession` (choose the model + instructions), **`samplingStrategy`**
  (`random` — default, no duplicates; `slidingWindow` — sequential, use when order is meaningful),
  and a **`validator`** closure.
- ⚠️ **Session reuse gotcha**: the generator calls `sessionProvider` **once** and reuses the session
  across batches for continuity — but can **exhaust the context window mid-run**, which throws;
  then it calls `sessionProvider` **again** for a fresh session with **no prior context**.
  ⇒ **your instructions must be self-contained and not assume a single invocation.**
- Validator runs **per sample in isolation** — it cannot check cross-sample properties (e.g.
  "reviews should vary in length" is *not* checkable there).
- Valid samples land in `.samples`, rejects in **`.invalidSamples`**, both updated in real time.
- Reality check from the demo: expanding 13 → 100 samples **made the scores drop**, revealing the
  feature was never as good as the small dataset suggested. Excellent teaching moment.
- Start-small guidance: **20–30 samples** is a fine start; "coverage" beats "count".

**Tool / agentic evaluation (299):**
- **`TrajectoryExpectation`** — checks the **order and kind** of tool calls in the transcript.
  `unordered` (just that it happened) vs ordered sequences. Argument matchers:
  **exact**, **`.naturalLanguage`** (matches intent, not string — e.g. cheerful/uplifting/happy),
  plus **`contains`, `oneOf`, `pattern`, `range`**, and more.
- **`disallowed`** parameter — tools that must **not** appear (tests negative instruction
  following).
- **`ToolCallEvaluator`** combines a `LanguageModelSession` + tools, gets a response, captures the
  structured transcript, scores against the expectation.
- `TrajectoryExpectation` is itself **`Generable`** ⇒ you can synthesize tool-eval datasets too.
  ⚠️ but the generating model **doesn't know your tools** — you must describe them, their purpose,
  and ordering constraints in the instructions.
- Motivating insight, quotable: "A model might give you a reasonable-sounding answer without ever
  calling the right tool. The final output can look correct while the path to get there isn't."

---

## 6. MLX (232 — plus repos, delegated)

- Four-layer local agentic stack: **MLX** → **MLX-LM** → **MLX-LM Server** → **agent**.
- `mlx_lm.server` is **OpenAI chat-completions compatible**, supports **structured tool calling**
  and **reasoning models**. Drop-in for any cloud LLM API.
- Agents shown: **OpenCode** (config: local provider, base URL localhost, model name), and
  **Xcode 27 itself** — *Settings → Intelligence → Add Chat Provider → Locally Hosted*, set port
  (8080 in demo). That's a notable integration: **Xcode's built-in AI can be pointed at a local
  MLX server.**
- Downstream consumers named: **Ollama, LM Studio, vLLM** "are just a few" built on MLX/MLX-LM.
- **M5 Neural Accelerators**: matmul **4× faster than M4**, which "translates almost exactly to
  prompt processing speedup". **No code changes or flags** — MLX picks the kernel.
  Framed around the agentic reality that sessions are **hundreds of thousands of tokens, mostly
  *not* generated** (prompt processing dominates).
- **Continuous batching** in MLX-LM Server — new requests join an in-flight batch; the point is
  parallel subagents not stalling in a queue.
- **Distributed**: `mlx.launch` + a **hostfile** describing nodes and connection type; model is
  **automatically sharded**. Motivating example: DeepSeek **1.6T params, >800 GB** of weights.
  **Thunderbolt RDMA from macOS 26.2** ⇒ up to **3× speedup with four nodes**.
  Cross-ref session: "Explore distributed inference and training with MLX" (we do NOT have that
  transcript — note as a gap).

---

## 7. Speech (docs only — no transcript in corpus)

- `SpeechAnalyzer` + module pipeline; `DictationTranscriber` with **presets**
  (`progressiveLongDictation` = immediate preliminary results, refined later) and
  **content hints** (`customizedLanguage(modelConfiguration:)`).
- **`CaptureInputSequenceProvider`** — **new in iOS/macOS 27**; sets up capture session + audio
  conversion + an async sequence compatible with the analyzer. Replaces hand-installing audio
  engine taps. `providerWithSession(from:compatibleWith:)`, `.analyzerInputs`.
  Also `AssetInputSequenceProvider` for files.
- `analyzer.analyzeSequence(_:)` → returns last audio time; then `finalizeAndFinish(through:)`.
- **`AssetInventory.assetInstallationRequest(supporting:)`** → `downloadAndInstall()`.
- Result-merging: results carry **audio time ranges**; volatile results replace earlier ones.
  Two documented strategies: (a) `rangeOfAudioTimeRangeAttributes(intersecting:)` +
  `replaceSubrange`, or (b) keep two transcripts (finalized + volatile).
- ⚠️ **Cancellation subtlety**: the display task must be **shielded from cancellation**
  (`withTaskCancellationShield`) or it stops reading before the transcriber emits its final update.
  Also: "the only way to fully end a capture session is to release all references to it" — hence
  cancellation is the more reliable approach.
- Custom LM: `SFCustomLanguageModelData` result-builder DSL — `PhraseCount`,
  `PhraseCountsFromTemplates` (classes + `Template("<piece> to <royal> <piece> <rank>", count:)`),
  `CustomPronunciation(grapheme:phonemes:)`; build a `.bin` with a CLI utility; then
  `SFSpeechLanguageModel.prepareCustomLanguageModel(for:configuration:)`.
- ⚠️ sample doesn't run in the Simulator; needs a physical iOS 27 device.

---

## 8. Sessions referenced but NOT in our corpus (evidence gaps)

Named in the transcripts, no local file:
- "What's new in image understanding" (Vision; BarcodeReaderTool / OCRTool detail)
- "LLM search using Core Spotlight" — *possibly* = 246, which we have; verify
- "Deep dive into Core AI model authoring and optimization" — *possibly* = 325; verify
- "Optimize custom machine learning operations with Metal tensors" — *possibly* = 330; verify
- "Explore distributed inference and training with MLX" — **not in corpus, real gap**
- "M5 machine learning" talk (TensorOps matmul basics) — **not in corpus**
- "Secure your apps with App Attest"
- "Supporting semantic search with Core Spotlight" (WWDC25)
- "Discover Apple-Hosted Background Assets" (WWDC25)
- "Deep dive into the Foundation Models framework" (WWDC25)
- "Build AI-powered scripts with the fm CLI and Python SDK" — *possibly* = 334; verify
- "Bring an LLM provider to the Foundation Models framework" — *possibly* = 339; verify

## 9. My running list of guide-topic candidates (pre-synthesis)

Recording these before reading subagent output so I can tell whether the synthesis adds to or
merely echoes my own read.

1. The 2026 Apple AI stack: choosing between Foundation Models / Core AI / MLX / Core ML
2. `LanguageModel` + `LanguageModelExecutor`: authoring a model provider package
3. Executor-store & configuration semantics; stateful executors and transcript diffing
4. Dynamic profiles I: profiles, DynamicInstructions, modifiers
5. Dynamic profiles II: history transforms, session properties, lifecycle modifiers
6. Agent orchestration: baton-pass, phone-a-friend, Skills, tool-calling mode
7. Transcript surgery: mutation, error policies, KV-cache economics
8. Private Cloud Compute: entitlement, reasoning levels, quota UX, watchOS
9. Guided generation deep dive (@Generable/@Guide, dynamic schemas)
10. Image input / multimodal prompting
11. System tools: OCR, barcode
12. Spotlight RAG deep dive (guidance profiles, pipeline stages, index delegate)
13. Debugging with the Foundation Models Instrument
14. `fm` CLI and shell automation
15. Foundation Models Python SDK
16. Core AI runtime fundamentals (AIModel/InferenceFunction/NDArray, non-escapable views)
17. Specialization & caching (incl. bookmarks, app groups, policies)
18. AOT compilation with `coreai-build` + Background Assets distribution
19. Core AI states / KV cache end-to-end
20. Core AI low-level perf (layouts, preallocated outputs, ComputeStream)
21. PyTorch → `.aimodel` with coreai-torch
22. Multi-function models and entrypoint splitting
23. coreai-opt: quantization (PTQ/QAT)
24. coreai-opt: palettization & pruning
25. Custom Metal kernels in Core AI (TorchMetalKernel)
26. Core AI Debugger workflow (sync points, PSNR, intermediates)
27. Model re-authoring for iOS/ANE (conv projections, static shapes, channels-first)
28. TensorOps: quantized tensors and scale planes
29. TensorOps: FlashAttention with cooperative tensors
30. Evaluations: first evaluation, metrics, Swift Testing integration
31. Evaluations: model judges & score dimensions
32. Evaluations: judge alignment, drift, Cohen's kappa
33. Evaluations: synthetic data generation
34. Evaluations: trajectory expectations / tool-call evaluation
35. Hill climbing / evaluation-driven development
36. MLX Python fundamentals
37. mlx-lm: CLI, quantization, LoRA
38. mlx-lm server + local agentic workflows (incl. Xcode Intelligence provider)
39. MLX distributed inference
40. MLX Swift for apps
41. mlx2coreai bridge
42. SpeechAnalyzer live transcription
43. Speech custom language models
44. DNIKit / data-quality introspection
45. Shipping & operating on-device models (download, update, storage, memory, thermals)
