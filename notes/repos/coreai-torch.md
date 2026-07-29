# apple/coreai-torch — deep-dive research notes

> Research notes for guide authoring. Everything below is grounded in files read in
> this session from the local clone at
> `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-torch`
> (git `main`, HEAD = `4529671` "Remove run_transforms helper in favor of result.optimize() (#50)",
> package version `0.4.1`).
> Anything I could not verify from source is marked **UNVERIFIED**.

---

## 0. TL;DR / What this repo is

`coreai-torch` is Apple's **PyTorch → Core AI IR** converter package (Python, BSD-3-Clause).
It walks a `torch.export.ExportedProgram`'s FX graph node-by-node and emits MLIR in the
`coreai` dialect, producing a `coreai.authoring.AIProgram` which is then saved as an
`.aimodel` asset directory and executed by `coreai.runtime`.

Repo README, line 3 (verbatim):

> Core AI PyTorch Extensions (`coreai-torch`) is a Python package that bridges PyTorch and Core AI.
> Use it to bring up an existing PyTorch model into Core AI IR, or to author Core AI models directly
> from PyTorch by composing the built-in composite op library (`coreai_torch.composite_ops`),
> authoring new ops via `register_torch_lowering`, and authoring inline Metal GPU kernels via
> `TorchMetalKernel`. The resulting IR can be compiled and executed efficiently by the Core AI
> inference stack.

**Important naming note:** there is *no* `convert()` function in this package. The entry point is
the `TorchConverter` **class** (`add_exported_program` / `add_pytorch_module` → `to_coreai()`).
The `.aimodel` file is produced by `AIProgram.save_asset(path)` from `coreai-core`, not by
coreai-torch itself.

---

## 1. Repository layout (verbatim `find` output, `.git` excluded)

```
./LICENSE
./.pre-commit-config.yaml
./CODEOWNERS
./pyproject.toml
./MANIFEST.in
./README.md
./.gitignore
./CONTRIBUTING.md
./.python-version
./.license-header.txt
./coreai_torch/_torch_metal_kernel.py
./coreai_torch/_decomp.py
./coreai_torch/converter.py
./coreai_torch/__init__.py
./coreai_torch/__version__.py
./coreai_torch/_custom_to_core.py
./coreai_torch/_debug_locations.py
./coreai_torch/_validate.py
./coreai_torch/py.typed
./coreai_torch/_type_mapping.py
./coreai_torch/externalize.py
./coreai_torch/_composite_declaration.py
./coreai_torch/_aten_to_core.py
./coreai_torch/_utils.py
./coreai_torch/debugging/{validator,benchmarker,comparator,search_strategy,graph,graph_diff,inspector,__init__,debug_info,torch_utils}.py
./coreai_torch/composite_ops/{_gated_delta_update,_gather_mm,_rope,__init__,_sdpa,_rms_norm,_utils}.py
./coreai_torch/_compression/{_types,custom_layers,_intx,__init__,_floatx,utils}.py
./tests/... (conftest.py, utils.py, test_converter.py, test_externalize.py, test_stateful.py,
             test_validate.py, test_debug_locations.py, test_get_module_hierarchy.py,
             test_lower_simple_model.py, test_docs.py,
             debugging/, composite_ops/, compression/, api/, ops/, subgraph/, dsl/)
./tools/graphdiff/{graphdiff.py,README.md}
./tools/freqop/{freqop.py,README.md}
./scripts/{release.sh,smoke_test_wheel.sh}
./docs/{index.md,faq.md,whats-new.md,release-notes.md,resources.md,contributing.md,conf.py,deploy.sh}
./docs/getting-started/{installation.md,quickstart.ipynb}
./docs/guides/{conversion-workflows,custom-op-lowering,custom-metal-kernels,composite-ops,externalization}.ipynb
./docs/api/{TorchConverter.md,composite-ops.md,supported-aten-ops.md,TorchMetalKernel.md,
            generate-composite-decl.md,debugging.md,ExternalizeSpec.md}
./docs/api/composite-ops/{module-class,aten-derived,rope,batch-norm,rms-norm,layer-norm,sdpa,
                          instance-norm,linalg-vector-norm,pixel-shuffle,hard-sigmoid,group-norm,
                          gather-mm,gated-delta-update,log-softmax}.md
./docs/coreai-core/{index.md,api/coreai.md,tutorials/run-an-aimodel.ipynb,tutorials/construct-a-graph.ipynb}
./.github/workflows/ci.yml
```

Line counts (largest first): `tests/test_externalize.py` 3790, `coreai_torch/_aten_to_core.py` 3741,
`coreai_torch/_utils.py` 1964, `tests/test_stateful.py` 1470, `coreai_torch/_debug_locations.py` 1388,
`coreai_torch/debugging/graph_diff.py` 1371, `coreai_torch/debugging/torch_utils.py` 1265,
`tools/graphdiff/graphdiff.py` 1237, `coreai_torch/debugging/benchmarker.py` 1169,
`coreai_torch/converter.py` 1082, `tests/test_converter.py` 1082.

There is **no** `AGENTS.md` / `CLAUDE.md` in this repo.

---

## 2. Versions, requirements, dependency constraints

From `pyproject.toml` (verbatim, lines 5–59):

```toml
[project]
name = "coreai-torch"
dynamic = ["version"]
description = "Convert PyTorch models to CoreAI format"
requires-python = ">=3.11"
dependencies = [
    "coreai-core==1.0.0b2",
    "ml-dtypes",
    "networkx",
    "numpy",
    "packaging",
    "scipy",
    "sympy",
    "torch>=2.8.0",
    "typing-extensions",
    "strenum",
    "rich>=13.0,<16.0",
]

[project.optional-dependencies]
test = [
    "coremltools", "filecheck",
    "mlx; sys_platform == 'darwin'", "mlx_lm; sys_platform == 'darwin'",
    "pytest", "pytest-asyncio", "pytest-randomly", "pytest-rerunfailures",
    "pytest-sugar", "pytest-xdist",
    "torch==2.13.0", "torchaudio==2.11.0", "torchvision==0.28.0",
    "transformers==4.57.3",
]
docs = ["sphinx>=7.0", "shibuya==2026.5.19", "myst-nb>=1.0", "nbmake>=1.5.0",
        "ghp-import>=2.1.0", "nest-asyncio>=1.5.0"]
dev = ["deptry>=0.20", "nbstripout", "pre-commit>=4.0", "ruff>=0.12.0"]
```

Key facts:
- **`coreai-core==1.0.0b2`** is an exact pin (beta 2). `coreai-torch` version = **0.4.1**
  (`coreai_torch/__version__.py`).
- Runtime allows **torch >= 2.8.0** with *no* upper bound, but the package warns above 2.13.0.
  `coreai_torch/__init__.py:32-39`:
  ```python
  _TORCH_MAX_VERSION = "2.13.0"

  if _Version(_torch_version) > _Version(_TORCH_MAX_VERSION):
      _warnings.warn(
          f"coreai-torch has only been validated with torch<={_TORCH_MAX_VERSION}; "
          f"found torch {_torch_version}. Some functionality may not work as expected.",
          stacklevel=2,
      )
  ```
  (Introduced in commit `ef1181b` "Allow newer versions of PyTorch than we have verified. (#39)".)
- Tests pin `torch==2.13.0`, `torchvision==0.28.0`, `torchaudio==2.11.0`, `transformers==4.57.3`.
- `.python-version` = `3.11`. Wheel smoke test covers `3.11,3.12,3.13`
  (`scripts/smoke_test_wheel.sh`, `PYTHON_VERSIONS="3.11,3.12,3.13"`).
- `ruff` config: `target-version = "py311"`, `select = ["E","F","I","W"]`, `ignore = ["E501"]`,
  `known-first-party = ["coreai_torch"]`.
- CI (`.github/workflows/ci.yml`) runs on **self-hosted `[self-hosted, macos, tahoe, ARM64]`**
  runners (macOS "Tahoe" = macOS 26/27 line; Apple Silicon only). Test command:
  `uv run --extra test pytest tests/ -n auto -m "not slow and not dsl"` (timeout 60 min).
  Lint job: `uv run --extra dev ruff check .` + `ruff format --check .` (timeout 15 min).
- deptry maps `coreai-core` distribution → `coreai` import name
  (`package_module_name_map = { "coreai-core" = "coreai" }`).

### pytest markers (from `[tool.pytest.ini_options]`)

```toml
asyncio_mode = "auto"
addopts = ["--tb=short", "--ff"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "dsl: marks Metal DSL kernel tests (macOS only)",
    "composite: marks composite operation tests (require MLX + transformers)",
    "compression: marks compression/quantization tests",
    "ops: marks core operator tests",
    "ir: marks tests that verify CoreAI IR output via filecheck",
]
```
Plus a `control_flow` marker used in `tests/ops/test_ops.py` (auto-skipped on non-interpreter
compute units — see §12).

---

## 3. Public API surface (`coreai_torch/__init__.py`, verbatim)

```python
"""coreai-torch: Convert PyTorch models to Core AI format."""

import warnings as _warnings

# Re-export MetalParameter so users don't need a separate coreai import.
from coreai.authoring import MetalParameter
from packaging.version import Version as _Version
from torch import __version__ as _torch_version

from .__version__ import __version__
from ._composite_declaration import generate_composite_decl
from ._decomp import get_decomp_table
from ._torch_metal_kernel import TorchMetalKernel
from .converter import TorchConverter
from .externalize import ExternalizeSpec

__all__ = [
    "__version__",
    "ExternalizeSpec",
    "MetalParameter",
    "TorchConverter",
    "TorchMetalKernel",
    "get_decomp_table",
    "generate_composite_decl",
]
```

Second public module: `coreai_torch.composite_ops`:

```python
from ._gated_delta_update import GatedDeltaUpdate
from ._gather_mm import GatherMM
from ._rms_norm import RMSNorm, RMSNormImpl
from ._rope import RoPE
from ._sdpa import SDPA

__all__ = ["GatherMM", "GatedDeltaUpdate", "RMSNorm", "RMSNormImpl", "RoPE", "SDPA"]
```

Third (semi-public, documented in `docs/api/debugging.md` but with **no `__all__`** —
`coreai_torch/debugging/__init__.py` contains only the license header):
`coreai_torch.debugging.{validator, comparator, inspector, benchmarker, graph, graph_diff,
search_strategy, debug_info, torch_utils}`.

Underscore-prefixed but **used directly in the official docs & tests**:
`coreai_torch._utils.get_operand`, `get_operands`, `get_promoted_type`, `print_graph`;
`coreai_torch._compression.utils.inject_subbyte_tensors`;
`coreai_torch._compression.custom_layers` (import registers the `coreai::*` torch ops).

---

## 4. `TorchConverter` — full API

File: `coreai_torch/converter.py`.

### 4.1 Constructor & `Mode`

```python
class TorchConverter:
    class Mode(Enum):
        """Controls the level of debug information embedded in the converted asset.

        Attributes:
            RELEASE: Lightweight mode that records only operation IDs without
                stack traces.
            DEBUG: Includes full torch stack traces for comprehensive source
                mapping and debugging.
        """
        DEBUG = "debug"
        RELEASE = "release"

    def __init__(self, *, mode: "TorchConverter.Mode" = Mode.DEBUG) -> None:
```
- `mode` is **keyword-only**, defaults to `Mode.DEBUG` (full torch stack traces embedded).
- `docs/api/TorchConverter.md` documents the constructor as bare `TorchConverter()` — the `mode`
  parameter is **undocumented in the API md** (gap).
- Docstring: *"Reusable state (custom op lowerings) is retained across calls to `to_coreai()`.
  Per-conversion transient state is reset each time."*
- Also from the docstring: *"Call `coreai_torch.debugging.debug_info.strip_debug_info` to remove
  debug metadata from an already-converted program."*

### 4.2 `add_exported_program`

```python
def add_exported_program(
    self,
    exported_program: ExportedProgram,
    *,
    input_names: Sequence[str] | None = None,
    output_names: Sequence[str] | None = None,
    state_names: Sequence[str] | None = None,
    entrypoint_name: str = "main",
) -> Self:
```
**Note the `*`**: all naming params are **keyword-only** in the source, even though
`docs/api/TorchConverter.md` shows them positionally. Guide code must use keywords.

Behavior (source order):
1. Raise `ValueError` if `entrypoint_name` already staged
   (`"A program with entrypoint_name={...!r} is already staged. Each staged program must have a unique entrypoint_name."`).
2. `inject_subbyte_tensors(exported_program)` — promotes uint8 compression constants to sub-byte.
3. `validate_exported_program(exported_program, self._user_defined_torch_lowering)`.
4. Append a `_StagedEntry`. Returns `self`.

Docstring on names:
> `input_names`: Non-stateful forward() arg names only.
> `output_names`: Return value names only (not mutation outputs).
> `state_names`: One name per state, applied to both input and mutation output. Order: buffers
> (registration order), then mutated user inputs (signature order). Defaults to FX placeholder
> names when not provided.

`docs/api/TorchConverter.md` flags a **Breaking change** for `input_names`/`output_names`:
"previously this covered all graph inputs / all graph outputs".

### 4.3 `add_pytorch_module`

```python
def add_pytorch_module(
    self,
    model: torch.nn.Module,
    *,
    export_fn: Callable[[torch.nn.Module], ExportedProgram],
    externalize_modules: list[type | ExternalizeSpec] | None = None,
    input_names: Sequence[str] | None = None,
    output_names: Sequence[str] | None = None,
    state_names: Sequence[str] | None = None,
    entrypoint_name: str = "main",
) -> Self:
```
- `export_fn` is **keyword-only and required** (docs show it positional — wrong).
- Runs `export_fn(model)` **eagerly** inside `add_pytorch_module`; on exception re-raises:
  ```python
  raise RuntimeError(
      f"Your model failed to export: {e}\n"
      f"Ensure the model is exportable via torch.export before "
      f"passing it to TorchConverter.add_pytorch_module."
  ) from e
  ```
- **Gotcha:** `inject_subbyte_tensors(ep)` is called **only when `externalize_modules` is falsy**:
  ```python
  if not externalize_modules:
      inject_subbyte_tensors(ep)
  ```
  When externalizing, injection happens later on the *re-exported* whole program inside
  `_run_externalize_pipeline`.
- Model is **not mutated**: externalization patches are always restored in a `finally`
  (verified by `tests/test_externalize.py::test_model_not_mutated_after_convert`).

### 4.4 `to_coreai`

```python
def to_coreai(self, *, entrypoints: Sequence[str] | None = None) -> AIProgram
```
- Filters staged entries by `entrypoint_name` when `entrypoints` is given.
- Raises `RuntimeError("No programs to convert. Call add_exported_program() or add_pytorch_module() first.")`
  if nothing matches.
- Prints a rich banner: `f"[bold cyan]coreai-torch[/] [dim]{__version__}[/]: converting {len(entries)} program(s) to Core AI"`.
- Creates a single MLIR `Module.create()`, iterates entries, calls `_get_graph_op(entry.entrypoint_name, primary_entrypoint=True)`.
- Returns `AIProgram._from_mlir_module(module)`.
- **Staged programs persist after conversion** — call `clear()` to remove them.

