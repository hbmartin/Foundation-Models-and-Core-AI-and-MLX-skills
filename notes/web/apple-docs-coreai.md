# Apple Developer Docs — Core AI framework (complete API reference harvest)

**Agent:** `apple-docs-coreai` (web research)
**Harvest date:** 2026-07-27
**Method:** `curl` directly against `https://sosumi.ai/documentation/<path>` (Apple docs → AI-readable markdown mirror) **plus** Apple's own raw DocC JSON API at `https://developer.apple.com/tutorials/data/documentation/<path>.json`, which recovers content sosumi drops (termLists, tables, parameter blocks, per-declaration platform lists).

**Coverage claim:** I enumerated Apple's full nav index via `https://developer.apple.com/tutorials/data/index/coreai` → **312 symbol/page entries** (1 module, 7 articles, 2 collections, 31 structs, 6 enums, 3 classes, 3 protocols, 100 properties, 56 methods, 53 cases, 42 inits, 8 subscripts). I verified that **every one of those 312 paths appears in the index page I captured** (diff returned `MISSING: 0`). Every declaration below was read this session.

> ⚠️ Everything in Core AI is **Beta** as of this harvest. All symbols are `27.0+`.

---

## 0. TL;DR orientation

Core AI is a **new framework** (not Core ML). Tagline: *"Run AI models in your app on Apple silicon."*

The pipeline is:

```
PyTorch model
  → [Core AI PyTorch Extensions: coreai-torch]  → .aimodel   (portable, unspecialized)
  → [optional: xcrun coreai-build compile]      → .aimodelc  (per-device-architecture, AOT-compiled)
  → [on-device specialization]                  → cached specialized asset (AIModelCache)
  → AIModel → InferenceFunction → run(inputs:) → NDArray / CVPixelBuffer
```

Three separate tools ship alongside:
1. **Core AI Debugger** — standalone macOS app (separate download).
2. **Core AI debug gauge** — Xcode Debug navigator gauge.
3. **Core AI instrument** — Instruments template.

Plus one CLI: **`xcrun coreai-build compile`**.

---

## 1. Framework page

Source: `https://sosumi.ai/documentation/coreai/` → `https://developer.apple.com/documentation/coreai/`

```
Framework
# Core AI
Available on: iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta,
              macOS 27.0+ Beta, tvOS 27.0+ Beta, visionOS 27.0+ Beta, watchOS 27.0+ Beta
> Run AI models in your app on Apple silicon.
```

### Overview (verbatim)

> "Core AI helps you build, run, and deploy AI models in your app. Designed with Apple silicon in mind, Core AI allows your app to use the latest model architectures and inference techniques across the CPU, GPU, and Neural Engine. The Swift API makes common tasks simple, while giving you more control over model specialization, caching, and inference performance when needed."

> "Alongside the framework, Core AI includes additional tools for model preparation, integration, and debugging. Prepare your models for Apple silicon with [Core AI Optimization](https://apple.github.io/coreai-optimization), then convert them into the `.aimodel` format with [Core AI PyTorch Extensions](https://apple.github.io/coreai-torch). The [Core AI Debugger](https://developer.apple.com/core-ai-debugger/) app supports visualization and numeric debugging, letting you inspect model structure and trace tensor values directly back to your Python source code."

> "Core AI also integrates with Xcode and the developer toolchain. The Core AI debug gauge and Core AI instrument help you monitor and profile inference performance in your app. You can also compile models ahead of time with the `coreai-build` command-line tool."

> "If your app uses model types other than neural networks, such as decision trees or tabular feature engineering, see [Core ML](/documentation/CoreML)."

**External URLs cited by Apple on this page:**
- `https://apple.github.io/coreai-optimization` — Core AI Optimization
- `https://apple.github.io/coreai-torch` — Core AI PyTorch Extensions
- `https://developer.apple.com/core-ai-debugger/` — Core AI Debugger app download

Hero image asset: `https://docs-assets.developer.apple.com/published/3436c2b440f83e13deb0e14474c5e08e/core-ai-framework-hero%402x.png`

### ⚠️ Availability quirk (VERIFIED, surprising)

The **framework** page lists 7 platforms including macOS and Mac Catalyst. But **every individual symbol page's `metadata.platforms` array omits macOS and Mac Catalyst**. Raw JSON check:

```
coreai          → iOS, iPadOS, Mac Catalyst, macOS, tvOS, visionOS, watchOS  (all 27.0 beta)
coreai/aimodel  → iOS, iPadOS, tvOS, visionOS, watchOS                       (no macOS, no Mac Catalyst)
coreai/ndarray  → iOS, iPadOS, tvOS, visionOS, watchOS
coreai/inferencefunction → iOS, iPadOS, tvOS, visionOS, watchOS
```

However the **`declarations` section of the same JSON** lists `platforms: [iOS, iPadOS, Mac Catalyst, tvOS, visionOS, watchOS]` — i.e. Mac Catalyst *is* there but macOS still isn't. This is almost certainly a **docs-generation bug**, since Core AI Debugger requires macOS 27 hosts, the Instruments template runs on macOS, `coreai-build` runs on macOS, and the debug gauge works in Xcode on Mac. Treat macOS 27 as supported; flag as a doc inconsistency.

**Notable narrower availability (real, not a bug):** Metal-backed initializers drop **watchOS**:
- `NDArray.RawView.init(metalBuffer:...)` → `DECL(iOS, iPadOS, Mac Catalyst, tvOS, visionOS)`
- `InferenceFunction.AsyncValue.init(unsafeBuffer:...)` → `DECL(iOS, iPadOS, Mac Catalyst, tvOS, visionOS)`
- `ComputeStream.init(commandQueue:)` → `DECL(iOS, iPadOS, Mac Catalyst, tvOS, visionOS)`
  (but `ComputeStream.init()` and `currentWorkCompleted()` include watchOS)

---

## 2. `AIModel`

```swift
struct AIModel
```
Conforms to: `Sendable`, `SendableMetatype`.

> "A specialized model for running inference on a device."

### Overview (verbatim)

> "An `AIModel` represents a specialized `.aimodel` asset, optimized for the current device's hardware. You create one by loading the asset from disk:"

```swift
let model = try await AIModel(contentsOf: modelURL)
```

> "Use `functionDescriptor(for:)` to inspect a function's inputs and outputs, then load an `InferenceFunction` to run inference."

> **NOTE:** "The model instance is lightweight and doesn't own weights or intermediate buffers. Those resources belong to the functions you load from it."

### Full member list with exact signatures

```swift
// Creating a model
init(contentsOf modelURL: URL, options: SpecializationOptions = .default) async throws
init?(resolvingBookmark bookmark: Data) throws

// Loading inference functions
func loadFunction(named functionName: String) throws -> InferenceFunction?
func functionDescriptor(for functionName: String) -> InferenceFunctionDescriptor?
var functionNames: [String] { get }

// Specializing a model
@discardableResult
static func specialize(contentsOf modelURL: URL,
                       options: SpecializationOptions = .default,
                       cache: AIModelCache = .default,
                       cachePolicy: AIModelCache.Policy = .default) async throws -> AIModel

// Inspecting a model
var bookmarkData: Data { get }
static var deviceArchitectureName: String { get }
```

### `init(contentsOf:options:)`

- **modelURL**: "The URL of a `.aimodel` or `.aimodelc` file."
- **options**: "Options for the specialization process."
- Discussion: *"This initializer specializes the model if needed, caching the result for future calls. Specializing the model can take a significant amount of time depending on model size and the compute unit types it targets. This initializer always uses the `default` cache."*
- Aside (NOTE): *"If specializing or loading the model fails."* — ⚠️ this is a malformed doc string; it's clearly a truncated `- Throws:` clause rendered as a Note. Same malformation appears on `specialize(...)`.

### `init(resolvingBookmark:)`

- **bookmark**: "Data previously obtained from `AIModel.bookmarkData`."
- Return: *"If the bookmark data can be resolved, the resulting `AIModel` pins and references the cache entry as the model that generated the bookmark data. If it cannot be resolved due to the specialized asset entry no longer being present nil is returned."*
- Discussion: *"Resolving bookmark data involves checking it is a valid bookmark, validating the associated cache and cache entry it references exists, and returning a AIModel constructed with that specialized asset contained within that entry. If any of these steps fail, nil is returned"*
- NOTE: *"If the bookmark data is malformed due to not being sourced from AIModel.bookmarkData an error is thrown"*

**Key distinction:** malformed bookmark → **throws**; valid-but-stale bookmark → **returns nil**.

### `functionDescriptor(for:)`
- Return: "A descriptor for the function, or `nil` if the model doesn't contain a function with the specified name."
- Discussion: "Use the descriptor to inspect the function's inputs, outputs, and state names before loading it for inference."

### `bookmarkData`
- Discussion: *"The data returned can be stored and later resolved to re-create a model with init?(resolvingBookmark:). It contains information about the cache and entry backing the model"*
- ⚠️ **NOTE (footgun):** *"Bookmark data is just data. It does not pin entries in the cache. Only a `AIModel` will pin its associated entry in the cache while it is held."*

### `deviceArchitectureName`
- Discussion: *"When compiling model assets ahead of time with `xcrun coreai-build compile`, the toolchain produces artifacts for specific device architectures. Use this property to discover which compiled asset matches the current device."*

---

## 3. `AIModelAsset` — inspect without specializing

```swift
struct AIModelAsset
```

> "An unspecialized source model asset."

Overview (verbatim):
> "Use a model asset to inspect a model's structure and metadata without specializing it for a specific device. This lets you query model information without performing specialization, which is an expensive operation. You create a model asset by providing the URL of an `.aimodel` bundle on disk:"

```swift
let asset = try AIModelAsset(contentsOf: modelURL)
guard let summary = try asset.summary(includingStatistics: true) else { return }
```

> "Unlike `AIModel`, a model asset can't perform inference. Instead, use it to query model information such as function signatures, input and output descriptions, compute and storage types, and author-provided metadata."

### Signatures

```swift
init(contentsOf url: URL) throws
static func isValid(at url: URL) -> Bool

var metadata: AIModelAsset.Metadata { get }
func summary(includingStatistics: Bool) throws -> AIModelAsset.Summary?
let url: URL

mutating func updateMetadata(_ updates: (inout AIModelAsset.Metadata) throws -> Void) throws
mutating func removeDerivedArtifacts() throws
```

### `isValid(at:)` — Discussion (verbatim)
> "This checks that:
> - the URL is a file URL
> - the extension is one of the known model asset extensions
> - the model contains either a source program or a derived artifact"

### `summary(includingStatistics:)`
- **includingStatistics**: *"A Boolean value that indicates whether to read detailed model statistics. If `false`, the summary contains only version information and function signatures. **Including model statistics is considerably slower for large models.**"*
- Return: "The model summary, or `nil` if no program bytecode exists."

### `updateMetadata(_:)` — Discussion + Example (verbatim)
> "Pass a closure that takes the existing metadata and updates it. After the closure executes, this method writes the new metadata to the model asset on disk."

```swift
var asset = try AIModelAsset(contentsOf: input)
try asset.updateMetadata { metadata in
  metadata.author = "Alice"
  metadata.description = "An example model"
  metadata["iterations"] = 1000 // Custom metadata
}
```

### `AIModelAsset.FunctionDescriptor`
```swift
struct FunctionDescriptor
var name: String { get }
var inputs: [AIModelAsset.ValueDescriptor] { get }
var outputs: [AIModelAsset.ValueDescriptor] { get }
var states: [AIModelAsset.ValueDescriptor] { get }
```

### `AIModelAsset.ValueDescriptor`
```swift
struct ValueDescriptor
var name: String { get }
var typeName: String { get }     // NOTE: a String, not a strongly-typed enum
```

### `AIModelAsset.Metadata`
```swift
struct Metadata
init()

var description: String { get set }     // "Returns an empty string if the model has no description."
var author: String { get set }
var license: String { get set }
var creationDate: Date? { get set }

var creatorDefinedMetadata: [String : AIModelAsset.Metadata.CreatorDefinedValue] { get set }
// "Returns an empty dictionary if the model has no creator-defined metadata."
```

Typed subscripts (six overloads, disambiguated by the second `type:` parameter which defaults):
```swift
subscript(key: String, type: String.Type = String.self) -> String? { get set }                            // -44ov4
subscript(key: String, type: Bool.Type = Bool.self) -> Bool? { get set }                                  // -50v52
subscript(key: String, type: [CreatorDefinedValue].Type) -> [CreatorDefinedValue]? { get set }            // -5o1kb
subscript(key: String, type: [String : CreatorDefinedValue].Type) -> [String : CreatorDefinedValue]? { get set } // -5se5j
subscript(key: String, type: Double.Type = Double.self) -> Double? { get set }                            // -6bxrd
subscript(key: String, type: Int.Type = Int.self) -> Int? { get set }                                     // -9hpy0
```

Overview example (verbatim):
```swift
var asset = try AIModelAsset(contentsOf: modelURL)
try asset.updateMetadata { metadata in
  metadata.author = "Alice"
  metadata["iterations"] = 1000
  metadata["accuracy"] = 0.95
}
```

### `AIModelAsset.Metadata.CreatorDefinedValue`
```swift
enum CreatorDefinedValue
case string(String)
case integer(Int)
case number(Double)
case bool(Bool)
case array([AIModelAsset.Metadata.CreatorDefinedValue])
case dictionary([String : AIModelAsset.Metadata.CreatorDefinedValue])

init(_: [String : AIModelAsset.Metadata.CreatorDefinedValue])   // -1q79a
init(_: Bool)                                                    // -2lzjt
init(_: Double)                                                  // -40q72
init(_: String)                                                  // -5y6lm
init(_: Int)                                                     // -61sg1
init(_: [AIModelAsset.Metadata.CreatorDefinedValue])             // -9xsmm

// Default Implementations → CustomStringConvertible Implementations
var description: String { get }
```
(JSON-ish value model. Note the case is `integer(Int)` but the init is `init(_: Int)`.)

### `AIModelAsset.Summary`
```swift
struct Summary
var computeTypes: [String] { get }
var storageTypes: [AIModelAsset.Summary.StorageType] { get }
var operationDistribution: [AIModelAsset.Summary.OperationCount] { get }
var functions: [AIModelAsset.FunctionDescriptor] { get }
```
Overview: *"Obtain a summary by calling `summary(includingStatistics:)`. The summary describes the model's functions, storage types, compute types, and operation distribution."*

```swift
struct OperationCount
var operationName: String { get }
var count: Int { get }

struct StorageType
var typeName: String { get }
var count: Int { get }
```

---

## 4. `InferenceFunction`

```swift
struct InferenceFunction
```
Conforms to: `Sendable`, `SendableMetatype`.

> "A function that performs inference on input values and produces output values."

Overview (verbatim):
> "An `InferenceFunction` owns the resources needed for inference, including model weights and intermediate buffers. You load a function from an `AIModel` and call `run(inputs:states:outputViews:)` to perform inference."
> "This type is `Sendable`, so you can run it concurrently from multiple tasks. **The function automatically allocates additional intermediate buffers as needed to support concurrency.**"

⚠️ That last sentence is a memory footgun: concurrent `run` calls silently grow scratch memory.

### `run` overload A — dictionary of NDArray (convenience)

```swift
func run(inputs: [String : NDArray],
         states: consuming InferenceFunction.MutableViews = MutableViews(),
         outputViews: consuming InferenceFunction.MutableViews = MutableViews())
    async throws -> InferenceFunction.Outputs
```
(doc slug `-mqfb`)

