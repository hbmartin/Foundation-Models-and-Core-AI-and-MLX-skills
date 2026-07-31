# apple/coreai-models — the NON-LLM half (vision, audio, diffusion)

> Companion to `/Volumes/ExtStor/FM and MLX and CoreAI/notes/repos/apple-coreai-models.md`,
> which covers `CoreAILanguageModels`, the Python LLM export tooling, and `skills/`.
> **This file deliberately covers what that one did not**: the four non-LLM Swift products,
> their CLI tools, the vision/audio/diffusion model catalog, and the non-LLM Python primitives.
>
> Repo: `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__coreai-models` @ commit `5ed9981`
> (`5ed9981303b38d5a44aa6b45509bc4f6945029f5`, the pinned checkout in `scripts/clone-research-repos.sh`).
> All code quoted with `path:LINE` citations relative to that repo root.
> Anything not directly read is marked **UNVERIFIED**.

## Table of contents

1. Orientation: the four non-LLM products and how they relate
2. `CoreAIShared` — the reusable substrate
   - 2.1 `Runtime/ModelStructure.swift` — structure detection & compute-unit selection
   - 2.2 `Runtime/NDArray+Helpers.swift` — the fill/read/flatten layer
   - 2.3 `Runtime/ResourceManaging`, `FileSize`
   - 2.4 `Bundle/` — `ModelBundle`, `BundleKind`, `FunctionMap`
   - 2.5 `Image/` — `ImagePreprocessor`, `CGImageUtils` (image ↔ tensor)
   - 2.6 `Logger/CLILogger`
3. `CoreAISegmentation` (`CoreAIImageSegmenter`)
   - 3.1 Public API surface
   - 3.2 `CoreAISegmentationEngine` — single-function vs multi-function backends
   - 3.3 Tensor-name discovery (the duck-typing layer)
   - 3.4 Point prompts: `PointQuery`, sentinel padding, best-of-K, segment-everything
   - 3.5 Postprocessing & visualization
   - 3.6 `CLIPTokenizer`
   - 3.7 Copyable usage
4. `CoreAIObjectDetection` (`CoreAIObjectDetector`)
5. `CoreAISpeech`
6. `CoreAIDiffusion` (`CoreAIDiffusionPipeline`)
   - 6.1 The protocol layer · 6.2 `CoreAIDiffusionModelFunction`
   - 6.3 Components: text encoder, denoiser, latent codec
   - 6.4 `PipelineDescriptor` — the diffusion bundle schema
   - 6.5 `StableDiffusionPipeline` — the canonical orchestration loop
   - 6.6 Multi-model bundle layout — FLUX.2
   - 6.7 Schedulers · 6.8 RNG parity · 6.9 `BPETokenizer` · 6.10 Copyable usage
7. CLI tools (`swift/Sources/Tools/`)
   - 7.1 `benchmark`
   - 7.2 `image-segmenter`
   - 7.3 `object-detector`
   - 7.4 `speech-runner`
   - 7.5 `diffusion-runner`
8. The non-LLM model catalog (`models/`)
9. Python non-LLM primitives (`python/src/coreai_models/`)
10. The multi-model / multi-function pipeline story
11. iOS vs macOS divergence
12. Guide topics this material uniquely supports
13. Source inventory
14. Open questions / UNVERIFIED

---

## 1. Orientation: the four non-LLM products

`Package.swift` declares **five** libraries. Four are non-LLM:

| Product (library) | Target | Source dir | Deps | Executable(s) |
|---|---|---|---|---|
| `CoreAILM` | `CoreAILanguageModels` | — | *(covered in the other notes file)* | `llm-runner`, `llm-benchmark` |
| `CoreAIDiffusion` | `CoreAIDiffusionPipeline` | `swift/Sources/CoreAIDiffusionPipeline` | `CoreAIShared`, `Transformers` (swift-transformers) | `diffusion-runner` |
| `CoreAISegmentation` | `CoreAIImageSegmenter` | `swift/Sources/CoreAIImageSegmenter` | `CoreAIShared` **only** | `image-segmenter` |
| `CoreAISpeech` | `CoreAISpeech` | `swift/Sources/CoreAISpeech` | `CoreAIShared`, `Transformers` | `speech-runner` |
| `CoreAIObjectDetection` | `CoreAIObjectDetector` | `swift/Sources/CoreAIObjectDetector` | `CoreAIShared` **only** | `object-detector` |

`Package.swift:14-41` (products), `:49-117` (targets), `:130-200` (executables).

Notable: the **segmenter and detector have zero third-party dependencies** — they depend only
on `CoreAIShared`, which itself has `dependencies: []` (`Package.swift:84-91`). That makes them the
cleanest templates for "run a vision model on Core AI" with nothing but the OS frameworks.
The segmenter ships its own `CLIPTokenizer` precisely to avoid pulling in swift-transformers
(see §3.6).

Test targets (`Package.swift:227-252`): `ImageSegmenterTests`, `DiffusionPipelineTests`,
`ObjectDetectorTests`, `CoreAISharedTests`. There is **no** `SpeechTests` target — speech is the
least-tested product in the repo.

### The shape of every non-LLM product

All four follow the same three-layer sandwich:

```
  <Product>            e.g. ImageSegmenter, ObjectDetector, SpeechModel, StableDiffusionPipeline
     │                 high-level: takes CGImage / URL / String, returns domain types
     ▼
  <Engine/Components>  e.g. CoreAISegmentationEngine, CoreAIDenoiser, WhisperDecoder
     │                 owns InferenceFunction(s), builds NDArrays, name-discovery
     ▼
  CoreAIShared         PreparedModel, ModelBundle, ImagePreprocessor, fillNDArray/flattenAsFloat
     │
     ▼
  CoreAI (SDK)         AIModel, AIModelAsset, InferenceFunction, NDArray, NDArrayDescriptor
```

The value of reading this repo is **layer 2 and 3** — everything between `CGImage` and
`NDArray` that Apple's own vision products had to write by hand.

---

## 2. `CoreAIShared` — the reusable substrate

Ten files, ~700 lines total, no dependencies. This is the layer a reader should copy rather
than reinvent. Full inventory:

```
CoreAIShared/Bundle/BundleKind.swift          16 L
CoreAIShared/Bundle/FunctionMap.swift         41 L
CoreAIShared/Bundle/ModelBundle.swift        200 L
CoreAIShared/Image/CGImageUtils.swift         59 L
CoreAIShared/Image/ImagePreprocessor.swift   286 L
CoreAIShared/Logger/Logger.swift              48 L
CoreAIShared/Runtime/FileSize.swift           39 L
CoreAIShared/Runtime/ModelStructure.swift    229 L
CoreAIShared/Runtime/NDArray+Helpers.swift   139 L
CoreAIShared/Runtime/ResourceManaging.swift   22 L
```

### 2.1 `Runtime/ModelStructure.swift` — structure detection & compute-unit selection

This is the single most reusable idea in the repo: **look at the function names inside an
`.aimodel`, infer what kind of model it is, and use that to pick the compute unit *before*
you specialize.**

Well-known function names (`ModelStructure.swift:12-20`):

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

Three structures (`ModelStructure.swift:29-39`):

```swift
public enum ModelStructure: Equatable, Sendable, CustomStringConvertible {
    case chunkedStatic(batchSize: Int)   // has extend_* AND load_embeddings
    case dynamic                          // has main
    case multiFunctionSegmenter           // has image_encode AND text_encode AND detect
}
```

Compute-unit mapping (`ModelStructure.swift:57-80`) — **quote this verbatim in any guide**:

```swift
public var preferredDevice: String {
    switch self {
    case .chunkedStatic, .multiFunctionSegmenter: return "NeuralEngine"
    case .dynamic:                                 return "GPU"
    }
}

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

So: **the three-function SAM3 split is not just a latency trick — it is what routes the model
to the Neural Engine.** A single-`main` SAM3 export is classified `.dynamic` and lands on the GPU.
That is the mechanism behind the WWDC26 session-325 speedup claim, expressed in code.

The two-phase load (`ModelStructure.swift:145-165`):

```swift
public static func prepare(at url: URL) async throws -> PreparedModel {
    CLILogger.log("PreparedModelAsset: Preparing \(url.lastPathComponent)")
    // Probe structure before specializing so we can pick the right compute-unit preference.
    let probedStructure = probeStructure(at: url)
    CLILogger.log("  - Probed structure: \(probedStructure.description)")
    let options = probedStructure.specializationOptions
    let model = try await AIModel(contentsOf: url, options: options)
    CLILogger.log("  - Loaded \(model.functionNames.count) graphs")
    // Re-detect from compiled library — source of truth, should match the probe.
    let structure = detectStructure(from: model.functionNames)
    return PreparedModel(model: model, structure: structure)
}
```

`probeStructure` uses `AIModelAsset.summary(includingStatistics: false)` to read function names
**without triggering specialization** (`ModelStructure.swift:170-185`) — a cheap metadata read.
On any failure it silently defaults to `.dynamic`:

```swift
private static func probeStructure(at url: URL) -> ModelStructure {
    do {
        let asset = try AIModelAsset(contentsOf: url)
        if let summary = try asset.summary(includingStatistics: false) {
            let names = summary.functions.map(\.name)
            if !names.isEmpty { ... return detectStructure(from: names) }
        }
        CLILogger.log("  - Probe (summary) returned empty; defaulting to .dynamic")
    } catch { ... }
    return .dynamic
}
```

Detection order matters and is commented (`ModelStructure.swift:190-218`):

1. `extend*` + `load_embeddings` → `.chunkedStatic(batchSize:)`, batch parsed from
   `extend_<context>_<batch>` by splitting on `_` and taking index 2 (`:223-228`).
2. `image_encode` ∧ `text_encode` ∧ `detect` → `.multiFunctionSegmenter`.
   Checked **before** the `main` fallback, with the comment:
   *"checked before the `main` fallback because some asset variants ship a thin `main` graph
   alongside the trio."* (`:201-203`)
3. `main` → `.dynamic`.
4. otherwise → `.dynamic` with a warning log.

Also `PreparedModel.resolveCoreAIModelURL(from:)` (`:111-132`): if you hand it a non-`.aimodel`
path it looks for a sibling `<basename>.aimodel` and logs the redirect, else passes through.

### 2.2 `Runtime/NDArray+Helpers.swift` — the fill/read/flatten layer

Four public free functions + one extension. This is the whole "get Swift arrays in and out of
`NDArray`" story (`NDArray+Helpers.swift:15-139`):

```swift
public func resolvedStrides(descriptor: NDArrayDescriptor, shape: [Int]) throws -> [Int]

public func fillNDArray<T: BitwiseCopyable>(
    _ array: inout NDArray, as type: T.Type, with elements: some Collection<T>)

public func fillNDArray<T: BitwiseCopyable>(
    _ array: inout NDArray, as type: T.Type, count: Int, using generator: (Int) -> T)

public func readNDArray<T: BitwiseCopyable>(
    _ array: NDArray, as type: T.Type, count: Int) -> [T]

public func flattenAsFloat(_ array: NDArray) -> [Float]

public func flattenNDArray<T: BinaryFloatingPoint & BitwiseCopyable>(
    _ array: NDArray, as type: T.Type) -> [Float]
```

Three things worth stealing:

**(a) `Span` has no `Sequence` conformance.** `NDArray` shapes come back as `Span<Int>`, which
is non-escapable, so `.reduce` is unavailable. They hand-roll a product (`:25-33`):

```swift
extension Span where Element == Int {
    var product: Int {
        var result = 1
        for i in 0..<count { result *= self[i] }
        return result
    }
}
```

**(b) Never thread an `isFloat16` flag from the input side.** `flattenAsFloat` branches on the
*output array's own* `scalarType`, with the reason in the doc comment (`:81-95`):

> *"Output dtype can differ from the model's input dtype, so always inspect the array rather
> than threading an `isFloat16` flag from input descriptors."*

```swift
public func flattenAsFloat(_ array: NDArray) -> [Float] {
    switch array.scalarType {
    #if !((os(macOS) || targetEnvironment(macCatalyst)) && arch(x86_64))
    case .float16: return flattenNDArray(array, as: Float16.self)
    #endif
    case .float32: return flattenNDArray(array, as: Float.self)
    default: preconditionFailure("flattenAsFloat: unsupported scalar type \(array.scalarType)")
    }
}
```

Note the `#if` — **`Float16` does not exist on Intel macOS**. This guard recurs in at least four
places in the segmenter (see §11).

**(c) Contiguity fast path.** `flattenNDArray` checks whether the strides are already row-major
and, if so, does a flat copy; otherwise it walks an odometer of indices (`:101-139`). Core AI
outputs are *usually* contiguous, but not guaranteed — the framework returns
`preferredStrides` that "respect hardware alignment constraints" (`:12-14`), which can pad.

### 2.3 `Runtime/ResourceManaging` and `FileSize`

```swift
// CoreAIShared/Runtime/ResourceManaging.swift:10-22
public protocol ResourceManaging: Sendable {
    func loadResources() async throws
    func unloadResources() async
}
extension ResourceManaging {
    public func prewarmResources() async throws {
        try await loadResources()
        await unloadResources()
    }
}
```

`prewarmResources()` is a load-then-immediately-unload — it exists to warm the OS page cache /
JIT cache without holding memory.

```swift
// CoreAIShared/Runtime/FileSize.swift:17
extension URL { public func recursiveFileSizeInBytes() -> Int? }
```

Sums a directory tree via `FileManager.enumerator(at:includingPropertiesForKeys:[.fileSizeKey])`.
Doc comment is explicit: *"This reflects bytes on disk, not resident memory."* (`:15-16`).
This is what the `benchmark` tool reports as model size (§7.1).

### 2.4 `Bundle/` — the model-bundle format

**`BundleKind`** (`BundleKind.swift:11-16`) — the complete set of top-level model categories:

```swift
public enum BundleKind: String, Codable, Sendable, CaseIterable {
    case llm
    case vlm
    case diffusion
    case segmenter
}
```

Note what is **absent**: there is no `.speech`, no `.detector`. Speech and object detection do
**not** use `ModelBundle` at all — they load directories by convention (§5, §4). So the bundle
format covers 4 of the 6 model families in the repo.

**`ModelBundle`** (`ModelBundle.swift:23-35`) parses only the fields common to every kind:

```swift
public struct ModelBundle: Sendable {
    public let metadataVersion: String
    public let kind: BundleKind
    public let name: String
    public let bundlePath: URL
    public let userData: [String: String]?
    public let assets: [String: String]      // role -> filename
    public let raw: Data                      // full metadata.json, preserved
}
```

The `raw: Data` field is the extension point: *"Kind-specific config blocks (`language`, `vlm`,
`diffusion`, `segmenter`) are decoded by per-kind types in their respective runner modules …
using the preserved `raw` JSON."* (`ModelBundle.swift:10-15`).

Role resolution (`:39-62`):

```swift
public enum ComponentKey {
    public static let main = "main"
    public static let vision = "vision"
    public static let embedding = "embedding"
}
public var componentKeys: [String] { assets.keys.sorted() }
public func modelURL(for key: String) -> URL?
public func requireModelURL(for key: String) throws -> URL   // throws .missingField("assets.<key>")
public func verify() throws                                  // stat every declared asset
```

Version gate (`:158-161`): `metadata_version` **must** literally equal `"0.2"`; a missing key
defaults to `"0.1"` and then throws `.unsupportedVersion`.

Two error cases are worth calling out because they encode real user mistakes:

```swift
// ModelBundle.swift:88-92 — you pointed at the .aimodel, not the bundle dir
case .pointedAtModelAsset(let url):
    return "'\(url.lastPathComponent)' is a model asset, not a model bundle "
        + "directory. A model bundle directory contains metadata, a tokenizer, "
        + "and a model asset."
```

```swift
// ModelBundle.swift:103-109 — you ran `coreai-build compile` and didn't update metadata
case .missingAsset(let key, let path):
    return """
        Asset '\(key)' not found at \(path.path). \
        If you compiled this model with `xcrun coreai-build compile`, \
        update metadata.json "assets" to reference the compiled filename \
        (e.g. modelName.architectureName.aimodelc). See models/README.md#compiled-models
        """
```

The `.pointedAtModelAsset` check runs **before any filesystem read**, and the comment explains
why (`ModelBundle.swift:122-127`):

> *"a compiled `.aimodelc` is itself a directory holding its own unrelated metadata.json, which
> would otherwise parse as a bogus 0.1 bundle and surface a misleading 'unsupported
> metadata_version' error."*

So: **`.aimodel` and `.aimodelc` are directories, and `.aimodelc` contains its own
`metadata.json` with a different schema.** That is a genuinely load-bearing detail for anyone
writing a bundle loader.

**`FunctionMap`** (`FunctionMap.swift:17-41`) — the escape hatch for non-conventional function
names:

```swift
public struct FunctionMap: Codable, Sendable, Equatable {
    public let entries: [String: [String]]
    public init(_ entries: [String: [String]])
    public func names(for role: String) -> [String]   // [] if absent
    public func name(for role: String) -> String?     // first, or nil
}
```

Doc comment (`:6-16`) states the default is **convention, not configuration**:

> *"Most bundles don't need this — the runtime probes `AIModel`'s function list and matches
> against known role names by convention (`main`, `extend_<N>`, `load_embeddings`, etc.).
> `FunctionMap` is the override for bundles whose function names don't follow conventions, or
> where one logical role maps to multiple physical functions."*

Values are **always arrays**, even for single-name roles, "keeping the JSON shape uniform".

### 2.5 `Image/` — image ↔ tensor conversion

Two files. This is the pervasive practical pain point, and the repo solves it **entirely with
Core Graphics + Accelerate — no `CVPixelBuffer` anywhere in the non-LLM Swift.**

> **Finding:** grepping the whole `swift/Sources/` tree, `CVPixelBuffer` appears **zero** times.
> Every vision product takes a `CGImage` (or a `URL`/`CIImage` that it immediately converts to
> `CGImage`) and hand-builds a Float32 `NDArray`. There is no `CVPixelBuffer`-backed
> zero-copy path in this repo. If the Core AI SDK offers one, this repo does not use it.
> **UNVERIFIED** whether the SDK supports it.

#### `ImagePreprocessor` (`ImagePreprocessor.swift:37-270`)

```swift
public enum ImageStrategy: String, Codable, Sendable {
    case stretch
    case centerCrop = "center_crop"
    case pad
}

public struct ImagePreprocessor: Sendable {
    public let targetSize: CGSize
    public let mean: (CGFloat, CGFloat, CGFloat)
    public let std: (CGFloat, CGFloat, CGFloat)
    public let rescaleFactor: CGFloat

    public init(targetSize: CGSize,
                mean: (CGFloat, CGFloat, CGFloat),
                std: (CGFloat, CGFloat, CGFloat),
                rescaleFactor: CGFloat)

    public static let gemma3: ImagePreprocessor   // 896×896, ImageNet mean/std, rescale 1.0
    public static let clip:   ImagePreprocessor   // 336×336, CLIP mean/std,     rescale 1.0

    // NHWC RGBA Float32 — returns (Data, width, height)
    public func preprocess(imageURL: URL) throws -> (Data, Int, Int)
    public func preprocess(image: CIImage) throws -> (Data, Int, Int)
    public func preprocess(cgImage: CGImage) throws -> (Data, Int, Int)

    // Planar CHW Float32 — [3, H, W] flattened
    public func preprocessCHW(cgImage: CGImage) throws -> [Float]
    public func preprocessCHWCenterCrop(cgImage: CGImage) throws -> [Float]
    public func preprocessCHWPad(cgImage: CGImage) throws -> [Float]
    public func preprocessCHW(cgImage: CGImage, strategy: ImageStrategy) throws -> [Float]
}

public enum ImagePreprocessorError: Error, LocalizedError {
    case loadFailed(URL)
    case renderFailed
}
```

The exact presets (`ImagePreprocessor.swift:58-72`):

```swift
/// Gemma 3 / SigLIP preset (ImageNet normalization, 896x896).
public static let gemma3 = ImagePreprocessor(
    targetSize: CGSize(width: 896, height: 896),
    mean: (0.485, 0.456, 0.406), std: (0.229, 0.224, 0.225), rescaleFactor: 1.0)

/// CLIP preset (336x336).
public static let clip = ImagePreprocessor(
    targetSize: CGSize(width: 336, height: 336),
    mean: (0.48145466, 0.4578275, 0.40821073),
    std: (0.26862954, 0.26130258, 0.27577711), rescaleFactor: 1.0)
```

**Pixel format decisions, all explicit and all worth stealing:**

- Color space is hard-pinned to `CGColorSpace.sRGB` in *both* the resize and the normalize
  contexts (`:197`, `:222`). Not device RGB — sRGB, so results are display-independent.
- Bitmap format is `bitsPerComponent: 8`, `bytesPerRow: width * 4`,
  `bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue` (`:204-208`) — RGBA8 with alpha ignored.
- `ctx.interpolationQuality = .high` with the doc claim it *"matches PIL BICUBIC closely"*
  (`:26-27`, `:213`). This is the PyTorch-parity lever.
- Output is `[H, W, 4]` Float32 NHWC with **alpha zero-filled** (`:264-265`), and the doc says
  *"The caller transposes to `[1, 3, H, W]` (NCHW) before binding to a vision encoder input."*
  (`:28-29`)

The normalization is a two-pass vDSP formula, `(pixel * rescale − mean) / std`, refactored into
a single fused multiply-add per channel (`ImagePreprocessor.swift:251-265`):

```swift
let scale = Float(rescaleFactor) / 255.0
let means: [Float] = [Float(mean.0), Float(mean.1), Float(mean.2)]
let stds:  [Float] = [Float(std.0),  Float(std.1),  Float(std.2)]

var channel = [Float](repeating: 0, count: pixelCount)
let n = vDSP_Length(pixelCount)
for c in 0..<3 {
    var a = scale / stds[c]
    var b = -means[c] / stds[c]
    vDSP_vfltu8(rawPixels.advanced(by: c), 4, &channel, 1, n)          // UInt8 -> Float, stride 4
    vDSP_vsmsa(channel, 1, &a, &b, dstBase.advanced(by: c), 4, n)      // out = in*a + b, stride 4
}
var zero: Float = 0
vDSP_vfill(&zero, dstBase.advanced(by: 3), 4, n)                        // alpha = 0
```

Note `/255.0` is folded into `scale` — so `rescaleFactor: 1.0` means "map [0,255]→[0,1]".
A caller wanting raw `[0,255]` pixels would pass `rescaleFactor: 255.0`.

The NHWC→CHW transpose is a naive triple loop, not vDSP (`:114-127`):

```swift
public func preprocessCHW(cgImage: CGImage) throws -> [Float] {
    let (data, w, h) = try preprocess(cgImage: cgImage)
    let pixelCount = w * h
    var chw = [Float](repeating: 0, count: 3 * pixelCount)
    data.withUnsafeBytes { rawSrc in
        let src = rawSrc.bindMemory(to: Float.self)
        for c in 0..<3 {
            for i in 0..<pixelCount { chw[c * pixelCount + i] = src[i * 4 + c] }
        }
    }
    return chw
}
```

**Strategy semantics, exactly as implemented:**

| Strategy | Implementation | Cite |
|---|---|---|
| `.stretch` | Draw source into a `targetW × targetH` context filling the whole rect. Aspect ratio **not** preserved. | `:100-107` |
| `.centerCrop` | `scale = srcW < srcH ? targetW/srcW : targetH/srcH` (shortest edge → target), render at that size, then `cropping(to:)` a centered `targetW × targetH` rect, then `preprocessCHW`. **Renders twice.** | `:131-155` |
| `.pad` | `scale = srcW > srcH ? targetW/srcW : targetH/srcH` (longest edge → target), draw into a `targetW × targetH` canvas at offset `((targetW−resizedW)/2, (targetH−resizedH)/2)`. Remainder is context-zero → **black**, not mean-color. | `:159-180` |

