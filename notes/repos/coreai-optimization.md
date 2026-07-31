# `apple/coreai-optimization` — deep dive notes (package: `coreai-opt`, import: `coreai_opt`)

Research notes taken directly from the local clone at
`/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-optimization`
(`--depth 50`, branch `main`, HEAD = `cd95cb2 fix: try per-channel act quant for shared observers but fall back to per-tensor if unsafe (#52)`).

Everything below was read in-session. Line references are `path:line` into that clone.
Anything I did not verify is explicitly flagged **UNVERIFIED**.

---

## 1. Identity, version, scope

- PyPI distribution name: **`coreai-opt`**. Python import package: **`coreai_opt`**.
- Version: `src/coreai_opt/_about.py:10` → `__version__ = "0.2.1"`.
- Copyright headers are `# Copyright 2026 Apple Inc.` — this is 2026-era code.
- License: BSD-3-Clause (`LICENSE`, `pyproject.toml:19`).
- `Development Status :: 3 - Alpha` (`pyproject.toml:22`).
- README one-liner (`README.md:3`):
  > "`coreai-opt` provides implementations of popular model optimizations such as quantization, palettization (codebook-based compression), and pruning, for PyTorch models, customized for deployment on Apple Silicon via Core AI."
- Docs site: <https://apple.github.io/coreai-optimization/>
- Related repos it names (`README.md:75-79`): **Core AI** (framework), **coreai-torch** (PyTorch → `.aimodel` converter, the *downstream* step), **coreai-models** (ready-to-run optimized models + AI skills that wrap coreai-opt workflows).
- CHANGELOG (`CHANGELOG.md`): `0.2.0` released **2026-06-08** (initial release), `0.2.1` released **2026-07-02`.

**Relationship to `coremltools.optimize`:** this *is* the successor/sibling. It targets Core AI (`.aimodel`) first, and keeps a `ExportBackend.CoreML` compatibility path for `coremltools`. `coremltools` was *removed as a runtime dependency* in commit `edd4720` (changelog fragment `changelog.d/31.changed`):
> "Replace the coremltools-based 1D k-means used by palettization with a vendored C++ core that is JIT-compiled at runtime via `torch.utils.cpp_extension`. `coremltools` is no longer a runtime dependency (it is now an optional dependency, installable via the `coreml` extra). This requires a C++ compiler to be available on the host at runtime."

---

## 2. Install, dependencies, version gates

### Install (`README.md:11-37`, `docs/src/introduction/installation.md`)

```bash
pip install coreai-opt
# or
uv pip install coreai-opt
```

From source:

```bash
make env                 # creates .venv and installs everything
source .venv/bin/activate
```

### Hard requirements (`pyproject.toml:20-53`)

```toml
requires-python = ">=3.11,<3.14"          # 3.11 / 3.12 / 3.13 only
dependencies = [
    "ninja>=1.11",                        # needed by torch.utils.cpp_extension for kmeans1d
    "numpy>=2",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "safetensors>=0.5.3,<=0.7.0",
    "setuptools>=42",                     # runtime, for torch.utils.cpp_extension
    "torch>=2.8.0,<=2.11.0",
    "torchao>=0.15.0,<=0.17.0",
    "tqdm>=4.65",
]
```

- **A C++ toolchain must be present on the host at runtime** — the vendored kmeans1d `_core.cpp` is JIT-compiled by `torch.utils.cpp_extension.load()` on first palettization use (`src/coreai_opt/deps/_kmeans1d/core.py:30-55`). Flags: `["-std=c++11", "-O2", "-DNDEBUG"]`, plus `-stdlib=libc++` on darwin.
- Comment at `pyproject.toml:44-48`: "PyTorch >= 2.9.0 requires torchao >= 0.15.0 … Opting option 1" (a stricter floor for everyone rather than a runtime check).
- Supported OS classifiers: **macOS** and **POSIX :: Linux**.
- `[tool.uv] environments` restricts resolution to `darwin+arm64` and `linux+x86_64` (`pyproject.toml:188-191`).

### Extras (`pyproject.toml:56-65`)

```toml
[project.optional-dependencies]
coreai = ["coreai-core==1.0.0b2", "coreai-torch==0.4.1", "scikit-learn>=1.7.2"]
coreml = ["coremltools>=8.3", "numpy>=2,<2.4"]
```

**Exact pins worth recording**: `coreai-core==1.0.0b2`, `coreai-torch==0.4.1`.

### Torch matrix dependency groups (`pyproject.toml:134-153`)

| group | torch | torchao | torchvision |
| --- | --- | --- | --- |
| `torch_2_8` | 2.8.0 | 0.15.0 | 0.23.0 |
| `torch_2_9` | 2.9.1 | 0.15.0 | 0.24.1 |
| `torch_2_10` | 2.10.0 | 0.16.0 | 0.25.0 |
| `torch_2_11` | 2.11.0 | 0.17.0 | 0.26.0 |

These four groups are declared `conflicts` in `[tool.uv]` (`pyproject.toml:198-205`).
`Makefile:59-60`: `HIGHEST_TORCH_GROUP := torch_2_11`, `LOWEST_TORCH_GROUP := torch_2_8`.

### Other tool config

- ruff: `target-version = "py311"`, `line-length = 100`, `isort.known-first-party = ["coreai_opt"]`, `pylint.max-args = 8`.
- mypy: `python_version = "3.11"`, `disallow_untyped_defs = true`, `plugins = ["pydantic.mypy"]`.
- pytest markers (`pyproject.toml:285-288`): `seed(value)` ("no value uses default seed (42), value=None means nondeterministic seeding") and `slow`.
- towncrier for changelog: `directory = "changelog.d"`, types Added/Changed/Deprecated/Removed/Fixed/Security.
- uv security knob: `exclude-newer = "3 days"` — "only install distributions on PyPI for at least 3 days"; `coreai-core` / `coreai-torch` are exempted so CI tests their latest releases.

---

## 3. Package tree (src layout)

`src/coreai_opt/` — 29,337 total Python LOC across `src/` (`wc -l`).

```
coreai_opt/
  __init__.py               # exports CoreMLExportError, ExportBackend, __version__
  _about.py                 # __version__ = "0.2.1"
  common.py                 # CompressionType, ExportBackend, CoreMLExportError, _StrEnum, deprecated-alias enum meta
  base_model_compressor.py  # _BaseModelCompressor ABC (prepare/finalize/calibration_mode/training_mode)
  py.typed
  config/                   # generic 3-level config machinery (shared by all techniques)
    compression_config.py   # OpCompressionConfig / ModuleCompressionConfig / CompressionConfig + mixins
    spec/                   # CompressionSpec, CompressionSimulatorBase, CompressionComponentFactoryBase, CompressionTargetTensor
  quantization/
    quantizer.py            # public Quantizer facade (dispatches graph vs eager)
    base_quantizer.py
    _axis_defaults.py       # default per-channel/per-block weight axes per module type
    _fake_quant_utils.py
    _export_utils.py
    _utils.py
    config/                 # QuantizerConfig / ModuleQuantizerConfig / OpQuantizerConfig / QATSchedule / KVCacheQuantConfig / ExecutionMode
      _presets/             # .presets.w8() / w4() / w4_per_block()
    spec/                   # QuantizationSpec, granularity, qscheme, qformulation, qparams_calculator, range_calculator, fake_quantize, factory
    _graph/                 # PT2E/torchao graph-mode impl: quantizer, annotation registry/utils/config, conv-bn utils, prepare_for_export
    _eager/                 # __torch_function__ eager impl
  palettization/
    base_palettizer.py
    config/                 # KMeansPalettizerConfig / ModuleKMeansPalettizerConfig / OpKMeansPalettizerConfig (+ _presets)
    spec/                   # PalettizationSpec, granularity, fake_palettize, factory, errors
    kmeans/                 # KMeansPalettizer, _KMeansFakePalettize, _efficient_kmeans, supported_ops_registry, _prepare_for_export
  pruning/
    magnitude_pruner.py     # MagnitudePruner
    base_pruner.py
    config/                 # MagnitudePrunerConfig / ModuleMagnitudePrunerConfig / OpMagnitudePrunerConfig + sparsity_schedule
    spec/                   # PruningSpec, PruningScheme (Unstructured/ChannelStructured), PruneImplBase
    supported_ops_registry.py
  casting/                  # cast_to_16_bit_precision / cast_fp32_to_fp16 / cast_int32_to_int16
  inspection/               # ModelInspector + types (ModelSummary, ModuleInfo, OpInfo, InputEdge, BoundaryEdge, ModuleContext, SourceFrame)
  coreai_utils/             # MLIR/AIProgram-level compression: quantize_weights / palettize_weights / sparsify_weights
    passes/, _utils/, _coreai_imports.py, common.py (DType, QScheme, CompressionGranularity)
  deps/_kmeans1d/           # vendored MIT kmeans1d (core.py + _core.cpp), JIT-compiled at runtime
  _utils/                   # torch/fx/config/registry/spec/import/export/metadata/casting/eager utils + insertion/torch_function/*
```

**Naming convention enforced by tests**: `tests/test_api_visibility.py` asserts every public package declares `__all__`, that `__all__` contains no submodule names, and that every public symbol defined in a public module is re-exported by some package `__init__`. `make api-list` prints the whole public API surface (`Makefile:239-241`, `scripts/make/print_api_list.py`).

---

## 4. Top-level public API

`src/coreai_opt/__init__.py`:

```python
from . import palettization, pruning, quantization
from ._about import __version__
from .common import CoreMLExportError, ExportBackend

__all__ = ["CoreMLExportError", "ExportBackend", "__version__"]
```

### `ExportBackend` (`src/coreai_opt/common.py:137-160`)

```python
class ExportBackend(_StrEnum, metaclass=_DeprecatedMemberEnumMeta):
    _TORCH = auto()
    CoreML = auto()
    CoreAI = auto()

    __deprecated_aliases__: ClassVar[dict[str, str]] = {"MIL": "CoreML", "MLIR": "CoreAI"}
```

- `ExportBackend.MIL` and `ExportBackend.MLIR` still work but emit `DeprecationWarning` (both attribute access *and* value lookup, case-insensitively — see `_DeprecatedMemberEnumMeta.__getattr__` / `__call__` at `common.py:62-99`).
- `_TORCH` is a real member: "for torch-based evaluation" / dynamic-quant escape hatch.

### `CoreMLExportError` (`src/coreai_opt/common.py:163-177`)

```python
class CoreMLExportError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(f"{message} Use backend=ExportBackend.CoreAI instead.")

    @classmethod
    def from_dtype(cls, dtype, context) -> CoreMLExportError: ...
    @classmethod
    def from_config(cls, config, context) -> CoreMLExportError: ...
```

Every CoreML export error message ends with "Use backend=ExportBackend.CoreAI instead."

### `CompressionType` (`common.py:110-134`) and CoreML codes

```python
_COREML_COMPRESSION_CODES = {"quantization": 3, "palettization": 2, "pruning": 1}

class CompressionType(_StrEnum):
    QUANTIZATION = auto(); PALETTIZATION = auto(); PRUNING = auto()
    def to_coreml_code(self) -> int: ...
```

---

## 5. The universal compressor lifecycle

Defined by `_BaseModelCompressor` (`src/coreai_opt/base_model_compressor.py`) and documented in `docs/src/introduction/how_to_use_coreaiopt.md`.

| Method | Semantics |
| --- | --- |
| `__init__(model, config)` | compressor is built from an `nn.Module` + a config object |
| `prepare(...) -> nn.Module` | compresses weights + inserts fake-quantize / fake-palettize / mask ops; a forward on the result reflects compression. **Data-free PTQ happens here.** May modify in place — use the returned model. |
| `calibration_mode(...)` (ctx mgr) | enables observers / sensitivity collection during forwards |
| `training_mode(...)` (ctx mgr) | QAT: train mode + observers + fake quant. **Only `Quantizer` implements it** |
| `finalize(model=None, backend=ExportBackend.CoreAI, *, mmap_dir=None)` | freezes qparams, swaps fake ops for backend ops/metadata |

Internal prepared-marker (`base_model_compressor.py:21,57-69`):

```python
_COREAI_OPT_PREPARED_ATTR = "_coreai_opt_prepared"
model.register_buffer(_COREAI_OPT_PREPARED_ATTR, torch.tensor(True), persistent=False)
```

Registered as a **non-persistent buffer** so it survives `deepcopy` of an `fx.GraphModule` but stays out of `state_dict()`. `KMeansPalettizer.finalize()` deletes it so the palettized model can be handed to `Quantizer` for joint compression (`palettization/kmeans/palettizer.py:420-423`).

Doc notes worth quoting (`how_to_use_coreaiopt.md:39,79`):
- "You don't need to put the model in `.eval()` or `.train()` before calling `prepare()` — the API runs the trace internally in eval mode and restores the original mode when it returns."
- "The finalized model inherits the current training mode, so call `.eval()` on it before running inference or downstream conversion."

Base `calibration_mode` / `training_mode` raise `NotImplementedError` with messages like
`"{cls} does not implement training_mode(). This compressor doesn't support training time compression."`

---

## 6. Quantization

### 6.1 Entry point

```python
from coreai_opt.quantization import Quantizer, QuantizerConfig
config = QuantizerConfig.presets.w8()
quantizer = Quantizer(model, config)
prepared_model = quantizer.prepare(example_inputs)   # example_inputs MUST be a tuple
finalized_model = quantizer.finalize()               # backend defaults to ExportBackend.CoreAI
```

`coreai_opt.quantization.__all__` = `ExecutionMode, InvalidExecutionModeError, ModuleQuantizerConfig, QuantizationSpec, Quantizer, QuantizerConfig`.
`coreai_opt.quantization.spec.__all__` (`spec/__init__.py:34-55`) =
`DynamicQParamsCalculator, GlobalMinMaxQParamsCalculator, MinMaxRangeCalculator, MovingAverageQParamsCalculator, PerBlockGranularity, PerChannelGranularity, PerTensorGranularity, QParamsCalculatorBase, QuantizationComponentFactory, QuantizationFormulation, QuantizationGranularity, QuantizationScheme, QuantizationSpec, RangeCalculatorBase, RunningRangeMixin, StatefulQParamsCalculatorBase, StatelessQParamsCalculatorBase, StaticQParamsCalculator, default_activation_quantization_spec, default_weight_quantization_spec`.
`coreai_opt.quantization.config.__all__` = `ExecutionMode, InvalidExecutionModeError, KVCacheQuantConfig, ModuleQuantizerConfig, OpQuantizerConfig, QATSchedule, QuantizerConfig`.

### 6.2 `Quantizer` exact signatures (`src/coreai_opt/quantization/quantizer.py`)

```python
class Quantizer(_BaseQuantizer):
    def __init__(self, model: nn.Module, config: QuantizerConfig | None = None)

    def prepare(
        self,
        example_inputs: tuple[Any, ...],
        dynamic_shapes: dict[str, Any] | tuple[Any] | list[Any] | None = None,
        export_with_no_grad: bool = True,
    ) -> nn.Module | fx.GraphModule

    def finalize(
        self,
        model: nn.Module | fx.GraphModule | None = None,
        backend: ExportBackend = ExportBackend.CoreAI,
        *,
        mmap_dir: str | PathLike[str] | None = None,
    ) -> nn.Module | fx.GraphModule

    @contextmanager
    def calibration_mode(self, model=None)
    @contextmanager
    def training_mode(self, model=None)

    def step(self) -> None                       # advances the QAT schedule
    def enable_observer(self, module: nn.Module | None = None) -> None
    def disable_observer(self, module: nn.Module | None = None) -> None
    def enable_fake_quant(self, module: nn.Module | None = None) -> None
    def disable_fake_quant(self, module: nn.Module | None = None) -> None
