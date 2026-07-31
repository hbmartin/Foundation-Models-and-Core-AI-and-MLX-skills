# lucasnewman/mlx2coreai — deep dive

Research notes. Everything here was read from the local clone at
`/Volumes/ExtStor/FM and MLX and CoreAI/repos/lucasnewman__mlx2coreai`
(git remote `https://github.com/lucasnewman/mlx2coreai`, branch `main`, HEAD `059c9f3`),
plus cross-verification against sibling clones of `ml-explore/mlx` and `apple/coreai-models`.
Line numbers refer to the files as they exist at HEAD.

**One-line summary:** `mlx2coreai` is the *bridge* between the MLX half and the Core AI half of
Apple's 2026 stack. It captures an MLX function/module with MLX's **export callback** tracer,
parses the event stream into a tiny SSA graph IR, normalizes + shape-infers it, and emits **Core AI
MLIR** (`coreai.GraphOp` inside a `coreai.authoring.AIProgram`) which it saves as a `.aimodel`
asset. It has a dedicated stateful path that reproduces the *exact* `coreai-models` macOS LLM
contract (`input_ids` / `position_ids` + mutable `keyCache`/`valueCache`).

---

## 0. Repo metadata

| Fact | Value | Source |
| --- | --- | --- |
| Package name / version | `mlx2coreai` `0.1.1` | `pyproject.toml:6-7` |
| License | MIT, "Copyright (c) 2026 Lucas Newman" | `LICENSE:1-3` |
| Author | Lucas Newman `<lucasnewman@me.com>` | `pyproject.toml:12-14` |
| Python floor | `requires-python = ">=3.11"` | `pyproject.toml:10` |
| Total source | 33 files, ~12.1k lines (py+md+swift+toml) | `wc -l` |
| Commits | 11 total (`cc9558e` … `059c9f3`), all June 2026 | `git log --oneline -50` |

Full commit list (newest first, all authored by Lucas Newman):

```
059c9f3 Add a swift runner as python bindings are incomplete as of now.   (Tue Jun  9 06:43:06 2026 -0700)
d032a95 Cleaner conversion API.                                          (Mon Jun  8 21:37:42 2026 -0700)
2359323 Merge remote-tracking branch 'origin/main' into kv-cache
948a3bd Checkpoint.                                                      (Mon Jun  8 21:30:31 2026 -0700)
bbadb88 Fix command and code examples in README.md
f6b0b4c Update README
a441487 Add installation notes.
5e9c7de Allow optimization on SDPA for macOS 27.                          (Mon Jun  8 16:04:34 2026 -0700)
dab7096 Fix runtime on macOS 27.                                         (Mon Jun  8 15:57:14 2026 -0700)
94bd2b9 Update project.
cc9558e Initial commit.
```

`.gitignore` (note the asset patterns and the Swift build dir):

```
.DS_Store
__pycache__/
*.py[cod]
.pytest_cache/
.build/
*.aimodel/
*.aimodels/
```

### Dependencies (`pyproject.toml:21-37`)

```toml
dependencies = [
    "coreai-core==1.0.0b1",
    "ml-dtypes",
    "mlx",
    "mlx-lm",
    "numpy",
]

[project.optional-dependencies]
test = ["pytest"]

[project.scripts]
mlx2coreai = "mlx2coreai.cli:main"
mlx2coreai-convert-mlx-lm = "mlx2coreai._convert_mlx_lm:main"
mlx2coreai-convert-mlx-lm-stateful = "mlx2coreai._convert_mlx_lm_stateful:main"
```

**Hard pin:** `coreai-core==1.0.0b1` — the beta Core AI Python wheel. Everything in
`lower_to_coreai.py` is written against that exact beta; several workarounds in the code are
explicitly labelled "beta asset writer" bugs (see Gotchas).

`ml-dtypes` is a required dependency purely to carry **bfloat16** through numpy
(`ml_dtypes.bfloat16` is used as a numpy dtype in capture, lowering, and comparison).

`pytest` config (`pyproject.toml:45-50`): `testpaths = ["tests"]`, `addopts = ["--tb=short"]`.

---

## 1. Pipeline architecture

```
MLX callable / nn.Module
        │
        │  mx.export_function(callback, fn, shapeless=?, **mx_inputs)   ← from_mlx.py
        ▼
  list[dict] "events"  (inputs / keyword_inputs / outputs / constants / primitive …)
        │  parse_mlx_export_events_to_graph()
        ▼
   Graph  (ir.py: TensorSpec / Node / StateSpec, plain SSA, string tensor names)
        │  optional: dynamicize_graph_from_probe()  ← second capture at a nearby shape
        │  normalize_graph()      (op-name canon, name sanitize, const canon, SDPA masks, identity DCE)
        │  infer_graph_specs()    (shape+dtype inference used by lowering fallbacks)
        │  ensure_supported()     (raises UnsupportedOpsError with a per-op backlog report)
        ▼
   CoreAILowerer.lower_many()  → coreai.GraphOp per entrypoint inside one mlir Module
        │  AIProgram._from_mlir_module(module); program.optimize()
        ▼
   program.save_asset(path)  →  <name>.aimodel/{main.mlirb, main.hash, metadata.json}
        │
        └─ stateful path also writes:  bundle/{metadata.json, tokenizer/, <name>.aimodel}
```

Module map:

| File | Lines | Role |
| --- | ---: | --- |
| `mlx2coreai/__init__.py` | 92 | Public exports + lazy-import shim for the mlx-lm converters |
| `mlx2coreai/ir.py` | 113 | `TensorSpec`, `StateSpec`, `Node`, `Graph`, dynamic-dim refs |
| `mlx2coreai/from_mlx.py` | 1303 | MLX capture (callback + DOT modes), primitive-arg → attr extraction, IR replay |
| `mlx2coreai/passes.py` | 1032 | Normalization passes + shape/dtype inference |
| `mlx2coreai/op_registry.py` | 543 | MLX-name → lowering-key map, DOT-label aliases, unsupported-op reporting |
| `mlx2coreai/lower_to_coreai.py` | 2072 | The Core AI MLIR emitter (the heart) |
| `mlx2coreai/conversion.py` | 304 | `ConversionConfig` + `capture/prepare/lower/convert` orchestration |
| `mlx2coreai/dynamic_shapes.py` | 151 | Probe-based dynamic-axis inference |
| `mlx2coreai/_composite_declaration.py` | 202 | **Vendored Apple file** — builds `#coreai.composite_declaration<…>` attrs |
| `mlx2coreai/_convert_mlx_lm.py` | 341 | Stateless mlx-lm → single `.aimodel` |
| `mlx2coreai/_convert_mlx_lm_stateful.py` | 881 | Stateful KV-cache LLM → coreai-models-style bundle |
| `mlx2coreai/runtime.py` | 556 | Async/sync `.aimodel` execution + numeric validation |
| `mlx2coreai/op_coverage.py` | 310 | Coverage report generator (`docs/op_coverage.md/.json`) |
| `mlx2coreai/reporting.py` | 77 | Version collection + stage timing helpers |
| `mlx2coreai/cli.py` | 208 | argparse CLI |
| `scripts/benchmark_aimodel_sampling.py` | 531 | Decode-throughput benchmark, Python **and** Swift backends |
| `scripts/benchmark_aimodel_sampling_coreai.swift` | 351 | Native Swift CoreAI runner |

`_composite_declaration.py:1-4` carries an Apple header:

```python
# Copyright 2026 Apple Inc.
#
# Use of this source code is governed by a BSD-3-clause license that can
# be found in the LICENSE file or at https://opensource.org/licenses/BSD-3-Clause
```

i.e. it is copied out of Apple's Core AI Python tooling into this MIT repo.

---

## 2. Public API surface (`mlx2coreai/__init__.py`)

`__all__` (lines 44-78), exactly:

```
CapturedMLXGraph, ConversionConfig, ConvertedCoreAIModel, CoreAIOutputComparison,
CoreAIRuntimeOutputs, CoreAIRuntimeUnavailableError, CoreAIValidationResult, Graph,
MLXLMConversionInputs, MLXLMStatefulConversion, Node, PreparedMLXGraph, StateSpec, TensorSpec,
build_mlx_lm_inputs, capture_mlx_graph, compare_coreai_outputs, convert_mlx_lm,
convert_mlx_lm_stateful, convert_mlx_to_coreai, coreai_runtime_available, lower_graph_to_coreai,
prepare_mlx_conversion, run_aimodel, run_aimodel_sync, run_converted_model,
run_converted_model_sync, run_coreai_program, run_coreai_program_sync, validate_aimodel_outputs,
validate_aimodel_outputs_sync, validate_converted_model, validate_converted_model_sync
```

The mlx-lm converters are **lazily** imported through a module `__getattr__`
(`__init__.py:36-42, 81-92`) so that importing `mlx2coreai` does not pull in `mlx_lm`:

```python
_LAZY_EXPORTS = {
    "MLXLMConversionInputs": "MLXLMConversionInputs",
    "MLXLMStatefulConversion": ("._convert_mlx_lm_stateful", "MLXLMStatefulConversion"),
    "build_mlx_lm_inputs": "build_mlx_lm_inputs",
    "convert_mlx_lm": "convert_mlx_lm",
    "convert_mlx_lm_stateful": ("._convert_mlx_lm_stateful", "convert_mlx_lm_stateful"),
}
```

### 2.1 `ConversionConfig` — every field and default (`conversion.py:23-37`)

```python
@dataclass(slots=True)
class ConversionConfig:
    capture_mode: str = "callback"                          # "callback" | "dot"
    allow_unknown_sources: bool = True
    capture_shapeless: bool = False                         # → mx.export_function(shapeless=)
    dynamic_axes: DynamicAxes | None = None                 # {input_name: [axis,...] | "all"}
    dynamic_probe_inputs: Mapping[str, Any] | None = None
    capture_is_training: bool = False
    optimize: bool = True                                   # → AIProgram.optimize()
    entrypoint_name: str = "main"
    state_specs: list[StateSpec] | None = None
    externalize_weights: bool = True
    external_weight_threshold: int = 10                     # elements, not bytes; -1 = never
    min_runtime_target: str = "macOS27"                     # metadata only, not enforced
    constant_inputs: Mapping[str, Any] | None = None
```

Notes:
* `min_runtime_target` is **recorded into metadata only** (`conversion.py:253`); nothing validates it.
* `external_weight_threshold` counts **elements** (`arr.size`), not bytes
  (`lower_to_coreai.py:570-580`).
* `constant_inputs` is how you turn a captured graph input into a baked constant/dense-resource.

### 2.2 Result dataclasses

```python
@dataclass(slots=True)
class CapturedMLXGraph:            # conversion.py:40-45
    graph: Graph
    normalized_inputs: dict[str, np.ndarray]
    expected_outputs: dict[str, np.ndarray]

@dataclass(slots=True)
class PreparedMLXGraph:            # conversion.py:47-67
    captured: CapturedMLXGraph
    normalized_graph: Graph
    expected_outputs: dict[str, np.ndarray]
    inference_summary: dict[str, int]          # {"total_tensors","with_shape","with_dtype"}
    unsupported_details: list[dict[str, Any]]
    extra_input_names: list[str]               # graph inputs that were NOT user-supplied (= weights)
    # properties: .graph, .normalized_inputs, .weights_captured_as_constants

@dataclass(slots=True)
class ConvertedCoreAIModel:        # conversion.py:69-83
    prepared: PreparedMLXGraph
    lowered: LoweredCoreAIProgram
    asset: Any | None              # whatever program.save_asset() returned
    asset_path: Path | None
    metadata: dict[str, Any] = field(default_factory=dict)
    # properties: .program, .weight_manifest
```

`metadata` produced by `convert_mlx_to_coreai` (`conversion.py:251-264`) has exactly these keys:
`entrypoint_name, min_runtime_target, capture_shapeless, dynamic_axes, optimized,
optimization_skip_reason, externalize_weights, external_weight_threshold, extra_input_names,
unresolved_extra_inputs, weight_manifest, inference_summary`.

### 2.3 Entry-point functions

```python
capture_mlx_graph(target, inputs, *, dot_output_path=None, capture_mode="callback",
                  capture_shapeless=False, allow_unknown_sources=True,
                  capture_is_training=False, capture_function=None) -> CapturedMLXGraph

prepare_mlx_conversion(target, inputs, *, config=None, dot_output_path=None,
                       capture_function=None) -> PreparedMLXGraph

lower_graph_to_coreai(graph, *, config=None, public_input_names=None) -> LoweredCoreAIProgram

convert_mlx_to_coreai(target, inputs, *, config=None, output_path=None,
                      dot_output_path=None, capture_function=None) -> ConvertedCoreAIModel
```

`target` must be callable unless `capture_function` is given
(`_resolve_capture_components`, `conversion.py:296-304`); for `nn.Module`s you pass the module as
`target` (so `.train()/.eval()` toggling works) and a closure as `capture_function`.

`temporary_capture_training_mode` (`conversion.py:86-109`) flips `.train()` during capture when
`capture_is_training=True` and restores the prior `.training` flag afterwards.

### 2.4 Minimal working example (verbatim from `README.md:40-64`)

```python
import mlx.core as mx
import numpy as np

from mlx2coreai import ConversionConfig, convert_mlx_to_coreai


def model(x, w):
    return mx.tanh(mx.matmul(x, w))


converted = convert_mlx_to_coreai(
    model,
    {
        "x": np.ones((2, 3), dtype=np.float32),
        "w": np.ones((3, 4), dtype=np.float32),
    },
    config=ConversionConfig(optimize=True),
    output_path="model.aimodel",
)

print(converted.asset_path)
```

---

## 3. CLI reference

Console script `mlx2coreai` → `mlx2coreai.cli:main`; also runnable as `python -m mlx2coreai`
(`__main__.py`). Four subcommands.

