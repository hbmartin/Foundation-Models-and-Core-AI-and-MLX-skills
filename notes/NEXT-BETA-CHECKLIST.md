# Next-beta checklist — run on every new Xcode 27 beta / Apple doc refresh

Assembled 2026-07-31 from the open questions the 2026-07-29 refresh pass left behind.
Baseline for "changed?" everywhere below: Xcode 27.0 beta `27A5228h`, macOS SDK 27.0,
host macOS 26.5.2, dumps committed in `notes/sdk-interfaces/`. Companion docs:
`notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` (items that need a *running* OS 27, not just
a toolchain — this checklist covers what a toolchain drop CAN answer).

Every item is independent; check them off per beta. Commands are copy-pasteable from
the repo root.

---

## 0. The re-dump ritual (do this first, in order)

- [ ] Point the toolchain at the new beta and confirm what you got:
  ```bash
  sudo xcode-select -s /Applications/Xcode-beta.app
  xcodebuild -version && xcrun --sdk macosx --show-sdk-version
  ```
- [ ] Dump + drift in one step — `scripts/diff-interfaces.sh` runs
  `scripts/dump-sdk-interfaces.sh` and then git-diffs every fresh capture against the
  committed one, filtered to `public|open|@available|case ` lines:
  ```bash
  ./scripts/diff-interfaces.sh                # fresh dumps vs HEAD
  ./scripts/diff-interfaces.sh --against <tag-of-previous-beta>   # if HEAD moved
  ```
  A same-version re-dump with no toolchain change must read "clean — no drift" for
  every framework (that is the verified 2026-07-31 baseline output). Anything else IS
  the beta's API drift — start the guide pass from those lines. One known benign
  wrinkle: Evaluations may report a few "raw +/- lines below the filter" — the
  committed capture is the arm64 slice while fresh dumps prefer arm64e, so only the
  `swift-module-flags` header line differs, zero declarations. It disappears once an
  arm64e capture is committed.
- [ ] Cross-major comparisons on request, one framework at a time:
  ```bash
  ./scripts/diff-interfaces.sh --baseline 26.5 --framework FoundationModels
  ./scripts/diff-interfaces.sh --baseline 26.5 --framework Speech
  ```
- [ ] CLI help capture, by hand. `dump-sdk-interfaces.sh` invokes `fm`/`coreai-build`
  by bare name (line 71: `"$t" --help`), so a tool that only resolves through xcrun —
  which is how `coreai-build` ships today (see item 1) — writes "command not found"
  into its `-help-sdk*.txt` capture. Until that script is fixed, capture manually:
  ```bash
  xcrun coreai-build --help > notes/sdk-interfaces/coreai-build-help-sdk$(xcrun --sdk macosx --show-sdk-version).txt 2>&1
  xcrun fm --help           # still expected ABSENT from the toolchain; see item 2
  ```
- [ ] Re-run the runtime probes **if `probes/` exists**. As of 2026-07-31 a
  `probes/` Swift package is being assembled (in progress, untracked): probes that
  need an OS 27 runtime `XCTSkip` on this 26.5 host, so re-run per beta AND once on
  a real OS 27 machine:
  ```bash
  [ -d probes ] && (cd probes && swift test)
  ```
  The two probe snippets that motivated it stay documented in
  `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` items 5 and 6.
- [ ] Re-check the GitHub defect hedges (a doc refresh usually rides a beta):
  ```bash
  ./scripts/refresh-defect-statuses.sh > /tmp/defect-report.md   # full report
  ./scripts/refresh-defect-statuses.sh --changed-only            # just the edits needed
  ```
  Work the STATE-CHANGED rows into the guides by hand; the script never edits.
- [ ] After guide edits, rebuild the indexes. Per the header of
  `scripts/build-indexes.sh`: re-run `python3 scripts/extract-callouts.py`, then
  **classify any NEW ⚠️ callout rows by hand** (symptom ids per
  `notes/synthesis/SYMPTOM-TAXONOMY.md` — this is the one step that needs judgment,
  not automation), assemble the per-part `part-NN.tsv` files, then:
  ```bash
  ./scripts/build-indexes.sh <classified-dir>
  ```

---

## 1. `coreai-build` — it APPEARED (2026-07-31), watch where it lands next

State change since the 2026-07-29 pass, found while building this checklist — **no new
Xcode involved**: the Metal Toolchain component download (`xcodebuild
-downloadComponent MetalToolchain`, suggested in NEEDED item 6) brought it in.
`xcrun --find coreai-build` now resolves into
`…/DVTDownloads/MetalToolchain/mounts/…/Metal.xctoolchain/usr/bin/coreai-build`,
version `coreai-build 3600.79.1`, subcommands `compile` | `package` | `inspect` |
`metadata`, and a real `--help`. The guides still say it is absent — that is a pending
guide edit, not yet made.

