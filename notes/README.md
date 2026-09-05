# Notes index

Start here for current project state. Dated research files preserve what was known when they were
written; operational files below are the maintained source of truth for what to run next.

## Current snapshot

<!-- current-state:notes:start -->
**As of 2026-09-05**, the corpus has 60 reference guides in 17 parts, 1788 classified callouts (1426 concrete silent failures), 1213 indexed symbols, and 10 generated skills.

Snippet verification covers 1359 fences: 486 `ILLUSTRATIVE`, 2 `MIGRATION-PROVEN`, 677 `PRELUDE-NEEDED`, 192 `VERIFIED`, 2 `XFAIL-PROVEN`. Blocker: SDK-26 target Xcode is not installed at /Applications/Xcode.app/Contents/Developer.

Installed: macOS 27.0 (26A5406e), Xcode 27.0 (27A5237l), and `fm` at `/usr/bin/fm`. Latest observed: Xcode 27 beta 6 (27A5252f), iOS 27.0 beta 8 (24A5430a), and macOS 27.0 beta 8 (26A5425a). Installed Xcode build 27A5237l trails observed build 27A5252f. Installed macOS build 26A5406e trails observed build 26A5425a. Installed iOS Simulator build 24A5408d trails observed build 24A5430a.
<!-- current-state:notes:end -->

Historical evidence and open writing work remain in the dated notes and
[`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md). Machine-readable state lives in
[`current-state.json`](current-state.json); update it and run `scripts/current-state.py render
--write` instead of hand-editing the block above.

## Maintained operational notes

| File | Use it for |
|---|---|
| [`FRESHNESS-RUNBOOK.md`](FRESHNESS-RUNBOOK.md) | Daily, weekly, and release-event evidence refreshes; includes the known defect-state parser false positives. |
| [`NEXT-BETA-CHECKLIST.md`](NEXT-BETA-CHECKLIST.md) | Exact Xcode/SDK/interface/snippet/probe ritual for a new beta or host update. |
| [`NEEDED-FROM-A-MACOS-27-MACHINE.md`](NEEDED-FROM-A-MACOS-27-MACHINE.md) | The sole remaining original machine-dependent item (manual Instruments UI) and the closed-run record. |
| [`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md) | Open writing work carried forward from the 2026-08-02 harvest — evidence already on disk, guides not yet updated. Preserves the now-superseded ordinal re-keying trap as history. |
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

Update `current-state.json` and render the generated status blocks. Regenerate verifier and index
artifacts through their scripts. For issue/PR freshness, inspect the cited sentence before editing;
the reporter bounds state parsing and marks uncertain claims AMBIGUOUS, but its verdicts remain
review leads rather than edit instructions.