### 3.1 `mlx2coreai inspect <path>`
Lists the children of a saved `.aimodel` directory (`cli.py:116-122`). That's all it does — it is
**not** an MLIR dumper.

### 3.2 `mlx2coreai ops`
Generates the op-coverage report.

| Flag | Type | Default |
| --- | --- | --- |
| `--output` | Path | `docs/op_coverage.md` |
| `--json-output` | Path | `docs/op_coverage.json` |
| `--model-zoo-module` | str | `tests.model_zoo` |
| `--validate-assets` | flag | off — when on, actually lowers + saves every zoo graph |

Equivalent module form: `python -m mlx2coreai.op_coverage --validate-assets`.

### 3.3 `mlx2coreai convert-mlx-lm <model_id>` (stateless)

| Flag | Type | Default | Notes |
| --- | --- | --- | --- |
| `--output` | Path | **required** | `.aimodel` directory |
| `--prompt` | str | None | tokenized to build capture `input_ids` |
| `--sequence-length` / `--seq-len` | int | None | "Defaults to the prompt token length, or 1 for synthesized inputs." |
| `--batch-size` | int | 1 | |
| `--revision` | str | None | passed to `mlx_lm.load(revision=)` |
| `--lazy-load` | flag | off | → `mlx_lm.load(lazy=True)` |
| `--dot-output` | Path | None | also dumps an MLX DOT graph for debugging |
| `--no-optimize` | flag | off | skips `AIProgram.optimize()` |
| `--dynamic-sequence` / `--no-dynamic-sequence` | BooleanOptionalAction | **True** | dynamic token axis via probe capture |
| `--externalize-weights` / `--no-externalize-weights` | BooleanOptionalAction | **True** | |
| `--external-weight-threshold` | int | 10 | "Use -1 to keep all constants inline." |
| `--capture-is-training` / `--no-…` | BooleanOptionalAction | False | |
| `--allow-unknown-sources` / `--no-…` | BooleanOptionalAction | True | |

Prints on success (`cli.py:160-167`):
```
Wrote <asset_path>
Nodes: <n>
Weights: <n> constants (<k> resource, <m> inline)
```

### 3.4 `mlx2coreai convert-mlx-lm-stateful <model_id>` (the LLM path)

Canonical invocation (`README.md:19-23`):

```bash
mlx2coreai convert-mlx-lm-stateful mlx-community/Qwen3-0.6B-bf16 \
  --output qwen \
  --max-context-length 256
```

| Flag | Type | Default |
| --- | --- | --- |
| `--output` | Path | **required**. "A .aimodel suffix is treated as the nested asset name." |
| `--max-context-length` | int | 256 |
| `--revision` | str | None |
| `--input-name` | str | `input_ids` |
| `--position-ids-name` | str | `position_ids` |
| `--key-cache-name` | str | `keyCache` |
| `--value-cache-name` | str | `valueCache` |
| `--compute-precision` | choice `auto\|fp32\|fp16\|bf16` | `auto` |
| `--cache-dtype` | choice `fp32\|fp16\|bf16` | None (follows compute precision) |
| `--entrypoint` | str | `main` |
| `--dynamic-sequence` / `--no-…` | BooleanOptionalAction | **True** |
| `--dynamic-state` / `--no-…` | BooleanOptionalAction | **True** |
| `--cast-bf16-logits-to-fp16` / `--no-…` | BooleanOptionalAction | **True** |
| `--externalize-weights` / `--no-…` | BooleanOptionalAction | True |
| `--external-weight-threshold` | int | 10 |
| `--capture-is-training` / `--no-…` | BooleanOptionalAction | False |
| `--allow-unknown-sources` / `--no-…` | BooleanOptionalAction | True |
| `--no-optimize` | flag | off |

Prints (`cli.py:194-200`): `Wrote bundle …`, `Asset: …`, `Entrypoints: …`, `States: …`,
`Compute precision: …`, `Cache dtype: …`, `Max context: …`.

**Note:** the standalone `mlx2coreai-convert-mlx-lm-stateful` console script
(`_convert_mlx_lm_stateful.parse_args`, lines 814-842) accepts the same flags but **omits
`--batch-size`**; the Python function accepts `batch_size` but raises for anything but 1
(see §7.1).

---

## 4. MLX capture layer (`from_mlx.py`)

### 4.1 Two capture modes

`capture_graph_from_mlx_function(dot_output_path, inputs, function, *, input_specs=None,
allow_unknown_sources=False, capture_mode="callback", shapeless=False)` — docstring
(`from_mlx.py:854-863`):

> `capture_mode` controls the source graph format:
> - `callback` (default): uses `mx.export_function(..., callback=...)` and preserves primitive
>   arguments needed for shape ops.
> - `dot`: preserves legacy `mx.export_to_dot` parsing behavior.

The callback capture (`from_mlx.py:754-808`) is 5 lines of real work:

```python
events: list[dict[str, Any]] = []

def _callback(payload: dict[str, Any]) -> None:
    events.append(payload)

mx.export_function(_callback, function, shapeless=bool(shapeless), **mx_inputs)
```

then it **runs the function a second time** (`outputs = function(**mx_inputs)`, line 781) to get
reference/"expected" numpy outputs used for later validation. So *the model is evaluated twice per
capture* (three times if a dynamic probe capture is also requested — see §6).

MLX imports are **always lazy** (`import mlx.core as mx  # noqa: PLC0415` inside functions) with
the recurring comment: *"MLX import is intentionally lazy to allow non-live operation in restricted
envs."*

### 4.2 The MLX callback event contract (verified against MLX C++ source)

`parse_mlx_export_events_to_graph` (`from_mlx.py:473-666`) consumes five event types. Verified
against `ml-explore__mlx/mlx/export.cpp:698-756` (`FunctionExporter::export_with_callback`):

```cpp
callback({{"type", "inputs"},         {"inputs",   to_vector_data(inputs)}});   // (name, shape, dtype)
callback({{"type", "keyword_inputs"}, {"keywords", keyword_inputs}});           // (kwarg_key, tensor_name)
callback({{"type", "outputs"},        {"outputs",  to_vector_data(outputs)}});
callback({{"type", "constants"},      {"constants", new_constants}});           // (name, array)
callback({{"type", "primitive"},
          {"inputs",  to_vector_data(arr.inputs())},
          {"outputs", to_vector_data(arr.outputs())},
          {"name", name},
          {"arguments", state}});
```

Confirmed by the MLX test `python/tests/test_export_import.py:501-537`, which asserts
`primitives == ["Subtract", "Abs", "Log", "AsType"]` and `primitive_args[2] == [2]`.

Key consequences mlx2coreai exploits:
* **Constants** (weights) arrive as an explicit `constants` event and become `const` nodes
  (`from_mlx.py:571-582`), i.e. **model weights are captured as graph constants, not inputs**, when
  MLX classifies them as tape constants.
* **Keyword names** let the parser rename MLX's internal tensor names back to your Python kwarg
  names (`alias_by_tensor_name`, `from_mlx.py:532-538`). MLX sorts kwargs into a `std::map` before
  appending them to the flat input list (`export.cpp:766-772`), which is exactly why the
  `keyword_inputs` event is needed at all.
* The primitive `name` is the **canonical MLX primitive class name after `name_remap`**, not the
  display name. `export.cpp:506-521` does `name = p->name(); name = name.substr(0, name.find(' '));`
  then applies `name_remap`, built from `SERIALIZE_PRIMITIVE(T, "alias", …)` keys
  (`export.cpp:454-459`). So e.g. `Sum/Prod/Min/Max/And/Or` all report as **`Reduce`**
  (`export.cpp:406`), and `BitwiseAnd/Or/Xor/LeftShift/RightShift` all report as
  **`BitwiseBinary`** (`export.cpp:340-346`), and `Log2/Log10` report as **`Log`**
  (`export.cpp:381`).
* `extract_state` drops `std::nullptr_t` entirely (`export.cpp:277-294` — nullptr matches no
  branch), so the leading `nullptr` in `Custom` primitive states (RoPE/SDPA/RMSNorm) is **not**
  emitted. mlx2coreai's `[arg for arg in arguments if arg is not None]` filters are defensive
  no-ops.

### 4.3 Primitive-state → attribute extraction

`_primitive_attrs_from_arguments(op, arguments, output_shape, output_dtype)`
(`from_mlx.py:113-308`) is the table that turns MLX primitive `state()` tuples into IR attrs.
The important rows, cross-checked against MLX headers:

| op (normalized) | MLX `state()` (verified) | attrs produced |
| --- | --- | --- |
| `reshape`/`flatten`/`unflatten`/`broadcast`/`broadcast_to` | — | `shape` = **the captured output shape** |
| `transpose` | `perm` | `perm` |
| `moveaxis` | `(src, dst)` | `source`, `destination` |
| `swapaxes` | `(a1, a2)` | `axis1`, `axis2` |
| `slice`/`slice_update` | `(begin, end, stride)` | `begin`, `end`, `stride` |
| `dynamic_slice_update` | `(axes,…)` | `axes` |
| `sum/mean/min/max/prod/all/any/var/std/logsumexp` | `(axes, keep_dims[, ddof])` | `axes`, `keep_dims`, `ddof` |
| `reduce` | `Reduce::state() = (reduce_type, axes)` — `mlx/primitives.h:1811-1813` | `mode` (int), `axes`, `keep_dims` **default True** |
| `argmax`/`argmin` | `ArgReduce::state() = (reduce_type, axis)` | `axis`, `keep_dims` |
| `take`/`take_along_axis` | `axis` | `axis` |
| `split` | `(indices\|num, axis)` | `split_indices` or `num_splits`, `axis` |
| `expanddims` | `axes` | `axes` |
| `gather` | `(axes, slice_sizes)` | `axis`, `slice_shape`, `shape` (= captured output shape) |
| `squeeze` | `axes` | `axes` |
| `concatenate` | `axis` | `axis` |
| `softmax` | `Softmax::state() = precise_` (bool only!) — `mlx/primitives.h:2171-2173` | `precise` (and *only* `axis` if a non-bool leads) |
| `rmsnorm` | `RMSNorm::state() = (nullptr, eps_)` | `eps` |
| `rope` | `RoPE::state() = (nullptr, dims_, traditional_, base_, scale_, forward_)` — `mlx/fast_primitives.h:194-197` | `dims`, `traditional`, `base`, `scale` |
| `astype`/`cast` | dtype | `dtype` = **the captured output dtype** |
| `bitwisebinary` | `BitwiseBinary::Op` enum int | `mode` |
| `scaled_dot_product_attention` | `(nullptr, scale_, do_causal_, has_sinks_, output_logsumexp_)` — `mlx/fast_primitives.h:251-254` | `scale`, `do_causal`, `has_sinks`, `output_logsumexp` |
| `convolution` | `(strides, pad_lo, pad_hi, dilations, ?, groups, transpose)` | `strides`, `padding` (**lo+hi summed!**), `pad_type="custom"`, `dilations`, `groups`, `transpose` |
| `arange` | `(start, end, step)` | `start`, `end`, `step` (all cast to **int**) |
| `linspace` | `(start, stop, num[, endpoint])` | `start`, `stop`, `num`, `endpoint` |

Verbatim comments worth quoting:

```python
# from_mlx.py:173-174
        # MLX callback Reduce currently emits rank-preserving reductions.
        attrs["keep_dims"] = bool(arguments[2]) if len(arguments) >= 3 else True

# from_mlx.py:222-223
    if op == "softmax" and arguments:
        # MLX export can emit [precise] when axis is defaulted to -1.

# from_mlx.py:254-256
    if op == "scaled_dot_product_attention" and arguments:
        # MLX fast primitive state is [scale, do_causal, has_sinks, output_logsumexp].
        # Some serializers may preserve placeholder nulls; filter them first.
```

The conv padding merge is a genuine semantic collapse (`from_mlx.py:275-280`):

```python
        if len(arguments) >= 3:
            pad_hi = _int_list(arguments[2])
            if pad_hi is not None:
                pad_lo = attrs.get("padding")
                if isinstance(pad_lo, list) and len(pad_lo) == len(pad_hi):
                    attrs["padding"] = [int(lo) + int(hi) for lo, hi in zip(pad_lo, pad_hi)]
```

i.e. asymmetric MLX padding `(lo, hi)` is folded into a single per-axis total and then re-split
symmetrically downstream — asymmetric padding is silently lost.

### 4.4 dtype mapping

`_numpy_dtype_to_ir` (`from_mlx.py:21-47`) — IR dtype strings are `"bf16" | "fp16" | "fp32" |
"int32" | "int64" | "bool"`. Any float wider than fp16 → `fp32`, so **fp64 collapses at capture
time**. `_mlx_dtype_to_ir` does the same from MLX dtype reprs.

`_constant_to_numpy` (`from_mlx.py:79-93`) has a bf16 workaround:

```python
    except Exception:
        # MLX bf16 arrays can fail direct numpy conversion via buffer protocol.
        if hasattr(value, "astype"):
            try:
                import mlx.core as mx
                if "bfloat16" in str(getattr(value, "dtype", "")).lower():
                    return np.asarray(value.astype(mx.float32)).astype(ml_dtypes.bfloat16)
                return np.asarray(value.astype(mx.float32))
```

### 4.5 The legacy DOT path

`parse_mlx_dot_to_graph` (`from_mlx.py:343-470`) regex-parses `mx.export_to_dot` output:

```python
_SOURCE_RE = re.compile(r'rank=source;\s*"([^"]+)"')
_SINK_RE   = re.compile(r'rank=sink;\s*"([^"]+)"')
_OP_RE     = re.compile(r'^\{\s*(\d+)\s+\[label\s*=\s*"(.*?)",\s*shape=rectangle\];\s*\}$')
_EDGE_RE   = re.compile(r'^"?([^"]+?)"?\s*->\s*"?([^"]+?)"?$')
```

