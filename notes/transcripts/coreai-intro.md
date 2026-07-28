# Core AI — Intro Theme Notes (WWDC26 sessions 324 + 326)

**Researcher scope:** deep-read of two WWDC26 transcripts —
- `transcripts/wwdc2026-324.txt` — "Meet Core AI" (presenter: **Ben**, Core AI team) — 189 lines
- `transcripts/wwdc2026-326.txt` — "Core AI app features" / language-learning app w/ ViT + LLM (presenter: **Carina**, Core AI team) — 216 lines

Cross-checked against local Apple docs mirrors in `docs/` and local repo clones in `repos/`.

**Ground rules used in this file**
- Anything in a fenced block labelled **VERBATIM** is quoted exactly from a file I read in this session (path + line numbers given).
- Anything labelled **RECONSTRUCTED** is code that the presenter *described aloud* while it was on screen — the transcript contains no literal code. I reconstructed it from the narration and then grounded each API name against `docs/` or `repos/`. Treat identifiers as verified only where I say so.
- **UNVERIFIED** marks claims I could not corroborate anywhere.

---

## 0. TL;DR — what these two sessions establish

1. **Core AI is a new inference framework + toolchain**, distinct from Core ML, that is "the inference framework powering on-device Apple Intelligence" and is now public (324:8-9).
2. **Model format is `.aimodel`** — a *source*/portable representation, not an executable. It must be **specialized** per device before it can run.
3. **Swift runtime API** is three main types: `AIModel` → `InferenceFunction` → `NDArray`, plus `NDArray.View` / `NDArray.MutableView` non-escapable views.
4. **Python side** is `coreai-torch` (`TorchConverter`, `get_decomp_table()`) + `coreai.runtime` bindings for numeric parity testing, plus `coreai-optimization` for compression.
5. **Tooling**: Xcode `.aimodel` model viewer (General + Functions tabs), **Core AI Debugger** (standalone macOS app), **Core AI debug gauge** (Xcode Debug Navigator), **Core AI instrument** (Instruments), and **`coreai-build`** CLI for ahead-of-time compilation to `.aimodelc`.
6. **Core AI Models repo** (`github.com/apple/coreai-models`) supplies conversion recipes + a Swift package of runtime libraries + agent skills, and **`CoreAILanguageModel` plugs a custom model into the Foundation Models framework's `LanguageModelSession`**.

---

# PART 1 — WWDC2026-324 "Meet Core AI"

Presenter: **Ben**, engineer on the Core AI team (324:1).

## 1.1 Positioning statements (verbatim quotes)

> "Core AI marks the next evolution of on-device AI execution across Apple platforms. It's built from the ground up for modern workloads, and delivers the high-performance inference you need to build advanced AI features." — 324:6-7

> "Core AI is the inference framework powering on-device Apple Intelligence. And now, it's available for you to use, bringing that same power to your app's own intelligence." — 324:8-9

> "Core AI is more than just a framework. It's a complete set of technologies, covering the model deployment lifecycle, from model optimization and conversion to debugging and integration into your app. All designed to support the fast, iterative cycle that building great AI features requires." — 324:10-12

Five pillars, as enumerated (324:13-19):

| Pillar | Quote |
|---|---|
| Hardware | "Core AI allows you to leverage all of Apple Silicon. It provides blazing fast inference across the CPU, GPU, and Neural Engine." (324:13-14) |
| Swift API | "The framework comes with a modern Swift API. It's an expressive API that delivers the performance your app demands without compromising on memory safety." (324:15-16) |
| Python/PyTorch | "The broader set of technologies fit naturally into common ML engineering workflows, reusing familiar Python and PyTorch foundations for model authoring, optimization and conversion." (324:17) |
| Customization | "Core AI also supports extensive customization from fine-grained inference management and model specialization to custom GPU kernels." (324:18) |
| Toolchain | "…tightly integrated into a new developer toolchain, with ahead-of-time compilation, dedicated Core AI Instruments, and a powerful visual Debugger to trace tensor values directly back to your original Python source code." (324:19) |

## 1.2 The declared scaling range (324:20-23)

Three named example workloads, in increasing size:
1. "identify who's talking in a live meeting with a small **speaker diarization model**"
2. "point their camera at anything, ask a question, and instantly get an answer with a larger **vision language model**"
3. "hand off complex, multi-step tasks to a powerful agentic assistant powered by a **70 billion parameter LLM**"

> "With all of it running locally on Apple devices, with no server and no cost per token." — 324:23

**Note the 70B claim.** That is a *stated* upper bound for Core AI on Apple silicon (presumably Mac). No hardware qualifier was given in the transcript. Mark as **worth flagging** — the coreai-models repo's largest catalog entries are `gpt_oss`, `mixtral`, `qwen3_moe`, and `flux2`, and `models/qwen3/README.md` marks Qwen3 8B as macOS-only ("iOS: No").

## 1.3 Talk structure (324:24-27)

1. Get your model into the Core AI format.
2. Integrate the converted model into your app.
3. Optimize model + app performance.
4. Additional features of Core AI and its tools.

## 1.4 The running example: two-player Snake with an AI snake

Setup (324:36-42):
- Two-player snake; one snake driven by a model run through Core AI.
- Traditional rules: grow by eating food; avoid walls, self, and the other snake; last snake standing wins.
- "At each time step, the AI model will see a set of features describing the current board state, and those features will be accumulated into the full game history that gets fed to the model. It will then predict the best direction to move." (324:40-41)
- Key framing: "While snake is a simple game, the tools and APIs used to create this experience are the same foundation that scale all the way up to the larger, more complex use cases." (324:42)

Training (324:43-46):
- Authored in PyTorch, "With a little help from an AI coding assistant I was able to sketch out a simple snake action prediction model pretty quickly."
- "To train it, I used a naive simulation to generate training data, just running the game and recording states and actions."
- Module name given on screen: **`SnakeTransformer`** (324:49).

## 1.5 Conversion step — Python (`coreai-torch`)

### Narration, verbatim (324:47-53)

> "So the next step is taking this PyTorch model and converting it to Core AI.
> I'll use the new Core AI Torch Python package to easily perform the conversion.
> First I'll load the trained checkpoint of the SnakeTransformer module, and prepare a sample input.
> Then I'll export the torch program using torch.export and also make sure to use the **dynamic_shapes** argument to specify that the sequence length of the features is dynamic, that way it doesn't get traced with the static sample length of 5.
> Also I'll run decompositions on the converted program using **Core AI's decomposition table**.
> Next I'll run **Core AI's TorchConverter**, specify the names of the inputs and outputs, and finally **save** the converted Core AI model to disk."

### RECONSTRUCTED conversion script

```python
# RECONSTRUCTED from 324:47-53. API names grounded against
# repos/apple__coreai-torch/README.md and docs/getting-started/quickstart.ipynb.
import torch
from coreai_torch import TorchConverter, get_decomp_table

# 1. Load the trained checkpoint of the SnakeTransformer module
model = SnakeTransformer()
model.load_state_dict(torch.load("snake_transformer.pt"))
model.eval()

# 2. Prepare a sample input — sample sequence length of 5 (stated at 324:51)
sample_features = torch.randn(5, HIDDEN_DIM)

# 3. torch.export with dynamic_shapes so seq-len is NOT baked in at 5
seq = torch.export.Dim("seq")
ep = torch.export.export(
    model,
    args=(sample_features,),
    dynamic_shapes={"features": {0: seq}},
)

# 4. Run decompositions with Core AI's decomposition table
ep = ep.run_decompositions(get_decomp_table())

# 5. Convert, naming inputs and outputs
coreai_program = (
    TorchConverter()
    .add_exported_program(ep, input_names=["features"], output_names=["logits"])
    .to_coreai()
)
coreai_program.optimize()

# 6. Save the converted Core AI model to disk
asset = coreai_program.save_asset(Path("SnakeModel.aimodel"))
```

**Grounding for the reconstruction** — VERBATIM from `repos/apple__coreai-torch/README.md:40-58`:

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

VERBATIM from `repos/apple__coreai-torch/docs/getting-started/quickstart.ipynb` (cell 10):

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

So the transcript's "specify the names of the inputs and outputs" maps exactly to `input_names=` / `output_names=` on `add_exported_program()`. ✅ **Verified.**

The "save the converted Core AI model to disk" maps to **`AIProgram.save_asset(path)`** — VERBATIM from `docs/getting-started/quickstart.ipynb` cell 12:

```python
asset = coreai_program.save_asset(Path(tmpdir) / "quick_start_example.aimodel")
```

And from `docs/coreai-core/tutorials/construct-a-graph.ipynb:164`:
> "`AIProgram.save_asset(path)` writes the program out as an `.aimodel` directory"

⚠️ **Important format fact not stated in the transcript but confirmed in the repo docs: an `.aimodel` is a DIRECTORY, not a single file.** (`construct-a-graph.ipynb:192`: "An `.aimodel` is a directory. List its contents and total size to confirm the …"). Finder/Xcode presents it as a bundle. Transcript 326:78-79 says "we get these `.aimodel` files in Finder" — consistent with a package/bundle presentation.

### `get_decomp_table()` — what it actually does

VERBATIM from `repos/apple__coreai-torch/docs/getting-started/quickstart.ipynb` cell 6:
> "`get_decomp_table()` returns the default PyTorch ATen decomposition table minus the operations that `TorchConverter` lowers as composite ops, so those operations are preserved in the exported graph rather than being decomposed into lower-level primitives."

VERBATIM from `repos/apple__coreai-torch/README.md:36`:
> "Use `get_decomp_table()` so that composite ops (`instance_norm`, `pixel_shuffle`, `scaled_dot_product_attention`) are preserved for optimal runtime performance."

VERBATIM warning, `quickstart.ipynb` cell 8:
> "This call is required when using `add_exported_program()`. Skipping it will leave ops in the graph that have no lowering rule."

VERBATIM warning, `docs/guides/conversion-workflows.ipynb` cell 3:
> "You **must** call `run_decompositions()` before passing the program. Use `get_decomp_table()` to preserve the operations that `TorchConverter` lowers as composite ops."

**GOTCHA:** skipping `run_decompositions(get_decomp_table())` is a hard failure mode, not a perf regression.

### `TorchConverter` API surface (verified from source)

From `repos/apple__coreai-torch/coreai_torch/converter.py`:

```python
class TorchConverter:
    class Mode(Enum):
        DEBUG = "debug"      # includes full torch stack traces for source mapping
        RELEASE = "release"  # records only operation IDs, no stack traces

    def __init__(self, *, mode: "TorchConverter.Mode" = Mode.DEBUG) -> None: ...

    def add_exported_program(
        self,
        exported_program: ExportedProgram,
        *,
        input_names: Sequence[str] | None = None,
        output_names: Sequence[str] | None = None,
        state_names: Sequence[str] | None = None,
        entrypoint_name: str = "main",
    ) -> Self: ...

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
    ) -> Self: ...
```
(converter.py:137-190, 195-248, 249-297 — signatures copied exactly.)

Docstring detail, VERBATIM converter.py:211-217:
```
            input_names: Non-stateful forward() arg names only.
            output_names: Return value names only (not mutation outputs).
            state_names: One name per state, applied to both input and
                mutation output. Order: buffers (registration order), then
                mutated user inputs (signature order). Defaults to FX
                placeholder names when not provided.
```

**KEY: `TorchConverter.Mode.DEBUG` is the DEFAULT.** That means converted assets carry full torch stack traces by default — which is exactly what makes the Core AI Debugger's "trace back to your Python source code" feature work (324:19, 324:138). Docstring says to use `coreai_torch.debugging.debug_info.strip_debug_info` to remove debug metadata from an already-converted program (converter.py:148-150). **Ship-time footgun: you probably want `RELEASE` mode or `strip_debug_info` for release builds** — this was NOT mentioned in the talk.

Also from `coreai_torch/__init__.py:32-39`:
```python
_TORCH_MAX_VERSION = "2.13.0"

if _Version(_torch_version) > _Version(_TORCH_MAX_VERSION):
    _warnings.warn(
        f"coreai-torch has only been validated with torch<={_TORCH_MAX_VERSION}; "
        f"found torch {_torch_version}. Some functionality may not work as expected.",
        stacklevel=2,
    )
```
**Version gate: torch ≤ 2.13.0.**

Public exports (`coreai_torch/__init__.py:22-30`): `__version__`, `ExternalizeSpec`, `MetalParameter`, `TorchConverter`, `TorchMetalKernel`, `get_decomp_table`, `generate_composite_decl`.

Uniqueness constraint on entrypoints (converter.py:180-184, verbatim error string):
```
f"A program with entrypoint_name={entrypoint_name!r} is already staged. "
f"Each staged program must have a unique entrypoint_name."
```
→ This is the mechanism for the multi-function models the talk mentions ("you can convert a single model with multiple functions" — 324:74).

## 1.6 Numeric parity test in Python (before leaving Python)

### Narration, verbatim (324:54-59)

> "Before leaving the Python environment, one more thing I'll do is run a test to verify that the converted Core AI model matches the numerics of my original PyTorch model.
> This can be done easily with the **Core AI framework Python bindings**.
> First I'll load the PyTorch and Core AI models.
> Then prepare a sample snake game input.
> Then run that same input through both the PyTorch module and the **Core AI inference function**.
> And finally assert a sufficiently small delta for my use case between the PyTorch and Core AI outputs."

**This is a strong, repeated recommendation: always numerically validate the converted model against PyTorch before integrating.**

### RECONSTRUCTED parity test

```python
# RECONSTRUCTED from 324:54-59, grounded on coreai-torch quickstart cell 12.
import numpy as np, torch
from coreai.runtime import NDArray

async def verify_parity(coreai_program, torch_model, sample):
    asset = coreai_program.save_asset(Path("SnakeModel.aimodel"))
    async with asset.executable() as ai_model:
        function = ai_model.load_function("main")
        coreai_outputs = await function({"features": NDArray(sample)})
        with torch.no_grad():
            torch_out = torch_model(sample)
        assert np.allclose(torch_out.numpy(), coreai_outputs["logits"].numpy(), atol=1e-4)
```

