# Apple Official Sample Code — WWDC26 AI/ML Stack (iOS/macOS 27)

Harvested 2026-07-27. **Everything below is quoted from downloaded Apple sample-code
archives** (or, where noted, from the doc article). Nothing here is written from memory.
Line citations are `<relative-path-inside-archive>:LINE` against the extracted archive at
`…/scratchpad/samples/<ArchiveName>/`.

## Table of contents

1. Source inventory (URLs, download status, sizes)
2. **Corrections to our reconstructed API signatures** ← read this first
3. Origami — Dynamic Profiles / DynamicInstructions / orchestration / PCC (sessions 241/242/243)
4. Book Tracker — Evaluations framework (sessions 298/299/335)
5. LLMSearchUsingCoreSpotlight — SpotlightSearchTool, hiking trails (session 246)
6. FoundationModelsCoffeeGame — generative game content ⚠️ **iOS 26 vintage, not refreshed for WWDC26**
7. SwiftTranscriptionSampleApp — SpeechAnalyzer ⚠️ **WWDC25 sample; `DictationTranscriber` / `CaptureInputSequenceProvider` / `SFCustomLanguageModelData` / `datagenerator` are ABSENT**
8. Bonus: AddingIntelligentAppFeaturesWithGenerativeModels ⚠️ **iOS 26 vintage**
9. Cross-cutting patterns worth reproducing in the guide series
10. Open questions / UNVERIFIED

**Three of the five targets (Origami, Book Tracker, Spotlight) are genuine iOS 27 / WWDC26 code.
The game and speech samples are iOS 26 leftovers** — valuable as a "what changed" baseline, but
do not cite them as 2026 API.

---

## 1. Source inventory

All discovered by hitting Apple's DocC JSON backing store, which exposes the download URL:

```
https://developer.apple.com/tutorials/data/documentation/<framework>/<slug>.json
https://developer.apple.com/tutorials/data/index/<framework>            # index; type=="sampleCode"
```

`grep -o 'https://docs-assets.developer.apple.com[^"]*\.zip'` on that JSON yields the ZIP.
This is a reliable, repeatable recipe — the sosumi.ai mirror does NOT surface the ZIP URL.

| # | Sample | Doc page | ZIP | Size | Status |
|---|--------|----------|-----|------|--------|
| 1 | **Origami: Crafting a dynamic tutorial for Apple Intelligence** | `/documentation/foundationmodels/origami-crafting-a-dynamic-tutorial-for-apple-intelligence` | `docs-assets…/published/e843a4026a2e/OrigamiCraftingADynamicTutorialForAppleIntelligence.zip` | 200,398,017 B | **OBTAINED** — 61 Swift files |
| 2 | **Book Tracker: Using Evaluations to evaluate an intelligent feature** | `/documentation/evaluations/book-tracker-using-evaluations-to-evaluate-an-intelligent-feature` | `…/published/6bb5705513b4/BookTrackerUsingEvaluationsToEvaluateAnIntelligentFeature.zip` | 56,243,741 B | **OBTAINED** — 20 Swift files (+ a real `.git` dir) |
| 3 | **Searching indexed content with natural language** (the hiking-trails / `SpotlightSearchTool` sample) | `/documentation/corespotlight/searching-indexed-content-with-natural-language` | `…/published/f9dfe6c6f5d3/SearchingIndexedContentWithNaturalLanguage.zip` | 128,546,222 B | **OBTAINED** — 6 Swift files, target `LLMSearchUsingCoreSpotlightApp` |
| 4 | **Generate dynamic game content with guided generation and tools** | `/documentation/foundationmodels/generate-dynamic-game-content-with-guided-generation-and-tools` | `…/published/86c65aeb21cc/GenerateDynamicGameContentWithGuidedGenerationAndTools.zip` | 206,978 B | **OBTAINED** — 21 Swift files, `FoundationModelsCoffeeGame` |
| 5 | **Bringing advanced speech-to-text capabilities to your app** | `/documentation/speech/bringing-advanced-speech-to-text-capabilities-to-your-app` | `…/published/e40c20fc5641/BringingAdvancedSpeechToTextCapabilitiesToYourApp.zip` | 55,630 B | **OBTAINED** — 8 Swift files, `SwiftTranscriptionSampleApp` |
| 6 | *(bonus)* **Adding intelligent app features with generative models** | `/documentation/foundationmodels/adding-intelligent-app-features-with-generative-models` | `…/published/5414fd17db13/AddingIntelligentAppFeaturesWithGenerativeModels.zip` | — | **OBTAINED** |

**Zero download failures.** Note the task brief said Book Tracker was "~31 KB" — the actual
archive is **56 MB** (it bundles book-cover assets and a git pack). The *code* is small.

Exhaustive `sampleCode` sweep of the doc indexes found **no other** samples in
`foundationmodels`, `evaluations`, or `speech`. `coreai` has **no sample-code entries at all**.
`speech` also lists the older *Recognizing speech in live audio* (not fetched — pre-2026).

Extraction root:
`/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/samples/`

### Build settings (from `project.pbxproj`)

| Sample | Deployment targets | Platforms | Swift |
|---|---|---|---|
| Origami | `IPHONEOS_DEPLOYMENT_TARGET = 27.0`, `MACOSX_DEPLOYMENT_TARGET = 27.0`, `XROS_DEPLOYMENT_TARGET = 27.0` | `iphoneos iphonesimulator macosx` | `SWIFT_VERSION = 6.0` |

Origami entitlements (`Origami/Origami.entitlements`) contain **only** `com.apple.security.app-sandbox`.
The PCC entitlement is *not* shipped — see §3.2.

---

## 2. Corrections to our reconstructed API signatures

Legend: **CONFIRMED** = sample matches our notes. **CORRECTED** = sample contradicts or refines
our notes. **NEW** = sample shows API our notes never captured.

### 2.1 Dynamic Profiles (from Origami)

| # | Our note said | The sample says | Verdict |
|---|---|---|---|
| 1 | Protocol conformance is `LanguageModelSession.DynamicProfile` (working conclusion, `fm-advanced.md:160`) | `struct OrchestratorProfile: LanguageModelSession.DynamicProfile` | **CONFIRMED** |
| 2 | "Guides should use `some LanguageModelSession.DynamicProfile` for the `body` type" (`fm-advanced.md:162`) | `var body: some DynamicProfile` — the **short** form | **CORRECTED**. Apple writes the short name inside a conforming type (SwiftUI `some View` ergonomics). Use the short form. |
| 3 | `Profile(model: PrivateCloudComputeLanguageModel()) { … }` (`fm-advanced.md:263`) | `Profile { … }.model(serverModel)` | **CORRECTED**. Content closure + `.model(_:)` modifier. `init(model:)` never appears. |
| 4 | `.temperature(1)` (`fm-advanced.md:266`) | `.temperature(1.0)` | **CORRECTED** (Double). |
| 5 | `.reasoningLevel(.deep)` | `.reasoningLevel(.deep)` | **CONFIRMED**, verbatim. |
| 6 | `.historyTransform { history in … }`, element type UNVERIFIED (`fm-advanced.md:412`) | `.historyTransform(shortHistory(_:))` where `func shortHistory(_ entries: [Transcript.Entry]) -> [Transcript.Entry]` | **CORRECTED/RESOLVED**. Signature is `([Transcript.Entry]) -> [Transcript.Entry]`; a function reference is accepted. |
| 7 | `PrivateCloudComputeLanguageModel` vs "PCCLanguageModel" ambiguity (`fm-advanced.md:188-190`) | `PrivateCloudComputeLanguageModel()` in two archives | **CONFIRMED**. "PCCLanguageModel" was caption shorthand. |
| 8 | Entitlement `com.apple.developer.private-cloud-compute` | Named in a code comment in **two** samples, with the request URL `https://developer.apple.com/contact/request/private-cloud-compute/`; it is a **managed** entitlement you must apply for | **CONFIRMED + NEW** (the request URL and "managed" status). |
| 9 | `DynamicProfileBuilder` "enforces exactly one active Profile; avoid parallel `if` blocks" (`apple-docs…:1054`) | `switch` over an app enum, with nested `if !x { … } else { … }` | **CONFIRMED**, and if-*else* is the sanctioned conditional shape. |
| 10 | `DynamicInstructions` is top-level (not nested) | `struct OrigamiInstructions: DynamicInstructions`, `var body: some DynamicInstructions` | **CONFIRMED** |
| 11 | Nesting concatenates instructions + tools (242:42) | `TutorialInstructions` embeds `CoachInstructions` / `OrigamiInstructions` as values | **CONFIRMED** |
| 12 | `Instructions { … }` builder form | Both `Instructions("…")` **and** `Instructions { … }` appear, in adjacent files | **CONFIRMED both**. |
| 13 | `init(profile:)` (`apple-docs…:192`) | `LanguageModelSession(profile:history:)` where `history: Transcript` | **NEW** — the `history:` label was not in our notes. |
| 14 | — | `Transcript(entries: [Transcript.Entry])`, `.response(Transcript.Response(assetIDs:segments:))`, `.text(Transcript.TextSegment(content:))`; **`assetIDs` is a required `[String]`, passed `[""]`** | **NEW** |
| 15 | — | `Transcript` is **`Encodable`** (`JSONEncoder().encode(session.transcript)`) | **NEW** |
| 16 | `SystemLanguageModel.default` | Origami/Spotlight use **`SystemLanguageModel()`** exclusively; Book Tracker uses **both** `SystemLanguageModel.default` and `SystemLanguageModel()` | **NEW** — the bare initializer exists and is the 2026 house style. |
| 17 | — | `SystemLanguageModel(guardrails: .permissiveContentTransformations)` | **NEW** — an initializer parameter absent from our notes. |
| 18 | `LanguageModelSession(transcript:)` (iOS 26) | Coffee game uses `transcript:`; Origami uses `history:` | **NEW/AMBIGUOUS** — two labels coexist; deprecation status UNVERIFIED. |

### 2.2 Errors (Origami **and** Spotlight, independently)

| # | Item | Verdict |
|---|---|---|
| 19 | `LanguageModelError` case names **`.timeout`**, **`.guardrailViolation`**, **`.refusal`**, **`.contextSizeExceeded`**, **`.unsupportedLanguageOrLocale`** | **CONFIRMED** by two separate archives shipping near-identical `Error+DisplayMessage.swift`. Our notes had `.contextSizeExceeded`, `.unsupportedGenerationGuide`, `.rateLimited`; `.timeout`/`.guardrailViolation`/`.refusal`/`.unsupportedLanguageOrLocale` are newly confirmed. |
| 20 | `LanguageModelError` is **non-frozen** — both samples end with `default: break` | **NEW** |
| 21 | `SystemLanguageModel.Error` is a **distinct type**, checked *before* `LanguageModelError` via `if self is SystemLanguageModel.Error` | **CONFIRMED + refined** (ordering matters). |
| 22 | `GeneratedContent.ParsingError` exists and is caught separately | **NEW** |
| 23 | `LanguageModelSession.Error` (listed in our harvest) | **NOT USED by any sample** — UNVERIFIED. |

### 2.3 Guided generation & tools

| # | Item | Verdict |
|---|---|---|
| 24 | `@Generable(description:)` | **CONFIRMED** (`BrainstormIdea.swift:11`, `SearchBooks.swift:20`) |
| 25 | `@Guide` arities | **THREE confirmed**: `@Guide(description:)`, `@Guide(.minimumCount(3))` / `@Guide(.count(2))` (guide only, no description), and `@Guide(description: "…", .count(3...8))` (both). |
| 26 | `.count` accepts `Int` *and* `ClosedRange<Int>` | **NEW** (`@Guide(.count(2))` vs `@Guide(…, .count(3...8))`) |
| 27 | `@Generable` on enums | **CONFIRMED** for `String`-raw + `CaseIterable`, `String`-raw + `Codable`, and **no raw type at all**. |
| 28 | `Tool` requires `name` | **CORRECTED** — `name` is **optional**; `CalculatePaperSize`/`ConvertMeasurement` declare only `description`. Works as `let` or as computed `var`. |
| 29 | — | **`Tool` has an `Output` associated type** (`typealias Output = String`), and `Arguments` may be supplied by `typealias` to an out-of-line `@Generable` type | **NEW** |
| 30 | Tool arguments | `@Generable struct Arguments: Sendable` written explicitly in all samples; fields may be **all-Optional**; a `@Generable` enum is a legal argument type. |
| 31 | Manual `Generable` conformance | **NEW**: `static var generationSchema: GenerationSchema` + `var generatedContent: GeneratedContent` + `init(_ content: GeneratedContent) throws`; helpers `GenerationSchema(type:description:properties:)`, `GenerationSchema.Property(name:type:)`, `GeneratedContent(properties:)`, `content.value(forProperty:)`. |
| 32 | Structured tool output | **NOT DEMONSTRATED** — every `call(arguments:)` in every archive returns `String`. UNVERIFIED. |

### 2.4 Multimodal prompting

| # | Item | Verdict |
|---|---|---|
| 33 | `Attachment` / `ImageAttachmentContent` / `ImageReference` (names only in our harvest, `:92`) | **CONFIRMED + fully worked**: `Attachment(uiOrNsImage).label(String)` inside a `Prompt {}`; **`ImageReference` is a `@Generable`-usable field type** and resolves via **`ImageReference.attachmentLabel: String`**. `ImageAttachmentContent` never appears at a call site. |
| 34 | `Prompt` builder | **NEW**: accepts `if let` bindings, interpolated strings, **and `[Prompt]` arrays spliced inline**; `Prompt {}` (empty) is valid; `Prompt("…")` value init also exists. |

