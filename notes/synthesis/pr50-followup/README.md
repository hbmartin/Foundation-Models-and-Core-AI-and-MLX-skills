# Remaining Core AI review repairs

This page retains the original follow-up evidence at `2367dc31`. Subsequent
verifier and claim-guard repairs at `e4a24f6`, including fresh runs of both native
profiles, are recorded in [guard-repair evidence](guard-repair/README.md).

Evidence date: **2026-10-06**. Base: merged PR #50, main
`8972e4abeea713f233e55dd7e9b39073b4e90ada`. The original fifteen comments review
PR #49 at `2b12a8544deb7b7c4a807d1e83ad35be2079dabf`; later fixes were inspected
at PR #50 revision `d91f1f4f425ec32ba4f24618f311c3b40750b2a5` and its merged tree.

The reviewed implementation and separate clean trusted runner both use
`2367dc31a7c02ccf0f80f54454a35f5015d73234`. Native execution reads approved Git
blobs with `python -I`; it does not import helpers from the candidate checkout.
Selecting a reviewed commit establishes trust. A virtual environment isolates
dependencies; it does not restrict the executed examples' host privileges.

## Disposition of all fifteen comments

Validity describes the original reviewed target, independently of the remaining
action after PR #50. [Machine-readable dispositions](review-dispositions.json)
retain that distinction and the original evidence.

| Comment | Original validity | Action in this follow-up | Validation |
|---|---|---|---|
| 1: Part 7 “NO passes” | Confirmed | Preserve PR #50's successful module-exit rewrite guidance | Preservation regression; synchronized skill copy |
| 2: packed-intx PR status | Confirmed | §9.3 says `apple/coreai-torch#41` merged September 25; its fix is outside converter 0.4.3 | Immutable converter snapshot and merged PR evidence; preservation regression |
| 3: pipeline numbering/alignment | Confirmed | Preserve corrected stage headings/Contents; align stage-9 arrow with its stem | Stage-8/stage-9 column regression; anchor checks |
| 4: numeric-formats footer | Confirmed | Preserve the complete balanced footer and historical citations | Preservation regression; synchronized skill copy |
| 5: casting exclusions | Partial | Keep the historical quotation verbatim; add 0.3.0 `ignored_ops` guidance, distinct from unreleased automatic calibration | Pinned casting source and differential native fixture |
| 6: tied-weight limitations | Partial | Restore eager post-finalize re-tying failure and shared schedule cautions; separate graph fixes and priority-aware override observations | Both profiles reject re-tying with missing `right_inverse`; both forward orders resolve the tested override to int4 |
| 7: CI composite opt-out | Partial | Require keyword `required_composites`; explicit `()` opts out | Portable omitted/empty/satisfied/missing cases; native missing-rms_norm rejection |
| 8: incomplete composite example | Confirmed | Include asset loader, contracts, copied outputs, compressed-reference comparison and standalone invocation | Actual named fence and `__main__` invocation pass in both profiles |
| 9: application range assert | Confirmed | Materialize lengths; raise `ValueError` outside 2–32 before any asset access | Portable `-O` stubs prove no load; native lengths 1/33 reject with the designated diagnostic |
| 10: fenced headings | Partial | Use the existing fence-aware iterator for heading selection and termination | Backtick/tilde/blockquote boundaries, fenced comments/headings, missing heading; prior current scopes were not themselves truncated |
| 11: invalid Unicode names | Confirmed | Validate `NAME.isidentifier()` while retaining strings/comments, valid Unicode names and syntactic fragments | Focused tests pass on Python 3.11, 3.12 and 3.14; illustrative `…` tokens changed to Python `...` |
| 12: setup failure records | Confirmed | Enter recording lifecycle before package/toolchain/import work; compression dependencies are conditional | Missing-package/toolchain mocks produce JSON failure/nonzero status; migration-only avoids compression metadata |
| 13: stale-claim guards | Confirmed | Scan Parts 8/10/17 with offline reference boundaries, negation, case and dated-history handling; whole-word overwrite checks | Actual old text, “remains open”, “not OPEN”, neighboring references, historical status, outside-register prose and valid “Note” fixtures |
| 14: overwrite proof | Confirmed | Preserve independent A/sentinel/B replacement and read-only gate checks | Both profiles remove the sentinel, run the numerically different B, and independently preserve supplied-asset bytes |
| 15: casting proof | Confirmed | Separate standard/excluded exports; assert computation dtypes and entry/exit/downstream casts; add exp(15) overflow control | Both profiles pass; no-op and ignored-exclusion substitutes fail the designated assertions |

## Immutable source context

