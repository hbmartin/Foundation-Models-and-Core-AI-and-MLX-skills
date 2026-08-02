# MLX — training beyond `mlx_lm.lora`, release timeline, and ecosystem inventory

**Harvested 2026-08-02.** Targets three self-declared gaps in
`guides/part-12-mlx-python/references/06-finetuning-and-porting-models.md`:

- `:1211` 🔴 "**no quality comparison exists in this corpus.** mlx-lm ships no LoRA-vs-DoRA-vs-full …"
- `:1464` 🔴 "**no rank/target ablation exists in this corpus.** mlx-lm publishes no rank sweep …"
- `:1820` 🔴 "**no measured checkpointing overhead.** Neither mlx-lm nor this corpus publishes …"

**Headline result: those three gaps cannot be closed from mlx-lm, but they can be *reframed*.**
mlx-lm genuinely publishes none of it — that finding stands. What exists is a **third-party
training layer built on top of mlx-lm** that the corpus does not mention at all, and it publishes
throughput and memory numbers (though still not quality ablations).

---

## 1. `mlx-lm-lora` — the training superset (0 corpus references)

`https://github.com/Goekdeniz-Guelmez/mlx-lm-lora` · `pip install -U mlx-lm-lora` ·
also on PyPI. Grep of `guides/` for `mlx-lm-lora`: **0 hits**. Grep for `GRPO`: **2 hits**.

> ⚠️ **Evidence tier: third-party project README.** Everything below is what the project claims
> about itself. None of it is Apple, and none of it was run on this machine. Mark 🟠/🟡 and
> attribute to the project by name. The benchmark table in §1.3 in particular is a **vendor
> self-comparison against its own competitors** and should be presented as such.

### 1.1 Twelve training algorithms

mlx-lm's own `mlx_lm.lora` offers LoRA / DoRA / full / (automatic) QLoRA. `mlx-lm-lora` claims:

| Family | Methods |
|---|---|
| Supervised | **SFT** |
| Offline preference | **DPO**, **CPO**, **ORPO** |
| Group-relative RL | **GRPO**, **GSPO**, **Dr. GRPO**, **DAPO** |
| Online / judge-in-the-loop | **Online DPO**, **XPO**, **RLHF Reinforce**, **PPO** |

Plus **QAT (quantization-aware training)** — "projects weights onto quantized grids during
training" — supported for SFT, DPO and ORPO.

**Why this matters for the guide series.** Part 12.6 currently presents Apple's MLX training story
as LoRA/DoRA/full/QLoRA, which is accurate for `mlx-lm`, and Part 6 (Evaluations) discusses judges
and alignment. There is no bridge between them: nothing in the corpus tells a reader that
**preference optimisation and RL post-training are available on Apple silicon at all**. That is a
structural gap, not a detail. It also connects to Part 9 (compression/numerics) via QAT — the
corpus covers post-training quantization thoroughly and QAT thinly.

### 1.2 CLI surface (as documented by the project)

```
mlx_lm_lora.train --model <model_path> --data <data_path> --train
```

Selected flags, grouped:

| Group | Flags |
|---|---|
| Core | `--config` (YAML), `--train-type {lora,dora,full}`, `--train-mode {sft,dpo,cpo,orpo,grpo,…}`, `--batch-size`, `--iters`, `--epochs`, `--learning-rate`, `--adapter-path`, `--max-seq-length` (default 2048), `--num-layers` (-1 = all), `--lora-parameters '{"rank": 8, "dropout": 0.0, "scale": 10.0}'` |
| Load-time quant | `--load-in-4bits`, `--load-in-6bits`, `--load-in-8bits` |
| **QAT** | `--qat-enable`, `--qat-bits` (default 8), `--qat-group-size` (default 64, `0` = per-tensor), `--qat-mode` (default `affine`), `--qat-start-step` (default 1), `--qat-interval` (default 1) |
| DPO/CPO | `--beta`, `--dpo-cpo-loss-type {sigmoid,hinge,ipo,dpop}`, `--reference-model-path` |
| ORPO | `--beta`, `--reward-scaling` |
| GRPO family | `--group-size` (default 4), `--epsilon`, `--temperature` (default 0.8), `--max-completion-length`, `--reward-functions`, `--reward-weights`, `--grpo-loss-type {grpo,bnpo,dr_grpo}` |
| Online | `--judge` (model id or the literal `human`), `--alpha` (default 1e-5) |
| Optimizer | `--optimizer {adam,adamw,qhadam,muon}`, `--lr-schedule {cosine,linear,constant}` |
| Memory | `--grad-checkpoint`, `--gradient-accumulation-steps` |
| Ops | `--steps-per-report`, `--steps-per-eval`, `--val-batches`, `--save-every`, `--wandb`, `--fuse` |

