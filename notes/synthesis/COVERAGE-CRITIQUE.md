# Coverage critique — `PROPOSED-GUIDE-TOPICS.md`

> **Status 2026-08-01:** historical review of the initial proposal. Its accepted findings were
> incorporated into the 17-part guide corpus, including the dedicated non-LLM Core AI guide. Keep
> the dated counts below as review evidence; do not use them as the current coverage ledger.

Adversarial completeness review of the 50-guide proposal against the raw material actually
sitting on disk (16 transcripts, 6 doc articles, 4 forum captures, 16 cloned repos).
Date: 2026-07-27. Method: read the proposal + `RESEARCH-INDEX.md` end to end, then grep the
34-file notes corpus for the API names each topic depends on, then diff the notes against the
raw corpus directory listings.

**Headline.** The synthesis is strong where the notes are strong, and the notes are strong.
But three things are true:

1. The whole series treats **Core AI as an LLM runtime**. In the raw material it is not — 15 of
   the 22 models Apple ships are non-LLM, and Apple ships four non-LLM Swift runtime products
   that appear **zero times** in the 161 KB proposal.
2. **Two of the sixteen cloned repos were never opened** — including a 926-file repo whose
   `knowledge/` directory (78 files, ~10,900 lines) independently closes at least five of the
   proposal's own §6.1 **BLOCKING** gaps.
3. **Two guides (35, 36) cite a source that does not contain their subject.** The real evidence
   for them is 3,900 lines of shipped MSL inside a repo that was cloned and never read.

Forums are the one modality that was run to completion (all 64 captured thread IDs appear in
the notes). Transcripts were genuinely read, not skimmed. The failure mode here is **repo
directory traversal**, not transcript depth.

---

## 1. Substantive technical areas missing or under-represented

### P0-1 — Non-LLM Core AI is absent from all 50 guides

**Source files dropped:**
- `repos/apple__coreai-models/Package.swift` — lines 21, 27, 33, 37 declare the products
  `CoreAIDiffusion`, `CoreAISegmentation`, `CoreAISpeech`, `CoreAIObjectDetection`, alongside
  `CoreAILM`. Lines 66–110 declare the targets `CoreAIImageSegmenter`, `CoreAIObjectDetector`,
  `CoreAISpeech`, `CoreAIDiffusionPipeline`. Lines 142–179 declare four CLI runners:
  `image-segmenter`, `object-detector`, `diffusion-runner`, `speech-runner`. Lines 228–244
  declare `ImageSegmenterTests`, `DiffusionPipelineTests`, `ObjectDetectorTests`.
- `repos/apple__coreai-models/models/` — 22 model directories. **15 are non-LLM**: `clap`,
  `clip`, `depth-anything`, `edsr`, `efficient-sam`, `flux2`, `pvt`, `roberta`, `sam3`,
  `stable-diffusion`, `t5`, `vlm`, `wav2vec2`, `whisper`, `yolo`. Only `gemma3`, `gpt_oss`,
  `mistral`, `mixtral`, `qwen2`, `qwen3`, `qwen3_moe` are decoder LLMs.

**Verification.** `grep -ric` over `PROPOSED-GUIDE-TOPICS.md`:
`CoreAIDiffusion` = 0 · `CoreAISegmentation` = 0 · `CoreAISpeech` = 0 ·
`CoreAIObjectDetection` = 0 · `diffusion` = 0 · `object detection` = 0 ·
`super-resolution` = 0 · `reranker` = 0 · `Whisper` = 0 · `embedding model` = 0.
The four products *are* named once each in `notes/repos/apple-coreai-models.md` and
`notes/transcripts/coreai-intro.md` — so the research captured them and **the synthesis dropped
them**. `RESEARCH-INDEX.md` line 78 even advertises "the five-product Swift package"; the
proposal inherits none of it.

