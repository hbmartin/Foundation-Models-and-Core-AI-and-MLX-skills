# Lead agent's own repo spot-checks

Independent verification of high-leverage repo facts, done in parallel with the subagent fleet so
the topic proposal doesn't rest solely on delegated summaries. Everything below I read directly.

---

## `apple/coreai-models` — much bigger than the transcripts implied

`git log -1`: `5ed9981 2026-07-23 Move away from deprecated FM API (#123)`

### Four components (per README)
| Directory | Contents |
|---|---|
| `models/` | Model catalog + per-model export recipes |
| `python/` | Python primitives for authoring + export utilities |
| `swift/` | Swift package `coreai-models` — runtime utilities |
| `skills/` | Agent-skill plugin for coding agents |

**Requirements: macOS and iOS 27.0+, Xcode 27.0+.** Uses **`uv`** as the Python runner
(`brew install uv`). Model discovery: `uv run coreai.model.registry --list-models`.

### Model catalog (`models/`) — 22 entries
`gpt_oss`, `mixtral`, `gemma3`, `edsr`, `clip`, `qwen2`, `flux2`, `depth-anything`, `pvt`,
`qwen3`, `t5`, `wav2vec2`, `vlm`, `stable-diffusion`, `clap`, `efficient-sam`, `roberta`, `yolo`,
`sam3`, `mistral`, `whisper`, `qwen3_moe`

That's LLMs (incl. **MoE**: mixtral, qwen3_moe, gpt_oss), VLMs, diffusion (flux2,
stable-diffusion), ASR (whisper, wav2vec2), audio (clap), detection (yolo), segmentation (sam3,
efficient-sam), depth (depth-anything), super-resolution (edsr), encoders (clip, t5, roberta, pvt).

Important note from the README: **some models need more than a `.aimodel`.** LLMs need a
tokenizer; diffusion runs several models in sequence. So recipes emit a **resource folder** with
one or more `.aimodel` files plus resources — and the Swift package knows how to consume that
bundle layout. That "model bundle" concept is not in the Apple docs we have and deserves coverage.

### Swift package products — five, not one
```swift
platforms: [.macOS("27.0"), .iOS("27.0")]
products:
  CoreAILM             -> CoreAILanguageModels
  CoreAIDiffusion      -> CoreAIDiffusionPipeline
  CoreAISegmentation   -> CoreAIImageSegmenter
  CoreAISpeech         -> CoreAISpeech
  CoreAIObjectDetection-> CoreAIObjectDetector
```
Dependencies: **`apple/swift-argument-parser`**, **`huggingface/swift-transformers` (1.1.0+)**,
and **`mlc-ai/xgrammar` (branch main)**.

> **`xgrammar` is a significant finding.** It's the grammar-constrained-decoding library. Combined
> with the `CoreAILanguageModels/GuidedGeneration/` directory, this tells us how `@Generable`
> guided generation is made to work against *arbitrary* Core AI models — via constrained decoding
> with a compiled grammar, not just prompt engineering. There's a `Sources/lib/CXGrammar` C-shim
> target with a `dlpack` include dir. This is a genuinely deep, guide-worthy mechanism and it is
> **not** described in any transcript or doc we have.

`CoreAILanguageModels` internal structure — reads like a table of contents for an LLM runtime guide:
`Assets/`, `Bundle/`, `DecodingStrategies/`, `GuidedGeneration/`, `InferenceEngines/`,
`LanguageModel/`, `Output/`, `Profiling/`, `Samplers/`, `Session/`, `TextGeneration/`, `VLM/`

CLI tools in `Sources/Tools/`: `benchmark`, `diffusion-runner`, `image-segmenter`, `llm-runner`,
`object-detector`, `speech-runner`.

Python package `coreai_models` submodules: `llm/`, `segmentation/`, `models/`, `diffusion/`,
`vlm/`, `primitives/`, `export/`. Tests split into `test_model_conversion/`, `test_model_units/`
(with `test_models`, `test_export`, `test_primitives`) and a `_runner_infra/`.

### `skills/` — Apple's own empirical deployment knowledge, in writing
Three skills, installable as a **Claude Code plugin marketplace**
(`/plugin marketplace add git@github.com:apple/coreai-models.git`) and there is also a
`.codex-plugin` and a `gemini-extension.json` — so Codex and Gemini too.