### 2.5 Evaluations (Book Tracker)

| # | Our note said | The sample says | Verdict |
|---|---|---|---|
| 35 | `Evaluation`, `ModelSample`, `Loader`, `SampleGenerator`, `Metric`, `Evaluator`, `MetricsAggregator`, `EvaluationResult` … (names only) | all present | **CONFIRMED** |
| 36 | — | **`ModelSubject<T>`** with `init(value:)` and `init(value:transcript:)` — the return type of `subject(from:)` | **NEW**, and it was missing from our symbol list entirely. |
| 37 | — | `func subject(from sample: ModelSample<T>) async throws -> ModelSubject<T>` is the core `Evaluation` requirement | **NEW** |
| 38 | — | **`ModelSample<Value>` is generic over the expected/output type**; `ModelSample(prompt:expected:)` and `ModelSample(prompt:expected:instructions:expectations:)`; read back via `sample.promptDescription` (String) or `sample.prompt` (Prompt); `Codable` | **NEW** |
| 39 | `Loader` protocol | Concrete: **`ArrayLoader(samples:)`** and **`JSONLoader<T>(url:)`**; `dataset` is a **stored** property | **NEW** |
| 40 | `Metric` | `Metric(_ name: String)`; results via **`.passing()` / `.passing(rationale:)` / `.failing()` / `.failing(rationale:)` / `.scoring(Double)`** | **NEW** (the five factories) |
| 41 | `Evaluator` | **`Evaluator { input, subject in … }`** — a *two*-argument closure returning a metric result; collected in **`var evaluators: Evaluators`** (a result-builder type named `Evaluators`) | **NEW** |
| 42 | `ScoreDimension` | `ScoreDimension(_ name:, description:, scale: .numeric([Int: String]))`; exposes **`.metric`** for aggregation | **NEW** (the `.numeric` dictionary form and `.metric`) |
| 43 | `ModelJudgeEvaluator` | `ModelJudgeEvaluator(judge:dimensions:prompt:)`; `judge:` takes a model value (`SystemLanguageModel.default` **or** `SystemLanguageModel()`) | **NEW** |
| 44 | `ModelJudgePrompt` | `ModelJudgePrompt(instructions:evaluationTarget:reference:)` where `evaluationTarget: (Value) -> String` and **`reference: (ModelSample<Value>, _) -> [String: String]`** (a labelled dictionary, not a string) | **NEW** |
| 45 | `MetricsAggregator` | `func aggregateMetrics(using aggregator: inout MetricsAggregator)`; `.group(_:) { }`; `computeMean(of:)`, `computeStandardDeviation(of:)`, `computeVariance(of:)`, **`custom(of:label:) { [Double] -> Double }`** | **NEW** |
| 46 | `.evaluates` Swift Testing trait | **`.evaluates(evaluation)`** and **`.evaluates(evaluation, info: [String: String])`**; the evaluation must be a `static let` on the suite | **NEW** |
| 47 | `EvaluationResult` | Reached via **`EvaluationContext.current.result`** inside the `@Test` body; queried with **`result.aggregateValue(.mean(of: metric))`** and **`result.aggregateValue(.custom(label:))`** → `Double`. The test body never iterates samples. | **NEW** |
| 48 | `ToolCallEvaluator` | **`ToolCallEvaluator(allPass:percentagePass:)`** — two `Metric`s | **NEW** |
| 49 | `TrajectoryExpectation` | Four inits: `(unordered:)`, `(ordered:allowsAdditionalToolCalls:)`, `(unordered:disallowed:)`, `(expected:arguments:)` | **NEW** |
| 50 | `ArgumentMatcher` | Call-site type is **`ToolExpectation(_ name:)` / `ToolExpectation(_ name:, arguments:)`**; matchers are `.exact(argumentName:value:)`, `.naturalLanguage(argumentName:criteria:)`, `.keyOnly(argumentName:)`, `.oneOf(argumentName:allowedValues:)`, `.contains(argumentName:substring:)`, `.hasSuffix(argumentName:suffix:)`, `.range(argumentName:minimum:maximum:)`; values wrapped as `.string(_)` | **NEW** (we had the type name only) |
| 51 | — | **`session.transcript.structuredTranscript`** — required to feed `ToolCallEvaluator` via `ModelSubject(value:transcript:)` | **NEW** |
| 52 | `SampleGenerator` | **`SampleGenerator<S>(_ prompt: Prompt, samples:targetCount:sessionProvider:validator:)`**; `sessionProvider: () -> LanguageModelSession` (a factory); `validator: (S) -> Bool`; `.run()` is an async sequence of valid samples; it is an **actor** exposing `await .samples` / `await .invalidSamples` | **NEW** |
| 53 | Cohen's-kappa judge alignment | **CONFIRMED as a technique**, but **the framework ships no agreement statistic** — `Statistics.cohensKappa` is 72 lines of hand-rolled Swift in the sample. Threshold used: κ > 0.6. | **CORRECTED** (don't imply it's built in) |
| 54 | — | `.xcevalresult` on-disk shape: `{"results":[{"Input":"<escaped JSON>","Response":{"value":"…"}}]}` where `Input` decodes to `{"input":{"prompt":"…"}}` | **NEW** |

### 2.6 Core Spotlight / `SpotlightSearchTool`

| # | Item | Verdict |
|---|---|---|
| 55 | `SpotlightSearchTool(configuration:)` with `sources:` + `guide:` | **NEW** (exact shape) |
| 56 | `.coreSpotlight(.init(searchableIndexDelegate:fetchAttributes:))` source case | **NEW**. The `FileSource` mentioned in session 246 is **not exercised** — UNVERIFIED. |
| 57 | Guidance profiles | **`.focused()`** (with parens — has defaulted params) and **`.complete`** (no parens). Sample picks `.focused()` on-device, `.complete` for server. | **NEW** |
| 58 | `SearchableItemAttribute` | A `RawRepresentable` struct: statics `.title`, `.contentDescription`, `.namedLocation`, `.stateOrProvince`, `.keywords`, `.latitude`, `.longitude`, `.rating`, `.duration`, `.contentCreationDate`, `.completionDate`, **plus `init(rawValue:)` to admit `CSCustomAttributeKey.keyName`** | **NEW** |
| 59 | Index delegate `searchableItems(forIdentifiers:)` | Full signature: **`nonisolated func searchableItems(forIdentifiers: [String], searchableItemsHandler: @escaping @Sendable ([CSSearchableItem]) -> Void)`** | **CONFIRMED + refined** |
| 60 | — | **`tool.searchResults`** is an `AsyncSequence`; `reply.content` is a **non-frozen** enum with `.items`, `.scoredItems`, `.groupedItems`, `.count`, `.table`, `.statistic`, `.text` (+ `@unknown default`). Element accessors: `.item`, `.item.item` (scored), dictionary values (grouped). | **NEW** |
| 61 | Model-facing tool name | **`spotlight_search`** (snake_case), per the sample's own instructions text | **NEW** |
| 62 | Entitlements | **None required** — the sample's `.entitlements` is an empty `<dict/>` | **NEW** |
| 63 | "Custom pipeline stages" / sentiment-analysis `PipelineStage` (session 246) | **ABSENT from the sample** | **UNVERIFIED** |
| 64 | "Contact resolver" (session 246) | **ABSENT from the sample** | **UNVERIFIED** |

### 2.7 Speech

| # | Item | Verdict |
|---|---|---|
| 65 | `SpeechAnalyzer(modules:)`, `SpeechTranscriber(locale:transcriptionOptions:reportingOptions:attributeOptions:)`, `AnalyzerInput(buffer:)`, `AssetInventory.assetInstallationRequest(supporting:)`, `.reservedLocales`, `.release(reservedLocale:)`, `bestAvailableAudioFormat(compatibleWith:)`, `finalizeAndFinishThroughEndOfInput()` | **CONFIRMED** (but from the **iOS 26** sample) |
| 66 | `DictationTranscriber`, `CaptureInputSequenceProvider`, `SFCustomLanguageModelData`, the `datagenerator` CLI | **NO SAMPLE EXISTS.** The speech sample was never refreshed for WWDC26. Doc index confirms `DictationTranscriber` + `Preset` statics exist; everything else must be sourced from docs/transcripts. | **UNVERIFIED by sample** |

### 2.8 Not demonstrated by ANY sample (still UNVERIFIED)

`DynamicInstructionsForEach`, `DynamicInstructions.SessionProperty`,
`LanguageModelSession.DynamicProfileModifier` (custom modifiers), `@SessionProperty(\.history)`,
`.samplingMode`, `GenerationOptions`, `ContextOptions(reasoningLevel:)` as a standalone value,
`toolCallMode`/`.required`, `LanguageModelSession.Usage`,
`PrivateCloudComputeLanguageModel.QuotaUsage` / `.Availability`, `LanguageModelFeedback`,
`Transcript.CustomSegment`, `LanguageModelError.rateLimited`, `.unsupportedGenerationGuide`,
structured (non-`String`) tool output, `ScoreDimension` scales other than `.numeric`.

---
## 3. Origami — Dynamic Profiles, DynamicInstructions, orchestration, PCC

Archive: `OrigamiCraftingADynamicTutorialForAppleIntelligence/`. Single app target `Origami`.
61 Swift files. Uses **SwiftData** (`@Model`), **SwiftUI**, **Observation** (`@Observable`), `os` logging.

### 3.1 File tree of the AI-relevant code

```
Origami/
├── OrigamiApp.swift
├── Models/
│   ├── Orchestrator.swift            (702 lines — the event-driven brain)
│   ├── OrchestratorProfile.swift     (75  — THE DynamicProfile)
│   ├── OrchestratorState.swift       (55  — mode/event/effect enums)
│   ├── TranscriptRecorder.swift      (77  — dumps Transcript to JSON)
│   ├── Error+DisplayMessage.swift    (37  — error taxonomy → UI copy)
│   └── DataModels/{Project,Photo,TutorialTemplate,TutorialTemplateStore,TermLookup,DataModel}.swift
├── Brainstorm/
│   ├── BrainstormInstructions.swift  (130 — DynamicInstructions + prompt extensions)
│   ├── BrainstormIdea.swift          (@Generable list w/ .minimumCount)
│   ├── CraftDomain.swift             (@Generable enum)
│   ├── ImageAnalysis.swift           (@Generable using ImageReference)
│   └── BrainstormModel.swift         (stream consumption)
├── Tutorial/Intelligence/
│   ├── TutorialInstructions.swift    (83  — conditional DynamicInstructions)
│   ├── OrigamiInstructions.swift     (31  — the "OrigamiExpert" component)
│   ├── CraftTools.swift              (92  — 3 Tool conformances)
│   ├── OrigamiTemplate.swift         (@Generable enum: String, CaseIterable)
│   └── TutorialContent.swift         (nested @Generable tree)
├── Coach/
│   ├── CoachInstructions.swift       (36 — nested DynamicInstructions + tools)
│   ├── MovePhotoToStepTool.swift     (38 — Tool that mutates app state)
│   └── CoachModel.swift             (74 — ResponseStream<String> consumption)
└── Terms/
    ├── TermInstructions.swift        (38 — conditional Instructions)
    ├── TermExtractor.swift           (66 — a *separate* one-shot session)
    └── TermModel.swift              (207)
```

### 3.2 `OrchestratorProfile` — the real `DynamicProfile`, verbatim

`Origami/Models/OrchestratorProfile.swift:11-75`:

```swift
struct OrchestratorProfile: LanguageModelSession.DynamicProfile {
    var orchestrator: Orchestrator

    // Brainstorm and tutorial work best on a server model. The sample
    // defaults to the on-device system model so it runs out of the box.
    // To use Private Cloud Compute, request access to the managed
    // `com.apple.developer.private-cloud-compute` entitlement at
    // https://developer.apple.com/contact/request/private-cloud-compute/,
    // then replace the `serverModel` initialization with the line below.
    // var serverModel = PrivateCloudComputeLanguageModel()
    var serverModel = SystemLanguageModel()

    var body: some DynamicProfile {
        switch orchestrator.mode {
        case .brainstorm:
            if !isOnDevice {
                Profile {
                    BrainstormInstructions(orchestrator: orchestrator)
                }
                .model(serverModel)
                .temperature(1.0)
            } else {
                // Brainstorming is lower-quality on-device than with
                // Private Cloud Compute.
                Profile {
                    BrainstormInstructions(orchestrator: orchestrator)
                }
                .model(SystemLanguageModel())
            }

        case .tutorial:
            if !isOnDevice {
                Profile {
                    TutorialInstructions(orchestrator: orchestrator)
                }
                .model(serverModel)
                .reasoningLevel(.deep)
            } else {
                // Tutorial generation is lower-quality on-device than with
                // Private Cloud Compute.
                Profile {
                    TutorialInstructions(orchestrator: orchestrator)
                }
                .model(SystemLanguageModel())
                .historyTransform(shortHistory(_:))
            }
        case .term:
            Profile {
                TermInstructions(orchestrator: orchestrator)
            }
            .model(SystemLanguageModel())
            .historyTransform(shortHistory(_:))
        }
    }

    private var isOnDevice: Bool {
        type(of: serverModel) == SystemLanguageModel.self
    }

    /// Returns the most recent four entries so longer on-device sessions
    /// stay within the smaller context window.
    private func shortHistory(_ entries: [Transcript.Entry]) -> [Transcript.Entry] {
        entries.suffix(4)
    }
}
```

