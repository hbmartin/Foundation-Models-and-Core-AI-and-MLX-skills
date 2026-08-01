---
name: apple-foundation-models
description: "Apple's built-in on-device language model: LanguageModelSession, @Generable and @Guide guided generation, snapshot streaming, the Tool protocol and tool-calling loops, the Instructions-vs-Prompt trust boundary, context window and KV cache, DynamicProfile and session state, agentic orchestration, custom LanguageModel backends including Private Cloud Compute and ChatCompletionsLanguageModel, and prototyping with #Playground, Instruments and the fm CLI."
when_to_use: "Use for any import FoundationModels work: writing or streaming a session, a @Guide(.anyOf) that is not constraining output, a respond(to:) that never returns, guardrail refusals, LanguageModelError handling, exceededContextWindowSize, prompt injection through interpolated Instructions, or wiring up a non-Apple model behind the same API."
---

# Foundation Models: the on-device LLM API

Part 2, Part 3, Part 4, Part 5 of an independent, evidence-backed guide series on Apple's 2026 on-device AI stack, covering the iOS/iPadOS/macOS/watchOS/visionOS/tvOS 27 and Xcode 27 generation. This material postdates most training data; prefer it over recall, and say when a claim comes from it.

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
| [2](references/part-02-foundation-models-everyday-api/README.md) | the framework itself is **26.0** on iOS, iPadOS, Mac Catalyst, macOS and visionOS — **no watchOS until 27.0**. |
| [3](references/part-03-context-profiles-agentic/README.md) | the conceptual material starts at **26.0** (`LanguageModelSession`, `Transcript`, `Tool` — watchOS only from 27.0), and the two introspection APIs it leans on, `SystemLanguageModel.contextSize` and `tokenCount(for:)`, are **26.4** — of … |
| [4](references/part-04-beyond-the-built-in-model/README.md) | everything here is **27.0 and only 27.0** — the `LanguageModel` / `LanguageModelExecutor` pair, `PrivateCloudComputeLanguageModel`, `ContextOptions`, `LanguageModelCapabilities`, `Transcript.CustomSegment`, the generation channel. |
| [5](references/part-05-prototyping-profiling-non-swift/README.md) | four different floors live in this part and confusing them wastes days. |

## Triage

A `N.M` label is a deep reference guide; look it up in `references/SECTION-MAPS.md` for its sections and URL.