It topologically sorts, then names nodes `mlx_dot:<opid>:<raw_label>`. It **has no primitive
arguments**, which is precisely why the callback mode exists. It also silently drops extra sink
tensors: *"MLX DOT export can include additional sink tensors unrelated to requested outputs."*
(`from_mlx.py:738`).

### 4.6 IR → MLX replay (`_eval_node_with_mlx`, `from_mlx.py:957-1257`)

A ~300-line interpreter that re-executes an IR `Graph` with MLX ops, used only by
`export_dot_from_ir` / `capture_graph_from_ir` (test/debug utilities). Its NCHW↔NHWC juggling is
informative about the zoo's layout convention:

```python
    if op in {"conv2d", "conv_general"}:
        # MLX core conv kernels use NHWC; zoo fixtures are NCHW.
        x_nhwc = mx.transpose(x, (0, 2, 3, 1))
        w_hwio = mx.transpose(w, (0, 2, 3, 1))
```

Unsupported ops raise `ValueError(f"MLX replay capture does not support op '{op}' yet.")`.

---

## 5. The IR (`ir.py`)

```python
@dataclass(frozen=True)
class TensorSpec:
    name: str
    shape: tuple[int, ...]
    dtype: str = "fp32"      # note: default fp32

@dataclass(frozen=True)
class StateSpec:
    name: str
    shape: tuple[int, ...]
    dtype: str = "fp16"      # note: default fp16, different from TensorSpec

@dataclass(frozen=True)
class Node:
    op: str
    inputs: tuple[str, ...]
    output: str
    attrs: dict[str, Any] = field(default_factory=dict)
    source: str | None = None      # e.g. "mlx_export:37:RoPE"

@dataclass
class Graph:
    inputs: list[TensorSpec]
    nodes: list[Node]
    outputs: list[str]
```

`Graph.validate()` (`ir.py:86-106`) enforces SSA: unique input names, no duplicate tensor names,
every node input already produced, every graph output produced. Errors:
`"Graph input names must be unique."`, `"Duplicate tensor name detected: {name}"`,
`"Node '{op}' has missing inputs: …"`, `"Graph outputs reference unknown tensors: …"`.

**Multi-output MLX primitives** are represented as *N separate nodes sharing the same inputs*, with
`attrs["output_index"]` and `attrs["num_outputs"]` (`from_mlx.py:433-446, 612-614`). The lowering
then re-selects the right result per node (`split`, `broadcast_arrays`, `meshgrid`, `divmod`).

### Dynamic dimension references

`shape` entries may be a special dict instead of an int (`ir.py:9-17`):

```python
_DYNAMIC_DIM_KEY = "__mlx2coreai_dynamic_dim__"

def dynamic_dim_ref(source: str, axis: int) -> dict[str, Any]:
    return {_DYNAMIC_DIM_KEY: True, "source": str(source), "axis": int(axis)}

def is_dynamic_dim_ref(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get(_DYNAMIC_DIM_KEY))
```

`-1` in a `TensorSpec.shape` means "dynamic" at the *type* level; a `dynamic_dim_ref` inside an
**attr** means "at runtime, read dim `axis` of tensor `source`". The lowering turns those into
`coreai.get_shape` + `coreai.slice_` + `coreai.cast` chains (`_dim_1d_from_value`,
`lower_to_coreai.py:240-251`).

---

## 6. Dynamic shapes via probe capture (`dynamic_shapes.py`)

`DynamicAxes = Mapping[str, Sequence[int] | Mapping[int, Any] | str]` — value may be `"all"`.

The core trick, docstring verbatim (`dynamic_shapes.py:68-73`):

> Replace attrs that vary with requested input axes by dynamic-dim refs.
>
> MLX's callback export still reports concrete primitive shapes, even with shapeless export.
> Capturing one nearby probe shape lets us identify which reshape/broadcast/range/slice attributes
> are really input dimensions.

Algorithm (`dynamicize_graph_from_probe`, lines 60-104):
1. Mark the requested input axes as `-1` in the `TensorSpec`s (`apply_dynamic_axes`).
2. `_validate_probe_compatibility` — the base and probe graphs must have identical node counts,
   identical ops and identical input arities, else
   `"dynamic shape probe produced a different graph structure: N nodes vs M nodes."`
3. Build candidate triples `(base_dim, probe_dim, ref)` for each dynamic axis where the two capture
   shapes differ.
4. Walk every attr of every node in lockstep with the probe graph; any **int** attr equal to
   `base_dim` in the base and `probe_dim` in the probe is replaced by the `dynamic_dim_ref`.

Guards in `_candidate_replacement` (lines 139-151): `np.generic` is unwrapped via `.item()`, and
`bool` is explicitly excluded so `True/1` is not mistaken for a dimension.

Test that pins the behavior (`tests/test_lower_to_coreai_smoke.py:296-322`): base has
`arange(end=4)` + `reshape([1,4])`, probe has `end=5` / `[1,5]`; after dynamicization
`dynamic.inputs[0].shape == (1, -1)`, `is_dynamic_dim_ref(nodes[0].attrs["end"])` and
`is_dynamic_dim_ref(nodes[1].attrs["shape"][1])` are both true.

**Cost:** using `dynamic_axes` + `dynamic_probe_inputs` means the model is traced twice and
executed at least twice more.

---

## 7. Normalization + inference passes (`passes.py`)

`normalize_graph(graph)` (lines 1024-1032) runs, in order:

1. `canonicalize_op_names` — `normalize_mlx_op_name` on every node op.
2. `canonicalize_input_specs` — strip names, int-ify shapes, alias dtypes
   (`half→fp16, bfloat16→bf16, float→fp32, double→fp64, int→int32, long→int64`).
3. `canonicalize_tensor_names` — `[^0-9a-zA-Z_] → _`, prefix `t_` if leading digit, de-dup with
   `_2`, `_3`… suffixes.
4. `canonicalize_constant_attrs` — `const|constant|literal → "constant"`, hoist `val/data/tensor`
   into `value`, normalize `dtype`. Arrays ≤ `_MAX_INLINE_ARRAY_VALUES = 128` become Python lists;
   larger ones stay as `np.ndarray` ("Avoid exploding memory/time for large weight tensors").
5. `canonicalize_sdpa_masks` — forces `do_causal`, `has_sinks`, `output_logsumexp` to bools and
   computes a `mask_mode` attr: `"none"` when <4 inputs, `"causal_plus_explicit"` when
   `do_causal and mask_mode=="auto"`, else one of `auto|bool|additive`.
6. `eliminate_identity_noops` — DCE for `{"identity","stop_gradient","copy","contiguous"}` unless
   the node output is a graph output.

`infer_graph_specs(graph) -> dict[str, InferredTensorSpec(shape, dtype)]` is a ~520-line
forward shape/dtype propagator (`_infer_node_spec`, lines 483-999). It handles broadcast, matmul
(2-D only!), SDPA, reductions, reshape with a single `-1`, transpose/moveaxis/swapaxes/expand_dims,
concat (with dynamic-axis awareness → `-1`), split, cast, slice_by_index, gather,
zeros/ones/full/arange/linspace, comparisons→bool, diag/diagonal/trace/tri/eye, broadcast_to,
meshgrid, kron, and **full conv/conv_transpose output-shape math** (`_conv_spatial_output`,
lines 406-429):

```python
        if transpose:
            dim = (input_size - 1) * stride - before - after + dilation * (kernel - 1) + output_padding[i] + 1
        else:
            dim = math.floor((input_size + before + after - dilation * (kernel - 1) - 1) / stride + 1)
```

dtype promotion rank (`_promote_dtype`, line 281):
`{"bool":0, "int32":1, "int64":2, "fp16":3, "bf16":4, "fp32":5, "fp64":6}` — note **bf16 ranks
above fp16**, so mixing fp16 and bf16 promotes to bf16.

`summarize_inference` returns `{"total_tensors", "with_shape", "with_dtype"}`; this is the
`inference_summary` you see in metadata — a coverage signal for how much of the graph the
inferencer understood.

---

## 8. Op registry (`op_registry.py`)

Two tables:

* `SUPPORTED_MLX_TO_COREAI_OPS: dict[str, str]` (lines 10-173) — **156 source names → 121 distinct
  lowering keys** (numbers from `docs/op_coverage.md:7-8`). Aliased as
  `SUPPORTED_MLX_TO_MIL_OPS` for "the shared normalization code ported from mlx2coreml. The values
  are lowering keys, not necessarily literal CoreAI op names."
* `_DOT_LABEL_ALIASES: dict[str, str]` (lines 181-340) — PascalCase MLX DOT labels → snake_case.

`normalize_mlx_op_name(name)` = alias lookup, else `name.strip().lower()`.
`coreai_op_for_mlx(name)` / `mil_op_for_mlx(name)` are the same function (both kept for compat).

Selected mappings worth memorizing:

```
divide/real_div     -> real_div        reciprocal/inverse -> inverse
remainder/mod       -> mod             where/select       -> select
slice               -> slice_by_index  take               -> gather
take_along_axis     -> gather_along_axis
logsumexp           -> reduce_log_sum_exp
stop_gradient/copy/contiguous -> identity
concatenate/concat  -> concat          arccos/arcsin/arctan/arctanh -> acos/asin/atan/atanh
conv1d/conv2d/conv3d/conv_general/convolution -> conv
conv_transpose{1,2,3}d -> conv_transpose
read_state / write_state / state_update_masked -> (same)     # stateful lowering primitives
```

### `UnsupportedOpsError`

`ensure_supported(graph)` raises `UnsupportedOpsError(ValueError)` carrying `.first_op`,
`.all_ops`, `.details`. The message is a mini backlog report (`op_registry.py:345-374`):

```
Unsupported MLX op encountered first: <op>
All unsupported ops: a, b, c
Recommendations:
- <op> (count=N, source=mlx_export:12:Foo, primitive=Foo) -> backlog status <status>; <recommendation>
  sample: output=..., inputs=[...], attrs={...}
Add mappings/lowerings in mlx2coreai/op_registry.py and mlx2coreai/lower_to_coreai.py.
```

Statuses come from parsing `docs/ops_status.md` sections `## Supported` / `## Not Yet Implemented`
/ `## Not Supported` (`_load_ops_statuses`, lines 377-408). **That file does not exist in the
repo**, so every unsupported op reports status `unlisted` with the recommendation *"Classify this op
in docs/ops_status.md and then implement or defer explicitly."* (dangling feature).

---

## 9. Lowering to Core AI MLIR (`lower_to_coreai.py`) — the heart

### 9.1 The `coreai` Python surface it consumes

Imports (lines 13-31) — this is a precise inventory of the `coreai-core==1.0.0b1` API this
converter depends on:

```python
from coreai._compiler.dialects import coreai
from coreai._compiler.ir import (
    ArrayAttr, BF16Type, DenseResourceElementsAttr, DictAttr, F16Type, F32Type,
    InsertionPoint, IntegerType, Location, Module, RankedTensorType, StringAttr, Type, Value,
)
from coreai.authoring import AIProgram, Context
from coreai._compiler.types import TensorSpec as CoreAITensorSpec
```

`_composite_declaration.py` additionally imports `Attribute, BoolAttr, Context, FloatAttr,
IntegerAttr, NamedAttribute` from `coreai._compiler.ir`.

Ops/builders used from `coreai._compiler.dialects.coreai` (exhaustive, gathered by reading the
file):

*Builders/classes:* `GraphOp(name=, input_types=, result_types=, input_names=, private=,
no_inline=, composite_decl=, loc=)`, `ConstantOp(value=, loc=)`, `ReshapeOp(value, shape,
results=[])`, `BroadcastToOp(value, shape, results=[])`, `RangeOp(start, stop, step, results=[])`,
`invoke(results=, callee=, operands=, loc=)`.

*Functions:* `constant`, `cast`, `get_shape`, `slice_`, `slice_update`, `shrink_dims`,
`expand_dims`, `reshape`, `transpose`, `concat`, `tile`, `pad`, `gather_nd`, `gather_along_axis`,
`scatter_nd`, `broadcast_shapes`, `softmax`, `argmax`, `reduce_sum`, `reduce_mean`, `reduce_min`,
`reduce_max`, `reduce_product`, `all_`, `any_`, `not_`, `conv2d`, `conv3d`, `greater`,
`sigmoid/silu/gelu/tanh/sin/cos/erf/acos/asin/atan/atanh/exp/log/sqrt/rsqrt/abs_`, and the
`broadcasting_*` family: `broadcasting_add/sub/mul/divide/pow/modulo/maximum/minimum/greater/
equal/not_equal/where/and/or/xor/bitwise_and/bitwise_or/bitwise_xor/batch_matmul/floor_divide`.

`GraphOp` members used: `.block` (context manager), `.arguments`, `.arg_attrs` (get/set
`ArrayAttr` of `DictAttr`), `.set_outputs_spec_from_dict(OrderedDict[str, Value])`.

`AIProgram` members used: `AIProgram._from_mlir_module(module)` (private!), `.optimize()`,
`.save_asset(Path)`, `str(program)` → MLIR text.

### 9.2 Type mapping (`_element_type`, lines 125-142)

| IR dtype | MLIR type |
| --- | --- |
| `fp16` | `F16Type.get()` |
| `bf16` | `BF16Type.get()` |
| `fp32`, **`fp64`** | `F32Type.get()` |
| `int32` | `IntegerType.get_signed(32)` |
| **`int64`** | `IntegerType.get_signed(32)` |
| `bool` | `IntegerType.get_signless(1)` |

Verbatim comment for int64 (lines 136-139):

> `# CoreAI can represent si64 in MLIR, but the runtime stack is generally <=32-bit oriented. Input
> types are narrowed to match the conversion policy used for constants.`

