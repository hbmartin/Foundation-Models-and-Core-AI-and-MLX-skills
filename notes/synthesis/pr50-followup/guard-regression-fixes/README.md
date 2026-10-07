# Defect reporting and Core AI verification follow-up

Evidence date: **2026-10-06**. Implementation and separately reviewed runner:
`893624e9a09adf991d87c191b91795986a82b422`. Starting revision:
`406b8dbc1aeb4e3420754dcfcb8f9f2998ca675e`. Shared reporter comparison base:
`4714a9a4aeb91a8984dc8b8f9dcb12f518c5e1cb`.

This follow-up addresses the fourteen pasted review comments. It supersedes the
negation and reference-association behavior described in the earlier
[guard-repair record](../guard-repair/README.md). Earlier native results and
review dispositions retain their original provenance.

## Repairs

| Comments | Result |
|---|---|
| 1–2 | Coordinated references share their predicates and metadata. Separately asserted references retain local state and dates. Leading clause dates are preserved, explicit local dates override them, and directly preceding state words belong to the following reference. The mlx#3757 sighting regains its 2026-08-23 date; mlx-lm#1444 regains CLOSED. |
| 3–4 | Shared reporting ignores negated states instead of inferring their opposite. Negation recognizes been, intervening adverbs, and straight/curly contractions. The focused #49 guard independently checks affirmative OPEN and negated CLOSED. The been gap existed before the reviewed patch. |
| 5–6 | #49 predicates are selected by repository/number rather than literal reference spelling. URLs, qualified references, mapped bare references, coordinated history, silently miscompiles, and is still miscompiling are covered. Neighboring references and Markdown list items cannot donate historical exemptions. Quoted issue titles remain exempt. |
| 7–8 | Shape predicates can precede or follow their shape; negated predicates are ignored. Overwrite negation recognizes the missing contractions and respects sentence/list boundaries while allowing wrapped prose and dotted filenames. |
| 9 | Finalization runs through finally. Keyboard interruption records interrupted and returns 130; cancellation and other escaping base exceptions record interrupted before propagating. Completed checkpoints survive; later fixtures do not run after cancellation. Publication failure retains the last successful checkpoint and returns nonzero. |
| 10 | Atomic record publication preserves existing modes and uses 0666 masked by the process umask for new files, retaining flush/fsync and temporary-file cleanup. |
| 11 | The protected log1p result must have exactly one user. Explicit boundary diagnostics and selective exclusion, entry-cast, exit-cast, and extra-user controls supplement the existing overflow no-op control. The local exit variable is renamed exit_cast. |
| 12 | The canonical Part 8 classification distinguishes affected 0.4.1 from tested fixed 0.4.3 and qualifies apple/coreai-torch#49. Indexes and both affected skills are regenerated. The generated index remains excluded from the guard. |
| 13–14 | Paragraph analysis reuses normalized reference spans and clause boundaries. Fence opener validity uses the existing match and is shared with the callout extractor, preserving its blockquote policy. |

CLI flags, JSON schema version/fields, legacy TSV columns, sighting ordering,
and centered display context remain compatible. claimText now includes the
shared text of coordinated lists; the two affected structured golden values
were reviewed and updated. No status ledger or dependency is introduced.

## Complete corpus comparison

Both readers receive the **same guide tree at the implementation revision**.
All **1,002 sightings** and **413 grouped references** preserve their keys and
order. Thirteen state/confidence changes relative to the base were reviewed:

- Ten previously unclaimed members of explicit lists inherit CLOSED or MERGED.
  Their repositories remain unresolved, so their verdicts remain AMBIGUOUS.
- Two mlx#3856 sightings now share the CLOSED/OPEN predicates of their paired
  mlx#3887 references. This exposes conflicting historical/current guide claims
  using the reporter's existing aggregation policy.
- mlx PR #3828 no longer borrows CLOSED from the following mlx-lm#1444 reference.
  That word directly prefixes the latter issue. No replacement state is inferred.

All claim dates match the base. The two regressions relative to 406b8db are
separately recorded. mlx#3757 already retained a grouped date through another
sighting; losing its individual date did not change that grouped value.

[Corpus comparison](corpus-comparison.json) accounts for every changed state,
date, confidence, diagnostic, and grouped value. The valid issue/PR state matrix
records possible verdict changes deterministically; **no fresh live GitHub
status is asserted**. The remaining historical/current conflict is exposed for
review rather than changing the reporter's broader aggregation policy.

## Validation

| Check | Result |
|---|---|
| Full portable discovery, Python 3.14 | 348 tests pass |
| Focused suites, Python 3.11 / 3.12 / 3.14 | 73 tests pass in each interpreter |
| Native model-export profile, run first | 38 checks: 22 passes, 16 designated rejections, zero failures |
| Native standalone profile, run second | 38 checks: 22 passes, 16 designated rejections, zero failures |
| Executed example provenance | Five example hashes match the implementation in both profiles |
| Generated skills | 10 skills, 142 files, 8,444 links, 80 trigger evaluations verified |
| Callout identities and bodies | All 1,785 preserved |
| Python fences | 464; only compression-native-fixtures changed and was executed in both profiles |
| Swift fences | All 1,360 identities and bodies preserved; no fresh compilation claimed |
| Anchors and current-state blocks | 17 part READMEs and four generated blocks verified |
| Primary checkout | HEAD, status, file set, and SHA-256 bytes of 458 files unchanged |
| Whitespace | git diff --check passes |

Both native profiles use Python 3.12.14, Core AI 1.0.0b3, coreai-torch 0.4.3,
coreai-opt 0.3.0, NumPy 2.4.6, and scikit-learn 1.9.1. Model-export uses Torch
2.9.0 / TorchAO 0.17.0; standalone uses Torch 2.11.0 / TorchAO 0.18.0. Package,
OS, Xcode, SDK, source revision, runner revision, and helper hashes are captured
in each fresh native record. Existing environments were reused without installs.

See [portable validation](portable-validation.json),
[model-export](native-model-export.json), [standalone](native-standalone.json),
[reconciliation](reconciliation.json), [Python fence hashes](python-fence-hashes.tsv),
[callout reconciliation](callout-reconciliation.json),
[preflight](preflight.json), and [primary preservation](primary-preservation.json).

## Reproduction

Run portable checks from the implementation checkout:

```sh
python3.14 -B -m unittest discover -s scripts/tests -p 'test_*.py'
# Repeat the following with python3.11, python3.12, and python3.14:
python3.12 -B -m unittest scripts.tests.test_defect_statuses \
  scripts.tests.test_coreai_examples scripts.tests.test_platform_refresh_consistency \
  scripts.tests.test_coreai_native_controls
python3 scripts/verify-skills.py
python3 scripts/current-state.py render --check
python3 scripts/anchor-section-links.py guides
git diff --check
```

For native execution, use separate clean source and reviewed runner checkouts
at **893624e9a09adf991d87c191b91795986a82b422**, with the existing pinned profiles.
The later evidence-only commit does not change executable source or guide
fences. Run model-export first, wait for its completion, then run standalone:

```sh
<profile-python> -I <reviewed-runner>/scripts/verify_coreai_examples.py \
  --source-repo <clean-source-at-893624e> \
  --reviewed-revision 893624e9a09adf991d87c191b91795986a82b422 \
  --compression --out <fresh-external-profile-output>/record.json
```

The primary checkout's preexisting edits are preserved. No push, merge,
publishing, automation changes, or fresh Swift compilation are included.