| Skill | Covers |
|---|---|
| `working-with-coreai` | End-to-end deploy: export with `coreai-torch`, run with the Core AI runtime |
| `model-authoring` | **BC1S layout, op compatibility, KV cache patterns, precision rules, PSNR verification, activation functions, MoE, common issues** |
| `model-compression-exploration` | Systematically explore quantization/palettization configs with `coreai-opt`; ships `scripts/compression_metrics.py` + `scripts/quality_metrics.py` |

Reference files (952 lines total of dense empirical rules):
`model-authoring/references/neural_engine_rules.md` (479), `gpu_rules.md` (297),
`common_issues.md` (176); `model-compression-exploration/references/{compression_patterns,
experiment_runner,output_report,size_estimation}.md`; `working-with-coreai/references/guidance.md`.

**This is the single densest source of practical gotchas in the entire corpus.** Sample of what's
in `neural_engine_rules.md`:

- **Max tensor rank on ANE is 5.** Rank-6+ intermediates are rejected.
- **ANE dtypes: fp16, int8, int16.** *Any* fp32 falls back to GPU/CPU — including a bare Python
  float literal. `x = hidden * (1.0 + scale)` is a bug; you must build a fp16 `torch.ones(1)`.
  `torch.exp(...)` upcasts to f32 and must be cast back.
- **Fully static shapes** on ANE — "export one function per static shape config".
- **Alignment**: ANE processes fixed-size blocks along the last dim (treated as *width*); the last
  axis must be contiguous and **64-byte aligned**. A singleton last axis is padded to 64 bytes ⇒
  **32× memory cost at fp16, 64× at int8**. Rules: power-of-2 last dims, ≥32 fp16 elements,
  never singleton-last.
- **BC1S format** `(Batch, Channels, 1, Sequence)`; matmuls are 1×1 Conv2d. Exact permute/reshape
  recipes given for standard↔BC1S and multi-head GPU↔BC1S.
- **`nn.Conv2d(in, out, kernel_size=1)` instead of `nn.Linear`** — Linear decomposes into less
  efficient ops that may fall to CPU. Weight conversion:
  `conv.weight.data = linear.weight.unsqueeze(-1).unsqueeze(-1)`; norm `(D,) → (1, D, 1, 1)`.
- **Transpose bookkeeping**: `x.transpose(-3,-1)` → proj → `transpose(-3,-1)` at *every* projection
  site; "mismatched transposes are a common source of silent correctness bugs".
- **Prefer high-level ops** (`nn.LayerNorm`, `nn.RMSNorm`) — manually decomposed equivalents may
  not be reassembled by the compiler.
- **Softmax on the channel dim, not spatial dims**, to preserve the compiler's ability to split
  work spatially.
- **Convolution strides that factor into 2s and 3s** map efficiently; others add overhead.
- **ANE residency**: any unsupported op causes graph segmentation + cross-accelerator transfers,
  and that overhead dominates small-model inference.

**Verification gates (PSNR) — Apple's own numeric acceptance thresholds:**
| Comparison | Threshold |
|---|---|
| Re-authored vs source (torch) | > 70 dB |
| ANE layout vs GPU layout (torch) | > 70 dB |
| Compiled vs torch | ≥ 40 dB |
| After 4-bit palettization | ≥ 35 dB |

Also prescribes a **bottom-up authoring order** (norm → linear projections → attention → MLP →
decoder block) with per-primitive verification, an architecture-discovery phase
("run code, don't read code"; `register_forward_hook` to capture intermediates), and a
`from_source_model(cls, source_model)` factory convention so nothing is hardcoded.

`gpu_rules.md` covers the *opposite* set: fused QKV, native SDPA, stateful KV cache,
**MoE via GatherMM/SwitchLinear**, memory-efficient loading, RMSNorm variants.

Cross-references online docs we should also fetch:
`apple.github.io/coreai-torch/guides/composite-ops.html`,
`.../guides/externalization.html`, `.../api/composite-ops.html`.
→ **"composite ops" and "externalization" are coreai-torch concepts absent from every transcript.**

---

## `apple/python-apple-fm-sdk` — ⚠️ version discrepancy worth flagging

`git log -1`: `e868e60 2026-07-07 Release composed_prompt pointer in all respond() paths (#18)`

