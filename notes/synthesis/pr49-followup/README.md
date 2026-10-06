# PR #49 follow-up and final SDK evidence

Reviewed PR #49 revision: `2b12a8544deb7b7c4a807d1e83ad35be2079dabf`.
Merged main revision: `425c1544b53442b004eba4d71dffc2368da6822a`; both have tree
`acdeb9785ec2a3b034fcee4d83380a0a3536e54b`. Evidence date: **2026-10-06**.

## Review dispositions

All eleven findings apply to both the reviewed tree and merged main. The security finding is
conditional on executing an unreviewed candidate; reviewed examples intentionally execute with
host privileges. The implemented policy explicitly selects a reviewed immutable source revision
from a separate trusted clean runner with `python -I`. Dependency isolation is not a sandbox.

| Review finding / comment ID | Action | Evidence and validation |
|---|---|---|
| Superagent `4197989165` | Require immutable source selection, isolated interpreter, clean separate runner/source; capture approved Git blobs and load only runner helpers | Trust-selection, candidate shadowing, callback, replacement-ref and dirty-index regressions; manual native profiles recorded separately |
| CodeRabbit `4198114488` | Correct Part 7 rewrite quick reference | Pinned converter `b51fd006` and b3 module exit; portable contract scan |
| `4198114496` | Escape `format_summary` union separator | Part 9.1 table retains one signature cell |
| `4198114521` | Mark palettizer step supported inside training_mode | opt `189612be`, actual named PAT schedule fixture |
| `4198114527` | Complete numeric formats footer | Original source citations and historical benchmark context retained |
| `4198114541` | Align Part 10 stages 6–7/8/9 and links | Anchor verification; existing section numbers retained |
| `4198114547` | Generic Part 17 artifact producer uses b3 | b2 configs, source-ledger rows and incidents explicitly historical |
| `4198114558` | section() raises ValueError naming missing heading | Missing/existing heading regression |
| `4198114583` | Explicit optimizer violation report; reject optimized Python | Paths/lines and -O/-OO trust failures tested |
| `4198114589` | Separate replacement proof from read-only gate | A + sentinel replaced by numerically different B; runtime B parity and independent non-mutation check |
| Review `PRR_kwDOTlQmW88AAAABQ8NWkg`, outside-diff Part 8 custom-kernel checklist | Current conversion/rewrite wording | Historical source quotation retained; adapted current checklist |

## SDK capture promotion

Reviewed the 2026-10-06 final Xcode candidate (`27A266a`): macOS SDK `27.0/26A425`,
iPhoneOS SDK `27.0/24A430`, Metal component `27A266a` / `32023.921.5`.
Seventeen current 27.0 paths transfer manifest ownership to that capture. SDK 26.5 and
unrelated legacy captures remain. Superseded bytes remain at the reviewed PR #49 SHA above.
Fifteen Swift interfaces change compiler flags; Evaluations additionally removes the deprecated
EvaluationError.metricsNotFound case and adds EvaluationRunErrors and EvaluationResult.errors.
The current fm help capture has the seven-command system surface. Fresh capture hashes are
verified by the manifest preflight; declaration drift is reviewed independently of toolchain flags.

## Model-free Evaluations observations

Final Xcode 27 host, macOS 27.0 (`26A428`), 2026-10-06:

| Case, four samples | Inference failures | Evaluator failures | hasFailures | anyInferenceProduced | Rows / metric-column count | Mean |
|---|---|---|---|---|---|---|
| Clean | 0 | 0 | false | true | 4 / 4 | 1.0 |
| One subject throws | 1 | 0 | true | true | 4 / 4 | 1.0 |
| One evaluator throws | 0 | 1 | true | true | 4 / 4 | 1.0 |
| Every subject throws | 4 | 0 | true | false | 4 / 4 | -1.0 |

The original five-row/two-subject-failures fixture also completes with mean 1.0 and reports two
inference failures. Row/column counts alone do not flag these failures. Error checks and coverage
checks address separate concerns: ignored scores and loader omissions still require fixture and
metric coverage checks. These canned subjects/evaluators establish no model-judge retry policy.

## Daily evidence findings

The provider example now uses LanguageModelCapabilities([.toolCalling]); it is an adaptation.
Fresh compilation validates the current SDK contract separately from the historical upstream
runtime claim. ImageReference current overview/member captures agree on resolved(in:), with
sequence input; beta-4 resolve spelling remains historical. Capture failures/missing declarations
fail with a durable partial manifest. Part 15 records apple/coreai-models#55 closed August 27:
crash resolved, residual GPU fallback separately reported, no categorical exit-139 diagnosis.
Part 13's citation is qualified as ml-explore/mlx-swift-lm#434.

Collector routing: explicit DEVELOPER_DIR, then system-selected Xcode; saved environment values
are prior evidence. Swift verification checks SDK generation and supports explicit per-generation
overrides. Partial mode records unavailable targets, completes available checks, and returns 3.
Discussion URLs use GraphQL and separate reference-kind groups; TSV columns remain unchanged.
Neighboring-reference state leakage is fixed with actual prose fixtures and explicit shared lists.
Unresolved repository mappings remain a backlog, not automatically inferred corrections.

## Release observations and limits

[Apple's dated release list](https://developer.apple.com/news/releases/) reports parallel tracks:
Xcode 27.2 beta 2 (`27B5028f`, September 28) and Xcode 27.1 RC (`27A9275`, October 5).
iOS 27.2 beta 3 (`24B5099f`) and macOS 27.2 beta 3 (`26B5101f`) are dated October 5.
The latest Simulator build remains unknown: a public iOS OS build is not Simulator evidence.
Installed runtime identities are recorded independently. No toolchain installation, schedule
resumption, merging, or publication is included. The daily schedule remains paused/report-only.

The independent read-only security review identified nested-tree substitution under an approved
Git OID. The runner now verifies raw commit, every descendant tree, and every leaf blob digest.
A focused corrupted-object regression confirms rejection before parsing/execution. The review
session did not produce a complete final report; this is a bounded finding/fix, not a full scan.

Fresh Swift run: 1,360 fences, 486 illustrative, 677 prelude-needed, 189 verified,
1 migration-proven, 2 xfail-proven, 5 toolchain-unavailable; exit 3, no unexpected failures.
Final provider and new error-summary helper compiled. Host default: 47 tests, 26 skips, 0 failures.
The first Simulator destination (iPhone 17 Pro) was unavailable. The available iPhone 18 Pro run
hit the 60-second allowance in Spotlight's direct call (linguistic-asset sandbox entitlement
failure reported first); it was stopped and the independent bounded lane excludes that call.
This timeout is retained as unavailable runtime coverage, not successful verification.

The bounded Simulator lane completed **39 tests / 22 skipped / 0 failures** with Spotlight's
direct call excluded. The four new error-counter cases and original subject fixture agree with
host observations above. The skipped/excluded count is explicit; no complete Spotlight runtime
coverage is claimed. The refreshed live defect report contains 1,002 sightings / 416 groups,
zero unreachable or state-changed groups, and 309 sightings with unresolved repository mappings.
237 groups have ambiguity diagnostics and remain report-only.

Final immutable native execution and reconciliation records follow in validation.md.
