---
name: apple-ai-shipping
description: "Getting an on-device model out of development and into a shipping app: model distribution, background asset packs and model updates, memory budgets and jetsam, thermal throttling, and honest benchmarking of on-device inference."
when_to_use: Use when a model must ship or update outside the app binary, when an app is terminated under memory pressure or throttled mid-inference, when sizing a download or an on-disk model budget, or when writing or interpreting an on-device performance benchmark.
---

# Shipping and operating on-device AI in a released app

Part 15 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

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

The deep reference guides are not bundled, so reaching one needs network access
to the public repository. `references/SECTION-MAPS.md` lists every top-level
section with its anchor; fetch a single section rather than a whole file. Offline,
everything above still works — the part READMEs and both indexes are local.

## Version floors

| Part | Floor |
|---|---|
| [15](references/part-15-shipping-and-operating/README.md) | **iOS · iPadOS · macOS · tvOS · visionOS · watchOS 27.0 — all Beta** — plus **Xcode 27** and the **Metal Toolchain**, a separate download (`xcodebuild -downloadComponent MetalToolchain`) whose absence fails any build containing a `.aimodel` with a *missing Metal compiler* error that never mentions Core AI. |

## Read these before you trust a signature

- **Part 15** — [Read this before anything else in this part](references/part-15-shipping-and-operating/README.md#️-read-this-before-anything-else-in-this-part)

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 15 — Shipping and operating on device** ([all 13 rows](references/part-15-shipping-and-operating/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "My models add over a gigabyte to the app download" | 15.1 §1–§3 | Host remotely, download one variant; the first-run screen is where the wait belongs |
| "How do I actually deliver the bytes?" | 15.1 §3 | 🔴 no verified 2026 Background Assets surface for Core AI — own the delivery protocol, `URLSession` first |
| "Works on my Mac, `invalidCompiledModel` on device" | 15.1 §4.4, §5 | iPhone 17 Pro is `iPhone18,1` → **`h18p`**, not `h17p`. Never hardcode an arch code |
| "Users report 'Download failed' on a perfectly good connection" | 15.1 §5.2 | A wrong `--architecture` becomes a **404 from your asset host**, which your retry logic hides forever |
| "First launch stalls for tens of seconds, or minutes" | 15.1 §2, §6 | Specialization. 19.2 s JIT vs 4.9 s AOT on one measured model; ≥ 1 GB means AOT |
| "The stall came back after I fixed it" · "storage grew by a multiple of my model" | 15.1 §9 | `SpecializationOptions` is part of the cache key and has a mutable property |
| "I deleted the source `.aimodel` and now nothing loads" | 15.1 §8 | Bookmarks do not pin the cache entry, and resolution fails by returning `nil` |
| "I need to push a model update to shipped users" | 15.1 §7 | Delete cache entries **before** replacing the file; `deleteEntries(for:)`, not the single-entry form |
| "Can I stop this installing on devices where it won't work?" | 15.1 §12 | No. Four strategies for the world where you can't |
| "It loaded, then the app just vanished" · `signal 9` · `std::bad_alloc` | 15.2 §1–§3 | Jetsam. Load success is not a fit test; the first step is the test |
| "My tok/s moves 40% between runs on the same device" | 15.2 §7.1 | DVFS clock ramp, with thermals eliminated as the cause. 66 → 102 tok/s, one afternoon |
| "Which backend should I ship?" | 15.2 §7.3, §8 | Burst and sustained give different rankings; so do tok/s and battery |
| "I'm about to publish a comparison" | 15.2 §9–§10 | Read §9.9 first. A harness once manufactured an 80%-vs-20% gap that was entirely its own bugs |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **15.1** Shipping models: Background Assets, per-architecture variants, and updates — The operational guide for how a model reaches a device and how it gets replaced later: the size problem, the feature-introduction screen (which does three jobs at once and is where you hide specialization latency), delivery, `coreai-build compile` and per-architecture `.aimodelc` variants, specialization and its cache, the update sequence, storage hygiene, app groups, and the App Store reality.
- **15.2** Memory, jetsam, thermals, energy, and measuring honestly — The gap between a demo that works on your desk and an app that survives a week on someone else's phone.

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-core-ai`, `apple-foundation-models`, `apple-ai-evaluations`.
