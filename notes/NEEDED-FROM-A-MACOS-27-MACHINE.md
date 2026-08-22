# What still requires macOS 27, Instruments UI, or a physical OS-27 device

**Status checked 2026-08-20.** **Xcode 27.0 beta 5 (`27A5237l`)**, its optional Metal Toolchain,
the **iOS 27.0 beta 5 simulator (`24A5408d`)**, and macOS 27 beta 5 (`26A5406e`) are installed.
An attached iPhone 15 Pro (`iPhone16,1`, `D83AP`) running iOS 27 build `24A5408d` completed the
physical-device probes. `scripts/dump-sdk-interfaces.sh` has captured the 27.0
interface set into `notes/sdk-interfaces/` — including the Core AI SubFrameworks umbrella
(`CoreAIRuntime`, `CoreAIAsset`, `CoreAIDelegates`), the cross-import overlays
(`_Vision_FoundationModels`, `_CoreSpotlight_FoundationModels`), and Xcode-bundled `Evaluations`.
**Items 1, 2, 4, 5, 6, and 7 below are resolved and folded into the guides (2 and 6's toolchain half fell
on 2026-07-31 when the Metal Toolchain component turned out to contain `coreai-build` and the Metal
compiler).** **Item 3 — one manual Instruments GUI recording — is the only original item still
open.** The broader behavioral backlog (including cancellation with a genuinely slow Core AI
asset and an entitled app-group cache run) remains in `probes/README.md`.

Run what you can, paste the raw output back. Partial is fine — every item is independent.

**Probes for these live in `probes/`** — the remaining behavioral items plus the guide-level 🔴
GAPs are executable XCTest probes; see `probes/README.md` for per-destination commands.

---

## 1. The `fm` CLI — ✅ RESOLVED 2026-08-17 on macOS 27 beta 5

The project ran `/usr/bin/fm` on macOS 27 beta 5 (`26A5406e`) and captured top-level plus every
revealed subcommand help page in `notes/sdk-interfaces/fm-help-27.0.txt`. The live surface has
eight commands: `available`, `chat`, `count-tokens`, `license`, `quota-usage`, `respond`, `schema`,
and `serve`. This corrects the third-party `token-count` spelling and adds the previously unreported
`license` command. `fm --version` is unsupported. The managed capture includes all short/long flags,
the complete `schema object` property grammar, and `serve` transports/endpoints.

Runtime-only questions remain in the guide: interactive slash commands beyond Apple's demonstrated
`/model` and `/save`, refusal/error exit behavior, and field-level Chat Completions compatibility.

### Historical pre-capture record

Rechecked 2026-08-01: `fm` is **absent from the Xcode 27.0 beta** —
`xcrun --no-cache --find fm` exits 72 and an
exhaustive `find` of Xcode-beta.app returns nothing. That is *consistent* with the corpus claim
that `fm` comes **preinstalled with macOS 27** (this host is 26.5.2, so the claim is untested, not
false).

**Updated 2026-08-02 — the guide is no longer flag-blind.** A web harvest found **three
independent third-party write-ups by people who ran the binary on macOS 27**, one of which pastes
`fm --help` from build **`26A5378n`**. Folded into
`part-05/references/02-fm-cli-and-python-sdk.md` as 🟠 **Suggestive** (never ✅ — nobody on this
project has run it). Now reported:

- installed path **`/usr/bin/fm`**;
- **seven** subcommands — `available`, `chat`, `quota-usage`, `respond`, `schema`, `serve`,
  `token-count` (three of which Apple never named in any session);
- `fm respond` flags **`--model pcc`**, **`--image <path>`**, **`--schema <file>`**, `--help`;
- `fm schema object --name <T> --string <prop> [--array]`, emitting JSON **on stdout**.

Evidence and the source-reliability analysis:
`notes/web/2026-08-02-harvest/fm-cli-real-machine-evidence.md`.

**What the run below still buys, and why it is still worth doing:** the `--help` paste is
**truncated mid-line on `token-count`**, so the list may not be complete; `--instructions` is
listed by one source and demonstrated by none; no short forms are known; no source shows the flags
of any subcommand except `respond`; every `fm serve` behaviour (port, bind address, auth, protocol
coverage) is unattested; and exit codes, stderr discipline and streaming are entirely unknown.
Priority: **unchanged — still the highest-value single run in this file.**

