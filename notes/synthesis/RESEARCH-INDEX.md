# Research index — Apple 2026 AI/ML stack sweep

Index of the grounded research and synthesis files, so the investigation can be reconstructed
later. For current operational status, start at `notes/README.md`.

**Initial sweep:** 2026-07-27 · **Index reconciled:** 2026-08-01 · **Corpus root:** `notes/`
**Current total:** 37 research files + 7 synthesis files, ~5.2 MB
**Subject matter:** WWDC 2026 / iOS 27 / macOS 27 / Xcode 27 era. **This postdates the model's training data — nothing in the guides may be written from memory.**

---

## How the sweep was structured

Four parallel research fleets, each writing to one subdirectory, plus lead-agent grounding and
the synthesis layer:

| Fleet | Directory | Method |
|---|---|---|
| Transcripts | `transcripts/` | Deep-read of 23 WWDC26/Tech Talk sessions, grouped into 7 files |
| Repos | `repos/` | Local clones read file-by-file, 16 repos + 3 issue-mining sweeps; exact snapshots are pinned[^repo-snapshot-pins] |
| Web/docs | `web/` | Live fetches of Apple developer docs, the MLX docs site, and community blogs |
| Forums | `forums/` | RSS captures plus live thread fetches of `developer.apple.com/forums` |
| Lead agent | `00–02*.md` | Independent grounding, written before and alongside subagent output |
| Synthesis | `synthesis/` | Three independent topic proposals, merged plan, critique, taxonomy, and this index |

**Shared provenance convention** used across every file: `VERBATIM` / `VERIFIED: path:line` for text read directly; `RECONSTRUCTED` for code reassembled from spoken narration; `UNVERIFIED` for anything not corroborated. This convention should be carried into the guides themselves.

---

## Lead-agent files (read these first)

| File | Description |
|---|---|
| `00-ORIENTATION-lead-agent.md` | The lead agent's own end-to-end read of all 6 local doc mirrors and 14 of 16 WWDC26 transcripts, written *before* subagent results arrived. Contains the version decoder ring, the four-layer stack diagram, a per-area summary (Foundation Models, Core AI, Metal/TensorOps, Evaluations, MLX, Speech), a list of sessions referenced but absent from the corpus, and a 45-item pre-synthesis topic candidate list. |
| `01-lead-agent-repo-spotchecks.md` | Independent verification of high-leverage repo facts: `apple/coreai-models`' four components and its three **agent skills** (the ANE/GPU authoring rules and PSNR gates that appear in no video or doc page); the `python-apple-fm-sdk` 26-vs-27 version discrepancy; `mlx2coreai`'s stateful LLM contract; `coreai-torch`'s composite ops / externalization / custom lowerings; `coreai-optimization`'s three techniques; the discovery that `MLXFoundationModels` lives inside `mlx-swift-lm`; and the `john-rocky/coreai-model-zoo` community gotcha archive with its sourcing caveat. |
| `02-lead-agent-corpus-gaps-filled.md` | Two gaps the original research plan missed, found by reading the forum captures: (A) `apple/foundation-models-utilities` was not in the clone list — it holds `ChatCompletionsLanguageModel`, the history modifiers, the Skills API and Apple's own `LanguageModel` protocol agent skill; (B) the forum pain-point clusters. Also resolves PCC eligibility as **three** conditions, not one. |

---

## `transcripts/` — WWDC26 session deep-reads (7 files, 23 sessions)

