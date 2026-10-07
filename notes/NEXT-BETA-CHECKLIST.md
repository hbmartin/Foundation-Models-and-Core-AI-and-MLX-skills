# Release-event checklist

Run when Xcode, an SDK, the OS, a simulator runtime, or relevant Apple documentation changes. Keep installed verification and latest observed releases separate; a beta announcement does not verify local runtime behavior.

<!-- current-state:next-beta:start -->
Current installed baseline: Xcode 27.0 `27A266a`, macOS 27.0 `26A428`, macOS SDK `26A425`, iOS SDK `24A430`, and newest iOS Simulator runtime `24A5408d`. Latest observed releases are Xcode 27.2 beta 2 `27B5028f`, iOS 27.2 beta 3 `24B5099f`, and macOS 27.2 beta 3 `26B5101f`. Installed Xcode build 27A266a differs from observed build 27B5028f. Installed macOS build 26A428 differs from observed build 26B5101f.
<!-- current-state:next-beta:end -->

## 0. The re-dump ritual (do this first, in order)

- [ ] Select the intended Xcode in this shell, then record `xcodebuild -version`, `sw_vers`, SDK versions/builds, and simulator runtimes. Do not change global selection.
- [ ] Run `./scripts/dump-sdk-interfaces.sh --check-only`; check the optional Metal Toolchain before capture.
- [ ] Run `./scripts/diff-interfaces.sh` into a temporary candidate. Promote changed evidence only through the hashed capture workflow in [SDK evidence](sdk-interfaces/README.md).
- [ ] Run `./scripts/verify-snippets.sh --sdk 27 --developer-dir-27 "$DEVELOPER_DIR" --allow-unavailable-targets --out artifacts/swift-refresh`. Preserve unavailable-target results with their original provenance.
- [ ] Run `./scripts/run-probes.sh host` and the simulator lane with an available explicit destination. Run the hosted device lane when hardware-dependent claims changed. Preserve logs, results and complete topology; do not compare fixed test counts between lanes.
- [ ] Triage current defect records, update canonical guides, reconcile changed callout identities, regenerate indexes and skills, then run portable checks.
- [ ] Update `notes/current-state.json`, including full consistency-check dates, and run `./scripts/current-state.py render --write`.

## 1. `coreai-build` — component-scoped capture

- [ ] Compare help and Metal Toolchain identity using the managed capture workflow. A changed component can change the CLI without an OS update.

## 2. `fm` — OS-bundled capture

- [ ] Check `/usr/bin/fm --help` on the recorded OS build. Compare against [the canonical surface](../guides/part-05-prototyping-profiling-non-swift/references/02-fm-cli-and-python-sdk.md#3--the-fm-help-surface-captured-on-macos-27); an absent tool in another SDK is not evidence about the running OS.

## 3. Evaluations — framework location and tvOS

- [ ] Check SDK and Xcode developer-framework locations independently. Recheck tvOS availability annotations; do not infer support from another platform's capture.

## 4. `ImageReference.resolve(in:)` vs `resolved(in:)` — watch for regression

- [ ] Run `./scripts/capture-apple-docs-watch.py --output artifacts/freshness/apple-docs/<unique-run-id>` before changing the guide. The overview and member captures must agree; inspect their hashes and argument types.
- [ ] Compare the fresh FoundationModels declaration with the overview and member documentation. The current sequence overload is `resolved(in: some Sequence<Transcript.Entry>)`; a whole-Transcript overload is not a mechanical rename.

## 5. MetalPerformancePrimitives — headers and availability

- [ ] Inspect C++ headers directly for per-feature deployment macros and supported matmul/convolution formats; Swift interface diffs do not cover MPP.
- [ ] Recheck compiler language-mode gates and `slice<...>` if relevant headers changed.

## 6. FoundationModels error/tool surface drift

- [ ] Compare `GenerationError` deprecation messages, `LanguageModelError` cases, and `Tool.includesSchemaInInstructions` declarations. Runtime-only defaults require a matching probe, not an inferred interface body.

## 7. Speech — `AssetInventory.Status` case order

- [ ] Compare the fresh declaration and runtime ordering. Preserve the OS 26/27 ordering difference where migration code depends on it.

## 8. AppIntents — annotation versus captured surface

- [ ] Compare annotation floors with the actual supported SDK declaration. A missing declaration in an older capture must not be silently rewritten as runtime unavailability.

## Manual evidence

[Instruments recording](../probes/INSTRUMENTS-RECORDING.md) owns rendered UI labels and Core AI lane/metric names. Keep this checklist actionable; put current results in the manifest and retained evidence, not an event log here.