**Grounding — VERBATIM `repos/apple__coreai-torch/docs/getting-started/quickstart.ipynb` cell 12:**

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
```

**Python runtime API inventory (verified):**
- `from coreai.runtime import InferenceFunction, NDArray` (`docs/coreai-core/tutorials/run-an-aimodel.ipynb:53`)
- `from coreai.runtime import AIModel`; `ai_model = await AIModel.load(asset_path)` (`docs/api/debugging.md`)
- `AIProgram.save_asset(path) -> asset`
- `asset.executable(specialization_options=...)` — async context manager yielding an `AIModel` (`tests/utils.py:591-593`)
- `ai_model.load_function("main") -> InferenceFunction` — **raises `KeyError` if the name is missing** (`construct-a-graph.ipynb:231`). Note: this differs from the **Swift** API, where `loadFunction(named:)` returns `nil`.
- `await function({"name": NDArray(tensor)}) -> dict[str, NDArray-ish]`; outputs have `.numpy()`
- `AIModelAsset.load(...)` "reads the `.aimodel` directory header from disk" (`run-an-aimodel.ipynb:110`)
- `coreai_program._save_bytecode(path)` writes `main.AICode.bc` (private; seen in `tests/utils.py:586`)

## 1.7 Xcode model viewer

### Narration, verbatim (324:60-65)

> "Now that I have the converted AI model, the next step is to hop into Xcode and integrate the model into my app.
> First I'll open the AI model file with Xcode, which shows information about the model.
> It includes the **model size**, the **distribution of operations** and other helpful metadata.
> Also in the **Functions tab** it shows you the exact function signature of each unique function in the model.
> In this case the model just has one function, which takes the features of the game board as an input and produces **logits** as an output which indicate which direction the model thinks would be best to move.
> Also note that the **question mark in the NDArray values denotes that the dimension has a dynamic shape**, which matches how I converted the model with a dynamic sequence length."

### Cross-check vs `docs/Integrating on-device AI models in your app with Core AI.md`

Full agreement, and the doc adds detail the talk omits (doc lines 47-67):

- Selecting the `.aimodel` in the Project Navigator opens the model viewer.
- **General tab**: parameter count, storage size on disk, metadata (description, author, license, creator-defined key-value pairs). "You can edit metadata fields inline; Xcode saves your changes automatically."
- General tab also shows **numeric precision split into compute vs storage**:
  - "Compute types are the representations used during inference."
  - "Storage types are the representations used for the model's weights on disk."
  - "The operation distribution shows a breakdown of operations in the model's graph, sorted by count."
- **Functions tab**: "the exact function signature of each function in the model, including the names, types, and optional descriptions for each input and output."
- Confirms the `?` semantics: "A question mark in an `NDArray` dimension means the dimension is dynamic and is supplied or determined at runtime." ✅ **agrees with 324:65**.

### Xcode project setup gotchas (from the doc; NOT mentioned in either transcript)

VERBATIM, `docs/Integrating on-device AI models in your app with Core AI.md:26-45`:
> Start by adding the model file to an Xcode target:
> 1. Drag the `.aimodel` file from the Finder into the Project Navigator in Xcode, or choose File > Add Files to add it.
> 2. When the sheet appears, select the targets to include the model under Add to targets, then review the remaining options.
> 1. Click Finish.
>
> [!NOTE] After adding the file, you should also see the model in the **Compile Sources** build phase for that target.
>
> ## Add the Metal Toolchain to Xcode
> Core AI model integration in Xcode requires the **Metal Toolchain, which isn't installed by default**. There are two options for adding the Metal Toolchain:
> 1. In Xcode, choose Xcode > Settings > Components > Other Components, then click Get to download and install the Metal Toolchain.
> 1. In Xcode, select any `.aimodel` file in your project and click the Get button in the Metal toolchain download bar that appears.
>
> [!IMPORTANT] If the Metal toolchain isn't included, **builds that include `.aimodel` files fail with a missing Metal compiler error**.

🔥 **Top footgun**: `.aimodel` goes in **Compile Sources**, and the **Metal Toolchain is a separate download** — builds fail without it.

CLI install: `xcodebuild -downloadComponent MetalToolchain` (`docs/Compiling Core AI models ahead of time.md:41`).

## 1.8 The Swift framework — core types

### Narration, verbatim (324:66-78)

> "Now that I've included the AI model file in my Xcode project and have examined its structure, the next step is to use the Core AI framework to run the model.
> The Core AI framework is a new Swift API surface for loading and running Core AI models.
> It offers a **progressively disclosing set of APIs**, which makes it simple to get things up and running, while also having deeper layers of flexibility for supporting performance critical applications.
> Also, it uses modern Swift language features like **non-escapable types**, to offer memory-safe APIs while not sacrificing performance.
> Let's begin by discussing the core types within the framework.
> An **AIModel** is initialized from a URL to a `.aimodel` file and is used primarily to **inspect and load one or more inference functions**.
> An **InferenceFunction** is the runnable object which represents a **single loaded compute graph**.
> In the common case, your AIModel will only have a single main InferenceFunction, though **you can convert a single model with multiple functions**.
> The AIModel and InferenceFunction are typically objects you'll construct when **preparing your app's AI feature. For example this could be on app initialization.**
> **NDArray** is the type which holds your multi-dimensional input and output data and you use the **`run` method on an InferenceFunction** to run inference with that data.
> Finally you can read and process the outputs of the inference."

### Mental model (the "big three")

```
AIModel            ← init from URL to .aimodel; inspect + load functions.  Async init (specialization!)
   └─ loadFunction(named:) → InferenceFunction   ← one loaded compute graph; the runnable thing
                                 └─ run(inputs:) → outputs   ← NDArray in / NDArray out
NDArray            ← multidimensional data container
   ├─ .view()          / .view(as:)          → NDArray.View        (read-only, non-escapable)
   └─ .mutableView()   / .mutableView(as:)   → NDArray.MutableView (write, non-escapable)
```

Verified against `docs/Run AI models in your app on Apple silicon.md` framework index (lines 28-61):

| Group | Symbols |
|---|---|
| Essentials | `AIModel` — "A specialized model for running inference on a device."; `AIModelAsset` — "An unspecialized source model asset." |
| Inference | `InferenceFunction`, `InferenceFunctionDescriptor`, `InferenceValue`, `ImageDescriptor`, `ComputeStream` |
| Multidimensional arrays | `NDArray`, `NDArrayDescriptor` |
| Configuration | `AIModelCache`, `ComputeUnitKind`, `SpecializationOptions` |
| Errors | `AssetError` — "An error that occurs during model asset operations." |

⚠️ **Terminology subtlety the talk glosses over**: `AIModel` = *specialized* model; `AIModelAsset` = *unspecialized source* asset. The talk (324:142-143) describes the same distinction in prose but only ever names `AIModel`.

**Availability** (`docs/Run AI models in your app on Apple silicon.md:12`):
> "Available on: iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta, macOS 27.0+ Beta, tvOS 27.0+ Beta, visionOS 27.0+ Beta, watchOS 27.0+ Beta"

Note watchOS and tvOS are in the list. (324:187: "Core AI is available on all Apple Silicon to help you build cutting edge AI experiences on all Apple platforms.")

**Relationship to Core ML** — VERBATIM `docs/Run AI models in your app on Apple silicon.md:26`:
> "If your app uses model types other than neural networks, such as decision trees or tabular feature engineering, see [Core ML](/documentation/CoreML)."

→ **Core AI = neural networks. Core ML remains for trees / tabular / classical ML.** This is the cleanest statement of the Core AI ↔ Core ML boundary I found; it is *not* stated in either transcript.

## 1.9 `ModelPlayer` — Swift integration code

### Narration, verbatim (324:79-91)

> "So for implementing the snake game, I'll start by making the **ModelPlayer** type.
> At app initialization time, it'll be initialized with the URL to the AI model file that it should use.
> Then it will initialize the AIModel, and **load the main inference function** from it.
> Next is the logic for the model player to make decisions.
> It'll conform to the **SnakePlayer** protocol that I've defined in my app.
> The main protocol requirement is the **chooseAction** function which is passed in the game's history, and returns the next action that the snake should take.
> The first thing to do is create an **NDArray** to populate with the input features.
> For this inference function, the expected structure of the NDArray is **2 dimensional with float32 data, where the first dimension of the shape is the current sequence length, and the second is the fixed hidden dimension size**.
> Then it'll write the features into that NDArray using this **writeFeatures** helper function which takes the game and a **mutable view** of the NDArray.
> The **NDArray.MutableView** type is a **non-escapable type** which provides safe and efficient access to the backing storage of the NDArray.
> After preparing the inputs, it'll run inference with them, and extract the expected output **logits** ndarray.
> The last step is to **sample the output logits** to pick the next direction that the snake will move, by passing an ndarray **view** into the helper function which will read the values and choose the direction with the largest corresponding logit."

### RECONSTRUCTED `ModelPlayer` (v1, no KV cache)

```swift
// RECONSTRUCTED from 324:79-91. Type/method names in the narration are exact
// (ModelPlayer, SnakePlayer, chooseAction, writeFeatures, NDArray.MutableView).
// Call shapes grounded on docs/Integrating on-device AI models in your app with Core AI.md.
import CoreAI

final class ModelPlayer: SnakePlayer {
    private let model: AIModel
    private let function: InferenceFunction

    init(modelURL: URL) async throws {
        // Specialize the model for this device and load it.
        self.model = try await AIModel(contentsOf: modelURL)
        guard let function = try model.loadFunction(named: "main") else {
            throw SnakeError.missingFunction
        }
        self.function = function
    }

    func chooseAction(history: GameHistory) async throws -> Direction {
        // 2-D, float32: [sequenceLength, hiddenDimension]
        var features = NDArray(shape: [history.count, hiddenDimension],
                               scalarType: .float32)

        // Write the board features through a non-escapable mutable view.
        writeFeatures(from: history, into: features.mutableView(as: Float.self))

        var outputs = try await function.run(inputs: ["features": features])

        guard let logitsValue = outputs.remove("logits"),
              let logits = logitsValue.ndArray else {
            throw SnakeError.missingOutput
        }

        return sampleDirection(from: logits.view(as: Float.self))
    }
}
```

**Grounding — VERBATIM `docs/Integrating on-device AI models in your app with Core AI.md:73-83`:**

```swift
import CoreAI

// Specialize the model for this device and load it.
let model = try await AIModel(contentsOf: urlOfModel)

// Load a function from the model.
guard let function = try model.loadFunction(named: "main") else {
    // Handle case where expected function is not found.
}
```

**VERBATIM, same doc, lines 125-168:**

```swift
// Create an `NDArray` that matches the expected type and shape.
var input = NDArray(shape: [3, 4], scalarType: .float32)
```
```swift
// Access a mutable view to write data into the array.
var mutableView = input.mutableView(as: Float.self)
guard let elements = mutableView.contiguousElements else {
    // Handle non-contiguous memory layout.
}

// Your function that writes input data into the mutable span.
writeInputData(into: elements)
```
```swift
// Run the function with the `NDArray` input.
var outputs = try await function.run(inputs: ["input": input])
```
```swift
// Extract the returned output.
guard let predictionValue = outputs.remove("prediction") else {
    // Handle output not found.
}

guard let prediction = predictionValue.ndArray else {
    // Handle output of unexpected type of value.
}

// Read the output data through a view.
// Your function that processes the output.
processOutput(prediction.view())
```

**Verified API facts:**
- `AIModel(contentsOf:)` / `AIModel(contentsOf:options:)` — **`async throws`**, "because specialization needs to complete before a valid `AIModel` is returned" (doc:85).
- `model.loadFunction(named:) throws -> InferenceFunction?` — "throws on a load failure, and returns `nil` when no function with that name exists" (doc:87).
- `model.functionNames` — list all function names (doc:89).
- `function.run(inputs: [String: NDArray]) async throws -> Outputs`; the result type has **`remove(_:) -> InferenceValue?`** (namespaced `InferenceFunction.Outputs.remove(_:)` per doc:152).
- `InferenceValue` has `.ndArray` and `.pixelBuffer` accessors (doc:152).
- `NDArray(shape:scalarType:)`; `NDArray.ScalarType` is an enum with `.float32` (doc:130).
- `NDArray.mutableView(as:)` → `NDArray.MutableView`; `.view()` / `.view(as:)` → `NDArray.View`.
- `MutableView.contiguousElements` → optional span; **can be `nil` for non-contiguous layouts** (doc:137-139).

**VERBATIM design rationale, doc:121:**
> "For `NDArray` values, write input data with `NDArray.MutableView` and read results with `NDArray.View`. **Swift enforces this at compile time.** A mutable view allows writes, and a view allows only reads, so you always know how your data is accessed."

**Concurrency, VERBATIM doc:89:**
> "If your app processes multiple inputs simultaneously, **you can safely call the same inference function from different tasks**."

**Images:** "Values marked as images at conversion time use `CVMutablePixelBuffer`" (doc:119) — i.e. Core AI has an image input concept distinct from NDArray, described by `ImageDescriptor`. Neither transcript covers this.

### Extra `NDArray` API confirmed from `repos/apple__coreai-models`

VERBATIM `repos/apple__coreai-models/swift/Sources/CoreAIShared/Runtime/NDArray+Helpers.swift`:

```swift
/// Fill an NDArray from a collection of elements.
public func fillNDArray<T: BitwiseCopyable>(
    _ array: inout NDArray, as type: T.Type, with elements: some Collection<T>
) {
    var view = array.mutableView(as: type)
    view.copyElements(fromContentsOf: elements)
}

/// Fill an NDArray using a closure that maps index → value.
public func fillNDArray<T: BitwiseCopyable>(
    _ array: inout NDArray, as type: T.Type, count: Int, using generator: (Int) -> T
) {
    var view = array.mutableView(as: type)
    view.withUnsafeMutablePointer { ptr, shape, _ in
        let capacity = shape.product
        precondition(count <= capacity, "fillNDArray: count \(count) exceeds array capacity \(capacity)")
        for i in 0..<count {
            ptr[i] = generator(i)
        }
    }
}

/// Read elements from an NDArray into a new Array.
public func readNDArray<T: BitwiseCopyable>(
    _ array: NDArray, as type: T.Type, count: Int
) -> [T] {
    array.view(as: type).withUnsafePointer { ptr, shape, _ in
        ...
    }
}
```

→ Real member names: **`MutableView.copyElements(fromContentsOf:)`**, **`MutableView.withUnsafeMutablePointer { ptr, shape, strides in }`**, **`View.withUnsafePointer { ptr, shape, strides in }`**, **`NDArray.scalarType`**.

Also from the same file:
```swift
/// `Span` doesn't conform to `Sequence` (non-escapable by design), so `.reduce` isn't available.
extension Span where Element == Int {
    var product: Int { ... }
}
```
🔥 **Footgun:** the `shape` handed to you inside `withUnsafePointer` is a `Span<Int>`, which is non-escapable and **does not conform to `Sequence`** — no `map`/`reduce`/`for-in` over it via Sequence APIs. You must index it manually.

And:
```swift
public func resolvedStrides(descriptor: NDArrayDescriptor, shape: [Int]) throws -> [Int] {
    let resolved = descriptor.resolvingDynamicDimensions(shape)
    return resolved.preferredStrides
}
```
→ **`NDArrayDescriptor.resolvingDynamicDimensions(_ shape: [Int]) -> NDArrayDescriptor`** and **`NDArrayDescriptor.preferredStrides: [Int]`**. Doc comment: "Uses `NDArrayDescriptor.resolvingDynamicDimensions().preferredStrides` to get **framework-blessed strides that respect hardware alignment constraints**." This is exactly the "optimal memory layout" API the talk teases at 324:177.

Also seen: `NDArray(descriptor: resolvedDesc)` initializer (`CoreAISequentialEngine.swift:257`).

### `InferenceFunctionDescriptor` — runtime introspection (doc-only, not in talk)

VERBATIM `docs/Integrating on-device AI models in your app with Core AI.md:97-113`:

```swift
let function: InferenceFunction = ...

let functionDescriptor = function.descriptor
guard let valueDescriptor = functionDescriptor.inputDescriptor(of: "input"),
      case .ndArray(let arrayDescriptor) = valueDescriptor else {
        // Handle input not found, or an unexpected type.
}

guard arrayDescriptor.shape == [3, 4] else {
    // Handle an unexpected shape.
}

