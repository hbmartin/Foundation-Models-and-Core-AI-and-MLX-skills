# Core AI Python ecosystem + Metal tensors / TensorOps — deep transcript notes

**Theme:** `coreai-python-metal`
**Primary sources (read in full this session):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-325.txt` (268 lines) — *"Dive into Core AI model authoring and optimization"* (title confirmed by `repos/apple__coreai-models/models/sam3/README.md`, which links `https://developer.apple.com/videos/play/wwdc2026/325/`). Presenters: **Sachin** (Core AI team) and **Nicole** (Core AI Debugger).
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-330.txt` (138 lines) — *"Optimize custom machine learning operations with Metal tensors"* (title inferred from 325:205 cross-reference). Presenter: **Shiyao**, GPU Software Engineer.

**Cross-check corpus (also read this session):** local `docs/`, the vendored Apple repos `apple__coreai-torch`, `apple__coreai-optimization`, `apple__coreai-models`, MLX's Metal kernels, and the **Xcode 26.6 macOS SDK headers** for `MetalPerformancePrimitives` and `MTLTensor`. Full list in [Source inventory](#source-inventory).

> **Reading convention used throughout.** Anything marked **[TRANSCRIPT]** is what was said aloud. **[RECONSTRUCTED]** is code I reassembled from the spoken description — treat signatures there as best-effort unless a **[VERIFIED]** block from a repo/SDK file confirms it. **[VERIFIED: path:line]** blocks are verbatim from files on disk.

---

## 0. TL;DR of the two sessions

| | Session 325 (Python) | Session 330 (Metal) |
|---|---|---|
| Layer | `coreai-torch` / `coreai-opt` / Core AI Debugger | `MetalPerformancePrimitives` + TensorOps MSL API |
| Entry point | `TorchConverter().add_exported_program(ep).to_coreai()` | `mpp::tensor_ops::matmul2d<desc, Scope>` |
| Artifact | `.aimodel` asset (one or many entrypoint functions) | MSL source string embedded in the `.aimodel` |
| Driving demo | SAM3 (848M params) segmentation, 3-function iOS re-author | FlashAttention kernel plugged into the same SAM3 model |
| Headline numbers | 3 GB → ~430 MB (w4); 76% faster 2nd inference after 3-way split | M5 neural accelerator per shader core; E8M0 block scales in 27 |

The two talks are explicitly wired together in both directions:
- 325:205 — *"For more details on how you can write efficient Metal kernels for Core AI, and to see an optimized kernel live in action with the SAM3 model please see the 'Optimize custom machine learning operations with Metal tensors' talk."*
- 330:121 — *"Check out the 'Deep Dive into Core AI Model authoring and Optimization' session for the details of how to integrate a Metal kernel into a Core AI model."*

---

# PART 1 — Session 325: Core AI's Python ecosystem

## 1.1 Agenda as stated (325:9–15)

1. Core AI **models repository** + **Core AI skills**
2. Basic **conversion and verification**
3. **Model optimization** (`coreai-opt`)
4. **Core AI Debugger** (Nicole)
5. **Deep customization** during model authoring and conversion

Framing quote (325:12): *"Core AI is built around the Python and PyTorch workflows you already know and if you've used Core ML before, a lot of this will feel pretty familiar."*

## 1.2 `coreai-models` repository and Core AI Skills

**[TRANSCRIPT] 325:18–28.** The repo contains:
- A **Swift package** for running LLMs in your app.
- An **open-source repository of ready-to-go models**, including "generative architectures like cutting-edge large language models."
- "Examples engineered for various use-cases and constraints, along with **components that you can use to bring your own models to Core AI**."
- **A set of agent skills.** *"You can install these skills into your favorite coding assistant, to get started with Core AI, just like an expert, from day one."*

Presenter's reasoning about skills (325:24–28), worth quoting in a guide:

> *"Core AI skills work with you and translate your high-level ideas into a clear deployment plan for downstream tasks. They may get clarifications from you around **the model you are interested in, the hardware families you are targeting, and the constraints your application has**. These requirements inform the Core AI features you need, all the way from any changes in the PyTorch model code to conversion, optimization and running the models. AI skills give your coding agent access to the best practices and domain knowledge from our engineers. This empowers you to leverage Core AI like a pro... In fact, **most of the code you will see throughout this talk was co-developed with an agent actively leveraging these skills**."*

**[VERIFIED]** The skills are real and vendored. `repos/apple__coreai-models/.claude-plugin/` declares a plugin named `coreai-skills` sourced from `./skills`:

```json
{
  "name": "coreai-models",
  "metadata": {
    "description": "Agent skills for authoring, exporting, compiling, and running Core AI models on Apple silicon.",
    "version": "0.1.0"
  },
  "owner": { "name": "Apple" },
  "plugins": [
    { "name": "coreai-skills",
      "description": "Skills for authoring, exporting, compiling, and running PyTorch models on Apple silicon via Core AI.",
      "version": "0.1.0",
      "source": "./skills" }
  ]
}
```
(`repos/apple__coreai-models/.claude-plugin/*.json`)

There is also a `skills/gemini-extension.json` — i.e. the skill bundle ships for **more than one** coding assistant.

**The three skills** (`repos/apple__coreai-models/skills/skills/`):

| Skill | References it ships |
|---|---|
| `working-with-coreai` | `references/guidance.md` |
| `model-authoring` | `references/common_issues.md`, `gpu_rules.md`, `neural_engine_rules.md` |
| `model-compression-exploration` | `references/compression_patterns.md`, `experiment_runner.md`, `output_report.md`, `size_estimation.md`; `scripts/compression_metrics.py`, `scripts/quality_metrics.py` |

**[VERIFIED: repos/apple__coreai-models/skills/skills/working-with-coreai/SKILL.md:2–3]** — the skill's own trigger description, which reveals the vocabulary Apple expects developers to use:

```
description: Use this skill whenever the user mentions coreai-torch, TorchConverter,
coreai-build, AIModel, AIProgram, .aimodel, or wants to export/compile/run a PyTorch
model on Apple silicon (iPhone, iPad, Mac). Also triggers for "deploy on device",
"optimize for on-device performance", onboarding new models to Core AI, or choosing
between iOS and macOS deployment paths.
```

The same SKILL.md states the canonical 5-step pipeline (this is the mental model the whole talk follows):

```text
1. AUTHOR        Re-structure model for target platform
                  → Skill("coreai-skills:model-authoring")
2. COMPRESS      Explore quantization/palettization tradeoffs
                  → Skill("coreai-skills:model-compression-exploration")
3. EXPORT        Convert PyTorch → AIProgram via TorchConverter
                  → coreai-torch docs
4. COMPILE       Ahead-of-time compilation for target platform
                  → coreai-build CLI
5. RUN           Load and run on device (Swift or Python)
                  → CoreAI framework / coreai Python API
```
with the note: *"Steps 1 and 2 are optional — many models export directly without re-authoring or compression. Start with export, then add authoring or compression if needed (poor accuracy, poor performance, too large)."*

## 1.3 Installation and package layout

**[TRANSCRIPT] 325:30–31:**
> *"The Core AI Python libraries, primarily Core AI PyTorch extensions, are your entry point into the ecosystem. Installation is simple with **`pip install coreai-torch`**, this installs both the **`coreai`** package and the **`coreai-torch`** library building on top of it."*

**[VERIFIED]** `repos/apple__coreai-torch/README.md:20–28`:
```bash
pip install coreai-torch
```
```bash
# or from source with uv
uv sync
```

And the second package, **[VERIFIED]** `repos/apple__coreai-optimization/README.md`:
```bash
pip install coreai-opt
# or
uv pip install coreai-opt
# from a checkout:
make env          # creates .venv and installs deps
source .venv/bin/activate
```

> **Naming gotcha.** The distribution is `coreai-opt`; the import is `coreai_opt`. The distribution `coreai-torch`; import `coreai_torch`. The runtime/authoring core is plain `coreai` (`coreai.runtime`, `coreai.authoring`, and the private `coreai._compiler`).

### `coreai_torch` module map [VERIFIED — `ls -R repos/apple__coreai-torch/coreai_torch`]

```
__init__.py  __version__.py
_aten_to_core.py            _composite_declaration.py   _custom_to_core.py
_debug_locations.py         _decomp.py                  _torch_metal_kernel.py
_type_mapping.py            _utils.py                   _validate.py
converter.py                externalize.py              py.typed
_compression/   __init__.py _floatx.py _intx.py _types.py custom_layers.py utils.py
composite_ops/  __init__.py _gated_delta_update.py _gather_mm.py _rms_norm.py _rope.py _sdpa.py _utils.py
debugging/      __init__.py benchmarker.py comparator.py debug_info.py graph_diff.py
                graph.py inspector.py search_strategy.py torch_utils.py validator.py
```

### `coreai_opt` module map [VERIFIED — `find repos/apple__coreai-optimization/src -type d`]

```
coreai_opt/{_utils, config, coreai_utils, quantization, inspection, pruning, deps, casting, palettization}
coreai_opt/quantization/{_graph, config, spec, _eager}
coreai_opt/palettization/{config, spec, kmeans}
coreai_opt/pruning/{config, spec}
```

Note `pruning/` exists as a first-class sibling of quantization and palettization — the transcript only name-drops pruning implicitly ("popular model optimizations"), but the README is explicit: *"`coreai-opt` provides implementations of popular model optimizations such as **quantization, palettization (codebook-based compression), and pruning**, for PyTorch models, customized for deployment on Apple Silicon via Core AI."*

## 1.4 What `coreai-torch` does (capability list, 325:32–35)

**[TRANSCRIPT]** *"You hand `coreai-torch` a PyTorch exported program, and it converts directly to a Core AI model. It supports advanced features that let you tailor the Core AI program to your exact use-case. For example, you can:*
1. *assemble **multiple models into a single artifact**,*
2. *register **custom lowerings for specific operations**, and*
3. *inline **Metal 4 kernels** right into your converted model.*

*And finally, you can **specialize models into optimized assets, and run them natively on Apple Silicon entirely from Python**."*

> Note the phrase **"Metal 4 kernels"** (325:34, 325:177) — the custom-kernel story is explicitly tied to Metal 4, not legacy Metal.

**[VERIFIED]** README:3 matches all three, plus one more (externalization):
> *"Use it to bring up an existing PyTorch model into Core AI IR, or to author Core AI models directly from PyTorch by composing the built-in composite op library (`coreai_torch.composite_ops`), authoring new ops via `register_torch_lowering`, and authoring inline Metal GPU kernels via `TorchMetalKernel`."*

## 1.5 The basic conversion pipeline

**[TRANSCRIPT] 325:38–52** — the presenter walks a two-linear-layer + ReLU net through export → convert → save → run.

**[RECONSTRUCTED] the model shown on screen** (325:39: *"two linear layers with a relu activation"*). The `coreai-torch` quickstart notebook has a byte-for-byte plausible match, so I use it as the **[VERIFIED]** stand-in:

**[VERIFIED: repos/apple__coreai-torch/docs/getting-started/quickstart.ipynb, cell 2]**
```python
import torch
import torch.nn as nn


class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = nn.Linear(10, 20)
        self.relu = nn.ReLU()
        self.linear2 = nn.Linear(20, 5)

    def forward(self, x):
        x = self.linear1(x)
        x = self.relu(x)
        x = self.linear2(x)
        return x


model = SimpleModel()
model.eval()
```
Quickstart cell 3 adds a rule the talk skips: *"**Always call `.eval()` before exporting.** Layers such as `BatchNorm` and `Dropout` behave differently in training mode and produce a different graph."*

**Export step** — 325:41–44: *"Then, I run `torch.export`, I pass the model and an `example_input`, which gives me an `exported_program`. This `exported_program` is the starting point for Core AI conversion. **It captures the full computational graph: weights, operations and shapes** in a format that `coreai-torch` can work with."*

```python
example_input = (torch.randn(1, 10),)
exported = torch.export.export(model, args=example_input)
```

**Decomposition step** — the talk mentions this only later (325:78, in the SAM3 helper), but it is *mandatory*:

**[VERIFIED: repos/apple__coreai-torch/docs/api/TorchConverter.md:53–55]**
> ```{warning}
> The caller **must** call `run_decompositions()` on the program before passing it here — use `get_decomp_table()` to preserve known composite ops in the lowered IR.
> ```

**[VERIFIED: quickstart.ipynb cell 8]** *"This call is required when using `add_exported_program()`. Skipping it will leave ops in the graph that have no lowering rule."*

```python
from coreai_torch import get_decomp_table
exported = exported.run_decompositions(get_decomp_table())
```

**Convert step** — 325:46: *"Core AI's `TorchConverter` takes my exported program, along with the input and output names, and converts it to a `coreai_program`."* (The raw transcript renders this as "core_ai_ program" — an ASR artifact for the variable `coreai_program`.)

```python
from coreai_torch import TorchConverter

converter = TorchConverter()
coreai_program = converter.add_exported_program(
    exported,
    input_names=["x"],
    output_names=["out"],
).to_coreai()
coreai_program.optimize()
```

**Optimize + save step** — 325:48: *"The converted model is then **optimized** and saved as an **aimodel asset** — an on-device format ready to run on Apple Silicon."*

Note the crucial detail the transcript blurs: `optimize()` is a **method on the `AIProgram`, called for its side effect, in-place** — every single example in the repo calls it as a bare statement after `to_coreai()`, never assigning the result:

```python
coreai_program = converter.to_coreai()
coreai_program.optimize()          # <- in-place, return value never used in any doc example
asset = coreai_program.save_asset(Path(tmpdir) / "quick_start_example.aimodel")
```

**Run step** — 325:49–51: *"Once I have the specialized asset, I can **load a function from the program** and perform inference right from Python. You can also **pass specialization options** at this point to customize the process. To actually run inference, all you need to do is provide **a dictionary mapping input names to corresponding numpy tensors**!"*

**[VERIFIED: quickstart.ipynb cell 12]** — the full async run loop:
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

            with torch.no_grad():
                pytorch_output = model(example_input[0])

            coreai_output = coreai_outputs["out"].numpy()
            pytorch_numpy = pytorch_output.numpy()
            print(f"Outputs match: {np.allclose(pytorch_numpy, coreai_output, atol=1e-4)}")


await compile_and_run(coreai_program, example_input, model)
```

Key facts this pins down that the transcript only gestures at:
- `save_asset()` returns an **`AIModelAsset`**; the `.aimodel` is a **directory**, not a file.
- Inference is **`async`**: `async with asset.executable() as ai_model`, then `await function(inputs)`.
- Default entrypoint name is **`"main"`**.
- Outputs come back keyed by **output name**; `.numpy()` materializes them.

**[VERIFIED: repos/apple__coreai-torch/docs/coreai-core/tutorials/run-an-aimodel.ipynb]** adds the four public runtime types and two lifecycle warnings:

> - **`AIModelAsset`** — the on-disk representation of a saved program (from `coreai.authoring`).
> - **`InferenceFunction`** — a callable function inside the model (here, `main`).
> - **`NDArray`** — the runtime's multi-dimensional array type... *"(which accepts a NumPy array, a PyTorch tensor, or a Python list, wrapping the data without a copy where possible)"*
> - **`SpecializationOptions`** — for advanced device/configuration tuning.

> *"`AIModelAsset.load` reads the `.aimodel` directory header from disk so you can inspect it; **it does not yet compile the program for inference. That work happens lazily inside the `executable()` async context manager**."*

> *"**Two ways to load a model.** ... `AIModelAsset.load(path)` followed by `async with asset.executable() as model:` — the resource-managed form... There is also a one-shot **`await AIModel.load(path)`** that returns a runnable `AIModel` directly; reach for it when you want a long-lived model handle without the `async with` block."*

> **FOOTGUN (verbatim):** *"Materialize the result inside the block — **the model's backing buffers are only guaranteed valid until the context exits**."* (call `.numpy()` before leaving `async with`.)

Runtime introspection surface, verbatim from the same notebook:
```python
async with asset.executable() as model:
    print(f"functions: {model.function_names}")
    function: InferenceFunction = model.load_function("main")
    desc = function.desc
    print(f"name:    {desc.name}")
    print(f"inputs:  {desc.input_names}")
    print(f"outputs: {desc.output_names}")
```
And the two advanced runtime knobs:
```python
from coreai.runtime import SpecializationOptions, StorageKind
```
- `SpecializationOptions` — *"pass to `asset.executable(options)` to pin the preferred compute unit (CPU / GPU / Neural Engine) or enable debug mode. **(macOS only.)**"* ← this is the "specialization options" the transcript mentions at 325:50, and the **macOS-only** restriction is a real gate.
- `StorageKind` — *"passed to `NDArray(data, backing=...)` to choose byte-backed, IOSurface-backed, or Metal-backed storage. The default (`StorageKind.BYTES`) is what you want unless you are interoperating with graphics or camera buffers."*

### `TorchConverter` full API [VERIFIED: repos/apple__coreai-torch/docs/api/TorchConverter.md]

```python
TorchConverter()                                    # no loaded programs, no custom lowerings

def add_exported_program(
    self,
    exported_program: ExportedProgram,
    input_names: Sequence[str] | None = None,
    output_names: Sequence[str] | None = None,
    state_names: Sequence[str] | None = None,
    entrypoint_name: str = "main",
) -> TorchConverter                                  # returns self, chainable

def add_pytorch_module(
    self,
    module: nn.Module,
    export_fn: Callable[[nn.Module], ExportedProgram],
    externalize_modules: list | None = None,
    input_names: Sequence[str] | None = None,
    output_names: Sequence[str] | None = None,
    state_names: Sequence[str] | None = None,
    entrypoint_name: str = "main",
) -> TorchConverter

def to_coreai(self, *, entrypoints: Sequence[str] | None = None) -> AIProgram

def clear(self, *, entrypoints: Sequence[str] | None = None) -> None
    # "Custom lowerings registered via register_torch_lowering() are always preserved."

def register_torch_lowering(self, qualified_name: str, allow_override: bool = False) -> Callable

def register_custom_kernels(self, kernels: Sequence[TorchMetalKernel]) -> TorchConverter

# standalone
def get_decomp_table() -> dict     # "Each call returns a fresh copy of the table"
```

**Breaking-change notes flagged in the doc** (important for anyone with pre-release code):
- `input_names` — *"Names for non-stateful user inputs only. Mutated inputs (buffers and user-input mutations) are renamed via `state_names`. **Breaking change**: previously this covered all graph inputs."*
- `output_names` — same shape of breaking change for outputs.
- `entrypoint_name` — *"Must be unique across all staged programs."*

**IO naming / state semantics — [VERIFIED: TorchConverter.md:409–418], a genuine footgun:**
> **What counts as state (no opt-out).** The converter treats two things as state:
> 1. **Mutable buffers** registered via `self.register_buffer(...)` and mutated in-place inside `forward()` (e.g., `self.buf.add_(x)`).
> 2. **User inputs mutated in-place** inside `forward()` (e.g., `x.mul_(2)` on a `forward()` arg).
>
> Both are detected from the exported program's graph signature. There is **no flag** to opt a mutated user input out of state... If you don't want a `forward()` argument treated as state, eliminate the in-place mutation from your model — clone first (`x_local = x.clone(); x_local.mul_(2)`) or use the out-of-place form (`x_scaled = x * 2`).

Default names when you omit the parameters (observed FX behavior, **explicitly not a stable contract**):

| Category | FX source | Example |
|---|---|---|
| Input | placeholder `node.name` | `def forward(self, x, z)` → `"x"`, `"z"` |
| Output | output node's input `node.name` | `return a + b, c * d` → `"add"`, `"mul"` |
| State (buffer) | placeholder `node.name` | `register_buffer("kv_cache", ...)` → `"b_kv_cache"` |
| State (mutated user input) | placeholder `node.name` | `def forward(self, y): y.mul_(2)` → `"y"` |

> *"These naming conventions are observed behavior from the FX graph, not a stable contract from PyTorch. They may change across PyTorch versions. **Always provide explicit names for production use.**"*
> *"The ordering of `state_names` (buffers first, then mutated user inputs) is based on observed FX graph behavior... The converter asserts that the number of state inputs matches state outputs, but **cannot detect silent reordering**. Always verify state ordering when upgrading PyTorch versions."*

These names propagate to the runtime descriptor: `desc.input_names`, `desc.output_names`, `desc.state_names`.

## 1.6 SAM3 as the driving optimization use-case

**[TRANSCRIPT] 325:54–63.** SAM3 = Segment Anything Model 3, **"an 850-million parameter model that performs prompt-based image segmentation."** Structure as described:

| Component | Role | Share of params |
|---|---|---|
| Image encoder | processes the image | *(with text encoder)* **96%** |
| Text encoder | handles the user's prompt | *(with image encoder)* **96%** |
| Detector (DEtection TRansformer + mask decoder) | produces the segmentation mask | **4%** (stated at 325:158) |

> 325:60 — *"These two components combined make up **96% of the model's parameters** so **getting these right is key**."*
> 325:63 — *"this is exactly the kind of use-case developers increasingly want to execute on-device."*

**[VERIFIED — cross-check]** `repos/apple__coreai-models/models/sam3/README.md` gives **848M** parameters for `facebook/sam3` (transcript rounds to "850-million"), and lists the exact three-function split with per-function compression:

| Function | Compression | Inputs | Outputs |
|---|---|---|---|
| `image_encode` | 4-bit k-means palettization (gs=32) + fp16 | `pixel_values` | `backbone_features` |
| `text_encode` | 6-bit k-means palettization (gs=8) + fp16 | `input_ids` | `text_features` |
| `detect` | fp16 (no weight compression) | `backbone_features`, `text_features` | `pred_masks`, `pred_boxes`, `pred_logits`, `presence_logits` |

> **DISCREPANCY worth flagging in a guide.** The transcript (325:241) says *"I apply **4-bit** palettization... to **the two encoders**"*. The shipped recipe is **asymmetric**: image encoder w4/gs32, text encoder **w6/gs8**. The talk simplified.

## 1.7 `coreai-opt` — capability claims

**[TRANSCRIPT] 325:64–68:**
- *"`coreai-opt` enables **config-driven model compression**, you describe **what to compress and what to leave alone**."*
- *"It supports **various optimization schemes**, from which you can choose one to **optimize differently for macOS versus iOS**, as an example."*
- *"It also supports **int4, int8, FP4 and FP8** weight compression with **flexible granularity**."*
- *"`coreai-opt` includes quantization APIs that you can either use with a **small amount of calibration data**, or perform **quantization aware training on larger data sets**."*

**[VERIFIED]** every claim:
- Config-driven with a strict precedence hierarchy — `QuantizerConfig` docstring (`src/coreai_opt/quantization/config/quantization_config.py:576–582`):
  > *"The configuration lookup follows a hierarchical precedence (most to least specific): 1. `module_name_configs` — Applies to module instances matching a name pattern (**supports regex**) 2. `module_type_configs` — Applies to all modules of a specific type 3. `global_config` — Default configuration applied to all modules not otherwise configured"*
  > *"Setting a config to `None` explicitly disables quantization for that scope."* ← this is the **"leave alone"** mechanism, and it is exactly how you'd "ignore the detector."
- FP4/FP8 — `docs/src/quantization/config.md` has a `W_MXFP4_A_FP8` worked example:
  ```python
  fp8_activation = QuantizationSpec(dtype=torch.float8_e4m3fn)
  mxfp4_weight = QuantizationSpec(
      dtype=torch.float4_e2m1fn_x2,
      granularity=PerBlockGranularity(block_size=32),
      scale_dtype=torch.float8_e8m0fnu,      # <- E8M0 again; ties directly to session 330
  )
  config = QuantizerConfig(
      global_config=ModuleQuantizerConfig(
          op_input_spec={"*": fp8_activation},
          op_output_spec={"*": fp8_activation},
          op_state_spec={"weight": mxfp4_weight},
      )
  )
  ```
  YAML equivalent (configs are YAML-loadable via `QuantizerConfig.from_yaml("config.yaml")` / `from_dict`):
  ```yaml
  quantization_spec:
    spec1: &fp8_activation
      dtype: float8_e4m3fn
    spec2: &mxfp4_weight
      dtype: float4_e2m1fn_x2
      granularity: { type: per_block, block_size: 32 }
      scale_dtype: float8_e8m0fnu
  quantization_config:
    global_config:
      op_input_spec: { "*": *fp8_activation }
      op_output_spec: { "*": *fp8_activation }
      op_state_spec: { weight: *mxfp4_weight }
  ```
- Calibration + QAT — `Quantizer` exposes `calibration_mode()` and `training_mode()` context managers plus a `QATSchedule` (see §1.9).

**The three op-level tensor groups** (this is the vocabulary the whole config system is built on):

| Field | Targets |
|---|---|
| `op_input_spec` | input activations to ops; `{"*": spec}` quantizes all supported inputs, `None` disables |
| `op_output_spec` | output activations from ops |
| `op_state_spec` | weights and other `state_dict` tensors; `{"weight": spec}` targets weights only (excludes `bias`) |

Weight-only quantization = `op_input_spec=None, op_output_spec=None, op_state_spec={"weight": ...}` — exactly what the `w4`/`w8` presets do.

## 1.8 The compression step inserted into the pipeline

**[TRANSCRIPT] 325:69–72:** *"This is the simple pipeline I had previously. Now I am adding a step. **Before conversion**, I run the model through `coreai-opt` with a compression config or I can use one of their convenient **presets**. This gives me a smaller model that still goes through the same export pipeline."*

Pipeline shape:
```
nn.Module ──(coreai-opt: Quantizer / KMeansPalettizer, prepare→finalize)──► compressed nn.Module
          ──(torch.export.export)──► ExportedProgram
          ──(run_decompositions(get_decomp_table()))──► decomposed ExportedProgram
          ──[optional cast_to_16_bit_precision]──►
          ──(TorchConverter.add_exported_program → to_coreai → optimize)──► AIProgram
          ──(save_asset)──► .aimodel
```

### The SAM3 export wrapper and reusable conversion helper (325:74–80)

**[TRANSCRIPT]**
> 325:74–75 — *"I start by **wrapping SAM3 for export**. This wrapper defines the interface for torch export to capture the full computational graph of the model."*
> 325:76 — *"And here's the conversion pipeline from the slides, **wrapped into a reusable helper**. A couple of interesting points though."*
> 325:78–79 — *"**First**, it runs decompositions in the PyTorch `exported_program` with **Core AI's custom table**. This ensures that **high-level semantics that Core AI supports, like attention, are preserved in the graph**."*
> 325:80 — *"**Second**, it also supports **casting the program to 16-bit floating point using `coreai-opt`'s helper**, if needed."*

Both points are verifiable:
- **Custom decomp table** — `get_decomp_table()`: *"Returns the default PyTorch ATen decomposition table **minus** the operations that `TorchConverter` lowers as composite ops, so those operations are preserved in the exported graph rather than being decomposed into lower-level primitives."* The README names the preserved trio explicitly: *"Use `get_decomp_table()` so that composite ops (`instance_norm`, `pixel_shuffle`, `scaled_dot_product_attention`) are preserved for optimal runtime performance."*
- **fp16 cast helper** — `coreai_opt.casting` public API [VERIFIED: `src/coreai_opt/casting/__init__.py` and `casting.py:19–21`]:
  ```python
  from coreai_opt.casting import (
      cast_fp32_to_fp16,          # -> ExportedProgram
      cast_int32_to_int16,        # -> ExportedProgram
      cast_to_16_bit_precision,   # -> ExportedProgram (FP then INT casting)
  )
  ```
  Module docstring on the strategy:
  > *"FP32→FP16: Convert parameters/inputs upfront, walk nodes topologically **inserting casts only when ops should run in higher precision**, let cleanup collapse roundtrips between consecutive casted ops. INT32→INT16: Convert inputs where all uses are safe args, walk nodes topologically inserting int16 casts at designated ops with cast-backs after..."*
  It operates on the **ExportedProgram**, i.e. **after** `torch.export` and `run_decompositions`, not on the `nn.Module`.

**[RECONSTRUCTED] the helper as described** (shape confirmed against `coreai_models/segmentation/pipeline.py`):
```python
def convert(module, example_args, *, input_names, output_names,
            entrypoint_name="main", fp16=True):
    ep = torch.export.export(module, args=example_args)
    ep = ep.run_decompositions(coreai_torch.get_decomp_table())   # Core AI's custom table
    if fp16:
        ep = cast_to_16_bit_precision(ep)                          # coreai-opt helper
    converter = coreai_torch.TorchConverter()
    converter.add_exported_program(
        ep, entrypoint_name=entrypoint_name,
        input_names=input_names, output_names=output_names,
    )
    program = converter.to_coreai()
    program.optimize()
    return program
```

### Baseline run (325:81–88)

> *"The full conversion **takes a few minutes**, so I have pre-computed the baseline asset."*
> *"What I do here is load the baseline **32-bit** converted model and run it. As you can see, it's **over 3 gigs** in size."*
> *"When I run, **the default specialization kicks in** to specialize and run the model."*
> *"In this image, I ask for a segmentation mask over **all the flowers**. All are successfully detected based on the default threshold, running on-device. **This is what I need to preserve after compression.**"*

## 1.9 Quantization with presets — the `w4` experiment

**[TRANSCRIPT] 325:90–95:**
> *"`coreai-opt` ships with **preset configurations**. `presets.w4` gives me **4-bit per-channel, symmetric quantization in one line**."*
> *"I set **`ExecutionMode` to `EAGER`, which works great for weight compression. For activations, I would use the `GRAPH` mode.**"*
> *"Then I initialize `coreai-opt`'s **`Quantizer`** with the config, **pass example inputs** and **finalize** — the model is then compressed."*

**[RECONSTRUCTED, high confidence]:**
```python
from coreai_opt.quantization import Quantizer, QuantizerConfig, ExecutionMode

config = QuantizerConfig.presets.w4()
config.set_execution_mode(ExecutionMode.EAGER)     # or: QuantizerConfig.presets.w4(execution_mode=ExecutionMode.EAGER)

quantizer = Quantizer(sam3_wrapper, config)
prepared = quantizer.prepare(example_inputs)       # example_inputs is a tuple
quantized = quantizer.finalize()
```

**[VERIFIED: repos/apple__coreai-optimization/src/coreai_opt/quantization/config/_presets/quantizer_config.py]** — the preset is exactly "4-bit per-channel symmetric," and both signatures accept `execution_mode` directly:

```python
def w4(
    self,
    *,
    axis: int | None = None,
    execution_mode: ExecutionMode = ExecutionMode.GRAPH,
) -> QuantizerConfig:
    """int4 weight-only quantization, per-channel symmetric."""
    weight_spec = QuantizationSpec(
        dtype=torch.int4,
        qscheme=QuantizationScheme.SYMMETRIC,
        granularity=PerChannelGranularity(axis=axis),
    )
    global_config = ModuleQuantizerConfig(
        op_input_spec=None,
        op_output_spec=None,
        op_state_spec={"weight": weight_spec},
    )
    return self._owner_cls(global_config=global_config, execution_mode=execution_mode)
```

**Full `QuantizerConfig.presets` roster [VERIFIED]:**

| Preset | Meaning | Extra kwargs |
|---|---|---|
| `w8(*, axis=None, execution_mode=GRAPH)` | int8 weight-only, per-channel symmetric | — |
| `w4(*, axis=None, execution_mode=GRAPH)` | int4 weight-only, per-channel symmetric | — |
| `w4_per_block(*, block_size=32, axis=None, execution_mode=GRAPH)` | int4 weight-only, **per-block** symmetric | `block_size` default **32** |

> *"`axis`... When `None` (default), the axis is **auto-resolved based on the module type** during quantization."*

**`ExecutionMode` [VERIFIED: quantization_config.py:134–158]:**
```python
class ExecutionMode(_StrEnum, metaclass=_DeprecatedMemberEnumMeta):
    GRAPH = auto()   # torch.export → FX graph, built on torchao's PT2E. "Recommended default."
    EAGER = auto()   # works directly on nn.Module, no graph capture. Supports dynamic control flow.
    __deprecated_aliases__ = {"PT2E": "GRAPH"}     # ExecutionMode.PT2E is deprecated → use GRAPH
```
Docstrings verbatim:
- `GRAPH`: *"Graph-based quantization using `torch.export` to capture the model as an FX graph, then applying quantization on top. Built on `torchao`'s PT2E implementation. **Requires the model to be exportable via `torch.export.export`. Recommended default.**"*
- `EAGER`: *"Eager-mode quantization that works directly on `nn.Module` without graph capture. **Supports dynamic control flow (if/else, loops) and is the fallback when a model is not exportable.**"*

> ⚠️ **DISCREPANCY / nuance to surface in a guide.** The *transcript* says EAGER "works great for weight compression" and to reach for GRAPH for activations. The *repo* calls GRAPH the "recommended default" and `QuantizerConfig.execution_mode` **defaults to `ExecutionMode.GRAPH`** (`quantization_config.py:695`). Reconciliation: for weight-only compression the two modes converge, and EAGER avoids the `torch.export` requirement — a real win for a model as gnarly as SAM3. For activation quantization the graph-mode machinery (observer dedup, FQ-node dedup, module fusion) actually matters. The repo spells out why:

**[VERIFIED: src/coreai_opt/quantization/quantizer.py, GRAPH-vs-EAGER comparison table]**
| Dimension | GRAPH | EAGER |
|---|---|---|
| Module fusion | Automatic pattern-based fusion (e.g. conv+bn+relu) | Manual fusion required |
| Control flow | Static graph only; requires `torch.export`-compatible model | Supports dynamic control flow (if/else, loops) |
| Shared observer ops | *"ops like MaxPool that share the same observer across inputs and outputs are detected and deduplicated on the graph"* | *"Not supported; ops like MaxPool have independent observers for input vs output, **which can cause incorrect quantization**"* |
| FQ node dedup | Back-to-back fake-quantize nodes collapsed into one | *"No deduplication; ... two consecutive FQ nodes are inserted on that intermediate edge"* |

> **Verbatim warning:** *"As a result of above mentioned differences, the total number of fake-quantize nodes inserted by graph and eager mode can differ for the same `QuantizerConfig`. This means the two modes are **not guaranteed to produce equivalent quantized models**, and final model performance (accuracy and latency) may differ between modes even when using identical configurations."*

**`Quantizer` workflow surface [VERIFIED: quantizer.py docstring examples]:**
```python
from coreai_opt.quantization import Quantizer, QuantizerConfig, ExecutionMode

# --- PTQ with calibration (default int8, graph mode) ---
config = QuantizerConfig()
quantizer = Quantizer(model, config)
prepared_model = quantizer.prepare((example_input,))
with quantizer.calibration_mode():
    for data in calibration_loader:
        prepared_model(data)
quantized_model = quantizer.finalize()

# --- QAT (default schedule — observers and fake_quant enabled throughout) ---
prepared_model = quantizer.prepare((example_input,))
with quantizer.training_mode():
    for epoch in range(num_epochs):
        for data, target in train_loader:
            optimizer.zero_grad()
            output = prepared_model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
quantized_model = quantizer.finalize()

# --- QAT with an explicit schedule ---
from coreai_opt.quantization import ModuleQuantizerConfig
from coreai_opt.quantization.config import QATSchedule
# Enable observers from the start, enable fake quant at the 100th step,
# and disable observers at the 500th step.
schedule = QATSchedule(enable_observer=0, enable_fake_quant=100, disable_observer=500)
config = QuantizerConfig(global_config=ModuleQuantizerConfig(qat_schedule=schedule))
quantizer = Quantizer(model, config)
prepared_model = quantizer.prepare((example_input,))
with quantizer.training_mode():
    for data, target in train_loader:
        optimizer.zero_grad()
        loss = criterion(prepared_model(data), target)
        loss.backward()
        optimizer.step()
        quantizer.step()                    # <- required to advance the QAT schedule
quantized_model = quantizer.finalize()
```
- `Quantizer(model, config=None)` — *"If None, a default configuration with int8 weight and activation quantization is created."*
- `quantizer.step()` is what advances a `QATSchedule`; without it the schedule never fires.

Also present (not mentioned in the talk but relevant to LLM work): **`kv_cache_quant_configs`** on `QuantizerConfig` — *"Each entry enables storing the corresponding KV-cache buffer in a quantized dtype... **Graph mode only; rejected for eager mode.**"* Raises:
```
ValueError: kv_cache_quant_configs is only supported with ExecutionMode.GRAPH (got ...)
```

### The result — and the failure that motivates the debugger

**[TRANSCRIPT] 325:96–102:**
> *"As before, I load the model and run it on-device. The model is now **around 430 megabytes**."*
> *"Look at the result. **One of the occluded flowers is no longer detected.**"*
> *"**I applied the same aggressive compression to every single layer, and it's likely that not every layer handles this equally well.** The question is — **which layers are causing this?** This is the kind of problem that's **hard to diagnose from the output alone. I need to see inside the model.**"*

So: **3 GB (fp32) → ~430 MB (int4)**, roughly 7×, with a visible quality regression on an occluded object.

## 1.10 Core AI Debugger (Nicole, 325:104–165)

**[TRANSCRIPT] 325:107–108:** *"Core AI Debugger is a **new standalone application** that can help you inspect your models on Apple platforms. With the debugger you can:*
1. *visualize your model's structure in an easy-to-understand **graph format**,*
2. *execute your model on **specific hardware** for **true runtime results**, and*
3. *validate **inference correctness against a reference run** — all in one place."*

**[VERIFIED cross-check]** `docs/Run AI models in your app on Apple silicon.md:22` — *"The [Core AI Debugger](https://developer.apple.com/core-ai-debugger/) app supports visualization and numeric debugging, letting you inspect model structure and **trace tensor values directly back to your Python source code**."* Distribution URL: `https://developer.apple.com/core-ai-debugger/`.

### Static analysis workspace

| Pane | Position | What it shows |
|---|---|---|
| **Navigator** | left | *"a structured list of operations in the model"*, **grouped by their PyTorch module** |
| **Structure viewer** | top | graph view — *"operation connectivity, execution order, and data dependencies"* |
| **Source viewer** | bottom | *"I'm always grounded in my model's original Python code **down to the specific line**"* |
| **Inspector** | right | per-op *"description, and additional details on the operation's inputs and outputs"* |

Flow described: open the model → click **Inspect** → workspace opens (325:110–111).

> 325:113 — *"These operations are grouped by their PyTorch module, which is **especially powerful for larger models like SAM3** and allows you to navigate your model in a way that feels familiar."*
> 325:114 — *"Selecting a PyTorch module in the navigator, like the **detector decoder**, will **highlight all of the corresponding nodes** in the structure viewer."*
> 325:119 — *"Together, these views allow you to move fluidly between **graph structure, source code, and execution details**, which **dramatically reduces the cognitive overhead of debugging complex models like SAM3**."*

### Runtime analysis on-device

**[TRANSCRIPT] 325:120–129:**
- Click **device** at the top of the workspace.
- In **scheme settings**: *"I'll **pick my Mac from the list of targets**, then specify the inputs I want to provide to the model. Starting with the **pixel values**, then the **input_IDs**, and the **attention_mask**."*
- Click **Run**. → *"SAM3 is now being **specialized** to run on my device."*
- *"the structure viewer has updated to show me the model, **exactly as it would run on my Mac**."*
- *"I can now **click on any operation to see its output tensor directly in the inspector. Without needing to modify anything.**"*
- Tensor inspection: *"In the inspector, I'll click on the **tensor preview** to get a closer look at the mask."*

> Note the input names in the debugger UI — `pixel_values`, `input_ids`, `attention_mask` — match the HF `Sam3Model` signature (and `pipeline.py`'s full-export path uses `pixel_values` + `input_ids`).

### Reference comparison via `save_intermediates`

**[TRANSCRIPT] 325:134–137:**
> *"I'll return to my notebook and use the **NEW save intermediates API**. This API **executes a PyTorch model and captures intermediate tensor values at each operation**. I want to compare my quantized results with the baseline Sachin showed earlier, so **I'll pass in the int4 model alongside the original SAM3**."*

**[VERIFIED: repos/apple__coreai-torch/coreai_torch/debugging/torch_utils.py:905–913]** — the exact signature:
```python
def save_intermediates(  # noqa: PLR0913
    program: ExportedProgram,
    inputs: Union[tuple[Any, ...], list[Any]],
    output_dir: Union[str, Path],
    node_filter: Callable[[torch.fx.Node, Any], bool] = _default_node_filter,
    coreai_program: AIProgram | None = None,
    enable_autocast: bool = False,
    model_name: str = "main",
) -> str:
```
Parameter semantics (verbatim from the docstring):
- `program` — *"ExportedProgram to execute and inspect."*
- `node_filter` — *"callable that takes `(node: torch.fx.Node, result: Any)` and returns True if the node's value should be dumped."*
- `coreai_program` — *"Optional `AIProgram` to extract source info from. If provided, **variable information from source locations will be added to the metadata**."* ← this is how the debugger links intermediates back to Python source lines.
- `enable_autocast` — *"Whether to enable automatic mixed precision during execution. Default is False. **Set to True to handle mixed precision models and avoid dtype mismatch errors.** Uses CPU for autocast operations."*
- `model_name` — *"Creates a directory named **`{model_name}.aimodelintermediates`** within the specified `output_dir`."*
- **Returns:** *"Path to the generated metadata JSON file"* (`<...>.aimodelintermediates/metadata.json`).

On-disk layout: numpy files for tensors + a `metadata.json` with three top-level keys — `"inputs"`, `"outputs"`, `"intermediates"` (plus optional `"mappings"` when `coreai_program` is supplied).

Companion loader [VERIFIED: `torch_utils.py:1164+`, and `docs/api/debugging.md:250–283`]:
```python
from coreai_torch.debugging.torch_utils import save_intermediates, load_intermediates
from pathlib import Path

metadata_path = save_intermediates(
    program=exported_program,
    inputs=example_input,
    output_dir=Path("./debug_output"),
)

debug_trace = load_intermediates(Path("./debug_output/main.aimodelintermediates"))
print(f"Inputs: {list(debug_trace.inputs.keys())}")
print(f"Outputs: {list(debug_trace.outputs.keys())}")
print(f"Intermediates: {len(debug_trace.intermediates)} operations")
for node_name, tensor in debug_trace.intermediates.items():
    print(f"{node_name}: shape {tensor.shape}, mean {tensor.mean():.3f}")
```
Custom filter example:
```python
def custom_filter(node, result):
    """Only save convolution and linear layer outputs"""
    return any(op in str(node.target).lower() for op in ["conv", "linear", "matmul"])

metadata_path = save_intermediates(
    program=exported_program, inputs=example_input,
    output_dir=Path("./debug_output"), node_filter=custom_filter,
)
```
> **Gotcha:** `load_intermediates` validates the directory suffix — passing a path that doesn't end in `.aimodelintermediates` raises with *"Expected a `.aimodelintermediates` directory, but got: ..."*. Also note the docstring examples in the source still call the function `dump_intermediates` (a stale name); the exported symbol is `save_intermediates`.

> **Preview-only environment gate [VERIFIED: docs/api/debugging.md:5–13]:**
> ```bash
> export USE_LOCAL_COREAI=1
> export ENABLE_DEBUG_INFO=1
> ```
> *"During the current preview, set the following environment variables to ensure **operation-level debug metadata is preserved** and available to these tools."* — Without these, module-stack/source-location metadata (the thing that makes the debugger's navigator and source viewer work) may be missing.

### Comparison sessions and **sync points**

**[TRANSCRIPT] 325:139–152** — the core concept of the debugger:
- Click the **comparison icon** at the top of the workspace → *"initialize a new comparison session."*
- Left = existing configuration; right = *"another configuration to compare against **like a different Target or Compute Unit**."*
- *"In this case, I'll click **Target** and load a reference run from an **Intermediates File**."*
- *"The navigator is now populated with **operation pairs** which combine an operation from the **specialized model** and **PyTorch model**."*
- **Definition (325:145):** *"These pairs are called **sync points**, places where the specialized model's output is **expected to match** the original PyTorch result. **The debugger automatically identifies these points throughout the model** to make the comparison process easy."*
- *"Each sync point is paired with a **metric** indicating how similar the two outputs are which makes it **trivial to find where they diverge**."*
- **Default metric (325:148):** *"The default metric is a **peak signal-to-noise ratio or PSNR**, but this **can be changed to whichever similarity indicator suits your model best**."*
- **Color coding (325:150):** *"**green nodes indicate similar tensors, red nodes would indicate significant differences**"*, plus a status indicator on the right. Intermediate = **yellow** (*"several yellow sync points, which indicates that parts of my model have **moderately diverged**"*).
- **Workflow:** *"I'll **sort by similarity**, and investigate the most dissimilar sync points."* Then: *"I'll use the **up arrow key** to navigate through the low-PSNR sync points **one-by-one to see if a pattern emerges**."*
- Clicking a sync point updates the **source viewer** to *"show me the operation's **PyTorch module hierarchy**."*

### The diagnosis and the fix

**[TRANSCRIPT] 325:156–162:**
> *"I'm noticing that **the vast majority of low-PSNR sync points are actually coming from the detector decoder**. This tells me that the quantization scheme applied earlier has **mildly corrupted the detector results**. Since we previously identified that **the detector block only accounts for 4% of model parameters, we're not getting much benefit from compressing it anyway**. So, I'll return to the Jupyter notebook, and try **changing the quantization scheme to ignore the detector**."*
> *"Great! I can see that we have **once again reached baseline quality** where all flowers are detected and the model is only a fraction of the size! **Core AI Debugger turned hours of manual tensor comparison into a visual diagnosis. I started with missing detections and reached a revised quantization scheme in minutes.**"*

**[RECONSTRUCTED] "ignore the detector"** — the config mechanism, grounded in `docs/src/quantization/config.md`:
```python
config = QuantizerConfig.presets.w4(execution_mode=ExecutionMode.EAGER)
# name-pattern scope (supports regex), None == "leave this alone"
config.module_name_configs = {"detector.*": None}
# or by module type:
# config = QuantizerConfig(module_type_configs={"my_pkg.sam3.DetectorDecoder": None})
```
> **[VERIFIED gotcha]** For `module_type_configs`, *"Keys must be the **fully-qualified Python class name** (e.g. `"torch.nn.modules.linear.Linear"`). **Short-form names like `"torch.nn.Linear"` are not supported** — the key must match the internal module path exactly."*

### Other debugging tools not mentioned on stage but shipping in `coreai_torch.debugging`

**[VERIFIED: docs/api/debugging.md]** — worth a whole guide of their own:
```python
# NaN / Inf bisection on a PyTorch program
from coreai_torch.debugging.validator import create_validator_for_exported_program
validator = create_validator_for_exported_program(exported)
nan_result = await validator.check_for_nans(inputs=example_input)
inf_result = await validator.check_for_infs(inputs=example_input)
print(nan_result.failed_nodes[0])          # first failing op

# ...and on a Core AI program
from coreai_torch.debugging.validator import create_validator_for_coreai_program
validator = await create_validator_for_coreai_program(coreai_program, "main")
result = await validator.check_for_nans(inputs={"x": torch.randn(2, 4)})

# Cross-framework comparison (PyTorch vs Core AI)
from coreai_torch.debugging.comparator import create_comparator_for_programs
comparator = await create_comparator_for_programs(
    source_program=exported_program, target_program=coreai_program,
    target_entry_point="main")
result = await comparator.compare_with_tolerance(
    inputs={"x": example_input}, rtol=1e-5, atol=1e-8)
for source_op, target_op in result.failed_nodes:
    print(f"Mismatch: {source_op} vs {target_op}")

# Deployed-model intermediates
from coreai_torch.debugging.inspector import CoreAIInspector
from coreai.runtime import AIModel
ai_model = await AIModel.load(Path("my_model.aimodel"))
inspector = CoreAIInspector(model=ai_model, function_name="main")
results = await inspector.get_intermediates_for_ops(
    [1, 5, 10, 15], inputs={"x": np.random.randn(2, 4).astype(np.float32)})

# Structural graph diff (graph isomorphism)
from coreai_torch.debugging.graph_diff import (
    compute_exported_program_diff, compute_coreai_program_diff, write_diff)
diff = compute_exported_program_diff(source_program, target_program)
if diff.is_isomorphic: ...
else: print(diff.summary.unmapped_source_node_count)
write_diff(diff, diff.source_graph, diff.target_graph, max_items=20)

# Op-level benchmarking
from coreai_torch.debugging.benchmarker import benchmark_coreai_program
result = await benchmark_coreai_program(
    coreai_program=coreai_program, inputs={"x": torch.randn(2, 4)}, num_runs=50)
result.write_summary(sys.stdout)
for name, module in result.get_module_timings().items():
    print(f"{name}: {module.aggregated_op_stats.average:.3f}ms avg")

# Custom predicate checks
def check_large_values(outputs):
    return any(abs(arr).max() > 1000.0 if arr is not None else False for arr in outputs)
result = await validator.check(check_large_values, inputs=example_input)

# Search strategies for the bisection
from coreai_torch.debugging.search_strategy import LevelOrderStrategy
strategy = LevelOrderStrategy.bisection(graph, batch_size=10)   # default, fastest to first issue
strategy = LevelOrderStrategy.top_down(graph)                   # systematic inputs → outputs
strategy = LevelOrderStrategy.auto(graph)                       # adaptive
```
Nearly everything in this module is **`async`**.

## 1.11 Advanced model authoring — op fusion and custom Metal kernels

**[TRANSCRIPT] 325:166–177** — framing:
> *"So far, I have been converting the model as a **single, end-to-end unit**. And for a lot of models, **that works just fine**. But it may not always be enough, depending on your use-case and **especially your constraints**. And this is where Core AI really empowers you to dig deeper."*
> *"**What advanced model authoring implies, is that you look inside this computational graph and really tune how it runs on the hardware.**"*
> *"you can take a group of those ops and **fuse them into a single operation**. This **replaces several steps with a single kernel dispatch** within the graph."*
> *"Core AI **already ships with pre-packaged fast kernels and primitives for heavy operations like Scaled Dot Product Attention**, commonly found in Transformers. You can find examples of how to leverage these operations in the `coreai-models` repository."*
> *"But if you **live on the cutting edge** and want even more customization, we also have support for **custom Metal 4 kernels**."*

**[VERIFIED]** The "pre-packaged" composite ops are `coreai_torch.composite_ops`, documented per-op under `docs/api/composite-ops/`:
`aten-derived`, `batch-norm`, `gated-delta-update`, `gather-mm`, `group-norm`, `hard-sigmoid`, `instance-norm`, `layer-norm`, `linalg-vector-norm`, `log-softmax`, `module-class`, `pixel-shuffle`, `rms-norm`, `rope`, `sdpa`.
Source modules: `_gated_delta_update.py`, `_gather_mm.py`, `_rms_norm.py`, `_rope.py`, `_sdpa.py`.

How you *mark* a block as a composite op — **[VERIFIED: docs/guides/conversion-workflows.ipynb cell 8]**:
```python
from coreai_torch import ExternalizeSpec, TorchConverter
from coreai_torch.composite_ops import RMSNormImpl

converter = TorchConverter().add_pytorch_module(
    model,
    export_fn=lambda m: torch.export.export(m, args=sample).run_decompositions(
        coreai_torch.get_decomp_table()
    ),
    externalize_modules=[
        ExternalizeSpec(
            target_class=RMSNormImpl,
            composite_op_name="rms_norm",
            composite_attrs=["axes", "eps"],
        )
    ],
)
coreai_program = converter.to_coreai()
coreai_program.optimize()
```
with the rationale: *"Externalizing a submodule **preserves its operation boundary** during conversion... When you mark a well-known building block — such as attention, RoPE, or RMSNorm — as a **composite op**, the compiler recognizes that operation and can apply an optimized implementation tailored to it, producing a faster model."*
And the trap: *"`coreai_torch.composite_ops` ships convenience wrappers like `RMSNorm`... but **`target_class` in the `ExternalizeSpec` must still be `RMSNormImpl`** (the inner module the converter recognizes as the `rms_norm` composite op)."*
Plus: *"Passing a bare module class to `externalize_modules` instead of an `ExternalizeSpec` performs **simple externalization**: the submodule is extracted into its own standalone graph **with no composite-op metadata and no optimization benefit. This is experimental** — prefer composite-op externalization."*

### Custom Metal kernels — pipeline change

**[TRANSCRIPT] 325:178–184:**
> *"Here's what changes with custom Metal kernels. **I am adding a second input to `coreai-torch`. My kernel's source code written in the Metal Shading Language, or MSL.** The converter takes both my PyTorch model and my custom kernel, and **bundles them together into a single asset. The MSL is embedded right inside. It ships with the model.**"*

**[TRANSCRIPT] 325:186–204 — the SiLU example:**
> *"First, I define a **PyTorch reference** for our example. A standard **Sigmoid Linear Unit, or SiLU**. It's a common activation function used in generative transformer models. **This is what `torch.export` sees during tracing.**"*
> *"Below that, I implement the actual Metal kernel in MSL. This is a **simple element-wise kernel, one thread per element**, that computes the **fused activation** directly on the GPU."*
> *"With just these two pieces, I can now register a Core AI **`TorchMetalKernel`**, give it **the Metal source, the PyTorch reference and the input and output names.** In this case, the input and output names are **`"x"` and `"y"`** respectively, and **you can see those names being used in the MSL kernel above**."*
> *"So you write the Metal. You write the PyTorch reference. **And Core AI binds them together.**"*
> *"Using it in a model, I will just **call it like any other Python function. Pass the input, specify the thread grid and I am done.**"*
> *"**One thing to note, is that I pass in the `result_shapes` to every instantiation of the custom kernel** in the PyTorch source. **This allows Core AI to bake in the computation of the output shapes of the kernel from the input shapes, if your model has dynamic shaped inputs.**"*
> *"When I convert with `TorchConverter`, **I register my custom kernels with the converter, then add the exported program as before.** The Metal source gets embedded directly in the asset — **a single artifact. The kernel travels with the model.**"*

**[RECONSTRUCTED — SiLU kernel, using verified `TorchMetalKernel` API and the stated `x`/`y` names]:**
```python
import torch
from coreai_torch import TorchMetalKernel, MetalParameter, TorchConverter, get_decomp_table


def torch_silu(x: torch.Tensor) -> torch.Tensor:
    """PyTorch reference — this is what torch.export sees during tracing."""
    return x * torch.sigmoid(x)


silu_kernel = TorchMetalKernel(
    "silu",
    input_names=["x"],
    result_names=["y"],
    src="y[id] = x[id] / (1.0f + exp(-x[id]));",   # one thread per element
    torch_defn=torch_silu,
    metal_params=[MetalParameter("id", "uint", "thread_position_in_grid")],
)


class Model(torch.nn.Module):
    def forward(self, x):
        return silu_kernel(
            x,
            threads_per_grid=(x.shape[0], 1, 1),
            threads_per_thread_group=(1, 1, 1),
            result_shapes=[list(x.shape)],          # <- required at EVERY call site
        )


converter = TorchConverter()
converter.register_custom_kernels([silu_kernel])    # BEFORE add_exported_program
ep = torch.export.export(Model().eval(), args=(torch.randn(1024),))
ep = ep.run_decompositions(get_decomp_table())
program = converter.add_exported_program(ep, input_names=["x"], output_names=["y"]).to_coreai()
program.optimize()
```

**[VERIFIED: repos/apple__coreai-torch/docs/api/TorchMetalKernel.md]** — the real constructor and call signature:
```python
from coreai_torch import TorchMetalKernel, MetalParameter   # MetalParameter re-exported from coreai.authoring

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

def __call__(
    self,
    *args,
    threads_per_grid: tuple[int, int, int],
    threads_per_thread_group: tuple[int, int, int],
    result_shapes: list[list[int]],
)
```

| Param | Notes (verbatim) |
|---|---|
| `name` | *"Becomes part of the generated kernel's name in the converted model."* |
| `input_names` | *"Names matching the input variables in the Metal source. **Must match the parameter count of `torch_defn`**."* |
| `result_names` | *"Names matching the output variables in the Metal source."* |
| `src` | *"**Body** of the Metal `[[kernel]]` function. The signature, buffer bindings, and `#include <metal_stdlib>` are **generated automatically** from `input_names`, `result_names`, and `metal_params`."* |
| `torch_defn` | *"Reference PyTorch implementation used for **shape inference during `torch.export`**."* |
| `metal_params` | *"Metal thread attributes to bind in the generated kernel signature (e.g. `MetalParameter("id", "uint", "thread_position_in_grid")`)."* |
| `helper_src` | *"Additional Metal source **pasted before the kernel definition** (helper functions, type aliases, etc.)."* ← this is where a big FlashAttention body's helpers/typedefs go |
| `template_dtypes` | *"Map from input name to a placeholder string in `src`. Each placeholder is replaced with the corresponding **Metal dtype at compile time**, allowing one kernel to serve multiple dtypes."* |

**Constraints on `torch_defn` — enforced at construction time:**
> 1. *"**Inputs** — every parameter must be annotated as `torch.Tensor`, `int`, `float`, or `bool`. The parameter count must match `len(input_names)`."*
> 2. *"**Return** — the return annotation must be `torch.Tensor`, `list[torch.Tensor]`, or `tuple[torch.Tensor, ...]` (with a **concrete** number of tuple members)."*
>
> *"Violations raise **`TypeError`** (input/return annotations) or **`ValueError`** (parameter count mismatch) at construction time."*

**Ordering constraint (verbatim):** *"`TorchMetalKernel` instances must be registered with the converter via `register_custom_kernels()` **before** `add_exported_program()`."*

**Dtype templating [VERIFIED]** — one kernel, many dtypes:
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
    template_dtypes={"A": "TYPE"},
)
```
Two API details visible only here: inside `src`, tensors expose **`.get_extent(i)`** and support **multi-index subscripting `A[k, gid.y]`** — they are Metal *tensor* objects, not raw pointers. Substitution: *"Every occurrence of `"TYPE"` in `src` is replaced with the Metal type matching the dtype of input `A` (e.g. `half`, `float`, `bfloat`)."*

**Multiple outputs [VERIFIED]:**
```python
def torch_sincos(x: torch.Tensor) -> list[torch.Tensor]:
    return [torch.sin(x), torch.cos(x)]

sincos = TorchMetalKernel(
    "sincos", input_names=["x"], result_names=["out_sin", "out_cos"],
    src="out_sin[id] = sin(x[id]); out_cos[id] = cos(x[id]);",
    torch_defn=torch_sincos,
    metal_params=[MetalParameter("id", "uint", "thread_position_in_grid")],
)
results = sincos(x, threads_per_grid=(x.shape[0], 1, 1),
                 threads_per_thread_group=(1, 1, 1),
                 result_shapes=[list(x.shape), list(x.shape)])
```

**Experimental-API warnings [VERIFIED, two separate ones]:**
> *"Authoring Metal kernels uses APIs from `coreai-core` (such as `coreai.authoring`). **These APIs are experimental and subject to change in future releases.**"*
> On `register_torch_lowering`: *"Lowering functions are written against authoring APIs from `coreai-core` (such as `coreai._compiler.dialects`). **The leading underscore on `_compiler` marks this as private upstream API — it may move or change without notice** across `coreai-core` releases."*

**Also: custom op lowering** (the "register custom lowerings" bullet from 325:34). **[VERIFIED: docs/api/TorchConverter.md:196–264]**
```python
@converter.register_torch_lowering("my_lib::scaled_add.default")
def lower_scaled_add(values_map, node, loc):
    x, y = get_operands(values_map, node, [0, 1], loc)
    scale = node.args[2]  # plain Python float
    scale_val = coreai.constant(scale, dtype=x.type.element_type)
    scaled_y = coreai.broadcasting_mul(y, scale_val, loc=loc)
    return coreai.broadcasting_add(x, scaled_y, loc=loc)
```
Callback signature:
```python
def lowering_func(values_map: dict[str, Value], node: torch.fx.Node, loc: Location) -> Value | list[Value]
```
Raises:
- `ValueError` if `qualified_name` is not `"namespace::op_name"` form
- `ValueError` if the namespace is **reserved**: `aten`, `higher_order`, `coreai`, `coreaix`
- `ValueError` if a lowering already exists and `allow_override is False`

## 1.12 Model **re-authoring** (the iOS story)

**[TRANSCRIPT] 325:206–222** — the key conceptual section:
> *"So far, I showed how you can take multiple operations in the graph and fuse them into one. But for **more advanced optimizations, especially for iOS**, you need to go further and **rewrite the entire model with a specific target in mind. We refer to this process, as model re-authoring.**"*
> *"Re-authoring typically involves replacing many aspects of this computational graph. This may imply using **different operations, novel tensor layouts, and even modifying the interfaces of the model**. Essentially, this is a **completely different implementation of the source code**."*

Three named mechanisms:
1. **Predefined patterns that tell Core AI about a specific concept** (325:213–215): *"using predefined patterns in the PyTorch code that tell Core AI about a specific concept. This allows the framework to **map these semantics to an optimized implementation at runtime**. An example of this, is **in-place updates of the Key-Value cache** commonly used in Large Language models."* ← ties directly to the `state_names` / mutable-buffer machinery in §1.5.
2. **iOS-targeting layout rules** (325:216–217): *"especially when targeting iOS, is the usage of **static tensor shapes, channels-first tensor layouts and convolutional op patterns**. These enable Core AI to leverage **powerful underlying primitives** and meet your on-device constraints."*
3. **Rigorous testing** (325:218–220): *"When you engineer a novel PyTorch implementation in this way, **it's crucial that you employ rigorous testing both at the module level and at the model level**. This ensures that individual building blocks, as well as the entire model work as intended. This testing can take the shape of **unit tests or integration tests**."*

> 325:221–222 — *"To get you started, the Core AI models repository includes **multiple examples of such reusable components and best practices across different models**. Core AI skills also enable your coding assistant to **write PyTorch code optimized for Apple Silicon from day one**."*

### The three-function split

**[TRANSCRIPT] 325:224–230:**
> *"Instead of converting the model as-is, I can **author a new PyTorch implementation that's hand-crafted for my goals**. The biggest change I make is to have **three separate functions in the Core AI Model instead of one. `coreai-torch` has APIs that lets you do this.** `image_encode` handles the image, `text_encode` processes the prompt, and `detect` wraps the final post-processing to generate the output."*
> *"**Splitting the work this way allows me to run each bit at a different cadence.** For example, I may want to **process a single prompt once and use it across a variety of images**. It also gives each function a **clean interface**, and lets me **compress and author each one independently**."*

**[VERIFIED — this is real, shipping code]** `repos/apple__coreai-models/python/src/coreai_models/segmentation/pipeline.py:265–286`:
```python
logger.info("Converting to Core AI...")
converter = coreai_torch.TorchConverter()
converter.add_exported_program(
    img_program,
    entrypoint_name="image_encode",
    input_names=["pixel_values"],
    output_names=["backbone_features"],
)
converter.add_exported_program(
    txt_program,
    entrypoint_name="text_encode",
    input_names=["input_ids"],
    output_names=["text_features"],
)
converter.add_exported_program(
    det_program,
    entrypoint_name="detect",
    input_names=["backbone_features", "text_features"],
    output_names=["pred_masks", "pred_boxes", "pred_logits", "presence_logits", "semantic_seg"],
)
coreai_program = converter.to_coreai()
coreai_program.optimize()

metadata = build_aimodel_metadata(config.hf_model_id)
coreai_program.save_asset(asset_path, metadata)
```
→ *"**When saved, I get one model asset with three callable functions inside.**"* (325:256). Note `save_asset(path, metadata)` takes an optional **second positional metadata argument** — not shown in the talk or the quickstart.

### Re-authored attention block

**[TRANSCRIPT] 325:232–237:**
> *"Here's the attention block from the Image Encoder transformer, **rewritten for power-efficient execution on iOS**. Instead of standard **Linear layers, I use convolutional projections**. This is one of the patterns that lets Core AI **leverage native hardware primitives on the right compute unit**. The text encoder gets a similar treatment. **The smaller decoder stays mostly unchanged. It's a small fraction of the compute, so the payoff from re-authoring it is minimal.**"*

**[VERIFIED]** `repos/apple__coreai-models/python/src/coreai_models/models/ios/sam3/image_encoder.py` — module docstring:
```
"""Re-authored SAM3 image encoder backbone in BC1S layout.

32 transformer layers: 28 window attention (24x24 windows) + 4 global
attention at indices [7, 15, 23, 31]. All intermediates in BC1S
(B, C, 1, S) format. Linear projections replaced with Conv2d(1x1).
GELU approximated with sigmoid.

HF reference: ``Sam3ViTModel`` in ``transformers/models/sam3/modeling_sam3.py``.
"""
```
and the attention block itself:
```python
class ImageEncoderAttention(nn.Module):
    """Self-attention with 2D axial RoPE in BC1S layout."""

    def __init__(self, hidden_size=1024, num_heads=16, head_dim=64,
                 grid_h=24, grid_w=24, rope_theta=10000.0, rope_scale=1.0):
        super().__init__()
        self.q_proj = nn.Conv2d(hidden_size, hidden_size, 1, bias=True)
        self.k_proj = nn.Conv2d(hidden_size, hidden_size, 1, bias=True)
        self.v_proj = nn.Conv2d(hidden_size, hidden_size, 1, bias=True)
        self.o_proj = nn.Conv2d(hidden_size, hidden_size, 1, bias=True)
        self.sdpa = BidirectionalSDPA(num_heads=num_heads, head_dim=head_dim)
        self.rope = AxialRoPE2DReauthored(head_dim=head_dim, grid_h=grid_h, grid_w=grid_w,
                                          num_heads=num_heads, rope_theta=rope_theta, scale=rope_scale)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q = self.q_proj(x); k = self.k_proj(x); v = self.v_proj(x)
        q_rotated = self.rope(q); k_rotated = self.rope(k)
        attn_out = self.sdpa(q_rotated, k_rotated, v)
        return self.o_proj(attn_out)
```
plus the Linear→Conv2d weight surgery helper:
```python
def _linear_to_conv2d(linear: nn.Linear) -> nn.Conv2d:
    """Convert ``nn.Linear`` to ``nn.Conv2d(1x1)`` for BC1S layout."""
    in_features, out_features = linear.in_features, linear.out_features
    has_bias = linear.bias is not None
    conv = nn.Conv2d(in_features, out_features, 1, bias=has_bias)
    conv.weight.data = linear.weight.data.reshape(out_features, in_features, 1, 1)
    if has_bias:
        conv.bias.data = linear.bias.data
    return conv
```
**"BC1S"** = `(B, C, 1, S)` channels-first — this is the concrete name for the transcript's "channels-first tensor layouts". Constants confirmed: `_HIDDEN_SIZE=1024`, `_NUM_HEADS=16`, `_HEAD_DIM=64`, `_MLP_DIM=4736`, `_WINDOW_SIZE=24`, `_GLOBAL_ATTN_INDICES=[7,15,23,31]`, `_PATCH_SIZE=14`, `_LAYER_NORM_EPS=1e-6`, `_ROPE_THETA=10000.0`.

The `coreai-skills` `gpu_rules.md` reference confirms the *contrast* for GPU targets: *"Standard PyTorch shapes throughout — **no BC1S conversion needed**. Use `nn.Linear` for all projections."* and *"GPU uses **fused** scaled dot-product attention — a single call processes all heads in parallel... **This is the opposite of Neural Engine, where each head must be computed individually.**"* → **BC1S + Conv2d + per-head attention is a Neural-Engine/iOS pattern, not a universal one.**

### Palettization of the two encoders

**[TRANSCRIPT] 325:241–248:**
> *"For compression, I apply **4-bit palettization with per-channel scales** to the two encoders. **There is a preset available for this, but I use the lower-level representation here to showcase the APIs.** This **lookup-table-based compression, is well-suited for power efficiency on iOS**."*
> *"As before, I **construct a `KMeansPalettizer` similar to the `Quantizer`**, and pass it the **model and config**. Then, I **prepare and finalize**."*
> *"Also note, that I **changed the input image size from 1008 pixels to 336** to run on an iPhone."*
> *"**The detector stays uncompressed. I know that it's sensitive to compression from our previous exercise.**"*

**[VERIFIED] the "preset available for this"** — `KMeansPalettizerConfig.presets` (`src/coreai_opt/palettization/config/_presets/kmeans_palettizer_config.py`):

| Preset | Spec |
|---|---|
| `w4(*, axis=0, group_size=16)` | `PalettizationSpec(n_bits=4, granularity=PerGroupedChannelGranularity(axis=axis, group_size=group_size))` |
| `w6(*, axis=0, group_size=16)` | `n_bits=6`, per-grouped-channel |
| `w8()` | `n_bits=8`, `PerTensorGranularity()` |

**[VERIFIED] the "lower-level representation"** — exactly what `pipeline.py:208–245` does:
```python
from coreai_opt import ExportBackend
from coreai_opt.palettization import (
    KMeansPalettizer, KMeansPalettizerConfig,
    ModuleKMeansPalettizerConfig, PalettizationSpec,
)
from coreai_opt.palettization.spec import PerGroupedChannelGranularity

def _make_pal_config(n_bits: int, group_size: int) -> KMeansPalettizerConfig:
    spec = PalettizationSpec(
        n_bits=n_bits,
        granularity=PerGroupedChannelGranularity(axis=0, group_size=group_size),
    )
    return KMeansPalettizerConfig(
        global_config=ModuleKMeansPalettizerConfig(op_state_spec={"weight": spec}),
    )

img_pal_config = _make_pal_config(config.image_n_bits, config.image_group_size)   # 4, 32
txt_pal_config = _make_pal_config(config.text_n_bits,  config.text_group_size)    # 6, 8

img_enc = ImageEncoderModule(sam3_lite.image_encoder); img_enc.eval()
img_palettizer = KMeansPalettizer(img_enc, img_pal_config)
img_enc = img_palettizer.prepare(example_inputs=(pixel_ref,))
img_enc = img_palettizer.finalize(backend=ExportBackend.CoreAI)
```

**`PalettizationSpec` full field list [VERIFIED: src/coreai_opt/palettization/spec/spec.py:44–90]:**
```python
n_bits: Literal[1, 2, 3, 4, 6, 8] = 4
lut_qspec: QuantizationSpec | None = None
granularity: PalettizationGranularity = PerTensorGranularity()
cluster_dim: PositiveInt = 1
enable_per_channel_scale: bool = False
```
Verbatim semantics:
- `n_bits` — *"Number of bits used for palette indices. Determines palette size (2^n_bits entries). **Must be one of {1, 2, 3, 4, 6, 8}**."* (note: **no 5 or 7**)
- `lut_qspec` — *"Quantization specification for the lookup table values... only `torch.int8`, `torch.uint8`, `torch.float8_e4m3fn`, and `torch.float8_e5m2` dtypes are supported, and **granularity must be `PerTensorGranularity`. FP8 dtypes require symmetric quantization.**"* Also `qformulation=MINVAL` is rejected: *"Use `lut_qspec.qformulation=ZP` instead."*
- `cluster_dim` — *"The dimension of centroids for each lookup table... When `cluster_dim > 1`, it indicates **2-D clustering**, and each `cluster_dim` length of weight vectors along the output channel are palettized using the same 2-D centroid."*
- `enable_per_channel_scale` — *"When set to True, **weights are normalized along the output channels using per-channel scales before being palettized**."*

Granularity classes: `PerTensorGranularity` (`axis: Literal[None] = None`) and `PerGroupedChannelGranularity` (`axis: int | None` constrained `ge=0, le=1`; `group_size: int`). Validation: *"Tensor size ... along axis ... is not divisible by `group_size` ... the tensor shape along the specified axis must be divisible by `group_size`."*

> ⚠️ **MAJOR CROSS-CHECK FINDING — "per-channel scales".** The transcript says *"4-bit palettization **with per-channel scales**"*. The shipping recipe **deliberately leaves `enable_per_channel_scale=False`** and gets its "per-channel-ness" from `PerGroupedChannelGranularity` instead. The reason is a concrete hardware limit, verbatim from `SegmentationExportConfig`'s docstring (`pipeline.py:136–142`):
> > *"Both encoders **deliberately disable per-channel scale**: `enable_per_channel_scale=True` lowers to **`mps.dequantize_lut` ops with rank-6 LUTs, which ANE rejects (max tensor rank 5)**, forcing the runtime to **fall back to GPU**. Keeping it off keeps the asset **ANE-compatible** at the cost of a small PyTorch-side quality regression."*
>
> This is one of the most valuable footguns in the whole corpus: **ANE max tensor rank is 5**, and per-channel scale on top of grouped-channel palettization produces rank-6 LUTs. Either the talk used the phrase loosely, or the shipped recipe changed after the talk was recorded. Flag both readings in any guide.

**`KMeansPalettizer` API [VERIFIED: src/coreai_opt/palettization/kmeans/palettizer.py]:**
```python
KMeansPalettizer(model: torch.nn.Module, config: KMeansPalettizerConfig | None = None)

def prepare(
    self,
    example_inputs: tuple[torch.Tensor],
    sensitivity_path: str | None = None,
    num_workers: int = 1,
) -> torch.nn.Module

@contextmanager
def calibration_mode(self, model=None, *, loss_fn: Callable, sensitivity_path: str | None = None)

def finalize(
    self,
    model: torch.nn.Module | None = None,
    backend: ExportBackend = ExportBackend.CoreAI,
    *,
    mmap_dir: str | PathLike[str] | None = None,
) -> torch.nn.Module
```
Verbatim gotchas:
- `prepare` returns *"the prepared `nn.Module` with fake palettization modules inserted. **This is a data-free PTP compressed model.**"* Raises `RuntimeError` if already prepared, `ValueError` if `num_workers < 1`.
- `num_workers` — *"`1` runs clustering sequentially. Values greater than `1` use `torch.multiprocessing` to parallelize clustering across layers. **It is recommended to use more than one worker process to parallelize the clustering, especially when multiple CPUs are available.**"* ← perf tip absent from the talk; SAM3 clustering is slow.
- `sensitivity_path` — enables **weighted k-means** (SqueezeLLM-style): *"sensitivity values indicate the importance of each weight element... **k-means clustering will place centroids closer to more sensitive weight values**"*, computed via `calibration_mode(loss_fn=...)` which *"uses the loss function to compute gradients via backpropagation, and the squared gradients are collected as sensitivity values"*. Reference: *"SqueezeLLM: Dense-and-Sparse Quantization" (arxiv 2306.07629)*.
- `finalize` — *"**Only call `finalize` when exporting to a target backend.** For torch-based evaluation, **use the model returned by `prepare()` directly** rather than calling `finalize`."*
- `finalize` backends: `ExportBackend.CoreAI` (default) and `ExportBackend.CoreML`; `mmap_dir` is **CoreAI-only** (`ValueError` otherwise) and *"the files in `mmap_dir` must remain in place for the lifetime of the returned model; removing them invalidates the mmap-backed weights."*
- **Destructive side effect:** *"When `backend=ExportBackend.CoreAI`, finalize **frees the original dense weights in place**: on each parametrized weight, `parametrizations[...].original` is replaced with a zero-size placeholder so its storage can be released."*
- Silent skips: if a tensor is incompatible with the granularity or `cluster_dim`, `_FakePalettizeImplBase.forward` logs `"Tensor incompatible with granularity: ... Skipping palettization."` and **disables palettization for that layer** rather than failing. Watch your logs.

### Export + convert all three, and the payoff

**[TRANSCRIPT] 325:249–262:**
> *"I then run each model through `torch.export`. **All of them get cast to half-precision.**"*
> *"And here's where it comes together. **A single `TorchConverter`, three exported programs, each with its own entrypoint name.** First, `image_encode`. Then, `text_encode`. And finally, `detect`."*
> *"Now, lets load and run the pre-computed asset. First, I see **all the flowers segmented as expected**."*
> *"And here's the payoff of the three-function split. **I swapped the prompt to butterfly and only re-ran the text encoder and the detector.** As a result, the **second inference is 76% faster, even after warmup. This shows the benefit of re-authoring.**"*

**[VERIFIED]** the fp16 cast on all three (`pipeline.py:250–263`):
```python
img_program = torch.export.export(img_enc, args=(pixel_ref,))
img_program = img_program.run_decompositions(coreai_torch.get_decomp_table())
img_program = cast_to_16_bit_precision(img_program)
# ...same for txt_program and det_program
```
Reference tensors (which reveal the BC1S interfaces):
```python
pixel_ref     = torch.randn(1, 3, image_size, image_size)                       # 336
ids_ref       = torch.randint(0, 49408, (1, config.max_text_seq_len), dtype=torch.int32)  # 32, CLIP vocab
backbone_ref  = torch.randn(1, 1024, 1, grid * grid)                            # grid = 336 // 14 = 24 → 576
text_feat_ref = torch.randn(1, 256, 1, config.max_text_seq_len)
```

**CLI of the shipped reproduction** (`models/sam3/README.md`) — a real, runnable command set:
```sh
uv run models/sam3/export.py                       # lite (iOS) export, the WWDC26 325 demo
uv run models/sam3/export.py --help
uv run models/sam3/export.py --full                # plain HF Sam3Model, float32, 1008x1008
uv run models/sam3/export.py --full --dtype float16
```
| Flag | Description | Default |
|---|---|---|
| `--full` | Export plain HF `Sam3Model` (no iOS targeting) | — |
| `--output-dir` | Output directory for the bundle | `<repo-root>/exports/` |
| `--output-name` | Custom bundle directory name | derived |
| `--image-size` | Input resolution (336 lite / 1008 full) | `336` / `1008` |
| `--max-text-seq-len` | (lite) Static text sequence length | `32` |
| `--n-bits` | (lite) Uniform palettization bit-width override applied to **BOTH** encoders | asymmetric: image w4, text w6 |
| `--group-size` | (lite) Uniform palettization group-size override applied to **BOTH** encoders | asymmetric: image gs32, text gs8 |
| `--dtype` | (`--full`) `float16` or `float32` | `float32` |
| `--overwrite` | Overwrite existing bundle | — |
| `--dry-run` | Print resolved config and exit | — |

> *"`image-size=336` is **the resolution we recommend for iOS deployment**."*
> Bundle layout: `<name>.aimodel` + `tokenizer/` + `metadata.json` (**segmenter bundle, schema 0.2**).
> Gated model: SAM3 requires HF auth (`hf auth login --token ...`); `transformers>=5.5.4,<5.10.1` and `huggingface-hub>=1.5.0,<2.0` — the export script is a **PEP 723 uv inline script** with `override-dependencies` because *"the workspace pins `transformers<5.0` but SAM3 needs `Sam3Model` from `>=5.5.4`."*

## 1.13 Session 325 closing recommendations (325:263–267, verbatim)

> *"So, here's what you can do today. **Convert** your PyTorch models using Core AI's Python libraries. **Optimize** them with `coreai-opt`, and **use the debugger when you need to understand what's happening inside**. **Build on top of the examples in `coreai-models`**. And **plug in Core AI Skills into your favorite AI agent** to leverage the new framework like an expert."*

---

# PART 2 — Session 330: Metal tensors and TensorOps

## 2.1 Where TensorOps sits in the stack (330:4–14)

**[TRANSCRIPT]**
> *"Apple platforms provide **first-class support for running ML models at every layer of the software stack**. High-level frameworks like **Core AI and MLX** make it easy to deploy your models with minimal code, while lower-level APIs like **Metal Performance Shaders** provide access to high-performance Metal kernels. **These layers all build on the low-level acceleration provided by Metal Performance Primitives and the TensorOps library.**"*

**When to drop to the Metal level — three reasons, verbatim (330:7–10):**
1. *"ML research moves quickly, so you might want to implement **custom operations which can plug into a higher level frameworks such as Core AI**."*
2. *"You may also need to write Metal kernels **if you're contributing to an ML framework such as MLX or llama.cpp**."*
3. *"or if you're **working on a Metal-based application**."*

**What TensorOps is (330:11–14):**
> *"The easiest way to get started is using the TensorOps library. **TensorOps is a Metal Shading Language API which accelerates tensor operations on the GPU, including matrix multiplication and convolution.** It **automatically uses any available hardware acceleration across all Apple Silicon GPU generations, so you don't need to worry about the differences between hardware generations.** In particular, it takes full advantage of the **neural accelerator in the M5 chip family**."*

**The M5 neural accelerator (330:15–16):**
> *"The neural accelerator is a **new hardware block in M5, located directly in each shader core**. It **sits alongside the other GPU pipelines** and is designed to accelerate **dense compute-bound work such as the prefill stage of an LLM**."*

**[VERIFIED — the framework is real and vendored in the SDK]:**
`/Applications/Xcode.app/.../MacOSX.sdk/System/Library/Frameworks/MetalPerformancePrimitives.framework/Versions/A/Headers/`
```
MetalPerformancePrimitives.h        # umbrella: includes MPPTensorOpsConvolution2d.h + MPPTensorOpsMatMul2d.h
MPPTensorOpsConvolution2d.h  (177 lines)
MPPTensorOpsMatMul2d.h       (642 lines)
__impl/ MPPTensorOpsAvailability.h  MPPTensorOpsBase.h  MPPTensorOpsConvolution2dImpl.h (4914)
        MPPTensorOpsMatMul2dImpl.h (8963)  MPPTensorOpsTraits.h  MPPTensorOpsTypes.h  MPPTensorOpsUtility.h
```
MSL include line (as used by MLX):
```cpp
#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>
```
Namespace: **`mpp::tensor_ops`**. Guarded by `#if defined(__METAL_VERSION__) && defined(__HAVE_TENSOR__)` and `#pragma METAL internals : enable`.

**Version gate found in the SDK [VERIFIED: `__impl/MPPTensorOpsAvailability.h`]:**
```c
#define __TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2 ((__ENVIRONMENT_OS_VERSION_MIN_REQUIRED__) >= 260200)
```
→ a feature tier gated on **deployment target 26.2**. Matches the transcript's *"We added support for 4- and 8-bit integer types in an update to macOS and iOS 26"* (330:28).

> **Prerequisite the talk assumes.** 330:17 — *"You can check out the related sessions to learn the **basics** of getting started with TensorOps."*, 330:48 — *"We covered the basics of how to write a high performance matrix multiplication kernel with TensorOps in **the M5 machine learning talk**."* This session is explicitly a **level-2** talk.

## 2.2 Working with quantized data

**Motivation, verbatim (330:21–26):**
> *"state-of-the-art machine learning models are getting larger. **The inference stage is typically memory bandwidth bound**, so compressing the weights becomes necessary **both to better fit models into memory and to save memory bandwidth**."*
> *"The standard approach for compressing weights is quantization... For example, 16-bit half-precision weights could be compressed down to just 4-bits. **These quantized weights are paired with scale factors, which let us scale the quantized values back into the original range when it's time to compute.**"*

**Data type timeline (330:27–29) — a precise version matrix:**

| Types | Availability (as stated) |
|---|---|
| 16- and 32-bit floating point | baseline |
| **4- and 8-bit integer** | *"added ... in an **update to macOS and iOS 26**"* |
| **4- and 8-bit floating point**, **2-bit integer** | *"we're **extending support to even more data types in macOS and iOS 27**"* |

**[VERIFIED against the Xcode 26.6 SDK — partial confirmation + a discrepancy]**

`MTLTensor.h` (macOS 26 SDK) enumerates:
```objc
typedef NS_ENUM(NSInteger, MTLTensorDataType) {
    MTLTensorDataTypeNone     = MTLDataTypeNone,
    MTLTensorDataTypeFloat32  = MTLDataTypeFloat,
    MTLTensorDataTypeFloat16  = MTLDataTypeHalf,
    MTLTensorDataTypeBFloat16 = MTLDataTypeBFloat,
    MTLTensorDataTypeInt8     = MTLDataTypeChar,
    MTLTensorDataTypeUInt8    = MTLDataTypeUChar,
    MTLTensorDataTypeInt16    = MTLDataTypeShort,
    MTLTensorDataTypeUInt16   = MTLDataTypeUShort,
    MTLTensorDataTypeInt32    = MTLDataTypeInt,
    MTLTensorDataTypeUInt32   = MTLDataTypeUInt,
    MTLTensorDataTypeInt4  API_AVAILABLE(macos(26.4), ios(26.4)) = 143,
    MTLTensorDataTypeUInt4 API_AVAILABLE(macos(26.4), ios(26.4)) = 144,
} API_AVAILABLE(macos(26.0), ios(26.0));
```
→ **Int4/UInt4 are gated `macos(26.4), ios(26.4)`**, which pins down "an update to macOS and iOS 26" to **26.4**. FP4/FP8/Int2 tensor data types are **absent from the 26.6 SDK** — consistent with them being a 27 addition. **Do not assume names for the 27 enum cases; they are UNVERIFIED.**

The MSL-side type enum in the 26.6 SDK (`__impl/MPPTensorOpsTypes.h`) likewise stops at int4/uint4:
```cpp
enum __tensor_ops_datatype {
  __tensor_ops_datatype_invalid = 0,
  __tensor_ops_datatype_float_bit  = 0x10000000,
  __tensor_ops_datatype_float32 = __tensor_ops_datatype_float_bit | 32,
  __tensor_ops_datatype_float16 = __tensor_ops_datatype_float_bit | 16,
  __tensor_ops_datatype_signed_bit = 0x20000000,
  __tensor_ops_datatype_int4  = __tensor_ops_datatype_signed_bit | 4,
  __tensor_ops_datatype_int8  = __tensor_ops_datatype_signed_bit | 8,
  __tensor_ops_datatype_int16 = __tensor_ops_datatype_signed_bit | 16,
  __tensor_ops_datatype_int32 = __tensor_ops_datatype_signed_bit | 32,
  __tensor_ops_datatype_uint4 = 4, __tensor_ops_datatype_uint8 = 8,
  __tensor_ops_datatype_uint16 = 16, __tensor_ops_datatype_uint32 = 32,
  __tensor_ops_datatype_alternate_encoding_bit = 0x80000000,
  __tensor_ops_datatype_bfloat16 = __tensor_ops_datatype_alternate_encoding_bit | __tensor_ops_datatype_float16,
};
```
MSL element types accepted: `float`, `half`, `bfloat`, `metal::int4b_format`, `metal::uint4b_format` (behind `__HAVE_INT4B_FORMAT_TYPE__`), `int8_t`, `uint8_t`, `int32_t`, `uint32_t`.

**Supported matmul dtype combinations [VERIFIED: MPPTensorOpsMatMul2d.h:13–61]** — the full Left × Right → Destination table:
```
half     half           half        half     half           float
half     int8_t         half        half     float          float
half     uint8_t        half        half     int8_t         float
int8_t   half           half        half     uint8_t        float
uint8_t  half           half        float    half           float
float    float          float       float    int8_t         float
float    uint8_t        float       int8_t   half           float
uint8_t  half           float       int8_t   float          float
uint8_t  float          float       int8_t   int8_t         int32_t
uint8_t  uint8_t        int32_t     bfloat   bfloat         bfloat
bfloat   bfloat         float       bfloat   float          float
bfloat   int8_t         bfloat      bfloat   int8_t         float
float    bfloat         float       int8_t   bfloat         bfloat
int8_t   bfloat         float       bfloat   half           bfloat
bfloat   half           half        bfloat   half           float
half     bfloat         bfloat      half     bfloat         half
half     bfloat         float       bfloat   uint8_t        bfloat
bfloat   uint8_t        float       uint8_t  bfloat         bfloat
uint8_t  bfloat         float
half     int4b_format   half        half     int4b_format   float
half     uint4b_format  half        half     uint4b_format  float
int8_t   int4b_format   int32_t     uint8_t  uint4b_format  int32_t
bfloat   int4b_format   bfloat      bfloat   uint4b_format  bfloat
bfloat   int4b_format   float       bfloat   uint4b_format  float
```
> **Observation for a guide:** 4-bit is only ever a **right** (weight) operand. There is no `int4 × int4` combination.

### Creating a quantized tensor on the host

**[TRANSCRIPT] 330:31–33:**
> *"Creating a tensor with a quantized data type is **very similar to creating a regular tensor**. You **fill in your descriptor's properties like any other tensor, but simply specify a quantized `dataType`**. Then create the tensor by calling **`newTensorWithDescriptor`** on your Metal device."*

**[VERIFIED]** `newTensorWithDescriptor:` exists on both `MTLDevice` (`MTLDevice.h:1344`) and `MTLBuffer` (`MTLBuffer.h:83`), each returning `nullable id<MTLTensor>`.

**[RECONSTRUCTED — Swift, matching the 26.6 `MTLTensorDescriptor` surface]:**
```swift
let desc = MTLTensorDescriptor()
desc.dimensions = MTLTensorExtents(rank: 2, values: [K, N])!
desc.dataType   = .int4                     // the "quantized dataType"
desc.usage      = [.compute, .machineLearning]
let weights = device.makeTensor(descriptor: desc)   // newTensorWithDescriptor:
```

**[VERIFIED: MTLTensor.h] `MTLTensorDescriptor` properties (macOS/iOS 26.0+):**
`dimensions: MTLTensorExtents` (default rank-1 size-1) · `strides: MTLTensorExtents?` (*"Only set this property when creating tensors from a buffer"*) · `dataType: MTLTensorDataType` (default `Float32`) · `usage: MTLTensorUsage` (default `Render | Compute`) · `resourceOptions` · `cpuCacheMode` · `storageMode` (default `.shared`) · `hazardTrackingMode`.

**`MTLTensorUsage`:** `.compute` (1<<0), `.render` (1<<1), `.machineLearning` (1<<2, for `MTL4MachineLearningCommandEncoder`).
**Errors:** `MTLTensorDomain`, `MTLTensorError.{None, InternalError, InvalidDescriptor}`.
**Max rank:** `#define MTL_TENSOR_MAX_RANK 16`.

> **⚠️ THE ALIGNMENT GOTCHA — 330:79 verbatim:** *"Note that **these new data types have additional alignment requirements compared to the larger data types**, so **be sure to check the Metal documentation for details**."*
> **[VERIFIED — here is the actual rule, from `MTLTensor.h:113–116` `strides` docs]:**
> - *"The first element of `strides` is one."*
> - *"If `usage` contains `MTLTensorUsageMachineLearning`, **the second element of `strides` is aligned to 64 bytes**, and for any `i` larger than one, `strides[i] == strides[i-1] * dimensions[i-1]`."*
> - *"**If `dataType` is a sub-byte `MTLTensorDataType`, for any `i >= 1`, `strides[i]` is aligned to 128 bytes.** This is not a requirement for non-sub-byte data types, but following this convention improves performance."*
>
> **64-byte stride alignment for ML usage; 128-byte stride alignment for sub-byte dtypes.** That is the concrete answer to "check the documentation."

Host-side data movement on `id<MTLTensor>`:
```objc
- (void)replaceSliceOrigin:(MTLTensorExtents *)sliceOrigin
           sliceDimensions:(MTLTensorExtents *)sliceDimensions
                 withBytes:(const void *)bytes
                   strides:(MTLTensorExtents *)strides;
- (void)getBytes:(void *)bytes strides:(MTLTensorExtents *)strides
 fromSliceOrigin:(MTLTensorExtents *)sliceOrigin
 sliceDimensions:(MTLTensorExtents *)sliceDimensions;
```
Read-only props: `gpuResourceID`, `buffer`, `bufferOffset`, `strides`, `dimensions`, `dataType`, `usage`.

### Scale planes — the headline iOS/macOS 27 feature

**[TRANSCRIPT] 330:36–44:**
> *"**In macOS and iOS 27, a single `MTLTensor` object can now represent your scales alongside your tensor's quantized data as an additional scale plane.** This plane supports **the popular FP8 E8M0 block-wise scale factor format**. **Each element of the scale plane applies to a block of elements in the data plane.**"*
> *"Declaring the scale plane is similar to declaring a tensor. **First, create a descriptor object for the scale plane. Then fill in the `dataType` and `blockFactors`. Finally, create an auxiliary plane map to specify that this plane is for scales.** Then simply **attach the auxiliary planes map to your original `tensorDescriptor`. The quantized data, scales, and metadata will all be packed into a single tensor object.**"*

**[RECONSTRUCTED — Swift; type names are the transcript's, NOT verified in any SDK on this machine]:**
```swift
// 1. descriptor for the scale plane
let scaleDesc = MTLTensorScalePlaneDescriptor()          // UNVERIFIED name
scaleDesc.dataType     = .float8E8M0                     // UNVERIFIED case name
scaleDesc.blockFactors = [32, 1]                         // 32x1 block → 32 data elems share 1 scale

// 2. auxiliary plane map declaring this plane is the scales plane
let auxPlanes = MTLTensorAuxiliaryPlaneMap()             // UNVERIFIED name
auxPlanes.scales = scaleDesc                             // UNVERIFIED key

// 3. attach to the data tensor's descriptor
tensorDescriptor.auxiliaryPlanes = auxPlanes             // UNVERIFIED property
let quantizedTensor = device.makeTensor(descriptor: tensorDescriptor)
```
> ⚠️ **UNVERIFIED.** None of `blockFactors`, the auxiliary-plane map type, or the E8M0 `MTLTensorDataType` case appear in the Xcode 26.6 SDK's `MTLTensor.h`. The *concepts* are confirmed by the transcript and by the E8M0 usage elsewhere in the stack (see below), but the exact Objective-C/Swift spellings must be confirmed against an Xcode 27 SDK.

**E8M0 corroboration elsewhere in the corpus [VERIFIED]:**
- `coreai-opt`: `QuantizationSpec(dtype=torch.float4_e2m1fn_x2, granularity=PerBlockGranularity(block_size=32), scale_dtype=torch.float8_e8m0fnu)` — **same 32-element block, same E8M0 scale dtype**, on the Python side. The MX-format story is consistent end-to-end from `coreai-opt` down to Metal.
- MLX: `mlx/backend/metal/kernels/fp8.h:51` defines `struct fp8_e8m0`; `fp_quantized.h:2020` — `using ScaleType = metal::conditional_t<use_mx_scale, fp8_e8m0, fp8_e4m3>;`; `python/src/ops.cpp:4655-4656` documents `mxfp4` and `mxfp8` with **group size 32** and **e8m0** scales; `ops.cpp:4691` — *"modes use an E8M0 scale and the `"nv"` mode uses an E4M3 scale."*
- MLX safetensors I/O has `#define ST_F8_E8M0 "F8_E8M0"`.

### Binding quantized tensors in the kernel

**[TRANSCRIPT] 330:52–60:**
> *"In the kernel, **it helps to define type aliases up front before binding the tensors**. Here we declare a **scales factor plane with `fp8_e8m0` data type, and a block size of 32 by 1. That means every 32 elements in the data plane share a single element in the `scales_plane`.** Then we declare a **full tensor type, specifying an FP8 data type along with the `scales_plane`.**"*
> *"You can simply **bind these tensors to buffer binding points**. The kernel will then have access to the tensors you've allocated on the host side."*
> *"**Alternatively, if you don't want to create a full `MTLTensor` on the host, you can create a temporary tensor right on the shader's stack. The syntax is almost identical, just swap the tag `tensor_handle` with `tensor_inline`.** Then **pass your buffer pointers and other metadata to the tensor constructor** to create a tensor on the stack."*

**[RECONSTRUCTED — MSL; `tensor_handle`/`tensor_inline` tags ARE verified, the scale-plane type name is NOT]:**
```cpp
#include <metal_tensor>
#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>
using namespace metal;
using namespace mpp::tensor_ops;

// --- type aliases up front ---
using scales_plane = scale_plane<fp8_e8m0, /*block*/ 32, 1>;         // UNVERIFIED spelling
using weight_t     = tensor<device fp8_e4m3, dextents<int32_t, 2>, tensor_handle, scales_plane>;  // UNVERIFIED 4th param