### 4.5 `clear`

```python
def clear(self, *, entrypoints: Sequence[str] | None = None) -> None
```
"Remove staged programs. If entrypoints given, remove only those; else remove all.
Custom lowerings are always preserved."

### 4.6 `register_torch_lowering`

```python
def register_torch_lowering(
    self: Self,
    qualified_name: str,
    allow_override: Optional[bool] = False,
) -> Callable
```
Decorator. Decorated function signature: `(values_map: dict[str, Value], node: fx.Node, loc: Location) -> Value | list[Value]`.

Validation inside the decorator:
- `qualified_name` must split into exactly 2 non-empty parts on `"::"` else
  `ValueError(f"qualified_name must be 'namespace::op_name', got {qualified_name!r}")`.
- Reserved namespaces map (only checked when `allow_override` is falsy):
  ```python
  _reserved = {
      "aten": _aten_to_core_resolver,
      "higher_order": _higher_order_resolver,
      "coreai": _custom_to_core_resolver,
      "coreaix": _custom_to_core_resolver,
  }
  ```
  → `ValueError(f"{qualified_name!r} is already registered; set allow_override=True to replace it")`.
- Registration is **per-`TorchConverter` instance**; the global resolver dicts are never mutated
  (asserted by `tests/test_converter.py::test_override_aten_add_does_not_mutate_resolver`).

**Dispatch precedence in `_handle_call_function_op`** (converter.py:657–740), in order:
1. `node.name in self._externalized_lowerings` (per-node externalized submodule invoke)
2. `qualified_target in self._user_defined_torch_lowering` where `qualified_target = f"{namespace}::{target}"`
3. `namespace is None or namespace == "aten"` → `_aten_to_core_resolver[target]`, else
   `ValueError(f"Unsupported ATen op: {target}. Use register_torch_lowering() to provide a custom lowering.")`
4. `namespace in ("coreai", "coreaix")` → `_custom_to_core_resolver[variantless_target]`
5. `namespace == "higher_order"` → `_higher_order_resolver[target]` (called with
   `graph_module=self.exported_program.graph_module` kwarg, **not** `loc`)
6. else `ValueError(f"unable to handle call function op: target: {target}, namespace: {namespace}")`

Multiple results are stored as `values_map["<node.name>#<i>"]`; a single result as `values_map[node.name]`.
Every result is type-checked against `node.meta["val"]` via `check_result_type`.

### 4.7 `register_custom_kernels`

```python
def register_custom_kernels(self: Self, kernels: Sequence[TorchMetalKernel]) -> Self
```
For each kernel it registers `register_torch_lowering(f"coreai_metal_kernels::{kernel.name}.default")`.
Scalar args are converted with `scalar_constant(scalar_type, arg)` (bypasses fp16 promotion);
tensor args with `get_operand(values_map, node, idx)`. Then calls
`kernel._construct_kernel_op(input_values, get_result_types(node))`.
**Must be called BEFORE `add_exported_program()`** (docs + tests always do this order).

### 4.8 `__repr__`

```
TorchConverter(
  programs:
    main: ExportedProgram ['x'] -> ['y'], externalize=['Inner']
  custom_lowerings: ['my_lib::my_op.default']
)
```
(kind is `"nn.Module"` when `entry.module is not None` else `"ExportedProgram"`.)

### 4.9 Internal `Context`

```python
class Context(_CoreAIAuthoringContext):   # coreai.authoring.Context
    def __init__(self) -> None:
        super().__init__()
        self._location: Location = Location.unknown(self._mlir_context)
```
`TorchConverter.context` is this object; `to_coreai()` does `with self.context, _ProgressBar() as bar:`.

---

## 5. Canonical usage snippets (copyable)

### 5.1 ExportedProgram path (README lines 45–60, verbatim)

```python
import torch
from coreai_torch import TorchConverter, get_decomp_table

model = ...  # your nn.Module
model.eval()

# Export and decompose — this is your responsibility
ep = torch.export.export(model, args=(torch.randn(1, 3, 224, 224),))
ep = ep.run_decompositions(get_decomp_table())

# Convert to Core AI IR
converter = TorchConverter().add_exported_program(ep)
coreai_program = converter.to_coreai()
coreai_program.optimize()
```

### 5.2 nn.Module path (README lines 66–82, verbatim)

```python
import coreai_torch
from coreai_torch import TorchConverter

model = ...  # your nn.Module
model.eval()
sample = (torch.randn(1, 3, 224, 224),)

converter = TorchConverter().add_pytorch_module(
    model,
    export_fn=lambda m: torch.export.export(m, args=sample).run_decompositions(
        coreai_torch.get_decomp_table()
    ),
)
coreai_program = converter.to_coreai()
coreai_program.optimize()
```

### 5.3 Full save → load → run (from `docs/getting-started/quickstart.ipynb`, cell 12, verbatim)

```python
import tempfile
from pathlib import Path

import numpy as np
import torch
from coreai.runtime import NDArray


async def compile_and_run(coreai_program, example_input, model):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Compile: save the AIProgram to an .aimodel directory on disk.
        asset = coreai_program.save_asset(Path(tmpdir) / "quick_start_example.aimodel")

        # Load: open the executable and bind the `main` function.
        async with asset.executable() as ai_model:
            function = ai_model.load_function("main")

            # Run: invoke the function on the example input.
            coreai_outputs = await function({"x": NDArray(example_input[0])})

            # Compare with PyTorch: run the same input through the original model.
            with torch.no_grad():
                pytorch_output = model(example_input[0])

            coreai_output = coreai_outputs["out"].numpy()
            pytorch_numpy = pytorch_output.numpy()

            print(f"PyTorch output shape: {pytorch_numpy.shape}")
            print(f"Core AI output shape: {coreai_output.shape}")
            print(
                f"Outputs match: {np.allclose(pytorch_numpy, coreai_output, atol=1e-4)}"
            )


await compile_and_run(coreai_program, example_input, model)
```

### 5.4 MobileNetV2 (quickstart cell 14, verbatim)

```python
import torch
import torchvision.models as tv_models

model = tv_models.mobilenet_v2(weights=None).eval()
example_input = (torch.randn(1, 3, 224, 224),)

exported = torch.export.export(model, args=example_input)
exported = exported.run_decompositions(get_decomp_table())

coreai_program = (
    TorchConverter()
    .add_exported_program(
        exported,
        input_names=["image"],
        output_names=["logits"],
    )
    .to_coreai()
)
coreai_program.optimize()
```
Note: `torchvision` is **not** a dependency; the quickstart says `pip install torchvision`.

### 5.5 Multi-function (multi-entrypoint) model — from `tests/test_converter.py::TestMultiGraphChaining`

```python
coreai_program = (
    TorchConverter()
    .add_exported_program(add_model, input_names=["x", "y"],
                          output_names=["added"], entrypoint_name="add")
    .add_exported_program(mul_model, input_names=["a", "b"],
                          output_names=["muled"], entrypoint_name="mul")
    .to_coreai()
)
```
Resulting IR contains two graphs:
```
coreai.graph @add(... {coreai.name = "x"} ... {coreai.name = "y"}) -> (... {coreai.name = "added"})
coreai.graph @mul(... {coreai.name = "a"} ... {coreai.name = "b"}) -> (... {coreai.name = "muled"})
```
You can also mix `add_exported_program` and `add_pytorch_module` on one converter
(`test_chaining_exported_program_and_pytorch_module`).

Selective conversion: `converter.to_coreai(entrypoints=["encoder"])`.
Unknown entrypoint → `RuntimeError` (test `test_selective_conversion_unknown_entrypoint_raises`).

---

## 6. `result.optimize()` — the optimization step

**Every documented example calls `coreai_program.optimize()` after `to_coreai()`.**
`to_coreai()` is a **pure conversion step** — no optimization passes run
(`tests/test_converter.py::TestConvertToCoreaiNoOptimization`).

Evidence — cast-chain test (`test_cast_chain_preserved_until_optimize`):
```python
coreai_program = TorchConverter().add_exported_program(program).to_coreai()
# BEFORE optimize:
#   coreai.cast %{{.*}} : tensor<3x4xsi32> to tensor<3x4xf32>
#   coreai.cast %{{.*}} : tensor<3x4xf32> to tensor<3x4xf16>
coreai_program.optimize()
# AFTER optimize:
#   CHECK-NOT: coreai.cast %{{.*}} : tensor<3x4xsi32> to tensor<3x4xf32>
#   CHECK:     coreai.cast %{{.*}} : tensor<3x4xsi32> to tensor<3x4xf16>
```

### 6.1 What `optimize()` replaced (the pass catalog)

HEAD commit `4529671` "Remove run_transforms helper in favor of result.optimize() (#50)" deleted
this helper from `tests/utils.py`. The removed code (from `git show 4529671`) is the best available
enumeration of the passes `AIProgram.optimize()` now wraps:

```python
from coreai._compiler._transforms import GlobalOptions, PassEntry, apply_passes
from coreai._compiler._transforms.passes import CorePasses
from coreai.authoring import AIProgram

async def run_transforms(coreai_program: AIProgram) -> None:
    """Run essential transformation passes."""
    await apply_passes(
        coreai_program._mlir_module,
        passes=[
            PassEntry.get(CorePasses._CORE_OPTIMIZE),
            PassEntry.get(CorePasses._UPDATE_SIGNATURE_TO_HANDLES),
            PassEntry.get(CorePasses._PROPAGATE_HANDLE_UPDATES),
        ],
        options=GlobalOptions(Path()),
    )
```
Migration in the same commit: `await run_transforms(result)` → `result.optimize()` (synchronous,
not awaited).

**Pass catalog (from `coreai._compiler._transforms.passes.CorePasses`, all private/underscored):**
| Pass | Purpose (inferred from usage) |
|---|---|
| `CorePasses._CORE_OPTIMIZE` | Core dialect optimization (const folding, cast fusion, inlining of non-`noinline` graphs) |
| `CorePasses._UPDATE_SIGNATURE_TO_HANDLES` | Rewrites stateful graph signature to handle-based state (mutation outputs become tokens) |
| `CorePasses._PROPAGATE_HANDLE_UPDATES` | Propagates the handle updates through the module |
The full `CorePasses` enum could not be enumerated (coreai-core is not installed locally) — **UNVERIFIED beyond the three above.**

### 6.2 Const-folding hook (escape hatch)

`tests/test_converter.py::test_const_folding_hook_prevents_cast_folding`:
```python
from coreai._compiler._mlir_libs._coreaiIR._bindings.mlir.dialects.coreai import (
    register_should_const_folding_hook,
)

coreai_program = TorchConverter().add_exported_program(program).to_coreai()
register_should_const_folding_hook(
    callable=lambda op: op.name != "coreai.cast",
    context=coreai_program._mlir_module.context,
)
coreai_program.optimize()
# Now both survive:
#   coreai.constant dense<7> : tensor<1xsi32>
#   coreai.cast %{{.*}} : tensor<1xsi32> to tensor<1xf32>
```

### 6.3 When optimize is required