Gotcha: `.pad` pads with zeros in *pixel* space (before normalization), so the padding becomes
`(0 − mean)/std` after normalization, **not** zero in tensor space. If a model expects zero-padding
in tensor space this is subtly wrong. **UNVERIFIED** whether any shipped model cares.

Gotcha: `preprocessCHWCenterCrop` computes `cropX/cropY` as `(resizedW − targetW) / 2` — integer
division, and if the source is already smaller than the target in the long dimension this goes
negative and `cropping(to:)` returns `nil` → `.renderFailed`.

**EXIF / orientation:** there is **no** orientation handling anywhere in `ImagePreprocessor`.
`CIImage(contentsOf:)` (`:80`) does apply EXIF orientation; `CGImageSourceCreateImageAtIndex`
(used by the CLI tools, §7) does **not**. So the same JPEG can be preprocessed two different ways
depending on which entry point you use. This is a real, unfixed inconsistency in the repo.

#### `CGImageUtils` (`CGImageUtils.swift:11-59`)

```swift
public enum CGImageUtils {
    public static func resize(_ image: CGImage, to side: Int) -> CGImage?
    public static func toNormalizedPlanarRGB(_ image: CGImage) throws -> [Float]
}
```

Used by the diffusion pipeline (img2img). Differences from `ImagePreprocessor` worth noting:

- `resize` is **square-only** (`to side: Int`) and uses `CGImageAlphaInfo.premultipliedLast`, not
  `noneSkipLast` (`:19`).
- `toNormalizedPlanarRGB` hardcodes the **diffusion** normalization `(pixel / 127.5) − 1.0`,
  i.e. `[0,255] → [−1,1]`, and does the whole planar conversion in **four vDSP calls total**
  (`:48-56`) rather than per-channel loops:

```swift
result.withUnsafeMutableBufferPointer { buf in
    let base = buf.baseAddress!
    vDSP_vfltu8(ptr,     4, base,                  1, vDSP_Length(pixelCount))
    vDSP_vfltu8(ptr + 1, 4, base + pixelCount,     1, vDSP_Length(pixelCount))
    vDSP_vfltu8(ptr + 2, 4, base + 2 * pixelCount, 1, vDSP_Length(pixelCount))
    var scale: Float = 1.0 / 127.5
    var bias:  Float = -1.0
    vDSP_vsmsa(base, 1, &scale, &bias, base, 1, vDSP_Length(3 * pixelCount))
}
```

Because the de-interleave already writes planar, the single `vDSP_vsmsa` covers all
`3 * pixelCount` elements at once — **this is the faster of the two implementations** and the
one to copy when you don't need per-channel mean/std.

### 2.6 `Logger/CLILogger` (`Logger.swift:11-48`)

```swift
public struct CLILogger {
    public static var level: Int                              // Atomic<Int>, asserts >= 0
    public static func log(_ message: String, component: String? = nil, level: Int = 1)
    public static func isEnabled(at level: Int) -> Bool        // Self.level >= level
    public static var isVerbose: Bool                          // Self.level >= 1
}
```

Backed by `Synchronization.Atomic<Int>` with `.acquiring`/`.releasing` orderings (`:12-22`).
Every CLI tool sets `CLILogger.level` from a `--verbose` flag. Output goes to `print`, i.e.
stdout — not `os_log`, so it is CLI-oriented, not app-oriented.

---

## 3. `CoreAISegmentation` — the `CoreAIImageSegmenter` target

Nine files, ~2,400 lines. The richest non-LLM product and the one WWDC26 sessions 325/326
demoed. Zero third-party deps.

```
CoreAIImageSegmenter/ImageSegmenter.swift                        176 L  <- public façade
CoreAIImageSegmenter/ImageSegmentationEngine.swift              1292 L  <- the engine
CoreAIImageSegmenter/PointQuery.swift                             84 L
CoreAIImageSegmenter/TextQuery.swift                              33 L
CoreAIImageSegmenter/SegmentationRuntimeError.swift               45 L
CoreAIImageSegmenter/Preprocessing/CLIPTokenizer.swift           220 L
CoreAIImageSegmenter/Postprocessing/SegmentationOutputs.swift    218 L
CoreAIImageSegmenter/Postprocessing/SegmentationPostprocessor.swift 311 L
CoreAIImageSegmenter/Postprocessing/SegmentationVisualization.swift 251 L
```

### 3.1 Public API surface — complete

```swift
// ImageSegmenter.swift:34-176
public struct ImageSegmenter {
    public init(engine: CoreAISegmentationEngine, tokenizer: CLIPTokenizer? = nil) throws
    public init(engine: CoreAISegmentationEngine, tokenizerFolder: URL?) throws
    public init(resourcesAt path: String,
                parameters: SegmentationParameters = .default) async throws

    public func warmup() async throws

    public func segment(image: CGImage, textQuery: TextQuery,
                        parameters: SegmentationParameters = .default) async throws -> SegmentationResponse
    public func segment(image: CGImage, prompt: String,
                        parameters: SegmentationParameters = .default) async throws -> SegmentationResponse
    public func segment(image: CGImage, pointQuery: PointQuery = PointQuery(),
                        parameters: SegmentationParameters = .default) async throws -> SegmentationResponse
}
```

> **Correction to the prior notes file.** `apple-coreai-models.md` §14 flags the
> `ImageSegmenter(resourcesAt:)` snippet in `models/sam3/README.md` as *"aspirational/stale"*
> because it did not match the source. That is **no longer true for the initializer**:
> `init(resourcesAt path: String, parameters:) async throws` genuinely exists at
> `ImageSegmenter.swift:163-175`. The README's `import ImageSegmenter` is still wrong — the
> module is `CoreAIImageSegmenter` (product `CoreAISegmentation`).

```swift
// ImageSegmentationEngine.swift:23-134
public struct CoreAISegmentationEngine {
    public var supportsTextQuery: Bool
    public var supportsPointQuery: Bool
    public init(parameters: SegmentationParameters, modelURL: URL) async throws
    public func warmup() async throws
    public func segment(image: CGImage, textQuery: TextQuery,
                        parameters: SegmentationParameters) async throws -> SegmentationOutput
    public func segment(image: CGImage, pointQuery: PointQuery,
                        parameters: SegmentationParameters) async throws -> SegmentationOutput
}
```

```swift
// TextQuery.swift:26-33
public enum TextQuery: Sendable {
    case prompt(String)              // tokenized by ImageSegmenter; engine THROWS on this
    case tokens([[Int32]])           // [batch, contextLength]
    case embeddings([[[Float]]])     // [batch, seqLen, hiddenSize]
}

// PointQuery.swift:38-84
public struct PointQuery: Sendable {
    public enum Label: Int32, Sendable {
        case background = 0, foreground = 1, boxTopLeft = 2, boxBottomRight = 3
    }
    public struct Point: Sendable {
        public var x: Float; public var y: Float; public var label: Label
        public init(x: Float, y: Float, label: Label = .foreground)
    }
    public var queries: [[Point]]                 // outer = Q, inner = P
    public init(queries: [[Point]] = [])
    public init(points: [Point])                  // single query fusing all points
}
```

```swift
// SegmentationOutputs.swift:12-218
public struct SegmentationResponse: Sendable {
    public let segments: [Segment]                       // sorted by score desc
    public let probabilityMap: SemanticSegmentationMap?  // nil if no semantic head
}
public struct SemanticSegmentationMap: Sendable {
    public var probabilities: [Float]                    // row-major, H*W, sigmoid [0,1]
    public let width: Int; public let height: Int
    public subscript(x: Int, y: Int) -> Float { get set }
}
public struct Segment: Sendable {
    public let mask: [Bool]                              // input-image resolution, row-major
    public let maskWidth: Int; public let maskHeight: Int
    public let box: CGRect                               // ORIGIN DIFFERS BY PLATFORM — see §11
    public let score: Float                              // [0,1]
}
public struct SegmentationOutput: Sendable {             // raw engine IR
    public let predictedMasks: [Float]        // [B, Q, mH, mW] logits (pre-sigmoid)
    public let masksShape: [Int]
    public let predictedBoxes: [Float]        // [B, Q, 4] XYXY normalized; [] for EfficientSAM
    public let predictedLogits: [Float]       // [B, Q]; [] when predictedScores used
    public let predictedScores: [Float]       // [B, Q] already in [0,1] (EfficientSAM IOU)
    public let presenceLogits: [Float]        // [B, 1]; [] -> treated as 1.0
    public let semanticSegment: [Float]       // [B, 1, H, W]; [] when no semantic head
    public let semanticSegmentShape: [Int]
}
public struct SegmentationParameters: Sendable {
    public var maskThreshold: Float                      // default 0.5
    public var maxSegments: Int                          // default 5
    public var normalizationMeans: (CGFloat, CGFloat, CGFloat)  // default (0.5, 0.5, 0.5)
    public var normalizationStds:  (CGFloat, CGFloat, CGFloat)  // default (0.5, 0.5, 0.5)
    public var tokenizerContextLength: Int               // default 77
    public static let `default`: SegmentationParameters
}
```

```swift
// SegmentationRuntimeError.swift:11-45
public enum SegmentationRuntimeError: Error, LocalizedError, Sendable {
    case modelLoadFailed(String), outputMissing(String), unsupportedEngine(String)
    case notLoaded, invalidConfiguration(String), bundleNotFound(String), modelNotFound(String)
}
```

### 3.2 `CoreAISegmentationEngine` — two backends, autodetected

The doc comment states the contract (`ImageSegmentationEngine.swift:13-22`):

> *"Supports two asset shapes, autodetected at init time:*
> - *Single-function — one `main` graph that consumes the image (and a text or point prompt) and
>   emits all detection outputs in one call. Produced by the baseline SAM3 export and EfficientSAM.*
> - *Multi-function — three graphs (`image_encode`, `text_encode`, `detect`) wired together at
>   runtime. Produced by the SAM3 lite export. The engine pipes the encoder outputs into the
>   detector and returns the same `SegmentationOutput` shape as the single-function path."*

Dispatch is **delegated to `PreparedModel`**, not re-probed (`:44-84`):

```swift
public init(parameters: SegmentationParameters, modelURL: URL) async throws {
    let preparedAsset = try await PreparedModel.prepare(at: modelURL)
    let model = preparedAsset.model
    // `PreparedModel` already classified the asset (and used that classification to pick
    // the compute-unit specialization at load time). Reuse it as the single source of
    // truth for multi- vs single-function dispatch rather than re-probing here.
    if preparedAsset.structure == .multiFunctionSegmenter {
        guard let imageEncodeDescriptor = model.functionDescriptor(for: GraphNames.imageEncode),
              let textEncodeDescriptor  = model.functionDescriptor(for: GraphNames.textEncode),
              let detectDescriptor      = model.functionDescriptor(for: GraphNames.detect)
        else { throw ... }
        self.backend = .multi(try await MultiFunctionContext(...))
        return
    }
    guard let mainDescriptor = model.functionDescriptor(for: GraphNames.main) else { throw ... }
    self.backend = .single(try await SingleFunctionContext(model: model, descriptor: mainDescriptor))
}
```

**Capability flags fall straight out of tensor discovery** (`:28-40`):

```swift
public var supportsTextQuery: Bool {
    switch backend {
    case .single(let s): return s.textInputName != nil
    case .multi:         return true
    }
}
public var supportsPointQuery: Bool {
    switch backend {
    case .single(let s): return s.pointsInputName != nil && s.pointLabelsInputName != nil
    case .multi:         return false      // the 3-function split is text-only
    }
}
```

**The matrix that results:**

| Asset | Structure | Compute unit | Text query | Point query | Embeddings query |
|---|---|---|---|---|---|
| SAM3 baseline (`main`) | `.dynamic` | GPU | ✅ | ❌ | ✅ if `embed`/`text_feat` input exists |
| SAM3 lite (`image_encode`/`text_encode`/`detect`) | `.multiFunctionSegmenter` | **Neural Engine** | ✅ | ❌ | ❌ *(throws — see below)* |
| EfficientSAM (`main`) | `.dynamic` | GPU | ❌ | ✅ | ❌ |

The multi-function path explicitly rejects `.embeddings` (`:855-859`):

```swift
case .embeddings:
    throw SegmentationRuntimeError.unsupportedEngine(
        "Multi-function segmentation assets accept token IDs only — "
            + "the text_encode graph already projects them internally.")
```

**The multi-function run loop** — this is the orchestration pattern WWDC26 session 325 describes
(`ImageSegmentationEngine.swift:871-920`). Note that `detect`'s inputs are the *unmodified
`NDArray` outputs* of the two encoders — no round-trip through Swift arrays:

```swift
private func runMultiFunctionInference(
    state: MultiFunctionContext, imageArray: NDArray, textArray: NDArray
) async throws -> SegmentationOutput {
    var imageOutputs = try await state.imageEncode.run(inputs: [state.imageInputName: imageArray])
    guard let backboneFeatures = imageOutputs.remove(state.backboneFeaturesOutputName)?.ndArray
    else { throw ... }

    var textOutputs = try await state.textEncode.run(inputs: [state.textInputName: textArray])
    guard let textFeatures = textOutputs.remove(state.textFeaturesOutputName)?.ndArray
    else { throw ... }

    var detectOutputs = try await state.detect.run(inputs: [
        state.backboneFeaturesInputName: backboneFeatures,
        state.textFeaturesInputName:      textFeatures,
    ])
    ...
}
```

Doc comment on that function (`:869-870`): *"Outputs are pulled out of each `function.run`
return dict — never pre-allocated."* That contrasts with `CoreAISpeech`, which **does**
pre-allocate via `InferenceFunction.MutableViews` (§5) — two different Core AI output styles
live in the same repo.

> ⚠ **The engine does not cache `backboneFeatures` across calls.** Every `segment()` re-runs
> `image_encode`. The WWDC26 session-325 "76% faster second inference" story is about *reusing
> the image encoding when only the text prompt changes* — but `CoreAISegmentationEngine` as
> written re-encodes the image every time. To get the speedup you would have to hold the
> `image_encode` output yourself; the engine exposes no API for that.
> **This is a genuine gap between the session narrative and the shipped code.**

### 3.3 Tensor-name discovery — the duck-typing layer

Neither product hardcodes tensor names. Both discover them with substring matching over
`descriptor.inputNames` / `outputNames`. Complete set for the segmenter
(`ImageSegmentationEngine.swift:1193-1270`):

```swift
static func findImageInputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("pixel") || l.contains("image") }
}
static func findTextInputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased()
        // Match input_id / token / text, but exclude text_features (a `detect` input that
        // also contains "text") so it isn't mistaken for the token input.
        return (l.contains("input_id") || l.contains("token") || l.contains("text")) && !l.contains("feat") }
}
static func findEmbeddingsInputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("embed") || l.contains("text_feat") }
}
static func findPointsInputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("point") && !l.contains("label") }
}
static func findPointLabelsInputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("point") && l.contains("label") }
}
static func findBackboneFeaturesName(in names: [String]) -> String? {
    names.first { $0.lowercased().contains("backbone") }
}
static func findTextFeaturesName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("text_feat") || l == "text_features" }
}
static func findMasksOutputName(in names: [String])   -> String? { names.first { $0.lowercased().contains("mask") } }
static func findBoxesOutputName(in names: [String])   -> String? { names.first { $0.lowercased().contains("box") } }
static func findLogitsOutputName(in names: [String])  -> String? {
    names.first { let l = $0.lowercased(); return l.contains("logit") && !l.contains("presence") }
}
static func findPresenceOutputName(in names: [String])-> String? { names.first { $0.lowercased().contains("presence") } }
static func findIouScoresOutputName(in names: [String]) -> String? {
    names.first { let l = $0.lowercased(); return l.contains("iou") || (l.contains("score") && !l.contains("logit")) }
}
static func findSemanticOutputName(in names: [String])-> String? { names.first { $0.lowercased().contains("semantic") } }
```

Detector equivalents (`ObjectDetector.swift:316-332`) — same idea, three names:
`pixel|image`, `logit`, `box`.

**Why this matters for a guide:** the whole contract between the Python exporter and the Swift
runner is *naming conventions inside the `.aimodel`*, not a schema. The engine's error messages
always print `descriptor.inputNames` / `outputNames` so a failed match tells you exactly what
the model actually exposes. The three `!l.contains(...)` negative filters are the accumulated
scar tissue — `text_features` vs `input_ids`, `presence_logits` vs `pred_logits`,
`iou_scores` vs `pred_logits`.

Note `names.first { … }` — **`inputNames` order decides ties.** If a model has two inputs both
matching `image`, you silently get whichever the SDK lists first.

### 3.4 Validation, sentinel padding, best-of-K, segment-everything

The point path is where the engine hides the most work.

**Static shapes drive everything** (`:612-651`). `batched_points` is `[B, Q, P, 2]`,
`batched_point_labels` is `[B, Q, P]`; ranks and the three shared dims are cross-checked, and
`[B, Q, P]` come from the *model*, not the caller.

**Sentinel padding** (`:653-705`). Unused slots are filled with `-1.0` in both tensors:

> *"Sentinel `-1` marks unused slots: the EfficientSAM prompt encoder routes them to its
> `invalid_points` embedding so they contribute nothing to the mask. The user's queries fill
> batch slot 0 and replicate identically across any additional batches."* (`:655-657`)

Coordinates are scaled to model space at fill time: `point.x * scaleX` where
`scaleX = modelSize.width / imageWidth` (`:558-559`, `:676-677`).

**Segment-everything** (`:1075-1108`): an empty `PointQuery` becomes a `gridSide × gridSide`
grid of foreground points at pixel centers, where `gridSide = sqrt(queryCount)`:

```swift
if pointQuery.queries.isEmpty {
    let gridSide = Int(Double(queryCount).squareRoot())
    guard gridSide * gridSide == queryCount else {
        throw SegmentationRuntimeError.invalidConfiguration(
            "Segment-everything requires a perfect-square num_queries (got \(queryCount)).")
    }
    ...
    let x = imageWidth  * (Float(col) + 0.5) / Float(gridSide)
    let y = imageHeight * (Float(row) + 0.5) / Float(gridSide)
```

**So `--num-queries` must be a perfect square if you want segment-everything to work.** That
constraint is invisible from the Python export side.

**Validation** (`:1110-1169`) checks, per query: non-empty, finite coords, coords within
`[0, imageW] × [0, imageH]`, at most one `.boxTopLeft`, at most one `.boxBottomRight`, and the
two counts equal. The size errors name the exact re-export flag:

```swift
"PointQuery has \(queries.count) queries but model expects ≤ \(queryCount). "
    + "Re-export with --num-queries \(queries.count) (or higher)."
"Query \(queryIndex) has \(query.count) points but model expects ≤ \(pointsPerQuery). "
    + "Re-export with --num-pts \(query.count) (or higher)."
```

**Best-of-K** (`:979-1029`). EfficientSAM emits `[B, Q, K, H, W]` masks and `[B, Q, K]` IOU
scores (K = 3 mask candidates per prompt). `reduceBestOfK` picks the argmax-K per `(B, Q)` and
collapses to `[B, Q, H, W]` / `[B, Q]`. It is a `static` pure-data function specifically so it
can be unit-tested without `NDArray` (`:996-998`).

**Phantom-query trimming** (`:1037-1063`). `sliceUserQueries` drops the sentinel-padded query
slots so the postprocessor never surfaces masks generated from `invalid_points`. No-op when
`userQueryCount == queryCount` (the segment-everything case).

**Boxes for point prompts** (`:1174-1189`): `extractBoxesFromPointQuery` synthesizes the box
output EfficientSAM doesn't produce, echoing the user's own box prompt back normalized to [0,1];
queries without a box pair get zeros.

**Two different image normalizations in one file.** The text path uses
`parameters.normalizationMeans/Stds` (default 0.5/0.5/0.5 — CLIP/SAM3), `:940-945`. The point
path hardcodes identity, and says why (`:573-575`):

> *"EfficientSAM bakes `(x - mean) / std` into the graph, so we feed raw `[0, 1]` pixels
> (`rescaleFactor=1/255`, identity mean/std)."*

```swift
let preprocessor = ImagePreprocessor(
    targetSize: CGSize(width: modelWidth, height: modelHeight),
    mean: (0, 0, 0), std: (1, 1, 1), rescaleFactor: 1.0)   // ImageSegmentationEngine.swift:588-593
```

(The comment says `rescaleFactor=1/255` but the code passes `1.0`; `ImagePreprocessor` already
divides by 255 internally, so the *behavior* is `[0,1]` as described — only the comment's
notation is loose.)

Both paths read spatial dims from the descriptor as `shape[2]` = height, `shape[3]` = width,
i.e. **NCHW is assumed everywhere** (`:586-587`, `:938-939`).

### 3.5 Postprocessing (`SegmentationPostprocessor.swift`)

```swift
public enum SegmentationPostprocessor {
    public static func decode(output: SegmentationOutput, inputSize: CGSize,
                              parameters: SegmentationParameters = .default) -> SegmentationResponse
    public static func sigmoid(_ x: Float) -> Float
    public static func bilinearUpsampleToBool(source: [Float],
        sourceHeight: Int, sourceWidth: Int,
        destinationHeight: Int, destinationWidth: Int, threshold: Float) -> [Bool]
    public static func bilinearUpsampleToFloat(source: [Float],
        sourceHeight: Int, sourceWidth: Int,
        destinationHeight: Int, destinationWidth: Int) -> [Float]
}
```

Scoring (`:11-15`, `:108-132`):

```
combined_score = sigmoid(pred_logit) * sigmoid(presence_logit)     // SAM3
score          = predictedScores[q]                                // EfficientSAM (IOU, already [0,1])
```
Presence is *shared across all queries* (`:114-116`) and treated as `1.0` when absent.
The doc says the formula *"matches SAM3's test_sam3.py"* (`:11`).

**Threshold AFTER upsampling — the single most transferable postprocessing lesson here**
(`:180-184`):

> *"Threshold AFTER upsampling: pre-thresholding then resampling locks in nearest-neighbor
> staircase artifacts (the binary edge propagates straight through any kernel), which is
> especially obvious for the SAM3 lite export — its mask grid is ~10× lower resolution than
> the baseline's."*

So the mask pipeline is: `logits → sigmoid → bilinear upsample to input resolution → threshold`.

The sampling convention is spelled out (`:236-243`) — **PIL `BILINEAR` / `align_corners=False`**:

```
src_coord = ((dst + 0.5) * srcSize/dstSize) - 0.5      // clamped into [0, srcSize-1]
```

`decode` is defensively guarded: seven early-return checks against malformed engine output
(`:34-65`), each returning an empty `SegmentationResponse` rather than crashing. It only ever
reads `batchIndex = 0` (`:38`) — **the postprocessor is single-batch even though the tensors
carry a batch dim.**

### 3.6 `CLIPTokenizer` (`Preprocessing/CLIPTokenizer.swift`)

```swift
public struct CLIPTokenizer: Sendable {
    public let encoder: [String: Int32]
    public static let sotTokenId: Int32 = 49406
    public static let eotTokenId: Int32 = 49407
    public init(folder: URL) throws                                  // reads folder/tokenizer.json
    public init(vocab: [String: Int32], merges: [(String, String)]) throws
    public func encode(_ text: String, contextLength: Int = 77) -> [Int32]
}
```

Why it exists (`:8-14`):

> *"swift-transformers' AutoTokenizer doesn't support CLIP's BPE variant (specifically the
> `end_of_word_suffix: "</w>"` flag), so we ship this CLIP-specific encoder. The on-disk layout
> still matches HF conventions — only the loader is custom."*

That is **why `CoreAIImageSegmenter` has no swift-transformers dependency**.