kernel void quantized_matmul(
    tensor<device half,  dextents<int32_t, 2>, tensor_handle> A [[buffer(0)]],
    weight_t                                                  B [[buffer(1)]],
    tensor<device float, dextents<int32_t, 2>, tensor_handle> C [[buffer(2)]],
    uint2 tgid [[threadgroup_position_in_grid]])
{ ... }
```
Stack-allocated variant (330:59–60):
```cpp
// swap tensor_handle -> tensor_inline, then construct from raw pointers + metadata
auto Bt = tensor<device fp8_e4m3, dextents<int32_t, 2>, tensor_inline, scales_plane>(
              b_data_ptr, b_scale_ptr, dextents<int32_t, 2>(K, N));   // arg list UNVERIFIED
```

**[VERIFIED — the tag taxonomy is real]** `__impl/MPPTensorOpsTypes.h`:
```cpp
enum __tensor_ops_tensor_descriptor_type {
  __tensor_ops_tensor_descriptor_type_handle,
  __tensor_ops_tensor_descriptor_type_offset,
  __tensor_ops_tensor_descriptor_type_inline,
  __tensor_ops_tensor_descriptor_type_none,   // raw data pointer (thread*)
};
enum __tensor_ops_address_space {
  __tensor_ops_address_space_invalid,
  __tensor_ops_address_space_device,
  __tensor_ops_address_space_threadgroup,
  __tensor_ops_address_space_thread_private,
};
```
and `MPPTensorOpsMatMul2d.h:9–10`:
> *"**A and B can be `tensor_handle`, `tensor_offset`, and `tensor_inline`. C can be `tensor_handle`, `tensor_offset`, `tensor_inline` or `cooperative_tensor`.**"*

So there are **four** descriptor tags (`handle`, `offset`, `inline`, `none`), and **three address spaces** (`device`, `threadgroup`, `thread_private`). `tensor_offset` is what `.slice()` produces.

### Slicing per threadgroup

**[TRANSCRIPT] 330:61–64:**
> *"we'll **divide the problem over many threadgroups for better parallelism**. First, we'll **slice out the tile for each threadgroup** and then perform the multiplication with TensorOps. To do this, simply **call `slice` on your input and output tensors using the threadgroup ID**. **The data and scales plane will both be sliced simultaneously according to the block size.**"* ← the last sentence is the important new-in-27 behavior.

**[VERIFIED — `slice` / `static_slice` semantics, MPPTensorOpsMatMul2d.h:106–114 and 143–145]:**
```cpp
// Following three lines of code create appropriate slice for this thread
// group to work on. E.g. A.slice below creates a
// tensor<device half, dextents<int32_t, 2>, tensor_offset>
// which has same extents as original tensor A but origin shifted to
// (0, tgid.y*64) i.e. mA[x,y] == A[x, tgid.y*64+y]
auto mA = A.slice(0, tgid.y*64);
auto mB = B.slice(tgid.x*32, 0);
auto mC = C.slice(tgid.x*32, tgid.y*64);

