# Apple `ImageReference` documentation evidence — 2026-10-05

**Capture date:** 2026-10-05

**Method:** `scripts/capture-apple-docs-watch.py` fetched Apple's direct Markdown responses without
rewriting them. The exact responses and machine-readable manifest are retained under
`artifacts/freshness/apple-docs/20261005T-current/` in the local evidence store.

| Apple page | Direct Markdown URL | Bytes | SHA-256 | Extracted spelling |
|---|---|---:|---|---|
| `ImageReference` overview | `https://developer.apple.com/documentation/foundationmodels/imagereference.md` | 2813 | `0119a237f0a1f74e5f67917afafc1f5d59a9a43b730655c3433196e6189b55a6` | `resolved(in:)` |
| `resolved(in:)` member | `https://developer.apple.com/documentation/foundationmodels/imagereference/resolved%28in%3A%29.md` | 1613 | `ca3546c07791512b2c61ff20defd38414aba6baec78b684cfedb617d4af919d1` | `resolved(in:)` |

## Conclusion

Both current pages and Xcode 27.0 final (`27A266a`) agree on
`func resolved(in transcript: some Sequence<Transcript.Entry>) -> Transcript.ImageAttachment?`.
Neither captured response contains `func resolve(in:)`. This matches the shipping 27.0 SDK capture
read directly from
`/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX27.0.sdk`
at lines 3023-3027, as well as the checked-in interface at the same lines.

The 2026-07-27 documentation harvest remains useful historical provenance: its changes view showed
the whole-`Transcript` `resolve(in:)` overload as deprecated. That historical view explains how the
older spelling entered the corpus, but it is not evidence that the overload remains in the current
surface.

## Recheck — 2026-10-06

Current Apple pages still agree. The overview response remains 2,813 bytes but its hash is now
`15c000331729f6492cdb2e3c978e723f855f00f13a9f88a48c0beb031557bd79`; the member response
remains 1,613 bytes with the same hash above. Fresh raw responses and manifest are retained at
`artifacts/pr49-followup/apple-imagereference/`. This new hash does not replace the October 5
measurement. The final Xcode interface promotion retains the same declaration.
