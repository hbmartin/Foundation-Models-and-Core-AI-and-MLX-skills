---
title: Managing model specialization and caching
description: Configure model specialization, manage cached assets, and reduce your app’s storage footprint.
source: https://developer.apple.com/documentation/coreai/managing-model-specialization-and-caching
timestamp: 2026-07-27T17:32:07.227Z
---

**Navigation:** [Coreai](/documentation/coreai)

**Article**

# Managing model specialization and caching

> Configure model specialization, manage cached assets, and reduce your app’s storage footprint.

## Overview

When you load a `.aimodel` file with [`AIModel`](/documentation/coreai/aimodel), Core AI performs *specialization*, the process of optimizing the model for the current device’s hardware. The `.aimodel` file contains your model in a portable format that works across Apple devices. Before the model can run, Core AI specializes it for the current device, producing executable code tied to that device’s hardware and OS version.

By default, an `AIModel` automatically specializes the model and caches the result. On the first call, Core AI specializes the model and stores the output. On subsequent calls with the same model and options, Core AI loads the cached version rather than running the specialization process again, which reduces load times.

Core AI provides APIs to control how, when, and where specialization happens.

## Check for a cached specialization

To avoid re-specializing your model whenever your app launches, check if a cached version already exists. Call [`model(for:options:)`](/documentation/coreai/aimodelcache/model(for:options:)) on the app’s default AI model cache. The `options` parameter specifies which [`SpecializationOptions`](/documentation/coreai/specializationoptions) to match against:

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

This method checks whether a cached specialization exists for the given model and options; however, it doesn’t perform specialization. If a cached version exists, the method returns the model instantly. If it returns `nil`, no cached specialization exists.

## Choose how Core AI specializes your model

Use [`SpecializationOptions`](/documentation/coreai/specializationoptions) to configure how Core AI specializes your model. By default, the system selects the combination of compute units (CPU, GPU, and Neural Engine) to minimize inference latency:

```swift
let model = try await AIModel(contentsOf: modelURL, options: .default)
```

For advanced use cases, restrict specialization to CPU only with `.cpuOnly`, or prefer a specific compute unit with [`init(preferredComputeUnitKind:)`](/documentation/coreai/specializationoptions/init(preferredcomputeunitkind:)). For example, if your app runs a small model in the background, use `.cpuOnly` to avoid competing with foreground GPU work.

In most scenarios, the default configuration offers the best performance, so test your app’s performance carefully before overriding it. Because not all devices have the same compute units available, check what’s available with [`availableKinds`](/documentation/coreai/computeunitkind/availablekinds). For details on all available specialization options, see [`SpecializationOptions`](/documentation/coreai/specializationoptions).

## Specialize a model before loading it

When your app downloads a model or enables a feature that uses one, you can specialize the model at a convenient moment so the person doesn’t notice a delay when they use it. Use [`specialize(contentsOf:options:cache:cachePolicy:)`](/documentation/coreai/aimodel/specialize(contentsof:options:cache:cachepolicy:)) to specialize a model without loading it for inference:

```swift
guard let localModelURL = try await downloadModel(forFeature: feature) else {
    throw AppError.failedToDownloadModel(feature)
}

// Specialize the model so it's ready before the person needs it.
try await AIModel.specialize(contentsOf: localModelURL, options: .default)

// The model is now specialized and cached. Future loads skip specialization.
let model = try await AIModel(contentsOf: localModelURL, options: .default)
```

This method stores the specialized assets in [`default`](/documentation/coreai/aimodelcache/default) and returns the specialized `AIModel`. After explicit specialization, any future `AIModel` initialization with the same model URL and options loads directly from cache.

> [!NOTE]
> Calling `specialize` multiple times with the same model URL and options returns the cached result without repeating the specialization process.

The `specialize` method differs from ahead-of-time compilation. With ahead-of-time compilation, most of the heavy computation happens on your Mac at build time, so on-device specialization finishes faster. With `specialize`, the full specialization process runs on the person’s device. You are controlling *when* specialization happens, not reducing the work it does.

## Control cache persistence with policies

Because the system can automatically delete specialized assets to free up storage, use [`AIModelCache.Policy`](/documentation/coreai/aimodelcache/policy) to control whether the system can remove your app’s cached assets.

The system can remove specialized assets from the cache under three conditions:

For most apps, use the default policy. It allows the system to reclaim storage when needed by deleting assets under both storage pressure and source model changes.

If your app deletes the source model file to save storage, use the `.persistent` policy to keep the cached assets available across launches:

```swift
try await AIModel.specialize(
    contentsOf: modelURL,
    options: .default,
    cachePolicy: .persistent
)
```

## Delete cached assets you no longer need

To reduce your app’s storage footprint, delete cached assets when they’re no longer needed. For example, when your app downloads an updated version of a model and the previous version’s cached assets are no longer valid:

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

Core AI provides methods for deleting cached assets:

If an [`AIModel`](/documentation/coreai/aimodel) instance still uses a cache entry, Core AI defers deletion until that instance is deallocated.

## Share specialized models across apps

If you have multiple apps or extensions that use the same model, create an app group using the [`App Groups Entitlement`](/documentation/BundleResources/Entitlements/com.apple.security.application-groups). Then use [`init(appGroup:)`](/documentation/coreai/aimodelcache/init(appgroup:)) to target the group identifier and load a shared cache. This avoids duplicating specializations across apps:

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

Other apps in the same group can then load the model from the shared cache:

```swift
guard let groupCache = AIModelCache(appGroup: groupIdentifier) else {
    return
}

if let model = try groupCache.model(for: sharedModelURL, options: .default) {
    // Use the model. No specialization needed.
}
```

## Delete the source model and load from cache

The unspecialized `.aimodel` file, along with the [`SpecializationOptions`](/documentation/coreai/specializationoptions) you pass, is what Core AI uses to index and retrieve the cached specialization at runtime when you call [`init(contentsOf:options:)`](/documentation/coreai/aimodel/init(contentsof:options:)) or [`model(for:options:)`](/documentation/coreai/aimodelcache/model(for:options:)). Because of this, you can’t simply delete the source file and expect those APIs to keep working. Instead, save a bookmark to the cached specialization and load the model directly from that bookmark on later launches.

After specializing a model, capture its `bookmarkData` and save it somewhere your app can read on later launches, such as `UserDefaults`:

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

On a subsequent launch, resolve the bookmark to load the model directly from the cache, without going through the source file:

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

With the bookmark saved, your app can delete the source `.aimodel` file to reclaim storage and continue working with the cached specialization through the bookmark:

```swift
// Delete the source model to reclaim storage.
try FileManager.default.removeItem(at: llmURL)
```

Bookmark data doesn’t prevent removing assets from the device. If the system purges the assets, you manually delete them, or an OS update invalidates them, your app can’t resolve the bookmark and needs to download and specialize the model again.

## Configuration

- [Compiling Core AI models ahead of time](/documentation/coreai/compiling-core-ai-models-ahead-of-time)
- [`AIModelCache`](/documentation/coreai/aimodelcache)
- [`ComputeUnitKind`](/documentation/coreai/computeunitkind)
- [`SpecializationOptions`](/documentation/coreai/specializationoptions)

---

*Extracted by [sosumi.ai](https://sosumi.ai) - Making Apple docs AI-readable.*
*This is unofficial content. All documentation belongs to Apple Inc.*
