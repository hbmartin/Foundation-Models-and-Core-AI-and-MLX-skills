# GitHub Issues & PRs mined: `apple/coreai-torch`, `apple/coreai-optimization`, `apple/coreai-models`

**Research date:** 2026-07-27. All content below was read live via `gh` CLI in this session
(issue/PR bodies + comment threads + release notes). Nothing here is from model memory.
Where a claim is inferred rather than quoted, it is marked **(INFERRED)** or **UNVERIFIED**.

Repo one-liners (from `gh repo view`, verbatim):

- `apple/coreai-torch` — *"Bridges PyTorch and Core AI. Convert existing models to Core AI IR, or author new
  ones from PyTorch via composite ops, custom op lowerings, and inline Metal GPU kernels."*
- `apple/coreai-optimization` — *"A library for PyTorch model compression and optimizations for deployment via
  Core AI on Apple silicon."* (PyPI name: `coreai-opt`, import name `coreai_opt`, source under `src/coreai_opt/`)
- `apple/coreai-models` — *"Model export recipes, Python primitives, and Swift runtime utilities for on-device AI"*

---

## 0. Version / platform landscape established by these threads

| Fact | Source |
|---|---|
| `coreai-torch` latest release = **v0.4.1**, published 2026-07-06 | `gh release list -R apple/coreai-torch` |
| `coreai-opt` latest release = **v0.2.1** (2026-07-02); v0.2.0 pre-release 2026-06-08 | `gh release list -R apple/coreai-optimization` |
| `coreai-models` latest release = **0.2.0** pre-release (2026-07-08) | `gh release list -R apple/coreai-models` |
| `coreai-core` versions in the wild: `1.0.0b1` → `1.0.0b2` (b2 bumped by coreai-torch v0.4.1) | torch v0.4.1 release notes |
| `coreai-models` requires **macOS and iOS 27.0+**, **Xcode 27.0+** | coreai-models README |
| `coreai-core` wheels: **macOS cp311 / cp312 only** at first; **cp313 added in `1.0.0b2`** | coreai-torch #4, #20 |
| **No linux/arm64 `coreai-core` wheels** — Linux containers must use `--platform linux/amd64` | coreai-opt PR #19 comment (@guru-desh) |
| PyTorch versions actively tested by coreai-opt CI: **2.8, 2.9, 2.10, 2.11** | coreai-opt PR #32 |
| `coreai-torch` removed its PyTorch max-version pin; now *warns* if torch is newer than verified | coreai-torch PR #39 |
| Real user stacks seen in bug reports: torch 2.9.0 / 2.11.0, Python 3.11.15 / 3.12.13, macOS 27.0 builds `26A5353q` (β1), `26A5368g` (β2), `26A5378j`/`26A5378n` (β3), `26A5388g`; iOS `24A5380h`; Xcode `27A5194q`, `27A5209h`, `27A5218g` | many |
| `coreai-build` (the AOT compiler) versions seen: `3600.67.5.8.1` (MetalToolchain-v27.1.5194), `3600.73.1`, `3600.75.3` | coreai-models #55, #27; coreai-torch #44 |

### 🚨 THE BIGGEST VERSION GATE (coreai-torch v0.4.1 release note, verbatim)

> "**.aimodel artifacts converted with coreai-torch v0.4.0 will fail to load/specialize on-device starting
> with OS 27 second beta onwards. Reconvert your model using coreai-torch v0.4.1 or later to produce a
> compatible artifact.**"

Maintainer @gokulkrishna98 on coreai-torch#37:
> "Hi @zli96 , from macOS beta 2 the assets generated via coreai-torch 0.4.0 will fail to compile.
> Please use coreai-torch 0.4.1 for conversion."

`coreai-torch` **v0.4.1 changelog** (verbatim, from `gh release view v0.4.1`):
- Added support for `masked_scatter` (writing values into a tensor at masked positions)
- `repeat` op lowering now supports dynamic/symbolic repeat counts (not just fixed integers)
- Mixed SymInt/int shape lowering across `pow`, `round`, `upsample`, `cat`, and `repeat`
- Support `concat` (`cat`) lowering when a non-concat axis stays dynamic after shape promotion
- For `arange` op lowering, preserve static output shape for float dtypes with integer bounds
- Skip externalization for submodules never invoked in the exported graph
- Reworked `debug_info` and `inspector` modules for improved debug location tracking and intermediate value inspection
- Bumped `coreai-core` dependency to `1.0.0b2`

`coreai-core v1.0.0b2` changelog (bundled into the same release page, verbatim):
- NDArray Python bindings now support **strided views**.
- `AIProgram.save_asset` now **records the producer in asset metadata**, **overwrites an existing serialized
  model instead of failing**, and **validates that the destination has a `.aimodel` extension**.
- Added string representations for `SpecializationOptions`, `ComputeUnitKind`, and `InferenceFunction`.
- Fixed an import cycle in the Python package.
- `NDArray.View`/`MutableView.subscript(scalarAt:)` now a public API.
- Added **image type support** to `InferenceValue.Kind`.
- Documentation polish for `InferenceFunction.encode`.
- Removed the unused `ml_asset` module and the **legacy Torch importer**.

---

## 1. coreai-torch — issue-by-issue

### coreai-torch#51 — `[Bug][ANE] FP16 numerical discrepancy in MobileNetV3 (2D MatMul + Hardswish)` — OPEN, 0 comments
Author `zli96`, 2026-07-23. Env: macOS 27 beta 3, `coreai-torch` v0.4.1.

**Core problem.** FP16 models on the ANE diverge badly when a **2D Linear/MatMul feeds directly into
`Hardswish`**.

| Test Case (FP16 NPU vs GPU) | Max Abs Diff | Rel L2 Diff |
|---|---|---|
| MobileNet V2 (Linear + ReLU/Identity classifier) | `0.002686` | `0.001025` |
| MobileNet V3 Small (Linear + Hardswish classifier) | `0.199219` | `0.039235` |

Reported summary line says "Max Abs Diff: ~0.199, Rel L2 Diff: ~3.92%".

**Isolation / workaround (author's own):**
> "Transforming the 2D matrix into a 4D matrix (1 x 1 x m x n) avoids the issue on the NPU."

**Repro pattern worth stealing for a guide — the exact ANE-vs-GPU A/B harness:**
```python
import asyncio, numpy as np, pathlib, torch, torchvision
from coreai_torch import TorchConverter, get_decomp_table
import coreai.runtime as r

spec_gpu = r.SpecializationOptions.from_preferred_compute_unit_kind(r.ComputeUnitKind.gpu())
spec_npu = r.SpecializationOptions.from_preferred_compute_unit_kind(r.ComputeUnitKind.neural_engine())

in_np = torch.randn(1, 3, 224, 224).numpy().astype(np.float16)
nd_in = r.NDArray(in_np)

model_v3 = torchvision.models.mobilenet_v3_small(
    weights=torchvision.models.MobileNet_V3_Small_Weights.DEFAULT).half().eval()
ep_v3 = torch.export.export(model_v3, (torch.randn(1, 3, 224, 224).half(),))
ep_v3 = ep_v3.run_decompositions(get_decomp_table())
prog_v3 = TorchConverter().add_exported_program(
    ep_v3, input_names=['image'], output_names=['logits']).to_coreai()
prog_v3.optimize()
prog_v3.save_asset(path_v3)

m_v3_gpu = await r.AIModel.load(path_v3, specialization_options=spec_gpu)
m_v3_npu = await r.AIModel.load(path_v3, specialization_options=spec_npu)
v3_gpu = (await m_v3_gpu.load_function("main")({"image": nd_in}))["logits"].numpy().astype(np.float32)
v3_npu = (await m_v3_npu.load_function("main")({"image": nd_in}))["logits"].numpy().astype(np.float32)
```
API surface confirmed here: `r.SpecializationOptions.from_preferred_compute_unit_kind(...)`,
`r.ComputeUnitKind.gpu()` / `.neural_engine()`, `r.NDArray(np_array)`,
`await r.AIModel.load(path, specialization_options=spec)`,
`m.load_function("main")` returning an awaitable callable taking a `dict[str, NDArray]`.

**Guide takeaway:** always A/B ANE vs GPU vs CPU on the *same* `.aimodel`. Reshaping a 2D matmul to
`[1,1,m,n]` before an ANE-hostile activation is a real, cheap mitigation.

---

### coreai-torch#49 — `AIProgram.optimize() removes broadcasting-significant axis moves and silently miscompiles N×N distance expressions` — OPEN, 0 comments
Author `dkomoroske`, 2026-07-23. Env: macOS 27.0 `26A5378j` and `26A5388g`, `coreai-torch 0.4.1`,
`coreai-core 1.0.0b2`, `torch 2.11.0`, Python 3.12.13. Also filed as Feedback Assistant **FB23695952**.

**Core problem.** `AIProgram.optimize()` deletes an `expand_dims`/`transpose` that is *semantically
load-bearing for broadcasting*, in the classic expanded squared-distance form
`D[i,j] = ||x_i||² − 2·x_i·y_j + ||y_j||²`.

Failing minimal form (no matmul needed — `z` is a graph input):
```python
s1 = torch.sum(x ** 2, dim=-1).unsqueeze(-1)  # (1,N,1)
s2 = torch.sum(y ** 2, dim=-1).unsqueeze(-2)  # (1,1,N)
out = (s1 - 2 * z + s2).clamp(min=0.0)
```

**IR before optimize (verbatim from the issue):**
```text
%y_norm = coreai.reduce_sum ... -> tensor<1x32x1xf32>
%y_norm_moved = coreai.expand_dims ... -> tensor<1x1x32xf32>
%tmp = ...broadcasting_sub ... : (tensor<1x32x1xf32>, tensor<1x32x32xf32>) -> tensor<1x32x32xf32>
%out = ...broadcasting_add %tmp, %y_norm_moved : (tensor<1x32x32xf32>, tensor<1x1x32xf32>) -> tensor<1x32x32xf32>
```
**IR after optimize (the axis move is GONE):**
```text
%x_norm = coreai.reduce_sum ... %arg0 ... -> tensor<1x32x1xf32>
%y_norm = coreai.reduce_sum ... %arg1 ... -> tensor<1x32x1xf32>
%tmp = ...broadcasting_sub ... : (tensor<1x32x1xf32>, tensor<1x32x32xf32>) -> tensor<1x32x32xf32>
%out = ...broadcasting_add %tmp, %y_norm : (tensor<1x32x32xf32>, tensor<1x32x1xf32>) -> tensor<1x32x32xf32>
```

**Measured harness output (verbatim):**
```text
Chain           optimize=False: max|d| = 1.907e-06  OK
Chain           optimize=True : max|d| = 1.022e+01  MISCOMPILED
ChainKeepdim    optimize=False: max|d| = 1.907e-06  OK
ChainKeepdim    optimize=True : max|d| = 1.022e+01  MISCOMPILED
ChainReordered  optimize=False: max|d| = 3.815e-06  OK
ChainReordered  optimize=True : max|d| = 3.815e-06  OK
```

**Controls table (verbatim rows worth quoting):**
- `SpecializationOptions.cpu_only()` → *same* miscompile (so it is a compiler/optimizer bug, not a delegate bug)
- Real `x @ y.transpose(-1,-2)` with distinct equal-length inputs → miscompiled
- `s1 + s2` alone → correct
- **Unequal input lengths (17×23) → correct** (needs shape compatibility for the wrong operand to broadcast)
- Reordered `(s1 + s2) - 2*z` → correct

**Impact quote:**
> "In a larger GeoTransformer conversion, this appeared as approximately **17 dB PSNR** versus eager
> PyTorch and scrambled nearest-neighbor relationships. **Disabling `optimize()` restored approximately
> 78–85 dB parity.**"

**Two verified workarounds:**
1. Don't call `AIProgram.optimize()` — "Conversion, `save_asset`, specialization, loading, and inference work
   correctly without it."
2. Reorder to `(||x_i||² + ||y_j||²) − 2·x_i·y_j`.

**Guide takeaway:** `optimize()` is *not* semantics-preserving in all cases as of 0.4.1/1.0.0b2. Any pipeline
guide should recommend an "optimize=True vs optimize=False numerics gate" as a standard step.
Square/equal-length shapes hide the bug because the output shape still validates.

---

### coreai-torch#21 — `softplus, mish, logsumexp, logcumsumexp overflow in fp16 on ANE — missing stable decompositions` — OPEN
Author `Ashutosh0x`, 2026-06-21. Env: macOS 26 / Apple Silicon, PyTorch 2.7+.

**Overflow table (verbatim):**
| Operation | Naïve Decomposition | Failure Threshold | Failure Mode |
|---|---|---|---|
| `softplus` | `log(1 + exp(x))` | `x ≈ 10.4` | Output → 0 |
| `mish` | `x * tanh(log(1 + exp(x)))` | `x ≈ 10.4` | Output → 0 |
| `logsumexp` | `log(sum(exp(x_i)))` | `x ≈ 7.63` | Output → 0 |
| `logcumsumexp` | `log(cumsum(exp(x_i)))` | `x ≈ 11.09` | Output → ∞/NaN |

**Root cause naming actual internals (very quotable):**
> "In `_decomp.py`, the decomposition table preserves only **6 ops** (`hardsigmoid`, `hardswish`,
> `instance_norm`, `pixel_shuffle`, `scaled_dot_product_attention`, `silu`). When `softplus` is not in this
> list, PyTorch decomposes it to `log(1 + exp(x))`, where `exp(x)` overflows fp16 (max 65,504) for
> `x > ~11.09`. **On the ANE specifically, the overflow occurs even earlier at `x ≈ 10.4` due to an internal
> 2^15-bounded representation.**"

Also: `log_softmax` is *already* handled by a stable max-shift path named **`replace_log_softmax` in
`_aten_to_core.py`** (issue #5 pins it to line 2541 as of June 2026).

**Names to remember:** `coreai_torch/_decomp.py`, the `_COMPOSITE_OPS` preserve list,
`coreai_torch/_aten_to_core.py`, `replace_log_softmax`, `get_decomp_table()`.

Prior art cited: coremltools PRs #2725 (softplus, mish), #2726 (logsumexp), #2727 (log_softmax,
logcumsumexp), coremltools issue #2687. Also cited: "the Orion paper (arXiv:2603.06728)" (issue #5).

