---
name: apple-ai-evaluations
description: "Apple's Evaluations framework, new in the 27 cycle with no back-deployment: building an eval harness for on-device model output, hill-climbing a prompt against it, model-as-judge graders and judge alignment, synthetic data generation, and tool-trajectory evaluation. Also DNIKit, for auditing a dataset or a network before you spend time converting it."
when_to_use: Use when measuring or regression-testing LLM output quality on Apple platforms, writing or calibrating graders, scoring generations, building an adversarial or synthetic eval set, evaluating whether an agent called the right tools in the right order, or checking a training dataset for duplicates and a convnet for excess width.
---

# Evaluations: measuring on-device model output

Part 6, Part 16 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

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
| [6](references/part-06-evaluations/README.md) | the `Evaluations` framework is **new in the 27 cycle and does not back-deploy**. |
| [16](references/part-16-adjacent-capabilities/README.md) | deliberately mixed, and this is the part where version confusion costs the most. |

## Read these before you trust a signature

- **Part 16** — [Two things to learn before you plan anything](references/part-16-adjacent-capabilities/README.md#️-two-things-to-learn-before-you-plan-anything)

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 6 — Evaluations** ([all 16 rows](references/part-06-evaluations/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I have never written an `Evaluation`" | 6.1 | The five steps, mapped to exact API, with a complete copyable file |
| "I have eval code from a blog post or a transcript reconstruction" | 6.1 §19 | The corrections table. Four out of four spellings in circulation are wrong and do not compile |
| "My tests are green and the output is visibly bad" | 6.1 §10 | The defect is in your measurements. Four heuristics passed on tags including "overrated" and a wrong genre |
| "My pass rate is 100% and I am suspicious" | 6.1 §7 | A range metric reads 100% over a collapsed distribution. Pair it with a scored metric and a σ |
| "I work in Python" | 6.1, then Part 5 | Evaluations is Swift-only. Apple's guidance is the Python FM SDK plus your own scoring code |
| "I need to measure something I can only describe in words" | 6.2 | `ModelJudgeEvaluator`, `ScoreDimension`, `ScoringScale` |
| "I disagree with a score the judge gave" | 6.2 §7 | **Split the question.** The judge is usually right by the rubric you wrote |
| "The judge scores everything 3" | 6.2 §5.1 | Odd-numbered scale, or a question that is asking two things |
| "Can I trust the judge at all?" | 6.2 §16 | The κ meta-evaluation: freeze the output, replay it, score it against your own ratings |

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

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **6.1** Building blocks, Swift Testing integration, and evaluation-driven development — The foundation everything else hangs on: the `Evaluation` protocol's five steps (`subject(from:)` → `dataset` → `evaluators` + `Metric` → `aggregateMetrics(using:)` → a…
- **6.2** Model judges, score dimensions, drift, and Cohen's kappa — The half of evaluation that cannot be written as an `if`, and then the harder half: proving the thing doing the judging deserves to.
- **6.3** `SampleGenerator`, synthetic datasets, and evaluating tool trajectories — Two subjects that share a chapter because both are about honesty.
- **16.5** DNIKit: auditing datasets and networks before you convert — The shortest guide in the series, on purpose.

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-foundation-models`, `apple-core-ai`, `apple-ai-shipping`.