// bounds-check-free variant for interior tiles:
auto tA = A.static_slice<dynamic_extent, 64>(0, tgid.y*64);
auto tB = B.static_slice<32, dynamic_extent>(tgid.x*32, 0);
auto tC = C.static_slice<32, 64>(tgid.x*32, tgid.y*64);
```
> **Perf guidance verbatim from the header (a great guide item, not in the talk):** *"Above matrix multiplication implementation will do **edge checking for all thread groups** against extents of original tensor although **for large enough matrices most of thread groups will be working on 'inside' tiles, requiring no bounds check**. In high performance code we can **avoid edge checking for inside thread groups and get better performance**"* — via the `if (tgid.x*64 + 63 < M && tgid.y*32 + 31 < N)` + `static_slice` pattern.

### Setting up the quantized matmul

**[TRANSCRIPT] 330:65–68:**
> *"Setting up the matrix multiplication with quantized tensors is **identical to normal tensors**. First, set up the **`matmul2d_descriptor`, specifying the tile sizes and other parameters**. Then create a **`matmul2d` op, specifying the number of simdgroups in the threadgroup**. Then simply **pass in your quantized tensors and TensorOps will handle dequantization for you**."*

**[VERIFIED — exact descriptor definition, MPPTensorOpsMatMul2d.h:349–377]:**
```cpp
struct matmul2d_descriptor
{
  enum class mode { multiply, multiply_accumulate, };