---

### coreai-torch#5 (proposal) + PR#22 (implementation) — stable softplus/mish/logsumexp — both OPEN

Proposed decompositions (verbatim table from PR #22):
| Operation | Naïve Form | Failure | Stable Form |
|---|---|---|---|
| softplus | `log(1 + exp(x))` | Output → 0 at x ≈ 10.4 | `max(x,0) + log(1+exp(-|x|))` |
| mish | `x * tanh(log(1+exp(x)))` | Output → 0 at x ≈ 10.4 | `x * tanh(softplus_stable(x))` |
| logsumexp | `log(sum(exp(x)))` | Output → 0 at x ≈ 7.63 | `max(x) + log(sum(exp(x-max(x))))` |

PR #22 touches `coreai_torch/_aten_to_core.py`, `coreai_torch/_decomp.py`,
`tests/ops/test_fp16_stable_ops.py` (+244/−0). New symbols proposed:
`_stable_softplus(x)`, `replace_softplus` (with **beta scaling and PyTorch `threshold` support**),
`replace_mish`, `replace_logsumexp` (with `keepdim` support), plus adding `softplus`, `mish`, `logsumexp`
to `_COMPOSITE_OPS`.

**Maintainer bar for merging (quotable, @DawerG, CONTRIBUTOR):**
> "This is great - thank you for your interest in contributing! Would it be possible to add tests that fail
> numerically with current decomposition but would then pass with proposed ones?"

And in PR #22:
> "Thanks for the PR. Please also consider adding test that would fail otherwise but pass with this change."

Test helper name confirmed by the contributor's reply: **`validate_numerical_output`** — "Tests use
`validate_numerical_output` following the repo's existing pattern (async, parametrized over dynamic shapes)."

Numeric proof snippet the contributor added (verbatim):
```python
x = np.float16(15.0)
naive = np.float16(np.log(np.float16(1.0) + np.exp(x)))  # inf (WRONG)
stable = np.float16(np.maximum(x, 0) + np.log(1 + np.exp(-np.abs(x))))  # 15.0 (CORRECT)
```

**Status as of 2026-07-27: NOT MERGED.** So on shipped `coreai-torch 0.4.1`, softplus/mish/logsumexp/
logcumsumexp are still fp16-unsafe on ANE. Workaround is model-side substitution (see coreai-opt#7).

---

### coreai-torch#11 — `Runtime clobbers an unrelated live tensor when an int64-comparison bool mask chain executes` — OPEN
Author `john-rocky`, 2026-06-12. `coreai-torch 0.4.0`, `coreai-core 1.0.0b1` (cp312), `torch 2.11.0`,
macOS 27.0 `26A5353q`, M4 Max.

**Core problem.** An `int64 comparison → bool → float` mask chain (`((ix0 >= 0) & (ix0 < W)).to(dtype)`)
inside a gather-based bilinear sampler **corrupts an unrelated, still-live intermediate tensor elsewhere in
the graph** — including a declared graph *output*.

Author's characterization:
> "The victim tensor is provably computed correctly first (another consumer that runs *before* the sampler
> sees exact values), then reads back as garbage/NaN afterwards … Looks like a buffer-liveness/aliasing bug
> in buffer planning. Deterministic; reproduces with `cpu_only()` (and on GPU); `prog.optimize()` not
> required; **inserting `clone()`/`contiguous()` barriers does not protect the victim.**"

Measured output (verbatim):
```
  t    cos=nan      max|d|=nan       <- LayerNorm output, ALSO a graph output, clobbered
  cq   cos=1.000000 max|d|=4.8e-07   <- cq = t + qpos consumed t BEFORE the sampler ran: t was computed right
  t2   cos=1.000000 max|d|=4.2e-07
  out  cos=nan      max|d|=nan       <- residual re-read of t after the sampler
```
Float-mask variant: all four `cos=1.000000`.

**Nastier in the wild:**
> "In larger graphs (RF-DETR's full decoder) the same trigger corrupts the tensor to plausible-looking
> garbage rather than NaN, which makes it nastier to catch — **output cosine ~0.65 with no error raised**."

**Workaround (exact, verbatim):**
> "Compute in-bounds masks in float arithmetic only — for integer-valued floats,
> `1 - (x - x.clamp(lo, hi)).abs().clamp(max=1)` is an exact 0/1 mask — and cast to int only at the gather index."

---

### coreai-torch#10 — `GPU delegate executes aten.floor/trunc/ceil as identity; round uses away-from-zero ties; div(x,1,floor) folds to identity` — OPEN
Same author/env as #11.

**Measured table (GPU unit), verbatim:**
| op | got | expected |
|---|---|---|
| floor | `[0.3, 1.7, -0.4, -1.6, 2, -2, 0.5, -0.5]` (identity) | `[0, 1, -1, -2, 2, -2, 0, -1]` |
| trunc | identity | `[0, 1, -0, -1, 2, -2, 0, -0]` |
| ceil | identity | `[1, 2, -0, -1, 2, -2, 1, -0]` |
| round | `[0, 2, 0, -2, 2, -2, 1, -1]` (ties away) | `[0, 2, -0, -2, 2, -2, 0, -0]` (ties to even) |
| div(x, 1, floor) | identity (folded at conversion) | floor |
| **div(2x, 2, floor)** | **correct** | floor |

**CPU is correct for all four.** So the same `.aimodel` gives different math on CPU vs GPU.

**Impact quote:**
> "Hit while porting RF-DETR — the deformable-attention sampling floor turned the whole decoder into noise
> on GPU while CPU was bit-clean."

**Workaround:** `torch.div(x * 2.0, 2.0, rounding_mode="floor")` — divisor ≠ 1 lowers correctly, and ×2/÷2 is
exact in FP.

The `SpecializationOptions` selection API is shown here too:
```python
opts = rt.SpecializationOptions.cpu_only() if unit == "cpu" else \
    rt.SpecializationOptions.from_preferred_compute_unit_kind(rt.ComputeUnitKind.gpu())
m = await rt.AIModel.load(out, opts)
res = await m.load_function("main")({"x": rt.NDArray(x.numpy())})
```
Also confirms `prog.save_asset(out, rt.AIModelAssetMetadata())` — a second positional metadata arg.

---

### coreai-torch#9 — `Converter folds float→int→float cast round-trips, dropping truncation semantics (CPU too)` — OPEN
Same author/env.

```python
class M(torch.nn.Module):
    def forward(self, x):
        return (x + 64.0).long().float() - 64.0   # floor(x) for x > -64
# got:      [ 0.3  1.7 -0.4 -1.6]   (identity)
# expected: [ 0.   1.  -1.  -2. ]   (torch eager)
```
> "One-directional casts consumed by integer-typed ops (e.g. `gather` indices) behave correctly — only the
> round-trip is folded."

Combined with #10, both natural in-graph floor workarounds are removed on GPU. Issue #49 explicitly
cross-references #9 as "also … a silent semantics-changing simplification reached through `prog.optimize()`".

---

### coreai-torch#6 — `ANECompiler crash (ANECPlistInterface::addOpToNetwork EXC_BAD_ACCESS) at AIModel.load when slice_update begin/end indices are runtime values` — OPEN
Author `scndls`, 2026-06-11. `coreai-torch 0.4.0`, `coreai-models @ b1cb71b`, torch 2.9.0, Py 3.11.15,
macOS 27.0 `26A5353q`, M1 Max 32 GB.

Crash frame (verbatim):
```
thread #13, queue = 'MPSGraphExecutable_queue', stop reason = EXC_BAD_ACCESS (code=1, address=0x12a)
  frame #0: ANECompiler`mlir::anecir::ANECPlistInterface::addOpToNetwork(
      mlir::Operation*, mlir::anecir::ANECIRNetwork*, mlir::anecir::ANECIRWeightSerializer&) + 31400
```

**Decision table (verbatim):**
| `begin`/`end` of the state slice update | Result |
|---|---|
| compile-time constants | **runs** (correct outputs) |
| computed from an input tensor's values (e.g. `position_ids[0, :1]`) | **EXC_BAD_ACCESS** in ANECompiler at load |

Why it matters (verbatim):
> "This is the third member of a bug family that currently blocks the natural export paths for hybrid
> DeltaNet models (Qwen3.5/3.6, Qwen3-Next): dynamic context dims trip #1 (SDPA externalize re-export) and
> #2 (MPSGraph `FloatType::getWidth()` null-deref), so the model must be exported **fully static**. But a
> static stateful decode function then needs its KV write position as a **runtime value** — which this crash
> forbids."

Workaround used: **sliding-window KV cache** — every call shifts the cached window left by the static query
length and appends the new chunk at the end so all slice indices stay constant; a host-built attention mask
encodes validity/causality. Costs a full cache rewrite per step. `MODE=roll` in the repro matches eager
across stepped calls with rel err ≤ 5e-4.

API names confirmed by the repro: `coreai_models.primitives._ops.mutable_slice_update(x=, update=, begin=, end=)`
lowering to `coreai.slice_update`; `coreai_models.export.macos.export_to_coreai(model, trace, input_names=,
output_names=, state_names=, dynamic_shapes=)`; `coreai_models.export.macos._EXTERNALIZE_SPECS` (a list of
specs with a `.composite_op_name` attribute — SDPA's is `"scaled_dot_product_attention"`);
`coreai_models.primitives.macos.{rope.initialize_rope, sdpa.SDPA, cache.KVCache, rms_norm.RMSNorm,
rms_norm.RMSNormGated, mlp.MLP}`; `coreai_models.primitives.macos.cache.KVCache.seq_len_dim()`.

---

### coreai-torch#1 — `externalize: SDPA submodule re-export drops the upper bound on the key-length dim with a static query + dynamic KV context` — OPEN
Author `scndls`, 2026-06-10.

Error (verbatim):
```
RuntimeError: Internal error: failed to export submodule 'sdpa_061e31ac': Constraints violated (d_20)!
  - Not all values of d_20 = L['key'].size()[2] in the specified range satisfy the generated guard
    12 <= L['key'].size()[2] and L['key'].size()[2] <= IntInfinity()
Suggested fixes:
  d_20 = Dim('d_20', min=12)
This is a coreai-torch bug. Please report it.
```

Why the shipped models don't hit it (verbatim):
> "The shipped models don't hit this because they keep the **query** dynamic as well, so query and key share
> a single bounded symbol. The bug only surfaces when `query_len` is static (a fixed prefill chunk / single
> decode step) while the context is dynamic — which is what you need for hybrid linear-attention models
> (e.g. Qwen3.5 / Qwen3-Next Gated DeltaNet), where the query must be a static chunk so the recurrence's
> `scf.while` lowers."

Internals named: **`_dim_for_sym` in `_utils.py`** reads `var_to_range` for the reconstructed `Dim`.
`torch._check(key.size(-2) <= cap)` in the parent forward does **not** propagate into the submodule re-export.
Workaround: drop `SDPA` from the externalize list so it decomposes to primitive ops.

Open PR **coreai-torch#7** `[fix(externalize)] Skip fully-specialised dims in submodule re-export` targets
this (+347/−241, still "TODO" description, unmerged).

---

### coreai-torch#2 — `Runtime MPSGraph null-deref (mlir::FloatType::getWidth) executing 2+ GatedDeltaUpdate layers + an attention layer with dynamic KV context` — OPEN
Author `scndls`. Crash:
```
thread #23, stop reason = EXC_BAD_ACCESS (code=1, address=0x0)
  frame #0: MetalPerformanceShadersGraph`mlir::FloatType::getWidth() + 16
```

**Layer-count decision table (verbatim):**
| Model | Result |
|---|---|
| 1 GatedDeltaUpdate layer + 1 attention layer (dynamic context) | **runs** (exit 0) |
| **2** GatedDeltaUpdate layers + 1 attention layer (dynamic context) | **EXC_BAD_ACCESS** at execute |
| N stacked GatedDeltaUpdate layers, **no attention**, fully static export | runs (verified to N=3) |

> "It is the **combination**: 2+ DeltaNet `scf.while` scans plus a dynamic KV-context dimension in the same
> exported function."

Also in the thread (author correction/notes):
- "The NDELTA=1 run prints an `ANECCompile() FAILED ... MLIR MPS to ANEC conversion failed` error on the first
  execute. **The runtime falls back and the call still completes (exit 0).**"
- Composite op confirmed: `from coreai_torch.composite_ops import GatedDeltaUpdate`, constructed as
  `GatedDeltaUpdate(use_qk_l2_norm=True)`, called as
  `self.gdu(q, k, v, g.permute(0,2,1), beta.permute(0,2,1), ss)` → returns `(out, new_ssm)`.
- `SDPA` externalized breaks export entirely (issue #1), so SDPA must be removed from `_EXTERNALIZE_SPECS`.

---

### coreai-torch#8 — `Converter aborts (bad_optional_access) on aten.arange with float start/end/step args` — OPEN but FIXED on main
```
coreai-torch 0.4.0: converting 1 program(s) to Core AI
bad_optional_access was thrown in -fno-exceptions mode
[process aborts]
```
Key nuance (verbatim): *"Integer arguments work, regardless of the requested output dtype — it is the
*argument types* that matter, not the tensor dtype."* Real-world trigger: DETR sine position embeddings call
`gen_sineembed_for_position(..., d_model / 2)`, producing `torch.arange(128.0)`.

Resolution comment (@eyupcanakman, CONTRIBUTOR, 2026-06-28):
> "This no longer reproduces on current main. The minimal repro (`x + torch.arange(8.0, dtype=x.dtype)`
> through `to_coreai()`) aborts with `bad_optional_access` on the pre-#13 commit but **converts cleanly from
> #13 (53d6bdd) onward**, including HEAD."

Fixed by PRs #13, #25, #27 (see PR section). **Still OPEN as of 2026-07-27** despite being fixed.

---

### coreai-torch#3 — `Support for transposed conv3d` — OPEN
Model: UNETR (MONAI) 3D segmentation. Hits an explicit converter guard at
`coreai_torch/_aten_to_core.py#L1179` raising **`Transposed conv3d is not yet supported`**. Env
`coreai-core==1.0.0b1`, `coreai-torch==0.4.0`. No maintainer answer yet.
Note: PR #40 fixed transposed conv **1D/2D**; 3D remains unsupported.

Documented conversion snippet from this issue (canonical minimal flow):
```python
import coreai, coreai_torch
converter = coreai_torch.TorchConverter()
exported_program = exported_program.run_decompositions(coreai_torch.get_decomp_table())
converter.add_exported_program(exported_program, input_names=["features"], output_names=["logits"])
core_ai_program = converter.to_coreai()
```

---

### coreai-torch#33 — `Segfault: TorchConverter derived program segfaults on .optimize()` — CLOSED (fixed by macOS 27 β3)
Model: BiRefNet Swin-Large (220M), `ZhengPeng7/BiRefNet_HR-matting`, 38 unique aten ops.
Status matrix (verbatim from body):
```
to_coreai()   succeeds
save_asset()  succeeds (produces a valid .aimodel, 426 MB at fp16)
optimize()    segfault
Individual passes (legalize-to-core, core-to-odix)  segfault
```
**Named optimize() passes: `legalize-to-core`, `core-to-odix`; the crash site is `apply_passes_sync`.**
Resolution (@andremolnar): *"Tested again in Mac OS 27.0 Beta 3 (26A5378n) and I am no longer seeing a crash."*
Maintainer @jakesabathia2: *"Thanks for the update. If you start seeing the issue, please re-open this issue."*

---

### coreai-torch#37 — `[Bug] LLVM ERROR: cannot unwrap empty odiec_module_t` — CLOSED
Author `zli96`. Repro: `python models/edsr/export.py` from `coreai-models` (EDSR super-resolution),
then `xcrun coreai-build compile exports/edsr_r16f64_x2_float32_static.aimodel` OR
`asyncio.run(AIModel.load(...))`.

Error (verbatim, abbreviated):
```
loc(fused<{call_stack = ["PixelShuffle$1", "Upsampler$1", "Sequential$19", "EDSR$1"],
  identifiers = ["pixel_shuffle"]}>[...]): error: expected AICode versioned location, got: loc(fused<...>)
loc(...): error: Failed to convert to versioned IR
LLVM ERROR: cannot unwrap empty `odiec_module_t`
```

**Named internals:** `TorchConverter` hardcodes
```python
debug_config = _DebugInfoRecorder.Config(
    include_stack_trace=True,
    options=options,
    verify_debuginfo_locations=_get_verify_debuginfo_locations_enabled(),
)
```
in `converter.py`. Monkeypatch workaround (from the issue, works on 0.4.0):
```python
converter = TorchConverter()
if hasattr(converter, "_debug_info_recorder") and hasattr(converter._debug_info_recorder, "config"):
    cfg = converter._debug_info_recorder.config
    converter._debug_info_recorder.config = cfg.__class__(
        include_stack_trace=False, options=cfg.options,
        verify_debuginfo_locations=cfg.verify_debuginfo_locations)
```
**Authoritative resolution:** upgrade to coreai-torch **0.4.1**. Confirmed by reporter: *"Updating
coreai-torch fixes it."*

The same error text also appears in coreai-models#77 (Flux on iPadOS beta 3) — maintainer @stikves there:
> "`LLVM ERROR: cannot unwrap empty odiec_module_t` — Yes, **Beta 3 needs new exports and clean re-compile**"

---

### coreai-torch#44 — `Migration path for .aimodel artifacts already published with coreai-torch 0.4.0?` — CLOSED ⭐ high-value
Author `john-rocky` (maintains a ~60-model community zoo). Env macOS 27 β3, `coreai-build 3600.75.3`,
`coreai-core 1.0.0b2`.

What he tried and what it did (all verbatim findings):
- **`coreai-build package`** re-emits the asset and the producer stamp updates to `coreai-build-3600.75.3`,
  *but the IR locations are untouched* — compiling the repacked `.aimodel` still fails identically.
- **`coreai-build inspect`** reads the same asset fine — "function signatures, inputs/outputs and states all
  print correctly. So the payload itself isn't corrupt; only the location metadata is in the pre-0.4.1 form."
- Pinning back to `coreai-core 1.0.0b1` does not help — "the gate is OS-side from beta 2."

**MAINTAINER ANSWER (@cymbalrush) — the migration recipe, verbatim:**
> "Thank you for reporting the issue. Could you try using `strip_debug_info` to remove debugging metadata?
> This should prevent the compiler failure. After stripping the debug information, make sure to save the
> updated asset."
```python
from coreai_torch.debugging.debug_info import strip_debug_info
from coreai.authoring import AIModelAsset
from pathlib import Path

# Load an existing asset
asset = AIModelAsset.load(Path("model.aimodel"))
coreai_program = asset.program

# Strip debug info (modifies the program in place), then save
coreai_program = strip_debug_info(coreai_program)  # NOTE: maintainer's snippet calls it as a statement
coreai_program.save_asset(Path("model_stripped.aimodel"))
```
(exact maintainer code was `strip_debug_info(coreai_program)` then `coreai_program.save_asset(...)`;
implementation pointer given: `https://github.com/apple/coreai-torch/blob/main/coreai_torch/debugging/debug_info.py#L539`)

Closed by @gokulkrishna98: *"Closing the issue. Please feel free to raise a new one, if the issue still persists."*

**Guide takeaway:** the 0.4.0→0.4.1 artifact break is recoverable *without* re-conversion via
`coreai_torch.debugging.debug_info.strip_debug_info` + `coreai.authoring.AIModelAsset.load(...).program` +
`save_asset`. `coreai-build inspect` succeeding is NOT evidence a model will compile.

---

## 2. coreai-torch — notable PRs (behavior changes worth documenting)

| PR | State | What it changes |
|---|---|---|
| **#50** `[clean up] Remove run_transforms helper in favor of AIProgram.optimize()` | MERGED 2026-07-23 | The `run_transforms` test helper is gone; **stateful tests now call `result.optimize()` directly**. Signals `AIProgram.optimize()` is *the* pass-driver API. |
| **#43** `argmin-negation-overflow: fix aten.min.dim indices at dtype-extremal minima` | MERGED 2026-07-20 | `replace_min_dim` computed argmin as `argmax(x * -1)`. `0 * -1 == 0` for unsigned and `-128 * -1` overflows int8, so **`values` was correct but `indices` was silently wrong** at dtype extremes. Fix: bitwise complement `~x = x ^ -1` (`broadcasting_bitwise_xor` with an all-ones constant) for integer dtypes; float keeps `x * -1`. |
| **#42** `mean-dtype-kwarg-crash` | MERGED | Cast operand to output dtype before `reduce_mean`. |
| **#45** `int-reduce-int64-narrowing-overflow` | **CLOSED, not merged** | See below — important known gap. |
| **#41** `Fix cat dim on packed intx tensors` | OPEN | `SubbyteTensor.__torch_dispatch__`'s `aten.cat` branch reads `dim` via `fill_defaults` but never passes it, so **every `cat` on a packed intx/uintx tensor runs on dim 0**. Two `(2,4)` tensors with `dim=1` give `(4,4)` instead of `(2,8)`, silently. Affects both `IntxTensor` and `UintxTensor`. File: `coreai_torch/_compression/_intx.py`. |
| **#40** `Fix conv transpose lowering` | MERGED 2026-07-15 | Two bugs in `_conv_transpose`: (1) the 1D path did `coreai.reshape(result, coreai.slice_(coreai.get_shape(result), [0],[3],[1]))` — a **runtime-shape reshape erases static types → `tensor<?x?x?xf32>`**, and a downstream `coreai.shrink_dims` then failed MLIR verification at `save_asset()` with *"shrink dimension 1 has dynamic dimension length in input tensor"* / `RuntimeError: failed to persist mlasset`. (2) `output_padding` was emulated by pre-padding the input, which in a stride>1 transposed conv adds `stride` instead of `output_padding` (padding=0, output_padding=1, stride=2 → length 136 vs PyTorch's 135) — **silently wrong at runtime**. Fix uses `coreai.shrink_dims(result, [-1])` and passes `padding`/`output_padding` natively to Core AI's `conv_transpose2d`. Unblocks htdemucs-style audio source separation. |
| **#39** `Allow newer versions of PyTorch than we have verified` | MERGED | Removes the max PyTorch pin; warns if newer than verified. Also adds pre-commit setup instructions to README. |
| **#38** `Support Latest Version of PyTorch` | MERGED | — |
| **#36** `Bug fix: max_pool2d default stride value` | MERGED | Converter assumed `stride` was always set; **PyTorch's default is `None`, meaning `kernel_size`**. |
| **#35** `atan2: propagate NaN instead of returning 0/pi at x == +/-0` | MERGED | The x=0 branch classified purely via comparisons (`y > 0`, `0 > y`), all `False` for NaN, so `atan2(NaN, +0.0)` returned `0` and `atan2(NaN, -0.0)` returned `pi`. Adds an explicit `y != y or x != x` check with top priority. |
| **#34** `[DO NOT MERGE] Try to add RNN ops as composite ops` | OPEN | RNN ops are **not** composite ops today. |
| **#32** `Fix integer true-divide silently truncating instead of promoting to float` | OPEN | `div.Tensor`/`div.Scalar`/`true_divide.Tensor` were wired to the generic `replace_binary_ops`, which keeps same-kind integers as integers — correct for add/sub/mul, **wrong for true divide**: it divided as ints then cast, dropping the fraction on *every* backend. Re-points to `replace_truediv`. Same latent bug in `replace_div_tensor_mode`'s `rounding_mode=None` branch. `floordiv`/`mod`/`fmod`/`rounding_mode="floor"/"trunc"` were already correct. |
| **#31 / #30 / #29** pad | MERGED | **#29 `Do not decompose pad op`** — pad with modes other than `constant` was decomposed into many small ops, complicating the IR; pad is now excluded from the default decomposition table and lowered directly. Touches `docs/api/supported-aten-ops.md`. |
| **#28** | MERGED | Version bump; `coreai-core` → b2. |
| **#27 / #25** arange | MERGED | `fix(arange): guard si32 path on all operands being integer-typed`; `preserve static output shape for float-dtype arange with integer bounds`. |
| **#24** `[converter] Fix negative axis in quantize/dequantize lowering` | MERGED 2026-07-08 | `coreai::quantize`/`coreai::dequantize` normalized a negative axis as **`axis + rank - 1`**, off by one from the eager op which uses **`axis + rank`**. A per-channel `axis=-1` landed one dimension early; when the channel and its neighbour share a size there is *no shape error* — the model silently picks the wrong channel. File `coreai_torch/_custom_to_core.py`. |
| **#23** | MERGED | `implement aten::atan2 conversion`. |
| **#18** `externalize: skip submodules not invoked in the exported graph` | MERGED | Previously raised `ValueError: Custom op for '<name>' not found in any ancestor program` from `_find_program_for` and aborted the whole conversion; now a `UserWarning`. Files: `coreai_torch/_utils.py`, `coreai_torch/externalize.py`. |
| **#16** | MERGED | `Add aten.masked_scatter lowering`. |
| **#15** | MERGED | `Support SymInt repeats in aten.repeat lowering`. |
| **#14** | MERGED | `Fix cat lowering when promoted shape still has dynamic axes`. |
| **#13** `Harden mixed-source SymInt lowerings under dynamic shapes` | MERGED 2026-06-15 | Six fixes, all one root cause: "FX graphs that mix SymInt-derived Values (varying ranks / element types) with plain-int constants flow into coreai ops whose verifiers require uniform operands." Specifically: register bare `aten.pow` and bare `aten.round` in `_op_map`; `upsample_build_output_shape_dynamic` normalizes each `(out_h, out_w)` to rank-1 `si32`; `get_operand` mixed-list path same normalization for `view`/`expand`/`reshape`/`repeat` dim-vector concat; `replace_cat` reshapes a dynamic non-concat axis to a sibling's known static size; `replace_arange_start_step` unifies start/end/step to the FX node output dtype before `coreai.range_`. New helper **`to_rank1_int32(v)`**. |
| **#12** CI | MERGED | GH Actions on **self-hosted Apple Silicon runners** labeled `[self-hosted, macos, tahoe, ARM64]`. Jobs: `lint` = `ruff check . && ruff format --check .`; `python-test` = `pytest tests/ -n auto -m "not slow"`. Guard `if: github.repository == 'apple/coreai-torch'` so forks don't run. "The DSL/composite tests require **Metal + MLX** on Apple Silicon." |
| **#19** | OPEN | `dump op tests in more rigorous format`. |

### coreai-torch PR #45 (CLOSED without merge) — a known-live correctness gap worth documenting
`torch.sum` / `torch.prod` on a narrower integer input (e.g. `int32`) promote the accumulator to `int64`
per PyTorch's contract. But `replace_sum_dim_intlist` / `replace_prod_default` / `replace_prod_dim_int`
cast the input to a target type from **`get_output_element_type_from_node`** (`coreai_torch/_utils.py`),
which unconditionally narrows int64→int32 via **`_NARROW_TORCH_DTYPE`**.

> "That made the reduction itself run (and overflow) in `int32` instead of `int64`, **silently wrapping
> identically on every backend (interpreter, cpu, gpu, ane)** — this corrupts the lowered IR itself,
> upstream of any backend."

Proposed (unmerged) fix: `get_unnarrowed_output_element_type_from_node`. Author's note:
> "**Known related gap, intentionally not fixed here:** `replace_cumsum` has the same accumulator-narrowing
> shape … `cumsum`'s narrowing appears to additionally **crash** rather than silently wrap when pressed with
> an overflowing input."

Also states: "CoreAI's IR already supports `int64` (`si64`) as a first-class type."

### Contributor-process gotchas surfaced in torch PRs
- @gokulkrishna98: *"Please install pre-commit, to resolve linting issues:
  https://github.com/apple/coreai-torch/blob/main/.pre-commit-config.yaml"*
- @gokulkrishna98: *"for merging, your commits must have **verified signature**. I think you have to setup
  signing-key ssh for this GitHub account."*
- Known CI/lint mismatch (@eyupcanakman, PR #41): *"That format failure is **ruff 0.16.0**, which started
  formatting python code blocks inside `.md` files. CI installs the newest ruff from the dev extra while
  **pre-commit pins v0.12.8**, so the six docs files it flags fail on a clean main too."*
- Test suite invocation used by contributors:
  `uv run pytest tests/ -n auto -q -p no:rerunfailures -p no:randomly`
- Known flaky: `tests/composite_ops/test_gated_delta_update.py` (`@pytest.mark.flaky(reruns=3)`).

---

## 3. coreai-optimization (`coreai-opt`)

### Issue #7 — `FP16 casting pass does not guard against activation-level overflow (softplus, exp, logsumexp)` — OPEN ⭐ maintainer answer
Author `Ashutosh0x`. Names the API: **`coreai_opt.casting.cast_fp32_to_fp16()`**, and internals
**`casting.py`**, **`check_tensor_overflow_fp16()`**, **`handle_overflow_op()`**, **`handle_non_overflow_op()`**.

Core problem (verbatim): the pass "correctly guards against **static tensor overflow** (weights/constants >
FP16_MAX = 65504), but does not account for **activation-level overflow**".

Worked numbers (verbatim):
```
exp(10.4) ≈ 32,900 (fits fp16)
exp(11.0) ≈ 59,874 (barely fits fp16)
exp(11.1) ≈ 66,686 → OVERFLOW → output collapses to 0
```
Thresholds: softplus x ≈ 10.4; logsumexp x ≈ 7.63; logcumsumexp x ≈ 11.09.

**The compound effect (verbatim):**
> "When `coreai-optimization` applies weight compression (palettization, quantization) AND fp16 casting
> together: 1. Quantization introduces rounding errors in weights 2. These errors can shift activation
> distributions 3. Values that were safely below the overflow threshold may now exceed it 4. The casting
> pass has no mechanism to detect or prevent this"

**MAINTAINER ANSWER (@crowbat, CONTRIBUTOR), verbatim:**
> "Thanks for raising this issue @Ashutosh0x . You're right that the casting utility currently only considers
> statically available tensors when choosing whether or not to cast parts of the model to lower precision.
>
> Irrespective of any specific decompositions, it would be useful to enhance the casting utility to handle
> one or both of the following:
> - using **calibration logic to analyze activation tensor ranges** when determining casting locations
> - **allowing the user to specify specific ops or op types to ignore being casted**
>
> Marking this as a feature request issue.
>
> Before such handling is in place, **a workaround could be to manually edit the original Pytorch model
> definition to substitute stable versions of ops like `Softplus`**, avoiding the need for changes in either
> `coreai-opt` or `coreai-torch`."

**Guide takeaway:** as of 2026-07, the *sanctioned* fix for fp16 activation overflow is
**rewrite the PyTorch module**, not a converter or optimizer flag.

### Issue #41 — `Shared/tied weight gets its dtype and QAT schedule from different module configs (graph mode)` — OPEN
Author `eyupcanakman`, commit `3e01e4a`, torch 2.8.0, Python 3.12, macOS.

Repro shape: two `nn.Linear` sharing one weight, `l1` int8 + `enable_fake_quant=1`, `l2` int4 +
`enable_fake_quant=5`. Result (verbatim):
```
distinct weight FQ objects: 1
weight FQ dtype quant_min/quant_max: -8 / 7  -> int4     # l2, declared last
weight FQ governing schedule enable_fake_quant step: 1   # l1, first in graph
step=1 fake_quant_enabled=1    # fires at step 1, not l2's step 5
```

**Root cause names two independent owner-resolution paths:**
- Schedule owner ← `_get_fake_quantize_modules` in `_graph/quantizer.py`, which walks the FX graph and maps
  each shared FQ to the **first consumer with `nn_module_stack`** → graph order picks `l1`.
- Dtype owner ← `_get_state_node_shared_spec` in `_graph/_annotation_utils.py`, which keeps the spec of the
  **user annotated first in priority order**, and priority follows **config declaration order** → `l2` wins.

> "Eager mode has the same split. It warns about the schedule conflict, but **the warning only mentions the
> schedule, not the dtype**."

Test-gap noted: `tests/quantization/test_qat_schedule.py::test_shared_weight_keeps_first_schedule` gives both
modules the same dtype, so the conflict is never covered.

API names confirmed: `QuantizerConfig(global_config=..., module_name_configs={...}, execution_mode="graph")`,
`ModuleQuantizerConfig(op_state_spec={"weight": wspec(torch.int8)}, qat_schedule=QATSchedule(enable_observer=0, enable_fake_quant=1))`,
`Quantizer(model, cfg)`, `q.prepare((torch.randn(1, 10),))`.

### Issue #16 — `KMeansPalettizer.prepare loads sensitivities with torch.load without weights_only=True` — CLOSED (fixed by PR #18)
File `src/coreai_opt/palettization/kmeans/palettizer.py`:
```python
# line 202 — unsafe (pickle => code execution)
sensitivities = torch.load(sensitivity_path)
# line 723 — safe (contrast)
model.load_state_dict(torch.load(checkpoint_path, weights_only=True))
```
CWE-502. Realistic untrusted-input path: "Sensitivities are expensive to compute for large models and are
therefore commonly shared/redistributed (like checkpoints)". API confirmed:
`KMeansPalettizer(model, config).prepare(example_inputs, sensitivity_path=...)`.
Maintainer @aseemw: *"Thanks for reporting the issue… Please feel free to go ahead and open up a PR! If the
fix passes the CI, we can merge it."* → merged as PR #18.

### coreai-opt v0.2.0 release notes — the authoritative API map + **KNOWN ISSUES** (verbatim, highly quotable)

Key APIs:
- `coreai_opt.quantization.Quantizer` — "Supports weight-only quantization and activation quantization, via
  calibration and training modes, for **Integer and FP8/FP4** dtypes." Config: `QuantizerConfig`.
- `coreai_opt.palettization.KMeansPalettizer` — "Supports kmeans + sensitive kmeans based Palettization."
  Config: `KMeansPalettizerConfig`.
- `coreai_opt.pruning.MagnitudePruner` — "for pruning weights of the model via fine tuning."
  Config: `MagnitudePrunerConfig`.
- `finalize` API — "After compressing PyTorch models, `finalize` API updates the model to make it ready to
  conversion via coreai-torch to deploy using the Core AI framework"
- `coreai_opt.casting.cast_fp32_to_fp16()` — "autocast a torch exported program from FP32 precision to FP16
  (weight and activations)"
- `coreai_opt.inspection.*` — model inspection utilities
- `coreai_opt.coreai_utils.*` — "a few methods to apply a graph pass to a given `AIProgram` to compress
  weights. **While compressing a PyTorch model is the recommended path**, this maybe useful for testing and
  debugging."
- Docs: `https://apple.github.io/corai-optimization` (sic — typo in the release note)

**Known issues (verbatim):**
> - Tying model weights (e.g. `layer1.weight = layer2.weight`) after quantizer finalize in eager execution
>   mode will fail
> - For models with shared weights, in Eager mode, **MODULE_NAME > MODULE_TYPE precedence is only honored if
>   you express the override via `module_state_spec`. With `op_state_spec` alone, it depends on forward-pass
>   execution order.**
> - Model Inspector utility only supports graph mode and `compressor={None, Quantizer}`
> - For models with shared weights using **different local names** (last part of the name after the rightmost
>   "."), in graph mode quantization, only one particular local name is matched. To know which name, users
>   must examine the torch exported graph or view ModelInspector summary for modules sharing the weights.
>   Alternatively, users can configure the same weight spec for each distinct local name to be safe.

### coreai-opt v0.2.1 release notes (verbatim)
Added: "Support palettization of `ConvTranspose1d`/`ConvTranspose2d`/`ConvTranspose3d` layers via
`KMeansPalettizer`"; "Support for `EAGER` execution mode in model inspection utility".
Fixed: "Fixed pruning mask `dtype` to match that of the weight being pruned"; "Fixes to allow better support
for `bfloat16` `dtype` in palettization and quantization".

### coreai-opt PRs worth documenting

| PR | State | Substance |
|---|---|---|
| **#56** `Block activation support` | OPEN | "Enable **block activation quantization** support (limited to pre-finalize stages)". Files: `_eager/_prepare_for_export.py`, `_graph/_prepare_for_export.py`, `spec/granularity.py`. |
| **#54** `build: redesign version scheme` | OPEN | `main` always carries next release + `.dev0`; `_about.py` stores `latest_released_version` as source of truth; `make build` vs `make build-dev` (`.dev<timestamp>+<sha>`); `make version` reads `_about.py` as plain text, no venv; new `check-about-version` pre-commit hook. Env var **`COREAI_OPT_VERSION_EXTENSION=1`** switches `0.2.2` → `0.2.1.1`. Documented release workflow: branch `release/vX.Y.Z` off `main`, bump `main` immediately, **"Do not merge the release branch back into `main`."** |
| **#52** `fix: try per-channel act quant for shared observers but fall back to per-tensor if unsafe` | MERGED 2026-07-24 | Previously **always** forced per-tensor activation for "channel altering ops". Now: (1) if shape before/after changes → per-channel unsafe; (2) if the per-channel axis changed → unsafe; (3) if unsafe, **log to the user and use per-tensor**. Logic in `_shared_granularity_axis_is_unsafe` (`_graph/_utils.py`). Pooling layers newly included in channel-altering ops. |
| **#44** / **#42** `CoreMLExportError` | MERGED | New `validate_coreml_compatibility` / `validate_coreml_palettization_compatibility` in `src/coreai_opt/_utils/export_utils.py`; `CoreMLExportError` now raised for **incompatible configs** as well as dtypes. **"I verified that CoreML doesn't support per-channel activations"** (@guru-desh). |
| **#40** `Constraint-queue reconciler for quantization annotation` | OPEN, +2326/−523 | Full rewrite of graph-mode annotation. Motivating bug: **YOLO** subgraph `concat(conv(...), sigmoid(...), sigmoid(...))` — sigmoid has a fixed (0,1) qspec, conv a floating one; the old order-dependent propagation crashed. New model: `NodeSlot` → `ProvisionalQSpec` map (`_provisional_qspec_generation.py`), constraint generation, a queue processed by `annotate_via_reconciliation` (`_qspec_reconcile.py`) that can **relax** (sigmoid (0,1) + hardtanh → (-1,1)), force a winning field by priority, merge into a shared qspec, or error. "Convergence here is guaranteed because each time we change a qspec, we lower the priority value of some field in the graph (0 is the 'highest priority')." New files: `_qspec_constraint_generation.py`, `_qspec_constraints.py`, `_qspec_resolution.py`, `_qspec_types.py`, `_annotation_config.py`, `_annotation_pattern_registry.py`. |
| **#39** `Add graph mode debugging hints and troubleshooting doc` | MERGED | Adds `docs/src/debugging/graph_mode_troubleshooting.md` and `model_inspection.md`; **new `export_with_strict` flag that sets `strict=True/False` in `torch.export.export`**; error messages in `prepare()` now enumerate all options; `get_partitions..` errors now include the module name "to help with debugging by skipping that layer". |
| **#34** `Enable support for FP4 weight quantization for non-conv layers` | MERGED 2026-07-13 | Fixes (1) "Handling subbyte tensors with **safetensors**, which doesn't have that support by default"; (2) `validate_fp4_export` now allows **4D tensors with 32 block size**. |
| **#31** | MERGED | **Removes the `coremltools` dependency**; uses `torch.utils.cpp_extension` to load `kmeans1d`. |
| **#25** `Enable weight fake quantization in calibration mode` | MERGED | `Quantizer.calibration_mode()` previously disabled fake quant on **both** weights and activations; now only activations, "so activation observers see the effect of quantized weights when computing activation ranges." New helpers `enable_weight_fake_quant` / `disable_activation_fake_quant` in `_fake_quant_utils.py`. |
| **#22** `Fix output spec adjustment for fixed qparams ops` | MERGED | relu/relu6/sigmoid/tanh etc. — "Qscheme was not being set correctly, and no fixed ranges were ever in place." Removes fake-quantize's independent `qscheme` attribute in favor of `qparams_calculator.qscheme`. **MNIST test accuracy expectation moved from <88% to <94%** because hardtanh output quantizers are now asymmetric with float range (0.0, 1.0). |
| **#15** `export root-module weights in graph CoreML` | OPEN | `Quantizer.finalize(backend=ExportBackend.CoreML)` crashes on a bare `nn.Linear`: `_get_weight_input_names` splits the `get_attr` target on the last dot; a root-module parameter has a **dot-less target** (`weight`) → `ValueError: Invalid weight target path: weight`. Fix returns `""` as the module name (`named_modules()` has a `""` key). |
| **#45** `fix(pruning): normalize a negative channel axis` | OPEN | **`ChannelStructured(axis=-1)` prunes the wrong channels.** `_compute_channel_mask` compares each dim index against the raw axis; a negative axis never matches, so the per-channel L1 norms collapse to a scalar. With >1 channel kept it fails with `RuntimeError: selected index k out of range`. `PerChannelGranularity` already documents/resolves negative indexing. |
| **#38** | MERGED | `InvalidExecutionModeError` for unknown execution modes. |
| **#37** | MERGED | Test fix: give `AIModel` a **temp file path, not a directory**, when saving an asset. |
| **#36 / #35** | MERGED | Unskipped eager CoreML int8-activation export tests ("they now pass") and Graph CoreML export tests ("segfault no longer occurs"). |
| **#21** | MERGED | Test infra: **allow selection of CoreAI compute unit during inference**. |
| **#6 / #2** bfloat16 | MERGED | `_cluster_weights_1d` clustered via `block_weight.flatten().numpy()`; **numpy has no bfloat16 dtype** → `TypeError: Got unsupported ScalarType BFloat16`. Fix casts bf16 → fp32 before numpy, matching `_cluster_weights_2d`'s `vectorized.float()`. Centroids cast back by the caller so LUT/reconstruction stay bf16. |
| **#5** `match the float_range bound dtype to the input` | MERGED | `StaticQParamsCalculator._get_min_and_max_val` crashes on fp16/bf16 when `float_range` fixes only one side: the fixed bound comes from `torch.full` (float32) and the other from the range calculator (input dtype) → `AssertionError: Expecting min_val and max_val to have the same dtype` from `choose_qparams_affine_with_min_max`. |
| **#3** eager subclass axis defaults | **CLOSED — intentional** | See maintainer quote below. |
| **#1** `match the pruning mask dtype to the weight` | MERGED | `MagnitudePruner` mask buffer was float32 and only re-cast to the weight *device*; masking a half weight promoted back to float32 → `RuntimeError: expected m1 and m2 to have the same dtype, but got: c10::Half != float`. |
| **#19 / #32 / #50** CI | MERGED | Linux `ubuntu-latest` pipelines; smoke tests across a python × torch matrix with dependency groups `torch_2_8/2_9/2_10/2_11` (build-matched torchao/torchvision per pytorch/ao#2919); `make env-lowest-torch` / `env-highest-torch`. |

**Authoritative "this is intentional" answer (coreai-opt PR #3, @pkmandke, MEMBER):**
> "Applying the default axis for user-defined subclasses such as `class MyLinear(nn.Linear)` could be
> misleading and is **intentionally unsupported in eager mode**. Specifically because a custom subclass may
> use the weight in a way such that the default axis may no longer apply. Could you please try specifying an
> explicit axis for such custom modules using the config?"

Contributor's own summary of the difference (worth quoting in a guide):
> "The graph path can default the axis because it resolves through the consuming op, but inferring one
> through an eager subclass is a guess the framework shouldn't make."

Failure text on the unsupported path:
`ValueError: Weight fake-quantize modules with unresolved axis=None remain after applying defaults`

**coreai-opt build/dev commands seen:** `make env`, `source .venv/bin/activate`, `make check`,
`make test-smoke`, `make test-tutorials`, `make test-lowest-pytorch`, `make build`, `make build-dev`,
`make version`, `make render-api-index`, `make env-lowest-torch`, `make env-highest-torch`.
Full-suite scale as of June 2026: `4529 passed, 1417 skipped, 567 xfailed, 7 xpassed` in ~30 min.

---

## 4. coreai-models

### Issue #124 — `iOS: pipelined decode bundle produces corrupt output when the KV cache state is bound at seq >= 2048` — OPEN ⭐
Author `john-rocky`, 2026-07-24. iPhone 17 Pro (A19 Pro), iOS 27 beta `24A5380h`. int8 LanguageBundle from
`coreai-core 1.0.0b2`; static S=1 `input_ids [1,1]`; dynamic KV state `[44, 1, 8, ctx, 128]`, max_context 4096.
`COREAI_CHUNK_THRESHOLD=1`.

**Result matrix (verbatim):**
| Condition | Bound KV seq | Output | Decode tok/s | TTFT |
|---|---|---|---|---|
| maxTokens 150 / 200 (greedy) / 512 | ≤1024 | coherent, correct | 6.2–7.6 | 5.2–5.6 s |
| maxTokens 1024 | 2048 | corrupt from token 1 (multilingual token soup) | 55.5 | 0.65 s |
| maxTokens 2048 | 4096 | corrupt from token 1 | 65.5 | 0.62 s |
| `.fixedSize` KV (4096 at engine creation), maxTokens 2048 | 4096 | corrupt | 58.2 | 0.71 s |
| Full `Library/Caches` evict, then fresh 24.8 s on-device compile, fixedSize 4096 | 4096 | **still corrupt** | 59.4 | 2.9 s |
| macOS M4 Max, maxTokens 1024 (greedy) | 2048 | token-exact vs fp32 oracle | 55.5 | — |

Diagnostic signature (verbatim): *"The corruption is accompanied by physically impossible throughput (~10× the
weight-bandwidth floor) and a collapsed TTFT, which suggests the miscompiled specialization elides or
mis-addresses the state reads, so the pipeline never stalls on them."*

Sample corrupt output: `Джерела随著 Джерела Джерела ... 参差不 vegg 佛罗伦 çà KDW 要知道 ...`

Impact framing worth quoting:
> "Any chat host that passes a generous `maxTokens` (e.g. a 2048-token response budget — a common default)
> silently crosses the shape cliff on iOS and produces garbage, while every 'benchmark-sized' run (g=256)
> stays in the clean regime and looks perfect."

Also documents the engine's growth policy: *"The engine pre-grows the KV cache to `prompt + maxTokens` before
prefill, so `maxTokens` selects the bound state shape; the growing cache doubles 256 → 512 → 1024 → 2048 → 4096."*

**Maintainer triage questions (@stikves) — a useful checklist:**
> "1 - Does this happen with the sequential engine as well (`coreai-sequential`, which can be requested in the
> `CoreAILanguageModel.init(..., variant: "coreai-sequential")`
> 2 - Are the versions of macOS, iOS and Xcode are aligned (all of them Beta 4, or similar)?
> 3 - Is this error encountered only for this specific model / quantization combination?"

### Issue #118 — `[Swift runtime] CoreAISequentialEngine rejects hybrid models with four persistent states` — OPEN ⭐ authoritative NO
Author `massif-01`. Apple source commit `04a3fd6cfe9bfae9cf05b1f246cf915d930d1c0a`. FB **FB23893830**.

Function contract of the 16 KB no-weights repro:
```text
inputs: input_ids, position_ids
output: logits
states: keyCache, valueCache, convState, recState
```
Error (verbatim):
```text
Expected 2 states (KV cache), got 4: states=["keyCache", "valueCache", "convState", "recState"], outputs=["logits"]
```
Root cause: `descriptor.stateNames.count == 2` guard.

**MAINTAINER ANSWER (@stikves), verbatim — the definitive statement on hybrid/linear-attention support:**
> "Thanks for the report. **The check for only 2 states is deliberate. We currently do not have support for
> linear attention or similar hybrid state models.** Keeping this open for potential future changes."

Reporter's correctness note worth reproducing in a guide:
> "There is also a correctness issue with KV-only prefix rewind. **Recurrent state is a summary of the full
> prefix and cannot be rewound by changing a KV token cursor.** A safe implementation must replay the prompt
> or maintain recurrent checkpoints."

Also names a Swift lifetime constraint: *"uses explicit lexical state bindings required by
`InferenceFunction.MutableViews.insert` lifetime semantics"*.

### Issue #84 — `Monolithic stateful dynamic prefill becomes nondeterministic above 16 tokens` — OPEN ⭐
Author `kylejfrost`. Model `Qwen/Qwen3-0.6B`, macOS monolithic dynamic bundle, **fp16, no compression**,
`max_context_length = 8192`.

**Constants named in source:** `coreai_models/export/_constants.py` → `QUANT_TRACE_QUERY_LEN = 16`,
`QUANT_TRACE_OFFSET = 8`. Path: `coreai_models/models/macos/qwen3.py` uses `SDPA(is_causal=True)` and
`cache.update_and_fetch(layer_idx, offset, key, value, seq_len=seq_len, query_len=query_len)`;
`coreai_models/primitives/macos/cache.py` `KVCache.update_and_fetch` uses `mutable_slice_update` then
`narrow(..., 0, seq_len)`.

Findings:
- default / `chunk16` → deterministic and HF-matching
- `chunk17`, `chunk19`, `chunk20`, `chunk64`, full-batch prefill → **process-to-process nondeterministic**
- Re-exporting with **trace width 64** or **19** does *not* help — so it is not the trace query width.
- An **explicit in-graph causal mask** (instead of `SDPA(is_causal=True)`) also still fails above 16.
- Ruled out: tokenization, sampling (greedy), quantization (fp16 repro), trace width, causal-mask geometry,
  runtime chunk policy.

Impact: *"This forces production runtimes to chunk monolithic stateful prefill at `<=16` for correctness. That
avoids nondeterminism but costs substantial TTFT/prefill throughput. On the same machine/model class, caix
decode is already at MLX parity, while prefill remains slower because the safe path must use many
host-dispatched `<=16` updates."*

**Maintainer response (@stikves) — could NOT reproduce:**
> "I've tried replicating it with both llm-runner and also running the model directly in Python. However I was
> unable to replicate the issue, and got consistent logits every time. Can you describe your machine setup?
> Hardware? M1/M2/…, Base/Pro/Max/Ultra, RAM, GPU Cores? Software? macOS 27.0 Beta N? Xcode version?"

Environment-reporting checklist implied: hardware tier, RAM, GPU core count, macOS beta number, Xcode version.

### Issue #55 — `coreai-build compile SIGSEGVs in MPSGraph anePreCompileBinary on a static-shape LLM with linear INT4 weights (palettized compiles fine)` — OPEN ⭐
Author `john-rocky`. macOS 27.0 `26A5353q`, M4 Max (Mac16,9). `coreai-build` Metal toolchain
**v27.1.5194.15**, build **3600.67.5.8.1**. `coreai-core 1.0.0b1`, `coreai-torch 0.4.0`, `coreai-opt 0.2.0`.
Target arch **h18p** (iPhone 17 Pro). Model `Qwen/Qwen3-0.6B` via `coreai.llm.export`.

**Control that works (verbatim commands):**
```bash
uv run coreai.llm.export qwen3-0.6b --platform iOS \
  --compression 4bit_weight_palettized_group32 --output-name qwen3_0_6b_ios_pure4bit
xcrun coreai-build compile exports/qwen3_0_6b_ios_pure4bit/qwen3_0_6b_ios_pure4bit.aimodel \
  --platform iOS --preferred-compute neural-engine --architecture h18p --output /tmp/ok
# OK — compiled .aimodelc has 31 `*_ANE_region_*` segments, 0 non-ANE.
```

**The crash path.** The CLI couples quant scheme to platform:
`--platform iOS --compression 4bit` → `RuntimeError: macOS quantization preset provided, but platform is iOS`.
So linear INT4 must be applied at the MLIR level:
```python
from coreai_opt.coreai_utils import CompressionGranularity, DType, quantize_weights
from coreai_opt.coreai_utils.common import QScheme
prog = quantize_weights(prog, dtype=DType.INT4, qscheme=QScheme.SYMMETRIC,
                        granularity=CompressionGranularity.PER_BLOCK, block_size=32,
                        weight_num_threshold=32768, in_place=True)
prog.optimize()
```
Crash report (`~/Library/Logs/DiagnosticReports/coreai-build-*.ips`), verbatim:
```
Exception:  EXC_BAD_ACCESS (SIGSEGV) — KERN_INVALID_ADDRESS
Crashing thread: MPSGraphExecutable_queue
  0  libobjc.A.dylib                    objc_release
  1  MetalPerformanceShadersGraph_host  GPU::anePreCompileBinary(MPSGraphExecutable*, llvm::SmallVectorImpl<mlir::…>)
  2  MetalPerformanceShadersGraph_host  BaseModuleRef::compileAndLoadANE()
  3  MetalPerformanceShadersGraph_host  -[MPSGraphExecutable specializedModuleWithDevice:shapedEntryPoints:compilationDescriptor:…]
```
`coreai-build` runs ~5 min at 100% CPU then exits 139, no diagnostic, no `.aimodelc`.

**Key structural facts (verbatim):**
- Palettized weights lower to **`lut_to_dense`**; linear blockwise INT4 lowers to **`blockwise_shift_scale`**.
- `coreai-build inspect` on the crashing asset shows **34 static-shape functions**:
  `extend_{256..4096}_{8,16,64}`, `prompt_opt_*`, `gather_embeddings_*`, `load_embeddings`.
- "The dynamic (GPU) `--platform macOS` export lowers to the **same** `blockwise_shift_scale` form and
  compiles/runs fine on the GPU MPSGraph path — only the **ANE** pre-compiler crashes on it."
- "**`--preferred-compute neural-engine` on the *dynamic* export is a no-op** (still a GPU MPSGraph delegate,
  0 ANE regions)."