guard arrayDescriptor.scalarType == .float32 else {
    // Handle an unexpected scalar type.
}
```

Doc rationale (doc:93):
> "You can use this descriptor to verify that a function accepts the inputs your app provides, or to **dynamically adapt your app's behavior as the model's inputs and outputs change between deployments, without needing to change your code**."

→ `InferenceValue.Descriptor` is an enum with at least a `.ndArray(NDArrayDescriptor)` case. `InferenceFunctionDescriptor` also exposes `inputNames`, `outputNames`, **`stateNames`** (seen used in `CoreAISequentialEngine.swift:211`):
```swift
"CoreAI clean engine initialized — inputs: \(descriptor.inputNames), outputs: \(descriptor.outputNames), states: \(descriptor.stateNames)"
```
And `AIModel.functionDescriptor(for: String) -> InferenceFunctionDescriptor?` (`CoreAIImageSegmenter/ImageSegmentationEngine.swift:55-57`).

## 1.10 The Snake feature vector (324:92-98)

`writeFeatures` populates, in order as narrated:
1. "the normalized distance of the AI snake's head to all the walls"
2. "the normalized relative X and Y distance to the nearest food"
3. "Four elements encoding it's current direction" (one-hot over 4 directions)
4. "the normalized distance to the other snake"
5. "the opponent's direction"

Useful as a concrete example of hand-rolled feature engineering into an `NDArray` — no Vision/image pipeline involved.

## 1.11 First perf problem — quadratic attention

### Narration, verbatim (324:99-108)

> "Now with this put together I'm going to try a test run with both snakes powered by the AI model to see how it does. Running it shows that the model is working. However, I see that **the game is getting slower as it goes on**.
> Alongside the Core AI framework, there's a **new instrument in Xcode** to help you profile the Core AI models running in your app.
> In this case I've ran the app with Instruments and I can see the **inference intervals getting notably larger over time**, which means the inference calls are increasing in latency.
> This makes sense because **transformer models have quadratic time complexity with respect to the sequence length**. And in our game the sequence length is increasing with every move the model makes.
> The next step in this case is to optimize the performance of the model usage.
> Each time the input sequence is increased, the transformer model **recomputes a set of internal key and value embeddings for every element in the sequence**.
> A common strategy used to improve the performance of decoding loops like this when using transformers is to **cache keys and values** that are computed for each element in the sequence, as opposed to re-computing them all from scratch with each inference."

### Core AI **states** — the key concept

VERBATIM 324:109-112:
> "This can be achieved through Core AI by using **states**.
> **States are inputs to the model which are both read, and updated in-place during inference.**
> By introducing the key and value caches as states on the model, we both avoid recomputing them on each inference, and also **remove the need to provide the full history of the game as an input** since the data needed from older steps are stored in the states.
> So after the first input, each subsequent step uses the cache for history and only takes the new features of the latest board state."

**This is the single most important architectural idea in session 324.** States are the Core AI equivalent of Core ML's stateful models / MLState, but authored via `torch.register_buffer` + in-place mutation.

### Authoring change (Python side), narration verbatim 324:113-119

> "To implement the key/value caching, I'll go back to the original authoring code and make a few changes to add in the key and value caches.
> First I'll update the torch module by adding key and value cache tensors as **buffers** within the transformer module, by using the **torch `register_buffer` API**.
> This will later result in these tensors being **mutable buffers in the exported torch program which Core AI will convert to states**.
> Then in the forward function of the module, I'll add the logic to actually use the caches.
> This involves **reading previous features keys and values out of the cache**.
> Then **writing the computed keys and values for the new features back into the cache**.
> Lastly, I'll rerun the same code from before to re-convert the model, but now adding in the **`state_names` argument to the convert call** to specify the names of the new state arguments."

### RECONSTRUCTED stateful `SnakeTransformer`

```python
# RECONSTRUCTED from 324:113-119. register_buffer + in-place mutation pattern
# grounded on repos/apple__coreai-torch/tests/test_stateful.py.
class SnakeTransformer(nn.Module):
    def __init__(self, max_context: int, n_heads: int, head_dim: int):
        super().__init__()
        # Fixed-size caches for the maximum possible context length (324:123)
        self.register_buffer("key_cache",   torch.zeros(max_context, n_heads, head_dim))
        self.register_buffer("value_cache", torch.zeros(max_context, n_heads, head_dim))
        ...

    def forward(self, features, position):
        k_new, v_new = self.compute_kv(features)
        # write new keys/values into the cache (in-place mutation => state)
        self.key_cache[position]   = k_new
        self.value_cache[position] = v_new
        # read the full history back out of the cache
        k = self.key_cache[: position + 1]
        v = self.value_cache[: position + 1]
        ...
        return logits
```

Re-conversion adds `state_names`:

```python
coreai_program = (
    TorchConverter()
    .add_exported_program(
        ep,
        input_names=["features"],
        output_names=["logits"],
        state_names=["key_cache", "value_cache"],   # <-- new (324:119)
    )
    .to_coreai()
)
```

**Grounding — VERBATIM `repos/apple__coreai-torch/tests/test_stateful.py:58-64`:**

```python
        class _BufMutate(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.register_buffer("state", torch.zeros(1, 4))

            def forward(self, x: Tensor) -> Tensor:
                self.state.copy_(x)
                return self.state
```

**VERBATIM, resulting Core AI IR (test_stateful.py:88-95), showing how a mutable buffer becomes a state:**

```
// CHECK-LABEL: module {
// CHECK-NEXT:   coreai.graph @main(%{{.*}}: tensor<1x4xf32> {MutableBuffers.buffer_mutation = "b_state", coreai.name = "b_state"}, %{{.*}}: tensor<1x4xf32> {coreai.name = "x"}) -> (tensor<1x4xf32> {coreai.name = "b_state"}) {
// CHECK:     coreai.output %{{.*}} : tensor<1x4xf32>
// CHECK:   }
// CHECK: }
```

**VERBATIM, `state_names` usage (test_stateful.py:113-116):**
```python
            .add_exported_program(
                program, state_names=["custom_buf"], input_names=["custom_x"]
            )
```
Resulting IR: `{MutableBuffers.buffer_mutation = "custom_buf", coreai.name = "custom_buf"}`.

Also confirmed in the tests: a state named `kv_cache` (test_stateful.py:878), multiple states (`state_names=["my_buf", "my_y"]`, line 479/734), and that states can come from **mutated user inputs** as well as buffers.

🔥 **GOTCHA (from `coreai_torch/_utils.py:1700-1856`):**
- `user_state_names` must have exactly one entry per graph state or you get:
  ```
  f"Graph has {len(graph_state_names)} stateful inputs "
  f"({graph_state_names}), but state_names has "
  f"{len(user_state_names)} entries ({list(user_state_names)})."
  ```
- Ordering matters, per the converter docstring: **"Order: buffers (registration order), then mutated user inputs (signature order)."**
- There is a defensive warning path: `"documented state_names ordering — pass state_names explicitly "` (_utils.py:1841) — i.e. when the converter can't confidently derive ordering it tells you to pass `state_names` explicitly.
- `input_names` covers **non-stateful** args only; `output_names` covers **return values only, not mutation outputs** (test_stateful.py:629, 679: "Buffer mutation output is handled by `state_names`; `output_names` covers only non-state.").

### App-side change (Swift), narration verbatim 324:120-127

> "Now that I've re-converted the model with the new function signature, I'll update the app code to handle it.
> To start, I'll update the ModelPlayer to **store the key and value cache NDArrays** which will be the state arguments passed to each inference.
> I'll initialize them with the expected shape for the transformer.
> In this case I converted the model such that it expects the key and value caches to always be a **fixed size for a maximum possible context length**.
> Then when it's time to run inference, I'll construct a **collection of MutableViews** containing both views of the key and value caches.
> Then provide those as the **`states` argument of the `InferenceFunction.run` method**.
> Now the caches will be both read and updated in-place during each inference."

### RECONSTRUCTED `ModelPlayer` (v2, stateful)

```swift
// RECONSTRUCTED from 324:120-127.
// The `InferenceFunction.MutableViews` type + `.insert(_:for:)` + `consume` pattern is
// VERIFIED against repos/apple__coreai-models CoreAISequentialEngine.swift.
final class ModelPlayer: SnakePlayer {
    private let model: AIModel
    private let function: InferenceFunction
    private var keyCache: NDArray
    private var valueCache: NDArray

    init(modelURL: URL) async throws {
        self.model = try await AIModel(contentsOf: modelURL)
        guard let function = try model.loadFunction(named: "main") else { throw ... }
        self.function = function
        // Fixed-size caches sized for the maximum possible context length.
        self.keyCache   = NDArray(shape: [maxContext, nHeads, headDim], scalarType: .float32)
        self.valueCache = NDArray(shape: [maxContext, nHeads, headDim], scalarType: .float32)
    }

    func chooseAction(history: GameHistory) async throws -> Direction {
        var features = NDArray(shape: [1, hiddenDimension], scalarType: .float32)
        writeFeatures(from: history.latest, into: features.mutableView(as: Float.self))

        var states = InferenceFunction.MutableViews()
        states.insert(&keyCache,   for: "key_cache")
        states.insert(&valueCache, for: "value_cache")

        var outputs = try await function.run(
            inputs: ["features": features],
            states: consume states
        )
        ...
    }
}
```

**Grounding — VERBATIM `repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAISequentialEngine.swift:275-291`:**

```swift
        // Build states (KV cache — persistent, inout)
        var states = InferenceFunction.MutableViews()
        states.insert(&keyCache, for: keyCacheName)
        states.insert(&valueCache, for: valueCacheName)

        // Build output backings (logits — written in-place)
        var outputViews = InferenceFunction.MutableViews()
        outputViews.insert(&logitsArray, for: logitsName)

        // Execute
        _ = try await function.run(
            inputs: [inputIdsName: inputIdsArray, positionIdsName: positionIds],
            states: consume states,
            outputViews: consume outputViews
        )
```

✅ **Full signature verified: `InferenceFunction.run(inputs:states:outputViews:) async throws`.**
`InferenceFunction.MutableViews` is a non-escapable collection built with `insert(_ array: inout NDArray, for name: String)` and passed with Swift's `consume` operator.

Also seen (`SpeechModel.swift:81`): passing an **empty** `InferenceFunction.MutableViews()` when there are no states:
```swift
states: InferenceFunction.MutableViews(), outputViews: consume out)
```

### Result

VERBATIM 324:128-130:
> "Now with the updated model, I'll re-run the app. This time I can see it **maintains a steady speed, no longer slowing down overtime**.
> When tracing the updated app in Instruments, I can confirm that the **inference latency is growing at a much slower rate**."

⚠️ Note the careful hedge: **"growing at a much slower rate"**, not "constant". With a fixed-size cache and a growing attention window, per-step cost still grows linearly.

## 1.12 Advanced authoring pointer (324:131-136)

> "When converting the snake game models, I used the **coreai-torch package** to directly convert the PyTorch module. This flow is simple and works great for many use cases, but sometimes you may need more control over how your model is authored, and potentially even how the operations within the model are run.
> We've only touched the surface of what the Core AI Python package has to offer. It also has support for **directly authoring your model with Core AI APIs**, **optimizing the model for Apple Silicon**, and **defining custom kernel implementations with Metal 4**.
> To learn more about these advanced model authoring flows, see the talk **'Dive into Core AI model authoring and optimization'**."

→ That's WWDC2026-325 (also present at `transcripts/wwdc2026-325.txt`; covered by another agent).
Repo confirmation of the three pieces: `coreai_torch.composite_ops`, `register_torch_lowering`, `TorchMetalKernel` — VERBATIM `repos/apple__coreai-torch/README.md:3`:
> "Use it to bring up an existing PyTorch model into Core AI IR, or to author Core AI models directly from PyTorch by composing the built-in composite op library (`coreai_torch.composite_ops`), authoring new ops via `register_torch_lowering`, and authoring inline Metal GPU kernels via `TorchMetalKernel`."

## 1.13 Core AI Debugger + debug gauge (324:137-140)

VERBATIM:
> "In addition to debugging performance, it's also crucial to be able to **debug the numerics** of your converted model.
> For this you can use the **Core AI Debugger** which allows you to **visualize your converted model**, **easily inspect intermediate tensor values**, and **trace back operations in the converted model to the Python source code which introduced them**.
> There is also a convenient **Core AI debug gauge** which shows you **streaming Core AI activity while your app is running in Xcode**.
> This is a great place to **spot performance issues before jumping into instruments**."

**Three-tool split (recommendation):**
| Tool | Purpose | Where |
|---|---|---|
| Core AI Debugger | numerics / graph visualization / trace-to-Python | standalone macOS app (`developer.apple.com/core-ai-debugger/`) |
| Core AI debug gauge | live streaming activity, first-look perf triage | Xcode Debug Navigator |
| Core AI instrument | detailed inference interval profiling | Instruments |

Doc corroboration, VERBATIM `docs/Run AI models in your app on Apple silicon.md:22-24`:
> "Prepare your models for Apple silicon with [Core AI Optimization](https://apple.github.io/coreai-optimization), then convert them into the `.aimodel` format with [Core AI PyTorch Extensions](https://apple.github.io/coreai-torch). The **[Core AI Debugger](https://developer.apple.com/core-ai-debugger/) app** supports visualization and numeric debugging, letting you **inspect model structure and trace tensor values directly back to your Python source code**.
> Core AI also integrates with Xcode and the developer toolchain. The **Core AI debug gauge** and **Core AI instrument** help you monitor and profile inference performance in your app. You can also compile models ahead of time with the `coreai-build` command-line tool."

✅ Full agreement between transcript and framework landing doc. The doc adds a fourth landing article: **"Inspecting, debugging, and profiling Core AI models"** (`/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models`) — **not present in the local `docs/` mirror**; only a third-party summary exists locally (see §4.3).

**How trace-to-Python is implemented** (mechanism, from `coreai-torch` source): `TorchConverter.Mode.DEBUG` (the default) sets `include_stack_trace=True` on a `_DebugInfoRecorder`, which "preserves location and module-stack information for debugging" (README.md:11). Converted IR carries `coreai.name` attributes and torch stack traces. Intermediate captures are saved as `*.aimodelintermediates` files — VERBATIM `repos/apple__coreai-torch/docs/api/debugging.md:273`:
```python
debug_trace = load_intermediates(Path("./debug_output/main.aimodelintermediates"))
```

**Preview-era env vars** — VERBATIM `repos/apple__coreai-torch/docs/api/debugging.md:5-12`:
> "During the current preview, set the following environment variables to ensure operation-level debug metadata is preserved and available to these tools:
> ```bash
> export USE_LOCAL_COREAI=1
> export ENABLE_DEBUG_INFO=1
> ```"

🔥 **Big gotcha not mentioned in either talk.** Without these env vars during the preview, op-level debug metadata may not be preserved and the debugger tooling degrades.

## 1.14 Specialization — the deep dive (324:141-174)

### What specialization is, VERBATIM 324:141-147

> "One thing that was glossed over in the snake game implementation is the process of **model specialization**.
> When you **ship an AI model with your app, that is a source representation of the model, which can be run on any Apple device**.
> However, **to actually load and run the model within your app, it must be specialized for the device that the app is running on**.
> When your model is loaded it is **checked to see if it has already been specialized and cached**.
> The specialization process **can take a significant amount of time for very large models**.
> While future loads are from the cache and fast, **that first time is something you may need to plan for**.
> **It is recommended you avoid having model specialization occur within user interactive flows.**"

☝️ That last line is the headline recommendation of both talks.

### Core AI's three levers (324:148-161)

**Lever 1 — check the cache first:**
> "First, Core AI gives you **programmatic access to the default model cache for your app**. You can **request to load models directly from it**. If **nil is returned, it is not present and requires specialization**. You can use this to **gate features or inform the users that they may need to wait a bit while your app prepares the model**." (324:149-152)

**Lever 2 — explicit pre-specialization:**
> "Second, you can **request model specialization explicitly in your app independent of it being loaded**. You can do this **after downloading assets or when the user opts in to a feature** so the model is ready to go ahead of time." (324:153-154)

**Lever 3 — options + cache management:**
> "And there is a lot more control available. **SpecializationOptions** help configure how you want your model to be optimized for inference.
> With the **AIModelCache** you can also **delete entries you no longer need**, and **control the policy on how long entries persist**.
> You can even **share a cache between multiple apps in the same app group**.
> Check out the **'Managing model specialization and caching' article on developer.apple.com** to learn more." (324:155-161)

### RECONSTRUCTED → then VERIFIED against the doc

The doc `docs/Managing model specialization and caching.md` matches point-for-point. VERBATIM, doc:28-45:

```swift
func loadModel(from modelURL: URL) async throws -> AIModel {
    // The default cache stores all specialized assets for your app bundle.
    let cache = AIModelCache.default

    // A non-`nil` result means the model was previously specialized and cached.
    if let model = try cache.model(for: modelURL, options: .default) {
        return model
    }

    // No cached specialization exists. Inform the person and specialize now.
    Task { @MainActor in
        informUser("Preparing AI features. This may take a while…")
    }

    // This call performs specialization, caches the result, and returns the model.
    return try await AIModel(contentsOf: modelURL, options: .default)
}
```
✅ exactly Ben's "Lever 1", including the nil semantics.

VERBATIM doc:66-76 (Lever 2):
```swift
guard let localModelURL = try await downloadModel(forFeature: feature) else {
    throw AppError.failedToDownloadModel(feature)
}