```

Notes from the source:
- `dynamic_shapes` and `export_with_no_grad` are **graph-mode only**; passing them in eager mode emits a `UserWarning` and they are ignored (`quantizer.py:365-377`).
- `prepare()` caches `self._module_config_dict = self._config.build_module_config_dict(...)` **before** the underlying prepare, "so that `module_type_configs` can match original types. After prepare, modules can be modified such that the types no longer match" (`quantizer.py:360-363`).
- `finalize()` runs two validations first: `_validate_mmap_dir_constraints` and `_validate_no_persistent_observer_calculators`.
- `mmap_dir` is **eager-mode + CoreAI-only**; graph mode raises `ValueError("mmap_dir is only supported in eager execution mode, got execution_mode=graph.")` (`_graph/quantizer.py:1051-1054`). It also requires all tensors on CPU (`_utils/export_utils.py:validate_mmap_backend_and_device`): error text — *"mmap_dir requires the prepared model to be on CPU; found tensor(s) on device(s) …. Call model.cpu() before finalize(mmap_dir=…). mmap is a CPU-only mechanism"*.
- Dynamic quantization can't be exported: `_validate_no_persistent_observer_calculators` raises `NotImplementedError` naming every affected FakeQuantize module and telling you to `Use backend=ExportBackend._TORCH for torch-only inference` (`quantizer.py:410-433`).
- `finalize(backend=CoreAI)` in **eager** mode "frees the original dense weights" (docstring `quantizer.py:478-480`).

### 6.3 `QuantizationSpec` — every field

`src/coreai_opt/quantization/spec/spec.py:357-370`:

```python
class QuantizationSpec(CompressionSpec):          # pydantic BaseModel, frozen=True, extra="forbid"
    dtype: torch.dtype = torch.int8
    qscheme: QuantizationScheme = QuantizationScheme.SYMMETRIC
    qformulation: QuantizationFormulation = QuantizationFormulation.ZP
    granularity: QuantizationGranularity = PerTensorGranularity()   # BeforeValidator maybe_build_from_dict
    fake_quantize_cls: type[FakeQuantizeImplBase] = "default"
    qparam_calculator_cls: type[QParamsCalculatorBase] = "default"
    range_calculator_cls: type[RangeCalculatorBase] = "minmax"
    float_range: list[float | int | None] = [None, None]
    scale_dtype: torch.dtype | None = None
```

Computed (cached) fields: `n_bits`, `target_dtype`, `_quant_range`, `quant_min`, `quant_max`.

`SUPPORTED_DTYPES` (class var, `spec.py:376-390`):
```
torch.int8, torch.int4, torch.int2,
torch.uint8, torch.uint4, torch.uint2,
torch.float8_e4m3fn, torch.float8_e5m2,
torch.float4_e2m1fn_x2
```
String aliases (`spec.py:394-398`): `"float4_e2m1fn" → torch.float4_e2m1fn_x2`, `"float8_e4m3" → torch.float8_e4m3fn`, `"float8_e8m0" → torch.float8_e8m0fnu`. Any other string resolves via `getattr(torch, name)`.

`get_target_dtype` mapping (`spec.py:606-635`): sub-byte ints → `int8`/`uint8`; `float4_e2m1fn_x2` → `float8_e4m3fn` ("All FP4 representable values are exactly representable in FP8").

`get_quant_range` examples straight from the docstring (`spec.py:653-662`):
```
int8 symmetric            -> (-128, 127)
int8 symmetric_with_clip  -> (-127, 127)
int4 symmetric            -> (-8, 7)
int4 symmetric_with_clip  -> (-7, 7)
uint8                     -> (0, 255)
uint8 symmetric_with_clip -> (0, 255)   # same as symmetric
float4_e2m1fn_x2          -> (-6.0, 6.0)   # torch.finfo not implemented; hardcoded
float8_e4m3fn             -> (-448.0, 448.0)
float8_e5m2               -> (-57344.0, 57344.0)
```

Validators (all raise `ValueError`):
- FP dtype ⇒ `qscheme` must be `SYMMETRIC` (`validate_qscheme_for_fp_quant`).
- FP dtype ⇒ `qformulation` must be `ZP` (`validate_qformulation_for_fp_quant`).
- `scale_dtype` may only be `None` or `torch.float8_e8m0fnu`; must be `None` for integer dtypes; **FP4 auto-resolves `scale_dtype=None` → `torch.float8_e8m0fnu`** in a `mode="before"` model validator (`resolve_scale_dtype`, `spec.py:486-500`).
- `float_range` must be a length-2 list/tuple of ints/floats/None (bools rejected explicitly because `bool` subclasses `int`), `min <= 0`, `max >= 0`, `min < max`.

Scale formulas from the class docstring (`spec.py:126-156`):

| dtype | qscheme | quant range | scale | zero_point |
| --- | --- | --- | --- | --- |
| INT8 | SYMMETRIC | [-128,127] | `max_abs / 127.5` | 0 |
| INT8 | SYM_W_CLIP | [-127,127] | `max_abs / 127` | 0 |
| INT8 | ASYMMETRIC | [-128,127] | `range / 255` | `clip(-128 - round(min_val_neg/scale), -128, 127)` |
| UINT8 | SYMMETRIC | [0,255] | `max_abs / 127.5` | 128 |
| UINT8 | SYM_W_CLIP | [0,255] | `max_abs / 127.5` | 128 |
| UINT8 | ASYMMETRIC | [0,255] | `range / 255` | `clip(-round(min_val_neg/scale), 0, 255)` |

FP: zero-point always 0. `scale_dtype=None` (FP8 only): `scale = max_abs / fp_max` (448.0 for E4M3, 57344.0 for E5M2). `scale_dtype=float8_e8m0fnu` (FP4 and FP8): power-of-2 per OCP MX spec, `scale = 2^(floor(log2(max_abs)) - target_max_pow2)` with `target_max_pow2` = **2 (FP4 E2M1), 8 (FP8 E4M3), 15 (FP8 E5M2)**.

MINVAL formulation table (`spec.py:157-172`) — `quant_offset == q_min`; **not allowed with FP4/FP8**.

Export-backend constraint quoted verbatim (`spec.py:174-179`):
> "CoreML export only supports ``ZP``. Specs with ``qformulation=MINVAL`` are rejected during finalize with CoreML Export-backend. CoreAI export supports both ``ZP`` and ``MINVAL``."

Two factory functions (`spec.py:716-735`):

```python
def default_weight_quantization_spec() -> QuantizationSpec:
    return QuantizationSpec(dtype=torch.int8, qscheme="symmetric",
                            granularity=PerChannelGranularity(axis=0),
                            fake_quantize_cls="default", qparam_calculator_cls="static",
                            range_calculator_cls="minmax")

def default_activation_quantization_spec() -> QuantizationSpec:
    return QuantizationSpec(dtype=torch.int8, qscheme="symmetric",
                            granularity=PerTensorGranularity(),
                            fake_quantize_cls="default", qparam_calculator_cls="moving_average",
                            range_calculator_cls="minmax")
```

### 6.4 Enums

```python
class QuantizationScheme(Enum):              # spec/qscheme.py
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    SYMMETRIC_WITH_CLIPPING = "symmetric_with_clipping"
```
`_maybe_clip_bounds` sets `min_val = -max_val` only for `SYMMETRIC_WITH_CLIPPING` **and signed dtypes**.

```python
class QuantizationFormulation(_StrEnum):     # spec/qformulation.py
    MINVAL = auto()   # "minval"
    ZP = auto()       # "zp"
```
- ZP: `q = clamp(round(x/scale) + zero_point, qmin, qmax)`, `x' = (q - zero_point) * scale`
- MINVAL: `q = clamp(round((x - minval)/scale) + quant_min, qmin, qmax)`, `x' = (q - quant_min) * scale + minval`

### 6.5 Granularity (`spec/granularity.py`)

Registry keys: `"per_tensor"`, `"per_channel"`, `"per_block"` (used in YAML `granularity: {type: per_block, block_size: 32}`).

- `PerTensorGranularity()` — `axis: Literal[None] = None`.
- `PerChannelGranularity(axis: int | None = None)` — negative axes allowed (`-ndim <= axis < ndim`); `axis=None` resolved at `prepare()` for *weights only*.
- `PerBlockGranularity(axis: Annotated[int, ge=0, le=1] | None = None, block_size: int | tuple[int|-1, ...])`
  - **single-axis mode**: `axis ∈ {0,1}` + int `block_size`. `axis=None` allowed only for weights (resolved at prepare); otherwise `_handle_single_axis_block_size` raises `ValueError("axis must be specified when block_size is an int")`.
  - **multi-axis mode**: `axis` must be `None`, `block_size` a tuple with one entry per tensor dim; `-1` means "no blocking on this axis".
  - divisibility failures raise the internal `_BlockSizeMismatchError` (`spec/errors.py`) — which is *caught* by the fake-quant forward and turns into a **warning + permanently disabled FQ node** (see §6.10).
  - Table from the docstring:

| weight shape | axis | block_size | resulting block shape |
| --- | --- | --- | --- |
| `[C_out, C_in]` | 1 | 32 | `[1, 32]` |
| `[C_out, C_in]` | None | `(4, 8)` | `[4, 8]` |
| `[C_out, C_in, KH, KW]` | 0 | 16 | `[16, 1, KH, KW]` |
| `[C_out, C_in, KH, KW]` | None | `(4, 16, 3, -1)` | `[4, 16, 3, KW]` |

### 6.6 Default weight axes (`src/coreai_opt/quantization/_axis_defaults.py`)

```python
_WEIGHT_AXIS_SPECS: dict[type[nn.Module], _WeightAxisSpec] = {
    nn.Conv1d: _WeightAxisSpec(0, 1),
    nn.Conv2d: _WeightAxisSpec(0, 1),
    nn.Conv3d: _WeightAxisSpec(0, 1),
    nn.ConvTranspose1d: _WeightAxisSpec(1, 0),
    nn.ConvTranspose2d: _WeightAxisSpec(1, 0),
    nn.ConvTranspose3d: _WeightAxisSpec(1, 0),
    nn.Linear: _WeightAxisSpec(0, 1),
    nn.Embedding: _WeightAxisSpec(0, 1),
}   # (per_channel_axis, per_block_axis)
```

Graph mode maps aten ops → module types via `ATEN_OP_TO_MODULE_TYPE` (`_utils/torch_utils.py:38-47`):
`aten.conv1d.default→Conv1d`, `aten.conv2d.default→Conv2d`, `aten.conv3d.default→Conv3d`, `aten.conv_transpose1d.default→ConvTranspose1d`, `aten.conv_transpose2d.input→ConvTranspose2d`, `aten.conv_transpose3d.input→ConvTranspose3d`, `aten.linear.default→Linear`, `aten.embedding.default→Embedding`.

Docs table (`docs/src/quantization/config.md:72-88`):

**Per-channel defaults**: Conv*: axis 0, scale `(C_out,1,…,1)`; ConvTranspose*: axis 1, scale `(1,C_out,1,…,1)`; Linear: axis 0, scale `(C_out,1)`; Embedding: axis 0, scale `(V,1)`.
**Per-block defaults**: Conv*: axis 1, scale `(C_out, C_in/B, 1,…,1)`; ConvTranspose*: axis 0, scale `(C_in/B, C_out, 1,…,1)`; Linear: axis 1, scale `(C_out, C_in/B)`; Embedding: axis 1, scale `(V, D/B)`.

Failure modes:
- Unresolvable weight axis → `ValueError`: *"Weight fake-quantize modules with unresolved axis=None remain after applying defaults: … Provide an explicit axis value in the granularity configuration (e.g., PerChannelGranularity(axis=0))."*
- Shared weight whose consumers disagree → `ValueError`: *"Conflicting default axes for shared weight fake-quantize modules: … All consumers of a shared weight must resolve to the same default axis. Provide an explicit axis."*
- **Activations get NO axis defaults.** `validate_activation_axes()` raises: *"Activation fake-quantize modules with unresolved axis=None: … Activation quantization does not support axis=None. Provide an explicit axis value…"*

### 6.7 QParams calculators (`spec/qparams_calculator.py`)

Registry keys → classes:

| key | class | base | notes |
| --- | --- | --- | --- |
| `"default"` | `_DefaultQParamsCalculator` | marker | resolved by factory: **weights/LUT → `StaticQParamsCalculator`, activations → `MovingAverageQParamsCalculator`**; `__init__` raises `RuntimeError` if ever constructed |
| `"static"` | `StaticQParamsCalculator` | `StatefulQParamsCalculatorBase` | min/max of the current tensor only, no history |
| `"moving_average"` | `MovingAverageQParamsCalculator` | `RunningRangeMixin + Stateful` | EMA, `averaging_constant: float = 1e-2` |
| `"global_minmax"` | `GlobalMinMaxQParamsCalculator` | `RunningRangeMixin + Stateful` | element-wise running min/max |
| `"dynamic"` | `DynamicQParamsCalculator` | `StatelessQParamsCalculatorBase` | recompute per forward; **activations only** (factory raises `ValueError` for weight/LUT); supports variable-shape scales |

