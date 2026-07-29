# ml-explore/mlx-swift-examples — deep-dive research notes

**Local clone:** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-swift-examples` (`--depth 50`)
**Branch:** `main`, HEAD = `378f244` "MLXChatExample: fix VLM image handling on iOS (PhotosPicker, EXIF, empty assistant trim) (#472)" — authored **2026-06-16**.
**Research date:** 2026-07-27. Everything below was read from the working tree or `git show` in this session.

> ⚠️ Everything in this file is grounded in files I actually opened. Where I infer or extrapolate I mark it **UNVERIFIED**.

---

## 0. TL;DR — what this repo is now (2026)

The repository has been **gutted of model implementations**. As of commit `0db7c5d` (2025-11-11, "split out mlx-swift-lm (#441)"), `MLXLMCommon`, `MLXLLM`, `MLXVLM` and `MLXEmbedders` were **moved to a separate repository**: <https://github.com/ml-explore/mlx-swift-lm>. `mlx-swift-examples` is now:

1. **Example applications** (`Applications/`) — SwiftUI apps for iOS/macOS/visionOS.
2. **Example command-line tools** (`Tools/`) — ArgumentParser CLIs.
3. **Numerical computing demos** (`Numerical/`) — new for **WWDC26** (commit `70eaaca`, 2026-06-09).
4. **Two remaining reusable libraries** (`Libraries/`): `MLXMNIST` and `StableDiffusion`.
5. `mlx-run` — shell wrapper to run Xcode-built CLI binaries.

README.md:56-62 (verbatim):

```
> [!IMPORTANT]
> `MLXLMCommon`, `MLXLLM`, `MLXVLM` and `MLXEmbedders` have moved to a new repository
> containing _only_ reusable libraries: [mlx-swift-lm](https://github.com/ml-explore/mlx-swift-lm).

Previous URLs and tags will continue to work, but going forward all updates to these
libraries will be done in the other repository.  Previous tags _are_ supported in
the new repository.
```

README.md:64-66:

```
> [!TIP]
> Contributors that wish to edit both `mlx-swift-examples` and `mlx-swift-lm` can
> use [this technique in Xcode](https://developer.apple.com/documentation/xcode/editing-a-package-dependency-as-a-local-package).
```

---

## 1. Repository tree (complete, non-`.git`)

```
.
├── ACKNOWLEDGMENTS.md  CODE_OF_CONDUCT.md  CONTRIBUTING.md  LICENSE  README.md
├── .swift-format  .pre-commit-config.yaml  .spi.yml  .gitignore
├── .github/workflows/pull_request.yml
├── Package.swift  Package.resolved
├── mlx-run                                  # shell wrapper for CLI tools
├── mlx-swift-examples.xcodeproj/            # THE build system (17 targets)
├── Configuration/Build.xcconfig             # DISAMBIGUATOR = ${DEVELOPMENT_TEAM}
├── Applications/
│   ├── LLMBasic/            {LLMBasicApp,ContentView,ChatModel}.swift, README, .entitlements
│   ├── LLMEval/             LLMEvalApp.swift, Views/*, ViewModels/*, Models/*, Services/*
│   ├── MLXChatExample/      MLXChatExampleApp.swift, ChatView.swift, Views/*, ViewModels/*, Models/*, Services/*, Support/*
│   ├── LoRATrainingExample/ LoRATrainingExampleApp.swift, ContentView.swift
│   ├── MNISTTrainer/        MNISTTrainerApp.swift, ContentView.swift, PredictionView.swift
│   └── StableDiffusionExample/ StableDiffusionExampleApp.swift, ContentView.swift
├── Tools/
│   ├── llm-tool/            LLMTool.swift, Chat.swift, LoraCommands.swift, ListCommands.swift, Tools.swift, Arguments.swift
│   ├── image-tool/          ImageTool.swift, Arguments.swift
│   ├── embedder-tool/       15 .swift files
│   ├── mnist-tool/          MNISTTool.swift
│   ├── LinearModelTraining/ LinearModelTraining.swift
│   └── Tutorial/            Tutorial.swift
├── Numerical/               # WWDC26
│   ├── CurveFit/            Algorithm/Gradient.swift, ContentView.swift, CurveFitApp.swift
│   ├── HeatTransfer/        Algorithm/{Jacobi+MLX,Configuration}.swift, Renderer.swift, Utilities/*
│   └── Mandelbrot/          Algorithm/{Mandelbrot+MLX,Mandelbrot+CPU,Configuration}.swift, Renderer.swift, Utilities/*
├── Libraries/
│   ├── MLXMNIST/            MNIST.swift, Files.swift, Random.swift
│   └── StableDiffusion/     StableDiffusion.swift, Load.swift, UNet.swift, VAE.swift, Clip.swift,
│                            Sampler.swift, Tokenizer.swift, Image.swift, Configuration.swift
├── Data/lora/               train.jsonl (1000), valid.jsonl (100), test.jsonl (100), wikisql.py
└── support/                 mlx-run helper scripts: run-all-llms.sh, generate-run-all-llms.sh, test.jpg
```

---

## 2. Dependencies, versions, OS/Xcode requirements

### 2.1 `Package.swift` (SwiftPM package name = **`mlx-libraries`**, NOT `mlx-swift-examples`)

Verbatim, `Package.swift:1-63`:

```swift
// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "mlx-libraries",
    platforms: [.macOS(.v14), .iOS(.v16)],
    products: [
        .library(name: "MLXMNIST", targets: ["MLXMNIST"]),
        .library(name: "StableDiffusion", targets: ["StableDiffusion"]),
    ],
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift", .upToNextMinor(from: "0.31.4")),

        // Note: used by StableDiffusion library to download weights
        .package(
            url: "https://github.com/huggingface/swift-transformers",
            .upToNextMajor(from: "1.3.0")
        ),
        .package(url: "https://github.com/1024jp/GzipSwift", "6.0.1" ... "6.0.1"),  // Only needed by MLXMNIST
    ],
    targets: [
        .target(
            name: "MLXMNIST",
            dependencies: [
                .product(name: "MLX", package: "mlx-swift"),
                .product(name: "MLXFast", package: "mlx-swift"),
                .product(name: "MLXNN", package: "mlx-swift"),
                .product(name: "MLXOptimizers", package: "mlx-swift"),
                .product(name: "MLXRandom", package: "mlx-swift"),
                .product(name: "Gzip", package: "GzipSwift"),
            ],
            path: "Libraries/MLXMNIST",
            exclude: ["README.md"],
            swiftSettings: [.enableExperimentalFeature("StrictConcurrency")]
        ),
        .target(
            name: "StableDiffusion",
            dependencies: [
                .product(name: "MLX", package: "mlx-swift"),
                .product(name: "MLXNN", package: "mlx-swift"),
                .product(name: "MLXRandom", package: "mlx-swift"),
                .product(name: "Transformers", package: "swift-transformers"),
            ],
            path: "Libraries/StableDiffusion",
            exclude: ["README.md"],
            swiftSettings: [.enableExperimentalFeature("StrictConcurrency")]
        ),
    ]
)

if Context.environment["MLX_SWIFT_BUILD_DOC"] == "1"
    || Context.environment["SPI_GENERATE_DOCS"] == "1"
{
    // docc builder
    package.dependencies.append(
        .package(url: "https://github.com/apple/swift-docc-plugin", from: "1.3.0")
    )
}
```

**Note:** `Package.swift` does *not* depend on `mlx-swift-lm`. The LLM/VLM dependency lives only in the **Xcode project**.

**Gotcha (verified inconsistency):** root `Package.resolved` pins `mlx-swift` at **0.31.3** while `Package.swift` requires `.upToNextMinor(from: "0.31.4")`. The Xcode workspace `Package.resolved` correctly pins **0.31.4**. Also `.gitignore` contains `Package.resolved` yet both files are committed.

### 2.2 Xcode project remote package requirements (`mlx-swift-examples.xcodeproj/project.pbxproj:3890-3956`)

| Package | URL | Requirement |
|---|---|---|
| `swift-markdown-ui` | https://github.com/gonzalezreal/swift-markdown-ui | `upToNextMajorVersion` **2.3.1** |
| `mlx-swift` | https://github.com/ml-explore/mlx-swift | `upToNextMajorVersion` **0.31.4** |
| `GzipSwift` | https://github.com/1024jp/GzipSwift | `exactVersion` **6.0.1** |
| **`mlx-swift-lm`** | https://github.com/ml-explore/mlx-swift-lm.git | `upToNextMajorVersion` **3.31.3** |
| `Progress.swift` | https://github.com/jkandzi/Progress.swift | `upToNextMajorVersion` **0.4.0** |
| `swift-argument-parser` | https://github.com/apple/swift-argument-parser.git | `upToNextMajorVersion` **1.4.0** |
| `swift-huggingface` | https://github.com/huggingface/swift-huggingface | `upToNextMajorVersion` **0.9.0**, `traits = ()` |
| `swift-transformers` | https://github.com/huggingface/swift-transformers | `upToNextMajorVersion` **1.3.0**, `traits = ()` |
| (local) | `Libraries/..` | `XCLocalSwiftPackageReference` — the root `mlx-libraries` package |

`traits = ( );` on `swift-huggingface` / `swift-transformers` is **new pbxproj syntax** (SwiftPM package traits). Empty = no optional traits enabled.

### 2.3 Resolved versions — `mlx-swift-examples.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved` (`"version": 3`)

| identity | version | revision |
|---|---|---|
| eventsource | 1.4.1 | a3a85a8 |
| gzipswift | 6.0.1 | 731037f |
| **mlx-swift** | **0.31.4** | dc43e62 |
| **mlx-swift-lm** | **3.31.3** | 1c05248 |
| networkimage | 6.0.1 | 2849f53 |
| progress.swift | 0.4.0 | fed6598 |
| swift-argument-parser | 1.6.2 | cdd0ef3 |
| swift-asn1 | 1.6.0 | — |
| swift-atomics | 1.3.0 | — |
| swift-cmark | 0.7.1 | — |
| swift-collections | 1.3.0 | — |
| swift-crypto | 4.3.0 | — |
| **swift-huggingface** | **0.9.0** | b721959 |
| swift-jinja | 2.3.1 | d81197f |
| swift-markdown-ui | 2.4.1 | 5f61335 |
| swift-nio | 2.97.0 | — |
| swift-numerics | 1.1.1 | — |
| swift-syntax | 600.0.1 | — |
| swift-system | 1.6.4 | — |
| **swift-transformers** | **1.3.0** | b38443e |
| yyjson | 0.12.0 | — |

**swift-syntax 600.0.1 is present because `mlx-swift-lm` 3.x ships Swift macros** (see §5.3). CI passes `-skipMacroValidation` for this reason.

### 2.4 Per-target deployment targets (extracted from `project.pbxproj`, Release config)

| Target | bundle id | iOS | macOS | SWIFT_VERSION | device family | SUPPORTED_PLATFORMS |
|---|---|---|---|---|---|---|
| **LLMBasic** | `mlx.LLMBasic${DISAMBIGUATOR}` | **26.2** | **26.2** | **6.0** | 1,2,7 | iphoneos iphonesimulator macosx xros xrsimulator |
| **Mandelbrot** | `mlx.Mandelbrot${DISAMBIGUATOR}` | **26.5** | **26.5** | 5.0 | 1,2,7 | + xros |
| **HeatTransfer** | `mlx.HeatTransfer${DISAMBIGUATOR}` | **26.5** | **26.5** | 5.0 | 1,2,7 | + xros |
| **CurveFit** | `mlx.CurveFit${DISAMBIGUATOR}` | **26.5** | **26.5** | 5.0 | 1,2,7 | + xros |
| MLXChatExample | `mlx.MLXChatExample${DISAMBIGUATOR}` | 18.0 | 15.0 | 5.0 | 1,2,7 | + xros |
| LoRATrainingExample | `mlx.LoRATrainingExample${DISAMBIGUATOR}` | 17.2 | 14.2 | 5.0 | 1,2,7 | + xros |
| StableDiffusionExample | `mlx.StableDiffusionExample${DISAMBIGUATOR}` | 17.2 | 14.2 | 5.0 | 1,2,7 | + xros |
| LLMEval | `mlx.LLMEval${DISAMBIGUATOR}` | 17.2 | 14.2 | 5.0 | 1,2,7 | + xros |
| MNISTTrainer | `mlx.MNISTTrainer${DISAMBIGUATOR}` | 17.2 | 14.2 | 5.0 | **1,2** (no visionOS) | iphoneos iphonesimulator macosx |
| MLXLMTests | `mlx.MLXLMTests` | 17.6 | 14.6 | 5.0 | 1,2,7 | + xros |
| CLI tools (llm-tool etc.) | — | — | 14.0–15.4 | 5.0 / 6.0 | — | macOS only |

⚠️ **Notable:** `LLMBasic` requires **iOS 26.2 / macOS 26.2 and Swift 6**; the three Numerical apps require **iOS 26.5 / macOS 26.5**. These are the "new for 2026" targets. Older examples still target iOS 17.2.

`Configuration/Build.xcconfig` (verbatim):

```
DISAMBIGUATOR=${DEVELOPMENT_TEAM}
```
with a comment saying this is only for sample projects so bundle IDs are unique without a team set.

### 2.5 Which SwiftPM products each Xcode target links (extracted from `packageProductDependencies`)

| Target | Linked products |
|---|---|
| `llm-tool` | ArgumentParser, **MLXHuggingFace**, **MLXLLM**, **MLXLMCommon**, **MLXVLM**, HuggingFace, Tokenizers |
| `MLXChatExample` | **MLXHuggingFace**, HuggingFace, **MLXLLM**, **MLXVLM**, Tokenizers |
| `LLMEval` | **MLXHuggingFace**, HuggingFace, **MLXLLM**, MarkdownUI, Tokenizers |
| `LLMBasic` | **MLXHuggingFace**, **MLXLLM**, HuggingFace, Tokenizers |
| `LoRATrainingExample` | **MLXHuggingFace**, HuggingFace, **MLXLLM**, Tokenizers |
| `embedder-tool` | ArgumentParser, **MLXHuggingFace**, HuggingFace, **MLXEmbedders**, Tokenizers |
| `image-tool` | ArgumentParser, Progress, **StableDiffusion** (local) |
| `mnist-tool`, `MNISTTrainer` | ArgumentParser / **MLXMNIST** (local) |
| `LinearModelTraining` | ArgumentParser, MLX, MLXNN, MLXOptimizers |
| `Tutorial` | MLX |
| `Mandelbrot`, `HeatTransfer`, `CurveFit` | **MLX only** |
| `MLXLMTests` | MLX, MLXNN (test sources moved to mlx-swift-lm; target is a shell here) |
| `ExampleLLM` | MLXLLM, MLXVLM (target exists in pbxproj but **no sources in tree**) |

**`MLXHuggingFace` is a new product from `mlx-swift-lm` 3.x** that vends the Swift macros `#hubDownloader`, `#huggingFaceTokenizerLoader`, `#huggingFaceLoadModelContainer`.

### 2.6 Xcode schemes present (`mlx-swift-examples.xcodeproj/xcshareddata/xcschemes/`)

`MLXChatExample`, `mlx-libraries-Package`, `image-tool`, `llm-tool`, `StableDiffusionExample`, `embedder-tool`, `Mandelbrot`, `LLMBasic`, `HeatTransfer`, `LLMEval`.

(No shared schemes for MNISTTrainer / LoRATrainingExample / mnist-tool / Tutorial / LinearModelTraining / CurveFit — they exist as targets and Xcode autocreates schemes.)

Full target list (17): `LLMEval, MLXChatExample, LLMBasic, llm-tool, ExampleLLM, embedder-tool, StableDiffusionExample, image-tool, LoRATrainingExample, mnist-tool, MNISTTrainer, Tutorial, LinearModelTraining, MLXLMTests, Mandelbrot, HeatTransfer, CurveFit`.

---

## 3. Building and running

### 3.1 `mlx-run` — verbatim (`mlx-run:1-45`)

```sh
#!/bin/sh

# Wrapper to help run command line tools -- this will find the build directory
# and set the DYLD_FRAMEWORK_PATH so that command line tools that link frameworks
# can be run.
#
# Example:
# ./mlx-run --debug llm-tool --help

if [ "$#" -lt 1 ]; then
	echo "usage: mlx-run [--debug/--release] <tool-name> arguments"
	exit 1
fi

CONFIGURATION=Release
if [ "$1" == "--release" ]; then
	CONFIGURATION=Release
	shift
fi
if [ "$1" == "--debug" ]; then
	CONFIGURATION=Debug
	shift
fi
if [ "$1" == "--list" ]; then
	xcodebuild -list
	exit 0
fi

COMMAND="$1"
shift

BUILD_DIR=`xcodebuild -configuration $CONFIGURATION -showBuildSettings -scheme $COMMAND | grep 'BUILT_PRODUCTS_DIR = /' | sed -e 's/^[^=]*= //g'`

if [ -d "$BUILD_DIR/$COMMAND.app" ]; then
	exec $BUILD_DIR/$COMMAND.app/Contents/MacOS/$COMMAND "$@" &
fi

if [ -f "$BUILD_DIR/$COMMAND" ]; then
	export DYLD_FRAMEWORK_PATH=$BUILD_DIR/PackageFrameworks:$BUILD_DIR
	exec "$BUILD_DIR/$COMMAND" "$@"
else
	echo "$BUILD_DIR/$COMMAND does not exist -- check build configuration ($CONFIGURATION)"
	exit 1
fi
```

Key facts:
- **Defaults to Release.** `--debug` selects Debug. `--list` runs `xcodebuild -list`.
- Sets `DYLD_FRAMEWORK_PATH=$BUILD_DIR/PackageFrameworks:$BUILD_DIR` — **required** because the CLI links MLX as dynamic frameworks; running the raw binary out of DerivedData without this fails to load.
- If a `.app` is found it launches the macOS app bundle's executable in the background.
- You must **build the scheme in Xcode first** — `mlx-run` does not build.

Examples from the READMEs:

```sh
./mlx-run llm-tool --prompt "swift programming language"
./mlx-run --debug llm-tool --help
./mlx-run mnist-tool --data /tmp
./mlx-run image-tool sd text --prompt "purple cow on the moon" --output /tmp/cow.png
./mlx-run embedder-tool index --output /tmp/embedder-index.json --directory Libraries --extensions md --recursive
```

### 3.2 CI (`.github/workflows/pull_request.yml`)

Two jobs, `on: pull_request`, both gated by `if: github.repository == 'ml-explore/mlx-swift-examples'`.

**`lint`** — runs on `ubuntu-22.04` in container `swift:6.2-rhel-ubi9`:
- `astral-sh/setup-uv@v6` → `uv pip install pre-commit`
- Fetches the *latest* `swiftlang/swift-format` release tag from the GitHub API, clones it, `swift build -c release`, symlinks into `/usr/local/bin`, caches `.build`.
- `pre-commit run --all` with the message: `"Style checks failed, please install pre-commit and run pre-commit run --all and push the change"`.

**`mac_build_and_test`** — `runs-on: [self-hosted, macos]`, `needs: lint`:
```yaml
- name: Verify MetalToolchain installed
  env: { DEVELOPER_DIR: /Applications/Xcode-latest.app }   # "workaround for CI failure"
  run: xcodebuild -showComponent MetalToolchain

- name: Build Package (Xcode, macOS)
  run: |
    xcodebuild -version
    swift --version
    rm -rf ~/Library/Developer/Xcode/DerivedData/*
    xcodebuild build-for-testing -scheme mlx-libraries-Package -destination 'platform=macOS' -skipMacroValidation

- name: Build tools (Xcode, macOS)
  run: |
    find . -name Package.resolved -exec rm {} \;
    xcodebuild -scheme llm-tool      -skipMacroValidation
    xcodebuild -scheme embedder-tool -skipMacroValidation
    xcodebuild -scheme image-tool    -skipMacroValidation
    xcodebuild -scheme mnist-tool    -skipMacroValidation
```

**Gotchas encoded in CI:**
- `xcodebuild -showComponent MetalToolchain` is checked explicitly — the Metal toolchain must be installed (`xcodebuild -downloadComponent MetalToolchain` **UNVERIFIED** as the install command, but the check is real).
- `-skipMacroValidation` is required everywhere since `mlx-swift-lm` 3.x introduced macros (added in commit `357c97f`).
- `find . -name Package.resolved -exec rm {} \;` before building tools — they intentionally re-resolve.
- Switched from CircleCI to GitHub Actions in `7e2e757` (2025-12-02); `0db7c5d` still touched `.circleci/config.yml`.

### 3.3 Formatting

`.pre-commit-config.yaml`:
```yaml
repos:
- repo: local
  hooks:
    - id: swift-format
      name: swift-format
      language: system
      entry: swift-format format --in-place --configuration .swift-format --recursive .
      require_serial: true
      types: [swift]
```

`.swift-format`:
```json
{
    "version": 1,
    "indentation": { "spaces": 4 },
    "spacesAroundRangeFormationOperators": true,
}
```

CONTRIBUTING.md manual invocation:
```sh
swift-format format --in-place --recursive Libraries Tools Applications
pre-commit run --all-files
```
(`pip install pre-commit; pre-commit install`; `brew install swift-format` if needed.)

`.spi.yml` (Swift Package Index doc build) still lists the moved targets:
```yaml
version: 1
builder:
  configs:
    - documentation_targets: [MLXLLM, MLXVLM, MLXLMCommon, MLXMNIST, MLXEmbedders, StableDiffusion]
```
(**Stale** — MLXLLM/MLXVLM/MLXLMCommon/MLXEmbedders no longer live here.)

---

## 4. Memory & GPU cache control — the **new `Memory` API**

> **BREAKING vs. older tutorials.** The old idiom `MLX.GPU.set(cacheLimit: 20 * 1024 * 1024)` **does not appear anywhere in this repo**. It has been replaced by a `Memory` enum/namespace in the `MLX` module.

Verified API surface (all from `import MLX`):

| Symbol | Type | Where seen |
|---|---|---|
| `Memory.cacheLimit` | settable `Int` (bytes) | `LLMBasicApp.swift:12`, `MLXService.swift:56`, `LLMEvaluator.swift:105`, `LoRATrainingExample/ContentView.swift:181`, `StableDiffusionExample/ContentView.swift:146,149`, all `MemoryArguments` |
| `Memory.memoryLimit` | settable **and readable** `Int` (bytes) | `StableDiffusionExample/ContentView.swift:141` reads it; CLIs set it |
| `Memory.snapshot()` | `-> Memory.Snapshot` | `DeviceStat.swift:10,12,26`, all CLI `MemoryArguments` |
| `Memory.Snapshot.activeMemory` | `Int` | `LLMEval/Views/ContentView.swift:58` |
| `Memory.Snapshot.cacheMemory` | `Int` | `.../ContentView.swift:59` |
| `Memory.Snapshot.peakMemory` | `Int` | `.../ContentView.swift:60` |
| `Memory.Snapshot.description` | `String` | `MemoryArguments.reportMemoryStatistics()` |
| `Memory.Snapshot.delta(_:) -> Memory.Snapshot` | | `DeviceStat.swift:26`, `MemoryArguments` |

### 4.1 Canonical app-level idiom

`Applications/LLMBasic/LLMBasicApp.swift` (whole file):

```swift
// Copyright © 2025 Apple Inc.

import MLX
import MLXLLM
import MLXLMCommon
import SwiftUI

@main
struct LLMBasicApp: App {

    init() {
        Memory.cacheLimit = 20 * 1024 * 1024
    }

    @State var loader = ModelLoader()

    var body: some Scene {
        WindowGroup {
            ContentView(loader: loader)
        }
    }
}
```

Documented rationale, `Applications/LLMBasic/README.md:19-23` (verbatim):

```
Some notes about the setup:

- this downloads models from hugging face so LLMBasic -> Signing & Capabilities has the "Outgoing Connections (Client)" set in the App Sandbox
- LLM models are large so this uses the Increased Memory Limit entitlement on iOS to allow ... increased memory limits for devices that have more memory
- `Memory.cacheLimit = 20 * 1024 * 1024` is used to limit the buffer cache size
```

`Applications/LLMEval/README.md:15` is the identical bullet.

**Observed limits used per app:**
| App | cacheLimit | memoryLimit |
|---|---|---|
| LLMBasic | 20 MB | — |
| LLMEval (`performLoad()`) | 20 MB | — |
| MLXChatExample (`MLXService.load`) | 20 MB | — |
| LoRATrainingExample (`startInner()`) | **32 MB** | — |
| StableDiffusionExample, low-memory device | **1 MB** | **3 GB** |
| StableDiffusionExample, normal | **256 MB** | — |
| `llm-tool` / `image-tool` / `embedder-tool` | `--cache-size` MB (image-tool default **1024**) | `--memory-size` MB |

### 4.2 Adaptive low-memory detection (StableDiffusionExample)

`Applications/StableDiffusionExample/ContentView.swift:133-151`:

```swift
    public nonisolated let conserveMemory: Bool

    init() {
        let defaultParameters = configuration.defaultParameters()
        self.canShowProgress = defaultParameters.steps > 4
        self.canUseNegativeText = defaultParameters.cfgWeight > 1

        // this will be true e.g. if the computer has 8G of memory or less
        self.conserveMemory = Memory.memoryLimit < 8 * 1024 * 1024 * 1024

        if conserveMemory {
            print("conserving memory")
            loadConfiguration.quantize = true
            Memory.cacheLimit = 1 * 1024 * 1024
            Memory.memoryLimit = 3 * 1024 * 1024 * 1024
        } else {
            Memory.cacheLimit = 256 * 1024 * 1024
        }
    }
```

**This is the copyable "detect a small device" pattern**: read `Memory.memoryLimit` before setting it; MLX seeds it from the device's recommended working-set size.

### 4.3 Live memory HUD (`DeviceStat`)

`Applications/LLMEval/ViewModels/DeviceStat.swift` (whole file):

```swift
// Copyright © 2025 Apple Inc.

import Foundation
import MLX

@Observable
final class DeviceStat: @unchecked Sendable {

    @MainActor
    var gpuUsage = Memory.snapshot()

    private let initialGPUSnapshot = Memory.snapshot()
    private var timer: Timer?

    init() {
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.updateGPUUsages()
        }
    }

    deinit {
        timer?.invalidate()
    }

    private func updateGPUUsages() {
        let gpuSnapshotDelta = initialGPUSnapshot.delta(Memory.snapshot())
        DispatchQueue.main.async { [weak self] in
            self?.gpuUsage = gpuSnapshotDelta
        }
    }
}
```

Injected in `LLMEvalApp.swift`: `ContentView().environment(DeviceStat())`, read via `@Environment(DeviceStat.self) private var deviceStat`.

### 4.4 Shared CLI `MemoryArguments` pattern (copyable)

`Tools/llm-tool/LLMTool.swift:234-307` (verbatim, abridged only where repeated):

```swift
/// Argument package for adjusting and reporting memory use.
struct MemoryArguments: ParsableArguments, Sendable {

    @Flag(name: .long, help: "Show memory stats")
    var memoryStats = false

    @Option(name: .long, help: "Maximum cache size in M")
    var cacheSize: Int?

    @Option(name: .long, help: "Maximum memory size in M")
    var memorySize: Int?

    var startMemory: Memory.Snapshot?

    mutating func start<L>(_ load: @Sendable () async throws -> L) async throws -> L {
        if let cacheSize { Memory.cacheLimit  = cacheSize  * 1024 * 1024 }
        if let memorySize { Memory.memoryLimit = memorySize * 1024 * 1024 }
        let result = try await load()
        startMemory = Memory.snapshot()
        return result
    }

    mutating func start() { /* same limits, then */ startMemory = Memory.snapshot() }

    func reportCurrent() {
        if memoryStats { print(Memory.snapshot().description) }
    }

    func reportMemoryStatistics() {
        if memoryStats, let startMemory {
            let endMemory = Memory.snapshot()
            print("=======")
            print("Memory size: \(Memory.memoryLimit / 1024)K")
            print("Cache size:  \(Memory.cacheLimit / 1024)K")
            print("")
            print("=======")
            print("Starting memory"); print(startMemory.description)
            print("")
            print("=======")
            print("Ending memory");   print(endMemory.description)
            print("")
            print("=======")
            print("Growth");          print(startMemory.delta(endMemory).description)
        }
    }
}
```

Three near-identical copies exist: `Tools/llm-tool/LLMTool.swift`, `Tools/image-tool/Arguments.swift` (defaults `cacheSize = 1024`, non-optional), `Tools/embedder-tool/MemoryArguments.swift` (prints "GPU memory limit"/"GPU cache limit", `private(set) var startMemory`).

### 4.5 iOS entitlements — required for big models

Every LLM/VLM/SD app enables **`com.apple.developer.kernel.increased-memory-limit`**.

`Applications/MLXChatExample/MLXChatExample.entitlements` (verbatim):
```xml
<dict>
	<key>com.apple.developer.kernel.increased-memory-limit</key>
	<true/>
	<key>com.apple.security.app-sandbox</key>
	<true/>
	<key>com.apple.security.files.downloads.read-write</key>
	<true/>
	<key>com.apple.security.files.user-selected.read-only</key>
	<true/>
	<key>com.apple.security.network.client</key>
	<true/>