`tests/utils.py::_export_and_convert` runs optimize when
`run_optimize_passes or state_names or has_state` where
`has_state = bool(sig.buffers_to_mutate) or bool(sig.user_inputs_to_mutate)` — i.e. **stateful
models must be optimized** before the runtime state protocol works (mutation outputs become tokens
after optimize; see `_compare_by_name` comment: *"state mutation outputs become tokens after
optimize and won't appear here"*).

---

## 7. `get_decomp_table()` and the decomposition contract

File `coreai_torch/_decomp.py` (whole list, verbatim):

```python
_COMPOSITE_OPS: list = [
    torch.ops.aten.hardsigmoid.default,
    torch.ops.aten.hardswish.default,
    torch.ops.aten.instance_norm.default,
    torch.ops.aten.pixel_shuffle.default,
    torch.ops.aten.reflection_pad1d.default,
    torch.ops.aten.reflection_pad2d.default,
    torch.ops.aten.reflection_pad3d.default,
    torch.ops.aten.replication_pad1d.default,
    torch.ops.aten.replication_pad2d.default,
    torch.ops.aten.replication_pad3d.default,
    torch.ops.aten.scaled_dot_product_attention.default,
    torch.ops.aten.silu.default,
]

def get_decomp_table() -> dict:
    table = torch.export.default_decompositions()
    for op in _COMPOSITE_OPS:
        table.pop(op, None)
    return table
```
- Returns a **fresh copy each call** (mutating it doesn't affect other callers) —
  tested by `test_returns_independent_copy`.
- Split per the docstring: *composite ops* = `hardsigmoid`, `instance_norm`, `pixel_shuffle`,
  `scaled_dot_product_attention`; *direct lowerings* = `hardswish`,
  `reflection_pad{1,2,3}d` (→ `coreai.pad` reflect), `replication_pad{1,2,3}d`
  (→ `coreai.pad` replicate), `silu`.
- The pad entries were added by commit `45a231f` "do not decompose pad op (#29)".
- **Gotcha:** using the raw `torch.export.default_decompositions()` instead can make conversion
  *fail*: `test_add_pytorch_module_full_table_decomposes_instance_norm` expects
  `pytest.raises(ValueError, match="unsupported ATen ops")` because full decomposition of
  `instance_norm` produces `_native_batch_norm_legit` which has no lowering.

### 7.1 Pre-conversion validation (`coreai_torch/_validate.py`)

`validate_exported_program(ep, user_lowerings)` raises `ValueError` in two shapes:

```python
raise ValueError(
    f"The exported program contains non-decomposed ops: {ops_list}. "
    f"Please call run_decompositions() on your ExportedProgram before "
    f"passing it to TorchConverter. Example:\n"
    f"  ep = ep.run_decompositions(coreai_torch.get_decomp_table())"
)
```
```python
raise ValueError(
    f"The exported program contains unsupported ATen ops: {ops_list}. "
    f"Use register_torch_lowering() to provide a custom lowering for "
    f"these ops."
)
```
Ops skipped by the validator:
- everything in `_COMPOSITE_OPS`
- assertion ops that `preprocess_graph()` strips:
  ```python
  {torch.ops.aten._assert_async.msg,
   torch.ops.aten._assert_scalar.default,
   torch.ops.aten.sym_constrain_range_for_size.default,
   torch.ops.aten.sym_constrain_range.default,
   torch.ops.aten._assert_tensor_metadata.default}
  ```
- non-`aten.` targets (custom ops pass through untouched).

Validation runs eagerly in **both** `add_exported_program` and `add_pytorch_module`
(test `test_validation_via_add_pytorch_module`). A registered user lowering suppresses the
"unsupported" error (`test_user_lowering_bypasses_unsupported_check`).

---

## 8. Op coverage / lowering system

### 8.1 The resolver tables

`coreai_torch/_aten_to_core.py` lines 3543–3741:
- `_aten_to_core_resolver: dict[str, Callable[..., Any]]` — key is the **variant-suffixed FX
  target name with the `aten.` namespace stripped**, e.g. `"add.Tensor"`, `"mean.dim"`,
  `"sym_size.int"`, plus bare Python-operator keys `"add"`, `"mul"`, `"sub"`, `"neg"`, `"pow"`,
  `"round"`, `"ceil"`, `"trunc"`, `"mod"`, `"floordiv"`, `"truediv"`, `"getitem"`.
- `_higher_order_resolver = {"_yield": replace_yield, "cond": replace_cond, "while_loop": replace_while_loop}`
- `_custom_to_core_resolver` (in `_custom_to_core.py`):
  ```python
  {"lut_to_dense": ..., "constexpr_blockwise_shift_scale": ...,
   "quantize": ..., "dequantize": ..., "sparse_to_dense": ...}
  ```
  keyed by **variantless** target (`strip_variant_from_target` removes `.default|.Tensor|.Scalar|.dim`).

### 8.2 Full ATen op list

`docs/api/supported-aten-ops.md` is the canonical table (~180 entries). Copy of the notable
"Notes" column entries (verbatim from the doc):

| ATen op | Notes |
|---|---|
| `_local_scalar_dense.default` | Returns the 0-dim input as-is |
| `_native_batch_norm_legit_no_training.default` | Inference path only |
| `_to_copy.default` | Identity or `coreai.cast` |
| `addmm.default` | `alpha`, `beta` honored |
| `alias.default` | Identity — no IR emitted |
| `avg_pool2d.default` / `avg_pool3d.default` | Lowered as a composite op |
| `clone.default` | Identity in the absence of memory-format changes |
| `convolution.default` | 1D / 2D / 3D, transposed, grouped |
| `cumsum.default` | Lowered to `coreai.scan` with a sum combiner |
| `div.Tensor_mode` | Honors `rounding_mode` (`None`, `"floor"`, `"trunc"`) |
| `embedding.default` | Lowered to `coreai.gather_nd` |
| `gather.default` | Lowered to `coreai.gather_along_axis` |
| `hardsigmoid.default` | Lowered as a composite |
| `index.Tensor` | Lowered to `coreai.gather_nd` |
| `index_put.default` | Lowered to `coreai.scatter_nd` |
| `index_select.default` | Lowered to `coreai.gather_along_axis` |
| `instance_norm.default` | Preserved as composite by `get_decomp_table()` |
| `isinf.default` | Lowered as `(x == +inf) \| (x == -inf)` |
| `pixel_shuffle.default` | Preserved as composite by `get_decomp_table()` |
| `reflection_pad{1,2,3}d.default` | Lowered to `coreai.pad` with `reflect` mode |
| `replication_pad{1,2,3}d.default` | Lowered to `coreai.pad` with `replicate` mode |
| `scaled_dot_product_attention.default` | Preserved as composite by `get_decomp_table()` |
| `select.int` | Lowered to `coreai.slice_` plus a dim removal |
| `slice.Tensor` | Lowered to `coreai.slice_` |
| `slice_scatter.default` | Lowered to `coreai.slice_update` |
| `split_with_sizes.default` | Lowered to `coreai.split` |
| `sym_float` | Casts a `SymInt` scalar tensor to a `SymFloat` scalar tensor |
| `sym_size.int` | Returns the size of a tensor along a dim as a shape-`[1]` tensor |
| `upsample_bilinear2d.vec` | Lowered to `coreai.interpolate` (linear mode) |
| `upsample_nearest2d.vec` | Lowered to `coreai.interpolate` (nearest-neighbor mode) |

Higher-order ops table (verbatim):
| Op | Notes |
|---|---|
| `cond` | `torch.cond` — emitted as a Core AI conditional with two branch subgraphs |
| `while_loop` | `torch._higher_order_ops.while_loop` |

**Doc/source drift found (report as gotcha):** the source resolver contains two ops that are
**missing from `docs/api/supported-aten-ops.md`**:
- `"atan2.default": replace_atan2` (added in `a43cc84`, fixed in `1b3cb3b`)
- `"masked_scatter.default": replace_masked_scatter` (added in `a68f1ad`)
Also the source has bare `"pow"` and `"round"` keys that the doc doesn't list (added in `53d6bdd`
because *"torch.export rewrites leave `aten.pow` as the OpOverloadPacket target with no overload suffix"*).

### 8.3 Writing a custom lowering (verbatim from `docs/guides/custom-op-lowering.ipynb`)

Step 1 — define the torch op:
```python
import torch

@torch.library.custom_op("my_lib::scaled_add", mutates_args=())
def scaled_add(x: torch.Tensor, y: torch.Tensor, scale: float) -> torch.Tensor:
    """Eager implementation: runs on CPU during normal PyTorch inference."""
    return x + scale * y


@scaled_add.register_fake
def _(x: torch.Tensor, y: torch.Tensor, scale: float) -> torch.Tensor:
    """Abstract implementation: called by torch.export to infer output shapes."""
    return torch.empty_like(x)
```

Step 4 — register the lowering:
```python
from coreai._compiler.dialects import coreai

from coreai_torch import TorchConverter
from coreai_torch._utils import get_operands

converter = TorchConverter()


@converter.register_torch_lowering("my_lib::scaled_add.default")
def lower_scaled_add(values_map, node, loc):
    x, y = get_operands(values_map, node, [0, 1])
    scale = node.args[2]  # plain Python float

    scale_val = coreai.constant(scale, dtype=x.type.element_type)
    scaled_y = coreai.broadcasting_mul(y, scale_val, loc=loc)
    return coreai.broadcasting_add(x, scaled_y, loc=loc)
```

Override a built-in ATen lowering (verbatim, also in `tests/api/test_torch_converter.py`):
```python
import numpy as np
from coreai_torch._utils import get_operand

@converter.register_torch_lowering(
    "aten::_adaptive_avg_pool2d.default", allow_override=True
)
def lower_adaptive_avg_pool2d_static(values_map, node, loc):
    x = get_operand(values_map, node, 0, loc)
    output_h, output_w = node.args[1]
    input_h, input_w = x.type.shape[2], x.type.shape[3]
    stride_h, stride_w = input_h // output_h, input_w // output_w
    kernel_h = input_h - (output_h - 1) * stride_h
    kernel_w = input_w - (output_w - 1) * stride_w
    return coreai.broadcasting_divide(
        coreai.sumpool2d(
            x,
            kernel_size=np.array([kernel_h, kernel_w], dtype=np.uint32),
            strides=np.array([stride_h, stride_w], dtype=np.uint32),
            dilation=coreai.constant([1, 1], dtype=np.uint32),
        ),
        coreai.cast(float(kernel_h * kernel_w), x.type.element_type),
    )
```

Doc "Notes" section (verbatim):
- **Op name format.** The qualified name must be `"namespace::op_name.overload"`. Custom ops
  defined with `@custom_op` always use the `.default` overload.
- **Reserved namespaces.** `aten`, `higher_order`, `coreai`, and `coreaix` are built-in.
  Overriding requires `allow_override=True`.
- **Per-instance registration.** Lowerings are stored on the `TorchConverter` instance.
- **Multiple return values.** Return a Python list of `Value`s; stored as `"node_name#0"`, `"node_name#1"`, …

Warning block from the docs:
> Lowering functions are written against authoring APIs from `coreai-core` (such as
> `coreai._compiler.dialects`). The leading underscore on `_compiler` marks this as private
> upstream API — it may move or change without notice across `coreai-core` releases.

### 8.4 Emitting a **composite** from a custom lowering

`generate_composite_decl` — actual source signature (`_composite_declaration.py:162`):
```python
def generate_composite_decl(
    context: Context,
    composite_name: str,
    input_names: Sequence[str],
    output_names: Sequence[str],
    op_attributes: dict,
    version=1,
):
```
**Doc drift:** `docs/api/generate-composite-decl.md` declares it as
`generate_composite_decl(context, op_name, input_names, output_names, op_attributes) -> CompositeDeclaration`
— the real 2nd param is named `composite_name` and there is an extra `version=1` param. The
function *mutates the caller's dict*: `op_attributes["version"] = version`. It returns the parsed
MLIR `Attribute`, not the `CompositeDeclaration` dataclass.

Attribute textual form produced (`CompositeDeclaration.to_coreai_attr`):
```python
Attribute.parse(f'#coreai.composite_declaration<"{self.name}" = {attrs!s}>', context=context)
```
with `attrs = {"input_names": [...], "output_names": [...], "op_attrs": {...}}`.

Supported attribute value types: `bool` → `BoolAttr`, `int` → `IntegerAttr(si64)`,
`float` → `FloatAttr(f32)`, `str` → `StringAttr`, `dict` → nested `DictAttr`, `list` → `ArrayAttr`.
Anything else raises `TypeError("Unsupported value provided in composite declaration {v}.")`.

Doc example (verbatim from `docs/api/generate-composite-decl.md`):
```python
from coreai_torch import generate_composite_decl, TorchConverter


def my_custom_op_conversion(values_map, node, loc):
    arg0 = values_map[node.args[0].name]
    arg1 = values_map[node.args[1].name]
    op_attributes = {
        "some_attribute": 0.5,
        "version": 1,
    }
    composite_decl = generate_composite_decl(
        arg0.context,
        "my_custom_op",
        ["argument0", "argument1"],
        ["output"],
        op_attributes,
    )

    # The decorator transforms this function: calling it returns an OpResultList
    @coreai.graph(no_inline=True, composite_decl=composite_decl)
    def my_custom_op_impl(argument0: Value, argument1: Value) -> Value:
        ...
        return result

    return my_custom_op_impl(arg0, arg1)[0]


converter = TorchConverter()
converter.register_torch_lowering("mylib::my_custom_op")(my_custom_op_conversion)
```
> "The `coreai.graph` decorator always returns an `OpResultList`. Index it at `[0]` when the
> composite produces a single output."

Real in-tree example — `build_hard_sigmoid_composite` (`_utils.py:1926`):
```python
def build_hard_sigmoid_composite(context: Any) -> coreai.GraphOp:
    """Build a hard_sigmoid composite graph: min(max(x + 3, 0), 6) / 6."""
    composite_decl = generate_composite_decl(
        context, "hard_sigmoid", ["input"], ["output"], {}
    )

    @coreai.graph(private=True, no_inline=True, composite_decl=composite_decl)
    def hard_sigmoid(input: Value) -> Value:
        dtype = input.type.element_type
        three = coreai.constant(3.0, dtype=dtype)
        zero = coreai.constant(0.0, dtype=dtype)
        six = coreai.constant(6.0, dtype=dtype)
        add_three = coreai.broadcasting_add(input, three)
        max_val = coreai.broadcasting_maximum(add_three, zero)
        min_val = coreai.broadcasting_minimum(max_val, six)
        return coreai.broadcasting_divide(min_val, six)

    return hard_sigmoid
```

---

## 9. SDPA lowering (`replace_sdpa`) — worth its own guide section

`_aten_to_core.py:3407-3540`. Docstring decomposition order:
```
1. (GQA) repeat-interleave key/value heads to match query head count
2. scaled_query = query * scale
3. key^T = transpose(key, [0, 1, 3, 2])
4. attn_scores = matmul(scaled_query, key^T)
5. (mask) attn_scores += float_mask
6. attn_weights = softmax(attn_scores, dim=-1)
7. output = matmul(attn_weights, value)
```
Key behaviors:
- Reads `attn_mask` from `args[3]` or `kwargs["attn_mask"]`; `is_causal` from `args[5]`/kwargs;
  `scale` from `args[6]`/kwargs; `enable_gqa` from `args[7]`/kwargs.
- **Rank handling**: rank 3 `(B, S, E)` → `expand_dims(…, [1])` then squeezed back at the end;
  rank > 4 → `_sdpa_flatten_leading_batch_dims` then reshaped back with `coreai.get_shape`.
  `query_rank < 3` → `ValueError(f"SDPA expects query rank >= 3, got {query_rank}")`.
- `is_causal=True` **and** `attn_mask` set → `ValueError("scaled_dot_product_attention: attn_mask and is_causal=True cannot both be set")`.
- `is_causal` is implemented by **building a float mask outside the composite** and passing it as
  `attn_mask` — *"The composite interface is always mask-based."* Masked positions get `-1e4`
  (not `-inf`): `_sdpa_build_causal_mask` → `neg_large = coreai.constant(-1e4, dtype=ele_type)`.
  So the emitted `op_attrs` always has `is_causal: False, window_size: 0`:
  ```python
  op_attributes: dict[str, Any] = {"is_causal": False, "window_size": 0, "version": 1}
  if scale is not None:
      op_attributes["scale"] = scale
  ```
- `scale` is NOT a composite input; when `None` and head_dim static → `1/sqrt(head_dim)` constant;
  when head_dim dynamic → computed at runtime from `coreai.get_shape(query)`.
- Two composite graph variants: `sdpa(q, k, v, m)` and `sdpa_maskless(q, k, v)`.
- Both assert `result.type == query.type` / `original_query.type`.

**Contrast with `composite_ops.SDPA`** (§10.3): the ATen path bakes `is_causal`/window into a mask;
the module path preserves `is_causal`/`window_size` as real composite attributes.

---

## 10. Composite ops library (`coreai_torch.composite_ops`)

Two categories (from `docs/api/composite-ops.md`):
- **Module-class composite ops** — `nn.Module` subclasses you build into your model + externalize
  with an `ExternalizeSpec`: `GatherMM`, `GatedDeltaUpdate`, `RMSNormImpl` (+ `RMSNorm` wrapper),
  `RoPE`, `SDPA`.
- **ATen-derived composite ops** — recognized automatically from ATen nodes:
  `batch_norm`, `group_norm`, `hard_sigmoid`, `instance_norm`, `layer_norm`,
  `linalg_vector_norm`, `log_softmax`, `pixel_shuffle`.

### 10.1 The three-step pattern (from `docs/guides/composite-ops.ipynb`)
1. Use the provided class as a **named submodule** in your model — *not as the root module*.
2. Convert via **`add_pytorch_module`** — required entrypoint for composite op externalization.
3. Pass an `ExternalizeSpec` with `composite_op_name` and `composite_attrs`.

> Tip from docs: "`composite_attrs` must match actual instance attribute names on the target class
> (e.g., `self.eps`, `self.axes`)."

### 10.2 `RMSNormImpl` / `RMSNorm`

`coreai_torch/composite_ops/_rms_norm.py` (verbatim forward):
```python
class RMSNormImpl(torch.nn.Module):
    def __init__(self, eps: float = 1e-5) -> None:
        super().__init__()
        self.eps = eps
        self.axes = -1
        self.version = Version.v1

    def forward(self, input: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        # need f32, otherwise square may overflow f16 max 65504
        input_f32 = input.to(torch.float32)
        square_f32 = input_f32 * input_f32
        # need f32, otherwise accumulation may ignore small values
        mean_square_f32 = square_f32.mean(self.axes, keepdim=True)
        inv_rms_f32 = torch.rsqrt(mean_square_f32 + self.eps)
        input_normalized = input * inv_rms_f32

        # for the gemma3 case, the scale is always fp32, and hence we
        # do the down cast in the end
        if scale.dtype != input.dtype and scale.dtype == torch.float32:
            return (input_normalized * scale).to(input.dtype)

        # in other case, we convert the fp32 intermediate tensor back to
        # input dtype before multiplying with the scale
        return input_normalized.to(input.dtype) * scale
```
`RMSNorm(dim, eps=1e-5, n_heads=None)` wrapper owns `self.weight` (shape `(dim,)` or
`(n_heads, 1, dim)` for fused Q/K norm) and `self.rmsnorm_impl = RMSNormImpl(eps=eps)`.
**Gotcha:** `target_class` must be `RMSNormImpl`, never `RMSNorm`.

Spec:
```python
ExternalizeSpec(target_class=RMSNormImpl, composite_op_name="rms_norm",
                composite_attrs=["axes", "eps"])
```
Expected IR (from `tests/composite_ops/test_rms_norm.py`):
```
coreai.graph private noinline @norm.rmsnorm_impl_<hash>(%arg0: tensor<2x3x4xf32>, %arg1: tensor<4xf32>)
  composite_decl = #coreai.composite_declaration<"rms_norm" =
    input_names = ["input", "scale"], op_attrs = {axes = -1 : si64, eps = 9.99999974E-6 : f32,
    version = 1 : si64}, output_names = ["output"]>
coreai.invoke @norm.rmsnorm_impl_<hash>(%arg0, %N)
```
(Note the `eps = 9.99999974E-6` float32 rendering of `1e-5`.)

### 10.3 `SDPA` (`_sdpa.py`)

```python
class SDPA(torch.nn.Module):
    def __init__(self, scale: float | None = None, is_causal: bool = False,
                 window_size: int = 0, _use_hf_impl: bool = False) -> None: ...
    def forward(self, query, key, value,
                attn_mask: torch.Tensor | None = None,
                sinks: torch.Tensor | None = None) -> torch.Tensor: ...
```
Extra undocumented private ctor arg `_use_hf_impl` (selects `_sdpa_hf_impl` which matches
HuggingFace numerics; `sinks` is `NotImplementedError` there).

Notable internals:
- `CausalVariant` (`strenum.StrEnum`): `upper_left`, `lower_right`. Only **lower_right** is
  supported ("Lower-right is the v1 used in language model linear decoding"). Docstring contrast:
  ```
  torch.nn.functional.scaled_dot_product_attention causal mask is upper-left
      1 0 0 0 0 / 1 1 0 0 0 / 1 1 1 0 0
  while our causal mask is lower-right
      1 1 1 0 0 / 1 1 1 1 0 / 1 1 1 1 1
  ```
- `_vanilla_sdpa` adds two things over torch's SDPA: **sinks** and **GQA that survives dynamic-shape export**.
- `_vanilla_repeat_interleave` exists because *"PyTorch official torch.repeat_interleave has dynamic
  shape bug starting from torch 2.8 and still fails at torch 2.10"* — it uses
  `torch.index_select(x, 1, arange(num_heads).repeat_interleave(reps))` instead.
- Bool mask → float mask conversion uses `-1e4` (`float_mask = -1e4 * not_attended.to(query.dtype)`).
- Sinks: `sinks` must be 1-D with `sinks.shape[0] == query.shape[1]`; it is broadcast to
  `(*query.shape[:-1], 1)`, concatenated on the last dim, softmaxed, then narrowed back to `k_len`.
- `_sdpa_hf_impl` asserts `enable_gqa=False` with message *"Hugging Face GQA produces wrong f16 numerics"*.

Spec + doc attention-schema table:
```python
ExternalizeSpec(target_class=SDPA, composite_op_name="scaled_dot_product_attention",
                composite_attrs=["scale", "is_causal", "window_size"])
```
| Schema | Constraint |
|---|---|
| MHA | `N_q == N_kv` |
| GQA | `N_q > N_kv`, `N_q % N_kv == 0` |
| MQA | `N_kv == 1` |
Shapes: `query [B, N_q, T_q, D]`, `key [B, N_kv, T_kv, D]`, `value [B, N_kv, T_kv, D_v]`.
> "For GQA / MQA, do **not** pre-tile `key` / `value` to match `N_q`."

`input_names` variants in IR depend on which optional args were passed:
`["query","key","value"]`, `+["attn_mask"]`, `+["sinks"]`, or all five.

### 10.4 `RoPE` (`_rope.py`)

```python
class RoPE(torch.nn.Module):
    def __init__(self, scale: float = 1.0, base: float = 1e4, dims: int | None = None,
                 interleaved: bool = False, _use_hf_impl: bool = False) -> None: ...
    def forward(self, input, cos=None, sin=None, position_ids=None, freqs=None, offset=None): ...
```
Resolution priority (from source `_rope_impl` + docs):
1. `cos` and `sin` both provided → used directly, all other position args ignored.
2. else build cos/sin from `position_ids` (or `offset + arange(seq_len)`) and `freqs`
   (or `1 / base ** (i/half_dim)`).

Hard-coded numerical requirements (`torch._check` in `_compute_angle`):
- `position_ids.dtype == torch.float32` ("position_ids needs to be in fp32")
- `freqs.dtype == torch.float32` ("freqs needs to be in fp32")
Source comment on why f32 is mandatory:
> "in practice f16 gives wrong generated text... even if half_dim = 64 = 2^6 — anyway, observation
> is always correct :p let us just stick to f32"

Partial rotation: `dims` must be even and `>= 2` (`torch._check(rotation_dims % 2 == 0, ...)`).
`interleaved=True` pairs alternate elements (HF style); `False` splits in half.

Spec:
```python
ExternalizeSpec(target_class=RoPE, composite_op_name="rope",
                composite_attrs=["scale", "base", "dims", "interleaved"])
```

### 10.5 `GatherMM` (`_gather_mm.py`) — the MoE primitive

```python
class GatherMM(torch.nn.Module):
    def __init__(self, num_batch_axes: int = 0) -> None: ...
    def forward(self, lhs, rhs, lhs_indices=None, rhs_indices=None) -> Tensor: ...
```
Reference decomposition (verbatim from source `_gather`):
```python
def _gather(x: Tensor, indices: Tensor, num_batch_axes: int = 0) -> Tensor:
    x_shape = x.shape
    result_shape = (x_shape[0:num_batch_axes] + indices.shape + x_shape[num_batch_axes + 1 :])
    # TODO: Remove this explict cast once torch supports uint indices
    indices = indices.to(torch.int32)
    flat_indices = indices.flatten()
    flat_gather = torch.index_select(x, dim=num_batch_axes, index=flat_indices)
    return flat_gather.view(result_shape)
```
MoE example (verbatim from `docs/api/composite-ops/gather-mm.md`):
```python
class MoELayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.gather_mm = GatherMM(num_batch_axes=0)

    def forward(self, x, experts, indices):   # x [B,T,1,1,D]; experts [E,D,H]; indices [B,T,K]
        return self.gather_mm(x, experts, rhs_indices=indices)   # -> [B,T,K,1,H]
```
Fused gate+up projections: `GatherMM(num_batch_axes=1)` with `fused_experts [2, E, D, H]` → `[2,B,T,K,1,H]`.
Spec: `composite_op_name="gather_mm"`, `composite_attrs=["num_batch_axes"]`.

### 10.6 `GatedDeltaUpdate` (`_gated_delta_update.py`)

```python
class GatedDeltaUpdate(torch.nn.Module):
    def __init__(self, use_qk_l2_norm: bool = True) -> None: ...
    def forward(self, query, key, value, g, beta, initial_state) -> tuple[Tensor, Tensor]: ...
```
Recurrence: `S_t = g_t ⊙ S_{t-1} + β_t k_tᵀ (v_t − S_{t-1} k_t)`.
Shapes: `query/key [B, N_kq_heads, S, D_k]`, `value [B, N_v_heads, S, D_v]`,
`g/beta [B, N_v_heads, S]`, `initial_state [B, N_v_heads, D_k, D_v]`.
Returns `(output [B, S, N_v_heads, D_v], final_state [B, N_v_heads, D_k, D_v])`.

**The implementation uses `torch.ops.higher_order.while_loop` internally** — i.e. converting a model
that uses `GatedDeltaUpdate` exercises the `while_loop` higher-order lowering. Verbatim comment:
```python
# Run the while loop: equivalent to for t in range(s).
# query/key/value/g_exp/beta are passed as additional_inputs so they are
# explicit graph inputs to the subgraph rather than closed-over tensors.
_, state, output = torch.ops.higher_order.while_loop(
    cond_fn, body_fn,
    (torch.tensor(0, device=query.device), state, output),
    (query, key, value, g_exp, beta),
)
```
Constraints (docs): `g` should be negative (op applies `exp` internally); `beta` typically `[0,1]`;
delta update computed in **fp32** internally then cast back to input dtype.
Spec: `composite_op_name="gated_delta_update"`, `composite_attrs=["use_qk_l2_norm"]`.

All composite modules set `self.version = Version.v1` where
`class Version(enum.Enum): v1 = 1` (`composite_ops/_utils.py`).

### 10.7 ATen-derived composite attribute schemas (from `docs/api/composite-ops/*`)

| Composite | ATen source | Inputs | Attributes |
|---|---|---|---|
| `batch_norm` | `aten._native_batch_norm_legit_no_training` | input, gamma, beta, mean, variance | `eps`, `version` (momentum dropped) |
| `group_norm` | `aten.native_group_norm` | input, weight, bias | `num_groups`, `num_channels`, `eps`, `version` |
| `layer_norm` | `aten.native_layer_norm` | input, gamma, beta | `axes`, `eps`, `version` |
| `instance_norm` | `aten.instance_norm` | input, gamma, beta | `eps`, `version` |
| `hard_sigmoid` | `aten.hardsigmoid` | input | `version` |
| `log_softmax` | `aten._log_softmax` | input | `axis`, `version` |
| `linalg_vector_norm` | `aten.linalg_vector_norm` | input | `ord`, `axes`, `keep_dim`, `version` |
| `pixel_shuffle` | `aten.pixel_shuffle` | input | `upscale_factor`, `version` |

`replace_instance_norm` (source) only emits the composite when `use_input_stats` (`node.args[5]`)
is truthy; otherwise it inlines running-stat normalization. Its composite body upcasts fp16 → fp32
via `prepare_compute_type_for_norm` and casts back.

---

## 11. Externalization (`coreai_torch/externalize.py`)

### 11.1 `ExternalizeSpec`

```python
@dataclass
class ExternalizeSpec:
    target_class: type
    composite_op_name: str | None = None
    composite_attrs: list[str] | None = None

    def __post_init__(self) -> None:
        if self.composite_op_name is None:
            ... raise ValueError(
                f"ExternalizeSpec: {set_fields} can only be set when composite_op_name is provided."
            )
```
- Matching is by `isinstance(mod, config.target_class)` over `model.named_modules()`
  (skipping the root, `if not name: continue`); **first matching config wins** (`break`).
- Unmatched target classes → `UserWarning`, not an error:
  > "externalize_modules: the following target class(es) did not match any submodule in the model:
  > {...}. No externalization will happen for these classes. If intentional (e.g. passing a superset
  > across model variants), this warning is safe to ignore. Otherwise, check for typos or stale
  > class references."
- Marked-but-unreachable submodules are skipped with a warning (added by `ea728d6`):
  > "[WARN] coreai_torch.externalize: skipping unused submodule '{name}'. It matched an
  > externalize_modules target class but is not reachable from the exported graph. Action: remove it
  > from the model passed to add_pytorch_module, or ignore if intentional."
- Passing a **bare class** instead of a spec = *simple externalization*, documented as
  **experimental**, "no composite-op metadata and no optimization benefit".

### 11.2 The 5-phase pipeline (module docstring, verbatim summary)

```
Phase 1: Mark & Re-export (_mark_externalize)
  1. Walk model.named_modules(); for each match: resolve path, sanitize op name, save
     _original_forward, register a torch.library.custom_op from the submodule's forward,
     register the original forward as the fake impl via register_fake, patch submodule.forward
     to call the custom op, stamp _externalize_config = ExternalizeSpec(...).
  2. Re-export via export_fn(model) and run_decompositions(decomp_table).
Phase 2: Prepare (_prepare_externalized / _prepare_module_export)
  yields _PreparedModule objects shallowest-first; one per call-site node, with a UUID-suffixed
  graph name, fake inputs, dynamic shapes, and source nodes.
Phase 3: Export Submodules (_torch_export_module / _finalize_module_export)
  torch.export.export with prepared fake inputs + dynamic shapes; derive composite I/O names from
  the graph signature; then run_decompositions().
Phase 4: Emit Core AI IR (_perform_externalization)
  deepest-first; coreai.GraphOp (noinline for all, private + composite_decl for composite ops);
  register per-node lowerings keyed by FX node name.
Phase 5: Cleanup (_restore_externalized)
  Remove all markers. The user's model is left unmodified.
```

Concrete details worth quoting in a guide:
- Namespace of the temporary torch ops: `_EXTERNALIZE_NAMESPACE = "coreai_torch_ext"`
  (`_utils.py:1512`), op name = dotted module path with dots → underscores
  (`_sanitize_op_name`), i.e. `coreai_torch_ext::block_norm`.
- Graph name = `f"{module_path}_{uuid4().hex[:8]}"` — **each call site gets its own graph**:
  > "Even when two call sites have the same argument count, each must get its own noinline graph so
  > the runtime does not deduplicate invocations of the same graph symbol."
- Inner submodules are decomposed with the **default** table, not `get_decomp_table()`:
  ```python
  # The user's export_fn may preserve composite ops like aten.scaled_dot_product_attention
  # so they survive in the *whole-model* graph for externalization detection.
  # Inside the externalized body those ops must be decomposed.
  inner_ep = inner_ep.run_decompositions()
  ```
- Fake inputs are **fresh concrete tensors** (`torch.empty(shape, dtype, device)`), not the parent's
  FakeTensors, to avoid: (1) view metadata like `storage_offset` from `.narrow()`, (2) SymInts bound
  to the parent `ShapeEnv`.
- Dynamic shapes are reconstructed per call site with `_dim_for_sym`, which reuses a `Dim` per
  symbol string and sanitizes derived expressions (`s0 + s1` → `s0___s1`, prefixed `d_` if needed),
  honoring `shape_env.var_to_range` for `min`/`max`.
- Optional `None` args in the middle of `node.args` force a **kwargs-based re-export**
  (`needs_kwargs = non_none_positions != list(range(len(prep.fake_inputs)))`).
- Non-tensor args to an externalized submodule are rejected:
  ```
  TypeError: Expected argument {i} of custom op node '{node.target}' to be a Tensor, but got
  {type}. Only Tensor inputs are supported for externalized submodules.
  ```

### 11.3 `_derive_composite_io_names`

```python
input_names: PARAMETER/BUFFER -> spec.target (attribute name);  USER_INPUT -> spec.arg.name
output_names: ["output"] for a single user output, else ["output_0", "output_1", ...]
```
Verified by `tests/test_externalize.py::test_derive_composite_io_names_*`:
- `forward(query, key)` → `["query", "key"]`, `["output"]`
- `self.weight = nn.Parameter(...)`, `forward(input)` → `["weight", "input"]` (**parameters come first**)
- tuple return → `["output_0", "output_1"]`
- optional args left `None` at export → excluded from `input_names`
- middle optionals skipped, later ones passed → correct ordering (`["x", "c"]`, `["x", "a", "c"]`)

### 11.4 Emitted IR shapes (verbatim from `docs/guides/externalization.ipynb`)

Composite-op externalization:
```llvm
module {
  coreai.graph private noinline @norm.rms_norm(
      %arg0: tensor<1x10xf32> {coreai.name = "input"},
      %arg1: tensor<10xf32> {coreai.name = "scale"}
  ) -> tensor<1x10xf32> attributes {
      composite_decl = #coreai.composite_declaration<"rms_norm" = {
          input_names = ["input", "scale"],
          op_attrs = {axes = -1 : si64, eps = 9.99999974E-6 : f32, version = 1 : si64},
          output_names = ["output"]}>
  } {
    // ... rms-norm body ...
    coreai.output %15 : tensor<1x10xf32>
  }
  coreai.graph @main(%arg0: tensor<1x10xf32>) -> tensor<1x5xf32> {
    %3 = coreai.invoke @norm.rms_norm(%arg0, %0)
        : (tensor<1x10xf32>, tensor<10xf32>) -> tensor<1x10xf32>
    coreai.output %7 : tensor<1x5xf32>
  }
}
```
Simple externalization:
```llvm
coreai.graph noinline @norm(%arg0: tensor<1x10xf32>) -> tensor<1x10xf32> { ... }
coreai.graph @main(...) { %3 = coreai.invoke @norm(%arg0) : ... }
```
> "Symbol names and constants above are illustrative (the converter appends a hash suffix to each
> externalized graph name)."