**README requirements say macOS 26.0+ / Xcode 26.0+ / Python 3.10+ / Apple Intelligence on.**
But WWDC26 session 334 presents the Python SDK as new-this-year and says "Xcode installed, Apple
Silicon Mac, Python ≥3.10". So the public repo is currently at the **iOS/macOS 26 generation** and
does not yet expose the 27-era additions (PCC model, dynamic profiles, LanguageModel protocol).
Guides must state this explicitly rather than assuming parity with Swift.

`pip install apple-fm-sdk`; import as `apple_fm_sdk as fm`. Docs at
`apple.github.io/python-apple-fm-sdk/`. **"This project is not yet taking contributions."**

Confirmed API shape from the README (verbatim):
```python
model = fm.SystemLanguageModel()
is_available, reason = model.is_available()      # tuple, not a Swift-style enum
session = fm.LanguageModelSession()
response = await session.respond("Hello, how are you?")   # async
```
```python
@fm.generable
class Cat:
    name: str
    age: int = fm.guide("Age in years", range=(0, 20))

cat = await session.respond("Generate an adorable rescue cat", generating=Cat)
```
So: `@fm.generable` decorator, `fm.guide(description, range=…)` as a *default value*,
`generating=` kwarg — matches session 334.

Stated purposes include one the transcript underplayed: **"Process transcripts exported from Swift
apps for quality analysis"** and **"Evaluate Swift Foundation Models app features by running batch
inference and analyzing results from Python."** There's an `examples/transcript_processing.py`.
That's a real cross-language workflow: Swift app → export transcript → Python analysis.

Test-file inventory is an excellent map of the actual supported surface:
`test_system_model, test_session, test_error_handling, test_prompts, test_streaming,
test_json_guided_generation, test_generable_protocol, test_guided_generation,
test_generation_options, test_memory_stress, test_guides, test_memory, test_tool, test_transcript,
test_image_prompts, test_composed_prompt_cleanup, test_token_count`
→ tools ✅, images ✅, streaming ✅, token counting ✅, JSON-schema guided generation ✅ (separate
from the decorator path), **and two memory tests plus a `composed_prompt_cleanup` test** — which
lines up with the HEAD commit about releasing a `composed_prompt` pointer. **Memory management
across the Python↔Swift/C boundary is a real, documented hazard here.**
There is also a `foundation-models-c/` directory — a C shim layer — and a custom
`build_backend.py`. And a `doc_tests/` suite that tests README and doc-website snippets.

---

## `lucasnewman/mlx2coreai` — the MLX→Core AI bridge

`git log -1`: `059c9f3 2026-06-09 Add a swift runner as python bindings are incomplete as of now.`

Self-described: *"Experimental MLX to CoreAI conversion. Captures MLX graphs, lowers supported ops
to **CoreAI MLIR**, and writes `.aimodel` assets or **coreai-models-style LLM bundles**."*

→ Confirms **Core AI's IR is MLIR-based**, and that the `coreai-models` bundle layout is a
de-facto interchange format a third party targets.

`pip install mlx2coreai`.

**Stateful LLM path** (the interesting one):
```bash
mlx2coreai convert-mlx-lm-stateful mlx-community/Qwen3-0.6B-bf16 \
  --output qwen --max-context-length 256
```
Emits a bundle with `metadata.json`, `tokenizer/`, and a nested `.aimodel`.
> "The exported model has one `main` entrypoint with `input_ids`, `position_ids`, and mutable
> `keyCache` / `valueCache` state."

That is a concrete, verified example of the Core AI **states** mechanism from session 324 — and it
pins down the conventional signature for an LLM `.aimodel`.

**Generic path**: `convert_mlx_to_coreai(fn, {name: np.ndarray}, config=ConversionConfig(optimize=True), output_path=…)`
→ returns something with `.asset_path`.

**Runtime**: `await run_aimodel("model.aimodel", {"x": np.ones(...)})` → `result.outputs`
("when the local CoreAI runtime is available").

