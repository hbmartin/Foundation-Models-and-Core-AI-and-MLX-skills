# Final validation record

2026-10-06, after canonical repairs and generated-output reconciliation:

| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` | **292 passed** (37.666 seconds) |
| Native model-export profile, actual named guide fences | **24/24 fixtures passed** |
| Native standalone compression profile, actual named guide fences | **24/24 fixtures passed** |
| Part 9 static import/signature audit | **142 fences, 125 calls checked, zero errors**; 19 signature/pseudocode fragments were tokenized, not executed |
| Removed-optimizer token guard across Parts 7/8/9/10/17 | **464 Python fences**, zero current executable optimizer calls |
| `scripts/verify-skills.py --skills skills` | **10 skills, 142 files, 8,444 links, 80 trigger evaluations verified** |
| `scripts/anchor-section-links.py` | **17 part READMEs verified**, zero changes needed |
| `git diff --check` | Passed |
| Swift verification reconciliation | **1,359 records preserved**, zero bodies require fresh verification |

The full portable suite verifies that indexes and skills match clean regeneration. Callout
reconciliation uses semantic identity and content hash, with 18 changed classifications reviewed
in [classification-reconciliation.tsv](classification-reconciliation.tsv). Three removed rows
correspond to the replaced attention toy's warning and two stale graph tied-weight defect
callouts. The rebuilt index has **1,785 callouts / 1,425 concrete failures** and **1,210 symbols**.
Unrelated callout ordering was preserved.

Swift reconciliation carried existing verdicts only for identical source content and identity;
it did not run a new compiler pass. No Swift source bodies changed. Native Python verification
has its own package, OS and fixture records; its limits are described in [README.md](README.md).
Initial failed harness attempts and static inspection are not reported as successful runtime
verification.
