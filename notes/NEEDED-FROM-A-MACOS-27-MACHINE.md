# What to run on a macOS 27 / Xcode 27 machine

**Status update 2026-07-29.** The **Xcode 27.0 beta (27A5228h)** is now installed on this machine
(host OS still macOS 26.5.2), and `scripts/dump-sdk-interfaces.sh` has captured the full 27.0
interface set into `notes/sdk-interfaces/` — including the Core AI SubFrameworks umbrella
(`CoreAIRuntime`, `CoreAIAsset`, `CoreAIDelegates`), the cross-import overlays
(`_Vision_FoundationModels`, `_CoreSpotlight_FoundationModels`), and Xcode-bundled `Evaluations`.
**Items 4, 5 and 6 below are resolved and folded into the guides. Items 1–3 and 7 still genuinely
need a machine (or recording target / device) *running* macOS 27 — the toolchain alone cannot
produce them.**

Run what you can, paste the raw output back. Partial is fine — every item is independent.

---

## 1. The `fm` CLI — 🔴 still open, now sharper

Verified 2026-07-29: `fm` is **absent from the Xcode 27.0 beta** — `xcrun --find fm` fails and an
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

## 2. `coreai-build` — 🔴 still open, materially narrowed

Verified 2026-07-29 on the Xcode 27.0 beta: **`coreai-build` does not ship in the beta** (`xcrun
--find` fails; exhaustive find of the bundle). What *does* ship is **`aimodelc`**
(`Contents/Developer/usr/bin/aimodelc`, IDEMLKit): command types exactly `package` | `compile`,
requires `--output`, and has **no `--help`**. Bizarrely, Apple's `aimodelc` usage stub says
*"Please use 'xcrun coreai-build' instead"* — pointing at a tool that is not there.

Still needed, from any machine whose Xcode carries the tool (possibly a later beta, or macOS 27):

```bash
xcrun coreai-build --help
xcrun coreai-build compile --help
xcrun coreai-build inspect --help
```

Specifically needed: the full `--preferred-compute` value list, and the enumeration of device
architecture codes (we have only `h18p`, from a blog, unconfirmed).

---

## 3. Xcode 27 Instruments lane names — 🔴 still open, narrowed to "needs a target"

Progress 2026-07-29, from the beta's `Instruments.app` on disk: the **Foundation Models** template
archives exactly **one instrument, `com.apple.FoundationModels`** (all six lanes are its lanes),
and the **Core AI** template archives exactly **four** (`com.apple.dt.instruments.coreai`,
`com.apple.ane`, `metal-gpu`, `coresampler2`) — both now cited in guides 5.1 §6.3 and 10.2 §3.2.
But the **lane names are not extractable from the host toolchain**: instrument definitions stream
from the *recording target* at attach time (a full-text sweep of Instruments.app for the known lane
name "Model Inference" finds nothing).

So the remaining job needs Instruments 27 **attached to a device or Mac running an OS 27**:

1. Open Instruments 27 → Foundation Models template → record anything → read the six lane headers.
2. Same for the Core AI template — its on-screen lane and metric names, the detail-pane columns,
   and whether a cache-hit metric exists.

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
`some PromptRepresentable` — deliberately unnameable). One residue that still needs a runtime probe
on any 26/27 machine (interfaces cannot print non-inlinable default bodies):

```swift
// The Tool.includesSchemaInInstructions default value:
struct Probe: Tool { /* minimal conformance */ }
print(Probe().includesSchemaInInstructions)
```

---

## 6. MetalPerformancePrimitives on the 27 SDK — ✅ RESOLVED 2026-07-29 (answer inverted)

The "confirm nothing changed" expectation was wrong in the interesting direction. The 27.0 headers
add **22 new matmul dtype rows** (int2b/uint2b, fp4 `e2m1`, fp8 `e4m3` **and** `e5m2`) and
**blockwise scale planes now exist** (`tensor_blockwise` + `tensor_plane_scales`, scale dtype
`metal_fp8_ue8m0` only, block 32×1, strict transpose rules), gated behind a new
`__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_27_0` macro. Conv2d gets none of it. Per-symbol
availability is still macro-only (the 26.2-vs-Tech-Talk-ladder discrepancy stands, unchanged in
27). All written into Part 11 with header citations.

Small follow-up runnable on THIS machine when convenient (needs the ~multi-GB Metal Toolchain
component): `xcodebuild -downloadComponent MetalToolchain`, then re-check `static_slice` and the
`-std=metal` level questions in 11.1.

---

## 7. Two device tests — 🔴 still open (only if you have a 27 device handy)

- **`AIModelCache` deletion semantics.** Apple's own docs contradict themselves: the reference page
  says deleting a referenced entry throws; the caching article says deletion is deferred until the
  `AIModel` deallocates. One test settles it. (The interfaces confirm only spellings, not
  behaviour — checked 2026-07-29.)
- **On-device `contextSize`.** Narrowed 2026-07-29: the 26.5 interface **hardcodes `return 4096`**;
  the 27.0 interface returns a dynamic `_contextSize` on OS 27+ and falls back to 4096 below. So
  TN3193's 4096 is the 26.x truth, and the third-party 8192 claim is *plausible* for 27 devices —
  print `SystemLanguageModel().contextSize` on a real 27 device to settle it.

---

## Not needed from you

Everything else is either resolved or resolvable from material already on disk. The research corpus
is ~85,000 lines and the guides are written against it; after the 2026-07-29 SDK-capture pass, the
four items above (1, 2, 3, 7 — plus the two small probes inlined in items 5 and 6) are the residue
that genuinely requires a running macOS 27 / an OS 27 recording target / a 27 device.