**What this costs.** Guides 22–34 (13 guides, ~85,000 words of Core AI) are written entirely
around a decode loop: `metadata.json` `kind: language`, four *LLM* engines, KV caches, samplers,
xgrammar, `coreai.llm.export`. A reader converting a YOLO detector, a SAM3 segmenter, an EDSR
upscaler, a CLIP/CLAP encoder or a Flux2 diffusion pipeline gets the `NDArray` memory model
(22) and the conversion contract (26) and then falls off a cliff — no bundle format for
non-`language` kinds, no multi-asset diffusion pipeline scheduling, no image pre/post-processing
contract, no `ImageDescriptor` worked example, no runner CLIs. This is also the single largest
audience gap: object detection / segmentation / super-resolution / ASR is where most Core ML
migrants are coming *from*.

**Recommended fix:** add 2–3 guides to P10 or a new pillar — `coreai-vision-models-end-to-end`
(segmentation, detection, depth, super-resolution: the four Swift products, the four runner
CLIs, `ImageDescriptor`, and the `sam3`/`yolo`/`efficient-sam`/`edsr`/`depth-anything`
recipes), and `coreai-diffusion-and-encoder-models` (`CoreAIDiffusionPipeline`, multi-asset
scheduling, `flux2`/`stable-diffusion`, plus the encoder-only path: `clip`, `clap`, `roberta`,
`t5`, `wav2vec2`, embeddings and rerankers).

### P0-2 — `john-rocky/coreai-model-zoo` was never opened (926 files)

**Source directory dropped:** `repos/john-rocky__coreai-model-zoo/` — cloned, HEAD dated
**2026-07-27** (freshest repo in the corpus), and it has **no notes file**. It appears in the
notes only secondhand, via `repos/issues-community-stack.md` (13 hits) and
`repos/issues-coreai-stack.md` (7 hits) — i.e. it was *issue-mined* but the working tree was
never traversed.

What is in it that was dropped:

| Path | Size | What it contains that the proposal declares unknown |
|---|---|---|
| `knowledge/` | **78 `.md` files, 10,939 lines** | A first-person engineering logbook of porting 61 models to Core AI |
| `knowledge/tensorops-quantized-kernels.md` | 353 lines / 28 KB | Empirical quantized-TensorOps work. §6.1 lists "**The `MTLTensor` scale-plane API is entirely unverified**" as BLOCKING for guides 35–36 |
| `knowledge/aot-and-specialization.md` | 13.5 KB | §6.1 lists "**`coreai-build`'s full CLI surface**" as BLOCKING for guides 23, 34, 47 |
| `knowledge/pipelined-engine.md` | **36 KB** | The four-engine story, engine selection, and the two-state wall — the primary evidence for guide 25, which currently rests on the Apple repo alone |
| `knowledge/coreai-beta-mpsgraph-kvwrite-bug.md`, `coreai-torch-041-ir-incident.md` | 6.2 + 8.2 KB | §6.1: "**Several Core AI beta defects have unknown current status**" — these are dated post-mortems of exactly those defects |
| `knowledge/fm-provider.md` | 14.6 KB | A **fourth** `LanguageModel` conformance (`ZooFMProvider`, `swift/Sources/ZooFMProvider`) with streaming tool calling incl. LFM's native dialect. Guides 15–16 currently read three conformances; this is the only one written up as engineering notes rather than source |
| `knowledge/prefix-cache-kv-reuse.md` | 7.5 KB | Directly the subject of guide 16's transcript-diff/KV-reuse section |
| `knowledge/spec-decode-*.md` (5 files) | ~60 KB | **Speculative decoding on Core AI** — appears in *no* proposed guide (the 4 `speculative decod` hits in the proposal are all MLX) |
| `knowledge/agentic-security-checklist.md` | 13 KB | **Security has no guide at all** in the 50 |
| `knowledge/visual-intelligence-third-party-model.md` | 4.4 KB | `Visual Intelligence` = 0 hits in the proposal; 1 hit in the whole notes corpus (a forum thread) |
| `knowledge/kokoro-tts.md`, `voxcpm-tts.md`, `vibevoice-multispeaker-tts.md`, `chatterbox-port.md` | ~28 KB | §6.3 states "**Speech synthesis / expressive TTS does not exist as an API**" and stops. True of Apple's API — but there is a complete on-device TTS-via-Core-AI story in the corpus that guide 49 declines to mention |
| `knowledge/whisper-asr-fixed-decode.md`, `sortformer-speaker-diarization.md`, `qwen2.5-omni-audio-understanding.md`, `lfm2audio-port.md` | ~31 KB | ASR/diarization/audio-understanding beyond `SpeechAnalyzer`. `diarization` = 0 hits in the proposal |
| `knowledge/raw-metal-loop-playbook.md`, `custom-metal-kernels.md`, `gemma4-raw-metal-port.md`, `gemma4-raw-metal-a19-levers.md` | ~32 KB | A "hand-write the decode loop in raw Metal" modality that exists in no guide |
| `knowledge/coreai-vs-mlx-speed.md`, `performance-ceiling.md`, `apple-models-bench.md` | ~28 KB | An **independent second source** for the Core AI vs MLX numbers that §1 of the proposal currently sources from a single Grade-A community harness |
| `knowledge/evaluations-framework.md`, `dynamic-profiles-local-models.md`, `spotlight-rag-third-party.md`, `compression-reference.md`, `compute-units-and-authoring.md`, `swift-runtime.md`, `stateful-kv-cache.md`, `ship-playbook.md`, `conversion-guide.md` | ~80 KB | Third-party corroboration for guides 19, 10, 6, 29–31, 32, 22, 24, 47, 26 |
| `models/<name>/recipe.toml` × 61 | — | Reproducible per-model export recipes with a `zoo_verify.py` device-verification gate. Guide 34 has Apple's recipes only |
| `conversion/` | ~80 export scripts | `export_*_decode_pipelined.py` per architecture — the concrete shape of the iOS/macOS export contract |
| `BENCHMARKS.md` + `scripts/aggregate_bench.py` | — | A crowd-sourced benchmark with a **published protocol** (`pb-random-v1`: 128-token seed-0 prompt, 256 greedy tokens, `COREAI_CHUNK_THRESHOLD=1`, 1 cold + 3 warm, thermal/Low-Power exclusion, machine-generated blobs). Guide 48's "honest benchmarking" section has no comparable published methodology to cite |
| `skills/skills/{port-a-model-to-the-zoo,reproduce-a-zoo-model}/SKILL.md` | — | Two more agent skills. Guide 32 is built on Apple's three skills; these are the community counterpart |
| `apps/` (13 SwiftUI apps + 5 `.patch` files) | — | `CoreAIChat`, `CoreAIOCR`, `CoreAISegment`, `CoreAITranscribe`, `CoreAIUpscale`, `CoreAIVideo`, `CoreAIDepth`, `CoreAIImageGen`, `MiniCPMVisualIntel`, `TripoSplatMac`. §6.3 says "**Core AI ships with zero Apple sample code**" — these are the closest thing to end-to-end samples that exists, and they cover exactly the non-LLM gap in P0-1 |
| `swift/Sources/{CoreAIRunner,coreai-run,zoo-fm-gate}` | — | Third-party runtime harnesses |
| `PORTING.md`, `CATALOG_PLAN.md`, `AGENTS.md` | — | Never read |

**Caveat to carry.** This is a single-author community repo with a self-declared
non-controlled benchmark (`BENCHMARKS.md`: "This is NOT a controlled-environment benchmark").
`web/community-blogs.md` §9 rightly established an A–D reliability grading; this repo should be
graded before use — but it is *code plus reproducible recipes plus a published protocol*, which
is a different evidentiary class from the fabricated blog posts, and `01-lead-agent-repo-spotchecks.md`
already flagged it as a "community gotcha archive with a sourcing caveat" and then nobody went back.

### P0-3 — MLX's shipped TensorOps call sites were never read, and guides 35–36 cite a source that lacks them

**Source files dropped** (all inside the already-cloned `repos/ml-explore__mlx/`):