`_array_to_coreai` (lines 168-186) mirrors this for constant data and records a `downcast` string
in the weight manifest (`"fp64->fp32"`, `"int64->int32"`). int64 constants outside int32 range hard
fail: `ValueError("int64 constant cannot be safely downcast to int32.")`.

Dynamic dims: `_tensor_type` maps any negative dim to `RankedTensorType.get_dynamic_size()`
(lines 145-150).

### 9.3 Program construction (`CoreAILowerer.lower_many`, lines 441-515)

```python
with self.context:
    self.location = Location.unknown(self.context._mlir_context)
    with self.location:
        self.module = Module.create()
        with InsertionPoint(self.module.body):
            for entry in entries:
                graph = normalize_graph(entry.graph); graph.validate(); ensure_supported(graph)
                self.env = {}; self.inferred = infer_graph_specs(graph)
                public_inputs = self._public_inputs(graph, public_input_names=entry.public_input_names)
                graph_op = coreai.GraphOp(name=entry.entrypoint_name,
                                          input_types=[_tensor_type(s) for s in public_inputs],
                                          result_types=[],
                                          input_names=[s.name for s in public_inputs],
                                          loc=self.location)
                with graph_op.block:
                    self._seed_inputs(graph_op, public_inputs, graph)
                    for node in graph.nodes:
                        self.env[node.output] = self._lower_node(node)
                    outputs = OrderedDict((self._coreai_output_name(graph, name), self.env[name])
                                          for name in graph.outputs)
                    graph_op.set_outputs_spec_from_dict(outputs)
                self._mark_mutable_buffers(graph_op, public_inputs, graph)
...
program = AIProgram._from_mlir_module(self.module)
if optimized: program.optimize()
```

`LoweredCoreAIProgram` (lines 107-118):

```python
program: AIProgram
graph: Graph
public_inputs: list[TensorSpec]
weight_manifest: list[WeightInfo]
unresolved_extra_inputs: list[str]
optimized: bool
optimization_skip_reason: str | None
entrypoint_names: list[str]
public_inputs_by_entrypoint: dict[str, list[TensorSpec]]
graphs_by_entrypoint: dict[str, Graph]
```

**Multi-entrypoint support** is real: `build_coreai_programs([CoreAIGraphEntry(...), ...])` emits
several `coreai.GraphOp`s into one module. Test `test_multi_entrypoint_asset_generation`
(`tests/test_lower_to_coreai_smoke.py:32-56`) asserts `"@prefill" in str(program)` and
`"@decode" in str(program)` and that a single `.aimodel` saves. The stateful LLM converter
currently emits **only one** (`main`), but the plumbing for prefill/decode split exists.

**Optimization gating:** `_optimization_skip_reason(graph)` (line 2067) now unconditionally returns
`None`. Commit `5e9c7de` ("Allow optimization on SDPA for macOS 27") deleted this body:

```python
    has_dynamic_input = any(any(int(dim) < 0 for dim in spec.shape) for spec in graph.inputs)
    if not has_dynamic_input:
        return None
    for node in graph.nodes:
        if node.op == "scaled_dot_product_attention" and bool(node.attrs.get("do_causal", ...)):
            return "coreai_optimize_dynamic_causal_sdpa_reshape_bug"
```

The removed README caveat said: *"Dynamic causal `scaled_dot_product_attention` graphs currently
skip `AIProgram.optimize()` because the beta optimizer rewrites the causal mask into an invalid
runtime reshape for dynamic sequence shapes."* — a Core AI beta optimizer bug that was fixed
between betas. The dead hook remains, so re-adding a skip rule is a one-liner.

### 9.4 Weights: inline constants vs dense resources

```python
@dataclass(slots=True)
class WeightInfo:            # lines 59-86
    name: str; shape: tuple[int, ...]; dtype: str; source: str
    storage: str = "inline"          # "inline" | "resource"
    nbytes: int = 0
    resource_name: str | None = None
    external_weight_threshold: int | None = None
    downcast: str | None = None      # "fp64->fp32" | "int64->int32"
```

`_should_use_resource_constant` (lines 570-580): resource iff `externalize_weights` and
`threshold >= 0` and `arr.size >= threshold` and dtype is **not bool** and dtype is numeric or
bfloat16.

Resource emission (lines 582-589):

```python
    def _resource_constant(self, arr: np.ndarray, resource_name: str) -> Value:
        tensor_type = CoreAITensorSpec(list(arr.shape), arr.dtype.type)._to_mlir_type()
        attr = DenseResourceElementsAttr.get_from_buffer(
            np.ascontiguousarray(arr), resource_name, tensor_type,
        )
        return coreai.ConstantOp(value=attr, loc=self.location).result
```

Resource names are sanitized and prefixed: `_resource_name` → `mlx2coreai_<sanitized>`
(lines 336-342). Test pins it: `lowered.weight_manifest[0].resource_name == "mlx2coreai_w"`,
`.nbytes == 48`, `"dense_resource" in str(lowered.program)`
(`tests/test_lower_to_coreai_smoke.py:80-101`).

`source` values seen in the manifest: `"constant"`, `"constant_node"`, `"externalized_input"`,
`"zeros"/"ones"/"full"`, `"linspace"`, `"tri"`, `"eye"`, `"array_equal_shape"`.

**How weights flow end-to-end:** MLX's exporter classifies `nn.Module` parameters as *tape
constants* → `constants` event → `const` IR nodes with a numpy `value` attr → `_constant()` →
dense-resource `ConstantOp`. There is no separate weight file: the weights live in the `.aimodel`'s
`main.mlirb` as MLIR dense resources. There is **no quantization support in this repo** — no
palettization, no int4/int8 packing, no `coreai_opt` integration. bf16 checkpoints stay bf16;
everything else is fp32/fp16.

### 9.5 Named composites (RMSNorm / RoPE / SDPA / conv_transpose fallback)

`_emit_private_composite` (lines 691-737) creates a **private, no-inline `GraphOp`** with a
`composite_decl` attribute and then `coreai.invoke`s it from the main graph:

```python
graph_name = f"__mlx2coreai_{composite_name}_{self._private_graph_counter}_{node.output}"
composite_decl = generate_composite_decl(self.module.context, composite_name,
                                         input_names, ["output"], dict(attrs))
private = coreai.GraphOp(name=graph_name, input_types=[v.type for v in input_values],
                         result_types=[], input_names=input_names,
                         private=True, no_inline=True, composite_decl=composite_decl,
                         loc=self.location)
with private.block:
    result = body(list(private.arguments))
    private.set_outputs_spec_from_dict(OrderedDict([("output", result)]))
with self.current_graph.block:
    [out] = coreai.invoke(results=[result_type or input_values[0].type],
                          callee=graph_name, operands=input_values, loc=self.location)
```

The attribute text form (from `_composite_declaration.py:131-138`):

```python
    def to_coreai_attr(self, context: Context) -> Attribute:
        with Location.unknown(context):
            attrs = self._dict_to_dict_attr(self.attributes, context)
        return Attribute.parse(
            f'#coreai.composite_declaration<"{self.name}" = {attrs!s}>',
            context=context,
        )
```

`generate_composite_decl(context, composite_name, input_names, output_names, op_attributes,
version=1)` builds `{"input_names": [...], "output_names": [...], "op_attrs": {..., "version": 1}}`.
**Note it mutates the caller's dict**: `op_attributes["version"] = version` (line 194).

Composites emitted and their declared attrs:

| composite name | input_names | op_attrs |
| --- | --- | --- |
| `rms_norm` | `["input", "scale"]` | `{"axes": [...], "eps": float}` |
| `rope` | `["input"] (+ "offset", + "freqs")` | `{"scale", "base", "dims", "interleaved"}` |
| `scaled_dot_product_attention` | `["query","key","value"] (+ "attn_mask")` | `{"is_causal": bool, "window_size": int, ["scale": float]}` |
| `mlx_conv_transpose` | `["input_0","input_1",…]` | `{"source_op": …, "fallback": "unsupported_coreai_beta_asset_writer"}` |

Tests assert the literal MLIR text: `'composite_declaration<"rms_norm"' in str(program)`
(`test_lower_to_coreai_smoke.py:131`), and `'composite_declaration<"rope"'`
(`test_op_coverage.py:415`).

**Important:** the composite body is a *real, fully-lowered implementation*, not a stub — the
composite declaration is a hint for the Core AI compiler/runtime to pattern-match a fused kernel,
with the generic decomposition available as fallback. (Exception: the `mlx_conv_transpose` body is
literally `coreai.constant(np.zeros(spec.shape))` — a **numerically wrong placeholder** that only
exists so the asset can be written. See Gotchas.)

#### SDPA body (`_lower_sdpa`, lines 1301-1345)

```python
def body(args):
    bq, bk, bv = args[:3]
    bm = args[3] if len(args) > 3 else None
    if _rank(bq) >= 4 and _rank(bk) >= 4:
        target_heads = int(bq.type.shape[1])
        bk = _repeat_attention_heads(bk, target_heads)     # GQA expansion via expand_dims+tile+reshape
        bv = _repeat_attention_heads(bv, target_heads)
    head_dim = int(bq.type.shape[-1])
    effective_scale = scale_f if scale_f is not None else 1.0 / math.sqrt(float(head_dim))
    scaled_q = _bmul(bq, effective_scale)
    kt = coreai.transpose(bk, np.asarray([0, 1, 3, 2], dtype=np.uint32))
    scores = coreai.broadcasting_batch_matmul(scaled_q, kt)
    if bm is not None:
        scores = _badd(scores, coreai.cast(bm, scores.type.element_type))
    if is_causal:
        scores = _badd(scores, _causal_mask_like(scores))
    weights = coreai.softmax(scores, _rank(scores) - 1)
    return coreai.broadcasting_batch_matmul(weights, bv)
```

* **GQA:** `_repeat_attention_heads` (lines 1773-1797) requires `target_heads % heads == 0`, else
  `ValueError(f"Cannot repeat attention heads from {heads} to {target_heads}.")`.
* **Causal mask** (`_causal_mask_like`, lines 1740-1770) builds `range(q_len)` vs `range(k_len)`
  (dynamic-aware via `RangeOp` with a `?` result dim), does `coreai.greater(k, q)` and multiplies by
  **`-1e4`** (not `-inf`, not `-1e9`) in the score element type.
* **A bool mask is added, not selected**: `scores = scores + cast(mask, score_dtype)`. So an MLX
  *boolean* mask (True = keep) becomes `+1.0` on kept positions — numerically wrong. Only additive
  float masks work. The `mask_mode` attr computed by `canonicalize_sdpa_masks` is **never read** by
  the lowering.
* `has_sinks` / `output_logsumexp` are parsed into attrs and then **ignored** by the lowering.

#### RoPE body (`_rope_body`, lines 1900-1982)

```python
freq_values = np.power(np.float32(base), np.arange(0, dims, 2, dtype=np.float32) / np.float32(dims))
freqs = _reshape_with_mixed_shape(coreai.cast(freqs, F32Type.get()), [1, half])
angles = _bdiv(pos, freqs)          # pos / freqs  (MLX convention: freqs are periods)
cos = coreai.cos(angles); sin = coreai.sin(angles)
```

* Positions come from `RangeOp(0, seq_len_or_dynamic, 1)` cast to f32, optionally `* scale` and
  `+ offset`.
* `interleaved` (a.k.a. MLX `traditional`) reshapes to `[..., half, 2]` and slices even/odd;
  otherwise it slices the first/second half of the rotary block.
* `dims < feature_dim` → the tail is concatenated back unrotated.
* `ValueError(f"RoPE dims must be even, got {dims}.")` if odd.
* Trig tables are **explicitly broadcast** (`_broadcast_to_with_shape`) — a test asserts the exact
  MLIR type `"tensor<1x1x4x64xf32>"` (`test_lower_to_coreai_smoke.py:212-224`).
* MLX RoPE primitive inputs are always `{x, offset}` and optionally `{x, offset, freqs}`
  (verified `mlx/fast.cpp:530-557`), so mlx2coreai's `inputs[1]→offset`, `inputs[2]→freqs` mapping
  is correct. When `freqs` is supplied MLX passes `base = 1.0` (`fast.cpp:553`), which mlx2coreai
  records but ignores.

#### RMSNorm body (lines 1283-1289)

```python
def body(args):
    bx, bscale = args
    square = _bmul(bx, bx)
    mean_square = coreai.reduce_mean(square, axes)
    inv = coreai.rsqrt(_badd(mean_square, eps))
    out = _bmul(_bmul(bx, inv), bscale)
    return _reshape_like(out, bx)
```

`_reshape_like` is needed because `reduce_mean` drops dims and the composite's declared result type
must match `x.type` exactly.

### 9.6 Mutable state / KV cache in the MLIR

Three IR ops are "stateful lowering primitives" and all lower to *pass-through* values
(`_lower_node`, lines 749-759):

```python
if op == "read_state":   return self.env[node.inputs[0]]        # state tensor itself
if op == "write_state":  return self.env[node.inputs[1]]        # the new value
if op == "state_update_masked":
    state, value = self.env[node.inputs[0]], self.env[node.inputs[1]]
    if len(node.inputs) < 3: return value
    return coreai.broadcasting_where(self.env[node.inputs[2]], value, state)
```

The actual "this is a state" signal is an **argument attribute** written after the block is built
(`_mark_mutable_buffers`, lines 658-682):

```python
if spec.name in output_by_state:
    attrs["MutableBuffers.buffer_mutation"] = StringAttr.get(output_by_state[spec.name])
...
graph_op.arg_attrs = ArrayAttr.get(arg_attrs)
```

where `output_by_state[state_name]` is `node.attrs.get("coreai_output_name", node.output)` of the
`write_state`/`state_update_masked` node whose **first input** is that state.

