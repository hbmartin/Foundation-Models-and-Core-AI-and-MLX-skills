# Proposal: compiler-verify every Swift snippet in the guides

**Status: proposal, 2026-07-31.** Nothing described here exists yet. The prerequisite toolchain
(Xcode 27.0 beta, both SDK interface sets) is already on this machine.

## The problem

The guides contain on the order of **1,900 fenced Swift code blocks** (`grep -c` of ```` ```swift ````
fences across guides/). The 2026-07-29 verification pass checked the *claims* around them against
the captured `.swiftinterface` files — but interface-reading verifies spellings one at a time,
by hand, and never composes them. A snippet can cite four individually-correct symbols and still
not compile (wrong argument order, missing `await`, an overload that doesn't exist with that
combination). Today nothing catches that, and nothing re-checks snippets when a guide is edited
or a new beta lands.

The key insight from this machine's constraints: **you do not need a running macOS 27 to
type-check code against the macOS 27 SDK.** `swiftc -typecheck` needs only the SDK and the
toolchain, both of which are installed. Compile-verification is the single biggest evidence
upgrade available without new hardware.

## What it would do

A `scripts/verify-snippets.py` (plus a small driver shell script) that:

1. **Extracts** every fenced Swift block from guides/, tagged with file, line, and the fence's
   info string.
2. **Classifies** each block by an explicit marker convention (see below): complete / fragment /
   illustrative / pseudocode / BEFORE-26 / AFTER-27.
3. **Wraps** fragments in the minimal harness their marker declares (imports + an `@available`
   func body — most guide snippets are expression- or statement-level).
4. **Type-checks** each against one or both SDKs:
   - 26.5: `swiftc -typecheck -sdk <Xcode 26.6's MacOSX26.5.sdk> -target arm64-apple-macos26.5`
   - 27.0-beta: `swiftc -typecheck -sdk <Xcode-beta's MacOSX27.0.sdk> -target arm64-apple-macos27.0`
   - iOS-only API (App Intents schemas, some Speech): `-target arm64-apple-ios27.0-simulator`
     against the iPhoneOS/Simulator SDK.
   - Cross-import overlay snippets need both parent imports present — the wrapper emits them;
     this is also exactly how the overlay requirement gets *tested* rather than asserted.
5. **Reports**: a TSV + markdown summary (per guide: N blocks, N verified-26.5, N verified-27.0,
   N illustrative-by-declaration, N FAILING with the first error line). Failing blocks are work
   items: either the guide is wrong (fix it) or the block is genuinely illustrative (mark it).

## The marker convention (the real work)

Compile status must be *declared*, not guessed. Extend the fence info string:

    ```swift compile:27          — must type-check against the 27.0 SDK
    ```swift compile:26,27       — must type-check against both (migration guides)
    ```swift compile:27 wrap:none    — a complete file; no harness wrapper
    ```swift compile:27 imports:Vision,FoundationModels   — extra imports for the wrapper
    ```swift illustrative        — never compiled (pseudocode, elided bodies, API-sketches)
    ```swift compile:sim27       — iOS-simulator target

Info strings after the language tag are invisible in rendered markdown, so this costs readers
nothing. Unmarked `swift` fences are reported as UNCLASSIFIED — the backlog metric. Python,
bash, and Metal fences are out of scope for v1 (Metal snippets can join later via
`xcrun metal -std=metal4.0 -c` now that the Metal Toolchain is installed; Python/MLX snippets
would need the mlx wheel pinned and are a separate proposal).

## Rollout plan

1. **Build the extractor + wrapper + runner** (a day of work; the extraction machinery in
   scripts/extract-callouts.py is the pattern).
2. **Dry run in guess mode**: attempt every unmarked block with a default wrapper against 27.0,
   report the pass rate. Passing blocks get `compile:27` markers added mechanically. This
   bootstraps the inventory without hand-marking ~1,900 fences: expect a substantial fraction to
   pass as-is; the interesting output is the failures.
3. **Triage failures** (agent-assisted, like the callout classification): each failing block is
   either (a) a real guide bug — fix the snippet and cite the compiler as evidence, (b) a
   fragment needing a smarter wrapper or imports — mark accordingly, or (c) deliberately
   illustrative — mark `illustrative` so it is never counted as verified again.
4. **Wire into the beta ritual**: `notes/NEXT-BETA-CHECKLIST.md` gains a step — re-run the
   verifier against the new SDK; any block that *was* green and turns red is API drift caught the
   day the beta lands, with the failing symbol named by the compiler.

## What this buys, concretely

- Upgrades ~hundreds of `✅ SDK-verified` (interface-read) claims to compiler-proven, wholesale.
- Catches composition errors interface-reading cannot see (the class of bug the corpus itself
  documents in Apple's own samples — e.g. the Speech snippet passing `AVAudioFormat?` where a
  non-optional is required was found by *reading*; a compiler finds all of these at once).
- Turns each future beta into a one-command drift report instead of a re-read.
- Produces an honest, queryable inventory of which snippets are load-bearing verified code vs.
  illustration — a distinction the guides currently make in prose only.

## Costs and risks

- Wrapper design is the fiddly part: fragments referencing guide-local types (`struct Probe`,
  `myTool`) need per-block context or a shared prelude of stub types; expect a `prelude:` marker
  or per-guide prelude files for the worst cases. Budget most of the triage time here.
- Type-checking against a beta SDK on a 26.5 host is supported and fast (no linking, no running),
  but concurrency-heavy snippets may need `-swift-version` pinning to match the guides' assumed
  language mode; make it a marker (`lang:6`).
- The 27.0 SDK is a beta: a snippet can be *correct for release* and fail on the beta (or vice
  versa). The verifier's verdict is always "against 27A5228h", never "against iOS 27" — the same
  honesty rule the corpus already uses for interface evidence.
- CI: nothing here needs GitHub Actions to be useful (it runs locally in minutes), but if the
  repo ever gets macOS runners with the beta Xcode cached, the whole thing is `verify-snippets.sh
  --changed` on PRs.

## Decision needed

Approve the marker convention (or amend it), then the build can proceed: extractor + runner
first, guess-mode dry run second, triage third. The dry-run report is the natural first
deliverable — it costs nothing to look at and sizes the triage backlog precisely.