Maintainer @carinapeng: *"We will file an internal report and investigate this. I would be helpful to give us
a full crash report."*

**Also documents export path shape conventions:** dynamic (`--platform macOS`) export ships **linear INT4**;
static (`--platform iOS`) export ships **palettized** weights.

### Issue #27 — Gemma 4 12B: MPSGraph scratch-heap overflow + macOS AOT `.aimodelc` load regression — OPEN ⭐ two bugs
Author `john-rocky`. macOS 27.0 `26A5353q`, M4 Max (`applegpu_g16s`), `coreai-build 3600.67.5.8.1`.

**Bug 1 — scratch heap.** At the first decode token:
```
allocateMTLBufferFromMTLHeap: offset 198400 + size 16384 exceeds heap total 212992
.../MPSRuntime/Operations/GPUMemrefOps.mm:687: failed assertion
  'Failed to acquire the source buffer for the ViewOp'
```
Bisection (verbatim):
- `--num-layers 5` (all *sliding*, head_dim 256) → **runs** (~409 tok/s)
- `--num-layers 6` (adds the first *full* layer: head_dim 512, 16 query heads) → **crashes**

> "The failing buffer is exactly `[1, 16, 1, 512]` fp16 = **16384 B**, the full layer's `q_proj` output. It
> scales with the number of full layers (16 KB at 1 full layer, 32 KB at 2) and overflows MPSGraph's ~208 KB
> decode scratch heap (mis-sized by ~2 KB). Sliding-layer Q (`[1,16,1,256]` = 8 KB) fits, and **Gemma 4
> E2B/E4B full layers (8 heads × 512 = 8 KB) also fit and run** — only the 12B's 16-head × 512 Q tips the
> heap over. The crash is **invariant** to every graph-source change tried (KV cache pad↔replicate, uniform
> narrow, `.contiguous()` on Q and on K/V, vanilla vs HF SDPA)."