  int m, n, k;
  bool transpose_left, transpose_right;
  bool relaxed_precision;
  mode matmul_mode;

  constexpr matmul2d_descriptor(int __m, int __n,
                                int __k = static_cast<int>(metal::dynamic_extent),
                                bool __transpose_left = false,
                                bool __transpose_right = false,
                                bool __relaxed_precision = false,
                                mode __matmul_mode = mode::multiply) thread;
};
```
Parameter semantics, verbatim from the header comments:
- `m`, `n` — *"outer dim of local tile"*
- `k` — *"k inner dimension. **`dynamic_extent` means operation will read K from input tensor**"*; passing a concrete value (e.g. 16) means *"tilek = 16, **we loop over K in chunks of 16 rather than letting matmul op run method loop over K internally**"*
- `transpose_left` — *"false for NN and NT and true for TN and TT"*
- `transpose_right` — *"false for NN and TN and true for NT and TT"*
- `relaxed_precision` — *"set it to true to **allow implementation to sacrifice accuracy for performance**"*
- `matmul_mode` — `multiply` (default!) vs `multiply_accumulate`

> **FOOTGUN:** the default `matmul_mode` is **`multiply`**, not `multiply_accumulate`. MLX explicitly passes `multiply_accumulate` (see below). Also the header's first example says *"**execute the operation. Assumes C is initialized to zero.**"*

**[VERIFIED — the op class and execution scopes, MPPTensorOpsMatMul2d.h:391–418]:**
```cpp
template <matmul2d_descriptor Descriptor, typename Scope, class... Args>
class matmul2d : __tensor_ops_detail::op {
  static constexpr constant matmul2d_descriptor descriptor = Descriptor;
  using scope = Scope;
  matmul2d() thread = default;

