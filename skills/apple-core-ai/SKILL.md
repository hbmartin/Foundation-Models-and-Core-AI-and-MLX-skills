---
name: apple-core-ai
description: "Core AI, the new-in-27 runtime that supersedes Core ML: import CoreAI, AIModel, NDArray, model bundles and engines, guided decoding, specialization, caching and ahead-of-time compilation - plus the Python side, converting a torch.nn.Module to an .aimodel with coreai-torch, op coverage and composites, custom Metal kernels, quantization, palettization and pruning, numeric formats, ANE-versus-GPU authoring rules, debugging, profiling and end-to-end LLM export."
when_to_use: "Use for any .aimodel or import CoreAI work: a target that fails to build with a missing Metal compiler error, an unsupported-op conversion failure, a model that silently falls back off the Neural Engine, a compiled model that loads but runs far slower than expected, or compression that quietly costs accuracy."
---

# Core AI: the 27-cycle inference runtime and its conversion pipeline

Part 7, Part 8, Part 9, Part 10 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

## Evidence markers — never flatten these

Every non-obvious claim in `references/` carries one of these. Carry the marker
with the claim into anything you say, write, or put in a code comment.

- ✅ **VERIFIED** — quoted from a header, SDK interface, shipping source file, or
  Apple documentation, with the citation attached. Safe to rely on.
- 🟡 **RECONSTRUCTED** — the concept is attested, usually from a WWDC session, but
  the exact spelling is inferred. Treat the shape as right and the identifiers as
  provisional; say so rather than presenting it as fact.
- 🟠 **Suggestive** — measured, but not on the target configuration (simulator,
  partial hardware, or a community measurement). Directional only.
- 🔴 **GAP** — could not be verified. The callout names what is unknown and what
  would resolve it. Never guess past one.
- ⚠️ **SILENT FAILURE** — fails without throwing. Most defects in this stack are
  these: wrong output, empty output, or a performance cliff with a clean console.

## Find the answer in three moves

`references/` holds far more than fits in context. Never read a file whole —
route to the section you need:

1. **You have a symptom** (wrong output, empty result, silent no-op, perf cliff,
   something ignored) — `Grep` `references/SILENT-FAILURES.md` for words from what
   you actually observed. Entries are grouped by symptom and each links to the
   guide section that explains it.
2. **You have a symbol** (`LanguageModelSession`, `AIModel`, `mx.compile`, …) —
   `Grep` `references/API-INDEX.md`. The row shows whether the symbol appears in
   the captured 26.5 and 27.0 SDK interfaces; **blank in both columns means the
   spelling is not SDK-confirmed**, so treat it as provisional.
3. **You have a task** — use the triage table below, then the part README it
   points at.

The deep reference guides are not bundled. `references/SECTION-MAPS.md` lists
every section of every one with its anchor; fetch a single section rather than a
whole file.

## Version floors

| Part | Floor |
|---|---|
| [7](references/part-07-coreai-swift-runtime/README.md) | everything here is **27.0 and only 27.0**. |
| [8](references/part-08-coreai-pytorch-conversion/README.md) | `coreai-torch` **0.4.1** (2026-07-06), which pins `coreai-core==**1.0.0b2**` *exactly*, requires **Python ≥ 3.11** and **torch ≥ 2.8.0** (validated to **2.13.0**; above that, a `UserWarning` and you are on your own). |
| [9](references/part-09-coreai-compression-numerics/README.md) | this part is almost entirely **host-side Python**. |
| [10](references/part-10-coreai-hardware-authoring-debugging/README.md) | everything here is **27.0 and only 27.0**. |

## Read these before you trust a signature

