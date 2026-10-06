# Final validation — 2026-10-06

Implementation base: merged PR #49 / main `425c1544b53442b004eba4d71dffc2368da6822a`.
Reviewed native source: `428807a8047ae4be2146b2a948fcdb286c88d9dd`.
Trusted runner: `2711181edf1e24cca867060c19abe937e28df444`.
Final generated reconciliation changes no named native fence body or trusted helper.

| Check / command | Result |
|---|---|
| `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` | **316 passed**, 49.712 seconds; includes clean regeneration and trust, parser, toolchain, capture and target-provenance regressions |
| Model-export native profile, Python 3.12 / Torch 2.9.0 / TorchAO 0.17.0 | **26/26 passed** |
| Standalone native profile, Python 3.12 / Torch 2.11.0 / TorchAO 0.18.0 | **26/26 passed**, executed sequentially after model-export |
| Named native examples | Actual approved Git fences; five example hashes / runner helpers / both revisions / package, OS and Xcode identities recorded |
| `verify-snippets.sh --sdk 27 --developer-dir-27 /Applications/Xcode.app/Contents/Developer --allow-unavailable-targets --jobs 4 --out artifacts/pr49-followup/swift-final` | **1,360 fences**, no unexpected available-target failures; **exit 3** because five SDK-26 fences are unavailable |
| Fresh Swift classifications | 486 illustrative, 677 prelude-needed, 189 verified, 1 migration-proven, 2 xfail-proven, 5 toolchain-unavailable |
| Swift reconciliation | All 1,360 identities/hashes match current fences; five historical unchanged SDK-26 target verdicts retained with separate provenance |
| Corrected provider and new Evaluations helper | Fresh compilation passes on Xcode 27 final; no historical upstream runtime claim inferred from compilation |
| Default host probes | **47 tests / 26 skipped / 0 failures**; four new model-free counter cases and original subject fixture pass |
| Bounded independent Simulator probes | **39 tests / 22 skipped / 0 failures**, Spotlight direct call excluded after retained timeout |
| ImageReference watch capture | Current overview/member agree on resolved(in:); raw hashes recorded; agreement/disagreement/missing declaration/capture failure regressions pass |
| SDK manifest promotion / `dump-sdk-interfaces.sh --check-only` | Seventeen current paths transferred to final capture; legacy / SDK-26 ownership retained; all hashes and toolchain identities pass |
| `diff-interfaces.sh` against committed promotion | **Clean**: all fifteen Swift interfaces and both CLI help surfaces |
| Immutable upstream snapshots | **1,173 blobs match**: converter 186, optimizer 382, models 605; zero missing/mismatched files |
| Installed Core AI package integrity, each pinned profile | **287 RECORD hashes / 183 pinned Python source files** match; both b3 authoring evidence hashes match |
| Part 9 fresh static import/signature check | **142 fences / 130 resolved calls / zero errors**; 19 fragments tokenized, not executed |
| Removed optimizer guard | All **464** Python fences in Parts 7/8/9/10/17 scanned; zero current violations; historical exemptions retain version context |
| Live defect sweep | **1,002 sightings / 416 groups**; zero unreachable or state-changed groups; 237 ambiguous groups and 309 unmapped sightings remain report-only |
| `verify-skills.py --skills skills` | **10 skills / 142 files / 8,444 links / 80 trigger evaluations** verified |
| `anchor-section-links.py guides` | **17 part READMEs**, zero changes needed; full suite also checks generated index links |
| `current-state.py render --check` and collect | Four blocks current; final collection complete with no blockers; latest Simulator observation unknown |
| `validate-automation-contracts.py` | Two repository contracts pass |
| `validate-automation-contracts.py --installed` from primary checkout | Both installed copies match; daily schedule remains paused |
| `git diff --check` | Pass |
| Primary checkout preservation | **458 file hashes + HEAD + Git status unchanged**, attested separately |

## Limits and failed attempts retained

SDK 26 is not installed: Xcode.app supplies SDK 27 and is not treated as a generation-26 target.
Five historical target verdicts remain historical; this does not establish fresh complete coverage.
The last full multi-SDK run remains August 2. No toolchain was installed.

The saved iPhone 17 Pro destination was unavailable. On the available iPhone 18 Pro Simulator,
Spotlight's direct call exceeded the 60-second bound after a linguistic-asset sandbox entitlement
error. That run was stopped; the independent bounded pass excludes that call. Its success does
not erase the timeout or establish Spotlight direct-call behavior on this topology. No new
model-backed judge retry policy, PCC/device run, or GUI Instruments result is claimed.

An initial portable run caught stale current-state blocks and an old mock that failed developer
selection before exercising the intended Simulator parsing path. Rendering the blocks and fixing
that fixture yielded the complete 316-test pass. The object-substitution fixture initially needed
write permission for Git's read-only loose-object file; the corrected fixture demonstrates commit
and nested-tree digest rejection. These failed attempts are not passing evidence.

The fresh read-only security review found the nested-tree integrity gap, then ended without a
complete final report. The confirmed gap is patched and covered by focused execution and the
full portable suite; no full repository security scan is claimed. The reviewed-revisions-only
policy deliberately permits reviewed guide code to execute with host privileges.

Raw commands, logs, captures, and result bundles are retained locally under
`artifacts/pr49-followup/` and `artifacts/freshness/manual-probes/`; native assets are under
`/tmp/pr49-native/`. Portable JSON/TSV evidence needed for review is committed alongside this note.
Historical benchmarks and previous interface/runtime records remain dated and retrievable through
Git history. Merging, publication, schedule resumption, and toolchain installation are outside scope.
