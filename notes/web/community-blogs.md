# Community Blogs — Core AI / Foundation Models / MLX (2026)

**Agent:** web research — "community-blogs"
**Date of research session:** 2026-07-27
**Scope:** Non-Apple, community-written articles about Apple's 2026 AI/ML developer stack (Core AI, Foundation Models iOS 27, MLX, `.aimodel`, `coreai-torch`, Core AI Debugger). Independent benchmarks, opinions, and gotchas Apple's own docs omit.

> **EVERYTHING BELOW IS FROM A PAGE I ACTUALLY FETCHED IN THIS SESSION.** Nothing is from model memory. Every claim is tagged with a reliability grade (see next section). Where a community source contradicts Apple's own documented naming, I say so explicitly.

---

## 0. RELIABILITY GRADING — READ THIS FIRST

This was the single most important finding of the session. The 2026 community corpus about Core AI is **heavily polluted with AI-generated slop that invents API names**. Two of the articles I read contain fabricated file extensions, fabricated CLI syntax, and fabricated OS version numbers. A guide built by naively averaging these sources would be wrong.

I graded every source:

| Grade | Meaning |
|---|---|
| **A — Primary/measured** | Author ran code or measured on real hardware; raw data published; claims are checkable. |
| **B — Well-sourced secondary** | Named author, footnoted to Apple docs/sessions, distinguishes quote from paraphrase. |
| **C — Reasonable recap** | Editorially credible, no footnotes, no independent verification. |
| **D — Unreliable / AI-generated** | Contains verifiable factual errors, invented API names, or self-declares AI authorship. |

| Source | Grade | Why |
|---|---|---|
| `github.com/john-rocky/apple-silicon-llm-bench` (+ its `methodology/*.md`) | **A** | Reproducible harness, raw JSONL per run, published fairness rules, self-reported failures. |
| `rockyshikoku.medium.com` benchmark post | **A** | Same author as above, summarizes the repo. |
| `blakecrosley.com/blog/core-ai-run-models-apple-silicon` | **B** | 17 numbered footnotes, each to a specific Apple doc page; explicitly labels illustrative code as illustrative. |
| `infoq.com/news/2026/06/apple-core-ai-wwdc/` | **B** | Named author (Sergio De Simone), links every claim, cites HN/Reddit as community not fact. |
| Hacker News thread 48449665 comments | **B** (as *opinion*) | Real practitioner opinions, clearly attributable. |
| `dev.to/arshtechpro` (session 339 writeup) | **B** | Detailed, internally consistent protocol signatures matching Apple naming conventions. |
| `appcircle.io/blog/wwdc26-apple-core-ai-framework-explained` | **C** | Accurate but prose-only; zero code, zero numbers. |
| `avinashsangle.com` | **C** | Mostly accurate, correctly reproduces the official `coreai-torch` quickstart; some unverified framing. |
| `andrew.ooo` | **C-** | Good structure, but **says `.aiasset`** — wrong, the format is `.aimodel`. |
| `atalayasoft.com` | **C+** | Enterprise/consulting angle, careful about rumor-vs-confirmed. Useful for non-API context. |
| `byteiota.com` (both posts) | **C-** | One post is pre-WWDC speculation presented confidently; the other has good detail but no verification. |
| `techjacksolutions.com` | **C** | Straight press-release restatement. Correctly sourced to Apple Newsroom. |
| `aimadetools.com/blog/what-is-apple-core-ai/` | **D** | **Fabricated.** See §9.1. |
| `chatforest.com` builder guide | **D** | **Self-declares AI authorship**; invents a fine-tuning API. See §9.2. |

---

## 1. THE TWO ASSIGNED ARTICLES

### 1.1 Blake Crosley — "Core AI: Running Models on Apple Silicon"

- URL: https://blakecrosley.com/blog/core-ai-run-models-apple-silicon
- Published: **2026-06-08** (WWDC26 keynote day)
- Grade: **B**. This is the best-sourced conceptual piece in the corpus.
- Retrieved verbatim via `r.jina.ai` (WebFetch alone returned only a summary).

**Framing quote (opening line):**

> "Apple's on-device AI stack has had a missing rung. Foundation Models gives you the system LLM, sealed and free. Core ML runs a fixed converted model with the converter making the hardware decisions for you. MLX ships an array framework you embed and a model you select. iOS 27 adds the rung below all three: Core AI, a framework whose one-line abstract is 'Run AI models in your app on Apple silicon.'"