Source modules map the conversion pipeline cleanly and would structure a guide:
`from_mlx.py` (capture) → `ir.py` → `passes.py` → `op_registry.py` / `_composite_declaration.py` →
`lower_to_coreai.py` → `conversion.py`; plus `dynamic_shapes.py`, `runtime.py`, `cli.py`,
`reporting.py`, `op_coverage.py`, `_convert_mlx_lm.py`, `_convert_mlx_lm_stateful.py`.
**`docs/op_coverage.md` is a machine-generated op-support matrix** — exactly the artifact a
"what converts and what doesn't" guide needs. Tests include a `model_zoo.py` and `coverage_zoo.py`.

`scripts/benchmark_aimodel_sampling.py` + `scripts/benchmark_aimodel_sampling_coreai.swift` —
the README's note that "python bindings are incomplete as of now" is why the Swift runner exists;
worth verifying which Core AI Python binding gaps forced that.

---

## `apple/coreai-torch` — the conversion API is bigger than session 325 showed

`git log -1`: `4529671 2026-07-23 Remove run_transforms helper in favor of result.optimize() (#50)`

README, verbatim on what it is: *"traverses a `torch.export.ExportedProgram` and produces Core AI
IR — the same IR consumed by the Core AI compiler and runtime. The public entry point is
`TorchConverter`, which lowers PyTorch operators to Core AI dialect operations, **preserves
location and module-stack information for debugging**, and provides extension points for custom
Metal kernels and submodule externalization."*

→ The "preserves location and module-stack info" is exactly what powers the Core AI Debugger's
**source viewer** and **group-by-PyTorch-module navigator**. Good causal link to teach.

**Two input forms**, which session 325 never mentioned:
| You have | Use |
|---|---|
| A decomposed `ExportedProgram` | `add_exported_program()` |
| An `nn.Module` + need externalization | `add_pytorch_module()` with `externalize_modules` |
| An `nn.Module`, no externalization | either; `add_exported_program()` is more direct |

Canonical snippet (verbatim from README):
```python
import torch
from coreai_torch import TorchConverter, get_decomp_table

model.eval()
ep = torch.export.export(model, args=(torch.randn(1, 3, 224, 224),))
ep = ep.run_decompositions(get_decomp_table())

converter = TorchConverter().add_exported_program(ep)
coreai_program = converter.to_coreai()
coreai_program.optimize()
```
`pip install coreai-torch`, or from source with **`uv sync`**.

### Three concepts absent from every transcript

1. **Composite ops** (`coreai_torch.composite_ops`) — a *built-in library you compose models from*,
   not just a conversion detail. Documented ops each get their own page:
   `aten-derived`, `batch-norm`, **`gated-delta-update`**, **`gather-mm`**, `group-norm`,
   `hard-sigmoid`, `instance-norm`, `layer-norm`, `linalg-vector-norm`, `log-softmax`,
   `module-class`, `pixel-shuffle`, `rms-norm`, **`rope`**, **`sdpa`**.
   `gated-delta-update` = modern linear-attention / SSM state update (Qwen3-Next-class models);
   `gather-mm` = MoE expert dispatch (matches the `GatherMM/SwitchLinear` note in the ANE/GPU
   skill). So Core AI has *first-class* MoE and SSM support. Nobody said this out loud.
2. **Externalization** (`ExternalizeSpec`, `externalize_modules`) — pulling submodules out of the
   converted program. Whole guide + API page. Referenced by the ANE skill for
   "memory-efficient weight loading for large models" and "iOS embedding quantization"
   (the ANE rules say embeddings are shape `(V, 1, D)` — "externalized").
3. **Custom op lowering** — `register_torch_lowering()`, with **`allow_override=True`** to replace
   a *built-in* lowering. Plus `generate-composite-decl` tooling.

### `supported-aten-ops.md` (177 lines) — the op-coverage contract
Reading rules worth quoting to readers:
- op names are FX qualified `op_name.overload`; **"When PyTorch's decomposition pipeline produces a
  different overload than the one listed, that overload is not supported."** ← classic footgun
- exactly three ops are **deliberately preserved** by `get_decomp_table()` and emitted as
  composites: `instance_norm.default`, `pixel_shuffle.default`,
  `scaled_dot_product_attention.default`
- everything resolves through the registry in `coreai_torch._aten_to_core`

Other doc pages: `api/TorchConverter.md` (504 lines), `api/TorchMetalKernel.md`, `api/debugging.md`,
`faq.md`, `release-notes.md`, `whats-new.md`.
Guide notebooks: `composite-ops`, `conversion-workflows`, `custom-metal-kernels`,
`custom-op-lowering`, `externalization`, plus `getting-started/quickstart.ipynb`.