- `mlx/backend/metal/kernels/steel/gemm/nax.h` — **887 lines**
- `mlx/backend/metal/kernels/steel/attn/nax.h` — **887 lines**
- `mlx/backend/metal/kernels/quantized_nax.h` — **1,680 lines**
- `mlx/backend/metal/kernels/fp_quantized_nax.h` — **1,018 lines**
- `mlx/backend/metal/kernels/{quantized_nax,fp_quantized_nax}.metal`, `steel/gemm/gemm_nax.h`

These `#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>` and contain real,
compiling call sites, e.g. `steel/gemm/nax.h:401–422`:

```
constexpr auto desc = mpp::tensor_ops::matmul2d_descriptor(
    ...,
    mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);
mpp::tensor_ops::matmul2d<desc, metal::execution_simdgroup> gemm_op;
auto ct_a = gemm_op.template get_left_input_cooperative_tensor<AType, BType, CType>();
auto ct_b = gemm_op.template get_right_input_cooperative_tensor<AType, BType, CType>();
auto ct_c = gemm_op.template get_destination_cooperative_tensor<...>();
```

**Verification.** `grep -ic tensorops notes/repos/mlx-core.md` → **0**. Likewise
`matmul2d` = 0, `MTLTensor` = 0, `cooperative_tensor` = 0, `MetalPerformancePrimitives` = 0 in
that file. Yet guide 35 lists `repos/mlx-core.md` as a source for "*A real production call site
from MLX's own GEMM kernels, with fragment-layout constants*", and `RESEARCH-INDEX.md` line 89
claims that file "*Includes real TensorOps call sites from MLX's own GEMM kernels*". **That
claim is false**; the call sites are in the repo, not in the notes.

This is the highest-value/lowest-cost fix in the whole critique: reading four already-cloned
files resolves the §6.1 BLOCKING item "*The `MTLTensor` scale-plane API is entirely
unverified… Re-harvest against an Xcode 27 SDK*" without needing Xcode 27 at all — MLX compiles
against the real headers today.

It also produces a likely **correction**: MLX's quantized NAX kernels dequantize by hand
(`fp_quantized_nax.h:36` casts through `fp8_e8m0`) rather than attaching scale planes to an
`MTLTensor`. Guide 35's planned section "*feeding quantized tensors straight to `matmul2d` and
letting TensorOps dequantize*" may be describing a path that the reference implementation
deliberately does not take. Verify before asserting.

### P1-4 — `john-rocky/coreai-models` (the fork) was never opened (364 files)

`repos/john-rocky__coreai-models/README.md` lines 1–40 are a precise, dated changelog of a
minimal additive patch to Apple's pipelined engine: `≥2` states for hybrid/SSM bundles
(Qwen3.5/3.6 GatedDeltaNet, LFM2.5, Granite 4 Mamba2 — the `Expected 2 states, got 4` failure),
`EngineOptions.perTokenInputProvider` (Gemma per-layer-embedding rows),
`EngineOptions.staticInputBuffers`, a static-shape logits-buffer sizing fix for decode-only
`S=1` graphs, an SSM state-descriptor shape fix in `python/.../primitives/macos/cache.py`, and
a **consumer-break stop fix** with a measured result: *"a two-turn chat through Apple's own
`CoreAILanguageModel` adapter dropped its second-turn latency from 2.74 s to 0.40 s, with
byte-identical output."*

The proposal already asserts both the two-state wall (guides 25, 34, §6.1) and post-EOS
overshoot poisoning the cache (guide 16) — but sourced from issue-mining paraphrase, not from
the patch. The exact `EngineOptions` surface and the diff scope
(`swift/.../InferenceEngines/{CoreAIPipelinedEngine,EngineFactory}.swift` only) were never read.
§6.1's open question "*Whether hybrid/SSM support has landed… Check `apple/coreai-models` HEAD*"
is directly answerable from this tree plus one `gh` call.

### P1-5 — Security / prompt-injection has no guide

