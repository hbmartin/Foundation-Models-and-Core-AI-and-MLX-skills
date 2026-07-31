# john-rocky: `coreai-models` fork + `coreai-model-zoo`

Research notes for the WWDC26 / iOS-macOS 27 Apple AI-ML stack sweep.
Compiled 2026-07-27 from local clones only. **Every claim below is grounded in a file read
this session and cited as `path:LINE`.** Nothing here is from model memory.

> ⚠️ **SOURCING WARNING — READ BEFORE QUOTING ANY NUMBER.**
> Both repos are **community** work by GitHub user `john-rocky` (Daisuke Majima /
> "rockyshikoku"), partly agent-generated (the repo ships `AGENTS.md` + Claude/Codex
> skill plugins and many docs are written in an agent-handoff voice). The benchmark
> tables, bug reports and incident write-ups are **unique primary sources** and are often
> the only public measurements of these paths — but they are **NOT Apple-official**.
> Attribute them as *community-measured*. Where a number complicates or contradicts
> Apple's own documentation, this file flags it inline with **[CONTRADICTS APPLE]**.
> Hardware/OS provenance is recorded wherever the source states it; where the source
> omits it, this file says so rather than guessing.

---

## Table of contents

1. Source inventory
2. Repo A — `john-rocky/coreai-models` (fork of `apple/coreai-models`)
   - 2.1 Fork topology & what it adds/drops
   - 2.2 Commit `9e5b605` — hybrid-bundle support in the pipelined engine
   - 2.3 Commit `627fec7` — stop-on-consumer-break (D1 latency fix)
   - 2.4 Commit `0fdf710` — **`trimKVCache` cross-turn prefix reuse** (deep dive)
3. Repo B — `john-rocky/coreai-model-zoo`: shape of the project
   - 3.1 What it is (README / catalog / CoreAIKit / FM tie-in)
   - 3.2 `AGENTS.md` + `CLAUDE.md` — the agent porting contract
   - 3.3 `BENCHMARKS.md` — the community bench protocol
   - 3.4 `CATALOG_PLAN.md` — reproducibility engineering
   - 3.5 `CONTRIBUTING.md` — acceptance bars
   - 3.6 Directory structure (`conversion/`, `models/`, `zoo/`, `official/`, `apps/`, `swift/`, `scripts/`, `_smoke/`)
4. The porting playbook
   - 4.1 `PORTING.md` step by step
   - 4.2 Skill `port-a-model-to-the-zoo`
   - 4.3 Skill `reproduce-a-zoo-model`
   - 4.4 Comparison with Apple's own `model-authoring` skill
5. Platform mechanics (knowledge/ Tier 1)
   - 5.1 `coreai-overview.md`
   - 5.2 `aot-and-specialization.md`
   - 5.3 `compute-units-and-authoring.md`
   - 5.4 `conversion-guide.md`
   - 5.5 `compression.md` + `compression-reference.md`
   - 5.6 `custom-metal-kernels.md`
   - 5.7 `accel-levers-survey-and-plan.md`
6. **Incidents** (unique primary sources)
   - 6.1 MPSGraph KV-write bug (`coreai-beta-mpsgraph-kvwrite-bug.md`)
   - 6.2 coreai-torch 0.4.1 IR incident (`coreai-torch-041-ir-incident.md`)
7. Benchmarks (knowledge/ Tier 2)
   - 7.1 `coreai-vs-mlx-speed.md`
   - 7.2 `apple-models-bench.md`
   - 7.3 `cross-runtime-quality-benchmarking.md`
   - 7.4 `dense-int4km-flagship-session-findings.md`
   - 7.5 Consolidated benchmark table
8. Foundation Models integration, community side (Tier 3)
   - 8.1 `fm-provider.md`
   - 8.2 `dynamic-profiles-local-models.md`
   - 8.3 `evaluations-framework.md`
9. Per-model porting write-ups (Tier 4)
   - 9.1 The Gemma 4 cluster (five files)
   - 9.2 Ternary / 1.58-bit ports (BitCPM, BitVLA)
   - 9.3 Generative-audio and vision ports (Chatterbox, eSAM3, DA3, AdcSR)
   - 9.4 Non-autoregressive / generative ports (FLUX.2, LLaDA dLLM)
   - 9.5 `flagship-full-tuning-stack.md`
   - 9.6 `agentic-security-checklist.md`
10. Prototype code (Tier 5)
    - 10.1 `_tensorops_proto/`
    - 10.2 `_specdecode_proto/tree_attn_verify.py`
11. GitHub issues & PRs
12. Guide topics this material uniquely supports
13. Open questions / UNVERIFIED

---

## 1. Source inventory

Everything below was read this session. Paths are absolute.

### Repo A — `/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-models`

Fork of `apple/coreai-models`, remote `https://github.com/john-rocky/coreai-models`.
Full history is only **4 commits** (the fork was re-initialised, not rebased on Apple's history):

```
0fdf710  2026-07-03  InferenceEngine: trimKVCache primitive for cross-turn prefix reuse
627fec7  2026-06-13  Stop the pipelined engine when the consumer stops the stream
9e5b605  2026-06-13  Add hybrid-bundle support to the pipelined inference engine
b1cb71b  (initial)   Initial commit
```

Files read:
- `swift/Sources/CoreAILanguageModels/InferenceEngines/InferenceEngine.swift` (protocol + defaults)
- `swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAISequentialEngine.swift`
- `swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAIPipelinedEngine.swift`
- `README.md`, `NOTICE.txt`
- Compared against `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models` by
  `git ls-files` set-diff (deliberately **not** a full content diff).

### Repo B — `/Volumes/ExtStor/FM and MLX and CoreAI/repos/john-rocky__coreai-model-zoo`

Top-level docs: `README.md` (37 KB), `PORTING.md` (351 lines), `CATALOG_PLAN.md` (14 KB),
`BENCHMARKS.md`, `AGENTS.md` (7.2 KB), `CONTRIBUTING.md`, `CLAUDE.md` (a 1-line pointer at
`AGENTS.md`), `LICENSE`.

Agent skills: `skills/skills/port-a-model-to-the-zoo/SKILL.md`,
`skills/skills/reproduce-a-zoo-model/SKILL.md`, plus plugin manifests
`skills/.claude-plugin/plugin.json`, `skills/.codex-plugin/plugin.json`,
`skills/gemini-extension.json`, and `.claude-plugin/`.

`knowledge/` — **77 markdown files, 9 872 lines total** plus two prototype code dirs
(`_tensorops_proto/`, `_specdecode_proto/`) and `knowledge/scripts/`. This is the densest
practical-gotcha archive in the corpus.

Directory scale (see §3.5 for detail): `conversion/` ~105 entries, `models/` ~62 model cards,
`zoo/` ~52, `apps/` ~23, `_smoke/` ~21, `swift/`, `scripts/`, `official/`.


---

## 2. Repo A — `john-rocky/coreai-models` (fork of `apple/coreai-models`)

### 2.1 Fork topology & what it adds/drops

The fork's own README states its scope, verbatim
(`repos/john-rocky__coreai-models/README.md:9-14`):

> **Why this fork exists.** The upstream Swift pipelined inference engine validates exactly
> two model states (the KV cache pair) and only `input_ids`/`position_ids` inputs, so it
> cannot load *hybrid-attention* or *state-space* language bundles — e.g. Qwen3.5/3.6
> (GatedDeltaNet), LFM2.5, and Granite 4 (Mamba2) fail at load with `Expected 2 states, got 4`.

Self-declared scope (`README.md:35-43`): only
`swift/.../InferenceEngines/{CoreAIPipelinedEngine,EngineFactory}.swift` and
`python/.../primitives/macos/cache.py` differ from upstream; tagged `v0.1.0-zoo` (hybrid
bundles) and `v0.1.1-zoo` (consumer-break stop fix). It is consumed by
`github.com/john-rocky/coreai-kit` and the zoo demo apps via SwiftPM.

**Set-diff of tracked files** (`git ls-files`, apple 388 files vs fork 364):

*The fork LACKS (i.e. the fork's snapshot predates these upstream additions):*

| Upstream-only path | Capability the fork therefore misses |
|---|---|
| `.github/ISSUE_TEMPLATE/*.yml`, `.github/workflows/ci.yml` | Apple's issue templates + CI |
| `python/src/coreai_models/models/ios/sam3/*` (10 files: `detr.py`, `fpn.py`, `image_encoder.py`, `mask_decoder.py`, `sam3_reauthored.py`, `text_encoder.py`, `primitives/rope.py`, `primitives/window.py`) | Apple's SAM3 iOS re-authoring |
| `python/src/coreai_models/models/macos/qwen3_vl.py` | Apple's Qwen3-VL macOS recipe |
| `python/src/coreai_models/primitives/ios/{bidirectional_sdpa,gelu,layer_norm}.py` | newer iOS primitives |
| `python/src/coreai_models/primitives/macos/cache_scatter.py` | scatter-based cache primitive |
| `python/src/coreai_models/{segmentation,vlm}/` (`export.py`, `pipeline.py`) | segmentation + VLM export pipelines |
| `swift/.../InferenceEngines/CoreAISequentialVLMEngine.swift`, `EmbeddedInput.swift`, `GenerationToken.swift`, `InferenceOutputSequence.swift`, `TokenHistory.swift` | Apple's VLM engine and newer token-stream types |
| `swift/.../LanguageModel/ModelResources.swift`, `CoreAIShared/Runtime/{FileSize,ResourceManaging}.swift` | resource-management refactor |
| `swift/Sources/CoreAISpeech/{MelSpectrogram,SpeechBundle,SpeechDecoder,SpeechModel}.swift`, `Tools/speech-runner/` | the whole **CoreAISpeech** module + speech CLI |
| `swift/.../ToolCallParser.swift`, `VLM/CoreAIVisionLanguageModel.swift` | tool-call parsing, VLM facade |
| `swift/Sources/lib/CXGrammar/…` (source form: `xgrammar_c_bridge.cpp` + headers) | upstream builds XGrammar **from source** |
| tests: `VLMProtocolTests`, `CancelAPITests`, `GenerationStopReasonTests`, `ModelResourcesTests`, `FileSizeTests`, `test_infra.py` | |

*The fork ADDS:*

| Fork-only path | Note |
|---|---|
| `NOTICE.txt` | BSD-3 attribution / trademark disclaimer for the fork |
| `swift/Sources/CoreAIDiffusionPipeline/Components/ResourceManaging.swift` | local copy (upstream moved it to `CoreAIShared`) |
| `swift/Sources/CoreAILanguageModels/lib/CXGrammar.xcframework/` — **prebuilt** `libxgrammar_ios.a` + `libxgrammar_macos.a` for `ios-arm64_arm64e` and `macos-arm64_arm64e`, with `xgrammar/{compiler,config,exception,grammar,matcher,object,tokenizer_info,xgrammar}.h` + `dlpack/dlpack.h` | the fork **vendors a prebuilt XGrammar xcframework** instead of compiling the C++ bridge — a practical SwiftPM-consumability change (no C++ toolchain needed downstream) |

> **Read this carefully before drawing conclusions:** the fork is *not* strictly
> "upstream + 3 patches". It is a **snapshot** of `apple/coreai-models` at some point before
> Apple shipped SAM3 / VLM / Speech, plus three commits. So "missing" files are almost
> certainly *upstream-newer*, not deliberately removed. Treat the fork as evidence of what
> upstream looked like circa mid-2026, not as a critique of it. **UNVERIFIED**: exactly which
> upstream commit `b1cb71b` corresponds to — the fork has no upstream history to bisect against.

### 2.2 Commit `9e5b605` — hybrid-bundle support in the pipelined engine

*"Community fork patch (-zoo). Lets the Swift pipelined engine load hybrid-attention /
state-space language bundles (Qwen3.5/3.6, LFM2.5, Granite 4) that the upstream engine
rejects with 'Expected 2 states'."* — 4 files, +609/−32; the bulk (+538) in
`CoreAIPipelinedEngine.swift`.

The upstream guard becomes a `>= 2` check plus a bounded extra-state pool
(`CoreAIPipelinedEngine.swift:502-511`):

```swift
guard descriptor.stateNames.count >= 2 else {
    throw InferenceRuntimeError.invalidOutputType(
        "Expected at least 2 states (KV cache), got \(descriptor.stateNames.count): \(descriptor.stateNames)")
}
guard descriptor.stateNames.count - 2 <= Self.maxExtraStates else { … }
```

Extra states must be **fully static-shaped** — this is the load-bearing constraint
(`CoreAIPipelinedEngine.swift:527-531`):

```swift
guard !desc.shape.contains(where: { $0 < 0 }) else {
    throw InferenceRuntimeError.invalidOutputType(
        "Extra state '\(name)' has dynamic dims \(desc.shape) — only the first two "
            + "states (KV cache) may be dynamic in the pipelined engine")
}
```

Each extra state gets one **owned, zero-filled, `.storageModeShared` Metal buffer**
allocated at load and memset to 0, persisting across steps and re-zeroed on `reset()`
(`CoreAIPipelinedEngine.swift:533-547`). Binding is a hand-unrolled
`switch extraStates.count` at both encode sites (`:1009-1030` prefill, `:1349-1370` decode)
— i.e. 0/1/2 extra states, no loop, presumably to keep the hot path allocation-free.

`EngineFactory.swift` adds two additive, defaulted `EngineOptions` fields
(`EngineFactory.swift:293-327`):
- `public let perTokenInputProvider: PerTokenInputProvider?` (typealias at `:235`) — a
  `@Sendable` closure that fills a model input **gathered by the step's token id**. The
  motivating case is **Gemma per-layer-embedding (PLE) rows**.
- `public let staticInputBuffers: [String: StaticInputBuffer]` (struct at `:253`) — binds a
  constant host buffer unchanged on every encode, e.g. an **mmap'd embedding table**. The
  doc comment at `:246` notes that unlike `PerTokenInputProvider` it imposes **no decode-loop
  wait**.

Plus a static-shape logits-buffer sizing fix for decode-only `S=1` graphs, and a one-line SSM
state-descriptor shape fix in `python/src/coreai_models/primitives/macos/cache.py`.

### 2.3 Commit `627fec7` — stop the pipelined engine on consumer break (the "D1 fix")

Symptom (from the commit message): a consumer that `break`s the returned token stream at EOS
— *"every executor"* — leaves `runCompletion` generating to `maxTokens` **in the background**.
Those post-EOS tokens are **consumed into the KV cache**, so the next turn's
`reset()`/`drain()` blocks on the leftover generation. Two consequences: a **multi-turn
latency tax**, and on a slow model a risk of tripping `drain()`'s `fatalError`.

Fix: `generate()` now terminates the inner token stream on consumer break — both eagerly via
the returned stream's `onTermination` and from the forwarding loop's `yield` result — which
trips `runCompletion`'s existing `onTermination` cancel flag, stopping within pipeline depth.
Sampling, KV and the uninterrupted path are unchanged (**byte-identical output** claimed).

**Community-measured, via Apple's own `CoreAILanguageModel` adapter** (qwen3.5-0.8B, two-turn
chat): second-turn latency **2.74 s → 0.40 s**, same output. Hardware/OS not stated in the
commit or README — **UNVERIFIED** which device.

> This is a genuinely interesting finding for a guide: it is a bug in the *interaction between
> the AsyncSequence contract and a pipelined GPU generator*, and it only shows up on turn ≥ 2.
> It is community-attributed to upstream's engine, so treat "upstream has this bug" as a
> community claim, not an Apple statement.

### 2.4 Commit `0fdf710` — `trimKVCache`: cross-turn prefix reuse (DEEP DIVE)

**Diff size: 3 files, +69 / −0.** Tiny patch, very large effect. This is the single most
transferable idea in the fork.

#### 2.4.1 The problem it solves

A chat loop on top of these engines was doing, every turn:
`engine.reset()` → `applyChatTemplate(entire history)` → **full re-prefill**. So turn *N*
re-processes all of turns 1..*N*−1 from scratch — system prompt, retrieved RAG documents,
the whole history — before emitting a single new token. From
`knowledge/prefix-cache-kv-reuse.md:12-18`:

> `CoreAIChatMac/Sources/ChatEngine.swift` was doing exactly the worst thing: `engine.reset()`
> + `applyChatTemplate(full history)` + full re-prefill on EVERY turn … For a 4k-token RAG
> context that is seconds of dead time before the first new token, every turn.

#### 2.4.2 The key insight — *nothing has to be cleared*

The engines **already** (a) preserve KV across `generate()` calls, and (b) prefill only the
un-processed suffix. The only missing primitive was a **rewind**. And a rewind is *free*
because attention is causal. `knowledge/prefix-cache-kv-reuse.md:22-25` credits
upstream `reset()`'s own comment for the insight:

> `reset()`'s own comment gave the key: *"the KV pair needs no clearing — attention only reads
> positions below the new offset."* So a partial trim = just set `processedTokenCount =
> length`; positions ≥ length are overwritten before they're ever read.

That is the whole trick: **trimming the KV cache is a single integer assignment.** No buffer
zeroing, no memmove, no reallocation. The KV tensor is left byte-for-byte untouched; only the
engine's notion of "how many tokens are committed" moves backwards.

#### 2.4.3 What is trimmed, precisely

*Nothing is trimmed in memory.* What is trimmed is the **cache offset / write cursor**:

- `CoreAISequentialEngine.processedTokenCount` (declared
  `repos/john-rocky__coreai-models/swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAISequentialEngine.swift:72`).
- `EngineImpl.processedTokenCount` **and** `step` in the pipelined engine
  (`CoreAIPipelinedEngine.swift:446`, and the trim at `:1406-1415`), plus
  `lastSampledToken = nil` so the pipelined sampler doesn't carry a stale token across the
  rewind.

Retained KV rows `[0 ..< retained]` stay valid because they were written at exactly those
positions with exactly those tokens. Rows `≥ retained` are stale garbage that will be
**overwritten before any causal read can see them** — a query at position *p* only attends to
keys at positions `≤ p`, and every position `≥ retained` gets rewritten by the next prefill
before a query reaches it.

#### 2.4.4 The API — three additions to `InferenceEngine`

`InferenceEngine.swift:123`:

```swift
func trimKVCache(to length: Int) async -> Int
```

Contract, from the doc comment (`InferenceEngine.swift:111-122`):
- Rewinds toward `length`, keeping the leading cached tokens valid and dropping everything
  after, *"so the next `generate(with:)` prefills only the un-cached suffix instead of the
  whole prompt."*
- Returns the **ACTUAL retained prefix length** (0…`length`), *"which may be less than
  requested because the last generated token's KV can lag one step behind — the caller must
  prefill from the returned offset, not from `length`."* This is a subtle and important
  correctness detail: **never trust your own requested length.**
- Returns a **negative value** if the engine can't safely rewind, in which case the caller
  must `reset()` and re-feed the full prompt.

`InferenceEngine.swift:138`:

```swift
var prefixReuseFeedsFullSequence: Bool { get }
```

The **feed contract**, which differs per engine and is the easiest thing to get wrong:
- `true` (default) — `generate(with:)` takes the **FULL running sequence** and the engine
  slices `input[retained...]` internally. This is `CoreAISequentialEngine`.
- `false` — the caller passes **ONLY the un-cached suffix**, because the pipelined engine
  prefills exactly the tokens it is handed, at the current offset
  (`CoreAIPipelinedEngine.swift:179`, comment at `:176-178`).

Protocol-extension defaults (`InferenceEngine.swift:185`, `:188`):

```swift
public func trimKVCache(to length: Int) async -> Int { -1 }
public var prefixReuseFeedsFullSequence: Bool { true }
```

i.e. **opt-in, fail-safe**: any engine that doesn't implement it reports "unsupported" and the
caller degrades to the old full re-prefill path. No existing engine changes behaviour.

#### 2.4.5 The two implementations

**Sequential** (`CoreAISequentialEngine.swift:437-443`) — the verified one:

```swift
public func trimKVCache(to length: Int) async -> Int {
    drain()
    guard length >= 0 else { return -1 }
    let retained = min(length, processedTokenCount)
    processedTokenCount = retained
    return retained
}
```

`drain()` first (`:412`) so no in-flight generation is still writing KV. Then clamp and
assign. Its doc comment (`:432-436`) spells out why it is always safe: *"KV-only (no recurrent
state) — always safe; no clearing needed since causal attention never reads positions ≥ the
retained offset before they're rewritten."*

**Pipelined** (`CoreAIPipelinedEngine.swift:183-189` wrapper → `:1406-1415` impl):

```swift
func trimKVCache(to length: Int) async -> Int {
    drain()
    guard tryAcquireEngine() else { return -1 }
    defer { releaseEngine() }
    return engine.trimKVCache(to: length)
}
```
```swift
mutating func trimKVCache(to length: Int) -> Int {
    guard extraStates.isEmpty else { return -1 }
    let retained = max(0, min(length, processedTokenCount))
    processedTokenCount = retained
    step = retained
    lastSampledToken = nil
    return retained
}
```

#### 2.4.6 Why hybrids are refused — the important negative result

The `guard extraStates.isEmpty else { return -1 }` is the crux. The doc comment
(`CoreAIPipelinedEngine.swift:1401-1405`) is precise:

> Rejected when the graph carries recurrent `extraStates` (GDN/SSM): those hold a running scan
> that can't be reconstructed at position `length` from the retained KV, so a partial rewind
> would corrupt them. Pure attention KV needs no clearing (causal reads never see positions
> ≥ `length`).

**This is the deep asymmetry between attention and linear/recurrent attention on-device.**
An attention KV cache is *positionally addressed* — row *i* is self-contained, so you can
truncate at any *i*. An SSM/GatedDeltaNet/Mamba2 state is a **running scan**: a single fixed
-size tensor that is a lossy fold of *all* tokens seen so far. There is no row to drop. To get
the state as of token *k* you must re-run the scan from 0. Hence: **hybrid models cannot do
cheap prefix reuse.** Per `knowledge/prefix-cache-kv-reuse.md:101-102`, Qwen3.5/3.6 linear-attn
hybrids return `-1` and fall back to full re-prefill; *"Pure-attention models get the win."*

> Guide-worthy framing: linear attention buys you O(1) decode memory and pays for it by
> **forfeiting prefix caching**. On a device where multi-turn TTFT is the user-felt metric,
> that trade can invert the usual "SSMs are better on-device" story. Note this is a
> **community-derived** conclusion from one implementation, not an Apple claim.

#### 2.4.7 The caller-side algorithm (LCP reuse)

From `knowledge/prefix-cache-kv-reuse.md:40-46`, `ChatEngine.send()` per turn:

1. `full = applyChatTemplate(history)` (unchanged).
2. `want = min(commonPrefixLength(full, kvTokens), full.count - 1)` — where `kvTokens` is the
   **exact token sequence the engine's KV currently holds** (prompt **+** streamed generation),
   tracked by the caller across turns. The `full.count - 1` clamp guarantees at least one
   token is fed, so the graph always has something to run.
3. `reused = await engine.trimKVCache(to: want)`; on `< 0` → `reset()` and `reused = 0`.
4. `feed = engine.prefixReuseFeedsFullSequence ? full : full[reused...]` →
   `engine.generate(with: feed)`.
5. **Break at the stop sequence (no drain)** so the KV ends at prompt + real answer — which is
   exactly what commit `627fec7` (§2.3) made safe.

Note step 5's dependency on step §2.3: the two commits compose. Prefix reuse is only correct if
the KV ends at a *known* token boundary, which requires the engine to actually stop at EOS
rather than run on to `maxTokens`.

#### 2.4.8 Losslessness

Claimed **lossless by construction** (`prefix-cache-kv-reuse.md:48-49`): `KV[0..reused]` holds
identical tokens at identical positions whether reused or recomputed. And empirically proven:
with `CHATMAC_GREEDY=1` (temp 0), the turn-2 output is **byte-identical** ON vs OFF
(`prefix-cache-kv-reuse.md:60-62`). A/B toggles shipped: `CHATMAC_NO_PREFIX_CACHE=1` forces the
old reset path, `CHATMAC_STATS_LOG=<file>` dumps `PFXCACHE prompt=… reused=… ttft=…` per turn.

#### 2.4.9 What it buys — the numbers

**Community-measured. qwen3-0.6b, sequential engine, CoreAIChatMac, on a Mac. Exact Mac model
and macOS build NOT stated in the source — UNVERIFIED.** (`prefix-cache-kv-reuse.md:52-58`)

| Turn | Prompt tokens | Reused | TTFT prefix-cache ON | TTFT OFF | Speedup |
|---|---|---|---|---|---|
| 1 (cold) | 81–3820 | 0 | = OFF | initial prefill, unavoidable | 1× |
| 2 | 357 | 336 | **0.126 s** | **1.915 s** | **15.2×** |
| 2 | 4103 | **4075 (99.3 %)** | **0.230 s** | **23.282 s** | **101×** |

Multi-turn robustness, 3 turns, greedy (`:66-70`):

| Turn | Tokens | Reused | TTFT |
|---|---|---|---|
| 1 (cold) | 826 | 0 | 4.40 s |
| 2 | — | 826 | **0.122 s** |
| 3 | — | 849 | **0.151 s** |

Turn 3 reuses turn 2's entire prompt **and turn 2's answer** — prior assistant turns are reused
too, for models whose `reply.content` equals the raw generation (qwen/llama pass through
`HarmonyParser` unchanged). No degradation across turns.

The scaling shape is the headline: **re-prefill cost grows with context while reuse cost stays
roughly flat**, so 15× at 357 tokens → 101× at 4 k → more for real RAG/agent contexts.
Also note the honest counterweight in the same doc (`:63-64`): turn 1 still pays the full
prefill — 3820 tokens ≈ **22 s** on this small model's `S=1` sequential prefill — which the
author flags as a separate chunked-prefill lever, not something prefix caching addresses.

#### 2.4.10 Reuse depth in practice

`prefix-cache-kv-reuse.md:72-76`: the **system prompt + prior user turns always match** because
the chat template is append-only there, so the dominant cost in long RAG/agent contexts is
always reused. Prior **assistant** turns reuse only when the model's raw generation matches the
template's re-render — thinking-stripping / retokenization can diverge. LCP degrades gracefully:
reuse the common part, re-prefill the tail.

#### 2.4.11 Known limits, per the author (do not re-derive)

From `prefix-cache-kv-reuse.md:78-105` and `:94-105`:

- **Pipelined path is UNVERIFIED.** Implemented and symmetric, but could not be exercised:
  CoreAIChatMac forces `variant: "coreai-sequential"` because the pipelined variant
  **SIGTRAPs in `GrowingLogitsBuffer`** for these bundles, and the iOS pipelined app is
  single-turn. Verification needs either a `GrowingLogitsBuffer` fix or a multi-turn pipelined
  device harness.
- **iOS `CoreAIChat` is single-turn** (`PipelinedBackend.generate(_ prompt:)` templates a lone
  user message, no history accumulation) → prefix caching has nothing to reuse there. Making it
  multi-turn is a product feature, not a caching add.
- **Assistant re-anchoring** (deeper reuse when content is stripped, e.g. gpt-oss harmony) was
  assessed and **deliberately not implemented**: it needs a *prefill-only engine call* (align KV
  to the canonical rendering without sampling) since `generate()` always decodes. Judged narrow
  benefit vs a real new engine API.
- Short single-turn chats see **nothing**. This is a long-context/agent lever only.
- The doc says *"All changes uncommitted"* — it was written 2026-07-03, the same day as commit
  `0fdf710`, which committed the engine half. The **`ChatEngine` caller half is not in either
  repo I read** — **UNVERIFIED**, it presumably lives in the CoreAIChatMac app repo.

---

## 3. Repo B — `john-rocky/coreai-model-zoo`: shape of the project

### 3.1 What it is

Self-description (`README.md:8-16`): *"Converted models + conversion recipes for Apple **Core
AI** (`.aimodel`, iOS 27 / macOS 27): every model here is downloadable, device-verified, and
carries the recipe that produced it in `models/<model>/recipe.toml`."* Explicit successor to the
author's older `CoreML-Models` repo. Weights are published under `huggingface.co/mlboydaisuke`
(and contributors' own namespaces), consumed by a sibling Swift package
**CoreAIKit** (`github.com/john-rocky/coreai-kit`).

The pitch line — *"The `from_pretrained` of Core AI"* (`README.md:18`):

```swift
let chat = try await ChatSession(catalog: "qwen3.5-2b")   // downloads once, then cached
let reply = try await chat.respond(to: "What can you do, offline?")
```

**Direct FoundationModels tie-in** (`README.md:32-39`) — important for the FM guides:

```swift
LanguageModelSession(model: try await KitLanguageModel(model: .qwen3_0_6B))
```

*"gives you the system session — `Tool` calling, `@Generable` guided generation, transcripts —
backed by a zoo model."* And: *"every bundle loads with Apple's own
`CoreAILanguageModel(resourcesAt:)` as-is; this repo's `ZooFMProvider` adds streaming tool
calling on top (incl. LFM's native dialect)."* See §8.1.

### 3.2 `AGENTS.md` — the porting contract for coding agents

`CLAUDE.md` is one line: *"See AGENTS.md — the porting contract, the gates, and what is not an
agent's call."*

`AGENTS.md` is unusually well-designed as an agent contract; the reusable ideas:

- **Thesis** (`AGENTS.md:13-17`): *"Porting is not format conversion. There is no
  `convert(model)` that works. … An agent that reaches for a one-shot converter produces a
  bundle that loads, runs, and emits plausible garbage — the most expensive failure mode here,
  because it looks like success."*
- **The single rule** (`:19-21`): *"the oracle comes first, and every stage gates against it …
  A port without gates is a guess with extra steps."*
- **Two hard gates before writing code** (`:45-51`): **GAP** (Apple's stock stack does not
  already ship this capability — if it does, stop) and **EDGE** (the port must be at least as
  good as the realistic alternative, *especially MLX*). *"this repo has shipped and then pulled
  two of those [worse-MLX ports]."* And: *"'The user asked for it' is not an answer to EDGE."*
- **Traps that specifically catch agents** (`:65-79`) — verbatim list, all of which are
  guide-worthy:
  1. Trusting notes over the oracle (a handoff note said "no input normalization"; the oracle
     showed the feature extractor always normalizes).
  2. Re-authoring from the HF `modeling_*.py` instead of the weights — *"The modeling file has
     branches that never run for this checkpoint, and hides ones that do."*
  3. Believing int4 because the loss looks fine — *"int4 is a cliff, not a slope."*
  4. Timing with `cpu_only()` — that is the **parity** option, not a performance option.
  5. Benchmarking through a chat UI — *"Headless self-test entrypoint, or it did not happen."*
  6. JIT-ing a ≥ 1 GB graph on device — AOT-compile it (`--architecture h18p` for iPhone 17 Pro).
  7. Running an iOS bundle on a Mac — *"Wedges the GPU stack; costs a reboot."*
  8. **Naked `exp()` in a hand-written kernel. *"Three separate sessions lost to this; subtract
     the max first."*** (i.e. numerically-unstable softmax in custom Metal.)
  9. Comparing quality across runtimes without matching the generation budget — *"A 12-point
     'quality gap' in this repo's history turned out to be a 600-vs-2048 token cap difference."*
     (See §7.3.)
- **"Not your call"** (`:104-111`) — ask the human every time: publishing weights to HF; posting
  publicly (X/HN/Reddit); opening issues/PRs against `apple/*` repos; marking a port
  `status = "verified"` on numbers you did not produce. This is a notably mature agent-safety
  boundary set and worth calling out in any "agents in your dev loop" guide.
- **"The step you cannot do, and don't have to"** (`:96-102`): everything runs on any Apple
  silicon Mac; what needs an iOS 27 device (AOT load, thermals, sustained tok/s under DVFS, the
  memory ceiling) is handed back via a *device gate request* issue template, and a maintainer
  runs it and posts numbers into the thread under the contributor's name. *"Do not report iPhone
  numbers you did not measure, and do not let an unmeasured device claim reach a card."*

### 3.3 `BENCHMARKS.md` — the community bench protocol

This file is a **process artifact more than a data artifact** right now, and worth citing as a
methodology template (`BENCHMARKS.md:1-30`):

- Data comes from the **Bench tab of CoreAIChat** (TestFlight) on contributors' own devices,
  submitted as `bench-result` GitHub issues — *"the public audit log. The app measures and
  builds the result blob; no number in this table was typed by a human."*
- Explicitly labelled *"NOT a controlled-environment benchmark — background load and heat show
  up here as real-world variance."*
- **Protocol `pb-random-v1`**: fixed 128-token random prompt (seed 0) → **256 greedy decode
  tokens**, S=1 prefill (`COREAI_CHUNK_THRESHOLD=1`), **1 cold + 3 warm runs on a freshly
  created engine**. Cell = median across submissions of each submission's median **warm decode
  tok/s**. `n` = accepted submissions; `n < 3` marked provisional.
- **Environment filter**: blobs with **Low Power Mode on** or a **serious/critical thermal
  state** before the run are excluded from medians (and the exclusion count is published).
- Aggregated by `scripts/aggregate_bench.py`; header says *"do not edit by hand"*.

Actual content as of `Last run: 2026-07-03 06:15 UTC`:

| Device | qwen3.5-0.8b | lfm2.5-1.2b | granite-4.0-h-1b |
|---|---|---|---|
| iPhone 17 Pro (A19 Pro, `iPhone18,1`) | 68.4\* (n=1) | — | — |

Accepted submissions: **1**; excluded: 0; rejected: 0. So the crowd-sourced table is essentially
empty — **the real numbers all live in the README and `knowledge/`**, measured by the author.
Do not cite `BENCHMARKS.md` as a multi-device dataset; cite it as a protocol.

> Cross-check worth noting: `BENCHMARKS.md` gives qwen3.5-0.8b at **68.4** tok/s on iPhone 17 Pro
> under `pb-random-v1`, while the README headline table gives **71.9**. ~5 % apart, consistent
> with different prompts/thermal state — a useful illustration of measurement variance to cite.

### 3.4 `CATALOG_PLAN.md` — reproducibility engineering (the most quotable process doc)

Dated 2026-07-25. Phases `C0`–`C4`; `C0/C1/C2/C4.2/C4.3` done, `C3` (oracles) and `C4.1`
(device tier) not started. Subordinate to a `../ZOO_BLUEPRINT.md` **that is not in this repo**
(**UNVERIFIED** — referenced at `CATALOG_PLAN.md:3`; presumably a private/parent doc).

**Catalog scale, measured 2026-07-25 by `scripts/gen_inventory.py`** (`CATALOG_PLAN.md:30-38`):

| Layer | Count |
|---|---|
| Published Hugging Face repos | **123** (122 owned + 1 contributor-owned) |
| Of those, **Core AI** repos | **70** (rest = pre-Core-AI Core ML ports, LiteRT collaboration repos) |
| Bundles inside them | **238** |
| Core AI repos with a card in `models/<model>/` | **52** |
| Repos with a recipe | **52** (was 6) |
| Bundles with an automated tier-1 check | **222** (was ~0) |
| Core AI repos with **no downloads in 30 days** | **55** |

**The three things that blocked reproduction** (`:44-53`) — a great "how on-device ML projects
rot" list:
1. *"Scripts hardcoded one machine's home directory."* — **47 files, 69 occurrences**. Fixed by
   routing everything through `conversion/_paths.py` (`ZOO_WORK_ROOT` / `ZOO_EXPORTS` /
   `ZOO_CODE_ROOT` / `HF_HUB_CACHE`). Acceptance test: `grep -rln "/Users/<name>" conversion/`
   returns nothing.
2. *"Prerequisites were prose."* — `notes = ["Runtime needs apps/…patch + COREAI_CHUNK_THRESHOLD=1"]`
   is invisible to a runner. Split into typed fields, and crucially **export-time vs run-time**
   prerequisites separated, because *"a bundle rebuilt without the runtime patch looks correct
   and then misbehaves in the app."*
3. *"The shipped configuration was often unrecorded."* — where it could not be derived, the
   entry says so instead of guessing.

Also `C0.2`: **75 uncommitted source files**, including the exporters for several *shipped*
bundles, were found and committed.

#### Conversion is NOT byte-deterministic — a hard, citable measurement

`CATALOG_PLAN.md:116-121` (echoed at `README.md:94-98`):

> Measured 2026-07-25: the same recipe run twice on the same machine, minutes apart, produces
> `.aimodel` bundles that differ from each other (**`main.mlirb` by 7 bytes, `main.hash`
> entirely**) — and the published bundle differs from both by **492 bytes out of 1.19 GB**.
> Conversion is not byte-deterministic, so "did this recipe reproduce the published bundle?"
> can only be answered behaviourally.

**Consequence: a stored hash is worthless as a reproducibility criterion for `.aimodel`
bundles.** This is a concrete, unique finding and directly relevant to anyone building CI around
Core AI exports.

#### `zoo_verify.py` — "tier-1" checks with no oracle, no device, no weights

Checks four things per bundle (`:75-76`): **eos/bos, chat template, context length, declared
precision** — and reads the expectations **from the source HF repository at run time** rather
than from transcribed local files: *"A transcription can be wrong and goes stale; the source
repo cannot."* `models/<model>/verify.toml` exists only to record a *deliberate* deviation, and
once recorded that becomes the bar.

First full run over **222 bundles: 162 PASS, 8 DIFF, 10 FAIL, 42 SKIPPED**.
After fixes: **180 PASS, 0 DIFF, 0 FAIL, 42 SKIPPED** (`:83-84`, `:203`).

#### The defects it found (all real, all shipped)

- **10 FAILs: Gemma 4 E2B/E4B bundles shipped NO chat template at all** while their source ships
  one — *"E2B is the most-downloaded text model in the catalog"* (`:96-98`). Root cause
  (`:177-181`): `export_gemma4_decode_pipelined.py` (and the VL / mixed-bit / pf variants)
  copied `tokenizer.json`, `tokenizer_config.json` and `special_tokens_map.json` **but not
  `chat_template.jinja`**, while the 12B exporter did.
- **`eos` vs `eot`** (`:88-94`, `:182-185`): Gemma 4 E2B/E4B shipped `eos_token: "<eos>"`, which
  *"a host loop stops on only at end-of-sequence, never at end-of-turn."* The source's own
  `eot_token` is `<turn|>`. Workaround in the wild: **`apps/CoreAIChat` hardcodes `EOT = 106`.**
  12B/31B ship `<turn|>` correctly.
- **MiniCPM5-1B `eos`** resolved from evidence, not changed: the source's chat template emits
  only `<|im_start|>` / `<|im_end|>` and its `generation_config` lists both `</s>` and
  `<|im_end|>` as stop ids, so the bundle's `<|im_end|>` is correct.
- **Nemotron-3-Nano chat template "drift" was a verifier bug**: the bundle ships the template
  both as a file and inside `tokenizer_config.json`, the two differ by **7 bytes**, and the
  verifier compared the field while `transformers` reads the file. Precedence fixed in the
  checker. (A very good cautionary tale about tokenizer-config duplication.)
- **A metadata privacy leak, published**: MinerU's `hf_model_id` and `tokenizer` fields *"held
  an absolute path from this machine, published."* Now names the upstream model. Worth citing in
  any "shipping model bundles" guide.
- **The overlay was three weeks stale** — missing the diffusion pipeline (FLUX.2 in-context
  editing), the VLM export path, and *"a long tail of decoder work"*, so applying it produced an
  environment that could not run the newer exports.

Two recipes remain permanently `unverified` for stated reasons (`:164-173`): `glm-4.7-flash`
(was `--head-sym` passed? *"unknowable from the record"* — settling it means re-exporting the
head both ways and comparing against a published **30 GB** bundle) and `flux2-klein-4b-edit`
(which flag selects the edit transformer).

**Meta-lesson the doc states about itself** (`:88-94`): *"Verification earns its keep by
contradicting the plan that asked for it."* The known-answer test's premise was wrong, and the
defect turned out to be in the models the draft called clean.

**Agent guardrails** (`:210-234`) — reusable verbatim for anyone letting agents touch an ML repo:
no publishing (no HF pushes, posts, or PRs against `apple/*`); **no deletion of artifacts**
(*"several are the only copy in existence"*); keep the repo small; **do not change export
hyperparameters while migrating** (*"A recipe must reproduce the published bundle, not improve
it"*); *"Verification tiers that cannot run report `skipped`. Never `pass` for a tier that did
not execute."*; and *"If the test's premise turns out to be wrong (as C1's did), report that
rather than adjusting the result to match."*

### 3.5 `CONTRIBUTING.md` — acceptance bars

Three bars (`CONTRIBUTING.md:10-22`): **License** (must permit redistributing converted
weights); **Parity** (teacher-forced / oracle top-1 parity vs the fp32 reference + a greedy
rollout sanity check); **Real hardware** (Apple silicon Mac minimum; *"Debug builds don't count
— measure Release."*).

**Toolchain requirement — a hard version floor, citable** (`CONTRIBUTING.md:24-28`):

> Export with **coreai-core ≥ 1.0.0b2**. Bundles exported with earlier wheels are rejected by
> the **Xcode 27 beta 3+ SDK loader** (`Failed to convert to versioned IR` — tracked as
> **FB23666783**); the zoo's own pre-b2 artifacts are being migrated for the same reason.

**Device gate** (`:52-64`): a maintainer runs the iPhone gate on an **iPhone 17 Pro (iOS 27
beta)** and posts back load time, cold + settled runs, parity vs the Mac reference, and thermal
behaviour, under the contributor's name. *"a gate can also come back no-go, which is still a
result worth publishing."* The first community port hit exactly this wall.

### 3.6 Directory structure

| Path | Contents (as listed this session) |
|---|---|
| `models/` | **59 model directories** + `_INVENTORY.md`, `_VERIFY.json`, `index.json`, `README.md`. One dir per model: card `README.md` + `recipe.toml` (+ optional `verify.toml`). Laid out to mirror `apple/coreai-models`. |
| `zoo/` | **49 `*.md` redirect stubs** (`bitcpm-8b.md`, `qwen3.5.md`, …) kept alive because *"~50 published Hugging Face READMEs link to it"* (`CATALOG_PLAN.md:149-150`). |
| `conversion/` | ~105 entries. ~60 `export_*.py` scripts, plus per-model dirs (`bitcpm/`, `bitvla/`, `chatterbox/`, `dllm/`, `dots_tts/`, `gemma4_raw_metal/`, `lfm_audio/`, `ltxvideo/`, `melband_roformer/`, `nemotron_asr/`, `parakeet/`, `quant_fp4/`, `qwen3_asr/`, `rwkv7/`, `sortformer_diar/`, `stable_audio/`, `timesfm/`, `triposplat/`, `unlimited_ocr/`, `vibevoice/`, `vjepa2/`, `voxcpm/`, `zimage/`), the `overlay/` patch tree, and the tooling: `zoo_convert.py`, `zoo_verify.py`, `coreai_gate.py`, `coreai_kit.py`, `_paths.py`, `_hf_catalog.py`, `_publish_tier1_fixes.py`, and one-off `_*_hf_upload.py` publishers. |
| `official/` | Only `official/README.md` — the `-CoreAI-official` bench exports of **Apple's own recipes** live on HF, not here (ten uncarded repos per `CATALOG_PLAN.md:40`). |
| `apps/` | 15 apps (`CoreAIChat`, `CoreAIChatMac`, `coreai-audio`, `coreai-video`, `CoreAIImageGen`, `CoreAIOCR`, `CoreAIDepth`, `CoreAISegment`, `CoreAITranscribe`, `CoreAIUpscale`, `CoreAIVideo`, `MiniCPMVisualIntel`, `QwenChatFast`, `TripoSplatMac`, `AppShared`) **plus five engine patches shipped as `.patch` files**: `coreai-pipelined-extra-states.patch`, `coreai-pipelined-per-token-inputs.patch`, `coreai-pipelined-static-inputs.patch`, `coreai-prefix-cache.patch`, `coreai-shared-product.patch`. Note these mirror exactly the fork commits in §2 — **`coreai-prefix-cache.patch` is the caller+engine form of `trimKVCache`.** |
| `swift/` | Four SwiftPM targets: `CoreAIRunner` (drives `.aimodel` LLM bundles incl. non-standard architectures), `coreai-run` (CLI), **`ZooFMProvider`** (the FoundationModels provider — §8.1), `zoo-fm-gate` (its gate harness). |
| `scripts/` | `aggregate_bench.py`, `gen_inventory.py`, `gen-cards`. |
| `_smoke/` | 19 gate/parity scripts, e.g. `gate_colmodernvbert_{doc,query,retrieval}_engine.py`, `gate_gemma4_mixedbit_verify_s4.py`, `gate_gemma4_mtp_drafter_bundle.py`, `check_gemma4_mtp_drafter_parity{,_real}.py`, `test_nanbeige{_parity,42}.py`, `test_ornith9b_eager_gate.py`, `test_qwen35_verify_chunk_parity.py`, `cv_from_device_bench.py`, and five `specdecode_*.py` (`reference`, `speedup_model`, `ngram_alpha_realtext`, `pretokenize_realprompt`). |

---

## 4. The porting playbook

### 4.1 `PORTING.md` step by step

351 lines. Structure: 10 numbered stages, each ending in a numbered **Checkpoint** that is a
falsifiable statement. Two archetype tracks run through all of it (`PORTING.md:10-13`):

| Track | Model | Archetype | Why it teaches |
|---|---|---|---|
| **V** (start here) | Depth Anything 3, `conversion/export_da3.py` | **Stateless single graph** — image in, depth out. No tokenizer, no state, no host loop. | The full pipeline with the fewest moving parts. |
| **L** (full course) | Qwen3.5, `conversion/export_qwen3_5_decode_pipelined.py` | **Stateful autoregressive LLM** — KV cache, prefill/decode, tokenizer, host sampling loop. | *"Most of the zoo is this shape."* |

**§0 — what a port actually is** (`:23-39`). Core AI (iOS 27 / macOS 27) runs models as
`.aimodel` **bundles**: one or more compiled static graphs plus assets (tokenizer files,
filterbanks, metadata). Runtime loads a graph (`GraphModel` in Swift, `coreai.runtime` in
Python) and executes on GPU/ANE/CPU. Porting = **re-author → export → verify**, and the reason
for re-authoring is stated precisely:

> You do this instead of exporting the Hugging Face modeling file because HF code carries
> training-time baggage (dynamic control flow, complex-number RoPE, optional branches) that
> either fails to trace or lowers badly. Re-authoring sounds heavier than it is: for a ViT it is
> an afternoon.

**§1 — setup** (`:43-61`): Apple silicon Mac on **macOS 27** (*"the runtime is OS-bound; betas
count"*), **Xcode 27**, Python 3.11+, this repo + an `apple/coreai-models` checkout, an iOS 27
iPhone for the device tier. Two practical notes: keep **two venvs** if the target model needs a
newer `transformers` than the export stack likes (*"Don't cross-contaminate"*), and *"GPU work on
the beta driver is happiest **serialized** — run one export/verify at a time."*
Checkpoint 1: `python -c "import torch, coreai_torch, coreai.runtime"` runs clean.

**§2 — should you port at all** (`:65-82`): GAP / EDGE (hard), then FIRST, **DEVICE**
(*"it fits an iPhone (~6 GB practical ceiling) = top tier. Mac-only = tier 2"*), QUALITY,
License. For a *first* port also: stateless, single graph, < 1 GB fp16.

**§3 — the oracle comes first** (`:86-109`):

```python
out = hf_model(**inputs)
np.savez("oracle.npz", **{k: v.float().cpu().numpy() for k, v in tensors.items()})
```
- Track V: one image + edge cases (non-square, high-contrast) → output maps. **Save the
  *preprocessed tensor* too**, because host preprocessing gets gated against it in §5.
- Track L: a fixed prompt → **per-step logits (or at minimum per-step argmax ids) for a few dozen
  greedy steps.** *"Per-step matters: an AR loop can look fine at step 1 and drift by step 30."*
- The normalization anecdote (`:104-106`) — see §3.2.

**§4 — re-author and export** (`:113-180`). The canonical export skeleton, verbatim
(`PORTING.md:121-134`):

```python
import torch, shutil
from pathlib import Path
from coreai_torch import TorchConverter, get_decomp_table
import coreai.runtime as rt

ep = torch.export.export(m.eval(), args=(), kwargs=inputs).run_decompositions(get_decomp_table())
prog = (TorchConverter()
        .add_exported_program(exported_program=ep, input_names=[...], output_names=[...])
        .to_coreai())
prog.optimize()
shutil.rmtree(out, ignore_errors=True)          # save_asset will NOT overwrite
prog.save_asset(Path(out), rt.AIModelAssetMetadata())
```

Note the gotcha baked into the comment: **`save_asset` will not overwrite** — you must
`rmtree` first.

> Core AI graphs are **static-shape**. You don't fight this; you design around it: fix the
> shapes that can be fixed, enumerate the ones that can't (a bundle may hold multiple graphs),
> and push variable-length logic to the host. (`:136-138`)

*Track V moves* (`:142-154`), in order:
1. Re-author backbone + head in plain torch straight from `model.safetensors`. *"Keep it boring:
   explicit cos/sin RoPE (no complex ops), explicit RMS/L2 norms with the eps inside
   (`F.normalize` silently drops it), no data-dependent branches."* ← the `F.normalize`
   eps-dropping trap is a genuinely non-obvious one.
2. **Fix the input contract.** DA3 exports as one square `R×R` graph (`R=504`); the host resizes
   any image to `R×R` and resizes the depth map back. *"Aspect distortion cancels for relative
   depth — **measured** (mean r ≈ 0.98 vs the official viewer across aspect ratios), not
   assumed."*
3. **Fold what you can into the graph** — DA3 bakes ImageNet mean/std normalization in-graph so
   the host feeds raw `[0,1]` RGB *"and one class of host bugs disappears."*
4. **Let dead code die** — export only the outputs you need; `optimize()` DCEs the branches that
   don't feed them (DA3 drops its camera/ray heads this way, no surgery needed).

*Track L = Track V + three systems* (`:158-170`):
1. **KV cache lives in the graph as mutable state** — in-place writes via `slice_update`, which
   **requires `remove_functionalization(ep)` after `run_decompositions` or the mutation is
   silently dropped.** (Silently! This is the single most dangerous export gotcha in the doc.)
2. **Prefill and decode are different shapes of the same weights**; the zoo's engine runs them
   as a pipelined pair.
3. **Tokenizer and sampling loop live on the host.**

**Honest caveat, verbatim** (`PORTING.md:171-176`) — important for anyone trying to reproduce:

> ⚠️ **Honest caveat (2026-07):** the zoo's *registered* LLM exports (`qwen3_5`, `gemma4_text`,
> …) currently depend on an overlay of the `coreai-models` package that lives as working-tree
> edits … Until that overlay is packaged, the reproducible-from-this-repo-alone path for a
> **new** LLM is the self-contained pattern the bespoke ports use (`conversion/bitcpm/`,
> `conversion/dllm/`, `conversion/rwkv7/`).

**§5 — the gates** (`:184-211`). Two, in order.

*Gate A — graph parity*:
```python
model = await rt.AIModel.load(Path(out), rt.SpecializationOptions.cpu_only())  # cpu_only for parity
fn = model.load_function("main")
res = await fn({"image": rt.NDArray(x)})
```
- `cpu_only()` for **parity** (fp16 GPU/ANE adds harmless but distracting noise); anything you
  **time** must use `SpecializationOptions.default()` — *"it is ~an order of magnitude faster and
  that is what ships."* **← a concrete, citable claim: `cpu_only()` is ~10× slower than
  `default()`.**
- Pass bar Track V: **cos ≥ 0.999** on every output tensor (*"you will usually see 1.000000"*).
- Pass bar Track L: **per-token cosine ≥ 0.999 on logits AND greedy argmax token-exact** over the
  oracle's decode steps. *"Token-exact is the headline; per-token cosine tells you where it broke
  when it isn't."*

*Gate B — host processing parity*: everything the app will compute (image resize/normalize, mel
spectrograms, detokenization, samplers) is implemented **in NumPy first**, as the exact algorithm
the Swift will use, gated end-to-end against the oracle's preprocessed tensors, **and only then**
translated to Swift. Rationale: *"host-side mismatches are the #1 source of 'the graph is perfect
but the output is garbage', and they are unfindable once the only implementation is inside an
app."*

Checkpoint 5: a `gate_*.py` script prints PASS from a clean run with no manual steps — *"This
script goes in your PR; it is the reviewable artifact."*

**§6 — compress** (`:217-234`) — see §5.5 below for the full compression notes. The four rules:
- Track V / small models (< ~1.5 GB fp16): **ship fp16**.
- Track L default: **int8 linear** — *"the reliably-safe LLM scheme on this stack."*
- **int4 is a cliff, not a slope** — *"the failure is capacity, so no clever rounding rescues
  it."*
- **The ANE rule**: *"statically-compiled ANE execution requires palettized (LUT) weights —
  blockwise-linear int4 is a GPU-only format there. If you aren't explicitly targeting ANE,
  target GPU and move on."*
- And: re-run **Gate A on the compressed bundle** — *"compression is part of the model, so it
  gates like the model."*

**§7 — Mac run** (`:239-255`). Time with `SpecializationOptions.default()` / GPU compute units;
**report load time and steady-state throughput separately** (first call includes JIT
specialization). And the loudest warning in the document (`:250-252`):

> ⚠️ **Never execute an iOS-compiled bundle on a Mac.** It can wedge the GPU/ANE stack and take
> the whole machine down (watchdog reboot). Mac bundles on Mac, iOS bundles on device. This is
> the one mistake in this document that costs a reboot instead of an afternoon.

**§8 — iPhone** (`:260-286`):
1. **AOT-compile large graphs.** *"On-device JIT specialization of a big static graph stalls or
   gets killed; roughly **≥ 1 GB means AOT**, ≤ ~50 MB JITs fine, in between try it."*
   ```
   xcrun coreai-build compile model.aimodel --output out/ \
        --platform iOS --architecture h18p \
        --preferred-compute gpu --min-deployment-version 27.0
   ```
   *"The architecture name tracks the **device identifier**, not the marketing name (iPhone 17
   Pro = `iPhone18,1` → `h18p`; M-series Macs → `h16c`). The result (`*.h18p.aimodelc`, **~2× the
   `.aimodel` size**) embeds the precompiled graph."*
2. **Getting it on device**: a debug app whose `Documents/Models/<X>/` is filled via
   Finder/`devicectl` copy, app preferring a sideloaded bundle over a download. *"Push many files
   individually rather than one giant transfer, and verify a copy by reading it back — wired-
   tunnel transfers can report success falsely."*
3. **Measure with a self-test, not a UI**: an env-gated headless entrypoint (`<X>_SELFTEST=1`)
   that loads the bundle, runs **1 cold + N warm** passes, computes the metric (tok/s, RTF,
   ms/frame) and writes a result file. *"Numbers measured through a chat UI are not comparable to
   anything."*

**§9 — publish** (`:292-321`). Five artifacts: HF weights **under your own account**; export +
gate scripts in `conversion/`; a card at `models/<model>/README.md`; a `recipe.toml`; a README
table row. One publishing trap worth extracting (`:298-300`):

> `swift-transformers` rejects unregistered `tokenizer_class` values — retag the bundle's
> `tokenizer_config.json` to a registered class (e.g. `PreTrainedTokenizer` → `BPETokenizer`) in
> your upload script; decode stays exact because it is driven by `tokenizer.json`.

Review bar (`:319-321`): Gate A numbers as claimed and **re-runnable** · host processing
NumPy-gated · license clean · card complete with measured, device-attributed numbers · **no
weights/binaries in the git PR itself**.

**§10 — the traps in one place** (`:332-342`) — the process traps, listed in §3.2 above.

### 4.2 Skill `port-a-model-to-the-zoo`

A 96-line map of `PORTING.md` — deliberately *not* a duplicate: *"This skill is the map of it,
plus the parts an agent gets wrong."* Notable design choices worth stealing:
- Its frontmatter `description` enumerates the **user phrasings** that should trigger it,
  including the failure phrasing: *"why does my exported bundle produce garbage"*.
- It **explicitly cross-references Apple's skills** as `Skill("coreai-skills:working-with-coreai")`
  and `Skill("coreai-skills:model-authoring")` and tells the agent to install both.
- A 9-row stage table mapping stage → where it is written down, so the skill stays a router.
- Closes with the authority boundary: *"Publishing to Hugging Face, posting, and PRs against
  `apple/*` are the owner's calls, not yours."*

### 4.3 Skill `reproduce-a-zoo-model`

152 lines, a different job: rebuild/verify/run an *already published* model.
- **"Start here"**: `models/index.json` is the machine-readable catalog — *"Read it first — do
  not grep the tree."* Schema sample (`SKILL.md:29-34`):
  ```json
  {"family": "qwen3.5", "card": "models/qwen3.5/README.md",
   "recipes": [{"name": "qwen3.5-0.8b", "status": "verified",
                "hf_repo": "mlboydaisuke/qwen3.5-0.8B-CoreAI",
                "bundle": "gpu-pipelined/qwen3_5_0_8b_decode_int8hu_block32_sym",
                "run": "python3 conversion/zoo_convert.py run qwen3.5-0.8b"}]}
  ```
- Interpreter setup, verbatim (`SKILL.md:72-76`) — the overlay mechanism, pinned to a base commit:
  ```bash
  git clone https://github.com/apple/coreai-models.git
  git -C coreai-models checkout "$(awk -F': *' '/^commit:/{print $2}' conversion/overlay/BASE)"
  python3 conversion/overlay/apply.py ./coreai-models
  cd coreai-models && python3 -m venv .venv && . .venv/bin/activate && pip install -e python/
  ```
- **Verdict semantics** (`:113-121`), a genuinely good four-state model:
  `PASS` (agrees with source) · `DIFF` (deviates with **no recorded reason**; not automatically a
  bug — *"swapping `eos_token` for the turn terminator is a real ship-time decision. It becomes
  correct by being recorded in `models/<family>/verify.toml`, after which an unexplained
  deviation fails."*) · `FAIL` (wrong on its own terms) · `skipped` (*"Never report a skipped
  check as a pass."*).
- *"This is also the 'what did this SDK beta break?' tool: rerun `--all` and diff
  `_VERIFY.json`."* — a nice regression-tracking idiom for a moving beta OS.

### 4.4 Comparison with Apple's own `model-authoring` skill

Read `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models/skills/skills/model-authoring/SKILL.md`
(153 lines; siblings `working-with-coreai` 199 lines, `model-compression-exploration` 191 lines,
plus `references/{neural_engine_rules,gpu_rules,common_issues}.md`).

**They are complementary, not competing — and the zoo says so** (`AGENTS.md:117-118`,
`port-a-model-to-the-zoo/SKILL.md:17-19`): *"Apple's own `coreai-skills` covers the toolchain
itself; install both."*

| Axis | Apple `model-authoring` | Zoo `port-a-model-to-the-zoo` |
|---|---|---|
| Scope | **Inside** the PyTorch module: how to write ops so they lower well | **Around** the module: oracle, gates, device, publishing |
| Organizing frame | Compute unit (ANE vs GPU vs CPU) and layout | Process stages with checkpoints |
| Verification metric | **PSNR in dB** | **cosine ≥ 0.999 + token-exact argmax** |
| Verification bars | re-authored vs source **> 70 dB**; ANE-layout vs GPU-layout **> 70 dB**; compiled vs torch **≥ 40 dB**; after 4-bit palettization **≥ 35 dB** (`model-authoring/SKILL.md:94-99`) | Track V cos ≥ 0.999 per output; Track L per-token cos ≥ 0.999 **and** greedy token-exact |
| Compression guidance | palettization PSNR table: 8-bit ~2× / > 55 dB (flag < 50); 4-bit ~4× / ~40 dB (flag < 35); 2-bit ~8× / ~25–35 dB *"Usually unacceptable"* (`:149-153`) | *"int4 is a cliff, not a slope"*; int8 linear default for LLMs; **read the generations** |
| Device/deploy | Not covered | AOT (`h18p`), sideload, self-test entrypoint, thermals |
| Publishing | Not covered | HF repo, card, recipe.toml, README row, `zoo_verify.py` |
| Authority | Apple-official | Community |

**Where they genuinely differ in advice, not just scope:**

1. **Metric.** Apple's stack is PSNR-in-dB throughout (including a compression PSNR table);
   the zoo uses **cosine + token-exactness** for LLMs and is explicit that *"Step 1 looking fine
   is not a gate; AR drift shows up late."* Apple's skill has no per-token AR-drift gate.
   Neither is wrong — but a guide should note that a **PSNR ≥ 40 dB "compiled vs torch" pass can
   coexist with a non-token-exact LLM**, which is the failure the zoo's gate is built to catch.
   *(This is my reading of the two documents, not a claim either author makes. Flagged.)*
2. **KV cache.** Apple's skill gives two canonical shapes and a hard rule
   (`model-authoring/SKILL.md:127-132`): ANE `[n_layers, B, H_kv*D, 1, max_S]` with a
   **readonly functional I/O** pattern (no cache writes in the model); GPU
   `[n_layers, B, H_kv, max_S, D]` with a **stateful export wrapper** (`register_buffer` +
   `hoistToArg`). Plus: *"Do not use stateful transforms for token generation — state resets
   between inference calls."* The zoo's `PORTING.md` instead prescribes in-graph mutable state
   via `slice_update` + `remove_functionalization(ep)`. **These are describing different
   mechanisms at different layers; a guide should not present them as alternatives without
   checking.** **UNVERIFIED** how `hoistToArg` and `remove_functionalization` relate — I did not
   find them in the same file this session.
3. **"Run code, don't read code"** (Apple, `:76`) vs the zoo's *"the oracle comes first"* — the
   same instinct, but the zoo turns it into a persisted artifact (`oracle.npz`) that gates every
   later stage, whereas Apple's phase-1 is discovery-only (`register_forward_hook` to capture
   intermediates).
4. Apple mandates a **`from_source_model` classmethod** on every re-authored model
   (`:103-119`) — *"no hardcoded constants"*, config-driven construction + `load_weights_from`.
   The zoo has no equivalent convention; its exporters load `model.safetensors` directly.
5. Apple's compute-unit routing table (`:36-42`) maps user vocabulary → compute unit
   (energy/battery/iPhone → ANE; throughput/macOS/large → GPU; correctness → CPU) and instructs
   the agent to use **outcome-oriented language** (*"optimized for energy-efficient inference on
   iPhone" rather than "targets Neural Engine"*). The zoo is bluntly GPU-first: *"If you aren't
   explicitly targeting ANE, target GPU and move on."* — and its measured ANE numbers (§7)
   support that stance.

---

## 5. Platform mechanics (knowledge/ Tier 1)

### 5.1 `coreai-overview.md` — the stack, per the community

*"**Core AI** is Apple's Core ML successor, announced at WWDC 2026 (iOS/macOS 27). It keeps the
'convert once, run on ANE/GPU/CPU' idea but replaces the `.mlpackage` + coremltools stack with a
new IR, compiler, and runtime."* (`knowledge/coreai-overview.md:3-5`)

**Three open Apple repos + a closed runtime** (`:9-16`):

| Repo | Core ML analog | Role |
|---|---|---|
| `coreai-torch` | coremltools converter | PyTorch → Core AI IR. Entry: `TorchConverter().add_exported_program(...).to_coreai()`. Extension points: `register_torch_lowering`, `composite_ops` (SDPA, RoPE, RMSNorm, **GatedDeltaUpdate**, **GatherMM**), `ExternalizeSpec`. |
| `coreai-optimization` (`coreai-opt`) | `coremltools.optimize` | quant / palettization / pruning (**torchao PT2E**). |
| `coreai-models` | — | Apple's own model zoo + Swift runtime + agent skills. |

> *"The **compiler + runtime are closed-source**, shipped as the `coreai-core` Python wheel (the
> `coreai.runtime` module) + the OS Core AI framework (`CoreAI.framework`, on-device)."*

**The `.aimodel` bundle** (`:20-22`): a **directory** bundle of
`{metadata.json, main.mlirb, main.hash}` (IR + manifest). It can hold multiple **functions**
(entrypoints) and declares **states** — *"tensors the graph mutates in place, surfaced via a
`state=` API at runtime — this is how KV caches live."* (Matches the byte-nondeterminism finding
in §3.4: it is `main.mlirb` and `main.hash` that differ run-to-run.)

Pipeline (`:26-33`):
```
PyTorch (re-authored model)
  → coreai-opt (optional compress: palettize / quantize)
  → coreai-torch TorchConverter → Core AI IR
  → .optimize() → save_asset() → .aimodel
  → [Python] coreai.runtime  (macOS, for convert/verify)
  → [Swift]  CoreAI.framework (on device, iOS/macOS 27)  ── AOT-compiled by `aimodelc`
```

Key division of labour (`:35-36`): *"**macOS is enough to convert + run (Python) + numerically
verify.** On-device iOS / the Swift runtime / the AOT compiler (`aimodelc`, shipped in Xcode 27)
need iOS/macOS 27."*

**Toolchain (attributed to WWDC 324 / 326)** (`:43-48`): **Core AI Debugger** — a separate macOS
app that visualizes the converted graph, inspects intermediate tensor values, and *"trace[s] each
op back to the Python source line that introduced it"*; plus an in-Xcode **debug gauge**
(streaming Core AI activity) and **Core AI Instruments** for profiling inference **and
specialization**.

**Foundation Models integration** (`:49-58`) — the crux for FM guides:

> `CoreAILanguageModel` (from `coreai-models`'s Swift `CoreAILM`) plugs your own `.aimodel` into
> the **same `LanguageModelSession` API** as Apple's built-in on-device LLM: same
> `session.respond(to:)`, streaming, and **`@Generable` guided/structured generation**. … (For
> non-standard architectures the high-level pipeline can't express — multi-state SSMs, dual-KV —
> drop to the low-level `CoreAI` framework.)
>
> *Update 2026-06-11, verified:* with the pipelined-engine patch stack, the non-standard bundles
> (hybrid Qwen3.5, SSM Granite/LFM) **DO** run behind `LanguageModelSession` too; note **guided
> generation requires engine logits, which GPU-pipelined bundles don't expose**.

**← That last clause is a first-class finding for the FM guides: on a GPU-pipelined bundle,
`@Generable` guided generation is unavailable because the engine samples on-device and never
surfaces logits.** Cross-checks with `InferenceEngine.supportsLogits` in the fork
(`InferenceEngine.swift:131` region; default `false`, overridden `true` by sequential/static-shape
engines). Community-verified, not an Apple statement.

**Why the zoo exists** (`:62-65`): *"Apple's `coreai-models` zoo lags ~one generation (Qwen3 /
Gemma 3, no VLM) and its Swift runtime assumes standard `input_ids → logits` + single KV
models."* — consistent with the file-set diff in §2.1, though note Apple's repo *has since*
added SAM3/VLM/Speech (§2.1), so this critique is time-stamped and partially superseded.

### 5.2 `aot-and-specialization.md` — AOT, specialization, and the 4B wall

Sourced by the author to WWDC **324 "Meet Core AI"** and **326 "Integrate on-device AI models"**
(with local transcripts at `ondevice/_wwdc{324,326}_transcript.txt` — **not in this repo**), plus
Apple docs and `coreai-models` source.

**What specialization is** (`:12-18`): a shipped `.aimodel` is **source/device-agnostic**; the OS
**specializes** it for the specific device + OS version via two transforms —
(1) *"a core set of compilation steps that segment, plan, and optimize compute — **this is where
most of the latency is**"*; (2) *"executable-artifact generation for the compute units used —
these artifacts are **tied to the device + OS version**."* Result is cached. Quoted Apple
guidance: *"This process can take a significant amount of time for very large models… avoid
having model specialization occur within user-interactive flows."*

**Community finding on top of that** (`:20-22`): *"a **dynamic**-shape core re-specializes on
every new sequence length (**~60–80× per-shape compile tax**)."* — i.e. dynamic shapes are not
merely slower, they re-trigger the expensive step. **UNVERIFIED**: the underlying measurement
lives in a project memory not in this repo.

**The Swift API** (`:25-34`), quoted as WWDC 324 verbatim:
```swift
let cache = AIModelCache.default
guard let model = try cache.model(for: modelURL, options: .default) else {
    informUser("Preparing AI features. This may take a while…"); return
}
// or, ahead of first use:
try await AIModel.specialize(contentsOf: modelURL)
```
`AIModelCache` can delete unused entries, control retention policy, and **share a cache across
apps in one app group**. `SpecializationOptions` (Python: `runtime/_specialization_options.py`)
exposes `cpu_only()`, `default()`, `from_preferred_compute_unit_kind(ComputeUnitKind.gpu()/.ane()/…)`.

#### The 4B wall — device-verified

`aot-and-specialization.md:48-60`. Small decoders (≤ ~1–2 B, e.g. MiniCPM5-1B) ship as portable
`.aimodel` IR and specialize on device fine. A **4 B** decoder does not — verified on
**FastContext-1.0-4B (Qwen3-4B), iPhone 17 Pro / iOS 27**:

| Attempt | Failure |
|---|---|
| **macOS**-tagged IR on iOS | no iOS delegates to load → `NSPOSIXErrorDomain Code=2` |
| **iOS**-tagged palettized IR, on-device GPU specialization | *"exhausts the device's scratch disk mid-compile → `LLVM ERROR: No space left on device`"* |
| **iOS ANE** bundle | static-loads (**31 ANE regions, ~518 s cold**) but warmup **inference** dies: `com.apple.appleneuralengine` / `ANECompilerService` **`Code=4097`** ("ANE compile failed") |
| **GPU AOT `.aimodelc`** (`--preferred-compute gpu --architecture h18p`) | ✅ the only working on-device path |

Conclusion: 4B-class GPU bundles **must** be AOT-compiled per device class and shipped as
`.aimodelc`. *"**ANE is worse at this size.**"*

#### Tool naming, resolved

`:62-70`. **`xcrun coreai-build compile` = the verb; `aimodelc` = the compiler binary and the
compiled extension.** Compiled bundle is `modelName.architectureName.aimodelc`
(`ModelBundle.swift:103`); the runner accepts either `.aimodel` or `.aimodelc`
(`LLMRunnerMain.swift:719-722`); `aimodelc` exists at `Xcode-beta.app/.../usr/bin/aimodelc`.

Full CLI surface (`--help`, verified 2026-06-10, `:73-77`):
```
coreai-build compile <input.aimodel> [--output <dir>] [--platform iOS|macOS|watchOS|visionOS|tvOS ...]
    [--min-deployment-version 27.0] [--preferred-compute gpu|neural-engine|none]
    [--architecture <arch> ...] [--expect-frequent-reshapes]
```
Output: **one `.aimodelc` per device architecture**, `base.<arch>.aimodelc`, each containing
`main-<arch>.mlirb` + `main-<arch>-delegates`. Ship as **Background Assets**; the app detects the
device arch and requests the matching one.

#### ⚠️ Incident-grade finding: `expectFrequentReshapes` on a fixed-shape graph kills the AOT bundle (device-validated 2026-07-23)

`aot-and-specialization.md:88-106`. **The hint is not free insurance — it is a request for a
*reshape-tolerant* specialization.** Ask for it at load time on an all-static graph and the
runtime **stops using the AOT specialization and compiles on device**, which on iPhone 17 Pro
segfaults inside the MPSGraph AICode compiler:

```
EXC_BAD_ACCESS (SIGSEGV) … MPSGraphAICodeCompilerDelegate getInitializedAICodeBytecodeWithPayloadPrefix:
  → Compiler_coreAI.compile(moduleBytecode:to:with:) → libODIECompiler … CompileForDelegates
```

*"No error string, no partial output — the app just dies at `AIModel(contentsOf:options:)`."*

- Found on **VibeVoice** (5 fixed-shape graphs: `q=1` stateful decode + fixed-T decoder).
  `expectFrequentReshapes = true` → SIGSEGV on the first graph; `= false` → **all 6 loads in
  2.6 s, gate PASS**.
- **Compiling with `--expect-frequent-reshapes` does NOT make the runtime hint safe** — both the
  plain and the reshape-hinted `.aimodelc` crash when the *runtime* asks for the hint.
  **It is the load-time option that matters.**
- Rule: `expectFrequentReshapes = true` **only** where shapes really change (dynamic query length
  / bucketed prefill — MinerU decode, spec-decode verify, gemma4's 3-stage pipeline). Static
  decode (`S=1`) and fixed-T vocoders must load **without** it.

#### ⚠️ Architecture names track the DEVICE IDENTIFIER (device-validated 2026-06-10)

`:108-121`. The `--architecture` h-numbers follow the hardware **device-identifier major
version** (`iPhone18,1`, `Mac16,5`), **not** the marketing name:

- **iPhone 17 Pro = `iPhone18,1` → `h18p`.** An `h17p` `.aimodelc` pushed to it fails to load with
  `invalidCompiledModel`; the same model compiled `--architecture h18p` loads and runs.
- **M4 Max Mac = `Mac16,x` → `h16c`.** *"Of all 20 macOS archs, only `h16c` loads in the Python
  runtime on an M4 Max; h17\*/h16g/h16s all raise RuntimeError."*
- **`coreai-build compile` EXITs 0 for ANY requested arch** — *"a successful compile does NOT
  validate the arch choice; only a device load does."* The doc explicitly corrects its own earlier
  note ("h17p for iPhone 17 Pro" was name-matching, unvalidated). **← Excellent example of the
  archive self-correcting; cite it as such.**
- Bonus, same check: **a custom-Metal-kernel (`TorchMetalKernel`) model survives AOT** — the
  `.aimodelc`'s `specialized_model_*.mpsgraph` contains the full `[[kernel]]` MSL signature +
  compiled MTLB in `resources.bin`, and *"the compiled asset's outputs are **bit-identical** to
  the source `.aimodel`."*

#### AOT status / measured load-time wins

`:128-155`:
- ✅ AOT works on the beta (verified 2026-06-10; Xcode `27A5194q`, Metal Toolchain
  `v27.1.5194.15` / `metal 32023.917`, macOS 27.0 `26A5353q`):
  `--platform macOS` → EXIT 0, **20 per-arch `.aimodelc`** (`h13c…h17s`);
  `--platform iOS --preferred-compute neural-engine` → EXIT 0, **8** (`h13g h14g h15g h16g h16p
  h17g h17p h18p`).
- ✅ **AOT avoids the first-run-compile OOM.** The un-chunked **35-layer monolith**
  (`gemma4_e2b_hostcache_L35_int8.aimodel`, **1.8 GB**) compiled for iOS ANE `h18p` (EXIT 0,
  ~4.0 GB host RSS) **loads on iPhone 17 Pro with `cu=ane` in 6.5–8.1 s, no jetsam** (available
  memory 6130 → ~2810 MB).
- ❌ **But EXECUTE dies**: *"the first inference step is jetsam-SIGKILLed — load ✅ / run ❌."*
  The ANE load leaves only ~2.8 GB headroom (the GPU path leaves ~6.0 GB for the same-size core)
  and the first-step working set blows through it.
- ❌ **The 6 host-cache chunk graphs CANNOT be AOT-compiled — `coreai-build` itself SIGSEGVs**
  (host-side `ANECompilerOffline::~ANECompilerOffline → objc_release`, inside MPSGraph's
  `anePreCompileBinary`; ~0.9 s in, all 6 chunks, both archs). The L35 monolith from the same
  authoring compiles fine → *"beta compiler bug, size/shape-correlated."* So the chunked-ANE path
  gets **no AOT first-load relief**.
- ✅ **GPU monoliths fully work AOT'd**, with a clean A/B on first load:
  **`.aimodelc` 4.9 s vs `.aimodel` 19.2 s true-cold specialize (~4×; post cache-wipe); warm 0.0 s
  both** (the OS cache serves `.aimodelc` too). The int4-kernel `.aimodelc` (1.9 GB) cold-loads and
  verifies 8/8.

#### The int4-head split by compute unit

`:156-159`: **k-means palettization is `F.linear`-only**, so the GPU int4-class head is a
**fused-int8 Metal kernel** (GPU-only). The **ANE can't run that MSL**, so its low-bit head path
is **int4 per-output-channel *quantization* on a Conv2d head** (coreai-opt quant, not
palettization) and/or **vocab pruning**, or split the head to the GPU.

#### ANE-later is blocked on an Apple bug, not on authoring

`:160-165`: *"The official iOS ANE stateful decode is blocked by the SAME KV-write bug — Apple's
own `KVCacheHandler` (`primitives/ios/cache.py`) uses the data-tensor `in_step` write that
SIGSEGV/SIGTRAPs the beta (verified on GPU; device-ANE fails MLIR lowering). So ANE-later
genuinely waits on the Apple fix (FB23024751); it is not a self-inflicted pattern."* And:
*"Apple's own skill even prescribes the **readonly-KV-I/O** (host-cache) pattern as the fix for
stateful-reset (`common_issues.md:145-148`) — i.e. host-cache is an Apple-acknowledged
workaround, not a hack."*

### 5.3 `compute-units-and-authoring.md` — ANE vs GPU, the two first-class modes

Framing (`:4-5`): *"**iOS/ANE = static-shape, BC1S, Conv2d, per-head, fp16-only**; **macOS/GPU =
dynamic-shape, standard layout, fused, custom kernels**. These are Apple's two first-class
modes."* Sourced to Apple's own `neural_engine_rules.md` / `gpu_rules.md` / `common_issues.md`
plus `primitives/{ios,macos}/`.

| | ANE | GPU | CPU (BNNS) |
|---|---|---|---|
| Best for | energy-efficient, fixed shapes, iOS foreground | large models, dynamic shapes, batch, throughput | validation, fallback |
| Shapes | **fully static** (one fn per shape config) | dynamic OK | any |
| Layout | **BC1S** `(B, C, 1, S)` | standard `(B,S,D)` / `(B,H,S,D)` | any |
| Projections | **1×1 Conv2d** (conv engine accumulates fp32) | `nn.Linear`, fused QKV | any |
| Attention | **per-head, sequential** (no fused SDPA) | **fused native SDPA** | either |
| KV cache | **readonly functional I/O** (host writes), seq on **dim 4** | **stateful** (`mutable_slice_update`), seq on **dim 3** | — |
| Custom MSL kernels | **NO** | **YES** (`TorchMetalKernel`) | no |
| Precision | **fp16 only** (no fp32 literals/intermediates) | fp16 weights, fp32 intermediates OK | fp32/fp16 |

**ANE authoring rules, the high-leverage ones** (`:26-46`) — each cited to Apple's reference files:
- **Conv2d not `nn.Linear`** — Linear falls back off-ANE; Conv2d maps to the conv engine **and
  accumulates in fp32** (the fix for fp16 matmul drift over many layers).
- **No fp32 anywhere** — *"a single Python float literal (`1.0`) creates an f32 buffer and breaks
  ANE residency. Use `torch.ones(1, dtype=x.dtype)`. **`.float()` is a no-op on the ANE**
  (MPSGraph drops the cast). To get fp32 accumulation you must use an op the hardware accumulates
  in fp32 (Conv engine, LayerNorm kernel)."*
- **RMSNorm trap**: composite RMSNorm computes `mean(x²)` in fp16 → **overflows** large
  activations. Fix = the **`[x,-x]` LayerNorm trick** (`LayerNorm([x,-x]) == RMSNorm`, and the ANE
  runs LayerNorm with an fp32-accumulating hardware kernel). *This is the zoo's gemma4 fix.*
- **Causal mask**: shape `(1, key, 1, query)` (transposed vs GPU), masked value **`-40000.0` not
  `-inf`** — *"ANE softmax mishandles IEEE −inf."*
- **RoPE as input**: precompute cos/sin outside the graph, pass as 4D `(1, head_dim, 1, S)` —
  *"in-graph `gather_nd` makes rank-3 → ANE rejects."*
- **Cache the post-RoPE key** (`key_rope`), not raw — *"else stale keys → PSNR ~20 dB."*
- Last dim aligned to 64 B / power-of-2; **rank ≤ 5**; strides/dilations factored into 2s and 3s;
  large kernels decomposed (`k = k1+k2-1`).
- **Chunked prefill (`S_q=64`)** for long prompts — *"fp16 per-token decode drifts ~5–10 dB / 50
  tokens."*

**Runtime compute-unit selection is derived from STRUCTURE, and is a preference not a lock**
(`:115-127`) — an important correction to the folk model "iOS ⇒ ANE":

> The official runtime does NOT hard-pin a compute unit … the Swift runtime probes the model's
> **structure** and derives a *preference* (`CoreAIShared/Runtime/ModelStructure.swift:57-66`):
> **`chunkedStatic`** (chunked + static shapes) → `preferredComputeUnitKind: .neuralEngine`;
> **`dynamic`** (single `main`) → `.gpu` + `expectFrequentReshapes`.
> … AOT `--preferred-compute` **defaults to `none`** (compiler decides), and a "compiles but runs
> on CPU" case needs an explicit `--preferred-compute neural-engine`. So "iOS ⇒ ANE" is the
> *default tendency*, not a guarantee. The axis is **structure, not literally iOS**.

**Verification gates restated in PSNR** (`:129-133`), matching Apple's skill: re-authored vs
source (fp16) **> 70 dB** (investigate < 60); compiled vs torch (fp16) **≥ 40–50 dB**; 4-bit
palettized **~40 dB** (investigate < 30). Plus the hardest-won lesson (`:135-136`):

> **Localize divergence with REAL inputs** — degenerate constant-input probes lie (they said an
> ANE chunk was exact when real inputs showed it diverged from layer 1).

**The zoo's stance** (`:138-143`): **GPU now** (custom kernels, beta-robust) **+ ANE later** (when
the KV-write bug lifts + int4 head + AOT).

#### The MoE decode findings (this section is dense with unique numbers)

`compute-units-and-authoring.md:55-104`. Three stages of a real optimization story:

**(1) The problem — `GatherMM` over-reads.** *"`GatherMM` gathers then runs a DENSE matmul — it
does **NOT** read only the routed experts, so MoE decode is over-read-bound, not
active-param-bound (Qwen3.6-35B-A3B int8 sits at ~25 % of BW)."*

**(2) The dtype effect, "the first direct Core-AI int4-vs-int8 MoE measurement"** — LFM2.5-8B-A1B:

| Scheme | Decode | Bundle | Effective BW | Interpretation |
|---|---|---|---|---|
| int8 | **39 tok/s** | 8.8 GB | 345 GB/s | ≈ full-read BW-saturated |
| int4 | **170 tok/s** | 5.0 GB | **848 GB/s** (> physical BW) | ⇒ int4 is **NOT** full-reading |

*"dropping a MoE to int4 buys ~4× decode here, not the ~2× the byte ratio predicts — but non-QAT
int4 flips structural tokens (broken grammar), so int8 stays the quality floor."*
**← A superlinear-in-dtype effect. Genuinely surprising and highly guide-worthy.**

**(3) The fix — a custom `gather_qmm` Metal kernel** (`models/macos/moe_metal.py`, 2026-06-13). A
`coreai_torch.TorchMetalKernel` matvec that *"takes the routed expert indices as a kernel INPUT
and reads ONLY the top-k experts' weight slabs (`QP[w,n,e]`, `e = IDX[slot]` — indexed global
load; the other E−k experts are never fetched)."* `MetalSwitchGLU` is a drop-in for `SwitchGLU`;
`metalize_moe(model, nbits)` swaps every MoE layer. Key enabler: *"rank-3 DSL buffer indexing +
a data-dependent gather both lower **and** run on the GPU."*

Results on **LFM2.5-8B-A1B, M4 Max**:

| Config | Decode | Size | Note |
|---|---|---|---|
| int8 MoE, stock GatherMM | 39 tok/s | 8.8 GB | over-read bound |
| int8 MoE, `gather_qmm` | **141 tok/s** | — | **3.6×**, reads 4/32 experts |
| int4km, `gather_qmm` | **162.7 tok/s** | **4.7 GB** | iPhone-jetsam-safe |
| int4km on **iPhone 17 Pro (A19 Pro) GPU** | **~32 tok/s** | 4.7 GB | *"the zoo's first iPhone MoE on hardware"* |

Numerics: *"kernel == 'select-from-all' bit-for-bit."*

**(4) Quality — which quant scheme, gated by fp32-oracle margin rule on a 41-token paragraph**
(kernel is bit-exact, so the *scheme* is the lever):

| Scheme | Flips / 41 tokens | Verdict |
|---|---|---|
| `sym8` (symmetric-LINEAR int8, per-K-block-32 scale) | **+1** (at the fp16 ceiling) | **CLEAN — the Mac ship** (also 140 tok/s) |
| k-means int8 | +5 | *"lossier — don't use"* |
| k-means int4 | +12 | wall |
| affine-block-32 int4 | +11 | wall |

*"int4 is a WALL … non-QAT int4 can't reach clean (needs QAT weights)."* The doc also
**retracts its own earlier claim**: *"(An earlier 'fp16-faithful' claim was WRONG — held only on a
degenerate loop-y prompt; the gather kernel's QUALITY is set by the expert quant scheme, not the
gather.)"*

**(5) ⚠️ The refinement that reverses the rule — top-1 routing** (ZAYA1-8B, 2026-06-22,
`:89-103`). This is one of the sharpest results in the whole archive:

> **"sym8 not k-means" holds for top-k ≥ 4, REVERSES for top-1.** The sym8-wins result was
> measured on top-4 (LFM) / top-8 (Qwen3.6) MoE, where each token's FFN output is a weighted sum
> of k experts so expert-quant error **AVERAGES (~/√k)** and even crude linear int8 survives.
> **ZAYA is top-1 of 16: one token → one expert, error NOT averaged → `sym8` (linear) collapses**
> (engine skips the reasoning block + emits `<pad>`; diverges from fp16 at token 1), while
> **`km8` (k-means int8, 256-entry codebook) recovers fp16 quality** (matched fp16 29 tokens
> token-exact). So: **top-k ≥ 4 → sym8; top-1 / low-k → km8** (k-means fits outlier expert weights
> that linear int8 clips).

Two gotchas from that session: (a) a real bug in `moe_metal.py` `_proj` —
`k_pad = qp.shape[2] * (4 if sym8 else 8)` lumped km8 (4 bytes/uint32, like sym8) with km4
(8 nibbles) → `K_pad = 2K` einsum mismatch; **FIX** = `(4 if scheme in ("sym8","km8") else 8)`
(*"km8 was unusable zoo-wide before this"*). (b) *"`MetalSwitchGLU`'s eager torch path is
unreliable (garbage on MPS) — judge schemes ONLY via a real export + engine run, never
eager-MPS."* Fallback for Mac-only models when even km8 is risky: **skip metalize entirely →
plain fp16 `SwitchGLU` / dense `GatherMM`** (ZAYA 27 tok/s vs km8 49, *"zero quant loss = the Mac
quality ceiling"*).

### 5.4 `conversion-guide.md` — the export gotcha catalogue

The single most practically useful file in `knowledge/`. 186 lines, almost all of it distinct
traps. Canonical API block matches `PORTING.md` §4, with three extra API facts (`:21-25`):
`save_asset` takes a **`Path` not a `str`**; `minimum_os` **defaults to v27**;
**`AIModel.load` is async, `load_function` is SYNC, calling the function is async** —
*"Mixing these up is the most common first error."*

**Precision / option traps**
- `cpu_only()` vs `default()`: **TripoSplat DiT 24.2 s → 2.6 s per call, ~9.3×**, and *"cos vs
  cpu still 1.000000"*. Landmine: *"`coreai_kit.run` **defaults to `cpu_only`**, so
  apps/benchmarks that copy it silently run on CPU — override it."*
- **`AIModel.load(path, None)` trips `RuntimeError: MPSGraph Unresolved symbol
  (prepare/initialize)`** on the GPU path — pass an **explicit** `SpecializationOptions.default()`
  or `.cpu_only()`, never `None`. (And `coreai_kit.run` passes `None` for the non-cpu branch.)
- **Keep the `AIModel` reference alive** in a persistent multi-call runner — *"storing only the
  `load_function` lets the model get GC'd and the function then returns **GARBAGE** (no crash,
  just wrong output → looks like a conversion bug). Hold `self.models[name] = m`."*

**Tracing / lowering traps**
- **Unsupported ATen ops surface at `add_exported_program` validate time**, not runtime. e.g.
  `aten.remainder.Scalar` (tensor modulo) is unsupported.
- **In-place state writes need `remove_functionalization(ep)`** after `run_decompositions` —
  *"Without it the mutation is dropped."* (silently)
- **`ExternalizeSpec` marks ops by *class***; if the export unit holds submodules of that class
  that are NOT in the traced graph (e.g. a front-end norm kept as an attribute), externalizing
  fails with *"custom op not found"*. Opt out with `coreai_externalize_specs = ()` on the module.
- **No complex ops** (`torch.polar`, `view_as_complex`/`view_as_real`, complex `*`). Rewrite
  complex RoPE as real cos/sin: `rope` returns `stack([cos,sin],-1)`; apply as
  `(x_re·cos − x_im·sin, x_re·sin + x_im·cos)`.
- **`F.normalize` drops the eps denom clamp** → near-zero-norm vectors blow up (**~1e13**).
  *"Input-dependent, so it hides at small seq len and surfaces at large."* Replace with explicit
  `x*rsqrt(mean(x²)+eps)` (RMS) or `x*rsqrt(sum(x²)+eps)` (L2).
- **Constant-folding sin/cos of LARGE args is low-precision** — *"cos collapses to ~0.5"*. If a
  positional embed is computed in-graph from a *constant* (fixed Sobol/grid → sin/cos of arg
  ~1e5) it folds wrong. Precompute in torch and bake as
  `register_buffer(..., persistent=False)`. Runtime/input-driven sin/cos is fine.
- **No-op `squeeze(dim)` aborts the converter**: `x.squeeze(1)` is a torch no-op when dim 1 ≠ 1,
  but coreai-torch lowers `squeeze(dim)` to a **hard shrink** and aborts
  (`dimension to be shrunk must have size 1, got N`). Guard: `if x.shape[1]==1: x = x.squeeze(1)`.
- **`prog.optimize()` can hang** on big attention graphs (TripoSplat DiT: 24 blocks × ~12 k-token
  attention → **> 90 min, ~64 GB RAM**) while the conversion itself is ~7 s. Skip with
  `convert(..., optimize=False)` then gate with a manual `run()` (note `verify()` **forces**
  `optimize=True`). On-device AOT `coreai-build` optimizes anyway.
- **Bisect divergence at TRUE scale** — *"the eps and constant-fold bugs above are emergent at
  scale and invisible in small-L probes."*
- **fp16 conversion**: keep RoPE `inv_freq` a plain **fp32 attribute (NOT a buffer)** so `.half()`
  can't underflow the small frequencies to zero. Cast RoPE cos/sin to the query dtype.
- **T5-XXL (and T5-family) encoders OVERFLOW in fp16** → washed-out generative output even though
  the bundle converts. Use **bf16** (same exponent range as fp32, still half size) or fp32; other
  nets (DiT/VAE) are fp16-clean. (LTX-Video text encoder.)

**The two opposite quantization-gating failure modes** (`:68-84`) — excellent guide material:

| | int8 | fp16 |
|---|---|---|
| Symptom | per-net **cos 0.9998** yet output visibly wrong | per-net CPU **cos ~0.9** yet output perfect |
| Mechanism | quant error in conditioning/decoder **compounds through a 20-step sampler** (TripoSplat splats desaturate: RGB std 0.275 → 0.172, *"colors collapse to gray"*) | forcing fp16 **compute** overflows attention/softmax/layernorm **on CPU**; on GPU e2e is identical to fp32 (GPU runs fp32 bundles at fp16 compute anyway) |
| Correct gate | **VISUAL end-to-end output, not cosine** | **GPU / visual, not CPU cos** |

Also: *"on GPU int8 is **NOT faster** (weights dequant to fp16 for compute) — the win is
size/memory + fitting on ANE/iPhone, not speed."* (Contrast with the MoE `gather_qmm` result
above, where low-bit *is* faster precisely because the custom kernel avoids the dequant-everything
path.)

**Gating a stochastic diffusion/sampler port** (`:98-102`): end-to-end pixel cosine vs a reference
is dominated by **sampler variance, not conversion error** — *"two legit torch runs (MPS vs CPU,
same seed) differ at cos ≈ 0.93."* Gate by **per-step net cos** (capture the real rollout inputs
from a torch run, feed the bundle, compare each step → expect 1.000000) **plus** a visual check.
LTX-Video DiT: 8/8 steps cos 1.000000 while e2e pixel cos is 0.93 — *"identical to torch-vs-torch
device variance."*

#### Four platform bugs found by the RF-DETR port (all model-agnostic)

`conversion-guide.md:110-147`. *"all four bite ANY model, not just detection — detection
transformers just happen to use the trigger ops."*

1. **`aten.arange` with float start/end/step aborts the converter** — C++ `bad_optional_access`,
   **no Python error**. `torch.arange(8.0)` fails; `torch.arange(8)` is fine — *"the **dtype**
   doesn't matter, the **argument types** do."* DETR-class models hit it via
   `gen_sineembed_for_position(…, d_model / 2)`. Fix: precompute `dim_t` as a Python-list constant.
2. **int64-comparison bool chains clobber unrelated live buffers at runtime.** A chain like
   `((ix0 >= 0) & (ix0 < W)).to(float)` on `.long()` tensors makes *a different, still-live fp
   tensor* (two ops upstream, **even a graph OUTPUT**) read back garbage/NaN once the subgraph
   executes. *"Deterministic, unit-independent (CPU too); `clone()` / `contiguous()` barriers do
   NOT protect the victim; skipping `optimize()` doesn't either."* Diagnosis pattern: *"a tensor
   is provably computed right (its other consumer is exact) but reads wrong later → buffer-
   liveness bug, hunt the comparison chain."* Fix: compute 0/1 masks in **float** arithmetic —
   `1 - (x - x.clamp(lo, hi)).abs().clamp(max=1)` is exact on integer-valued floats.
3. **`aten.floor` / `trunc` / `ceil` lower to IDENTITY on the GPU delegate** (CPU correct;
   `round` rounds ties **away-from-zero** instead of to-even). Two natural workarounds also fail:
   `div(x, 1, rounding_mode="floor")` simplifies to identity, and float→long→float roundtrips are
   *"cast-cancelled by the converter dropping truncation semantics (CPU too)."* The floor that
   survives: **`torch.div(x * 2.0, 2.0, rounding_mode="floor")`** — floor-div with divisor ≠ 1
   lowers correctly, and ×2/2 is a power-of-two scale (exact in fp).
4. **`torch._assert` on data-dependent comparisons breaks `torch.export` non-strict**
   (`GuardOnDataDependentSymNode`, torch 2.11) — *"ironically added by upstreams **for** export
   compatibility."* For static-shape exports, no-op `torch._assert` around the export and restore.

**Detection-gate design note**: gate detector numerics with **set-based matching** (per confident
oracle detection: same class, **IoU ≥ 0.75**, score within tolerance), not positional top-k
compare — *"DETR-family models emit near-duplicate predictions whose ranks swap under fp16/h16c
noise."* And: use **real images**, noise only as an informational probe.

#### HF Xet storage traps (publishing multi-GB bundles)

`:149-170`. **`HF_HUB_DISABLE_XET=1` does NOT bypass Xet** — `resolve/main/<file>` still
302-redirects to `cas-bridge.xethub.hf.co`, which reconstructs cold files server-side and *"can
crawl or stall (the 'stuck at a few MB' symptom)"*. **`curl -C -` (resume) HANGS the Xet bridge**
(the `Range:` header stalls it — 0 bytes forever); a plain GET streams fine (13 MB/s measured).
Best for a flaky link: **`HF_XET_HIGH_PERFORMANCE=1 hf download <repo>`** — parallel chunks and
**resume at chunk granularity**. *"Don't mix Xet and non-Xet attempts for the same file"* — the
cache snapshot symlink can point at a **sparse, incomplete** blob (apparent size right, `du` small).
Upload: `hf upload-large-folder <repo> . --repo-type=model` is resumable.

#### Device-integration traps (added 2026-07-14, from RF-DETR device work)

`:173-186`:
- **`.aimodel` directories cannot be embedded in an app bundle** — *"the installer misreads the
  extension-suffixed root dir as a nested bundle → 'invalid bundle'."* Ship via download or
  sideload to Documents.
- **Never name a folder `Resources/` at the iOS bundle root** — CodeSign fails with *"code object
  is not signed at all (embedded.mobileprovision)"*.
- **Benchmark only at `thermalState == .nominal`**: *"a day of device use silently degrades a
  **25 ms** model to **58–103 ms** (thermal saturation, not your app)."* Record thermal/lowPower
  alongside stats; cool down between runs. **← a 2.3–4.1× measurement swing from thermals alone.**
- **ANE status for CV (iOS 27 beta)**: *"CV graphs silently fall back to GPU even with an ANE
  preference and a pure-ViT split backbone (fingerprint-identical outputs, zero ANE-compile
  wait)."* GPU monolith is the fastest deployment.

### 5.5 `compression.md` + `compression-reference.md`

`compression.md` is short (48 lines) and its TL;DR is the zoo's whole quantization stance:

> **For LLM decoders: int8 k-means palettization is the floor that stays exact when applied
> across the whole transformer; whole-model int4 degrades. SELECTIVE 4-bit works: k-means int4 on
> the **FFN + lm_head only** (attention/embeddings kept ≥ int8/fp16) measured top-1 exact and is
> the shipping iPhone-GPU config (via custom fused kernels).**

Details (`compression.md:9-25`):
- Across **Gemma 4 E2B and Qwen3.5**, *"linear int4 and k-means int4 **both** flip next-token
  argmax vs the HF reference; **int8 k-means palettization reproduces HF top-1 exactly** at ~half
  the fp16 size."*
- *"k-means fits a per-group lookup table to the actual weight clusters → tracks non-uniform
  weight distributions far better than symmetric per-block int4 at the same bit width."*
- *"**Finer groups are the main int4 lever** (group32 → group8 helps), but still don't reach
  exact. Per-channel scale is marginal or harmful."*
- **For Gemma 4 the gate/up MLP projections must be int8** for exactness — *"keeping them at
  4-bit caps accuracy regardless of other layers."*
- k-means palettizes **`F.linear`/`F.conv` weights only**, so RMSNorm/RoPE params stay full
  precision automatically.
- **Recommended LLM recipe**: *"int8 k-means, group 32, all projections; keep tied `lm_head` +
  1-D conv (SSM) full precision."*

> ⚠️ Note the tension with §5.3's ZAYA/LFM result, which found **`sym8` (symmetric LINEAR int8,
> per-K-block-32) CLEAN and k-means int8 lossier** for top-k ≥ 4 MoE experts. The archive holds
> both, at different dates and for different tensor roles (dense projections vs MoE experts).
> **A guide must not flatten these into one rule.** The defensible synthesis from this corpus:
> *int8 is the safe floor everywhere; **which** int8 (k-means vs symmetric-linear-block32) is
> tensor-role- and routing-dependent and must be gated per model.*

**Sizes recorded**: Gemma 4 E2B core **7.0 GB fp32 → 3.5 GB fp16 → 1.9 GB int8**;
Qwen3.5-0.8B **969 MB**; Qwen3.5-2B **2.2 GB** (fp16 embed + int8 transformer, single bundle).

**Palettization × stateful export composes** (`:27-33`) — but with an ordering requirement:
*"read the export spec (reference inputs / dynamic shapes / state names) from the ORIGINAL model
first (**the finalized palettized model loses that method**), palettize, then drive
`export_to_coreai` with that spec."* Verified top-1-exact for Gemma 4 (dual-KV) and Qwen3.5
(hybrid 4-state).

**Embedding tables** (`:35-42`): Gemma 4's per-layer table is **9.4 GB fp32**. The decode core
keeps these tables **out** of the graph (gathered on a front-end); the front-end gather table
compresses with **plain int8 per-row dequant-gather** (`q_table[ids].to(fp16) * scale[ids]`) —
*"k-means is `F.linear`-only so it doesn't apply to a gather, and the iOS palettized-embedding
custom op doesn't lower on macOS. **int4 gather has no clean path today; int8 is the practical
floor** for embedding gather too."*

#### `compression-reference.md` — the `coreai-opt` API surface

Where it plugs in (`:9-12`):
```
PyTorch model → coreai-opt (compress) → finalize() → torch.export(run_decompositions(get_decomp_table()))
              → cast_to_16_bit_precision → coreai_torch.TorchConverter → .optimize() → save_asset() → .aimodel
```
Lifecycle: `Quantizer/KMeansPalettizer(model, config)` → `prepare(example_inputs)` → optional
`calibration_mode()` / `training_mode()` (QAT) → `finalize(backend=ExportBackend.CoreAI)`.
*"Every compressor output is itself a PyTorch model."*

**Quantization** (`:17-33`):
- dtypes **INT2/4/8** (signed + unsigned), **FP4_E2M1**, **FP8_E4M3FN / E5M2** (*"limited Core AI
  support"*).
- granularity per-tensor / per-channel (axis 0) / **per-block** (`block_size`, e.g. 32 along
  in-features).
- ⚠️ **A hard beta bug**: *"per-channel (axis-0) int8 Linear weights are **broken on the
  macOS-27-beta MPSGraph GPU delegate** — torch-level numerics are clean but the lowered matmul
  returns **garbage** (minimal head-only repro 2026-06-11, multiple shapes, sym and clipping
  alike); use per-block-32 there."*
- scheme: *"At int8 the gap [sym vs asym] is small (~1.5 dB); at int4 asymmetric gains **+3–5 dB**,
  and `symmetric_with_clipping` can add **+7 dB**."*
- workflows: data-free weight-only PTQ (seconds; good ≥ 8-bit, sometimes 4–6) → calibration
  (≈ 128 samples, needed for activation ranges) → **QAT (full training; the only way to recover
  ≤ 4-bit)**.
- modes: **graph** (torchao PT2E, default; needs a `torch.export`-able model; best for
  weight+activation) vs **eager** (`__torch_function__`; weight-only, or when graph fails;
  supports dynamic control flow).
- config precedence **name > type > global**. No-arg default = **W_INT8_A_INT8**. Presets
  `.w8()`, `.w4()` (int4 per-block 32); `.without(nn.LayerNorm, "model.lm_head")` to skip.

**Palettization** (`:35-43`):
- `n_bits ∈ {1,2,3,4,6,8}`, LUT = `2^n_bits` centroids.
- **scalar** (1-D k-means, default) vs **vector** (`cluster_dim>1`; effective bpw =
  `n_bits/cluster_dim`).
- *"**Per-channel (group_size=1) basically always wins**; at per-channel, k-means beats
  quantization by **~15–19 dB** at both 8-bit and 4-bit. Per-tensor palettization can be *worse*
  than per-channel quantization."*
- **`lut_qspec`**: quantize the LUT centroids to int8 → enables W_INT8-A_INT8 execution
  (*"a fp LUT forces fp ops"*).
- **sensitivity-based k-means (SqueezeLLM)**: cluster by per-weight importance from calibration
  gradients.
- **vector k-means is non-deterministic** — seed numpy + torch before each `prepare()` (and
  `num_workers=1`).

**Mixed precision & joint** (`:45-51`): per-layer bit-widths from a layer-sensitivity sweep
(compress one layer at a time, score by PSNR), then walk least-loss-first to a target average
bitwidth. **Joint**: palettize weights **first** (with int8 `lut_qspec`), *then* quantize
activations on the palettized model — **finalizable to the Core AI backend only**.

**Pitfalls** (`:65-69`), all sharp:
- **Silent skips**: *"per-block quant / per-grouped-channel palettization silently skip layers
  whose dim isn't divisible by the block/group → those layers stay uncompressed. **Check
  divisibility before trusting a size.**"*
- **Boundary layers** (first/last) are high-error — *"skipping them can add up to **+9 dB**;
  always ablate."*
- graph-mode export fails on dynamic control flow → fall back to eager for weight-only.

**Size formula** (`:72-79`) — useful for a guide's sizing section:
```
weight/index bytes = numel * n_bits/8
scale bytes        = n_groups * 2 (fp16)
zero_point bytes   = n_groups * n_bits/8      # asymmetric only
lut bytes          = 2^n_bits * n_luts * 2    # palettization
avg_bitwidth       = Σ(numel_i * bits_i) / Σ numel_i
```

**The LM-head / embedding lever** (`:53-63`): the head is `vocab × hidden` (e.g.
**262 144 × 1536** for Gemma 4) — *"largest single tensor, high sensitivity, needs **per-row
(per-output-channel)** scales for matmul efficiency."* And the closing implication:
*"an int4 head needs a **kernel** path, not coreai-opt's `F.linear` quantizer."*

### 5.6 `custom-metal-kernels.md` — the GPU speed lever

Attributed to **WWDC 325** plus `coreai-torch/docs/guides/custom-metal-kernels.ipynb`,
`coreai-torch/coreai_torch/_torch_metal_kernel.py`, `coreai/authoring/metal.py`.

**What it is** (`:11-14`): *"A custom Metal kernel lets you write a raw MSL GPU function, wrap it
with a PyTorch reference, and have `torch.export` + `coreai-torch` embed it into the `.aimodel` as
a real Core AI op (`coreai.metal4_kernel`). It is **not a raw-Metal bypass** — the MSL travels
inside the single `.aimodel` artifact and runs in the OS Core AI runtime."*
Quoted WWDC 325: *"You can take a group of these ops and fuse them into a single operation. This
replaces several steps with a single kernel dispatch within the graph."*

**GPU-only, structurally** (`:22-24`): *"The ANE runs only fixed hardware ops (Conv/LayerNorm/…);
it cannot execute arbitrary MSL. So 'write fused-int8 kernels' is, by construction, a GPU strategy
— independent of any beta bug."*

**API** (`:28-45`, cited to `_torch_metal_kernel.py:44-93` / `metal.py:36-52`):

```python
TorchMetalKernel(
    name: str, input_names: list[str], result_names: list[str],
    src: str,                       # MSL BODY ONLY (signature/bindings/#includes auto-generated)
    torch_defn: Callable,           # PyTorch reference — what torch.export sees, for shape inference
    metal_params: list[MetalParameter] | None = None,
    helper_src: str | None = None,
    template_dtypes: dict[str,str] | None = None,
)
MetalParameter(name: str, dtype: str, attr: str)   # e.g. ("gid","uint2","thread_position_in_grid")
```
Called inside an `nn.Module` with per-call dispatch and output shapes:
```python
out = kernel(*args, threads_per_grid=(N,1,1),
             threads_per_thread_group=(T,1,1), result_shapes=[list(out_shape)])
```
*"`result_shapes` is how Core AI 'bakes in' output-shape-from-input-shape so the kernel works
under dynamic shapes."*

**Critical ordering** (`:57-67`) — register kernels **before** `add_exported_program`:
```python
converter = TorchConverter()
converter.register_custom_kernels([kernel])        # FIRST
converter.add_exported_program(ep, input_names=[...], output_names=[...])   # THEN
prog = converter.to_coreai(); prog.optimize()
```

**Constraints** (`:97-114`): Metal-backed buffers forced on all I/O (*"the GPU can't read host
memory mid-kernel"*); **≤ 31 params total** (`PARAMETER_LIMIT=31`); dtypes must be in the Metal
map (`bf16→bfloat, f16→half, f32→float, si8→int8_t, ui8→uint8_t, ui32→uint, si32→int, i1→bool`);
`template_dtypes` substitutes a placeholder in `src` with the input's Metal dtype at compile time
(one kernel, many dtypes); `torch_defn` validation is strict (every param annotated
`Tensor|int|float|bool`, no `*args/**kwargs`, param count == `len(input_names)`, concrete return
length matching `result_names`); **kernels are pure functions** — no shared state, no
execution-order dependence.

**The data-dependent-gather probe result** (`:104-110`) — the enabler for `gather_qmm`:
*"**Rank-3 buffer indexing + a DATA-DEPENDENT gather both lower + run on the GPU.** So a kernel
can take an index tensor as an INPUT and read only the rows it points at — `W[m, n, e]` with
`e = uint(IDX[slot])` reads only expert-slab `e` out of a `[E, N, M]` tensor."* Critical caveat:
*"The `torch_defn` must stay fake-traceable: express the gather as
`torch.index_select(W, 0, idx)` (shape-static), **NEVER `int(idx[i])`** (FakeTensor has no
concrete value)."* Same kernel runs on M4 Max **and** iPhone 17 Pro A19 Pro GPU.

**MoE per-slot activation gotcha** (`:111-114`): gate/up share the token `x` across routed
experts, but *"the **down** projection feeds each expert its OWN gated activation — so the
kernel's `A` must be `[k, K]` (one row per slot, `A[c, slot]`), with `x` replicated k-wide for
gate/up. Treating `A` as a single shared `[1, K]` row silently corrupts down (relative error ~1.3
= garbage)."*

**Performance patterns** (`:116-125`) — the most transferable set in the file:

1. **The win is killing dispatch overhead via fusion, not kernelizing ops.** *"Per-op
   kernelization of small ops does NOT help — measured here: **kernelizing attention q/k/v/o was
   *slower*; any single op-class ≤ 1.3 ms.** The real lever is collapsing **~28 ops/layer into 1–3
   mega-kernels** (whole-layer fusion)."*
2. **Custom int8 wins only on BIG memory-bound matmuls** (FFN, the 262 144-vocab head): a fused
   int8 dequant-LUT matvec *"beat both int8-MPSGraph and fp16-MPSGraph at int8 memory. Don't
   kernelize small projections (k/v)."*
3. **Prefer native SDPA on GPU** — *"already fused; don't hand-roll it."*
4. **A `metal4_kernel` op is a FUSION BARRIER, and its edges are materialized in the dtype/layout
   the kernel asks for.** *"A dtype cast on the boundary (e.g. `state.float()` in, `.half()` out)
   is a real `coreai.cast` op that blows the tensor up — hand large state/activation tensors
   across in their native dtype and accumulate fp32 in registers."*
5. **`blockwise_shift_scale` only fuses into the matmul when its shift is all-zero** — *"so
   symmetric int4 dequants cheaper than int8, but **asymmetric (zero-point) int4 falls off the
   fast path (~4.6× slower on device)**. A fused affine-int4 matvec factors the zero point out
   (`acc += s*(dot − z*Σx)`) to keep the fast path AND the accuracy; it beats stock-asymmetric
   **3.3× Mac / ~5× device** but only ties/+11 % int8 (nibble-unpack ALU caps it)."*
6. **A decode-step SSM scan kernel is only ~3–8 % faster than the plain torch graph** (paired
   A/B) — *"not worth the barrier + shape constraints. The SSM kernel win is **prefill** (chunked
   SSD, **13.7× on Mac**), not decode."*
7. **Measurement protocol** (`:124`), the single most reusable sentence in the archive:
   > **"Measurement protocol matters more than the kernel: pair both arms in one process,
   > interleave ≥ 8 reps, report median + spread; unpaired single-shot on a ±15 %-drift machine
   > will confirm anything."**

### 5.7 `accel-levers-survey-and-plan.md` — the four-lever roadmap (2026-07-01)

**Read this as a *plan*, not as results.** The doc says so at `:8-9`: *"**All speedups marked ⚗️
are targets/estimates** (industry numbers are cited; nothing below is zoo-device-measured yet)."*
Its Part 1 is an industry survey with external citations, so those numbers are **third-party**,
not zoo measurements — do not attribute them to Apple or to the zoo.

**Part 1 — industry survey (cited, external)**, in brief:
- *Custom GPU kernels*: FlashAttention v1→v4 (FA3 75 % Hopper util + FP8; FA4 1605 TFLOP/s on
  Blackwell, ~2.7× over Triton); PagedAttention/vLLM (2–4× serving throughput, < 4 % KV waste);
  Marlin→Machete fused dequant+GEMM (~4× FP16×INT4 at batch 16–32).
- *Hardware matmul accel*: FP8 + Transformer Engine (DeepSeek-V3 trained in FP8); **FP4
  (NVFP4/MXFP4) on Blackwell — 4× over FP8, ~7× GEMM over Hopper, ≤ 1 % accuracy drop; gpt-oss
  ships native MXFP4**.
- **Apple TensorOps / M5-A19**: *"`matmul2d` auto-dequant (int4/int8/fp8/fp4) on the neural
  accelerator. **MLX-on-M5: prefill 3.33–4.06×, decode +19–27 %.** Third-party `cider` already
  gets **1.2–1.9× prefill via INT8 TensorOps on M5**."* (cited to Apple's MLX-on-M5 research post
  and the `cider` repo — **third-party/Apple-research figures, not zoo-measured**).
- *Speculative decoding (all lossless)*: EAGLE-3 **3–5×** (4.8× on 70B code), accept 0.80–0.88,
  pretrained heads exist for Qwen3 1.7B–235B; DeepSeek MTP ~1.8 %, > 80 % accept, free at deploy;
  **n-gram / prompt-lookup — training-free, 2–4× on input-grounded tasks (RAG/code/structured),
  ~0 on free chat.**
- *Quantization*: GGUF k-quants, AWQ (*"AWQ > GPTQ is the 2026 verdict"*), FP4.
  **"HONEST NUANCE (decides a zoo bet)"** (`:48-51`): *"AWQ/GPTQ vs naive RTN at 4-bit / gs128 /
  large model is a **surprisingly small gap (< 1 pt PPL)** — AWQ's edge is at 3-/2-bit and small
  models. So 'AWQ rescues Qwen3.6 int4' is weak. **The real 4-bit-quality answers are (a) official
  QAT, (b) FP4 (E2M1)** — and Apple TensorOps natively dequants fp4 on A19 (OS27)."*

**Part 2 — the four streams**:

| Stream | Lever | Targets | Key gate / de-risk |
|---|---|---|---|
| **A** | Pure custom MSL: **absorbed-MLA cross-head staging** | GLM-4.7-Flash → DeepSeek-V2-Lite → GLM-5.x / DeepSeek-V3/V4 / Kimi / Mistral-3 | staged ≥ naive across ctx, **≥ 1.5× @ ≥ 4K**, token-match vs oracle; *"If it can't beat naive even @8K → record and stop (don't ship a non-win)."* Status: *"math proven, kernel correct-but-per-head (**0.78×**)"* i.e. currently a **regression**. |
| **B** | **TensorOps `matmul2d`** on compute-bound forwards | **LLaDA-8B dLLM** (32-layer bidirectional forward every step, no KV, **185 ms/forward**) → FLUX.2 DiT → MiniCPM-V SigLIP → ASR/Whisper encoders → Stable Audio DiT | ✅ **gate DONE 2026-07-01: LLaDA forward on A19 is matmul-bound (S-scaling 1.79×, ~80–89 % compute; S128 warm_min 385.8 ms / med 450 ms, S256 692.1 / 754 ms)** |
| **C** | **Speculative decoding** | Qwen3.6-27B dense (15.9 tok/s) and 35B-A3B | *"confirm the pipelined engine can do a verify-forward (S=K batch)"*; n-gram + vanilla draft first, then EAGLE-3 |
| **D** | **FP4-via-TensorOps + QAT-int4** | Qwen3.6, LFM2.5-8B-A1B, FLUX/LLaDA | gate on **multi-token reasoning**, per the *"Nanbeige lesson: single-token survives but reasoning craters — test long chains, not just 'Paris'"* |

**Two unresolved technical unknowns for TensorOps** (`:163-167`), useful as open questions:
(a) *"can coreai-torch compile the embedded MSL at **`-std=metal4.1`**? (blockwise scale plane
`metal::tensor_blockwise` needs `__HAVE_TENSOR_MULTIPLANE__` = 4.1; matmul2d + uniform int4 =
4.0)"*; (b) *"build `tensor`/`tensor_blockwise` operands from the auto-generated raw
buffer-pointer signature inside `helper_src`/`src`."*
Header cited: `iPhoneOS27.0.sdk/…/MetalPerformancePrimitives.framework/Headers/MPPTensorOpsMatMul2d.h`.

**OS/HW gating claim** (`:143-144`): *"int4/int8 TensorOps = **OS26 point update**; **fp4/fp8 =
OS27**."* **UNVERIFIED against Apple docs — treat as a community claim.**

**A toolchain landmine noted in passing** (`:168-169`): re-export must happen *"on a **macOS-26.4
box** (⚠️ NOT this Mac — **27 mis-converts**)."* — i.e. the author believes macOS 27 mis-converts
this particular graph. **UNVERIFIED**, cited to a private memory.

**Operational conventions** (`:133-151`) worth reusing: *"Parallel = **separate sessions, NOT
background agents** — bg agents collide on CoreAIChat, the Mac GPU, and the single A19 device"*;
a `_GPU_LOCK` file at the work root before any Mac-GPU run (**GPU SOLO**; concurrent CPU
export/quant is safe); a single A19 device (iPhone 17 Pro) is the bench; *"Bench truth =
`ondevice/PipelinedBench`, not chat UIs"*; *"**never `git add -A`** (concurrent sessions dirty the
tree)"*; *"**Don't claim a win until the bench shows one.**"*

---

## 6. Incidents — the two unique primary sources

These two files are the most valuable things in the corpus for a technical guide: they are
complete, dated, first-hand incident write-ups with symptom → isolation → diagnosis → workaround,
each cross-referenced to a real Apple Feedback / GitHub issue number.

### 6.1 The MPSGraph in-graph KV-write bug (`coreai-beta-mpsgraph-kvwrite-bug.md`)

**Filed as: Apple Feedback `FB23024751` · [`apple/coreai-models#5`](https://github.com/apple/coreai-models/issues/5)
· public repro gist by `john-rocky`.** (`:27`)

#### Symptom

On the WWDC26 betas (macOS 27 / iOS 27) the **fixed-shape / ANE decode path** — *"the one that
writes each new KV column in-graph with `slice_update` at a runtime `in_step` index (**Apple's
documented `export/ios.py` + `CoreAIStaticShapeEngine` recipe**)"* — **does not lower on the
MPSGraph backend** (`:3-11`):

| Platform | Failure |
|---|---|
| **Mac GPU** | `EXC_BREAKPOINT` / **SIGTRAP** at the first execute (process exit 133) |
| **iPhone GPU** | **SIGSEGV** at the first execute — *"the graph loads + specializes, **then** crashes"* |
| **iPhone ANE** | `MPSGraphExecutable.mm` → *"MLIR pass manager failed"* (**SIGABRT**); **corrupts the ANE compile cache** (next load = `ENOENT`) |

And the detail that makes it nasty: *"Conversion **succeeds** — it is load + execute that dies."*

#### The decisive isolation

Same attention block, same `slice_update`, same SDPA, exported three ways differing in **only the
KV-write column index** (`:19-23`):

| Write index `begin` | Shapes | Result |
|---|---|---|
| shape **symint** (`position_ids.shape[-1] − query_len`, the `update_and_fetch` path) | dynamic | **runs ✅** |
| runtime **tensor** (`in_step` scalar input) | dynamic | **SIGTRAP ✗** |
| runtime **tensor** (`in_step` scalar input) | **static** | **SIGTRAP ✗** |

> *"So it is not the mask, not static-ness, not the model — flipping the begin-index **source**
> (shape symint → runtime tensor) alone flips run → crash. Model-agnostic: every model shares the
> one `KVCache.update_and_fetch` helper."*

**This is a textbook minimal isolation and should be shown as one in any guide about debugging
on-device ML.**

#### The trap in the surviving path

`:29-31`: *"the **dynamic symint path runs but re-specializes per sequence length** (the slow path
— a new `position_ids` length recompiles, **~27 ms → ~1.9 s/step**). The fast fixed-shape path is
exactly the one that crashes."* **← a ~70× per-step penalty for taking the working path.**

#### Workaround 1 — host-cache (no in-graph indexed write)

`:33-50`. Express the KV cache as plain model **input/output** instead of a Core AI state, and
remove the indexed write entirely:
- append the new token's K/V in-graph with `torch.cat` (past ++ current);
- attend with a **masked SDPA** over the concatenated keys (valid past + current marked by an
  explicit mask);
- the **host** writes the new column back between steps (plain numpy / `[Float16]`).

*"Only MPSGraph-safe ops (masked SDPA over plain inputs + `cat`) — no state, no `slice_update`.
Numerically identical to the stateful core (**8/8 top-1 vs HF**). Runs on Mac GPU, iPhone GPU
(full model), and iPhone ANE (chunked). For the ANE, split into **≤ ~8-layer chunks** (the
35-layer monolith OOMs the first-run ANE compile)."*
Cost: *"a host round-trip per step + losing Core AI's in-place state."*

#### Workaround 2 — the **input-mask escape** (2026-06-10): stateful KV without the fix

`:52-79`. The better result. Further isolation narrowed the trigger: *"what crashes is deriving
the write position **in-graph** from runtime data. Hand the graph the position as a pre-computed
mask **input** and the numerically identical write lowers and runs."*

```python
# host builds a one-hot fp16 write_mask[ctx] per step (1.0 at the write column) — 2 KB
sl = cache[slot]                          # state, compile-time slot index
m  = write_mask.reshape(1, 1, ctx, 1)
sl.copy_(sl * (1 - m) + col * m)          # exact one-hot select; NO data-derived index anywhere
```

Five formulations isolated on the beta Mac GPU (each in its own process, multi-step state values
verified exact):

| Formulation | Result |
|---|---|
| constant-mask blend | ✅ |
| **input-mask blend** | ✅ |
| shift-append (`cache ← cat(cache[1:], col)`) | ✅ |
| input-mask blend into one slot of a packed `[n_slots,…]` state (both slot-view and whole-state forms) | ✅ |
| the same blend with the one-hot computed **in-graph** (`arange == in_step`) | **✗ crashes exactly like `slice_update`** |

**Proven at full scale**: *"a 35-layer Gemma 4 E2B static decode core with the blend write
(everything else identical to the official fixed-shape recipe) exports to int8 and runs **8/8
greedy-exact on the beta macOS GPU** — **the first fixed-shape *stateful* core that executes on
this beta at all.** You get fixed shapes (no per-step respecialization, flat memory) **and** Core
AI states (no host KV round-trip) at the cost of one tiny mask input per step."*

Honest status (`:77-79`): *"Mac GPU verified; iPhone GPU / ANE re-isolation **pending** (the crash
was platform-agnostic, the escape should be too — but the ANE's MLIR path is a different lowering,
so **verify before betting a port on it**)."*

#### The strategy note — de-confusing "the ANE wall" (`:85-101`)

Three facts that had been conflated into *"ANE is walled by a SIGSEGV, so we pivoted to GPU"*:

1. **ANE is correct, not broken**: *"gemma4 E2B ran **8/8 exact on the device ANE** once fp16
   numerics were fixed (`[x,-x]` LayerNorm trick + fp32 accumulation for Conv2d-1×1). **The
   earlier 'ANE 0/8' read was retracted.**"*
2. **ANE is speed-capped, not correctness-capped** (~6 tok/s at the time): *"a 262k-vocab head
   plus host-cache KV re-feed every step. Lifting it needs stateful KV (this very bug) + a reduced
   head + AOT."*
3. **The sound reason to standardize on GPU is that custom Metal kernels are GPU-only by
   construction** — *"the ANE runs fixed hardware ops, never hand-written MSL. If the speed lever
   is fused kernels, that is a GPU play regardless of this bug."*

Caveat kept explicitly (`:99-101`): *"on-device the GPU lead was small at measurement time
(**iPhone GPU 7.4 vs ANE 5.9 tok/s**); the big GPU numbers are Mac. Keep the ANE path alive — it
is the energy-efficient lane MLX/llama.cpp cannot touch, and it revives whenever the FB above
lifts."*

> **Guide framing:** this incident is *the* reason the community stack is GPU-first on the WWDC26
> betas, and the input-mask escape is a technique with no Apple documentation behind it.
> Attribute both clearly as community work; note the Feedback number so a reader can check whether
> it has since been fixed.

### 6.2 The coreai-torch 0.4.0 → 0.4.1 IR-location incident (`coreai-torch-041-ir-incident.md`)

Note the filename says `041` but the doc's title says **0.4.0** — the incident is *caused by*
0.4.0 and *fixed in* 0.4.1. The zoo README's recovery note also says "0.4.0 incident"
(`README.md:313`). Cite it as **the 0.4.0 IR-location incident**.

#### What happened (2026-07-18)

`:3-11`: *"Every `.aimodel` converted with `coreai-torch` **0.4.0** stops loading on **iOS/macOS
27 beta 2 and later**. It runs on beta 1."* On beta 2+, **both** `AIModel.load` **and**
`coreai-build compile` abort with:

```
error: expected AICode versioned location, got: loc(fused<...>)
error: Failed to convert to versioned IR
LLVM ERROR: cannot unwrap empty `odiec_module_t`
```

**Root cause** (Apple, [`apple/coreai-torch#37`](https://github.com/apple/coreai-torch/issues/37),
v0.4.1 release notes): *"0.4.0 baked PyTorch stack traces into the IR as MLIR `fused` locations;
the beta-2 compiler no longer parses that nested form. **It fires on deep module hierarchies.**"*

**Things that do NOT work (all verified)** (`:18-23`) — an unusually valuable negative list:
- `coreai-build package` — *"re-emits the asset (producer bumps) but leaves IR locations
  untouched; compile fails identically."*
- Pinning `coreai-core` back to `1.0.0b1` — *"the gate is OS-side, not in the wheel."*
- Re-AOT with the beta-3 toolchain — *"dies at the same op."*
- `coreai-build inspect` still reads the asset fine — ***"which makes it look recoverable. It
  isn't."***

#### Telling a broken asset from a fixed one — the producer fingerprint

`:27-36`. A 0.4.1-converted `metadata.json` carries a `producer` field; a 0.4.0 one does not:

```
0.4.1 (good):  {"producer": "coreai-core 1.0.0b2", "assetVersion": "2.0", "creationDate": ...}
0.4.0 (dead):  {"assetVersion": "2.0"}
```

*"Audit any tree by that field alone — no dates, no guessing."* Caveat: *"`.aimodelc` bundles
**always** carry a `producer` (the `coreai-build-<ver>` string), so for those use the **source**
`.aimodel`'s producer, not the compiled one."*

#### Environment the fix needs

`:40-47`: `coreai-torch` **0.4.1+**, `coreai-core` **1.0.0b2**, `coreai-opt` **0.2.1**, on pinned
**`torch==2.9.0`** — *"do NOT let `uv` bump torch to 2.11 — it breaks torchvision with a circular
import and every export dies at load."* Xcode 27 **Beta 3** (`27A5218g`) for AOT
(`xcrun coreai-build` → `3600.75.3`). Beta-2-or-earlier `.aimodelc` also need a beta-3 recompile
per Apple **181264112**, but *"that is a **separate** issue from the 0.4.0 conversion break — do
not conflate them."*

And a Python-packaging landmine (`:46-47`):
> ⚠️ **Never run python with the coreai-torch clone as cwd**: its `coreai_torch.egg-info` (0.4.0)
> shadows the installed 0.4.1 via `sys.path[0]`, so **exports silently use 0.4.0**.

#### Re-verification tool: `conversion/coreai_gate.py`

`:49-92`. *"Loading is necessary but not sufficient — a bundle must still **speak**."* The gate
drives the exported bundle through the Core AI engine and compares its **greedy decode,
token-for-token, against the overlay model run in fp32** (the "16/16 oracle" the cards publish).
It checks the **conversion** — *"unlike the eager numerics gates, which check the quant recipe and
pass regardless of converter version."*

```
python3 conversion/coreai_gate.py <bundle-dir> <hf-id> [--arch KEY] [-n 16]
```

PASS = token-for-token match, **or a first divergence only at a top-2 margin < 0.1** (*"a
knife-edge tie, fp16 class"*). Use a **deterministic** prompt (*"The capital of France is"*);
*"open-ended prompts hit ties everywhere and aren't gate material."*

- **Large models: `--oracle-dtype fp16`** — *"The fp32 oracle materialises all weights in fp32 — a
  35B is ~140 GB and won't fit (**27B at ~108 GB was the largest that fit 137 GB RAM**). fp16 is
  the export's own trace dtype, so an fp16 oracle is still a valid conversion check."*
- **MoE + custom-Metal-kernel bundles gate fine** on OS 27 beta 3 — *"the 'custom Metal kernels
  fail to load' known issue (**178056451**) did NOT fire for them."*

**"Non-obvious things the gate encodes (documented nowhere else)"** (`:73-84`) — verbatim value:
- Engine launch needs **`COREAI_CHUNK_THRESHOLD=1` + `--inference-engine-variant coreai-pipelined`
  + `--warmup off`**. *"The default warmup does a synthetic 256-token prefill that a static-`S=1`
  decode graph can't serve (`Shape at dimension 1 of 256 is not a valid substitution for source
  shape 1`)."*
- **`llm-runner --inference-engine-variant` help text is STALE**; the real values are
  `auto / coreai-sequential / coreai-pipelined / static-shape`.
- *"The fp32 oracle steps `S=1` but **`position_ids` carries the full `0..t` range each step**
  (dynamic full-length positions); a single position yields plausible-looking garbage."*
- *"The oracle must stop at EOS and step only after the prompt is consumed (`t >= len(prompt)-1`),
  else it emits prompt-position predictions."*

Per-architecture fp32 reference construction (`:86-92`) — recorded in `coreai_gate.py`'s `ARCH`
map: `qwen3.5` = `Qwen3_5StatefulForCausalLM.from_hf_memory_efficient(hf_config_attr="text_config")`
with a pure-text fallback (Ornith); `lfm2_5` = `lfm2_from_hf(stateful=True)`; `granite` =
`Granite4HForCausalLMStateful.from_hf`; `youtu` =
`YoutuAbsorbedStatefulForCausalLM.from_causal_lm(youtu_absorbed_from_hf(...))` (states
`kv_a`/`kv_b`); `nanbeige` = plain-Llama `LlamaForCausalLM` (KV cache only). Aliases:
`ornith`, `qwen3_6` → `qwen3.5`.

#### Recovery loop, per model (`:94-108`)

1. Export with 0.4.1 using the recorded ship command (`models/<model>/recipe.toml`).
2. Gate: `coreai_gate.py <bundle> <hf-id>` → PASS.
3. Upload to HF (two path renames happened: `perchan_sym` → `block32_sym`, `absorbed_msdpa` →
   `absorbed_int8_msdpa`). *"Big files (10–40 GB) need `HF_HUB_DISABLE_PROGRESS_BARS=1`, retries,
   and background — a flaky link kills one-shot uploads mid-file."*
4. Verify the uploaded `producer` is `coreai-core 1.0.0b2`.
5. **Re-pin `catalog.json` `revision` in coreai-kit** — *"the catalog is fetched remotely and
   revision-pinned, so **upload alone does not reach users**; the re-pin commit does."*
   ← a real distribution-architecture lesson.
6. Free disk.

#### UPDATE 2026-07-21 — the in-place fix, `strip_debug_info`

`:110-141`. Apple later shared a workaround
([`coreai-torch#44`](https://github.com/apple/coreai-torch/issues/44)): *"the broken assets are
healthy except the debug locations, and those can simply be stripped."*

```python
from coreai_torch.debugging.debug_info import strip_debug_info
from coreai.authoring import AIModelAsset
asset = AIModelAsset.load(path)          # <-- fails on beta 2+ with b2 wheels, see below
strip_debug_info(asset.program)
asset.program.save_asset(out_path)
```

**Verified on 40 zoo bundles: weights byte-identical, minutes per model, stripped assets load
clean on beta 3.**

**But there is a chicken-and-egg caveat** (`:126-137`) — *"on a beta 2+ machine the snippet above
cannot even load the asset (the authoring bytecode reader in coreai-core 1.0.0b2 wheels runs the
same versioned-IR conversion and aborts)."* The working recipe:

1. Isolated venv with **coreai-torch 0.4.0 + coreai-core 1.0.0b1** — *"the b1 wheel's bundled MLIR
   parses the old fused locations fine."* And an explicit self-correction:
   > *"The earlier 'pinning coreai-core back to 1.0.0b1 does not help, the gate is OS-side'
   > finding in this doc was about the **RUNTIME load** path; for the **AUTHORING parse** the gate
   > is in the wheel, not the OS."*
   **← Two different gates that look like one. Excellent nuance for a guide.**
2. `AIProgram._load_bytecode(bundle/main.mlirb)` → **vendored 0.4.1 `strip_debug_info`** (0.4.0
   lacks it; *"two helper signatures need adapting"*) → `save_asset`.
3. Re-load + re-save with the b2 wheel (now parses fine) to get a proper
   `producer: coreai-core 1.0.0b2` fingerprint, then probe + publish.

*"`.aimodelc` (compiled) artifacts **cannot** be stripped — those need re-export + AOT
recompile."*

#### Blast radius, from the README (`README.md:313-322`)

Every affected model was re-published — re-converted with 0.4.1 (gates re-run) or repaired in
place with `strip_debug_info`. *"Catalog-served apps just re-download."* One casualty was
permanent: **FastContext-1.0-4B was retired instead of recovered, because "Microsoft removed its
upstream weights on 2026-06-30, so it cannot be rebuilt."*
**← A concrete, dated instance of upstream-weight disappearance breaking reproducibility. Very
citable for a "reproducibility of on-device ML" guide.**

---

## 7. Benchmarks (knowledge/ Tier 2)

> ⚠️ Everything in §7 is **community-measured** by the zoo author on his own hardware unless
> stated otherwise. Numbers are on **iOS 27 / macOS 27 BETAS** and will move. Where the source
> does not state the hardware or OS build, that is flagged.

### 7.1 `coreai-vs-mlx-speed.md` — the head-to-head database

**Protocol (stated, `:4-7`)**: *"All LLM rows are **same M4 Max, same protocol** as `mlx-lm
benchmark` (Apple's `llm-benchmark` is explicitly modeled on it): **512 prompt / 1024 generation /
5 trials, release build**. MLX side = **`mlx-lm 0.31.3`, `mlx-community` 4-bit**."*
Note the asymmetry the doc itself calls out: **Core AI ships int8, MLX ships 4-bit** — so this is
not an iso-precision comparison, it is a ship-config comparison.

#### The database — decode tok/s, M4 Max

| # | Model | Arch class | Core AI | MLX | CA/MLX | Winner | Engine path | Dominant factor |
|---|---|---|---:|---:|---:|---|---|---|
| 1 | qwen3-0.6b | dense | **484** | 432 | 1.12 | **CA +12 %** | pipelined | dispatch-bound, not BW-bound → MLX's 4-bit edge doesn't cash in |
| 2 | qwen3-4b | dense | 145.4 | 145.8 | 1.00 | tie | pipelined | — |
| 3 | qwen3-8b | dense | **94.1** | 90.0 | 1.05 | **CA +5 %** | pipelined | — |
| 4 | gemma3-4b-it | dense | **141.5** | 136.3 | 1.04 | **CA +4 %** | pipelined | — |
| 5 | gemma3-12b-it | dense | 55.0 | 55.1 | 1.00 | tie | pipelined | biggest dense → BW starts to matter → MLX 4-bit pulls even |
| 6 | mistral-7b-v0.3 | dense | **101.7** | 97.5 | 1.04 | **CA +4 %** | pipelined | — |
| 7 | gpt-oss-20b | **MoE** | 78.1 | **100.2** | 0.78 | **MLX +28 %** | pipelined, stock `GatherMM` | **`GatherMM` reads ALL experts/token (over-read-bound)** |
| 8 | Qwen3.6-35B-A3B | MoE (256e / top-8) | 30.9 | ~55–70 | ~0.5 | MLX | stock `GatherMM` | **32× expert over-read** |
| 8b | Qwen3.6-35B-A3B | MoE + **`gather_qmm` kernel** | **64.9** | ~55–70 | ~1.0 | **tie/CA** | custom Metal `sym8` gather | kernel reads only routed experts → gap closes |
| 9 | LFM2.5-8B-A1B | MoE (32e / top-4) | 39 → **141** | — | — | (3.6× self) | stock → `gather_qmm` | same over-read fix |
| 10 | GLM-4.7-Flash | **MoE + MLA** | 20.3 → **52.4** | — | — | (2.6× self) | stock → `gather_qmm` | MoE fixed by kernel; **MLA on all 47 layers keeps it < qwen3.6** |
| 11 | Qwen3-Coder-Next-80B-A3B | MoE (512e) | ~24 | "MLX-competitive" | ~1.0 | tie | `gather_qmm` | BW-bound on 79 GB cold weight, not GDN |
| 12 | Qwen3-ASR-1.7B (audio) | dense decoder, **ANE** | WhisperKit-ANE | **MLX 2.6×** | — | **MLX** | ANE (CoreML) | *"ANE = energy-not-speed; MLX-GPU wins raw tok/s + WER (1.52 vs 1.71)"* |

#### The one-line answer (`:31-43`)

> **The difference is operator/architecture coverage on the engine — NOT the core engine.**
> On standard **dense** transformers Core AI's pipelined engine ties or beats MLX. Core AI only
> loses where the model uses an op-class the stock engine lowers *naively*.

And the historical correction (`:47-50`) — **important, because the "MLX is 2× faster" folklore
came from a bad baseline**:

> The historical "MLX is ~2× faster, structural" verdict was measured on a **hand-rolled per-token
> `fn.run()` loop** (~11 % of BW peak, ~1000 Metal dispatches/token). That was the *loop's*
> ceiling, not Core AI's. Apple's **`coreai-pipelined` engine** runs the same weights **~3.5×
> faster (qwen3.5 58.5 → 204 tok/s, ~2× MLX)** with zero custom kernels.

#### Factor decomposition (`:52-58`)

| Factor | Size | Helps MLX when… |
|---|---|---|
| **Kernel coverage / dispatch** | ~2× | the model has uncovered op-classes (MoE gather, MLA) |
| **Quantization byte-class** | ~1.5–2× | **bandwidth-bound** (big models, long ctx). MLX = 4-bit affine g64; CA ships int8 |
| **Host / framework / OS-runtime tax** | ~1.3× | always — *"the irreducible ~15–25 % you don't own"* |

#### The predictive decision rule (`:60-81`)

1. **Dense + pipelined engine** → Core AI ≥ MLX. *"The smaller / less BW-bound the model, the
   bigger Core AI's win (0.6b +12 %); the bigger the model, the more MLX's 4-bit erases it
   (12b tie)."*
2. **MoE** → Core AI loses on stock lowering, reaches **parity** with a custom gather kernel, but
   *"does **not** beat MLX — MLX's sparse dispatch is already good."*
3. **MLA / exotic attention** → Core AI loses; *"the structural kernel (absorbed-MLA latent
   staging) is unsolved."*
4. **ANE / iPhone** → *"not a raw-tok/s contest"* — and now measured.

#### The ANE-vs-GPU-vs-MLX iPhone measurement (the most decision-relevant table in the corpus)

`:68-77`. **iPhone 17 Pro, DeepSeek-R1-1.5B, matched 4-bit bytes (ANE 0.97 / GPU 0.95 / MLX
0.95 GB), cold short-chat, median-of-3.** Source cited as
`litertlm-convert/reports/coreai-ane-gpu-parity-addendum.md` (**not in this repo** — UNVERIFIED at
source).

| Path | Decode tok/s | Energy (tokens per 1 % battery) |
|---|---:|---:|
| **Core AI ANE** | **83.3** | **6 144** |
| **MLX (GPU, mlx-swift)** | 73.0 | 5 662 |
| **Core AI GPU** | 75.9 | 4 506 |

Interpretation, verbatim: *"The ANE-vs-GPU delta **sign-flips across sibling models** →
**throughput parity**, not an ANE speed win. And the ANE *energy* edge over MLX-GPU is only
**~+8.5 %** (it's +36 % over CA's own GPU — MLX's GPU path is energy-efficient); the robust ANE
win is **GPU exclusivity** (UI/rendering don't contend)."*

Two explicit self-corrections in the same paragraph:
- *"MLX **DOES** run on iPhone (GPU, via mlx-swift) — correction 2026-07-24: an earlier note here
  claimed it 'can't run on ANE/iPhone at all'; only the ANE is closed to MLX."*
- *"(Foundation Models integration is **NOT** an exclusive: **the `LanguageModel` protocol is
  public and MLX plugs in via `MLXLanguageModel`** — see `fm-provider.md`; CA's edge is only the
  official zero-code adapter.)"*

#### §5 "Audited non-speed differentials" (2026-07-24) — the most contrarian section

`:97-138`. The author re-checked his own earlier marketing-shaped claims against artifacts.
**Net: *"the technical differential for LLM execution is thin; most of the advertised deployment
gap was illusory."***

**5.1 "OS-resident runtime / nothing to bundle" — HALF-FALSE.** *"Only the **graph compiler +
executor** (`CoreAI.framework`) is OS-resident. The LLM runtime — `EngineFactory`, the
`coreai-pipelined` engine, `LanguageBundle`, on-GPU sampling, KV growth — is Swift code from
`coreai-models` that **you compile into the app** (proof: we patch it —
`apps/coreai-pipelined-extra-states.patch`; **you can't patch an OS framework**)."* And the
double edge: *"beta seed-to-seed ABI churn kills TestFlight launches (**`FoundationModels` must be
weak-linked**); the OS reclaims model assets into **6-byte zeroed stubs**; the **~O(p²) prefill
scratch lives in the closed compiler and cannot be fixed app-side**. 'The OS owns it' = 'you can't
repair it.'"*
**← Three separate, concrete, citable OS-residency hazards. The `FoundationModels` weak-linking
one is directly relevant to any FM guide.**

**5.2 AOT startup control — real, but mostly self-remediation.** *"Cold GPU specialization is Core
AI's own cost (**0.8B ≈ 4.8 s, 2.3 GB ≈ 29 s on iPhone**); AOT / `AIModelCache` gives *control
over* that first-run cost; MLX's runtime kernel JIT is light enough that it never had the problem.
Deterministic first-launch is a genuine product knob, but don't sell it as an advantage over MLX."*

**5.3 Reverse differential — logits / guided generation favour MLX.** *"FM guided generation
(`@Generable`) needs engine logits, and the GPU-pipelined fast path **does not expose logits**.
MLX exposes logits trivially → structured generation, logprobs tooling, and sampler experiments
are *easier* on MLX than on Core AI's fast path."*
**← Repeat of the §5.1 finding, and the single most guide-relevant FM constraint in the corpus.**

**5.4 What each side genuinely keeps** —
*Core AI*: ANE access (throughput parity, ~+8.5 % energy vs MLX-GPU, **GPU exclusivity** — *"the
one structural fact MLX can never reach"*); AOT first-launch control; official zero-code FM
adapter; a closed compiler that improves with OS updates (double-edged).
*MLX*: fully-OSS stack (every layer fixable); **no conversion step → new-arch turnaround in days**;
mature 4-bit affine quant; free logits; **no O(p²) prefill-scratch wall.**

#### Porting decision takeaways (`:83-95`)

- Dense → expect tie-or-win vs MLX **for free** on the pipelined engine.
- MoE → **budget a `gather_qmm` custom Metal kernel up front**, or ship at ~0.5–0.78× MLX. With
  the kernel you reach **parity (the ceiling), not a win**.
- MLA → *"parity/win is not currently reachable; ship for coverage/quality, not speed."*
- *"Optimize for [ANE exclusivity / AOT control / ecosystem positioning] — **not** for beating MLX
  on tok/s."*

> **[COMPLICATES APPLE]** — Apple's WWDC framing of Core AI centres on convert-once/run-anywhere
> and OS-resident efficiency. This community audit finds (a) the LLM runtime is *app-compiled*,
> not OS-resident; (b) a documented `O(p²)` prefill-scratch limitation *inside the closed
> compiler*; (c) the flagship FM feature `@Generable` unavailable on the fastest engine path. None
> of these contradict a specific Apple statement I read this session, but they materially
> complicate the marketing story and should be presented with that caveat and with the
> community-source attribution.

### 7.2 `apple-models-bench.md` — "the README Apple didn't write"

Premise (`:3-7`): *"Apple's `coreai-models` repo ships **21 export recipes** but publishes **zero
performance numbers and zero sample apps**. This page is the missing table: every model exported
with **Apple's official recipe, unmodified**, and measured with **Apple's official runners**
(`llm-benchmark` / `llm-runner`) on real hardware."*
**This is the most directly citable file in the corpus, because it measures Apple's own artifacts
with Apple's own tools.**

**Hardware/method** (`:9-15`): MacBook Pro **M4 Max 128 GB (macOS 27 beta)** · **iPhone 17 Pro
(iOS 27 beta)**. `llm-benchmark` defaults — **512 prompt / 1024 generation / 5 trials, release
build**. Load times from `llm-runner`'s "Model Load" line. Memory = peak physical footprint
(`/usr/bin/time -l`). Cold = first run after export (includes on-device specialization).

#### LLMs — macOS, M4 Max 128 GB

| Model | Recipe (registry preset) | Artifact | Prompt tok/s | Gen tok/s | Load (warm) | Peak mem |
|---|---|---|---:|---:|---|---|
| gpt-oss-20b (MoE) | `none` / bf16 / ctx 32768 (MXFP4 kept) | 13 GB | **1252** | **78.1** | 2.1 s (cold 13.2 s) | 33.9 GB RSS |
| qwen3-0.6b | `4bit` / fp16 / ctx 8192 | 335 MB | 9396 | **484** (558 short-ctx) | 0.10 s (cold 0.85 s) | 0.77 GB RSS |
| qwen3-4b | `4bit` / fp16 / ctx 40960 | 2.1 GB | 1635 | 145.4 (164 short-ctx) | 0.36 s (cold 1.95 s) | 4.6 GB RSS |
| qwen3-8b | `4bit` / fp16 / ctx 40960 | 4.3 GB | 912 | 94.1 (102 short-ctx) | 0.64 s (cold 2.92 s) | 9.3 GB RSS |
| gemma3-4b-it | `4bit` / bf16 / ctx 131072 | 2.1 GB | 1669 | 141.5 (157 short-ctx) | 0.32 s (cold 2.20 s) | 4.5 GB RSS |
| gemma3-12b-it | `4bit` / bf16 / ctx 131072 | 6.2 GB | 578 | 55.0 (59 short-ctx) | **5.4–7.7 s (variance across runs)** | 13.4 GB RSS |
| mistral-7b-instruct-v0.3 | `4bit` / fp16 / ctx 8192 | 3.8 GB | 976 | 101.7 (109 short-ctx) | 0.56 s (cold 2.49 s) | 8.3 GB RSS |

Note the **short-ctx vs 512p/1024g gap** in every row (e.g. qwen3-0.6b 484 vs 558): decode is
context-dependent, so a headline tok/s without a stated protocol is meaningless.

#### LLMs — iPhone 17 Pro (iOS 27 beta)

Preconditions stated (`:31-42`): only Qwen has iOS presets; iOS execution **requires AOT**
(`--platform iOS --preferred-compute <unit> --architecture h18p`), *"then point `metadata.json`
`assets.main` at the `.aimodelc` — an uncompiled `.aimodel` fails at engine load with
`NSPOSIXErrorDomain Code=2`."* Same 512p/1024g/5 protocol — *"note this carries a much deeper KV
than 'short-chat' benchmarks elsewhere; **numbers are NOT comparable across protocols**."*
And: *"the drop on run 2 is **thermal**, not cache state."*

| Variant | Source export | Prompt tok/s | Gen tok/s (run 1 / run 2) | Load cold / warm | Footprint |
|---|---|---:|---|---|---|
| qwen3-0.6b **ANE** (official iOS preset) | mixed 4/8-bit static, ctx 4096 | 5 325 | **69.6 / 54.1** | 2.85 s / **0.045 s** | 1.1 GB |
| qwen3-0.6b **GPU** (macOS dynamic compiled for iOS) | `4bit` dynamic (**macOS-27β artifact**) | 1 519 | 57.2 / 52.5 | 1.14 s / 0.07 s | 0.47 GB |
| qwen3-0.6b GPU — **macOS-26 artifact** | same recipe, 26-era export | **5 807** | **115.1 / 90.4** | 0.90 s / 0.066 s | **0.22 GB** |
| qwen3-4b **ANE** (official iOS preset) | mixed 4/8-bit static, ctx 4096 | 546 / 462 | 13.2 / 12.2 | **194 s** / 0.46 s | 3.3 GB |

**Two findings of the first order here:**

1. **The macOS-26 vs macOS-27β lowering A/B — same recipe, same code, same wheels, ~2× decode /
   3.8× prefill / half the memory difference on the identical device.** (`:48`,
   *"the lowering A/B on device"*.) And restated in the gotchas (`:196-200`):
   > **"An `.aimodel` is a build artifact, not a pure function of the recipe"**: the same
   > `coreai.llm.export qwen3-0.6b` produced a **2.2× faster artifact on macOS 26 than on the
   > 27 beta** (**native quantized-Linear lowering vs explicit dequant ops**; same code, same
   > wheels). … **Version-stamp and keep your artifacts.**

   **[COMPLICATES APPLE]** — this is a *regression in the beta toolchain*, community-measured,
   with the mechanism identified (loss of native quantized-Linear lowering). It is also the reason
   the accel plan says re-export must happen on a macOS-26.4 box (§5.7). Attribute carefully;
   flag that betas move.
2. **qwen3-4b ANE cold load = 194 s** (3 GB `.aimodelc`, *"cold on-device specialization takes
   ~3 min"*), warm 0.46 s. That is the specialization tax made concrete.

Protocol cross-check the author performed (`:51-54`): the macOS-26 GPU artifact at short-chat
scale (**128p/128g**, engine-warm) gives **184–190 tok/s** (median of 5 = 184; *"later trials drop
to ~125 thermally"*) versus **115** at 512p/1024g. *"Protocols matter: the same artifact measures
115 (512p/1024g) and ~184 (128p/128g)."* **← a 1.6× swing from protocol alone; essential caveat
for any tok/s comparison.**

#### Vision — GPU vs ANE vs CPU, M4 Max

Method (`:58-63`): load each **official** `.aimodel` with
`SpecializationOptions.from_preferred_compute_unit_kind(<unit>)` (Python runtime), synthetic
inputs from the function descriptors, **3 warmup + 20 timed runs, median single-inference
latency**. *"'Preferred' means the runtime may still place unsupported ops elsewhere."*

| Model | Recipe | Artifact | GPU | ANE | CPU | Winner |
|---|---|---|---:|---:|---:|---|
| clip-vit-base-patch32 | fp32 static (image+text joint) | 577 MB | 6.54 ms | **5.43 ms** | 18.76 ms | ANE |
| clip-vit-base-patch32 | **fp16** (`--dtype float16`) | 289 MB | 6.31 ms | **3.68 ms** | — | **ANE, 1.7× over GPU** |
| yolos-base | fp32 static | 488 MB | **444.8 ms** | 456.7 ms | 733.7 ms | GPU (≈ tie) |
| sam3 | fp32 static (promptable, bundled tokenizer) | 3.1 GB | **559.9 ms** | 565.7 ms | 2789.7 ms | GPU (≈ tie) |
| depth-anything-3 (small) | fp32 static | 101 MB | 7.30 ms | **6.84 ms** | 34.58 ms | ANE |

**The actionable observation** (`:75-80`): *"**every official CV recipe DEFAULTS to float32**, and
at fp32 the big ViTs land in a GPU/ANE tie on M4 Max. But the scripts expose `--dtype float16`,
and fp16 is what the ANE runs natively: CLIP at fp16 drops to **3.68 ms on ANE (1.7× faster than
GPU, 1.5× faster than fp32-ANE) at half the artifact size**. If you're deploying these recipes to
ANE, **pass `--dtype float16`**."* (First ANE load of a new variant pays ~5 s one-time
specialization for CLIP.)
**← A concrete, defensible "Apple's default is not the deployment default" finding.**

iPhone 17 Pro CV table: *"(pending)"*.

#### gpt-oss-20b deep dive — "the first big-MoE numbers on Core AI"

`:108-144`. Export: ~8 min download (13.8 GB — *"only the MXFP4 shards; `original/` and `metal/`
weights are NOT fetched"*) + ~3 min convert on M4 Max. **MXFP4 weights pass through unchanged**
(`compression: null` in metadata) → 13 GB artifact.

| Metric | Value |
|---|---|
| Prefill (512 tok) | **1252 tok/s** (σ < 0.5 %) |
| Decode (1024 tok) | **78.1 tok/s** (σ < 0.1 %) |
| Cold load (first ever, incl. GPU specialization) | **13.2 s** |
| Warm load | **2.1 s** |
| Peak RSS | **33.9 GB** |

**The `COREAI_CHUNK_THRESHOLD` dial** (`:124-141`) — a genuinely useful, undocumented knob.
`llm-runner --help` hints *"use 128 for MoE"*. On a 128 GB M4 Max **the opposite is true**, but
*"the hint is really a **memory dial**"*. 4096-token prefill, 3 trials:

| Chunk threshold | Prefill tok/s | Peak dirty footprint |
|---|---:|---:|
| **128** (the MoE hint) | 766 | **1.7 GB** |
| **1024** (default) | 1237 | (not measured) |
| **8192** (no chunking) | **1439** | **18.0 GB** |

*"Unchunked MoE prefill allocates huge expert activations (~18 GB dirty for 4096 tokens on top of
the mmap'd weights). On a 16–32 GB Mac that would swap or jetsam — chunk 128 caps it at 1.7 GB for
a **1.9× prefill cost**. On a big-RAM Mac, RAISE the threshold: **+16 % prefill over the default
for free**. Decode is unaffected (~76–78 tok/s everywhere)."*
Repro given: `COREAI_CHUNK_THRESHOLD=8192 swift run -c release llm-benchmark --model exports/gpt_oss_20b_dynamic -p 4096 -g 128 -n 3`

#### The Core AI vs MLX matrix, with prefill

`:153-173`. Same numbers as §7.1's rows 1–7, plus prefill in parentheses:

| Model | Core AI decode (prefill) | MLX 0.31.3 decode (prefill) | Verdict |
|---|---|---|---|
| gpt-oss-20b (MoE) | 78.1 (1252) | **100.2** (1528) | **MLX +28 %** |
| qwen3-0.6b | **484** (9396) | 432 (9366) | **CA +12 %** |
| qwen3-4b | 145.4 (**1635**) | 145.8 (1495) | tie |
| qwen3-8b | **94.1** (912) | 90.0 (825) | **CA +5 %** |
| gemma3-4b-it | **141.5** (1669) | 136.3 (1631) | **CA +4 %** |
| gemma3-12b-it | 55.0 (**578**) | 55.1 (528) | tie |
| mistral-7b-v0.3 | **101.7** (976) | 97.5 (918) | **CA +4 %** |

*"Core AI matches or beats MLX on every dense model (+4–12 % decode, +6–11 % prefill on the bigger
ones). MLX's one clear win is the MoE."* Memory caveat: *"gpt-oss memory: **MLX Metal peak 14.6 GB
vs Core AI 33.9 GB RSS** — not directly comparable; RSS includes the mmap'd 13 GB weight file."*
Quantization comparability note: *"Core AI macOS presets = int4 weight-only, block 32;
mlx-community = 4-bit affine, group 64. Same weight-byte class, slightly different schemes.
gpt-oss is byte-identical MXFP4 in both."*

#### Benching gotchas (`:177-200`)

- *"`/usr/bin/time -l`'s 'peak memory footprint' counts only **dirty** pages — the mmap'd weight
  file shows up in 'maximum resident set size' instead. Report **RSS** for 'how much RAM do I
  need', **footprint** for 'how much does inference itself allocate'."*
- *"The first-ever run of a bundle includes on-device GPU specialization (gpt-oss-20b: 13.2 s vs
  2.1 s warm). **Don't average it into load-time numbers** — report both."*
- **`mistralai/Mistral-7B-Instruct-v0.3` downloads 27 GB, not 15** — the repo ships transformers
  shards **and** a redundant `consolidated.safetensors` (14 GB), and the export fetches
  everything. *"On a tight disk this ENOSPCs mid-export."*
- *"Apple's exporters need scratch space ≈ **one extra copy of the fp16 weights** while
  serializing."*
- **`models/depth-anything/export.py` crashes with OMP Error #15** (duplicate libomp — torch +
  DA3's deps both link OpenMP in the uv-resolved env). Workaround:
  `KMP_DUPLICATE_LIB_OK=TRUE uv run export.py`.

Reproduction is offered: every bundle is on HF as `mlboydaisuke/<model>-CoreAI-official`,
hash-stamped (including the macOS-26 0.6B artifact), and the CV bench script is
`knowledge/scripts/bench_cv_aimodel.py`.

### 7.3 `cross-runtime-quality-benchmarking.md` — how to not measure your own harness

Written 2026-07-17 after a **Gemma-4-E2B GSM8K comparison (Core AI / MLX / LiteRT-LM) produced a
Core AI "quality win" that was entirely an artifact of the harness.** This is the single best
methodology document in the corpus and its lesson is transferable to *any* cross-runtime claim.

#### The failure, concretely (`:9-34`)

> Scores about to be published: **Core AI 80 % vs MLX ~20 %. Both numbers were meaningless.**

1. **The arms ran the model in different MODES.** *"Gemma-4 has a configurable thinking mode.
   **HF's `apply_chat_template` defaults to thinking ON. The same template rendered by
   swift-transformers (what `llm-runner` uses) comes out thinking OFF**, and `llm-runner` exposes
   no flag to turn it on. One arm did chain-of-thought, the other answered directly — and the
   delta was about to be reported as runtime quality."*
2. **The token budget truncated the thinking arm.** *"Thinking-ON Gemma-4-E2B spends ~250 tokens
   reasoning before it answers; a GSM8K item needs **419–479 tokens**. The budget was **512** —
   right at the cliff. Easy items fit; hard ones were cut off mid-thought, and the answer extractor
   then scraped a stray number out of the reasoning text. Measured: same build, same weights →
   **~20 % at 512, correct when given room.**"*
   > **"A truncated reasoning arm is indistinguishable from a bad model. Nothing in the log says
   > 'truncated' — you get a confident wrong number."**
3. **The two defects hid each other**: *"the arm we had **handicapped** (Core AI, thinking off) was
   the one that **scored well**, because direct answers fit in 512. **The harness manufactured the
   result we would have liked.**"*
4. **Provenance.** *"Three of the four numbers in the table (bf16 92 / LiteRT 88 / MLX 78) had no
   stored report and no recorded budget or mode. **Inherited numbers are not measurements. If you
   cannot re-run it, do not cite it.**"*

(This is the *same* incident referenced in `AGENTS.md:78-79` as *"A 12-point 'quality gap' in this
repo's history turned out to be a 600-vs-2048 token cap difference."*)

#### The checklist (`:36-50`) — reproduce this verbatim in a guide

- **Same checkpoint.** *"Not 'both int4' — the same file."*
- **Same mode.** *"Thinking/reasoning defaults differ **per template renderer**, not just per
  model. Verify by grepping the raw generations for the thinking marker (`<|channel>thought` on
  Gemma-4) — **do not trust the template source**."*
- **Budget ≥ 2× the observed worst case.** *"Measure the worst case first … Never set the budget
  from the *typical* length."*
- **Check the truncation rate explicitly.** *"Count generations that hit `max_tokens` without
  emitting the answer marker. If it is not ~0, the score is a budget artifact."*
- **Probe-item parity before the full run.** One item through every arm; compare prompt token
  count, output token count, and answer. *"Ours: Core AI 76→195, MLX 75→197, both correct."*
- **Store a report per run** with `n`, `max_tokens`, mode, checkpoint, per-item preds.

#### "Bits are not a spec" (`:52-82`) — a crucial framing for Gemma 4 QAT

*"'int4' named three different products in this comparison. Google publishes **four** QAT
checkpoints for Gemma-4 and they are not interchangeable"*:

| Variant | What it is | Who uses it |
|---|---|---|
| **Unquantized QAT (Q4_0)** | half-precision weights from the QAT pipeline, *"for custom downstream compilation and research"* | Core AI, the zoo's MLX build |
| **Mobile-optimized (`wNa8o8`)** | *"targeted **2-bit decoding layers**, optimized **KV caches**, and **static activations**"* | LiteRT-LM `.litertlm` |
| GGUF (Q4_0) | ready-to-deploy | llama.cpp etc. |
| Compressed Tensors (w4a16) | vLLM | server |

> *"The mobile variant is a **co-designed weights+runtime package, not a bit-width**. It differs
> on three axes at once (2-bit layers → fewer bytes/token; optimized KV cache → less traffic *and*
> smaller footprint; int8 activations → a different arithmetic path). Comparing it to a generic
> Q4_0 build and calling the delta 'runtime speed' credits the engine with what is substantially
> the checkpoint's doing."*

**A bandwidth sanity check that fails** (`:70-72`) — and why: *"Gemma-4 **gathers** its PLE, so
model size ≠ bytes/token (**MLX at 181.9 tok/s × 3.3 GB = 600 GB/s would exceed the M4 Max's
546 GB/s peak** — proof that no arm reads its whole file per token)."*
**← A nice worked example of using a hardware ceiling to falsify an assumption.**

**To build a matched pair** (`:74-82`): compile every arm from the *unquantized QAT* checkpoint
yourself, at the same block size:
```
mlx_lm.convert --hf-path <qat-q4_0-unquantized> --mlx-path <out> -q --q-bits 4 --q-group-size 32
```
*"matching Core AI's int4lin per-block-32. Then weights, recipe, and block size are equal and the
runtime is the only variable."*

#### Ops notes (`:84-97`)

- HF python downloads stall (xet) → `curl -C -` against `resolve/main/<file>`, check
  `x-linked-size` for the real size; `HF_HUB_DISABLE_XET=1` also helps. **(Note: this contradicts
  `conversion-guide.md:151-153`, which says `HF_HUB_DISABLE_XET=1` does NOT bypass Xet and that
  `curl -C -` HANGS the bridge. The two docs disagree — see §13 Open questions.)**
- *"`llm-runner` on a gemma4 `tbl` bundle needs `--raw-dir <ple dump>` (PLE static inputs) and
  `COREAI_CHUNK_THRESHOLD=1` (the `S=1` graph cannot take a multi-token prompt), plus
  `--warmup exact --warmup-length 1` (the default warmup prefills 256 → fatal on `S=1`)."*
- **A silent, expensive one**: *"A bundle with no `chat_template` anywhere **silently falls back to
  raw completion**. `--apply-chat-template` defaults to true and does *not* warn when there is
  nothing to apply."* ← this is exactly the defect `zoo_verify.py` found on 10 Gemma 4 bundles
  (§3.4). The two facts together make a complete story: *the exporter dropped
  `chat_template.jinja`, the runner silently degraded to raw completion, and nothing warned.*

### 7.4 `dense-int4km-flagship-session-findings.md` — the dense-path int4 lever

Dated 2026-07-01. **Lever**: the shipped `metalize_moe` (`gather_qmm`) kernelizes only the routed-
expert FFN; **the dense path (lm_head + attention q/o + shared expert) stays on MPSGraph**. So wire
the proven fused int4km matvec into the dense path too. *"lm_head is the single biggest per-token
matvec (vocab × hidden); attn q/o are the next; **k/v stay fp16 (N small — 'small-N matvecs never
pay', the Mac lesson)**."*

#### Measured results (`:32-38`)

| Evidence | Number | Method / file |
|---|---|---|
| lm_head int4km **per-op** vs fp16 @ vocab = 248 K (flagship's shape) | **2.77×** | `ondevice/_dense_int4km_microbench.py` |
| Byte-audit ceiling (config-only) | Qwen3.6 **~1.97×**, GLM-4.7 **~1.34×** | `_flagship_dense_coverage_audit.py` |
| **LFM-8B on-device (A19, PipelinedBench)** decode | **1.23× sustained / 1.43× avg** | thermally-matched `PB_N=6` |
| LFM-8B on-device **quality** | **PASS** (33/48 greedy match, coherent, 25+17=42 correct) | reasoning prompt |
| **Flagship Qwen3.6-35B (Mac M4 Max GPU)** decode | **2.18×** (2.79 → 6.08 tok/s) | `_qwen36_mac_bench.py` |

*"The flagship 2.18× **exceeds** the ~1.97 × audit projection — and per-step fixed overhead
*compresses* the ratio, so the true byte-read win is ≥ 2.18×."*

#### The methodological caveats the author attaches to his own numbers (`:45-63`) — model behaviour

- **⚠️ On-device (A19) model-size ceiling ≈ 5–6 GB (int4-8B-class).** LFM-8B (5 GB) runs;
  **Qwen3.6-35B int4 (18 GB) → `signal 9` (jetsam OOM)** on the iPhone 17 Pro's ~12 GB RAM,
  *"killed during the ~26-min cold compile."* **The flagship 35B cannot run on the phone.**
- **✅ Mac-GPU method**: raw `rt.AIModel.load(aimodel,
  SpecializationOptions.from_preferred_compute_unit_kind(ComputeUnitKind.gpu()))`.
  *"It **spews `ANECCompile() FAILED / MLIR MPS to ANEC conversion failed` (dozens) — these are
  NON-FATAL**: MPSGraph falls back to GPU and runs. Earlier I killed a run on the first ANE error
  (wrong call)."* And: *"There is **no GPU-only spec** (`allowed_compute_unit_kinds` is a
  **read-only property**; only `default` / `cpu_only` / `from_preferred` exist), so you can't
  suppress the ANE attempts."*
- **⚠️ *"Absolute tok/s from the quick Mac driver are ~10× too slow"*** (ANE-retry + per-step
  re-specialization overhead): *"**2.79 / 6.08 are NOT real speeds** (the real Qwen3.6-35B is tens
  of tok/s via the proper engine). **Only the RATIO (2.18×) is valid**."*
  **← Do not quote 2.79/6.08 as throughput. Quote the 2.18× ratio only.**
- **HF download slowness = an `hf_xet` bug, NOT a rate-limit** — *"Symptom: starts ~14 MB/s then
  stalls (esp. near 99 %). Fix = `HF_HUB_DISABLE_XET=1`."* HF's actual rate limit
  (`ratelimit-policy: fixed window;resolvers;q=12000;w=300`) was *"nowhere near hit"*. Also:
  *"Restarting `snapshot_download` repeatedly **LOSES `.incomplete` progress**; let one run
  finish."* Cited to `xet-core #789` / `huggingface_hub #3580`.

#### Quality — the honest state (`:65-81`)

*"The dense-int4km lever itself is quality-safe (LFM-8B coherent). **Flagship int4 degrades
quality** … the 2.18× is a **speed win at a known int4 quality cost.**"* The flagship greedy check
was **inconclusive** — *"the quick Mac driver produced garbage for BOTH int8 and int4 = a driver
bug, not int4."*

#### §8 — the FP4 (E2M1) dense matvec twin (built + measured 2026-07-02)

**Premise**: swap int4km → fp4-E2M1 for the same ¼ weight bytes but *"int8-level quality"*.
Implementation notes (`:126-134`): everything identical to int4km (packing 8 codes/uint32, R/SGY
tiling, dispatch) except the dequant — *"fp4 maps the 4-bit code through the FIXED universal E2M1
grid (16 constants staged in **tg memory**) × a per-K-block **e8m0** power-of-2 scale (block 32).
So the kernel is the AFFINE-int4 structure (scale along K) minus the bias."*
Numerics: *"`quantize_fp4_e2m1` uses e8m0 scale `2^(floor(log2|amax|)-2)` + torchao
`f32_to_f4_unpacked`; reconstruction `max|W_mine − torchao_fp4| = 0.0`. The Metal kernel matches
its torch reference `cosKern = 1.0000`."*

**Speed** (per-op `q=1` decode, **Mac M4 Max**, random weights, `_dense_fp4_microbench.py`,
`:137-141`):

| Shape | K | N | fp16 ms | int4km ms | fp4 ms | fp4/fp16 | **fp4/int4km** | cos(fp4,fp16) |
|---|---|---|---|---|---|---|---|---|
| q_proj | 2048 | 4096 | 0.482 | 0.509 | 0.524 | 0.92× | 0.97× | 0.9926 |
| o_proj | 4096 | 2048 | 0.470 | 0.512 | 0.502 | 0.94× | 1.02× | 0.9919 |
| **lm_head** | 2048 | **248 320** | 3.358 | 1.972 | **1.951** | **1.72×** | **1.01×** | 0.9930 |

*"Small shapes sit under the **~0.35 ms round-trip floor**, so < 1× vs fp16 there — the Mac
ALU-bound regime … lm_head is the real signal."*

**Key kernel lesson** (`:148-151`), directly reusable:
> *"a naive `const float FP4[16]` indexed by a **runtime** code **spills to stack** on Apple GPUs
> and made fp4 ~1.4× SLOWER than int4km (0.70× at lm_head). **Staging the 16-entry grid into
> threadgroup memory** (as int4km does its codebook) turns the lookup into a fast tg-mem gather →
> fp4 back to int4km speed."*

#### §8b — the honest negative result: **fp4 does NOT beat int4km on quality**

`:170-195`. The premise came from an fp4-vs-int4-**RTN** de-risk (fp4 +1.0 % vs int4-RTN +10.2 %
ppl). But the flagship uses int4-**km** (k-means), *"which is already outlier-robust."* Measured on
**real flagship weights** (`conversion/quant_fp4/flagship_dense_fp4_vs_int4km_quality.py`; lm_head
top-1 flip on an embed-rows-through-final-RMSNorm hidden proxy, S=512):

| | int8km | int4km | fp4 (e8m0) | fp4 (fp16 scale) |
|---|---|---|---|---|
| lm_head weight rel-err | 0.032 | 0.124 | 0.115 | 0.102 |
| **lm_head top-1 flip vs fp16** | **32 / 512** | **104 / 512** | **104 / 512** | **117 / 512** |

> *"**fp4 ≈ int4km in quality** (identical 104/512 flip for e8m0; **fp16-scale fp4 has LOWER weight
> error yet MORE flips — weight-RMSE is a misleading proxy in both directions**). Neither 4-bit
> scheme approaches int8km (32 flips). **Conclusion: fp4 gives no quality advantage over int4km on
> the dense path** … **The int4 flagship cliff is a 4-bit-CAPACITY gap vs int8, NOT an RTN-vs-fp4
> issue** (k-means already fixed the RTN part). So **int4km → fp4 is a no-op**."*

Remaining quality-safe paths: (a) keep the dense path **int8** (int8km: 6 % flip, ~half the byte
win), or (b) **QAT-int4**. *"fp4's genuine edge is only when the neural accelerator dequants it for
free (TensorOps) — which is decode-irrelevant (BW-bound) and A19-refuted for prefill."*
Caveat kept: the flip was measured on a **hidden-state proxy**, not real decode hidden.

#### §6 — two important corrections about prefill / FlashAttention

`:84-94`:
- **⚠️ A correction of an over-generalization**: *"On **M4 Max, MPSGraph prefill SDPA is only
  ~22 % of the fp16 peak (~6.4 TFLOP/s @ S=4096)** — i.e. **~78 % HEADROOM, NOT near-ceiling**. A
  custom prefill kernel (simdgroup_matrix / fused FlashAttention) on Mac is **UNTESTED**."*
  So **Mac prefill FlashAttention is a genuine open lever.**
- **The A19 refutation is A19-only**: the "TensorOps `matmul2d` gives 3–4× prefill" claim is an
  **M5 result that does not hold on A19** — *"default MPSGraph already ≈ 6 TFLOP/s there."*
  **← This directly qualifies the survey numbers quoted in §5.7. If a guide cites Apple's
  MLX-on-M5 3.33–4.06× prefill figure, it must note this community A19 refutation.**

### 7.5 Consolidated benchmark table (all numbers found this session)

Every row is **community-measured** unless the "Source" column says otherwise. Hardware/OS is
recorded exactly as the source states it; blank = the source did not say.

#### A. Decode throughput, iPhone 17 Pro (A19 Pro), iOS 27 beta, GPU unless noted

| Model | tok/s | Note | Source |
|---|---:|---|---|
| Qwen3.5-0.8B | **71.9** | GPU | `README.md:193` |
| Qwen3.5-0.8B | 14.7 | **ANE** | `README.md:193` |
| Qwen3.5-0.8B | 68.4\* | `pb-random-v1` protocol, n=1 | `BENCHMARKS.md:28` |
| Qwen3.5-2B | **29** | | `README.md:194` |
| LFM2.5-1.2B | **45.4** | | `README.md:195` |
| Granite 4.0-H 1B | **36.3** | | `README.md:196` |
| Nanbeige4.1-3B | **15.9** | | `README.md:197` |
| MiniCPM5-1B (int8) | **66.8** | 24/24 exact vs HF | `README.md:199` |
| Youtu-LLM-2B (dense MLA, int8) | ~19 (in-app ~24) | 16/16 device ≡ Mac ≡ HF | `README.md:200` |
| FastContext-1.0-4B (4-bit, AOT h18p) | **20.4** | **ANE inference unsupported** | `README.md:201` |
| BitCPM-8B (**1.58-bit ternary**, AOT h18p) | **17** | ~2.1 GB resident, token-exact 3/3 | `README.md:202` |
| Gemma 4 E2B | **30.3** (QAT 30.7) | GPU | `README.md:203` |
| Gemma 4 E2B | 6 | **ANE** | `README.md:203` |
| Gemma 4 E2B **raw-Metal** (mixed-bit int2/int4 hand kernels) | **~55** | *"= LiteRT-LM parity, lossless"* | `README.md:120` |
| Gemma 4 E4B (official QAT) | **15.1** | | `README.md:204` |
| Gemma 4 E2B VL (image+text, QAT) | **25.5** | | `README.md:205` |
| MiniCPM-V 4.6 (sub-2B VLM) | **53.4** | | `README.md:206` |
| LFM2.5-8B-A1B int4km MoE (`gather_qmm`) | **~32** | *"the zoo's first iPhone MoE on hardware"*, 4.7 GB | `compute-units-and-authoring.md:76-77` |
| qwen3-0.6b **ANE**, official iOS preset | 69.6 / 54.1 (run1/run2) | 512p/1024g protocol; **run-2 drop is thermal** | `apple-models-bench.md:46` |
| qwen3-0.6b GPU, **macOS-27β artifact** | 57.2 / 52.5 | | `apple-models-bench.md:47` |
| qwen3-0.6b GPU, **macOS-26 artifact** | **115.1 / 90.4** | **same recipe — 2× the 27β artifact** | `apple-models-bench.md:48` |
| qwen3-0.6b GPU, macOS-26 artifact, **128p/128g** | **184–190** | *"later trials drop to ~125 thermally"* | `apple-models-bench.md:51-54` |
| qwen3-4b **ANE**, official iOS preset | 13.2 / 12.2 | cold load **194 s** | `apple-models-bench.md:49` |
| DeepSeek-R1-1.5B, **Core AI ANE** | **83.3** | matched 4-bit bytes, short-chat, median-of-3 | `coreai-vs-mlx-speed.md:71` |
| DeepSeek-R1-1.5B, **Core AI GPU** | 75.9 | " | " |
| DeepSeek-R1-1.5B, **MLX (mlx-swift, GPU)** | 73.0 | " | " |
| gemma4 E2B, iPhone **GPU vs ANE** (earlier measurement) | 7.4 vs 5.9 | *"the GPU lead was small"* | `coreai-beta-mpsgraph-kvwrite-bug.md:99` |

Energy, same DeepSeek-R1-1.5B run (**tokens per 1 % battery**): **ANE 6 144 · MLX 5 662 ·
Core AI GPU 4 506**. (`coreai-vs-mlx-speed.md:71-72`)

#### B. Decode throughput, Mac (M4 Max 128 GB, macOS 27 beta) unless noted

| Model | tok/s | Note | Source |
|---|---:|---|---|
| Qwen3.5-0.8B | **210** | | `README.md:193` |
| Qwen3.5-2B | **161** | | `README.md:194` |
| LFM2.5-1.2B | **276.5** | | `README.md:195` |
| Granite 4.0-H 1B | **136.5** | | `README.md:196` |
| Nanbeige4.1-3B | **114.5** | | `README.md:197` |
| Nanbeige4.2-3B (looped Llama, int8) | **46.4** | 22 physical / 44 executed+cache layers | `README.md:198` |
| MiniCPM5-1B (int8) | 59.4 | **slower than iPhone's 66.8** — see note below | `README.md:199` |
| Youtu-LLM-2B (dense MLA, int8) | **102.8** | | `README.md:200` |
| BitCPM-8B (1.58-bit ternary) | **62.7** | | `README.md:202` |
| Gemma 4 E2B | **77.0** (QAT 78.9) | | `README.md:203` |
| Gemma 4 E4B (QAT) | **55.8** | | `README.md:204` |
| Gemma 4 E2B VL | **82.4** | | `README.md:205` |
| MiniCPM-V 4.6 | **224.3** | | `README.md:206` |
| Qwen3.6-35B-A3B (MoE, `gather_qmm`) | **64.9** | Mac-only | `README.md:207` |
| Qwen3.6-27B (dense) | **15.9** | Mac-only | `README.md:208` |
| GLM-4.7-Flash (MoE+MLA, `gather_qmm`) | **52.4** | Mac-only | `README.md:209` |
| Gemma 4 12B (dense, custom flash-decode kernel) | **23 int8 / 33 int4** | *"unrunnable without"* the kernel | `README.md:210` |
| Gemma 4 31B (dense, custom flash-decode kernel) | **17.2 int4** | " | `README.md:211` |
| Ornith-1.0-9B | **48 int8 / 59 int4** | agentic coding, Qwen3.5 arch | `README.md:117` |
| qwen3-0.6b (Apple official recipe) | **484** (558 short-ctx) | 512p/1024g/5 | `apple-models-bench.md:22` |
| qwen3-4b | 145.4 (164 short-ctx) | | `apple-models-bench.md:23` |
| qwen3-8b | 94.1 (102) | | `apple-models-bench.md:24` |
| gemma3-4b-it | 141.5 (157) | | `apple-models-bench.md:25` |
| gemma3-12b-it | 55.0 (59) | | `apple-models-bench.md:26` |
| mistral-7b-instruct-v0.3 | 101.7 (109) | | `apple-models-bench.md:27` |
| gpt-oss-20b (MoE, MXFP4 passthrough) | **78.1** | prefill 1252, cold load 13.2 s, 33.9 GB RSS | `apple-models-bench.md:21` |
| GLM-Image AR stage | ~36 | 9B GLM-4 sampling visual prior tokens | `README.md:167` |

> **Note the MiniCPM5-1B inversion**: iPhone 66.8 vs M4 Max 59.4 tok/s. The README does not
> explain it. Plausibly a small model in a dispatch-bound regime plus a different bundle config;
> **UNVERIFIED**. Worth flagging as an example of why "Mac is always faster" is not safe.

#### C. Kernel / config A-B results

| Change | Before → After | Hardware | Source |
|---|---|---|---|
| MoE stock `GatherMM` → `gather_qmm` Metal kernel, LFM2.5-8B-A1B int8 | **39 → 141 tok/s (3.6×)** | M4 Max | `compute-units-and-authoring.md:74-75` |
| Same, Qwen3.6-35B-A3B | **30.9 → 64.9 (2.1×)** | M4 Max | `coreai-vs-mlx-speed.md:19-20` |
| Same, GLM-4.7-Flash | **20.3 → 52.4 (2.6×)** | M4 Max | `coreai-vs-mlx-speed.md:22` |
| LFM2.5-8B-A1B MoE int8 → int4 (stock path) | **39 → 170 tok/s** (8.8 → 5.0 GB) | M4 Max | `compute-units-and-authoring.md:59-62` |
| Dense-path int4km (lm_head + attn q/o), Qwen3.6-35B | **2.18× ratio** (absolute numbers invalid) | M4 Max | `dense-int4km-flagship-session-findings.md:38` |
| Dense-path int4km, LFM-8B | **1.23× sustained / 1.43× avg** | iPhone 17 Pro | `dense-int4km-...:36` |
| lm_head int4km vs fp16, vocab 248 K | **2.77×** per-op | M4 Max | `dense-int4km-...:34` |
| lm_head fp4-E2M1 vs fp16, vocab 248 K | **1.72×** (and **1.01× vs int4km**) | M4 Max | `dense-int4km-...:141` |
| fp4 lookup table in registers → threadgroup memory | fixes a **1.4× slowdown** | Apple GPU | `dense-int4km-...:148-151` |
| Hand-rolled per-token `fn.run()` loop → Apple's `coreai-pipelined` engine, qwen3.5 | **58.5 → 204 tok/s (~3.5×)** | M4 Max | `coreai-vs-mlx-speed.md:47-50` |
| `COREAI_CHUNK_THRESHOLD` 128 → 1024 → 8192, gpt-oss-20b prefill @4096 | **766 → 1237 → 1439 tok/s**; footprint **1.7 GB → 18.0 GB** | M4 Max 128 GB | `apple-models-bench.md:130-134` |
| `cpu_only()` → `default()`, TripoSplat DiT | **24.2 s → 2.6 s (~9.3×)** per call | Mac | `conversion-guide.md:35-36` |
| `.aimodel` JIT → `.aimodelc` AOT, first (cold) load, int8-kernel monolith | **19.2 s → 4.9 s (~4×)**; warm 0.0 s both | iPhone | `aot-and-specialization.md:148-150` |
| Prefix-cache OFF → ON, turn 2 @ 4103 tokens | **23.282 s → 0.230 s (101×)** TTFT | Mac | `prefix-cache-kv-reuse.md:58` |
| Prefix-cache OFF → ON, turn 2 @ 357 tokens | **1.915 s → 0.126 s (15.2×)** TTFT | Mac | `prefix-cache-kv-reuse.md:57` |
| Consumer-break stop fix, two-turn chat, qwen3.5-0.8B | **2.74 s → 0.40 s** 2nd-turn latency | — | fork commit `627fec7` |
| SSM scan: chunked-SSD prefill kernel | **13.7×** (prefill only; decode kernel only 3–8 %) | Mac | `custom-metal-kernels.md:124` |
| Asymmetric int4 → zero-point-factored fused matvec | **3.3× Mac / ~5× device** over stock asymmetric | both | `custom-metal-kernels.md:123` |

#### D. Vision / other-modality latency

| Model | Latency | Hardware | Source |
|---|---|---|---|
| clip-vit-base-patch32 fp32 | GPU 6.54 / **ANE 5.43** / CPU 18.76 ms | M4 Max | `apple-models-bench.md:69` |
| clip-vit-base-patch32 **fp16** | GPU 6.31 / **ANE 3.68** ms (289 MB) | M4 Max | `apple-models-bench.md:70` |
| yolos-base fp32 | **GPU 444.8** / ANE 456.7 / CPU 733.7 ms | M4 Max | `apple-models-bench.md:71` |
| sam3 fp32 (3.1 GB) | **GPU 559.9** / ANE 565.7 / CPU 2789.7 ms | M4 Max | `apple-models-bench.md:72` |
| depth-anything-3 (small) fp32 | GPU 7.30 / **ANE 6.84** / CPU 34.58 ms | M4 Max | `apple-models-bench.md:73` |
| TimesFM 2.5 200M forecast | **~14 ms** / **~25 ms** | M4 Max / iPhone 17 Pro | `README.md:169` |
| V-JEPA 2 ViT-L, 16-frame clip | **~160 ms/clip** (fp16 ~675 MB) | M4 Max | `README.md:153` |
| Stable Audio Open Small, 11 s @44.1 kHz stereo | **~0.4 s ≈ 30× real-time** | M4 Max | `README.md:152` |
| Mel-Band RoFormer source separation | **6.5× real-time** | iPhone 17 Pro | `README.md:151` |
| VibeVoice-Realtime-0.5B TTS | **10.6 tok/s ≈ 1.4× real-time** | iPhone 17 Pro | `README.md:150` |
| Parakeet-TDT-0.6B ASR | **47.9× real-time** | iPhone | `README.md:144` |
| GLM-OCR (0.9B) | **~4 s/page** | iPhone + Mac | `README.md:139` |
| Z-Image-Turbo (6B S3-DiT) | **18 s @512² / 70 s @1024²**; PSNR **42.6 dB** vs fp32 | M4 Max | `README.md:168` |
| LTX-Video 2B, 512×768×49f | **~14 s** | Mac GPU | `README.md:165` |
| TripoSplat single image → 3DGS | **~1 min** | Mac GPU | `README.md:164` |
| RF-DETR-class CV model, thermally saturated | **25 ms → 58–103 ms** | iPhone | `conversion-guide.md:180-182` |
| LLaDA-8B dLLM forward, S=128 / S=256 | **385.8 / 692.1 ms** (warm min) | iPhone 17 Pro (A19) | `accel-levers-survey-and-plan.md:158-159` |

#### E. Load / specialization times

| Event | Time | Source |
|---|---|---|
| gpt-oss-20b cold (incl. GPU specialization) / warm | **13.2 s / 2.1 s** | `apple-models-bench.md:21` |
| qwen3-4b ANE `.aimodelc` (3 GB) cold / warm | **194 s / 0.46 s** | `apple-models-bench.md:49` |
| qwen3-0.6b ANE cold / warm | 2.85 s / **0.045 s** | `apple-models-bench.md:46` |
| gemma4 E2B 1.8 GB ANE `.aimodelc` load on iPhone | 6.5–8.1 s, no jetsam (**but first inference is jetsam-killed**) | `aot-and-specialization.md:134-141` |
| Cold GPU specialization, 0.8B / 2.3 GB, iPhone | **≈ 4.8 s / ≈ 29 s** | `coreai-vs-mlx-speed.md:119-120` |
| Qwen3.5-0.8B int8 as a FoundationModels `LanguageModelSession` | load **3.7 s**, first turn **0.41 s** | `fm-provider.md:5` |
| gemma3-12b-it warm load | **5.4–7.7 s (variance across runs)** | `apple-models-bench.md:26` |
| Qwen3.6-35B int4 (18 GB) on iPhone 17 Pro | **`signal 9` jetsam OOM** during a **~26-min cold compile** | `dense-int4km-...:53-54` |

---

## 8. Foundation Models integration — the community side

### 8.1 `fm-provider.md` — zoo models behind `LanguageModelSession`

**The single most important file in this corpus for the FM guides.** Verified 2026-06-11 on
macOS 27 beta, M4 Max. Sources it cites: **WWDC26 339 "Bring an LLM provider to the Foundation
Models framework"**, **WWDC26 241 "What's new in the Foundation Models framework"**, and — this
matters — *"the `FoundationModels.swiftmodule` interface in the macOS 27 beta SDK (**signatures
above were read from it, not from docs**)"*.

#### Headline (`:3-11`)

> a zoo pipelined bundle backs Apple's standard `LanguageModelSession` **with zero new code** —
> `CoreAILanguageModel(resourcesAt: bundleDir)` is the entire integration (Qwen3.5-0.8B int8:
> load 3.7 s, first turn 0.41 s, multi-turn OK). **The one capability Apple's adapter lacks is
> tool calling**; a **~200-line** own `LanguageModel` conformance added it, and the full round trip
> — model emits a call, the framework runs the Swift `Tool`, the model answers grounded on the
> result — worked on the first run, hybrid 4-state Qwen included.

Ecosystem context (`:13-17`): *"Anthropic and Google announced FM provider packages for
Claude/Gemini; MLX has `MLXLanguageModel` (`ml-explore/mlx-swift-lm`); Hugging Face ships
`AnyLanguageModel`."*

#### The protocol (read from the 27-beta `.swiftinterface`) (`:23-38`)

```swift
protocol LanguageModel: Sendable {
    associatedtype Executor: LanguageModelExecutor where Self == Executor.Model
    var capabilities: LanguageModelCapabilities { get }   // .vision/.guidedGeneration/.reasoning/.toolCalling
    var executorConfiguration: Executor.Configuration { get }
}
protocol LanguageModelExecutor: Sendable {
    associatedtype Configuration: Hashable, Sendable      // per-session executor cache KEY
    init(configuration: Configuration) throws
    func prewarm(model: Model, transcript: Transcript)    // careful: default no-op exists
    nonisolated(nonsending) func respond(
        to request: LanguageModelExecutorGenerationRequest,
        model: Model,
        streamingInto channel: LanguageModelExecutorGenerationChannel) async throws
}
```

Execution model (`:40-47`): *"The session hands the executor the **full transcript on every
`respond`** (entries: `instructions / prompt / toolCalls / toolOutput / response / reasoning`),
plus `enabledToolDefinitions`, an optional `schema`, and `generationOptions`. The executor streams
events back: `.response(action: .appendText(...))`, `.reasoning(...)`,
`.toolCalls(action: .toolCall(id:name:action: .appendArguments(json)))`, `.updateUsage`,
`.updateMetadata`. One-shot `respond` is just collected streaming. **KV reuse across turns is the
executor's job** (diff the new transcript against the one you saved; invalidate at the divergence
point) — **nobody does it for you.**"*
**← This is exactly the problem `trimKVCache` (§2.4) exists to solve, from the other side of the
protocol.**

#### Quick start — Apple's adapter, zoo bundle (`:51-60`)

```swift
import CoreAILanguageModels   // product "CoreAILM" of the coreai-models package
import FoundationModels

setenv("COREAI_CHUNK_THRESHOLD", "1", 1)   // BEFORE engine creation (decode-only S=1 bundles)

let model = try await CoreAILanguageModel(resourcesAt: bundleDirURL)  // LanguageBundle dir
let session = LanguageModelSession(model: model, instructions: "You are a helpful assistant.")
let answer = try await session.respond(to: "Why is the sky blue?")
```

Requirements (`:62-71`): a **LanguageBundle dir** (`metadata.json` + `.aimodel` + `tokenizer/`);
**the patched `coreai-models` package** for non-standard architectures (*"Plain-attention bundles
run on the unpatched upstream; **Qwen3.5 (hybrid GDN), LFM2.5, Granite (SSM), Gemma 4 tbl do
not**"*); `EngineFactory` auto-picks the engine from bundle structure.

Free from Apple's adapter (`:74-76`): *"UTF-8-safe incremental detokenization, `<think>` /
`<|reasoning_start|>` auto-detection routed to `.reasoning` transcript entries, chat templating
via the bundle tokenizer, greedy default + temperature override."*

#### What works / what doesn't (`:79-87`) — the capability matrix

| Surface | Status |
|---|---|
| Plain chat, streaming, multi-turn | ✅ via Apple's adapter, **zero code** |
| Reasoning models (`<think>`) | ✅ auto-routed to `Transcript.reasoning` entries |
| **Tool calling** | ❌ in Apple's adapter (*"tool entries skipped, capability never declared"*) → ✅ `ZooFMProvider` (multi-call, streaming parse, **per-model dialect**) |
| **Guided generation (`@Generable`, schema)** | ⚠️ **only when `engine.supportsLogits`** — *"**GPU-pipelined engines sample on-GPU and return `false`**, so every zoo pipelined bundle lacks `.guidedGeneration`; **the sequential engine has it**."* `ZooFMProvider` throws `unsupportedCapability` on schema requests |
| `session.prewarm()` | ❌ **silent no-op** for Core AI models → ✅ `ZooFMProvider` (real 1-token generate + reset) |
| Usage accounting (`.updateUsage`) | ❌ placeholder in Apple's adapter → ✅ `ZooFMProvider` (per-turn, summed into `session.usage`, `cachedTokenCount` on KV reuse) |
| **KV reuse across turns** | ❌ *"Apple's adapter resets + re-prefills everything."* `ZooFMProvider` implements the append-only fast path |

**The KV-reuse row deserves quoting in full** (`:87`):
> `ZooFMProvider` implements the append-only fast path — measured on **LFM2.5-1.2B int8** (turns
> ended by token cap): **turn 2 reused 97 cached tokens and prefilled 18, per-turn latency flat at
> ~0.33 s instead of growing with history**. Structural limits: the engine **over-generates past
> EOS into the cache** and thinking models' templates **strip historic `<think>` blocks the cache
> still contains** — so EOS-ended/thinking turns still reset (measured: **~2.3–2.7 s turn-2
> settle** on the default 512-token budget). **The real fix is engine-side (stop-at-break + KV
> truncate).**

**← "stop-at-break + KV truncate" is *literally* fork commits `627fec7` + `0fdf710` (§2.3, §2.4).
This document states the requirement; the fork commits are the answer. That is the single most
important cross-repo connection in this whole assignment.**

#### Tool calling with an own conformance (`:89-117`)

Four steps:
1. Declare `capabilities = [.toolCalling]`.
2. In `respond`, **render the transcript to ChatML yourself**. Advertise
   `request.enabledToolDefinitions` in the system message inside `<tools>…</tools>` (each as
   `{"type":"function","function":{name, description, parameters: <JSONEncoder'd
   GenerationSchema>}}`); replay past `toolCalls` entries as assistant
   `<tool_call>{json}</tool_call>` turns and `toolOutput` entries as user-role
   `<tool_response>…</tool_response>` turns.
3. Generate (`engine.generate(with:samplingConfiguration:inferenceOptions:)`, break on
   `tokenizer.eosTokenId`), split a leading `<think>` block into a `.reasoning` event, then if the
   output contains `<tool_call>` parse `{"name","arguments"}` and send
   `.toolCalls(action: .toolCall(id: UUID().uuidString, name: name,
   action: .appendArguments(argsJSON, tokenCount: n)))`; otherwise send the text as `.response`.
4. *"That's all — the **framework** parses the arguments against the tool's `@Generable` schema,
   executes the Swift `Tool`, appends the `toolOutput` entry, and calls `respond` again."*

Reused public pieces: `CoreAIRunner(from:).makeInferenceEngine()` + `LanguageBundle.loadTokenizer()`.

Verified transcript on Qwen3.5-0.8B int8, greedy, one shot (`:114-117`):
```
instructions → prompt → reasoning → toolCall get_weather({"city":"Tokyo"})
             → toolOutput get_weather → response   (turn 4.6 s incl. both respond calls)
```

`ZooFMProvider` (in `swift/Sources/ZooFMProvider`) packages: *"streaming incremental
`<tool_call>`/`<think>` parse (**tags straddling token deltas are caught**; text streams the moment
it decodes), multi-call turns (**consecutive `.toolCalls` events coalesce into ONE transcript entry
with N calls** — and the framework executes all of them before re-responding), usage events with
`cachedTokenCount`, `toolCallingMode` honoring (`.disallowed` drops the tools block, `.required`
renders a must-call instruction), and a working `prewarm`."*

**Two beta behaviours the packaged executor encodes** (`:127-136`):
- *"**Don't send WWDC-339-style upfront usage/metadata.** A `.response(updateUsage:)` event on a
  turn that ends in tool calls materializes an **EMPTY `Response` transcript entry**. Send metadata
  + usage once at end of turn, attached to the entry kind the turn produced."*
- *"**Breaking the token stream does not stop the pipelined engine.** It generates to `maxTokens`
  in the background and those post-EOS tokens land in the KV cache; the next `engine.reset()`
  blocks on them (**and its internal drain traps after ~5 s** — big slow models beware). The
  packaged executor pumps the stream through a task it can settle on the next respond instead of
  breaking the engine stream directly."*
  **← the app-side workaround for the same defect fork commit `627fec7` fixed engine-side.**

#### Tool-calling dialects — a genuinely novel finding (`:138-179`)

> *"A model emits tool calls in the format it was **fine-tuned** on, and **an in-context
> instruction will not override that prior** (trap 9). So tool calling can't share one
> renderer/parser across families — each needs its own."*

```swift
public protocol PromptDialect: Sendable {
    var name: String { get }
    var toolCallOpen: String { get }      // stream markers delimiting a call block
    var toolCallClose: String { get }
    func render(transcript:tools:requireToolCall:) -> String          // whole prompt, framing included
    func parseToolCalls(_ body: String, tools:) throws -> [ParsedToolCall]   // a block may hold N calls
}
```
*"The dialect owns the **whole** render (not just the tool block) because families differ in
framing too, not only call syntax. `ZooLanguageModel` **auto-selects by probing the tokenizer
vocab** (`defaultDialect(probing:)`); pass `dialect:` to override."*

Both shipped dialects were validated the right way: *"verified against the bundle's own
`chat_template.jinja` (**render the template with jinja2 and diff against the Swift output — the
template is the spec**)."*

| | **Hermes** (Qwen3.5, default) | **LFM** (LFM2.5) |
|---|---|---|
| tools advertised | system `<tools>{json}…</tools>` block | system `List of tools: [{json}, …]` text |
| call syntax | `<tool_call>\n{"name","arguments"}\n</tool_call>` | `<\|tool_call_start\|>[fn(a="x"), fn2(n=3)]<\|tool_call_end\|>` (**pythonic**) |
| result replay | user-role `<tool_response>…</tool_response>` | `tool`-role `<\|tool_response_start\|>…<\|tool_response_end\|>` |
| framing | ChatML `<\|im_start\|>` | ChatML `<\|im_start\|>` |
| parse | JSON object (or array of objects) | **tolerant pythonic scanner** |

*"The LFM parser must be **tolerant**: the model emits half-mangled argument lists (single quotes,
bare/unquoted values, Python `True`/`None`, nested containers, truncated tails). It **salvages
per-call** (a broken call is skipped, the rest of the block still executes) and maps a lone
positional argument onto a single-parameter tool via the schema. **The replay path sorts kwargs so
re-rendered calls are byte-stable (the KV fast path's prefix match depends on it).**"*
**← that last clause is a beautiful, non-obvious coupling: prefix-cache reuse imposes a
determinism requirement on your prompt renderer.**

Recon for two more families (templates read, dialects not built): **granite-4.0** uses Hermes tool
*syntax* but `<|start_of_role|>…<|end_of_role|>…<|end_of_text|>` framing (so it needs its own
dialect); **gemma4** is fully custom and **non-JSON**
(`<|tool_call>call:name{key:value}<tool_call|>`, a `<|"|>` quote token, `<|channel>thought` for
reasoning).

#### The nine traps (`:181-213`) — reproduce these in any FM-provider guide

1. **`prewarm` has a default no-op extension.** *"Implement `prewarm(model:transcript:)`
   **exactly** — implement `prewarm(transcript:)` and it **compiles but is never called**.
   **Apple's own adapter has this today**, which is why `session.prewarm()` does nothing for Core
   AI models."*
2. **`request.enabledToolDefinitions`** is the property; `enabledTools` is only the
   memberwise-init label.
3. **`Configuration` is the executor cache key.** *"The session stores executors keyed by your
   `Hashable` `Configuration` — key it by bundle identity (+ anything that changes behavior).
   **Apple keys by `(modelIdentifier, samplingConfig)`.**"*
4. **`COREAI_CHUNK_THRESHOLD=1` before engine creation** for decode-only `S=1` bundles, and
   *"never call `engine.warmup()` with the default query length on them (warms `S=256`, which the
   `S=1` graph rejects)."*
5. **Pipelined ⇒ no `.guidedGeneration`.** *"Don't declare it without logits; schema requests on a
   pipelined bundle can't be honored (approximate-or-throw rule: throw
   `LanguageModelError.unsupportedCapability`)."*
6. **Multi-turn re-prefill tax.** *"Until an executor implements transcript diffing, budget
   ~decode-speed × history-tokens per turn on decode-only bundles (measured: **turn 1 = 0.41 s,
   turn 2 = 2.8 s** on the 0.8B with a 3-entry history + hidden thinking)."*
7. **Thinking is invisible in `response.content`** — it lands as `.reasoning` transcript entries.
   *"A 'hanging' first response is usually the model thinking."*
8. **Small `maximumResponseTokens` + a thinking model = no response at all.** *"If the cap cuts
   generation mid-`<think>`, the turn produces only reasoning events and the session throws
   **'ended without producing a response'**."*
9. **Tool-prompt dialects don't transfer** — see above; *"the training prior wins over the
   prompt."*

### 8.2 `dynamic-profiles-local-models.md` — `DynamicProfile` with two LOCAL models

Verified 2026-06-13, macOS 27 beta, M-series Mac. Source: **WWDC26 242 "Build agentic app
experiences"**. Demo: `agent-demos/DualProfileChat` (**not in this repo** — UNVERIFIED).

**The idea** (`:8-18`): WWDC 242 introduces `DynamicProfile` — *"inside a single
`LanguageModelSession` you declare multiple **profiles** (each a model + instructions + tools +
modifiers) and switch between them as the conversation moves. **Apple's example routes between
`SystemLanguageModel` (on-device) and `PrivateCloudComputeLanguageModel` (server).**"* But:

> Because `DynamicProfile.model(_:)` takes `some LanguageModel`, and any Core AI zoo bundle is a
> `LanguageModel` via coreai-kit's `KitLanguageModel`, the same API routes between **two local
> models** — a fast 0.6B for triage and a 4B for hard questions — **with no server, no PCC, in
> airplane mode. This is the configuration Apple's demo does not show. It works.**

**API surface, verified against the macOS 27.0 SDK** (`:21-38`):

```swift
struct RoutingProfile: LanguageModelSession.DynamicProfile {
    let router: Router            // your state: which profile is active
    let fast: KitLanguageModel
    let smart: KitLanguageModel

    var body: some LanguageModelSession.DynamicProfile {
        if router.route == .smart {
            Profile { Instructions("You are the expert.") }
                .model(smart).maximumResponseTokens(384)
        } else {
            Profile { Instructions("You are fast triage.") }
                .model(fast)
        }
    }
}
let session = LanguageModelSession(profile: RoutingProfile(...))
```

Available profile modifiers, enumerated (`:40-44`): `.model`, `.temperature`, `.samplingMode`,
`.maximumResponseTokens`, `.reasoningLevel`, `.toolCallingMode`, `.historyTransform`,
`.transcriptErrorHandlingPolicy`; lifecycle
`.onActivate / .onDeactivate / .onPrompt / .onResponse / .onToolCall / .onToolOutput`; and
`.modifier(_:)`. Shared state across tools and profiles via **`@SessionPropertyEntry`** (custom) or
the built-in `history` property.

**Four measured behaviours you must design around** (`:46-68`):

1. **The `body` is re-evaluated multiple times per turn** — *"**7 evaluations for 3 turns**. The
   framework reads it more than once to gather instructions and resolve the model. **Keep the body
   pure** — read your route variable there, never mutate state. Imperative work goes in lifecycle
   modifiers."*
2. **Lifecycle order on a switch**: `old.onDeactivate → new.onActivate → onPrompt → onResponse`.
   First entry into a profile fires `onActivate` before `onPrompt`.
3. **Switching models re-prefills the shared transcript on the newly active engine.** *"Each model
   has its own executor and KV cache … Measured (0.6B↔4B): **switch-in first-delta 2.35 s**
   (re-prefill ~106 tok + the 4B's reasoning), **switch-back 0.94 s**. Append-only KV reuse only
   helps across consecutive *same-model* turns."*
4. **Two resident models cost two footprints.** *"qwen3-0.6b + qwen3-4b: **~102 MB** with both
   bundles loaded but un-touched, rising to **~920 MB `phys_footprint`** after the turns run. Note
   `phys_footprint` is the **jetsam-relevant dirty number** and **excludes clean read-only-mmapped
   weight pages** — these are 4-bit bundles, so total mapped RSS is higher (**~2.4 GB+** of
   weights). The 86→920 MB growth is runtime KV / activation / Metal buffers, not weights paging
   in. **Report both numbers, labeled**, if footprint matters for your jetsam budget."*

**Routing decision: use guided generation, NOT a tool** (`:70-91`) — a direct, measured
disagreement with the WWDC pattern:

> **242's baton-pass flips the route from inside a *tool* the model calls. On the kit's upstream
> engine that path is unreliable**: small/thinking models emit tool-call JSON the framework rejects
> with `GenerationError.decodingFailure` ("failed to parse generated content"), **independent of
> the argument schema (verified with required, optional, and empty `@Generable` arguments)**. The
> reliable "the model decides" channel is **guided generation**.

```swift
@Generable struct RouterDecision {
    @Guide(description: "true if the request needs the deep/expert model…")
    var needsExpert: Bool
}
// One persistent session on the sequential engine:
let session = LanguageModelSession(model: routerModel)           // engineVariant: .sequential
let decision = try await session.respond(to: "Classify: \(q)", generating: RouterDecision.self)
router.set(decision.content.needsExpert ? .smart : .fast)
```

*"Guided generation runs on the **sequential** engine (one logits step per token): the output can't
leak the model's `<think>` reasoning and can't be malformed, and **that engine has no
over-generation pump**, so it's also free of the consecutive-turn KV hazard."*

**The two 242 patterns, fully local** (`:93-103`): **baton-pass** (collaboration over one shared
transcript; the tool-flipped form is what the kit can't do reliably, guided-classification routing
is the working equivalent) and **phone-a-friend** (consultation via a **short-lived child
`LanguageModelSession`** on the big model with an isolated transcript — *"The child's transcript
never merges into the parent's (verified: parent transcript = 1 prompt / 1 response)"*).

**Hard-won rules** (`:105-122`):
- **One engine, one session, for the engine's lifetime.** *"Two `LanguageModelSession`s over the
  same `KitLanguageModel` **corrupt the KV state** (the second resets the engine under the first).
  A per-turn fresh classifier session is the classic way to trip this — reuse one router session."*
- **Consecutive same-model plain-respond turns can crash** — *"D1 over-generation leaves post-EOS
  tokens in the cache; the next same-model turn's KV fast-path meets garbage."* Workarounds:
  alternate models, change the instructions each turn (*"inject a summary → the prefix changes →
  clean reset"*), or use guided gen. **← the third appearance of the D1 defect; here it manifests
  as a crash.**
- **A thinking model cut mid-`<think>` → `decodingFailure`.**
- **Prefer a single-profile `DynamicProfile` over `LanguageModelSession(model:instructions:)`** —
  *"the plain initializer's first respond can `decodingFailure` where the profile path is solid."*
- **Model choice matters**: *"qwen3.5 is a hybrid (GDN, 4 KV states) the upstream engine won't
  load; **VL decode bundles declare 4 per-token inputs and won't load either** (true vision routing
  needs an own executor + the vision encoder). Use plain Qwen3 catalog bundles."*

### 8.3 `evaluations-framework.md` — Apple's Evaluations framework, mapped to the zoo's gates

> ⚠️ **Caveat the doc puts on itself** (`:10-14`): *"Symbols (`subject(from:)`, `ModelSample`,
> `Metric`, `Evaluator`, `ModelJudgeEvaluator`, `ScoreDimension`, `TrajectoryExpectation`,
> `ToolCallEvaluator`, `SampleGenerator`) are **transcribed from talks — captions don't show
> code**. Concepts are verbatim; **confirm exact signatures in the docs**."* So treat every symbol
> name here as **UNVERIFIED** spelling. The *concepts* are the value.

Framework facts asserted (`:13-14`): **new in Xcode 27**, runs in **Swift Testing**, supports
**macOS/iOS/watchOS/visionOS**, and can run **on-device or against PCC**. Sourced to WWDC26
**298** (Meet Evaluations), **299** (agentic), **335** (hill-climbing), with **243** for the
Foundation Models Instrument and **319** for the PCC judge entitlement.

**The shared premise** (`:20-25`), quoting 298: generative models *"break a contract fundamental to
software testing"* — the same input can produce different outputs, so *"unit tests are
insufficient."* The zoo's independent answer to the same problem was the **margin rule + flip
budget**; Apple's is **scoring + aggregate thresholds**. *"Same insight, two altitudes."*

#### The API in one screen (`:29-50`)

- **`subject(from:)`** — runs the thing under test for one sample, returns the "subject".
- **`ModelSample`** — one input + an **expected** output. The dataset is `[ModelSample]`.
- **`Evaluator`** — per-sample closure over the subject's output → emits a **`Metric`** (pass/fail
  *or* a numeric score).
- **`aggregateMetrics(using:)`** — roll per-sample metrics into trends (mean, ratio, custom — e.g.
  Cohen's κ).
- **Run in a test**: `@Test(.evaluates(MyEval(), notes:))`; then
  `#expect(results.aggregateValue(...) >= target)`. *"That **threshold is your optimization
  target**."*
- **`ModelJudgeEvaluator`** — a *model* scores the output. Same protocol/`Metric` as a quantitative
  evaluator, *"so **mix them freely** in one evaluation."*
  - **`ScoreDimension`** — name + description + scale; *"use an **even** number of levels, e.g.
    1–4, so the judge can't park on a neutral middle; 'four levels = enough distinction without
    dilution'."*
  - **`ModelJudgePrompt`** — gives the judge app context + the expected value as reference.
  - *"Judge model should be **≥ as capable** as the model under test → 298 uses **PCC** to judge an
    on-device feature."*
  - *"**Rationales are the product** — read them; they tell you *why* a score happened."*
- **`SampleGenerator` / `makeSamples`** (299) — synthesize more `ModelSample`s. Knobs:
  `sessionProvider` (which model drives generation; PCC for big context), `samplingStrategy`
  (`random` | `slidingWindow`), `validator` (accept/reject → `samples` / `invalidSamples`).
  *"**Coverage > count.**"*
- **`TrajectoryExpectation` + `ToolCallEvaluator`** (299) — *"evaluate the agent's **path**, not
  just the answer: which tools, which arguments, in what order, and a **`disallowed`** set that
  must *not* appear."* Matchers: `naturalLanguage` (**intent, not string**), `contains`, `oneOf`,
  `pattern`, `range`; `unordered` when timing doesn't matter. *"These are themselves `@Generable`,
  so synthetic data works for them too."*
- **Xcode Evaluations report** — per-sample drill-down + a **Compare** button across two runs.

#### The correspondence table (`:54-65`) — the doc's core contribution

| Zoo gate (numeric/tensor layer) | Apple Evaluations equivalent (feature/behaviour layer) |
|---|---|
| **Oracle** = fp32/bf16 reference output | `ModelSample.expected…` (closed answer) **or** a **Model Judge** (open answer) |
| **Numeric parity gate** (cos = 1.0, bit-exact, `engine ≡ python`, 24/24 tokens) | a **quantitative `Evaluator`** over a fixed dataset returning pass/fail |
| **Margin rule** (a flip counts only if logit margin ≥ ~0.1; ties ignored) | a tolerance band inside a quantitative evaluator — *"in Apple terms it's 'score within ε', not 'assert equal'. **Encode the band in the `Evaluator`, not as an `==`**"* |
| **Flip budget ≤ N** / "24 of 24" | **optimization target**: `#expect(aggregateValue >= rate)` — *"identical math, native shape"* |
| **Busy-scene tolerance** (torch itself flips on 1e-4) | **drift** + judge rationale; *"our 'the oracle is unstable here' = Apple's 'raters disagree / the judge drifts'. **Measure it, don't pretend it's zero.**"* |
| **Device-verified RELEASE bench** | run the eval target **on-device**; pair with **WWDC 243** Instruments (TTFT / tokens-per-sec / total latency) — *"it **profiles any FM-framework model, including our `ZooFMProvider` models**"* |
| **Hill-climbing the quant scheme** (sym8 vs km8 vs km4 by flip-count) | **evaluation-driven development** + the **Compare** view; one variable at a time |
| *(no zoo equivalent yet)* | **`SampleGenerator`** synthetic data |
| *(no zoo equivalent yet)* | **Model judge + Cohen's κ alignment (≥ 0.6)** — *"evaluate the evaluator so it stays aligned as data grows"* |
| *(no zoo equivalent yet)* | **`TrajectoryExpectation` / `disallowed`** |

#### The altitude insight (`:67-81`) — the guide-worthy framing

> - **zoo gate**: *"Does the converted/quantized model emit the **same tokens** as the
>   high-precision reference?"* → **fidelity of the port** (tensor layer).
> - **Evaluations**: *"Does the **feature** behave as the user expects across a diverse dataset?"*
>   → **quality of the behaviour** (feature layer).
>
> *"They are orthogonal: a model can pass zoo gates (bit-exact port) and still flunk Evaluations
> (the base model is just bad at the task), or score well on a tiny Evaluations set yet be a broken
> port. **Run both.** zoo gates protect 'we shipped the model we think we shipped'; Evaluations
> protects 'the feature is actually good.'"*

#### Two carried findings (`:83-94`)

1. **`disallowed` `TrajectoryExpectation` is a deterministic prompt-injection test.** *"299's
   mechanism for 'the model must **not** call `findSimilarBooks`' is exactly the gate
   `agentic-security-checklist.md` §6 asks for: feed **poisoned context**, then assert the
   destructive tool is **absent** from the trajectory **and the parameters weren't rewritten**
   (`naturalLanguage` matcher on the recipient/target). This converts 'we mitigated injection' from
   a claim into a **number you can hill-climb**."*
2. **Watch judge drift; target Cohen's κ ≥ 0.6.** *"add app context + a **few** worked examples
   (too many → **overfit the alignment score**), and gate on κ ≥ 0.6 ('meaningful agreement')."*

#### Starter suite sketch (`:96-107`)

- **Quantitative**: retrieval hit-rate, answer-contains-citation, latency budget, route correctness.
- **Qualitative** (`ModelJudgeEvaluator`, PCC judge, 1–4): groundedness, helpfulness. *"Split the
  moment you disagree with a score (298: a broad question = two questions)."*
- **Trajectory**: ordered "search-before-answer"; `disallowed` destructive tools under poisoned
  context; no unexpected tool calls.
- **Data**: *"start 20–30 hand-written samples (298 best practice), then `SampleGenerator` to
  ~hundreds; **expect scores to DROP when the dataset grows (299) — that's the small set having
  flattered you, not a regression.**"*

---

## 9. Per-model porting write-ups (Tier 4)

Summaries extract the **transferable technique** and the **gotcha**, not the narrative.

### 9.1 The Gemma 4 cluster (five files)

#### `gemma4-wna8o8-requires-int8-activations.md` — ★ the most important quality finding in the whole archive

**Measured 2026-07-17. Ship-blocking.** Google's mobile QAT weights
(`google/gemma-4-E2B-it-qat-mobile-transformers`, bit-identical to the `.litertlm`) **lose roughly
half their reasoning accuracy when run with fp16 activations** — *"Running them at **higher**
arithmetic precision than they were trained for is what breaks them."*

Same weights, same 100 GSM8K questions, same prompt/greedy/extractor, same day (`:14-18`):

| Runtime | Activations | GSM8K |
|---|---|--:|
| **LiteRT-LM** (the `.litertlm`, as shipped) | **int8 static** | **86.0 %** |
| **Core AI** (the mixed-bit transplant) | fp16 | **48.0 %** |

Control: on the *other* official checkpoint (`-qat-q4_0-unquantized` → uniform int4, no activation
quantization in its recipe) **Core AI scores 88.0 % and MLX 87.0 %**. *"So the ~48 % is specific to
wNa8o8-on-fp16, not to Core AI and not to quantization in general."*

**Proof it is not a port bug** (`:26-42`): three *independent* fp16 implementations — the Core AI
export, an MLX oracle (plain `mlx_lm` dequant+load), and the raw-Metal kernel chain — produce the
**identically wrong** answers on the 12 questions where LiteRT succeeded (q0 gold 18 → all three
say **26**; q3 gold 540 → all **180**; q5 gold 64 → all **48**; q10 gold 366 → all **246**).
*"Not 'similarly bad' — **identically** wrong."* And the weights are verified bit-exact vs the
extraction (`max|Δ| = 0.0`, 312/313 tensors byte-identical).

**The mechanism, PROVEN by fake-quant** (`:44-56`):

> int8 **static** activation quantization clamps activations into a learned, fixed range. QAT
> trains the weights *with that clamp in the loop*, so **the clamp is not a precision loss to be
> recovered — it is a learned outlier suppressor the model depends on.** Run the same weights with
> fp16 activations and the clamp disappears, outliers propagate, and error compounds across
> reasoning steps. … The official checkpoint ships `input_activation_scale`,
> `output_activation_scale`, and `k/v_cache_scale`. **Our pipeline reads none of them. They are not
> optional metadata.**

**Two independent fake-quant harnesses, with ablations** (`:58-81`) — `clamp(round(x/s),-128,127)*s`
added to the pure-fp16 MLX oracle, scales read from the checkpoint, nothing else changed:

| Activations | 12-q set | GSM8K n=100 |
|---|--:|--:|
| fp16, no clamp (both harnesses reproduce the original per-answer exactly) | 2/12 | **48 %** |
| ablation: **KV-cache clamp only** | **0/12** | — |
| ablation: **linear in/out clamps only** | **9/12** | **88 %** |
| harness A — linear + KV clamps (checkpoint scales only) | 10/12 | **89 %** |
| harness B — + the TFLite-only `per_layer_model_projection` quant | 11/12 | 86 % |
| **LiteRT (control, true static-int8 graph)** | **12/12** | **86 %** |

*"The ablations put the learned suppressor at the **linear boundaries**: KV quantization alone
recovers nothing (**it even loses the two questions fp16 got right — noise without the
suppressor**), while the linear clamps carry 9 of the recovered points."*
And: *"**the clamp recovers the entire fp16 gap** … there is no second mechanism left to find."*

**The exact semantics any port must implement** (`:99-120`) — read op-by-op from the `.litertlm`
Section-10 decode graph, 21/21 scalars spot-checked against the checkpoint:
- All **activation** scales are **per-tensor scalars, zero-point 0** (weight scales are per-channel).
- **Quantization happens at linear boundaries only**: fp32 → quantize with
  `input_activation_scale` → int8 × int-weight matmul → requantize the result to int8 with
  `output_activation_scale` → dequantize → fp32. *"Norms, residuals, GELU, RoPE, softmax and the
  final logit softcap all run in float. q/k/v share one input quantize (their three input scales
  are equal); gate/up likewise."*
- **`k/v_cache_scale` is int8 KV-cache storage quantization**: K quantized **after k_norm+RoPE**,
  V **after value_norm**, at cache-write time; attention math runs in float on dequantized values.
  `v_cache_scale = 6/127` for every layer; `k_cache_scale` is learned per layer.
- **`lm_head` activation scales are 0 in the checkpoint = unquantized** (float activations into the
  int2 head, then softcap).
- Two gotchas visible only in the TFLite graph: `per_layer_model_projection` is *also*
  activation-quantized (`s_in=0.038878`, `s_out=0.002353`) but the checkpoint carries no scales for
  it (its weight is even plain bf16 there); and **`value_norm` is a real RMS norm with weight ≡ 1.0**.

**Why every gate missed it** (`:122-138`) — the methodological punchline, and the best single
paragraph in the corpus:

> `g4loop --gate` … is blind twice over: **(1) It tests 3 prompts**, all single-hop recall ("Why is
> the sky blue?", "What is the capital of France?", "Explain photosynthesis in one sentence") —
> *"The defect only shows in multi-step reasoning."* **(2) It compares against `oracle_refs.json`**
> — generated by the fp16 MLX oracle, *"i.e. a reference carrying the identical defect. '3/3 EXACT
> vs oracle' proves conformance to a degraded reference, not quality."*
>
> **"Every gate in the transplant chain has this shape … They are equivalence gates, not quality
> gates. An equivalence gate cannot detect a defect its reference shares — that is the whole
> lesson."**

**Consequences** (`:140-151`):
- *"**`gemma4-metal` ships a model that is ~half as good at reasoning as it looks.** The +24 % Mac
  speed and the iPhone LiteRT-parity claims stand; the quality does not."*
- *"**The byte-floor argument was incomplete.** '783 MB/token vs 2.0 GB → must be faster' left
  quality out. Measured on the Core AI standard runtime, mixed-bit loses on **both**: decode
  **70.6 vs 75.9 tok/s** (int2 unpack eats the bandwidth saving) and **48.0 % vs 88.0 %**."*
- *"**'Just publish the int4 weights' does not transfer a mobile QAT model.** The wNa8o8 weights are
  **half of a co-designed weights+runtime product**. This bounds what any third-party port of these
  weights can achieve."*

**The fix, implemented 2026-07-18** (`:168-202`): fake-quant at every linear boundary
(`s * clamp(rint(x * (1/s)), -128, 127)`, per-tensor checkpoint scales, input post-norm + output at
store) plus int8 KV-cache storage quant, in shared MSL kernels both harnesses compile.

| Runtime, same weights | GSM8K-100 | Decode tok/s (M4 Max) |
|---|--:|--:|
| raw-Metal, fp16 activations (before) | 48 | **157** |
| raw-Metal + int8-activation fake-quant | **73** | 140 |
| LiteRT-LM (true int8 arithmetic, control) | **85** | — |

*"The learned clamp restores **+25 points at ~11 % decode cost**."* The residual gap is **the
fake-quant method itself**: three independent fake-quant implementations (Metal reciprocal-mul 73,
Metal divide 75, MLX oracle 79) sit within binomial noise at n=100, while LiteRT's true int8
arithmetic (int8×int8 → **int32 accumulate** → requant) scores 85 above the whole family.
*"the per-op int32-accumulate/requant rounding is itself part of the trained numerics."*

**Two transferable engineering notes** (`:191-202`):
1. **"A token-exact gate is not a logit-exact gate."** The python and Swift engines compile the same
   MSL through different compilers (torch `mps.compile_shader` = **fast math**; `MTLLibrary`
   `.safe`). *"A bare `exp()` in the SDPA kernel lowered differently — **1-ulp context differences
   on ~0.05 % of lanes** that token gates never surfaced, because fp16 argmax margins absorb 1 ulp.
   The int8 activation grid makes argmax near-ties common enough that the dormant difference started
   forking tokens. **Namespace every transcendental (`metal::precise::`) in cross-compiler MSL.**"*
2. **"Quantize with `x * (1/s)`, not `x / s`, in hot loops."** *"An inner-loop divide cost **31 % of
   decode**; the reciprocal multiply is also what TFLite's own quantize kernels do."*

Plus a tooling landmine (`:210-212`): *"litert-mac-verify's `--max-tokens` is **TOTAL context**, not
a generation budget, and **undersizing it CORRUPTS output rather than truncating** (25-token input
at 30 → garbage)."*

#### `gemma4-raw-metal-port.md` — a fully hand-written Metal decode loop

**What shipped** (`:3-10`): Gemma-4-E2B on *"a fully hand-written Metal decode loop — **no Core AI
engine, no `.aimodel`, no MPSGraph**. A 2.18 GB mmap'd pack of Google's official QAT mixed-bit
weights (int2/int4/int8 + PLE tables) is driven by **5 hand-tuned kernel files and a ~250-dispatch-
per-token host sequence with on-GPU argmax**."* Lossless (token-exact vs the fp16 oracle) and at
**LiteRT-LM speed parity on iPhone 17 Pro** — same-afternoon interleaved A/B, 2026-07-15:
**raw median 53.7 vs LiteRT 50.5 tok/s; session best 56.2**. Mac M4 Max `S=1`: **124.1 tok/s**
(engine int4lin path: 82.4).

**The byte-floor argument** (`:22-29`): decode is bandwidth-bound. The shipped int4lin engine bundle
reads ~2.0 GB/token; the QAT mixed-bit weights read **783 MB/token** — *"but the stock engine graph
cannot express the int2/int4/int8 mix + PLE gather at full efficiency (**36.5 tok/s on iPhone =
28.6 GB/s effective**). The raw loop exists to harvest the missing bandwidth: **36.5 → 55–56 tok/s
(43.8 GB/s effective vs LiteRT-LM's 44.6 = 98 %)**."*
(Read this together with the wNa8o8 file above, which shows the *quality* half of the argument was
missing.)

**Techniques worth stealing**:
- **The pack format** (`:33-39`): every tensor already in **kernel layout** (quantized words `qp`,
  scales `sc`, biases `bi`, per-layer norms, PLE tables, packed embeddings, rope inv-freq tables),
  **64 B aligned, mmap'd into ONE `bytesNoCopy` MTLBuffer** — *"load = mmap + JSON parse, weights
  never copied."* The shipped variant is **interleave-4**: *"QP words of 4 consecutive rows sit in
  one `uint4` for single-16 B-load fetches; per-row word values and dot order are unchanged, **so
  bit-exactness proofs carry**."*
- **Token-dependence resolved entirely on GPU** (`:46-49`): *"~253 dispatches/token … the argmax
  writes the next token id into the token buffer the next step's embed-gather reads — **the CPU
  never touches the token chain**. Steps are encoded **8 per command buffer, 3 CBs in flight**."*
- **Cross-turn KV prefix reuse in the raw loop** (`:50-55`) — *"longest common prefix with the
  previous call is not re-prefilled — **the kit `ChatSession` `trimKVCache` contract maps straight
  onto it**."* ← another `trimKVCache` connection.
- **Batched prefill with bit-exact widening** (`:56-70`): M=8 default (16/8/4 widest-fit + `S=1`
  remainder). *"`m8/m16` widenings **keep every output scalar's EXACT `S=1` accumulation order**
  (loop staging is the only difference), so chunked KV is **byte-identical to `S=1` KV** — proven by
  a KV cache byte-compare."* Measured Mac M4 Max m8: **553–560 @p128 / 508–510 @p512 / 464–465
  @p1024** (+24 % over m4 chunks, ≈4.5× over `S=1`). **iPhone: m8 ≈ m4 parity — "the A19 prefill is
  ALU/clock-bound well above its byte floor, so width alone doesn't pay there."**
  Variants **measured and rejected** (kept in-file, off by default): m16 (register spill on both
  GPUs), staged bodies `_m8s/_m16s`, byte-LUT int2 `_m4l/_m8l` (*"decode's LUT win does not transfer
  to the wide lane"*).
- **⚠️ A19 prefill numbers are DVFS-ramp dependent** (`:71-81`, 17 single-variable runs): *"a p347
  prefill launched from device-idle **finishes before the GPU clock ramps (66–68 tok/s)**; a p~1000
  prefill ramps mid-run (**87**); runs launched right after sustained UI interaction hit **~95–102**.
  Thermal, Low Power Mode, cable vs battery, screen state and brightness were all eliminated as
  causes. **Quote the pair '≈87 tok/s @p1k / 66–68 @p347 cold-start' — never a pre-ramped burst
  number alone.**"* And a diagnostic: *"Byte-bound decode barely moves between regimes (51–52
  @ctx≈380), which is also the **thermal tell**: decode sliding below ~51 means the device is
  genuinely warm."*
  **← One of the sharpest benchmarking-hygiene findings anywhere in this corpus.**

**Discipline (do not relax)** (`:82-93`):
1. **`mathMode .safe` + literal op sequences.** *"Fast math contracts/reassociates fp16 chains
   differently per kernel shape; near-ties then fork. **This bit twice.**"*
2. **Kernels version with the HOST, not the weights** — they ship inside the app/kit bundle, never
   next to the pack on HF.
3. *"**The gates are the only proof.** tok/s claims come from settled fresh trial-1 runs;
   losslessness claims come from the S1 token gate, **never from eyeballing text**."*

**Known limits** (`:95-114`): **greedy only** (*"argmax on GPU; no logits surface, no sampling, no
guided gen"*); prefill chunked not GEMM-tiled (*"still well below LiteRT-LM's wide-batch prefill
(452–3 250 tok/s)"*); a **fused wide prefill lane was built, gated bit-exact, measured and KILLED at
−34 % Mac / −40 % A19** — *"the fold recomputes at least once per threadgroup vs once globally …
in an ALU-bound lane that always exceeds the ~1–3 % dispatch savings (the `S=1` fused lane wins only
because decode is byte-bound and the fold ALU hides under the weight stream)"*; MTP stays **off on
iPhone** (48.0 < `S=1`'s 55.9 on A19, though it wins on Mac 181.9 vs 124.1); E2B only, ctx 4096.

#### `gemma4-raw-metal-a19-levers.md` — what actually moved the needle on A19

iPhone 17 Pro, Gemma4 E2B mixed-bit (783 MB/token), fresh settled trial-1, greedy, p128 g256, **all
lossless** (`:13-19`):

| Config | Decode tok/s |
|---|---|
| Core AI pipelined engine (shipped) | 36.5 |
| raw loop, session 1 (M4-tuned kernels) | 47.7 |
| raw loop, session 2 (**A19-tuned**) | **55–56.2** (day noise ±1.4) |
| LiteRT-LM (single historical measurement) | 57 |

**What moved it, largest first — all bit-exact by construction** (`:24-50`):

1. **Constant-memory byte-LUT for the int2 decode (+~4.3 tok/s).** The int2 gate/up (16 codes/word ×
   2 matrices, ~6 ops/code) measured **23.4 GB/s CACHE-HOT on A19 = ALU-bound, ~42 % of the token
   from ~24 % of the bytes.** `constant half4 LUT2[256]` (byte → 4 decoded values) → **59.8 GB/s**;
   int2 down 50.8 → 80.4. Bit-exact because *"products x·c with c ∈ {−2,−1,0,1} are EXACT in fp16
   and the fp32 accumulation stays in code order."* And a **retraction**: *"The 2026-07-03 'kernels
   are BW-bound at 43.5, tuning closed' verdict was a **probe-mix artifact**."* Note the *banned*
   variants: *"threadgroup byte-LUT, shl-asr die on the tg-gather — **the constant cache is the
   working lane**."* And `lm_head` int2 is genuinely DRAM-bound (40.6 GB/s) so the LUT is neutral
   there.
2. **Dispatch-count fusion, 452 → 253 per token (+~3 tok/s).** The measurement that justifies it:
   > **"A19 charges ~8 µs per dispatch ON the GPU timeline even with no hazards** (dep chain 8.5 µs,
   > independent 8.0 µs — **issue rate, not fences**; **M4 ≈ 3 µs**; decode wall == gpuBusy, CPU
   > contributes zero)."

   **← A hard per-dispatch cost number for A19 vs M4. Extremely useful and I have not seen it
   published elsewhere.** Folds used: residual-add rmsnorms into the next matvec prologue, q/k/v
   single dispatch, q-rope/k-rope/v-norm merged into the SDPA dispatch (*"key `pos` is the owner
   subgroup's last strided iterate, so **the online-softmax order is preserved exactly**"*).
3. **A19-specific tile/G retune (+~2.3).** *"M4's R=1 matvec lane is an **A19 regression** → R=4;
   sliding SDPA G 16 → 8. **Decode-G and verify-G must MATCH** (G changes the fp32 strided-merge
   order; MTP losslessness needs verify == S1 bitwise)."*
4. **`char4` int8 weight loads** (PLE + model_proj) — *"1 B scalar loads are issue-bound"* — small
   but free.
5. **Interleave-4 pack: ~0 gain** — *"the flat layout was already 128 B-coalesced per SIMD-group.
   Kept … but **do NOT expect speed from wide loads here again**."*

**Traps** (`:52-62`):
- **fp16 op-sequence trap, 2nd sighting**: *"writing rope as `c*x1 - s*x2` instead of the reference's
  explicit `m1=c*x1; m2=s*x2; … m1-m2` let the Metal compiler **contract to FMA even under
  `mathMode .safe`** → near-tie drift. **RULE: copy the reference kernel's op sequence LITERALLY,
  temporaries included.**"*
- **Thermal protocol**: *"back-to-back device runs droop 5–10 %; **'20-min-cold' does NOT measure
  faster than mid-session (tested)** — day noise is ±1.4 tok/s. Fresh = trial-1 of a settled run,
  and **cross-config claims need interleaved A/B, not different-day numbers.**"*
- **Per-kernel BW probes on small tensors read CACHE-HOT on A19** — *"SLC swallows 5–10 MB tensors ×
  reps — only ≥ 100 MB streams (lm_head) give true DRAM numbers."*

**Wall decomposition at 56 tok/s** (`:66-67`): *"exec ≈ 16.0 ms (≈ DRAM-stream levels everywhere
after the LUT) + **dispatch tax ≈ 1.8 ms (253 × ~7 µs)** + thermal band ±0.5 ms."* The parked
"mega-kernel restructure (LiteRT-style whole-layer single dispatches)" is estimated at *"up to +5,
uncertain — a PROJECT, not a lever."*

#### `gemma4-ple-static-input-fm-stack.md` — running Gemma 4's PLE table behind FoundationModels

**The problem** (`:3-8`): *"Gemma 4's small models (E2B / E4B) carry a non-standard extra input: a
giant **per-layer embedding (PLE) table** the decoder gathers from once per token — **the text-model
analogue of a VL decoder's `image_embeds`**. A stock text load path declares only `input_ids` /
`position_ids` (+ KV states), so it can't feed the PLE table and the engine rejects the bundle."*

**Two bundle forms** (`:14-25`): **provider mode** (a per-token `PerTokenInputProvider` fills the PLE
gather each step) vs **`…_tbl` / static mode** (*"the PLE table is exported as a **graph input**
(`ple_table` [vocab, ld·layers] int8 + `ple_scale` [vocab] f32), gathered **in-graph** by
`index_select` on `input_ids` (the `q·s·√ld` scaling is in-graph, bit-exact). The head (tied lm_head
+ final softcap) is fused into the same graph, so the engine samples logits directly."*).
**Recommendation: use `…_tbl`.**

**The wiring** (`:29-52`) — this is exactly the fork's `EngineOptions.staticInputBuffers` (§2.2):

```swift
setenv("COREAI_CHUNK_THRESHOLD", "1", 1)   // BEFORE the engine reads ModelConfig.chunkThreshold

let buffers: [String: StaticInputBuffer] = [
  "ple_table": StaticInputBuffer(ownedBuffer(tablesDir + "/embed_per_layer.i8")),
  "ple_scale": StaticInputBuffer(ownedBuffer(tablesDir + "/embed_per_layer.scale.f32")),
]

let bundle = try LanguageBundle(at: decoderDir)
let config = ModelConfig(name: bundle.name, tokenizer: bundle.tokenizer,
  vocabSize: bundle.vocabSize, maxContextLength: bundle.maxContextLength,
  serializedModel: [bundle.modelAssetPath], function: "main")
let engine = try await EngineFactory.createEngine(
  config: try JSONEncoder().encode(config),
  modelURL: try bundle.requireModelURL(for: "main"),
  options: EngineOptions(staticInputBuffers: buffers))   // ← the one line that unblocks Gemma
```

**A non-obvious perf note** (`:33-35`): *"Read each PLE table file once into an **OWNED
`storageModeShared` MTLBuffer** (**owned beats a read-only mmap here — a no-copy mapping pays a
large per-encode residency tax**, and these are bound on every step). ~2.35 GB for E2B."*
**← directly contradicts the usual "mmap, never copy" instinct, and the reason is per-encode
residency. Worth a callout.**

Also: keep the buffers alive for the engine's lifetime; *"Do **not** call `engine.warmup()` (it warms
query length 256, which the `S=1` graph rejects — **a 1-token generate after load is the warmup**).
A QAT bundle must be paired with the **QAT** PLE tables."*

**Gemma 4's chat format is NOT Gemma 3's** (`:60-83`) — a concrete, citable format spec:
- Turns framed by **`<|turn>` (105) … `<turn|>` (106)** — **not** `<start_of_turn>`/`<end_of_turn>`.
- Reasoning rides a **`<|channel>thought\n … <channel|>` (100 … 101)** channel.
- `<eos>` = 1, `<bos>` = 2.
- The stock `google/gemma-4-E2B-it` tokenizer has **no embedded chat template**, so render:
  ```
  <bos>
  <|turn>system\n{system}<turn|>\n        # only if instructions are present
  <|turn>user\n{user}<turn|>\n
  <|turn>model\n                          # generation prompt
  ```
- **Gotcha 1**: *"**Emit `<bos>` yourself** — Gemma's tokenizer post-processor does not add one."*
- **Gotcha 2**: *"**Do NOT pre-inject an empty `<|channel>thought\n<channel|>` 'thinking-off'
  channel.** The jinja's thinking-off path injects it, but on this bundle that **triggers** a verbose
  reasoning block; ending the prompt at plain `<|turn>model\n` yields a direct answer."*

**Memory / device** (`:87-94`): E2B `…_tbl` ships **Mac + iPhone** — *"iPhone 17 Pro: **2.35 GB
tables → ~4.4 GB peak** vs the **~6.44 GB entitled jetsam limit** (needs the **increased-memory
entitlement**). **The ~2 GB-constants graph crashes the on-device specializer** → ship the AOT
`…_tbl_aotc_h18p` `.aimodelc`. Verified: greedy 8/8 vs HF, decode 30.3 tok/s / prefill 38.9."*
E4B `…_tbl` is **Mac-only** (55.8 tok/s); on iPhone the E4B path is **provider mode** (mmap PLE,
~2.2 GB footprint, decode ~15 tok/s) — *"the first 4B-class Gemma on an iPhone in this project."*

**Net** (`:98-101`): *"The only thing standing between Gemma 4 and the standard text path is two
extra graph inputs. Bind them as constant static buffers and Gemma 4 runs behind
`LanguageModelSession` like any other local model — so **'Ask Gemma 4' from Siri / App Intents is
just a model swap**. Same `EngineOptions` hook the VL executor uses for `image_embeds`."*

#### `gemma4-litertlm-to-official-migration.md` — provenance laundering, done right

**Status**: source migrated + proven bit-exact 2026-07-17.

The mixed-bit QAT weights that make the raw-Metal engine hit LiteRT parity were originally obtained
by **reverse-engineering Google's LiteRT binary**: download
`litert-community/gemma-4-E2B-it-litert-lm`, crack the `.litertlm` container with
`litert_lm_builder.litertlm_peek`, and pull the quantized tensors out of the embedded TFLite
subgraphs. *"It worked and was bit-exact, but shipping that recipe meant publishing 'how to crack
Google's binary' — **awkward provenance for a public port**."*

**2026-07-15 Google published the same weights as a plain 🤗 Transformers checkpoint**:
`google/gemma-4-E2B-it-qat-mobile-transformers` (Apache-2.0, `quant_method: "gemma"`, the wNa8o8
mobile schema). *"This is the same QAT run, released in a standard, redistributable format — so the
extraction can be replaced by a normal `safe_open` read of an official checkpoint."*

**The swap carried zero risk because it was proven bit-exact first**: `max|Δ| = 0.0`, **312/313
tensors byte-identical**.

> **Transferable lesson**: when you must reverse-engineer to port, keep the extraction *provably*
> equivalent so that the moment an official artifact appears you can swap the provenance without
> re-validating the port. Also a nice data point on vendor behaviour: **Google published the mobile
> QAT weights in HF format ~mid-2026**, making the crack unnecessary.

### 9.2 Ternary / 1.58-bit ports

#### `bitcpm-ternary-1.58bit.md` — BitCPM-8B, the zoo's first sub-int8 kernel

**Result**: MiniCPM4-8B QAT'd to ternary {−1,0,+1}, running on the **iPhone 17 Pro GPU at 17 tok/s
decode in ~2.1 GB resident** (*"an 8B at a 4B's footprint"*); M4 Max **62.7 tok/s**.

**Technique — recovering ternary from TQ2_0 GGUF** (`:8-19`): the HF `main` repo ships the **bf16
latent master** (standard MiniCPM modeling, no BitLinear) — *"running it as-is is full-precision, not
ternary."* The ship truth is `bitcpm4-8b-tq2_0.gguf` (2.37 GB). TQ2_0 (llama.cpp) = per **256-element
block** along the reduction axis K: each weight is a 2-bit code in {0,1,2} → value `(code−1)`, times
one fp16 scale `d` per block. `gguf.quants.dequantize` handles TQ2_0 / Q4_K / Q6_K directly.
Recovery from a dequantized `W[N,K]`: **`d_block = max(|W| in block)`** (*"exact — the nonzero
magnitude **is** `d`"*), `code = round(W/d)+1`.
Note the mixed precision: *"Only the **224 transformer linears** are TQ2_0. The **embedding is Q4_K**
and the **untied LM head is Q6_K** — BitNet practice keeps those higher-precision."*

**The kernel** (`:21-32`) — *"the int4-k-means matvec minus the codebook"*: pack **16 ternary codes
per uint32**; decode block = **512 K** (32 lanes × 16 codes/lane, and 16 | 256 so a lane's codes sit
inside one scale block); dequant is `(code−1)` so *"the matvec is a sign-add/subtract"*, no codebook
gather, no LUT. **Per-lane scale before `simd_sum`**, justified by linearity:
`Σ_k x_k·d_b·(q_k−1) = Σ_b d_b·Σ_{k∈b} x_k·(q_k−1)`. Constraints `K % 512 == 0`, `N % 32 == 0`.
Numerics: **bit-identical to the gguf dequant (maxerr 0)**; engine output token-identical to torch,
3/3 greedy.

**⚠️ The key trap — `M=1` kernel ⇒ `S=1` static-ids export** (`:38-51`):
> The ternary kernel is **M=1** (single-row decode matvec). A **dynamic-`input_ids`** export lets
> prefill run **`S>1`**; the kernel's `x.reshape(s,k)` then produces a dynamic-row tensor MPSGraph
> can't constrain, and lowering fails at engine-compile:
> ```
> error: 'mps_spi.copy_discarding_constraints' op input must have tensor constraints
> ```
> Fix: export **`--static-ids`** — `input_ids` pinned to `[1,1]`, `position_ids` + KV dynamic.
> Prefill then runs as pipelined `S=1` steps under `COREAI_CHUNK_THRESHOLD=1` ("prompt tok/s ≈
> decode tok/s"). `position_ids` must carry the **full length** (attention offset = `seq_len − 1` =
> the KV write slot).

**Harness gotchas for an `M=1` static bundle** (`:53-65`):
- **`llm-runner` cannot drive it** — `--raw-tokens` / `--prompt` always attempt a multi-token prefill
  (256-tok specialization) vs the static `[1,1]`:
  `NDArrayDescriptor: Shape at dimension 1 of 256 is not a valid substitution for source shape 1`.
- `llm-benchmark` runs it (speed only).
- **Token gate = the Python `coreai.runtime` API**, and **load the `.aimodel` directly** — *"a bundle
  dir's hand-written outer `metadata.json` lacks `assetVersion`; the inner `.aimodel`/`.aimodelc` has
  it."* The decode contract from `fn.desc`: inputs `[input_ids, position_ids]`, **state
  `[keyCache, valueCache]`**, output `[logits]` — *"the state NDArrays mutate in place across steps."*

**iPhone deploy traps** (`:68-77`): a `TorchMetalKernel` graph **survives AOT** for the iPhone GPU
(ANE unsupported). *"the AOT load stages the precompiled MPSGraph package into
`Library/Caches/coreai-cache` — needs ~3 GB free; **a near-full device fails ENOSPC, and the partial
stage pollutes the content-keyed cache** → next launch fails `Code=2` (No such file). **`devicectl`
has no file-remove; the clean reset is uninstall → reinstall → re-copy → relaunch.**"*
Measured: decode 17 tok/s, prefill 13 tok/s, resident ~2.1 GB, headroom 4.3 GB, no jetsam, cold load 9 s.

**The strategic rationale** (`:80-84`), worth quoting in a positioning guide:
> *"The 2026 MLX surge on Apple Silicon makes 'match MLX on a Mac' a moving target. **The durable
> Core AI edge is a kernel MLX structurally lacks** (its quant is 4/8-bit affine — there is no 2-bit
> ternary GEMM) **on a device MLX doesn't ship to**. 1.58-bit on iPhone is both."*

#### `bitvla-1.58bit-vla.md` — BitVLA, first VLA/robotics + first ternary multimodal

Port of `lxsy/bitvla-bf16` (arXiv 2506.07530, MIT): BitNet-b1.58-2B LLM + BitSigLIP-SO400M vision,
**image + instruction → 7-DoF robot action**, on the iPhone 17 Pro GPU, reusing the BitCPM kernel.

**Checkpoint archaeology** (`:9-24`): a **bf16 latent master** (quantized on the fly), structured as
LLaVA. *"There is **no action head and no proprio** in the base model — those live only in the LIBERO
OFT fine-tunes."* The base is the OXE-pretrained autoregressive policy generating **7 discrete action
tokens from the 256-token tail of the vocab**. *"The OFT path (`use_bi_attn=True`, bidirectional
parallel decode + regression head) is for the LIBERO fine-tunes — do **not** use it for the OXE base."*
Quant formulas: **WeightQuant** = per-tensor absmean `round(W·s).clamp(-1,1)/s`, `s = 1/mean(|W|)`;
**ActQuant** = per-token int8 `round(x·127/max|x|).clamp(-128,127)/(127/max|x|)`. Both LLM and SigLIP
linears use **W1.58-A8**.

**Generalizing the ternary kernel** (`:26-37`): BitCPM assumed `K % 512 == 0`, `N % 32 == 0`; BitVLA
breaks both (LLM `down_proj` K=6912, SigLIP K ∈ {1152, 4304}, fc1 N=4304). Generalization: arbitrary
K (only `K%16` for packing) with a per-lane `k0 < K` guard zeroing the tail; **N padded** to a
multiple of 32 (padded rows computed then sliced); **per-tensor (per-row) scale** for BitNet's
absmean (vs BitCPM's per-256-block), `D` is `[N,1]`. `BitLinearMetal` applies **ActQuant before the
kernel**, so it equals `F.linear(ActQuant(x), WeightQuant(W))` exactly.

**⚠️ A superb bug** (`:39-43`):
> The per-row scale buffer must be torch **`[N,1]`, not `[1,N]`**. **The DSL reverses axes**, so the
> Metal `D[0, n]` reads `torch d[n,0]`. **The torch reference (`d.reshape(-1,1)`) is shape-agnostic
> so CPU passed either way — but the Metal kernel read out-of-bounds and produced NaN logits on the
> engine.**

**← A perfect illustration of why the reference implementation can silently mask a kernel bug.**

**VLM splice + action decode** (`:45-57`):
- **`inputs_embeds`, not `input_ids`.** *"The LLM decode graph takes `inputs_embeds[1,1,2560]`; the
  host builds the sequence (text embeds + 256 projected vision embeds) and feeds it
  position-by-position (static-ids `S=1`)."*
- **Action-head slice**: the model only emits the 256 tail tokens, so slice the LM head to rows
  `[128012 : 128268]` → **656 MB → 1.3 MB**, and decode `argmax j` → token `128012+j`.
  **← a very cheap, very large memory win from an application-specific vocabulary restriction.**
- **Detokenize** (OpenVLA): 256-bin centers over [−1,1];
  `bin = clip(total_vocab − token − 1, 0, 254)`; then BOUNDS-Q99
  `0.5·(b+1)·(q99−q01)+q01` from the config `norm_stats` (27-dataset OXE mix, pick an `unnorm_key`).

**Cheap-oracle validation** (`:59-68`): run the official bundled **transformers fork** in an isolated
venv (`python -m venv --system-site-packages`, `pip install -e transformers --no-deps`,
`pip install "tokenizers>=0.21,<0.22"`), reconstruct with
`LlavaForConditionalGeneration(LlavaConfig(**config.json minus norm_stats/n_action_bins/auto_map/
architectures))` + `load_state_dict` = **0 missing / 0 unexpected**. Results: vision per-token
**cos 0.9994**, full-pipeline action **6/7 tokens** with ~identical 7-DoF.

**On-device gotchas** (`:70-87`) — *"the part that took the longest"*:
- **The custom Metal kernel cannot JIT on device.** Plain `.aimodel` low-level load
  (`AIModel(contentsOf:)`) crashes the on-device compiler (`LLVM ERROR: cannot unwrap empty
  odiec_module_t`). **It must be AOT-compiled.** *"(Standard-op graphs like the vision tower JIT
  fine.)"*
- **Loading the AOT `.aimodelc` low-level requires `expectFrequentReshapes = false`** — *"The
  dynamic-shape LLM compiled with `--expect-frequent-reshapes` then loaded with `=true` fails
  `POSIX Code=2`; with `=false` it loads."* (Consistent with §5.2's VibeVoice finding: **it is the
  load-time option that matters**.)
- **Vision A8 act-quant stalls the iPhone GPU** — *"With the in-graph per-token round/amax activation
  quant, **the first vision forward hung > 10 min on h18p**. Dropping vision to **fp16 activations**
  (ternary weights still baked; cos 0.997) runs in ~0.1–2.7 s."*
- **Always pass `--architecture h18p`** — *"omitting it emits all ~20 Mac GPU archs (**34 GB**)."*
- *"Device install/launch need the screen **unlocked** (`CoreDeviceError 4016` = locked; set
  Auto-Lock = Never). Clear the captured `--console` log between runs (stale-log false alarms)."*

### 9.3 Generative-audio and vision ports

#### `chatterbox-port.md` — zero-shot voice-cloning TTS, four networks + host DSP

The zoo's first zero-shot voice-cloning TTS and first multi-network generative-audio pipeline
end-to-end on iPhone: *"~2 s of compute yields 2.16 s of audio, no server."*

| Net | Role | Core AI form |
|---|---|---|
| **T3** | AR speech-token LM (Llama_520M, embeds-in) | **int8** stateful graph, KV cache |
| **S3Gen encoder** | speech tokens → mel-conditioning `mu` | static graph (bucketed) |
| **S3Gen estimator** | CFM flow-matching velocity UNet1D (CFG batch-2) | **fp16** static graph (bucketed) |
| **HiFT** | vocoder: f0-predictor + HnNSF source + conv trunk | 2 graphs + **host** STFT/iSTFT/source |

**Device-verified numerics (iPhone 17 Pro GPU vs Mac/HF)** (`:23-30`): T3 prefill logits cos
**0.99994** / argmax exact; T3 decode (KV-grow) cos **0.99998** / argmax exact / **29 ms/token**;
S3Gen encoder cos **1.00000**; **CFM estimator cos 1.00000 (fp16, 150 ms/step vs 3.3 s fp32 = 22×)**;
vocoder wav cos **0.9998**. Full pipeline speech-tokens→wav on device: wav cos 0.9998 vs Mac, ~6 s.

**Findings** (`:34-69`):
- **fp16 is the estimator's ship lever, not int8.** *"`export_to_coreai(model.half(), half_inputs)`
  works and lands 150 ms/call at cos 1.000000 — the earlier 'fp16/int8 export fails' was **a bug in
  the *reference* computation (`.float()` on fp16 inputs)**, not the export."*
  And: *"**Step-count reduction is a false economy**: wav-vs-10-step cos falls 8→0.958 / 6→0.814 /
  4→0.443; with fp16 speed you keep all 10 steps."*
- **The T3 needs CFG + sampling; greedy degenerates.** *"Greedy argmax (even with CFG) locks into a
  repeated token and **never emits stop**."* Shipped recipe: CFG `cfg_weight 0.5` with **two KV
  caches** (cond = cond-prefix+text+speech; uncond = the same with the **text-token embeddings zeroed
  but their positional embeddings kept**; `logits = cond + 0.5·(cond − uncond)`) + sampling
  (temperature 0.8, repetition-penalty 1.2, top-p 0.95).
- **The graph position-id convention is full-range.** *"A decode step passes `position_ids = [0…P]`
  (length processed+q), **not** `[P]`; `offset = len(position_ids) − q` selects the new token.
  Getting this wrong on the *reference* … produced a phantom 'KV-grow mismatch' until both sides used
  the same convention."* (Matches `coreai-torch-041-ir-incident.md:81-82`.)
- **Static shapes + bucketing beat dynamic export.** Neither the Conformer encoder nor the HiFT trunk
  exports cleanly with `torch.export.Dim`. *"Export encoder@256 tokens and estimator@512 mel; **pad
  the tokens and pass the real `xs_lens`** (encoder masks the padding → real-region `mu` cos 0.9996);
  **pad `mu`/`z`/`cond` to the bucket with `mask=1` only on the real region** (CFM real-region mel cos
  1.0)."*
- **`reflection_pad` is load-bearing**: *"Omit it and the source/`x` lengths align only at the traced
  length (fine at T=112, cos 0.9998) but **broadcast-fail at any other bucket**."*
  ← a bug that only appears at the *second* bucket.
- **`ELU` doesn't lower** — swap for the identity `where(x>0, x, expm1(x))` before export (cos 1.0).
- **⚠️ `~/Library/Caches/coreai-cache` serves stale compiles at the same asset path** — *"always clear
  it after re-exporting to the same directory, **or a fixed graph reports its predecessor's
  numerics**."* **← a devastating debugging trap; worth a callout in any guide.**
- Device: `inputs_embeds` and KV states are **Float16**; *"`devicectl copy to` into an existing
  directory does **not** reliably add new files, copy new `.bin` individually."*

#### `esam3-port.md` — EfficientSAM3, a port that was DROPPED (and why that's the interesting part)

**Outcome: dropped (KEEP-LOCAL).** *"The port worked end-to-end and was device-verified, but it was
redundant: the zoo already ships the full official Meta SAM 3."* An honest record of the **EDGE/GAP
gate applied after the fact**.

**Why it was dropped — the value gate, not a technical failure** (`:13-27`). Coverage sweep on the
**HF reference model** (threshold 0.05, all raw scores), checkpoint
`efficient_sam3_repvit_m1.1_mobileclip_s1_ft`:
- **Fires**: `a wheel`, `a tire`, `a window`, `a shoe`, `a sneaker`, `a foot`.
- **Empty (all scores ~0)**: `a car`, `a truck`, `a vehicle`, `bottle`, `banana`, `apple`, `person`,
  *"and everything on a cluttered groceries photo."*
- **Article matters**: *"`a window` fires but bare `window` → empty; `a tire` fires but `tire` →
  empty."*

*"So this **distilled** checkpoint segments a narrow, part-level concept set — **the 'segment
anything by text' pitch does not hold for it**. The coverage loss comes from shrinking SAM 3's text
encoder **354 M → MobileCLIP-S1 42.5 M**."*
**← A concrete, measured warning about distilled open-vocab models: the distillation silently
narrows the vocabulary, and the model does not tell you.**

**Seven transferable techniques** (`:52-74`), all validated before the drop:
1. **Cross-venv export**: `torch.export` the sub-module *in the model's venv* → `torch.export.save` →
   load + `TorchConverter` in the coreai venv (same torch 2.9.0; the `ExportedProgram` transfers; the
   model package is not needed there). **⚠️ Engine int inputs must be int32 (int64 → `CoreAIError 3`).**
2. **DETR data-dependent guard** → set `torch.compiler.is_dynamo_compiling = lambda: True`
   (+ `torch._dynamo.is_compiling`) before export, so the decoder takes the trace-friendly cached
   branch instead of comparing symbolic feat-sizes (`Eq(u0,1)` guard failure).
3. **Geometry-encoder stub**: for text-only PCS the geometry encoder emits a constant dummy token but
   its box/point paths use `torchvision.roi_align` + `grid_sample` + `scatter` — *"which Core AI
   can't lower and which fail to **deserialize** in the coreai venv (no torchvision). Capture the
   dummy output once, replace `model.geometry_encoder` with a stub returning those constants."*
4. **pos_enc = data resource, not a graph output.** Fixed constant for the 1008² input (~111 MB).
   *"Emitting it from a graph bloats the bundle (+115 MB) **AND broke GPU load**; ship it as a
   `pe{0,1,2}.bin` resource."*
5. **`lang_mask` = float input, not bool** — *"Core AI `TensorValue` has **no bool**. Export taking
   `lang_mask` as float32 and cast `>0.5` internally (bool graph input → device `dtypeMismatch`)."*
6. **Generate `tokenizer.json` from the model's own vocab** — sam3's `SimpleTokenizer` is standard
   OpenAI CLIP BPE (vocab 49408, sot 49406 / eot 49407); emit `tokenizer.json` from its `encoder` +
   `bpe_ranks` so a Swift CLIP tokenizer reads the exact vocab (*"parity by construction"*).
   *"Note: it **pads with 0**, not eot, so the `(tok!=0)` mask works."*
7. **Swift mask overlay**: draw each mask as a **tinted-RGBA CGImage** and `ctx.draw` it — *"NOT
   `clip(to:mask:)`+fill-full-rect (washes the whole frame). In a top-left-flipped context, **flip the
   mask rows**."*

Gates that passed: per-graph vs HF oracle cos 1.0 (all 3); end-to-end vs HF `truck`+"wheel" → 2
detections, scores exact, **mask IoU 1.0** on CPU and Mac GPU; iPhone 17 Pro in-app "a wheel" → 2
wheels, scores ≈ Mac (±0.001 fp16), **warm ~738 ms**, iOS h18p AOT. Ship dtype **fp32** —
*"(rf-detr precedent; DETR resists a clean `.half()`)."*

#### `depth-anything-3-monocular-depth.md` — the Track-V archetype

DA3 (ByteDance, Apache-2.0): DINOv2 ViT backbone + DPT-style dense head. *"DA3 is an 'any-view'
model (1→N views); fed a **single view (S=1)** it is a monocular depth estimator."*

**Why `S=1` "just works" as a static graph** (`:18-20`) — a nice trick for any-view models:
*"the cross-view **global attention collapses to self-attention** (s=1), the reference-view reorder
is **statically dead** (it needs S ≥ a threshold), and the camera token is a **fixed parameter** —
no data-dependent control flow survives."* Exported as ONE static graph:
`image [1,3,504,504]` raw `[0,1]` → `depth [1,504,504]` + `depth_conf`. `R = 504 = 36×14` matches
DA3's default `process_res`; *"the DINOv2 pos-embed bicubic interpolation is over fixed sizes so it
**folds to a constant at export** (no runtime bicubic)."* The camera decoder and ray aux head are
**dead-code-eliminated by `optimize()`** because only depth/depth_conf are named outputs.

**⚠️ THE bug of the port — "the graph normalizes in-graph, feed RAW `[0,1]` (this cost a day)"**
(`:26-39`). The `ExportWrapper` folds ImageNet mean/std into the graph, so the runtime input must be
raw `[0,1]`. Feeding an already-normalized tensor double-normalizes and **silently** corrupts depth.
The false symptoms it produced:

> a fake **cos ≈ 0.9 engine-vs-torch**, "the engine output looks noisy", "**non-square exports are
> broken (cos 0.9)**", "**letterbox padding breaks attention**". **All of it was the
> double-normalization.** With raw `[0,1]`, the engine is **cos 1.000000 vs torch at any fixed shape
> — square AND non-square.**
>
> Lesson: *"when an on-device vision graph 'looks subtly wrong', **first confirm where normalization
> lives (in-graph vs host)** before blaming the conversion."*

**← This is the single best "one bug generated four false architectural conclusions" story in the
corpus.** (CoreAIKit's `DepthEstimator` therefore uses an identity preprocessor,
`ImagePreprocessor(mean: 0, std: 1)`.)

**Input contract: square + resize-back (SQUISH), not letterbox** (`:41-57`), and — crucially —
**measured, not assumed**:
> squish vs the official DA3 viewer is **mean Pearson r ≈ 0.98** across aspect ratios (a square input
> is r = 1.000). *"That deviation is **within DA3's own resolution sensitivity** — its 504-vs-518
> outputs already differ by **r ≈ 0.975–0.984**. So a fixed-square deployment is faithful to the
> model's intrinsic floor, not lossy. **Measure a model's own resolution variance before calling a
> fixed-res port 'unfaithful.'**"*

Display convention: *"inverse-depth → percentile 2–98 normalize → `Spectral` colormap."*

**Three export patches, numerically identical** (`:59-71`):
1. **RoPE table length baked as a constant** — `RotaryPositionEmbedding2D` sizes its cos/sin table by
   `int(positions.max()) + 1`, *"a Python int pulled from a traced tensor → a data-dependent guard."*
2. **RoPE / `PositionGetter` caches made cache-free** — *"Both memoize tensors into dicts;
   `torch.export` **poisons those dicts with fake tensors**, and a later eager run in the same
   process then dies with `GuardOnDataDependentSymNode`. Recompute every call."*
   **← A subtle cross-contamination between export and a later eager run *in the same process*.**
3. **pos-embed UV grid dtype** — the DPT `_add_pos_embed` hard-casts `.float()`; under fp16 it
   upcasts the feature map and the next conv sees Half weights vs float input.

*"No GPU-delegate op workarounds were needed (unlike RF-DETR): bilinear upsample, 2D RoPE, SDPA and
ConvTranspose all lower as-is."*

**fp16 works — but `.half()`, not autocast** (`:76-83`):
- **`copy.deepcopy(wrapper).to(fp16)`**, never in place — *"the caller reuses the fp32 module as the
  verify oracle, and `.to()` mutates in place."*
- **No `torch.autocast`** — *"under autocast LayerNorm stays fp32, so its output collides with the
  Half conv that follows (`Input type (float) and bias type (c10::Half)`). Half the whole model, run
  Half."*

**Matrix (M4 Max GPU, vs HF eager fp32)** (`:89-94`):

| Variant · dtype | Params | Size | Parity | M4 Max GPU |
|---|---|---|---|---|
| small · fp32 | 34.3 M | 105 MB | cos 1.000000 (cpu+gpu) | 17.7 ms · 56.5 FPS |
| **small · fp16** | 34.3 M | **54 MB** | cos 1.000000, relmax 7e-3 | **15.2 ms · 65.7 FPS** |
| base · fp16/fp32 | 135.4 M | 202 / 402 MB | cos 1.000000 | 37.7 / 43.4 ms |
| mono-large · fp32 | 334.2 M | 1.34 GB | cos 1.000000 | 118 ms |

#### `adcsr-super-resolution.md` — one-step diffusion-GAN ×4 SR, and a case where fp16 FAILS

AdcSR (CVPR 2025): *"the Adversarial Diffusion Compression of OSEDiff — a pruned Stable Diffusion 2.1
UNet (~456 M params) plus a half-size VAE decoder, run in a single forward."* Licensing note worth
keeping: *"unlike the ResShift/SinSR family, which are non-commercial … the code is Apache-2.0 and
the SD-2.1-derived weights carry **CreativeML Open RAIL++-M — the same license under which Apple
ships SD CoreML**."*

Graph: ONE static graph, `lr [1,3,128,128]` in `[-1,1]` → `sr [1,3,512,512]`. *"Only standard SD ops
… no swin, so the `coreai-pre-compilation-rewrite` SIGSEGV that bit the SinSR swin port does not
apply here."* One rejected op: **`aten.var.correction`** from the original color-match's `.std()`.

**⚠️ Two failure modes that force host-side work** (`:24-34`):
1. **Tiling.** Fixed 128→512 tile; `SuperResolver` caps the input long side (`maxInputSide=512`),
   splits into overlapping 128-px windows, feather-blends.
2. **Per-image color-match must be applied GLOBALLY, once, after stitching.** *"This MUST be global:
   **baking it per-tile in the graph divides by a tile's std, which → 0 on uniform tiles
   (sky/skin/white fur) → pure-white square artifacts.**"*
   **← a beautiful example of a statistic that is only valid at whole-image scope.**

**fp16 does NOT work — ship fp32** (`:36-48`), the counter-example to DA3:
> The pruned SD-2.1 UNet is numerically unstable in fp16: attention overflows (the classic SD-2.1
> fp16 NaN), and **`upcast_attention` has no effect because the diffusers SDPA processor ignores
> it**; group-norm of a low-variance tile also divides by ~0. The result is whole tiles → NaN →
> black/gray patches on smooth regions. **group-norm-fp32 upcast alone did not fix it.** **fp32
> (~1.7 GB) is the shipped precision** — cosine 1.000012 vs torch. With the 512-px input cap +
> tiling, per-tile activation is bounded, so fp32 fits iPhone 17 Pro (**~2.7 GB peak < 6 GB**).

Plus: *"the Python runtime's **default-options `AIModel.load` SIGSEGVs in the GPU-delegate JIT
(`CompileForDelegates`) for fp16**; loading with an explicit `SpecializationOptions(.gpu)` (which the
Swift `GraphModel` always does) is clean."*

**CoreGraphics traps found on-device** (`:50-56`) — transferable to any CV app:
- **Row stride**: *"read a `CGContext`'s actual `bytesPerRow` (pass `bytesPerRow: 0`), never assume
  `width*4` — CG pads non-16-aligned widths, and assuming `width*4` **shears** the image."*
- **No y-flip**: *"a standard top-down `CGBitmapContext` already maps the image's top to row 0;
  adding a `scaleBy(1,-1)` flip inverts the result."*

### 9.4 Non-autoregressive / generative ports

#### `flux2-in-context-editing.md` — in-context image editing with zero graph surgery

**Why it exists** (`:8-16`): FLUX.2 [klein] is a *unified* model — the same 4B DiT does T2I, i2i and
in-context editing. *"The editing capability was blocked only by the runtime path — **Apple's stock
`CoreAIDiffusionPipeline` exposes `startingImage` + `strength` (SDEdit), which re-renders the whole
frame and can't do 'add a hat, keep everything else.'**"* And the licensing dead end that forced the
approach: *"FLUX.2 [dev] ControlNets and klein-9B RefControl LoRAs are all **non-commercial** (FLUX
NCL)."*

**The mechanism (in-context / "Kontext"-style)** (`:18-40`) — clearly explained, worth reproducing:
> FLUX.2 editing is **not** a separate transformer input. The reference image's VAE-latent tokens are
> **concatenated into the image sequence** the transformer denoises, distinguished only by a time
> coordinate `T` in the model's 4-axis `(T, H, W, L)` rotary positions:
> ```
> image sequence = [ output latent (T=0) ; reference 0 (T=10) ; reference 1 (T=20) ; … ]
> ```
> Per denoising step: (1) `hidden_states = concat(output_latents, clean_reference_latents…)`;
> (2) run the transformer over the joint sequence (+ text); (3) **slice the prediction back to the
> output tokens and step only those. The reference tokens are re-supplied clean every step and their
> predictions are discarded — they are context, never denoised.**
>
> The output starts from **pure noise (`sigmaMax = 1.0`)**, not a noised copy of an input — so the
> instruction can add / replace / relight / combine content while attention to the clean references
> keeps the subjects. **`guidance_embeds = false` on klein, so there is no CFG (single forward).**

**Why it needed no graph surgery** (`:55-59`) — the key architectural insight:
> The exported wrapper (`Flux2TransformerPrecomputedRoPEWrapper`) is **token-content-agnostic** — it
> takes `hidden_states [1, seq, C]` plus **precomputed RoPE** (cos/sin), so all of the `(T,H,W,L)` id
> layout is decided by the runtime, **not baked into the graph**. That is the single reason this
> worked with zero graph surgery: **the shipped T2I graph's RoPE already has the `T` axis (T2I just
> uses `T=0` for every image token).**

**← Generalizable design rule: pass RoPE in as data, not as graph logic, and your static graph
becomes reusable for sequence layouts you did not anticipate.**

**Static shapes ⇒ one export per reference count** (`:41-53`):

| Component | Sequence (1024 / 512) | Contents |
|---|---|---|
| `transformer_edit` / `_512` | 8192 / 2048 | output + 1 reference |
| `transformer_edit_2ref` / `_512` | 12288 / 3072 | output + 2 references |

```bash
uv run coreai.diffusion.export flux2-klein-4b --components transformer_edit transformer_edit_2ref
```

**Numbers (M-class Mac GPU, int4, 4 steps)** (`:73-80`): 1 reference @1024 **~25 s** (seq 8192);
2 references @1024 **~43 s** (seq 12288). Parity confirmed against the diffusers
`Flux2KleinPipeline` edit path. *"Mac-first — at 4B the peak footprint overruns a **12 GB iPhone**;
the 512 edit transformers are the iPhone path (not yet gated)."*

**Gotchas** (`:82-89`):
- **Runtime base matters**: *"apple/coreai-models `02a8edd` has a working Qwen3 text-encode path;
  **some other revisions crash with `77 vs 512` (a CLIP-77 tokenizer fallback)**. Base the fork on a
  verified revision."*
- **Fixed shape = one graph per reference count.**
- **Edit weights are separate ~2 GB transformers** — fetch on demand, not in the base download.

#### `diffusion-llms-dllm.md` — LLaDA-8B, a masked diffusion LLM

*"A masked **diffusion** LLM is not autoregressive. Instead of writing one token left-to-right with a
KV cache, it runs a **bidirectional** forward over a fixed-length canvas of `[MASK]` tokens and
**unmasks the most-confident positions in parallel**, repeating until the canvas resolves."*

**Shape of the port** (`:8-26`): a fixed-shape exportable **LLaMA-dense 8B** but with
**bidirectional SDPA** (`is_causal=False`, no mask), **no KV cache** (every denoising step is a full
forward over the whole canvas `S`), RoPE θ=500000, RMSNorm `weight*x` (**not** Gemma's `1+w`), MHA
32×128 (no GQA), no qk-norm, SwiGLU intermediate **12288** (*"`activation_type="silu"` so `ff_proj`
and `up_proj` are each full-width — **NOT half**"*), lm_head `ff_out` (`weight_tying False`).
Export: one static bundle `main(input_ids[1,S] int32) → logits[1,S,vocab]`; **int4 per-block-32 body
+ int8 head ≈ 4.9 GB**. `metadata.json` carries the diffusion knobs (`seq`, `block_size`,
`threshold`) *"so they retune without a recompile."*

**Lessons** (`:28-54`):
- **⚠️ "Exact-token-match is the WRONG metric for a diffusion LM."** *"Small logit noise reroutes the
  denoising path to a **different but equally valid paraphrase**, so token-match drops while the
  answer stays correct. **We almost rejected int4 over this (PTQ int4 showed 20/64 token-match) — the
  decoded TEXT was correct the whole time.** Judge by output text, not token ids."*
  **← A direct, explicit exception to the zoo's own headline "token-exact" gate. Any guide that
  presents token-exactness as universal must carry this caveat.**
- **int4 is viable here, not a cliff.** int8 is lossless; int4 per-block-32 (engine
  `symmetric_with_clipping`) keeps answers correct. Head fp16 vs int8: no quality difference.
- **The speed ceiling is the no-KV full-canvas forward** (~**185 ms/forward @ S=128**, ~linear in S).
  The entropy `threshold` is a **near-free knob** — *"it only changes the step count (NFE), not
  ms/forward: **0.5→NFE19, 1.0→NFE11/~38 tok/s, 1.5→NFE8/~53 tok/s, ~2.5 starts to degrade**."*
  The real lever named: **delayed-KV-cache decode** (d3LLM's `generate_multi_block_kv_cache`: cache
  committed blocks, forward only the active region) — not yet done.
- **Keep `block_size` small (32).** *"Larger blocks denoise more of the canvas in parallel (a more
  striking 'whole-canvas fill' visual) but **garble coherence** (a count comes out `11,22,2,3…`).
  LLaDA's semi-AR blocks are what hold the output together."*
- **Canvas `S` bounds the answer** (no KV ⇒ prompt+answer must fit in `S`). **S=128 ≈ 80-token
  answers; S=256 ≈ 210 tokens.** *"The host must reserve gen room and drop old turns, or a long
  history collapses the gen budget to a sliver (1-token 'answers')."*
  **← A hard structural limitation of dLLMs for multi-turn, stated plainly.**
- **Demo prompts** (a UX finding): *"the parallel fill is only visible when the model emits a
  **direct structured answer with no preamble** — `List the planets`, `Count 1 to 20`, or a short
  arithmetic word problem (the equation digits fill out of order: `48 + ░4 =░7░ → 72`).
  `explain` / `show your work` / `write a function` trigger a chatty preamble that eats the canvas."*

### 9.5 `flagship-full-tuning-stack.md` — the multiplicative-speedup framing

Dated 2026-07-01. Target: Qwen3.6-35B-A3B (primary) and GLM-4.7-Flash. *"All ⚗️ numbers are
targets/estimates unless marked MEASURED."*

**The core idea** (`:8-17`) — a clean mental model worth reusing verbatim:
> Decode tok/s ≈ **1 / (per-forward bytes)** × **1 / (forwards per token)**. The two factors are
> independent, so byte-reduction and forward-reduction **compound**. Prefill (TTFT) is a third,
> compute-bound axis.
> ```
> decode speedup  ≈ (Axis-1 byte cut) × (Axis-2 spec-decode)   [× kernel micro-opts]
> prefill speedup ≈ (Axis-3 TensorOps matmul/flash)
> ```

**Baseline byte model, Qwen3.6-35B-A3B, per-token decode read (MEASURED via config audit)**
(`:21-30`) — a genuinely useful worked bandwidth budget:

| Bucket | int8 now | Note |
|---|---:|---|
| routed experts (`gather_qmm`, top-8/256) | **1007 MB** | biggest single chunk |
| attn q/o (k/v small) | **755 MB** | dense, un-kernelized fused |
| lm_head (vocab 248 k × 2048) | **509 MB** | single biggest matvec |
| shared expert | 126 MB | always-on |
| router (fp16) | 42 MB | stays |
| **TOTAL** | **~2438 MB/tok** | ← BW-bound decode floor |

GLM-4.7-Flash = **~3586 MB/tok** (MLA attn 1023 + experts 1736 + shared 434 + lm_head 317), *"cross-
checked to its known 3.58 GB/tok."*

**Axis-1 (byte reduction)**: dense-path int4km (−695 MB, ~1.40×, **MEASURED on LFM-8B: 1.23×
sustained / 1.43× avg, quality PASS**); experts int8→int4km (1007→504 MB, stacks to ~1.97×); FP4 via
TensorOps; KV-quant in the decode-attn kernel. **Stacked: 2438 → ~1240 MB/tok ≈ 1.97× decode from
bytes alone.**

**Axis-2 (forward-count reduction, spec-decode)**: n-gram/prompt-lookup (2–4× on code/RAG/structured,
training-free), vanilla draft (~2×), EAGLE-3 head (3–5×, accept 0.80–0.88).
**Gating prereq stated bluntly** (`:60-62`): *"prove the pipelined engine can do a **verify-forward
(S=K batch)** + draft→verify→rollback wiring. This is new **ENGINE** work (Swift), not a kernel —
**the single highest-leverage build in the whole plan**."*

**Axis-3 (prefill/TTFT)**: *"**MEASURED this session**: MPSGraph prefill SDPA plateaus at ~22 % of
the M4 fp16 ceiling (clean S² scaling, no crash) — big headroom, but **scalar-MSL kernels can't beat
a matrix-tuned baseline (the documented 16 % loss)**. The win needs **matrix units**."*

**Axis-4 (kernel micro-opts)**: fused RoPE+RMSNorm+SwiGLU; **absorbed-MLA cross-head staging (GLM-4.7
only): 1.12× @4K MEASURED, long-ctx-only**; FlashDecoding-style seq-split occupancy.

**Combined target**: decode Axis-1 (~1.97×) × Axis-2 (~3× conservative) ≈ **~5–6×**
(Qwen3.6-27B dense 15.9 → **~90+ tok/s** target); prefill ~3–4×. *"Quality preserved: FP4/QAT holds
4-bit quality; **spec-decode is lossless (verify)**."*

Two operational facts worth extracting (`:107-109`):
- *"On-device decode bundles: raw `.aimodel` (`main.mlirb`) **JITs on A19 for ≤ 8B decode-only
  graphs** (MEASURED, engine ready ~47 s); **needs > 15 GB device free for the on-device compile
  scratch**."*
- *"**Gate every quant lever on multi-token reasoning** (chat-formatted prompt token-match + PPL,
  not a single token — the **Nanbeige lesson**)."*

### 9.6 `agentic-security-checklist.md` — shipping an on-device LLM agent safely

Distilled from **WWDC26 347 "Secure your app: mitigate risks to agentic features"** and **343
"Explore advanced App Intents features"**, with an explicit caveat (`:10-12`) that *"API names below
are as **spoken in the talks** — captions don't capture on-screen code, so confirm exact
spelling/signatures (`.onToolCall`, `.historyTransform`, `authenticationPolicy`,
`OwnershipProvidingEntity`, `IntentDonationManager`) against the developer docs."* **UNVERIFIED
symbol spellings; concepts described as verbatim-confirmed.**

**The framing sentence** (`:18-19`), quoting Apple: *"Indirect prompt injection is an **unsolved
research problem**. Apple's own framing (347): 'our best approach at the moment is to understand how
much your app is at risk, and aim to mitigate that risk.'"*

**Risk model** (`:26-48`): **indirect prompt injection** = instructions embedded in *extra context*
(not the user's prompt) that redirect control flow — *"The context can arrive in the initial prompt
**or in a tool result**."* Two effects:
- **Data poisoning** — attacker influences the **parameters** of an action you were going to run
  anyway ("message Mom" → recipient rewritten).
- **Action poisoning** — attacker influences **which** action runs ("summarize this email" →
  injection opens a URL with the email body appended → exfiltration).

**The Lethal Trifecta** (Simon Willison, cited verbatim in 347): maximum danger when an agent
simultaneously has (1) access to **private data**, (2) exposure to **untrusted content**, (3) the
ability to **externally communicate** — *"generalize this to **any action with a side effect**."*
The doc's design lever: *"break **one leg per risky flow**."*

**Threat-modeling exercise** (`:50-75`): Step A data-flow analysis of prompt construction (*"**and
every tool result**"*); Step B mark untrusted — *"**anything from an external entity is attack
surface** … Your own first-party UI input is the only thing that starts trusted"*; Step C enumerate
actions by side-effect class:

| Side-effect class | Example (347) |
|---|---|
| **Financial** | `OrderTeaTool` |
| **Data exfiltration** | `PostAndFetchPublicFeedTool` |
| **Data loss** | `DeletePhoto` (no undo) |
| **Stored / second-order** | `BrewingTimerIntent` *label* — injection writes instructions that a later "list timers" pulls back into context |

> **The stored-injection row is the sneaky one.** 347's `createTimer` example: *"a tool that looks
> harmless (no side effect) but takes an **optional `String` label the model fills in**. An injection
> sets the label to attacker text; a later 'list timers' query reads it back → **context poisoning
> across turns**. … **audit every place the model writes a string that is later read back into a
> prompt.**"*

**Mitigations — deterministic first** (`:77-92`). 347 is explicit: *"prefer deterministic mitigations
as the baseline ('their security guarantees are easier to audit and reason about'); use probabilistic
ones as defense-in-depth."*
- Prompt-level: **redact PII/sensitive data before it reaches the LLM** (deterministic);
  **spotlighting** — wrap untrusted spans in delimiter tags — *"**Probabilistic** (a crafted
  injection can negate it), but cheap and worth stacking; **different models enforce it to different
  degrees**."*
- Action-level: **user confirmation** before any side-effecting action; **authentication /
  device-unlocked requirement** — *"the agent may be reachable from the **lock screen** (Siri), so
  significant-risk actions must not run while locked."*

**The concrete APIs** (`:94-142`):

*Foundation Models lifecycle event modifiers:*
- **`.onToolCall`** — fires when the model emits a tool call, **before the executor runs it**.
  ***"If the callback throws, the tool never runs"*** → *"the single chokepoint for confirmations. One
  `.onToolCall` that checks the tool name and calls your `confirmWithUser()` gives **full coverage of
  every tool call from one place**."*
  ```swift
  profile.onToolCall { call in
      guard call.toolName == "OrderTea" else { return }              // others run untouched
      guard await confirmWithUser(call) else { throw CancelledByUser() }  // throw == block
  }
  ```
- **`.historyTransform`** — fires *before the transcript is rendered to the model*, on every new user
  request **and every loop iteration**; modifies the **tail** of the transcript. The place for
  spotlighting and PII redaction. *"⚠️ **Transforms are scoped to the current inference only** — not
  visible to the next call, so **re-apply every iteration**. For an expensive transform you want to
  persist, use the **`@SessionProperty`** annotation (stateful history transform)."*

*App Intents (when the model is Siri, not your loop):*
- **Risk-based, contextual confirmation** — *"**Risk metadata is auto-assigned when your intent
  adopts a schema** — you do nothing. The *schema* carries it (`deleteAssets` → destructive)."*
  343's nuance: *"Siri **assumes entities are private by default and may skip confirmation**; it
  confirms more for destructive actions and for content the user **shared/made public**."*
- **`OwnershipProvidingEntity`** (343, new) — conform shareable/publishable entities and keep the
  ownership state current. *"**Only add it to entities a user can actually share or make public.**"*
- **Lock-screen authentication**: `authenticationPolicy = .requiresAuthentication`. *"A schema has
  its **own default policy** (by sensitivity), auto-assigned to your intent; you may **override only
  to make it stricter** — **a weaker override is a *build error* that tells you the minimum**."*
- **Interaction-donation hygiene** (343): *"'**if your app donates excessively, the system may ignore
  those donations**.' Donate **real user UI actions only** … (Donating from the *agent* loop would
  both pollute Siri's learning and **risk laundering injected actions into 'learned' behavior**)."*
- **Build-time design hints** (240): *"Adopting `sendMessage` without `draftMessage` is a **build
  error** — Apple forces the draft/confirm path for messaging. **Read these errors as security
  guidance, not noise.**"*

**Pre-ship checklist** (`:144-166`) — reproducible as-is, with the closing verification item being
the strongest bit: *"A **regression eval feeds poisoned context** and asserts (via a `disallowed`
**`TrajectoryExpectation`**) that destructive tools are **not** called and parameters are **not**
rewritten. **This is the one deterministic test that turns 'we mitigated injection' into a number you
can hill-climb.**"*

---

## 10. Prototype code (Tier 5)

### 10.1 `knowledge/_tensorops_proto/` — a de-risk ladder for Apple TensorOps `matmul2d`

Seven small self-contained scripts (61–120 lines each), all built on the **same skeleton**:
`TorchMetalKernel(src=<MSL body>) → torch.export → TorchConverter.register_custom_kernels →
add_exported_program → to_coreai().optimize() → save_asset → asset.executable() → load_function("main")
→ await fn({...})`, then cosine + relative-L2 vs a torch reference. They are a **model of how to
de-risk a kernel idea in isolation**, and I would recommend them directly as a guide artifact.

**The critical shared discovery, documented in a code comment**
(`_tensorops_proto/m0_half_x_half.py:21-24`):

```
# Metal tensor coords are TRANSPOSED vs numpy: torch[M,K] -> tensor extents [K,M]
# (dim0 = inner/contiguous). Verified with probe_dispatch: out[a,b] lands at numpy[b,a].
# So header-verbatim slicing is correct: tgid.x -> N tiles (step 32, tensor dim0),
# tgid.y -> M tiles (step 64, tensor dim1).
```

**← Same axis-reversal that produced the BitVLA NaN bug (§9.2). It is the recurring footgun of the
Core AI Metal DSL.**

| Script | What it proves / measures |
|---|---|
| **`probe_dispatch.py`** (61 L) | *"which threadgroups actually run, and what tgid they see, under `dispatchThreads`"*. Thread 0 of each group writes `out[tgid.x, tgid.y] = 100 + 10x + y` into a known-good `[64,32]` output. `TGX`/`TGY`/`TPTGX` env-driven. **This is the script that established the axis-reversal fact above** — a 30-line experiment that unblocks everything after it. |
| **`m0_half_x_half.py`** (92 L) | The base case: `half × half → half` via `matmul2d`. Stated goal: *"prove coreai embeds + compiles + runs a `matmul2d` kernel, that the auto-generated `tensor<device T, dextents, tensor_handle>` signature feeds `matmul2d` directly, and **pin the metal language version the runtime uses**."* Kernel body is 6 lines: `matmul2d_descriptor(64, 32, dynamic_extent, false,false,false)`, `matmul2d<desc, execution_simdgroups<4>> op`, three `.slice()`s, `op.run(mA, mB, mC)`. Reports cos-sim, rel-L2, **and a per-64×32-tile correctness map** — so a partially-wrong tiling shows up as a spatial pattern rather than one bad number. |
| **`m1a_half_x_int8.py`** (67 L) | *"half activations × int8 weights → half, via `matmul2d` (native `half × int8_t → half`). **Proves the quantized `matmul2d` path with zero reinterpret** (`int8_t` is a native coreai dtype)."* Identical kernel body to M0 — *"only B's element dtype differs (via the auto signature)"*. |
| **`m1b_half_x_int4_uniform.py`** (85 L) | The reinterpret path: weights arrive as **packed uint8**, and the kernel builds an `int4b_format` tensor view from the raw device pointer: `device uchar* wptr = &Wp[0,0]; metal::dextents<int,2> wext(N, K); tensor<device metal::int4b_format, metal::dextents<int,2>, tensor_inline> Wi(wptr, wext);` then feeds `matmul2d` directly. *"No per-block scale (uniform int4) — **proves the uint8→int4 reinterpret path**."* `N`,`K` baked as literals. |
| **`m2_int4_block32_scaled.py`** (120 L) | The realistic one: *"LLaDA-shaped block-32 fp16-scaled int4 matmul."* Because `matmul2d` has no blockwise-scale plane at this Metal version, it **manually dequants each `[k=32, n=32]` weight block into `threadgroup half wsh[BLK*TILE_N]`**, applying the per-block fp16 scale, then runs `matmul2d` half×half with `mode::multiply` on the first block and **`mode::multiply_accumulate`** thereafter — accumulating into a float `C` across `K/32` blocks, with `threadgroup_barrier` on both sides. Signed-int4 decode is done explicitly (`if (code > 7) code -= 16;`) — the comment says *"decode signed int4 manually (**unambiguous**)"*. Validates against a torch blockwise-dequant reference. **This is the concrete answer to the `-std=metal4.1` blockwise-scale-plane open question raised in `accel-levers-survey-and-plan.md` §5.7: you can get block-32 scaling at Metal 4.0 by staging the dequant in threadgroup memory.** |
| **`m4_speed_ab.py`** (89 L) | **The gating A/B**, and its docstring states the decision logic exactly: *"does the matrix-unit path (`matmul2d`) **BEAT** coreai's default MPSGraph matmul on M4 Max at compute-bound shapes? **If `matmul2d` can't beat MPSGraph matmul here, a custom FlashAttention won't beat MPSGraph SDPA either (same matrix ceiling). If it can, FlashAttention is worth building.**"* Benches square `S ∈ {1024, 2048, 4096}` fp16 matmuls, 4 warmup + 30 timed iterations, **median**, printing ms and **TFLOP/s for both arms plus the ratio and cos**. ← a textbook "cheapest experiment that decides the expensive one". |
| **`device_matmul_ab_export.py`** (77 L) | Exports the same A/B to **persistent `.aimodel`s for A19 AOT compile + `PipelinedBench` timing**. `MODE=mm2d` vs `MODE=ref`, same `M(S)×K×N`. Note the modelling choice: *"B is a **RESIDENT weight (baked constant)**, only A streams in — **matches LLaDA (weights resident)**."* Tile/simdgroup/relaxed-precision knobs are env-driven (`MTILE`, `NTILE`, `NSIMD`, `RELAXED`) so the device sweep is parameterised. Defaults `K=4096, N=12288` — LLaDA's FFN shape. |

**Note the outcome recorded elsewhere**: §7.4 records that on **A19** the `matmul2d` *prefill* lever
was **refuted** (default MPSGraph already ≈ 6 TFLOP/s), while on **M4 Max** MPSGraph prefill SDPA sits
at only ~22 % of fp16 peak so the lever is **still open there**. So this ladder produced a negative
result on one device and an open question on another — which is exactly what a de-risk ladder is for.

### 10.2 `knowledge/_specdecode_proto/tree_attn_verify.py` — the lossless spec-decode kernel

139 lines. Its docstring is the clearest statement of the technique in the corpus:

> **Tree-attention VERIFY kernel (the structural, LOSSLESS spec-decode lever) — correctness de-risk.**
> EAGLE-3-style spec-decode drafts a **TREE** of candidate tokens; verifying them in ONE forward needs
> each tree node to attend to the prefix + its **ANCESTORS only** (not siblings/other branches). That
> = a **multi-query (q=T) flash attention with an ARBITRARY additive mask** (tree-ancestor mask), a
> generalization of the q=1 flash-decode SDPA. **The batched forward amortizes the weight read over T
> tree tokens (the speed) and verify keeps the output distribution EXACT (lossless — no quality cost,
> unlike 4-bit quant).** This file de-risks the KERNEL only.

**What it demonstrates concretely:**
- **Layout**: one SIMD-group (32 lanes) per `(head h = gid.y, query t = gid.z)`; `lane = gid.x` owns
  `ept = D/32` head dims held in a per-lane register slice (`float qx[_MAX_EPT]`, `_MAX_EPT = 8` for
  `D = 256`).
- **The DSL axis reversal spelled out again** (`:24-27`): *"DSL axes are reversed vs torch:
  Q torch `[H,T,D]` → `A[d,t,h]`; K/V torch `[nkv,Sk,D]` → `K[d,j,kv]`; MASK torch `[T,Sk]` →
  `M[j,t]`; CTX torch `[H,T,D]` → `CTX[d,t,h]`."*
- **GQA mapping**: `kv = h / (H / nkv)`.
- **fp32 online (streaming) softmax** with the standard running-max correction, written out in the
  kernel body:
  ```c
  float s = simd_sum(p) + float(M[j, t]);   // masked score (M additive: 0 or -inf)
  float mnew = max(m, s);
  float corr = exp(m - mnew);
  float e    = exp(s - mnew);
  l = l * corr + e;
  for (uint i = 0; i < ept; ++i) o[i] = o[i] * corr + e * float(V[lane*ept + i, j, kv]);
  m = mnew;
  ```
  Note this *does* subtract the running max — i.e. it obeys the `AGENTS.md` rule *"Naked `exp()` in a
  hand-written kernel. Three separate sessions lost to this; subtract the max first."* (Though it
  uses bare `exp`, not `metal::precise::exp` — which the wNa8o8 doc §9.1 says is required for
  cross-compiler determinism. Minor inconsistency; noted.)
- **The mask is fully general**: *"mask is ADDITIVE (0 = attend, −inf = block) — **the tree-ancestor
  mask (or any custom mask)**."* Scale is baked into `qx` at load; `template_dtypes={"A": "TYPE"}`
  makes the kernel dtype-generic.
- **The test builds a real tree mask** (`make_tree_mask`, `:95-105`): a binary tree over `T` nodes
  where node `i`'s parent is `(i-1)//2`; every node sees the **whole prefix** plus **self + ancestor
  chain**.
- **Gate**: `H=8, nkv=2, D=256, T=15` (a depth-4 binary tree), `prefix=40`.
  **PASS = `maxdiff < 2e-2` AND `cos > 0.9999`** vs a torch masked-attention reference.

**Why this matters for a guide**: it is a complete, runnable, ~140-line demonstration that the
structural prerequisite for tree-based speculative decoding — arbitrary-mask multi-query flash
attention — **compiles and runs correctly as a Core AI custom Metal kernel**. Per §5.7/§9.5, the
*remaining* work is engine-side (a verify-forward `S=K` batch plus draft→verify→rollback wiring in the
pipelined engine), not kernel-side. **Community-verified correctness; no speed number is claimed
here.**

---

## 11. GitHub issues & PRs (`john-rocky/coreai-model-zoo`)

Fetched this session with `gh issue list --state all --limit 40` and `gh pr list --state all
--limit 40`. The repo is small and young: **5 issues, 6 PRs**.

| # | Kind | Title | State | Date |
|---|---|---|---|---|
| 5 | issue | `[request] Nanbeige4.2-3B` | CLOSED | 2026-07-23 |
| 4 | issue | WebGPU port of TripoSplat (thanks for TripoSplatMac) | OPEN | 2026-07-18 |
| 3 | issue | `[bench] iPhone18,1 · qwen3.5-0.8b` (label `bench-result`) | OPEN | 2026-07-03 |
| 2 | issue | "Can you provide your custom CoreAI Model repo?" | CLOSED | 2026-06-14 |
| 1 | issue | "demo resources." | OPEN | 2026-06-14 |
| 10 | PR | CoreAIStudio: rebuild UI around `ConversionQueue` (video-only, batch queue) | CLOSED | 2026-07-23 |
| 9 | PR | Add `ConversionQueue`: batch conversion queue data model | CLOSED | 2026-07-23 |
| 8 | PR | Add `VideoUpscaler`: model-agnostic video frame upscale pipeline | CLOSED | 2026-07-23 |
| 7 | PR | knowledge: add deep reference on `apple/coreai-models` | CLOSED | 2026-07-23 |
| **6** | **PR** | **Add Nanbeige4.2-3B Core AI support** (`ukint-vs`) | **MERGED** | 2026-07-23 |

### 11.1 PR #6 — the first external port, and the best single artifact in the repo

+986 lines, 12 files. Worth studying as **the reference for what a contributed on-device-ML port
looks like.**

**The model**: `Nanbeige/Nanbeige4.2-3B` at pinned checkpoint revision
`5ff54fb7ed86ce8e216d78bff5417ab9981de3d4`, Apache-2.0. Architecturally interesting: *"a **looped
transformer**: 22 physical Llama blocks execute **twice** with a norm after each pass and **separate
KV history**, producing **44 executed/cache layers without duplicating weights**."*

**Published artifact discipline** (from the PR body):
- repo `huggingface.co/ukint-vs/Nanbeige4.2-3B-CoreAI` — **contributor's own namespace**
- **immutable revision** `5864ec7a5581940958e58354a6b6c46c8f06891e`
- path `gpu-pipelined/nanbeige4_2_3b_decode_int8hu_block32_sym_s1`, 4.59 GiB
- **`producer: coreai-core 1.0.0b2`** (the §6.2 fingerprint check)
- *"The remote model and tokenizer LFS hashes were verified against the local bundle. The bundled
  vendor chat template was validated with **both `enable_thinking=true` and `enable_thinking=false`**."*

**Validation list, verbatim** — this is the shape a real port's evidence takes:
- released-configuration and named unsupported-feature validation: pass
- 22 unique physical layers / 44 logical cache slots / two-pass execution order: pass
- **float32 full and cached logits: `rtol=1e-4`, `atol=1e-4`; identical 32-token greedy continuation**
- pinned official-checkpoint parity: pass; config SHA-256 `f6cb15b2…`
- **int8 authoring gate: prompt top-1 8/8, greedy 32/32, cosine 0.9997768**
- **int8 Core AI gate: token-exact** for the factual prompts and a `9.11` vs `9.8` reasoning smoke; deterministic rerun
- quantization traversal: **111 physical linear modules**, without duplicating the recurrent stack
- **M4 Max Release benchmark, p128 / g256 / 3 runs: 47.37 prefill and 46.35 decode tok/s**
- **4096-token boundary: 29.83 prefill / 32.80 decode tok/s, 9.17 GiB peak RSS, zero swaps**
- **Xcode 27 GPU AOT compile for iOS 27 `h18p`: pass**; generated package source hash matches
- *"**Int4 and mixed int4/int8 variants were evaluated but failed the same quality gates, so neither
  is exposed as a shipping option.**"* ← an honest negative shipped in the PR

**The remaining-gate paragraph** models the norm from `AGENTS.md`/`CONTRIBUTING.md`: *"The iOS 27
`h18p` hardware gate is pending, so **this PR makes no iPhone throughput or memory claim.**"*

**The maintainer's device-gate report** (posted into the PR thread — this is the "device gate
request" workflow actually executing):
- Mac reproduction on independent hardware (M4 Max, macOS 27, coreai-core 1.0.0b2): *"**int8 bundle
  is token-for-token identical to the fp32 oracle, 24/24, on both gate prompts** — your central claim
  reproduces exactly."* And **60.3/59.9 prefill, 56.8/56.6 decode tok/s** vs the contributor's
  47.4/46.4 — *"your claim is comfortably conservative."*
- **Device gate (PipelinedBench, sideloaded bundle, md5-verified file-by-file)**:
  - Engine ready in **31.7 s cold** (first-ever load, on-device GPU specialization) / **10.8 s warm**;
    free space 22.4 GB; no jetsam.
  - **NUMERICS: nat 24/24 + oracle 24/24 — device greedy tokens IDENTICAL to the Mac engine
    reference**, which is itself token-exact vs the fp32 oracle. *"So **iPhone == Mac == fp32 oracle**
    across both prompts, and it reproduced identically on a second full run. **Cross-device
    determinism holds for the recurrent two-pass graph.**"*
    **← A genuinely useful data point: greedy decode is bit-reproducible across A19 and M4 Max for
    this graph class.**
  - Throughput (p128 g256, `S=1` prompt chunking, ×2 trials each; *"phone GPU clocks swing with
    DVFS/thermals so both runs are quoted"*):
    **first run after cold spec: prefill 6.9 / decode 5.7 tok/s** (trials 8.6/5.9, 5.2/5.5);
    **settled rerun (300 s idle first): prefill 8.5 / decode 6.4 tok/s** (trials 9.1/7.0, 7.9/5.8).
  - The maintainer explicitly attributes the low iPhone number to the architecture, *"not a
    conversion issue: the two-pass execution reads the 22 shared physical blocks twice"* — i.e. a
    looped transformer costs **2× the weight reads per token** on a bandwidth-bound device while
    keeping the small download.
    **← The interesting on-device consequence of weight-tied looped transformers: they save storage
    and RAM, not bandwidth. M4 Max 46.4 tok/s vs iPhone 17 Pro ~6.4 tok/s is a ~7× gap, much wider
    than the ~3× typical for this size class (cf. Nanbeige4.1-3B: 114.5 Mac / 15.9 iPhone ≈ 7×
    — actually comparable; UNVERIFIED whether the looping specifically widens it).**

Merge comment (worth quoting for the community-process guide): *"**you are this zoo's first external
model contributor** … a pinned checkpoint and an immutable bundle revision end to end, a faithful
two-pass recurrent authoring that reuses the existing Llama primitives instead of forking them,
explicit failure modes for every unsupported config, **an honest int4 rejection backed by multi-token
quality gates**, kernel and speculation experiments documented even where the conclusion was 'keep
stock'."*

### 11.2 Issue #3 — the only submitted bench blob (and it is machine-generated)

The full JSON result blob for `qwen3.5-0.8b` on `iPhone18,1` (iOS 27.0, build `24A5355q`, 12.3 GB
RAM), protocol `pb-random-v1`. Full environment capture is the point:

```json
"environment": { "available_memory_mb": 6373, "battery_level": 0.9, "battery_state": "charging",
                 "free_disk_gb": 64.9, "low_power_mode": false,
                 "thermal_state_before": "nominal", "thermal_state_after": "nominal" }
```

Runs (`load_s: 3.4`; bundle `qwen3_5_0_8b_decode_int8hu_perchan_sym`, HF revision `34ed8b08…`):

| Kind | Prefill tok/s | Decode tok/s |
|---|---:|---:|
| cold | **31.10** | **70.67** |
| warm | 70.38 | 68.72 |
| warm | 69.70 | 68.41 |
| warm | 64.45 | 66.16 |

Two observations: (1) the **cold prefill is 31.1 vs ~70 warm** — a 2.3× first-run penalty entirely
separate from the 3.4 s load; (2) **decode drifts down 70.7 → 66.2 across four consecutive runs at
`thermal_state: nominal`** — a ~6 % droop with no thermal-state change reported, which supports the
`gemma4-raw-metal-a19-levers.md` claim that thermal *state* is a coarse instrument.
Note also the bundle name is `…perchan_sym`, i.e. **this blob predates the
`perchan_sym → block32_sym` rename** recorded in §6.2 — and that per-channel int8 is the scheme
`compression-reference.md:21-24` says is **broken on the macOS-27-beta MPSGraph GPU delegate**
(it evidently works on the iOS GPU here). **UNVERIFIED / worth flagging as a possible inconsistency.**

### 11.3 PRs #7–#10 — agent-generated contributions, all closed

All four are from `seanxylin`, branch names of the form `worktree-agent-<hash>`; PR #7's body ends
with *"🤖 Generated with Claude Code"*. **#7** added a 375-line `knowledge/coreai-models-apple-
overview.md` — a deep reference on Apple's repo *"verified via the GitHub API tree + per-file fetches
(**not the rendered file browser**)"*, covering the SwiftPM pins, the `conversion/overlay/`
mechanism, the **22-model catalog**, a full extraction of Apple's agent-skill content, and
confirmation that Apple's *"not accepting pull requests"* policy is current.
**Note: that file is NOT in the local clone** (the PR was closed) — so it is not a source I could
read. **UNVERIFIED.**

The maintainer's closing comment is itself a data point on reviewing agent-generated research:
*"I cross-checked a number of its claims against the actual repositories — the SwiftPM pin revisions,
the `conversion/overlay/BASE` commit, the verbatim quotes from the `apple/coreai-models` README, and
the model count. **Everything I checked was accurate**; it's clear this was researched with real
care."* He still closed them, with the reason: *"**PRs that build and run standalone are much easier
to review**"*, plus a substantive gap — *"this repo hasn't published a Core AI conversion of a
frame-interpolation model (RIFE) yet, so that piece has nothing to download today."*

Issues #1, #2, #4 are minor (demo resources; a request for the fork — which is Repo A; a WebGPU
TripoSplat port note). Nothing substantive beyond what is above.

---

## 12. Guide topics this material uniquely supports

Ranked by how much of the evidence is *only* available here. Each entry names the primary sources.

1. **"Prefix caching on-device: why multi-turn TTFT is the metric that matters, and how a
   one-integer KV rewind gets you 101×."**
   Sources: fork commits `0fdf710` + `627fec7`; `knowledge/prefix-cache-kv-reuse.md`;
   `knowledge/fm-provider.md` (the `LanguageModelExecutor` side: *"KV reuse across turns is the
   executor's job … nobody does it for you"*).
   Unique angle: the **attention-vs-recurrent asymmetry** — pure-attention KV can be truncated at any
   position; SSM/GDN running-scan state cannot, so hybrids forfeit prefix caching entirely. That
   inverts the usual "SSMs win on device" story for agent/RAG workloads. Also: the caller-side LCP
   algorithm, the "retained may be < requested" contract, and the byte-stable-renderer requirement
   from `fm-provider.md`.

2. **"Two Core AI beta incidents, in full: the MPSGraph KV-write bug and the coreai-torch 0.4.0 IR
   break."**
   Sources: `knowledge/coreai-beta-mpsgraph-kvwrite-bug.md` (FB23024751 / apple/coreai-models#5),
   `knowledge/coreai-torch-041-ir-incident.md` (apple/coreai-torch#37 and #44).
   Unique angle: complete symptom → minimal-isolation → workaround chains with Feedback numbers. The
   KV-write isolation (*"flipping the begin-index **source** alone flips run → crash"*) and the
   **input-mask escape** are primary-source engineering with no Apple documentation behind them. The
   0.4.0 story adds the **producer-fingerprint audit trick**, the **`strip_debug_info` chicken-and-egg
   (b1 wheel to parse, b2 wheel to stamp)**, and the runtime-gate-vs-authoring-gate distinction.

3. **"Benchmarking on-device LLMs without fooling yourself."**
   Sources: `knowledge/cross-runtime-quality-benchmarking.md`, `knowledge/apple-models-bench.md`,
   `knowledge/gemma4-raw-metal-a19-levers.md`, `knowledge/custom-metal-kernels.md:124`,
   `BENCHMARKS.md`, `conversion-guide.md:180-182`, issue #3's blob.
   Unique angle: an accumulation of *measured* measurement hazards — protocol swing (115 vs 184 tok/s
   on the same artifact), **DVFS ramp on A19 (66–68 vs 87 vs 95–102 tok/s for the same prefill)**,
   thermal degradation (25 ms → 58–103 ms), the "thinking-mode + token-budget" quality artifact that
   manufactured an 80 %-vs-20 % result, "bits are not a spec", `cpu_only()` as a 9× trap, and
   *"pair both arms in one process, interleave ≥ 8 reps … unpaired single-shot on a ±15 %-drift
   machine will confirm anything."*

4. **"QAT weights are half a product: why Gemma 4's wNa8o8 checkpoint loses 38 GSM8K points at fp16."**
   Source: `knowledge/gemma4-wna8o8-requires-int8-activations.md` (+ `cross-runtime-quality-...`).
   Unique angle: a fully worked proof (three independent implementations wrong *identically*; two
   independent fake-quant harnesses recovering the whole gap; an ablation localizing it to the linear
   boundaries) that **static activation quantization is a learned outlier suppressor the weights
   depend on** — plus the meta-lesson *"they are **equivalence gates, not quality gates**. An
   equivalence gate cannot detect a defect its reference shares."*

5. **"Quantization on Apple silicon: what actually survives, per tensor role and per routing."**
   Sources: `knowledge/compression.md`, `compression-reference.md`,
   `compute-units-and-authoring.md:55-104`, `dense-int4km-flagship-session-findings.md`,
   `diffusion-llms-dllm.md`, `conversion-guide.md:68-84`.
   Unique angle: the contradictions are the content. **int8 k-means is the LLM floor** *and*
   **`sym8` linear beats k-means for top-k ≥ 4 MoE experts** *and* **k-means beats linear for top-1
   routing** (error averages ~/√k) *and* **int4 is a cliff for dense LLMs but not for a diffusion
   LLM** *and* **fp4 buys nothing over int4-km on quality** (both 104/512 flips vs int8km's 32) —
   with the mechanism named each time. Plus: int8 is *not* faster on GPU (dequant to fp16) unless a
   custom kernel avoids the dequant; and the two mirror-image gating failures (int8 cos 0.9998 but
   visually broken; fp16 CPU cos 0.9 but GPU-perfect).

6. **"Bringing your own model to the Foundation Models framework."**
   Sources: `knowledge/fm-provider.md`, `dynamic-profiles-local-models.md`,
   `coreai-overview.md:49-58`, plus `evaluations-framework.md` and `agentic-security-checklist.md`.
   Unique angle: a real `LanguageModel`/`LanguageModelExecutor` conformance with working code, a
   capability matrix of what Apple's own `CoreAILanguageModel` adapter does and does **not** do
   (**no tool calling, no usage accounting, `prewarm` is a silent no-op, no KV reuse**), the
   **`PromptDialect`** finding (*"the training prior wins over the prompt"* — tool formats do not
   transfer across model families), and the **`@Generable` ⇒ needs logits ⇒ unavailable on
   GPU-pipelined bundles** constraint. Then `DynamicProfile` routing between **two local models** —
   *"the configuration Apple's demo does not show"* — with measured switch costs and the finding that
   **tool-based routing is unreliable while guided-generation routing works**.

7. **"Custom Metal kernels in Core AI: when they pay, and how to prove it before you build."**
   Sources: `knowledge/custom-metal-kernels.md`, `_tensorops_proto/*`,
   `_specdecode_proto/tree_attn_verify.py`, `compute-units-and-authoring.md`,
   `gemma4-raw-metal-*.md`.
   Unique angle: the **de-risk ladder as an artifact** (M0 → M1a → M1b → M2 → M4 speed A/B → device
   export), the negative results (per-op kernelization is *slower*; SSM decode kernel 3–8 %; fused
   wide prefill −34 %/−40 %; a naive `const float[16]` LUT spilling to stack), the **A19 ~8 µs vs M4
   ~3 µs per-dispatch cost**, `metal4_kernel` as a **fusion barrier with dtype-materialized edges**,
   the **`blockwise_shift_scale` all-zero-shift fast path**, and the recurring **DSL axis reversal**
   that has now caused at least two real bugs.

8. **"Reproducibility for on-device model catalogs."**
   Sources: `CATALOG_PLAN.md`, `CONTRIBUTING.md`, `PORTING.md` §9, both skills, PR #6.
   Unique angle: **`.aimodel` conversion is not byte-deterministic** (`main.mlirb` differs by 7 bytes
   run-to-run; published bundle differs by 492 B of 1.19 GB) so hashes are worthless and
   reproduction must be behavioural; the four-verdict model (`PASS`/`DIFF`/`FAIL`/`skipped`) with
   *"a deviation becomes correct by being recorded"*; `status = "unverified"` + a precise question as
   the correct output when the record is missing; 47 files with hardcoded home directories; a
   published metadata privacy leak; and **an upstream weight deletion (FastContext, 2026-06-30)
   permanently un-reproducing a port**.

9. **"Core AI vs MLX, honestly."**
   Sources: `knowledge/coreai-vs-mlx-speed.md`, `apple-models-bench.md`.
   Unique angle: an iso-protocol table (512p/1024g/5, M4 Max) showing **Core AI ties or wins every
   dense row and loses MoE by 28 %**, the causal decomposition (kernel coverage ~2× / quant byte
   class ~1.5–2× / framework tax ~1.3×), the **self-audit that retracts the author's own earlier
   advantage claims** (OS-resident runtime is "HALF-FALSE"; FM integration is not exclusive; iPhone
   reach is not exclusive), and the reverse differential — **logits/guided generation favour MLX**.
   Also the ANE/GPU/MLX iPhone triple with **energy** numbers.

10. **"Agent-run engineering repositories: contracts, guardrails, and gates."**
    Sources: `AGENTS.md`, both `skills/skills/*/SKILL.md`, `CATALOG_PLAN.md` "Instructions for the
    agent" + "Guardrails", `accel-levers-survey-and-plan.md` Part 3, PR #7's review.
    Unique angle: a mature, real-world agent contract — "Not your call" boundaries, *"never `pass` for
    a tier that did not execute"*, *"if the test's premise turns out to be wrong, report that rather
    than adjusting the result"*, *"Parallel = separate sessions, NOT background agents"* with a
    `_GPU_LOCK`, *"Don't claim a win until the bench shows one"*, and a maintainer's account of
    reviewing (and closing) agent-authored PRs.

11. *(bonus)* **"Static graphs and the shapes you must choose."**
    Sources: `PORTING.md` §4, `conversion-guide.md`, `chatterbox-port.md`, `flux2-in-context-editing.md`,
    `bitcpm-ternary-1.58bit.md`, `depth-anything-3-monocular-depth.md`, `aot-and-specialization.md`.
    Unique angle: a coherent treatment of "Core AI graphs are static-shape" as a **design discipline**
    rather than a limitation — bucketing with real-length masks (Chatterbox), one export per reference
    count (FLUX.2), `--static-ids` because the kernel is `M=1` (BitCPM), a square-graph + resize-back
    contract *validated against the model's own resolution variance* (DA3), passing RoPE as data so a
    T2I graph does editing unchanged (FLUX.2), and the `expectFrequentReshapes` landmine at both
    compile and load time.

12. *(bonus)* **"Speculative decoding on Apple silicon: the kernel is ready, the engine is not."**
    Sources: `_specdecode_proto/tree_attn_verify.py`, `accel-levers-survey-and-plan.md` Stream C,
    `flagship-full-tuning-stack.md` Axis 2, the `_smoke/specdecode_*.py` scripts.
    Unique angle: a runnable, gate-passing tree-attention verify kernel plus an explicit statement
    that the blocker is **Swift engine work (verify-forward `S=K` + draft→verify→rollback)**, not
    kernels — and that it is *"the single highest-leverage build in the whole plan"* because it is the
    **only lever that beats the decode bandwidth wall** and it is **lossless**.

---

## 13. Open questions / UNVERIFIED

### Things I could not verify from these repos

- **Which upstream commit the fork's `b1cb71b` corresponds to.** The fork has no upstream history,
  so the set-diff in §2.1 cannot distinguish "removed" from "predates". My reading is
  *predates*, but it is an inference.
- **The `ChatEngine.send()` caller half of `trimKVCache`.** `prefix-cache-kv-reuse.md` describes it
  in detail and `apps/coreai-prefix-cache.patch` presumably contains it, but the `CoreAIChatMac`
  source is not in either clone. The engine half (§2.4) *is* verified from source.
- **Hardware/OS for the `627fec7` measurement** (2.74 s → 0.40 s) and for the entire
  `prefix-cache-kv-reuse.md` table ("Mac", model unstated).
- **`ZOO_BLUEPRINT.md`** — referenced as the parent document of `CATALOG_PLAN.md`; not in the repo.
- **All `ondevice/_wwdc*_transcript.txt` files**, `litertlm-convert/`, `agent-demos/DualProfileChat`,
  `GEMMA4_METAL_LOOP_STATE.md`, `MLA_KERNEL_BREAKTHROUGH.md`, `ZAYA1_8B_CCA_VALIDATED_UNSHIPPED.md`,
  `_flagship_dense_coverage_audit.py`, `_qwen36_mac_bench.py`, `PipelinedBench`, and every
  `[[project_*]]` memory reference. **A large fraction of the archive's primary evidence lives
  outside these repos.** Numbers sourced only to those are second-hand *within* the community source.
- **`knowledge/coreai-models-apple-overview.md`** (PR #7) — closed, not in the clone.

### Internal contradictions in the archive (do not flatten these)

1. **HF Xet download advice.** `conversion-guide.md:151-153` says `HF_HUB_DISABLE_XET=1` does **not**
   bypass Xet and `curl -C -` **hangs** the bridge; `cross-runtime-quality-benchmarking.md:86-88` and
   `dense-int4km-flagship-session-findings.md:47-51` both recommend exactly `HF_HUB_DISABLE_XET=1`
   and `curl -C -`. Different dates; likely HF-side behaviour changed. **Cite with dates or not at
   all.**
2. **int8 scheme for LLM projections.** `compression.md` says **int8 k-means, group 32, all
   projections**. `compute-units-and-authoring.md` says **`sym8` (symmetric linear, block-32) CLEAN,
   k-means int8 lossier (+5 flips)** — for MoE experts at top-k ≥ 4 — and then reverses for top-1.
   These are about different tensor roles, but a careless reader will take them as one rule.
3. **Per-channel int8.** `compression-reference.md:21-24`: *"per-channel (axis-0) int8 Linear weights
   are **broken on the macOS-27-beta MPSGraph GPU delegate** … returns garbage."* Yet issue #3's
   submitted iPhone bench ran `qwen3_5_0_8b_decode_int8hu_**perchan**_sym` successfully, and the
   §6.2 recovery notes a `perchan_sym → block32_sym` rename. **Is per-channel broken only on macOS,
   only in some window, or was the shipped bundle silently degraded? Unresolved.**
4. **`exp()` in kernels.** `AGENTS.md` says subtract the max (the tree-attn prototype does);
   `gemma4-wna8o8-...` says namespace every transcendental as `metal::precise::` for cross-compiler
   determinism. `_specdecode_proto/tree_attn_verify.py` uses bare `exp`. Minor, but a guide that
   prescribes one rule should prescribe both.
5. **`coreai-overview.md:62-65`** says Apple's zoo *"lags ~one generation (Qwen3 / Gemma 3, no VLM)"*
   — but the current `apple/coreai-models` clone **does** contain SAM3, `qwen3_vl.py`, a VLM export
   path and `CoreAISpeech` (§2.1). The critique is time-stamped and **partially superseded**.

### Claims that would complicate Apple's story and need careful attribution

- **The macOS-26 vs macOS-27β lowering regression**: same recipe, same wheels, **2.2× slower artifact
  and 2× the memory** on the 27 beta, attributed to loss of native quantized-Linear lowering
  (`apple-models-bench.md:48`, `:196-200`). Community-measured; betas move.
- **`@Generable` guided generation is unavailable on the GPU-pipelined engine** because it samples
  on-GPU and does not expose logits (`fm-provider.md:84`, `coreai-vs-mlx-speed.md:124-129`,
  `coreai-overview.md:55-58`). This is a real constraint on the flagship FM feature for BYO models.
- **The LLM runtime is app-compiled, not OS-resident** (`coreai-vs-mlx-speed.md:102-109`), with the
  patchability of `apps/*.patch` offered as proof.
- **A `~O(p²)` prefill-scratch limitation inside the closed compiler that "cannot be fixed app-side"**
  (`coreai-vs-mlx-speed.md:113-115`). **UNVERIFIED mechanism** — no measurement is given in the files
  I read.
- **Apple's own documented fixed-shape/ANE stateful decode recipe does not run on the betas**
  (`coreai-beta-mpsgraph-kvwrite-bug.md:3-5`) — and Apple's own `KVCacheHandler` uses the crashing
  pattern (`aot-and-specialization.md:160-162`). Filed as FB23024751; check whether it has since been
  fixed before publishing.
- **`coreai-build compile` exits 0 for any `--architecture`**, so a successful compile does not
  validate the arch (`aot-and-specialization.md:116-118`).
- **`expectFrequentReshapes = true` on a fixed-shape graph SIGSEGVs on iPhone 17 Pro** at
  `AIModel(contentsOf:options:)` (`aot-and-specialization.md:88-106`).
- **TensorOps availability**: *"int4/int8 TensorOps = OS26 point update; fp4/fp8 = OS27"*
  (`accel-levers-survey-and-plan.md:143-144`). **UNVERIFIED against Apple docs.**
- **Apple's MLX-on-M5 "prefill 3.33–4.06×" figure does not hold on A19**, per this archive's own
  device A/B (`dense-int4km-flagship-session-findings.md:84-94`). If a guide quotes Apple's M5 figure
  it should carry this caveat.

### Things I'd want measured before building a guide on them

- The **pipelined-engine `trimKVCache` path is UNVERIFIED** (blocked on a `GrowingLogitsBuffer`
  SIGTRAP and single-turn iOS apps). Only the sequential path is proven.
- The **input-mask escape** for stateful KV is Mac-GPU-verified only; iPhone GPU/ANE pending.
- **Whether the looped-transformer (Nanbeige4.2) two-pass structure specifically widens the
  Mac↔iPhone gap** — the numbers are consistent with the non-looped 4.1 sibling, so probably not.
- The **MiniCPM5-1B inversion** (iPhone 66.8 > M4 Max 59.4 tok/s) is unexplained in the README.
- **Symbol spellings** in `evaluations-framework.md` and `agentic-security-checklist.md` — both docs
  say they are transcribed from talk captions and must be checked against Apple's docs.

### Sourcing rule to apply throughout

Every number in §7 and §9 is **community-measured by one person on one Mac and one iPhone, on beta
OSes**, except where a third-party citation is given (the industry survey in §5.7) or where the
measurement is of **Apple's own recipes with Apple's own runners** (`apple-models-bench.md` — the
strongest class of evidence here). Nothing in these repos is an Apple statement. Where this file
quotes a WWDC session, it is quoting **the community author's transcript of it**, not Apple.
