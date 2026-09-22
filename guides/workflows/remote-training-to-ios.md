# Remote GPU training to an iOS app: hosted CUDA, MLX, and Core AI

**Current as of 2026-09-16.** This is a deployment workflow, not an Agent Skill. It covers a
worked causal-language-model LoRA path; the artifact boundary and service advice also apply to
vision, audio, and embedding models, but their exporters and iOS runners differ.

## Evidence and version floor

This workflow targets the package and service behavior available on 2026-09-16 and the iOS 27 /
Xcode 27 Core AI generation. Non-obvious API claims use the corpus-wide evidence states:

- ✅ **VERIFIED** — confirmed in current upstream documentation or source linked beside the claim;
- 🟡 **RECONSTRUCTED** — the route is supported, but the exact end-to-end composition is this
  guide's;
- 🔴 **GAP** — the current public interface cannot satisfy part of the desired contract.

Recheck service pricing, GPU inventory, and moving package versions immediately before a run.

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

✅ **VERIFIED** — the service capabilities in the table are linked to each provider's current
documentation. The recommendation below is 🟡 **RECONSTRUCTED** from those capabilities and this
workflow's requirement to retain portable weights.

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
    run-manifest.json
    eval.json
  merged/                      # portable release candidate
    config.json
    generation_config.json     # when the base model supplies one
    tokenizer.json             # or the model's equivalent tokenizer files
    tokenizer_config.json
    model-*.safetensors
    run-manifest.json
    eval.json
  run-manifest.json
  eval.json
  publication-receipt.json     # append-only identities for every published artifact
