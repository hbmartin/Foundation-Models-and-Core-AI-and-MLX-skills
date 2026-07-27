---
title: Compiling Core AI models ahead of time
description: Reduce on-device specialization time by compiling Core AI models at build time.
source: https://developer.apple.com/documentation/coreai/compiling-core-ai-models-ahead-of-time
timestamp: 2026-07-27T17:32:27.742Z
---

**Navigation:** [Coreai](/documentation/coreai)

**Article**

# Compiling Core AI models ahead of time

> Reduce on-device specialization time by compiling Core AI models at build time.

## Overview

Core AI models must be specialized to the specific device they run on before inference can begin. Specialization happens automatically when you create an [`AIModel`](/documentation/coreai/aimodel) in your app. For large models, this can take significant time, which can introduce a delay the first time your app loads the model.

Core AI can help reduce on-device specialization time with *ahead-of-time compilation* through the `coreai-build` command-line tool. The tool moves the most expensive part of specialization, model compilation, to your build machine, so on-device specialization has less work to do, and your model loads faster when your app runs it.

Ahead-of-time compilation converts your `.aimodel` model file into `.aimodelc` assets, one for each device architecture. At runtime, your app picks the asset that matches the current device’s architecture, and Core AI generates the executable code on device without repeating the compilation step.

Before compiling, set up your project to load a Core AI model. See [Integrating on-device AI models in your app with Core AI](/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai) for project setup, the Xcode model viewer, and loading basics.

> [!NOTE]
> Ahead-of-time compilation only compiles for devices that support Apple Intelligence, including iPhone or iPad with the A17 Pro chipset or later, a Mac with the M1 chipset or later, or Apple Vision Pro with the M2 chipset or later.

## Compile your model ahead of time

To use `coreai-build`, install the Metal Toolchain on your Mac, either through Xcode or the command line.

To install in Xcode:

1. Choose Xcode > Settings.
2. Choose Components, and under Other Components, click Get next to Metal Toolchain.

Another option is to install from the command line:

```shell
% xcodebuild -downloadComponent MetalToolchain
```

With the Metal Toolchain installed, use `xcrun` with `coreai-build` to compile your model for iOS:

```shell
% xcrun coreai-build compile MyModel.aimodel --platform iOS --min-deployment-version 27.0 --output compiled/
```

`coreai-build` outputs one compiled `.aimodelc` file per device architecture, using the input model’s filename as the prefix. For example, compiling `MyModel.aimodel` produces files named `MyModel.<arch>.aimodelc`, where `<arch>` is the device architecture identifier returned by [`deviceArchitectureName`](/documentation/coreai/aimodel/devicearchitecturename) at runtime. Each compiled `.aimodelc` works on any OS version at or above the minimum deployment version you pass to `coreai-build`.

By default, Core AI selects the compute units that deliver the best performance for the model and platform. To override, pass `--preferred-compute`. For the available values, the minimum deployment version, the target architecture, and other options, run `coreai-build compile --help`. For background on compute unit configuration, see the *Choose how Core AI specializes your model* section of [Managing model specialization and caching](/documentation/coreai/managing-model-specialization-and-caching).

## Load a compiled model on device

Ahead-of-time compilation produces one `.aimodelc` per supported device architecture, but each device only needs the variant that matches its own architecture. It’s recommended to host the compiled assets remotely and download the matching variant to the device at runtime, because each device only uses one of them. The [Background Assets](/documentation/BackgroundAssets) framework can manage downloads, installs, and updates for your hosted model files.

At runtime, query the device architecture to identify which `.aimodelc` to fetch. Use [`deviceArchitectureName`](/documentation/coreai/aimodel/devicearchitecturename) to read the architecture string for the current device, then build the file name that matches the asset on your server:

```swift
let arch = AIModel.deviceArchitectureName
let assetName = "MyModel.\(arch).aimodelc"
```

To load the downloaded `.aimodelc` asset, use [`init(contentsOf:options:)`](/documentation/coreai/aimodel/init(contentsof:options:)). This is the same API you use to load `.aimodel` files, so you don’t need to change your loading code when you adopt ahead-of-time compilation. Use the default options, or specify options that match the compute units you used at compile time.

Even with ahead-of-time compilation, the compiled asset still requires some specialization on the device. The amount of compilation that remains depends on the model and the compute units it uses. For more information on specialization, see [Managing model specialization and caching](/documentation/coreai/managing-model-specialization-and-caching).

## Configuration

- [Managing model specialization and caching](/documentation/coreai/managing-model-specialization-and-caching)
- [`AIModelCache`](/documentation/coreai/aimodelcache)
- [`ComputeUnitKind`](/documentation/coreai/computeunitkind)
- [`SpecializationOptions`](/documentation/coreai/specializationoptions)

---

*Extracted by [sosumi.ai](https://sosumi.ai) - Making Apple docs AI-readable.*
*This is unofficial content. All documentation belongs to Apple Inc.*