| File | Sessions covered | Description |
|---|---|---|
| `fm-core.md` | 241 "What's new in Foundation Models"; 334 "Foundation Models on macOS" (`fm` CLI + Python SDK); meet-with-apple-205 (1,013-line FM code-along, the iOS 26 baseline) | The core Foundation Models surface: sessions, instructions vs prompts, `@Generable`/`@Guide`, snapshot streaming, `Tool`, availability, context window, prewarming. Opens with a 2025→2026 delta table. |
| `fm-advanced.md` | 242 "Build agentic app experiences…"; 243 (Instruments debugging/profiling) | Dynamic Profiles end to end — `DynamicInstructions`, `Profile`, modifiers, lifecycle hooks, session properties, `historyTransform`, KV-cache economics, tool-calling modes, transcript mutability — plus the Foundation Models Instruments template and the worked silent-failure bug. |
| `fm-ecosystem.md` | 319 (Private Cloud Compute); 339 "Bring an LLM provider to the Foundation Models framework"; 246 "LLM search using Core Spotlight" | The expansion beyond the on-device model: PCC (32K, reasoning levels, quota), the `LanguageModel`/`LanguageModelExecutor` protocol and the generation channel, image input, and `SpotlightSearchTool` local RAG including guidance profiles and pipeline stages. |
| `coreai-intro.md` | 324 "Meet Core AI"; 326 (Core AI app features / language-learning app) | Core AI positioning and runtime: `AIModelAsset`/`AIModel`/`InferenceFunction`/`NDArray`, specialization and caching, the snake-game states/KV-cache story, AOT with `coreai-build`, the multi-model app pattern and Background Assets distribution. |
| `coreai-python-metal.md` | 325 "Dive into Core AI model authoring and optimization"; 330 "Optimize custom ML operations with Metal tensors" | The Python toolchain (`coreai-torch`, `coreai-opt`), the Core AI Debugger and sync points, model re-authoring, `TorchMetalKernel`, and the whole TensorOps layer: `matmul2d`, quantized Metal tensors, MX scale planes, cooperative tensors and FlashAttention. Cross-checked against the **Xcode 26.6 SDK headers**. |
| `evals-mlx.md` | 298 "Meet the Evaluations framework"; 299 (agentic evaluations); 335 "Improve your prompts by hill climbing with Evaluations"; 232 (agentic AI workflows on Mac with MLX) | The complete Evaluations story — protocol, metrics, Swift Testing integration, the Xcode report, model judges, `ScoreDimension`, drift, Cohen's kappa, `SampleGenerator`, `TrajectoryExpectation` — plus the MLX local agentic stack and `mlx_lm.server`. |
| `missing-sessions.md` | 240, 237, 233, 343, 344, 345; Tech Talk 111432 | Closure pass for the seven sessions missing from the initial corpus: App Schemas/Siri, advanced App Intents, image understanding, distributed MLX, and the M5/A19 GPU talk. Includes fetched transcripts and Apple's separately published code samples with explicit provenance tags. |

> The original six thematic files carry the caveat that transcripts contain **no literal on-screen
> code**. `missing-sessions.md` separately distinguishes Apple's published code-sample blocks from
> reconstruction; follow each file's local provenance tags.

---

## `web/` — documentation, samples, and community sources (6 files)