Implementation details worth citing:
- `byteEncoder` reproduces Python's `bytes_to_unicode()` exactly (`:29-50`).
- Padding uses **`eotTokenId`, not 0** — *"Pads with `eotTokenId` to match SAM3's
  `torch.zeros`-then-fill behavior."* (`:91-92`). Truncation force-overwrites the last slot with
  EOT (`:101-104`).
- The pre-tokenizer regex is reimplemented by hand as a character scanner (`:125-169`), matching
  SAM3's `|'s|'t|'re|'ve|'m|'ll|'d|[\p{L}]+|[\p{N}]|[^\s\p{L}\p{N}]+`. Note `[\p{N}]` is
  **one digit at a time** — "2024" becomes four tokens.
- Text is `whitespaceClean(...).lowercased()` before tokenizing (`:94`).
- BPE merge loop is O(n²) per token, no caching (`:171-212`).

### 3.7 Complete copyable usage — segmentation

**(a) Bundle-directory path (simplest; SAM3 text-guided):**

```swift
import CoreAIImageSegmenter    // NOTE: module is CoreAIImageSegmenter, product is CoreAISegmentation
import CoreGraphics

// Bundle dir must contain: metadata.json (kind: "segmenter"), the .aimodel named by
// assets.main, and a tokenizer/ subdir with tokenizer.json.
let segmenter = try await ImageSegmenter(resourcesAt: "~/models/sam3_lite_336_w4_static")
try await segmenter.warmup()

let src = CGImageSourceCreateWithURL(imageURL as CFURL, nil)!
let cgImage = CGImageSourceCreateImageAtIndex(src, 0, nil)!

let response = try await segmenter.segment(image: cgImage, prompt: "cat")
for segment in response.segments {
    print("score=\(segment.score) box=\(segment.box)")
    // segment.mask is [Bool], row-major, segment.maskWidth × segment.maskHeight
    // == the INPUT image resolution (already upsampled).
}
if let map = response.probabilityMap {
    print("semantic map \(map.width)×\(map.height), p(100,100) = \(map[100, 100])")
}
```

**(b) Explicit engine + tuned parameters:**

```swift
var params = SegmentationParameters()
params.maskThreshold = 0.35          // default 0.5
params.maxSegments = 20              // default 5
params.tokenizerContextLength = 77   // CLIP max
// params.normalizationMeans/Stds default to (0.5,0.5,0.5) — correct for SAM3/CLIP.

let modelURL = URL(fileURLWithPath: "/path/to/sam3.aimodel")
let engine = try await CoreAISegmentationEngine(parameters: params, modelURL: modelURL)
print("text:", engine.supportsTextQuery, "point:", engine.supportsPointQuery)

let segmenter = try ImageSegmenter(engine: engine,
                                   tokenizerFolder: URL(fileURLWithPath: "/path/to/tokenizer"))
let response = try await segmenter.segment(image: cgImage, prompt: "a red car", parameters: params)
```

**(c) Reusing a tokenization across many images (skip the BPE work):**

```swift
let tokenizer = try CLIPTokenizer(folder: tokenizerFolder)
let ids = tokenizer.encode("cat", contextLength: 77)     // [Int32], length 77, EOT-padded
let segmenter = try ImageSegmenter(engine: engine, tokenizer: tokenizer)
for image in images {
    let r = try await segmenter.segment(image: image, textQuery: .tokens([ids]))
    ...
}
```

**(d) Point prompts (EfficientSAM):**

```swift
let engine = try await CoreAISegmentationEngine(parameters: .default, modelURL: efficientSamURL)
let segmenter = try ImageSegmenter(engine: engine)        // no tokenizer needed

// Single click
let click = PointQuery(points: [.init(x: 320, y: 240)])                    // label defaults .foreground

// Box prompt — ONE query, TWO points
let box = PointQuery(points: [
    .init(x: 100, y: 100, label: .boxTopLeft),
    .init(x: 400, y: 300, label: .boxBottomRight),
])

// Click + negative click — still ONE query
let refined = PointQuery(points: [
    .init(x: 320, y: 240, label: .foreground),
    .init(x: 100, y: 400, label: .background),
])

// N INDEPENDENT prompts — N queries, 1 point each
let multi = PointQuery(queries: [[.init(x: 100, y: 100)], [.init(x: 300, y: 300)]])

// Segment everything — requires a perfect-square num_queries in the export
let everything = PointQuery()

let response = try await segmenter.segment(image: cgImage, pointQuery: box)
// EfficientSAM: segment.box echoes YOUR box prompt (or .zero); segment.score is an IOU score.
```

**(e) Rendering results:**

```swift
if let overlay = SegmentationVisualization.renderInstanceMasks(onto: cgImage,
                                                              segments: response.segments) { ... }
if let map = response.probabilityMap,
   let heat = SegmentationVisualization.renderSemanticOverlay(onto: cgImage, map: map) { ... }
// boxes must be TOP-LEFT origin regardless of platform for this call:
if let boxed = SegmentationVisualization.renderPromptBoxes(onto: cgImage, boxes: [rect],
                                                           color: (255, 0, 0), lineWidth: 3) { ... }
```

`SegmentationVisualization` public API (`SegmentationVisualization.swift:17-203`):
`renderSemanticOverlay(onto:map:) -> CGImage?` (blue→green→red heat map, alpha `prob*200`,
max ~78% opacity), `renderInstanceMasks(onto:segments:) -> CGImage?` (evenly-spaced hue wheel
`hsvToRGB(h: idx/total, s: 0.85, v: 0.95)`, alpha 153 ≈ 60%, index 0 drawn on top),
`renderPromptBoxes(onto:boxes:color:lineWidth:) -> CGImage?`.

Y-axis handling is documented per-function and is **not uniform**: `renderSemanticOverlay` and
`renderInstanceMasks` say *"CGImage pixel data is stored top-to-bottom (row 0 = top), matching
the segmentation map, so no vertical flip is needed"* (`:45-46`), while `renderPromptBoxes`
explicitly flips (`:185`, `:194-199`). And `Segment.box` from the postprocessor is *already*
bottom-left on macOS (§11). Mixing these is an easy way to draw upside-down boxes.

---

## 4. `CoreAIObjectDetection` — the `CoreAIObjectDetector` target

Three files, 633 lines. The **simplest complete example in the repo** — if you want to show
someone "run a vision model on Core AI" in one file, this is it.

```
CoreAIObjectDetector/ObjectDetector.swift          356 L
CoreAIObjectDetector/DetectionPostprocessor.swift  143 L
CoreAIObjectDetector/DetectionOutputs.swift        134 L
```

### 4.1 Public API — complete

```swift
// ObjectDetector.swift:14-333
public struct ObjectDetector {
    public init(resourcesAt path: String) async throws
    public func warmup(imageCount: Int = 1,
                       parameters: DetectionParameters = .default) async throws
    public func detect(image: CGImage) async throws -> [DetectedObject]
    public func detect(image: CGImage, parameters: DetectionParameters) async throws -> [DetectedObject]
    public func detect(images: [CGImage]) async throws -> [[DetectedObject]]
    public func detect(images: [CGImage], parameters: DetectionParameters) async throws -> [[DetectedObject]]
}

// DetectionOutputs.swift:33-134
public struct DetectedObject: Sendable {
    public let boundingBox: CGRect      // pixel coords, TOP-LEFT origin on every platform
    public let labelIndex: Int
    public let label: String
    public let confidence: Float        // [0,1]
    public init(boundingBox: CGRect, labelIndex: Int, label: String, confidence: Float)
}

public struct DetectionParameters: Sendable {
    public var threshold: Float                                  // default 0.3
    public var maxDetections: Int                                // default 100
    public var normalizationMeans: (CGFloat, CGFloat, CGFloat)   // default (0.485, 0.456, 0.406) ImageNet
    public var normalizationStds:  (CGFloat, CGFloat, CGFloat)   // default (0.229, 0.224, 0.225) ImageNet
    public var classLabels: [Int: String]                        // default ObjectDetectionLabels.coco
    public var inputHeight: Int                                  // default 800
    public var inputWidth:  Int                                  // default 800
    public static let `default`: DetectionParameters
}

public enum ObjectDetectionLabels {
    public static let coco: [Int: String]    // 91 entries, 0:"N/A" .. 90:"toothbrush", with N/A holes
}

// ObjectDetector.swift:338-356
public enum DetectionRuntimeError: Error, LocalizedError, Sendable {
    case modelLoadFailed(String), outputMissing(String), invalidConfiguration(String), modelNotFound(String)
}
```

Non-public but structurally important (`DetectionOutputs.swift:19-30`, `DetectionPostprocessor.swift:16`):
`struct DetectionOutput` (`logits [B,Q,C]`, `logitsShape`, `predictedBoxes [B,Q,4]`) and
`enum DetectionPostprocessor` are **internal** — unlike the segmenter, whose equivalents are
`public`. So you cannot plug your own postprocessor into `ObjectDetector` without forking it.

### 4.2 How it differs from the segmenter — four notable divergences

**(1) It does NOT use `ModelBundle`, and does NOT use `PreparedModel`.** It takes a raw
`.aimodel` path and calls `AIModel(contentsOf:)` with **no `SpecializationOptions` at all**
(`ObjectDetector.swift:23-34`):

```swift
public init(resourcesAt path: String) async throws {
    let modelURL = URL(fileURLWithPath: NSString(string: path).expandingTildeInPath)
    var isDirectory: ObjCBool = false
    guard FileManager.default.fileExists(atPath: modelURL.path, isDirectory: &isDirectory),
        isDirectory.boolValue,
        modelURL.pathExtension == "aimodel"
    else { throw DetectionRuntimeError.modelNotFound(modelURL.path) }
    let model = try await AIModel(contentsOf: modelURL)
    ...
}
```

Two consequences: it gets whatever compute unit the framework defaults to (no GPU/ANE steering),
and the `isDirectory.boolValue` guard confirms again that **`.aimodel` is a directory**.

**(2) It supports dynamic shapes and real batching** — the segmenter does neither.
`planBatch` (`:289-312`) is the reusable piece:

```swift
static func planBatch(expectedShape: [Int], imageCount: Int,
                      parameters: DetectionParameters) throws -> BatchPlan {
    guard imageCount >= 1 else { throw ... }
    let batchExpected = expectedShape[0]
    if batchExpected >= 0 && batchExpected != imageCount {
        throw DetectionRuntimeError.invalidConfiguration(
            "Model expects fixed batch=\(batchExpected) but caller supplied \(imageCount) image(s)")
    }
    let heightExpected = expectedShape[2]
    let widthExpected  = expectedShape[3]
    let height = heightExpected < 0 ? parameters.inputHeight : heightExpected
    let width  = widthExpected  < 0 ? parameters.inputWidth  : widthExpected
    return BatchPlan(batch: imageCount, height: height, width: width)
}
```

Rules, verbatim from the doc comment (`:283-288`):
> - *"**Batch**: always `imageCount`. A static-batch model must match."*
> - *"**Spatial dims**: a dynamic `-1` dim is filled from `parameters.inputHeight` /
>   `inputWidth`. A static dim is taken from the model descriptor (the parameters' values are
>   ignored for that axis)."*

**`-1` is the dynamic-dimension sentinel in `NDArrayDescriptor.shape`**, and
`descriptor.resolvingDynamicDimensions([B, 3, H, W])` binds it (`:162-163`, `:104-105`).
That is the canonical dynamic-shape recipe in this repo.

**(3) It writes preprocessed pixels directly into batch slots** — no intermediate flat buffer.
This is the most idiomatic modern-Swift code in the repo (`:195-239`), and the doc comment
explains the `Span` subtlety (`:191-194`):

> *"`contiguousElements` is consuming, so the `MutableSpan` is obtained once outside the loop and
> indexed per image; being a safe, bounds-checked handle lets `try` stay inline. It is `nil` for a
> non-contiguous buffer, which the slot arithmetic's dense row-major assumption treats as an error."*

```swift
var view = imageArray.mutableView(as: Float.self)
guard var span = view.contiguousElements else {
    throw DetectionRuntimeError.invalidConfiguration("Image input NDArray is not contiguous")
}
for (b, image) in images.enumerated() {
    let chw = try preprocessor.preprocessCHW(cgImage: image)
    let start = b * slotCount                     // slotCount = 3 * H * W
    for i in 0..<slotCount { span[start + i] = chw[i] }
}
```

**(4) DETR/YOLOS-family postprocessing**, not SAM-family (`DetectionPostprocessor.swift:9-15`):

> *"1. Softmax over the class dimension (last class is "no-object")
>    2. For each query, take max probability across object classes
>    3. Filter by threshold
>    4. Convert boxes from [cx, cy, w, h] normalized → pixel [x, y, w, h] (top-left origin)"*

- Softmax is `classCount` wide but the argmax search runs over `classCount - 1`, dropping the
  trailing background class (`:100-113`).
- **No NMS.** DETR-family models are set-prediction, so non-max suppression is unnecessary — but
  it means this postprocessor is wrong for anchor-based YOLO variants.
- Box format is **`[cx, cy, w, h]` normalized**, converted to top-left-origin pixel `CGRect`
  (`:66-78`). Contrast the segmenter, which uses **XYXY** normalized. **Two different box
  conventions in one repo — check which one your model emits.**
- `decode` returns `[]` on any shape mismatch (`:31-45`), never throws.

Also note `warmup(imageCount:parameters:)` runs a real forward pass with an all-zero
`NDArray` at the same `(B,H,W)` the real calls will use (`:87-107`).

### 4.3 Complete copyable usage — object detection

```swift
import CoreAIObjectDetector   // module name; product is CoreAIObjectDetection
import CoreGraphics
import ImageIO

let detector = try await ObjectDetector(resourcesAt: "~/models/yolos.aimodel")
try await detector.warmup()                       // 1 image, .default params

