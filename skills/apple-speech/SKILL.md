---
name: apple-speech
description: "Apple's 2026 Speech framework: SpeechAnalyzer, SpeechTranscriber and DictationTranscriber, asset installation through AssetInventory, custom vocabulary, live and file-based transcription, AnalyzerInputConverter, and volatile-versus-finalized results."
when_to_use: "Use for any speech-to-text or live transcription work on Apple platforms: an empty transcript with a clean console, a final sentence that gets cut off, duplicated phrases in a merged transcript, custom vocabulary that is ignored, or looking for a speech generation API on this framework."
---

# SpeechAnalyzer: live and file-based transcription

Part 16 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

## Evidence markers — never flatten these

Every non-obvious claim in `references/` carries one of these. Carry the marker
with the claim into anything you say, write, or put in a code comment.

- ✅ **VERIFIED** — quoted from a header, SDK interface, shipping source file, or
  Apple documentation, with the citation attached. Safe to rely on.
- 🟡 **RECONSTRUCTED** — the concept is attested, usually from a WWDC session, but
  the exact spelling is inferred. Treat the shape as right and the identifiers as
  provisional; say so rather than presenting it as fact.
- 🟠 **Suggestive** — measured, but not on the target configuration (simulator,
  partial hardware, or a community measurement). Directional only.
- 🔴 **GAP** — could not be verified. The callout names what is unknown and what
  would resolve it. Never guess past one.
- ⚠️ **SILENT FAILURE** — fails without throwing. Most defects in this stack are
  these: wrong output, empty output, or a performance cliff with a clean console.

## Find the answer in three moves

`references/` holds far more than fits in context. Never read a file whole —
route to the section you need:

1. **You have a symptom** (wrong output, empty result, silent no-op, perf cliff,
   something ignored) — `Grep` `references/SILENT-FAILURES.md` for words from what
   you actually observed. Entries are grouped by symptom and each links to the
   guide section that explains it.
2. **You have a symbol** (`LanguageModelSession`, `AIModel`, `mx.compile`, …) —
   `Grep` `references/API-INDEX.md`. The row shows whether the symbol appears in
   the captured 26.5 and 27.0 SDK interfaces; **blank in both columns means the
   spelling is not SDK-confirmed**, so treat it as provisional.
3. **You have a task** — use the triage table below, then the part README it
   points at.

The deep reference guides are not bundled. `references/SECTION-MAPS.md` lists
every section of every one with its anchor; fetch a single section rather than a
whole file.

## Version floors

| Part | Floor |
|---|---|
| [16](references/part-16-adjacent-capabilities/README.md) | deliberately mixed, and this is the part where version confusion costs the most. |

## Read these before you trust a signature

- **Part 16** — [Two things to learn before you plan anything](references/part-16-adjacent-capabilities/README.md#️-two-things-to-learn-before-you-plan-anything)

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 16 — Adjacent capabilities** ([all 15 rows](references/part-16-adjacent-capabilities/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "The keynote promised speech generation and I can't find the API" | 16.1 §1.1 | It does not exist. AVFoundation, per Apple staff on thread 834149 |
| "I'm learning the 2026 Speech API from the downloadable sample" | 16.1 §1.2 | That ZIP is WWDC25. It has **none** of the 2026 input symbols |
| "Users report the last sentence gets cut off" | 16.1 §9, §6.6 | The cancellation shield — or a missing `AnalyzerInputConverter.flush()` |
| "My transcript reads *'I went to the I went to the store'*" | 16.1 §8.3 | Your preset does not emit `.audioTimeRange`, so the merge always appends |
| "Empty transcript, clean console" | 16.1 §5.5 | Assets before format before analyzer before audio. The analyzer converts nothing |
| "Is there a Siri schema for what my app does?" | 16.2 §5–§6 | All 23 domains enumerated — then the categories with no domain at all |
| "My category isn't covered. What is left?" | 16.2 §8 | `.system.searchInApp`, with code. Works without domains or indexing |
| "*'Remove the due date'* reports success and changes nothing" | 16.2 §14.1 | `IntentParameter.valueState`. A `nil` check cannot express "clear it" |
| "Siri answers from my screen text and ignores my `AppEntity`" | 16.3 §1 | Descriptive requests take the screenshot path and never call `entities(for:)` |
| "*'Send this to X'* → *'I can't attach the image from your screen'*" | 16.3 §5 | `.files.file` + `FileEntityIdentifier` + **`FileRepresentation`**; the verified export path needs a real file, while draft identifiers cover pre-materialization identity |
| "Siri asks to clarify, or acts on the wrong item" | 16.3 §4, §8.2 | A slow `displayRepresentations`; or per-row annotation on a scrolling list |
| "My own model invents details for content I indexed" | 16.4 §7.3, §9 | The index is searchable, not readable. The hydration hook is the fix |
| "What are *'indexed entities for Apple Intelligence'*?" | 16.4 §1 | `IndexedEntity` + `indexAppEntities(_:)`. Same index, different door |
| "Dirty dataset, or a convnet that may be over-wide" | 16.5 §6.3, §6.5, §8 | `Duplicates` and PFA. Prune, retrain, *then* convert |
| Anything transformer, MLX, Core ML or Core AI shaped | **skip 16.5** | DNIKit supports none of them. §1 says so in a table |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **16.1** SpeechAnalyzer: live transcription, assets, and custom vocabulary — The 2026 speech-to-text stack end to end: an actor owning analysis modules, fed one time-coded audio sequence, handing each module's output back as its own `AsyncSequenc…

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-app-intents`, `apple-foundation-models`, `apple-on-device-ai`.