// Specialize the model so it's ready before the person needs it.
try await AIModel.specialize(contentsOf: localModelURL, options: .default)

// The model is now specialized and cached. Future loads skip specialization.
let model = try await AIModel(contentsOf: localModelURL, options: .default)
```

Full signature per the doc's link text: **`AIModel.specialize(contentsOf:options:cache:cachePolicy:)`**.

VERBATIM doc:83 — the crucial distinction:
> "The `specialize` method **differs from ahead-of-time compilation**. With ahead-of-time compilation, most of the heavy computation happens on your Mac at build time, so on-device specialization finishes faster. With `specialize`, **the full specialization process runs on the person's device. You are controlling *when* specialization happens, not reducing the work it does.**"

**`SpecializationOptions`** (doc:52-60):
- `.default` — "the system selects the combination of compute units (CPU, GPU, and Neural Engine) to **minimize inference latency**"
- `.cpuOnly` — "restrict specialization to CPU only"
- `init(preferredComputeUnitKind:)` — prefer a specific compute unit
- Rationale quote: "if your app runs a small model in the background, use `.cpuOnly` to avoid competing with foreground GPU work."
- Warning: "In most scenarios, the default configuration offers the best performance, so **test your app's performance carefully before overriding it**."
- `ComputeUnitKind.availableKinds` — "Because not all devices have the same compute units available, check what's available."

Extra `SpecializationOptions` members found in the wild — VERBATIM `repos/apple__coreai-models/swift/Sources/CoreAIShared/Runtime/ModelStructure.swift:70-81`:
```swift
    public var specializationOptions: SpecializationOptions {
        switch self {
        case .chunkedStatic, .multiFunctionSegmenter:
            return SpecializationOptions(preferredComputeUnitKind: .neuralEngine)
        case .dynamic:
            var opts = SpecializationOptions(preferredComputeUnitKind: .gpu)
            opts.expectFrequentReshapes = true
            return opts
        }
    }
```
→ **`SpecializationOptions.expectFrequentReshapes: Bool`** (mutable property) and **`ComputeUnitKind.neuralEngine` / `.gpu`**. `expectFrequentReshapes` is not in either talk or in the local docs — real API, undocumented locally. Apple's own sample picks `.neuralEngine` for static-shape/chunked models and `.gpu + expectFrequentReshapes` for dynamic-shape LLMs.

**`AIModelCache`** (doc:85-161):
- `AIModelCache.default`
- `cache.model(for:options:) throws -> AIModel?` (does **not** specialize)
- `cache.deleteEntries(for: URL) throws`
- `AIModelCache.Policy` with a `.persistent` case; default policy "allows the system to reclaim storage when needed by deleting assets under both storage pressure and source model changes."
- `AIModelCache(appGroup: String)` → `AIModelCache?` — returns nil on "Invalid group identifier or entitlement"; requires `com.apple.security.application-groups`.
- "If an `AIModel` instance still uses a cache entry, Core AI **defers deletion until that instance is deallocated**."

**Bookmarks (doc:163-207)** — this whole mechanism is absent from both talks and is important:
```swift
// Specialize and keep a reference to the model.
let model = try await AIModel.specialize(
    contentsOf: llmURL,
    options: .default,
    cachePolicy: .persistent
)

// Save bookmark data to restore access after the app exits.
let bookmarkData = model.bookmarkData
UserDefaults.standard.set(bookmarkData, forKey: "llm.bookmark")
```
```swift
if let bookmarkData = UserDefaults.standard.data(forKey: "llm.bookmark") {
    do {
        if let model = try AIModel(resolvingBookmark: bookmarkData) {
            // Use the model.
            return model
        }
        // The model can't be found or was invalidated by an OS update.
    } catch {
        // The bookmark data is invalid.
    }
}
```
🔥 **Gotcha (doc:165):** "The unspecialized `.aimodel` file, along with the `SpecializationOptions` you pass, is what Core AI uses to **index and retrieve the cached specialization** at runtime… Because of this, **you can't simply delete the source file and expect those APIs to keep working.**" Use `AIModel.bookmarkData` + `AIModel(resolvingBookmark:)` if you want to delete the source `.aimodel` to reclaim storage.
🔥 And (doc:207): "Bookmark data doesn't prevent removing assets from the device. If the system purges the assets, you manually delete them, **or an OS update invalidates them**, your app can't resolve the bookmark and needs to download and specialize the model again."

### What specialization actually does — the two-phase story

VERBATIM 324:162-173:
> "Independent of when specialization occurs, it still takes time. Lets take a quick peak inside.
> During specialization, the model goes through **two main transformations**.
> **First, it goes through a core set of compilation steps which segment, plan and optimize compute.**
> **Second, executable artifacts are generated for the compute units used. These artifacts are tied to the device and OS version they were generated on.**
> Of these two steps, **compilation is the one which incurs most of the latency**.
> The Core AI toolchain can help you reduce that time by **allowing some compilation to occur ahead of time on your development machine, producing a compiled version of the model**.
> While that compiled model **still needs to be specialized for the specific users device**, there is now much less work to do and finishes significantly faster.
> To learn more about this option, check out the **'Compiling Core AI models ahead of time' article on developer.apple.com**."

Carina repeats this nearly word-for-word at 326:155-162 — see §2.9. The two descriptions are consistent.

**Three-word summary of phase 1:** *segment, plan, optimize compute.*

## 1.15 Low-level inference optimization APIs (324:175-181)

VERBATIM:
> "Another area you may want to optimize is **removing any overheads in tight inference loops** using your model. The Core AI Framework has several APIs to help you here.
> 1. You can **dynamically check the optimal memory layout of NDArray arguments and allocate them with that structure to avoid layout conversions at inference time**.
> 2. You can also **pre-allocate output values for the framework to write into, to avoid allocating new output values during inference**.
> 3. And you can also use **asynchronous values to efficiently pipeline execution of multiple inference functions together**.
> For most use cases, the higher-level inference APIs will get you exactly where you need to be. But when you're **optimizing a tight inference loop or integrating a model into a complex compute pipeline**, these lower-level APIs are there when you need them."

### Mapping each of the three to real API (verified in `apple/coreai-models`)

**(1) Optimal memory layout** → `NDArrayDescriptor.resolvingDynamicDimensions(_:)` + `.preferredStrides`, then `NDArray(descriptor:)`.
VERBATIM `swift/Sources/CoreAIShared/Runtime/NDArray+Helpers.swift:12-19`:
```swift
/// Resolve strides from an NDArrayDescriptor for a given concrete shape.
///
/// Uses `NDArrayDescriptor.resolvingDynamicDimensions().preferredStrides` to get
/// framework-blessed strides that respect hardware alignment constraints.
public func resolvedStrides(descriptor: NDArrayDescriptor, shape: [Int]) throws -> [Int] {
    let resolved = descriptor.resolvingDynamicDimensions(shape)
    return resolved.preferredStrides
}
```

**(2) Pre-allocated outputs** → the `outputViews:` parameter of `run`.
VERBATIM `CoreAISequentialEngine.swift:281-291` (already quoted above): `outputViews.insert(&logitsArray, for: logitsName)` then `outputViews: consume outputViews`.
Also, the perf reasoning in Apple's own sample, VERBATIM `CoreAISequentialEngine.swift:252-255`:
```swift
        // Reuse pre-allocated input_ids when the batch size is unchanged.
        // Steady-state decode keeps batchSize=1 forever, so this avoids the
        // `NDArray(descriptor:)` + `resolvingDynamicDimensions` work on every
        // step — small per call, but compounds over long generations.
```

**(3) Asynchronous values / pipelining** → `InferenceFunction.AsyncValue`, `InferenceFunction.AsyncMutableValue`, `InferenceFunction.AsyncMutableViews`, `ComputeStream`, and **`InferenceFunction.encode(inputs:states:outputViews:to:)`**.
VERBATIM `swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAIPipelinedEngine.swift:592`:
```swift
        let computeStream = ComputeStream(commandQueue: pipelineQueue)
```
VERBATIM `CoreAIPipelinedEngine.swift:707-741`:
```swift
        let tokenValue: InferenceFunction.AsyncValue
        if tokens.isEmpty {
            // Decode: read input token from previous step's decode output buffer
            tokenValue = unsafe InferenceFunction.AsyncValue(
                unsafeBuffer: decodeOutputBuffers[(step + pipelineDepth - 1) % pipelineDepth],
                byteOffset: 0,
                scalarType: .int32,
                shape: tokenShape,
                strides: tokenStrides
            )
        } else {
            ...
        }
        let asyncInputs: [String: InferenceFunction.AsyncValue] = [
            inputIdsName: tokenValue,
            positionIdsName: posValue,
        ]
```
VERBATIM `CoreAIPipelinedEngine.swift:743-766`:
```swift
        // Build States as AsyncMutableValue (KV cache, in-place update)
        var keyState = unsafe InferenceFunction.AsyncMutableValue(
            unsafeBuffer: keyBuffer,
            byteOffset: 0,
            scalarType: keyCacheScalarType,
            shape: keyShape,
            strides: keyStrides
        )
        ...
        var asyncStates = InferenceFunction.AsyncMutableViews()
        asyncStates.insert(&keyState, for: keyCacheName)
        asyncStates.insert(&valState, for: valueCacheName)
```
VERBATIM `CoreAIPipelinedEngine.swift:789-800`:
```swift
        // Encode inference using the public encode() API.
        // This commits + uses runAfterSyncPoint (no stream wait) — enables true pipelining.
        let _ = try function.encode(
            inputs: asyncInputs,
            states: consume asyncStates,
            outputViews: consume asyncOutputs,
            to: computeStream
        )
```

✅ So "asynchronous values" = `AsyncValue` / `AsyncMutableValue`, built directly over **`MTLBuffer`s** (`unsafeBuffer:` label + Swift 6 `unsafe` expression), submitted via **`InferenceFunction.encode(... to: ComputeStream)`** — a *non-blocking encode* rather than `run`'s await. `ComputeStream(commandQueue: MTLCommandQueue)`.

**Verified constructor signature:** `InferenceFunction.AsyncValue(unsafeBuffer:byteOffset:scalarType:shape:strides:)` and the same for `AsyncMutableValue`.

## 1.16 Core AI Models repository (324:182-186)

VERBATIM:
> "Whether you're just getting started or diving deep, the **Core AI Models repository** is a great place to find what you need.
> It has a **collection of popular models, each just a single command away from being converted and optimized for your app**.
> **AI skills that are experts in Core AI model authoring, optimization, and conversion.**
> And a **Swift package with libraries for specific families of models that give you higher-level APIs that already have many of those low-level inference optimizations built in**.
> It also provides an API for **creating a Core AI Language model, which plugs right in to the Foundation Models framework, letting you bring your own custom models and token sampling strategies**."

☝️ **That last sentence is the Core AI ↔ Foundation Models bridge**, and it's the seam session 326 builds its whole app on.

### Verified against the real repo (`repos/apple__coreai-models`)

Directory contract, VERBATIM `README.md`:
| Directory | What's inside |
|---|---|
| `models/` | Model catalog with README and export recipes. |
| `python/` | Python primitives for authoring and utilities for exporting models. |
| `swift/` | Swift package (`coreai-models`): runtime utilities to integrate Core AI models in your app. |
| `skills/` | Pluggable skills that enable coding agents to leverage Core AI more effectively. |

**Requirements**, VERBATIM README:
> - **macOS and iOS 27.0+**
> - **Xcode 27.0+**

**Discovery CLI**, VERBATIM README:
```bash
git clone https://github.com/apple/coreai-models.git && cd coreai-models
uv run coreai.model.registry --list-models
```
> "Run `uv run coreai.model.registry --help` for details."

**Agent skills** (matches "AI skills that are experts in…"), VERBATIM README table:
| Skill | Description |
|---|---|
| `working-with-coreai` | End-to-end workflow for deploying PyTorch models on Apple silicon, covering export with `coreai-torch` and running with the Core AI runtime. |
| `model-authoring` | Empirical rules for authoring PyTorch models for on-device execution on Apple platforms, covering BC1S layout, op compatibility, KV cache patterns, precision rules, MoE, and common issues. |
| `model-compression-exploration` | Systematically explore weight compression configurations (quantization and palettization) for a PyTorch model using `coreai-opt`. |

Install for Claude Code, VERBATIM README:
```
/plugin marketplace add git@github.com:apple/coreai-models.git
/plugin install coreai-skills@coreai-models
```
Also documented: `codex plugin marketplace add https://github.com/apple/coreai-models`, and `gemini extensions install /path/to/coreai-models/skills`.

**Model catalog** (`models/` dir listing, verified): `clap, clip, depth-anything, edsr, efficient-sam, flux2, gemma3, gpt_oss, mistral, mixtral, pvt, qwen2, qwen3, qwen3_moe, roberta, sam3, stable-diffusion, t5, vlm, wav2vec2, whisper, yolo`.

**Swift package products** (VERBATIM `Package.swift`):
```swift
let package = Package(
    name: "coreai-models",
    platforms: [.macOS("27.0"), .iOS("27.0")],
    products: [
        .library(name: "CoreAILM",             targets: ["CoreAILanguageModels"]),
        .library(name: "CoreAIDiffusion",      targets: ["CoreAIDiffusionPipeline"]),
        .library(name: "CoreAISegmentation",   targets: ["CoreAIImageSegmenter"]),
        .library(name: "CoreAISpeech",         targets: ["CoreAISpeech"]),
        .library(name: "CoreAIObjectDetection",targets: ["CoreAIObjectDetector"]),
    ],
```
Dependencies (VERBATIM): `apple/swift-argument-parser` (from 1.2.0), `huggingface/swift-transformers` (from 1.1.0), `mlc-ai/xgrammar` (branch `main`).
Executable CLI targets: `llm-runner`, `image-segmenter`, `object-detector`, `diffusion-runner`, `speech-runner`, `llm-benchmark`.
Swift settings used throughout: `.enableUpcomingFeature("MemberImportVisibility")`; `CoreAILanguageModels` also `.define("CXGRAMMAR_IMPORT")` and `.linkedLibrary("c++")`.

**Contribution policy footgun**, VERBATIM README:
> "### We are not accepting code contributions at this time … **If you open a pull request, it will be closed.**"

## 1.17 Closing (324:187-189)

> "Core AI is available on all Apple Silicon to help you build cutting edge AI experiences on all Apple platforms.
> It has tight integration with the existing Python tools that you're already familiar with, a modern Swift framework for running your models efficiently within your app, and state of the art debugging tools to help you understand how your models are running on Apple devices."

---

# PART 2 — WWDC2026-326 "Core AI app features" (ViT + LLM language-learning app)

Presenter: **Carina**, Core AI team (326:1).

Prerequisite call-out (326:8-9): "If you haven't already, check out **'Meet Core AI'**. You will learn the high-level ideas behind our framework and design philosophy and the best ways to use our APIs."

## 2.1 The pitch (326:5-7, repeated at 326:211-212)

> "With Core AI, you can build app experiences where **user's data never leaves their device**. There's **no server to manage, no cost per token, and no latency to the cloud**."

(Verbatim at both 326:6-7 and 326:211-212 — a deliberate bookend.)

## 2.2 The app + the problem

- iOS app for students learning vocabulary in a new language, "starting with **Mandarin Chinese**" (326:11).
- Existing state: hand-curated vocab cards (word, translation, example usage). "But this is **hard to scale**. I would need to include all of these statically in my app." (326:13-14)
- The AI idea (326:16-20): "How cool would it be if students could **point their camera at something** they see in their garden, or an object on the street, and just **ask the app to pull it right out of the scene**? From that, it generates a vocab card in the language they're learning. **No curated deck can keep up with a curious student. But a camera and an on-device model can.**"

Talk agenda (326:22-25):
1. model discovery
2. write the code to use those models in the app
3. practical considerations of model deployment
4. macOS version, reusing the same code + larger models

## 2.3 Model discovery — the method (this is the most reusable part)