### 11.5 Requirements for composite-op modules (docs, verbatim)

1. **Forward arguments must be tensors** — all `forward` parameters that become inputs must be
   `torch.Tensor`. Scalar configuration (e.g. `eps`, `is_causal`) should be stored as instance
   attributes and serialized via `composite_attrs`.
2. **Optional arguments must use `torch.Tensor | None = None`** — when left `None`, the arg is
   excluded entirely and does not appear in `input_names`. There is no support for default tensor
   values.

---

## 12. Stateful models / KV cache / IO naming

Source of truth: `docs/api/TorchConverter.md` §"IO naming" + `_utils.py::_resolve_io_names` +
`tests/test_stateful.py`.

### 12.1 What counts as state (no opt-out) — docs verbatim

> The converter treats two things as state:
> 1. **Mutable buffers** registered via `self.register_buffer(...)` and mutated in-place inside
>    `forward()` (e.g., `self.buf.add_(x)`).
> 2. **User inputs mutated in-place** inside `forward()` (e.g., `x.mul_(2)` on a `forward()` arg).
>
> Both are detected from the exported program's graph signature. There is **no flag** to opt a
> mutated user input out of state. … If you don't want a `forward()` argument treated as state,
> eliminate the in-place mutation from your model — clone first (`x_local = x.clone(); x_local.mul_(2)`)
> or use the out-of-place form (`x_scaled = x * 2`).

