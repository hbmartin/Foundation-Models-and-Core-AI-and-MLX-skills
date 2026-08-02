# apple/coreai-models — deep dive notes

**Repo path (local clone, `--depth 50`):** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models`
**Upstream:** `https://github.com/apple/coreai-models`
**License:** BSD-3-Clause. All source headers say `Copyright 2026 Apple Inc.`
**HEAD at time of reading:** `5ed9981 Move away from deprecated FM API (#123)` (authored **2026-07-23**), on `main`.
**Contribution policy (README.md:129-135):** "**We are not accepting code contributions at this time** … If you open a pull request, it will be closed." Issues (bug report / model request / workflow feedback templates) are open.

Everything below was read from the actual files in this session. Line numbers are from the local checkout.

---

## 1. What this repo is

From `README.md:1-16`:

> # Core AI Models
> Model export recipes, Python primitives, and Swift runtime utilities for building on-device AI with [Core AI](https://developer.apple.com/documentation/coreai).

| Directory | What's inside |
| --------- | ------------- |
| `models/` | Model catalog with README and export recipes. |
| `python/` | Python primitives for authoring and utilities for exporting models. |
| `swift/`  | Swift package (`coreai-models`): runtime utilities to integrate Core AI models in your app. |
| `skills/` | Pluggable skills that enable coding agents to leverage Core AI more effectively. |

**Requirements (README.md:32-42):**
- **macOS and iOS 27.0+**
- **Xcode 27.0+**
- Models are exported as standalone **`.aimodel`** files (a *directory*, not a single file — see §6). Compiled variant is **`.aimodelc`**.
- Models needing extra resources (tokenizer, multi-component pipelines) are shipped as a **bundle directory** containing one or more `.aimodel` plus `tokenizer/` plus `metadata.json`.

Repo size: 388 tracked files; ~35.7k lines of Swift, ~39.1k lines of Python/Markdown/JSON/YAML.

---

## 2. THE "deprecated FM API" commit (#123) — answer to the assignment question

`git show 5ed9981` — commit **"Move away from deprecated FM API (#123)"**, author `tjia1818`, 2026-07-23. Two-line change across two files:

```diff
--- a/swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift
+++ b/swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift
@@ -61,7 +61,7 @@ public struct CoreAILanguageModel: LanguageModel {
         if isGuidedGenerationSupported { caps.append(.guidedGeneration) }
-        return LanguageModelCapabilities(capabilities: caps)
+        return LanguageModelCapabilities(caps)
```
```diff
--- a/swift/Sources/CoreAILanguageModels/VLM/CoreAIVisionLanguageModel.swift
+++ b/swift/Sources/CoreAILanguageModels/VLM/CoreAIVisionLanguageModel.swift
@@ -29,7 +29,7 @@ public struct CoreAIVisionLanguageModel: LanguageModel {
     public var capabilities: LanguageModelCapabilities {
-        LanguageModelCapabilities(capabilities: [.vision])
+        LanguageModelCapabilities([.vision])
```

**Deprecated API:** `FoundationModels.LanguageModelCapabilities.init(capabilities:)` (labeled argument).
**Replacement:** `LanguageModelCapabilities.init(_:)` — unlabeled, takes `[LanguageModelCapabilities.Capability]`.

Capability cases observed in use: `.toolCalling`, `.reasoning`, `.guidedGeneration`, `.vision`.

Related nearby API-churn commit `102f832` ("Polish a few APIs, method names, and remove unnecessarily vending public extension (#122)"), same day:
- `CoreAIRunner.init(from bundle:)` → `CoreAIRunner.init(bundle:)`
- `PerformanceMetrics.setPromptTokenCount(_:)` → `recordPromptTokens(_:)`; `setGeneratedTokenCount(_:)` → `recordGeneratedTokens(_:)`; `getGeneratedTokenCount` → `generatedTokenCount` (`public private(set) var`); `totalTokenCount` became a computed `promptTokenCount + generatedTokenCount`.
- `CLILogger.setLevel(to:)` removed → `CLILogger.level` is now a settable `public static var`.
- `Duration.inSeconds` / `.inMilliseconds` were **un-published** (made internal) with the rationale: *"vending members on a standard-library type we don't own would pollute `Duration`'s API surface for every client of this library."*

---

## 3. Swift package (`Package.swift`)

`swift-tools-version: 6.0`, `swiftLanguageModes: [.v6]`, `cxxLanguageStandard: .cxx17`.
`platforms: [.macOS("27.0"), .iOS("27.0")]`.

### Products
| Product | Target |
| --- | --- |
| `CoreAILM` | `CoreAILanguageModels` |
| `CoreAIDiffusion` | `CoreAIDiffusionPipeline` |
| `CoreAISegmentation` | `CoreAIImageSegmenter` |
| `CoreAISpeech` | `CoreAISpeech` |
| `CoreAIObjectDetection` | `CoreAIObjectDetector` |

`.spi.yml` documents these 4 doc targets: `CoreAILM`, `CoreAIDiffusion`, `CoreAISegmentation`, `CoreAIObjectDetection`.

### Dependencies (Package.swift:43-47, pins from Package.resolved)
```swift
.package(url: "https://github.com/apple/swift-argument-parser", from: "1.2.0"),      // pinned 1.7.0
.package(url: "https://github.com/huggingface/swift-transformers", from: "1.1.0"),   // pinned 1.2.0
.package(url: "https://github.com/mlc-ai/xgrammar", branch: "main"),                 // rev 4d145cc1…
```
Transitive pins in `Package.resolved`: `swift-huggingface 0.9.0`, `swift-jinja 2.3.2`, `swift-nio 2.96.0`, `swift-collections 1.4.1`, `swift-crypto 4.3.0`, `swift-atomics 1.3.0`, `swift-asn1 1.6.0`, `swift-system 1.6.4`, `EventSource 1.4.1`, `yyjson 0.12.0`.

Note: `xgrammar` is tracked on **branch `main`** (unpinned semver) — a reproducibility footgun. Commit `277238e` "Remove notice file as we have adopted upstream Swift package for xgrammar (#45)".

### Targets & special settings
- Every target sets `.enableUpcomingFeature("MemberImportVisibility")`.
- `CoreAILanguageModels` additionally: `.define("CXGRAMMAR_IMPORT")`, `linkerSettings: [.linkedLibrary("c++")]`, depends on `CoreAIShared`, `CXGrammar`, `Transformers`.
- `CXGrammar` is a C/C++ bridge target at `swift/Sources/lib/CXGrammar` with `publicHeadersPath: "include"` (files: `xgrammar_c_bridge.h/.cpp`, `dlpack/dlpack.h`, `module.modulemap`).
- Executable targets: `llm-runner`, `image-segmenter`, `object-detector`, `diffusion-runner`, `speech-runner`, `llm-benchmark` ("Public LLM Benchmark CLI (based on mlx-lm benchmark)").
- Test targets: `LanguageModelsTests` (resources: `.copy("Resources/MinimalTokenizer")`, links `c++`), `ImageSegmenterTests`, `DiffusionPipelineTests`, `ObjectDetectorTests`, `CoreAISharedTests`, `GuidedGenerationTests` (links `c++`), plus a shared `TestUtilities` target.

---

## 4. Python package (`python/pyproject.toml`, root `pyproject.toml`)

Root `pyproject.toml` is a **uv workspace** with member `python`:
```toml
[tool.uv]
index-url = "https://pypi.org/simple"
prerelease = "allow"
index-strategy = "unsafe-best-match"
keyring-provider = "subprocess"
default-groups = ["dev"]
required-version = ">=0.9.0"
```
Dev groups: `test` = pytest 8.4.0, pytest-asyncio 0.24.0, pytest-cov 7.1.0, pytest-rerunfailures 15.1, pytest-xdist 3.6.1; `lint` = ruff 0.15.12, mypy 1.14.1.

`.python-version` = `3.11`. Package `requires-python = ">=3.11"` (but ruff `target-version = "py310"` and mypy `python_version = "3.10"` — inconsistent).

### Runtime dependency pins (`python/pyproject.toml:28-43`)
```toml
"accelerate>=1.12,<2.0",
"coreai-core==1.0.0b2",
"coreai-torch==0.4.1",
"coreai-opt==0.2.1",
"torch==2.9.0",
"numpy>=2.2,<3.0",
"tqdm>=4.67,<5.0",
"rich>=14.0,<15.0",
"transformers>=4.57,<5.0",
"huggingface-hub>=0.34,<1.0",
"safetensors>=0.5,<1.0",
"sentencepiece>=0.2,<1.0",
"tokenizers>=0.22,<1.0",
"diffusers>=0.37,<1.0",
```
Confirmed in `uv.lock`: `coreai-core 1.0.0b2` (**beta**), `coreai-opt 0.2.1`, `coreai-torch 0.4.1` (depends on `coreai-core`, `ml-dtypes`, `networkx`, `numpy`).

### Console scripts (`[project.scripts]`)
```
"coreai.llm.export"       = "coreai_models.llm.export:main"
"coreai.llm.eval"         = "coreai_models.llm.eval:main"
"coreai.vlm.export"       = "coreai_models.vlm.export:main"
"coreai.diffusion.export" = "coreai_models.diffusion.export:main"
"coreai.model.registry"   = "coreai_models.model_registry:main"
```
All are invoked as `uv run <script> …` in the docs.

**GOTCHA:** `coreai.llm.eval` is a **stub**. `python/src/coreai_models/llm/eval.py:26-31` — `main()` always calls `parser.error("Evaluation support is coming soon. See models/README.md for current capabilities.")`. The declared flags (`--model`, `--tasks`) do nothing.

### CI (`.github/workflows/ci.yml`)
Runs on `[self-hosted, macos, tahoe, ARM64]` (Apple Silicon, macOS "Tahoe"), `if: github.repository == 'apple/coreai-models'`.
Jobs: `lint` (`ruff check` + `ruff format --check` on `python/src/ python/tests/`), `swift-format` (`swift format lint --strict --recursive swift/Sources/ swift/Tests/`, `DEVELOPER_DIR=/Applications/Xcode-latest.app/Contents/Developer`), `python-test` (`uv run pytest python/tests/test_model_units -x -q`).
Note: only `test_model_units` runs in CI; `test_model_conversion` (the heavy HF-download tests) is **not** in CI.

`.pre-commit-config.yaml` pins ruff 0.15.12, `uv-lock` hook 0.9.26, and local `swift-format` format/lint hooks. Install with `pre-commit install --hook-type pre-commit --hook-type pre-push`.

---

## 5. Supported models (authoritative tables)

### 5.1 LLM presets — `python/src/coreai_models/model_registry.py:73-167`
`ModelPreset(short_name, hf_id, family, type, variant, compression, compute_precision, max_context_length, experimental=False, notes=None, compression_config=None)`

**macOS variants** (all `compression="4bit"` unless noted):
| short_name | hf_id | family | precision | max_ctx |
|---|---|---|---|---|
| `qwen2.5-1.5b-instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | qwen2.5 | float16 | 32768 |
| `qwen3-0.6b` | `Qwen/Qwen3-0.6B` | qwen3 | float16 | 8192 |
| `qwen3-4b` | `Qwen/Qwen3-4B` | qwen3 | float16 | 40960 |
| `qwen3-8b` | `Qwen/Qwen3-8B` | qwen3 | float16 | 40960 |
| `qwen3-coder-30b-a3b-instruct` | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | qwen3 | float16 | 262144 |
| `gemma3-4b-it` | `google/gemma-3-4b-it` | gemma3 | **bfloat16** | 131072 |
| `gemma3-12b-it` | `google/gemma-3-12b-it` | gemma3 | **bfloat16** | 131072 |
| `mistral-7b-instruct-v0.3` | `mistralai/Mistral-7B-Instruct-v0.3` | mistral | float16 | 8192 |
| `mixtral-8x7b-instruct-v0.1` | `mistralai/Mixtral-8x7B-Instruct-v0.1` | mixtral | float16 | 32768 |
| `gpt-oss-20b` | `openai/gpt-oss-20b` | gpt-oss | **bfloat16**, compression **`none`** | 32768 |

**iOS variants** (`IOS_DEFAULT_MAX_CONTEXT_LENGTH = 4096`):
| short_name | hf_id | compression | notes |
|---|---|---|---|
| `qwen3-0.6b` | `Qwen/Qwen3-0.6B` | `none` + `compression_config="models/qwen3/qwen3_0_6b_mixed_4bit_8bit.yaml"` | float16, ctx 4096 |
| `qwen2.5-1.5b-instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | `4bit_weight_palettized_group8` | float16, ctx 4096 |
| `qwen3-4b` | `Qwen/Qwen3-4B` | `none` + `compression_config="models/qwen3/qwen3_4b_mixed_4bit_8bit.yaml"` | float16, ctx 4096 |

### 5.2 Diffusion presets — `model_registry.py:173-215`
| short_name | hf_id | family | compression | precision |
|---|---|---|---|---|
| `sd-1.5` | `runwayml/stable-diffusion-v1-5` | stable-diffusion | none | float16 |
| `sd-2.1` | `sd2-community/stable-diffusion-2-1` | stable-diffusion | none | float16 |
| `sd-3.5-medium` | `stabilityai/stable-diffusion-3.5-medium` | stable-diffusion-3 | none | float16 |
| `flux2-klein-4b` | `black-forest-labs/FLUX.2-klein-4B` | flux2 | **4bit** | float16 — notes: *"4bit recommended; use --compression none for full precision"* |

### 5.3 Utility models (standalone `export.py` scripts) — `model_registry.py:221-343`
`UtilityModel(short_name, hf_id, model_type, task, export_script, platforms=("iOS","macOS"), notes=None)`

| short_name | hf_id | type | task | script |
|---|---|---|---|---|
| `clip-vit-b32` | `openai/clip-vit-base-patch32` | clip | embedding | `models/clip/export.py` |
| `clap-htsat` | `laion/clap-htsat-unfused` | clap | embedding | `models/clap/export.py` |
| `whisper-large-v3-turbo` | `openai/whisper-large-v3-turbo` | whisper | asr | `models/whisper/export.py` |
| `whisper-large-v3` | `openai/whisper-large-v3` | whisper | asr | `models/whisper/export.py` |
| `wav2vec2-base` | `wav2vec2_asr_base_960h` | wav2vec2 | asr | `models/wav2vec2/export.py` |
| `yolos-base` | `hustvl/yolos-base` | yolo | detection | `models/yolo/export.py` |
| `yolos-tiny` | `hustvl/yolos-tiny` | yolo | detection | `models/yolo/export.py` |
| `efficient-sam-vitt` | `efficient_sam_vitt` | efficient-sam | segmentation | `models/efficient-sam/export.py` |
| `sam3` | `facebook/sam3` | sam3 | segmentation | `models/sam3/export.py` |
| `depth-anything-3-small` | `depth-anything/da3-small` | depth-anything | depth | `models/depth-anything/export.py` (**platforms=("macOS",) only**) |
| `edsr-x2` | `edsr_r16f64_x2` | edsr | super-resolution | `models/edsr/export.py` |
| `roberta-base` | `roberta-base` | roberta | encoding | `models/roberta/export.py` |
| `t5-small` / `t5-base` / `t5-large` | `google-t5/t5-*` | t5 | encoding | `models/t5/export.py` |
| `pvt-v2-b0` | `pvt_v2_b0` | pvt | classification | `models/pvt/export.py` |

### 5.4 VLM — `python/src/coreai_models/vlm/export.py:76-90`
Only `qwen3-vl` → `Qwen/Qwen3-VL-2B-Instruct`, output_name `qwen3_vl_2b`:
```python
VLMSpec(
    short_name="qwen3-vl",
    hf_model_id="Qwen/Qwen3-VL-2B-Instruct",
    output_name="qwen3_vl_2b",
    image_token_id=151655,  # <|image_pad|>
    image_size=448, patch_size=16, spatial_merge_size=2, temporal_patch_size=2,
    image_mean=(0.5, 0.5, 0.5), image_std=(0.5, 0.5, 0.5), rescale_factor=1.0,
    image_strategy="stretch", include_image_info=True,
)
```
`num_visual_tokens = (image_size // patch_size // spatial_merge_size) ** 2` → `(448/16/2)**2 = 196`.
Commit `ace0dc6` "Fix Qwen3-VL normalization: use 0.5/0.5/0.5 from checkpoint" — i.e. **not** CLIP mean/std for this model.

### 5.5 PyTorch model-class registry — `python/src/coreai_models/models/registry.py`
```python
@dataclass
class ModelEntry:
    macos_class: type[nn.Module] | None = None
    ios_class: type[nn.Module] | None = None
    hf_config_attr: str | None = None        # e.g. "text_config" for Gemma-3
    hf_state_dict_prefix: str = ""           # e.g. "language_model." for Gemma-3
```
| HF `model_type` | macOS class | iOS class | hf_config_attr | state-dict prefix |
|---|---|---|---|---|
| `gemma3_text` | `Gemma3ForCausalLM` | — | `text_config` | `language_model.` |
| `gpt_oss` | `GptOssForCausalLM` | — | | |
| `mistral` | `MistralForCausalLM` | `MistralForCausalLMForiOS` | | |
| `mixtral` | `MixtralForCausalLM` | — | | |
| `qwen2` | `Qwen2ForCausalLM` | `Qwen2ForCausalLMForiOS` | | |
| `qwen3` | `Qwen3ForCausalLM` | `Qwen3ForCausalLMForiOS` | | |
| `qwen3_moe` | `Qwen3MoeForCausalLM` | — | | |
| `qwen3_vl` | `Qwen3VLForCausalLM` | — | `text_config` | `model.language_model.` |

`MODEL_TYPE_REMAPPING = {"gemma3": "gemma3_text", "qwen2_5": "qwen2"}`.
**iOS is only supported for `mistral`, `qwen2`, `qwen3`.** `export_model` raises `ValueError(f"Model '{model_type}' does not support iOS variant")` otherwise (`pipeline.py:149-150`).

### 5.6 Diffusion families — `python/src/coreai_models/diffusion/models.py`
```python
SUPPORTED_MODELS: list[tuple[str, str, str]] = [
    ("stable-diffusion-1.x", "runwayml/stable-diffusion-v1-5", "sd"),
    ("stable-diffusion-2.x", "sd2-community/stable-diffusion-2-1", "sd"),
    ("stable-diffusion-3.x", "stabilityai/stable-diffusion-3.5-medium", "sd3"),
    ("flux2", "black-forest-labs/FLUX.2-klein-4B", "flux2"),
]
```

---

## 6. Bundle format — `metadata.json` schema **0.2**

Defined by `swift/Sources/CoreAIShared/Bundle/ModelBundle.swift` (reader) and `python/src/coreai_models/export/bundle.py` (writer).

### Writer (`bundle.py:42-74`) — exact JSON emitted for LLMs
```python
METADATA_VERSION = "0.2"
metadata = {
    "metadata_version": "0.2",
    "kind": "llm",
    "name": name,
    "assets": {"main": f"{name}.aimodel"},
    "language": {
        "tokenizer": hf_model_id,
        "vocab_size": hf_config.vocab_size,
        "max_context_length": hf_config.max_position_embeddings,
        "embedded_tokenizer": True,
        "function_map": {"main": ["main"]},
    },
    "source": {"model_definition": "torch", "hf_model_id": hf_model_id},
    "compression": compression if compression != "none" else None,
    "compilation": {"date": datetime.now().astimezone().isoformat(), "targets": []},
}
```
`bundle_llm_asset()` also writes `tokenizer/` via `AutoTokenizer.from_pretrained(hf_model_id).save_pretrained(bundle_path/"tokenizer")`.

### Reader — `BundleKind` (`BundleKind.swift`)
```swift
public enum BundleKind: String, Codable, Sendable, CaseIterable {
    case llm; case vlm; case diffusion; case segmenter
}
```

### `ModelBundle` (CoreAIShared)
```swift
public struct ModelBundle: Sendable {
    public let metadataVersion: String
    public let kind: BundleKind
    public let name: String
    public let bundlePath: URL
    public let userData: [String: String]?
    public let assets: [String: String]      // role -> filename
    public let raw: Data                     // full metadata.json bytes, preserved
    public enum ComponentKey { static let main = "main"; static let vision = "vision"; static let embedding = "embedding" }
    public var componentKeys: [String] { assets.keys.sorted() }
    public func modelURL(for key: String) -> URL?
    public func requireModelURL(for key: String) throws -> URL
    public func verify() throws          // checks every declared asset exists on disk
    public init(from path: String) throws        // tilde-expanded
    public init(at url: URL) throws
    public init(raw: Data, bundlePath: URL) throws
}
```
Errors (`ModelBundle.BundleError`): `.missingMetadata(URL)`, `.malformedMetadata(URL, underlying:)`, `.unsupportedVersion(String)`, `.kindMismatch(expected:got:)`, `.missingField(String)`, `.missingAsset(key:path:)`, `.pointedAtModelAsset(URL)`.

**Two important footguns encoded in the reader:**
1. Passing a `.aimodel`/`.aimodelc` path where a bundle *directory* is expected throws `.pointedAtModelAsset` **before any filesystem read**, because *"a compiled `.aimodelc` is itself a directory holding its own unrelated metadata.json, which would otherwise parse as a bogus 0.1 bundle and surface a misleading 'unsupported metadata_version' error"* (`ModelBundle.swift:122-131`). Commit `d5804c8` added this.
2. `metadata_version` defaults to `"0.1"` when absent, and **anything other than `"0.2"` throws** `.unsupportedVersion` (`ModelBundle.swift:158-161`). Error text: `"unsupported metadata_version '\(v)' (known: 0.2)"`.
3. `.missingAsset` message tells you exactly what to do after AOT compilation:
   > "If you compiled this model with `xcrun coreai-build compile`, update metadata.json "assets" to reference the compiled filename (e.g. modelName.architectureName.aimodelc). See models/README.md#compiled-models"

### `LanguageConfig` — the `language` block (schema 0.2)
`swift/Sources/CoreAILanguageModels/Bundle/LanguageConfig.swift`
```swift
public struct LanguageConfig: Codable, Sendable, Equatable {
    public let tokenizer: String            // "tokenizer"
    public let vocabSize: Int               // "vocab_size"
    public let maxContextLength: Int        // "max_context_length"
    public let embeddedTokenizer: Bool      // "embedded_tokenizer", default true
    public let functionMap: FunctionMap?    // "function_map"
    public let vision: VisionConfig?        // "vision"
}
```
`FunctionMap` (`CoreAIShared/Bundle/FunctionMap.swift`) is `[String: [String]]` role → physical function names, always array-valued. `name(for:)` returns the first. Used for chunked-static (ANE) models with several `extend_<N>` functions.

### `VisionConfig` — the `vision` block (VLM bundles)
```swift
public struct VisionConfig: Codable, Sendable, Equatable {
    public let imageSize: Int          // "image_size"
    public let patchSize: Int          // "patch_size"
    public let imageTokenCount: Int    // "image_token_count"
    public let imageTokenId: Int32     // "image_token_id"
    public let imageMean: [Double]     // "image_mean",  default VisionConfig.clipMean
    public let imageStd: [Double]      // "image_std",   default VisionConfig.clipStd
    public let rescaleFactor: Double   // "rescale_factor", default 1.0
    public let imageStrategy: ImageStrategy // "image_strategy", default .stretch
    public let includeImageInfo: Bool  // "include_image_info", default false

    public static let clipMean = [0.48145466, 0.4578275, 0.40821073]
    public static let clipStd  = [0.26862954, 0.26130258, 0.27577711]
}
```

### `LanguageBundle` (strict LLM/VLM loader)
```swift
public struct LanguageBundle: Sendable {
    public let bundle: ModelBundle
    public let modelAssetPath: String      // assets.main
    public let language: LanguageConfig
    public let visionConfig: VisionConfig?
    public init(from path: String) throws
    public init(at url: URL) throws
    public init(bundle: ModelBundle) throws  // requires kind == .llm || .vlm
    public var tokenizerPath: URL?          // bundlePath/"tokenizer" iff embeddedTokenizer && tokenizer.json exists
    public var hasEmbeddedTokenizer: Bool
    public func loadTokenizer() async throws -> any Tokenizer  // AutoTokenizer.from(modelFolder:) else .from(pretrained:)
}
```
`LanguageBundle(bundle:)` throws `.kindMismatch` if kind isn't llm/vlm, `.missingField("assets.main")`, `.missingField("language")`, and (for vlm) `.missingField("vision")`.

### VLM bundle layout (`models/vlm/README.md:29-39`)

> ⚠️ **STALE as of upstream `86b4c04` (2026-07-28), checked 2026-08-02.** The commit
> *"Remove Deprecated LLMAsset Terminology"* **drops the `.llmasset` extension**: VLM export now
> writes `<name>/`, not `<name>.llmasset/` (`python/src/coreai_models/vlm/export.py` —
> `bundle_path = output_dir / output_name`, previously `output_dir / (output_name + ".llmasset")`).
> The layout *inside* the directory is unchanged. Anything globbing `*.llmasset` breaks against a
> current clone. Left below as read at `5ed9981`.

Historical layout at `5ed9981`: directory `<name>.llmasset/` with `kind=vlm`:
| Asset role | File | Role |
|---|---|---|
| `main` | `<name>.aimodel` | Text decoder (`inputs_embeds`, stateful KV) |
| `embedding` | `embed.aimodel` | Token-embedding lookup (`input_ids → embeds`) |
| `vision` | `vision.aimodel` | Vision encoder (`pixel_values → image_features`) |
| — | `tokenizer/` | Embedded HF tokenizer |

---

## 7. Export pipeline (Python) — end to end

### 7.1 `coreai.llm.export` CLI (`python/src/coreai_models/llm/export.py`)
Full flag list from `build_parser()`:
```
model                              positional; registry short-name OR HuggingFace id (org/model)
--platform {macOS,iOS}             default None → macOS (or registry preset's variant)
--compression NAME                 mutually exclusive with --compression-config
--compression-config PATH          coreai-opt YAML; top key must be 'kmeans_palettization_config' (iOS)
                                   or 'quantization_config' (macOS)
--max-context-length INT
--compute-precision {float16,bfloat16,float32}   REQUIRED for raw HF ids
--output-dir DIR                   default <repo-root>/exports/
--output-name NAME                 without extension
--num-layers INT                   truncate to N layers (debugging)
--list-presets
--list-models
--dry-run
--verbose / -v
--overwrite
--experimental                     allow HF ids with no registry preset; requires --compute-precision
--disable-embedding-quantization-ios   iOS only; keeps embedding in float32
```

Key resolution rules (`_resolve_export_config`, export.py:263-368):
- Non-HF-id (no `/`) must resolve in the registry, else `SystemExit`. If it exists for another platform: *"Error: '<m>' is not available for <platform>. Run --list-models to see options."*
- HF id with no preset and no `--experimental` → SystemExit with hint; when `--platform iOS`, extra hint *"This model may not be suitable for iOS application due to its memory requirements."*
- `--compute-precision` missing and no preset → SystemExit.
- `--disable-embedding-quantization-ios` with non-iOS platform → SystemExit.
- Preset mismatch guards raise `RuntimeError("macOS quantization preset provided, but platform is iOS.")` / `("iOS palettization preset provided, but platform is macOS.")`.

YAML loader (`_load_compression_config_object`, export.py:163-237):
- YAML must be a mapping with **exactly one** coreai-opt top-level key after popping an optional `coreai_models:` block.
- `coreai_models:` block allows only `{"calibrate_activations"}`; unknown keys → SystemExit.
- `kmeans_palettization_config` ⇒ requires `--platform iOS`, does **not** support the `coreai_models` block; parsed with `KMeansPalettizerConfig.from_dict({top_key: inner})`.
- `quantization_config` ⇒ requires `--platform macOS`; validated with `QuantizerConfig.from_dict(...)`, then `calibrate_activations` is re-inlined into the returned dict.
- Registry-referenced YAMLs live in the **source tree only** — `_resolve_registry_compression_config` raises SystemExit when running from a wheel: *"Registry preset references <path>, but the YAML lives in the source tree which is unavailable in this install."*

### 7.2 Compression presets (`python/src/coreai_models/export/presets.py`)
```python
DEFAULT_MACOS_COMPRESSION_PRESET = "4bit"
DEFAULT_IOS_COMPRESSION_PRESET   = "4bit_weight_palettized_group32"
```
**macOS** `MACOS_PRESETS`: `"none"`, `"4bit"`.
`4bit` = `torch_quantization_config`:
```python
{"execution_mode": "eager",
 "global_config": {"op_state_spec": {"weight": {"dtype": "int4",
        "qscheme": "symmetric_with_clipping",
        "granularity": {"type": "per_block", "block_size": 32, "axis": 1}}},
   "op_input_spec": None, "op_output_spec": None},
 "module_type_configs": _TORCH_MODULE_CONFIGS_4BIT}
```
Excluded module types (`_TORCH_MODULE_EXCLUSIONS`) — mapped to `None` (skip):
```
coreai_models.primitives.macos.sdpa.SDPA
coreai_models.primitives.macos.rope.RoPE
coreai_models.primitives.macos.rms_norm.RMSNorm
coreai_models.primitives.macos.rms_norm.RMSNormPlusOne
```
MoE override `_TORCH_MOE_SWITCH_LINEAR_4BIT` for `coreai_models.primitives.macos.switch.SwitchLinear`:
```python
{"module_state_spec": {"weight": {"dtype": "int4",
    "qscheme": "symmetric_with_clipping",
    "granularity": {"type": "per_block", "block_size": [1, 1, 1, 32], "axis": None}}},
 "op_input_spec": None, "op_output_spec": None}
```
> Comment: expert weight is 4-D `[num_weight_sets, num_experts, output_dims, input_dims]` which the global 2-D `per_block/32/axis=1` spec can't express. Safe on non-MoE models (no `SwitchLinear` instances → no-op).

**iOS** `IOS_PRESETS`: `"none"`, `"4bit_weight_palettized_group8"`, `"4bit_weight_palettized_group32"`.
Both palettization presets: `{"n_bits": 4, "granularity": {"type": "per_grouped_channel", "axis": 0, "group_size": 8 or 32}}`, with embedding modules excluded:
```
torch.nn.modules.sparse.Embedding
coreai_models.primitives.ios.embedding.LoadEmbeddings
```
README note (`models/README.md:54`): **"All `iOS` palettization presets quantize the Embedding to 8-bit per tensor by default."** (via `quantize_per_tensor`, `primitives/ios/quantization.py`; symmetric, `nbits=8` only, `scale = max|x| / 127`, clamped min `1e-6`).

**Diffusion** `diffusion/presets.py`: `DEFAULT_COMPRESSION_PRESET = "none"`; `"4bit"` = `{"type": "int4", "symmetric": True, "granularity": "per_block", "block_size": 32}`. *"The VAE encoder/decoder is small and quality-sensitive, so it is never quantized."*

### 7.3 Export constants (`export/_constants.py`) — verbatim
```python
KEY_CACHE_NAME = "keyCache"
VALUE_CACHE_NAME = "valueCache"
TRACE_KV_CACHE_SEQ_LEN = 2048     # trace-time only; runtime cache size is dynamic
QUANT_TRACE_QUERY_LEN = 16
QUANT_TRACE_OFFSET = 8
IOS_DEFAULT_MAX_CONTEXT_LENGTH = 4096
```

### 7.4 `export_model()` orchestration (`export/pipeline.py`)
```python
@dataclass
class ExportConfig:
    hf_model_id: str
    variant: Literal["macOS", "iOS"] = "macOS"
    max_context_length: int | None = None
    compute_precision: str = "float16"
    compression: str = DEFAULT_MACOS_COMPRESSION_PRESET
    output_dir: str = "outputs"
    output_name: str | None = None
    num_layers: int | None = None
    overwrite: bool = False
    disable_embedding_quantization: bool = False   # iOS only
    compression_config_object: Any = field(default=None, repr=False)

def export_model(config_or_model_id: ExportConfig | str) -> str:   # returns bundle path
    return asyncio.run(_async_export_model(config))
```
Steps (`_async_export_model`):
1. `AutoConfig.from_pretrained(hf_model_id)` → `model_type` → `get_model_entry(model_type)`; unwrap `entry.hf_config_attr` sub-config.
2. Resolve dtype (`float16|bfloat16|float32` only, else `ValueError`).
3. **max-context validation**: `--max-context-length` may not exceed `hf_config.max_position_embeddings`; error text: *"--max-context-length (X) exceeds the model's max_position_embeddings (Y). Choose a value <= Y."* iOS defaults to `min(4096, native_max_ctx)`.
4. Loading path: **macOS uses `model_class.from_hf_memory_efficient(...)`** with a `tempfile.TemporaryDirectory(prefix="coreai_export_")` mmap dir; **iOS uses `from_hf(...)`** (full RAM). Comment: *"the iOS variant keeps the legacy full-RAM path since its palettization flow has not been validated against streaming weight loading."*
5. Compression: quantization (macOS) via `quantize_pytorch_model`, palettization (iOS) via `palettize_pytorch_model`; asserts both are never set simultaneously.
6. Variant export → `export_macos_model` / `await export_ios_model`.
7. Save: `bundle_path = output_dir/output_name`; asset at `bundle_path/f"{output_name}.aimodel"`; `await asyncio.to_thread(coreai_program.save_asset, aimodel_path, metadata)`; then `bundle_llm_asset(...)`. `FileExistsError` unless `--overwrite`.

Output naming (`_generate_output_name`): `re.sub(r"[^a-z0-9]+", "_", hf_tail.lower()).strip("_")` + `_<compression>` (unless `none`) + `_dynamic` (macOS) / `_static` (iOS). With a YAML config, the YAML **stem** replaces the compression segment (prefixed by the base name unless the stem already starts with it).
Registry mirror of this logic exists in `model_registry._preset_to_output_name` and is exposed via `--as-output-name`.

### 7.5 macOS export (`export/macos.py`)
Graph contract: `input_names = ("input_ids", "position_ids")`, `output_names = ("logits",)`, `state_names = ("keyCache", "valueCache")`.

Reference inputs / dynamic shapes:
```python
input_ids    = torch.randint(1, vocab_size, (1, 16), dtype=torch.int32)          # QUANT_TRACE_QUERY_LEN
position_ids = torch.arange(16 + 8, dtype=torch.int32).unsqueeze(0)               # + QUANT_TRACE_OFFSET
k_cache, v_cache = KVCache.create_cache_tensors(config, dtype=target_dtype)       # with max_position_embeddings temporarily clamped to 2048
dynamic_shapes = {
  "input_ids":    {1: Dim("seq_ids", max=max_context_length - 2)},
  "position_ids": {1: Dim("seq_pos", min=16, max=max_context_length - 1)},
  "k_cache": {KVCache.seq_len_dim(): Dim("k_seq_len", min=2048, max=max_context_length)},
  "v_cache": {KVCache.seq_len_dim(): Dim("v_seq_len", min=2048, max=max_context_length)},
}
```
`KVCache.seq_len_dim() == 3`; cache tensors are `(n_layers, 1, n_kv_heads, max_seq_len, head_dim)`.

Export function (`export_to_coreai`):
```python
def export_fn(module):
    with torch.no_grad():
        ep = torch.export.export(module, args=(), kwargs=reference_inputs, dynamic_shapes=dynamic_shapes)
    ep = ep.run_decompositions(coreai_torch.get_decomp_table())
    remove_functionalization(ep)
    return ep

converter = coreai_torch.TorchConverter()
converter.add_pytorch_module(model, export_fn=export_fn,
                             externalize_modules=_EXTERNALIZE_SPECS,
                             input_names=..., output_names=..., state_names=...)
register_custom_torch_lowering(converter)
program = converter.to_coreai()
program.optimize()
```
`_EXTERNALIZE_SPECS` — composite ops kept as named composites in MLIR:
| target_class | composite_op_name | composite_attrs |
|---|---|---|
| `coreai_torch.composite_ops.GatherMM` | `gather_mm` | `["num_batch_axes"]` |
| `RMSNormImpl` | `rms_norm` | `["axes", "eps"]` |
| `RoPE` | `rope` | `["scale", "base", "dims", "interleaved"]` |
| `SDPA` | `scaled_dot_product_attention` | `["scale", "is_causal", "window_size"]` |
| `GatedDeltaUpdate` | `gated_delta_update` | `[]` |

### 7.6 iOS export (`export/ios.py`) — 4 entrypoints
```python
LOAD_EMBEDDINGS_FUNCTION_NAME   = "load_embeddings"     # () -> embedding_table
GATHER_EMBEDDINGS_FUNCTION_NAME = "gather_embeddings"   # (in_new_token_ids, embedding_table) -> gathered_embeddings
EXTEND_FUNCTION_NAME            = "extend"              # decode
PROMPT_OPT_FUNCTION_NAME        = "prompt_opt"          # prefill (set_prefill_mode(True))
KV_CACHE_INTERLEAVE_FACTOR = 8
```
I/O names (must match the Swift runner):
```
transformer_input, position_ids, in_step, causal_mask, embedding_table   # inputs
key_cache, value_cache                                                   # states
new_k_cache, new_v_cache                                                 # state outputs
out_logits                                                               # output
```
iOS cache shape: `(num_hidden_layers, 1, num_key_value_heads*head_dim, 1, max_context_length)`, fp16. `causal_mask` is `(1, max_context_length, 1, query_len)` fp16. `position_ids` is **uint16**. `in_step` is `int32` shape `(1,)`.

Decomp table for iOS keeps SiLU intact:
```python
decomp_table = torch.export.default_decompositions()
decomp_table.pop(torch.ops.aten.silu.default)
decomp_table.pop(torch.ops.aten.silu.out)
```

Static shape specialization:
```python
query_lengths = [8, 16, 64]
# gather_embeddings: {"8": {in_new_token_ids: (1,8)}, "16": …, "64": …}
cache_len = 256
while cache_len <= max_context_length:
    for q_len in query_lengths:
        forward_static_cfg[f'"{cache_len}_{q_len}"'] = {
            transformer_input: (1, q_len, 1, hidden_size),
            position_ids:      (1, q_len),
            causal_mask:       (1, cache_len, 1, q_len),
            key_cache:   (num_layers, 1, kv_cached_embed_size, 1, cache_len),
            value_cache: (num_layers, 1, kv_cached_embed_size, 1, cache_len),
        }
    cache_len *= 2
coreai_program.set_static_shape_config(GATHER_EMBEDDINGS_FUNCTION_NAME, gather_static_cfg)
coreai_program.set_static_shape_config(EXTEND_FUNCTION_NAME, forward_static_cfg)
coreai_program.set_static_shape_config(PROMPT_OPT_FUNCTION_NAME, forward_static_cfg)
```
→ produces functions named `extend_<cacheLen>_<qLen>` / `prompt_opt_<cacheLen>_<qLen>` / `gather_embeddings_<qLen>`, which is exactly what `StaticShapeEngine` and `ModelStructure.chunkedStatic` parse.

Hardware constraints:
```python
emb_table_constraints = HardwareConstraints(AllocationType.IOSurface, interleave=[8,1,1], alignments=[1,1,1,1])
cache_constraints = HardwareConstraints(AllocationType.IOSurface,
    interleave=[1, 1, 8, 1, 1],
    alignments=[1, 1, 1, 1, 8 * max_context_length, 1])
```
applied to `load_embeddings`, `gather_embeddings`, `extend`, `prompt_opt`.

### 7.7 Compression helpers (`export/compression.py`)
- `get_c4(tokenizer, max_sequence_length=2048, num_calibration_samples=16)` — loads `allenai/c4` `en/c4-train.00000-of-01024.json.gz`, truncates to 2048 tokens. Requires optional `datasets` + `tqdm` (not in the base deps!) — raises ImportError with install hint otherwise.
- `quantize_pytorch_model(model, inputs, dynamic_shapes, quantization_config, calibration_data_fn=None, export_backend=None, mmap_dir=None)`; `export_backend` defaults to `ExportBackend.CoreAI`; pops `calibrate_activations` off the dict; `quantizer.finalize(prepared_model, backend=..., mmap_dir=... if quantizer._execution_mode == ExecutionMode.EAGER else None)`.
  Calibration bounds derived from the traced dynamic shapes: `max_calib_query_len = cache_seq_len - QUANT_TRACE_OFFSET - 1`, `min_calib_query_len = QUANT_TRACE_QUERY_LEN - QUANT_TRACE_OFFSET` (= 8). Raises `ValueError(f"No calibration samples have length >= {min_calib_query_len} tokens")`.
- `palettize_pytorch_model(model, example_inputs, palettization_config)` — `KMeansPalettizer(model, config).prepare(example_inputs=..., num_workers=32)` then `.finalize(prepared, backend=ExportBackend.CoreAI)`.

### 7.8 Custom MLIR ops (`export/mlir_ops.py`)
- Registers `coreai::immutable_slice_update` (`@torch.library.custom_op(..., mutates_args=[])`) — a non-mutating twin used during graph transformation; hardcoded to 5-D slicing.
- Re-exports `mutable_slice_update` from `coreai_models.primitives._ops`.
- `remove_functionalization(exported_program)` replaces `AutoFunctionalized`/`AutoFunctionalizedV2` HOP nodes with immutable variants.
- `register_custom_torch_lowering(converter)` registers slice-update, composite-op, and dequantization lowerings.
Imports from private modules: `coreai._compiler.dialects.{coreai, coreaix}`, `coreai._compiler.ir.{Location, OpResultList, Value}`, `coreai_torch._utils.generate_composite_decl` — **private API surface; likely to break across versions**.

### 7.9 AIModel asset metadata (`export/metadata.py`)
`build_aimodel_metadata(hf_model_id, component=None) -> coreai.runtime.AIModelAssetMetadata` fills `author`, `license`, `model_description`, `creation_date = int(time.time())`. Keyed by HF id in a hardcoded `_METADATA` dict (Qwen2.5-1.5B, Qwen3-0.6B/4B/8B, Qwen3-Coder-30B-A3B, gemma-3-4b/12b-it, Mistral-7B-Instruct-v0.3, Mixtral-8x7B, gpt-oss-20b, Qwen3-VL-2B-Instruct, SD v1-5 / 2-1 / 3.5-medium, FLUX.2-klein-4B, facebook/sam3). Unknown ids log an 80-`!` banner warning and ship an asset with only `creation_date`.

### 7.10 Python model base class (`models/base.py`)
`BaseForCausalLM(torch.nn.Module)` API surface: `_init_model`, `_mutate_state_dict`, `_get_reauthored_config`, `from_hf`, `from_hf_memory_efficient`, `from_pretrained`, `_reassign_cache`, `half/bfloat16/float/to`, plus a `cast_logits_bfloat16_to_float16` decorator.
`BaseForCausalLMForiOS(BaseForCausalLM)` adds `__init__(config, model_device, disable_embedding_quantization=False)` and `set_prefill_mode(prefill_mode: bool)`.
Module-level helpers: `move_model_to_disk`, `_save_and_mmap_safetensors`, `_resolve_safetensors_files`, `_build_safetensors_key_index`, `_load_tensors_for_keys` — the streaming layer-by-layer loader behind `from_hf_memory_efficient`.

### 7.11 Reusable authoring primitives (`python/src/coreai_models/primitives/`)
**macOS** (`primitives/macos/__init__.py` `__all__`): `KVCache`, `SSMState`, `MLP`, `RMSNorm`, `RMSNormGated`, `RMSNormPlusOne`, `RoPE`, `YarnRoPE`, `initialize_rope`, `SDPA`, `SwitchGLU`, `SwitchLinear`, `SwiGLU`. Also `cache_scatter.py` (VLM embedding scatter).
**iOS** (`primitives/ios/__init__.py` `__all__`): `BidirectionalSDPA`, `GELUReauthored`, `gelu_ane`, `GatherEmbeddings`, `LoadEmbeddings`, `KVCacheHandler`, `LayerNormReauthored`, `MLP`, `RMSNorm`, `RoPECache`, `SDPA`, `quantize_per_tensor`, `dequantize_per_tensor`.

`KVCache` (macOS, `primitives/macos/cache.py`):
```python
class KVCache:
    HF_K_BUFFER_NAME = "_full_cached_k"
    HF_V_BUFFER_NAME = "_full_cached_v"
    @classmethod def seq_len_dim(cls) -> int: return 3
    @classmethod def create_cache_tensors(cls, config, dtype=torch.float32) -> (k, v)
        # shape (n_layers, 1, n_kv_heads, max_seq_len, head_dim)
    @classmethod def from_dimensions(cls, n_layers, n_kv_heads, max_seq_len, head_dim)
    def update_and_fetch(self, layer_idx, offset, k, v, seq_len=None, query_len=None) -> (k_out, v_out)
```
`update_and_fetch` uses `mutable_slice_update` with explicit `torch._check`/`torch._check_is_size` guards so `torch.export` can trace it, and supports cross-device (`k.device != cache.device`) by round-tripping.
`SSMState` provides the equivalent for Mamba-style state (`update_states(layer_idx, new_state)`).

### 7.12 SAM3 iOS re-authored model (`models/ios/sam3/`)
Files: `sam3_reauthored.py`, `image_encoder.py`, `text_encoder.py`, `mask_decoder.py`, `detr.py`, `fpn.py`, `primitives/{window.py,rope.py}`. Added in commit `d967fa3` "Adding SAM3 iOS Model (#106)". Split into three functions (`image_encode`, `text_encode`, `detect`) — see §12.

---

## 8. CLI reference — exact invocations

### 8.1 Registry (`coreai.model.registry`)
```bash
uv run coreai.model.registry                                 # summary + suggestions
uv run coreai.model.registry --list-models
uv run coreai.model.registry --list-models --type llm
uv run coreai.model.registry --list-models --type llm --platform macOS
uv run coreai.model.registry --list-models --type diffusion
uv run coreai.model.registry --list-models --type utility
uv run coreai.model.registry --list-families --type llm
uv run coreai.model.registry --list-variants qwen3-0.6b --type llm
uv run coreai.model.registry --model-info qwen3-0.6b --platform iOS --json
uv run coreai.model.registry --model-info qwen3-0.6b --platform iOS --as-export-args
uv run coreai.model.registry --model-info qwen3-0.6b --platform iOS --as-output-name
uv run coreai.model.registry --model-info clip-vit-b32 --type utility --as-export-args
```
Flags: `--type {llm,diffusion,utility}`, `--platform {macOS,iOS}`, `--family`, `--task`, `--experimental`; actions (mutually exclusive) `--list-families | --list-models | --list-variants SHORT_NAME | --model-info SHORT_NAME`; formats (mutually exclusive) `--text` (default) `| --json | --tsv | --as-export-args | --as-output-name`.
`--as-export-args` for a utility model prints `uv run <script> --model <hf_id>`.
`--as-export-args`/`--as-output-name` require exactly one matching preset (pass `--platform` to disambiguate), else exit code 2.
`_require_type` exits 2 for `--list-families`, `--model-info`, `--list-variants` without `--type`.

### 8.2 LLM export
```bash
uv run coreai.llm.export Qwen/Qwen3-0.6B                       # macOS default, 4bit
uv run coreai.llm.export Qwen/Qwen3-0.6B --platform iOS
uv run coreai.llm.export Qwen/Qwen3-0.6B --compression none
uv run coreai.llm.export Qwen/Qwen3-0.6B --platform iOS --compression 4bit_weight_palettized_group8
uv run coreai.llm.export Qwen/Qwen3-0.6B --platform iOS --compression-config my_custom_recipe.yaml
uv run coreai.llm.export Qwen/Qwen3-0.6B --max-context-length 4096
uv run coreai.llm.export Qwen/Qwen3-0.6B --output-dir ./my-models/
uv run coreai.llm.export Qwen/Qwen3-0.6B --num-layers 1 --compression none    # debugging
uv run coreai.llm.export Qwen/Qwen3-0.6B --dry-run
uv run coreai.llm.export org/NewModel --experimental --compute-precision float16 \
    --compression 4bit --max-context-length 4096
uv run coreai.llm.export google/gemma-3-4b-it --compression none --compute-precision bfloat16
uv run coreai.llm.export Qwen/Qwen3-Coder-30B-A3B-Instruct --compression 4bit
```
Context-length rule (`models/README.md:81`): *"macOS models use dynamic KV cache and default to the model's maximum supported context. iOS models require a fixed context length at export time."*

### 8.3 VLM export
```bash
uv run coreai.vlm.export --list-models
uv run coreai.vlm.export qwen3-vl
uv run coreai.vlm.export qwen3-vl --skip-vision
```
Flags: `model` (positional short-name), `--max-context-length N` (default **4096**), `--num-layers N`, `--output-dir DIR`, `--skip-vision`, `--list-models`, `--overwrite`, `--verbose/-v`.

### 8.4 Diffusion export
```bash
uv run coreai.diffusion.export runwayml/stable-diffusion-v1-5
uv run coreai.diffusion.export sd2-community/stable-diffusion-2-1
uv run coreai.diffusion.export stabilityai/stable-diffusion-3.5-medium
uv run coreai.diffusion.export flux2-klein-4b --platform iOS                 # 512 default
uv run coreai.diffusion.export flux2-klein-4b --platform iOS --resolution 1024
uv run coreai.diffusion.export flux2-klein-4b --platform macOS --low-memory
uv run coreai.diffusion.export runwayml/stable-diffusion-v1-5 --components text_encoder unet
uv run coreai.diffusion.export flux2-klein-4b --compression none
```
Flags: `model`, `--output-dir`, `--components …`, `--compute-precision {float16,bfloat16,float32}`, `--compression`, `--overwrite`, `--platform {iOS,macOS}`, `--resolution {512,1024}`, `--low-memory`, `--experimental`, `--dry-run`, `--verbose/-v`.

Component names per family (from `--components` help + `models/*/README.md`):
- SD 1.x/2.x: `text_encoder`, `unet`, `vae_decoder`, `vae_encoder`
- SD 3.x: `text_encoder` (CLIP-L), `text_encoder_2` (CLIP-G), `transformer` (MMDiT), `vae_decoder`
- FLUX.2: `transformer` (1024, macOS), `transformer_512` (iOS), `text_encoder` (Qwen3 encoder, intermediate layers 9/18/27), `vae_decoder`, `vae_decoder_half`, `vae_encoder`, `vae_encoder_half`

### 8.5 Standalone recipes
```bash
uv run models/<name>/export.py            # PEP 723 inline dependencies
uv run models/whisper/export.py --model openai/whisper-large-v3-turbo --dtype float32 --output-dir <dir> --overwrite
uv run models/sam3/export.py                          # lite iOS export, 336x336, w4/gs32 image + w6/gs8 text
uv run models/sam3/export.py --full --dtype float16   # plain HF Sam3Model, 1008x1008
```
Whisper flags: `--model` (default `openai/whisper-large-v3-turbo`), `--output-dir`, `--dtype {float16,bfloat16,float32}` (default float32), `--overwrite`. Saves `<repo-root>/exports/<model>_<dtype>.aimodel`.
SAM3 flags: `--full`, `--output-dir`, `--output-name`, `--image-size` (336 lite / 1008 full), `--max-text-seq-len` (default 32), `--n-bits`, `--group-size`, `--dtype`, `--overwrite`, `--dry-run`.

### 8.6 AOT compilation
```bash
xcrun coreai-build compile model.aimodel --platform iOS
xcrun coreai-build compile model.aimodel --preferred-compute neural-engine   # from common_issues.md
xcrun coreai-build compile --help
```
`models/README.md:173`: *"If you compile a model, replace the corresponding asset in the bundle directory and update `metadata.json` to reference the new filename."*

### 8.7 Swift CLI tools
```bash
swift run -c release llm-runner    --model path/to/exported_model_folder --prompt "Hello"
swift run -c release llm-benchmark --model path/to/exported_model_folder      # -p 512 -g 1024 -n 5
swift run -c release diffusion-runner --model DIR --prompt "…" --steps 4 --guidance-scale 1.0
swift run -c release image-segmenter --model DIR --prompt "cat" --image path/to/image.jpg
swift run -c release speech-runner <bundleDirOrAimodel> [audio.wav]
swift run -c release object-detector --model model.aimodel --image img.jpg
```

#### `llm-runner` — full option list (`swift/Sources/Tools/llm-runner/LLMRunnerMain.swift:67-205`)
```
--model PATH                       model bundle directory (required)
--prompt TEXT                      default "Hello, how are you?"
--prompt-file PATH                 UTF-8 text file
--raw-tokens PATH                  JSON {"tokens":[…]}   (mutually exclusive with the above two)
--max-tokens INT                   default 50
--temperature DOUBLE               default 0.7
--top-k INT
--top-p DOUBLE
--min-p DOUBLE
--sampling-strategy {temperature,greedy}   default "temperature"
--synchronous-sampling             flag; sets SamplingConfiguration.combined = false
--json-schema STRING|PATH          constrained generation
--inference-engine-variant STR     default "default"; {auto|default|coreai-sequential|coreai-pipelined|static-shape}
--kv-cache-strategy {auto,growing,chunked,fixed_size}   default auto
--kv-cache-initial-capacity INT
--stop-tokens STR                  repeatable
--save-logits PATH
--save-logits-length {1..20|full}  default 5
--apply-chat-template BOOL         default true
--continuation TEXT                requires --apply-chat-template=false AND (--print-logits or --save-logits)
--print-logits                     flag
--warmup {default,off,none,exact}  default "default"
--warmup-length INT                HIDDEN; only valid with --warmup exact
--bucket-size INT                  HIDDEN; sets env COREAI_QUERY_BUCKET_SIZE (0 disables, default 64)
--chunk-size INT                   HIDDEN; sets env COREAI_CHUNK_THRESHOLD (default 1024, "use 128 for MoE")
--image PATH                       VLM
--image-strategy {stretch,center_crop,pad}
--image-info {on,off,auto}         default auto
--verbose                          flag
--verbose-level INT                implies --verbose
```
Validation errors: `--warmup exact requires --warmup-length N`; `--warmup-length can only be used with --warmup exact`; `--bucket-size must be >= 0`; `--chunk-size must be > 0`. Using `--top-k/--top-p/--min-p` together with `--sampling-strategy greedy` prints an error and exits.

`ModelPaths` search order (`swift/Sources/CoreAILanguageModels/Assets/ModelPaths.swift`):
1. `--model` (explicit; absolute paths must exist)
2. env `COREAI_MODEL_PATH` (colon-separated)
3. defaults `[".", "./exports", "~/.coreai-models"]`
Error text: `"Model '<x>' not found. Searched: <expanded paths>"`.

Asset extension guard: `modelAssetTypeLabel` accepts only `aimodel` ("source") and `aimodelc` ("compiled"); anything else prints *"Unsupported model file: only .aimodel or .aimodelc"*.

#### `llm-benchmark` (`swift/Sources/Tools/benchmark/BenchmarkMain.swift`)
```
--model PATH (required)
-p/--prompt-tokens INT      default 512
-g/--generation-tokens INT  default 1024
-n/--num-trials INT         default 5
--seed UInt64               default 0
--output-json PATH
```
"Based on mlx-lm benchmark". Uses greedy `SamplingConfiguration(temperature: 0)` and a synthetic splitmix64 random prompt. Prints per-trial prompt/generation tok/s and averages; JSON report keys are snake_cased (`prompt_tps`, `gen_tps`, `averages.prompt_tps`, `averages.generation_tps`). Warns when built in DEBUG.
Generation tok/s denominator is `count - 1` (the prefill-produced first token is excluded).

#### `image-segmenter`
`--model`, `--image`, `--prompt`, plus point/box options, `--max-segments`, `--threshold` (mask sigmoid), `--warmup` flag, JSON output path, `--verbose`, and others.

#### `object-detector`
`--model` (.aimodel dir), `--image`, confidence threshold, max detections, `--warmup`, `--verbose`.

#### `diffusion-runner`
`--model`, `--prompt`, `--negative-prompt`, `--steps`, `--guidance-scale`, `--seed` (default 42), `--scheduler {pndm,dpmpp}` (default dpmpp), `--output` (default `output.png`), `--config` (pipeline.json), `--image` (img2img), `--vae-decode {full,half,tiled}` (default full), `--parity-test DIR`.

#### `speech-runner`
Positional `modelPath` (bundle dir with `encoder.aimodel`+`decoder.aimodel`, or single `.aimodel` legacy), optional positional `audioPath` (omit → 480 000-sample silence latency benchmark).

---

## 9. Swift inference architecture (CoreAILanguageModels)

### 9.1 FoundationModels adoption — `CoreAILanguageModel`

Documented usage (`CoreAILanguageModel.swift:23-31`):
```swift
let model = try await CoreAILanguageModel(resourcesAt: url)  // .lazy by default
print(model.estimatedSizeOnDiskBytes ?? 0)
try await model.load()                                       // optional; respond auto-loads
let session = LanguageModelSession(model: model)
// ... generate ...
model.unload()
```
Canonical app snippet repeated in every model README:
```swift
import FoundationModels
import CoreAILanguageModels

let model = try await CoreAILanguageModel(resourcesAt: modelURL)
let session = LanguageModelSession(model: model)
let response = try await session.respond(to: "What is quantum computing?")
print(response)
```
`PublicInterfaceTests.swift` asserts `response.content` also type-checks.

Type:
```swift
public struct CoreAILanguageModel: LanguageModel {
    public enum LoadMode: Sendable { case lazy; case eager }
    public typealias Executor = CoreAIExecutor

    public init(resourcesAt url: URL,
                mode: LoadMode = .lazy,
                variant: String? = nil,                       // "coreai-sequential", "ane", …
                kvCacheStrategy: KVCacheStrategy = .auto) async throws

    public var capabilities: LanguageModelCapabilities        // .toolCalling/.reasoning/.guidedGeneration
    public var executorConfiguration: CoreAIExecutor.Configuration
    public var estimatedSizeOnDiskBytes: Int? { get }
    public func load() async throws
    public func unload()
}
```
Init behaviour: builds `LanguageBundle`, creates a `CoreAIExecutor.Configuration` (url, variant, kvCacheStrategy, modelIdentifier=bundle.name, samplingConfig: `.greedy`, vocabSize), gets a **process-shared** `ModelResources` for that configuration, then **concurrently** loads the tokenizer and (if `.eager`) the engine via `async let`.

Capability detection at init:
- `supportsReasoning` = tokenizer has `<think>` **or** `<|reasoning_start|>`.
- `supportsToolCalling` = `detectToolCallMarkers(using:) != nil`.
- `isGuidedGenerationSupported` = loaded engine's `supportsLogits` if known, else `variant != "coreai-pipelined"`.

Marker detection (static, on `CoreAIExecutor`):
```swift
detectThinkingMarkers → first of [("<think>","</think>"), ("<|reasoning_start|>","<|reasoning_end|>")]
                        whose BOTH tokens exist via convertTokenToId; falls back to ("<think>","</think>")
detectToolCallMarkers → first of [("<tool_call>","</tool_call>"), ("<function_calls>","</function_calls>")]
                        else Mistral special case: ("[TOOL_CALLS]", "\n")   // synthetic close; JSON array is single-line
                        else nil
```

### 9.2 The FM executor protocol shape (as adopted here)
```swift
public struct CoreAIExecutor: LanguageModelExecutor {
    public typealias Model = CoreAILanguageModel
    public struct Configuration: Hashable, Sendable { url; variant; kvCacheStrategy; modelIdentifier; samplingConfig; vocabSize }
    public init(configuration: Configuration) throws
    public func prewarm(model: CoreAILanguageModel, transcript: Transcript)      // synchronous, fires a Task
    public nonisolated(nonsending) func respond(
        to request: LanguageModelExecutorGenerationRequest,
        model: CoreAILanguageModel,
        streamingInto channel: LanguageModelExecutorGenerationChannel
    ) async throws
}
```
Request surface used: `request.transcript` (a `Transcript` of `Transcript.Entry`), `request.enabledToolDefinitions` (`[Transcript.ToolDefinition]`), `request.schema` (`GenerationSchema?`), `request.generationOptions` (`GenerationOptions` — `.temperature`, `.maximumResponseTokens`).

Channel events emitted:
```swift
await channel.send(.response(action: .appendText(text, tokenCount: 1)))
await channel.send(.reasoning(action: .appendText(text, tokenCount: 1)))
await channel.send(.toolCalls(action: .toolCall(id: id, name: name, action: .appendArguments(argsJSON, tokenCount: 1))))
await channel.send(.response(action: .updateUsage(
        input: .init(totalTokenCount: promptTokens.count, cachedTokenCount: 0),
        output: .init(totalTokenCount: generatedTokenCount, reasoningTokenCount: reasoningTokenCount))))
```
Two authoritative comments about the 2026 FM API:
- `CoreAILanguageModel.swift:309-310`: *"FoundationModels now threads entry identity itself based on event ordering — we no longer mint an entryID and pass it down."*
- `:487-492`: *"Reasoning is a sibling of response/tool-calls in the new API (not nested under response) because at parse time we don't yet know whether the model will follow the thought block with a response or a tool call."*

Errors thrown into FM:
```swift
LanguageModelError.unsupportedTranscriptContent(.init(unsupportedContent: Array(request.transcript),
                                                      debugDescription: "…"))
LanguageModelError.unsupportedCapability(.init(capability: .guidedGeneration, debugDescription: "…"))
```

Defaults: `maxTokens = request.generationOptions.maximumResponseTokens ?? (model.supportsReasoning ? 2048 : 512)`.
Sampling: only `options.temperature` is honoured — `makeSamplingConfig` returns `SamplingConfiguration(temperature:)` when set, else the model's base config (`.greedy`). **topK/topP/minP are not reachable through the FM path.**

### 9.3 Transcript → tokens (chat templating)
`CoreAIExecutor.makeTokens(from:using:tools:component:)` maps entries to `[Message]` dicts:
| `Transcript.Entry` | message |
|---|---|
| `.instructions` | `{"role":"system","content": segments joined with "\n"}` |
| `.prompt` | `{"role":"user","content": …}` |
| `.response` | `{"role":"assistant","content": …}` |
| `.toolCalls` | `{"role":"assistant","content":"","tool_calls":[{"id":…, "type":"function","function":{"name":…,"arguments":…}}]}` |
| `.toolOutput` | `{"role":"tool","tool_call_id":…, "name":…, "content":…}` |
| `.reasoning` | **skipped** — *"Don't echo the model's prior reasoning back into the prompt."* |
Then `tokenizer.applyChatTemplate(messages: messages, tools: toolSpecs)`; on throw it falls back to concatenating `content` strings with `"\n"` and plain `tokenizer.encode(text:)`.
Tool definitions become `ToolSpec` = `["type":"function","function":["name":…,"description":…,"parameters": <JSON tree>]]` via a private `JSONValue` Sendable enum.

### 9.4 Incremental detokenization (the subtle part)
`respondVanilla` keeps `pendingTokens` and re-decodes:
- On U+FFFD in the **full decoded text** (not just the delta) it holds the token and emits `.appendText("", tokenCount: 1)`. Comment explains why checking the delta is insufficient: *"Some tokenizers emit one U+FFFD per attempted decode of an incomplete multi-byte sequence … making `delta` empty and hiding the still-incomplete state."*
- After a clean emit it retains exactly **one** trailing token as context: *"SentencePiece needs at least one prior token to infer the leading ▁ (space) on the following token; clearing to empty decodes each new token in isolation and drops inter-word spaces."* → decode cost bounded to 2 tokens/step.
- `thinkParser.flush()` + `toolCallParser.flush()` at end of stream, *"Without this, content right at the EOS boundary (or inside an unclosed block) would be lost."*
- Ends with `await Task.yield()` *"to let the engine's tokenSequence Task finish cleanup (putBackEngine, state reset, etc.) before the next respond()."*

EOS set = tokenizer `eosTokenId` ∪ `model.additionalEosTokenIds` (see `LanguageConfig.additionalStopTokenIds`).

### 9.5 `LanguageConfig.additionalStopTokenIds(from:tokenizer:)`
Parses `tokenizer_config.json` (best-effort; returns `[]` on any failure):
1. `additional_special_tokens` (strings or `{"content": …}` dicts)
2. array-valued `eos_token`
3. `added_tokens_decoder` entries with `special == true` whose lowercase content contains one of
   `["end_of_turn", "im_end", "eot_id", "endoftext"]`
Main EOS is excluded. `TODO` in source: *"Upstream this to swift-transformers as `Tokenizer.additionalEosTokenIds`."*
Commit `cba2c84` added `"endoftext"` because *"Qwen3 declares eos_token as `<|im_end|>` (151645) but xgrammar can also produce `<|endoftext|>` (151643) as a valid grammar terminal."*
Commit `02a8edd` "Fix Gemma stop tokens: read additional EOS from tokenizer config" (Gemma's `<end_of_turn>` = 106).

### 9.6 `ThinkTagParser` (internal struct)
```swift
struct ThinkTagParser {
    enum Event { case text(String); case reasoning(String) }
    init(open: String = "<think>", close: String = "</think>")
    mutating func consume(_ delta: String) -> [Event]
    mutating func flush() -> [Event]
}
```
Holds back at most `closeMarker.count - 1` characters so a marker straddling two deltas isn't truncated (`lastSafeIndex(forTag:)`).

`ToolCallParser` mirrors this with `init(openMarker:closeMarker:)` and `Event { case text(String); case toolCall(id:name:argsJSON:) }`.

### 9.7 `ModelResources` — lazy load / shared registry
`swift/Sources/CoreAILanguageModels/LanguageModel/ModelResources.swift` (introduced by `eb3998e` "Lazy runner design: defer engine load (#91)"). `final class ModelResources: ResourceManaging`.
- `engine() async throws -> any InferenceEngine` — single in-flight load shared by concurrent callers; failures are **not** cached (task dropped so next caller retries); a `generation` counter lets an in-flight load detect it was cancelled by `unloadResources()`.
- `withEngine { engine in … }` — increments `activeBorrows`; a concurrent `unloadResources()` sets `unloadPending` and teardown is deferred until the last borrow returns, *"so the engine is never freed mid-generation."*
- `static func shared(for: CoreAILanguageModel.CoreAIExecutor.Configuration) -> ModelResources` — process-wide registry keyed by the Hashable Configuration, values held in a `WeakBox` so releasing the model releases the engine.
- `loadEngine` does `CoreAIRunner(contentsOf:variant:kvCacheStrategy:)` → `makeInferenceEngine()` → `try await engine.warmup(queryLength: 1, sampling: nil)`.

### 9.8 `CoreAIRunner`
```swift
public struct CoreAIRunner {
    public init(contentsOf url: URL, variant: String? = nil, kvCacheStrategy: KVCacheStrategy = .auto) throws
    public init(bundle: LanguageBundle, variant: String? = nil, kvCacheStrategy: KVCacheStrategy = .auto)
    public func makeInferenceEngine() async throws -> any InferenceEngine
}
```
(the `bundle:` label is post-#122; it was `from:` before.)

---

## 10. `InferenceEngine` protocol & engine variants

`swift/Sources/CoreAILanguageModels/InferenceEngines/InferenceEngine.swift`

```swift
public typealias LogitsScalarType = Float16      // Float on macOS x86_64

public struct InferenceOutput: Sendable {
    public let tokenId: Int32
    public let logits: [LogitsScalarType]?       // only when InferenceOptions.includeLogits
}

public struct InferenceOptions: Sendable {
    public var maxTokens: Int?                   // nil = until EOS / context limit
    public var includeLogits: Bool
    public var forcedContinuation: [Int32]?      // MMLU-style P(continuation|context)
    public init(maxTokens: Int? = nil, includeLogits: Bool = false, forcedContinuation: [Int32]? = nil)
}

public protocol InferenceEngine: Sendable {
    associatedtype OutputSequence: InferenceOutputSequence
    typealias TokenId = Int32
    func generate(with input: [TokenId],
                  samplingConfiguration: SamplingConfiguration,
                  inferenceOptions: InferenceOptions) async throws -> OutputSequence
    var processedTokenCount: Int { get }                       // default 0
    func reset(to tokenIndex: Int) async throws                // 0 == full reset
    func warmup(queryLength: Int, sampling: SamplingConfiguration?) async throws   // default no-op
    var isBusy: Bool { get }                                   // default false
    func cancel() async throws                                 // default no-op
    var supportsLogits: Bool { get }                           // default false
    var lastPrefixHitCount: Int { get }                        // default 0
    associatedtype ConfigType: Codable, InferenceConfiguration
    var config: ConfigType { get }
}
extension InferenceEngine { public func reset() async throws { try await reset(to: 0) } }
```
`InferenceConfiguration` defaults: `prefillChunkSize = 512`, `chunkThreshold = 1024`.
The memory rationale in the doc comment is worth quoting verbatim:
> Logits buffer = batch × seqLen × vocabSize × sizeof(Float16)
> Example with Qwen3 (vocab_size = 151,936):
> - 32K prompt without chunking: 1 × 32,768 × 151,936 × 2 = **9.6 GB**
> - 512-token chunk: 1 × 512 × 151,936 × 2 = **155 MB** (98% reduction)

`MultimodalInferenceEngine: InferenceEngine` adds `encodeImage(at:) async throws -> EmbeddedInput` and `generate(with: EmbeddedInput, tokens:samplingConfiguration:inferenceOptions:)`.

### 10.1 `KVCacheStrategy`
```swift
public enum KVCacheStrategy: String, Codable, Sendable, CaseIterable {
    case auto      = "auto"
    case fixedSize = "fixed_size"
    case growing   = "growing"
    case chunked   = "chunked"     // NOT IMPLEMENTED — falls back to StaticKVCache
    public func defaultSize(maxContextLength: Int) -> Int? {
        switch self { case .auto: nil; case .fixedSize: maxContextLength; case .growing: 256; case .chunked: maxContextLength }
    }
}
```
Docs: `.growing` = "Start small, grow exponentially (2×) … ~20ms stall on growth (amortized O(log₂ N))".
`.auto` resolves in `KVCacheFactory.make`: `growing` if the model's key-cache seq dim is `-1` (dynamic), else `fixedSize`.
Explicit non-auto, non-fixedSize strategy on a static-seq-dim model throws:
> `"Strategy 'growing' requires dynamic KV cache support. Model has fixed seqDim. Re-export with --dynamic-sized-kvcache-gpu flag."`
`KVCacheError.capacityExceeded` message: `"KV cache capacity exceeded: need N tokens but only M available. Use --kv-cache-strategy growing for automatic expansion."`
**NOTE / UNVERIFIED:** `--dynamic-sized-kvcache-gpu` is referenced in Swift error strings and doc comments but does **not** exist in this repo's Python export CLIs. It presumably belongs to a different/earlier export tool.

### 10.2 `EngineFactory` and variant selection
```swift
public static func createEngine(config: Data, modelURL: URL, options: EngineOptions = EngineOptions())
    async throws -> any InferenceEngine
```
Variants (private enum, raw values are the strings users pass):
```
"coreai-sequential"  -> CoreAISequentialEngine   (CPU-ish, dynamic model)
"coreai-pipelined"   -> CoreAIPipelinedEngine    (GPU, dynamic model)   ← auto for .dynamic
"static-shape"       -> StaticShapeEngine        (Neural Engine, chunked static) ← auto for .chunkedStatic
```
`nil`, `"auto"`, `"default"` all mean auto-detect. Unknown string throws:
> `"Unknown variant '<x>'. Valid: auto, coreai-sequential, coreai-pipelined, static-shape"`
Compatibility matrix (`checkVariantCompatibility`):
| variant × structure | result |
|---|---|
| staticShape × dynamic | incompatible — *"Static-shape variant requires chunked static model (extend_* functions)"* |
| pipelined × chunkedStatic | incompatible — *"Core AI pipelined variant requires dynamic model"* |
| sequential × chunkedStatic | incompatible — *"Sequential variant requires dynamic model"* |
| anything × (dynamic \| chunkedStatic) | OK |
| anything × other structure | *"LLM engine variants are incompatible with this model structure"* |

`autoDetectVariant` **`preconditionFailure`s** (crashes) for any structure other than `.chunkedStatic`/`.dynamic`.

```swift
public struct EngineOptions: Sendable {
    public let variant: String?
    public let kvCacheStrategy: KVCacheStrategy   // default .auto
    public let kvCacheSize: Int?                  // default nil
    public init(variant: String? = nil, kvCacheStrategy: KVCacheStrategy = .auto, kvCacheSize: Int? = nil)
    public func resolvedKVCacheSize(maxContextLength: Int) -> Int?
}
```
Doc warning on `.fixedSize`: *"Avoid `.fixedSize` unless you need a known upper bound. It pre-allocates the cache at the full `maxContextLength`, which can consume several gigabytes on long-context models and slows each decoding step because every iteration operates on the full-size KV."*

### 10.3 Model structure detection (`CoreAIShared/Runtime/ModelStructure.swift`)
```swift
public enum GraphNames {
    public static let main = "main"
    public static let loadEmbeddings = "load_embeddings"
    public static let extendPrefix = "extend"
    public static let imageEncode = "image_encode"
    public static let textEncode = "text_encode"
    public static let detect = "detect"
}
public enum ModelStructure { case chunkedStatic(batchSize: Int); case dynamic; case multiFunctionSegmenter }
```
Detection order: `extend*` + `load_embeddings` → `.chunkedStatic(batchSize:)` (batch parsed from `extend_<context>_<batch>`, index 2); `image_encode`+`text_encode`+`detect` → `.multiFunctionSegmenter`; `main` → `.dynamic`; else `.dynamic` with a warning.

Specialization options derived from structure:
```swift
case .chunkedStatic, .multiFunctionSegmenter:
    SpecializationOptions(preferredComputeUnitKind: .neuralEngine)
case .dynamic:
    var opts = SpecializationOptions(preferredComputeUnitKind: .gpu)
    opts.expectFrequentReshapes = true
```
`PreparedModel.prepare(at:)`:
```swift
let asset = try AIModelAsset(contentsOf: url)
let summary = try asset.summary(includingStatistics: false)      // probe function names WITHOUT specializing
let model = try await AIModel(contentsOf: url, options: probedStructure.specializationOptions)
```
Also `PreparedModel.resolveCoreAIModelURL(from:)` — if the URL isn't `.aimodel`, looks for a sibling `<basename>.aimodel`.

### 10.4 `CoreAISequentialEngine` (dynamic, CPU-side sampling, `supportsLogits == true`)
Model contract (doc comment, `CoreAISequentialEngine.swift:24-32`):
> Expects a `.aimodel` with:
> - **2 inputs**: `input_ids` (Int32), `position_ids` (Int32)
> - **1 output**: `logits` (LogitsScalarType)
> - **2 states**: `keyCache`, `valueCache` — persistent across steps, updated in-place
> KV cache NDArrays start small (256 tokens) and grow dynamically with 2× expansion.

Init validates `descriptor.inputNames.count == 2`, `outputNames.count >= 1`, `stateNames.count == 2`, and `logitsDesc.scalarType == .float16` (else `unsupportedLogitsType`). Names are taken **positionally** from the descriptor arrays (inputs[0]=input_ids, inputs[1]=position_ids, states[0]=key, states[1]=value, outputs[0]=logits).

Execution core:
```swift
var states = InferenceFunction.MutableViews()
states.insert(&keyCache, for: keyCacheName)
states.insert(&valueCache, for: valueCacheName)
var outputViews = InferenceFunction.MutableViews()
outputViews.insert(&logitsArray, for: logitsName)
_ = try await function.run(
    inputs: [inputIdsName: inputIdsArray, positionIdsName: positionIds],
    states: consume states,
    outputViews: consume outputViews)
```
Perf notes in source: `input_ids`/`logits` NDArrays are cached and only reallocated when batch size changes (*"Saves ~50-100 µs/step"*). `zeroFill` uses a hand-rolled pointer loop because *"under -Onone, fillNDArray's `(Int) -> LogitsScalarType` closure is invoked per element … which made zeroing the KV cache (~14.7M elements for a 32K-context Qwen3) take **~6 seconds per `reset()`**"*.
`drain()` busy-waits with 1 ms sleeps and `fatalError`s after 5000 attempts (*"Sequential engine drain() timeout — generation Task stuck?"*).

Prefill strategy: `.chunked(chunkSize: config.prefillChunkSize)` when `newTokenCount > config.chunkThreshold`, else `.wholeBatch` (`.oneAtATime` exists but is unused by `selectPrefillStrategy`).

Implicit prefix caching in `generate()`: resolves input against `TokenHistory`; on divergence → `internalReset(to: 0)`; on pure extension → `internalReset(to: max(0, commonPrefix - 1))`; sets `lastPrefixHitCount`.

`ModelConfig` chunking env overrides (`ModelConfig.swift:126-144`):
```swift
public var chunkThreshold: Int  // env COREAI_CHUNK_THRESHOLD (>0) else 1024
public var prefillChunkSize: Int { min(512, chunkThreshold) }
```

### 10.5 `CoreAIPipelinedEngine` (GPU, on-device sampling, `supportsLogits == false`)
Header (`CoreAIPipelinedEngine.swift:36-43`):
> GPU-pipelined inference engine using Core AI's encode API.
> - Non-blocking GPU encoding via `InferenceFunction.encode`
> - GPU-direct token sampling (argmax/topK) via MPSGraph compute shaders
> - Pipeline-depth-matched buffer rotation for CPU/GPU overlap
> - Growing KV cache with pipelined expansion
> - All tensors are owned MTLBuffers — Core AI never allocates/frees them

Constants:
```swift
private let pipelineDepth = 3
private let averageExpectedPromptSize = 256
private let temperatureTolerance: Double = 0.001
private let minimumMPSNDArrayBufferSize = 64   // "MPSNDArray enforces 64-byte row-stride alignment"
```

Hard errors thrown by `generate()`:
- `includeLogits == true` → `"CoreAI pipelined engine does not support logits (GPU-side sampling). Use a sequential engine for constrained generation or evaluation."`
- `forcedContinuation != nil` → `"CoreAI pipelined engine does not support forcedContinuation (GPU-side sampling). Use a sequential engine for evaluation."`
- Changing temperature/greediness mid-generation → `"Sampling configuration changed mid-generation. Call reset() first."` / `"Temperature changed mid-generation (a -> b). Call reset() first."`
- `contextLengthExceeded` before prefill when `maxContextLength - processedTokenCount - prompt.count < 1`.

The Core AI async encode API used:
```swift
let tokenValue = unsafe InferenceFunction.AsyncValue(
    unsafeBuffer: mtlBuffer, byteOffset: …, scalarType: .int32, shape: [1, queryLength], strides: …)
var keyState = unsafe InferenceFunction.AsyncMutableValue(
    unsafeBuffer: keyBuffer, byteOffset: 0, scalarType: keyCacheScalarType, shape: keyShape, strides: keyStrides)
var asyncStates = InferenceFunction.AsyncMutableViews()
asyncStates.insert(&keyState, for: keyCacheName)
…
let _ = try function.encode(inputs: asyncInputs,
                           states: consume asyncStates,
                           outputViews: consume asyncOutputs,
                           to: computeStream)          // ComputeStream(commandQueue:)
await computeStream.currentWorkCompleted()
```
Comment: *"This commits + uses runAfterSyncPoint (no stream wait) — enables true pipelining."*

`PipelineGate` (internal `final class`, capacity == `pipelineDepth`) — backpressure. Doc comment states the failure mode precisely:
> Without this, the decode loop submits encodes (~220/s) faster than the sampler callback drains them (~70/s); depth grows until `MPSCommandBufferImageCache` fails to allocate another private MTLBuffer.
> Class, not actor: `release()` runs synchronously from the Metal callback — an actor would force `Task { await release() }` with ordering ambiguity.
Test hooks: `_inFlightForTesting`, `_waitersForTesting` (exercised by `PipelineGateTests`).

Buffer rotation: `cachePositionBuffers`, `decodeOutputBuffers`, `decodeLogitsBuffers` all have `pipelineDepth` entries, indexed by `step % pipelineDepth`. Decode reads its input token from `decodeOutputBuffers[(step + pipelineDepth - 1) % pipelineDepth]` — i.e. the previous step's GPU-written token, never round-tripping to CPU. Fixed by `e358c84` "Fix pipeline race condition: rotate all buffers by pipeline depth (#53)".
Prefill writes tokens at their **natural position** in `inputTokensBuffer` so concurrent chunks touch disjoint regions (*"no encodeWriteOperands serialization available in Core AI"*).

End-of-generation sentinel (`runCompletion`, lines 988-1004):
> Submit an empty command buffer on the same serial queue. Its `addCompletedHandler` fires after all real sampler callbacks (serial queue FIFO ordering via `MTLDispatchListApply`), guaranteeing every `continuation.yield` has returned before the caller calls `finish()`. We use a bare command buffer instead of the sampler to avoid the shared `MPSGraphExecutableExecutionDescriptor` issue in `MPSGraphCompositeSampler`.

`reset(to:)` semantics differ from the other engines:
- `tokenIndex == 0`: cancel + drain + `currentWorkCompleted()` + `engine.reset()` + `history.clear()`.
- `tokenIndex > 0`: **does not cancel** — *"cancelling corrupts the pipeline's double-buffer state"*; drains, waits for GPU, then rewinds counters.
Divergence during `generate()` forces a **full** reset: *"Tokens differ — full reset (partial rewind corrupts buffer rotation)"*.

Warmup: `performWarmup(queryLength:samplingConfig:)`; default warms shapes `[1, 256]`. *"A single warmup at any shape primes the framework's internal caches (reshape, kernel compilation, state pool). Benchmarks show no benefit from warming every bucket shape."*

### 10.6 `StaticShapeEngine` (Neural Engine chunked-static, `supportsLogits == true`)
`swift/Sources/CoreAILanguageModels/InferenceEngines/CoreAIStaticShapeEngine.swift`
```swift
// MARK: I/O name contracts — models must use these exact names
private static let logitsOutputName = "out_logits"
private static let keyCacheName     = "key_cache"
private static let valueCacheName   = "value_cache"
```
- Function categorisation: names with prefix `extend` **or** `prompt` are decoder functions; `gather_embeddings*` are gather functions.
- `maxQueryLength` = max trailing integer across extend function names (fallback 64).
- Requires an extend function whose context length equals `config.maxContextLength`, else `invalidState("Failed to find an extend function with the max context length of N")`.
- KV caches are `NDArray`s allocated from the max-context descriptor (IOSurface-backed).
- Embedding table loaded once at init from `load_embeddings`.
`ModelShapeConfig` / `ModelShapeSelector` (`ModelShapeConfig.swift`) parse `entrypoint` names into `(maxContextLength, querySize, entrypoint)` and pick shapes via `selectShape(currentSeqLength:desiredQuerySize:)` / `selectShapeForDecode(currentSeqLength:tokensToProcess:)`.

### 10.7 `CoreAISequentialVLMEngine` (`MultimodalInferenceEngine`)
```swift
public struct VLMModelConfig: InferenceConfiguration, Codable, Sendable {
    public let base: ModelConfig
    public let visionConfig: VisionConfig
}
public final class CoreAISequentialVLMEngine: MultimodalInferenceEngine, @unchecked Sendable {
    public init(config: VLMModelConfig, visionModel: PreparedModel, embedModel: PreparedModel,
                llmModel: PreparedModel, options: EngineOptions) async throws
    public func encodeImage(at url: URL) async throws -> EmbeddedInput
    public func encodeImage(cgImage: CGImage) async throws -> EmbeddedInput
    public func generate(with input: EmbeddedInput, tokens: [Int32],
                         samplingConfiguration: SamplingConfiguration,
                         inferenceOptions: InferenceOptions) async throws -> GenerationSequence
}
public struct EmbeddedInput: Sendable {
    public let embeddings: NDArray          // [batch, seq_len, hidden_dim]; init throws if rank != 3
    public let embeddingPositions: Range<Int>
    public var tokenCount: Int { embeddings.shape[1] }
}
```
Note: `llm-runner` loads the three VLM sub-models **sequentially** with the comment *"Sequential to avoid runtime errors with concurrent model preparation."*, whereas `CoreAIVisionLanguageModel.init` loads them **concurrently** with `async let`. (Divergent — see open questions.)

`CoreAIVisionLanguageModel` prompt construction fallback uses the Qwen3-VL ChatML format:
```
<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n
<|im_start|>user\n<|vision_start|>{<|image_pad|> × N}<|vision_end|>\n{userText}<|im_end|>\n<|im_start|>assistant\n
```
VLM stop set = tokenizer EOS ∪ `<|im_end|>`. VLM sampling is hardcoded to `SamplingConfiguration(temperature: 1.0, topK: 1)`; `maxTokens` defaults to 512.

### 10.8 Stop reasons & output sequences
```swift
public enum StopReason: Sendable, Equatable {
    case maxTokens, eos, stopSequence(String), cancelled, error
}
public protocol InferenceOutputSequence: AsyncSequence<InferenceOutput, any Error> {
    var stopReason: StopReason? { get }
    func setStopReason(_ reason: StopReason)
}
```
`StopReasonStore` is a `Mutex`-backed reference box with `set` / `setIfUnset` so the value survives the value-typed sequence. Engine iterators set `.maxTokens` on natural exhaustion (`setIfUnset` so a consumer's `.eos` isn't clobbered), `.cancelled`, `.error`.
`GenerationToken` is a `Sendable final class` with `isCancelled` / `cancel()`; the engine holds the active token and iterators poll it each `next()`.

---

## 11. Sampling

### 11.1 `SamplingConfiguration`
```swift
public struct SamplingConfiguration: Sendable, Equatable, Hashable {
    public let temperature: Double
    public let topK: Int?
    public let topP: Double?
    public let minP: Double?
    public let combined: Bool                 // default true; false = separate sampling step (finer instrumentation)
    public init(temperature: Double, topK: Int? = nil, topP: Double? = nil, minP: Double? = nil, combined: Bool = true)
    public static let greedy = SamplingConfiguration(temperature: 0)
    public static func temperature(_ t: Double) -> SamplingConfiguration
    public var isGreedy: Bool        // temperature == 0
    public var isComposite: Bool     // temperature > 0 && (topK|topP|minP != nil)
    public func validateAndWarn()
    public func normalized() -> SamplingConfiguration
    public func fallbackSampler(from logits: inout [LogitsScalarType]) -> Int32
}
```
Preconditions (**crash, not throw**): `temperature >= 0`, `topK > 0`, `topP ∈ (0,1]`, `minP ∈ (0,1]`.

Documented algorithm order:
```
logits → [temperature scaling] → [minP filter] → [topP filter] → [topK filter] → [softmax] → [sample]
```
Warnings emitted by `validateAndWarn()`: `topK=1` with `temperature>0`; `topP=1.0`; `minP=1.0`; `minP`+`topP` together; any of topK/topP/minP with `temperature=0`.

### 11.2 CPU `CompositeSampler`
Float16 and Float32 overloads, each with an optional `using rng: inout some RandomNumberGenerator` variant for deterministic tests.
- Greedy: vImage `Planar16F→PlanarF` conversion then `vDSP_maxvi`.
- Fast path (no topK/topP/minP): `vDSP_vsdiv` temperature, vectorized softmax (`vDSP_maxv`, `vDSP_vsadd`, `vvexpf`, `vDSP_sve`, `vDSP_vsmul`), inverse-CDF multinomial.
- Slow path: `selectActiveIndices` — min-heap top-K in O(V log K) when `topK` set, else full sort; `minP` applied in logit space as `logit >= maxLogit + logf(minP)`; `topP` computed over the K-sized window only; then softmax + multinomial over the compacted subset.
- `allMasked(_:)` helper for grammar-masked logits (all `-inf`/NaN).
Doc note: guided generation works through either path because masked positions are set to `-Float.infinity` (or `-Float16.greatestFiniteMagnitude`) and `exp()` them to 0.

### 11.3 GPU `MPSGraphSampler`
```swift
protocol MPSGraphSampler: AnyObject, Sendable {
    var vocabSize: Int { get }
    func encode(to queue: MTLCommandQueue, logitsBuffer: MTLBuffer, logitsOffset: Int,
                outputBuffer: MTLBuffer, outputOffset: Int, completion: @escaping (Int32) -> Void)
    func encodeWithSlice(to queue: MTLCommandQueue, logitsBuffer: MTLBuffer, queryLength: Int,
                         outputBuffer: MTLBuffer, outputOffset: Int, completion: @escaping (Int32) -> Void)
}
enum MPSGraphSamplerFactory {
    static func makeSampler(device:vocabSize:config:) throws -> any MPSGraphSampler
}
```
Selection: `temperature == 0` → `MPSGraphArgmaxSampler`; else `MPSGraphCompositeSampler(device:vocabSize:k:temperature:…)`.
Effective K: explicit `topK`; else `min(1000, vocabSize)` when only topP/minP set; else **40**.
Design notes from the file header: vocab size and temperature are **fixed at sampler construction** (*"Changing temperature requires engine reset + new sampler"*); `encodeWithSlice` blits out the last token's logits for multi-token prefill.

**Bug fixed in `aff0bb2` (#121)** — worth quoting:
> The MPSGraphCompositeSampler reused a single `MPSGraphExecutableExecutionDescriptor` across all pipelined steps. Under pipelined execution (depth > 1), overlapping runAsync calls on the same executable corrupt intermediate scratch buffers when sharing a descriptor, producing garbled output (word repetitions, doubled punctuation) with temperature > 0. Create a fresh descriptor per `encode()` call, matching the pattern `MPSGraphArgmaxSampler` already uses.

Commit `1522e5a` "Add TopP and MinP sampling to all engines (#48)".

---

## 12. Guided / constrained generation (xgrammar)

### 12.1 Swift wrapper over the C bridge (`GuidedGeneration/XGrammarWrapper.swift`)
```swift
public final class CompiledGrammar { public var memorySizeBytes: Int }
public final class GrammarCompiler {
    public init(tokenizerInfo: TokenizerInfo, maxThreads: Int = 8, cacheEnabled: Bool = true)
    public func compileJSONSchema(_ schema: String, anyWhitespace: Bool = true, strictMode: Bool = true) throws -> CompiledGrammar
}
public final class GrammarMatcher {
    public init(compiledGrammar: CompiledGrammar, maxRollbackTokens: Int = 0)
    public func fillNextTokenBitmask(_ bitmask: UnsafeMutablePointer<Int32>) -> Bool
    public func acceptToken(_ tokenId: Int32) -> Bool
    public var isTerminated: Bool
    public func reset()
}
public enum XGrammarError: Error { case schemaCompilationFailed(String) }
```
The bitmask is passed as a **DLPack** `DLTensor` (`kDLCPU`, `kDLInt` 32-bit, 1-D, length `(vocabSize + 31) / 32`).

Complete C bridge surface (`swift/Sources/lib/CXGrammar/include/xgrammar_c_bridge.h`, all 14 declarations):
```c
XGrammarTokenizerInfo*  xgrammar_tokenizer_info_create(const char** vocab, int32_t count,
                                                      XGrammarVocabType type, bool addPrefixSpace);
int                     xgrammar_tokenizer_info_get_vocab_size(const XGrammarTokenizerInfo*);
void                    xgrammar_tokenizer_info_free(XGrammarTokenizerInfo*);
XGrammarCompiler*       xgrammar_compiler_create(...);
XGrammarCompiledGrammar* xgrammar_compile_json_schema(...);
size_t                  xgrammar_compiled_grammar_memory_size(const XGrammarCompiledGrammar*);
void                    xgrammar_compiled_grammar_free(XGrammarCompiledGrammar*);
void                    xgrammar_compiler_free(XGrammarCompiler*);
XGrammarMatcher*        xgrammar_matcher_create(...);
bool                    xgrammar_matcher_fill_next_token_bitmask(XGrammarMatcher*, DLTensor*);
bool                    xgrammar_matcher_accept_token(XGrammarMatcher*, int32_t);
bool                    xgrammar_matcher_is_terminated(const XGrammarMatcher*);
void                    xgrammar_matcher_reset(XGrammarMatcher*);
void                    xgrammar_matcher_free(XGrammarMatcher*);
```
**There is no stop-token entry point in the bridge at all** — which is why `stopTokenIds` is unimplementable as written (see below).

### 12.2 `ConstrainedGenerationSession` (~Copyable)
```swift
public struct ConstrainedGenerationSession: ~Copyable {
    public let schema: String
    public let vocabularySize: Int
    public var isTerminated: Bool                     // matcher.isTerminated || allTokensBlocked
    public var compiledGrammarMemoryBytes: Int
    public init(jsonSchema: String, vocabulary: [String], vocabType: VocabularyType = .byteLevel, stopTokenIds: [Int32]? = nil) throws
    public init(jsonSchema: String, tokenizerInfo: TokenizerInfo) throws
    public init(jsonSchema: String, tokenizer: any Tokenizer, vocabSize: Int, vocabType: VocabularyType = .byteLevel, stopTokenIds: [Int32]? = nil) throws
    public init(schemaPath: String, vocabulary: [String], vocabType: VocabularyType = .byteLevel, stopTokenIds: [Int32]? = nil) throws
    public mutating func nextTokenBitmask() -> [Int32]?
    @discardableResult public mutating func applyMask(to logits: inout [Float]) -> Bool
    @discardableResult public mutating func applyMask(to logits: inout [Float16]) -> Bool   // non-x86_64
    @discardableResult public mutating func acceptToken(_ tokenId: Int32) -> Bool
    public mutating func reset()
}
public enum ConstrainedGenerationError: Error { case invalidSchema(String); case generationFailed(String) }
```
Termination is detected **two** ways: `matcher.isTerminated`, **or** `fillNextTokenBitmask` returning false / filling an all-zeros bitmask (`allTokensBlocked`).

**CONFIRMED BUG (verified by reading `GuidedGeneration/TokenizerInfo.swift`): the `stopTokenIds:` parameter is dead.**
`TokenizerInfo`'s only initializer is
```swift
public init(vocabulary: [String], vocabType: VocabularyType = .raw, addPrefixSpace: Bool = false)
```
— there is no `stopTokenIds` parameter and no other sink for it. `ConstrainedGenerationSession.init(jsonSchema:vocabulary:vocabType:stopTokenIds:)` accepts the array, documents it as *"xgrammar allows these only at grammar-terminal states"*, and then calls `TokenizerInfo(vocabulary:vocabType:)` **without forwarding it**. Same for the `tokenizer:vocabSize:` and `schemaPath:` inits. `ConstrainedDecodingStrategy.createSession` computes `singleTokenStops` and passes them in — they are silently discarded. This is very likely why commit `cba2c84` needed *"defense in depth"* (stopping on `isTerminated` in the decoder loop **and** adding `endoftext` to the tokenizer-config stop-token patterns) rather than relying on xgrammar's stop-token handling.

Supporting types:
```swift
public final class TokenizerInfo {
    public let vocabulary: [String]; public let vocabularySize: Int
    public let vocabType: VocabularyType; public let addPrefixSpace: Bool
}
public actor TokenizerInfoCache {
    public func getOrCreate(modelName: String, vocabulary: [String], vocabType: VocabularyType = .byteLevel) -> TokenizerInfo
    public func clear()
}
public enum VocabularyType: Sendable { case raw; case byteFallback; case byteLevel }
// → XGRAMMAR_VOCAB_RAW / XGRAMMAR_VOCAB_BYTE_FALLBACK / XGRAMMAR_VOCAB_BYTE_LEVEL
```
Note the default-value mismatch: `TokenizerInfo.init` defaults `vocabType` to `.raw`, while `ConstrainedGenerationSession` and `TokenizerInfoCache` default to `.byteLevel`. Constructing `TokenizerInfo` yourself and passing it to `init(jsonSchema:tokenizerInfo:)` will silently use RAW vocab semantics unless you pass `.byteLevel` explicitly. `TokenizerInfo.init` also `preconditionFailure`s (crashes) on a NULL handle from the C bridge: *"Failed to create xgrammar TokenizerInfo: invalid vocabulary (N tokens)"*.
Vocabulary extraction fills `tokenizer.convertIdToToken(i) ?? ""` for `0..<vocabSize` — *"xgrammar handles empty strings for missing token IDs; many tokenizers have gaps in their ID space, so nil here is expected, not an error."*
Masking sets disallowed logits to `-.infinity` (Float) / `-Float16.greatestFiniteMagnitude` (Float16); the bit loop short-circuits fully-set words (`0xFFFF_FFFF`) and fully-clear words.

### 12.3 `ConstrainedDecodingStrategy`
```swift
public init(jsonSchema: String, vocabSize: Int? = nil)
public func decode(from:tokenizer:inferenceEngine:samplingConfiguration:options:stopSequences:) async throws -> ConstrainedDecodedSequence
```
- Per-step options are hardcoded: `InferenceOptions(maxTokens: 1, includeLogits: true)` → requires an engine with `supportsLogits` (sequential / static-shape / VLM), **never** the pipelined GPU engine.
- Default `maxTokens` when `options.maxTokens == nil` is **512**.
- Calls `inferenceEngine.reset()` eagerly before returning the sequence.
- Only single-token stop sequences reach xgrammar: *"Warning: Multi-token stop sequences not supported by xgrammar, using single-token stops only"*.
- `deriveVocabSize(from:)` binary-searches `convertIdToToken` over `[0, 524288)` when no explicit vocab size is given.
- Per-step: run 1 inference step → `session.applyMask(&maskedLogits)` → `CompositeSampler.sample(from:&maskedLogits, config:)` → `session.acceptToken(token)`; a rejected token ends the stream.
- Fix from `cba2c84`: when the grammar terminates after accept, return `nil` **before** emitting the terminal token's decoded text — *"This prevents ANY special token from leaking into structured output, regardless of whether it's in the stop sequences list."*

FM path: `CoreAIExecutor.respondConstrained` JSON-encodes the FM `GenerationSchema` (`try JSONEncoder().encode(schema)`) and feeds the string to `ConstrainedDecodingStrategy(jsonSchema:vocabSize:)`. If the engine lacks logits it throws `unsupportedCapability(.guidedGeneration)` with debugDescription *"This model's inference engine does not support guided generation (constrained decoding requires per-step logits)."*

CLI: `llm-runner --json-schema '{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}'` (or a file path).

---

## 13. Text generation façade (non-FM path)

```swift
let generator = try await TextGeneratorBuilder()
    .withInferenceEngine(inferenceEngine)
    .withSampling(configuration: samplingConfiguration)
    .withDecoding(type: .vanilla, parameters: DecodingParameters())
    .withTokenizer(tokenizer)
    .build()

let text = try await generator.generate(input: .prompt("Hello"), maxTokens: 50, stopSequences: nil)
let (text, logits) = try await generator.generateWithLogits(input: .rawText("…"), maxTokens: 50)
let result = try await generator.evaluateContinuation(context: ctx, continuation: cont)
```
```swift
public enum Input: Sendable { case rawText(String); case prompt(String); case tokens([Int]) }
public struct PromptUtils {
    public static func maybeApplyTokenizerChatTemplate(_ input: Input, tokenizer: any Tokenizer) throws -> [Int]
}
public enum DecodingType { case vanilla }        // only one strategy in the factory
public struct GenerationResult: Sendable { public let text: String; public let tokenId: Int32; public let rawLogits: [LogitsScalarType]? }
public struct StopSequences: Sendable {
    public let sequences: [[Int32]]; public let maxLength: Int
    public init(sequences: [[Int32]])
    public init(for tokenizer: any Tokenizer, additionalSequences: [[Int32]] = [], additionalEosTokenIds: [Int32] = [])
    public func matches(recentTokens: [Int32]) -> Bool
    public func matchedSequence(recentTokens: [Int32]) -> [Int32]?
}
```
`evaluateContinuation` runs `generate(with: contextTokens, …, InferenceOptions(maxTokens: contTokens.count, includeLogits: true, forcedContinuation: contTokens))` between two `reset()`s → for MMLU-style `P(continuation|context)`.
CLI equivalent: `--continuation "…" --apply-chat-template false --print-logits` (errors: `ContinuationEvaluationError.requiresDisabledChatTemplate`, `.requiresLogitsOutput`, `.emptyContinuation`, `.rawTokensNotSupported`).

`PromptInput` / `PromptInputResolver` handle `--prompt` / `--prompt-file` / `--raw-tokens` mutual exclusion (`PromptInputError.mutuallyExclusive`, `.fileNotFound`). Raw-token JSON shape: `{"tokens": [1, 2, 3, ...]}`.

---

## 14. Other Swift modules

### `CoreAIImageSegmenter` (product `CoreAISegmentation`)
```swift
public struct ImageSegmenter {
    public init(engine: CoreAISegmentationEngine, tokenizer: CLIPTokenizer? = nil) throws
    public init(engine: CoreAISegmentationEngine, tokenizerFolder: URL?) throws
    public func warmup() async throws
    public func segment(image: CGImage, prompt: String) async throws -> [...]
    public func segment(image: CGImage, pointQuery: PointQuery) async throws -> [...]
}
public struct PointQuery { /* points with labels: .boxTopLeft, .boxBottomRight, …; also queries: [[Point]] */ }
```
README (`models/sam3/README.md`) usage:
```swift
import ImageSegmenter
let segmenter = try await ImageSegmenter(resourcesAt: "coreai-models/exports/sam3_lite_336_w4_static")
let segments = try await segmenter.segment(image: cgImage, prompt: "cat")
```
> ⚠ The README's `import ImageSegmenter` / `ImageSegmenter(resourcesAt:)` does **not** match the module name (`CoreAIImageSegmenter`, product `CoreAISegmentation`) or the initializers in the source. Treat the README snippet as aspirational/stale.

SAM3 iOS lite export splits into three functions (from `models/sam3/README.md`):
| Function | Compression | Inputs | Outputs |
|---|---|---|---|
| `image_encode` | 4-bit k-means palettization (gs=32) + fp16 | `pixel_values` | `backbone_features` |
| `text_encode` | 6-bit k-means palettization (gs=8) + fp16 | `input_ids` | `text_features` |
| `detect` | fp16 (no weight compression) | `backbone_features`, `text_features` | `pred_masks`, `pred_boxes`, `pred_logits`, `presence_logits` |
Referenced WWDC26 session: **"Dive into Core AI model authoring and optimization"** — `https://developer.apple.com/videos/play/wwdc2026/325/`.

### `CoreAISpeech`
```swift
public actor SpeechModel {
    public init(resourcesAt url: URL, decoder: any SpeechDecoder = WhisperDecoder(), melConfig: MelConfig = .whisper) async throws
    public func transcribe(audioURL: URL) async throws -> String
    public func transcribe(pcm: [Float]) async throws -> String
}
```
Bundle = directory with `encoder.aimodel` + `decoder.aimodel`. Encoder contract: input `input_features`, output `encoder_hidden_states`, function `main`. `MelSpectrogram.loadAndResample(url, targetSampleRate: 16_000)` + `MelSpectrogram.fromPCM(pcm)`; Whisper mel is 128 bins × 3000 frames. Legacy monolithic path uses `decoder_input_ids` + `logits` and `GenerationConfig.whisper` (`forcedPrefix`, `eotToken`, `maxDecodeSteps`); prefix token 50258.

### `CoreAIDiffusionPipeline` (product `CoreAIDiffusion`)
Files: `Pipelines/{Pipeline,PipelineConfiguration,PipelineDescriptor,PipelineDescriptor+CoreAI,StableDiffusionPipeline,SD3Pipeline,Flux2Pipeline(+Resources)}.swift`, `Schedulers/{Scheduler,SchedulerMath,PNDMScheduler,DPMSolverMultistepScheduler,DiscreteFlowScheduler}.swift`, `Components/{Components,CoreAIDenoiser,CoreAILatentCodec,CoreAITextEncoder,CoreAIDiffusionModelFunction,CoreAIComponentError}.swift`, `RNG/{RandomSource,NumPyRandomSource,TorchRandomSource,NvRandomSource}.swift`, `Tokenizers/BPETokenizer(+Reading).swift`.
Usage (from model READMEs):
```swift
import CoreAIDiffusionPipeline
let pipeline = try await StableDiffusionPipeline.load(from: modelURL)
let config = PipelineConfiguration(prompt: "a photograph of an astronaut riding a horse",
                                   stepCount: 20, guidanceScale: 7.5, schedulerType: .dpmSolverMultistep)
let result = try await pipeline.generateImages(configuration: config,
    progressHandler: { progress in print("Step \(progress.step)/\(progress.totalSteps)"); return true })
let image = result.images.first!
```
```swift
let pipeline = try await Flux2Pipeline(from: modelURL)   // auto-detects best mode from available components
let config = PipelineConfiguration(prompt: "a photo of a cat", stepCount: 4, guidanceScale: 1.0, schedulerType: .discreteFlow)
```
Recent fixes: `aeb6ae3` "Fix diffusion GPU memory leak: reuse InferenceFunction (#110)", `917dc99` "Fix SD text encoder crash: infer sequence length from model (#103)", `2d9497a` "Align diffusion bundles with metadata.json v0.2 schema (#33)", `ca4fa50` "Flux2 Updates to Improve Image Quality (#120)".

### `CoreAIShared`
- `Bundle/`: `ModelBundle`, `BundleKind`, `FunctionMap`
- `Image/`: `CGImageUtils`, `ImagePreprocessor` (+ `ImageStrategy`)
- `Logger/CLILogger` (`public static var level: Int`, atomic)
- `Runtime/`: `ResourceManaging`, `NDArray+Helpers` (`fillNDArray`, `readNDArray`, `flattenAsFloat`), `FileSize` (`recursiveFileSizeInBytes()`), `ModelStructure` / `PreparedModel` / `GraphNames`

```swift
public enum ImageStrategy: String, Codable, Sendable { case stretch; case centerCrop = "center_crop"; case pad }
public struct ImagePreprocessor: Sendable {
    public init(targetSize: CGSize, mean:(CGFloat,CGFloat,CGFloat), std:(CGFloat,CGFloat,CGFloat), rescaleFactor: CGFloat)
    public static let gemma3 = …   // 896×896, ImageNet mean/std
    public static let clip   = …   // 336×336, CLIP mean/std
    public func preprocess(imageURL: URL) throws -> (Data, Int, Int)   // Float32 RGBA [H,W,4]; caller transposes to NCHW
}
```
Strategy semantics (`models/vlm/README.md:53-59`):
| Strategy | Behavior | Use when |
|---|---|---|
| `stretch` | Resize directly to target size | Default. Works for most models. |
| `center_crop` | Shortest-edge resize, then center crop | CLIP-based vision towers (FastVLM) |
| `pad` | Longest-edge resize, zero-pad remainder | Models expecting preserved geometry |

### `CoreAIObjectDetector`
`ObjectDetector.swift`, `DetectionOutputs.swift`, `DetectionPostprocessor.swift`. Commits: `dd124a8` "Dynamic and Batch Support for Object Detector (#29)", `f9e9357` "change object detector input array creation to use span (#93)".

---

## 15. `skills/` — agent-skill plugin (enumerated)

Layout:
```
.claude-plugin/marketplace.json          # marketplace "coreai-models" → plugin "coreai-skills" source ./skills
skills/.claude-plugin/plugin.json        # Claude Code plugin manifest
skills/.codex-plugin/plugin.json         # Codex plugin manifest (skills: "./skills/", interface{…}, capabilities ["Read","Write"])
skills/gemini-extension.json             # Gemini CLI extension manifest
skills/skills/working-with-coreai/SKILL.md              (+ references/guidance.md)
skills/skills/model-authoring/SKILL.md                  (+ references/{neural_engine_rules,gpu_rules,common_issues}.md)
skills/skills/model-compression-exploration/SKILL.md    (+ references/{compression_patterns,size_estimation,experiment_runner,output_report}.md,
                                                            scripts/{compression_metrics.py,quality_metrics.py})
```
Plugin identity: name `coreai-skills`, version `0.1.0`, author Apple, keywords `["coreai","on-device-ai"]`.

Install (README.md:67-125):
```
# Claude Code
/plugin marketplace add git@github.com:apple/coreai-models.git
/plugin marketplace add /path/to/coreai-models
/plugin install coreai-skills@coreai-models

# Codex CLI
codex plugin marketplace add https://github.com/apple/coreai-models
codex plugin marketplace add /path/to/coreai-models
codex   # then /plugins → coreai-models tab → coreai-skills → Install

# Gemini CLI
gemini extensions install /path/to/coreai-models/skills
```

### 15.1 `working-with-coreai`
YAML frontmatter description triggers on: *"coreai-torch, TorchConverter, coreai-build, AIModel, AIProgram, .aimodel, or wants to export/compile/run a PyTorch model on Apple silicon (iPhone, iPad, Mac) … 'deploy on device', 'optimize for on-device performance', onboarding new models to Core AI, or choosing between iOS and macOS deployment paths."*

Pipeline it teaches:
```
1. AUTHOR   → Skill("coreai-skills:model-authoring")
2. COMPRESS → Skill("coreai-skills:model-compression-exploration")
3. EXPORT   → coreai-torch docs
4. COMPILE  → coreai-build CLI
5. RUN      → CoreAI framework / coreai Python API
```
Doc URLs it points at (all appear here for the first time in this corpus):
- `https://apple.github.io/coreai-torch/index.html`
- `https://developer.apple.com/documentation/coreai`
- `https://developer.apple.com/documentation/coreai/compiling-core-ai-models-ahead-of-time`
- `https://apple.github.io/coreai-torch/main/coreai-core`
- `https://apple.github.io/coreai-torch/guides/composite-ops.html`, `…/guides/externalization.html`, `…/api/composite-ops.html`
- `https://apple.github.io/coreai-optimization/introduction/how_to_use_coreaiopt.html`, `https://apple.github.io/coreai-optimization/llms-full.txt`

Minimal export snippet it ships:
```python
import torch
from coreai_torch import TorchConverter, get_decomp_table

model = MyModel().eval()
ep = torch.export.export(model, args=(torch.randn(1, 3, 224, 224),))
ep = ep.run_decompositions(get_decomp_table())

program = (
    TorchConverter()
    .add_exported_program(ep, input_names=["image"], output_names=["logits"])
    .to_coreai()
)
program.optimize()
program.save_asset("model.aimodel")
```
Swift run snippet:
```swift
import CoreAI
let model = try await AIModel(contentsOf: modelURL)
guard let fn = try model.loadFunction(named: "main") else { return }
var input = NDArray(shape: [1, 3, 224, 224], scalarType: .float32)
var view = input.mutableView(as: Float32.self)
var outputs = try await fn.run(inputs: ["image": input])
let result = outputs.remove("logits")?.ndArray
```
Python run snippet:
```python
from coreai.runtime import AIModel, NDArray
import numpy as np
model = await AIModel.load("model.aimodel")
fn = model.load_function("main")
outputs = await fn({"image": NDArray(np.random.randn(1, 3, 224, 224).astype(np.float32))})
logits = outputs["logits"].numpy()
```
PSNR acceptance table:
| Scenario | Expected PSNR | Investigate if below |
|---|---|---|
| float32 end-to-end | > 70 dB | 60 dB |
| fp16 on-device | > 50 dB | 40 dB |
| 4-bit palettized | ~40 dB | 30 dB |

`references/guidance.md` platform rules: iOS *"Keep models under 2 GB"*; macOS *"Leave at least 6 GB of RAM headroom"*; use `os_proc_available_memory()` at runtime; use `.default` specialization options unless you deliberately pin a compute unit.

### 15.2 `model-authoring`
Empirical rules for Neural Engine vs GPU. At-a-glance table:
| Aspect | Neural Engine | GPU |
|---|---|---|
| Tensor layout | BC1S `(B, H*D, 1, S)` | Standard `(B, S, D)` |
| Projections | `nn.Conv2d(kernel_size=1)` | `nn.Linear` (fused QKV) |
| Embedding shape | `(V, 1, D)` — externalized | standard `nn.Embedding` |
| Attention | Per-head sequential | Fused native SDPA |
| Float precision | fp16 only — no fp32 literals anywhere | fp16 weights, fp32 intermediates OK |
| Shapes | Fully static | Dynamic supported |
| Weight conversion | `unsqueeze(-1).unsqueeze(-1)` | none |

KV cache conventions table:
| Compute unit | Cache shape | Seq dim | Pattern |
|---|---|---|---|
| Neural Engine | `[n_layers, B, H_kv*D, 1, max_S]` | 4 | Readonly functional I/O — model has no cache writes, returns new K/V as outputs |
| GPU | `[n_layers, B, H_kv, max_S, D]` | 3 | Stateful export wrapper — `register_buffer` + `hoistToArg` |

Verification gates: re-authored vs source > 70 dB; NE-layout vs GPU-layout > 70 dB; compiled vs torch ≥ 40 dB; after 4-bit palettization ≥ 35 dB.
Palettization sizing: 8-bit ≈ 2× / >55 dB (flag <50); 4-bit ≈ 4× / ~40 dB (flag <35); 2-bit ≈ 8× / 25-35 dB ("usually unacceptable").

**`references/neural_engine_rules.md` highlights (479 lines):**
- Max tensor rank **5**; dtypes fp16/int8/int16 (fp32 falls back to GPU/CPU); fully static shapes.
- Last axis must be contiguous and **64-byte aligned**; a singleton last axis costs **32× memory at fp16, 64× at int8**; keep ≥32 fp16 elements; prefer powers of two.
- BC1S conversions:
  ```python
  x = x.permute(0, 2, 1).unsqueeze(2)        # (B,S,D) → (B,D,1,S)
  x = x.squeeze(2).permute(0, 2, 1)          # back
  def gpu_to_bc1s(x): B,H,S,D = x.shape; return x.permute(0,1,3,2).reshape(B, H*D, 1, S)
  def bc1s_to_gpu(x, n_heads, head_dim): B,_,_,S = x.shape; return x.reshape(B,n_heads,head_dim,S).permute(0,1,3,2)
  ```
- Conv2d transpose bookkeeping: `x = x.transpose(-3, -1); y = self.proj(x); y = y.transpose(-3, -1)`.
- Weight conversion: Linear `[O,I]` → Conv2d `[O,I,1,1]`; norm `(D,)` → `(1,D,1,1)`.
- Conv stride: only prime factors 2 and 3 (4,6,8,9,12,16,24,32); palettized kernels support stride ≤ 2. Large kernel decomposition `k_fused = k1 + k2 - 1`. Dilation factorization into 2/3 chains. Pooling stride 2 or 4.
- **Causal mask is `(1, key_seq, 1, query_seq)` — transposed from GPU** — and uses `-40000.0`, *"Neural Engine hardware does not handle IEEE `-inf` correctly in softmax."* NE also computes `K @ Q` rather than `Q @ K^T`.
- Per-head attention einsums: `torch.einsum("bchq,bkhc->bkhq", q_h, k_kv)` then `torch.einsum("bkhq,bkhc->bchq", attn, v_kv)`.
- RoPE: precompute cos/sin **outside** the exported model, pass as `(1, head_dim, 1, S)`; indexing a 2-D table with `position_ids` produces `gather_nd` 3-D output NE rejects.
- Readonly KV pattern: **return `key_rope`, not raw `new_k`** — *"If you cache pre-RoPE K, the next call attends to stale non-RoPE-encoded keys → PSNR collapses to ~20 dB."*
- Chunked prefill `CHUNK = 64`; seam rule offset = `chunk_start` not `chunk_end`; *"For prefill > ~50 tokens, use chunked prefill (S_q=64) or fp32 KV cache tensors in Python"* (fp16 drift).
- NE entrypoints table: `extend_{ctx}_{len}` (logits + updated KV), `prompt_opt_{ctx}_{len}` (KV only, no logits), `gather_embeddings_{N}`. *"All functions compile from **one dynamic `torch.export`** via Core AI shape specialization."*

**`references/gpu_rules.md` highlights (297 lines):** fused QKV `nn.Linear(dim, n_heads*hd + 2*n_kv_heads*hd, bias=False)`; fused Q/K norm+RoPE before splitting; MLP computes `up_proj` **before** `gate_proj` (*"reversed from many reference implementations but yields better GPU utilization"*); `mutable_arg_action="hoistToArg"` in `LegalizeToCoreOptions`; `coreai::mutable_slice_update` custom op explanation; MoE via `SwitchLinear`/`SwitchGLU`/`GatherMM` with weights stacked to `(1, num_experts, out, in)`; meta-device init + `load_state_dict(..., assign=True)` + per-layer safetensors streaming.

**`references/common_issues.md` (176 lines)** — a debugging cookbook. Selected entries:
- `si32` not `i32` for input JSON descriptors.
- Filter `torch.export` input specs to `{InputKind.USER_INPUT, InputKind.BUFFER}` before naming.
- `nn.functional.silu(x)` lowers to `mps.cast(→f32) + mps.swish(f32) + mps.cast(→f16)` (3 invalid ops on NE) → use `gate_pre * torch.sigmoid(gate_pre)`.
- Call `.contiguous()` on all tensors before wrapping in `NDArray` — *"The runtime reads raw memory as if contiguous, ignoring tensor strides."*
- `xcrun coreai-build compile model.aimodel --preferred-compute neural-engine` when the model runs on CPU.
- `InferenceFunction.__call__` uses `**kwargs` — `await runner(**inputs)`, not `runner(inputs_dict)`.
- Output dict key order is non-deterministic → identify outputs by shape, not index.
- `torch.tanh` → `2 * torch.sigmoid(2 * x) - 1` for AdaLN on NE.
- Patch `ROPE_INIT_FUNCTIONS["default"]` when HF `post_init()` fails on missing `rope_parameters`.

### 15.3 `model-compression-exploration`
Drives ~30 main-sweep + ~30 refinement `coreai_opt` configs.
- Step 3 timing probe: `QuantizerConfig.presets.w8()` (graph mode default); on `Quantizer.prepare` failure fall back to `QuantizerConfig.presets.w8(execution_mode=ExecutionMode.EAGER)` **for the whole sweep**. `KMeansPalettizerConfig.presets.w6()` = 6-bit, per-grouped-channel, group_size=16; **palettization is eager-only**.
- Groups: **1a** channel-structured quant = `{int8,int4} × {symmetric, asymmetric, symmetric_with_clipping}` (6); **1b** block-structured = `{block_size 16,32,128} × {3 qschemes}` int4 per-block (9); **2** palettization = `{(8-bit per-tensor), (6-bit per-tensor), (6-bit gs 4/8/16), (4-bit gs 4/8/16)} × {enable_per_channel_scale True/False}` (15).
- Preset anchors: `presets.w8()`/`w4()` (per-channel symmetric), `presets.w4_per_block(block_size=32)`, `KMeansPalettizerConfig.presets.w8()/w6()/w4()`.
- Refinement: filter PSNR < 10 dB / IoU < 0.1, pick 95th & 75th percentile seeds, 5 layer-skip variants each via `set_module_name` overrides.
- Do **not** call `finalize()` — *"Calibration is not needed for weight-only compression."*
- Pitfalls: per-block/per-grouped-channel **silently skip** layers whose weight dim isn't divisible (pre-check with `check_divisibility()`); scale/ZP overhead 5-15% at 2-4 bit fine granularity; 8-bit per-channel LUT stores 256 × fp16 entries per output channel; at `block_size=16` + int4 the effective width is ~5 bits.
- Output JSON record shape (verbatim):
  ```json
  {"group":"2","config":{"name":"palette_grouped_gs4_6bit_pcs0_skip-Embedding","path":"path/to/config"},
   "time_taken":1000,
   "output_quality_metrics":[{"name":"bbox","metric":"iou","value":0.7},{"name":"logits","metric":"psnr","value":16}],
   "compression_metrics":{"average_bitwidth":5,"compression_ratio":1.7,"theoretical_model_size":402}}
  ```
- Report: exactly 5 configs per group spanning the frontier; columns `Config | PSNR (dB) | Avg Bitwidth | Compression Ratio`; scatter plot saved as `compression_exploration.png`.
- Parallelization: one subagent per group appending to a shared `results.jsonl`; the main agent uses `/loop 5m` for progress. Bundled scripts `scripts/compression_metrics.py` (theoretical size, average bitwidth, divisibility, parametrize walk) and `scripts/quality_metrics.py` (PSNR/SNR/IoU + dispatcher).

---

## 16. Tests as documentation

Swift test suites (`swift/Tests/`), with `coreai-models-Package.xctestplan`:
- `LanguageModelsTests/` — 25 files. Highlights: `UnifiedGenerationAPITests` (737 lines; `InferenceOutput`, `InferenceOptions`, generate defaults, maxContextLength clamping, multi-turn `generate(maxTokens:1)` no-deadlock, generate→reset→generate, `forcedContinuation` exactness, partial reset parity **"reset(to:) produces identical output vs full re-generate — 20 random iterations"**, `TokenHistory`), `KVCacheStrategyTests` (defaults: fixedSize→maxContextLength, growing→256, auto→nil, explicit override precedence), `MPSGraphSamplerTests` (827 lines), `CompositeSamplerTests` (500), `KVCacheTests` (423), `ContinuationEvaluationTests`, `CoreAIPipelinedTests`, `PipelineGateTests`, `CancelAPITests`, `GenerationStopReasonTests`, `StopSequencesTests`, `ThinkTagParserTests`, `MinimalTokenizerTests` + `TokenizerIntegrationTests` (use the checked-in `Resources/MinimalTokenizer/{tokenizer.json,tokenizer_config.json}`), `ModelPathsTests`, `LanguageBundleTests`, `ModelResourcesTests`, `LogitsWriterTests`, `ProfileSpanTests`, `TimingTests`, `PerformanceMetricsTests`, `GraphSelectionTests`, `EngineOptionsTests`, `ModelConfigHandlerTests`, `PromptProcessingTests`, `VLMProtocolTests`, `PublicInterfaceTests`.
- `GuidedGenerationTests/ConstrainedGenerationSessionTests` — 378 lines; tests `firstTokenMustBeOpenBrace`, `enumConstraint`, `integerConstraint`, `nestedObjectSchema`, `arraySchema`, `allTokensBlockedTermination`, `applyMask*` (Float and Float16), `reset`/`multipleResets`, `resetAfterCompletion`.
- `DiffusionPipelineTests/` — `SchedulerTests`, `SD3ParityDataTests`, `ComponentTests`, `PipelineDescriptorTests`, `MultiOutputModelFunctionTests`.
- `ImageSegmenterTests/`, `ObjectDetectorTests/`, `CoreAISharedTests/` (`ImagePreprocessorTests`, `CGImageUtilsTests`, `ModelBundleTests`, `FileSizeTests`).

Python tests (`python/tests/`):
- `test_model_units/` (**the only suite CI runs**): `test_model_registry.py`, `test_models/test_registry.py`, `test_models/test_ios_layers/{mistral,qwen2,qwen3}.py`, `test_models/test_macos_layers/{qwen2,qwen3,qwen3_moe,mixtral,gemma3_text,gpt_oss}.py` (up to 1457 lines), `test_models/test_macos_layer_counts/*`, `test_primitives/test_macos/{rope,rms_norm,cache,switch}.py` + `_random_input_models.py`, `test_primitives/test_ios/{embedding,rope,sdpa,cache}.py`.
- `test_model_conversion/`: `test_macos_models.py` (586), `test_ios_models.py`, `test_infra.py` — real HF downloads, **not in CI**.
- `_runner_infra/` — a mini cross-framework harness: `run/runners/{torch_runner,mlx_runner,coreai_runner}.py`, `export/exporters/{torch_exporter,mlx_exporter,coreai_exporter}.py`, `common/utils/{torch,coreai,mlx}/`, typed contracts in `common/types/{dependency,run,source,export}_types.py`. **Note: MLX appears here as a comparison backend** (`mlx_runner.py`, `mlx_exporter.py`, `common/utils/mlx/tensor.py`).
Pytest config: `testpaths=["tests"]`, `--strict-markers --strict-config --verbose`, marker `slow`.

Commit `2382bb2` "Enable running `iOS` and `macOS` authored models on CUDA GPUs (#99)" — the Python model definitions are device-portable for testing.

---

## 17. Consolidated gotchas / footguns

1. **`.aimodel` is a directory.** `PreparedModel.resolveCoreAIModelURL` and `recursiveFileSizeInBytes()` both assume this; `shutil.rmtree(aimodel_path)` on overwrite in `pipeline.py` confirms it.
2. **Point tools at the bundle *directory*, not the asset.** Otherwise `BundleError.pointedAtModelAsset`.
3. **`metadata_version` must be exactly `"0.2"`.**
4. **After `xcrun coreai-build compile`, you must hand-edit `metadata.json`'s `assets`** to the `.aimodelc` filename.
5. **Pipelined GPU engine cannot produce logits.** No guided generation, no `forcedContinuation`, no MMLU-style eval. `isGuidedGenerationSupported` falls back to `variant != "coreai-pipelined"` before the engine loads.
6. **Sampling config is immutable for the lifetime of a pipelined generation.** Changing temperature or crossing the greedy boundary mid-generation throws; reset first.
7. **FM `GenerationOptions` only forwards `temperature`** in this adapter. topK/topP/minP require the non-FM `TextGenerator`/engine API or the CLI.
8. **`SamplingConfiguration.init` uses `precondition`, not `throws`.** Bad values crash in release-with-checks builds.
9. **`EngineFactory.autoDetectVariant` `preconditionFailure`s** on non-LLM model structures (e.g. a segmenter asset) — the compatibility path throws, but the *auto* path crashes.
10. **`.fixedSize` KV cache pre-allocates `maxContextLength`** — multi-GB on 40K/262K-context presets, and slows every decode step.
11. **`.chunked` KV cache strategy is accepted but silently falls back to `StaticKVCache`.**
12. **`--dynamic-sized-kvcache-gpu`** appears only in Swift error strings; no such flag exists in this repo's Python exporters.
13. **iOS export is only wired for mistral / qwen2 / qwen3.** Gemma3, Mixtral, GPT-OSS, Qwen3-MoE, Qwen3-VL are macOS-only.
14. **Gemma 3 requires `--compute-precision bfloat16`.** GPT-OSS ships pre-quantized MXFP4 and uses `--compression none`.
15. **Gated HF models** (`google/gemma-3-*`, `stabilityai/stable-diffusion-3.5-medium`, `facebook/sam3`) need `brew install hf && hf auth login --token <TOKEN>`.
16. **Calibration path needs `datasets` + `tqdm`, which are NOT in `[project.dependencies]`.** `get_c4` raises ImportError telling you to `pip install datasets tqdm`.
17. **Registry `compression_config` YAMLs are source-tree-only** — a pip-installed wheel can't resolve them.
18. **`coreai.llm.eval` is a stub that always errors.**
19. **`xgrammar` is pinned to branch `main`** in Package.swift — non-reproducible builds.
20. **`coreai-core==1.0.0b2` is a beta pin** and `[tool.uv] prerelease = "allow"` + `index-strategy = "unsafe-best-match"` are set at workspace level.
21. **`swift run` defaults to Debug**; `llm-benchmark` prints a warning and the docs always say `-c release`.
22. **`zeroFill` on a 32K-context Qwen3 KV cache took ~6 s per `reset()` under `-Onone`** before the hand-rolled loop — build optimized.
23. **`drain()` on both sequential and pipelined engines `fatalError`s after 5 s** of busy-waiting.
24. **Multi-token stop sequences are dropped** in constrained decoding (xgrammar limitation, logged as a warning).
25. **Mistral tool calls use `"\n"` as a synthetic close marker** — a multi-line tool-call JSON would break the parser.
26. **`ModelBundle.verify()` is only called by `llm-runner`**, not by `CoreAILanguageModel.init`.
27. **Neural Engine mask must use `-40000.0`, never `-inf`**, and is transposed relative to GPU.
28. **NE readonly KV must cache post-RoPE keys** or PSNR collapses to ~20 dB.
29. **iOS `position_ids` is `uint16`** in the exported graph while macOS uses `int32`.
30. **`models/sam3/README.md` Swift snippet (`import ImageSegmenter`, `ImageSegmenter(resourcesAt:)`) does not match the shipped module/API.**

---

## 18. Notable recent commits (`git log --oneline -50`, newest first)

| SHA | Subject | Why it matters |
|---|---|---|
| `5ed9981` | Move away from deprecated FM API (#123) | `LanguageModelCapabilities(capabilities:)` → `(_:)` |
| `102f832` | Polish a few APIs, method names… (#122) | `CoreAIRunner(bundle:)`, `PerformanceMetrics.record*`, `CLILogger.level`, `Duration` ext un-published |
| `aff0bb2` | Fix pipelined sampling corruption: per-call execution descriptor (#121) | Garbled text at temperature > 0 |
| `cba2c84` | Fix guided generation: stop on grammar termination, include `<\|endoftext\|>` (#117) | Special-token leakage into structured output |
| `ca4fa50` | Flux2 Updates to Improve Image Quality (#120) | |
| `04a3fd6` | Stop pipelined generation when consumer drops the stream (#113) | Cancel-and-replace contract on all engines |
| `2607aea` | Add configurable VLM image preprocessing strategy (#108) | `image_strategy`, `include_image_info`, `--image-strategy`, `--image-info` |
| `aeb6ae3` | Fix diffusion GPU memory leak: reuse InferenceFunction (#110) | |
| `ace0dc6` | Fix Qwen3-VL normalization: use 0.5/0.5/0.5 from checkpoint (#105) | |
| `917dc99` | Fix SD text encoder crash: infer sequence length from model (#103) | |
| `d967fa3` | Adding SAM3 iOS Model (#106) | `models/ios/sam3/*` |
| `162ee99` | VLM: fix EmbeddedInput shape handling, error recovery, parallel loading (#79) | |
| `d5a78c8` | VLM support for FoundationModels protocol (#97) | `CoreAIVisionLanguageModel` |
| `2382bb2` | Enable running iOS and macOS authored models on CUDA GPUs (#99) | |
| `85e2f2d` | Fresh export needs tokenizer patterns (#95) | |
| `5624cef` | Add AIModel metadata for Qwen3-VL-2B-Instruct (#94) | |
| `eb3998e` | Lazy runner design: defer engine load (#91) | `ModelResources`, `LoadMode.lazy/.eager` |
| `7bd9d32` | Use views in consuming manner, not mutating (#89) | `consume` on `MutableViews` |
| `3f38f50` | Fix missing await on generate() in ConstrainedGenerator (#86) | |
| `9962781` | Make generate() async to serialize back-to-back turns (#80) | |
| `e203a0d` | Default max-context-length of 4096 for LLM iOS platform exports | `IOS_DEFAULT_MAX_CONTEXT_LENGTH` |
| `c2a0274` | bump coreai-core, coreai-torch, coreai-opt versions (#78) | current pins |
| `1303957` | VLM: wire performance instrumentation and logits output (#72) | |
| `78413ae` | Use `NDArrayDescriptor.resolvingDynamicDimensions` instead of modifying `.shape` directly (#74) | Core AI API guidance |
| `de896bf` | VLM model support: Qwen3-VL-2B export (#68) | |
| `9e1ffa5` | Add VLM inference infrastructure: engine, protocol, CLI support (#65) | |
| `1eb2dae` | Optimize expert selection (#69) | MoE |
| `34f0db3` | Enable multi-turn KV cache reuse by removing per-turn engine.reset() (#64) | |
| `7af7755` | Fix/mpsndarry minimum buffer size (#62) | `minimumMPSNDArrayBufferSize = 64` |
| `5a0f161` | Add speech-runner: Swift inference for Whisper model (#54) | |
| `d5804c8` | Gracefully exit when pointed at a model asset instead of a model bundle directory (#60) | `.pointedAtModelAsset` |
| `e358c84` | Fix pipeline race condition: rotate all buffers by pipeline depth (#53) | |
| `18cd896` | Add `reset(to:)`, `processedTokenCount`, and implicit prefix caching (#51) | `TokenHistory` |
| `1522e5a` | Add TopP and MinP sampling to all engines (#48) | |
| `9afe6d6` | Fix pipelined engine reset(): cancel before drain (#47) | |
| `277238e` | Remove notice file as we have adopted upstream Swift package for xgrammar (#45) | |
| `dd124a8` | Dynamic and Batch Support for Object Detector (#29) | |
| `e53b8b3` | Add `cancel()` and `isBusy` to InferenceEngine protocol (#32) | |
| `02a8edd` | Fix Gemma stop tokens: read additional EOS from tokenizer config | |
| `a43371e` | Whisper export traced with dynamic shapes (#34) | |
| `d89efa7` | **rename export backend from MLIR to CoreAI (#35)** | Explains lingering "MLIR" names (`mlir_ops.py`) |
| `2d9497a` | Align diffusion bundles with metadata.json v0.2 schema (#33) | |
| `d83f0b0` | ci: run CI on self-hosted Apple Silicon macOS runners (#30) | |
| `5ae71b2` | Use custom AsyncSequences and avoid unstructured concurrency (#24) | `InferenceOutputSequence` |
| `38990b3` | Add Bits Per Weight (BPW) info for model cards (#17) | |

---

## 19. Published quality numbers (WikiText-2 perplexity via lm-evaluation-harness, Core AI PyTorch models)

Collected from `models/*/README.md`. "BPW" marked `*` includes the INT8-per-tensor embedding.

| Model | Compression | BPW | Platform | Perplexity |
|---|---|---|---|---|
| Qwen3 0.6B | none (float16) | 16.00 | iOS | 26.16 |
| Qwen3 0.6B | Mixed 4-bit/8-bit palettized (YAML) | 5.71* | iOS | 30.90 |
| Qwen3 4B | none (float16) | 16.00 | macOS | 16.41 |
| Qwen3 4B | 4-bit quantized | 4.50 | macOS | 18.33 |
| Qwen3 4B | none (float16) | 16.00 | iOS | 16.41 |
| Qwen3 4B | Mixed 4-bit/8-bit palettized (YAML) | 4.89* | iOS | 18.80 |
| Qwen3 8B | none (float16) | 16.00 | macOS | 12.19 |
| Qwen3 8B | 4-bit quantized | 4.50 | macOS | 12.90 |
| Qwen2.5 1.5B Instruct | none | 16.00 | macOS | 12.21 |
| Qwen2.5 1.5B Instruct | 4-bit quantized | 4.50 | macOS | 14.79 |
| Qwen2.5 1.5B Instruct | none | 16.00 | iOS | 12.21 |
| Qwen2.5 1.5B Instruct | 4-bit palettized (gs 8) | 4.63* | iOS | 14.64 |
| Gemma 3 4B | none | 16.00 | macOS | 17.90 |
| Gemma 3 4B | 4-bit quantized | 4.50 | macOS | 19.28 |
| Gemma 3 12B | none | 16.00 | macOS | 11.24 |
| Gemma 3 12B | 4-bit quantized | 4.50 | macOS | 11.75 |
| Mistral 7B Instruct | none | 16.00 | macOS | 8.29 |
| Mistral 7B Instruct | 4-bit quantized | 4.50 | macOS | 8.41 |
| Mixtral 8x7B | none | 16.00 | macOS | 5.72 |
| Mixtral 8x7B | 4-bit quantized | 4.50 | macOS | 6.19 |
| Qwen3 Coder 30B-A3B | none | 16.00 | macOS | 11.06 |
| Qwen3 Coder 30B-A3B | 4-bit quantized | 4.50 | macOS | 11.90 |

Parameter counts noted in READMEs: SAM3 848M, Whisper large-v3-turbo 809M / large-v3 1.54B, SD1.5/2.1 0.9B, SD3.5-medium 2.5B, FLUX.2 Klein 4B, Mixtral 8x7B = 47B total / 13B active, Qwen3 Coder 30B-A3B = 30B/3B.

---

## 20. Source inventory (files actually read this session)

Root / config
- `README.md`, `Package.swift`, `Package.resolved`, `pyproject.toml`, `python/pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`, `.python-version`, `.spi.yml`, `.claude-plugin/marketplace.json`, `.github/workflows/ci.yml`, `uv.lock` (grep for coreai-* pins)

Swift sources
- `swift/Sources/CoreAILanguageModels/LanguageModel/CoreAILanguageModel.swift` (777 L, full)
- `swift/Sources/CoreAILanguageModels/LanguageModel/CoreAIRunner.swift`, `ModelResources.swift`, `ThinkTagParser.swift`
- `swift/Sources/CoreAILanguageModels/VLM/CoreAIVisionLanguageModel.swift` (full)
- `swift/Sources/CoreAILanguageModels/InferenceEngines/InferenceEngine.swift`, `EngineFactory.swift`, `ModelConfig.swift`, `KVCache+CoreAI.swift`, `KVCacheShared.swift`, `InferenceOutputSequence.swift`, `GenerationToken.swift`, `EmbeddedInput.swift`, `CoreAISequentialEngine.swift` (full), `CoreAIPipelinedEngine.swift` (full, 1276 L), `CoreAIStaticShapeEngine.swift` (head 140 L + public-API grep), `CoreAISequentialVLMEngine.swift` (public-API grep)
- `swift/Sources/CoreAILanguageModels/Samplers/SamplingConfiguration.swift`, `CompositeSampler.swift`, `MPSGraphSamplers.swift` (head 130 L)
- `swift/Sources/CoreAILanguageModels/Bundle/LanguageBundle.swift`, `LanguageConfig.swift`
- `swift/Sources/CoreAILanguageModels/DecodingStrategies/DecodingStrategy.swift`, `ConstrainedDecodingStrategy.swift`, `VanillaDecodingStrategy.swift` (head 120 L)
- `swift/Sources/CoreAILanguageModels/GuidedGeneration/ConstrainedGenerationSession.swift`, `XGrammarWrapper.swift`
- `swift/Sources/CoreAILanguageModels/TextGeneration/TextGenerator.swift`, `PromptProcessing.swift`
- `swift/Sources/CoreAILanguageModels/Assets/ModelPaths.swift`, `ModelShapeConfig.swift` (grep)
- `swift/Sources/CoreAIShared/Bundle/ModelBundle.swift`, `BundleKind.swift`, `FunctionMap.swift`, `Runtime/ModelStructure.swift`, `Image/ImagePreprocessor.swift` (head 80 L)
- `swift/Sources/CoreAIImageSegmenter/ImageSegmenter.swift` (head 80 L)
- `swift/Sources/CoreAISpeech/SpeechModel.swift` (head 90 L)
- `swift/Sources/Tools/llm-runner/LLMRunnerMain.swift` (full, 1096 L), `Tools/benchmark/BenchmarkMain.swift` (full), `Tools/speech-runner/SpeechRunnerMain.swift` (full), `Tools/{image-segmenter,object-detector,diffusion-runner}` (option grep)
- `swift/Tests/LanguageModelsTests/PublicInterfaceTests.swift` (full); test-name greps across `UnifiedGenerationAPITests`, `KVCacheStrategyTests`, `ConstrainedGenerationSessionTests`

Python sources
- `python/src/coreai_models/model_registry.py` (full, 1051 L)
- `python/src/coreai_models/llm/export.py` (full), `llm/eval.py` (full)
- `python/src/coreai_models/export/{_constants,presets,pipeline,macos,ios,bundle,metadata,compression}.py` (full), `export/mlir_ops.py` (head 70 L)
- `python/src/coreai_models/models/registry.py` (full), `models/base.py` (symbol grep)
- `python/src/coreai_models/primitives/macos/cache.py` (full), `primitives/{macos,ios}/__init__.py`, `primitives/ios/quantization.py` (head 60 L)
- `python/src/coreai_models/vlm/export.py` (head 120 L + CLI section 600-824)
- `python/src/coreai_models/diffusion/{export.py (head 160 L), presets.py, models.py}`

Models catalog
- `models/README.md`, `models/qwen3/README.md`, `models/gemma3/README.md`, `models/gpt_oss/README.md`, `models/mixtral/README.md`, `models/qwen3_moe/README.md`, `models/mistral/README.md`, `models/qwen2/README.md`, `models/vlm/README.md`, `models/whisper/README.md`, `models/sam3/README.md`, `models/stable-diffusion/README.md`, `models/flux2/README.md`

Skills
- `skills/.claude-plugin/plugin.json`, `skills/.codex-plugin/plugin.json`, `skills/gemini-extension.json`
- `skills/skills/working-with-coreai/SKILL.md` + `references/guidance.md`
- `skills/skills/model-authoring/SKILL.md` + `references/gpu_rules.md` + `references/neural_engine_rules.md` + `references/common_issues.md`
- `skills/skills/model-compression-exploration/SKILL.md`

Git
- `git log --oneline -50`; `git show` for `5ed9981`, `102f832`; `git log -1 --format` + `--stat` for `aff0bb2`, `cba2c84`, `04a3fd6`, `2607aea`, `eb3998e`, `18cd896`

---

## 21. Open questions / unverified

1. **`--dynamic-sized-kvcache-gpu`** — referenced in `KVCache+CoreAI.swift` and `KVCacheShared.swift` error text, but no such flag exists in `coreai.llm.export` here. Where does it live? (Possibly an internal/older exporter, or the flag was renamed.) **UNVERIFIED.**
2. **`FoundationModels` API shapes** (`LanguageModelExecutorGenerationRequest`, `…GenerationChannel`, `Transcript.Entry` cases, `LanguageModelError` payload structs, `GenerationSchema` Codable conformance) are consumed but not defined here — I only know the members this repo calls. The exact enum/struct definitions need the SDK or another agent's notes.
3. **`CoreAI` framework API** (`AIModel`, `AIModelAsset`, `AIProgram`, `InferenceFunction`, `NDArray`, `NDArrayDescriptor`, `SpecializationOptions`, `ComputeStream`, `AIModelAssetMetadata`, `HardwareConstraints`, `AllocationType`, `TensorSpec`) — same caveat. `InferenceFunction.AsyncValue(unsafeBuffer:byteOffset:scalarType:shape:strides:)` and `function.encode(inputs:states:outputViews:to:)` are used with `unsafe` expression markers, which suggests these are `@unsafe`-annotated in the SDK.
4. ~~`TokenizerInfo` / `stopTokenIds`~~ — **RESOLVED, confirmed dead parameter**: `stopTokenIds` is accepted by three `ConstrainedGenerationSession` initializers, never forwarded, and the C bridge has no stop-token entry point at all (all 14 declarations enumerated in §12.1). Only remaining question is whether upstream xgrammar's C++ `TokenizerInfo` supports stop-token ids and the bridge simply doesn't expose them.
5. **VLM model loading concurrency divergence**: `llm-runner` loads the 3 VLM assets sequentially (comment: *"to avoid runtime errors with concurrent model preparation"*) while `CoreAIVisionLanguageModel.init` uses `async let` for all three. One of the two is presumably wrong.
6. `models/edsr|clip|depth-anything|pvt|t5|wav2vec2|clap|efficient-sam|roberta|yolo/export.py` were **not** read line-by-line (only their registry entries and, for whisper/sam3, their READMEs). Their PEP-723 headers and flags are unverified.
7. `swift/Sources/CoreAIDiffusionPipeline/**` was inventoried by filename only; `Flux2Pipeline` (786 L), schedulers, and `PipelineDescriptor` JSON schema are unread.
8. `swift/Sources/CoreAIObjectDetector/**` and `CoreAIImageSegmenter/ImageSegmentationEngine.swift` (1292 L) unread beyond headers.
9. `skills/skills/model-compression-exploration/references/{compression_patterns,size_estimation,experiment_runner,output_report}.md` and `scripts/*.py` were only summarised from `SKILL.md` — the concrete `compute_average_bitwidth`, `check_divisibility`, `extract_layer_specs`, `append_record`, `status_snapshot` signatures are unread.
10. `python/tests/_runner_infra/**` MLX comparison harness (mlx_runner/mlx_exporter) unread — relevant for a "MLX vs Core AI parity" guide.
11. Whether `AIModel(contentsOf:options:)` supports `.aimodelc` directly (the `llm-runner` accepts the extension but `PreparedModel.resolveCoreAIModelURL` only maps to `.aimodel`).
12. What `COREAI_QUERY_BUCKET_SIZE` actually does at runtime — set by `--bucket-size` but never read anywhere in this repo's Swift (it's read by the Core AI framework or an unread engine path). **UNVERIFIED.**