**Seven corrections/confirmations packed into 75 lines** — see §2 for the consolidated list.
Highlights:

- Conformance is the **nested** `LanguageModelSession.DynamicProfile`. ✅ (matches our note's
  "working conclusion").
- But **`var body: some DynamicProfile`** — the *short* spelling. Apple's own code does **not**
  write `some LanguageModelSession.DynamicProfile` here. This works because the protocol vends
  nested typealiases (`DynamicProfile`, `Profile`) visible inside a conforming type — the exact
  SwiftUI `View`/`some View` ergonomic. **Our guide should show the short form**, matching Apple.
- **`Profile { … }.model(…)`, not `Profile(model:) { … }`.** Our reconstruction from 242 used
  `Profile(model: PrivateCloudComputeLanguageModel()) { … }`. The compiling code uses a trailing
  content closure plus a **`.model(_:)` modifier**. (The `init(model:)` form may also exist —
  UNVERIFIED — but the sample never uses it.)
- **`.temperature(1.0)`** — `Double` literal, not `.temperature(1)` as our note reconstructed.
- **`.reasoningLevel(.deep)`** ✅ exactly as reconstructed.
- **`.historyTransform(_:)` takes `([Transcript.Entry]) -> [Transcript.Entry]`** — a plain function
  reference works (`shortHistory(_:)`). It is **NOT** handed a `Transcript`; it's handed the entry
  array. This resolves the UNVERIFIED note at `fm-advanced.md:412`.
- **`SystemLanguageModel()`** — a plain initializer. Not `SystemLanguageModel.default`. Origami never
  writes `.default` anywhere.
- **`if/else` inside the `DynamicProfileBuilder` is legal**, alongside `switch`. Our note said the
  builder "enforces a hard constraint at compile time so exactly one `Profile` is active" and warned
  against "parallel `if` blocks" — the sample shows `if !x { … } else { … }` (an if-*else*, so still
  exactly one branch) is the sanctioned shape.
- **PCC is opt-in-by-comment.** The sample ships on-device and tells you to request the managed
  entitlement `com.apple.developer.private-cloud-compute` at
  `https://developer.apple.com/contact/request/private-cloud-compute/`, then swap one line.
  The `.entitlements` file ships with only `com.apple.security.app-sandbox`.
- **`type(of:) == SystemLanguageModel.self` is the runtime model-kind test** the sample uses to
  branch quality expectations. Slightly hacky, but it's Apple's own idiom here.
- **Model choice is a *property* of the profile struct, not of each branch.** `serverModel` is stored
  once and referenced from multiple branches — this is what makes flipping to PCC a one-line change.

### 3.3 `DynamicInstructions` — three real conformances

**(a) The reusable expert component** — this is the thing 242 called "OrigamiExpert".
Its real name is `OrigamiInstructions`. `Origami/Tutorial/Intelligence/OrigamiInstructions.swift:11-31`:

```swift
struct OrigamiInstructions: DynamicInstructions {
    var body: some DynamicInstructions {
        Instructions(
            """
            To generate an origami tutorial, always call the \
            fetchOrigamiTemplate tool first and base your tutorial \
            on the project template retrieved by that tool.

            Next when generating a tutorial:
            - Try to use standard Origami terminology
            - Clearly state how the paper should look at the end of each \
            step
            - Instead of saying "repeat steps..." fully list out all steps \
            in a clear way e.g. "Now repeat step N for the right side"
            """
        )

        // Fetch the templates tool.
        FetchOrigamiTemplate()
    }
}
```

Confirms: **protocol is bare `DynamicInstructions`** (top-level, *not* nested under
`LanguageModelSession`), `body: some DynamicInstructions`, and the builder accepts an
`Instructions(...)` value **and bare `Tool` instances side by side**. ✅ matches 242:39–42.

**(b) Conditional nesting + mode switching inside instructions.**
`Origami/Tutorial/Intelligence/TutorialInstructions.swift:12-42`:

```swift
struct TutorialInstructions: DynamicInstructions {
    let orchestrator: Orchestrator

    var body: some DynamicInstructions {
        if orchestrator.tutorialReady {
            CoachInstructions(orchestrator: orchestrator)
        } else {
            Instructions {
                """
                You are an expert craft AI assistant. Your job is to generate \
                step-by-step tutorial instructions for a craft project. …
                DO NOT use the word "I" or mention yourself in the tutorial.
                """
            }

            if orchestrator.project.craftDomain == .origami {
                // Origami specific tools and instructions.
                OrigamiInstructions()
            }
        }
    }
}
```

This is the single most instructive listing in the whole archive:
- **Nesting confirmed** — `CoachInstructions` and `OrigamiInstructions` are used as *values* inside
  another `DynamicInstructions` body. ✅ 242:42 "nesting … will concatenate the instructions and tools".
- **A bare `if` with no `else`** is legal in `DynamicInstructionsBuilder` (line 36-39) — unlike the
  profile builder's one-active-Profile constraint.
- **Both `Instructions(…)` (value init) and `Instructions { … }` (builder) spellings appear**, in
  adjacent files. Both compile.
- **The "phone-a-friend"/baton-pass is implemented as an instructions swap, not a new session.**
  When `orchestrator.tutorialReady` flips (which is `coach.isActive`, `Orchestrator.swift:99-101`),
  the *same* `LanguageModelSession` re-evaluates its profile and the tutorial-generator persona is
  replaced wholesale by the coach persona — **with the whole conversation transcript intact**.

**(c) Conditional extra knowledge, no tools.** `Origami/Terms/TermInstructions.swift:13-38`:

```swift
struct TermInstructions: DynamicInstructions {
    let orchestrator: Orchestrator

    var body: some DynamicInstructions {
        Instructions(
            """
            You explain crafting terminology to beginners.
            - 1-3 short sentences. Plain language. No preamble.
            - If given the step the user is on, ground the answer in what they're \
            physically doing.
            - For follow-ups: answer directly, don't restate the term.
            """
        )

        if orchestrator.project.craftDomain == .origami {
            Instructions(
                """
                This craft is origami. Common Origami terms include:
                valley fold, mountain fold, centerline, inside reverse fold,
                kite base, triangle base, waterbomb base... and many others.
                """
            )
        }
    }
}
```

**(d) The coach — instructions + a fresh tool set.** `Origami/Coach/CoachInstructions.swift:12-36`:

```swift
struct CoachInstructions: DynamicInstructions {
    let orchestrator: Orchestrator

    var body: some DynamicInstructions {
        Instructions {
            """
            You are an expert craft tutorial coach.
            When you are asked to valuate the user's in-progress work \
            from a photo: compare their work against the tutorial step \
            they appear to be on and provide specific, constructive feedback.
            …
            If the photo appears like they did the step incorrectly, \
            first check if it might be correct for a **different** step \
            ahead in the tutorial. Next help them find the correct step or else \
            kindly guide them towards a fix. To move a photo to the correct step. \
            call the movePhotoToStep tool.
            """
        }

        CalculatePaperSize()
        ConvertMeasurement()
        MovePhotoToStepTool(orchestrator: orchestrator)
    }
}
```

Note: **three tools appear/disappear atomically with the persona.** In tutorial mode the session has
`FetchOrigamiTemplate` only; the instant `tutorialReady` is true it has
`CalculatePaperSize`/`ConvertMeasurement`/`MovePhotoToStepTool` and *not* `FetchOrigamiTemplate`.
That's the "swap tools in and out" claim, made concrete.

**Nothing in Origami uses** `DynamicInstructionsForEach`, `DynamicInstructions.SessionProperty`,
`DynamicProfileModifier`, `.samplingMode`, `GenerationOptions`, `ContextOptions`, `prewarm()`, or
`toolCallMode`/`required`. Those API surfaces are **UNVERIFIED by sample code**.

### 3.4 Session construction with a profile AND a seeded history

`Origami/Models/Orchestrator.swift:41-47` — **this initializer was not in our notes**:

```swift
    @ObservationIgnored
    private lazy var session = LanguageModelSession(
        profile: OrchestratorProfile(orchestrator: self),
        history: Transcript(
            entries: startHistory
        )
    )
```

So the shape is **`LanguageModelSession(profile:history:)`** — our harvest listed
`init(profile: sending some LanguageModelSession.DynamicProfile, …)` but did not record the
`history:` label or that it takes a `Transcript`. Note the retain cycle avoidance:
`private lazy var` + `@ObservationIgnored`, with `self` captured — the profile holds the
orchestrator, the orchestrator lazily holds the session.

**Hand-authored transcript seeding** (`Orchestrator.swift:103-139`) — a pattern nothing in the
sessions mentions. It fabricates *assistant* turns to prime the model with app state:

```swift
    var startHistory: [Transcript.Entry] {
        var desc: [Transcript.Entry] = []

        desc.append(
            .response(
                Transcript.Response(
                    assetIDs: [""],
                    segments: [
                        .text(
                            Transcript
                                .TextSegment(
                                    content: "I can see the user's current project is: \(project.description)"
                                )
                        )
                    ]
                )
            )
        )
        if project.hasTutorial {
            desc.append(
                .response(
                    Transcript.Response(
                        assetIDs: [""],
                        segments: [ .text(Transcript.TextSegment(
                            content: "The user's project has a tutorial: \(project.tutorialDescription)")) ]
                    )
                )
            )
        }
        return desc
    }
```