Key behaviors:
- Constructor kwargs (`QParamsCalculatorBase.__init__`): `dtype, qscheme, granularity, target_dtype, quant_min, quant_max, range_calculator, float_range, scale_dtype=None, **kwargs`.
- `granularity` setter raises `RuntimeError("Cannot change granularity after observer has been initialized. Granularity must be set before the first forward pass.")`.
- `_resolved_axis` uses an `Ellipsis` sentinel for "unresolved" and is resolved on first `forward()` from `tensor.ndim` (negative axes normalized).
- `StatefulQParamsCalculatorBase` registers buffers `scale`, `zero_point` (int32; `None` for FP), `minval` (`None` for FP). Buffer shapes are allocated on first forward and **must stay stable** (`copy_` requires shape compat) — hence the stateless class for dynamic quant.
- Optimization: if `_initialized` and both `float_range` bounds are set, forward short-circuits and returns cached qparams without touching the range calculator.
- `StatelessQParamsCalculatorBase.__init__` raises `ValueError` if any `float_range` bound is non-`None`: *"StatelessQParamsCalculatorBase requires float_range=[None, None] … Bounded ranges contradict the per-forward recompute contract."*
- `StatelessQParamsCalculatorBase.set_export_mode(True)` raises `NotImplementedError("Stateless quantization (e.g. dynamic) does not support export mode; qparams are input-dependent and cannot be frozen for export.")`.
- `_compute_e8m0_scale` is a bit-manipulation FLOOR-mode implementation (extract float32 biased exponent bits 23-30, subtract `target_max_pow2`, clamp to `[-bias, bias+1]`, re-encode, clamp to min normal float32). References OCP MX spec + torchao `mx_tensor.py`.
- Non-e8m0 path calls `torchao.quantization.quant_primitives.choose_qparams_affine_with_min_max(...)` with `eps=torch.finfo(torch.float32).eps`, `zero_point_dtype=torch.int32`.

**Custom calculator recipe** (from `docs/src/quantization/advanced.md:312-341`, verified against `RunningRangeMixin`):

```python
import torch
from coreai_opt.quantization.spec import QParamsCalculatorBase, RunningRangeMixin

@QParamsCalculatorBase.register("max_range")
class MaxRangeQParamsCalculator(RunningRangeMixin, QParamsCalculatorBase):
    """Track the widest observed min/max range across all calibration batches."""
    def update_running_range(self, min_val: torch.Tensor, max_val: torch.Tensor):
        return torch.minimum(self.running_min, min_val), torch.maximum(self.running_max, max_val)

spec = QuantizationSpec(dtype=torch.int8, qparam_calculator_cls="max_range")
```

> Gotcha the code makes explicit: `RunningRangeMixin` "Must appear before `StatefulQParamsCalculatorBase` in the MRO so that its `compute_qparams` and `_initialize_state` take precedence."

### 6.8 Range calculators (`spec/range_calculator.py`)

Only one registered: `@RangeCalculatorBase.register("minmax") class MinMaxRangeCalculator`. It uses `torchao.quantization.quant_primitives._get_reduction_params(block_size_list, tensor.size())` then `torch.amin/amax(dim=reduction_dims, keepdim=True)` and reshapes so each dim's size equals the number of blocks.
Extension point: subclass `RangeCalculatorBase`, implement `_generate_min_max`, `@RangeCalculatorBase.register("key")`.

### 6.9 Fake quantize (`spec/fake_quantize.py`)

`FakeQuantizeImplBase(CompressionSimulatorBase, torchao.quantization.pt2e.FakeQuantizeBase)`.
Only registered impl: `@FakeQuantizeImplBase.register("default") class _DefaultFakeQuantizeImpl`.

Forward logic (`fake_quantize.py:138-170`):
1. If `self._disabled` → passthrough.
2. If `observer_enabled[0] == 1` → run `qparams_calculator(tensor)` under `torch.no_grad()` ("Gradients should be computed through the actual QDQ path only"); a `_BlockSizeMismatchError` here triggers `_warn_and_disable()` and passthrough.
3. Else → `qparams_calculator.get_qparams()`.
4. If `fake_quant_enabled[0] == 1` → cast to fp32, run `_fused_fake_quant_dequant`, cast back to original dtype.

Overrides that matter:
- `disable_observer()` is a **no-op for stateless calculators** ("Applies to **any** caller (direct, `apply(disable_observer)`, `convert_pt2e`, QAT scheduling)").
- `enable_observer(False)` likewise ignored for stateless.
- `convert(self, model, observer_node)` is a deliberate **no-op**: "keep fake quant nodes intact during convert_pt2e. If this method is not present, torchao's convert method will try to replace fake quant nodes with its standard quantize/dequantize ops and fails in the process."

Math kernels (module-level functions):
```python
def _quantize_int(tensor, scale, quant_offset, float_offset, quant_min, quant_max):
    result = (tensor - float_offset) / scale
    result.round_(); result.add_(quant_offset)
    mask = (result >= quant_min) & (result <= quant_max)
    result.clamp_(quant_min, quant_max)
    return result, mask

def _dequantize_int(tensor, scale, quant_offset, float_offset):
    return (tensor - quant_offset) * scale + float_offset
```
Offset selection (`_select_int_offsets`): **ZP → `(zero_point, 0)`; MINVAL → `(quant_min, minval)`**.
FP path: `_quantize_float` = `clamp(tensor/scale, qmin, qmax)` then cast-decast; FP8 via `.to(dtype).to(torch.float32)`, FP4 via `torchao.prototype.mx_formats.kernels.f32_to_f4_unpacked` / `f4_unpacked_to_f32` (lazy imported inside the function).

STE autograd: `_FusedFakeQuantizeIntSTE` / `_FusedFakeQuantizeFloatSTE` (`torch.autograd.Function`). Documented rationale:
> "Fusing into one node reduces QAT memory: intermediate tensors (scaled, rounded, clamped) are local to forward and freed immediately instead of being retained by the autograd graph. Only a boolean mask (1 byte/element) is saved for backward, replacing multiple float32 intermediates (4 bytes/element each)."
Backward = `grad_output * mask` (clamped positions get zero gradient).

### 6.10 Silent-skip behavior (footgun)

If a tensor's shape isn't divisible by the configured `block_size`, the FQ module **logs a warning and permanently disables itself**, then the prepared model *drops that FQ node entirely*:
```
logger.warning("Tensor (target: %s) incompatible with block size configuration: %s. Skipping quantization.", ...)
```
Graph mode then calls `_remove_disabled_fake_quant_nodes(prepared_model)` after the init forward pass (`_graph/quantizer.py:1004-1006, 1307-1317`). Palettization has the analogous `_remove_disabled_fake_palett_modules`. **Net effect: a mis-sized block config silently leaves layers uncompressed.**

### 6.11 Config classes

Three-level hierarchy, precedence `module_name_configs > module_type_configs > global_config`, and inside a module `op_name_config > op_type_config > op_input/output/state_spec`.

```python
class QuantizerConfig(CompressionConfig[ModuleQuantizerConfig]):   # @final
    global_config: ModuleQuantizerConfig | None
    module_type_configs: dict[str | type[nn.Module], ModuleQuantizerConfig | None] = {}
    module_name_configs: dict[str, ModuleQuantizerConfig | None] = {}
    preserved_attributes: list[str] | None = None
    execution_mode: ExecutionMode = ExecutionMode.GRAPH
    kv_cache_quant_configs: dict[str, KVCacheQuantConfig] | None = None
    _CONFIG_KEY = "quantization_config"; _SPEC_KEY = "quantization_spec"
    presets: ClassVar[_QuantizerConfigPresets]
```

```python
class ModuleQuantizerConfig(ModuleCompressionConfig[OpQuantizerConfig, QuantizationSpec]):  # @final
    op_input_spec:    dict[str|int, QuantizationSpec|None] | None
    op_output_spec:   dict[str|int, QuantizationSpec|None] | None
    op_state_spec:    dict[str,     QuantizationSpec|None] | None
    op_type_config:   dict[str, OpQuantizerConfig|None] = {}
    op_name_config:   dict[str, OpQuantizerConfig|None] = {}
    module_input_spec:  dict[str|int, QuantizationSpec|None] = {}
    module_output_spec: dict[str|int, QuantizationSpec|None] = {}
    module_state_spec:  dict[str,     QuantizationSpec|None] = {}
    qat_schedule: QATSchedule | None = None
    presets: ClassVar[_ModuleQuantizerConfigPresets]
```

```python
class OpQuantizerConfig(OpCompressionConfig[QuantizationSpec]):
    op_input_spec / op_output_spec / op_state_spec   # same three, scoped to one op type/name
```

Defaults (`OpQuantizerConfig.get_default_*`):
- `op_input_spec  = {"*": default_activation_quantization_spec()}`
- `op_output_spec = {"*": default_activation_quantization_spec()}`
- `op_state_spec  = {"weight": default_weight_quantization_spec()}`

So bare `QuantizerConfig()` == **W_INT8(per-channel)_A_INT8(per-tensor)**.

Semantics captured in `config/compression_config.py`:
- `None` in a dict value means "disable compression for this scope"; a `mode="after"` validator normalizes it into a real config object with empty specs (`_normalize_none_op_configs`, `_normalize_none_module_configs`).
- **Omitting** a field applies defaults; **explicitly passing `None`** converts to `{}` via `BeforeValidator(_convert_none_to_empty_dict)`. This distinction is load-bearing.
- `module_type_configs` keys must be fully-qualified strings (`"torch.nn.modules.linear.Linear"`) or `nn.Module` subclasses. A string without a `.` raises `ValueError(f"Expected fully-qualified name, got {module_type}")`. Docs: "Short-form names like `torch.nn.Linear` are not supported."
- `module_name_configs` keys are matched with `re.fullmatch` (regex).
- `global_config` may **not** contain `module_input_spec` / `module_output_spec` / `module_state_spec` → `ValueError("global_config cannot have module_input_spec, module_output_spec, or module_state_spec. These are only allowed in module_type_configs and module_name_configs.")`
- Digit-string dict keys are coerced to ints (`_convert_digit_str_keys_to_int`); collisions raise `ValueError("Key collision detected: keys 'x' and 'y' both convert to …")`.
- Module **aliases** (same module object registered under two attribute paths, e.g. HF wrappers) are handled: `_build_module_alias_map` builds canonical↔alias maps so a regex targeting an alias still applies under the canonical name.
- Child modules inherit op-level settings recursively but **not** `module_*_spec` (`_prepare_config_for_child`).
- `ModuleQuantizerConfig`, `QuantizerConfig`, `KMeansPalettizerConfig`, `ModuleKMeansPalettizerConfig` are all `@final` **and** define `__init_subclass__` that raises `TypeError(f"{cls.__name__} cannot subclass … (marked final).")` — "Prohibit subclassing due to preset limitation: presets remain bound to the base class."

Setters/chaining (all return `Self`):
```python
config.set_global(cfg_or_None)
config.set_module_type(nn.Linear | "torch.nn.modules.linear.Linear", cfg_or_None)
config.set_module_name("model.lm_head", cfg_or_None)
config.only_for(nn.Linear, nn.Conv2d)          # or only_for([nn.Linear, "lm_head"])
config.without(nn.LayerNorm, nn.Embedding, "model.lm_head")
config.set_execution_mode(ExecutionMode.EAGER) # QuantizerConfig only
```
`only_for` disables `global_config` and deep-copies it onto each target. Calling it twice raises `ValueError("only_for requires a non-disabled global_config to redistribute as per-module overrides. If you've already called only_for or set_global(None), pass all targets in one only_for(...) call instead of chaining.")`. Note the doc caveat: the guard uses a private attr excluded from `model_dump`/`to_yaml`, so a round-tripped config accepts `only_for` again.

YAML/dict loading:
```python
config = QuantizerConfig.from_yaml("config.yaml")     # top-level key: quantization_config
config = QuantizerConfig.from_dict({"quantization_config": {...}})
config.to_dict()                                      # {"quantization_config": model_dump()}
```
`from_yaml` uses `yaml.safe_load`; empty YAML → `warnings.warn("Empty YAML content detected, returning None …")` and returns `None`; non-dict YAML → `ValueError`. Unexpected top-level keys → `RuntimeError`. Allowed top-level keys are only `_CONFIG_KEY` and `_SPEC_KEY` (`quantization_spec` / `palettization_spec` / `pruning_spec`, which exist purely to host YAML anchors).

### 6.12 Presets

`QuantizerConfig.presets` (`config/_presets/quantizer_config.py`) and `ModuleQuantizerConfig.presets` (same three, minus `execution_mode`):

| preset | signature | spec |
| --- | --- | --- |
| `w8` | `w8(*, axis: int|None = None, execution_mode=ExecutionMode.GRAPH)` | `int8`, SYMMETRIC, `PerChannelGranularity(axis)`, weight-only (`op_input_spec=None, op_output_spec=None`) |
| `w4` | `w4(*, axis=None, execution_mode=GRAPH)` | `int4`, SYMMETRIC, `PerChannelGranularity(axis)`, weight-only |
| `w4_per_block` | `w4_per_block(*, block_size: int = 32, axis=None, execution_mode=GRAPH)` | `int4`, SYMMETRIC, `PerBlockGranularity(axis, block_size)`, weight-only |

There is **no** `w2`, `w6`, `fp8`, or activation preset for quantization.

### 6.13 Execution modes

```python
class ExecutionMode(_StrEnum, metaclass=_DeprecatedMemberEnumMeta):
    GRAPH = auto()      # "graph"  (default)
    EAGER = auto()      # "eager"
    __deprecated_aliases__ = {"PT2E": "GRAPH"}
```
`ExecutionMode.PT2E` is deprecated → `GRAPH`. Unknown modes raise `InvalidExecutionModeError` ("Unknown execution_mode {x}. Expected 'graph' or 'eager'.").

Comparison table (docs `quantization/overview.md:215-223` + `Quantizer` docstring):

| Feature | Graph (default) | Eager |
| --- | --- | --- |
| Input → output | `nn.Module` → `fx.GraphModule` | `nn.Module` → `nn.Module` |
| Dynamic control flow | limited to `torch.export` support | supported |
| Conv+BN weight quant | BN folded into preceding Conv weight first | Conv weight unfused |
| Consecutive FQ dedup | dedups (`out→fq→fq→inp` ⇒ `out→fq→inp`) | duplication persists |
| Pattern fusion boundaries (Conv-BN-ReLU as one block) | supported | not supported |
| Shared quantizer for value-preserving ops (maxpool/avgpool/flatten/concat) | supported | not supported |
| Config op names | aten op names | `__torch_function__` call sites |
| `mmap_dir` in finalize | ✗ (`ValueError`) | ✓ (CoreAI only) |
| Palettization / pruning | n/a | **only mode supported** |

