# Notes index

Start here for current project state. Dated research files preserve what was known when they were
written; operational files below are the maintained source of truth for what to run next.

## Current snapshot — 2026-08-20

- The guide corpus has 60 reference guides in 17 parts and 1,359 classified Swift fences.
- The cross-cutting indexes carry **1,777 callouts, of which 1,415 are concrete silent failures**
  (`guides/README.md` hardcodes this pair — bump it when you regenerate).
- The last complete snippet verification is green: 192 `VERIFIED`, 2 `MIGRATION-PROVEN`,
  2 `XFAIL-PROVEN`, 485 `ILLUSTRATIVE`, and 678 `PRELUDE-NEEDED`; zero unclassified or verifier
  errors. A beta-5 rerun remains blocked only because the SDK-26 target Xcode is not installed at
  `/Applications/Xcode.app/Contents/Developer`.
- `transcripts/` holds 29 files after the 2026-08-02 harvest added sessions **328, 253, 297, 375,
  310 and 258**.
- Xcode 27 beta 5 (`27A5237l`), the Metal Toolchain, macOS 27 beta 5 (`26A5406e`), and iOS 27
  simulator runtime `24A5408d` are installed. The beta-5 baselines are 46 host tests (23 skips)
  and 39 simulator tests (19 skips).
- An attached iPhone 15 Pro (`iPhone16,1`, `D83AP`) on iOS 27 build `24A5408d` completed the first
  hardware baseline on 2026-08-20. It confirmed a 4,096-token on-device context, `h16p`, live-cache
  deletion failure until release, default cache placement under `Library/Caches/coreai-cache`,
  and several Foundation Models tool/error behaviors; exact results live in `probes/README.md`.
- A 2026-08-03 defect sweep folded four upstream closures into Parts 8/9/11/12/13: mlx#3883 and
  mlx#3924 closed unmerged (TF32 stays unannounced; the `tile_matmad_nax` missing-`else` is still
  at HEAD), mlx-lm#1566 closed with `generate_step` defaults unchanged, and mlx-swift-lm#358
  superseded by PR #453, which merged 2026-08-05 — the only one of the four to land a fix.
- The `fm` CLI and original physical-device questions are closed. The remaining item from the
  machine-dependency ledger is one manual Instruments GUI capture; probe-level residuals include
  cancellation with a genuinely slow Core AI asset and an entitled app-group cache run.
- Open *writing* work — evidence on disk, guides not yet updated — is tracked in
  [`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md). The largest item: **the Music Understanding
  framework has zero coverage anywhere in the series.**

## Maintained operational notes

| File | Use it for |
|---|---|
| [`FRESHNESS-RUNBOOK.md`](FRESHNESS-RUNBOOK.md) | Daily, weekly, and release-event evidence refreshes; includes the known defect-state parser false positives. |
| [`NEXT-BETA-CHECKLIST.md`](NEXT-BETA-CHECKLIST.md) | Exact Xcode/SDK/interface/snippet/probe ritual for a new beta or host update. |
| [`NEEDED-FROM-A-MACOS-27-MACHINE.md`](NEEDED-FROM-A-MACOS-27-MACHINE.md) | The sole remaining original machine-dependent item (manual Instruments UI) and the closed-run record. |
| [`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md) | Open writing work carried forward from the 2026-08-02 harvest — evidence already on disk, guides not yet updated. Includes the callout re-keying ritual and its ordinal trap. |
| [`snippet-verification/README.md`](snippet-verification/README.md) | Canonical marker grammar and verifier CLI behavior. |
| [`snippet-verification/report.md`](snippet-verification/report.md) | Latest exact toolchain identities and per-guide verification totals. |
| [`sdk-interfaces/README.md`](sdk-interfaces/README.md) | Capture-manifest contract and safe interface-evidence promotion workflow. |
| [`CORRECTIONS-PENDING.md`](CORRECTIONS-PENDING.md) | Historical correction register; despite the retained filename, all twelve items are applied. |

## Research and historical planning

- [`synthesis/RESEARCH-INDEX.md`](synthesis/RESEARCH-INDEX.md) maps the grounded transcript,
  documentation, forum, repository, and synthesis corpus and states its remaining evidence bounds.
- [`synthesis/PROPOSED-GUIDE-TOPICS.md`](synthesis/PROPOSED-GUIDE-TOPICS.md) and the three
  lens-specific proposals are historical planning artifacts. Their dated counts are not current
  completion state; use `guides/` as the authoritative content tree.
- [`SNIPPET-COMPILE-VERIFICATION-PROPOSAL.md`](SNIPPET-COMPILE-VERIFICATION-PROPOSAL.md) is now an
  implementation record. The canonical live contract is the snippet-verification README above.
- `transcripts/`, `web/`, `forums/`, and `repos/` are evidence snapshots. Preserve dated findings
  even when later work closes them; add a status banner or superseding note instead of rewriting
  the historical observation as though it had always been known.

## Maintenance rule

Update current status in this file and the owning operational note. Regenerate verifier and index
artifacts through their scripts. For issue/PR freshness, inspect the cited sentence before editing;
the reporter bounds state parsing and marks uncertain claims AMBIGUOUS, but its verdicts remain
review leads rather than edit instructions.