  template <typename LeftOperandType, typename RightOperandType, typename DestinationOperandType, ...>
  INLINE void run(thread LeftOperandType &left,
                  thread RightOperandType &right,
                  thread DestinationOperandType &destination) thread const;
  ...
};
```
**Execution scopes, verbatim (MPPTensorOpsMatMul2d.h:296–315):**
> *"A tensor operation may be executed on a single thread entirely or cooperatively among a set of SIMD groups. The set of threads is called the **'execution scope'**... **All the threads in this execution scope must enter the `run` method i.e. call to run methods must be 'execution scope' uniform.**"*
> - `metal::execution_thread` — *"The operation will be run on a single thread. **Fragment shaders only support this execution scope.**"*
> - `metal::execution_simdgroup` — *"run cooperatively by all threads in the SIMD group. **May be used for finer control over tiling by slicing tensors with SIMD IDs.**"* ← exactly the FlashAttention trick in §2.4
> - `metal::execution_simdgroups<N>` — *"executed cooperatively by N SIMD groups. **Must be used when all threads in a threadgroup are cooperatively performing the operation.**"*
>
> *"**It is undefined behavior if the number of SIMD groups dispatched does not match the number of SIMD groups that the operation was configured with.**"*

Host-side dispatch pairing, verbatim from the header:
```objc
id<MTLComputePipelineState> state = [device newComputePipelineState:...];
NSUInteger simdgroupWidth = [state threadExecutionWidth];
[encoder dispatchThreadgroups:threadgroups
        threadPerThreadgroups:MTLSizeMake(simdgroupWidth*4, 1, 1)];   // 4 SIMD-groups