> "the two modes are **not guaranteed to produce equivalent quantized models**, and final model performance (accuracy and latency) may differ between modes even when using identical configurations." (`quantizer.py:83-87`)

Guidance: weight-only → eager is fine and slightly simpler (no BN folding); weight+activation → **graph strongly preferred** ("Eager mode may yield models with sub-optimal runtime performance").

`fx.GraphModule.train()/.eval()` after prepare/finalize: enabled via `torchao…allow_exported_model_train_eval`, but **"only dropout and batchnorm ops are affected via FX graph rewriting. User code branching on the `training` flag and other ops with mode-dependent behavior are not affected."**

### 6.14 Graph-mode internals (`quantization/_graph/`)

`GraphQuantizer.prepare()` order of operations (`_graph/quantizer.py:878-1021`):
1. Reject re-prepare; assert `example_inputs` is a non-empty tuple.
2. Record `original_train_mode` ("After export, GraphModule.training is always True").
3. Build `module_config_dict`, `module_name_to_state_names_map`, alias map; build `_AnnotationHandler` (a `torchao…pt2e.quantizer.Quantizer` subclass).
4. Collect `preserved_attributes` (missing ones → warning + skip).
5. `export_model(...)` → `torch.export.export`.
6. `_validate_kv_cache_quant_ops(exported_model)`.
7. If `torchao < 0.16.0`: `strip_non_aten_metadata_kwargs(graph)` because "torchao < 0.16.0 asserts that annotated nodes have empty kwargs"; restored afterwards with `restore_kwargs`.
8. `prepare_qat_pt2e(exported_model, quantizer)` — wrapped: any exception is re-raised as `type(e)(f"prepare_qat_pt2e call failed, with error: {e}")`.
9. `_postprocess_prepared_model()` = `remove_conv_bn_zeros_like_dtype` → `force_per_tensor_for_channel_altering_ops` → `apply_weight_axis_defaults_graph` → `validate_activation_axes`.
10. `allow_exported_model_train_eval(prepared_model)`.
11. `apply(disable_fake_quant)`, `apply(enable_observer)`, one `torch.no_grad()` forward in eval mode to init qparams.
12. `_remove_disabled_fake_quant_nodes`.
13. `apply(enable_fake_quant)`, `apply(disable_observer)` → **prepared state = FQ on, observers off**.
14. mark prepared, re-attach preserved attrs.

`GraphQuantizer.finalize()`:
1. `convert_pt2e(model)` (failure → `RuntimeError("Failed to convert model with convert_pt2e, with error: …")`).
2. `_post_conversion_process` → `fold_conv_bn_weights`.
3. backend switch:
   - `_TORCH`: no-op (KV-cache quant is a no-op here).
   - `CoreML`: raises `NotImplementedError` if `kv_cache_quant_configs` set; else `prepare_for_mil_export`.
   - `CoreAI`: `prepare_for_mlir_export`, then `_move_cache_dequant_to_output` per configured cache op.
4. `allow_exported_model_train_eval(finalized_model)` again ("convert_pt2e() re-applies `_disallow_eval_train`").

**Config validation rejects (graph mode only)** (`_validate_config`, `_graph/quantizer.py:679-731`):
- String keys other than `"*"` in any op/module input/output spec → `NotImplementedError("Only integer indices or '*' are supported for op and module input and output specs currently…")`
- `op_output_spec` keys other than `"*"` or `0` → `NotImplementedError("op_output_qspec currently supports setting for '*' or 0 tensor only…")`

**Annotation ordering** (`_sort_nodes_in_annotation_order`) — priority, decreasing:
1. config level (module_name > module_type > global)
2. pattern length (longer pattern wins)
3. config index within a level (later-listed config wins → smaller index)
4. topological order in the graph

`get_compressible_op_names(model) -> set[str]` is a public classmethod on `GraphQuantizer` that returns every node name any registered annotation pattern matches.

#### Annotation pattern registry (`_graph/_annotation_pattern_registry.py`)

Registered keys (verified by grep):
`conv_bn_act, conv_transpose_bn_act, conv_act, conv_transpose_act, conv_bn, conv_transpose_bn, conv, conv_transpose, linear_bn_act, linear_act, linear_bn, linear, embedding, matmul, matmul_act, add, add_act, mul, mul_act, sub, flatten, maxpool, avgpool, concat`

Base classes:
- `WeightedModulePattern` — conv/linear/embedding families.
- `NAryActPattern` — elementwise/matmul families; `use_act=True` expands to every supported activation appended to the base op. **Chains longer than 2 are not supported** ("the annotation function raises an error for chains longer than 2"); also "sequential partition matching requires each op type in the chain to be unique (e.g. `mul -> sub` works but `mul -> mul -> sub` does not)".
- `SharedObserverModulePattern` — `flatten`, `maxpool` (`max_pool1d/2d/3d`), `avgpool` (`avg_pool1d/2d/3d`, `adaptive_avg_pool1d/2d/3d`, `mean`), `concat` (`cat`, `concat`). Input and output share the **same FakeQuantize object**.

Registering with an existing key overwrites with a warning; there is **no `unregister`** — delete from `_AnnotationPatternRegistry.REGISTRY["key"]` directly.

Custom pattern example (docs `advanced.md:202-217`, verbatim):

```python
from coreai_opt.quantization._graph._annotation_pattern_registry import (
    NAryActPattern, _AnnotationPatternRegistry, _get_all_patterns_from_base_ops,
)

@_AnnotationPatternRegistry.register("div_act")
class DivActPattern(NAryActPattern):
    @classmethod
    def generate_patterns(cls):
        return _get_all_patterns_from_base_ops({torch.div, operator.truediv}, use_act=True)
```

#### Known-range activation overrides (graph mode only)

`docs/src/quantization/advanced.md:167-192` — at prepare time the quantizer **overrides the user's `qscheme` and `float_range`** for ops with analytically known output ranges (dtype is always preserved):

| Op | Output range | qscheme | float_range | Scale (int8) | Zero point (int8) |
| --- | --- | --- | --- | --- | --- |
| `hardsigmoid` | [0,1] | asymmetric | (0,1) | 1/255 | −128 |
| `hardtanh` | depends on node args | depends | depends | depends | depends |
| `relu` | [0,∞) | asymmetric | (0, None) | dynamic | −128 |
| `relu6` | [0,6] | asymmetric | (0,6) | 6/255 | −128 |
| `sigmoid` | [0,1] | asymmetric | (0,1) | 1/255 | −128 |
| `tanh` | [−1,1] | symmetric | (−1,1) | 2/255 | 0 |

`hardtanh`: bounds read from node args; symmetric iff `min_val == -max_val`. `relu6` is handled as `hardtanh(0,6)`.
**Eager mode does not perform these adjustments.** Implemented by `adjust_output_qspec_for_qscheme_and_propagate` (`_graph/_annotation_utils.py`), fixed in `0eabc57` ("Fix output spec adjustment for fixed qparams ops"; changelog fragment `180525445.fixed`).

#### The HEAD commit: per-channel activation quant for shared observers (`#52`, `cd95cb2`)

Lives in `src/coreai_opt/quantization/_graph/_utils.py`. Three op sets:

```python
_AXIS_RESIZING_ATEN_OPS = {
    aten.max_pool1d.default, aten.max_pool2d.default, aten.max_pool3d.default,
    aten.avg_pool1d.default, aten.avg_pool2d.default, aten.avg_pool3d.default,
    aten.adaptive_avg_pool1d.default, aten.adaptive_avg_pool2d.default, aten.adaptive_avg_pool3d.default,
    aten.mean.dim,
}
_AXIS_REORDERING_ATEN_OPS = {aten.transpose.int, aten.t.default, aten.permute.default}
_CHANNEL_ALTERING_ATEN_OPS = (
    _AXIS_RESIZING_ATEN_OPS | _AXIS_REORDERING_ATEN_OPS
    | {aten.flatten.using_ints, aten.reshape.default, aten.view.default, aten.unsqueeze.default}
)
```

`force_per_tensor_for_channel_altering_ops(model)` runs **after** `prepare_qat_pt2e`. For every channel-altering node it finds the FQ modules on inputs and users; if the **same object** appears on both sides (shared observer), it calls `_shared_granularity_axis_is_safe(fq, input_fq_node, node)` and downgrades to `PerTensorGranularity()` when unsafe.

`_shared_granularity_axis_is_safe` decision tree (fail-safe: *unproven ⇒ unsafe*):
- `PerTensorGranularity` → safe.
- not `PerChannelGranularity` (e.g. `PerBlockGranularity`) → **unsafe** (unconditional downgrade).
- rank changed between input/output → unsafe.
- unresolved axis → unsafe.
- op in `_AXIS_RESIZING_ATEN_OPS` → safe iff `input_shape[axis] == output_shape[axis]`.
- op in `_AXIS_REORDERING_ATEN_OPS` → safe iff `_op_preserves_axis_identity(op_node, axis)`:
  - `transpose.int` → `axis not in (dim0, dim1)` (negatives normalized with ndim)
  - `t.default` → `axis not in (0, 1)`
  - `permute.default` → `dims[axis] == axis`
  - fallback → `False`
- flatten/reshape/view/unsqueeze or unknown op → unsafe.

The downgrade now logs at **warning** level with an actionable message:
```
"Forcing per-tensor granularity for the shared observer around '%s' (was %s): this op either changes the size
 of the quantization axis between its input and output, or moves it to a different physical dimension (e.g.
 via transpose/permute), so a per-channel scale can't safely apply to both sides. To keep per-channel activation
 quantization here, choose a different axis that this op leaves untouched."
```

Bug it fixed (changelog `changelog.d/52.fixed`):
> "Fix per-channel activation quantization crashing with a shape-mismatch `RuntimeError` on MaxPool/AvgPool/AdaptiveAvgPool layers whose shared observer spans an axis the pool shrinks (e.g. a spatial axis under a stride>1 pool). Axes pooling never touches (batch, channel) keep working as per-channel; only the specific unsafe axis falls back to per-tensor…"

Subtle hazard the commit message calls out: **concat pulls transpose/permute into shared-observer territory** — "concat (a `SharedObserverModulePattern`, like MaxPool) ties both of its inputs to the same observer object, so a transpose/permute branch feeding concat alongside its own untransposed source gets its input and output tied together the same way MaxPool's are". A `transpose(2,3)` on a square tensor passes a size-only check but silently applies row-3's scale to column-3's data — hence `_op_preserves_axis_identity`.

Tests added: `test_shared_observer_forces_per_tensor_for_pool_axis_that_shrinks`, `test_shared_observer_preserves_per_channel_for_pool_axis_that_is_invariant` (18 parametrized cases over pool_type × dim), `test_shared_observer_forces_per_tensor_when_transpose_swaps_equal_size_axes`, `test_shared_observer_permute_axis_identity`, plus removal of a MNIST `act_granularity_axis=-1` skip.

#### CoreAI custom ops emitted at finalize

`_graph/_prepare_for_export.py:403-430`:
```python
# coreai.quantize(input, scale, output_dtype, zero_point=, minval=, axis=)
# coreai.dequantize(input, scale, zero_point=, minval=, axis=, input_dtype=, output_dtype=)
```
`input_dtype` is passed for integer dtypes because it is "needed for determining n_bits for subbyte (e.g. int4) quantization and for deriving q_min in the MINVAL formulation". `output_dtype` is set explicitly when `scale_dtype == torch.float8_e8m0fnu`. `coreai_torch` is **lazy-imported** (`lazy_import_coreai_torch`) so the package works without it installed.

### 6.15 QAT

```python
class QATSchedule(BaseModel):                        # frozen=True
    enable_observer: int = Field(default=0, ge=0)
    enable_fake_quant: int = Field(default=0, ge=0)
    disable_observer: int | None = Field(default=None, gt=0)
```
Validation: `enable_fake_quant >= enable_observer`; `disable_observer > enable_observer`; `disable_observer >= enable_fake_quant`. State at step `s`: `obs_on = enable_observer <= s < (disable_observer or ∞)`, `fq_on = s >= enable_fake_quant`.

Placement is a `ModuleQuantizerConfig` field, so different modules can have different schedules. The units are whatever cadence you call `quantizer.step()` at (per-batch or per-epoch). `step()`:
- raises `RuntimeError("step() must be called inside a training_mode() context.")` outside the ctx;
- increments `_step_count` **monotonically — never reset between training loops**;
- warns `UserWarning` if no schedule is configured anywhere ("step() has no effect…").

Two documented conflict rules (from `QATSchedule` docstring):
- Graph mode dedup: "The schedule of the **consuming module** is always applied to the deduplicated node, irrespective of the choice of deduplication made by the graph preparation."
- Shared weights: "the schedule of the **first module encountered in the module tree** is applied. A warning is emitted for the conflict if there is no fake-quantize node deduplication happening (in Eager execution mode)."

Manual API (`enable_observer` / `disable_observer` / `enable_fake_quant` / `disable_fake_quant`) is **mutually exclusive** with schedules:
```
RuntimeError: Enable/disable APIs for observers or fake quantization cannot be used with a qat_schedule
configured. To use these APIs, make sure there are no global or module-level qat_schedule configured.
For using the QAT schedule, refer to the step() API.
```
Each takes an optional `module: nn.Module` to scope to a subtree; unknown module → `ValueError(f"Module {module} is not a submodule of the prepared model.")`.

`training_mode()` is **not re-entrant**: nested entry raises `RuntimeError("Cannot enter training_mode() while already inside a training_mode() context. Nested training_mode() calls are not supported.")`.

Working QAT loop (docs `advanced.md:49-77`, verbatim-ish):

```python
config = QuantizerConfig(
    global_config=ModuleQuantizerConfig(
        qat_schedule=QATSchedule(enable_observer=0, enable_fake_quant=150, disable_observer=2000)
    )
)
quantizer = Quantizer(model, config)
prepared_model = quantizer.prepare(example_inputs)

optimizer = torch.optim.Adam(prepared_model.parameters(), lr=0.01)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

for epoch in range(30):
    with quantizer.training_mode():
        for batch, target in train_dataloader:
            optimizer.zero_grad()
            loss = criterion(prepared_model(batch), target)
            loss.backward()
            optimizer.step()
            quantizer.step()          # advance QAT schedule (per mini-batch)
        scheduler.step()
    val_metric = validate(prepared_model, val_dataloader)   # obs off, fq on
```

Equivalent YAML:
```yaml
quantization_config:
  global_config:
    qat_schedule:
      enable_observer: 0
      enable_fake_quant: 150
      disable_observer: 2000
```

### 6.16 Calibration semantics