- **Part 7** — [Read this before you trust a signature in this part](references/part-07-coreai-swift-runtime/README.md#️-read-this-before-you-trust-a-signature-in-this-part)
- **Part 10** — [Read this before you trust a signature anywhere in this part](references/part-10-coreai-hardware-authoring-debugging/README.md#️-read-this-before-you-trust-a-signature-anywhere-in-this-part)

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 7 — Core AI: the Swift runtime** ([all 12 rows](references/part-07-coreai-swift-runtime/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I have a `.aimodel` and want it running today" | 7.1 §0–§9 | The whole object model; §14 is a runner you can paste |
| "What error type do I `catch`?" · "`contiguousElements` is `nil`" · "`shape.reduce` won't compile" | 7.1 §13, §7 | ✅ SDK-verified: untyped throws, `AssetError` only; preferred strides or interleave; `Span` is not a `Sequence` |
| "My first launch stalls for minutes" | 7.2 §1–§5 | Specialization. Gate on `model(for:options:)`, pre-specialize behind explanatory UI |
| "The stall came back after I was sure I'd paid it" | 7.2 §4, §6 | The key is `(asset, options)` — or an OS update, which purges everything regardless of policy |

**Part 8 — Core AI: converting a model from PyTorch** ([all 14 rows](references/part-08-coreai-pytorch-conversion/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I have a working `nn.Module` and want an `.aimodel`" | 8.1 §1–§7 | The five lines, what each owns, and the IO contract that becomes your Swift call site |
| "My assets stopped loading on a newer beta" | 8.1 §2.3 | The 0.4.0 gate, plus the `strip_debug_info` recovery that does *not* need a reconvert |
| "My transformer converted fine and is slower than I expected" | 8.1 §4.4 | You probably passed PyTorch's default decomposition table; SDPA decomposed into six supported ops and the fast path vanished |
| "The numbers are wrong and nothing threw" | 8.1 §6.4 → §11.4 | The `optimize()` miscompile, then the A/B gate that catches it and its whole family |

**Part 9 — Core AI: compression and numeric formats** ([all 15 rows](references/part-09-coreai-compression-numerics/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I just need something smaller, today" | 9.1 §3 | `presets.w4()` / `w8()`, and the eleven fields each one silently sets |
| "My compressed model is bigger than the arithmetic says" | 9.1 §7.5 · 9.3 §2.7 | The block-divisibility silent skip. The single most common defect in this part |
| "My model won't `torch.export`" | 9.1 §8.4 | EAGER mode — and the non-obvious externalization reason for choosing it |
| "I need to quantize activations, not just weights" | 9.1 §8–§9 | GRAPH mode, observers, calibration, and the six ops whose qscheme is overridden behind your back |

**Part 10 — Core AI: hardware authoring, debugging, and LLM deployment** ([all 12 rows](references/part-10-coreai-hardware-authoring-debugging/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I am about to re-author a model and don't know which compute unit to target" | 10.1 §1–§3 | The two rulesets side by side, plus Apple's own decision tables and memory budgets |
| "My ANE model runs correctly but the phone is hot" | 10.1 §4.16 | Residency. One fp32 literal in a norm is 56 accelerator transitions per forward pass |
| "Fine at token 1, degraded by token 64" | 10.1 §4.13 | You cached the pre-RoPE key. Apple marks this **CRITICAL**, and nowhere else |
| "I re-authored for the ANE and it still runs on the GPU" | 10.1 §8 · §4.1 | Entrypoint names, or `enable_per_channel_scale=True` and its rank-6 LUTs |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **7.1** `AIModel`, `InferenceFunction`, `NDArray`, and the memory model — The object-model primer every other guide assumes, built around the structural fact that makes app architecture fall out: **`AIModel` owns nothing and pins a cache …
- **7.2** Specialization, the model cache, and ahead-of-time compilation — The single largest source of first-launch stalls, wedged loads and mysterious disk growth.
- **7.3** States as KV cache, and pipelined execution — A decode loop written the naive way gets slower every step, and in Instruments it is unmistakable: **inference intervals that visibly widen along the timeline**.
- **7.4** Model bundles, the LLM engines, and grammar-constrained decoding — The layer above the runtime, where a raw `.aimodel` becomes something shippable and Apple's own Swift package turns "I have a converted Qwen3" into …
- **7.5** Non-LLM engines: bundles, function structure, warmup, specialization, and caching — The runtime owner for `CoreAISegmentation`, `CoreAIObjectDetection`, and `CoreAIDiffusion`.
- **8.1** `torch.export` to `.aimodel`, and the IO / state / dynamic-shape contract — The pipeline end to end as a series of contracts rather than a recipe: the decomposition table and exactly which twelve ops it preserves (Apple's README says three — a …
- **8.2** When an op will not convert: coverage, composite ops, custom lowerings, externalization — The debugging guide for conversion failures — and, more usefully, for **conversions that succeed and should not have**.
- **8.3** `TorchMetalKernel`: writing and embedding a custom Metal kernel — The seam, not the shader: how a kernel you already know how to write gets into an `.aimodel`.
- **9.1** `coreai-opt` quantization: configs, GRAPH vs EAGER, calibration and QAT — The foundation guide, and the one everything else assumes.
- **9.2** Palettization, pruning, joint compression, and mixed precision — The other three things `coreai-opt` does, plus the two ways of combining them.
- **9.3** int4 to MX: which layer supports which numeric format — A reference rather than a tutorial, answering one question in as many tables as it takes: for a given format — int4, FP8 E4M3, FP4 E2M1, MXFP4, a 6-bit palette, E8M0 …
- **10.1** Authoring for the Neural Engine and for the GPU: two opposite rulesets — Apple's at-a-glance comparison table reproduced in full and unpacked row by row: on the ANE, rank ≤ 5, fp16 with **no Python float literals anywhere**, the 64-byte …
- **10.2** The debug gauge, the Core AI Instrument, and the Core AI Debugger — Three tools at three levels — *is anything happening* (gauge, free), *where is the time going and on which compute unit* (Instruments, one run), *which operation …
- **10.3** From a Hugging Face checkpoint to a loadable LLM bundle — The capstone: one continuous path from `Qwen/Qwen3-0.6B` to `try await session.respond(to:)`, in ten stages, each with its gates and failure modes.

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-on-device-ai`, `apple-metal-tensorops`, `apple-ai-migration`, `apple-ai-shipping`.