**`docs/coreai-core/`** — separate from coreai-torch: `api/coreai.md`, and tutorials
**`construct-a-graph.ipynb`** and **`run-an-aimodel.ipynb`**. So there is a *direct Python graph
authoring API* for Core AI that bypasses PyTorch entirely, plus a Python runtime for `.aimodel`.
Session 325 alluded to "directly authoring your model with Core AI APIs" — this is it.

---

## `apple/coreai-optimization` — three techniques, deep config surface

`git log -1`: `cd95cb2 2026-07-24 fix: try per-channel act quant for shared observers but fall back to per-tensor if unsafe (#52)`

Package is `coreai_opt`. Source tree maps exactly onto the doc tree:

- **`quantization/`** — with **`_eager/` and `_graph/` submodules** (confirms
  `ExecutionMode.EAGER` vs `GRAPH` from session 325 is a real structural split, not a flag),
  `config/_presets/`, `spec/`. Docs: overview, basics, config, **advanced**.
- **`palettization/`** — `kmeans/`, `config/_presets/`, `spec/`, and a vendored
  **`deps/_kmeans1d`**. Docs include diagrams for three schemes: **scalar per-tensor**,
  **scalar per-grouped-channel**, and **vector palettization**.
- **`pruning/`** — docs with diagrams for **magnitude** pruning, **schedules**, and **schemes**.
  (Session 325 never mentioned pruning at all.)
- **`casting/`** — the fp16 cast helper session 325 used.
- **`inspection/`** — plus docs `debugging/model_inspection.md` and
  `debugging/graph_mode_troubleshooting.md`.
- **`coreai_utils/passes/`** — and doc `utils/coreai_compression.md`,
  `introduction/integration_coreai.md` — i.e. compressing an *already-converted* Core AI program,
  not only a PyTorch one.
- **`utils/joint_compression.md`** and **`utils/mixed_precision.md`** +
  `examples/mixed_precision_palettization.md` (with a `mixed_precision_tradeoff.png` chart) —
  **combining techniques and per-layer precision assignment is a documented, first-class workflow.**
  This is precisely the "which layers tolerate compression" problem session 325 diagnosed with the
  Debugger, so the two connect into one strong guide.
- `utils/activation_comparison.md`, `utils/casting.md`.

Worked examples shipped: **`edsr`**, **`resnet50`**, `toy_models`, plus four MNIST notebooks
(quantization / palettization / pruning / palettization+activation-quantization).
Has `changelog.d/` (towncrier-style), `AGENTS.md`, an `agents/` dir, `Makefile`, `ci/`, `configs/`.

---

## `ml-explore/mlx-swift-lm` — ⚠️ this is where the FM↔MLX bridge actually lives

`git log -1`: `3cbf928 2026-07-24 Integration tests: build on both macOS 26 and 27 SDKs (#464)`

⚠️ **`main` is a new major version, 3.x**, with **breaking changes** that decoupled the tokenizer
and downloader packages. There's an upgrade doc. Guides must pin a version.
CI pins `swift-format` to `603.0.0`.

Library targets — several are *not* what mlx-swift-examples-era material would lead you to expect:

| Target | What it is |
|---|---|
| `MLXLLM` | LLM architectures |
| `MLXVLM` | VLM architectures |
| `MLXLMCommon` | shared API (ModelContainer, generation, …) |
| `MLXEmbedders` | encoder / embedding models |
| **`MLXFoundationModels`** | **"Bridge MLX models into Apple's `FoundationModels.LanguageModel` for use with `LanguageModelSession`. (Requires the macOS/iOS/visionOS 27.0 SDK.)"** |
| **`MLXGuidedGeneration`** | **"Grammar-constrained generation (JSON Schema or EBNF) for any MLX model."** |
| **`MLXCXGrammar`** | the xgrammar C interop layer |
| `MLXHuggingFace`, `MLXHuggingFaceMacros` | hub integration, macro-generated |
| `BenchmarkHelpers`, `IntegrationTestHelpers` | test/bench support |