- **inputs**: "A dictionary that maps input names to their `NDArray` values."
- **states**: *"The in-out arguments of the function, which the function reads and writes during inference. **You must provide views for all states; omitting any state produces an error.**"*
- **outputViews**: *"Pre-allocated output values that the function updates during inference. **Outputs with a provided view are updated in-place and are not included in the returned `InferenceFunction.Outputs`.** Outputs without a provided view produce new values in the returned `InferenceFunction.Outputs`."*
- Discussion: "This is a convenience overload that accepts a dictionary of `NDArray` values instead of an `InferenceFunction.Inputs` collection."
- ⚠️ **"Any `NDArray` values in the returned outputs have a row-major contiguous layout."**

### `run` overload B — `Inputs` collection

```swift
func run(inputs: borrowing InferenceFunction.Inputs,
         states: consuming InferenceFunction.MutableViews = MutableViews(),
         outputViews: consuming InferenceFunction.MutableViews = MutableViews())
    async throws -> InferenceFunction.Outputs
```
(doc slug `-14emi`) — same parameter docs; same row-major-contiguous guarantee on returned outputs.

### `encode(inputs:states:outputViews:to:)` — async pipelining

```swift
func encode(inputs: [String : InferenceFunction.AsyncValue],
            states: consuming InferenceFunction.AsyncMutableViews = AsyncMutableViews(),
            outputViews: consuming InferenceFunction.AsyncMutableViews = AsyncMutableViews(),
            to stream: ComputeStream)
    throws -> [String : InferenceFunction.AsyncValue]
```

- Note this is **`throws`, not `async throws`** — it returns as soon as the work is *encoded*.
- **states**: *"The `inout` arguments that the function reads and writes during inference. Note that views for states are not optional. Omitting a view for any state results in an error."*
- **outputViews**: *"…The returned dictionary doesn't contain `InferenceFunction` outputs for which you provide a view, because the inference updates the mutable view in place. When you don't provide a view, the returned dictionary includes a new async output value."*
- Return: "A dictionary mapping output name to an `InferenceFunction.AsyncValue` for each output not included in `outputViews`."
- Discussion: *"When this method returns, the compute may still be running on `stream`. You can pass the returned async values as inputs to subsequent `encode` calls to build a pipeline of inferences without waiting for intermediate results, or await them to retrieve the final compute outputs on the CPU."*

**Verbatim example from the docs:**
```swift
let computeStream = ComputeStream()
let pipelineFunctionOne: InferenceFunction = ...
let pipelineFunctionTwo: InferenceFunction = ...
let initialInput: NDArray = ...

// Run stage one of pipeline and get async value output.
let asyncInput = InferenceFunction.AsyncValue(initialInput)
let functionOneOutputs = try pipelineFunctionOne.encode(inputs: ["input": asyncInput], to: computeStream)
guard let functionOneOutput = functionOneOutputs["output"] else {
    // Handle unexpected missing output
    return
}

// Feed output from function one as an input to function two.
// Note that function one may be running the actual compute asynchronously while function two
// encodes its inference.
let functionTwoOutputs = try pipelineFunctionTwo.encode(inputs: ["input": functionOneOutput], to: computeStream)
guard let functionTwoOutput = functionTwoOutputs["output"] else {
    // Handle unexpected missing output
    return
}

// Now both inferences have been encoded
guard let finalNDArray = try await functionTwoOutput.ndArray else {
    // Handle case where output is not an NDArray
    return
}
```

### `descriptor`
```swift
let descriptor: InferenceFunctionDescriptor
```
(a stored `let`, not a computed property)

### `InferenceFunction.Inputs`
```swift
struct Inputs
init()
mutating func insert(_ rawView: consuming NDArray.RawView, for inputName: String)                                    // -3eg32
mutating func insert(_ value: borrowing some InferenceValue.ViewRepresentable & ~Copyable, for inputName: String)    // -2htrp
mutating func insert<Element>(_ view: consuming NDArray.View<Element>, for inputName: String)
    where Element : BitwiseCopyable                                                                                   // -5o5oi
```
Overview: *"Build an `Inputs` collection by calling `insert(_:for:)` for each named input the function expects, then pass it to `InferenceFunction/run(inputs:states:outputViews:)`."*

### `InferenceFunction.Outputs`
```swift
struct Outputs
mutating func remove(_ outputName: String) -> InferenceValue?
var count: Int { get }
var names: some Collection<String> { get }
```
`remove(_:)` Discussion: *"After you remove a value, subsequent calls with the same name return `nil`."*
(Destructive read — `Outputs` is a take-once bag, not a dictionary.)

### `InferenceFunction.MutableViews`
```swift
struct MutableViews
init()
mutating func insert(_ value: inout some InferenceValue.MutableViewRepresentable & ~Copyable, for name: String)  // -1b2yx
mutating func insert<Element>(_ mutableView: consuming NDArray.MutableView<Element>, for name: String)
    where Element : BitwiseCopyable                                                                              // -8ossp
mutating func insert(_ mutableRawView: consuming NDArray.MutableRawView, for name: String)                       // -9ixpc
```
Used for **both** `states:` and `outputViews:`.

### `InferenceFunction.AsyncValue`
```swift
final class AsyncValue          // a class, and Sendable
init(_: CVReadOnlyPixelBuffer)                                          // -5qtut
init(_: consuming InferenceFunction.AsyncMutableValue)                  // -90hbj
init(_: consuming NDArray)                                              // -9wk3
init(unsafeBuffer: consuming any MTLBuffer, byteOffset: Int = 0,
     scalarType: NDArray.ScalarType, shape: [Int], strides: [Int] = [],
     interleaveLayout: NDArray.InterleaveLayout? = nil)                 // no watchOS

var kind: InferenceValue.Kind { get }
final var ndArray: NDArray? { get async throws }
final var pixelBuffer: CVReadOnlyPixelBuffer? { get async throws }
```

Overview (verbatim):
> "An `AsyncValue` contains an underlying `InferenceValue` however that value may be actively in-use by some previously dispatched async work, and thus accessing the underlying value below an `AsyncValue` requires an `await` to wait for any previous compute writing it to be complete."
> "An `AsyncValue` is immutable once any previous compute has completed."
> "Async values can be used in async pipelines of inference to dispatch multiple inference functions in sequence without waiting for each to complete before dispatching the next. This can improve performance by parallelizing phases of the inferences which are not data dependent"

Doc example (verbatim — **note this snippet omits the required `to:` stream argument and has a typo `embeddingsOutputs` vs `embeddingOutputs`; it does not compile as written**):
```swift
 // Pipeline encoding of a text embedding function followed by decoder
 var textTokens: NDArray = ...
 let embeddingOutputs = try textEmbeddingFunction.encode(inputs: ["tokens": .init(textTokens)])
 let embeddings: InferenceFunction.AsyncValue = embeddingsOutputs["embeddings"]

 let decoderOutputs = try decodingFunction.encode(inputs: ["embeddings": embeddings])
 let logits = decoderOutputs["logits"]!
 // Await the compute of logits to be complete
 let logitsNDArray = try await logits.ndArray
```

⚠️ **Aliasing note on `.ndArray`:** *"If this value was constructed from a provided MTLBuffer directly, then this will return a **copy** of the data to avoid unsafe aliasing. If aliasing is desired, you can work with the original MTLBuffer directly."* Returns `nil` if `kind` is not `.ndArray`.

⚠️ `init(unsafeBuffer:)`: *"`unsafeBuffer` must have `shared` storage mode. Initializing an async value this way requires that you manually ensure the provided metal buffer is not mutated while this value is being used by an inference function."*
Parameter defaults: `byteOffset: Int = 0`, `strides: [Int] = []` (*"If left empty, they will be computed as contiguous row-major."*), `interleaveLayout: ... = nil`.