</dict>
```

| App | increased-memory-limit | app-sandbox | network.client | files.user-selected.read-only | files.downloads.read-write |
|---|---|---|---|---|---|
| LLMBasic | ✅ | — | — | — | — |
| LLMEval | ✅ | ✅ | ✅ | ✅ | — |
| LoRATrainingExample | ✅ | ✅ | ✅ | ✅ | — |
| MLXChatExample | ✅ | ✅ | ✅ | ✅ | ✅ |
| MNISTTrainer | — | ✅ | ✅ | ✅ | — |
| StableDiffusionExample | ✅ | ✅ | ✅ | ✅ | — |

MNISTTrainer README:10-13 notes the data host is **http**, so an "App Transport Security Settings" Info.plist entry is needed — though the checked-in `MNISTTrainer-Info.plist` is an **empty `<dict/>`** (ATS keys presumably live in the build settings / `INFOPLIST_KEY_*`; **UNVERIFIED**). The base URL is `https://raw.githubusercontent.com/fgnt/mnist/master/` in `Libraries/MLXMNIST/Files.swift:39`, i.e. now https — the README comment is stale.

---

## 5. LLM / VLM app patterns (the meat)

### 5.1 `LLMBasic` — the minimal, canonical 2026 app

Purpose (README.md:1-17): "*A minimal example of: loading a model, including downloading weights; setting up a ChatSession; a simple UI for a back and forth session with the model.* … *The goal of this example is to be a **minimal** application*". Requires iOS/macOS **26.2**, Swift 6.

`Applications/LLMBasic/ChatModel.swift` — **whole file, verbatim** (this is THE copyable pattern):

```swift
// Copyright © 2025 Apple Inc.

import HuggingFace
import MLXHuggingFace
import MLXLLM
import MLXLMCommon
import SwiftUI
import Tokenizers

/// which model to load
private let modelConfiguration = LLMRegistry.gemma3_1B_qat_4bit

/// instructions for the model (the system prompt)
private let instructions =
    """
    You are a friendly and helpful chatbot.
    """

/// parameters controlling generation
private let generateParameters = GenerateParameters(temperature: 0.5)

/// Downloads and loads the weights for the model -- we have one of these in the process
@MainActor @Observable public class ModelLoader {

    enum State {
        case idle
        case loading(Task<ModelContainer, Error>)
        case loaded(ModelContainer)
    }

    public var progress = 0.0
    public var isLoaded: Bool {
        switch state {
        case .idle, .loading: false
        case .loaded: true
        }
    }

    private var state = State.idle

    public func model() async throws -> ModelContainer {
        switch self.state {
        case .idle:
            let task = Task {
                // download and report progress
                try await #huggingFaceLoadModelContainer(
                    configuration: modelConfiguration
                ) { value in
                    Task { @MainActor in
                        self.progress = value.fractionCompleted
                    }
                }
            }
            self.state = .loading(task)
            let model = try await task.value

            self.state = .loaded(model)
            return model

        case .loading(let task):
            return try await task.value

        case .loaded(let model):
            return model
        }
    }
}

/// View model for the ChatSession
@MainActor @Observable public class ChatModel {

    private let session: ChatSession

    /// back and forth conversation between the user and LLM
    public var messages = [Chat.Message]()

    private var task: Task<Void, Error>?
    public var isBusy: Bool {
        task != nil
    }

    public init(model: ModelContainer) {
        self.session = ChatSession(
            model,
            instructions: instructions,
            generateParameters: generateParameters)
    }

    public func cancel() {
        task?.cancel()
    }

    public func respond(_ message: String) {
        guard task == nil else { return }

        self.messages.append(.init(role: .user, content: message))
        self.messages.append(.init(role: .assistant, content: "..."))
        let lastIndex = self.messages.count - 1

        self.task = Task {
            var first = true
            for try await item in session.streamResponse(to: message) {
                if first {
                    self.messages[lastIndex].content = item
                    first = false
                } else {
                    self.messages[lastIndex].content += item
                }
            }
            self.task = nil
        }
    }
}
```

Key takeaways:
- **`Task<ModelContainer, Error>` stored in the `.loading` state** so concurrent callers `await task.value` instead of double-downloading. Same idiom in `StableDiffusionExample.ModelFactory` and `LoRAEvaluator`.
- `session.streamResponse(to: String)` yields **`String` deltas** (an `AsyncSequence` of chunks, `try await` — throwing).
- The placeholder `"..."` assistant message is replaced (not appended) by the **first** chunk.

`Applications/LLMBasic/ContentView.swift` streaming UI (verbatim highlights):

```swift
struct ContentView: View {
    let loader: ModelLoader
    @State var session: ChatModel?
    @State var error: String?
    @State var prompt = ""
    @FocusState var promptFocused

    var body: some View {
        VStack {
            if let error {
                Text("Error: \(error)")
            } else if !loader.isLoaded {
                ProgressView("Loading", value: loader.progress, total: 1)
            } else if let session {
                ScrollView(.vertical) {
                    ForEach(session.messages.enumerated(), id: \.offset) { _, message in
                        let bold = message.role == .user
                        HStack {
                            Text(message.content).bold(bold)
                            Spacer()
                        }
                        .padding(.bottom, 4)
                    }
                    Spacer()
                    if session.isBusy {
                        // a stop button -- cmd-. to interrupt
                        HStack {
                            Button("Stop", action: { session.cancel() })
                                .keyboardShortcut(".")
                            Spacer()
                        }
                    } else {
                        TextField("Prompt", text: $prompt)
                            .onSubmit(respond)
                            .focused($promptFocused)
                            .onAppear { promptFocused = true }
                    }
                }
                .defaultScrollAnchor(.bottom)
            }
        }
        .padding()
        .task {
            do {
                let model = try await loader.model()
                self.session = ChatModel(model: model)
            } catch {
                self.error = error.localizedDescription
            }
        }
        .onDisappear {
            self.session?.cancel()
        }
    }

    private func respond() {
        session?.respond(prompt)
        prompt = ""
    }
}
```

Notable SwiftUI details: `.defaultScrollAnchor(.bottom)` pins to bottom while streaming; `ForEach(session.messages.enumerated(), id: \.offset)` (iterating an `enumerated()` sequence directly — requires newer SwiftUI/Swift); `.keyboardShortcut(".")` gives ⌘-. as interrupt; `.onDisappear { cancel() }`.

### 5.2 `MLXChatExample` — LLM + VLM chat, the most complete app

Requirements per its README:17-21 — "iOS 17.0+ / macOS 14.0+, Xcode 15.0+, Swift 5.9+" (**stale**: the pbxproj actually says iOS 18.0 / macOS 15.0).

Architecture: MVVM — `Views/`, `Models/`, `ViewModels/`, `Services/`, `Support/`.

#### 5.2.1 `MLXService` — model registry, cache, generation

`Applications/MLXChatExample/Services/MLXService.swift` (whole file, verbatim):