So the contract is: *graph argument `keyCache` carries
`MutableBuffers.buffer_mutation = "<name of the graph output that is its new value>"`.*
Test pin: `'MutableBuffers.buffer_mutation = "cache_out"' in str(lowered.program)`
(`tests/test_op_coverage.py:300-313`).

`_coreai_output_name` (lines 684-689) lets a node rename the exported output — the stateful
converter sets `attrs={"coreai_output_name": spec.name}` so the mutated cache is exported under the
plain name `keyCache` rather than the internal `keyCache__updated`.

### 9.7 Dispatch tables (lines 1985-2048)

```python
_BINARY_OPS = {
    "add": coreai.broadcasting_add, "maximum": coreai.broadcasting_maximum,
    "minimum": coreai.broadcasting_minimum, "sub": coreai.broadcasting_sub,
    "mul": coreai.broadcasting_mul, "real_div": coreai.broadcasting_divide,
    "divide": coreai.broadcasting_divide, "pow": coreai.broadcasting_pow,
    "mod": coreai.broadcasting_modulo, "greater": coreai.broadcasting_greater,
    "greater_equal": lambda x, y: coreai.broadcasting_or(coreai.broadcasting_greater(x, y),
                                                         coreai.broadcasting_equal(x, y)),
    "less":  lambda x, y: coreai.broadcasting_greater(y, x),
    "less_equal": lambda x, y: coreai.broadcasting_or(coreai.broadcasting_greater(y, x),
                                                      coreai.broadcasting_equal(x, y)),
    "equal": coreai.broadcasting_equal, "not_equal": coreai.broadcasting_not_equal,
}
```

**Core AI has no `less`/`less_equal`/`greater_equal` primitive** — they are synthesized from
`greater`/`equal`/`or`. Same story for several unary ops:

```python
"expm1": lambda x: coreai.broadcasting_sub(coreai.exp(x), 1.0),
"log1p": lambda x: coreai.log(coreai.broadcasting_add(x, 1.0)),
"log2":  lambda x: coreai.broadcasting_divide(coreai.log(x), math.log(2.0)),
"log10": lambda x: coreai.broadcasting_divide(coreai.log(x), math.log(10.0)),
"degrees": lambda x: coreai.broadcasting_mul(x, 180.0 / math.pi),
"radians": lambda x: coreai.broadcasting_mul(x, math.pi / 180.0),
"isnan":  lambda x: coreai.broadcasting_not_equal(x, x),
"isinf":  lambda x: coreai.broadcasting_equal(coreai.abs_(x), float("inf")),
"isfinite": lambda x: coreai.not_(coreai.broadcasting_equal(coreai.abs_(x), float("inf"))),
```

`_REDUCE_OPS` maps `reduce_log_sum_exp` to the **numerically naive** `log(reduce_sum(exp(x)))`
(no max-subtraction) — an fp16 overflow hazard.

Also note there is **no `negative` op**: `negative` lowers to `broadcasting_mul(x, -1.0)`
(line 786), and `inverse` to `1.0 / (x + eps)` (lines 767-771).

### 9.8 Per-op lowering highlights

* `matmul` → `coreai.broadcasting_batch_matmul`; `addmm` → `add(bias, batch_matmul(x, y))`.
* `slice_update` (static) is lowered by **materializing every scatter index in Python**
  (`np.ndindex(*update_shape)` → an `(N, rank)` int32 constant → `coreai.scatter_nd`,
  lines 1084-1107). Cost is O(number of updated elements) *at conversion time*, and the index
  tensor is baked into the asset. Fails on non-positive strides or shape mismatch.
* `dynamic_slice_update` → `coreai.slice_update(x, start, start + shape(update), ones, update)`;
  requires full-rank `axes` and a rank-1 `start_indices` of length `rank`.
* `take`/`gather` → transpose the gathered axis to 0, `expand_dims` the indices, `gather_nd`, then
  transpose back (lines 1151-1231). `gather` with `slice_shape` requires **unit slice on the
  gathered axis** and **full slices on all other axes**, otherwise it raises.
* `split` computes slice bounds in Python and emits `coreai.slice_` per output index — the split
  axis must be **statically known** (`int(x.type.shape[axis])`).
* `zeros_like/ones_like/full_like` → `x*0 + value` (avoids needing a shape op).
* `tri/eye/linspace/diag(vector)` are **folded to constants at conversion time**.
* `number_of_elements` → `reduce_product(cast(get_shape(x), si32), [0])` — genuinely dynamic.
* `arange` with a dynamic bound uses `coreai.RangeOp(..., results=[RankedTensorType.get([?], si32)])`.
* Conv: `spatial ∈ {1,2,3}`; rank-3 (1-D) input is **expanded to 2-D** (`expand_dims` axis 2) and
  squeezed back. Padding is applied as an explicit `coreai.pad(x, [0,0,0,0,*padding], 0,
  "constant")` before `coreai.conv2d/conv3d(x, w, strides, dilations, groups)` — i.e. Core AI's
  conv takes no pad argument in this beta.
* Transposed conv: only the **1×1, stride-1, dilation-1, groups-1, no-padding** case gets a real
  lowering (reshape→matmul→transpose, `_lower_pointwise_conv_transpose`, lines 1667-1694).
  Everything else goes to the zero-filled composite fallback.
* `var/std` correction (`ddof`) requires a **static** shape (`_static_shape`), else it raises.

---

## 10. Stateless mlx-lm conversion (`_convert_mlx_lm.py`)

```python
convert_mlx_lm(model_id, output_path, *, prompt=None, sequence_length=None, batch_size=1,
               input_ids=None, input_name="input_ids", lazy_load=False, revision=None,
               dynamic_sequence=True, config=None, dot_output_path=None,
               load_fn=None, capture_function=None) -> ConvertedCoreAIModel
```

Docstring (lines 42-48):

> Load an `mlx-lm` model, capture its logits path, and save an `.aimodel`.
> `capture_function` can be supplied for models that need a non-standard signature, masks, or
> cache/state arguments. By default the helper captures `model(input_ids)` and selects the first
> output when the model returns a tuple, list, or mapping.

`load_mlx_lm_model` (lines 98-117): `from mlx_lm import load as load_fn`, called as
`load_fn(model_id, lazy=bool(lazy_load)[, revision=revision])`. Missing package raises
`ImportError("convert_mlx_lm requires mlx-lm. Install it with `pip install mlx-lm` or pass a
custom load_fn.")`. The `load_fn=` seam is what all tests use to avoid network.

`build_mlx_lm_inputs(*, tokenizer, prompt=None, sequence_length=None, batch_size=1,
input_ids=None) -> MLXLMConversionInputs` (lines 120-170):
* explicit `input_ids` wins, is `np.int32`, 1-D is promoted to `(1, N)`, and **`sequence_length`
  and `batch_size` are ignored in that branch** (pinned by
  `test_build_mlx_lm_inputs_accepts_explicit_ids`).
* no prompt → `synthetic=True`, `sequence_length or 1` copies of a fallback token
  (`bos_token_id → eos_token_id → pad_token_id → 0`).
* with `sequence_length`: truncate, or pad with `pad_token_id → eos_token_id → bos_token_id →
  last token`.
* `batch_size > 1` → `np.repeat` along axis 0.

Dynamic sequence (lines 263-291): sets `capture_shapeless=True`,
`dynamic_axes={input_name: [1]}`, and a probe input built by appending **one duplicate of the last
token** (`np.concatenate([base, base[:, -1:]], axis=1)`), i.e. probe length = base length + 1.

The `metadata["mlx_lm"]` block records: `model_id, revision, lazy_load, prompt, sequence_length,
capture_sequence_length, batch_size, input_name, dynamic_sequence, token_count,
padded_token_count, synthetic_input_ids`.

---

## 11. Stateful LLM conversion (`_convert_mlx_lm_stateful.py`) — the KV-cache story

This is the most consequential file in the repo. Docstring (lines 151-157):

> Convert an mlx-lm model into one stateful CoreAI asset.
>
> The generated `.aimodel` follows the macOS LLM contract used by `coreai-models`: a single dynamic
> `main` entrypoint with `input_ids`, `position_ids`, and two mutable KV-cache state tensors named
> `keyCache` and `valueCache` by default.

### 11.1 Trace constants — deliberately mirror Apple's

```python
TRACE_QUERY_LENGTH = 16      # _convert_mlx_lm_stateful.py:34
TRACE_POSITION_OFFSET = 8    # _convert_mlx_lm_stateful.py:35
```

Compare `apple/coreai-models` `python/src/coreai_models/export/_constants.py`:

```python
# KV cache names used by the Swift runner
KEY_CACHE_NAME = "keyCache"
VALUE_CACHE_NAME = "valueCache"
TRACE_KV_CACHE_SEQ_LEN = 2048
QUANT_TRACE_QUERY_LEN = 16
QUANT_TRACE_OFFSET = 8
```

Identical values (16 / 8) and identical state names. mlx2coreai is deliberately reproducing the
Apple LLM export recipe from the MLX side.

### 11.2 Cache layout

```python
def _make_state_specs(layout, *, batch_size, max_context_length, cache_dtype,
                      key_cache_name, value_cache_name) -> list[StateSpec]:
    shape = (layout.num_layers, int(batch_size), layout.num_key_value_heads,
             int(max_context_length), layout.head_dim)
    return [StateSpec(key_cache_name, shape, cache_dtype),
            StateSpec(value_cache_name, shape, cache_dtype)]
```

`(n_layers, batch, n_kv_heads, max_seq_len, head_dim)` — byte-for-byte the same as
`coreai_models/primitives/macos/cache.py:52-53`
(`torch.zeros(n_layers, 1, n_kv_heads, max_seq_len, head_dim)`), and the dynamic axis is **3**,
matching `KVCache.seq_len_dim() == 3`.

`_infer_cache_layout(model)` (lines 634-657) reads `model.layers` (or `model.model.layers`) for
depth, then `model.args.num_key_value_heads` / `model.args.head_dim`, falling back to
`layers[0].self_attn.n_kv_heads` and `hidden_size // num_attention_heads`. Raises
`"Could not infer mlx-lm transformer layers for stateful cache conversion."` or
`"Could not infer KV-cache head layout from mlx-lm model args."`.

### 11.3 The exportable cache shim

The clever bit: a duck-typed replacement for mlx-lm's `KVCache` that records slice-updates into a
single stacked tensor so MLX's tracer sees them (lines 67-128):

```python
@dataclass(slots=True)
class _LayeredKVCacheState:
    keys: Any
    values: Any


class _ExportableLayeredKVCache:
    def __init__(self, state, *, layer_idx, offset):
        self.state = state
        self.layer_idx = int(layer_idx)
        self.keys = state.keys[self.layer_idx]
        self.values = state.values[self.layer_idx]
        self.offset = offset

    def update_and_fetch(self, keys, values):
        import mlx.core as mx
        offset = mx.reshape(self.offset, (1,))
        layer = mx.array([self.layer_idx], dtype=mx.int32)
        start = mx.concatenate([
            layer,
            mx.array([0, 0], dtype=mx.int32),
            offset,
            mx.array([0], dtype=mx.int32),
        ])
        expanded_keys = mx.expand_dims(keys, 0)
        expanded_values = mx.expand_dims(values, 0)
        self.state.keys = mx.slice_update(self.state.keys, expanded_keys, start, [0, 1, 2, 3, 4])
        self.state.values = mx.slice_update(self.state.values, expanded_values, start, [0, 1, 2, 3, 4])
        self.keys = self.state.keys[self.layer_idx]
        self.values = self.state.values[self.layer_idx]
        return self.keys, self.values

    def make_mask(self, N, window_size=None, return_array=False):
        import mlx.core as mx
        if window_size is not None:
            raise NotImplementedError(
                "stateful KV-cache export does not support sliding-window masks yet."
            )
        query_positions = mx.arange(N) + self.offset
        key_positions = mx.arange(self.state.keys.shape[3])
        return (query_positions[:, None] >= key_positions[None, :])[None, None, :, :]

    def size(self) -> int: return self.state.keys.shape[3]
    def empty(self) -> bool: return False
```

The interface it emulates (`update_and_fetch`, `make_mask`, `size`, `empty`, `.offset`, `.keys`,
`.values`) is mlx-lm's cache protocol. `mx.slice_update(dst, src, start, axes)` becomes a
`DynamicSliceUpdate` primitive → `dynamic_slice_update` IR op → `coreai.slice_update`.

The write offset is derived from `position_ids` **inside the traced function** (lines 558-564):

```python
def _offset_from_position_ids(input_ids, position_ids):
    query_indices = mx.arange(input_ids.shape[1], dtype=mx.int32)
    query_len = mx.max(query_indices) + mx.array(1, dtype=mx.int32)
    last_position = mx.max(position_ids)
    return last_position - query_len + mx.array(1, dtype=mx.int32)
```

i.e. `offset = max(position_ids) - len(input_ids) + 1`. **This is the whole reason `position_ids`
must be the *full* position vector `[0 .. total_positions-1]`, not just the new positions** —
see §12.2, where both benchmark backends feed `arange(total_positions)`.

### 11.4 The capture function

```python
def capture(**kwargs):
    import mlx.core as mx
    input_ids = kwargs[input_name]
    position_ids = kwargs[position_ids_name]
    offset = _offset_from_position_ids(input_ids, position_ids)
    state = _LayeredKVCacheState(keys=kwargs[key_cache_name], values=kwargs[value_cache_name])
    caches = [_ExportableLayeredKVCache(state, layer_idx=i, offset=offset)
              for i in range(layout.num_layers)]
    logits = _select_primary_output(model(input_ids, cache=caches))
    if cast_bf16_logits_to_fp16 and "bfloat16" in str(getattr(logits, "dtype", "")).lower():
        logits = logits.astype(mx.float16)
    return logits, state.keys, state.values
```

So the traced function returns a **3-tuple** `(logits, keys, values)`; the two cache tensors are
then rewritten into `write_state` nodes.