### `InferenceFunction.AsyncMutableValue`
```swift
struct AsyncMutableValue        // a struct (unlike AsyncValue which is a class)
init(_: consuming CVMutablePixelBuffer)                             // -4aqgq
init(_: consuming NDArray)                                          // -x6se
init(descriptor: consuming InferenceValue.Descriptor)
init(unsafeBuffer: consuming any MTLBuffer, byteOffset: Int = 0,
     scalarType: NDArray.ScalarType, shape: [Int], strides: [Int] = [],
     interleaveLayout: NDArray.InterleaveLayout? = nil)

var ndArray: NDArray? { get async throws }
var pixelBuffer: CVMutablePixelBuffer? { get async throws }
```
Overview (verbatim):
> "When dispatching an `encode(inputs:states:outputViews:to:)`, mutable values are what is included in the states and output vaiews." *(sic — typo "vaiews" in Apple's docs)*
> "Similar to `InferenceFunction.AsyncValue`, this type is a wrapper around an underlying inference value, however this type may be mutated repeatedly after construction by providing it as a state argument in sequence to one or more inference functions."
> "**When encoding a sequence of inferences which each mutate the same `AsyncMutableValue`, the framework will insert the necessary synchronization to avoid it being read or written while a previous write is occurring.**"

`init(descriptor:)`: *"Note that the descriptor must not have a dynamic shape."*

### `InferenceFunction.AsyncMutableViews`
```swift
struct AsyncMutableViews
init()
mutating func insert(_ mutableValue: inout InferenceFunction.AsyncMutableValue, for name: String)
```
Param doc: *"The mutable value that this collection will reference. **Its lifetime is tied to the resulting collection.**"*

---

## 5. `InferenceFunctionDescriptor`

```swift
struct InferenceFunctionDescriptor          // Sendable, SendableMetatype

var name: String { get }

var inputCount: Int { get }
var inputNames: [String] { get }
func inputDescriptor(of inputName: String) -> InferenceValue.Descriptor?

var outputCount: Int { get }
var outputNames: [String] { get }
func outputDescriptor(of outputName: String) -> InferenceValue.Descriptor?

var stateNames: [String] { get }
func stateDescriptor(of stateName: String) -> InferenceValue.Descriptor?
```

Overview: *"Use a descriptor to inspect the names and types of a function's inputs, outputs, and states before running inference. You obtain a descriptor from `functionDescriptor(for:)` or from the `descriptor` property."*

⚠️ **`stateNames` Discussion (verbatim):** *"States are function arguments that the function both reads and writes during inference. **You must provide a mutable view for every state** when calling `InferenceFunction/run(inputs:states:outputViews:)`."*

Note asymmetry: there is `inputCount` and `outputCount` but **no `stateCount`**.

---

## 6. `InferenceValue`

```swift
struct InferenceValue

var kind: InferenceValue.Kind { get }
var ndArray: NDArray? { get }
var pixelBuffer: CVMutablePixelBuffer? { get }
init(_ pixelBuffer: consuming CVMutablePixelBuffer)
```

Overview: *"An `InferenceValue` wraps either an `NDArray` or a pixel buffer, and you retrieve it after inference using the `ndArray` property."*

⚠️ **`ndArray` Discussion (verbatim):** *"This property is `nil` when the value contains an image instead of an array. **Accessing this property consumes the value and transfers ownership of the array to the caller.**"*
(So `value.ndArray` is a *consuming* read despite looking like a plain getter.)

`pixelBuffer` return: "The underlying pixel buffer or `nil` if this was not an image value."

### `InferenceValue.Descriptor`
```swift
enum Descriptor                 // Sendable, SendableMetatype
case image(ImageDescriptor)
case ndArray(NDArrayDescriptor)
```
Overview: *"You obtain descriptors from `InferenceFunctionDescriptor` to inspect what kind of value a function expects for each input or output."*

### `InferenceValue.Kind`
```swift
enum Kind
case image
case ndArray
```

### Views and protocols
```swift
struct InferenceValue.View               // "A borrowed, read-only view of an inference value."
                                         // Overview: "Use views to pass input values to Inputs without transferring ownership."
struct InferenceValue.MutableView        // "A borrowed, mutable view of an inference value."
struct InferenceValue.NamedMutableViews  // "A collection of named mutable views into inference values."
                                         // Overview: "Each view can only be taken once to ensure exclusive access."
mutating func take(_ valueName: String) -> InferenceValue.MutableView?
```
⚠️ **`take(_:)` Discussion:** *"Each value can only be taken once. **Requesting the same value again produces a fatal error.**"* (a *crash*, not `nil` — `nil` is only for "no value with that name")

```swift
protocol InferenceValue.ViewRepresentable
func view() -> InferenceValue.View

protocol InferenceValue.MutableViewRepresentable
mutating func mutableView() -> InferenceValue.MutableView
```
`NDArray` conforms to both.

---

## 7. `ImageDescriptor`

```swift
struct ImageDescriptor          // Equatable, Sendable, SendableMetatype
let pixelFormatType: OSType     // "The four-character code that identifies the pixel format."
let width: Int
let height: Int
```
`pixelFormatType` Discussion: *"Compare this value to the `pixelFormatType` of a `CVPixelBuffer`."*

---

## 8. `ComputeStream`

```swift
final class ComputeStream
convenience init()                                      // "Initialize an empty compute stream."
init(commandQueue: any MTLCommandQueue)                 // no watchOS
final func currentWorkCompleted() async
```

Overview (verbatim):
> "A compute stream is what is provided to `encode(inputs:states:outputViews:to:)` to encode the work onto the stream. **Multiple inferences encoded to the same stream are serialized as needed based on the the values read/written.**" *(sic — "the the")*

`init(commandQueue:)`: param *"The queue which inference will be encoded to when running `encode(inputs:states:outputViews:to:)`."*; Discussion: *"You can use this to encode inferences to your own metal queue."*

`currentWorkCompleted()`: "Waits for all previous work encoded to this stream to be complete." (`async`, non-throwing, no return.)

---

## 9. `NDArray`

```swift
struct NDArray
```
Conforms to: `Escapable`, `InferenceValue.MutableViewRepresentable`, `InferenceValue.ViewRepresentable`, `Sendable`, `SendableMetatype`.

> "A multidimensional array of scalar values used for model inference."
Overview: *"An `NDArray` stores data in a layout defined by its `shape`, `scalarType`, and `strides`."*

### Initializers
```swift
init(shape: [Int], scalarType: NDArray.ScalarType)
init(shape: [Int], scalarType: NDArray.ScalarType, strides: [Int])
init(shape: [Int], scalarType: NDArray.ScalarType, strides: [Int], interleaveLayout: NDArray.InterleaveLayout)
init<Scalar>(scalars: some Sequence, shape: [Int]) where Scalar : BitwiseCopyable
init(descriptor: consuming NDArrayDescriptor)
```

- `init(shape:scalarType:)` Discussion: *"This initializer creates an array with contiguous, row-major strides."*
- `init(shape:scalarType:strides:)` Discussion: *"The `shape` and `strides` arrays must have the same number of elements."*
- `init(scalars:shape:)` param docs: *"A sequence of scalars to be copied into the new ndArray. Note that `Scalar` must be a type that corresponds to a scalar type found on the `NDArray.ScalarType` enum."* / *"The shape of the new ndArray. The ndArray will be stored in row-major order and the scalars will be assigned in row-major order."*
  ```swift
  var ndArray = NDArray(scalars: (0..<4) as Range<Int32>, shape: [2, 2])
  // The resulting NDArray has contents:
  [[0, 1], [2, 3]]
  ```
- ⚠️ `init(descriptor:)` Discussion (verbatim, important):
  > "**The resulting array may not have a contiguous layout.** The strides match the values returned by the descriptor's preferred strides, so `contiguousElements` on a view of this array may return `nil`. In that case, use `withUnsafePointer` or `withUnsafeMutablePointer` to access the data while respecting the strides."
  > "If the descriptor has an `InterleaveLayout`, the resulting ndArray will carry that interleave metadata."
  > "**The descriptor's `hasDynamicShape` must be `false`.** If the descriptor has dynamic shapes, call `resolvingDynamicDimensions(_:)` first."

### Properties
```swift
var shape: [Int] { get }
var scalarType: NDArray.ScalarType { get }
var strides: [Int] { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }
```
`strides` Discussion: *"The strides array has the same number of elements as `shape`, where `strides[i]` describes the distance between consecutive elements in the `i`th dimension."*

### View accessors
```swift
func view<T>(as type: T.Type = T.self) -> NDArray.View<T> where T : BitwiseCopyable
mutating func mutableView<T>(as type: T.Type = T.self) -> NDArray.MutableView<T> where T : BitwiseCopyable
func rawView() -> NDArray.RawView
mutating func mutableRawView() -> NDArray.MutableRawView
```
⚠️ Note `as:` **has a default** (`= T.self`), which is why the integration article's example can write `prediction.view()` with no argument (`T` inferred from the call site). `mutableView`/`mutableRawView` are **`mutating`**; `view`/`rawView` are not.

Param doc for `view(as:)`: *"The Swift type that corresponds to this array's `scalarType`. For example, pass `Int32.self` for an array with scalar type `.int32`."*

---

## 10. `NDArray.View<Element>` / `MutableView<Element>` / `RawView` / `MutableRawView`

### `NDArray.View`
```swift
struct View<Element> where Element : BitwiseCopyable
init(span: Span<Element>, shape: [Int], strides: [Int])

var isContiguous: Bool { get }      // "Returns true if the elements in this view have a row-major contiguous layout."
var rank: Int { get }
var shape: Span<Int> { get }
var strides: Span<Int> { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }

var contiguousElements: Span<Element>? { get }
subscript<let rank : Int>(scalarAt index: InlineArray<rank, Int>) -> Element { get }

func withUnsafePointer<R, E>(_ body: (UnsafePointer<Element>, Span<Int>, Span<Int>) throws(E) -> R) throws(E) -> R where E : Error

@export(implementation) func slice(at ranges: [any NDArray.RangeExpression]) -> NDArray.View<Element>              // -32gsh
func slice<let indexRank : Int>(at: [indexRank of any NDArray.RangeExpression]) -> NDArray.View<Element>           // -4yomr

var rawView: NDArray.RawView { get }
```

Note the modern Swift features on display: `Span`/`MutableSpan`/`RawSpan`, **value generics** (`<let rank : Int>`), `InlineArray<rank, Int>`, fixed-count array parameter syntax `[indexRank of any NDArray.RangeExpression]`, typed throws `throws(E)`, `~Copyable`, `consuming`/`borrowing`.

- `contiguousElements` NOTE: *"`contiguous` here refers to elements in row-major order with zero padding."*
- `subscript(scalarAt:)` param: *"The multi-dimensional index of the element to access. It must have the same count as rank of this view."*; NOTE: *"`rank` must be equal to the `rank` of this view."*
- ⚠️ `withUnsafePointer(_:)` NOTE (verbatim): *"This function is intended for situations where you may not be working with contiguous layouts, and as such cannot use `contiguousElements`. **You are responsible for reading the `strides` passed in when indexing the backing data.** If the view has an `interleaveLayout`, the strides for that dimension are **block strides** and must be interpreted accordingly."*
- `slice(at:)` param: *"The range expressions describing where to slice along each dimension. `ranges.count` must be ≤ `rank`. **Unspecified trailing dimensions are assumed to be `.all`.**"*

Doc example (verbatim):
```swift
/// Returns the sum of the given row.
func sumOfRow(
  of view: borrowing NDArray.View<Float>,
  row: Int
) -> Float {
  let rowSlice = view.slice(at: [row])
  let elements = rowSlice.contiguousElements! // contiguous row expected in this case

  var sum: Float = 0
  for i in elements.indices {
    sum += elements[i]
  }
  return sum
}
```

### `NDArray.MutableView`
```swift
struct MutableView<Element> where Element : BitwiseCopyable
init(mutableSpan: consuming MutableSpan<Element>, shape: [Int], strides: [Int])

var isContiguous: Bool { get }
var rank: Int { get }
var shape: Span<Int> { get }
var strides: Span<Int> { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }

var contiguousElements: MutableSpan<Element>? { get }
subscript<let rank : Int>(scalarAt _: InlineArray<rank, Int>) -> Element { get }

@export(implementation) mutating func copyElements(from sequence: some Sequence<Element>)
mutating func copyElements(fromContentsOf: some Collection<Element>)

func withUnsafeMutablePointer<R, E>((UnsafeMutablePointer<Element>, Span<Int>, Span<Int>) throws(E) -> R) throws(E) -> R

func slice<let indexRank : Int>(at: [indexRank of any NDArray.RangeExpression]) -> NDArray.MutableView<Element>    // -50cpv
func slice(at: [any NDArray.RangeExpression]) -> NDArray.MutableView<Element>                                      // -qyjq
mutating func mutatingSlice<let indexRank : Int>(at: [indexRank of any NDArray.RangeExpression]) -> NDArray.MutableView<Element>  // -30asd
@export(implementation) mutating func mutatingSlice(at ranges: [any NDArray.RangeExpression]) -> NDArray.MutableView<Element>     // -9pmi4

var view: NDArray.View<Element> { get }
var mutableRawView: NDArray.MutableRawView { get }
```

⚠️ `slice` vs `mutatingSlice`: both exist on `MutableView`. `mutatingSlice` is `mutating` (borrows self mutably, yielding a writable sub-view); `slice` is not. Use `mutatingSlice` when you intend to write through the slice.

- `copyElements(from:)`: *"The number of elements in `sequence` must be less than or equal to `layout.scalarCount`."* (note: `layout.scalarCount` is referenced but `layout` is not a documented public property — likely an internal doc leak.)

Doc example for `mutatingSlice(at:)` (verbatim):
```swift
/// Updates the desired channel and range of rows
func incrementRegion(
  of mutableView: inout NDArray.MutableView<Float>,
  channel: Int,
  startRow: Int,
  endRow: Int
) {
  var region = mutableView.mutatingSlice(at: [channel, startRow..<endRow, .all])
  var mutableSpan = region.contiguousElements! // contiguous region expected in this case

  for i in mutableSpan.indices {
    mutableSpan[i] += 1
  }
}
```
(Shows heterogeneous range expressions in one array: `Int`, `Range<Int>`, `.all`.)

### `NDArray.RawView`
```swift
struct RawView                  // "A type-erased immutable view over the memory owned by a tensor."
init(bytes: RawSpan, byteOffset: Int, scalarType: NDArray.ScalarType, shape: [Int], strides: [Int], interleaveLayout: NDArray.InterleaveLayout?)
init(metalBuffer: borrowing any MTLBuffer, byteOffset: Int = 0, scalarType: NDArray.ScalarType, shape: [Int], strides: [Int] = [], interleaveLayout: NDArray.InterleaveLayout? = nil)   // no watchOS
init(ioSurface: borrowing IOSurface, byteOffset: Int, scalarType: NDArray.ScalarType, shape: [Int], strides: [Int], interleaveLayout: NDArray.InterleaveLayout?)

var scalarType: NDArray.ScalarType { get }
var shape: Span<Int> { get }
var strides: Span<Int> { get }
var bytes: RawSpan { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }

consuming func view<T>(as: T.Type = T.self) -> NDArray.View<T> where T : BitwiseCopyable
func slice<let indexRank : Int>(at: [indexRank of any NDArray.RangeExpression]) -> NDArray.RawView    // -1gght
func slice(at: [any NDArray.RangeExpression]) -> NDArray.RawView                                     // -kd5b
func withUnsafeBytes<R, E>((UnsafeRawPointer, Span<Int>, Span<Int>) throws(E) -> R) throws(E) -> R
```

⚠️ **`init(metalBuffer:...)` Discussion (verbatim — high-value gotchas):**
> "`metalBuffer` must have `shared` storage mode."
> "Note that the provided `scalarType` will be stored and later checked if you attempt to convert the raw view to a typed view."
> "Also note that the `shape/strides` must not be able to produce offsets that go outside of the range of `metalBuffer`."
> "**This initializer is unsafe, you are responsible for ensuring that no other code (or GPU pipeline) writes to the buffer while the resulting view is alive.**"
> - `strides`: "If left empty, they will be computed as contiguous row-major."

`view(as:)` is **`consuming`** ("Consume this raw view to create a typed view"); NOTE: *"`T` must match `self.scalarType.type`."*

### `NDArray.MutableRawView`
```swift
struct MutableRawView
init(mutableBytes: consuming MutableRawSpan, byteOffset: Int, scalarType: NDArray.ScalarType, shape: [Int], strides: [Int], interleaveLayout: NDArray.InterleaveLayout?)
init(metalBuffer: borrowing any MTLBuffer, byteOffset: Int, scalarType: ..., shape: [Int], strides: [Int], interleaveLayout: ...?)
init(ioSurface: borrowing IOSurface, byteOffset: Int, scalarType: ..., shape: [Int], strides: [Int], interleaveLayout: ...?)

var scalarType: NDArray.ScalarType { get }
var shape: Span<Int> { get }
var strides: Span<Int> { get }
var mutableBytes: MutableRawSpan { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }

func view<T>(as: T.Type) -> NDArray.MutableView<T>       // NOTE: returns a MutableView, despite being named `view(as:)`
var rawView: NDArray.RawView { get }
func slice<...>(at:) -> NDArray.MutableRawView           // -47fbq / -82sdj
func mutatingSlice<...>(at:) -> NDArray.MutableRawView   // -5tnq5 / -5ts4w
func withUnsafeMutableBytes<R, E>((UnsafeMutableRawPointer, Span<Int>, Span<Int>) throws(E) -> R) throws(E) -> R
```

**Three memory-backing sources across raw views:** raw span (`bytes`/`mutableBytes`), **`MTLBuffer`** (must be `shared` storage mode), and **`IOSurface`**.

---

## 11. `NDArray.ScalarType` — the full type zoo (33 cases)

```swift
enum ScalarType    // CaseIterable, Equatable, Hashable, Sendable, SendableMetatype
```

| Group | Cases | Doc |
|---|---|---|
| Floating-point | `float16`, `float32`, `float64`, `bfloat16` | 16/32/64-bit float; "A 16-bit brain floating-point type." |
| 8-bit float | `float8e4m3fn`, `float8e5m2` | "An 8-bit floating-point type with 4 exponent bits and 3 mantissa bits, **without a sign bit**." / "…5 exponent bits and 2 mantissa bits." |
| 4-/8-bit special | `float4e2m1fn`, `float8e8m0fn` | "A 4-bit floating-point type with 2 exponent bits and 1 mantissa bit." / "An 8-bit floating-point type with 8 exponent bits and 0 mantissa bits, without a sign bit." |
| Complex | `cfloat16`, `cfloat32`, `cfloat64` | "A 16/32/64-bit complex floating-point type." |
| Signed int | `int8`, `int16`, `int32`, `int64`, `int128` | |
| Unsigned int | `uint8`, `uint16`, `uint32`, `uint64`, `uint128` | |
| Sub-byte signed | `int2`, `int3`, `int4`, `int5`, `int6`, `int7` | `int4`: "Four-bit signed integers can represent values in the range **[-8, 7]**. Widely used in model quantization for efficient storage and computation." |
| Sub-byte unsigned | `uint1`, `uint2`, `uint3`, `uint4`, `uint5`, `uint6`, `uint7` | |
| Boolean | `bool` | "A Boolean scalar." |

Notable: **`float8e8m0fn`** and **`float4e2m1fn`** are the MX (microscaling) block-format scale/element types — strong signal that Core AI supports MXFP4-class quantization natively. Sub-byte integers go all the way down to **`uint1`**, and odd widths (`int3`, `int5`, `int6`, `int7`, `uint3`, `uint5`, `uint6`, `uint7`) are present, which is unusual and points at fine-grained palettization/quantization schemes. There is **no `int1`** (only `uint1`) and **no `uint0`**.

Also note there is **no `Float8`/`Int4` Swift standard type**, so `view(as:)` for sub-byte types is unclear (see Open Questions).

---

## 12. `NDArray.InterleaveLayout` — the most detailed doc page in the framework

```swift
struct InterleaveLayout          // Equatable, Sendable, SendableMetatype
init(dimension: Int, factor: Int)
var dimension: Int { get }       // "The index of the interleaved dimension."
var factor: Int { get }          // "The number of elements from the interleaved dimension stored contiguously per block.
                                 //  Adjacent elements within a block have stride 1 in memory."
```

### Overview (verbatim)
> "An interleaved layout means that elements of the interleaved `dimension` are stored in physically contiguous blocks of `factor` elements (stride 1 between adjacent elements within a block). This differs from the standard layout where a dimension's elements are separated by the strides of subsequent dimensions."
> "A common use case is representing an image with interleaved channels: a `[C, H, W]` tensor uses `InterleaveLayout(dimension: 0, factor: C)` to store all channels for each pixel contiguously — like `RGBRGB...` — rather than in separate planar slices — like `RRR...GGG...BBB...`. More generally, this can be useful for optimizing the layout of an ndArray based on how the later compute will access it."

### Stride semantics (verbatim section)
> "The stride for the interleaved dimension (as reported by `NDArray.strides`) is a *block stride* — the distance in memory between adjacent blocks of `factor` elements, not between individual elements. Within a block, adjacent elements have stride 1. The element offset formula is:"

```swift
// Given strides and InterleaveLayout with dimension d and factor f:
// offset = (index[d] / f) * strides[d] + (index[d] % f)
//        + Σ index[i] * strides[i]  for all i ≠ d
```

### Equivalence with shape/stride transformations (verbatim section)
> "When `factor` divides the size of the interleaved dimension evenly, the layout can equivalently be expressed as a shape/stride transformation without interleave metadata. For example, for `shape=[8, 256, 256]` with `InterleaveLayout(dimension: 0, factor: 4)`:"

```swift
// Interleaved representation:
shape=[8, 256, 256], strides=[262144, 1024, 4]
interleaveLayout=InterleaveLayout(dimension: 0, factor: 4)

// Equivalent shape/stride form (no interleave needed):
shape=[2, 256, 256, 4], strides=[262144, 1024, 4, 1]
interleaveLayout=nil
```

> "The interleaved form preserves the original logical shape; the equivalent form makes the blocking explicit as an extra dimension."
> "**When `factor` does not divide the dimension size evenly, the shape/stride equivalence is not possible. In such case the interleaved representation is the only way to express the layout.**"

---

## 13. `NDArray.RangeExpression`

```swift
protocol RangeExpression : Sendable
static var all: _AllRange { get }         // "A range expression that selects the entire dimension."
func relative(to dimension: Range<Int>) -> Range<Int>
```
`relative(to:)` Discussion: *"For example, when the range expression specifies `1...` on the axis with dimension 3, the resultant Range is `1 ..< 3`."*
Return: "The range of the selected dimension."

Note `_AllRange` is an underscored (unofficial/internal-ish) type exposed in the public signature.

---

## 14. `NDArrayDescriptor`

```swift
struct NDArrayDescriptor        // Equatable, Sendable, SendableMetatype

var shape: [Int] { get }
var scalarType: NDArray.ScalarType { get }
var rank: Int { get }
var hasDynamicShape: Bool { get }
var interleaveLayout: NDArray.InterleaveLayout? { get }

var minimumByteCount: Int { get }
var preferredStrides: [Int] { get }

func resolvingDynamicDimensions(_ newShape: [Int]) -> NDArrayDescriptor
```

Overview (verbatim):
> "You obtain an `NDArrayDescriptor` from an `InferenceFunctionDescriptor` by querying the descriptor of a specific input or output:"
```swift
let valueDescriptor = functionDescriptor.inputDescriptor(of: "x")!
guard case .ndArray(let ndArrayDescriptor) = valueDescriptor else { ... }
```
> "The descriptor contains the expectations for an array value that you provide to an `InferenceFunction`. **Most expectations are strict**: for example, if the descriptor specifies `scalarType` as `.float32`, the array you provide must use `.float32`."

`shape` Discussion: *"The shape contains `rank` elements. **A value of `-1` in any dimension indicates a dynamic size.**"*

### `preferredStrides` — Discussion (verbatim, PERFORMANCE-CRITICAL)
> "During the specialization of an `AIModel`, a preferred memory layout for a given ndArray value may be set depending on structure of the model and which compute units it is specialized for. In some cases, this can result in a **non-contiguous layout being preferred/required by the backing compute**. In such case, you are still able to provide `InferenceFunction.run` normal contiguous ndArray values, however **it may incur a copy to the preferred layout**. As such, this property provides an opportunity for you to optimize performance by creating your source ndArray value with the preferred striding and avoiding that copy."

> **NOTE:** "Constructing an ndArray with these preferred strides may result in a non-contiguous layout. In such case calling `ndArrayView.contiguousElements` on a view of the ndArray will return `nil`. If you choose to use the preferred strides, you must read/write the resulting ndArray by dynamically respecting whatever strides are returned:"

```swift
guard case .ndArray(let inputDescriptor) = inferenceFunctionDescriptor.inputDescriptor(of: "input") else {
  throw UnexpectedInferenceValueType()
}
let preferredStrides = inputDescriptor.preferredStrides
var ndArray = NDArray(shape: [theShape], scalarType: .float32, strides: preferredStrides)
var view = ndArray.mutableView(as: Float.self)
if let contiguousElements = view.contiguousElements {
  // The preferred strides were a normal contiguous layout
} else {
  // The preferred strides were non-contiguous
  view.withUnsafeMutablePointer { data, shape, strides in
    ... logic which respects whatever strides were preferred ...
  }
}
```

> **NOTE:** "Accessing this property on a descriptor for which `hasDynamicShape` is true, is a **programming error**. If the descriptor has a dynamic shape, you must first call `resolvingDynamicDimensions` to provide a concrete size for each dimension."

### `minimumByteCount` — Discussion (verbatim) + manual-allocation example
> "The shape/strides/scalarType of this descriptor are used to compute the addressable byte range of the layout, and the size of that range is returned as the minimum size a backing storage would need to be to contain the ndArray."
> "In most cases it is preferred to make `NDArray` instances which handle creating the allocations for you, but in circumstances where you need to manually handle your allocations, this property can be useful to help you find how large of a storage to allocate."

```swift
let metalDevice: any MTLDevice = ...
let functionDescriptor = model.functionDescriptor(for: "main")
guard case .ndArray(let ndArrayDescriptor) = functionDescriptor.inputDescriptor(of: "dynamic_shape_input") else {
  // Handle input not found or not ndArray
}

// Assuming that the descriptor is known to have static shapes. If it had dynamic shapes it'd be
// required to first call `resolvingDynamicDimensions`.
let byteCount = ndArrayDescriptor.minimumByteCount
let metalBuffer = metalDevice.makeBuffer(length: byteCount)!

// Later at inference time... manual allocations can be provided by making views from them.
let view = NDArray.RawView(
  metalBuffer: metalBuffer,
  byteOffset: 0,
  shape: ndArrayDescriptor.shape,
  scalarType: ndArrayDescriptor.scalarType,
  strides: ndArrayDescriptor.preferredStrides
)
var inputs = InferenceFunction.Inputs()
inputs.insert(view, for: "myInput")
var outputs = inferenceFunction.run(inputs: inputs)
```
⚠️ This official sample has bugs: `RawView.init` argument order is declared `(metalBuffer:byteOffset:scalarType:shape:strides:interleaveLayout:)` but the sample passes `shape:` before `scalarType:`; and `run(inputs:)` is `async throws` so the last line needs `try await`. Treat as illustrative pseudo-code.

> "`hasDynamicShape` must be false when accessing this property, as the size is unknown if there are dynamic shapes."

### `resolvingDynamicDimensions(_:)` — Discussion (verbatim)
> "If the original model contained ndArray arguments with dynamic shapes, then the `NDArrayDescriptor` returned for that argument from the `InferenceFunctionDescriptor` will contain the value `-1` in the dimensions with dynamic sizes."
> "This method allows you to provide a resolved shape and obtain a new descriptor with that adjusted shape."

```swift
let functionDescriptor = model.functionDescriptor(for: "main")
guard case .ndArray(let ndArrayDescriptor) = functionDescriptor.inputDescriptor(of: "dynamic_shape_input") else {
  // Handle input not found or not ndArray
}

// The 'dynamic_shape_input' argument is a rank 3 ndArray with a dynamic shape for the final dimension.
// ndArrayDescriptor.shape == [128, 128, -1]

// Make a resolved descriptor which fills in the -1 dimension with the concrete value 10
let resolvedDescriptor = ndArrayDescriptor.resolvingDynamicDimensions([128, 128, 10])
```

> **NOTE:** "`newShape` must be the same size as the `shape` of the descriptor it is called on. Also for each dimension, it must hold true that the provided new shape either matches the existing shape, or the existing shape is `-1`."

---

## 15. `AIModelCache`

```swift
final class AIModelCache         // Sendable, SendableMetatype

static let `default`: AIModelCache
init?(appGroup groupIdentifier: String)

final func model(for modelURL: URL, options: SpecializationOptions) throws -> AIModel?

final func deleteEntry(for modelURL: URL, options: SpecializationOptions) throws
final func deleteEntries(for modelURL: URL) throws
final func deleteAll() throws
static func deleteEntry(referencedBy bookmark: Data) throws
```

Overview: *"The cache holds the optimized, device-specific artifacts that `AIModel` loads to execute its inference functions. **Each cache entry contains a specialized asset formed from a specific `.aimodel` or `.aimodelc` and `SpecializationOptions` combination.**"*

- `default` Discussion: *"The shared specialized asset cache for your app bundle. The framework uses this cache by default whenever specialization happens automatically, such as during `init(contentsOf:options:)`."*
- `init(appGroup:)`:
  - param: *"A string that names the group whose shared cache you want to obtain. **This input should exactly match one of the strings in the app's App Groups Entitlement.**"*
  - return: *"The shared app group cache, or `nil` when the group identifier is invalid (**on iOS**), the app group container cannot be accessed, or entitlement checks fail."*
  - Discussion: *"Use this initializer when multiple apps within an app group need to share a cache for their specialized assets. This allows all apps within an app group to avoid each performing their own specialization for a shared model."*
  - Entitlement: `com.apple.security.application-groups`
- `model(for:options:)` Discussion: *"If this cache holds a specialized asset from previously specializing the model at `modelURL` with the specified `options`, this method loads and returns the model. **This method never performs specialization.**"* NOTE: *"If a cache entry was found but the specialized asset failed to load."* (again a truncated Throws clause)
- `deleteEntries(for:)` Discussion: *"A model may have multiple entries in the cache. For example, one with `cpuOnly` and another with `default`. This method deletes all of them."*
- ⚠️ **Deletion NOTE, repeated on all four delete APIs (verbatim):** *"For each entry, if no `AIModel` instance currently references it, deletion happens immediately. **Otherwise, an error is thrown.** Deletion can only occur for an entry when the last `AIModel` releases it."*
  (The prose article says it more softly: *"If an `AIModel` instance still uses a cache entry, Core AI defers deletion until that instance is deallocated."* — the reference doc says it **throws**. Contradiction worth flagging.)
- `deleteAll()` Discussion: *"Use this method to reclaim storage when the app no longer needs any of its specialized models, or to reset the cache during testing."*
- `deleteEntry(referencedBy:)` Discussion: *"Because bookmark data encodes both the specific cache instance and the entry within it, **this method is static and requires no cache instance to call**."*

### `AIModelCache.Policy`
```swift
struct Policy       // Decodable, Encodable, Equatable, Hashable, Sendable, SendableMetatype
static let `default`: AIModelCache.Policy
static let persistent: AIModelCache.Policy
init(purgeConditions: AIModelCache.Policy.PurgeConditions)
var purgeConditions: AIModelCache.Policy.PurgeConditions { get }
```
Overview: *"Defines the conditions under which the system may purge specialized assets in an `AIModelCache`."*
> ⚠️ **NOTE:** "**Regardless of policy, the system always purges assets when the OS updates**, as specialized assets are OS-version specific."

- `default` Discussion: *"The default policy marks a specialized asset as purgeable. The system can delete it when low on storage or when its source `.aimodel` changes or you delete it."*
- `persistent` Discussion: *"This policy ensures the system does not purge specialized assets **until the next OS update**. You can manually delete them, but the system does not automatically purge them under low storage or when the source `.aimodel` changes."*

### `AIModelCache.Policy.PurgeConditions`
```swift
struct PurgeConditions   // OptionSet, SetAlgebra, RawRepresentable, ExpressibleByArrayLiteral,
                         // Codable, Equatable, Hashable, Sendable, SendableMetatype
static let sourceAssetChangedOrDeleted: AIModelCache.Policy.PurgeConditions
static let storagePressure: AIModelCache.Policy.PurgeConditions
```
- `sourceAssetChangedOrDeleted`: *"This option allows the system to delete a specialized asset when the `.aimodel` the asset derives from changes or no longer exists."*
- `storagePressure`: *"This option allows the system to delete a specialized asset when the device runs low on storage and needs to reclaim space."*
- Overview NOTE: *"The system always purges assets on OS update regardless of these conditions."*

Inference: `.default == Policy(purgeConditions: [.sourceAssetChangedOrDeleted, .storagePressure])` and `.persistent == Policy(purgeConditions: [])`. (UNVERIFIED — the raw values aren't documented, but the prose descriptions imply exactly this.)

---

## 16. `SpecializationOptions`

```swift
struct SpecializationOptions     // Equatable, Hashable, Sendable, SendableMetatype

static let `default`: SpecializationOptions
static let cpuOnly: SpecializationOptions
init(preferredComputeUnitKind: ComputeUnitKind)

var allowedComputeUnitKinds: Set<ComputeUnitKind> { get }
var preferredComputeUnitKind: ComputeUnitKind? { get }
var expectFrequentReshapes: Bool               // { get set } — the only non-get-only property
```

- `default` Discussion: *"The specialization process selects the combination of compute units that minimizes inference latency."*
- `cpuOnly` Discussion: *"The resulting specialized model only uses the CPU during inference. **Because all operations support the CPU, no fallback to other compute units occurs.**"*
- `init(preferredComputeUnitKind:)` Discussion: *"The specialization process maximizes use of the specified compute unit kind, falling back to other allowed compute units for incompatible operations."*
- `allowedComputeUnitKinds` Discussion: *"The model may use all or any subset of the kinds in this set during inference."*
- ⚠️ `preferredComputeUnitKind` Discussion (verbatim, valuable): *"When set, the specialization process maximizes use of this compute unit kind. **Fallback to other kinds in `allowedComputeUnitKinds` may still occur for operations or operation patterns that are incompatible with the preferred kind. Operation patterns refer to groups of operations that are fused or transformed together during specialization; an operation that is individually compatible with the preferred unit kind may be part of a fused pattern that is not.**"*
- `expectFrequentReshapes` — abstract only: *"Setting to allow more optimal specialization if the model performs frequent reshapes based on usage"*. **No Discussion section exists.** ⚠️ Undocumented default value; there is no documented initializer that sets it, so it must be set via `var` mutation after constructing options.

⚠️ **Important:** `SpecializationOptions` is `Hashable` and is part of the **cache key** — different options ⇒ different cache entry ⇒ separate specialization cost and storage.

---

## 17. `ComputeUnitKind`

```swift
enum ComputeUnitKind     // Equatable, Hashable, Sendable, SendableMetatype
case cpu                 // "The central processing unit."
case gpu                 // "The graphics processing unit."
case neuralEngine        // "The Neural Engine."
static var availableKinds: Set<ComputeUnitKind> { get }   // "The compute unit kinds available on the current device."
```
Overview: *"You use compute unit kinds with `SpecializationOptions` to control which hardware the framework targets when specializing a model. **By default, specialization uses all available compute units on the device.**"*

---

## 18. `AssetError`

```swift
struct AssetError        // Error, LocalizedError, Sendable, SendableMetatype
var kind: AssetError.Kind { get }
var debugMessage: String? { get }
var errorDescription: String? { get }
init(kind: AssetError.Kind, debugMessage: String?)

enum Kind                // Sendable, SendableMetatype
case corruptedMetadata            // "An error that indicates the asset metadata is corrupted."
case duplicateName                // "An error that indicates a component with that name already exists in the asset."
case invalidFeatureType(String)   // "An error that indicates the feature type is invalid."
case invalidName                  // "An error that indicates the component name is invalid."
case unsupportedVersion(String)   // "An error that indicates the asset version is unsupported."
```
`unsupportedVersion(_:)` Discussion: *"This typically means a more recent version of this library generated the asset, and you may need to upgrade."*

⚠️ `AssetError` is `public init`-able by app code — it is not a sealed system error. Note that `AssetError` covers **asset** operations only; the errors thrown by `AIModel.init`, `loadFunction`, `run`, and cache deletion are **not documented anywhere** (see Open Questions).

---

## 19. Article: *Integrating on-device AI models in your app with Core AI*

`/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai`

### Why on-device (verbatim)
> "Core AI allows you to deploy AI models within your app. Inference happens on device, so data stays private, AI features can be readily available and work offline, and **there is no per-inference cost** to you or the people using your app."

> "You start with an `.aimodel` file, either converted from a model using the `coreai-torch` or already prepared in the correct format. The model it represents should contain one or more inference functions needed to power your app's intelligent features."

### Adding the model to a target
1. "Drag the `.aimodel` file from the Finder into the Project Navigator in Xcode, or choose File > Add Files to add it."
2. "When the sheet appears, select the targets to include the model under Add to targets, then review the remaining options."
3. "Click Finish."

> **NOTE:** "After adding the file, you should also see the model in the **Compile Sources** build phase for that target."

Model distribution options: *"You can bundle the file directly in your Xcode project or Swift package, or your app can download it over the network."*

### ⚠️⚠️ Metal Toolchain requirement (BIG FOOTGUN)
> "Core AI model integration in Xcode requires the **Metal Toolchain, which isn't installed by default**. There are two options for adding the Metal Toolchain:
> - In Xcode, choose **Xcode > Settings > Components > Other Components**, then click **Get** to download and install the Metal Toolchain.
> - In Xcode, select any `.aimodel` file in your project and click the **Get** button in the Metal toolchain download bar that appears."

> **IMPORTANT:** "**If the Metal toolchain isn't included, builds that include `.aimodel` files fail with a missing Metal compiler error.**"

CLI alternative (from the AOT article):
```shell
% xcodebuild -downloadComponent MetalToolchain
```

### Xcode model viewer
> "The model viewer has several tabs for exploring different aspects of your model. The **General** tab shows the model's size, in number of parameters and storage size on disk, along with metadata such as description, author, license, and creator-defined key-value pairs. **You can edit metadata fields inline; Xcode saves your changes automatically.**"

> "The General tab also shows the model's numeric precision, split into compute and storage categories:
> - **Compute types** are the representations used during inference.
> - **Storage types** are the representations used for the model's weights on disk.
> - The **operation distribution** shows a breakdown of operations in the model's graph, sorted by count."

(These map 1:1 onto `AIModelAsset.Summary.computeTypes` / `.storageTypes` / `.operationDistribution`.)

### Functions tab
> "The **Functions** tab shows the exact function signature of each function in the model, including the names, types, and optional descriptions for each input and output."
> "Most models have a single function. The named inputs and outputs describe what data your code provides and what it returns. **A question mark in an `NDArray` dimension means the dimension is dynamic and is supplied or determined at runtime.**"

(So the viewer shows `?`; the API shows `-1`.)

### Loading the model (verbatim code)
```swift
import CoreAI

// Specialize the model for this device and load it.
let model = try await AIModel(contentsOf: urlOfModel)

// Load a function from the model.
guard let function = try model.loadFunction(named: "main") else {
    // Handle case where expected function is not found.
}
```

> "Core AI specializes the model for the current device, considering all available compute units and selecting the combination that delivers the best performance. `init(contentsOf:options:)` is asynchronous **because specialization needs to complete before a valid `AIModel` is returned**. Depending on the model size, specialization can take a significant amount of time."

> "Call `loadFunction(named:)` to get an `InferenceFunction` for running the model with your inputs and receiving its outputs. **Loading a function prepares the resources needed to run that function and can also be expensive.** The method throws on a load failure, and returns `nil` when no function with that name exists."

> "Most models have a single function. If the model contains multiple functions, check `functionNames` to see all available names. **If your app processes multiple inputs simultaneously, you can safely call the same inference function from different tasks.**"

Module import name: **`import CoreAI`** (framework identifier `CoreAI`; URL slug `coreai`).
Default function name: **`"main"`**.

### Inspecting function inputs/outputs (verbatim code)
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

Use case (verbatim): *"You can use this descriptor to verify that a function accepts the inputs your app provides, or to **dynamically adapt your app's behavior as the model's inputs and outputs change between deployments, without needing to change your code**."*

### Running inference (verbatim code, four snippets)
> "The `NDArray` type represents the input and output tensors from the converted model function at runtime. **Values marked as images at conversion time use `CVMutablePixelBuffer`.** Pass your data using the same input names defined at model conversion time."
> "For `NDArray` values, write input data with `MutableView` and read results with `View`. **Swift enforces this at compile time.** A mutable view allows writes, and a view allows only reads, so you always know how your data is accessed."

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

> "After the model runs, call `remove(_:)` with the output name to extract each result. The result is an `InferenceValue` which holds either an `NDArray` or an image. To check which type your output uses, look at the function signature in the model viewer's Functions tab, or inspect the `InferenceFunctionDescriptor` at runtime. Access the output with `.ndArray` or `.pixelBuffer` based on the type."

Note the last snippet calls `prediction.view()` with **no `as:` argument** — valid because `view<T>(as type: T.Type = T.self)` defaults, with `T` inferred from `processOutput`'s parameter type.

---

## 20. Article: *Managing model specialization and caching*

`/documentation/coreai/managing-model-specialization-and-caching`

### What specialization is (verbatim)
> "When you load a `.aimodel` file with `AIModel`, Core AI performs **specialization**, the process of optimizing the model for the current device's hardware. The `.aimodel` file contains your model in a **portable format that works across Apple devices**. Before the model can run, Core AI specializes it for the current device, producing **executable code tied to that device's hardware and OS version**."
> "By default, an `AIModel` automatically specializes the model and caches the result. On the first call, Core AI specializes the model and stores the output. On subsequent calls with the same model and options, Core AI loads the cached version rather than running the specialization process again, which reduces load times."

### Check for a cached specialization (verbatim code)
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

### Choosing compute units (verbatim)
> "For advanced use cases, restrict specialization to CPU only with `.cpuOnly`, or prefer a specific compute unit with `init(preferredComputeUnitKind:)`. **For example, if your app runs a small model in the background, use `.cpuOnly` to avoid competing with foreground GPU work.**"
> "**In most scenarios, the default configuration offers the best performance, so test your app's performance carefully before overriding it.** Because not all devices have the same compute units available, check what's available with `availableKinds`."

### Pre-specialize (verbatim code)
```swift
guard let localModelURL = try await downloadModel(forFeature: feature) else {
    throw AppError.failedToDownloadModel(feature)
}

// Specialize the model so it's ready before the person needs it.
try await AIModel.specialize(contentsOf: localModelURL, options: .default)

// The model is now specialized and cached. Future loads skip specialization.
let model = try await AIModel(contentsOf: localModelURL, options: .default)
```
> **NOTE:** "Calling `specialize` multiple times with the same model URL and options returns the cached result without repeating the specialization process."

⚠️ **`specialize` vs AOT compilation (verbatim, important distinction):**
> "The `specialize` method **differs from ahead-of-time compilation**. With ahead-of-time compilation, most of the heavy computation happens on your Mac at build time, so on-device specialization finishes faster. With `specialize`, **the full specialization process runs on the person's device. You are controlling *when* specialization happens, not *reducing the work it does*.**"

### Three purge conditions (verbatim termList)
> - **OS update** — "Specialized assets are tied to the OS version. **The system always invalidates assets on OS update, regardless of policy.**"
> - **Source model change** — "If the source `.aimodel` file is modified or deleted, cached assets derived from it become invalid."
> - **Storage pressure** — "The system can reclaim space by deleting assets marked as purgeable."

> "If your app deletes the source model file to save storage, use the `.persistent` policy to keep the cached assets available across launches:"
```swift
try await AIModel.specialize(
    contentsOf: modelURL,
    options: .default,
    cachePolicy: .persistent
)
```

### Delete cached assets (verbatim code)
```swift
func downloadAndUpdateModel(from remoteURL: URL, localModelURL: URL) async throws {
    let tempURL = try await downloadLatestModel(from: remoteURL)

    // Delete cached assets for the old model.
    let cache = AIModelCache.default
    try cache.deleteEntries(for: localModelURL)

    // Replace the old model with the new one.
    try FileManager.default.replaceItemAt(localModelURL, withItemAt: tempURL)

    // Specialize the updated model.
    try await AIModel.specialize(
        contentsOf: localModelURL,
        options: .default,
        cachePolicy: .persistent
    )
}
```
Deletion API summary (verbatim termList):
> - `deleteEntries(for:)` — "Ignores any `SpecializationOptions` and deletes all cache entries for a specific `.aimodel`."
> - `deleteEntry(for:options:)` — "Deletes a single cache entry for a specific `.aimodel` and `SpecializationOptions` combination."
> - `deleteAll()` — "Deletes all entries in the entire cache."
> "If an `AIModel` instance still uses a cache entry, Core AI defers deletion until that instance is deallocated."

### App group sharing (verbatim code)
```swift
// Get the app group cache.
guard let groupCache = AIModelCache(appGroup: groupIdentifier) else {
    fatalError("Invalid group identifier or entitlement.")
    return
}

// Specialize into the shared cache.
try await AIModel.specialize(
    contentsOf: sharedModelURL,
    options: .default,
    cache: groupCache,
    cachePolicy: .persistent
)
```
```swift
guard let groupCache = AIModelCache(appGroup: groupIdentifier) else {
    return
}

if let model = try groupCache.model(for: sharedModelURL, options: .default) {
    // Use the model. No specialization needed.
}
```
Entitlement: `com.apple.security.application-groups`.
> "This avoids duplicating specializations across apps."

### ⚠️ Delete-the-source-model + bookmark workflow (verbatim, key section)
> "The unspecialized `.aimodel` file, **along with the `SpecializationOptions` you pass**, is what Core AI uses to index and retrieve the cached specialization at runtime when you call `init(contentsOf:options:)` or `model(for:options:)`. Because of this, **you can't simply delete the source file and expect those APIs to keep working.** Instead, save a bookmark to the cached specialization and load the model directly from that bookmark on later launches."

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

// Download and specialize the model again.
```
```swift
// Delete the source model to reclaim storage.
try FileManager.default.removeItem(at: llmURL)
```
> "Bookmark data doesn't prevent removing assets from the device. **If the system purges the assets, you manually delete them, or an OS update invalidates them, your app can't resolve the bookmark and needs to download and specialize the model again.**"

(The variable name `llmURL` here is a strong hint that this workflow is aimed squarely at large downloaded LLMs.)

---

## 21. Article: *Compiling Core AI models ahead of time* — the `coreai-build` CLI

`/documentation/coreai/compiling-core-ai-models-ahead-of-time`

### What AOT does (verbatim)
> "Core AI can help reduce on-device specialization time with ahead-of-time compilation through the **`coreai-build`** command-line tool. The tool **moves the most expensive part of specialization, model compilation, to your build machine**, so on-device specialization has less work to do, and your model loads faster when your app runs it."
> "Ahead-of-time compilation converts your `.aimodel` model file into `.aimodelc` assets, **one for each device architecture**. At runtime, your app picks the asset that matches the current device's architecture, and Core AI generates the executable code on device without repeating the compilation step."

### ⚠️⚠️ HARDWARE GATE (verbatim NOTE — the biggest gotcha in the framework)
> **NOTE:** "Ahead-of-time compilation only compiles for devices that support Apple Intelligence, including **iPhone or iPad with the A17 Pro chipset or later, a Mac with the M1 chipset or later, or Apple Vision Pro with the M2 chipset or later**."

### Installing the toolchain
In Xcode:
1. "Choose Xcode > Settings."
2. "Choose Components, and under Other Components, click Get next to Metal Toolchain."

From the command line:
```shell
% xcodebuild -downloadComponent MetalToolchain
```

### The command (verbatim)
```shell
% xcrun coreai-build compile MyModel.aimodel --platform iOS --min-deployment-version 27.0 --output compiled/
```

**Documented flags/subcommands (from Apple's docs):**
| Token | Meaning |
|---|---|
| `coreai-build compile` | the subcommand |
| `<input>.aimodel` | positional input |
| `--platform iOS` | target platform |
| `--min-deployment-version 27.0` | minimum OS version the artifacts must run on |
| `--output compiled/` | output directory |
| `--preferred-compute` | "By default, Core AI selects the compute units that deliver the best performance for the model and platform. To override, pass `--preferred-compute`." |
| `coreai-build compile --help` | "For the available values, the minimum deployment version, the target architecture, and other options, run `coreai-build compile --help`." |

⚠️ Apple's docs explicitly say a `--help` run reveals **"the target architecture, and other options"** — so there is at least an architecture-selection flag Apple does not name in prose. Third-party sources (NOT Apple, treat as UNVERIFIED) report `--architecture h18p` (iPhone 17 Pro) and `--preferred-compute neural-engine`.

### Output naming (verbatim)
> "`coreai-build` outputs one compiled `.aimodelc` file per device architecture, using the input model's filename as the prefix. For example, compiling `MyModel.aimodel` produces files named **`MyModel.<arch>.aimodelc`**, where `<arch>` is the device architecture identifier returned by `deviceArchitectureName` at runtime. **Each compiled `.aimodelc` works on any OS version at or above the minimum deployment version you pass to `coreai-build`.**"

### Loading on device (verbatim)
> "It's recommended to **host the compiled assets remotely and download the matching variant to the device at runtime**, because each device only uses one of them. The **`BackgroundAssets`** framework can manage downloads, installs, and updates for your hosted model files."

```swift
let arch = AIModel.deviceArchitectureName
let assetName = "MyModel.\(arch).aimodelc"
```

> "To load the downloaded `.aimodelc` asset, use `init(contentsOf:options:)`. **This is the same API you use to load `.aimodel` files, so you don't need to change your loading code when you adopt ahead-of-time compilation.** Use the default options, or specify options that match the compute units you used at compile time."

⚠️ **AOT is not a full escape from specialization (verbatim):**
> "**Even with ahead-of-time compilation, the compiled asset still requires some specialization on the device.** The amount of compilation that remains depends on the model and the compute units it uses."

---

## 22. Collection: *Inspecting, debugging, and profiling Core AI models*

`/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models`
(This was flagged as missing from the local corpus — captured in full below.)

### Overview (verbatim)
> "Core AI provides **three tools** to help you investigate model behavior, monitor activity, and profile performance. Use them as needed while authoring a model, after integrating it, or when your app is running.
> - **Core AI Debugger**: A standalone macOS app for inspecting model structure, running models, and validating inference against reference data.
> - **Core AI debug gauge**: An Xcode feature that monitors model load, specialization, and inference activity in real time during a debug session.
> - **Core AI instrument**: An Instruments template that profiles execution timing across the CPU, GPU, and Neural Engine."

> "The Core AI debug gauge and Core AI instrument focus on a model that's **already running inside your app**. Core AI Debugger works **directly with the `.aimodel` file** and gives you a closer look when something the gauge or instrument flags needs deeper inspection. **The tools share data, so a finding in one often leads to a closer look in another.**"

Workflow diagram alt-text (verbatim — describes the whole tool topology):
> "A two-phase workflow diagram. In the **Development** phase, authoring and optimization sends reference data to Core AI Debugger and saves an .aimodel file. The .aimodel file provides numeric debug data to Core AI Debugger and integrates into an app in the **Runtime** phase. The app runs into the Core AI debug gauge, which captures data back to Core AI Debugger and captures a trace into the Core AI instrument. The app also profiles directly into the Core AI instrument."

Per-tool summaries:
> "Core AI Debugger is a standalone macOS app that you download… for working directly with `.aimodel` files. You can inspect a model's operation graph, step through the source that produced each operation, and run the model against a connected device or your Mac. The debugger also allows you to compare pairs of a model's output against a reference run…"
> "Built into Xcode, the Core AI debug gauge tracks each model load, specialization, and inference event in real time… The Core AI debug gauge can hand a captured event off to Core AI Debugger for structural inspection, or to the Core AI instrument for deeper profiling."
> "The Core AI instrument is a template in Instruments that profiles your app's Core AI activity with detailed timing across the CPU, GPU, and Neural Engine. Use it when you need detailed performance information, such as **which compute units run your model, whether specialization happens when you expect, and how often your app reloads a model**. The trace correlates Core AI events with hardware activity…"

---

## 23. Article: *Monitoring model performance with the debug gauge*

`/documentation/coreai/monitoring-model-performance-with-the-debug-gauge`

### ⚠️ Gauge requires a **direct** link to CoreAI.framework
> **NOTE:** "**The gauge only appears in projects that link the Core AI framework. The gauge does not support the Core ML framework.**"

> "If you don't see the gauge, verify that your project **directly links** the Core AI framework. To check, go to your project settings in the Xcode Navigator and scroll to **Frameworks, Libraries, and Embedded Content** in the **General** section. If you don't see the Core AI framework, add it, then build and run your project again."
(Screenshot alt-text confirms: "CoreAI.framework set to **Always Used**.")

### Where it lives
> "With your Xcode project open, build and run the project. In **Debug navigator**, you'll see gauges such as CPU, Memory, Energy Impact, and the **Core AI** gauge."
Alt-text notes the row shows "**0 µs/event**" before any inference runs, and later "**10 ms per event**".

### Tray graph semantics (verbatim)
> "Vertical bars appear in the graph, where **each bar represents the combined Core AI events that occur within a one-second interval**. The horizontal axis shows time and the vertical axis shows the total duration of each combined event. Next to the bars, a label summarizes the **median** duration across all events combined."

### The three event types (verbatim, with colors)
> "At the top, three separate metrics show the **median** duration for each event type:
> - **Inference**: A single, complete inference from the model. **Primary event type.** Appears in **blue** in both the metrics and graph.
> - **Load**: Preparation of the model for loading into memory. Appears in **green** in both the metrics and graph.
> - **Specialization**: Runtime specialization of the model for the target device architecture. **This only appears for models that aren't specialized ahead of time.** Appears in **orange** in both the metrics and graph."

⚠️ **Color inconsistency vs the Instruments article:** in the gauge, Load = green and Specialization = orange; in Instruments, Specialization = green, Load = cyan, Setup = magenta, Inference = blue. Also the **gauge has only 3 event types; Instruments has 4** (Instruments adds **Setup**).

### Graph statistics (verbatim)
> "Each graph displays data for a single event type. **Each bar represents the maximum activity duration within a one-second interval.**"
> - **High**: Maximum event duration.
> - **Low**: Minimum event duration.
> - **Count**: Number of events.

(Note: tray bars = *total/combined*; per-type graph bars = *maximum*; metric labels = *median*. Three different aggregations in one UI.)

### Activity table columns (verbatim)
> - **Start**: Start time of the event. Uses `hh:mm:ss.sss` format, **relative to start time of first event received**.
> - **Duration**: Total duration of event. **Units change dynamically depending on time scale.**
> - **Model**: Name of the model that produced the event. **Matches the model's filename.**
> - **Event**: Type of event. Either a Load, Inference, or Specialization event.

> "The table shows events from oldest to newest. **Scroll to the bottom to turn on automatic scrolling**, which always shows the latest events. To examine a specific row, scroll up to turn off automatic scrolling."
> "The activity graphs and the table are interactive… click it, and the table selects the corresponding events… You can also select events in the table, and the charts highlight the corresponding bars."

### The More menu (verbatim)
> "The options available are:
> - **Open in Core AI Debugger**: Opens the external Core AI Debugger to inspect model structure and intermediate values.
> - **Export to file**: Saves the input values for this inference to a file for later inspection."

⚠️ **NOTE (major footgun):** "**Open the report page before triggering the event you want to investigate. The More button options aren't available for events recorded before the report was open.**"

Screenshot alt-text reveals a **pre-release label leak**: the context menu shows "**Open in DebugML…** and Export to file…" — i.e. the tool's internal codename was *DebugML*, while the body text says "Open in Core AI Debugger".

### ⚠️ Export file formats (verbatim)
> "Choose **Export to file** to save the input tensors for the selected Inference event. A save dialog appears, letting you choose where to store the file. **Single-tensor inputs save as `.npy` files; multi-tensor inputs save as zipped `.npz` files.**"

### Unique capability (verbatim)
> "The debug gauge provides **the only entry point to a live Core AI Debugger session, and the only way to capture the input tensors that produced a specific Inference event**."

### Handoff to Instruments
> "Start profiling in Instruments by clicking the **Profile in Instruments** button in the top-right corner of the gauge's report page."

Example model name seen in screenshots: `MobileNetV3ClassifierFP16`.

---

## 24. Article: *Analyzing model runtime performance with Instruments*

`/documentation/coreai/analyzing-model-runtime-performance-with-instruments`

### What the template is for (verbatim)
> "This template helps you:
> - Profile model performance alongside the rest of your app.
> - Identify startup delays from models that aren't specialized for the current hardware.
> - Compare model performance across CPU, GPU, and Neural Engine.
> - Find unnecessary delays from repeatedly loading uncached models."

### Recording
> "Select your app's scheme and a run destination, then choose **Product > Profile**. In the Instruments template picker, select the **Core AI** template and click the **Choose** button. Alternatively, open Instruments and choose the Core AI template."

Template picker description string (verbatim from alt-text): **"Core AI: Monitors an application's machine learning activity executed through Core AI."**

### ⚠️ The four instruments in the Core AI template
*(This termList is DROPPED by sosumi.ai — recovered from Apple's raw DocC JSON.)*
> - **Core AI** — "Captures timing information for activity in the Core AI framework across all four event categories (Specialization, Load, Setup, and Inference)."
> - **Neural Engine** — "Captures activity on the Neural Engine, so you can correlate Core AI events with the hardware that runs them."
> - **GPU** — "Captures and shows activity on the GPU during the trace."
> - **Time Profiler** — "Profiles running threads on all cores at regular intervals for all processes."

> **NOTE:** "Profile on a **real device** for the most accurate performance data."
> **NOTE:** "For the most actionable results, **run your app on its own. Other apps competing for CPU, GPU, or Neural Engine resources can distort the trace.**"

### Track hierarchy (verbatim)
> "The Core AI instrument divides model activity into multiple tracks. The **top track shows all activity. Expand it to reveal a child track for each active model, and expand a model's track to reveal a child track for each of its active functions.**"
> **NOTE:** "The default function name is `main`."

### ⚠️ The four event categories with colors
*(Also a DROPPED termList — recovered from raw JSON. Listed "in the order they typically appear".)*
> - **Specialization** — "Runtime specialization of the model for the target device architecture. Only appears for models that aren't specialized ahead of time. Appears in **green** in the timeline."
> - **Load** — "Preparation of the model for loading into memory. Appears in **cyan** in the timeline."
> - **Setup** — "Preparation of the model before each inference. Appears in **magenta** in the timeline."
> - **Inference** — "A single, complete inference from the model. Appears in **blue** in the timeline."

> "**Specialization events are often the most time-intensive operations during model runtime. Each model produces at most one Specialization event — none if the model is fully specialized for the device or already cached.**"
> "Next, brief **Load** events appear in the timeline. They occur **only at the start of runtime**, when your app first loads the model into memory. **If you see frequent Load events during runtime, check that your app doesn't reload models repeatedly.**"
> "Finally, brief **Setup** events appear in the timeline, and Inference events follow. **A Setup event precedes each inference.**"

### Concrete event labels/timings visible in the docs' screenshots (useful for recognizing the UI)
- Specialize event label: **`Compile Asset, Specialize`** with a nested **`Compile segment`** sub-event; example duration ~800 ms (00:13.000 → ~00:13.800).
- Load event label: **`Load model::main (10.54 μs)`**
- Setup event label: **`Setup for model::main (66.96 μs)`** with nested **`Context.alloc (22.83 μs)`**
- Inference event labels: **`Run main`** and **`Run streaming function func_19`**
- Hardware tracks in the example: `Neural Engine`, `GPU (M3 Max)`, `Time Profiler / CPU Usage`, `M3 Max Metal Device State`

Naming convention: **`model::function`** (e.g. `model::main`). Note `Run streaming function func_19` implies specialized graphs get auto-generated sub-function names.

---

## 25. Article: *Inspecting Core AI models with Core AI Debugger*

`/documentation/coreai/inspecting-core-ai-models-with-core-ai-debugger`

### Workflow (verbatim)
> "Core AI Debugger is a standalone app for inspecting a Core AI model asset (`.aimodel`). The debugger follows a **three-step workflow: visualize, execute, and validate.** You visualize the model first to understand its structure, then execute the model to produce tensor outputs for each operation, and finally compare those outputs against a reference run to validate correctness."

> **NOTE:** "If you have a PyTorch model that needs to be converted to an `.aimodel`, see the `coreai-torch` documentation" → `https://apple.github.io/coreai-torch/main/getting-started/quickstart.html`

### Workspace layout (verbatim)
> "The Core AI Debugger workspace includes a **Navigator** panel on the left, **Structure** and **Source Viewers** in the middle, and an **Inspector** to the right.
> - Use the Navigator to explore, sort, and filter model operations.
> - The Structure Viewer shows a graphical representation of the model as a series of connected operations, while the Source Viewer shows the model's original Python source code, alongside a structured module hierarchy.
> - Use the Inspector to see detailed metadata about the selected operation, including its description, inputs, and outputs."
> "**The workspace stays synchronized around the selected operation**, so you can move fluidly between structure, source, and execution details."

### Visualization (verbatim)
> "Opening an `.aimodel` file loads the model's operations, structure, and source. **Operations in the Navigator are organized by their PyTorch module.** Selecting a module highlights the corresponding operations in the Structure Viewer, revealing their connectivity, data dependencies, and execution order. Clicking a specific operation highlights its Python source line in the Source Viewer. The Inspector shows additional details about the selected operation, including tensor formats of its inputs and outputs."

### ⚠️ Debug metadata requirement (verbatim)
> "The source-level features, including source line and PyTorch module mappings, **require debug metadata embedded in the `.aimodel` at export time**. Without this operation-level metadata, you can still view model operations in the Navigator, Structure Viewer, and the Inspector, but **the Source Viewer is unavailable**."
> **NOTE:** "See the `coreai-torch` documentation for details on how to export your model with debug metadata." → `https://apple.github.io/coreai-torch/main/api/debugging.html`

**Cross-checked against coreai-torch docs (read this session):**
> "During the current preview, set the following environment variables to ensure operation-level debug metadata is preserved and available to these tools:"
> ```
> export USE_LOCAL_COREAI=1
> export ENABLE_DEBUG_INFO=1
> ```

### Specialization scheme (verbatim)
> "Configure a **specialization scheme** before executing your model. The scheme settings let you specify a **hardware target, compute unit, and model inputs using predefined tensors (zeros, ones, or random) or values from a NumPy file.**"

Scheme dialog fields (from alt-text): **Target** (e.g. "Demo's MacBook Pro"), **Function** (`main`), **Compute Units** (e.g. "Prefer GPU", "Default"), **Graph Visualization** (e.g. "Specialized"), **Inputs** section (per-input, e.g. `pixel_values`, `input_ids`, `attention_mask`, each configurable as "NumPy Array"), buttons **Cancel** / **Run**.

> "Clicking Run **specializes the model for the selected target**, optimizing it for that hardware's capabilities. **The Structure Viewer updates to show the specialized model exactly as it executes on the chosen device.**"
> "After running, click any operation in the Navigator or Structure Viewer to see its **output tensor** directly in the Inspector."

### Two comparison configurations (verbatim)
> - "**Validate against a reference run.** Run your model in PyTorch and export the intermediate tensor values to an `aimodelintermediates` file using the `coreai-torch` API. Open that file alongside your `.aimodel` to compare the results."
> - "**Validate across configurations.** Configure two runs of the same `.aimodel` to compare execution across **different hardware targets, compute units, or inputs**."

### Sync points (verbatim)
> "Core AI Debugger compares two inference runs using ***sync points*: operation pairs whose outputs are expected to match.** When a comparison session starts, the debugger **automatically identifies sync points and computes similarity metrics for each one** so you can pinpoint where inference diverges."

---

## 26. Article: *Validating inference correctness against a reference run*

`/documentation/coreai/validating-inference-correctness-against-a-reference-run`

### Why (verbatim)
> "**Quantization and model specialization can introduce numerical drift** between a Core AI model and the original source model. Core AI Debugger pairs each operation in your Core AI asset with its counterpart in a reference run, then automatically measures similarity for every matched pair."

### The `.aimodelintermediates` file (verbatim)
> "An `.aimodelintermediates` file **records the intermediate tensor values produced at each operation of a PyTorch reference run**. To generate the file, use the `save_intermediates` API, **passing both the model you want to validate and the original source model**. The result is a per-operation mapping between the PyTorch run and the Core AI model that Core AI Debugger can use to compare inference results."

Cross-referenced from coreai-torch docs (read this session):
```python
from coreai_torch.debugging.torch_utils import save_intermediates, load_intermediates
from pathlib import Path

exported_program = torch.export.export(model, args=example_input)
metadata_path = save_intermediates(
    program=exported_program,
    inputs=example_input,
    output_dir=Path("./debug_output")
)
# → ./debug_output/main.aimodelintermediates
debug_trace = load_intermediates(Path("./debug_output/main.aimodelintermediates"))
# debug_trace.inputs / .outputs / .intermediates  (dict node_name -> tensor)
# save_intermediates(..., node_filter=custom_filter)  to restrict which ops are captured
```

### Starting a comparison session (verbatim, 6 steps)
> 1. "Open your `.aimodel` file in Core AI Debugger."
> 2. "In the toolbar, click the **Comparison** button to start a comparison session."
> 3. "Under **Configuration A**, set the **Target, Function, Compute Unit, and Graph Visualization**, and specify your model inputs."
> 4. "Under **Configuration B**, click the **Target** menu and select **Intermediates File** under **Load Reference Run**."
> 5. "Click the folder icon and select your `.aimodelintermediates` file."
> 6. "Click **Compare**."
> **NOTE:** "You can return to single-session mode at any time by clicking the Comparison button."

### Navigator sync-point indicators (verbatim)
> "Each sync point shows both operation names alongside a similarity score and a color-coded indicator dot:
> - **Green**: close match
> - **Yellow**: moderate divergence
> - **Red**: large error"
> "**Sort by Similarity** to identify the most divergent pairs, or **sort by Operation** to see whether failures cluster in a specific part of the model."

### ⚠️ The five comparison metrics
*(DROPPED termList — recovered from raw DocC JSON.)*
> "Core AI Debugger reports **five metrics** for each sync point. **Color indicators are metric-aware, so green always signals a good result regardless of which metric you choose.** The **default metric is PSNR**."
>
> - **PSNR** — "The ratio of the reference tensor's peak output value to the mean squared error, expressed in decibels. **A good general-purpose choice** that works well for most models and tensor types."
> - **Mean Absolute Error (MAE)** — "The average absolute difference across all elements. Use this to understand overall deviation **without sensitivity to outliers**."
> - **Mean Squared Error (MSE)** — "The average squared difference, which **amplifies larger errors**. Useful when large deviations are more consequential than small ones."
> - **Max Absolute Error** — "The single largest per-element difference. **A high value can expose clipping or overflow even when MAE looks acceptable.**"
> - **Mean Relative Error** — "The average difference as a proportion of the expected value at each element. **Useful when tensor magnitudes vary widely across operations.**"

### Investigation workflow (verbatim)
> "In the Inspector, the **tensor outputs from both runs are displayed side by side alongside a visual difference**, letting you see directly where the values diverge."
> "Use the Source Viewer to trace the operation back to its origin in the PyTorch code. **The module hierarchy at the top of the Source Viewer tells you which PyTorch module the operation belongs to. If low-similarity sync points cluster in the same module, the divergence is localized there, giving you a precise target for changes to your model.** If only specific operations diverge, use the Source Viewer to understand their implementation and identify what may be causing the discrepancy."

Inspector comparison view (from alt-text): "three stacked heatmap panels: the top panel shows the output from Configuration A, the middle panel shows the **element-wise difference with red highlighting** in regions of greatest divergence, and the bottom panel shows the output from Configuration B."

Example model referenced in screenshots: `modeling_sam.py` (Segment Anything), and a `Concat` operation.

---

## 27. Core AI Debugger app — download page

Source: `https://developer.apple.com/core-ai-debugger/` (fetched this session)

> "Core AI Debugger bridges the gap between modeling and deployment. It allows you to visualize, run, and validate Core AI models across every Apple platform with actionable feedback built for fast iteration."

**System requirements (verbatim from page):**
- **Host machine: macOS 27 or later**
- **Paired devices: iOS 27 or later, iPadOS 27 or later, or macOS 27 or later**
  - ⚠️ Note: **no visionOS / tvOS / watchOS in the paired-device list**, even though the framework supports them.

Distribution: "Sign in with your Apple Account to download. Complete free registration if prompted. Accept the Apple Developer Agreement."
Download search link: `https://developer.apple.com/download/all/?q=core%20ai%20debugger`

Feature bullets: "Inspect operations and trace data flow between them"; "Shows module hierarchy"; "Supports source mapping for Core AI models imported from PyTorch"; "Choose a paired device to specialize your model"; "Run models directly from Core AI Debugger"; "Load reference intermediate values and find sync points"; "Computes similarity scores like PSNR at each pair"; "Compare tensor values side by side with expanded tensor preview".

---

## 28. Release notes / updates status

- ❌ **`https://sosumi.ai/documentation/updates/coreai` → HTTP 404.** There is **no Core AI updates/release-notes page** at this time.
- ✅ `https://sosumi.ai/documentation/updates` → HTTP 200 (48,617 bytes). I grepped it for `core ai` / `coreai` / `mlx` / `evaluation`: **zero hits.** Core AI is entirely absent from Apple's "Updates" hub. The only AI-adjacent entries are:
  - `/documentation/updates/foundationmodels` — "Foundation Models updates"
  - `/documentation/foundationmodels`
  - `/documentation/foundationmodels/generating-content-and-performing-tasks-with-foundation-models`
- Interpretation: Core AI shipped as a **brand-new framework in the 27.0 cycle**, so there is no "what's new" delta page yet. Every symbol carries the `Beta` flag.

---

## 29. Consolidated gotchas / footguns

**Build & setup**
1. **Metal Toolchain is not installed by default.** Builds containing `.aimodel` files fail with a *missing Metal compiler* error. Install via Xcode > Settings > Components > Other Components > Metal Toolchain, or `xcodebuild -downloadComponent MetalToolchain`.
2. `.aimodel` files must appear in the target's **Compile Sources** build phase.
3. The **debug gauge only appears if the target *directly* links `CoreAI.framework`** (check General > Frameworks, Libraries, and Embedded Content). Transitive linkage is not enough. It does not work for Core ML.

**Specialization & caching**
4. Specialization output is tied to **both device hardware and OS version**. **OS update always invalidates the cache, regardless of `Policy`.**
5. The cache key is `(source .aimodel/.aimodelc URL, SpecializationOptions)`. `SpecializationOptions` is `Hashable` and changing it creates a **second** cache entry (duplicate storage + duplicate specialization cost).
6. **You cannot delete the source `.aimodel` and keep using `init(contentsOf:)`/`model(for:options:)`.** Use `bookmarkData` + `init(resolvingBookmark:)`.
7. **Bookmark data does not pin the cache entry.** Only a live `AIModel` pins it. A purge/OS-update invalidates the bookmark → re-download + re-specialize.
8. `init(resolvingBookmark:)`: malformed bookmark **throws**; stale-but-well-formed bookmark **returns `nil`**. Handle both.
9. Reference-doc vs article contradiction on deletion: reference says deleting an entry still referenced by a live `AIModel` **throws an error**; the prose article says deletion is **deferred**. Assume it throws and retry after releasing models.
10. `AIModelCache(appGroup:)` returns `nil` on invalid identifier / missing `com.apple.security.application-groups` entitlement / inaccessible container — the docs explicitly qualify "(on iOS)" for the invalid-identifier case, hinting at platform-divergent behavior.
11. AOT compilation **does not eliminate on-device specialization** — "the compiled asset still requires some specialization on the device."
12. **`AIModel.specialize` ≠ AOT.** It relocates *when*, not *how much*, work happens.

**Hardware / platform**
13. ⚠️ **AOT (`coreai-build`) only targets Apple-Intelligence-capable devices: A17 Pro or later (iPhone/iPad), M1 or later (Mac), M2 or later (Vision Pro).** Older devices get no `.aimodelc` and must fall back to on-device specialization from `.aimodel`.
14. Metal-backed APIs (`RawView.init(metalBuffer:)`, `AsyncValue.init(unsafeBuffer:)`, `ComputeStream.init(commandQueue:)`) are **unavailable on watchOS**.
15. `MTLBuffer` passed to Core AI **must use `shared` storage mode**.
16. Symbol pages omit macOS/Mac Catalyst from `metadata.platforms` even though the framework page lists both — a docs bug, not a real restriction.
17. Core AI Debugger: host must be **macOS 27+**; paired-device list is **iOS/iPadOS/macOS 27+ only** (no visionOS/tvOS/watchOS).

**Memory / layout**
18. `NDArrayDescriptor.preferredStrides` may be **non-contiguous**; if you use it, `contiguousElements` returns `nil` and you must use `withUnsafe(Mutable)Pointer` and respect the returned strides. If you *don't* use it, you may eat a hidden **layout-conversion copy** on every `run`.
19. Accessing `preferredStrides` or `minimumByteCount` on a descriptor with `hasDynamicShape == true` is a **programming error** — call `resolvingDynamicDimensions(_:)` first.
20. Dynamic dimensions are `-1` in the API but shown as `?` in the Xcode model viewer.
21. `NDArray.init(descriptor:)` requires `hasDynamicShape == false`.
22. With `InterleaveLayout`, the reported stride for the interleaved dimension is a **block stride**, not an element stride. Offset formula: `offset = (index[d]/f)*strides[d] + (index[d]%f) + Σ_{i≠d} index[i]*strides[i]`.
23. Raw-view metal/IOSurface initializers are **explicitly unsafe** — you must guarantee no other CPU code or GPU pipeline writes the buffer while the view is alive.
24. `AsyncValue.ndArray` / `AsyncMutableValue.ndArray` return a **copy** when the value was built from an `MTLBuffer` (to avoid aliasing).

**API-shape traps**
25. `InferenceValue.ndArray` is a **consuming** read ("Accessing this property consumes the value and transfers ownership") despite looking like an ordinary getter.
26. `InferenceFunction.Outputs.remove(_:)` is destructive — a second `remove` of the same name returns `nil`.
27. `InferenceValue.NamedMutableViews.take(_:)` **fatal-errors** if you take the same name twice (`nil` only means "no such name").
28. **You must supply a mutable view for *every* state** in `states:`; omitting any state is an error. There is no `stateCount` property — use `stateNames.count`.
29. Outputs you pass a view for in `outputViews:` do **not** appear in the returned `Outputs`.
30. `run(...)` returned `NDArray`s are always **row-major contiguous**, regardless of internal preferred layout.
31. `InferenceFunction` is `Sendable` and safe to call concurrently, but **"automatically allocates additional intermediate buffers as needed to support concurrency"** — concurrency costs memory silently.
32. `encode(...)` is `throws`, **not** `async throws`; it returns when work is *encoded*, not complete. Await the returned `AsyncValue`s or call `ComputeStream.currentWorkCompleted()`.
33. `mutableView(as:)` / `mutableRawView()` are `mutating`; `view(as:)` / `rawView()` are not.
34. `NDArray.MutableRawView.view(as:)` returns a **`MutableView`**, not a `View`, despite the name.
35. `NDArray.RawView.view(as:)` is **`consuming`** and asserts `T` matches the stored `scalarType`.
36. `slice(at:)` accepts fewer ranges than `rank`; **unspecified trailing dimensions default to `.all`**.
37. On `MutableView`/`MutableRawView`, use **`mutatingSlice(at:)`** (not `slice(at:)`) when you intend to write through the sub-view.
38. `SpecializationOptions.expectFrequentReshapes` has **no Discussion, no documented default, and no initializer** that sets it.

**Tooling**
39. ⚠️ **The debug gauge's More menu (Open in Core AI Debugger / Export to file) only works for events recorded *after* you open the report page.** Open it first.
40. Exported inference inputs: `.npy` for a single tensor, zipped `.npz` for multiple.
41. Event-color schemes **differ between the gauge (3 categories) and Instruments (4 categories, adds `Setup`)**, and Load/Specialization colors are swapped between the two. Don't transfer color intuitions.
42. Core AI Debugger's Source Viewer requires **debug metadata embedded at export time**. In the current preview, `coreai-torch` needs `USE_LOCAL_COREAI=1` and `ENABLE_DEBUG_INFO=1`.
43. Profile **on a real device** and **with no other apps running** — the docs call this out twice.
44. Frequent **Load** events in a trace mean your app is reloading models — a bug signal.

**Doc-quality issues found (useful for guide-writing accuracy)**
45. Several `- Throws:` clauses render as orphaned Notes: "If specializing or loading the model fails." (on `AIModel.init` and `specialize`), "If a cache entry was found but the specialized asset failed to load." (on `model(for:options:)`).
46. The `AsyncValue` overview example omits the required `to:` stream argument and misspells a variable (`embeddingsOutputs`).
47. The `minimumByteCount` example passes `RawView.init` arguments out of declared order and omits `try await` on `run`.
48. Apple's own text has typos: "vaiews" (`AsyncMutableValue`), "the the" (`ComputeStream`).
49. `MutableView.copyElements(from:)` docs reference `layout.scalarCount`, a symbol that isn't in the public API — internal-doc leak.
50. Several abstracts have empty inline-code placeholders where sosumi dropped symbol references (e.g. `AIModel.init(contentsOf:options:)` abstract renders as "Creates an  from a or  file." — the real text is "Creates an **AIModel** from a **.aimodel** or **.aimodelc** file").

---

## 30. Complete symbol inventory (all 312 paths, grouped)

Verified against `https://developer.apple.com/tutorials/data/index/coreai`. Counts: `property 100, method 56, case 53, init 42, struct 31, subscript 8, article 7, enum 6, class 3, protocol 3, collection 2, module 1` = **312**.

**Articles (7)** + **collections (2)**:
```
/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai      (article)
/documentation/coreai/managing-model-specialization-and-caching                     (article)
/documentation/coreai/compiling-core-ai-models-ahead-of-time                        (article)
/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models             (collection)
/documentation/coreai/monitoring-model-performance-with-the-debug-gauge             (article)
/documentation/coreai/analyzing-model-runtime-performance-with-instruments          (article)
/documentation/coreai/inspecting-core-ai-models-with-core-ai-debugger               (article)
/documentation/coreai/validating-inference-correctness-against-a-reference-run      (article)
/documentation/coreai/aimodelasset/metadata-swift.struct/creatordefinedvalue/customstringconvertible-implementations  (collection)
```

**Top-level types (13):** `AIModel` (struct), `AIModelAsset` (struct), `AIModelCache` (class), `InferenceFunction` (struct), `InferenceFunctionDescriptor` (struct), `InferenceValue` (struct), `ImageDescriptor` (struct), `ComputeStream` (class), `NDArray` (struct), `NDArrayDescriptor` (struct), `ComputeUnitKind` (enum), `SpecializationOptions` (struct), `AssetError` (struct).

**Classes (3):** `AIModelCache`, `ComputeStream`, `InferenceFunction.AsyncValue`.
**Protocols (3):** `NDArray.RangeExpression`, `InferenceValue.ViewRepresentable`, `InferenceValue.MutableViewRepresentable`.
**Enums (6):** `ComputeUnitKind`, `NDArray.ScalarType`, `InferenceValue.Kind`, `InferenceValue.Descriptor`, `AssetError.Kind`, `AIModelAsset.Metadata.CreatorDefinedValue`.

**Nested structs (under their owners):**
- `AIModelAsset`: `FunctionDescriptor`, `Metadata`, `Summary`, `Summary.OperationCount`, `Summary.StorageType`, `ValueDescriptor`
- `AIModelCache`: `Policy`, `Policy.PurgeConditions`
- `InferenceFunction`: `Inputs`, `Outputs`, `MutableViews`, `AsyncMutableValue`, `AsyncMutableViews` (+ class `AsyncValue`)
- `InferenceValue`: `View`, `MutableView`, `NamedMutableViews`
- `NDArray`: `View<Element>`, `MutableView<Element>`, `RawView`, `MutableRawView`, `InterleaveLayout`

**Disambiguation slugs seen (needed to build correct doc URLs):**
```
aimodel/init(contentsof:options:) | init(resolvingbookmark:) | loadfunction(named:)
  | functiondescriptor(for:) | functionnames | specialize(contentsof:options:cache:cachepolicy:)
  | bookmarkdata | devicearchitecturename
aimodelasset/metadata-swift.property   vs  aimodelasset/metadata-swift.struct
aimodelcache/policy/purgeconditions-swift.property vs .../purgeconditions-swift.struct
inferencevalue/kind-swift.property     vs  inferencevalue/kind-swift.enum
ndarray/scalartype-swift.property      vs  ndarray/scalartype-swift.enum
ndarray/interleavelayout-swift.property vs ndarray/interleavelayout-swift.struct
asseterror/kind-swift.property         vs  asseterror/kind-swift.enum
inferencefunction/run(inputs:states:outputviews:)-mqfb   (dictionary overload)
inferencefunction/run(inputs:states:outputviews:)-14emi  (Inputs overload)
inferencefunction/inputs/insert(_:for:)-3eg32 | -2htrp | -5o5oi
inferencefunction/mutableviews/insert(_:for:)-1b2yx | -8ossp | -9ixpc
inferencefunction/asyncvalue/init(_:)-5qtut | -90hbj | -9wk3
inferencefunction/asyncmutablevalue/init(_:)-4aqgq | -x6se
ndarray/view/slice(at:)-32gsh | -4yomr
ndarray/mutableview/slice(at:)-50cpv | -qyjq ; mutatingslice(at:)-30asd | -9pmi4
ndarray/rawview/slice(at:)-1gght | -kd5b
ndarray/mutablerawview/slice(at:)-47fbq | -82sdj ; mutatingslice(at:)-5tnq5 | -5ts4w
aimodelasset/metadata-swift.struct/subscript(_:_:)-44ov4 | -50v52 | -5o1kb | -5se5j | -6bxrd | -9hpy0
aimodelasset/metadata-swift.struct/creatordefinedvalue/init(_:)-1q79a | -2lzjt | -40q72 | -5y6lm | -61sg1 | -9xsmm
```

---

## 31. Cross-links to other agents' areas

- **`coreai-torch`** (`https://apple.github.io/coreai-torch/`) — the PyTorch → `.aimodel` converter. Owns: `TorchConverter`, `to_coreai()`, composite ops (`GatherMM`, `GatedDeltaUpdate`, `RMSNormImpl`, `RoPE`, `SDPA`, `batch_norm`, `group_norm`, `hard_sigmoid`, `instance_norm`, `layer_norm`, `linalg_vector_norm`, `log_softmax`, `pixel_shuffle`), `generate_composite_decl`, `ExternalizeSpec`, `TorchMetalKernel`, Supported ATen ops, Custom Op Lowering, Custom Metal Kernels, Externalization, Debugging module (`coreai_torch.debugging.validator` / `.comparator` / `.torch_utils`). **This owns `save_intermediates` / `.aimodelintermediates`, which the Core AI Debugger article depends on.**
- **`coreai-core`** (Python pkg, `pip install coreai-core`) — `coreai.authoring` (build an AI Model from Python) and `coreai.runtime` (load & run `.aimodel` with NumPy inputs). A **Python-side runtime mirror** of the Swift `AIModel`/`InferenceFunction` API; worth a dedicated comparison.
- **`coreai-optimization`** (`https://apple.github.io/coreai-optimization`) — quantization/palettization. Directly explains why `NDArray.ScalarType` has `int2…int7`, `uint1…uint7`, `float4e2m1fn`, `float8e8m0fn`.
- **`apple/coreai-models`** GitHub repo — pre-converted `.aimodel` files (third-party search result, unverified by me).
- **Foundation Models framework** — the only AI framework with an `/documentation/updates/foundationmodels` page. Core AI is the *custom model* path; FM is the *system LLM* path.
- **Core ML** — Apple explicitly routes non-neural-network model types (decision trees, tabular feature engineering) to Core ML. Core AI does **not** replace Core ML for those.
- **BackgroundAssets** — Apple's recommended delivery mechanism for remotely-hosted `.aimodelc` variants.
- **Metal / MTLBuffer / MTLCommandQueue / IOSurface / CoreVideo (`CVMutablePixelBuffer`, `CVReadOnlyPixelBuffer`)** — Core AI's zero-copy interop surface. Note `CVReadOnlyPixelBuffer` / `CVMutablePixelBuffer` are the *new* Swift-native pixel buffer types (not `CVPixelBuffer`).
- **Swift 6.x/7 language features** — `Span`, `MutableSpan`, `RawSpan`, `MutableRawSpan`, `InlineArray`, value generics `<let rank : Int>`, `[n of T]` fixed-count array syntax, typed throws `throws(E)`, `~Copyable`, `consuming`/`borrowing`, `@export(implementation)`. Core AI is one of the heaviest adopters in Apple's SDK; a guide on "reading Core AI's Swift signatures" would be genuinely useful.
- **WWDC26 sessions** (found via search, not fetched — for the transcripts agent): **324 "Meet Core AI"**, **325 "Dive into Core AI model authoring and optimization"**, **326 "Integrate on-device AI models into your app using Core AI"**, plus `developer.apple.com/wwdc26/guides/machine-learning/`.

---

## 32. Source inventory (everything I actually read this session)

### Apple docs via sosumi.ai (HTTP 200 unless noted) — cached at `/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/coreai/`
```
https://sosumi.ai/documentation/coreai/                                              (framework page, trailing slash)
https://sosumi.ai/documentation/coreai                                               (FULL SYMBOL INDEX w/ signatures, 40,308 B)
https://sosumi.ai/documentation/coreai/aimodel
https://sosumi.ai/documentation/coreai/aimodel/init(contentsof:options:)
https://sosumi.ai/documentation/coreai/aimodel/init(resolvingbookmark:)
https://sosumi.ai/documentation/coreai/aimodel/loadfunction(named:)
https://sosumi.ai/documentation/coreai/aimodel/functiondescriptor(for:)
https://sosumi.ai/documentation/coreai/aimodel/functionnames
https://sosumi.ai/documentation/coreai/aimodel/specialize(contentsof:options:cache:cachepolicy:)
https://sosumi.ai/documentation/coreai/aimodel/bookmarkdata
https://sosumi.ai/documentation/coreai/aimodel/devicearchitecturename
https://sosumi.ai/documentation/coreai/aimodelasset            (+ init(contentsof:), isvalid(at:), metadata-swift.property,
                                                                  summary(includingstatistics:), url, updatemetadata(_:),
                                                                  removederivedartifacts(), functiondescriptor,
                                                                  metadata-swift.struct, summary, valuedescriptor,
                                                                  metadata-swift.struct/creatordefinedvalue,
                                                                  metadata-swift.struct/{creatordefinedmetadata,description,creationdate},
                                                                  metadata-swift.struct/subscript(_:_:)-44ov4, -9hpy0,
                                                                  functiondescriptor/{states,inputs},
                                                                  summary/{computetypes,storagetypes,operationdistribution,functions,
                                                                           storagetype,storagetype/typename,operationcount},
                                                                  valuedescriptor/typename)
https://sosumi.ai/documentation/coreai/aimodelcache            (+ default, init(appgroup:), model(for:options:),
                                                                  deleteentries(for:), deleteentry(for:options:), deleteall(),
                                                                  deleteentry(referencedby:), policy, policy/default,
                                                                  policy/persistent, policy/purgeconditions-swift.struct,
                                                                  policy/purgeconditions-swift.struct/{sourceassetchangedordeleted,storagepressure})
https://sosumi.ai/documentation/coreai/inferencefunction       (+ run(...)-mqfb, run(...)-14emi, encode(...), descriptor,
                                                                  inputs, outputs, mutableviews, asyncvalue, asyncmutablevalue,
                                                                  asyncmutableviews, inputs/insert(_:for:)-3eg32/-2htrp/-5o5oi,
                                                                  outputs/{remove(_:),names},
                                                                  mutableviews/insert(_:for:)-1b2yx/-8ossp/-9ixpc,
                                                                  asyncvalue/{init(unsafebuffer:...),ndarray,pixelbuffer},
                                                                  asyncmutablevalue/{init(descriptor:),ndarray},
                                                                  asyncmutableviews/insert(_:for:))
https://sosumi.ai/documentation/coreai/inferencefunctiondescriptor  (+ inputdescriptor(of:), statenames, statedescriptor(of:))
https://sosumi.ai/documentation/coreai/inferencevalue          (+ kind-swift.property, ndarray, pixelbuffer, init(_:),
                                                                  descriptor, descriptor/ndarray(_:), kind-swift.enum,
                                                                  kind-swift.enum/{image,ndarray}, view, mutableview,
                                                                  namedmutableviews, namedmutableviews/take(_:),
                                                                  viewrepresentable/view(), mutableviewrepresentable/mutableview())
https://sosumi.ai/documentation/coreai/imagedescriptor         (+ pixelformattype)
https://sosumi.ai/documentation/coreai/computestream           (+ init(), init(commandqueue:), currentworkcompleted())
https://sosumi.ai/documentation/coreai/ndarray                 (+ init(shape:scalartype:), init(shape:scalartype:strides:),
                                                                  init(shape:scalartype:strides:interleavelayout:),
                                                                  init(scalars:shape:), init(descriptor:), shape, strides,
                                                                  view(as:), mutableview(as:), rawview(), mutablerawview(),
                                                                  view, mutableview, rawview, mutablerawview,
                                                                  scalartype-swift.enum (+ float8e8m0fn, int4),
                                                                  interleavelayout-swift.struct (+ init(dimension:factor:)),
                                                                  interleavelayout-swift.property, rangeexpression (+ all, relative(to:)),
                                                                  view/{contiguouselements,subscript(scalarat:),withunsafepointer(_:),slice(at:)-32gsh},
                                                                  mutableview/{copyelements(from:),mutatingslice(at:)-9pmi4},
                                                                  rawview/{init(metalbuffer:...),view(as:)})
https://sosumi.ai/documentation/coreai/ndarraydescriptor       (+ shape, preferredstrides, minimumbytecount, hasdynamicshape,
                                                                  resolvingdynamicdimensions(_:))
https://sosumi.ai/documentation/coreai/computeunitkind         (+ availablekinds, cpu, neuralengine)
https://sosumi.ai/documentation/coreai/specializationoptions   (+ default, cpuonly, init(preferredcomputeunitkind:),
                                                                  allowedcomputeunitkinds, preferredcomputeunitkind, expectfrequentreshapes)
https://sosumi.ai/documentation/coreai/asseterror              (+ kind-swift.enum, kind-swift.enum/unsupportedversion(_:),
                                                                  init(kind:debugmessage:), errordescription)
https://sosumi.ai/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai
https://sosumi.ai/documentation/coreai/managing-model-specialization-and-caching
https://sosumi.ai/documentation/coreai/compiling-core-ai-models-ahead-of-time
https://sosumi.ai/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models
https://sosumi.ai/documentation/coreai/monitoring-model-performance-with-the-debug-gauge
https://sosumi.ai/documentation/coreai/analyzing-model-runtime-performance-with-instruments
https://sosumi.ai/documentation/coreai/inspecting-core-ai-models-with-core-ai-debugger
https://sosumi.ai/documentation/coreai/validating-inference-correctness-against-a-reference-run
https://sosumi.ai/documentation/updates                                              (200; contains ZERO Core AI mentions)
https://sosumi.ai/documentation/updates/coreai                                       ❌ HTTP 404 — page does not exist
```

### Apple raw DocC JSON API (used to recover sosumi-dropped content)
```
https://developer.apple.com/tutorials/data/index/coreai                              (full nav index, 312 entries)
https://developer.apple.com/tutorials/data/documentation/coreai.json
https://developer.apple.com/tutorials/data/documentation/coreai/aimodel.json
https://developer.apple.com/tutorials/data/documentation/coreai/ndarray.json
https://developer.apple.com/tutorials/data/documentation/coreai/inferencefunction.json
https://developer.apple.com/tutorials/data/documentation/coreai/analyzing-model-runtime-performance-with-instruments.json   ← recovered 2 termLists
https://developer.apple.com/tutorials/data/documentation/coreai/validating-inference-correctness-against-a-reference-run.json ← recovered metrics termList
https://developer.apple.com/tutorials/data/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai.json
https://developer.apple.com/tutorials/data/documentation/coreai/managing-model-specialization-and-caching.json
https://developer.apple.com/tutorials/data/documentation/coreai/compiling-core-ai-models-ahead-of-time.json
   … plus ~70 individual symbol .json files (all listed under the sosumi block above; fetched via scratchpad/aj.py)
```

### Other pages read
```
https://developer.apple.com/core-ai-debugger/                            (Core AI Debugger download page, system requirements)
https://apple.github.io/coreai-torch/main/coreai-core/                   (coreai-core Python package overview)
https://apple.github.io/coreai-torch/main/api/debugging.html             (save_intermediates / load_intermediates / env vars)
```

### Web searches (third-party, treated as UNVERIFIED)
```
"coreai-build" compile aimodel --preferred-compute flags xcrun
Apple "Core AI" framework aimodel WWDC26 AIModel InferenceFunction
```
Surfaced (not fetched, for other agents): `developer.apple.com/videos/play/wwdc2026/324|325|326`, `developer.apple.com/wwdc26/guides/machine-learning/`, `github.com/apple/coreai-models`, plus blog posts (theswift.dev, blakecrosley.com, Qiita/Zenn benchmarks).

### Local scratch artifacts (raw markdown, reusable)
```
/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/coreai/*.md
/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/coreai/fetch.sh
/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/aj.py     (Apple DocC JSON → text extractor)
/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/idx.json  (full nav index)
```

**Methodology note for future agents:** `curl` against `sosumi.ai` beats `WebFetch` for archival work — `WebFetch` runs a summarizer model over the page and destroys verbatim signatures. But sosumi **silently drops DocC `termList` and `table` blocks**; when a page ends a sentence with "…are:" or "…includes the following:" followed by nothing, refetch `https://developer.apple.com/tutorials/data/documentation/<path>.json` and parse it. `https://developer.apple.com/tutorials/data/index/<framework>` gives the complete symbol tree for coverage verification.

---

## 33. Open questions / unverified

1. **`coreai-build compile --help` full flag list.** Apple's prose names only `--platform`, `--min-deployment-version`, `--output`, `--preferred-compute`, and alludes to a target-architecture flag. Third-party sources suggest `--architecture h18p` and `--preferred-compute neural-engine`. **UNVERIFIED** — needs a machine with Xcode 27 + Metal Toolchain to run `xcrun coreai-build compile --help`. Also unknown: whether `coreai-build` has other subcommands besides `compile`.
2. **The set of `deviceArchitectureName` values.** No documented enumeration. `h18p` (iPhone 17 Pro) is a third-party claim only.
3. **`--preferred-compute` accepted values** and how they map to `ComputeUnitKind` (`cpu`/`gpu`/`neuralEngine` vs `neural-engine`?).
4. **`SpecializationOptions.expectFrequentReshapes` default value and semantics.** No Discussion section exists. Also: is it settable given `default`/`cpuOnly` are `let`s and the only init takes `preferredComputeUnitKind`? (Presumably `var options = SpecializationOptions.default; options.expectFrequentReshapes = true`.)
5. **Raw values of `AIModelCache.Policy.PurgeConditions`** and the exact composition of `.default` / `.persistent`. Inferred but not stated.
6. **What error type is thrown** by `AIModel.init(contentsOf:)`, `loadFunction(named:)`, `run(...)`, `encode(...)`, and the cache `delete*` methods. `AssetError` covers *asset* operations only. There is **no documented inference/specialization/cache error type** anywhere in the 312 symbols. Possibly `CoreAIError` exists but is undocumented, or they throw `NSError`/`CocoaError`.
7. **How `view(as:)` works for sub-byte scalar types** (`int4`, `uint1`, `int3`, …) and 8-bit floats (`float8e4m3fn`, …) — there's no corresponding `BitwiseCopyable` Swift standard type. Is there a Core AI-provided `Int4`/`Float8E4M3FN` type? `RawView` may be the only access path. **Unverified.**
8. **`NDArray.ScalarType.type`** — referenced in `RawView.view(as:)`'s note ("`T` must match `self.scalarType.type`") but **not present in the 312-symbol index**. Either undocumented or internal.
9. **`AIModelAsset.removeDerivedArtifacts()`** — no abstract, no discussion. What is a "derived artifact" inside an `.aimodel` bundle, and when should you strip it? (Likely the pre-compiled `.aimodelc`-ish payload embedded in the asset.)
10. **`.aimodel` bundle on-disk format.** Docs call it a "bundle" (`AIModelAsset(contentsOf:)` takes "the URL of an `.aimodel` bundle on disk") but never describe its structure. Also unknown: where `AIModelCache.default` stores entries on disk.
11. **`.aimodelc` vs `.aimodel` in `AIModelAsset`.** `isValid(at:)` says "the extension is one of the known model asset extensions" (plural) — unclear if `AIModelAsset` accepts `.aimodelc`.
12. **`AIModelAsset` is not `Sendable`** (no Conforms To section at all, unlike every other type). Intentional or a doc omission?
13. **`ComputeStream` throughput/ordering guarantees** beyond "serialized as needed based on the values read/written." No documentation of how many concurrent streams are advisable, or interaction with `run()`'s implicit stream.
14. **Whether Core AI ships an Objective-C or C interface.** All docs are Swift-only; no `interfaceLanguages.occ` entries in the index.
15. **`_AllRange`** — underscored type exposed as `RangeExpression.all`'s type. Is it public-but-underscored (SPI-ish) or will it be renamed before GA?
16. **Relationship between the gauge's 3 event types and Instruments' 4.** Why does the gauge not surface `Setup`? Is `Setup` folded into the gauge's `Inference` measurement (which would inflate it)?
17. **Whether Core AI Debugger can attach to visionOS/tvOS/watchOS devices.** The download page lists only iOS/iPadOS/macOS 27+ as paired devices, but the framework supports 7 platforms.
18. **macOS availability annotation.** Almost certainly a docs bug, but I could not find any page stating `macOS 27.0+` on a *symbol*. Should be confirmed against the actual SDK's `.swiftinterface` if anyone has Xcode 27.
19. **No sample-code project** exists in the Core AI docs (index shows 0 `sampleCode` entries) — unusual for a flagship Apple framework. May appear later, or may live in `github.com/apple/coreai-models`.
20. **`InferenceFunction.AsyncValue` is a `final class` while `AsyncMutableValue` is a `struct`.** The asymmetry is undocumented; presumably because `AsyncValue` needs reference identity for the pipeline dependency graph.