| File | Description |
|---|---|
| `apple-docs-fm-evals-speech.md` | The largest file in the corpus (~202 KB). Complete harvest of `/documentation/foundationmodels` (121 KB index), `/documentation/evaluations` (44 KB) and `/documentation/speech` (60 KB), plus ~40 article pages. Covers the availability decoder ring, the 2026 error reshuffle, guided generation, Dynamic Profiles, KV caching, context management, image input, PCC, the `LanguageModel` protocol, `Transcript` structure, safety, the full Evaluations symbol inventory, and the Speech framework. Ends with a consolidated gotcha list, a source inventory of every URL fetched, and an explicit `UNVERIFIED` list. **Corrects the earlier belief that Evaluations had no docs — it has substantial ones.** |
| `apple-docs-coreai.md` | Complete Core AI API reference harvest (312 symbol paths). Per-type pages for `AIModel`, `AIModelAsset`, `InferenceFunction`, `InferenceFunctionDescriptor`, `InferenceValue`, `ImageDescriptor`, `ComputeStream`, `NDArray` and its four view types, the 33-case `ScalarType` enum, `InterleaveLayout` (the most detailed page in the framework), `NDArrayDescriptor`, `AIModelCache`, `SpecializationOptions`, `ComputeUnitKind`, `AssetError` — plus the seven articles (integration, specialization/caching, AOT compilation, debug gauge, Instruments, Core AI Debugger, reference-run validation). Notes that Core AI ships **zero sample code** and that `/documentation/updates/coreai` 404s. |
| `mlx-docs-site.md` | Exhaustive crawl of `ml-explore.github.io/mlx` (MLX 0.32.0). Signatures extracted verbatim from raw HTML via a custom parser rather than WebFetch summaries. Covers arrays, lazy evaluation, unified memory, streams, `mx.compile`, function transforms, export, `mx.fast`, quantization, custom Metal/CUDA kernels, distributed collectives and backends, `mlx.nn`, and optimizers. |
| `community-blogs.md` | Community coverage with an explicit **A–D reliability grading system**, which was the session's most important finding: the 2026 community corpus is heavily polluted with AI-generated slop that invents API names. Grade A is the independent `apple-silicon-llm-bench` harness (reproducible, raw JSONL, published fairness rules) — the source of the Core AI vs MLX, burst-vs-sustained and joules-per-token measurements. §9 documents two **fabricated** sources in detail (`.coreaimodel`, a `coreai-torch convert` CLI, "iOS 20 / macOS 17", an invented on-device LoRA training API) so nobody re-adds them. |
| `app-intents-siri-schemas.md` | App Intents, App Schemas, on-screen awareness, entity hand-off, Spotlight indexing, and Apple-staff clarifications recovered from docs and session pages. |
| `apple-sample-code.md` | Source-level audit of Apple's downloadable WWDC26 projects, including Origami, Book Tracker, Spotlight, generative game content, and Speech; corrections were applied through C9 in the corrections register. |

---

## `forums/` — Apple Developer Forums (1 file)

| File | Description |
|---|---|
| `forum-pain-points.md` | Four RSS topic captures (Foundation Models, Apple Intelligence, Evaluations, General) enumerated thread-by-thread, plus **live fetches of the individual threads** to recover Apple-staff replies that the RSS bodies truncate. Contains ~1,000 lines of verbatim Apple-staff answers; twelve ranked pain-point clusters (availability, guardrails, context, tools, Simulator, adapters, PCC, App Intents, extensions, BYO-model, vision); a quick-reference table of ~50 undocumented limits, error codes, entitlements and gates; the FB numbers referenced; and a guide to weighting Apple-staff vs community identities. **The strongest single signal for what the guides must cover.** Key findings: custom adapters discontinued in OS 27; two on-device model tiers; `.anyOf` confirmed broken; the `SpotlightSearchTool` description/schema mismatch; PCC's three-condition eligibility; no Required Device Capability for Apple Intelligence. |

---

## `repos/` — source-tree deep dives (20 files)

These deep dives are tracked evidence, distinct from the large third-party checkouts under the
repository-root `repos/` directory. The reproduction script fetches each upstream repository at the
exact full commit used during research rather than at a moving default branch.[^repo-snapshot-pins]

### Apple first-party