Confirmed spellings: `Transcript.Entry.response(_:)`, `Transcript.Response(assetIDs:segments:)`,
`Transcript.Segment.text(_:)`, `Transcript.TextSegment(content:)`.
**`assetIDs: [""]` is required and is passed an array containing an empty string** — an
undocumented wart worth calling out in a guide (it's `[String]`, not optional).

Also: `Transcript` is **`Encodable`** — `TranscriptRecorder.swift:57-67` does
`try JSONEncoder().encode(transcript)` with `.prettyPrinted, .sortedKeys` and writes it to
`~/Documents/OrigamiTranscripts/<title>_<timestamp>.json`, gated behind a `UserDefaults` debug
toggle, re-snapshotted after **every** effect (`Orchestrator.swift:173-178`). **This is a
genuinely reusable debugging harness** and no WWDC session mentions it.

`session.isResponding` is used as a re-entrancy guard at `Orchestrator.swift:367`.

### 3.5 Prompting: `Prompt` builder, arrays of prompts, and multimodal attachments

`Prompt { }` accepts interpolated strings, `if let` bindings, and **`[Prompt]` arrays spliced
inline**. `Origami/Models/Orchestrator.swift:596-616`:

```swift
            var imagePrompts: [Prompt] = []
            for photo in photos {
                imagePrompts.append(try await photo.toPrompt())
            }
            …
            let prompt = Prompt {
                if let note {
                    note
                }
                "I'm on section \(sectionIndex) step number \(stepNumber) of the tutorial. How does this look?"
                imagePrompts
                "For reference the step reads: \(stepContent ?? "")"
            }
            let stream = session.streamResponse(to: prompt)
```

**The attachment API, verbatim** (`Origami/Models/DataModels/Photo.swift:77-91`):

```swift
    func toPrompt() async throws -> Prompt {
        #if canImport(UIKit)
        guard let image = UIImage(data: data) else {
            return Prompt {}
        }
        #elseif canImport(AppKit)
        guard let image = NSImage(data: data) else {
            return Prompt {}
        }
        #endif
        let idImage = Attachment(image).label(idString)
        return Prompt {
            idImage
        }
    }
```

- **`Attachment(_:)` takes a `UIImage`/`NSImage` directly** — no intermediate `ImageAttachmentContent`
  construction at the call site.
- **`.label(_:)` is a modifier returning an attachment usable in a `Prompt` builder.**
- `Prompt {}` (empty) is a valid graceful-degradation value.
- The label is app-generated and stable: `"Photo_\(id.uuidString.prefix(6))"` (`Photo.swift:65-67`).

**`ImageReference` closes the loop.** A `@Generable` struct can contain an `ImageReference` field, and
the model fills it with the label of the attachment it's talking about
(`Origami/Brainstorm/ImageAnalysis.swift:11-21`):

```swift
@Generable
struct ImageAnalysis {
    var image: ImageReference
    var analysis: String

    @Guide(
        description:
            "What do you think the *purpose* of this photo is for the project?"
    )
    var typeOfImage: ImageCategory
}
```

and the app resolves it via **`ImageReference.attachmentLabel`**
(`Origami/Brainstorm/BrainstormModel.swift:142-144` and `:168-171`):

```swift
            let photo = project.photos.first { photo in
                photo.idString == image.attachmentLabel
            }
```
```swift
                for item in partialResponse.content.images ?? [] {
                    // Need at least an ID to start streaming.
                    if let id = item.image?.attachmentLabel {
```

**This is the single most valuable undocumented-in-transcripts pattern in the archive**: multi-image
prompting where the structured output is *keyed back to specific input images*. Label your
attachments with app-side IDs, declare `ImageReference` in the `@Generable`, read `.attachmentLabel`.

### 3.6 `@Generable` / `@Guide` exact spellings observed

| Spelling | File:line |
|---|---|
| `@Generable struct TutorialContent: Codable` with **nested `@Generable` structs** | `Tutorial/Intelligence/TutorialContent.swift:9-44` |
| `@Generable(description: "A single brainstorm idea")` | `Brainstorm/BrainstormIdea.swift:11` |
| `@Guide(.minimumCount(3))` — **no description argument** | `Brainstorm/BrainstormIdea.swift:20` |
| `@Guide(description: "…")` on a property of a nested type | `Tutorial/Intelligence/TutorialContent.swift:38-42` |
| `@Generable enum OrigamiTemplate: String, CaseIterable` (raw values incl. hyphens: `"cat-or-dog-face"`) | `Tutorial/Intelligence/OrigamiTemplate.swift:10-19` |
| `@Generable enum CraftDomain: String, Codable` | `Brainstorm/CraftDomain.swift:10-15` |
| `@Generable enum ImageCategory: String, Codable` with **sentence-length raw values** (`case craftInspiration = "inspiration for the craft"`) | `Brainstorm/ImageAnalysis.swift:23-27` |
| `@Generable private struct ExtractedTerms: Codable` — **`private` + `@Generable` compiles** | `Terms/TermExtractor.swift:14-17` |
| Optional `@Generable` fields (`var difficulty: TextSection?`) | `Tutorial/Intelligence/TutorialContent.swift:36` |

Note the enum-raw-value trick in `ImageCategory`: the raw string *is* the prompt-facing description.
Also `@Generable` types double as `Codable` for SwiftData persistence — `TutorialContent` is
JSON-encoded into `project.tutorialJSON` and decoded back (`Orchestrator.swift:565-566`).

### 3.7 Tools

`Origami/Tutorial/Intelligence/CraftTools.swift:12-32`:

```swift
struct FetchOrigamiTemplate: Tool {
    let description = "Fetch a relevant starting origami template to adapt into a tutorial."
    let name = "fetchOrigamiTemplate"

    @Generable
    struct Arguments: Sendable {
        @Guide(description: "A theme or topic for the origami project")
        var topic: String

        @Guide(description: "Origami starter template that best matches the theme")
        var templateMatch: OrigamiTemplate
    }

    func call(arguments: Arguments) async throws -> String {
        logger.debug("[fetchOrigamiTemplate] tool call: \(arguments.templateMatch.rawValue)")
        if let body = await TutorialTemplateStore.template(for: arguments.templateMatch.rawValue) {
            return body
        }
        return "No template available. Please try your best to generate folding instructions."
    }
}
```

Confirmations:
- `Tool` requires `description`; **`name` is optional** — `CalculatePaperSize` and
  `ConvertMeasurement` (`CraftTools.swift:34`, `:54`) declare **only** `description` and rely on the
  derived name.
- `@Generable struct Arguments: Sendable` — the explicit `Sendable` conformance is written out in
  all four tools in the archive.
- **`func call(arguments:) async throws -> String`** — every tool in every sample returns `String`,
  never a `ToolOutput`/`@Generable` type. (Structured tool output is UNVERIFIED by samples.)
- A `@Generable` **enum can be a tool argument type** (`templateMatch: OrigamiTemplate`).
- **Graceful degradation inside a tool**: on lookup failure it returns *prose instructions to the
  model* rather than throwing (`CraftTools.swift:30`). Excellent pattern.

`Origami/Coach/MovePhotoToStepTool.swift:12-38` shows a **tool that mutates app state and
returns control to the UI**:

```swift
struct MovePhotoToStepTool: Tool {
    let name = "movePhotoToStep"
    let description =
        "Move a photo the user gave you to the correct step of a tutorial."

    var orchestrator: Orchestrator

    @Generable
    struct Arguments: Sendable {
        @Guide(description: "Section to move the photo TO")
        var tutorialSectionIndex: Int

        @Guide(description: "Step to move the photo TO")
        var tutorialStepNumber: Int
    }

    func call(arguments: Arguments) async throws -> String {
        …
        await orchestrator.proposeMoveToStep(
            section: arguments.tutorialSectionIndex,
            step: arguments.tutorialStepNumber
        )
        return "Asked the user to confirm moving to step \(arguments.tutorialStepNumber)."
    }
}
```

The tool **holds a reference to the app's observable model** (`var orchestrator: Orchestrator`) and
its return string tells the model that a *human confirmation* is now pending. The UI then swaps the
follow-up text field for a Yes/No prompt, and the answer is fed back as a new user turn
(`Orchestrator.swift:500-561`). **Human-in-the-loop tool calling, fully worked** — no session covers this.

### 3.8 Error handling — the complete taxonomy, verbatim

`Origami/Models/Error+DisplayMessage.swift:12-36` is the single best artifact in the archive for
confirming the iOS 27 error redesign:

```swift
extension Error {
    /// A short message describing the error, suitable for display in the UI.
    var displayMessage: String {
        if self is SystemLanguageModel.Error {
            return "Apple Intelligence isn't available right now."
        }
        if let modelError = self as? LanguageModelError {
            switch modelError {
            case .timeout:
                return "This is taking longer than expected. Please try again."
            case .guardrailViolation, .refusal:
                return "Origami can't work with that. Try a different photo or prompt."
            case .contextSizeExceeded:
                return "There's too much in this conversation. Try regenerating to start fresh."
            case .unsupportedLanguageOrLocale:
                return "Origami doesn't support this language."
            default:
                break
            }
        }
        if self is GeneratedContent.ParsingError {
            return "Origami had trouble understanding the response. Please try again."
        }
        return "Something went wrong. Please try again."
    }
}
```

Confirms as **real, compiling case names on `LanguageModelError`**:
`.timeout`, `.guardrailViolation`, `.refusal`, `.contextSizeExceeded`, `.unsupportedLanguageOrLocale`.
Confirms **`SystemLanguageModel.Error`** and **`GeneratedContent.ParsingError`** exist as distinct types.
Note the `default: break` — `LanguageModelError` is **non-frozen / has more cases** than these five.
Also note the cases are matched **without binding associated values**, which is valid for payload cases.

`SystemLanguageModel.Error` is checked **first**, before `LanguageModelError` — availability failures
are a *different* type from generation failures, and they do not appear as a `LanguageModelError` case.

**Cancellation is handled as a first-class, non-error outcome** everywhere
(`Orchestrator.swift:353, 374, 396, 415, 439, 453, 624, 652`):

```swift
        } catch is CancellationError {
            brainstorm.state = .idle
            log("analyzing photos completed -> canceled")
        } catch {
            brainstorm.state = .error(error.displayMessage)
        }
```

with `try Task.checkCancellation()` after each stream completes, and
`currentTask?.cancel()` at the head of every event (`Orchestrator.swift:167`).

**No availability check anywhere.** Origami never calls `SystemLanguageModel.availability`, never
uses `@available`/`#available` guards, and never gates UI on model readiness. It relies **entirely**
on catching `SystemLanguageModel.Error` at use time and surfacing `displayMessage`. Worth flagging in
a guide as Apple's own (arguably under-defensive) posture — the deployment target is 27.0 so
`#available` is moot, but the *runtime* Apple-Intelligence-disabled path is handled reactively only.

### 3.9 Streaming consumption

Two shapes, both in the archive.

**Structured** (`Brainstorm/BrainstormModel.swift:103-124` / `:161-179`): iterate
`LanguageModelSession.ResponseStream<T>`; `partialResponse.content` is the partially-generated
projection where **every field is Optional** (`partialResponse.content.ideas` is `[…]?`,
`partialIdea.title` is `String?`). Note the UI trick at `BrainstormModel.swift:120-123`:

```swift
                // When the model starts a new idea, all earlier ones are
                // finalized — reveal those, but keep the in-progress one hidden
                // so its text doesn't grow visibly midstream.
                completedNewIdeasCount = max(completedNewIdeasCount, newIdeas.count - 1)
```

**Reveal N-1 items during streaming, all N at the end.** A polish pattern for guided generation that
avoids the "text visibly growing" jitter. Nothing in the sessions mentions it.

**Free-text** (`Coach/CoachModel.swift:58-73`): `ResponseStream<String>` whose `partial.content` is a
plain `String` (already-accumulated, not a delta):

```swift
    func processStream(_ stream: LanguageModelSession.ResponseStream<String>) async throws {
        state = .loading
        var accumulated = ""
        var didReceivePartial = false
        for try await partial in stream {
            didReceivePartial = true
            accumulated = partial.content
            state = .responded(accumulated)
        }
        // If the stream finished without ever yielding text (for example, the model
        // only returned a tool call), land on `.responded("")` so the UI
        // exits the loading state and the follow-up field returns.
        if !didReceivePartial {
            state = .responded("")
        }
    }
```

**Critical edge case Apple documents here and nowhere else: a stream can complete having yielded
zero partials when the model only emitted a tool call.** Any UI that leaves a spinner up until the
first partial will hang forever. Guide-worthy.

### 3.10 One-shot side sessions

Not everything goes through the orchestrated session. `Terms/TermExtractor.swift:32-39` spins up a
disposable session with the legacy initializer:

```swift
        let session = LanguageModelSession(
            model: SystemLanguageModel(),
            instructions: instructions(for: craftDomain)
        )
        let response = try await session.respond(
            to: body,
            generating: ExtractedTerms.self
        )
```

Confirms **`LanguageModelSession(model:instructions:)` accepts `SystemLanguageModel()`** and
`respond(to:generating:)` → `.content`. It also shows a **hallucination filter**
(`TermExtractor.swift:48-51`) — drop any extracted term that doesn't literally appear in the source:

```swift
            // Drop anything the model invented or paraphrased that
            // doesn't actually appear in the tutorial text.
            guard body.range(of: term, options: .caseInsensitive) != nil else { continue }
```

And a **cache-before-inference** pattern in `TermModel.explain` (`Terms/TermModel.swift:87-99`):
a project-wide lookup table is consulted first and "skip[s] the LLM call entirely" on a hit.

### 3.11 Orchestration architecture (event → reduce → effect)

`OrchestratorState.swift` declares three flat enums — `OrchestratorMode` (3 cases),
`OrchestratorEvent` (11 cases), `OrchestratorEffect` (9 cases) — and `Orchestrator.send(_:)`
(`Orchestrator.swift:165-179`) is a Redux-style loop:

```swift
    func send(_ event: OrchestratorEvent) {
        log("event: \(event)")
        currentTask?.cancel()
        if state.mode == .term {
            dismissTerm()
        }
        let effects = reduce(event)
        guard !effects.isEmpty else { return }
        currentTask = Task {
            for effect in effects {
                await execute(effect)
                snapshotTranscript()
            }
        }
    }
```

`reduce` is **pure-ish state mutation returning `[OrchestratorEffect]`**; `execute` performs the
async model work. Because the profile's `body` reads `orchestrator.mode` (an `@Observable`
property), mutating `state.mode` inside `reduce` **is** the profile switch. That is the whole
mechanism: *the DynamicProfile is a projection of your app's observable state machine.*

Two guard patterns worth stealing:
- **In-flight de-duplication keyed by logical target** (`Orchestrator.swift:64-65, 587-593`):
  `coachingInFlight: Set<String>` keyed `"\(section)-\(step)"`, with `defer { remove }`.
- **Orthogonal flows bypass the reducer.** Term lookups deliberately do *not* go through
  `send`/`reduce` so "a tap on a term shouldn't cancel an in-flight stream"
  (`Orchestrator.swift:661-687`). They call into `TermModel` with the shared `session` directly.


---

## 4. Book Tracker — the Evaluations framework

Archive: `BookTrackerUsingEvaluationsToEvaluateAnIntelligentFeature/`.
`MACOSX_DEPLOYMENT_TARGET = 27.0`, `SUPPORTED_PLATFORMS = "iphoneos iphonesimulator xros xrsimulator"`,
`SWIFT_VERSION = 5.0` (!). Five targets: 1 app, **2 unit-test bundles**, **2 command-line tools**.

```
BookTracker/                 (app)
  Services/BookTaggingService.swift   ← the feature under evaluation (101 lines)
  Services/BookSearchTools.swift      ← 3 Tools shared by app AND evals (267)
BookTrackerEvaluations/      (test bundle #1)
  BookTags.swift             (200)  heuristic + model-judge evaluation
  SyntheticBookTags.swift    (133)  same evaluation over a JSONLoader dataset
  SearchBooks.swift          (578)  ToolCallEvaluator + 16 TrajectoryExpectations
  synthetic_book_samples.json       100 generated samples
HillClimbingEvaluations/     (test bundle #2)
  ModelJudgeAlignmentEvaluation.swift (353)  Cohen's-kappa judge calibration
  Statistics.swift           (72)   hand-rolled Cohen's kappa
  BookTaggingEvaluation-extracted.json      expert-scored fixture
BookSampleGenerator/main.swift  (87)   CLI: SampleGenerator over PCC
DatasetExtractor/main.swift     (167)  CLI: parse .xcevalresult → JSON
```

### 4.1 The `Evaluation` protocol, verbatim

`BookTrackerEvaluations/BookTags.swift:17-30`:

```swift
import Evaluations
import Foundation
import FoundationModels
import Testing
@testable import BookTracker

struct BookTaggingEvaluation: Evaluation {
    func subject(from sample: ModelSample<BookTags>) async throws -> ModelSubject<BookTags> {
        let result = try await BookTaggingService.generateTags(for: sample.promptDescription)
        return ModelSubject(value: result)
    }

    /// Pairs each curated review with the maintainer's reference tags.
    var dataset = ArrayLoader(samples:
        Book.sampleBooks.map { book in
            ModelSample(prompt: book.review, expected: BookTags(tags: book.tags))
        }
    )
```

