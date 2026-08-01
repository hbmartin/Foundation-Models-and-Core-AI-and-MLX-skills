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

- [ ] Point this shell at the new beta and confirm what you got. Keep the selection process-local;
  the capture scripts respect `DEVELOPER_DIR` and never change global `xcode-select` state:
  ```bash
  export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
  xcodebuild -version
  xcrun --sdk iphoneos --show-sdk-version
  xcrun --sdk macosx --show-sdk-version
  ```
- [ ] Preflight the complete capture identity before writing evidence. This checks Xcode and SDK
  versions plus the separately installed Metal Toolchain, `metal`, and `coreai-build` identities:
  ```bash
  ./scripts/dump-sdk-interfaces.sh --check-only
  ```
  The capture manifest makes a stable SDK filename safe: a different Xcode build cannot silently
  overwrite an existing `*-27.0-macos.swiftinterface` merely because both betas report SDK 27.0.
- [ ] Dump + drift in one step — `scripts/diff-interfaces.sh` captures into a temporary
  destination, then compares every fresh artifact against the committed managed capture without
  mutating it, filtered to `public|open|@available|case ` lines:
  ```bash
  ./scripts/diff-interfaces.sh                # fresh dumps vs HEAD
  ./scripts/diff-interfaces.sh --against <tag-of-previous-beta>   # if HEAD moved
  ```
  A same-version re-dump with no toolchain change must read "clean — no drift" for
  every framework (that is the verified 2026-07-31 baseline output). Anything else IS
  the beta's API drift — start the guide pass from those lines. Slice selection is deterministic:
  OS SDK frameworks prefer arm64e, while Xcode-bundled developer frameworks such as Evaluations
  prefer their ordinary arm64 host slice. The same run also diffs each fresh CLI help capture
  (`coreai-build`, and `fm` if present) body-for-body against the newest committed help capture
  for that tool, so `--help` surface drift shows up here too — no separate manual step. Known
  SDK-27.0 baseline: the committed `coreai-build-help-27.0-beta.txt` is a manual legacy capture,
  so this comparison reports its section-marker spelling (`===== coreai-build compile =====` vs
  the scripted `… compile --help =====`) and its extra validation-oracle lines as drift — that
  exact report (verified 2026-07-31: +4 / −17 lines) is "clean" for 27.0. Flag-surface changes
  appear as additional lines. From the next SDK version on, scripted captures compare against
  scripted captures and a no-change run reads genuinely clean.
- [ ] Re-verify the guide snippets against the new SDK (added 2026-07-31; grammar and
  committed baseline in `notes/snippet-verification/README.md`):
  ```bash
  ./scripts/verify-snippets.sh --sdk 27 --out notes/snippet-verification
  ```
  Any fence that WAS green and turns red **is the beta's snippet-level API drift**, with
  the failing symbol named by the compiler at a mapped guide line. Fold fixes into the
  guides, re-run, commit the refreshed `results.tsv` + `report.md`.
- [ ] Cross-major comparisons on request, one framework at a time:
  ```bash
  ./scripts/diff-interfaces.sh --baseline 26.5 --framework FoundationModels
  ./scripts/diff-interfaces.sh --baseline 26.5 --framework Speech
  ```
- [ ] If the drift is intentional and you need to retain a same-SDK/new-Xcode candidate for review,
  capture it to a fresh staging directory. Do not copy its manifest over the managed one: that
  would discard the independently owned 26.5 and legacy records.
  ```bash
  capture_candidate_dir="$(mktemp -d)"
  ./scripts/dump-sdk-interfaces.sh --dest "$capture_candidate_dir"
  ```
  Promote only the reviewed artifacts and merge their manifest ownership using the procedure in
  `notes/sdk-interfaces/README.md`, then finish with
  `./scripts/dump-sdk-interfaces.sh --check-only`. There is deliberately no blind auto-promotion
  mode.
- [ ] Confirm the CLI surfaces. `dump-sdk-interfaces.sh` resolves tools through `xcrun`, captures
  top-level and all four `coreai-build` subcommand help pages, and writes the canonical
  `coreai-build-help-<macOS-SDK-version>.txt`; the drift step above already compared its body
  against the committed capture. On a **new SDK version**, a plain managed capture adds the new
  help file alongside the interfaces. On a **same-SDK/new-Xcode beta**, the managed capture
  correctly refuses (cross-build protection on the stable interface filenames) — use the
  candidate-directory flow from the previous step; the legacy `-27.0-beta.txt` evidence remains
  separately managed and is never overwritten either way:
  ```bash
  ./scripts/dump-sdk-interfaces.sh            # new SDK version only
  xcrun --no-cache --find fm  # still expected absent from this toolchain; see item 2
  ```