### 12.2 Default names table (docs verbatim)

| Category | FX graph source | Relates to | Example |
|---|---|---|---|
| Input | Placeholder `node.name` | `forward()` arg name | `def forward(self, x, z)` → `"x"`, `"z"` |
| Output | Output node's input `node.name` | Internal op name | `return a + b, c * d` → `"add"`, `"mul"` |
| State (buffer) | Placeholder `node.name` | `"b_"` + `register_buffer` attr | `register_buffer("kv_cache", …)` → `"b_kv_cache"` |
| State (mutated user input) | Placeholder `node.name` | `forward()` arg name | `def forward(self, y): y.mul_(2)` → `"y"` |

Ordering: `state_names` = mutable buffers (registration order) **then** mutated user inputs
(signature order).

Warnings from the docs (verbatim):
> "These naming conventions are observed behavior from the FX graph, not a stable contract from
> PyTorch. They may change across PyTorch versions. Always provide explicit names for production use."
> "The ordering of `state_names` (buffers first, then mutated user inputs) is based on observed FX
> graph behavior, not a stable PyTorch contract. … Always verify state ordering when upgrading
> PyTorch versions."

### 12.3 Assertions in `_resolve_io_names` (`_utils.py:1783-1889`)

- `assert len(state_in_idx) == len(state_out_idx)` →
  `"State input/output count mismatch: … This may indicate an unsupported graph signature layout."`
- Ordering invariant assert:
  ```
  "FX placeholder order violates the 'mutable buffers first, then mutated user inputs' invariant.
   … This breaks the documented state_names ordering — pass state_names explicitly matched to your
   buffer/arg names, or check PyTorch version compatibility."
  ```
- Count validation errors: `f"Graph has {n} live inputs ({names}), but input_names has {m} entries ({...})."`
  and the analogous "live outputs" message.

### 12.4 IR annotation

Each stateful input carries `MutableBuffers.buffer_mutation = "<resolved state name>"`:
```
coreai.graph @main(
  %0: tensor<1x4xf32> {MutableBuffers.buffer_mutation = "b_state", coreai.name = "b_state"},
  %1: tensor<1x4xf32> {coreai.name = "x"}
) -> (tensor<1x4xf32> {coreai.name = "b_state"})
```
Regression note (from `tests/test_stateful.py`): before a fix, the annotation loop used renamed
`graph_input_names` for the `inputs_to_buffers` lookup (which is keyed by original FX placeholder
names), silently dropping `MutableBuffers.buffer_mutation` whenever custom `input_names` were given.

### 12.5 Full stateful example (docs verbatim)

```python
class KVCache(nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("kv_cache", torch.zeros(1, 4))   # state[0]
        self.register_buffer("pos_idx", torch.zeros(1))       # state[1]

    def forward(self, x, y, z):
        self.kv_cache.add_(x)       # buffer mutation
        self.pos_idx.add_(1)        # buffer mutation
        y.mul_(2)                   # state[2]: mutated user input
        # non-mutated: x -> input[0], z -> input[1]
        return self.kv_cache + y, z * 3

ep = torch.export.export(KVCache().eval(),
                         args=(torch.randn(1, 4), torch.randn(1, 4), torch.randn(1, 4)))
ep = ep.run_decompositions(get_decomp_table())

TorchConverter().add_exported_program(
    ep,
    state_names=["kv_cache", "pos_idx", "y_state"],
    input_names=["query", "context"],
    output_names=["attn_out", "scaled"],
).to_coreai().optimize()
```

Realistic KV-cache test (`tests/test_stateful.py::test_kv_cache_pattern`):
```python
class KVCacheModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("k_cache", torch.zeros(1, 4, 8))
        self.register_buffer("v_cache", torch.zeros(1, 4, 8))

    def forward(self, q, k, v):
        self.k_cache.copy_(k)
        self.v_cache.copy_(v)
        attn = torch.matmul(q, self.k_cache.transpose(-2, -1))
        return torch.matmul(attn, self.v_cache)
```
Runtime state protocol (from `tests/utils.py`):
```python
state: dict[str, NDArray] = {}
for name in desc.state_names:
    d = desc.state_descriptor(name=name)
    shape = tuple(s if s is not None else 1 for s in d.shape)
    state[name] = NDArray(np.zeros(shape, dtype=np.dtype(d.dtype)))
...
rt_outputs = await rt_func(inputs=inputs, state=state)
```
**Gotcha from the source comment:** `NDArray.from_descriptor` only sizes the buffer; on Linux the
backing storage isn't zeroed, so buffer-state reads return garbage on the first call — allocate a
zero-filled numpy array instead.

---

## 13. Dynamic shapes

- Standard `torch.export` mechanism: `torch.export.export(model, args=..., dynamic_shapes={...})`
  with `torch.export.Dim("batch", min=1, max=10)`.
- Test helper worth reproducing in a guide (`tests/utils.py:81`):
  ```python
  def make_dynamic_shapes(**arg_specs) -> dict[str, dict[int, torch.export.Dim]]:
      """Pass each model argument as a keyword, mapped to either a list of dim names
      (index = position) or a dict of {dim_index: dim_name}. Using the same string name for two
      positions in different tensors produces the *same* Dim object. Use None to leave a dim static."""
  # make_dynamic_shapes(x=["batch", "seq", "feat"])
  # make_dynamic_shapes(mat1=["batch", "M", "K"], mat2=["batch", "K", "N"])
  # make_dynamic_shapes(x={0: "batch"}, y={0: "batch"})
  # make_dynamic_shapes(x=["batch", None, "h", "w"])
  ```
- Dynamic dims become `ShapedType.get_dynamic_size()` (printed as `?`) in the tensor type
  (`get_tensor_type`: `dim = ShapedType.get_dynamic_size() if isinstance(s, torch.SymInt) else s`).
- Externalization propagates dynamic dims into the sub-graph:
  `coreai.graph noinline @inner_<hash>(%arg0: tensor<?x4xf32>) -> tensor<?x4xf32>`.
- **SymInt hardening** (commit `53d6bdd`, quoted in the commit message) — six related fixes:
  1. bare `'pow'` resolver entry (torch.export can leave `aten.pow` as an OpOverloadPacket with no
     overload suffix → `Unsupported ATen op: pow`).
  2. bare `'round'` for the same reason.
  3. `upsample_build_output_shape_dynamic`: make each `(out_h,out_w)` operand rank-1 int32 before
     the concat — "the dialect verifier rejects mixed-rank / mixed-element-type concat inputs".
  4. `get_operand` mixed-list path (SymInt `fx.Node`s + plain ints): normalise every element to
     canonical rank-1 si32 (`to_rank1_int32`) and emit plain ints as
     `coreai.constant([e], dtype=np.int32)`. Affects `view`, `expand`, `reshape`, `repeat`.
  5. `replace_cat`: when one input has a dynamic non-concat axis and a sibling has a static size for
     that axis, reshape the dynamic side to the static size before concat.
  6. `replace_arange_start_step`: unify start/end/step element types to the node's output dtype
     before `coreai.range_` (its verifier requires uniform element types).
- **Slice gotcha** (`resolve_slice_arg`):
  ```python
  SLICE_INT32_MAX: int = 2**31 - 1
  # ATen uses INT64_MAX (~9.2e18) to mean "slice to end". Core AI indices are si32, so values above
  # INT32_MAX overflow to negative (e.g. INT64_MAX → -1), causing coreai.slice_ to compute a wrong
  # output shape. Clamp to INT32_MAX.
  return min(val, SLICE_INT32_MAX)
  ```
  Symbolic `torch.SymInt` slice args are rejected:
  `ValueError("Symbolic SymInt slice argument is not supported: … Use fx.Node references (e.g. results of aten.sym_size.int).")`
- `max_pool2d` rejects dynamic stride:
  `ValueError(f"Encountered dynamic stride at maxpool2d: node: {node}, name: {node.name}")`.

---

## 14. Dtypes & type mapping (`coreai_torch/_type_mapping.py`)

`TORCH_TO_COREAI_DTYPE` (verbatim keys):
```python
torch.bool          -> IntegerType.get_signless(1)
torch.uint1/2/3/4/6 -> IntegerType.get_unsigned(1/2/3/4/6)
torch.int8/uint8    -> IntegerType.get_signed(8) / get_unsigned(8)
torch.int16/uint16  -> signed(16) / unsigned(16)
torch.int32/uint32  -> signed(32) / unsigned(32)
torch.int64         -> signed(64)
torch.float32/64/16 -> F32Type / F64Type / F16Type
torch.bfloat16      -> BF16Type
torch.float8_e5m2 / e4m3fn / e8m0fnu -> Float8E5M2Type / Float8E4M3FNType / Float8E8M0FNUType
torch.complex32/64  -> ComplexType(F16Type) / ComplexType(F32Type)   # "Torch calls complex<f32> as complex64"
# conditionally, if hasattr(torch, "int4"):  torch.int2/int4 -> signed(2)/signed(4)
# conditionally, if hasattr(torch, "float4_e2m1fn_x2"): -> Float4E2M1FNType
```

**64-bit narrowing** (`_utils.py:305`):
```python
# Narrow int64/fp64 to int32/fp32 since coreai does not handle 64-bit types.
_NARROW_TORCH_DTYPE: dict[torch.dtype, torch.dtype] = {
    torch.int64: torch.int32,
    torch.float64: torch.float32,
}
```
`check_result_type` accepts either the wide or narrowed dtype (int64 also accepts uint32;
complex64 also accepts complex32 "After f16 casting, view_as_complex produces complex<f16>").

Constant emission (`TorchConverter._constant_from_tensor`) special cases:
- fp8 (`e4m3fn`/`e5m2`/`e8m0fnu`): detour via float16 → numpy → `ml_dtypes.float8_*`.
- bfloat16: detour via float32 → `ml_dtypes.bfloat16`.
- `_NARROW_TORCH_DTYPE`: cast then `.numpy()`.
- Sub-byte tensor subclasses store bit-packed bytes in `.elem` (uint8) and the logical dtype in
  `future_dtype`.
- Comment worth quoting (converter.py:610-617):
  > "We prefer to create DenseElementsAttr whenever possible, because DenseElementsAttr has better
  > support than DenseResourceElementsAttr, e.g. Core AI compiler can only check if a
  > DenseElementsAttr is splat, i.e. cannot check the opaque DenseResourceElementsAttr. As of
  > 2026-04-10 coreai.constant API is not as good at this as create_elements_attr + ConstantOp APIs
  > … TODO: Once coreai.constant reaches parity, migrate to it."
- Packed FP4: `get_tensor_type` doubles the last dim when `future_dtype == torch.float4_e2m1fn_x2`
  and the physical dtype is uint8.

fp16 scalar promotion in `get_operand`: a Python `float` arg becomes an **fp16 constant** when every
float tensor operand of the node is fp16 and the value round-trips losslessly
(`_all_float_operands_are_fp16` + `_is_float_in_float16_range`). `scalar_constant()` deliberately
bypasses this for Metal-kernel scalars.

---

## 15. Custom Metal kernels — `TorchMetalKernel`

File `coreai_torch/_torch_metal_kernel.py`; subclasses `coreai.authoring.CustomMetalKernel`.

```python
TorchMetalKernel(
    name: str,
    input_names: list[str],
    result_names: list[str],
    src: str,
    torch_defn: Callable[..., Any],
    metal_params: list[MetalParameter] | None = None,
    helper_src: str | None = None,
    template_dtypes: dict[str, str] | None = None,
)
```
Call:
```python
def __call__(self, *args, threads_per_grid: tuple[int,int,int],
             threads_per_thread_group: tuple[int,int,int],
             result_shapes: list[list[int]])
```
Under the hood `__call__` converts the tuples to `torch.tensor(list(...), dtype=torch.uint32)` and
appends them (plus one uint32 shape tensor per result) as extra args of the generated torch op.

Registered torch op name: **`coreai_metal_kernels::{name}`** (overload `.default`).
The generated op signature is the `torch_defn` signature **augmented** with
`threads_per_grid`, `threads_per_thread_group`, and `result_shape_<result_name>` params
(`result_shape_params` property).