Where the absence hedge lives: `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 2;
`guides/part-07-coreai-swift-runtime/references/02-specialization-caching-and-aot.md`
§13 (the "⚠️ not currently possible — the tool is absent" note near line 1700);
`guides/part-10-coreai-hardware-authoring-debugging/references/03-llm-export-end-to-end.md`
(line ~2512); `guides/part-15-shipping-and-operating/references/01-model-distribution-and-updates.md`
(lines ~21, 71–73, 128); `guides/part-17-migration-from-pre-ios-27/references/06-toolchain-and-asset-compatibility.md`
§7 and its header (lines ~96–98, the `aimodelc` stub that says *"Please use 'xcrun
coreai-build' instead"*).

- [ ] Does it move from the Metal Toolchain mount into Xcode proper?
  ```bash
  xcrun --find coreai-build && xcrun coreai-build --version
  ```
- [ ] Capture the subcommand surfaces NEEDED item 2 still wants — the full
  `--preferred-compute` value list and the device-architecture code enumeration
  (only `h18p` known, from a blog):
  ```bash
  xcrun coreai-build help compile; xcrun coreai-build help inspect
  xcrun coreai-build help package; xcrun coreai-build help metadata
  ```
- [ ] Does `aimodelc`'s usage stub still point at `coreai-build`? (`aimodelc` at
  `Xcode-beta.app/Contents/Developer/usr/bin/aimodelc`, no `--help`.)

## 2. `fm` — still nothing in the toolchain; OS 27 claim untested

`xcrun --find fm` fails on `27A5228h` (verified 2026-07-29; NEEDED item 1). The corpus
claims it comes preinstalled **with macOS 27**, so the toolchain check can only ever
prove the negative. Guide with no attested flag surface:
`guides/part-05-prototyping-profiling-non-swift/references/02-fm-cli-and-python-sdk.md`.

- [ ] `xcrun --find fm` on each new beta (absence expected until a beta bundles it).
- [ ] On any machine actually *running* macOS 27: the full `fm --help` /
  `fm <subcommand> --help` sweep spelled out in NEEDED item 1.

## 3. Evaluations — Xcode-bundled today; watch for an OS-SDK move and tvOS

`Evaluations.framework` ships **inside Xcode, not in the OS SDKs** — the 27.0 beta
SDKs contain no trace; it lives under
`Xcode-beta.app/…/Platforms/<Platform>.platform/Developer/Library/Frameworks/` and is
**absent for AppleTVOS** (99 `@available(tvOS, unavailable)` marks). Cited in
`guides/part-06-evaluations/README.md` (callout, lines ~13–21) and
`guides/part-06-evaluations/references/01-foundations-and-hill-climbing.md` (lines
~7–28). `dump-sdk-interfaces.sh` already checks Frameworks/, SubFrameworks/ and the
Xcode fallback in that order, so a move shows up as a changed path in its output.

- [ ] Did it enter the OS SDK?
  ```bash
  ls "$(xcrun --sdk macosx --show-sdk-path)/System/Library/Frameworks" | grep -i evaluations
  ```
- [ ] Did tvOS appear?
  ```bash
  grep -c 'tvOS, unavailable' notes/sdk-interfaces/Evaluations-*-macos.swiftinterface
  ls "/Applications/Xcode-beta.app/Contents/Developer/Platforms/AppleTVOS.platform/Developer/Library/Frameworks" | grep -i evaluations
  ```

## 4. `ImageReference.resolve(in:)` vs `resolved(in:)` — live docs-vs-SDK contradiction

Docs present `resolved(in:)` as current and `resolve(in:)` as deprecated; the captured
27.0 interface has **only** un-deprecated `resolve(in: Transcript)`
(`FoundationModels-27.0-macos.swiftinterface:2959-2963`). Tracked at
`guides/part-17-migration-from-pre-ios-27/references/01-what-changed-checklist.md`
§7.6 (line ~1905) and gap-table row 11 (line ~2570): resolves via "a later beta's
interface, or a doc revision".

- [ ] After each re-dump:
  ```bash
  grep -n 'func resolved\?(in' notes/sdk-interfaces/FoundationModels-27.0-macos.swiftinterface
  ```
  If `resolved(in:)` appears (or `resolve(in:)` grows a deprecation), update §7.6 —
  and mind the argument-type difference the guide warns about
  (`ArraySlice<Transcript.Entry>` vs whole `Transcript`), so no mechanical rename.

## 5. MetalPerformancePrimitives — availability still macro-only? conv2d still excluded?

MPP has no `.swiftinterface` (C++ headers), so `diff-interfaces.sh` does not cover it —
check the headers directly. Two watches, both from the 2026-07-29 pass (NEEDED item 6):
per-symbol availability is **macro-only** (`__TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_27_0`
gates the 22 new matmul dtype rows; gap at
`guides/part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md`
lines ~281–291), and **`convolution2d` gets none of the new formats**
(`guides/part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md`
line ~271; related gap at line ~458).

- [ ] ```bash
  MPP="$(xcrun --sdk macosx --show-sdk-path)/System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers"
  grep -rn 'TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET' "$MPP" | head    # new gate macros = new ladder rung
  grep -rln 'e2m1\|e4m3\|e5m2' "$MPP"                              # do the fp4/fp8 rows reach conv2d files?
  ```
- [ ] Also still pending on THIS machine (NEEDED item 6): the `static_slice` and
  `-std=metal` questions in guide 11.1, now that the Metal Toolchain is downloaded.

## 6. FoundationModels error/tool surface drift

Three separate hedges, all answerable from the fresh dump + one runtime probe:

- [ ] **`GenerationError` per-case deprecation messages** — the 27.0 interface keeps
  deprecated `GenerationError` (`introduced: 26.0, deprecated: 27.0`, interface
  `:3466-3510`) with a migration message on every case; the §4 mapping table in
  `guides/part-17-migration-from-pre-ios-27/references/03-error-taxonomy-migration.md`
  (lines ~726–737, summary table line ~3261) is built from them. Watch for reworded
  messages or a removed case:
  ```bash
  sed -n '3466,3510p' notes/sdk-interfaces/FoundationModels-27.0-macos.swiftinterface   # line range moves with each beta — re-locate with: grep -n 'enum GenerationError' …
  ```
  (or just read the `diff-interfaces.sh` FoundationModels drift lines — `@available`
  and `case ` lines are exactly what the filter keeps).
- [ ] **`LanguageModelError` case drift** — nine cases as of `27A5228h` (NEEDED item 5,
  destinations mapped in part-17 ref 03 §4). Any added/removed case shows in the
  FoundationModels drift output; re-count with:
  ```bash
  awk '/enum LanguageModelError/,/^}/' notes/sdk-interfaces/FoundationModels-27.0-macos.swiftinterface | grep -c 'case '
  ```
- [ ] **`Tool.includesSchemaInInstructions` still non-inlinable?** The default body is
  invisible in interfaces (extension at `FoundationModels` interface `:1202`; guide
  `guides/part-02-foundation-models-everyday-api/references/03-tools-and-tool-calling.md`
  §4.4, line ~810). If a beta makes it `@inlinable`, the default value becomes
  readable; until then only the runtime probe in NEEDED item 5 answers it:
  ```bash
  grep -n -A3 'includesSchemaInInstructions' notes/sdk-interfaces/FoundationModels-27.0-macos.swiftinterface | grep -B1 -A3 '@inlinable'
  ```

## 7. Speech — `AssetInventory.Status` case order

The enum is `Comparable`; the case **declaration order differs between the 26.5 and
27.0 captures**, so if `<` is synthesized the ordering changed between OS generations.
Gap at `guides/part-16-adjacent-capabilities/references/01-speech-analyzer-end-to-end.md`
§5.2 (line ~1126), probe list item 6 (line ~2993), gap table **G2** (line ~3871).

- [ ] Per beta, has the 27-side order changed again?
  ```bash
  grep -n -A8 'enum Status' notes/sdk-interfaces/Speech-26.5-macos.swiftinterface
  grep -n -A8 'enum Status' notes/sdk-interfaces/Speech-27.0-macos.swiftinterface
  ```
- [ ] The definitive answer stays a runtime probe on both OS generations
  (`print([Status.installed, .downloading, .supported, .unsupported].sorted())`) —
  an interface cannot distinguish a synthesized `<` from a hand-written one.

## 8. AppIntents — the 26.4-annotation-vs-26.5-capture oddity

The 27.0 interface annotates the new execution-model surface
(`IntentValueRepresentation`, `IntentCancellationReason`, `performBackgroundTask`…)
`@available(anyAppleOS 26.4, *)` — **yet none of it appears in this repo's 26.5
capture**. Noted in
`guides/part-16-adjacent-capabilities/references/02-app-schema-domains.md` §13 (line
~2664–2668) and gap rows G4/G9 (lines ~3505–3510). Either the 26.5 SDK genuinely lags
its own OS availability, or the capture caught an odd slice.

- [ ] Does a fresh dump on a newer 26.x-SDK Xcode (or the next 27 beta's view of 26.x)
  make them appear?
  ```bash
  grep -cn 'IntentValueRepresentation\|IntentCancellationReason' notes/sdk-interfaces/AppIntents-26.5-macos.swiftinterface   # 0 today
  grep -cn 'IntentValueRepresentation\|IntentCancellationReason' notes/sdk-interfaces/AppIntents-27.0-macos.swiftinterface   # non-zero today
  ```
- [ ] If a later 26.x capture materializes them, the "not in 26.5" hedges in part-16
  §13 need their wording tightened from "SDK absent" to "26.5-interface absent".

---

Everything above feeds the same loop: dump → diff → edit guides → re-run
`refresh-defect-statuses.sh` → rebuild indexes. Items that need a *running* macOS 27
(fm on-OS, Instruments lane names, AIModelCache deletion semantics, on-device
`contextSize`) stay in `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` — do not duplicate
them here.
