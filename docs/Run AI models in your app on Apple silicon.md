---
title: Core AI
description: Run AI models in your app on Apple silicon.
source: https://developer.apple.com/documentation/coreai/
timestamp: 2026-07-27T17:25:14.006Z
---

**Framework**

# Core AI

**Available on:** iOS 27.0+ Beta, iPadOS 27.0+ Beta, Mac Catalyst 27.0+ Beta, macOS 27.0+ Beta, tvOS 27.0+ Beta, visionOS 27.0+ Beta, watchOS 27.0+ Beta

> Run AI models in your app on Apple silicon.

## Overview

Core AI helps you build, run, and deploy AI models in your app. Designed with Apple silicon in mind, Core AI allows your app to use the latest model architectures and inference techniques across the CPU, GPU, and Neural Engine. The Swift API makes common tasks simple, while giving you more control over model specialization, caching, and inference performance when needed.

![An illustration showing AI models connecting to Apple devices.](https://docs-assets.developer.apple.com/published/3436c2b440f83e13deb0e14474c5e08e/core-ai-framework-hero%402x.png)

Alongside the framework, Core AI includes additional tools for model preparation, integration, and debugging. Prepare your models for Apple silicon with [Core AI Optimization](https://apple.github.io/coreai-optimization), then convert them into the `.aimodel` format with [Core AI PyTorch Extensions](https://apple.github.io/coreai-torch). The [Core AI Debugger](https://developer.apple.com/core-ai-debugger/) app supports visualization and numeric debugging, letting you inspect model structure and trace tensor values directly back to your Python source code.

Core AI also integrates with Xcode and the developer toolchain. The Core AI debug gauge and Core AI instrument help you monitor and profile inference performance in your app. You can also compile models ahead of time with the `coreai-build` command-line tool.

If your app uses model types other than neural networks, such as decision trees or tabular feature engineering, see [Core ML](/documentation/CoreML).

## Essentials

- [Integrating on-device AI models in your app with Core AI](/documentation/coreai/integrating-on-device-ai-models-in-your-app-with-core-ai) Power your app’s intelligent features with an on-device AI model.
- [`AIModel`](/documentation/coreai/aimodel) A specialized model for running inference on a device.
- [`AIModelAsset`](/documentation/coreai/aimodelasset) An unspecialized source model asset.

## Inference

- [`InferenceFunction`](/documentation/coreai/inferencefunction) A function that performs inference on input values and produces output values.
- [`InferenceFunctionDescriptor`](/documentation/coreai/inferencefunctiondescriptor) A description of an inference function’s signature.
- [`InferenceValue`](/documentation/coreai/inferencevalue) A value that an inference function accepts as input or produces as output.
- [`ImageDescriptor`](/documentation/coreai/imagedescriptor) A description of an image’s dimensions and pixel format.
- [`ComputeStream`](/documentation/coreai/computestream) A stream of work to be run asynchronously.

## Multidimensional arrays

- [`NDArray`](/documentation/coreai/ndarray) A multidimensional array of scalar values used for model inference.
- [`NDArrayDescriptor`](/documentation/coreai/ndarraydescriptor) A description of an array’s shape, scalar type, and memory layout expectations.

## Configuration

- [Managing model specialization and caching](/documentation/coreai/managing-model-specialization-and-caching) Configure model specialization, manage cached assets, and reduce your app’s storage footprint.
- [Compiling Core AI models ahead of time](/documentation/coreai/compiling-core-ai-models-ahead-of-time) Reduce on-device specialization time by compiling Core AI models at build time.
- [`AIModelCache`](/documentation/coreai/aimodelcache) A cache that stores the specialized model artifacts for inference.
- [`ComputeUnitKind`](/documentation/coreai/computeunitkind) A type of hardware compute unit available for model inference.
- [`SpecializationOptions`](/documentation/coreai/specializationoptions)

## Debugging and performance

- [Inspecting, debugging, and profiling Core AI models](/documentation/coreai/inspecting-debugging-and-profiling-core-ai-models) Investigate model behavior, monitor activity, and profile performance using the Core AI tools across Xcode and the Core AI Debugger app.

## Errors

- [`AssetError`](/documentation/coreai/asseterror) An error that occurs during model asset operations.

---

*Extracted by [sosumi.ai](https://sosumi.ai) - Making Apple docs AI-readable.*
*This is unofficial content. All documentation belongs to Apple Inc.*