| File | Repo | Description |
|---|---|---|
| `apple-coreai-models.md` | `apple/coreai-models` | The 22-model catalog with per-model export recipes, the Python export primitives, the five-product Swift package (`CoreAILM`, `CoreAIDiffusion`, `CoreAISegmentation`, `CoreAISpeech`, `CoreAIObjectDetection`), and the three **agent skills**. Documents the model-bundle format (`metadata.json` 0.2), the four LLM inference engines, KV-cache strategies, samplers, xgrammar guided decoding, `CoreAILanguageModel`, and the `coreai.llm.export` recipe for both the macOS dynamic and iOS static paths. |
| `coreai-torch.md` | `apple/coreai-torch` (0.4.1) | The PyTorch→Core AI IR converter. `TorchConverter`, `get_decomp_table()`, the ~180-entry ATen lowering registry and its overload footgun, the composite-op library (including `gather_mm` for MoE and `gated_delta_update` for SSM), the five-phase externalization pipeline, `register_torch_lowering`, `TorchMetalKernel`, IO/state naming rules, dynamic shapes, and the `coreai_torch.debugging` toolkit. |
| `coreai-optimization.md` | `apple/coreai-optimization` (`coreai-opt`) | The compression stack: quantization (three-level config precedence, `QuantizationSpec`, presets, GRAPH vs EAGER as a correctness fork, QAT), k-means palettization (including the rank-6-LUT / ANE-rank-5 trap and SqueezeLLM sensitivity weighting), magnitude pruning and schedules, fp16 casting, joint compression, mixed precision, `ModelInspector`, and the PyTorch-free `coreai_utils` path. |
| `foundation-models-utilities.md` | `apple/foundation-models-utilities` (1.0.0-beta3) | The out-of-band package: `ChatCompletionsLanguageModel` (and its hardcoded-`v1` bug), the three history modifiers with their outside-in application order, the Skills API and the `prompt:`-vs-`instructions:` KV-cache table, `SkillActivations`. Also holds **Apple's own `foundation-models-language-model-protocol` agent skill** — the primary written source for the provider guides — and confirms Linux support. |
| `python-apple-fm-sdk.md` | `apple/python-apple-fm-sdk` | Python bindings over Swift via a C shim and a custom PEP 517 build backend. Swift↔Python API mapping, `@fm.generable`/`fm.guide`/`generating=`, the guide-type compatibility matrix, tools, streaming, transcript round-tripping, token counting — and five confirmed bugs including an FD leak. Flags that the public repo is at the **26 generation**, not 27. |
| `coreai-models-nonllm.md` | `apple/coreai-models` | Companion to `apple-coreai-models.md` covering the **non-LLM half**: the `CoreAIShared` substrate (`ModelStructure` compute-unit selection, `NDArray` helpers, `ModelBundle`/`FunctionMap`, image↔tensor preprocessing), `CoreAISegmentation`, `CoreAIDiffusion`, `CoreAISpeech`, `CoreAIObjectDetection`, their CLI tools, the vision/audio/diffusion model catalog, and the non-LLM Python primitives. |
| `dnikit.md` | `apple/dnikit` (2.0.0) | Data and Network Introspection Kit: `Producer`/`PipelineStage`/`Introspector`, `Batch`, PFA network compression, IUA dead-unit analysis, Familiarity, Duplicates, `DatasetReport`. Leads with an honest status warning — effectively dormant since 2023, published build broken under Keras 3, fix only on `main`. |

### MLX

| File | Repo | Description |
|---|---|---|
| `mlx-core.md` | `ml-explore/mlx` (0.32.1) | The array framework: lazy evaluation, unified memory and streams, `mx.compile` and its fusable-primitive set, function transforms, export, `mx.fast` fused ops and their narrow coverage, the four quantization modes, custom Metal/CUDA kernels and primitives, distributed backends, and the memory allocator. Includes real TensorOps call sites from MLX's own GEMM kernels. |
| `mlx-lm.md` | `ml-explore/mlx-lm` (0.31.3) | The LLM layer: 18 console scripts with real flags, `load`/`generate`/`stream_generate`/`generate_step`, samplers and logits processors, model conversion and mixed-precision recipes, the four learned-quantization CLIs, the 121-architecture zoo and the 2026 per-layer config schema, the ten KV cache classes, disk and server prompt caching, speculative decoding and MTP, the continuous-batching server, and LoRA/DoRA fine-tuning. |
| `mlx-examples.md` | `ml-explore/mlx-examples` | The Python example zoo (as of 2026-04): standalone LoRA, custom-kernel examples, C++ extension packaging, and the training/optimizer patterns that the library docs assume. |
| `mlx-swift-lm.md` | `ml-explore/mlx-swift-lm` (3.x) | The Swift port. The 3.x breaking redesign that decoupled tokenizer/downloader into protocols, the `MLXHuggingFace` macros, `ModelContainer` and the Swift 6 concurrency model, generation entry points, ten tool-call wire formats, reasoning parsing, the eight KV cache types including **TurboQuant**, wired memory — plus `MLXFoundationModels` (the reference third-party `LanguageModel` conformance) and `MLXGuidedGeneration` (vendored xgrammar). |
| `mlx-swift-examples.md` | `ml-explore/mlx-swift-examples` | The Swift sample apps: SwiftUI streaming patterns, VLM media input (PhotosPicker `Transferable`, EXIF, security-scoped URLs), memory policies and entitlements, benchmarking helpers, and the Qwen3VL 33.9 GB vision-prefill incident with its fix. |
| `mlx-tensorops-kernels.md` | `ml-explore/mlx` (Metal kernels) | Verified API reference for MLX's Metal/TensorOps surface: replaces every WWDC26 session-330 narration-reconstructed spelling with a `path:LINE`-cited spelling from the Xcode 26.6 SDK headers and MLX's own kernels — the `__tensor_ops_datatype` enum, `matmul2d` call sites, the fp8/fp4 software structs, and the NAX kernel gates. |