Custom reward functions are registered in Python and passed by name:

```python
from mlx_lm_lora.reward_functions import register_reward_function

@register_reward_function()
def my_reward(prompt, completion, reference_answer, **kwargs):
    return score  # float 0-1
```
```
--reward-functions-file ./my_rewards.py --reward-functions "my_reward"
```

Judge training has its own entry point: `python -m mlx_lm_lora.train_judge --model <model>
--train-type full --data <data>`. **Cross-reference Part 6.2 (model judges and alignment, 11 🔴)** —
this is a local, MLX-native way to train the judge that Part 6 discusses in Evaluations terms.

### 1.3 The published throughput/memory table

Setup as stated: **M4 Pro (24 GB unified) vs NVIDIA A100 (80 GB)**, 0.6B–8B models, **100 training
steps, batch size 1, context length 4096**.

| Run | mlx-lm-lora | Unsloth (A100) | mlx-tune |
|---|---|---|---|
| Qwen3-0.6B **SFT** | ~4.7 it/s, 2–2 GB | ~2.7 it/s, 1–2 GB VRAM | ~0.6 it/s, 4–6 GB |
| Qwen3-0.6B **ORPO** | ~4.5 it/s, 2–4 GB | ~2.4 it/s, 2–8 GB VRAM | **OOM** |
| Qwen3-8B **SFT (4-bit)** | ~4.1 it/s, 6–10 GB | ~1.3 it/s, 10–16 GB VRAM | ~0.07 it/s, 8–18 GB |

