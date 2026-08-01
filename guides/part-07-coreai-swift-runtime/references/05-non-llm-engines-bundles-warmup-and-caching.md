# Non-LLM engines: bundles, function structure, warmup, specialization, and caching

**Part 7 · Core AI: the Swift runtime · Reference 05**

**Version floor: everything in this guide is 27.0 and only 27.0.** The low-level `CoreAI` framework
supports Apple's 27.0 platforms, but the optional `apple/coreai-models` package discussed here declares
only **iOS 27.0 and macOS 27.0**, requires **Xcode 27**, uses Swift 6 language mode, and has no
watchOS, tvOS, visionOS, or Mac Catalyst product. This guide is verified against the pinned checkout at
commit **`5ed9981`** (2026-07-23). It describes that package's implementation policy, not a promise that
the Core AI framework will route every similarly named model the same way.

This is the missing non-language-model half of Part 7. Apple's package ships three non-LLM
runtime products relevant here:

- `CoreAISegmentation` / module `CoreAIImageSegmenter`
- `CoreAIObjectDetection` / module `CoreAIObjectDetector`
- `CoreAIDiffusion` / module `CoreAIDiffusionPipeline`

`CoreAISpeech` is adjacent but architecturally different: it owns an encoder/decoder streaming state
machine and an unresolved exporter gap, so [Part 16](../../part-16-adjacent-capabilities/references/01-speech-analyzer-end-to-end.md)
owns the speech decision. This guide uses speech only to show where the common bundle vocabulary stops.

> ⚠️ **Do not turn the sample package's classifier into a framework routing rule.** In
> `apple/coreai-models`, a three-function segmentation asset is loaded with a Neural Engine preference
> and a single-`main` dynamic asset is loaded with a GPU preference. That mapping lives in
> `CoreAIShared/Runtime/ModelStructure.swift`; it is an optional package's loader policy. Core AI itself
> still accepts explicit `SpecializationOptions`, and `AIModel(contentsOf:)` without options uses the
> framework default.[^sample-routing-policy]

---

## Contents