### Community and third-party

| File | Repo | Description |
|---|---|---|
| `noema-ios.md` | `noemaai-labs/noema-ios` (Noema 3.5) | A **shipping App Store app** running six backends behind one enum (llama.cpp GGUF, MLX, Core AI, Foundation Models, PCC, remote). The single best source in the corpus for shipping/ops: the two-stage launch memory gate, MoE-plus-mmap residency accounting, a hysteretic pressure governor, verified unloads, the dual-session download engine with live task migration, `BGContinuedProcessingTask`, thermal policy, and Core AI engine integration in production. |
| `mlx2coreai.md` | `lucasnewman/mlx2coreai` | The MLX→Core AI bridge: capture MLX graphs via the export callback, lower to Core AI MLIR, emit `.aimodel` or coreai-models-style bundles. Documents the stateful LLM contract (`input_ids`, `position_ids`, mutable `keyCache`/`valueCache`), dynamic-shape probe differencing, composite declarations, the machine-generated op-coverage matrix, and three silent miscompiles. |
| `swift-lm.md` | `1amageek/swift-lm` (0.11.0-alpha) | A declarative Swift DSL → LMIR → versioned JSON contract → generic Python lowerer, targeting Core AI. The stateless and stateful contracts with states derived purely from the IR graph, SHA-256 contract pinning, `CoreAIStateSession` with MTLBuffer-backed persistent states, a VLM adapter for Apple's three-asset contract, and a hard-fail-never-fallback policy. |
| `john-rocky-models.md` | `john-rocky/coreai-models` (fork), `john-rocky/coreai-model-zoo` | The community fork's `InferenceEngine` additions (`trimKVCache` prefix reuse) and the model-zoo gotcha archive: device benchmark tables, porting incidents, and bug write-ups that are often the only public measurements of these paths. Opens with an explicit sourcing warning — partly agent-generated, **not Apple-official**. |

### Issue and PR mining

| File | Scope | Description |
|---|---|---|
| `issues-coreai-stack.md` | `apple/coreai-torch`, `apple/coreai-optimization`, `apple/coreai-models` | Live `gh` CLI mining of issue bodies, comment threads, PR diffs and release notes. Source of the beta-defect catalogue: the `optimize()` silent miscompile (~17 dB PSNR), the linear-INT4 ANE pre-compile SIGSEGV, the MPSGraph decode scratch-heap overflow, prefill nondeterminism, iOS KV-state corruption, the `coreai-core` version floor and `strip_debug_info` rescue, plus four unmerged PRs fixing live silent miscompiles. |
| `issues-mlx-stack.md` | `ml-explore/mlx`, `mlx-lm`, `mlx-swift-lm`, `mlx-swift-examples` | ~280 issue titles and ~150 PR titles triaged, ~35 threads deep-read, with maintainer statements quoted and attributed. Source of the hardware-gating material: `MLX_ENABLE_TF32` defaults, NAX gating, silent fused-SDPA fallback tables, the M5 `gather_qmm` memory-exposure corruption, the buffer-count resource limit, the `maybeQuantizeKVCache` `inout` bug, and CVE-2026-5843. |
| `issues-community-stack.md` | `apple/python-apple-fm-sdk`, `apple/dnikit`, `1amageek/swift-lm`, `noemaai-labs/noema-ios`, `lucasnewman/mlx2coreai`, `john-rocky/coreai-model-zoo`, `john-rocky/coreai-models` | Issue/PR mining across the community half of the stack, with per-repo activity stats. Source of the Python SDK bug list, the `.aimodel` bundle-path version error, the iOS "No such file or directory" JIT failure signature, and the community porting incidents. |

