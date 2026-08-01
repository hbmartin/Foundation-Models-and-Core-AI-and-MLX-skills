---
name: apple-mlx
description: "MLX on Apple silicon in both languages: mx.array, unified memory, lazy evaluation, mx.compile, function transforms, custom Metal kernels, quantization, numerics and hardware gating, the mlx-lm CLI with generation and prompt caching, serving and distributed inference, fine-tuning and porting models; MLX Swift with mlx-swift-lm in an app, generation, tools and caching, and the Foundation Models bridge; plus converting between MLX and Core AI."
when_to_use: "Use for any import mlx, mlx_lm or MLX Swift work: an array that never evaluates, a recompilation storm from mx.compile, unified-memory growth, a quantization accuracy drop, a Hugging Face checkpoint that will not port, or moving a model between MLX and Core AI."
---

# MLX in Python and Swift, and bridges to Core AI

Part 12, Part 13, Part 14 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

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
| [12](references/part-12-mlx-python/README.md) | MLX **0.32.x** (the tree declares `MLX_VERSION 0.32.1` at commit `973e27f`; the docs site served the 0.32.0 build) and **mlx-lm 0.31.3**, plus `main` at `e5baded` (2026-07-26). |
| [13](references/part-13-mlx-swift/README.md) | `mlx-swift-lm` **3.x** — pin `.upToNextMajor(from: "3.31.3")`; latest release **3.31.4** (2026-06-30). |
| [14](references/part-14-bridges-between-stacks/README.md) | **macOS 27 / iOS 27** for anything that *executes*, **Python 3.11+** to convert, and a set of wheel pins that **do not agree with each other**. |

## Read these before you trust a signature

- **Part 12** — [Pin your versions. Every date in this part is suspect.](references/part-12-mlx-python/README.md#️-pin-your-versions-every-date-in-this-part-is-suspect)
- **Part 14** — [Read this before you trust anything in this part](references/part-14-bridges-between-stacks/README.md#️-read-this-before-you-trust-anything-in-this-part)

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 12 — MLX in Python** ([all 11 rows](references/part-12-mlx-python/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I know NumPy; what breaks first?" · "why is my program using 60 GB?" | 12.1 §1–§4 | Unified memory, laziness, the transforms — nothing computes until forced |
| "`mx.compile` made my code *slower*" · "my gradient is zero and nothing threw" | 12.1 §8.4, §5.3, §7.1 | A varying Python `int` is in the cache key; captured arrays are frozen constants |
| "Green on my M3, red on the M5" · "`allclose(rtol=1e-5)` started failing" | 12.2 §3 | TF32 by default; `MLX_ENABLE_TF32` is the only control |
| "Prefill is slow" · "OOM at a context length the arithmetic said fits" | 12.2 §5 | Silent SDPA fallback — check `head_dim` against the allow-list |
| "MLX has no op for this" | 12.2 §7–§9 | `mx.fast.metal_kernel`: a JIT'd string, no Xcode, no build step |
| "Which bits, group size and mode?" · "3-bit is unusable" | 12.3 §2–§3, §8, §12 | Mode inventory, sizing arithmetic, selection table; AWQ/GPTQ/DWQ/dynamic |

**Part 13 — MLX in Swift** ([all 15 rows](references/part-13-mlx-swift/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "The sample code I found doesn't compile" | 13.1 §1, §2.6 | It is 2.x. The migration table is there |
| "First build fails and I don't know which products to link" | 13.1 §2–§3 | Nine products, **three integration styles**; §3.5 decides for you |
| `ModelFactoryError.noModelFactoryAvailable` | 13.1 §4.2 · 13.3 §3.3 | You linked `MLXLMCommon` but not `MLXLLM`/`MLXVLM`; the registry uses `NSClassFromString` |
| "cannot find `MLXLanguageModel` in scope" | 13.3 §1 · 13.1 §9.1 | You are on the 26 SDK. The target compiled to an empty library |
| "It is killed on device with no crash report" | 13.1 §6.7–§6.8 | Jetsam. `Memory.snapshot()` reports MLX's allocator, not `phys_footprint` |
| "It crashes when the app backgrounds mid-generation" | 13.1 §5.6 | A Metal command-buffer error on a completion handler Swift cannot catch |

**Part 14 — Bridges between stacks** ([all 11 rows](references/part-14-bridges-between-stacks/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I have an `mlx-lm` causal LM and want a Core AI bundle" | 14.1 §3, then **§6** | One command; it reproduces Apple's `keyCache`/`valueCache` contract exactly. §6 is not optional |
| "I have an MLX vision or audio model — one graph, no state" | 14.1 §5 | The generic converter. `ConversionConfig` field by field, and the three fields that need a warning label |
| "It converted. The text is fine at step 1 and nonsense by step 30" | 14.1 §3.5, §7 | The classic KV-offset bug, and the eight lossy lowerings that produce plausible garbage |
| "I am writing my own bridge / my bundle won't load" | 14.1 §4 | Schema 0.2 field by field, what Apple's reader enforces, and a targeting checklist |
| `unsupported metadata_version '0.1'` | 14.1 §4.2 | Absent key defaults to `"0.1"`; or you pointed at the `.aimodel`, not the bundle dir |
| `Failed to convert to versioned IR` | 14.1 §2.3 | The wheel-pin collision, plus a ninety-second probe that settles it before a 4 GB conversion |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **12.1** MLX fundamentals: unified memory, lazy evaluation, transforms, and `compile` — The conceptual primer the other five assume, built on five ideas: unified memory (you never move arrays, you choose per-op *which device runs it*), lazy evaluation, the …
- **12.2** Numerics, hardware gating, and writing custom Metal kernels from Python — Where MLX stops being a portable array library and becomes a program on one specific piece of Apple silicon.
- **12.3** MLX quantization: modes, group sizes, gates, and the corruption bugs — Quantization in MLX is four things wearing one name: a numeric format (affine at 2/3/4/5/6/8 bits, or `mxfp4`/`mxfp8`/`nvfp4`), a memory layout (**three arrays** — …
- **12.4** mlx-lm: the CLI surface, the generation API, and KV caching — The layer where MLX becomes an LLM runtime: **18 command-line entry points** enumerated from `setup.py`; the Python generation API (`load`, `generate`, …
- **12.5** `mlx_lm.server`, local agents, and distributed inference over Thunderbolt — Two halves.
- **12.6** LoRA and DoRA fine-tuning, and adding a new architecture — Opens with the frame (§0): **custom Foundation Models adapters are discontinued in OS 27**, per two independent Apple-staff forum statements, with the Adapter Training …
- **13.1** `mlx-swift-lm` in an app: setup, concurrency, memory, and media input — The "make it survive contact with an iPhone" guide, in the order things hurt: the 3.x break and the nine products; the **three integration styles** for tokenizers and …
- **13.2** Generation, tool calling, and KV cache management in Swift — Deliberately structured to mirror Part 12 guide 04 so you can move between the languages, …
- **13.3** `MLXFoundationModels` and `MLXGuidedGeneration`: backing `LanguageModelSession` with an MLX model — Opens by answering the question a developer asked on forum thread **836264** after seeing `import MLXFoundationModels` on a WWDC26 session-339 slide: it is a library …
- **14.1** Bridges into Core AI: `mlx2coreai`, `swift-lm`, and the community zoo — Three bridges, one destination.

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-on-device-ai`, `apple-core-ai`, `apple-metal-tensorops`, `apple-foundation-models`.