**Corrections/additions vs. our notes:**
- The requirement is **`func subject(from:) async throws -> ModelSubject<T>`** — a type
  **`ModelSubject`** that our API harvest **never listed** (we had `Evaluation`, `ModelSample`,
  `Loader`, `Metric`, `Evaluator`, …). `ModelSubject(value:)` and `ModelSubject(value:transcript:)`.
- **`ModelSample<Value>` is generic over the *expected/output* type**, not the input.
  `ModelSample(prompt:expected:)`; the input text is read back as **`sample.promptDescription`**
  (`String`) or **`sample.prompt`** (a `Prompt`, used at `SearchBooks.swift:551`).
- **`ArrayLoader(samples:)`** and **`JSONLoader(url:)`** are the two concrete `Loader`s.
  `JSONLoader` is generic: `var dataset: JSONLoader<ModelSample<BookTags>>`
  (`SyntheticBookTags.swift:25`).
- `dataset` is a **stored property**, not a computed one.

### 4.2 `Metric` and heuristic `Evaluator`s

`BookTags.swift:35-104`:

```swift
    let tagCount = Metric("Tag Count")
    let tagTotal = Metric("Tag Total")
    let hasGenreTag = Metric("Has Genre Tag")
    let wordCount = Metric("Word Count")

    var evaluators: Evaluators {
        // Tag count is within the required 3–8 range.
        Evaluator { _, subject in
            let count = subject.value.tags.count
            if count >= 3 && count <= 8 {
                return tagCount.passing(rationale: "\(count) tags")
            }
            return tagCount.failing(rationale: "Got \(count) tags, expected 3–8")
        }

        // Records raw tag count.
        Evaluator { _, subject in
            let count = subject.value.tags.count
            return tagTotal.scoring(Double(count))
        }

        // Tags must be single-word or hyphenated.
        Evaluator { _, subject in
            for tag in subject.value.tags where tag.contains(" ") {
                return wordCount.failing(rationale: "Tag \(tag) contains multiple words")
            }
            return wordCount.passing()
        }
        …
    }
```

Exact spellings confirmed:
- **`Metric(_ name: String)`** — positional label only.
- **`var evaluators: Evaluators`** — the associated type is a *result-builder* type named
  **`Evaluators`** (plural). Our notes never captured this name.
- **`Evaluator { input, subject in … }`** — a **two-argument** closure. First arg is the
  `ModelSample` (all four heuristics discard it as `_`); second is the `ModelSubject`.
- Metric result factories, all four observed: **`.passing()`**, **`.passing(rationale:)`**,
  **`.failing()`**, **`.failing(rationale:)`**, **`.scoring(_ value: Double)`**.
  Pass/fail are *not* booleans — they are metric-produced result values.
- `subject.value` is the typed model output.

### 4.3 `ScoreDimension` + `ModelJudgeEvaluator` + `ModelJudgePrompt`

`BookTags.swift:43-56` and `:107-123`:

```swift
    let relevance = ScoreDimension(
        "Relevance",
        description: """
            Whether each tag describes a quality, theme, or tone
            of the book itself rather than incidental details or
            the reader's personal reactions.
            """,
        scale: .numeric([
            4: "Every tag describes the book itself",
            3: "Most tags describe the book",
            2: "Some tags describe personal reactions",
            1: "Tags don't meaningfully describe the book"
        ])
    )
```
```swift
        // Overall tag quality — groundedness, coverage, specificity.
        ModelJudgeEvaluator(
            judge: SystemLanguageModel.default,
            dimensions: [relevance, usefulness],
            prompt: ModelJudgePrompt(
                instructions: """
                    You are evaluating tags generated for a personal book-tracking app where users
                    organize their library by browsing and filtering tags.
                    """,
                evaluationTarget: { value in
                    "\(value.tags.count) Generated tags: " + value.tags.joined(separator: ", ")
                },
                reference: { input, _ in
                    let expectedTags = input.expected?.tags.joined(separator: ", ")
                    return ["Expected Tags": expectedTags ?? "No expected tags defined"]
                }
            )
        )
```

Confirmed:
- **`ScoreDimension(_ name: String, description: String, scale: …)`**, positional name.
- **`.scale: .numeric([Int: String])`** — a *dictionary literal mapping score → anchor text*, and
  the sample uses **descending 4/3/2/1** in source order. Every dimension in the archive uses a
  4-point scale. (Other `scale` cases — e.g. binary/categorical — are UNVERIFIED.)
- **`ScoreDimension.metric`** — a dimension exposes an underlying `Metric` for aggregation
  (`relevance.metric`, `BookTags.swift:139`).
- **`ModelJudgeEvaluator(judge:dimensions:prompt:)`**; `dimensions` is `[ScoreDimension]`.
- **`judge:` takes a language model directly.** Two spellings appear in the same archive:
  `SystemLanguageModel.default` (`BookTags.swift:108`, `SyntheticBookTags.swift:98`) and
  `SystemLanguageModel()` (`ModelJudgeAlignmentEvaluation.swift:213`). **Both compile** — so
  `.default` does exist alongside the initializer, contrary to what Origami's exclusive use of
  `SystemLanguageModel()` might suggest.
- **`ModelJudgePrompt(instructions:evaluationTarget:reference:)`**, where
  `evaluationTarget: (Value) -> String` and **`reference: (ModelSample<Value>, _) -> [String: String]`**
  — a *dictionary* of labelled reference material, not a string. The second closure parameter is
  discarded in both usages (UNVERIFIED what it is; plausibly the `ModelSubject`).

### 4.4 `MetricsAggregator`

`BookTags.swift:129-142`:

```swift
    func aggregateMetrics(using aggregator: inout MetricsAggregator) {
        aggregator.group("Heuristics") { aggregator in
            aggregator.computeMean(of: tagCount)
            aggregator.computeStandardDeviation(of: tagTotal)
            aggregator.computeMean(of: tagTotal)
            aggregator.computeVariance(of: tagTotal)
            aggregator.computeMean(of: wordCount)
            aggregator.computeMean(of: hasGenreTag)
        }
        aggregator.group("Quality") { group in
            group.computeMean(of: relevance.metric)
            group.computeMean(of: usefulness.metric)
        }
    }
```

- Signature is **`func aggregateMetrics(using aggregator: inout MetricsAggregator)`** — `inout`.
- **`.group(_ label: String) { … }`** nests a sub-aggregator.
- Built-ins observed: **`computeMean(of:)`, `computeStandardDeviation(of:)`, `computeVariance(of:)`**.
- **`computeMean(of:)` over a pass/fail metric yields a pass *rate*** (used with `>= 0.8` thresholds).
- **`.custom(of:label:_:)`** for arbitrary statistics — see §4.7.

### 4.5 The `.evaluates` Swift Testing trait

`BookTags.swift:149-167`:

```swift
@Suite("Book Tag Evaluations")
struct BookTagEvaluationTests {
    static let evaluation = BookTaggingEvaluation()

    /// Metadata recorded alongside each run.
    static let evaluationInfo: [String: String] = [
        "Prompt": BookTaggingService.instructions,
        "ModelName": "SystemLanguageModel",
        "AppVersion": "1.0",
        "Feature": "Automatic tag generation from book reviews"
    ]

    @Test("Book Tag Evaluations", .evaluates(evaluation, info: evaluationInfo))
    func evaluateBookTagging() async throws {
        let result = EvaluationContext.current.result

        let rangeMetric = BookTagEvaluationTests.evaluation.tagCount
        #expect(result.aggregateValue(.mean(of: rangeMetric)) >= 0.8)
    }
}
```

Exact spellings:
- **`.evaluates(_ evaluation:)`** and **`.evaluates(_ evaluation:, info: [String: String])`** — both
  forms appear (`SearchBooks.swift:572` uses the bare form).
- The evaluation instance must be a **`static let`** on the suite so the test body can reach the
  same `Metric` identities. This is load-bearing, not stylistic.
- **`EvaluationContext.current.result`** — the trait runs the whole dataset *before* the test body,
  and the body is an assertion over the aggregate. **The test function never iterates samples.**
- **`result.aggregateValue(.mean(of: metric))` → `Double`**, and
  **`result.aggregateValue(.custom(label: String))`**.
- `info:` is free-form `[String: String]` and the sample uses it to **stamp the prompt text itself
  into the run record** — that is what makes cross-run "hill climbing" diffs meaningful.
- `@Suite("…", .serialized)` is used for the judge-calibration suite
  (`ModelJudgeAlignmentEvaluation.swift:337`).

### 4.6 Tool-call trajectory evaluation

`SearchBooks.swift:525-563` — the whole evaluation is 39 lines because `ToolCallEvaluator` does the work:

```swift
struct SearchToolEvaluations: Evaluation {
    var dataset = samples
    
    let pass = Metric("All Passed")
    let percent = Metric("Percentage Passed")
    
    var evaluators: Evaluators {
        ToolCallEvaluator(allPass: pass, percentagePass: percent)
    }

    var registeredTools: [any Tool] = [
        SearchBooksTool(books: Book.sampleBooks.map(\.snapshot)),
        GetBookDetailsTool(books: Book.sampleBooks.map(\.snapshot)),
        FindSimilarBooksTool(books: Book.sampleBooks.map(\.snapshot))
    ]

    func subject(from sample: ModelSample<BookResults>) async throws -> ModelSubject<BookResults> {
        let model = SystemLanguageModel(
            guardrails: .permissiveContentTransformations
        )
        let session = LanguageModelSession(
            model: model,
            tools: registeredTools,
            instructions: BookAssistant.instructions
        )

        let response = try await session.respond(to: sample.prompt, generating: BookResults.self)

        return ModelSubject(
            value: response.content,
            transcript: session.transcript.structuredTranscript
        )
    }
```

**Four findings our notes did not have:**
1. **`ToolCallEvaluator(allPass:percentagePass:)`** takes *two `Metric`s* — a strict all-or-nothing
   metric and a partial-credit percentage metric.
2. **`ModelSubject(value:transcript:)`** is how the trajectory reaches the evaluator, and the
   transcript is passed as **`session.transcript.structuredTranscript`** — a property on `Transcript`
   we had never seen. Without it, `ToolCallEvaluator` has nothing to inspect.
3. **`var registeredTools: [any Tool]`** is a plain stored property on the `Evaluation` — the name
   is the sample's own, not a protocol requirement, but the pattern (build the session yourself
   inside `subject(from:)`) is the sanctioned one.
4. **`SystemLanguageModel(guardrails: .permissiveContentTransformations)`** — an initializer
   parameter absent from our notes entirely. It appears in *both* the app service
   (`BookTaggingService.swift:40`) and the eval, i.e. **the evaluation must construct the model the
   same way the feature does, or you evaluate a different system.**

### 4.7 `TrajectoryExpectation` and the argument matchers

`ModelSample` gains two extra labels for tool-calling
(`SearchBooks.swift:46-74`):

```swift
    ModelSample(
        prompt: "gothic",
        expected: BookResults(books: [ … ]),
        instructions: BookAssistant.instructions,
        expectations: TrajectoryExpectation(unordered: [
            ToolExpectation(
                "searchBooks",
                arguments: [
                    .exact(argumentName: "tag", value: .string("gothic"))
                ]
            )
        ])
    ),
```

**`ModelSample(prompt:expected:instructions:expectations:)`.**

`TrajectoryExpectation` initializers observed (all four):

| Form | Where |
|---|---|
| `TrajectoryExpectation(unordered: [ToolExpectation])` | `SearchBooks.swift:66` |
| `TrajectoryExpectation(ordered: [ToolExpectation], allowsAdditionalToolCalls: true)` | `:140-154` |
| `TrajectoryExpectation(unordered: [...], disallowed: [ToolExpectation("findSimilarBooks")])` | `:344-359` |
| `TrajectoryExpectation(expected: "searchBooks", arguments: [...])` — single-call shorthand | `:413-418` |

**`ToolExpectation(_ name: String)`** and **`ToolExpectation(_ name: String, arguments: [...])`**.
Note `ToolExpectation` is the call-site type; our notes had `ArgumentMatcher` but not `ToolExpectation`.

**The complete argument-matcher vocabulary exercised by the sample** (these are the `ArgumentMatcher`
static factories):

| Matcher | Example | Line |
|---|---|---|
| `.exact(argumentName:value:)` | `.exact(argumentName: "tag", value: .string("gothic"))` | `:71` |
| `.naturalLanguage(argumentName:criteria:)` | `.naturalLanguage(argumentName: "mood", criteria: "Should relate to uplifting, hopeful, or positive feelings.")` | `:96-99` |
| `.keyOnly(argumentName:)` | `.keyOnly(argumentName: "bookId")` | `:150` |
| `.oneOf(argumentName:allowedValues:)` | `.oneOf(argumentName: "tag", allowedValues: [.string("strategy"), .string("epic"), .string("political intrigue")])` | `:172-176` |
| `.contains(argumentName:substring:)` | `.contains(argumentName: "tag", substring: "histor")` | `:202` |
| `.hasSuffix(argumentName:suffix:)` | `.hasSuffix(argumentName: "genre", suffix: "fiction")` | `:517` |
| `.range(argumentName:minimum:maximum:)` | `.range(argumentName: "limit", minimum: 1, maximum: 3)` | `:327` |

Values are wrapped: **`.string(_)`** (presumably a `GeneratedContent`-ish enum;
only `.string` appears in the archive — `.number`/`.bool` are UNVERIFIED).

**`.naturalLanguage` is the headline capability**: an LLM decides whether the argument the model
actually passed satisfies a prose criterion. That is how you write a trajectory expectation for
`"cheerful"` → `mood:` without pinning an exact string.