```
with `MTLSize threadgroups = MTLSizeMake((M + 63)/64, (N + 31)/32, 1);` for a 64×32 tile.

**[VERIFIED — a real production call site, MLX]** `repos/ml-explore__mlx/mlx/backend/metal/kernels/steel/gemm/nax.h:401–447`:
```cpp
constexpr auto desc = mpp::tensor_ops::matmul2d_descriptor(
    16,
    32,
    16,
    transpose_a,
    transpose_b,
    true,                                                             // relaxed_precision = TRUE
    mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);

// Create matmul op
mpp::tensor_ops::matmul2d<desc, metal::execution_simdgroup> gemm_op;

// Create matmul operands in registers
auto ct_a = gemm_op.template get_left_input_cooperative_tensor<AType, BType, CType>();
auto ct_b = gemm_op.template get_right_input_cooperative_tensor<AType, BType, CType>();

// Create matmul output in register
auto ct_c = gemm_op.template get_destination_cooperative_tensor<
    decltype(ct_a), decltype(ct_b), CType>();

// ...load A, B, C into the cooperative tensors elementwise...
gemm_op.run(ct_a, ct_b, ct_c);
// ...copy results out...
```
(same code duplicated in `steel/attn/nax.h:401`+, i.e. MLX's *attention* kernels use exactly this.) MLX's `BaseNAXFrag` uses `kFragRows = kFragCols = 16`, `kElemsPerFrag = 16*16/32 = 8`, `kElemRows = 2`, `kElemCols = 4`, `kElemRowsJump = 8` — useful concrete numbers for the register layout of a 16×16 fragment across a 32-lane SIMD group.

### Custom dequantization paths

**[TRANSCRIPT] 330:69–77** — the decision tree, verbatim and worth reproducing wholesale in a guide:
> *"**In most cases, you should feed your quantized data straight into TensorOps so that it can automatically utilize any available hardware acceleration.** However, if you need to dequantize a custom format, TensorOps still have you covered."*
> *"**The simplest approach** is to have each thread **load a chunk of quantized data from device memory and dequantize it to f16 values in threadgroup memory**. You can then pass it as an **inline threadgroup tensor** to TensorOps. **However, this approach requires extra loads and stores through threadgroup memory.**"*
> *"**Ideally, we would keep all this data in thread registers instead.** You can do this by **dequantizing the data into a cooperative tensor, which can now be passed as an input to the `matmul2d` op**. **Cooperative tensors distribute their storage across the thread private memory of the threads participating in the matmul operation.** So if you can't use quantized tensors directly, **you can still skip the round trip through threadgroup memory**."*

Three-tier ranking, best → worst:
1. **Native quantized tensor** (data plane + scale plane) → hardware dequant.
2. **Dequantize into a `cooperative_tensor`** → registers only; pass as matmul input. *(new capability — see §2.4)*
3. **Dequantize into threadgroup memory** → wrap as `tensor_inline` over `threadgroup` address space → extra loads/stores.

**[VERIFIED — what a `cooperative_tensor` *is*, MPPTensorOpsMatMul2d.h:212–225]:**
> *"Unlike `tensor_handle`, `tensor_offset` and `tensor_inline` which are **non-owning** — meaning these are wrappers around resource in device, threadgroup or thread address space — **`cooperative_tensor` owns thread private data and divides the data for entire tensor among threads (participating in the scope of operation) in implementation defined manner. This thread private memory is allocated at construction of `cooperative_tensor` and deallocated when this `cooperative_tensor` goes out of scope. The layout of `cooperative_tensor` depends on operation, data type, number of threads in opscope with which op was created.** Note that **`cooperative_tensor` created from an op is only valid for threads that are part of execution scope on which op was created.**"*

**[VERIFIED — the cooperative tensor accessor API, from the header's worked example]:**
```cpp
auto cT = matmulOp.get_destination_cooperative_tensor<decltype(mA), decltype(mB), float>();