`agentic-security-checklist.md` (13 KB) exists in the unread zoo repo; guide 3 covers the
instructions-vs-prompts injection defense in two bullets; guide 8 covers guardrails; guide 16
covers auth. But an agent with `.toolCallingMode(.required)`, a Spotlight retrieval tool reading
user documents, and a `ChatCompletionsLanguageModel` pointed at a local server is a
prompt-injection surface, and nothing in the 50 addresses it as a topic. Note also
`CVE-2026-5843` (mlx-lm `config.json` `model_file` → arbitrary Python on a plain `load()`),
which is currently a single bullet inside guide 40.

---

## 2. Proposed topics NOT well supported by the notes

Verified by grepping the notes corpus for each topic's load-bearing API names. Counts are
occurrences per file.

| # | Topic | Verdict | Evidence |
|---|---|---|---|
| **35** | `tensorops-matmul-and-quantized-tensors` | **Single-sourced.** Effectively one transcript. | `matmul2d`: coreai-python-metal.md **23**, mlx-core.md **0**, apple-docs-coreai.md **0**. `MTLTensor`: 44 / 0 / 0. `MetalPerformancePrimitives`: 8 / 0 / 0. `static_slice`: 6 / 0 / 0. The cited second source contains none of it (see P0-3). |
| **36** | `tensorops-cooperative-tensors-and-flashattention` | **Single-sourced**, and the demoed MSL was never read aloud (proposal admits this). | `cooperative_tensor`: coreai-python-metal.md **30**, mlx-core.md **0**. `reduce_rows`: 9 / 0. `map_iterator`: 13 / 0. `execution_simdgroup`: 9 / 0. |
| **49** | `speech-analyzer-end-to-end` (**9,000 words**) | **Single-sourced** — one doc harvest, no transcript, no forum corroboration beyond the TTS negative, no repo. | `SpeechAnalyzer` appears in exactly **two** notes files: `web/apple-docs-fm-evals-speech.md` (15) and `00-ORIENTATION` (3). `forum-pain-points.md` = **0**. `SpeechTranscriber` 23/0/0, `SpeechDetector` 14/0/0, `contextualStrings` **2**, `ModelRetention` **2**. **`finishAndFinalize` = 0 hits anywhere in the corpus** yet is a named key section. Also: the local mirrors `docs/Recognizing speech in live audio.md` (16.6 KB) and `docs/Bringing advanced speech-to-text capabilities to your app.md` were only skim-read by the lead agent (`00-ORIENTATION` line 9: "All 6 files in `docs/`") and produced no dedicated notes file. 9,000 words is not supportable at this evidence density. |
| **6** | `fm-spotlight-rag-and-system-tools` — the OCR/Barcode half | **Explicitly unharvested.** | `web/apple-docs-fm-evals-speech.md:1586` — "*`OCRTool` and `BarcodeReaderTool` live at `/documentation/Vision/OCRTool` and `/documentation/Vision/BarcodeReaderTool` — **NOT fetched this session**; another agent should harvest the Vision framework updates*", repeated at :3631 and :3732. All existing evidence is one sentence of transcript paraphrase (`fm-core.md:345–346`) plus one docs snippet. The Spotlight half is strong; the tools half is not. |
| **18** | `fm-cli-and-python-sdk` | Already ⚠-flagged; confirmed. | `fm serve` appears in **one** non-synthesis file (`repos/issues-community-stack.md`). Not in `transcripts/fm-core.md`. Correctly deferred. |
| **50** | `dnikit-dataset-and-model-introspection` | Already ⚠-flagged; confirmed. | Sourced from one repo note. Correctly deferred. |

**Not pattern-matched from pre-2026 memory** — I checked for that specifically and found no
instance. Every 2026-era API in the topic list has real corpus grounding:
`DynamicProfile` (7 non-synthesis files), `LanguageModelExecutor` (11),
`PrivateCloudComputeLanguageModel` (10), `ChatCompletionsLanguageModel` (6),
`SessionPropertyEntry` (3), `TrajectoryExpectation` (4), `SampleGenerator` (4),
`ScoreDimension` (4), Cohen's kappa (3), `xgrammar` (10), `JACCL` (5), `TurboQuant` (2),
`InterleaveLayout` (2), `TorchMetalKernel` (7), `gated_delta_update` (5),
`expectFrequentReshapes` (7), `logFeedbackAttachment` (4), `BGContinuedProcessingTask` (1),
`coreai-build` (9). The synthesis is disciplined. The failure is **omission, not invention** —
with the one exception of the `repos/mlx-core.md` source attribution on guide 35 (P0-3), which
is a citation to material that does not exist in the cited file.

