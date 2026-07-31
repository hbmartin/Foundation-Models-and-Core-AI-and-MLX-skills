# SDK interface evidence

This directory contains raw public Swift interfaces and CLI help used to verify claims throughout
the guides. The files are evidence snapshots, not vendored SDKs and not generated documentation.
Every capture artifact is owned by [`capture-manifest.json`](capture-manifest.json), which records
its SHA-256 digest and the provenance that is actually known.

## Quick start

Select Xcode per process when necessary; the scripts honor `DEVELOPER_DIR` and never change the
machine-wide `xcode-select` setting:

```bash
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  ./scripts/dump-sdk-interfaces.sh --check-only
```

The normal commands are:

```bash
# Verify Xcode, both SDKs, the Metal Toolchain, and all tracked hashes. Writes nothing.
./scripts/dump-sdk-interfaces.sh --check-only

# Capture into this directory, but only when every existing stable path belongs to this build.
./scripts/dump-sdk-interfaces.sh

# Capture an isolated candidate. The destination may not contain unmanaged evidence.
./scripts/dump-sdk-interfaces.sh --dest /tmp/sdk-candidate

# Compare a temporary fresh capture to a git revision. Tracked evidence is not modified.
./scripts/diff-interfaces.sh
./scripts/diff-interfaces.sh --against <git-revision>

# Compare two already-tracked SDK versions. No installed Xcode is needed for this mode.
./scripts/diff-interfaces.sh --baseline 26.5 --framework FoundationModels
```

## What the capture script proves before writing

All preflight checks occur before the script creates a temporary capture or destination file:

1. The selected developer directory is a full Xcode 27 or newer.
2. Its iPhoneOS SDK is 27 or newer. The macOS SDK is also required because the captured interfaces
   are macOS slices.
3. `xcrun --no-cache` resolves both `coreai-build` and `metal` from one
   `Metal.xctoolchain` component.
4. That toolchain's `ToolchainInfo.plist` identifier matches the identifier and search path reported
   by `xcodebuild -showComponent MetalToolchain` for the selected Xcode.
5. Every existing artifact named in the manifest still has its recorded hash, no manifest-owned
   file is missing, and no capture-shaped file is unmanaged.

`fm` is optional because it ships with macOS rather than Xcode and is absent on the host used for
the original beta capture. If `xcrun` finds it, the script adds a sanitized `fm` help artifact and
records the result. Its absence does not fail an otherwise valid capture.

The script invokes CLI tools through the paths returned by `xcrun`; it never assumes that a
component-installed tool is on `PATH`. Resolved absolute paths are used only for local checks. They
are never written into evidence. The capture also rejects artifacts containing machine-specific
user-home or mounted-volume path prefixes.

## Capture contents and stable names

Framework interfaces use a stable SDK-version path:

```text
<Framework>-<macOS-SDK-version>-macos.swiftinterface
```

The script searches the selected macOS SDK's `Frameworks/` and `SubFrameworks/`, then Xcode's
platform developer-framework directory. SDK frameworks prefer the sorted `arm64e-apple-macos`
slice. Xcode-bundled developer frameworks such as `Evaluations` prefer the ordinary
`arm64-apple-macos` slice. The exact target remains visible in each interface's
`swift-module-flags` header.

CLI surfaces use:

```text
coreai-build-help-<macOS-SDK-version>.txt
fm-help-<macOS-SDK-version>.txt        # only when fm exists
```

The Core AI file contains the top-level help plus `compile`, `package`, `inspect`, and `metadata`
subcommand help. Capture time and build identity live in the manifest rather than in these stable,
deterministic text files.

The full capture is assembled in a temporary directory first. Only after interface discovery, CLI
capture, path sanitization, hash computation, provenance construction, and destination validation
all succeed are new files installed. Existing evidence files are never overwritten by the script.

## Manifest contract

`capture-manifest.json` schema version 1 contains one or more capture records. Each scripted record
includes:

- Xcode version and build;
- macOS and iPhoneOS SDK versions and build identifiers;
- host OS version/build and architecture, but no host or developer-directory path;
- Metal Toolchain component build, `ToolchainInfo.plist` identifier, sanitized tool paths, and tool
  version strings;