**Bug 2 — macOS AOT load regression.** Compile succeeds:
```bash
xcrun coreai-build compile <bundle>.aimodel --platform macOS --architecture h16s \
  --expect-frequent-reshapes -o /tmp/aot
```
Load fails:
```
CoreAIDelegates.AIModelError error 3      (raw AIModel.load)
invalidCompiledModel                      (llm-runner / LanguageBundle)
```
> "this macOS build cannot load *any* precompiled `.aimodelc` for a macOS target, while the same Core AI
> runtime loads AOT `.aimodelc` fine on **iOS** (h18p bundles run on iPhone 17 Pro)."

**Sibling report in the same thread (@andrew9123).** `coreai-pipelined` aborts with
`MPSNDArray.mm:893: failed assertion '[MPSNDArray, initWithBufferImpl:…] Error: buffer is not large enough.
Must be 64 bytes'` on stock `coreai.llm.export Qwen/Qwen3-0.6B`; `coreai-sequential` runs the *same bundle*
fine (~170 tok/s decode). Invariant to quantization (4-bit and fp16), `--synchronous-sampling` doesn't help.
Env: macOS 27.0 `26A5368g` β2, M5 (`Mac17,4`) 32 GB, Xcode `27A5209h`, `coreai-build 3600.73.1`.
→ Duplicated as issue **#61**, **fixed by PR #62** ("Some machine configurations seem to require minimum 64
byte size buffers. This bumps up the new ones from 4 bytes to that minimum."). Reporter confirmed fixed.