#pragma unroll full                       // "It is imperative for performance to include 'unroll pragma'"
for (uint16_t i = 0; i < cT.get_capacity(); ++i) {
  if (cT.get_mask(i))                     // "not all threads and even all elements within a thread need be valid"
    cT[i] = 0;
}

op.run(mA, mB, cT);

auto biasT = matmulOp.get_destination_cooperative_tensor<decltype(mA), decltype(mB), float>();
biasT.load(bias);                          // load from a tensor_handle into cooperative layout

#pragma unroll full
for (uint16_t i = 0; i < cT.get_capacity(); ++i) {
  if (cT.get_mask(i)) {
    cT[i] += biasT[i];
    auto ids = cT.get_multidimensional_index(i);   // 2-D local coord within the tile
    cT[i] = foo(cT[i], ids);
  }
}
cT.store(mC);                              // store back to a tensor handle
```
Accessors: **`get_capacity()`**, **`get_mask(i)`**, **`operator[](i)`**, **`get_multidimensional_index(i)`**, **`load(tensor)`**, **`store(tensor)`**, plus iterators **`begin()` / `end()`** and **`map_iterator(...)`** (§2.4).
Motivation verbatim: *"we need to do some post processing on computed results before storing... One can do GEMM as above which writes the result to device memory, read the value back, call post processing function and write again. **This results in wasted bandwidth, performance and power.** User can apply post processing **in-register**."*

### Recap (330:78–79, verbatim)
> *"Metal tensors natively support a wide range of quantized data types, including **the new MX scaling formats and E8M0 scale factors coming in iOS and macOS 27**. Note that **these new data types have additional alignment requirements** compared to the larger data types, so **be sure to check the Metal documentation for details**."*

## 2.3 Attention recap (330:81–85)

> *"**Attention is at the core of every transformer network, including LLMs.** To compute attention, you first **multiply two matrices together called Q and K**. Next, you **compute SoftMax using reductions on the rows of the intermediate matrix**. Finally, you **multiply by a third matrix called V**. **The popular FlashAttention algorithm fuses all of these operations together into a single kernel.**"*

## 2.4 Building FlashAttention with TensorOps

### Step 1 — custom SIMD-group mapping

**[TRANSCRIPT] 330:86–90:**
> *"To implement this with TensorOps, you'll first need to **set up a custom simd group mapping so that each simd group owns complete rows of the intermediate matrix. This allows you to compute the SoftMax without exchanging data between simd groups.** You can do this using the **`execution_simdgroup` operation scope**. This means that **each simd group will perform an independent matrix multiplication in parallel.** You can use the **simd group ID to slice your input tiles**."*

This is precisely the header's stated use for `execution_simdgroup`: *"May be used for finer control over tiling by **slicing tensors with SIMD IDs**."*

**[RECONSTRUCTED]:**
```cpp
constexpr auto qk_desc = mpp::tensor_ops::matmul2d_descriptor(
    TILE_M, TILE_N, static_cast<int>(metal::dynamic_extent),
    /*transpose_left=*/false, /*transpose_right=*/true,      // Q @ K^T
    /*relaxed_precision=*/true,
    mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);

mpp::tensor_ops::matmul2d<qk_desc, metal::execution_simdgroup> qk_op;   // per-SIMD-group scope

// each simdgroup owns complete rows of S
auto qTile = Q.slice(0, sgid * TILE_M);
auto kTile = K.slice(0, 0);
auto S = qk_op.get_destination_cooperative_tensor<decltype(qTile), decltype(kTile), float>();
qk_op.run(qTile, kTile, S);          // S stays in registers — never written to memory
```
> 330:91 — *"We'll use a **cooperative tensor to store the intermediate matrix so that we can use it as an input to the next step without writing it to the memory**."*

### Step 2 — row reductions for SoftMax

**[TRANSCRIPT] 330:93–100:**
> *"To do this, we'll need to compute a couple of reductions on the cooperative tensor. **TensorOps includes a `reduce_rows` function to help with this.** **Threads will exchange data amongst themselves to calculate the max for each row. The result is returned in another cooperative tensor.**"*
> *"Let's set it up. **First, create a cooperative tensor to store the reduction output. Then pass the source and destination to the `reduce_rows` function. Here we'll use the `max` `reduction_operation` with an initial value of negative `INFINITY`.**"*

**[VERIFIED — exact signatures, MPPTensorOpsMatMul2d.h:342–347 and 587–609]:**
```cpp
enum class reduction_operation { sum, max, min, };

template <typename ElementType>
struct reduction_operation_identity {
  static const constant ElementType sum_identity = (ElementType)0;
  static const constant ElementType max_identity = metal::numeric_limits<ElementType>::lowest();
  static const constant ElementType min_identity = metal::numeric_limits<ElementType>::max();
};

template <class ElementType, class SrcExtents, class DstExtents, class SrcLayout, class DstLayout>
inline void reduce_rows(
    thread metal::cooperative_tensor<ElementType, SrcExtents, SrcLayout> &source,
    thread metal::cooperative_tensor<ElementType, DstExtents, DstLayout> &destination,
    reduction_operation op = reduction_operation::sum,
    ElementType identity = reduction_operation_identity<ElementType>::sum_identity);

template <class ElementType, class SrcExtents, class DstExtents, class SrcLayout, class DstLayout>
inline void reduce_columns(   /* same shape */ );
```
> **⚠️ Default-argument footgun (exactly what the presenter warns around).** `identity` defaults to **`sum_identity` (== 0)** *regardless of `op`*. If you pass `reduction_operation::max` and forget the identity, you get an identity of 0, not `-INFINITY`. This is why 330:100 says *"the `max` reduction_operation **with an initial value of negative INFINITY**."* **Always pass the identity explicitly when op != sum.**

Also on the op class — dedicated factories for reduction destinations (correct shapes, no guessing):
```cpp
auto rowMax = op.get_row_reduction_destination_cooperative_tensor<LeftT, RightT, ElementType>();
auto colSum = op.get_column_reduction_destination_cooperative_tensor<LeftT, RightT, ElementType>();
```

**[RECONSTRUCTED]:**
```cpp
auto rowMax = qk_op.get_row_reduction_destination_cooperative_tensor<
                  decltype(qTile), decltype(kTile), float>();
mpp::tensor_ops::reduce_rows(S, rowMax,
                             mpp::tensor_ops::reduction_operation::max,
                             -INFINITY);                    // explicit identity
```

### Step 3 — `map_iterator` to line up two differently-shaped cooperative tensors

**[TRANSCRIPT] 330:101–105:**
> *"**These two cooperative tensors have different shapes**, so to help map between them, **TensorOps also includes a `map_iterator` function. Given an iterator pointing to an element in the 2D tensor, it returns an iterator pointing to the corresponding element in the reduction destination.**"*
> *"First, **set up a loop over the 2D cooperative tensor using iterators**. Then **call `map_iterator` to map each element to its corresponding row max**. Finally, **dereference these iterators to compute SoftMax and store the result back into the cooperative tensor**."*

**[VERIFIED — the canonical pattern, verbatim from MPPTensorOpsMatMul2d.h:611–633]:**
```cpp
// Returns whether the iterators are compatible between a source and destination cooperative tensor.
//
// Use this to check whether map_iterator will be return a valid iterator. For example:
//
//     if (is_iterator_compatible(sourceCT, destCT)) {
//         for (auto it = sourceCT.begin(); it != sourceCT.end(); it++) {
//             auto dst_it = destCT.map_iterator(sourceCT)
//
//             *it += *dst_it;
//         }
//     }
//     else {
//          // Fall back to storing sourceCT to threadgroup memory and access via
//          // destCT's multidimensional indices
//     }
template <class SrcElementType, class DstElementType, class SrcExtents, class DstExtents,
          class SrcLayout, class DstLayout>
inline bool is_iterator_compatible(
    const thread metal::cooperative_tensor<SrcElementType, SrcExtents, SrcLayout> &source,
    const thread metal::cooperative_tensor<DstElementType, DstExtents, DstLayout> &destination);
```
> **[GUIDE-WORTHY GAP]** The talk never mentions **`is_iterator_compatible`** — but the header says you should call it before relying on `map_iterator`, with a documented threadgroup-memory fallback. That is a second compatibility check, distinct from `is_compatible_as_left/right_input` in step 4.
>
> (The snippet in the header is illustrative pseudo-code — note it's missing a `;` and passes `sourceCT` rather than `it` to `map_iterator`. Treat the *argument* of `map_iterator` as UNVERIFIED; the transcript says it takes "an iterator pointing to an element in the 2D tensor", which suggests `destCT.map_iterator(it)`.)

**[RECONSTRUCTED]:**
```cpp
for (auto it = S.begin(); it != S.end(); ++it) {
    auto m_it = rowMax.map_iterator(it);     // corresponding row-max element
    *it = exp(*it - *m_it);                  // softmax numerator, in-register
}
// row sums, then normalize
auto rowSum = qk_op.get_row_reduction_destination_cooperative_tensor<
                  decltype(qTile), decltype(kTile), float>();
mpp::tensor_ops::reduce_rows(S, rowSum, mpp::tensor_ops::reduction_operation::sum, 0.0f);
for (auto it = S.begin(); it != S.end(); ++it) {
    auto s_it = rowSum.map_iterator(it);
    *it = *it / *s_it;
}
```

### Step 4 — feed the cooperative tensor into the second matmul

**[TRANSCRIPT] 330:106–117** — the single most important new-capability statement in the talk:
> *"Now we're ready to multiply this cooperative tensor by V. **In macOS 26, you would have had to first store it to threadgroup memory. But it's now possible to use cooperative tensors directly as inputs to matmul operations.**"*
> *"To do this, call **`get_left_input_cooperative_tensor` method, passing the source cooperative tensor as an argument**. You can then pass the result as an input to the second matmul operation."*
> *"**One thing to watch out for: not every cooperative tensor can be reused as an input. The layouts may differ depending on the data types and other factors. So before you do this, call the `is_compatible_as_left` or `right _input` method to check for compatibility.**"*
> *"If it returns true, you're good to go. **If not, you'll need to store and reload the data through threadgroup memory to convert it to the correct layout. Either way, the call to `op.run` is the same.**"*

**[VERIFIED — the two overloads and the compatibility predicates, MPPTensorOpsMatMul2d.h:425–524]:**
```cpp
// (a) no-arg: create fresh input registers
template <typename LeftElementType, typename RightElementType, typename ElementType,
          typename CoordType = int, ..., typename... CoopArgs>
INLINE cooperative_tensor_left_input_t<...> get_left_input_cooperative_tensor() thread const;

// (b) NEW: build a left input FROM an existing cooperative tensor  <-- what the talk describes
template <typename LeftElementType, typename RightElementType, typename ElementType,
          typename CoordType = int,
          typename SrcElemType, typename SrcExtents, typename SrcLayout, ..., typename... CoopArgs>
INLINE cooperative_tensor_left_input_t<...>
get_left_input_cooperative_tensor(
    const thread metal::cooperative_tensor<SrcElemType, SrcExtents, SrcLayout> & src) thread const;

// the compatibility guard
template <typename LeftElementType, typename RightElementType, typename ElementType,
          typename SrcElemType, typename SrcExtents, typename SrcLayout, ...>
INLINE bool is_compatible_as_left_input(
    const thread metal::cooperative_tensor<SrcElemType, SrcExtents, SrcLayout> & src) thread const;

// ...and the exact right-hand mirrors:
get_right_input_cooperative_tensor()                     // no-arg
get_right_input_cooperative_tensor(src)                  // from an existing cooperative tensor
is_compatible_as_right_input(src)
```
> **Naming correction for the transcript.** The talk says *"call the `is_compatible_as_left` or `right _input` method"* — an ASR mangling of the two real method names **`is_compatible_as_left_input`** and **`is_compatible_as_right_input`**.

**[RECONSTRUCTED — the full step 4]:**
```cpp
constexpr auto pv_desc = mpp::tensor_ops::matmul2d_descriptor(
    TILE_M, HEAD_DIM, static_cast<int>(metal::dynamic_extent),
    false, false, true,
    mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);
mpp::tensor_ops::matmul2d<pv_desc, metal::execution_simdgroup> pv_op;

auto vTile = V.slice(0, 0);
auto O     = pv_op.get_destination_cooperative_tensor<decltype(S), decltype(vTile), float>();

if (pv_op.is_compatible_as_left_input<float, half, float>(S)) {
    auto lhs = pv_op.get_left_input_cooperative_tensor<float, half, float>(S);   // registers only
    pv_op.run(lhs, vTile, O);                       // "Either way, the call to op.run is the same."
} else {
    // fall back: store S to threadgroup memory, reload in the correct layout
    S.store(tg_scratch);
    threadgroup_barrier(mem_flags::mem_threadgroup);
    auto lhs = /* tensor_inline over tg_scratch */;
    pv_op.run(lhs, vTile, O);
}
O.store(outTile);
```

> **⚠️ SDK-vs-talk timing discrepancy.** The presenter frames "cooperative tensors directly as matmul inputs" as **new after macOS 26** (330:107). But the **Xcode 26.6 SDK header already ships** `get_left_input_cooperative_tensor(src)`, `is_compatible_as_left_input`, `reduce_rows`, `reduce_columns`, `is_iterator_compatible`, and the row/column reduction destination factories — and the header comment at line 10 already lists `cooperative_tensor` as a valid **destination** (only). Most likely reading: these landed in a **macOS 26.x point release** (cf. `__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2`), and "in macOS 26 you would have had to..." refers to **26.0**. **Verify availability annotations before promising a deployment target in a guide.**

### Step 5 — recap and the Core AI hand-off

**[TRANSCRIPT] 330:118–132:**
> *"Those are the key TensorOps features you'll need to build an advanced operation like FlashAttention using TensorOps."*
> *"Core AI provides tools for Python developers to convert PyTorch models to Core AI models, **including support for custom Metal kernels**."*
> *"I've followed the steps outlined in that session to integrate our custom FlashAttention kernel into a **Sam3 image segmentation model**. **We define the body of our custom attention kernel as a string in Python and register the `TorchMetalKernel` object**, shown here."*
> *"Then, **we replace the default huggingface attention implementation with one that calls our kernel**, shown here."*
> *"Finally, **we load the model from huggingface and export it from PyTorch as an optimized Core AI asset**. The export will take a moment to finish."*
> *"**Sam3 performs promptable concept segmentation**, so we provide the model with an image and text, and then it responds with a segmentation mask indicating where objects are located in the image. Here, I'm **prompting the model to label all pixels containing a car** in this image."*
> *"Looking at the final result, we can see the model correctly segmented the image. **The car is highlighted in blue, so our attention kernel is fully integrated into the model as expected.**"*

**[RECONSTRUCTED — the monkey-patch shape implied by 330:124]:**
```python
FLASH_ATTENTION_MSL = """
    ... FlashAttention body in MSL, using mpp::tensor_ops ...
"""

flash_attn = TorchMetalKernel(
    "flash_attention",
    input_names=["q", "k", "v"],
    result_names=["o"],
    src=FLASH_ATTENTION_MSL,
    helper_src=TENSOR_OPS_HELPERS,        # type aliases / includes go here
    torch_defn=torch_sdpa_reference,
    metal_params=[MetalParameter("tgid", "uint2", "threadgroup_position_in_grid"), ...],
)

# "replace the default huggingface attention implementation with one that calls our kernel"
def custom_attention_forward(self, q, k, v, **kwargs):
    return flash_attn(q, k, v,
                      threads_per_grid=(...), threads_per_thread_group=(...),
                      result_shapes=[list(q.shape)])