**Step 1: define core capabilities** (326:27-31):
- Input = picture + a prompt from the user about what they want to learn.
- "the app needs to **highlight and extract** what the user requested from the image. This **segmented image becomes the graphic on the card**."
- "from the text input in their native language, the app will **reason about the word and generate all the vocab information**: the translation, the natural example usage in the language being learned, and the English meaning of that usage."

**Step 2: three explicit requirements** (326:32-40):
| # | Requirement | Quote |
|---|---|---|
| 1 | **Content** | "This app is about real-world learning, so it needs to handle settings like kitchens, streets, and offices." |
| 2 | **Languages** | "The model architecture needs to support multiple languages from the start. For my initial release, I'm scoping to Mandarin Chinese." |
| 3 | **Device constraints** | "Everything runs on-device on iPhone, so I need to keep both **storage and memory footprint small**. That means being deliberate about **model size and how many models I ship**." |

**Step 3: research method** (326:41):
> "I explored a few directions here, **reading through model documentation, running some prototypes, and bouncing ideas off an AI assistant**."

**Step 4: the architectural decision — decompose into two small models** (326:42-46):
> "The conclusion was clear: **decompose the problem into two small models**.
> The first is a dedicated **vision model that handles image segmentation**. The second is a **multi-lingual large language model** that takes that English label and generates vocab, translation, and example sentences.
> **Why two models on device? Task-specific models give me better quality, smaller individual sizes, and the ability to upgrade them independently.**
> I'm targeting **variants under one billion parameters each**, which keeps the total on-device footprint manageable."

🔑 **This is the presenter's central architectural recommendation:** prefer *two small task-specific models* over one large general model, for (a) quality, (b) size, (c) independent upgradeability.

### Vision model choice: **SAM 3**

VERBATIM 326:47-52:
> "For image segmentation, I am interested in **SAM 3, the Segment Anything Model 3**. SAM 3 is a **vision-transformer-based model for promptable image segmentation**. It's a powerful model that does exactly what my app needs. A student points their camera at something and SAM 3 **isolates the object according to their prompt precisely**. It provides a **clean cutout for the card graphic**. **The prompt can provide an English label for the language model.**"

☝️ Note the neat design trick: the *same* user text prompt serves double duty — segmentation prompt AND the English label fed to the LLM.

### LLM requirements — four criteria (326:53-58)

> "an English label like **'Hummingbird'** goes in, and the model generates vocab information in the target language. So I need four things.
> **Multilingual**, so it handles translations accurately.
> **Reasoning**, so I get contextual example sentences.
> **Structured output**, so it fills typed fields reliably.
> And **compact**, so it fits on device alongside the vision model."

### LLM choice: **Qwen** (326:59-64)

> "Many open source language models have strong reasoning capabilities in this size range. I did some quick tests and **Qwen stood out — it supports one hundred nineteen languages and dialects, and it is a reasoning model**, which means it can **generate contextual examples, not just translations**. A great starting point for vocab card generation.
> There is even a **0.6 billion parameter version** of the model, which should work great for my app.
> **I found these models and documentation about them on HuggingFace and GitHub.**"

## 2.4 Two paths to get a model into Core AI (326:65-76)

VERBATIM:
> "One path is to **convert them directly from their PyTorch representation using the Core AI PyTorch extensions package**.
> I could also incorporate **model compression with the Core AI optimization package**. To learn more about this process, check out the talk **'Dive into Core AI model authoring and optimization'**. **In that section we even show how to convert the SAM 3 model!**
> Core AI has powerful tools for model optimization, conversion, and even direct authoring. **However, for many popular models there is an another path.**
> The **Core AI Models repo** is a great resource to check out. It contains many popular models, each with **conversion scripts that yield optimized versions of those models in the Core AI format, along with optional platform specific variants**.
> …
> **`models/` is the catalog.** Browse what's available, find the model you want, and **follow its export recipe**. **`python/` gives you reusable primitives and utilities for exporting.**
> Here I found the SAM 3 and Qwen family models, and I followed the export recipe to get our Core AI models."

✅ Matches the real repo README table exactly (§1.16).

### The actual export recipes (verified in the repo)

**SAM 3** — VERBATIM `repos/apple__coreai-models/models/sam3/README.md`:
```sh
uv run export.py
```
> "Saves to `<repo-root>/exports/<model>_lite_<image-size>_w<n-bits>_static/` as a bundle directory containing `<...>.aimodel`, a `tokenizer/` folder, and a `metadata.json` (**segmenter bundle, schema 0.2**). Pass `--output-dir <path>` to override the destination."

Flags (VERBATIM table): `--full`, `--output-dir`, `--output-name`, `--image-size` (336 lite / 1008 full), `--max-text-seq-len` (default 32), `--n-bits`, `--group-size`, `--dtype` (`float16`|`float32`, default `float32`, only with `--full`), `--overwrite`, `--dry-run`.
> "`image-size=336` is the resolution we recommend for iOS deployment."

⚠️ **Gated model:** "SAM3 is a gated model on Hugging Face (HF). You will need to accept the terms of the license, generate a HF token, and add your HF token to your machine before exporting this model." → `brew install hf; hf auth login --token <YOUR_TOKEN_HERE>`.

**Qwen3** — VERBATIM `repos/apple__coreai-models/models/qwen3/README.md`:
```bash
# Defaults to macOS variant
uv run coreai.llm.export Qwen/Qwen3-0.6B

# Full precision
uv run coreai.llm.export Qwen/Qwen3-0.6B --compression none
# iOS variant
uv run coreai.llm.export Qwen/Qwen3-0.6B --platform iOS
# Custom output directory
uv run coreai.llm.export Qwen/Qwen3-0.6B --output-dir ./my-models/
# Truncate to N layers (for debugging)
uv run coreai.llm.export Qwen/Qwen3-0.6B --num-layers 1 --compression none
# Preview resolved config without exporting
uv run coreai.llm.export Qwen/Qwen3-0.6B --dry-run
```
Support matrix (VERBATIM):
| Model | Parameters | macOS | iOS |
|---|---|---|---|
| Qwen3 0.6B | 0.6B | Yes | Yes |
| Qwen3 4B | 4.0B | Yes | Yes |
| Qwen3 8B | 8.0B | **Yes** | **No** |

✅ This **independently corroborates** the transcript's iOS=0.6B / Mac=8B split (326:188-189 and 326:207).
⚠️ **Note the default is the macOS variant** — you must pass `--platform iOS` for the iOS variant. Easy to miss.

## 2.5 The `.aimodel` in Xcode — SAM 3's three functions

VERBATIM 326:78-93:
> "After our model export, we get these **`.aimodel` files in Finder**. Let's see what's inside of the SAM3 model.
> In Xcode, I can inspect everything about it. **I can see it's 623 MB — I am interested that it targets iOS 27.0 and macOS 27.0** for my use case. You can find useful information about the model, such as the **size, metadata, and more**.
> If I click into the **Functions tab**, I can see this model's interface. **It actually exposes three separate functions.** For instance, let's look at the **imageEncode** function.
> **The input isn't just an image, it's a tensor with a specific shape and data type.** And output is a **dense feature embedding**.
> Another function is **detect**. It takes those **image features plus a text prompt**, and outputs **raw masks, bounding boxes, and confidence scores**.
> So to use this model directly, **I'd need to write all the pre-processing to get my camera frame into the right format and all the post-processing to turn these raw tensors into something meaningful**."

### 🔑 New model-viewer fact not in session 324
The Xcode model viewer shows the model's **minimum deployment targets** (iOS 27.0 / macOS 27.0) alongside size. Not mentioned in `docs/Integrating on-device AI models in your app with Core AI.md`, which only lists size, parameter count and metadata. **Possible doc gap; worth flagging.**

### Cross-check on SAM 3's three functions — ✅ exact match

VERBATIM `repos/apple__coreai-models/models/sam3/README.md`:
| Function | Compression | Inputs | Outputs |
|---|---|---|---|
| `image_encode` | 4-bit k-means palettization (gs=32) + fp16 | `pixel_values` | `backbone_features` |
| `text_encode` | 6-bit k-means palettization (gs=8) + fp16 | `input_ids` | `text_features` |
| `detect` | fp16 (no weight compression) | `backbone_features`, `text_features` | `pred_masks`, `pred_boxes`, `pred_logits`, `presence_logits` |

- Transcript's "imageEncode" (spoken camel case) → real graph name **`image_encode`** (snake case).
- Transcript "input isn't just an image, it's a tensor" → `pixel_values`. ✅
- Transcript "output is a dense feature embedding" → `backbone_features`. ✅
- Transcript `detect` "takes those image features plus a text prompt" → `backbone_features`, `text_features`. ✅
- Transcript "raw masks, bounding boxes, and confidence scores" → `pred_masks`, `pred_boxes`, `pred_logits` (+ `presence_logits`, which the transcript omits). ✅

Confirmed in Swift too — VERBATIM `swift/Sources/CoreAIShared/Runtime/ModelStructure.swift:13-20`:
```swift
public enum GraphNames {
    public static let main = "main"
    public static let loadEmbeddings = "load_embeddings"
    public static let extendPrefix = "extend"
    // Multi-function segmenter (lite SAM3 export for iOS).
    public static let imageEncode = "image_encode"
    public static let textEncode = "text_encode"
    public static let detect = "detect"
}
```

⚠️ **Discrepancy / open question — the 623 MB figure.** The repo says `facebook/sam3` is **848M parameters**, and the iOS lite export uses **4-bit palettization on the image encoder, 6-bit on the text encoder, fp16 detector**. 848M params at those mixed precisions would be well under 623 MB (roughly 0.5–0.9 bytes/param for the encoders). 623 MB is more consistent with a **less-compressed or fp16-ish** variant. Either (a) the demo used a different/earlier export configuration, or (b) 623 MB includes tokenizer + metadata + the fp16 detector head. **Mark as UNVERIFIED.**

⚠️ Note also that the transcript describes the model as one `.aimodel`, whereas the repo's SAM 3 export produces a **bundle directory** with `<...>.aimodel` + `tokenizer/` + `metadata.json` (schema 0.2). Consistent with a Finder bundle presentation but worth calling out to developers.

## 2.6 The Swift package — pre/post-processing abstraction

VERBATIM 326:94-99:
> "The **Core AI Models repository can help me with these model-specific pre- and post-processing tasks**. In addition to the models and Python conversion utilities, the repo also hosts a **Swift package for a set of runtime libraries**.
> The libraries abstract things such as **text encoding on the way in, the mask extraction and labeling on the way out**. **So instead of wrangling tensor shapes, you just call a clean Swift API.**
> I already cloned the repo so we can easily add **coreai-models as a dependency** to my project to try it out.
> Once we add the **coreai-models URL as a Swift Package**, we can select the **CoreAILM** and **CoreAISegmentation** to my app target, as easy as that."

✅ **`CoreAILM` and `CoreAISegmentation` are exact product names** — VERBATIM `Package.swift`:
```swift
.library(name: "CoreAILM",           targets: ["CoreAILanguageModels"]),
.library(name: "CoreAISegmentation", targets: ["CoreAIImageSegmenter"]),
```

## 2.7 Integration code — segmentation

VERBATIM narration 326:100-102:
> "Now let's see the code we write to integrate these two models into my app.
> **CoreAIImageSegmenter** imports the image segmentation library that provides the SAM 3 model functionality, which allows us to **load the SAM 3 model from disk**. Then we perform **text-prompted segmentation on an input text prompt, such as 'flower'** and lastly we **extract the best segmentation mask**."

### RECONSTRUCTED (then corrected against the repo)

The narration says "**CoreAIImageSegmenter** imports the image segmentation library" — that's the *target* name. The **product** to add is `CoreAISegmentation`; the **module** is `CoreAIImageSegmenter`; the **type** is `ImageSegmenter`.

```swift
// RECONSTRUCTED from 326:100-102, corrected against
// repos/apple__coreai-models/models/sam3/README.md + swift/Sources/CoreAIImageSegmenter/ImageSegmenter.swift
import CoreAIImageSegmenter

// Load the SAM 3 model from disk (a segmenter bundle dir: metadata.json + *.aimodel + tokenizer/)
let segmenter = try await ImageSegmenter(resourcesAt: sam3BundleURL)

// Text-prompted segmentation
let response = try await segmenter.segment(image: cgImage, prompt: "flower")

// Extract the best segmentation mask (segments are sorted by score descending)
let best = response.segments.first
```

**Grounding — VERBATIM `repos/apple__coreai-models/models/sam3/README.md`:**
```swift
import ImageSegmenter

// Load from a segmenter bundle directory (contains metadata.json, *.aimodel, and tokenizer/)
let segmenter = try await ImageSegmenter(resourcesAt: "coreai-models/exports/sam3_lite_336_w4_static")

// Text prompt (SAM3):
let segments = try await segmenter.segment(image: cgImage, prompt: "cat")
```
⚠️ The README's `import ImageSegmenter` disagrees with `Package.swift`'s target name `CoreAIImageSegmenter`. **The README's import line looks stale/wrong.** Flagged.

**VERBATIM `swift/Sources/CoreAIImageSegmenter/ImageSegmenter.swift:10-33` (doc comment):**
```swift
/// High-level runner that combines tokenization, engine inference, and output decoding.
///
/// ```swift
/// // Text-guided (SAM3):
/// let runner = try ImageSegmenter(engine: sam3Engine, tokenizerFolder: url)
/// let segments = try await runner.segment(image: cgImage, prompt: "cat")
///
/// // Single click (EfficientSAM):
/// let runner = try ImageSegmenter(engine: efficientSamEngine)
/// let pq = PointQuery(points: [.init(x: 320, y: 240)])
/// let segments = try await runner.segment(image: cgImage, pointQuery: pq)
///
/// // Box prompt — one query with two points:
/// let box = PointQuery(points: [
///     .init(x: 100, y: 100, label: .boxTopLeft),
///     .init(x: 400, y: 300, label: .boxBottomRight),
/// ])
///
/// // Multiple independent prompts — Q queries, P points each:
/// let multi = PointQuery(queries: [
///     [.init(x: 100, y: 100)],
///     [.init(x: 300, y: 300)],
/// ])
/// ```
```

**Real signatures (VERBATIM from ImageSegmenter.swift):**
```swift
public struct ImageSegmenter {
    public init(engine: CoreAISegmentationEngine, tokenizer: CLIPTokenizer? = nil) throws
    public init(engine: CoreAISegmentationEngine, tokenizerFolder: URL?) throws

    /// Warm up the engine with a dummy forward pass to trigger kernel compilation.
    public func warmup() async throws

    public func segment(
        image: CGImage,
        textQuery: TextQuery,
        parameters: SegmentationParameters = .default
    ) async throws -> SegmentationResponse

    public func segment(
        image: CGImage,
        prompt: String,
        parameters: SegmentationParameters = .default
    ) async throws -> SegmentationResponse