func loadCGImage(_ url: URL) -> CGImage? {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
    return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

// --- single image, defaults (threshold 0.3, top 100, COCO labels, ImageNet norm) ---
let objects = try await detector.detect(image: loadCGImage(imageURL)!)
for o in objects {
    print("\(o.label) (\(o.labelIndex)) \(String(format: "%.3f", o.confidence)) \(o.boundingBox)")
    // boundingBox is TOP-LEFT origin pixel coords on ALL platforms.
}

// --- tuned ---
var params = DetectionParameters()
params.threshold = 0.5
params.maxDetections = 20
params.inputHeight = 640          // only used if the model's H dim is -1 (dynamic)
params.inputWidth  = 640
params.classLabels = [0: "background", 1: "widget"]   // override COCO
let tuned = try await detector.detect(image: cgImage, parameters: params)

// --- batched: ONE forward pass over N images, results in input order ---
let images = urls.compactMap(loadCGImage)
let batched: [[DetectedObject]] = try await detector.detect(images: images, parameters: params)
// Requires the model's batch dim to be -1 (dynamic) or exactly images.count.
try await detector.warmup(imageCount: images.count, parameters: params)  // warm at the real batch size
```

---

## 5. `CoreAISpeech`

Four files, 528 lines. The **least polished** of the four products: no `ModelBundle`, no
`PreparedModel`, no test target, hardcoded tensor names, and a hardcoded fallback shape.

```
CoreAISpeech/MelSpectrogram.swift   176 L
CoreAISpeech/SpeechModel.swift      130 L
CoreAISpeech/SpeechBundle.swift     125 L
CoreAISpeech/SpeechDecoder.swift     97 L
```

### 5.1 Public API — complete

```swift
// SpeechModel.swift:17-130
public actor SpeechModel {
    public init(resourcesAt url: URL,
                decoder: any SpeechDecoder = WhisperDecoder(),
                melConfig: MelConfig = .whisper) async throws     // calls warmUp() in init
    public func transcribe(audioURL: URL) async throws -> String
    public func transcribe(pcm: [Float]) async throws -> String   // 16 kHz mono
}

// SpeechDecoder.swift:13-97
public protocol SpeechDecoder: Sendable {
    func decode(encoderOutput: NDArray, encoderOutputShape: [Int],
                decoderModel: AIModel, config: GenerationConfig) async throws -> [Int32]
}
public struct WhisperDecoder: SpeechDecoder {
    public init()
    public func decode(...) async throws -> [Int32]               // greedy
}

// SpeechBundle.swift:22-125
public struct SpeechBundle: Sendable {
    public let encoder: AIModel
    public let decoder: AIModel
    public let tokenizer: (any Tokenizer)?
    public let generationConfig: GenerationConfig
    public init(at url: URL) async throws
}
public struct GenerationConfig: Sendable {
    public let forcedPrefix: [Int32]
    public let eotToken: Int32
    public let maxDecodeSteps: Int
    public let tokenizerName: String?
    public static let whisper: GenerationConfig
}
public enum SpeechError: Error, CustomStringConvertible {
    case missingModel(String), missingTokenizer, invalidAudio(String)
}

// MelSpectrogram.swift:14-176
public struct MelConfig: Sendable {
    public let sampleRate: Double; public let nFFT: Int; public let hopLength: Int
    public let nMelBins: Int;      public let nFrames: Int
    public var nSamples: Int { Int(sampleRate) * (nFrames * hopLength / Int(sampleRate / 100)) }
    public static let whisper: MelConfig
}
public enum MelSpectrogram {
    public static func fromFile(_ url: URL, config: MelConfig = .whisper) throws -> [Float]
    public static func fromPCM(_ raw: [Float], config: MelConfig = .whisper) -> [Float]
    public static func loadAndResample(_ url: URL, targetSampleRate: Double) throws -> [Float]
}
```

### 5.2 The speech bundle layout — convention, not `metadata.json`

`SpeechBundle.init(at:)` (`SpeechBundle.swift:28-46`) hardcodes filenames:

```
<bundle-dir>/
  encoder.aimodel           REQUIRED  — audio features -> encoder hidden states
  decoder.aimodel           REQUIRED  — autoregressive decoder with persistent KV state
  generation_config.json    optional  — falls back to GenerationConfig.whisper
  tokenizer.json            optional  — else falls back to the HF cache
```

There is **no `metadata.json` and no `BundleKind.speech`**. If either `.aimodel` is missing:

```swift
throw SpeechError.missingModel(
    "bundle at \(url.lastPathComponent) must contain encoder.aimodel and decoder.aimodel")
```

**The tokenizer fallback reaches outside the bundle** (`SpeechBundle.swift:48-69`) — worth
knowing before you ship an app:

```swift
// 1. Try tokenizer files in the bundle itself
if FileManager.default.fileExists(atPath: bundleURL.appending(path: "tokenizer.json").path) {
    return try? await AutoTokenizer.from(modelFolder: bundleURL)
}
// 2. Fall back to local HF cache using the model name from config
if let name = config.tokenizerName {
    let cacheRoot = FileManager.default.homeDirectoryForCurrentUser
        .appending(path: ".cache/huggingface/hub")
    let folderName = "models--" + name.replacingOccurrences(of: "/", with: "--")
    let snapshotsDir = cacheRoot.appending(path: "\(folderName)/snapshots")
    if let snapshot = try? FileManager.default.contentsOfDirectory(atPath: snapshotsDir.path).first { ... }
}
return nil
```

`~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots/<first>` — this
works on a dev Mac and fails on device. The error message admits it:
*"Tokenizer not found — ensure the model bundle includes a tokenizer or the HF cache is
populated"* (`:121`).

`GenerationConfig.whisper` defaults (`SpeechBundle.swift:86-91`):

```swift
public static let whisper = GenerationConfig(
    forcedPrefix: [50258, 50259, 50360, 50364],  // BOS <|en|> <|transcribe|> <|notimestamps|>
    eotToken: 50257,
    maxDecodeSteps: 50,
    tokenizerName: "openai/whisper-large-v3-turbo")
```

`maxDecodeSteps: 50` is **very short** — ~1 sentence. `generation_config.json` keys read
(`:100-107`): `forced_decoder_ids`, `eos_token_id`, `max_new_tokens`, `tokenizer_name`.

### 5.3 The tensor contract (hardcoded, unlike the vision products)

Encoder `main` (`SpeechModel.swift:61-82`):
- input `input_features` — `[1, nMelBins, nFrames]` Float32 = `[1, 128, 3000]` for Whisper
- output `encoder_hidden_states`

Decoder `main` (`SpeechDecoder.swift:39-45`) — six descriptors, all by literal name:
- inputs: `input_ids` `[1,1]`, `position_ids` `[1, pos+1]`, `encoder_hidden_states`
- **states**: `keyCache`, `valueCache` (via `decDesc.stateDescriptor(of:)`)
- output: `logits` `[1, 1, vocabSize]`

This is the repo's clearest example of **`InferenceFunction` persistent state**:

```swift
// SpeechDecoder.swift:47-52 — dynamic cache dims resolved to maxTargetPos
let maxTargetPos = 448
let kcShape = keyCacheNDDesc.shape.map { $0 < 0 ? maxTargetPos : $0 }
let vcShape = valCacheNDDesc.shape.map { $0 < 0 ? maxTargetPos : $0 }
var keyCache   = NDArray(descriptor: keyCacheNDDesc.resolvingDynamicDimensions(kcShape))
var valueCache = NDArray(descriptor: valCacheNDDesc.resolvingDynamicDimensions(vcShape))

// :60-76 — one decode step; state and outputs are pre-allocated MutableViews
func step(_ tok: Int32, pos: Int) async throws {
    var ids    = NDArray(descriptor: inputIdsNDDesc.resolvingDynamicDimensions([1, 1]))
    var posIds = NDArray(descriptor: posIdsNDDesc.resolvingDynamicDimensions([1, pos + 1]))
    fillNDArray(&ids,    as: Int32.self, with: [tok])
    fillNDArray(&posIds, as: Int32.self, count: pos + 1) { Int32($0) }
    var st = InferenceFunction.MutableViews()
    st.insert(&keyCache,   for: "keyCache")
    st.insert(&valueCache, for: "valueCache")
    var out = InferenceFunction.MutableViews()
    out.insert(&logitsArray, for: "logits")
    _ = try await decFn.run(inputs: ["input_ids": ids, "position_ids": posIds,
                                     "encoder_hidden_states": encHSArray],
                            states: consume st, outputViews: consume out)
}
```

`maxTargetPos = 448` is hardcoded — Whisper's max target positions. `consume st` /
`consume out` are Swift ownership moves; `MutableViews` is non-copyable.

Greedy loop (`:78-95`): prime the KV cache by stepping each forced-prefix token, then argmax
`logits` until `eotToken` or `maxDecodeSteps`. Detokenization filters `tokens < eotToken`
(`SpeechModel.swift:127`) to strip special tokens — which works only because Whisper puts all
specials at IDs ≥ 50257.

### 5.4 `MelSpectrogram` — a full hand-rolled STFT, no vDSP FFT

`MelConfig.whisper` (`MelSpectrogram.swift:24-25`) — *"Whisper / Parakeet shared parameters"*:

```swift
public static let whisper = MelConfig(
    sampleRate: 16_000, nFFT: 400, hopLength: 160, nMelBins: 128, nFrames: 3_000)
```

= 30 s of audio at 16 kHz (3000 × 160 = 480,000 samples), 25 ms window / 10 ms hop, 128 mel bins.

The pipeline (`fromPCM`, `:38-92`) is a faithful librosa/Whisper reimplementation:

1. **Truncate or zero-pad** to exactly `nFrames * hopLength` samples (`:42-46`).
2. **Reflect-pad** by `nFFT/2` on both ends (`:48-52`) — hand-written reflection, matching
   `torch.stft(center=True, pad_mode="reflect")`.
3. **Hann window**, periodic-ish: `0.5*(1 - cos(2πn/(size-1)))` (`:132-134`).
4. **DFT by dense matrix multiply, not FFT** (`:136-148`, `:71-78`): it precomputes
   `[nFreqs × nFFT]` cos and sin bases and calls `cblas_sgemv` twice per frame.
   That is O(nFFT²) per frame instead of O(nFFT log nFFT) — 3000 frames × 2 × (201×400) GEMV.
   **A guide could legitimately point at this as the thing to replace with `vDSP_DFT`.**
5. **Power spectrum** via one fused `vDSP_vmma` (`real*real + imag*imag`) (`:79`).
6. **Mel filterbank** as another `cblas_sgemv` (`:80-83`); the bank is Slaney-normalized
   triangular (`norm = 2/(fR-fL)`) with the HTK mel scale `2595*log10(1+f/700)` (`:150-175`).
7. **log10, clamp at 1e-10**, then Whisper's exact normalization (`:85`, `:89-90`):
   ```swift
   mel[i] = log10(max(melFrame[i], 1e-10))
   let maxVal = mel.max() ?? 0
   for i in 0..<mel.count { mel[i] = (max(mel[i], maxVal - 8) + 4) / 4 }
   ```
8. Output layout is **`[nMelBins, nFrames]`** — written as `mel[i * nFrames + t]` (`:85`),
   i.e. mel-major/time-minor, matching `input_features` `[1, 128, 3000]`.

Audio loading (`loadAndResample`, `:96-128`) uses `AVAudioFile` + `AVAudioConverter` to force
**Float32, mono, 16 kHz, non-interleaved**. The converter callback feeds the entire file in one
buffer (`fed` flag) then reports `.endOfStream` — so **the whole file is read into memory at
once**; there is no streaming path.

### 5.5 Complete copyable usage — speech

```swift
import CoreAISpeech

// Bundle dir must contain encoder.aimodel + decoder.aimodel (+ optional
// generation_config.json and tokenizer.json).
let model = try await SpeechModel(resourcesAt: URL(fileURLWithPath: "~/models/whisper-turbo"
                                                    .expandingTildeInPath))
// init already ran a silence warm-up through the encoder.

let text = try await model.transcribe(audioURL: URL(fileURLWithPath: "audio.wav"))
print(text)

// --- from raw PCM (must be 16 kHz mono Float32) ---
let pcm: [Float] = ...
let text2 = try await model.transcribe(pcm: pcm)

// --- custom decoder / mel config ---
struct MyDecoder: SpeechDecoder {
    func decode(encoderOutput: NDArray, encoderOutputShape: [Int],
                decoderModel: AIModel, config: GenerationConfig) async throws -> [Int32] { ... }
}
let custom = try await SpeechModel(resourcesAt: url, decoder: MyDecoder(), melConfig: .whisper)

// --- mel spectrogram standalone (e.g. to feed your own encoder) ---
let mel = try MelSpectrogram.fromFile(audioURL)            // [128 * 3000] Float, mel-major
let pcm16k = try MelSpectrogram.loadAndResample(audioURL, targetSampleRate: 16_000)
let mel2 = MelSpectrogram.fromPCM(pcm16k)
```

**Caveats to state in any guide:**
- Only the first **30 s** of audio is transcribed — longer input is truncated at
  `MelSpectrogram.fromPCM` (`:42-44`). No chunking/windowing exists.
- `maxDecodeSteps` defaults to **50 tokens**.
- `encOutShape ?? [1, 1500, 1280]` (`SpeechModel.swift:117`) — a hardcoded
  Whisper-large-v3-turbo fallback shape.
- `bundle.encoder.functionDescriptor(for: "main")!` is force-unwrapped in three places
  (`:65`, `:88`, `:106`).

---

## 6. `CoreAIDiffusion` — the `CoreAIDiffusionPipeline` target

23 files, ~3,400 lines. **This is the richest multi-model orchestration example in the repo**:
several `.aimodel` files run in sequence, plus a scheduler, a tokenizer, an RNG, and lazy
load/unload for memory.

```
Pipelines/Flux2Pipeline.swift              786 L
Pipelines/SD3Pipeline.swift                296 L
Pipelines/PipelineDescriptor.swift         272 L
Pipelines/StableDiffusionPipeline.swift    236 L
Pipelines/Flux2Pipeline+Resources.swift    172 L
Pipelines/PipelineDescriptor+CoreAI.swift  138 L
Pipelines/PipelineConfiguration.swift      126 L
Pipelines/SD3Pipeline+Resources.swift       60 L
Pipelines/Pipeline.swift                    54 L
Schedulers/DPMSolverMultistepScheduler.swift 290 L
Schedulers/PNDMScheduler.swift             184 L
Schedulers/DiscreteFlowScheduler.swift     123 L
Schedulers/SchedulerMath.swift              39 L
Schedulers/Scheduler.swift                  13 L
Components/CoreAIDiffusionModelFunction.swift 244 L
Components/CoreAILatentCodec.swift         116 L
Components/CoreAITextEncoder.swift          84 L
Components/CoreAIDenoiser.swift             67 L
Components/CoreAIComponentError.swift       24 L
Components/Components.swift                 20 L
RNG/TorchRandomSource.swift                129 L
RNG/NumPyRandomSource.swift                101 L
RNG/NvRandomSource.swift                    83 L
RNG/RandomSource.swift                      23 L
Tokenizers/BPETokenizer.swift              167 L
Tokenizers/BPETokenizer+Reading.swift       59 L
DiffusionUtilities.swift                    57 L
```

### 6.1 The protocol layer

```swift
// Pipelines/Pipeline.swift:11-54
public struct GenerationResult: Sendable {
    public let images: [CGImage]
    public let latents: [NDArray]          // [1, C, H, W] — for img2img round-trips or debugging
}
public struct PipelineProgress: Sendable {
    public let step: Int
    public let totalSteps: Int
    public let currentLatent: NDArray?     // preview latent, if available
}
public protocol DiffusionPipeline: ResourceManaging {   // note: ResourceManaging from CoreAIShared
    var defaultImageSize: (width: Int, height: Int) { get }
    var supportedSchedulers: [SchedulerType] { get }
    var supportsImageToImage: Bool { get }
    func generateImages(configuration: PipelineConfiguration,
                        progressHandler: (PipelineProgress) -> Bool) async throws -> GenerationResult
}
```

`progressHandler` returns `Bool` — **return `false` to cancel the denoise loop** (`:49`).

```swift
// Pipelines/PipelineConfiguration.swift:26-89
public struct PipelineConfiguration: Hashable, Sendable {
    public var prompt: String
    public var negativePrompt: String            = ""
    public var seed: UInt32                      = 0
    public var stepCount: Int                    = 50
    public var guidanceScale: Float              = 7.5
    public var schedulerType: SchedulerType      = .dpmSolverMultistep
    public var startingImage: CGImage?           = nil     // img2img
    public var strength: Float                   = 1.0
    public var encoderScaleFactor: Float         = 0.18215
    public var decoderScaleFactor: Float         = 0.18215
    public var decoderShiftFactor: Float         = 0.0
    public var decodeResolution: DecodeResolution = .full
    public var originalSize: Float               = 1024    // SDXL geometry conditioning
    public var targetSize: Float                 = 1024
    public var lazyModelLoading: Bool            = true
    public var isImageToImage: Bool { startingImage != nil }
}

public enum DecodeResolution: String, Hashable, Sendable, CaseIterable {
    case auto     // picks the highest quality mode available in the model directory
    case full     // Transformer + VAEDecoder      -> 1024×1024
    case half     // Transformer_512 + VAEDecoder_half -> 512×512 (4× faster)
    case tiled    // Transformer + VAEDecoder_half in tiles -> 1024×1024, low memory
}
```

`lazyModelLoading` doc (`:50-51`): *"Load model components on demand and unload after each
pipeline stage to reduce peak memory. Disable to keep all models resident and exercise full
memory pressure (e.g. profiling peak footprint)."* Default **true**.

`Hashable` conformance is hand-written because `CGImage` isn't `Hashable` (`:91-126`) —
`startingImage` is excluded from both `hash(into:)` and `==`. **So two configs differing only
in their input image compare equal.** A cache keyed on `PipelineConfiguration` would collide.

### 6.2 `CoreAIDiffusionModelFunction` — the per-component wrapper

This is the diffusion analogue of `PreparedModel`, and it is an **actor** (`:12`):

```swift
public actor CoreAIDiffusionModelFunction {
    public init(modelURL: URL)
    public func loadResources() async throws
    public func unloadResources()
    public func run(floatInputs: [([Float], [Int])]) async throws -> [Float]
    public func run(intInputs:   [([Int32], [Int])]) async throws -> [Float]
    public func predict(inputs: [String: NDArray]) async throws -> [String: [Float]]
    public func predictAllOutputs(inputs: [String: NDArray]) async throws -> [String: [Float]]
    public func predictAutoNamed(inputs: [NDArray]) async throws -> [String: [Float]]
    public var inputDescriptors:  [String: NDArrayDescriptor] { get async throws }
    public var outputDescriptors: [String: NDArrayDescriptor] { get async throws }
    public func inferSequenceLength() async throws -> Int?
}
public enum CoreAIDiffusionError: Error, LocalizedError {
    case functionNotFound(String, URL), notLoaded
    case unsupportedInputScalarType(NDArray.ScalarType)
    case unsupportedOutputScalarType(NDArray.ScalarType)
    case expectedSingleOutput(got: [String])
}
```

Key facts:

- **Every diffusion component is pinned to the GPU** (`:27-28`):
  ```swift
  let options = SpecializationOptions(preferredComputeUnitKind: .gpu)
  let loadedModel = try await AIModel(contentsOf: modelURL, options: options)
  ```
  Unlike the segmenter, there is no structure probing — diffusion is unconditionally GPU.
- The `run(floatInputs:)` API is **positional**: it zips `floatInputs` against
  `fn.descriptor.inputNames` **in declaration order** (`:50`). Callers pass a tuple array and
  the names come from the model. Fragile but concise; re-exporting with reordered inputs
  silently mis-binds.
- `inferSequenceLength()` (`:210-217`) reads `shape[1]` of the first input descriptor. This is
  the fix behind commit `917dc99` "Fix SD text encoder crash: infer sequence length from model" —
  77 is no longer assumed.
- Every I/O crosses a `[Float]` boundary; `ndArrayToFloats` (`:159-180`) handles float16/float32
  with the usual x86-macOS `#if` guard.
- `unloadResources()` just nils `function` and `model` (`:38-42`) — this is what makes
  `lazyModelLoading` work.

### 6.3 Components: text encoder, denoiser, latent codec

```swift
// Components/Components.swift:10-20
public struct TextEncoderOutput: Sendable {
    public let hiddenStates: NDArray      // [1, seq_len, hidden_dim]
    public let pooledOutput: NDArray?     // [1, hidden_dim]; nil for SD 1.5 CLIP-L
}

// Components/CoreAITextEncoder.swift:11-84
public final class CoreAITextEncoder: Sendable {
    public let function: CoreAIDiffusionModelFunction
    public let tokenize: @Sendable (String) -> [Int32]
    public init(function:, tokenize: @escaping @Sendable (String) -> [Int32], maxLength: Int = 77)
    public func loadResources() async throws
    public func unloadResources() async
    public func encode(_ text: String) async throws -> TextEncoderOutput
}

// Components/CoreAIDenoiser.swift:10-67
public final class CoreAIDenoiser: Sendable {
    public let function: CoreAIDiffusionModelFunction
    public init(function: CoreAIDiffusionModelFunction)
    public func loadResources() async throws
    public func unloadResources() async
    public func predictNoise(latents: NDArray, timestep: Float, textEmbeddings: NDArray,
                             additionalInputs: [String: NDArray]) async throws -> NDArray
}

// Components/CoreAILatentCodec.swift:12-116
public final class CoreAILatentDecoder: Sendable {
    public let function: CoreAIDiffusionModelFunction
    public func decode(_ latents: NDArray, scaleFactor: Float, shiftFactor: Float) async throws -> NDArray
}
public final class CoreAILatentEncoder: Sendable {
    public let function: CoreAIDiffusionModelFunction
    public func encode(_ image: CGImage, scaleFactor: Float) async throws -> NDArray
}
```

**Text encoder output classification by descriptor RANK** — a neat trick worth stealing
(`CoreAITextEncoder.swift:54-76`):

```swift
// Classify by descriptor rank:
//   rank 3 → token-level hidden state  [1, seq, hiddenDim]
//   rank 2 → pooled / projection       [1, pooledDim]
for (name, floats) in outputs {
    let rank = outputDescs[name]?.shape.count ?? 0
    if rank == 3 { ... hiddenStates = array }
    else if rank == 2 { ... pooledOutput = array }
}
```

Tokenization pads with **0**, not EOT (`:39`) — the opposite of `CLIPTokenizer` in the segmenter.
Truncation is a hard `prefix(maxLength)` with no EOT re-insertion.

**The denoiser hardcodes three input names** (`CoreAIDenoiser.swift:39-44`) —
`"sample"`, `"timestep"`, `"encoder_hidden_states"` — plus a caller-supplied
`additionalInputs` dictionary for pooled projections / guidance / RoPE.
**This is the only place in the non-LLM Swift where tensor names are hardcoded rather than
discovered**, other than `CoreAISpeech`.

**Latent scaling lives in the codec, not the model** (`CoreAILatentCodec.swift:36`):
```swift
inputFloats.append(ptr[i] / scaleFactor + shiftFactor)      // decode
...
for i in 0..<outputFloats.count { ptr[i] = outputFloats[i] * scaleFactor }   // encode
```
And the VAE output shape is **inferred, not read from the model** (`:42-45`):
```swift
// Infer output shape: [1, 3, H*8, W*8] for VAE decoder
let outH = shape[2] * 8
let outW = shape[3] * 8
```
`CoreAILatentEncoder.encode` hardcodes `[1, 4, height/8, width/8]` (`:108`) — **4 latent
channels**, which is right for SD 1.x/2.x and wrong for SD3 (16) and FLUX.2 (32).
So this class is SD1/2-only despite its generic name. It also does its own inline
`[0,255] → [-1,1]` conversion with per-channel vDSP (`:93-104`) rather than calling
`CGImageUtils.toNormalizedPlanarRGB` — **duplicate logic**.

### 6.4 `PipelineDescriptor` — the diffusion bundle schema

```swift
// Pipelines/PipelineDescriptor.swift:19-96
public struct PipelineDescriptor: Codable, Sendable {
    public var type: PipelineType?
    public var version: String?
    public var predictionType: PredictionType?
    public var imageSize: Int?
    public var components: ComponentPaths
    public var scheduler: SchedulerDefaults?
    public var encoderScaleFactor: Float?
    public var decoderScaleFactor: Float?
    public var decoderShiftFactor: Float?
    // FLUX.2-specific fields
    public var batchNormEps: Float?
    public var guidanceEmbeds: Bool?
    public var ropeAxesDims: [Int]?
    public var ropeTheta: Float?
    public var defaultGuidanceScale: Float?
    public var defaultSteps: Int?
}

public enum PipelineType: String, Codable, Sendable {
    case stableDiffusion    = "stable-diffusion"
    case stableDiffusionXL  = "stable-diffusion-xl"
    case stableDiffusion3   = "stable-diffusion-3"
    case flux2              = "flux2"
}
public struct ComponentPaths: Codable, Sendable {
    public var textEncoder: String?
    public var textEncoder2: String?
    public var unet: String?
    public var vaeDecoder: String?
    public var vaeEncoder: String?
}
public struct SchedulerDefaults: Codable, Sendable {
    public var trainingSteps: Int  = 1000
    public var betaStart: Float    = 0.00085
    public var betaEnd: Float      = 0.012
    public var betaSchedule: String = "scaled_linear"
}
public enum ConfigSource { case auto, file(URL), explicit(PipelineDescriptor) }
public static func resolve(at url: URL, config: ConfigSource = .auto) throws -> PipelineDescriptor
public static func loadFromMetadata(at url: URL) throws -> PipelineDescriptor
public static func load(from url: URL) throws -> PipelineDescriptor
public static func detect(at url: URL) -> PipelineDescriptor
```

**Three-tier resolution** (`:106-136`) — this is the bundle-format story for diffusion:

> 1. `metadata.json` (v0.2 schema with `kind: "diffusion"`)
> 2. `pipeline.json` (**deprecated — now a hard error**)
> 3. Directory scan for known component filenames

```swift
// :122-129 — pipeline.json is now fatal, not a warning
let pipelineURL = url.appendingPathComponent("pipeline.json")
if FileManager.default.fileExists(atPath: pipelineURL.path) {
    throw PipelineLoadError.deprecatedFormat(
        "This bundle uses the legacy pipeline.json format which is no longer supported.\n"
            + "Please re-export with `coreai.diffusion.export` to produce metadata.json.\n"
            + "See: https://github.com/apple/coreai-models/issues/TBD")
}
```
> ⚠ The prior notes' README-sourced snippets referencing `pipeline.json` are stale — an
> existing `pipeline.json` in `.auto` mode now **throws**. It is only honored via
> `ConfigSource.file(URL)`. Note also the dangling `issues/TBD` link in shipped code.

`loadFromMetadata` bridges the generic `assets` map to the diffusion-specific component slots
(`:155-160`) — **`transformer` and `unet` are aliases**:

```swift
descriptor.components.textEncoder  = assets["text_encoder"]
descriptor.components.textEncoder2 = assets["text_encoder_2"]
descriptor.components.unet         = assets["transformer"] ?? assets["unet"]
descriptor.components.vaeDecoder   = assets["vae_decoder"]
descriptor.components.vaeEncoder   = assets["vae_encoder"]
```

`decoder.keyDecodingStrategy = .convertFromSnakeCase` (`:151`) — so the `diffusion` block in
`metadata.json` uses snake_case keys (`prediction_type`, `image_size`, `encoder_scale_factor`,
`rope_axes_dims`, `default_guidance_scale`, …).

**Filename auto-detect** (`:187-212`) — the fallback convention when there is no metadata:

| Substring (lowercased) | Slot |
|---|---|
| `textencoder2` / `text_encoder_2` | `textEncoder2` |
| `textencoder` / `text_encoder` | `textEncoder` |
| `unet` / `transformer` / `mmdit` | `unet` |
| `vaedecoder` / `vae_decoder`, **and not `half`** | `vaeDecoder` |
| `vaeencoder` / `vae_encoder`, **and not `half`** | `vaeEncoder` |

The `!lower.contains("half")` filters keep FLUX.2's `_half` variants out of the generic slots —
those are resolved by explicit name instead (§6.6).

**Cross-validation against the actual model** (`PipelineDescriptor+CoreAI.swift:69-92`) — this is
the pattern to copy for "trust but verify" bundle configs:

```swift
let unetInputs = try await unetFunction.inputDescriptors
if let sampleDesc = unetInputs["sample"] ?? unetInputs["latent_model_input"] {
    let shape = sampleDesc.shape
    // shape is [1, C, H, W] — image_size = H * 8 (latent space is 8x downsampled)
    if shape.count == 4 && shape[2] > 0 {
        let inferredSize = shape[2] * 8
        if let configSize = imageSize {
            if configSize != inferredSize {
                throw PipelineLoadError.configMismatch(
                    field: "imageSize", expected: "\(configSize)", actual: "\(inferredSize)")
            }
        } else { imageSize = inferredSize }
    }
}
if type == nil { type = .stableDiffusion }
if predictionType == nil { predictionType = .epsilon }
if decoderScaleFactor == nil { decoderScaleFactor = 0.18215 }
```

Tokenizer lookup is two-location (`:95-105`): first `<bundle>/vocab.json` + `<bundle>/merges.txt`,
else `<bundle>/tokenizer/vocab.json` + `<bundle>/tokenizer/merges.txt`.

```swift
public struct CoreAIDiffusionComponents: Sendable {
    public let textEncoder: CoreAITextEncoder
    public let denoiser: CoreAIDenoiser
    public let decoder: CoreAILatentDecoder
    public let encoder: CoreAILatentEncoder?      // nil => no img2img
}
public enum PipelineLoadError: Error, LocalizedError {
    case missingComponent(String), missingConfig(String), deprecatedFormat(String)
    case configMismatch(field: String, expected: String, actual: String)
}
```

### 6.5 `StableDiffusionPipeline` — the canonical orchestration loop

Read `StableDiffusionPipeline.generateImages` (`:84-170`) as *the* reference for
"several models in sequence." Annotated skeleton:

```swift
public func generateImages(configuration: PipelineConfiguration,
                           progressHandler: (PipelineProgress) -> Bool) async throws -> GenerationResult {
    let scaleFactor    = descriptor.decoderScaleFactor ?? 0.18215
    let predictionType = descriptor.predictionType ?? .epsilon

    // 1. MODEL A — text encoder, twice (positive + negative prompt)
    let textEmbeddings     = try await encodeText(configuration.prompt)
    let negativeEmbeddings = try await encodeText(configuration.negativePrompt)
    if configuration.lazyModelLoading { await components.textEncoder.function.unloadResources() }

    // 2. Scheduler (pure Swift, no model)
    let schedule = try createSchedule(type: configuration.schedulerType,
                                      stepCount: configuration.stepCount,
                                      predictionType: predictionType)

    // 3. RNG — initial latents [1, 4, H/8, W/8]
    let latentShape = [1, 4, size.height / 8, size.width / 8]
    var latents = generateNoise(count: latentShape.reduce(1, *), seed: configuration.seed)

    // 4. MODEL B — denoise loop
    let batchedEmbeddings = negativeEmbeddings + textEmbeddings          // [2, 77, dim]
    let batchedEmbShape   = [2, 77, textEmbeddings.count / 77]
    for (step, timeStep) in schedule.timeSteps.enumerated() {
        if !progressHandler(PipelineProgress(step: step, totalSteps: schedule.timeSteps.count,
                                             currentLatent: nil)) { break }   // cancellation
        let batchedLatents = latents + latents                           // CFG: [2, 4, H, W]
        let unetOutput = try await runDenoiser(...)
        // classifier-free guidance, in Swift
        let half = unetOutput.count / 2
        for i in 0..<half {
            guided[i] = unetOutput[i] + scale * (unetOutput[half + i] - unetOutput[i])
        }
        latents = schedule.step(guided, timeStep, latents)
    }
    if configuration.lazyModelLoading { await components.denoiser.function.unloadResources() }

    // 5. MODEL C — VAE decode, then pixels -> CGImage
    for i in 0..<latentCount { scaledLatents[i] = latents[i] * (1.0 / scaleFactor) }
    let pixels = try await components.decoder.function.run(floatInputs: [(scaledLatents, latentShape)])
    if configuration.lazyModelLoading { await components.decoder.function.unloadResources() }
    let image = try DiffusionUtilities.pixelsToCGImage(pixels, height: size.height, width: size.width)
    return GenerationResult(images: [image], latents: [latentsND])
}
```

Design note in the file header (`:15`): *"All intermediate computation in `[Float]`. NDArray only
at model I/O boundary."* That is the opposite of the segmenter's multi-function path, which
threads `NDArray`s directly between graphs. Both are valid; the diffusion choice trades a copy
per step for CPU-side math (CFG, scheduler) that would be awkward on the GPU.

**Classifier-free guidance is done in Swift, not in the graph** — the UNet is called with a
batch of 2 (negative, positive) and the two halves are blended on CPU (`:132-138`).

`supportedSchedulers` = `[.pndm, .dpmSolverMultistep]`; `.discreteFlow` throws with an actionable
message (`:226-229`):
```swift
case .discreteFlow:
    throw CoreAIComponentError.invalidShape(
        "discreteFlow is not supported by StableDiffusionPipeline — use SD3Pipeline or Flux2Pipeline")
```

`supportsImageToImage` is simply `components.encoder != nil` (`:29-31`) — but note
`generateImages` in this file **never reads `configuration.startingImage`**. SD1/2 img2img is
declared-capable but not implemented in this pipeline's `generateImages`; the img2img path lives
in `diffusion-runner` and the Flux2/SD3 pipelines. **UNVERIFIED** whether that is intentional.

### 6.6 Multi-model bundle layout — FLUX.2, the fullest example

`Flux2Pipeline.init(from:config:mode:)` (`Flux2Pipeline+Resources.swift:17-113`) loads
**up to four `.aimodel` files + a tokenizer dir + two `.npy` sidecars** out of one directory:

```
<bundle>/
  Transformer.aimodel          or Transformer.aimodelc      # full res (1024)
  Transformer_512.aimodel      or .aimodelc                 # half res (512)
  TextEncoder.aimodel                                       # Qwen3 encoder
  VAEDecoder.aimodel
  VAEDecoder_half.aimodel
  VAEEncoder.aimodel
  VAEEncoder_half.aimodel
  tokenizer/                                                # HF format, AutoTokenizer.from(modelFolder:)
  vae_bn_mean.npy                                           # VAE batch-norm statistics
  vae_bn_var.npy
  metadata.json                                             # kind: "diffusion", + diffusion block
```

Two loading conventions coexist in this one initializer:

- **Metadata-driven** for `text_encoder` and (full-mode) `vae_encoder` — read from
  `descriptor.components` (`:32-34`, `:81`).
- **Name-driven** for everything mode-dependent — `Self.resolveAsset(at:name:)` (`:116-126`),
  which tries `"<Name>.aimodel"` then `"<Name>.aimodelc"`:

```swift
private static func resolveAsset(at url: URL, name: String) -> String? {
    let fm = FileManager.default
    let aimodel  = "\(name).aimodel"
    let aimodelc = "\(name).aimodelc"
    if fm.fileExists(atPath: url.appendingPathComponent(aimodel).path)  { return aimodel }
    else if fm.fileExists(atPath: url.appendingPathComponent(aimodelc).path) { return aimodelc }
    return nil
}
```

**`.aimodelc` (AOT-compiled) is transparently substituted for `.aimodel` here** — this is the
runtime half of `models/README.md#compiled-models`.

**Mode auto-detection by asset probing** (`:130-144`) — priority `.full > .tiled > .half`:

```swift
private static func bestAvailableMode(at url: URL, descriptor: PipelineDescriptor) throws -> DecodeResolution {
    let hasFullTransformer = descriptor.components.unet != nil
    let hasFullDecoder     = descriptor.components.vaeDecoder != nil
    let hasHalfDecoder     = resolveAsset(at: url, name: "VAEDecoder_half") != nil
    let hasHalfTransformer = resolveAsset(at: url, name: "Transformer_512") != nil
    if hasFullTransformer && hasFullDecoder { return .full }
    if hasFullTransformer && hasHalfDecoder { return .tiled }
    if hasHalfTransformer && hasHalfDecoder { return .half }
    throw PipelineLoadError.missingComponent(
        "No valid component combination found. Need Transformer+VAEDecoder, "
            + "Transformer+VAEDecoder_half, or Transformer_512+VAEDecoder_half.")
}
```

So **`--platform iOS` at export time ships `Transformer_512` + `VAEDecoder_half`, and the Swift
side then auto-selects `.half`.** The export-time platform choice and the runtime mode selection
meet through nothing but filenames.

**A hand-rolled `.npy` reader ships in the Swift** (`:148-171`) for the VAE batch-norm statistics
— magic bytes `\x93NUMPY`, v1 vs v2 header length, then a raw `Float32` bind:

```swift
guard data.count > 10,
    data[0] == 0x93, data[1] == 0x4E, data[2] == 0x55,
    data[3] == 0x4D, data[4] == 0x50, data[5] == 0x59
else { return nil }
let majorVersion = data[6]
if majorVersion == 1 { headerLen = Int(data[8]) | (Int(data[9]) << 8); headerStart = 10 }
else { headerLen = Int(data[8]) | (Int(data[9]) << 8) | (Int(data[10]) << 16) | (Int(data[11]) << 24)
       headerStart = 12 }
let rawData = data[(headerStart + headerLen)...]
return rawData.withUnsafeBytes { Array($0.bindMemory(to: Float32.self)) }
```

It ignores the header's dtype/shape/fortran_order entirely — it assumes little-endian float32 C
order. A second, richer `.npy` reader (float16/float32/int32/uint8 + shape) exists in
`Tools/image-segmenter` (§7.2). **Two independent npy readers in one repo.**

FLUX.2 uses **swift-transformers' `AutoTokenizer`**, not the local BPE tokenizer (`:96`) —
because its text encoder is Qwen3, not CLIP.

### 6.7 Schedulers

```swift
// Schedulers/Scheduler.swift:9-13 — the entire type
public enum SchedulerType: String, Sendable, CaseIterable {
    case pndm
    case dpmSolverMultistep = "dpmpp"
    case discreteFlow       = "flow_match_euler"
}
```

Note the raw values: the CLI/JSON strings are `"pndm"`, `"dpmpp"`, `"flow_match_euler"`.

`DiscreteFlowScheduler` (`:10-123`) — flow matching for SD3/FLUX:

```swift
public final class DiscreteFlowScheduler {
    public let trainStepCount: Int
    public let inferenceStepCount: Int
    public let timeSteps: [Int]
    public var startSigma: Float { sigmas.first ?? 1.0 }
    public private(set) var modelOutputs: [[Float]]
    public init(stepCount: Int = 50, trainStepCount: Int = 1000,
                timeStepShift: Float = 3.0, mu: Float? = nil, sigmaMax: Float = 1.0)
    public func step(output: [Float], timeStep t: Int, sample: [Float]) -> [Float]
    public func calculateTimesteps(strength: Float?) -> [Int]
    public func addNoise(to sample: [Float], noise: [Float], at strength: Float) -> [Float]
}
```

The sigma-floor comment is a genuine bug post-mortem worth quoting in full (`:40-49`):

> *"Lower bound of the pre-shift sigma linspace. Diffusers builds
> `sigmas = np.linspace(1.0, 1 / num_inference_steps, num_inference_steps)`
> (pipeline_flux2_klein.py) and passes it to `FlowMatchEulerDiscreteScheduler.set_timesteps`,
> which uses the provided sigmas as-is and only applies the mu/shift transform — it does NOT
> recompute the endpoints from num_train_timesteps. So the floor must be `1/stepCount` for BOTH
> the dynamic-shift (mu) and static-shift paths. Using `1/trainStepCount` here collapsed the
> final sigma to ~0 at low step counts (e.g. 4-step Klein), wasting the last step and misplacing
> all intermediate noise levels."*

Two shift modes (`:53-62`):
```swift
if let mu {                                    // dynamic (resolution-dependent) shift
    let expMu = expf(mu)
    inferSigmas = inferSigmas.map { expMu / (expMu + (1.0 / $0 - 1.0)) }
} else if timeStepShift != 1.0 {               // static shift, default 3.0
    inferSigmas = inferSigmas.map { timeStepShift * $0 / (1.0 + (timeStepShift - 1.0) * $0) }
}
self.sigmas    = inferSigmas + [0.0]
self.timeSteps = inferSigmas.map { Int($0 * ts) }
```

Euler step (`:84-111`): `denoised = sample − output·σ`, then `x' = x + ((x − denoised)/σ)·Δσ`.
Flow-matching forward noising for img2img (`:119-122`): `x_t = (1−t)·x₀ + t·ε`.

`SchedulerMath.swift` (39 L) is the shared numeric kit: `weightedSum` via `cblas_saxpy` (Float and
Double-weights overloads), `linspace`, and an `Array[back:]` subscript. DPM-Solver *"uses Double
internally"* (`:23`) — a precision decision worth noting.

### 6.8 RNG parity — three implementations of "random"

`RNG/RandomSource.swift:20-23`:
```swift
public protocol RandomSource {
    mutating func nextNormal(mean: Double, stdev: Double) -> Double
    mutating func normalArray(_ shape: [Int], mean: Double, stdev: Double) -> [Float]
}
```

The doc comment is the whole point (`:8-19`):

> *"Deterministic random source for reproducible noise generation. Multiple implementations exist
> to match the exact random sequences produced by different Python frameworks. Using the matching
> source guarantees the same seed produces the same image across platforms.*
> - *`TorchRandomSource`: **Default**. Matches PyTorch (`torch.manual_seed`). Used by SDXL, SD3, Flux.*
> - *`NumPyRandomSource`: Matches NumPy (`numpy.random.RandomState`). Used by SD 1.5/2.x.*
> - *`NvRandomSource`: Matches NVIDIA cuRAND (Philox). Used by some ComfyUI/Automatic1111 workflows.*
>
> *The implementations are direct ports of MT19937 / Philox; **do not refactor the bitwise logic
> without verifying output against the Python reference for multiple seeds.**"*

`StableDiffusionPipeline.generateNoise` picks NumPy (`StableDiffusionPipeline.swift:232-235`):
```swift
private func generateNoise(count: Int, seed: UInt32) -> [Float] {
    var rng = NumPyRandomSource(seed: seed)
    return (0..<count).map { _ in Float(rng.nextNormal()) }
}
```

**This is the highest-leverage under-documented topic in the whole non-LLM half**: "why does my
port produce a different image from the same seed" is answered here, in three files, with named
framework targets.

### 6.9 `BPETokenizer` — the diffusion (CLIP/SD) tokenizer

Separate from the segmenter's `CLIPTokenizer`. Loads HF **`vocab.json` + `merges.txt`** (the older
two-file layout), not `tokenizer.json`:

```swift
// Tokenizers/BPETokenizer+Reading.swift:14-49
static func readVocabulary(url: URL) throws -> [String: Int]              // JSONDecoder
static func readMerges(url: URL) throws -> [TokenPair: Int]               // byte-wise line scan
static func parseMergesLine(_ line: [UInt8], index: Int) throws -> TokenPair?
enum FileReadError: Error { case invalidMergeFileLine(Int) }
```
Merges parsing skips blank lines and `#` comments, and throws `invalidMergeFileLine(index+1)` for
any line without exactly two space-separated fields (`:40-49`). Constructed as
`BPETokenizer(mergesAt:vocabularyAt:)` and driven via
`tokenizer.tokenize(input:minCount:) -> (_, [Int])` (`PipelineDescriptor+CoreAI.swift:99-123`).

**So the repo contains three tokenizers for the non-LLM products**: `CLIPTokenizer`
(segmenter, `tokenizer.json`), `BPETokenizer` (SD diffusion, `vocab.json`+`merges.txt`), and
swift-transformers `AutoTokenizer` (FLUX.2 + speech, `tokenizer/` folder).

### 6.10 Complete copyable usage — diffusion

```swift
import CoreAIDiffusionPipeline
import CoreGraphics

// ---------- SD 1.5 / 2.x ----------
let pipeline = try await StableDiffusionPipeline.load(from: modelDirURL)   // .auto config source
print(pipeline.defaultImageSize)      // (512, 512) or from metadata
print(pipeline.supportedSchedulers)   // [.pndm, .dpmSolverMultistep]
print(pipeline.supportsImageToImage)  // true iff a VAEEncoder asset exists

var config = PipelineConfiguration(
    prompt: "a photograph of an astronaut riding a horse",
    negativePrompt: "blurry, low quality",
    seed: 42,
    stepCount: 20,
    guidanceScale: 7.5,
    schedulerType: .dpmSolverMultistep,
    lazyModelLoading: true)      // unload each component after its stage

let result = try await pipeline.generateImages(configuration: config) { progress in
    print("Step \(progress.step)/\(progress.totalSteps)")
    return true                  // return false to CANCEL the denoise loop
}
let image: CGImage = result.images[0]
let latents: NDArray = result.latents[0]     // [1, 4, H/8, W/8]

// ---------- FLUX.2 ----------
// mode: .auto picks the best of .full/.tiled/.half from what's on disk
let flux = try await Flux2Pipeline(from: modelDirURL, mode: .auto)
var fluxConfig = PipelineConfiguration(
    prompt: "a photo of a cat",
    seed: 42,
    stepCount: 4,                        // Klein is a few-step model
    guidanceScale: 1.0,
    schedulerType: .discreteFlow)        // REQUIRED for FLUX.2 / SD3
let fluxResult = try await flux.generateImages(configuration: fluxConfig) { _ in true }

// Force half-res (512) even if full assets are present:
let fast = try await Flux2Pipeline(from: modelDirURL, mode: .half)
// Tiled 1024 decode with the half-res VAE (low memory):
let lowMem = try await Flux2Pipeline(from: modelDirURL, mode: .tiled)

// ---------- SD 3.x ----------
let sd3 = try await SD3Pipeline(from: modelDirURL)
// schedulerType must be .discreteFlow

// ---------- explicit descriptor (no metadata.json on disk) ----------
var d = PipelineDescriptor()
d.type = .stableDiffusion
d.imageSize = 512
d.components = PipelineDescriptor.ComponentPaths(
    textEncoder: "TextEncoder.aimodel", unet: "Unet.aimodel",
    vaeDecoder: "VAEDecoder.aimodel", vaeEncoder: "VAEEncoder.aimodel")
let explicit = try await StableDiffusionPipeline.load(from: url, config: .explicit(d))

// ---------- memory: keep everything resident (profiling) ----------
config.lazyModelLoading = false
try await pipeline.loadResources()      // ResourceManaging
defer { Task { await pipeline.unloadResources() } }
```

---

## 7. CLI tools (`swift/Sources/Tools/`)

Five executables. Build with `swift build -c release`; run with `swift run -c release <tool> …`.

| Executable target | Source dir | Product it exercises | Non-LLM? |
|---|---|---|---|
| `llm-runner` | `Tools/llm-runner` | `CoreAILM` (+VLM) | no *(prior notes)* |
| `llm-benchmark` | `Tools/benchmark` | `CoreAILM` | **no — see 7.1** |
| `image-segmenter` | `Tools/image-segmenter` | `CoreAISegmentation` | yes |
| `object-detector` | `Tools/object-detector` | `CoreAIObjectDetection` | yes |
| `speech-runner` | `Tools/speech-runner` | `CoreAISpeech` | yes |
| `diffusion-runner` | `Tools/diffusion-runner` | `CoreAIDiffusion` | yes |

### 7.1 `benchmark` — ⚠ it is LLM-ONLY

**Correcting a likely assumption:** the directory is `Tools/benchmark`, but the executable target
is named **`llm-benchmark`** (`Package.swift:188-189`), the command name is `llm-benchmark`
(`BenchmarkMain.swift:21`), and it `import CoreAILanguageModels` (`:9`) and hard-depends on
`LanguageBundle` (`:57`), `EngineFactory` (`:70`), `SamplingConfiguration` (`:76`) and
`InferenceEngine` (`:121`).

**There is no benchmarking tool for segmentation, detection, speech, or diffusion.**
Each non-LLM tool times itself inline instead (see 7.2–7.5). This is a real gap in the repo and
a legitimate "here's what to build" hook for a guide.

For completeness — `llm-benchmark`'s full flag set (`BenchmarkMain.swift:25-41`):

```
--model <path>                       Path to a model bundle directory        (required)
-p, --prompt-tokens <int>            Length of prompt                        (default 512)
-g, --generation-tokens <int>        Length of completion                    (default 1024)
-n, --num-trials <int>               Number of timing trials                 (default 5)
--seed <uint64>                      Random seed for synthetic prompt        (default 0)
--output-json <path>                 Write summary JSON to file
```

What it measures (`:120-154`): per trial it calls `engine.reset()`, then times
`engine.generate(...)` with `temperature: 0` over a **synthetic random-token prompt**
(splitmix64 over `0..<vocabSize`, `:158-172`). Two throughputs:

- `promptTps = prompt.count / time-to-first-token`
- `genTps = (tokenCount − 1) / (total − time-to-first-token)`

using `SuspendingClock` (`:130`, `:148`, `:174-178`). One untimed warmup trial precedes the loop
(`:79-80`), and it prints a Debug-build warning (`:53-55`). JSON output is
`{model, prompt_tokens, generation_tokens, num_trials, trials[{prompt_tps, gen_tps}], averages}`
with `.convertToSnakeCase` (`:186-218`).

The comment at `:6` credits the design: *"Based on mlx-lm benchmark
(https://github.com/ml-explore/mlx-lm)"*.

Notably it does **not** report model size on disk, memory, or compute-unit placement — despite
`URL.recursiveFileSizeInBytes()` existing in `CoreAIShared` for exactly that.

### 7.2 `image-segmenter`

`commandName: "image-segmenter"`, abstract: *"Run image segmentation using a text prompt (SAM3) or
point/box prompts (EfficientSAM)."* (`ImageSegmentationRunnerMain.swift:16-18`)

Complete flags (`:22-107`):

```
--model <path>                 Path to the model dir.                                    (required)
--image <path>                 Path to the input image.               (required unless --parity-test)
--prompt <string>              Text prompt describing the object to segment (SAM3).
--point <x,y>                  Point prompt as 'x,y' in input-image pixel coordinates
                               (repeatable). EfficientSAM only.
--point-label <label>          Label for each --point: foreground (default), background,
                               box-top-left, box-bottom-right (repeatable).
--segment-everything           Segment without prompts. EfficientSAM only.               (flag)
--queries-json <path>          JSON file with multiple point queries. EfficientSAM only.
--max-segments <int>           Maximum number of segments to process and return.   (default 5)
--mask-threshold <float>       Mask sigmoid activation threshold (0-1).            (default 0.5)
--warmup                       Run a warmup pass before timed inference.                 (flag)
--output-json <path>           Write JSON results to this path.
--output-path <path>           Output PNG path. Default output_<timestamp>.png in cwd.
--verbose                      Print verbose progress information.                       (flag)
--parity-test <dir>            Path to a parity-data dir (source_image.npy + input_ids.npy
                               + ref_<output>.npy). Compares each raw model output
                               against its reference via PSNR + cosine similarity.
--psnr-floor <float>           Minimum PSNR (dB) per output in --parity-test.      (default 30.0)
--cosine-floor <float>         Minimum cosine similarity per output.               (default 0.999)
```

`--queries-json` format, verbatim from the help text (`:53-60`):
```json
[[{"x":N,"y":N,"label":"foreground"}, ...], ...]
```
> *"outer array is queries, inner array is points per query. Label is optional (defaults to
> foreground); accepted values: foreground, background, box-top-left, box-bottom-right."*

`validate()` (`:110-145`) enforces exactly one query mode:
- `--parity-test` bypasses all other requirements (it reads its image and tokens from `.npy`).
- otherwise `--image` is required;
- exactly one of `{--prompt}`, `{--point | --segment-everything}`, `{--queries-json}` —
  *"--prompt, --point/--segment-everything, and --queries-json are mutually exclusive."*
- `--segment-everything` and `--point` are additionally mutually exclusive;
- `--point-label` count must equal `--point` count when non-empty.

Behavior (`:147-190`): `--verbose` sets `CLILogger.level = 1`; loads via
`ImageSegmenter(resourcesAt: model)`; optional `warmup()`; times the segment call with
`SuspendingClock` and prints *"Inference time (including pre and post processing)"*; renders
a PNG and, on macOS only, shells out to `/usr/bin/open` (`:511-521`).

Output rendering (`:526+`): semantic overlay when a probability map exists, else instance masks;
prompt boxes stroked on top. PNG written with `CGImageDestinationCreateWithURL(..., "public.png", 1, nil)`
(`:500-509`).

**The parity harness is the most reusable non-obvious asset here.** It ships a minimal `.npy`
reader supporting float16 / float32 / int32 / uint8 with shape parsing (`:530+`), plus PSNR and
cosine-similarity metrics (`:679-700`). The doc comment says why tokens come from a file
(`:395-400`):

> *"Routes through the same `CoreAISegmentationEngine.segment(...)` call the production path uses,
> so `ImagePreprocessor` is in scope. Tokens come pre-computed from Python (via `input_ids.npy`)
> to isolate the test from any `CLIPTokenizer` drift — tokenizer parity is a separate concern."*

Real invocations:
```bash
swift build -c release

# SAM3 text prompt
swift run -c release image-segmenter \
  --model ~/coreai-models/exports/sam3_lite_336_w4_static \
  --prompt "cat" --image ./photo.jpg --verbose --warmup

# EfficientSAM single click
swift run -c release image-segmenter \
  --model ~/coreai-models/exports/efficient_sam_vitt_float32_static \
  --image ./photo.jpg --point 100,100

# EfficientSAM box prompt (one query, two points)
swift run -c release image-segmenter --model <dir> --image ./photo.jpg \
  --point 100,100 --point-label box-top-left \
  --point 400,300 --point-label box-bottom-right

# Segment everything (needs a perfect-square --num-queries at export time)
swift run -c release image-segmenter --model <dir> --image ./photo.jpg --segment-everything

# Tuned + JSON + explicit PNG
swift run -c release image-segmenter --model <dir> --image ./photo.jpg --prompt "dog" \
  --max-segments 20 --mask-threshold 0.35 \
  --output-json ./segments.json --output-path ./overlay.png

# PyTorch parity check
swift run -c release image-segmenter --model <dir> \
  --parity-test ./parity_data --psnr-floor 30 --cosine-floor 0.999
```

### 7.3 `object-detector`

`commandName: "object-detector"`, abstract: *"Run object detection on an image using a CoreAI
.aimodel model."* (`ObjectDetectionMain.swift:16-17`)

Complete flags (`:22-70`):

```
--model <path>            Path to the .aimodel directory.                          (required)
--image <path>            Path to an input image. Pass --image multiple times to run
                          detection on a batch of images (one --image per source file).
                                                                       (required, repeatable)
--threshold <float>       Confidence threshold (0-1).                        (default 0.3)
--max-detections <int>    Maximum number of detections to return.            (default 100)
--input-height <int>      Override model input height (only used for dynamic models).
                          Defaults to DetectionParameters.inputHeight if not set.
--input-width <int>       Override model input width (only used for dynamic models).
--warmup                  Run a warmup pass before timed inference.                 (flag)
--output-image <path>     Render detections onto the input image(s). For a single --image
                          this is a file path; for multiple it is a DIRECTORY and the CLI
                          writes <source-stem>_detections.png into it.
--output-json <path>      Write JSON results to this path instead of stdout. With one
                          --image the JSON is an array of detections; with multiple it is
                          an array of {image, detections} objects.
--verbose                 Print verbose progress information.                       (flag)
```

`validate()`: at least one `--image` (`:74-78`).

Behavior (`:81-160`): builds `DetectionParameters` from the flags, warms up **at the real batch
size** (`detector.warmup(imageCount: loaded.count, …)`, `:97`), then runs **one batched
`detect(images:parameters:)` call** and times the whole thing with `SuspendingClock`. Stdout
summary is suppressed when `--output-json` is set (`:135`).

JSON schema (`:160-175`, `JSONDetection` / `JSONImageResult`), pretty-printed with sorted keys:
```json
// single --image
[ { "label": "dog", "labelIndex": 18, "score": 0.98,
    "box": {"x": 12.0, "y": 40.0, "width": 220.0, "height": 310.0} } ]
// multiple --image
[ { "image": "a.jpg", "detections": [ … ] }, { "image": "b.jpg", "detections": [ … ] } ]
```

The tool also draws labelled boxes itself using CoreText (`:280-300` uses
`ascent`/`descent`/`leading`) — there is no `DetectionVisualization` type in the library, unlike
segmentation's `SegmentationVisualization`. **Rendering for detection lives only in the CLI.**

Real invocations (README-sourced, `models/yolo/README.md:70-77`):
```bash
swift run -c release object-detector --model path/to/exported_model.aimodel --image path/to/image.jpg

swift run -c release object-detector \
  --model path/to/dynamic.aimodel \
  --image a.jpg --image b.jpg \
  --input-height 800 --input-width 1024 \
  --warmup

# tuned + outputs
swift run -c release object-detector --model yolos.aimodel --image photo.jpg \
  --threshold 0.5 --max-detections 20 \
  --output-image ./detected.png --output-json ./detections.json --verbose

# batch -> --output-image is a DIRECTORY
swift run -c release object-detector --model yolos.aimodel \
  --image a.jpg --image b.jpg --image c.jpg --output-image ./out/
```

### 7.4 `speech-runner`