### 4.8 `Tool` gains an `Output` associated type

`BookTracker/Services/BookSearchTools.swift:106-120`:

```swift
struct SearchBooksTool: Tool {
    typealias Arguments = SearchBooksArguments
    typealias Output = String

    let books: [BookSnapshot]
    var collector: BookSearchCollector? = nil

    var name: String { "searchBooks" }
    var description: String {
        "Searches the user's personal book library by query, tag, mood, or genre. "
        + "Returns matching books with their IDs, titles, authors, and tags."
    }

    func call(arguments: SearchBooksArguments) async throws -> String {
```

- **`typealias Output = String`** — `Tool` has an `Output` associated type. Origami's tools never
  spell it (inferred from `call`'s return). Confirms structured tool output *is* representable.
- **`Arguments` can be an out-of-line `@Generable` type** via `typealias`, not just a nested struct.
- `name`/`description` as **computed properties** (`var … { }`) — Origami used `let`. Both work.
- Tool arguments can be **all-Optional** (`SearchBooksArguments` has 5 optional fields,
  `BookSearchTools.swift:69-84`) — the model picks which filters to fill.
- A tool can hold an **`actor`** for out-of-band result collection (`BookSearchCollector`,
  `:24-37`), letting the app observe the trajectory without touching the transcript.

### 4.9 Judge calibration with Cohen's kappa

`HillClimbingEvaluations/ModelJudgeAlignmentEvaluation.swift`. The trick: **the "subject" performs no
inference at all** — it replays a fixture of expert-scored samples so the only thing being measured
is the *judge* (`:166-169`):

```swift
    func subject(from sample: ModelSample<BookTagJudgmentValue>) async throws -> ModelSubject<BookTagJudgmentValue> {
        let value = sample.expected ?? .placeholder
        return ModelSubject(value: value)
    }
```

Custom aggregation joins judge scores to expert scores positionally (`:303-332`):

```swift
    func aggregateMetrics(using aggregator: inout MetricsAggregator) {
        let expertRelevance = Self.samples.map { $0.expected?.expertRelevanceScore ?? 0.0 }
        let expertUsefulness = Self.samples.map { $0.expected?.expertUsefulnessScore ?? 0.0 }

        aggregator.group("Relevance") { group in
            group.computeMean(of: relevance.metric)
            group.computeStandardDeviation(of: relevance.metric)
            group.custom(
                of: relevance.metric,
                label: "Relevance Alignment Score"
            ) { judge in
                Statistics.cohensKappa(ratings1: expertRelevance, ratings2: judge) ?? 0
            }
        }
        …
    }
```

and the test asserts on it (`:344-352`):

```swift
    @Test("Judge Calibration", .evaluates(evaluation))
    func evaluateJudgeCalibration() async throws {
        let result = EvaluationContext.current.result

        // Both the judge and the expert must produce an alignment score of 0.6
        // for the judge to be considered calibrated.
        #expect(result.aggregateValue(.custom(label: "Relevance Alignment Score")) > 0.6)
        #expect(result.aggregateValue(.custom(label: "Usefulness Alignment Score")) > 0.6)
    }
```

- **`aggregator.group(_:) { group in group.custom(of: Metric, label: String) { scores in Double } }`** —
  the closure receives the per-sample scores for that metric as **`[Double]` in dataset order**, and
  returns a single `Double`. That ordering guarantee is what makes the positional join valid.
- **`result.aggregateValue(.custom(label:))`** retrieves it by label — the same string.
- **Cohen's kappa is hand-rolled** in `Statistics.swift` (72 lines). The Evaluations framework does
  **not** ship an agreement statistic. κ > 0.6 is the sample's calibration bar.
- The judge prompt (`:216-283`) is **67 lines containing six labelled worked examples (A–F)** with
  explicit "Librarian: Relevance 4, Usefulness 4 / Why: …" rationales, and the instruction
  *"Score Relevance and Usefulness independently, even when one tag affects both."*
  **Few-shot calibration of a model judge is the technique, and this is the reference implementation.**
- The two `ScoreDimension` definitions here are **deliberately re-worded** versus the ones in
  `BookTags.swift` (compare `BookTags.swift:43-56` with `ModelJudgeAlignmentEvaluation.swift:175-189`):
  the calibration copy encodes the librarian's *generosity* ("small drift … is acceptable"). Tuning
  the dimension text is itself part of the hill-climb.

### 4.10 `SampleGenerator` — synthetic datasets (`BookSampleGenerator/main.swift`)

A **command-line tool target**, not a test. Verbatim, `:13-74`:

```swift
import Evaluations
import Foundation
import FoundationModels

let prompt = Prompt("""
        Generate diverse range of book reviews and corresponding tags.
        Cover a wide range of genres, time periods, cultures, and
        reader personas. Do not repeat books already in the dataset.
        """)

let dataset = Book.sampleBooks.map { book in
    ModelSample(prompt: book.review, expected: BookTags(tags: book.tags))
}

let targetCount = 100

var expandedDataset: [ModelSample<BookTags>] = dataset

let generator = SampleGenerator<ModelSample<BookTags>>(
    prompt,
    samples: dataset,
    targetCount: targetCount,
    // Uses Private Cloud Compute for larger, more diverse generations.
    sessionProvider: {
        LanguageModelSession(
            model: PrivateCloudComputeLanguageModel(),
            instructions: """
            You are a synthetic data generator for a book-tracking app's evaluation suite.
            …
            Rules:
            - Review must be at least 100 characters long.
            …
            """
            )
    },
    // Reject samples that violate the rules defined in the instructions.
    validator: { sample in
        guard let book = sample.expected else { return false }
        guard sample.promptDescription.count >= 100 else { return false }
        guard (3...8).contains(book.tags.count) else { return false }
        guard book.tags.allSatisfy({ $0 == $0.lowercased() }) else { return false }
        return true
    }
)

for try await sample in generator.run() {
    // Access results during iteration.
    expandedDataset.append(sample)
}

// Access results after iteration.
let allSamples = await generator.samples
let invalidSamples = await generator.invalidSamples
```

Confirmed signature: **`SampleGenerator<S>(_ prompt: Prompt, samples:targetCount:sessionProvider:validator:)`**,
generic over the *sample* type (`ModelSample<BookTags>`), with:
- **`sessionProvider: () -> LanguageModelSession`** — a *factory*, so the generator can spin up fresh
  sessions (context-window management for a 100-sample run).
- **`validator: (S) -> Bool`** — rejection sampling.
- **`generator.run()` is an `AsyncThrowingSequence`** yielding only *valid* samples.
- **`await generator.samples` / `await generator.invalidSamples`** — it's an **actor**; the rejects
  are retained for inspection.
- **`Prompt(_ string:)`** value initializer (no builder) — confirms that spelling.
- **`PrivateCloudComputeLanguageModel()` used with a bare `init()`**, no configuration, and the
  comment states the motive: "larger, more diverse generations".
- `ModelSample` is **`Codable`** — the tool JSON-encodes `[ModelSample<BookTags>]` straight to
  `synthetic_book_samples.json` (`:82-86`), which `JSONLoader(url:)` reads back.

### 4.11 `.xcevalresult` — the on-disk run format (`DatasetExtractor/main.swift`)

The second CLI parses **Xcode's evaluation result bundle**. This documents the file format, which no
session or doc article describes:

```
{ "results": [ { "Input": "<escaped JSON string>", "Response": { "value": "<string>" }, … } ] }
```
where the escaped `Input` string decodes to `{ "input": { "prompt": "…" } }`
(`DatasetExtractor/main.swift:15-32`, `:94-131`). Default output is
`~/Desktop/<BaseName>-extracted.json` (`:153-162`).

This is the **round trip that makes hill-climbing work**: run an evaluation in Xcode → export
`.xcevalresult` → `DatasetExtractor` → hand rows to a human expert to score → feed the scored file
back in as `BookTaggingEvaluation-extracted.json` for judge calibration. The bundled fixture in
`HillClimbingEvaluations/` is literally the output of this pipeline plus expert columns.

Note `DatasetExtractor` depends on **`ArgumentParser`** and ends with a comment worth quoting
(`:165-167`):

```swift
// @main cannot be used in main.swift — Swift's implicit top-level entry point and
// @main are mutually exclusive. Calling .main() explicitly is the equivalent.
DatasetExtractorCommand.main()
```

### 4.12 The feature under test, and `#Playground`

`BookTracker/Services/BookTaggingService.swift:13-45`:

```swift
@Generable
struct BookTags: Codable, Equatable {
    @Guide(description: "Descriptive tags capturing themes, genres, moods, and topics from the review", .count(3...8))
    var tags: [String]
}

struct BookTaggingService {
    static let instructions = """
        You are a librarian and literary analyst. …
          Rules:
           - Return between 3 and 8 tags.
        …
        """

    static func generateTags(for review: String) async throws -> BookTags {
        let prompt = tagsPrompt(review: review)
        let session = LanguageModelSession(
            model: SystemLanguageModel(guardrails: .permissiveContentTransformations),
            instructions: instructions
        )
        let response = try await session.respond(to: prompt, generating: BookTags.self)
        return response.content
    }
```

- **`@Guide(description: "…", .count(3...8))`** — the **two-argument** form: description **and** a
  variadic guide, `.count` taking a **`ClosedRange`**. (Origami used the one-arg forms
  `@Guide(description:)` and `@Guide(.minimumCount(3))`.) So all three spellings are real.
- **`SystemLanguageModel(guardrails:)` with `.permissiveContentTransformations`**.
- **Belt-and-braces constraint**: the 3–8 range is asserted in the `@Guide`, restated in the
  instructions prose, **and** checked by a heuristic `Evaluator`. That triple redundancy is the
  sample's implicit lesson — guides are a hint, not a guarantee, so measure it.
- `import Playgrounds` + a **`#Playground { … }`** block (`:76-101`) exercising two hand-written
  reviews. This is the fast inner loop that precedes the evaluation suite.

`BookTracker/Models/MockBooksModifier.swift:12` uses **`PreviewModifier`** with
`#Preview(traits: .modifier(MockBooksModifier()))` — how to preview AI-backed views without a model.


---

## 5. `SpotlightSearchTool` — "Searching indexed content with natural language" (session 246)

Archive `SearchingIndexedContentWithNaturalLanguage/`, target **`LLMSearchUsingCoreSpotlightApp`**.
`IPHONEOS_DEPLOYMENT_TARGET = 27.0`, `SWIFT_VERSION = 6.0`. **Entitlements file is an empty `<dict/>`** —
`SpotlightSearchTool` needs *no* entitlement. Only 6 Swift files, 792 lines total.

README (`README.md`): *"This sample demonstrates `SpotlightSearchTool`, a type that connects a
Foundation Models language-model session to your app's Core Spotlight index… The app indexes a
collection of hiking trail entries as `CSSearchableItem` objects, then lets people ask
natural-language questions like 'Which trails in California have water features?'"*

### 5.1 Constructing the tool — the whole API in 15 lines

`LLMSearchUsingCoreSpotlightApp/Session.swift:116-158`:

```swift
    private static let fetchAttributes: [SearchableItemAttribute] = {
        var attributes: [SearchableItemAttribute] = [
            .title,
            .contentDescription,
            .namedLocation,
            .stateOrProvince,
            .keywords,
            .latitude,
            .longitude,
            .rating,
            .duration,
            .contentCreationDate,
            .completionDate
        ]
        if let key = SpotlightIndexer.distanceAttributeKey {
            attributes.append(SearchableItemAttribute(rawValue: key.keyName))
        }
        return attributes
    }()

    private func makeSpotlightTool() -> SpotlightSearchTool {
        SpotlightSearchTool(
            configuration: .init(
                sources: [
                    .coreSpotlight(
                        .init(
                            searchableIndexDelegate: SpotlightIndexer.shared,
                            fetchAttributes: Self.fetchAttributes
                        )
                    )
                ],
                guide: isOnDevice ? .focused() : .complete
            )
        )
    }

    private func makeSession(tool: SpotlightSearchTool) -> LanguageModelSession {
        LanguageModelSession(
            model: serverModel,
            tools: [tool],
            instructions: instructions
        )
    }
```

Confirmed spellings:
- **`SpotlightSearchTool(configuration:)`**; the configuration has **`sources: [...]`** and **`guide:`**.
- **`.coreSpotlight(.init(searchableIndexDelegate:fetchAttributes:))`** is a *source* case. (Session
  246 narration mentioned a `FileSource`; the archive only exercises `.coreSpotlight` —
  other source cases are **UNVERIFIED**.)
- **`SearchableItemAttribute`** is a `RawRepresentable` struct with static members
  (`.title`, `.contentDescription`, `.namedLocation`, `.stateOrProvince`, `.keywords`, `.latitude`,
  `.longitude`, `.rating`, `.duration`, `.contentCreationDate`, `.completionDate`) **and a
  `init(rawValue:)`** for custom keys — `SearchableItemAttribute(rawValue: key.keyName)` bridges a
  `CSCustomAttributeKey` into the fetch list. **This is how custom attributes reach the model.**
- **Guidance profiles are `guide:` values: `.focused()` (a function call) and `.complete`
  (a plain member).** `.focused()` taking parens implies parameters with defaults — **UNVERIFIED**
  what they are. The sample picks **`.focused()` for on-device and `.complete` for the server
  model**, i.e. *guidance level is a function of model capacity*.
- The tool is passed through the ordinary **`LanguageModelSession(model:tools:instructions:)`** —
  it's just a `Tool`.
- The model-facing tool name is **`spotlight_search`** (snake_case), per the instructions text at
  `Session.swift:43`: *"Always use the spotlight_search tool to search trails before answering.
  Never answer from memory."*

### 5.2 Reading results out of the tool — the side channel

`Session.swift:160-181`:

```swift
    private func listenForSearchResults(from tool: SpotlightSearchTool) -> Task<Void, Never> {
        Task { @MainActor in
            var seen: Set<String> = []
            for await reply in tool.searchResults {
                let items: [CSSearchableItem]
                switch reply.content {
                case .items(let searchItems):
                    items = searchItems.map(\.item)
                case .scoredItems(let scored):
                    items = scored.map(\.item.item)
                case .groupedItems(let groups):
                    items = groups.values.flatMap { $0 }.map(\.item)
                case .count, .table, .statistic, .text:
                    continue
                @unknown default:
                    continue
                }
                let newItems = items.filter { seen.insert($0.uniqueIdentifier).inserted }
                self.results.append(contentsOf: newItems)
            }
        }
    }
```

**`tool.searchResults` is an `AsyncSequence` of replies** you consume *in parallel with* the response
stream. `reply.content` is a **frozen-ish enum with at least seven cases**:
`.items(_)`, `.scoredItems(_)`, `.groupedItems(_)`, `.count`, `.table`, `.statistic`, `.text`
— plus `@unknown default`, so it is **non-frozen**. Note the nesting depth:
`.items` elements have `.item` (→ `CSSearchableItem`); `.scoredItems` elements have `.item.item`;
`.groupedItems` is a **dictionary** (`groups.values.flatMap { $0 }.map(\.item)`).

This is the sample's most transferable idea: **the model narrates in prose while the app renders the
actual `CSSearchableItem`s it touched** — grounded UI, no parsing of the model's text.
De-duplication is by `uniqueIdentifier` across multiple tool calls in one turn.

`Session.swift:96-112` — *"Creates a fresh session and tool for each search so that every query
starts with fresh context."* One tool instance per query, because the tool accumulates results.

### 5.3 The index side, incl. `searchableItems(forIdentifiers:)`

`Indexer.swift:34-58`:

```swift
final class SpotlightIndexer: NSObject, CSSearchableIndexDelegate {
    static let shared = SpotlightIndexer()
    let index = CSSearchableIndex(name: "TrailSearchSample")

    static let distanceAttributeKey: CSCustomAttributeKey? = CSCustomAttributeKey(
        keyName: "distance",
        searchable: true,
        searchableByDefault: true,
        unique: false,
        multiValued: false
    )
    …
    private override init() {
        super.init()
        index.indexDelegate = self
    }
```

**The hydration delegate method** (`Indexer.swift:123-128`) — this is the one session 246 called out:

```swift
    nonisolated func searchableItems(forIdentifiers identifiers: [String], searchableItemsHandler: @escaping @Sendable ([CSSearchableItem]) -> Void) {
        Task { @MainActor in
            let items = createSearchableItems(identifiers: identifiers)
            searchableItemsHandler(items)
        }
    }
```

Exact signature: **`searchableItems(forIdentifiers:searchableItemsHandler:)`**, `nonisolated`, with
an `@escaping @Sendable ([CSSearchableItem]) -> Void` completion. **This is what lets the tool return
live, full attribute sets rather than whatever was frozen into the index** — the tool hands you IDs,
you hand back hydrated items. Passing `SpotlightIndexer.shared` as
`searchableIndexDelegate:` in the tool configuration is what wires it up.

Batch indexing with client-state gating (`Indexer.swift:62-88`): `index.fetchLastClientState`,
`index.beginBatch()`, `try await index.indexSearchableItems(items)`,
`try await index.endBatch(withClientState:)` — the **async/await** spellings.

Custom attribute round trip: `attributeSet.setValue(NSNumber(value: distance), forCustomKey: key)`
(`Indexer.swift:180`) written at index time, then surfaced to the model via
`SearchableItemAttribute(rawValue: key.keyName)` in `fetchAttributes`.

### 5.4 Prompt engineering: the index schema *is* the system prompt

`Session.swift:40-82` is a 40-line instructions string that **enumerates every indexed attribute with
its semantics and units** ("rating (difficulty 1 to 5, where 1 is Easy…)", "duration (estimated time
in seconds)", "distance (trail distance in miles, stored as a custom attribute)"), then gives
negative constraints:

- *"All trails are indexed with contentType `public.text`. Do not filter by contentType. Use keyword
  and text predicates instead."*
- *"Search for the meaningful topic in the request, not generic words like 'trail', 'trails', 'hike'…"*
- *"When searching for a topic, also search for related words. For example, 'water' could also mean
  lakes, rivers, creeks, waterfalls, ocean, tidepools, or swimming."*
- *"If the user asks about an attribute that isn't indexed (for example: elevation gain, calories,
  pace), say plainly that this data is not available rather than inventing values."*