transformers.models.sam3.modeling_sam3.Sam3Attention.forward = custom_attention_forward
```
> ⚠️ Fully **[RECONSTRUCTED]** — the talk shows this on screen without reading it out. The `TorchMetalKernel` construction is grounded; the monkey-patch target class name is a guess.

**Closing (330:133–137, verbatim):**
> *"Today, I've covered all the tools you can use to build optimized custom ML kernels on Apple Silicon. From **quantized data types**, to advanced TensorOps features like **cooperative tensors and reductions**, to **integrating with Core AI**. To go further, explore the **Metal Performance Primitives documentation for the full API reference**, and the **programming guide** for more performance optimization guidelines. You can also **download the TensorOps sample code** to see the details that I couldn't cover here."*

→ Three named follow-up resources: **MPP API reference**, an **MPP programming guide**, and **downloadable TensorOps sample code**.

---

# PART 3 — Cross-check summary: transcripts vs. local docs / repos / SDK

## Agreements (transcript claim → independent confirmation)

| Transcript claim | Confirmed by |
|---|---|
| `pip install coreai-torch` installs `coreai` + `coreai-torch` | `coreai-torch/README.md:20-22` |
| `TorchConverter` takes exported program + input/output names → `coreai_program` | `docs/api/TorchConverter.md:41-84` |
| ".aimodel asset" is the on-device format | `docs/Run AI models in your app on Apple silicon.md:22`; `docs/Integrating on-device AI models...:20`; `quickstart.ipynb` `save_asset(...)` |
| Run inference from Python with a dict of names → arrays | `quickstart.ipynb` cell 12; `run-an-aimodel.ipynb` cell 8 |
| "specialization options at this point" | `SpecializationOptions` in `coreai.runtime`; `asset.executable(options)` **(macOS only)** |
| `presets.w4` = 4-bit per-channel symmetric, one line | `_presets/quantizer_config.py::w4` |
| `ExecutionMode.EAGER` / `.GRAPH` exist | `quantization_config.py:134-153` |
| `Quantizer(model, config)` → `prepare(example_inputs)` → `finalize()` | `quantizer.py` + `coreai-optimization/README.md` usage block |
| `coreai-opt` supports int4/int8/FP4/FP8 with flexible granularity | `docs/src/quantization/config.md` `W_MXFP4_A_FP8` example |
| calibration data *or* QAT | `Quantizer.calibration_mode()` / `training_mode()` / `QATSchedule` |
| "casting the program to 16-bit using coreai-opt's helper" | `coreai_opt.casting.cast_to_16_bit_precision` |
| "custom table" preserves attention | `get_decomp_table()` preserves `scaled_dot_product_attention`, `instance_norm`, `pixel_shuffle` |
| `TorchMetalKernel(source, torch reference, input/output names)` | `docs/api/TorchMetalKernel.md` — exact ctor |
| `result_shapes` at every call site for dynamic shapes | `TorchMetalKernel.__call__` requires `result_shapes` |
| "register my custom kernels with the converter, then add the exported program" | *"This must be called **before** `add_exported_program()`."* |
| "coreai-torch has APIs that lets you [have three functions]" | `entrypoint_name=` on `add_exported_program`; `pipeline.py` uses `image_encode`/`text_encode`/`detect` |
| SAM3 ~850M params; 3-function split; iOS 336px | `models/sam3/README.md` (848M, 336 default) |
| Conv projections instead of Linear for iOS | `models/ios/sam3/image_encoder.py` — `nn.Conv2d(hidden,hidden,1)` ×4, `_linear_to_conv2d` |
| "channels-first tensor layouts" | BC1S `(B, C, 1, S)` throughout the re-authored SAM3 |
| "detector stays uncompressed" | `pipeline.py`: `DetectorModule` gets fp16 only, no palettizer |
| `KMeansPalettizer` "similar to the Quantizer", prepare + finalize | `palettization/kmeans/palettizer.py` |
| MSL is embedded in the asset, ships with the model | `TorchMetalKernel` doc: *"the kernel travels with the model"* framing matches `register_custom_kernels` |
| TensorOps = MSL API for matmul + convolution | SDK ships exactly `MPPTensorOpsMatMul2d.h` + `MPPTensorOpsConvolution2d.h` |
| `matmul2d_descriptor` with tile sizes and other params | verbatim struct in the SDK header |
| `execution_simdgroup` scope for per-SIMD-group matmuls | SDK header scope docs; MLX uses exactly `matmul2d<desc, metal::execution_simdgroup>` |
| `reduce_rows`, `reduction_operation::max`, cooperative tensors | verbatim in the SDK header |
| `is_compatible_as_left/right_input` before reusing a coop tensor | `is_compatible_as_left_input` / `is_compatible_as_right_input` in the header |
| E8M0 block scales, 32-element blocks | `torch.float8_e8m0fnu` + `block_size=32` in `coreai-opt`; `fp8_e8m0` in MLX; mxfp4/mxfp8 group 32 |
| Int4/Int8 "in an update to macOS and iOS 26" | `MTLTensorDataTypeInt4/UInt4 API_AVAILABLE(macos(26.4), ios(26.4))` |
| "additional alignment requirements" for small dtypes | `MTLTensor.h:116` — sub-byte dtypes need **128-byte** stride alignment (vs 64 for ML usage) |

## Discrepancies / nuances to flag

1. **`ExecutionMode` recommendation.** Talk: "EAGER works great for weight compression." Repo: GRAPH is the *"Recommended default"* and the actual default value. Not a contradiction, but a guide must state both and explain *why* (exportability vs. observer/FQ dedup).
2. **SAM3 palettization is asymmetric in the shipped recipe.** Talk: "4-bit palettization... to the two encoders." Repo: image w4/gs32, **text w6/gs8**.
3. **"per-channel scales."** Talk says the encoders use per-channel scales. Shipped code deliberately sets `enable_per_channel_scale=False` because `True` produces **rank-6 LUTs that ANE rejects (max rank 5)**, forcing GPU fallback. Either the talk meant `PerGroupedChannelGranularity`, or the recipe changed post-recording.
4. **"In macOS 26, you would have had to first store it to threadgroup memory."** The Xcode 26.6 SDK already exposes the cooperative-tensor-as-input overloads. Likely means macOS 26.0 vs a 26.x point release (`__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2`).
5. **Scale-plane API names are unconfirmed.** `blockFactors`, the auxiliary plane map, and an E8M0 `MTLTensorDataType` case do **not** appear in the 26.6 SDK. Everything in §2.2's scale-plane snippet is UNVERIFIED spelling.
6. **`is_iterator_compatible` is absent from the talk** but the header says to use it as the guard for `map_iterator` (with a documented threadgroup-memory fallback). The talk only mentions the *matmul-input* compatibility check.
7. **`matmul2d_descriptor` default mode is `multiply`, not `multiply_accumulate`.** The talk never mentions the mode parameter; the header's own examples say "Assumes C is initialized to zero." MLX always passes `multiply_accumulate` explicitly.
8. **`reduce_rows` identity default is `sum_identity` regardless of `op`.** The talk implicitly warns about this by stating "-INFINITY" for max; the API makes it easy to get wrong.
9. **Transcript ASR artifacts to not propagate:** "core_ai_ program" → `coreai_program`; "`is_compatible_as_left` or `right _input`" → `is_compatible_as_left_input` / `is_compatible_as_right_input`; "fp8_e8m0_" → `fp8_e8m0`; "witchever" → "whichever"; "transpse_left" (typo is in the *SDK header*, not ASR).
10. **`save_intermediates` docstring examples still say `dump_intermediates`** — a stale name in the shipping source. Only `save_intermediates` / `load_intermediates` are exported.

---

# PART 4 — Consolidated gotchas / footguns

**Python / conversion**
- `run_decompositions(get_decomp_table())` is **mandatory** before `add_exported_program`; skipping leaves ops with no lowering rule.
- `.eval()` before `torch.export` — BatchNorm/Dropout produce a different graph otherwise.
- `optimize()` mutates the `AIProgram` in place; nothing consumes its return value in any Apple example.
- `entrypoint_name` must be unique across staged programs; default `"main"`.
- `input_names`/`output_names` **no longer cover state** — breaking change; state is renamed via `state_names`.
- **No opt-out from state:** any in-place mutation of a buffer or a `forward()` arg makes it state. Clone or go out-of-place to avoid it.
- Default IO names and `state_names` ordering are *observed FX behavior*, not contracts; always name explicitly.
- Runtime buffers are only valid inside `async with asset.executable()`; call `.numpy()` before exiting.
- `SpecializationOptions` is **macOS only**.
- `coreai._compiler.*` is private upstream API (used by custom lowerings) and may move without notice.
- Reserved lowering namespaces: `aten`, `higher_order`, `coreai`, `coreaix`.
- Debug metadata requires `USE_LOCAL_COREAI=1` and `ENABLE_DEBUG_INFO=1` during the preview.
- `load_intermediates` rejects directories not ending in `.aimodelintermediates`.

**Compression**
- GRAPH and EAGER *"are not guaranteed to produce equivalent quantized models"* for the same config.
- EAGER has **no shared-observer handling** — MaxPool-style ops get independent input/output observers, *"which can cause incorrect quantization."*
- EAGER inserts back-to-back fake-quantize nodes (no dedup).
- `kv_cache_quant_configs` is **GRAPH-only**; raises `ValueError` in EAGER.
- `module_type_configs` keys must be **fully-qualified** class paths (`torch.nn.modules.linear.Linear`, not `torch.nn.Linear`).
- `PalettizationSpec.n_bits ∈ {1,2,3,4,6,8}` only.
- `lut_qspec` requires `PerTensorGranularity`; FP8 LUT dtypes require symmetric; `MINVAL` formulation rejected.
- `PerGroupedChannelGranularity` requires the axis length to be divisible by `group_size`.
- `enable_per_channel_scale=True` → rank-6 LUTs → **ANE rejects (max rank 5)** → GPU fallback.
- `KMeansPalettizer.finalize(backend=CoreAI)` **destroys the original dense weights in place**.
- `finalize()` is only for export; for torch-side eval use the `prepare()` model.
- Palettization silently *disables itself per-layer* on granularity/`cluster_dim` incompatibility (warning only).
- `mmap_dir` is CoreAI-backend-only and the files must outlive the model.
- `num_workers=1` default makes k-means clustering slow on big models; bump it.

**Metal / TensorOps**
- Sub-byte tensor dtypes need **128-byte** stride alignment; ML-usage tensors need **64-byte** second-stride alignment; `strides[0]` must be 1.
- `matmul2d_descriptor` defaults to `mode::multiply`; destination must be pre-zeroed for accumulate-style use.
- `reduce_rows`'s `identity` default is the **sum** identity even when `op` is `max`/`min`.
- `run()` calls must be **execution-scope uniform** — all threads in the scope must enter.
- **UB** if dispatched SIMD-group count ≠ the count baked into `execution_simdgroups<N>`.
- Fragment shaders support **only** `execution_thread`.
- Cooperative tensors are only valid for threads in the op's execution scope; layout is implementation-defined.
- Not all cooperative-tensor elements are valid — always guard with `get_mask(i)`.
- `#pragma unroll full` on cooperative-tensor loops is described as *"imperative for performance."*
- Check `is_compatible_as_left/right_input` before reusing a cooperative tensor as a matmul input; check `is_iterator_compatible` before `map_iterator`. Both have a threadgroup-memory fallback.
- 4-bit types only appear as the **right** operand in the supported dtype matrix.
- Edge/bounds checking costs perf; use `static_slice<...>` on interior tiles.

**SAM3 reproduction specifics**
- `facebook/sam3` is **gated on Hugging Face** — needs `hf auth login`.
- Needs `transformers>=5.5.4,<5.10.1` + `huggingface-hub>=1.5.0,<2.0`, which **conflict with the `coreai-models` workspace pins** — hence the PEP 723 inline script with `override-dependencies`.
- `--n-bits` / `--group-size` apply to **both** encoders uniformly, overriding the asymmetric default.

---

# Source inventory

**Transcripts (read in full):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-325.txt` (268 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-330.txt` (138 lines)

**Local docs:**
- `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Run AI models in your app on Apple silicon.md` (full)
- `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Integrating on-device AI models in your app with Core AI.md` (grep, line 20)

**`repos/apple__coreai-torch`:**
- `README.md` (full)
- `docs/api/TorchConverter.md` (full, 504 lines)
- `docs/api/TorchMetalKernel.md` (full, 178 lines)
- `docs/api/debugging.md` (full, 309 lines)
- `docs/coreai-core/api/coreai.md` (full)
- `docs/getting-started/quickstart.ipynb` (all cells)
- `docs/coreai-core/tutorials/run-an-aimodel.ipynb` (all cells)
- `docs/guides/custom-metal-kernels.ipynb` (all cells)
- `docs/guides/conversion-workflows.ipynb` (all cells)
- `coreai_torch/debugging/torch_utils.py` (lines 900–1030 + greps)
- module tree listing of `coreai_torch/`

**`repos/apple__coreai-optimization`:**
- `README.md` (full)
- `src/coreai_opt/quantization/config/_presets/quantizer_config.py` (full)
- `src/coreai_opt/quantization/config/quantization_config.py` (lines 134–164, 560–771)
- `src/coreai_opt/quantization/quantizer.py` (lines 60–220, 357–430 region)
- `src/coreai_opt/palettization/__init__.py`, `spec/__init__.py`, `spec/spec.py` (1–140), `spec/granularity.py` (greps), `spec/fake_palettize.py` (head)
- `src/coreai_opt/palettization/config/_presets/kmeans_palettizer_config.py` + `module_kmeans_palettizer_config.py` (head)
- `src/coreai_opt/palettization/kmeans/palettizer.py` (1–120, 154–260, 357–430)
- `src/coreai_opt/casting/__init__.py`, `src/coreai_opt/casting/casting.py` (1–120)
- `docs/src/quantization/config.md` (lines 183–345)
- doc tree listings for `docs/src/{quantization,palettization,pruning,utils,tutorials,introduction,debugging,examples}`

**`repos/apple__coreai-models`:**
- `models/sam3/README.md` (full)
- `models/sam3/export.py` (full)
- `python/src/coreai_models/segmentation/pipeline.py` (full, 467 lines)
- `python/src/coreai_models/models/ios/sam3/image_encoder.py` (lines 1–120)
- `skills/skills/working-with-coreai/SKILL.md` (lines 1–60)
- `skills/skills/model-authoring/references/gpu_rules.md` (lines 1–120)
- `.claude-plugin/*.json`, `skills/gemini-extension.json`
- file tree of `python/src/coreai_models/`

**`repos/ml-explore__mlx`** (Metal ground truth):
- `mlx/backend/metal/kernels/steel/gemm/nax.h` (lines 1–40, 370–520)
- `mlx/backend/metal/kernels/steel/attn/nax.h` (greps, identical matmul2d usage)
- greps in `mlx/backend/metal/kernels/fp8.h`, `fp_quantized.h`, `fp_quantized_nax.h`, `mlx/io/safetensors.cpp`, `python/src/ops.cpp`

**Xcode 26.6 macOS SDK** (`/Applications/Xcode.app/.../MacOSX.sdk/System/Library/Frameworks/`):
- `MetalPerformancePrimitives.framework/Versions/A/Headers/MPPTensorOpsMatMul2d.h` (full, 642 lines)
- `.../Headers/__impl/MPPTensorOpsTypes.h` (full)
- `.../Headers/__impl/MPPTensorOpsAvailability.h` (full)
- `.../Headers/MetalPerformancePrimitives.h` (full)
- `Metal.framework/Versions/A/Headers/MTLTensor.h` (full, 215 lines)
- greps for `newTensorWithDescriptor` in `MTLDevice.h`, `MTLBuffer.h`
- Xcode version: `26.6` (so all SDK evidence is the **26** generation, not 27)

---

# Open questions / unverified

1. **Scale-plane API spelling (iOS/macOS 27).** Exact Objective-C/Swift names for the scale-plane descriptor, `blockFactors`, the auxiliary plane map type, the property on `MTLTensorDescriptor`, and the E8M0 `MTLTensorDataType` case. None exist in the Xcode 26.6 SDK. **Needs an Xcode 27 SDK or the MPP docs.**
2. **MSL-side scale-plane type.** The transcript says "declare a scales factor plane with `fp8_e8m0` data type and a block size of 32 by 1", then "declare a full tensor type, specifying an FP8 data type along with the `scales_plane`". The MSL template spelling (a 4th template parameter on `tensor<>`? a separate `quantized_tensor<>`?) is unknown.
3. **New 27 MSL element types.** Names for FP4/FP8/Int2 in `__tensor_ops_datatype` and the corresponding `MTLTensorDataType` cases.
4. **`map_iterator` argument.** Header pseudo-code passes the source *tensor*; the transcript says it takes an *iterator*. Real signature unresolved.
5. **`tensor_inline` constructor argument list.** "pass your buffer pointers and other metadata to the tensor constructor" — exact parameter order/types unknown.
6. **Availability annotations on the new TensorOps overloads.** `get_left_input_cooperative_tensor(src)` etc. appear in the 26.6 header with no visible `API_AVAILABLE`; which OS version actually gates them at runtime?
7. **The SiLU MSL body from 325:191.** Reconstructed; the on-screen source (exact expression, whether it used `precise::exp`, `fast::exp`, or `metal::sigmoid`) is unknown.
8. **The FlashAttention MSL body from 330.** Only the algorithmic outline was narrated; tile sizes, threadgroup config, online-softmax rescaling (whether they used the streaming/online variant), and the `TorchMetalKernel` parameters used are all unknown. **The "TensorOps sample code" download (330:136) presumably contains it.**
9. **"Core AI Debugger" download / distribution.** URL is `https://developer.apple.com/core-ai-debugger/`; whether it is a separate download or bundled with Xcode 27 is not stated.
10. **Changing the debugger's similarity metric.** 330→325:148 says PSNR "can be changed to whichever similarity indicator suits your model best" — the list of available metrics is not given.
11. **Debugger scheme settings.** Whether the target list includes physical iOS devices / simulators, and what "Compute Unit" values are selectable in a comparison session.
12. **`AIProgram.optimize()` parameters.** Every example calls it bare; whether it accepts options (target platform, opt level) is unknown.
13. **`save_asset(path, metadata)`.** The metadata argument appears only in `pipeline.py` via `build_aimodel_metadata(hf_model_id)`; its schema and effect on the asset are unexamined.
14. **The "76% faster" measurement** (325:261) — device, warmup protocol, and whether it's wall-clock for the `text_encode`+`detect` pair vs. all three functions.
15. **The 430 MB figure** (325:97) — whether that is the `.aimodel` on disk or the specialized artifact.
16. **Preset for "4-bit palettization with per-channel scales"** (325:242 says one exists). `KMeansPalettizerConfig.presets.w4()` gives per-*grouped*-channel with `group_size=16` and `enable_per_channel_scale=False` — not obviously "with per-channel scales." Which preset did the presenter mean?
17. **`coreai-build`** — named in the `working-with-coreai` skill and in `docs/Run AI models...` ("compile models ahead of time with the `coreai-build` command-line tool") but **not covered in either transcript**. Flags/usage unknown from these sources.
18. **`coreai_torch.debugging.graph.py` / `debug_info.py` / `search_strategy.py` public surface** — only partially documented in `docs/api/debugging.md`.
19. **MPP "programming guide"** (330:135) — a distinct document from the API reference; not present locally.
