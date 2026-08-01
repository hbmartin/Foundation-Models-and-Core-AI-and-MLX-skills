---
name: apple-on-device-ai
description: "Decide which Apple on-device AI stack a project should use - Foundation Models, Core AI, MLX or Metal - and get the platform, OS-version and hardware gates right across iOS, iPadOS, macOS, visionOS, tvOS and watchOS 26 and 27. Also the corpus-wide entry point: carries the full symbol index and silent-failure index for all 17 guide parts."
when_to_use: Use when picking a framework for on-device inference, when writing @available or SystemLanguageModel.availability checks, when a 26.0 / 26.2 / 26.4 / 27.0 version floor is in question, when a feature compiles but is unavailable at runtime, or when you know the symptom or the symbol but not which Apple framework owns it.
---

# Apple on-device AI: choosing a stack and getting the gates right

Part 1 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

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
| [1](references/part-01-orientation-and-gating/README.md) | **iOS / iPadOS / macOS / visionOS 26.0 → 27.0**, **watchOS 27.0**, **tvOS 27.0**, built with **Xcode 26 → 27**. |

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 1 — Orientation and gating** ([all 18 rows](references/part-01-orientation-and-gating/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Where |
|---|---|---|
| "I don't know whether I want Foundation Models, Core AI, or MLX" | 1.1 | §3 then §5 |
| "I want a Hugging Face model in my app's real prompt flow *this afternoon*" | 1.1 | §3.5 — `mlx_lm.server` + `ChatCompletionsLanguageModel` |
| "I have a tok/s number and want to know whether it means anything" | 1.1 | §6.4 |
| "My feature is always-on / battery-sensitive" | 1.1 | §6.2 and §6.3 — the ranking inverts by axis |
| "I need `@Generable` **and** my own weights" | 1.1 | §3.3 — Core AI's *fastest* engine can't do it |
| "I have a working Core ML model — do I move it?" | 1.1 | §4 |
| "My streaming UI spins forever and nothing threw" | 1.1 | §7 — a tool-only turn yields zero partials |
| "A blog post gave me an API that doesn't compile" | 1.1 | §8 |
| "Am I even allowed to use Private Cloud Compute?" | 1.2 | §8.2 — two of the three conditions are commercial |
| "`cannot find 'MLXLanguageModel' in scope`" | 1.2 | §3.3 — it's your Xcode version, not your dependency |
| "It fails in the Simulator with error `-1`" | 1.2 | §10.1 |
| "Apple Intelligence is on, but availability says it isn't" | 1.2 | §7.4 — the Siri coupling, an acknowledged bug |
| "I'm rebuilding an iOS 26 app with Xcode 27" | 1.2 | §3.4, then [Part 17](https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills/blob/main/guides/part-17-migration-from-pre-ios-27/README.md) |
| "I'm shipping to watchOS" | 1.2 | §2.2 and §10.3 |
| "I want the App Store to only offer my app to capable devices" | 1.2 | §9 — you can't; build a baseline |
| "I'm bundling `.aimodel` files" | 1.2 | §4.1 and §5.2 |
| "What hardware do I actually need to test on?" | 1.2 | §12 |
| "Just give me something that compiles and tells me what I can use" | 1.2 | §11 |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **1.1** The 2026 Apple AI stack, and how to choose a model backend — The map, and the decision it replaced.
- **1.2** Every version, hardware, entitlement and runtime-surface gate — The complete inventory of everything sitting between the code you write and a feature that runs: the four OS floors and what each one *means*, a per-symbol decoder ring …

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-foundation-models`, `apple-core-ai`, `apple-mlx`, `apple-ai-migration`.
