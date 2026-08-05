# GitHub Issue/PR Mining — MLX Stack (mlx, mlx-lm, mlx-swift-lm, mlx-swift-examples)

**Research session date:** 2026-07-27
**Method:** `gh` CLI against `ml-explore/mlx`, `ml-explore/mlx-lm`, `ml-explore/mlx-swift-lm`, `ml-explore/mlx-swift-examples`. Triaged ~280 issue titles + ~150 PR titles, deep-read ~35 threads. Everything below is grounded in text I read this session; anything not directly read is marked **UNVERIFIED**.

**Scope caveat:** These are *community bug reports and PRs*, not official docs. Many contain measurements from individual machines. Where a maintainer (`angeloskath`, `zcbenz`, `davidkoski`, `awni`) spoke, it is quoted and attributed. Where a non-maintainer made a claim, treat it as a strong hypothesis unless a second party reproduced it.

---

## 0. Version / release landscape (as of 2026-07-27)

From `gh release list`:

| Repo | Latest release | Date | Notable prior |
|---|---|---|---|
| `ml-explore/mlx` | **v0.32.0** | 2026-07-07 | v0.31.2 (2026-04-22), v0.31.1, v0.31.0 (2026-02-28), v0.30.6 |
| `ml-explore/mlx-lm` | **v0.31.3** | 2026-04-22 | v0.31.2, v0.31.0 (yanked-in-practice, see below), v0.30.7 |
| `ml-explore/mlx-swift-lm` | **3.31.4** | 2026-06-30 | 3.31.3 (2026-04-15), 2.31.3, 2.30.6, 2.29.3, 2.29.1 |
| `ml-explore/mlx-swift-examples` | (no release list pulled) | — | 2.29.1 referenced as "last known-good on iPhone 16 Pro" in #462 |