**Two independently important confirmations:**
1. `MLXFoundationModels` is the real, readable implementation of the **`MLXLanguageModel`**
   announced in sessions 241/339. It is the best worked example in existence of conforming a
   third-party runtime to the `LanguageModel` / `LanguageModelExecutor` protocol — and it's small
   enough to read. **This should anchor the "author a LanguageModel package" guide.**
2. Both Apple's `coreai-models` **and** `mlx-swift-lm` independently reach for **xgrammar** to do
   grammar-constrained decoding (JSON Schema / EBNF). That is how `@Generable` guided generation
   gets enforced on non-Apple models. Convergent design; strongly guide-worthy; documented nowhere
   in the WWDC transcripts.

Also ships **its own agent skill** (`skills/mlx-swift-lm/`) whose reference files read like a
guide outline: `concurrency.md`, `embeddings.md`, `generation.md`, `kv-cache.md`,
`lora-adapters.md`, `model-container.md`, `model-porting.md`, `supported-models.md`,
`tokenizer-chat.md`, `tool-calling.md`, `training.md`, **`wired-memory.md`**
(← wired memory = the iOS/macOS memory-residency issue everyone hits).

The HEAD commit — *"Integration tests: build on both macOS 26 and 27 SDKs"* — plus
`MLXFoundationModels` requiring the 27 SDK means **SDK-conditional compilation is a live concern**
in this package. Worth a section.

---

## `john-rocky/coreai-model-zoo` — the richest community gotcha archive in the corpus

`git log -1`: `9001528 2026-07-27 Open the device gate to contributors, and give agents a zero-install entry`
(i.e. **updated today**).

Top-level: `README.md` (328), `PORTING.md` (350), `CATALOG_PLAN.md` (234), `AGENTS.md` (119),
`CONTRIBUTING.md` (74), `BENCHMARKS.md` (35). Also ships **agent skills**
(`port-a-model-to-the-zoo`, `reproduce-a-zoo-model`) as Claude/Codex/Gemini plugins.

**`knowledge/` holds ~40 dense field notes.** Selected, grouped:

*Platform mechanics*
`coreai-overview.md`, `aot-and-specialization.md`, `compute-units-and-authoring.md`,
`conversion-guide.md`, `compression.md`, `compression-reference.md`, `custom-metal-kernels.md`,
`accel-levers-survey-and-plan.md`

*Real bugs and incidents — unavailable anywhere else*
- **`coreai-beta-mpsgraph-kvwrite-bug.md`** — a KV-cache write bug in MPSGraph under Core AI beta
- **`coreai-torch-041-ir-incident.md`** — an IR regression incident in coreai-torch 0.4.1
- `agentic-security-checklist.md`

*Benchmarking / cross-runtime comparison*
**`coreai-vs-mlx-speed.md`**, `apple-models-bench.md`, `cross-runtime-quality-benchmarking.md`,
`dense-int4km-flagship-session-findings.md`

*Foundation Models integration from the community side*
**`fm-provider.md`**, **`dynamic-profiles-local-models.md`**, `evaluations-framework.md`

*Per-model porting write-ups* — gemma4 ×5 (`raw-metal-port`, `raw-metal-a19-levers`,
`mixedbit-qat-transplant`, `ple-static-input-fm-stack`, `litertlm-to-official-migration`),
`bitcpm-ternary-1.58bit`, `bitvla-1.58bit-vla`, `chatterbox-port` (TTS), `esam3-port`,
`depth-anything-3-monocular-depth`, `adcsr-super-resolution`, `flux2-in-context-editing`,
`diffusion-llms-dllm`, `flagship-full-tuning-stack`

*Prototype code*
`_tensorops_proto/` — a graded series of TensorOps matmul experiments:
`m0_half_x_half.py`, `m1a_half_x_int8.py`, `m1b_half_x_int4_uniform.py`,
`m2_int4_block32_scaled.py`, `m4_speed_ab.py`, `probe_dispatch.py`,
`device_matmul_ab_export.py` — i.e. someone actually measured the quantized-TensorOps path from
session 330. `_specdecode_proto/tree_attn_verify.py` — speculative decoding with tree attention.

⚠️ **Sourcing caveat for the guides:** this is a *community* repo, some of it agent-generated.
Its benchmark numbers and bug reports are valuable and often unique, but must be attributed as
community-measured, not Apple-official, and spot-checked where they contradict Apple's docs.