Two second-order notes:
- `TurboQuant` and `BGContinuedProcessingTask` each rest on a single repo note. Fine, but they
  are stated as fact in guides 44 and 47 — mark them.
- Guide 22 (7,000 words) and guide 23 (6,500 words) rest almost entirely on
  `web/apple-docs-coreai.md`, since §6.3 confirms Core AI ships zero Apple sample code. The zoo
  repo's `knowledge/swift-runtime.md`, `stateful-kv-cache.md` and 13 SwiftUI apps are the only
  independent corroboration available anywhere — another reason P0-2 matters.

---

## 3. Research modalities never run

**Repo directory traversal — the big one.**
- `repos/john-rocky__coreai-model-zoo/` (926 files) — never opened. See P0-2.
- `repos/john-rocky__coreai-models/` (364 files) — never opened. See P1-4.
- `repos/ml-explore__mlx/mlx/backend/metal/kernels/**` — the Metal kernel sources were never
  read despite being the only shipped TensorOps code in the corpus. See P0-3.
- `repos/apple__coreai-models/swift/Sources/{CoreAIImageSegmenter,CoreAIObjectDetector,CoreAIDiffusionPipeline,CoreAISpeech}`
  and the 15 non-LLM `models/` recipe directories. See P0-1.
- Net: **2 of 16 repos entirely unread; 4 more read only along their LLM axis.**

**Doc pages never fetched** (each flagged in the notes themselves, then not actioned):
- `https://developer.apple.com/documentation/Vision/OCRTool`
- `https://developer.apple.com/documentation/Vision/BarcodeReaderTool`
- The Vision framework's 2026 updates page generally.
- Apple's sample-code projects — **Origami** (dynamic profiles), **Book Tracker** (Evaluations,
  31 KB), the generative-game-content sample, the advanced speech-to-text sample.
  `RESEARCH-INDEX.md` line 130 and proposal §6.4 both call these "*the richest end-to-end
  examples in existence*" and "*the highest-value cheap follow-up*" — and nobody fetched them.
- The PCC entitlement application page (§6.2 asks for one more confirmation of the Small
  Business Program condition).

**Forum threads — fully run.** All **64** thread IDs appearing in the four RSS captures also
appear in the notes. This modality has no gap. The only forum-adjacent gap is scope: four topic
feeds were captured, and the App Intents / Siri cluster was deliberately deferred (§6.4) because
sessions 240/343/345 are absent from the transcript corpus.

**Transcripts — genuinely read, not skimmed.** Per-session mention counts across all notes:
242=221, 205=184, 298=182, 241=159, 299=150, 335=131, 243=125, 324=108, 325=95, 339=92, 334=91,
326=79, 246=72, 319=66, 232=58, **330=51**. Session 330 is the thinnest *and* is the sole
support for two 5,500–6,000-word guides (35, 36) — that is a read-*depth* risk concentrated on
one file, not a skim.

**Never run at all: execution.** §6.1 is honest that nothing was built or run. Beyond that,
one cheap non-execution modality was also skipped: **no post-sweep `gh` status check** on the
repos whose HEAD state §6.1 says would change the advice (the four unmerged `coreai-torch` PRs,
`apple/coreai-models` hybrid/SSM support). The clones are `--depth`-limited snapshots dated
2026-06-09 to 2026-07-27; `mlx2coreai` is the stalest at 2026-06-09.

---

## 4. Highest-value next research actions, before writing begins

Ordered by (value × cheapness). Actions 1–4 need no new machine and no Xcode 27.