Useful CLI shown:
```bash
swift run -c release llm-runner --model "$BUNDLE" \
  --prompt "Explain on-device AI in one sentence." --max-tokens 24 \
  --sampling-strategy greedy --inference-engine-variant coreai-pipelined   # or coreai-sequential
```

### Issue #5 — `Official iOS static-shape decode path crashes at runtime … MPSGraph can't lower the data-indexed KV-cache slice_update` — OPEN, **fixed in β4 per maintainer**
Author `john-rocky`, 2026-06-10. FB **FB23024751**.

Decisive isolation (verbatim):
```python
# (a) begin index from a SHAPE symint   — the update_and_fetch path
p = position_ids.shape[-1] - query_len    # symint
# (b) begin index from a RUNTIME TENSOR  — the static / in_step path
p = in_step                               # int32 scalar input
```
| `begin` index | shapes | macOS 27 Mac GPU |
|---|---|---|
| shape symint | dynamic | runs, finite output (exit 0) |
| runtime tensor | dynamic | **SIGTRAP, exit 133** |
| runtime tensor | static | **SIGTRAP, exit 133** |

Per-platform failure modes: Mac GPU `EXC_BREAKPOINT` (SIGTRAP, code 5) in `CoreAIRuntime` →
`_coreai_runtime_os.cpython-311-darwin.so`; iPhone GPU SIGSEGV at first execute; iPhone ANE
`MPSGraphExecutable.mm` → `optimizeOriginalModule` → *"MLIR pass manager failed"* (SIGABRT).

