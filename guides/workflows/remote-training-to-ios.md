# Remote GPU training to an iOS app: hosted CUDA, MLX, and Core AI

**Current as of 2026-09-16.** This is a deployment workflow, not an Agent Skill. It covers a
worked causal-language-model LoRA path; the artifact boundary and service advice also apply to
vision, audio, and embedding models, but their exporters and iOS runners differ.

## The short answer

Yes. Train or fine-tune on an online NVIDIA GPU, preserve a portable Hugging Face/PyTorch
checkpoint, and convert that checkpoint into the artifact your iOS runtime consumes.

The CUDA result is **not** the iOS artifact. CUDA is where optimization happens; MLX or Core AI is
where inference happens:

```text
dataset + base revision + training code
                    │
                    ▼
       hosted Linux/NVIDIA CUDA job
                    │
                    ▼
     merged Hugging Face checkpoint
 config + tokenizer + *.safetensors + manifest
             │                         │
             │                         │
             ▼                         ▼
      mlx_lm.convert            coreai-models export
      quantized MLX             iOS .aimodel bundle
             │                         │
             ▼                         ▼
       MLX Swift on iOS          Core AI on iOS
```

The merged Hugging Face checkpoint is the release source of truth. Do not make a CUDA optimizer
checkpoint, an MLX adapter, or a compiled `.aimodelc` directory your only surviving artifact.

If there is any chance you will ship both MLX and Core AI, train with PyTorch/Transformers. MLX
itself now has an official Linux CUDA backend and can fine-tune directly on NVIDIA hardware, but
that path is best when MLX is definitely the only destination. The conversion path from a standard
PyTorch checkpoint into both Apple stacks is better supported than a round trip from MLX weights
back into PyTorch.

## 1. Choose a service by the artifact you can take home

The first filter is not GPU type or hourly price. It is **weight export**.

A turnkey fine-tuning API that returns only a hosted endpoint is not an iOS training service. For
on-device deployment you need, at minimum:

- the merged model weights in `safetensors` form;
- `config.json` and the complete tokenizer files;
- the exact base-model revision and license;
- an evaluation report and the training arguments;
- permission, under both the data terms and model license, to redistribute the derived weights.

Use one of these service shapes:

