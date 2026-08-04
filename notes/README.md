# Notes index

Start here for current project state. Dated research files preserve what was known when they were
written; operational files below are the maintained source of truth for what to run next.

## Current snapshot — 2026-08-03

- The guide corpus has 60 reference guides in 17 parts and 1,359 classified Swift fences.
- The cross-cutting indexes carry **1,780 callouts, of which 1,418 are concrete silent failures**
  (`guides/README.md` hardcodes this pair — bump it when you regenerate).
- Snippet verification is green: 192 `VERIFIED`, 2 `MIGRATION-PROVEN`, 2 `XFAIL-PROVEN`,
  485 `ILLUSTRATIVE`, and 678 `PRELUDE-NEEDED`; zero unclassified or verifier errors.
- `transcripts/` holds 29 files after the 2026-08-02 harvest added sessions **328, 253, 297, 375,
  310 and 258**.
- Xcode 27 beta 4 (`27A5228h`), the Metal Toolchain, and iOS 27 simulator runtime `24A5390f`
  are installed. The probe baselines are 46 host tests (34 skips) and 39 simulator tests (2 skips).
- The host updated to macOS 26.6 (`25G72`); the release-event ritual ran clean 2026-08-03 — no
  interface drift, no snippet drift, no PROBE-RESULT drift. iOS/Xcode 27 **beta 5** (expected
  ~2026-08-03) has not yet appeared and is the next freshness event — see `NEXT-BETA-CHECKLIST.md`.
- A 2026-08-03 defect sweep folded four upstream closures into Parts 8/9/11/12/13: mlx#3883 and
  mlx#3924 closed unmerged (TF32 stays unannounced; the `tile_matmad_nax` missing-`else` is still
  at HEAD), mlx-lm#1566 closed with `generate_step` defaults unchanged, and mlx-swift-lm#358
  superseded by open PR #453. None closed with a fix landing — the hazards they document stand.
- The remaining machine-dependent evidence is limited to the `fm` CLI on macOS 27 (now narrowed by
  third-party reports, not closed), one manual Instruments GUI capture, and physical-device
  Core AI probes. The on-device `contextSize` question is **answered by Apple** and no longer
  blocking.
- Open *writing* work — evidence on disk, guides not yet updated — is tracked in
  [`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md). The largest item: **the Music Understanding
  framework has zero coverage anywhere in the series.**

## Maintained operational notes

| File | Use it for |
|---|---|
| [`FRESHNESS-RUNBOOK.md`](FRESHNESS-RUNBOOK.md) | Daily, weekly, and release-event evidence refreshes; includes the known defect-state parser false positives. |
| [`NEXT-BETA-CHECKLIST.md`](NEXT-BETA-CHECKLIST.md) | Exact Xcode/SDK/interface/snippet/probe ritual for a new beta or host update. |
| [`NEEDED-FROM-A-MACOS-27-MACHINE.md`](NEEDED-FROM-A-MACOS-27-MACHINE.md) | The three remaining OS/UI/device evidence gaps and commands needed to close them. |
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
artifacts through their scripts. For issue/PR freshness, inspect the cited sentence before editing:
`refresh-defect-statuses.sh` can currently leak nearby state words across references.