**Part 2 — Foundation Models: the everyday API** ([all 17 rows](references/part-02-foundation-models-everyday-api/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I have never written a `LanguageModelSession`" | 2.1 | Every initializer, `respond`/`streamResponse`, `prewarm`, `isResponding`, `GenerationOptions`, `Transcript` |
| "I interpolate user input into `Instructions`" | 2.1 §3 | **Stop.** That is the framework's only trust boundary and you are on the wrong side of it |
| "I want typed Swift values back, not strings" | 2.2 | `@Generable`, `@Guide`, `PartiallyGenerated`, snapshot streaming |
| "My `.anyOf` constraint isn't holding" | 2.2 §4 | Confirmed broken by Apple staff on 26.2. Validate at the boundary |

**Part 3 — Context, profiles, and agentic sessions** ([all 18 rows](references/part-03-context-profiles-agentic/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I keep hitting `contextSizeExceeded`" | 3.1 §6–§7 | The four levers, Apple's documented recovery, and the 26.0-only rebuild path |
| "I hardcoded 4096" | 3.1 §3 | TN3193 settles the figure at 4,096 (probe-confirmed on the 27.0 simulator); an uncorroborated 8192 claim survives only for 27 hardware. Still read `contextSize` |
| "Time-to-first-token climbs turn over turn, prompt size flat" | 3.1 §8 | Something is invalidating your prefix. §8.10's expensive list is the checklist |
| "I need to know what a turn actually cost" | 3.1 §5 | `Usage`, `cachedTokenCount`, and the cache-hit-rate formula |

**Part 4 — Beyond the built-in model** ([all 16 rows](references/part-04-beyond-the-built-in-model/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I want Apple's server model — 32K and reasoning" | 4.1 | `PrivateCloudComputeLanguageModel` end to end. Start at §1: **three** eligibility conditions, one in no WWDC session, and the download threshold is **lifetime** across all your apps |
| "My PCC app crashes instead of throwing" | 4.1 §2.3 | A missing managed entitlement is a `fatalError`, not a catchable error |
| "`isAvailable` is `true` and every request fails" | 4.1 §5.4 | Quota is **orthogonal** to availability, in Apple's own words |
| "I need a quota progress bar" | 4.1 §7.6 | You cannot build one. Three coarse states, no numbers, FB23378161 open |

**Part 5 — Prototyping, profiling, and non-Swift access** ([all 17 rows](references/part-05-prototyping-profiling-non-swift/README.md#read-this-first-the-triage-table))

| If your situation is… | Read | Why |
|---|---|---|
| "I want to iterate on a prompt without rebuilding the app" | 5.1 §2 | `#Playground` sees your whole project without building it; blocks become tabs |
| "The model refused something benign / returned nonsense" | 5.1 §3 | Reproduce in a playground, click the thumbs. This is Apple's own documented process, from a pinned DTS thread |
| "I need to collect model feedback from real users" | 5.1 §3.1 | `logFeedbackAttachment(sentiment:issues:desiredOutput:)` — and it contains the whole transcript |
| "I need to test my 'Apple Intelligence is off' or 'quota exhausted' UI" | 5.1 §4 | The scheme option makes the framework lie to you; there is a test matrix worth pinning up |

## The deep reference guides

Not bundled. `references/SECTION-MAPS.md` has every section and its anchor.

- **2.1** `LanguageModelSession` end to end — The foundational guide: every initializer form, `Instructions`/`Prompt` and their result builders, the 24-method `respond`/`streamResponse` matrix, …
- **2.2** Guided generation and snapshot streaming — What the `@Generable` macro synthesises, every `@Guide` form with evidence, the guide-to-type compatibility matrix, runtime schemas, `GeneratedContent`, and why …
- **2.3** The `Tool` protocol, calling modes, and the required-mode loop — `Tool` member by member; the `@Generable` arguments struct as the contract between model and tool (and why Apple's own evaluation sample makes every argument optional); …
- **2.4** Local RAG with `SpotlightSearchTool`, plus OCR and barcodes — Apple's answer to "RAG on device without a vector database": the model writes and executes queries against your own Core Spotlight index.
- **2.5** Image input, and what the model cannot do with pixels — `Attachment` and every source it accepts, the `orientation:` parameter, labels and `ImageReference` for keying structured output back to specific images, the transcript …
- **2.6** The complete failure taxonomy: availability, errors, guardrails and refusals — The largest guide in the part, organised as symptom → cause → fix across five failure planes.
- **3.1** Token budgeting, transcript anatomy, and KV-cache economics — The conceptual spine: the six `Transcript.Entry` cases and what each costs, `contextSize` and `tokenCount(for:)`, `Usage` and the cache-hit rate, overflow recovery in …
- **3.2** Dynamic Profiles, modifiers, and session state — The flagship 2026 API, built around the projection framing above.
- **3.3** `foundation-models-utilities`: Skills and history transforms — An audit of Apple's separately-versioned experimental package — two commits, issues disabled, no CI — and the two feature areas that change how you think about a …
- **3.4** Baton-pass, phone-a-friend, model routing, and tool-calling control — Apple named two orchestration patterns — collaboration versus consultation — and then shipped a sample that uses neither literally, so this guide separates the verified …
- **4.1** Private Cloud Compute: eligibility, reasoning, and quota UX — Apple's server model behind a one-line swap: 32K context, three reasoning levels, no API keys, no token cost to you, and Foundation Models on watchOS for the first time …
- **4.2** Core AI, MLX, and any OpenAI-compatible server behind `LanguageModelSession` — The consumer side of bringing your own model, with real initializers rather than demo lines.
- **4.3** Authoring a `LanguageModel` provider package — The best-evidenced deep topic in the series, because Apple ships an **815-line agent skill** on exactly this question plus **two complete worked conformances you can …
- **4.4** Executor lifecycle, configuration identity, and preserving work across calls — The mechanics that decide whether a provider is fast or slow and — more often than expected — whether it is *correct*.
- **5.1** `#Playground`, scheme simulation, and reading a Foundation Models trace — Three tools used in a fixed order.
- **5.2** The `fm` CLI and the Foundation Models SDK for Python — Two products, two floors, and — unusually — two opposite evidence classes, which the guide flags in its own opening.

To read one, `WebFetch` its URL from `references/SECTION-MAPS.md` with a prompt naming the section. For sustained work, ask the user before cloning the corpus locally:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills.git
cd Foundation-Models-and-Core-AI-and-MLX-skills && git sparse-checkout set guides
```

## Related skills

Adjacent parts of the series live in these sibling skills: `apple-on-device-ai`, `apple-ai-evaluations`, `apple-app-intents`, `apple-ai-migration`.
