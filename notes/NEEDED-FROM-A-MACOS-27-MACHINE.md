# What still requires macOS 27, Instruments UI, or a physical OS-27 device

**Status checked 2026-08-01.** **Xcode 27.0 beta 4 (`27A5228h`)**, its optional Metal Toolchain,
and the **iOS 27.0 beta 4 simulator (`24A5390f`)** are installed. The host remains macOS 26.5.2
(`25F84`), with Apple's 26.6 (`25G72`) update still to apply. The full simulator probe suite now
passes (36 tests, 2 intentional skips), and `scripts/dump-sdk-interfaces.sh` has captured the 27.0
interface set into `notes/sdk-interfaces/` — including the Core AI SubFrameworks umbrella
(`CoreAIRuntime`, `CoreAIAsset`, `CoreAIDelegates`), the cross-import overlays
(`_Vision_FoundationModels`, `_CoreSpotlight_FoundationModels`), and Xcode-bundled `Evaluations`.
**Items 2, 4, 5 and 6 below are resolved and folded into the guides (2 and 6's toolchain half fell
on 2026-07-31 when the Metal Toolchain component turned out to contain `coreai-build` and the Metal
compiler). Items 1, 3, and 7 still need, respectively, a macOS 27 host, one manual Instruments GUI
recording against the OS-27 target, or a physical OS-27 device — the toolchain alone cannot produce
them.**

Run what you can, paste the raw output back. Partial is fine — every item is independent.

**Probes for these live in `probes/`** — the remaining behavioral items plus the guide-level 🔴
GAPs are executable XCTest probes; see `probes/README.md` for per-destination commands.

---

## 1. The `fm` CLI — 🔴 still open, now sharper

Rechecked 2026-08-01: `fm` is **absent from the Xcode 27.0 beta** —
`xcrun --no-cache --find fm` exits 72 and an
exhaustive `find` of Xcode-beta.app returns nothing. That is *consistent* with the corpus claim
that `fm` comes **preinstalled with macOS 27** (this host is 26.5.2, so the claim is untested, not
false). Guide `part-05/references/02-fm-cli-and-python-sdk.md` still has no attested flag surface.

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

## 7. Two device tests — 🔴 still open (only if you have a 27 device handy)

- **`AIModelCache` deletion semantics.** Apple's own docs contradict themselves: the reference page
  says deleting a referenced entry throws; the caching article says deletion is deferred until the
  `AIModel` deallocates. One test settles it. (The interfaces confirm only spellings, not
  behaviour — checked 2026-07-29.)
- **On-device `contextSize`.** Narrowed 2026-07-29: the 26.5 interface **hardcodes `return 4096`**;
  the 27.0 interface returns a dynamic `_contextSize` on OS 27+ and falls back to 4096 below.
  Narrowed again 2026-07-31: the `probes/` run measured **4096 on the iOS 27.0 simulator runtime**
  (and the overflow error text there independently says "maximum allowed context size of 4096").
  The third-party 8192 claim now rests entirely on 27 *hardware* — print
  `SystemLanguageModel().contextSize` on a real 27 device to settle it.

---

## Not needed from you

Everything else is either resolved or resolvable from material already on disk. The research corpus
is ~85,000 lines and the guides are written against it; after the 2026-07-29 SDK-capture pass,
the 2026-07-31 Metal-Toolchain pass, and the 2026-08-01 simulator acceptance run, items 1, 3, and 7
are the residue
that genuinely require a running macOS 27, an OS-27 recording target, or a physical OS-27 device.