- [ ] Re-run the runtime probes. The `probes/` package is tracked (31 probes committed in
  `b7a9432`, extended 2026-07-31; see `probes/README.md` for the four-destination table
  HOST-26 / SIM-27 / MAC-27 / DEVICE-27 and the healthy-baseline counts). Probes that need an
  OS 27 runtime `XCTSkip` on this 26.5 host, so re-run per beta on both local destinations AND
  once on a real OS 27 machine:
  ```bash
  (cd probes && swift test)
  (cd probes && xcodebuild test -scheme Probes-Package \
      -destination 'platform=iOS Simulator,OS=27.0,name=iPhone 17 Pro')
  ```
  Any probe whose `PROBE-RESULT` differs from the value recorded in `probes/README.md` is the
  beta's behavioral drift. The probes that motivated the package are documented in
  `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` items 5 and 7.
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
  not automation), update the committed per-part `part-NN.tsv` files under
  `notes/synthesis/callout-classifications/`, then:
  ```bash
  ./scripts/build-indexes.sh
  ```
- [ ] Rebuild the installable skills, which are derived from the same guides and the
  indexes you just regenerated:
  ```bash
  ./scripts/build-skills.sh
  ```
  It refuses to run if a part README grew a heading it does not recognize, so a
  structural guide edit surfaces here rather than silently dropping a section from a
  released skill. `scripts/tests/test_skills.py` fails CI if `skills/` is stale.

---

## 1. `coreai-build` — component-scoped and captured (resolved 2026-07-31)

The 2026-07-29 negative check was a component-installation result, not a beta-product result:
`coreai-build` is not inside Xcode-beta.app. Apple's Core AI documentation requires the optional
Metal Toolchain component (`xcodebuild -downloadComponent MetalToolchain`); after installation,
`xcrun --no-cache --find coreai-build` resolves into
`…/DVTDownloads/MetalToolchain/mounts/…/Metal.xctoolchain/usr/bin/coreai-build`, version
`coreai-build 3600.79.1`. Its `compile` | `package` | `inspect` | `metadata` surfaces are captured,
and the affected guides now distinguish the app bundle from the required component. See Apple's
[*Compiling Core AI models ahead of time*](https://developer.apple.com/documentation/coreai/compiling-core-ai-models-ahead-of-time).

- [ ] Does it move from the Metal Toolchain mount into Xcode proper, or change independently of
  the Xcode build?
  ```bash
  xcodebuild -showComponent MetalToolchain -json
  xcrun --no-cache --find coreai-build && xcrun coreai-build --version
  ```
- [ ] Re-capture every subcommand surface. The 2026-07-31 baseline has
  `--preferred-compute {gpu, neural-engine, none}` and 24 accepted architecture codes; a new
  component can drift even when the macOS SDK version remains `27.0`:
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
§7.6 (line ~1929) and gap-table row 11 (line ~2570): resolves via "a later beta's
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
- [ ] ~~Also still pending on THIS machine (NEEDED item 6): the `static_slice` and `-std=metal`
  questions in guide 11.1.~~ **Resolved 2026-07-31** (NEEDED item 6: `static_slice` does not
  exist — the real API is `slice<...>`; the tensor macros are `-std`-gated, measured per version)
  and folded into guide 11.1. Per beta, only re-check that the compiler's answers hold.

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
  §4.4, line ~815). If a beta makes it `@inlinable`, the default value becomes
  readable in the interface; the runtime probe in `probes/` has already measured the default
  (`true`, 2026-07-31, both the 26.5 host and the 27.0 sim runtime) — re-measure per beta:
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
- [x] The definitive answer stays a runtime probe on both OS generations — an interface cannot
  distinguish a synthesized `<` from a hand-written one. The probe now exists and has run
  (2026-07-31): `speech.assetInventory-status-order` in
  `probes/Tests/ProbesTests/SpeechProbes.swift` measured **26.5 host:
  `unsupported<supported<downloading<installed`; 27.0 sim:
  `unsupported<downloading<supported<installed`** — `<` is synthesized and the ordering really
  changed (guide 16.1 §5.2 / G2 closed). Re-run per beta and compare against
  `probes/README.md`.

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
