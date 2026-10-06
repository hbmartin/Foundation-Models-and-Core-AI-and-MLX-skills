# Validation record

2026-10-06, before generated-output reconciliation:

- Focused fence/contract and platform consistency suite: **21 passed**.
- Native model-export and standalone profiles: **24/24 fixtures passed per profile**; exact versions,
  code hashes and outcomes are in the native JSON records.
- Part 9 static import/signature audit: **142 fences, 125 calls checked, zero errors**; 19
  signature/pseudocode fragments were tokenized rather than executed.
- Full portable suite: 292 tests run; four expected generated-output failures (indexes, skills,
  README anchor, Swift line records), plus a Part 9 README router heading error corrected in source.
  Final generated-output checks will replace this provisional entry in the reconciliation commit.
- `git diff --check`: passed.