**The retrieval quality lives in the instructions, not the API.** A guide section should reproduce
this verbatim as the template: *describe your schema, forbid unindexed inference, seed synonyms.*

Note the **PCC opt-in comment block is byte-for-byte the same as Origami's**
(`Session.swift:27-34` vs `OrchestratorProfile.swift:14-21`), including the
`type(of: serverModel) == SystemLanguageModel.self` check. This is clearly a house pattern across
the 2026 samples.

### 5.5 Error handling — identical taxonomy, independently confirmed

`LLMSearchUsingCoreSpotlightApp/Error+DisplayMessage.swift:11-32` is the **same file** as Origami's
minus the `GeneratedContent.ParsingError` clause: `SystemLanguageModel.Error` first, then
`LanguageModelError` with `.timeout` / `.guardrailViolation, .refusal` / `.contextSizeExceeded` /
`.unsupportedLanguageOrLocale` / `default: break`. **Two independent samples agreeing on these five
case names is as strong a confirmation as we can get without the headers.**


---

## 6. FoundationModelsCoffeeGame — generative game content

⚠️ **VINTAGE WARNING: this sample is WWDC25-era, not WWDC26.**
`IPHONEOS_DEPLOYMENT_TARGET = 26.0`, `MACOSX_DEPLOYMENT_TARGET = 26.0`, `SWIFT_VERSION = 6.0`.
It uses **no** Dynamic Profiles, no `LanguageModelError`, no PCC. Everything in it is iOS 26 API that
presumably still compiles. Treat as "the iOS 26 baseline", useful for showing *what changed*.

21 Swift files under `FoundationModelsCoffeeGame/`. AI-relevant: `GenerateDialog/`,
`GenerateEncounters/`, `ToolCalling/`, `SpriteKitScene/RandomCustomerGenerator.swift`.

### 6.1 Availability — the pattern Origami/Spotlight omit

`MainMenu/MainMenuView.swift:47-70` — the **only** availability switch in any of the five archives:

```swift
            switch SystemLanguageModel.default.availability {
            case .available:
                gameStartButton
            case .unavailable(let reason):
                switch reason {
                case .appleIntelligenceNotEnabled:
                    Text("To play this game, turn on Apple Intelligence in Settings.")
                        .modifier(GameBoxStyle())
                case .modelNotReady:
                    Text("Cannot start the game until model is ready to use. Come back later!")
                        .modifier(GameBoxStyle())
                case .deviceNotEligible:
                    Text(":( Sorry, this game needs a device compatible with Apple Intelligence.")
                        .modifier(GameBoxStyle())
                default:
                    Text(":( Sorry, cannot start game. The model is unavailable for unknown reasons.")
```

Confirms `SystemLanguageModel.default.availability` → `.available` / `.unavailable(reason)` with
reasons `.appleIntelligenceNotEnabled`, `.modelNotReady`, `.deviceNotEligible` (+ `default`).
**The 2026 samples replaced this proactive gate with reactive `SystemLanguageModel.Error` catching.**
Worth flagging as a possible regression in Apple's own guidance — a guide should probably do both.

### 6.2 Manual `Generable` conformance — the escape hatch

`GenerateEncounters/GenerableImage.swift:12-62`. This is the **only** hand-written `Generable`
conformance in any sample, and it's the reference for when the macro won't do:

```swift
@MainActor
@Observable
final class GenerableImage: Generable, Equatable {
    …
    @Guide(
        description:
            "Avoid descriptions that look human-like. Stick to animals, plants, or objects."
    )
    let imageDescription: String

    let imageStyle: ImagePlaygroundStyle = .sketch
    …
    nonisolated static var generationSchema: GenerationSchema {
        GenerationSchema(
            type: GenerableImage.self,
            description: """
                A description of an image to be given to a image generation model. \
                The description should be short and non-human-like.
                """,
            properties: [
                GenerationSchema.Property(
                    name: "imageDescription",
                    type: String.self
                )
            ]
        )
    }

    nonisolated var generatedContent: GeneratedContent {
        GeneratedContent(properties: [
            "imageDescription": imageDescription
        ])
    }

    nonisolated init(_ content: GeneratedContent) throws {
        self.imageDescription = try content.value(forProperty: "imageDescription")
        Logging.general.log("Generating image for description: \(self.imageDescription)")
        Task { try await self.generateImage() }
    }
```

Three requirements: **`static var generationSchema: GenerationSchema`**,
**`var generatedContent: GeneratedContent`**, **`init(_ content: GeneratedContent) throws`**.
Plus `GenerationSchema(type:description:properties:)`, `GenerationSchema.Property(name:type:)`,
`GeneratedContent(properties: [String: …])`, `content.value(forProperty:) throws`.

**The trick worth stealing:** a `Generable` whose *initializer kicks off a side effect*. Decoding
the model's `imageDescription` immediately launches an ImagePlayground generation
(`Task { try await self.generateImage() }`), so a *class* `Generable` becomes a live view model that
the SwiftUI hierarchy observes while the picture renders. It chains **text generation → image
generation** in one type. Cross-framework bridge: `import ImagePlayground`, `try await ImageCreator()`,
`generator.images(for: [.text(prompt)], style: .sketch, limit: 1)` yielding `generation.cgImage`
(`:72-88`), with a fallback description on failure (`:16`, `:95+`).

### 6.3 Context-window management by transcript surgery

`GenerateDialog/DialogEngine.swift:103-127` — the iOS 26 way to do what `.historyTransform` now does:

```swift
    private func resetSession(_ character: any Character, previousSession: LanguageModelSession) {
        let allEntries = previousSession.transcript
        var condensedEntries = [Transcript.Entry]()
        if let firstEntry = allEntries.first {
            condensedEntries.append(firstEntry)
            if allEntries.count > 1, let lastEntry = allEntries.last {
                condensedEntries.append(lastEntry)
            }
        }

        // A transcript includes instructions, so consider checking
        // whether the tool is still necessary for the session.
        let condensedTranscript = Transcript(entries: condensedEntries)
        var newSession: LanguageModelSession
        if let customer = character as? GeneratedCustomer {
            newSession = LanguageModelSession(
                tools: [CalendarTool(contactName: customer.displayName)],
                transcript: condensedTranscript
            )
        } else {
            newSession = LanguageModelSession(transcript: condensedTranscript)
        }
        newSession.prewarm()
        conversations[character.id] = newSession
    }
```

- **`LanguageModelSession(transcript:)` and `LanguageModelSession(tools:transcript:)`** — note the
  label is **`transcript:`** here, versus **`history:`** in Origami's `init(profile:history:)`.
  Both labels exist; **UNVERIFIED** whether `transcript:` is deprecated in iOS 27.
- **Keep first + last entry** — the first entry *is the instructions*, hence the comment.
- **`session.prewarm()`** — called right after constructing a session that will be used soon.
  Only appears in this sample.
- `session.transcript` is directly `Collection`-like (`.first`, `.last`, `.count`).

### 6.4 Misc confirmations from the coffee game

- `@Guide(.count(2))` on `let attributes: [Attribute]` (`GenerateDialog/Characters.swift:70`) —
  exact count, no description. Third `@Guide` arity observed across the corpus.
- **`@Generable` enums with no raw type** and no associated values
  (`Characters.swift:79-92`: `enum Attribute { case sassy, tired, … }`) — contrast with Origami's
  `String`-raw-valued enums. Both work.
- `@Generable struct GeneratedCustomer: Character` conforming to an **app protocol**, mixing
  `@Guide`d model-filled fields with hard-coded `let persona = "…"` defaults the model never sees.
- Tools live in `ToolCalling/`: `CalendarTool`, `ContactsTool` — tools carrying **injected
  per-conversation config** (`CalendarTool(contactName: customer.displayName)`), the same
  dependency-injection-into-a-Tool idea as Origami's `MovePhotoToStepTool(orchestrator:)`.
- Every `Character` declares an **`errorResponse` string** (`Characters.swift:57`, `:94`) — an
  in-world fallback line used when generation fails, so failures stay diegetic. Nice UX pattern.

---

## 7. SwiftTranscriptionSampleApp — SpeechAnalyzer

⚠️ **NEGATIVE FINDING — this is the WWDC25 sample and it has NOT been refreshed for WWDC26.**

`README.md`: *"This sample code project is associated with **WWDC25 session 277**: Bring advanced
speech-to-text capabilities to your app with SpeechAnalyzer."*
`IPHONEOS_DEPLOYMENT_TARGET = 26.0`, `MACOSX_DEPLOYMENT_TARGET = 26.0`, `SWIFT_VERSION = 5.0`.
Git history inside the archive is two commits: `c57e937 Initial release for WWDC25`,
`c28fe49 Updated to latest SDK`.