```

Record these values in `run-manifest.json`:

- base model ID **and immutable commit SHA**;
- dataset ID, revision, split, and a post-processing fingerprint;
- exact dependency lock or container digest;
- GPU model, CUDA version, driver, precision, seed, and training arguments;
- intended adapter and merged-repository IDs in the manifest;
- every returned Hub commit SHA and the Core AI release URL/digest in
  `publication-receipt.json`;
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
import importlib.metadata
import json
import math
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import torch
from datasets import load_dataset
from huggingface_hub import HfApi
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
    parser.add_argument(
        "--environment-id",
        required=True,
        help="Immutable container digest or SHA-256 of the dependency lock",
    )
    parser.add_argument("--adapter-repo")
    parser.add_argument("--merged-repo")
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--eval-steps", type=int, default=50)
    parser.add_argument("--precision", choices=("bf16", "fp16"), default="bf16")
    return parser.parse_args()


def json_ready(value: Any) -> Any:
    """Convert config values such as enums, paths, and sets to stable JSON."""
    if is_dataclass(value):
        return json_ready(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, set):
        return sorted((json_ready(item) for item in value), key=str)
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return json_ready(value.value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def installed_versions() -> dict[str, str]:
    names = (
        "datasets",
        "huggingface-hub",
        "peft",
        "safetensors",
        "torch",
        "transformers",
        "trl",
    )
    return {name: importlib.metadata.version(name) for name in names}


def cuda_driver_version() -> str:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=driver_version",
            "--format=csv,noheader",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().splitlines()[0]


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(json_ready(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def require_finite_metrics(label: str, records: list[dict[str, Any]]) -> None:
    for record in records:
        for name, value in record.items():
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and not math.isfinite(float(value))
            ):
                raise RuntimeError(f"{label} produced non-finite {name}={value!r}")


def publication_inputs(args: argparse.Namespace, fingerprints: dict[str, str]) -> dict:
    return {
        "base_model": {"id": args.base_model, "revision": args.base_revision},
        "dataset": {
            "id": args.dataset_id,
            "revision": args.dataset_revision,
            "fingerprints": fingerprints,
        },
    }


def load_publication_receipt(path: Path, inputs: dict) -> dict:
    if not path.exists():
        return {"schema_version": 1, "inputs": inputs, "artifacts": {}}

    receipt = json.loads(path.read_text(encoding="utf-8"))
    if "schema_version" not in receipt:
        raise ValueError(
            "legacy publication receipt is not bound to immutable model and dataset "
            "inputs; preserve the existing checkpoints and archive or rename only "
            "publication-receipt.json before resuming in this output directory. Only "
            "reconstruct a schema-v1 receipt after independently binding the old "
            "publications to the original immutable inputs"
        )

    if receipt.get("schema_version") != 1:
        raise ValueError("unsupported publication receipt schema")
    if receipt.get("inputs") != inputs:
        raise ValueError("publication receipt belongs to different model or dataset inputs")
    if not isinstance(receipt.get("artifacts"), dict):
        raise ValueError("publication receipt artifacts must be an object")
    return receipt


def record_hub_publication(
    path: Path,
    receipt: dict,
    artifact_key: str,
    repo: str,
    commit_sha: str,
) -> None:
    if not isinstance(commit_sha, str) or not commit_sha.strip():
        raise ValueError("commit_sha must be a nonblank string")
    commit_sha = commit_sha.strip()
    artifact = receipt["artifacts"].setdefault(
        artifact_key, {"kind": "hugging_face", "publications": []}
    )
    if artifact.get("kind") != "hugging_face":
        raise ValueError(f"artifact {artifact_key!r} has incompatible kind")
    publication = {"repo": repo, "commit_sha": commit_sha}
    if publication not in artifact["publications"]:
        artifact["publications"].append(publication)
    write_json(path, receipt)


def require_private_repo(api: HfApi, repo_id: str) -> None:
    api.create_repo(repo_id, private=True, exist_ok=True)
    if not api.repo_info(repo_id).private:
        raise RuntimeError(f"refusing to upload to public repository {repo_id}")


def main() -> None:
    args = arguments()
    if not torch.cuda.is_available():
        raise RuntimeError("This recipe expects an NVIDIA CUDA worker")
    driver_version = cuda_driver_version()
    package_versions = installed_versions()

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
    # Validate the datasets implementation detail before paid training begins.
    dataset_fingerprints = {
        "source": dataset._fingerprint,
        "train": split["train"]._fingerprint,
        "eval": split["test"]._fingerprint,
    }
    publication_path = run_dir / "publication-receipt.json"
    publication = load_publication_receipt(
        publication_path, publication_inputs(args, dataset_fingerprints)
    )

    use_bf16 = args.precision == "bf16"
    torch_dtype = torch.bfloat16 if use_bf16 else torch.float16
    dtype_name = "bfloat16" if use_bf16 else "float16"

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
        bf16=use_bf16,
        fp16=not use_bf16,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=2,
        report_to="none",
        logging_nan_inf_filter=False,
        seed=42,
        model_init_kwargs={
            "revision": args.base_revision,
            "dtype": dtype_name,
            "trust_remote_code": False,
        },
        push_to_hub=False,
    )
    lora = LoraConfig(
        task_type="CAUSAL_LM",
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules="all-linear",
    )

    trainer = SFTTrainer(
        model=args.base_model,
        args=training,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        processing_class=tokenizer,
        peft_config=lora,
    )

    resume = get_last_checkpoint(str(checkpoint_dir))
    train_result = trainer.train(resume_from_checkpoint=resume)
    require_finite_metrics("training log", trainer.state.log_history)
    require_finite_metrics("training summary", [train_result.metrics])
    metrics = trainer.evaluate()
    require_finite_metrics("evaluation", [metrics])
    eval_path = run_dir / "eval.json"
    write_json(eval_path, metrics)
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(adapter_dir)

    manifest = {
        "base_model": args.base_model,
        "base_revision": args.base_revision,
        "dataset_id": args.dataset_id,
        "dataset_revision": args.dataset_revision,
        "dataset_fingerprints": dataset_fingerprints,
        "command_arguments": vars(args),
        "environment_id": args.environment_id,
        "packages": package_versions,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_toolkit": torch.version.cuda,
        "cuda_driver": driver_version,
        "gpu": torch.cuda.get_device_name(0),
        "precision": dtype_name,
        "sft_config": training.to_dict(),
        "lora_config": lora.to_dict(),
        "hub_destinations": {
            "adapter": args.adapter_repo,
            "merged": args.merged_repo,
        },
        "eval": metrics,
    }
    manifest_path = run_dir / "run-manifest.json"
    write_json(manifest_path, manifest)
    shutil.copy2(manifest_path, adapter_dir / manifest_path.name)
    shutil.copy2(eval_path, adapter_dir / eval_path.name)

    api = HfApi()
    if args.adapter_repo:
        require_private_repo(api, args.adapter_repo)
        adapter_commit = api.upload_folder(
            repo_id=args.adapter_repo,
            folder_path=adapter_dir,
            commit_message="Final LoRA adapter with run manifest",
        )
        record_hub_publication(
            publication_path, publication, "adapter", args.adapter_repo, adapter_commit.oid
        )

    # Produce the portable handoff only after the independently useful adapter
    # is durable. A merge OOM or timeout cannot prevent adapter publication.
    del trainer
    torch.cuda.empty_cache()
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        revision=args.base_revision,
        dtype=torch_dtype,
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
    shutil.copy2(manifest_path, merged_dir / manifest_path.name)
    shutil.copy2(eval_path, merged_dir / eval_path.name)

    if args.merged_repo:
        require_private_repo(api, args.merged_repo)
        merged_commit = api.upload_folder(
            repo_id=args.merged_repo,
            folder_path=merged_dir,
            commit_message="Merged portable checkpoint with run manifest",
        )
        record_hub_publication(
            publication_path, publication, "merged_hf", args.merged_repo, merged_commit.oid
        )


if __name__ == "__main__":
    main()
```