### A1. Read the zoo `knowledge/` directory — one agent, one pass
Closes at least five §6.1 BLOCKING items and P0-2 in a single sweep. Priority order:

```
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/tensorops-quantized-kernels.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/pipelined-engine.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/aot-and-specialization.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/fm-provider.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/prefix-cache-kv-reuse.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/coreai-beta-mpsgraph-kvwrite-bug.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/coreai-torch-041-ir-incident.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/compute-units-and-authoring.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/swift-runtime.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/stateful-kv-cache.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/conversion-guide.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/coreai-vs-mlx-speed.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/performance-ceiling.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/agentic-security-checklist.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/visual-intelligence-third-party-model.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/spec-decode-design.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/spec-decode-hybrid-verify-design.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/raw-metal-loop-playbook.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/custom-metal-kernels.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/knowledge/README.md
```
Plus `PORTING.md`, `BENCHMARKS.md`, `skills/skills/*/SKILL.md`, and
`swift/Sources/ZooFMProvider/`. Write to `notes/repos/coreai-model-zoo.md` **with an explicit
reliability grade** per `web/community-blogs.md` §9 — this is community, single-author,
self-declared-uncontrolled-benchmark material, and every number lifted from it must be
attributed as such and never presented as Apple-official.

### A2. Read MLX's TensorOps kernels — resolves two BLOCKING gaps with zero new tooling
```
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/steel/gemm/nax.h
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/steel/attn/nax.h
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/quantized_nax.h
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/fp_quantized_nax.h
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/steel/gemm/gemm_nax.h
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/quantized_nax.metal
/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/backend/metal/kernels/fp_quantized_nax.metal
```
Extract: every `mpp::tensor_ops::*` spelling actually used; the `matmul2d_descriptor` argument
order and `mode::` cases; `metal::execution_simdgroup` vs other scopes; the
`get_{left_input,right_input,destination}_cooperative_tensor` template signatures; how quantized
weights are actually fed (hand-dequant via `fp8_e8m0` vs scale planes). Then **correct guide 35's
source list**, which currently cites `repos/mlx-core.md` for material that file does not contain.
Also worth a `git log` on these paths to date the NAX/M5 support:
```
git -C "/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx" log --oneline -- mlx/backend/metal/kernels/steel/gemm/nax.h
```

### A3. Read `apple/coreai-models`' non-LLM half — unblocks the P0-1 guides
```
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/Package.swift
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/swift/Sources/CoreAIImageSegmenter/
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/swift/Sources/CoreAIObjectDetector/
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/swift/Sources/CoreAIDiffusionPipeline/
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/swift/Sources/CoreAISpeech/
/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/models/{sam3,yolo,efficient-sam,edsr,depth-anything,stable-diffusion,flux2,clip,clap,wav2vec2,whisper,roberta,t5,pvt,vlm}/
```
Target the `metadata.json` `kind:` values for non-`language` bundles, the image pre/post-processing
contract, and the four runner CLIs' flags. Write to `notes/repos/coreai-models-vision-audio.md`.

### A4. Read the fork's patch + one `gh` call to answer §6.1's hybrid/SSM question
```
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-models/README.md
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-models/swift/Sources/.../InferenceEngines/CoreAIPipelinedEngine.swift
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-models/swift/Sources/.../InferenceEngines/EngineFactory.swift
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/apps/coreai-pipelined-extra-states.patch
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/apps/coreai-prefix-cache.patch
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/apps/coreai-pipelined-per-token-inputs.patch
/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo/apps/coreai-pipelined-static-inputs.patch
```
```bash
gh api repos/apple/coreai-models/commits --paginate -q '.[] | "\(.commit.author.date) \(.sha[0:8]) \(.commit.message|split("\n")[0])"' | head -50
gh search commits --repo apple/coreai-models "state" --limit 30 --json commit,sha
gh issue list  --repo apple/coreai-models --state all --search "states OR hybrid OR mamba OR GatedDeltaNet" --limit 40
```