- whether optional `fm` was present;
- frameworks that were absent or did not publish a Swift interface; and
- per-file kind, stable filename, normalized SDK/platform/toolchain-relative source, byte size,
  line count, capture time, and SHA-256 digest.

A filename may be owned by exactly one capture record. The script refuses these states:

- a capture-shaped file exists without a manifest entry;
- a manifest-owned file is missing or no longer matches its hash;
- a different Xcode, macOS/iPhoneOS SDK version or build, or Metal Toolchain identifier/component
  build attempts to claim an existing stable filename; or
- the same build produces different bytes for an existing managed filename.

These are intentional stops. Do not bypass them by deleting the manifest or editing a hash to make
the check green; investigate the provenance change first.

## Recovering from an interrupted capture

New artifacts are copied into the destination before the merged manifest is written. A capture
killed in that window leaves files the manifest does not own, and every later run stops with
`destination contains unmanaged capture artifacts` (or, if the manifest landed but a copy did not,
`manifest-managed artifacts are missing`). Nothing is lost — a same-build recapture reproduces
identical bytes — so recovery is mechanical:

1. `git status notes/sdk-interfaces/` — the stray files are untracked (or the manifest is locally
   modified).
2. Delete the artifact files named in the error, or `git restore notes/sdk-interfaces/` to return
   both files and manifest to the committed state.
3. Re-run `./scripts/dump-sdk-interfaces.sh --check-only`, then the capture. The same selected
   build re-produces the same artifacts and manifest entries.

For a non-git destination (a `--dest` candidate directory), simply delete the directory and
capture again.

## Reviewing and promoting a new Xcode seed

Several Xcode beta, RC, and GM seeds can all report SDK `27.0`. Stable SDK-version filenames alone
cannot distinguish them, so automatic replacement would destroy the evidence boundary this
manifest establishes.

Use this workflow:

1. Run `./scripts/diff-interfaces.sh`. It captures into a temporary destination and compares those
   bytes directly to the requested git revision, leaving this directory untouched.
2. If the candidate must survive beyond that command, capture it into a new empty directory with
   `./scripts/dump-sdk-interfaces.sh --dest <empty-candidate-directory>`.
3. Review declaration drift, raw diffs, Xcode/SDK identity, the Metal Toolchain record, and all
   candidate hashes.
4. Promote in a dedicated reviewed change: replace only the affected stable artifacts; remove those
   paths from the prior capture record; append the candidate capture record and its file entries;
   retain the 26.5 and unrelated legacy records. Do **not** replace the tracked manifest wholesale
   with the candidate manifest, because a standalone candidate does not contain earlier captures.
5. With the promoted Xcode still selected, run `./scripts/dump-sdk-interfaces.sh --check-only`, then
   run the normal diff again. Both must pass before guide claims are updated.

Git history remains the archive for the superseded bytes. The stable working-tree paths keep guide
citations and symbol extraction deterministic, while the reviewed manifest transition makes the
change of evidence source explicit.

## Backfilled evidence and its limits

The initial files predate this manifest, so their provenance has been backfilled without inventing
facts. A known calendar date is stored as `documented_capture_date`; `captured_at` remains `null`
when no exact timestamp was recorded:

- The 26.5 interface files attest their SDK version in filenames and headers, but their Xcode build,
  capture time, host build, iPhoneOS SDK, and component state were not recorded. Those fields are
  `null` under `legacy-macosx-26.5-provenance-partial`.
- Repository notes attest that the 27.0 interfaces were captured on 2026-07-29 from Xcode 27.0 beta
  build `27A5228h` on macOS 26.5.2. A 2026-07-31 byte-for-byte check against the still-selected
  Xcode backfilled macOS SDK build `26A5388f` and normalized source paths. The original run did not
  record an exact time, host build, iPhoneOS SDK version/build, or Metal Toolchain identity, so
  those unknowns remain explicit.
- `coreai-build-help-27.0-beta.txt` is a separate documented 2026-07-31 legacy capture from the
  optional Metal Toolchain. It includes validation-oracle material beyond the deterministic help
  surface generated by the new script. Its original embedded home path was replaced with the stable
  `Metal.xctoolchain/usr/bin/coreai-build` form; the manifest hashes the sanitized file.

`FoundationModels-26.5-key-declarations.md` is a derived excerpt, not a raw interface. It remains
manifest-managed so edits cannot masquerade as the original evidence.
