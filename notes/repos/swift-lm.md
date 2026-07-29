# 1amageek/swift-lm — deep dive notes

**Repo path:** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/1amageek__swift-lm`
**Clone depth:** 50 · **HEAD:** `db7a802 Add Core AI vision language model adapter` (Sat Jul 18 18:38:25 2026 +0900)
**Author:** 1amageek `<tmy0x3@icloud.com>`
**Version line:** `0.11.0-alpha.1` (Swift package), `swiftlm-coreai 0.11.0a1` (Python)

Everything below is grounded in files read in this session. Anything I could not
verify from the repo is explicitly marked **UNVERIFIED**.

---

## 0. One-paragraph summary

`swift-lm` started life as a *Metal compiler* for LLM inference on Apple Silicon
(0.10 line). In the 0.11 line it pivots to **Core AI first**: model families are
declared once in a SwiftUI-like DSL (`LMArchitecture`), normalized into a
backend-independent IR (`LMIR`), and exported as a **versioned JSON "executable
contract"** (`CoreAIExport` → `CoreAIExportDocument`, format version 2). A
*generic* Python lowerer (`python/src/swiftlm_coreai/lowering.py`) walks that JSON
and rebuilds a `torch.nn.Module` — **with no model-family dispatch in Python** —
binding weights directly out of the Hugging Face `safetensors`, then hands the
module to Apple's `coreai-torch` / `coreai-models` exporter to produce an
`.aimodel`. Two Swift runtime surfaces consume the result: `SwiftLMCoreAI`
(low-level `AIModelAsset`/`AIModel`/`InferenceFunction`/`NDArray` with explicit
mutable state) and `SwiftLMFoundationModels` (Apple's high-level
`CoreAILanguageModels` `LanguageBundle` + the brand-new
**`CoreAISequentialVLMEngine` three-asset VLM adapter**).

This is one of the very few *real, third-party* Core AI integrations available to
read — it exercises `CoreAI` (the OS framework), `CoreAILanguageModels` (the SPM
package `apple/coreai-models`, product `CoreAILM`), `coreai-torch`, `coreai-opt`,
`coreai-core`, and the `coreai-build` CLI.

---

## 1. Requirements, versions, dependency pins (exact)

### `Package.swift` (verbatim header)

`Package.swift:1-35`

```swift
// swift-tools-version: 6.4
import PackageDescription
import Foundation

let enableMetalProbes = ProcessInfo.processInfo.environment["ENABLE_METAL_PROBES"] == "1"
let metalProbeSwiftSettings: [SwiftSetting] = enableMetalProbes
    ? [.define("ENABLE_METAL_PROBES")]
    : []