Workaround: *"keep KV as plain model I/O, append the new column with `torch.cat`, and have the host write it
back between steps… Numerically identical (8/8 top-1 vs Hugging Face)."* — and this *localizes* the bug to the
data-indexed slice-update lowering.

**Maintainer answer (@stikves, 2026-07-22):**
> "Thanks for your report, **The underlying issue should be fixed in macOS / Xcode beta 4.** Can you help test
> and verify?"

Names `export/ios.py` static buckets, `KVCacheHandler` fixed-capacity KV state, `CoreAIStaticShapeEngine`,
`set_static_shape_config`, and the per-step `in_step` write.

### Issue #66 — `Composite RoPE partial-rotary mode pairs contiguously — incompatible with transformers partial/proportional rotary` — OPEN ⭐ maintainer answer
Author `kylejfrost`. Affects `coreai_torch.composite_ops.RoPE` as wrapped by
`coreai_models/primitives/macos/rope.py`.

> "The composite `RoPE` partial-rotary mode (`dims < head_dim`) pairs dimensions in a **contiguous block**
> (dim `i` ↔ `i + dims/2`, *inside* the first `dims` dims, passing the rest through). HuggingFace
> `transformers`' **partial / 'proportional' rotary** (any model with `partial_rotary_factor < 1`) instead
> pairs across the **full head_dim half-split** (dim `i` ↔ `i + head_dim/2`), with only the first
> `rope_angles` frequencies non-zero (`inv_freq` zero-padded). The **frequencies are identical; only the dim
> pairing differs**, so the result is silently wrong."

Measured: sliding (full-rotary) layers bit-exact (PSNR ∞); global partial-rotary layer **PSNR ≈ 21.6 dB,
max-abs ≈ 8.2** for gemma-4-26B-A4B (`head_dim=512`, `partial_rotary_factor=0.25` → rotates
dims {0..63}∪{256..319}, not {0..127}). Internal impl named: `_rope_with_cos_and_sin_impl`.

Impact: *"Generation stays coherent (global layers are ~1/6 of the stack), so it passes a smoke test — but it
isn't faithful to the reference, and it **breaks EAGLE/MTP speculative-draft acceptance**."*

Reference fix (verbatim, verified bit-exact):
```python
inv_freq = cat([1/base**(arange(0, 2*rope_angles, 2)/head_dim),
                zeros(head_dim//2 - rope_angles)])           # zero-padded, full-head
ang = positions[..., None] * inv_freq
emb = cat([ang, ang], dim=-1)                                # full-head half-split
x_rot = x * emb.cos() + rotate_half(x) * emb.sin()
```

**Secondary precision footgun (verbatim):**
> "If `inv_freq` is stored as a **registered buffer**, `model.to(bfloat16)` downcasts it and bf16's ~3-digit
> mantissa corrupts the frequencies (cos error ≈ 0.35 at position 200). Recomputing `inv_freq` in fp32 inside
> `forward` avoids it."

**MAINTAINER ANSWER (@stikves):**
> "Thank you, this is a **known issue**, and currently the workaround is **pre-computing the sine/cosine
> tables** for RoPE embeddings: For example:
> https://github.com/apple/coreai-models/blob/9e1ffa5.../python/src/coreai_models/diffusion/flux2.py#L80
> We can keep this issue open until a proper solution replaces the workarounds."

### Issue #83 — `Gemma4 E-series staged export should PAD-mask image-token rows for per-layer embedding inputs` — OPEN
Author `kylejfrost`. Path: `models/macos/gemma4.py`,
`Gemma4TransformerLayerStage.project_per_layer_inputs`, for models with `hidden_size_per_layer_input > 0`.

Pre-fix behavior (verbatim):
```python
inputs_embeds = self.embed_tokens(input_ids)
image_mask = (input_ids == image_token_id).unsqueeze(-1)
inputs_embeds = torch.where(image_mask, hidden_states, inputs_embeds)
per_layer_projection = ...
per_layer_inputs = self.get_per_layer_inputs(input_ids)   # still sees 258880 on every image row
return (per_layer_projection + per_layer_inputs) * self.per_layer_input_scale
```
Validated fix: decouple the image-position projection mask from the PLE identity ids; PLE ids for
image/PAD rows become `pad_token_id`.

Instrumentation numbers (verbatim):
- Raw image-id PLE path: HF-vs-CoreAI layer-0 image-row PLE cosine **0.34706932306289673**; all-layer raw PLE
  delta norm mean ≈ **102.109**
- PAD-masked PLE path: cosine **1.0**; all-layer PLE delta norm **0.0**
- After fix: first token `818`, matching HF; teacher-forced `mm_on_hf_top1=58/64` vs `mm_off_hf_top1=43/64`.

Notes `image_token_id=258880`, `pad_token_id=0`, 266 image rows, staged split `0:21,21:42`, native context
131072. "The 12B `gemma4_unified` path did not expose this because its transformer stages do not use this
E-series `input_ids` / PLE side channel."

