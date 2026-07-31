# mlx-lm (ml-explore/mlx-lm) — Deep Dive Research Notes

> **Provenance**: Everything below was read from the local clone at
> `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-lm` in this session.
> HEAD = `e5baded8c1d286754edb479ffbde4655a68e2758` — *"Support for Poolside LagunaXS open
> source coding model in nvfp4 (#1334)"*, dated **Sun Jul 26 2026**. Clone is `--depth 50`
> so only the last 50 commits are visible.
> Package version: `mlx_lm/_version.py` → `__version__ = "0.31.3"`.
> Nothing here is from memory; line references are to the files as they exist at this commit.

---

## 1. Package metadata, versions, dependencies

`setup.py` (74 lines, verbatim essentials):

```python
MIN_MLX_VERSION = "0.31.2"

setup(
    name="mlx-lm",
    version=__version__,                      # 0.31.3
    description="LLMs with MLX and the Hugging Face Hub",
    author_email="mlx@group.apple.com",
    author="MLX Contributors",
    url="https://github.com/ml-explore/mlx-lm",
    license="MIT",
    install_requires=[
        f"mlx>={MIN_MLX_VERSION}; platform_system == 'Darwin'",
        "numpy",
        "transformers>=5.7.0",
        "sentencepiece",
        "protobuf",
        "pyyaml",
        "jinja2",
    ],
    packages=[
        "mlx_lm", "mlx_lm.models", "mlx_lm.quant",
        "mlx_lm.tuner", "mlx_lm.tool_parsers", "mlx_lm.chat_templates",
    ],
    python_requires=">=3.8",
    extras_require={
        "test": ["datasets", "lm-eval"],
        "train": ["datasets", "tqdm"],
        "evaluate": ["lm-eval", "tqdm"],
        "cuda13": [f"mlx[cuda13]>={MIN_MLX_VERSION}"],
        "cuda12": [f"mlx[cuda12]>={MIN_MLX_VERSION}"],
        "cpu": [f"mlx[cpu]>={MIN_MLX_VERSION}"],
    },
    ...
)
```

Key facts:
- **mlx >= 0.31.2 required, but only pinned on Darwin** (`platform_system == 'Darwin'`).
  Non-macOS installs get mlx via the `cuda12` / `cuda13` / `cpu` extras
  (`pip install "mlx-lm[cuda13]"`). So mlx-lm now targets **CUDA and CPU backends**, not just
  Apple silicon.
- **transformers >= 5.7.0** (bumped in commit `c89c93c`, "transformers>=5.7 (#1356)"). This is a
  major-version bump vs the transformers 4.x era — chat-template / tokenizer APIs differ.
- `python_requires=">=3.8"` but source uses `X | None` PEP-604 unions in
  `mlx_lm/quant/awq.py`, `mlx_lm/tool_parsers/*.py` (e.g. `tools: Any | None = None`) which
  need Python ≥ 3.10 at runtime, and `list[tuple[str, str]]` annotations in `cli_ui.py`. The
  declared 3.8 floor is stale.
- Install variants from README: `pip install mlx-lm` or `conda install -c conda-forge mlx-lm`.

### Undeclared runtime imports (real footguns)
| Module | Imported by | In `install_requires`? |
|---|---|---|
| `rich` | `mlx_lm/cli_ui.py` (module-level: `from rich.console import Console`, `rich.progress`, `rich.panel`, `rich.theme`) — pulled in by `chat.py`, `lora.py`, `tuner/trainer.py`, `tuner/utils.py`, `tuner/datasets.py` | **No** |
| `regex` | `mlx_lm/tool_parsers/{pythonic,mistral,qwen3_coder,gemma4,kimi_k2,glm47,longcat,minimax_m2}.py` (`import regex as re`) | **No** |
| `tqdm` | `mlx_lm/lora.py`, `quant/*.py`, `evaluate.py`, `share.py` (module level) | Only in `[train]`/`[evaluate]` extras |
| `huggingface_hub` | `utils.py`, `server.py`, `manage.py`, `share.py` | Not listed (arrives transitively via transformers) |
| `datasets` | `tuner/datasets.py` (lazy, inside functions) | `[train]`/`[test]` |
| `lm_eval` | `evaluate.py` (module level) | `[evaluate]`/`[test]` |
| `aiohttp` | `benchmarks/server_benchmark.py` | No |
| `mlx._distributed_utils` | `share.py` (`from mlx._distributed_utils.common import Hostfile`) | via mlx |

### CI (`.github/workflows/pull_request.yml`)
- `check_lint`: ubuntu-22.04, Python 3.10, `pre-commit/action@v3.0.1`.
- `mac_build_and_test`: `[self-hosted, macos]`, conda (miniconda, py3.10), `pip install -e ".[test]"`,
  downloads `test_data.zip` from the `test_data` release tag, then:
  ```
  METAL_DEVICE_WRAPPER_TYPE=1 METAL_DEBUG_ERROR_MODE=0 HF_HOME="." \
      python -m xmlrunner discover -v tests -o test-results/
  mlx.launch -n 2 tests/model_parallel_tests.py
  ```
- Formatting: `black` 25.1.0 + `isort` 6.0.0 (`--profile=black`) via `.pre-commit-config.yaml`.
- Release: tag `v*` → `python -m build` → PyPI trusted publishing.

---

## 2. CLI surface — every entry point

`setup.py` `console_scripts` (exact list):

```
mlx_lm               = mlx_lm.cli:main
mlx_lm.awq           = mlx_lm.quant.awq:main
mlx_lm.dwq           = mlx_lm.quant.dwq:main
mlx_lm.dynamic_quant = mlx_lm.quant.dynamic_quant:main
mlx_lm.gptq          = mlx_lm.quant.gptq:main
mlx_lm.benchmark     = mlx_lm.benchmark:main
mlx_lm.cache_prompt  = mlx_lm.cache_prompt:main
mlx_lm.chat          = mlx_lm.chat:main
mlx_lm.convert       = mlx_lm.convert:main
mlx_lm.evaluate      = mlx_lm.evaluate:main
mlx_lm.fuse          = mlx_lm.fuse:main
mlx_lm.generate      = mlx_lm.generate:main
mlx_lm.lora          = mlx_lm.lora:main
mlx_lm.perplexity    = mlx_lm.perplexity:main
mlx_lm.server        = mlx_lm.server:main
mlx_lm.share         = mlx_lm.share:main
mlx_lm.manage        = mlx_lm.manage:main
mlx_lm.upload        = mlx_lm.upload:main
```

`mlx_lm/cli.py` also supports `python -m mlx_lm <subcommand>`:

```python
subcommands = ("benchmark","cache_prompt","chat","convert","evaluate","fuse","generate",
               "lora","manage","perplexity","awq","dwq","dynamic_quant","gptq","server",
               "upload","share")
subpackages = {"awq":"quant","dwq":"quant","dynamic_quant":"quant","gptq":"quant"}
```
- `mlx_lm --version` prints `__version__`; `mlx_lm -h/--help` lists subcommands only.
- Every module's `if __name__ == "__main__":` prints a deprecation banner:
  `"Calling `python -m mlx_lm.generate...` directly is deprecated. Use `mlx_lm.generate...` or `python -m mlx_lm generate ...` instead."`

### 2.1 `mlx_lm.generate` (`mlx_lm/generate.py:54-213`)
Defaults (module constants, lines 36-47):
```python
DEFAULT_PROMPT = "hello"
DEFAULT_MAX_TOKENS = 100
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_MIN_P = 0.0
DEFAULT_TOP_K = 0
DEFAULT_XTC_PROBABILITY = 0.0
DEFAULT_XTC_THRESHOLD = 0.0          # NOTE: argparse default is 0.1, see gotchas
DEFAULT_MIN_TOKENS_TO_KEEP = 1
DEFAULT_SEED = None
DEFAULT_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
DEFAULT_QUANTIZED_KV_START = 5000
```

Full flag list:

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--model` | str | `None` → `mlx-community/Llama-3.2-3B-Instruct-4bit` | local dir or HF repo |
| `--trust-remote-code` | store_true | False | tokenizer **and** custom `model_file` arch |
| `--adapter-path` | str | None | LoRA/DoRA adapter dir |
| `--extra-eos-token` | str, `nargs="+"` | `()` | extra stop tokens |
| `--system-prompt` | str | None | prepended as `{"role":"system"}` |
| `--prompt` / `-p` | str | `"hello"` | `-` reads stdin; `\n`/`\t` escapes expanded |
| `--prefill-response` | str | None | appends an assistant msg + `continue_final_message=True` |
| `--max-tokens` / `-m` | int | 100 | |
| `--temp` | float | 0.0 | 0 ⇒ argmax |
| `--top-p` | float | 1.0 | only active when `0 < top_p < 1.0` |
| `--min-p` | float | 0.0 | |
| `--top-k` | int | 0 | must satisfy `0 < top_k < vocab_size` when enabled |
| `--xtc-probability` | float | 0.0 | |
| `--xtc-threshold` | float | **0.1** | must be in `[0, 0.5]` |
| `--min-tokens-to-keep` | int | 1 | for min-p |
| `--seed` | int | None | `mx.random.seed` |
| `--ignore-chat-template` | store_true | False | |
| `--use-default-chat-template` | store_true | False | |
| `--chat-template-config` | JSON str | None | kwargs to `apply_chat_template` |
| `--verbose` | `str2bool` | True | `"false"/"f"` ⇒ False (case-insensitive) |
| `--max-kv-size` | int | None | rotating cache size |
| `--prompt-cache-file` | str | None | `.safetensors` prompt cache |
| `--quantize-activations` / `-qa` | store_true | False | needs nvfp4/mxfp8 weights |
| `--kv-bits` | int | None | KV-cache quantization bits |
| `--kv-group-size` | int | 64 | |
| `--quantized-kv-start` | int | 5000 | step at which to switch to quantized KV |
| `--draft-model` | str | None | speculative decoding |
| `--num-draft-tokens` | int | 3 | |

Examples:
```bash
mlx_lm.generate --prompt "How tall is Mt Everest?"
mlx_lm.generate --model mistralai/Mistral-7B-Instruct-v0.3 --prompt "hello"
mlx_lm.generate --model mlx-community/Qwen3-8B-4bit -m 512 --temp 0.7 --top-p 0.9 \
                --kv-bits 4 --quantized-kv-start 1024 --max-kv-size 4096
mlx_lm.generate --prompt-cache-file mistral_prompt.safetensors \
                --prompt "\nSummarize the above text."
mlx_lm.generate --model big-model --draft-model small-model --num-draft-tokens 4
```

Prompt-cache semantics in `main()` (lines 2070-2150):
- Model is read from the cache metadata; passing a **different** `--model` raises
  `ValueError("Providing a different model ... is an error.")`.
- `--kv-bits` / `--kv-group-size` must match the saved `QuantizedKVCache` or it errors.
- When a cache is used with a chat template, the code re-renders the template with the user
  content replaced by the literal `"<query>"` and slices the prompt from that index, so only the
  *suffix* is fed to the model:
  ```python
  messages[-1]["content"] = "<query>"
  test_prompt = tokenizer.apply_chat_template(messages, tokenize=False, ...)
  prompt = prompt[test_prompt.index("<query>"):]
  prompt = tokenizer.encode(prompt, add_special_tokens=False)
  ```

### 2.2 `mlx_lm.chat` (`mlx_lm/chat.py`)
Defaults: `DEFAULT_TEMP=0.0`, `DEFAULT_TOP_P=1.0`, `DEFAULT_XTC_PROBABILITY=0.0`,
`DEFAULT_XTC_THRESHOLD=0.0`, `DEFAULT_SEED=0`, `DEFAULT_MAX_TOKENS=256`,
`DEFAULT_MODEL="mlx-community/Llama-3.2-3B-Instruct-4bit"`.

Flags: `--model --trust-remote-code --adapter-path --temp --top-p --xtc-probability
--xtc-threshold --seed --max-kv-size --max-tokens/-m --system-prompt --pipeline`.

REPL commands (from `cli_ui.print_chat_help` + `chat.main`): **`q` = exit, `r` = reset context
(rebuilds the prompt cache), `h` = help**. Context is preserved via a single
`make_prompt_cache(model, args.max_kv_size)` shared across turns.

Distributed: if `mx.distributed.init().size() > 1`, uses `sharded_load` with
`pipeline_group` if `--pipeline` else `tensor_group`; **adapters are rejected in distributed
mode** (`parser.error("Adapters not supported in distributed mode")`).

### 2.3 `mlx_lm.convert` (`mlx_lm/convert.py`)
| Flag | Default | Notes |
|---|---|---|
| `--hf-path` / `--model` | — | same dest (`hf_path`) |
| `--mlx-path` | `mlx_model` | **must not already exist** |
| `-q` / `--quantize` | False | |
| `--q-group-size` | None → mode default | |
| `--q-bits` | None → mode default | |
| `--q-mode` | `affine` | choices: `affine`, `mxfp4`, `nvfp4`, `mxfp8` |
| `--quant-predicate` | None | choices: `mixed_2_6`, `mixed_3_4`, `mixed_3_6`, `mixed_4_6` |
| `--dtype` | None | choices `float16`,`bfloat16`,`float32`; else from config `torch_dtype` |
| `--upload-repo` | None | |
| `-d`/`--dequantize` | False | mutually exclusive with `-q` |
| `--trust-remote-code` | False | |

```bash
mlx_lm.convert --model mistralai/Mistral-7B-Instruct-v0.3 -q
mlx_lm.convert --model mistralai/Mistral-7B-Instruct-v0.3 -q --upload-repo mlx-community/my-4bit-mistral
mlx_lm.convert --model Qwen/Qwen3-8B -q --q-mode nvfp4          # group_size 16, bits 4
mlx_lm.convert --model meta-llama/Llama-3.1-8B -q --q-bits 3 --quant-predicate mixed_3_6
```
Errors: `ValueError(f"Cannot save to the path {mlx_path} as it already exists...")`;
`ValueError("Choose either quantize or dequantize, not both.")`;
quant predicates only work with `--q-mode affine`.

### 2.4 `mlx_lm.lora` (`mlx_lm/lora.py`)
`CONFIG_DEFAULTS` (lines 44-81), which double as CLI defaults when unspecified:
```python
{"model": "Qwen/Qwen3-0.6b", "train": False, "fine_tune_type": "lora",
 "optimizer": "adam",
 "optimizer_config": {"adam": {}, "adamw": {}, "muon": {}, "sgd": {}, "adafactor": {}},
 "data": "mlx-community/WikiSQL", "seed": 0, "num_layers": 16, "batch_size": 4,
 "iters": 1000, "val_batches": 25, "learning_rate": 1e-5, "steps_per_report": 10,
 "steps_per_eval": 200, "resume_adapter_file": None, "adapter_path": "adapters",
 "save_every": 100, "test": False, "test_batches": 500, "max_seq_length": 2048,
 "config": None, "grad_checkpoint": False, "grad_accumulation_steps": 1,
 "clear_cache_threshold": 0, "lr_schedule": None,
 "lora_parameters": {"rank": 8, "dropout": 0.0, "scale": 20.0},
 "mask_prompt": False, "report_to": None, "project_name": None,
 "trust_remote_code": False}
```
Flags: `--model --train --data --fine-tune-type {lora,dora,full}
--optimizer {adam,adamw,muon,sgd,adafactor} --mask-prompt --num-layers --batch-size --iters
--val-batches --learning-rate --steps-per-report --steps-per-eval --grad-accumulation-steps
--resume-adapter-file --adapter-path --save-every --test --test-batches --max-seq-length
-c/--config --grad-checkpoint --clear-cache-threshold --report-to --project-name --seed
--trust-remote-code`.

- `--num-layers -1` = all layers (`model.layers[-max(num_layers,0):]`, so `-1` → `[0:]`).
- `--clear-cache-threshold` uses `_parse_size` so it accepts `"4GB"`, `"512MB"`, `"1e9"`-ish
  digits + unit (`M`, `G`, `MB`, `GB`, or bare bytes).
- `--report-to wandb`, `--report-to swanlab`, or `--report-to wandb,swanlab`.
- Note the odd YAML loader override at the top of `lora.py` — it re-registers the implicit float
  resolver so `1e-5` in YAML parses as a float (PyYAML 1.1 would give a string).
- CLI flags override YAML: `for k, v in config.items(): if args.get(k) is None: args[k] = v`.

### 2.5 `mlx_lm.fuse` (`mlx_lm/fuse.py`)
`--model` (default `mlx_model`), `--save-path` (default `fused_model`), `--adapter-path`
(default `adapters`), `--upload-repo`, `--dequantize`, `--export-gguf`,
`--gguf-path` (default `ggml-model-f16.gguf`), `--trust-remote-code`.

Fusing is generic: `[(n, m.fuse(dequantize=args.dequantize)) for n, m in model.named_modules()
if hasattr(m, "fuse")]` then `model.update_modules(tree_unflatten(fused_linears))`.
GGUF export is restricted: `if model_type not in ["llama", "mixtral", "mistral"]: raise
ValueError(f"Model type {model_type} not supported for GGUF conversion.")`.

### 2.6 `mlx_lm.server` (`mlx_lm/server.py:1717-1862`)
| Flag | Default |
|---|---|
| `--model` | None (lazy — model can be chosen per-request) |
| `--adapter-path` | None |
| `--host` | `127.0.0.1` |
| `--port` | `8080` |
| `--allowed-origins` | `"*"` (comma-split into a list when given) |
| `--draft-model` | None |
| `--num-draft-tokens` | 3 |
| `--trust-remote-code` | False |
| `--log-level` | `INFO` (`DEBUG/INFO/WARNING/ERROR/CRITICAL`) |
| `--chat-template` | `""` |
| `--use-default-chat-template` | False |
| `--temp` | 0.0 |
| `--top-p` | 1.0 |
| `--top-k` | 0 |
| `--min-p` | 0.0 |
| `--max-tokens` | 512 |
| `--chat-template-args` | `{}` — JSON, e.g. `'{"enable_thinking":false}'` |
| `--decode-concurrency` | 32 |
| `--prompt-concurrency` | 8 |
| `--prefill-step-size` | 2048 |
| `--prompt-cache-size` | 10 (max distinct KV caches) |
| `--prompt-cache-bytes` | None (`_parse_size`, e.g. `--prompt-cache-bytes 8GB`) |
| `--pipeline` | False (use pipelining instead of tensor parallelism) |

On startup it sets the wired limit if Metal is available:
```python
if mx.metal.is_available():
    mx.set_wired_limit(mx.device_info()["max_recommended_working_set_size"])
```
and warns: *"mlx_lm.server is not recommended for production as it only implements basic
security checks."*

### 2.7 `mlx_lm.cache_prompt`
`--model` (default `mlx_model`), `--adapter-path`, `--trust-remote-code`, `--eos-token`,
`--max-kv-size`, `--prompt-cache-file` (**required**), `--prompt` (**required**, `-` = stdin),
`--kv-bits`, `--kv-group-size` (64), `--quantized-kv-start` (5000).

```bash
cat prompt.txt | mlx_lm.cache_prompt \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --prompt - \
  --prompt-cache-file mistral_prompt.safetensors
```
Internally it calls `generate_step(y, model, max_tokens=0, prompt_cache=cache, ...)` and drains
the (empty) generator, then `save_prompt_cache(file, cache, metadata)` with
`metadata = {"model": args.model, "tokenizer_config": json.dumps(tokenizer_config)}`.
Uses `apply_chat_template(messages, add_generation_prompt=False, continue_final_message=True)`.

### 2.8 `mlx_lm.evaluate` (lm-evaluation-harness bridge)
```bash
mlx_lm.evaluate --model mlx_model \
  --tasks winogrande boolq arc_challenge arc_easy hellaswag openbookqa piqa social_iqa
mlx_lm.evaluate --model model/repo --task mmlu_pro          # from BENCHMARKS.md
```
Flags: `--model` (required), `--tasks` (nargs="+", required), `--output-dir` (`.`),
`--batch-size` (16), `--num-shots` (None), `--max-tokens` (None → `DEFAULT_MAX_TOKENS = 8192`),
`--limit`, `--seed` (123), `--fewshot-as-multiturn`, `--apply-chat-template`
(`BooleanOptionalAction`, i.e. `--no-apply-chat-template` works), `--chat-template-args` (JSON),
`--confirm-run-unsafe-code`, `--trust-remote-code`, `--temp` (0.0), `--top-p` (1.0), `--top-k` (0).

Registers an lm-eval model: `@register_model("mlxlm") class MLXLM(LM)` implementing
`loglikelihood`, `loglikelihood_rolling`, `generate_until`. `generate_until` routes through
`batch_generate(...)`. Results are written to
`"_".join(["eval", model.replace("/","_"), lm_eval_version, [num_shots], *tasks])`.
Distributed-aware: requests are split `requests[rank::size]` and gathered with
`mx.distributed.all_gather`.

### 2.9 `mlx_lm.perplexity`
`--model` (required), `--trust-remote-code`, `--batch-size` (8), `--sequence-length` (512),
`--num-samples` (256, `-1` = all), `--data-path` (`allenai/tulu-3-sft-mixture`), `--seed` (123).
Reports `Perplexity: {ppl:.3f} ± {se:.3f}` where the standard error uses a delta approximation:
`standard_error_ppl = ppl * (std/sqrt(n_tokens))`.

### 2.10 `mlx_lm.benchmark`
`--model`, `--prompt-tokens/-p` (512), `--generation-tokens/-g` (1024), `--batch-size/-b` (1),
`--num-trials/-n` (5), `--pipeline`, `--quantize-activations/-qa`, `--prefill-step-size` (2048),
`--delay` (0 s between trials), `--trust-remote-code`.
It generates **random token IDs** as the prompt and blanks EOS
(`tokenizer._eos_token_ids = {}`) so generation never stops early. `batch_size == 1` uses
`stream_generate`, otherwise `batch_generate`. Reports `prompt_tps`, `generation_tps`,
`peak_memory` per trial + averages.

`mlx_lm/BENCHMARKS.md` gives the canonical commands and a results table
(64 GB M4 Max, mlx 0.29.2.dev, mlx-lm 0.28.2, macOS 26.1), e.g. Qwen3-4B-Instruct-2507:
bf16 MMLU-Pro 64.05 @ 52.47 gen tok/s / 9.02 GB; q4 60.72 @ 134.52 tok/s / 3.35 GB.

### 2.11 `mlx_lm.manage`
`--scan`, `--delete`, `--pattern` (default `"mlx"`). Scans/deletes from the HF cache via
`huggingface_hub.scan_cache_dir()`; delete prompts for y/n confirmation.

### 2.12 `mlx_lm.upload`
`--path` (default `mlx_model`), `--upload-repo`. Thin wrapper on `utils.upload_to_hub`.

### 2.13 `mlx_lm.share` (new, © 2026)
Distributes a model directory to other nodes over `mx.distributed` (no HF download on each
node). `--path`, `--model`, `--hostfile`, `--dst`, `--tmpdir`.
- If run with world size 1 it *re-launches itself* via
  `mlx._distributed_utils.launch.launch_ring` / `launch_jaccl` using the hostfile.
- Backend must be one of `ring`, `jaccl`, `jaccl-ring`; hostfile must have >1 host and a
  `backend` field.
- Transfers in 100 MB chunks (`CHUNK_SIZE = 100 * 1024 * 1024`) using `mx.distributed.all_sum`
  as the transport, preserving directories/symlinks (`DirectoryEntry`), writing to a
  `TemporaryDirectory` then `os.rename`.
- Error text when nothing found: *"The --path needs to exist in at least one node. If it is a
  remote repository download it first with `hf download`"*.

### 2.14 Learned-quantization CLIs
See §7.

---

## 3. Python API

`mlx_lm/__init__.py`:
```python
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
from .convert import convert
from .generate import batch_generate, generate, stream_generate
from .utils import load
__all__ = ["__version__", "convert", "batch_generate", "generate", "stream_generate", "load"]
```

### 3.1 `load`
```python
def load(
    path_or_hf_repo: str,
    tokenizer_config: Optional[Dict[str, Any]] = None,
    model_config: Optional[Dict[str, Any]] = None,
    adapter_path: Optional[str] = None,
    lazy: bool = False,
    return_config: bool = False,
    revision: Optional[str] = None,
    trust_remote_code: bool = False,
) -> Union[Tuple[nn.Module, TokenizerWrapper],
           Tuple[nn.Module, TokenizerWrapper, Dict[str, Any]]]
```
(`mlx_lm/utils.py:482`)

```python
from mlx_lm import load, generate
model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.3-4bit")
prompt = tokenizer.apply_chat_template(
    [{"role": "user", "content": "Write a story about Einstein"}],
    add_generation_prompt=True,
)
text = generate(model, tokenizer, prompt=prompt, verbose=True)
```

Tokenizer options:
```python
model, tokenizer = load(
    "qwen/Qwen-7B",
    tokenizer_config={"eos_token": "<|endoftext|>", "trust_remote_code": True},
)
```

Related helpers in `utils.py`: `load_model`, `load_config`, `load_tokenizer`, `load_adapters`,
`sharded_load`, `pipeline_load`, `save`, `save_model`, `save_config`, `make_shards`,
`quantize_model`, `dequantize_model`, `upload_to_hub`, `create_model_card`,
`get_total_parameters`, `compute_bits_per_weight`, `common_prefix_len`,
`does_model_support_input_embeddings`, `hf_repo_to_path`, `_parse_size`.

Download filter (`DEFAULT_ALLOW_PATTERNS`, utils.py:219):
```python
["*.json", "model*.safetensors", "*.py", "tokenizer.model", "*.tiktoken",
 "tiktoken.model", "*.txt", "*.jsonl", "*.jinja"]
```
`hf_repo_to_path(hf_repo)` calls `snapshot_download(..., local_files_only=True,
allow_patterns=DEFAULT_ALLOW_PATTERNS)` — the `allow_patterns` was added specifically to fix
`IncompleteSnapshotError` (commit `4128c00`).

ModelScope support: set `MLXLM_USE_MODELSCOPE=true` and `pip install modelscope` and
`snapshot_download` comes from modelscope instead of huggingface_hub (utils.py:27-33).

At import, `utils.py` raises the fd limit: `resource.setrlimit(resource.RLIMIT_NOFILE, (2048, 4096))`.

### 3.2 `stream_generate`
```python
def stream_generate(
    model: nn.Module,
    tokenizer: Union[PreTrainedTokenizer, TokenizerWrapper],
    prompt: Union[str, mx.array, List[int]],
    max_tokens: int = 256,
    draft_model: Optional[nn.Module] = None,
    **kwargs,                     # forwarded to generate_step / speculative_generate_step
) -> Generator[GenerationResponse, None, None]
```
```python
from mlx_lm import load, stream_generate
model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.3-4bit")
for response in stream_generate(model, tokenizer, prompt, max_tokens=512):
    print(response.text, end="", flush=True)
```

`GenerationResponse` dataclass (generate.py:260-287):
```python
text: str
token: int
logprobs: mx.array         # full vector of log probs for the step
from_draft: bool           # True if produced by the draft model
prompt_tokens: int
prompt_tps: float
generation_tokens: int
generation_tps: float
peak_memory: float         # GB
finish_reason: Optional[str] = None   # "stop" | "length" | None
```
Behavior details:
- If `prompt` is a `str`, `add_special_tokens` is inferred:
  `tokenizer.bos_token is None or not prompt.startswith(tokenizer.bos_token)`.
- EOS token is **not** emitted: the loop `break`s before `detokenizer.add_token(token)` when
  `token in tokenizer.eos_token_ids`.
- A final `GenerationResponse` is always yielded after `detokenizer.finalize()` carrying
  `finish_reason`.
- The whole loop runs inside `with wired_limit(model, [generation_stream])`.
- When `draft_model` is given, `max_kv_size` and `prompt_progress_callback` kwargs are
  **silently dropped**; when it is `None`, `num_draft_tokens` is dropped.

### 3.3 `generate`
```python
def generate(model, tokenizer, prompt, verbose: bool = False, **kwargs) -> str
```
Concatenates `response.text`; when `verbose=True` prints `==========` fences plus
prompt tokens/tps, generation tokens/tps, peak memory. **Returns `None` (not `""`) if no text
was generated** (`if len(text) == 0: print("No text generated for this prompt"); return`).

### 3.4 `generate_step` — the core generator
```python
def generate_step(
    prompt: mx.array,
    model: nn.Module,
    *,
    max_tokens: int = 256,                 # -1 ⇒ infinite
    sampler: Optional[Callable[[mx.array], mx.array]] = None,
    logits_processors: Optional[List[Callable[[mx.array, mx.array], mx.array]]] = None,
    max_kv_size: Optional[int] = None,
    prompt_cache: Optional[Any] = None,    # updated IN PLACE
    prefill_step_size: int = 2048,
    kv_bits: Optional[int] = None,
    kv_group_size: int = 64,
    quantized_kv_start: int = 0,
    prompt_progress_callback: Optional[Callable[[int, int], None]] = None,
    input_embeddings: Optional[mx.array] = None,
) -> Generator[Tuple[mx.array, mx.array], None, None]      # yields (token_id:int, logprobs)
```
- Default sampler is `lambda x: mx.argmax(x, axis=-1)`.
- Logprobs are computed as `logits - mx.logsumexp(logits, keepdims=True)`.
- Prefill loop processes `min(prefill_step_size, remaining-1)` tokens per step, calls
  `mx.eval([c.state for c in prompt_cache])` and `mx.clear_cache()` after each chunk.
- During decode, `mx.clear_cache()` every 256 tokens (`if n % 256 == 0`).
- Uses `mx.async_eval(next_y, next_logprobs)` for one-step lookahead pipelining.
- `input_embeddings`: requires `does_model_support_input_embeddings(model)` (checks for an
  `input_embeddings` parameter in `model.__call__`'s signature) and either an empty prompt or
  `len(prompt) == len(input_embeddings)`.

Generation stream (commit `ed1fca4` "Thread local generation stream"):
```python
generation_stream = mx.new_thread_local_stream(mx.default_device())
```

`wired_limit` context manager (generate.py:220-257):
```python
model_bytes = tree_reduce(lambda acc, x: acc + x.nbytes if isinstance(x, mx.array) else acc, model, 0)
max_rec_size = mx.device_info()["max_recommended_working_set_size"]
if model_bytes > 0.9 * max_rec_size:
    print("[WARNING] Generating with a model that requires {model_mb} MB which is close to the "
          "maximum recommended size of {max_rec_mb} MB. This can be slow. ...")
old_limit = mx.set_wired_limit(max_rec_size)
```
README fix for that warning: `sudo sysctl iogpu.wired_limit_mb=N` (macOS ≥ 15 required for
memory wiring at all).

### 3.5 `speculative_generate_step`
```python
def speculative_generate_step(
    prompt: mx.array, model: nn.Module, draft_model: nn.Module, *,
    num_draft_tokens: int = 2, max_tokens: int = 256,
    sampler=None, logits_processors=None, prompt_cache=None,
    prefill_step_size: int = 512, kv_bits=None, kv_group_size=64, quantized_kv_start=0,
) -> Generator[Tuple[mx.array, mx.array, bool], None, None]
```
- **The prompt cache must be trimmable**, else:
  `ValueError(f"Speculative decoding requires a trimmable prompt cache (got {types}).")`
  → RotatingKVCache past `max_size` and `ArraysCache`-based (SSM/Mamba) models cannot be used.
- When a `prompt_cache` is passed it is split: `model_cache = prompt_cache[:len(model.layers)]`,
  `draft_cache = prompt_cache[len(model.layers):]` — i.e. the caller concatenates both caches
  (this is exactly what `server._serve_single` does).
- Accept/reject: greedy match `tokens[n] != draft_tokens[n]` ⇒ break. Cache is rewound in a
  `finally:` via `_rewind_cache(num_draft, n)` → `trim_prompt_cache(model_cache, num_draft-n)`
  and `trim_prompt_cache(draft_cache, max(num_draft-n-1, 0))`.
- If **all** draft tokens are accepted, the last draft token is prepended to the next draft
  input because the draft model hasn't processed it yet.
- Note `speculative_generate_step`'s default `num_draft_tokens=2` while the CLI/server default
  is 3, and `prefill_step_size` default is 512 here vs 2048 in `generate_step`.
- `mlx_lm.generate` validates
  `draft_tokenizer.vocab_size != tokenizer.vocab_size → ValueError("Draft model tokenizer does not match model tokenizer.")`;
  the server only **warns**.

Test expectation (tests/test_generate.py:86-117) — using the model as its own draft with
`num_draft_tokens=2` and `max_tokens=5`:
```python
self.assertEqual(drafted, [True, True, False, True, True])
```

### 3.6 `batch_generate` and `BatchGenerator` (continuous batching)

```python
def batch_generate(
    model, tokenizer,
    prompts: List[List[int]],                       # token id lists, NOT strings
    prompt_caches: Optional[List[List[Any]]] = None,
    max_tokens: Union[int, List[int]] = 128,
    verbose: bool = False,
    return_prompt_caches: bool = False,
    return_token_ids: bool = False,
    return_logprobs: bool = False,
    **kwargs,                                       # → BatchGenerator
) -> BatchResponse
```
```python
@dataclass
class BatchResponse:
    texts: List[str]
    stats: BatchStats
    caches: Optional[List[List[Any]]]
    token_ids: Optional[List[List[int]]] = None
    logprobs: Optional[List[List[float]]] = None     # logprob of the SAMPLED token
```
`return_logprobs` / `return_token_ids` were added in commit `2c008fd`; the docstring calls out
the RL use-case: *"Useful for reinforcement learning (e.g. RLOO, PPO) where behavior
log-probabilities are needed for importance weighting."*

`BatchStats`: `prompt_tokens, prompt_tps, prompt_time, generation_tokens, generation_tps,
generation_time, peak_memory`.

`BatchGenerator.__init__` (generate.py:1576):
```python
BatchGenerator(
    model, *,
    max_tokens: int = 128,
    stop_tokens: Optional[Sequence[Sequence[int]]] = None,
    sampler=None,
    logits_processors=None,
    completion_batch_size: int = 32,     # max sequences decoding at once
    prefill_batch_size: int = 8,         # max sequences prefilling at once
    prefill_step_size: int = 2048,
    max_kv_size: Optional[int] = None,
    stream=None,
)
```
`completion_batch_size = max(completion_batch_size, prefill_batch_size)`. It sets the wired
limit in `__init__` and restores it in `close()`/`__del__`.

Public methods:
- `insert(prompts, max_tokens=None, caches=None, all_tokens=None, samplers=None,
   logits_processors=None, stop_matchers=None) -> List[int]  # uids`
- `insert_segments(segments: List[List[List[int]]], ...)` — segmented prefill; the generator is
  guaranteed to **stop at segment boundaries** (used by the server for per-segment KV caching of
  system prompt / user turn / thinking tail).
- `next() -> (prompt_responses, generation_responses)`
- `next_generated() -> List[GenerationBatch.Response]` (loops until generation output exists)
- `extract_cache(uids) -> {uid: (cache, tokens)}`
- `remove(uids, return_prompt_caches=False)`
- `prompt_cache_nbytes` property
- `stats(stats=None)` context manager returning a `BatchStats`
- `close()`

`GenerationBatch.Response`: `uid, token, logprobs, finish_reason, prompt_cache, all_tokens`
(the last two are only populated on the final response for a uid).
`PromptProcessingBatch.Response`: `uid, progress: tuple, end_of_segment: bool, end_of_prompt: bool`.

`_make_cache` maps regular caches → batch caches:
`KVCache → BatchKVCache`, `RotatingKVCache → BatchRotatingKVCache` (**`keep > 0` raises
`ValueError("RotatingKVCache with keep tokens is not supported.")`**), `ArraysCache` gets
`left_padding` set, `CacheList` recurses; anything else →
`ValueError(f"{type(c)} does not yet support batching")`.

Batchability check in the server: `all(hasattr(c, "merge") for c in make_prompt_cache(model))`.

Working example (`mlx_lm/examples/batch_generate_response.py`, verbatim):
```python
from mlx_lm import batch_generate, load

checkpoint = "mlx-community/Llama-3.2-3B-Instruct-4bit"
model, tokenizer = load(path_or_hf_repo=checkpoint)

prompts = ["Write a story about Einstein.", "Why is the sky blue?",
           "What time is it?", "How tall is Mt Everest?"]
prompts = [tokenizer.apply_chat_template([{"role": "user", "content": p}],
                                         add_generation_prompt=True) for p in prompts]

result = batch_generate(model, tokenizer, prompts, verbose=False,
                        return_prompt_caches=True, max_tokens=2048)
print(result.texts[-1])

prompts = ["Could you summarize that?", "And what about the sea?", "Try again?", "And Mt Olympus?"]
prompts = [tokenizer.apply_chat_template([{"role": "user", "content": p}],
                                         add_generation_prompt=True) for p in prompts]
result = batch_generate(model, tokenizer, prompts, verbose=False, prompt_caches=result.caches)
print(result.texts[-1])
```

### 3.7 Stop detection & text state machine (generate.py:887-1085)
- `_build_trie(sequences)` builds an **Aho–Corasick** trie with `__fail__` links and `__match__`
  markers.
- `StopSequenceMatcher(stop_sequences)` — token-level. API:
  `make_state()`, `StopSequenceMatcher.match(state, trie, token) -> (new_state, matched: bool)`.
- `make_stop_matcher(tokenizer, stop_words=None)` builds it from `tokenizer.eos_token_ids` plus
  `tokenizer.encode(w, add_special_tokens=False)` for each stop word.
- `TextStateMachine(transitions: Dict[str, List[Tuple[str, str]]])` — **text-level** state
  machine (commit `86e9b35` "Text-based state machine for tool/reasoning parsing"). Docstring:
  *"Matching on text rather than token ids is robust to tokenization differences (e.g. a
  marker's trailing `>` being merged with the following byte)."*
  ```python
  sm = TextStateMachine(transitions={
      "normal":    [("<think>", "reasoning"), ("<tool_call>", "tool")],
      "reasoning": [("</think>", "normal")],
      "tool":      [("</tool_call>", "normal")],
  })
  state = sm.make_state(initial="normal")
  state, emittable_text, current_state = TextStateMachine.step(state, chunk)
  state, remaining, cur = TextStateMachine.flush(state)    # use on finish_reason == "length"
  state, cur = TextStateMachine.discard(state)             # use on finish_reason == "stop"
  ```
  Runtime state is the tuple `(state_name, trie_node, states, buffer)`; text is only emitted
  once it can't be part of a match.
- `make_text_state_machine(tokenizer, stop_words=None)` wires up
  `think_start/think_end/tool_call_start/tool_call_end` from the tokenizer and adds stop words as
  self-transitions in every state so they get stripped without changing state.

---

## 4. Sampling & logits processors (`mlx_lm/sample_utils.py`, 369 lines)

```python
def make_sampler(
    temp: float = 0.0,
    top_p: float = 0.0,
    min_p: float = 0.0,
    min_tokens_to_keep: int = 1,
    top_k: int = 0,
    xtc_probability: float = 0.0,
    xtc_threshold: float = 0.1,
    xtc_special_tokens: List[int] = [],
) -> Callable[[mx.array], mx.array]
```
Order of application (only enabled filters are chained, then `categorical_sampling`):
1. `apply_top_p` — only if `0 < top_p < 1.0`
2. `apply_min_p` — if `min_p != 0.0`
3. `apply_xtc` — if `xtc_probability > 0.0`
4. `apply_top_k` — if `top_k > 0`
5. `categorical_sampling(logprobs, temp)` = `mx.random.categorical(logits * (1/temp))`

`temp == 0` short-circuits the whole thing to `lambda x: mx.argmax(x, axis=-1)`.

All four filters are `@partial(mx.compile, inputs=mx.random.state, outputs=mx.random.state)`.

Validation errors:
- `apply_top_k`: `` f"`top_k` has to be an integer in the (0, {vocab_size}) interval, but is {top_k}." `` (exclusive bounds — fixed in commit `df48987`).
- `apply_min_p`: `` f"`min_p` has to be a float in the [0, 1] interval, but is {min_p}" `` and `min_tokens_to_keep` must be a positive int.
- `apply_xtc`: threshold in `[0, 0.5]`, probability in `[0, 1]`.

XTC implementation (per-row min, fixed in `7661de1`):
```python
probs = mx.softmax(logits, -1)
mask = probs > mx.where(probs > xtc_threshold, probs, mx.inf).min(axis=-1, keepdims=True)
if xtc_special_tokens:
    mask[..., xtc_special_tokens] = False
return mx.where(mx.random.uniform(0, 1) > xtc_probability, logits, mx.where(mask, -mx.inf, logits))
```
Callers pass `xtc_special_tokens=tokenizer.encode("\n") + list(tokenizer.eos_token_ids)`
(generate.py:2168, server.py:389, chat.py:152) so newlines and EOS are never XTC-suppressed.

`apply_top_p` sorts **ascending** and keeps `cumulative_probs > 1 - top_p`.
`apply_min_p` works in log space: `scaled_min_p = max_logprob + math.log(min_p)`.

```python
def make_logits_processors(
    logit_bias: Optional[Dict[int, float]] = None,
    repetition_penalty: Optional[float] = None,
    repetition_context_size: Optional[int] = 20,
    presence_penalty: Optional[float] = None,
    presence_context_size: Optional[int] = 20,
    frequency_penalty: Optional[float] = None,
    frequency_context_size: Optional[int] = 20,
) -> List[Callable[[mx.array, mx.array], mx.array]]
```
Individual factories: `make_repetition_penalty(penalty, context_size=20)` (sign-aware
multiplicative, arXiv:1909.05858), `make_presence_penalty` (additive, subtract once),
`make_frequency_penalty` (additive per occurrence, uses `logits.at[:, tokens].subtract(penalty)`).
`logit_bias` uses `logits.at[:, indices].add(values)`.

**Processor contract**: `processor(tokens: mx.array, logits: mx.array) -> mx.array`, where
`logits` is `(batch, vocab)` and `tokens` is the token history. Test
`test_batch_generate_processor_tokens_match_prompt_on_first_step` asserts the first call
receives the whole prompt as an `mx.array`.

---

## 5. KV caches & prompt caching (`mlx_lm/models/cache.py`, 1764 lines)

### 5.1 Module-level functions
```python
make_prompt_cache(model: nn.Module, max_kv_size: Optional[int] = None) -> List[Any]
save_prompt_cache(file_name: str, cache: List[Any], metadata: Dict[str, str] = {})
load_prompt_cache(file_name, return_metadata=False)
can_trim_prompt_cache(cache: List[Any]) -> bool
trim_prompt_cache(cache: List[Any], num_tokens: int) -> int   # returns #trimmed, in-place
create_attention_mask(N, offset, return_array, window_size)
```
`make_prompt_cache` defers to `model.make_cache()` when present; otherwise it makes
`RotatingKVCache(max_size=max_kv_size, keep=4)` per layer if `max_kv_size` is given, else
`KVCache()` per layer. **Note the `keep=4`** — "old entries (except the first 4 tokens) will be
overwritten".

Serialization format: `save_prompt_cache` writes a `.safetensors` where the tensors are
`tree_flatten([c.state for c in cache])` and the metadata is
`tree_flatten([[c.meta_state ...], user_metadata, [type(c).__name__ ...]])`.
`load_prompt_cache` reconstructs with `globals()[class_name].from_state(state, meta_state)` —
so **only classes defined in `cache.py` can be round-tripped**.

### 5.2 Cache classes
| Class | Purpose | `is_trimmable()` | `to_quantized()` | batch `merge` |
|---|---|---|---|---|
| `_BaseCache` | ABC: `state`, `meta_state`, `size()`, `nbytes`, `empty()`, `from_state` | False | — | — |
| `ConcatenateKVCache` | simplest, `mx.concatenate` each step | True | — | — |
| `KVCache` | growable buffer, `step = 256` | True | ✅ `(group_size=64, bits=4)` | ✅ → `BatchKVCache` |
| `QuantizedKVCache(group_size=64, bits=8)` | packed uint32 + scales + biases | True | — | — |
| `RotatingKVCache(max_size, keep=0)` | ring buffer, `_temporal_order()` reordering | **only while `offset < max_size`** | ❌ `NotImplementedError("RotatingKVCache Quantization NYI")` | ✅ → `BatchRotatingKVCache` |
| `ChunkedKVCache(chunk_size)` | keeps only last `chunk_size`, tracks `start_position` | True | — | — |
| `ArraysCache(size, left_padding=None)` | generic slot list for SSM/Mamba/linear-attn states | False | — | ✅ |
| `CacheList(*caches)` | composite (e.g. hybrid attention+SSM layers) | all(...) | — | ✅ |
| `BatchKVCache(left_padding: List[int])` | left-padded batched KV | True | — | classmethod `merge` |
| `BatchRotatingKVCache(max_size, left_padding)` | batched sliding window | `_offset < max_size` | ❌ NYI | classmethod `merge` |
| `TokenBuffer(tokens=[])` | append-efficient int32 token buffer for logits processors | — | — | — |

`BatchKVCache` docstring shows the left-padding convention verbatim:
```
E.g. the following prompts:
    [1, 3, 5]
    [7]
    [2, 6, 8, 9]
Should be padded like so:
    [0, 1, 3, 5]
    [0, 0, 0, 7]
    [2, 6, 8, 9]
And ``left_padding`` specifies the amount of padding for each.
In this case, ``left_padding = [1, 3, 0]``.
```
Batch caches expose `prepare(left_padding=, lengths=, right_padding=)`, `finalize()`,
`filter(batch_indices)`, `extend(other)`, `extract(idx)` (→ a single-sequence `KVCache` /
`RotatingKVCache`), and use `dynamic_roll(x, shifts, axis)` (a `take_along_axis` based
per-row roll) to right-justify right-padded prefills.

`maybe_quantize_kv_cache(prompt_cache, quantized_kv_start, kv_group_size, kv_bits)` swaps in
`c.to_quantized(...)` once `c.offset >= quantized_kv_start`.

### 5.3 Server-side prompt caching: `PromptTrie` + `LRUPromptCache`
```python
@dataclass
class PromptTrieResult:
    model: Any
    exact: Optional[List[int]]     # exact match found
    shorter: Optional[List[int]]   # longest prefix with a value
    longer: Optional[List[int]]    # shortest value extending beyond tokens
    common_prefix: int
```
`PromptTrie`: `add(model, tokens, value)`, `get`, `pop`, `pop_prefixes`, `search`.

```python
class LRUPromptCache:
    def __init__(self, max_size: int = 10, max_bytes: int = 1 << 63)
    def fetch_nearest_cache(self, model, tokens) -> (cache_or_None, remaining_tokens)
    def insert_cache(self, model, tokens, prompt_cache, *, cache_type: str = "assistant")
    def trim_to(self, *, n_sequences=None, n_bytes=None)
    def stats_by_type(self) -> {cache_type: {"n_sequences": int, "n_bytes": int}}
    nbytes  # property
```
- Eviction ordering class `CacheOrder(ordering=["assistant", "user", "system"])`. `pop()` evicts
  from the *earlier* category while it has at least as many entries as the next one — i.e.
  assistant caches are dropped before user, and user before system.
- `fetch_nearest_cache` can rewind a **longer** cached sequence via `trim_prompt_cache` when the
  common prefix is longer than the best shorter match:
  ```python
  cache = copy.deepcopy(cache_entry.prompt_cache)
  prefix = min(len(tokens) - 1, result.common_prefix)
  trim_prompt_cache(cache, len(result.longer) - prefix)
  return cache, tokens[prefix:]
  ```
- `insert_cache` removes strict prefixes when the cache is trimmable ("they just take space").

Test `tests/test_prompt_cache.py` and `tests/test_server.py::TestLRUPromptCache` are excellent
executable docs for the semantics (prefix hits, byte-based trimming, root-entry eviction).

### 5.4 Multi-turn prompt caching example (`mlx_lm/examples/chat.py`, verbatim)
```python
from mlx_lm import generate, load
from mlx_lm.models.cache import load_prompt_cache, make_prompt_cache, save_prompt_cache

model, tokenizer = load("mlx-community/Mistral-7B-Instruct-v0.3-4bit")
prompt_cache = make_prompt_cache(model)

prompt = tokenizer.apply_chat_template([{"role": "user", "content": "Hi my name is <Name>."}],
                                       add_generation_prompt=True)
response = generate(model, tokenizer, prompt=prompt, verbose=True, prompt_cache=prompt_cache)

prompt = tokenizer.apply_chat_template([{"role": "user", "content": "What's my name?"}],
                                       add_generation_prompt=True)
response = generate(model, tokenizer, prompt=prompt, verbose=True, prompt_cache=prompt_cache)

save_prompt_cache("mistral_prompt.safetensors", prompt_cache)
prompt_cache = load_prompt_cache("mistral_prompt.safetensors")
```

---

## 6. The OpenAI-compatible server (`mlx_lm/server.py`, 1870 lines)

### 6.1 Endpoints
POST:
- `/v1/completions` → `object: "text_completion"`, id `cmpl-<uuid4>`
- `/v1/chat/completions` and `/chat/completions` → `chat.completion` / `chat.completion.chunk`,
  id `chatcmpl-<uuid4>`

GET:
- `/v1/models` and `/v1/models/<repo_id>` (path suffix filters by repo id)
- `/health` → `{"status": "ok"}`

`OPTIONS` returns 204 with CORS headers. Unknown paths → 404 `Not Found`.

Server class = `ThreadingHTTPServer`, handler `APIHandler(BaseHTTPRequestHandler)`.
`system_fingerprint = f"{mlx_lm_version}-{mx.__version__}-{platform.platform()}-{gpu_arch}"`.

### 6.2 Request fields actually parsed (`do_POST`, lines 1110-1147)
```
stream (False), stream_options, model ("default_model"), draft_model ("default_model"),
num_draft_tokens (cli default 3), adapters (None), max_completion_tokens | max_tokens (cli 512),
temperature, top_p, top_k, min_p, repetition_penalty (0.0), repetition_context_size (20),
presence_penalty (0.0), presence_context_size (20), frequency_penalty (0.0),
frequency_context_size (20), xtc_probability (0.0), xtc_threshold (0.1), logit_bias (None),
logprobs (False), top_logprobs (-1), seed (None), chat_template_kwargs (None),
stop (str or list[str]), messages, tools, role_mapping, prompt
```
Validation (`validate_model_parameters`, lines 1178-1206):
- `max_tokens >= 0`, `temperature >= 0`, `0 <= top_p <= 1`, `top_k >= 0`, `0 <= min_p <= 1`,
  `num_draft_tokens >= 0`, penalties/context sizes `>= 0`,
  `top_logprobs` int in `[0, 11]` **or** the sentinel `-1`,
  `0 <= xtc_probability <= 1`, `0 <= xtc_threshold <= 1`, `logit_bias` dict of int→float.
- Missing `Content-Length` → **411**; bad int → 400; bad JSON → 400; non-dict body → 400.
- Any exception raised while creating the generator returns **404** with `{"error": str(e)}`
  (yes, 404 — see gotchas).

`stream_options: {"include_usage": true}` emits a final usage-only chunk before `data: [DONE]`.

### 6.3 Response shape
```json
{
  "id": "chatcmpl-…", "system_fingerprint": "…", "object": "chat.completion",
  "model": "…", "created": 1699999999,
  "choices": [{"index": 0, "finish_reason": "stop",
               "message": {"role": "assistant", "content": "…",
                           "reasoning": "…", "tool_calls": [...]}}],
  "usage": {"prompt_tokens": N, "completion_tokens": M, "total_tokens": N+M,
            "prompt_tokens_details": {"cached_tokens": K}}
}
```
- Reasoning is exposed as **`message.reasoning`** (streaming: `delta.reasoning`), *not*
  `reasoning_content`. See `mlx_lm/examples/openai_reasoning_content.py`:
  ```python
  reasoning = response.choices[0].message.reasoning
  ...
  if (reasoning := chunk.choices[0].delta.reasoning) is not None: ...
  ```
- `finish_reason` becomes `"tool_calls"` when generation ended with `stop` and a tool call was
  produced (`if finish_reason == "stop" and made_tool_call: finish_reason = "tool_calls"`).
- `usage.prompt_tokens_details.cached_tokens` reports the prompt-cache hit length
  (`ctx.prompt_cache_count`), only when `>= 0`.
- `logprobs` shape: with `top_logprobs > 0` → `choices[0].logprobs.content = [dict(top[0],
  top_logprobs=top), ...]`; with only `logprobs: true` → `[{"id": tok, "logprob": lp}, ...]`.
- Streaming keepalives are SSE comments: `": keepalive {processed}/{total}\n\n"` emitted from
  the prompt-progress callback so long prefills don't time out the connection.

### 6.4 Internal architecture
- `ModelProvider` — lazy load/cache of `(model_path, adapter_path, draft_model_path)`. Maps the
  magic name `"default_model"` to the CLI `--model` / `--adapter-path` / `--draft-model`.
  Refuses adapters/draft models in distributed mode.
- `ResponseGenerator` — owns a background `Thread(target=self._generate)`; requests arrive on a
  `queue.Queue` as `(response_queue, CompletionRequest, GenerationArguments)`.
  - **Batched path**: builds a `BatchGenerator(model, completion_batch_size=--decode-concurrency,
    prefill_batch_size=--prompt-concurrency, prefill_step_size=--prefill-step-size, stream=…)`
    and inserts each request via `insert_segments`.
  - **Sequential path** (`_serve_single`): used when `not self.model_provider.is_batchable` or
    `args.seed is not None` (`_is_batchable = model_provider.is_batchable and args.seed is None`),
    i.e. **any request with a `seed` forces non-batched generation**, and so does a loaded draft
    model.
  - Switching models drains the current batch (`drain_batch = True`).
- `_tokenize` splits a chat prompt into up to **3 segments** — system prompt, user context,
  thinking tail (`up to 11 tokens` looked back for a `think_start`) — with `segment_types`
  `["system", "user", "assistant"]`, so each boundary's KV cache is stored separately in the
  `LRUPromptCache` with the corresponding `cache_type`.
- `TimeBudget(budget=0.5, iterations=25, sync_frequency=10)` — bounds how long the generation
  thread spends before checking the request queue; in distributed mode it switches from a wall
  clock to an iteration count that is periodically re-tuned via `mx.distributed.all_sum`.
- Distributed request fan-out uses `pickle.dumps` + `mx.distributed.all_sum` of a `uint8` array
  (`_share_object`).
- `ToolCallFormatter` wraps the tokenizer's tool parser and emits OpenAI-shaped
  `{"function": {...}, "type": "function", "id": <uuid4>, "index": i}`; parse failures log
  *"Failed to parse tool call (… ) — tool text was likely truncated mid-generation."* and are
  dropped.
- `handle_models_request` scans the HF cache and only lists repos that contain
  `["config.json", "model.safetensors.index.json", "tokenizer_config.json"]`.

### 6.5 Client examples
```bash
curl localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say this is a test!"}],"temperature":0.7}'

curl localhost:8080/v1/models -H "Content-Type: application/json"
```
Tool use with the OpenAI SDK (`mlx_lm/examples/openai_tool_use.py`):
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")
response = client.chat.completions.create(model=model, messages=messages, tools=tools)
function = response.choices[0].message.tool_calls[0].function
tool_result = functions[function.name](**json.loads(function.arguments))
messages.append({"role": "tool", "name": function.name, "content": tool_result})
```

### 6.6 Load testing (`benchmarks/server_benchmark.py`)
```bash
mlx_lm.server
python server_benchmark.py --concurrency 4
```
Flags: `--url` (default `http://localhost:8080/v1/chat/completions`), `--api-key`, `--model`
(`default_model`), `--max-tokens` (100), `--concurrency` (1), `--total-requests` (10),
`--prompt-file`, `--output`. Reports TTFT min/max/avg/p95, per-request tok/s, aggregate tok/s,
and an ASCII bar plot of tokens/sec over time. Requires `aiohttp`.

---

## 7. Quantization

### 7.1 Static quantization at convert time
`utils.quantize_model(model, config, group_size, bits, mode="affine", quant_predicate=None)`:
```python
mode_defaults = {"affine": (64, 4), "mxfp4": (32, 4), "nvfp4": (16, 4), "mxfp8": (32, 8)}
```
- The predicate wrapper skips layers whose `weight.shape[-1] % group_size != 0` and layers
  without `to_quantized`.
- Per-layer overrides are written into `config["quantization"][path] = {"group_size":…, "bits":…}`;
  `config["quantization_config"] = config["quantization"]` "support hf model tree #957".
- If the model already has a `quantization` key, config becomes fine-grained per-layer.
- Models may define their own `quant_predicate` property; `quantize_model` picks it up via
  `getattr(model, "quant_predicate", None)`. Example (`models/gpt_oss.py:328`):
  ```python
  def quant_predicate(self):
      def predicate(path, _):
          if path.endswith("router"):
              return {"group_size": 64, "bits": 8}
          return True
  ```
  22 model files define one: `gemma4_text, granitemoe, gemma4, jamba, gpt_oss, granitemoehybrid,
  afmoe, longcat_flash_ngram, bailing_moe, kimi_linear, mellum, lfm2_moe, minimax,
  bailing_moe_linear, longcat_flash, qwen3_moe, qwen3_next, Klear, step3p5, qwen3_5,
  qwen3_vl_moe, rwkv7`.
- Prints `[INFO] Quantized model with {bpw:.3f} bits per weight.`
  (`compute_bits_per_weight` = `model_bytes * 8 / get_total_parameters(model)`).

### 7.2 Mixed-precision recipes (`convert.py:20-80`)
```python
QUANT_RECIPES = ["mixed_2_6", "mixed_3_4", "mixed_3_6", "mixed_4_6"]
```
Recipe → `(low_bits, high_bits)`: `mixed_2_6 → (2, 6)`, `mixed_3_4 → (3, 4)`,
`mixed_3_6 → (3, 6)`, `mixed_4_6 → (4, 6)`.
The predicate is llama.cpp-Q4_K_M-like (credited to Alex Barron / a llama.cpp permalink):
```python
use_more_bits = (index < num_layers // 8
                 or index >= 7 * num_layers // 8
                 or (index - num_layers // 8) % 3 == 2)
if ("v_proj" in path or "v_a_proj" in path or "v_b_proj" in path) and use_more_bits: high
if "down_proj" in path and use_more_bits: high
if "lm_head" in path: high
else: low
```
It requires the model to have `down_proj` modules, else
`ValueError("Model does not have expected keys for mixed quant.")`.

### 7.3 Loading externally-quantized checkpoints (`utils.load_model`, lines 391-419)
`config["quantization"]` is honored directly (including per-path dicts). Otherwise a legacy
`quantization_config` is translated:

| `quant_method` | Handling |
|---|---|
| `bitnet` | `from .models.bitlinear_layers import bitnet_quantize; model = bitnet_quantize(model, quantization_config)` |
| `mxfp4` | `{"group_size": 32, "bits": 4, "mode": "mxfp4"}` |
| `compressed-tensors` with `format == "nvfp4-pack-quantized"` | `{"group_size": 16, "bits": 4, "mode": "nvfp4"}` ← **this is the nvfp4 support** |
| `compressed-tensors` (other) | `{"group_size": 32, "bits": 4, "mode": "affine"}` |
| `awq` / `gptq` | `_transform_awq_weights(weights, quantization_config)` unpacks/transposes/repacks AutoAWQ-GPTQ 4-bit weights into MLX layout |

`_transform_awq_weights` details:
- Only `bits == 4` supported: `ValueError(f"Only {bits=} is supported for AutoAWQ/GPTQ models.")`
- Any `*.g_idx` key raises: *"Models with non-contiguous group indices (g_idx) are not currently
  supported. Please use a model without g_idx or re-quantize the model using mlx_lm.convert."*
- AWQ stores `qweight` as `[in_features, out//8]`; MLX wants `[out, in//8]`. Unpack shifts are
  the AWQ interleave `mx.array([0, 4, 1, 5, 2, 6, 3, 7]) * bits`.
- Bias conversion: MLX dequant is `w*scale + bias`, AWQ is `(w - zero)*scale`, so
  `biases = -zeros * scales`; symmetric case uses `zero_point = 1 << (bits-1)` (8).

### 7.4 Activation quantization (`--quantize-activations` / `-qa`)
`load_model` when `config["quantize_activations"]` is true swaps every `nn.QuantizedLinear` for
`nn.QQLinear(in_dims, out_dims, group_size, bits, mode)`:
```python
if m.mode not in ("nvfp4", "mxfp8"):
    raise ValueError("Mode ({m.mode}) does not support activation quantization")
if m.get("bias", False):
    raise ValueError("Linear layer with bias does not support activation quantization")
```
Exposed by `mlx_lm.generate -qa` and `mlx_lm.benchmark -qa` (passed as
`model_config={"quantize_activations": args.quantize_activations}`).

### 7.5 Learned quantization (`mlx_lm/LEARNED_QUANTS.md` + `mlx_lm/quant/`)
Doc summary (verbatim framing):
> DWQ fine-tunes non-quantized parameters (including quantization scales and biases) using the
> non-quantized model as a teacher. AWQ scales and clips the weights prior to quantization.
> Dynamic quantization estimates the sensitivity of a model's outputs to each layer and uses a
> higher precision for layers which have higher sensitivity. GPTQ finds quantized weights which
> minimize the squared error of each layer's output given the provided input.
> … Dynamic quantization is the fastest to run. DWQ takes longer but typically yields better
> results. You can also cascade methods.

Prereq for all: `pip install "mlx-lm[train]"`.

**Shared calibration data** (`mlx_lm/quant/utils.py`):
```python
save_dir = Path.home() / ".cache/mlx-lm/calibration_v5.txt"
url = "https://gist.githubusercontent.com/tristandruyen/9e207a95c7d75ddf37525d353e00659c/raw/571fda718462de863e5a0171078c175420c7649a/calibration_data_v5_rc.txt"
```
Downloaded once, tokenized, chunked into non-overlapping `sequence_length` blocks, randomly
permuted.

#### DWQ — `mlx_lm.dwq` (`quant/dwq.py`, 428 lines)
```bash
mlx_lm.dwq --model Qwen/Qwen3-0.6B
mlx_lm.dwq --model Qwen/Qwen3-8B --bits 3 --group-size 32 --batch-size 1 --max-seq-length 512
```
Flags (actual `argparse` defaults): `--model/-m` (**required**), `--quantized-model` (None),
`--mlx-path` (`mlx_model`), `--bits` (4), `--group-size` (64), `--num-samples` (**2048**),
`--max-seq-length` (**1025**), `--seed` (123), `--learning-rate` (1e-6), `--batch-size` (**4**),
`--data-path` (`allenai/tulu-3-sft-mixture`), `--grad-checkpoint`, `--target-dir`,
`--targets-only`, `--pipeline`, `--trust-remote-code`.

Mechanics:
- Unfreezes only quantization params of affine sub-8-bit layers:
  ```python
  if hasattr(m, "bits") and hasattr(m, "group_size") and m.mode == "affine" and m.bits < 8:
      m.unfreeze(keys=["scales", "biases"], recurse=False)
  ```
- Loss = `kl_div_loss(scale*logits, scale*targets)` with `scale = 1/temperature`, `temperature=2.0`.
- Optimizer `optimizers.Adam(learning_rate=args.learning_rate, bias_correction=True)`; params
  accumulated in float32, applied back as bfloat16.
- Optional pre-computed targets: with `--target-dir` it saves top-1024 logits + indices per batch
  as `{i:010d}.safetensors` (`--targets-only` to just compute and exit); this lets the teacher be
  freed. `has_targets` requires actual `*.safetensors` in `train/` **and** `valid/` (fix `f39cb8e`).
- Validation every 200 iterations; final warning if it regressed:
  `"❌❌❌\n[WARNING] Final validation loss … is worse than initial validation loss …"`.
- Doc tips: works best 2–4 bit; 16→8/6 bit "often doesn't work well"; `--group-size 32` doubles
  tunable params; distill from an 8-bit teacher and use `--max-seq-length 512` to save memory.

#### AWQ — `mlx_lm.awq` (`quant/awq.py`, 595 lines)
```bash
mlx_lm.awq --model Qwen/Qwen3-0.6B
```
Flags (actual defaults): `--model/-m` (`mlx-community/Qwen2.5-7B-Instruct-bf16`),
`--mlx-path` (`mlx_model`), `--bits` (4), `--group-size` (64), `--embed-bits` (4),
`--embed-group-size` (32), `--num-samples` (**128**), `--sequence-length` (512),
`--n-grid` (**20**), `--seed` (123), `--trust-remote-code`.

**Supported model types only** (`AWQ_MODEL_CONFIGS`):
`llama`, `mistral`, `qwen2`, `qwen3`, `gemma3_text`, `gemma3`, `deepseek_v2`.
Anything else: `NotImplementedError(f"AWQ support for {model_type} models NYI.")`.

Config dataclasses:
```python
@dataclass
class ScaleConfig:
    prev: nn.Module; layers: list[nn.Module]; block: nn.Module | None = None
    kwargs: list = field(default_factory=list); use_config: Callable | None = None

@dataclass
class AWQConfig:
    embed: str; lm_head: str; no_clip: list[str]
    scale_configs: list[ScaleConfig]; lm_key: str | None = None
```
Algorithm per transformer block: capture per-linear `input_feat` with a `Catcher` module →
quantize without AWQ to get a reference loss → grid search scales
(`scales = max(x_max**ratio, 1e-4)`, normalized by `sqrt(max*min)`, `ratio = i/n_grid`) →
fold scales into the previous op (`apply_scale` handles `Linear/SwitchLinear`, `LayerNorm/RMSNorm`,
and Gemma-style RMSNorm with the `1 + w` convention) → per-group clip search
(`max_shrink=0.5`, `n_frames=512` subsampled activations) → requantize.
If `after_loss > before_loss` it **reverts**: *"Loss is not reduced, falling back to original weights."*
Progress prints `Loss reduction: {after/before}` per block. Distributed-aware via
`mx.distributed.all_sum` and `dist_split`.

#### GPTQ — `mlx_lm.gptq` (`quant/gptq.py`, 239 lines)
```bash
mlx_lm.gptq --model Qwen/Qwen3-0.6B
```
Flags: `--model/-m` (`Qwen/Qwen3-0.6B-base`), `--mlx-path` (`mlx_model`), `--bits` (4),
`--group-size` (64), `--fallback-bits` (**6**), `--fallback-group-size` (64),
`--num-samples` (-1 = all), `--sequence-length` (512), `--seed` (123), `--trust-remote-code`.
- `assert bits in {2, 4, 8}, f"Unsupported bits {bits}"`.
- Hessians accumulated with a `Catcher` (`self.H = self.H + xf.T @ xf`), damped with
  `1e-2 * mean(diag(H))`, inverted with `mx.linalg.cholesky` / `cholesky_inv` **on the CPU
  stream** (`with mx.stream(mx.cpu)`).
- Applies only to `nn.Linear` / `SwitchLinear`; everything else quantizable gets the fallback
  config.

#### Dynamic quantization — `mlx_lm.dynamic_quant` (`quant/dynamic_quant.py`, 268 lines)
```bash
mlx_lm.dynamic_quant --model Qwen/Qwen3-0.6B --target-bpw 4.8
```
Flags: `--model/-m` (`Qwen/Qwen3-0.6B-base`), `--mlx-path` (`mlx_model`), `--seed` (123),
`--sensitivities` (path to a precomputed JSON), `--target-bpw` (5.0), `--low-bits` (4),
`--low-group-size` (64), `--high-bits` (5), `--high-group-size` (64), `--report-ppl`,
`--grad-checkpoint`, `--accumulation-dtype` (`float32`|`bfloat16`), `--trust-remote-code`.
- Sensitivity = `(accumulated_grad * (low_q_weight - high_q_weight)).sum() / (n_params/1e6)`,
  gradients of `kl_div_loss(q_model(batch), model(batch))`.
- Writes `{model.replace("/","_")}_sensitivities.json` for reuse.
- Threshold is found by **binary search** on bits-per-weight down to
  `tolerance = 1e-3 * (max_sens - min_sens)`.
- Doc: *"For a given set of quantization parameters only certain ranges are possible. For example,
  with the default parameters a BPW in the range `[4.5, 5.5]` is achievable."*

#### Post-quantization evaluation + upload
```bash
mlx_lm.evaluate --model mlx_model \
  --tasks winogrande boolq arc_challenge arc_easy hellaswag openbookqa piqa social_iqa
mlx_lm.upload --path mlx_model --upload-repo mlx-community/Mistral-7B-Instruct-v0.3-3bit-DWQ
```

### 7.6 Custom KL/JS kernels (`mlx_lm/tuner/losses.py`, 798 lines)
Public: `kl_div_loss(logits_q, logits_p)`, `js_div_loss(logits_q, logits_p)`; plus
`can_run_metal()`, `_make_kl_forward_kernel()`, `_make_kl_backward_kernel()`,
`_make_js_forward_kernel()`, `_make_js_backward_kernel()` and `@mx.custom_function`-registered
vjps. These are hand-written Metal kernels (with a fallback path) used by DWQ and dynamic quant.

---

## 8. Fine-tuning: LoRA / QLoRA / DoRA / full

### 8.1 End-to-end workflow (from `mlx_lm/LORA.md`)
```bash
pip install "mlx-lm[train]"

# 1. (optional) quantize the base model for QLoRA
mlx_lm.convert --model mistralai/Mistral-7B-v0.1 -q

# 2. train
mlx_lm.lora --model <path_to_model> --train --data <path_to_data> --iters 600
mlx_lm.lora --config /path/to/config.yaml
mlx_lm.lora --model <model> --train --fine-tune-type full --num-layers 8

# 3. test-set perplexity
mlx_lm.lora --model <path_to_model> --adapter-path <path_to_adapters> --data <data> --test

# 4. generate with adapters
mlx_lm.generate --model <path_to_model> --adapter-path <path_to_adapters> --prompt "..."

# 5. fuse
mlx_lm.fuse --model <path_to_model>
mlx_lm.fuse --model mistralai/Mistral-7B-v0.1 \
            --upload-repo mlx-community/my-lora-mistral-7b \
            --hf-path mistralai/Mistral-7B-v0.1
mlx_lm.fuse --model mistralai/Mistral-7B-v0.1 --export-gguf   # → fused_model/ggml-model-f16.gguf
```
> "If `--model` points to a quantized model, then the training will use QLoRA, otherwise it will
> use regular LoRA."
>
> Memory tips from LORA.md: QLoRA; `--batch-size 1`; `--grad-accumulation-steps N`;
> `--num-layers 4`; shorter sequences; `--grad-checkpoint`.
> "The above command on an M1 Max with 32 GB runs at about 250 tokens-per-second."

**⚠ `mlx_lm.fuse` has no `--hf-path` argument** in this version (only `--model`, `--save-path`,
`--adapter-path`, `--upload-repo`, `--dequantize`, `--export-gguf`, `--gguf-path`,
`--trust-remote-code`) — the LORA.md instruction to pass `--hf-path` is stale.

LORA.md claims LoRA works with: Mistral, Llama, Phi2, Mixtral, Qwen2, Gemma, OLMo, MiniCPM,
InternLM2 — but `linear_to_lora_layers` is generic and works with any model whose layers contain
`nn.Linear`/`nn.QuantizedLinear`/`SwitchLinear`/`QuantizedSwitchLinear`/`nn.Embedding`/
`nn.QuantizedEmbedding` or a `to_lora` method.

### 8.2 `linear_to_lora_layers` (`tuner/utils.py:38-110`)
```python
def linear_to_lora_layers(model, num_layers: int, config: Dict, use_dora: bool = False)
```
- `config` keys: `rank`, `scale`, `dropout`, optional `keys` (list of module paths).
- If `keys` is absent, **all** quantizable/linear/embedding submodules in every layer are
  collected automatically (`get_keys_for_lora`).
- Layers converted: `model.layers[-max(num_layers, 0):]`, plus top-level `model.named_modules()`
  entries matching `keys` (this is how `lm_head` / `model.embed_tokens` get LoRA'd).
- A layer may define `to_lora(r=, scale=, dropout=)` to customize (only honored when `use_dora`
  is False).
- `SwitchLinear`/`QuantizedSwitchLinear` + DoRA → `ValueError("... doesn't support DoRA yet.")`.

### 8.3 LoRA modules (`tuner/lora.py`)
`LoRALinear`, `LoRASwitchLinear`, `LoRAEmbedding`; each has `from_base(...)` and
`fuse(dequantize: bool = False)`.
```python
class LoRALinear(nn.Module):
    def __init__(self, input_dims, output_dims, r=8, dropout=0.0, scale=20.0, bias=False):
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
`fuse()`: `delta = ((self.scale * self.lora_b.T) @ self.lora_a.T).astype(weight.dtype)` added to
the (dequantized) base weight; re-quantized with the original `group_size`/`bits`/`mode` unless
`dequantize=True`. `LoRAEmbedding.as_linear(x)` supports tied embeddings.
For `LoRASwitchLinear` the update uses `mx.gather_mm(..., rhs_indices=indices, sorted_indices=…)`
with `lora_a: (num_experts, r, in)`, `lora_b: (num_experts, out, r)`.

### 8.4 DoRA modules (`tuner/dora.py`)
`DoRALinear` / `DoRAEmbedding`. Magnitude vector `self.m = ||W||_2 along axis=1` recomputed in
`set_linear`. Forward:
```python
w = self._dequantized_weight()
y = x @ w.T
z = (self.dropout(x) @ self.lora_a) @ self.lora_b
out = y + (self.scale * z).astype(x.dtype)
adapted = w + (self.scale * self.lora_b.T) @ self.lora_a.T
denom = mx.stop_gradient(mx.linalg.norm(adapted, axis=1))
out = (self.m / denom).astype(x.dtype) * out
```
**DoRA dequantizes the base weight on every forward pass** — much slower/heavier than LoRA on
quantized models. `DoRAEmbedding.from_base` raises
`ValueError("DoRAEmbedding does not yet support quantization.")` for quantized embeddings.

### 8.5 Trainer (`tuner/trainer.py`, 379 lines)
```python
@dataclass
class TrainingArgs:
    batch_size: int = 4
    iters: int = 100
    val_batches: int = 25
    steps_per_report: int = 10
    steps_per_eval: int = 200
    steps_per_save: int = 100
    max_seq_length: int = 2048
    adapter_file: str = "adapters.safetensors"
    grad_checkpoint: bool = False
    grad_accumulation_steps: int = 1
    clear_cache_threshold: int = 0
```
```python
def train(model, optimizer, train_dataset, val_dataset=None,
          args: TrainingArgs = TrainingArgs(),
          loss: callable = default_loss,
          iterate_batches: callable = iterate_batches,
          training_callback: TrainingCallback = None)

def evaluate(model, dataset, batch_size, num_batches, max_seq_length=2048,
             loss=default_loss, iterate_batches=iterate_batches,
             clear_cache_threshold=0, progress_callback=None) -> float   # avg loss
```
Loss (`default_loss`): next-token CE with a *two-sided* mask supporting prompt masking:
```python
steps = mx.arange(1, targets.shape[1] + 1)
mask = mx.logical_and(steps >= lengths[:, 0:1], steps <= lengths[:, 1:])
ce = (nn.losses.cross_entropy(logits, targets) * mask).astype(mx.float32).sum() / mask.sum()
```
`lengths` is `mx.array(list(zip(offsets, lengths)))` — column 0 is the prompt offset
(0 unless `--mask-prompt`), column 1 the true length.

Batching (`iterate_batches`):
- Dataset indices **sorted by length**; batches are contiguous slices of the sorted order,
  then batch order is permuted each epoch.
- `pad_to = 32`; `max_length_in_batch = min(1 + 32*ceil(max_len/32), max_seq_length)`.
- `ValueError(f"Dataset must have at least batch_size={batch_size} examples but only has {len(dataset)}.")`
- Distributed: `offset = comm_group.rank()`, `step = comm_group.size()`, and
  `ValueError("The batch size must be divisible by the number of workers")`.
- Warns when truncating: *"[WARNING] Some sequences are longer than {max_seq_length} tokens…
  Consider pre-splitting your data to save memory."*

Step function is `mx.compile`d over `state = [model.state, optimizer.state, mx.random.state]`;
gradient accumulation adds grads then divides by `grad_accum_steps` and calls
`average_gradients(grad)` (from `mlx.nn.utils`) before `optimizer.update`.

`grad_checkpoint(layer)` monkey-patches `type(layer).__call__` with an `mx.checkpoint`-wrapped
version — note it patches the **class**, so it affects all instances process-wide.

Checkpointing: every `steps_per_save` iters and at the end, `rank == 0` writes
`adapters.safetensors` plus `{it:07d}_adapters.safetensors` in the same dir.

Adapter config: `save_config(vars(args), adapter_path / "adapter_config.json")`;
`load_adapters(model, adapter_path)` reads it, rebuilds LoRA/DoRA layers from
`config.num_layers` + `config.lora_parameters` + `config.fine_tune_type`, and calls
`model.load_weights(adapters.safetensors, strict=False)`.
`fine_tune_type == "full"` skips the LoRA rebuild entirely.

`print_trainable_parameters(model)` prints
`Trainable parameters: X% (Y M/Z M)`.

LR schedules (`build_schedule`):
```yaml
lr_schedule:
  name: cosine_decay      # any attribute of mlx.optimizers.schedulers
  warmup: 100             # 0 for no warmup
  warmup_init: 1e-7       # 0 if not specified
  arguments: [1e-5, 1000, 1e-7]   # passed positionally to the scheduler
```
It joins a `linear_schedule(warmup_init, arguments[0], warmup)` with the main schedule at
boundary `[warmup_steps + 1]`.

### 8.6 Datasets (`tuner/datasets.py`, 334 lines)
Supported jsonl formats (auto-detected from the first record, one example per line):
```jsonl
{"messages": [{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
{"messages":[...], "tools":[{"type":"function","function":{...}}]}
{"prompt": "What is the capital of France?", "completion": "Paris."}
{"text": "This is an example for the model."}
```
Classes: `TextDataset(text_key="text")`, `ChatDataset(chat_key="messages", mask_prompt=False)`,
`CompletionsDataset(prompt_key, completion_key, mask_prompt)`, `ConcatenatedDataset`,
`CacheDataset` (memoizes `process()` results; exposes `itemlen(idx)`).
Detection order in `create_dataset`: prompt+completion → chat → text; else
`ValueError("Unsupported data format, check the supported formats here: …LORA.md#Data.")`.
`--mask-prompt` is not supported for `text` datasets
(`ValueError("Prompt masking not supported for text dataset.")`).
`TextDataset.process` appends `eos_token_id` if missing.

Local loading expects `train.jsonl`, `valid.jsonl` (optional), `test.jsonl` in `--data`.
HF datasets: pass a repo id to `--data`, or use YAML:
```yaml
hf_dataset:
  path: "billsum"
  prompt_feature: "text"
  completion_feature: "summary"
  train_split: "train[:1000]"     # default "train[:80%]"
  valid_split: "train[-100:]"     # default "train[-10%:]"
  test_split: ...
  config: {}                      # kwargs to datasets.load_dataset
```
A **list** of `hf_dataset` records is also supported and produces a `ConcatenatedDataset`.
Feature keys configurable: `prompt_feature`, `completion_feature`, `text_feature`, `chat_feature`.

### 8.7 Experiment tracking (`tuner/callbacks.py`)
```python
class TrainingCallback:
    def on_train_loss_report(self, train_info: dict): ...
    def on_val_loss_report(self, val_info: dict): ...
```
`train_info` keys: `iteration, train_loss, learning_rate, iterations_per_second,
tokens_per_second, trained_tokens, peak_memory`.
`val_info` keys: `iteration, val_loss, val_time`.
Built-ins: `WandBCallback`, `SwanLabCallback`, registry
`SUPPORT_CALLBACK = {"wandb": WandBCallback, "swanlab": SwanLabCallback}`, composed by
`get_reporting_callbacks(report_to, project_name, log_dir, config)` — comma-separated names are
**nested** (each wraps the previous).

⚠ Bug in `lora.run()`: the `training_callback` parameter is immediately overwritten by
`get_reporting_callbacks(...)`, so a programmatically-supplied callback is discarded, and if
`--report-to` is unset the callback becomes `None`.

---

## 9. Tokenizer layer (`mlx_lm/tokenizer_utils.py`, 651 lines)

### 9.1 Streaming detokenizers
`StreamingDetokenizer` interface: `reset()`, `add_token(token)`, `finalize()`, properties
`text`, `tokens`, `last_segment` (text since last access).
Implementations:
- `NaiveStreamingDetokenizer` — works with any HF tokenizer, **O(T²)** per line.
- `SPMStreamingDetokenizer(trim_space=True)` — SentencePiece `▁` handling, linear.
- `BPEStreamingDetokenizer` — GPT-2 byte-level decoder table (`make_byte_decoder`).

Selection is done by inspecting `tokenizer.json`'s `decoder` field
(`_is_spm_decoder`, `_is_spm_decoder_no_space`, `_is_bpe_decoder`). Docstring warning:
*"Note, to use a fast streaming tokenizer, pass a local file path rather than a Hugging Face
repo ID."*

### 9.2 `TokenizerWrapper`
```python
TokenizerWrapper(tokenizer, detokenizer_class=NaiveStreamingDetokenizer, eos_token_ids=None,
                 chat_template=None, tool_call_start=None, tool_call_end=None, tool_parser=None)
```
Adds: `apply_chat_template(*args, tokenize=True, **kwargs)` (defaults
`enable_thinking=self.has_thinking`, forces `return_dict=False`), `add_eos_token(token)`,
`eos_token_ids` (a mutable set), `detokenizer` (returns a **fresh** detokenizer each access),
`has_chat_template`, `has_thinking`, `think_start`, `think_end`, `think_start_id`,
`think_end_id`, `think_start_tokens`, `think_end_tokens`, `find_think_start`,
`rfind_think_start`, `find_think_end`, `rfind_think_end`, `has_tool_calling`,
`tool_call_start`, `tool_call_end`, `tool_call_start_tokens`, `tool_call_end_tokens`,
`tool_parser`. All other attribute access is forwarded to the wrapped HF tokenizer.

Thinking-token inference (`_infer_thinking`):
```python
THINK_TOKENS = [("<think>", "</think>"), ("<longcat_think>", "</longcat_think>")]
# multi-token: if "<|channel>" and "<channel|>" are in the vocab →
#   think_start = "<|channel>thought", think_end = "<channel|>"
```

`NewlineTokenizer(PreTrainedTokenizerFast)` — replaces `\n` ↔ `<n>` around encode/decode; it is
registered with `AutoTokenizer.register(NewlineTokenizer, fast_tokenizer_class=NewlineTokenizer)`.

### 9.3 Tool-call parsers (`mlx_lm/tool_parsers/`)
Each module exports `tool_call_start`, `tool_call_end`, and
`parse_tool_call(text, tools=None) -> dict | list[dict]` with keys `name`, `arguments`
(and optionally `id`).

| Module | `tool_call_start` / `tool_call_end` | Format |
|---|---|---|
| `json_tools` | `<tool_call>` / `</tool_call>` | plain JSON `{"name":…, "arguments":…}` |
| `qwen3_coder` | `<tool_call>` / `</tool_call>` | `<function=NAME><parameter=k>v</parameter></function>`, values coerced by the tool JSON-schema type |
| `gemma4` | `<\|tool_call>` / `<tool_call\|>` | `call:name{key: <\|"\|>str<\|"\|>}` with a recursive brace regex |
| `function_gemma` | — | `call:name{...}` variant |
| `mistral` | `[TOOL_CALLS]` / `""` (**empty**) | `name[ARGS]{json}` |
| `kimi_k2` | `<\|tool_calls_section_begin\|>` / `…_end\|>` | `functions.name:0<\|tool_call_argument_begin\|>{json}`, returns a list with `id` |
| `pythonic` | `<\|tool_call_start\|>` / `<\|tool_call_end\|>` | `[name(a="x", b=2)]`, values via `ast.literal_eval` |
| `glm47` | `<arg_key>`/`<arg_value>` markers | 3 accepted forms (JSON, `k=v`, arg_key/arg_value) |
| `longcat` | `<longcat_tool_call>` | `<longcat_arg_key>`/`<longcat_arg_value>` |
| `minimax_m2` | `<minimax:tool_call>` | `<invoke name="…"><parameter name="…">…</parameter></invoke>` |

Auto-selection (`_infer_tool_parser(chat_template)`) matches literal substrings in the chat
template, checked in this order:
`<minimax:tool_call>` → minimax_m2; `<|tool_call>` + `<tool_call|>` → gemma4;
`<start_function_call>` → function_gemma; `<longcat_tool_call>` → longcat;
`<arg_key>` → glm47; `<|tool_list_start|>` → pythonic; `<tool_call>\n<function=` → qwen3_coder;
`<|tool_calls_section_begin|>` → kimi_k2; `[TOOL_CALLS]` → mistral;
`<tool_call>` + `tool_call.name` → json_tools; else `None`.
An explicit `tool_parser_type` key in `tokenizer_config.json` overrides the inference.
Similarly `chat_template_type` in `tokenizer_config.json` loads
`mlx_lm.chat_templates.<name>.apply_chat_template` (only `deepseek_v32` ships today).

Manual tool-use without the server (`mlx_lm/examples/tool_use.py`):
```python
prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                       tools=list(tools.values()))
...
start_tool = response.find(tokenizer.tool_call_start) + len(tokenizer.tool_call_start)
end_tool = response.find(tokenizer.tool_call_end)
tool_call = tokenizer.tool_parser(response[start_tool:end_tool].strip())
tool_result = tools[tool_call["name"]](**tool_call["arguments"])
messages = [{"role": "tool", "name": tool_call["name"], "content": tool_result}]
```

---

## 10. The model zoo (`mlx_lm/models/`, 121 `.py` files)

Architecture files are named after `config.json`'s `model_type` (per CONTRIBUTING.md). A
`MODEL_REMAPPING` table in `utils.py` handles aliases:
```python
MODEL_REMAPPING = {
    "mistral": "llama", "llava": "mistral3", "phi-msft": "phixtral",
    "falcon_mamba": "mamba", "joyai_llm_flash": "deepseek_v3", "kimi_k2": "deepseek_v3",
    "qwen2_5_vl": "qwen2_vl", "minimax_m2": "minimax", "iquestcoder": "llama",
    "gemma4_unified": "gemma4",  # encoder-free multimodal variant; vision/audio weights stripped by sanitize()
}
```

Notable / recent architectures present: `afm7`, `afmoe`, `apertus`, `baichuan_m1`,
`bailing_moe(+_linear)`, `bitnet` (+`bitlinear_layers`), `cohere`/`cohere2`, `dbrx`,
`deepseek`, `deepseek_v2`, `deepseek_v3`, `deepseek_v32`, `dots1`, `ernie4_5(+_moe)`,
`exaone`, `exaone4`, `exaone_moe`, `falcon_h1`, `gemma`…`gemma4`/`gemma4_text`/`gemma3n`,
`glm`, `glm4`, `glm4_moe`, `glm4_moe_lite`, `glm_moe_dsa`, `gpt2`, `gpt_bigcode`, `gpt_neox`,
`gpt_oss`, `granite`/`granitemoe`/`granitemoehybrid`, `helium`, `hunyuan(+_v1_dense)`,
`internlm2`/`internlm3`, `iquestloopcoder`, `jamba`, `kimi_k25`, `kimi_linear`, `kimi_vl`,
`Klear`, **`laguna`** (Poolside LagunaXS, newest), `lfm2`, `lfm2_moe`, `lfm2-vl`, `lille-130m`,
`llama`, `llama4`/`llama4_text`, `longcat_flash(+_ngram)`, `mamba`, `mamba2`, `mellum`,
`mimo`, `mimo_v2_flash`, `minicpm`/`minicpm3`, `minimax`, `ministral3`, `mistral3`, `mixtral`,
`nanochat`, `nemotron`, `nemotron_h`, `nemotron-nas`, `olmo`/`olmo2`/`olmo3`/`olmoe`,
`openelm`, `phi`/`phi3`/`phi3small`/`phimoe`/`phixtral`, `pixtral`, `plamo`/`plamo2`,
`qwen`/`qwen2`/`qwen2_moe`/`qwen2_vl`/`qwen3`/`qwen3_moe`/`qwen3_next`/`qwen3_vl`/
`qwen3_vl_moe`/**`qwen3_5`**/**`qwen3_5_moe`**, `recurrent_gemma`, `rwkv7`, `seed_oss`,
`smollm3`, `solar_open`, `stablelm`, `starcoder2`, `step3p5`, `telechat3`, `youtu_llm`.

Shared infrastructure:
- `models/base.py`: `BaseModelArgs.from_dict` (filters unknown keys via `inspect.signature`),
  `create_causal_mask(N, offset, window_size, right_padding, left_padding)`,
  `create_attention_mask(h, cache, window_size, return_array)`, `create_ssm_mask`,
  `scaled_dot_product_attention(queries, keys, values, cache, scale, mask, sinks=None)` which
  dispatches to `quantized_scaled_dot_product_attention` when the cache has `bits`.
  **Quantized SDPA does not support attention sinks**:
  `ValueError("Quantized SDPA does not support attention sinks.")`
- `models/rope_utils.py`: `initialize_rope(dims, base, traditional, scaling_config,
  max_position_embeddings)` plus `SuScaledRoPE`, `Llama3RoPE`, `YarnRoPE`, `ProportionalRoPE`.
- `models/switch_layers.py`: `SwitchLinear`, `QuantizedSwitchLinear`, `SwiGLU`, `SwitchGLU`,
  `SwitchMLP`, `_gather_sort`, `_scatter_unsort`.
- `models/activations.py`: `swiglu(gate, x)` and `xielu`/`XieLU`, both
  `@partial(mx.compile, shapeless=True)`.
- `models/ssm.py` (`ssm_attn`, `ssm_update`), `models/gated_delta.py`
  (`gated_delta_kernel`, `gated_delta_ops`, `gated_delta_update`), `models/mla.py`.
- `models/pipeline.py`: `PipelineMixin` — splits `self.layers` in **reverse** so rank 0 gets the
  *last* layers; non-local layers are set to `None` to keep numbering stable for weight loading.

Model contract (from `llama.py` as the canonical example):
- `ModelArgs(BaseModelArgs)` dataclass with `model_type` and `from_dict`.
- `Model.__call__(inputs, cache=None, input_embeddings=None) -> logits`
- `Model.layers` property
- optional `sanitize(weights) -> weights` (drop `inv_freq`, tied `lm_head.weight`, vision towers…)
- optional `make_cache()` (41 files define it)
- optional `shard(group)` for tensor parallelism (18 files):
  `deepseek_v2, exaone_moe, deepseek_v32, iquestloopcoder, deepseek_v3, llama, longcat_flash,
   ministral3, minimax, glm4_moe, glm4_moe_lite, qwen2, gpt_oss, kimi_k25, qwen3,
   longcat_flash_ngram, qwen3_5, step3p5`
- optional `model.pipeline(group)` / `PipelineMixin` (7 model files):
  `deepseek_v3, glm4_moe_lite, deepseek_v2, deepseek_v32, glm4_moe, qwen3_5, ministral3`
- optional `quant_predicate` property
- optional `cast_predicate(key) -> bool` (used in `convert` to skip casting some params)

Tensor-parallel sharding uses `mlx.nn.layers.distributed.shard_linear(layer, "all-to-sharded" |
"sharded-to-all", group=group)` and divides `n_heads`/`n_kv_heads` by the group size.

`laguna.py` (newest model, added at HEAD) is a good template for 2026-era hybrid designs:
per-layer `layer_types` (`full_attention` / `sliding_attention`), per-layer
`mlp_layer_types` (`dense` / `sparse`), `num_attention_heads_per_layer`, and a **nested
`rope_parameters` schema keyed by layer type** so full-attention layers can use YARN + partial
rotary while sliding layers use default RoPE with full rotary:
```python
rope_params = (args.rope_parameters or {}).get(layer_type) or {}
base = rope_params.get("rope_theta", 10000.0)
partial = rope_params.get("partial_rotary_factor", args.partial_rotary_factor or 1.0)
dims = int(args.head_dim * partial)
```
Defaults: `vocab_size=100352, hidden_size=2048, num_hidden_layers=40,
num_attention_heads=48, num_key_value_heads=8, head_dim=128,
max_position_embeddings=262144, sliding_window=512, num_experts=256,
num_experts_per_tok=8, moe_intermediate_size=512, shared_expert_intermediate_size=512`.
The model is distributed in **nvfp4** (`compressed-tensors` / `nvfp4-pack-quantized`).

---

## 11. Distributed inference & training

### 11.1 `sharded_load` (`utils.py:543-634`)
```python
def sharded_load(repo, pipeline_group=None, tensor_group=None, return_config=False, *,
                 tokenizer_config=None, trust_remote_code=False)
def pipeline_load(repo, return_config=False)   # = sharded_load(repo, mx.distributed.init(), None, ...)
```
- Lazily loads the model **without weights** to discover capabilities:
  `has_pipelining = hasattr(model, "model") and hasattr(model.model, "pipeline")`,
  `has_tensor_parallel = hasattr(model, "shard")`.
- Errors: *"The model does not support pipelining but a pipeline_group was provided"*,
  *"The model does not support tensor parallelism but a tensor_group was provided"*,
  *"The model does not support any sharding"*.
- If neither group is passed it auto-picks tensor parallel when available, else pipelining.
- **Pipelining only downloads the shard's weight files**, using
  `model.safetensors.index.json`'s `weight_map`; if the index is missing it raises
  *"Pipeline loading is only supported for MLX converted models."*
- Ends with a barrier: `mx.eval(mx.distributed.all_sum(mx.array(1.0), stream=mx.cpu))`.

### 11.2 Launching (`mlx_lm/examples/sharded_generate.py`, verbatim header)
```
mlx.launch \
    --backend jaccl \
    --env MLX_METAL_FAST_SYNCH=1 \
    --hostfile /path/to/hosts.json \
    /path/to/sharded_generate.py \
    --prompt 'Hello world'
```
Docs pointer: `https://ml-explore.github.io/mlx/build/html/usage/distributed.html`.
Body:
```python
group = mx.distributed.init()
pipeline_group = group if args.pipeline else None
tensor_group  = group if not args.pipeline else None
model, tokenizer = sharded_load(args.model, pipeline_group, tensor_group)
for response in stream_generate(model, tokenizer, prompt, max_tokens=args.max_tokens):
    rprint(response.text, end="", flush=True)
```
Default model in the example: `mlx-community/Llama-3.3-70B-Instruct-4bit`.

### 11.3 Distributed-aware entry points
`mlx_lm.chat --pipeline`, `mlx_lm.benchmark --pipeline`, `mlx_lm.server --pipeline`,
`mlx_lm.dwq --pipeline`, `mlx_lm.evaluate` (data-parallel request split), `mlx_lm.lora`
(data-parallel via `average_gradients` + rank-strided batches), `mlx_lm.awq`
(`dist_split` of calibration data + `all_sum` losses), `mlx_lm.share`.
`cli_ui.rprint` prints on rank 0 only.

In the server: rank 0 runs the HTTP server, other ranks just `response_generator.join()`:
```python
group = mx.distributed.init()
prompt_cache = LRUPromptCache(model_provider.cli_args.prompt_cache_size)
response_generator = ResponseGenerator(model_provider, prompt_cache)
if group.rank() == 0:
    _run_http_server(host, port, response_generator)
else:
    response_generator.join()
```
Seeds are synchronized: `seed = mx.distributed.all_sum(mx.random.state[0]).view(mx.uint64).item(); mx.random.seed(seed)`.

`tests/model_parallel_tests.py` (run in CI with `mlx.launch -n 2`) asserts
`model.shard()` preserves outputs to `rtol=1e-3, atol=1e-3` for `deepseek_v3`, `llama`
(with mixed `layer_types`), and `glm4_moe_lite`.

---

## 12. Saving / uploading

```python
def save(dst_path, src_path_or_repo, model, tokenizer, config, donate_model: bool = True)
def save_model(save_path, model, *, donate_model: bool = False)
def save_config(config, config_path)
def make_shards(weights: dict, max_file_size_gb: int = 5) -> list
def create_model_card(path, hf_path)
def upload_to_hub(path: str, upload_repo: str)
```
- Shards are `model-{i:05d}-of-{n:05d}.safetensors` (or a single `model.safetensors`), max 5 GB,
  with metadata `{"format": "mlx"}` and an index containing
  `{"metadata": {"total_size", "total_parameters"}, "weight_map": {...}}` (sorted).
- `donate_model=True` replaces params with `mx.array([])` while writing to cap peak memory.
- `save()` also copies `*.py` and `generation_config.json` from the source model dir and calls
  `tokenizer.save_pretrained(dst_path)`.
- `save_config` deletes `_name_or_path` and **`vision_config`**, mirrors `quantization` into
  `quantization_config`, and sorts keys.
- `upload_to_hub` uses `HfApi().upload_large_folder(...)`, sets
  `library_name="mlx"`, `pipeline_tag="text-generation"`, tag `mlx`, and writes a model card
  containing a ready-to-run snippet plus the provenance line
  *"…was converted to MLX format from … using mlx-lm version **{__version__}**."*

GGUF export (`mlx_lm/gguf.py`, 314 lines): `convert_to_gguf(model_path, weights, config,
output_file_path)`, helpers `translate_weight_names`, `permute_weights(weights, n_head,
n_head_kv=None)`, `prepare_metadata(config, vocab)`, `HfVocab`, `TokenType`, `GGMLFileType`.
Only fp16 llama/mistral/mixtral.

---

## 13. Tests as documentation (`tests/`, 13 files)

| File | What it teaches |
|---|---|
| `test_generate.py` (849 ln) | `generate`, `stream_generate`, logits processors, speculative decoding accept pattern, `BatchGenerator` (per-sequence samplers / processors / stop matchers / max_tokens, continued generation from returned caches, sliding-window batching, `max_kv_size`), `batch_generate(return_logprobs=True, return_token_ids=True)` |
| `test_prompt_cache.py` (773 ln) | save/load for every cache class incl. `CacheList`, rotating-cache round-trip after rotation, `trim_prompt_cache` semantics, cache + `generate_step` equivalence |
| `test_server.py` (764 ln) | `TextStateMachine` semantics (buffering, back-to-back tool calls, empty tool_call_end for Mistral, reasoning→tool transitions), full HTTP round trips, `LRUPromptCache` behavior, XTC special tokens |
| `test_models.py` (3298 ln) | Per-architecture smoke tests incl. the new `laguna` config; cache unit tests; `gated_delta`/`ssm` kernels |
| `test_finetune.py` (451 ln) | `linear_to_lora_layers` parameter-count math for llama/gpt_neox, LoRA/DoRA embedding fuse round-trips |
| `test_utils.py` (269 ln) | `load`, `make_shards`, `quantize_model`, `convert`, custom `get_model_classes`, **`TestTrustRemoteCode`** (CVE regression) |
| `test_tuner_trainer.py`, `test_tuner_utils.py`, `test_losses.py`, `test_datsets.py` (sic) | trainer/schedule/dataset internals |
| `test_tokenizers.py`, `test_tool_parsing.py` | detokenizer equivalence, every tool parser against a `multiply(a,b)` sample |
| `test_chat.py`, `test_evaluate.py`, `test_gguf.py`, `test_sample_utils.py` | CLI arg parsing, lm-eval bridge, gguf, sampler math |
| `model_parallel_tests.py` | run via `mlx.launch -n 2` |

Run everything: `python -m unittest discover tests/`.
Fixed test model used almost everywhere: `mlx-community/Qwen1.5-0.5B-Chat-4bit`.

Example of the parameter-count contract asserted in `test_finetune.py`:
```python
params = {"rank": 8, "dropout": 0.0, "scale": 10.0}
nparams = (hidden*2*4 + (intermediate + hidden)*3) * lora_layers      # all linear layers
check_config(params, expected_trainable_parameters=nparams * params["rank"])
params["keys"] = ["lm_head"]
check_config(params, expected_trainable_parameters=rank * (hidden_size + vocab_size))
```

---

## 14. Recent commits worth knowing (last 50, newest first)

```
e5baded Support for Poolside LagunaXS open source coding model in nvfp4 (#1334)   <-- HEAD
cf10f96 fix(sampler): change xtc_threshold default from 0.0 to 0.1 everywhere (#1372)
7661de1 Fix XTC threshold to be per-row for batched logits (#1575)
15b522f Lc/fix xtc special tokens server (#1176)
a790972 Fix broadcast crash in quantized SDPA with GQA + batched padding mask (batch >= 2) (#1467)
86e9b35 Text-based state machine for tool/reasoning parsing (#1501)
4128c00 Fix IncompleteSnapshotError in hf_repo_to_path (#1504)
ab1806e Fix syntax error by removing quotes from NewLineTokenizer (#1465)
2ed2231 Fix deepseek indexer rope argument (#1431)
2c008fd feat: add return_logprobs and return_token_ids to batch_generate (#1359)
c89c93c transformers>=5.7 (#1356)
bfa25a1 Fix CVE-2026-5843: gate model_file execution behind trust_remote_code (#1385)
df48987 fix(sample_utils): correct top_k error message to the exclusive (0, vocab_size) bound (#1377)
39c4019 Fix server 404 on short prompts: clamp negative start in think-token search (#1327)
e476a22 Add Mellum (Mellum 2) model support (#1339)
bdb77da New UI for chat and lora (#1344)
d39cfec fix: add sanitize method to Granite model for tied embeddings (#1298)
04a1910 Fix LFM2 MoE routing to match the HF reference (sigmoid gating) (#1354)
8239c72 Fix gemma4_unified model type not supported (#1349)
fe468f9 Add pipelining for Qwen 3.5 (#1345)
df1d3f3 Fix Gemma 4 sanitize() not stripping KV projections for shared layers (#1240)
ed1fca4 Thread local generation stream (#1090)
4f5cbd2 Fix Gemma 4 KV-shared layers creating unused projections (#1158)
3cd9a52 Fix ArraysCache extend (#1177)
2f1ab85 Fix Mistral empty tool_call_end flipping state machine to normal (#1151)
f3bb10c Fix Gemma4 tool parser: support hyphenated names and braces in strings (#1150)
e1c24b3 fix: handle NoneType check for think tokens in TokenizerWrapper (#1167)
f39cb8e Fix dwq: check for actual safetensors in target_dir (#1173)
a9856b4 Fix batch dimension mismatch in ArraysCache extend() (#1169)
e92138c Apertus tie_word_embeddings fix (#1143)
a401730 Fix missing tree_reduce import in models/cache.py (#1165)
6d11468 Fix MiniMax M2 parallel tool calling (#1171)
aa4f880 Fix parallel tool call handling in server (#1170)
62f38ae Fix batch dimension mismatch in BatchKVCache and BatchRotatingKVCache extend() (#1141)
dcbf6e3 Align batch logits processor token contract (#1115)
f26fddf Gemma4 final fixes and multi-token think/tool start/end (#1114)
f56d997 Fix output corruption in speculative decoding (#1109)
c65c27b Fix Gemma 4 quantized per-layer projection loading (#1112)
3257c3d Add Gemma 4 tool call parser (#1105)
d4eb136 Bring back max-kv-size to the batch generator (#1106)
4469ad4 Add gemma 4 (#1093)
f79dba7 perf: use max instead of argsort in apply_min_p sampling (#1083)
3f9d179 Batch generation refactoring and various fixes (#1072)
9dc023b Fix PromptTrie.pop_prefixes() off-by-one when pruning immediate prefixes (#1078)
9dcefa5 fix: break shared-buffer memory leak in GatedDeltaNet cache (#1077)
bdeac59 Inserting logits processors into BatchGenerator in batch_generate (#1008)
6ddfdda Fix SSM dt clamp default for Nemotron-H (#1026)
4d3af3c Refactor LRUPromptCache (#1019)
d9c63ff Bump the patch version (#1124)
```

### CVE-2026-5843 (commit `bfa25a1`) — the important security change
Previously `config.json`'s `model_file` key caused mlx-lm to `exec` an arbitrary Python file from
the model repo. Now, in `utils.load_model`:
```python
if (model_file := config.get("model_file")) is not None:
    if not trust_remote_code:
        raise ValueError(
            f"The model at {model_path} requires importing and running a "
            f"custom module ({model_file!r}) to build its architecture. This "
            "is disabled by default. Pass trust_remote_code=True if you "
            "trust this model."
        )
    spec = importlib.util.spec_from_file_location("custom_model", model_path / model_file)
    arch = importlib.util.module_from_spec(spec); spec.loader.exec_module(arch)
    model_class, model_args_class = arch.Model, arch.ModelArgs
```
`--trust-remote-code` was added to **every** CLI (benchmark, cache_prompt, chat, convert,
evaluate, fuse, generate, lora, perplexity, awq, dwq, dynamic_quant, gptq, server) and now gates
*both* tokenizer remote code and the model-architecture file. `tests/test_utils.py::
TestTrustRemoteCode` asserts the side-effect file is **not** written by default.

---

## 15. Gotchas, footguns, and inconsistencies

1. **`rich` and `regex` are imported at module level but are not declared dependencies.**
   `import mlx_lm.chat` / `mlx_lm.lora` / anything touching `mlx_lm.tuner` fails with
   `ModuleNotFoundError: No module named 'rich'` on a bare `pip install mlx-lm`; tool parsing
   fails without `regex`.
2. **`python_requires=">=3.8"` is wrong** — `X | None` annotations (awq.py, tool_parsers) and
   `list[tuple[...]]` (cli_ui.py) require ≥ 3.10.
3. **xtc_threshold default is inconsistent.** `generate.py` `DEFAULT_XTC_THRESHOLD = 0.0` but its
   argparse default is `0.1`; `chat.py` still uses `0.0` for both; `make_sampler` defaults to
   `0.1`; the server body default is `0.1`. Setting `xtc_threshold=0` with
   `xtc_probability > 0` makes the XTC mask trivially true for everything above 0 probability.
4. **`top_p` is a no-op unless `0 < top_p < 1.0`**, and `make_sampler`'s own default is `0.0`
   (disabled) while the CLIs pass `1.0` (also disabled). Also, `temp == 0` disables *all*
   filters, including `top_k` and XTC.
5. **`stream_generate(..., max_tokens=0)` raises `UnboundLocalError`** — `generate_step` breaks
   before yielding, so `token`/`n`/`prompt_tps` are never bound before the final
   `yield GenerationResponse(...)`. Use `generate_step` directly (as `cache_prompt.py` does) if
   you only want prefill.
6. **`generate()` returns `None` (not `""`) when the model emits no text** and `verbose=True`.
7. **Speculative decoding requires a trimmable cache.** RotatingKVCache past `max_size`, SSM /
   Mamba / gated-delta (`ArraysCache`) models, and hybrid `CacheList` models with any
   non-trimmable member are rejected. Also `max_kv_size` and `prompt_progress_callback` are
   silently ignored when a draft model is provided.
8. **Draft/target tokenizer mismatch**: `mlx_lm.generate` raises, the server only logs a warning.
9. **Server errors return HTTP 404** with `{"error": ...}` when model loading or tokenization
   fails (`self._set_completion_headers(404)` in `handle_completion`) — not 400/500.
10. **A `seed` in a server request disables batching** (`_is_batchable = is_batchable and
    args.seed is None`) and forces the sequential path; so does loading a draft model
    (`is_batchable = draft_model is None`).
11. **`top_logprobs` sentinel is `-1`** (meaning "off"); values `0..11` are accepted even though
    SERVER.md says 1–10.
12. **Reasoning field name is `reasoning`**, not OpenAI's `reasoning_content` — clients written
    against other servers may not pick it up.
13. **`RotatingKVCache` cannot be quantized**: `NotImplementedError("RotatingKVCache Quantization
    NYI")` — so `--max-kv-size` + `--kv-bits` together will fail once the rotating cache is used
    (the quantize helper only fires on caches with `to_quantized`).
14. **`RotatingKVCache(keep>0)` can't be batched**:
    `ValueError("RotatingKVCache with keep tokens is not supported.")`. Note
    `make_prompt_cache(model, max_kv_size)` creates `keep=4` by default, while `BatchGenerator`'s
    `_make_new_cache` creates `RotatingKVCache(max_size=...)` with `keep=0`.
15. **`mlx_lm.convert` refuses to write into an existing path** — no `--force`/overwrite flag.
16. **`save_config` silently drops `vision_config`** from any config it writes, and mirrors
    `quantization` → `quantization_config`. It is also (re)used for `adapter_config.json`, which
    means adapter configs get the same treatment.
17. **LEARNED_QUANTS.md defaults disagree with the code**: doc says DWQ `--num-samples 1024`,
    `--batch-size 8`, "default is 2048" for max seq length; code says `2048`, `4`, and
    `--max-seq-length 1025`. Doc says AWQ `--num-samples 32`, `--n-grid 10`; code says `128`
    and `20`.
18. **AWQ only supports 7 model types**; everything else raises `NotImplementedError`.
19. **GPTQ bits are restricted to `{2, 4, 8}`** (`assert`), and non-`Linear`/`SwitchLinear`
    layers fall back to `--fallback-bits` (default 6), which raises the effective BPW.
20. **AutoAWQ/GPTQ import path is 4-bit only and rejects `g_idx`**.
21. **Activation quantization only works with `nvfp4`/`mxfp8` weights and bias-free linears.**
22. **`mlx_lm.fuse --hf-path` does not exist** in this version despite LORA.md documenting it.
23. **GGUF export supports only `llama`, `mixtral`, `mistral`** in fp16.
24. **`grad_checkpoint` patches the class `__call__`**, not the instance — global side effect for
    the process.
25. **`lora.run()` overwrites any caller-supplied `training_callback`** with the result of
    `get_reporting_callbacks(...)`, which is `None` when `--report-to` is unset.
26. **Latent `NameError` in `evaluate.py::loglikelihood`**: the `prefix_l == 0` branch calls
    `all_scores.extend(...)` / `all_is_greedy.extend(...)` but those names don't exist in scope
    (the locals are `scores` / `is_greedy`). Triggers only when a completion is longer than the
    context budget.
27. **`utils.py` mutates the process fd limit on import**
    (`resource.setrlimit(RLIMIT_NOFILE, (2048, 4096))`).
28. **Memory wiring requires macOS ≥ 15**; README: *"Models which are large relative to the total
    RAM … `mlx-lm` will attempt to make them faster by wiring the memory occupied by the model
    and cache. This requires macOS 15 or higher to work."* Fix: `sudo sysctl iogpu.wired_limit_mb=N`
    where N > model MB but < machine RAM.
29. **`load_prompt_cache` can only rebuild classes defined in `models/cache.py`**
    (`globals()[class_name]`), so custom caches don't round-trip.
30. **Prompt cache file + `--model` mismatch is a hard error**, and `--kv-bits` /
    `--kv-group-size` must match the saved cache exactly.
31. **`BatchGenerator` mutates the `caches` list you pass to `insert`** (`caches[i] = ...` when
    `None`), and `batch_generate` reuses the same name for input and output caches.
32. **`--allowed-origins` default is the string `"*"`, not a list** (the `type=lambda x:
    x.split(",")` only applies to explicitly provided values). Works only because
    `"*" in "*"` is `True`.
33. **`mlx_lm.benchmark` zeroes the EOS set** (`tokenizer._eos_token_ids = {}`) — don't reuse
    that tokenizer object for real generation.
34. **Deprecation banner**: running `python -m mlx_lm.generate` prints a deprecation notice; the
    supported forms are `mlx_lm.generate ...` and `python -m mlx_lm generate ...`.

---

## 16. Copy-paste quick reference

```bash
# --- Inference ---
mlx_lm.generate --model mlx-community/Qwen3-8B-4bit -p "Explain MoE routing" -m 512 --temp 0.7
mlx_lm.generate --model M --prompt - < long.txt --max-kv-size 4096 --kv-bits 4 --quantized-kv-start 2048
mlx_lm.chat --model mlx-community/Llama-3.2-3B-Instruct-4bit --system-prompt "Be terse."
mlx_lm.server --model M --port 8080 --decode-concurrency 32 --prompt-concurrency 8 \
              --prompt-cache-size 20 --prompt-cache-bytes 8GB --chat-template-args '{"enable_thinking":false}'

# --- Prompt caching to disk ---
cat book.txt | mlx_lm.cache_prompt --model M --prompt - --prompt-cache-file book.safetensors
mlx_lm.generate --prompt-cache-file book.safetensors --prompt "\nSummarize chapter 3."

# --- Conversion / quantization ---
mlx_lm.convert --model org/Model -q                                   # affine 4-bit g64
mlx_lm.convert --model org/Model -q --q-mode nvfp4                    # nvfp4 4-bit g16
mlx_lm.convert --model org/Model -q --q-bits 3 --quant-predicate mixed_3_6
mlx_lm.convert --model org/Model -d --mlx-path model_bf16             # dequantize
mlx_lm.awq  --model org/Model --bits 4 --group-size 64 --num-samples 128 --n-grid 20
mlx_lm.dwq  --model org/Model --bits 4 --group-size 32 --batch-size 1 --max-seq-length 512
mlx_lm.gptq --model org/Model --bits 4 --group-size 64 --fallback-bits 6
mlx_lm.dynamic_quant --model org/Model --target-bpw 4.75 --low-bits 4 --high-bits 5
mlx_lm.upload --path mlx_model --upload-repo mlx-community/Model-4bit-DWQ

# --- Fine-tuning ---
mlx_lm.lora --model org/Model --train --data ./data --iters 600 \
            --fine-tune-type lora --num-layers 16 --batch-size 4 \
            --grad-accumulation-steps 4 --grad-checkpoint --mask-prompt \
            --report-to wandb,swanlab --project-name my-run
mlx_lm.lora --config mlx_lm/examples/lora_config.yaml
mlx_lm.lora --model org/Model --adapter-path adapters --data ./data --test
mlx_lm.generate --model org/Model --adapter-path adapters -p "..."
mlx_lm.fuse --model org/Model --adapter-path adapters --save-path fused_model \
            --upload-repo mlx-community/my-lora

# --- Eval / bench ---
mlx_lm.evaluate --model mlx_model --tasks mmlu_pro --batch-size 16 --limit 200
mlx_lm.perplexity --model mlx_model --num-samples 512 --sequence-length 1024
mlx_lm.benchmark --model mlx_model -p 2048 -g 128 -b 8 -n 5
python -m mlx --version && python -m mlx_lm --version

# --- Model cache mgmt / distribution ---
mlx_lm.manage --scan --pattern mlx-community
mlx_lm.manage --delete --pattern mlx-community/Old-Model
mlx_lm.share --model mlx-community/Llama-3.3-70B-Instruct-4bit --hostfile hosts.json
mlx.launch --backend jaccl --hostfile hosts.json -- mlx_lm.server --model M --pipeline
```

```python
# --- Minimal streaming + custom sampling + logits processing ---
from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler, make_logits_processors

model, tokenizer = load("mlx-community/Qwen3-8B-4bit")
prompt = tokenizer.apply_chat_template([{"role":"user","content":"hi"}], add_generation_prompt=True)

sampler = make_sampler(temp=0.7, top_p=0.95, min_p=0.02, top_k=50,
                       xtc_probability=0.1, xtc_threshold=0.15,
                       xtc_special_tokens=tokenizer.encode("\n") + list(tokenizer.eos_token_ids))
processors = make_logits_processors(logit_bias={128009: -100.0},
                                    repetition_penalty=1.1, repetition_context_size=64)

for r in stream_generate(model, tokenizer, prompt, max_tokens=512,
                         sampler=sampler, logits_processors=processors,
                         kv_bits=4, kv_group_size=64, quantized_kv_start=1024,
                         prefill_step_size=2048,
                         prompt_progress_callback=lambda done, tot: print(f"{done}/{tot}", end="\r")):
    print(r.text, end="", flush=True)
print(f"\n{r.finish_reason} {r.generation_tps:.1f} tok/s, peak {r.peak_memory:.2f} GB")
```

```python
# --- Continuous batching with per-request settings ---
from mlx_lm.generate import BatchGenerator, StopSequenceMatcher
from mlx_lm.sample_utils import make_sampler

gen = BatchGenerator(model, stop_tokens=[[t] for t in tokenizer.eos_token_ids],
                     max_tokens=256, completion_batch_size=32, prefill_batch_size=8,
                     prefill_step_size=2048, max_kv_size=None)
uids = gen.insert(
    [tokenizer.encode(p) for p in prompts],
    max_tokens=[128, 256, 512],
    samplers=[make_sampler(temp=t) for t in (0.0, 0.7, 1.0)],
    stop_matchers=[StopSequenceMatcher([tokenizer.encode("\n\n", add_special_tokens=False)])]*3,
)
out = {u: [] for u in uids}
while responses := gen.next_generated():
    for r in responses:
        if r.finish_reason != "stop":
            out[r.uid].append(r.token)
gen.close()
print([tokenizer.decode(out[u]) for u in uids])
```

---

## 17. Source inventory (every file I actually read this session)

Root:
- `README.md` (283 ln), `setup.py`, `CONTRIBUTING.md`, `MANIFEST.in`, `.pre-commit-config.yaml`
- `.github/workflows/pull_request.yml`, `.github/workflows/release.yml`,
  `.github/actions/setup-macos/action.yml`

`mlx_lm/`:
- `__init__.py`, `_version.py`, `cli.py`, `README.md`
- `generate.py` (2195 ln, read in full)
- `server.py` (1871 ln, read in full)
- `utils.py` (1035 ln, read in full)
- `sample_utils.py` (370 ln), `tokenizer_utils.py` (652 ln), `convert.py` (269 ln)
- `chat.py`, `cache_prompt.py`, `benchmark.py`, `perplexity.py`, `evaluate.py`, `fuse.py`,
  `manage.py`, `upload.py`, `share.py`, `cli_ui.py`
- `LORA.md`, `SERVER.md`, `LEARNED_QUANTS.md`, `MANAGE.md`, `BENCHMARKS.md`
- `models/cache.py` (1764 ln, read in full), `models/base.py`, `models/pipeline.py`,
  `models/llama.py`, `models/activations.py`; greps over all 121 `models/*.py`
  (`shard`, `pipeline`, `make_cache`, `quant_predicate`), `models/laguna.py` (via `git show`)
- `quant/awq.py` (595 ln), `quant/dwq.py` (428 ln), `quant/gptq.py` (239 ln),
  `quant/dynamic_quant.py` (268 ln), `quant/utils.py`
- `tuner/utils.py`, `tuner/trainer.py`, `tuner/lora.py`, `tuner/dora.py`, `tuner/datasets.py`,
  `tuner/callbacks.py`, `tuner/__init__.py`, `tuner/losses.py` (function list only)
- `tool_parsers/{json_tools,pythonic,mistral,qwen3_coder,gemma4,kimi_k2}.py`
  (others surveyed via `_infer_tool_parser` + `tests/test_tool_parsing.py`)
- `examples/{generate_response,batch_generate_response,chat,tool_use,openai_tool_use,
  openai_reasoning_content,sharded_generate}.py`, `examples/lora_config.yaml`,
  `examples/merge_config.yaml`

`tests/`:
- `test_generate.py` (full), `test_server.py` (full), `test_utils.py` (full),
  `test_prompt_cache.py` (first 300 ln), `test_finetune.py` (first 200 ln),
  `test_models.py` (head + laguna case), `test_chat.py` (head), `test_tool_parsing.py` (head),
  `model_parallel_tests.py` (full)

`benchmarks/server_benchmark.py` (349 ln, full)

Git: `git log --oneline -50`, `git show e5baded --stat`, `git show e5baded -- mlx_lm/models/laguna.py`,
`git show bfa25a1`, `git show c89c93c --stat`.

---

## 18. Open questions / unverified

- The clone is `--depth 50`; anything about the history before commit `4d3af3c` is unknown here.
- I did **not** execute any code (no MLX runtime available/attempted), so all behavior is read
  from source, not observed. Perf numbers come solely from `BENCHMARKS.md`.
- The exact `mlx` 0.31.x APIs used (`mx.new_thread_local_stream`, `nn.QQLinear`,
  `nn.quantize(..., mode=...)`, `mx.quantize(..., mode=)`, `shard_linear`,
  `mlx._distributed_utils.launch.launch_jaccl`, `mx.depends`, `mx.contiguous`,
  `mx.linalg.cholesky_inv`, `optim.Muon`) are **assumed to exist in mlx ≥ 0.31.2** — verify
  against the mlx repo/docs; they are not defined in mlx-lm.
- `nvfp4` semantics (group_size 16, 4-bit, FP4 with FP8 scales) live in mlx core, not here;
  mlx-lm only selects the mode. The exact numeric format is UNVERIFIED from this repo.
- Whether `rich`/`regex` are shipped as dependencies in the published PyPI wheel (setup.py here
  omits them) — UNVERIFIED; may be a packaging bug at this commit.
- `mlx_lm.share` hostfile schema (`Hostfile.from_file`, fields `backend`, `hosts`, `envs`) comes
  from `mlx._distributed_utils.common` — schema not documented in this repo.
- `LORA.md`'s `--hf-path` for `mlx_lm.fuse` and the model-family list appear stale; whether they
  were removed intentionally is unknown.
- `tests/test_models.py` is 3298 lines; I sampled it rather than reading it end to end, so some
  per-architecture config details are not captured.
- `mlx_lm/tuner/losses.py` Metal kernel source (798 lines) was only surveyed by function name.
- `chat_templates/deepseek_v32.py` contents not read (only its wiring via
  `tokenizer_config["chat_template_type"]`).