Existing package pins and source snapshots remain unchanged: `coreai-torch`
`b51fd006`, `coreai-opt` `189612be`, and the inspected `coreai-models` dependency
snapshot `db63a2d8`. The earlier [full source/package reconciliation](../pr49-followup/README.md)
and [Part 9 refresh](../coreai-030-refresh/README.md) remain dated evidence.

Current casting behavior is supported by the
[0.3.0 implementation](https://github.com/apple/coreai-optimization/blob/189612be60bc1d5cca9b73ad8811660f738c637d/src/coreai_opt/casting/casting.py).
The [priority-aware resolver](https://github.com/apple/coreai-optimization/blob/189612be60bc1d5cca9b73ad8811660f738c637d/src/coreai_opt/_utils/insertion/torch_function/state_spec_resolver.py)
explains the tested override behavior; it does not establish every eager configuration.
[coreai-optimization#41](https://github.com/apple/coreai-optimization/issues/41)
addresses graph ownership, separate from eager re-tying.
[coreai-torch#41](https://github.com/apple/coreai-torch/pull/41) merged on
September 25, after the inspected converter tag.

## Fresh native execution

Both runs use Python **3.12.14**, Core AI **1.0.0b3**, converter **0.4.3**,
optimizer **0.3.0**, NumPy **2.4.6**, and scikit-learn **1.9.1**.
Host: arm64 macOS **27.0 / 26A428**; Xcode **27.0 / 27A266a**;
macOS SDK **26A425**, developer directory `/Applications/Xcode.app/Contents/Developer`.

| Sequential profile | Torch / TorchAO | Result |
|---|---|---|
| [Model export](native-model-export.json) | 2.9.0 / 0.17.0 | 31 checks: 21 pass, 10 expected rejections, zero failures |
| [Standalone compression](native-standalone.json) | 2.11.0 / 0.18.0 | 31 checks: 21 pass, 10 expected rejections, zero failures |

The records include runner/source revisions, helper and example hashes, packages,
toolchain identity and each fixture's actual outcome. They cover consecutive/reset/
asymmetric state at lengths 2/8/32, copied outputs, supplied RELEASE assets,
replacement, missing composites, wrong weights, shapes, finite values and error
tolerances; graph/eager quantization, mmap finalize, palettization and PAT schedule,
pruning, joint compression, direct IR utilities, casting, block activation and
composite quantization. Negative controls only pass for their expected exception
type and diagnostic; unrelated loader/compiler/runtime failures fail verification.

For the small composite fixture, conversion error against the **compressed**
reference is `3.5762786865234375e-07`; the separate dense-versus-compressed maximum
absolute difference is `0.009537994861602783`, identical in these two runs. These
are fixture measurements, with model-specific tolerances, not a general quality
or performance guarantee. The standard fp16 overflow control is infinite;
explicitly excluded exp/log1p remains finite and returns **15.0**.

The Torch 2.9 environment reports skipped optional C++ extension imports; the
Torch 2.11 environment reports deprecated TreeSpec checks. Neither produces a
fixture failure. Eager re-tying remains unsupported; observed override order
independence covers the documented fixture only. No released automatic dynamic
overflow calibration is claimed.

Reproduce manually from a separately reviewed clean runner using an existing
pinned environment (run profiles sequentially):

```sh
<profile-python> -I <trusted-runner>/scripts/verify_coreai_examples.py \
  --source-repo <clean-source-at-reviewed-commit> \
  --reviewed-revision 2367dc31a7c02ccf0f80f54454a35f5015d73234 \
  --compression --out <output-directory>/results.json
```

## Reconciliation and limits

[Fresh fence hashes](python-fence-hashes.tsv) compare all 464 Python fences in
Parts 7/8/9/10/17 with merged main. Changed named fixtures have fresh native
coverage; illustrative ellipsis changes have tokenization coverage. No other
fence is newly claimed to have run. [Part 9 section hashes](part9-section-hashes.tsv)
identify the changed sections while preserving old audits as historical evidence.

All **1,785** classified callout identities and content hashes remain unchanged;
their locations and generated indexes are reconciled. All **1,360** Swift fence
identities and bodies are unchanged. Line-only re-keying preserves existing target
provenance, including five historical SDK-26 verdicts; it is not a fresh compilation.
SDK 26 remains unavailable. The prior bounded Simulator lane and its excluded
Spotlight call/timeout remain explicit in [the earlier evidence](../pr49-followup/README.md).
No additional Swift, device, Simulator, model-judge or performance execution is
claimed here. Daily automations remain paused/report-only.

See [validation](validation.md) and [reconciliation](reconciliation.json) for final
portable checks and primary-checkout preservation. The implementation uses a
managed worktree; the primary checkout's existing edits are retained unchanged.
