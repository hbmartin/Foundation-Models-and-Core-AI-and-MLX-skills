# Callout classifications

These TSV files are the committed human-judgment input for
`guides/SILENT-FAILURES.md`. Each non-comment row contains exactly six tab-separated fields:

```text
guide-relative-file  source-line  GitHub-anchor  callout-kind  symptom-id  index-blurb
```

`symptom-id` must be one of the IDs in
[`../SYMPTOM-TAXONOMY.md`](../SYMPTOM-TAXONOMY.md). The file, line, anchor, and kind together identify
one row emitted by `scripts/extract-callouts.py`; they are deliberately strict so a moved, added, or
removed warning cannot disappear from the generated index unnoticed.

After editing a guide:

1. Run `python3 scripts/extract-callouts.py guides` and reconcile every changed row here. Preserve
   the existing symptom and blurb when only line numbers moved; classify new callouts deliberately.
2. Run `./scripts/build-indexes.sh`. The build fails on malformed rows, duplicate keys, unknown
   symptom IDs or kinds, missing callouts, and stale classifications.
3. Review both generated pages and run the index-tooling tests. Do not edit the generated pages by
   hand.

For a reproducible generated date, set `SOURCE_DATE_EPOCH` before running the build. The extractor
assigns duplicate headings the same suffixes GitHub uses (`anchor`, `anchor-1`, `anchor-2`, …), so
the stored anchors must not be manually collapsed back to the unsuffixed form.