    public func segment(
        image: CGImage,
        pointQuery: PointQuery = PointQuery(),
        parameters: SegmentationParameters = .default
    ) async throws -> SegmentationResponse
}
```
Return doc, VERBATIM: "A `SegmentationResponse` with segments **sorted by score descending**, and a `SemanticSegmentationMap` if the model exposes a semantic head."
Error cases: `SegmentationRuntimeError.unsupportedEngine` — "Throws … if the loaded model does not accept text queries (e.g. EfficientSAM)" and conversely for point queries with SAM3.
`TextQuery` is an enum with at least `.prompt(String)`, `.tokens([[Int]])`, `.embeddings(...)`.
`SegmentationParameters` has `.default`, `threshold`, `maxSegments`, `tokenizerContextLength`.

**`CoreAISegmentationEngine`** — VERBATIM doc comment `ImageSegmentationEngine.swift:13-22`:
```swift
/// Core AI-backed segmentation engine.
///
/// Supports two asset shapes, autodetected at init time:
///   * Single-function — one ``main`` graph that consumes the image (and a text or point
///     prompt) and emits all detection outputs in one call. Produced by the baseline
///     SAM3 export and EfficientSAM.
///   * Multi-function — three graphs (``image_encode``, ``text_encode``, ``detect``) wired
///     together at runtime. Produced by the SAM3 lite export. The engine pipes the encoder
///     outputs into the detector and returns the same `SegmentationOutput` shape as the
///     single-function path.
public struct CoreAISegmentationEngine {
    public var supportsTextQuery: Bool { ... }
    public var supportsPointQuery: Bool { ... }
    public init(parameters: SegmentationParameters, modelURL: URL) async throws
```
Error message when the classification is wrong (VERBATIM):
```
"Model classified as multi-function segmenter but is missing one of "
+ "{'image_encode','text_encode','detect'}. Available functions: \(model.functionNames)."
```

**Note `warmup()`** — "Warm up the engine with a dummy forward pass to **trigger kernel compilation**." This is a *fourth* latency lever (beyond cache-check / explicit specialize / AOT compile) that neither talk names explicitly. 🔑

## 2.8 Integration code — the LLM, via **Foundation Models**

VERBATIM 326:103-118 (the most important passage in session 326):
> "Now for the language model. **To load, it's just one line. I create a `CoreAILanguageModel`, point it at my model bundle and it's ready. One line — asset loading, engine creation, tokenizer setup — all abstracted away for you.**
> **Notice we're importing FoundationModels here. This is the same framework you may already be familiar with.**
> Here's the beautiful part. To use it, I create a **`LanguageModelSession`**. This is the **same API that gives you access to Apple's on-device large language model**. **The difference is that now you'll pass in your own model to use.**
> **Same `session.respond(to:)` call, same streaming support, same structured output capabilities.** You get the **ergonomics of the Foundation Models API with the flexibility of choosing exactly which model runs underneath**.
> **We also support guided generation.** This is important for our use case. Instead of letting the model generate free-form text, I can provide a **`@Generable` macro that describes exactly what a vocabulary card looks like: a word field, a translation field, an example sentence field.**"

### RECONSTRUCTED app code

```swift
// RECONSTRUCTED from 326:103-118.
// CoreAILanguageModel + LanguageModelSession(model:) is VERIFIED against
// repos/apple__coreai-models/models/qwen3/README.md and CoreAILanguageModel.swift.
import FoundationModels
import CoreAILanguageModels

// One line: asset loading, engine creation, tokenizer setup.
let model = try await CoreAILanguageModel(resourcesAt: qwenBundleURL)

// Same Foundation Models session type — just pass your own model.
let session = LanguageModelSession(model: model)

@Generable
struct VocabCard {
    @Guide(description: "The vocabulary word in the target language")
    var word: String
    @Guide(description: "The English translation")
    var translation: String
    @Guide(description: "A natural example sentence using the word")
    var exampleSentence: String
}

let card = try await session.respond(to: "Generate a vocab card for: Hummingbird",
                                     generating: VocabCard.self)
```
⚠️ The `@Guide` attributes are **my addition**, not described in the transcript. The transcript only says the `@Generable` type "describes exactly what a vocabulary card looks like: a word field, a translation field, an example sentence field." **Field names are RECONSTRUCTED.** The `generating:` argument label is from the Foundation Models framework and is **UNVERIFIED against a 2026 source in this session** (another agent covers FM).

### ✅ Verified grounding for the Core AI ↔ FM bridge

VERBATIM `repos/apple__coreai-models/models/qwen3/README.md`:
```swift
import FoundationModels
import CoreAILanguageModels

let model = try await CoreAILanguageModel(resourcesAt: modelURL)

let session = LanguageModelSession(model: model)

let response = try await session.respond(to: "What is quantum computing?")

print(response)
```

VERBATIM `swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift:12-32`:
```swift
/// FoundationModels Adoption for Core AI inference engines.
///
/// Wraps any `InferenceEngine` (pipelined, sequential, or static-shape) and exposes it
/// through the FoundationModels `LanguageModel` protocol. It uses the modern `tokenSequence()`
/// API for efficient streaming token generation.
/// ## Engine Selection
/// The engine type is determined by `EngineFactory` based on model structure:
/// - **Pipelined**: GPU-accelerated with pipeline-depth-matched buffering (fastest for GPU models)
/// - **Sequential**: CPU-based synchronous execution (fallback)
/// - **Static-shape**: Neural Engine optimized for chunked static models
///
/// ## Usage
/// ```swift
/// let model = try await CoreAILanguageModel(resourcesAt: url)  // .lazy by default
/// print(model.estimatedSizeOnDiskBytes ?? 0)
/// try await model.load()                                       // optional; respond auto-loads
/// let session = LanguageModelSession(model: model)
/// // ... generate ...
/// model.unload()
/// ```
public struct CoreAILanguageModel: LanguageModel {
```

🔑 **This proves the key architectural claim:** `FoundationModels` exposes a **public `LanguageModel` protocol** that third parties can conform to, and `LanguageModelSession` has an initializer taking a custom model: **`LanguageModelSession(model:)`**.

**Full verified initializer, VERBATIM CoreAILanguageModel.swift:78-104:**
```swift
    /// Creates a model from a resource bundle on disk.
    ///
    /// - Parameter url: URL to the model bundle directory.
    /// - Parameter mode: When to load the engine. Defaults to `.lazy`. With
    ///   `.eager`, the tokenizer and engine load concurrently
    /// - Parameter variant: Engine variant override (e.g. "coreai-sequential",
    ///   "ane"). Nil for auto-detect from model structure.
    /// - Parameter kvCacheStrategy: KV cache memory strategy. Defaults to
    ///   `.auto` (256-token initial size for dynamic models). Pass
    ///   `.fixedSize` to pre-allocate at full `maxContextLength`.
    /// - Throws: If the asset bundle is invalid or the tokenizer fails to load.
    ///   With `.eager`, also throws on engine-creation failure.
    public init(
        resourcesAt url: URL,
        mode: LoadMode = .lazy,
        variant: String? = nil,
        kvCacheStrategy: KVCacheStrategy = .auto
    ) async throws
```
```swift
    public enum LoadMode: Sendable {
        case lazy
        case eager
    }
```

**Capabilities plumbing, VERBATIM CoreAILanguageModel.swift:58-65:**
```swift
    public var capabilities: LanguageModelCapabilities {
        var caps: [LanguageModelCapabilities.Capability] = []
        if supportsToolCalling { caps.append(.toolCalling) }
        if supportsReasoning { caps.append(.reasoning) }
        if isGuidedGenerationSupported { caps.append(.guidedGeneration) }
        return LanguageModelCapabilities(caps)
    }
```
→ FM `LanguageModelCapabilities.Capability` includes **`.toolCalling`, `.reasoning`, `.guidedGeneration`**. Reasoning is auto-detected by probing the tokenizer:
```swift
        self.supportsReasoning =
            tokenizer.convertTokenToId("<think>") != nil
            || tokenizer.convertTokenToId("<|reasoning_start|>") != nil
```
→ explains 326:208 "you can see that it is thinking before it gives me the outputs."

**Guided generation implementation:** the package links **XGrammar** (`mlc-ai/xgrammar`, branch `main`) through a `CXGrammar` C bridge and a `ConstrainedGenerationSession` (`swift/Sources/CoreAILanguageModels/GuidedGeneration/`). So `@Generable` structured output on a *custom* Core AI model is implemented via grammar-constrained decoding, not by Apple's built-in adapter.
🔥 **Footgun:** `CoreAILanguageModels` requires `.linkedLibrary("c++")` and `.define("CXGRAMMAR_IMPORT")` — a C++ dependency comes along for the ride.

**"same streaming support"** → the doc comment says it "uses the modern `tokenSequence()` API for efficient streaming token generation."

**Custom token sampling strategies** (promised at 324:186) → `swift/Sources/CoreAILanguageModels/Samplers/` incl. `MPSGraphSamplers.swift`, and `DecodingStrategies/`. VERBATIM comment `MPSGraphSamplers.swift:154, 253`:
```
/// ## Usage with Core AI's ComputeStream
///   - queue: The command queue (from Core AI's ComputeStream via withMetal3Queue)
```
→ **`ComputeStream.withMetal3Queue`** exists (bridges back to a Metal 4 command queue). Not mentioned in either talk.

## 2.9 The demo failure → specialization (the pedagogical centerpiece)

VERBATIM 326:119-140:
> "Now let's see it in action. I'll take a photo… and we're waiting. **The segmentation hasn't come back yet, so we can't get to card generation. Something is clearly slow here.**
> I know from my code that **I show this spinner when I'm first instantiating my SAM 3 model and sending it a prompt**. Let's see what's going on.
> **I took a trace with the new Core AI instruments, and sure enough there's a model load event right at that point, with a large sub-event for specialization.**
> **Specialization is the process that prepares a Core AI model for execution on device.** When your model is loaded it is checked to see if it has already been specialized and cached. **This process can take a significant amount of time for very large models.** That is what we were seeing in our instrument trace.
> While future loads are from the cache and are fast, **that first time is something I need to plan for**.
> **Having that happen right in the middle of the user experience is... probably not great.** So when should I do it? **I could kick it off at launch or run it in the background but that feels wasteful if the user isn't even interested in this feature yet.**
> **I think a better idea is to create a dedicated first-run experience, where I can move this work to happen while the user is learning about the feature for the first time. This keeps model loading and specialization out of the interactive flow.**"

🔑 **The recommendation, distilled:** *don't* specialize at launch or eagerly in the background; build a **dedicated first-run / feature-introduction experience** and do the work there, behind explanatory UI.

🔑 **The Instruments signature to look for:** a **model load event with a large "specialization" sub-event**.

## 2.10 Deployment strategy (326:140-149)

VERBATIM:
> "Before I make that change though, I want to step back and think more broadly about my **deployment strategy** for this feature.
> There are a few things I want to get right. **I'm shipping this as an update to my existing app, so I want the feature to be discoverable but not required. Users who try it should have a great experience, and users who don't should feel just as great about the app as before.**
> My first-run experience gives me a natural place to explain the feature and prepare for a smooth first launch. But **I'd been assuming the models would just be bundled with the app and when I checked, they're adding over 1 GB to my download size. That hits everyone who updates, even people who'll never touch this feature.**
> **So instead, I'll have my feature introduction screen include a button that only triggers the model download if the user actually wants to try it. I'll use Background Assets for this.** If you want to dig into the details, check out **'Discover Apple-Hosted Background Assets' from last year's WWDC**."

📌 **Concrete number: SAM 3 + Qwen3 0.6B bundled = "over 1 GB" added to app download size.** (Consistent with 623 MB SAM3 + a compressed 0.6B LLM + tokenizer.)

📌 **Recommended pattern:** feature-intro screen → explicit opt-in button → **Background Assets** download → then specialize. Never bundle >1 GB of models into the app binary for an optional feature.

VERBATIM 326:150-154:
> "When a user says they want to give the feature a try, **I request the model assets and show them the download progress. Once that's done, I kick off specialization.**
> The specialization is no longer interrupting the main experience **but it's still taking a while. That's a bit of an awkward waiting time for the user experience.**"

## 2.11 Ahead-of-time compilation with `coreai-build` (326:155-170)

VERBATIM:
> "Fortunately, Core AI has an awesome feature that can help here. **During specialization the model goes through two main transformations. First it goes through a core set of compilation steps. Second, executable artifacts are generated. These artifacts are tied to the device and OS version they were generated on. Of these two steps, compilation is the most expensive and takes the most amount of time.**
> The Core AI toolchain lets me do **some of that compilation ahead-of-time on my development machine, producing a compiled version of the model**. While that compiled model **still needs to be specialized for the specific user's device**, there is now much less work to do and finishes significantly faster.
> **This is done with the `coreai-build` command.** You give it a model as input, and **depending on your options, it generates one or more compiled models targeting specific device architectures**.
> **I did this with my model and created a background asset for each compiled model. There is a small amount of code I add to my app to detect the architecture of the device it's running on and then request the appropriate asset based on that.**
> You can find all the details in the **'Compiling Core AI models ahead of time' article on developer.apple.com**."

### Cross-check with `docs/Compiling Core AI models ahead of time.md` — ✅ full agreement, doc has the details

VERBATIM doc:20-22:
> "Core AI can help reduce on-device specialization time with *ahead-of-time compilation* through the `coreai-build` command-line tool. The tool moves **the most expensive part of specialization, model compilation, to your build machine**…
> Ahead-of-time compilation converts your `.aimodel` model file into **`.aimodelc`** assets, **one for each device architecture**. At runtime, your app picks the asset that matches the current device's architecture, and Core AI generates the executable code on device **without repeating the compilation step**."

**The command, VERBATIM doc:47:**
```shell
% xcrun coreai-build compile MyModel.aimodel --platform iOS --min-deployment-version 27.0 --output compiled/
```

**Flags established:**
| Flag | Meaning |
|---|---|
| `compile` | subcommand |
| `--platform` | e.g. `iOS` |
| `--min-deployment-version` | e.g. `27.0` |
| `--output` | output directory |
| `--preferred-compute` | override compute unit selection |
| `--help` | "For the available values, the minimum deployment version, the target architecture, and other options, run `coreai-build compile --help`." |

**Output naming, VERBATIM doc:50:**
> "`coreai-build` outputs **one compiled `.aimodelc` file per device architecture**, using the input model's filename as the prefix. For example, compiling `MyModel.aimodel` produces files named **`MyModel.<arch>.aimodelc`**, where `<arch>` is the device architecture identifier returned by `deviceArchitectureName` at runtime. **Each compiled `.aimodelc` works on any OS version at or above the minimum deployment version you pass to `coreai-build`.**"

**Prereq:** "To use `coreai-build`, install the Metal Toolchain on your Mac, either through Xcode or the command line." → `xcodebuild -downloadComponent MetalToolchain`.

**The "small amount of code" Carina mentions — VERBATIM doc:60-63:**
```swift
let arch = AIModel.deviceArchitectureName
let assetName = "MyModel.\(arch).aimodelc"
```
✅ **`AIModel.deviceArchitectureName` is a static property returning a `String`.**

**Loading is unchanged, VERBATIM doc:65:**
> "To load the downloaded `.aimodelc` asset, use `init(contentsOf:options:)`. **This is the same API you use to load `.aimodel` files, so you don't need to change your loading code when you adopt ahead-of-time compilation.** Use the default options, or **specify options that match the compute units you used at compile time.**"

🔥 **HARD HARDWARE GATE, VERBATIM doc:26-27:**
> "[!NOTE] Ahead-of-time compilation **only compiles for devices that support Apple Intelligence**, including **iPhone or iPad with the A17 Pro chipset or later, a Mac with the M1 chipset or later, or Apple Vision Pro with the M2 chipset or later.**"

→ This is a *big* deal and it is **not mentioned in either transcript**. AOT compilation doesn't help pre-A17-Pro iPhones; those devices fall back to full on-device specialization.

**Hosting recommendation, VERBATIM doc:56:**
> "Ahead-of-time compilation produces one `.aimodelc` per supported device architecture, but each device only needs the variant that matches its own architecture. **It's recommended to host the compiled assets remotely and download the matching variant to the device at runtime, because each device only uses one of them.** The Background Assets framework can manage downloads, installs, and updates for your hosted model files."

✅ exactly what Carina did (326:165-166).

**Residual work, VERBATIM doc:67:**
> "**Even with ahead-of-time compilation, the compiled asset still requires some specialization on the device.** The amount of compilation that remains depends on the model and the compute units it uses."

## 2.12 Demo #2 and results (326:170-178)

VERBATIM:
> "I've integrated this and now we have the ahead-of-time compilation already done. On my desk, I have some rocks I've collected from my travels. Let's see this in action.
> **Now the model preparation step should be a fraction of what it was before, and the user can get started quickly.**
> The model gave me an example usage, and I can save it to my collection.
> Let's try a few more objects. Here I have a piece of wood gifted from my college roommate, and a sunflower from my little sister…
> **And on subsequent inferences, we are using the cached model asset so the user experience is seamless.**"

Segmentation prompts demoed: rocks, wood, sunflower, and later "butterflies, rock, flower, lake, bird".

## 2.13 Multiplatform / macOS (326:179-210)

VERBATIM:
> "Here's what we've built so far on iOS. **SAM3 handles segmentation, and Qwen 0.6B model generates the vocab cards. With Core AI, I can reuse all the same code and just build from there on Mac.**
> On Mac, I'm not learning one word at a time. I'm curating. I might have a folder of photos from a recent trip, and I want to generate cards for all of them in one go. **So I add a batch processing layer on top.** What took an afternoon of typing can now be completely automated.
> **And because I have more memory and processing power on the Mac, I can step up to a larger model variant of the same model. More parameters means better reasoning and higher-quality output.** For curation, that matters. I can give the model **richer prompts, ask for multiple example sentences instead of one, or even have it generate pinyin in Chinese. The same code, calling the same API, just a more capable model underneath.**
> **And with longer context, I can go beyond individual cards. I can hand the model an entire category of words and ask it to build a curriculum: sequence them from simple to complex, group them into lessons, and write example sentences that reuse earlier vocab to reinforce what the student already learned. One prompt, and I have a structured lesson plan.**"

Demo (326:204-210):
> "I want to segment **butterflies, rock, flower, lake, bird**, etc. **Right away, we are parallelizing the workload to segment the photos, to find all objects in all my photos**, so I can reuse a photo to create multiple cards. Once that's done, we kick off the generation with our **Qwen3 8 billion model**. **It is a more powerful reasoning model, so you can see that it is thinking before it gives me the outputs. In fact, it is checking whether the pinyin is correct for each word and example usage, since those are easy to mess up.** Once that's done, we get cards with multiple images for me to now distribute to my apps, and even a curriculum to help me guide my teaching!"

🔑 **The multiplatform recipe, distilled:**
1. Same Swift code, same `CoreAILanguageModel` / `LanguageModelSession` API.
2. **Swap the model bundle**, not the code — iOS: Qwen3 0.6B; macOS: Qwen3 8B.
3. Add a **batch/parallelism layer** on Mac (parallel segmentation across a photo folder).
4. Exploit the larger model's **longer context** for qualitatively different features (curriculum generation) not just better cards.

✅ Corroborated by `models/qwen3/README.md`: 8B is macOS-only.
📌 Recall from §1.9: "you can safely call the same inference function from different tasks" — that's the API guarantee behind "parallelizing the workload."

Closing (326:211-216):
> "With Core AI, you can build a multiplatform app experience where **your user's data never leaves their device. There's no server to manage, no cost per token, and no latency to the cloud. The models are ready. The tools are ready.** With Core AI you have everything you need to bring powerful, private intelligence to every Apple platform."

Also, a small easter egg at 326:210: "**my agents are calling me**" — offhand, but consistent with the agentic framing in 324:21.

---

# PART 3 — Consolidated API reference extracted from these two sessions

## 3.1 Swift — `CoreAI` framework

```swift
import CoreAI

// ---- Model ----
public struct/class AIModel {
    init(contentsOf url: URL) async throws
    init(contentsOf url: URL, options: SpecializationOptions) async throws
    init?(resolvingBookmark: Data) throws
    static func specialize(contentsOf: URL,
                           options: SpecializationOptions,
                           cache: AIModelCache = .default,
                           cachePolicy: AIModelCache.Policy = ...) async throws -> AIModel
    static var deviceArchitectureName: String { get }
    var bookmarkData: Data { get }
    var functionNames: [String] { get }
    func loadFunction(named: String) throws -> InferenceFunction?
    func functionDescriptor(for name: String) -> InferenceFunctionDescriptor?
}

public struct AIModelAsset          // unspecialized source model asset

// ---- Inference ----
public struct InferenceFunction {
    var descriptor: InferenceFunctionDescriptor { get }

