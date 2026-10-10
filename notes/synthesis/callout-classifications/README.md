# Callout classifications

These TSV files are the committed human-judgment input for
`guides/SILENT-FAILURES.md`. Each file starts with `# schema-version: 2`; every data row contains
exactly seven tab-separated fields:

```text
guide-relative-file  callout-id  content-hash  GitHub-anchor  callout-kind  symptom-id  index-blurb
```

The format is strictly tab-delimited: there is no csv quoting or escaping, double quotes are
literal characters, and no field may contain a tab or newline. Do not paste csv-quoted text
(`"…""…"""`) into a blurb — the tooling reads it back byte-for-byte.

`symptom-id` must be one of the IDs in
[`../SYMPTOM-TAXONOMY.md`](../SYMPTOM-TAXONOMY.md). File plus `callout-id` identifies a semantic
warning emitted by `scripts/extract-callouts.py`; the hash, anchor, and kind are review guards.
Line-only movement is harmless, while changed warning text, kind, or section fails closed.
Each prose warning start in a blockquote has its own row, including warning headings, list items,
and bold warnings. Its explanation includes quoted blanks, inline badges, and code comments, and
ends at the next prose warning or an unquoted boundary. Preceding context belongs to the first
warning only; edits to a later warning do not invalidate earlier warnings' review hashes. Quoted
blocks without prose warning starts emit their warning-bearing lines as `INLINE`, hashing each
line independently.
The default ID is derived from normalized semantic content. If exact duplicates are intentional,
place `<!-- callout-id: unique-slug -->` immediately before a Markdown callout. Inside a blockquote,
use `> <!-- callout-id: unique-slug -->` before the designated warning; quoted blank lines may
intervene. Hidden identity markers are excluded from the content hash and excerpt. For the Nth warning
inside a code fence, place `<!-- callout-id: unique-slug occurrence:N -->` immediately before the
fence. Callout metadata must never be inserted into the reader-visible code itself.

After editing a guide:

1. Run `python3 scripts/extract-callouts.py guides` and reconcile every changed identity or hash
   here. Classify new or edited callouts deliberately; line-only changes need no re-keying.
2. Run `./scripts/build-indexes.sh`. The build fails on malformed rows, duplicate keys, unknown
   symptom IDs or kinds, missing callouts, and stale classifications.
3. Review both generated pages and run the index-tooling tests. Do not edit the generated pages by
   hand.

For a reproducible generated date, set `SOURCE_DATE_EPOCH` before running the build. The extractor
assigns duplicate headings the same suffixes GitHub uses (`anchor`, `anchor-1`, `anchor-2`, …), so
the stored anchors must not be manually collapsed back to the unsuffixed form. All committed classification files use schema version 2.
