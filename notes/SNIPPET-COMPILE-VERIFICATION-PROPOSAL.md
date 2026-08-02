# Implementation record: compiler-verifying every Swift snippet

**Status: implemented and current as of 2026-08-01.** The proposal below became
`scripts/verify-snippets.py`, `scripts/verify-snippets.sh`, the committed markers throughout
`guides/`, and `notes/snippet-verification/{results.tsv,report.md}`. Canonical usage and marker
grammar now live in `notes/snippet-verification/README.md`; this file records why the system exists
and how the rollout happened.

## The problem

The guides currently contain **1,354 fenced Swift code blocks**. The earlier estimate of roughly
1,900 counted generated indexes and non-canonical matches. The 2026-07-29 verification pass checked
the *claims* around them against the captured `.swiftinterface` files — but interface-reading
verifies spellings one at a time,
by hand, and never composes them. A snippet can cite four individually-correct symbols and still
not compile (wrong argument order, missing `await`, an overload that doesn't exist with that
combination). The verifier now catches that composition class and re-checks snippets when a guide
is edited or a new beta lands.

The key insight from this machine's constraints: **you do not need a running macOS 27 to
type-check code against the macOS 27 SDK.** `swiftc -typecheck` needs only the SDK and the
toolchain, both of which are installed. Compile-verification is the single biggest evidence
upgrade available without new hardware.

## What it does

`scripts/verify-snippets.py`, delegated to by a small shell driver:

1. **Extracts** every fenced Swift block from guides/, tagged with file, line, and the fence's
   info string.
2. **Classifies** each block by explicit marker: verified targets, expected failures,
   illustration, or an explicit contextual prelude dependency.
3. **Wraps** fragments in a minimal file-scope, async-body, or mixed harness. `wrap:none` is
   genuinely verbatim and therefore rejects injected `imports:`.
4. **Type-checks** each against every marker-requested target:
   - 26.5: `swiftc -typecheck -sdk <Xcode 26.6's MacOSX26.5.sdk> -target arm64-apple-macos26.5`
   - 27.0-beta: `swiftc -typecheck -sdk <Xcode-beta's MacOSX27.0.sdk> -target arm64-apple-macos27.0`
   - iOS-only API (App Intents schemas, some Speech): `-target arm64-apple-ios27.0-simulator`
     against the iPhoneOS/Simulator SDK.
   - Cross-import overlay snippets need both parent imports present — the wrapper emits them;
     this is also exactly how the overlay requirement gets *tested* rather than asserted.
   - `27-on-26` and `sim27-on-26` separate SDK generation from a 26.0 deployment floor.
5. **Reports** a deterministic TSV and Markdown summary with exact toolchain identities, mapped
   source lines, per-guide totals, and explicit failure diagnostics. Current baseline: 1,354
   fences = 192 `VERIFIED` + 2 `MIGRATION-PROVEN` + 2 `XFAIL-PROVEN` + 487 `ILLUSTRATIVE` +
   671 `PRELUDE-NEEDED`, with zero unclassified, parse, or marker errors.

## The marker convention (the real work)

Compile status must be *declared*, not guessed. Extend the fence info string:

    ```swift compile:27          — must type-check against the 27.0 SDK
    ```swift compile:26,27       — must type-check against both (migration guides)
    ```swift compile:27 wrap:none    — a complete file; no harness wrapper
    ```swift compile:27 imports:Vision,FoundationModels   — extra imports for the wrapper
    ```swift xfail:26 compile:27 — prove an older failure and newer success
    ```swift defines:FEATURE     — pass a declared custom condition with -D
    ```swift illustrative        — never compiled (pseudocode, elided bodies, API-sketches)
    ```swift prelude:guide-context — classified contextual excerpt, not compiled alone
    ```swift compile:sim27       — iOS-simulator target

Info strings after the language tag are invisible in rendered markdown, so this costs readers
nothing. Unmarked `swift` fences are reported as UNCLASSIFIED — the backlog metric. Python,
bash, and Metal fences are out of scope for v1 (Metal snippets can join later via
`xcrun metal -std=metal4.0 -c` now that the Metal Toolchain is installed; Python/MLX snippets
would need the mlx wheel pinned and are a separate proposal).

## Completed rollout

1. The extractor, wrapper, runner, changed-file selection, toolchain discovery, and report writer
   were implemented with Linux-safe unit coverage.
2. Guess mode bootstrapped the inventory, after which all 1,354 fence-info strings were reviewed.
   Mechanical marker changes were kept separate from substantive Swift repairs.
3. Every failed guess was triaged: each failing block was
   either (a) a real guide bug — fix the snippet and cite the compiler as evidence, (b) a
   fragment needing a smarter wrapper or imports — mark accordingly, or (c) deliberately
   illustrative — mark `illustrative` so it is never counted as verified again.
4. The verifier is wired into `notes/NEXT-BETA-CHECKLIST.md`: re-run the
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

## Current boundaries and risks

- The 671 `PRELUDE-NEEDED` fences deliberately remain a contextual backlog. Shared prelude files
  were not invented merely to turn excerpts green.
- Type-checking against a beta SDK on a 26.5 host is supported and fast (no linking, no running),
  but concurrency-heavy snippets may need `-swift-version` pinning to match the guides' assumed
  language mode; make it a marker (`lang:6`).
- The 27.0 SDK is a beta: a snippet can be *correct for release* and fail on the beta (or vice
  versa). The verifier's verdict is always "against 27A5228h", never "against iOS 27" — the same
  honesty rule the corpus already uses for interface evidence.
- CI can run the Python contract tests everywhere. Real SDK compilation remains a local Xcode
  gate until a runner with both required toolchains exists.

## Acceptance snapshot

On 2026-08-01 the full corpus passed against the installed Xcode 26/27 toolchains. Runs with
`--jobs 1` and `--jobs 8` produced byte-identical TSV and Markdown output. The focused verifier
and DocC tooling are covered by the repository's 69-test Python suite. Future changes belong in
the canonical README and tests; this implementation record is not a second grammar specification.