    func run(inputs: [String: NDArray]) async throws -> Outputs
    func run(inputs: [String: NDArray],
             states: consuming MutableViews,
             outputViews: consuming MutableViews) async throws -> Outputs

    func encode(inputs: [String: AsyncValue],
                states: consuming AsyncMutableViews,
                outputViews: consuming AsyncMutableViews,
                to stream: ComputeStream) throws -> ...

    struct Outputs { mutating func remove(_ name: String) -> InferenceValue? }
    struct MutableViews { init(); mutating func insert(_ a: inout NDArray, for name: String) }
    struct AsyncValue {
        init(unsafeBuffer: MTLBuffer, byteOffset: Int, scalarType: NDArray.ScalarType,
             shape: [Int], strides: [Int])
    }
    struct AsyncMutableValue { /* same init labels */ }
    struct AsyncMutableViews { init(); mutating func insert(_ v: inout AsyncMutableValue, for: String) }
}

public struct InferenceFunctionDescriptor {
    var inputNames: [String] { get }
    var outputNames: [String] { get }
    var stateNames: [String] { get }
    func inputDescriptor(of name: String) -> InferenceValue.Descriptor?
}

public enum InferenceValue {
    var ndArray: NDArray? { get }
    var pixelBuffer: CVMutablePixelBuffer? { get }   // for image-typed values
    enum Descriptor { case ndArray(NDArrayDescriptor) /* + image case */ }
}

public struct ImageDescriptor { /* dimensions + pixel format */ }
public struct ComputeStream { init(commandQueue: MTLCommandQueue); /* withMetal3Queue */ }

// ---- Arrays ----
public struct NDArray {
    init(shape: [Int], scalarType: ScalarType)
    init(descriptor: NDArrayDescriptor)
    var scalarType: ScalarType { get }
    enum ScalarType { case float16, float32, int32, ... }
    borrowing func view() -> View
    borrowing func view<T>(as: T.Type) -> View
    mutating func mutableView<T>(as: T.Type) -> MutableView