### Validation (all at construction time)
| Check | Exception + message |
|---|---|
| empty/whitespace name | `ValueError(f"Kernel name must be a non-empty string, got {name!r}")` |
| empty `result_names` | `ValueError("result_names must contain at least one entry")` |
| duplicate names | `ValueError(f"Duplicate {label} names: {duplicates}")` |
| name in both lists | `ValueError(f"Names appear in both input_names and result_names: {overlap}")` |
| `*args`/`**kwargs` in `torch_defn` | `TypeError("custom kernels do not support variadic parameters (*args / **kwargs); got parameter '{name}' with kind {kind}")` |
| bad param annotation | `TypeError("custom kernels only support `torch.Tensor`, `float`, `bool` and `int` inputs, got {annotation}")` |
| param count ≠ `len(input_names)` | `ValueError("torch function should have same number of parameters as specified by input names, expected N, got M")` |
| bad return annotation | `TypeError("Metal kernels only support return types of `torch.Tensor`, `list[torch.Tensor]`, or `tuple[torch.Tensor]` (with a concrete number of tuple members). …")` |
| single Tensor return but >1 result name | `ValueError("torch_defn returns a single torch.Tensor, but result_names has N entries: …")` |
| `tuple[...]` arity mismatch | `ValueError("torch_defn returns tuple of N tensors, but result_names has M entries: …")` |
| non-3-tuple grid/threadgroup | `ValueError("threads_per_grid must be a 3-tuple, got N elements: …")` |
| `result_shapes` length mismatch | `ValueError("result_shapes must contain one shape per result name; expected N (for [...]), got M")` |
| int scalar out of int32 | `ValueError("int scalar {name!r}={v!r} is outside the 32-bit int range that MSL `int` supports")` |
| non-finite float scalar | `ValueError("float scalar {name!r}={v!r} is not finite; NaN/Inf scalars are not supported")` |

Notes:
- `inspect.signature(torch_defn, eval_str=True)` — needed so PEP-563 string annotations
  (`from __future__ import annotations` in the *caller's* module) resolve.
- Allowed scalars: `_ALLOWED_SCALARS = {int, float, bool}`;
  `_SCALAR_METAL_DTYPE = {bool: "bool", int: "int", float: "float"}`.
- **Bool scalars are widened to `ui8` at the IR level** because `i1` is rejected by the
  `metal4_kernel` verifier; the MSL signature is patched back to `constant bool&`.
- **Scalars are baked into the kernel body as literals** and shadow the declared parameter:
  ```python
  return "{\n" + "\n".join(decls) + "\n" + src + "\n}"   # e.g.  "float c = 2.5f;"
  ```
  Rationale (verbatim): *"The runtime binds rank-0 inputs as `MTLTensor` resource handles, so a
  `constant T&` parameter declared in the kernel source can't be dereferenced as a value … keep the
  parameter declaration intact but shadow it inside the body with a local variable initialized to
  the literal."*
- Per-scalar-value kernel caches (`_scalar_kernel_caches`) so two call sites with different scalar
  values don't collide in the base `(rank, dtype)` cache but identical ones still share a PSO.
- 31-buffer limit: `CustomMetalKernel.PARAMETER_LIMIT` (referenced in `tests/dsl/test_scalar_inputs.py`
  docstring) covers data + scalar inputs together.

### Canonical kernel (docs verbatim)

```python
import torch
from coreai.authoring import MetalParameter

from coreai_torch import TorchMetalKernel


def torch_add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """Reference implementation for shape inference during export."""
    return x + y


custom_add = TorchMetalKernel(
    "vector_add",
    input_names=["x", "y"],
    result_names=["output"],
    src="output[id] = x[id] + y[id];",
    torch_defn=torch_add,
    metal_params=[
        MetalParameter("id", "uint", "thread_position_in_grid"),
    ],
)


class AddModel(nn.Module):
    def forward(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return custom_add(
            x, y,
            threads_per_grid=(x.shape[0], 1, 1),
            threads_per_thread_group=(1, 1, 1),
            result_shapes=[list(x.shape)],
        )
```
Conversion:
```python
converter = TorchConverter()
converter.register_custom_kernels([custom_add])       # BEFORE add_exported_program
converter.add_exported_program(exported, input_names=["x", "y"], output_names=["result"])
coreai_program = converter.to_coreai()
coreai_program.optimize()
```

### Dtype templating (docs verbatim)

```python
custom_matmul = TorchMetalKernel(
    "matmul",
    input_names=["A", "B"],
    result_names=["C"],
    src="""
        const uint K = A.get_extent(0);
        const uint M = A.get_extent(1);
        const uint N = B.get_extent(0);
        if (gid.x >= N || gid.y >= M) return;
        TYPE sum = 0.0f;
        for (uint k = 0; k < K; ++k) {
            sum += A[k, gid.y] * B[gid.x, k];
        }
        C[gid.x, gid.y] = sum;
    """,
    torch_defn=torch_matmul,
    metal_params=[MetalParameter("gid", "uint2", "thread_position_in_grid")],
    # "A" is the input whose dtype determines the substitution; every occurrence of "TYPE"
    # in src is replaced with the corresponding Metal type (e.g. "half", "float", "bfloat").
    template_dtypes={"A": "TYPE"},
)
```
Multiple outputs:
```python
def torch_sincos(x: torch.Tensor) -> list[torch.Tensor]:
    return [torch.sin(x), torch.cos(x)]

sincos_kernel = TorchMetalKernel(
    "sincos", input_names=["x"], result_names=["out_sin", "out_cos"],
    src="out_sin[id] = sin(x[id]); out_cos[id] = cos(x[id]);",
    torch_defn=torch_sincos,
    metal_params=[MetalParameter("id", "uint", "thread_position_in_grid")],
)
results = sincos_kernel(x, threads_per_grid=(x.shape[0],1,1),
                        threads_per_thread_group=(1,1,1),
                        result_shapes=[list(x.shape), list(x.shape)])
```

### Emitted IR shape (from `tests/dsl/test_custom_kernels.py`)

```
coreai.metal4_kernel kernel_args(%a, %b), threads_per_grid %g, threads_per_thread_group %tg,
  result_shapes(%rs) {kernel_name = "custom_add_<rand>", kernel_source = "<msl>"}
  : (tensor<2x2x3xf16, #coreaix.hw_constraints<MTLBuffer, alignments: [1x1x1x1], interleave: [1x1x1]>>,
     ..., tensor<3xui32>, tensor<3xui32>, tensor<3xui32>) -> tensor<2x2x3xf16, ...>
```
Note the `#coreaix.hw_constraints<MTLBuffer, alignments: [...], interleave: [...]>` encoding
attached to every kernel tensor operand. Runtime inputs for Metal kernels must be
`NDArray(data, backing=StorageKind.METAL)` (`tests/utils.py`, `metal_inputs=True` path).

Runtime failure surface (`tests/dsl/test_failures.py`): a bad MSL body converts fine but
`model.load_function("main")` raises
`RuntimeError("Kernel coreai.metal4_kernel invoked with invalid parameters")`.

Kernel names get a randomized suffix — tests diff by `kernel_source = "..."` string attribute
rather than by name.

---

## 16. Compression / quantization path

`coreai_torch/_compression/custom_layers.py` registers 5 torch custom ops under the `coreai::`
namespace (importing the module is what registers them):

| torch op | Core AI lowering (`_custom_to_core.py`) |
|---|---|
| `coreai::lut_to_dense(indices, lut, axis)` | `coreai.lut_to_dense` (axis normalized to scalar **si16**) |
| `coreai::constexpr_blockwise_shift_scale(input, scale, zero_point?, minval?, input_dtype?, output_dtype?)` | `coreai.blockwise_shift_scale` |
| `coreai::quantize(input, scale, output_dtype, zero_point?, minval?, axis=0)` | `coreai.quantize` |
| `coreai::dequantize(input, scale, zero_point?, minval?, axis=0, input_dtype?, output_dtype?)` | `coreai.dequantize` |
| `coreai::sparse_to_dense(nonzero_data, mask)` | `coreai.build_sparse_with_bitmask` + `coreai.sparse_with_bitmask_to_dense` |

Offset convention (module docstring, verbatim):
```
- zero_point mode (arg is not None): offset1 = zero_point,          offset2 = zeros(float_dtype)
- minval mode     (arg is not None): offset1 = q_min(quant_dtype),  offset2 = minval
- no-offset mode:                    offset1 = zeros(quant_dtype),  offset2 = zeros(float_dtype)
```

Modules provided: `PalettizeModule(indices, lut, vector_axis=None)`, `SparseModule(nonzero_data, mask)`,
plus quantize/dequantize modules. `wrap_for_parametrization(cls)` produces a
`…Parametrization` subclass usable with `torch.nn.utils.parametrize.register_parametrization`.

`inject_subbyte_tensors(program)` (public-ish, `coreai_torch._compression.utils`) runs three passes
on the ExportedProgram **in place** and is called automatically by `add_exported_program`:
```
- _inject_subbyte_in_lut    → UintxTensor for LUT indices   (nbits = log2(lut.shape[-2]))
- _inject_subbyte_in_quant  → IntxTensor / UintxTensor for blockwise-shift-scale data (+ zero_point)
                              and FP4 detection (sets tensor.future_dtype = torch.float4_e2m1fn_x2)
- _inject_subbyte_in_sparse → UintxTensor(nbits=1) for sparse masks
```
Supported nbits: `QUANTIZATION_SUPPORT_NBITS = (2, 4, 8)`, `PALETTIZATION_SUPPORT_NBITS = (1, 2, 3, 4, 6, 8)`.
Unsupported → `RuntimeError(f"{nbits}-bit quantization is not supported. Supported nbits: …")`.
nbits resolution order for quant: explicit `input_dtype` arg (index 4) → a sibling
`…quantization_n_bits` state-dict entry (coremltools-produced models) → inferred from data range.

FP4 signature detection (verbatim comment):
> "FP4 signature: uint8 input, output last dim = 2 × input last dim"

**Gotcha:** the manual path (e.g. `tests/ops/test_custom_ops.py`) must call
`inject_subbyte_tensors(exported)` **before** `TorchConverter().add_exported_program(...)` if it
built the EP by hand — but `add_exported_program` already calls it, so calling twice is the tested
pattern and is idempotent-ish.

Quantized-weight externalization tests exist but are **currently skipped**:
> `@pytest.mark.skip(reason="transform_with_custom_compression_ops has been deprecated. Consider
> removing these tests or use an alternative way to generate quantized weights")`
They used `coremltools.optimize.torch.quantization.PostTrainingQuantizer` +
`PostTrainingQuantizerConfig` with `{"quantization_scheme": "symmetric", "granularity": "per_block",
"weight_dtype": "int4", "block_size": 4}`. The regression they guard: the externalize re-export used
to discard sub-byte injection (si4 weights degraded to si8).

---

## 17. Debugging numerics — `coreai_torch.debugging`

**Preview-only env vars** (`docs/api/debugging.md`, verbatim note):
```bash
export USE_LOCAL_COREAI=1
export ENABLE_DEBUG_INFO=1
```
> "During the current preview, set the following environment variables to ensure operation-level
> debug metadata is preserved and available to these tools"

Also `VERIFY_DEBUGINFO_LOCATIONS` (read by `_get_verify_debuginfo_locations_enabled()`; accepts
`true|1|yes|on`, default off "for performance reasons").

### 17.1 Validator (NaN / Inf isolation)

```python
def create_validator_for_exported_program(
    program: torch.export.ExportedProgram,
    strategy: SearchStrategy[torch.fx.Node, torch.fx.Graph] | None = None,
    use_caching: bool = True,
) -> Validator[torch.fx.Node, torch.fx.Graph]

async def create_validator_for_coreai_program(
    program: AIProgram,
    entry_point: str,
    strategy: SearchStrategy[Operation, Module] | None = None,
    use_caching: bool = True,
    specialization_options: SpecializationOptions | None = None,
) -> Validator[Operation, Module]
```
`Validator` methods: `await validator.check_for_nans(inputs)`, `check_for_infs(inputs)`,
`check(predicate, inputs)`. Returns `Validator.Result(failed_nodes: list, unknown_nodes: list)`
sorted topologically. Default strategy = `LevelOrderStrategy.bisection(graph, batch_size=10)`.
`show_progress=True` by default (uses `_ProgressBar`).

Docs example (verbatim):
```python
from coreai_torch.debugging.validator import create_validator_for_exported_program

model = MyModel().eval()
exported = torch.export.export(model, args=(torch.randn(1, 10),))

validator = create_validator_for_exported_program(exported)
result = await validator.check_for_nans(inputs=(torch.randn(1, 10),))

if result.failed_nodes:
    print(f"NaN detected at: {result.failed_nodes[0]}")
```
Custom check (docs verbatim):
```python
def check_large_values(outputs):
    return any(abs(arr).max() > 1000.0 if arr is not None else False for arr in outputs)

result = await validator.check(check_large_values, inputs=example_input)
```

### 17.2 Search strategies

`LevelOrderStrategy` static factories, all `(graph, batch_size=10, initial_scope_id=None)`:
`top_down()` (`level_selector=lambda _: 0`), `bottom_up()` (`len(level_nodes)-1`),
`bisection()` (`len(level_nodes)//2`), `auto()` ("selects the sparsest level (fewest nodes) at each step").

### 17.3 Comparator (PyTorch ↔ Core AI)

```python
async def create_comparator_for_programs(
    source_program: torch.export.ExportedProgram,
    target_program: AIProgram,
    target_entry_point: str,
    strategy=None,
    use_caching: bool = True,
    exclude_ops: frozenset[str] = _DEFAULT_EXCLUDED_OPS,   # view/reshape ops; pass frozenset() to disable
    specialization_options: SpecializationOptions | None = None,
) -> Comparator[...]
```
Usage (docs verbatim):
```python
comparator = await create_comparator_for_programs(
    source_program=exported_program, target_program=coreai_program, target_entry_point="main"
)
result = await comparator.compare_with_tolerance(
    inputs={"x": example_input}, rtol=1e-5, atol=1e-8
)
if result.failed_nodes:
    for source_op, target_op in result.failed_nodes:
        print(f"Mismatch: {source_op} vs {target_op}")
```
The ID map between torch and coreai ops is auto-extracted from the AIProgram's debug info.

### 17.4 Inspector

```python
from coreai_torch.debugging.inspector import CoreAIInspector
from coreai.runtime import AIModel

ai_model = await AIModel.load(asset_path)
inspector = CoreAIInspector(model=ai_model, function_name="main")
results = await inspector.get_intermediates_for_ops(
    [1, 5, 10, 15], inputs={"x": np.random.randn(2, 4).astype(np.float32)}
)
```
Class hierarchy: `Inspector` (ABC) → `CachingInspector`, `TorchFXInspector(exported_program=…)`,
`CoreAIInspector(model, function_name="main", temp_dir=None)`. `IntermediateKind` enum exists.

### 17.5 Benchmarker

```python
async def benchmark_coreai_program(
    coreai_program: AIProgram,
    inputs: dict[str, Any],
    entry_point: str = "main",
    num_runs: int = 1,
    excluded_operations: tuple[str, ...] | None = None,   # default ("coreai.graph", "coreai.constant")
    specialization_options: SpecializationOptions | None = None,
) -> BenchmarkResult
```
`BenchmarkResult.write_summary(sys.stdout)`, `.get_module_timings()` →
`{name: ModuleTiming}` with `.aggregated_op_stats.average` (ms). Also `OperationTiming`,
`Statistics`, `Measurement` dataclasses.
**Note:** the only benchmarker test is `@pytest.mark.skip(reason="debugger issue (will be solved later)")`.

### 17.6 Graph diff

```python
def compute_exported_program_diff(source_program, target_program) -> GraphDiff
def compute_coreai_program_diff(source_program, target_program, *, entry_point: str | None = "main") -> GraphDiff
def compute_per_graph_diff(...)          # composite-aware
def format_multi_graph_diff(...)
def write_diff(diff, source_graph, target_graph, *, output=None, indent_size=2, max_items=None) -> None
```
`GraphDiff` fields: `is_isomorphic`, `source_to_target_mapping`, `target_to_source_mapping`,
`unmapped_source_nodes`, `unmapped_target_nodes`, `unmapped_source_edges`, `unmapped_target_edges`,
`summary: GraphDiffSummary`, `source_graph`, `target_graph` (both `nx.DiGraph`).
`GraphDiffSummary`: `source_node_count`, `target_node_count`, `source_edge_count`,
`target_edge_count`, `mapped_node_count`, `unmapped_{source,target}_node_count`,
`unmapped_{source,target}_edge_count`.
Matching uses `_greedy_topological_match` — "much faster than `subgraph_isomorphisms_iter` for large
graphs, providing O(n) matching instead of exponential worst case".

### 17.7 Torch intermediates dump / load

```python
def save_intermediates(
    program: ExportedProgram,
    inputs: tuple | list,
    output_dir: str | Path,
    node_filter: Callable[[torch.fx.Node, Any], bool] = _default_node_filter,
    coreai_program: AIProgram | None = None,
    enable_autocast: bool = False,
    model_name: str = "main",
) -> str      # returns path to metadata JSON

def load_intermediates(metadata_path: str | Path, device: str | torch.device | None = None) -> DebugTrace
```
Output layout: `{output_dir}/{model_name}.aimodelintermediates/` containing numpy files +
`metadata.json`. `load_intermediates` accepts either the `.aimodelintermediates` directory or the
JSON path; a directory not ending in `.aimodelintermediates` raises `ValueError`.
`DebugTrace` has `.inputs`, `.outputs`, `.intermediates` dicts.
Other helpers: `get_torch_to_coreai_output_mapping`, `get_torch_to_ops_mapping`,
`fetch_intermediate_values`.

### 17.8 Debug info

- `TorchConverter(mode=TorchConverter.Mode.RELEASE)` → op IDs only, no stack traces.
- `coreai_torch.debugging.debug_info.strip_debug_info(program: AIProgram) -> None` — in-place;
  replaces every op location with an unknown-file location plus a fresh sequential `coreai` op ID.
  "useful for reducing asset size when full debug traces are no longer needed."
- `parse_debug_infos(debug_infos_bytes: bytes) -> list[DebugInfoRecord]`;
  `DebugInfoRecord.find_by_odix_id(id)`, `.find_by_torch_op_id(id)`.
- Module hierarchy naming: `_get_module_hierarchy(node, registry)` returns entries like
  `"Linear$1"`, `"Block$2"` — `<ClassName>$<per-type instance count>`, reversed (outermost last →
  the list is reversed so it reads outermost-first). Repeated calls to the *same* submodule instance
  reuse the same count (see `tests/test_get_module_hierarchy.py`, which asserts ≥2 distinct `Block$n`
  and ≥3 distinct `Linear$n` for a model that calls `self.block(x)` twice).
- `_DebugInfoRecorder.Config(include_stack_trace: bool, verify_debuginfo_locations: bool)`.

---

## 18. CLI tools

Both live under `tools/` and are run as plain scripts (`python tools/<name>/<name>.py`); they are
**not** console-script entry points (no `[project.scripts]` in pyproject).

### 18.1 `tools/graphdiff/graphdiff.py`

```
usage: graphdiff [-h] [--entry-point NAME] [--max-items N] [--output FILE] SOURCE TARGET

positional arguments:
  SOURCE              source AIModel asset (.aimodel)
  TARGET              target AIModel asset to compare against (.aimodel)

options:
  -h, --help          show this help message and exit
  --entry-point NAME  coreai.graph entry point to compare (default: all graphs)
  --max-items N       limit the number of items shown in the diff table
  --output FILE       write output to FILE (.html for styled HTML, otherwise plain text)
```
Exit codes: `0` isomorphic, `1` structural differences, `2` input error.
Composite-aware by default: diffs `main` vs `main`, matches composite sub-graphs via paired
`coreai.invoke` callees (e.g. `@sdpa_abc123` ↔ `@sdpa_def456`), diffs each, reports unmatched.
Deps: `coreai` (for `AIModelAsset`), `networkx`.

### 18.2 `tools/freqop/freqop.py`

```
usage: freqop [-h] [--plot] FILE [FILE]

positional arguments:
  FILE        AIModel asset to analyze (.aimodel)
  FILE        optional second AIModel asset to compare against

options:
  -h, --help  show this help message and exit
  --plot      open a matplotlib histogram (grouped bar chart for two-file mode)
```
Counts `coreai.*` ops; composite ops (graphs with a `composite_decl`) are reported as
`composite.<name>` (e.g. `composite.layer_norm`, `composite.scaled_dot_product_attention`).
Two-file mode prints a Delta column and marks differing ops with `*`.
`--plot` requires matplotlib (not a declared dependency).

### 18.3 `scripts/release.sh`

7-step post-merge release: pre-flight → lint → tests → tag+push → build from tag → `uv publish` → docs deploy.
Flags: `-y|--yes`, `--dry-run`, `--skip-lint`, `--skip-tests`, `--skip-docs`, `--skip-publish`,
`--commit SHA`, `--publish-url URL`, `-h|--help`.
Env: `UV_PUBLISH_URL` (default `https://upload.pypi.org/legacy/`), `UV_PUBLISH_TOKEN`, or
`UV_PUBLISH_USERNAME`+`UV_PUBLISH_PASSWORD`. Version is read from `coreai_torch/__version__.py`; tag = `v{VERSION}`.

### 18.4 `scripts/smoke_test_wheel.sh`

```
./scripts/smoke_test_wheel.sh                    # build + smoke test
./scripts/smoke_test_wheel.sh --no-build         # use existing dist/*.whl
./scripts/smoke_test_wheel.sh --python 3.11,3.12 # restrict versions
```
Installs the wheel into a clean `uv venv` per Python version (default `3.11,3.12,3.13`,
`uv pip install --prerelease=allow`) and asserts every public symbol imports, `__all__` matches real
attributes, every non-private submodule imports, and `TorchConverter()` constructs.

### 18.5 `docs/deploy.sh`

`./docs/deploy.sh [--remote <name>]` — builds with `sphinx-build -b html` per version
(`VERSION_MATCH=<version>`), stages, and publishes via `ghp-import`. Requires `sphinx-build` and
`ghp-import` (`uv sync --extra docs`). Aborts on a dirty working tree.

### 18.6 Dev/test commands (README)

```bash
pip install coreai-torch                 # install
uv sync                                  # from source
uv sync --extra test && uv run pytest tests/ -n auto
uv run pytest docs/ --nbmake -v          # test the notebooks
uv sync --extra docs && uv run jupyter-book build docs/ && open docs/_build/html/index.html
pre-commit install --hook-type pre-commit --hook-type pre-push
uv run ruff check . --fix && uv run ruff format .
```
**Doc/reality mismatch:** README says `uv run jupyter-book build docs/`, but `docs/conf.py` is a
plain Sphinx conf (theme `shibuya`, `myst_nb`) and `tests/test_docs.py` / `docs/deploy.sh` both use
`sphinx-build -b html docs <out>`. `jupyter-book` is **not** in any extra.

### 18.7 Custom pytest options (`tests/conftest.py`)

```
--compute-unit-kind {interpreter,cpu,gpu,neural_engine}   (default: interpreter)
  interpreter   - bundled runtime (USE_LOCAL_COREAI=1)
  cpu           - SpecializationOptions.cpu_only() (BNNS)
  gpu           - preferred ComputeUnitKind.gpu() (MPSGraph)
  neural_engine - preferred ComputeUnitKind.neural_engine()
  Anything other than 'interpreter' unsets USE_LOCAL_COREAI so the OS runtime is used.
--dump-optests                                            (writes op_tests/<path>/test_data.npz + main.AICode.bc)
```
Tests marked `control_flow` are auto-skipped when `--compute-unit-kind != interpreter`:
> "Higher-order ops like `torch.cond` / `while_loop` are not yet supported by the cpu/gpu/neural_engine
> compute unit runtimes."

---

## 19. Runtime API surface touched by this repo (`coreai-core`)

From `docs/coreai-core/tutorials/*.ipynb` and `tests/utils.py`:

```python
from coreai.authoring import AIModelAsset, AIProgram, Module, TensorSpec, MetalParameter, CustomMetalKernel, Context
from coreai.runtime import NDArray, InferenceFunction, AIModel, SpecializationOptions, StorageKind, ComputeUnitKind
from coreai._compiler.dialects import coreai as ops        # graph-building primitives (temporary location)
from coreai._compiler.ir import Value, RankedTensorType, Location, Module, ...
```
Warning from the coreai-core tutorial (verbatim):
> "**APIs in flux.** A few graph-building primitives (the `@graph` decorator and elementwise op
> constructors) currently live under `coreai._compiler` while the public authoring surface is
> finalized. They will be re-exported from `coreai.authoring` in a follow-up release."

