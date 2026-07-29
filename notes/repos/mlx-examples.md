# `ml-explore/mlx-examples` — deep dive (Python MLX example zoo)

**Local clone:** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-examples`
**HEAD at time of reading:** `796f5b53cab69a3d48a44233ce21aae889e94a08` — "Add wan 2.1 model (#1409)", **2026-04-06**
**License:** MIT (root `LICENSE`)
**Everything below was read from files in this clone in this session.** Line numbers refer to the files at this commit.

---

## 0. What this repo is (and is NOT) as of 2026-04

From root `README.md`:

> This repo contains a variety of standalone examples using the [MLX framework](https://github.com/ml-explore/mlx).
> The [MNIST](mnist) example is a good starting point to learn how to use MLX. … **Check-out [MLX LM](https://github.com/ml-explore/mlx-lm) for a more fully featured Python package for LLMs with MLX.**

**Critical structural fact:** `mlx_lm` was *removed* from this repo. `llms/README.md` is now a single move notice:

```
# MOVE NOTICE

The mlx-lm package has moved to a [new repo](https://github.com/ml-explore/mlx-lm).

The package has been removed from the MLX Examples repo. Send new contributions
and issues to the MLX LM repo.
```

Removal commit: `c243370 2025-03-18 Awni Hannun "remove mlx lm (#1353)"` — deleted `llms/mlx_lm/**` including `LORA.md`, `SERVER.md`, `MERGE.md`, `MANAGE.md`, `UPLOAD.md`, `cache_prompt.py`, `chat.py`, `convert.py`, etc. Older git history in this repo (depth-50 clone still contains many mlx-lm commits like `f621218 Tool use example (#1316)`, `e150621 Adding multiple optimizers to mlx lm`, `b7f742e Mixed quant recipes (#1300)`) refers to code that **no longer lives here**.

**There is no `pyproject.toml`, no `setup.py`, and no root package.** Every subdirectory is a standalone script folder with its own `requirements.txt`. The only installable package in the tree is `whisper/` (`mlx-whisper` on PyPI, has its own `setup.py`).

There is **no** `AGENTS.md` / `CLAUDE.md` in this repo.

### Directory census (23 top-level dirs)

| Dir | Domain | Entry point(s) |
|---|---|---|
| `bert/` | BERT encoder | `convert.py`, `model.py`, `test.py` |
| `cifar/` | ResNet on CIFAR-10 (+ distributed) | `main.py` |
| `clip/` | CLIP joint text/image embeddings | `convert.py`, `clip.py`, `linear_probe.py`, `test.py` |
| `cvae/` | Conv VAE on MNIST | `main.py` |
| `encodec/` | Meta EnCodec audio codec | `example.py`, `convert.py`, `test.py`, `benchmarks/` |
| `flux/` | FLUX.1 diffusion (T2I + LoRA dreambooth + distributed) | `txt2image.py`, `dreambooth.py`, `generate_interactive.py` |
| `gcn/` | Graph conv net on Cora | `main.py` |
| `llava/` | LLaVA VLM | `generate.py`, `test.py` |
| `llms/` | move notice + legacy single-model examples | `llama/`, `mistral/`, `mixtral/`, `gguf_llm/`, `speculative_decoding/` |
| `lora/` | Standalone LoRA/QLoRA fine-tune | `lora.py`, `convert.py`, `fuse.py` |
| `mnist/` | MLP on MNIST (hello-world) | `main.py` |
| `musicgen/` | Meta MusicGen text→music | `generate.py`, `benchmarks/` |
| `normalizing_flow/` | RealNVP density estimation | `main.py` |
| `segment_anything/` | SAM | `convert.py`, `main.py`, 2 notebooks |
| `speechcommands/` | Keyword Transformer (KWT) | `main.py` |
| `stable_diffusion/` | SD 2.1 / SDXL-turbo | `txt2image.py`, `image2image.py` |
| `t5/` | T5 / FLAN-T5 encoder-decoder | `t5.py`, `hf_t5.py` |
| `transformer_lm/` | Decoder-only LM training from scratch | `main.py` |
| `video/wan2.1/` | Wan2.1 T2V + I2V **(newest, 2026-04)** | `txt2video.py`, `img2video.py` |
| `whisper/` | `mlx-whisper` pip package | `mlx_whisper/cli.py`, `convert.py`, `benchmark.py`, `test.py` |
| `wwdc25/` | **WWDC25 session code** (2 notebooks + Xcode project) | `.ipynb` × 2, `WWDC25MLXSwiftExamples/` |

### Contributing / tooling

`CONTRIBUTING.md`: fork + PR, tests required, ≥1 review, `pre-commit`.
`.pre-commit-config.yaml`:
```yaml
repos:
-   repo: https://github.com/psf/black-pre-commit-mirror
    rev: 25.1.0
    hooks:
    -   id: black
-   repo: https://github.com/pycqa/isort
    rev: 6.0.0
    hooks:
    -   id: isort
        args:
            - --profile=black
```
CI (`.github/workflows/pull_request.yml`, switched to GH Actions in `7ddca42`, 2025-11-20): **lint only** — `ubuntu-22.04`, Python `3.10`, `pre-commit/action@v3.0.1`. **No functional tests run in CI** (all example `test.py` files are manual).

---

## 1. `wwdc25/` — WWDC25 MLX session code (HIGHEST-VALUE DIRECTORY)

Added by `4b2a0df 2025-06-10 Shashank "adding wwdc25 samples (#1370)"` (6053 insertions).

`wwdc25/README.md` links two YouTube videos (`UbzOBg8fsxo`, `tn2Hvw7eCsw`) and describes two sessions:
1. **"Get started with MLX for Apple silicon"** → `Get_started_with_MLX_for_Apple_silicon.ipynb`
2. **"Explore large language models on Apple silicon with MLX"** → `Explore_language_models_on_Apple_silicon_with_MLX.ipynb`
3. **Xcode project** → `WWDC25MLXSwiftExamples/`

### 1.1 Exact pinned dependency set — `wwdc25/requirements.txt` (verbatim)

```
mlx==0.25.2
mlx-data==0.1.0
mlx-lm==0.24.1
torch==2.7.0
transformers==4.52.3
datasets==3.6.0
huggingface-hub==0.32.2
numpy
jupyterlab
ipykernel
matplotlib
ipywidgets
```

This is the **authoritative WWDC25-era version matrix for MLX Python**: `mlx 0.25.2`, `mlx-lm 0.24.1`, `mlx-data 0.1.0`.

### 1.2 Environment setup (verbatim from `wwdc25/README.md`)

```bash
# venv
python3 -m venv mlx
source mlx/bin/activate
pip install -r requirements.txt
```
```bash
# conda
conda create -n mlx python=3.12 -y
conda activate mlx
pip install -r requirements.txt
```
```bash
jupyter lab      # opens http://localhost:8888/lab
```

### 1.3 `Get_started_with_MLX_for_Apple_silicon.ipynb` — cell-by-cell

Notebook metadata claims kernel `python 3.9.17` (stale metadata; requirements say 3.12).

**Cell 2 — basics**
```python
import mlx.core as mx
a = mx.array([1, 2, 3])
b = mx.array([4, 5, 6])
c = a + b
shape = c.shape          # (3,)
dtype = c.dtype          # mlx.core.int32
```
Output: `Result c: array([5, 7, 9], dtype=int32)`

**Cell 4 — unified memory / per-op stream selection**
```python
c = mx.add(a, b, stream=mx.gpu)
d = mx.multiply(a, b, stream=mx.cpu)
```
> `c computed on the GPU: array([5, 7, 9], dtype=int32)` / `d computed on the CPU: array([4, 10, 18], dtype=int32)`

**Cell 6 — lazy evaluation**; three ways to force eval: `print(c)`, `c.tolist()`, `mx.eval(c)`.

**Cell 8 — function transforms / higher-order grads**
```python
dfdx = mx.grad(sin)
d2fdx2 = mx.grad(mx.grad(mx.sin))
d2fdx2(mx.array(1.0))    # array(-0.841471, dtype=float32)
```

**Cell 10 — `mx.vmap` over grads + matplotlib**
```python
x = mx.linspace(0, 2 * mx.pi, 400)
cos = mx.vmap(dfdx)
negative_sin = mx.vmap(d2fdx2)
```
(Note `mx.pi` exists as a module constant.)

**Cells 13/15 — MLX NN + training loop (side-by-side against PyTorch)**
```python
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim

class MLP(nn.Module):
    """A simple MLP."""
    def __init__(self, dim, h_dim):
        super().__init__()
        self.linear1 = nn.Linear(dim, h_dim)
        self.linear2 = nn.Linear(h_dim, dim)

    def __call__(self, x):          # NB: __call__, not forward
        x = self.linear1(x)
        x = nn.relu(x)
        x = self.linear2(x)
        return x

n_epochs = 5
input_dim, hidden_dim, num_samples = 10, 50, 1000
model = MLP(input_dim, hidden_dim)

def loss_fn(model, X, y):
    return nn.losses.mse_loss(model(X), y)

loss_and_grad_fn = nn.value_and_grad(model, loss_fn)
optimizer = optim.Adam(learning_rate=0.01)

X_train = mx.random.normal([num_samples, input_dim])
y_train = mx.random.normal([num_samples, input_dim])

for epoch in range(n_epochs):
    loss, grads = loss_and_grad_fn(model, X_train, y_train)
    model.update(optimizer.apply_gradients(grads, model))
    mx.eval(model.parameters(), optimizer.state)
```
> `Final Loss after 5 steps: 1.0052` (PyTorch equivalent printed `1.0028`)

Note the WWDC form uses `model.update(optimizer.apply_gradients(grads, model))`; every other example in the repo uses the shorter `optimizer.update(model, grads)`.

**Cell 21 — `mx.compile`**
```python
@mx.compile
def compiled_gelu(x):
    return x * (1 + mx.erf(x / math.sqrt(2))) / 2
```

**Cell 23 — `mlx.core.fast`**
```python
y_fast = mx.fast.rms_norm(x, weight, eps=1e-5)   # matches hand-written rms_norm exactly
```

**Cell 25 — custom Metal kernel (`mx.fast.metal_kernel`) — full API**
```python
source = """
    uint elem = thread_position_in_grid.x;
    out[elem] = metal::exp(inp[elem]);
"""
kernel = mx.fast.metal_kernel(
    name="myexp",
    input_names=["inp"],
    output_names=["out"],
    source=source,
)
x = mx.array([1.0, 2.0, 3.0])
out = kernel(
    inputs=[x],
    grid=(x.size, 1, 1),
    threadgroup=(256, 1, 1),
    output_shapes=[x.shape],
    output_dtypes=[x.dtype],
)[0]
# array([2.71828, 7.38906, 20.0855], dtype=float32)
```
Notes: kernel body is the *body only* (no signature); inputs/outputs are named buffers; `kernel(...)` returns a **list**.

**Cell 27 — low-level quantization ops**
```python
quantized_weight, scales, biases = mx.quantize(weight, bits=4, group_size=32)
y = mx.quantized_matmul(x, quantized_weight, scales=scales, biases=biases,
                        bits=4, group_size=32)
w_orig = mx.dequantize(quantized_weight, scales=scales, biases=biases,
                       bits=4, group_size=32)
```

**Cell 28 — module-level quantization + repr change**
```python
nn.quantize(model, bits=4, group_size=32)
```
Before: `(layers.1): Linear(input_dims=32, output_dims=32, bias=True)`
After: `(layers.1): QuantizedLinear(input_dims=32, output_dims=32, bias=True, group_size=32, bits=4)`
`nn.Embedding` → `QuantizedEmbedding(100, 32, group_size=32, bits=4)`

**Cell 29 — distributed**
```python
group = mx.distributed.init()
world_size = group.size()
rank = group.rank()
x_sum = mx.distributed.all_sum(mx.array([1.0]))
```

### 1.4 `Explore_language_models_on_Apple_silicon_with_MLX.ipynb` — cell-by-cell

**Cell 1 — required env var** (avoids HF tokenizer fork warnings in Jupyter):
```python
import os
os.environ["TOKENIZERS_PARALLELISM"]="false"
```

**Cell 3 — DeepSeek V3 670B demo (commented out; terminal only)**
```
# mlx_lm.chat --model mlx-community/DeepSeek-V3-0324-4bit
```
> Note 1: This example requires **Mac Studio M3 Ultra with 512 GB of unified memory**.
> Note 2: … run it in the terminal, since Jupyter Notebook output doesn't allow turn-by-turn chat interaction

**Cells 6/8 — `mlx_lm.generate` CLI**
```bash
mlx_lm.generate --model "mlx-community/Mistral-7B-Instruct-v0.3-4bit" \
                --prompt "Write a quick sort in Swift"

mlx_lm.generate --model "mlx-community/Mistral-7B-Instruct-v0.3-4bit" \
                --prompt "Write a quick sort in Swift" \
                --top-p 0.5 \
                --temp 0.2 \
                --max-tokens 1024
```

**Cell 10 — Python API**
```python
from mlx_lm import load, generate

model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.3-4bit")
prompt = "Write a quick sort in Swift"
messages = [{"role": "user", "content": prompt}]
prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
text = generate(model, tokenizer, prompt=prompt, verbose=True)
```

**Cells 13–15 — introspection**: `print(model)`, `print(model.parameters())`, `print(model.layers[0].self_attn)`.

**Cells 17/19 — prompt/KV cache reuse across turns**
```python
from mlx_lm.models.cache import make_prompt_cache

cache = make_prompt_cache(model)
text = generate(model, tokenizer, prompt=prompt, prompt_cache=cache, verbose=True)

# follow-up turn reuses the same `cache` object
prompt = "how can I explain it to a five year old?"
messages = [{"role": "user", "content": prompt}]
prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
text = generate(model, tokenizer, prompt=prompt, prompt_cache=cache, verbose=True)
```

**Cell 21 — `mlx_lm.convert` CLI (quantize)**
```bash
mlx_lm.convert --hf-path "mlx-community/Mistral-7B-Instruct-v0.3" \
               --mlx-path "./mistral-7b-v0.3-4bit" \
               --dtype float16 \
               --quantize --q-bits 4 --q-group-size 64
```

**Cell 24 — mixed-precision quantization via `quant_predicate` (Python)**
```python
from mlx_lm.convert import convert

def mixed_quantization(layer_path, layer, model_config):
    if "lm_head" in layer_path or "embed_tokens" in layer_path:
        return {"bits": 6, "group_size": 64}
    elif hasattr(layer, "to_quantized"):
        return {"bits": 4, "group_size": 64}
    else:
        return False

convert(
    hf_path="mistralai/Mistral-7B-Instruct-v0.3",
    mlx_path="./mistral-7b-v0.3-mixed-4-6-bit",
    quantize=True,
    quant_predicate=mixed_quantization,
)
```
Predicate signature: `(layer_path: str, layer, model_config) -> dict | False`.

**Cell 28 — LoRA fine-tune CLI (commented out in the notebook)**
```bash
mlx_lm.lora --model "./mistral-7b-v0.3-4bit" --train --data ./data \
            --iters 300 --batch-size 8 --mask-prompt --learning-rate 1e-5
```
Note `--mask-prompt` (loss on completion only). Adapters land in `./adapters`.

**Cell 30 — inference with adapter**
```bash
mlx_lm.generate --model "./mistral-7b-v0.3-4bit" \
                --prompt "Who played in the latest super bowl?" \
                --adapter "adapters"
```

**Cells 32/34 — fuse then generate**
```bash
mlx_lm.fuse --model "./mistral-7b-v0.3-4bit" \
            --adapter-path "adapters" \
            --save-path "fused-mistral-7b-v0.3-4bit"

mlx_lm.generate --model "./fused-mistral-7b-v0.3-4bit" \
                --prompt "Who played in the latest super bowl?" \
                --temp 0.6
```

### 1.5 `wwdc25/data/` — the fine-tuning dataset format

- `train.jsonl` — **1800** lines, `valid.jsonl` — **144** lines, `all.jsonl` — **1944** lines.
- Keys per line: exactly `{"prompt", "completion"}` (verified by parsing all three files).
- Topic: Super Bowl LIX Q&A (post-training-cutoff knowledge injection demo).
- Sample line (`valid.jsonl:1`):
```json
{"prompt": "How many yards did Patrick Mahomes throw for?", "completion": "Patrick Mahomes threw for 257 yards in Super Bowl LIX."}
```
**Gotcha:** this is `prompt`/`completion` format, whereas the standalone `lora/` example in this same repo uses `{"text": ...}`. They are different loaders.

### 1.6 `wwdc25/WWDC25MLXSwiftExamples/` — Xcode project

**Build settings** (from `project.pbxproj`): `objectVersion = 77`, `LastUpgradeCheck = 1620`, `MACOSX_DEPLOYMENT_TARGET = 15.2`, `SWIFT_VERSION = 5.0`, command-line tool target `WWDC25MLXSwiftExamples`.

**SPM dependencies declared in pbxproj:**
- `https://github.com/ml-explore/mlx-swift` — `upToNextMajorVersion`, `minimumVersion = 0.25.4`
- `https://github.com/ml-explore/mlx-swift-examples/` — `upToNextMajorVersion`, `minimumVersion = 2.25.4`

**Products linked:** `MLX`, `MLXFFT`, `MLXFast`, `MLXLinalg`, `MLXNN`, `MLXLLM`, `MLXLMCommon`.

**`Package.resolved` (exact pins):**

| package | version | revision |
|---|---|---|
| mlx-swift | 0.25.4 | `b94473af8c50010edba87a48bbd60c3d7f949852` |
| mlx-swift-examples | 2.25.4 | `8e41311a3c17e902441cfcaa46629244c9758afd` |
| swift-transformers (huggingface) | 0.1.21 | `c2f302a…` |
| Jinja (johnmai-dev) | 1.1.2 | `31c4dd3…` |
| GzipSwift (1024jp) | 6.0.1 | `731037f…` |
| swift-argument-parser | 1.4.0 | `0fbc884…` |
| swift-collections | 1.2.0 | `c180559…` |
| swift-numerics | 1.0.3 | `e0ec0f5…` |

**`main.swift` (verbatim, 32 lines):**
```swift
// WWDC Session: Get started with MLX for Apple silicon

// Swift
import MLX

// Make an array
let a = MLXArray([1, 2, 3])
let b = MLXArray([1, 2, 3])
let c = a + b
let shape = c.shape
let dtype = c.dtype

print("a: \(a)")
print("b: \(b)")
print("c = a + b: \(c)")
print("shape: \(shape)")
print("dtype: \(dtype)")

// WWDC Session: Explore large language models on Apple silicon with MLX

/// Example 1: Simple MLXLM Swift example using Mistral-7B-Instruct-v0.3-4bit
try await SimpleMLXLM()

/// Example 2: Using KVCache and custom TokenIterator with Mistral-7B-Instruct-v0.3-4bit
try await SimpleMLXLMWithKVCache()
```

**`SimpleMLXLM.swift` (verbatim):**
```swift
import Foundation
import MLX
import MLXLMCommon
import MLXLLM

func SimpleMLXLM() async throws {
    // Load the model and tokenizer directly from HF
    let modelId = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    let modelFactory = LLMModelFactory.shared
    let configuration = ModelConfiguration(id: modelId)
    let model = try await modelFactory.loadContainer(configuration: configuration)

    try await model.perform({context in
        // Prepare the prompt for the model
        let prompt = "Write a quicksort in Swift"
        let input = try await context.processor.prepare(input: UserInput(prompt: prompt))

        // Generate the text
        let params = GenerateParameters(temperature: 0.0)
        let tokenStream = try generate(input: input, parameters: params, context: context)
        for await part in tokenStream {
            print(part.chunk ?? "", terminator: "")
        }
    })
}
```

**`SimpleMLXLMWithKVCache.swift` (verbatim, low-level `TokenIterator` + shared cache across two prompts):**
```swift
import Foundation
import MLX
import MLXLMCommon
import MLXLLM

func SimpleMLXLMWithKVCache() async throws {
    let modelId = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    let modelFactory = LLMModelFactory.shared
    let configuration = ModelConfiguration(id: modelId)
    let model = try await modelFactory.loadContainer(configuration: configuration)

    try await model.perform({context in
        let prompt = "Write a quicksort in Swift"
        let input = try await context.processor.prepare(input: UserInput(prompt: prompt))

        // Create the key-value cache
        let generateParameters = GenerateParameters()
        let cache = context.model.newCache(parameters: generateParameters)

        // Low level token iterator
        let tokenIter = try TokenIterator(input: input,
                                          model: context.model,
                                          cache: cache,
                                          parameters: generateParameters)
        let tokenStream = generate(input: input, context: context, iterator: tokenIter)
        for await part in tokenStream {
            print(part.chunk ?? "", terminator: "")
        }

        print("\n=============================================================================\n")

        // Prompt the model again with a follow up questions:
        let newPrompt = "What is it's time complexity?"
        let newInput = try await context.processor.prepare(input: .init(prompt: newPrompt))
        let newTokenIter = try TokenIterator(input: newInput,
                                     model: context.model,
                                     cache: cache,
                                     parameters: generateParameters)

        let newTokenStream = generate(input: newInput, context: context, iterator: newTokenIter)
        for await part in newTokenStream {
            print(part.chunk ?? "", terminator: "")
        }
    })
}
```

**Swift API surface confirmed here** (mlx-swift-examples 2.25.4):
`LLMModelFactory.shared`, `ModelConfiguration(id:)`, `modelFactory.loadContainer(configuration:) async throws`, `container.perform { context in }`, `context.processor.prepare(input: UserInput(prompt:)) async throws`, `GenerateParameters(temperature:)`, free function `generate(input:parameters:context:) throws -> AsyncStream`, `context.model.newCache(parameters:)`, `TokenIterator(input:model:cache:parameters:) throws`, `generate(input:context:iterator:)`, stream element has `.chunk: String?`.

---

## 2. `flux/` — FLUX.1 diffusion (the deepest diffusion example)

`flux/README.md`: ported from `black-forest-labs/flux`; weights from HF Hub.
`flux/requirements.txt`:
```
mlx>=0.18.1
huggingface-hub
regex
numpy
tqdm
Pillow
sentencepiece
```
(`datasets` is an *optional* extra for HF dataset training — README mentions it but it is **not** in requirements.txt.)

### 2.1 Package surface — `flux/flux/__init__.py`
```python
from .datasets import Dataset, load_dataset
from .flux import FluxPipeline
from .lora import LoRALinear
from .sampler import FluxSampler
from .trainer import Trainer
from .utils import (
    load_ae, load_clip, load_clip_tokenizer, load_flow_model,
    load_t5, load_t5_tokenizer, save_config,
)
```

### 2.2 Model configs — `flux/flux/utils.py:30-95`

Two entries in `configs`: `"flux-dev"` and `"flux-schnell"`.

```python
"flux-dev": ModelSpec(
    repo_id="black-forest-labs/FLUX.1-dev",
    repo_flow="flux1-dev.safetensors",
    repo_ae="ae.safetensors",
    ckpt_path=os.getenv("FLUX_DEV"),
    params=FluxParams(
        in_channels=64, vec_in_dim=768, context_in_dim=4096,
        hidden_size=3072, mlp_ratio=4.0, num_heads=24,
        depth=19, depth_single_blocks=38,
        axes_dim=[16, 56, 56], theta=10_000,
        qkv_bias=True, guidance_embed=True),
    ae_path=os.getenv("AE"),
    ae_params=AutoEncoderParams(
        resolution=256, in_channels=3, ch=128, out_ch=3,
        ch_mult=[1, 2, 4, 4], num_res_blocks=2, z_channels=16,
        scale_factor=0.3611, shift_factor=0.1159),
)
```
`flux-schnell` is identical except `repo_id="black-forest-labs/FLUX.1-schnell"`, `repo_flow="flux1-schnell.safetensors"`, `ckpt_path=os.getenv("FLUX_SCHNELL")`, and **`guidance_embed=False`**.

**Env-var overrides for local weights: `FLUX_DEV`, `FLUX_SCHNELL`, `AE`.**

Loaders (`utils.py`): `load_flow_model(name, hf_download=True)`, `load_ae(name, hf_download=True)`, `load_clip(name)` (`text_encoder/config.json` + `text_encoder/model.safetensors`), `load_t5(name)` (reads `text_encoder_2/model.safetensors.index.json` and downloads every shard listed in `weight_map`), `load_clip_tokenizer(name)` (`tokenizer/vocab.json` + `tokenizer/merges.txt`, slices merges `[1 : 49152 - 256 - 2 + 1]`, `max_length=77`), `load_t5_tokenizer(name, pad=True)` → `T5Tokenizer(spiece.model, 256 if "schnell" in name else 512)`.

### 2.3 `FluxPipeline` — `flux/flux/flux.py`

```python
class FluxPipeline:
    def __init__(self, name: str, t5_padding: bool = True):
        self.dtype = mx.bfloat16          # hard-coded bf16
        ...
        self.ae, self.flow, self.clip, self.clip_tokenizer, self.t5, self.t5_tokenizer, self.sampler
```
Key methods and exact signatures:
- `ensure_models_are_loaded()` — `mx.eval` on all four param trees.
- `reload_text_encoders()` — re-`load_t5` / `load_clip` (used after `del`ing them for memory).
- `tokenize(text) -> (t5_tokens, clip_tokens)`.
- `generate_latents(text, n_images=1, num_steps=35, guidance=4.0, latent_size=(64,64), seed=None)` — **generator**; first yield is the conditioning tuple `(x_T, x_ids, txt, txt_ids, vec)`, subsequent yields are `x_t`.
- `decode(x, latent_size=(64,64))` — unpatchifies then `ae.decode`, returns `mx.clip(x + 1, 0, 2) * 0.5`.
- `generate_images(text, n_images, num_steps, guidance, latent_size, seed, reload_text_encoders=True, progress=True)`.
- `training_loss(x_0, t5_features, clip_features, guidance)` — flow-matching loss `(pred + x_0 - eps).square().mean()`.
- `linear_to_lora_layers(rank=8, num_blocks=-1)` — swaps **every `nn.Linear`** in the last `num_blocks` of `double_blocks + single_blocks` (list is reversed first, so `num_blocks` counts from the end).
- `fuse_lora_layers()`.

**2×2 latent patchification + 3-axis RoPE ids (`flux.py:53-71`) — the transferable trick:**
```python
def _prepare_latent_images(self, x):
    b, h, w, c = x.shape
    # Pack the latent image to 2x2 patches
    x = x.reshape(b, h // 2, 2, w // 2, 2, c)
    x = x.transpose(0, 1, 3, 5, 2, 4).reshape(b, h * w // 4, c * 4)

    i = mx.zeros((h // 2, w // 2), dtype=mx.int32)
    j, k = mx.meshgrid(mx.arange(h // 2), mx.arange(w // 2), indexing="ij")
    x_ids = mx.stack([i, j, k], axis=-1)
    x_ids = mx.repeat(x_ids.reshape(1, h * w // 4, 3), b, 0)
    return x, x_ids
```
Comment in source explains: "the first part holds information independent of the spatial position (hence 0s), the 2nd part holds vertical spatial information and the last one horizontal."

### 2.4 `FluxSampler` — `flux/flux/sampler.py` (rectified-flow, 57 lines total)

```python
class FluxSampler:
    def __init__(self, name, base_shift=0.5, max_shift=1.15):
        self._schnell = "schnell" in name

    def _time_shift(self, x, t):
        x1, x2 = 256, 4096
        t1, t2 = self._base_shift, self._max_shift
        exp_mu = math.exp((x - x1) * (t2 - t1) / (x2 - x1) + t1)
        return exp_mu / (exp_mu + (1 / t - 1))

    @lru_cache
    def timesteps(self, num_steps, image_sequence_length, start=1, stop=0):
        t = mx.linspace(start, stop, num_steps + 1)
        if not self._schnell:
            t = self._time_shift(image_sequence_length, t)
        return t.tolist()

    def random_timesteps(self, B, L, dtype=mx.float32, key=None): ...
    def sample_prior(self, shape, dtype=mx.float32, key=None): return mx.random.normal(...)
    def add_noise(self, x, t, noise=None, key=None): return x * (1 - t) + t * noise
    def step(self, pred, x_t, t, t_prev): return x_t + (t_prev - t) * pred
```
Note `@lru_cache` on an instance method (works because args are hashable; caches across instances).
`random_timesteps` for schnell samples `mx.random.randint(1, 5)` / 4 (i.e. one of 0.25/0.5/0.75/1.0), with a `# TODO: Should we upweigh 1 and 0.75?`.

### 2.5 `LoRALinear` — `flux/flux/lora.py` (76 lines, complete)

```python
class LoRALinear(nn.Module):
    @staticmethod
    def from_base(linear: nn.Linear, r: int = 8, dropout: float = 0.0, scale: float = 1.0):
        output_dims, input_dims = linear.weight.shape
        lora_lin = LoRALinear(input_dims=input_dims, output_dims=output_dims,
                              r=r, dropout=dropout, scale=scale)
        lora_lin.linear = linear
        return lora_lin

    def fuse(self):
        linear = self.linear
        bias = "bias" in linear                 # membership test on a Module!
        weight = linear.weight; dtype = weight.dtype
        output_dims, input_dims = weight.shape
        fused_linear = nn.Linear(input_dims, output_dims, bias=bias)
        lora_b = self.scale * self.lora_b.T
        lora_a = self.lora_a.T
        fused_linear.weight = weight + (lora_b @ lora_a).astype(dtype)
        if bias: fused_linear.bias = linear.bias
        return fused_linear

    def __init__(self, input_dims, output_dims, r=8, dropout=0.0, scale=1.0, bias=False):
        super().__init__()
        self.linear = nn.Linear(input_dims, output_dims, bias=bias)
        self.dropout = nn.Dropout(p=dropout)
        self.scale = scale
        scale = 1 / math.sqrt(input_dims)
        self.lora_a = mx.random.uniform(low=-scale, high=scale, shape=(input_dims, r))
        self.lora_b = mx.zeros(shape=(r, output_dims))

    def __call__(self, x):
        y = self.linear(x)
        z = (self.dropout(x) @ self.lora_a) @ self.lora_b
        return y + (self.scale * z).astype(x.dtype)
```
**Default `scale=1.0` here**, vs `scale=20.0` in `lora/models.py`. Different defaults across examples — a real footgun.

### 2.6 DiT layers — `flux/flux/layers.py` (321 lines)

- `_rope(pos, dim, theta)` builds an explicit **2×2 rotation matrix** stack (`mx.stack([cosx, -sinx, sinx, cosx], -1).reshape(..., 2, 2)`) rather than complex numbers.
- `@partial(mx.compile, shapeless=True) def _ab_plus_cd(a,b,c,d): return a*b + c*d` — a **shapeless compiled fused kernel** reused for RoPE application.
- `_attention(q,k,v,pe)` uses `mx.fast.scaled_dot_product_attention(q, k, v, scale=D ** (-0.5))`.
- `timestep_embedding(t, dim, max_period=10000, time_factor=1000.0)`.
- `EmbedND(dim, theta, axes_dim)` concatenates per-axis RoPE along `axis=-3`.
- `MLPEmbedder`, `QKNorm` (two `nn.RMSNorm`), `SelfAttention(dim, num_heads=8, qkv_bias=False)`.
- `Modulation(dim, double)` → `(ModulationOut(shift, scale, gate), Optional[ModulationOut])`; `multiplier = 6 if double else 3`.
- `DoubleStreamBlock` — separate img/txt streams, joint attention over concatenated q/k/v, `nn.LayerNorm(hidden, affine=False, eps=1e-6)`, `nn.GELU(approx="tanh")`. Has `self.sharding_group`; when set, inserts `mx.distributed.all_sum(...)` after attn-proj and after MLP.
- `SingleStreamBlock` — one fused `linear1: hidden→3*hidden + mlp_hidden`, `linear2: hidden+mlp_hidden→hidden`.
- `LastLayer` — `adaLN_modulation = nn.Sequential(nn.SiLU(), nn.Linear(hidden, 2*hidden))`.

### 2.7 Weight sanitization + tensor-parallel sharding — `flux/flux/model.py`

```python
def sanitize(self, weights):
    for k, w in weights.items():
        if k.startswith("model.diffusion_model."): k = k[22:]
        if k.endswith(".scale"): k = k[:-6] + ".weight"
        for seq in ["img_mlp", "txt_mlp", "adaLN_modulation"]:
            if f".{seq}." in k:
                k = k.replace(f".{seq}.", f".{seq}.layers.")
                break
```

```python
from mlx.nn.layers.distributed import shard_inplace, shard_linear

def shard(self, group=None):
    group = group or mx.distributed.init()
    N = group.size()
    if N == 1: return
    for block in self.double_blocks:
        block.num_heads //= N
        block.img_attn.num_heads //= N
        block.txt_attn.num_heads //= N
        block.sharding_group = group
        block.img_attn.qkv = shard_linear(block.img_attn.qkv, "all-to-sharded", segments=3, group=group)
        block.txt_attn.qkv = shard_linear(block.txt_attn.qkv, "all-to-sharded", segments=3, group=group)
        shard_inplace(block.img_attn.proj, "sharded-to-all", group=group)
        shard_inplace(block.txt_attn.proj, "sharded-to-all", group=group)
        block.img_mlp.layers[0] = shard_linear(block.img_mlp.layers[0], "all-to-sharded", group=group)
        block.txt_mlp.layers[0] = shard_linear(block.txt_mlp.layers[0], "all-to-sharded", group=group)
        shard_inplace(block.img_mlp.layers[2], "sharded-to-all", group=group)
        shard_inplace(block.txt_mlp.layers[2], "sharded-to-all", group=group)
    for block in self.single_blocks:
        block.num_heads //= N
        block.hidden_size //= N
        block.linear1 = shard_linear(block.linear1, "all-to-sharded",
                                     segments=[1 / 7, 2 / 7, 3 / 7], group=group)
        block.linear2 = shard_linear(block.linear2, "sharded-to-all",
                                     segments=[1 / 5], group=group)
```
**This is the canonical MLX tensor-parallel recipe**: `shard_linear(layer, "all-to-sharded"|"sharded-to-all", segments=…, group=…)` and `shard_inplace(...)` from `mlx.nn.layers.distributed`; `segments` expresses fused-qkv (3) or fractional splits.

### 2.8 `txt2image.py` — every CLI flag (`flux/txt2image.py:42-66`)

| flag | type/default |
|---|---|
| `prompt` | positional |
| `--model` | `{schnell,dev}`, default `schnell` |
| `--n-images` | int, default `4` |
| `--image-size` | `HxW` string → tuple, default `(512, 512)` |
| `--steps` | int (default = `50` for dev, `2` for schnell — set at line 70) |
| `--guidance` | float, default `4.0` |
| `--n-rows` | int, default `1` |
| `--decoding-batch-size` | int, default `1` |
| `--quantize` / `-q` | store_true |
| `--preload-models` | store_true |
| `--output` | default `out.png` |
| `--save-raw` | store_true |
| `--seed` | int |
| `--verbose` / `-v` | store_true |
| `--adapter` | path to `.safetensors` |
| `--fuse-adapter` | store_true |
| `--no-t5-padding` | `dest=t5_padding, action=store_false` |
| `--force-shard` | store_true |

Quantization predicate (both `txt2image.py:28` and `generate_interactive.py:18`):
```python
def quantization_predicate(name, m):
    return hasattr(m, "to_quantized") and m.weight.shape[1] % 512 == 0
```

Adapter loading with metadata round-trip:
```python
def load_adapter(flux, adapter_file, fuse=False):
    weights, lora_config = mx.load(adapter_file, return_metadata=True)
    rank = int(lora_config["lora_rank"])
    num_blocks = int(lora_config["lora_blocks"])
    flux.linear_to_lora_layers(rank, num_blocks)
    flux.flow.load_weights(list(weights.items()), strict=False)
    if fuse: flux.fuse_lora_layers()
```

Latent-size rounding (`to_latent_size`): image dims rounded **up to a multiple of 16**, then `//8`.

Distributed auto-mode selection (`txt2image.py:81-96`):
```python
group = mx.distributed.init()
if group.size() > 1:
    if args.force_shard or n_images < group.size() or n_images % group.size() != 0:
        flux.flow.shard(group)                 # model-parallel
    else:
        n_images //= group.size(); should_gather = True   # data-parallel
    if args.seed is None:
        args.seed = mx.distributed.all_sum(mx.random.randint(0, 2**20)).item()
    if should_gather:
        args.seed = args.seed + group.rank()
```
Then `decoded = mx.distributed.all_gather(decoded)` if data-parallel.

Memory accounting uses `mx.get_peak_memory()` / `mx.reset_peak_memory()` and `del flux.t5; del flux.clip; del flux.flow` between phases.

### 2.9 `dreambooth.py` — LoRA fine-tuning FLUX

Full flag list (`dreambooth.py:62-153`): `--model {dev,schnell}` (default `dev`), `--guidance 4.0`, `--iterations 600`, `--batch-size 1`, `--resolution 512x512`, `--num-augmentations 5`, `--progress-prompt` (**required**), `--progress-steps 50`, `--progress-every 50`, `--checkpoint-every 50`, `--lora-blocks -1`, `--lora-rank 8`, `--warmup-steps 100`, `--learning-rate 1e-4`, `--grad-accumulate 4`, `--output-dir mlx_output`, positional `dataset`.

Training-loop mechanics worth stealing:
```python
mx.random.seed(0x0F0F0F0F)            # same seed => identical LoRA init on all workers
flux = FluxPipeline("flux-" + args.model)
flux.flow.freeze()
flux.linear_to_lora_layers(args.lora_rank, args.lora_blocks)
mx.random.seed(0xF0F0F0F0 + mx.distributed.init().rank())   # then diverge per worker

warmup = optim.linear_schedule(0, args.learning_rate, args.warmup_steps)
cosine = optim.cosine_decay(args.learning_rate, args.iterations // args.grad_accumulate)
lr_schedule = optim.join_schedules([warmup, cosine], [args.warmup_steps])
optimizer = optim.Adam(learning_rate=lr_schedule)
state = [flux.flow.state, optimizer.state, mx.random.state]
```
Four separately-compiled step functions to make grad accumulation compile-friendly:
`single_step`, `compute_loss_and_grads`, `compute_loss_and_accumulate_grads`, `grad_accumulate_and_step` — all `@partial(mx.compile, inputs=state, outputs=state)`; dispatched by a plain Python `step(...)` router. `average_gradients` (from `mlx.nn.utils`) is applied only on the steps that actually update.

Adapter save with metadata:
```python
mx.save_safetensors(str(out_file),
    dict(tree_flatten(flux.flow.trainable_parameters())),
    metadata={"lora_rank": str(args.lora_rank), "lora_blocks": str(args.lora_blocks)})
```

`Trainer` (`flux/trainer.py`): pre-encodes the whole dataset into latents + T5 + CLIP features once (`encode_dataset()`), applying `num_augmentations` random crop/resize per image; `iterate(batch_size)` permutes latent indices and derives caption indices as `x_indices // n_aug`.

`load_dataset(path)` (`flux/datasets.py`) dispatch order: `train.jsonl` (`LocalDataset`, key `prompt`) → `index.json` (`LegacyDataset`, key `text`, prints a deprecation WARNING) → otherwise treat the string as an **HF dataset id** (`HuggingFaceDataset`, needs `datasets`, uses split `"train"`, columns `image`/`prompt`).

### 2.10 Runnable FLUX commands (verbatim from README)

```shell
python txt2image.py --model schnell --n-images 1 --image-size 256x512 --verbose \
    'A photo of an astronaut riding a horse on Mars.'

python txt2image.py --n-images 4 --n-rows 2 --image-size 256x512 \
    'A photo of an astronaut riding a horse on Mars.'

python dreambooth.py \
    --progress-prompt 'A photo of an sks dog lying on the sand at a beach in Greece' \
    --progress-every 600 --iterations 1200 --learning-rate 0.0001 \
    --lora-rank 4 --grad-accumulate 8 \
    mlx-community/dreambooth-dog6

python txt2image.py --model dev --save-raw --image-size 512x512 --n-images 1 \
    --adapter mlx_output/final_adapters.safetensors \
    --fuse-adapter --no-t5-padding \
    'A photo of an sks dog lying on the sand at a beach in Greece'

# distributed training on 4 machines (same effective batch: iters/4, grad-accum/4)
mlx.launch --verbose --hostfile hostfile.json -- python dreambooth.py \
    --progress-prompt '...' --progress-every 150 --iterations 300 \
    --learning-rate 0.0001 --lora-rank 4 --grad-accumulate 2 \
    mlx-community/dreambooth-dog6

# distributed generation
mlx.launch --verbose --hostfile hostfile.json -- \
    python txt2image.py --model schnell --n-images 8 --image-size 512x512 --verbose \
    'A photo of an astronaut riding a horse on Mars'
```

Dreambooth `train.jsonl` format:
```jsonl
{"image": "00.jpg", "prompt": "A photo of sks dog"}
```

README gotchas (direct quotes):
- "**FLUX finetuning requires approximately 50GB of RAM. QLoRA is coming soon** and should reduce this number significantly."
- "on an M2 Ultra it takes a bit more than 1 hour" (1200 iters, rank 4, grad-accum 8).
- "FLUX pads the prompt to a specific size of **512 tokens for the dev model and 256 for the schnell model**. Not applying padding results in faster generation but it is not clear how it may affect the generated images."
- For model-parallel: "we suggest that you use a thunderbolt ring" and "you may want to also pass `--env MLX_METAL_FAST_SYNCH=1` to `mlx.launch` which is an experimental setting that reduces the CPU/GPU synchronization overhead."

`generate_interactive.py`: REPL with commands `q` (quit), `s HxW` (size), `n S` (steps), `h` (help); flags `--quantize/-q`, `--model {schnell,dev}`, `--output out.png`. Auto-shards when `group.size() > 1`.

---

## 3. `stable_diffusion/` — SD 2.1 base + SDXL-turbo

`requirements.txt`: `mlx>=0.11`, `huggingface-hub`, `regex`, `numpy`, `tqdm`, `Pillow`.

Supported model ids (`stable_diffusion/model_io.py:16-46`):
```python
_DEFAULT_MODEL = "stabilityai/stable-diffusion-2-1-base"
_MODELS = {
  "stabilityai/sdxl-turbo": {unet_config, unet, text_encoder_config, text_encoder,
     text_encoder_2_config, text_encoder_2, vae_config, vae, diffusion_config,
     tokenizer_vocab, tokenizer_merges, tokenizer_2_vocab, tokenizer_2_merges},
  "stabilityai/stable-diffusion-2-1-base": { ... same minus the *_2 keys ... },
}
```
Each value maps a logical key to an HF-repo relative file, e.g. `"unet": "unet/diffusion_pytorch_model.safetensors"`, `"diffusion_config": "scheduler/scheduler_config.json"`.

### 3.1 `StableDiffusion` / `StableDiffusionXL` (`stable_diffusion/__init__.py`, 306 lines)

```python
class StableDiffusion:
    def __init__(self, model: str = _DEFAULT_MODEL, float16: bool = False): ...
    def ensure_models_are_loaded(self)
    def generate_latents(self, text, n_images=1, num_steps=50, cfg_weight=7.5,
                         negative_text="", latent_size=(64,64), seed=None)   # generator
    def generate_latents_from_image(self, image, text, n_images=1, strength=0.8,
                                    num_steps=50, cfg_weight=7.5, negative_text="", seed=None)
    def decode(self, x_t)   # autoencoder.decode then clip(x/2+0.5, 0, 1)
```
`StableDiffusionXL` overrides: uses `SimpleEulerAncestralSampler`; keeps `text_encoder_1/tokenizer_1` and adds `text_encoder_2` (`model_key="text_encoder_2"`) + `tokenizer_2` (`merges_key="tokenizer_2_merges"`, `vocab_key="tokenizer_2_vocab"`); conditioning = `concat(enc1.hidden_states[-2], enc2.hidden_states[-2], axis=-1)` plus `pooled_output` from encoder 2; defaults `num_steps=2, cfg_weight=0.0`; feeds micro-conditioning
```python
text_time = (pooled_conditioning,
             mx.array([[512, 512, 0, 0, 512, 512.0]] * len(pooled_conditioning)))
```

CFG batching (`_denoising_step`): duplicates the batch (`mx.concatenate([x_t]*2)`) only when `cfg_weight > 1`, then `eps_pred = eps_neg + cfg_weight * (eps_text - eps_neg)`.

### 3.2 Samplers — `stable_diffusion/sampler.py` (105 lines, complete)

`SimpleEulerSampler(config: DiffusionConfig)` builds sigmas from betas:
```python
betas = _linspace(beta_start**0.5, beta_end**0.5, num_train_steps).square()   # "scaled_linear"
alphas_cumprod = mx.cumprod(1 - betas)
self._sigmas = mx.concatenate([mx.zeros(1), ((1 - alphas_cumprod) / alphas_cumprod).sqrt()])
```
API: `max_time` property, `sample_prior(shape, dtype, key)`, `add_noise(x, t, key)`, `sigmas(t)` (linear interp via `_interp`), `timesteps(num_steps, start_time=None, dtype)` → list of `(t, t_prev)` pairs, `step(eps_pred, x_t, t, t_prev)`.
`SimpleEulerAncestralSampler` overrides `step` with `sigma_up`/`sigma_down` + extra noise.

`DiffusionConfig` defaults: `beta_schedule="scaled_linear"`, `beta_start=0.00085`, `beta_end=0.012`, `num_train_steps=1000`.
`AutoencoderConfig`: `latent_channels_out=8`, `latent_channels_in=4`, `block_out_channels=(128,256,512,512)`, `scaling_factor=0.18215`.
`UNetConfig`: `block_out_channels=(320,640,1280,1280)`, `num_attention_heads=(5,10,20,20)`, `cross_attention_dim=(1024,)*4`, `down_block_types=("CrossAttnDownBlock2D",)*3 + ("DownBlock2D",)`, plus SDXL-only `addition_embed_type`, `addition_time_embed_dim`, `projection_class_embeddings_input_dim`.

### 3.3 Weight remapping (`model_io.py:49-95`) — HF diffusers → MLX

`map_unet_weights` rules (transferable when porting any diffusers UNet):
- `downsamplers.0.conv` → `downsample`; `upsamplers.0.conv` → `upsample`
- `mid_block.resnets.0|attentions.0|resnets.1` → `mid_blocks.0|1|2`
- `to_k/to_q/to_v/to_out.0` → `key_proj/query_proj/value_proj/out_proj`
- `ff.net.2` → `linear3`; `ff.net.0.proj` → **split in half** into `linear1` + `linear2` (GEGLU)
- `conv_shortcut.weight` → `.squeeze()`
- 4-D `proj_in`/`proj_out` (1×1 conv) → `.squeeze()` to Linear
- any remaining 4-D weight → `.transpose(0, 2, 3, 1)` (**NCHW → NHWC**), then `.reshape(-1).reshape(shape)` to force contiguity.
`map_clip_text_encoder_weights` strips `text_model.` / `embeddings.` / `encoder.` prefixes and renames `self_attn.`→`attention.`, `q/k/v_proj.`→`query/key/value_proj.`, `mlp.fc1/fc2`→`linear1/linear2`.

### 3.4 CLI

`txt2image.py`: `prompt`, `--model {sd,sdxl}` (default **sdxl**), `--n_images 4`, `--steps`, `--cfg`, `--negative_prompt ""`, `--n_rows 1`, `--decoding_batch_size 1`, `--no-float16` (`dest=float16`), `--quantize/-q`, `--preload-models`, `--output out.png`, `--seed`, `--verbose/-v`.
Defaults chosen at runtime: sdxl → `cfg=0.0, steps=2`; sd → `cfg=7.5, steps=50`.
Quantization: text encoders `nn.quantize(..., class_predicate=lambda _, m: isinstance(m, nn.Linear))`; UNet `nn.quantize(sd.unet, group_size=32, bits=8)`.

`image2image.py`: adds positional `image`, `--strength 0.9`; auto-bumps steps when `int(steps*strength) < 1`; downsamples input so W,H are divisible by **64** (`Image.NEAREST`).

Commands:
```shell
python txt2image.py "A photo of an astronaut riding a horse on Mars." --n_images 4 --n_rows 2
python image2image.py --strength 0.5 original.png 'A lit fireplace'
python txt2image.py --n_images 4 -q -v --output still-life.png \
  "A painting of a vase on a wooden table, dark background, still life."
```
README claim: with `-q` (text encoders 4-bit, unet 8-bit) images generate on an **8GB M1 Mac mini with no swapping**.

**Gotcha:** `stable_diffusion/*.py` still call the deprecated `mx.metal.get_peak_memory()` while `flux/txt2image.py` and `video/wan2.1/*` use the newer top-level `mx.get_peak_memory()` / `mx.reset_peak_memory()`. `flux/dreambooth.py:273` also still uses `mx.metal.get_peak_memory()`.

---

## 4. `whisper/` — the `mlx-whisper` pip package (ASR)

Package version: `mlx_whisper/_version.py` → `__version__ = "0.4.3"`.

`setup.py`: name `mlx-whisper`, `python_requires=">=3.8"`, `license="MIT"`, `author_email="mlx@group.apple.com"`, console script:
```python
entry_points={"console_scripts": ["mlx_whisper = mlx_whisper.cli:main"]}
```
`mlx_whisper/requirements.txt`:
```
mlx>=0.11
numba
numpy
torch
tqdm
more-itertools
tiktoken
huggingface_hub
scipy
```
(`torch` is needed only for `convert.py`/tests; `numba` for DTW in `timing.py`.)

`mlx_whisper/__init__.py`:
```python
from . import audio, decoding, load_models
from ._version import __version__
from .transcribe import transcribe
```

### 4.1 CLI — every flag (`mlx_whisper/cli.py:15-202`)

`mlx_whisper AUDIO [AUDIO ...]` (use `-` to read from **stdin**).

| flag | default | notes |
|---|---|---|
| `--model` | `mlx-community/whisper-tiny` | dir or HF repo |
| `--output-name` | `None` | defaults to input stem, or `content` for stdin |
| `--output-dir` / `-o` | `.` | |
| `--output-format` / `-f` | `txt` | `{txt,vtt,srt,tsv,json,all}` |
| `--verbose` | `True` | `str2bool` (`True`/`False` literal strings only) |
| `--task` | `transcribe` | `{transcribe,translate}` |
| `--language` | `None` | choices = `LANGUAGES` keys + titled `TO_LANGUAGE_CODE` keys |
| `--temperature` | `0` | |
| `--best-of` | `5` | `optional_int` (accepts `None`) |
| `--patience` | `None` | beam search patience |
| `--length-penalty` | `None` | |
| `--suppress-tokens` | `"-1"` | comma-separated ids; `-1` = default non-speech set |
| `--initial-prompt` | `None` | |
| `--condition-on-previous-text` | `True` | |
| `--fp16` | `True` | |
| `--compression-ratio-threshold` | `2.4` | |
| `--logprob-threshold` | `-1.0` | |
| `--no-speech-threshold` | `0.6` | |
| `--word-timestamps` | `False` | |
| `--prepend-punctuations` | `"\"'“¿([{-"` | |
| `--append-punctuations` | `"\"'.。,，!！?？:：”)]}、"` | |
| `--highlight-words` | `False` | requires `--word-timestamps True` |
| `--max-line-width` | `None` | requires word timestamps |
| `--max-line-count` | `None` | warns if used without `--max-line-width` |
| `--max-words-per-line` | `None` | warns if combined with `--max-line-width` |
| `--hallucination-silence-threshold` | `None` | requires word timestamps |
| `--clip-timestamps` | `"0"` | `start,end,start,end,...` seconds |

Argparse validation: `parser.error(f"--{argop} requires --word-timestamps True")` if any word-option is set without word timestamps.

CLI usage from README:
```sh
mlx_whisper audio_file.mp3
some-process | mlx_whisper -
mlx_whisper -h
```
Requires `ffmpeg` on PATH (`brew install ffmpeg`).

### 4.2 Python API

```python
import mlx_whisper
text = mlx_whisper.transcribe(speech_file)["text"]
result = mlx_whisper.transcribe(speech_file, path_or_hf_repo="models/large")
output = mlx_whisper.transcribe(speech_file, word_timestamps=True)
print(output["segments"][0]["words"])
```

Full signature (`transcribe.py:62-79`):
```python
def transcribe(
    audio: Union[str, np.ndarray, mx.array],
    *,
    path_or_hf_repo: str = "mlx-community/whisper-turbo",
    verbose: Optional[bool] = None,
    temperature: Union[float, Tuple[float, ...]] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    compression_ratio_threshold: Optional[float] = 2.4,
    logprob_threshold: Optional[float] = -1.0,
    no_speech_threshold: Optional[float] = 0.6,
    condition_on_previous_text: bool = True,
    initial_prompt: Optional[str] = None,
    word_timestamps: bool = False,
    prepend_punctuations: str = "\"'“¿([{-",
    append_punctuations: str = "\"'.。,，!！?？:：”)]}、",
    clip_timestamps: Union[str, List[float]] = "0",
    hallucination_silence_threshold: Optional[float] = None,
    **decode_options,
)
```
Returns `dict(text=..., segments=[...], language=...)`. Segment dict keys: `seek, start, end, text, tokens, temperature, avg_logprob, compression_ratio, no_speech_prob` (+ `words` when word timestamps on, + `id` added at the end).

**Default-model discrepancy (verified gotcha):** README says "The default model is `mlx-community/whisper-tiny`", the CLI default *is* `mlx-community/whisper-tiny`, but the Python `transcribe()` default was changed to **`mlx-community/whisper-turbo`** in commit `8e4391c` (2025-09-03, "whisper nits").

`ModelHolder` is a module-level singleton cache keyed on `model_path`; repeated `transcribe()` calls with the same repo reuse the loaded model.

### 4.3 Audio front-end — `mlx_whisper/audio.py`

Constants (verbatim):
```python
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
CHUNK_LENGTH = 30
N_SAMPLES = CHUNK_LENGTH * SAMPLE_RATE      # 480000
N_FRAMES = N_SAMPLES // HOP_LENGTH          # 3000
N_SAMPLES_PER_TOKEN = HOP_LENGTH * 2        # initial convs have stride 2
FRAMES_PER_SECOND = SAMPLE_RATE // HOP_LENGTH   # 100 -> 10ms/frame
TOKENS_PER_SECOND = SAMPLE_RATE // N_SAMPLES_PER_TOKEN  # 50 -> 20ms/token
```
`load_audio(file, sr=SAMPLE_RATE, from_stdin=False)` shells out to ffmpeg:
```python
cmd = ["ffmpeg", "-nostdin", "-i", file]     # or ["ffmpeg", "-i", "pipe:0"] for stdin
cmd.extend(["-threads", "0", "-f", "s16le", "-ac", "1",
            "-acodec", "pcm_s16le", "-ar", str(sr), "-"])
```
Returns `mx.array(np.frombuffer(out, np.int16)).flatten().astype(mx.float32) / 32768.0`.

**Pure-MLX STFT** (no librosa/scipy at inference), notable for reuse:
```python
def stft(x, window, nperseg=256, noverlap=None, nfft=None, axis=-1, pad_mode="reflect"):
    ...
    padding = nperseg // 2
    x = _pad(x, padding, pad_mode)             # manual reflect padding via slicing + [::-1]
    strides = [noverlap, 1]
    t = (x.size - nperseg + noverlap) // noverlap
    x = mx.as_strided(x, shape=[t, nfft], strides=strides)
    return mx.fft.rfft(x * window)
```
`hanning(size)` = `mx.array(np.hanning(size + 1)[:-1])`, `@lru_cache`.
`mel_filters(n_mels)` loads `assets/mel_filters.npz` with keys `mel_80` / `mel_128`; `assert n_mels in {80, 128}`.
`log_mel_spectrogram(audio, n_mels=80, padding=0)` → `log10`, clamp to `max-8`, `(x+4)/4`.

Assets shipped in the package: `gpt2.tiktoken`, `multilingual.tiktoken`, `mel_filters.npz`, `ls_test.flac`, `download_alice.sh`.

### 4.4 Model — `mlx_whisper/whisper.py` (266 lines)

```python
@dataclass
class ModelDimensions:
    n_mels: int; n_audio_ctx: int; n_audio_state: int; n_audio_head: int; n_audio_layer: int
    n_vocab: int; n_text_ctx: int; n_text_state: int; n_text_head: int; n_text_layer: int
```
- `MultiHeadAttention` returns `(out, (k, v), qk)` — the raw `qk` is kept because word-timestamp DTW needs cross-attention maps. Scaling is folded into q and k (`scale = (n_state // n_head) ** -0.25` applied to both) rather than using SDPA.
- `AudioEncoder`: `nn.Conv1d(n_mels, n_state, 3, padding=1)` → `nn.Conv1d(n_state, n_state, 3, stride=2, padding=1)`, `sinusoids()` positional embedding stored as `self._positional_embedding` (leading underscore ⇒ **not** a trainable parameter/saved weight).
- `TextDecoder`: `self._mask = nn.MultiHeadAttention.create_additive_causal_mask(n_ctx).astype(dtype)`; output via **weight tying**: `self.token_embedding.as_linear(x)`.
- `Whisper.is_multilingual` ⇔ `n_vocab >= 51865`; `num_languages = n_vocab - 51765 - int(is_multilingual)`.
- `set_alignment_heads(dump)` accepts a `np.ndarray` or base85+gzip `bytes`.
- Methods attached at class level: `detect_language = detect_language_function`, `decode = decode_function`.

### 4.5 Decoding — `mlx_whisper/decoding.py` (741 lines)

```python
@dataclass(frozen=True)
class DecodingOptions:
    task: str = "transcribe"
    language: Optional[str] = None
    temperature: float = 0.0
    sample_len: Optional[int] = None
    best_of: Optional[int] = None
    beam_size: Optional[int] = None
    patience: Optional[float] = None
    length_penalty: Optional[float] = None
    prompt: Optional[Union[str, List[int]]] = None
    prefix: Optional[Union[str, List[int]]] = None
    suppress_tokens: Optional[Union[str, Iterable[int]]] = "-1"
    suppress_blank: bool = True
    without_timestamps: bool = False
    max_initial_timestamp: Optional[float] = 1.0
    fp16: bool = True

@dataclass(frozen=True)
class DecodingResult:
    audio_features: mx.array
    language: str
    language_probs: Optional[Dict[str, float]] = None
    tokens: List[int] = field(default_factory=list)
    text: str = ""
    avg_logprob: float = np.nan
    no_speech_prob: float = np.nan
    temperature: float = np.nan
    compression_ratio: float = np.nan
```
Classes: `Inference`, `SequenceRanker`/`MaximumLikelihoodRanker`, `TokenDecoder`/`GreedyDecoder`, `LogitFilter` subclasses `SuppressBlank`, `SuppressTokens`, `ApplyTimestampRules`, and the driver `DecodingTask`. `categorical(logits, temp)` is `@mx.compile`d. The main loop uses `mx.async_eval(completed, tokens, sum_logprobs, no_speech_probs)`.

`detect_language(model, mel, tokenizer=None)` → `(language_tokens, language_probs)`; masks all non-language tokens with `-inf` and runs a **single** `<|startoftranscript|>` token forward pass ("performed outside the main decode loop in order to not interfere with kv-caching").

### 4.6 Fallback / segmentation logic in `transcribe()` (transferable ASR recipe)

- `decode_with_fallback(segment)` loops over the temperature tuple; retries when `compression_ratio > compression_ratio_threshold` (too repetitive) **or** `avg_logprob < logprob_threshold`; but sets `needs_fallback = False` when `no_speech_prob > no_speech_threshold` (silence). At `t > 0` it drops `beam_size`/`patience`; at `t == 0` it drops `best_of`.
- `input_stride = N_FRAMES // model.dims.n_audio_ctx  # 2`; `time_precision = input_stride * HOP_LENGTH / SAMPLE_RATE  # 0.02 s`.
- Segments are cut at **consecutive timestamp tokens**; `single_timestamp_ending` handling decides whether to seek by `segment_size` or to the last timestamp.
- Hallucination suppression: `word_anomaly_score(word)` adds 1.0 if `probability < 0.15`, `(0.133 - duration) * 15` if too short, `duration - 2.0` if longer than 2 s; `is_segment_anomaly` looks at the first 8 non-punctuation words and triggers at `score >= 3 or score + 0.01 >= len(words)`.
- `if not condition_on_previous_text or result.temperature > 0.5: prompt_reset_since = len(all_tokens)`.

### 4.7 Conversion — `whisper/convert.py`

CLI: `--torch-name-or-path` (default `tiny`), `--mlx-path` (default `mlx_models`), `--dtype` (default `float16`, `_VALID_DTYPES = {"float16","float32"}`), `-q/--quantize`, `--q-group-size` (64), `--q-bits` (4), `--upload-name`.

`_MODELS` contains download URLs for: `tiny.en, tiny, base.en, base, small.en, small, medium.en, medium, large-v1, large-v2, large-v3, large, large-v3-turbo, turbo` (`large` aliases large-v3; `turbo` aliases large-v3-turbo). `_ALIGNMENT_HEADS` holds base85-encoded boolean masks per model.

Output files (**changed in `e52c128`, 2025-12-15**):
```python
mx.save_safetensors(str(mlx_path / "model.safetensors"), weights)
config["model_type"] = "whisper"; json.dump(config, ...)   # config.json
```
`load_models.load_model` fallback order (same commit):
```python
wf = model_path / "model.safetensors"
if not wf.exists(): wf = model_path / "weights.safetensors"
if not wf.exists(): wf = model_path / "weights.npz"
```
Quantized models: `config["quantization"] = {"group_size":…, "bits":…}` and reload uses
```python
class_predicate = lambda p, m: isinstance(m, (nn.Linear, nn.Embedding)) and f"{p}.scales" in weights
nn.quantize(model, **quantization, class_predicate=class_predicate)
```

**Doc drift:** `whisper/README.md` still says "the conversion script will make the directory `mlx_models` and save the converted **`weights.npz`** and `config.json` there" — it now writes `model.safetensors`.

Conversion commands (README):
```bash
python convert.py --torch-name-or-path tiny --mlx-path mlx_models/tiny
model="tiny"
python convert.py --torch-name-or-path ${model} --mlx-path mlx_models/${model}_fp16
python convert.py --torch-name-or-path ${model} --dtype float32 --mlx-path mlx_models/${model}_fp32
python convert.py --torch-name-or-path ${model} -q --q_bits 4 --mlx-path mlx_models/${model}_quantized_4bits
```
(README shows `--q_bits`; the parser actually declares `--q-bits`; argparse accepts prefix-normalized `--q-bits` only — **README flag name is wrong**, though argparse's `allow_abbrev` will not fix an underscore. Treat `--q-bits` as correct.)

"Each time it is run, `convert.py` will **overwrite** any model in the provided path."

### 4.8 Tests + benchmark

`whisper/test.py` (464 lines, `unittest`) — requires `torch` and the OpenAI checkpoint; builds fp32/fp16/4-bit local models under `mlx_models/tiny_*`. Notable assertions:
- `test_torch_mlx`: `np.allclose(torch_logits, mlx_logits, atol=1e-2, rtol=1e-2)`
- `test_decode_lang`: `result.language == "en"`, `len(result.language_probs) == 99`
- `test_transcribe_alice`: `len(result["text"]) == 10920`, `len(result["segments"]) == 77`
- `test_transcribe_word_level_timestamps_confidence_scores` — golden word dicts with `word/start/end/probability`.
`whisper/mlx_whisper/assets/download_alice.sh` fetches the long-form test audio.

`whisper/benchmark.py`: flags `--all` and `-m/--models` (comma-separated). Times three things — `model_forward`, `decode`, `everything` (full `transcribe`) — with 5 warmups + 10 timed iterations, on `mlx_whisper/assets/ls_test.flac`.

### 4.9 Recent whisper bug fixes (read via `git show`)

- `cfc5d25` (2025-08-29, v0.4.2) "fix temperature based sampling": `logprobs = logits - mx.logsumexp(logits, axis=-1)` → **`keepdims=True`** in two places (`GreedyDecoder`, `ApplyTimestampRules`), and `tokens.reshape(tokens, (...))` → `tokens.reshape((...))`. If you copy older MLX code that computes logprobs this way, add `keepdims=True`.
- `bded1a8` "fix looping in whisper", `1cbf5cd` "use more standard window strategy" — older window/loop fixes.
- `21a4d4c` (2025-10-07) — help text mentions `--word-timestamps`.

---

## 5. `llava/` — vision-language model

`requirements.txt`: `mlx>=0.8.0`, `numpy`, `transformers`, `torch`, `huggingface_hub`, `Pillow`.

CLI (`generate.py:15-52`): `--model` (default `llava-hf/llava-1.5-7b-hf`), `--image` (URL or path; default the COCO cats image), `--prompt` (default `"USER: <image>\nWhat are these?\nASSISTANT:"`), `--max-tokens 100`, `--temp 0.3`, `--eos-token`.

```bash
python generate.py \
  --model llava-hf/llava-1.5-7b-hf \
  --image "http://images.cocodataset.org/val2017/000000039769.jpg" \
  --prompt "USER: <image>\nWhat are these?\nASSISTANT:" \
  --max-tokens 128 \
  --temp 0
```
Expected output: `These are two cats lying on a pink couch.`

Python API (README + `generate.py`):
```python
from generate import load_model, prepare_inputs, generate_text

processor, model = load_model("llava-hf/llava-1.5-7b-hf")
input_ids, pixel_values = prepare_inputs(processor, image, prompt)
reply = generate_text(input_ids, pixel_values, model, processor, max_tokens, temperature)
```
**Bug/footgun:** `prepare_inputs` actually **returns `(pixel_values, input_ids)`** (`generate.py:85`), i.e. the opposite order of the README snippet's `input_ids, pixel_values = prepare_inputs(...)`. `main()` does it correctly:
```python
pixel_values, input_ids = prepare_inputs(processor, args.image, prompt)
```

Prompt escapes: `prompt = codecs.decode(args.prompt, "unicode_escape")` so the shell-quoted `\n` becomes a real newline.

`llava.py`:
```python
@dataclass
class LlaVAConfig:
    text_config: TextConfig
    vision_config: VisionConfig
    ignore_index: int = -100
    image_token_index: int = 32000
    vision_feature_select_strategy: str = "default"   # or "full"
    vision_feature_layer: int = -2
    vocab_size: int = 32000
```
Fusion pipeline (`get_input_embeddings`): text embeds from `language_model.model.embed_tokens`; vision tower called with **`pixel_values.transpose(0, 2, 3, 1)`** (NCHW→NHWC) and `output_hidden_states=True`; take `hidden_states[vision_feature_layer]`; `"default"` strategy drops the CLS token (`[:, 1:]`); project through `LlavaMultiModalProjector` (`Linear → GELU → Linear`); then scatter into the text embeddings at `<image>` positions:
```python
image_positions = mx.array(np.where(input_ids[0] == image_token_index)[0], mx.uint32)
if len(image_positions) != num_image_patches: raise ValueError(...)
inputs_embeds[0, image_positions] = image_features
```
**Batch-size-1 only** (comment: "assuming batch size is 1").

`LlavaModel.from_pretrained` downloads with `allow_patterns=["*.json","*.safetensors","*.py","tokenizer.model","*.tiktoken"]`, then `VisionModel.sanitize(weights)` and `LanguageModel.sanitize(weights)`.

`vision.py`: `VisionConfig(model_type, num_hidden_layers=24, hidden_size=1024, intermediate_size=4096, num_attention_heads=16, image_size=336, patch_size=14, projection_dim=768, vocab_size=32000, num_channels=3, layer_norm_eps=1e-5)`; enforces `model_type == "clip_vision_model"`; `nn.GELU(approx="fast")`; note the intentionally misspelled attribute `self.pre_layrnorm` (matches HF checkpoint key).

`language.py`: `TextConfig(model_type, hidden_size=4096, num_hidden_layers=32, intermediate_size=11008, num_attention_heads=32, rms_norm_eps=1e-6, vocab_size=32000, num_key_value_heads=None, rope_theta=10000, rope_traditional=False, rope_scaling=None)`; `rope_scaling` must contain `{"factor","type"}` and `type` must be `"linear"`.

`test.py` cross-checks against `transformers.LlavaForConditionalGeneration` (`mx.allclose(..., atol=1e-2)` on projected image features).

---

## 6. `lora/` — standalone LoRA / QLoRA fine-tuning

> README TIP: "For a more fully featured LLM package, checkout [MLX LM]".

`requirements.txt`: `mlx>=0.8.0`, `transformers`, `numpy`.

### 6.1 `LoRALinear` (`lora/models.py:49-…`)

```python
class LoRALinear(nn.Module):
    @staticmethod
    def from_linear(linear: nn.Linear, rank: int = 8):
        output_dims, input_dims = linear.weight.shape
        if isinstance(linear, nn.QuantizedLinear):
            input_dims *= 32 // linear.bits          # unpack packed dim
        lora_lin = LoRALinear(input_dims, output_dims, rank)
        lora_lin.linear = linear
        return lora_lin

    def to_linear(self):
        ...
        if is_quantized:
            dtype = mx.float16
            weight = mx.dequantize(weight, linear.scales, linear.biases,
                                   linear.group_size, linear.bits)
        fused_linear.weight = weight + lora_b @ lora_a
        ...
        if is_quantized:
            fused_linear = nn.QuantizedLinear.from_linear(fused_linear,
                                                          linear.group_size, linear.bits)
        return fused_linear

    def __init__(self, input_dims, output_dims, lora_rank=8, bias=False, scale=20.0): ...
```
**`scale=20.0` default** (contrast with flux's 1.0). `input_dims *= 32 // linear.bits` is the key trick for attaching LoRA to a `QuantizedLinear`.

### 6.2 Which layers get LoRA (`lora.py:342-348`, `fuse.py:62-67`)
```python
model.freeze()
for l in model.model.layers[len(model.model.layers) - args.lora_layers :]:
    l.self_attn.q_proj = LoRALinear.from_linear(l.self_attn.q_proj)
    l.self_attn.v_proj = LoRALinear.from_linear(l.self_attn.v_proj)
    if hasattr(l, "block_sparse_moe"):
        l.block_sparse_moe.gate = LoRALinear.from_linear(l.block_sparse_moe.gate)
```
Only **q_proj and v_proj** of the last N layers (+ the MoE gate). `fuse.py` re-derives N from the adapter file: `lora_layers = len([m for m in adapters if "q_proj.lora_a" in m[0]])`.

### 6.3 `lora.py` CLI (complete)

`--model mlx_model`, `--max-tokens/-m 100`, `--temp 0.8`, `--prompt/-p None`, `--train`, `--add-eos-token 1`, `--data data/`, `--lora-layers 16`, `--batch-size 4`, `--iters 1000`, `--val-batches 25`, `--learning-rate 1e-5`, `--steps-per-report 10`, `--steps-per-eval 200`, `--resume-adapter-file None`, `--adapter-file adapters.npz`, `--save-every 100`, `--test`, `--test-batches 500`, `--seed 0`.

Line 20 (added by `1bc3476 "chore(lora): Add real-time log buffering fix for nohup execution"`):
```python
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", buffering=1)
```

Loss with padding mask:
```python
def loss(model, inputs, targets, lengths):
    logits, _ = model(inputs)
    logits = logits.astype(mx.float32)
    length_mask = mx.arange(inputs.shape[1])[None, :] < lengths[:, None]
    ce = nn.losses.cross_entropy(logits, targets) * length_mask
    ntoks = length_mask.sum()
    return ce.sum() / ntoks, ntoks
```
Batching warns above 2048 tokens: `"[WARNING] Some sequences are longer than 2048 tokens. Consider pre-splitting your data to save memory."`

Adapters saved as `.npz`: `mx.savez(args.adapter_file, **dict(tree_flatten(model.trainable_parameters())))`; loaded with `model.load_weights(args.adapter_file, strict=False)`.

### 6.4 Data format & commands

`data/{train,valid,test}.jsonl`, one JSON object per line with a **`text`** key:
```json
{"text": "table: 1-1000181-1\ncolumns: State/territory, ...\nQ: ...\nA: SELECT Notes FROM 1-1000181-1 WHERE Current slogan = 'SOUTH AUSTRALIA'"}
```
"Note other keys will be ignored by the loader."
`data/wikisql.py` downloads `https://raw.githubusercontent.com/salesforce/WikiSQL/master/data.tar.bz2` into `/tmp/wikisql`.

```bash
python convert.py --hf-path mistralai/Mistral-7B-v0.1 -q     # -> mlx_model (4-bit QLoRA base)
python lora.py --model <path_to_model> --train --iters 600
python lora.py --model <path_to_model> --adapter-file <path_to_adapters.npz> --test
python lora.py --model <path_to_model> --adapter-file <path_to_adapters.npz> \
               --max-tokens 50 --prompt "table: 1-10015132-16
columns: Player, No., Nationality, Position, Years in Toronto, School/Club Team
Q: What is terrence ross' nationality
A: "
python fuse.py
python fuse.py --upload-name My-4-bit-model --hf-path mistralai/Mistral-7B-v0.1
# low memory (32 GB M1 Max ≈ 250 tok/s)
python lora.py --model mistralai/Mistral-7B-v0.1 --train --batch-size 1 --lora-layers 4
```
Note commit `7ca05d2` fixed the README: `convert.py` takes **`--hf-path`**, not `--hf-repo`.

Reported results (README): Llama 7B WikiSQL initial val loss 2.66 → 1.23 after 1000 iters; ~475 tokens/sec on an **M2 Ultra**.

Memory tips (README, verbatim list): QLoRA via `-q` convert; smaller `--batch-size` (default 4); fewer `--lora-layers` (default 16 → 8 or 4); shorter examples.

### 6.5 `fuse.py`
Flags: `--model mlx_model`, `--save-path lora_fused_model`, `--adapter-file adapters.npz` ("npz or safetensors"), `--hf-path`, `--upload-name`, `-d/--de-quantize`.
De-quantize path manually rebuilds `nn.Linear` from every `nn.QuantizedLinear` via `mx.dequantize(...).astype(mx.float16)` and pops `config["quantization"]`.

### 6.6 `lora/utils.py` — reusable save/load helpers
- `fetch_from_hub(hf_path)` → `(weights, config_dict, tokenizer)` using `snapshot_download(allow_patterns=["*.json","*.safetensors","tokenizer.model"])`.
- `make_shards(weights, max_file_size_gibibyte=15)`; `save_model` writes `model-{:05d}-of-{:05d}.safetensors` (or `model.safetensors`), `metadata={"format": "mlx"}`, plus a sorted `model.safetensors.index.json` with `{"metadata": {"total_size":…}, "weight_map": {...}}`.
- `load(path_or_hf_repo, tokenizer_config={})` → `(model, tokenizer, config)`; quantized reload uses the same `f"{p}.scales" in weights` class predicate.
- `generate(prompt, model, temp=0.0)` generator, `sample = argmax if temp == 0 else mx.random.categorical(logits * (1/temp))`.
- `upload_to_hub(path, name, hf_path)` → pushes to `mlx-community/{name}` with a generated ModelCard (**the generated card's instructions are stale**: it references `mlx-examples/llms/hf_llm`, a directory that no longer exists).

---

## 7. `encodec/` + `musicgen/` — audio codec & music generation

### 7.1 EnCodec

`encodec/requirements.txt`: `mlx>=0.18`, `numpy`, `huggingface_hub`. Optional: `ffmpeg` (loading) and `scipy` (saving).

Complete usage (`encodec/example.py`, mirrored in README):
```python
import mlx.core as mx
from encodec import EncodecModel
from utils import load_audio, save_audio

model, processor = EncodecModel.from_pretrained("mlx-community/encodec-48khz-float32")
audio = load_audio("path/to/audio", model.sampling_rate, model.channels)
feats, mask = processor(audio)

@mx.compile
def encode(feats, mask):
    return model.encode(feats, mask, bandwidth=3)

@mx.compile
def decode(codes, scales, mask):
    return model.decode(codes, scales, mask)

codes, scales = encode(feats, mask)
reconstructed = decode(codes, scales, mask)
reconstructed = reconstructed[0, : len(audio)]     # trim padding
save_audio("reconstructed.wav", reconstructed, model.sampling_rate)
```

`EncodecModel.from_pretrained(path_or_repo)` returns **`(model, processor)`** where `processor` is `functools.partial(preprocess_audio, sampling_rate=…, chunk_length=model.chunk_length, chunk_stride=model.chunk_stride)`. Weights: `model.safetensors` + `config.json`, `snapshot_download(allow_patterns=["*.json","*.safetensors","*.model"])`.

```python
def preprocess_audio(raw_audio: Union[mx.array, List[mx.array]],
                     sampling_rate: int = 24000,
                     chunk_length: Optional[int] = None,
                     chunk_stride: Optional[int] = None) -> (mx.array, mx.array)
```
Returns `(inputs, masks)` stacked; pads to `max_length + chunk_length - (max_length % chunk_stride)`.

`model.encode(input_values, padding_mask=None, bandwidth=None)`: bandwidth must be one of `config.target_bandwidths`; "bandwidth is represented as a thousandth of what it is, e.g. 6kbps bandwidth is represented as bandwidth == 6.0". Channels must be 1 or 2. Properties: `channels`, `sampling_rate`, `chunk_length` (`int(chunk_length_s * sampling_rate)`), `chunk_stride` (`max(1, int((1.0 - overlap) * chunk_length))`).

Internal classes worth citing: `lstm_custom`, `LSTM`, `EncodecConv1d` (with `_get_extra_padding_for_conv1d` / `_pad1d`), `EncodecConvTranspose1d`, `EncodecResnetBlock`, `EncodecEncoder`/`EncodecDecoder`, `EncodecEuclideanCodebook`, `EncodecVectorQuantization`, `EncodecResidualVectorQuantizer` (`get_num_quantizers_for_bandwidth`), plus the static `_linear_overlap_add(frames, stride)`.

`utils.load_audio(file, sampling_rate, channels)` → ffmpeg subprocess → `mx.array(...).reshape(-1, channels).astype(mx.float32) / 32767.0`. `save_audio` uses `scipy.io.wavfile.write` after `(audio * 32767).astype(mx.int16)`.

Pre-converted HF models: the `mlx-community/encodec-*` collection (24 kHz, 32 kHz, 48 kHz in several dtypes).

`encodec/test.py` compares against `transformers.EncodecModel` for `facebook/encodec_48khz`: **exact equality on codes** (`np.array_equal(pt_codes, mx_codes)`) and `np.allclose(atol=1e-3, rtol=1e-4)` for scales. Note the axis convention: MLX is channels-last so PT tensors need `.moveaxis(2, 1)`.

`encodec/benchmarks/bench_mx.py` and `bench_pt.py` for MLX vs. PyTorch-MPS comparison. `convert.py -h` for conversion options (uses `snapshot_download(allow_patterns=["*.json","*.safetensors"])` and can `upload_to_hub`).

### 7.2 MusicGen

`requirements.txt`: `mlx>=0.18`, `numpy`, `huggingface_hub`, `torch`, `transformers`, `scipy`.

```python
from musicgen import MusicGen
from utils import save_audio

model = MusicGen.from_pretrained("facebook/musicgen-medium")
audio = model.generate("happy rock")
save_audio("out.wav", audio, model.sampling_rate)
```
CLI (`generate.py`): `--model facebook/musicgen-medium`, `--text "happy rock"`, `--output-path 0.wav`, `--max-steps 500`.
```bash
python generate.py --model facebook/musicgen-medium --text "happy rock" --output-path 0.wav --max-steps 500
```

```python
def generate(self, text: str, max_steps: int = 200, top_k: int = 250,
             temp: float = 1.0, guidance_coef: float = 3.0) -> mx.array
```
Implementation highlights:
- Conditional + unconditional in **one batch**: `text_tokens = mx.concatenate([text_tokens, mx.zeros_like(text_tokens)], axis=0)`, then `noise = uncond + (cond - uncond) * guidance_coef`.
- The MusicGen **"delay" codebook pattern** implemented inline:
```python
audio_tokens[..., offset + 1 :] = self.bos_token_id
audio_tokens[..., : -max_steps + offset] = self.bos_token_id
audio_seq[:, offset + 1 : offset + 2] = audio_tokens
mx.eval(audio_seq)
# ... after the loop, undo the delay:
for i in range(self.num_codebooks):
    audio_seq[:, : -self.num_codebooks, i] = audio_seq[:, i : -self.num_codebooks + i, i]
audio_seq = audio_seq[:, 1 : -self.num_codebooks + 1]
```
- Hand-rolled `KVCache(head_dim, n_kv_heads)` with `self.step = 256` growth chunking and `update_and_fetch(keys, values)`.
- `top_k_sampling(logits, top_k, temperature, axis=-1)` is `@partial(mx.compile, inputs=mx.random.state, outputs=mx.random.state)` — **compiling a stochastic function requires threading `mx.random.state` through `inputs`/`outputs`**.
- `from_pretrained` loads `state_dict.bin` via `torch.load(..., weights_only=True)["best_state"]`, `allow_patterns=["*.json", "state_dict.bin"]`; `sanitize` strips `transformer.`, renames `cross_attention`→`cross_attn`, `condition_provider.conditioners.description`→`text_conditioner`, and splits `in_proj_weight` into `q/k/v_proj.weight` thirds.
- The audio decoder is auto-derived: `encodec_name = config.audio_encoder._name_or_path.split("/")[-1].replace("_","-")` → `EncodecModel.from_pretrained(f"mlx-community/{encodec_name}-float32")`.

**MAJOR GOTCHA — cross-directory imports.** `musicgen/musicgen.py:13-14`:
```python
from encodec import EncodecModel
from t5 import T5
```
There is **no `encodec.py` or `t5.py` inside `musicgen/`** (verified: the dir contains only `generate.py`, `musicgen.py`, `utils.py`, `README.md`, `requirements.txt`, `benchmarks/`). These resolve to the sibling `../encodec/encodec.py` and `../t5/t5.py`, so you must run it with something like
`PYTHONPATH="$PWD/../encodec:$PWD/../t5" python generate.py …`
(or copy the files). The README does not mention this.

`musicgen/benchmarks/bench_mx.py` inserts `Path(__file__).parents[1]` onto `sys.path` and times 100 steps; `bench_pt.py` is the PyTorch-MPS equivalent using `MusicgenForConditionalGeneration`.

---

## 8. `video/wan2.1/` — Wan2.1 text/image → video (newest example, 2026-04)

Files carry `# Copyright © 2026 Apple Inc.`

`requirements.txt` (with inline justifications — very informative about MLX version gates):
```
einops>=0.8.2  # for mlx compatible einops
huggingface_hub
mlx>=0.31.0  # for conv3d memory and speed fix
numpy
Pillow
tokenizers
torch  # for loading of huggingface weights
tqdm
```
**`mlx>=0.31.0` required** ("for conv3d memory and speed fix"). Saving videos requires `ffmpeg` on PATH.

### 8.1 Model table (README, measured on M4 Max, 81 frames)

| Model | Task | HF Repo | RAM (unquantized) | s/it (single DiT step) |
|---|---|---|---|---|
| 1.3B | T2V | `Wan-AI/Wan2.1-T2V-1.3B` | ~10 GB | ~90 s |
| 14B | T2V | `Wan-AI/Wan2.1-T2V-14B` | ~36 GB | ~230 s |
| 14B | I2V | `Wan-AI/Wan2.1-I2V-14B-480P` | ~39 GB | ~250 s |

`wan/utils.py` `configs`:
```python
"t2v-1.3B": ModelSpec(repo_id="Wan-AI/Wan2.1-T2V-1.3B",
    repo_dit="diffusion_pytorch_model.safetensors",
    repo_vae="Wan2.1_VAE.pth",
    repo_t5="models_t5_umt5-xxl-enc-bf16.pth",
    dit_params={"dim":1536,"ffn_dim":8960,"num_heads":12,"num_layers":30},
    ckpt_path=os.getenv("WAN_T2V_1_3B"))
"t2v-14B": ... dit_params={"dim":5120,"ffn_dim":13824,"num_heads":40,"num_layers":40},
    repo_dit="diffusion_pytorch_model.safetensors.index.json", ckpt_path=os.getenv("WAN_T2V_14B")
"i2v-14B": ... repo_clip="models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth",
    dit_params={..., "model_type":"i2v", "in_dim":36}, ckpt_path=os.getenv("WAN_I2V_14B")
```
`ModelSpec.repo_tokenizer` default `"google/umt5-xxl/tokenizer.json"`.
**Env overrides: `WAN_T2V_1_3B`, `WAN_T2V_14B`, `WAN_I2V_14B`.**

`_load_weights(path)` handles three formats in one function: `*.index.json` (downloads any missing shard by reverse-engineering the repo id from the HF cache path `models--Org--Repo`), `*.pth` (via `torch.load(map_location="cpu", weights_only=True)` then `mx.array(v.float().numpy())`, then `del torch`), else `mx.load(path)`.

### 8.2 CLI — `txt2video.py`

| flag | default | notes |
|---|---|---|
| `prompt` | positional | |
| `--model` | `t2v-1.3B` | `{t2v-1.3B, t2v-14B}` |
| `--size` | `(832, 480)` | `WxH` |
| `--frames` | `81` | |
| `--steps` | `50` | |
| `--guidance` | `5.0` | `1.0` disables CFG (halves compute) |
| `--shift` | `5.0` | |
| `--seed` | None | |
| `--quantize` / `-q` | `0`, `const=8`, choices `{0,4,8}` | bare `-q` ⇒ 8-bit |
| `--n-prompt` | `"Text, watermarks, blurry image, JPEG artifacts"` | |
| `--teacache` | `0.0` | threshold; `0.05` recommended for 1.3B |
| `--checkpoint` | None | custom DiT `.safetensors` |
| `--sampler` | `unipc` | `{unipc, euler}` |
| `--output` | `out.mp4` | |
| `--preload-models` | store_true | |
| `--no-cache` | store_true | calls `mx.set_cache_limit(0)` |
| `--verbose` / `-v` | store_true | |

`img2video.py` is the same minus `--model {i2v-14B}` and plus `--image` (required); its defaults differ: `--steps 40`, `--shift 3.0`, teacache help says "0.26=recommended for i2v".

Euler timestep construction for distilled models (`txt2video.py:76-81`):
```python
if args.sampler == "euler":
    n = args.steps
    denoising_step_list = [1000 * i // n for i in range(n, 0, -1)]   # 4 steps -> [1000,750,500,250]
```

Commands (README, verbatim):
```shell
python txt2video.py 'A cat playing piano' --output out.mp4
python txt2video.py 'A cat playing piano' --model t2v-14B --quantize --output out_14B.mp4
python txt2video.py 'Ocean waves crashing on a rocky shore at sunset' \
    --size 832x480 --frames 81 --steps 50 --guidance 5.0 --seed 42 --output waves.mp4
python img2video.py 'Astronaut riding a horse' \
    --image ./inputs/astronaut-on-a-horse.png --quantize --output out_i2v.mp4
python txt2video.py 'A cat playing piano' --output out.mp4 --no-cache
python txt2video.py 'A cat playing piano' --teacache 0.05 --output out.mp4 --verbose

wget https://huggingface.co/lightx2v/Wan2.1-Distill-Models/resolve/main/wan2.1_t2v_14b_lightx2v_4step.safetensors
python txt2video.py 'A cat playing piano' \
    --model t2v-14B --checkpoint ./wan2.1_t2v_14b_lightx2v_4step.safetensors \
    --sampler euler --steps 4 --guidance 1.0 --quantize --output out_t2v_distilled.mp4
```
README memory note: "For 1.3B model 480p 81 frames `--no-cache` run utilizes **~10GB of RAM and ~14GB of RAM otherwise**".

### 8.3 TeaCache — full mechanism (`wan/pipeline.py`)

Per-model calibrated polynomial coefficients (from LightX2V configs), keys `coeffs`, `ret_steps`, `use_e0`:
- `t2v-1.3B`: `[-5.21862437e04, 9.23041404e03, -5.28275948e02, 1.36987616e01, -4.99875664e-02]`, `ret_steps=5`, `use_e0=True`
- `t2v-14B`: `[-5784.54975374, 5449.50911966, -1811.16591783, 256.27178429, -13.02252404]`, `ret_steps=1`, `use_e0=False`
- `i2v-14B`: `[2.57151496e05, -3.54229917e04, 1.40286849e03, -1.35890334e01, 1.32517977e-01]`, `ret_steps=5`, `use_e0=True`

`_precompute_teacache(sampler, num_steps, teacache)`:
1. Precompute `(t_emb, e0)` for every timestep via `self.flow.compute_time_embedding(t_val)` (lazy).
2. `raw_dists = mx.abs(embs[1:] - embs[:-1]).mean(axis=(1,2)) / (mx.abs(embs[:-1]).mean(axis=(1,2)) + 1e-8)`.
3. Horner-evaluate the polynomial **in float64 on the CPU stream**: `with mx.stream(mx.cpu): ...`.
4. One `mx.eval(rescaled, *all_t_emb, *all_e0)` materializes GPU embeddings + CPU distances together.
5. Simulate accumulation → boolean `skip_mask`; a step is forced to compute when `step_idx < ret_steps or step_idx >= cutoff_steps or step_idx == 0`.

Skip steps call the DiT with `block_residual=prev_residual_*` and `precomputed_time=(t_emb, e0)`; compute steps capture the new residual and `mx.eval(prev_residual_cond)` immediately ("Materialize residual now so it persists for cached (skip) steps").

Recommended thresholds (README, 1.3B): `0.05` ≈ 34 % skipped, "Almost lossless"; `0.1` ≈ 58 %, "Slightly corrupted"; `0.25` ≈ 76 %, "Visible quality loss". TeaCache is **auto-disabled** with distilled models: `logger.warning("TeaCache is not calibrated for distilled models; disabling.")`.

### 8.4 Other transferable MLX techniques in `wan/`

- `flow = mx.compile(self.flow.__call__, inputs=[self.flow.state])` — compiling a **bound method** with module state as compile input. Ordering caveat documented in-source: TeaCache precompute "Must run before `mx.compile(self.flow.__call__)` below, since `compute_time_embedding` uses `self.flow.state` and `mx.eval` here materializes those parameters."
- `mx.async_eval(x_t)` then `yield x_t` — "async_eval starts GPU work on x_t and returns immediately, so the caller's `mx.eval` blocks less (pipeline overlap)."
- `mx.clear_cache()` between phases (after `del pipeline.t5`, after `del pipeline.flow`).
- VAE keeps its own compiled entry points: `self._compiled_decode = mx.compile(self.decoder.__call__)`, `self._compiled_encode = mx.compile(self.encoder.__call__)`.
- `@partial(mx.compile, shapeless=True)` in `wan/layers.py:21`, `wan/model.py:24`, `wan/sampler.py:360`; `@mx.compile` in `wan/rope.py:31`.

`WanModel.__call__` signature (channels-last throughout):
```python
def __call__(self, x, t, context,
             block_residual: Optional[mx.array] = None,
             precomputed_time: Optional[Tuple[mx.array, mx.array]] = None,
             clip_fea: Optional[mx.array] = None,
             first_frame: Optional[mx.array] = None) -> Tuple[mx.array, mx.array]
```
Docstring: `x: [F, H, W, C_in]`, `context: [L, C_text]`, `clip_fea: [1, 257, 1280]` (I2V only), `first_frame` "Concatenated channel-wise with x before patchify (in_dim=36)". Returns `(output, block_residual)`.

Samplers: `FlowUniPCMultistepScheduler` (with `multistep_uni_p_bh_update` / `multistep_uni_c_bh_update`, `convert_model_output`, `index_for_timestep`, `set_timesteps(num_inference_steps, shift=None)`) and `FlowEulerDiscreteScheduler(num_train_timesteps=1000)` with `set_timesteps(denoising_step_list, shift=5.0)`.

`WanPipeline` fields: `vae_stride = (4, 8, 8)`, `z_dim = 16`, `dtype = mx.bfloat16`. T5 context is always padded/truncated to exactly **512** tokens of dim 4096. Empty-prompt embedding for CFG is cached in `self._null_context`.

`save_video(frames, output_path, fps=16)` pipes raw `rgb24` frames to ffmpeg:
```python
cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
       "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps), "-i", "-", ...]
```

---

## 9. `segment_anything/` — SAM

`requirements.txt`: `matplotlib`, `opencv-python`, `huggingface_hub` (**no explicit mlx pin**).

```bash
python convert.py --hf-path facebook/sam-vit-base --mlx-path sam-vit-base
python main.py --model <path/to/model> --input <image_or_folder> --output <path/to/output>
```
Sizes: `facebook/sam-vit-base`, `-large`, `-huge`.

`convert.py` transposes conv weights for MLX's NHWC:
- `.transpose(0, 2, 3, 1)` for `vision_encoder.patch_embed.projection.weight`, `vision_encoder.neck.conv1/conv2.weight`, `prompt_encoder.mask_embed.conv1/2/3.weight`
- `.transpose(1, 2, 3, 0)` for `mask_decoder.upscale_conv1/conv2.weight`
Saves `model.safetensors` + `model.safetensors.index.json`.

`main.py` flags: `--input` (req), `--output` (req), `--model` (req), `--convert-to-rle` (needs `pycocotools`), `--points-per-side`, `--points-per-batch`, `--pred-iou-thresh`, `--stability-score-thresh`, `--stability-score-offset`, `--box-nms-thresh`, `--crop-n-layers`, `--crop-nms-thresh`, `--crop-overlap-ratio`, `--crop-n-points-downscale-factor`, `--min-mask-region-area`.

Python API (from `notebooks/predictor_example.ipynb`):
```python
import sys; sys.path.append("..")
from segment_anything.sam import load
from segment_anything.predictor import SamPredictor

sam = load("../sam-vit-base")
predictor = SamPredictor(sam)
predictor.set_image(image)                     # cv2 BGR->RGB numpy array
input_point = mx.array([[500, 375]])           # (x, y)
input_label = mx.array([1])                    # 1 = foreground, 0 = background
masks, scores, logits = predictor.predict(
    point_coords=input_point[None],
    point_labels=input_label[None],
    multimask_output=True,
)
```
`segment_anything/__init__.py` exports only `SamAutomaticMaskGenerator`. Other public classes: `Sam` (with `postprocess_masks`, `preprocess`), `SamPredictor` (`set_image`, `predict`, `get_image_embedding`, `reset_image`), `SamAutomaticMaskGenerator.generate(image) -> List[Dict]`, plus helpers `box_area`, `batched_iou`, `non_max_supression` (sic — one "s") and `utils/amg.py`, `utils/transforms.py`.

---

## 10. `clip/`

`requirements.txt`: `mlx`, `mlx-data`, `numpy`, `transformers`, `torch`, `huggingface_hub`, `Pillow`.

```bash
python convert.py            # default openai/clip-vit-base-patch32 -> ./mlx_model
python clip.py               # runs the demo in __main__
python test.py
python linear_probe.py
```
`convert.py` flags: `--hf-repo openai/clip-vit-base-patch32`, `--mlx-path mlx_model`, `--dtype float32`, `-f/--force-download`.

```python
from PIL import Image
import clip

model, tokenizer, img_processor = clip.load("mlx_model")
inputs = {
    "input_ids": tokenizer(["a photo of a cat", "a photo of a dog"]),
    "pixel_values": img_processor([Image.open("assets/cat.jpeg"), Image.open("assets/dog.jpeg")]),
}
output = model(**inputs)
text_embeds = output.text_embeds
image_embeds = output.image_embeds
```
Output dataclasses (`clip/model.py`): `CLIPVisionOutput(pooler_output, last_hidden_state, hidden_states)`, `CLIPTextOutput(pooler_output, last_hidden_state)`, `CLIPModelOutput(loss, text_embeds, image_embeds, text_model_output, vision_model_output)`. Configs: `CLIPTextConfig`, `CLIPVisionConfig`, `CLIPConfig(text_config, vision_config, projection_dim)`. Local `quick_gelu(x) = x * mx.sigmoid(1.702 * x)`.
"To embed only images or only the text, pass only the `input_ids` or `pixel_values`, respectively."
Tested repos: `openai/clip-vit-base-patch32`, `openai/clip-vit-large-patch14`. `hf_preproc.py` shows the transformers-based preprocessing alternative. `test.py` has `MLX_PATH`/`HF_PATH` constants to edit for new models.

---

## 11. Small/foundational examples (exact flags)

### `mnist/` — the recommended starting point
`requirements.txt`: `mlx>=0.2`, `numpy`. Flags: `--gpu` (store_true), `--dataset {mnist,fashion_mnist}`.
**Defaults to CPU** (`if not args.gpu: mx.set_default_device(mx.cpu)`), hard-coded hyperparameters (2 layers, hidden 32, batch 256, 10 epochs, SGD lr=0.1). Uses two compiled functions:
```python
@partial(mx.compile, inputs=model.state, outputs=model.state)
def step(X, y): ...
@partial(mx.compile, inputs=model.state)          # eval fn: inputs only, no outputs
def eval_fn(X, y): return mx.mean(mx.argmax(model(X), axis=1) == y)
```

### `cifar/` — ResNet + **distributed data parallel**
`requirements.txt`: `mlx>=0.2`, `mlx-data`, `numpy`. Flags: `--arch resnet{20,32,44,56,110,1202}` (default `resnet20`), `--batch_size 256`, `--epochs 30`, `--lr 1e-3`, `--seed 0`, `--cpu`.
Distributed launch (README):
```shell
$ cat >hostfile.json
[
    {"ssh": "host-to-ssh-to", "ips": ["ip-to-bind-to"]},
    {"ssh": "host-to-ssh-to", "ips": ["ip-to-bind-to"]}
]
$ mlx.launch --verbose --hostfile hostfile.json main.py --batch 256 --epochs 5 --arch resnet20
```
(Note: README writes `--batch`, the parser declares `--batch_size`; argparse abbreviation will resolve `--batch` only if unambiguous — it is, so it works.)
Data-parallel pieces: `mlx.data` pipeline `.partition_if(group.size() > 1, group.size(), group.rank())`; gradient averaging `grads = nn.utils.average_gradients(grads)`; stats reduced with `with mx.stream(mx.cpu): mx.distributed.all_sum(...)`.
Reported: `Epoch: 29 | avg. Train loss 0.294 | avg. Train acc 0.897 | Throughput: 270.81 images/sec`, `Test acc 0.841` on an M1 MacBook Pro 16 GB.
`cifar/dataset.py` shows the full mlx-data augmentation chain: `.shuffle().partition_if(...).to_stream().image_random_h_flip("image", prob=0.5).pad("image",0,4,4,0.0).pad("image",1,4,4,0.0).image_random_crop("image",32,32).key_transform("image", normalize).batch(bs).prefetch(4,4)`.

### `speechcommands/` — Keyword Transformer
`requirements.txt`: `mlx>=0.2`, `mlx-data`. Flags: `--arch kwt{1,2,3}` (default `kwt1`), `--batch_size 256`, `--epochs 100`, `--lr 1e-3`, `--seed 0`, `--cpu`.
mlx-data audio features:
```python
from mlx.data.datasets import load_speechcommands
from mlx.data.features import mfsc
data.squeeze("audio").key_transform("audio",
    mfsc(40, 16000, frame_size_ms=30, frame_stride_ms=10, high_freq=7600, low_freq=20))
```
Reported: kwt1 → Test acc 0.882; kwt2 → 0.893 (M1 MBP 16 GB, 100 epochs).

### `transformer_lm/` — training a decoder-only LM from scratch
Only dependency: `mlx>=0.2`. Flags: `--gpu`, `--seed 42`, `--dataset {enwik8,ptb,wikitext2,wikitext103}` (default `ptb`), `--context_size 1024`, `--num_blocks 12`, `--dim 1024`, `--num_heads 16`, `--checkpoint` (**gradient checkpointing**), `--batch_size 2`, `--num_iters 100000`, `--learning_rate 3e-4`, `--weight_decay 1e-5`, `--lr_warmup 200`, `--steps_per_report 10`, `--steps_per_eval 1000`, `--eval_test`.
Uses built-ins: `nn.SinusoidalPositionalEncoding(dims)`, `nn.TransformerEncoder(num_layers, dims, num_heads, norm_first=True, checkpoint=checkpoint)`, `nn.MultiHeadAttention.create_additive_causal_mask(L)`, `optim.AdamW`. Manual LR warmup: `optimizer.learning_rate = min(1, it / args.lr_warmup) * args.learning_rate`.

### `cvae/` — conv VAE
`requirements.txt`: `mlx>=0.2`, `mlx-data`, `numpy`, `Pillow`. Flags: `--cpu`, `--seed 0`, `--batch-size 128`, `--max-filters 64`, `--epochs 50`, `--lr 1e-3`, `--latent-dims 8`, `--save-dir models/`.
Documented MLX limitation (still present): "**MLX does not have transposed 2D convolutions.** The example approximates them with a combination of nearest neighbor upsampling and regular convolutions, similar to the original U-Net." → class `UpsamplingConv2d` doing `self.conv(upsample_nearest(x))`.
Reported: 0.1493 M params, ~1800 im/s on a 32 GB M1 Max, loss 14626 → 8293 over 50 epochs.

### `normalizing_flow/` — RealNVP
`requirements.txt`: `mlx>=0.2`, `numpy`, `tqdm`, `scikit-learn`, `matplotlib`. Flags: `--n_steps 5000`, `--n_batch 64`, `--n_transforms 6`, `--d_params 2`, `--d_hidden 128`, `--n_layers 4`, `--learning_rate 3e-4`, `--noise 0.06`, `--cpu`.
```python
from flows import RealNVP
model = RealNVP(n_transforms=8, d_params=4, d_hidden=256, n_layers=4)
log_prob = model.log_prob(x=x)
x_samples = model.sample(sample_shape=(32, 4))
```
Note `self.freeze(keys=["mask_list"])` to keep the alternating boolean masks out of the parameter tree. Modules: `bijectors.AffineBijector`, `bijectors.MaskedCoupling` (`forward_and_log_det` / `inverse_and_log_det`), `distributions.Normal`.

### `gcn/` — graph conv net on Cora
`requirements.txt`: `mlx>=0.0.4`, `numpy>=1.26.2`, `scipy>=1.11.4`, `requests>=2.31.0`. Flags: `--nodes_path cora/cora.content`, `--edges_path cora/cora.cites`, `--hidden_dim 20`, `--dropout 0.5`, `--nb_layers 2`, `--nb_classes 7`, `--bias True`, `--lr 0.001`, `--weight_decay 0.0`, `--patience 20`, `--epochs 100`. Downloads Cora automatically.
`GCNLayer.__call__(x, adj)` is literally `adj @ self.linear(x)`.

### `bert/`
`requirements.txt`: `mlx>=0.0.5`, `transformers`, `numpy`.
```bash
python convert.py --bert-model bert-base-uncased --mlx-model weights/bert-base-uncased.npz
python test.py
```
```python
import mlx.core as mx
from model import Bert, load_model

model, tokenizer = load_model("bert-base-uncased", "weights/bert-base-uncased.npz")
batch = ["This is an example of BERT working on MLX."]
tokens = tokenizer(batch, return_tensors="np", padding=True)
tokens = {key: mx.array(v) for key, v in tokens.items()}
output, pooled = model(**tokens)
```
`output` is `B × T × D`; `pooled` is `B × D`. Attention-mask trick (`model.py:111-114`):
```python
attention_mask = mx.log(attention_mask)        # 1 -> 0, 0 -> -inf
attention_mask = mx.expand_dims(attention_mask, (1, 2))
```
Post-norm layer (`ln1(x + attn)`, `ln2(ff_out + add_and_norm)`), `layer_norm_eps=1e-12`.

### `t5/`
`requirements.txt`: `mlx>=0.8.0`, `numpy`, `transformers`.
```sh
python t5.py --model t5-small --prompt "translate English to German: A tasty apple"   # -> Ein leckerer Apfel
```
Flags: `--model t5-small`, `--prompt "translate English to German: That is good."`, `--encode-only`, `--max-tokens/-m 100`, `--temp 0.0`, `--dtype {float16,bfloat16,float32}` (default **bfloat16**), `--seed 0`. Sizes table in README: t5-small 60M → t5-11b 11B; FLAN via `google/flan-t5-*`.
`T5.from_pretrained(path_or_repo, dtype=mx.bfloat16) -> (T5, Tokenizer)` — loads `model.safetensors`, `allow_patterns=["*.json","*.safetensors","*.model"]`. **Gotcha:** the tokenizer is always constructed as `Tokenizer(config, "t5-base")` regardless of `path_or_repo`.
Also implements `_relative_position_bucket` + `RelativePositionBias` (T5-style relative attention bias), `DenseActivation` (gated/ungated), `OutputHead`. `hf_t5.py` is the reference implementation using `transformers`.

---

## 12. `llms/` legacy single-model examples (all still present)

All of these predate mlx-lm and write **`weights.npz` + `tokenizer.model` + `config.json`** into `mlx_model/`.

| Example | requirements | key flags |
|---|---|---|
| `llama/` | `mlx>=0.11.0, sentencepiece, torch, numpy` | `llama.py`: `--model-path mlx_model`, `--prompt`, `--few-shot <file>`, `--max-tokens/-m 100`, `--write-every 1`, `--temp 0.0`, `--seed 0`. `convert.py --torch-path <p> [-q] [--model-name tiny_llama]` |
| `mistral/` | (own reqs) | `mistral.py`: `--model-path mlx_model`, `--prompt`, `--max-tokens/-m 100`, `--temp 0.0`, `--tokens-per-eval 10`, `--seed 0` |
| `mixtral/` | (own reqs) | `mixtral.py`: `--model-path mlx_model`, `--prompt`, `--max-tokens/-m 100`, `--temp 0.0`, `--seed 0`. Needs git-lfs; "for 16-bit precision this model needs a machine with substantial RAM (**~100GB**)". Instruct prompt format `[INST] … [/INST]` |
| `gguf_llm/` | `mlx>=0.8, numpy, protobuf==3.20.2, sentencepiece, huggingface_hub` | `generate.py --repo <hf_repo> --gguf <file.gguf> --prompt … [--max-tokens/-m] [--temp] [--seed]` |
| `speculative_decoding/` | (own reqs) | `main.py`: `--num-draft 5`, `--model-name t5-small`, `--draft-model-name t5-small`, `--seed 0`, `--max-tokens/-m 100`, `--prompt`, `--delta 0.1`, `--regular-decode` |

Mistral download: `curl -O https://models.mistralcdn.com/mistral-7b-v0-1/mistral-7B-v0.1.tar && tar -xf mistral-7B-v0.1.tar`.
Mixtral download:
```bash
export MIXTRAL_MODEL=Mixtral-8x7B-Instruct-v0.1
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/mistralai/${MIXTRAL_MODEL}/
cd $MIXTRAL_MODEL/ && git lfs pull --include "consolidated.*.pt" && git lfs pull --include "tokenizer.model"
python convert.py --torch-path $MIXTRAL_MODEL/
python mixtral.py --model-path mlx_model
```

**GGUF quantization support (`gguf_llm/models.py:275-292`)** — direct read of quantized GGUF:
```python
weights, metadata = mx.load(gguf_file, return_metadata=True)
gguf_ft = metadata["general.file_type"]
if gguf_ft in (0, 1):   # ALL_F32 / MOSTLY_F16 -> no quantization
elif gguf_ft in (2, 3): # MOSTLY_Q4_0 / Q4_1   -> {"group_size": 32, "bits": 4}
elif gguf_ft == 7:      # MOSTLY_Q8_0          -> {"group_size": 32, "bits": 8}
else: print("[WARNING] Using unsupported GGUF quantization. Casting to float16.")
```
README: "MLX is able to read most quantization formats from GGUF directly. However, only a few quantizations are supported directly: `Q4_0`, `Q4_1`, and `Q8_0`. Unsupported quantizations will be cast to `float16`." Tested files listed: `mistral-7b-v0.1.Q8_0.gguf`, `.Q4_0.gguf`, `tinyllama-1.1b-chat-v1.0.Q8_0/Q4_0.gguf`, `phi-3-mini-4k-instruct.Q4_0.gguf`.

**Speculative decoding algorithm** (`speculative_decoding/decoder.py`):
```python
class SpeculativeDecoder:
    def __init__(self, model, draft_model, tokenizer, num_draft: int = 5, delta: float = 0.0)
    def generate(self, prompt, max_tokens=100)             # plain autoregressive
    def speculative_decode(self, prompt, max_tokens=100)   # draft/verify loop
```
Acceptance with lenience (`_get_num_accept`): `log_unis = mx.log(mx.maximum(unis - self.delta, 0.0))` compared against `model_probs - draft_probs`. Cache rewind on rejection:
```python
if (n := len(draft_tokens)) > num_to_accept:
    self.draft_model.truncate_cache(n - len(new_tokens))
    self.model.truncate_cache(n - len(new_tokens) + 1)
```
README guidance: `--delta` in `[0,1]`, `1` accepts all draft tokens, `0` uses the strict criterion; tune `--num-draft` to trade discarded drafts vs. large-model evaluations. Setup uses `python convert.py --model t5-11b` (main) and `--model t5-small` (draft).

---

## 13. Cross-cutting MLX idioms this repo teaches (with file references)

1. **Generator-based diffusion loops** — `generate_latents()` yields conditioning first, then one latent per step, so the caller controls `mx.eval` granularity and can `del` the text encoders after conditioning. Used identically in `stable_diffusion/__init__.py`, `flux/flux/flux.py`, `video/wan2.1/wan/pipeline.py`.
2. **Explicit peak-memory phase accounting**: `mx.get_peak_memory()/1024**3` + `mx.reset_peak_memory()` around conditioning / denoising / decoding (`flux/txt2image.py:115-141`, `video/wan2.1/txt2video.py:122-146`).
3. **Deliberate module deletion to reuse allocator memory**: `del sd.text_encoder; del sd.unet; del sd.sampler` (`stable_diffusion/txt2image.py:77-83`), `del flux.t5; del flux.clip; del flux.flow`, `del pipeline.t5; mx.clear_cache()`.
4. **`mx.compile` patterns**: `@partial(mx.compile, inputs=state, outputs=state)` with `state = [model.state, optimizer.state]` (cifar, transformer_lm, cvae, gcn, speechcommands, flux dreambooth); `inputs=model.state` only for eval fns (mnist); `shapeless=True` for shape-agnostic elementwise helpers (flux layers, wan layers/model/sampler); `inputs=mx.random.state, outputs=mx.random.state` for stochastic fns (`musicgen/musicgen.py:148`); compiling a bound method (`wan/pipeline.py:306`, `wan/vae.py:326-327`).
5. **Distributed**: `mx.distributed.init()`, `group.size()/rank()`, `mx.distributed.all_sum/all_gather`, `nn.utils.average_gradients` (aka `from mlx.nn.utils import average_gradients`), `mlx.nn.layers.distributed.shard_linear/shard_inplace`, launcher `mlx.launch --verbose --hostfile hostfile.json -- <cmd>`, and the `--env MLX_METAL_FAST_SYNCH=1` experimental flag.
6. **Quantization**: `nn.quantize(module, group_size=…, bits=…, class_predicate=…)`; reload predicate `lambda p, m: isinstance(m, (nn.Linear, nn.Embedding)) and f"{p}.scales" in weights` (whisper `load_models.py`, lora `utils.py`); shape-based predicate `hasattr(m,"to_quantized") and m.weight.shape[1] % 512 == 0` (flux).
7. **Weight sanitization** is the standard porting hook: every ported model defines `sanitize(weights)` (flux `Flux.sanitize`, wan `WanModel.sanitize`/`WanVAE.sanitize`/`_merge_qkv_weights`, musicgen `MusicGen.sanitize`, t5 `T5.sanitize`, llava `VisionModel/LanguageModel.sanitize`). Conv weights consistently need NCHW→NHWC transposes.
8. **Safetensors metadata as a config channel**: `mx.save_safetensors(..., metadata={"lora_rank": ..., "lora_blocks": ...})` and `mx.load(file, return_metadata=True)` (flux). Also `metadata={"format": "mlx"}` in `lora/utils.py`.
9. **Underscore-prefixed attributes are non-parameters**: `self._positional_embedding` (whisper), `self._mask`, `self._t5`, `self._audio_decoder`, `self._sigmas`. Combined with `self.freeze(keys=[...])` (normalizing_flow) for masks.
10. **`mx.as_strided` + `mx.fft.rfft`** to implement STFT without scipy (whisper `audio.py:106-129`).
11. `mx.stream(mx.cpu)` / `stream=mx.cpu` for tiny reductions and float64 math (cifar stats, wan TeaCache polynomial, flux `Trainer._random_crop_resize` uniform draw).

---

## 14. Gotchas / footguns (consolidated)

- **`llms/mlx_lm` no longer exists here.** Use `github.com/ml-explore/mlx-lm`. WWDC25 notebooks depend on `mlx-lm==0.24.1` from PyPI, not on this repo.
- **`musicgen/` cannot run standalone** — it imports `encodec` and `t5` from sibling directories that are not on `sys.path` by default.
- **`llava` README snippet has the return order of `prepare_inputs` backwards.**
- **`whisper` Python default model ≠ CLI default model** (`whisper-turbo` vs `whisper-tiny`), and the README says `weights.npz` while `convert.py` now writes `model.safetensors`.
- **Whisper README shows `--q_bits`; the real flag is `--q-bits`.**
- **Two different `LoRALinear` implementations with different `scale` defaults** (`flux/flux/lora.py` scale=1.0 vs `lora/models.py` scale=20.0) and different fusing behavior (flux does not re-quantize; lora does).
- **Deprecated memory API still in use**: `mx.metal.get_peak_memory()` in `stable_diffusion/txt2image.py`, `stable_diffusion/image2image.py`, `flux/dreambooth.py`; newer code uses `mx.get_peak_memory()`.
- **`mx.logsumexp` needs `keepdims=True`** when subtracting from logits (whisper fix `cfc5d25`).
- **Image size constraints**: FLUX rounds up to multiples of 16 (then /8 for latents); stable diffusion `image2image.py` forces divisibility by 64 by downsampling with `Image.NEAREST`.
- **MLX has no transposed 2-D convolution** (documented in `cvae/README.md`); workaround = nearest-neighbor upsample + conv.
- **`mlx-data` is a separate package** (`mlx-data`), required by `cifar`, `cvae`, `speechcommands`, `clip`.
- **`ffmpeg` is a hard runtime dep** for whisper (`load_audio`), encodec (`utils.load_audio`), and wan2.1 (`save_video`). `scipy` needed to *save* wavs in encodec/musicgen.
- **Wan2.1 needs `mlx>=0.31.0`** ("conv3d memory and speed fix") and `einops>=0.8.2` ("mlx compatible einops"); the 14B models need 36–39 GB RAM unquantized.
- **DeepSeek-V3 demo in the WWDC25 notebook needs a Mac Studio M3 Ultra / 512 GB.**
- **FLUX dreambooth needs ~50 GB RAM**; QLoRA "coming soon" as of this commit.
- **TeaCache is uncalibrated for distilled models** and is force-disabled with a warning.
- **`lora/utils.upload_to_hub` generates a model card pointing at `mlx-examples/llms/hf_llm`**, a path that no longer exists.
- **CI only runs `black`/`isort`.** No example is functionally tested on CI; every `test.py` needs `torch` + network + real checkpoints.
- **Notebook kernel metadata in `Get_started_...ipynb` claims Python 3.9.17** while `requirements.txt` targets 3.12 — cosmetic but confusing.
- **`whisper/mlx_whisper` `str2bool` accepts only the literal strings `True`/`False`** (`--verbose true` errors).

---

## 15. Version / dependency matrix observed in this repo

| Example | pinned/floor MLX | other notable pins |
|---|---|---|
| `wwdc25/` | **`mlx==0.25.2`** | `mlx-lm==0.24.1`, `mlx-data==0.1.0`, `torch==2.7.0`, `transformers==4.52.3`, `datasets==3.6.0`, `huggingface-hub==0.32.2` |
| `video/wan2.1/` | **`mlx>=0.31.0`** | `einops>=0.8.2`, `tokenizers`, `torch` |
| `flux/` | `mlx>=0.18.1` | `sentencepiece`, `regex` |
| `encodec/`, `musicgen/` | `mlx>=0.18` | musicgen adds `torch`, `transformers`, `scipy` |
| `whisper/` | `mlx>=0.11` | `numba`, `tiktoken`, `torch`, `scipy`, `more-itertools`; py`>=3.8`; pkg version `0.4.3` |
| `stable_diffusion/` | `mlx>=0.11` | |
| `llms/llama` | `mlx>=0.11.0` | `sentencepiece`, `torch` |
| `t5/`, `lora/`, `llava/` | `mlx>=0.8.0` | |
| `llms/gguf_llm` | `mlx>=0.8` | `protobuf==3.20.2` |
| `cifar`, `cvae`, `speechcommands`, `transformer_lm`, `normalizing_flow`, `mnist` | `mlx>=0.2` | `mlx-data` for the first three |
| `bert/` | `mlx>=0.0.5` | |
| `gcn/` | `mlx>=0.0.4` | `scipy>=1.11.4`, `numpy>=1.26.2`, `requests>=2.31.0` |
| `clip/`, `segment_anything/` | unpinned / absent | clip: `mlx`, `mlx-data`; SAM: no mlx line at all |

Swift side (wwdc25 Xcode project): macOS deployment target **15.2**, Swift 5.0, mlx-swift **0.25.4**, mlx-swift-examples **2.25.4**, swift-transformers 0.1.21, Jinja 1.1.2.

---

## 16. Source inventory (every file I actually read this session)

Root: `README.md`, `CONTRIBUTING.md`, `ACKNOWLEDGMENTS.md`, `.pre-commit-config.yaml`, `.github/workflows/pull_request.yml`; `git log --oneline -50`, `git log -12 --date=short`, `git show` for `cfc5d25`, `e52c128`, `f143957`, `8e4391c`, `--stat` for `796f5b5`, `4b2a0df`, `c243370`.

- `wwdc25/`: `README.md`, `requirements.txt`, `Get_started_with_MLX_for_Apple_silicon.ipynb` (all cells + outputs), `Explore_language_models_on_Apple_silicon_with_MLX.ipynb` (all cells), `data/{train,valid,all}.jsonl` (parsed all lines for keys/counts), `WWDC25MLXSwiftExamples/WWDC25MLXSwiftExamples/{main.swift,SimpleMLXLM.swift,SimpleMLXLMWithKVCache.swift}`, `…/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`, `…/project.pbxproj` (grepped for build settings + SPM deps).
- `flux/`: `README.md`, `requirements.txt`, `txt2image.py`, `dreambooth.py`, `generate_interactive.py`, `flux/__init__.py`, `flux/flux.py`, `flux/sampler.py`, `flux/lora.py`, `flux/datasets.py`, `flux/trainer.py`, `flux/utils.py`, `flux/model.py`, `flux/layers.py`, `flux/tokenizers.py` (partial).
- `stable_diffusion/`: `README.md`, `requirements.txt`, `txt2image.py`, `image2image.py`, `stable_diffusion/__init__.py`, `stable_diffusion/sampler.py`, `stable_diffusion/config.py`, `stable_diffusion/model_io.py` (lines 1-120).
- `whisper/`: `README.md`, `setup.py`, `mlx_whisper/_version.py`, `mlx_whisper/requirements.txt`, `mlx_whisper/__init__.py`, `mlx_whisper/cli.py`, `mlx_whisper/load_models.py`, `mlx_whisper/audio.py`, `mlx_whisper/whisper.py`, `mlx_whisper/transcribe.py` (full), `mlx_whisper/decoding.py` (lines 1-140 + class index), `mlx_whisper/writers.py` (class index), `convert.py` (models table + CLI), `benchmark.py`, `test.py` (structure + assertions).
- `llava/`: `README.md`, `requirements.txt`, `generate.py`, `llava.py`, `vision.py` (config + structure), `language.py` (config), `test.py` (head).
- `lora/`: `README.md`, `requirements.txt`, `lora.py`, `models.py` (ModelArgs + LoRALinear), `utils.py`, `fuse.py`, `data/wikisql.py`, `data/train.jsonl` (sample).
- `encodec/`: `README.md`, `requirements.txt`, `example.py`, `utils.py`, `convert.py` (head), `encodec.py` (API index + `preprocess_audio`/`from_pretrained`), `test.py` (head).
- `musicgen/`: `README.md`, `requirements.txt`, `generate.py`, `utils.py`, `musicgen.py` (full API), `benchmarks/bench_mx.py`, `benchmarks/bench_pt.py`.
- `video/wan2.1/`: `README.md`, `requirements.txt`, `txt2video.py`, `img2video.py` (flags), `wan/__init__.py`, `wan/pipeline.py` (full), `wan/utils.py` (configs, `_load_weights`, `save_video`), `wan/model.py` (`__call__` signature + index), `wan/sampler.py` (index), `wan/vae.py` (index).
- `segment_anything/`: `README.md`, `requirements.txt`, `convert.py`, `main.py` (flags), `segment_anything/__init__.py`, class index of `sam.py`/`predictor.py`/`automatic_mask_generator.py`, `notebooks/predictor_example.ipynb` (cells 0-15).
- `clip/`: `README.md`, `requirements.txt`, `clip.py`, `convert.py` (flags), `model.py` (dataclasses).
- `t5/`: `README.md`, `requirements.txt`, `t5.py` (index + `from_pretrained` + CLI), `hf_t5.py` (head).
- `bert/`: `README.md`, `requirements.txt`, `model.py`.
- `cifar/`: `README.md`, `requirements.txt`, `main.py`, `dataset.py`.
- `cvae/`: `README.md`, `requirements.txt`, `main.py` (flags), `vae.py`.
- `gcn/`: `README.md`, `requirements.txt`, `main.py` (flags), `gcn.py`.
- `mnist/`: `README.md`, `requirements.txt`, `main.py`.
- `normalizing_flow/`: `README.md`, `requirements.txt`, `main.py` (flags), `flows.py`.
- `speechcommands/`: `README.md`, `requirements.txt`, `main.py` (head).
- `transformer_lm/`: `README.md`, `requirements.txt`, `main.py`.
- `llms/`: `README.md`, `llama/README.md`+`requirements.txt`+`llama.py` (flags), `mistral/README.md`+`mistral.py`, `mixtral/README.md`+`mixtral.py` (flags), `gguf_llm/README.md`+`requirements.txt`+`generate.py` (flags)+`models.py` (GGUF load), `speculative_decoding/README.md`+`main.py` (flags)+`decoder.py`.
- Repo-wide greps: `add_argument` (AST-extracted), `mx.compile|mx.distributed|average_gradients|get_peak_memory|clear_cache|set_cache_limit|async_eval`.

---

## 17. Open questions / unverified

- **UNVERIFIED:** whether `mlx-lm 0.24.1`'s `mlx_lm.lora --mask-prompt` flag and the `prompt`/`completion` JSONL schema in `wwdc25/data/` are still current in later mlx-lm versions — that code lives in the separate `ml-explore/mlx-lm` repo, not here.
- **UNVERIFIED:** exact `mlx.core` API signatures (e.g. `mx.fast.metal_kernel`, `mx.quantize`) beyond how they are called here — I read call sites, not the MLX source.
- **UNVERIFIED:** whether `mx.metal.get_peak_memory()` is merely deprecated or removed in `mlx>=0.31`; if removed, `stable_diffusion/*.py` and `flux/dreambooth.py` would break at those lines. Worth checking against the MLX repo.
- **UNVERIFIED:** whether `musicgen` is *intended* to be run with `PYTHONPATH` pointing at the sibling dirs, or whether this is an outright bug. No comment or README note addresses it.
- **UNVERIFIED:** whether `whisper/convert.py`'s `_MODELS` URLs (openaipublic.azureedge.net) still resolve in 2026.
- **UNVERIFIED:** the `wan2.1` `--quantize 4` path — README only demonstrates the default 8-bit; quality/RAM numbers for 4-bit are not given.
- **UNVERIFIED:** whether `mlx.launch` still takes `--hostfile` in the JSON shape shown in `cifar/README.md` and `flux/README.md` for current MLX; only the example text was read.
- Not read end-to-end (only indexed): `stable_diffusion/{unet,vae,clip,tokenizer}.py`, `flux/flux/{autoencoder,clip,t5}.py`, `video/wan2.1/wan/{layers,rope,t5,clip,vae,vae_layers,tokenizers}.py`, `whisper/mlx_whisper/{timing,tokenizer,torch_whisper,writers}.py`, `segment_anything/segment_anything/*`, `clip/{model,image_processor,tokenizer,linear_probe,hf_preproc}.py`, `cifar/resnet.py`, `speechcommands/kwt.py`, `llms/*/convert.py`, `bert/convert.py`, `segment_anything/notebooks/automatic_mask_generator_example.ipynb`.