1. [One repository, three runtime shapes](#1-one-repository-three-runtime-shapes)
2. [Bundle directory, model asset, and function map](#2-bundle-directory-model-asset-and-function-map)
3. [`PreparedModel`: inspect before specializing](#3-preparedmodel-inspect-before-specializing)
4. [Segmentation: one function or a three-function graph](#4-segmentation-one-function-or-a-three-function-graph)
5. [Object detection: one raw asset, one real warmup](#5-object-detection-one-raw-asset-one-real-warmup)
6. [Diffusion: a bundle of independently owned models](#6-diffusion-a-bundle-of-independently-owned-models)
7. [Warmup is not one operation](#7-warmup-is-not-one-operation)
8. [Specialization and caching, layer by layer](#8-specialization-and-caching-layer-by-layer)
9. [Choosing a function and bundle structure](#9-choosing-a-function-and-bundle-structure)
10. [Production checklist](#10-production-checklist)
11. [Gaps and device tests still required](#11-gaps-and-device-tests-still-required)
12. [Sources and evidence ledger](#12-sources-and-evidence-ledger)

---

## 1. One repository, three runtime shapes

All three products sit on the same basic stack:

```text
product facade                 ImageSegmenter / ObjectDetector / StableDiffusionPipeline
        ↓
engine or components           CoreAISegmentationEngine / one detector function / diffusion actors
        ↓
CoreAIShared where used        PreparedModel / ModelBundle / NDArray helpers / image preprocessing
        ↓
CoreAI                         AIModel → InferenceFunction → NDArray
```

The resemblance stops at the second row. Their actual ownership and loading strategies are different:

| Product | Asset shape | Loader | Compute preference in this package | Public preparation operation |
|---|---|---|---|---|
| Segmentation, baseline or EfficientSAM | one `.aimodel`, function `main` | `PreparedModel.prepare` | GPU + `expectFrequentReshapes = true` after classifying it `.dynamic` | `warmup()` runs a dummy forward |
| Segmentation, lite SAM3 | one `.aimodel`, functions `image_encode`, `text_encode`, `detect` | `PreparedModel.prepare` | Neural Engine | `warmup()` runs all three functions |
| Object detection | one raw `.aimodel`, function `main` | direct `AIModel(contentsOf:)` | no explicit option; framework default | `warmup(imageCount:parameters:)` runs a shape-matched forward |
| Diffusion | several component `.aimodel` assets, each with `main` | one `CoreAIDiffusionModelFunction` actor per component | GPU, explicitly, for every component | `loadResources` loads; `prewarmResources` loads then unloads; no pipeline dummy-forward warmup |

This table is the answer to the first design question: **“using Core AI” does not imply one engine,
one bundle, one compute-unit choice, or one meaning of warmup.** Keep those choices explicit in your own
adapter instead of hiding them behind a single `prepare()` boolean.

The two simplest products have no third-party runtime dependency: `CoreAISegmentation` and
`CoreAIObjectDetection` depend only on `CoreAIShared`, which itself has none. They are the cleanest
Apple-authored examples of turning `CGImage` into descriptor-shaped NDArrays and decoding the outputs.

---

## 2. Bundle directory, model asset, and function map

Three nouns are easy to collapse and should stay separate:

1. A **model asset**, `.aimodel` or `.aimodelc`, contains one or more named functions.
2. A **model bundle directory** contains `metadata.json`, an `assets` role-to-filename map, and optional
   sidecars. It can point to one asset or several.
3. A **function map** maps logical roles to physical function names *inside* an asset.

`ModelBundle` parses common schema `0.2` fields: `kind`, `name`, optional `user_data`, and
`assets: [String: String]`. It preserves the raw JSON so a product-specific reader can decode its own
block. Its `BundleKind` enum has exactly four cases:

```swift illustrative
enum BundleKind {
    case llm
    case vlm
    case diffusion
    case segmenter
}
```

There is no `speech` case and no `detector` case. That is not proof those products cannot be shipped;
it means this shared metadata envelope is not their universal loader contract. The detector takes a raw
asset URL. `SpeechBundle` has its own encoder/decoder expectation outside `BundleKind`.

### 2.1 The assets map is operational, not descriptive

The map must name the file that is actually on disk:

```json
{
  "metadata_version": "0.2",
  "kind": "diffusion",
  "name": "Example",
  "assets": {
    "text_encoder": "TextEncoder.aimodelc",
    "transformer": "Transformer.aimodelc",
    "vae_decoder": "VAEDecoder.aimodelc"
  }
}
```

If `coreai-build compile` changes `TextEncoder.aimodel` into an architecture-qualified compiled
directory, update the map. `ModelBundle.verify()` checks every declared asset and gives specific
compiled-filename guidance. Passing a `.aimodel` or `.aimodelc` where a bundle directory is expected
produces a dedicated `pointedAtModelAsset` error before its internal metadata can be mistaken for bundle
schema `0.1`.

> ⚠️ **SILENT FAILURE — stale bundle metadata can select an unintended file.** A directory scan in the
> diffusion fallback matches filenames by substrings such as `text_encoder`, `transformer`, `unet`, and
> `vae_decoder`. If old and new exports coexist, enumeration order is not a version policy. Prefer a
> schema-`0.2` `assets` map, verify it at packaging time, and remove stale artifacts from the shipped
> bundle rather than relying on scan order.

### 2.2 `FunctionMap` is an escape hatch with limited evidence

`FunctionMap` stores `[logicalRole: [physicalName]]`; `name(for:)` returns the first and
`names(for:)` returns all. The source describes it as an override for models that do not follow naming
conventions. The verified consumer in the language-model path reads the `main` override. None of the
three non-LLM engine implementations in this guide consumes it:

- segmentation recognizes literal `main`, or the literal trio `image_encode` / `text_encode` /
  `detect`;
- detection loads literal `main`;
- each diffusion component loads literal `main`.

Treat conventional function names as part of the exported asset's ABI. Do not assume a
`function_map` entry renames a non-LLM function until a consumer in your exact package version proves it.

---

## 3. `PreparedModel`: inspect before specializing

Segmentation does not load blindly and inspect later. `PreparedModel.prepare(at:)` uses a two-pass
sequence:

1. Open `AIModelAsset` and request `summary(includingStatistics: false)`.
2. Read the function names without specializing.
3. Classify the structure and derive `SpecializationOptions`.
4. Load `AIModel(contentsOf:options:)`, which may specialize or recover a matching cache entry.
5. Re-detect from the loaded model's `functionNames`, now the source of truth.

The classifier's order matters:

```text
extend_* + load_embeddings              → chunkedStatic(batchSize:) → prefer Neural Engine
image_encode + text_encode + detect     → multiFunctionSegmenter    → prefer Neural Engine
main                                    → dynamic                    → prefer GPU + frequent reshapes
anything else                           → dynamic, with a warning    → prefer GPU + frequent reshapes
```

The trio is checked before `main` because some multi-function segmenter variants also contain a thin
`main`. A generic “if `main` exists, load it” probe therefore selects the wrong path for those assets.

If the summary request throws, returns `nil`, or yields no functions, the loader falls back to
`.dynamic`. That fallback is deliberately permissive, but it changes the specialization choice before
the loaded model can be inspected.

> ⚠️ **SILENT PERFORMANCE FAILURE — a failed pre-specialization probe becomes a GPU policy.** The
> fallback does not fail closed. A multi-function asset whose summary cannot be read is loaded with
> dynamic-model options; only after loading is its real structure detected. Log the probed structure,
> loaded function names, and chosen options in production diagnostics. If the distinction matters to
> your product, fail or require an explicit override rather than silently accepting `.dynamic`.

The reusable design is not the literal names. It is **metadata-only inspection before choosing the
specialization key**, followed by validation against the loaded artifact. If you create your own
classifier, make its version part of your telemetry: changing the classifier can create a second cache
entry for the same source asset because options are part of the key.

---

## 4. Segmentation: one function or a three-function graph

`CoreAISegmentationEngine` supports two backends chosen from the `PreparedModel.structure` result.

### 4.1 Single-function backend

A baseline SAM3 or EfficientSAM export exposes `main`. The engine inspects the descriptor to decide
whether the prompt is text-shaped or point-shaped, loads that function, and builds one call containing
image plus prompt inputs. Capabilities come from the inputs, not from a model-family string:

| Shape | Text query | Point query | Precomputed embeddings | Package specialization policy |
|---|---:|---:|---:|---|
| Baseline SAM3, `main` | yes | no | descriptor-dependent | dynamic → GPU + frequent reshapes |
| EfficientSAM, `main` | no | yes | no | dynamic → GPU + frequent reshapes |
| Lite SAM3 trio | yes | no | no public high-level path | multi-function → Neural Engine |

This descriptor-driven capability check is worth copying. It fails at initialization if a
text-capable engine is constructed without the tokenizer, and `segment` rejects an unsupported prompt
kind before inference.

### 4.2 Multi-function backend

The lite export uses one model asset and three independently loadable functions:

```text
image NDArray ──▶ image_encode ──▶ backboneFeatures ──┐
                                                     ├──▶ detect ──▶ masks, boxes, logits, …
token NDArray ──▶ text_encode  ──▶ textFeatures ──────┘
```

The intermediate values remain `NDArray`s. The engine takes them out of one function's `Outputs` and
passes them directly to `detect`, avoiding the `[Float]` round-trip used by the diffusion pipeline.
All three functions share one specialized `AIModel`, so this design gives one asset identity and one
specialization choice while still exposing stage boundaries.

Input and output roles are inferred with substring helpers, then the first match is used. The engine
checks scalar category for critical arrays and throws when required roles are absent, but it cannot
know whether two plausible names carry different semantics.

> ⚠️ **SILENT FAILURE — ambiguous tensor names pick the first match.** A re-export that leaves both an
> old and a new “backbone feature” output can wire the wrong tensor without a missing-name error. Add a
> bundle-level ABI test that asserts the exact input/output name sets and descriptors for every shipped
> model version. Substring discovery is a compatibility convenience, not a substitute for an ABI lock.

### 4.3 The advertised reuse is not implemented by the high-level API

Splitting the graph makes different call cadences *possible*: encode an image once, then issue several
text prompts against the cached backbone. WWDC26 session 325 attributes a **76% faster second
inference** to that shape. But `ImageSegmenter.segment` calls the engine's private
`runMultiFunctionInference`, and that method runs `image_encode`, then `text_encode`, then `detect`
every time. It exposes neither `backboneFeatures` nor a cache handle.

> ⚠️ **SILENT PERFORMANCE FAILURE — `segment` re-encodes an unchanged image.** Repeating prompts for
> the same image looks semantically correct and receives no diagnostic, but does not obtain the reuse
> benefit that motivated the split. To realize it, own the three `InferenceFunction`s directly, cache
> the image encoder's `NDArray`, define invalidation by image identity and model version, and measure
> the memory cost. The package's public segmentation facade does not provide that cache.

This is also the boundary between **function structure** and **application caching**. Core AI may cache
specialization artifacts; it does not infer that two calls contain the same image and memoize an
intermediate tensor for you.

---

## 5. Object detection: one raw asset, one real warmup

`ObjectDetector` is intentionally simpler than the segmenter:

- initialization takes a raw model URL, not `ModelBundle`;
- it calls `AIModel(contentsOf: modelURL)` with no explicit specialization options;
- it requires `main`, discovers image/logits/boxes names from its descriptor, and retains that one
  function;
- dynamic batch and spatial dimensions are resolved from `DetectionParameters` for each planned call.

The absence of explicit options is meaningful. Do not describe the detector as “GPU-routed by the
package”; it delegates compute selection to the Core AI framework default. If you need deterministic
specialization identity across several call sites, wrap or fork the loader so they all construct the
same explicit options.

Its public warmup is the clearest warmup contract in the repo:

> 🟡 **RECONSTRUCTED composition** — assembled from the verified `ObjectDetector` initializer and
> `warmup(imageCount:parameters:)` API; it is not a verbatim Apple sample.

```swift prelude:external-module
import CoreAIObjectDetector

let detector = try await ObjectDetector(resourcesAt: modelURL.path)
try await detector.warmup(
    imageCount: expectedBatchSize,
    parameters: detectionParameters
)
```

For dynamic models, this performs a real zero-filled forward pass with the same `(B, H, W)` that later
calls will use. For static models, descriptor dimensions win and the arguments are ignored. A warmup at
batch 1 and 640×640 therefore says little about the first request at batch 8 and 1024×1024.

> ⚠️ **SILENT FAILURE — malformed detector output becomes “no objects.”** The postprocessor returns an
> empty array when logits are not rank 3, query/class counts are invalid, or flat logits/box lengths do
> not match the declared shape. That is indistinguishable from a valid scene with no detections. Assert
> output descriptors when accepting a new asset, log decode-shape rejection separately from a genuine
> empty result, and include a known-positive image in release validation.

Warmup belongs after the production parameters are known. The bundled CLI follows that rule by warming
the real batch size rather than calling a parameterless convenience method.

---

## 6. Diffusion: a bundle of independently owned models

Diffusion is a multi-asset pipeline, not a multi-function asset. A typical bundle maps roles such as
`text_encoder`, `text_encoder_2`, `transformer` (or legacy `unet`), `vae_decoder`, and optional
`vae_encoder` to separate model directories.

### 6.1 Descriptor resolution has three tiers

`PipelineDescriptor.resolve(at:config:)` uses this order in `.auto` mode:

1. Read schema-`0.2` `metadata.json` and its `diffusion` block plus `assets` map.
2. If legacy `pipeline.json` exists, throw a migration error; it is no longer an automatic fallback.
3. Otherwise scan filenames for recognized component substrings.

Explicit configuration can still be supplied as a descriptor or file. For shipped bundles, prefer
metadata over scanning: it makes component identity reviewable and prevents an old export from winning
a substring match.

### 6.2 Each component owns its own Core AI lifetime

`CoreAIDiffusionModelFunction` is an actor holding one model URL, optional `AIModel`, optional
`InferenceFunction`, and an `isLoaded` flag. `loadResources()` is idempotent, constructs
`SpecializationOptions(preferredComputeUnitKind: .gpu)`, loads the model, and loads `main`.
`unloadResources()` nils both objects.

> 🟡 **RECONSTRUCTED composition** — assembled from the verified pipeline lifecycle and generation
> APIs; it is not copied verbatim from the package.

```swift prelude:external-module
import CoreAIDiffusionPipeline

let pipeline = try await StableDiffusionPipeline.load(from: bundleURL)

// Keep all component models resident for this generation session.
try await pipeline.loadResources()

let result = try await pipeline.generateImages(configuration: configuration) { progress in
    !Task.isCancelled
}
await pipeline.unloadResources()
```

The linear example makes the boundary visible; production code must also unload on the throwing path,
normally in the actor or session owner that controls the pipeline's lifetime.

This structure permits component-specific lifetimes, but the package does not vary compute unit by
component: text encoders, denoisers, and VAE codecs all explicitly prefer GPU.

### 6.3 Eager residency versus lazy stage residency

`StableDiffusionPipeline.loadResources()` loads text encoder, denoiser, decoder, and optional encoder.
When `PipelineConfiguration.lazyModelLoading` is enabled, generation instead lets components load on
demand and unloads them after their last stage:

```text
text encode ── unload text encoder
       ↓
denoising loop ── unload denoiser
       ↓
VAE decode ── unload decoder
```

Unloading releases the package's `AIModel` and `InferenceFunction` references. It does **not** mean
“delete the Core AI specialization cache.” A later load may still recover the device-specialized
artifact, while paying model/function load and residency costs again.

The pipeline also crosses a different memory boundary from segmentation. Its component wrapper exposes
a `[Float]` API: it copies arrays into NDArrays before a model call and flattens results back afterward.
The scheduler and classifier-free guidance operate on Swift arrays. Segmentation, by contrast, threads
intermediate NDArrays directly between functions in one model.

> ⚠️ **SILENT PERFORMANCE FAILURE — lazy loading can trade memory for repeated stage-load latency.**
> Results remain correct, but repeated generation requests reload every component after the previous
> request discarded it. Measure resident memory, load latency, and steady-state request cadence on the
> target device. Use eager residency for an active generation session; use lazy loading when avoiding
> jetsam is worth the reload cost.

---

## 7. Warmup is not one operation

The package uses three similar words for different work. Keep them distinct in logs and telemetry:

| Operation | What it proves or warms | What it does not prove |
|---|---|---|
| `AIModel(contentsOf:options:)` | a matching specialization exists or can be produced; model object loads | that a particular function executes successfully at production shapes |
| `loadFunction(named:)` | the named function exists and its weights/resources load | that kernels for a real run are hot |
| segmentation `warmup()` | dummy forward through the selected single function or all three functions | production image/prompt distributions; image-encoder reuse |
| detector `warmup(imageCount:parameters:)` | zero-input forward at the resolved batch/spatial shape | other dynamic shapes |
| `ResourceManaging.prewarmResources()` | `loadResources()` succeeds, then package references are dropped | an inference forward; production-shape kernel execution |
| diffusion `loadResources()` | all component models and `main` functions load | a full text→denoise→decode pass |

`prewarmResources()` is literally load followed by unload. It may warm filesystem pages, driver/JIT
work, or Core AI's specialization cache as consequences of loading, but it is not equivalent to the
dummy forward performed by segmentation and detection.

A production preparation state machine should name its milestones:

```swift illustrative
enum PreparationMilestone {
    case specializationReady
    case functionsLoaded
    case productionShapeExecuted
    case featureCachePopulated
}
```

Do not store them as one `isWarm` flag. They have different invalidation rules: an OS update can remove
specializations; memory pressure can evict resident functions; a new dynamic shape can be cold; a new
image invalidates segmentation backbone features.

---

## 8. Specialization and caching, layer by layer

There are at least four things an app may call “the cache”:

| Layer | Key or identity | Owned by | Survives package `unloadResources()`? |
|---|---|---|---:|
| Core AI specialization cache | source asset plus `SpecializationOptions`, device/OS context | Core AI / `AIModelCache` | yes, unless evicted or deleted |
| resident `AIModel` and `InferenceFunction` | object lifetime | your engine or component actor | no |
| warm execution state | function, shape, kernels and driver state | runtime/device | unspecified; measure |
| semantic intermediate cache | model version + input identity + preprocessing contract | your app | only if you implement it |

### 8.1 Options are part of identity

Segmentation's package path supplies one of two option values. Diffusion supplies GPU preference.
Detection supplies no explicit options. Those paths can create distinct specialization identities even
when pointed at the same underlying asset. Centralize loading if the same asset is shared across
features, and log an option fingerprint beside the asset version.

Before a user-interactive load, use the readiness probe from
[7.2](02-specialization-caching-and-aot.md): `AIModelCache.model(for:options:)` checks for a compatible
entry without triggering specialization. None of these non-LLM facades exposes that check, so an app
that needs preparation UX must retain the asset URL and exact options outside the facade.

### 8.2 Unload is not cache deletion

Diffusion's unload only clears object references. It does not call `AIModelCache.delete*`. Conversely,
deleting a specialization entry is not a safe substitute for releasing functions. The framework docs
still conflict on deletion while a live model references the entry; [7.2 §7](02-specialization-caching-and-aot.md)
keeps the unresolved device test and code that is correct under either behavior.

### 8.3 AOT changes packaging, not the function contract

An `.aimodelc` can reduce work left for the device, but the containing `metadata.json` must reference
the compiled filename and the runtime still loads named functions. AOT does not add `image_encode`
reuse, turn a multi-asset diffusion pipeline into zero-copy execution, or validate postprocessing.

### 8.4 Cache explicitly at application boundaries

Only cache a semantic intermediate when all of these are part of the key:

- immutable model/export identity;
- specialization/options identity if layout or compute choice can affect compatibility;
- normalized input identity **after** orientation and resizing;
- preprocessing version, color space, and normalization;
- function name and output descriptor.

For segmentation, cache `backboneFeatures` only behind a type that also owns the `AIModel` or function
lifetime required by that array. For diffusion, keeping a denoiser resident is normally more valuable
than memoizing one step's output because timestep, latents, prompt embeddings, guidance, and scheduler
state all participate in the result.

---

## 9. Choosing a function and bundle structure

The source demonstrates three patterns rather than one winner:

| Pattern | Best when | Advantages | Costs |
|---|---|---|---|
| One asset, one `main` | the graph always runs as a unit | smallest loader; one descriptor contract | no stage-specific reuse or lifetime control |
| One asset, several functions | stages share a specialization and exchange NDArrays | direct intermediate handoff; app can choose cadence | fixed naming ABI; all functions share compute preference and model lifetime |
| Several assets, one `main` each | components need independent residency, updates, or specialization | release stages under memory pressure; replace components independently | multiple loads; bundle metadata; possible array/copy boundaries |

Choose **multi-function** when the boundaries are stable, intermediates should stay device-native, and
the app genuinely calls stages at different cadences. Choose **multi-asset** when memory lifetime or
component replacement dominates. Do not split merely because a pipeline diagram has boxes: every split
creates a versioned function or asset ABI that packaging and validation must preserve.

A fourth pattern—several bundle directories orchestrated by the app—is possible but has no worked
non-LLM example in the pinned Apple package. If you use it, your app owns compatibility negotiation and
atomic update behavior across bundles.

---

## 10. Production checklist

### At export and packaging time

- Record the exact function-name set and every input/output descriptor as a checked artifact.
- Prefer schema-`0.2` metadata over filename scanning.
- Run `ModelBundle.verify()` or an equivalent file-existence check in CI.
- After AOT compilation, update `assets` to the `.aimodelc` filename actually shipped.
- Reject duplicate or ambiguous role-like tensor names.
- Version preprocessing and postprocessing with the model, not only in app code.

### At preparation time

- Decide the exact `SpecializationOptions` in one place and use them for both readiness probing and load.
- Separate “specialization ready,” “function loaded,” and “production shape executed” in telemetry.
- Warm the detector using the actual batch and spatial parameters.
- Expect segmentation warmup to execute the whole selected backend.
- Decide diffusion residency from a measured memory/latency budget; do not assume lazy is faster.

### At inference time

- Log selected backend, function names, descriptors, option fingerprint, and first-run timings.
- Bound concurrency; several simultaneously loaded component functions multiply resident memory.
- Distinguish detector decode rejection from a valid empty scene.
- Cache segmentation image features only with explicit input/model/preprocessing invalidation.
- Normalize `CGImage` orientation before either vision product; the package does no EXIF handling.

### Before release

- Run a cold-specialization test and a warm-cache test on each supported device family.
- Re-run after an OS update, which can invalidate specialization artifacts.
- Include known-positive segmentation and detection images, not only “did not throw.”
- Measure first request, second same-shape request, changed-shape request, and memory after unload.
- Test the exact shipped bundle after signing/copying, not an export directory on the development Mac.

---

## 11. Gaps and device tests still required

| Unknown | What would settle it | Safe default |
|---|---|---|
| Live-model cache deletion behavior | delete a cache entry while a loaded non-LLM function remains alive, on device | release functions before deletion; follow 7.2's recovery ladder |
| Whether failed `AIModelAsset.summary` materially misroutes a trio asset | corrupt or block the summary path while preserving loadability; trace compute unit | treat fallback as observable and allow an explicit policy |
| How much `prewarmResources` preserves after immediate unload | cold/warm Instruments trace per component and device | call it load/unload prewarm, not inference warmup |
| The memory and latency crossover for diffusion lazy loading | repeated generations under memory pressure on each supported device | eager during an active session, lazy only from measured need |
| Safe lifetime for cached segmentation NDArrays after model/function release | device test accessing cached backbone features across teardown/reload | bind cached features to the engine lifetime |
| Non-LLM baseline performance | a real segmentation/detection/diffusion benchmark harness | publish your own device, OS, model, shape, and quality data |

The last row matters: the repository's tool is **`llm-benchmark`**, imports
`CoreAILanguageModels`, and has no non-LLM sibling. The repo publishes no controlled latency or quality
number for these products. WWDC's 76% segmentation reuse result is evidence for one restructuring, not
a general throughput baseline.

---

## 12. Sources and evidence ledger

### Primary source read on disk

`apple/coreai-models` @ `5ed9981303b38d5a44aa6b45509bc4f6945029f5`:

- `Package.swift`, `.spi.yml`, `models/README.md`
- `swift/Sources/CoreAIShared/Bundle/{BundleKind,FunctionMap,ModelBundle}.swift`
- `swift/Sources/CoreAIShared/Runtime/{ModelStructure,ResourceManaging}.swift`
- `swift/Sources/CoreAIImageSegmenter/{ImageSegmenter,ImageSegmentationEngine}.swift`
- `swift/Sources/CoreAIObjectDetector/{ObjectDetector,DetectionPostprocessor}.swift`
- `swift/Sources/CoreAIDiffusionPipeline/Components/CoreAIDiffusionModelFunction.swift`
- `swift/Sources/CoreAIDiffusionPipeline/Pipelines/{PipelineDescriptor,StableDiffusionPipeline}.swift`
- `swift/Sources/Tools/{ImageSegmenter,ObjectDetector,DiffusionRunner}/`

Repository-wide synthesis and source inventory:
[`notes/repos/coreai-models-nonllm.md`](../../../notes/repos/coreai-models-nonllm.md).

### Apple presentation evidence

- WWDC26 session 324, **Meet Core AI** — framework object model and the `coreai-models` package.
- WWDC26 session 325, **Dive into Core AI model authoring and optimization** — SAM3 three-function
  split and the reported 76% faster second inference.
- WWDC26 session 326, **Core AI app features** — model preparation and deployment framing.

### Evidence boundaries

- Function names, loader choices, lifecycle, and silent-return paths above are ✅ verified against the
  pinned source.
- The 76% number is 🟡 Apple-presented and lacks a hardware/model-condition table in the transcript.
- Cache persistence, deletion with live models, and warmup effects beyond the executed source are 🔴
  device gaps; the guide does not infer them from API names.

---

*Part 7 · Reference 05. Verified against `apple/coreai-models` @ `5ed9981` and the captured Xcode 27.0
beta SDK interfaces. Guide compiled 2026-08-01.*

[^sample-routing-policy]: The classifier and preferences are implemented in the optional
    `apple/coreai-models` package's pinned
    [`ModelStructure.swift`](https://github.com/apple/coreai-models/blob/5ed9981303b38d5a44aa6b45509bc4f6945029f5/swift/Sources/CoreAIShared/Runtime/ModelStructure.swift#L12-L218).
    Core AI's framework-level specialization behavior is covered separately in
    [7.2](02-specialization-caching-and-aot.md).