Authoring a graph by hand:
```python
module = Module.create()
with module:
    @ops.graph
    def main(x: Annotated[Value, TensorSpec(shape=[2,3], dtype=np.float32)]
             ) -> Annotated[Value, TensorSpec(shape=[2,3], dtype=np.float32, name="y")]:
        return ops.add(x, x)

module.verify()
program = AIProgram(module)
asset = program.save_asset(Path("./hello-graph.aimodel"))
```
> "`AIProgram.save_asset(path)` writes the program out as an `.aimodel` directory — a small bundle
> containing the program bytecode plus a `metadata.json` file."

Running:
```python
asset = AIModelAsset.load(asset_path)          # reads the header only; compilation is lazy
async with asset.executable() as model:
    print(model.function_names)
    function: InferenceFunction = model.load_function("main")   # KeyError if missing
    desc = function.desc                       # .name, .input_names, .output_names, .state_names
    outputs = await function({"x": NDArray(np.full((2,3), 1.5, dtype=np.float32))})
    result = outputs["y"].numpy()              # materialize INSIDE the block
```
> "Materialize the result inside the block — the model's backing buffers are only guaranteed valid
> until the context exits."

Alternative one-shot load: `await AIModel.load(path)` (optionally with `SpecializationOptions`).
`SpecializationOptions` — "pass to `asset.executable(options)` to pin the preferred compute unit
(CPU / GPU / Neural Engine) or enable debug mode. *(macOS only.)*"; also
`.with_debug(enabled=True)`, `.cpu_only()`, `.from_preferred_compute_unit_kind(compute_unit_kind=ComputeUnitKind.gpu())`.
`StorageKind` — `NDArray(data, backing=...)`: `BYTES` (default), IOSurface-backed, Metal-backed.
`AIProgram` extras used in-tree: `.optimize()`, `.save_asset(path)`, `._mlir_module`,
`._from_mlir_module(module)`, `._save_bytecode(path)`, `str(program)` (prints MLIR).

---

## 20. Gotchas / footguns (consolidated)

1. **`run_decompositions()` is mandatory.** `add_exported_program` validates and raises with an
   actionable message otherwise. Even `aten.linear` trips it (`test_error_message_lists_ops`).
2. **`get_decomp_table()` vs `torch.export.default_decompositions()`** — the latter decomposes
   `instance_norm` into `_native_batch_norm_legit`, which is unsupported → `ValueError: … unsupported ATen ops`.
3. **`to_coreai()` does not optimize.** Always call `coreai_program.optimize()`. Stateful models
   *require* it (mutation outputs become handle tokens).
4. **Naming params are keyword-only** in the real signatures (`*` in the source), unlike the docs.
5. **`export_fn` is keyword-only and required** on `add_pytorch_module`.
6. **Externalization requires `add_pytorch_module`.** `add_exported_program` has no externalization.
7. **`target_class=RMSNormImpl`, not `RMSNorm`.** The wrapper is not the externalization target.
8. **Unmatched `ExternalizeSpec` target classes only warn**, they don't error — typos are silent.
9. **Each externalized call site gets its own `noinline` graph** with a UUID suffix
   (`@name_<8 hex>`) so runtime doesn't dedupe invocations. Don't pattern-match on exact symbol names.
10. **Composite `forward` args must all be tensors**; optionals must be `Tensor | None = None`,
    never default tensors. Non-tensor args → `TypeError`.
11. **64-bit dtypes are silently narrowed** (int64→int32, float64→float32). `check_result_type`
    tolerates both. Values beyond int32 range will be wrong.
12. **`INT64_MAX` slice ends are clamped to `INT32_MAX`** — a real correctness carve-out.
13. **`is_causal` in the ATen SDPA path becomes a materialized `-1e4` float mask**, and the emitted
    `op_attrs` say `is_causal = false, window_size = 0`. Only the `composite_ops.SDPA` module path
    preserves them as attributes.
14. **`composite_ops.SDPA` causal mask is lower-right**, torch's is upper-left. They differ whenever
    `q_len != k_len` (i.e. every decode step).
15. **RoPE requires fp32 `position_ids` and `freqs`** (`torch._check` enforced).
16. `RMSNormImpl` deliberately computes the square/mean in fp32 (fp16 max is 65504) and has a
    *special case* for fp32 scale + non-fp32 input (Gemma3).
17. **`torch.repeat_interleave` has a dynamic-shape bug from torch 2.8 through ≥2.10**;
    `_vanilla_repeat_interleave` works around it with `index_select`.
18. **`register_custom_kernels` must precede `add_exported_program`.**
19. **Metal bool scalars widen to `ui8` in IR** (i1 rejected by the `metal4_kernel` verifier);
    scalar values are baked as MSL literals shadowing the parameter.
20. **Metal kernel inputs need `StorageKind.METAL` backing at runtime.**
21. `int` Metal scalars must fit in int32; float scalars must be finite.
22. **`generate_composite_decl` mutates the `op_attributes` dict you pass** (`["version"] = version`).
23. **Doc drift:** `atan2.default` and `masked_scatter.default` are supported but missing from
    `docs/api/supported-aten-ops.md`; `generate_composite_decl`'s documented signature is wrong;
    README's `jupyter-book build` command doesn't match the Sphinx-based docs setup.