    struct View: ~Escapable {
        func withUnsafePointer<R>(_ body: (ptr, Span<Int>/*shape*/, Span<Int>/*strides*/) -> R) -> R
    }
    struct MutableView: ~Escapable {
        var contiguousElements: MutableSpan<T>? { get }   // nil if non-contiguous
        mutating func copyElements(fromContentsOf: some Collection<T>)
        mutating func withUnsafeMutablePointer<R>(_ body: (ptr, Span<Int>, Span<Int>) -> R) -> R
    }
}

public struct NDArrayDescriptor {
    var shape: [Int] { get }
    var scalarType: NDArray.ScalarType { get }
    var preferredStrides: [Int] { get }
    func resolvingDynamicDimensions(_ shape: [Int]) -> NDArrayDescriptor
}

// ---- Specialization / cache ----
public struct SpecializationOptions {
    static var `default`: Self
    static var cpuOnly: Self
    init(preferredComputeUnitKind: ComputeUnitKind)
    var expectFrequentReshapes: Bool     // mutable
}
public enum ComputeUnitKind { case cpu, gpu, neuralEngine; static var availableKinds: [ComputeUnitKind] }
public struct AIModelCache {
    static var `default`: AIModelCache
    init?(appGroup: String)
    func model(for url: URL, options: SpecializationOptions) throws -> AIModel?
    func deleteEntries(for url: URL) throws
    enum Policy { case `default`, persistent }
}
public enum AssetError: Error { }
```
⚠️ `~Escapable`, exact struct-vs-class choices, and enum case lists are inferred from prose + usage. The **member names** above are all grounded; the **declaration syntax** is my reconstruction.

## 3.2 Python

| Symbol | Notes |
|---|---|
| `pip install coreai-torch` | install |
| `coreai_torch.TorchConverter(mode=Mode.DEBUG)` | `Mode.DEBUG` / `Mode.RELEASE` |
| `.add_exported_program(ep, *, input_names, output_names, state_names, entrypoint_name="main")` | |
| `.add_pytorch_module(model, *, export_fn, externalize_modules, input_names, output_names, state_names, entrypoint_name="main")` | |
| `.to_coreai() -> AIProgram` | |
| `AIProgram.optimize()` | |
| `AIProgram.save_asset(Path) -> AIModelAsset` | writes an `.aimodel` **directory** |
| `AIProgram._save_bytecode(path)` | private; writes `main.AICode.bc` |
| `coreai_torch.get_decomp_table()` | REQUIRED before conversion |
| `coreai_torch.ExternalizeSpec(target_class=, composite_op_name=, composite_attrs=)` | composite-op externalization |
| `coreai_torch.TorchMetalKernel` | inline Metal GPU kernels |
| `coreai_torch.MetalParameter` | re-export of `coreai.authoring.MetalParameter` |
| `coreai_torch.generate_composite_decl` | |
| `coreai_torch.composite_ops` (e.g. `RMSNormImpl`) | |
| `coreai.runtime.NDArray`, `.InferenceFunction`, `.AIModel` | Python runtime bindings |
| `AIModel.load(asset_path)` (await) | |
| `asset.executable(specialization_options=...)` | async context manager |
| `ai_model.load_function("main")` | **raises `KeyError`** if missing (unlike Swift's `nil`) |
| `await function({"name": NDArray(t)})` → dict, values have `.numpy()` | |
| `coreai_torch.debugging.validator.create_validator_for_exported_program` / `create_validator_for_coreai_program` | `check_for_nans` / `check_for_infs` / `check` |
| `coreai_torch.debugging.comparator.create_comparator_for_programs(...).compare_with_tolerance(inputs=, rtol=, atol=)` | PyTorch ↔ Core AI diff |
| `coreai_torch.debugging.inspector.CoreAIInspector(model=, function_name=).get_intermediates_for_ops(ids, inputs=)` | |
| `coreai_torch.debugging.graph_diff.{compute_exported_program_diff, compute_coreai_program_diff, write_diff}` | graph isomorphism |
| `coreai_torch.debugging.benchmarker.benchmark_coreai_program(coreai_program=, inputs=, num_runs=)` | `.write_summary(f)`, `.get_module_timings()` |
| `coreai_torch.debugging.torch_utils.{save_intermediates, load_intermediates}` | `*.aimodelintermediates` |
| `coreai_torch.debugging.search_strategy.LevelOrderStrategy.{bisection, top_down, auto}` | |
| `coreai_torch.debugging.debug_info.strip_debug_info` | strip DEBUG metadata before shipping |

## 3.3 CLI

```shell
# Metal toolchain (required for .aimodel builds AND coreai-build)
xcodebuild -downloadComponent MetalToolchain

# Ahead-of-time compile
xcrun coreai-build compile MyModel.aimodel \
      --platform iOS \
      --min-deployment-version 27.0 \
      --output compiled/ \
      [--preferred-compute <unit>]
xcrun coreai-build compile --help

# coreai-models repo
uv run coreai.model.registry --list-models
uv run coreai.model.registry --help
uv run coreai.llm.export Qwen/Qwen3-0.6B [--platform iOS] [--compression none] \
        [--output-dir DIR] [--num-layers N] [--dry-run]
uv run models/sam3/export.py [--full] [--image-size 336] [--n-bits N] [--group-size G] \
        [--max-text-seq-len 32] [--dtype float16|float32] [--output-dir DIR] \
        [--output-name NAME] [--overwrite] [--dry-run]

# coreai-models CLI tools (Mac, Xcode 27+)
swift run -c release llm-runner       --model path/to/exported_model_folder --prompt "Hello"
swift run -c release llm-benchmark    --model path/to/exported_model_folder   # -p / -g / -n
swift run -c release image-segmenter  --model path/to/exported_model_folder --prompt "cat" --image path/to/image.jpg
```

## 3.4 File extensions / formats

| Extension | What it is |
|---|---|
| `.aimodel` | Portable **source** model. A **directory/bundle**. Runs on any Apple device *after* specialization. |
| `.aimodelc` | Ahead-of-time **compiled** model, **one per device architecture**, named `<Name>.<arch>.aimodelc`. Still needs (much less) on-device specialization. |
| `.aimodelintermediates` | Saved intermediate tensor values from a debug run (e.g. `main.aimodelintermediates`). |
| `main.AICode.bc` | Core AI bytecode dump (private `_save_bytecode`). |
| "segmenter bundle" dir | `metadata.json` (schema 0.2) + `*.aimodel` + `tokenizer/` — produced by `models/sam3/export.py`. |

---

# PART 4 — Cross-check summary: transcripts vs local docs vs repos

## 4.1 Agreements (transcript claim → corroborating source)

| Claim | Source |
|---|---|
| `.aimodel` is a portable source format needing per-device specialization (324:142-143) | `docs/Managing model specialization and caching.md:18` |
| Cache-miss returns `nil` (324:151) | `docs/Managing…:34, 48` |
| Explicit `specialize` independent of loading (324:153) | `docs/Managing…:64-76` |
| `SpecializationOptions` configure optimization (324:156) | `docs/Managing…:52-60` |
| `AIModelCache` delete + policy + app-group sharing (324:157-158) | `docs/Managing…:87-161` |
| Specialization = compile (expensive) + artifact gen; artifacts tied to device+OS (324:164-168; 326:156-160) | `docs/Compiling…:20-22, 67` |
| AOT compilation via `coreai-build` reduces but doesn't remove specialization (324:169-170; 326:161-162) | `docs/Compiling…:20-22, 67` |
| `?` in NDArray dims = dynamic shape (324:65) | `docs/Integrating…:67` |
| Xcode model viewer shows size + op distribution + metadata; Functions tab shows signatures (324:62-63) | `docs/Integrating…:51-65` |
| `AIModel` init from URL; `loadFunction`; `NDArray`; `run` (324:71-77) | `docs/Integrating…:73-168` |
| MutableView is non-escapable, safe access to backing storage (324:88-89) | `docs/Integrating…:121` |
| States = read + updated in place (324:110) | `coreai-torch/tests/test_stateful.py` IR checks; `run(states:)` in coreai-models |
| `state_names` argument on convert (324:119) | `coreai_torch/converter.py:202, 248` |
| Optimal memory layout / preallocated outputs / async values (324:177-179) | `NDArray+Helpers.swift`, `CoreAISequentialEngine.swift`, `CoreAIPipelinedEngine.swift` |
| Core AI Models repo = models + skills + Swift package + FM bridge (324:182-186) | `repos/apple__coreai-models/README.md`, `Package.swift`, `CoreAILanguageModel.swift` |
| SAM3 exposes 3 functions incl. `imageEncode` and `detect` (326:86-92) | `models/sam3/README.md`; `GraphNames` in `ModelStructure.swift` |
| SAM3 targets iOS 27.0 / macOS 27.0 (326:82-84) | `Package.swift` platforms `.macOS("27.0"), .iOS("27.0")`; `coreai-models/README.md` "macOS and iOS 27.0+" |
| `CoreAILM` / `CoreAISegmentation` products (326:99) | `Package.swift` |
| `CoreAILanguageModel` + `LanguageModelSession(model:)` (326:105-113) | `models/qwen3/README.md`; `CoreAILanguageModel.swift` |
| Qwen 0.6B on iOS, 8B on Mac (326:188, 207) | `models/qwen3/README.md` support matrix |
| Guided generation / `@Generable` support (326:116-118) | `LanguageModelCapabilities.Capability.guidedGeneration` + XGrammar in `Package.swift` |
| Reasoning model "thinking" visible (326:208) | `supportsReasoning` via `<think>` token probe; `ThinkTagParser.swift` |

## 4.2 Discrepancies / things only in one place

| Item | Note |
|---|---|
| **SAM3 = 623 MB** (326:82) | Repo says `facebook/sam3` = 848M params, lite export = w4/w6 palettized + fp16. 623 MB doesn't obviously follow. **UNVERIFIED**; probably a different export config than the current repo default. |
| **Xcode viewer shows deployment targets** (326:82-84) | Not in `docs/Integrating…`. Doc gap or newer Xcode build. |
| **70B LLM claim** (324:21) | No corroboration in local repos; largest catalog entries are MoE (`gpt_oss`, `mixtral`, `qwen3_moe`). **UNVERIFIED.** |
| **`import ImageSegmenter`** in `models/sam3/README.md` | Contradicts `Package.swift` target name `CoreAIImageSegmenter`. Repo README likely stale. |
| **AOT compile only covers Apple-Intelligence-capable devices (A17 Pro+/M1+/M2 Vision Pro)** | In `docs/Compiling…:26-27` only. **Neither talk mentions it.** Major planning constraint. |
| **`TorchConverter.Mode.DEBUG` is the default** | Only in `converter.py`. Neither talk nor docs mention stripping debug info for release. |
| **`USE_LOCAL_COREAI=1` / `ENABLE_DEBUG_INFO=1` preview env vars** | Only in `coreai-torch/docs/api/debugging.md`. |
| **`AIModel.bookmarkData` / `init(resolvingBookmark:)`** | Only in `docs/Managing…:163-207`. Neither talk mentions it. |
| **Metal Toolchain required for `.aimodel` builds** | Only in `docs/Integrating…:36-45`. Neither talk mentions it — but it's the #1 first-build failure. |
| **`SpecializationOptions.expectFrequentReshapes`** | Only in `coreai-models` source. Undocumented locally. |
| **`ImageSegmenter.warmup()` "trigger kernel compilation"** | Only in repo source. A 4th latency lever not named in either talk. |
| **`ComputeStream.withMetal3Queue`** | Only referenced in a comment in `MPSGraphSamplers.swift`. |
| Python `load_function` raises `KeyError`; Swift `loadFunction(named:)` returns `nil` | Deliberate API asymmetry. Worth documenting for readers who move between the two. |

## 4.3 Third-party / secondary source (treat with caution)

`repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/CoreAI/DebuggingAndProfiling.md` is a **mirror/summary of Apple's "Inspecting, debugging, and profiling Core AI models"** article (the article itself is NOT in our `docs/` mirror). It reads like a condensed rewrite, so treat specifics as *unverified*, but it does name four sub-article URLs that plausibly exist:
- `/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models`
- `/documentation/coreai/validating-inference-correctness-against-a-reference-run`
- `/documentation/coreai/monitoring-model-performance-with-the-debug-gauge`
- `/documentation/coreai/analyzing-model-runtime-performance-with-instruments`

Its claims that align with the transcripts (and are therefore plausible):
- Core AI Debugger = **standalone macOS app**, drag in a `.aimodel`, browse structure, browse function signatures (inputs/outputs/**states**) **without running inference**, validate numerics against a reference dataset, find NaN/Inf layers.
- Debug gauge = Xcode Debug Navigator; tracks **load / specialization / inference** events live; useful to "**Identify unexpected re-specialization (e.g., when `SpecializationOptions` changes between calls)**" and "**Verify cache hits are occurring (no specialization events on subsequent launches)**".
- Core AI Instrument = Instruments template; per-call inference duration broken down by compute unit; Product ▸ Profile ▸ select the **Core AI** template.

⚠️ Its "memory bandwidth / queue depth / cache hit-miss" capture list and its "Common Issues" table are **UNVERIFIED** — that file may be LLM-generated. Do not quote it as authoritative in the final guides without a second source.

---

# PART 5 — Presenter guidance, distilled into rules

Ordered roughly by how often the two presenters stressed them.

1. **Never let specialization happen inside a user-interactive flow.** (324:147 — "It is recommended you avoid having model specialization occur within user interactive flows."; 326:139 — "This keeps model loading and specialization out of the interactive flow.")
2. **Build a dedicated first-run experience for the feature** and do model download + specialization behind it, while the user reads about the feature. Explicitly rejected alternatives: at-launch specialization and background specialization — "that feels wasteful if the user isn't even interested in this feature yet" (326:138).
3. **Check the cache first (`AIModelCache.default.model(for:options:)`); `nil` means you must specialize.** Use that to gate features or show an explanatory wait UI. (324:149-152)
4. **Don't bundle large models in the app binary for an optional feature.** >1 GB "hits everyone who updates, even people who'll never touch this feature" (326:145-146). Use **Background Assets** with an explicit opt-in button.
5. **Use `coreai-build` AOT compilation** and ship one `.aimodelc` per architecture as a background asset; select at runtime with `AIModel.deviceArchitectureName`. (326:163-166)
6. **Always numerically validate the converted model against PyTorch before integrating** — "assert a sufficiently small delta for my use case" (324:59).
7. **Use `dynamic_shapes` at `torch.export` time for any dimension that varies at runtime**, or it gets frozen at the sample value. (324:51 — the seq-len-5 trap.)
8. **Always `run_decompositions(get_decomp_table())`.** (324:52; repo warns it's required.)
9. **For any decoding loop / transformer, use states (KV cache).** Author them as `register_buffer` + in-place mutation, name them with `state_names`, pass them as `InferenceFunction.MutableViews` in the `states:` argument. (324:107-127)
10. **Profile with the Core AI instrument; triage with the debug gauge first.** "This is a great place to spot performance issues before jumping into instruments." (324:140)
11. **Prefer two small task-specific models over one big general model** — better quality, smaller individual sizes, independent upgradeability. (326:45)
12. **Target sub-1B-parameter variants for iPhone.** (326:46)
13. **Check the Core AI Models repo before writing conversion code** — "for many popular models there is an another path" (326:69) and the Swift package saves you all pre/post-processing.
14. **Reuse the same code across platforms; swap the model bundle for a bigger variant on Mac**, and use the extra context for qualitatively new features. (326:190-203)
15. **Progressive disclosure is intentional**: "For most use cases, the higher-level inference APIs will get you exactly where you need to be. But when you're optimizing a tight inference loop or integrating a model into a complex compute pipeline, these lower-level APIs are there when you need them." (324:180-181)
16. **Test before overriding `SpecializationOptions`.** Doc: "In most scenarios, the default configuration offers the best performance, so test your app's performance carefully before overriding it."

---

# PART 6 — Gotchas & footguns (consolidated)

## Build / setup
- 🔥 **Metal Toolchain is not installed by default.** Builds containing `.aimodel` fail with a missing Metal compiler error. Install via Xcode ▸ Settings ▸ Components ▸ Other Components ▸ Metal Toolchain, or `xcodebuild -downloadComponent MetalToolchain`. Also required for `coreai-build`.
- `.aimodel` must appear in the target's **Compile Sources** build phase.
- coreai-models Swift package requires **macOS/iOS 27.0+, Xcode 27.0+**, and links `c++`.

## Conversion (Python)
- 🔥 Skipping `run_decompositions(get_decomp_table())` leaves ops with **no lowering rule** → hard conversion failure.
- 🔥 `dynamic_shapes` omission bakes in your sample shape (the "seq length 5" trap).
- `torch` must be **≤ 2.13.0** or you get a validation warning.
- `TorchConverter` defaults to `Mode.DEBUG`, embedding full torch stack traces in the asset. Use `Mode.RELEASE` or `strip_debug_info` for shipping.
- `state_names` count must match graph state count exactly; ordering is **buffers (registration order), then mutated user inputs (signature order)**.
- `input_names` = non-stateful args only; `output_names` = return values only, **not** mutation outputs.
- Each staged program needs a **unique `entrypoint_name`**.
- `.eval()` your module before export — "Layers such as `BatchNorm` and `Dropout` behave differently in training mode and produce a different graph."
- SAM 3 is a **gated HF model**; you must accept the license and `hf auth login` first.
- `coreai.llm.export` **defaults to the macOS variant** — pass `--platform iOS` for iOS.

## Runtime (Swift)
- `AIModel(contentsOf:)` is `async` **because it specializes** — this is where multi-second first-launch stalls come from.
- `loadFunction(named:)` returns `nil` for unknown names (throws only on load failure). Loading a function is itself "expensive".
- `MutableView.contiguousElements` can be **`nil`** for non-contiguous layouts — handle it.
- `Span<Int>` shapes inside `withUnsafePointer` **don't conform to `Sequence`** (non-escapable) — no `reduce`/`map`.
- `run(inputs:states:outputViews:)` takes `consuming` views — you must `consume` them; they can't be reused.
- Cached specializations are keyed on **`.aimodel` URL + `SpecializationOptions`**. Changing options ⇒ re-specialization. Deleting the source file breaks `init(contentsOf:)` and `cache.model(for:)` — use `bookmarkData` instead.
- Bookmarks are invalidated by **OS updates** and by system storage reclamation.
- `AIModelCache(appGroup:)` returns `nil` on invalid identifier/entitlement.
- Cache entry deletion is **deferred** while a live `AIModel` still references it.

## AOT compilation
- 🔥 **Only compiles for Apple-Intelligence-capable devices**: iPhone/iPad A17 Pro+, Mac M1+, Vision Pro M2+.
- One `.aimodelc` **per architecture** — do not ship them all in the app; host remotely and download the matching one.
- `.aimodelc` works on any OS version **≥** the `--min-deployment-version` you passed.
- Load-time `options` should **match the compute units used at compile time**.
- Residual on-device specialization still happens.

## Modeling / perf
- Transformers without KV caching have **quadratic** cost in sequence length — the Snake demo's visible slowdown.
- Even with states, latency still grows ("growing at a much slower rate", 324:130), just not quadratically.
- Fixed-size KV caches must be allocated for the **maximum possible context length** up-front (324:123) — a memory/latency tradeoff. `CoreAILanguageModel`'s `kvCacheStrategy` exposes `.auto` (256-token initial size for dynamic models) vs `.fixedSize` (pre-allocate at full `maxContextLength`).
- `SpecializationOptions` guidance from Apple's own code: `.neuralEngine` for static-shape/chunked models; `.gpu` + `expectFrequentReshapes = true` for dynamic-shape LLMs.

---

# PART 7 — Source inventory (everything I actually read this session)

**Transcripts (read in full):**
1. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-324.txt` (189 lines) — "Meet Core AI", presenter Ben.
2. `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-326.txt` (216 lines) — Core AI app features, presenter Carina.

**Apple docs mirrors (read in full):**
3. `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Run AI models in your app on Apple silicon.md` — Core AI framework landing page (source: developer.apple.com/documentation/coreai/, fetched 2026-07-27).
4. `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Integrating on-device AI models in your app with Core AI.md`
5. `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Managing model specialization and caching.md`
6. `/Volumes/ExtStor/FM and MLX and CoreAI/docs/Compiling Core AI models ahead of time.md`

**Repos (targeted reads):**
7. `repos/apple__coreai-torch/README.md`
8. `repos/apple__coreai-torch/coreai_torch/__init__.py`
9. `repos/apple__coreai-torch/coreai_torch/converter.py` (lines 60-320)
10. `repos/apple__coreai-torch/tests/test_stateful.py` (lines 1-130; greps through 1330)
11. `repos/apple__coreai-torch/tests/utils.py` (lines 81-106, 560-620)
12. `repos/apple__coreai-torch/docs/getting-started/quickstart.ipynb` (all cells)
13. `repos/apple__coreai-torch/docs/guides/conversion-workflows.ipynb` (all cells)
14. `repos/apple__coreai-torch/docs/api/debugging.md` (full)
15. `repos/apple__coreai-torch/docs/coreai-core/index.md`, `tutorials/run-an-aimodel.ipynb`, `tutorials/construct-a-graph.ipynb` (grep-level)
16. `repos/apple__coreai-models/README.md`
17. `repos/apple__coreai-models/Package.swift` (full)
18. `repos/apple__coreai-models/models/sam3/README.md` (full)
19. `repos/apple__coreai-models/models/qwen3/README.md` (lines 1-80)
20. `repos/apple__coreai-models/swift/Sources/CoreAIShared/Runtime/NDArray+Helpers.swift`
21. `repos/apple__coreai-models/swift/Sources/CoreAIShared/Runtime/ModelStructure.swift` (lines 1-120)
22. `repos/apple__coreai-models/swift/Sources/CoreAIShared/Runtime/FileSize.swift`
23. `repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift` (lines 1-160)
24. `repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAISequentialEngine.swift` (lines 205-300)
25. `repos/apple__coreai-models/swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAIPipelinedEngine.swift` (lines 580-800)
26. `repos/apple__coreai-models/swift/Sources/CoreAIImageSegmenter/ImageSegmenter.swift` (lines 1-140)
27. `repos/apple__coreai-models/swift/Sources/CoreAIImageSegmenter/ImageSegmentationEngine.swift` (lines 1-90)
28. `repos/noemaai-labs__noema-ios/DocumentationforAPIs&SDKs/CoreAI/DebuggingAndProfiling.md` — **third-party mirror, treat as unverified.**

**Directory listings used as evidence:** `repos/apple__coreai-models/models/` (catalog), `swift/Sources/**` (module layout), `docs/` (mirror inventory).

---

# PART 8 — Open questions / unverified

1. **What exactly does the Xcode model viewer's "General" tab show for deployment targets?** 326:82-84 says iOS 27.0 / macOS 27.0 are shown; `docs/Integrating…` doesn't list this field. Needs a screenshot or a newer doc.
2. **The 623 MB SAM 3 figure** doesn't reconcile with the repo's current lite export (848M params, w4/w6 palettized). Which export produced 623 MB?
3. **Is the 70B LLM claim (324:21) Mac-only?** No hardware qualifier given. What is the actual max model size Core AI supports on iPhone vs Mac?
4. **`AIModel` value semantics:** struct or class? Docs say "If an `AIModel` instance still uses a cache entry, Core AI defers deletion until that instance is deallocated" — implies reference semantics or a ref-counted handle. Not confirmed.
5. **`InferenceFunction.Outputs` exact type name.** Doc links `/documentation/coreai/inferencefunction/outputs/remove(_:)`, so `InferenceFunction.Outputs` is right, but its full API (iteration, subscripting) is unknown.
6. **`NDArray.ScalarType` full case list.** Confirmed: `.float16`, `.float32`, `.int32`. Others (int8, uint8, sub-byte types, bf16?) unknown.
7. **`ComputeUnitKind` full case list.** Confirmed `.gpu`, `.neuralEngine` (from repo) and CPU implied by `.cpuOnly`. Exact spelling of the CPU case unconfirmed.
8. **`AIModelCache.Policy` full case list.** Only `.persistent` and "the default policy" are named. The doc has an empty bullet list at line 89-90 ("The system can remove specialized assets from the cache under three conditions:") — the three conditions were stripped by the mirror. **Need the original page.**
9. **`coreai-build` full flag list** — only `compile`, `--platform`, `--min-deployment-version`, `--output`, `--preferred-compute`, `--help` are confirmed. Are there other subcommands (e.g. `inspect`, `verify`)? What are valid `--preferred-compute` values?
10. **Core AI Debugger app**: distribution channel (developer.apple.com/core-ai-debugger/), exact UI, whether it can attach to a running app or only work offline on `.aimodel` files. Only the third-party summary describes the workflow.
11. **Core AI debug gauge**: exact metrics streamed, whether it's automatic or requires a scheme option.
12. **Core AI instrument**: exact track/lane names in the Instruments template ("inference intervals", "model load event", "specialization sub-event" are the only named ones).
13. **`@Generable` field names** in the vocab card example are reconstructed — the transcript only says "a word field, a translation field, an example sentence field".
14. **The `generating:` argument label** on `session.respond(to:generating:)` — assumed from FM, not verified in this session.
15. **`ImageDescriptor` / image-typed inputs**: how are they marked at conversion time in `coreai-torch`? Neither transcript covers it.
16. **`AIModelAsset` Swift API surface** — listed as an Essential in the framework index but never used in any code sample I read.
17. **`AssetError` cases** — unknown.
18. **Does Core AI have a Swift-side model *authoring* API?** 324:135 says the *Python* package supports "directly authoring your model with Core AI APIs" (confirmed: `coreai._compiler.dialects.coreai as ops` + `AIProgram.save_asset`). No Swift authoring API observed.
19. **`ImageSegmenter(resourcesAt:)`** — the `models/sam3/README.md` shows this initializer but `ImageSegmenter.swift` only shows `init(engine:tokenizer:)` and `init(engine:tokenizerFolder:)`. There is presumably a `resourcesAt:` convenience in an extension I didn't read.
20. **"Discover Apple-Hosted Background Assets"** (326:149) — cited as "from last year's WWDC" i.e. WWDC25. Not in our transcript set.