### 11.5 `_add_state_writes` (lines 588-621)

```python
    for spec, value_name in zip(state_specs, state_value_outputs, strict=True):
        output_name = f"{spec.name}__updated"
        nodes.append(
            Node("write_state", (spec.name, value_name), output_name,
                 attrs={"coreai_output_name": spec.name},
                 source="mlx2coreai:stateful_kv_cache")
        )
```

`_reorder_graph_inputs(graph, [input_name, position_ids_name, key_cache_name, value_cache_name])`
then forces the argument order — which is why the Swift runner can index
`descriptor.stateNames[0]` = key, `[1]` = value.

### 11.6 Dynamic axes for the stateful path (lines 448-489)

```python
if dynamic_sequence:
    dynamic_axes_dict[input_name] = [1]
    dynamic_axes_dict[position_ids_name] = [1]
if dynamic_state:
    dynamic_axes_dict[key_cache_name] = [3]
    dynamic_axes_dict[value_cache_name] = [3]
```

Probe shapes: `probe_length = base+1` if `base < max_context_length` else `base-1`
(`_probe_sequence_length`, lines 753-758); `probe_state_context_length = max_context_length + 1`.
So the probe genuinely perturbs both the token axis and the cache axis.

Trace shapes: `trace_sequence_length = min(16, max_context_length)`,
`trace_offset = 8` (clamped so `offset + seq <= max_context_length`),
`position_length = trace_offset + trace_sequence_length` → `position_ids = arange(24)[None, :]`
for the default `max_context_length=256`.

`stateful_config = replace(config, capture_shapeless=bool(dynamic_axes), dynamic_axes=…,
dynamic_probe_inputs=…, state_specs=state_specs)`.

### 11.7 Precision handling

* `_resolve_compute_precision(model, "auto")` walks `model.parameters()` and returns the first
  `bf16|fp16|fp32` it sees, defaulting to `fp32`.
* `_apply_model_compute_precision` calls `model.set_dtype(mx.bfloat16|float16|float32)` when the
  model exposes it — **this mutates the loaded model in place**.
* `cache_dtype` defaults to the resolved compute precision.
* `cast_bf16_logits_to_fp16=True` (default) casts bf16 logits to fp16 *inside the traced graph*.
  The older README explains why: *"logits are cast to FP16 by default to match the public Qwen3
  coreai-models recipe."* The Swift benchmark hard-codes `logits.view(as: Float16.self)`, so
  disabling this flag breaks that runner.

### 11.8 Bundle output

`_resolve_bundle_paths` (lines 301-311):

| `--output` | bundle dir | nested asset |
| --- | --- | --- |
| `qwen` | `qwen/` | `qwen/qwen.aimodel` |
| `qwen.aimodel` | `qwen/` | `qwen/qwen.aimodel` |

`_write_coreai_models_bundle` writes `tokenizer/` (via `tokenizer.save_pretrained(...)`, else
`transformers.AutoTokenizer.from_pretrained(model_id, revision=…).save_pretrained(...)`; if neither
works: `RuntimeError("Could not save tokenizer: mlx-lm did not return a tokenizer with
save_pretrained(), and transformers is not importable.")`) and `metadata.json`:

```python
{
    "metadata_version": "0.2",
    "kind": "llm",
    "name": name,
    "assets": {"main": asset_name},
    "language": {
        "tokenizer": model_id,
        "vocab_size": _vocab_size(tokenizer, model),
        "max_context_length": int(max_context_length),
        "embedded_tokenizer": True,
        "function_map": {"main": [entrypoint_name]},
    },
    "source": {"model_definition": "mlx", "hf_model_id": model_id},
    "compression": None,
    "compilation": {"date": datetime.now().astimezone().isoformat(), "targets": []},
}
```

This is **identical in shape** to `apple/coreai-models`
`python/src/coreai_models/export/bundle.py:48-68`, whose only differences are
`"model_definition": "torch"`, a real `compression` string, and `max_context_length` sourced from
`hf_config.max_position_embeddings`. Test `test_convert_mlx_lm_stateful_live_mlx_smoke_saves_unified_asset`
(`tests/test_convert_mlx_lm.py:196-257`) asserts every one of these fields.

Final on-disk layout:

```
qwen/
├── metadata.json
├── tokenizer/            # HF tokenizer files (tokenizer.json, etc.)
└── qwen.aimodel/
    ├── main.mlirb        # serialized Core AI MLIR (weights live here as dense resources)
    ├── main.hash
    └── metadata.json
```

(The three asset children are pinned by `test_smoke_asset_generation`,
`tests/test_lower_to_coreai_smoke.py:25-29`.)

`MLXLMStatefulConversion` fields (lines 38-57): `main, lowered, asset, bundle_path, asset_path,
bundle_metadata, max_context_length, inputs, state_specs, metadata` + `.program` and
`.weight_manifest` properties. `metadata["mlx_lm_stateful"]` records every knob including
`trace_sequence_length`, `trace_offset`, `compute_precision`, `cache_dtype`, `num_layers`,
`num_key_value_heads`, `head_dim`, `cast_bf16_logits_to_fp16`.

---

## 12. Runtime (`runtime.py`) and the Swift runner question

### 12.1 The Python runtime helper

```python
def _load_coreai_runtime() -> _CoreAIRuntimeBindings:
    try:
        from coreai.authoring import AIModelAsset
        from coreai.runtime import (ComputeUnitKind, NDArray, SpecializationOptions, StorageKind)
    except Exception as exc:
        raise CoreAIRuntimeUnavailableError(
            "coreai.runtime is not available. Install coreai-core with runtime "
            "support and run on a CoreAI-capable macOS/iOS runtime."
        ) from exc
```

The one real execution path (`run_aimodel`, lines 67-98):

```python
    asset, asset_path = _coerce_asset(asset_or_path, bindings.AIModelAsset)   # AIModelAsset.load(path)
    resolved_storage_kind = _resolve_storage_kind(storage_kind, bindings.StorageKind)
    nd_inputs = {name: _to_ndarray(value, bindings.NDArray, resolved_storage_kind)
                 for name, value in inputs.items()}

    async with asset.executable(specialization_options=specialization_options) as ai_model:
        function = ai_model.load_function(function_name)
        raw_outputs = await function(inputs=nd_inputs)

    outputs = {str(name): _output_to_numpy(value) for name, value in raw_outputs.items()}
```

`NDArray` is constructed as `NDArray(data)` or `NDArray(data=data, backing=storage_kind)`
(lines 455-461). Outputs are converted with `value.numpy()` when available.

Sync wrappers refuse to run inside a loop (`_run_sync`, lines 547-556):
`RuntimeError("Cannot use a sync CoreAI runtime helper from a running event loop; await the async
helper instead.")`

Validation: `compare_coreai_outputs(actual, expected, *, rtol=1e-4, atol=1e-4,
match_by_order=True)` → `list[CoreAIOutputComparison]` with `max_abs_error` computed in
`complex128`. bf16 is treated as numeric via `dtype == ml_dtypes.bfloat16`
(`_is_numeric_dtype`, lines 541-544). `match_by_order=True` means a runtime output named `out_0`
can be compared against a captured output named `attn` purely positionally.

**Critical gap:** `run_aimodel` calls `await function(inputs=nd_inputs)` with **no `state=`
argument**. The packaged library therefore *cannot execute the stateful KV-cache asset it
produces*. Only `scripts/benchmark_aimodel_sampling.py` can, by calling the raw `function` object
itself.

### 12.2 The two benchmark backends

`scripts/benchmark_aimodel_sampling.py` — flags:

| Flag | Default |
| --- | --- |
| `asset` (positional) | — bundle dir **or** nested `.aimodel` |
| `--contexts` | `"16,32,64,128,256"` |
| `--steps` | 16 |
| `--warmup` | 1 |
| `--function-name` | `main` |
| `--input-name` | `input_ids` |
| `--position-ids-name` | `position_ids` |
| `--output-name` | None → first runtime output |
| `--model-id`, `--revision` | None (tokenizer override; default = embedded `tokenizer/`) |
| `--prompt` | None |
| `--fill-token-id` | 0 |
| `--temperature` | 0.0 (0 ⇒ greedy `nanargmax`) |
| `--top-k` | 50 |
| `--seed` | 0 |
| `--grow-context` | flag — "Increment position_ids after each sampled token. Default keeps each interval fixed." |
| `--decode` | flag |
| `--json-output` | None |
| `--runtime-backend` | `auto` \| `python` \| `swift`, **help suppressed** (`argparse.SUPPRESS`) |

README invocation (`README.md:30-35`):

```bash
python scripts/benchmark_aimodel_sampling.py qwen \
  --contexts 16,32,64,128,256 \
  --steps 16 \
  --decode
```

Python-backend call shape (lines 214-239) — **this is the only place in the repo that shows how to
drive a stateful Core AI function from Python**:

```python
async def run_main(function, NDArray, token_ids, position_ids, state, *, input_name, position_ids_name):
    return await function(
        inputs={
            input_name: NDArray(np.asarray(token_ids, dtype=np.int32)[None, :]),
            position_ids_name: NDArray(np.asarray(position_ids, dtype=np.int32)[None, :]),
        },
        state=state,
    )


def allocate_state(function, NDArray, *, state_capacity: int) -> dict[str, Any]:
    state = {}
    for name in function.desc.state_names:
        descriptor = function.desc.state_descriptor(name=name)
        shape = tuple(int(state_capacity) if int(dim) < 0 else int(dim) for dim in descriptor.shape)
        state[name] = NDArray(np.zeros(shape, dtype=_runtime_dtype_to_numpy(descriptor.dtype)))
    return state
```

So the Python runtime surface is: `AIModelAsset.load(path)` → `async with asset.executable() as
model` → `model.load_function(name)` → `function.desc.{state_names, output_names,
state_descriptor(name=)}` → `await function(inputs=…, state=…)` → dict of NDArrays with `.numpy()`.

Bundle resolution (`resolve_asset_path`, lines 190-203): reads `metadata.json["assets"]["main"]`,
falling back to a single `*.aimodel` glob; raises
`ValueError(f"Could not resolve .aimodel asset from {path}.")`.

### 12.3 The Swift runner — and *which* Python bindings are incomplete

