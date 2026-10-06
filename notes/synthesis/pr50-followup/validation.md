# Validation — 2026-10-06

Implementation/source and trusted runner revision:
`2367dc31a7c02ccf0f80f54454a35f5015d73234`.
Base main: `8972e4abeea713f233e55dd7e9b39073b4e90ada`.

| Check | Actual result |
|---|---|
| Full repository Python suite | **328 tests**, 50.160 seconds, zero failures |
| Focused fence/helper/native-control/consistency tests, Python 3.11 | **34 tests**, zero failures |
| Same focused tests, Python 3.12 | **34 tests**, zero failures |
| Same focused tests, Python 3.14 | **34 tests**, zero failures |
| Model-export native profile | **31 checks**, 21 passes and 10 designated rejections, zero failures |
| Standalone-compression native profile, run second | **31 checks**, 21 passes and 10 designated rejections, zero failures |
| Python fence scan, Parts 7/8/9/10/17 | **464 fences**, 145 named IDs, zero removed-optimizer violations; all current text tokenizes |
| Callout reconciliation | **1,785** identities and content hashes unchanged |
| Swift reconciliation | **1,360** identities, bodies, locations and target verdicts unchanged; no fresh compilation claimed |
| Generated indexes and skills | Clean-generation comparisons pass in the full suite; regeneration introduces only six skill reference updates and their manifest hashes |
| Skill verification | **10 skills, 142 files, 8,444 links, 80 trigger evaluations** pass |
| Anchors | **17 part READMEs** verified, zero changed links |
| Current-state rendering | Four blocks regenerated and checked; no resulting byte changes |
| SDK preflight | Xcode 27.0/27A266a; macOS SDK 27.0/26A425; iPhoneOS SDK 27.0/24A430; destination integrity passes, no files written |
| Installed automation contracts | Two contracts and installed copies pass using the primary checkout to resolve installed working directories |
| Primary preservation | HEAD, Git status, file set and SHA-256 bytes of all **458** tracked/non-ignored files unchanged |
| Whitespace | `git diff --check` passes |

The focused tests include both fence styles, quoted fences, comments as false
headings, invalid/valid Unicode names, comments/strings, historical exemptions,
optimizer call forms and a bounded subprocess with hundreds of parenthesis
pairs. They exercise strict negative-control diagnostics, missing dependencies,
toolchain query failures, range checks under `-O`, and explicit composite
requirements. Corpus-wide stale-status fixtures cover negation, case, dated
history, neighboring references and stale prose outside the register.

Native records are stored separately from historical runs. Both execute the
actual named fences and standalone composite entry point from the reviewed Git
tree. Source inspection is not reported as runtime verification. All native
fixture outcomes and environment identities are in
[model-export](native-model-export.json) and [standalone](native-standalone.json).

Reproduction commands (run from the follow-up checkout):

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
<python-3.11-or-3.12-or-3.14> -m unittest \
  scripts.tests.test_coreai_examples \
  scripts.tests.test_coreai_native_controls \
  scripts.tests.test_platform_refresh_consistency
bash scripts/build-indexes.sh
python3 scripts/current-state.py render --write
bash scripts/build-skills.sh
python3 scripts/verify-skills.py
python3 scripts/anchor-section-links.py guides
python3 scripts/current-state.py render --check
scripts/dump-sdk-interfaces.sh --check-only
git diff --check
```

Installed-contract validation runs the identical validator from the primary
checkout with `--installed`; it reads the installed schedules without modifying
them. Running it from a worktree correctly reports a working-directory mismatch,
because the installed jobs target the primary checkout. The validated contracts
and installed jobs remain unchanged and paused/report-only.

SDK 26 is unavailable; the five unchanged historical SDK-26 target results retain
their existing provenance. The prior Simulator Spotlight timeout/exclusion is
retained; no fresh Simulator coverage is claimed. No toolchain installation,
schedule resumption, merging or publication is included.