`commandName: "speech-runner"`, abstract: *"Transcribe audio using a CoreAI speech model bundle"*
(`SpeechRunnerMain.swift:18-19`). **Positional arguments, no options at all** (`:22-26`):

```
<model-path>   Bundle dir (encoder.aimodel + decoder.aimodel) or single .aimodel (legacy)
<audio-path>   Audio file (wav, flac, m4a, …). Omit for latency benchmarking with silence.  [optional]
```

Dispatch is by probing for `encoder.aimodel` (`:29-35`):

```swift
let bundleURL = URL(fileURLWithPath: modelPath)
if FileManager.default.fileExists(atPath: bundleURL.appending(path: "encoder.aimodel").path) {
    try await runBundle(bundleURL: bundleURL, audioPath: audioPath)   // prints "Format: split (encoder + decoder, KV cache)"
} else {
    try await runLegacy(modelPath: modelPath, audioPath: audioPath)   // prints "Format: legacy (monolithic, no KV cache)"
}
```

**Two model formats, one tool:**

- **Split bundle** (`:40-60`): uses `SpeechModel`; times the whole transcribe with
  `ContinuousClock` and prints `"%.1f ms total"`.
- **Legacy monolithic** (`:64-151`): drives `AIModel` directly with `input_features` +
  `decoder_input_ids` → `logits`, no KV cache. It detects whether `decoder_input_ids` is static
  and warns (`:78-81`):
  ```swift
  let isStaticIds = !idsNDDesc.shape.contains(where: { $0 < 0 })
  if isStaticIds { print("  ⚠️  decoder_input_ids has static shape — no past context per step") }
  ```
  Per step it re-feeds either the last token (static) or the whole sequence (dynamic)
  (`:114`), argmaxes the last position (`:127-129`), and reports
  `"steps: %d  latency: %.1f ms/tok  speed: %.1f tok/s"` (`:135-138`).
  Detokenization here reaches into `~/.cache/huggingface/hub/models--openai--whisper-large-v3-turbo/snapshots`
  directly (`:141-144`) and falls back to printing raw token ids.

**Omitting the audio path is the built-in benchmark mode** — it feeds 480,000 zero samples
(30 s of silence at 16 kHz) and reports total ms (`:53-59`):

```swift
print("No audio — silence benchmark")
let pcm = [Float](repeating: 0, count: 480_000)
```

Real invocations:
```bash
swift run -c release speech-runner ~/models/whisper-turbo ./audio.wav
swift run -c release speech-runner ~/models/whisper-turbo                 # 30s-silence latency benchmark
swift run -c release speech-runner ./whisper-large-v3-turbo_float32.aimodel ./audio.wav   # legacy path
```

### 7.5 `diffusion-runner`

`commandName: "diffusion-runner"`, abstract: *"Generate images using Stable Diffusion models"*
(`DiffusionRunnerMain.swift:18-19`). Note `extension DecodeResolution: ExpressibleByArgument {}`
at `:13` — that is how `--decode-resolution` accepts `full|half|tiled|auto`.

Complete flags (`:22-74`):

```
--model <path>              Path to model directory containing .aimodel components
                            (or pipeline.json)                                    (required)
--prompt <string>           Text prompt for image generation      (default "a photo of a cat")
--negative-prompt <string>  Negative prompt                                      (default "")
--steps <int>               Number of denoising steps      (default: pipeline default, else 20)
--guidance-scale <float>    Guidance scale                (default: pipeline default, else 7.5)
--seed <uint32>             Random seed                                          (default 42)
--scheduler <string>        Scheduler: pndm or dpmpp                        (default "dpmpp")
--output <path>             Output image path                          (default "output.png")
--config <path>             Path to pipeline.json (auto-detected if not specified)
--input-image <path>        Path to input image for image-to-image generation
--strength <float>          img2img strength                                   (default 0.85)
--lazy-model-loading        (flag, default TRUE)
--decode-resolution <enum>  VAE decode resolution: full, half, or tiled       (default full)
--parity-test <dir>         Path to parity data directory (numpy .npy files)
--trace-inputs <dir>        (see :71-74)
```

**Pipeline dispatch is by `descriptor.type`, and the scheduler is overridden for flow models**
(`:99-106`):

```swift
let resolvedDescriptor = try PipelineDescriptor.resolve(at: modelURL, config: configSource)
let isFlux2 = resolvedDescriptor.type == .flux2
let isSd3   = resolvedDescriptor.type == .stableDiffusion3
let schedulerType: SchedulerType =
    (isFlux2 || isSd3) ? .discreteFlow : (scheduler == "pndm" ? .pndm : .dpmSolverMultistep)
let effectiveSteps    = steps ?? resolvedDescriptor.defaultSteps ?? 20
let effectiveGuidance = guidanceScale ?? resolvedDescriptor.defaultGuidanceScale ?? 7.5
```

**So `--scheduler` is silently ignored for FLUX.2 and SD3**, and `--steps`/`--guidance-scale`
fall back to the bundle's `default_steps` / `default_guidance_scale` before the hardcoded
20 / 7.5. Three branches follow (`:135-200`): `Flux2Pipeline(from:config:mode:)`,
`SD3Pipeline(from:config:)`, `StableDiffusionPipeline.load(from:config:)` — each prints
`"Steps: … Guidance: … Seed: …"`, the resolved image size, a per-step progress line, and
`"Generated in %.2fs"` from a `ContinuousClock`.

> Off-by-one: the SD branch prints `progress.step + 1` while the Flux2 and SD3 branches print
> `progress.step` (`:196` vs `:141`, `:168`). Cosmetic, but it means SD counts 1…N and the others
> count 0…N−1.

Two special modes short-circuit before normal generation (`:79-87`): `--parity-test` and
`--trace-inputs`. `--trace-inputs` replays a directory of captured tensors through the graph —
useful for isolating a Swift-vs-Python divergence to a single component.

Real invocations:
```bash
# SD 1.5 / 2.1
swift run -c release diffusion-runner \
  --model path/to/exported_model_folder \
  --prompt "a photograph of an astronaut riding a horse"

# explicit everything
swift run -c release diffusion-runner --model ./sd15 \
  --prompt "an astronaut riding a horse" --negative-prompt "blurry, low quality" \
  --steps 20 --guidance-scale 7.5 --seed 42 --scheduler dpmpp --output ./out.png

# FLUX.2 Klein — few-step, guidance 1.0; --scheduler is IGNORED (forced .discreteFlow)
swift run -c release diffusion-runner \
  --model path/to/exported_model_folder \
  --prompt "a photo of a cat" --steps 4 --guidance-scale 1.0

# FLUX.2 at half resolution (512) / tiled 1024 low-memory
swift run -c release diffusion-runner --model ./flux2 --prompt "a cat" --decode-resolution half
swift run -c release diffusion-runner --model ./flux2 --prompt "a cat" --decode-resolution tiled

# img2img
swift run -c release diffusion-runner --model ./sd15 --prompt "make it snowy" \
  --input-image ./photo.jpg --strength 0.85

# parity / tracing
swift run -c release diffusion-runner --model ./sd15 --parity-test ./parity_data
swift run -c release diffusion-runner --model ./sd15 --trace-inputs ./traced
```

---

## 8. The non-LLM model catalog (`models/`)

15 non-LLM recipe directories. **All 15 have a README; 12 also ship an `export.py`.**
The 3 without (`stable-diffusion`, `flux2`, `vlm`) drive shared CLIs
(`coreai.diffusion.export`, `coreai.vlm.export`) instead.

### 8.1 The two artifact shapes

This is the single most confusing thing in the catalog:

| Artifact shape | Models |
|---|---|
| **Bare `.aimodel` file, no `metadata.json`** | yolo, clip, t5, roberta, pvt, edsr, depth-anything, wav2vec2, clap, whisper |
| **Bundle directory** (`.aimodel` + `metadata.json` [+ `tokenizer/`]) | sam3, efficient-sam, stable-diffusion, flux2, vlm |

So **10 of the 15 non-LLM models produce something `ModelBundle` cannot load at all** — you must
hand them to `AIModel(contentsOf:)` yourself (which is exactly what `ObjectDetector` does, §4.2).
Only the segmenters, the diffusion pipelines and the VLM use the bundle format.

Common `export.py` skeleton, shared by all 12 standalone recipes:
PEP-723 header pinning `coreai-core==1.0.0b2` + `coreai-torch==0.4.1`
(SAM3 excepted — it uses the editable workspace `coreai-models`), then
`torch.export.export` → `run_decompositions(get_decomp_table())` →
`TorchConverter().add_exported_program(...)` → `to_coreai()` → `optimize()` →
`save_asset(path, AIModelAssetMetadata)`.
`_default_output_dir()` is uniformly `Path(__file__).resolve().parents[2] / "exports"` =
`<repo-root>/exports/`. Overwrite guard is uniformly
`FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")`.
Run them with `uv run models/<name>/export.py` (`models/README.md:115`).

### 8.2 Master comparison table

| Model | Dir | Checkpoint | Params | Artifact | Default output name | Entrypoints | Inputs | Outputs | dtype (default / choices) | Dynamic | Compression | Platform notes | Swift consumer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **SAM 3** | `sam3` | `facebook/sam3` (gated) | 848M | bundle | `sam3_lite_336_w4_static/`, `sam3_float32/` | **3**: `image_encode`, `text_encode`, `detect` (lite); `main` (full) | `pixel_values[1,3,336,336]`; `input_ids[1,32]` i32 | `backbone_features[1,1024,1,576]`; `text_features[1,256,1,32]`; `pred_masks`,`pred_boxes`,`pred_logits`,`presence_logits`,`semantic_seg` | fp16 (lite); f32 / f16,f32 (full) | static only | image w4/gs32 + text w6/gs8 k-means palettization; detect fp16 only | iOS-targeted BC1S; 336 recommended | `ImageSegmenter`, `image-segmenter` |
| **EfficientSAM** | `efficient-sam` | URL `merve/EfficientSAM/.../efficient_sam_vitt.pt` | 10M | bundle | `efficient_sam_vitt_float32_static/` | 1 | `batched_images[B,3,1024,1024]`, `batched_points[B,Q,P,2]`, `batched_point_labels[B,Q,P]` | `pred_masks`, `iou_scores` | f32 / f16,bf16,f32 | batch 1–64 | none | **fp16 + `--dynamic` unsupported** | `ImageSegmenter`, `image-segmenter` |
| **YOLOS** | `yolo` | `hustvl/yolos-base` (def), `-tiny` | 127M / 6.5M | **file** | `hustvl_yolos-base_float32_static.aimodel` | 1 | `pixel_values[B,3,800,800]` | `logits`, `pred_boxes`, `last_hidden_state` | f32 / f16,bf16,f32 | batch 1–64; H,W 128–1024 step 16 | none | — | `ObjectDetector`, `object-detector` |
| **CLIP** | `clip` | `openai/clip-vit-base-patch32` | 151M | **file** | `openai_clip-vit-base-patch32_float32_static.aimodel` | 1 | `pixel_values[B,3,224,224]`, `input_ids` i32, `attention_mask` i32 (77) | `logits_per_image`, `logits_per_text`, `image_embeds`, `text_embeds` | f32 / f16,bf16,f32 | image_batch + text_batch 1–64 | none | — | *(none)* |
| **T5** | `t5` | `google-t5/t5-small` (def), `-base`, `-large` | 60M/220M/770M | **file** | `google-t5_t5-small_float32_static.aimodel` | 1 | `input_ids` i32, `decoder_input_ids` i32 | `logits`, `encoder_last_hidden_state` | f32 / **f16,f32 only** | batch 1–64; f16 seq capped 4096 | none | f16→ANE, f32→GPU | *(none)* |
| **RoBERTa** | `roberta` | `roberta-base` | 125M | **file** | `roberta-base_float32_static.aimodel` | 1 | `input_ids` i32 | `last_hidden_state` | f32 / f16,bf16,f32 | batch 1–64, seq 1–512 | none | — | *(none)* |
| **PVT v2** | `pvt` | timm `pvt_v2_b0` | 3.7M | **file** | `pvt_v2_b0_float32_static.aimodel` | 1 | **`x`**`[B,3,224,224]` | `logits` | f32 / f16,bf16,f32 | batch 1–64 only | none | — | *(none)* |
| **EDSR** | `edsr` | torchSR `edsr_r16f64(scale=2)` | 1.5M | **file** | `edsr_r16f64_x2_float32_static.aimodel` | 1 | `x[B,3,16,16]` | `output` | f32 / f16,bf16,f32 | batch 1–64, H/W 8–256 | none | — | *(none)* |
| **Depth Anything v3** | `depth-anything` | `depth-anything/da3-small` | 35M | **file** | `da3-small_float32.aimodel` | 1 | `image[1,2,3,224,224]` (B,N_views,3,H,W) | `depth`, `depth_conf`, `extrinsics`, `intrinsics` | **f32 only** | **none — no `--dynamic` flag** | none | **macOS-only** in registry | *(none)* |
| **Wav2Vec 2.0** | `wav2vec2` | torchaudio `WAV2VEC2_ASR_BASE_960H` | 95M | **file** | `wav2vec2_asr_base_960h_float32_static.aimodel` | 1 | `waveform[B,80000]` @16 kHz | `emission` | f32 / f16,f32 | batch 1–64 + `Dim.DYNAMIC` length | none | — | *(none)* |
| **CLAP** | `clap` | `laion/clap-htsat-unfused` | 153M | **file** | `laion_clap-htsat-unfused_float32_static.aimodel` | 1 | `input_ids` i32, `attention_mask` i32, `input_features` (48 kHz), `is_longer` bool | `logits_per_audio`, `logits_per_text`, `text_embeds`, `audio_embeds` | f32 / f16,f32 | text batch 1–64 only | none | — | *(none)* |
| **Whisper** | `whisper` | `openai/whisper-large-v3-turbo` (def), `-large-v3` | 809M / 1.54B | **file** | `whisper-large-v3-turbo_float32.aimodel` | 1 | `input_features` (30 s mel, static), `decoder_input_ids` i32 | `logits` | f32 / f16,bf16,f32 | `dec_seq_len` 1–448 (always on) | none | — | `speech-runner` **legacy path only** |
| **Stable Diffusion** | `stable-diffusion` | `runwayml/stable-diffusion-v1-5`, `sd2-community/stable-diffusion-2-1`, `stabilityai/stable-diffusion-3.5-medium` (gated) | 0.9B/0.9B/2.5B | bundle | `<out>/<hf-tail>/` | 4 assets (SD1/2), 4 (SD3) | see 8.4 | see 8.4 | f16 preset | fixed | preset `none` default; `4bit` (INT4 blk32 sym) available; **VAE never quantized** | macOS + iOS | `StableDiffusionPipeline` / `SD3Pipeline`, `diffusion-runner` |
| **FLUX.2 Klein** | `flux2` | `black-forest-labs/FLUX.2-klein-4B` | 4B | bundle | `<out>/FLUX.2-klein-4B/` | up to 7 assets | see 8.4 | see 8.4 | f16 preset | fixed per component | **`4bit` default** on transformer + text_encoder | `--platform iOS`→512; `macOS`→1024; `--low-memory` adds halves | `Flux2Pipeline`, `diffusion-runner` |
| **Qwen3-VL** | `vlm` | `Qwen/Qwen3-VL-2B-Instruct` | 2B | bundle `.llmasset/` | `qwen3_vl_2b.llmasset/` | **3 assets**: `main`, `embedding`, `vision` | `inputs_embeds`+`position_ids`; `input_ids`; `pixel_values[1,3,448,448]` f32 | `logits`; `embeddings`; `image_features[1,196,hidden]` f16 | f16 decoder/embed, f32 vision math | `main` seq ≤ ctx−2 | f16 embed table | KV ctx default 4096 | `ModelBundle`, `llm-runner` |

> **No quality or latency numbers exist anywhere in the non-LLM model docs.** A repo-wide search
> found perplexity tables only in the LLM READMEs (gemma3, mixtral, qwen2, qwen3 — WikiText-2 via
> lm-evaluation-harness). There is **no** published mIoU, mAP, WER, PSNR, CLIP score or latency
> figure for any vision/audio/diffusion model in this repo. Any guide must generate its own.

### 8.3 SAM 3 — the flagship, in detail

Real CLI lives at `python/src/coreai_models/segmentation/export.py`; `models/sam3/export.py` is a
63-line wrapper that injects the `"sam3"` positional and calls `segmentation.export.main()`
(`models/sam3/export.py:53-59`).

```bash
# Gated checkpoint — auth first
brew install hf
hf auth login --token <YOUR_TOKEN_HERE>                    # models/sam3/README.md:24-26

# Lite (default): ANE-targeted, 3 entrypoints, 336x336, image w4 / text w6
uv run export.py                                            # models/sam3/README.md:31
uv run export.py --help                                     # :37

# Full: plain transformers.Sam3Model, single `main`, 1008x1008
uv run models/sam3/export.py --full                         # :66  (float32)
uv run models/sam3/export.py --full --dtype float16         # :67
```

Full flag set (`segmentation/export.py:86-169`):

| Flag | Type | Default | Notes |
|---|---|---|---|
| `model` (positional) | str | required | short-name `sam3` or `facebook/sam3` |
| `--full` | flag | False | plain HF model, no ANE targeting or palettization |
| `--output-dir` | str | `<repo-root>/exports/` | |
| `--output-name` | str | derived | |
| `--image-size` | int | 336 lite / 1008 full | |
| `--max-text-seq-len` | int | 32 | (lite) static text sequence length |
| `--n-bits` | int ∈ {2,3,4,6,8} | — | (lite) **uniform** override for BOTH encoders |
| `--group-size` | int | — | (lite) uniform override for BOTH encoders |
| `--dtype` | `float16`\|`float32` | `float32` | `--full` only |
| `--overwrite` / `--dry-run` / `--verbose`,`-v` | flags | False | `--dry-run` prints resolved config and exits |

The three entrypoints (`segmentation/pipeline.py:266-284`):

| Function | Inputs | Outputs | Compression |
|---|---|---|---|
| `image_encode` | `pixel_values [1,3,336,336]` | `backbone_features [1,1024,1,576]` (`grid = 336//14 = 24`, 24² = 576) | k-means palettization **4-bit, group_size 32** |
| `text_encode` | `input_ids [1,32]` int32 (vocab 0–49408) | `text_features [1,256,1,32]` | k-means palettization **6-bit, group_size 8** |
| `detect` | `backbone_features`, `text_features` | `pred_masks`, `pred_boxes`, `pred_logits`, `presence_logits`, `semantic_seg` | **none** — fp16 only |

That asymmetry is the point: `segmentation/pipeline.py:9-15` calls it a split into three
*"independently optimizable functions"*, and compression is applied **per function before
export** (`:230-234`, `:241-245`, `:247-248`).

**The ANE rank constraint** — the most quotable caveat in the repo
(`segmentation/pipeline.py:133-142`):

> *"Both encoders deliberately disable per-channel scale: `enable_per_channel_scale=True` lowers
> to `mps.dequantize_lut` ops with **rank-6 LUTs, which ANE rejects (max tensor rank 5)**, forcing
> the runtime to fall back to GPU. Keeping it off keeps the asset ANE-compatible at the cost of a
> small PyTorch-side quality regression."*

Bundle written at `pipeline.py:288-296`, and `metadata.json` is written **before** the tokenizer
fetch *"so a tokenizer-fetch failure … doesn't leave the bundle unloadable by ImageSegmenter"*
(`:292-293`). Emitted metadata (`:327-338`):
```json
{"metadata_version": "0.2", "kind": "segmenter", "name": "<dir>",
 "assets": {"main": "<file>.aimodel"}}
```

**README discrepancies to flag:** the README's function table lists only 4 `detect` outputs; the
code emits 5 including `semantic_seg` (`models/sam3/README.md:11` vs `pipeline.py:283`).
The README shows `--n-bits` with no choice restriction; the code restricts to `{2,3,4,6,8}`.

### 8.4 Diffusion component tables

**SD 1.x / 2.x** (`diffusion/components.py:258-289`, dummy shapes `:208-240`):

| Component | Asset file | Inputs | Outputs | Quantizable |
|---|---|---|---|---|
| `text_encoder` | `TextEncoder.aimodel` | `input_ids [1,77]` int64 | `last_hidden_state` | yes |
| `unet` | `Unet.aimodel` | `sample [2,in_ch,S,S]`, `timestep [2]` (999.0), `encoder_hidden_states [2,77,cross_dim]` | `noise_pred` | yes |
| `vae_decoder` | `VAEDecoder.aimodel` | `z [1,latent_ch,S,S]` | `image` | **no** |
| `vae_encoder` | `VAEEncoder.aimodel` | `image [1,3,S*8,S*8]` | `latent_params` | **no** |

**SD 3.x** (`components.py:365-397`):

| Component | Asset file | Inputs | Outputs |
|---|---|---|---|
| `text_encoder` (CLIP-L) | `TextEncoder.aimodel` | `input_ids` | `hidden_embeds`, `pooled_outputs` |
| `text_encoder_2` (CLIP-G) | `TextEncoder2.aimodel` | `input_ids` | `hidden_embeds`, `pooled_outputs` |
| `transformer` (MMDiT) | `MMDiT.aimodel` | `sample`, `timestep`, `encoder_hidden_states [2,154,joint_dim]`, `pooled_projections [2,pooled_dim]` | `noise_pred` |
| `vae_decoder` | `VAEDecoder.aimodel` | `z` | `image` |

**FLUX.2** (`components.py:293-360`, shapes `diffusion/flux2.py:219-290`):

| Component | Asset file | Inputs | Outputs | Quantizable |
|---|---|---|---|---|
| `transformer` | `Transformer.aimodel` | `hidden_states [1,4096,in_ch]`, `encoder_hidden_states [1,512,joint_dim]`, `timestep [1]`, `guidance [1]`, `rotary_emb_cos`, `rotary_emb_sin` | `output` | yes |
| `transformer_512` | `Transformer_512.aimodel` | same names; grid 32 → seq 1024 | `output` | yes |
| `text_encoder` | `TextEncoder.aimodel` | `input_ids [1,512]` i64, `attention_mask [1,512]` i64 | `hidden_states` | yes |
| `vae_decoder` / `_half` | `VAEDecoder[_half].aimodel` | `z [1,latent_ch,128\|64,128\|64]` | `image` | no |
| `vae_encoder` / `_half` | `VAEEncoder[_half].aimodel` | `image [1,3,1024\|512,1024\|512]` | `latent_params` | no |

`coreai.diffusion.export` flags (`diffusion/export.py:37-105`):

```
model                       positional — registry short-name or HF id
--output-dir <path>         default <repo-root>/exports/
--components <c> [<c> ...]  SD1/2: text_encoder unet vae_decoder vae_encoder
                            SD3:   text_encoder text_encoder_2 transformer vae_decoder
                            FLUX2: transformer text_encoder vae_decoder vae_encoder
--compute-precision {float16,bfloat16,float32}   required for raw HF IDs
--compression <preset|json|none>
--overwrite
--platform {iOS,macOS}      iOS -> 512 resolution; macOS -> 1024
--resolution {512,1024}     overrides the platform default
--low-memory                include half-resolution VAEs for tiled decode
--experimental              allow models without a registry preset (needs --compute-precision)
--dry-run
--verbose / -v
```
**`--components` and `--platform` are mutually exclusive** (`diffusion/export.py:168-169`);
the platform→component mapping only applies when `pipeline_type == "flux2"` (`:179-206`).

```bash
uv run coreai.diffusion.export runwayml/stable-diffusion-v1-5
uv run coreai.diffusion.export sd2-community/stable-diffusion-2-1
uv run coreai.diffusion.export stabilityai/stable-diffusion-3.5-medium
uv run coreai.diffusion.export runwayml/stable-diffusion-v1-5 --compression none
uv run coreai.diffusion.export runwayml/stable-diffusion-v1-5 --components text_encoder unet
uv run coreai.diffusion.export flux2-klein-4b --platform iOS                    # 512
uv run coreai.diffusion.export flux2-klein-4b --platform iOS --resolution 1024
uv run coreai.diffusion.export flux2-klein-4b --platform macOS                  # 1024
uv run coreai.diffusion.export flux2-klein-4b --platform macOS --low-memory
uv run coreai.diffusion.export flux2-klein-4b --compression none
```