let package = Package(
    name: "swift-lm",
    platforms: [.macOS("27.0"), .iOS("27.0")],
    products: [
        .library(name: "LMIR", targets: ["LMIR"]),
        .library(name: "LMArchitecture", targets: ["LMArchitecture"]),
        .library(name: "ModelDeclarations", targets: ["ModelDeclarations"]),
        .library(name: "CoreAIExport", targets: ["CoreAIExport"]),
        .library(name: "SwiftLMCoreAI", targets: ["SwiftLMCoreAI"]),
        .library(name: "SwiftLMFoundationModels", targets: ["SwiftLMFoundationModels"]),
        .library(name: "MetalCompiler", targets: ["MetalCompiler"]),
        .library(name: "SwiftLM", targets: ["SwiftLM"]),
        .executable(name: "swiftlm-ir", targets: ["SwiftLMIR"]),
        .executable(name: "lfm25-a1b-benchmark", targets: ["LFM25A1BBenchmark"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-collections.git", from: "1.4.1"),
        .package(url: "https://github.com/huggingface/swift-jinja", from: "2.3.5"),
        .package(url: "https://github.com/huggingface/swift-transformers", from: "1.3.0"),
        .package(url: "https://github.com/mattt/JSONSchema", from: "1.3.1"),
        .package(url: "https://github.com/1amageek/swift-testing-heartbeat", from: "0.1.0"),
        .package(
            url: "https://github.com/apple/coreai-models.git",
            revision: "938d0b8943b942ce66438b94ab017c5631d1aef4"
        ),
    ],
```

Notable target wiring (`Package.swift:52-66`):

```swift
        .target(
            name: "SwiftLMCoreAI",
            dependencies: ["CoreAIExport"]
        ),
        .target(
            name: "SwiftLMFoundationModels",
            dependencies: [
                .product(name: "CoreAILM", package: "coreai-models"),
                .product(name: "Tokenizers", package: "swift-transformers"),
            ]
        ),
        .executableTarget(
            name: "SwiftLMIR",
            dependencies: ["CoreAIExport", "ModelDeclarations"]
        ),
```

**KEY FINDING — two distinct Core AI module namespaces:**

| Swift module | Where it comes from | Evidence |
|---|---|---|
| `CoreAI` | **OS framework in the macOS 27 / iOS 27 SDK.** `SwiftLMCoreAI` imports it while depending on *nothing* but `CoreAIExport`. | `Sources/SwiftLMCoreAI/*.swift:1` `import CoreAI`; `Package.swift:52-55` |
| `CoreAILanguageModels` | SPM package `apple/coreai-models`, product name **`CoreAILM`** (module name ≠ product name) | `Sources/SwiftLMFoundationModels/*.swift:1` `import CoreAILanguageModels`; `Package.swift:57-62` |

`Package.resolved` pins (`Package.resolved:3-137`):

- `coreai-models` — `https://github.com/apple/coreai-models.git`, revision `938d0b8943b942ce66438b94ab017c5631d1aef4` (no semver tag)
- transitively pulls **`xgrammar`** — `https://github.com/mlc-ai/xgrammar`, branch `main`, revision `257f870d1b905060a5d3168f6f997bb3481f90c1`
- also transitively: `swift-huggingface 0.9.0`, `swift-nio 2.99.0`, `swift-crypto 4.5.0`, `swift-asn1 1.7.0`, `swift-atomics 1.3.0`, `swift-system 1.6.4`, `yyjson 0.12.0`, `EventSource 1.4.1`
- direct: `swift-collections 1.4.1`, `swift-jinja 2.3.5`, `swift-transformers 1.3.0`, `JSONSchema 1.3.1`, `swift-testing-heartbeat 0.1.0`

### README "Requirements" (`README.md:18-34`)

```
- Xcode 27 beta or later
- Swift 6.4+
- macOS 27.0+ or iOS 27.0+ as declared by `Package.swift`
- Apple Silicon for local Core AI execution
- A Hugging Face model bundle containing:
  - `config.json`
  - model weights and tokenizer metadata when running a complete model
```

Optional bundle files used when present: `tokenizer_config.json`,
`special_tokens_map.json`, `chat_template.jinja`, `preprocessor_config.json`,
`processor_config.json`.

### Python `python/pyproject.toml` (verbatim)

```toml
[build-system]
requires = ["hatchling>=1.25,<2.0"]
build-backend = "hatchling.build"

[project]
name = "swiftlm-coreai"
version = "0.11.0a1"
description = "Core AI export tooling for swift-lm declarative model graphs"
requires-python = ">=3.11"
dependencies = [
    "coreai-core==1.0.0b2",
    "coreai-torch==0.4.1",
    "coreai-opt==0.2.1",
    "coreai-models @ git+https://github.com/apple/coreai-models.git@0.2.0#subdirectory=python",
    "torch==2.9.0",
    "transformers>=4.57,<5.0",
]

[project.scripts]
swiftlm-coreai = "swiftlm_coreai.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/swiftlm_coreai"]

[tool.hatch.metadata]
allow-direct-references = true
```

**Exact Core AI Python package pins (2026 beta):**
`coreai-core==1.0.0b2`, `coreai-torch==0.4.1`, `coreai-opt==0.2.1`,
`coreai-models` from git tag `0.2.0`, subdirectory `python`; `torch==2.9.0`;
`transformers>=4.57,<5.0`; Python `>=3.11`.

> "The Python project pins the Core AI beta packages in `python/pyproject.toml`.
> The Swift package uses the corresponding Apple `coreai-models` revision and its
> transitive `xgrammar` dependency. Keep those versions aligned when updating the
> Xcode beta." — `docs/design/core-ai.md:165-168`

---

## 2. Design philosophy (PHILOSOPHY.md, CLAUDE.md, AGENTS.md)

`PHILOSOPHY.md` is written in Japanese and enumerates 10 convictions. Direct
quotes (with translation gloss):

1. **"swift-lm はコンパイラである"** (`PHILOSOPHY.md:7-20`) — PyTorch/MLX/llama.cpp
   are *interpreters*; swift-lm compiles an HF bundle into Metal kernels.
   Justification: *"Apple Silicon の実測値で、decode の GPU 時間の **~85% が barrier
   同期** に消える"* — ~85% of decode GPU time is barrier sync, so the only real
   lever is reducing dispatch count via static analysis/fusion.
2. **"モデルはコードではなくデータである"** (`:22-32`) — the consumer supplies **one
   HuggingFace repo ID**. `config.json + safetensors + tokenizer.json` is the
   canonical input. Expressive model DSL was *deliberately given up* in exchange
   for "distributability and zero-cost additions".
3. **3-axis separation of concerns** (`:34-46`): `LMIR` = WHAT (structure),
   `InferencePolicy` = WHY (deployment intent: KV-cache quantization, max seq
   length), `MetalCompiler` = HOW (kernel selection, buffers, dispatch plan).
4. **"Fragment は自己記述的である。Compiler は無知である"** (`:48-67`) — the compiler
   never does `if fragment is XxxFragment`. Adding a fragment must not change one
   line of compiler code. *"compiler が `if fragment is XxxFragment` と書いたら負け"*.
5. **"HuggingFace が唯一の正である"** (`:68-80`) — correctness is *only* established
   against HF `modeling_*.py` intermediate values. Internal comparison is not
   proof: *"全層が壊れている場合、内部比較は壊れたものと壊れたものを比較して合格判定を出してしまう"*.
6. **"Probe First — 観測が静的解析に先立つ"** (`:82-99`) — when output breaks, probe
   layer hidden states first; read kernel source last.
7. **"Silent Fallback は禁止する"** (`:101-118`) — `MetalCompilable`-less
   `OperationAttributes` ⇒ `fatalError`; no `try?`; missing required config
   fields are errors, never defaulted.
8. **"性能を追求する"** (`:120-139`) — performance is the raison d'être, but
   *"壊れた出力の生成速度を性能とは呼ばない"* (throughput on broken output is not
   performance).
9. **"Apple Silicon は前提であり、target ではない"** (`:141-153`) — Metal 4 preferred
   over Metal 3; `private` buffers to get lossless compression.
10. **"我々が拒否するもの"** (`:155-166`) — hand-written fused kernels, compiler
    `switch fragment.kind`, per-model Swift codegen, tests without output
    verification, benchmark-first refactors.

`CLAUDE.md` (Japanese, 53 KB) is the *rules* document; `AGENTS.md` (English/JP mix,
38 KB) is the Codex-facing equivalent. AGENTS.md restates the 0.11 goal in
English (`AGENTS.md:47-64`):

> "`swift-lm` is a Core AI-first declarative model authoring and export package for
> macOS and iOS 27+. … The core thesis is to describe model families once in Swift,
> normalize them to backend-independent IR, and emit a validated Core AI export
> contract. Apple's official exporter owns deployment asset generation for
> supported models. Custom stateful families use the low-level Core AI Torch
> converter and Swift runtime wrapper."

Module rules (`AGENTS.md:262-270`):

- `LMArchitecture` must not depend on `MetalCompiler`.
- `MetalCompiler` must not depend on `LMArchitecture`; both meet at `LMIR`.
- Backend behavior extends IR attribute types; no backend detail in `LMIR`.

---

## 3. Architecture / module map

`README.md:434-475`:

```text
LMIR              Backend-independent graph and operation model.
LMArchitecture    Declarative model DSL and validation.
ModelDeclarations Family-specific model declarations.
CoreAIExport      Versioned executable contract with functions, states,
                  operations, and parameter bindings.
SwiftLMIR         Hugging Face config to Swift-authored contract CLI.
SwiftLMCoreAI     Generated bundle validation, specialization, persistent state,
                  and execution.
SwiftLMFoundationModels
                  Adapter for Apple-native Core AI language bundles.
MetalCompiler / SwiftLM
                  Direct Metal 0.10 compatibility runtime.
```

Dependency direction (`README.md:466-475`):

```text
LMIR  <-  LMArchitecture  <-  ModelDeclarations
  |                               |
  +---- CoreAIExport <------------+
  |          |                    |
  |          +---- SwiftLMIR      +---- generic Python Core AI lowerer
  |          +---- SwiftLMCoreAI
  |
  +---- MetalCompiler ---- SwiftLM (0.10 compatibility)
```

Core AI layered flow (`docs/design/core-ai.md:17-45`):

```text
Hugging Face bundle (config.json + safetensors + tokenizer metadata)
  -> ModelDeclarations (family-level declarative Swift components)
  -> LMArchitecture -> LMIR (normalized graph, regions, operations, bindings)
  -> CoreAIExport (versioned function, state, graph, and binding contract)
  -> Generic Swift LMIR lowerer in Python (safetensors bindings -> coreai-torch / coreai-models)
  -> .aimodel + embedded Swift contract
  -> AIModel / InferenceFunction
  -> Core AI runtime on macOS/iOS 27+
```

---

## 4. ⭐ The Core AI **VLM adapter** (HEAD commit `db7a802`)

This is the newest and most valuable artifact for a "real third-party Core AI
usage" guide. Commit touched 17 files, +710/-8.

### 4.1 What the three-asset contract looks like

`README.md:132-138`:

```text
image -> vision.aimodel ----+
                            v
prompt -> embed.aimodel -> decoder.aimodel -> generated text
```

`docs/design/core-ai.md:80-85` (added in this commit):

> "6. `CoreAISequentialVLMEngine` executes Apple's official three-asset VLM
>    contract: vision encoder, token embedding, and embedding-input decoder.
>
> The VLM adapter preserves that asset boundary and provides a state-owning Swift
> actor. Text input is rendered by the embedded tokenizer chat template and must
> produce one image placeholder before expansion. Pre-tokenized input must carry
> the exact declared placeholder count. Both contracts fail explicitly when the
> bundle metadata, template, or token layout disagrees with the exported model."

### 4.2 Bundle loader — `SwiftLMFoundationModelBundle`

`Sources/SwiftLMFoundationModels/CoreAILanguageModelBundle.swift:1-83` **verbatim**:

```swift
import CoreAILanguageModels
import Foundation

/// Strict loader for Apple Core AI language-model bundles.
@available(macOS 27.0, iOS 27.0, *)
public struct SwiftLMFoundationModelBundle: Sendable {
    private let bundle: LanguageBundle

    public init(contentsOf url: URL) throws {
        bundle = try LanguageBundle(at: url)
    }

    public var name: String { bundle.name }
    public var tokenizer: String { bundle.tokenizer }
    public var vocabSize: Int { bundle.vocabSize }
    public var maxContextLength: Int { bundle.maxContextLength }
    public var bundleURL: URL { bundle.bundlePath }
    public var isVisionLanguageModel: Bool { bundle.visionConfig != nil }

    public var visionConfiguration: SwiftLMVisionConfiguration? {
        bundle.visionConfig.map(SwiftLMVisionConfiguration.init)
    }

    public func makeLanguageModel(
        variant: String? = nil,
        kvCacheStrategy: KVCacheStrategy = .auto
    ) async throws -> CoreAILanguageModel {
        guard !isVisionLanguageModel else {
            throw SwiftLMVisionLanguageModelError.visionLanguageModelRequiresVisionAPI
        }
        return try await CoreAILanguageModel(
            resourcesAt: bundle.bundlePath,
            variant: variant,
            kvCacheStrategy: kvCacheStrategy
        )
    }

    public func makeVisionLanguageModel(
        kvCacheStrategy: KVCacheStrategy = .auto
    ) async throws -> SwiftLMVisionLanguageModel {
        let visionConfig = try validatedVisionConfiguration()

        try bundle.bundle.verify()

        let visionURL = try bundle.requireModelURL(for: ModelBundle.ComponentKey.vision)
        let embeddingURL = try bundle.requireModelURL(for: ModelBundle.ComponentKey.embedding)
        let decoderURL = try bundle.requireModelURL(for: ModelBundle.ComponentKey.main)
        let functionName = bundle.language.functionMap?.name(for: "main") ?? "main"
        let baseConfig = ModelConfig(
            name: bundle.name,
            tokenizer: bundle.tokenizer,
            vocabSize: bundle.vocabSize,
            maxContextLength: bundle.maxContextLength,
            serializedModel: [decoderURL.path],
            function: functionName
        )
        let configuration = VLMModelConfig(base: baseConfig, visionConfig: visionConfig)

        let visionModel = try await PreparedModel.prepare(at: visionURL)
        let embeddingModel = try await PreparedModel.prepare(at: embeddingURL)
        let decoderModel = try await PreparedModel.prepare(at: decoderURL)
        let engine = try await CoreAISequentialVLMEngine(
            config: configuration,
            visionModel: visionModel,
            embedModel: embeddingModel,
            llmModel: decoderModel,
            options: EngineOptions(kvCacheStrategy: kvCacheStrategy)
        )
        let tokenizer = try await bundle.loadTokenizer()

        var stopTokenIDs = Set<Int32>()
        if let eosTokenID = tokenizer.eosTokenId {
            stopTokenIDs.insert(Int32(eosTokenID))
        }

        return SwiftLMVisionLanguageModel(
            engine: engine,
            tokenizer: tokenizer,
            configuration: SwiftLMVisionConfiguration(visionConfig),
            maxContextLength: bundle.maxContextLength,
            stopTokenIDs: stopTokenIDs
        )
    }
```

**Apple `CoreAILanguageModels` API surface exercised here (all verified by use):**

- `LanguageBundle(at: URL) throws` — bundle wrapper
- `LanguageBundle.name / .tokenizer / .vocabSize / .maxContextLength / .bundlePath`
- `LanguageBundle.visionConfig -> VisionConfig?` (presence ⇒ VLM)
- `LanguageBundle.bundle -> ModelBundle` and `ModelBundle.verify() throws`
- `LanguageBundle.requireModelURL(for: ModelBundle.ComponentKey) throws -> URL`
- `ModelBundle.ComponentKey.vision`, `.embedding`, `.main`
- `LanguageBundle.language.functionMap?.name(for: String) -> String?`
- `LanguageBundle.loadTokenizer() async throws -> any Tokenizer` (swift-transformers `Tokenizer`)
- `ModelConfig(name:tokenizer:vocabSize:maxContextLength:serializedModel:function:)`
  — note `serializedModel: [String]` is an **array of paths**
- `VLMModelConfig(base: ModelConfig, visionConfig: VisionConfig)`
- `PreparedModel.prepare(at: URL) async throws -> PreparedModel`
- `CoreAISequentialVLMEngine(config:visionModel:embedModel:llmModel:options:) async throws`
- `EngineOptions(kvCacheStrategy: KVCacheStrategy)`
- `KVCacheStrategy.auto`
- `CoreAILanguageModel(resourcesAt: URL, variant: String?, kvCacheStrategy:) async throws`

> ⚠️ Name collision hazard: `CoreAILanguageModels.ModelConfig` (bundle config)
> is a *different* type from `LMIR.ModelConfig` (HF-derived model dimensions) and
> from `SwiftLM.ModelConfiguration`. In a guide, always qualify.

### 4.3 Strict vision-config validation (fails **before** any asset load)

`CoreAILanguageModelBundle.swift:85-141` **verbatim**:

```swift
    private func validatedVisionConfiguration() throws -> VisionConfig {
        guard let configuration = bundle.visionConfig else {
            throw SwiftLMVisionLanguageModelError.languageModelDoesNotSupportVision
        }
        guard configuration.imageSize > 0 else {
            throw invalidVisionConfiguration(
                field: "image_size", reason: "must be greater than zero")
        }
        guard configuration.patchSize > 0 else {
            throw invalidVisionConfiguration(
                field: "patch_size", reason: "must be greater than zero")
        }
        guard configuration.imageSize.isMultiple(of: configuration.patchSize) else {
            throw invalidVisionConfiguration(
                field: "patch_size",
                reason: "must divide image_size exactly"
            )
        }
        guard configuration.imageTokenCount > 0 else {
            throw invalidVisionConfiguration(
                field: "image_token_count",
                reason: "must be greater than zero"
            )
        }
        guard configuration.imageTokenId >= 0 else {
            throw invalidVisionConfiguration(
                field: "image_token_id", reason: "must not be negative")
        }
        guard configuration.imageMean.count == 3 else {
            throw invalidVisionConfiguration(
                field: "image_mean", reason: "must contain three RGB values")
        }
        guard configuration.imageStd.count == 3 else {
            throw invalidVisionConfiguration(
                field: "image_std", reason: "must contain three RGB values")
        }
        guard configuration.imageMean.allSatisfy(\.isFinite) else {
            throw invalidVisionConfiguration(field: "image_mean", reason: "values must be finite")
        }
        guard configuration.imageStd.allSatisfy({ $0.isFinite && $0 != 0 }) else {
            throw invalidVisionConfiguration(
                field: "image_std",
                reason: "values must be finite and nonzero"
            )
        }
        guard configuration.rescaleFactor.isFinite else {
            throw invalidVisionConfiguration(field: "rescale_factor", reason: "must be finite")
        }
        return configuration
    }
```

**`CoreAILanguageModels.VisionConfig` fields (confirmed by mirror struct):**
`imageSize: Int`, `patchSize: Int`, `imageTokenCount: Int`, `imageTokenId: Int32`,
`imageMean: [Double]`, `imageStd: [Double]`, `rescaleFactor: Double`.

Mirrored publicly as (`SwiftLMVisionConfiguration.swift:1-24`):

```swift
import CoreAILanguageModels
import Foundation

/// Vision metadata declared by an Apple Core AI VLM bundle.
@available(macOS 27.0, iOS 27.0, *)
public struct SwiftLMVisionConfiguration: Sendable, Equatable {
    public let imageSize: Int
    public let patchSize: Int
    public let imageTokenCount: Int
    public let imageTokenID: Int32
    public let imageMean: [Double]
    public let imageStandardDeviation: [Double]
    public let rescaleFactor: Double

    init(_ configuration: VisionConfig) {
        imageSize = configuration.imageSize
        patchSize = configuration.patchSize
        imageTokenCount = configuration.imageTokenCount
        imageTokenID = configuration.imageTokenId
        imageMean = configuration.imageMean
        imageStandardDeviation = configuration.imageStd
        rescaleFactor = configuration.rescaleFactor
    }
}
```

### 4.4 The state-owning actor — `SwiftLMVisionLanguageModel`

`Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageModel.swift:1-128` **verbatim**:

```swift
import CoreAILanguageModels
import Foundation
import Tokenizers

/// Stateful Swift interface over Apple's Core AI sequential VLM engine.
@available(macOS 27.0, iOS 27.0, *)
public actor SwiftLMVisionLanguageModel: SwiftLMVisionLanguageGenerating {
    public nonisolated let configuration: SwiftLMVisionConfiguration

    private let engine: CoreAISequentialVLMEngine
    private let tokenizer: any Tokenizer
    private let maxContextLength: Int
    private let stopTokenIDs: Set<Int32>

    init(
        engine: CoreAISequentialVLMEngine,
        tokenizer: any Tokenizer,
        configuration: SwiftLMVisionConfiguration,
        maxContextLength: Int,
        stopTokenIDs: Set<Int32>
    ) { ... }

    public func generate(
        from input: SwiftLMVisionLanguageInput,
        options: SwiftLMVisionLanguageGenerationOptions = SwiftLMVisionLanguageGenerationOptions()
    ) async throws -> SwiftLMVisionLanguageOutput {
        guard options.maxTokens > 0 else {
            throw SwiftLMVisionLanguageModelError.invalidMaximumTokenCount(options.maxTokens)
        }

        let embeddedInput = try await engine.encodeImage(at: input.imageURL)
        guard embeddedInput.tokenCount == configuration.imageTokenCount else {
            throw SwiftLMVisionLanguageModelError.invalidImagePlaceholderCount(
                expected: configuration.imageTokenCount,
                actual: embeddedInput.tokenCount
            )
        }

        let promptTokenIDs = try makePromptTokenIDs(from: input.prompt)
        let requestedTokenCount = promptTokenIDs.count + options.maxTokens
        guard requestedTokenCount <= maxContextLength else {
            throw SwiftLMVisionLanguageModelError.contextLengthExceeded(
                maximum: maxContextLength,
                requested: requestedTokenCount
            )
        }

        let sequence = try await engine.generate(
            with: embeddedInput,
            tokens: promptTokenIDs,
            samplingConfiguration: options.samplingConfiguration,
            inferenceOptions: InferenceOptions(maxTokens: options.maxTokens)
        )

        var generatedTokenIDs: [Int32] = []
        for try await output in sequence {
            if stopTokenIDs.contains(output.tokenId)
                || options.additionalStopTokenIDs.contains(output.tokenId)
            {
                sequence.setStopReason(.eos)
                break
            }
            generatedTokenIDs.append(output.tokenId)
        }

        guard let stopReason = sequence.stopReason else {
            throw SwiftLMVisionLanguageModelError.generationEndedWithoutReason
        }
        return SwiftLMVisionLanguageOutput(
            text: tokenizer.decode(tokens: generatedTokenIDs.map(Int.init)),
            tokenIDs: generatedTokenIDs,
            stopReason: stopReason
        )
    }

    public func reset() async throws {
        try await engine.reset()
    }

    public func cancel() async throws {
        try await engine.cancel()
    }

    private func makePromptTokenIDs(
        from prompt: SwiftLMVisionLanguagePrompt
    ) throws -> [Int32] {
        switch prompt {
        case .text(let text):
            return try makeTemplatedPromptTokenIDs(text: text)
        case .tokens(let tokenIDs):
            try promptTokenExpander.validatePretokenizedTokenIDs(tokenIDs)
            return tokenIDs
        }
    }

    private func makeTemplatedPromptTokenIDs(text: String) throws -> [Int32] {
        guard let imageToken = tokenizer.convertIdToToken(Int(configuration.imageTokenID)) else {
            throw SwiftLMVisionLanguageModelError.imageTokenUnavailable(configuration.imageTokenID)
        }

        let renderedTokenIDs: [Int]
        do {
            renderedTokenIDs = try PromptUtils.maybeApplyTokenizerChatTemplate(
                .prompt("\(imageToken)\n\(text)"),
                tokenizer: tokenizer
            )
        } catch {
            throw SwiftLMVisionLanguageModelError.chatTemplateFailed(String(describing: error))
        }

        return try promptTokenExpander.expandTemplatedTokenIDs(
            renderedTokenIDs.map(Int32.init)
        )
    }

    private var promptTokenExpander: SwiftLMVisionPromptTokenExpander {
        SwiftLMVisionPromptTokenExpander(
            imageTokenID: configuration.imageTokenID,
            imageTokenCount: configuration.imageTokenCount
        )
    }
}
```

**Apple VLM-engine API surface exercised (all verified by use):**

- `CoreAISequentialVLMEngine.encodeImage(at: URL) async throws -> <EmbeddedInput>`
  where the result exposes `.tokenCount: Int` (exact type name **UNVERIFIED**;
  only `.tokenCount` is used)
- `CoreAISequentialVLMEngine.generate(with:tokens:samplingConfiguration:inferenceOptions:) async throws -> <TokenSequence>`
  - `tokens: [Int32]`
  - the returned sequence is an `AsyncSequence` (`for try await output in sequence`)
    whose element has `.tokenId: Int32`
  - the sequence itself is *stateful and mutable*: `sequence.setStopReason(.eos)`
    and `sequence.stopReason -> StopReason?`
- `InferenceOptions(maxTokens: Int)`
- `SamplingConfiguration` with a `.greedy` static member
- `StopReason` (has `.eos`; used as public output field)
- `CoreAISequentialVLMEngine.reset() async throws`, `.cancel() async throws`
- `PromptUtils.maybeApplyTokenizerChatTemplate(_:tokenizer:) throws -> [Int]`
  with an input case `.prompt(String)`

### 4.5 Prompt placeholder expansion — the "one placeholder" contract

`Sources/SwiftLMFoundationModels/SwiftLMVisionPromptTokenExpander.swift:1-44` **verbatim**:

```swift
import Foundation

@available(macOS 27.0, iOS 27.0, *)
struct SwiftLMVisionPromptTokenExpander: Sendable {
    let imageTokenID: Int32
    let imageTokenCount: Int

    func expandTemplatedTokenIDs(_ tokenIDs: [Int32]) throws -> [Int32] {
        let placeholderCount = countPlaceholders(in: tokenIDs)
        guard placeholderCount == 1 else {
            throw SwiftLMVisionLanguageModelError.invalidImagePlaceholderCount(
                expected: 1,
                actual: placeholderCount
            )
        }

        var expandedTokenIDs: [Int32] = []
        expandedTokenIDs.reserveCapacity(tokenIDs.count + imageTokenCount - 1)
        for tokenID in tokenIDs {
            if tokenID == imageTokenID {
                expandedTokenIDs.append(
                    contentsOf: repeatElement(imageTokenID, count: imageTokenCount)
                )
            } else {
                expandedTokenIDs.append(tokenID)
            }
        }
        return expandedTokenIDs
    }

    func validatePretokenizedTokenIDs(_ tokenIDs: [Int32]) throws {
        let actualCount = countPlaceholders(in: tokenIDs)
        guard actualCount == imageTokenCount else {
            throw SwiftLMVisionLanguageModelError.invalidImagePlaceholderCount(
                expected: imageTokenCount,
                actual: actualCount
            )
        }
    }

    private func countPlaceholders(in tokenIDs: [Int32]) -> Int {
        tokenIDs.count(where: { $0 == imageTokenID })
    }
}
```

Semantics:
- `.text(String)` path: the chat template must render **exactly one** image token;
  the adapter then repeats it `imageTokenCount` times (196 for a 448/16 ViT).
- `.tokens([Int32])` path: caller must already have **exactly `imageTokenCount`**
  image tokens — validated, never expanded.
- Note `tokenIDs.count(where:)` — Swift 6 `count(where:)` on `Sequence`.

### 4.6 Remaining VLM value types (verbatim)

```swift
// SwiftLMVisionLanguagePrompt.swift
@available(macOS 27.0, iOS 27.0, *)
public enum SwiftLMVisionLanguagePrompt: Sendable, Equatable {
    /// Text rendered through the tokenizer's chat template.
    case text(String)
    /// Fully rendered token IDs containing exactly the required image placeholders.
    case tokens([Int32])
}

// SwiftLMVisionLanguageInput.swift
@available(macOS 27.0, iOS 27.0, *)
public struct SwiftLMVisionLanguageInput: Sendable, Equatable {
    public let imageURL: URL
    public let prompt: SwiftLMVisionLanguagePrompt
    public init(imageURL: URL, prompt: SwiftLMVisionLanguagePrompt)
}

// SwiftLMVisionLanguageGenerationOptions.swift
@available(macOS 27.0, iOS 27.0, *)
public struct SwiftLMVisionLanguageGenerationOptions: Sendable, Equatable {
    public let maxTokens: Int
    public let samplingConfiguration: SamplingConfiguration
    public let additionalStopTokenIDs: Set<Int32>

    public init(
        maxTokens: Int = 256,
        samplingConfiguration: SamplingConfiguration = .greedy,
        additionalStopTokenIDs: Set<Int32> = []
    )
}

// SwiftLMVisionLanguageOutput.swift
@available(macOS 27.0, iOS 27.0, *)
public struct SwiftLMVisionLanguageOutput: Sendable, Equatable {
    public let text: String
    public let tokenIDs: [Int32]
    public let stopReason: StopReason
    public init(text: String, tokenIDs: [Int32], stopReason: StopReason)
}

// SwiftLMVisionLanguageGenerating.swift
@available(macOS 27.0, iOS 27.0, *)
public protocol SwiftLMVisionLanguageGenerating: Sendable {
    func generate(
        from input: SwiftLMVisionLanguageInput,
        options: SwiftLMVisionLanguageGenerationOptions
    ) async throws -> SwiftLMVisionLanguageOutput

    func reset() async throws
    func cancel() async throws
}
```

Error enum, complete (`SwiftLMVisionLanguageModelError.swift:5-14`):

```swift
public enum SwiftLMVisionLanguageModelError: Error, LocalizedError, Sendable, Equatable {
    case languageModelDoesNotSupportVision
    case visionLanguageModelRequiresVisionAPI
    case invalidVisionConfiguration(field: String, reason: String)
    case invalidMaximumTokenCount(Int)
    case imageTokenUnavailable(Int32)
    case chatTemplateFailed(String)
    case invalidImagePlaceholderCount(expected: Int, actual: Int)
    case contextLengthExceeded(maximum: Int, requested: Int)
    case generationEndedWithoutReason
}
```

Message strings worth quoting in a guide:
- `.visionLanguageModelRequiresVisionAPI` → *"The bundle contains vision assets and must be loaded with makeVisionLanguageModel()."*
- `.generationEndedWithoutReason` → *"Core AI generation ended without reporting a stop reason."*

### 4.7 Minimal end-to-end VLM usage (README `:143-152`)

```swift
let bundle = try SwiftLMFoundationModelBundle(contentsOf: bundleURL)
let model = try await bundle.makeVisionLanguageModel()
let output = try await model.generate(
    from: SwiftLMVisionLanguageInput(
        imageURL: imageURL,
        prompt: .text(prompt)
    )
)
```

README caveats (`README.md:154-161`):

> "Text prompts must render exactly one image placeholder through the bundle's
> chat template; the adapter expands it to the declared visual token count.
> Callers with a model-specific renderer can pass fully rendered token IDs using
> `.tokens`. Missing or ambiguous placeholders fail with a typed error rather
> than using a generic prompt fallback. **The model owns mutable KV state, so call
> `reset()` before starting an unrelated request.** Model-specific turn-ending
> tokens can be supplied explicitly through
> `SwiftLMVisionLanguageGenerationOptions.additionalStopTokenIDs`."

### 4.8 VLM bundle `metadata.json` (`kind: "vlm"`, metadata_version 0.2)

Test fixture, verbatim (`Tests/SwiftLMFoundationModelsTests/SwiftLMFoundationModelBundleTests.swift:153-179`):

```json
{
  "metadata_version": "0.2",
  "kind": "vlm",
  "name": "test-vlm",
  "assets": {
    "main": "decoder.aimodel",
    "embedding": "embed.aimodel",
    "vision": "vision.aimodel"
  },
  "language": {
    "tokenizer": "test/tokenizer",
    "vocab_size": 152064,
    "max_context_length": 4096,
    "embedded_tokenizer": false
  },
  "vision": {
    "image_size": 448,
    "patch_size": 16,
    "image_token_count": 196,
    "image_token_id": 151655,
    "image_mean": [0.48145466, 0.4578275, 0.40821073],
    "image_std": [0.26862954, 0.26130258, 0.27577711],
    "rescale_factor": 0.00392156862745098
  }
}
```

(448/16 = 28 patches/side, 28² = 784, /4 spatial merge = 196 visual tokens; the
`image_token_id` `151655` is the Qwen-VL `<|image_pad|>` id.)

### 4.9 VLM tests — env-var gated real-asset execution

`Tests/SwiftLMFoundationModelsTests/SwiftLMFoundationModelBundleTests.swift:22-54`:

```swift
    @Test("Runs an official Core AI VLM bundle when test assets are provided")
    func runsVisionLanguageBundle() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard
            let bundlePath = environment["SWIFTLM_COREAI_TEST_VLM_BUNDLE"],
            let imagePath = environment["SWIFTLM_COREAI_TEST_VLM_IMAGE"]
        else { return }

        let bundle = try SwiftLMFoundationModelBundle(
            contentsOf: URL(fileURLWithPath: bundlePath, isDirectory: true)
        )
        let model = try await bundle.makeVisionLanguageModel()
        let prompt: SwiftLMVisionLanguagePrompt
        if let rawTokenIDs = environment["SWIFTLM_COREAI_TEST_VLM_TOKEN_IDS"] {
            let tokenIDs = try rawTokenIDs.split(separator: ",").map { value in
                try #require(Int32(value))
            }
            prompt = .tokens(tokenIDs)
        } else {
            prompt = .text("Describe the image.")
        }
        let output = try await model.generate(
            from: SwiftLMVisionLanguageInput(
                imageURL: URL(fileURLWithPath: imagePath),
                prompt: prompt
            ),
            options: SwiftLMVisionLanguageGenerationOptions(maxTokens: 1)
        )

        #expect(output.tokenIDs.count == 1)
    }
```

Env vars that gate Core AI tests across the repo:

| Env var | Used by |
|---|---|
| `SWIFTLM_COREAI_TEST_BUNDLE` | LLM bundle (`SwiftLMFoundationModelBundleTests.loadsExportedBundle`) **and** the stateful bundle in `CoreAIModelAssetTests.dynamicStateExecution` |
| `SWIFTLM_COREAI_TEST_VLM_BUNDLE` | VLM bundle directory |
| `SWIFTLM_COREAI_TEST_VLM_IMAGE` | image file path |
| `SWIFTLM_COREAI_TEST_VLM_TOKEN_IDS` | comma-separated pre-tokenized prompt |
| `SWIFTLM_COREAI_TEST_STATELESS_BUNDLE` | stateless `.aimodel` bundle |
| `SWIFTLM_COREAI_TEST_STATELESS_EXPECTED_LAST_TOKEN` | expected argmax token id |
| `SWIFTLM_COREAI_TEST_MODEL` / `SWIFTLM_COREAI_STATELESS_DOCUMENT` / `SWIFTLM_COREAI_STATEFUL_DOCUMENT` | `python/tests/test_real_lfm2.py` |
| `ENABLE_METAL_PROBES=1` | compiles `-D ENABLE_METAL_PROBES` into MetalCompiler/SwiftLM |

⚠️ **Footgun:** every one of these tests silently `return`s (passes!) when the env
var is missing. `docs/production-readiness.md:48-52` explicitly calls this out:

> "Apple-native VLM changes must also run `SwiftLMFoundationModelsTests`. Set
> `SWIFTLM_COREAI_TEST_VLM_BUNDLE`, `SWIFTLM_COREAI_TEST_VLM_IMAGE`, and, for a
> pre-tokenized fixture, `SWIFTLM_COREAI_TEST_VLM_TOKEN_IDS` to exercise vision
> encoding, embedding scatter, stateful decoding, and token generation.
> **Metadata-only tests are not sufficient for this runtime boundary.**"

---

## 5. `SwiftLMCoreAI` — low-level Core AI runtime (the `CoreAI` OS framework)

### 5.1 `CoreAIModelAsset` — validate + specialize

`Sources/SwiftLMCoreAI/CoreAIModelAsset.swift:1-50` **verbatim**:

```swift
import CoreAI
import Foundation

/// A validated Core AI source or compiled model asset.
@available(macOS 27.0, iOS 27.0, *)
public struct CoreAIModelAsset: Sendable {
    public let url: URL
    public let summary: AIModelAsset.Summary

    public init(contentsOf url: URL, includingStatistics: Bool = false) throws {
        guard AIModelAsset.isValid(at: url) else {
            throw CoreAIModelAssetError.invalidAsset(url)
        }
        let asset = try AIModelAsset(contentsOf: url)
        guard let summary = try asset.summary(includingStatistics: includingStatistics) else {
            throw CoreAIModelAssetError.missingSummary(url)
        }
        self.url = url
        self.summary = summary
    }

    public var functionNames: [String] {
        summary.functions.map(\.name)
    }

    public func function(named name: String) throws -> AIModelAsset.FunctionDescriptor {
        guard let function = summary.functions.first(where: { $0.name == name }) else {
            throw CoreAIModelAssetError.functionNotFound(name)
        }
        return function
    }

    public func specialize(
        options: SpecializationOptions = .default,
        cache: AIModelCache = .default,
        cachePolicy: AIModelCache.Policy = .default
    ) async throws -> AIModel {
        guard !options.expectFrequentReshapes else {
            throw CoreAIModelAssetError.unsupportedSpecializationOption(
                "expectFrequentReshapes is disabled until the current Core AI runtime is compatible"
            )
        }
        return try await AIModel.specialize(
            contentsOf: url,
            options: options,
            cache: cache,
            cachePolicy: cachePolicy
        )
    }
}
```

**⭐ GOTCHA (documented Core AI beta bug):** `docs/design/core-ai.md:87-90`

> "`CoreAIModelAsset` rejects unsupported specialization settings explicitly.
> The current beta has a reproducible failure when `expectFrequentReshapes` is
> enabled, so callers must resolve dynamic shapes before execution and use the
> default specialization policy."

**`CoreAI` framework API surface used here:**
`AIModelAsset.isValid(at: URL) -> Bool`; `AIModelAsset(contentsOf: URL) throws`;
`AIModelAsset.summary(includingStatistics: Bool) throws -> AIModelAsset.Summary?`
(note: **optional** return); `AIModelAsset.Summary.functions -> [AIModelAsset.FunctionDescriptor]`;
`FunctionDescriptor.name / .inputs / .states / .outputs -> [AIModelAsset.ValueDescriptor]`;
`ValueDescriptor.name: String`, `ValueDescriptor.typeName: String`;
`AIModel.specialize(contentsOf:options:cache:cachePolicy:) async throws -> AIModel`;
`SpecializationOptions` (`.default`, `.expectFrequentReshapes: Bool`);
`AIModelCache.default`; `AIModelCache.Policy.default`.

### 5.2 `CoreAIModelBundle` — contract-checked bundle load

`Sources/SwiftLMCoreAI/CoreAIModelBundle.swift`. Load path (`:15-89`):

1. read `metadata.json`, decode `Metadata`
2. hard gate:
```swift
        guard metadata.metadataVersion == "0.2",
              metadata.kind == "llm",
              metadata.source.modelDefinition == "swift_lmir",
              metadata.source.formatVersion == CoreAIExportDocument.currentFormatVersion else {
            throw CoreAIModelAssetError.invalidBundle(
                url, "bundle metadata does not declare the Swift LMIR v2 contract")
        }
```
3. resolve `assets.main` and `assets.contract` **inside the bundle only**:
```swift
    private static func resolve(_ path: String, inside bundle: URL) throws -> URL {
        let bundlePath = bundle.standardizedFileURL.path
        let resolved = bundle.appendingPathComponent(path).standardizedFileURL
        guard resolved.path == bundlePath || resolved.path.hasPrefix(bundlePath + "/") else {
            throw CoreAIModelAssetError.invalidBundle(bundle, "asset path escapes the bundle")
        }
        return resolved
    }
```
4. **SHA-256 the contract** and compare with `assets.contract_sha256`
   (`CryptoKit.SHA256`, lowercase hex `%02x`)
5. decode `CoreAIExportDocument`, cross-check `formatVersion`,
   `program.source == .swiftLMIR`, `metadata.name`, `maxContextLength`, `vocabSize`
6. `CoreAIModelAsset(contentsOf: assetURL)` then `Self.validate(document:asset:)`

Contract↔asset validation compares **name order and type name** of every input,
state, and output (`:192-242`):

```swift
    private static func typeName(for tensor: CoreAIProgramContract.Tensor) -> String {
        let dataType: String
        switch tensor.dataType {
        case .int32:    dataType = "Int32"
        case .float16:  dataType = "Float16"
        case .bfloat16: dataType = "BFloat16"
        case .float32:  dataType = "Float32"
        }
        let dimensions = tensor.dimensions.map { dimension in
            switch dimension.kind {
            case .fixed:   return String(dimension.size ?? 0)
            case .dynamic: return "?"
            }
        }
        return "NDArray (\(dataType), \(dimensions.joined(separator: " \u{00D7} ")))"
    }
```

**⭐ This reveals Core AI's `ValueDescriptor.typeName` string format verbatim:**
`NDArray (Float16, 1 × 1 × 32000)` — a multiplication sign U+00D7 with spaces,
`?` for dynamic axes.

Session factories (`:91-156`):

```swift
    public func makeStateSession(
        functionName: String = "main",
        maxContextLength: Int? = nil,
        options: SpecializationOptions = .default,
        cache: AIModelCache = .default,
        cachePolicy: AIModelCache.Policy = .default
    ) async throws -> CoreAIStateSession
```
- rejects unless `document.program.execution == .stateful`
- resolves each state's dynamic dimensions to `resolvedContextLength`:
```swift
            stateShapes: Dictionary(uniqueKeysWithValues: function.states.map { state in
                (state.name, state.dimensions.map { dimension in
                    switch dimension.kind {
                    case .fixed:   return dimension.size ?? 0
                    case .dynamic: return resolvedContextLength
                    }
                })
            })
```

```swift
    public func makeStatelessSession(
        functionName: String = "main",
        options: SpecializationOptions = .default,
        cache: AIModelCache = .default,
        cachePolicy: AIModelCache.Policy = .default
    ) async throws -> CoreAIStatelessSession
```
- rejects unless `document.program.execution == .stateless`

`metadata.json` for an LLM bundle is decoded as (`:256-305`, snake_case keys):
`metadata_version`, `kind`, `name`, `assets{main, contract, contract_sha256}`,
`language{max_context_length, vocab_size}`, `source{model_definition, format_version}`.

### 5.3 `CoreAIStateSession` — the meaty part

`Sources/SwiftLMCoreAI/CoreAIStateSession.swift`. Doc comment (`:5-11`):

> "Serial stateful execution for Core AI tensor functions.
> The session owns one mutable value for every tensor state declared by the
> function. It is intentionally an actor because state updates and GPU submission
> order are part of the execution contract. Dynamic state shapes must be supplied
> at initialization, and dynamic output shapes must be supplied for each run."

Shared protocol (`CoreAIExecutableSession.swift`):

```swift
import CoreAI

/// A specialized Core AI function that accepts named tensors and returns named tensors.
@available(macOS 27.0, iOS 27.0, *)
public protocol CoreAIExecutableSession: Sendable {
    func run(
        inputs: [String: NDArray],
        outputShapes: [String: [Int]]
    ) async throws -> [String: NDArray]
}
```

State storage — persistent shared `MTLBuffer` per state, zeroed (`:231-264`):

```swift
    private static func makeStates(
        for function: InferenceFunction,
        stateShapes: [String: [Int]]
    ) throws -> [StateValue] {
        try function.descriptor.stateNames.map { name in
            guard let descriptor = function.descriptor.stateDescriptor(of: name) else {
                throw CoreAIModelAssetError.stateNotFound(function: function.descriptor.name, state: name)
            }
            guard case .ndArray(let arrayDescriptor) = descriptor else {
                throw CoreAIModelAssetError.unsupportedSpecializationOption(
                    "image state '\(name)' is not supported by CoreAIStateSession"
                )
            }
            let resolvedDescriptor = try Self.resolve(
                arrayDescriptor,
                function: function.descriptor.name,
                state: name,
                requestedShape: stateShapes[name]
            )
            guard let device = MTLCreateSystemDefaultDevice(),
                  let buffer = device.makeBuffer(
                    length: resolvedDescriptor.minimumByteCount,
                    options: .storageModeShared
                  ) else {
                throw CoreAIModelAssetError.stateAllocationFailed(name)
            }
            memset(buffer.contents(), 0, buffer.length)
            return StateValue(name: name, buffer: buffer, descriptor: resolvedDescriptor)
        }
    }
```

Recursive mutable-view construction (this is the pattern Core AI forces because
`AsyncMutableValue` is non-copyable and inserted by `inout`) (`:159-191`):

```swift
    private func encode(
        stateIndex: Int,
        inputs: [String: InferenceFunction.AsyncValue],
        stateViews: consuming InferenceFunction.AsyncMutableViews,
        stream: borrowing ComputeStream
    ) throws -> [String: InferenceFunction.AsyncValue] {
        guard stateIndex < states.count else {
            let outputViews = InferenceFunction.AsyncMutableViews()
            return try function.encode(
                inputs: inputs,
                states: stateViews,
                outputViews: consume outputViews,
                to: stream
            )
        }

        let state = states[stateIndex]
        var stateValue = unsafe InferenceFunction.AsyncMutableValue(
            unsafeBuffer: state.buffer,
            scalarType: state.descriptor.scalarType,
            shape: state.descriptor.shape,
            strides: state.descriptor.preferredStrides,
            interleaveLayout: state.descriptor.interleaveLayout
        )
        var nextViews = stateViews
        nextViews.insert(&stateValue, for: state.name)
        return try encode(
            stateIndex: stateIndex + 1,
            inputs: inputs,
            stateViews: consume nextViews,
            stream: stream
        )
    }
```

Note the Swift 6.4 ownership keywords: `consuming` / `borrowing` / `consume` /
the `unsafe` expression prefix (SE "unsafe" expressions for `@unsafe` APIs).

Run flow (`:80-121`):
- rejects functions with `outputNames.count != 1` → `.unsupportedOutputCount`
- resolves the single output descriptor, honoring `outputShapes[name]`
- wraps every input in `InferenceFunction.AsyncValue(value)`
- awaits `asyncOutput.ndArray` (`try await` → `NDArray?`)
- verifies `resolvedOutput.shape == expectedDescriptor.shape`

Input validation (`:123-157`) checks: unexpected inputs, missing inputs,
non-NDArray inputs, `scalarType` equality, `shape.count == arrayDescriptor.rank`,
and per-axis `expected == -1 || expected == actual` (**Core AI encodes a dynamic
axis as `-1` in `NDArrayDescriptor.shape`**).

Serialization primitive — a hand-rolled async mutex over actor reentrancy (`:211-227`):

```swift
    private func acquireExecution() async {
        guard isExecuting else { isExecuting = true; return }
        await withCheckedContinuation { continuation in
            executionWaiters.append(continuation)
        }
    }

    private func releaseExecution() {
        guard !executionWaiters.isEmpty else { isExecuting = false; return }
        executionWaiters.removeFirst().resume()
    }
```

`reset()` re-allocates & zeroes all states under the same lock.

**`CoreAI` API surface used by `CoreAIStateSession`:**
`AIModel.loadFunction(named:) throws -> InferenceFunction?`;
`InferenceFunction.descriptor -> InferenceFunctionDescriptor` with
`.name`, `.inputNames: [String]`, `.outputNames: [String]`, `.stateNames: [String]`,
`.inputDescriptor(of:)`, `.outputDescriptor(of:)`, `.stateDescriptor(of:)`
(each returning an enum with an `.ndArray(NDArrayDescriptor)` case);
`NDArrayDescriptor.scalarType / .shape / .rank / .preferredStrides /
.interleaveLayout / .hasDynamicShape / .minimumByteCount /
.resolvingDynamicDimensions([Int])`;
`NDArray(scalars:shape:)`, `.shape`, `.scalarType`,
`.view(as: T.self).withUnsafePointer { pointer, _, _ in }`;
`ComputeStream()`;
`InferenceFunction.AsyncValue(_:)` + `.ndArray` (async throws optional);
`InferenceFunction.AsyncMutableViews()` + `.insert(_:for:)`;
`InferenceFunction.AsyncMutableValue(unsafeBuffer:scalarType:shape:strides:interleaveLayout:)`;
`InferenceFunction.encode(inputs:states:outputViews:to:) throws -> [String: AsyncValue]`.

### 5.4 `CoreAIStatelessSession`

```swift
import CoreAI

/// Serial execution of a stateless Core AI tensor function.
@available(macOS 27.0, iOS 27.0, *)
public struct CoreAIStatelessSession: CoreAIExecutableSession {
    private let executor: CoreAIStateSession

    public init(model: AIModel, functionName: String) throws {
        guard let function = try model.loadFunction(named: functionName) else {
            throw CoreAIModelAssetError.functionNotFound(functionName)
        }
        guard function.descriptor.stateNames.isEmpty else {
            throw CoreAIModelAssetError.statefulFunctionRequiresStateSession(functionName)
        }
        executor = try CoreAIStateSession(model: model, functionName: functionName)
    }
    ...
}
```

### 5.5 Full error enum (`CoreAIModelAssetError.swift:5-25`)

```swift
public enum CoreAIModelAssetError: Error, LocalizedError, Sendable, Equatable {
    case invalidAsset(URL)
    case invalidBundle(URL, String)
    case missingSummary(URL)
    case functionNotFound(String)
    case inputNotFound(function: String, input: String)
    case unexpectedInput(function: String, input: String)
    case unsupportedInput(function: String, input: String)
    case invalidInputShape(function: String, input: String, expected: [Int], provided: [Int])
    case invalidInputDataType(function: String, input: String, expected: String, provided: String)
    case stateNotFound(function: String, state: String)
    case statefulFunctionRequiresStateSession(String)
    case missingDynamicStateShape(String)
    case missingDynamicOutputShape(String)
    case stateAllocationFailed(String)
    case invalidStateShape(function: String, state: String, expected: [Int], provided: [Int])
    case invalidOutputShape(function: String, output: String, expected: [Int], provided: [Int])
    case unsupportedOutputCount(Int)
    case outputUnavailable(String)
    case contractMismatch(function: String, message: String)
    case unsupportedSpecializationOption(String)
}
```

### 5.6 Runtime usage snippets (README `:163-184`)

Stateless:

```swift
let bundle = try CoreAIModelBundle(contentsOf: bundleURL)
let session = try await bundle.makeStatelessSession()
let outputs = try await session.run(
    inputs: ["input_ids": inputIDs, "position_ids": positionIDs],
    outputShapes: ["logits": [1, tokenCount, bundle.document.metadata.vocabSize]]
)
```

Stateful (dynamic states resolved at session creation, no output shape needed
because logits are fully fixed `[1,1,V]`):

```swift
let bundle = try CoreAIModelBundle(contentsOf: bundleURL)
let session = try await bundle.makeStateSession(maxContextLength: 40960)
let outputs = try await session.run(
    inputs: ["input_ids": inputIDs, "position_ids": positionIDs]
)
```

Full runtime test showing the **serial-generation contract**
(`Tests/SwiftLMCoreAITests/CoreAIModelAssetTests.swift:56-135`):

```swift
        let session = try await bundle.makeStateSession(
            maxContextLength: min(32, bundle.maxContextLength)
        )
        // missing position_ids is a typed error:
        //   CoreAIModelAssetError.inputNotFound(function: "main", input: "position_ids")
        let first = try await session.run(
            inputs: [
                "input_ids": NDArray(scalars: [Int32(1)], shape: [1, 1]),
                "position_ids": NDArray(scalars: [Int32(0)], shape: [1, 1]),
            ]
        )
        let second = try await session.run(
            inputs: [
                "input_ids": NDArray(scalars: [Int32(2)], shape: [1, 1]),
                "position_ids": NDArray(scalars: [Int32(0), Int32(1)], shape: [1, 2]),
            ]
        )
        try await session.reset()
```

`docs/design/core-ai.md:123-126`:

> "The LFM2 stateful export is an explicit serial-generation contract:
> `input_ids` has shape `1x1`, while `position_ids` carries the **complete prefix
> range** for the current token. Callers preserve one `CoreAIStateSession` across
> calls and resolve its dynamic state shapes before the first call."

Argmax helper from the test (useful, because `NDArray` gives a raw pointer view):

```swift
private func lastTokenArgmax(_ logits: NDArray, vocabSize: Int) -> Int {
    let tokenCount = logits.shape.dropFirst().dropLast().reduce(1, *)
    let offset = (tokenCount - 1) * vocabSize
    return logits.view(as: Float16.self).withUnsafePointer { pointer, _, _ in
        var maximumIndex = 0
        var maximumValue = pointer[offset]
        for index in 1..<vocabSize where pointer[offset + index] > maximumValue {
            maximumIndex = index
            maximumValue = pointer[offset + index]
        }
        return maximumIndex
    }
}
```

---

## 6. `CoreAIExport` — the versioned Swift contract (format version 2)

### 6.1 Document shape

`Sources/CoreAIExport/CoreAIExportDocument.swift`:

```swift
public struct CoreAIExportDocument: Codable, Equatable, Sendable {
    public static let currentFormatVersion = 2

    public let formatVersion: Int
    public let metadata: Metadata
    public let program: CoreAIProgramContract
    public let rootRegion: Region

    public struct Metadata: Codable, Equatable, Sendable {
        public let name: String
        public let modelType: String
        public let target: Target
        public let maxContextLength: Int
        public let vocabSize: Int
    }

    public enum Target: String, Codable, Equatable, Sendable {
        case macOSDynamic = "macos_dynamic"
        case iOSStatic = "ios_static"
    }

    public struct Region: Codable, Equatable, Sendable {
        public let parameters: [ValueID]
        public let operations: [Operation]
        public let results: [ValueID]
    }

    public struct Operation: Codable, Equatable, Sendable {
        public let key: Int
        public let operands: [ValueID]
        public let results: [ValueID]
        public let parameterBindings: [ParameterBinding]
        public let stateBindings: [StateBinding]
        public let kind: OperationKind
    }

    public struct ParameterBinding: Codable, Equatable, Sendable {
        public let role: String
        public let tensorName: String
    }

    public struct StateBinding: Codable, Equatable, Sendable {
        public let role: String
        public let state: String
        public let axisIndex: Int
    }

    public indirect enum OperationKind: Codable, Equatable, Sendable {
        case primitive(Primitive)
        case residual(strategy: ResidualStrategy, body: Region)
        case parallel(merge: ParallelMergeStrategy, branches: [Region])
        case repeating(count: Int, body: Region)
        case conditional(condition: ConditionKind, then: Region, else: Region)
    }

    public struct Primitive: Codable, Equatable, Sendable {
        public let opcode: String
        public let attributes: JSONValue
    }
}
```

`OperationKind` is encoded with a **`tag` discriminator** (`"primitive"`,
`"residual"`, `"parallel"`, `"repeating"`, `"conditional"`) plus payload keys
`primitive|strategy|body|merge|branches|count|condition|then|else`.
`ValueID` encodes as a bare `Int` (`singleValueContainer`).

### 6.2 Program contract (functions / states / tensors)

`Sources/CoreAIExport/CoreAIProgramContract.swift`:

```swift
public struct CoreAIProgramContract: Codable, Equatable, Sendable {
    public let source: Source            // enum Source: String { case swiftLMIR = "swift_lmir" }
    public let execution: Execution      // enum Execution: String { case stateless, stateful }
    public let functions: [Function]

    public struct Function: Codable, Equatable, Sendable {
        public let name: String
        public let inputs: [Tensor]
        public let outputs: [Tensor]
        public let states: [Tensor]
    }

    public struct Tensor: Codable, Equatable, Sendable {
        public let name: String
        public let dataType: DataType
        public let dimensions: [Dimension]
    }

    public enum DataType: String, Codable, Equatable, Sendable {
        case int32, float16, bfloat16, float32
    }

    public struct Dimension: Codable, Equatable, Sendable {
        public let kind: Kind            // .fixed | .dynamic
        public let size: Int?
        public let symbol: String?
        public let minimum: Int?
        public let maximum: Int?

        public static func fixed(_ size: Int) -> Dimension
        public static func dynamic(_ symbol: String, minimum: Int, maximum: Int) -> Dimension
    }
}
```

### 6.3 Contract *derivation* — how states are inferred from the graph

`Sources/CoreAIExport/CoreAIProgramContractBuilder.swift`. This is the single most
instructive file for "how do I decide what Core AI states a model needs".

**Stateless main** (`:25-53`):

```swift
        let sequence = CoreAIProgramContract.Dimension.dynamic(
            "sequence_length", minimum: 1, maximum: configuration.maxContextLength
        )
        return CoreAIProgramContract(
            execution: .stateless,
            functions: [
                .init(
                    name: "main",
                    inputs: [
                        .init(name: "input_ids",    dataType: .int32, dimensions: [.fixed(1), sequence]),
                        .init(name: "position_ids", dataType: .int32, dimensions: [.fixed(1), sequence]),
                    ],
                    outputs: [
                        .init(name: "logits", dataType: .float16,
                              dimensions: [.fixed(1), sequence, .fixed(configuration.vocabSize)])
                    ],
                    states: []
                )
            ]
        )
```

**Stateful main** (`:55-206`) — walks the graph, groups mutable primitives by
*shape*, and emits one state tensor per group with a leading "layer axis":

- `AttentionAttributes` grouped by `(kvHeadCount, headDimension)` →
  `keyCache{suffix}` / `valueCache{suffix}`, `float16`,
  dims `[.fixed(groupLayerCount), .fixed(1), .fixed(kvHeads), prefixLength, .fixed(headDimension)]`
  and per-operation `StateBinding(role: "key_cache"|"value_cache", state:, axisIndex: layerOrdinal)`
- `ShortConvAttributes` grouped by `(hiddenSize, kernelSize)` → `convCache{suffix}`,
  `float16`, dims `[.fixed(count), .fixed(1), .fixed(hiddenSize), .fixed(kernelSize)]`,
  role `"conv_cache"`
- `StateSpaceAttributes` grouped by a derived shape → **two** states:
  - `stateSpaceConvCache{suffix}`, `float16`,
    `[.fixed(count), .fixed(1), .fixed(convolutionDimension), .fixed(kernelSize)]`
    where `convolutionDimension = 2 * groupCount * keyHeadDim + numHeads * valueHeadDim`
  - `stateSpaceRecurrentState{suffix}`, **`float32`**,
    `[.fixed(count), .fixed(1), .fixed(numHeads), .fixed(keyHeadDim), .fixed(valueHeadDim)]`
  - roles `"conv_cache"` and `"recurrent_state"`
- Suffix rule: empty string when there is exactly one group, otherwise the group
  index as a decimal string (`keyCache0`, `keyCache1`, …).
- `prefixLength = .dynamic("prefix_length", minimum: 1, maximum: maxContextLength)`

Stateful function signature:

```swift
                    inputs: [
                        .init(name: "input_ids",    dataType: .int32, dimensions: [.fixed(1), .fixed(1)]),
                        .init(name: "position_ids", dataType: .int32, dimensions: [.fixed(1), prefixLength]),
                    ],
                    outputs: [
                        .init(name: "logits", dataType: .float16,
                              dimensions: [.fixed(1), .fixed(1), .fixed(configuration.vocabSize)])
                    ],
```

Two hard errors:

```swift
        guard configuration.target == .macOSDynamic else {
            throw CoreAIExportError.invalidConfiguration(
                "stateful execution currently requires the macos_dynamic target")
        }
        ...
        guard !states.isEmpty else {
            throw CoreAIExportError.invalidConfiguration(
                "stateful execution requires at least one mutable LMIR operation")
        }
```

### 6.4 Exporter and opcode table

`Sources/CoreAIExport/CoreAIModelExporter.swift`:

```swift
    public func makeDocument(graph: ModelGraph, configuration: CoreAIExportConfiguration) throws -> CoreAIExportDocument
    public func makeDocument<Component: ModelComponent>(
        component: Component,
        namingConvention: any WeightNamingConvention,
        configuration: CoreAIExportConfiguration
    ) throws -> CoreAIExportDocument
    public func write(_ document: CoreAIExportDocument, to url: URL) throws
```

`makeDocument(graph:configuration:)` runs `GraphValidator.validate` +
`DimensionValidator.validate` (wrapping failures in `.invalidGraph`), then
`canonicalize(graph)`, then builds the contract, then encodes regions.

`write` uses `JSONEncoder` with **`[.prettyPrinted, .sortedKeys]`** and
`.atomic` write — this is what makes the document byte-deterministic.

Opcode table (`:135-201`) — **complete list of `Primitive.opcode` strings**:

| Swift attribute type | `opcode` |
|---|---|
| `AttentionAttributes` | `attention` |
| `LayerScaleAttributes` | `layer_scale` |
| `LinearAttributes` | `linear` |
| `MLPAttributes` | `mlp` |
| `MoEAttributes` | `moe` |
| `RMSNormAttributes` | `rms_norm` |
| `LayerNormAttributes` | `layer_norm` |
| `OutputHeadAttributes` | `output_head` |
| `PatchEmbeddingAttributes` | `patch_embedding` |
| `PerLayerInputAttributes` | `per_layer_input` |
| `PoolingAttributes` | `pooling` |
| `PositionEmbeddingAttributes` | `position_embedding` |
| `RoPEAttributes` | `rope` |
| `ShortConvAttributes` | `short_conv` |
| `StandardizeAttributes` | `standardize` |
| `StateSpaceAttributes` | `state_space` |
| `TokenEmbeddingAttributes` | `token_embedding` |

anything else ⇒ `CoreAIExportError.unsupportedPrimitive(String(reflecting: type(of: attributes)))`.

Errors (`CoreAIExportError.swift`): `.invalidConfiguration`, `.invalidGraph`,
`.unsupportedPrimitive`, `.invalidAttributePayload`, `.unsupportedFormatVersion`,
`.serializationFailed`.

`CoreAIExportConfiguration` init validates non-empty `name`/`modelType`,
positive `maxContextLength` and `vocabSize`; `execution` defaults to `.stateless`.

---

## 7. `swiftlm-ir` CLI (Swift executable)

`Sources/SwiftLMIR/SwiftLMIRCLI.swift`. Hand-rolled arg parser (no ArgumentParser).

**Complete flag set:**

| Flag | Required | Values |
|---|---|---|
| `--config <path>` | yes | HF `config.json` |
| `--output <path>` | yes | output JSON document |
| `--name <string>` | yes | contract/bundle name |
| `--target <macos\|ios>` | yes | `macos` → `.macOSDynamic`, `ios` → `.iOSStatic`, anything else → error `"--target must be macos or ios"` |
| `--max-context-length <int>` | no | must be `> 0`; defaults to `configuration.maxContextLength` from HF config |
| `--stateful` | no | boolean flag; sets `execution = .stateful`, otherwise `.stateless` |

Unknown leftover arguments → `"unknown arguments: …"`. On success it prints the
output path to stdout; on failure it writes `swiftlm-ir: <error>` to stderr and
`exit(1)`.

Body (`:8-44`):

```swift
            let configuration = try HuggingFaceConfigDecoder().decode(from: arguments.configURL)
            let exportConfiguration = try CoreAIExportConfiguration(
                name: arguments.name,
                modelType: configuration.modelType,
                target: arguments.target,
                maxContextLength: arguments.maxContextLength ?? configuration.maxContextLength,
                vocabSize: configuration.modelConfig.vocabSize,
                execution: arguments.execution
            )
            let exporter = CoreAIModelExporter()
            let graph = try ModelFamilyRegistry.resolveModelGraph(
                modelType: configuration.modelType,
                config: configuration.modelConfig
            )
            let resolvedGraph = ParameterResolver().resolve(
                graph: graph,
                convention: try ModelFamilyRegistry.namingConvention(for: configuration.modelType)
            )
            let document = try exporter.makeDocument(graph: resolvedGraph, configuration: exportConfiguration)
            try exporter.write(document, to: arguments.outputURL)
            print(arguments.outputURL.path)
```

---

## 8. Full export command sequence (copyable)

From `docs/design/core-ai.md:128-163` and `README.md:74-123`:

```bash
# Build the Swift graph exporter.
xcrun swift build -c release --product swiftlm-ir

# Emit a deterministic document.
xcrun swift run swiftlm-ir \
  --config /path/to/config.json \
  --output /tmp/model.json \
  --name model \
  --target macos

# Validate the document before invoking Apple's exporter.
PYTHONPATH=python/src python3 -m swiftlm_coreai.cli validate /tmp/model.json

# Install the Python bridge in an isolated environment.
python3 -m venv .venv
.venv/bin/pip install -e python

# Export a stateless Swift contract (model_id can be a HF repo id OR a local dir).
.venv/bin/swiftlm-coreai export /tmp/model.json \
    Qwen/Qwen3-0.6B \
    --output-dir /tmp/coreai-model \
    --overwrite

# Same command, different family — no Python-side dispatch.
.venv/bin/swiftlm-coreai export /tmp/lfm2.json \
    LiquidAI/LFM2.5-1.2B-Instruct \
    --output-dir /tmp/coreai-lfm2 \
    --overwrite

# Derive mutable KV / ShortConv state in Swift, then lower the same contract.
xcrun swift run swiftlm-ir \
  --config /path/to/lfm2/config.json \
  --output /tmp/lfm2-stateful.json \
  --name lfm2-stateful \
  --target macos \
  --stateful

.venv/bin/swiftlm-coreai export /tmp/lfm2-stateful.json \
    LiquidAI/LFM2.5-1.2B-Instruct \
    --output-dir /tmp/coreai-lfm2-stateful \
    --overwrite

# Inspect a generated asset with Apple's toolchain.
xcrun coreai-build inspect --json /tmp/coreai-model/model.aimodel
```

**`xcrun coreai-build inspect --json <asset>` is the only `coreai-build`
invocation in the repo.** Subcommand `inspect`, flag `--json`.

`swiftlm-coreai` CLI, verbatim from `python/src/swiftlm_coreai/cli.py:12-24`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swiftlm-coreai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("document", type=Path)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("document", type=Path)
    export_parser.add_argument("model_id")
    export_parser.add_argument("--output-dir", type=Path, required=True)
    export_parser.add_argument("--overwrite", action="store_true")
    return parser
```

`validate` prints:
`valid format={formatVersion} model_type={modelType} target={target}`;
`ExportError` → prints `"{code}: {message}"` and returns exit code **2**.

---

## 9. Python side: `swiftlm_coreai` package

Module map (line counts):

| File | Lines | Role |
|---|---|---|
| `document.py` | 351 | strict validator/parser of the Swift JSON contract |
| `lowering.py` | 1207 | **generic** LMIR → `torch.nn.Module` lowerer |
| `ir_export.py` | 295 | orchestration: HF snapshot → lower → coreai export → bundle |
| `bundle.py` | 221 | write/validate Apple `metadata.json` (`metadata_version 0.2`) |
| `weights.py` | 63 | lazy safetensors resolver honoring `*.safetensors.index.json` |
| `program.py` | 75 | low-level `coreai_torch.TorchConverter` escape hatch |
| `exporter.py` | 30 | `validate_document` / `export_model` |
| `cli.py` | 52 | argparse entry point |
| `errors.py` | 13 | `ExportError(code, message)` |

`__init__.py` `__all__`: `ExportDocument`, `ExportError`, `export_model`,
`export_torch_module`, `validate_document`.

### 9.1 `program.py` — the low-level `coreai_torch` escape hatch (verbatim core)

```python
def export_torch_module(
    module: Any,
    reference_inputs: Mapping[str, Any],
    output_path: Path,
    *,
    input_names: Sequence[str],
    output_names: Sequence[str],
    state_names: Sequence[str] = (),
    dynamic_shapes: Mapping[str, Any] | None = None,
) -> Path:
    """Export a PyTorch module as an optimized Core AI source asset.

    This is the escape hatch for model families that are not in Apple's
    high-level registry. State names are explicit and must be mutated by the
    module during forward execution so Core AI can surface them as states.
    """
    try:
        import coreai_torch
        import torch
        from coreai_torch import TorchConverter
    except ImportError as error:
        raise ExportError(
            "missing_coreai_dependencies",
            "Install the pinned Python dependencies from python/pyproject.toml",
        ) from error

    if not output_path.name.endswith(".aimodel"):
        raise ExportError("invalid_output", "output_path must end with .aimodel")
    ...
    def export_fn(model: Any) -> Any:
        with torch.no_grad():
            exported = torch.export.export(
                model,
                args=(),
                kwargs=dict(reference_inputs),
                dynamic_shapes=dynamic_shapes,
                strict=False,
            )
        return exported.run_decompositions(coreai_torch.get_decomp_table())

    try:
        module.eval()
        converter = TorchConverter()
        converter.add_pytorch_module(
            module,
            export_fn=export_fn,
            input_names=tuple(input_names),
            output_names=tuple(output_names),
            state_names=tuple(state_names),
        )
        program = converter.to_coreai()
        program.optimize()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        program.save_asset(output_path)
    except Exception as error:
        raise ExportError("coreai_program_export_failed", str(error)) from error
    return output_path
```

**`coreai_torch` API confirmed:** `coreai_torch.get_decomp_table()`;
`coreai_torch.TorchConverter()`;
`TorchConverter.add_pytorch_module(module, export_fn=, input_names=, output_names=, state_names=)`;
`TorchConverter.to_coreai()` → program; `program.optimize()`;
`program.save_asset(Path)`.
Uses `torch.export.export(model, args=(), kwargs=..., dynamic_shapes=..., strict=False)`
then `.run_decompositions(...)`.

**An `.aimodel` is a directory**, not a file: `bundle.py` requires
`asset_path.suffix == ".aimodel" and asset_path.is_dir()`, and the export test
asserts `(output / "metadata.json").is_file()` inside the `.aimodel`.

### 9.2 Stateful export path uses `coreai_models.export.macos.export_to_coreai`

`ir_export.py:158-186` **verbatim**:

```python
def _export_stateful_model(document, model, reference_inputs, dynamic_shapes, asset_path) -> None:
    try:
        from coreai_models.export.macos import export_to_coreai
    except ImportError as error:
        raise ExportError(
            "missing_coreai_dependencies",
            "Stateful export requires Apple's coreai-models package",
        ) from error

    try:
        program = export_to_coreai(
            model,
            reference_inputs,
            dynamic_shapes=dynamic_shapes,
            input_names=tuple(tensor["name"] for tensor in document.function["inputs"]),
            output_names=tuple(tensor["name"] for tensor in document.function["outputs"]),
            state_names=tuple(tensor["name"] for tensor in document.function["states"]),
        )
        program.optimize()
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        program.save_asset(asset_path)
    except Exception as error:
        raise ExportError("coreai_program_export_failed", str(error)) from error
```

Reference-input synthesis (`ir_export.py:101-155`) — how dynamic dims become
`torch.export.Dim`:

```python
        for axis, dimension in enumerate(tensor["dimensions"]):
            if dimension["kind"] == "fixed":
                shape.append(dimension["size"]); continue
            minimum = dimension["minimum"]; maximum = dimension["maximum"]
            reference = min(maximum, max(minimum, 8))     # reference size 8, clamped
            shape.append(reference)
            if minimum != maximum:
                symbol = dimension["symbol"]
                dynamic[axis] = symbols.setdefault(
                    symbol, torch.export.Dim(symbol, min=minimum, max=maximum)
                )
```

- `position_ids` gets `torch.arange(shape[1]).unsqueeze(0)`; requires shape
  `[1, sequence]` else `ExportError("invalid_contract", "position_ids must have shape [1, sequence]")`
- `input_ids` gets `torch.ones(...)`; everything else `torch.zeros(...)`
- for stateful, states are packed as a **tuple** under the key `"states"`:
  `inputs["states"] = tuple(state_values)`, `dynamic_shapes["states"] = tuple(state_shapes)`

### 9.3 Bundle layout produced by `export_ir_language_model`

`ir_export.py:19-98`. Output tree:

```
<output-dir>/<name>/
├── <name>.aimodel/            # directory asset
│   └── metadata.json          # Core AI's own asset metadata
├── swiftlm-program.json       # the Swift contract, re-serialized indent=2 sort_keys=True
├── tokenizer/                 # copied HF tokenizer assets
│   ├── tokenizer.json         # REQUIRED
│   ├── tokenizer_config.json
│   ├── special_tokens_map.json
│   ├── added_tokens.json
│   ├── chat_template.jinja
│   ├── vocab.json
│   ├── merges.txt
│   ├── tokenizer.model
│   ├── sentencepiece.bpe.model
│   └── spiece.model
└── metadata.json              # Apple LanguageBundle metadata (metadata_version 0.2)
```

`_copy_tokenizer_assets` hard-fails when `tokenizer.json` is absent:
`ExportError("tokenizer_export_failed", f"HF bundle is missing tokenizer.json: …")`.
It **never instantiates a Transformers tokenizer class** — assets are `shutil.copy2`'d.
`config.json` is deliberately *not* copied (asserted by
`python/tests/test_ir_export.py:26`).

`bundle.write_language_bundle_metadata` emits (verbatim from `bundle.py:44-66`):

```python
    metadata: dict[str, Any] = {
        "metadata_version": METADATA_VERSION,          # "0.2"
        "kind": "llm",
        "name": name,
        "assets": {
            "main": resolved_asset_name,               # f"{name}.aimodel"
            "contract": contract_name,                 # "swiftlm-program.json"
            "contract_sha256": contract_sha256,
        },
        "language": {
            "tokenizer": "tokenizer",
            "vocab_size": vocab_size,
            "max_context_length": max_context_length,
            "embedded_tokenizer": True,
            "function_map": function_map or {"main": ["main"]},
        },
        "source": {
            "model_definition": "swift_lmir",
            "format_version": 2,
            "hf_model_id": model_id,
        },
        "compression": compression,                    # None by default
    }
```

Written atomically via `metadata.json.tmp` → `Path.replace`, `indent=2, sort_keys=True`.

`validate_language_bundle` re-checks: metadata_version, kind, name,
`assets.main` is an existing `.aimodel` **directory**, contract file exists,
`contract_sha256` is 64 hex chars and matches, contract `formatVersion == 2` and
`program.source == "swift_lmir"`, `source.model_definition/format_version/hf_model_id`,
`language.tokenizer` non-empty, `vocab_size`, `max_context_length`,
`embedded_tokenizer` bool → if true `tokenizer/tokenizer.json` must exist,
`function_map` values are non-empty string arrays, and **path-escape protection**
(`asset_path.is_relative_to(bundle_root)`).

### 9.4 Source-contract cross-check (multimodal aware)

`ir_export.py:253-274`:

```python
def _validate_source_contract(document, config) -> None:
    actual_model_type = config.get("model_type")
    if actual_model_type != document.model_type:
        raise ExportError("model_type_mismatch", ...)
    language_config = config.get("text_config", config)     # ← falls back to root
    ...
    actual_vocab_size = language_config.get("vocab_size")
    if actual_vocab_size != document.metadata["vocabSize"]:
        raise ExportError("vocab_size_mismatch", ...)
```

So for VLM-shaped configs (`qwen3_5`), the vocab size is read from
`config["text_config"]["vocab_size"]` (test: `python/tests/test_ir_export.py:37-65`,
uses `248320`).

### 9.5 `weights.py` — safetensors binding resolver

```python
class SafetensorWeightStore:
    """Resolve Swift parameter bindings directly from Hugging Face safetensors."""

    def __init__(self, model_directory: Path, torch: Any, dtype: Any) -> None: ...
    def tensor(self, name: str, *, dtype: Any | None = None) -> Any: ...
```

- reads `*.safetensors.index.json` `weight_map` if present, otherwise scans
  `sorted(model_directory.glob("*.safetensors"))`
- `safe_open(path, framework="pt", device="cpu")`, `handle.get_tensor(name).to(dtype=…).contiguous()`
- errors: `weights_not_found`, `invalid_weight_index`, `weight_not_found`,
  `missing_coreai_dependencies`

`compute_precision` default in `export_ir_language_model` is **`"float16"`**
(`_resolve_dtype` accepts `float16|bfloat16|float32`).

---

## 10. The generic lowerer (`lowering.py`) — how a JSON graph becomes a torch module

### 10.1 Structure

- `TorchGraphLowerer(document, weights, torch)` — constructor runs
  `_validate_lowering_contract(document.raw["rootRegion"], "root")` **before any
  weight is loaded**, so unsupported semantics fail fast with an operation path
  like `root.operations[2].branches[0]`.
- `.make_stateless_model()` → `nn.Module.forward(input_ids, position_ids)`
- `.make_stateful_model()` → `nn.Module.forward(input_ids, position_ids, states: tuple)`
- `.make_model()` dispatches on `document.execution`; unknown → `ExportError("unsupported_execution", …)`
- Both assert exactly one output: `"Language-model graphs must produce one logits tensor"`

`_RegionModule.__new__` is a factory that closes over the `torch` module and
builds an SSA value environment keyed by integer ValueIDs:

```python
            def forward(self, parameters, input_ids, position_ids, states, iteration_index=None):
                values = {vid: v for vid, v in zip(self.parameter_ids, parameters, strict=True)}
                for operation in self.operations:
                    operands = tuple(values[vid] for vid in operation.operand_ids)
                    results = operation(operands, input_ids, position_ids, states, iteration_index)
                    for vid, value in zip(operation.result_ids, results, strict=True):
                        values[vid] = value
                return tuple(values[vid] for vid in self.result_ids)
```

Structural ops:
- `residual` — only `strategy == "add"`; `operand + body_output` elementwise zip
- `parallel` — only `merge == "add"` (any other merge → `"has no axis contract"`)
- `repeating` — Python `for index in range(count)` (fully unrolled at trace time),
  passing `index` down as `iteration_index`
- `conditional` — compile-time layer-index selection; requires a repeating parent
  (`"Layer-index condition requires a repeating parent"`); the condition JSON must
  be `{"layerIndices": [...]}` (also accepts `{"layerIndices": {"_0": [...]}}`,
  i.e. Swift's associated-value encoding)

### 10.2 Supported primitives in the lowerer

`_validate_lowering_contract` `supported_primitives` (`lowering.py:902-914`) —
**note this is smaller than the document-level `SUPPORTED_PRIMITIVES`**:

```python
    supported_primitives = {
        "attention", "layer_norm", "layer_scale", "linear", "mlp", "moe",
        "output_head", "rms_norm", "short_conv", "state_space", "token_embedding",
    }
```

`document.py:15-33` `SUPPORTED_PRIMITIVES` additionally allows
`patch_embedding`, `per_layer_input`, `pooling`, `position_embedding`,
`standardize`, `rope` — so those pass *document validation* but fail
*lowering* with `ExportError("unsupported_lowering", f"{path}: primitive {opcode!r}")`.
That is exactly the "vision primitives fail before graph construction" behavior
the README promises.

### 10.3 Parameter role tables (`_parameter_roles`) — the binding contract

| opcode | required roles | optional roles |
|---|---|---|
| `token_embedding` | `embedding_table` | — |
| `rms_norm` | `scale` (only if `withScale != False`) | — |
| `layer_norm` | `scale` (if `affine`) | `bias` |
| `layer_scale` | `layer_scalar` | — |
| `linear` | `weight` (+`bias` if `attributes["bias"]`) | — |
| `mlp` | `up_proj`, `down_proj` (+`gate_proj` when `gating != none`) | `*_bias` variants when `attributes["bias"]` |
| `moe` | `router`, `expert_{i}_gate_proj`, `expert_{i}_up_proj`, `expert_{i}_down_proj` for `i in 0..<expertCount` (+`expert_bias` when `useExpertBias`) | — |
| `short_conv` | `in_proj`, `conv_weight`, `out_proj` | `in_proj_bias`, `conv_bias`, `out_proj_bias` |
| `state_space` | `in_proj_qkv`, `in_proj_z`, `in_proj_b`, `in_proj_a`, `out_proj`, `scale`, `conv_weight`, `dt_bias`, `A_log` | — |
| `attention` | `q_proj`, `k_proj`, `o_proj` (+`v_proj` unless `valueProjectionSource != dedicatedProjection`; +`q_layernorm`,`k_layernorm` when `qkNorm != none`; +`*_bias` when `bias`) | — |
| `output_head` | `weight` (+`bias`) | — |

Missing roles → `"{path}: missing parameter roles [...]"`;
extra roles → `"{path}: unused parameter roles [...]"`.

**State role tables:**
- `attention` → `{key_cache, value_cache}` (both or neither)
- `short_conv` → `{conv_cache}`
- `state_space` → `{conv_cache, recurrent_state}` (both or neither)
- anything else → `"{path}: unused state roles [...]"`

### 10.4 Explicit capability rejections (fail before graph construction)

`attention` (`lowering.py:1080-1109`) rejects when any of these is non-nil/unsupported:
`sharedKeyValueSourceLayerIndex`, `valueNorm`, `window` (sliding window),
`rope.scaling` ("scaled RoPE"), `outputGate != sigmoidPackedInQProj`,
`qkNorm not in {none, rmsNorm, rmsNormUnitOffset}`,
`valueProjectionSource != dedicatedProjection`.
Message: `"{path}: attention features scaled RoPE, window, …"`.

`mlp`: activation ∈ `{gelu, relu, silu, swish}`, gating ∈ `{none, glu, geglu, swiglu}`.

`moe`: `expertCount > 0`, `0 < expertsPerToken <= expertCount`,
`gateKind ∈ {topK, sigmoidTopK}`, and the expert MLP must have
`inputSize == outputSize`, activation ∈ `{silu, swish}`, gating `== swiglu`,
`bias == False` — otherwise
`"{path}: MoE expert MLP different input/output sizes, activation 'gelu', gating 'geglu', projection bias"`.

`state_space`: `variant == "gated_deltanet"`, `computeDType == "float32"`,
`numHeads % groupCount == 0`, `normEpsilon > 0`.

### 10.5 Which Apple Core AI *primitives* the lowerer emits

Constructed in `_make_primitive.__init__` (`lowering.py:351-384`):

```python
            if opcode == "attention":
                from coreai_models.primitives.macos.sdpa import SDPA
                scale = attributes.get("attentionScale")
                if scale is None:
                    scale = attributes["headDimension"] ** -0.5
                self.sdpa = SDPA(scale=scale, is_causal=attributes["causal"])
            if opcode == "moe":
                from coreai_models.primitives.macos.switch import SwitchGLU
                expert_mlp = attributes["expertMLP"]
                self.switch_glu = SwitchGLU(
                    expert_mlp["inputSize"],
                    expert_mlp["intermediateSize"],
                    attributes["expertCount"],
                    bias=False,
                )
                for projection in ("gate_proj", "up_proj", "down_proj"):
                    stacked = torch.stack(
                        [tensors[f"expert_{index}_{projection}"]
                         for index in range(attributes["expertCount"])],
                        dim=0,
                    ).unsqueeze(0)
                    switch_projection = getattr(self.switch_glu, projection)
                    switch_projection.weight = torch.nn.Parameter(stacked, requires_grad=False)
            if opcode == "state_space":
                from coreai_torch.composite_ops import GatedDeltaUpdate
                self.gated_delta_update = GatedDeltaUpdate(use_qk_l2_norm=True)
```

Plus, inside attention forward (`:784-799`):

```python
                from coreai_models.primitives.macos.cache import KVCache
                key_cache, key_index = self._state("key_cache", states)
                value_cache, value_index = self._state("value_cache", states)
                if key_index != value_index:
                    raise RuntimeError("Key and value cache axis indices must match")
                cache = KVCache(key_cache, value_cache)
                key, projected_value = cache.update_and_fetch(
                    key_index, offset, key, projected_value,
                    seq_len=position_ids.shape[-1],
                    query_len=query_length,
                )
```

and, for in-place state writes (`:653-677`, `:700-720`):

```python
                from coreai_models.primitives._ops import mutable_slice_update
                begin = torch.tensor((axis_index,) + (0,) * (cache.dim() - 1), dtype=torch.int32, device=device)
                end   = torch.tensor((axis_index + 1,) + tuple(cache.shape[1:]), dtype=torch.int32, device=device)
                mutable_slice_update(x=cache, update=update.unsqueeze(0), begin=begin, end=end)
```

**⭐ Apple Core AI Python primitive inventory confirmed by this repo:**

| Import path | Symbol | Signature as used |
|---|---|---|
| `coreai_models.primitives.macos.sdpa` | `SDPA` | `SDPA(scale: float, is_causal: bool)`; `sdpa(q, k, v)` |
| `coreai_models.primitives.macos.switch` | `SwitchGLU` | `SwitchGLU(input_size, intermediate_size, expert_count, bias=False)`; projections `.gate_proj/.up_proj/.down_proj` whose `.weight` is `[1, E, out, in]`; call `switch_glu(x, indices.to(torch.uint16))` |
| `coreai_models.primitives.macos.cache` | `KVCache` | `KVCache(key_cache, value_cache)`; `.update_and_fetch(layer_index, offset, key, value, seq_len=, query_len=)` |
| `coreai_models.primitives._ops` | `mutable_slice_update` | `mutable_slice_update(x=, update=, begin=, end=)` with int32 index tensors |
| `coreai_torch.composite_ops` | `GatedDeltaUpdate` | `GatedDeltaUpdate(use_qk_l2_norm=True)`; call `(q, k, v, decay, beta, initial_state) -> (output, updated_state)`, all float32, heads-major `[B, H, T, D]` |
| `coreai_models.export.macos` | `export_to_coreai` | `export_to_coreai(model, reference_inputs, dynamic_shapes=, input_names=, output_names=, state_names=)` |

**Routing indices must be `torch.uint16`** for `SwitchGLU` —
`self.switch_glu(value, active_indices.to(torch.uint16))`. That is a surprising,
easily-missed detail.

### 10.6 MoE routing semantics (verbatim, `lowering.py:477-523`)

```python
        def _moe(self, value: Any) -> Any:
            router_logits = torch.nn.functional.linear(value, self.router).float()
            gate_kind = _enum_case(self.attributes["gateKind"])
            top_k = self.attributes["expertsPerToken"]
            normalize = self.attributes["normalizeRoutingWeights"]

            if gate_kind == "topK":
                if normalize:
                    top_logits, active_indices = torch.topk(router_logits, top_k, dim=-1, largest=True)
                    active_scores = torch.softmax(top_logits, dim=-1)
                else:
                    routing_scores = torch.softmax(router_logits, dim=-1)
                    active_scores, active_indices = torch.topk(routing_scores, top_k, dim=-1, largest=True)
            elif gate_kind == "sigmoidTopK":
                routing_scores = torch.sigmoid(router_logits)
                selection_scores = routing_scores
                if self.attributes["useExpertBias"]:
                    selection_scores = selection_scores + self.expert_bias.float()
                _, active_indices = torch.topk(selection_scores, top_k, dim=-1, largest=True)
                active_scores = torch.gather(routing_scores, -1, active_indices)
                if normalize:
                    active_scores = active_scores / active_scores.sum(dim=-1, keepdim=True)
            else:
                raise RuntimeError(f"Unsupported MoE gate kind {gate_kind}")

            active_scores = active_scores * self.attributes["routedScalingFactor"]
            active_outputs = self.switch_glu(value, active_indices.to(torch.uint16))
            weighted = active_outputs * active_scores.to(value.dtype).unsqueeze(-1)
            return weighted.sum(dim=-2).to(value.dtype)
```

Key semantic: **expert bias affects selection only, not the weights** — a
classic DeepSeek/LFM2 detail with a dedicated test
(`test_sigmoid_top_k_moe_uses_bias_only_for_selection`).

### 10.7 Attention with packed sigmoid gate + RoPE (verbatim highlights)

```python
            output_gate = self.attributes.get("outputGate")
            gate = None
            if output_gate is not None:
                output_gate_kind = _enum_case(output_gate)
                if output_gate_kind == "sigmoidPackedInQProj":
                    query = query.view(*input_shape, head_count, head_dimension * 2)
                    query, gate = query.chunk(2, dim=-1)     # split WITHIN each head
                    gate = gate.reshape(*input_shape, -1)
```

RoPE is implemented inline (no Apple primitive), NeoX-style `rotate_half`:

```python
        def _apply_rope(self, query, key, position_ids):
            rope = self.attributes.get("rope")
            if rope is None: return query, key
            dimension = rope["dimension"]; base = rope["base"]
            indices = torch.arange(0, dimension, 2, device=query.device).float()
            inverse_frequency = 1.0 / (base ** (indices / dimension))
            frequencies = position_ids.float().unsqueeze(-1) * inverse_frequency
            embedding = torch.cat((frequencies, frequencies), dim=-1)
            cosine = embedding.cos().to(query.dtype).unsqueeze(1)
            sine = embedding.sin().to(query.dtype).unsqueeze(1)
            ...
```

Partial RoPE (`dimension < head_dim`) is supported by concatenating the untouched
tail. GQA expansion is `_repeat_kv` (expand + reshape).

Stateful attention position slicing (`:778-783`):

```python
            query_positions = position_ids
            if "key_cache" in self.states_by_role:
                query_length = query.shape[-2]
                offset = position_ids.shape[-1] - query_length
                query_positions = position_ids.narrow(-1, offset, query_length)
```

i.e. `position_ids` carries the whole prefix, and the query's own positions are
the trailing `query_length` entries.

### 10.8 GatedDeltaNet (Qwen3.5) lowering — verbatim structure

`lowering.py:525-651`. Highlights:

- `mixed_qkv = linear(x, in_proj_qkv).transpose(-1,-2)`; either prepend the
  conv cache or left-pad `kernel_size - 1`; depthwise `conv1d(groups=convolution_dimension)`;
  take `[..., -sequence_length:]`; `silu`
- `convolution_dimension = 2 * group_count * key_head_dimension + head_count * value_head_dimension`
- split into `(key_dimension, key_dimension, value_dimension)`; reshape;
  `repeat_interleave(head_count // group_count, dim=2)` for q/k
- `beta = sigmoid(linear(x, in_proj_b))`
- `decay = -A_log.float().exp() * softplus(linear(x, in_proj_a).float() + dt_bias.float())`
- `gate = linear(x, in_proj_z).reshape(B, T, H, Dv)`
- recurrence:
```python
            recurrence_output, updated_recurrent = self.gated_delta_update(
                query.transpose(1, 2).float(),
                key.transpose(1, 2).float(),
                projected_value.transpose(1, 2).float(),
                decay.transpose(1, 2).float(),
                beta.transpose(1, 2).float(),
                initial_state,
            )
```
- post-norm: RMSNorm with `normEpsilon`, multiply by `scale.float()`, then
  `* silu(gate.float())`, reshape, `linear(out_proj)`
- `A_log`, `dt_bias`, `scale` are force-loaded as **float32** regardless of the
  store dtype (`lowering.py:329-331`):
```python
        if opcode == "state_space" and role in {"A_log", "dt_bias", "scale"}:
            dtype = torch.float32
```

### 10.9 ShortConv (LFM2) lowering

```python
        def _short_conv(self, value, states):
            projected = linear(value, self.in_proj, in_proj_bias).transpose(-1, -2)
            gate, candidate, source = projected.chunk(3, dim=-2)
            mixed = gate * source
            ...
            convolution = conv1d(padded, self.conv_weight, conv_bias, groups=self.attributes["hiddenSize"])
            ...
            output = candidate * convolution
            return linear(output.transpose(-1, -2).contiguous(), self.out_proj, out_proj_bias)
```

Chunk order is **(B=gate, C=candidate, x=source)** — matches
`Sources/LMIR/IR/ShortConvAttributes.swift:4-5`:
`in_proj(D -> 3D) -> chunk(B, C, x) -> B*x -> depthwise_conv1d -> C*conv_out -> out_proj`.

### 10.10 RMSNorm / LayerNorm details

```python
        def _rms_norm(self, value):
            input_dtype = value.dtype
            normalized = value.float()
            variance = normalized.pow(2).mean(-1, keepdim=True)
            normalized = normalized * torch.rsqrt(variance + self.attributes["epsilon"])
            normalized = normalized.to(input_dtype)
            if not self.attributes.get("withScale", True):
                return normalized
            scale = self.scale + self.attributes.get("weightBias", 0)
            return normalized * scale
```

`weightBias` is the Gemma "unit offset" (`(1 + w)`); `withScale=False` supports
norm-only ops.

QK norm (`_qk_norm`) uses `qkNormEpsilon` defaulting to `1e-6` and adds
`weight_bias = 1` for `rmsNormUnitOffset`.

---

## 11. Document validator (`document.py`) — the strict JSON schema

Constants:

```python
SUPPORTED_FORMAT_VERSION = 2
SUPPORTED_TARGETS = {"macos_dynamic", "ios_static"}
SUPPORTED_EXECUTION_MODES = {"stateless", "stateful"}
SUPPORTED_DATA_TYPES = {"int32", "float16", "bfloat16", "float32"}
```

Enforced invariants (each raises `ExportError(code, message)`):

- `formatVersion == 2` → `unsupported_format_version`
- metadata must contain `name, modelType, target, maxContextLength, vocabSize`;
  the two numbers must be positive ints (bools rejected via `_is_integer`)
- `program.source == "swift_lmir"`; exactly **one** function; named **`main`**
- tensor names unique across inputs ∪ outputs ∪ states
- `stateless` must declare **no** states; `stateful` **must** declare states
- dimension `fixed` needs positive `size`; `dynamic` needs non-empty `symbol`,
  integer `minimum`/`maximum`, `minimum > 0`, `maximum >= minimum`
- SSA discipline per region: every operand must already be `defined`; result IDs
  unique and not previously defined; region `results` must be defined
- `parameterBindings`: role non-empty and unique per operation; `tensorName` non-empty
- `stateBindings`: forbidden entirely when `execution == "stateless"`
  (`"stateless operation has state at {path}"`); `state` must be a declared state
  name; `axisIndex` non-negative int; roles unique

---

## 12. Model declaration DSL (`LMArchitecture` / `ModelDeclarations`)

### 12.1 `ModelComponent` — the SwiftUI-like protocol

`Sources/LMArchitecture/Declaration/ModelComponent.swift:40-71` (verbatim):

```swift
public protocol ModelComponent: Sendable {
    associatedtype Attributes: OperationAttributes, Sendable, Codable = Never
    associatedtype Body: ModelComponent = Never

    var attributes: Attributes { get }
    var operationSignature: OperationSignature { get }

    @ModelComponentBuilder var body: Body { get }
}
```

Defaults: composite components (`Attributes == Never`) `fatalError` on
`.attributes`; primitive components (`Body == Never`) `fatalError` on `.body`;
default `operationSignature` is `OperationSignature(operandArity: .exact(1), resultArity: .exact(1))`.
`extension Never: ModelComponent` closes the recursion.

`Sources/LMArchitecture/Exports.swift` is literally:

```swift
// Re-export LMIR so `import LMArchitecture` provides all LMIR types.
@_exported import LMIR
```

Graph construction entry points (`Declaration/LanguageModel.swift`):

```swift
extension NormalizedModel { public init(_ component: some ModelComponent) throws }
extension ModelGraph      { public init(_ component: some ModelComponent) throws }
```

Component files present under
`Sources/LMArchitecture/Declaration/Components/`: `Attention`, `DeltaNet`,
`Group`, `Linear`, `MLP`, `MoE`, `Norm`, `OutputHead`, `PatchEmbedding`,
`Pooling`, `PositionEmbedding`, `ShortConv`, `Standardize`, `StateSpace`,
`Structural`, `TokenEmbedding`, `Transformer`.
Structural: `ConditionalComponent`, `ForEach`, `LayerStack`, `OptionalComponent`,
`TupleComponent`, `ModelComponentBuilder`, `ModelDeclaration`.
Validation: `Canonicalizer`, `DimensionValidator`, `GraphValidator`,
`LLMProfileValidator`, `ModelValidator`, `SemanticNormalizer`.

### 12.2 A real declaration — LFM2 (verbatim)

`Sources/Models/LFM2/LFM2.swift:60-82`:

```swift
    @ModelComponentBuilder
    public var body: some ModelComponent {
        TokenEmbedding(vocabSize: config.vocabSize, embeddingSize: config.hiddenSize)

        LayerStack(0..<config.layerCount) { layerIndex in
            if convLayerIndices.contains(layerIndex) {
                LFM2ConvDecoderLayer(
                    config: config, convLCache: convLCache,
                    useMoE: isMoELayer(layerIndex))
            } else {
                LFM2AttnDecoderLayer(
                    config: config, headDimension: headDimension,
                    useMoE: isMoELayer(layerIndex))
            }
        }

        RMSNorm(dimension: config.hiddenSize, epsilon: config.normEps)
        OutputHead(
            inputSize: config.hiddenSize,
            vocabSize: config.vocabSize,
            tiedToEmbedding: config.tiedEmbeddings
        )
    }
```

and a decoder layer (`:117-162`):

```swift
struct LFM2ConvDecoderLayer: ModelComponent {
    @ModelComponentBuilder
    var body: some ModelComponent {
        Residual {
            RMSNorm(dimension: config.hiddenSize, epsilon: config.normEps)
            ShortConv(hiddenSize: config.hiddenSize, kernelSize: convLCache)
        }
        Residual {
            RMSNorm(dimension: config.hiddenSize, epsilon: config.normEps)
            LFM2FeedForward(config: config, useMoE: useMoE)
        }
    }
}
```

`LFM2.validate(_:)` errors explicitly on missing `layer_types`, `conv_L_cache`,
`expertsPerToken`, `moeIntermediateSize` — no defaults (philosophy #7).

### 12.3 `ModelFamilyRegistry` — the single routing point

`Sources/Models/ModelFamilyRegistry.swift:6-90` (verbatim `family(for:)`):

```swift
    public static func family(for modelType: String) -> ModelFamily? {
        switch modelType.lowercased() {
        case "llama", "qwen2", "qwen3", "mistral", "gemma", "gemma2",
             "phi", "phi3", "starcoder2", "gpt_neox", "internlm2",
             "deepseek", "yi", "baichuan", "chatglm", "mixtral",
             "qwen2_moe", "deepseek_v2", "arctic", "dbrx":
            return .transformer
        case "gemma3_text":            return .gemma3Text
        case "gemma4", "gemma4_text":  return .gemma4
        case "qwen3_5", "qwen3_vl", "qwen2_5_vl", "qwen2_vl": return .qwen35
        case "lfm2", "lfm2_moe":       return .lfm2
        case "cohere", "command-r":    return .cohere
        default:                       return nil
        }
    }
```

Plus `resolveModelGraph(modelType:config:)`,
`resolveEmbeddingBackboneGraph(modelType:config:)` (only `gemma3_text`), and
`namingConvention(for:)` → `Gemma3TextFamilyNaming` / `Gemma4FamilyNaming` /
`Qwen35FamilyNaming` / `LFM2FamilyNaming` / `LlamaFamilyNaming`.

README notes `nemotron_h` is **explicitly rejected** by the current loader
(`README.md:431`).

### 12.4 `WeightNamingConvention` — role → HF tensor name

`Sources/Models/Qwen35/Qwen35FamilyNaming.swift` (verbatim state-space + MoE
sections; these define the exact `parameterBindings` a Core AI document carries):

```swift
        if let attrs = attributes as? MoEAttributes {
            let moePrefix = "\(prefix).mlp"
            return [ParameterBinding(role: "router", tensorName: "\(moePrefix).gate.weight")]
                + WeightNamingHelpers.moeExperts(
                    expertCount: attrs.expertCount,
                    expertsPrefix: "\(moePrefix).experts",
                    gateProjection: "gate_proj.weight",
                    upProjection: "up_proj.weight",
                    downProjection: "down_proj.weight"
                )
        }

        if let _ = attributes as? StateSpaceAttributes {
            let ssPrefix = "\(prefix).linear_attn"
            return [
                ParameterBinding(role: "in_proj_qkv", tensorName: "\(ssPrefix).in_proj_qkv.weight"),
                ParameterBinding(role: "in_proj_z",   tensorName: "\(ssPrefix).in_proj_z.weight"),
                ParameterBinding(role: "in_proj_b",   tensorName: "\(ssPrefix).in_proj_b.weight"),
                ParameterBinding(role: "in_proj_a",   tensorName: "\(ssPrefix).in_proj_a.weight"),
                ParameterBinding(role: "out_proj",    tensorName: "\(ssPrefix).out_proj.weight"),
                ParameterBinding(role: "scale",       tensorName: "\(ssPrefix).norm.weight"),
                ParameterBinding(role: "conv_weight", tensorName: "\(ssPrefix).conv1d.weight"),
                ParameterBinding(role: "dt_bias",     tensorName: "\(ssPrefix).dt_bias"),
                ParameterBinding(role: "A_log",       tensorName: "\(ssPrefix).A_log"),
            ]
        }
```

Prefix is `model.language_model.layers.\(layerIndex)` for Qwen3.5 (VLM-shaped
checkpoints). LFM2 MoE experts use `w1/w3/w2` (`gate/up/down`) under
`…feed_forward.experts.{i}`; Llama/Mixtral use `…block_sparse_moe.experts.{i}.w1|w3|w2`.

The `WeightNamingHelpers.moeExperts` helper (added in `537f24d`) emits the
`expert_{i}_{gate|up|down}_proj` roles the Python `SwitchGLU` path expects —
i.e. **canonical per-expert safetensors, not a pre-stacked `gate_up_proj`**.
This was a behavioral change: LFM2 previously bound
`expert_gate_up_proj` / `expert_down_proj` (stacked) and now binds per-expert
`w1/w3/w2`.

---

## 13. Worked example: a full v2 export document (from tests, verbatim)

MoE fixture from `python/tests/test_lowering.py:520-668` — this is the best
copyable illustration of the on-disk contract:

```json
{
  "formatVersion": 2,
  "metadata": {
    "name": "moe", "modelType": "test", "target": "macos_dynamic",
    "maxContextLength": 8, "vocabSize": 2
  },
  "program": {
    "source": "swift_lmir",
    "execution": "stateless",
    "functions": [{
      "name": "main",
      "inputs": [
        {"name": "input_ids", "dataType": "int32",
         "dimensions": [{"kind":"fixed","size":1},
                        {"kind":"dynamic","symbol":"sequence_length","minimum":1,"maximum":8}]},
        {"name": "position_ids", "dataType": "int32",
         "dimensions": [{"kind":"fixed","size":1},
                        {"kind":"dynamic","symbol":"sequence_length","minimum":1,"maximum":8}]}
      ],
      "outputs": [
        {"name": "logits", "dataType": "float32",
         "dimensions": [{"kind":"fixed","size":1},
                        {"kind":"dynamic","symbol":"sequence_length","minimum":1,"maximum":8},
                        {"kind":"fixed","size":2}]}
      ],
      "states": []
    }]
  },
  "rootRegion": {
    "parameters": [],
    "operations": [
      { "key": 0, "operands": [], "results": [0],
        "parameterBindings": [{"role":"embedding_table","tensorName":"embedding.weight"}],
        "stateBindings": [],
        "kind": {"tag":"primitive","primitive":{"opcode":"token_embedding",
                 "attributes":{"vocabSize":2,"embeddingSize":2}}}},
      { "key": 1, "operands": [0], "results": [1],
        "parameterBindings": [
          {"role":"router","tensorName":"router.weight"},
          {"role":"expert_0_gate_proj","tensorName":"expert.0.gate"},
          {"role":"expert_0_up_proj","tensorName":"expert.0.up"},
          {"role":"expert_0_down_proj","tensorName":"expert.0.down"},
          ... , {"role":"expert_bias","tensorName":"expert.bias"}
        ],
        "stateBindings": [],
        "kind": {"tag":"primitive","primitive":{"opcode":"moe","attributes":{
          "expertCount": 3, "expertsPerToken": 2,
          "gateKind": {"sigmoidTopK": {}},
          "normalizeRoutingWeights": true,
          "routedScalingFactor": 1.25,
          "useExpertBias": true,
          "expertMLP": {"inputSize":2,"outputSize":2,"intermediateSize":3,
                        "activation":{"silu":{}},"gating":{"swiglu":{}},"bias":false}
        }}}},
      { "key": 2, "operands": [1], "results": [2],
        "parameterBindings": [{"role":"weight","tensorName":"head.weight"}],
        "stateBindings": [],
        "kind": {"tag":"primitive","primitive":{"opcode":"output_head","attributes":{
          "inputSize":2,"vocabSize":2,"tiedToEmbedding":false,"bias":false}}}}
    ],
    "results": [2]
  }
}
```

**Swift enum encoding gotcha:** Swift's synthesized `Codable` for enums with no
payload emits `{"silu": {}}`, `{"swiglu": {}}`, `{"sigmoidTopK": {}}`. Python
handles both forms:

```python
def _enum_case(value: Any) -> str:
    if isinstance(value, str): return value
    if isinstance(value, dict) and len(value) == 1: return next(iter(value))
    raise ExportError("invalid_enum", repr(value))
```

Attention attribute payload (from `test_attention_lowering.py:186-205`) — note
every optional field is present as explicit `null`:

```json
"attributes": {
  "hiddenSize": 4, "headCount": 2, "kvHeadCount": 2, "headDimension": 2,
  "causal": true, "bias": false, "attentionScale": null, "rope": null,
  "qkNorm": {"none": {}}, "qkNormEpsilon": 1e-06,
  "outputGate": {"sigmoidPackedInQProj": {}},
  "valueProjectionSource": {"dedicatedProjection": {}},
  "valueNorm": null, "window": null, "sharedKeyValueSourceLayerIndex": null
}
```

Stateful ShortConv fixture states + bindings (`test_lowering.py:690-706`):

```json
"states": [{
  "name": "convCache", "dataType": "float32",
  "dimensions": [{"kind":"fixed","size":1},{"kind":"fixed","size":1},
                 {"kind":"fixed","size":2},{"kind":"fixed","size":3}]
}]
...
"stateBindings": [{"role": "conv_cache", "state": "convCache", "axisIndex": 0}]
```

Stateful GatedDeltaNet fixture states (`test_state_space_lowering.py:196-224`):

```json
"states": [
 {"name":"stateSpaceConvCache","dataType":"float32",
  "dimensions":[{"kind":"fixed","size":1},{"kind":"fixed","size":1},
                {"kind":"fixed","size":10},{"kind":"fixed","size":3}]},
 {"name":"stateSpaceRecurrentState","dataType":"float32",
  "dimensions":[{"kind":"fixed","size":1},{"kind":"fixed","size":1},
                {"kind":"fixed","size":2},{"kind":"fixed","size":2},{"kind":"fixed","size":3}]}
]
```

(the real Swift builder emits `float16` for the conv cache and `float32` for the
recurrent state — see §6.3; the test fixture uses float32 for both because it is
a hand-written document.)

Note the stateful `position_ids` symbol is `"position_length"` in the test
fixtures, while the Swift builder emits `"prefix_length"` — the symbol name is
free-form; only min/max/kind matter.

---

## 14. Swift-side export tests (usage patterns)

`Tests/CoreAIExportTests/CoreAIExportTests.swift`. Key assertions:

```swift
    @Test("Stateful export derives persistent state from Swift IR")
    ...
        #expect(function.states.map(\.name) == ["keyCache", "valueCache", "convCache"])
        #expect(function.states[0].dimensions[0] == .fixed(1))
        #expect(function.states[0].dimensions[3] == .dynamic("prefix_length", minimum: 1, maximum: 64))
        #expect(document.rootRegion.operations[0].stateBindings == [
            .init(role: "key_cache", state: "keyCache", axisIndex: 0),
            .init(role: "value_cache", state: "valueCache", axisIndex: 0),
        ])
```

```swift
    @Test("Stateful export derives DeltaNet convolution and recurrent state")
    ...
        #expect(function.states.map(\.name) == ["stateSpaceConvCache", "stateSpaceRecurrentState"])
        #expect(function.states[0].dataType == .float16)
        #expect(function.states[0].dimensions == [.fixed(1), .fixed(1), .fixed(32), .fixed(4)])
        #expect(function.states[1].dataType == .float32)
        #expect(function.states[1].dimensions == [.fixed(1), .fixed(1), .fixed(4), .fixed(3), .fixed(5)])
```

(For `numHeads=4, groupCount=2, keyHeadDim=3, valueHeadDim=5, convKernelSize=4`:
`2*2*3 + 4*5 = 32` ✓.)

Determinism test:

```swift
        let first  = try exporter.makeDocument(component: Transformer(config: config),
                                               namingConvention: LlamaFamilyNaming(),
                                               configuration: configuration)
        let second = try exporter.makeDocument(component: Transformer(config: config),
                                               namingConvention: LlamaFamilyNaming(),
                                               configuration: configuration)
        #expect(first == second)
```

Layer unrolling: `Transformer` layers are **fully unrolled** by canonicalization —
`#expect(document.rootRegion.operations.contains { if case .repeating = $0.kind { return true }; return false } == false)`
and both `model.layers.0.self_attn.q_proj.weight` and
`model.layers.1.self_attn.q_proj.weight` appear.

JSON scalar-type test proves `Int`s stay numbers and `Bool`s stay booleans
(`payload["kvHeadCount"] == .number(1)`, `payload["causal"] == .bool(true)`).

Also: stateful + `.iOSStatic` target throws; stateful with no mutable op throws.

---

## 15. Real-model verification evidence (release notes)

`docs/releases/0.11.0-alpha.1.md:66-98` — quoted verbatim because these are the
only concrete numeric Core AI results in the repo:

> - Real `yujiepan/lfm2-tiny-random` stateless logits matched Hugging Face with
>   `0.001220703125` maximum absolute error and exact Top-5 token IDs.
> - The same Swift graph's stateful and stateless paths matched exactly across
>   sequential tokens in Python.
> - A generated stateless LFM2 `.aimodel` ran through
>   `CoreAIModelBundle.makeStatelessSession()` in Swift and returned the
>   contract-declared logits shape.
> - A generated stateful LFM2 `.aimodel` passed asset inspection and the Swift
>   runtime state-persistence/reset regression test.
> - The local `yujiepan/lfm2-moe-tiny-random` bundle lowered from Swift LMIR with
>   canonical per-expert weights; stateless and stateful logits matched exactly
>   across four decode steps, and both Core AI 27 assets passed inspection.
> - The local `yujiepan/qwen3.5-tiny-random` text graph matched the Hugging Face
>   float32 reference with maximum logits error `1.52e-6`. …
>
> "Larger production model bundles still require model-specific validation before
> publishing an application asset. **Core AI beta compiler warnings may appear on
> Apple Silicon during these smoke tests**; the process must still complete and
> the output must be compared with the reference model."

The Python equivalence harness lives in `python/tests/test_real_lfm2.py`:
it compares `TorchGraphLowerer(...).make_stateless_model()` against
`AutoModelForCausalLM.from_pretrained(model_directory, dtype=torch.float32)`
with `rtol=2e-3, atol=2e-3` **and** exact top-5 IDs, then steps the stateful model
one token at a time against the stateless prefix with `rtol=1e-5, atol=1e-5`.

---

## 16. Build / test / CI recipes (copyable)

From `README.md:715-756`:

```bash
swift build

# Focused test target with a hard timeout
perl -e 'alarm shift; exec @ARGV' 120 \
  xcodebuild test \
  -scheme swift-lm-Package \
  -destination 'platform=macOS' \
  -only-testing:SwiftLMTests

# Build once, then run one suite at a time (real-model / Metal-heavy work)
perl -e 'alarm shift; exec @ARGV' 120 \
  xcodebuild build-for-testing -scheme swift-lm-Package -destination 'platform=macOS'

perl -e 'alarm shift; exec @ARGV' 120 \
  xcodebuild test-without-building -scheme swift-lm-Package -destination 'platform=macOS' \
  -only-testing:SwiftLMTests/ReleaseSmokePromptStateTests
```

Runners:

| Script | Purpose |
|---|---|
| `scripts/xcodebuild/build-supported-platforms.sh [--timeout SECONDS]` | iOS + Mac Catalyst package builds (new in `db7a802`) |
| `scripts/xcodebuild/test-timeout.sh <seconds> -- <command…>` | hard timeout + peak-RSS process-tree sampler; exit `124` on timeout |
| `scripts/xcodebuild/test-hang-guard.sh [--repeats N] [--timeout S] -- <cmd…>` | repeated runs with lockdir + diagnostics into `.test-artifacts/hang-guard/<ts>/` |
| `scripts/benchmarks/run-qwen35-vision-tests.sh` | `--destination --derived-data-path --build-timeout --test-timeout --suite --include-real --skip-build` |
| `scripts/benchmarks/run-generation-pipeline.sh` | split generation benchmarks |
| `scripts/benchmarks/run-prefill-artifact-validation.sh [--timeout] [--qwen-baseline-dir] [--qwen-experimental-dir]` | prefill route promotion gate |
| `scripts/benchmarks/run-lfm25-a1b-readiness.sh --timeout 120` | LFM2.5 A1B readiness |

`scripts/xcodebuild/build-supported-platforms.sh` (verbatim tail, from `db7a802`):

```bash
build_destination() {
  local label="$1"
  local destination="$2"
  echo "[platform-build] ${label}: ${destination}"
  scripts/xcodebuild/test-timeout.sh "$timeout_seconds" -- \
    xcodebuild build \
      -quiet \
      -scheme swift-lm-Package \
      -destination "$destination"
}

build_destination "iOS" "generic/platform=iOS"
build_destination "Mac Catalyst" "generic/platform=macOS,variant=Mac Catalyst"
```

⚠️ The script *rejects* `--timeout` values above 120: `"--timeout must be an
integer between 1 and 120"`.

Swift package test targets: `MetalCompilerTests`, `ModelsTests`,
`CoreAIExportTests`, `SwiftLMCoreAITests`, `SwiftLMFoundationModelsTests`,
`SwiftLMTests`. Scheme name is `swift-lm-Package`.

`AGENTS.md:100-102` / `CLAUDE.md:576-582`: **do not use `swift test`** —
"`swift test` は使わない（Metal metallib が見つからずクラッシュ）"; and running
multiple modules concurrently hangs on GPU resource contention.

---

## 17. Gotchas / footguns catalogue

1. **`expectFrequentReshapes` is a landmine.** `CoreAIModelAsset.specialize`
   hard-rejects it: *"expectFrequentReshapes is disabled until the current Core AI
   runtime is compatible"*; the design doc calls it "a reproducible failure" in
   the current beta.
2. **`CoreAI` is an SDK framework, `CoreAILanguageModels` is an SPM module named
   `CoreAILM` as a product.** Getting this wrong produces "no such module" errors.
3. **`AIModelAsset.summary(includingStatistics:)` returns an Optional** — `nil`
   is a real case (`missingSummary`).
4. **`CoreAIStateSession` supports exactly ONE output tensor.**
   `unsupportedOutputCount(Int)` otherwise. Image states are rejected outright.
5. **Dynamic axes appear as `-1` in `NDArrayDescriptor.shape`.** Dynamic *state*
   shapes must be resolved at session creation; dynamic *output* shapes must be
   passed on **every** `run()` call (`missingDynamicOutputShape`).
6. **`.aimodel` is a directory.** `is_dir()` checks throughout `bundle.py`.
7. **Stateful export requires `--target macos`** (`macos_dynamic`);
   `ios_static` throws `invalidConfiguration`.
8. **Stateful export requires at least one Attention / ShortConv / StateSpace op**
   in the graph, otherwise `"stateful execution requires at least one mutable LMIR
   operation"`.
9. **Stateful `input_ids` is `[1,1]` and `position_ids` is `[1, prefix_length]`.**
   Passing a full sequence to a stateful bundle is a contract violation.
10. **`SwitchGLU` expects `torch.uint16` expert indices** and `[1, E, out, in]`
    stacked weights.
11. **MoE expert bias is selection-only.** Adding it to the returned weights
    silently changes outputs.
12. **`A_log`, `dt_bias`, `scale` in `state_space` are forced to float32**;
    loading them at the store dtype silently degrades DeltaNet.
13. **`tokenizer.json` is mandatory** for the Python export; there is no
    Transformers fallback.
14. **`config.json` is intentionally NOT copied into the exported bundle.**
15. **The document validator accepts more primitives than the lowerer supports**
    (`patch_embedding`, `pooling`, `position_embedding`, `standardize`,
    `per_layer_input`, `rope`). Vision/embedding graphs validate then fail at
    lowering with an operation path.
16. **`parallel` merge must be `add`**; anything else →
    `"…parallel merge 'concat' has no axis contract"`.
17. **`residual` strategy must be `add`.**
18. **`conditional` requires a `repeating` ancestor** to supply `iteration_index`.
19. **Every Core AI test in this repo silently no-ops without its env var.**
    A green `SwiftLMFoundationModelsTests` run proves nothing about the runtime.
20. **VLM prompt contract asymmetry:** `.text` requires *exactly 1* image
    placeholder (then expands); `.tokens` requires *exactly `imageTokenCount`*.
    Same error case (`invalidImagePlaceholderCount`) with different `expected`.
21. **`SwiftLMVisionLanguageModel` owns mutable KV state** — you must `reset()`
    between unrelated requests, and it is an `actor`, so cross-request ordering is
    serialized for you but state is not.
22. **`makeLanguageModel()` throws on a VLM bundle** and vice versa
    (`visionLanguageModelRequiresVisionAPI` / `languageModelDoesNotSupportVision`).
23. **The exported contract's SHA-256 is checked at load**; hand-editing
    `swiftlm-program.json` breaks `CoreAIModelBundle`.
24. **Docs are internally inconsistent.** `docs/using-swift-lm.md:5-10` still says
    "Swift 6.2+ … macOS 26+, iOS 26+, visionOS 26+ … from 0.10.0" while
    `Package.swift` says Swift tools 6.4 / macOS 27 / iOS 27 and README says
    `from: "0.11.0"`. Trust `Package.swift`.
25. **`swiftlm-ir` prints errors as `swiftlm-ir: <Swift error dump>`** — not
    localized descriptions; expect `CoreAIExportError` case dumps.
26. **`ExportError` exit code from `swiftlm-coreai` is `2`, not `1`.**
27. **Reference input size for dynamic axes is hardcoded to `min(max, max(min, 8))`**
    in `_build_reference_inputs` — a model whose graph misbehaves at seq-len 8 will
    fail at export time.
28. **Do not batch heavy real-model suites into one `xcodebuild test`** — repeated
    GPU allocations cause `unexpected exit`; use `build-for-testing` +
    `test-without-building`.
29. **`hazardTrackingModeUntracked` models must not be simultaneously alive during
    benchmarks** — "GPU cache interference causes anomalous speedups (up to 4.6x)
    on the last-measured model" (`CLAUDE.md`, RotorQuant benchmark methodology note).

---

## 18. The 0.10 direct-Metal compatibility surface (context, not the focus)

Retained public API (`README.md:207-227`, `AGENTS.md:437-457`):

- generation: `ModelBundleLoader`, `LanguageModelContainer`, `LanguageModelContext`,
  `ModelInput`, `GenerationParameters`, `PromptSnapshot`
- embeddings: `ModelBundleLoader`, `TextEmbeddingContainer`, `TextEmbeddingContext`,
  `TextEmbeddingInput`
- staged/advanced: `PreparedPrompt`, `ExecutablePrompt`

`GenerationParameters` fields (`Sources/SwiftLM/GenerationParameters.swift`):
`maxTokens: Int?`, `maxReasoningTokens: Int?`, `streamChunkTokenCount: Int`,
`temperature: Float`, `topP: Float`, `topK: Int?`, `minP: Float`,
`repetitionPenalty: Float?`, `presencePenalty: Float?`,
`repetitionContextSize: Int`, `reasoning: ReasoningOptions`.

Canonical example (`README.md:233-268`):

```swift
import SwiftLM

let container = try await ModelBundleLoader().load(repo: "LiquidAI/LFM2.5-1.2B-Instruct")

let input = ModelInput(
    chat: [
        .system("You are a concise assistant."),
        .user("Write a haiku about Metal shaders.")
    ],
    promptOptions: .init(isThinkingEnabled: true)
)

let stream = try await container.generate(
    input,
    parameters: GenerationParameters(
        maxTokens: 128, streamChunkTokenCount: 8,
        temperature: 0.6, topP: 0.9, reasoning: .separate
    )
)

for await event in stream {
    switch event {
    case .text(let text): print(text, terminator: "")
    case .reasoning(let reasoning): fputs(reasoning, stderr)
    case .completed(let info):
        print("\nGenerated \(info.tokenCount) tokens at \(info.tokensPerSecond) tok/s")
    }
}
```

Notable 0.10 subsystems (documented in `CLAUDE.md`, not re-derived here):
STAF execution cache (`model.staf` next to the safetensors),
`InferencePolicy` (KV-cache scheme + `maximumSequenceLength` + layout mode),
**RotorQuant** Clifford-rotor KV-cache quantization
(`rotorQ8Group32ScaleF16` = scheme id `0x70`, `rotorQ4Group64ScaleF16` = `0x71`;
unit-quaternion rotors `[s, b₁₂, b₁₃, b₂₃]` in Float16, deterministic LCG init
with Knuth multiplier `6364136223846793005`, buffer layout
`[layer × kvHeadCount × ceil(headDim/3) × 4]`), Metal 4 barrier work, and
automatic kernel fusion via `FusionContract` / `KernelScaffold` /
`SynthesizedFragment`. Benchmarked claim: EmbeddingGemma-300M BF16 prefill
**66.2 emb/s vs MLX 62.0 emb/s (+6.8%)** after auto-fusion (was 44.3 emb/s).

---

## 19. Timeline of Core AI work (git log, newest first)

```
db7a802 2026-07-18 18:38  Add Core AI vision language model adapter          (+710/-8, 17 files)
537f24d 2026-07-18 02:37  Add Core AI MoE and Qwen3.5 state-space lowering   (+1761/-71, 22 files)
b2cf3b4 2026-07-18 00:49  Build Core AI-first declarative export pipeline    (+3932/-1047, 35 files)
e956e56 2026-07-17 09:07  Add Core AI bundle validation
10ac849 2026-07-12 22:22  Centralize Hugging Face model routing and config decoding
2d142d8 2026-07-12 19:48  Add stateful LFM2 Core AI export
30bd665 2026-07-12 19:13  Complete Core AI model export paths
97b6294 2026-07-12 18:39  Add Core AI export and runtime support             (+2270/-245, 30 files)
d30e589                   Prepare swift-lm 0.10.0 release
```

`b2cf3b4` is the pivotal commit: it **deleted `python/src/swiftlm_coreai/lfm2.py`
(535 lines of model-family-specific Python)** and replaced it with the generic
`lowering.py` (+859) and `ir_export.py` (+263). That is the concrete realization
of "Python lowers the contract generically and does not rebuild model-family
graphs."

---

## 20. Source inventory (every file/URL actually read this session)

Repo root:
- `README.md` (767 lines, full)
- `PHILOSOPHY.md` (full)
- `CLAUDE.md` (full, via system context)
- `AGENTS.md` (sections: 1-50, 47-130, 194-300, 377-530; headings index for whole file)
- `Package.swift` (full)
- `Package.resolved` (full)

Docs:
- `docs/design/core-ai.md` (full, 186 lines)
- `docs/releases/0.11.0-alpha.1.md` (full)
- `docs/production-readiness.md` (full)
- `docs/README.md` (full)
- `docs/using-swift-lm.md` (heading index + lines 1-60)

Swift sources (full reads unless noted):
- `Sources/SwiftLMFoundationModels/CoreAILanguageModelBundle.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageModel.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionConfiguration.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageGenerating.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageGenerationOptions.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageInput.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageModelError.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguageOutput.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionLanguagePrompt.swift`
- `Sources/SwiftLMFoundationModels/SwiftLMVisionPromptTokenExpander.swift`
- `Sources/SwiftLMCoreAI/CoreAIModelAsset.swift`
- `Sources/SwiftLMCoreAI/CoreAIModelAssetError.swift`
- `Sources/SwiftLMCoreAI/CoreAIModelBundle.swift`
- `Sources/SwiftLMCoreAI/CoreAIStateSession.swift`
- `Sources/SwiftLMCoreAI/CoreAIStatelessSession.swift`
- `Sources/SwiftLMCoreAI/CoreAIExecutableSession.swift`
- `Sources/CoreAIExport/CoreAIExportConfiguration.swift`
- `Sources/CoreAIExport/CoreAIExportDocument.swift`
- `Sources/CoreAIExport/CoreAIExportError.swift`
- `Sources/CoreAIExport/CoreAIProgramContract.swift`
- `Sources/CoreAIExport/CoreAIProgramContractBuilder.swift`
- `Sources/CoreAIExport/CoreAIModelExporter.swift`
- `Sources/SwiftLMIR/SwiftLMIRCLI.swift`
- `Sources/LMArchitecture/Declaration/ModelComponent.swift`
- `Sources/LMArchitecture/Declaration/LanguageModel.swift`
- `Sources/LMArchitecture/Exports.swift`
- `Sources/LMIR/IR/AttentionAttributes.swift` (lines 1-140)
- `Sources/LMIR/IR/StateSpaceAttributes.swift`
- `Sources/LMIR/IR/MoEAttributes.swift`
- `Sources/LMIR/IR/ShortConvAttributes.swift`
- `Sources/Models/ModelFamilyRegistry.swift`
- `Sources/Models/LFM2/LFM2.swift` (lines 1-162)
- `Sources/Models/Qwen35/Qwen35FamilyNaming.swift`
- `Sources/SwiftLM/GenerationParameters.swift` (public-symbol grep)
- `Sources/SwiftLM/ModelBundleLoader.swift`, `LanguageModelContainer.swift` (public-symbol grep)

Python:
- `python/pyproject.toml`
- `python/src/swiftlm_coreai/__init__.py`, `errors.py`, `exporter.py`, `cli.py`,
  `program.py`, `weights.py`, `bundle.py`, `document.py`, `ir_export.py`
- `python/src/swiftlm_coreai/lowering.py` (full, 1207 lines, in 3 reads)
- `python/tests/test_ir_export.py` (full)
- `python/tests/test_real_lfm2.py` (full)
- `python/tests/test_lowering.py` (lines 1-120, 226-360, 520-760)
- `python/tests/test_attention_lowering.py` (lines 1-209)
- `python/tests/test_state_space_lowering.py` (lines 174-366)

Tests (Swift):
- `Tests/SwiftLMFoundationModelsTests/SwiftLMFoundationModelBundleTests.swift` (full)
- `Tests/SwiftLMCoreAITests/CoreAIModelAssetTests.swift` (full)
- `Tests/CoreAIExportTests/CoreAIExportTests.swift` (full)

Scripts:
- `scripts/xcodebuild/test-timeout.sh` (full)
- `scripts/xcodebuild/test-hang-guard.sh` (lines 1-60)
- `scripts/xcodebuild/build-supported-platforms.sh` (full, via `git show db7a802`)
- `scripts/benchmarks/run-qwen35-vision-tests.sh` (lines 1-60)

Git:
- `git log --oneline -50`
- `git show --stat` for `db7a802 537f24d b2cf3b4 97b6294 30bd665 2d142d8 10ac849 e956e56`
- `git show db7a802 -- README.md docs/… scripts/… Package.swift` (full diff)
- `git show 537f24d -- Sources/Models/… Sources/LMIR/… Sources/LMArchitecture/…` (full diff)

No URLs were fetched; everything is from the local clone.

---

## 21. Open questions / UNVERIFIED

1. **Exact type name of `engine.encodeImage(at:)`'s return value.** Only
   `.tokenCount` is used. Likely `EmbeddedInput` / `VLMEmbeddedInput`. UNVERIFIED.
2. **Exact type of the value returned by `engine.generate(...)`.** It is an
   `AsyncSequence` with mutating `setStopReason(_:)` and readable `stopReason`
   — probably a class (reference semantics inside a `let`). Name UNVERIFIED.
3. **Full `StopReason` case list.** Only `.eos` observed.
4. **Full `SamplingConfiguration` API.** Only the static `.greedy` observed.
5. **Full `KVCacheStrategy` case list.** Only `.auto` observed.
6. **Full `ModelBundle.ComponentKey` case list.** Only `.vision`, `.embedding`,
   `.main` observed.
7. **`CoreAILanguageModel`'s own generation API** — this repo only *constructs* it
   (`makeLanguageModel`), never calls generate on it.
8. **`SpecializationOptions` full field list.** Only `.default` and
   `.expectFrequentReshapes` observed.
9. **`AIModelCache.Policy` cases.** Only `.default` observed.
10. **`InferenceFunctionDescriptor`'s descriptor enum name** (the thing that has
    an `.ndArray(NDArrayDescriptor)` case). Pattern-matched but never named.
11. **`NDArrayDescriptor.interleaveLayout` type/semantics.** Passed through only.
12. **Whether `coreai-build` has subcommands beyond `inspect`.** Only
    `xcrun coreai-build inspect --json <asset>` appears in this repo.
13. **How Apple's official VLM exporter produces the three assets.** The repo
    says "Official `coreai-models` exporter emits `vision`, `embedding`, and
    `main` assets" (`docs/design/core-ai.md:105`) but contains no invocation of it.
14. **`coreai_models.primitives.macos.*` full inventory.** Only `sdpa.SDPA`,
    `switch.SwitchGLU`, `cache.KVCache`, and `_ops.mutable_slice_update` are used.
15. **`GatedDeltaUpdate`'s other constructor arguments** beyond `use_qk_l2_norm`.
16. **`function_map` semantics** in Apple's `metadata.json` — this repo writes
    `{"main": ["main"]}` and reads `language.functionMap?.name(for: "main")`,
    implying role→function-name mapping, but the full schema is UNVERIFIED.
17. **`compression` field in bundle metadata** — always `None` here.
18. **Whether `metadata_version` "0.2" has other `kind` values** beyond `"llm"`
    and `"vlm"`.
19. **iOS-static Core AI export path.** `--target ios` produces `ios_static`
    documents but stateful is rejected and no iOS asset appears in tests.
20. **What `xgrammar` is used for** in the `coreai-models` dependency graph
    (structured output/grammar-constrained decoding is the obvious guess) —
    UNVERIFIED from this repo.