| Service shape | Good examples | Best for | What you must own |
|---|---|---|---|
| Fire-and-forget GPU job | [Hugging Face Jobs](https://huggingface.co/docs/huggingface_hub/en/guides/jobs) | A script that already runs locally; Hub datasets and model repos | Timeout, output volume, final upload, resume policy |
| Python-defined serverless GPU | [Modal GPU functions](https://modal.com/docs/guide/gpu) | Repeatable jobs without managing a VM | Image definition, mounted Volume, retry/resume logic |
| Interactive GPU pod | [Runpod Pods](https://docs.runpod.io/pods/overview) | Exploration, notebooks, custom system packages | Shutdown discipline, persistent storage, automation |
| Managed enterprise training job | [Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html), Vertex AI, Azure ML | IAM, audit, private networking, regulated data | Container contract, object storage, quotas, infrastructure configuration |

Prices, available GPU names, quotas, and regions change frequently. Query them immediately before
a run. For example, Hugging Face exposes `hf jobs hardware`, Modal links its live pricing from the
GPU guide, and Runpod exposes current inventory in its console and CLI.

### The practical recommendation

- Start with **Hugging Face Jobs** if the dataset and output already live on the Hub.
- Start with **Modal** if you want the infrastructure definition committed beside the training
  script.
- Use a **Runpod Pod** when you need an interactive shell or an unusual container.
- Use your organization's managed cloud platform when networking, audit, or data residency matters
  more than minimizing setup.

The same training script below works in all four. Only the launch wrapper and durable path change.

## 2. Define the portable training contract first

Before renting a GPU, make one run directory mean the same thing everywhere:

```text
/outputs/<run-id>/
  checkpoints/                 # optimizer + scheduler state; resumable
  adapter/                     # LoRA adapter, before merge
  merged/                      # portable release candidate
    config.json
    generation_config.json     # when the base model supplies one
    tokenizer.json             # or the model's equivalent tokenizer files
    tokenizer_config.json
    model-*.safetensors
  run-manifest.json
  eval.json
```

Record these values in `run-manifest.json`:

- base model ID **and immutable commit SHA**;
- dataset ID, revision, split, and a post-processing fingerprint;
- exact dependency lock or container digest;
- GPU model, CUDA version, driver, precision, seed, and training arguments;
- adapter and merged-repository commit SHAs;
- the evaluation suite and its result;
- later, the MLX version or Core AI/Xcode version used to derive the shipping artifact.

Two rules prevent most expensive failures:

1. **Checkpoint to storage that outlives compute.** A path on the container's root disk is not a
   checkpoint strategy.
2. **Smoke-test the entire route before the real run.** Train 10–20 steps, merge, convert, load on a
   physical iPhone, and generate one answer. A four-hour run should not be the first time you learn
   that the architecture is unsupported by your chosen exporter.

## 3. Worked example: Qwen3 0.6B LoRA on CUDA

Qwen3 0.6B is used because it is small enough for a cheap end-to-end rehearsal and Apple publishes
both macOS and iOS Core AI recipes for the family. Replace it only after this route works.

The dataset is a Hugging Face dataset with a `train` split and conversational prompt/completion
columns:

```json
{"prompt":[{"role":"user","content":"Summarize: ..."}],"completion":[{"role":"assistant","content":"..."}]}
```

Hugging Face TRL supports this structured conversational format and computes completion-only loss
for prompt/completion datasets. Its [SFT guide](https://huggingface.co/docs/trl/sft_trainer) and
[PEFT integration](https://huggingface.co/docs/trl/peft_integration) are the upstream references.

### 3.1 The portable script

Save this as `train_sft.py`. The dependency list is intentionally visible for a first run. After
the smoke test, resolve it to exact versions or a container digest; a moving dependency set is not a
reproducible release recipe.

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "datasets",
#   "huggingface-hub",
#   "peft",
#   "safetensors",
#   "torch",
#   "transformers",
#   "trl",
# ]
# ///

import argparse
import json
import platform
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.trainer_utils import get_last_checkpoint
from trl import SFTConfig, SFTTrainer


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--adapter-repo")
    parser.add_argument("--merged-repo")
    parser.add_argument("--max-steps", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if not torch.cuda.is_available():
        raise RuntimeError("This recipe expects an NVIDIA CUDA worker")

    run_dir = Path(args.output_dir)
    checkpoint_dir = run_dir / "checkpoints"
    adapter_dir = run_dir / "adapter"
    merged_dir = run_dir / "merged"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        args.dataset_id,
        revision=args.dataset_revision,
        split="train",
    )
    required = {"prompt", "completion"}
    if not required.issubset(dataset.column_names):
        raise ValueError(f"dataset must contain {sorted(required)}")
    split = dataset.train_test_split(test_size=0.05, seed=42)

    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        revision=args.base_revision,
        trust_remote_code=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    training = SFTConfig(
        output_dir=str(checkpoint_dir),
        max_steps=args.max_steps,
        max_length=1024,
        completion_only_loss=True,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=8,
        gradient_checkpointing=True,
        learning_rate=2e-4,
        warmup_steps=10,
        bf16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=2,
        report_to="none",
        seed=42,
        model_init_kwargs={
            "revision": args.base_revision,
            "dtype": "bfloat16",
            "trust_remote_code": False,
        },
        push_to_hub=bool(args.adapter_repo),
        hub_model_id=args.adapter_repo,
        hub_private_repo=True,
        hub_strategy="checkpoint",
    )

    trainer = SFTTrainer(
        model=args.base_model,
        args=training,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        processing_class=tokenizer,
        peft_config=LoraConfig(
            task_type="CAUSAL_LM",
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            target_modules="all-linear",
        ),
    )

    resume = get_last_checkpoint(str(checkpoint_dir))
    trainer.train(resume_from_checkpoint=resume)
    metrics = trainer.evaluate()
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(adapter_dir)
    if args.adapter_repo:
        trainer.push_to_hub(commit_message="Final LoRA adapter and training metadata")

    # Produce the portable handoff. PEFT adapter checkpoints do not contain the
    # base weights, so MLX/Core AI should consume this merged directory instead.
    del trainer
    torch.cuda.empty_cache()
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        revision=args.base_revision,
        dtype=torch.bfloat16,
        trust_remote_code=False,
    )
    adapted = PeftModel.from_pretrained(base, adapter_dir)
    merged = adapted.merge_and_unload(safe_merge=True)
    merged.save_pretrained(
        merged_dir,
        safe_serialization=True,
        max_shard_size="4GB",
    )
    tokenizer.save_pretrained(merged_dir)
    if args.merged_repo:
        merged.push_to_hub(args.merged_repo, private=True, safe_serialization=True)
        tokenizer.push_to_hub(args.merged_repo, private=True)

    manifest = {
        "base_model": args.base_model,
        "base_revision": args.base_revision,
        "dataset_id": args.dataset_id,
        "dataset_revision": args.dataset_revision,
        "dataset_fingerprint": dataset._fingerprint,
        "seed": 42,
        "max_steps": args.max_steps,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "eval": metrics,
    }
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
```

The [PEFT checkpoint documentation](https://huggingface.co/docs/peft/main/developer_guides/checkpoint)
is explicit that an adapter checkpoint contains only adapter parameters. `merge_and_unload()` is
the step that creates an ordinary model again. Preserve **both** artifacts: the adapter for future
training and the merged model for conversion.

If the selected GPU does not support BF16, change both `bf16=True` and the two BF16 dtypes to FP16.
Do not silently let the model load in FP32: it can double memory and change the hardware size you
think the run requires.

### 3.2 Launch it on Hugging Face Jobs

Hugging Face Jobs can run a local UV script, inject encrypted secrets, select a GPU flavor, and
mount a writable Storage Bucket. The default job timeout is only 30 minutes, so set it explicitly.

Create a small local `submit_hf.py`:

```python
import os

from huggingface_hub import run_uv_job, sync_job_volume

outputs = sync_job_volume("./outputs", "/outputs", read_only=False)

job = run_uv_job(
    "train_sft.py",
    script_args=[
        "--base-model", "Qwen/Qwen3-0.6B",
        "--base-revision", "<BASE_COMMIT_SHA>",
        "--dataset-id", "<ORG>/<DATASET>",
        "--dataset-revision", "<DATASET_COMMIT_SHA>",
        "--output-dir", "/outputs/qwen3-ios-v1",
        "--adapter-repo", "<ORG>/qwen3-ios-v1-adapter",
        "--merged-repo", "<ORG>/qwen3-ios-v1-hf",
        "--max-steps", "20",  # smoke test first
    ],
    flavor="a10g-large",
    timeout="4h",
    volumes=[outputs],
    secrets={"HF_TOKEN": os.environ["HF_TOKEN"]},
)
print(job.id, job.url)
```

Then:

```bash
python submit_hf.py
hf jobs logs <JOB_ID>
hf jobs wait <JOB_ID>
```

The official Jobs guide documents writable bucket mounts for checkpoints, local-directory sync,
encrypted secrets, status, metrics, cancellation, and timeout behavior. Keep the Hub repositories
private until license, data, and evaluation review is complete.

### 3.3 Launch the same script on Modal

Modal expresses the image, GPU, secret, timeout, and durable Volume in Python. Save this beside the
training script as `modal_train.py`:

```python
import subprocess

import modal

app = modal.App("qwen3-ios-training")
checkpoints = modal.Volume.from_name("qwen3-ios-training", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "datasets",
        "huggingface-hub",
        "peft",
        "safetensors",
        "torch",
        "transformers",
        "trl",
    )
    .add_local_file("train_sft.py", "/app/train_sft.py")
)


@app.function(
    image=image,
    gpu="A10G",
    timeout=6 * 60 * 60,
    secrets=[modal.Secret.from_name("huggingface")],
    volumes={"/outputs": checkpoints},
)
def train() -> None:
    subprocess.run(
        [
            "python", "/app/train_sft.py",
            "--base-model", "Qwen/Qwen3-0.6B",
            "--base-revision", "<BASE_COMMIT_SHA>",
            "--dataset-id", "<ORG>/<DATASET>",
            "--dataset-revision", "<DATASET_COMMIT_SHA>",
            "--output-dir", "/outputs/qwen3-ios-v1",
            "--adapter-repo", "<ORG>/qwen3-ios-v1-adapter",
            "--merged-repo", "<ORG>/qwen3-ios-v1-hf",
            "--max-steps", "20",
        ],
        check=True,
    )
    checkpoints.commit()


@app.local_entrypoint()
def main() -> None:
    train.spawn().get()
```

Create a Modal Secret named `huggingface` containing `HF_TOKEN`, then run:

```bash
modal run --detach modal_train.py
```

The [Modal Volumes guide](https://modal.com/docs/guide/volumes) describes the checkpoint pattern and
commit/reload semantics. Modal also recommends checkpointing and reentrant jobs even when the
planned run is shorter than its maximum timeout; see its
[long-training example](https://modal.com/docs/examples/long-training).

### 3.4 Run it on a GPU pod

For Runpod or a comparable GPU VM:

1. Start from a pinned PyTorch CUDA image.
2. Attach persistent storage at `/workspace`.
3. Put the script and dataset access credentials in the pod through a secret mechanism.
4. Run the same command with `--output-dir /workspace/outputs/qwen3-ios-v1`.
5. Upload the merged model to the Hub or object storage before deleting the pod.
6. Stop or terminate the compute as soon as the upload and checksums complete.

Runpod distinguishes container disk, volume disk, network volume, and global volume. Its
[storage table](https://docs.runpod.io/pods/storage/types) says container disk is lost on restart,
volume disk is deleted with the Pod, and network volume survives independently. It also recommends
external long-term backup. Treat `/workspace` as a working checkpoint location, not the only copy
of a release model.

### 3.5 Map it onto SageMaker or another managed cloud

Keep the script unchanged and map its paths to the platform contract. For SageMaker:

- dataset channels arrive under `/opt/ml/input/data/<channel>`;
- resumable state belongs under `/opt/ml/checkpoints`;
- the final model belongs under `/opt/ml/model`;
- logs and metrics go to CloudWatch;
- a Spot job is safe only when the trainer can resume from the synced checkpoint directory.

SageMaker synchronizes `/opt/ml/checkpoints` with S3 and restores it when a managed Spot job
restarts. That behavior and its limits are documented in
[Checkpoints in SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/model-checkpoints.html)
and [Managed Spot Training](https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html).
Vertex AI and Azure ML have equivalent job/container/object-storage boundaries; preserve the same
logical directories and manifest instead of rewriting the trainer around a provider SDK.

## 4. Alternative: train MLX directly on hosted NVIDIA GPUs

MLX 0.32.2 documents an official Linux CUDA wheel:

```bash
pip install "mlx[cuda12]" "mlx-lm[train]"
```

The current requirements are Linux with glibc 2.35 or later, Python 3.10 or later, NVIDIA SM 7.5
or later, CUDA 12 or later, and driver 550.54.14 or later. CUDA 13 has a separate extra and higher
driver floor. Check the live [MLX installation page](https://ml-explore.github.io/mlx/build/html/install.html)
before choosing a provider image.

Then the same style of job can run:

```bash
mlx_lm.lora \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --data <ORG>/<DATASET> \
  --train \
  --mask-prompt \
  --iters 600 \
  --adapter-path /outputs/mlx-run/adapters

mlx_lm.fuse \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --adapter-path /outputs/mlx-run/adapters \
  --save-path /outputs/mlx-run/fused
```

The [MLX CUDA announcement](https://github.com/ml-explore/mlx/discussions/2422) explicitly
demonstrated `mlx_lm.lora` on CUDA, and the current
[mlx-lm LoRA guide](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) documents local
and Hub datasets, prompt masking, resume, evaluation, and fusion.

Use this route when all of the following are true:

- the model architecture works in `mlx-lm`;
- the operations used by training exist on the CUDA backend;
- MLX Swift is the only intended iOS runtime;
- you have tested the fused result on Apple silicon before the expensive run.

Do not assume a missing CUDA operation falls back automatically. The MLX CUDA announcement says an
unsupported operation fails unless code explicitly selects a CPU stream. Also avoid starting from a
quantized checkpoint if Core AI remains a possible destination; keep a full-precision PyTorch/HF
master and quantize separately for each runtime.

## 5. Convert the merged checkpoint for MLX on iOS

Run conversion on an Apple-silicon Mac so the exact artifact is exercised in the same ecosystem in
which it will ship. Download an immutable merged revision first:

```bash
hf download <ORG>/qwen3-ios-v1-hf \
  --revision <MERGED_MODEL_COMMIT_SHA> \
  --local-dir artifacts/qwen3-ios-v1-hf

python3 -m venv .venv-mlx
.venv-mlx/bin/pip install "mlx-lm==<VALIDATED_VERSION>"

.venv-mlx/bin/mlx_lm.convert \
  --model artifacts/qwen3-ios-v1-hf \
  --mlx-path artifacts/qwen3-ios-v1-mlx-4bit \
  --quantize \
  --q-bits 4 \
  --q-group-size 64

.venv-mlx/bin/mlx_lm.generate \
  --model artifacts/qwen3-ios-v1-mlx-4bit \
  --prompt "Give the fixed smoke-test answer."

hf upload <ORG>/qwen3-ios-v1-mlx-4bit \
  artifacts/qwen3-ios-v1-mlx-4bit .
```

Do not copy only the `safetensors` shards. The tokenizer, model config, chat template, special-token
configuration, and quantization metadata are part of the runtime contract.

### 5.1 Load the result with MLX Swift

For a prototype, add these packages and products to the iOS target:

```swift illustrative
dependencies: [
    .package(
        url: "https://github.com/ml-explore/mlx-swift-lm",
        .upToNextMajor(from: "3.31.3")),
    .package(
        url: "https://github.com/huggingface/swift-huggingface",
        from: "0.9.0"),
    .package(
        url: "https://github.com/huggingface/swift-transformers",
        from: "1.3.0"),
]
```

Select the `MLXLLM`, `MLXLMCommon`, `MLXHuggingFace`, `HuggingFace`, and `Tokenizers` products, then
load the exact model revision:

```swift illustrative
import Foundation
import HuggingFace
import MLXHuggingFace
import MLXLLM
import MLXLMCommon
import Tokenizers

let configuration = ModelConfiguration(
    id: "<ORG>/qwen3-ios-v1-mlx-4bit",
    revision: "<MLX_MODEL_COMMIT_SHA>"
)

let container = try await #huggingFaceLoadModelContainer(
    configuration: configuration
)

let session = ChatSession(
    container,
    generateParameters: GenerateParameters(maxTokens: 256, temperature: 0)
)

for try await delta in session.streamResponse(
    to: "Summarize the release notes in three bullets."
) {
    print(delta, terminator: "")
}
```

This macro-based downloader is the shortest proof of life. A shipping app generally needs its own
background/resumable download policy, checksum verification, cellular policy, and local
`ModelConfiguration(directory:)`. The full implementation choices are in
[Part 13: MLX in Swift](../part-13-mlx-swift/README.md), and model distribution is covered by
[Part 15](../part-15-shipping-and-operating/README.md).

## 6. Export the merged checkpoint for Core AI on iOS

Core AI is a different branch from the same master checkpoint. Do not convert the quantized MLX
artifact into Core AI. Start again from `artifacts/qwen3-ios-v1-hf`.

Use macOS 27, Xcode 27, and the separately installed Metal Toolchain. Clone Apple's recipe
repository rather than relying on a wheel when using its source-tree compression YAMLs:

```bash
xcodebuild -downloadComponent MetalToolchain
git clone https://github.com/apple/coreai-models.git
cd coreai-models
uv sync

# Seconds-to-minutes smoke export before the full graph.
uv run coreai.llm.export ../artifacts/qwen3-ios-v1-hf \
  --platform iOS \
  --experimental \
  --compute-precision float16 \
  --compression none \
  --num-layers 1 \
  --output-dir ../artifacts/coreai-smoke

# Full iOS/ANE-oriented export using Apple's Qwen3 0.6B mixed recipe.
uv run coreai.llm.export ../artifacts/qwen3-ios-v1-hf \
  --platform iOS \
  --experimental \
  --compute-precision float16 \
  --compression-config models/qwen3/qwen3_0_6b_mixed_4bit_8bit.yaml \
  --max-context-length 4096 \
  --output-dir ../artifacts/coreai-ios
```

Why `--experimental`? The fine-tuned repository has a new ID, so it is not an exact registry preset
even though its architecture remains Qwen3. The command still needs to recognize the architecture;
changing model code or tensor names during training can make export fail.

Apple's [Core AI model catalog](https://github.com/apple/coreai-models/blob/main/models/README.md)
documents the iOS flag, compression recipes, context length, dry run, and supported presets. The
[Qwen3 model card](https://github.com/apple/coreai-models/blob/main/models/qwen3/README.md) is the
reference for the Swift integration below. For a custom architecture, stop here and use
[Part 8](../part-08-coreai-pytorch-conversion/README.md) and the ANE/GPU authoring rules in
[Part 10](../part-10-coreai-hardware-authoring-debugging/README.md); changing a CLI flag cannot make
an unsupported graph deployable.

### 6.1 Put the Core AI bundle where iOS can load it

Treat the exported resource directory as an immutable release asset:

1. archive it without altering internal names;
2. publish the archive and a SHA-256 manifest;
3. download it with a background-capable transfer;
4. verify the digest before extraction;
5. extract under Application Support using a versioned directory;
6. pass that directory URL to the runner.

Do not add a raw `.aimodel` directory to Copy Bundle Resources. Xcode/iOS can interpret an
extension-suffixed directory as a nested bundle and reject the application. A portable `.aimodel`
can specialize on first use; ahead-of-time `.aimodelc` variants are an optional optimization and
must be built and tested for the exact device architecture. Part 15 covers that delivery and cache
lifecycle.

### 6.2 Load it through Foundation Models

Add Apple's package and the `CoreAILM` product:

```swift illustrative
.package(url: "https://github.com/apple/coreai-models", branch: "main")
```

The upstream package currently follows branches for some dependencies, so commit your resolved
package graph. Then:

```swift illustrative
import CoreAILanguageModels
import FoundationModels

// A downloaded and verified export resource directory in Application Support.
let modelURL: URL = installedModelDirectory

let model = try await CoreAILanguageModel(resourcesAt: modelURL)
let session = LanguageModelSession(model: model)
let response = try await session.respond(
    to: "Summarize the release notes in three bullets."
)

print(response.content)
```

This gives the custom Core AI model the same session surface used elsewhere in Foundation Models.
Load and generate on a physical supported iPhone; the simulator does not validate Neural Engine
placement, specialization cost, memory pressure, or thermal behavior.

## 7. Validation gates before the model enters the app

Use one fixed, versioned evaluation set at every boundary:

| Gate | What to compare | Fail the release when… |
|---|---|---|
| Base → adapter | task score, refusal/safety set, held-out loss | target gain is absent or safety regresses |
| Adapter → merged HF | deterministic prompt outputs or logits | merge changes behavior beyond numeric tolerance |
| HF → MLX/Core AI uncompressed | deterministic prompts, tokenizer IDs | prompt rendering or first divergence is unexplained |
| Uncompressed → quantized | task score, worst-case examples | aggregate or slice regression exceeds the declared budget |
| Mac → physical iPhone | output, peak memory, TTFT, sustained throughput, energy | the process jetsams, stalls, or misses the product budget |

Also test these integration properties:

- the chat template renders system/user/assistant roles exactly once;
- BOS/EOS and additional stop tokens match between Python and Swift;
- context truncation matches the training assumption;
- cancellation releases generation work;
- the app can recover from an interrupted model download;
- a model update does not reuse incompatible compiled or KV-cache state;
- airplane mode works after installation if offline operation is promised.

Quantization is a new model candidate, not a packaging step. A successful conversion only proves
that an artifact was written, not that it retained the fine-tune.

## 8. Security, privacy, and cost controls

### Data and credentials

- Confirm that training data may leave the device and enter the selected provider and region.
- Remove secrets, access tokens, and personal data that are not necessary for the objective.
- Inject credentials through the service's secret mechanism; never bake them into an image,
  dataset, notebook, or command history.
- Use least-privilege tokens: read for the base/dataset, write only for the intended output repos.
- Keep `trust_remote_code=False` unless you have reviewed and pinned the remote code.
- Prefer `safetensors` for the portable checkpoint and verify downloaded artifact hashes.
- Document model and dataset licenses in the output model card before distribution.

### Cost

- Run 20 steps before 2,000.
- Measure tokens/second and peak VRAM during the smoke run, then estimate total runtime.
- Include storage, idle pod time, egress, retries, and conversion machines—not just GPU seconds.
- Use preemptible/Spot compute only after resume has been tested by actually interrupting a run.
- Add a timeout and budget alert. A detached job without either is a billing incident waiting to
  happen.
- Terminate interactive pods after the checksum and upload are complete; persistent storage can
  continue billing after compute stops.

## 9. Release checklist

- [ ] The service exports full weights; it does not return only a hosted endpoint.
- [ ] Base model and dataset are pinned to immutable revisions.
- [ ] Model and data licenses permit the intended on-device distribution.
- [ ] The output path survives worker or pod deletion.
- [ ] Resume was tested after a deliberate interruption.
- [ ] The LoRA adapter and merged HF checkpoint are both preserved.
- [ ] Tokenizer, chat template, special tokens, config, and generation config accompany the weights.
- [ ] `run-manifest.json` records environment, arguments, revisions, and evaluation results.
- [ ] A short end-to-end smoke run reached a physical iPhone before the full training run.
- [ ] MLX and Core AI artifacts were derived independently from the same merged HF revision.
- [ ] Quantized candidates passed the same evaluation suite as the merged checkpoint.
- [ ] The final iOS artifact is revisioned, checksummed, downloadable, and recoverable.
- [ ] Physical-device memory, first-token latency, sustained throughput, thermals, and cancellation
      were measured.

## 10. Decision summary

| Goal | Train online with | Preserve | Build for iOS with |
|---|---|---|---|
| MLX only, supported architecture | PyTorch/CUDA **or** MLX/CUDA | full HF checkpoint if possible; otherwise fused MLX + adapter | `mlx_lm.convert` or the fused MLX directory → MLX Swift |
| Core AI only | PyTorch/CUDA | merged HF/PyTorch checkpoint | `coreai-models` preset/experimental exporter or `coreai-torch` → Core AI |
| Both MLX and Core AI | **PyTorch/CUDA** | merged HF checkpoint as the master | two independent conversion branches |
| Hosted API returns no weights | not viable for this goal | nothing deployable | choose a different service or model |

The durable strategy is simple: rent CUDA, not lock-in. Make the online service replaceable, make
the merged checkpoint portable, and treat each iOS conversion as a separately evaluated release
artifact.