---

## `synthesis/` — proposals

| File | Description |
|---|---|
| `proposal-by-framework.md` | Topic proposal organized by **framework/product line** (16 pillars, 55 topics). Strongest on per-framework completeness and on the "verified vs unverified" editorial convention. |
| `proposal-by-task.md` | Topic proposal organized by **developer task / reader journey** (12 pillars, 56 topics). Strongest on ordering, on the five reader journeys, and on surfacing the silent-failure theme. |
| `proposal-by-depth.md` | Topic proposal organized by **stack depth**, L0→L10 (11 pillars, 55 topics). Strongest on the vertical dependency structure and on the low-level Core AI / TensorOps material other lenses under-weighted. |
| **`PROPOSED-GUIDE-TOPICS.md`** | The merged, adjudicated initial plan — 50 guides in 16 parts. It is now a historical planning artifact; the 17-part `guides/` tree is authoritative. |
| `COVERAGE-CRITIQUE.md` | Adversarial review that found the initial plan's missing non-LLM Core AI, repo, and source coverage; its accepted gaps were later closed in the guides. |
| `SYMPTOM-TAXONOMY.md` | Canonical symptom vocabulary used by the silent-failure index and committed callout classifications. |
| `RESEARCH-INDEX.md` | This reconstruction map and the current boundary ledger for the notes corpus. |

[^repo-snapshot-pins]: The exact revisions are recorded in
    [`scripts/clone-research-repos.sh`](../../scripts/clone-research-repos.sh), including Apple
    [`coreai-models@5ed9981`](https://github.com/apple/coreai-models/commit/5ed9981303b38d5a44aa6b45509bc4f6945029f5),
    MLX [`mlx@973e27f`](https://github.com/ml-explore/mlx/commit/973e27f82ffe68dbd626cda31ba34997045d1eb7),
    and [`mlx-lm@e5baded`](https://github.com/ml-explore/mlx-lm/commit/e5baded8c1d286754edb479ffbde4655a68e2758).

---

## Known corpus boundaries

Recorded so a later pass knows what remains outside the evidence envelope:

- The host is still macOS 26.5.2. Xcode 27 beta 4, the optional Metal Toolchain, and an iOS 27
  simulator are installed and exercised, but no macOS 27 host or physical OS-27 device has run the
  remaining hardware/OS probes. The precise residue is maintained in
  `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md`.
- The `fm` executable is absent from both installed Xcode toolchains. Its claimed macOS-27 CLI
  surface remains untested until the host OS changes.
- Core AI is absent from the simulator SDK, so cache deletion semantics, device specialization,
  ANE behavior, thermals, and physical-device context size remain device evidence gaps.
- The six Foundation Models and Core AI Instruments lane headers still require one manual GUI
  recording; headless `xctrace` cannot recover them on this host.
- The MSL bodies demoed in sessions 325 and 330 (FlashAttention, SiLU) were on screen but never
  read aloud, and the exact bodies were not downloadable.
- Repository and defect-state evidence is snapshot-based and continues to age. Use
  `notes/FRESHNESS-RUNBOOK.md` before treating an OPEN/CLOSED/MERGED statement as current.
