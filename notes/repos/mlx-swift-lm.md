# ml-explore/mlx-swift-lm — deep dive notes

**Local clone:** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-swift-lm`
**HEAD at time of reading:** `3cbf928b5eb24190e8952725699ae6a3bb02824d` — `Integration tests: build on both macOS 26 and 27 SDKs (#464)` — authored `2026-07-24 09:01:37 -0700` by Charlie Le <charlie_le@apple.com>
**Branch:** `main` (clone depth 50)
**License:** MIT (`LICENSE`)

Everything below was read from the checked-out source in this session. Where a claim is not
directly grounded in a file I read, it is marked **UNVERIFIED**.

---

## 1. What this repo is

From `README.md:1-19`:

> # MLX Swift LM
>
> MLX Swift LM is a Swift package to build tools and applications with large language models (LLMs) and vision language models (VLMs) in [MLX Swift](https://github.com/ml-explore/mlx-swift).
>
> > [!IMPORTANT]
> > The `main` branch is a _new_ major version number: 3.x.  In order
> > to decouple from tokenizer and downloader packages some breaking
> > changes were introduced. …
>
> > [!IMPORTANT]
> > We use `swift-format` to keep the code formatting consistent.  CI has this pinned to `603.0.0` right now.
>
> …
> For some example applications and tools that use MLX Swift LM, check out [MLX Swift Examples](https://github.com/ml-explore/mlx-swift-examples).

Key relationship to `mlx-swift-examples`: **this repo is the library; mlx-swift-examples is the app/tool
repo.** The former `Tools/llm-tool`, `Applications/…` trees are *not* in this repo (references to
`../../Tools/llm-tool` in `Libraries/MLXLLM/README.md:68` and `Libraries/MLXVLM/README.md:82` are dead
links pointing at mlx-swift-examples). `Libraries/MLXLMCommon/Documentation.docc/developing.md:39-64`
explains the workflow for developing against a local checkout:

> You will want to have mlx-swift-examples (or your own project) open in
> Xcode with a local checkout of mlx-swift-lm (your fork). … drag the `mlx-swift-lm` _directory_ onto the top item (the mlx-swift-examples project) in the Xcode navigator and chose _reference files in place_

Repo tree (492 files) top level:

```
.github/  IntegrationTesting/  Libraries/  Tests/  scripts/  skills/  tools/
ACKNOWLEDGMENTS.md CODE_OF_CONDUCT.md CONTRIBUTING.md LICENSE Package.swift README.md
.gitignore .pre-commit-config.yaml .spi.yml .swift-format
```

---

## 2. Package.swift — targets, traits, versions

`Package.swift:1-14`:

```swift
// swift-tools-version: 6.1
import CompilerPluginSupport
import PackageDescription

let package = Package(
    name: "mlx-swift-lm",
    platforms: [
        .macOS(.v14),
        .iOS(.v17),
        .tvOS(.v17),
        .visionOS(.v1),
    ],
```

**Products (9 libraries)** — `Package.swift:15-43`:
`MLXLLM`, `MLXVLM`, `MLXLMCommon`, `MLXEmbedders`, `MLXHuggingFace`, `MLXFoundationModels`,
`MLXGuidedGeneration`, `BenchmarkHelpers`, `IntegrationTestHelpers`.

**Traits** — `Package.swift:44-59` (verbatim):

```swift
    traits: [
        // Gates the MLXLanguageModel adapter for Apple's FoundationModels
        // framework. Default-on. Disabling the trait compiles MLXFoundationModels
        // to an empty library: the entire `MLXLanguageModel` / `MLXLanguageModel.Executor`
        // surface requires FoundationModels types that are not available on platforms
        // older than iOS/macOS/visionOS 27.0, and the MLXDownloadProgress observable
        // (whose only producer is that adapter) is gated alongside it. Consumers
        // targeting older OS versions can still use this package for MLXLLM /
        // MLXLMCommon / MLXEmbedders etc. by turning the trait off.
        .trait(
            name: "FoundationModelsIntegration",
            description:
                "Enables the MLXLanguageModel adapter for Apple's FoundationModels framework. Disabling removes the MLXLanguageModel / MLXLanguageModel.Executor types."
        ),
        .default(enabledTraits: ["FoundationModelsIntegration"]),
    ],
```

**Dependencies** — `Package.swift:60-66`:

```swift
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift", .upToNextMinor(from: "0.31.4")),
        // 602.0.0 floor: swift.org publishes signed prebuilt swift-syntax artifacts only for
        // >= 602 tags on current toolchains; a 600.x/601.x resolution falls back to the full
        // source compile of swift-syntax.
        .package(url: "https://github.com/swiftlang/swift-syntax.git", "602.0.0" ..< "604.0.0"),
    ],
```

Note there is **no** dependency on swift-transformers / swift-huggingface in `Package.swift` — the
whole point of 3.x is that tokenizer + downloader are protocols supplied by the consumer.

**Targets** (paths, notable settings):

| Target | Path | Deps |
|---|---|---|
| `MLXLLM` | `Libraries/MLXLLM` | MLXLMCommon, MLX, MLXNN, MLXOptimizers |
| `MLXVLM` | `Libraries/MLXVLM` | MLXLMCommon, MLX, MLXNN, MLXOptimizers |
| `MLXLMCommon` | `Libraries/MLXLMCommon` | MLX, MLXNN, MLXOptimizers |
| `MLXEmbedders` | `Libraries/MLXEmbedders` | MLX, MLXNN, MLXLMCommon |
| `BenchmarkHelpers` | `Libraries/BenchmarkHelpers` | MLXLMCommon, MLXLLM, MLXVLM, MLXEmbedders, MLX |
| `IntegrationTestHelpers` | `Libraries/IntegrationTestHelpers` | same as BenchmarkHelpers |
| `MLXHuggingFaceMacros` | `Libraries/MLXHuggingFaceMacros` | `.macro` target: SwiftSyntaxMacros, SwiftCompilerPlugin |
| `MLXHuggingFace` | `Libraries/MLXHuggingFace` | MLXHuggingFaceMacros, MLXLMCommon, (trait-conditional) MLXFoundationModels |
| `MLXCXGrammar` | `Libraries/MLXCXGrammar` | vendored xgrammar C++17 |
| `MLXGuidedGeneration` | `Libraries/MLXGuidedGeneration` | MLXLMCommon, MLXCXGrammar, MLX |
| `MLXFoundationModels` | `Libraries/MLXFoundationModels` | MLXLMCommon, (trait-conditional) MLXGuidedGeneration, MLX, MLXNN |

Test targets: `MLXLMTests` (`Tests/MLXLMTests`, resources `Resources/1080p_30.mov`, `Resources/audio_only.mov`),
`MLXHuggingFaceMacrosTests`, `MLXFoundationModelsTests`, `MLXGuidedGenerationTests`, `CXGrammarTests`.

`cxLanguageStandard: .cxx17` (`Package.swift:312`).

**MLXCXGrammar** cxxSettings are unusual and worth quoting (`Package.swift:203-228`):

```swift
            cxxSettings: [
                .headerSearchPath("xgrammar/include"),
                .headerSearchPath("xgrammar/cpp"),
                .headerSearchPath("xgrammar/3rdparty/picojson"),
                .headerSearchPath("xgrammar/3rdparty/dlpack/include"),
                .define("XGRAMMAR_ENABLE_CPPTRACE", to: "0"),
                .define("XGRAMMAR_ENABLE_INTERNAL_CHECK", to: "0"),
                // Rename the vendored C++ namespaces at compile time so this
                // target's symbols cannot collide with another xgrammar in the
                // same binary (e.g. CoreAI's prebuilt copy). …
                .define("xgrammar", to: "mlx_xgrammar"),
                .define("picojson", to: "mlx_picojson"),
                …
                .unsafeFlags(["-w"], .when(platforms: [.macOS, .iOS, .visionOS, .tvOS])),
            ],
            linkerSettings: [ .linkedLibrary("c++") ]
```

> "Rename the vendored C++ namespaces at compile time so this target's symbols cannot collide with another xgrammar in the same binary (e.g. **CoreAI's prebuilt copy**)."
> — direct evidence that Apple's Core AI framework ships its own xgrammar.

Doc generation is opt-in via env (`Package.swift:315-321`):

```swift
if Context.environment["MLX_SWIFT_BUILD_DOC"] == "1"
    || Context.environment["SPI_GENERATE_DOCS"] == "1"
{
    package.dependencies.append(
        .package(url: "https://github.com/apple/swift-docc-plugin", from: "1.3.0")
    )
}
```

**Recommended consumer version pin** (`README.md:49`, `README.md:67`, `using.md:206`):
`.package(url: "https://github.com/ml-explore/mlx-swift-lm", .upToNextMajor(from: "3.31.3"))`.

---

## 3. Installation / quick start (canonical, from root README)

`README.md:63-100` (verbatim):

```swift
dependencies: [
    .package(url: "https://github.com/ml-explore/mlx-swift-lm", .upToNextMajor(from: "3.31.3")),
    .package(url: "https://github.com/huggingface/swift-huggingface", from: "0.9.0"),
    .package(url: "https://github.com/huggingface/swift-transformers", from: "1.3.0"),
],
targets: [
    .target(
        name: "YourTargetName",
        dependencies: [
            .product(name: "MLXLLM", package: "mlx-swift-lm"),
            .product(name: "MLXLMCommon", package: "mlx-swift-lm"),
            .product(name: "MLXHuggingFace", package: "mlx-swift-lm"),
            .product(name: "HuggingFace", package: "swift-huggingface"),
            .product(name: "Tokenizers", package: "swift-transformers"),
        ]),
]
```

```swift
import MLXLLM
import MLXLMCommon
import MLXHuggingFace
import HuggingFace
import Tokenizers

let model = try await #huggingFaceLoadModelContainer(
    configuration: LLMRegistry.gemma3_1B_qat_4bit
)

let session = ChatSession(model)
print(try await session.respond(to: "What are two things to see in San Francisco?"))
print(try await session.respond(to: "How about a great place to eat?"))
```

FoundationModels bridge quick start (`README.md:104-141`) — note the two different availability
floors, `@Generable` at 26.0 and the session at 27.0:

```swift
@available(iOS 26.0, macOS 26.0, visionOS 26.0, *)
@Generable
struct Recommendation {
    let attraction: String
    let neighborhood: String
    let tip: String
}

if #available(iOS 27.0, macOS 27.0, visionOS 27.0, *) {
    let model = #huggingFaceLanguageModel(
        configuration: LLMRegistry.gemma3_1B_qat_4bit,
        capabilities: [.guidedGeneration])
    let session = LanguageModelSession(model: model)

    let recommendation = try await session.respond(
        to: "Recommend one thing to do in Chicago.",
        generating: Recommendation.self)
    print(recommendation.content)
}
```

---

## 4. Core protocols: Downloader / Tokenizer / TokenizerLoader (the 3.x split)

`Libraries/MLXLMCommon/Downloader.swift:16-36`:

```swift
public protocol Downloader: Sendable {
    func download(
        id: String,
        revision: String?,
        matching patterns: [String],
        useLatest: Bool,
        progressHandler: @Sendable @escaping (Progress) -> Void
    ) async throws -> URL
}
```

`Libraries/MLXLMCommon/Downloader.swift:48-57`:

```swift
public enum TokenizerSource: Sendable, Equatable {
    case id(String, revision: String? = nil)
    case directory(URL)
}
```

`Libraries/MLXLMCommon/Downloader.swift:69-101` — `ResolvedModelConfiguration`:

```swift
public struct ResolvedModelConfiguration: Sendable {
    public var modelDirectory: URL
    public var tokenizerDirectory: URL
    public var name: String
    public var defaultPrompt: String
    public var extraEOSTokens: Set<String>
    public var stopStrings: Set<String>
    public var eosTokenIds: Set<Int>
    public var toolCallFormat: ToolCallFormat?
    public var reasoningConfig: ReasoningConfig?
    // init(...) — stopStrings defaults to extraEOSTokens when nil
}
```

`Libraries/MLXLMCommon/TokenizerLoader.swift` (the whole file):

```swift
public protocol TokenizerLoader: Sendable {
    func load(from directory: URL) async throws -> any Tokenizer
}
```

`Libraries/MLXLMCommon/Tokenizer.swift:6-21`:

```swift
public protocol Tokenizer: Sendable {
    func encode(text: String, addSpecialTokens: Bool) -> [Int]
    func decode(tokenIds: [Int], skipSpecialTokens: Bool) -> String
    func convertTokenToId(_ token: String) -> Int?
    func convertIdToToken(_ id: Int) -> String?

    var bosToken: String? { get }
    var eosToken: String? { get }
    var unknownToken: String? { get }

    func applyChatTemplate(
        messages: [[String: any Sendable]],
        tools: [[String: any Sendable]]?,
        additionalContext: [String: any Sendable]?
    ) throws -> [Int]
}
```

Defaults in the extension (`Tokenizer.swift:23-54`): `encode(text:)` ⇒ `addSpecialTokens: true`;
`decode(tokenIds:)` ⇒ `skipSpecialTokens: false` (important — reasoning delimiters render as literal
text because of this, see `ReasoningConfig.isSpecialToken` doc); `eosTokenId` / `unknownTokenId`
computed via `convertTokenToId`.

`TokenizerError.missingChatTemplate` is the one typed error (`Tokenizer.swift:56-65`).

**Streaming detokenizer** (`Tokenizer.swift:67-114`): `StreamingDetokenizer: IteratorProtocol<String>`
with `mutating func append(token: Int)`; the concrete `NaiveStreamingDetokenizer` re-decodes the whole
segment each step, returns `nil` while a partial UTF-8 sequence is pending (`new.last == "\u{fffd}"`),
and restarts a segment on `"\n"`.

### Download patterns

`Libraries/MLXLMCommon/ModelFactory.swift:5-7`:

```swift
package let tokenizerDownloadPatterns = ["*.json", "*.jinja"]
package let modelDownloadPatterns = ["*.safetensors"] + tokenizerDownloadPatterns
```

---

## 5. MLXHuggingFace macros (the batteries-included path)

`Libraries/MLXHuggingFace/Macros.swift` declares 7 freestanding expression macros; the
implementations live in `Libraries/MLXHuggingFaceMacros/HuggingFaceIntegrationMacros.swift`
(`@main struct Macros: CompilerPlugin`, providing `DownloaderMacro`, `TokenizerAdaptorMacro`,
`TokenizerLoaderMacro`, `LoadContainerMacro`, `LoadContextMacro`, `LanguageModelMacro`).

| Macro | Result type | Notes |
|---|---|---|
| `#hubDownloader(_ hub: Any)` | `MLXLMCommon.Downloader` | wraps a `HuggingFace.HubClient` |
| `#hubDownloader()` | `MLXLMCommon.Downloader` | defaults to `HubClient()` |
| `#adaptHuggingFaceTokenizer(_ upstream: Any)` | `MLXLMCommon.Tokenizer` | wraps `Tokenizers.Tokenizer` |
| `#huggingFaceTokenizerLoader()` | `MLXLMCommon.TokenizerLoader` | uses `Tokenizers.AutoTokenizer.from(modelFolder:)` |
| `#huggingFaceLoadModelContainer(configuration:)` / `(configuration:progressHandler:)` | `ModelContainer` | |
| `#huggingFaceLoadModel(configuration:)` / `(configuration:progressHandler:)` | `ModelContext` | |
| `#huggingFaceLanguageModel(configuration:capabilities:configurationResolver:)` | `MLXLanguageModel` | `@available(iOS 27.0, macOS 27.0, visionOS 27.0, *)` |

The `#hubDownloader` expansion (exact, from `HuggingFaceIntegrationMacros.swift:25-64`) shows the
required conformance shape:

```swift
{ (hubApi: HuggingFace.HubClient) -> MLXLMCommon.Downloader in
    struct HubBridge: MLXLMCommon.Downloader {
        private let upstream: HuggingFace.HubClient
        init(_ upstream: HuggingFace.HubClient) { self.upstream = upstream }

        public func download(
            id: String, revision: String?, matching patterns: [String],
            useLatest: Bool,
            progressHandler: @Sendable @escaping (Foundation.Progress) -> Void
        ) async throws -> URL {
            guard let repoID = HuggingFace.Repo.ID(rawValue: id) else {
                throw HuggingFaceDownloaderError.invalidRepositoryID(id)
            }
            let revision = revision ?? "main"
            return try await upstream.downloadSnapshot(
                of: repoID, revision: revision, matching: patterns,
                progressHandler: { @MainActor progress in progressHandler(progress) })
        }
    }
    return HubBridge(hubApi)
}(HubClient())
```

The tokenizer bridge maps swift-transformers' `decode(tokens:)` onto MLXLMCommon's
`decode(tokenIds:)` and translates `Tokenizers.TokenizerError.missingChatTemplate` into
`MLXLMCommon.TokenizerError.missingChatTemplate` (`HuggingFaceIntegrationMacros.swift:95-123`).

`FoundationModelsMacros.swift:3` shows the SDK gate used everywhere for the FM path:

```swift
#if FoundationModelsIntegration && canImport(FoundationModels, _version: 2)
```

`LanguageModelMacro` synthesizes `weightsLocation:` (using `HuggingFace.HubCache.default`,
`resolveRevision(repo:kind:ref:"main")`, `snapshotPath(repo:kind:commitHash:)`) and
`load:` (a `loadModelContainer(from:#hubDownloader(), using:#huggingFaceTokenizerLoader(), …)` closure)
— `HuggingFaceIntegrationMacros.swift:243-266`.

**Gotcha:** the macro expansions reference symbols that must be *imported at the call site*:
`Foundation`, `MLXHuggingFace`, `MLXFoundationModels`, `MLXLMCommon`, `HuggingFace`, `Tokenizers`
(documented in `FoundationModelsMacros.swift:17-25`).

---

## 6. Model loading: factories, registries, ModelContext / ModelContainer

### 6.1 `GenericModelFactory`

`Libraries/MLXLMCommon/ModelFactory.swift:106-126`:

```swift
public protocol GenericModelFactory<ContextType, ContainerType>: Sendable {
    associatedtype ContextType
    associatedtype ContainerType: Sendable

    var modelRegistry: AbstractModelRegistry { get }

    func _load(
        configuration: ResolvedModelConfiguration,
        tokenizerLoader: any TokenizerLoader
    ) async throws -> ContextType

    func _wrap(_ context: ContextType) -> ContainerType
}
```

`public typealias ModelFactory = GenericModelFactory<ModelContext, ModelContainer>` (`ModelFactory.swift:221`).

Extension methods actually called by users (`ModelFactory.swift:148-210`):

```swift
func load(from downloader: any Downloader, using tokenizerLoader: any TokenizerLoader,
          configuration: ModelConfiguration, useLatest: Bool = false,
          progressHandler: @Sendable @escaping (Progress) -> Void = { _ in }) async throws -> sending ContextType

func loadContainer(from downloader: …, using: …, configuration: …, useLatest: Bool = false,
                   progressHandler: … = { _ in }) async throws -> ContainerType

func load(from directory: URL, using tokenizerLoader: any TokenizerLoader) async throws -> sending ContextType
func loadContainer(from directory: URL, using tokenizerLoader: any TokenizerLoader) async throws -> ContainerType

// plus, from GenericModelFactory extension:
func configuration(id: String) -> ModelConfiguration   // registry lookup or fresh instance
func contains(id: String) -> Bool
```

### 6.2 Free functions and the trampoline registry

`ModelFactory.swift:279-411` exposes four families of free functions:
`loadModel(from:using:configuration:useLatest:progressHandler:)`,
`loadModelContainer(from:using:configuration:…)`,
`loadModel(from:using:id:revision:useLatest:progressHandler:)` (`revision` defaults to `"main"`),
`loadModelContainer(from:using:id:revision:…)`, plus `loadModel(from directory:using:)` and
`loadModelContainer(from directory:using:)`.

These dispatch through `ModelFactoryRegistry.shared.modelFactories()` and **try each factory in
order, keeping the last error** (`ModelFactory.swift:413-431`):

```swift
private func load<R>(loader: (any ModelFactory) async throws -> sending R) async throws -> sending R {
    let factories = ModelFactoryRegistry.shared.modelFactories()
    var lastError: Error?
    for factory in factories {
        do { return try await loader(factory) } catch { lastError = error }
    }
    if let lastError { throw lastError } else { throw ModelFactoryError.noModelFactoryAvailable }
}
```

The registry uses **`NSClassFromString` dynamic discovery** so MLXLMCommon has no compile-time
dependency on MLXLLM/MLXVLM (`ModelFactory.swift:484-497`):

```swift
self.trampolines = [
    { (NSClassFromString("MLXVLM.TrampolineModelFactory") as? any ModelFactoryTrampoline.Type)?.modelFactory() },
    { (NSClassFromString("MLXLLM.TrampolineModelFactory") as? any ModelFactoryTrampoline.Type)?.modelFactory() },
]
```

**Gotcha:** VLM is tried *before* LLM. If neither `MLXLLM` nor `MLXVLM` is linked, you get
`ModelFactoryError.noModelFactoryAvailable`. `Package.swift:272-283` documents exactly this trap for
the FoundationModels test target:

> "MLXLLM is linked here (not by MLXFoundationModels itself) so its module-init registers a factory with MLXLMCommon's ModelFactoryRegistry. Without it, loadModelContainer throws .noModelFactoryAvailable before ever reaching the downloader, which deadlocks AvailabilityTests' in-flight gate."

`ModelFactoryRegistry.addTrampoline(_:)` lets you inject more.

### 6.3 `resolve(configuration:from:useLatest:progressHandler:)`

`ModelFactory.swift:228-263` — the single place downloads happen:
- `.id(id, revision)` → `downloader.download(id:revision:matching: modelDownloadPatterns, useLatest:progressHandler:)`
- `.directory(url)` → used as-is
- tokenizer source `.id` → downloaded with `tokenizerDownloadPatterns` and a **no-op progress handler**
- tokenizer source `nil` → model directory.

### 6.4 `ModelContext` / `ModelContainer`

`ModelFactory.swift:75-90`:

```swift
public struct ModelContext {
    public var configuration: ModelConfiguration
    public var model: any LanguageModel
    public var processor: any UserInputProcessor
    public var tokenizer: Tokenizer
}
```

`Libraries/MLXLMCommon/ModelContainer.swift:32-55` — `public final class ModelContainer: Sendable`,
backed by `SerialAccessContainer<ModelContext>`, `init(context: consuming ModelContext)`.

Async computed properties: `configuration`, `processor`, `tokenizer`, `modelDirectory`,
`tokenizerDirectory` (the last two `throws`).

Access methods:

```swift
public func perform<R: Sendable>(_ action: @Sendable (ModelContext) async throws -> sending R) async rethrows -> sending R
public func perform<V: Sendable, R: Sendable>(values: V, _ action: @Sendable (ModelContext, V) async throws -> R) async rethrows -> sending R
public func perform<V, R: Sendable>(nonSendable values: consuming V, _ action: @Sendable (ModelContext, V) async throws -> R) async rethrows -> sending R
public func update(_ action: @Sendable (inout ModelContext) -> Void) async
```

Deprecated: `perform { (model, tokenizer) in }` and `perform(values:) { (model, tokenizer, v) in }`
(`ModelContainer.swift:59-81`), `decode(tokens:)` → `decode(tokenIds:)`, and
`applyChatTemplate(messages:)` on the container.

Convenience (`ModelContainer.swift:145-229`):

```swift
public func prepare(input: consuming sending UserInput) async throws -> sending LMInput
public func generate(input: consuming sending LMInput, parameters: GenerateParameters,
                     wiredMemoryTicket: WiredMemoryTicket? = nil) async throws -> AsyncStream<Generation>
public func decode(tokenIds: [Int]) async -> String
public func encode(_ text: String) async -> [Int]
```

Important concurrency note verbatim (`ModelContainer.swift:191-197`):

> "Note: this is only visiting the model exclusively for the pre-fill time.  Beyond that there is no shared mutable state. This means that there may be concurrent access to the model weights themselves (but they are already evaluated)."

### 6.5 `SerialAccessContainer` / `SendableBox`

`Libraries/MLXLMCommon/Utilities/SerialAccessContainer.swift` — a `private actor AsyncMutex`
(`isLocked` + `[CheckedContinuation<Void, Never>]` waiters) plus:

```swift
package final class SerialAccessContainer<T>: @unchecked Sendable {
    public init(_ value: consuming T)
    public func read<R>(_ body: @Sendable (T) async throws -> sending R) async rethrows -> sending R
    public func update<R>(_ body: @Sendable (inout T) async throws -> sending R) async rethrows -> sending R
}

package final class SendableBox<T>: @unchecked Sendable {
    package init(_ value: consuming T)
    package consuming func consume() -> T   // fatalError("value already consumed") on 2nd call
}
```

Rationale (verbatim, `SerialAccessContainer.swift:39-43`):

> "Unlike an `actor`, this will guarantee exclusive access for the duration of the async call.  This is important for things like `ModelContainer` that have to perform async work but also need to prevent other callers for using _any_ of the internal state."

Both are `package`-scoped — **not** public API for consumers.

### 6.6 `LLMModelFactory._load` — the exact load pipeline

`Libraries/MLXLLM/LLMModelFactory.swift:569-669`, in order:

1. Read `config.json` from `configuration.modelDirectory`; failure ⇒ `ModelFactoryError.configurationFileError`.
2. `JSONDecoder.json5().decode(BaseConfiguration.self, …)`; `DecodingError` ⇒ `.configurationDecodingError`.
3. `typeRegistry.createModel(configuration: configData, modelType: baseConfig.modelType)`.
4. EOS ids: start with `baseConfig.effectiveEOSTokenIds`; if `generation_config.json` has
   `eos_token_id`, **replace** the set (`eosTokenIds = Set(genEosIds)  // Override per Python mlx-lm behavior`).
5. `mutableConfiguration.stopStrings.formUnion(generationConfig?.stopStrings ?? [])`.
6. `toolCallFormat` ← `ToolCallFormat.infer(from: baseConfig.modelType, configData: configData)` if not preset.
7. `reasoningConfig` ← `ReasoningConfig.infer(from: modelType, modelId: configuration.name, configData:)` if not preset.
8. Load tokenizer via `async let tokenizerTask = tokenizerLoader.load(from: configuration.tokenizerDirectory)`
   **in parallel** with `try loadWeights(modelDirectory:model:perLayerQuantization:)`.
9. `messageGenerator` from `LLMModel.messageGenerator(tokenizer:)` (default `DefaultMessageGenerator()`).
10. Build a `ModelConfiguration(directory:…)` and an `LLMUserInputProcessor`.

`VLMModelFactory._load` (`Libraries/MLXVLM/VLMModelFactory.swift:335-447`) adds:
- `async let processorConfigTask = loadProcessorConfig(from: modelDirectory)` — **prefers
  `preprocessor_config.json` over `processor_config.json`** (`VLMModelFactory.swift:460-476`).
- processor-class overrides keyed on model type (`VLMModelFactory.swift:419-424`):

```swift
let processorTypeOverrides: [String: String] = [
    "mistral3": "Mistral3Processor",
    "gemma4_unified": "Gemma4UnifiedProcessor",
]
```

  with the comment "Mistral3 models ship with 'PixtralProcessor' in their config but need Mistral3Processor to handle spatial merging correctly".
- VLM `_load` does **not** set `reasoningConfig` (LLM factory does).

### 6.7 Registries

`Libraries/MLXLMCommon/Registries/ModelTypeRegistry.swift`:

```swift
public actor ModelTypeRegistry<T> {
    public init()
    public init(creators: [String: (Data) throws -> T])
    public func registerModelType(_ type: String, creator: @escaping (Data) throws -> T)
    public func createModel(configuration: Data, modelType: String) throws -> sending T
    public func contains(_ modelType: String) -> Bool
}
```

`contains(_:)` doc is a nice detail: "Lets a caller check support without attempting a (throwing,
allocating) `createModel`, e.g. to decide before a multi-GB download whether a Hub repo's
`model_type` is runnable."

`ProcessorTypeRegistry` is the same shape with
`createModel(configuration:processorType:tokenizer:) throws -> sending any UserInputProcessor`.

`AbstractModelRegistry` (`open class … @unchecked Sendable`, NSLock-backed) maps
`ModelConfiguration.name` → configuration; `configuration(id:)` **returns a fresh
`ModelConfiguration(id:)` for unknown ids** (so unknown ids "just work"); use `contains(id:)` to test.

### 6.8 `loadWeights` and quantization

`Libraries/MLXLMCommon/Load.swift:42-83` (verbatim body):

```swift
public func loadWeights(
    modelDirectory: URL, model: BaseLanguageModel,
    quantization: BaseConfiguration.Quantization? = nil,
    perLayerQuantization: BaseConfiguration.PerLayerQuantization? = nil
) throws {
    var weights = [String: MLXArray]()
    var metadata = [String: String]()
    for url in try safetensorWeightURLs(in: modelDirectory) {
        let (w, m) = try loadArraysAndMetadata(url: url)
        for (key, value) in w { weights[key] = value }
        if metadata.isEmpty { metadata = m }
    }

    weights = model.sanitize(weights: weights, metadata: metadata)

    if quantization != nil || perLayerQuantization != nil {
        quantize(model: model) { path, module in
            if weights["\(path).scales"] != nil {
                if let perLayerQuantization {
                    return perLayerQuantization.quantization(layer: path)?.asTuple
                } else {
                    return quantization?.asTuple
                }
            } else { return nil }
        }
    }

    let parameters = ModuleParameters.unflattened(weights)
    try model.update(parameters: parameters, verify: [.all])
    eval(model)
}
```

`safetensorWeightURLs(in:)` (`Load.swift:15-33`) **honors `model.safetensors.index.json`** if present
(deduped + sorted `weight_map` values), else enumerates `*.safetensors` recursively. (Added in commit
`f5f18ed` "fix: Honor safetensors index when loading weights (#408)".)

`BaseConfiguration` (`Libraries/MLXLMCommon/BaseConfiguration.swift`):
- decodes `model_type`, `quantization` (as `QuantizationContainer`), `text_config.eos_token_id`, `eos_token_id`
- `Quantization { groupSize (group_size), bits, mode (default .affine) }`, `asTuple: (Int, Int, QuantizationMode)`
- `QuantizationOption { .skip, .quantize(Quantization) }`
- `PerLayerQuantization { quantization: Quantization?, perLayerQuantization: [String: QuantizationOption] }`
- `QuantizationContainer.init(from:)` manually walks the *interleaved* dict: skips `group_size`,
  `bits`, `mode`, plus `"quant_method"`, `"linear_class"`, `"quantization_mode"` (see
  `mlx-community/bitnet-b1.58-2B-4T-4bit`); decodes `false` as `.skip`, otherwise a nested `Quantization`.
- `effectiveEOSTokenIds: Set<Int>` = root `eos_token_id` **or** `text_config.eos_token_id` (commit `bc95ffb`).
- `.quantization` (single) is deprecated in favor of `perLayerQuantization`.

Mixed-precision QAT checkpoints are explicitly covered — commit `eaefe75` describes
`gemma-4-12B-it-qat-4bit` / `gemma-4-E4B-it-qat-4bit` as "4-bit attention/embeddings, 8-bit
mlp.{gate,up,down}_proj" and adds `Tests/MLXLMTests/MixedPrecisionQuantLoadTests.swift`, noting the
failure mode if overrides are ignored: `mismatchedSize on layers.0.mlp.gate_proj ([128, 8] vs [128, 16])`.

`JSONDecoder.json5()` (`Extensions/JSONDecoder+JSON5.swift`) — every config decode uses
`allowsJSON5 = true`.

---

## 7. `ModelConfiguration`

`Libraries/MLXLMCommon/ModelConfiguration.swift:16-184`:

```swift
public struct ModelConfiguration: Sendable, Equatable {
    public enum Identifier: Sendable, Equatable {
        case id(String, revision: String = "main")
        case directory(URL)
    }
    public var id: Identifier
    public var name: String              // repo id, or "Parent/Dir" for local
    public let tokenizerSource: TokenizerSource?
    public var defaultPrompt: String
    public var extraEOSTokens: Set<String>
    public var stopStrings: Set<String>?          // nil ⇒ falls back to extraEOSTokens
    public var effectiveStopStrings: Set<String> { stopStrings ?? extraEOSTokens }
    public var eosTokenIds: Set<Int> = []
    public var toolCallFormat: ToolCallFormat?
    public var reasoningConfig: ReasoningConfig? = nil

    public init(id: String, revision: String = "main", tokenizerSource: TokenizerSource? = nil,
                defaultPrompt: String = "", extraEOSTokens: Set<String> = [],
                stopStrings: Set<String>? = nil, eosTokenIds: Set<Int> = [],
                toolCallFormat: ToolCallFormat? = nil, reasoningConfig: ReasoningConfig? = nil)
    public init(directory: URL, …same tail…)

    public func resolved(modelDirectory: URL, tokenizerDirectory: URL) -> ResolvedModelConfiguration
}
```

`DirectoryError.unresolvedModelDirectory(_:)` / `.unresolvedTokenizerDirectory(_:)` are thrown by the
`package`-scoped `modelDirectory` / `tokenizerDirectory` getters when the config is still a remote id.

Removed in 3.x (`upgrade.md:252-256`): `tokenizerId`, `overrideTokenizer`, `preparePrompt`,
`modelDirectory(hub:)`.

---

## 8. Input types: `UserInput`, `Chat.Message`, `LMInput`

### 8.1 `UserInput` (`Libraries/MLXLMCommon/UserInput.swift`)

```swift
public typealias Message = [String: any Sendable]      // UserInput.swift:13

public struct UserInput {
    public enum Prompt: CustomStringConvertible {
        case text(String)
        case messages([Message])       // model-specific dictionaries
        case chat([Chat.Message])      // model-agnostic
    }
    public var prompt: Prompt          // didSet re-derives images/videos/audios for .chat
    public var images  = [Image]()
    public var videos  = [Video]()
    public var audios  = [Audio]()
    public var tools: [ToolSpec]?
    public var additionalContext: [String: any Sendable]?
    public var processing: Processing = .init()
}
```

Media enums:

```swift
public enum Image {                     // UserInput.swift:108-173
    #if canImport(CoreImage)
    case ciImage(CIImage)
    #endif
    case url(URL)
    case array(MLXArray)
    public func asCIImage() throws -> CIImage    // handles 0..1 scaling, planar→pixels, RGB→RGBA pad
}

public enum Video {                     // UserInput.swift:79-105
    #if canImport(AVFoundation)
    case avAsset(AVAsset)
    #endif
    case url(URL)
    case frames([VideoFrame])
}

public enum Audio { case url(URL); case array(MLXArray) }
public enum AudioFormat: Sendable { case linearPCM }

public struct VideoFrame { public let image: Image; public let timeStamp: CMTime }
```

Processing:

```swift
public struct Processing: Sendable {                    // UserInput.swift:189-207
    public var resize: CGSize?
    public var audio = AudioProcessing()
    public var minPixels: Int?      // per-call override of model min_pixels
    public var maxPixels: Int?      // per-call override of model max_pixels
    public init(resize: CGSize? = nil, minPixels: Int? = nil, maxPixels: Int? = nil)
}

public struct AudioProcessing: Sendable {               // UserInput.swift:210-222
    public var sampleRate = 48_000.0
    public var channels = 1
    public var audioFormat: AudioFormat = .linearPCM
}
```

Initializers: `init(prompt: String, images:videos:audios:tools:additionalContext:)` (wraps into
`.chat([.user(...)])`), `init(messages: [Message], …)`, `init(chat: [Chat.Message], processing:tools:additionalContext:)`,
`init(prompt: Prompt, images:videos:audios:processing:tools:additionalContext:)`.

**Gotcha (explicit source comment):** `// note: prompt.didSet is not triggered in init` — every init
manually re-derives `images`/`videos`/`audios`.

`UserInputProcessor` (`UserInput.swift:450-452`):

```swift
public protocol UserInputProcessor: Sendable {
    func prepare(input: UserInput) async throws -> LMInput
}
```

`StandInUserInputProcessor` throws `UserInputError.notImplemented`.

### 8.2 `Chat.Message` (`Libraries/MLXLMCommon/Chat.swift`)

```swift
public enum Chat {
    public struct Message {
        public var role: Role                 // .user .assistant .system .tool
        public var content: String
        public var images: [UserInput.Image]
        public var videos: [UserInput.Video]
        public var audios: [UserInput.Audio]
        public var tool: Tool?                // .calls([ToolCall]) or .result(id: String)

        public static func system(_ content: String, images:…, videos:…) -> Self
        public static func assistant(_ content: String, images:…, videos:…, toolCalls: [ToolCall]? = nil) -> Self
        public static func user(_ content: String, images:…, videos:…, audios:…) -> Self
        public static func tool(_ content: String, id: String? = nil) -> Self
    }
}
```

`MessageGenerator` protocol + default extension (`Chat.swift:111-181`) converts `Chat.Message` →
raw `Message` dicts. The default emits `["role": …, "content": …]` plus tool metadata:
`tool_calls` (array of `{type:"function", function:{name, arguments}, id?}`) for assistant messages,
`tool_call_id` for tool results.

Two built-in generators: `DefaultMessageGenerator`, `NoSystemMessageGenerator` (filters `.system`).
`LlamaModel.messageGenerator(tokenizer:)` picks between them by **probing the chat template with a
system message and catching the throw** (`Libraries/MLXLLM/Models/Llama.swift:186-202`).

### 8.3 `LMInput` / `LMOutput` (`Libraries/MLXLMCommon/LanguageModel.swift`)

```swift
public struct LMInput {
    public let text: Text
    public let image: ProcessedImage?
    public let video: ProcessedVideo?
    public let audio: ProcessedAudio?

    public struct Text {
        public let tokens: MLXArray
        public let mask: MLXArray?
        public var sequenceLengths: [Int]?     // from mask, else uniform for 2-D tokens
        public subscript(indices: MLXArrayIndex..., stream:) -> Text          // slices tokens AND mask
        public subscript(text indices: MLXArrayIndex..., stream:) -> Text     // slices tokens only
    }
    public struct ProcessedImage { public let pixels: MLXArray; public let positionIds: MLXArray?; public let frames: [THW]? }
    public struct ProcessedVideo { /* identical shape */ }
    public struct ProcessedAudio { public let features: MLXArray; public let mask: MLXArray? }
}

public struct THW: Sendable { public let t, h, w: Int; public var values: (Int,Int,Int); public var product: Int }

public struct LMOutput {
    public let logits: MLXArray
    public let state: State?
    public struct Key<T>: Identifiable, Sendable { public let id: String }
    public struct State { public subscript<T>(_ key: Key<T>) -> T? { get set } }   // heterogeneous typed dict
}

public enum PrepareResult { case tokens(LMInput.Text); case logits(LMOutput) }
```

### 8.4 `LanguageModel` protocol

`LanguageModel.swift:238-266`:

```swift
public protocol LanguageModel: BaseLanguageModel {
    func prepare(_ input: LMInput, cache: [KVCache], state: LMOutput.State?, windowSize: Int?)
        throws -> PrepareResult

    func callAsFunction(_ input: LMInput.Text, cache: [KVCache]?, state: LMOutput.State?) -> LMOutput
    func callAsFunction(_ inputs: MLXArray, cache: [KVCache]?) -> MLXArray
    func newCache(parameters: GenerateParameters?) -> [KVCache]
}
```

`BaseLanguageModel: Module` adds `sanitize(weights:)` and `sanitize(weights:metadata:)` (default
forwards to the former; models can inspect `metadata["format"] == "mlx"`).

`KVCacheDimensionProvider { var kvHeads: [Int] { get } }` supplies a default `newCache`:
`RotatingKVCache(maxSize: maxKVSize, keep: 4)` per layer when `parameters?.maxKVSize != nil`,
otherwise `KVCacheSimple()` (`LanguageModel.swift:287-302`).
**Gotcha:** `kvHeads.count` is the layer count — commit `12d2da0` fixed DeepSeek-V3 crashing with
"Index out of range" because `kvHeads` was declared `[Int] = []` and never assigned.

`ModelConversionMetadataProvider { var modelConversionMetadata: [String: String] { get } }` lets a
model stamp metadata into converted safetensors.

`LLMModel` (`Libraries/MLXLLM/LLMModel.swift`) = `LanguageModel & LoRAModel` plus
`messageGenerator(tokenizer:)`, and supplies the **default chunked prefill**:

```swift
public func prepare(_ input: LMInput, cache: [KVCache], state: LMOutput.State?, windowSize: Int?) throws -> PrepareResult {
    let prefillStepSize = windowSize ?? 512
    var y = input.text
    try withPreparedCache(cache, lengths: y.sequenceLengths) {
        var state: LMOutput.State? = state
        while y.tokens.size > prefillStepSize {
            try Task.checkCancellation()        // cooperative cancellation (commit 2b03485)
            autoreleasepool {
                let input = y[.newAxis, ..<prefillStepSize]
                let output = self(input, cache: cache.isEmpty ? nil : cache, state: state)
                state = output.state
                asyncEval(cache)
                y = y[prefillStepSize...]
            }
        }
        eval(cache)
    }
    return .tokens(y)
}
```

The cancellation comment is worth quoting (`LLMModel.swift:36-42`):

> "On iOS, GPU work submitted after the app moves to the background is rejected by the system ('Insufficient Permission'), and the resulting command-buffer error is thrown from a Metal completion handler where it cannot be caught, aborting the process."

`VLMModel` is just `public protocol VLMModel: LanguageModel, LoRAModel {}`.

---

## 9. Generation: `Evaluate.swift` (2432 lines) — the heart of the package

### 9.1 `GenerateParameters`

`Libraries/MLXLMCommon/Evaluate.swift:54-169` — all stored properties are `var` and public:

| property | type | default | notes |
|---|---|---|---|
| `prefillStepSize` | `Int?` | `nil` | nil ⇒ model picks (generic default 512) |
| `maxTokens` | `Int?` | `nil` | nil ⇒ unlimited |
| `maxKVSize` | `Int?` | `nil` | switches to `RotatingKVCache` |
| `kvBits` | `Int?` | `nil` | affine KV quantization bits |
| `kvGroupSize` | `Int` | `64` | |
| `quantizedKVStart` | `Int` | `0` | token offset at which quantization kicks in |
| `kvScheme` | `String?` | `nil` | overrides `kvBits`; see §11 |
| `temperature` | `Float` | **`0.6`** | 0 ⇒ `ArgMaxSampler` |
| `topP` | `Float` | `1.0` | active only when `0 < topP < 1` |
| `topK` | `Int` | `0` | 0 disables |
| `minP` | `Float` | `0.0` | 0 disables |
| `seed` | `UInt64?` | `nil` | reproducible sampling; inert at `temperature == 0` |
| `repetitionPenalty` | `Float?` | `nil` | |
| `repetitionContextSize` | `Int` | `20` | |
| `presencePenalty` | `Float?` | `nil` | |
| `presenceContextSize` | `Int` | `20` | |
| `frequencyPenalty` | `Float?` | `nil` | |
| `frequencyContextSize` | `Int` | `20` | |

Initializer parameter order (note `prefillStepSize` and `seed` are **last**):

```swift
public init(
    maxTokens: Int? = nil, maxKVSize: Int? = nil, kvBits: Int? = nil,
    kvGroupSize: Int = 64, quantizedKVStart: Int = 0, kvScheme: String? = nil,
    temperature: Float = 0.6, topP: Float = 1.0, topK: Int = 0, minP: Float = 0.0,
    repetitionPenalty: Float? = nil, repetitionContextSize: Int = 20,
    presencePenalty: Float? = nil, presenceContextSize: Int = 20,
    frequencyPenalty: Float? = nil, frequencyContextSize: Int = 20,
    prefillStepSize: Int? = nil, seed: UInt64? = nil
)
```

`sampler()` selection logic (`Evaluate.swift:171-184`): `temperature == 0` ⇒ `ArgMaxSampler`;
any of topP/topK/minP active ⇒ `TopPSampler(temperature:topP:topK:minP:seed:)`; else
`CategoricalSampler(temperature:seed:)`.

`processor()` returns `nil` unless at least one penalty is set & its context size > 0; otherwise a
`PenaltyProcessor(repetitionContext:presenceContext:frequencyContext:)`.

### 9.2 Samplers and processors

```swift
public protocol LogitSampler { func sample(logits: MLXArray) -> MLXArray }
public protocol LogitProcessor {
    mutating func prompt(_ prompt: MLXArray)
    func process(logits: MLXArray) -> MLXArray
    mutating func didSample(token: MLXArray)
}
```

`TopPSampler` (`Evaluate.swift:245-327`) applies filters in **Python mlx-lm order: top_p → min_p →
top_k**, masking with `-inf` in original vocab order; bfloat16 logits are upcast to float32;
runs inside `withRandomState(randomState)`. `applyTopK` uses `argPartition(-logprobs, kth: topK - 1, axis: -1)[0..., topK...]`
+ `putAlong` (O(V), no full sort).

Penalty processors share `TokenRing` — a **GPU-resident ring buffer** using `MLX.where` masks so no
CPU↔GPU sync happens per token, preserving `asyncEval` pipelining (`Evaluate.swift:348-400`).

Public processors: `RepetitionContext`, `PresencePenaltyContext`, `FrequencyPenaltyContext`,
`PenaltyProcessor`.

### 9.3 `TokenIteratorProtocol` and `TokenIterator`

```swift
public protocol TokenIteratorProtocol: Sequence, IteratorProtocol where Element == Int {
    var maxTokens: Int? { get }
    var tokenCount: Int { get }
    var promptPrefillTime: TimeInterval { get }
    var speculativeDecodingTelemetry: SpeculativeDecodingTelemetry? { get }  // default nil
    mutating func discardGeneratedToken()                                    // default no-op
}
```

`public struct TokenIterator: TokenIteratorProtocol` — three inits:

```swift
@available(*, deprecated, message: "please use init(input:model:cache:parameters:)")
public init(prompt: MLXArray, model: any LanguageModel, cache: [KVCache]? = nil, parameters: GenerateParameters) throws

public init(input: LMInput, model: any LanguageModel, cache: [KVCache]? = nil,
            state: LMOutput.State? = nil, parameters: GenerateParameters) throws

public init(input: LMInput, model: any LanguageModel, cache: [KVCache]? = nil,
            state: LMOutput.State? = nil,
            processor: LogitProcessor?, sampler: LogitSampler,
            prefillStepSize: Int? = nil, maxTokens: Int? = nil) throws
```

**Prefill runs inside `init`** (`self.promptPrefillTime = try measure { try prepare(...) }`), so
constructing a `TokenIterator` is the expensive part and it can `throw`.
The third init explicitly disables cache quantization ("No cache quantization for this direct initialization").

`public internal(set) var state: LMOutput.State?` — read it back after init to carry M-RoPE deltas
across turns (this is exactly what `ChatSession` does).

`prepare(input:windowSize:)` (`Evaluate.swift:703-723`) handles both `PrepareResult` cases; the
`.logits` branch does `self.state = result.state` — this line was the fix in commit `42f08a8`
("Fix prefill LMOutput.State being dropped on TokenIterator's .logits path").

`next()` (`Evaluate.swift:757-791`) — three notable behaviours:
- everything wrapped in `autoreleasepool` ("a full model forward produces hundreds of autoreleased
  wrapper objects … without this, long generations grow host memory without bound")
- `asyncEval([token] + cache.flatMap { $0.state })` — the cache state is evaluated *with* the token
- `if tokenCount % 256 == 0 { MLX.Memory.clearCache() }` — "Matches mlx-lm's clear cadence."

`step(previous:)` wraps the model call in `withPreparedCache(cache, lengths: previous.sequenceLengths)`
and then calls `maybeQuantizeKVCache(cache:&cache, kvBits:kvGroupSize:quantizedKVStart:kvScheme:)`.

### 9.4 The `generate` API surface

Non-deprecated, returning `AsyncStream`:

```swift
// standard
public func generate(input: LMInput, cache: [KVCache]? = nil, parameters: GenerateParameters,
                     context: ModelContext, wiredMemoryTicket: WiredMemoryTicket? = nil,
                     tools: [[String: any Sendable]]? = nil) throws -> AsyncStream<Generation>

// draft-model speculative decoding
public func generate(input:cache:parameters:context:draftModel: any LanguageModel,
                     draftCache: [KVCache]? = nil, numDraftTokens: Int = 2,
                     wiredMemoryTicket:) throws -> AsyncStream<Generation>

// MTP (multi-token-prediction) speculative decoding
public func generate(input:cache:parameters:context:mtpDrafter: any MTPDrafterModel,
                     blockSize: Int = 4, wiredMemoryTicket:) throws -> AsyncStream<Generation>

// raw token IDs
public func generateTokens(input:cache:parameters:context:
                           includeStopToken: Bool = false, wiredMemoryTicket:) throws -> AsyncStream<TokenGeneration>
public func generateTokens(input:cache:parameters:context:draftModel:draftCache:numDraftTokens:wiredMemoryTicket:) throws -> AsyncStream<TokenGeneration>
public func generateTokens(input:cache:parameters:context:mtpDrafter:blockSize:wiredMemoryTicket:) throws -> AsyncStream<TokenGeneration>

// stream + task handle
public func generateTask<TOKEN: TokenIteratorProtocol>(
    promptTokenCount: Int, modelConfiguration: ModelConfiguration, tokenizer: Tokenizer,
    iterator: consuming TOKEN, wiredMemoryTicket: WiredMemoryTicket? = nil,
    tools: [[String: any Sendable]]? = nil) -> (AsyncStream<Generation>, Task<Void, Never>)

public func generateTokensTask(input:cache:parameters:context:includeStopToken:wiredMemoryTicket:)
    throws -> (AsyncStream<TokenGeneration>, Task<Void, Never>)

public func generateTokenTask(promptTokenCount:modelConfiguration:tokenizer:
                              iterator: consuming TokenIterator, includeStopToken: Bool = false,
                              wiredMemoryTicket:) -> (AsyncStream<TokenGeneration>, Task<Void, Never>)
```

Deprecated callback-based forms (all annotated
`"Use the AsyncStream-based generate(input:cache:parameters:context:) instead for better Swift concurrency support"`):
`generate(promptTokens:parameters:model:tokenizer:extraEOSTokens:didGenerate:) -> GenerateResult`,
`generate(input:parameters:context:didGenerate: ([Int]) -> GenerateDisposition) -> GenerateResult`,
`generate(input:context:iterator:didGenerate:) -> GenerateResult`,
`generate(input:parameters:context:didGenerate: (Int) -> GenerateDisposition) -> GenerateCompletionInfo`,
`generate(input:context:iterator:didGenerate:) -> GenerateCompletionInfo`,
`generate(input:context:iterator:wiredMemoryTicket:) -> AsyncStream<Generation>`.

Important doc note on early break (`Evaluate.swift:1425-1429`):

> "if the stream is terminated early (e.g. break from the loop) computation will continue using the model, parameters, KVCache, etc. for some time (typically a few ms). This is typically OK for one-shot calls, but for 'chat session' type calls consider using `generateTask(...)` so that the end of the generation task can be observed."

### 9.5 Stream event types

```swift
public enum GenerateStopReason: Sendable { case stop; case length; case cancelled }

public struct GenerateCompletionInfo: Sendable {
    public let promptTokenCount: Int
    public let generationTokenCount: Int
    public let promptTime: TimeInterval
    public let generateTime: TimeInterval
    public let stopReason: GenerateStopReason
    public let proposedDraftTokens: Int?          // MTP only
    public let acceptedDraftTokens: Int?          // MTP only
    public let passthroughReason: String?         // MTP sticky passthrough
    public let speculativeDecodingTelemetry: SpeculativeDecodingTelemetry?
    public var promptTokensPerSecond: Double
    public var tokensPerSecond: Double
    public func summary() -> String
}

public enum Generation: Sendable {
    case chunk(String)
    case info(GenerateCompletionInfo)
    case toolCall(ToolCall)
    public var chunk: String?; public var info: GenerateCompletionInfo?; public var toolCall: ToolCall?
    @Sendable public static func collect(_ batch: [Generation]?, _ element: Generation) -> [Generation]
}

public enum TokenGeneration: Sendable {
    case token(Int)
    case info(GenerateCompletionInfo)
    public var token: Int?; public var info: GenerateCompletionInfo?
    @Sendable public static func collect(…) -> [TokenGeneration]
}
```

`Generation.collect` / `TokenGeneration.collect` are documented as "Reducer that can be used with
`throttle()` to gather elements into a batch" (i.e. for `swift-async-algorithms`).

`GenerateResult` (deprecated-callback result) exposes `inputText`, `promptTokenIds`, `tokenIds`,
`output`, `promptTokenCount`, `generationTokenCount`, `promptTime`, `generateTime`,
`promptTokensPerSecond`, `tokensPerSecond`, `summary()`. `promptTokens`/`tokens` are the deprecated
spellings.

### 9.6 The generation loop (`generateLoopTask`) — exact semantics

`Evaluate.swift:1867-2001` (private). Key mechanics:

- Builds `stopTokenIds` = `modelConfiguration.eosTokenIds` ∪ `tokenizer.eosTokenId` ∪
  `extraEOSTokens` mapped via `convertTokenToId` (`buildStopTokenIds`, `Evaluate.swift:1170-1185`).
- The loop is `tokenLoop: while !Task.isCancelled { guard let token = iterator.next() else { break } … }`
  — the cancellation check is deliberately **before** `next()`; see the verbatim comment:

  > "next() calls asyncEval() to pipeline the next GPU evaluation, so checking after it (the previous `while let token = iterator.next()` form) allowed one extra asyncEval to be submitted post-cancellation, which faults if the app has backgrounded (kIOGPUCommandBufferCallbackErrorBackgroundExecutionNotPermitted)."

- On a stop token with `includeStopToken == false` it calls `iterator.discardGeneratedToken()`.
- Ends with `Stream().synchronize()` then `continuation.finish()`.
- `continuation.onTermination = { if case .cancelled = $0 { task.cancel() } }`.
- Wraps the whole iteration in `await WiredMemoryTicket.withWiredLimit(ticket) { … }` when a ticket
  is supplied.
- MTP counters are picked up by `let mtpStats = iterator as? MTPStatsCollecting`.

Two handlers implement `TokenLoopHandler` (private): `TextToolTokenLoopHandler`
(`NaiveStreamingDetokenizer` + `StopStringFilter` + `ToolCallProcessor`) and `RawTokenLoopHandler`.

`StopStringFilter` (`Evaluate.swift:2219-2303`) buffers text, sorts stop strings longest-first, emits
text up to the earliest match, and holds back the longest partial suffix that could still complete a
stop string.

---

## 10. `ChatSession` (`Libraries/MLXLMCommon/ChatSession.swift`, 919 lines)

```swift
public final class ChatSession {
    public var instructions: String?
    public var processing: UserInput.Processing
    public var generateParameters: GenerateParameters
    public var additionalContext: [String: any Sendable]?
    public var tools: [ToolSpec]?
    public var toolDispatch: (@Sendable (ToolCall) async throws -> String)?
    public let speculativeDecoding: SpeculativeDecodingConfig?
}
```

**Not thread-safe** — "Each session should be used from a single task/thread at a time."

Eight initializers = {`ModelContainer`, `ModelContext`} × {plain, `history: [Chat.Message]`,
`cache: [KVCache]`}. Common tail (defaults):

```swift
instructions: String? = nil,
speculativeDecoding: SpeculativeDecodingConfig? = nil,
generateParameters: GenerateParameters = .init(),
processing: UserInput.Processing = .init(resize: CGSize(width: 512, height: 512)),
additionalContext: [String: any Sendable]? = nil,
tools: [ToolSpec]? = nil,
toolDispatch: (@Sendable (ToolCall) async throws -> String)? = nil
```

**Gotcha:** the default `processing` resizes images to **512×512** unless overridden.

Internal cache state machine (`ChatSession.swift:150-158`):

```swift
enum Cache {
    case empty
    case kvcache([KVCache], draftKVCache: [KVCache]?, state: LMOutput.State?)
    case history([Chat.Message])
}
```

Public methods:

```swift
func respond(to prompt: String, role: Chat.Message.Role = .user,
             images: consuming [UserInput.Image], videos: …, audios: …) async throws -> String
func respond(to prompt: String, role: … = .user, image: UserInput.Image? = nil,
             video: … = nil, audio: … = nil) async throws -> String
func respond(to messages: consuming [Chat.Message]) async throws -> String

func streamResponse(to prompt: String, role: … = .user, images: … = [], videos: … = [], audios: … = [])
    -> AsyncThrowingStream<String, Error>
func streamResponse(to messages: consuming [Chat.Message]) -> AsyncThrowingStream<String, Error>
func streamResponse(to prompt: String, image: … = nil, video: … = nil, audio: … = nil)
    -> AsyncThrowingStream<String, Error>

func streamDetails(to prompt: String, role: … = .user, images: … = [], videos: … = [], audios: … = [])
    -> AsyncThrowingStream<Generation, Error>
func streamDetails(to messages: consuming [Chat.Message]) -> AsyncThrowingStream<Generation, Error>

func clear() async                     // resets cache to .empty (keeps instructions)
func synchronize() async               // waits for exclusive access to the KVCache
func saveCache(to url: URL) async throws   // throws ChatSessionError.noCacheAvailable if never generated
```

Behaviour worth capturing from the `streamMap` implementation (`ChatSession.swift:574-836`):

- On each turn it prepends `.system(instructions)` when `instructions != nil` (so instructions are
  re-rendered every turn; a cache-restoring init warns against passing them again).
- The KV cache lock is a `SerialAccessContainer<Cache>`; the model is pulled *out* of the container
  via `SendableBox(context.model)` so multiple distinct `ChatSession`s can run in parallel against
  the same weights ("the KVCache cannot be shared and that is the lock that is held here").
- `lmState` (per-call `LMOutput.State`) is seeded into the iterator and read back:
  `let iterator = try TokenIterator(input:model:cache:state: lmState, parameters:)`;
  `lmState = iterator.state`.
- Tool loop: on tool calls with a `toolDispatch`, it appends **`.assistant("", toolCalls: pendingToolCalls)`
  first**, then one `.tool(result, id: toolCall.id)` per call, then `continue restart` (commit
  `19de279` — Gemma 4's template forward-scans from the assistant tool_calls message).
- `genTask.cancel()` is called when the consumer terminates or the enclosing task is cancelled, then
  `await genTask.value` — commit `2c1dd13` explains the deadlock this fixes.

`SpeculativeDecodingConfig` (`ChatSession.swift:43-122`):

```swift
public init(draftModel: ModelContainer, numDraftTokens: Int = 5,
            memoryPolicy: SpeculativeDecodingMemoryPolicy? = nil)

public init(draftModelBytes: Int, numDraftTokens: Int = 5,
            memoryPolicy: SpeculativeDecodingMemoryPolicy? = nil,
            loadDraftModel: @escaping @Sendable () async throws -> ModelContainer)

public var draftModel: ModelContainer?   // nil for the deferred form
public let numDraftTokens: Int
public let memoryPolicy: SpeculativeDecodingMemoryPolicy?
```

Note the **default `numDraftTokens` differs**: 5 in `SpeculativeDecodingConfig`, 2 in the free
`generate(…draftModel:…)` function.

---

## 11. KV cache (`Libraries/MLXLMCommon/KVCache.swift`, 2110 lines)

### 11.1 Protocol

```swift
public enum RoPEOffset { case scalar(Int); case batch(MLXArray) }

public protocol KVCache: Evaluatable {
    var offset: Int { get }
    var ropeOffset: RoPEOffset { get }                    // default .scalar(offset)
    var maxSize: Int? { get }
    func update(keys: MLXArray, values: MLXArray) -> (MLXArray, MLXArray)
    var state: [MLXArray] { get set }
    var metaState: [String] { get set }
    var isTrimmable: Bool { get }
    @discardableResult func trim(_ n: Int) -> Int
    func makeMask(n: Int, windowSize: Int?, returnArray: Bool) -> MLXFast.ScaledDotProductAttentionMaskMode
    func copy() -> any KVCache
    func prepare(lengths: [Int]?)
    func prepare(lengths: MLXArray?)
    func finalize()
}

public func withPreparedCache<Result>(_ cache: [any KVCache], lengths: [Int]?, _ body: () throws -> Result) rethrows -> Result
```

`open class BaseKVCache: KVCache` — note `open var ropeOffset` is declared **on the class** (commit
`616cae2`): if it were only on the protocol extension, a subclass override would be statically
shadowed and silently ignored through a `KVCache` existential.

### 11.2 Concrete caches

| class | notes |
|---|---|
| `KVCacheSimple` | default; `public var step = 256` growth; `toQuantized(groupSize: 64, bits: 4)`; trimmable |
| `RotatingKVCache` | `init(maxSize: Int, keep: Int = 0, step: Int = 256)`; sliding window; `toQuantized(...)` exists but `maybeQuantizeKVCache` does **not** convert it ("TODO: RotatingKVCache.toQuantized() is not implemented yet, like in Python") |
| `QuantizedKVCache` | `init(groupSize: Int = 64, bits: Int = 8, mode: QuantizationMode = .affine)`; `updateQuantized`, `getQuantizedState`, `toUnquantized()` |
| `ChunkedKVCache: KVCacheSimple` | `init(chunkSize: Int?)`, `maybeTrimFront()` |
| `ArraysCache` | `init(size: Int, leftPadding: [Int]? = nil)`; subscript access; `filter(batchIndices:)`, `extend(other:)`, `advance(_:)`, `currentLengths`, `makeMask(N:)` |
| `MambaCache: ArraysCache` | `init(leftPadding: [Int]? = nil)` |
| `CacheList` | `init(_ caches: KVCache...)`; `mapChildren(_:)`; forwards prepare/finalize/trim |
| `TurboQuantKVCache` | in `TurboQuantKVCache.swift` (1765 lines) + `TurboQuantKernels.swift` (2367 lines) |
| `StandardKVCache` | `typealias` for `KVCacheSimple` |

`QuantizedKVCacheProtocol: KVCache` adds `groupSize`, `bits`, `mode`, `updateQuantized(keys:values:)`,
`getQuantizedState()`.

### 11.3 Mask helpers

```swift
public func createCausalMask(n: Int, offset: Int, windowSize: Int? = nil, lengths: MLXArray? = nil) -> MLXArray
public func makeAttentionMask(n: Int, cache: KVCache?, windowSize: Int? = nil, returnArray: Bool = false)
    -> MLXFast.ScaledDotProductAttentionMaskMode
public func createAttentionMask(h: MLXArray, cache: KVCache?, windowSize: Int? = nil, returnArray: Bool = false)
    -> MLXFast.ScaledDotProductAttentionMaskMode
public func createSSMMask(h: MLXArray, cache: MambaCache?) -> MLXArray?

@_disfavoredOverload public func createAttentionMask(h: MLXArray, cache: [KVCache]?) -> MLXArray?
@available(*, deprecated, message: "Use createAttentionMask(h:cache:windowSize:returnArray:) with a single cache instead")
public func createAttentionMask(h: MLXArray, cache: [KVCache]?, returnArray: Bool = false) -> …MaskMode
```

Also `createBidirectionalMask(...)` / `createBidirectionalSlidingWindowMask(...)` in
`BidirectionalMasks.swift`.

### 11.4 Serialization

```swift
public func savePromptCache(url: URL, cache: [KVCache], metadata: [String: String] = [:]) throws
public func loadPromptCache(url: URL) throws -> ([KVCache], [String: String])
public func makePromptCache(model: any LanguageModel, parameters: GenerateParameters? = nil) -> [KVCache]
public func makePromptCache(model: any LanguageModel, maxKVSize: Int? = nil) -> [KVCache]   // legacy
public func makePromptCacheWithLayerCount(numLayers: Int, maxKVSize: Int? = nil) -> [KVCache]
public func canTrimPromptCache(_ cache: [KVCache]) -> Bool
@discardableResult public func trimPromptCache(_ cache: [KVCache], numTokens: Int) -> Int
```

Wire format is **Python-compatible**: arrays flattened as `"i.j"`; metadata as
`"0.i.j"` (cache_info) / `"1.key"` (user metadata) / `"2.i"` (class name). Class names written:
`"ChunkedKVCache"`, `"MambaCache"`, `"ArraysCache"`, `"RotatingKVCache"`, `"QuantizedKVCache"`,
`"TurboQuantKVCache"`, `"KVCache"` (for `KVCacheSimple`), `"CacheList"`.
Restoring a `RotatingKVCache` with `maxSize == "None"` throws
`KVCacheError("RotatingKVCache with maxSize=None is not supported.")`.

### 11.5 Dynamic quantization + TurboQuant schemes

```swift
public func resolveAffineScheme(_ scheme: String?) -> (bits: Int, groupSize: Int)?   // "affine4"->(4,64), "affine8"->(8,64)
public func maybeQuantizeKVCache(cache: inout [KVCache], kvBits: Int?, kvGroupSize: Int = 64,
                                 quantizedKVStart: Int = 0, kvScheme: String? = nil)
public func quantizedScaledDotProductAttention(queries:quantizedKeys:quantizedValues:scale:mask:
                                               groupSize: Int = 64, bits: Int = 8,
                                               mode: QuantizationMode = .affine) -> MLXArray
```

`kvScheme` **overrides** `kvBits`; unrecognized scheme strings are silently ignored. Eligibility for
affine conversion: cache is a plain `KVCacheSimple`, not already quantized, and
`cache.offset > quantizedKVStart` (recursing into `CacheList` children).

Scheme table verbatim from `Documentation.docc/kv-cache-quantization.md:31-43`
(`turbo<K-bits>v<V-bits>`, `0` = keys stay fp16):

| scheme | keys | values | KV compression | character |
|---|---|---|---|---|
| `affine8` | 8-bit affine | 8-bit affine | 1.88x | near-lossless on most models, full decode speed |
| `affine4` | 4-bit affine | 4-bit affine | 3.56x | collapses on some families; validate first |
| `turbo0v4` | fp16 | 4-bit turbo | 1.58x | safest start; beats affine8 quality on most models tested |
| `turbo0v3` | fp16 | 3-bit turbo | 1.66x | light value compression |
| `turbo0v2` | fp16 | 2-bit turbo | 1.58x† | aggressive value compression |
| `turbo8v4` | 8-bit affine | 4-bit turbo | 2.51x | conservative asymmetric |
| `turbo8v3` | 8-bit affine | 3-bit turbo | 2.75x | **recommended default** |
| `turbo8v2` | 8-bit affine | 2-bit turbo | 2.32x† | memory-bound long context |
| `turbo4`, `turbo3`, `turbo2` | turbo | turbo | up to 3.4x† | maximum compression; key sensitivity varies strongly by family |

† = boundary-layer protection auto-engages (first + last two attention layers fall back to 8-bit affine).

Measured performance quote (`kv-cache-quantization.md:87-95`):

> "Measured on Qwen3-1.7B (M5 Max, fp16 150 tok/s): turbo8v3 114, turbo4 122, turbo0v4 102. Prefill stays raw fp16, so prefill throughput is unaffected."

Family sensitivity (WikiText-2 decode-time KL vs fp16 cache):
Mistral-7B `turbo4` KLD 0.040 @2.8x; Qwen3-1.7B `turbo4` KLD 2.65 → **0.15 with per-dimension key
calibration**; Phi-4-mini 2.76 → 0.036; Qwen2.5-7B 0.62 → 0.060; Phi family affine8 KLD 0.0004;
Qwen2.5 affine8 KLD 0.041 vs turbo0v4 0.005.

Limitation: rotating/sliding-window layers (most Gemma layers) and hybrid recurrent layers are **not
converted**; a one-time notice lists layers that stayed fp16.

### 11.6 `attentionWithCacheUpdate`

`Libraries/MLXLMCommon/AttentionUtils.swift:37-95` — this is the function every ported model should
call. It routes:
- no cache ⇒ plain `MLXFast.scaledDotProductAttention`
- `TurboQuantKVCache` and `L > 1 && !isCompressed` ⇒ raw update + standard SDPA (prefill stays fp16)
- `TurboQuantKVCache` otherwise ⇒ `compressedAttention(...)`
- `QuantizedKVCacheProtocol` ⇒ `updateQuantized` + `quantizedScaledDotProductAttention`
- else ⇒ `cache.update` + `MLXFast.scaledDotProductAttention`

**Footgun (bit twice, in DeepSeek V2 and V3):** do **not** call `cache.update(...)` yourself and then
pass the result to `attentionWithCacheUpdate` — the helper updates the cache itself, so the cache
doubles and attention is corrupted after the first token (commits `12d2da0`, `294c31f`).

---

## 12. Tool calling

### 12.1 Declaring tools

`Libraries/MLXLMCommon/Tool/Tool.swift`:

```swift
public typealias ToolSpec = [String: any Sendable]
public protocol ToolProtocol: Sendable { var schema: ToolSpec { get } }

public struct Tool<Input: Codable, Output: Codable>: ToolProtocol {
    public let schema: ToolSpec
    public let handler: @Sendable (Input) async throws -> Output
    public var name: String        // reads schema["function"]["name"]

    public init(name: String, description: String, parameters: [ToolParameter],
                handler: @Sendable @escaping (Input) async throws -> Output)
    public init(schema: ToolSpec, handler: @Sendable @escaping (Input) async throws -> Output)
}
```

The synthesized schema is OpenAI-shaped:
`{"type":"function","function":{"name":…,"description":…,"parameters":{"type":"object","properties":{…},"required":[…]}}}`.

`ToolParameter` / `ToolParameterType` (`Tool/ToolParameter.swift`):

```swift
public indirect enum ToolParameterType {
    case string, bool, int, double
    case array(elementType: ToolParameterType)
    case object(properties: [ToolParameter])
    case data                                   // {"type":"string","contentEncoding":"base64"}
}

public static func required(_ name: String, type: ToolParameterType, description: String,
                            extraProperties: [String: any Sendable] = [:]) -> ToolParameter
public static func optional(… same …) -> ToolParameter
```

Verified schema output (from `Tests/MLXLMTests/ToolTests.swift:41-90`) — `.optional("unit", …,
extraProperties: ["enum": ["celsius","fahrenheit"]])` merges `enum` into that property's schema.

### 12.2 `ToolCall`

```swift
public struct ToolCall: Hashable, Codable, Sendable {
    public struct Function: Hashable, Codable, Sendable {
        public let name: String
        public let arguments: [String: JSONValue]
        public init(name: String, arguments: [String: JSONValue])
        public init(name: String, arguments: [String: any Sendable])
    }
    public let function: Function
    public let id: String?
    public init(function: Function, id: String? = nil)

    public func execute<Input, Output>(with tool: Tool<Input, Output>) async throws -> Output
}

public enum ToolError: Error, LocalizedError { case nameMismatch(toolName: String, functionName: String) }
```

`execute(with:)` JSON-encodes the arguments and `JSONDecoder().decode(Input.self, …)`.
`Encodable.toolResult` (`Extensions/Encodable+toolResult.swift`) encodes any `Encodable` to a
snake_case JSON string (`"{}"` on failure) — used for feeding results back.

### 12.3 `ToolCallFormat` and parsers

`Libraries/MLXLMCommon/Tool/ToolCallFormat.swift:64-103` — `public enum ToolCallFormat: String,
Sendable, Codable, CaseIterable`:

| case | raw value | wire example (from docs) | parser |
|---|---|---|---|
| `.json` | `json` | `<tool_call>{"name":…,"arguments":{…}}</tool_call>` | `JSONToolCallParser(startTag:"<tool_call>", endTag:"</tool_call>")` |
| `.lfm2` | `lfm2` | `<\|tool_call_start\|>[func(arg='value')]<\|tool_call_end\|>` | `PythonicToolCallParser` |
| `.xmlFunction` | `xml_function` | `<tool_call><function=name><parameter=key>value</parameter></function></tool_call>` | `XMLFunctionParser` |
| `.glm4` | `glm4` | `func<arg_key>k</arg_key><arg_value>v</arg_value>` | `GLM4ToolCallParser` |
| `.gemma` | `gemma` | `<start_function_call>call:name{key:value,k:<escape>str<escape>}<end_function_call>` | `GemmaFunctionParser(escapeMarker:"<escape>")` |
| `.gemma4` | `gemma4` | `<\|tool_call>call:name{key:<\|"\|>value<\|"\|>}<tool_call\|>` | `GemmaFunctionParser(escapeMarker: "<\|\"\|>")` |
| `.kimiK2` | `kimi_k2` | `functions.name:0<\|tool_call_argument_begin\|>{"key":"value"}` | `KimiK2ToolCallParser` |
| `.minimaxM2` | `minimax_m2` | `<invoke name="f"><parameter name="k">v</parameter></invoke>` | `MiniMaxM2ToolCallParser` |
| `.mistral` | `mistral` | `[TOOL_CALLS]get_weather [ARGS]{"location": "Tokyo"}` | `MistralToolCallParser` |
| `.llama3` | `llama3` | `<\|python_tag\|>{ "name": …, "parameters": {…} }` | `Llama3ToolCallParser` |

Tool-call ID generation (`ToolCallFormat.generateToolCallID()`): `.mistral` ⇒ first 9 chars of a
UUID with dashes stripped; everything else ⇒ `"call_" + lowercased uuid`.

`ToolCallFormat.infer(from modelType: String, configData: Data? = nil) -> ToolCallFormat?`:
- `"llama"`: needs a secondary signal — `vocab_size >= 128000` **or**
  `rope_scaling.rope_type == "llama3"` ⇒ `.llama3`, else `nil`
- prefix `lfm2` ⇒ `.lfm2`; prefix `glm4` ⇒ `.glm4`; prefix `gemma4` ⇒ `.gemma4`; exact `gemma` ⇒ `.gemma`
- prefix `nemotron` ⇒ `.xmlFunction`; prefix `qwen3_5` ⇒ `.xmlFunction`; prefix `qwen3_next` ⇒ `.xmlFunction`
- prefix `mistral3` ⇒ `.mistral`
- else `nil` (⇒ `.json` at generation time, since the loop uses `configuration.toolCallFormat ?? .json`)

```swift
public protocol ToolCallParser: Sendable {
    var startTag: String? { get }        // nil for inline formats
    var endTag: String? { get }
    func parse(content: String, tools: [[String: any Sendable]]?) -> ToolCall?
    func parseEOS(_ toolCallBuffer: String, tools: [[String: any Sendable]]?) -> [ToolCall]
}
```

### 12.4 `ToolCallProcessor`

`Libraries/MLXLMCommon/Tool/ToolCallProcessor.swift` (856 lines):

```swift
public class ToolCallProcessor {
    public enum Output: Sendable, Equatable { case response(String); case toolCall(ToolCall) }
    public var toolCalls: [ToolCall] = []
    public init(format: ToolCallFormat = .json, tools: [[String: any Sendable]]? = nil)

    public func processChunk(_ chunk: String) -> String?          // returns displayable text or nil
    public func processChunkOutputs(_ chunk: String) -> [Output]  // ordered API — do NOT mix with the above
    public func drainToolCalls() -> [ToolCall]
    public func processEOS()
    public func processEOS(returnBufferedText: Bool = true) -> String?
    public func processEOSOutputs() -> [Output]
}
```

Internals worth knowing: a 4-state machine (`normal`, `potentialToolCall`, `collectingToolCall`,
`collectingJSONToolCall`), a **bare-JSON fallback** enabled only for `.json`
(`supportsBareJSONFallback = format == .json`) with `maxJSONFallbackBufferLength = 32_768`, dedupe by
`emittedToolCallIDs`, and per-format EOS handling for Mistral/LFM2 (whose end tags never arrive as
text because `</s>` is intercepted at the token-ID level).

Explicit warning in the source: "Do not mix this API with `processChunk`, `processEOS`, or
`drainToolCalls()` on the same processor instance."

### 12.5 End-to-end tool loop (copyable, from `IntegrationTestHelpers.swift:260-290`)

```swift
struct EmptyInput: Codable {}
struct TimeOutput: Codable { let time: String }

let timeTool = Tool<EmptyInput, TimeOutput>(
    name: "get_time",
    description: "Get the current date and time including day of week.",
    parameters: []
) { _ in TimeOutput(time: "Wed Feb 18 17:50:43 PST 2026") }

let session = ChatSession(
    container, generateParameters: generateParameters,
    tools: [timeTool.schema]
) { toolCall in
    if toolCall.function.name == timeTool.name {
        return try await toolCall.execute(with: timeTool).toolResult
    }
    return "Unknown tool: \(toolCall.function.name)"
}

for try await chunk in session.streamResponse(to: "What day of week is it?") { print(chunk, terminator: "") }
```

Manual (no `toolDispatch`) variant, from `IntegrationTestHelpers.swift:209-257`:

```swift
let session = ChatSession(container, generateParameters: generateParameters, tools: [weatherToolSchema])
var toolCalls: [ToolCall] = []
for try await generation in session.streamDetails(to: "What is the weather in San Francisco?", images: [], videos: []) {
    switch generation {
    case .chunk(let text): responseText += text
    case .toolCall(let toolCall): toolCalls.append(toolCall)
    case .info(let completionInfo): info = completionInfo
    }
}
if !toolCalls.isEmpty {
    _ = try await session.respond(to: [.tool("Foggy with a high in the low 60s, clearing later in the day")])
}
```

---

## 13. Reasoning support

`Libraries/MLXLMCommon/ReasoningConfig.swift`:

```swift
public enum ReasoningError: Error, Equatable { case cannotDisableReasoning }

public enum ReasoningPromptStrategy: Sendable, Equatable {
    case templateFlag(key: String, defaultOn: Bool)     // e.g. Qwen3 "enable_thinking"
    case alwaysOn                                       // DeepSeek-R1
    case none
    public func additionalContext(forThinkingEnabled thinkingEnabled: Bool?) throws -> [String: any Sendable]?
}

public struct ReasoningConfig: Sendable, Equatable {
    public var startDelimiter: String        // "<think>"
    public var endDelimiter: String          // "</think>"
    public var promptStrategy: ReasoningPromptStrategy
    public var isSpecialToken: Bool          // diagnostic only in v1
    public static func infer(from modelType: String, modelId: String? = nil, configData: Data? = nil) -> ReasoningConfig?
}
```

Inference rules (`ReasoningConfig.swift:130-164`):
- `model_type` prefix `qwen3` ⇒ `<think>`/`</think>`, `.templateFlag(key: "enable_thinking", defaultOn: true)`, `isSpecialToken: true`
- `model_type == "deepseek_v3"` or `"deepseek_r1"`, **or repo id containing `deepseek-r1` / `r1-distill`** ⇒ `.alwaysOn`
  (the doc explains why `modelId` is load-bearing: R1-Distill reports `qwen2`/`llama`)
- else `nil`

Related files (not read in depth): `ReasoningEventEmitter.swift` (193 lines),
`ReasoningTokenCollector.swift` (66), `ReasoningHeuristics.swift` (32).
`MLXLMCommon` deliberately has **no** FoundationModels dependency; the reasoning-level ↔ `Bool?`
mapping lives in `MLXFoundationModels`.

---

## 14. Speculative decoding: draft-model and MTP

### 14.1 Draft-model speculative decoding

`SpeculativeTokenIterator: TokenIteratorProtocol` (`Evaluate.swift:819-1069`), a port of
`speculative_generate_step()` from mlx-lm. Requirements: **both models must share the same tokenizer**.

```swift
public init(input: LMInput, mainModel: any LanguageModel, draftModel: any LanguageModel,
            mainCache: [KVCache]? = nil, draftCache: [KVCache]? = nil,
            parameters: GenerateParameters, numDraftTokens: Int)
```

`SpeculativeDecodingTelemetry` (`SpeculativeDecoding.swift:14-98`) fields: `roundCount`,
`draftTokenCount`, `acceptedDraftTokenCount`, `targetModelCallCount`, `draftModelCallCount`,
`targetVerifiedTokenCount`, `emittedTokenCount`; derived `rejectedDraftTokenCount`, `acceptanceRate`,
`meanAcceptedDraftTokensPerRound`, `meanEmittedTokensPerTargetCall`.

Memory gating:

```swift
public enum SpeculativeDecodingMemoryAction: Sendable, Hashable { case allow, fallbackToDefault, fail }

public struct SpeculativeDecodingMemoryPolicy: Sendable, Hashable {
    public init(limitBytes: Int? = nil, additionalBytes: Int = 0,
                action: SpeculativeDecodingMemoryAction = .fallbackToDefault)
    public static var recommendedWorkingSet: Self       // GPU.maxRecommendedWorkingSetBytes()
    public func evaluate(mainModelBytes: Int, draftModelBytes: Int) -> SpeculativeDecodingMemoryEvaluation
}

public struct SpeculativeDecodingMemoryError: Error, Sendable { public let evaluation: … }
```

`modelWeightBytes(_:)` = `model.parameters().flattened().reduce(0) { $0 + $1.1.nbytes }`.

### 14.2 MTP (multi-token prediction) drafters

`Libraries/MLXLMCommon/MTPDrafterModel.swift`:

```swift
public protocol MTPDrafterModel: BaseLanguageModel {
    func draftBlock(target: any LanguageModel, lastToken: MLXArray, lastHidden: MLXArray,
                    sharedKV: [String: (MLXArray, MLXArray)], queryOffset: Int,
                    blockSize: Int, sampler: any LogitSampler) -> MLXArray   // [B, blockSize-1]
}

public struct MTPDrafterContext { public var configuration: ModelConfiguration; public var model: any MTPDrafterModel }
public final class MTPDrafterContainer: Sendable { public func perform<R: Sendable>(…) }

// cross-module LMOutput.State keys
public let mtpLastHiddenStatesKey = LMOutput.Key<MLXArray>("mtp.lastHiddenStates")
public let mtpSharedKVStatesKey   = LMOutput.Key<[String: (MLXArray, MLXArray)]>("mtp.sharedKVStates")
public let mtpEmitFlagKey         = LMOutput.Key<Bool>("mtp.emitDrafterState")

public protocol MTPStatsCollecting {
    var proposedDraftTokens: Int { get }
    var acceptedDraftTokens: Int { get }
    var passthroughReason: String? { get }
}
```

`MTPDrafterModelFactory` (`GenericModelFactory` with `ContextType = MTPDrafterContext`) +
`MTPDrafterTypeRegistry.shared` (empty at bootstrap!) + `MTPDrafterRegistry` with
`gemma4_26B_assistant_bf16` (`mlx-community/gemma-4-26B-A4B-it-assistant-bf16`) and
`gemma4_31B_assistant_bf16` (`mlx-community/gemma-4-31B-it-assistant-bf16`).

**Registration is manual and async** (`Libraries/MLXVLM/Gemma4AssistantRegistration.swift`):

```swift
await Gemma4AssistantRegistration.register()
// registers model types "gemma4_assistant" and "gemma4_unified_assistant"
// -> Gemma4AssistantDraftModel(Gemma4AssistantConfiguration)
```

Reason for the manual step (verbatim): "the drafter implementation (`Gemma4AssistantDraftModel`)
lives in MLXVLM, and importing it into MLXLMCommon's `MTPDrafterTypeRegistry.shared` would form a
circular dependency."

`blockSize` default 4 "Mirrors mlx-vlm's `draft_block_size`. Default 4 matches mlx-vlm's example configs."

---

## 15. LoRA / DoRA adapters and training

### 15.1 Adapter protocol

`Libraries/MLXLMCommon/Adapters/ModelAdapter.swift`:

```swift
public enum ModelAdapterError: Error { case unsupportedAdapterType(String); case incompatibleModelType }

public protocol ModelAdapter: Sendable {
    func load(into model: LanguageModel) throws
    func fuse(with model: LanguageModel) throws
    func unload(from model: LanguageModel)
}
public typealias SendableModelAdapter = ModelAdapter & Sendable

// LanguageModel conveniences
extension LanguageModel {
    public func load(adapter: ModelAdapter) throws
    public func fuse(with adapter: ModelAdapter) throws
    public func unload(adapter: ModelAdapter)
    public func perform<R>(with adapter: ModelAdapter, perform: () throws -> R) throws -> R
    public func perform<R>(with adapter: ModelAdapter, perform: () async throws -> R) async throws -> R
}
```

### 15.2 `LoRAConfiguration` / `LoRAContainer`

`Libraries/MLXLMCommon/Adapters/LoRA/LoRAContainer.swift` — compatible with `adapter_config.json`:

```json
{
  "fine_tune_type": "lora",
  "num_layers": 28,
  "lora_parameters": { "rank": 16, "scale": 20.0 }
}
```

```swift
public struct LoRAConfiguration: Sendable, Codable {
    public enum FineTuneType: String, Sendable, Codable { case lora; case dora }
    public struct LoRAParameters: Sendable, Codable {
        public let rank: Int          // default 8
        public let scale: Float       // default 10.0
        public let keys: [String]?    // default nil -> model's loraDefaultKeys
    }
    public let numLayers: Int         // default 16
    public let fineTuneType: FineTuneType
    public let loraParameters: LoRAParameters
}

public struct LoRAContainer: ModelAdapter, @unchecked Sendable {
    public let configuration: LoRAConfiguration
    public let parameters: ModuleParameters
    public static func from(model: LanguageModel, configuration: LoRAConfiguration = .init()) throws -> LoRAContainer
    public static func from(directory: URL) throws -> LoRAContainer   // adapter_config.json + adapters.safetensors
    public func load(into model: LanguageModel) throws     // update(parameters:verify: .noUnusedKeys)
    public func fuse(with model: LanguageModel) throws
    public func unload(from model: LanguageModel)
}
```

`LoRAContainer.from(model:)` **freezes the model** and applies the adapter to
`lora.loraLayers.suffix(configuration.numLayers)`.
Supporting files: `LoRA+Layers.swift` (`LoRALinear`), `DoRA+Layers.swift` (`DoRALinear`),
`LoRAModel.swift` (`loraLayers`, `loraDefaultKeys`, `LoRALinearLayers`), `PEFTAdapter.swift`,
`ModelAdapterFactory.swift`, `ModelAdapterTypeRegistry.swift`.

### 15.3 `LoRATrain` (`Libraries/MLXLLM/LoraTrain.swift`)

```swift
public enum LoRATrain {
    public typealias LoraLossFunction = (Module, MLXArray, MLXArray, MLXArray) -> (MLXArray, MLXArray)

    public struct Parameters: Sendable {
        public var batchSize = 4
        public var iterations = 1000
        public var stepsPerReport = 10
        public var stepsPerEval = 100
        public var validationBatches = 10
        public var saveEvery = 100
        public var adapterURL: URL?
    }
    // train(model:train:validate:optimizer:tokenizer:parameters:progress:)
    // evaluate(model:dataset:loss:tokenizer:batchSize:batchCount:)
    // saveLoRAWeights(model:url:) / loadLoRAWeights(model:url:)
}
```

Batching warns above 2048 tokens: `"[WARNING] Some sequences are longer than 2048 tokens. Consider pre-splitting your data to save memory."`

Data loading (`Libraries/MLXLLM/Lora+Data.swift`):

```swift
public func loadLoRAData(directory: URL, name: String) throws -> [String]   // tries name.jsonl then name.txt
public func loadLoRAData(url: URL) throws -> [String]                       // fatalError on unknown extension
```
`.jsonl` lines must be objects with a `"text"` field; `.txt` is one sample per non-empty line.

Working usage from `Tests/MLXLMTests/EvalTests.swift:26-53`:

```swift
let model = LlamaModel(config)
quantize(model: model, groupSize: 64, bits: 4)
let optimizer = Adam(learningRate: 1e-5)
try LoRATrain.train(
    model: model, train: ["a","b","c"], validate: ["x","y","z"], optimizer: optimizer,
    tokenizer: TestTokenizer(), parameters: LoRATrain.Parameters(iterations: 5)
) { progress in print(progress); return .more }
```

---

## 16. Model conversion (`mlx_lm.convert` equivalent)

`Libraries/MLXLMCommon/ModelConversion.swift` (860 lines) + `Libraries/MLXLLM/ModelConversion.swift`.

```swift
public struct ModelConversionQuantization: Sendable, Equatable {
    public var bits: Int?; public var groupSize: Int?; public var mode: QuantizationMode
    public init(bits: Int? = nil, groupSize: Int? = nil, mode: QuantizationMode = .affine)
}
public enum ModelConversionQuantizationDecision: Sendable, Equatable { … }
public typealias ModelConversionQuantizationPredicate = …
public struct ModelConversionOptions: Sendable {
    public var quantization: ModelConversionQuantization
    public var maxShardSize: Int64
    public var overwriteExistingOutput: Bool
    public var quantizationPredicate: ModelConversionQuantizationPredicate?
}
public enum ModelConversionStage: String, Sendable { … downloading, copyingFiles, loadingWeights,
                                                     quantizing, savingWeights, updatingConfiguration … }
public struct ModelConversionProgress: Sendable { public let stage; fractionCompleted: Double?; message: String? }
public struct ModelConversionResult: Sendable { public let outputDirectory: URL; weightsURL: URL; weightsURLs: [URL] }
public enum ModelConversionError: LocalizedError, Equatable {
    case outputDirectoryExists(URL), outputDirectoryMatchesSource(URL), noSafetensorsFiles(URL),
         unsupportedPyTorchWeights(URL), sourceAlreadyQuantized(URL), invalidShardSize(Int64)
}
public func convert(modelDirectory: URL, tokenizerDirectory: URL? = nil, model: BaseLanguageModel,
                    to outputDirectory: URL, options: ModelConversionOptions = .init(),
                    progressHandler: @Sendable (ModelConversionProgress) -> Void = { _ in },
                    perLayerQuantization: BaseConfiguration.PerLayerQuantization? = nil) throws -> ModelConversionResult
```

`LLMModelFactory` extension adds `convert(from downloader:configuration:to:options:useLatest:
downloadProgressHandler:progressHandler:)`, `convert(from directory:tokenizerDirectory:to:options:progressHandler:)`,
and `convert(configuration: ResolvedModelConfiguration, to:options:progressHandler:)`.

Constraints: **PyTorch `.bin` is out of scope**; converting an already-quantized source throws
`.sourceAlreadyQuantized`; output must not overlap the source or tokenizer directory.

---

## 17. Wired memory

`Libraries/MLXLMCommon/WiredMemoryPolicies.swift` — MLXLMCommon supplies *policies*;
`WiredMemoryManager` / `WiredMemoryTicket` / `WiredMemoryPolicy` themselves come from **mlx-swift**.

| policy | limit formula | admission |
|---|---|---|
| `WiredSumPolicy(cap: Int? = nil)` | `clamp(baseline + sum(activeSizes))` | denies if projected > cap |
| `WiredMaxPolicy()` | `max(baseline, max(activeSizes))` | default |
| `WiredFixedPolicy(limit: Int)` | `bytes` while any ticket active | default |
| `WiredBudgetPolicy(baseBytes: Int, cap: Int? = nil, id: UUID = UUID())` | `clamp(baseline + baseBytes + sum(activeSizes))` | denies if projected > cap |

`clamp` falls back to `GPU.maxRecommendedWorkingSetBytes()` when no cap is set and Metal is available.

Usage (`Documentation.docc/using-model.md:135-145`):

```swift
let policy = WiredSumPolicy()
let ticket = policy.ticket(size: estimatedBytes)
let stream = try MLXLMCommon.generate(
    input: input, parameters: generateParameters, context: context, wiredMemoryTicket: ticket)
```

`WiredMemoryUtils` (`WiredMemoryUtils.swift`):

```swift
public struct WiredMemoryMeasurement: Sendable {
    public let weightBytes, kvBytes, workspaceBytes, peakActiveBytes, tokenCount, prefillStepSize: Int
    public var totalBytes: Int
}
public enum WiredMemoryUtils { public static func tune(…) /* 3 overloads: tokens, LMInput, UserInput */ }
```

Measuring weight bytes (`wired-memory.md:21-28`):

```swift
let context = try await LLMModelFactory.shared.load(configuration: config)
let weightBytes = context.model.parameters().flattened().reduce(0) { $0 + $1.1.nbytes }
```

Measured deltas quoted in `wired-memory.md:58-61`:
Qwen3-4B-Sky-High-Hermes-4bit — nbytes 2,262,535,712; tensor files 2,262,637,937; active after load 2,264,337,376.
Qwen3-Next-80B-A3B-Instruct-MLX-4bit — 44,844,060,160 / 44,844,286,608 / 44,844,101,616.

Policy-only mode on CPU:

```swift
await WiredMemoryManager.shared.updateConfiguration { configuration in
    configuration.policyOnlyWhenUnsupported = true
}
```

KV-cache sizing formula (`wired-memory.md:118-128`):

```
elements per token per layer = 2 * kvHeads * headDim
layer bytes = tokens * elements per token per layer * bytesPerElement
total KV bytes = layer bytes * numAttentionLayers
```
`bytesPerElement`: 2 for FP16/BF16, 1 for INT8, 0.5 for INT4.

---

## 18. Model catalogue

### 18.1 `LLMTypeRegistry.shared` — 62 `model_type` keys (`LLMModelFactory.swift:26-89`)

```
mistral, mixtral, llama, phi, phi3, phimoe, gemma, gemma2, gemma3, gemma3_text, gemma3n,
gemma4, gemma4_unified, gemma4_text, qwen2, qwen3, qwen3_moe, qwen3_next, qwen3_5,
qwen3_5_moe, qwen3_5_text, minicpm, starcoder2, cohere, openelm, internlm2, deepseek_v2,
deepseek_v3, granite, granitemoehybrid, mimo, mimo_v2_flash, minimax, glm4, glm4_moe,
glm4_moe_lite, acereason, falcon_h1, bitnet, smollm3, ernie4_5, lfm2, baichuan_m1, exaone4,
gpt_oss, lille-130m, olmoe, olmo2, olmo3, bailing_moe, lfm2_moe, nanochat, nemotron_h,
afmoe, jamba, mamba2, mistral3, apertus, hunyuan_v1_dense, nemotron_labs_diffusion
```

`Libraries/MLXLLM/Models/` has 56 `.swift` files: AfMoE, Apertus, BaichuanM1, BailingMoe, Bitnet,
Cohere, DeepseekV2, DeepseekV3, Ernie4_5, Exaone4, FalconH1, Gemma, Gemma2, Gemma3Text, Gemma3nText,
Gemma4, Gemma4Text, GLM4, GLM4MOE, GLM4MOELite, GPTOSS, Granite, GraniteMoeHybrid, Hunyuan,
Internlm2, Jamba, LFM2, LFM2MoE, Lille130m, Llama, Mamba2, MiMo, MiMoV2Flash, MiniCPM, MiniMax,
Mistral3Text, Mixtral, NanoChat, NemotronH, NemotronLabsDiffusion, Olmo2, Olmo3, OlmoE, OpenELM, Phi,
Phi3, PhiMoE, Qwen2, Qwen3, Qwen35, Qwen35MoE, Qwen3MoE, Qwen3Next, SmolLM3, SSM, Starcoder2.

### 18.2 `LLMRegistry` presets (60 entries in `all()`)

Examples with their non-default settings:

```swift
static public let gemma3_1B_qat_4bit = ModelConfiguration(
    id: "mlx-community/gemma-3-1b-it-qat-4bit",
    defaultPrompt: "What is the difference between a fruit and a vegetable?",
    extraEOSTokens: ["<end_of_turn>"])

static public let gemma4_e4b_it_4bit = ModelConfiguration(
    id: "mlx-community/gemma-4-e4b-it-4bit", …, extraEOSTokens: ["<turn|>"])

static public let qwen3_4b_4bit = ModelConfiguration(
    id: "mlx-community/Qwen3-4B-4bit", …, extraEOSTokens: ["<|im_end|>"])

static public let llama3_2_3B_4bit = ModelConfiguration(
    id: "mlx-community/Llama-3.2-3B-Instruct-4bit", …, extraEOSTokens: ["<|eot_id|>"])

static public let glm4_9b_4bit = ModelConfiguration(
    id: "mlx-community/GLM-4-9B-0414-4bit", …, toolCallFormat: .glm4)

static public let lfm2_1_2b_4bit = ModelConfiguration(
    id: "mlx-community/LFM2-1.2B-4bit", …, toolCallFormat: .lfm2)

static public let lfm2_8b_a1b_3bit_mlx = ModelConfiguration(
    id: "mlx-community/LFM2-8B-A1B-3bit-MLX", defaultPrompt: "", toolCallFormat: .lfm2)
```

Other notable ids: `mlx-community/Qwen3.5-2B-4bit` (`qwen3_5_2b_4bit`),
`mlx-community/Qwen3.6-27B-4bit` (`qwen3_6_27b_4bit`), `mlx-community/gpt-oss-20b-MXFP4-Q8`,
`mlx-community/Nemotron-Labs-Diffusion-3B-4bit`, `mlx-community/AI21-Jamba-Reasoning-3B-4bit`,
`dnakov/nanochat-d20-mlx`, `mlx-community/Ling-mini-2.0-2bit-DWQ`,
`mlx-community/Granite-4.0-H-Tiny-4bit-DWQ`, `tiiuae/Falcon-H1R-7B`,
`mlx-community/Hunyuan-MT-7B-4bit`/`-8bit`, `mlx-community/Hy-MT2-7B-4bit`/`-8bit`.

`@available(*, deprecated, renamed: "LLMRegistry") public typealias ModelRegistry = LLMRegistry`
(same in MLXVLM for `VLMRegistry` — so `ModelRegistry` is ambiguous if both are imported).

### 18.3 `VLMTypeRegistry.shared` — 17 keys (`VLMModelFactory.swift:89-108`)

```
paligemma, qwen2_vl, qwen2_5_vl, qwen3_vl, qwen3_5, qwen3_5_moe, idefics3, gemma3,
gemma4, gemma4_unified, smolvlm, fastvlm, llava_qwen2, pixtral, mistral3, lfm2_vl, lfm2-vl, glm_ocr
```

`VLMProcessorTypeRegistry.shared` keys (`processor_class` from `preprocessor_config.json`):

```
PaliGemmaProcessor, Qwen2VLProcessor, Qwen2_5_VLProcessor, Qwen3VLProcessor, Idefics3Processor,
Gemma3Processor, Gemma4Processor, Gemma4UnifiedProcessor, SmolVLMProcessor, FastVLMProcessor,
PixtralProcessor, Mistral3Processor, Lfm2VlProcessor, Glm46VProcessor
```

`Libraries/MLXVLM/Models/` (17 files): FastVLM, Gemma3, Gemma4, Gemma4Assistant, GlmOcr, Idefics3,
LFM2VL, Mistral3, Paligemma, Pixtral, Qwen25VL, Qwen2VL, Qwen35, Qwen35MoE, Qwen3VL, QwenVL, SmolVLM2.

`VLMRegistry` presets include `mlx-community/gemma-4-e2b-it-4bit`, `-e4b-it-4bit`,
`-31b-it-4bit`, `-26b-a4b-it-4bit` (all `extraEOSTokens: ["<turn|>"]`),
`lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit`, `mlx-community/Qwen3-VL-4B-Instruct-8bit`,
`mlx-community/Qwen3.5-27B-4bit`, `mlx-community/Qwen3.5-35B-A3B-4bit`,
`mlx-community/LFM2.5-VL-1.6B-4bit`, `mlx-community/Ministral-3-3B-Instruct-2512-4bit`,
`mlx-community/FastVLM-0.5B-bf16`, `HuggingFaceTB/SmolVLM2-500M-Video-Instruct-mlx`.

### 18.4 Embedders

`EmbedderTypeRegistry.shared` keys: `bert`, `roberta`, `xlm-roberta`, `distilbert`, `nomic_bert`,
`qwen3`, `lfm2`, `gemma3`, `gemma3_text`, `gemma3n`.

`EmbedderRegistry` presets: `bge_micro`, `gte_tiny`, `minilm_l6`, `snowflake_xs`, `minilm_l12`,
`bge_small`, `multilingual_e5_small`, `bge_base`, `nomic_text_v1`, `nomic_text_v1_5`, `bge_large`,
`snowflake_lg`, `bge_m3`, `mixedbread_large`, `qwen3_embedding`
(`mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ`), `lfm2_embedding_350m{,_4bit,_8bit}`,
`lfm2_colbert_350m{,_4bit,_8bit}`.

```swift
public protocol EmbeddingModel: BaseLanguageModel {
    var vocabularySize: Int { get }
    var poolingStrategy: Pooling.Strategy? { get }     // default nil
    var maxPositionEmbeddings: Int? { get }            // default nil; inputs beyond get truncated with a warning
    func callAsFunction(_ inputs: MLXArray, positionIds: MLXArray?, tokenTypeIds: MLXArray?,
                        attentionMask: MLXArray?) -> EmbeddingModelOutput
}
public struct EmbeddingModelOutput { public let hiddenStates: MLXArray?; public let pooledOutput: MLXArray? }
public enum Pooling.Strategy: Sendable { case mean, cls, first, last, max, none }
```

`PoolingConfiguration` decodes `1_Pooling/config.json`-style keys: `word_embedding_dimension`,
`pooling_mode_cls_token`, `pooling_mode_mean_tokens`, `pooling_mode_max_tokens`,
`pooling_mode_lasttoken` (all optional — commit `efd498b`).

`EmbedderModelContext { configuration, model, tokenizer, pooling }`, `EmbedderModelContainer` mirrors
`ModelContainer` (`perform`, `update`, `poolingStrategy`, `modelDirectory`, `tokenizerDirectory`).

---

## 19. Porting a model to Swift — the concrete recipe

Sources: `Libraries/MLXLMCommon/Documentation.docc/porting.md` (778 lines),
`Libraries/MLXLLM/Documentation.docc/adding-model.md`, `Libraries/MLXVLM/README.md`,
`skills/mlx-swift-lm/references/model-porting.md`.

### 19.1 Imports

```swift
import Foundation
import MLX
import MLXLMCommon
import MLXNN
```

### 19.2 Configuration pattern

Optional-with-computed-default is the house style:

```swift
private let _ropeTheta: Float?
public var ropeTheta: Float { _ropeTheta ?? 10_000 }
enum CodingKeys: String, CodingKey { case _ropeTheta = "rope_theta" }
```

### 19.3 Property wrappers (Swift MLX vs Python MLX)

- `@ModuleInfo` for sub-modules (anything with `callAsFunction`); `@ParameterInfo` for raw `MLXArray`
- key override: `@ModuleInfo(key: "self_attn") var attention: Attention`
- init syntax changes to `self._attention.wrappedValue = …`
- optional modules for `tie_word_embeddings`: `@ModuleInfo(key: "lm_head") var lmHead: Linear?`
  — "If the `lmHead` module is created but not used, the parameter load will fail validation because
  the `lm_head` keys will be missing."
- pre-computed non-parameters use a **leading underscore private property**
  (`private let _positionIds: MLXArray`) so weight loading ignores them
- rare case: `@ModuleInfo(key: "weight") var weight: MLXArray` for quantized/expert layers

### 19.4 Canonical attention body (from `Libraries/MLXLLM/Models/Llama.swift:44-73`)

```swift
func callAsFunction(_ x: MLXArray, mask: MLXFast.ScaledDotProductAttentionMaskMode, cache: KVCache?) -> MLXArray {
    let (B, L) = (x.dim(0), x.dim(1))
    var queries = wq(x); var keys = wk(x); var values = wv(x)

    queries = queries.reshaped(B, L, args.attentionHeads, -1).transposed(0, 2, 1, 3)
    keys    = keys.reshaped(B, L, args.kvHeads, -1).transposed(0, 2, 1, 3)
    values  = values.reshaped(B, L, args.kvHeads, -1).transposed(0, 2, 1, 3)

    let offset = cache?.ropeOffset
    queries = applyRotaryPosition(rope, to: queries, offset: offset)
    keys    = applyRotaryPosition(rope, to: keys,    offset: offset)

    let output = attentionWithCacheUpdate(
        queries: queries, keys: keys, values: values, cache: cache, scale: scale, mask: mask)
        .transposed(0, 2, 1, 3).reshaped(B, L, -1)
    return wo(output)
}
```

Top level (`Llama.swift:152-203`):

```swift
public class LlamaModel: Module, LLMModel, KVCacheDimensionProvider {
    public let vocabularySize: Int
    public let kvHeads: [Int]
    public let model: LlamaModelInner
    @ModuleInfo(key: "lm_head") var lmHead: Linear?

    public init(_ args: LlamaConfiguration) {
        self.vocabularySize = args.vocabularySize
        self.kvHeads = (0 ..< args.hiddenLayers).map { _ in args.kvHeads }
        self.model = LlamaModelInner(args)
        if !args.tieWordEmbeddings {
            self._lmHead.wrappedValue = Linear(args.hiddenSize, args.vocabularySize, bias: false)
        }
    }

    public func callAsFunction(_ inputs: MLXArray, cache: [KVCache]?) -> MLXArray {
        let out = model(inputs, cache: cache)
        if let lmHead { return lmHead(out) } else { return model.embedTokens.asLinear(out) }
    }

    public func sanitize(weights: [String: MLXArray]) -> [String: MLXArray] {
        weights.filter { !$0.key.contains("self_attn.rotary_emb.inv_freq") }
    }
}
```

### 19.5 RoPE helpers (`Libraries/MLXLMCommon/RoPEUtils.swift`)

```swift
public typealias RoPELayer = OffsetLayer & ArrayOffsetLayer
public func initializeRope(dims: Int, base: Float, traditional: Bool,
                           scalingConfig: [String: StringOrNumber]?, maxPositionEmbeddings: Int?) -> RoPELayer
public func validateRoPEConfiguration(_ scalingConfig: [String: StringOrNumber]?,
                                      context: String = "rope_scaling", supportedTypes: Set<String>? = nil) throws
public func validateMROPESection(_ scalingConfig: …, context: String = "rope_scaling") throws
```
Recognized `rope_type`s: `default`/`linear` (→ `RoPE`), `proportional` (`ProportionalRoPE`),
`llama3` (`Llama3RoPE`), the YaRN family (`YarnRoPE`, defaults factor 32.0, orig max 4096,
beta_fast 32.0, beta_slow 1.0, mscale 1.0, mscale_all_dim 0.0), plus `DynamicNTKAlphaRoPE`
(added for Hunyuan, commit `5cd767e`), `SuScaledRoPE` (own file), and `longrope` /`mrope` validation.

Also available for porting: `SwitchGLU`, `FusedGateUpSwitchGLU`, `SwitchLinear`,
`QuantizedSwitchLinear`, `gatherSort`, `scatterUnsort`, `compiledSiluProduct`, `weightedExpertSum`
(`SwitchLayers.swift`); `GatedDelta.swift`; `InterpolationUtils.swift`;
`ParoQuant/{ParoQuantLoader,RotateQuantizedLinear}.swift`;
`Models/Gemma.swift` (`Gemma.RMSNorm` = `1.0 + weight` rmsNorm, `Gemma.clipResidual` for fp16 overflow);
`Models/Gemma4.swift` (`Gemma4SharedKVState`).

`Module.numParameters()` (`Module+Extensions.swift`) counts quantized layers correctly
(`qlin.scales.size * qlin.groupSize`).

### 19.6 Registration

LLM: add to `LLMTypeRegistry.shared` creators dict + a `ModelConfiguration` static on `LLMRegistry` +
add it to `all()`.
VLM: also register the processor class in `VLMProcessorTypeRegistry.shared`.
The `create` helper (private in each factory) is:

```swift
private func create<C: Codable, M>(_ configurationType: C.Type, _ modelInit: @escaping (C) -> M) -> (Data) throws -> M {
    { data in
        let configuration = try JSONDecoder.json5().decode(C.self, from: data)
        if let validating = configuration as? ModelConfigurationValidating { try validating.validateModelConfiguration() }
        return modelInit(configuration)
    }
}
```
so a config type conforming to `ModelConfigurationValidating { func validateModelConfiguration() throws }`
gets validated at instantiation.

### 19.7 Debugging a port

`porting.md:645-711` recommends a `trace` helper on both sides:

```swift
func trace(_ name: String, _ x: MLXArray) { print("\(name): \(x.shape) \(x.sum().item(Float.self))") }
```
```python
def trace(name, x): print(f"{name}: {x.shape} {x.sum().item()}")
```

Order of investigation: shapes → identical prompt tokens → identical sampling params/seed → array sums.

### 19.8 VLM processor pattern

`UserInputProcessor.prepare(input:) -> LMInput` must do: sRGB tone-curve conversion, user `Processing`
application, resample, normalize, `asMLXArray`, and **inject the model's image placeholder tokens**.
`MediaProcessing` (`Libraries/MLXVLM/MediaProcessing.swift`, 571 lines) public surface:

```swift
public struct ProcessedFrames { public let frames: [MLXArray]; timestamps: [CMTime]; totalDuration: CMTime }

public enum MediaProcessing {
    static func inSRGBToneCurveSpace(_ image: CIImage) -> CIImage
    static func inLinearToneCurveSpace(_ image: CIImage) -> CIImage
    static func bestFit(_ size: CGSize, in other: CGSize) -> CGSize
    static func bestFitScale(_ size: CGSize, in other: CGSize) -> CGFloat
    static func aspectRatioForResample(_ image: CIImage, size: CGSize) -> Float
    static func resampleLanczos(_ image: CIImage, to size: CGSize) -> CIImage
    static func resampleBicubic(_ image: CIImage, to size: CGSize) -> CIImage
    static func normalize(_ image: CIImage, mean:(CGFloat,CGFloat,CGFloat), std:(CGFloat,CGFloat,CGFloat)) -> CIImage
    static func asMLXArray(_ image: CIImage, colorSpace: CGColorSpace? = nil) -> MLXArray
    static func rectSmallerOrEqual(_ extent: CGRect, size: CGSize) -> Bool
    static func centerCrop(_ extent: CGRect, size: CGSize) -> CGRect
    static func centerCrop(_ image: CIImage, size: CGSize) -> CIImage
    static func fitIn(_ size: CGSize, shortestEdge: Int) -> CGSize
    static func fitIn(_ size: CGSize, longestEdge: Int) -> CGSize
    static func padToSquare(_ image: CIImage, backgroundColor: CIColor = .black) -> CIImage
    static func apply(_ image: CIImage, processing: UserInput.Processing?) -> CIImage
    static func asCIImageSequence(_ asset: AVAsset, samplesPerSecond: Int) async throws -> …
    static func asProcessedSequence(…)   // 4 overloads
}
// plus CIImage conveniences: .resampled(to:method:), .toSRGB(), .toLinear(),
// .normalized(mean:std:), .paddingToSquare(backgroundColor:), .asMLXArray(colorSpace:)
```

`VLMError` cases: `.imageRequired`, `.maskRequired`, `.singleImageAllowed`, `.singleVideoAllowed`,
`.singleMediaTypeAllowed`, `.imageProcessingFailure(String)`, `.processing(String)`,
`.noVideoTrackFound`, `.videoNotDecodable`.

VLM `prepare(_:cache:state:windowSize:)` should do **chunked prefill** (see the pattern in
`Libraries/MLXVLM/README.md:273-305`): merge image+text embeddings, loop in `windowSize ?? 512`
chunks with `asyncEval(cache)`, then one final `.logits(result)`.
Comment verbatim: "Single-pass prefill allocates transient buffers proportional to prompt length and
causes OOM on long prompts."

---

## 20. Tests

### 20.1 Unit tests — `Tests/MLXLMTests` (≈75 files)

Per `developing.md:12-17`: "The unit tests run without downloading model weights. There are some
tests that exercise the models by using random weights and mock tokenizers, see EvalTests."

Key harness types (`Tests/MLXLMTests/TestTokenizer.swift`):

```swift
struct TestTokenizer: MLXLMCommon.Tokenizer {
    let length = 8, maxLength = 50
    let _eosTokenId = 101, _unknownTokenId = 102     // deliberately OUTSIDE vocabularySize (100)
    init(vocabularySize: Int = 100)
    // encode() returns 8 random ids; decode() joins random 3-8 letter words
}

struct TestInputProcessor: UserInputProcessor {
    init()   // ModelConfiguration(id: "test") + TestTokenizer + DefaultMessageGenerator
    func prepare(input: UserInput) throws -> LMInput
}
```

Model tests build tiny configs and `quantize(model:groupSize:bits:)` then `eval(model)` **before**
concurrent use ("This ensures all weight promises are realized and avoids race conditions").

Notable suites: `ChatSessionTests`, `ChatSessionToolRoundTripTests`, `ToolTests`, `ToolCallIdTests`,
`KVCacheTests` (cache serialization round-trips per class), `TurboQuantTests`, `ParoQuantTests`,
`EvalTests` (incl. `testConcurrentEvaluation`, `testConcurrentSampling`), `SampleTests`,
`StopStringTests`, `CancellationTests`, `LoadWeightsTests`, `MixedPrecisionQuantLoadTests`,
`ModelConversionTests`, `LLMRegistryTests`, `VLMRegistryTests`, `ResolveTests`, `UserInputTests`,
`MediaProcessingTests`, `SpeculativeDecodingTests`, plus 10 `MTP*` suites and per-model tests
(DeepseekV2/V3, FalconH1, Hunyuan, Mamba2, Mixtral, NemotronH, NomicBert, SSM, Gemma4*, Qwen35*, LFM2*).

Both XCTest (`XCTestCase`) and swift-testing (`@Test` / `@Suite`) styles appear.

### 20.2 Integration tests — `IntegrationTesting/IntegrationTesting.xcodeproj`

Separate Xcode project (not a SwiftPM test target) that adds swift-huggingface + swift-transformers
and uses the `MLXHuggingFace` macros. Entry point:

```swift
private let models = IntegrationTestModels(
    downloader: #hubDownloader(),
    tokenizerLoader: #huggingFaceTokenizerLoader()
)

@Suite(.serialized)
struct ToolCallIntegrationTests { … }
```

`IntegrationTestModelIDs` (`Libraries/IntegrationTestHelpers/IntegrationTestHelpers.swift:36-43`):

```swift
public static let llm       = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
public static let vlm       = "mlx-community/Qwen3-VL-4B-Instruct-4bit"
public static let lfm2      = "mlx-community/LFM2-2.6B-Exp-4bit"
public static let glm4      = "mlx-community/GLM-4-9B-0414-4bit"
public static let mistral3  = "mlx-community/Ministral-3-3B-Instruct-2512-4bit"
public static let nemotron  = "mlx-community/NVIDIA-Nemotron-3-Nano-30B-A3B-4bit"
public static let qwen35    = "mlx-community/Qwen3.5-2B-4bit"
```

`IntegrationTestModels` is an `actor` caching `Task<Container, Error>` per `configuration.name`
(so each model loads at most once per run) with `llmContainer(for:)`, `vlmContainer(for:)`,
`embeddingContainer()` (nomic_text_v1_5).

Test-suite enums exported from `IntegrationTestHelpers`: `ChatSessionTests` (`oneShot`,
`oneShotStream`, `multiTurnConversation`, `visionModel`, `streamDetailsWithTools`, `toolInvocation`,
`planetsCoherence`, `promptRehydration`), `EmbedderTests` (`gemma3Embedder`, `readmeExample`),
`ToolCallTests` (per-family `*FormatAutoDetection` / `*EndToEndGeneration` / `*MultiToolGeneration`).
Also `hfCacheDir()`, `hfSnapshotDir(modelId:revision:)`, `downloadDataset(...)`,
`VisionTestImages.solidColor(_:size:)`.

Environment gates found in the integration tree:
`MLX_RUN_VLM_INTEGRATION=1`, `MLX_RUN_COLD_FETCH=1`, `MLX_RUN_FM_TOOL_INTEGRATION`,
`TEST_E2B_PAIR`, `TEST_E4B_PAIR`, `RECORD_C17_BASELINE=1`, `TURBO_FLASH_NR0`.

Default `GenerateParameters` used by the helpers: `GenerateParameters(maxTokens: 200, temperature: 0)`
(coherence test uses `maxTokens: 3000, temperature: 0`).

### 20.3 Running tests

From `CONTRIBUTING.md:22-55` (verbatim commands):

```bash
# unit tests — note: `swift test` DOES NOT WORK, use xcodebuild
xcodebuild test -scheme mlx-swift-lm-Package -destination 'platform=macOS' -skipPackagePluginValidation

# all integration tests
xcodebuild test \
  -project IntegrationTesting/IntegrationTesting.xcodeproj \
  -scheme IntegrationTesting \
  -destination 'platform=macOS' \
  -skipPackagePluginValidation

# a single integration test
xcodebuild test \
  -project IntegrationTesting/IntegrationTesting.xcodeproj \
  -scheme IntegrationTesting \
  -destination 'platform=macOS' \
  -skipPackagePluginValidation \
  -only-testing:IntegrationTestingTests/ToolCallIntegrationTests/qwen35FormatAutoDetection\(\)

# docs
scripts/verify-docs.sh
```

Why `-skipPackagePluginValidation` (commit `d242429`): "mlx-swift 0.31.5 added the CudaBuild
build-tool plugin, which xcodebuild refuses to run non-interactively without this flag."

---

## 21. CI, SDK/OS gating (macOS 26 vs 27) — the headline compatibility story

### 21.1 The gate

`MLXFoundationModels` (and `MLXHuggingFace/FoundationModelsMacros.swift`, and 37 integration-test
files) are guarded by:

```swift
#if FoundationModelsIntegration && canImport(FoundationModels, _version: 2)
```

- `FoundationModelsIntegration` is the SwiftPM **trait** (default on) — it is essentially always set.
- `canImport(FoundationModels, _version: 2)` is the **SDK version check**: true only on the
  macOS/iOS/visionOS **27.0 SDK**. On the 26 SDK the whole adapter compiles out to an empty library.
- Separately, all public FM API is `@available(iOS 27.0, macOS 27.0, visionOS 27.0, *)`.

`Package.swift:243-249` states the design intent:

> "Public surface is gated by @available(macOS 27 / iOS 27 / visionOS 27, *) and #if canImport(FoundationModels), so the target builds on every Xcode that compiles the rest of mlx-swift-lm."

### 21.2 Commit `3cbf928` — "Integration tests: build on both macOS 26 and 27 SDKs (#464)"

Message verbatim:

> The nightly IntegrationTesting job failed to compile on the Xcode 26.5 runner: the FoundationModels adapter (MLXFoundationModels) is gated behind `canImport(FoundationModels, _version: 2)` (macOS 27 SDK only), but the integration test files gated only on the always-set FoundationModelsIntegration trait, so they referenced symbols absent on the 26 SDK.
>
> - Extend the 37 FoundationModels-gated test files' top-level guard to `'#if FoundationModelsIntegration && canImport(FoundationModels, _version: 2)'`, mirroring the library so they compile out on the 26 SDK and stay active on 27.
> - Workflow: prefer Xcode 27 (via DEVELOPER_DIR) when the runner has it so the full suite runs; otherwise fall back to the default toolchain and run the SDK-agnostic suites (MTP, Qwen3VL/Qwen3.5 vision, Coherence, Gemma4, tool calls).

The workflow shell block (`.github/workflows/integration_tests.yml:21-42`):

```bash
dev=""
for app in /Applications/Xcode_27*.app /Applications/Xcode-27*.app /Applications/Xcode.app; do
  [ -d "$app" ] || continue
  v=$("$app/Contents/Developer/usr/bin/xcodebuild" -version 2>/dev/null | head -1)
  case "$v" in "Xcode 27"*) dev="$app/Contents/Developer" ;; esac
  [ -n "$dev" ] && break
done
if [ -n "$dev" ]; then
  echo "DEVELOPER_DIR=$dev" >> "$GITHUB_ENV"
else
  echo "FoundationModels tests will be compiled out (macOS 27 SDK required)."
fi
```

**SDK-agnostic suites** (run on Xcode 26): MTP, Qwen3VL/Qwen3.5 vision, Coherence, Gemma4, tool calls.
**27-only suites**: everything under `IntegrationTestingTests/MLXFoundationModelsIntegration/` plus
`VisionIntegrationTests.swift`.

Related SDK-drift commits:
- `2a76e56` — "FoundationModels renamed `GenerationOptions.SamplingMode.Kind`'s `.top`/`.nucleus`
  cases to `.randomTopK`/`.randomProbabilityThreshold`, which broke compilation against the newer SDK."
- `1c86cc1` — the FM-27 beta `.swiftinterface` declares
  `LanguageModelExecutorGenerationChannel.Response.Action.updateUsage(input:output:metadata: = [:])`
  but the shipping dylib exports only `updateUsage(input:output:)`; the compiled reference alone
  SIGSEGVs at load under chained-fixups linking, so the call was removed entirely.
- `9cd1a48` — "Fix FoundationModels API drift and the integration tests that no longer compiled".

### 21.3 CI workflows

`.github/workflows/pull_request.yml`:
- job `lint`: `ubuntu-22.04`, container `swift:6.2-rhel-ubi9`, installs `pre-commit` via `uv`,
  **builds swift-format from source pinned at `603.0.0`** and runs `pre-commit run --all`.
  Pin rationale verbatim: "a new swift-format release can change formatting rules and reformat files
  no PR touched, turning the whole-repo `pre-commit run --all` red on every open PR at once."
- job `mac_build_and_test`: self-hosted macOS; `xcodebuild -showComponent MetalToolchain`;
  `rm -rf ~/Library/Developer/Xcode/DerivedData/*`;
  `xcodebuild build-for-testing -skipPackagePluginValidation -scheme mlx-swift-lm-Package -destination 'platform=macOS'`;
  `scripts/verify-docs.sh`; then
  `xcrun xctest ~/Library/Developer/Xcode/DerivedData/mlx-swift-lm-*/Build/Products/Debug/MLXLMTests.xctest`.

`.github/workflows/integration_tests.yml`: `on: workflow_dispatch` only (the header still says
"Kept out of the PR path so they never block merges"; commit `5fbb130` mentions a nightly schedule but
the current file has no `schedule:` trigger), `runs-on: [self-hosted, macos]`, `timeout-minutes: 120`,
`-parallel-testing-enabled NO` (concurrent workers race on the shared HF cache),
`-resultBundlePath IntegrationTesting.xcresult`.

Formatting config `.swift-format`:

```json
{ "version": 1, "indentation": { "spaces": 4 },
  "spacesAroundRangeFormationOperators": true,
  "indentConditionalCompilationBlocks": false }
```

`.pre-commit-config.yaml` runs
`swift-format format --in-place --configuration .swift-format --recursive .`.

`.spi.yml`: `documentation_targets: [MLXLLM, MLXVLM, MLXLMCommon, MLXEmbedders]`
(MLXFoundationModels/MLXGuidedGeneration are **not** in SPI docs).

`scripts/verify-docs.sh`: sets `MLX_SWIFT_BUILD_DOC=1`, discovers library-product targets via
`swift package dump-package`, **filters out `MLXFoundationModels`** ("gated on the FoundationModels v2
SDK, so its DocC catalog can't be verified on SDKs that lack it"), and runs
`swift package generate-documentation --target "$TARGET" --warnings-as-errors` for each.

### 21.4 Linux

`Libraries/MLXLMCommon/Linux/` contains shims: `CoreGraphics.swift`, `CoreMedia.swift`,
`Logger.swift`, `String+Linux.swift`. Commit `65e28c2` "Make MLXLLM compilable on Linux (#321)" also
made `AudioFormat`/`AudioProcessing` platform-independent. Media-carrying enum cases are behind
`#if canImport(CoreImage)` / `#if canImport(AVFoundation)`.

---

## 22. `skills/` — the shipped agent skill

`skills/README.md` documents installation for three agents (paths differ):

```sh
# Claude Code
mkdir -p ~/.claude/skills && ln -s "$(pwd)/skills/mlx-swift-lm" ~/.claude/skills/mlx-swift-lm
# Codex
mkdir -p ~/.codex/skills && ln -s "$(pwd)/skills/mlx-swift-lm" ~/.codex/skills/mlx-swift-lm
# Droid
mkdir -p ~/.agents/skills && ln -s "$(pwd)/skills/mlx-swift-lm" ~/.agents/skills/mlx-swift-lm
```
Per-project variants use `.claude/skills`, `.codex/skills`, `.agents/skills`. "If your tool caches
skills, restart it after installing." `cp -R` works instead of `ln -s`.

`skills/mlx-swift-lm/SKILL.md` (431 lines) front matter:

```yaml
name: swift-mlx-lm
description: MLX Swift LM - Run LLMs and VLMs on Apple Silicon using MLX. Covers local inference, streaming, wired memory coordination, tool calling, LoRA fine-tuning, embeddings, and model porting.
triggers:
  - mlx
  - mlx-swift
  - mlx-lm
  - apple silicon llm
  - local llm swift
  - vision language model swift
  - lora training swift
  - wired memory
  - wiredmemory
  - wired memory ticket
  - model porting
  - add model support
```

**Note the name mismatch:** directory is `mlx-swift-lm` but the skill `name:` is `swift-mlx-lm`.

SKILL.md sections: 1 Overview & Triggers, 2 Key File Reference (path table), 3 Quick Start
(LLM chat / VLM with image / embeddings), 4 Primary Workflow: LLM Inference (ChatSession, streaming
via `ModelContainer.generate`, generation API surface, tool calling, `GenerateParameters`, wired
memory, prompt caching), 5 Secondary Workflow: VLM Inference, 6 Best Practices (DO/DON'T, thread
safety, memory management), 7 Reference Links, 8 Deprecated Patterns Summary, 9 Automatic vs Manual
Configuration.

Its deprecation table (`SKILL.md:396-404`) is a useful migration cheat sheet:

| If you see… | Use instead… |
|---|---|
| `generate(... didGenerate:)` callback | AsyncStream-based generation APIs |
| `perform { model, tokenizer in }` | `perform { context in }` |
| `TokenIterator(prompt: MLXArray)` | `TokenIterator(input: LMInput)` |
| `ModelRegistry` typealias | `LLMRegistry` or `VLMRegistry` |
| `createAttentionMask(h:cache:[KVCache]?)` | `createAttentionMask(h:cache:KVCache?)` |

The 12 reference files under `skills/mlx-swift-lm/references/`:

| file | lines | contents (section headings) |
|---|---|---|
| `generation.md` | 133 | Overview; **API Matrix** table (generate / generateTask / generateTokens / generateTokensTask / generateTokenTask × output × task handle × wiredMemoryTicket); Decoded Text/Tool Streaming; Task-Handle Pattern for Early Stop; Raw Token Streaming; With Wired Memory Coordination; Stop Reasons; Throwing vs Non-Throwing Behavior; Practical Defaults |
| `model-container.md` | 321 | Quick Reference type→file table; Creating/Using a ModelContainer; Convenience Methods; Generation + Wired Memory; ModelConfiguration; Model Factories; Registries; Type Registries; Loading Flow; Memory Management; Updating Model Parameters; Deprecated `perform()` signatures + `ModelRegistry` typealias |
| `kv-cache.md` | 295 | Cache Types (KVCacheSimple / RotatingKVCache / QuantizedKVCache); Dynamic Cache Quantization; Creating Caches (via model, via utility fns); Trimming; Serialization; Attention Masks; Memory Usage by Cache Type; Best Practices; Quantized Attention; MambaCache; CacheList; deprecated `createAttentionMask` signature + direct `cache.update()` on QuantizedKVCache |
| `tool-calling.md` | 333 | Supported Formats; Defining Tools; ToolParameter Types; Custom Schema; Passing Tools to Model; Processing Tool Calls (stream + execution); ToolCallProcessor; Processor with Tool Schemas; Format Auto-Detection; Explicit Format in Configuration; ToolCall Structure; Multi-Turn with Tool Results; Parser Protocol; Error Handling; DO/DON'T; Deprecated Patterns |
| `tokenizer-chat.md` | 322 | Tokenizer Loading (automatic + manual); Basic Encoding/Decoding; Chat Template; With Tools; Special Tokens; EOS Token Handling; Chat.Message; Using with ChatSession; MessageGenerator (Default / NoSystem / model-specific); StreamingDetokenizer + incomplete Unicode; Tokenizer Replacement Registry; deprecated `TokenIterator(prompt:)` |
| `concurrency.md` | 387 | SerialAccessContainer (incl. "Why Not Actor?"); SendableBox (consuming params, single consume); ModelContainer thread safety; ChatSession thread safety; AsyncStream patterns (creating, throwing boundaries, early termination, raw token task flow, cancellation); MLXArray & Sendable (eval before returning / SendableBox transfer / keep in isolation); Async Evaluation; Task Cancellation Best Practices; Deprecated callback `generate()` |
| `wired-memory.md` | 120 | Ticket Flow; Active vs Reservation Tickets; Policy Selection; Measurement-Driven Budgeting (text-only + multimodal); CPU and Unsupported Backends; Debug Event Stream; Practical Guidance |
| `supported-models.md` | 269 | LLM families (Llama/Mistral, Qwen, Gemma, Phi, DeepSeek, GLM, others); VLM families (Qwen VL, Gemma Vision, PaliGemma, others); Loading Any Model; Model-Specific Configurations (extra EOS tokens, tool call formats, tokenizer overrides); Adding New Model Types; Checking Supported Types; Memory Requirements |
| `lora-adapters.md` | 332 | LoRAConfiguration + `adapter_config.json` format; Loading Adapters (directory / from model); Applying (load weights / fuse / unload); Layer types (LoRALinear, QLoRALinear, DoRALinear); LoRAModel + LoRALayer protocols; Inference with adapter; Fuse for deployment; Hot-swap adapters; Memory considerations; Saving adapter weights; deprecated `LoRATrain.convert()` |
| `training.md` | 397 | Training Parameters; 5-step workflow (load model → apply LoRA layers → load data → configure optimizer → train); Progress Reporting; Data Formats (.txt, .jsonl); Loss Function + custom loss; Evaluation; Saving Weights (auto checkpointing + manual); Memory Optimization (sequence length, batch size, gradient checkpointing); Complete Example; Deprecated Patterns |
| `embeddings.md` | 316 | Pre-registered Models; Loading (registry / custom id / local dir / progress); Basic + Batch embeddings; Pooling strategies + custom pooling + options; EmbeddingModel protocol; Use cases (semantic search, RAG, clustering, similarity scoring); Model Configuration + Registry; Supported architectures; Memory considerations; deprecated `quantization` property |
| `model-porting.md` | 384 | Quick start; References to open; File structure mapping (Python→Swift); Configuration mapping incl. RoPE/`rope_scaling`; Module & weight key mapping; Structure patterns (Attention, SwiGLU MLP, transformer block, model inner, top-level model); Tied embeddings; `sanitize(weights:)`; LoRA; Registration; Common pitfalls; Minimal checklist; Testing |

**⚠ The skill content is stale relative to the 3.x API in this repo.** SKILL.md and several
references import `MLXLMHuggingFace  // from swift-huggingface-mlx` and
`MLXLMTokenizers   // from swift-tokenizers-mlx` and use `TokenizersLoader()` / `HubClient.default`.
Those packages are not referenced anywhere in `Package.swift`, `README.md`, or `using.md` — the
current supported paths are (a) hand-rolled `Downloader`/`TokenizerLoader` conformances, or
(b) the `MLXHuggingFace` macros over `swift-huggingface` + `swift-transformers`. The same stale
imports appear in `Libraries/MLXLMCommon/README.md`, `Libraries/MLXLLM/README.md`,
`Libraries/MLXVLM/README.md`, and `Libraries/MLXEmbedders/README.md`.

---

## 23. `tools/` and `scripts/`

### `tools/generate_mtp_fixtures.py`

Header: "Generate Python-reference fixtures for verifying Swift port of Gemma 4 MTP speculative
decoding. **Pinned to mlx-vlm commit: d49d428e9f570dc0387b9598b3b7e0ea391590d2**."
Capture technique: per-instance `__class__` swap to a locally-defined subclass overriding `__call__`.

CLI:

```
python generate_mtp_fixtures.py [--out DIR] [--suite {masks,drafter_forward,drafter_block,end_to_end,all}]
                                [--target-model-id ID] [--drafter-model-id ID] [--skip-end-to-end]
```
Defaults: `--out fixtures`, `--suite all`, target `mlx-community/gemma-4-31b-it-8bit`,
drafter `mlx-community/gemma-4-31B-it-assistant-bf16` (per `tools/fixtures/README.md:22-26`).
`assert_mlx_vlm_sha()` enforces the pinned mlx-vlm revision.

Output tree: `fixtures/{masks,drafter_forward,drafter_block,end_to_end}/*.safetensors` +
`FIXTURE-SCHEMA.md` + `FIXTURE-MANIFEST.json`.

### `tools/inspect_drafter_layout.py`

"Dump exhaustive weight-key inventory from a safetensors checkpoint directory… Reads tensor metadata
only (does not materialize arrays), so it works on multi-GB checkpoints."

```
python inspect_drafter_layout.py CHECKPOINT_DIR
python inspect_drafter_layout.py CHECKPOINT_DIR --plain     # just keys
python inspect_drafter_layout.py CHECKPOINT_DIR --json      # JSON [{key, shape, dtype, file}, ...]
python inspect_drafter_layout.py mlx-community/gemma-4-31B-it-assistant-bf16   # HF repo id via snapshot_download
```
Exit 0 on success, 1 on I/O/parse error.

### `tools/fixtures/`

The 43 `.safetensors` fixtures are **not vendored** — they live in the HF dataset
`angelsbrood/gemma4-mtp-fixtures` and are fetched on demand. Integration tests pin a dataset commit
SHA in a `fixturesRevision` constant at the top of each consuming test file. Regeneration workflow is
in `tools/fixtures/README.md:20-32`.

### `scripts/sync-xgrammar-source.sh`

```
scripts/sync-xgrammar-source.sh <sha-or-tag> [source-dir]     # source-dir defaults to ~/src/xgrammar
```
Rsyncs `cpp/**` (minus `tvm_ffi/`, `nanobind/`), `include/xgrammar/`,
`3rdparty/picojson/picojson.h`, `3rdparty/dlpack/include/dlpack/dlpack.h`, `LICENSE`, `NOTICE`;
auto-inits the dlpack submodule; writes `VERSION`. Currently pinned:

```
v0.1.30
Pinned to the upstream release tag v0.1.30
(resolved SHA d476a48dcd8fa3b5afeddbe850e73bb3b1dcf505, informational).
```

### `scripts/verify-docs.sh`

See §21.3.

---

## 24. Gotchas / footguns (consolidated)

1. **`swift test` does not work** — use `xcodebuild ... -skipPackagePluginValidation` (mlx-swift's
   CudaBuild plugin). `CONTRIBUTING.md:25`.
2. **`ModelFactoryError.noModelFactoryAvailable`** if neither `MLXLLM` nor `MLXVLM` is linked — the
   registry uses `NSClassFromString` and needs the module loaded.
3. **VLM factory is tried before LLM** in `ModelFactoryRegistry`; failures are swallowed and only the
   *last* error propagates.
4. **`TokenIterator.init` performs the prefill** and can throw; it is the expensive call.
5. **Early `break` out of an `AsyncStream<Generation>` leaves work in flight** — use the `…Task`
   variants and `await task.value`, or you may race on the KV cache.
6. **Do not call `cache.update()` before `attentionWithCacheUpdate`** — double update corrupts the
   cache (bit DeepSeek V2 & V3).
7. **`kvHeads` must be populated per layer** — `newCache` derives layer count from `kvHeads.count`.
8. **`ChatSession` is not thread-safe**; `ModelContainer` is. `MLXArray` is not `Sendable` — always
   `eval()` before returning from `perform`.
9. **`ChatSession` default `processing` resizes images to 512×512.**
10. **Restoring a saved KV cache**: do *not* also pass `instructions` if the cache already encodes a
    system prompt — "they would be re-tokenized on each call … without matching KV state, producing
    incoherent output."
11. **`generation_config.json` `eos_token_id` fully replaces (not unions) the `config.json` set**
    (matching Python mlx-lm).
12. **`stopStrings == nil` falls back to `extraEOSTokens`**; set it to `[]` explicitly to disable.
13. **`temperature` defaults to `0.6`, not 0** — set `temperature: 0` for deterministic output.
14. **`seed` is inert at `temperature == 0`.**
15. **`kvScheme` overrides `kvBits`; unknown scheme strings are silently ignored.**
16. **TurboQuant/affine quantization skips rotating (sliding-window) and recurrent layers.**
17. **`RotatingKVCache.toQuantized()` is never invoked by `maybeQuantizeKVCache`** (TODO in source).
18. **`ToolCallProcessor.processChunkOutputs` must not be mixed with `processChunk` / `processEOS` /
    `drainToolCalls`** on the same instance.
19. **Tool-call format auto-detection returns `nil` for plain `llama`** unless vocab ≥ 128000 or
    `rope_scaling.rope_type == "llama3"`.
20. **`ModelRegistry` typealias exists in both MLXLLM and MLXVLM** (both deprecated) — ambiguous if
    both modules are imported.
21. **`MTPDrafterTypeRegistry.shared` is empty at bootstrap**; you must
    `await Gemma4AssistantRegistration.register()` before loading a Gemma 4 drafter.
22. **`SendableBox.consume()` fatalErrors on a second call.**
23. **MLXFoundationModels compiles to an empty library on the macOS/iOS 26 SDK**; consumers must
    `#if canImport(FoundationModels, _version: 2)` their own call sites, not just `@available`.
24. **The `#huggingFaceLanguageModel` / `#hubDownloader` expansions need explicit imports at the call
    site** (`HuggingFace`, `Tokenizers`, `Foundation`, …) or you get confusing "cannot find type" errors.
25. **`preprocessor_config.json` wins over `processor_config.json`**, and `mistral3` /
    `gemma4_unified` override the declared `processor_class`.
26. **`loadLoRAData(url:)` `fatalError`s on an unknown extension** (only `.jsonl` / `.txt`).
27. **Model conversion refuses already-quantized sources** and PyTorch `.bin` weights.
28. **`swift-format` is pinned to `603.0.0`** in CI; a different local version will churn the diff.
29. **Integration tests must run with `-parallel-testing-enabled NO`** — concurrent xctest workers
    race on the shared `~/.cache/huggingface/` directory.
30. **The `skills/` content and per-library READMEs reference nonexistent packages**
    (`swift-huggingface-mlx` / `swift-tokenizers-mlx`, modules `MLXLMHuggingFace`, `MLXLMTokenizers`,
    `MLXEmbeddersHuggingFace`). Trust `README.md` + `using.md` instead.
31. **Qwen3VL vision head dim is 72** — outside the fused SDPA kernel's 64/80/128, so the code pads
    to 80; a naive dense joint mask cost 19.3 GB at 6144 tokens (commit `f7cacbc`).
32. **`ropeOffset` must be overridden on `BaseKVCache`, not just declared on a subclass** —
    protocol-extension witness binding otherwise wins silently.

---

## 25. Source inventory (files actually read this session)

All paths relative to `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-swift-lm`.

Root/meta: `README.md`, `CONTRIBUTING.md`, `Package.swift`, `.swift-format`,
`.pre-commit-config.yaml`, `.spi.yml`, `.github/workflows/pull_request.yml`,
`.github/workflows/integration_tests.yml`, `.github/pull_request_template.md`.

MLXLMCommon: `ModelContainer.swift`, `LanguageModel.swift`, `ModelFactory.swift`,
`Evaluate.swift` (read in 5 windows covering ~1,700 of 2,432 lines + full public-symbol grep),
`ChatSession.swift` (full), `Chat.swift` (full), `UserInput.swift` (full),
`ModelConfiguration.swift` (full), `Tokenizer.swift` (full), `Downloader.swift` (full),
`TokenizerLoader.swift` (full), `Load.swift` (full), `BaseConfiguration.swift` (full),
`KVCache.swift` (public-symbol grep + lines 1-380, 1560-1720, 1840-2110),
`AttentionUtils.swift` (full), `GenerationConfigFile.swift` (full),
`Extensions/Encodable+toolResult.swift`, `Extensions/JSONDecoder+JSON5.swift`,
`Utilities/SerialAccessContainer.swift` (full), `WiredMemoryPolicies.swift` (full),
`WiredMemoryUtils.swift` (grep), `SpeculativeDecoding.swift` (full), `MTPDrafterModel.swift` (full),
`MTPDrafterModelFactory.swift` (full), `ReasoningConfig.swift` (full),
`Registries/{ModelTypeRegistry,AbstractModelRegistry,ProcessorTypeRegistry}.swift` (full),
`Adapters/ModelAdapter.swift` (full), `Adapters/LoRA/LoRAContainer.swift` (full),
`ModelConversion.swift` (grep + lines 160-300), `RoPEUtils.swift` (grep + lines 20-90, 440-500),
`RoPEApplication.swift` (full), `Module+Extensions.swift` (full), `SwitchLayers.swift` (grep),
`JSONDecodingTypes.swift` (grep), `BidirectionalMasks.swift` (grep),
`Models/Gemma.swift` (full), `Models/Gemma4.swift` (full),
`Tool/{Tool,ToolCall,ToolCallFormat,ToolParameter}.swift` (full),
`Tool/ToolCallProcessor.swift` (lines 1-140 + full symbol grep),
`Documentation.docc/{using,upgrade,porting,developing,model-compatibility,kv-cache-quantization,wired-memory,Documentation}.md`.

MLXLLM: `LLMModelFactory.swift` (full), `LLMModel.swift` (full), `ModelConversion.swift` (full),
`Lora+Data.swift` (full), `LoraTrain.swift` (lines 1-140), `Models/Llama.swift` (lines 1-260),
`README.md`, `Documentation.docc/{adding-model,using-model,evaluation}.md`.

MLXVLM: `VLMModelFactory.swift` (full), `VLMModel.swift` (full),
`Gemma4AssistantRegistration.swift` (full), `MediaProcessing.swift` (public-symbol grep), `README.md`.

MLXEmbedders: `ModelFactory.swift` (full), `EmbedderModelContainer.swift` (full),
`EmbeddingModel.swift` (full), `Pooling.swift` (grep), `README.md` (partial).

MLXHuggingFace / macros: `Macros.swift` (full), `FoundationModelsMacros.swift` (full),
`MLXHuggingFaceMacros/HuggingFaceIntegrationMacros.swift` (full).

MLXFoundationModels: `README.md` (first 45 lines).
MLXGuidedGeneration: `README.md` (first 45 lines).
MLXCXGrammar: `xgrammar/VERSION`.

Helpers: `Libraries/IntegrationTestHelpers/IntegrationTestHelpers.swift`
(lines 1-160, 205-355 + full symbol grep), `Libraries/IntegrationTestHelpers/README.md`,
`Libraries/BenchmarkHelpers/BenchmarkHelpers.swift` (symbol grep).

Tests: `Tests/MLXLMTests/README.md`, `TestTokenizer.swift` (full), `EvalTests.swift` (lines 1-130),
`ChatSessionTests.swift` (lines 1-120), `ToolTests.swift` (lines 1-90), `KVCacheTests.swift` (grep),
`Tests/mlx-libraries-Package.xctestplan` (0 bytes — empty file).

IntegrationTesting: `IntegrationTesting/IntegrationTesting/IntegrationTesting.swift`,
`IntegrationTestingTests/ToolCallIntegrationTests.swift` (lines 1-80),
`IntegrationTestingTests/VisionIntegrationTests.swift` (lines 1-60).

skills: `skills/README.md` (full), `skills/mlx-swift-lm/SKILL.md` (full),
headings of all 12 `references/*.md`, first 70 lines of `references/generation.md`,
first 60 lines of `references/model-container.md`.

tools/scripts: `tools/generate_mtp_fixtures.py` (header + `main()`),
`tools/inspect_drafter_layout.py` (header + `main()`), `tools/fixtures/README.md`,
`scripts/verify-docs.sh` (full), `scripts/sync-xgrammar-source.sh` (full).

git: `git log --oneline -50`, `git show 3cbf928` (stat + head), bodies of 34 recent commits.

---

## 26. Open questions / unverified

1. **`GenerateParameters` has no `maxKVSize`+`kvScheme` interaction test I read** — the docs say
   rotating caches are skipped, but I did not read `TurboQuantKVCache.swift` (1,765 lines) or
   `TurboQuantKernels.swift` (2,367 lines). Numbers in the scheme table are quoted from the DocC
   article, not independently verified.
2. **The `SpeculativeTokenIterator` body (lines 864-1069) was not read** — accept/reject sampling
   details, bonus-token handling, and how `numDraftTokens` interacts with `maxTokens` are UNVERIFIED.
3. **`MTPSpeculativeTokenIterator.swift` (500 lines) was not read** — sticky-passthrough triggers and
   the `passthroughReason` strings are UNVERIFIED.
4. **`ToolCallProcessor` lines 140-856 were not read line by line** — the exact bare-JSON fallback
   heuristics, per-format EOS handling (Mistral/LFM2), and `stripProtocolSpans` semantics are only
   known from symbol names and doc comments.
5. **`ParoQuant` (`ParoQuantLoader.swift`, `RotateQuantizedLinear.swift`)** — read only as filenames;
   no notes on what checkpoint format it loads.
6. **`LoRATrain.train` signature beyond `Parameters`** — I read the doc comment and `Parameters` but
   not the actual `train(model:train:validate:optimizer:tokenizer:parameters:progress:)` declaration;
   the progress-callback type name is UNVERIFIED.
7. **`ModelConversionStage` case list** — inferred from `progressHandler(.init(stage: …))` call sites
   (`downloading`, `copyingFiles`, `loadingWeights`, `quantizing`, `savingWeights`,
   `updatingConfiguration`); the full enum was not read.
8. **`ModelConversionOptions` default values** (`maxShardSize`, `overwriteExistingOutput`) were not read.
9. **Whether the integration-tests workflow still runs nightly** — commit `5fbb130` says
   "manually (workflow_dispatch) and nightly (schedule)", but the current
   `integration_tests.yml` has only `workflow_dispatch`. Possibly the schedule was removed later.
10. **Exact `mlx-swift` version resolved** — `Package.resolved` is not committed;
    `.upToNextMinor(from: "0.31.4")` plus a commit reference to "mlx-swift 0.31.5" is all I have.
11. **Per-model architectures** — I read only `Llama.swift` in full-ish. The other 55 LLM / 17 VLM
    model files were catalogued but not read; their `sanitize` quirks and config keys are unknown.
12. **`MLXGuidedGeneration` / `MLXFoundationModels` internals** — deliberately out of scope here
    (other agents); I captured only READMEs, `Package.swift` wiring, and the SDK gate.
13. **`Tests/mlx-libraries-Package.xctestplan` is a 0-byte file** — either a placeholder or an
    accidental empty commit. Its intended contents are unknown.
14. **`skills/mlx-swift-lm/references/*.md` bodies** — I read headings for all 12 plus the opening
    of two. Individual code snippets inside the other 10 are UNVERIFIED (and, given the stale
    package names, should be treated as suspect).