Notes:
- mlx-lm **0.31.0 was yanked** for "BatchKV cache cross-contamination" — stated by the reporter of mlx-lm#1425: *"I realize `0.31.0` was yanked for BatchKV cache cross-contamination, so this is **not** a request to recommend 0.31.0."*
- mlx-lm 0.31.3 (April) is the newest PyPI release, but `main` has moved substantially (PRs merged through late July). Several issues explicitly distinguish "0.31.3 release" vs "current main".
- mlx 0.32.0 was patch-bumped to **0.32.1** on the dev line (PR #3816 "Patch bump to 0.32.1" by zcbenz, merged 2026-07-08) — dev wheels are tagged `0.32.1.dev*`.
- Repo rename: `mlx-swift-examples` split — the library now lives in **`ml-explore/mlx-swift-lm`** (the examples repo has mostly older/closed issues; new library issues are filed against mlx-swift-lm). CONTRIBUTING was renamed in swift-lm PR #427 "Update project name in CONTRIBUTING.md".

### Maintainer bandwidth (mlx-lm#1475, OPEN, "Project status: what should contributors expect going forward?")

Filed 2026-07-05. Verbatim from the issue body:

> Commit velocity was ~50/month through Feb 2026, dropped to 1 in May, ~13 in June
> The last merge was June 24, there are 30+ open PRs, several of which fix a critical import crash with transformers ≥5.13 (the current default install). At least 5 independent PRs address this, submitted between June 25 and July 5, with no response yet.
> Open issues have zero labels or triage signals

Asks: is there still an Apple team reviewing; expected PR turnaround; roadmap; **community maintainers**. As of this session the issue has **1 comment** (a junior engineer +1) and **no maintainer reply**. Merged PRs did resume in July (e.g. #1501, #1504 by angeloskath on 2026-07-08; #1334, #1372 merged 2026-07-21/26), so the gap was partial, not total.

Contrast: `mlx-swift-lm` maintainer `davidkoski` is visibly active and responsive across many threads (see §9).

---

## 1. Memory, the Metal allocator, and OOM — the single richest theme

### 1.1 `mx.get_peak_memory()` does NOT include the buffer pool — mlx#3896 (OPEN)

**Title:** `mx.get_peak_memory() significantly under-reports actual GPU memory footprint on Apple Silicon (Metal)`

**Core problem (reporter, M5 Max 128 GB, mlx 0.32.0, macOS Darwin 25.4.0):** streaming a 198B MoE layer-by-layer, `mx.get_peak_memory()` reported **~46 GB** while the OS reported **~110 GB**:

```
footprint <pid>
  109 GB   IOAccelerator (graphics)   [all DIRTY, 0 reclaimable]
  phys_footprint: 110 GB
```

> "Trusting `mx.get_peak_memory()` as the memory-pressure signal allowed the process to exceed the machine's actual safe working set twice before the discrepancy was caught by external OS tooling: once via a full OS-level hard reboot, once via a Metal command-buffer GPU watchdog timeout (`[METAL] Command buffer execution failed: Caused GPU Timeout Error`)."

**Resolution / mechanism** (contributor `PhilipJohnBasile`, reading `mlx/backend/metal/allocator.cpp` v0.32.0):

```cpp
166:  active_memory_ += buf->length();
167:  peak_memory_ = std::max(peak_memory_, active_memory_);   // peak tracks ACTIVE only
189:  active_memory_ -= buf->length();                          // on free...
190:  if (get_cache_memory() < max_pool_size_) { /* buffer RETAINED in the pool */ }
132:  size_t mem_required = get_active_memory() + get_cache_memory() + size;  // mlx's own check
```

> "`peak_memory_` is a high-water mark of `active_memory_`, so it can never include the buffer pool. When you free a buffer it leaves `active` but is **retained** by the pool — still a live Metal allocation, still GPU-dirty, still in your `phys_footprint`. Note line 132: mlx's *own* memory-limit enforcement uses `active + cache`. So the library already knows the true number; `get_peak_memory()` just isn't it."

Measured churn loop (60 × ~500 MB alloc→eval→drop), GB:

| | `get_peak_memory` | `active` | `cache` | `active+cache` | OS footprint |
|---|---|---|---|---|---|
| baseline | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 |
| after churn | **1.00** | 0.00 | 60.06 | **60.06** | **60.19** |
| `cache_limit=0`, same churn | 1.00 | 1.00 | 0.00 | 1.00 | 1.14 |

**ACTIONABLE TAKEAWAY (guide-worthy):**
- **Gate memory-pressure logic on `mx.get_active_memory() + mx.get_cache_memory()`**, not `get_peak_memory()`. That sum matched the OS footprint to 0.2% in the churn test.
- `mx.set_cache_limit(0)` (or a modest cap) trades reallocation for a bounded pool — same churn ended at 1.14 GB footprint instead of 60.19 GB.
- `mx.clear_cache()` genuinely returns the memory, but **`phys_footprint` trails the call by a few seconds** (retraction comment: 0.00 cache at t+0 with 15.14 GB footprint; 0.02 GB at t+4 s). Don't sample immediately after and conclude there's a leak.
- Metal heap in mlx is `heap_size_ = 1<<20` (1 MB) and only serves buffers below `small_size_ = 256 B` — it cannot hold GBs, so a multi-GB "residual" is never the heap.

### 1.2 `[metal::malloc] Resource limit (499000) exceeded` — mlx#3849 (OPEN)

**Title:** "How can the Metal resource limit be queried or configured on macOS?"

Key facts established in the thread:
- The Metal backend reads sysctl **`iogpu.rsrc_limit`**; when unavailable it uses a **hardcoded `499000` fallback in `device_info.cpp`**.
- On macOS 26/27 the OID is gone: `sysctl iogpu.rsrc_limit` returns `unknown oid`. So the fallback is *always* what's used on current OSes.
- **`mx.device_info()["resource_limit"]`** reports the value MLX is actually using (reads back `499000`).
- `sudo sysctl iogpu.rsrc_limit=<n>` was suggested by **zcbenz** on mlx#3512 but "only does anything where the OID exists."
- **There is no `set_resource_limit`.** Quote (contributor `katlun-lgtm`): *"We expose `set_memory_limit`, `set_cache_limit` and `set_wired_limit`, but `resource_limit` is the odd one out: it's read once at init and never settable."*
- Standalone Metal probe on M4/32 GB/macOS 27.0: amortized 256 B/buffer up to exactly **2^19 = 524,288** buffers; from 524,289 onward `MTLDevice.currentAllocatedSize` grew 16 KiB per buffer. Direct allocation succeeded with **1.1 M** live buffers; heap-backed with **2 M**. Conclusion: 499000 "isn't a hard Metal limit on recent systems, it's just a conservative guard."

**The non-obvious cause found in-thread:** it is a *count of live Metal buffers*, and **`mx.compile` variant accumulation** can exhaust it.

> "compiled training with a fixed shape plateaus; compiled training with new sequence shapes grows when each new shape is introduced; ... the same variable-shape schedule in eager mode remains flat; calling `mx.clear_cache()` after every step does not stop the growth."
> "`mx.compile` keeps a cache entry per distinct input signature (shape + dtype + constants), and it's unbounded ... `mx.clear_cache()` only drains the allocator's *recycle pool*; it never frees a buffer that's still live."

**Fix:** `mx.compile(train_step, shapeless=True)` compiles a single variant with symbolic leading dims. Caveats stated: shapeless gives up shape specialization, and *constants* varying across calls still make distinct entries. There is an internal `detail::compile_clear_cache` (wired to interpreter exit) but **no public "clear the compile cache" API**; `disable_compile()` turns compilation off rather than reclaiming.

### 1.3 BufferCache reuse window defeats growing allocations — mlx#3886 (OPEN)

`BufferCache::reuse_from_cache` (`mlx/backend/common/buffer_cache.h` L30-38):

```cpp
T* reuse_from_cache(size_t size) {
  auto it = buffer_pool_.lower_bound(size);
  if (it == buffer_pool_.end() ||
      it->first >= std::min(2 * size, size + 2 * page_size_)) {
    return nullptr;
  }
```

For any buffer > ~32 KB the reuse window is just `[size, size + 32 KB)`. A **monotonically growing** allocation sequence (naive per-token KV append via `mx::concatenate`) misses the cache *every single request*, forever.

Measured (M4 Max 128 GB), per "decode step" appending one position to 10 pairs of `[4, N, 512]` bf16 buffers:

| pattern | ctx=512 | 1024 | 2048 | 4096 |
|---|---:|---:|---:|---:|
| A: `concatenate` **grow** (cache-miss) | 1.19 ms | 1.28 | 1.74 | 3.12 |
| B: `concatenate` at **constant** size (cache-hit) | 0.58 | 0.82 | 1.13 | 1.96 |
| C: preallocated + `slice_update` (donation) | 0.38 | 0.36 | 0.35 | 0.35 |

> "Scaled to a real 60-layer model (Gemma-4-31B), the growing-concat pattern costs **~50 ms/token at 4096 ctx in appends alone** — it single-handedly looks like a 'long-context decode collapse.'"
> "The rotting pool degrades **everything that runs later in the same process**: after a growing-cache phase, byte-identical unrelated workloads measured 10–35% slower until process exit."
> "The miss cost is CPU-side (`newBuffer` + wiring), so the GPU starves while the timeline shows nothing wrong on the GPU side — it profiles as idle gaps, not as a hot kernel."

**Takeaway:** mlx-lm's Python `KVCache` avoids this by preallocating in 256-step chunks with `slice_update`. **C++/Swift/custom cache authors must do the same.** Nothing in the docs warns about this. Cross-referenced from mlx#3896 as the amplifier of pool growth under jittered allocation sizes.

### 1.4 Unbounded live-buffer growth from lazy graph retention in caches — mlx-lm#1332 (OPEN)

DeepSeek-V4 (Flash/Pro) on Apple Silicon: `RuntimeError: [metal::malloc] Resource limit (499000) exceeded` after **~11,300 generated tokens, independent of prompt length**; after failure the Metal command queue is wedged until process restart.

Root cause (reporter's analysis, cross-checked against `mlx/backend/metal/allocator.h`):
- `resource_limit` is a **count** of live resident Metal buffers (`num_resources_` vs `resource_limit_`, backed by the `ResidencySet`). **No byte-budget knob (`set_memory_limit`/`set_wired_limit`/`set_cache_limit`) affects it.** At OOM only ~2–3 GB was leaked.
- `PoolingCache.update_and_fetch` does `self.pooled = mx.concatenate([self.pooled, px], axis=1)` each step; `pooled_N` references `pooled_{N-1}` in its input graph and the cache holds the head, so **every prior step's intermediate array and its Metal buffer stays resident** → ~1 retained buffer per layer per step → `499000 / 43 layers ≈ 11.3K steps`.
- `mx.eval(token)` does **not** detach cache intermediates. Adding `mx.eval([c.state for c in cache])` after the per-step eval collapses growth from ~205 KB/step to ~7 KB/step.
- `RotatingKVCache._update_in_place` and the `Batch*` variants chain identically via sliced functional assignment.

**Takeaway:** if you write a cache that builds arrays functionally (concatenate/slice-assign) rather than writing in place, **you must `mx.eval` the cache state each step**, or you leak one buffer per layer per step until the 499k resource limit fires.

### 1.5 Other memory/OOM threads worth citing

- **mlx-lm#1390 (OPEN)** — `mlx_lm.server` aborts with `libc++abi: terminating due to uncaught exception of type std::runtime_error: [METAL] Command buffer execution failed: Insufficient Memory (00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)` after the prompt cache grew to **23.35 GB / 26.28 GB**. Qwen3.5-4B-8bit on 48 GB, macOS 27.0 (26A5353q), Python 3.14.6, mlx-lm 0.31.3, huggingface_hub 1.18.0. Also notes `BrokenPipeError: [Errno 32] Broken pipe` when clients disconnect mid-stream leaves cache state behind.
- **mlx-lm#1395 (OPEN)** — "`fetch_nearest_cache` deep-copies the cached KV, doubling peak memory exactly when a cached conversation is reused."
- **mlx-lm#1572 (OPEN)** — "One-shot `mx.eval(model.parameters())` of >300 GB models triggers IOGPU command-buffer watchdog timeout at load (crash; fixed by chunked eval)."
- **mlx-lm#1480 (OPEN)** — Metal OOM during long-context prefill on Qwen3.6-35B-A3B-4bit at ~176K tokens on a 128 GB Mac, *despite* only 10/40 layers having a full KV cache (rest are `ArraysCache(size=2)` GatedDeltaNet). Points at transient prefill workspace, not KV size.
- **mlx-lm#1610 (OPEN)** — a downstream runtime's "context auto-fit" computes a context ceiling from `working_set=36.00GiB reserve=3.00GiB safe_ceiling=33.00GiB baseline=20.15GiB full_kv=20480B/token prompt_inputs=4096B/token attention=65536B/token` and refuses to allocate against OS file-cache pages. Useful as evidence of how downstream engines size context on Apple Silicon; per-token KV/attention byte figures are quotable.
- **mlx#3689 (CLOSED)** — "Use-after-free under memory pressure: buffer-cache trim frees an MTLBuffer still used by an in-flight command buffer (`kIOGPUCommandBufferCallbackErrorInvalidResource`)."
- **mlx#3803 (CLOSED)** — "Metal GPU timeout when loading large MLX models from NFS / external volumes; same snapshots work from internal SSD."

---

## 2. SDPA / attention kernel coverage — where MLX silently falls back

### 2.1 The routing table (mlx#3885, quoting `mlx/backend/metal/scaled_dot_product_attention.cpp`)

From issue #3885 body (routing at `use_fallback`, L621-633 in commit `0c537a41`):

- **Vector path (decode, qL ≤ 8):** `query_head_dim ∈ {64, 96, 128, 256}` **or** the `(192, 128)` combo. **No 512.**
- **Full path (prefill, qL > 8):** `query_head_dim ∈ {64, 80, 128}`. **No 192/256** (tracked in #3658/#3293), **no 512.**
- Earlier pin (v0.29.3, L395-400) is stated as identical for these shapes: `vector = {64, 96, 128, 256}, full = {64, 80, 128}`.

Anything outside these dims **silently** composes from `matmul → softmax → matmul` and **materializes the full `[B, n_kv, n_rep, qL, kL]` score tensor.**

> "today the only ways to notice the composite path are a Metal System Trace or reading `use_fallback`."

Requested (not landed): `MLX_FAST_LOG_FALLBACK=1` env var and/or a queryable `mx.fast.sdpa_is_fused(q_shape, k_shape, ...)` predicate.

### 2.2 head_dim=512 (Gemma 4 global layers) — mlx#3885 (OPEN, 10 comments)

Gemma 4 31B dense layout stated in the issue: **50 sliding layers (n_q=32, n_kv=16, d=256) + 10 global layers (n_q=32, n_kv=4, d=512, 25% partial RoPE).** At prefill **no layer of this model fuses at all.**

Measured decode (M4 Max 128 GB, bf16, qL=1, additive mask):

| shape | seqK=1024 | seqK=4096 |
|---|---:|---:|
| d=512, 32q/4kv (**fallback**) | 168 µs | 260 µs |
| d=256, 32q/8kv (same KV bytes, vector kernel) | 146 µs | 184 µs |

Prefill: at L=4096 a single d=512 global layer runs **84 ms and materializes ~1 GB of transient scores**.

The thread contains an extremely thorough experimental campaign (worth mining for a "how to benchmark MLX kernels" guide):

- A naive `instantiate_sdpa_vector(type, 512, 512)` + env gate `MLX_SDPA_VECTOR_512=1` compiles and is numerically correct on M4 Max, 6–13% faster than the fallback.
- **Critical correctness find:** on **M1 Max (`applegpu_g13s`)** the compiler register-limits both d=512 pipelines to **832 threads/threadgroup** (probed via `maxTotalThreadsPerThreadgroup`; every other head dim gets 1024):
  ```
  sdpa_vector_bfloat16_t_256_256           maxThreads=1024
  sdpa_vector_bfloat16_t_512_512           maxThreads= 832
  sdpa_vector_2pass_1_bfloat16_t_256_256   maxThreads=1024
  sdpa_vector_2pass_1_bfloat16_t_512_512   maxThreads= 832
  ```
  Two failure modes: 2-pass (`L >= 1024`) throws via `check_kernel_threadgroup_size`; **1-pass (`L < 1024`) dispatches a flat 1024 with NO size check at all — the launch is invalid, the GPU drops it, and the kernel returns all zeros.** `MTL_DEBUG_LAYER=1` flags it immediately.
- **GPU architecture-name classes** (corrected in-thread): `MTLDevice.architecture.name` suffix `'g'` = base chips **and iPads/iPhones**, `'s'` = **Pro and Max**, `'d'` = **Ultra**. Confirmed values seen: `applegpu_g13s` (M1 Max), `applegpu_g15s` (M3 Max), `applegpu_g16s` (M4 Max **and** M4 Pro per #3852), `applegpu_g16g` (M4 iPad Pro), `applegpu_g17g` (M5 base), `applegpu_g17s` (M5 Max). `devc` **cannot distinguish Pro from Max.**
- The 2-pass `blocks` heuristic already branches on that architecture character; the `'g'` branch picks 64 blocks and no Mac exercises it.
- iPad Pro M4 (16 GB, iPadOS 26.5.2) was the *greenest* device for a fused d=512: **77 wins / 20 ties / 8 losses of 105 cells** — consistent with 120 GB/s bandwidth making the fallback's extra traffic expensive.
- Proposed final gate: `(devc == 'd' || devc == 's') && n_kv >= 2 && 8 <= gqa <= 16 && kL >= 4096`, plus adding the missing `check_kernel_threadgroup_size` to `sdpa_vector`'s dispatch unconditionally.

**Takeaways for a guide:** (a) d=512 models eat a silent fallback everywhere today; (b) `maxTotalThreadsPerThreadgroup` per-pipeline probing is the right way to detect register-limited targets; (c) M1/M2-class GPUs cap some pipelines at 832 threads; (d) loss severity for large threadgroups tracks `32·gqa`.

### 2.3 head_dim=256 prefill — mlx#3658 (OPEN, 10 comments) / PR #3293 / PR #3660

Real-world evidence for reviving the fused d=192/256 `steel_attention` path.

On the unfused path each prefill chunk materializes scores against the *whole* cache, per full-attention layer:

```
transient ≈ n_q_heads × chunk_len × kv_len × 4 bytes
```

Mac Studio 36 GB, Gemma 4 26B-A4B 3-bit (head_dim=256, 30 layers, only 5 full-attention):

| Scenario | Result |
|---|---|
| Cold prefill ~130K tokens, 1024-token chunks | 226 s — completes, transient-bound |
| Default 2048-token chunks at long context | Metal OOM abort (`kIOGPUCommandBufferCallbackErrorOutOfMemory`) |
| Multi-turn past ~133K with memory ceiling active | guard shrinks chunks to 32–512 tokens → **a single turn's prefill takes 26+ minutes** |

> "At kv_len=130K, even a 32-token chunk allocates ~665 MB for scores alone."

A rebased #3293 branch measured (M4 Max 36 GB, n_q=16/n_kv=8 GQA, d=256, fp16), peak memory including inputs:

| qL | kL | inputs | fused peak | unfused peak | max abs err |
|---:|---:|---:|---:|---:|---:|
| 1024 | 32768 | 264M | **272M** | 1,824M | 0.0 |
| 2048 | 65536 | 528M | **544M** | 5,696M | 0.0 |
| 2048 | 131072 | 1,040M | **1,056M** | 11,328M | 0.0 |

Speed honesty: above the `kL>16384` routing threshold the **fused kernel is 0.74–0.79× of unfused on M4 Max** — i.e. *slower* when the transient fits. The value is purely memory.

**Maintainer ask (zcbenz):** *"Would it be possible to measure with the mlx-lm instead of oMLX? We are not familiar with oMLX's code so it is hard for us to check if this is something that we could fix without sacrificing the performance."* A subsequent clean `python -m mlx_lm.benchmark` A/B showed **no change** for Gemma 4 26B 8-bit at 32K/64K (prompt_tps 896.2→892.6; peak 31.078 GB both) — and the original poster issued a **correction** that Gemma 4's large-context global layers are `head_dim=512, n_kv=2`, so #3660 doesn't activate for them.

**Takeaway:** be very careful attributing Gemma 4 attention behavior to head_dim=256 — the *global* layers are d=512. The 256 shape is the bounded sliding-window one.

### 2.4 Decode SDPA bandwidth ceiling — mlx#3837 (OPEN, 6 comments)

M1 Ultra, mlx 0.32.0, `q=(1,32,1,256)`, `k=v=(1,4,100000,256)`, bf16, `mask=None`: **2.2–2.4 ms** ≈ 170–190 GB/s, while the same machine sustains **~680 GB/s** on a plain reduction → **~25–28% of achievable bandwidth**. For a 16-full-attention-layer model that's ~39 ms/token at 100k context (~43% of token time).

- `MLX_SDPA_BLOCKS` (**new in 0.32.0**) was swept; default selection is already optimal here.
- `q_len=2` costs 5.39 ms (≈2.2×) → **batched-verify speculative decoding at long context is gated by the same kernel.**
- A hand-written split-S flash-decoding kernel via `mx.fast.metal_kernel` (~100 lines MSL) reached **1.41 ms (~290 GB/s, 1.52×)** with max|Δ| ≤ 5e-4.
- Contributor `hxu296` proposed a register-resident KV reuse scheme; on M1 Ultra it **regressed to 4.84 ms** (register spilling, ~110+ live floats/lane), but with **fp16 accumulators** it jumped to 1.47 ms.
- **`hxu296` (contributor) conclusion:** *"I benchmarked the shmem staging variant vs. direct register kv-reuse variant on a M5-class machine. And it didn't throttle on register pressure. This is presumably due to the introduction of GPU dynamic caching since M3."*

**Architecture rule of thumb established:** **M3+** → register KV-reuse with fp32 accumulators; **M1/M2** → shmem staging or register reuse with fp16 accumulators; both plateau ~280–310 GB/s at `metal_kernel` level vs ~475 GB/s load-only.

### 2.5 The L=8→L=12 routing cliff — mlx#3826 (OPEN)

GQA 32q/8kv, head_dim 128, fp16, no mask, **M5 Max**:

| S (kv len) | L=8 | L=12 | L=16 | L=32 | L=48 | L=64 |
|---|---|---|---|---|---|---|
| 16384 | 0.813 ms | 1.906 ms | 1.903 ms | 1.904 ms | 1.904 ms | 1.588 ms |
| 32768 | 1.319 ms | 3.633 ms | 3.646 ms | 3.643 ms | 3.630 ms | 2.992 ms |

- L=8→12 is a **2.34× (16k) / 2.75× (32k)** jump for 1.5× the work; **flat plateau L=12..48**; recovers at L≥64.
- The vector kernel's small-L path caps at **L ≤ 8**; above that everything falls to a path tuned for much larger L.
- **Directly hits speculative decoding**: MTP / prompt-lookup / draft-model verify steps live at L≈4–16; batched short continuations at 12–48.
- Surprising corollary: *"the decomposed quantized attention (qmm→softmax→qmm) **beats** fp16 SDPA at L=16 at these S (0.35–0.48× its latency)"*.

### 2.6 `MLX_SDPA_BLOCKS` must be a multiple of 32 — mlx PR #3875 (MERGED 2026-07-22)

`MLX_SDPA_BLOCKS` was added in #3455 and validated only for `> 0`, but pass-2 in `sdpa_vector.h` iterates `blocks / BN` with `BN = 32` and integer division:

```cpp
for (int b = 0; b < blocks / BN; ++b) {
  max_score = max(max_score, maxs[simd_lid + BN * b]);
}
```

> "Any other value silently corrupts the attention output on every decode step — no error, no clamp."

Fix rounds the override up to the next multiple of 32. **Gotcha: if you set `MLX_SDPA_BLOCKS` on mlx ≤ 0.32.0, use a multiple of 32 or you get silently wrong attention.** Built-in choices are 32–1024, all multiples of 32.

---

## 3. Numerics: TF32, NAX, and cross-silicon divergence

### 3.1 `MLX_ENABLE_TF32` defaults to 1 — mlx#3860 (CLOSED/completed 2026-08-04, 9 comments) + PR #3894 (MERGED 2026-08-04)

**Title (retitled in-thread):** "fp32 matmul silently defaults to TF32-class precision (`MLX_ENABLE_TF32=1`), undocumented on both backends"

CUDA side: `enable_tf32()` in `mlx/utils.h` defaults `MLX_ENABLE_TF32` to `1`; `dtype_to_compute_type()` in `mlx/backend/cuda/gemms/cublas_gemm.cpp` then selects `CUBLAS_COMPUTE_32F_FAST_TF32` for `float32` (and `complex64`).

Relative Frobenius error, 512×512 fp32 GEMM vs float64:

| backend | rel. error |
|---|---|
| NumPy fp32 | 2.9e-07 |
| MLX CPU stream | 4.1e-07 |
| MLX Metal (M-series, pre-gen-17) | fp32-class |
| **MLX CUDA (default, `MLX_ENABLE_TF32=1`)** | **2.9e-04** |
| MLX CUDA + `MLX_ENABLE_TF32=0` | 2.1e-07 |
| MLX CUDA + `NVIDIA_TF32_OVERRIDE=0` | 2.1e-07 |

Metal side (added by `pierre427` and `mabaeyens`), plain fp32 512³ matmul GPU vs CPU:

| device | arch | native | `MLX_ENABLE_TF32=0` | forced `MLX_METAL_GPU_ARCH=applegpu_g16s` |
|---|---|---|---|---|
| M5 base | `applegpu_g17g` | 2^-10.4 | 2^-19.8 | 2^-19.8 |
| M5 Max | `applegpu_g17s` | 2^-10.4 | 2^-20.9 | 2^-20.9 |
| M3 Max | `applegpu_g15s` | 2^-21.7 | 2^-21.7 (bit-identical, max|Δ|=0) | — |

**The exact gate**, quoted from `katlun-lgtm` reading source:

> "on Metal every TF32 gate is `is_nax_available() && (env::enable_tf32() || dtype != float32)` — the steel and gather GEMM paths in `matmul.cpp`, `quantized.cpp`, and the SDPA gate — and **`is_nax_available()` requires macOS ≥ 26.2 and `arch_gen >= 17` (18 on `'p'` parts)**. So the flag is inert before gen-17 on Metal. On CUDA it isn't gated at all."

**Scope summary to memorize: CUDA → always; Metal → gen-17 (M5/A19-class) and up on macOS 26.2+.**

Two mechanics repeatedly cost people bisections:
1. **Shape-dependent:** matvec shapes (M=1 or N=1) don't take the NAX route and stay exact fp32. So the *same dtype + op* gives different precision by operand shape. `mlx-lm`'s `test_ssm` passes on the gemv-shaped output comparison and fails on the outer-product state comparison.
2. **First-use latched:** the env var is read lazily on first use. `os.environ["MLX_ENABLE_TF32"]="0"` **before the first matmul** works in-process; set any later it silently does nothing.
3. **Not limited to things that look like matmuls:** *"On gen-17 it also moves attention paths that compose from ordinary GEMMs rather than a fused kernel. We hit this at head_dim 96, which fails `sdpa_full_supported_head_dim` ({64, 80, 128}) and so never enters the fused path, yet still responds to `MLX_ENABLE_TF32`."*

**Downstream blast radius:**
- CUDA sm_120 fitting workload: flipped near-tie `argmax` on 1.4–2.5% of spectra, ~**9 dB PSNR loss**, while every op-level parity test passed.
- `mlx-lm/tests/test_generate.py`: **8 of 28 tests fail on gen-17** (all batch-vs-single equivalence, models pinned `set_dtype(mx.float32)`); all pass with the flag off.
- `mlx-lm/tests/test_models.py::test_ssm` fails out of the box on any M5 + mlx ≥ 0.32.
- mlx-lm **PR #1595** pins `MLX_ENABLE_TF32=0` in `tests/test_models.py` (but *not* `test_generate.py`).
- mlx **PR #3894** — **MERGED 2026-08-04 06:16 UTC** (`0b5e91f`), adding `docs/src/usage/precision.rst` (21 lines) plus an `index.rst` toctree entry. The landed page was deliberately **reduced to what holds independently of backend and hardware generation**: it names the affected op family (matmul, quantized matmul, grouped matmul, convolution, attention), says results "can differ from a full-precision reference by several orders of magnitude more than `float32` rounding alone would explain", and gives `MLX_ENABLE_TF32=0`. It does **not** carry the gen-17/macOS 26.2 Metal gate, the CUDA-always rule, the measured numbers, or the fp16/bf16 boundary sentence — all of which were drafted in-thread and then cut. The hardware-specific measurements were re-posted into the #3860 thread (2026-08-03) precisely because the docs page no longer carries them.
- mlx **#3860** — **CLOSED as completed 2026-08-04 06:22 UTC by `zcbenz`**, six minutes after #3894 merged: *"I'm closing this issue since this behavior is being documented in #3894, having a programmable switch would be nice but at the moment I think there is no necessarility to add that."* **This settles the API question: the env var is the only control, by decision rather than by omission.** The one-time log line agreed in-thread never landed (#3883 closed unmerged 2026-08-03), so there is still **no runtime signal** that reduced precision engaged.

### 3.2 Batched vs single-sequence attention diverges on M5 — mlx#3897 (OPEN, 7 comments)

M5 base (`applegpu_g17g`, 32 GB, macOS 26.5.2 / 25F84), mlx 0.31.2 and 0.32.0 both reproduce; M3 Max clean.

Model-level: `mlx-lm/tests/test_generate.py` fails 8/28 (`test_batch_matches_single`, `test_batch_sliding_window`, `test_batch_continued_generation*`, `test_stream_generate_input_embeddings*`) on `mx.allclose(batch_logprobs, single_logprobs)` at `rtol=1e-5`. Max |Δlogprob| ≈ **0.031–0.039** (i.e. ~1/32), argmax always matched.

**Two independent gen-17 mechanisms** were separated in-thread:
1. **fp16/bf16 divergence → the NAX attention kernel** (masked reduction differs at 64-aligned head dims). Only the arch override (`MLX_METAL_GPU_ARCH=applegpu_g16s`) moves it; `MLX_ENABLE_TF32` does nothing because `dtype != float32` satisfies the gate's third clause regardless.
2. **fp32 divergence → TF32 in fp32 GEMM on gen-17**, wider than attention; both flags move it identically, including at head dims that never reach a fused kernel.

Methodological lesson quoted verbatim (worth a callout box in a guide):

> "Your per-seed table shows the medians were hiding a 27-of-32 disagreement with a ten-seed tail up to 2^-13 ... The median was the wrong statistic and I should not have leaned on it for a claim about a *mechanism*."

**Takeaway:** a strict `rtol=1e-5` batch-equivalence assertion **cannot hold on gen-17**, in any dtype.

### 3.3 A19 (iPhone 17 Pro) shape-gated wrong fp32 matmul — mlx#3702 (CLOSED, 8 comments)

Real-world symptom: Hybrid Transformer Demucs source separation on **iPhone 17 Pro Max (A19 Pro, iOS 26.5.1)** produced **+12 to +21 dB of spurious 14–22 kHz energy** in every stem; identical code/weights clean on M2.

Things that did **not** fix it: `MLX_ENABLE_TF32=0` (verified applied), forcing `can_use_nax = false` in the metal backend (output *changed* but stayed corrupted), forcing rfft/irfft to `stream: .cpu`, upgrading mlx-swift 0.30.6 → 0.31.4.

**zcbenz (collaborator) response:**
> "They should have the same output whether correct or corrupted, it is possible that `MLX_ENABLE_TF32=0` is set too late. But I think the neutral accelerator is not relevant here since with or without it the results are still corrupted. To know what is happening I think the only way is to isolate the op that is outputting wrong results on A19, for example if the problem is in `matmul` it would be nice to have code demonstrating that it outputs wrong result for given matrices in gpu stream compared to cpu stream."

The reporter then produced a minimal mlx-swift fp32 `matmul` GPU-vs-CPU sweep on A19 (`iPhone18,2`):

- **[A] M=N=64, K swept:** diverges (~7e-4 to 9e-4 relative) for **K ≤ 127**; clean and **bit-identical to M2** for **K ≥ 128**.
- **[B] K=64, M=N swept 16…512:** diverges for **every** M=N.
- **[C] K=256, M=N swept:** clean for M=N ≤ 256; **diverges for M=N ≥ 384** (rel ~8.3e-4, max abs up to 6.7e-2).
- M2 control: worst relative **8.3e-7** across all three sweeps.

> "Whether a shape is affected is decided by the GEMM dispatch, not a single dimension."

Cross-references from the thread: the A19 lane-masking dot-product hardware bug documented at <https://tzakharko.github.io/apple-neural-accelerators-benchmark/> ("a bug with masking out unused lanes in the dot product hardware"); mlx PR **#3083** enables the NAX matmul path for `gen >= 18` phone architectures; mlx#3534 declared M5 NAX reduced precision "expected behavior"; mlx#3568 documents `mx.random.normal` producing different fp32 output on M1 Max vs M3 Ultra/M5 (traced to the FMA chain in the Metal `erfinv` kernel).

### 3.4 The A18 precedent — mlx-swift-examples#462 (reopened)

iPhone 16 Pro (A18) produced gibberish from every LLM on iOS 26.2/26.2.1 while iPhone 17 and M4 Max were fine. **davidkoski:**

> "There is no connection with Apple Intelligence so that shouldn't matter. The curious thing is that it shows up on the iPhone 16 Pro and _not_ the 17. The 17 would potentially be using the new neural accelerator (basically different Metal kernels). The 16 will be using the same ones that all the other (earlier) systems used."

Reporter bisected: **2.29.1 works; main fails**, and the same regression appeared in his own app on mlx-swift-lm 2.30.3 but not 2.29.3 → "mlx-swift is a good clue." davidkoski reproduced and fixed it upstream, then:

> "GitHub automatically closed this because the root cause is fixed. We still need that to be in an mlx build, then an mlx-c build, then an mlx-swift build and finally the dependencies here and mlx-swift-lm need to point to the new tags."

**Takeaway for a guide:** the fix pipeline is **mlx → mlx-c → mlx-swift → mlx-swift-lm / mlx-swift-examples**, four tag bumps. Expect lag.

### 3.5 Deterministic temp=0 output differs across Apple Silicon — mlx-lm#1280 (OPEN)

Same model (`mlx-community/Qwen3.6-35B-A3B-4bit`), same prompt, `temperature: 0`, same seed, same `max_tokens`: M5 Max vs M3 Ultra produced different generated-token counts (e.g. 7857 vs 6145 on one AIME25 case) though both reached the correct answer. Repro gist provided. Consistent with §3.1–3.2 (gen-17 TF32/NAX). **Cross-device bit-reproducibility is not a property MLX offers.**

---

## 4. Quantization correctness bugs (the scary ones)

### 4.1 Silent MoE corruption: affine `gather_qmm` int16 overflow — mlx#3856 (OPEN, 9 comments) → PR #3922

**Trigger, stated precisely:** flattened gathered row count `n` with **`n > 32768` AND `n % 64 != 0`**, on the **sorted-indices `gather_qmm` path**, **affine** mode, **NAX-only** (M5-generation GPU on macOS 26.2+). *"The bug cannot be reproduced on M1–M4 hardware."*

In an MoE forward `n = tokens × top_k`, which unifies earlier reports: at top_k=2 it looks like `tokens % 32`, at top_k=4 like `tokens % 16` — **the invariant is row alignment, not sequence length.**

Root cause, `mlx/backend/metal/kernels/quantized_nax.h#L1532-L1535` (commit `b7c3dd6d`):

```c++
const short sgp_sm =
    align_M ? SM : min(SM, short(max(0, (M - (y_row + tm)))));
const short sgp_sn =
    align_N ? SN : min(SN, short(max(0, (N - (y_col + tn)))));
```

> "`M - (y_row + tm)` ... is cast to `short` **before** the `min`. When `align_M == false` (`n % 64 != 0`, `BM = 64`) and a tile sits ≥ 32768 rows from the end, the cast wraps negative; a negative `sgp_sm` zeroes the A-tile and the store path stores nothing. Those output rows are **never written** and expose stale allocator memory."

#3631 fixed the identical pattern in three sibling kernels (`fp_qmm_t_impl`, the fp gather-rhs kernel, and affine `qmm_t_nax_tgp_impl`) but missed this fourth site — which is exactly why **mxfp4 tests clean while affine corrupts**. A twin lurks in `sgp_sn` (needs `N > 32768`).

Measured (M5, mlx 0.32.0):

```
mode=affine bits=4 n=32768 (n%64= 0): max|err|=0.0078  bad rows=0/32768
mode=affine bits=4 n=32802 (n%64=34): max|err|=16.9303  bad rows=64/32802
mode=affine bits=4 n=40002 (n%64= 2): max|err|=21.7688  bad rows=7264/40002
mode=affine bits=8 n=32802 (n%64=34): max|err|=16.5858  bad rows=64/32802
mode=mxfp4  bits=4 n=32802 (n%64=34): max|err|=0.0077  bad rows=0/32802
```

Model-level scoping table (M5, one-shot vs 2048-chunked prefill, N=16068):

| model | expert quant mode | max logit diff | argmax |
|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-8bit | affine 8-bit | 7.4 | diverged |
| Qwen3-Coder-Next-MLX-4bit | affine 4-bit | 10.8 | diverged (37/64) |
| Qwen3-Next-80B-A3B-Instruct-4bit | affine 4-bit | 3.3 | diverged |
| Laguna-XS-2.1-8bit | affine 8-bit | 17.8 | diverged (60/64) |
| DeepSeek-V2-Lite-Chat-4bit (MLA) | affine 4-bit | 6.7 | survived |
| Nemotron-Super-120B-5bit (hybrid) | affine 5-bit | 7.1 | survived |
| gpt-oss-20b | mxfp4 | 0.34 | ok |
| Qwen3-Coder-Next abliterated mxfp4-gs32 | mxfp4 | 1.28 | ok |

**Workarounds / fixes:**
- Downstream: **mlx-lm PR #1585** "switch_layers: pad sorted gather rows to a multiple of 64" — provably output-neutral (the unsort indexes only original rows).
- Upstream: **mlx PR #3922** "Fix sorted gather_qmm NAX boundary handling" (open at time of research) — clamps remaining row/column counts in `int` before narrowing.

**Regression-test note worth quoting:** *"unwritten rows hold whatever the recycled MTLBuffer last contained, which is sometimes coincidentally plausible. A regression test should poison the output buffer (or compare two runs) rather than trust one lucky read."*

Security framing from the PR author: *"this can leave tensor rows unwritten and expose contents reused from MLX's same-process Metal allocator pool. ... We found no cross-process disclosure, arbitrary code execution, sandbox escape, or other trust-boundary crossing, so this is a correctness bug rather than a cybersecurity vulnerability."*

### 4.2 Second, independent gather_qmm defect — mlx#3887 (OPEN)

`gather_qmm` sorted-rhs path corrupt for **`K % 64 != 0`** on M5/NAX: `!align_K` tail bounds the load with `BK` instead of the K remainder. Two differences from #3856: the trigger axis is the **reduction dim**, and **mxfp4 is affected too** (wider blast radius). Root-caused by `jundot` in `omlx#2267`, verified on M5 against 0.32.0.

### 4.3 nvfp4 split-K corruption — mlx PR #3854 (MERGED 2026-07-22)

`nvfp4` (`group_size == 16`) quantized matmuls taking the split-K path (`qmm_splitk` / `fp_qmm_t_splitk`) produced non-uniform ~2× error and `NaN`/`inf`. `affine` unaffected (group_size ≥ 32 keeps partitions ≥ BK).

Before:
```cpp
split_k = std::min(split_k, K / group_size);
while (split_k > 1 && (K % (split_k * group_size) != 0)) split_k--;
```
After:
```cpp
int k_align = group_size > 32 ? group_size : 32; // BK
split_k = std::min(split_k, K / k_align);
while (split_k > 1 && (K % (split_k * k_align) != 0)) split_k--;
```

Example failure: `K=64, group_size=16 → split_k=4, k_partition_size=16 < BK=32`.

### 4.4 NVFP4 tensor-scale is NOT implemented on Metal — mlx#3911 (OPEN)

PR #3022 added per-tensor scale (`global_scale`) for NVFP4 on **CUDA and CPU**. Metal explicitly rejects it (`mlx/backend/metal/quantized.cpp` L1725-1730):

```cpp
if (mode_ == QuantizationMode::Nvfp4 &&
    static_cast<int>(inputs.size()) > base_size) {
  throw std::runtime_error(
      "[QQMatmul] Global scale (tensor-scale nvfp4) is not supported "
      "on the Metal backend.");
}
```

> "Without tensor-scale support, NVFP4 on Metal has ~137x less dynamic range than NVIDIA Blackwell (unsigned UE4M3 vs signed E4M3 scales) ... This blocks NVFP4 quantization for Apple Silicon users running MoE models (DeepSeek-V3/V4, GLM-5.1, etc.)"

Related merged PR: **#3723 "[CUDA] Make qmv support global scale"** — *"`qqmm` reroutes to `qmv` when M=1, while the latter did not support global scales."*

### 4.5 2-bit loses its advantage at M ≥ 3 — mlx#3852 (OPEN)

M4 Pro (`applegpu_g16s`), mlx 0.32.0 wheel, macOS 15.6, group_size=128:

| shape (K→N) | bits | M1 | M2 | M3 | M4 | M8 | M10 | M32 |
|---|---|---|---|---|---|---|---|---|
| 5120→17408 | 2 | 0.121 ms | 1.30× | 1.82× | 2.34× | 4.53× | 7.3× | 7.3× |
| 5120→17408 | 4 | 0.198 ms | **0.99×** | 1.13× | 1.43× | 2.84× | 4.5× | 4.5× |
| 5120→248320 (lm_head) | 2 | 1.539 ms | 1.39× | 1.98× | 2.53× | 5.11× | | |
| 5120→248320 (lm_head) | 4 | 2.725 ms | **1.01×** | 1.14× | 1.47× | 3.03× | | |

At M=3 the two bit widths cost the same absolute time (0.221 vs 0.224 ms). **This kills 2-bit's speculative-decoding value** since verify width M = draft+1 = 2–6. Measured spec speedup 1.2× on a 2-bit 27B vs 1.6–2.1× on 8-bit models, same machine.

Dispatch facts established in-thread:
- gen 16 takes **`qmv_wide`** for affine at **M ≥ 2** (`use_qmv_wide`), up to **`get_qmv_batch_limit`** (10–12 at these dims), then **`qmm`**.
- Past the qmv batch limit the qmm path is **flat at 0.887 ms for every M from 10 to 32** — so M=10 pays the M=32 price.
- Half-precision arithmetic ran at identical speed (**no 2× half rate on M-series**), and `math_mode: "fast"` was a no-op for this kernel.

---

## 5. KV-cache quantization: the real story

### 5.1 `QuantizedKVCache` uses MORE peak memory during prefill — mlx-lm#1587 (OPEN, 11 comments)

Reported: Llama-3.2-3B-Instruct-4bit, M4 Max 128 GB, macOS 27.0:

| context | case | peak MLX memory | decode speed |
|---|---|---|---|
| 8,000 tok | fp16 | 3.46 GB | 3.2 tok/s |
| 8,000 tok | q8 | 4.87 GB (**+1.41 GB**) | 2.6 tok/s |
| 32,000 tok | fp16 | 4.72 GB | 1.0 tok/s |
| 32,000 tok | q8 | 7.10 GB (**+2.38 GB**) | 0.7 tok/s |
| 32,000 tok | q4 | 6.53 GB (**+1.81 GB**) | 0.6 tok/s |

Independently reproduced on M5 128 GB with Qwen3-0.6B bf16: 32,768 ctx → fp16 5.53 GB, kv8 **9.56 GB (+73%)**, kv4 9.09 GB.

**This thread is a model of adversarial debugging and the conclusion is precise.** Split prefill/decode measurement (fresh process per cell) on M1 MBP 16 GB:

| ctx tokens | fp16 prefill | q8 prefill | prefill Δ | fp16 decode | q8 decode | decode Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 255 | 2.213 | 2.166 | −2.1% | 1.908 | 1.851 | −3.0% |
| 257 | 2.193 | 2.294 | **+4.6%** | 1.868 | 1.841 | −1.5% |
| 8191 | 3.284 | 4.287 | **+30.5%** | 3.160 | 2.521 | **−20.2%** |
| 8192 | 3.284 | 4.288 | +30.6% | 3.160 | 2.521 | −20.2% |

**Verdict (after two rigs ran a pre-registered discriminator):** it is **NOT resize churn**. Presizing the cache (`c.step = <prompt+decode, rounded to 256>`, `step` is a *class attribute* on `QuantizedKVCache` in `cache.py`) eliminated all resizes and closed only **1.5% (M1)** / **3.8% (M5 Max)** of the inversion.

**It IS the unfused quantized attention path.** Chunk-size sweep at ctx=8192:

| `prefill_step_size` | quantized peak GB | fp16 peak GB (control) |
|---|---|---|
| 512 | 3.072 | 3.175 |
| 1024 | 3.821 | 3.290 |
| 2048 | 4.288 | 3.284 |

> "The predicted size of one layer's scores tensor (`n_kv_heads × n_repeats × L_chunk × context × 4 bytes`, 8×3×128 head config) gives a predicted delta between chunk 2048 and 512 of 1.208 GB; measured delta is 1.216 GB. That's the mechanism, not just consistent with it."

**IMMEDIATELY ACTIONABLE MITIGATION:** *smaller `prefill_step_size` trades prefill latency for lower quantized-attention peak.* At chunk=512 **the inversion disappears entirely.** (mlx-lm PR **#1611** "docs: note quantized KV-cache prefill memory tradeoff (#1587)" was opened for this; the README apparently doesn't document `--kv-bits`/`--kv-group-size` at all.)

**Negative finding worth its own callout:** a naive blockwise/online-softmax quantized attention *in Python* is **worse**, because MLX's lazy evaluation keeps every block's intermediates alive until the final eval:

| block size | naive (lazy eval) | forced per-block `mx.eval` |
|---|---|---|
| 256 | 5.620 GB (worse) | **2.856 GB** |
| 512 | 5.793 GB (worse) | 2.969 GB |
| 1024 | 6.272 GB (worse) | 3.309 GB |

Forcing `mx.eval` per block fixes memory but costs ~2× prefill latency. **The real fix is a fused quantized-SDPA Metal kernel.**

**On mlx PR #3026 (stalled fused quantized SDPA):** verified in-thread that `QuantizedScaledDotProductAttention::use_fallback()` returns true when **`query_sequence_length > 8`** (plus a `query_sequence_length * gqa_factor > 32` cap and `qsl > ksl` / head-dim gates). Chunked prefill passes qL in the hundreds–thousands (2048 default). **So merged as written, #3026 changes nothing about prefill memory** — it only engages for single-token or small-batch speculative decode. Its signature:

```
fast::quantized_scaled_dot_product_attention(
    queries, keys, key_scales, key_biases,
    values, value_scales, value_biases,
    scale, mask, sinks, group_size, bits, mode, causal)
```
vs mlx-lm's `models/base.py` `quantized_scaled_dot_product_attention(queries, q_keys, q_values, scale, mask, group_size, bits)` where `q_keys`/`q_values` are `(data, scales, biases)` tuples — "a call-site swap, not a rewrite" if it ever lands.

### 5.2 `--kv-bits` is a CAPACITY tool, not a throughput tool

Qwen3-32B-4bit, group_size 64, int8 KV vs fp16, paired runs (mlx-lm#1573, cross-posted to mlx#3026 and mlx-lm#1587):

| ctx | greedy-argmax agreement | PPL ratio | decode Δ vs fp16 |
|---|---|---|---|
| 0.5K | 0.9804 | 0.9965 | **−7.4%** |
| 4K | 0.9968 | 0.9966 | −3.1% |
| 16K | 0.9990 | 0.9991 | −2.7% |

> "on a 4-bit dense model KV is only ~19% of decode-step bytes — weights dominate, so halving KV bandwidth cannot pay for the compose/dequant overhead. So `--kv-bits 8` is a **capacity** tool (roughly half the KV bytes → longer context or more cache slots in the same RAM), bought at a few percent of decode speed. It is not a throughput lever."

Quality is genuinely clean and **improves with context**.

### 5.3 `quantized_kv_start` library default is 0 but the CLI default is 5000 — mlx-lm#1566 (OPEN)

`generate_step()` and `speculative_generate_step()` in `mlx_lm/generate.py` both default `quantized_kv_start=0`. The CLIs (`mlx_lm.generate`, `mlx_lm.cache_prompt`) default `--quantized-kv-start` to `DEFAULT_QUANTIZED_KV_START = 5000`. **A library caller that passes `kv_bits=` without `quantized_kv_start=` quantizes from token 0 and eats the full cost.**

Measured (M4 Pro 24 GB, mlx 0.32.0), 512-token prompt / 64 generated, decode tok/s:

| Model | fp16 | q, start=0 | q, start=5000 |
|---|---:|---:|---:|
| Qwen2.5-0.5B-Instruct-4bit | 424.6 | 352.2 (**−17.1%**) | 425.8 (parity) |
| Llama-3.2-1B-Instruct-4bit | 256.6 | 260.0 | 265.1 |

5120-token prompt (past threshold): Qwen2.5-0.5B 296.4→307.4 (**+3.7%**), Llama-3.2-1B 177.6→210.1 (**+18.3%**).

### 5.4 `RotatingKVCache.to_quantized()` raises NotImplementedError — mlx-lm#1573 (OPEN, 9c) + #1583 → PR #1584

`mlx_lm/models/cache.py:552`:
```python
def to_quantized(self, group_size: int = 64, bits: int = 4) -> QuantizedKVCache:
    raise NotImplementedError("RotatingKVCache Quantization NYI")
```

**Symptom:** `mlx_lm.server --kv-bits N` starts cleanly, `/health` 200, then crashes on the **first inference request** for any model with sliding-window layers. Gemma 4 26B-A4B: **35 of 42 layers** sliding-window in the reporter's config.

**Why a `hasattr` guard doesn't help:** `maybe_quantize_kv_cache` in `generate.py` does
```python
for e, c in enumerate(prompt_cache):
    if hasattr(c, "to_quantized") and c.offset >= quantized_kv_start:
        prompt_cache[e] = c.to_quantized(...)
```
`RotatingKVCache` **does** have `to_quantized` — it's defined and it raises. Presence ≠ implementation.

**Monkeypatch trap** (a workaround in production use, called out as harmful): returning a plain `QuantizedKVCache` for *every* layer silently **drops the `max_kv_size` bound**, so bounded-and-fp16 becomes unbounded-and-int8, crossing over as soon as a conversation runs past ~2× the window.

**Fix in flight: mlx-lm PR #1584** adds `RotatingQuantizedKVCache` + `BatchRotatingQuantizedKVCache`. Validated in-thread on Gemma 4:
```
before: {'RotatingKVCache': 25, 'KVCache': 5}   (n=30, sliding_window=1024)
after : {'RotatingQuantizedKVCache': 25, 'QuantizedKVCache': 5}
```
`max_size=1024` preserved on the rotating layers; with a 3,592-token prompt (3.5× the window) fp16 and kv8 produced **character-identical 60 tokens across the rotation boundary**.

**Remaining gap after #1584 — `keep > 0` is still unimplemented:**
```python
if self.keep > 0:
    raise NotImplementedError(
        "Quantizing a RotatingKVCache with keep tokens is not supported.")
```
and the generic fallback in `make_prompt_cache` uses:
```python
RotatingKVCache(max_size=max_kv_size, keep=4)   # cache.py:37
```
**So every model that does NOT define its own `make_cache`, run with `--max-kv-size N --kv-bits 8`, still raises after #1584.** Gemma 4 escapes only because `gemma4_text.py:683` passes `keep=0`.

Why the author declined to fix `keep>0`: `BatchRotatingKVCache` has **no `keep` concept at all**, not even a constructor argument, and `merge()` validates `max_size` while ignoring `keep` — *"merging `RotatingKVCache(keep=4)` instances into a batch already drops the sink tokens today, quantized or not."* Numerically the fix is safe because *"`mx.quantize` groups along the last axis (head_dim) while every slice and concat here runs along axis 2 (sequence), so each position's row stays independently quantized."*

Related landed/queued: mlx-lm PR **#1618** "Fail early for unsupported KV-cache quantization"; **#1619** "Fix rotated flag round-trip in `BatchRotatingKVCache.meta_state`".

### 5.5 gpt-oss + quantized KV = silent client timeout

From mlx-lm#1438: *"gpt-oss uses attention sinks, and a quantized KV cache raises `'Quantized SDPA does not support attention sinks'` from the generation thread. The thread dies, the request never returns, and the client sits until its own timeout, so it presents as a network timeout during prefill rather than as an error. KV quantization has to be off for this family."*

---

## 6. Prompt cache correctness (mlx-lm server)

### 6.1 mlx-lm#1494 (OPEN) — reuse can return KV that doesn't match the keyed prefix

`LRUPromptCache.fetch_nearest_cache` assumes (1) a stored cache's KV corresponds exactly to its token key, and (2) `is_trimmable() == True` ⟹ `trim(n)` exactly removes the suffix. **`KVCache` satisfies both; `ChunkedKVCache` (llama4 chunked attention) and `ConcatenateKVCache` do not**, and nothing verifies at reuse time.

Three defects: **A** silently wrong output instead of falling back to recompute; **B** the server's segment checkpointing then stores the mismatched state under the *new* key so subsequent exact hits reuse the bad entry; **C** a trim-contract problem in `trim_prompt_cache` itself. A model-free repro script is provided in the issue (`repro_prompt_cache_reuse.py`, exits 1 while bugs present).

### 6.2 mlx-lm#1495 (OPEN) — `LRUPromptCache` is FIFO, and 1-token prefixes never match

Two defects against `main @ 2ed2231`:

1. `PromptTrie.search` (cache.py L1578-1603):
```python
shorter = None
if last_index > 0:
    shorter = tokens[: last_index + 1]
```
`last_index` is an *index* (`-1` = none), so a stored one-token key matches at `last_index == 0` and the condition should be `>= 0`. Repro returns `PromptTrieResult(model='m', exact=None, shorter=None, longer=[7], common_prefix=1)`. For **non-trimmable (hybrid/recurrent) caches the entry becomes unreachable** — full recompute of a cached prefix.
2. `fetch_nearest_cache` (L1674-1694) never touches `self._lru`, and `CacheOrder` (L1630-1657) has **no touch operation** (only `push`/`remove`/`pop`) → **eviction is insertion-order, not LRU.**

Merged fix in this area: mlx-lm PR **#1607** "Avoid quadratic path copying in prompt trie search"; PR **#1078** "Fix `PromptTrie.pop_prefixes()` off-by-one when pruning immediate prefixes".

### 6.3 mlx-lm#1493 (OPEN, 10 comments) — server **livelock**, not deadlock

`mlx_lm.server` hangs immediately after prompt processing on ~22–26k-token *streaming* requests from a real client (Obsidian Copilot: `stream:true, temperature:0.1, max_tokens:16000`, system prompt + long mixed-language markdown). Same-size synthetic prompts, concurrency, and streaming individually all pass. Trigger appears to need **prompt-cache priming (two small completions first) plus a >22k real prompt**. Model `mlx-community/gemma-4-26b-a4b-it-8bit`, M5 Max 128 GB, mlx-lm 0.31.3, `--decode-concurrency 32 --prompt-concurrency 8`.

The decisive diagnostic: py-spy + `sample` over 6 minutes showed the loop **alternating between the forward call (`generate.py:1332`) and the eval sync (`generate.py:1369`)** with live AGXMetalG17X compute-encoding frames and real CPU time — **the batch keeps stepping and delivers zero chunks**. Meanwhile fresh trivial completions hung >180 s parked at `server.py:1037`/`1048` in `response_queue.get()` with no timeout; `GET /v1/models` returned 200 throughout; only `launchctl kickstart` recovered it.

> "This failure mode defeats both detection strategies discussed so far: `_generation_thread.is_alive()` (#1513 as written) — true the whole time; a naive per-iteration heartbeat — **would also tick**, because iterations are happening. The liveness signal has to be defined at the delivery level: *requests in flight + no tokens delivered to any consumer queue for N seconds* = stalled engine."

Fix in flight: mlx-lm PR **#1598** "Detect and recover from livelocked batch generation (#1493)" — a delivery-staleness watchdog with `--generation-stall-timeout` (default 60 s) that fails in-flight requests and resets the batch generator using #1513's recovery path. Stacked on **#1513** (exception/dead-worker recovery).

### 6.4 mlx-lm#1500 (OPEN) — idle server pins a core at 100%

`ServerModel._generate()`'s worker thread busy-polls:
```python
def get_next_request():
    if unprocessed_requests:
        return unprocessed_requests.pop()
    else:
        try:
            return self.requests.get_nowait()   # returns immediately when empty
        except QueueEmpty:
            return None
```
`sample`/`py-spy` shows the thread parked in `_PyEval_EvalFrameDefault`. Happens **even with no `--model`**. Proposed fix blocks with `self.requests.get(timeout=1.0)` when no batch is in flight.

### 6.5 Other server threads

- **mlx-lm#1505 (OPEN)** — "any uncaught exception in `_generate` leaves HTTP threads serving while every completion hangs forever."
- **mlx-lm#1472 (OPEN)** — generation thread dies with `TypeError ('NoneType' object is not iterable)` when a batch mixes requests **with and without logits processors**; server then hangs forever.
- **mlx-lm#1435 (OPEN)** — **uniform +55–77 ms TTFT regression** on 0.31.3 vs 0.27.1 on M3 Ultra, decode flat (±1.5%), independent of model size (Qwen3-0.6B and gpt-oss-20b both pay ~+55–77 ms) → constant per-call setup. Hypothesis: `with wired_limit(model, [generation_stream]):` + `mx.new_thread_local_stream(...)` now entered on **every** generation call.
- **mlx-lm#1425 (OPEN)** — Qwen3.5-35B-A3B-8bit decode −7.4% / −7.9% on 0.31.3 vs 0.31.0 (M3 Ultra 256 GB); sweeps of `prefill_step`, `completion_batch` did not recover it.
- **mlx#3727 (CLOSED)** — Regression 0.31.1→0.31.2: *"stream created in main thread is unusable from a worker thread — `There is no Stream(gpu, 0) in current thread` (breaks mlx_lm threaded server)."* Related merged fix: mlx-lm PR **#1090** "Thread local generation stream", and mlx PR **#3828** "Fix captured random state in compile."

---

## 7. Speculative decoding & MTP

### 7.1 temp=0 divergence is expected float non-associativity — mlx-lm#1470 (OPEN, 7 comments) → PR #1592

Report: `speculative_generate_step` diverges from plain greedy at temp=0 with `num_draft_tokens=4` (Qwen3-32B-6bit target + Qwen3-0.6B-MLX-6bit draft); ndt 1/2/3 matched.

**Resolution — three independent reproductions on three model families all found the same signature:**
- Qwen3-4B/0.6B: `mx.eval(l1376 == l1887)` → `True` — **tokens 1376 and 1887 are an exact bit-level tie at 38.0 in bfloat16.**
- Qwen3-32B-4bit + 0.6B-4bit: both candidates logit `33.75`, softmax `0.3828`, `logit_gap = 0.0` exactly, ranks 1 and 2, byte-identical across 3 repeats.
- Qwen3-8B-6bit + 0.6B-6bit: index 99, both logprob `-1.000000`, gap 0.0, adjacent ranks.

> "`speculative_generate_step` verifies in a batched target forward (`num_draft+1` wide) while plain `generate_step` runs sequential single-token forwards — same math, different reduction order, so the tie-break can flip between tied ids while staying quality-equivalent. 'Lossless' holds up to floating-point tie-break behavior."

Accept/reject code verified correct: `generate.py:622-634` is a pure greedy argmax-equality test; the rewind at `589-591` is `num_draft - n` for every `n`. Resolution is **documentation** (PR #1592 adds a `Note:` to the docstring), not a code fix.

**Guide-worthy falsifier recipe:** at the divergence index, replay through the plain sequential path and print both candidates' raw logits/probs/ranks. Gap ≈ 0.0 with both top-rank ⟹ benign tie. Materially nonzero gap with a dominant baseline token ⟹ real bug in accept/verify.

### 7.2 Hybrid/recurrent caches are not trimmable → spec decoding refused

**mlx-lm#1446 (OPEN):** `mlx_lm.server --draft-model` on Qwen3.6-35B-A3B (`qwen3_5_moe`) + Qwen3.5-0.8B raises
```
ValueError: Speculative decoding requires a trimmable prompt cache (got {'ArraysCache'}).
```
Two competing answers in-thread:
- **PR #1455** — validate at load and fail fast with a clearer startup error.
- A branch `lBroth/mlx-lm@gdn-exact-replay` implementing **exact rollback for `ArraysCache`**: during the verify forward, GDN layers record the exact per-token tensors the recurrent kernel consumed; on partial acceptance the recurrent state is rebuilt by replaying the recurrence over the accepted prefix (*"bit-exact by causality — no deepcopy, no re-forward, no weight restreaming"*); conv state is a slice of the captured conv input. **Also rewinds the *draft's* recurrent cache** (the 0.8B draft is a hybrid too). Validation includes a "bit-exact tail-independence" test: two verify chunks sharing an m-token prefix with different tails must leave identical caches AND next-token logits. Measured 0.77×–1.93× across M2/M3/M5 on 9B+0.8B; ~1.4× on 80B+0.6B.
- Prior art referenced: #1111 (snapshot + re-forward), #1297 (deepcopy snapshot per round), #1456 (same replay insight, qwen3_5-scoped/MTP).
- Also: mlx-lm PR **#1596** "Prompt cache trimming for recurrent/hybrid and sliding-window models via prefill-boundary state checkpoints".

### 7.3 MTP checkpoints are silently stripped — mlx-lm#1292 (OPEN, 5 comments)

Symptom: `mlx_lm.server` returns **1–72 token completions** (vs `max_tokens=400`) on Qwen3.6 MTP variants when the *system prompt is reused with a different user prompt*; non-MTP variants of the same models are fine. `usage.completion_tokens` truthfully reports the truncated count, so it isn't a parser bug.

Discovery in-thread: across `mlx_lm/models/`, **MTP weights are filtered out at load time**, e.g. `qwen3_5.py`:
```python
weights = {k: v for k, v in weights.items() if "mtp." not in k}
```
Same pattern in `qwen3_next.py`, `mimo.py`, `mimo_v2_flash.py`, `kimi_linear.py`, `nemotron_h.py`, `exaone_moe.py`, `ernie4_5_moe.py`, `step3p5.py`, `longcat_flash.py`.

And in `qwen3_5.py:312`: `should_shift_norm_weights = has_mtp_weights or has_unsanitized_conv1d` — so **MLX-converted MTP checkpoints get their norm weights shifted by +1 at every load** even though they no longer have unsanitized conv1d. Measured downstream: **−56% to −79% decode tok/s** for the Unsloth MTP variant vs the non-MTP base on M4 Pro and M5 Max.

Fixes: **PR #1306** (load-time warning that MTP tensors were discarded); **PR #990** (native MTP, decouples `should_shift_norm_weights` from MTP detection); **PR #1623** "Fix Qwen3.6 converted RMSNorm double shift".

### 7.4 N-gram / prompt-lookup self-speculation — mlx-lm#1497 (OPEN)

Proposal for hybrid GDN/SA models (Qwen3.5/3.6): CPU-side trigram→bigram→unigram `NgramDraftTable`, `ngram_speculative_generate_step()`, `--ngram-spec` / `--ngram-n` (default n=3), plus `ArraysCache.checkpoint()/rollback()/trim()` (~18 lines; `trim` is a no-op for `ArraysCache` — state-based, not offset-based) and a vectorized `GatedDeltaNet._conv1d_decode_multi()` for S>1.

Measured, Qwen3.6-27B (48 GDN + 16 SA layers), M2 Ultra 137 GB:

| Mode | Speed | Notes |
|---|---|---|
| Baseline (S=1) | 44.6 tok/s | bandwidth-bound |
| N-gram spec (1 draft) | 52.1 tok/s | **+17%**, 44% draft hit rate |
| N-gram spec (2 drafts) | 34.4 tok/s | 0.77× — S=3 overhead exceeds gain |

Swift sibling: **mlx-swift-lm#425 (OPEN)** "Prompt-lookup (n-gram) speculative decoding" and **PR #426**.

### 7.5 MTP self-speculation for disk-offloaded MoE measured DEAD

From the mlx-lm#1438 consolidated summary's "not worth building" list: *"MTP self-speculation at small disk fractions (≤+3% at its best draft depth despite 85.7% acceptance — the resident MTP head costs ~a full extra layer per draft, cancelling the batched-verify amortization; measured independently dead by iliria as well)."*

---

## 8. MoE expert streaming / SSD offload — mlx-lm#1438 (OPEN, 32 comments) + PR #1588

This is the single most substantive engineering thread in the mlx-lm repo and reads like a small research paper. Original ask: run `glm-community/GLM-5.2-mxfp4` (**~395 GB / 76 shards**) on a 128 GB M5 Max.

### 8.1 What shipped: `enable_offload` (mlx-lm PR #1588, open)

API added to `SwitchLinear` and `QuantizedSwitchLinear`:
```python
enable_offload(resident_slots, fetch_fn)
```
`fetch_fn(expert_id)` returns raw host data for one expert; the caller decides storage. Off by default, single-file change.

**Three hard-won implementation notes (quote-worthy, from the PR body):**
1. *"The cache is dict-keyed rather than a fixed slot array. With a fixed array, an eviction later in the same forward call can overwrite a slot an earlier expert already resolved to, because the gather runs only after every index in the call resolves."*
2. *"The `mx.array` for a fetched expert must be constructed on the thread that runs the model. **MLX arrays are thread-affine**, so building one on a worker thread crashes the first time the engine thread touches it. Split the disk I/O (parallel, thread-safe) from the array construction (on the calling thread)."*
3. *"seed the resident set from `fetch_fn`, not by slicing the loaded weight, and replace the weight with a 1-row stand-in. **A prefix slice of an `mx.array` is a view that pins the whole parent buffer**, so slicing does not actually free the rest of the table."*

Also critical: **`mlx_lm.load` with default `lazy=False` calls `mx.eval(model.parameters())`**, which materializes the full stacked `(num_experts, ...)` expert table at load time — an 18.2 GB spike on Qwen3.6-35B-A3B-4bit *before a single token*. Use `load(lazy=True)` and drop the full-table references before anything forces their eval.

### 8.2 Demonstrated results

| model | table | machine | fraction | result |
|---|---|---|---|---|
| Qwen3.6-35B-A3B-8bit | ~33.8 GB stacked | 32 GB Mac | 0.30 | loads + coherent, **peak 12.7 GB** (eager load impossible) |
| gpt-oss-120b-MXFP4-Q8 | **56.73 GiB** (60.99 GB decimal) | 32 GB | 0.30 | runs; 0.35 warns (23235 MB vs 25559 MB limit), 0.40 hard Metal OOM |
| Qwen3-235B-A22B-4bit | ~118 GB | 48 GB | 0.20 | runs (0.30 OOMs) |
| GLM-5.2 744B int4 | ~395 GB class | 128 GB | ratio ≈9 | in-engine (iliria, C/Metal) |

Throughput cost, Qwen3.6-35B-A3B, 3022-token prefill / 200-token decode:

| config | prefill cold/warm | decode | peak |
|---|---|---|---|
| 4-bit, offload off | 616 / 957 t/s | 57.1 t/s | 19.3 GB |
| 4-bit, offload on 0.3 | 77 / 76 t/s | 10.8 t/s | 7.3 GB |
| 8-bit, offload on 0.3 (over-DRAM) | 59 / 56 t/s | 6.6 t/s | 13.0 GB |

> "warm prefill is no better than cold, because a diverse prefill routes to nearly all 256 experts while the cache holds only 30%."

### 8.3 The consolidated design theory (verbatim structure from the thread's v1.5.1 summary)

**1. Fetch policy: reactive-only. Predictive prefetch carries signal but doesn't pay.**
Adjacent-layer expert Jaccard sits on chance for three architectures — Qwen3.6 (0.0178 vs 0.0159 analytic), Qwen3-Coder-Next-80B (0.990× vs shuffle), GPT-OSS (0.982× vs shuffle). *"independently-trained per-layer routers + the load-balancing aux loss decorrelate layers."* A measured depth-2 predictor A/B: decode **−2.9%**; prefetch removed 18.3% of synchronous reads but spent **~6.9 bytes of background read per byte saved** (precision 14.4% vs 3.1% random).

**2. Cache policy: plain per-layer LRU. Don't pin.**
Steady-state decode hit at 0.3 resident: **0.80–0.87**; Belady ceiling 0.90–0.94 (oracle-only). Pinning the K hottest experts loses to LRU **even trained and tested within the same session** (−6.6 / −9.5 pts on 2 of 3 topics); cross-topic −6 to −30. Online LFU: +0.3 pts ≈ nothing.

**3. Resident fraction is a function of table/RAM ratio, not a constant.**
Ratio ≈1.05 → 0.45 production sizing. Ratio 1.8 → 0.30 usable. Ratio 2.6 → 0.20 runs. Per-miss cost **rises** with fraction (240→258→280 µs across 0.30→0.50) as the resident set squeezes the page cache.
**The Apple sizing curve is a peak, not a monotone** (GLM-5.2-4bit, M5 Max 128 GB, 407 GB side-file): decode hit rises monotonically with materialized cache (0.24→0.60 over 20→75 GB) but **decode t/s peaks at ~30–35 GB and collapses past it** — 60 GB → 0.34, 75 GB → 0.17; **shrinking 60→35 GB is +65% decode**. Floor datum: at 10 GB the hit rate is 0% yet decode (0.40) still beats the 60 GB cache (0.34) — *"the OS page cache alone outruns a materialized cache big enough to starve it."*
**Never size "as big as fits"; on Apple the effective kernel page-cache reserve is tens of GB.**

**4. Layout coalescing pays iff the miss path is latency-bound.**
`speedup = 1 / ((1−s) + s/g)` where `s` = exposed cold-read share of the decode token, `g` = per-cold-expert I/O gain vs a **named** baseline.
`g ≈ 1 + saved_ops · t_op / (slice_bytes / BW)` with `t_op ≈ 100–122 µs`, `BW ≈ 6 GB/s` laptop / 13.5 GB/s M5 Max.
Measured: ~1 MB slices pay (A2 = 2.34×, A1 = 1.61×, Qwen3.6-8bit); ~4 MB bandwidth-bound slices don't (1.29× / 1.08×, gpt-oss).
End-to-end: Qwen3.6-35B-8bit **+17.6% @0.30 / +14.3% @0.45**; gpt-oss-120b **+9.7%**; **in-engine** Qwen3-235B-4bit @0.20 **A1 = +32.3% decode, −26.3% TTFT** (preads/token 2394→798), **A2 = +31.2% decode, −7.4% TTFT**; GLM-5.2 744B with an already-per-expert-contiguous container: residual g = 1.053 ⇒ ~1.3% wall (below a ±5% gate), weights stream at 13.4–13.6 GB/s (within 0.7% of device ceiling).
**The law:** *"coalescing is a latency lever, and model scale buys bandwidth-bound misses."*

**Read fragmentation baseline in mlx-lm as-shipped:** `up`/`gate`/`down` are **three separate modules with separate readers/LRUs**, and a quantized module reads `weight`, `scales`, `biases` as three separate open+seek+read calls → **up to 9 open+seek+read ops per cold expert per layer**; at hit 0.836 that's **~471 `open()` syscalls per decoded token**. Measured `open()` cost per projection: **40 µs current, 3.3 µs with the handle kept open, 1.5 µs mmap** — i.e. **~36 µs is the `open()` syscall itself and it is cache-independent** (+4.5% decode just from handle reuse).

**5. Anti-result:** *"mmap/page-fault streaming is layout-blind (identical tok/s and pageins across layouts in our CPU-mode apples-to-apples runs). If your streamer reads *slices* explicitly you get the layout win; if it demand-pages, you don't."*

**6. Far end:** at ~395 GB-class scale, active-expert **bytes/s** converges near hardware (**~16–18 GB/s** across two unrelated engines) and is the stable cross-engine metric; **tok/s spreads with model size alone**.

### 8.4 Measurement traps catalogued in the thread (each cost someone a run)

- **macOS `F_NOCACHE` does not evict already-resident pages** — reusing offsets across A/B arms silently turns arm 2 into a RAM read. Canary: an absurd result like a **0.18× "speedup."** Fix: fresh non-repeating offsets per arm, or swap arm order and check invariance.
- **Two different hit rates:** process-lifetime (dragged down by prefill: 0.664) vs steady-state decode (0.839) — *same run*. Always say which. (#1588 now ships phase-split counters because of this.)
- **Analytic-uniform is the wrong overlap baseline** when usage is skewed: GPT-OSS Jaccard reads 1.17× "signal" against analytic and 0.98× against a **shuffle control**. Use shuffle.
- **A/B harness flags passed inside a label string** → both cells ran the same arm. Canary: byte-identical hit rates across a supposed comparison.
- **fd reuse does not make small reads cheap**: a cached-fd 13.7 KB pread still measured **122 µs** (NVMe latency), not the 3–10 µs guessed.
- **GitHub code search silently skips files > ~350 KB** → confident false negatives.
- **Units:** 56.80 GiB = 60.99 GB. Two people quoted the same table and it looked like a discrepancy.
- **Concurrency is regime-dependent:** ~8-way pays on cold-disk streams, but at page-cache-warm sizing **2-way is optimal (+30% decode)** and 4/8-way *regress* under unified-memory contention.

### 8.5 Recommended build (from the summary)

> "reactive fetch + plain per-layer LRU + ratio-aware fraction + phase-split counters + overlapped loaders ... Not worth building: predictive prefetch (6.9:1 bandwidth cost), pinning, inter-expert read coalescing / profile-guided adjacency at ≥19 MB block sizes, MTP self-speculation at small disk fractions."

---

## 9. Swift stack: `mlx-swift-lm`

### 9.1 Fork consolidation — swift-lm#221 (OPEN, 18 comments)

Notable forks named: `ekryski/mlx-swift-lm`, `osaurus-ai/mlx-swift-lm`, `osaurus-ai/vmlx-swift-lm`, `SharpAI/mlx-swift-lm` (+ `SharpAI/SwiftLM`). Claimed fork benchmarks:

| Model | Upstream | Fork | Gain |
|---|---:|---:|---:|
| Gemma 4 26B MoE | 25.0 tok/s | **101 tok/s** | +304% |
| Qwen 3.5-35B MoE | 42.4 tok/s | **61 tok/s** | +44% |
| NemotronH 30B-A3B | ~25 tok/s | **48 tok/s** | +92% |
| Qwen 3.5-4B Dense | 123 tok/s | 145 tok/s | +18% |

**davidkoski (collaborator):**
> "No, I wasn't aware of these. Yes, if people are willing to contribute back, I think we would welcome PRs here. **Smaller PRs are easier to review.** I think it would be great if this work was able to be consolidated back here so everybody can use it."

Landed/announced from the forks in-thread:
- **#224** GDN precision fix — *"the gated delta kernel was accumulating state in bf16 instead of fp32 (precision loss at T>1)"*.
- **#225** pipeline prefill chunks with `asyncEval` — *"combined they take Qwen3.6-35B prefill from ~250 to ~3100 tok/s on M5 Max"* (10× on GDN models).
- **#227** `FusedGateUpSwitchGLU` (single fused `gate_up_proj` for MoE).
- **#228** Gemma 4 26B router fix — *"softmax was applied to all 128 experts **before** top-k selection instead of after"*, plus fusing norm+scale from 3 dispatches into 1 → ~10% decode.
- **#229** dtype promotion in segsum — `MLXArray(-Float.infinity)` creates an **fp32 scalar**, causing `which()` to promote the whole bf16 output to fp32: *"~960 MB wasted on Qwen3.5-35B at 2k context, ~24 GB on Nemotron-30B. one line fix."*
- **#222** Qwen2.5-VL: 7 bugs — biggest single root cause was `scaledDotProductAttention` in the vision encoder called with `mask: .none`, so **every image patch attended globally instead of using windowed attention**. After the fix, Swift matches Python `mlx-vlm` at ≤2 px on all 8 bbox edges (6/8 bit-exact).
- **`ml-explore/mlx-c#113`** guards `mlx_array_dim` against 0-dim and out-of-bounds — *"crashes non-deterministically during Swift Module subclass initialization when lazy evaluation hits scalar arrays."*
- **`ml-explore/mlx#3461` / PR #3462** — *"metal CommandEncoder doesn't retain bound buffers under `MTLResourceHazardTrackingModeUntracked` + `commandBufferWithUnretainedReferences()`, so swift structured concurrency dropping the MLXArray ref between encode and CB completion hits an Invalid Resource race."* Validated on M5 Max: **0/10 → 10/10 at qwen35-35b-a3b B=17, 0/5 → 5/5 at B=32; ~2.4% throughput cost.** Described as *"a nasty bug that causes weird conditions due to buffer pointers getting clobbered. Can lead to random crashes or model incoherence."*

### 9.2 Upstreaming perf batch — swift-lm#466 (OPEN)

A systematic pass over Qwen3.5/3.6 hybrids (4-bit PARO, M3 Max), gated **token-identical** in interleaved A/B and bitwise for kernel changes. Planned PRs in mlx-swift-lm (all filed): **#467** compiled decode step, **#468** GDN conv1d as fused multiply-adds, **#469** fused router top-k Metal kernel (*"today every decode token fully sorts all 256 expert scores to pick 8, because argpartition delegates to sort"*), **#470** balanced prefill chunking (*"~9% prefill at prompt lengths that end in a degenerate last chunk"*), **#471** ParoQuant MoE (**35B load 41 s → 9 s**).

mlx-core side: **#3918** rows-per-expert-aware `gather_qmm_rhs` tile geometry (**MoE 32K prefill +6%**, kernel itself +13–22%), **#3919** fused causal-mask+softmax for the SDPA ops fallback (*"removes a 512 MB intermediate per layer chunk"*), **#3920** eval-path CPU overhead (flat degree map in `eval_impl`, gather identity-index cache).

Aggregate claim: **35B MoE decode ~1.25–1.3×, prefill ~1.1× at 8K / ~1.15×+ at 32K, load 4.6× faster; 4B dense decode ~1.06–1.09×, peak memory −9 to −13%; outputs token-identical everywhere.**

Deferred, with reasons: the custom-kernel-source memoization was half superseded by **mlx#3869** ("[Metal] Avoid regex in custom kernel name generation"); the command-buffer commit accounting pair needs re-implementation because *"the Metal command-buffer machinery has since been restructured (DeviceStream merged into CommandEncoder, thread-local encoders)."*

### 9.3 `MLXFoundationModels` — the Apple FoundationModels bridge (HIGH cross-link value)

This is the layer that lets an MLX model back Apple's `LanguageModelSession` / `ChatSession` APIs. Four issues/PRs here matter a lot for a Foundation Models guide.

**swift-lm#432 (CLOSED) → PR #434 (MERGED 2026-07-22): nested `@Generable` types break tool calling.**
Any `Tool` whose `Arguments` contain a nested `@Generable` type fails at the first tool-calling turn:
```
constraintCompilationFailed("... json_schema_converter.cc:957: Check failed: ...
Cannot find field $defs in {"oneOf": ...
```
Root cause: `GenerationSchema` serializes the nested type as **`$defs` + a root-anchored `"$ref": "#/$defs/Traveler"`**. `SchemaConverter.toolCallingEnvelopeObject` embeds the tool's schema as a nested object under `oneOf[i].properties.arguments`, burying the `$defs` inside `arguments` while the `$ref` still points at the (empty) envelope root. **xgrammar resolves JSON Pointers from the document root → dangling ref → hard check failure.** *"Flat tools (only primitive fields) work, which is presumably why this hasn't surfaced — demo-sized tools don't produce `$defs`."*
Fix: hoist each tool's `$defs` to the envelope root, namespaced per tool (`<tool>__<def>`), rewriting that tool's `$ref`s. **Implementation gotcha:** *"the ref rewrite runs on the raw `JSONEncoder` output, where the `#/$defs/` prefix appears literally. Rewriting a `JSONSerialization` re-serialization does not work — it escapes `/` as `\/`, the prefix never matches, and the refs silently survive unrewritten."*

**swift-lm#433 (CLOSED) → PR #435 (MERGED 2026-07-17): `.toolCalling` on a VLM-loaded model is a process-killing abort.**
```
MLX/ErrorHandler.swift:345: Fatal error: SmallVector out of range.
  at .../mlx-c/mlx/c/array.cpp:335
```
Isolation matrix from the issue:

| Model | Capabilities | Image | Result |
|---|---|---|---|
| Qwen3-8B (LLM factory) | `[.toolCalling]` | no | ✅ |
| Qwen3-VL-4B (VLM factory) | `[.vision]` | yes | ✅ |
| Qwen3-VL-4B (VLM factory) | `[.vision, .guidedGeneration]` | yes | ✅ |
| Qwen3-VL-4B (VLM factory) | `[.vision, .toolCalling]` | yes | 💥 fatal |
| Qwen3-VL-4B (VLM factory) | `[.toolCalling]` | **no** | 💥 fatal |

Root cause (PR #435): the tool-calling path hand-built `LMInput(tokens: MLXArray(toolAwareTokens))` — a **1-D `[N]`** array. That works for text models (default `LLMModel.prepare` slices with `[.newAxis, ...]`) but **every VLM `prepare` consumes `input.text.tokens` as given and indexes `dim(1)`** (e.g. `getRopeIndex` in Qwen3VL) → `mlx_array_dim` → `shape.at(1)` → uncatchable abort. A second defect in the same path: it re-templated text-only, **silently dropping image/video content from tool-calling prompts.** Fix: route through `context.processor.prepare(UserInput(chat:tools:additionalContext:))`.

**swift-lm#441 (OPEN) → PR #456 (MERGED 2026-07-23): multi-round tool calling.**
Before #456 a session could issue **at most one tool call**. #456 is ~3,200 lines across `MLXFoundationModels`, `MLXLMCommon`, `MLXGuidedGeneration` (about half tests). It adds:
- Multi-round replay of prior tool calls + results into the prompt, **no iteration cap**, matching `LanguageModelSession`/`ChatSession`.
- `ToolCallingModeResolution` (automatic / required / disallowed), including preventing fallback to a plain response when a tool is required.
- `AllowedToolOutputRouter` — native generation routing, ordered streaming at parse boundaries, EOS residuals, unfinished protocol tails.
- Structured FM tool outputs preserved rather than flattened to strings.
- `GuidedGenerationDiagnosticSink` (dormant unless bound).
- In `MLXLMCommon`: a **public `Output` enum (`.response` / `.toolCall`)** with `processChunkOutputs`, `processEOSOutputs`, `drainToolCalls` that emit events **in the order the model produced them** (previously text and tool calls were returned separately, losing relative order).
- End-of-stream reconstruction per format: Mistral `[TOOL_CALLS] ... [ARGS] {...}`; LFM2 pythonic `[func()]` via bracket balancing.
- **Quote-aware JSON scanning** replacing naive brace counting (so `{"path": "a}b"}` no longer terminates early).
- Qwen redundant-brace recovery for `{{ ...valid call... }}`.
- Removed the synthetic "final-answer tool."

**swift-lm PR #439 (MERGED 2026-07-17): FoundationModels SDK symbol drift — a SIGSEGV.**
The FM-27 beta `.swiftinterface` declares
```
LanguageModelExecutorGenerationChannel.Response.Action.updateUsage(input:output:metadata: = [:])
```
but the **shipping FoundationModels dylib exports only the older two-parameter `updateUsage(input:output:)`**. Calling the 2-arg form and relying on the `metadata:` default resolves to the 3-param symbol, which doesn't exist at runtime → dyld can't bind → `KERN_INVALID_ADDRESS at 0x0` on every `respond()`.
> "A runtime dlsym/availability guard cannot help here: under chained-fixups linking (the arm64 default) the compiled reference alone aborts the process at load, before any guard executes. Not referencing the symbol is the only safe option."
Confirmed with `dyld_info -exports`. Fix: remove the `channel.send(.updateUsage(...))` call entirely; `generationObserver` notification preserved.

**swift-lm PR #438 (MERGED 2026-07-17): FoundationModels API drift generally.**
> "The current FoundationModels SDK (macOS, iOS, and visionOS 27) changed its generation API. ... The values the framework uses to stream a response (generated text, tool calls, usage, and metadata) **became opaque**. Code that receives them can see that something was produced but can no longer read what it was."
Solution: a test-only observation shim; tests read readable copies while the framework still receives identical calls (and the opaque events must still be drained *"so that sending into the framework does not stall."*)
Also: **PR #431** "Track the current SDK's `SamplingMode.Kind` case names" — beta seeds renamed `randomTopK`/`randomProbabilityThreshold` ↔ `.top`/`.nucleus`. **This churns between Xcode 27 betas; expect local 2-line renames.**

Environment strings seen in these threads: **macOS 27.0 beta (26A5378n), Xcode 27 beta**; also `macOS 27.0 build 26A5353q`.

### 9.4 Swift KV cache bugs

**swift-lm#312 (OPEN, 6 comments): `maybeQuantizeKVCache` silently corrupts context mid-generation.**
> "`maybeQuantizeKVCache` is called on every step inside `TokenIterator`'s generation loop. When the `quantizedKVStart` threshold is crossed mid-generation, it replaces elements in `TokenIterator`'s local copy of the cache array with new `QuantizedKVCache` instances. Because the function takes `cache: inout [KVCache]`, it replaces array **elements** rather than mutating the cache objects in place. The caller's array (in `ChatSession`) still holds the original `KVCacheSimple` references ... The model loses all context generated after the quantization threshold."
Also: `!(firstQuantizable is QuantizedKVCache)` on line 1806 is dead code — `cache.first(where: { $0 is KVCacheSimple })` can never return a `QuantizedKVCache` because `QuantizedKVCache` inherits from `BaseKVCache`, not `KVCacheSimple`.
**davidkoski's proposed design:**
```swift
class KVCacheBox : KVCache {
    var implementation: KVCache
    // forwards
}
```
> "I think making a box type like this is probably the way to go — it will give us the most flexibility in terms of having behavior over the full KVCache and let us fix this problem. ... I do think that a higher level type that represents the collection of `KVCache` instances might be better. It would be nice to call it `KVCache` but that name is taken for the per-layer ones. The drawback: it doesn't match the python plain-list implementation."
Fix in flight: **PR #358** "Fix KV cache quantization: cache updates lost due to value-type propagation."

**swift-lm#424 (OPEN): `RotatingKVCache` becomes untrimmable once the window wraps.**
`RotatingKVCache.isTrimmable` is `offset < maxCacheSize`, and `offset` only grows.
1. **Silent spec-decode corruption:** `SpeculativeTokenIterator.speculateRound()` rewinds rejected drafts with `trimPromptCache(mainCache, numTokens: numDraft - accepted)` **and discards the result**. `trimPromptCache` guards on `canTrimPromptCache` = `allSatisfy { $0.isTrimmable }`, so **once one sliding layer wraps the whole rollback returns 0 silently** and generation continues on a transcript containing tokens that were never emitted. On Gemma-family models the sliding window is small (e.g. 512), so a single long reply is enough. `MTPSpeculativeTokenIterator` already trims by the amount actually reported.
2. **Prefix reuse degrades to full re-prefill post-wrap.**
3. **`RotatingKVCache.trim()` does not self-guard** — called directly on a wrapped buffer it still decrements `offset`/`idx` and returns nonzero, corrupting the circular-buffer mapping.
Cross-effect noted by `NivDvir`: for M-RoPE VLMs (Qwen2/2.5-VL) decode positions are `cacheOffset + ropeDeltas`, so the no-op rollback **also inflates the offset and generates at drifted positions** — silent, post-wrap only.

**swift-lm#406 (OPEN): `KVCacheSimple.offset` is a Swift `Int`, which breaks `MLX.compile()` decode.**
```swift
let previous = self.offset          // Swift Int → constant in compiled graph
self.offset += keys.dim(2)
self.keys?[.ellipsis, previous ..< self.offset, 0...] = keys
let returnedKeys = self.keys![.ellipsis, ..<self.offset, 0...]
```
`innerState()` does not include `offset`, and slice indices derived from a Swift `Int` are not graph nodes. With `shapeless: false`, recompilation triggers on **input array shape** changes, not integer-constant changes. Result: write position frozen at trace-time offset; attention window frozen. Observed on Qwen2.5-7B-Instruct-4bit greedy: uncompiled 42 tokens + EOS; compiled 64 tokens with a **4-token repeating cycle** (`3535, 11, 432, 4977, 1075, 11, 432, 4977, 1075, …`). Suggested fixes: graph-traceable `MLXArray` offset; functional cache step; or a dedicated compile-friendly cache type.

### 9.5 Swift VLM memory / correctness

**swift-lm PR #455 (MERGED 2026-07-22): Qwen3VL vision prefill memory.**
Two compounding causes:
1. All images merged into one attention sequence via a dense `[1, L, L]` additive `-1e9` mask, so attention memory grows with **(Σ Lᵢ)² instead of Σ Lᵢ²** — two images totaling 8140 pads requested a single **33.9 GB** Metal buffer, **past `maxBufferLength` on a 48 GB M4 Pro**.
2. **Qwen3VL's vision tower head dim is 72** (1152 / 16 heads), outside the fused Metal kernel's supported {64, 80, 128}, so `MLXFast.scaledDotProductAttention` **silently falls back** and materializes `numHeads × L² × 2` bytes.

Fixes: attend each `cuSeqlens` segment independently with **no mask** (mathematically identical to the block-diagonal mask; same as `mlx_vlm/models/qwen3_vl/vision.py`), and **zero-pad head dim 72 → 80** so the fused kernel dispatches (*"the same trick as `gemma4EnsureFusedSDPA` in this repo (and mlx-vlm's `ensure_fused_sdpa`). Padding is exact: the padded dims contribute nothing to the dot products and `scale` is passed explicitly."*)

| case | before | after |
|---|---|---|
| single image, 6188 pads | 28.7 GB peak | 12.6 GB peak |
| two images, 8140 pads total | fatal (33.9 GB > maxBufferLength) | 14.2 GB peak |
| two-image prefill wall | 59.8 s | 36.3 s |

**M-RoPE state loss (three linked issues):**
- **#419 (MERGED PR)** — prefill `LMOutput.State` dropped on `TokenIterator`'s `.logits` path.
- **#420 (OPEN)** — M-RoPE state dropped **across `ChatSession` turns**: *"`LMOutput.State` (which carries the M-RoPE `positionIds`/`ropeDeltas` since #239/#283) dies with each turn's `TokenIterator`. On the next turn the Qwen VLM position branches see a warm cache with no rope deltas and recompute positions from zero."* Fixed for Qwen3.5/3.6 by **PR #399**; still open for Qwen2.5-VL / Qwen2-VL / Qwen3-VL (PR #448 wires them).
- **#443 (OPEN)** — `savePromptCache`/`loadPromptCache` drop `LMOutput.State`: *"`ChatSession.saveCache(to:)` matches `.kvcache(let cache, _, _)` and passes only the KV arrays ... The safetensors layout has no slot for it, `loadPromptCache` returns only `([KVCache], metadata)`, and both cache-accepting `ChatSession` initializers hard-code `state: nil`."* Quantified in #399: on a tiny random-weight model warm turn-2 logits diverge from a cold full prefill by **0.43 max-abs** against an **8.3e-07** decode-path noise floor. *"At temp 0 on dense grounding prompts this can flip bbox output silently."*
- **PR #411** Qwen3VL: apply the sRGB tone curve in image preprocess (issue #410: linear-light values made dark content unreadable).
- **PR #398** Qwen3VL: default per-image resolution to a **1,280 vision-token budget** (issue #396: uncapped resolution let the ViT allocate tens of GB).

### 9.6 Gemma 4 in Swift — a long tail of loader/parser gaps

- **#231 (OPEN)** `Gemma4Text.swift` K-eq-V path double-transposes V → `Fatal error: [broadcast_shapes] Shapes (1,512,4,512) and (1,4,512,512) cannot be broadcast.` Affects any variant with `attention_k_eq_v: true` (26B-a4b, 31B); E2B/E4B have it `false`. MLXVLM path is correct.
- **#259 (OPEN)** Tool calls never extracted. Two causes: `ToolCallFormat.infer(from:)` at `Tool/ToolCallFormat.swift:174` uses `if type == "gemma"` **exact equality** while Gemma 4's `model_type` is `"gemma4"` (every other family in the same function uses `hasPrefix`); and `GemmaFunctionParser.swift:8-9` still declares `startTag = "<start_function_call>"` / `endTag = "<end_function_call>"` whereas Gemma 4 emits `<|tool_call>call:NAME{...}<tool_call|>` (asymmetric `stc_token`/`etc_token`). Net: `stopReason == .stop`, `toolCalls == []`, tool-call text intact in the prose.
- **#292 / #338 / #282** — loader gaps: `embed_vision.embedding_projection.weight` not found; **E2B/E4B QAT checkpoints omit `k_proj`/`k_norm`/`v_proj`/`v_norm` for KV-shared layers** while the attention module creates them unconditionally. Fixed by PRs **#390** and **#384** (`num_kv_shared_layers`).
- **#279 (OPEN)** — register `gemma4_assistant` so Gemma 4 MTP drafters load. Published drafters: `mlx-community/gemma-4-E2B-it-assistant-bf16` (78 MB), `-E4B-` (78.8 MB), `-26B-A4B-` (~400 MB), `-31B-` (~500 MB). Config keys: `"model_type": "gemma4_assistant"`, `backbone_hidden_size`, `num_centroids: 2048`, `centroid_intermediate_top_k: 32`, `use_ordered_embeddings: true`, nested `text_config` (hidden_size 256, 4 layers). `LLMTypeRegistry.shared` registers `gemma4` and `gemma4_text` but not `gemma4_assistant`.
  **davidkoski's architectural direction** for MTP (drafters need the target's last-layer hidden states and share its KV cache):
  ```swift
  public struct LMOutput {
      public let logits: MLXArray
      public let state: State?
      public struct State {
          public let crossAttentionStates: MLXArray?
      }
  }
  ```
  > "For #157 I plan to make this `State` be a little more flexible ... Anyway, if that were done then the model _could_ output various internal bits. Callers would mostly ignore them but they could be available if needed."
  Related landed: **PR #415** registers the *unified* sibling `gemma4_unified_assistant` (12B drafter) with `MTPDrafterTypeRegistry`, adds the MTP state entry point to `Gemma4Unified`, and makes `draftBlock` target-agnostic via an internal `Gemma4BackboneProviding` protocol. **Failure mode before the fix is silent:** *"the `mtpEmitFlagKey` opt-in is discarded by the protocol-extension default and the target never emits drafter state — the MTP iterator **silently falls back to single-token passthrough** (no error, just no speedup)."* Measured ~**62% draft acceptance** on predictable text with the 12B target + assistant drafter.
  **PR #383** implements the E-series `use_ordered_embeddings=true` centroid embedder that was a `fatalError` stub in #308.
- **#474 (OPEN, 2026-07-27)** — `MLXVLM/Gemma4Assistant.swift:288: Precondition failed: sliding KV length 515 exceeds slidingWindow 512` when combining `gemma-4-e4b-it-4bit` + `gemma-4-E4B-it-assistant-bf16`. Note the user set `Memory.cacheLimit = 20 * 1024 * 1024` (20 MB) in the repro.

### 9.7 Other Swift items

- **#450 (OPEN)** — `mlx-community/Qwen3.5-4B-OptiQ-4bit` (sensitivity-aware mixed 4/8-bit, per-layer overrides in `config.json`, ~5.0 bpw) loads with **verifiably correct per-layer bits** (`q.bits == 8`, groupSize matches) but generates multilingual word-salad from the first token; **uniform 4bit/6bit fine through the identical Swift path; Python `mlx-lm` fine on the same directory.** Environment: mlx-swift-lm 3.31.4, mlx-swift 0.31.6, swift-transformers 1.3.3, M4, Xcode 26.2, macOS 26. Regression coverage added in **PR #395**.
- **#294 (OPEN)** — TurboQuant / rotating quantized KV cache fork offer. **davidkoski:** *"Interested, but see also: mlx-swift#405, mlx-swift-lm#287, #232, #160. I have a bit of a backlog I am working through. I don't know exactly how these turboquant PRs will land ... ultimately I will have to select one of these to merge and it may be the one that looks the best or the one that is ready."* Also flagged in-thread: *"`@Landon-Molt`'s findings on mlx#3404 suggest codebook lookup is **3-5x slower than scalar dequant on Metal GPU**, and their revised recommendation is Hadamard rotation + `mx.quantize` scalar format leveraging the generic quantized SDPA from mlx#3026."*
- **#260 (OPEN, 13 comments)** — "Parse output and stream as Open Responses for all models." Argues the industry moved from Chat Completions to **Open Responses** (openresponses.org) and that *"Neither MLX Swift LM nor MLX LM in Python can parse the full range of model output formats, and neither can stream Open Responses. SGLang and vLLM have implemented this in Python."* Offers `DePasqualeOrg/swift-lm-response-parser` (ports of SGLang/vLLM parsers + tests) as a dependency. Lists 6 open parsing PRs and 5 parsing issues as evidence of the problem's shape.
- **#357 (OPEN)** — "[BUG] tests fail due to TF32" (the Swift-side manifestation of §3.1).
- **#339 (CLOSED)** — "MLXHuggingFace: consider a macro-free path — its macros pull swift-syntax into consumer build graphs." (Note the `#huggingFaceTokenizerLoader()` macro appears in #450's repro.)
- **#217 (OPEN)** — "3.31.3 release's upgrade notes are 404'd."
- **#382 (CLOSED) / PR #389** — "Cancelling generation can still submit one more GPU evaluation (iOS/iPadOS crash)"; PR **#423** adds a cooperative cancellation check to the prompt prefill loop; PR **#413** cancels the generation task when the consumer goes away.
- **#428 (OPEN in mlx-swift-examples #345)** — building `MLXChatExample`: the visible failure was actually **network entitlements** plus `shouldUseOfflineMode` returning true on a hotspot (a `HubApi`/swift-transformers feature). davidkoski's advice: fall back to `llm-tool` (CLI) to isolate.

---

## 10. iOS / device-specific constraints

- **mlx#3665 (OPEN)** — "MLX doesn't publish iOS-compatible wheels." Filed by *"a member of the CPython core team, the author of PEP 730 (which added support for iOS), and the maintainer of Briefcase."* As of Python 3.14, Python supports iOS; mlx publishes macOS wheels only.
- **mlx#3915 (OPEN)** — "CMake cannot build Metal kernels for iOS." PR #3617 fixed the configure-level gate that forced `MLX_BUILD_METAL` off for `CMAKE_SYSTEM_NAME == iOS`, but *"the Metal kernel custom commands still explicitly use `xcrun -sdk macosx metal ... -mmacosx-version-min=...`"* and the final `mlx.metallib` is linked with the macOS SDK; they don't inherit `CMAKE_OSX_SYSROOT=iphoneos`/`iphonesimulator`. Affects `mlx-rs → mlx-sys → mlx-c → mlx`. `mlx-swift` sidesteps it by having Xcode build/bundle the shaders separately from the `Cmlx` target.
- **mlx#3821 (CLOSED)** — "Source builds silently drop the NAX kernels when `MACOSX_DEPLOYMENT_TARGET < 26.2` — no configure-time warning." Follow-up merged PR **#3824** "Warn at configure time when NAX kernels are disabled."
- **mlx-swift-examples#429 (CLOSED)** — A19 Pro NAX not used. **davidkoski:** *"This will require changes in MLX ... and then an update to mlx-swift to pick it up"* → later *"See mlx-swift 0.30.2 and higher -- this now supports NAX!"*
- iPad Pro M4 reports `applegpu_g16g` and iPadOS 26.5.2 in the #3885 sweep; all d=512 pipelines report `maxThreads=1024` there (the 832 cap is M1-generational).

---

## 11. Newly landed / in-flight features worth naming

### mlx core (merged)
| PR | What |
|---|---|
| **#3764** | `qmv_wide` — small-batch quantized matvec for **M ∈ [2, vector_limit)**; dequantizes each weight group once and reuses across the tile ("adapted from llama.cpp's `kernel_mul_mv_ext`"). Covers **affine, nvfp4, mxfp4, mxfp8**, all dtypes, batched weights. **fp modes on all GPU generations; affine gated to gen-15+.** Speedups vs `qmv` on Gemma-4-12B `[15360x3840]` bf16: M=4 → 1.4–2.0×; M=8 → 1.2–2.2×. |
| **#3888** | `gemv_wide` — fp16/bf16 `x @ w.T` for **M = 2..15**, covering `Matmul`, `AddMM`, `GatherMM`, **M3 generation and later**. Streams a block of weight rows once against up to five input vectors in registers. `in_proj_a/b [M,2048]x[2048,32]`: M=2 → 3.0× (M3 Ultra) / 6.0× (M5 Max). `lm_head [M,2048]x[2048,248320]`: 1.3–2.3×. |
| **#3854** | nvfp4 split-K correctness (see §4.3). |
| **#3875** | `MLX_SDPA_BLOCKS` rounded up to a multiple of 32 (see §2.6). |
| **#3843** | `#pragma clang loop unroll_count(4)` on the NAX attention Q@K.T loop — **+12% throughput at head_dim 128** on M5 Max (5.70→5.08 ms, 48.2→54.1 TF); no change at 64. Scheduling-only, accumulation order preserved. |
| **#3882** | Reuse Metal WAR (write-after-read) tracking hash tables. *"Qwen 35B hits this path **1,056 times per decoded token**. The input side alone caused **1,859 bucket-table growths per token**."* → **~1.9% throughput**, identical output, unchanged peak memory. |
| **#3828** | Fix captured random state in compile (thread-local random state singleton). Closes mlx-lm#1444, fixes mlx-lm#1439 ("temperature > 0 is silently deterministic on the second call onward"). |
| **#3872** | **Zero-copy CPU import:** `mx.array(host_buffer, copy=False)` via Metal `newBufferWithBytesNoCopy`. 256 MB float32 numpy array on M4 Max: **copy 4.2 ms → adopt 0.02 ms**. Default `copy=None` (unchanged). Raises (rather than silently copying) when Metal is unavailable, element size ≠ dtype size, or the buffer can't be adopted. **Metal-build-only.** |
| **#3728** | `mx.fast.metal_kernel(..., math_mode=...)` with `"safe"` (**new default**), `"relaxed"`, `"fast"`. *"Custom Metal kernels now default to `math_mode="safe"` to preserve IEEE-compliant behavior ... ensuring `exp(-inf) == 0` ... critical for masked softmax implementations used in causal and sliding-window attention."* Closes #3592, which also asked for `-fmetal-math-mode`, integer template params, and Metal 4 Tensor types. |
| **#3723** | `[CUDA] Make qmv support global scale`. |
| **#3869** | `[Metal] Avoid regex in custom kernel name generation`. |
| **#3804** | Fix fp quantized matvec for output dim < 8 (issue #3762: `fp_qmv_impl` used the raw scale byte instead of `dequantize_scale` → wrong mxfp4 matvec for `out_vec_size < 8`). |
| **#3806/#3809/#3775** | CI: macOS refactor, Windows CUDA builds (+ large runner). |
| **#3783** | Quote hostname in `mlx.launch` ssh commands. |
| **#3768** | `[WIP] [CUDA] fsdp` (merged 2026-07-21). |

### mlx core (open, notable)
`#3922` sorted gather_qmm NAX boundary fix; `#3918/#3919/#3920` the mlx-swift-lm perf batch; `#3894` TF32 docs; `#3899/#3900/#3901` **JACCL** (optional coordinator, ring refactor + threads for multiple rings, scatter-reduce) by angeloskath; `#3923` BitLinear (BitNet b1.58 QAT layer); `#3927` `mlx.special` (erf, erfc, i0, gammaln, digamma); `#3928` restore type stubs in frontend wheels (issue **#3916**: *"0.32.0 wheels ship `py.typed` but no `.pyi` stubs — breaks type checking of `mlx.core` downstream"*); `#3912` fp quantized matmul corruption when the quantized dim isn't a multiple of 32; `#3913` faster logsumexp for short rows.

### Distributed (a whole open cluster of instability)
`#3910` JACCL `MeshImpl::recv` spins forever on peer loss (silent hang, no timeout); `#3876` CUDA distributed all_sum barrier hangs in `cu::AtomicEvent::wait` on Blackwell; `#3862` distributed ring `SocketThread` dies silently on transient connection reset → all ranks wedge in `Event::wait`; `#3777` JACCL segfaults in `ibv_reg_mr` (null PD) when RDMA absent; `#3755` ring and jaccl both fail to connect (errno 60/65) on a 4-node M3 Ultra cluster; `#3830` Metal fence handoff deadlocks under `MLX_METAL_FAST_SYNCH=1` (orphaned `fence_wait` kernel locks the GPU until reboot) and hits the **~5 s GPU watchdog** when unset (`kIOGPUCommandBufferCallbackErrorTimeout` at ~7.3k tokens). PR `#3933` "Fix crashes in the ring and jaccl distributed backends" is open.

### mlx-lm (merged)
| PR | What |
|---|---|
| **#1072** | Batch generation refactoring. Arbitrary prompt segments for checkpointing; steppable prompt processing; **right padding for prefill, left padding for decode** so finished sequences stop early (*"Previously inserting a sequence of 100 tokens and 10,000 tokens would process ~20,000 tokens, now we will process ~12,000."*); introduces a `StateMachine`; enables **system prompt checkpointing in the server**. Bug fixes: Qwen 3.5 batch mode (conv state grabbed incorrectly; the GDN kernel left uninitialized memory in the output → NaNs in the next full attention) and Deepseek DSA batch mode (mask ignored — affects GLM5 and Deepseek v3.2). |
| **#1501** | **Text-based state machine.** *"The token based `SequenceStateMachine` has a design flaw that makes it impossible to identify the state change because substrings can be encoded in different ways. This replaces it with `TextStateMachine` so we switch state on the actual string and not the tokens. It also introduces a `StopSequenceMatcher`."* Fixes #1373, #1447, #1406, #1336, #1160. |
| **#1385** | **CVE-2026-5843 / GHSA-9m9w-53g9-47c4** — `config.json`'s `model_file` key caused `load_model` to import and run a Python file straight from the model directory, on a plain `load()`, with no way to turn it off. Now gated behind `trust_remote_code` (default **False**) threaded through `load()` and `sharded_load()`; `MLX_LM_TRUST_REMOTE_CODE=1` works for CLI tools. Reported against Docker Model Runner, which embeds mlx-lm. |
| **#1359** | `batch_generate(return_logprobs=..., return_token_ids=...)` (both default off) for RLOO/PPO importance weighting. |
| **#1345** | Add pipelining for Qwen 3.5. |
| **#1504** | Fix `IncompleteSnapshotError` in `hf_repo_to_path`. |
| **#1467** | Fix broadcast crash in quantized SDPA with GQA + batched padding mask (batch ≥ 2). |
| **#1465 / #1461 / #1458** | transformers ≥ 5.13 fallout: `AutoTokenizer.register("NewlineTokenizer", ...)` passing a string as `config_class` breaks imports of both `mlx-lm` and `mlx-vlm`. |
| **#1372 / #1575** | XTC sampling: `xtc_threshold` default 0.0 → **0.1** everywhere; threshold made per-row for batched logits. |

### mlx-lm (open, notable)
`#1588` expert offload (§8); `#1584` rotating quantized KV; `#1585` pad sorted gather rows to 64 (mlx#3856 workaround); `#1586` fused sequential-scan SSM kernel for S=2–8; `#1596` prompt-cache trimming for recurrent/hybrid/sliding-window via prefill-boundary state checkpoints; `#1598` livelock watchdog; `#1595` pin `MLX_ENABLE_TF32=0` in tests; `#1592` document spec-decode tie-breaking; `#1590` never lower `RLIMIT_NOFILE` on import (issue **#1589**: *"Importing mlx_lm lowers RLIMIT_NOFILE and irreversibly caps the hard limit"*); `#1579` fused Metal kernels for the SSD prefill path in `ssm_update`; `#1609` faster loglikelihood scoring in `mlx_lm.evaluate`; `#1580` keyed per-request sampling; `#1593` drop import-level sampler compilation.

**Model-support velocity (July 2026 alone):** Nanbeige/Nanbeige4.2 (looped transformer, three competing PRs #1597/#1599/#1603), Laguna / Laguna-S 2.1 / Poolside nvfp4 (#1601/#1602/#1334), Apertus 1.5, granitemoe_swa, Kimi K3 (draft, "pending 2026-07-27 weights"), Mellum 2, DeepSeek-OCR + Unlimited-OCR (swift #473), Olmo3, GLM4MOE/GLM4MOELite, Mamba2, Mixtral, DeepSeek-V2/V3.

---

## 12. Cross-cutting gotchas checklist (guide-ready)

1. **`mx.get_peak_memory()` excludes the buffer pool.** Use `get_active_memory() + get_cache_memory()`.
2. **`mx.clear_cache()` does not free live buffers**, only the recycle pool; and `phys_footprint` trails it by seconds.
3. **`resource_limit` (default fallback 499000) is a COUNT of live Metal buffers.** No byte knob affects it. Check with `mx.device_info()["resource_limit"]`. There is no setter.
4. **Unbounded `mx.compile` variant accumulation** can exhaust that count. Use `shapeless=True`; there is no public compile-cache clear.
5. **Functional (concatenate/slice-assign) caches leak one buffer per layer per step** unless you `mx.eval` the cache state each step.
6. **Monotonically growing allocation sizes never hit the buffer cache** (reuse window `[size, size+2·page_size)`). Preallocate + `slice_update`.
7. **SDPA fused coverage is dim-gated and the fallback is silent:** vector {64, 96, 128, 256} + (192,128); full {64, 80, 128}. Anything else materializes `[B, n_kv, n_rep, qL, kL]` scores. Common victims: Gemma 4 global layers (**d=512**), Gemma 4 sliding (**d=256** at prefill), Qwen3VL vision tower (**d=72**), any **d=96** model.
8. **Pad odd head dims up to a supported one** (72→80 in Swift; `gemma4EnsureFusedSDPA` / `ensure_fused_sdpa`) — exact, since padded dims contribute nothing and `scale` is explicit.
9. **`MLX_ENABLE_TF32=1` is the default.** CUDA always; Metal only on gen-17+ with macOS ≥ 26.2. Read once, first use — set it before any matmul. Shape-dependent (matvec stays fp32).
10. **`MLX_SDPA_BLOCKS` must be a multiple of 32** on mlx ≤ 0.32.0 or attention silently corrupts.
11. **Batch-vs-single bit equivalence is not achievable on M5/gen-17.** Don't assert `rtol=1e-5`.
12. **Speculative decoding at temp=0 is lossless in exact arithmetic only.** bf16 exact ties break differently between batched verify and sequential decode.
13. **Affine-quantized MoE on M5/NAX corrupts silently** when gathered rows `> 32768 && % 64 != 0` (and separately when `K % 64 != 0`, which also hits mxfp4). Cannot reproduce on M1–M4.
14. **NVFP4 tensor-scale (`global_scale`) is not implemented on Metal** and throws.
15. **`--kv-bits` costs decode speed and (today) *raises* prefill peak memory.** It is a capacity lever. Mitigate the peak with a smaller `prefill_step_size`.
16. **`quantized_kv_start` defaults to 0 in the library and 5000 in the CLI.** Always pass it.
17. **`RotatingKVCache.to_quantized()` raises**; `hasattr` guards don't help; `keep>0` will still raise after PR #1584.
18. **`RotatingKVCache` becomes untrimmable after the window wraps** (both Python and Swift), silently breaking speculative rollback and prompt-cache prefix reuse.
19. **MTP weights are stripped at load in mlx-lm** and (in some paths) still trigger a norm-weight shift. Expect *slower*, not faster.
20. **gpt-oss + quantized KV cache = silent client timeout** (attention sinks unsupported).
21. **`load(lazy=False)` (the default) materializes the whole stacked MoE expert table** at load time.
22. **MLX arrays are thread-affine** — build them on the thread that runs the model.
23. **A prefix slice of an `mx.array` is a view that pins the whole parent buffer.**
24. **Swift: `MLX.compile()` + `KVCacheSimple` is broken** (Swift `Int` offset baked as a constant).
25. **Swift: `maybeQuantizeKVCache` replaces array elements, not objects** — the caller's `[KVCache]` keeps the stale references.
26. **Swift + FoundationModels: nested `@Generable` in tool arguments** and **`.toolCalling` on VLM-loaded models** were both fatal before mlx-swift-lm PRs #434/#435.
27. **Xcode 27 / FoundationModels beta SDK churns**: `SamplingMode.Kind` case names, opaque streaming event values, and a `updateUsage(input:output:metadata:)` interface/dylib mismatch that SIGSEGVs under chained fixups.
28. **Fix propagation for Swift is four hops:** mlx → mlx-c → mlx-swift → mlx-swift-lm/examples.
29. **macOS `F_NOCACHE` does not evict resident pages** — a classic A/B benchmarking trap on Apple SSDs.
30. **On Apple Silicon, "size the cache as big as fits" is wrong** — the OS page cache reserve is tens of GB and over-sizing collapses throughput.

---

## Source inventory (everything actually read this session)

### `ml-explore/mlx` issues
- #3849 (body + 6 comments) — Metal resource limit
- #3852 (body) — 2-bit qmm slope
- #3856 (body summary + 9 comments) — affine gather_qmm corruption
- #3858, #3859, #3860 (body + 5 comments) — TF32
- #3861, #3862, #3865, #3866, #3874, #3876, #3877 (titles)
- #3879, #3880, #3885 (body + 10 comments) — d=512 SDPA
- #3886 (body) — BufferCache reuse window
- #3887, #3896 (body + 2 comments) — peak memory undercount
- #3897 (body + comments) — batched attention M5
- #3910, #3911 (body), #3915 (body), #3916, #3925, #3926, #3932 (titles)
- #3658 (body + 4 comments) — head_dim 256 prefill
- #3665 (body) — iOS wheels
- #3702 (body + 3 comments) — A19 corruption
- #3826 (body), #3837 (body + 4 comments)
- Full triage list of 80 most-recent issues (open + closed)

### `ml-explore/mlx` PRs
- Merged: #3888, #3764, #3854, #3875, #3828, #3882, #3872, #3728, #3723, #3843 (full bodies); #3869, #3824, #3804, #3806, #3809, #3775, #3783, #3768, #3816 (titles)
- Open: #3922, #3918/#3919/#3920, #3894, #3899/#3900/#3901, #3923, #3927, #3928, #3912, #3913, #3933 (titles)

### `ml-explore/mlx-lm` issues
- #1438 (body + all 32 comments incl. the consolidated v1.5.1 findings summary)
- #1493 (body + comments), #1494 (body), #1495 (body)
- #1470 (body + 7 comments), #1475 (body + 1 comment)
- #1280 (body), #1292 (body + 4 comments), #1332 (body), #1390 (body)
- #1425 (body), #1435 (body), #1446 (body + 2 comments), #1480 (body)
- #1497 (body), #1500 (body), #1566 (body), #1573 (body + 6 comments)
- #1583 (body), #1587 (body + 11 comments), #1610 (body)
- Full triage list of 80 most-recent issues

### `ml-explore/mlx-lm` PRs
- Merged: #1501, #1072, #1345, #1385, #1359 (full bodies); #1504, #1467, #1465, #1431, #1372, #1575, #1327, #1240, #1177, #1109, #1114, #1106, #1090, #1078 (titles)
- Open: #1588 (full body); #1584, #1585, #1586, #1592, #1595, #1596, #1598, #1607, #1611, #1618, #1619, #1623 + ~25 more (titles)

### `ml-explore/mlx-swift-lm` issues
- #221 (body + 18 comments), #466 (body + 1), #441 (body + 2)
- #433 (body), #432 (body), #424 (body + 1), #420 (body), #443 (body)
- #450 (body), #406 (body), #474 (body), #312 (body + comments), #294 (body + 3)
- #279 (body + 5), #259 (body), #231 (body), #260 (body)
- Full triage list of 60 most-recent issues

### `ml-explore/mlx-swift-lm` PRs
- Merged: #456, #434, #435, #455, #439, #438, #415, #399, #383, #381 (full bodies); #464, #458, #457, #449, #445, #442, #440, #437, #431, #423, #422, #419, #418, #413, #411, #409, #408, #405, #404, #403, #398, #395, #391, #390, #389, #388, #387, #386, #384, #380, #379, #378, #377, #376 (titles)
- Open: #475, #473, #472, #471, #470, #469, #468, #467, #465, #463, #462, #460, #459, #454, #453, #452, #451, #448, #436, #426, #414, #412, #401, #400, #392, #375, #370, #358, #352, #351, #348, #335, #329, #322, #301, #288, #263, #194, #146, #106 (titles)

### `ml-explore/mlx-swift-examples`
- #462 (body + 9 comments), #429 (body + 6 comments), #345 (body + 6 comments)
- Full triage list of 60 issues

### Release metadata
- `gh release list` for all four repos

### External URLs referenced *inside* the threads (not fetched this session)
- <https://tzakharko.github.io/apple-neural-accelerators-benchmark/> — A19/M5 neural accelerator microbenchmark
- <https://www.openresponses.org> — Open Responses spec
- `https://ai.google.dev/gemma/docs/mtp/overview` — Gemma 4 MTP overview
- `https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/` — Gemma 4 MTP blog (drafters released 2026-05-05)
- `huggingface.co/collections/mlx-community/gemma-4-assistant-mtp`
- Gists: `doramirdor/0aeb975a99eb5a4644a3d105b57e3909` (coalesce pipeline), `mabaeyens/de8314ba6d90e50ce46d5dd328682e4a` (routing trace)
- Repos: `PhilipJohnBasile/scrutineer`, `PhilipJohnBasile/trailbrake`, `PhilipJohnBasile/iliria`, `rajanshxrma/mlx-kvcache-1587`, `doramirdor/mbolt`, `mu-hashni/mlx-moe`, `SharpAI/SwiftLM`, `DePasqualeOrg/swift-lm-response-parser`, `joelnishanth/mlx-swift-turboquant`, `angelsbrood/Gemma4SwiftRepro`

---

## Open questions / unverified

1. **Line numbers drift.** All source line references (`allocator.cpp:132/166-190`, `buffer_cache.h:30-38`, `scaled_dot_product_attention.cpp:621-633`, `quantized_nax.h:1532-1535`, `cache.py:37/552/1578/1630/1674`, `generate.py:294/589-591/622-634/1332/1369`, `server.py:1037/1048`, `ToolCallFormat.swift:174`, `GemmaFunctionParser.swift:8-9`) come from issue bodies at specific commits. **Verify against the actual checkout before quoting in a guide.**
2. **Did mlx#3922 merge?** It was open with a proposed fix at research time. Same for #3918/#3919/#3920, mlx-lm#1584/#1585/#1588/#1598, and mlx-swift-lm #467–#471. ✅ **RESOLVED for #3894** — merged 2026-08-04, closing #3860 with it (§3.1).
3. **`mlx_lm` on PyPI is 0.31.3 (April) while `main` has months of fixes.** I did not determine whether 0.31.4+ shipped. Guide readers on PyPI will hit several of the bugs above that are fixed on main.
4. **Exact `mx.device_info()` key set** — I verified only `resource_limit` and `device_name` appear in these threads.
5. **`MLX_METAL_GPU_ARCH`** is used in #3897/#3860 as a same-silicon kernel-family override (`applegpu_g16s`). Its documented status, valid values, and whether it is supported vs. debug-only are **UNVERIFIED**.
6. **`MLX_FAST_LOG_FALLBACK`** and **`mx.fast.sdpa_is_fused(...)`** were *requested* in #3885, not implemented. Do not present them as APIs.
7. **`mx.set_resource_limit`** does not exist as of this research. A contributor offered a PR; unknown whether it landed.
8. **`get_qmv_batch_limit` / `use_qmv_wide`** are internal dispatch functions cited from a benchmarking issue; not public API. Values "10–12 at these dims" are shape-specific.
9. **A19 root cause is unresolved.** #3702 was closed but the last substantive content was the reporter's shape sweep; I did not find a stated fix or a maintainer conclusion. Whether MLX now excludes A19 from the NAX matmul path is **UNVERIFIED**.
10. **mlx-swift-examples#462's fix** landed in mlx but the tag-chain propagation status (which mlx-swift release carries it) was unresolved in the thread.
11. **Gemma 4 configuration numbers conflict across reports** — 30 layers/sliding_window 1024 (one MLX repack), 42 layers/35 sliding (another), 26B-A4B vs 31B vs E2B/E4B vs 12B "unified". Do not state a single canonical layout; cite the specific checkpoint.
12. **Fork benchmark claims in swift-lm#221** (e.g. Gemma 4 26B MoE 25 → 101 tok/s, +304%) are fork-author-reported and **not independently reproduced upstream**.
13. **`ParoQuant` / `PARO`** appears in swift-lm #164/#471/#466 as a quantization scheme; I did not read its definition.
14. **`JACCL`** is MLX's distributed backend alongside `ring`; its docs/config surface (`distributed_config`, `rdma_ctl`, `mlx.launch`) was not read.
15. Whether **mlx-lm has a maintainer response** to #1475 after 2026-07-27 is unknown; the posture statement above is a snapshot.
16. **`MLX_METAL_FAST_SYNCH`** appears only in mlx#3830; semantics unverified.
17. The **`enable_offload` API signature** in mlx-lm PR #1588 is from the PR body; the merged form (if merged) may differ.