```swift
import Foundation
import HuggingFace
import MLX
import MLXHuggingFace
import MLXLLM
import MLXLMCommon
import MLXVLM
import Tokenizers

@Observable
class MLXService {
    /// List of available models that can be used for generation.
    static let availableModels: [LMModel] = [
        LMModel(name: "llama3.2:1b", configuration: LLMRegistry.llama3_2_1B_4bit, type: .llm),
        LMModel(name: "qwen2.5:1.5b", configuration: LLMRegistry.qwen2_5_1_5b, type: .llm),
        LMModel(name: "smolLM:135m", configuration: LLMRegistry.smolLM_135M_4bit, type: .llm),
        LMModel(name: "qwen3:0.6b", configuration: LLMRegistry.qwen3_0_6b_4bit, type: .llm),
        LMModel(name: "qwen3:1.7b", configuration: LLMRegistry.qwen3_1_7b_4bit, type: .llm),
        LMModel(name: "qwen3:4b", configuration: LLMRegistry.qwen3_4b_4bit, type: .llm),
        LMModel(name: "qwen3:8b", configuration: LLMRegistry.qwen3_8b_4bit, type: .llm),
        LMModel(name: "qwen2.5VL:3b", configuration: VLMRegistry.qwen2_5VL3BInstruct4Bit, type: .vlm),
        LMModel(name: "qwen2VL:2b", configuration: VLMRegistry.qwen2VL2BInstruct4Bit, type: .vlm),
        LMModel(name: "smolVLM", configuration: VLMRegistry.smolvlminstruct4bit, type: .vlm),
        LMModel(name: "gemma4:E2B", configuration: VLMRegistry.gemma4_E2B_it_4bit, type: .vlm),
        LMModel(name: "gemma4:E4B", configuration: VLMRegistry.gemma4_E4B_it_4bit, type: .vlm),
        LMModel(name: "acereason:7B", configuration: LLMRegistry.acereason_7b_4bit, type: .llm),
        LMModel(name: "gemma3n:E2B", configuration: LLMRegistry.gemma3n_E2B_it_lm_4bit, type: .llm),
        LMModel(name: "gemma3n:E4B", configuration: LLMRegistry.gemma3n_E4B_it_lm_4bit, type: .llm),
    ]

    /// Cache to store loaded model containers to avoid reloading.
    private let modelCache = NSCache<NSString, ModelContainer>()

    @MainActor
    private(set) var modelDownloadProgress: Progress?

    private func load(model: LMModel) async throws -> ModelContainer {
        // Set GPU memory limit to prevent out of memory issues
        Memory.cacheLimit = 20 * 1024 * 1024

        if let container = modelCache.object(forKey: model.name as NSString) {
            return container
        } else {
            let factory: ModelFactory =
                switch model.type {
                case .llm: LLMModelFactory.shared
                case .vlm: VLMModelFactory.shared
                }

            let downloader = #hubDownloader()
            let loader = #huggingFaceTokenizerLoader()

            let container = try await factory.loadContainer(
                from: downloader,
                using: loader,
                configuration: model.configuration
            ) { progress in
                Task { @MainActor in
                    self.modelDownloadProgress = progress
                }
            }

            modelCache.setObject(container, forKey: model.name as NSString)
            return container
        }
    }

    func generate(messages: [Message], model: LMModel) async throws -> AsyncStream<Generation> {
        let modelContainer = try await load(model: model)

        // Exclude trailing empty assistant message so the chat template
        // leaves the assistant turn open for generation (matching ChatSession behavior)
        var inputMessages = messages
        if let last = inputMessages.last, last.role == .assistant, last.content.isEmpty {
            inputMessages.removeLast()
        }

        let chat = inputMessages.map { message in
            let role: Chat.Message.Role =
                switch message.role {
                case .assistant: .assistant
                case .user:      .user
                case .system:    .system
                }

            let images: [UserInput.Image] = message.images.map { imageURL in .url(imageURL) }
            let videos: [UserInput.Video] = message.videos.map { videoURL in .url(videoURL) }

            return Chat.Message(role: role, content: message.content, images: images, videos: videos)
        }

        let userInput = UserInput(
            chat: chat, processing: .init(resize: .init(width: 1024, height: 1024)))

        return try await modelContainer.perform { (context: ModelContext) in
            let lmInput = try await context.processor.prepare(input: userInput)
            let parameters = GenerateParameters(temperature: 0.7)

            return try MLXLMCommon.generate(
                input: lmInput, parameters: parameters, context: context)
        }
    }
}
```

**Extractable facts:**
- `NSCache<NSString, ModelContainer>` works because `ModelContainer` is a class (an actor). Cheap model switching; the OS can evict under pressure.
- `ModelFactory` is an existential (`let factory: ModelFactory = switch …`); `LLMModelFactory.shared` / `VLMModelFactory.shared`.
- `factory.loadContainer(from:using:configuration:) { progress in }` — new 3.x signature. `progress` is a Foundation `Progress`.
- **The trailing-empty-assistant trim (added 2026-06-16)** — if you push an empty `.assistant("")` placeholder into the model input, the chat template *closes* the assistant turn and generation misbehaves. `ChatSession` already handles this; the raw `UserInput` path does not.
- VLM images are resized to **1024×1024** via `UserInput.Processing(resize:)` before the processor runs.
- Generation is produced *inside* `modelContainer.perform { context in … }` and the returned `AsyncStream<Generation>` is consumed outside.

#### 5.2.2 `ChatViewModel` — cancellation, media, metrics

`Applications/MLXChatExample/ViewModels/ChatViewModel.swift:61-136` (verbatim):

```swift
    /// Generates response for the current prompt and media attachments
    func generate() async {
        // Cancel any existing generation task
        if let existingTask = generateTask {
            existingTask.cancel()
            generateTask = nil
        }

        isGenerating = true

        messages.append(.user(prompt, images: mediaSelection.images, videos: mediaSelection.videos))
        messages.append(.assistant(""))

        clear(.prompt)

        generateTask = Task {
            for await generation in try await mlxService.generate(
                messages: messages, model: selectedModel)
            {
                switch generation {
                case .chunk(let chunk):
                    if let assistantMessage = messages.last {
                        assistantMessage.content += chunk
                    }
                case .info(let info):
                    generateCompletionInfo = info
                case .toolCall(let call):
                    break
                }
            }
        }

        do {
            try await withTaskCancellationHandler {
                try await generateTask?.value
            } onCancel: {
                Task { @MainActor in
                    generateTask?.cancel()
                    if let assistantMessage = messages.last {
                        assistantMessage.content += "\n[Cancelled]"
                    }
                }
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isGenerating = false
        generateTask = nil
    }

    /// Processes and adds media attachments to the current message
    func addMedia(_ result: Result<URL, any Error>) {
        do {
            let url = try result.get()
            if let mediaType = UTType(filenameExtension: url.pathExtension) {
                if mediaType.conforms(to: .image) {
                    mediaSelection.images = [url]
                } else if mediaType.conforms(to: .movie) {
                    mediaSelection.videos = [url]
                }
            }
        } catch {
            errorMessage = "Failed to load media item.\n\nError: \(error)"
        }
    }
```

`Generation` cases confirmed: **`.chunk(String)`, `.info(GenerateCompletionInfo)`, `.toolCall(ToolCall)`**.
`GenerateCompletionInfo.tokensPerSecond: Double`.

Security-scoped URL handling for macOS `fileImporter`, `ChatViewModel.swift:158-188`:

```swift
@Observable
class MediaSelection {
    var isShowing = false
    var images: [URL] = [] { didSet { didSetURLs(oldValue, images) } }
    var videos: [URL] = [] { didSet { didSetURLs(oldValue, videos) } }
    var isEmpty: Bool { images.isEmpty && videos.isEmpty }

    private func didSetURLs(_ old: [URL], _ new: [URL]) {
        // the urls we get from fileImporter require SSB calls to access
        new.filter { !old.contains($0) }.forEach { _ = $0.startAccessingSecurityScopedResource() }
        old.filter { !new.contains($0) }.forEach { $0.stopAccessingSecurityScopedResource() }
    }
}
```

`ClearOption: RawRepresentable, OptionSet` with `.prompt` (1<<0), `.chat` (1<<1), `.meta` (1<<2).

#### 5.2.3 ⭐ The iOS VLM image fix — commit `378f244` (2026-06-16)

Commit message:
```
MLXChatExample: fix VLM image handling on iOS (PhotosPicker, EXIF, empty assistant trim) (#472)

Fix VLM image handling on iOS

- Use custom Transferable types for reliable PhotosPicker loading
- Normalize image orientation before saving (CIImage ignores EXIF)
- Exclude trailing empty assistant message from model input
```

`Applications/MLXChatExample/ChatView.swift` — verbatim, whole file:

```swift
import AVFoundation
import AVKit
import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

#if canImport(UIKit)
    import UIKit

    /// Transferable wrapper that explicitly requests image content type from PhotosPicker.
    private struct PickedImage: Transferable {
        let data: Data

        static var transferRepresentation: some TransferRepresentation {
            DataRepresentation(importedContentType: .image) { data in
                PickedImage(data: data)
            }
        }
    }

    /// Transferable wrapper for video content from PhotosPicker.
    private struct PickedVideo: Transferable {
        let url: URL

        static var transferRepresentation: some TransferRepresentation {
            FileRepresentation(importedContentType: .movie) { receivedFile in
                let dest = FileManager.default.temporaryDirectory
                    .appendingPathComponent(
                        "\(UUID().uuidString).\(receivedFile.file.pathExtension)")
                try FileManager.default.copyItem(at: receivedFile.file, to: dest)
                return PickedVideo(url: dest)
            }
        }
    }
#endif

struct ChatView: View {
    @Bindable private var vm: ChatViewModel

    #if os(iOS)
        /// Selected items from PhotosPicker
        @State private var photosPickerItems: [PhotosPickerItem] = []
    #endif

    init(viewModel: ChatViewModel) { self.vm = viewModel }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ConversationView(messages: vm.messages)
                Divider()
                if !vm.mediaSelection.isEmpty {
                    MediaPreviewsView(mediaSelection: vm.mediaSelection)
                }
                PromptField(
                    prompt: $vm.prompt,
                    sendButtonAction: vm.generate,
                    // Only show media button for vision-capable models
                    mediaButtonAction: vm.selectedModel.isVisionModel
                        ? { vm.mediaSelection.isShowing = true } : nil
                )
                .padding()
            }
            .navigationTitle("MLX Chat Example")
            .toolbar { ChatToolbarView(vm: vm) }
            // Handle media file selection
            #if os(iOS)
                .photosPicker(
                    isPresented: $vm.mediaSelection.isShowing,
                    selection: $photosPickerItems,
                    maxSelectionCount: 1,
                    matching: .any(of: [.images, .videos])
                )
                .onChange(of: photosPickerItems) {
                    Task {
                        for item in photosPickerItems {
                            if item.supportedContentTypes.contains(where: { $0.conforms(to: .image) }) {
                                // Load image with explicit .image content type
                                if let picked = try? await item.loadTransferable(type: PickedImage.self),
                                    let uiImage = UIImage(data: picked.data)
                                {
                                    // Normalize orientation so pixels match the display orientation.
                                    // UIImage.jpegData() only writes an EXIF tag but CIImage(contentsOf:)
                                    // does not apply it, so the VLM would receive a rotated image.
                                    let renderer = UIGraphicsImageRenderer(size: uiImage.size)
                                    let oriented = renderer.image { _ in
                                        uiImage.draw(in: CGRect(origin: .zero, size: uiImage.size))
                                    }
                                    if let jpegData = oriented.jpegData(compressionQuality: 0.9) {
                                        let url = FileManager.default.temporaryDirectory
                                            .appendingPathComponent("\(UUID().uuidString).jpg")
                                        try? jpegData.write(to: url)
                                        vm.addMedia(.success(url))
                                    }
                                }
                            } else if item.supportedContentTypes.contains(where: { $0.conforms(to: .movie) }) {
                                if let picked = try? await item.loadTransferable(type: PickedVideo.self) {
                                    vm.addMedia(.success(picked.url))
                                }
                            }
                        }
                        photosPickerItems = []
                    }
                }
            #else
                .fileImporter(
                    isPresented: $vm.mediaSelection.isShowing,
                    allowedContentTypes: [.image, .movie],
                    onCompletion: vm.addMedia
                )
            #endif
        }
    }
}
```

**Three separate footguns, all worth a guide section:**
1. **PhotosPicker + `loadTransferable(type: Data.self)` is unreliable.** Fix: declare `PickedImage: Transferable` with `DataRepresentation(importedContentType: .image)` and `PickedVideo` with `FileRepresentation(importedContentType: .movie)` (the file rep must **copy** out of the sandboxed temp URL that `receivedFile.file` points to, which is deleted on return).
2. **EXIF orientation is silently dropped.** `UIImage.jpegData()` writes the orientation as an EXIF tag; `CIImage(contentsOf:)` — which the MLX VLM image pipeline uses — **does not apply it**, so a portrait photo arrives rotated 90°. Fix: re-render pixels with `UIGraphicsImageRenderer` before writing JPEG (`compressionQuality: 0.9`).
3. **Empty trailing assistant message** must be trimmed before the chat template runs (see `MLXService.generate`).

Platform split: iOS uses `.photosPicker(...)`; macOS uses `.fileImporter(...)`.

#### 5.2.4 HubApi download location override (macOS vs iOS)

`Applications/MLXChatExample/Support/HubApi+default.swift` (whole file):