`scripts/benchmark_aimodel_sampling_coreai.swift` (added by `059c9f3`, *"Add a swift runner as
python bindings are incomplete as of now."*). It uses the **Swift `CoreAI` framework** directly:

```swift
import CoreAI
import Darwin
import Foundation

@main
struct CoreAIBenchmarkBackend {
    static func main() async { ... }

    static func run() async throws {
        var options = SpecializationOptions(preferredComputeUnitKind: .gpu)
        options.expectFrequentReshapes = false
        let model = try await AIModel(contentsOf: modelURL, options: options)
        guard let descriptor = model.functionDescriptor(for: runOptions.functionName) else { ... }
        guard let function = try model.loadFunction(named: runOptions.functionName) else { ... }
        guard descriptor.inputNames.count == 2 else { ... }
        guard descriptor.stateNames.count == 2 else { ... }
        guard let outputName = runOptions.outputName ?? descriptor.outputNames.first else { ... }

        let keyName = descriptor.stateNames[0]
        let valueName = descriptor.stateNames[1]
        let inputDesc  = try ndArrayDescriptor(descriptor.inputDescriptor(of: inputName),  name: inputName)
        let keyDesc    = try ndArrayDescriptor(descriptor.stateDescriptor(of: keyName),    name: keyName)
        let logitsDesc = try ndArrayDescriptor(descriptor.outputDescriptor(of: outputName), name: outputName)
        let vocabSize  = logitsDesc.shape.last ?? 0
        ...
    }
}
```

Per-step call (lines 227-264):

```swift
        var inputIds = NDArray(descriptor: inputDesc.resolvingDynamicDimensions([1, tokens.count]))
        fillInt32(&inputIds, values: tokens)

        var positionIds = NDArray(descriptor: positionDesc.resolvingDynamicDimensions([1, totalPositions]))
        fillInt32(&positionIds, values: (0..<totalPositions).map { Int32($0) })

        var logits = NDArray(descriptor: logitsDesc.resolvingDynamicDimensions([1, tokens.count, vocabSize]))

        var states = InferenceFunction.MutableViews()
        states.insert(&keyCache, for: keyName)
        states.insert(&valueCache, for: valueName)

        var outputs = InferenceFunction.MutableViews()
        outputs.insert(&logits, for: outputName)

        _ = try await function.run(
            inputs: [inputName: inputIds, positionName: positionIds],
            states: consume states,
            outputViews: consume outputs
        )
```

Buffer access helpers:

```swift
func fillInt32(_ array: inout NDArray, values: [Int32]) {
    var view = array.mutableView(as: Int32.self)
    view.withUnsafeMutablePointer { pointer, _, _ in
        for i in values.indices { pointer[i] = values[i] }
    }
}

func greedyToken(logits: NDArray, tokenCount: Int, vocabSize: Int) -> Int32 {
    let offset = max(0, tokenCount - 1) * vocabSize
    let view = logits.view(as: Float16.self)          // hard-coded fp16 logits
    ...
}
```

Swift API surface used (a useful inventory of the macOS 27 `CoreAI` framework):
`AIModel(contentsOf:options:)` (async throws), `AIModel.functionDescriptor(for:)`,
`AIModel.loadFunction(named:)`, `SpecializationOptions(preferredComputeUnitKind:)` +
`.expectFrequentReshapes`, `ComputeUnitKind.gpu`, function descriptor `.inputNames / .stateNames /
.outputNames / .inputDescriptor(of:) / .stateDescriptor(of:) / .outputDescriptor(of:)`,
`InferenceValue.Descriptor` (enum, case `.ndArray(NDArrayDescriptor)`),
`NDArrayDescriptor.shape` + `.resolvingDynamicDimensions([Int])`, `NDArray(descriptor:)`,
`NDArray.view(as:)` / `.mutableView(as:)` / `withUnsafe(Mutable)Pointer { ptr, _, _ in }`,
`InferenceFunction.MutableViews` + `.insert(_:for:)`,
`InferenceFunction.run(inputs:states:outputViews:)` (async throws, takes `consume`d views).

**Which Python bindings are incomplete — evidence-based reading.** The commit message doesn't say,
but the API delta between the two backends is unambiguous:

1. **No output views.** Swift preallocates a `logits` `NDArray` and passes `outputViews:` so the
   runtime writes straight into it. The Python API only offers `raw_outputs = await
   function(inputs=…, state=…)` returning fresh NDArrays, then `.numpy()` copies them. For a
   0.6 B model with a 150k vocab that is a fresh multi-hundred-KB allocation + copy per decode
   step — exactly what wrecks a decode-throughput benchmark.
2. **No explicit mutable-state view/ownership model.** Swift has
   `InferenceFunction.MutableViews` and `consume` (Swift ownership), guaranteeing zero-copy,
   in-place KV mutation. Python passes a plain `dict[str, NDArray]` as `state=`; nothing in the
   binding expresses the aliasing/ownership contract.
3. **No specialization control in practice.** `dab7096` wired `SpecializationOptions` and
   `ComputeUnitKind` into `mlx2coreai/runtime.py` and gave the benchmark
   `--compute-unit {auto,default,cpu,cpu-preferred,gpu,neural-engine}` and
   `--debug-specialization`. Commit `d032a95` **removed** both flags; the current Python benchmark
   calls bare `asset.executable()` (line 108) with no options, while the Swift runner explicitly
   requests `.gpu` and `expectFrequentReshapes = false`. So on the Python side the compute-unit
   selection is either gone or non-functional at this beta.
4. **Weaker descriptor introspection.** Python exposes `function.desc.state_names` /
   `state_descriptor(name=)` / `output_names` and the script must hand-substitute negative dims;
   Swift has a first-class `resolvingDynamicDimensions(_:)` on the descriptor plus per-role
   descriptor accessors, and can validate arity up front.
5. **The library's own `run_aimodel` has no `state=` parameter at all** (`runtime.py:87`), so the
   supported public Python API cannot execute a stateful asset. That alone forces a Swift (or
   raw-binding) path for any KV-cache benchmark.

**Backend auto-selection** (`benchmark_aimodel_sampling.py:394-420`): `auto` picks Swift when
`platform.system() == "Darwin"` **and** an SDK with `CoreAI.framework` is found **and** none of the
Python-only options are used. The Swift backend explicitly rejects:

```python
def unsupported_swift_backend_options(args) -> list[str]:
    unsupported = []
    if args.prompt is not None:    unsupported.append("--prompt")
    if args.model_id is not None:  unsupported.append("--model-id")
    if args.revision is not None:  unsupported.append("--revision")
    if args.decode:                unsupported.append("--decode")
    if args.json_output is not None: unsupported.append("--json-output")
    if float(args.temperature) != 0.0: unsupported.append("--temperature != 0")
    return unsupported
```

with the error *"Swift CoreAI backend currently supports synthetic greedy benchmarking only;
unsupported options: …"*. So the README's `--decode` example silently keeps you on the **Python**
backend.

**Swift build recipe** (`ensure_swift_backend`, lines 461-500) — copyable:

```bash
xcrun swiftc \
  -parse-as-library \
  -sdk "$SDKROOT" \
  -target arm64-apple-macos27.0 \
  -framework CoreAI \
  scripts/benchmark_aimodel_sampling_coreai.swift \
  -o .build/coreai_stateful_benchmark
```

SDK discovery (lines 503-516): `$SDKROOT`, else
`/Applications/Xcode-beta.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`,
validated by the existence of `System/Library/Frameworks/CoreAI.framework`. `DEVELOPER_DIR` is
inferred by walking up until a dir has both `Toolchains/` and `Platforms/`. If nothing is found:

> `RuntimeError("Could not find a macOS 27 SDK with CoreAI.framework. Set SDKROOT or install Xcode
> beta at /Applications/Xcode-beta.app.")`

Rebuild is mtime-based (`binary.stat().st_mtime < source.stat().st_mtime`).

Swift runner CLI (its own parser, lines 17-96): positional `<model.aimodel>` plus
`--contexts`, `--steps`, `--warmup`, `--function-name`, `--input-name`, `--position-ids-name`,
`--output-name`, `--fill-token-id`, `--grow-context`. Unknown flags →
`"unknown Swift backend argument: <flag>"`.

Both backends print the same table:

```
 context  steps  elapsed_s      tok/s     output     pos0     pos1
-------- ------ ---------- ---------- ---------- -------- --------
```

### 12.4 State capacity trick

Both backends over-allocate the KV cache along the dynamic axis:

```python
state_capacity = context_length + (args.steps if args.grow_context else 1)   # python, line 113
```
```swift
let stateCapacity = contextLength + (runOptions.growContext ? runOptions.steps + 1 : 1)  // swift, line 148
```

(Note the off-by-one difference: Python uses `steps`, Swift uses `steps + 1`.)
Because `--dynamic-state` marks cache axis 3 dynamic, the runtime cache size is chosen **at
allocation time**, independent of `--max-context-length` used at conversion.

---

## 13. Tests as executable documentation

`tests/conftest.py` only inserts the repo root on `sys.path`.

| File | What it pins |
| --- | --- |
| `test_lower_to_coreai_smoke.py` (322 L) | asset children `["main.hash","main.mlirb","metadata.json"]`; multi-entrypoint; externalized weights; resource vs inline threshold; composite text; dynamic dim MLIR types (`"tensor<1x?xsi32>"`, `"tensor<1x?x1024xf32>"`, `"tensor<1x1x4x64xf32>"`); `coreai.get_shape` presence; SDPA optimizer now runs; probe dynamicization |
| `test_op_coverage.py` (420 L) | parametrized asset generation for 14 binary, 13 unary, 10 reduction, 2 arg-reduction ops + ~20 shape/index/creation graphs; `MutableBuffers.buffer_mutation`; rank-2 embedding `take`; callback-style `gather` with `slice_shape`; **two live MLX captures** (toy transformer, `mx.fast.rms_norm`/`mx.fast.rope`) |
| `test_convert_mlx_lm.py` (290 L) | input building/padding/synthesis; `load_fn` forwarding; the full stateful bundle metadata contract |
| `test_runtime.py` (196 L) | fake `AIModelAsset`/`NDArray`/`StorageKind` doubles — shows the exact runtime protocol shape the wrapper assumes |
| `test_mlx2coreml_zoo_assets.py` (21 L) | every `_build_*` in `tests/model_zoo` lowers + saves |
| `test_op_coverage_report.py` (23 L) | report writes MD+JSON, `schema_version == "mlx2coreai.op_coverage.v1"`, and `unique_source_ops == supported_source_op_names` (i.e. **100 % of the registry must be exercised** or the suite fails) |

Two highly copyable live-capture tests:

```python
# tests/test_op_coverage.py:404-420
def test_mlx_fast_rmsnorm_and_rope_emit_composites(tmp_path):
    mx = pytest.importorskip("mlx.core")

    def rms(x, w):
        return mx.fast.rms_norm(x, w, 1e-5)

    def rope(x):
        return mx.fast.rope(x, dims=4, traditional=False, base=1000000.0, scale=1.0, offset=0)

    rms_model = convert_mlx_to_coreai(
        rms, {"x": rng.standard_normal((2, 4)).astype(np.float32), "w": np.ones((4,), np.float32)},
        config=ConversionConfig(optimize=False), output_path=tmp_path / "rms.aimodel")
    assert 'composite_declaration<"rms_norm"' in str(rms_model.program)
    rope_node = next(n for n in rope_model.prepared.normalized_graph.nodes if n.op == "rope")
    assert rope_node.attrs["dims"] == 4
    assert rope_node.attrs["traditional"] is False
    assert rope_node.attrs["base"] == 1000000.0
```

`tests/model_zoo.py:881-1045` contains a full **Llama-3-style transformer block** (RoPE with
frequency smoothing, GQA-capable `Attention`, SwiGLU `MLP`, two `nn.RMSNorm`) captured live:

```python
    graph, normalized_inputs, expected = capture_graph_from_mlx_function(
        dot_output_path=artifacts_dir / "capture_graph.dot",
        inputs={"x": ..., "mask": np.triu(np.full((1, 1, seqlen, seqlen), -1e9, np.float32), 1)},
        function=lambda x, mask: block(x, mask=mask),
        allow_unknown_sources=True,
        capture_mode="callback",
    )
```

Note the mask fixture: an **additive `-1e9` upper-triangular float mask**, consistent with the
additive-only SDPA lowering.

`ZooModelSpec` default tolerances: `atol=2e-3, rtol=5e-3`; the transformer block relaxes to
`atol=5e-2, rtol=1e-2`; the arithmetic chain to `2e-2/2e-2`.

---

## 14. Op coverage report (`docs/op_coverage.md`, regenerable)

Header lines 1-14 verbatim:

```
# mlx2coreai Op Coverage

Coverage type: CoreAI asset generation. This does not imply runtime numerical parity.

## Summary

- Supported source op names in registry: 156
- Distinct lowering keys in registry: 121
- Coverage modules: `tests.model_zoo, tests.coverage_zoo`
- Coverage graphs: 26
- Coverage graph nodes: 252
- Unique source ops exercised: 156
- Unique lowering keys exercised: 121
- Asset validation: passed
```

"Unexercised Registry Ops: **None**". Notes section (lines 212-216):

> - Coverage is asset-generation coverage, not runtime numerical parity.
> - Runtime parity requires the macOS / iOS 27+ CoreAI execution stack.
> - General transposed convolution uses a named composite fallback when the beta CoreAI asset writer
>   rejects native conv_transpose IR; the vendored 1x1 stride-1 case lowers without that fallback.

Asset validation is literally `(asset_path / "main.mlirb").exists()` after
`lower_graph_to_coreai(spec.graph, config=ConversionConfig(optimize=False))` +
`lowered.program.save_asset(...)` (`op_coverage.py:155-163`) — **not** an execution check.

JSON schema key: `"schema_version": "mlx2coreai.op_coverage.v1"`, plus a `versions` block from
`reporting.collect_versions()`:

```python
{"python": platform.python_version(),
 "coreai-core": _package_version("coreai-core"),
 "numpy": ..., "mlx": ...}     # "unavailable" if not installed
```

(`reporting.py` also defines `REPORT_SCHEMA_VERSION = "mlx2coreai.run_report.v1"`,
`build_run_context`, `init_stage_timings`, `timed_stage`, `summarize_stage_timings`, `write_json` —
none of which are wired into anything at HEAD. Dead-ish scaffolding.)

The two zoo modules:
* `tests/model_zoo.py` — 16 static builders (`linear_relu, arithmetic_chain, reduction_suite,
  shape_helpers, indexing_transforms, creation_helpers, mlp_2layer, broadcast_tensordot,
  numeric_sanity, diagonal_trace, tri_band, logical_checks, meshgrid_kron, p0_math_pack,
  stats_divmod, conv_block`) + 1 live builder (`transformer_block`). API:
  `available_model_names()`, `available_live_model_names()`, `supports_live_capture(name)`,
  `get_model_spec(name, seed=0)`, `capture_model_spec(name, seed, artifacts_dir,
  write_debug_dot=True)`.
* `tests/coverage_zoo.py` — 10 `supplemental_*` graphs whose only job is to touch every remaining
  registry alias (`CoverageModelSpec(name, description, graph)`, no numerics).

---

## 15. Gotchas, footguns, and correctness hazards

**Capture / tracer**

1. `mx.export_function` is called **once per capture**, and the function is then **executed again**
   for reference outputs. With `dynamic_axes` + probe, that's 2 traces + 2 executions. Expensive
   for large models, and any nondeterminism (dropout, RNG) diverges between the trace and the
   reference run unless `capture_is_training=False`.
2. MLX refuses to export the same signature twice from one exporter
   (`"[export_function] Attempting to export a function twice with the same signature is not
   allowed."` — `mlx/export.cpp:770-773`). mlx2coreai sidesteps this by creating a fresh exporter
   per call.
3. **`mx.log2` / `mx.log10` silently become natural log.** MLX remaps `Log2`/`Log10` to the
   primitive name `Log` and puts the base in `state()` (`Log::Base { two=0, ten=1, e=2 }`,
   `mlx/primitives.h:1316-1345`). `_primitive_attrs_from_arguments` has **no `log` branch**, so the
   base is dropped and the lowering emits `coreai.log`. The registry's `log2`/`log10` entries only
   fire for hand-written IR or the DOT path.
4. **`mx.left_shift` / `mx.right_shift` silently become bitwise AND.** MLX remaps all five bitwise
   ops to `BitwiseBinary` with `Op { And=0, Or=1, Xor=2, LeftShift=3, RightShift=4 }`
   (`mlx/primitives.h:449-455`); `_lower_bitwise_binary` maps `{0:"and",1:"or",2:"xor"}` and
   **defaults everything else to `"and"`** (`lower_to_coreai.py:989-1000`).
5. **`mx.argmax` / `mx.argmin` through the callback path are unsupported.** MLX emits the primitive
   name `ArgReduce` (`DEFINE_NAME(ArgReduce)`, no remap alias), which normalizes to `"argreduce"`
   — absent from `SUPPORTED_MLX_TO_COREAI_OPS`. Expect `UnsupportedOpsError`. (Registry entries
   `argmax`/`argmin`/`reduce_argmax` only cover the DOT path and hand-authored IR.) *Inference from
   source; not directly executed.*
6. `Softmax::state()` is **only** `precise_` — no axis. mlx2coreai therefore defaults
   `axis = -1` for every captured softmax. Fine for MLX (whose `Softmax` primitive is last-axis by
   construction) but a trap for hand-written IR.
7. Asymmetric conv padding `(pad_lo, pad_hi)` is summed into one number per axis at capture and
   re-split evenly at lowering — asymmetric padding is lost.
8. `capture_shapeless=True` does **not** by itself produce dynamic shapes: "MLX's callback export
   still reports concrete primitive shapes, even with shapeless export." You need the probe.
9. The probe path requires the two traces to be structurally identical; any shape-dependent Python
   branching in the model raises `"dynamic shape probe produced a different graph structure…"`.
10. `allow_unknown_sources=True` (the default) silently invents `TensorSpec(name, shape=(), dtype
    "fp32")` for tensors with no known spec (`from_mlx.py:456-458`) — a scalar fp32 stand-in that
    can be very wrong.

**Types / numerics**

11. `fp64 → fp32` and `int64 → int32` are forced everywhere (types *and* constants). int64
    constants outside int32 range hard-fail.
12. `bool` maps to `IntegerType.get_signless(1)`; bool constants are never externalized as
    resources.
13. `reduce_log_sum_exp` is `log(sum(exp(x)))` with **no max subtraction** → overflow risk in fp16.
14. SDPA causal masking uses `-1e4`, not `-inf`. In fp16 that is fine; in fp32 it leaves a small
    non-zero attention weight on masked positions.
15. **Boolean attention masks are added, not selected** (`scores + cast(mask, dtype)`), so a
    `True/False` mask contributes `+1/0`. Only additive float masks are correct.
16. SDPA `has_sinks` and `output_logsumexp` are captured then ignored; `mask_mode` from
    `canonicalize_sdpa_masks` is computed then never read.
17. The historical README caveat *"MLX BF16 constants are currently widened to FP32 during capture
    … expect small full-model logit drift"* (README at `5e9c7de`) was **superseded** by
    *"BF16 MLX constants are preserved as BF16 weights when `ml_dtypes` is available. Some scalar
    literals and normalization constants may still be emitted in a higher precision when the CoreAI
    type system requires it."* (README at `948a3bd`). At HEAD the code path preserves bf16
    (`_element_type` → `BF16Type`, `_np_dtype_for_ir("bf16")` → `ml_dtypes.bfloat16`), and the
    Caveats section was deleted entirely from the README in `d032a95`. **Treat any "bf16 is widened"
    claim as stale.**

**Lowering**

18. `mlx_conv_transpose` composite fallback returns **`zeros`** — the asset saves, the numbers are
    garbage. It is tagged `"fallback": "unsupported_coreai_beta_asset_writer"` so you can grep for
    it. Only 1×1/stride-1/dilation-1/groups-1/no-pad transposed convs get a real lowering.
19. Static `slice_update` materializes one index row per updated element in a baked constant —
    O(update-size) conversion time and asset bloat. Avoid for large in-place updates.
20. `split`, `var/std` with `ddof`, `tensordot`, `kron`, `meshgrid`, `diag/diagonal/trace`,
    `array_equal`, and the triangular ops all call `_static_shape()` and therefore **raise on
    dynamic dimensions** (`ValueError(f"Expected static shape, got {shape}.")`).
21. `AIProgram._from_mlir_module` is a **private** coreai API — a wheel bump can break the whole
    converter.
22. `generate_composite_decl` mutates the caller's `op_attributes` dict (adds `"version"`).
23. `_optimization_skip_reason` is a dead hook returning `None`; `optimization_skip_reason` will
    always be `None` at HEAD.
24. `_public_inputs` appends to `self.unresolved_extra_inputs` for any graph input not in
    `public_input_names` — but still keeps it as a public argument. So captured weights that MLX did
    *not* classify as constants become **required runtime inputs**, and you only learn about it from
    `metadata["unresolved_extra_inputs"]` / `extra_input_names`.

**Runtime / packaging**

25. `mlx2coreai.run_aimodel` has **no `state=`** — the library cannot run its own stateful assets.
26. Sync helpers throw inside a running event loop.
27. `compare_coreai_outputs(match_by_order=True)` will happily compare mismatched names positionally.
28. `_load_ops_statuses` reads `docs/ops_status.md`, which **does not exist** → all unsupported ops
    report status `unlisted`.
29. `convert_mlx_lm_stateful` is **batch_size=1 only**:
    `ValueError("stateful mlx-lm conversion currently supports batch_size=1 only.")`.
30. `_ExportableLayeredKVCache.make_mask` raises
    `NotImplementedError("stateful KV-cache export does not support sliding-window masks yet.")` —
    so **sliding-window / SWA models (Gemma-style, Mistral SWA) cannot be converted** by the
    stateful path.
31. `_apply_model_compute_precision` calls `model.set_dtype(...)` — it mutates the model you loaded.
32. `--cast-bf16-logits-to-fp16` defaults on and the Swift runner hard-codes `Float16` logits;
    turning the flag off breaks the Swift backend's `greedyToken`.
33. `_write_tokenizer` does `shutil.rmtree(dest)` on an existing `bundle/tokenizer` directory —
    destructive re-run.
34. The Swift backend is auto-selected on Darwin whenever an Xcode-beta SDK exists, which silently
    changes sampling semantics (greedy only, no tokenizer, no JSON output). Use
    `--runtime-backend python` to force the Python path (the flag is `argparse.SUPPRESS`-hidden).
35. Python vs Swift state-capacity differ by one (`steps` vs `steps + 1`) under `--grow-context`.

---

## 16. Version / platform gates (explicit strings found in the repo)

* `requires-python = ">=3.11"`; the code uses 3.10+ syntax (`X | Y`, `match`-free), `slots=True`
  dataclasses, and `zip(..., strict=True)` (3.10+).
* `coreai-core==1.0.0b1` — exact pin.
* `ConversionConfig.min_runtime_target = "macOS27"` (metadata only).
* Swift: `-target arm64-apple-macos27.0`, `-framework CoreAI`, SDK must contain
  `System/Library/Frameworks/CoreAI.framework`; default path
  `/Applications/Xcode-beta.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`.
* `docs/op_coverage.md`: *"Runtime parity requires the macOS / iOS 27+ CoreAI execution stack."*
* Commit titles `Fix runtime on macOS 27.` / `Allow optimization on SDPA for macOS 27.` confirm the
  target OS.

---

## 17. Cross-links to other parts of the stack

* **`apple/coreai-models`** — mlx2coreai's stateful path is a deliberate MLX-side clone of the macOS
  LLM export recipe:
  * `export/_constants.py`: `KEY_CACHE_NAME="keyCache"`, `VALUE_CACHE_NAME="valueCache"`,
    `QUANT_TRACE_QUERY_LEN=16`, `QUANT_TRACE_OFFSET=8`, `TRACE_KV_CACHE_SEQ_LEN=2048`
    — mlx2coreai uses 16/8 and the same names.
  * `primitives/macos/cache.py:52-53` — cache shape `(n_layers, 1, n_kv_heads, max_seq_len,
    head_dim)`, `seq_len_dim() == 3` — identical to `_make_state_specs`.
  * `export/bundle.py:48-68` — the `metadata_version 0.2` LLM bundle schema mlx2coreai reproduces
    (only `source.model_definition` differs: `"mlx"` vs `"torch"`).
  * `export/macos.py:106-121` — the torch-export dynamic-shape recipe (`seq_ids`, `seq_pos`,
    `k_seq_len`, `v_seq_len`) that mlx2coreai's probe-based dynamic axes emulate.
* **`ml-explore/mlx`** — `mlx/export.cpp` (callback tracer, `PrimitiveFactory`, `name_remap`),
  `mlx/primitives.h` (`Reduce`, `ArgReduce`, `Softmax`, `BitwiseBinary`, `Log` state tuples),
  `mlx/fast_primitives.h` (`RMSNorm`, `RoPE`, `ScaledDotProductAttention` state tuples),
  `mlx/fast.cpp:530-557` (rope input ordering / `base=1.0` when `freqs` is given),
  `python/tests/test_export_import.py:501-537` (the callback contract test).
* **`mlx-lm`** — the cache protocol (`update_and_fetch`, `make_mask`, `size`, `empty`, `.offset`)
  that `_ExportableLayeredKVCache` duck-types, and `mlx_lm.load(model_id, lazy=, revision=)`.
* **`apple/coreai-optimization` (`coreai_opt`)** — the natural place quantization/palettization would
  plug in; mlx2coreai has **none** today.
* **`1amageek/swift-lm`** — an independent Swift+Python CoreAI export stack (`CoreAIExport/`,
  `swiftlm_coreai/program.py`) that also builds `AIProgram`s; useful contrast for the same problem.
* **Core AI Swift framework** — the Swift runner in this repo is one of the few concrete samples of
  `AIModel` / `InferenceFunction.MutableViews` / `NDArrayDescriptor.resolvingDynamicDimensions`
  usage.

---

## 18. Source inventory (everything actually read this session)

In `repos/lucasnewman__mlx2coreai/`:
* `README.md` (86 L, HEAD) — plus historical versions via `git show 5e9c7de:README.md` and
  `git show 948a3bd:README.md`
* `pyproject.toml`, `LICENSE` (head), `.gitignore`
* `mlx2coreai/__init__.py`, `__main__.py`, `ir.py`, `conversion.py`, `cli.py`, `from_mlx.py`,
  `op_registry.py`, `lower_to_coreai.py` (both halves), `passes.py`, `dynamic_shapes.py`,
  `_composite_declaration.py`, `_convert_mlx_lm.py`, `_convert_mlx_lm_stateful.py`, `runtime.py`,
  `op_coverage.py`, `reporting.py`
* `docs/op_coverage.md`
* `scripts/benchmark_aimodel_sampling.py`, `scripts/benchmark_aimodel_sampling_coreai.swift`
* `tests/conftest.py`, `test_lower_to_coreai_smoke.py`, `test_convert_mlx_lm.py`, `test_runtime.py`,
  `test_op_coverage.py`, `test_op_coverage_report.py`, `test_mlx2coreml_zoo_assets.py`,
  `model_zoo.py` (lines 1-200, 204-320, 875-1122), `coverage_zoo.py` (lines 1-80, 150-300)
* `git log --oneline -50`; `git show 059c9f3`, `git show 5e9c7de`, `git show dab7096`,
  `git show --stat d032a95 948a3bd 94bd2b9`

Cross-repo (same project root, `repos/`):
* `ml-explore__mlx/mlx/export.cpp` (lines 40-55, 273-340, 381-460, 495-560, 660-790)
* `ml-explore__mlx/mlx/primitives.h` (`ArgReduce` 354-379, `BitwiseBinary` 449-459, `Log` 1316-1345,
  `Reduce` 1777-1818, `Softmax` 2159-2176)
* `ml-explore__mlx/mlx/fast_primitives.h` (`RMSNorm` ~60-95, `RoPE` 159-204,
  `ScaledDotProductAttention` 207-263)
* `ml-explore__mlx/mlx/fast.cpp` (lines 368-430, 530-565)
* `ml-explore__mlx/python/tests/test_export_import.py` (lines 495-540)
* `apple__coreai-models/python/src/coreai_models/export/_constants.py`
* `apple__coreai-models/python/src/coreai_models/export/bundle.py`
* `apple__coreai-models/python/src/coreai_models/export/macos.py` (lines 60-140, 234-260)
* `apple__coreai-models/python/src/coreai_models/primitives/macos/cache.py` (lines 28-65)
* `apple__coreai-models/python/src/coreai_models/vlm/export.py` (grep: `KV_STATE_NAMES`)

---

## 19. Open questions / unverified

1. **Nothing here was executed.** `coreai-core` is not installed in this environment
   (`import coreai` fails), and there is no macOS 27 SDK to compile the Swift runner. Every claim is
   read from source. Actual `.aimodel` layout, `main.mlirb` contents, and runtime behavior are
   unverified by execution.
2. The exact `coreai-core==1.0.0b1` Python signatures (`GraphOp(...)` kwargs, `coreai.slice_`
   argument order, `NDArray(data=, backing=)`, `function(inputs=, state=)`,
   `function.desc.state_descriptor(name=)`) are inferred from call sites only. Needs confirmation
   against the wheel.
3. Whether Core AI's Python `function(inputs=, state=)` mutates the passed `NDArray`s in place or
   returns new state is **not observable from this repo** — the benchmark reuses the same `state`
   dict across steps, which implies in-place, but the API contract is unstated.
4. Gotcha #5 (`mx.argmax` → `ArgReduce` unsupported) and #3/#4 (log-base and shift collapse) are
   derived by reading MLX's `name_remap` + mlx2coreai's tables; they are **not** covered by any test
   in the repo. Worth an actual repro.
5. `docs/ops_status.md` is referenced by `op_registry._load_ops_statuses` but absent. Was it deleted,
   or never written?
6. `reporting.py`'s `build_run_context` / `timed_stage` / `REPORT_SCHEMA_VERSION
   "mlx2coreai.run_report.v1"` are unused at HEAD — leftovers from a removed reporting harness (the
   earlier benchmark script at `dab7096` was 443 lines and had `--storage-kind`,
   `--compute-unit`, `--debug-specialization`).
7. `capture_mode="dot"` is still reachable via `ConversionConfig(capture_mode="dot")` but no test
   exercises it end-to-end; its attribute coverage is far thinner than callback mode.
8. Multi-entrypoint lowering (`build_coreai_programs`) is tested but unused by any converter — is a
   prefill/decode split planned for the LLM path?
9. Does the Core AI beta still reject `coreai.conv_transpose2d`? The composite fallback is still in
   the code at HEAD, but the SDPA-optimizer workaround was removed one commit earlier, so beta
   behavior is clearly moving.
10. `min_runtime_target="macOS27"` is never enforced or written into the asset's own
    `metadata.json` — is there a Core AI API for declaring a deployment target that this repo isn't
    using?