Inside `calibration_mode()` (graph impl `_graph/quantizer.py:1160-1173`):
```python
self._model.apply(enable_observer)
self._model.apply(enable_weight_fake_quant)      # weight FQ stays ON
self._model.apply(disable_activation_fake_quant) # activation FQ OFF
with move_model_to_eval(self._model): yield
# finally:
self._model.apply(disable_observer)
self._model.apply(enable_fake_quant)
```
Rationale (docs `overview.md:113-117`): activation observers must see undistorted activations, but produced with quantized weights upstream "matching what the deployed model will actually see". This "weight fake quantization in calibration mode" behavior was added in commit `519f21c`.

Numerical caveat (docs note, `overview.md:123-125`):
> "For models with a **Conv + BatchNorm** pattern in the default graph execution mode, [prepared vs finalized] can differ slightly more: BatchNorm folding is handled with ops that are different between the prepared and finalized models (though algebraically equivalent). Weight quantization is matched closely … but activation quantization can still show a small numerical divergence."

### 6.17 KV-cache quantization (graph mode only)

```python
class KVCacheQuantConfig(BaseModel):   # frozen
    op_quantizer_config: OpQuantizerConfig
    @property
    def quant_input_idx(self) -> int   # the single int key of op_input_spec
```

Usage (from `tests/quantization/test_kv_cache_quantization.py:161-169` and the class docstring):

```python
QuantizerConfig(
    execution_mode="graph",
    global_config=ModuleQuantizerConfig(...),
    kv_cache_quant_configs={
        "mutable_cache_update_and_fetch": KVCacheQuantConfig(
            op_quantizer_config=OpQuantizerConfig(
                op_input_spec={1: default_activation_quantization_spec()},
                op_output_spec=None,
                op_state_spec=None,
            ),
        ),
    },
)
```

Rules enforced by validators:
- `op_input_spec` must have **exactly one non-negative int key** mapped to a non-`None` spec (no `"*"`, no multi-key) — "the finalize-side relocation needs a single, unambiguous input edge to act on".
- `op_output_spec` must be empty/None — "the finalize pass inserts the output dequantize".
- `op_state_spec` must be empty/None — "cache-update ops have no learnable state".
- Only `ExecutionMode.GRAPH` → else `ValueError`.
- Duplicate `op_type_config[op]` entries anywhere → `logger.warning` that the `kv_cache_quant_configs` entry wins at prepare time.
- After export, `_validate_kv_cache_quant_ops` raises `ValueError` if the key matches no node, or if `quant_input_idx >= len(node.all_input_nodes)`.
- Precondition the docstring states outright: "the cache op **must commute with quantize/dequantize** — i.e. a pure data-movement op (slicing, narrowing, copy). Arithmetic on cached values would silently produce a numerically wrong model."

What finalize does (CoreAI only): rewrites
`update -> coreai.quantize -> coreai.dequantize -> cache_op(x, dq, ...) -> consumer`
into
`update -> coreai.quantize -> cache_op(x, q, ...) -> coreai.dequantize -> consumer`
so the cache buffer stays in the quantized dtype (`_move_cache_dequant_to_output`, `_graph/_prepare_for_export.py:691-786`). CoreML backend raises `NotImplementedError`.

### 6.18 Eager-mode supported ops

`_eager/supported_ops_registry.py` registry keys: `conv1d, conv2d, conv3d, conv_transpose1d, conv_transpose2d, conv_transpose3d, linear, embedding, max_pool2d, adaptive_avg_pool2d, add, matmul, mul, sub`.
Eager tracing is built on the `__torch_function__` protocol (`_utils/insertion/torch_function/*`: `handler.py`, `modes.py`, `module_boundary_tracker.py`, `state_spec_resolver.py`, `preregistration_tracker.py`, `registered_optimizers_tracker.py`).

---

## 7. Palettization

### 7.1 API

```python
from coreai_opt.palettization import KMeansPalettizer, KMeansPalettizerConfig, ModuleKMeansPalettizerConfig, PalettizationSpec
```
`coreai_opt.palettization.__all__` = `KMeansPalettizer, KMeansPalettizerConfig, ModuleKMeansPalettizerConfig, PalettizationSpec`.
`coreai_opt.palettization.spec.__all__` = `PalettizationGranularity, PalettizationSpec, PerGroupedChannelGranularity, PerTensorGranularity, default_weight_palettization_spec`.

```python
class KMeansPalettizer(_BasePalettizer, _EagerCompressionComponentBuilderMixin):
    def __init__(self, model: nn.Module, config: KMeansPalettizerConfig | None = None)

    def prepare(self, example_inputs: tuple[torch.Tensor],
                sensitivity_path: str | None = None,
                num_workers: int = 1) -> nn.Module

    @contextmanager
    def calibration_mode(self, model=None, *, loss_fn: Callable,
                         sensitivity_path: str | None = None)

    def finalize(self, model=None, backend: ExportBackend = ExportBackend.CoreAI,
                 *, mmap_dir: str | PathLike[str] | None = None) -> nn.Module

    def save_sensitivities(self, path: str) -> None
    @classmethod
    def get_op_type_resolver(cls) -> Callable[[Callable], str | None]
```

**Palettization is eager-mode only** (docs `palettization/config.md:119`: "Palettization supports eager mode only."). There is no `training_mode()`.

### 7.2 `PalettizationSpec` (`palettization/spec/spec.py:86-93`)

```python
n_bits: Literal[1, 2, 3, 4, 6, 8] = 4
lut_qspec: QuantizationSpec | None = None
granularity: PalettizationGranularity = PerTensorGranularity()
cluster_dim: PositiveInt = 1
enable_per_channel_scale: bool = False
```

`_SUPPORTED_LUT_DTYPES = {torch.int8, torch.uint8, torch.float8_e4m3fn, torch.float8_e5m2}`.
`validate_lut_qspec` raises `ValueError` if: LUT dtype unsupported; `lut_qspec.granularity` isn't quantization `PerTensorGranularity`; `lut_qspec.qformulation == MINVAL` ("Use lut_qspec.qformulation=ZP instead.").

`default_weight_palettization_spec()` = `n_bits=4, lut_qspec=None, PerTensorGranularity(), cluster_dim=1, enable_per_channel_scale=False`.

Granularity registry keys: `"per_tensor"`, `"per_grouped_channel"`.
```python
class PerGroupedChannelGranularity(PalettizationGranularity):
    axis: int | None = Field(default=None, ge=0, le=1)
    group_size: int
```
`num_blocks_to_cluster` = `weight.shape[axis] // group_size`; raises `_IncompatibleGranularityError` if axis is None/out of range or the shape isn't divisible. That error is caught in `_FakePalettizeImplBase.forward` → warning + module permanently disabled + parametrization removed.

Vector palettization math (docs `palettization/basics.md:16`): `n_bits=4, cluster_dim=2` ⇒ K-means on 2-D data with 16 centroids, LUT `16x2`, effective **bpw = 4/2 = 2**.

LUT tensor shape contract (`spec/fake_palettize.py:139-151`):
```
[NUM_LUT_AXIS_0, NUM_LUT_AXIS_1, NUM_PALETTES, VECTOR_SIZE]
NUM_PALETTES == 2**n_bits ; VECTOR_SIZE == cluster_dim (1 ⇒ scalar palettization)
```

Buffers on `_FakePalettizeImplBase`: `lut, indices, per_channel_scale, quantized_lut, lut_quantization_scale, lut_quantization_zero_point`, plus `fake_palett_enabled`, `observer_enabled` (both `uint8` tensors). Custom `_load_from_state_dict` re-registers these dynamically-created buffers on load.

### 7.3 Config

```python
class OpKMeansPalettizerConfig(WeightOnlyOpValidationMixin, OpCompressionConfig[PalettizationSpec]):
    @classmethod
    def get_default_state_spec(cls):
        spec = default_weight_palettization_spec()
        return {"weight": spec, "in_proj_weight": spec}

class ModuleKMeansPalettizerConfig(WeightOnlyModuleValidationMixin,
                                   ModuleCompressionConfig[OpKMeansPalettizerConfig, PalettizationSpec]):  # @final
    enable_fast_kmeans_mode: bool = True
    rounding_precision: PositiveInt = 4
    presets: ClassVar[...]

class KMeansPalettizerConfig(CompressionConfig[ModuleKMeansPalettizerConfig]):   # @final
    _CONFIG_KEY = "kmeans_palettization_config"
    _SPEC_KEY   = "palettization_spec"
```

- Note the default targets **two** parameter names: `"weight"` and `"in_proj_weight"` (`nn.MultiheadAttention`).
- Weight-only mixins raise `ValueError` if you set `op_input_spec` / `op_output_spec` / `module_input_spec` / `module_output_spec`: *"{cls} does not support {key}. This is a weight-only compression type that only supports op_state_spec and module_state_spec."*
- `enable_fast_kmeans_mode` + `cluster_dim > 1` → `ValueError("enable_fast_kmeans_mode is not supported when cluster_dim > 1. …")`.
- `enable_fast_kmeans_mode` docstring: "enables optimizations for faster K-means clustering by rounding the weights before clustering if data is in float16 range. If weight dtype is float32, weights are cast to float16 and then rounded." `rounding_precision` = decimal places (default 4).

Presets (`KMeansPalettizerConfig.presets` and `ModuleKMeansPalettizerConfig.presets`):

| preset | signature | spec |
| --- | --- | --- |
| `w4` | `w4(*, axis: int = 0, group_size: int = 16)` | `n_bits=4`, `PerGroupedChannelGranularity(axis, group_size)` |
| `w6` | `w6(*, axis: int = 0, group_size: int = 16)` | `n_bits=6`, `PerGroupedChannelGranularity(axis, group_size)` |
| `w8` | `w8()` | `n_bits=8`, `PerTensorGranularity()` |

(applied to both `"weight"` and `"in_proj_weight"` keys)

### 7.4 Supported ops (eager registry)

`_KMeansPalettizerSupportedOpsRegistry` keys → torch functions:
`conv1d→F.conv1d`, `conv2d→F.conv2d`, `conv3d→F.conv3d`, `conv_transpose1d/2d/3d→F.conv_transpose*d`, `linear→F.linear`, `multi_head_attention_forward→F.multi_head_attention_forward`.
The registry's `register` decorator **validates at runtime** that the class subclasses `_PalettizationSupportMixin`, else `TypeError`.
ConvTranspose1d/2d/3d palettization was **added in 0.2.1** (CHANGELOG).

### 7.5 K-means execution and parallelism

`prepare(num_workers=N)`:
- `num_workers < 1` → `ValueError(f"num_workers must be >= 1, got {num_workers}")`.
- `num_workers == 1` → `_calculate_centroids_sequential`: single forward pass with tqdm bar `"Palettizing layers (num_workers=1)"`, hooks tick per FQ module.
- `num_workers > 1` → `_calculate_centroids_parallel`: `torch.multiprocessing.get_context("spawn").Pool(...)`, worker count capped at number of layers, tqdm `"Palettizing layers (num_workers=N)"`. Comment: "spawn (not fork) so workers don't inherit the parent's CUDA context or other process-global state." The worker returns the mutated `_KMeansFakePalettize` and the parent swaps it back into `module.parametrizations[attr][idx]`.

**Reproducibility gotcha** (docs `palettization/config.md:43-72`): with `cluster_dim > 1` vector k-means uses `numpy.random` + `torch.randint` for centroid init and is non-deterministic. Seeding works only with `num_workers=1` because "k-means runs in spawned worker processes that do not inherit the parent's RNG state." Scalar palettization (`cluster_dim == 1`) is deterministic.

```python
seed = 42
np.random.seed(seed); torch.manual_seed(seed)
model_1 = KMeansPalettizer(model, config).prepare(example_inputs)
np.random.seed(seed); torch.manual_seed(seed)
model_2 = KMeansPalettizer(model, config).prepare(example_inputs)   # identical
```

### 7.6 Sensitive K-means (SqueezeLLM)

Based on <https://arxiv.org/pdf/2306.07629> ("SqueezeLLM: Dense-and-Sparse Quantization"). Squared gradients are used as per-element importance weights for weighted k-means.

```python
import torch.nn.functional as F
with palettizer.calibration_mode(loss_fn=F.cross_entropy, sensitivity_path="sensitivities.pt") as skm:
    for batch, target in calibration_dataloader:
        output = prepared_model(batch)
        skm.step(output, target)      # computes loss + loss.backward()
```
Reuse later:
```python
prepared_model = palettizer.prepare(example_inputs, sensitivity_path="sensitivities.pt")
```
or `palettizer.save_sensitivities("sensitivities.pt")` post-hoc.

Mechanics (`kmeans/palettizer.py`):
1. Saves a **full `state_dict` checkpoint to a temp file** (`tempfile.NamedTemporaryFile(prefix="palettizer_calibration_", suffix=".pt")`) and `zero_grad()`.
2. Disables observers and fake palettization during sensitivity collection.
3. Registers `param.register_hook(lambda grad: torch.square(grad))` on every `requires_grad` parameter.
4. On exit: `_construct_sensitivities` → `-param.grad.cpu()` per param; `_normalize_sensitivities` does `val = 100 * -val`, normalize by max to [0,1], then `val[val == 0] = min(val[val != 0])` and clip `val < 1e-12` to `_SENSITIVITY_CLIP_THR = 1e-12` ("Clipping very small or zero sensitivity values stabilizes k-means, they can lead to divergence otherwise").
5. Restores the checkpoint, sets sensitivities on each `_KMeansFakePalettize`, re-enables observers, **recomputes centroids** with the same `num_workers` chosen at prepare time, then restores fake-palett on / observer off.
6. If `step()` was never called → `RuntimeError("calibration_mode requires at least one call to step(). No calibration data was processed.")`.

Sensitivity keys are `f"{module_name}.parametrizations.{attr_name}.original"`. Shapes must match the parameter exactly (assert). Loading uses `torch.load(path, weights_only=True)` (hardened in commit `367dfd5`).

### 7.7 Finalize / export chain

`finalize(backend=CoreAI)` → `_prepare_for_mlir_export(model, mmap_dir=...)` which replaces the fake-palettize parametrization with `coreai_torch._compression.custom_layers.PalettizeModule` / `ScaledPalettizeModule` wrapped by `coreai_torch._compression.utils.wrap_for_parametrization`. Op-chaining rules (`kmeans/_prepare_for_export.py:225-233`):

1. Palettization only → `lut_to_dense`
2. Quantized LUT → `lut_to_dense(int LUT)` + `constexpr_blockwise_shift_scale(lut_scale)`
3. Per-channel scale → `lut_to_dense` + `constexpr_blockwise_shift_scale(pcs)`
4. Both → `lut_to_dense(int LUT)` + `constexpr_blockwise_shift_scale(fused_scale)` where `fused_scale = lut_scale * per_channel_scale`