On a machine running macOS 27:

```bash
which fm && fm --help
fm respond --help
fm chat --help
fm schema --help
fm schema object --help
# and any other subcommands `fm --help` reveals:
fm <subcommand> --help
```

Inside an interactive session, the slash-command list:
```bash
fm chat
# then type: /help      (and /?  if /help does nothing)
```

---

## 2. `coreai-build` — ✅ RESOLVED 2026-07-31 (it ships in the Metal Toolchain component)

The 2026-07-29 "does not ship in the beta" finding was true of the bare Xcode install and wrong
about the product: **`coreai-build` 3600.79.1 arrives with the optional Metal Toolchain component**
(`xcodebuild -downloadComponent MetalToolchain`), resolving via `xcrun --no-cache --find
coreai-build` into `Metal.xctoolchain/usr/bin/` (plain `xcrun --find` can miss it through a stale
cache). That also dissolves the `aimodelc`-stub mystery — the stub pointed at a tool in a
different, optional component. Its version string matches the CoreAI framework's
`-user-module-version` (3600.79.1).

Everything the item asked for is captured in
`notes/sdk-interfaces/coreai-build-help-27.0-beta.txt`: subcommands are `compile | package |
inspect | metadata` (inspect exists, with `--io/--metadata/--storage/--compute/--ops/--json`);
**`--preferred-compute` = `gpu` | `neural-engine` | `none` (default `none`)**; and the
architecture codes were enumerated by validation-oracle probing — **24 valid codes, h11p…h18p**,
grammar `h<generation><variant>` (p = phone-class, s/c = Mac-class, g = both stacks from h13g),
`h18p` confirmed, per-platform acceptance matrix included (watchOS/visionOS accepted none of the
swept codes on this 26.5 host — the one residual caveat).

---

## 3. Xcode 27 Instruments lane names — 🔴 still open, narrowed to "needs a target"

Progress 2026-07-29, from the beta's `Instruments.app` on disk: the **Foundation Models** template
archives exactly **one instrument, `com.apple.FoundationModels`** (all six lanes are its lanes),
and the **Core AI** template archives exactly **four** (`com.apple.dt.instruments.coreai`,
`com.apple.ane`, `metal-gpu`, `coresampler2`) — both now cited in guides 5.1 §6.3 and 10.2 §3.2.
But the **lane names are not extractable from the host toolchain**: instrument definitions stream
from the *recording target* at attach time (a full-text sweep of Instruments.app for the known lane
name "Model Inference" finds nothing).

**Sharpened 2026-07-31: this no longer needs new hardware.** The iOS 27.0 Simulator runtime on
THIS machine is an OS 27 recording target, and Foundation Models inference provably runs in it
(`probes/`). What failed is *headless* capture: `xcrun xctrace record` against the booted
simulator hangs for every template on this 26.5 host (Time Profiler control included,
`--no-prompt` set), and the lane strings are not on disk (sim framework binaries live in the dyld
shared cache). The residue is one manual GUI job on this machine:

1. Open Instruments 27 → Foundation Models template → target the **booted iOS 27.0 simulator** →
   Record (click through the privacy consent) → read the six lane headers off the timeline.
2. Same for the Core AI template — lane/metric names and detail-pane columns render from the
   template even though Core AI events cannot occur in the simulator (CoreAI is absent from the
   simulator SDK; a real 27 device is still the only way to see live Core AI events).

---

## 4. Core AI error types — ✅ RESOLVED 2026-07-29

Answered from the captured interfaces, with evidence of absence: **CoreAIRuntime declares no public
error type at all** — `AIModel.init`, `loadFunction`, `run`, `encode` and every cache method throw
**untyped** `async throws`. The only public error type in the entire Core AI surface is
`CoreAIAsset.AssetError` (`kind` + `debugMessage`; `Kind` = `unsupportedVersion(String)`,
`invalidFeatureType(String)`, `corruptedMetadata`, `invalidName`, `duplicateName` —
`CoreAIAsset-27.0-macos.swiftinterface:230-247`). Correct `catch` guidance is now written into
guides 7.1 §13 and 7.2 §3. Also settled: `AIModelCache` lives in **CoreAIDelegates**;
`CoreAICache`/`CoreAICommon`/`CoreAICompiler` have empty public Swift surfaces.

---

