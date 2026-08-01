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

The deep reference guides are not bundled, so reaching one needs network access
to the public repository. `references/SECTION-MAPS.md` lists every top-level
section with its anchor; fetch a single section rather than a whole file. Offline,
everything above still works — the part READMEs and both indexes are local.

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
| "Dirty dataset, or a convnet that may be over-wide" | 16.5 §6.3, §6.5, §8 | `Duplicates` and PFA. Prune, retrain, *then* convert |
| Anything transformer, MLX, Core ML or Core AI shaped | **skip 16.5** | DNIKit supports none of them. §1 says so in a table |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **6.1** Building blocks, Swift Testing integration, and evaluation-driven development — The foundation everything else hangs on: the `Evaluation` protocol's five steps (`subject(from:)` → `dataset` → `evaluators` + `Metric` → `aggregateMetrics(using:)` → a Swift Testing `@Test`), each with the corrected spelling verified against Apple's Book Tracker sample rather than reconstructed from spoken narration.
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