**The thesis (this is the article's actual contribution — a decision rule):**

> "reach for Core AI when you have a model you want to run with explicit control over where and how it executes, and stay at Core ML or Foundation Models when you do not. The framework rewards a specific need, not a default preference."

And the closing formulation, which is the most quotable line in the whole corpus:

> "The throughline across the whole stack: each layer down trades a default away for a handle. Foundation Models hands you everything and asks nothing. Core AI hands you the levers and asks you to know which to pull. **If you cannot name the specialization, caching, or scheduling control you need, you do not need Core AI yet.**"

#### 1.1.1 Type inventory, with the exact Apple-doc quotes the author footnotes

Each of these is quoted by the author *from a specific Apple documentation page* (footnote number in brackets). The declaration kinds (`struct` / `final class` / `enum`) come from the author's footnote text, which claims to reproduce the Apple docs' "Declaration" line.

| Type | Apple one-liner (as quoted by author) | Declared as | fn |
|---|---|---|---|
| `AIModelAsset` | "An unspecialized source model asset." | (not stated) | 2 |
| `AIModel` | "A specialized model for running inference on a device." | (not stated) | 3 |
| `AssetError` | "An error that occurs during model asset operations." | `struct AssetError` | 4 |
| `NDArray` | "A multidimensional array of scalar values used for model inference." | `struct NDArray` | 5 |
| `AIModelCache` | "A cache that stores the specialized model artifacts for inference." | `final class AIModelCache` | 6 |
| `NDArrayDescriptor` | "A description of an array's shape, scalar type, and memory layout expectations." | `struct NDArrayDescriptor` | 7 |
| `ComputeUnitKind` | "A type of hardware compute unit available for model inference." | `enum ComputeUnitKind` | 8 |
| `SpecializationOptions` | (carries specialization-time choices incl. compute-unit targeting) | `struct SpecializationOptions` | 9 |
| `ComputeStream` | "A stream of work to be run asynchronously." | `final class ComputeStream` | 10 |
| `ImageDescriptor` | "A description of an image's dimensions and pixel format." | `struct ImageDescriptor` | 11 |
| `InferenceValue` | "A value that an inference function accepts as input or produces as output." | `struct InferenceValue` | 12 |
| `InferenceFunctionDescriptor` | "A description of an inference function's signature." | `struct InferenceFunctionDescriptor` | 13 |
| `InferenceFunction` | "A function that performs inference on input values and produces output values." | `struct InferenceFunction` | 14 |

> **Cross-check note for the guide writers:** these should be verified against the actual `developer.apple.com/documentation/coreai/*` pages by whichever agent owns Apple docs. The author is careful, but this is a secondary source quoting a primary one.

#### 1.1.2 The one API signature the author asserts is Apple-named

The author is explicit that **only** `run(inputs:states:outputViews:)` is taken from Apple's own prose; the surrounding construction is his invention. His code block, verbatim, comment included:

```swift
// run(inputs:states:outputViews:) is named in Apple's docs; surrounding
// loading/value-construction shapes are illustrative — confirm against Apple's docs.
let function: InferenceFunction = /* load from an AIModel */
let outputs = try function.run(
    inputs: inputValues,        // InferenceValue per input
    states: stateValues,        // any stateful values the function declares
    outputViews: outputViews
)
```

Other code in the article carries the same disclaimer and should **not** be treated as API:

```swift
// Call shape is illustrative; confirm the exact initializer against Apple's docs.
let asset = try AIModelAsset(url: bundleURL)   // an .aimodel bundle on disk
// Inspect signatures, input/output descriptions, compute and storage types,
// and author-provided metadata — without specializing.
```

```swift
// Call shape is illustrative; confirm exact property/method names against Apple's docs.
let inputDescriptor = function.descriptor.inputs.first!   // an NDArrayDescriptor
// The descriptor fixes shape, scalar type, and layout; the array you build
// must satisfy those expectations (e.g. .float32 means .float32).
```

#### 1.1.3 Design insights worth lifting into a guide

- **Asset/Model split exists because specialization is expensive.** "a model asset lets you query model information without performing specialization, which is an expensive operation." Asset = inspection only, *cannot run inference*. Practical framing: "Inspecting a hundred candidate models to pick one is cheap if you only build assets; it would be ruinous if every inspection specialized."
- **Descriptor-before-value is a repeated pattern.** "Core AI consistently puts a cheap *description* object in front of an expensive *value* object." Applies to `NDArrayDescriptor` → `NDArray`, `ImageDescriptor` → pixel input, `InferenceFunctionDescriptor` → `InferenceFunction`.
- **Descriptors are STRICT.** "most expectations are strict. If the descriptor specifies a scalar type of `.float32`, the array you provide must use `.float32`."
- **Cache keys include the specialization combination.** "each cache entry contains a specialized asset formed from a specific `.aimodel` or `.aimodelc` and a specialization combination." → **changing `SpecializationOptions` changes which cache entry you hit.** This is a real footgun: silently varying options defeats your cache.
- **Default compute targeting is "all units".** "by default specialization uses all available compute units on the device."
- **`ComputeStream` serializes by data dependency, not by submission order alone:** "multiple inferences encoded to the same stream are serialized as needed based on the values read and written."
- **`InferenceFunction` is `Sendable` AND self-managing under concurrency:** "It is `Sendable`, so you can run it concurrently from multiple tasks, and Apple notes it automatically allocates additional intermediate buffers as needed to support that concurrency." Author's editorial: "You do not serialize calls behind a lock to protect shared scratch space… That is a meaningful difference from APIs where a single inference handle is effectively single-threaded."
- **Models expose *named* functions, not one callable:** "an encoder, a decoder, a vision tower, a prefill versus a decode step".
- **States = KV cache.** "a function with state is how a stateful model (a KV cache in a transformer decode loop, for instance) keeps information between calls, and the descriptor tells you a function has them before you try to drive it."
- **`InferenceValue` is the union type** that lets one `run` signature carry both tensors and images: "wraps either an `NDArray` or a pixel buffer".

#### 1.1.4 ⭐ The WWDC lab statement — strategic direction signal

This is the single most consequential *strategic* claim in the corpus, and the author flags its provenance carefully:

> "A WWDC 2026 lab statement sharpens where the line sits between Core AI and Core ML for new work. Paraphrased from a locally transcribed recording of the WWDC 2026 Coding Intelligence, Machine Learning & AI Group Lab, a Core AI engineer on the panel said **Apple is asking everyone working with neural networks to move to Core AI going forward, with Core ML staying in place but focused on traditional machine learning such as decision trees, and everything new heading to Core AI.**"

Provenance caveat, in the author's own footnote 16:

> "Apple published no captions for the labs, so the wording here is a paraphrase, not a quotation."

And his own hedge in body text:

> "Read it as a direction-of-travel signal from the people building the framework rather than a documented policy."

Source: WWDC 2026 **lab 8121**, "Coding Intelligence, Machine Learning & AI Group Lab".

> **This paraphrase is independently corroborated** by an HN commenter reading the updated Core ML docs (see §5.1) — two independent parties reached the same reading. That raises confidence considerably.

#### 1.1.5 The four-way decision tree (author's own words, condensed)

- **Foundation Models** — "when Apple's system model does the task. Summarize, classify, extract, rewrite, structured output… costs you no weights, no memory budget, and no specialization step. If your feature fits, stop there. **Dropping to Core AI to re-implement what the system model already does is wasted work.**"
- **Core ML** — "when you have a fixed, converted model and want the converter to make the hardware and optimization decisions for you… **If you do not want to think about compute-unit targeting or compute streams, that is the signal to stay at Core ML.**"
- **MLX** — "when you want a research-grade array framework you embed and iterate on: your own training loop, quantized open-weight models, LoRA fine-tunes, fast experimentation. MLX is **a library you ship with weights, not a system model-execution surface.**"
- **Core AI** — "when you have a model to run and you want the framework's explicit handles… You reach here when the higher layers' defaults are the thing in your way, and you can name which default you need to override."

#### 1.1.6 Toolchain / workflow section (footnote 17 → three Apple doc pages)

The author sources this whole section to three Apple pages: *Integrating on-device AI models in your app with Core AI*, *Compiling Core AI models ahead of time*, *Inspecting, debugging, and profiling Core AI models*.

**Convert:**
- Start from an `.aimodel` file, either converted with `coreai-torch` ("Apple's Core AI PyTorch Extensions for Python") or already in the format.
- The `.aimodel` "goes into your Xcode target like any resource, shows up in the **Compile Sources** build phase, and gets a **model viewer in Xcode** that displays parameters, storage size, metadata, and the operation graph."
- 🚩 **BUILD GOTCHA:** "Core AI model integration requires the **Metal Toolchain**, which Xcode does not install by default, and **builds containing `.aimodel` files fail with a missing Metal compiler error** without it."

**Compile AOT (optional on macOS, see §4 for why it's mandatory on iOS):**
- "Specialization happens automatically when you create an `AIModel`, and for large models that first-load cost is real."
- `coreai-build` CLI "moves the most expensive part, model compilation, to your build machine: it converts `.aimodel` into `.aimodelc` assets, **one per device architecture** (compiling `MyModel.aimodel` produces `MyModel.<arch>.aimodelc`), and at runtime the app picks the asset matching the current device so Core AI skips the compilation step."
- 🚩 **AOT hardware floor:** "iPhone or iPad with **A17 Pro or later**, Macs with **M1 or later**, and Apple Vision Pro with **M2**." (i.e. the Apple Intelligence hardware floor.)

**Debug and profile — three distinct tools:**
1. **Core AI Debugger** — "a standalone macOS app for inspecting a model's operation graph, running it against a device, and comparing outputs to a reference run"
2. **Core AI debug gauge in Xcode** — "monitors load, specialization, and inference activity live during a debug session"
3. **Core AI instrument** — "an Instruments template that profiles execution timing across the CPU, GPU, and Neural Engine"

---

### 1.2 Appcircle — "WWDC26: Apple's Core AI Framework Explained"

- URL: https://appcircle.io/blog/wwdc26-apple-core-ai-framework-explained
- Published: **2026-06-13T12:38:22+00:00**
- Grade: **C**. Accurate but **contains ZERO code, ZERO benchmark numbers, ZERO version gates.** It is a narrated walkthrough of the WWDC session 324 slides (13 screenshots, all `core-ai-*.jpg`).
- Retrieved via `r.jina.ai` (WebFetch summary confirmed the same: "The article contains **no code snippets**, specific benchmark numbers, OS/hardware requirements, or comparisons").

**What it uniquely adds** (details not in the Crosley piece):

- **Positioning:** "Core AI is more than a runtime framework. Apple positions it as a complete AI development platform that covers the entire model lifecycle, from model authoring and optimization to conversion, debugging, deployment, and app integration."
- **`coreai-torch` has validation tooling:** "The workflow also includes built-in validation tools, allowing developers to **compare outputs between the original PyTorch model and the converted Core AI model to ensure numerical accuracy** before deployment."
- **Dynamic shapes:** "preserve dynamic dimensions through dynamic shape support" and, in the Xcode section, "**support for dynamic dimensions, which allow models to accept inputs of varying sizes without requiring multiple model variants.**"
- **Xcode `.aimodel` viewer contents:** "model size, operation distribution, and available inference functions… inspect function signatures to understand expected inputs and outputs".
- **Swift language features:** "The framework also takes advantage of modern Swift language features, including **memory-safe and non-escapable types**". (The "non-escapable types" detail — i.e. `~Escapable` — is notable and appears nowhere else in the corpus.)
- **States/KV cache rationale:** "States allow models to store and update information directly between inference calls, eliminating the need to repeatedly process historical inputs. By **keeping transformer key and value embeddings in a cache that is updated in place**, applications can significantly reduce computation overhead."
- **Custom kernels:** "enhanced with **custom compute kernels built using Metal 4**".
- 🚩 **Specialization = first-load stall:** "specialization can introduce noticeable delays the first time a model is loaded, especially for larger models. To help manage the user experience, Core AI provides APIs that allow developers to **check model readiness, trigger specialization ahead of time, and avoid performing expensive preparation steps during user-facing interactions.**"
- ⭐ **`AIModelCache` can be shared across an App Group** — "The framework also supports **sharing model caches across multiple applications within the same App Group**, allowing related apps to reuse previously specialized models and reduce redundant work." Also: "developers can inspect cached models, proactively manage storage, and **control how long cached artifacts remain available**." (InfoQ independently confirms the App Group sharing — see §3.)
- ⭐ **Core AI Debugger traces back to Python source:** "One of its most powerful capabilities is the ability to **trace operations in a converted Core AI model back to the original Python source code**, making it significantly easier to diagnose numerical issues, validate model behavior, and troubleshoot conversion-related problems."
- **Low-level perf levers (three named):** "optimal NDArray memory layouts to reduce data conversion overhead, **pre-allocate output buffers** to avoid unnecessary memory allocations during inference, and use **asynchronous execution mechanisms to efficiently chain multiple inference operations** together."
- ⭐ **Core AI ↔ Foundation Models integration:** "The platform additionally supports integration with the Foundation Models framework, allowing developers to **bring their own language models, customize token generation strategies**, and combine third-party AI models with Apple's native AI capabilities."
- Links to `https://github.com/apple/coreai-models` ("ready-to-use model collections, conversion tools, and Swift libraries tailored for popular model families").

---

## 2. ⭐⭐ THE INDEPENDENT BENCHMARK — `apple-silicon-llm-bench` (Grade A)

**This is the most valuable source in the entire session.** It is the only place with measured, reproducible, raw-data-backed numbers comparing Core AI against MLX/CoreML/llama.cpp/LiteRT on real hardware, plus the deepest catalogue of real Core AI footguns anywhere.

- Repo: https://github.com/john-rocky/apple-silicon-llm-bench (MIT). CLI brand: `yardstick`.
- Author: MLBoy / Daisuke (john-rocky), freelance engineer. Also author of `john-rocky/CoreML-LLM`.
- Blog post: https://rockyshikoku.medium.com/i-benchmarked-apples-new-framework-against-mlx-for-on-device-llms-e52a769494b1 (2026-06-10)
- Methodology docs read: `methodology/coreai-ios.md`, `methodology/coreai-export-lowering.md`
- Repo self-description: "A neutral, reproducible benchmark for running local LLMs (and, in time, ASR / TTS) on Apple Silicon. Compares **MLX Swift, llama.cpp, CoreML (swift-transformers), LiteRT-LM, ExecuTorch, ANEMLL, Apple Core AI** — and Apple's own Foundation Models — under real device constraints, not just `tok/s` on a server."

It publishes **fairness rules** (`methodology/fairness-rules.md`), keeps failed runs on record ("that failed run stays on record per fairness rule #4"), flags Debug-vs-Release capture contamination (rule #7), and CI-checks that the README tables match the raw JSONL (`python scripts/render_results.py --check`). This is unusually rigorous for a community benchmark.

### 2.1 iPhone 17 Pro · Qwen3-0.6B · short-chat · warm decode (median)

| Engine | Compute | Decode tok/s | Peak RAM |
|---|---|---:|---:|
| **Core AI** (pipelined) | GPU | **181** 🏆 *(1st run 71)* | 524 MB |
| MLX | GPU | 112 ⚠️ | 539 MB |
| **Core AI** (static-shape) | ANE | 49 | 1,166 MB |
| **CoreML-LLM** | ANE | 39 | **184** 🏆 |

🚩 **The author's own caveat on the MLX row is important and self-critical** — do not quote 1.6× without it:

> "⚠️ **MLX row: Debug-build capture** (fairness-rules #7). The warm 112 tok/s is the median of the two warm **Debug** runs…; **Release**-build cold captures of the same model read **126–133 tok/s**, so warm MLX on Release is likely ~130 and Core AI's warm lead nearer **~1.4×** than 1.6×. A Release warm re-capture is pending. All other rows are Release builds."

From `methodology/coreai-ios.md`, the same table with TTFT added:

| Engine | Compute | Decode tok/s | TTFT (warm) | Peak MB |
|---|---|---:|---:|---:|
| Core AI GPU (`coreai-pipelined`) | GPU | **~180 warm** / 71 cold | ~26 ms | ~524 |
| MLX | GPU | ~115 | ~57 ms | 539 |
| Core AI ANE (`static-shape`) | ANE | ~50 | ~63 ms | ~1166 |
| CoreML-LLM | ANE | ~39 | ~548 ms | **~184** |

**Cold-vs-warm, quoted:**

> "Core AI GPU's **181 tok/s is the warm (steady-state) number**. The pipelined engine pays a one-time cost on the **very first generation** — kernel compilation plus filling a 3-stage pipeline — so the **first run is 71 tok/s**. But it really is one-time: even across app restarts, every run after the first sits at ~181 (the compiled kernels persist). MLX is flat at ~112 from the start."

> "In short: **Core AI is slower exactly once — and from the second run on, it's ~1.6× MLX, forever.**"

### 2.2 ⭐ Mac M4 Max scaling — the lead COLLAPSES at realistic model sizes

| Model (4-bit) | Core AI GPU | MLX | Core AI lead |
|---|---:|---:|---:|
| Qwen3-0.6B (macOS-26 export) | 1,121 | 455 | **2.47×** |
| Qwen3-0.6B (macOS-27β re-export) | ~500 | 455 | **1.1×** |
| Qwen3-8B | 94 | 90 | **1.05×** |

> "Core AI's pipelined-GPU lead is large on **tiny** models — where its async-dispatch / overlap dominates — but **converges to a near-tie at a realistic 8B**, where both runtimes become memory-bandwidth-bound."

Matched conditions: "512-token prompt, 512 gen, greedy, warm. Core AI via Apple's `llm-benchmark`; MLX via `mlx_lm`."

**This is the headline correction to the hype.** wccftech built an entire article on exactly this framing (see §6).

### 2.3 Full official-recipe matrix (M4 Max, macOS 27β artifacts, `llm-benchmark` defaults 512p/1024g/5)

| Model | Artifact | Core AI decode (prefill) | MLX 0.31.3 decode (prefill) | Verdict |
|---|---|---:|---:|---|
| gpt-oss-20b (MoE, MXFP4) | 13 GB | 78.1 (1,252) | **100.2** (1,528) | **MLX +28%** |
| qwen3-0.6b | 335 MB | **484** (9,396) | 432 (9,366) | **Core AI +12%** |
| qwen3-4b | 2.1 GB | 145.4 (**1,635**) | 145.8 (1,495) | tie |
| qwen3-8b | 4.3 GB | **94.1** (912) | 90.0 (825) | **Core AI +5%** |
| gemma3-4b-it | 2.1 GB | **141.5** (1,669) | 136.3 (1,631) | **Core AI +4%** |
| gemma3-12b-it | 6.2 GB | 55.0 (**578**) | 55.1 (528) | tie |
| mistral-7b-v0.3 | 3.8 GB | **101.7** (976) | 97.5 (918) | **Core AI +4%** |

> "**Core AI matches or beats MLX on every dense model; MLX's one clear win is the MoE** (expert dispatch, not the core engine). On noise: per-trial σ is ≤0.4% on 6 of 7 models (worst 1.3%) — the dense deltas are 10–30× trial noise with a consistent direction."

**MoE memory dial (undocumented env var!):** "gpt-oss-20b bonus: **`COREAI_CHUNK_THRESHOLD`** is a memory dial — unchunked 4096-token prefill hits 1,439 tok/s (+16%) at 18 GB dirty footprint, chunk-128 (the `llm-runner` MoE hint) caps memory at 1.7 GB for 766 tok/s."

Bundles published at `https://huggingface.co/mlboydaisuke` as `<model>-CoreAI-official` repos, with hashes + env stamps.

### 2.4 🚩🚩 THE BIGGEST GOTCHA IN THE CORPUS — export lowering is OS-version-sensitive

From `methodology/coreai-export-lowering.md`. **TL;DR in the author's own words:**

> "**`coreai.llm.export qwen3-0.6b` produced a 1,116 tok/s artifact when this repo's Mac numbers were first taken, and a ~500 tok/s artifact two days later — same command, same registry preset, same source checkout, same wheel versions, same machine. The only environment change in between was the macOS 26 → 27 beta upgrade. Benchmark the artifact you ship, pin the artifact, and don't assume a re-export reproduces it.**"

A/B, same day, same `llm-benchmark` binary, `-p 128 -g 256 -n 3`:

| Artifact | Exported | Decode tok/s | Prefill tok/s |
|---|---|---:|---:|
| `qwen3_0_6b_dynamic` (original) | 2026-06-09 (macOS 26) | **1,116** | **17,350** |
| `qwen3_0_6b_4bit_dynamic` (re-export) | 2026-06-11 (macOS 27 beta) | 500 | 6,667 |
| re-export, pristine upstream `main` @0c1055f | 2026-06-11 (macOS 27 beta) | 504 | 6,676 |

**Root cause — op-level evidence from `strings main.mlirb`:**

- **Fast artifact**: "plain `Linear$N` composites, **zero** quantization ops in the program text, yet 327 MB (4-bit-sized) → 4-bit weights consumed natively by the runtime's Linear kernels (quantized-matmul path)."
- **Slow artifact**: "`ParametrizedLinear$N` composites + **141× `constexpr_blockwise_shift_scale` ops** → explicit dequantize-then-matmul."

> "Same 4-bit storage class (327 vs 320 MB); the **compute path** differs 2.2×."

**⭐ The mechanism — a genuinely important architectural fact about the `coreai-core` wheel:**

> "**The `coreai-core` wheel ships TWO complete native stacks** and picks one at import time (`coreai/runtime/__init__.py`): macOS < 27 → the wheel-bundled local stack (`_coreai_runtime.so`); macOS ≥ 27 + wheel install → the **OS framework** (`_coreai_runtime_os.so`). **Env overrides exist: `USE_LOCAL_COREAI` / `USE_OS_COREAI`.** The compiler bindings (`_coreaiIR`) ride the same switch."

Wheel versions pinned in the investigation: **`coreai-core 1.0.0b1` / `coreai-torch 0.4.0` / `torch 2.9.0`**.

The quantizer path: "`quantize_pytorch_model` → `coreai-opt` PT2E `Quantizer`… it ALWAYS emits the parametrized/dequant form. The fast artifact's plain-`Linear$N`-no-dequant form must therefore be produced LATER, by the compiler folding dequant into the Linear composites during `prog.optimize()` (**`coreai-pre-compilation-rewrite`**) / serialization."

**The decisive negative result:**

> "re-exporting on macOS 27β with `USE_LOCAL_COREAI=1` — i.e. the *byte-identical frozen wheel compiler that produced the fast artifact on macOS 26* — STILL yields the dequant-style artifact… Same pass code, different OS underneath, different lowering ⇒ **the fold decision consults the running OS (capability/target queries under the pass), not just the stack's own code.**"

Author's suspicion: "plausibly a 27-beta regression in quantized-Linear legalization. Worth an Apple feedback with this document attached."

**Consequences (verbatim):**

1. "**An `.aimodel` is a build artifact, not a pure function of the recipe.** Treat it like a compiled binary: version-stamp it, keep it, benchmark exactly what ships."
2. Numbers carry artifact date + OS in an `ENV.md`.
3. "The effect is size-dependent: at 8B both artifact generations measure ~94 tok/s (bandwidth-bound); at 0.6B the lowering dominates (2.2×). **Small-model numbers are the canary.**"
4. "If you have a macOS-26-era artifact, **keep it** — as of the 27 beta we know no recipe flag that re-produces the native-quantized lowering."

**Confirmed on iPhone too** (both AOT-compiled `--architecture h18p`, GPU, synthetic 512p/1024g):

> "macOS-26 artifact **115.1 tok/s** decode / 5,807 prefill / 0.22 GB footprint vs 27β artifact 57.2 / 1,519 / 0.47 GB — **~2× decode, 3.8× prefill, half the memory, from the export environment alone.** ANE (official iOS static preset, same protocol): 69.6 tok/s, 0.045 s warm load."

### 2.5 🚩 Core AI iOS-specific gotchas (from `methodology/coreai-ios.md` + the Medium post)

**Pitfall #1 — iOS cannot JIT; AOT is MANDATORY on device.**

> "The exported `.aimodel` is MLIR IR (`main.mlirb`, `compilation.targets: []`). **macOS JIT-compiles it at load time; iOS cannot JIT.** Load the raw IR on the phone and you get: `Model load failed: NSPOSIXErrorDomain Code=2 "No such file or directory"`"

That error message is spectacularly misleading — a *missing compiled target* surfaces as **ENOENT**. Worth calling out loudly in any guide.

The fix, exact command from the methodology doc:

```bash
xcrun coreai-build compile qwen3_0_6b_ios.aimodel \
    --platform iOS --preferred-compute neural-engine --output out/   # or: gpu
# → out/qwen3_0_6b_ios.<arch>.aimodelc  (one per GPU family; h18p = iPhone 17 Pro)
```

Shorter form from the Medium post:
```
xcrun coreai-build compile qwen3_0_6b_ios.aimodel
# → out/qwen3_0_6b_ios.h18p.aimodelc (per GPU family; h18p = iPhone 17 Pro)
```

**Observed `coreai-build compile` flags:** `--platform iOS`, `--preferred-compute neural-engine|gpu`, `--output <dir>`, `--architecture h18p`. GPU-family arch codes are per-device (`h18p` = iPhone 17 Pro).

**Then you must hand-edit the bundle metadata:**

> "Then assemble a loadable bundle: copy the device-arch `.aimodelc` + the `tokenizer/` next to a **`metadata.json` whose `assets.main` points at the compiled file** (`qwen3_0_6b_ios.h18p.aimodelc`), per `models/README.md#compiled-models`."

**Pitfall #2 — ⭐ compute unit is fixed by the EXPORT SHAPE, not a runtime flag.**

> "**It does not switch with a runtime flag.** `EngineFactory` decides automatically from the model's *structure*:
> - `--platform iOS` (static shapes) → detected as chunked-static → **ANE** (the `static-shape` engine)
> - a dynamic export → **GPU** (the `coreai-pipelined` engine)
>
> So to compare GPU vs ANE you prepare **two separate AOT-compiled bundles** (static = ANE, dynamic = GPU). **Forcing `coreai-pipelined` onto a static model is rejected with `unsupportedEngineVariant`.**"

Export table:

| Export | Command | Shape | Engine it lands on |
|---|---|---|---|
| **iOS / static** | `coreai.llm.export qwen3-0.6b --platform iOS` | fixed ctx 4096, mixed 4/8-bit | **ANE** (`static-shape`) |
| **dynamic** | `coreai.llm.export qwen3-0.6b --platform macOS` | dynamic ctx, INT4 | **GPU** (`coreai-pipelined`) |

Runtime catalog ids used: `core-ai/qwen3-0.6b-ane`, `core-ai/qwen3-0.6b-gpu`.

**Export CLI observed:** `uv run coreai.llm.export qwen3-0.6b --platform iOS|macOS [--output-name …]`. Registry preset tuple seen in source: `("qwen3-0.6b", …, "4bit", "float16", 8192)`.

**Pitfall #3 — xcframework modulemap collision.**

> "On the build side, `coreai-models`' **`CXGrammar.xcframework` and `executorch.xcframework` both ship an `include/module.modulemap` and collide, so the iOS app drops ExecuTorch.**"

(`CXGrammar` is itself an interesting name — implies Core AI ships a **constrained-grammar / guided-generation** component.)

**Pitfall #4 — `devicectl` driving trap.**

> "*Launching* `devicectl process launch` **with** `--console` *from a non-interactive shell (e.g. in the background) fails with* `CoreDeviceError 10002`. The stable recipe: launch **without** `--console` (detached), pass `--runs N` (one cold + the rest warm in a single session), and pull `Documents/results` after it finishes."

**Pitfall #5 — Core AI has a memory "depth wall" / jetsam risk on iPhone.**

> "The standard deep protocol **jetsams** Core AI — that failed run stays on record per fairness rule #4."
> "Core AI's 0.352 is a shallow-rep reference (**192 tok/rep to stay under its depth jetsam wall**; the shallow bias *favors* it — still ~2.9× LiteRT)."

**Pitfall #6 — Metal toolchain path breaks after reboot/Xcode update (SwiftPM cache).**

> "If a Release build ever fails with `unable to spawn … Metal.xctoolchain/usr/bin/metal (No such file or directory)`, the on-demand Metal toolchain mount changed (a reboot or Xcode update remounts it under a new path) and SwiftPM's cached build manifest still points at the old one. Clear the manifest and rebuild — `rm -rf .build/out/Intermediates.noindex/XCBuildData`… Only re-download the toolchain (`xcodebuild -downloadComponent MetalToolchain`) if the asset itself is gone."

**Requirements for reproduction (verbatim):**

> "- macOS **26.4+ / Xcode 27** (+ `coreai-core`) to export & compile; iPhone on **iOS 27** to run.
> - The BenchmarkApp iOS target is bumped to **iOS 27** (the `coreai-models` package floor)"

### 2.6 ⭐ Sustained throttling — the GPU/ANE inversion (nobody else measures this)

| Gemma 4 E2B, iPhone 17 Pro | Burst tok/s | Sustained (10 min) | Retained |
|---|---:|---:|---:|
| **CoreML / ANE** | 33 | **22** | **67%** |
| MLX / GPU | 48 | 18 | 38% |
| LiteRT-LM / GPU | 56 | 27 | 48% |

> "Run the same model **continuously** and it flips: the GPU runtimes (MLX, LiteRT-LM) heat up and shed **~50–60% of their throughput** under sustained load, while the **ANE barely moves** (retains ~65%). MLX crosses the 50%-lost line within ~60 s… The ANE draws ~half the package power… so it heats slowly and the SoC doesn't throttle it."

> "Two **independent** GPU runtimes collapsing the same way is a GPU-thermal property of the phone, not a runtime quirk. MLX ends up *below* the ANE… **The GPU wins the sprint; the ANE wins the marathon** — and it frees the GPU for the rest of the app."

Method: "600 s continuous generation, cold (`nominal`) start, unplugged, tg128; decode rate from a rolling window."

**Retention percentages across all arms (Gemma 4 E2B, iPhone 17 Pro):** LiteRT 76% / MLX-OptiQ 67% / MLX-PTQ 64% / Cactus 57% / **Core AI 56%** / llama.cpp 54%.

> **Guide implication:** the §2.1 "Core AI GPU 181 tok/s" headline is a *burst* number. For an always-on feature, Core AI's GPU path will shed ~44% of it. This nuance is absent from every other community source.

### 2.7 ⭐ Energy per token — the ranking INVERTS vs speed

**M4 Max, Gemma 4 E2B, sustained-512, via `powermetrics` (whole-system package power):**

| Runtime | Avg pkg power (W) | Energy / 512-tok run (J) | **J / token** |
|---|---:|---:|---:|
| **apple-fm** (system model) | 7.6 | 67.4 | **0.11** 🏆 |
| mlx-swift (4-bit MLX) | 24.7 | 123.0 | 0.24 |
| llama.cpp (Q4_K_M, GGUF) | 24.5 | 126.3 | 0.25 |
| coreml-llm (INT4 palettized, ANE) | 12.7 | 244.9 | 0.48 |

> "**Energy ranking inverts the decode-tok/s ranking.** Apple FM is 2× more efficient per token than the GPU-backed runtimes despite producing tokens at ~half the rate. **CoreML/ANE has the lowest *instantaneous* power (12.7 W) but is the *worst* J/tok at 4× Apple FM, because the slower decode (32 tok/s) keeps the package powered up much longer.**"

That last sentence is a genuinely counterintuitive, guide-worthy insight: **low power ≠ low energy.** "The ANE path draws ~half the GPU path's package power at full decode (12.7 W vs ~24.7 W)".

**Mac M4 Max, throughput × energy, best-available builds (2026-07-19, decode-window J/token, warm loads):**

| Build | J/tok (decode) | W (decode) | tok/s |
|---|---:|---:|---:|
| 🟣 MLX PTQ 4-bit | **0.090** 🏆 | 14.6 | **177.8** 🏆 |
| 🟣 MLX QAT OptiQ | 0.106 | 14.6 | 149.5 |
| 🔴 LiteRT wNa8o8 *(WebGPU path)* | 0.154 | 22.2 | 155.0 |
| 🔵 llama.cpp Q4_K_M | 0.170 | 20.5 | 127.1 |
| 🍎 Core AI own int4 *(patched, S=1 window)* | ~0.33 | 18.9 | 53 eff. |

> "**MLX owns the Mac energy Pareto** — fastest *and* most efficient, at the lowest package power."
> "**Core AI pays its S=1 prefill wall in energy too** on the Mac (~2.2× MLX's J/tok at 0.3× the speed) — patched-engine reference row."

### 2.8 iPhone 17 Pro, Gemma 4 E2B, seven runtimes with QUALITY (GSM8K n=100)

This table is the best "which runtime should I actually ship" evidence in existence, because it puts speed, memory, quality, and energy on one axis.

| Runtime | Build | Decode tok/s | ITL p50 | Peak MB | GSM8K | J/tok |
|---|---|---:|---:|---:|---:|---:|
| 🔴 LiteRT-LM | wNa8o8 QAT (official) | **52.7** 🏆 | **17.4 ms** | **487** 🏆 | 86.0% | **0.122** 🏆 |
| 🌵 Cactus | CQ4 **uncalibrated** | 50.6 | 19.6 ms | 1,061 | 87.0% | 0.322 |
| 🟣 MLX-Swift | PTQ 4-bit | 46.4 | 21.5 ms | 3,010 | 84.0% | 0.151 |
| 🔵 llama.cpp | Q4_K_M (PTQ) | 37.6 | 25.5 ms | 253 † | 76.0% | 0.483 |
| 🟣 MLX-Swift | QAT OptiQ int4 | 34.8 | 29.0 ms | 4,650 | **91.0%** 🏆 | 0.207 |
| 🍎 **Core AI** ‡ | own int4 (from official QAT q4_0) | 34.2 | 29.0 ms | 553 † | 88.0% | 0.352 |
| 🔵 llama.cpp | **official QAT q4_0** | **unloadable** | — | — | — | — |
| 🌵 Cactus | **CQ4 as shipped** (`cactus run` default) | 50.2 | 19.8 ms | 1,061 | **3.0%** | — |

🚩 **Core AI footnote ‡ — TTFT is brutal on Gemma 4:**

> "**Patched engine (reference)**: Apple ships no Gemma-4 bundle and **`EngineOptions.staticInputBuffers` is a local engine patch** — but the *path* is Apple's standard `EngineFactory`. **Its TTFT is the honest cost: ~5.1 s on a 19-token prompt (S=1 unbatched prefill — Gemma-4's per-layer embeddings force it).**"

> "† mmap'd weights: clean pages aren't charged to `phys_footprint`, so these 'memory' cells are not comparable with runtimes that wire their weights — footnote, don't rank."

**Verdict quote:**

> "No runtime is Pareto-dominant once quality is on the table: **speed/memory/energy → LiteRT-LM, quality → MLX-OptiQ, balance → Core AI or Cactus-uncalibrated** (Cactus: 0.83× LiteRT's decode at +1 GSM8K pt; **Core AI: +2 pts at 0.65×**)."

**⚠️ Cross-runtime methodological warning worth internalizing** (the "Cactus finding"):

> "'Which file did the runtime hand you' is worth 84 points — the sharpest case yet for stating the build per row."

(Cactus's *shipped default* build scores 3.0% GSM8K; the build they *demoted* scores 87.0%. Same speed, same engine. Also: Google's official QAT GGUF "does not load — llama.cpp aborts on a vocab defect ('empty token at index 237922')". **Shipping an artifact ≠ shipping a usable artifact.**)

**Session-drift honesty note (rare and worth emulating):** "a same-session LiteRT control re-ran at 60.9 decode… vs its published 52.7 — **this device runs ~16% faster today than in the 07-18 session**."

### 2.9 Apple Foundation Models as a measured runtime (reference row)

| Runtime | Model | n | TTFT (ms) | Decode tok/s | Peak Mem (MB, in-process) |
|---|---|---:|---:|---:|---:|
| apple-fm | Apple Foundation Model (default, ~3 B params est.) | 3 | 269 | 85.2 | 27 |

🚩 **Three caveats, all guide-worthy:**

> "- **Tokens are estimated** (`utf8.count / 4`) because **`FoundationModels` does not expose the tokenizer**. Treat decode tok/s as ±20%…
> - **Peak memory is in-process only.** The model lives in Apple's system process, not ours, so **27 MB is the harness overhead — not the true model footprint.**
> - **Quant is Apple-internal.** **Community reverse-engineering puts it at ~2-bit base weights + 4-bit task adapters**; Apple has not published numbers."

Adapter wiring note: `AppleFMRuntime.swift`, "system framework, `#if canImport(FoundationModels)` (macOS 26 / iOS 26)".

### 2.10 Other cross-runtime numbers (M4 Max, short-chat 128 tokens, decode tok/s median)

| Logical model | Params | mlx-swift (Q4) | llama.cpp (Q4_K_M) | coreml-llm | litert-lm |
|---|---:|---:|---:|---:|---:|
| Qwen 2.5 0.5B | 0.5 B | **531.1** | 297.1 | 181.2 (FP16) | n/a |
| Qwen 3.5 0.8B | 0.8 B | **421.1** | 201.1 | 58.2 (INT8) | n/a |
| Qwen 3.5 2B | 2 B | **291.9** | 149.7 | 35.0 (INT8) | n/a |
| Gemma 4 E2B | 2 B | **185.4** | 119.2 | 32.5 (INT4 palettized) | pending |
| Gemma 4 E4B | 4 B | **113.5** | 80.5 | not run | pending |

> "**MLX-Swift now wins decode on every cell** — 1.4×–1.8× over llama.cpp — after upstream `mlx-swift-lm` shipped Qwen + Gemma kernel updates in early 2026 (the Qwen rows roughly tripled vs. the snapshot captured before those landed). **The old 'llama.cpp Metal always wins small-model decode' rule is no longer true on M4 Max; re-measure before quoting it.**"

**Peak memory (MB, median), same models:**

| Logical model | Params | mlx-swift | llama.cpp | coreml-llm |
|---|---:|---:|---:|---:|
| Qwen 2.5 0.5B | 0.5 B | **390** | 538 | 962 |
| Qwen 3.5 0.8B | 0.8 B | **600** | 752 | 221 (INT8) |
| Qwen 3.5 2B | 2 B | 1223 | 1443 | **230** (INT8) |
| Gemma 4 E2B | 2 B | 2829 | 3212 | **1036** |
| Gemma 4 E4B | 4 B | **4376** | 5150 | — |

> "**'CoreML/ANE wins memory' is true once the chunked MLKV layout kicks in.** At 0.5 B params MLX-Swift is still smaller… from 0.8 B onward, CoreML's chunked MLKV path… holds the process RSS roughly flat — 206 MB at 0.8 B, 215 MB at 2 B — while MLX and llama.cpp scale linearly with parameter count."

### 2.11 MLX-specific practical notes from the repo

- Pinned **`mlx-swift 0.31.3`**; issue **mlx-swift#349** ("the MLX Metal bundle not being emitted by `swift build` from a downstream package") is **resolved** on 0.31.3 — `swift build` now emits `mlx-swift_Cmlx.bundle` (carrying `default.metallib`) next to the binary. The old Xcode-target workaround is no longer needed.
- 🚩 **"Build Release for real numbers — a Debug build adds large per-token host overhead and understates decode."** (This is fairness rule #7 and it bit the author's own MLX row.)
- LiteRT-LM SwiftPM caveat: "the released package trips SwiftPM's unsafe-flags rule via its `-all_load`"; vendored as a local package with `GIT_LFS_SKIP_SMUDGE=1`. Watch `-all_load` for duplicate-symbol clashes with vendored `llama`/`executorch` static libs; "fall back to scoped `-force_load`".
- ExecuTorch blocked: "current ET-community models ship SentencePiece `tokenizer.model` but ET's `hf_tokenizer.cpp` expects HF-format `tokenizer.json`."
- ANEMLL blocked: "`swift-huggingface.HFDownloader` fails on `.mlmodelc/` directory-shaped HF repos."
- CoreML-LLM API note: "public API since CoreML-LLM `v1.9.0`" for `Qwen35MLKVGenerator` (ANE chunked decode, **KV in `MLState`**).
- VLM work in progress: `MLXVLMRuntime` (`mlx-community/Qwen3-VL-2B-Instruct-4bit`) vs `CoreMLVLMRuntime` (`.cpuAndNeuralEngine`), measuring **ANE residency via `MLComputePlan`**.
- Devices verified in-tree: `mac-m4-max` (macOS 26), `macbook-air-m3` 16 GB (macOS 26), `iphone-17-pro` (iOS 26 → bumped to 27 for the Core AI work).

---

## 3. InfoQ — "Apple Launches Core AI for Apple-Silicon Optimized On-Device Generative AI" (Grade B)

- URL: https://www.infoq.com/news/2026/06/apple-core-ai-wwdc/
- Author: **Sergio De Simone**, published **2026-06-20**, "2 min read"
- (Note: the jina render is ~200 lines of site nav before the article; body starts at line 239 of the dump.)

**Key claims, verbatim:**

> "At WWDC 26, Apple announced the Core AI framework, **the official successor to Core ML**."

> "Apple says the new Core AI framework provides a unified architecture for deploying models ranging from **compact 3B-parameter vision models to large-scale LLMs, including reasoning models with up to 70B-parameter reasoning models**, across the iPhone, iPad, Mac, and Apple Vision Pro." — linked to `wwdc2026/324/?time=33`, i.e. sourced to a timestamp in the session.

> "Core AI is the technology underpinning Apple Intelligence… Apple is making it available to developers to build what it calls **'custom intelligence'**. Core AI, which **can only run on Apple Silicon**, ensures user data privacy, zero server dependencies, and zero per-token cloud costs."

> "Key Core AI capabilities include **unified hardware access**… a **memory-safe Swift API enabling zero-copy data paths** and fine-grained control over inference memory; and **ahead-of-time (AOT) compilation, which shifts work off the user's device**, yielding near-instant load times."

**Conversion, exact API string:**

> "The simplest approach is exporting a PyTorch as a `torch.export.ExportedProgram` and convert it to a CoreAI **`AIProgram`** using `TorchConverter().add_exported_program(ep).to_coreai()`."

**Authoring path — named composite ops:**

> "you can author a new Core AI model from a PyTorch one using built-in composite ops provided by the library, such as **attention, RoPE embeddings, RMSNorm, and `gather-matmul`**, registering custom lowering function to map new PyTorch ops to **Core AI IR**, or even creating custom Metal kernels for lower-level optimization."

Doc URLs cited: `apple.github.io/coreai-torch/main/guides/composite-ops.html`, `.../guides/custom-metal-kernels.html`, `apple.github.io/coreai-optimization/`, `.../quantization/index.html`, `.../palettization/index.html`.

**Apple quote on compression (blockquote in the article):**

> "Model compression can help reduce the memory footprint of your model (disk size and at runtime), reduce inference latency, reduce power consumption, or optimize them all at once."

**Specialization + cache paragraph (dense with API facts):**

> "One important aspect of running an `AIModel` is its automatic *specialization* to the current hardware and OS version, which is carried through when the model is first loaded into the model cache. As a result, **the first attempt to use a model may take significantly longer than subsequent runs**… Developers can control how and when this process happens by customizing `SpecializationOptions`, accessing the `AICacheModel` [sic — links to `AIModelCache`] to **check whether a model is already available or delete cached ones, and even share the model cache across an app group.**"

> ⚠️ Typo in the source: it writes **`AICacheModel`** but hyperlinks `developer.apple.com/documentation/coreai/aimodelcache`. The correct name is `AIModelCache`. Do not propagate `AICacheModel`.

**Three-framework positioning + the HN/Reddit sourcing (§5):**

> "With the introduction of Core AI, Apple is providing support for three distinct approaches to run ML/AI on its operating systems: **Core ML, Core AI, and MLX Swift.**"

---

## 4. `coreai-torch` official docs (read for grounding the community claims)

- URL: https://apple.github.io/coreai-torch/main/ (Apple-official; included because two community posts reproduce it and I needed to check they did so faithfully)

**Overview, verbatim:**

> "Core AI PyTorch Extensions (`coreai-torch`) is a Python package that bridges PyTorch and Core AI. You can use it to bring up an existing PyTorch model — exported as a `torch.export.ExportedProgram` — into a Core AI `AIProgram` ready to run on Apple hardware, **traversing the FX graph node-by-node and mapping ATen operators to Core AI operations.** You can equally use it to author Core AI models directly from PyTorch by composing the library of composite ops in `coreai_torch.composite_ops`, authoring new ops via `register_torch_lowering`, and authoring inline Metal GPU kernels through `TorchMetalKernel` and `register_custom_kernels`."

**The three-step pipeline, verbatim:**

> "First, export your PyTorch model with `torch.export.export` to capture the computation graph. Second, decompose the exported program with `get_decomp_table()`, which lowers composite ATen ops to the primitive set that `TorchConverter` can map **while preserving the operations that `TorchConverter` lowers as composite ops.** Third, call `TorchConverter().add_exported_program(ep).to_coreai()` to produce the `AIProgram`."

**Composite ops:**

> "`coreai_torch.composite_ops` exposes well-known building blocks — such as **attention, RoPE embeddings, RMSNorm, and gather-matmul (the MoE primitive)** — as PyTorch modules. **Passing these modules to `externalize_modules` preserves each one's operation boundary as a named composite op that the compiler can recognize and optimize.**"

**Official quickstart** (jina stripped the newlines; `avinashsangle.com` reproduces it correctly formatted, and I verified token-for-token that the two agree):

```python
import torch
from coreai_torch import TorchConverter, get_decomp_table

# 1. Export the PyTorch graph with torch.export
model = MyModel().eval()
ep = torch.export.export(model, args=(torch.randn(1, 10),))

# 2. Lower composite ATen ops using Core AI's decomposition table
ep = ep.run_decompositions(get_decomp_table())

# 3. Convert to a Core AI program, then specialize for Apple Silicon
coreai_program = TorchConverter().add_exported_program(ep).to_coreai()
coreai_program.optimize()
```

**Entry-point decision table** (as relayed by avinashsangle from the docs' "Choosing your workflow" table, which jina truncated):

- "Already have a decomposed `ExportedProgram`? Use `add_exported_program(ep)`."
- "Have a plain `nn.Module`? Use `add_exported_program()` or `add_pytorch_module()`."
- "Need to keep submodules separate? Use `add_pytorch_module(..., externalize_modules=[...])`."

**Named API surface collected across sources:** `TorchConverter`, `.add_exported_program(ep)`, `.add_pytorch_module(..., externalize_modules=[...])`, `.to_coreai()`, `AIProgram`, `.optimize()`, `get_decomp_table()`, `register_torch_lowering()`, `register_custom_kernels()`, `TorchMetalKernel`, `coreai_torch.composite_ops`.

**Related Apple packages named by community sources:** `apple/coreai-models`, `apple/coreai-torch`, `apple/coreai-optimization` (a.k.a. `coreai-opt`), `coreai-core`.

---

## 5. ⭐ HACKER NEWS — practitioner opinion (Grade B as opinion)

Story 48449665. Two comment subtrees, fetched via the HN Algolia API (`hn.algolia.com/api/v1/items/<id>`).

### 5.1 Comment 48459443 — user **ABS** (the doc-reading that corroborates the WWDC lab paraphrase)

> "looks to me like the docs don't give a feature-parity table, but they do draw the 'role' lines once you read across them:
> - **Core ML narrows to classic, non-neural ML** (its own docs now point you there for "decision trees or tabular feature engineering")
> - **Core AI takes neural nets and transformers** (the new .aimodel format, the new profiler)
> - **MLX stays the separate bring-your-own-weights track** (its WWDC sessions draw no line back to Core AI at all)
> **coreai-opt is the successor to coremltools on the optimization side.**"

Two things here are load-bearing: (a) an independent reader reached the *same* Core ML→classic-ML conclusion as the WWDC lab paraphrase in §1.1.4; (b) the **`coreai-opt` ⇒ successor to `coremltools`** mapping, which no article states outright.

### 5.2 Comment 48454273 subtree — the MLX/ANE argument

**LoganDark:**
> "My reading of it is:
> - Core ML is for models designed only for Apple platforms
> - **MLX is for models that don't need to be fast**
> - Core AI is for models that run everywhere already and also need to be fast"

**wahnfrieden (dissent):**
> "I use CoreML for models designed for other platforms. I port the models to it but it works for that without much trouble. **MLX is not for end user deployment.**"

**jkman (⭐ the key technical claim):**
> "This view is a bit off. First, keep in mind that **MLX was and will not be able to access the ANE, so it's a total non-starter for anything user-facing.** Based on updates to coreml docs, they're trying to sell **CoreML as the tool for tabular or domain-specific applications and CoreAI for NNs moving forward.**"

**LoganDark (reply):**
> "> keep in mind that MLX was and will not be able to access the ANE
> That's the rationale behind it not being fast.
> > so it's a total non-starter for anything user-facing
> Yep."

> **Assessment:** "MLX cannot access the ANE" is **community-asserted, not Apple-official**, but it is consistent with the benchmark repo's independent finding that MLX is a GPU-path runtime that throttles like one (§2.6). The stronger claim — "MLX is not fast" — is **contradicted** by the same repo's Mac data (§2.7: MLX owns the Mac energy Pareto AND is fastest at 177.8 tok/s). Treat "MLX is slow" as folklore; "MLX is GPU-only and therefore throttles + burns battery on phones" is the defensible version.

### 5.3 Reddit (via InfoQ; **direct fetch blocked**)

InfoQ quotes r/iOSProgramming thread `1u1nfxr` comment `or7429o`:

> Core AI "makes it easier to incorporate high-performance LLMs", but its long-term value will depend "on the future growth of the official Core AI/community".

🚩 I attempted `https://www.reddit.com/r/iOSProgramming/comments/1u1nfxr.json` and got a non-JSON body (Reddit blocks unauthenticated programmatic reads). **Flagged as NOT RETRIEVED** — see §10. The forums agent should own this.

---

## 6. wccftech — the "converges to a near-tie" framing (Grade C, but derived from Grade A data)

- URL: https://wccftech.com/apples-new-coreai-engine-barely-edges-out-its-own-mlx-framework-at-realistic-8b-model-sizes-despite-being-2-47x-faster-on-tiny-models/
- Published 2026-06-10. Author Rohail Saleem. It is **entirely** a restatement of §2's benchmark repo (which it links).

Useful because the headline is the correct takeaway most other coverage missed:

> "for small models such as the 0.6-billion-parameter Qwen3, CoreAI is around **2.47x faster** on decoding tasks than MLX on an M4 Mac. Similarly, on an iPhone 17 Pro, CoreAI is around **1.6x faster** than MLX on decoding… However, when model size increases to a more practical 8 billion parameters (Qwen3 8b, M4 Max Mac), **CoreAI is only 1.05x faster than MLX**, and offers a near-parity decoding performance."

> "on sustained workloads on the iPhone 17 Pro, **the GPU throttles relatively quickly, allowing the CoreML/Apple Neural Engine combo to sprint ahead in terms of performance retained.**"

> "Google's LiteRT-LM engine running its Gemma model was not only the fastest engine on the iPhone 17 Pro (**55.4 tokens per second**), but it also used **4.5× less RAM than Apple's own MLX framework (641 MB vs 2,900 MB)**."

> "Apple Foundation Models were found to be '**2× more energy-efficient per token than the GPU-backed runtimes, 4× more than CoreML/ANE.**'"

Editorial line worth keeping: "**Engines optimized to specific vendor-sourced models almost always trump general engines.**"

(Note: wccftech's 55.4 tok/s / 641 MB LiteRT figures come from a slightly different capture than the 52.7 / 487 in §2.8 — the repo refreshed. Prefer the repo.)

---

## 7. FOUNDATION MODELS iOS 27 — community coverage

### 7.1 dev.to / arshtechpro — "Apple Just Opened the Foundation Models Framework to Any LLM Provider" (Grade B) ⭐

- URL: https://dev.to/arshtechpro/wwdc-2026-apple-just-opened-the-foundation-models-framework-to-any-llm-provider-5ejn
- Published **2026-06-11**. Covers **WWDC26 session 339** ("Bring an LLM provider to the Foundation Models framework").
- **This is the richest FM API source in the community corpus.** Signatures below are the author's transcription of session code.

**The four model sources, one session API:**

```swift
// The existing on-device model — free, private, offline
let model = SystemLanguageModel()

// Apple's cloud model — 32K context, reasoning, Private Cloud Compute privacy guarantees
// let model = PrivateCloudComputeLanguageModel()

// A model you package and distribute via Swift Package Manager
// let model = try await CoreAILanguageModel(resourcesAt: modelURL)

// Any MLX-format model from HuggingFace
// let model = MLXLanguageModel(modelID: "mlx-community/my-model")

let session = LanguageModelSession(model: model)
let response = try await session.respond(to: "Summarize this contract.")
```

⭐ **`CoreAILanguageModel(resourcesAt:)` and `MLXLanguageModel(modelID:)` are the bridge types** between Core AI / MLX and Foundation Models. Independently corroborated by avinashsangle (§7.2), which shows the same `CoreAILanguageModel(resourcesAt:)` initializer. **This is the single most important cross-framework fact in the corpus.**

**The two provider protocols:**

```swift
// LanguageModel: declare capabilities and hand the session a configuration
public struct MyLanguageModel: LanguageModel {
    typealias Executor = MyLanguageModelExecutor

    public var capabilities: LanguageModelCapabilities {
        LanguageModelCapabilities(capabilities: [.toolCalling, .guidedGeneration, .reasoning])
    }

    public var executorConfiguration: Executor.Configuration {
        Executor.Configuration(/* API endpoint, auth, model variant, etc. */)
    }
}

// LanguageModelExecutor: translate the framework's request into your model's wire format
public struct MyLanguageModelExecutor: LanguageModelExecutor {
    public typealias Model = MyLanguageModel

    public init(configuration: Configuration) throws { }

    public func respond(
        to request: LanguageModelExecutorGenerationRequest,
        model: MyLanguageModel,
        streamingInto channel: LanguageModelExecutorGenerationChannel
    ) async throws { }
}
```

**Why the split (executor caching!):**

> "A single model type can have multiple executor configurations — for example, a fast tier and a quality tier backed by the same model family. **The session caches executor instances per configuration, so if a developer creates two sessions with identical configurations, they share an executor.**"

**`prewarm`:**

```swift
func prewarm(transcript: Transcript) {
    loadedModel = try? loadWeights()
}
```
> "`prewarm` is called before the first request arrives. For a local model that loads weights from disk, use it to get weights into memory… For a remote API, you might warm a connection pool here or do nothing at all."

**`Transcript.Entry` cases (verbatim comment block):**

```swift
// Transcript.Entry cases you will encounter:
// .instructions  → system prompt
// .prompt        → user message
// .toolCalls     → model-initiated tool invocations
// .toolOutput    → results from those tool calls
// .response      → assistant turn
```

**Streaming channel — three phases (metadata → usage → text deltas):**

```swift
func respond(to request: ..., streamingInto channel: ...) async throws {
    // Tell the framework what model/request handled this
    await channel.send(.response(action: .updateMetadata([
        "modelID": "my-model-2026",
        "requestID": request.id.uuidString
    ])))

    // Report input token count before generating
    await channel.send(.response(action: .updateUsage(
        input: .init(totalTokenCount: promptTokens, cachedTokenCount: cachedTokens),
        output: .init(totalTokenCount: 0, reasoningTokenCount: 0)
    )))

    // Stream tokens as they arrive
    for try await token in modelStream {
        await channel.send(.response(action: .appendText(token)))
    }
}
```

Channel actions seen: `.updateMetadata([String: String])`, `.updateUsage(input:output:)`, `.appendText(_)` and `.appendText(_, tokenCount:)`, `.updateCustomSegment(_)`. Usage structs carry `totalTokenCount`, `cachedTokenCount`, `reasoningTokenCount`.

**Unsupported-option policy — "approximate where you can, throw where you cannot":**

```swift
// Caller requested greedy sampling, your API only takes temperature — close enough
if request.generationOptions.sampling?.kind == .greedy {
    apiRequest.temperature = 0
}

// Schema + tiny token budget is genuinely unsatisfiable — throw
if let schema = request.schema,
   let budget = request.generationOptions.maximumResponseTokens,
   budget < minimumTokensNeeded(for: schema) {
    throw LanguageModelError.unsupportedCapability(
        .init(capability: .guidedGeneration,
              debugDescription: "Token budget too small for this schema.")
    )
}
```

**Typed error cases named:** `contextSizeExceeded`, `rateLimited`, `refusal`, `guardrailViolation`, `timeout`, `unsupportedCapability`. Plus: "Your own provider-specific errors… can be thrown as custom `Error` types. Give them a proper `errorDescription`; that string surfaces in developer-facing tooling."

**`Transcript.CustomSegment` — non-text payloads in the transcript:**

```swift
public struct AudioSegment: Transcript.CustomSegment {
    public var id: String
    public var content: URL
}

// In a session
let recording = AudioSegment(id: UUID().uuidString, content: audioFileURL)
let response = try await session.respond {
    "Transcribe the key decisions from this meeting."
    recording
}

// In the executor, emit back
await channel.send(.response(action: .updateCustomSegment(
    AudioSegment(id: outputFile.id, content: outputFile.url)
)))
```

Note the **result-builder prompt syntax** (`session.respond { "text"; segment }`) — corroborated by byteiota's image-attachment example (§7.4).

**Server-side tools (NOT client `Tool` conformances):**

```swift
public struct MyLanguageModel: LanguageModel {
    public struct ServerTool: Sendable {
        public static let webSearch: ServerTool = ...
    }
    public init(serverTools: [ServerTool] = []) { }
}

// Executor routes server events to the channel
for try await chunk in apiResponse {
    switch chunk {
    case .webSearch(let result):
        await channel.send(.response(action: .updateCustomSegment(
            WebSearchSegment(url: result.url, content: result.html)
        )))
    case .textDelta(let delta):
        await channel.send(.response(action: .appendText(delta.text, tokenCount: delta.tokenCount)))
    }
}
```

**Packaging guidance from the session:**

```swift
// Package.swift structure Apple recommends
targets: [
    .target(name: "MyModelRuntime"),          // inference engine, weights loader
    .target(name: "MyModel", dependencies: ["MyModelRuntime"]),  // public LanguageModel conformance
    .testTarget(name: "MyModelTests", dependencies: ["MyModel"])
]
```

- "Foundation Models supports iOS, macOS, visionOS, and **watchOS**. The Foundation Models framework is being **released as open source**, so your package could also be useful to developers who deploy **Swift on Linux servers** — consider supporting Linux too."
- "Every dependency translates to bytes that a developer ships to their users… **A bloated transitive dependency graph is a fast way to get your package rejected from app codebases.**"
- "Design initializers that guide developers toward secure usage rather than plain API key strings — **persist tokens via Keychain** rather than accepting them as plain strings."

**Partners named:** "Gemini models are available through the **Firebase Apple SDK**… **Anthropic is also listed as a launch partner.**"

**Editorial framing worth quoting:**
> "What Apple has built here is less a feature and more a **distribution channel**."
> ⚠️ Note: this author says the on-device model "is about 3B parameters" in one paragraph and "A 20B sparse model on a phone" in another — internally inconsistent. Both figures appear elsewhere (3B = AFM Core; 20B sparse = AFM Core Advanced), so it's likely conflation of two model tiers rather than error, but **do not cite this article for parameter counts.**

### 7.2 avinashsangle — "Apple Core AI: Run Open-Weight Models On-Device for Free" (Grade C)

- URL: https://avinashsangle.com/blog/apple-core-ai-on-device-inference-guide — published **2026-06-20**, "12 min read"

**Faithfully reproduces the official `coreai-torch` quickstart** (verified against §4 — token-for-token match). Its unique contributions:

**⭐ Core AI models plug into `LanguageModelSession`** (cites WWDC **session 326**, "Integrate on-device AI models"):

```swift
import FoundationModels
import CoreAILanguageModels

// Load a converted or pre-packaged model from disk
let model = try await CoreAILanguageModel(resourcesAt: qwenModelURL)

// Drive it with the familiar Foundation Models session API
let session = LanguageModelSession(model: model)
let response = try await session.respond(to: "Summarize this changelog in 3 bullets.")
print(response.content)
```

⭐ **Module name `CoreAILanguageModels`** (plural) — the only place in the corpus that names the import.

**Structured output works identically for Core AI-backed models:**

```swift
@Generable
struct VocabCard {
    let word: String
    let meaning: String
    let exampleSentence: String
}

let response = try await session.respond(
    to: "Create a vocab card for the word 'flower'",
    generating: VocabCard.self
)
let card: VocabCard = response.content
```

> "In the 'Integrate on-device AI models' session (WWDC session 326), Apple shows you import `FoundationModels` and get **the same session, the same streaming, and the same structured output, while choosing exactly which model runs underneath.**"

**Pre-converted models as SwiftPM packages:**

```swift
// Add a pre-converted Core AI model as a package dependency
dependencies: [
    .package(
        url: "https://github.com/apple/coreai-models",
        from: "1.0.0"
    )
]

// Then add the specific model product to your target, e.g. a Qwen text model
// or the SAM3 segmenter, per the package's product list.
```

> "The launch set includes popular open-weight families: **Qwen and Mistral for text generation, and SAM3 for image segmentation**, with more from the research community."

**Vision entry point:** "SAM3, for example, loads through an **`ImageSegmenter`** and returns segment masks for a prompt."

**`coreai-optimization`:** "provides **quantization and palettization**… Quantization lowers the numeric precision of weights, for example from 16-bit floats down to 4-bit integers… **Palettization goes further by mapping weights to a small shared lookup table.**" Practical advice: "quantize, measure output quality on a held-out set, and back off if the quality drop is unacceptable."

**Honest caveat the author flags himself:**
> "Apple does not list exact macOS, Python, or Xcode minimums on the overview pages, so check the Installing and Quickstart guides for the current toolchain before you start."

**Opinion — profiling:** "**profile before you optimize.** It is easy to assume a model is slow because of one big layer when the real cost is a memory copy or an op that fell back to the CPU."

**Cost framing (the most cited community argument for Core AI):**
> "'free' is only free at the margin. You pay up front in device memory, battery, and the engineering time to convert and quantize a model so it fits. **The hardware is the cost; the requests are free.**"

**On-device vs cloud split:** "**On-device (Core AI):** privacy-sensitive data, offline use, high-volume cheap calls, latency-critical UI, no per-token bill. **Cloud (Claude, Gemini, etc.):** frontier reasoning, huge context, cross-platform reach, models too large to fit a device."

### 7.3 andrew.ooo — three-layer comparison (Grade C-)

- URL: https://andrew.ooo/answers/apple-core-ai-vs-foundation-models-vs-mlx-ios-27-framework-june-2026/ — "Last verified: June 15, 2026"

🚩 **CONTAINS AN ERROR: it repeatedly says `.aiasset`** ("You bring your own (.aiasset)", "load an `.aiasset` model file", "Direct export paths to `.aiasset` for Core AI deployment"). **The format is `.aimodel` / `.aimodelc`.** Every other source agrees. Do not propagate `.aiasset`.

Useful anyway for its layer table:

| Layer | Surface | Model | Who decides quantization | Use case |
|---|---|---|---|---|
| Foundation Models | High-level Swift API | Apple's on-device LLM (sealed) | Apple | Default LLM features in any app |
| Core AI | Mid-level Swift API | You bring your own | You, via `SpecializationOptions` | Ship custom/third-party LLM on-device |
| Core ML | High-level Swift API | You bring your own (converted `.mlmodel`) | Core ML converter | Traditional ML — vision, audio, classification |
| MLX | Python + Swift framework | Anything you build | You | Training, research, model conversion |

**Its decision flow (community-authored, not Apple):**
```
Question 1: Does Foundation Models do what you need?
  Yes → Foundation Models. Done.
  No  → Continue.
Question 2: Do you need to ship a specific model?
  Yes → Core AI (production), MLX (build pipeline).
  No  → Continue.
Question 3: Is your model a converted traditional-ML pipeline?
  Yes → Core ML.
  No  → Core AI is probably the right answer.
Question 4: Are you training or doing research?
  Yes → MLX.
```

**Key opinion — MLX is a build-time tool, not a shipping runtime:**
> "**You don't ship MLX in a consumer app** — you use MLX in your build pipeline to produce the model file that Core AI loads."

(Consistent with wahnfrieden on HN: "MLX is not for end user deployment." **Contradicted** by §2, which ships MLX-Swift in an iOS app and measures it — so this is an *opinion about what's wise*, not a technical limitation.)

**Sizing table (UNVERIFIED — no methodology given; compare with §2's measured numbers, which are far more conservative):**

| Device | Unified RAM | Comfortable on-device model size |
|---|---|---|
| iPhone 17 Pro | 12 GB | 7B-13B at 4-bit |
| iPhone 17 (non-Pro) | 8 GB | 3B-7B at 4-bit |
| iPhone 16 series (most) | 8 GB | 3B-7B at 4-bit |
| iPad Pro M5 | 16 GB | 13B-30B at 4-bit |
| MacBook Pro M5 Max | 64-128 GB | 70B+ at 4-bit |

> ⚠️ "iPhone 17 Pro / 12 GB" is plausible but unsourced. §2 measured a **0.6B** model using 524 MB–1.17 GB on that device and hitting a jetsam wall on deep runs — treat "7B-13B comfortable on a phone" with heavy skepticism.

**Deprecation status:** "Existing Core ML deployments stay valid. **Apple has not announced a deprecation timeline.**"

**Cross-platform note:** "ONNX Runtime, llama.cpp, MLC LLM all work on Apple silicon but **bypass Apple's Neural Engine**; Core AI is the right choice when you want NPU acceleration."

### 7.4 byteiota — "Apple Foundation Models WWDC 2026: Multimodal + Python SDK" (Grade C-)

- URL: https://byteiota.com/apple-foundation-models-wwdc-2026-multimodal-python-sdk/ — 2026-06-09. Author byline is a mascot ("ByteBot"), so treat with care; but several claims are independently corroborated by atalayasoft (§7.6).

**Provider-swap sketch:**
```swift
// Apple's on-device model — free, no network required
let session = LanguageModelSession()

// Switch to Gemini via Firebase AI Logic
let geminiModel = GeminiModel(apiKey: .keychain)
let session = LanguageModelSession(model: geminiModel)

// Switch to Claude via Anthropic Swift package
let claudeModel = ClaudeModel(apiKey: .keychain)
let session = LanguageModelSession(model: claudeModel)
```
⚠️ `GeminiModel` / `ClaudeModel` / `.keychain` are **UNVERIFIED** — likely illustrative, not real type names. dev.to (§7.1) says Gemini ships "through the Firebase Apple SDK", which implies a Firebase-namespaced type instead.

**Image input (this API shape IS corroborated by atalayasoft and the WWDC search snippet):**
```swift
let response = try await session.respond {
    "What animal is this?"
    Attachment(UIImage(named: "photo.jpg")!)
}
```
> "Supported types include **UIImage, NSImage, CGImage, Core Image, CoreVideo pixel buffers, and file URLs.**"

🚩 **Claimed gate:** "image input requires **AFM 3 Core Advanced**, the new **20-billion parameter sparse** model that ships on **high-end devices only**." — **UNVERIFIED**, and in tension with the WWDC search snippet which said images work "at any size" without naming a device gate.

**AFM 3 architecture claim:** "all 20 billion parameters live in flash storage, but only **1–4 billion activate** at inference time depending on request complexity. It is a genuine mobile-optimized mixture-of-experts architecture." Cites `machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models` with preference numbers: "**AFM 3 Core achieving 45.6% preference over the 2025 baseline, with AFM 3 Cloud jumping from 8.7% to 64.7% preference.**" (Should be checked against the actual Apple research paper by whoever owns that.)

**Python SDK sketch (UNVERIFIED module name `apple_fm_sdk`):**
```python
import apple_fm_sdk as fm

model = fm.SystemLanguageModel()
available, reason = model.is_available()

session = fm.LanguageModelSession(model=model)
response = await session.respond(prompt="Summarize this document.")
```

**⭐ `fm` CLI on macOS 27** — corroborated by atalayasoft AND by the Evaluations-framework search snippet, so this one is likely real:
> "macOS 27 also ships a new `fm` CLI tool. **`fm chat`** opens an interactive terminal session with the on-device model; shell scripts can pipe through it."
> (atalayasoft adds the subcommands: "`fm respond/chat/schema`, on-device or PCC")

**⭐ Three built-in system tools** (also flagged by atalayasoft as "Local RAG with Spotlight"):
- **Spotlight Search Tool** — "local retrieval-augmented generation using the device's existing Spotlight index. **No embeddings, no vector database, no setup.** RAG in two lines of Swift."
- **OCRTool** — "Vision-backed text extraction from images, results passed directly to the LLM for reasoning."
- **BarcodeReaderTool** — "Barcode and QR code reading fed into the model context."

**What Apple still doesn't give you:**
> "**You cannot swap in custom model weights** [in Foundation Models]… If your use case requires a domain-specific model, you are looking at Core AI."
> "EU and China users do not get the new Siri AI features yet… **The Foundation Models developer API is not affected by this restriction.**"

### 7.5 byteiota — "Apple Core AI Replaces Core ML in iOS 27" (Grade C-, PRE-WWDC SPECULATION)

- URL: https://byteiota.com/apple-core-ai-replaces-core-ml-ios-27/ — published **2026-06-03**, i.e. **five days BEFORE the keynote.**

🚩 **This is a rumor piece written in the confident present tense.** It sources 9to5Mac (2026-03-01) and AppleInsider (2026-03-01) rumor reports. Its predictions were partly right (Core AI exists, third-party model support, MCP, multimodal FM) and partly wrong/unconfirmed (it claims Core AI itself "handles both on-device and cloud AI execution — with the system automatically routing inference", which is actually a Foundation Models behavior, not Core AI's).

Genuinely useful bits:

**Why Core ML aged out (good historical framing):**
> "Core ML was designed for **batch inference on deterministic models** — not autoregressive token generation, streaming responses, multi-turn sessions, or tool calling. **Converting even a modest 7B LLM to .mlmodel format through coremltools was unreliable at best, broken at worst.** Apple's own Foundation Models framework, shipped at WWDC 2025, **had to be built alongside Core ML rather than on top of it** — because Core ML simply could not handle LLM-native patterns."

**Migration reassurance (matches andrew.ooo):**
> "Existing .mlmodel and .mlpackage files continue to work in iOS 27. Apple's deprecation cycles are long… The trajectory will resemble **UIKit and SwiftUI: both coexist for years, but every new platform capability ships in the new framework, and the old one quietly stops receiving investment.**"

**ANE scaling datapoint:** "Apple's Neural Engine grew from **600 billion operations per second on the A11 in 2017 to 38 trillion** on current hardware."

**genai.apple.com subdomain** registered pre-WWDC (macrumors 2026-05-23).

### 7.6 atalayasoft — "WWDC 2026 and AI on iOS" (Grade C+) ⭐ best non-API context

- URL: https://www.atalayasoft.com/blog/wwdc-2026-ai-on-ios-agentic-xcode-and-foundation-models — 2026-06-16. Spanish consultancy, enterprise/CTO angle. Includes **own screenshots** of the Xcode 27 beta.

**Careful rumor-vs-confirmed discipline (rare and worth emulating):**
> "Apple confirms that its next-generation models were *built in collaboration with Google and its Gemini models*, that queries are anonymised, decoupled from the Apple ID, and that **Google is contractually barred from training on them.** What is **press reporting, not Apple confirmation** (via Bloomberg / Mark Gurman): a ~1.2-trillion-parameter model, a cost of ~$1bn/year and execution on Google Cloud GPUs. I'd treat that with caution… **'Apple trained *with* Gemini' is not the same as 'Siri *is* Gemini'.**"

**Foundation Models feature list (corroborates §7.4 on several points):**
- "**Multimodal input:** you can pass it images (`UIImage`, `CGImage`, video buffers, file URLs)"
- "**A single API for every provider.** Through a new `LanguageModel` protocol, the same call site serves the on-device model, Private Cloud Compute, models you bundle yourself locally on the Neural Engine (Core AI) or from the community (MLX), and external providers"
- "**Dynamic Profiles:** switch model, tools or system instructions on the fly, **without going through App Store review.**"
- "**Access outside Xcode:** an `fm` CLI preinstalled on macOS 27 (`fm respond/chat/schema`, on-device or PCC) and a **Python SDK (Apple Silicon)** for prototyping and building evaluation pipelines."
- "**The Private Cloud Compute model is a reasoning model:** a **32,000-token context window** and configurable *reasoning* levels… **no prompt storage.**"
- "**Local RAG with Spotlight**"
- "**No cloud API cost** for apps enrolled in the App Store Small Business Program with **fewer than 2 million total first-time downloads**: the Private Cloud Compute server model is available with a **per-user daily limit, extendable with iCloud+.** You request it on Apple's developer website." (techjacksolutions independently confirms this from the Apple Newsroom press release.)

Code sample:
```swift
// Same call, different backend. Start on-device,
// scale to cloud without touching the call site.
let session = LanguageModelSession(model: .systemDefault)

let classification = try await session.respond(
    to: "Classify this incident and extract the key fields.",
    generating: IncidentClassification.self
)
```
(⚠️ `.systemDefault` as a `model:` argument is unverified; dev.to shows `SystemLanguageModel()` instead.)

**⭐ Evaluations framework + trajectory testing:**
> "this year Apple shipped **not one but two validation frameworks. Evaluations**, to measure model output beyond what unit tests catch; and **AppIntentsTesting**, to exercise your intents in isolation, with no Siri in the loop… And on the agentic side there's one more step: **Evaluations doesn't stop at scoring the output; trajectory expectations verify that the model calls the right tools, with the right arguments and in the right order, and that it doesn't make calls it shouldn't.**"
> "the agentic world opens a new security surface — **indirect prompt injection, actions with side effects** — and Apple devotes a whole session to it, with mitigations such as **risk-based confirmations and lock-screen authentication.**"

**⭐ SiriKit formally deprecated:**
> "**SiriKit (2016) is now formally deprecated.** From now on, the only way for Siri to reach your app is through **App Intents.** Apps that don't expose App Intents are, quite simply, invisible to the new Siri. There's a migration window of around **2-3 years (somewhere around iOS 29)**… App Intents has gained richer entity types, streaming responses, multi-turn follow-ups, a new view-annotation API… and — this matters for regulated sectors — **per-intent privacy manifests**, where you declare whether an interaction may go to the cloud or must stay on-device."

```swift
struct FindTransactionIntent: AppIntent {
    static let title: LocalizedStringResource = "Find transaction"

    @Parameter(title: "Description")
    var description: String

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let transactions = try await Transactions.find(matching: description)
        return .result(dialog: "I found \(transactions.count) transactions.")
    }
}
```

**Xcode 27 agentic detail (from own screenshots):** agents from Anthropic (Claude), Google (Gemini), OpenAI (GPT/Codex); `/plan` command; **official Agent Skills**; MCP with GitHub and Figma connectors; Claude Agent model selector showing "**Default, Opus, Opus + Sonnet, Sonnet**"; Device Hub for driving the simulator.

**EU nuance:** "**Siri AI doesn't arrive at launch in the EU on iPhone and iPad** (Apple cites the **Digital Markets Act**), and European developers **can't even test those features during development.** Careful: this is the **DMA**, not the EAA… The good news is that the **Foundation Models API does work across the whole EU.**"

**The article's central thesis (useful editorial for a "how to adopt" guide):**
> "**AI has shifted the bottleneck: it's no longer in writing the code, it's in validating that what's been written holds up in production.**"

Cites community voices: Antoine van der Lee/SwiftLee (AI Swift code that compiles but "leaks memory, retains reference cycles or gets threading wrong"), Donny Wals (agentic delivery pipeline), Paul Hudson (open-source SwiftUI *agent skill* to "detect and fix the typical mistakes Claude, Codex and Gemini make").

### 7.7 techjacksolutions (Grade C) — press-release restatement

- URL: https://techjacksolutions.com/ai-brief/apple-foundation-models-api-developers-ios-27-reported/ — 2026-07-13. Sourced to `apple.com/newsroom/2026/06/apple-aids-app-development-with-new-intelligence-frameworks-and-advanced-tools/`.

**Betas listed:** "iOS 27, iPadOS 27, macOS 27, watchOS 27, tvOS 27, visionOS 27, and Xcode 27… starting [June 8, 2026]."

**Google/Apple deal:** "Apple and Google announced in **January 2026** that these models would be based on Google's Gemini models and cloud technology" (cites the joint Google/Apple statement).

**Small Business Program tier:** "those enrolled in the App Store Small Business Program with **fewer than 2 million total first-time App Store downloads** can access the next generation of Apple Foundation Models running on **Private Cloud Compute at no cloud API cost.**"

**Core AI one-liner:** "A separate new framework, Core AI, is designed for developers who want to run their own custom models on device. Core AI provides an architecture optimized for the **unified memory and Neural Engine** of Apple silicon, allowing developers to deploy **full-scale LLMs locally.**"

**Xcode 27 packaging facts:** "Xcode 27 is now **Apple silicon only, 30 percent smaller**… **Xcode Cloud is now up to 2x faster**, with new support for apps using Metal and for visionOS builds." Agents can "run autonomously for longer, including writing and running tests, trying ideas in Playgrounds, and interacting with the simulator through a new **Device Hub**." Extensible with "**custom skills**", MCP, and "agents compatible with the **Agent Client Protocol**". "GitHub and Figma are the first to offer seamless installation."

**Its own honest open questions (good list):**
> "- What is the capability ceiling for on-device Apple Intelligence models, which tasks can they handle reliably before the routing framework offloads to cloud providers?
> - What entitlements and App Store review implications come with Foundation Models API access?
> - Does the model routing framework introduce latency overhead that offsets the on-device speed advantage for real-time inference use cases?"

---

## 8. Core AI Debugger — what community sources say

Consolidated (Appcircle §1.2, Crosley §1.1.6, avinashsangle §7.2, plus a WebSearch result summarizing Apple's `inspecting-debugging-and-profiling-core-ai-models` doc):

- **Standalone macOS app**, distinct from Xcode.
- Views named (per the search summary of Apple's doc page): **navigator (PyTorch module hierarchy), structure viewer (operation graph), source viewer (original Python code), inspector (tensor details)**.
- Capabilities: "visualize your model's structure in an easy-to-understand graph format, **execute your model on specific hardware for true runtime results**, and **validate inference correctness against a reference run**"; "**run a model on-device to inspect intermediate tensor outputs**".
- ⭐ **Traces converted ops back to original Python source** (Appcircle) — the standout feature.
- Companion tools: **Xcode Core AI debug gauge** (live load/specialization/inference activity during a debug session) and **Core AI Instruments template** (execution timing across CPU/GPU/ANE).

> ⚠️ No community source I found has actually *used* the Core AI Debugger and written about it. All descriptions are restatements of Apple's docs/session. **There is a real content gap here.**

---

## 9. ⚠️⚠️ UNRELIABLE SOURCES — DO NOT USE (documented so no one re-adds them)

### 9.1 aimadetools.com — "What is Apple Core AI: On-Device LLMs Without API Costs (2026)"

URL: https://www.aimadetools.com/blog/what-is-apple-core-ai/ (published 2026-06-09)

**This article is largely fabricated.** Demonstrable errors:

| Claim in article | Reality (per every other source) |
|---|---|
| Model format is **`.coreaimodel`** | It is **`.aimodel`** / **`.aimodelc`** |
| `coreai-torch` is a **CLI**: `coreai-torch convert --model ./my-model.pt --architecture transformer --output ./MyCustomLLM.coreaimodel` | `coreai-torch` is a **Python package**; the real API is `TorchConverter().add_exported_program(ep).to_coreai()` |
| `coreai-optimization quantize --model … --precision int4 --calibration-data … --output …` | No such CLI attested anywhere |
| Swift API: `CoreAIModel(named:)` + `model.generate(prompt:parameters:)` returning `.text` | Real types are `AIModelAsset`/`AIModel`/`InferenceFunction`; no `generate(prompt:)` |
| "The runtime ships with **iOS 20, macOS 17, iPadOS 20, and visionOS 4**" | **iOS 27 / macOS 27 / visionOS 27.** These version numbers do not exist. |
| Benchmark table: iPhone 16 Pro 8 GB "15-25 tok/s", Mac Studio M4 Ultra 192 GB "60-100 tok/s", etc. | No methodology, no model named, no source. **Contradicted** by §2's measured data. |
| "First token latency for a 3B model on iPhone 16 Pro is **under 200ms**" | Unsourced |
| "Expect **20-30% better battery life** compared to running the same model through generic Metal compute" | Unsourced; §2.7 measured energy and found a far more complicated picture |

**Verdict: DO NOT CITE.** The `iOS 20` line alone is disqualifying — it's a tell that the text was generated without grounding.

The *only* things in it worth noting (and only because they're corroborated elsewhere): the layer diagram (`Your App → Foundation Models API → Core AI → Apple Silicon`), and the Ollama comparison framing ("If you're shipping an iOS/iPadOS app with on-device AI, Core AI is the only first-party option"). Even those should be re-sourced.

### 9.2 chatforest.com — "Apple Foundation Models in iOS 27: The Complete Builder Guide"

URL: https://chatforest.com/builders-log/apple-foundation-models-ios-27-on-device-llm-api-builder-guide/ (2026-06-08)

**The article self-declares AI authorship** in its own footer:

> "*This article was written by Grove, an AI agent operating ChatForest.*"
> "This article was written by an AI agent. ChatForest is an AI-native publication."

Credit for transparency, but it means every claim needs independent verification, and several fail:

- Says Foundation Models "was introduced at **WWDC 2025**" (correct) but then repeatedly refers to "**the iOS 18 model**" and "code written for **iOS 18** Foundation Models" — iOS 18 predates the framework entirely. Confused.
- **Invents an on-device fine-tuning API** with no corroboration anywhere in the corpus:
  ```swift
  let adapter = try await LanguageModelAdapter.train(
      examples: examples,
      configuration: .init(epochs: 3, learningRate: 1e-4)
  )
  try adapter.save(to: adapterURL)
  let session = LanguageModelSession(adapter: adapter)
  ```
  with `FineTuningExample(prompt:completion:)`, "training times under 10 minutes… on A17 Pro and later", "Training is paused when battery is below 20%", "**Adapter size is capped at 50MB**". **None of this is attested by any other source**, and no other WWDC26 coverage mentions on-device LoRA training in Foundation Models. Treat as **fabricated until proven otherwise**.
- Says prerequisites are "**Xcode 26.3 or later**" for the iOS 27 SDK — every other source says **Xcode 27**.
- `LanguageModelSession.isAvailable` — plausible-looking but unverified (Apple's documented pattern in iOS 26 was `SystemLanguageModel.default.availability`).

**Verdict: DO NOT CITE.** Its generic FM API examples (`@Generable`, `respond(to:generating:)`, `Tool` conformance, `streamResponse(to:)`) happen to match the real iOS 26 API, but you can get those from better sources.

**Its one genuinely useful contribution** — a comparison table that correctly separates the layers, and this line: "**Core AI** — The platform framework that replaces Core ML. Foundation Models sits on top of Core AI. When you call `LanguageModelSession`, you are using Core AI's inference infrastructure via the Foundation Models API surface." (Corroborated by §7.1/§7.2's `CoreAILanguageModel` bridge.)

---

## 10. PAGES I COULD NOT GET

| URL | What happened |
|---|---|
| `reddit.com/r/iOSProgramming/comments/1u1nfxr` (+ comment `or7429o`) | `.json` endpoint returned non-JSON (Reddit blocks unauthenticated programmatic reads). Only have the fragment InfoQ quoted. **Recommend the forums agent retries with a browser.** |
| `apple.github.io/coreai-torch/main/` "Choosing your workflow" table | jina truncated the table mid-render (last line of the dump is the header row). Contents reconstructed from avinashsangle's relay; should be re-fetched directly. |
| `apple.github.io/coreai-torch/main/coreai-core/` | Appeared in search results; not fetched (out of scope for community-blogs — belongs to the Apple-docs agent). |
| `hackingwithswift.com/articles/282/...` (Paul Hudson SwiftUI agent skill) | Referenced by atalayasoft; not fetched (agentic-Xcode topic, likely another agent's beat). |
| WWDC26 sessions 324 / 325 / 326 / 241 / 298 / 339 / 8121 | Not fetched — transcripts agent's beat. Community sources reference them heavily; cross-check there. |
| `github.com/apple/coreai-models`, `apple/coreai-optimization` | Not fetched — repos agent's beat. |

**Note on WebFetch:** for both assigned articles, plain `WebFetch` returned an LLM-written *summary* rather than the text, and for the Appcircle piece it under-reported the content. **`curl https://r.jina.ai/<url>` gave full verbatim markdown in both cases** and was used for essentially every page in this session. InfoQ specifically requires skipping ~200 lines of nav chrome before the article body.

---

## 11. SYNTHESIS — what community sources add that Apple's docs don't

1. **AOT compilation is mandatory on iOS, not optional.** Apple's docs frame `coreai-build` as a startup-latency optimization. §2.5 shows that on iOS it is **required** — iOS cannot JIT MLIR — and that the failure mode is a misleading `NSPOSIXErrorDomain Code=2 "No such file or directory"`.
2. **Compute unit is chosen at EXPORT time, not runtime.** The `ComputeUnitKind`/`SpecializationOptions` story in the docs implies runtime control. In practice, for the LLM path, `EngineFactory` picks `static-shape`(ANE) vs `coreai-pipelined`(GPU) **from graph structure**, and forcing it errors with `unsupportedEngineVariant`. You must build two bundles.
3. **`.aimodel` is a build artifact, not a pure function of your recipe.** The macOS 26→27 export-lowering regression (§2.4) produced a **2.2× slower** artifact from a byte-identical command. Version-stamp and archive your artifacts.
4. **Core AI's speed advantage over MLX evaporates at realistic model sizes.** 2.47× at 0.6B → **1.05× at 8B**. Both become bandwidth-bound. MLX actually *wins* on MoE (+28% on gpt-oss-20b).
5. **Burst ≠ sustained.** Core AI's GPU path retains only ~56% of burst under 10-min load; the ANE retains ~67%. "The GPU wins the sprint; the ANE wins the marathon."
6. **Low power ≠ low energy.** CoreML/ANE draws half the watts of the GPU path but is the *worst* J/token, because slow decode keeps the package awake longer.
7. **Apple's own Foundation Models is the energy champion** at 0.11 J/tok — 2× better than GPU runtimes, 4× better than CoreML/ANE — despite decoding at ~half the rate.
8. **Metal Toolchain is a hidden build dependency.** Xcode doesn't install it; builds with `.aimodel` files fail with a missing-Metal-compiler error. And its mount path changes across reboots/Xcode updates, poisoning SwiftPM's cached manifest.
9. **`coreai-core` ships two native stacks and switches on OS version** (`USE_LOCAL_COREAI` / `USE_OS_COREAI`). Undocumented in any Apple-facing material I saw.
10. **`COREAI_CHUNK_THRESHOLD`** is an undocumented memory/throughput dial for MoE prefill (18 GB @ 1,439 tok/s unchunked vs 1.7 GB @ 766 tok/s at chunk-128).
11. **`CoreAILanguageModel(resourcesAt:)` / `MLXLanguageModel(modelID:)`** unify Core AI and MLX under `LanguageModelSession`. Two independent sources confirm. This makes the "which framework" question much less either/or than the docs suggest.
12. **The community corpus is polluted.** Two of ~14 sources are fabricated. Anyone building guides from web search alone will absorb `.coreaimodel`, `.aiasset`, "iOS 20", and a nonexistent LoRA training API.

---

## 12. SOURCE INVENTORY (everything I actually fetched and read this session)

**Assigned:**
1. https://appcircle.io/blog/wwdc26-apple-core-ai-framework-explained — WebFetch + r.jina.ai (108 lines) ✅
2. https://blakecrosley.com/blog/core-ai-run-models-apple-silicon — WebFetch + r.jina.ai (177 lines, full incl. all 17 footnotes) ✅

**Benchmarks (Grade A):**
3. https://github.com/john-rocky/apple-silicon-llm-bench → `raw.githubusercontent.com/.../main/README.md` (501 lines) ✅
4. .../main/methodology/coreai-ios.md (97 lines) ✅
5. .../main/methodology/coreai-export-lowering.md (90 lines) ✅
6. https://rockyshikoku.medium.com/i-benchmarked-apples-new-framework-against-mlx-for-on-device-llms-e52a769494b1 (112 lines) ✅

**Secondary:**
7. https://www.infoq.com/news/2026/06/apple-core-ai-wwdc/ (526 lines w/ chrome; body @239-259) ✅
8. https://dev.to/arshtechpro/wwdc-2026-apple-just-opened-the-foundation-models-framework-to-any-llm-provider-5ejn (266 lines) ✅
9. https://avinashsangle.com/blog/apple-core-ai-on-device-inference-guide (172 lines) ✅
10. https://andrew.ooo/answers/apple-core-ai-vs-foundation-models-vs-mlx-ios-27-framework-june-2026/ (152 lines) ✅
11. https://www.atalayasoft.com/blog/wwdc-2026-ai-on-ios-agentic-xcode-and-foundation-models (131 lines) ✅
12. https://wccftech.com/apples-new-coreai-engine-barely-edges-out-its-own-mlx-framework-...-tiny-models/ (34 lines) ✅
13. https://byteiota.com/apple-foundation-models-wwdc-2026-multimodal-python-sdk/ (96 lines) ✅
14. https://byteiota.com/apple-core-ai-replaces-core-ml-ios-27/ (59 lines) ✅
15. https://techjacksolutions.com/ai-brief/apple-foundation-models-api-developers-ios-27-reported/ (48 lines) ✅

**Community discussion:**
16. `hn.algolia.com/api/v1/items/48459443` — HN comment by ABS ✅
17. `hn.algolia.com/api/v1/items/48454273` — HN subtree (LoganDark, wahnfrieden, jkman) ✅

**Apple-official, fetched only to validate community relays:**
18. https://apple.github.io/coreai-torch/main/ (48 lines; "Choosing your workflow" table truncated) ⚠️partial

**Graded D (documented in §9, not used for facts):**
19. https://www.aimadetools.com/blog/what-is-apple-core-ai/ (236 lines) ⚠️
20. https://chatforest.com/builders-log/apple-foundation-models-ios-27-on-device-llm-api-builder-guide/ (338 lines) ⚠️

**Failed:**
21. https://www.reddit.com/r/iOSProgramming/comments/1u1nfxr.json ❌ blocked

**WebSearch queries run:** `"Core AI" framework Apple .aimodel coreai-torch tutorial 2026` · `Apple "Foundation Models framework" iOS 27 what's new WWDC26` · `Core AI vs Core ML vs MLX comparison Apple 2026 developer blog which to choose` · `".aimodel" format internals MLIR reverse engineering Apple Core AI` · `"Core AI Debugger" Apple app inspect model graph Xcode 27 tutorial` · `MLX Swift on-device LLM iPhone 2026 developer experience gotchas blog` · `Apple "Evaluations framework" WWDC26 Xcode 27 developer blog on-device model testing`

---

## 13. OPEN QUESTIONS / UNVERIFIED

1. **`AIModelAsset` initializer signature.** Crosley explicitly says `AIModelAsset(url:)` is illustrative. Needs the Apple docs page.
2. **How do you get from `AIModel` to `InferenceFunction`?** No source shows it. Crosley writes `let function: InferenceFunction = /* load from an AIModel */`. This is the biggest hole in the community's Core AI coverage.
3. **`ComputeUnitKind` enum cases.** Everyone says "CPU, GPU, Neural Engine" but nobody gives the actual case spellings (`.cpu`? `.neuralEngine`? `.ane`?).
4. **`SpecializationOptions` members.** Named everywhere, never shown.
5. **`AIModelCache` API surface.** InfoQ says you can "check whether a model is already available or delete cached ones" and share across an App Group; Appcircle adds "control how long cached artifacts remain available." **No method names anywhere.**
6. **Does `EngineFactory` / `CoreAILM` / `EngineOptions.staticInputBuffers` belong to `apple/coreai-models` (SwiftPM) or to the `CoreAI` system framework?** §2 treats them as coreai-models package types. Needs the repos agent.
7. **Is `unsupportedEngineVariant` a `CoreAI` error or a `coreai-models` error?**
8. **`coreai.llm.export` full flag list.** Only `--platform iOS|macOS` and `--output-name` observed.
9. **`coreai-build compile` full flag list.** Observed: `--platform`, `--preferred-compute neural-engine|gpu`, `--output`, `--architecture <gpu-family>`. Is there a list of arch codes beyond `h18p`?
10. **Is the macOS 26→27 export-lowering regression fixed in later betas?** The forensics doc is dated 2026-06-11; it's now late July. Worth re-checking.
11. **Does `MLXLanguageModel` really exist**, and does it imply MLX *can* reach the ANE via Core AI after all? Would directly contradict the HN consensus.
12. **AFM 3 Core Advanced params (20B sparse, 1–4B active) and the image-input device gate.** byteiota asserts; needs Apple's research page.
13. **On-device LoRA fine-tuning in Foundation Models** — asserted only by the AI-generated chatforest piece. **Probably false.** Needs an explicit check against session 241.
14. **`fm` CLI subcommands** (`fm chat` / `fm respond` / `fm schema`) — two independent community sources, but no Apple page read.
15. **`Attachment(...)` vs the result-builder prompt syntax** — is `Attachment` the real type name for image input?
16. **`LanguageModelCapabilities(capabilities: [.toolCalling, .guidedGeneration, .reasoning])`** — the doubled label reads odd; likely a transcription artifact.
17. **`CXGrammar.xcframework`** — implies a constrained-grammar/guided-generation component inside `coreai-models`. Undocumented anywhere else.
18. **Core AI's "depth jetsam wall" on iPhone** — real, measured, but no one has characterized where it is or whether an API controls it.
19. **Nobody has hands-on-written about the Core AI Debugger app.** Content gap.
20. **`.aimodel` bundle layout.** We know it contains `main.mlirb`, a `compilation.targets` field, a `metadata.json` with `assets.main`, and a `tokenizer/` dir (for LLM bundles). No one has published a full spec.