> "The dense pre-palettization weight stored on the parametrization list is always replaced with a zero-size placeholder so its storage can be released." (i.e. **`finalize(CoreAI)` destroys the float weights in place**)

Missing `coreai-torch` → `ImportError` from `lazy_import_coreai_torch`.

---

## 8. Pruning

`coreai_opt.pruning.__all__` = `MagnitudePruner, MagnitudePrunerConfig, ModuleMagnitudePrunerConfig, PruningSpec`.
`coreai_opt.pruning.spec.__all__` = `ChannelStructured, PruneImplBase, PruningScheme, PruningSpec, Unstructured, default_weight_pruning_spec`.
`coreai_opt.pruning.config.__all__` = `ConstantSparsitySchedule, MagnitudePrunerConfig, ModuleMagnitudePrunerConfig, OpMagnitudePrunerConfig, PolynomialDecaySchedule, SparsityScheduleBase`.

```python
class MagnitudePruner(_BasePruner, _EagerCompressionComponentBuilderMixin):
    def __init__(self, model, config: MagnitudePrunerConfig | None = None)
    def prepare(self, example_inputs: tuple[torch.Tensor]) -> nn.Module
    def step(self) -> None
    def finalize(self, model=None, backend: ExportBackend = ExportBackend.CoreAI) -> nn.Module
```
**No `mmap_dir`, no `calibration_mode`, no `training_mode`.** Eager only.

### `PruningSpec`
```python
target_sparsity: float = Field(default=0.5, ge=0.0, le=1.0)
pruning_scheme: PruningScheme = Unstructured()
pruning_algo: type[PruneImplBase] = "default"     # → _MagnitudePruneImpl
```
Schemes (registry keys `"unstructured"`, `"channel_structured"`):
```python
class Unstructured(PruningScheme):        axis: Literal[None] = None
class ChannelStructured(PruningScheme):   axis: int = 0
```

Mask math (`pruning/spec/prune.py`):
- unstructured: `num_keep = numel - floor(numel * sparsity)`, `topk(|w|.flatten(), num_keep)` → 1.0 at kept indices.
- channel-structured: `num_prune = floor(num_channels * sparsity)`; channel importance = **L1 norm** (`weight.abs().sum(dim=all_dims_except_axis)`); keeps top `num_channels - num_prune`; mask broadcast/expanded to the full shape.
- `sparsity == 0.0` → `ones_like`; `sparsity >= 1.0` → `zeros_like`.
- Mask is a buffer named `mask`; `forward` recomputes only when `_dirty`, casts/resizes as needed, then `return weight * self.mask`. Mask dtype matches the weight (commit `3b8d61a`).

**Realized-sparsity gotcha** (docs `pruning/config.md:34-38`): for `ChannelStructured`, realized sparsity rounds *down* to a multiple of `1/num_channels`. `num_channels=7, target=0.5` ⇒ only 3 channels pruned ⇒ 3/7 ≈ 43 %.

### Sparsity schedules (`pruning/config/sparsity_schedule.py`)

```python
@SparsityScheduleBase.register("constant")
class ConstantSparsitySchedule(SparsityScheduleBase):
    begin_step: NonNegativeInt = 0
    # sparsity(s) = target if s >= begin_step else 0.0

@SparsityScheduleBase.register("polynomial_decay")
class PolynomialDecaySchedule(SparsityScheduleBase):
    begin_step: int = Field(default=0, ge=0)
    total_iters: PositiveInt                 # required
    power: PositiveFloat = 3.0
    initial_sparsity: float = Field(default=0.0, ge=0.0, le=1.0)
    update_frequency: PositiveInt = 1
```
Formula: `n_updates = max((total_iters - 1)//update_frequency + 1, 1)`, `i = offset//update_frequency`, `t = i / max(n_updates - 1, 1)`, `sparsity = target + (initial - target)*(1-t)**power`.
Behavior: `< begin_step` → `initial_sparsity`; `>= begin_step + total_iters` → `target_sparsity`; off-boundary steps return `prev_sparsity` (and raise `ValueError` if `prev_sparsity is None` when `update_frequency > 1`).

### Config
```python
class ModuleMagnitudePrunerConfig(WeightOnlyModuleValidationMixin, ModuleCompressionConfig[...]):
    sparsity_schedule: SparsityScheduleBase | None = None
class MagnitudePrunerConfig(CompressionConfig[ModuleMagnitudePrunerConfig]):
    _CONFIG_KEY = "magnitude_pruning_config"   # YAML top-level key
    _SPEC_KEY   = "pruning_spec"
```
Defaults target `{"weight", "in_proj_weight"}` at 50 % unstructured.
There are **no pruning presets** (no `MagnitudePrunerConfig.presets`).

Supported ops (`pruning/supported_ops_registry.py`): `linear, conv1d, conv2d, conv3d, conv_transpose1d, conv_transpose2d, conv_transpose3d, multi_head_attention` (all `F.*` functions).

Fine-tuning loop (docs `pruning/overview.md:56-89`):
```python
config = MagnitudePrunerConfig(
    global_config=ModuleMagnitudePrunerConfig(
        op_state_spec={"weight": PruningSpec(target_sparsity=0.7)},
        sparsity_schedule=PolynomialDecaySchedule(begin_step=0, total_iters=num_epochs, power=3.0),
    ),
)
pruner = MagnitudePruner(model, config); prepared_model = pruner.prepare(example_inputs)
for epoch in range(num_epochs):
    prepared_model.train()
    for batch, target in train_dataloader:
        optimizer.zero_grad(); criterion(prepared_model(batch), target).backward(); optimizer.step()
    pruner.step()          # advance schedule + recompute masks
```
`step()` is a no-op when nothing has a schedule. `_build_scheduled_modules()` runs at prepare time and applies the step-0 state before the init forward.

Accuracy expectation stated bluntly (docs `pruning/overview.md:7`):
> "Unless the original PyTorch model already has a large fraction of weights close to zero across all of its weight parameters, post-training pruning will almost always degrade accuracy. It is most useful as a quick way to evaluate the impact of sparsity on model size and inference latency before committing to a fine-tuning workflow."

---

## 9. Composition with `coreai-torch` (export path)

`docs/src/introduction/integration_coreai.md` — the canonical end-to-end:

```python
from pathlib import Path
from coreai_opt.casting import cast_to_16_bit_precision
import coreai_torch, torch

finalized_model = quantizer.finalize(backend=opt.ExportBackend.CoreAI)  # CoreAI is the default

exported_program = torch.export.export(finalized_model, example_inputs).run_decompositions(
    coreai_torch.get_decomp_table()
)
cast_to_16_bit_precision(exported_program)     # in-place graph rewrite

converter = coreai_torch.TorchConverter()
converter.add_exported_program(exported_program)
ai_program = converter.to_coreai()
ai_program.optimize()
ai_program.save_asset(Path("model.aimodel"))
```

> "Under the hood, `finalize()` replaces coreai-opt's internal fake-quantize/fake-palettize ops with PyTorch custom ops whose definitions match the corresponding compression ops in the Core AI dialect. This allows `coreai-torch` to recognize the ops and map them correctly in the Core AI representation."

CoreML path (`docs/src/quantization/overview.md:54-69`):
```python
finalized_model = quantizer.finalize(backend=opt.ExportBackend.CoreML)
traced_model = torch.jit.trace(finalized_model, example_inputs)
mlmodel = ct.convert(traced_model, convert_to="mlprogram", minimum_deployment_target=ct.target.iOS26)
mlmodel.save("model.mlpackage")
```
Note the deployment target used in docs: **`ct.target.iOS26`**.

Reason to use **eager** mode: "When `torch.nn.Module` needs to be provided as an input, instead of `ExportedProgram` to the conversion API of coreai-torch. This happens when the `coreai-torch` conversion needs to 'externalize' certain sub-modules to map them to _composite ops_ for better runtime performance."

### CoreML export restriction matrix (`src/coreai_opt/_utils/export_utils.py:17-47`)

```python
COREML_SUPPORTED_WEIGHT_DTYPES     = {torch.int8, torch.uint8, torch.int4, torch.uint4}
COREML_SUPPORTED_ACTIVATION_DTYPES = {torch.int8, torch.uint8}
COREML_SUPPORTED_LUT_DTYPES        = {torch.int8, torch.uint8}
COREML_SUPPORTED_ACTIVATION_GRANULARITIES = {PerTensorGranularity}
```
So on CoreML: **no FP4/FP8 anywhere, no int2/uint2 weights, no per-channel/per-block activation quantization, no MINVAL formulation.** Palettization has an extra rule (`validate_coreml_palettization_compatibility`): *at most one of* `{cluster_dim > 1, lut_qspec, enable_per_channel_scale}` — combining two raises `CoreMLExportError("CoreML export does not support cluster_dim + lut_qspec on <ctx>. Use backend=ExportBackend.CoreAI instead.")` because it "hits an unsupported CoreML/MIL op configuration (mismatched tensor ranks, or `lut_to_dense` divisibility errors)".
These checks were expanded in commits `56c4a36` and `012f399`; changelog fragment `changelog.d/42.fixed` = "Reject per-channel activation quantization on CoreML export".

---

## 10. Joint compression (palettization + activation quantization)

`docs/src/utils/joint_compression.md`. **Order is mandatory: palettize weights → `palettizer.finalize()` → quantize activations → calibrate → `quantizer.finalize()`.**

Why finalize in between: "`quantizer.prepare` uses `torch.export`, which cannot trace through the parametrizations."
Why quantize the LUT: "A floating-point LUT causes operations to execute in floating-point regardless of the activation quantization, whereas an `INT8` LUT allows the runtime to use the faster W_INT8-A_INT8 execution path where available."
**Restriction: "Models compressed via the joint compression flow can currently only be finalized to the `Core AI` backend."**

```python
lut_qspec = QuantizationSpec(dtype=torch.int8, qscheme=QuantizationScheme.SYMMETRIC)
palett_config = KMeansPalettizerConfig(
    global_config=ModuleKMeansPalettizerConfig(
        op_state_spec={"weight": PalettizationSpec(n_bits=4, lut_qspec=lut_qspec)},
    ),
)
palettizer = KMeansPalettizer(model, palett_config)
palettizer.prepare(example_inputs)
palettized_model = palettizer.finalize(backend=opt.ExportBackend.CoreAI)

act_spec = QuantizationSpec(dtype=torch.int8, qscheme=QuantizationScheme.SYMMETRIC)
quant_config = QuantizerConfig(
    global_config=ModuleQuantizerConfig(
        op_state_spec=None,                    # weights already compressed
        op_input_spec={"*": act_spec},
        op_output_spec={"*": act_spec},
    ),
)
quantizer = Quantizer(palettized_model, quant_config)
prepared_model = quantizer.prepare(example_inputs)
with quantizer.calibration_mode():
    for batch in calibration_dataloader:
        prepared_model(batch)
final_model = quantizer.finalize(backend=opt.ExportBackend.CoreAI)
```

Reference tests: `tests/test_joint_compression.py::test_p4a8_compression_mnist_accuracy` (marked `@pytest.mark.slow`, skipped without coreai), `tests/export/test_pt2e_mlir_export.py::test_mnist_p4a8_compression_export`.

---

## 11. `coreai_opt.casting`

```python
from coreai_opt.casting import cast_to_16_bit_precision, cast_fp32_to_fp16, cast_int32_to_int16
```
All three mutate a `torch.export.ExportedProgram` **in place** and return nothing meaningful.

| API | Scope |
| --- | --- |
| `cast_to_16_bit_precision` | FP32→FP16 **and** INT32/INT64→INT16 (recommended top-level) |
| `cast_fp32_to_fp16` | FP32→FP16 only |
| `cast_int32_to_int16` | INT32/INT64→INT16 only |

Selection criteria (docs `utils/casting.md:28-38`):
- **FP pass is aggressive**: casts all float state/ops except tensors whose values exceed the FP16 range (≈ ±65504).
- **INT pass is conservative**: skips tensors that are constant-foldable, feed an indexing op (overflow risk), or are not consumed by a computationally intensive op.

> ":::{note} These passes mutate the `ExportedProgram` in place and may change the dtypes of user inputs and outputs. Calling code may need to be updated so that input tensors are passed as `fp16`/`int16` …:::"

Comparison table it draws vs. PyTorch (`utils/casting.md:128-143`): `model.half()` only touches params/buffers (creation ops like `torch.zeros`/`torch.arange` stay FP32); `torch.autocast` wraps each op at runtime and produces no 16-bit artifact; `cast_to_16_bit_precision` rewrites the exported graph so "downstream converters see a 16-bit graph and do not need to insert per-op cast wrappers."

**Ordering rule: compress first, cast second.** "Any quantized int8 buffers are left untouched; any remaining FP32 weights move to FP16."

---

## 12. `coreai_opt.coreai_utils` — MLIR/AIProgram-level compression (no PyTorch)