```swift
import Foundation
@preconcurrency import Hub

extension HubApi {
    #if os(macOS)
        static let `default` = HubApi(
            downloadBase: URL.downloadsDirectory.appending(path: "huggingface")
        )
    #else
        static let `default` = HubApi(
            downloadBase: URL.cachesDirectory.appending(path: "huggingface")
        )
    #endif
}
```
Note `@preconcurrency import Hub` (swift-transformers' `Hub`, not the new `HuggingFace` module). **This file is now vestigial** — `MLXService` uses `#hubDownloader()` rather than `HubApi.default` since commit `357c97f`. Kept in the tree; a reader copying this app should be aware.

#### 5.2.5 Streaming UI bits

`ConversationView.swift`:
```swift
ScrollView {
    LazyVStack(spacing: 12) {
        ForEach(messages) { message in
            MessageView(message).padding(.horizontal, 12)
        }
    }
}
.padding(.vertical, 8)
.defaultScrollAnchor(.bottom, for: .sizeChanges)
```
`.defaultScrollAnchor(.bottom, for: .sizeChanges)` is the key modifier for auto-follow during streaming.

`MessageView.swift` renders markdown with **zero dependencies**:
```swift
// LocalizedStringKey used to trigger default handling of markdown content.
Text(LocalizedStringKey(message.content))
    .textSelection(.enabled)
```
`MLXChatExample/README.md:84-96` explains the trade-off verbatim: default SwiftUI markdown "*does not support advanced features like tables and task lists that are available in GitHub Flavored Markdown (GFM)*"; they avoided `swift-markdown-ui` because of an "*unresolved issue with text selection*" (issue 264); suggests `SelectableText` + `MarkdownToAttributedString` as alternatives. See repo issue #297.

`PromptField.swift` — self-contained run/stop button:
```swift
Button {
    if isRunning { task?.cancel(); removeTask() }
    else { task = Task { await sendButtonAction(); removeTask() } }
} label: {
    Image(systemName: isRunning ? "stop.circle.fill" : "paperplane.fill")
}
.keyboardShortcut(isRunning ? .cancelAction : .defaultAction)
...
private var isRunning: Bool { task != nil && !(task!.isCancelled) }
```

Toolbar (`ChatToolbarView.swift`) shows `ErrorView` (popover), `DownloadProgressView` (popover with `progress.localizedAdditionalDescription` / `.localizedDescription`), a clear-chat button labeled with tokens/sec, and a `Picker` bound to `$vm.selectedModel` over `MLXService.availableModels`.

Images in messages are displayed with `AsyncImage(url:)` even for local file URLs; videos with `VideoPlayer(player: AVPlayer(url:))`.

### 5.3 The `mlx-swift-lm` 3.x macros (`MLXHuggingFace`)

Three macros are used across the repo. **All require `import MLXHuggingFace`** (plus `import HuggingFace` and `import Tokenizers` in practice).

| Macro | Forms seen | Where |
|---|---|---|
| `#hubDownloader` | `#hubDownloader()` / `#hubDownloader(client)` / bare `#hubDownloader` | `LLMEvaluator.swift:108`, `MLXService.swift:71`, `LLMTool.swift:41`, `embedder-tool/ModelArguments.swift:49,78` |
| `#huggingFaceTokenizerLoader` | `#huggingFaceTokenizerLoader()` / bare | `LLMEvaluator.swift:142`, `MLXService.swift:72`, `LLMTool.swift:63`, `ModelArguments.swift:50` |
| `#huggingFaceLoadModelContainer` | `#huggingFaceLoadModelContainer(configuration:) { progress in }` | `LLMBasic/ChatModel.swift:46`, `LoRATrainingExample/ContentView.swift:146` |

Commit `85a9d85` (2026-06-16) shows exactly what the third macro replaces:

```diff
-                try await LLMModelFactory.shared.loadContainer(
-                    from: #hubDownloader(),
-                    using: #huggingFaceTokenizerLoader(),
+                try await #huggingFaceLoadModelContainer(
                     configuration: modelConfiguration
                 ) { value in
```

and in LoRATrainingExample:
```diff
-            let downloader = #hubDownloader()
-            let loader = #huggingFaceTokenizerLoader()
-
-            let modelContainer = try await LLMModelFactory.shared.loadContainer(
-                from: downloader,
-                using: loader,
+            let modelContainer = try await #huggingFaceLoadModelContainer(
                 configuration: modelConfiguration
             ) {
```

So `#huggingFaceLoadModelContainer(configuration:progressHandler:)` ≈ `LLMModelFactory.shared.loadContainer(from: #hubDownloader(), using: #huggingFaceTokenizerLoader(), configuration:…)`. (**UNVERIFIED**: how it picks LLM vs VLM factory — in both usages the model is an LLM.)

`#hubDownloader(client)` accepts a `HubClient`:
```swift
    var downloader: any Downloader {
        let client =
            if let download {
                HubClient(cache: HubCache(cacheDirectory: download))
            } else {
                HubClient()
            }
        let downloader = #hubDownloader(client)
        return downloader
    }
```
(`Tools/llm-tool/LLMTool.swift:34-43`; identical in `embedder-tool/ModelArguments.swift:71-80`.)

**Gotcha:** `-skipMacroValidation` is required for `xcodebuild` — otherwise Xcode blocks the unvalidated macro plugin. Added to CI in `357c97f`.

New HF types (from `swift-huggingface` 0.9.0 via the `HuggingFace` module): `HubClient`, `HubCache(cacheDirectory:)`, `HubCache.default`, `HubCache.repoDirectory(repo:kind:)`, `Repo.ID(namespace:name:)`, `.model` repo kind, and the protocol `Downloader`. Old `Hub` / `HubApi` (swift-transformers) is still used by the **StableDiffusion** library.

### 5.4 `LLMEval` — metrics, tools, thinking mode, long prompts

Default model, `ViewModels/LLMEvaluator.swift:50`:
```swift
    /// This controls which model loads.
    var modelConfiguration = LLMRegistry.qwen3_8b_4bit
```
README suggests `LLMRegistry.phi4bit` as a smaller alternative and warns:

> "*You may also find that running outside the debugger boosts performance. You can do this in Xcode by pressing cmd-opt-r and unchecking "Debug Executable".*" (README.md:43)

#### 5.4.1 Two-phase load with explicit `resolve(...)` + verification

`LLMEvaluator.swift:100-155` (verbatim):

```swift
    private func performLoad() async throws -> ModelContainer {
        loadState = .loading
        modelInfo = "Downloading \(modelName)..."
        downloadProgress = 0.0

        Memory.cacheLimit = 20 * 1024 * 1024

        do {
            let downloader = #hubDownloader()

            let resolved = try await resolve(
                configuration: modelConfiguration, from: downloader, useLatest: false
            ) { [weak self] progress in
                Task { @MainActor in
                    self?.updateDownloadProgress(progress)
                }
            }

            // Verify the download succeeded by checking for model files
            let fileManager = FileManager.default
            let directoryExists = fileManager.fileExists(atPath: resolved.modelDirectory.path)
            let contents =
                (try? fileManager.contentsOfDirectory(atPath: resolved.modelDirectory.path)) ?? []
            let hasSafetensors = contents.contains { $0.hasSuffix(".safetensors") }

            if !directoryExists || !hasSafetensors {
                throw NSError(
                    domain: "LLMEvaluator", code: -1,
                    userInfo: [NSLocalizedDescriptionKey:
                        "Model download failed. Please check your network connection and try again."])
            }

            modelInfo = "Loading \(modelName)..."
            downloadProgress = nil
            totalSize = nil

            let modelContainer = try await LLMModelFactory.shared.loadContainer(
                from: resolved.modelDirectory,
                using: #huggingFaceTokenizerLoader())

            let numParams = await modelContainer.perform { $0.model.numParameters() }

            self.prompt = PresetPrompts.all[0].prompt
            self.modelInfo = formatModelInfo(name: modelConfiguration.name, parameters: numParams)
            loadState = .loaded(modelContainer)
            return modelContainer

        } catch {
            resetLoadingState()
            throw error
        }
    }
```

**Two distinct APIs shown here:**
- Free function `resolve(configuration:from:useLatest:progressHandler:) async throws -> <something with .modelDirectory>` — download only.
- `LLMModelFactory.shared.loadContainer(from: URL, using: tokenizerLoader)` — **load from an already-downloaded directory**.
- `modelContainer.perform { $0.model.numParameters() }` for parameter count.

Reentrancy guard (`load()`, lines 84-98) — note this was changed in `c1198e2` from recursion to a `while true` loop:
```swift
    func load() async throws -> ModelContainer {
        while true {
            switch loadState {
            case .idle:
                return try await performLoad()
            case .loading:
                // Already loading, wait and retry
                try await Task.sleep(for: .milliseconds(100))
            case .loaded(let modelContainer):
                return modelContainer
            }
        }
    }
```

Download progress → human text (`updateDownloadProgress`, lines 157-170): if `progress.totalUnitCount` is small (<100) it means *file count* → "File 3 of 8"; otherwise byte counts via `ByteCountFormatter` with `[.useMB, .useGB]`.

#### 5.4.2 Generation loop with TTFT, tok/s, truncation detection, tool calls

`LLMEvaluator.swift:227-352` — the important shape (verbatim excerpts):

```swift
        var chat: [Chat.Message] = [
            .system("You are a helpful assistant"),
            .user(prompt),
        ]

        if let toolResult {
            chat.append(.tool(toolResult))
        }

        let userInput = UserInput(
            chat: chat,
            tools: includeWeatherTool ? toolExecutor.allToolSchemas : nil,
            additionalContext: ["enable_thinking": enableThinking]
        )

        do {
            let modelContainer = try await load()
            let parameters = generateParameters

            // Seed random generator to ensure varied output each generation
            MLXRandom.seed(UInt64(Date.timeIntervalSinceReferenceDate * 1000))

            let lmInput = try await modelContainer.prepare(input: userInput)
            let promptTokenCount = lmInput.text.tokens.size
            let start = Date.timeIntervalSinceReferenceDate
            let stream = try await modelContainer.generate(input: lmInput, parameters: parameters)

            var iterator = stream.makeAsyncIterator()
            if let first = await iterator.next() {
                let firstTick = Date.timeIntervalSinceReferenceDate
                let promptTime = firstTick - start
                ...
                var pendingToolCall: ToolCall?
                if let toolCall = first.toolCall {
                    pendingToolCall = toolCall
                } else if let chunk = first.chunk {
                    if !chunk.isEmpty { /* append to output */ }
                }

                if pendingToolCall == nil {
                    while let next = await iterator.next() {
                        if let toolCall = next.toolCall { pendingToolCall = toolCall; break }
                        if let chunk = next.chunk { ... }
                    }
                }
                ...
                if self.totalTokens >= parameters.maxTokens ?? Int.max {
                    self.wasTruncated = true
                }
                if let toolCall = pendingToolCall {
                    await self.executeToolAndContinue(toolCall: toolCall, originalPrompt: prompt)
                }
            }
        } catch { ... output = "Failed: \(error)" }
```

Key API facts extracted:
- `Chat.Message` statics: **`.system(_:)`, `.user(_:)`, `.tool(_:)`** (plus `Chat.Message(role:content:images:videos:)`).
- `UserInput(chat:tools:additionalContext:)` — `tools: [ToolSpec]?`, `additionalContext: [String: Any]` (here `["enable_thinking": Bool]` → **Qwen3 thinking mode toggle**, threaded into the Jinja chat template).
- `modelContainer.prepare(input:) async throws -> LMInput`; `lmInput.text.tokens.size` = prompt token count.
- `modelContainer.generate(input:parameters:) async throws -> AsyncStream<Generation>`.
- `Generation` has **optional accessors** `.chunk: String?` and `.toolCall: ToolCall?` in addition to being an enum.
- Manual `stream.makeAsyncIterator()` + `await iterator.next()` lets you time the first token (TTFT).
- `GenerateParameters.maxTokens` is **`Int?`**.

`ToolExecutor` (`Applications/LLMEval/Services/ToolExecutor.swift`, whole file):

```swift
import Foundation
import MLXLMCommon

public typealias ToolSpec = [String: Sendable]

@MainActor
class ToolExecutor {

    let currentWeatherTool = Tool<WeatherInput, WeatherOutput>(
        name: "get_current_weather",
        description: "Get the current weather in a given location",
        parameters: [
            .required("location", type: .string, description: "The city and state, e.g. San Francisco, CA"),
            .optional(
                "unit",
                type: .string,
                description: "The unit of temperature",
                extraProperties: [
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                ]
            ),
        ]
    ) { input in
        let range = input.unit == "celsius" ? (min: -20.0, max: 40.0) : (min: 0, max: 100)
        let temperature = Double.random(in: range.min ... range.max)
        let conditions = ["Sunny", "Cloudy", "Rainy", "Snowy", "Windy", "Stormy"].randomElement()!
        return WeatherOutput(temperature: temperature, conditions: conditions)
    }

    let addTool = Tool<AddInput, AddOutput>(
        name: "add_two_numbers",
        description: "Add two numbers together",
        parameters: [
            .required("first",  type: .int, description: "The first number to add"),
            .required("second", type: .int, description: "The second number to add"),
        ]
    ) { input in AddOutput(result: input.first + input.second) }

    let timeTool = Tool<EmptyInput, TimeOutput>(
        name: "get_time", description: "Get the current time", parameters: []
    ) { _ in TimeOutput(time: Date.now.formatted()) }

    var allToolSchemas: [ToolSpec] {
        [currentWeatherTool.schema, addTool.schema, timeTool.schema]
    }

    func execute(_ toolCall: ToolCall) async throws -> String {
        switch toolCall.function.name {
        case currentWeatherTool.name:
            return try await toolCall.execute(with: currentWeatherTool).toolResult
        case addTool.name:
            return try await toolCall.execute(with: addTool).toolResult
        case timeTool.name:
            return try await toolCall.execute(with: timeTool).toolResult
        default:
            return "Unknown tool: \(toolCall.function.name)"
        }
    }
}
```
Input/output structs are plain `Codable` (`Applications/LLMEval/Models/ToolDefinitions.swift`), e.g. `struct WeatherInput: Codable { let location: String; let unit: String? }`, `struct EmptyInput: Codable {}`.

**Tool API surface:** `Tool<Input: Codable, Output: Codable>(name:description:parameters:_ handler:)`; `.schema -> ToolSpec`; `.name`; parameter builders `.required(_:type:description:)` and `.optional(_:type:description:extraProperties:)`; parameter types seen: `.string`, `.int`. `ToolCall.function.name`; `toolCall.execute(with: tool)` returns something with `.toolResult: String`.

**Tool-result continuation pattern** (`executeToolAndContinue`, lines 354-367): the app appends `[Executing tool: name…]` to the visible output, executes, then **recursively calls `generate(prompt:toolResult:)`**, which rebuilds the chat as `[.system, .user(prompt), .tool(result)]`. Note: this is a *fresh* chat each round, not an accumulating transcript.

#### 5.4.3 Adaptive layout for iPhone portrait (`c1198e2`)

`HeaderView`/`MetricsView` both branch on `@Environment(\.horizontalSizeClass)`:
```swift
    @Environment(\.horizontalSizeClass) var horizontalSizeClass

    var body: some View {
        if horizontalSizeClass == .compact {
            DisclosureGroup("Statistics") { stats.scaleEffect(0.8) }
        } else {
            stats
        }
    }
```
`HeaderView` similarly collapses "Controls" into a `DisclosureGroup` when compact.

Max-tokens slider uses a log2 binding (`HeaderView.swift:59-69`):
```swift
Slider(
    value: Binding(
        get: { log2(Double(llm.maxTokens)) },
        set: { llm.maxTokens = Int(pow(2, $0)) }
    ),
    in: 10 ... 15,  // 2^10 (1024) to 2^15 (32768)
    step: 1
)
```

`MetricsView` help/alert text (macOS uses `.help(...)`, iOS uses an `.alert`):
```
Active Memory: <used>/<Memory.memoryLimit>
Cache Memory: <cache>/<Memory.cacheLimit>
Peak Memory: <peak>
```

`OutputView.swift` renders either `Text(output)` or `Markdown(output)` (from **MarkdownUI**), auto-scrolls with `ScrollViewReader` + `.onChange(of: output) { sp.scrollTo("bottom") }` and shows an orange "Output truncated: Maximum token limit reached" banner when `wasTruncated`.

Preset prompts (`Models/PresetPrompts.swift`) load long prompts from bundled markdown:
```swift
    private static func loadPrompt(named fileName: String) -> String {
        guard let url = Bundle.main.url(forResource: fileName, withExtension: "md"),
            let content = try? String(contentsOf: url, encoding: .utf8)
        else { return "Could not load \(fileName).md. …" }
        return content
    }
```
Bundled: `Models/LongPrompt.md` (~1300+ lines of MLX-related prose used as a long-context stress test) and `Models/CarKeysStory.md`.

Clipboard copy is platform-split:
```swift
#if os(macOS)
    NSPasteboard.general.clearContents()
    NSPasteboard.general.setString(string, forType: .string)
#else
    UIPasteboard.general.string = string
#endif
```
And `#if os(visionOS) .padding(40) #else .padding() #endif`.

---

## 6. `llm-tool` — full CLI reference (verified from source)

`@main struct LLMTool: AsyncParsableCommand`, subcommands `eval` (default), `chat`, `lora`, `list`.

```swift
    static let configuration = CommandConfiguration(
        abstract: "Command line tool for generating text and manipulating LLMs",
        subcommands: [EvaluateCommand.self, ChatCommand.self, LoRACommand.self, ListCommands.self],
        defaultSubcommand: EvaluateCommand.self)
```

### 6.1 Option groups → flags

**`ModelArguments`**
| Flag | Type | Default | Help |
|---|---|---|---|
| `--model` | String? | — | "Name of the Hugging Face model or absolute path to directory" |
| `--download` | URL? | — | "Hub download directory" |

Model resolution (`LLMTool.swift:46-65`):
```swift
        if modelName.hasPrefix("/") {
            modelConfiguration = ModelConfiguration(directory: URL(filePath: modelName))
        } else {
            modelConfiguration = modelFactory.configuration(id: modelName)
        }
        return try await modelFactory.loadContainer(
            from: self.downloader,
            using: #huggingFaceTokenizerLoader(),
            configuration: modelConfiguration)
```

**`PromptArguments`**
| Flag | Default | Notes |
|---|---|---|
| `-p/--prompt` | `configuration.defaultPrompt` | **`@path,@path` loads from files**, joined by newline |

```swift
    func resolvePrompt(configuration: ModelConfiguration) throws -> String {
        let prompt = self.prompt ?? configuration.defaultPrompt
        if prompt.hasPrefix("@") {
            let names = prompt.split(separator: ",").map { String($0.dropFirst()) }
            return try names.map { try String(contentsOfFile: $0) }.joined(separator: "\n")
        } else { return prompt }
    }
```

**`MediaArguments`**
| Flag | Type | Notes |
|---|---|---|
| `--resize` | `[Int]` (`.upToNextOption`) | 1 value → square; 2 values → `CGSize(width: v0, height: v1)` |
| `--image` | `[URL]` (`.upToNextOption`) | paths **or** URLs |
| `--video` | `[URL]` (`.upToNextOption`) | |

→ `UserInput.Image.url(_)`, `UserInput.Video.url(_)`, `UserInput.Processing` with `.resize: CGSize`.

**`GenerateArguments`**
| Flag | Type | Default |
|---|---|---|
| `-s/--system` | String | `""` |
| `-m/--max-tokens` | Int | `100` |
| `-t/--temperature` | Float | `0.6` |
| `--top-p` | Float | `1.0` |
| `--repetition-penalty` | Float? | nil |
| `--repetition-context-size` | Int | `20` |
| `--extra-eos-token` | String? | nil |
| `--seed` | UInt64 | `0` |
| `--kv-bits` | Int? | nil — "Number of bits for KV cache quantization (nil = no quantization)" |
| `--kv-group-size` | Int | `64` |
| `--quantized-kv-start` | Int | `0` — "Step to begin using quantized KV cache when kv-bits is set" |
| `-q/--quiet` | Flag | false |
| `--tool-time` | Flag | false — "Enable time telling tool" |

```swift
    var generateParameters: GenerateParameters {
        GenerateParameters(
            maxTokens: maxTokens,
            kvBits: kvBits,
            kvGroupSize: kvGroupSize,
            quantizedKVStart: quantizedKvStart,
            temperature: temperature, topP: topP, repetitionPenalty: repetitionPenalty,
            repetitionContextSize: repetitionContextSize)
    }
```
(`GenerateParameters` also has `prefillStepSize` in its init as of commit `5651f0b`, though `llm-tool` doesn't expose it.)

Extra EOS injection:
```swift
    func prepare(_ context: inout ModelContext) {
        if let extraEosToken {
            context.configuration.extraEOSTokens.insert(extraEosToken)
        }
    }
```
applied via `await modelContainer.update { [generate] context in generate.prepare(&context) }`.

**`MemoryArguments`**: `--memory-stats` (flag), `--cache-size <M>`, `--memory-size <M>`.

### 6.2 `eval` — LLM/VLM auto-switch + `ChatSession`

`EvaluateCommand.run()` (verbatim, `LLMTool.swift:321-389`):

```swift
    @MainActor
    mutating func run() async throws {
        let modelFactory: any ModelFactory
        let defaultModel: ModelConfiguration

        // Switch between LLM and VLM based on presence of media
        let vlm = !media.image.isEmpty || !media.video.isEmpty
        if vlm {
            modelFactory = VLMModelFactory.shared
            defaultModel = MLXVLM.VLMRegistry.qwen2VL2BInstruct4Bit
        } else {
            modelFactory = LLMModelFactory.shared
            defaultModel = MLXLLM.LLMRegistry.mistral7B4bit
        }

        let modelContainer = try await memory.start { [args] in
            try await args.load(defaultModel: defaultModel.name, modelFactory: modelFactory)
        }

        await modelContainer.update { [generate] context in
            generate.prepare(&context)
        }

        let modelConfiguration = await modelContainer.configuration

        let prompt =
            (try? self.prompt.resolvePrompt(configuration: modelConfiguration))
            ?? modelConfiguration.defaultPrompt

        if !generate.quiet { print("Loaded \(modelConfiguration.name)") }

        let session = ChatSession(
            modelContainer,
            instructions: generate.system,
            generateParameters: generate.generateParameters,
            processing: media.processing,
            tools: generate.toolSpecs
        )

        if !generate.quiet {
            print("Starting generation ...")
            print(prompt, terminator: " ")
        }

        // use the `stream` variant as we want to capture the generation statistics as well
        var completionInfo: GenerateCompletionInfo?

        for try await item in session.streamDetails(
            to: prompt, images: media.images, videos: media.videos
        ) {
            switch item {
            case .chunk(let chunk): print(chunk, terminator: "")
            case .info(let info): completionInfo = info
            default: break
            }
        }

        if !generate.quiet, let completionInfo {
            print("------")
            print(completionInfo.summary())
            memory.reportMemoryStatistics()
        }
    }
```

**`ChatSession` API confirmed:**
- `ChatSession(_ container: ModelContainer, instructions: String? = nil, generateParameters: GenerateParameters, processing: UserInput.Processing, tools: [ToolSpec])`
- `streamResponse(to: String) -> AsyncThrowingSequence<String>` (LLMBasic)
- `streamDetails(to: String, images: [UserInput.Image] = [], videos: [UserInput.Video] = []) -> AsyncThrowingSequence<Generation>`
- `await session.clear()` — reset conversation
- `session.generateParameters` is **mutable**: `.temperature`, `.topP`, `.maxTokens`
- `GenerateCompletionInfo.summary()`, `.promptTime`, `.tokensPerSecond`

### 6.3 `chat` — interactive REPL with slash commands

`Tools/llm-tool/Chat.swift`. Model load falls back LLM↔VLM:
```swift
        let modelContainer = try await memory.start { [args] in
            do {
                return try await args.load(
                    defaultModel: defaultModel.name, modelFactory: VLMModelFactory.shared)
            } catch ModelFactoryError.unsupportedModelType {
                return try await args.load(
                    defaultModel: defaultModel.name, modelFactory: LLMModelFactory.shared)
            }
        }
```
(`ModelFactoryError.unsupportedModelType` is the sentinel.)

Slash commands (verbatim `help()` output):
```
/help -- this message
/quit -- terminate the chat
/memory -- print memory stats
/stats -- toggle token stats
/reset -- reset the chat session to initial state
/image [pathOrURL] -- provide an image
/video [pathOrURL] -- provide a video
/parameters -- print generation parametes
/temperature [number] -- set the sampling temperature
/topP [number] -- set the top p sampling
/maxTokens [number] -- set the maximum number of tokens to generate or no number to remove limit
```
Implementation notes: images/videos accumulate in local arrays, are passed to `streamDetails(to:images:videos:)`, then **cleared after each turn** (`images.removeAll()`); the model keeps them in conversation context. `/maxTokens` with no number → `Int(rest)` is `nil` → unlimited. URL heuristic:
```swift
                func url(_ string: String) -> URL? {
                    if string.hasPrefix("/") || !string.hasPrefix("http") { URL(filePath: string) }
                    else { URL(string: string) }
                }
```

Real transcript from `Tools/llm-tool/README.md:57-71`:
```
./mlx-run llm-tool chat --download ~/Downloads/huggingface --model mlx-community/gemma-3-12b-it-qat-4bit

Loading mlx-community/gemma-3-12b-it-qat-4bit...

> /image support/test.jpg
> what type of creature is in the image?
The creature in the image is a **dog**, specifically a **Poodle**. …
> where is the dog sitting?
The dog is sitting on someone's **lap**. …
```

### 6.4 `list` — enumerate registries

```swift
struct ListLLMCommand: AsyncParsableCommand {   // commandName "llms"
    func run() async throws {
        for configuration in LLMRegistry.shared.models {
            switch configuration.id {
            case .id(let id, let revision): print("\(id)/\(revision)")
            case .directory: break
            }
        }
    }
}
```
Identical `ListVLMCommand` (`vlms`) over `VLMRegistry.shared.models`.
→ **`ModelConfiguration.id` is an enum with cases `.id(String, String /* revision */)` and `.directory`.**

Used by `support/generate-run-all-llms.sh`:
```sh
#!/bin/sh
echo "#!/bin/sh"
echo "# NOTE: GENERATED BY generate-run-all-llms.sh -- DO NOT MODIFY BY HAND"

./mlx-run llm-tool list llms | \
	awk '{printf "./mlx-run llm-tool eval --download ~/Downloads/huggingface --model %s\n", $0}' | \
	awk '{printf "echo\necho ======\necho '\''%s'\''\n%s\n", $0, $0}'

./mlx-run llm-tool list vlms | \
	awk '{printf "./mlx-run llm-tool eval --download ~/Downloads/huggingface --model %s --resize 512 --image support/test.jpg\n", $0}' | \
	awk '{printf "echo\necho ======\necho '\''%s'\''\n%s\n", $0, $0}'
```

Models exercised by the generated `support/run-all-llms.sh` (130 lines) — a snapshot of the registries:

LLMs: `mlx-community/quantized-gemma-2b-it`, `granite-3.3-2b-instruct-4bit`, `Mistral-7B-Instruct-v0.3-4bit`, `Meta-Llama-3-8B-Instruct-4bit`, `Qwen3-4B-4bit`, `Qwen1.5-0.5B-Chat-4bit`, `Qwen3-1.7B-4bit`, `Mistral-Nemo-Instruct-2407-4bit`, `gemma-2-9b-it-4bit`, `gemma-2-2b-it-4bit`, `Qwen2.5-7B-Instruct-4bit`, `Qwen2.5-1.5B-Instruct-4bit`, `Meta-Llama-3.1-8B-Instruct-4bit`, `Llama-3.2-1B-Instruct-4bit`, `Llama-3.2-3B-Instruct-4bit`, `Phi-3.5-mini-instruct-4bit`, `Phi-3.5-MoE-instruct-4bit`, `phi-2-hf-4bit-mlx`, `SmolLM-135M-Instruct-4bit`, `OpenELM-270M-Instruct`, `CodeLlama-13b-Instruct-hf-4bit-MLX`, `DeepSeek-R1-Distill-Qwen-7B-4bit`, `GLM-4-9B-0414-4bit`, `MiMo-7B-SFT-4bit`, `Qwen3-0.6B-4bit`, `Qwen3-8B-4bit`, `Qwen3-30B-A3B-4bit`.

VLMs (run with `--resize 512 --image support/test.jpg`): `mlx-community/SmolVLM-Instruct-4bit`, `paligemma-3b-mix-448-8bit`, `Qwen2.5-VL-3B-Instruct-4bit`, `HuggingFaceTB/SmolVLM2-500M-Video-Instruct-mlx`, `Qwen2-VL-2B-Instruct-4bit`.

### 6.5 Example invocations baked into `llm-tool.xcscheme`

```
--model mlx-community/CodeLlama-13b-Instruct-hf-4bit-MLX
--model mlx-community/gemma-3-27b-it-qat-4bit --prompt 'Describe the image in English.' --image https://www.gstatic.com/webp/gallery/1.webp
--model microsoft/Phi-4-mini-instruct --prompt "Why is the sky blue?" --extra-eos-token "<|end|>"
--model mlx-community/Qwen2-VL-2B-Instruct-4bit --prompt 'Describe the image in English.' --image https://www.gstatic.com/webp/gallery/1.webp
--model mlx-community/Qwen3-1.7B-4bit --prompt "Explain quantum computing in simple terms" --max-tokens 100 --kv-bits 4
--model mlx-community/Qwen3-1.7B-4bit --prompt "Explain quantum computing in simple terms" --max-tokens 100
--repetition-penalty 1.2
--top-p 0.95
--model mlx-community/c4ai-command-r-v01-4bit
--model mlx-community/starcoder2-3b-4bit
--model mlx-community/Qwen1.5-0.5B-Chat-4bit
--prompt 'def quick_sort(arr, left=None, right=None):'
--prompt 'Why is the sky blue?'
--model mlx-community/Mistral-7B-v0.1-hf-4bit-mlx
--model mlx-community/Llama-3.2-1B-Instruct-4bit
--model mlx-community/phi-2-hf-4bit-mlx
```
(All `isEnabled = "NO"` — they're a menu you toggle in Xcode via ⌘⌥R.) Note **`--image` accepts an https URL directly**.

`Tools/llm-tool/README.md:25-26`: "*you may be prompted for access to your Documents directory -- this is where the Hugging Face HubApi stores the downloaded files.*"

---

## 7. LoRA — CLI and app

### 7.1 `llm-tool lora` (Tools/llm-tool/LoraCommands.swift)

Subcommands: `train`, `fuse`, `test`, `eval`.

**`LoRAModelArguments`** (shared):
| Flag | Default |
|---|---|
| `--adapter` | `URL(filePath: "adapters.safetensors")` |
| `--lora-layers` | `16` |
| (+ all `ModelArguments`) | |

```swift
    func load(
        defaultModel: String = defaultModel,
        modelFactory: any ModelFactory = LLMModelFactory.shared
    ) async throws -> (ModelContainer, ModelAdapter) {
        let modelContainer = try await args.load(defaultModel: defaultModel, modelFactory: modelFactory)

        // Load LoRA adapter from directory or create a new one
        let modelAdapter: ModelAdapter
        do {
            modelAdapter = try LoRAContainer.from(directory: adapter)
        } catch {
            modelAdapter = try await modelContainer.perform { context in
                return try LoRAContainer.from(
                    model: context.model, configuration: LoRAConfiguration(numLayers: loraLayers))
            }
        }
        return (modelContainer, modelAdapter)
    }
```

**`lora train` flags:**
| Flag | Default | Help |
|---|---|---|
| `--resume` (Flag) | false | "Resume training with the given adapter file" |
| `--data` | `URL(filePath: "data")` | "Directory with {train, valid, test}.{jsonl,txt} files" |
| `--learning-rate` | `1e-5` (Float) | |
| `--batch-size` | `4` | "Number of dataset items to evaluate per iteration (batch)" |
| `--iterations` | `1000` | |
| `--steps-per-report` | `10` | |
| `--steps-per-eval` | `100` | |
| `--validation-batches` | `10` | "0 uses the entire set" |
| `--save-every` | `100` | checkpoint interval |

```swift
    var parameters: LoRATrain.Parameters {
        var p = LoRATrain.Parameters()
        p.batchSize = self.batchSize
        p.iterations = self.iterations
        p.stepsPerReport = self.stepsPerReport
        p.stepsPerEval = self.stepsPerEval
        p.validationBatches = self.validationBatches
        p.saveEvery = self.saveEvery
        p.adapterURL = args.adapter
        return p
    }
```

Training body:
```swift
        if resume {
            print("Loading pretrained adapters from \(args.adapter.path())")
            try await modelContainer.perform { context in
                try context.model.load(adapter: modelAdapter)
            }
        }

        let train = try loadLoRAData(directory: data, name: "train")
        let valid = try loadLoRAData(directory: data, name: "valid")
        if train.isEmpty { fatalError("Training set is empty: \(data.path()))") }
        if valid.isEmpty { fatalError("Validation set is empty: \(data.path()))") }

        try await modelContainer.perform { [args, parameters, learningRate] context in
            let optimizer = Adam(learningRate: learningRate)
            try LoRATrain.train(
                model: context.model, train: train, validate: valid, optimizer: optimizer,
                tokenizer: context.tokenizer,
                parameters: parameters
            ) { progress in
                print(progress)
                return .more
            }
            try LoRATrain.saveLoRAWeights(model: context.model, url: args.adapter)
        }
```

**`lora fuse` flags:** `--de-quantize` (Flag, "De-quantize QuantizedLinear layers back into Linear"), `--output` (String, "Hub ID (mlx-community/mistral-lora) or path (/tmp/mistral-lora)").

Output-path resolution uses the **new HF cache API**:
```swift
            let cache =
                if let download = args.args.download { HubCache(cacheDirectory: download) }
                else { HubCache.default }
            let parts = output.components(separatedBy: "/")
            guard parts.count == 2 else { fatalError("output must be org/name, e.g. mlx-community/mistral-lora: \(output)") }
            let repo = Repo.ID(namespace: parts[0], name: parts[1])
            outputURL = cache.repoDirectory(repo: repo, kind: .model)
```
Then fuse + copy non-safetensors files + write `weights.safetensors`:
```swift
        try await modelContainer.perform { context in try context.model.fuse(with: modelAdapter) }
        let resolved = try await resolve(
            configuration: modelContainer.configuration, from: args.args.downloader,
            useLatest: false, progressHandler: { _ in })
        ...
        for url in enumerator.allObjects.compactMap({ $0 as? URL }) {
            if url.pathExtension == "safetensors" { continue }   // skip original weights
            try FileManager.default.copyItem(at: url, to: outputURL.appending(component: url.lastPathComponent))
        }
        try await modelContainer.perform { context in
            let weights = Dictionary(uniqueKeysWithValues: context.model.parameters().flattened())
            try save(arrays: weights, url: outputURL.appending(component: "weights.safetensors"))
        }
```

**`lora test`**: `--data`, `--batch-size 4` → `LoRATrain.evaluate(model:dataset:tokenizer:batchSize:batchCount:)` (`batchCount: 0` = whole set), prints `Test loss \(loss), ppl \(exp(loss))`.

**`lora eval`**: uses `context.processor.prepare(input: .init(prompt: prompt))` then `generate.generate(input:context:)`.

`describe(model:)` prints:
```swift
        let totalParameterCount = model.numParameters()
        let trainableParameterCount = model.trainableParameters().flattenedValues().map { $0.size }.reduce(0, +)
```

Full command lines from `Tools/llm-tool/README.md`:
```sh
./mlx-run llm-tool lora train \
    --model mlx-community/Mistral-7B-v0.1-hf-4bit-mlx \
    --data Data/lora \
    --adapter /tmp/lora-layers-4.safetensors \
    --batch-size 1 --lora-layers 4 \
    --cache-size 1024

./mlx-run llm-tool lora test \
    --model mlx-community/Mistral-7B-Instruct-v0.3-4bit \
    --data Data/lora --adapter /tmp/lora-layers-4.safetensors \
    --batch-size 1 --lora-layers 4 --cache-size 1024

./mlx-run llm-tool lora eval \
    --model mlx-community/Mistral-7B-Instruct-v0.3-4bit \
    --adapter /tmp/lora-layers-4.safetensors \
    --lora-layers 4 \
    --prompt "table: 1-10015132-16
columns: Player, No., Nationality, Position, Years in Toronto, School/Club Team
Q: What is terrence ross' nationality
A: "

./mlx-run llm-tool lora fuse \
    --model mlx-community/Mistral-7B-Instruct-v0.3-4bit \
    --adapter /tmp/lora-layers-4.safetensors \
    --output mlx-community/mistral-lora
```
Sample output quoted in README: `Total parameters: 1,242M / Trainable parameters: 0.426M`, per-iteration loss lines with `iterations/sec` and `Tokens/sec`, `Test loss 1.327623, ppl 3.772065`.

**Data format** — `Data/lora/{train,valid,test}.jsonl`, 1000/100/100 lines, one JSON object per line:
```json
{"text": "table: 1-1000181-1\ncolumns: State/territory, Text/background colour, Format, Current slogan, Current series, Notes\nQ: Tell me what the notes are for South Australia \nA: SELECT Notes FROM 1-1000181-1 WHERE Current slogan = 'SOUTH AUSTRALIA'"}
```
`Data/lora/wikisql.py` is a Python preprocessor (adapted from salesforce/WikiSQL) that downloads `https://raw.githubusercontent.com/salesforce/WikiSQL/master/data.tar.bz2` and emits this format. README notes files can be `jsonl` **or** `txt`, one entry per line.

### 7.2 `LoRATrainingExample` (macOS app)

`Applications/LoRATrainingExample/ContentView.swift`. Model: `LLMRegistry.mistral7B4bit`. Constants:
```swift
    private let loraLayers = 4
    private let learningRate: Float = 1e-5
    private let parameters = LoRATrain.Parameters(batchSize: 1, iterations: 200)
    private let generateParameters = GenerateParameters(temperature: 0.6, topP: 0.9)
    private let evaluateShowEvery = 8
    private let maxTokens = 200
```

Training entry point:
```swift
    private func startInner() async throws {
        Memory.cacheLimit = 32 * 1024 * 1024
        await MainActor.run { output = ""; state = .training }

        let modelContainer = try await loadModel()

        // apply LoRA adapters and train
        let _ = try await modelContainer.perform { context in
            try LoRAContainer.from(
                model: context.model,
                configuration: LoRAConfiguration(numLayers: loraLayers)
            )
        }

        let train = try loadLoRAData(name: "train")
        let valid = try loadLoRAData(name: "valid")
        ...
        try await modelContainer.perform { context in
            let optimizer = Adam(learningRate: learningRate)
            try LoRATrain.train(
                model: context.model, train: train, validate: valid, optimizer: optimizer,
                tokenizer: context.tokenizer, parameters: parameters
            ) { progress in
                Task { @MainActor in
                    switch progress {
                    case .train(let i, _, _, _):
                        self.progress = .init(title: "Train", current: Double(i), limit: Double(parameters.iterations))
                    case .validation:
                        output += "\n"
                    default: break
                    }
                    output += progress.description + "\n"
                }
                return .more
            }
        }
```
**`LoRATrain.train` progress enum has `.train(Int, _, _, _)` and `.validation` cases and a `.description`; the callback returns `.more` to continue** (presumably `.stop` to abort — **UNVERIFIED**).

Data loaded from the app bundle:
```swift
    private func loadLoRAData(name: String) throws -> [String]? {
        if let url = Bundle.main.url(forResource: name, withExtension: "jsonl") {
            return try MLXLLM.loadLoRAData(url: url)
        }
        return nil
    }
```
(Two overloads exist: `loadLoRAData(directory:name:)` for the CLI, `MLXLLM.loadLoRAData(url:)` for a single file.)

Evaluation (`evaluateInner`) re-seeds and streams:
```swift
        MLXRandom.seed(UInt64(Date.timeIntervalSinceReferenceDate * 1000))
        let modelContainer = try await loadModel()
        let input = try await modelContainer.processor.prepare(input: .init(prompt: prompt))
        var count = 0
        var output = ""
        for try await item in try await modelContainer.generate(input: input, parameters: generateParameters) {
            switch item {
            case .chunk(let string):
                count += 1
                output += string
                if count % evaluateShowEvery == 0 { self.output = output }   // throttle UI updates
            default: break
            }
        }
```
**UI-throttling pattern:** only publish every 8th chunk to avoid SwiftUI churn.

---

## 8. StableDiffusion library + apps

### 8.1 Library public API (`Libraries/StableDiffusion/`)

`Load.swift`:
```swift
public struct LoadConfiguration: Sendable {
    public var float16 = true
    public var quantize = false
    public var dType: DType { float16 ? .float16 : .float32 }
    public init(float16: Bool = true, quantize: Bool = false)
}

public struct EvaluateParameters: Sendable {
    public var cfgWeight: Float
    public var steps: Int
    public var imageCount = 1
    public var decodingBatchSize = 1
    /// size of the latent tensor -- the result image is a factor of 8 larger than this
    public var latentSize = [64, 64]
    public var seed: UInt64
    public var prompt = ""
    public var negativePrompt = ""
    public init(cfgWeight: Float, steps: Int, imageCount: Int = 1, decodingBatchSize: Int = 1,
                latentSize: [Int] = [64, 64], seed: UInt64? = nil, prompt: String = "",
                negativePrompt: String = "")
    // seed defaults to UInt64(Date.timeIntervalSinceReferenceDate * 1000)
}

public struct StableDiffusionConfiguration: Sendable {
    public let id: String
    public let defaultParameters: @Sendable () -> EvaluateParameters
    public func download(hub: HubApi = HubApi(), progressHandler: @escaping (Progress) -> Void = { _ in }) async throws
    public func textToImageGenerator(hub: HubApi = HubApi(), configuration: LoadConfiguration) throws -> TextToImageGenerator?
    public func imageToImageGenerator(hub: HubApi = HubApi(), configuration: LoadConfiguration) throws -> ImageToImageGenerator?
    public enum Preset: String, Codable, CaseIterable, Sendable {
        case base                     // "base"
        case sdxlTurbo = "sdxl-turbo"
        public var configuration: StableDiffusionConfiguration
    }
    public static let presetSDXLTurbo            // stabilityai/sdxl-turbo, cfgWeight: 0, steps: 2
    public static let presetStableDiffusion21Base // stabilityai/stable-diffusion-2-1-base, cfgWeight: 7.5, steps: 50
}
```

Preset file manifests (`Load.swift:151-205`) — SDXL Turbo downloads exactly:
`unet/config.json`, `unet/diffusion_pytorch_model.safetensors`, `text_encoder/config.json`, `text_encoder/model.safetensors`, `text_encoder_2/config.json`, `text_encoder_2/model.safetensors`, `vae/config.json`, `vae/diffusion_pytorch_model.safetensors`, `scheduler/scheduler_config.json`, `tokenizer/vocab.json`, `tokenizer/merges.txt`, `tokenizer_2/vocab.json`, `tokenizer_2/merges.txt`.
SD 2.1 Base omits the `_2` files. Quantization filters in the factory closure:
```swift
            if loadConfiguration.quantize {
                quantize(model: sd.textEncoder,  filter: { k, m in m is Linear })
                quantize(model: sd.textEncoder2, filter: { k, m in m is Linear })
                quantize(model: sd.unet, groupSize: 32, bits: 8)
            }
```

Download uses the *old* `HubApi.snapshot(from:matching:progressHandler:)`:
```swift
    public func download(hub: HubApi = HubApi(), progressHandler: @escaping (Progress) -> Void = { _ in }) async throws {
        let repo = Hub.Repo(id: self.id)
        try await hub.snapshot(from: repo, matching: Array(files.values), progressHandler: progressHandler)
    }
```

`StableDiffusion.swift`:
```swift
public struct DenoiseIterator: Sequence, IteratorProtocol {
    public var underestimatedCount: Int { steps.count }
    mutating public func next() -> MLXArray?
}
public typealias ImageDecoder = (MLXArray) -> MLXArray
public protocol ImageGenerator {
    func ensureLoaded()
    func detachedDecoder() -> ImageDecoder
    func decode(xt: MLXArray) -> MLXArray
}
public protocol TextToImageGenerator: ImageGenerator {
    func generateLatents(parameters: EvaluateParameters) -> DenoiseIterator
}
public protocol ImageToImageGenerator: ImageGenerator {
    func generateLatents(image: MLXArray, parameters: EvaluateParameters, strength: Float) -> DenoiseIterator
}

public actor ModelContainer<M> {                 // NOTE: distinct from MLXLMCommon.ModelContainer
    static public func createTextToImageGenerator(configuration:loadConfiguration:) throws -> ModelContainer<TextToImageGenerator>
    static public func createImageToImageGenerator(configuration:loadConfiguration:) throws -> ModelContainer<ImageToImageGenerator>
    public func setConserveMemory(_ conserveMemory: Bool)
    public func perform<R>(_ action: @Sendable (M) throws -> R) throws -> R
    public func performTwoStage<R1, R2>(first: @Sendable (M) throws -> R1, second: @Sendable (R1) throws -> R2) throws -> R2
}
```
Doc comment on `performTwoStage` (verbatim):
> "If ``setConservativeMemory(_:)`` is `true` this will discard the model in between the `first` and `second` blocks. The container will have to be recreated if a caller wants to use it again. … Callers _must_ eval any `MLXArray` before returning as `MLXArray` is not `Sendable`."

Errors: `ModelContainerError.unableToCreate(String, String)` and `.modelDiscarded` (both `LocalizedError` with localized strings).

`Image.swift` public API:
```swift
public struct Image {
    public let data: MLXArray
    public init(_ data: MLXArray)
    public init(url: URL, maximumEdge: Int? = nil) throws
    public init(image: CGImage, maximumEdge: Int? = nil)
    public func asCGImage() -> CGImage
    public func asCIImage() -> CIImage
    public func save(url: URL) throws
}
```

Weight remapping (diffusers → MLX) is a set of `keyReplace`/`dropPrefix` rules in `Load.swift:211-363` — e.g. `to_k → key_proj`, `to_out.0 → out_proj`, `ff.net.0.proj` **split** into `linear1`/`linear2`, 4-D conv weights `transposed(0,2,3,1)` then `reshaped(-1).reshaped(shape)` to force contiguity, `proj_in`/`proj_out` 1×1 convs `.squeezed()` into Linear. Loading uses `try model.update(parameters: ModuleParameters.unflattened(weights), verify: .none)` with the comment "*not using verifier because some shapes change upon load*".

### 8.2 `StableDiffusionExample` app — the memory-conservation dance

`ContentView.swift:252-332` (verbatim core):

```swift
        do {
            // Note: The optionals are used to discard parts of the model
            // as it runs. This is used to conserve memory in devices
            // with less memory.
            let container = try await modelFactory.load(reportProgress: updateProgress)

            try await container.performTwoStage { generator in
                var parameters = modelFactory.configuration.defaultParameters()
                parameters.prompt = prompt
                parameters.negativePrompt = negativePrompt

                // Per measurement each step consumes memory that we want to conserve. Trade
                // off steps (quality) for memory.
                if modelFactory.conserveMemory { parameters.steps = 1 }

                // Generate the latent images. This is fast as it is just generating
                // the graphs that will be evaluated below.
                let latents: DenoiseIterator? = generator.generateLatents(parameters: parameters)

                // When conserveMemory is true this will discard the first part of
                // the model and just evaluate the decode portion.
                return (generator.detachedDecoder(), latents)

            } second: { decoder, latents in
                var lastXt: MLXArray?
                for (i, xt) in latents!.enumerated() {
                    lastXt = nil
                    eval(xt)
                    lastXt = xt

                    if showProgress, i % 10 == 0 { display(decoded: decoder(xt)) }

                    updateProgress(progress: .init(
                        title: "Generate Latents", current: Double(i), limit: Double(parameters.steps)))
                }
                if let lastXt { display(decoded: decoder(lastXt)) }
                updateProgress(progress: nil)
            }
        } catch {
            progress = nil
            message = "Failed: \(error)"
        }
```
`lastXt = nil` **before** `eval(xt)` is deliberate: dropping the previous array's reference before evaluating the next lets MLX free it.

Rendering an MLXArray to a `CGImage`:
```swift
    nonisolated private func display(decoded: MLXArray) {
        let raster = (decoded * 255).asType(.uint8).squeezed()
        let image = Image(raster).asCGImage()
        Task { @MainActor in updateImage(image: image) }
    }
```

Offline fallback in the loader:
```swift
                } catch {
                    let nserror = error as NSError
                    if nserror.domain == NSURLErrorDomain
                        && nserror.code == NSURLErrorNotConnectedToInternet
                    {
                        // Internet connection appears to be offline -- fall back to loading from
                        // the local directory
                        reportProgress(.init(title: "Offline", current: 100, limit: 100))
                    } else { throw error }
                }
```

Model retention policy:
```swift
            if conserveMemory {
                // if conserving memory return the model but do not keep it in memory
                self.loadState = .idle
            } else {
                // cache the model in memory to make it faster to run with new prompts
                self.loadState = .loaded(container)
            }
```

README troubleshooting (verbatim): "*Stable diffusion can run in less that 4G available memory (typically a device or computer with 6G of memory or more) in a constrained mode -- it will load and unload parts of the model as it runs and it can only perform one step of diffusion. … If the program exits while generating the image it may have exceeded the available memory.*"

### 8.3 `image-tool` CLI

`@main struct ImageTool` → `sd` → `text` | `image`.

`ModelArguments`: `--model <preset>` (default `.sdxlTurbo`; `Preset` made `ExpressibleByArgument` via `@retroactive`), `--float16 / --no-float16` (`inversion: .prefixedNo`, default true), `--quantize` (flag).

`GenerateArguments`:
| Flag | Default |
|---|---|
| `-p/--prompt` | `"purple cow on the moon"` |
| `-n/--negative-prompt` | `""` |
| `--cfg` | Float? |
| `--image-count` | 1 |
| `--batch-size` | 1 (decoding batch size) |
| `--latent-width` | 64 ("output size is 8x this value") |
| `--latent-height` | 64 |
| `--rows` | 1 |
| `--steps` | Int? |
| `--seed` | UInt64? |

`TextToImageCommand`: `--output` (default `/tmp/out.png`). `ImageToImageCommand`: `--input` (required), `--max-edge` (1024), `--output`, `--strength` (0.9).

Core loop (copyable):
```swift
        guard let generator = try configuration.textToImageGenerator(configuration: model.loadConfiguration)
        else { fatalError("Unable to produce TextToImageGenerator from \(configuration.id)") }

        generator.ensureLoaded()
        memory.start()

        let parameters = generate.evaluateParameters(configuration: configuration)
        let latents = generator.generateLatents(parameters: parameters)

        var lastXt: MLXArray!
        for xt in Progress(latents) { eval(xt); lastXt = xt }
        return (parameters, generator.detachedDecoder(), lastXt)
```
then decode in batches and tile:
```swift
func makeGrid(images: [MLXArray], rows: Int) -> MLXArray {
    var x = concatenated(images, axis: 0)
    x = padded(x, widths: [[0, 0], [8, 8], [8, 8], [0, 0]])
    let (B, H, W, C) = x.shape4
    x = x.reshaped(rows, B / rows, H, W, C).transposed(0, 2, 1, 3, 4)
    x = x.reshaped(rows * H, B / rows * W, C)
    x = (x * 255).asType(.uint8)
    return x
}
...
try Image(grid).save(url: output)
```
Image-to-image preprocessing: `let input = (Image(url:maximumEdge:).data.asType(.float32) / 255) * 2 - 1`, plus a step-count floor:
```swift
        if Int(Float(generate.evaluateParameters(configuration: configuration).steps) * strength) < 1 {
            generate.steps = Int(ceil(1 / strength))
        }
```
`Progress(...)` here is **jkandzi/Progress.swift** (terminal progress bar), not Foundation `Progress`. Both are used in this repo — a real naming hazard.

CLI examples from `Tools/image-tool/README.md`:
```sh
./mlx-run image-tool sd text \
    --prompt "an astronaut riding a horse on mars, cinematic" \
    --negative-prompt "low quality, blurry" \
    --steps 4 \
    --output /tmp/out.png

./mlx-run image-tool sd image \
    --input /tmp/in.png \
    --prompt "...same image but in watercolor..." \
    --strength 0.7 \
    --output /tmp/out.png
```

---

## 9. MNIST — training on device

### 9.1 `Libraries/MLXMNIST`

`MNIST.swift` (whole file, verbatim):
```swift
import Foundation
import MLX
import MLXNN

// based on https://github.com/ml-explore/mlx-examples/blob/main/mnist/main.py

public class LeNet: Module, UnaryLayer {

    @ModuleInfo var conv1: Conv2d
    @ModuleInfo var conv2: Conv2d
    @ModuleInfo var pool1: MaxPool2d
    @ModuleInfo var pool2: MaxPool2d
    @ModuleInfo var fc1: Linear
    @ModuleInfo var fc2: Linear
    @ModuleInfo var fc3: Linear

    override public init() {
        conv1 = Conv2d(inputChannels: 1, outputChannels: 6, kernelSize: 5, padding: 2)
        conv2 = Conv2d(inputChannels: 6, outputChannels: 16, kernelSize: 5, padding: 0)
        pool1 = MaxPool2d(kernelSize: 2, stride: 2)
        pool2 = MaxPool2d(kernelSize: 2, stride: 2)
        fc1 = Linear(16 * 5 * 5, 120)
        fc2 = Linear(120, 84)
        fc3 = Linear(84, 10)
    }

    public func callAsFunction(_ x: MLXArray) -> MLXArray {
        var x = x
        x = pool1(tanh(conv1(x)))
        x = pool2(tanh(conv2(x)))
        x = flattened(x, start: 1)
        x = tanh(fc1(x))
        x = tanh(fc2(x))
        x = fc3(x)
        return x
    }
}

public func loss(model: LeNet, x: MLXArray, y: MLXArray) -> MLXArray {
    crossEntropy(logits: model(x), targets: y, reduction: .mean)
}

public func eval(model: LeNet, x: MLXArray, y: MLXArray) -> MLXArray {
    mean(argMax(model(x), axis: 1) .== y)
}

public func iterateBatches(
    batchSize: Int, x: MLXArray, y: MLXArray, using generator: inout any RandomNumberGenerator
) -> some Sequence<(MLXArray, MLXArray)>
```
(`BatchSequence` shuffles `Array(0..<y.size).shuffled(using: &generator)` into an `MLXArray` of indices, then fancy-indexes `x[ids], y[ids]`.)

`Files.swift` public API: `enum Use { test, training }`, `enum DataKind { images, labels }`, `struct FileKind(Use, DataKind)`, `public func download(into: URL) async throws`, `public func load(from: URL) throws -> [FileKind: MLXArray]`.
- Base URL: `https://raw.githubusercontent.com/fgnt/mnist/master/`
- Files: `train-images-idx3-ubyte.gz` (offset 16), `t10k-images-idx3-ubyte.gz` (16), `train-labels-idx1-ubyte.gz` (8), `t10k-labels-idx1-ubyte.gz` (8)
- Images → `.reshaped([-1, 28, 28, 1]).asType(.float32) / 255.0`; labels → `.asType(.uint32)`
- Decompression via **GzipSwift** `Data.gunzipped()`
- Raw bytes → `MLXArray(data.dropFirst(offset), [count - offset], type: UInt8.self)`

### 9.2 `mnist-tool` CLI

```
--data <dir>              (required) "Directory with the training data"
--seed <UInt64>           default 0
--batch-size <Int>        default 256
--epochs <Int>            default 20
--learning-rate <Float>   default 1e-1
--device <gpu|cpu>        default .gpu   (DeviceType made ExpressibleByArgument)
--compile                 Flag
```

```swift
    func run() async throws {
        try await Device.withDefaultDevice(Device(device)) { try await runWithDevice() }
    }
```

Training core (the canonical MLX Swift training loop):
```swift
        let model = LeNet()
        eval(model.parameters())

        let lg = valueAndGrad(model: model, loss)
        let optimizer = SGD(learningRate: learningRate)

        func step(_ x: MLXArray, _ y: MLXArray) -> MLXArray {
            let (loss, grads) = lg(model, x, y)
            optimizer.update(model: model, gradients: grads)
            return loss
        }

        let resolvedStep =
            compile
            ? MLX.compile(inputs: [model, optimizer], outputs: [model, optimizer], step) : step

        for e in 0 ..< epochs {
            for (x, y) in iterateBatches(batchSize: batchSize, x: trainImages, y: trainLabels, using: &generator) {
                _ = resolvedStep(x, y)
                // eval the parameters so the next iteration is independent
                eval(model, optimizer)
            }
            let accuracy = eval(model: model, x: testImages, y: testLabels)
            print("Epoch \(e): test accuracy \(accuracy.item(Float.self).formatted())\nTime: \((end - start).formatted())\n")
        }
```
**`MLX.compile(inputs:outputs:_:)` with `[model, optimizer]` as both inputs and outputs is the documented way to compile a step function that mutates module state.**

### 9.3 `MNISTTrainer` app

`ContentView.swift` wraps the same loop in `actor LeNetContainer`, reports epochs to an `@MainActor @Observable class ModelState`:
```swift
@MainActor @Observable
class ModelState {
    enum State { case untrained, trained(LeNetContainer), predict(LeNetContainer) }
    var state: State = .untrained
    var messages = [String]()
    func train() async throws {
        let model = LeNetContainer()
        try await model.train(output: self)
        self.state = .trained(model)
    }
}

actor LeNetContainer {
    private let model = LeNet()
    let mnistImageSize: CGSize = CGSize(width: 28, height: 28)

    func train(output: ModelState) async throws {
        let url = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        try await download(into: url)
        let data = try load(from: url)
        let trainImages = data[.init(.training, .images)]!
        ...
        MLXRandom.seed(0)
        var generator: RandomNumberGenerator = SplitMix64(seed: 0)
        for e in 0 ..< 10 { ... await MainActor.run { output.messages.append(...) } }
    }

    func evaluate(image: CGImage) -> Int? {
        let pixelData = image.grayscaleImage(with: mnistImageSize)?.pixelData()
        if let pixelData {
            let x = pixelData.reshaped([1, 28, 28, 1]).asType(.float32) / 255.0
            return argMax(model(x)).item()
        } else { return nil }
    }
}
```
`SplitMix64(seed:)` comes from `Libraries/MLXMNIST/Random.swift`.

`PredictionView.swift` — draw-a-digit canvas: a `Path` + `DragGesture(minimumDistance: 0.05)`, centered via `path.center(to:)`, rasterized with `ImageRenderer(content:).cgImage`, converted to grayscale 28×28 through `CGContext(colorSpace: CGColorSpaceCreateDeviceGray(), bitsPerComponent: 8, bytesPerRow: width, bitmapInfo: CGImageAlphaInfo.none)`, then:
```swift
    func pixelData() -> MLXArray {
        guard let data = self.dataProvider?.data else { return [] }
        let bytePtr = CFDataGetBytePtr(data)
        let count = CFDataGetLength(data)
        return MLXArray(UnsafeBufferPointer(start: bytePtr, count: count))
    }
```
**`MLXArray(UnsafeBufferPointer)` is the zero-ceremony bytes→array constructor.**

---

## 10. `Numerical/` — the WWDC26 examples (commit `70eaaca`, 2026-06-09)

3010 insertions across 38 files. README.md:38-54 (verbatim):

```
## Numerical Computing

Examples that use MLX for general numerical computing (no ML model involved),
useful for seeing how MLX array idioms, `compile`, and custom Metal kernels
apply to classic numerical problems.

- [CurveFit](Numerical/CurveFit/README.md): Live visualization of gradient
  descent fitting a quadratic to noisy samples, using `MLX.grad` for
  automatic differentiation.

- [HeatTransfer](Numerical/HeatTransfer/README.md): 2D heat-diffusion
  simulation comparing three Jacobi/SOR stencil implementations
  (`conv2d`, compiled `roll`, red/black SOR).

- [Mandelbrot](Numerical/Mandelbrot/README.md): Mandelbrot set renderer
  comparing plain MLX, compiled MLX, and a custom Metal kernel
  (`MLXFast.metalKernel`) against a reference CPU implementation.
```

These three apps link **only `MLX`** and require **iOS/macOS 26.5**.

### 10.1 Mandelbrot — plain MLX vs `compile` vs custom Metal kernel

Performance claims quoted from `Numerical/Mandelbrot/README.md`:
| Implementation | Notes |
|---|---|
| Plain MLX | "uses `complex64` and `linspace` to build `c`" |
| Compiled MLX | "Operations fuse; **~3–4× faster** than plain MLX on the inner loop." |
| Metal kernel | "Counts live in a local variable (no per-iteration writes) and pixels can early-exit. **~10× faster** than the compiled MLX version." |
| Reference CPU | plain Swift + swift-numerics `Complex` |

Plain MLX (`Algorithm/Mandelbrot+MLX.swift:20-40`):
```swift
public func computeMandelbrotMLX(configuration: Configuration) -> MLXArray {
    let x = linspace(configuration.xMin, configuration.xMax, count: w)
    let y = linspace(configuration.yMin, configuration.yMax, count: h).reshaped(h, 1)

    let c = (x + y.asImaginary())
    var z = zeros(c.shape, dtype: .complex64)
    var counts = zeros(c.shape, dtype: .int16)

    for _ in 0 ..< maxIterations {
        z = z * z + c
        let mask = abs(z) .< radius
        counts = counts + mask
    }
    return counts
}
```
Note **`y.asImaginary()`** and **`dtype: .complex64`**.

Compiled variant:
```swift
    func step(z: MLXArray, c: MLXArray, counts: MLXArray) -> (MLXArray, MLXArray) {
        let z = z * z + c
        let mask = abs(z) .< radius
        let counts = counts + mask
        return (z, counts)
    }
    let compiledStep = compile(step)

    for _ in 0 ..< maxIterations {
        (z, counts) = compiledStep(z, c, counts)
    }
```
Doc comment (verbatim): "*Is compilation worth it? In this case probably yes -- the operations are all elementwise and the intermediate arrays can be elided. For a slight loss in readability you might see 3-4x performance gain (on my laptop, for this particular algorithm). Hot inner loops with elementwise operations are good candidates.*"

**Custom Metal kernel — `MLXFast.metalKernel` (the whole verified signature and usage):**
```swift
private let mandelbrotKernel = MLXFast.metalKernel(
    name: "mandelbrot",
    inputNames: ["params"],
    outputNames: ["out"],
    source: """
        uint elem = thread_position_in_grid.x;
        int width = int(params[0]);
        int height = int(params[1]);
        int maxIterations = int(params[2]);
        float xMin = params[3];
        float yMin = params[4];
        float xStep = params[5];
        float yStep = params[6];
        float radiusSquared = params[7];

        if (elem >= uint(width * height)) return;

        int px = int(elem) % width;
        int py = int(elem) / width;

        float cReal = xMin + float(px) * xStep;
        float cImag = yMin + float(py) * yStep;

        float zReal = 0.0f;
        float zImag = 0.0f;
        int count = maxIterations;
        for (int i = 0; i < maxIterations; i++) {
            float zRealNew = zReal * zReal - zImag * zImag + cReal;
            zImag = 2.0f * zReal * zImag + cImag;
            zReal = zRealNew;
            if (zReal * zReal + zImag * zImag > radiusSquared) {
                count = i;
                break;
            }
        }
        out[elem] = short(count);
        """
)

public func computeMandelbrotMetal(configuration: Configuration) -> MLXArray {
    let params = MLXArray([
        Float(w), Float(h), Float(configuration.maxIterations),
        configuration.xMin, configuration.yMin,
        configuration.xStep, configuration.yStep,
        configuration.escapeRadiusSquared,
    ])

    let total = w * h
    let threadGroupSize = 256

    return mandelbrotKernel(
        [params],
        grid: (total, 1, 1),
        threadGroup: (threadGroupSize, 1, 1),
        outputShapes: [[h, w]],
        outputDTypes: [.int16]
    )[0]
}
```
- Kernel body is **just the body** — MLX generates the signature from `inputNames`/`outputNames`.
- Metal builtins like `thread_position_in_grid` are available directly.
- Call form: `kernel(inputs, grid:threadGroup:outputShapes:outputDTypes:) -> [MLXArray]`.
- Output dtype `.int16` maps to Metal `short`.

SIMD caveat (verbatim doc comment): "*A note on early exit: threads run in SIMD groups, so a pixel that escapes quickly still waits for the slowest pixel in its group before the group can retire. When escape dominates a region you can observe roughly a 2x speedup from the early exit, but the effect is harder to reason about than the per-pixel early exit on the CPU.*"

### 10.2 Zero-copy MLXArray → IOSurface → CALayer display

`Numerical/Mandelbrot/Utilities/MLX+IOSurface.swift` (whole file, duplicated in HeatTransfer):

```swift
import CoreVideo
import Foundation
import IOSurface
import MLX

public func applyLUT(_ input: MLXArray, lut: MLXArray, max: Float, maxValue: UInt32) -> MLXArray {
    precondition(lut.ndim == 1)
    let lutCount = lut.dim(0)

    // LUT is BGRA and we want to interpolate per channel
    let lut = lut.view(dtype: .uint8)
        .reshaped([lutCount, 4])
        .asType(.float32)

    // interpolate 0 ... max -> lut indexes
    let scale = (Float(lutCount) - 1) / max
    let index = input.asType(.float32) * scale

    let lutIndexLow = floor(index).asType(.int16)
    let lutIndexHigh = minimum(lutIndexLow + 1, lutCount - 1)

    // compute the fraction between the lut values.
    // add .newAxis so that it will broadcast for the channels
    let fraction = (index - lutIndexLow)[.ellipsis, .newAxis]

    let colorLow = lut.take(lutIndexLow, axis: 0)
    let colorHigh = lut.take(lutIndexHigh, axis: 0)

    // the produces [H, W, 4]
    let maxValue = MLXArray([maxValue]).view(dtype: .uint8)
    let result = which(
        input[.ellipsis, .newAxis] .>= max, maxValue, colorLow + fraction * (colorHigh - colorLow))
    return round(result).asType(.uint8)
}

public func createIOSurface(bgra: MLXArray) -> IOSurface {
    precondition(bgra.ndim == 3)
    precondition(bgra.dim(2) == 4)
    precondition(bgra.dtype == .uint8)

    // Zero-copy access to MLX backing data
    let arrayData = bgra.asData(access: .noCopyIfContiguous)

    let w = bgra.dim(1)
    let h = bgra.dim(0)

    // Create IOSurface and memcpy
    let bytesPerRow = w * 4
    let surface = IOSurface(properties: [
        .width: w,
        .height: h,
        .bytesPerElement: 4,
        .bytesPerRow: bytesPerRow,
        .pixelFormat: kCVPixelFormatType_32BGRA,
    ])!

    surface.lock(options: [], seed: nil as UnsafeMutablePointer<UInt32>?)
    _ = arrayData.data.withUnsafeBytes { src in
        memcpy(surface.baseAddress, src.baseAddress!, h * bytesPerRow)
    }
    surface.unlock(options: [], seed: nil as UnsafeMutablePointer<UInt32>?)

    return surface
}
```
**Key MLX APIs here:** `MLXArray.view(dtype:)` (reinterpret bytes — used to split `UInt32` BGRA into 4×`UInt8`), `MLXArray.asData(access: .noCopyIfContiguous)` returning something with `.data: Data`, `.take(_:axis:)`, indexing with `[.ellipsis, .newAxis]`, `which(cond, a, b)`, `round(_:)`.

Display without SwiftUI `Image`: `Utilities/ImageView.swift` wraps a bare `UIView`/`NSView` and assigns the `IOSurface` to `layer.contents` inside a `CATransaction` with `setDisableActions(true)`:
```swift
#if os(iOS)
    public struct ImageView: UIViewRepresentable {
        public let image: Any
        public var gravity = CALayerContentsGravity.resizeAspect
        public func makeUIView(context: Context) -> UIView {
            let view = UIView()
            view.layer.contentsGravity = gravity
            view.autoresizingMask = [.width, .height]
            return view
        }
        public func updateUIView(_ uiView: UIView, context: Context) {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            uiView.layer.contents = image
            CATransaction.commit()
        }
    }
#else /* NSViewRepresentable variant */ #endif
```

### 10.3 Renderer pattern (both Mandelbrot and HeatTransfer)

```swift
@MainActor @Observable
class Renderer {
    public var image: IOSurface?
    public var kind: RendererKind = .mlxCompiled { didSet { /* reset timing stats */ } }
    private var renderTask: Task<Void, Never>?

    @ObservationIgnored private var recentTimes: [TimeInterval] = []
    private let recentTimesCapacity = 30
    @ObservationIgnored private var lastDisplayUpdate: CFTimeInterval = 0
    private let displayUpdateInterval: CFTimeInterval = 0.5
    public private(set) var averageFrameTime: TimeInterval?
    public var averageFPS: Double? { guard let t = averageFrameTime, t > 0 else { return nil }; return 1.0 / t }

    public func render() {
        renderTask = Task.detached { [self, configuration, kind] in
            let start = Date.timeIntervalSinceReferenceDate
            let result: IOSurface = ...
            let end = Date.timeIntervalSinceReferenceDate
            await MainActor.run {
                self.image = result
                self.recordFrameTime(end - start)
                self.renderTask = nil
            }
        }
    }

    public func startAnimation() {
        animationTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 60.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.tick() }
        }
    }
    public func tick() { guard renderTask == nil else { return } /* drop frames if busy */ ... }
}
```
Patterns worth guiding on: `@ObservationIgnored` for hot mutable stats; `Task.detached` for GPU work with an explicit `await MainActor.run` handoff; frame-drop guard `guard renderTask == nil`; smoothing window of 30 samples published at most every 0.5 s.

### 10.4 HeatTransfer — three stencil formulations

`Numerical/HeatTransfer/Algorithm/Jacobi+MLX.swift`:

`conv2d` version:
```swift
public func computeJacobiConv2d(state: inout Room, count: Int) {
    // [1, H, W, 1] -- match what conv2d needs
    var temperature = state.temperature[.newAxis, .ellipsis, .newAxis]
    let staticMask   = state.staticMask[.newAxis, .ellipsis, .newAxis]
    let heatSources  = state.heatSources[.newAxis, .ellipsis, .newAxis]

    let kernel = MLXArray(converting: [
        0, 0.25, 0,
        0.25, 0, 0.25,
        0, 0.25, 0,
    ]).reshaped(1, 3, 3, 1)

    for _ in 0 ..< count {
        let next = conv2d(temperature, kernel, padding: 1)
        temperature = which(staticMask, heatSources, next)
    }
    state.temperature = temperature.squeezed()
}
```

`roll` + `compile` version — README claims "**~2–3× faster** than `conv2d` on a laptop":
```swift
public func computeJacobiStencil(state: inout Room, count: Int) {
    @Sendable
    func step(_ temperature: MLXArray, _ staticMask: MLXArray, _ heatSources: MLXArray) -> MLXArray {
        let next =
            0.25
            * (roll(temperature, shift: -1, axis: 0)
                + roll(temperature, shift: 1, axis: 0)
                + roll(temperature, shift: -1, axis: 1)
                + roll(temperature, shift: 1, axis: 1))
        return which(staticMask, heatSources, next)
    }
    let compiledStep = compile(step)
    for _ in 0 ..< count {
        state.temperature = compiledStep(state.temperature, state.staticMask, state.heatSources)
    }
}
```
Doc comment enumerates the three shifting options: `roll()` (works because there are walls on the border), plain slicing (`temperature[1..., 0...]` — loses an edge), and `padded()` + slicing.

Red/black SOR:
```swift
    let ω: Float = 2.0 / (1.0 + sin(Float.pi / Float(max(M, N))))
    let redMask   = checkerboard(rows: M, cols: N, phase: 0)
    let blackMask = checkerboard(rows: M, cols: N, phase: 1)

    for _ in 0 ..< count {
        let sorRed = ω * conv2d(temperature, kernel, padding: 1) + (1 - ω) * temperature
        temperature = which(redMask, sorRed, temperature)
        temperature = which(heatMask, heatSources, temperature)

        let sorBlack = ω * conv2d(temperature, kernel, padding: 1) + (1 - ω) * temperature
        temperature = which(blackMask, sorBlack, temperature)
        temperature = which(heatMask, heatSources, temperature)
    }
```
with
```swift
func checkerboard(rows: Int, cols: Int, phase: Int) -> MLXArray {
    let rows = arange(0, rows)[.ellipsis, .newAxis]
    let cols = arange(0, cols)[.newAxis, .ellipsis]
    return (((rows + cols) % 2) .== phase)[.newAxis, .ellipsis, .newAxis]
}
```
Doc comment: "*Jacobi iterations takes O(n^2) … iterations to converge. Successive over-relaxation (SOR) converges in O(n) when an optimal ω is used. This is like switching bubble sort for quicksort.*" and "*SOR (1 iter/frame) runs ~10x slower per iteration than SOR Full Speed (200 iter/frame) — dispatch and sync overhead dominate at small batch sizes.*"

**Benchmarking gotcha, stated in the README and enforced in `Renderer.render()`:**
> "Note: the timing window calls `eval(room.temperature)` to force GPU sync — without it, MLX's lazy evaluation would defer the work past the timer."
```swift
            // important: evaluate the result, otherwise
            // the time for the computation lands below when
            // we produce an image from it.
            kind.apply(room: &room)
            eval(room.temperature)
```

Room construction (`HeatTransfer/Algorithm/Configuration.swift:116-148`) is a nice broadcasting/masking showcase:
```swift
        let rows = arange(0, height)[.ellipsis, .newAxis]
        let cols = arange(0, width)[.newAxis, .ellipsis]

        var wallMask =
            ((rows .== 0) .|| (rows .== (height - 1)) .|| (cols .== 0) .|| (cols .== (width - 1)))
        for wall in walls {
            wallMask = wallMask
                .|| ((rows .>= wall.minY) .&& (rows .< wall.maxY) .&& (cols .>= wall.minX) .&& (cols .< wall.maxX))
        }
        var heatSources = zeros([height, width])
        for heatSource in self.heatSources {
            let dx = cols - heatSource.x
            let dy = rows - heatSource.y
            let mask = (dx * dx + dy * dy) .< (heatSource.radius * heatSource.radius)
            heatSources = which(mask, heatSource.temperature, heatSources)
        }
        let staticMask = wallMask .|| (heatSources .> 0)
```
Default grid: 1280×1024, `initialTemperature = zeros([height, width], dtype: .float16)`.
Element-wise operators confirmed: `.==`, `.<`, `.>=`, `.>`, `.||`, `.&&`, `.!=`.

Wall overlay at display time:
```swift
            let wallColor = full(room.temperature.shape, values: UInt32(0xff80_8080))
                .view(dtype: .uint8)
                .reshaped(room.temperature.shape + [-1])
            var raster = applyLUT(room.temperature, lut: MLXArray(lut), max: 1.0, maxValue: 0xffff_ffff)
            raster = which(room.wallMask.expandedDimensions(axis: -1), wallColor, raster)
```

### 10.5 CurveFit — `grad` in 50 lines

`Numerical/CurveFit/Algorithm/Gradient.swift` (whole file):
```swift
import Foundation
import MLX

/// Quadratic model `θ₀ + θ₁·x + θ₂·x²` — the function we are fitting.
func model(_ θ: MLXArray, _ x: MLXArray) -> MLXArray {
    θ[0] + θ[1] * x + θ[2] * x * x
}

/// The target function we are trying to recover. The model is intentionally
/// under-parameterized (quadratic vs. cubic) so the fit is imperfect.
func target(_ x: MLXArray) -> MLXArray {
    3 + x * 0.5 + 3 * x * x - x * x * x
}

struct Gradient {
    let numParams = 3
    let totalSteps = 50
    let learningRate: Float = 0.005

    let x: MLXArray
    let y: MLXArray
    var θ: MLXArray

    private let gradLoss: (MLXArray) -> MLXArray

    init() {
        let x = MLX.linspace(Float(-2.0), Float(2.0), count: 40)
        // target function + noise
        let y = target(x) + MLXRandom.uniform(Float(-1) ..< Float(1), x.shape)
        self.x = x
        self.y = y
        self.θ = zeros([numParams])

        func loss(_ θ: MLXArray) -> MLXArray {
            mean((model(θ, x) - y) ** 2)
        }
        self.gradLoss = grad(loss)
    }

    mutating func step() {
        let g = gradLoss(θ)          // ∇L(θ)
        θ = θ - learningRate * g     // parameter update
        eval(θ)
    }
}
```
UI uses **Swift Charts** (`import Charts`) with `LineMark` + `.chartForegroundStyleScale(["Actual": .blue, "Predicted": .orange])`, `.chartXScale(domain: -2 ... 2)`, `.chartYScale(domain: -5 ... 15)`, and pulls values back to Swift with `gradient.x.asArray(Float.self)`. Steps are paced with `try? await Task.sleep(for: .milliseconds(200))`.

---

## 11. `Tools/Tutorial` and `Tools/LinearModelTraining`

`Tools/Tutorial/Tutorial.swift` — port of `mlx/examples/cpp/tutorial.cpp`, teaching:
```swift
        let x = MLXArray(1.0)
        assert(x.dtype == .float32)
        let s = x.item(Float.self)
        // reading the value with a different type is a fatal error
        // let i = x.item(Int.self)
        assert(x.size == 1); assert(x.ndim == 0); assert(x.shape == [])

        // Note: the argument is a [Double] array literal, which is not
        // a supported type, but we can explicitly convert it to [Float]
        let x = MLXArray(converting: [1.0, 2.0, 3.0, 4.0], [2, 2])
        let y = MLXArray.ones([2, 2])
        let z = x + y
        // mlx is lazy by default. At this point `z` only has a shape and a type but no actual data
        z.eval()

        let gradFn = grad(fn)
        assert(gradFn(MLXArray(1.5)).item() == Float(2 * 1.5))
        let df2dx2 = grad(grad(fn))(x)   // second derivative
```
Lazy-eval doc comment (verbatim): "*Under the hood, mlx records operations in a graph. The variable `z` is a node in the graph which points to its operation and inputs. When `eval` is called on an array (or arrays), the array and all of its dependencies are recursively evaluated to produce the result. Once an array is evaluated, it has data and is detached from its inputs.*"

`Tools/LinearModelTraining` — `y = mx + b`. Flags: `--epochs 20`, `--batch-size 8`, `--m 0.25`, `--b 7`, `--compile`, `--device cpu` (default **cpu** here, unlike mnist-tool). Model declared *inside* the function:
```swift
        class LinearFunctionModel: Module, UnaryLayer {
            let m = MLXRandom.uniform(low: -5.0, high: 5.0)
            let b = MLXRandom.uniform(low: -5.0, high: 5.0)
            func callAsFunction(_ x: MLXArray) -> MLXArray { m * x + b }
        }
        func loss(model: LinearFunctionModel, x: MLXArray, y: MLXArray) -> MLXArray {
            mseLoss(predictions: model(x), targets: y, reduction: .mean)
        }
```
Comment worth quoting: "*Note: A very large batch size will take longer to converge because the gradient will be representing too many samples down into a single float parameter.*"

---

## 12. `embedder-tool` (added `f156eda`, 2025-10-29)

`@main struct EmbedderTool` with subcommands `index`, `search`, `repl`, `list`, `demo`. Default model: `EmbedderRegistry.nomic_text_v1_5` (`nomic-ai/nomic-embed-text-v1.5`).

**`EmbedderCommand` protocol** — reusable boilerplate eliminator:
```swift
protocol EmbedderCommand: AsyncParsableCommand {
    var model: ModelArguments { get }
    var pooling: PoolingArguments { get }
    var memory: MemoryArguments { get set }
    mutating func run(runtime: EmbedderRuntime) async throws
}

extension EmbedderCommand {
    mutating func run() async throws {
        var memory = self.memory
        let capturedModel = model
        let capturedPooling = pooling
        let runtime = try await memory.start {
            try await EmbedderTool.loadRuntime(model: capturedModel, pooling: capturedPooling)
        }
        defer { memory.reportMemoryStatistics(); self.memory = memory }
        try await run(runtime: runtime)
    }
}
```

Loading:
```swift
        let hub = #hubDownloader
        let loader = #huggingFaceTokenizerLoader
        let container = try await EmbedderModelFactory.shared.loadContainer(
            from: hub, using: loader, configuration: configuration,
            progressHandler: { progress in ... })
```
(Note the **bare macro references without parentheses** here — both forms compile.)

Flags:
- `ModelArguments`: `--model`, `--download`
- `PoolingArguments`: `--strategy <mean|cls|first|last|max|none>`, `--normalize / --no-normalize` (default true), `--layer-norm` (flag)
- `CorpusArguments`: `-d/--directory` (default cwd), `-e/--extensions` (default `["txt","md"]`, `.upToNextOption`), `-r/--recursive`, `--limit`
- `index`: `-o/--output <URL>` (required), `--batch-size 8`
- `search`: `-i/--index <URL>`, `-q/--query <String>`, `-t/--top 5`
- `demo`: `--keep-index`, positional queries

`Pooling.Strategy` retroactively conformed:
```swift
extension Pooling.Strategy: @retroactive CaseIterable {
    public static var allCases: [Pooling.Strategy] { [.mean, .cls, .first, .last, .max, .none] }
}
extension Pooling.Strategy: @retroactive ExpressibleByArgument { … }
```

Embedding core (`EmbedderRuntime+Embedding.swift`) — **the padToken fallback from commit `44b14cf`**:
```swift
        return try await container.perform { context in
            let tokenizer = context.tokenizer
            let encoded = texts.enumerated().compactMap { index, text -> (Int, [Int])? in
                let tokens = tokenizer.encode(text: text, addSpecialTokens: true)
                guard !tokens.isEmpty else { skippedIndices.append(index); return nil }
                return (index, tokens)
            }

            // [PAD] (BERT standard), EOS (autoregressive like Qwen)
            let padToken = tokenizer.convertTokenToId("[PAD]") ?? tokenizer.eosTokenId ?? 0

            let maxLength = encoded.map { $0.1.count }.max() ?? 0
            let padded = stacked(encoded.map { _, tokens in
                MLXArray(tokens + Array(repeating: padToken, count: maxLength - tokens.count))
            })
            let mask = (padded .!= padToken)
            let tokenTypes = MLXArray.zeros(like: padded)

            let outputs = context.model(
                padded, positionIds: nil, tokenTypeIds: tokenTypes, attentionMask: mask)

            let poolingModule = resolvedPooler(for: context.pooling)
            let pooled = poolingModule(outputs, mask: mask, normalize: self.normalize, applyLayerNorm: self.applyLayerNorm)
            pooled.eval()
            ...
        }
```
**Embedding model call signature:** `context.model(_ tokens: MLXArray, positionIds:tokenTypeIds:attentionMask:)`. `context.pooling` exists on the embedder `ModelContext`. `EmbedderModelContainer.poolingStrategy` is an async property.

Index format is JSON `[IndexEntry]` (`{path, embedding}`) written with `[.prettyPrinted, .sortedKeys]`. Vectors are sanitized (NaN/Inf → 0) via `VectorOperations.sanitize/normalize/dotProduct/hasNonFiniteValues`. README warns to use the same `--no-normalize` for `index` and `search`.

**Broken doc link:** `Tools/embedder-tool/README.md:5` points at `../../Libraries/Embedders/README.md`, which no longer exists (moved to mlx-swift-lm).

---

## 13. Recent commit archaeology (`git log --oneline -50` + selective `git show`)

Dated log (most recent first):

| SHA | Date | Subject |
|---|---|---|
| `378f244` | 2026-06-16 | MLXChatExample: fix VLM image handling on iOS (PhotosPicker, EXIF, empty assistant trim) (#472) |
| `12fb46a` | 2026-06-16 | MLXChatExample: register Gemma 4 (E2B / E4B) VLMs (#473) |
| `552c6c9` | 2026-06-15 | docs(mnist-tool): fix link to renamed MLXMNIST README (#485) |
| `85a9d85` | 2026-06-16 | use more succint `#huggingFaceLoadModelContainer` macro in example codes (#487) |
| `0c4b2d1` | 2026-06-09 | docs(image-tool): add missing README (#481) |
| `70eaaca` | 2026-06-09 | **new files -- WWDC26 numerical computing examples (#480)** |
| `357c97f` | 2026-04-16 | **mlx-swift-examples prep for mlx-swift-lm 3.x release (#468)** |
| `c684488` | 2026-01-22 | add a minimal LLM chat example + switch to mlx-swift 0.30.2 (#454) |
| `44b14cf` | 2026-01-14 | fallback for finding padToken (#461) |
| `c1198e2` | 2026-01-14 | improve handling of portrait display on iOS (#459) |
| `fc3afc7` | 2025-12-11 | Update LLMEval example (#452) |
| `7e2e757` | 2025-12-02 | switch to github actions (#446) |
| `0db7c5d` | 2025-11-11 | **split out mlx-swift-lm (#441)** |
| `b071763` | 2025-11-04 | re-port sanitize, fix #431 (#432) |
| `fa76d9a` | 2025-11-04 | add `additionalContext` in streamlined API, fix #413 (#433) |
| `5651f0b` | 2025-11-04 | Add `prefillStepSize` to `GenerateParameters` init (#439) |
| `f156eda` | 2025-10-29 | Add embedder-tool CLI for document indexing and semantic search (#408) |
| `881ad5a` | 2025-10-29 | Add support LoRA layer keys from adapter config (#424) |
| `d1e6f55` | 2025-10-27 | Qwen3VL supports tool calling (#421) |
| `4c70e78` | 2025-10-28 | FastVLM (#423) |
| `e82141e` | 2025-10-24 | Download subfolder configs apart HuggingFace Snapshot (#428) |
| `eb76c5b` | 2025-10-22 | Fix Catalyst Build with Swift Transformer 1.1.0 (#420) |
| `9bff95c` | 2025-10-16 | mlx-swift 0.29.1 (#411) |
| `a7c99ec`, `b12ef41`, `95cc51f`, `6e987d8`, `f913e4c`, `d339a82`, `a920c21`, `98f28c1`, `8775112` | 2025-10 | model ports (Qwen3 VL, nanochat, LFM2MoE, granite hybrid moe, Falcon H1, bailing moe, OlmoE, lille-130m, LFM2 2.6B) — all now live in mlx-swift-lm |

### 13.1 The 3.x API migration diff (from `357c97f`) — **essential for a migration guide**

```diff
-import Hub
+import HuggingFace
 import MLX
+import MLXHuggingFace

-    func load(defaultModel: String, modelFactory: ModelFactory) async throws -> ModelContainer {
+    func load(defaultModel: String, modelFactory: any ModelFactory) async throws -> ModelContainer {
...
-        let hub =
-            if let download { HubApi(downloadBase: download) } else { HubApi() }
-        return try await modelFactory.loadContainer(hub: hub, configuration: modelConfiguration)
+        return try await modelFactory.loadContainer(
+            from: self.downloader,
+            using: #huggingFaceTokenizerLoader(),
+            configuration: modelConfiguration)
```
and in MLXService:
```diff
             let container = try await factory.loadContainer(
-                hub: .default, configuration: model.configuration
+                from: downloader,
+                using: loader,
+                configuration: model.configuration
             ) { progress in
```
Package bumps in the same commit: mlx-swift `0.30.3 → 0.31.3` (`.upToNextMinor`), swift-transformers `.upToNextMinor(from: "1.1.0") → .upToNextMajor(from: "1.3.0")`, plus `-skipMacroValidation` everywhere and `embedder-tool` added to CI.

**Migration checklist derived from this diff:**
1. `import Hub` → `import HuggingFace`; add `import MLXHuggingFace`.
2. `ModelFactory` → `any ModelFactory` (existential).
3. `loadContainer(hub:configuration:)` → `loadContainer(from: Downloader, using: TokenizerLoader, configuration:)`.
4. `HubApi(downloadBase:)` → `HubClient(cache: HubCache(cacheDirectory:))` + `#hubDownloader(client)`.
5. Add `-skipMacroValidation` to `xcodebuild`.
6. `case .toolCall:` → `case .toolCall(let toolCall):` if you want to handle tools.

---

## 14. Cross-cutting Swift/SwiftUI patterns catalogue (copyable)

| Pattern | Where | One-liner |
|---|---|---|
| Idempotent async load with a stored `Task` | `LLMBasic/ChatModel.swift`, `SDExample/ContentView.swift`, `LoRAEvaluator` | `case .loading(Task<T, Error>)` → concurrent callers `await task.value` |
| Poll-and-retry load guard | `LLMEvaluator.load()` | `while true { switch loadState { case .loading: try await Task.sleep(for: .milliseconds(100)) … } }` |
| Model cache | `MLXService` | `NSCache<NSString, ModelContainer>` |
| Streaming into `@Observable` | all chat apps | `for try await chunk in stream { message.content += chunk }` on `@MainActor` |
| Throttled UI updates | `LoRAEvaluator.evaluateInner` | `if count % evaluateShowEvery == 0 { self.output = output }` |
| Cancellation | `ChatViewModel.generate()` | `withTaskCancellationHandler { try await generateTask?.value } onCancel: { … "\n[Cancelled]" }` |
| Cancel on disappear | `LLMBasic/ContentView` | `.onDisappear { session?.cancel() }` |
| Auto-scroll while streaming | `ConversationView` / `LLMBasic` / `OutputView` | `.defaultScrollAnchor(.bottom, for: .sizeChanges)` or `ScrollViewReader` + `.onChange(of: output) { sp.scrollTo("bottom") }` |
| Markdown for free | `MessageView` | `Text(LocalizedStringKey(message.content))` |
| Adaptive iPhone layout | `HeaderView`, `MetricsView` | `@Environment(\.horizontalSizeClass)` + `DisclosureGroup` when `.compact` |
| GPU work off the main actor | `Numerical/*/Renderer` | `Task.detached { … await MainActor.run { … } }` |
| Frame-drop guard | `Renderer.tick()` | `guard renderTask == nil else { return }` |
| Timing MLX correctly | `HeatTransfer/Renderer.render()` | call `eval(...)` inside the timed region |
| CLI arg reuse | all Tools | `@OptionGroup var memory: MemoryArguments` etc. |
| URL as CLI argument | `Tools/*/Arguments.swift` | `extension URL: @retroactive ExpressibleByArgument` behind `#if swift(>=5.10)` |
| Progress reporting struct | SD + LoRA apps | `struct Progress: Equatable, Sendable { title; current: Double?; limit: Double? }` — **shadows Foundation `Progress`** |

---

## 15. Gotchas / footguns (consolidated)

1. **`MLX.GPU.set(cacheLimit:)` is gone from this repo** — use `Memory.cacheLimit` / `Memory.memoryLimit` / `Memory.snapshot()`.
2. **`-skipMacroValidation` is mandatory** for `xcodebuild` since `mlx-swift-lm` 3.x ships macros (`MLXHuggingFace`). CI does it for every scheme.
3. **`xcodebuild -showComponent MetalToolchain`** is a CI precondition — the Metal toolchain must be installed.
4. **`mlx-run` requires a prior Xcode build** and defaults to **Release**; it exists solely to set `DYLD_FRAMEWORK_PATH`.
5. **Trailing empty assistant message** breaks chat templates when using the raw `UserInput` path (`ChatSession` handles it internally). Trim it.
6. **EXIF orientation is not applied by `CIImage(contentsOf:)`** — VLMs get rotated images unless you re-render pixels (`UIGraphicsImageRenderer`) before writing the JPEG.
7. **PhotosPicker `loadTransferable(type: Data.self)` is unreliable**; declare explicit `Transferable` wrappers with `DataRepresentation(importedContentType: .image)` / `FileRepresentation(importedContentType: .movie)`, and **copy** the file out of `receivedFile.file`.
8. **`fileImporter` URLs need `startAccessingSecurityScopedResource()`/`stop…`** (see `MediaSelection.didSetURLs`).
9. **Two different `ModelContainer` types**: `MLXLMCommon.ModelContainer` (LLM/VLM) and `StableDiffusion.ModelContainer<M>` (generic actor). Don't confuse them.
10. **Two different `Progress` types**: Foundation `Progress` (download callbacks) and `Progress` from jkandzi/Progress.swift (terminal bar, used in image-tool) — plus the apps' own local `struct Progress`.
11. **`MLXArray` is not `Sendable`** — every `perform`/`performTwoStage` doc comment says callers must `eval()` before returning arrays across the isolation boundary.
12. **MLX is lazy** — benchmarks must call `eval(...)` inside the timed region or you measure nothing.
13. Root `Package.resolved` (0.31.3) contradicts `Package.swift` (`from: 0.31.4`); the workspace resolution (0.31.4) is what actually builds.
14. **`.spi.yml` and `MLXChatExample/README.md` requirements are stale** (list moved targets / say iOS 17 when the project says 18).
15. `Tools/embedder-tool/README.md` links to `Libraries/Embedders/README.md`, which no longer exists.
16. **LLMBasic requires iOS/macOS 26.2 + Swift 6**; the Numerical apps require **26.5**. You cannot open these on older tooling.
17. `MLXLMTests` and `ExampleLLM` are targets in the pbxproj with **no sources in this repo** (moved to mlx-swift-lm). `xcodebuild -scheme` on them will not do what you expect.
18. `MNISTTrainer/README.md` still says the data host is http; `Files.swift` uses https (`raw.githubusercontent.com/fgnt/mnist`). The checked-in Info.plist is an empty dict.
19. `GenerateParameters.maxTokens` is `Int?` — `nil` means unlimited (`/maxTokens` with no argument in `llm-tool chat` removes the limit).
20. `llm-tool eval` auto-switches to `VLMModelFactory` **only if** `--image` or `--video` is present; `llm-tool chat` tries VLM first and falls back on `ModelFactoryError.unsupportedModelType`.
21. Gemma 4 31B / 26BA4B were deliberately **not** added to MLXChatExample: "*they are too large to be practical on the supported iOS devices*" (commit `12fb46a`).
22. `GenerateArguments.generate(input:context:)` in llm-tool ends with `fatalError("exited loop without seeing .info")` — the stream is expected to always terminate with `.info`.
23. Xcode ⌘⌥R + unchecking "Debug Executable" measurably improves LLM throughput (LLMEval README).

---

## 16. Source inventory — every file/URL actually read this session

**Root / config**
- `README.md`, `CONTRIBUTING.md`, `ACKNOWLEDGMENTS.md`, `.gitignore`, `.swift-format`, `.pre-commit-config.yaml`, `.spi.yml`
- `Package.swift`, `Package.resolved`
- `mlx-run`
- `Configuration/Build.xcconfig`
- `.github/workflows/pull_request.yml`
- `mlx-swift-examples.xcodeproj/project.pbxproj` (grepped + parsed with python for package refs, build settings, target→product mapping)
- `mlx-swift-examples.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`
- `mlx-swift-examples.xcodeproj/xcshareddata/xcschemes/llm-tool.xcscheme` (+ arg extraction from image-tool/embedder-tool schemes)

**Applications**
- `Applications/LLMBasic/{README.md, LLMBasicApp.swift, ContentView.swift, ChatModel.swift, LLMBasic.entitlements}`
- `Applications/LLMEval/{README.md, LLMEvalApp.swift, LLMEval.entitlements}`
- `Applications/LLMEval/ViewModels/{LLMEvaluator.swift, DeviceStat.swift}`
- `Applications/LLMEval/Views/{ContentView.swift, HeaderView.swift, MetricsView.swift, MetricCard.swift, OutputView.swift, PromptInputView.swift, PresetPromptsSheet.swift, LoadingOverlayView.swift}`
- `Applications/LLMEval/Models/{PresetPrompts.swift, ToolDefinitions.swift}`
- `Applications/LLMEval/Services/{ToolExecutor.swift, FormatUtilities.swift}`
- `Applications/MLXChatExample/{README.md, MLXChatExampleApp.swift, ChatView.swift, MLXChatExample.entitlements}`
- `Applications/MLXChatExample/Services/MLXService.swift`
- `Applications/MLXChatExample/ViewModels/ChatViewModel.swift`
- `Applications/MLXChatExample/Models/{LMModel.swift, Message.swift}`
- `Applications/MLXChatExample/Views/{ConversationView.swift, MessageView.swift, MediaPreviewView.swift, PromptField.swift}`
- `Applications/MLXChatExample/Views/Toolbar/{ChatToolbarView.swift, DownloadProgressView.swift, GenerationInfoView.swift, ErrorView.swift}`
- `Applications/MLXChatExample/Support/{HubApi+default.swift, SampleData.swift}`
- `Applications/LoRATrainingExample/{README-referenced, ContentView.swift, LoRATrainingExample.entitlements}`
- `Applications/MNISTTrainer/{README.md, ContentView.swift, PredictionView.swift, MNISTTrainer-Info.plist, MNISTTrainer.entitlements}`
- `Applications/StableDiffusionExample/{README.md, StableDiffusionExampleApp.swift, ContentView.swift, StableDiffusionExample.entitlements}`

**Tools**
- `Tools/llm-tool/{README.md, LLMTool.swift, Chat.swift, LoraCommands.swift, ListCommands.swift, Tools.swift, Arguments.swift}`
- `Tools/image-tool/{README.md, ImageTool.swift, Arguments.swift}`
- `Tools/embedder-tool/{README.md, EmbedderTool.swift, EmbedderCommand.swift, ModelArguments.swift, PoolingArguments.swift, CorpusArguments.swift, MemoryArguments.swift, SearchCommand.swift, EmbedderRuntime+Embedding.swift}`
- `Tools/mnist-tool/{README.md, MNISTTool.swift}`
- `Tools/LinearModelTraining/LinearModelTraining.swift`
- `Tools/Tutorial/Tutorial.swift`

**Libraries**
- `Libraries/MLXMNIST/{README.md, MNIST.swift, Files.swift}`
- `Libraries/StableDiffusion/{README.md, Load.swift, StableDiffusion.swift (1-220)}` + `grep public` over `Configuration.swift`, `Image.swift`

**Numerical**
- `Numerical/Mandelbrot/{README.md, MandelbrotApp.swift, ContentView.swift, Renderer.swift}`
- `Numerical/Mandelbrot/Algorithm/{Mandelbrot+MLX.swift, Mandelbrot+CPU.swift, Configuration.swift}`
- `Numerical/Mandelbrot/Utilities/{MLX+IOSurface.swift, ImageView.swift, Array2D.swift}`
- `Numerical/HeatTransfer/{README.md, ContentView.swift, Renderer.swift}`, `Algorithm/{Jacobi+MLX.swift, Configuration.swift}`
- `Numerical/CurveFit/{README.md, ContentView.swift}`, `Algorithm/Gradient.swift`

**Data / support**
- `Data/lora/train.jsonl` (head), `Data/lora/wikisql.py` (head), line counts for all three splits
- `support/{generate-run-all-llms.sh, run-all-llms.sh}`

**Git**
- `git log --oneline -50`, `git log --pretty=format:"%h %ad %s" --date=short -30`
- `git show` for: `378f244`, `12fb46a`, `85a9d85`, `357c97f`, `c1198e2`, `0db7c5d --stat`, `70eaaca --stat`

**External URLs referenced by the repo (NOT fetched this session):**
- https://github.com/ml-explore/mlx-swift-lm (+ swiftpackageindex docs for MLXLMCommon / MLXLLM / MLXVLM / MLXEmbedders / ChatSession)
- https://swiftpackageindex.com/ml-explore/mlx-swift/main/documentation/mlx/troubleshooting
- https://huggingface.co/stabilityai/sdxl-turbo, .../stable-diffusion-2-1-base

---

## 17. Open questions / unverified

1. **Exact signature of `#huggingFaceLoadModelContainer`** — does it choose LLM vs VLM factory automatically, or default to `LLMModelFactory`? Both call sites use LLMs. Also unclear whether the trailing closure is `(Progress) -> Void` labeled `progressHandler:` (the calls use an unlabeled trailing closure).
2. **`#hubDownloader` with vs without parentheses** — both forms appear; likely the macro has a default-argument form. Need the macro declaration from `mlx-swift-lm`.
3. **`resolve(configuration:from:useLatest:progressHandler:)`** — return type name (I only saw `.modelDirectory`), and what `useLatest: false` actually gates (revision pinning?).
4. **`Memory` type shape** — is it an `enum` namespace, `struct`, or `actor` in mlx-swift 0.31.x? Are `cacheLimit`/`memoryLimit` `Int` bytes (assumed from `/ 1024` prints)? Is `Memory.Snapshot` `Sendable`?
5. Whether `MLX.GPU.set(cacheLimit:)` still exists as a deprecated alias in mlx-swift 0.31.4.
6. **`LoRATrain.train` progress callback return type** — `.more` is used; presumably an enum with a stop case.
7. `ModelConfiguration.id` enum: exact case payload names (`.id(String, String)` — second value printed as revision).
8. `Tool` parameter type enum: only `.string` and `.int` observed; full set unknown.
9. `GenerateParameters.prefillStepSize` (added `5651f0b`) — default value and semantics not verified from source (commit not inspected in detail).
10. `UserInput.additionalContext` type — `[String: Any]`? `[String: Sendable]`? Only `["enable_thinking": Bool]` seen.
11. MNISTTrainer ATS configuration — the Info.plist is empty; presumably `INFOPLIST_KEY_NSAppTransportSecurity` in build settings (not confirmed).
12. `ExampleLLM` and `MLXLMTests` targets: whether they build at all in the current tree (no sources present).
13. Whether the `traits = ( )` pbxproj key implies a minimum Xcode version (SwiftPM traits are new).
14. `Numerical/*` require iOS/macOS 26.5 — is that a real API dependency (e.g. `IOSurface` on iOS, or `MLXFast.metalKernel` availability) or just the author's SDK?
15. `EmbedderRegistry`, `EmbedderModelFactory`, `Pooling` full API — only partially observed through the tool.
16. Exact `Generation` declaration: it is matched both as an enum (`case .chunk(let s)`) and via optionals (`first.chunk`, `first.toolCall`) — presumably an enum plus computed properties.
