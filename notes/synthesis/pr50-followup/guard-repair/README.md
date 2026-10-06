# Core AI verifier and claim-guard repairs

Evidence date: **2026-10-06**. Base implementation:
`4714a9a4aeb91a8984dc8b8f9dcb12f518c5e1cb`. Repaired implementation and separately
reviewed clean runner:
`e4a24f663b37b96585310cf3001f90c65f6942c1`. The final reference-local
historical-tense guard is at `7380762be9609969b16db7aef97b613597090c72`; its added
regressions are included in the portable validation. Native helpers and all five
executed guide fences are byte-identical to the native-tested revision.

This evidence supplements the earlier [PR #50 follow-up](../README.md). Its
native records still describe `2367dc31`; they are retained as historical
measurements. The records in this directory describe the repaired implementation.

## Repairs and review dispositions

| Comment | Result |
|---|---|
| 1: unresolved bare #49 and stale callout | Unresolved references require repository qualification. The callout names `apple/coreai-torch`, describes 0.4.1 in the past tense, records the tested 0.4.3 resolution, and recommends both square and asymmetric inputs. |
| 2: negation | Straight/curly contractions and intervening adverbs are recognized. Not closed means open; not open means closed; not merged does not establish a state. |
| 3: shape explanation | Predicates are associated with their named shape. Correct square-failure/rectangular-success statements pass; reversed statements fail. |
| 4: overwrite regex | Inflections, cannot/can't, existing destinations, line wrapping, and dotted filenames are covered without matching “Note.” |
| 5: missing parts | The targeted guard scans Parts 7, 8, 9, 10, and 17. |
| 6: historical context leakage | Semantic checks use reference-local `claimText` and dates, rather than the centered display context. Neighboring history cannot exempt a current claim. |
| 7: serialization loss | Supported details are normalized; unsupported/non-finite values fail their fixture. Initial, per-fixture, and final records are published atomically. |
| 8: exit zero | Fixture `SystemExit(0)` is a failure and later fixtures continue. Setup exits and interruptions produce nonzero status; interruptions retain completed results. |
| 9: standalone false pass | A fresh directory prevents reuse of an earlier asset. The entrypoint must create an asset, and an independent comparison executes that asset against a reconstructed compressed reference. An inert entrypoint is rejected. |
| 10: weak overflow control | An untouched fp32 baseline stays finite. The exact standard/protected overflow graphs have asserted computation/input dtypes and boundary casts. A selective no-op on the overflow graph is rejected. |
| 11: helper drift | Both independently runnable helpers validate names, state, returned keys, finite inputs/outputs, and copied output ownership. Portable contract tests exercise both helpers. |
| 12: inline code hides headings | Both readers share a CommonMark backtick opener check; an info string containing backticks is not a fence opener. |
| 13: disposition provenance | The earlier fifteen dispositions remain relative to their recorded revision. Item-specific `fix_origin`, `fix_commit_sha`, and observation revisions distinguish fixes predating that follow-up from those made in it. Earlier observations are no longer called “current.” |
| 14: weak quoted-fence tests | Tests assert actual fence state and return to real headings after closure, alongside unquoted cases that the previous reader fails. |
| 15: generalized status guard | Deferred by user choice. These repairs keep #49 checking focused on Core AI; no repository-wide status ledger is introduced. |

## Recording interfaces

The native CLI and existing fixture fields/outcomes remain compatible. The JSON
record adds `run_status`: `running`, `passed`, `failed`, or `interrupted`. A killed
run may leave a complete checkpoint marked `running`; it does not claim completion.
Unsupported details cannot satisfy an expected negative-control exception.
Publication failure stops the run with nonzero status and preserves the last
complete checkpoint. Keyboard interruption exits with status 130.

The defect extraction JSON adds `claimText`; its existing fields, TSV columns,
reference ordering, and schema version are retained. The 240-character `context`
remains display text. Unresolved references are reported for qualification rather
than assigned an assumed repository. Closure still does not by itself establish
that a fix shipped.

## Validation

| Check | Result |
|---|---|
| Full portable suite, Python 3.14 | 343 tests pass |
| Focused suites, Python 3.11 / 3.12 / 3.14 | 68 tests pass in each interpreter |
| Model-export native profile | 34 checks: 22 passes, 12 designated rejections, zero failures |
| Standalone native profile, run second | 34 checks: 22 passes, 12 designated rejections, zero failures |
| Generated indexes, skills, current-state blocks, anchors | Pass; 10 skills, 142 files, 8,444 links, 80 trigger evaluations |
| Python fences | 464 fences, 145 named IDs; two changed named fences executed in both native profiles |
| Callout identities | All 1,785 preserved; one deliberately changed content hash and classification blurb |
| Swift fences | All 1,360 identities, bodies, and prior target verdicts preserved; no fresh compilation claimed |
| Primary checkout | HEAD, status, file set, and SHA-256 bytes of 458 tracked/non-ignored files unchanged |
| Whitespace | `git diff --check` passes |

Both native profiles use Python 3.12.14, Core AI 1.0.0b3, coreai-torch 0.4.3,
coreai-opt 0.3.0, NumPy 2.4.6, and scikit-learn 1.9.1. The model-export profile
uses Torch 2.9.0 / TorchAO 0.17.0; the standalone profile uses Torch 2.11.0 /
TorchAO 0.18.0. Runs were sequential on arm64 macOS 27.0 / 26A428, with Xcode
27.0 / 27A266a and macOS SDK 26A425.

The independently loaded standalone composite has maximum conversion error
`3.5762786865234375e-07`, measured against the compressed reference. Its separate
dense-versus-compressed error is `0.009537994861602783`. These are measurements
of this small deterministic fixture, with its own tolerances. The fp32 overflow
baseline and protected result are both 15.0; the ordinary fp16 result is infinite.

See [model-export](native-model-export.json), [standalone](native-standalone.json),
[portable results](portable-validation.json), [reconciliation](reconciliation.json),
[fence hashes](python-fence-hashes.tsv), [section hashes](part9-section-hashes.tsv),
and [primary preservation](primary-preservation.json).

## Reproduction

Run from the repair checkout:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
<python-3.11-or-3.12-or-3.14> -m unittest \
  scripts.tests.test_coreai_examples \
  scripts.tests.test_coreai_native_controls \
  scripts.tests.test_platform_refresh_consistency \
  scripts.tests.test_defect_statuses
python3 scripts/verify-skills.py
python3 scripts/current-state.py render --check
python3 scripts/anchor-section-links.py guides
git diff --check
```

Use clean source and separate reviewed runner checkouts at the implementation
revision; run the profiles sequentially with their pinned dependencies:

```sh
<profile-python> -I <trusted-runner>/scripts/verify_coreai_examples.py \
  --source-repo <clean-source-at-e4a24f6> \
  --reviewed-revision e4a24f663b37b96585310cf3001f90c65f6942c1 \
  --compression --out <external-output-directory>/results.json
```

The immutable revision selection establishes trust in the executed code; the
virtual environment isolates dependencies. Earlier device, Simulator, Swift,
performance, and SDK-26 records retain their original provenance. No merging,
publishing, or automation changes are included.