**Nearest-neighbor upsample workaround** (`diffusion/components.py:104-160`) — another
framework-limitation quote worth reusing:

> *"MPSGraph's segmenter **rejects `coreai.interpolate` with nearest_neighbor mode**, routing
> those ops to the BNNS (CPU) backend… Performance: cross-backend data copies (GPU→CPU→GPU) at
> every upsample boundary."* … *"This patch should be kept even after the framework fix ships."*

Replaced with `repeat_interleave(2, dim=-1).repeat_interleave(2, dim=-2)`; asserts
`scale_factor == 2`.

**FLUX.2 RoPE-outside-the-graph workaround** (`diffusion/flux2.py:9-18`): RoPE cos/sin are
computed on the host and passed as `rotary_emb_cos` / `rotary_emb_sin` inputs *"to work around a
Core AI graph optimizer bug that corrupts monolithic 25-block transformers when RoPE frequency
ops (arange, outer, pow, repeat_interleave) are in the compiled graph."*
And `Flux2VAEEncoderWrapper.forward` returns `latent_dist.mode()` not `.parameters` — *"Returning
`.parameters` would emit 64 channels where the pipeline expects 32, corrupting the img2img
latents"* (`flux2.py:203-211`).

### 8.5 Other catalog caveats and export-script discrepancies

| Model | Caveat | Cite |
|---|---|---|
| EfficientSAM | `--dynamic` + `--dtype float16` **raises `ValueError`**: *"The Core AI runtime cannot handle dynamic reshape in the attention heads at float16."* | `models/efficient-sam/export.py:136-142` |
| EfficientSAM | *"A box requires both corners in the **same** query (P ≥ 2), not two separate single-point queries."* | `README.md:55` |
| EfficientSAM | `--num-pts` default is **2** in code, but README says 1 in two places | `export.py:238` vs `README.md:35,49` |
| T5 | README + `--model` help advertise FLAN-T5, but argparse `choices` blocks anything outside `google-t5/{t5-small,t5-base,t5-large}` | `export.py:176` vs `README.md:45` |
| EDSR | README claims 2×/3×/4×, but `scale=2` is hardcoded and only `edsr_r16f64_x2` is a valid `--model` | `export.py:99,135` vs `README.md:3` |
| Wav2Vec2 | README says dynamic length has "min 720 samples"; code uses bare `Dim.DYNAMIC` with no min. **UNVERIFIED** | `export.py:55` vs `README.md:33` |
| Depth Anything | `override-dependencies = ["xformers ; python_version >= '99'"]` — a deliberate uv trick to drop xformers, which *"has no macOS-arm64 wheel and its sdist build fails on Apple Silicon"* | `export.py:19-24` |
| Depth Anything | `RotaryPositionEmbedding2D.forward` monkeypatched: upstream `int(positions.max()) + 1` is a data-dependent guard that breaks `torch.export` | `export.py:38-59` |
| Depth Anything | f32 only — *"CPU LayerNorm upcasts float16"* | `README.md:31` |
| YOLOS | README's Swift snippet loads `yolos-base_float32_static.aimodel` but the stated pattern yields `hustvl_yolos-base_…` | `README.md:19` vs `:50` |
| CLAP | `input_features` and `is_longer` are pinned fully static even under `--dynamic`; only text batch is dynamic | `export.py:71-86` |
| Compiled models | If you run `xcrun coreai-build compile`, you must hand-edit `metadata.json` `assets` to the `.aimodelc` filename | `models/README.md:171-173`; `ModelBundle.swift:103-109` |

---

## 9. Python non-LLM primitives (`python/src/coreai_models/`)

The prior notes file covers `export/pipeline.py`, `export/presets.py` and the LLM path.
This section covers the **vision/audio/diffusion-facing** primitives it did not.

### 9.1 `primitives/` — the reusable authoring kit

`primitives/__init__.py:6` is docstring-only: *"Reusable primitives for Core AI model authoring
(macOS and iOS)"*. There are **no package-level re-exports** — the two platform subpackages each
carry their own `__all__` (`primitives/ios/__init__.py:23-36`,
`primitives/macos/__init__.py:19-33`).

**The `ios/` vs `macos/` split is the central fact.** Same concepts, different implementations,
because iOS targets the Neural Engine and macOS targets the GPU.

| Concept | `primitives/ios/` | `primitives/macos/` | Divergence |
|---|---|---|---|
| Attention (LM) | `SDPA` — manual per-head loop | `SDPA` — thin subclass of `coreai_torch.composite_ops.SDPA` | *"iOS requires each attention head to be computed individually to meet hardware constraints"* (`ios/sdpa.py:14-19`) |
| Attention (vision) | `BidirectionalSDPA` | — | vision-only; no macOS counterpart |
| KV cache | `KVCacheHandler`, layout `[n_layers, B, n_kv_heads*head_dim, 1, max_seq]` | `KVCache`, layout `(n_layers, 1, n_kv_heads, max_seq, head_dim)` | *"On iOS we must update on dim 4, whereas on macOS we use dim 3"* (`ios/cache.py:14-20`); `macos/cache.py:28-32` `seq_len_dim() == 3` |
| MLP | `MLP` — **`nn.Conv2d(1×1)` instead of `nn.Linear`** | `MLP` — `nn.Linear`, up-proj before gate | *"Conv2d layers instead of Linear layers for better iOS performance"* (`ios/mlp.py:10`); *"we compute the up projection before the gate projection in order to get better performance on macOS"* (`macos/mlp.py:36-37`) |
| Norm | `RMSNorm`, `LayerNormReauthored` | `RMSNorm`, `RMSNormPlusOne`, `RMSNormGated` | `RMSNormPlusOne` adds 1.0 to weight — *"Used by Gemma3"* (`macos/rms_norm.py:26-28`) |
| RoPE | `RoPECache` — precomputed cos/sin buffers + custom gather op | `RoPE`, `YarnRoPE`, `initialize_rope` | *"On iOS, it is more efficient to compute RoPE using precomputed and cached cos/sin values"* (`ios/rope.py:53`) |
| MoE | — | `SwitchLinear`, `SwiGLU`, `SwitchGLU` | macOS-only |
| Embedding | `LoadEmbeddings`, `GatherEmbeddings` | — | rank-3 `(vocab, 1, hidden)` table |
| Activation | `GELUReauthored` / `gelu_ane` | — | |
| Quant | `quantize_per_tensor` / `dequantize_per_tensor` (8-bit only) | — | |
| Cache variant | — | `cache_scatter.KVCache` | uses `aten.slice_scatter` *"to avoid a Metal kernel crash during prefill"* (`macos/cache_scatter.py:68-69`) |

Shared: `primitives/_ops.py:12` `@torch.library.custom_op("coreai::mutable_slice_update", mutates_args=["x"])`
— begin/end are **tensors, not ints**, *"passed in as tensors for custom op compatibility"* (`:34`).

**Tensor layouts — the thing to internalize:**

| Layout | Meaning | Where used | Reduction axis |
|---|---|---|---|
| **BC1S** `(B, C, 1, S)` | channels-first, rank-4 | ALL SAM3 vision + text, `ios/sdpa.py`, `ios/cache.py`, `ios/bidirectional_sdpa.py` | `LayerNormReauthored` reduces `dim=1` |
| **BS1D** `(B, S, 1, D)` | seq-first | `ios/mlp.py`, `ios/rms_norm.py` | `RMSNorm` reduces `dim=-1` |
| **BHSD** `(1, n_kv_heads, S, head_dim)` | | `macos/cache.py` | `seq_len_dim() == 3` |
| **NCHW** | | diffusion VAE/UNet, VLM `StaticVisionEncoder` input, SAM3 `FPNNeckReauthored` internals | |
| **NLC** `(1, seq, C)` | | FLUX.2 transformer, VLM decoder `inputs_embeds` | |

**Where BC1S becomes NCHW**: `models/ios/sam3/fpn.py:199` —
`backbone_output.reshape(B, in_channels, grid_h, grid_w)`. That single reshape is the
transformer→conv boundary in SAM3.

**Key vision-only primitives** (they live under `models/ios/sam3/primitives/`, **not** in
`primitives/`):

- `AxialRoPE2DReauthored` (`models/ios/sam3/primitives/rope.py:34`) —
  *"SAM3's image encoder uses **2D axial RoPE with pairwise rotation (not the half-rotation used
  by most LLMs)**… Pairwise rotation is implemented with precomputed swap index/sign buffers so
  every intermediate stays at rank 4."* (`:6-13`). The reference `rotate_pairwise_bc1s` at `:19`
  is explicitly marked unusable for export (*"produces rank-5 intermediates"*).
- `window_partition_ane` / `window_unpartition_ane` (`models/ios/sam3/primitives/window.py:18,54`) —
  *"The HF reference reshapes through **rank-6 intermediates** `(B, H//ws, ws, W//ws, ws, C)`,
  which the on-device compiler rejects. This pair of helpers stays **strictly at rank 4** by
  working in channels-last format and folding `ws*C` together — two passes (H then W), each
  rank 4."* (`:6-13`)
- `GroupNormReauthored` (`models/ios/sam3/mask_decoder.py:38`) — *"`nn.GroupNorm` is **not
  supported on some accelerators (e.g. h16c)**; this implements the same math with reshape + mean
  + variance + scale + shift, **all rank 4**."*

**Recurring theme: tensor rank is the hard constraint.** Rank ≤ 5 for ANE; rank-6 LUTs from
per-channel scale are rejected; rank-6 window reshapes are rejected; rank-5 pairwise-RoPE
intermediates are rejected. **"Keep everything at rank 4" is the single most transferable rule in
the entire vision-authoring story**, and it has no analogue in the LLM material.

Second theme: **f32 literals poison the graph.** `GELUReauthored` stores its coefficients as
module-level f16 tensors *"to avoid f32 constants in the graph"* (`ios/gelu.py:21`);
`BidirectionalSDPA` registers its scale as an f16 buffer for the same reason (`:35-36`);
`LayerNormReauthored` makes `eps` a tensor *"to keep the exported graph free of f32 constants"*
(`ios/layer_norm.py:13-18`); `detr.py:1-18` says *"all f32 literals are stated as f16 buffers"*.

Third theme: **masked value is `-40000.0`, not `-inf`** —
`BidirectionalSDPA` (`ios/bidirectional_sdpa.py:6-13`) and SAM3's text encoder
(`models/ios/sam3/text_encoder.py:6-12`, `_make_causal_mask` at `:22`).

Two more f16-safety notes:
`GELUReauthored` (`ios/gelu.py:6-13`) claims **PSNR ~92 dB** vs exact GELU, *"compared to ~57 dB
for the simpler `x * sigmoid(1.702 * x)`"* — one of only two hard numeric-quality figures anywhere
in the non-LLM material. `ios/embedding.py:186-189` notes `nn.Embedding`'s gather *"requires Int64
indices the runtime won't feed"*, hence the manual `table[input_ids]` float path.

### 9.2 `segmentation/` — the SAM3 export pipeline

Three files. `segmentation/__init__.py:8-20` re-exports `FullExportConfig`,
`SegmentationExportConfig`, `export_full`, `export_segmentation`.

```python
# segmentation/pipeline.py:131-153
@dataclass
class SegmentationExportConfig:
    hf_model_id: str = "facebook/sam3"
    image_size: int = 336
    max_text_seq_len: int = 32
    image_n_bits: int = 4;  image_group_size: int = 32
    text_n_bits:  int = 6;  text_group_size:  int = 8
    output_dir: str = "exports"
    output_name: str | None = None
    overwrite: bool = False

# :346-361
@dataclass
class FullExportConfig:            # image_size=1008, dtype="float32"
    ...

def export_segmentation(config) -> str    # :168
def export_full(config) -> str            # :398
```

Wrapper modules that define the three entrypoints: `ImageEncoderModule` (`:43`),
`TextEncoderModule` (`:54`), `DetectorModule` (`:67`). `DetectorModule.forward(backbone_features,
text_features)` reassembles FPN → DETR-encoder → DETR-decoder → scoring → mask-decoder
(`:79-123`), reshaping FPN level-2 into BC1S at `:88`.

The multi-function converter call (`segmentation/pipeline.py:266-285`) — **this is the code that
answers "how do I put three entrypoints in one `.aimodel`"**:

```python
converter = coreai_torch.TorchConverter()
converter.add_exported_program(img_program, entrypoint_name="image_encode",
    input_names=["pixel_values"], output_names=["backbone_features"])
converter.add_exported_program(txt_program, entrypoint_name="text_encode",
    input_names=["input_ids"], output_names=["text_features"])
converter.add_exported_program(det_program, entrypoint_name="detect",
    input_names=["backbone_features", "text_features"],
    output_names=["pred_masks","pred_boxes","pred_logits","presence_logits","semantic_seg"])
coreai_program = converter.to_coreai()
coreai_program.optimize()
```

Each entrypoint is separately `torch.export`ed, decomposed with `coreai_torch.get_decomp_table()`,
and cast via `cast_to_16_bit_precision` (`:251-263`).

SAM3 model classes under `models/ios/sam3/`. Package docstring (`__init__.py:6-12`):
> *"every component is in **BC1S layout with `nn.Linear` replaced by `nn.Conv2d(1x1)`**,
> GELU/LayerNorm/RoPE re-implemented in fp16-safe primitives, and window-attention partitioning
> kept at rank 4."*

- `Sam3Lite(image_size: int = 336)` (`sam3_reauthored.py:45`), `from_pretrained(...)` (`:134`).
- `ImageEncoderBackbone` (`image_encoder.py:247`) — *"32 transformer layers: 28 window attention
  (24×24 windows) + 4 global attention at indices `[7, 15, 23, 31]`"* (`:6-15`). Patch embed is a
  **two-pass unfold** — *"Pass 1: unfold height. Pass 2: unfold width. Each stays at rank ≤ 5"*
  (`:318-327`). `_linear_to_conv2d` at `:44`.
- `FPNNeckReauthored` (`fpn.py:151`) — scale factors `[4.0, 2.0, 1.0, 0.5]`, sinusoidal
  position encodings precomputed as f16 buffers (`:29`, `:192`).
- `TextEncoderReauthored` (`text_encoder.py:143`) — 24 CLIP layers, BSD→BC1S transpose at `:200`.

Registry oddity: `model_registry.py:282-288` still lists SAM3's `export_script` as
`models/sam3/export.py`, while `segmentation/pipeline.py:18-20` says the new path produces
*"the same shape as `models/sam3/export.py` produced previously, but now with three entrypoints
instead of one `main`"*. SAM3 is **not** in `models/registry.py` (LLM/VLM only) — it is reachable
only via the segmentation CLI + the `UtilityModel` table.

### 9.3 Compression: vision/diffusion vs language

| Target | Mechanism | Cite |
|---|---|---|
| **macOS LLM** | PT2E **quantization**: `int4`, `symmetric_with_clipping`, `per_block block_size=32 axis=1`, applied **pre-`torch.export`**. Default preset `"4bit"`. | `export/presets.py:88-110`, `:151` |
| **iOS LLM** | K-means **palettization**: `n_bits=4`, `per_grouped_channel axis=0`, `group_size` 8 or 32. Default `"4bit_weight_palettized_group32"`. | `export/presets.py:118-147`, `:152` |
| **SAM3 lite (vision)** | K-means palettization, **asymmetric per encoder**: image w4/gs32, text w6/gs8, detector uncompressed fp16 | `segmentation/pipeline.py:144-153`, applied `:217-248` |
| **Diffusion** | **Post-MLIR** `int4` per_block bs=32 symmetric. Default `"none"`. | `diffusion/presets.py:24-40`, applied via `export/compiler.py:29` |
| **VLM vision/embed/decoder** | **none** — f16 cast only | `vlm/export.py` (no compression path) |

Three structural differences vs the LLM path:

1. **Vision compression is per-function, not per-model.** SAM3 compresses each of its three
   entrypoints differently *before* exporting each one.
2. **Diffusion quantizes after MLIR lowering**, not before export —
   `export/compiler.py:29 async def apply_mlir_quantization(coreai_program, quantize_config) -> AIProgram`
   calling `coreai_opt.coreai_utils.quantize_weights(..., weight_num_threshold=32768, in_place=True)`
   (`:59-67`). **Failures are swallowed with a warning, not raised** (`:69-72`) — so a "quantized"
   diffusion export can silently ship full precision.
3. **The VAE is never quantized.** `diffusion/presets.py:11-12`: *"The VAE encoder/decoder is
   small and quality-sensitive, so it is never quantized"*, enforced by
   `ComponentSpec.quantizable: bool = False` (`diffusion/components.py:194`); only
   `text_encoder`, `unet`, `transformer`, `transformer_512`, `text_encoder_2` set it True
   (`:258-397`).

Language-only exclusion lists that do **not** apply to vision (`export/presets.py`):
`_TORCH_MODULE_EXCLUSIONS` (`:31-36`) excludes `macos.sdpa.SDPA`, `macos.rope.RoPE`,
`macos.rms_norm.RMSNorm`, `RMSNormPlusOne` — *"should not be quantized because they use
specialized ops"*; `_IOS_PALETTIZATION_EMBEDDING_EXCLUSIONS` (`:39-42`);
`_TORCH_MOE_SWITCH_LINEAR_4BIT` (`:50-66`), a 4-D `block_size=[1,1,1,32]` MoE override where
*"axis is `None` because block_size is itself multi-dim."*

Modality branches in the shared pipeline: `export/pipeline.py:295-296`
`assert config.variant == "iOS", "palettization is only supported for iOS variant."`;
`export/pipeline.py:188` `use_memory_efficient = config.variant == "macOS"` — the iOS variant
*"keeps the legacy full-RAM path since its palettization flow has not been validated against
streaming weight loading."*

### 9.4 Vision-side export scaffolding beyond SAM3

- `export/macos.py:127`
  `export_to_coreai(model, reference_inputs, dynamic_shapes=None, input_names=None, output_names=None, state_names=None) -> AIProgram`
  — the generic stateful entry point; *"reach for this directly only when you need
  component-specific input/output names that `export_macos_model`'s text-only defaults don't
  fit"* (`:139-142`). The VLM uses it for all three assets.
  `_EXTERNALIZE_SPECS` (`:37-63`) keeps `GatherMM`, `RMSNormImpl`, `RoPE`, `SDPA`,
  `GatedDeltaUpdate` as **named MLIR composites**.
- `export/metadata.py:189`
  `build_aimodel_metadata(hf_model_id: str, component: str | None = None) -> AIModelAssetMetadata`
  — the `component` argument is how a multi-asset diffusion bundle tags which sub-model an asset
  is (`:218-222`); called as
  `build_aimodel_metadata(config.hf_model_id, component=spec.asset_name)`
  (`diffusion/pipeline.py:122`).
- `diffusion/gpu.py:22`
  `export_stateless(wrapper, dummy_inputs, input_names, output_names) -> AIProgram` —
  *"Simpler than the LLM export path: **no KV cache, no dynamic shapes, no externalized
  composites.** Each component is a single fixed-shape forward pass"* (`gpu.py:6-11`).
  **This is the cleanest starting template for exporting any non-LLM model.**
- `export/mlir_ops.py:377 register_custom_torch_lowering(converter)` registers 5 lowerings,
  including `custom_lowering_fused_gather_dequant` (`:287`) emitting a `no_inline` composite with
  IOSurface `interleave=[8,1,1]`, and `custom_lowering_rope_gather_cached_cos_sin` (`:342`) with
  `alignments=[1,1,32,1]`.
- VLM vision tower — `vlm/export.py:405`
  `StaticVisionEncoder(visual_model, *, image_size, patch_size, spatial_merge_size, temporal_patch_size)`:
  *"Avoids all data-dependent operations (linspace, repeat_interleave, etc.) by baking in the
  constant values at init time"*; input f32 `[1,3,S,S]` NCHW, output `[num_visual_tokens, text_hidden]`
  (`:415-416`). `_patchify` (`:466`) reproduces Qwen's exact permute `(0,3,6,4,7,2,1,5,8)`
  *"so the resulting patch order matches both the precomputed `pos_embeds` and the merger's 2×2
  spatial-merge grouping"* (`:469-473`). `BatchedF16VisionEncoder` (`:514`) —
  *"The vision math stays in f32; only the final result is batched and cast to f16"* (`:520`).
  `num_visual_tokens = (image_size // patch_size // spatial_merge_size) ** 2` = 196 for
  `qwen3-vl` (`:70-73`).

### 9.5 What the primitives test suite asserts

`python/tests/test_model_units/test_primitives/` — 3,008 lines, 12 files (8 test modules,
2 conftests, 1 helper).

Both conftests (`test_ios/conftest.py:6-16`, `test_macos/conftest.py:6-16`, identical) set
`USE_HF_IMPL=true` via an autouse module-scoped fixture *"so
`coreai_models.primitives.{ios,macos}.{sdpa,rope,rms_norm}` take the Hugging Face lowering path —
**the only path that gives bit-for-bit parity with HF eager**."* There is an opt-out fixture
`disable_hf_impl_for_coreai` because *"The HF impl decomposes
`F.scaled_dot_product_attention` into **where ops with dynamic-shaped i1 that the Core AI runtime
does not support**"* (`:44-48`). Every test in the tree carries
`pytest.mark.flaky(reruns=5)` (`:24-27`).

The pattern throughout is a paired `test_hf` (torch-vs-HF numeric parity) and `test_coreai`
(export → compile → run on the Core AI runtime), parameterized over
`[float32, float16, bfloat16]`.

Highlights:
- `test_ios/test_sdpa.py:142-172` — the key assertion is a **layout round-trip**: build in
  standard `(B, H, S, D)`, run HF `sdpa_attention_forward`, permute both inputs *and the expected
  output* into BC1S, and compare. Note `:152-154`: *"causal_mask_base is [query, key], but iOS
  needs [key, query]"* → `.t()`. Masked value `-40000` (`:114`). Tolerances HF `1e-3` f16,
  Core AI `5e-3` f16.
- `test_ios/test_rope.py:198` — *"important to set the batch to 2 not 1, **this caught a bug in
  the iOS rope**."*
- `test_ios/test_embedding.py:152` — `test_coreai` is **`pytest.xfail`ed**:
  *"Embedding layer produces incorrect output on this backend."*
- `test_macos/test_switch.py` (790 L, the largest) — three-way parity: pure-torch naive
  references, MLX wrappers, and the primitive, over `bias × num_weight_sets × precision`.
- All macOS test classes are gated on `@pytest.mark.skipif(not HAS_COREAI, …)`.

**Coverage gap worth naming**: there are **no tests** under `test_primitives/` for
`ios/bidirectional_sdpa.py`, `ios/gelu.py`, `ios/layer_norm.py`, `ios/mlp.py`,
`ios/quantization.py`, `ios/rms_norm.py`, `macos/mlp.py`, `macos/cache_scatter.py`, or
`macos/sdpa.py` — i.e. **the vision-facing iOS primitives (BidirectionalSDPA / GELU / LayerNorm)
are entirely untested in this directory.** **UNVERIFIED** whether they are covered elsewhere in
`python/tests/`.

---

## 10. The multi-model / multi-function pipeline story

The repo expresses "more than one model" in **three structurally different ways**. Knowing which
is which is the core of any pipeline guide.

### 10.1 Pattern A — multi-function: several entrypoints in ONE `.aimodel`