The [PEFT checkpoint documentation](https://huggingface.co/docs/peft/main/developer_guides/checkpoint)
is explicit that an adapter checkpoint contains only adapter parameters. `merge_and_unload()` is
the step that creates an ordinary model again. Preserve **both** artifacts: the adapter for future
training and the merged model for conversion.

✅ **VERIFIED** — the [Hub upload API](https://huggingface.co/docs/huggingface_hub/guides/upload)
returns `CommitInfo` for each folder upload. Each published folder contains its weights,
`run-manifest.json`, and `eval.json` in one commit. The separate local
`publication-receipt.json` records each returned `CommitInfo.oid` only after upload success. It is
updated atomically and appends distinct successful publications instead of clearing an earlier SHA
on retry. A legacy two-key receipt is deliberately rejected because it does not identify the
immutable model and dataset inputs that produced its SHAs. Preserve the checkpoints and archive or
rename only `publication-receipt.json`; keep the same output directory so its checkpoints remain
resumable. Reconstruct a schema-v1 receipt only after independently binding each old publication
identity to the original immutable inputs. Starting with a fresh receipt can publish an artifact again
because the new receipt no longer records the earlier publication identity. The adapter upload precedes
the memory-heavy merge, so a merge OOM still leaves the independently useful adapter published. If you
omit the repository arguments, the durable output volume is the only artifact copy.

Qwen3 was trained in BF16. If the selected GPU does not support BF16, `--precision fp16` is a risky
fallback, not an equivalent recommendation: FP16's smaller exponent range can overflow and produce
NaN or infinite loss. Use it for the 20-step smoke run first. The script disables Transformers'
NaN/Inf log filtering and refuses to save or publish if any logged, training-summary, or evaluation
metric is non-finite. The option controls both trainer flags, both model-loading dtypes, and the
manifest value. Do not silently load in FP32; it can double memory and invalidate the sizing run.

### 3.2 Carry one receipt through conversion and release

Copy `publication-receipt.json` from the durable training output to the conversion host beside the
downloaded artifacts. Save the helper below as `publish_artifact.py`. It refuses to upload into an
existing public Hub repository, captures the returned commit SHA, and records downstream Hub and
file releases in the same append-only receipt.

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["huggingface-hub"]
# ///

import argparse
import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import HfApi


def atomic_write(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_receipt(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or not isinstance(value.get("artifacts"), dict):
        raise ValueError("expected a schema-version-1 publication receipt")
    return value


def append_publication(path: Path, key: str, kind: str, publication: dict) -> None:
    if kind == "hugging_face":
        commit_sha = publication.get("commit_sha")
        if not isinstance(commit_sha, str) or not commit_sha.strip():
            raise ValueError("commit_sha must be a nonblank string")
        publication = {**publication, "commit_sha": commit_sha.strip()}
    receipt = load_receipt(path)
    artifact = receipt["artifacts"].setdefault(key, {"kind": kind, "publications": []})
    if artifact.get("kind") != kind or not isinstance(artifact.get("publications"), list):
        raise ValueError(f"artifact {key!r} has an incompatible receipt entry")
    if publication not in artifact["publications"]:
        artifact["publications"].append(publication)
    atomic_write(path, receipt)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload_hub(args: argparse.Namespace) -> None:
    api = HfApi()
    api.create_repo(args.repo, private=True, exist_ok=True)
    if not api.repo_info(args.repo).private:
        raise RuntimeError(f"refusing to upload to public repository {args.repo}")
    commit = api.upload_folder(
        repo_id=args.repo,
        folder_path=args.folder,
        commit_message=args.message,
    )
    publication = {"repo": args.repo, "commit_sha": commit.oid}
    if args.source_commit_sha:
        publication["source_commit_sha"] = args.source_commit_sha
    append_publication(args.receipt, args.artifact, "hugging_face", publication)
    print(commit.oid)


def record_file(args: argparse.Namespace) -> None:
    append_publication(
        args.receipt,
        args.artifact,
        "release_file",
        {
            "release_url": args.release_url,
            "sha256": sha256(args.file),
            "source_commit_sha": args.source_commit_sha,
            "exporter_commit_sha": args.exporter_commit_sha,
        },
    )


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    hub = subparsers.add_parser("hub")
    hub.add_argument("--receipt", type=Path, required=True)
    hub.add_argument("--artifact", required=True)
    hub.add_argument("--repo", required=True)
    hub.add_argument("--folder", type=Path, required=True)
    hub.add_argument("--message", required=True)
    hub.add_argument("--source-commit-sha")
    hub.set_defaults(run=upload_hub)

    file = subparsers.add_parser("file")
    file.add_argument("--receipt", type=Path, required=True)
    file.add_argument("--artifact", required=True)
    file.add_argument("--file", type=Path, required=True)
    file.add_argument("--release-url", required=True)
    file.add_argument("--source-commit-sha", required=True)
    file.add_argument("--exporter-commit-sha", required=True)
    file.set_defaults(run=record_file)
    return parser.parse_args()


if __name__ == "__main__":
    parsed = arguments()
    parsed.run(parsed)
```

The receipt is a run contract. If the base or dataset revision changes, start a new output directory
and receipt rather than mixing publications from different inputs.

### 3.3 Launch it on Hugging Face Jobs

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
        "--environment-id", "<LOCK_SHA256_OR_IMAGE_DIGEST>",
        "--adapter-repo", "<ORG>/qwen3-ios-v1-adapter",
        "--merged-repo", "<ORG>/qwen3-ios-v1-hf",
        "--max-steps", "20",  # smoke test first
        "--save-steps", "10",
        "--eval-steps", "10",
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

✅ **VERIFIED** — the official Jobs guide documents writable bucket mounts for checkpoints, local-directory sync,
encrypted secrets, status, metrics, cancellation, and timeout behavior. Keep the Hub repositories
private until license, data, and evaluation review is complete.

### 3.4 Launch the same script on Modal

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
            "--environment-id", "<LOCK_SHA256_OR_IMAGE_DIGEST>",
            "--adapter-repo", "<ORG>/qwen3-ios-v1-adapter",
            "--merged-repo", "<ORG>/qwen3-ios-v1-hf",
            "--max-steps", "20",
            "--save-steps", "10",
            "--eval-steps", "10",
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

✅ **VERIFIED** — the [Modal Volumes guide](https://modal.com/docs/guide/volumes) says attached
Volumes commit in the background every few seconds and take a final snapshot on container shutdown.
The explicit `checkpoints.commit()` above makes the successful return boundary visible; it is not
the only point at which checkpoint files become durable. Modal also recommends checkpointing and
reentrant jobs even when the planned run is shorter than its maximum timeout; see its
[long-training example](https://modal.com/docs/examples/long-training).

### 3.5 Run it on a GPU pod

For Runpod or a comparable GPU VM:

1. Start from a pinned PyTorch CUDA image.
2. Attach persistent storage at `/workspace`.
3. Put the script and dataset access credentials in the pod through a secret mechanism.
4. Run the same command with `--output-dir /workspace/outputs/qwen3-ios-v1` and
   `--environment-id` set to the pinned image digest or dependency-lock SHA-256.
5. Upload the merged model to the Hub or object storage before deleting the pod.
6. Stop or terminate the compute as soon as the upload and checksums complete.

Runpod distinguishes container disk, volume disk, network volume, and global volume. Its
[storage table](https://docs.runpod.io/pods/storage/types) says container disk is lost on restart,
volume disk is deleted with the Pod, and network volume survives independently. It also recommends
external long-term backup. Treat `/workspace` as a working checkpoint location, not the only copy
of a release model.

### 3.6 Map it onto SageMaker or another managed cloud

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

✅ **VERIFIED** — MLX 0.32.2 documents an official Linux CUDA wheel:

```bash
pip install "mlx[cuda12]" "mlx-lm[train]"
```

The current requirements are Linux with glibc 2.35 or later, Python 3.10 or later, NVIDIA SM 7.5
or later, CUDA 12 or later, and driver 550.54.14 or later. CUDA 13 has a separate extra and higher
driver floor. Check the live [MLX installation page](https://ml-explore.github.io/mlx/build/html/install.html)
before choosing a provider image.

MLX-LM's `prompt`/`completion` format expects strings, not the message lists used by the TRL dataset
in §3. Prepare a pinned local model and a deterministic MLX-specific chat dataset instead. Save this
as `prepare_mlx_data.py` beside `publish_artifact.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["datasets"]
# ///

import argparse
import hashlib
import json
import os
from pathlib import Path

from datasets import load_dataset


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args()


def normalize(row: dict) -> dict:
    prompt = row.get("prompt")
    completion = row.get("completion")
    if not isinstance(prompt, list) or not prompt:
        raise ValueError("prompt must be a non-empty message list")
    if not isinstance(completion, list) or len(completion) != 1:
        raise ValueError("completion must contain exactly one assistant message")
    messages = [*prompt, *completion]
    for message in messages:
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("role"), str)
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError("every message needs string role and content fields")
    if completion[0]["role"] != "assistant":
        raise ValueError("completion message must have the assistant role")
    return {"messages": messages}


def write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(normalize(row), sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    args = arguments()
    dataset = load_dataset(
        args.dataset_id,
        revision=args.dataset_revision,
        split="train",
    )
    split = dataset.train_test_split(test_size=0.05, seed=42)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    train_path = args.data_dir / "train.jsonl"
    valid_path = args.data_dir / "valid.jsonl"
    write_jsonl(train_path, split["train"])
    write_jsonl(valid_path, split["test"])

    inputs = {
        "base_model": {"id": args.base_model, "revision": args.base_revision},
        "dataset": {
            "id": args.dataset_id,
            "revision": args.dataset_revision,
            "fingerprints": {
                "source": dataset._fingerprint,
                "train_jsonl_sha256": sha256(train_path),
                "valid_jsonl_sha256": sha256(valid_path),
            },
        },
    }
    receipt = {"schema_version": 1, "inputs": inputs, "artifacts": {}}
    if args.receipt.exists():
        existing = json.loads(args.receipt.read_text(encoding="utf-8"))
        if existing.get("schema_version") != 1 or existing.get("inputs") != inputs:
            raise ValueError("existing receipt belongs to different immutable inputs")
        receipt = existing
    atomic_write(args.receipt, receipt)


if __name__ == "__main__":
    main()
```

The same style of job can now run entirely from those immutable local inputs:

```bash
mkdir -p /outputs/mlx-run
hf download Qwen/Qwen3-0.6B \
  --revision <BASE_COMMIT_SHA> \
  --local-dir /outputs/mlx-run/base-model

python prepare_mlx_data.py \
  --base-model Qwen/Qwen3-0.6B \
  --base-revision <BASE_COMMIT_SHA> \
  --dataset-id <ORG>/<DATASET> \
  --dataset-revision <DATASET_COMMIT_SHA> \
  --data-dir /outputs/mlx-run/data \
  --receipt /outputs/mlx-run/publication-receipt.json

mlx_lm.lora \
  --model /outputs/mlx-run/base-model \
  --data /outputs/mlx-run/data \
  --train \
  --mask-prompt \
  --iters 600 \
  --adapter-path /outputs/mlx-run/adapters

mlx_lm.fuse \
  --model /outputs/mlx-run/base-model \
  --adapter-path /outputs/mlx-run/adapters \
  --save-path /outputs/mlx-run/fused

mlx_lm.generate \
  --model /outputs/mlx-run/fused \
  --prompt "Give the fixed smoke-test answer."

python publish_artifact.py hub \
  --receipt /outputs/mlx-run/publication-receipt.json \
  --artifact mlx_fused \
  --repo <ORG>/qwen3-ios-v1-mlx-fused \
  --folder /outputs/mlx-run/fused \
  --message "Pinned fused MLX checkpoint" \
  --source-commit-sha <BASE_COMMIT_SHA>
```

The [MLX CUDA announcement](https://github.com/ml-explore/mlx/discussions/2422) explicitly
demonstrated `mlx_lm.lora` on CUDA, and the current
[mlx-lm LoRA guide](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) documents local
and Hub datasets, prompt masking, resume, evaluation, and fusion.

This route already produces an MLX-format fused model. The helper prints and records the returned
commit SHA. Skip the conversion commands in §5, and continue at §5.1 with
`<ORG>/qwen3-ios-v1-mlx-fused` and that commit SHA. It is a separate MLX-only branch, not an input
to the Core AI export in §6.

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

if test -e artifacts/qwen3-ios-v1-mlx-4bit; then
  echo "mlx_lm.convert requires a new --mlx-path; choose a fresh destination" >&2
else
  .venv-mlx/bin/mlx_lm.convert \
    --model artifacts/qwen3-ios-v1-hf \
    --mlx-path artifacts/qwen3-ios-v1-mlx-4bit \
    --quantize \
    --q-bits 4 \
    --q-group-size 64

  .venv-mlx/bin/mlx_lm.generate \
    --model artifacts/qwen3-ios-v1-mlx-4bit \
    --prompt "Give the fixed smoke-test answer."

  python publish_artifact.py hub \
    --receipt artifacts/publication-receipt.json \
    --artifact mlx_4bit \
    --repo <ORG>/qwen3-ios-v1-mlx-4bit \
    --folder artifacts/qwen3-ios-v1-mlx-4bit \
    --message "Pinned four-bit MLX checkpoint" \
    --source-commit-sha <MERGED_MODEL_COMMIT_SHA>
fi
```

Do not copy only the `safetensors` shards. The tokenizer, model config, chat template, special-token
configuration, and quantization metadata are part of the runtime contract.

✅ **VERIFIED** — current `mlx_lm.convert` rejects an existing `--mlx-path` and exposes no
`--force` or overwrite flag. The preflight fails safely instead of deleting an earlier conversion.

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

✅ **VERIFIED** — `ModelConfiguration(id:revision:)` is declared in
[`ModelConfiguration.swift`](https://github.com/ml-explore/mlx-swift-lm/blob/3cbf928b5eb24190e8952725699ae6a3bb02824d/Libraries/MLXLMCommon/ModelConfiguration.swift),
and the revision flows to the package's downloader. The fence remains illustrative because the
repository's SDK-only snippet verifier does not resolve third-party Swift packages.

This macro-based downloader is the shortest proof of life. A shipping app generally needs its own
background/resumable download policy, checksum verification, cellular policy, and local
`ModelConfiguration(directory:)`. The full implementation choices are in
[Part 13: MLX in Swift](../part-13-mlx-swift/README.md), and model distribution is covered by
[Part 15](../part-15-shipping-and-operating/README.md).

## 6. Export the merged checkpoint for Core AI on iOS

Core AI is a different branch from the same master checkpoint. Do not convert the quantized MLX
artifact into Core AI. Start again from `artifacts/qwen3-ios-v1-hf`, which §5 downloaded at
`<MERGED_MODEL_COMMIT_SHA>`. The exporter ultimately passes this local directory through the
Transformers `from_pretrained` path, so the Core AI and MLX branches can consume the same immutable
master without another Hub resolution or private-repository login.

Use macOS 27, Xcode 27, and the separately installed Metal Toolchain. Clone Apple's recipe
repository rather than relying on a wheel when using its source-tree compression YAMLs:

```bash
xcodebuild -downloadComponent MetalToolchain
git clone https://github.com/apple/coreai-models.git
cd coreai-models
git checkout --detach 5ed9981303b38d5a44aa6b45509bc4f6945029f5
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

cd ..
tar -czf artifacts/coreai-ios.tar.gz -C artifacts coreai-ios

# Publish the archive through the reviewed release channel, then record its identity.
python publish_artifact.py file \
  --receipt artifacts/publication-receipt.json \
  --artifact coreai_ios \
  --file artifacts/coreai-ios.tar.gz \
  --release-url <COREAI_RELEASE_URL> \
  --source-commit-sha <MERGED_MODEL_COMMIT_SHA> \
  --exporter-commit-sha 5ed9981303b38d5a44aa6b45509bc4f6945029f5
```

✅ **VERIFIED** — at the pinned exporter commit, the CLI's model positional reaches Transformers'
local-directory loading path. `--experimental` permits a model without a registry preset when
compute precision is explicit. The fine-tuned model has no exact registry preset even though its
architecture remains Qwen3; changing model code or tensor names during training can still make
export fail.

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
- [ ] `run-manifest.json` records environment, arguments, input revisions, and evaluation results.
- [ ] `publication-receipt.json` records adapter, merged-HF, MLX, and Core AI publication
      identities, including the Core AI archive digest and exporter commit.
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
