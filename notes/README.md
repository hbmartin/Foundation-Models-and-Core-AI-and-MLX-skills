# Notes index

Start here for current project state and maintained instructions. Stable releases lead; beta-only changes are labelled separately.

## Current snapshot

<!-- current-state:notes:start -->
**As of 2026-10-07**, the corpus has 60 reference guides in 17 parts, 1735 classified callouts (1392 concrete silent failures), 1201 indexed symbols, and 10 generated skills.

Snippet verification covers 1327 fences: 478 `ILLUSTRATIVE`, 2 `MIGRATION-PROVEN`, 661 `PRELUDE-NEEDED`, 184 `VERIFIED`, 2 `XFAIL-PROVEN`. Blocker: SDK-26 targets unavailable: /Applications/Xcode.app contains SDK 27. Fresh partial verification records available SDK-27 targets; unchanged historical SDK-26 verdicts retain their prior provenance.

Installed: macOS 27.0 (26A428), Xcode 27.0 (27A266a), and `fm` at `/usr/bin/fm` (no independent version; macOS build 26A428). Latest observed: Xcode 27.2 beta 2 (27B5028f), iOS 27.2 beta 3 (24B5099f), and macOS 27.2 beta 3 (26B5101f); SDK and runtime versions are recorded separately in the manifest, and `fm` has no independent version surface. Generated outputs: currentStateBlocks=current (2026-10-07), indexes=current (2026-10-07), skills=current (2026-10-07). Installed Xcode build 27A266a differs from observed build 27B5028f. Installed macOS build 26A428 differs from observed build 26B5101f.
<!-- current-state:notes:end -->

Historical evidence and open writing work remain in the dated notes and
[`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md). Machine-readable state lives in
[`current-state.json`](current-state.json); update it and run `scripts/current-state.py render
--write` instead of hand-editing the block above.

## Maintained operational notes

| File | Use it for |
|---|---|
| [`FRESHNESS-RUNBOOK.md`](FRESHNESS-RUNBOOK.md) | Report-only daily checks, weekly maintenance, and release-event evidence refreshes. |
| [`NEXT-BETA-CHECKLIST.md`](NEXT-BETA-CHECKLIST.md) | Exact Xcode/SDK/interface/snippet/probe ritual for a new beta or host update. |
| [`PLATFORM-UPGRADE-VALIDATION-2026-09-16.md`](PLATFORM-UPGRADE-VALIDATION-2026-09-16.md) | Promoted Mac/device findings, environment identity, freshness-job outcome, and remaining boundaries from the macOS/iOS upgrade run. |
| [`FOLLOWUP-BACKLOG.md`](FOLLOWUP-BACKLOG.md) | Open writing work carried forward from the 2026-08-02 harvest — evidence already on disk, guides not yet updated. Uses stable identities for current maintenance. |
| [`snippet-verification/README.md`](snippet-verification/README.md) | Canonical marker grammar and verifier CLI behavior. |
| [`snippet-verification/report.md`](snippet-verification/report.md) | Latest exact toolchain identities and per-guide verification totals. |
| [`sdk-interfaces/README.md`](sdk-interfaces/README.md) | Capture-manifest contract and safe interface-evidence promotion workflow. |

## Evidence and decisions

- [Research index](synthesis/RESEARCH-INDEX.md) maps primary evidence and remaining boundaries.
- [Current decisions](CURRENT-DECISIONS.md) retains distinctions that affect implementation.
- [Defect registry](defects.json) owns explicitly typed current issue, pull request, and discussion claims.
- [Core AI evidence](evidence/core-ai/README.md) retains current native results, immutable pins, hashes, and regression controls.
- [Instruments recording](../probes/INSTRUMENTS-RECORDING.md) owns the remaining manual UI task.
- Retain a dated snapshot only when it supports a current claim, supported-version migration, a workaround, or a distinct regression. Remove completed proposals and superseded review narratives; Git retains their history.

## Maintenance rule

Update `current-state.json` and render the generated status blocks. Regenerate verifier and index
artifacts through their scripts. For defect freshness, review the registry record and cited evidence
before changing recommendations. The reporter compares recorded state to live GitHub state;
closure alone never establishes remediation.

`defects.json` schema version 1 records a stable ID, typed GitHub URL, affected-version boundary,
guide file/anchor targets, and observed state/date. Unknown version boundaries remain explicit.
Resolution records keep disposition, release availability, demonstrated remediation, evidence URLs,
date, and rationale separate. A demonstrated fix requires reproduction evidence; a merge may remain
outside the verified release. Each active registered section has one `defect-ref` ID marker beside its warning; missing, duplicate,
unknown, or misplaced markers are rejected.
Ordinary historical citations remain source links.

After reviewing a registry edit, validate it with `scripts/refresh_defect_statuses.py --extract-only`
and regenerate indexes and skills. The defect reporter preserves its CLI flags, version-2 JSON fields,
and TSV columns; failed lookups also appear in `unreachableReferences` under `--changed-only`.