**Who:** SAM3 lite only.
**Python side:** `TorchConverter().add_exported_program(..., entrypoint_name=...)` called three
times, then one `to_coreai()` (`segmentation/pipeline.py:266-285`). Also used by the iOS LLM
export with 4 entrypoints (`export/ios.py:219-261`).
**Swift side:** `AIModel.functionNames` → `detectStructure` → `.multiFunctionSegmenter` →
`model.loadFunction(named:)` three times → chained `run()` calls threading raw `NDArray`s
(`ImageSegmentationEngine.swift:871-920`).
**Bundle:** ONE `.aimodel` + `metadata.json` (`kind: "segmenter"`, `assets: {"main": …}`) +
`tokenizer/`.

Why it exists — three reasons, all in the code:
1. **Independent compression per function** — image w4/gs32, text w6/gs8, detect fp16
   (`pipeline.py:9-15`, `:230-248`).
2. **Neural Engine routing** — `.multiFunctionSegmenter` maps to
   `SpecializationOptions(preferredComputeUnitKind: .neuralEngine)`, whereas a single-`main`
   SAM3 is `.dynamic` → GPU (`ModelStructure.swift:71-80`).
3. **Reuse potential** — separating `image_encode` from `text_encode` *allows* caching one while
   varying the other. This is the WWDC26 session-325 "76% faster second inference" claim.
   ⚠ **The shipped `CoreAISegmentationEngine` does not exploit it** — `runMultiFunctionInference`
   re-runs `image_encode` on every `segment()` call and exposes no API to hold the features.
   Realizing the speedup requires calling `imageEncode.run(...)` yourself.

### 10.2 Pattern B — multi-asset: several `.aimodel` files in ONE bundle directory

**Who:** all diffusion pipelines, and the VLM.
**Python side:** a loop over `ComponentSpec`s, one `save_asset` each
(`diffusion/pipeline.py:92-131`), each tagged with
`build_aimodel_metadata(hf_id, component=spec.asset_name)`.
**Swift side:** `PipelineDescriptor.resolve` → `loadComponents(from:)` → one
`CoreAIDiffusionModelFunction` per component (`PipelineDescriptor+CoreAI.swift:44-137`), each an
independent actor with its own `AIModel`, all pinned to `.gpu`.
**Bundle:** N `.aimodel` files + `metadata.json` (`kind: "diffusion"`, `assets` map) +
`tokenizer/` + optional `.npy` sidecars.

**The full FLUX.2 bundle — the most complex layout in the repo:**

```
FLUX.2-klein-4B/
├── metadata.json            {metadata_version:"0.2", kind:"diffusion",
│                             assets:{transformer,text_encoder,vae_decoder,vae_encoder,…},
│                             diffusion:{prediction_type, image_size, rope_axes_dims, rope_theta,
│                                        batch_norm_eps, guidance_embeds,
│                                        default_steps, default_guidance_scale, …},
│                             source:{…}, compression:{…}, compilation:{…}}
├── Transformer.aimodel          (or .aimodelc)   # 1024 — .full / .tiled
├── Transformer_512.aimodel                       #  512 — .half
├── TextEncoder.aimodel                           # Qwen3
├── VAEDecoder.aimodel                            # .full
├── VAEDecoder_half.aimodel                       # .half / .tiled
├── VAEEncoder.aimodel                            # img2img, .full
├── VAEEncoder_half.aimodel                       # img2img, .half / .tiled
├── tokenizer/                                    # HF dir -> AutoTokenizer.from(modelFolder:)
│   ├── tokenizer.json  ...
├── vae_bn_mean.npy                               # VAE batch-norm statistics (raw f32)
└── vae_bn_var.npy
```

Three resolution mechanisms coexist in this one directory:
metadata `assets` map → `descriptor.components`; explicit-name probing
(`resolveAsset(at:name:)` for `Transformer_512`, `VAEDecoder_half`, `VAEEncoder_half`, trying
`.aimodel` then `.aimodelc`); and filename substring auto-detect (`PipelineDescriptor.detect`) as
the last-ditch fallback when there is no metadata at all.

**Orchestration** is the `StableDiffusionPipeline.generateImages` skeleton in §6.5:
encode text (model A, twice) → scheduler (pure Swift) → RNG → denoise loop (model B, N steps, CFG
in Swift) → VAE decode (model C) → `CGImage`. With `lazyModelLoading: true`, each component's
`unloadResources()` is called the moment its stage finishes — **the memory-management pattern to
copy** for any multi-model on-device pipeline.

### 10.3 Pattern C — separate bundles orchestrated by the app

**Who:** the WWDC26 session-326 "SAM 3 + Qwen LLM in one app" story.

> **Finding: this pattern is not expressed anywhere in the repo.** `CoreAISegmentation` and
> `CoreAILM` are separate products with no shared type beyond `CoreAIShared`, no example app, no
> CLI that loads both, and no test that combines them. `Package.swift` has no target depending on
> both. The composition is left entirely to the app author.
>
> The *substrate* for doing it is there and is the reusable part: both products go through
> `ModelBundle` (`kind: "segmenter"` vs `kind: "llm"`), both go through `PreparedModel.prepare`,
> and `PreparedModel`'s structure-driven compute-unit selection means a segmenter lands on the ANE
> while a dynamic LLM lands on the GPU — **so the two models naturally occupy different compute
> units and can overlap.** That is the strongest available argument for the session-326 design,
> and it is inferred from `ModelStructure.swift:57-80`, not stated anywhere. **UNVERIFIED** as a
> deliberate design intent.

### 10.4 Cross-pattern comparison

| | A: multi-function | B: multi-asset | C: multi-bundle |
|---|---|---|---|
| Files on disk | 1 `.aimodel` | N `.aimodel` | N bundles |
| Python API | `add_exported_program(entrypoint_name:)` ×N | `save_asset` ×N | separate CLIs |
| Swift API | `model.loadFunction(named:)` ×N | `CoreAIDiffusionModelFunction` ×N | `ModelBundle` ×N |
| Data between stages | raw `NDArray`, no copy | `[Float]` round-trip | app's choice |
| Per-stage compression | ✅ | ✅ | ✅ |
| Per-stage compute unit | ❌ (one asset, one specialization) | ✅ | ✅ |
| Independent load/unload | ❌ | ✅ | ✅ |
| Example in repo | SAM3 lite, iOS LLM | SD / SD3 / FLUX.2 / VLM | **none** |

The tradeoff worth stating plainly: **multi-function buys you zero-copy tensor handoff and one
file; multi-asset buys you independent memory lifetime and per-component compute units.**
Diffusion needs the memory control (a 4B transformer plus a VAE will not co-reside on a phone),
so it pays the `[Float]` copy. SAM3 needs the zero-copy handoff between encoder and detector, so
it accepts loading all three graphs at once.

---

## 11. iOS vs macOS divergence

Only four `#if` sites exist in the non-LLM Swift, but they matter.

### 11.1 `Float16` does not exist on Intel macOS

The guard, verbatim, appears at 9 sites:

```swift
#if !((os(macOS) || targetEnvironment(macCatalyst)) && arch(x86_64))
    … Float16 path …
#else
    fatalError("Float16 is not supported on this platform")
#endif
```

Sites: `CoreAIShared/Runtime/NDArray+Helpers.swift:86`;
`CoreAIImageSegmenter/ImageSegmentationEngine.swift:597, 685, 696, 949`;
`CoreAIObjectDetector/ObjectDetector.swift:211`;
`CoreAIDiffusionPipeline/Components/CoreAIDiffusionModelFunction.swift:56, 162`;
`Tools/diffusion-runner/DiffusionRunnerMain.swift:752`;
`Tools/image-segmenter/ImageSegmentationRunnerMain.swift:586`.

Consequence: **an fp16 vision model literally cannot run on an Intel Mac** — you get a
`fatalError`, not a graceful degradation. `flattenAsFloat` (`NDArray+Helpers.swift:84-95`)
omits the `.float16` case entirely on x86, so it hits `preconditionFailure`.

### 11.2 Segment bounding boxes flip origin

`SegmentationPostprocessor.decodeSegment` (`:161-177`):

```swift
// AppKit/macOS uses bottom-left origin, so flip Y for macOS.
// UIKit/iOS uses top-left origin matching the model output directly.
#if os(macOS)
box = CGRect(x: x0 * imageWidth, y: (1.0 - y1) * imageHeight,
             width: (x1 - x0) * imageWidth, height: (y1 - y0) * imageHeight)
#else
box = CGRect(x: x0 * imageWidth, y: y0 * imageHeight,
             width: (x1 - x0) * imageWidth, height: (y1 - y0) * imageHeight)
#endif
```

Documented on the property (`SegmentationOutputs.swift:78-81`):
> *"On macOS (AppKit), the origin is bottom-left. On iOS/iPadOS (UIKit), it is top-left, matching
> the model's normalized XYXY output directly."*

**This is the single nastiest cross-platform trap in the repo.** Same code, same model, same
image → different `Segment.box.y` on Mac vs iPhone. And it is **inconsistent within the repo**:
`DetectedObject.boundingBox` is *always* top-left (`DetectionOutputs.swift:34`,
`DetectionPostprocessor.swift:19-20`), and `SegmentationVisualization.renderPromptBoxes` demands
top-left *"regardless of platform"* (`:157`). So on macOS you must **not** feed `Segment.box`
straight into `renderPromptBoxes`.

### 11.3 macOS-only CLI behavior

`Tools/image-segmenter/ImageSegmentationRunnerMain.swift:511-521` — after writing the PNG, the
segmenter CLI shells out to `/usr/bin/open` under `#if os(macOS)`.

### 11.4 Divergence that is NOT in the Swift

Everything else splits **at export time**, not runtime:

| Divergence | Where it lives |
|---|---|
| BC1S / Conv2d / rank-4 authoring | `primitives/ios/` + `models/ios/sam3/` (Python) |
| KV-cache layout (dim 4 vs dim 3) | `primitives/ios/cache.py` vs `primitives/macos/cache.py` |
| Palettization (iOS) vs PT2E quantization (macOS) | `export/presets.py:88-152` |
| FLUX.2 512 vs 1024 component sets | `diffusion/export.py:179-206` |
| Depth Anything = macOS only | `model_registry.py:290-297` |
| SAM3 lite = iOS-targeted | `models/sam3/README.md:5` |
| Streaming weight load (macOS) vs full-RAM (iOS) | `export/pipeline.py:188` |

**So the Swift runtime is almost platform-agnostic; the model is not.** You ship a different
`.aimodel` per platform and the same Swift code loads either. The two real runtime exceptions are
`Float16`-on-Intel and the segment box origin.

---

## 12. Guide topics this material uniquely supports

Ten topics that the LLM-only proposal cannot cover, each anchored to specific files here.

1. **"Run a vision model on Core AI in 40 lines"** — `CoreAIObjectDetector` end to end:
   `AIModel(contentsOf:)` → name discovery → `ImagePreprocessor.preprocessCHW` → batch slots via
   `MutableSpan` → `flattenAsFloat` → softmax/box decode. The whole product is 633 lines with
   zero third-party deps.
2. **The `.aimodel` / model-bundle format, definitively** — `BundleKind` (only 4 kinds),
   `metadata.json` v0.2, the `assets` role map, `FunctionMap`, `.aimodelc` being a directory with
   its own metadata, and the fact that **10 of 15 non-LLM models produce no bundle at all**.
   `ModelBundle.swift`, `PipelineDescriptor.swift`, `Flux2Pipeline+Resources.swift`.
3. **Image ↔ tensor conversion on Apple platforms** — CGContext + vDSP, sRGB pinning,
   `noneSkipLast` vs `premultipliedLast`, NHWC→NCHW, the three resize strategies,
   `interpolationQuality = .high` as the PIL-BICUBIC parity lever, **no `CVPixelBuffer` anywhere**,
   **no EXIF handling anywhere**. `ImagePreprocessor.swift` + `CGImageUtils.swift`.
4. **Structure detection & compute-unit steering** — the `ModelStructure` probe/specialize
   two-phase load, and the finding that *splitting SAM3 into three functions is what routes it to
   the Neural Engine*. `ModelStructure.swift:12-80, 145-218`.
5. **Multi-function vs multi-asset pipelines** — §10's three patterns, with the honest note that
   the shipped segmentation engine does not cache `image_encode` output, so the session-325
   speedup needs caller-side work.
6. **Diffusion on-device, end to end** — the 3-model orchestration loop, CFG in Swift, lazy
   load/unload for memory, `DecodeResolution` full/half/tiled, and how `--platform iOS` at export
   time meets `.half` at runtime through nothing but filenames.
7. **Seed reproducibility across frameworks** — `RNG/` with three ports (MT19937 NumPy, PyTorch,
   Philox/cuRAND) and the explicit "do not refactor without verifying against Python" warning.
   Answers "why is my image different from the diffusers output."
8. **fp16-safe / ANE-safe model authoring** — the rank-≤5 rule (rank-6 LUTs, rank-6 window
   reshapes, rank-5 RoPE intermediates all rejected), `-40000.0` instead of `-inf`, f32 literals
   as f16 buffers, `nn.Linear`→`Conv2d(1×1)`, GELU at 92 dB PSNR, `GroupNorm` reauthored.
   `primitives/ios/`, `models/ios/sam3/`.
9. **Numeric parity testing against PyTorch** — the `--parity-test` harnesses in `image-segmenter`
   and `diffusion-runner`: `.npy` readers in Swift, PSNR + cosine floors (30 dB / 0.999),
   `--trace-inputs` for per-component isolation, and `USE_HF_IMPL=true` on the Python side.
10. **What is missing, and how to build it** — there is **no non-LLM benchmark tool**
    (`Tools/benchmark` is `llm-benchmark`), **no published quality/latency number for any
    vision/audio/diffusion model**, no `BundleKind.speech`, no object-detection visualization in
    the library, and no example combining a vision model with an LLM. Each is a concrete
    build-it-yourself guide.

Bonus angle: **"the same repo, two philosophies"** — vision products discover tensor names by
substring matching and duck-type their capabilities; speech and the diffusion denoiser hardcode
them. Comparing `ImageSegmentationEngine.findTextInputName` against
`WhisperDecoder`'s six literal descriptor lookups is a good lesson in API robustness tradeoffs.

---

## 13. Source inventory

**Read in full (Swift, non-LLM):**
- `swift/Sources/CoreAIShared/` — all 10 files
  (`Bundle/{ModelBundle,BundleKind,FunctionMap}.swift`,
  `Image/{ImagePreprocessor,CGImageUtils}.swift`, `Logger/Logger.swift`,
  `Runtime/{ModelStructure,NDArray+Helpers,ResourceManaging,FileSize}.swift`)
- `swift/Sources/CoreAIImageSegmenter/` — all 9 files including `ImageSegmentationEngine.swift`
  (1292 L) read in three passes
- `swift/Sources/CoreAIObjectDetector/` — all 3 files
- `swift/Sources/CoreAISpeech/` — all 4 files
- `swift/Sources/CoreAIDiffusionPipeline/` — `Pipelines/{Pipeline,PipelineConfiguration,PipelineDescriptor,PipelineDescriptor+CoreAI,StableDiffusionPipeline,Flux2Pipeline+Resources}.swift`,
  `Components/{Components,CoreAIDiffusionModelFunction,CoreAILatentCodec,CoreAITextEncoder,CoreAIDenoiser}.swift`,
  `Schedulers/{Scheduler,SchedulerMath,DiscreteFlowScheduler}.swift`,
  `RNG/RandomSource.swift`, `Tokenizers/BPETokenizer+Reading.swift`
- `swift/Sources/Tools/benchmark/BenchmarkMain.swift`, `Tools/speech-runner/SpeechRunnerMain.swift`

**Read in part:**
- `Tools/image-segmenter/ImageSegmentationRunnerMain.swift` — options, `validate()`, `run()`,
  rendering, output helpers (lines 20-200, 370-400, 500-530)
- `Tools/object-detector/ObjectDetectionMain.swift` — options, `validate()`, `run()`, JSON output
  (lines 25-175)
- `Tools/diffusion-runner/DiffusionRunnerMain.swift` — options + `run()` dispatch (lines 13-200)
- `Package.swift` — products/targets/executables via grep

**Surveyed by delegated agents (findings incorporated, all `path:LINE`-cited):**
- `models/{sam3,efficient-sam,yolo,clip,t5,roberta,pvt,edsr,depth-anything,wav2vec2,clap,whisper,stable-diffusion,flux2,vlm}/`
  — every `README.md` and every `export.py`, plus `models/README.md`
- `python/src/coreai_models/{primitives,segmentation,diffusion,vlm,export,models}/`
- `python/tests/test_model_units/test_primitives/` — all 12 files

**Greps run:** `CVPixelBuffer|CVPixel|IOSurface|CoreVideo`, `orientation|exif|kCGImageProperty`,
`#if os(|targetEnvironment|arch(x86_64)|canImport(AppKit)|canImport(UIKit)` across
`swift/Sources/` and `swift/Tests/`.

**Not read (see Open questions):**
- `CoreAIDiffusionPipeline/Pipelines/Flux2Pipeline.swift` (786 L),
  `SD3Pipeline.swift` (296 L), `SD3Pipeline+Resources.swift` (60 L)
- `Schedulers/{DPMSolverMultistepScheduler,PNDMScheduler}.swift` (290 + 184 L)
- `RNG/{TorchRandomSource,NumPyRandomSource,NvRandomSource}.swift` (129 + 101 + 83 L)
- `Tokenizers/BPETokenizer.swift` (167 L), `DiffusionUtilities.swift` (57 L),
  `Components/CoreAIComponentError.swift` (24 L)
- `swift/Tests/{ImageSegmenterTests,ObjectDetectorTests,DiffusionPipelineTests,CoreAISharedTests}/`
- The bodies of `Tools/{image-segmenter,object-detector,diffusion-runner}` beyond the cited ranges

---

## 14. Open questions / UNVERIFIED

1. **`image_encode` caching.** `CoreAISegmentationEngine.runMultiFunctionInference` re-runs
   `image_encode` on every `segment()` call and exposes no way to reuse `backbone_features`.
   Does the WWDC26 session-325 "76% faster second inference" demo use a different, unshipped API,
   or does it call `InferenceFunction.run` directly? **UNVERIFIED.**
2. **`CVPixelBuffer` / zero-copy image input.** Zero occurrences in `swift/Sources`. Does the
   Core AI SDK support binding an `NDArray` to a `CVPixelBuffer` or `IOSurface` for camera input?
   If so, this repo never uses it and every vision path pays a full CGContext render +
   Float32 copy. **UNVERIFIED.**
3. **EXIF / image orientation.** No handling anywhere. `CIImage(contentsOf:)`
   (`ImagePreprocessor.preprocess(imageURL:)`) applies EXIF orientation;
   `CGImageSourceCreateImageAtIndex` (the CLI tools) does not. Is this a known bug or does the
   SDK normalize upstream? **UNVERIFIED.**
4. **`Segment.box` platform flip.** Deliberate per the comment, but it makes `Segment.box`
   incompatible with `SegmentationVisualization.renderPromptBoxes` on macOS and inconsistent with
   `DetectedObject.boundingBox`. Intentional or an unreconciled inconsistency? **UNVERIFIED.**
5. **SD1/2 img2img.** `StableDiffusionPipeline.supportsImageToImage` returns true when a VAE
   encoder exists, but `generateImages` never reads `configuration.startingImage`. Is img2img
   handled elsewhere (`diffusion-runner` has `--input-image`), or is this dead capability?
   **UNVERIFIED** — `diffusion-runner`'s img2img code path was not read in full.
6. **`CoreAILatentEncoder` latent channels.** Hardcodes `[1, 4, H/8, W/8]`
   (`CoreAILatentCodec.swift:108`) — correct for SD1/2, wrong for SD3 (16 ch) and FLUX.2 (32 ch).
   Do `SD3Pipeline` / `Flux2Pipeline` bypass this class entirely? Both were unread. **UNVERIFIED.**
7. **`.pad` strategy padding semantics.** `ImagePreprocessor.preprocessCHWPad` pads with zeros in
   *pixel* space, which becomes `(0−mean)/std` after normalization rather than tensor-space zero.
   Does any shipped model depend on tensor-space zero padding? **UNVERIFIED.**
8. **`ImageStrategy` is declared in `CoreAIShared` but never used by the segmenter or detector** —
   both call `preprocessCHW(cgImage:)` (implicit `.stretch`). Only the VLM path
   (`llm-runner --image-strategy`) consumes it. Are `.centerCrop` / `.pad` dead code for the
   non-LLM products? Appears so; **UNVERIFIED.**
9. **`FunctionMap` in non-LLM bundles.** Declared in `CoreAIShared` and used by the LLM bundle
   (`function_map: {"main": ["main"]}`), but no non-LLM bundle writer emits one, and no non-LLM
   Swift reader consumes one. Dead for vision/diffusion? **UNVERIFIED.**
10. **`ModelBundle.ComponentKey.vision` / `.embedding`** exist but are consumed only by the VLM
    path in `CoreAILanguageModels`. No non-LLM product reads them.
11. **Diffusion quantization silently failing.** `export/compiler.py:69-72` swallows
    `apply_mlir_quantization` errors with a warning. How would a user notice that a `--compression
    4bit` FLUX.2 export actually shipped fp16? File size is the only signal. **UNVERIFIED**
    whether `metadata.json`'s `compression` block records the *attempted* or *achieved* setting.
12. **Speech bundle format.** No `BundleKind.speech`, no `metadata.json`, tokenizer resolved from
    `~/.cache/huggingface/hub`. Is `CoreAISpeech` pre-release / not intended for app shipping?
    No test target exists for it. **UNVERIFIED.**
13. **`MelSpectrogram` DFT-by-GEMV.** `cblas_sgemv` against a dense `[201 × 400]` basis, twice per
    frame, 3000 frames — O(n²) where an FFT is O(n log n). Deliberate (Accelerate GEMV is very
    fast, and it avoids `vDSP_DFT` setup lifetime management) or just unoptimized? **UNVERIFIED.**
14. **`whisper` model → `CoreAISpeech` mapping.** `models/whisper/export.py` produces a single
    `.aimodel` with `main`, matching `speech-runner`'s **legacy** path. Nothing in the repo
    produces the `encoder.aimodel` + `decoder.aimodel` split bundle that `SpeechBundle` requires.
    Where does that split export live? **UNVERIFIED — apparently missing from this repo.**
15. **`--trace-inputs`** (`diffusion-runner`) — the mode was identified but its directory format
    and per-component semantics were not read. **UNVERIFIED.**
16. **`AIModelAsset.summary(includingStatistics:)`** — used by `probeStructure` to read function
    names without specializing. What else does the summary expose (op counts, weight sizes,
    compute-unit hints)? Would make a much better `benchmark` tool. **UNVERIFIED** (SDK API).
17. **Core AI SDK types** consumed but not defined here: `AIModel`, `AIModelAsset`,
    `AIProgram`, `InferenceFunction`, `InferenceFunctionDescriptor`, `NDArray`,
    `NDArrayDescriptor`, `SpecializationOptions`, `AIModelAssetMetadata`, `HardwareConstraints`,
    `AllocationType`, `InferenceFunction.MutableViews`. Their full signatures need the SDK.
    Same caveat as the prior notes file's §21.3.
18. **Vision-facing iOS primitives are untested** — no tests for `BidirectionalSDPA`, `gelu`,
    `layer_norm`, `mlp`, `rms_norm` (iOS) under `test_primitives/`. **UNVERIFIED** whether
    coverage exists elsewhere under `python/tests/`.
19. **`models/sam3/export.py` vs `segmentation/pipeline.py`** — `model_registry.py:282-288` still
    points `export_script` at the former while the latter is the real implementation. Is the
    registry entry stale? **UNVERIFIED.**
20. **No non-LLM quality baselines anywhere.** Confirmed by search across `models/**/README.md`.
    Any accuracy claim about SAM3-lite-w4 vs SAM3-full, or 4-bit FLUX.2 vs fp16, would have to be
    measured — the repo publishes none.