Also: *"We are filing this as an issue, not a PR, because the repository notes that PRs are closed."*
(Cross-check: coreai-models#49 reporter says *"PR creation on this repository is currently limited to
collaborators."*)

### Issue #49 — `Swift package fails to compile for the iOS Simulator (no such module 'CoreAI')` — OPEN ⭐ maintainer pushback
Author `KodaKoder`. FB **FB23189921**.

> "`CoreAI.framework` ships only in the device SDK (it's the Neural Engine inference runtime) and is **absent
> from the iOS Simulator SDK**. The library targets currently guard only the macOS-x86_64 case
> (`#if !((os(macOS) || targetEnvironment(macCatalyst)) && arch(x86_64))`), so every source that
> `import CoreAI` fails to compile for an iOS Simulator destination."

Failing targets: `CoreAILanguageModels`, `CoreAIDiffusionPipeline`, `CoreAIImageSegmenter`,
`CoreAIObjectDetector`. Proposed `#if canImport(CoreAI)` across 27 files (+54/−0).

**MAINTAINER ANSWER (@stikves):**
> "I don't think `#if canImport(CoreAI)` is a solution, as the repository is specifically using Core AI for
> all inference purposes. It would basically make all operations into no-op. As for the underlying Simulator
> issue, thanks for bringing this up."

Downstream pain (@Bersaelor): *"it makes it really hard to work with SwiftUI Previews and by extension use
agentic coding in Xcode 27… All I could do was to separate all CoreAI functionality into a separate target
… and weak link"* — which yields
`Module 'CoreAIDiffusionPipeline' was not compiled with library evolution support; using it means binary
compatibility for 'DiffusionKit' can't be guaranteed`.

**STILL OPEN as of 2026-07-27.** Related: issue #12 (also unresolved).

### Issue #41 — `CoreAIPipelinedEngine producer remains active after EOS, causing the next response to crash in drain()` — CLOSED ⭐ great engine-lifecycle material
Author `timokoethe`. macOS 27.0 β1, Xcode 27 β1, gemma3 4-bit dynamic.

Crash: `Fatal error: Engine not returned after drain() — tokenSequence Task stuck?` at
`CoreAIPipelinedEngine.swift:151` (later `:169`, then `:188`), ~5 s after the second `session.respond(...)`.

Reporter's root-cause analysis (verbatim):
> "`CoreAIPipelinedEngine.generate()` starts an independent producer task that keeps generating tokens up to
> `maxTokens` while holding exclusive ownership of the engine. When `respondVanilla()` detects EOS, it records
> `.eos` and stops consuming the stream. However, this does not cancel or await the producer task. The
> producer therefore continues running in the background while `engineInUse` remains `true`."

And the ordering bug that made the first fix insufficient:
> "In `reset()` … `drain()` is called before the active generation is cancelled… `reset()` should maybe cancel
> and await the active generation before draining."
> "Furthermore, the current tests miss this because `MockEngine.reset()` **cancels first**, while
> `CoreAIPipelinedEngine.reset()` **drains before cancelling**, causing the EOS timeout."

Maintainer acknowledgement (@stikves): *"Looks like we are doing `drain` and `cancel` in the wrong order."*
Fixed by **PR #47** (`Fix pipelined engine reset(): cancel before drain`).

**Critical scoping fact (@RichNasz):**
> "before discovering this issue, we tried working around the crash by creating a **new
> `LanguageModelSession` per iteration** with the same model. This also crashes, since **the
> `CoreAIPipelinedEngine` is shared across sessions on the same `CoreAILanguageModel` instance** — confirming
> the fix must be at the engine level, not the session level."

Related follow-on: **PR #80** — `InferenceEngine.generate()` became `async throws` (was `throws`) to fix
`CoreAIPipelinedEngine.swift:82: Fatal error: Trying to acquire engine when it's already in use`.
Root cause quoted: *"PR #64 removed the per-turn `engine.reset()` call to enable multi-turn KV cache reuse.
That `reset()` also served as the serialization point between consecutive turns (it called `drain()`
internally)."* Fix code:
```swift
if let priorTask = _generationTask.withLock({ $0 }) {
    _activeToken.withLock { $0?.cancel() }
    await priorTask.value
}
```
That signature change then broke `ConstrainedGenerator.decode()` (issue #86 / PR #87 — missing `await`):
```diff
-            for try await output in try inferenceEngine.generate(
+            for try await output in try await inferenceEngine.generate(
```

### Issue #58 — `unsupported metadata_version '0.1' (known: 0.2)` — CLOSED ⭐ classic user error
Error text: `unsupported metadata_version '0.1' (known: 0.2)`.

**Root cause (maintainer @stikves → confirmed by reporter):** the `modelURL` was pointed at the **`.aimodel`
file**, not at the **parent bundle directory** containing `.aimodel` + tokenizer + `metadata.json`.
> "Are you pointing your `modelURL` to the `.aimodel` path, or the directory that bundles the LLM assets (the
> one at upper level)?"

Also, Xcode packaging gotcha (verbatim): *"for Xcode resources **'Apply once to folder'** is necessary to have
them move as a single bundle. This can be set on the File Inspector on the righthand side."*

Reporter's docs suggestion: rename the sample variable from `modelURL` to `modelFolderURL`.

### Issue #112 — `Cannot load CoreAILanguageModel in iPadOS` (qwen3-4B) — CLOSED ⭐ entitlement answer
Symptom: `libc++abi: terminating due to uncaught exception of type std::bad_alloc` / `Debug session ended with
code 9: killed`, no useful Xcode console output.

**Resolution (reporter, after maintainer suggested launching without Xcode):**
> "I used the **Console app** and captured a key message: **`Out of Memory`**. I then added the **`Increased
> Memory Limit` entitlement**, and the app no longer crashes."

**Guide takeaway:** on iOS/iPadOS, `std::bad_alloc` from Core AI model load usually means jetsam, and the fix
is the `Increased Memory Limit` entitlement + checking Console.app rather than the Xcode console.

### Issue #102 — `SD 2.1: resolvingDynamicDimensions fails with "Shape at dimension 1 of 96 is not a valid substitution for source shape 77"` — CLOSED
Fixed by **PR #103**:
> "`StableDiffusionPipeline.encodeText()` passed raw token count as the sequence dimension, but **CLIP text
> encoders are exported with a fixed seq_len (77 for SD 1.5/2.x)**. When a prompt tokenizes to a different
> length, `resolvingDynamicDimensions` crashes."
Fix: use `CoreAITextEncoder.encode()` (pads/truncates), and **infer sequence length from the model's input
descriptor at load time** instead of hardcoding 77. New helper `inferSequenceLength()` on
`CoreAIDiffusionModelFunction`.

### Issue #77 — `Flux sometimes fails spuriously before encodeText and then kills my test iPad entirely until restart` — OPEN (13 comments) ⭐ memory-pressure goldmine
Author `Bersaelor`, iPad Pro M4 **8 GB**, iPadOS 27 β2/β3, Xcode 27 β2/β3, uv 0.11.25.

Export + AOT compile commands (verbatim):
```bash
uv run coreai.diffusion.export flux2-klein-4b --platform iOS --overwrite
for m in VAEEncoder_half VAEDecoder_half TextEncoder Transformer_512; do
  xcrun coreai-build compile "$SRC/${m}.aimodel" \
    --platform iOS --architecture h16g --preferred-compute gpu \
    --output "$DST/${m}.aimodelc"
done
```
So a Flux2 bundle = **4 components**: `VAEEncoder_half`, `VAEDecoder_half`, `TextEncoder`, `Transformer_512`.
`h16g` = iPad M4-class arch; `h16s` = M4 Max Mac; `h18p` = iPhone 17 Pro; `h16p` = iPhone 15 Pro-class.

Symptoms: intermittent `Task 1123: signal SIGABRT` inside
`CoreAIDiffusionPipeline/Components/CoreAIDiffusionModelFunction.swift:28`, ~1 in 20–50 generations. Then:
> "When this happens, my iPad is basically in a lost state. Any further attempt to start the app via Xcode
> leads to just: `terminating due to uncaught exception of type std::bad_alloc` … I can also not open the app
> again from the homescreen. **Only thing that helps is restarting the iPad.**"

JIT (uncompiled `.aimodel`) on 8 GB fails outright:
```
MemrefBufferizationRuntime.mm:202: error 'createMemrefHeap: newHeapWithDescriptor returned nil
  (size=3847225344, manualPlacement=1)'
```
(3.85 GB single heap request.)

Beta-3 breakage in the same thread: `error: expected AICode versioned location` / `Failed to convert to
versioned IR` / `LLVM ERROR: cannot unwrap empty odiec_module_t` — maintainer: *"Beta 3 needs new exports and
clean re-compile."*

Another observation worth flagging: *"despite Xcode still being connected with the debugger, after the first
generation, I don't see any logs anymore."*

Maintainer test-fleet note: *"The iPads I used to test this model were all **16GB** versions (M1 -> M5)."*
→ addressed partly by **PR #110** `Fix diffusion GPU memory leak: reuse InferenceFunction`:
> "The diffusion pipeline loaded a fresh `InferenceFunction` on every inference call (~30 per generation) as a
> workaround for an MPSGraph buffer caching bug. **That bug is fixed since macOS 27 Beta 3+.** The workaround
> caused GPU memory to accumulate across generations, leading to SIGABRT after ~20 images."

App-side lifecycle API confirmed: `Flux2Pipeline(from: url, mode: .half)`, `await pipeline?.unloadResources()`.

### Issue #111 — `Flux quality subjectively regressed in beta v3` — OPEN ⭐ authoritative quantization tradeoff
Maintainer @stikves:
> "One option is disabling quantization of the text encoder model (Qwen3), as the images themselves seem to be
> not losing any quality, but only not adhering to the prompt as well."

Then, closing PR #115:
> "Thinking back, **we quantize the text embedding model to able to fit flux pipeline in iPad RAM. It comes
> with some quality cost**, but should not be as much as what is reported here."

Fixed-ish by **PR #120 `Flux2 Updates to Improve Image Quality`** — three concrete changes (verbatim):
> "1. Denoising noise schedule computation (mu and sigma)
> 2. Disable thinking for text encoder
> 3. Use `<|endoftext|>` token (**151643**) instead of `<|im_end|>` (**151645**) for padding"
Files: `python/src/coreai_models/diffusion/flux2.py`, `Flux2Pipeline.swift`, `DiscreteFlowScheduler.swift`.

### Other coreai-models issues, condensed
- **#96** — the PyPI wheel `coreai-models==0.1.0` declares `Requires-Python: >=3.14` though source says
  `>=3.11`. **Maintainer @tjia1818: "the wheel on the pypi.org is not to be used, it's just a stub. Pls refer
  to README in this repo for usage."** Workaround `uv pip install -e path/to/coreai-models/python/ --no-deps`.
- **#28** — tool calling *is* supported now (@carinapeng: *"We added tool calling recently after initial
  release"*). See PR #9 below.
- **#43** — sampler feature matrix gap, verbatim: the **CPU/Accelerate `CompositeSampler`** supports TopK, TopP,
  Temperature (+ fast Greedy / Temperature=0); the **MPSGraph counterpart used in the pipelined engine**
  originally supported only TopK + Temperature. *"We should be able to implement TopP, however that requires a
  scatter operation."* Missing: repetition penalty, MinP. → Closed by PR #48 which added TopP + MinP to both.
- **#46** — self-reported race: *"with pipeline depth 3, and CPU being unable to catch up … This would show up
  as **repeated tokens** as the sampler output would not be updated in time."* → PR #53.
- **#82** — Qwen3-VL exported CLIP normalization stats; checkpoints specify `image_mean = image_std =
  [0.5,0.5,0.5]`. PR #105: *"caused a silent ~1.86x overscale on every pixel fed to the vision encoder."*
- **#86** — build break: missing `await` after `generate()` became async (PR #87). ToT main was broken.
- **#20 / #56 / #116 / #59 / #14 / #7 / #1** — model requests. #20 (Gemma 4 E4B iOS) has a community port at
  15.1 tok/s decode / 21.3 tok/s prefill on iPhone 17 Pro, ~2.2 GB footprint, *"AOT compile is mandatory on
  iPhone at this size."*
- **#116** — extremely detailed community A/B: W8/static-KV/ANE vs INT4/dynamic-KV/GPU for Qwen3-1.7B.
  Compiled bundle 1714.4 MiB vs 924.6 MiB; peak RSS 2865.0 vs 1995.3 MiB; 3790-in/10-out **6.116 s (ANE) vs
  13.717 s (GPU)**; 120-in/256-out **13.292 s (ANE) vs 7.159 s (GPU)**. Verbatim conclusion: *"INT4/GPU
  substantially reduces install size and memory pressure and is faster for sustained decoding. W8/ANE has much
  faster time to first token and long-prompt prefill."* Also a runtime gotcha: Qwen3 no-thinking mode must be
  applied at chat-template time via `additionalContext: ["enable_thinking": false]` —
  *"Appending `/no_think` to the prompt was not equivalent."*
- **#44** — an automated "Code Audit" bot issue (19 findings), CLOSED. Most findings are the same class:
  `torch.autocast(device_type="cpu", dtype=torch.float16)` in `models/{clap,efficient-sam,pvt,t5,wav2vec2,
  sam3}/export.py` — **CPU autocast only supports bfloat16**; and `reference_inputs` casting `input_ids` /
  `attention_mask` to `torch.int32` in `models/{clap,clip,roberta,sam3,t5}/export.py`. Treat as
  bot-generated/low-confidence, but the CPU-autocast-fp16 point is a genuine PyTorch constraint.

### coreai-models PRs — behaviors a guide must know

| PR | Substance |
|---|---|
| **#121** `[Temporary Workaround] Fix pipelined sampling corruption: use per-call execution descriptor` (MERGED) | "The `MPSGraphCompositeSampler` reused a single **`MPSGraphExecutableExecutionDescriptor`** across all pipelined steps. Under pipelined execution (depth > 1), **overlapping `runAsync` calls on the same executable corrupt intermediate scratch buffers when sharing a descriptor**, producing garbled output (word repetitions, doubled punctuation) with temperature > 0." Fix: fresh descriptor per `encode()`. |
| **#117** `Fix guided generation: include <\|endoftext\|> as stop token` (MERGED) | "Qwen3 models declare `eos_token` as `<\|im_end\|>` (151645) but the grammar (**xgrammar**) can also produce `<\|endoftext\|>` (151643) as a valid terminal. Since 151643 wasn't in the stop sequences, it passed through to the output as literal text, corrupting structured generation." Adds `endoftext` to `turnEndPatterns` alongside `im_end`, `end_of_turn`, `eot_id` (read from `added_tokens_decoder`). |
| **#113** `Stop pipelined generation when consumer drops the stream` (MERGED) | `outputContinuation.onTermination` finishes the inner stream so cancellation propagates; **cancel any prior active generation at the start of `generate()` on all engine types** (sequential, static-shape, VLM) — "cancel-and-replace contract". |
| **#110** | Diffusion GPU memory leak (see #77 above). Also "wraps model loading and inference in do/catch to surface actionable errors instead of crashing on GPU memory exhaustion." |
| **#108** `Add configurable VLM image preprocessing strategy` (MERGED) | Three strategies: **`stretch`** (default, backward compatible), **`center_crop`** (shortest-edge resize then center crop, for CLIP-based models), **`pad`** (longest-edge resize with zero-padding, preserves geometry). Declared in `metadata.json`, inferred at export, overridable via `--image-strategy`. Also `--image-info` to inject original image dimensions into the text prompt. |
| **#103** | SD text-encoder seq-len (see #102). |
| **#101** `Add support for memory efficient iOS exports for large models` (OPEN) | "**mmap-backed palettization and exports**" for iOS, matching macOS. Touches `export/compression.py`, `models/ios/{mistral,qwen2,qwen3}.py`. |
| **#99** `Enable running iOS and macOS authored models on CUDA GPUs` (MERGED) | "**`SDPA` in `iOS` uses Flash Attention** for memory efficient and faster runs"; exposes **`disable_embedding_quantization`** as an arg "so that FP16 runs don't implicitly quantize embedding to INT8 for iOS models"; multi-GPU via `accelerate`. |
| **#97** `VLM support for FoundationModels protocol` (MERGED) | New `CoreAIVisionLanguageModel: LanguageModel` + `CoreAIVLMExecutor: LanguageModelExecutor`. Declares the **`.vision` capability**. Usage: `let model = try await CoreAIVisionLanguageModel(resourcesAt: bundleURL); let session = LanguageModelSession(model: model); let response = try await session.respond(options: GenerationOptions(maximumResponseTokens: 256)) { Attachment(cgImage); "What is in this image?" }`. **"An image attachment is required; a text-only prompt throws `unsupportedTranscriptContent`."** |
| **#91** `Lazy runner design: defer engine load` (MERGED) | New **`ModelResources`** type owning engine load/unload; **`LoadMode { .lazy, .eager }` (default `.lazy`)**; `load()` / `unload()` / `estimatedSizeOnDiskBytes`; `isGuidedGenerationSupported` gating that works before the engine is resident; **"reasoning models default to a higher max-token budget"**; `prewarm` now non-blocking background load. New `URL.recursiveFileSizeInBytes()`. |
| **#85** `Avoid copying embedding table in static shape runner` (OPEN, **do not merge**) | "if we don't use the pre-allocated output view flow, it'll return an `NDArray` backed by the constant directly without making a copy." Author flagged a perf regression. |
| **#81** `Default max-context-length of 4096 for LLM iOS platform exports` (MERGED) | Plus "check to ensure that the max context length in the `ExportConfig` is less than or equal to that of the HF config". |
| **#79** VLM fixes (MERGED) | `EmbeddedInput.tokenCount` was returning `hidden_dim` instead of `seq_len` for 2D `[seq_len, hidden_dim]`; `scatterMerge` `precondition(float16)` replaced with a thrown error for bfloat16; **"sequential `PreparedModel.prepare` (parallel caused runtime errors)"**. |
| **#74** (MERGED) | Use **`NDArrayDescriptor.resolvingDynamicDimensions(_:)`** instead of mutating `NDArrayDescriptor.shape` directly — "will check for validity of swapped shaped". |
| **#69** `[Qwen3-MoE] Optimize expert selection` (MERGED) | Simplify when `norm_topk_prob` is set. Prompt 1066.4 → 1103.7 tok/s; Generation **62.1 → 69.2 tok/s**. |
| **#65** `Add VLM inference infrastructure` (MERGED) | `MultimodalInferenceEngine` protocol with `encodeImage()` + `generate()`; `CoreAISequentialVLMEngine` (vision encoder + projector + embed_tokens + LLM decoder with **scatter-merge of image embeddings at placeholder positions**); `EmbeddedInput`; `VisionConfig` in `LanguageConfig` (image_size, patch_size, token count/id). **"Supports any VLM that exports 3 components (`vision.aimodel`, `embed.aimodel`, `model.aimodel`) with a vision config block in `metadata.json`."** |
| **#64** `Enable multi-turn KV cache reuse` (MERGED, +0/−3) | Removes the unconditional `engine.reset()`; implicit prefix caching (`TokenHistory.resolve`) handles reuse/divergence/full-reprocess. Qwen3 0.6B on M2 Max: prompt 2 **3.0 s → 2.4 s (~20%)**. Verify with **`engine.lastPrefixHitCount > 0`**. |
| **#62** (MERGED) | 64-byte minimum MPSNDArray buffer size (fixes #61). |
| **#53** `Fix pipeline race condition: rotate all buffers by pipeline depth` (MERGED) | "With pipeline depth 3, the GPU sampler output and logits buffers were shared across in-flight stages, causing **stale reads (repeated tokens)** under CPU contention." Introduces a shared `pipelineDepth` constant and rotates `decodeOutputBuffers`, `decodeLogitsBuffers`, `cachePositionBuffers`. |
| **#51** `Add reset(to:), processedTokenCount, and implicit prefix caching` (MERGED) | `InferenceEngine` gains `reset(to: tokenIndex)` (truncate KV cache to first N), `processedTokenCount`; `TokenHistory` does **memcmp-based prefix detection**. Pipelined = implicit prefix caching; Sequential/Static = implicit rewind ("full divergence triggers zero-fill, prefix extension rewinds counter"). |
| **#48** `Add TopP and MinP sampling to all engines` (MERGED) | `MPSGraphTopKSampler` → **`MPSGraphCompositeSampler`** with TopP + MinP "via exclusive cumsum and relative probability mask"; `minP` added to `SamplingConfiguration`; **"use K=1000 window when only topP/minP is specified"**; `--min-p` CLI flag. |
| **#47** `Fix pipelined engine reset(): cancel before drain` (MERGED) | See #41. |
| **#36** `Fix Gemma stop tokens: read additional EOS from tokenizer config` (MERGED) | *"The root cause is **upstream not exposing the required fields**, and eventually we should try to have them fix this at the origin. However we can also manually read the tokenizer additional information."* Field name in code: `additionalEosTokenIds`. |
| **#34** `Fix Whisper export to support autoregressive decoding` (MERGED) | "The existing export traced `decoder_input_ids` at length 1 with no dynamic shapes, producing a model specialised to a single token… giving empty transcript." Fix adds `dynamic_shapes` for `decoder_input_ids` and traces with the **4-token forced prefix**. |
| **#33** `Align diffusion bundles with metadata.json v0.2 schema` (MERGED) | Diffusion exports now emit `metadata.json` (v0.2, same as LLM/segmenter) instead of legacy `pipeline.json`; pipeline config under a `"diffusion"` key alongside `kind`, `name`, `assets`, `source`, `compression`, `compilation`. Swift runner prints a **deprecation error** if only `pipeline.json` is found. |
| **#24** (MERGED, +1034/−507) | "Use custom AsyncSequences and avoid unstructured concurrency". |
| **#22** (MERGED) | Update to **Swift 6.2**. |
| **#16** `Add InferenceStream with StopReason` (MERGED) | `InferenceStream` — final class, `AsyncSequence`, `Sendable` — replaces opaque `some AsyncSequence<InferenceOutput, Error>`. Nested **`StopReason enum (.maxTokens, .eos, .stopSequence, .cancelled, .error)`**. Engines set `.maxTokens`/`.cancelled`/`.error`; decoders set `.eos`. Removes `associatedtype OutputSequence` from `InferenceEngine`. |
| **#9** `Tool calling support` (MERGED) | New **`ToolCallParser.swift`** — "streaming state machine that splits the token stream at configurable open/close markers. Emits `.text` or `.toolCall(id:name:argsJSON:)`". Handles **Qwen3 `<tool_call>…</tool_call>` tag pairs and Mistral `[TOOL_CALLS] [{...}]` single-line arrays**. Pipeline order: `ThinkTagParser` → `ToolCallParser` → channel. **"`capabilities` is now tokenizer-aware: `.toolCalling` and `.reasoning` are only advertised when the tokenizer's vocabulary contains the corresponding special tokens."** `transcriptToTokens` handles `.toolCalls` / `.toolOutput` transcript entries for multi-turn. |
| **#123** | "Move away from deprecated FM API" (in `CoreAILanguageModel.swift`, `CoreAIVisionLanguageModel.swift`). **UNVERIFIED which API was deprecated.** |
| **#106** | "WWDC 2026: SAM3 iOS Model". |

---

## 5. Cross-cutting patterns for guide writers

### 5.1 The "silent miscompile" family (highest-value guide content)
All of these produce **plausible output with the correct shape and no diagnostic**:
1. `optimize()` dropping broadcast-significant axis moves (torch#49) — 17 dB PSNR
2. float→int→float cast round-trip fold (torch#9) — identity instead of floor
3. GPU floor/trunc/ceil as identity, round ties-away (torch#10)
4. int-comparison bool mask chain clobbering a live tensor (torch#11) — cosine ~0.65
5. `min.dim` indices wrong at dtype extremes (torch PR#43)
6. int64→int32 accumulator narrowing in sum/prod (torch PR#45, **still unfixed**)
7. `cat` on packed intx tensors always using dim 0 (torch PR#41, **still open**)
8. quantize/dequantize negative-axis off-by-one (torch PR#24)
9. integer true-divide truncating (torch PR#32, **still open**)
10. transposed-conv `output_padding` adding `stride` instead (torch PR#40)
11. partial-rotary RoPE contiguous vs half-split pairing (models#66) — 21.6 dB
12. Qwen3-VL CLIP normalization ~1.86× overscale (models#82)
13. Gemma4 E-series PLE identity using image_token_id (models#83) — cosine 0.347
14. Pipelined sampler descriptor reuse → repeated words (models PR#121)
15. Pipeline-depth buffer aliasing → repeated tokens (models#46 / PR#53)
16. `ChannelStructured(axis=-1)` pruning wrong channels (opt PR#45)
17. Tied-weight dtype/schedule split in graph mode QAT (opt#41)

**Recommended standard gate for any guide:** run every converted model through
(a) eager-vs-Core-AI numerics, (b) `optimize=True` vs `optimize=False`, (c) CPU vs GPU vs ANE, and
(d) a token-exact greedy oracle for LLMs. Every one of the above was found by one of those four A/Bs.

### 5.2 Compute-unit selection recipe (assembled from repros)
```python
import coreai.runtime as rt
rt.SpecializationOptions.cpu_only()
rt.SpecializationOptions.from_preferred_compute_unit_kind(rt.ComputeUnitKind.gpu())
rt.SpecializationOptions.from_preferred_compute_unit_kind(rt.ComputeUnitKind.neural_engine())
m = await rt.AIModel.load(path, opts)                 # positional
m = await rt.AIModel.load(path, specialization_options=opts)   # keyword
fn = m.load_function("main")           # or m.load_function(m.function_names[0])
res = await fn({"x": rt.NDArray(np_arr)})              # stateless
res = await fn(inputs={...}, state={...})              # stateful
```
`AIModelAssetMetadata()` is an optional second positional to `prog.save_asset(path, metadata)`.

### 5.3 `coreai-build` CLI surface observed
```bash
xcrun coreai-build compile <asset>.aimodel \
  --platform {iOS,macOS} \
  --architecture {h16g,h16p,h16s,h18p} \
  --preferred-compute {gpu,neural-engine} \
  [--expect-frequent-reshapes] \
  --output|-o <path>
xcrun coreai-build inspect <asset>.aimodel   # prints function signatures, inputs/outputs, states, weight ops/dtypes
xcrun coreai-build package <asset>           # re-emits asset, updates producer stamp; does NOT rewrite IR locations
```
Compiled output is `.aimodelc`; ANE participation is visible as `*_ANE_region_*` segments in the compiled model.

### 5.4 Python export CLI surface observed
```bash
uv run coreai.llm.export Qwen/Qwen3-0.6B
uv run coreai.llm.export Qwen/Qwen3-0.6B --compression none
uv run coreai.llm.export qwen3-0.6b --platform iOS \
   --compression 4bit_weight_palettized_group32 --output-name <name>
uv run coreai.diffusion.export flux2-klein-4b --platform iOS --overwrite
```
Known coupling error: `--platform iOS --compression 4bit` →
`RuntimeError: macOS quantization preset provided, but platform is iOS`.

### 5.5 Swift runner CLI surface observed
```bash
swift run -c release llm-runner --model <bundleDir> \
  --prompt "..." --max-tokens 24 \
  --sampling-strategy greedy --min-p <f> \
  --inference-engine-variant {coreai-pipelined,coreai-sequential} \
  [--synchronous-sampling] [--image <path>] [--image-strategy {stretch,center_crop,pad}] [--image-info]
swift run -c release llm-benchmark ...
speech-runner ...   # Whisper; `--mic` requested but declared "out of scope" (#107)
```
Env var seen repeatedly: **`COREAI_CHUNK_THRESHOLD=1`**.
Engine variant is also selectable in Swift: `CoreAILanguageModel.init(..., variant: "coreai-sequential")`.

### 5.6 Bundle layout / metadata facts
- A model **bundle is a directory** containing the `.aimodel`(s), tokenizer files, and `metadata.json`.
  Pointing at the `.aimodel` itself yields `unsupported metadata_version '0.1' (known: 0.2)` (models#58).
- `metadata.json` schema version is **0.2**; shared fields `kind`, `name`, `assets`, `source`, `compression`,
  `compilation`, plus per-kind blocks (`"diffusion"`, `"vision"`).
- VLM bundles: 3 components — `vision.aimodel`, `embed.aimodel`, `model.aimodel`.
- Flux2 iOS bundles: 4 components — `VAEEncoder_half`, `VAEDecoder_half`, `TextEncoder`, `Transformer_512`.
- Static iOS LLM exports contain ~34 functions: `extend_{256..4096}_{8,16,64}`, `prompt_opt_*`,
  `gather_embeddings_*`, `load_embeddings`.
- Weight op names in the IR: `lut_to_dense` (palettized) vs `blockwise_shift_scale` (linear blockwise int).
- Xcode: model folders must be added with **"Apply once to folder"** (File Inspector) so they copy as one bundle.

### 5.7 Known-good / known-bad shape policies for LLM export
| Query | Context | Consequence |
|---|---|---|
| dynamic | dynamic (shared symbol) | shipped models; works |
| **static** | dynamic | SDPA externalize re-export fails (torch#1); 2+ GatedDeltaUpdate layers crash MPSGraph (torch#2) |
| static | static, **runtime-value** slice_update begin/end | ANECompiler `addOpToNetwork` EXC_BAD_ACCESS at load (torch#6); MPSGraph SIGTRAP (models#5) — **maintainer says fixed in beta 4** |
| static | static, **constant** slice_update begin/end | works — the sliding-window workaround |
| dynamic monolithic stateful | prefill chunk >16 | nondeterministic (models#84, not reproduced by Apple) |
| iOS pipelined, KV state bound at seq ≥2048 | — | corrupt from token 1 (models#124) |

---

## 6. Source inventory (everything actually read this session)

**Tooling:** `gh issue list/view`, `gh pr list/view`, `gh release list/view`, `gh repo view`, `gh search issues`.

### apple/coreai-torch
- Repo README (via `gh repo view`)
- Releases: `v0.4.1` (full body, incl. embedded `coreai-core v1.0.0b2` notes)
- Issues (full body + all comments): **#1, #2, #3, #5, #6, #8, #9, #10, #11, #21, #33, #37, #44, #51**
- Issues (title/state/comment-count triage only): #4, #20, #49 (#49 read in full)
- Issue **#49** read in full (body; 0 comments)
- PRs (full body + comments): **#7, #12, #13, #18, #22, #24, #29, #32, #35, #36, #39, #40, #41, #43, #45, #46, #50**
- PR triage list (all 35 PRs, titles/states/dates)

### apple/coreai-optimization
- Repo README (via `gh repo view`)
- Releases: `v0.2.0` (full, incl. Known Issues), `v0.2.1` (full)
- Issues (full body + comments): **#7, #16, #41** (that is all 3 issues in the repo)
- PRs (full body + comments): **#1, #2, #3, #5, #15, #19, #22, #25, #32, #34, #39, #40, #42, #44, #45, #48, #50, #52, #54, #56**
- PR triage list (all 57 PRs)

### apple/coreai-models
- Repo README (via `gh repo view`)
- Release: `0.2.0` (full)
- Issues (full body + comments): **#5, #12, #20, #27, #28, #41, #43, #44 (partial — long bot report), #46, #49, #55, #56, #58, #61, #66, #77, #83, #84, #96, #100/#102, #107, #111, #112, #116, #118, #119, #124**
- PRs (full body + comments): **#9, #16, #24, #33, #34, #36, #47, #48, #51, #53, #62, #64, #65, #69, #74, #79, #80, #81, #85, #87, #91, #97, #99, #101, #103, #105, #108, #110, #113, #117, #120, #121, #122, #123**
- Issue + PR triage lists (all 55 issues, all 74 PRs)

External URLs *referenced by* these threads but **not fetched** in this session (so unverified):
coremltools PRs #2725/#2726/#2727 and issue #2687; arXiv:2603.06728 ("the Orion paper");
`github.com/massif-01/coreai-hybrid-state-runtime`; `github.com/john-rocky/coreai-model-zoo`;
`huggingface.co/ukint-vs/Nanbeige4.2-3B-CoreAI`; `huggingface.co/mlboydaisuke/*`;
`github.com/RedHillsMediaFL/caix`; `apple.github.io/corai-optimization`.

---

## 7. Open questions / unverified

1. **`AIProgram.optimize()` signature and pass list.** Only two pass names are attested (`legalize-to-core`,
   `core-to-odix`, from torch#33) plus the driver `apply_passes_sync`. Whether `optimize()` takes arguments
   (pass selection, opt level) is **UNVERIFIED** — I never read the source.
2. **`strip_debug_info` return value.** The maintainer's snippet calls it as a statement and says it "modifies
   the program in place", but also shows `coreai_program = asset.program` first. Whether it returns a new
   program is **UNVERIFIED**.
3. **Does coreai-torch#8 (arange abort) still need closing?** Contributor says fixed on main since #13/53d6bdd,
   issue is still OPEN. Unclear whether 0.4.1 shipped the fix (PRs #25/#27 landed 2026-06-29, before the
   0.4.1 publish on 2026-07-06 — **likely yes, INFERRED**).
4. **Whether coreai-models#5 / #55 / #27 are actually fixed in macOS/Xcode beta 4.** Maintainer asked the
   reporter to verify; no confirmation in the thread as of 2026-07-27.
5. **coreai-models#84** (prefill >16 nondeterminism) — Apple **could not reproduce**. Root cause unknown;
   reporter never posted the requested hardware/software details in-thread.
6. **coreai-models#124** — no root cause yet; maintainer's three triage questions unanswered in-thread.
7. **Exact `_COMPOSITE_OPS` contents at v0.4.1.** The 6-op list (`hardsigmoid`, `hardswish`, `instance_norm`,
   `pixel_shuffle`, `scaled_dot_product_attention`, `silu`) is quoted from issue #21 dated 2026-06-21 against
   a June clone; PR #29 (pad) and PR #34 (RNN, unmerged) may have changed it. **Verify against source.**
8. **`coreai_torch.composite_ops` full inventory.** Only `GatedDeltaUpdate` and `RoPE` are attested here.
9. **`ComputeUnitKind`** — `.gpu()`, `.neural_engine()` attested; a `.cpu()` factory is **UNVERIFIED**
   (`SpecializationOptions.cpu_only()` is the attested CPU path).
10. **Which FoundationModels API PR #123 deprecates.** Body was empty.
11. **`coreai-models` PyPI package** — maintainer says the published wheel "is just a stub". So the Python
    package must be used from a source checkout. Whether that changed after 0.2.0 is **UNVERIFIED**.
12. **`AIModelError error 3` enum meaning.** Surfaces as `invalidCompiledModel` at the `LanguageBundle` layer,
    but the raw enum table was not read.
13. **`--experimental` flag** for model presets (mentioned in models#116) — CLI surface **UNVERIFIED**.
14. **Whether `coreai-torch` PRs #22 (stable fp16 ops), #32 (true-divide), #41 (intx cat), #45 (int64
    accumulator) will land.** All open/closed-unmerged as of 2026-07-27; guides should treat all four bugs as
    LIVE on 0.4.1.