## 5. The FoundationModels / Vision interfaces — ✅ RESOLVED 2026-07-29

All captured and folded into Parts 2–4 (34 gaps closed, 15 narrowed): the
`LanguageModelSession.init(model:...)` overload set (including a previously-undocumented generic
`some LanguageModel` family), the five `tokenCount(for:)` overloads, **no `Profile(model:)` init**
(only `.model(_:)` modifiers), full `QuotaUsage.Status` / `UnavailableReason` /
`LanguageModelError` (9 cases) lists, the `LanguageModel`/`LanguageModelExecutor` protocol
requirements, PCC surface, and `DynamicProfile`. The Vision `BarcodeReaderTool`/`OCRTool` question
resolved via the **cross-import overlay** `_Vision_FoundationModels` (their `Output` is an opaque
`some PromptRepresentable` — deliberately unnameable). The last residue fell on 2026-07-31: the
`probes/` package measured **`Tool.includesSchemaInInstructions` default = `true`** on both the
macOS 26.5 host and the iOS 27.0 simulator runtime.

---

## 6. MetalPerformancePrimitives on the 27 SDK — ✅ RESOLVED 2026-07-29 (answer inverted)

The "confirm nothing changed" expectation was wrong in the interesting direction. The 27.0 headers
add **22 new matmul dtype rows** (int2b/uint2b, fp4 `e2m1`, fp8 `e4m3` **and** `e5m2`) and
**blockwise scale planes now exist** (`tensor_blockwise` + `tensor_plane_scales`, scale dtype
`metal_fp8_ue8m0` only, block 32×1, strict transpose rules), gated behind a new
`__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_27_0` macro. Conv2d gets none of it. Per-symbol
availability is still macro-only (the 26.2-vs-Tech-Talk-ladder discrepancy stands, unchanged in
27). All written into Part 11 with header citations.

The Metal Toolchain follow-up ran on 2026-07-31: **`static_slice` does not exist** in the 27-era
compiler (comment-spelling only; the real API is `slice<...>`, verified by grep + compile error),
and the tensor macros are gated purely by `-std` — `metal4.0` defines `__HAVE_TENSOR__`,
`metal4.1` adds `__HAVE_TENSOR_MULTIPLANE__` and the fp4/fp8/int2b format macros (gated with
`==` per version, not `>=`); a ue8m0 scale-plane matmul compiles to AIR at 4.1. All folded into
Part 11.

---

## 7. Two device tests — ✅ RESOLVED 2026-08-20

- **`AIModelCache` deletion semantics.** On iPhone 15 Pro / iOS build `24A5408d`, deleting while a
  live `AIModel` retained the entry threw
  `AIModelCacheError.failedToPurge("Deletion could not be completed, assets still in use")`; the
  entry remained findable. After releasing the model, deletion succeeded. The tested runtime
  therefore matches the reference pages rather than the article's silent-deferral wording. The
  observed error type is not public in the captured SDK, so production code still needs a generic
  `catch`.
- **On-device `contextSize`.** ✅ **4096 on iPhone 15 Pro / iOS build `24A5408d`.**
  Narrowed 2026-07-29: the 26.5 interface **hardcodes `return 4096`**;
  the 27.0 interface returns a dynamic `_contextSize` on OS 27+ and falls back to 4096 below.
  Narrowed again 2026-07-31: the `probes/` run measured **4096 on the iOS 27.0 simulator runtime**
  (and the overflow error text there independently says "maximum allowed context size of 4096").
  **Documented 2026-08-02:** Apple's written Q&A summary for WWDC26 Group Lab 8121
  (ch. `0:08:11`) gives **4096, shared across input and output**, as the iOS 27 platform value,
  with PCC at 32K. The third-party 8192 device report remains uncorroborated rather than disproved.
  Folded into guides 17.1 §1.1 and 3.1 §3.3.
  The physical result closes the device-specific residual for this hardware/build and leaves the
  third-party 8192 report uncorroborated. Continue re-running on later seeds because the OS-27 API
  remains dynamic.

---

## Not needed from you

Everything else in this original machine-dependency list is resolved. After the SDK, Metal
Toolchain, macOS-27, simulator, and 2026-08-20 physical-device passes, **item 3's manual Instruments
GUI recording is the sole residue here**. New and partially answered runtime questions are tracked
at probe granularity in `probes/README.md`.