24. **Torch > 2.13.0 emits a `UserWarning`** at import time but is allowed.
25. **`coreai-core==1.0.0b2` is exactly pinned** — a beta. Lowering code depends on private
    `coreai._compiler.*` APIs that "may move or change without notice".
26. `max_pool2d` rejects dynamic stride; transposed conv3d unsupported
    (`ValueError("Transposed conv3d is not yet supported…")`); non-zero `output_padding` on
    non-transposed conv unsupported.
27. **Higher-order ops (`cond`, `while_loop`) only run on the interpreter compute unit** in tests —
    "not yet supported by the cpu/gpu/neural_engine compute unit runtimes".
28. `torch.empty` is lowered to **zeros** ("for deterministic behavior").
29. `_ProgressBar` is disabled when stdout is not a TTY (`disable=not sys.stdout.isatty()`).
30. Sub-byte compression injection is **skipped in `add_pytorch_module` when `externalize_modules`
    is set** — it happens on the re-exported program instead. Historical bug: the re-export used to
    drop it (si4 → si8).
31. `docs/faq.md`, `docs/whats-new.md`, `docs/release-notes.md`, `docs/resources.md` are all
    "Coming soon" placeholders — no release notes exist yet.

---

## 21. Recent commit log (context on what's actively changing)

```
4529671 Remove run_transforms helper in favor of result.optimize() (#50)
28defcc Cast mean operand to output dtype before reduce_mean (#42)
35589fa Fix `aten.min.dim` argmin indices at dtype-extremal minima (#43)
698f11a Fix conv transpose lowering (#40)
ef1181b Allow newer versions of PyTorch than we have verified. (#39)
bd14e8f Support Latest Version of PyTorch (#38)
cd21d5a Bug fix: max_pool2d uses default stride value (#36)
1b3cb3b atan2: propagate NaN instead of returning 0/pi at x == +/-0 (#35)
40312b5 [converter] Fix negative axis in quantize/dequantize lowering (#24)
a43cc84 [converter] implement aten::atan2 conversion (#23)
a374b48 Try to fix pad review comments (#31)
e3fc00c Add missing tests for the pas fix (#30)
45a231f do not decompose pad op (#29)
71ca4a8 sync : bump version, update coreai-core to b2 (#28)
779df85 _aten_to_core: gate si32 arange path on all operands being integer-typed (#27)
e8dac1d fix(arange): preserve static output shape for float-dtype arange with integer bounds (#25)
ea728d6 Skip externalize for submodules not invoked in the exported graph (#18)
a68f1ad _aten_to_core: implement masked_scatter (#16)
ced5268 [converter] Support SymInt repeats in aten.repeat lowering (#15)
9eeea28 [converter] Fix cat lowering when promoted shape still has dynamic axes (#14)
70c9a7d tests: make compression + debugging tests cross-platform (#17)
53d6bdd _aten_to_core, _utils: harden mixed-source SymInt lowerings under dynamic shapes (#13)
3a3ed6f ci: add GitHub Actions workflow on self-hosted Apple Silicon runners (#12)
7171b3b Initial commit
```
Only 24 commits total (`--depth 50` clone reaches the initial commit) — the repo was open-sourced
recently. Themes: numerics correctness in lowerings, dynamic-shape/SymInt hardening, PyTorch
version support, and migrating tests off private pass APIs onto `AIProgram.optimize()`.

Notable fix details worth quoting in a guide:
- `28defcc`: `torch.mean(x, dtype=…)` on an int tensor crashed with
  `ValueError: mean[0]: dtype si32 vs f32`; fix casts the operand to the node's output element type
  before `reduce_mean` (mirrors `replace_sum_dim_intlist`).
- `35589fa`: "Core AI has argmax but not argmin" — `min.dim` derives argmin from `argmax(~x)` for
  integers (bitwise complement, overflow-free) and `argmax(-x)` for float/bool.
- `698f11a`: `padding`/`output_padding` are now handled natively by Core AI's `conv_transpose2d`
  (previously emulated with pre-pad + post-crop).
- `cd21d5a`: `max_pool2d` with omitted stride now defaults to `kernel_size`.
- `1b3cb3b`: `atan2` NaN branch added last so it overrides the zero/quadrant branches.
- `40312b5`: quantize/dequantize negative axis was normalized as `axis + rank - 1` (off by one).

---

## 22. Contribution policy (relevant to guide "how to add an op")

`CONTRIBUTING.md` — **In scope:** bug fixes and conversion failures; "Support for missing ops or
layer types via existing conversion mechanisms (e.g. adding an entry to the ATen-to-Core resolver,
fixing a numerical mismatch in an existing lowering)"; minor enhancements to existing extension
points; docs; tests.
**Not in scope:** "Major new conversion features or architectural changes"; "Changes to the core API
surface." Also: *"We keep the API surface intentionally limited to ensure reliability and
maintainability across PyTorch releases."* All contributions require tests; numerical-accuracy
changes require a correctness test. AI-assisted contributions are allowed but "Low-quality pull
requests and issues … will be treated as spam and moderated accordingly."

---

## 23. Test-suite patterns worth mining for a guide

`tests/utils.py` contains the reusable end-to-end validation harness:

```python
await validate_numerical_output(
    model=MyModel(),          # OR coreai_program=<AIProgram> + torch_out=<expected>
    x=torch.randn(2, 4),      # named tensor inputs become forward() kwargs
    dynamic_shapes=make_dynamic_shapes(x=["batch", None]),
    state_names=["kv_cache"], input_names=["x"], output_names=["result"],
    num_calls=2, atol=1e-2, rtol=1e-5,
    remove_decomps=[...], prepare_program=lambda ep: ..., print_exported_graph=True,
    run_optimize_passes=False, custom_kernels=[kernel], metal_inputs=True,
)
```
Two modes documented in its docstring: (1) end-to-end with `model=`, (2) pre-converted with
`coreai_program=` + `torch_out=`. Default tolerance `atol=1e-2` because "FP16 accuracy is flaky".

IR assertions use `filecheck` (the `filecheck` PyPI package, `Matcher.from_opts(Options(...))`):
```python
from tests.utils import filecheck_pattern, get_ir

filecheck_pattern(str(coreai_program), check_file="""
    // CHECK: coreai.name = "image"
    // CHECK: coreai.name = "logits"
""")
```
`get_ir(model, dynamic_shapes=None, remove_decomps=None, **kwargs) -> str` exports, converts,
optimizes and returns `str(coreai_program)`.

Test counts (rough op coverage signal): `tests/ops/test_ops.py` 219 tests,
`tests/ops/test_ops_ir.py` 293 tests, `tests/ops/test_custom_ops.py` 18,
`tests/subgraph/test_elementwise.py` 3, `tests/subgraph/test_conv.py` 2.

Composite-op tests validate against **MLX** (`mlx.nn.RMSNorm`) and **HuggingFace transformers**
(`LlamaRMSNorm`, `MistralRMSNorm`, `MixtralRMSNorm`, `Qwen2/3/3MoE/3NextRMSNorm`,
`Gemma3RMSNorm`, `Llama4TextRMSNorm`) — a good cross-framework parity story for a guide.
Those tests are macOS-only ("MLX is stable only on MacOS").

---

## 24. Source inventory (every file I actually read this session)

Repo root: `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-torch`

**Read in full or near-full:**
- `README.md`, `CONTRIBUTING.md`, `pyproject.toml`, `MANIFEST.in`, `.pre-commit-config.yaml`,
  `.python-version`, `.github/workflows/ci.yml`
- `coreai_torch/__init__.py`, `coreai_torch/__version__.py`
- `coreai_torch/converter.py` (all 1082 lines)
- `coreai_torch/_decomp.py`, `coreai_torch/_validate.py`, `coreai_torch/_type_mapping.py`,
  `coreai_torch/_composite_declaration.py`, `coreai_torch/externalize.py`,
  `coreai_torch/_custom_to_core.py`, `coreai_torch/_torch_metal_kernel.py`
- `coreai_torch/composite_ops/{__init__,_rms_norm,_gather_mm,_gated_delta_update,_utils,_sdpa,_rope}.py`
- `coreai_torch/_compression/{__init__,utils}.py`
- `docs/index.md`, `docs/api/TorchConverter.md`, `docs/api/supported-aten-ops.md`,
  `docs/api/composite-ops.md`, `docs/api/generate-composite-decl.md`, `docs/api/ExternalizeSpec.md`,
  `docs/api/TorchMetalKernel.md`, `docs/api/debugging.md`
- `docs/api/composite-ops/{module-class,aten-derived,rms-norm,rope,sdpa,gather-mm,
  gated-delta-update,batch-norm,group-norm,hard-sigmoid,instance-norm,layer-norm,
  linalg-vector-norm,log-softmax,pixel-shuffle}.md`
- `docs/getting-started/installation.md`, `docs/faq.md`, `docs/whats-new.md`,
  `docs/release-notes.md`, `docs/resources.md`, `docs/coreai-core/index.md`,
  `docs/coreai-core/api/coreai.md`, `docs/conf.py`, `docs/_static/versions.json`
- Notebooks (all cells dumped via a JSON script):
  `docs/getting-started/quickstart.ipynb`, `docs/guides/conversion-workflows.ipynb`,
  `docs/guides/composite-ops.ipynb`, `docs/guides/externalization.ipynb`,
  `docs/guides/custom-op-lowering.ipynb`, `docs/guides/custom-metal-kernels.ipynb`,
  `docs/coreai-core/tutorials/construct-a-graph.ipynb`,
  `docs/coreai-core/tutorials/run-an-aimodel.ipynb`
- `tests/conftest.py`, `tests/utils.py`, `tests/test_lower_simple_model.py`,
  `tests/test_validate.py`, `tests/test_docs.py`, `tests/test_get_module_hierarchy.py`,
  `tests/api/test_torch_converter.py`
- `tools/graphdiff/README.md`, `tools/freqop/README.md`,
  `scripts/release.sh`, `scripts/smoke_test_wheel.sh`, `docs/deploy.sh` (partial)

**Read in substantial part (targeted ranges / greps):**
- `coreai_torch/_utils.py` (lines 1–200, 296–496, 903–1105, 1101–1421, 1421–1721, 1721–1965)
- `coreai_torch/_aten_to_core.py` (lines 1–120, 1197–1336, 3194–3541, 3543–3741; function index)
- `coreai_torch/_debug_locations.py` (lines 1–120 + full symbol index)
- `coreai_torch/_compression/custom_layers.py` (op registrations + selected docstrings)
- `coreai_torch/debugging/{validator,benchmarker,comparator,search_strategy,inspector,graph_diff,debug_info,torch_utils}.py`
  (public entry points + dataclasses)
- `tests/test_converter.py` (lines 1–90, 296–476, 588–718, 895–1083)
- `tests/test_stateful.py` (lines 1–140, 1000–1100, 1185–1340; greps)
- `tests/test_externalize.py` (lines 1–200, 1500–1770, 2901–3130; class index)
- `tests/composite_ops/{conftest.py,test_rms_norm.py,test_sdpa.py}` (selected ranges)
- `tests/ops/{conftest.py,test_ops.py,test_custom_ops.py}` (selected ranges)
- `tests/dsl/{conftest.py,test_custom_kernels.py,test_scalar_inputs.py,test_failures.py,test_dtype_specialization.py}` (heads)
- `tests/debugging/{test_validator.py,test_benchmarker.py}` (heads)
- `git log --oneline -50`; `git show` for `4529671`, `ef1181b`, `bd14e8f`, `28defcc`, `35589fa`,
  `698f11a`, `cd21d5a`, `1b3cb3b`, `40312b5`, `45a231f`, `53d6bdd`, `9eeea28`

**Not read (out of scope / very large):** `tools/graphdiff/graphdiff.py` (1237 lines) and
`tools/freqop/freqop.py` (818 lines) implementations (READMEs cover their CLIs);
`coreai_torch/_compression/{_intx,_floatx,_types}.py`; most of `coreai_torch/_aten_to_core.py`'s
individual lowerings; the bulk of `tests/ops/test_ops_ir.py`.

---

## 25. Open questions / unverified

1. **Full `CorePasses` catalog.** Only `_CORE_OPTIMIZE`, `_UPDATE_SIGNATURE_TO_HANDLES`,
   `_PROPAGATE_HANDLE_UPDATES` are attested (from the deleted `run_transforms`). What else
   `AIProgram.optimize()` runs, whether it takes arguments (pass list / opt level), and whether it
   is sync or async in coreai-core 1.0.0b2 — **UNVERIFIED** (`coreai` is not installed locally;
   in-tree call sites are all bare synchronous `program.optimize()`).
2. **`AIProgram.optimize()` signature** — no in-tree call passes arguments. Whether options exist is
   unknown.
3. **`.aimodel` internal layout.** The tutorial says "a small bundle containing the program bytecode
   plus a `metadata.json` file"; exact file names other than `metadata.json` are **UNVERIFIED**
   (`_save_bytecode` writes `main.AICode.bc` in the optest dump path, suggesting `*.AICode.bc`).
4. **iOS/macOS OS version gates.** Nothing in this repo states a minimum OS. CI runs on macOS
   "tahoe" ARM64 self-hosted runners. Deployment-target requirements for `.aimodel` are
   **UNVERIFIED here** — likely documented in coreai-core / the Core AI framework docs.
5. **Image inputs.** There is **no image-specific API** in coreai-torch (no `ImageType`,
   no color-space handling like coremltools). Image models are plain `(N,C,H,W)` float tensors
   (MobileNetV2 example). Whether Core AI has a separate image-input feature type is
   **UNVERIFIED / likely out of this package's scope**.
6. **`ENABLE_DEBUG_INFO`** is documented in `docs/api/debugging.md` but is **never read anywhere in
   this repo's Python** — it must be consumed by coreai-core. Semantics UNVERIFIED.
7. **`USE_LOCAL_COREAI`** likewise: set/unset by `tests/conftest.py` but consumed by coreai-core.
8. `coreai_torch.debugging` has an **empty `__init__.py`** (license header only) — none of the
   debugging symbols are re-exported at package level, so all docs imports are deep module paths.
   Whether that's intentional is unknown.
9. `docs/contributing.md` was listed in the tree but not read (presumably an include of
   `CONTRIBUTING.md`).
10. `Version` enum in `composite_ops/_utils.py` only has `v1`; both `rope()` and
    `scaled_dot_product_attention()` raise `NotImplementedError` for any other version. No v2 exists yet.
11. The `sphinx_llm` extension (emitting `llms.txt`, `llms-full.txt`, `*.html.md`) is referenced by
    `tests/test_docs.py` and `docs/conf.py` but is **not listed in the `docs` extra** in
    `pyproject.toml` — the test `importorskip`s it. Provenance of `sphinx_llm` UNVERIFIED.
12. `coreai_torch/_compression/_intx.py` / `_floatx.py` / `_types.py` (`IntxTensor`, `UintxTensor`,
    `Float4Tensor`) internals not read — packing layout details UNVERIFIED beyond
    "`.elem` holds packed uint8 bytes" and "`future_dtype` carries the logical dtype".