Memory guidance by model size (project's own):

- 1–3B: `--batch-size 4 --num-layers 16`
- 7B: `--batch-size 2 --num-layers 8 --load-in-8bits`
- 13B+: `--batch-size 1 --num-layers 4 --load-in-4bits --grad-checkpoint`

> 🚩 **Handle with tongs.** An M4 Pro beating an A100 on it/s at batch size 1 is a *latency* result
> at a batch size that maximally disadvantages the GPU; it says nothing about throughput at the
> batch sizes an A100 would actually be run at. Part 15's honest-benchmarking guide has exactly the
> right frame for this. If the table is cited, cite it **with** the batch-size-1 caveat, or don't
> cite it. The **memory-envelope** rows are the more defensible half — and the unified-memory
> argument ("up to 512 GB on Apple Ultra vs NVIDIA's 24–80 GB typical") is a structural claim, not
> a benchmark.

### 1.4 Dataset formats (directly useful for Part 12.6 and Part 6.3)

Local: `data/{train,valid,test}.jsonl`. HF: `--data "dataset/name"`. Field mapping via
`--text-feature`, `--chat-feature`, `--prompt-feature`, `--completion-feature`,
`--chosen-feature`, `--rejected-feature`, `--system-feature`.

```json
// SFT (chat)
{"messages": [{"role":"system","content":"You are helpful"},{"role":"user","content":"Question"},{"role":"assistant","content":"Answer"}]}
// SFT (completion)
{"prompt": "Question", "completion": "Answer"}
// DPO / CPO / ORPO
{"prompt": "Question", "chosen": "Good", "rejected": "Bad"}
// GRPO
{"prompt": "Problem", "answer": "Solution", "system": "Instructions"}
// Online (Online DPO, XPO, RLHF, PPO)
{"prompt": [{"role": "user", "content": "Question"}]}
```

Part 6.3 (`03-synthetic-data-and-tool-trajectories.md`) covers synthetic dataset generation for
Evaluations; these are the *consumption* formats on the MLX side. Worth a bridge paragraph.

## 2. `mlx-tune` — the Unsloth-API-compatible alternative (0 corpus references)

`https://github.com/ARahim3/mlx-tune`. Methods: SFT, DPO, ORPO, GRPO, **KTO**, **SimPO**, plus
dedicated trainers for **vision, TTS, STT, embeddings and OCR**. Requirements: Apple silicon
M1–M5, macOS 13.0+, 8 GB+ unified RAM (16 GB+ recommended), Python 3.9+, **MLX 0.20+**.

Its distinguishing claim is a **"100% compatible" Unsloth API** — `FastLanguageModel` and
`SFTTrainer` so "training scripts written once … work identically whether training on Mac or CUDA
GPUs." **That is the single most guide-relevant fact in this file for Part 14 (bridges between
stacks)**: a source-compatible path between the CUDA training ecosystem and Apple silicon. Publishes
no benchmarks of its own (the numbers in §1.3 are its competitor's).

## 3. Release timeline — corrected dates

An earlier fetch of the GitHub *releases HTML* returned confidently wrong years (2023/2024). The
**GitHub REST API** returns correct `published_at` values; use `api.github.com/repos/<o>/<r>/releases`
for anything date-sensitive. Corrected:

### `ml-explore/mlx`

| Version | Published | Notable |
|---|---|---|
| **v0.32.0** | **2026-07-07** | `mlx.core.linalg` determinant + sign-log-determinant; `flip`, `unstack`; array-API `empty`/`empty_like`/`astype`/`matrix_transpose`; CUDA quantized-kernel fixes; **53 new contributors** |
| v0.31.2 | 2026-04-22 | "Wider support for cuda quantized matmuls"; **"MLX can be used by multiple threads for independent computations"**; CUDA FFT; **"JACCL is now a standalone lib"** |
| v0.31.1 | 2026-03-12 | CUDA quantized GEMV; "[CUDA] Support 3/5/6-bit quants in QMV" |
| v0.31.0 | 2026-02-28 | "Initial version of QMMs for CUDA"; JACCL mesh bandwidth; "Massive speedups for 3D convs" |
| v0.30.6 | 2026-02-06 | "Much faster bandwidth with JACCL on **macOS >= 26.3**" |
| v0.30.4 | 2026-01-27 | Metal faster vector fused GQA; CUDA dense MoE; better consumer-GPU support |
| **v0.30.3** | **2026-01-13** | **"Support nvfp4 and mxfp8 quantized ops on Metal"** + quantized-quantized matmul on CUDA |
| v0.30.1 | 2025-12-18 | **"RDMA over thunderbolt with the JACCL backend (macOS >= 26.2)"**; "NAX with JIT so that they can be used in MLX Swift" |
| **v0.30.0** | **2025-11-19** | **"Support for Neural Accelerators on M5 (macOS >= 26.2)"** |

The guides already cite 0.31.5 / 0.32.1 in places, so **the corpus is current on MLX core** — the
value here is the corrected *dates* and the OS-version gates (`macOS >= 26.2` for M5 Neural
Accelerators and Thunderbolt RDMA; `>= 26.3` for the JACCL bandwidth win), which are gating facts
Part 12.2 and Part 1.2 should carry.

### `ml-explore/mlx-swift` (latest **0.31.6**, 2026-07-02)

- **0.31.6** (2026-07-02) — iOS build fixes (guarded `Process` usage); "align complex64 finfo with NumPy"
- **0.31.5** (2026-06-30) — SwiftPM tools 6.3; **`MultiOptimizer` and `Muon` optimizer** ported from Python `mlx.optimizers`; **learning-rate schedules**; Linux CUDA compilation via SwiftPM
- **0.31.4** (2026-06-01) — `QuantizedLinear` fixes for non-affine modes (**mxfp4**); AdamW bias correction; `compile()` overloads to 8 inputs / 4 outputs
- **0.30.6** (2026-02-10) — wired memory management; **NAX / Neural Accelerator hardware-detection fix (iPhone 16 Pro)**; Linux CPU-only via SwiftPM

The 0.31.5 optimizer/LR-schedule additions matter for Part 13 — on-device *training* in Swift is
newly practical, and `Muon` is not a name the corpus carries.

### `ml-explore/mlx-lm` (latest **v0.31.3**, 2026-04-22)

Training-relevant: v0.31.0 (2026-03-07) added **tensor parallelism for Qwen 3.5**; v0.30.6
(2026-02-04) added **distributed inference in the server** and Transformers v5 support; v0.30.4
(2026-01-19) added **AWQ/GPTQ weight-transformation utilities**; v0.30.0 (2025-12-18) added
**model-parallel generation**.

> Note the asymmetry worth stating in Part 12.5: **distributed *inference* landed in mlx-lm's
> server; distributed *training* is a WWDC26 session-233 story and an MLX-core capability, not an
> mlx-lm CLI feature.**

## 4. Apple ML Research — "Exploring LLMs with MLX and the Neural Accelerators in the M5 GPU"

`https://machinelearning.apple.com/research/exploring-llms-mlx-m5` — **first-party Apple, and not
in the corpus's URL inventory.**

- Hardware: **MacBook Pro M5, 24 GB unified**, vs an M4 MacBook Pro of similar configuration.
- Models: Qwen 1.7B (BF16), Qwen 8B (BF16 and 4-bit), Qwen 14B (4-bit), Qwen 30B MoE / 3B active
  (4-bit), GPT-OSS 20B (native **MXFP4**), FLUX-dev-4bit (12B) for images.
- Protocol: **prompt 4096 tokens, generate 128** — measuring TTFT (s), generation (tok/s), memory (GB).
- Results: **TTFT speedup 3.33×–4.06×** ("up to 4x speedup compared to a M4 baseline for
  time-to-first-token"); **generation speedup only 1.19×–1.27×**, explicitly attributed to being
  **memory-bandwidth-bound**. FLUX-dev "more than **3.8x faster** on a M5".
- Gate: **"MLX requires macOS 26.2 or later"** to use M5 Neural Accelerators.

> ⭐ This is the cleanest first-party statement of the **prefill-vs-decode asymmetry** anywhere in
> the corpus's reach: the Neural Accelerators help the compute-bound phase ~4× and the
> bandwidth-bound phase ~1.2×. Part 15.2 (memory, thermals, honest benchmarking) and Part 12.2
> (numerics/hardware gating) should both carry it, and it is the correct rebuttal to any
> "M5 is 4× faster" summary.

## 5. Ecosystem inventory — `awesome-mlx`

`https://github.com/raullenchai/awesome-mlx` catalogues ~140 projects. Categories and the entries
most relevant to this guide series (full list in the source):

- **Training & fine-tuning:** `mlx-lm-lora`, `mlx-tune`, `MLX-GRPO`, `SiLLM`, `TransformerLab`,
  `rlx`, `mlx-lm-gui`, `Tiny-Lab`, `nanoGPT_mlx`, `mlx-gpt2`, `mlx-snn`.
- **Serving / distributed:** `mlx_sharding` (distributed inference across devices),
  `mlx-omni-server`, `fastmlx`, `swama` (native Swift engine), `SwiftLM` ("SSD streaming for 100B+
  MoE"), `Toolio` (**JSON-schema steering + tool calling** — a direct analogue of guided
  generation, relevant to Part 13.3), `omlx`, `Rapid-MLX`.
- **Swift:** `mlx-swift-structured` (**structured output generation** — again a guided-generation
  analogue), `MLX-Outil` (tool calling across iOS/macOS/visionOS), `LocalLLMClient`,
  `fullmoon-ios`, `mlx-swift-chat`.
- **Audio/speech — relevant to Part 16.1:** `speech-swift` ("ASR, TTS, speech-to-speech, VAD, and
  diarization powered by **MLX and CoreML**"), `mlx-audio`, `parakeet-mlx`, `lightning-whisper-mlx`,
  `Lightning-SimulWhisper` (~15× faster streaming), `TheWhisper`, `f5-tts-mlx`, `csm-mlx`.
- **Benchmarks:** `mlx-benchmark` (**MLX ops vs MPS vs CUDA** — a candidate cross-check for Part 15),
  `Metal-Puzzles` (Metal GPU programming exercises — relevant to Part 11), `mlx-bitnet` (1.58-bit).
- **Bridges/tools:** `llmfit` (identify models that fit your hardware), `outlinesmlx` (guided
  generation), `einops` with MLX support, `mlx-c`, `mlx-rs`, `node-mlx`, `emlx`.

**Use:** this is a *pointer inventory*, not evidence. Its value is that Part 12/13/14 can name the
existing solution instead of describing a hole — e.g. Part 13.3 (FM bridge and guided generation,
18 🔴) currently reasons about guided generation in MLX Swift from first principles, and
`mlx-swift-structured`, `Toolio` and `outlinesmlx` are three prior-art implementations to compare
against.

## 6. What this file does NOT close

- 🔴 **`:1211` LoRA-vs-DoRA-vs-full quality comparison** — still nonexistent. mlx-lm-lora publishes
  *throughput*, not quality. **Recommendation: keep the gap and add one sentence recording that a
  survey of the third-party training layer also found no quality ablation** — that turns an absence
  of evidence into a documented negative result.
- 🔴 **`:1464` rank/target ablation** — same. No source found.
- 🔴 **`:1820` checkpointing overhead** — same; `--grad-checkpoint` exists in both projects and
  neither measures it. **This is a measurable-on-this-machine item** — a candidate for `probes/`
  or a small local benchmark rather than more searching.