**The WWDC26 APIs the brief asked for are ABSENT from the sample.** Verified by exhaustive grep over
all 8 Swift files:

| Requested API | Present in sample? |
|---|---|
| `SpeechAnalyzer` | ✅ yes |
| `SpeechTranscriber` | ✅ yes |
| `AssetInventory` | ✅ yes (`assetInstallationRequest(supporting:)`, `reservedLocales`, `release(reservedLocale:)`) |
| `AnalyzerInput` | ✅ yes |
| **`DictationTranscriber`** | ❌ **absent** |
| **`CaptureInputSequenceProvider`** | ❌ **absent** |
| **`SFCustomLanguageModelData`** | ❌ **absent** |
| **`datagenerator` CLI** | ❌ **absent** (no CLI target at all) |

Those symbols **do exist** in the shipped `speech` documentation index — e.g.
`DictationTranscriber` at `/documentation/speech/dictationtranscriber` with
`init(locale:preset:)` and
`init(locale:contentHints:transcriptionOptions:reportingOptions:attributeOptions:)`, and
`DictationTranscriber.Preset` statics **`.phrase`, `.shortDictation`, `.progressiveShortDictation`,
`.longDictation`, `.progressiveLongDictation`, `.timeIndexedLongDictation`** — but **no sample code
demonstrates them.** For the guide, `DictationTranscriber` must be sourced from docs/transcripts,
clearly marked as not sample-verified.

### 7.1 What the sample does confirm (iOS 26 baseline)

`SwiftTranscriptionSampleApp/Recording and Transcription/Transcription.swift:39-82`:

```swift
    func setUpTranscriber() async throws {
        transcriber = SpeechTranscriber(locale: Locale.current,
                                        transcriptionOptions: [],
                                        reportingOptions: [.volatileResults],
                                        attributeOptions: [.audioTimeRange])

        guard let transcriber else {
            throw TranscriptionError.failedToSetupRecognitionStream
        }

        analyzer = SpeechAnalyzer(modules: [transcriber])

        do {
            try await ensureModel(transcriber: transcriber, locale: Locale.current)
        } catch let error as TranscriptionError {
            print(error)
            return
        }

        self.analyzerFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber])
        (inputSequence, inputBuilder) = AsyncStream<AnalyzerInput>.makeStream()

        guard let inputSequence else { return }

        recognizerTask = Task {
            do {
                for try await case let result in transcriber.results {
                    let text = result.text
                    if result.isFinal {
                        finalizedTranscript += text
                        volatileTranscript = ""
                        updateStoryWithNewText(withFinal: text)
                    } else {
                        volatileTranscript = text
                        volatileTranscript.foregroundColor = .purple.opacity(0.4)
                    }
                }
            } catch {
                print("speech recognition failed")
            }
        }

        try await analyzer?.start(inputSequence: inputSequence)
    }
```

- **`SpeechTranscriber(locale:transcriptionOptions:reportingOptions:attributeOptions:)`**,
  with `.volatileResults` and `.audioTimeRange`.
- **`SpeechAnalyzer(modules:)`**, `SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith:)`,
  `analyzer.start(inputSequence:)`, `analyzer.finalizeAndFinishThroughEndOfInput()` (`:101`).
- **Input is a plain `AsyncStream<AnalyzerInput>`** built with `.makeStream()`; you `yield`
  `AnalyzerInput(buffer:)` after format conversion (`:88-97`).
- **`result.text` is an `AttributedString`** — the sample styles the volatile portion by assigning
  `volatileTranscript.foregroundColor` (`:73`). The volatile/final split
  (`result.isFinal`) is the whole UX.

Asset lifecycle (`:108-142`) — the complete graceful-degradation ladder:

```swift
    public func ensureModel(transcriber: SpeechTranscriber, locale: Locale) async throws {
        guard await supported(locale: locale) else {
            throw TranscriptionError.localeNotSupported
        }
        if await installed(locale: locale) {
            return
        } else {
            try await downloadIfNeeded(for: transcriber)
        }
    }

    func supported(locale: Locale) async -> Bool {
        let supported = await SpeechTranscriber.supportedLocales
        return supported.map { $0.identifier(.bcp47) }.contains(locale.identifier(.bcp47))
    }

    func installed(locale: Locale) async -> Bool {
        let installed = await Set(SpeechTranscriber.installedLocales)
        return installed.map { $0.identifier(.bcp47) }.contains(locale.identifier(.bcp47))
    }

    func downloadIfNeeded(for module: SpeechTranscriber) async throws {
        if let downloader = try await AssetInventory.assetInstallationRequest(supporting: [module]) {
            self.downloadProgress = downloader.progress
            try await downloader.downloadAndInstall()
        }
    }

    func releaseLocales() async {
        let reserved = await AssetInventory.reservedLocales
        for locale in reserved {
            await AssetInventory.release(reservedLocale: locale)
        }
    }
```

`supportedLocales` → `installedLocales` → `assetInstallationRequest(supporting:)` →
`downloader.progress` (a `Progress`, bindable to SwiftUI) → `downloadAndInstall()`.
And **`AssetInventory.reservedLocales` / `.release(reservedLocale:)`** — there is a *quota* on
reserved locales that apps must release. Comparing locales **by `.identifier(.bcp47)`**, not by
`Locale` equality, is deliberate and easy to get wrong.


---

## 8. Bonus: AddingIntelligentAppFeaturesWithGenerativeModels (`FoundationModelsTripPlanner`)

⚠️ Also **iOS 26** (`IPHONEOS_DEPLOYMENT_TARGET = 26.0`). Included only because it is the *canonical*
Foundation Models sample and shows the iOS 26 baseline the 2026 samples moved away from.

Two confirmations worth recording (`FoundationModelsTripPlanner/Views/Itinerary/LandmarkDescriptionView.swift`):

```swift
    let contentTaggingModel = SystemLanguageModel(useCase: .contentTagging)      // :22
    …
            if !contentTaggingModel.isAvailable { return }                        // :48
                let session = LanguageModelSession(model: contentTaggingModel)    // :50
```

- **`SystemLanguageModel(useCase: .contentTagging)`** — the specialized-use-case initializer.
- **`model.isAvailable`** — a Bool convenience alongside `.availability`.
- **`LanguageModelSession(model:)`** with no instructions and no tools.

---

## 9. Cross-cutting patterns worth reproducing in the guide series

Ranked by how much they'd improve a guide, and by how hard they'd be to invent from transcripts alone.

**1. The DynamicProfile as a projection of an `@Observable` state machine.**
Origami's entire "agentic" behaviour is: an `@Observable` orchestrator holds `state.mode`; the
profile's `body` `switch`es on it; mutating the mode *is* the agent handoff, and the shared session's
transcript carries across. Reduce/effect separation (`OrchestratorState.swift`,
`Orchestrator.swift:165-334`) keeps it testable. **This is the mental model to teach.** The profile
is not a config object — it is a *derived view* of app state, exactly like a SwiftUI `body`.

**2. Labelled image attachments + `ImageReference` round-tripping.**
`Attachment(image).label(photo.idString)` → `@Generable` field `var image: ImageReference` →
`image.attachmentLabel` → look up the app object. This is the only way to do multi-image analysis
where the output must be keyed back to specific inputs, and no session explains it.
(`Photo.swift:77-91`, `ImageAnalysis.swift:11-21`, `BrainstormModel.swift:142-144`.)

**3. The full evaluation ladder, exactly as Book Tracker layers it.**
`#Playground` (seconds) → heuristic `Evaluator`s over a curated `ArrayLoader` (deterministic,
cheap) → `ModelJudgeEvaluator` with `ScoreDimension`s (subjective quality) → `SampleGenerator` over
PCC to reach 100 samples (coverage) → **judge calibration against human scores via Cohen's kappa**
(is the judge trustworthy?) → `.evaluates(…, info: ["Prompt": …])` so runs are diffable.
The last two rungs are what separate real eval-driven development from vibes, and the
`DatasetExtractor` CLI is the missing link that gets model output in front of a human scorer.

**4. Tool-mediated human-in-the-loop.**
`MovePhotoToStepTool` takes the orchestrator as a dependency, mutates `coach.pendingMoveTo`, and
returns *"Asked the user to confirm…"* to the model. The UI swaps its text field for Yes/No; the
answer re-enters as a new user turn with a synthesized note explaining what happened
(`Orchestrator.swift:500-561`). **A tool call can be a request for consent, not just a computation.**

**5. Two-channel results: prose from the model, objects from the tool.**
`SpotlightSearchTool.searchResults` streams `CSSearchableItem`s while `session.streamResponse`
streams the narration. The app renders real records and never parses the model's text
(`Session.swift:160-181`). Generalizes to any retrieval tool: **have the tool publish its hits on a
side channel and bind your list view to that.**

Runners-up worth a sidebar:
- **Reveal N−1 during streaming** (`BrainstormModel.swift:120-123`) — stops guided-generation text
  from visibly growing.
- **A stream can yield zero partials when the model only emits a tool call** —
  `CoachModel.swift:67-72` handles it explicitly. Any "spinner until first token" UI is a bug.
- **Tools return prose on failure, not throws** (`CraftTools.swift:30`: *"No template available.
  Please try your best…"*).
- **Hallucination filter**: drop extracted terms that don't literally occur in the source
  (`TermExtractor.swift:48-51`).
- **Cache before inference** (`TermModel.swift:87-99`) — "skip the LLM call entirely" on a hit.
- **`TranscriptRecorder`** — JSON-dump `session.transcript` after every effect behind a debug toggle
  (`TranscriptRecorder.swift`). Cheap, and the single best debugging aid in the corpus.
- **The index schema as system prompt** (`Session.swift:40-82`) — enumerate attributes + units,
  forbid inference about unindexed fields, seed synonyms.
- **`PreviewModifier` + `#Preview(traits: .modifier(…))`** for previewing AI-backed views without a model.
- **In-world error strings** (`Characters.swift:57`) so failures stay diegetic.

---

## 10. Open questions / UNVERIFIED

1. **Does `Profile(model:) { … }` exist?** Only `Profile { … }.model(_:)` appears. Our 242-derived
   reconstruction used the init form. UNVERIFIED.
2. **What parameters does `.focused()` take?** It is called with empty parens next to the
   parenthesis-free `.complete`, implying defaulted arguments. UNVERIFIED.
3. **Other `SpotlightSearchTool` source cases.** Session 246 mentioned a `FileSource`; only
   `.coreSpotlight` is exercised. UNVERIFIED.
4. **Custom `PipelineStage`s and the contact resolver** (session 246) — absent from the sample.
   UNVERIFIED.
5. **`ModelJudgePrompt.reference`'s second closure parameter** — discarded (`_`) in both usages.
   Plausibly the `ModelSubject`. UNVERIFIED.
6. **`ScoreDimension.scale` cases other than `.numeric`.** Only `.numeric([Int: String])` appears.
7. **`ArgumentMatcher` value cases other than `.string(_)`.** No `.number`/`.bool`/`.array` in the corpus.
8. **`history:` vs `transcript:` on `LanguageModelSession.init`.** Both appear (in a 27.0 and a 26.0
   sample respectively). Is `transcript:` deprecated in iOS 27? UNVERIFIED.
9. **Why does `Transcript.Response` require `assetIDs`, and what does `[""]` mean?** Origami passes
   an array containing an empty string. Undocumented.
10. **Structured tool output.** `Tool.Output` exists as an associated type but every sample sets it
    to `String`. Whether a `@Generable` `Output` is supported is UNVERIFIED.
11. **`LanguageModelError`'s full case list.** Both samples end with `default: break`; at least
    `.rateLimited` and `.unsupportedGenerationGuide` exist per our doc harvest but appear nowhere.
12. **`LanguageModelSession.Error`** — listed in the docs, used by no sample.
13. **Origami's missing availability gate.** Is reactive `SystemLanguageModel.Error` catching now the
    recommended posture, or is this an oversight in the sample? The iOS 26 coffee game gates
    proactively on `SystemLanguageModel.default.availability`. Guides should probably do both.
14. **Book Tracker builds at `SWIFT_VERSION = 5.0`** while Origami/Spotlight are 6.0, and Book
    Tracker's `SUPPORTED_PLATFORMS` omits macOS despite an `SDKROOT = macosx` config. Possibly
    just sample-project untidiness; noted in case it signals an Evaluations-framework constraint.
15. **No `coreai` sample code exists.** The `coreai` doc index contains zero `sampleCode` entries.
    Anything we write about that framework is doc/transcript-sourced only.
16. **Speech WWDC26 surface has no sample at all** — see §7. `DictationTranscriber.Preset` statics
    (`.phrase`, `.shortDictation`, `.progressiveShortDictation`, `.longDictation`,
    `.progressiveLongDictation`, `.timeIndexedLongDictation`) are index-confirmed but never
    exercised in compiling code.

### Reproducing this harvest

```bash
# 1. find samples in a framework
curl -sL "https://developer.apple.com/tutorials/data/index/<framework>" | \
  python3 -c "import json,sys;d=json.load(sys.stdin);
def w(n):
  print(n.get('title'),n.get('path')) if n.get('type')=='sampleCode' else None
  [w(c) for c in n.get('children') or []]
[w(n) for rt in d['interfaceLanguages'].values() for n in rt]"

# 2. get the ZIP URL for one
curl -sL "https://developer.apple.com/tutorials/data/documentation/<fw>/<slug>.json" | \
  grep -o 'https://docs-assets.developer.apple.com[^"]*\.zip'
```