```python
from coreai_opt.coreai_utils import CompressionGranularity, DType, QScheme
from coreai_opt.coreai_utils import quantize_weights, palettize_weights, sparsify_weights
```
`__all__` = `CompressionGranularity, DType, palettize_weights, quantize_weights, sparsify_weights` (note: `QScheme` is defined in `coreai_utils.common.__all__` but not re-exported at package level — import it from `coreai_opt.coreai_utils.common` **or** it is reachable via the docs' `from coreai_opt.coreai_utils import ... QScheme ...` (docs claim this works; **UNVERIFIED** which one is authoritative — package `__all__` omits it)).

```python
class DType(_StrEnum):
    INT2, UINT2, INT4, UINT4, INT8, UINT8, FP4_E2M1FN, FP8_E4M3FN, FP8_E5M2, FP8_E8M0FNU
    def is_int(self) -> bool
class QScheme(_StrEnum): SYMMETRIC, ASYMMETRIC
class CompressionGranularity(_StrEnum): PER_TENSOR, PER_CHANNEL, PER_BLOCK, PER_GROUPED_CHANNEL
```

Only constants consumed by these ops are candidates (`coreai_utils/passes/__init__.py`):
```python
_OPS_WEIGHT_NEED_COMPRESSION = frozenset({
    "coreai.batch_matmul", "coreai.conv2d",
    "coreai.decomposable.broadcasting_batch_matmul",
    "coreai.gather_nd", "coreai.transpose",
})
```

### `quantize_weights` (exact signature, `passes/weight_quantization.py:151-160`)
```python
def quantize_weights(
    coreai_program: AIProgram,
    dtype: DType,
    qscheme: QScheme = QScheme.SYMMETRIC,
    granularity: CompressionGranularity = CompressionGranularity.PER_CHANNEL,
    block_size: int = 32,
    weight_num_threshold: int = 1024,
    scale_dtype: DType | None = None,
    in_place: bool = False,
) -> AIProgram
```
`_VALID_WEIGHT_DTYPES = {FP4_E2M1FN, FP8_E4M3FN, FP8_E5M2, INT2, INT4, INT8, UINT2, UINT4, UINT8}`.
block_sizes derived per granularity (from the docstring): 2-D linear `[C_out, C_in]` → PER_TENSOR `[0,0]`, PER_CHANNEL `[1,0]`, PER_BLOCK(32) `[1,32]`; 4-D conv → `[0,0,0,0]` / `[1,0,0,0]` / `[1,32,0,0]`.
Raises `ValueError` when: dtype unsupported; FP dtype + ASYMMETRIC; `scale_dtype != None` with an integer dtype; `scale_dtype != None` with FP4; **FP4 with granularity != PER_BLOCK or block_size != 32** ("FP4 weights must use per-block quantization with a block size of 32 to produce a valid MXFP4 encoding").
Emits `coreai.blockwise_shift_scale(data, scale, offset1=zero_point, offset2=zeros)`.

### `palettize_weights` (`passes/weight_palettization.py:63-76`)
```python
def palettize_weights(
    coreai_program: AIProgram,
    lut_dtype: DType | None,
    n_bits: int = 4,
    granularity: CompressionGranularity = CompressionGranularity.PER_TENSOR,
    group_size: int = 32,
    cluster_dim: int = 1,
    enable_per_channel_scale: bool = False,
    weight_num_threshold: int = 1024,
    num_kmeans_workers: int = 4,
    enable_fast_kmeans_mode: bool = True,
    rounding_precision: int = 4,
    in_place: bool = False,
) -> AIProgram
```
`_VALID_LUT_DTYPES = {INT8, UINT8, FP8_E4M3FN, FP8_E5M2}`; `_VALID_N_BITS = {1,2,3,4,6,8}`; granularity ∈ `{PER_TENSOR, PER_CHANNEL, PER_GROUPED_CHANNEL}`.
`enable_per_channel_scale=True` + `cluster_dim > 1` → `ValueError`.
**Note `lut_dtype` is positional #2 and has no default** — the docs example passes it as a kwarg.

### `sparsify_weights` (`passes/weight_sparsification.py:55-64`)
```python
def sparsify_weights(
    coreai_program: AIProgram,
    target_sparsity: float | None = 0.5,
    block_size: int | None = None,
    n_m_ratio: tuple[int, int] | None = None,
    quantize_dtype: DType | None = None,
    palettize_nbits: int | None = None,
    weight_num_threshold: int = 1024,
    in_place: bool = False,
) -> AIProgram
```
- `target_sparsity` XOR `n_m_ratio` (both set or both None → `ValueError`).
- `quantize_dtype` XOR `palettize_nbits` (joint sparse+quant or sparse+palett, not both).
- `quantize_dtype ∈ {INT8, UINT8, FP8_E4M3FN, FP8_E5M2}`; `palettize_nbits ∈ {1,2,3,4,6,8}`.
- `block_size` must be `> 1`; block sparsity is along the **output channel** dim, only for linear/conv.
- `n_m_ratio=(n, m)`: "Out of every `m` elements, the `n` with lowest magnitude are set to zero", along the **input channel** axis, linear/conv only.

Docs entry point (`utils/coreai_compression.md:11-31`):
```python
from coreai.authoring import AIModelAsset
from coreai_opt.coreai_utils import DType, quantize_weights

ai_asset = AIModelAsset.load(Path("model.aimodel"))
compressed_program = quantize_weights(coreai_program=ai_asset.program, dtype=DType.INT8, in_place=False)
compressed_program.optimize()
compressed_program.save_asset(Path("model_compressed.aimodel"))
```
Note the docs use `weight_num_threshold=2048` in "advanced" examples although the code default is `1024`.

---

## 13. `coreai_opt.inspection.ModelInspector`

```python
from coreai_opt.inspection import ModelInspector
ModelInspector(
    model: torch.fx.GraphModule | torch.nn.Module,
    example_inputs: tuple[Any, ...] | None,
    execution_mode: ExecutionMode,                     # "graph" | "eager"
    compressor: type[_BaseModelCompressor] | None = None,
    dynamic_shapes=None,
    export_with_no_grad: bool = True,
)
```
Methods: `.summary`, `.format_summary(colorize=True)` (UNVERIFIED kwarg name — docs say "Pass `colorize=False`"), `.get_matched_ops_for_op_type(op_type)` (exact string), `.get_matched_ops_for_op_name(pattern)` (`re.fullmatch`), `.get_matched_ops_for_module_name(pattern)` (`re.fullmatch` against each FQN in the op's module stack).
Exported types: `BoundaryEdge, InputEdge, ModelInspector, ModelSummary, ModuleContext, ModuleInfo, OpInfo, SourceFrame`.
`ModuleInfo` mirrors `nn.Module`: `children()`, `named_children()`, `modules()`, `named_modules()`, `get_submodule()`, `all_ops()`, plus `input_ops` / `output_ops` boundary dicts.
`OpInfo` fields: `op_name, op_type, module_stack, inputs, outputs, is_state`. `InputEdge` has the producing `OpInfo`, `output_idx`, and `is_state`.

Raises `TypeError` if model isn't an `nn.Module`, or if it's a `GraphModule` and `execution_mode="eager"`.
Graph mode requires `compressor` ∈ `{Quantizer, None}`; eager supports `Quantizer` and `KMeansPalettizer`.

Example tree output legend (docs `debugging/model_inspection.md:61-91`):
```
Legend:
  ■ module_name (module_type)  ◆ op_name [op_type]
  op inputs:  {I: producer[N]}   op states: param_name   op outputs: {N: [consumers]}
  untracked_N  — input tensor whose producer was not intercepted; still quantizable via op_input_spec
  module inputs:  {I: [op[N], ...]}   module outputs: {I: op[N]}
```
Graph-mode op names are global (`linear`, `linear_1`); eager op names are module-qualified (`linear1.linear`, `linear2.linear`). **Use the mode you plan to compress with.**

---

## 14. Reported accuracy / size / cost numbers (from docs)

### ResNet50 W/A quantization PTQ (128 eval samples from imagenette, `docs/src/examples/resnet50.md`)
| Config | Accuracy |
| --- | --- |
| FP32 baseline | 78.12 % |
| W_INT8(per-channel)_A_INT8(per-tensor), `moving_average`, 896 calib samples | 74.22 % |
| same but `global_minmax` activations | 75.78 % |
| W_FP8_E4M3_A_FP8_E4M3, `global_minmax` | **76.56 %** |

### EDSR super-resolution (`edsr_r16f64`, 1.5 M params, B100, 20 calib / 80 eval)
| Configuration | PSNR | Weight storage |
| --- | --- | --- |
| FP32 baseline | 30.68 dB | ~5.5 MB |
| W_INT8_A_INT8 | 30.33 dB (−0.35) | ~1.4 MB (4×) |
| W_P4(INT8)_A_INT8 joint | 29.86 dB (−0.47 more) | ~0.7 MB (8×) |

### ResNet50 mixed-precision palettization (ImageNet val 50 k, mps backend)
| Configuration | BPW | Size | Top-1 |
| --- | --- | --- | --- |
| FP16 baseline | 16 | 48.64 MB | 75.02 % |
| uniform 4-bit per-tensor | 4 | 12.16 MB | 65.87 % |
| greedy mixed precision (target 4) | 3.95 | 12.03 MB | **70.27 %** |

Recipe distribution: 2 layers at 6-bit (`conv1`, `layer1.0.downsample.0`), 50 at 4-bit, 2 at 2-bit (`layer1.1.conv1`, `layer3.4.conv2`). Curve inflection at ≈ 4.0 realized BPW: "below it, every additional 0.5 BPW buys us 15-35 percentage points of accuracy; above it, gains drop to 1-2 points per 0.5 BPW."

### Toy `Conv2d→ReLU→Linear` SNR table, default INT8 (`utils/activation_comparison.md:286-295`, graph mode)
```
conv_weight   -> activation_post_process_1  SNR = 47.17 dB
conv_bias     -> conv_bias                  SNR = inf dB
linear_weight -> activation_post_process_4  SNR = 48.13 dB
x             -> activation_post_process_0  SNR = 43.20 dB
conv2d        -> conv2d                     SNR = 42.40 dB
relu          -> activation_post_process_2  SNR = 38.94 dB
flatten       -> activation_post_process_3  SNR = 38.94 dB
linear        -> activation_post_process_5  SNR = 35.74 dB
```

### Workflow cost guidance (`docs/src/landing_page.md:43-47`)
- **Data-free**: "typically seconds to minutes even for large models. Often works well for reducing the model down to 8 bits, or even 6 or 4 bits, with only a slight decrease in accuracy."
- **Calibration-based**: "A small amount of representative data (e.g. ~128 samples)."
- **Fine-tuning-based**: "the most time-intensive workflow, but typically the only way to recover accuracy at the most aggressive compression ratios for weights (4 bits and below)."
- Supported precisions summary: weights INT2/INT4/INT8 + FP4/FP8; activations INT8 and FP8; palettization N ∈ {1,2,3,4,6,8} bits.

---

## 15. Make targets / dev CLI

All targets (`.PHONY` line, `Makefile:6`):
```
_maybe_patch_pyproject all api-list build build-dev check clean distclean distclean-all
docs docs-clean docs-open env env-all env-docs env-highest-torch env-lowest-torch env-tutorial
render-api-index set-auto-venv test test-cov test-fast test-highest-pytorch test-lowest-pytorch
test-slow test-smoke test-tutorials version
```

| Target | What it does |
| --- | --- |
| `make env` | `.venv` with dev+coreai+coreml default groups |
| `make env-highest-torch` / `env-lowest-torch` | `.venv-highest-torch` (torch 2.11) / `.venv-lowest-torch` (torch 2.8) |
| `make env-tutorial` | `.venv-tutorial` with `--with-tutorial` |
| `make env-all` | `--all-groups` |
| `make env-docs` | `.venv-docs` |
| `make build` | `uv build --no-sources` (publishable wheel+sdist) |
| `make build-dev` | `scripts/make/build.py` (supports PEP 440 `.dev` via `--dev`) |
| `make api-list [MODULE=coreai_opt.quantization.spec.spec]` | print `__all__` public surface |
| `make check` | `pre-commit run --all-files` (ruff, mypy, license headers, mdformat, taplo, mbake, pymarkdownlnt, …) |
| `make test [PYTEST_ARGS=…]` | full suite via `scripts/make/run_tests.sh` (pytest-xdist) |
| `make test-cov` | `PYTEST_ARGS="--cov"` |
| `make test-fast` | `--marker 'not slow'` |
| `make test-slow` | `--marker slow` |
| `make test-smoke [TORCH_GROUP=torch_2_9] [SMOKE_TEST_DIST=path.whl]` | nox session `smoke_tests` in `ci/nox/noxfile.py`: builds/installs the dist in a clean env and checks imports + basic quant/palett |
| `make test-lowest-pytorch` / `test-highest-pytorch` | run the suite pinned to torch 2.8 / 2.11 |
| `make test-tutorials` | runs `docs/tests/test_tutorials.py` (papermill over the notebooks) |
| `make docs` / `docs-open` / `docs-clean` | Sphinx build (shibuya theme, myst-parser, nbsphinx, autodoc-pydantic, sphinxcontrib-mermaid, sphinx-llm) |
| `make render-api-index` | `docs/scripts/generate_api_index.py` |
| `make version`, `make clean`, `make distclean`, `make distclean-all` | housekeeping |
| `make all` | `clean distclean-all env-all check test-lowest-pytorch test-highest-pytorch build-dev` |

Two environment variables the Makefile exports:
- `USE_LOCAL_COREAI ?= 1` — "Tell coreai's runtime to skip the symbol-version check against the host's installed `/System/Library/Frameworks/CoreAI.framework`. Required when the precompiled coreai wheel was built against a newer SDK than what's on the host — without this, importing `coreai_torch` aborts at dlopen time with a Swift `Symbol not found` error." Override with `make USE_LOCAL_COREAI=0 …`.
- `TORCH_GROUP ?= $(HIGHEST_TORCH_GROUP)`.

`AGENTS.md` (which is literally titled `# CLAUDE.md`) adds a critical uv rule:
> "Always pass `--no-sync` to `uv run`: `uv run --no-sync --active …`. `uv run` implicitly syncs the active project to its default-groups before running, which re-resolves dependencies and can clobber a venv's group-pinned packages — e.g. the torch pin in `.venv-lowest-torch`/`.venv-highest-torch` gets re-anchored back to the default torch."

Direct pytest:
```bash
pytest -n auto path/to/test.py
pytest path/to/test.py::test_name
```

### CI (`.github/workflows/ci.yaml`)
- Stage 1 (ubuntu-latest): `make check`; `make test-smoke` × {torch 2.8, 2.9, 2.10, 2.11}; `make test-tutorials`.
- Stage 2 (gated): **macOS self-hosted `[self-hosted, macos, tahoe, ARM64]`** running `make test-highest-pytorch PYTEST_ARGS="--marker 'not slow' --junit"` (only when `github.repository == 'apple/coreai-optimization'`); plus a Linux matrix over `torch: [highest, lowest] × speed: [slow, fast]`.
- Note the runner label **`tahoe`** = macOS 26 "Tahoe" class machine.
- `.github/workflows/release.yml` = PyPI trusted publishing (added in `04acaee`).

---

## 16. Test suite map (best executable documentation)

```
tests/
  test_smoke.py                     # minimal quant (eager+graph) + palett smoke
  test_joint_compression.py         # P4-A8 MNIST accuracy (slow, needs coreai)
  test_compression_config.py, test_base_model_compressor.py, test_inspection.py
  test_quantization_preset.py, test_palettization_preset.py
  test_api_visibility.py / test_api_visibility_utils.py    # enforces __all__ discipline
  quantization/  (21 files)  eager & graph e2e, qparams calc, range calc, fake quant, QAT schedule,
                             axis defaults, annotation pattern/utils/config, conv-bn folding,
                             state spec resolver, kv cache quantization, graph-mode prepare-for-export
  palettization/ kmeans palettizer (+mnist), kmeans_fake_palettize, kmeans1d, kmeans_parallel,
                 support mixins, config, spec
  pruning/       magnitude pruner (+mnist), config/spec, sparsity schedule
  export/        eager & graph MIL/MLIR export, pt2e weight-only MIL, kmeans export, pruning export,
                 eager MLIR embedding export
  casting/, coreai_utils/ (quantize/palettize/sparsify weights, sparse utils), deprecation/, devtools/
  models/        resnet.py, simple.py, mnist.py
  fixtures/      quantization.py, palettization.py, pruning.py, compression.py, fp4.py, fp8.py
  _test_artifacts/mnist/mnist_pretrained_1epoch_09032025.pt, mnist_example_input_11122025.pt
docs/src/tutorials/  mnist_quantization.ipynb, mnist_palettization.ipynb,
                     mnist_palettization_and_activation_quantization.ipynb, mnist_pruning.ipynb
```

Useful assertions seen in `tests/test_joint_compression.py`: MNIST baseline `> 97.0 %`, joint P4-A8 after calibration `> 90.0 %`, and `post_calib_acc == finalized_acc` for `ExportBackend._TORCH` (finalize must be numerically exact for the torch backend). MNIST model has 6 weight-bearing layers (conv1, conv2, conv_transpose1, conv_transpose2, dense1, dense2); `batch_size = 128`, `num_calibration_batches = 17`.

---

## 17. Recent commit history (what is actively changing)

`git log --oneline -50` (full list; the repo has only ~35 commits since `e27b3d0 chore: initial commit`):

```
cd95cb2 fix: try per-channel act quant for shared observers but fall back to per-tensor if unsafe (#52)
04acaee ci: add PyPI trusted-publishing release workflow (#51)
2d92c5c feat(pre-commit): add internal-import alias check with auto-fix (#49)
012f399 fix: raise CoreMLExportError on incompatible palettization configs (#44)
3f5b05d build: add env-lowest-torch make target (#50)
6513455 ci: run smoke tests across a python x torch version matrix (#32)
56c4a36 refactor: expand `CoreMLExportError` to error on non-compatible configs for CoreML and remove more CoreML export tests (#42)
7d1805b build: add render-api-index make target (#43)
2965864 refactor: add InvalidExecutionModeError for unknown execution modes (#38)
3e01e4a fix(test): change AIModel asset saving to give temp path to AIModel instead of directory (#37)
b1535b4 docs: add MNIST magnitude pruning tutorial  (#33)
d1e5d37 Add graph mode debugging hints and troubleshooting doc (#39)
edd4720 refactor: remove `coremltools` dependency and use `torch.utils.cpp_extension` to load kmeans1d (#31)
1001e57 test: unskip eager CoreML int8-activation export tests as they now pass (#36)
61d7084 test: unskip Graph CoreML export tests as segfault no longer occurs (#35)
0eabc57 Fix output spec adjustment for fixed qparams ops (#22)
256d4c4 Enable support for FP4 weight quantization for non-conv layers (#34)
5cdb1f1 refactor: use dataclass for weight axis defaults table (#30)
519f21c Enable weight fake quantization in calibration mode (#25)
4968b10 Update model inspector documentation (#24)
58d3b60 chore: delete dead code from efficient kmeans (#23)
de5803b Update `CHANGELOG.md` with release notes from `v0.2.1` (#28)
e0203ef 0.2.1 release (#26)
eee31ed test: allow selection of CoreAI compute unit during inference (#21)
367dfd5 Use weights_only=True when loading sensitivities (#16) (#18)
a87b440 ci: add `ubuntu-latest` test pipelines (#19)
aeee805 style: scrubbing (#20)
3698934 chore(release): sync updates (#17)
6162da5 ci: add dependabot yaml (#13)
b87471b ci: Add initial CI (#9)
4df45c0 fix(palettization): cast bfloat16 sensitivities to float32 (#6)
f6baedf fix(quantization): match the float_range bound dtype to the input (#5)
859d7c9 fix(palettization): cluster bfloat16 weights as float32 (#2)
3b8d61a fix(pruning): match the pruning mask dtype to the weight (#1)
e27b3d0 chore: initial commit
```

Pending (unreleased) changelog fragments in `changelog.d/`:
- `52.fixed` — shared-observer pooling per-channel act-quant fix (see §6.14)
- `42.fixed` — "Reject per-channel activation quantization on CoreML export"
- `31.changed` — coremltools removed as runtime dep; vendored kmeans1d JIT-compiled
- `180525445.fixed` — "Fix setting of qscheme and float_range for fixed output range ops"

Signals: bfloat16 support was patched three separate times (`4df45c0`, `859d7c9`, `f6baedf`) — bf16 paths are newer/less battle-tested. CoreML export tests were previously skipped due to a **segfault** (`61d7084`) and an eager int8-activation failure (`1001e57`); both now pass.

---

## 18. Gotchas / footguns (consolidated)

1. **`example_inputs` must be a `tuple`.** `TypeError("example_inputs must be a tuple")`, and empty → `ValueError`.
2. **For activation quantization, `example_inputs` must be *representative* data**, not `torch.randn` — it seeds the initial activation qparams. Docs repeat this three times.
3. **`prepare()` mutates in place.** `copy.deepcopy` first if you need the float model. In eager mode, `.weight` on *both* models returns the fake-quantized value after `prepare()` because parametrizations are registered in place — save weight copies before.
4. **Re-preparing raises**: `RuntimeError("Model has already been prepared. Cannot re-prepare a prepared model.")`.
5. **Block-size mismatch silently disables** the FQ/FP module (warning only) and the node is removed from the prepared model. Same for palettization granularity/cluster_dim mismatches.
6. **`None` vs omitted in configs**: omitting a spec field applies the class defaults; explicitly passing `None` disables. `op_state_spec=None` in a joint-compression quant config is what turns off weight quantization.
7. **`module_type_configs` keys must be fully qualified** (`"torch.nn.modules.linear.Linear"`); `"torch.nn.Linear"` fails.
8. **`only_for` cannot be chained** — pass all targets in one call.
9. **Configs are `@final`** — subclassing `QuantizerConfig` / `ModuleQuantizerConfig` / `KMeansPalettizerConfig` / `ModuleKMeansPalettizerConfig` raises `TypeError`.
10. **Specs are frozen** (`ConfigDict(frozen=True, extra="forbid")`); mutate via `model_copy(update={...})`.
11. **Activation per-channel/per-block requires an explicit `axis`** — no defaults, and it may still be silently downgraded to per-tensor around shared observers (now with a warning).
12. **Per-block granularity around shared observers is *always* downgraded** to per-tensor (only `PerChannelGranularity` gets the shape-aware check).
13. **CoreML backend**: no FP4/FP8, no int2/uint2 weights, no per-channel activation quant, no MINVAL, and palettization allows at most one of {`cluster_dim>1`, `lut_qspec`, `enable_per_channel_scale`}.
14. **Joint compression finalizes only to CoreAI.**
15. **`finalize(CoreAI)` frees dense weights** in eager quantization and in palettization (`parametrizations[...].original` → zero-size placeholder). Not reversible.
16. **`mmap_dir` files must stay on disk** for the lifetime of the returned model; the dir must be empty (`FileExistsError` otherwise) and the model must be on CPU. Eager + CoreAI only.
17. **Dynamic quantization (`qparam_calculator_cls="dynamic"`) cannot be exported** to CoreAI/CoreML — `NotImplementedError`; use `ExportBackend._TORCH`.
18. **`quantizer.step()` outside `training_mode()` raises**; `_step_count` is never reset.
19. **QAT schedules and the manual enable/disable APIs are mutually exclusive** (`RuntimeError`).
20. **`training_mode()` is not re-entrant.**
21. **Palettization with `cluster_dim > 1` is non-deterministic**, and seeding only works with `num_workers=1`.
22. **`enable_fast_kmeans_mode=True` (the default) rounds weights** (casting fp32→fp16 first) — set `False` for maximum precision; required `False` for `cluster_dim > 1`.
23. **A C++ toolchain is a runtime requirement** for palettization (vendored kmeans1d JIT).
24. **`ChannelStructured` realized sparsity rounds down** to `1/num_channels` multiples.
25. **`fx.GraphModule.train()/.eval()` after prepare only affects dropout/batchnorm**, nothing else.
26. **Prepared vs finalized are not bit-identical** for Conv+BN in graph mode.
27. **torchao < 0.16.0** requires stripping non-aten kwargs around `prepare_qat_pt2e` (handled internally, but explains odd behavior with custom ops carrying metadata kwargs).
28. **Deprecated names still work with warnings**: `ExportBackend.MIL/MLIR`, `ExecutionMode.PT2E`.
29. **`NAryActPattern` chains longer than 2 ops are unsupported**, and sequential-partition matching requires each op type in the chain to be unique.
30. **Graph-mode configs reject non-`"*"` string keys** and non-`{"*", 0}` output keys.
31. **Palettization and pruning have no graph mode** and no `training_mode()`.

---

## 19. Source inventory (files actually read this session)

Repo root:
`README.md`, `README.pypi.md` (skimmed), `AGENTS.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `RELEASE.md`, `pyproject.toml`, `Makefile` (lines 1-80, 171-330), `.github/workflows/ci.yaml`, `changelog.d/{42.fixed,52.fixed,31.changed,180525445.fixed}`, `agents/llm-first-principles.md` (head).

`src/coreai_opt/`:
`__init__.py`, `_about.py`, `common.py`, `base_model_compressor.py`,
`config/compression_config.py`, `config/spec/__init__.py`, `config/spec/base.py`, `config/spec/compression_simulator.py`, `config/spec/factory.py` (CompressionTargetTensor),
`quantization/__init__.py`, `quantization/quantizer.py`, `quantization/base_quantizer.py`, `quantization/_axis_defaults.py`,
`quantization/config/__init__.py`, `quantization/config/quantization_config.py`, `quantization/config/_presets/{__init__,quantizer_config,module_quantizer_config}.py`,
`quantization/spec/{__init__,spec,granularity,qscheme,qformulation,qparams_calculator,range_calculator,fake_quantize,errors}.py`, `quantization/spec/factory.py` (partial),
`quantization/_graph/quantizer.py`, `quantization/_graph/_utils.py`, `quantization/_graph/_annotation_pattern_registry.py` (structure + shared-observer section), `quantization/_graph/_prepare_for_export.py` (custom-op insertion + KV-cache relocation sections),
`quantization/_eager/quantizer.py` (signatures), `quantization/_eager/supported_ops_registry.py`,
`palettization/__init__.py`, `palettization/spec/{__init__,spec,granularity,fake_palettize}.py`, `palettization/config/{__init__,palettization_config}.py`, `palettization/config/_presets/{kmeans_palettizer_config,module_kmeans_palettizer_config}.py`, `palettization/kmeans/palettizer.py`, `palettization/kmeans/kmeans_fake_palettize.py` (structure), `palettization/kmeans/supported_ops_registry.py`, `palettization/kmeans/_prepare_for_export.py` (op-chaining section),
`pruning/{__init__,magnitude_pruner,supported_ops_registry}.py`, `pruning/spec/{__init__,spec,scheme,prune}.py`, `pruning/config/{__init__,sparsity_schedule}.py`, `pruning/config/magnitude_pruner_config.py` (grep),
`casting/__init__.py`, `inspection/__init__.py`, `inspection/model_inspector.py` (signatures),
`coreai_utils/{__init__,common}.py`, `coreai_utils/passes/{__init__,weight_quantization,weight_palettization,weight_sparsification}.py`,
`_utils/export_utils.py`, `_utils/torch_utils.py` (ATEN_OP_TO_MODULE_TYPE), `deps/_kmeans1d/core.py` (head).

`docs/src/`:
`index.md`, `landing_page.md`, `introduction/{installation,how_to_use_coreaiopt,integration_coreai}.md`,
`quantization/{index,basics,overview,config,advanced}.md`,
`palettization/{basics,overview,config}.md`, `pruning/{basics,overview,config}.md`,
`utils/{joint_compression,mixed_precision,casting,coreai_compression,activation_comparison}.md`,
`debugging/{model_inspection,graph_mode_troubleshooting}.md`,
`examples/{toy_models,resnet50,edsr,mixed_precision_palettization}.md`.

`tests/`: `test_smoke.py`, `test_joint_compression.py`, `test_api_visibility.py` (head), `quantization/test_kv_cache_quantization.py` (head + fixture).

Git: `git log --oneline -50`, `git show cd95cb2` (full message + `src/` diff).

---

## 20. Open questions / unverified

1. **`ModelInspector.format_summary(colorize=...)`** — the docs mention `colorize=False`, but I only read the class `__init__` and query methods, not the `format_summary` signature. **UNVERIFIED**.
2. **`QScheme` export path** — `coreai_opt/coreai_utils/__init__.py:__all__` does *not* list `QScheme`, yet `docs/src/utils/coreai_compression.md:92-97` does `from coreai_opt.coreai_utils import (..., QScheme, ...)`. Either the docs are stale or `__init__` re-exports it implicitly through `common`. **UNVERIFIED** which.
3. I did not read `_efficient_kmeans.py`, `kmeans_support_mixins.py`, or `_core.cpp` end to end — the exact k-means initialization/convergence criteria (max iters, tolerance) for scalar vs vector clustering are **UNVERIFIED**.
4. I did not read `casting/casting.py` — the exact pass names, node-level heuristics, and the FP16 threshold constant (docs say "approximately ±65504") are **UNVERIFIED** at the code level.
5. `_utils/insertion/torch_function/*` (eager `__torch_function__` machinery, module boundary tracking, state spec resolution) was only enumerated, not read. The exact op-naming rule for eager mode (`"linear1.linear"`) is documented but not code-verified.
6. `_graph/_conv_bn_utils.py` (`fold_conv_bn_weights`, `remove_conv_bn_zeros_like_dtype`) not read.
7. No `mmap_dir` end-to-end example exists in docs; safetensors layout/filenames under `mmap_dir` are **UNVERIFIED**.
8. Whether `coreai-torch 0.4.1` / `coreai-core 1.0.0b2` correspond to a specific Xcode/macOS release is not stated anywhere in this repo. The only OS hint is the CI runner label `tahoe`.
9. The tutorial notebooks (`docs/src/tutorials/*.ipynb`) were not opened — they likely contain the most complete runnable MNIST recipes (quantization, palettization, palettization+activation quantization, pruning).
10. `ci/nox/noxfile.py` smoke-session internals not read (exact pytest selection for smoke tests).
11. Sub-byte packing / actual on-disk bit widths (how int4/int2 weights are physically stored in the `.aimodel`) live in `coreai-torch`/Core AI, not here.