### A5. Refresh the beta-defect status that §6.1 says changes advice in three guides
```bash
gh pr list --repo apple/coreai-torch --state all --limit 60 \
  --json number,title,state,mergedAt,updatedAt \
  --jq '.[] | "\(.state)\t\(.mergedAt // .updatedAt)\t#\(.number)\t\(.title)"'
gh issue list --repo apple/coreai-torch --state all --limit 60 --json number,title,state,updatedAt
gh release list --repo apple/coreai-torch --limit 10
gh release list --repo apple/coreai-optimization --limit 10
gh release list --repo apple/foundation-models-utilities --limit 10
gh release list --repo ml-explore/mlx-swift-lm --limit 10
```
Specifically resolve: the four unmerged `coreai-torch` PRs (stable fp16 softplus/mish/logsumexp,
integer true-divide promotion, intx cat dim, int64 accumulator narrowing); the `optimize()`
~17 dB PSNR miscompile; the linear-INT4 ANE pre-compile SIGSEGV; the macOS 26→27 export-lowering
2.2× regression. Also refresh the two stalest clones:
```bash
git -C "/Volumes/ExtStor/FM and MLX and CoreAI/repos/lucasnewman__mlx2coreai" fetch --depth 50 && git -C ... log --oneline -10
git -C "/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__python-apple-fm-sdk" fetch --depth 50 && git -C ... log --oneline -10
```

### A6. Fetch the four Apple doc pages that the notes themselves flag as unfetched
```
https://developer.apple.com/documentation/vision/ocrtool
https://developer.apple.com/documentation/vision/barcodereadertool
https://developer.apple.com/documentation/vision            (2026 updates index)
https://developer.apple.com/documentation/updates/vision
```
Unblocks guide 6's second half. Use the same sosumi.ai extraction path the `web/` fleet used.

### A7. Download and read Apple's sample-code projects (§6.4's own "highest-value cheap win")
Sample-code zips hang off the article pages; harvest the download URLs from:
```
https://developer.apple.com/documentation/foundationmodels          (Origami / dynamic profiles)
https://developer.apple.com/documentation/evaluations               (Book Tracker, ~31 KB)
https://developer.apple.com/documentation/foundationmodels/generating-game-content
https://developer.apple.com/documentation/speech/bringing-advanced-speech-to-text-capabilities-to-your-app
```
These are the only Apple-authored end-to-end code in existence for guides 10, 12, 19–21 and 49 —
and guide 49 (9,000 words, single-sourced) cannot honestly be written at its planned length
without the speech sample.

### A8. Re-scope before writing
- Add the P0-1 guides (vision / diffusion / encoder / audio Core AI) — 2–3 new topics.
- Add a security topic, or fold `agentic-security-checklist.md` into guide 5 and guide 16 and
  say so explicitly in the pillar table.
- Cut guide 49 from 9,000 → ~5,000 words unless A7 lands, and drop `finishAndFinalize` from its
  key sections until it is attested anywhere.
- Split guide 6: keep the Spotlight half at full length, gate the OCR/Barcode half on A6.
- Correct guide 35's `Sources` line and `RESEARCH-INDEX.md` line 89.
- Decide explicitly whether speculative decoding on Core AI and the raw-Metal decode loop are
  in or out of scope; right now they are out by omission rather than by decision.

---

## 5. What the sweep got right (so it is not re-litigated)

- Forums: complete. 64/64 captured threads traced into the notes, with live thread fetches to
  recover truncated Apple-staff replies. This is the strongest part of the corpus.
- Transcripts: all 16 sessions have substantial per-session sections with line-cited quotes and
  a `VERBATIM`/`RECONSTRUCTED`/`UNVERIFIED` convention. No session was skimmed.
- The `community-blogs.md` A–D reliability grading and the §9 catalogue of two fabricated
  sources is the single best editorial decision in the sweep. Carry it into A1.
- §6.1–6.4 of the proposal is unusually honest self-accounting; every BLOCKING item I checked is
  real. The critique above mostly says: **four of those items are answerable from material
  already on this disk, without a live machine.**
